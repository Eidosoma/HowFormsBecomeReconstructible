from __future__ import annotations

import hashlib
import os
import warnings
from dataclasses import replace
from typing import Any, Sequence

import numpy as np

from .reference import ReferenceBackend
from .types import CategoricalModel, InferenceResult, PolicyResult


def configure_jax_environment() -> None:
    """Set deterministic CPU defaults before importing JAX or pymdp."""

    os.environ.setdefault("JAX_ENABLE_X64", "true")
    os.environ.setdefault("JAX_PLATFORMS", "cpu")
    os.environ.setdefault("JAX_COMPILATION_CACHE_DIR", "/tmp/fep_lab_jax_cache")
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/fep_lab_matplotlib")


def _imports() -> tuple[Any, Any, Any]:
    configure_jax_environment()
    import jax
    import jax.numpy as jnp
    from pymdp.agent import Agent

    jax.config.update("jax_enable_x64", True)
    return jax, jnp, Agent


def model_fingerprint(model: CategoricalModel) -> str:
    digest = hashlib.sha256()
    for value in (*model.A, model.B, *model.C, model.D, model.policies):
        array = np.ascontiguousarray(value)
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(array.tobytes())
    digest.update(str(model.gamma).encode("ascii"))
    digest.update(str(model.use_utility).encode("ascii"))
    digest.update(str(model.use_states_info_gain).encode("ascii"))
    return digest.hexdigest()


class PymdpBackend:
    """Adapter from the laboratory's immutable model to pymdp's JAX Agent API."""

    name = "pymdp"

    def __init__(self) -> None:
        self._agents: dict[tuple[str, int], Any] = {}
        self._batch_functions: dict[tuple[str, int], tuple[Any, Any]] = {}
        self._reference = ReferenceBackend()

    def _agent(self, model: CategoricalModel, batch_size: int = 1) -> Any:
        key = (model_fingerprint(model), batch_size)
        if key in self._agents:
            return self._agents[key]
        _jax, jnp, Agent = _imports()
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="A JAX array is being set as static!.*"
            )
            agent = Agent(
                A=[jnp.asarray(value) for value in model.A],
                B=[jnp.asarray(model.B)],
                C=[jnp.asarray(value) for value in model.C],
                D=[jnp.asarray(model.D)],
                E=jnp.asarray(model.policy_prior),
                A_dependencies=[[0] for _ in model.A],
                B_dependencies=[[0]],
                num_controls=[model.n_actions],
                control_fac_idx=[0],
                policy_len=model.horizon,
                policies=jnp.asarray(model.policies[:, :, None]),
                gamma=model.gamma,
                use_utility=model.use_utility,
                use_states_info_gain=model.use_states_info_gain,
                use_param_info_gain=False,
                action_selection="stochastic",
                batch_size=batch_size,
            )
        self._agents[key] = agent
        return agent

    def _compiled_batch_functions(
        self, model: CategoricalModel, batch_size: int
    ) -> tuple[Any, Any]:
        key = (model_fingerprint(model), batch_size)
        if key in self._batch_functions:
            return self._batch_functions[key]
        jax, _jnp, _Agent = _imports()
        agent = self._agent(model, batch_size=batch_size)

        def infer_fn(observations: tuple[Any, ...], priors: Any) -> Any:
            return agent.infer_states(
                list(observations),
                empirical_prior=[priors],
                return_info=True,
            )

        def policy_fn(posteriors: Any) -> Any:
            return agent.infer_policies([posteriors[:, None, :]])

        functions = (jax.jit(infer_fn), jax.jit(policy_fn))
        self._batch_functions[key] = functions
        return functions

    def infer_states(
        self,
        model: CategoricalModel,
        observation: Sequence[int],
        predictive_prior: np.ndarray,
    ) -> InferenceResult:
        _jax, jnp, _Agent = _imports()
        agent = self._agent(model)
        qs, info = agent.infer_states(
            [jnp.asarray([int(value)]) for value in observation],
            empirical_prior=[jnp.asarray(np.asarray(predictive_prior)[None, :])],
            return_info=True,
        )
        posterior = np.asarray(qs[0], dtype=np.float64)[0, -1].copy()
        likelihood = np.ones(model.n_states, dtype=np.float64)
        for modality, observed in zip(model.A, observation):
            likelihood *= modality[int(observed)]
        evidence = float(np.asarray(predictive_prior) @ likelihood)
        return InferenceResult(
            posterior=posterior,
            predictive_prior=np.asarray(predictive_prior, dtype=np.float64).copy(),
            log_evidence=float(np.log(evidence)),
            vfe=float(np.asarray(info["vfe"])[0]),
        )

    def score_policies(
        self, model: CategoricalModel, posterior: np.ndarray
    ) -> PolicyResult:
        _jax, jnp, _Agent = _imports()
        agent = self._agent(model)
        qs = [jnp.asarray(np.asarray(posterior)[None, None, :])]
        q_pi, neg_efe = agent.infer_policies(qs)
        diagnostic = self._reference.score_policies(model, posterior)
        return replace(
            diagnostic,
            neg_efe=np.asarray(neg_efe, dtype=np.float64)[0].copy(),
            posterior=np.asarray(q_pi, dtype=np.float64)[0].copy(),
        )

    def sample_action(
        self,
        result: PolicyResult,
        n_actions: int,
        rng: np.random.Generator,
    ) -> int:
        return self._reference.sample_action(result, n_actions, rng)

    def infer_states_batch(
        self,
        model: CategoricalModel,
        observations: np.ndarray,
        predictive_priors: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        values = np.asarray(observations, dtype=np.int64)
        priors = np.asarray(predictive_priors, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != len(model.A):
            raise ValueError("batched observations have an incompatible shape")
        if priors.shape != (values.shape[0], model.n_states):
            raise ValueError("batched priors have an incompatible shape")
        _jax, jnp, _Agent = _imports()
        infer_fn, _policy_fn = self._compiled_batch_functions(model, len(values))
        qs, info = infer_fn(
            tuple(jnp.asarray(values[:, index]) for index in range(values.shape[1])),
            jnp.asarray(priors),
        )
        return (
            np.asarray(qs[0], dtype=np.float64)[:, -1, :].copy(),
            np.asarray(info["vfe"], dtype=np.float64).copy(),
        )

    def score_policies_batch(
        self, model: CategoricalModel, posteriors: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        values = np.asarray(posteriors, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != model.n_states:
            raise ValueError("batched posteriors have an incompatible shape")
        _jax, jnp, _Agent = _imports()
        _infer_fn, policy_fn = self._compiled_batch_functions(model, len(values))
        q_pi, neg_efe = policy_fn(jnp.asarray(values))
        return (
            np.asarray(q_pi, dtype=np.float64).copy(),
            np.asarray(neg_efe, dtype=np.float64).copy(),
        )


def dependency_versions() -> dict[str, str]:
    configure_jax_environment()
    from importlib.metadata import version

    packages = (
        "inferactively-pymdp",
        "jax",
        "jaxlib",
        "numpy",
        "scipy",
    )
    return {package: version(package) for package in packages}
