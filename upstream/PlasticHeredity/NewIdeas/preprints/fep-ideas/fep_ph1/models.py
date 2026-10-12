from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import sha256_bytes
from fep_lab.reference import softmax
from fep_lab.types import CategoricalModel, PolicyResult

from .config import ExperimentConfig
from .types import Action


OBSERVATION_SIZES = (4, 3, 3, 4)
N_STATES = 9
N_ACTIONS = 4


def hidden_state(regime: int, alignment: int) -> int:
    if not 0 <= int(regime) < 3 or not 0 <= int(alignment) < 3:
        raise ValueError("hidden state factors are outside the frozen alphabet")
    return 3 * int(regime) + int(alignment)


def state_factors(state: int) -> tuple[int, int]:
    if not 0 <= int(state) < N_STATES:
        raise ValueError("hidden state is outside the frozen alphabet")
    return divmod(int(state), 3)


@dataclass
class ModelCounts:
    likelihood: tuple[NDArray[np.float64], ...]
    transition: NDArray[np.float64]
    initial: NDArray[np.float64]

    @classmethod
    def empty(cls, pseudocount: float = 0.5) -> "ModelCounts":
        if pseudocount <= 0.0:
            raise ValueError("pseudocount must be positive")
        return cls(
            likelihood=tuple(
                np.full((size, N_STATES), pseudocount, dtype=np.float64)
                for size in OBSERVATION_SIZES
            ),
            transition=np.full(
                (N_STATES, N_STATES, N_ACTIONS), pseudocount, dtype=np.float64
            ),
            initial=np.full(N_STATES, pseudocount, dtype=np.float64),
        )

    def copy(self) -> "ModelCounts":
        return ModelCounts(
            tuple(value.copy() for value in self.likelihood),
            self.transition.copy(),
            self.initial.copy(),
        )

    def add_initial(self, state: int, observation: tuple[int, ...]) -> None:
        self.initial[int(state)] += 1.0
        self._add_observation(state, observation)

    def add_transition(
        self,
        previous_state: int,
        action: int,
        next_state: int,
        observation: tuple[int, ...],
    ) -> None:
        self.transition[int(next_state), int(previous_state), int(action)] += 1.0
        self._add_observation(next_state, observation)

    def _add_observation(self, state: int, observation: tuple[int, ...]) -> None:
        if len(observation) != len(OBSERVATION_SIZES):
            raise ValueError("observation has the wrong number of modalities")
        for counts, category, size in zip(
            self.likelihood, observation, OBSERVATION_SIZES, strict=True
        ):
            if not 0 <= int(category) < size:
                raise ValueError("observation category is outside its alphabet")
            counts[int(category), int(state)] += 1.0

    def merge(self, other: "ModelCounts") -> "ModelCounts":
        return ModelCounts(
            tuple(
                left + right - 0.5
                for left, right in zip(self.likelihood, other.likelihood, strict=True)
            ),
            self.transition + other.transition - 0.5,
            self.initial + other.initial - 0.5,
        )

    def to_arrays(self) -> dict[str, NDArray[np.float64]]:
        output = {
            f"likelihood_{index}": value
            for index, value in enumerate(self.likelihood)
        }
        output["transition"] = self.transition
        output["initial"] = self.initial
        return output

    @classmethod
    def from_arrays(cls, arrays: dict[str, NDArray]) -> "ModelCounts":
        return cls(
            tuple(
                np.asarray(arrays[f"likelihood_{index}"], dtype=np.float64).copy()
                for index in range(len(OBSERVATION_SIZES))
            ),
            np.asarray(arrays["transition"], dtype=np.float64).copy(),
            np.asarray(arrays["initial"], dtype=np.float64).copy(),
        )


def _normalize(values: NDArray[np.float64], axis: int) -> NDArray[np.float64]:
    array = np.asarray(values, dtype=np.float64)
    totals = array.sum(axis=axis, keepdims=True)
    if np.any(totals <= 0.0):
        raise ValueError("cannot normalize empty counts")
    return array / totals


def policy_array(horizon: int = 2) -> NDArray[np.int64]:
    return np.asarray(list(product(range(N_ACTIONS), repeat=horizon)), dtype=np.int64)


def model_from_counts(
    counts: ModelCounts,
    config: ExperimentConfig,
    *,
    information_gain: bool = True,
) -> CategoricalModel:
    preferences = (
        np.asarray((0.50, 0.20, -0.50, -4.00), dtype=np.float64),
        np.zeros(3, dtype=np.float64),
        np.zeros(3, dtype=np.float64),
        np.zeros(4, dtype=np.float64),
    )
    model = CategoricalModel(
        A=tuple(_normalize(value, axis=0) for value in counts.likelihood),
        B=_normalize(counts.transition, axis=0),
        C=preferences,
        D=_normalize(counts.initial, axis=0),
        policies=policy_array(config.policy_horizon),
        gamma=16.0,
        policy_prior=np.full(16, 1.0 / 16.0, dtype=np.float64),
        use_utility=True,
        use_states_info_gain=information_gain,
        labels={
            "state": tuple(
                f"{regime}-{alignment}"
                for regime in ("A", "B", "shock")
                for alignment in ("low", "medium", "high")
            ),
            "action": ("wait", "adapt_a", "adapt_b", "sample"),
        },
    )
    model.validate()
    return model


def prior_counts_from_model(
    model: CategoricalModel, concentration: float = 4.0
) -> ModelCounts:
    """Turn a pooled model into a weak Dirichlet prior for local calibration."""

    if concentration <= 0.0:
        raise ValueError("local prior concentration must be positive")
    return ModelCounts(
        likelihood=tuple(
            0.5 + concentration * np.asarray(value, dtype=np.float64)
            for value in model.A
        ),
        transition=0.5 + concentration * np.asarray(model.B, dtype=np.float64),
        initial=0.5 + concentration * np.asarray(model.D, dtype=np.float64),
    )


def model_to_arrays(model: CategoricalModel) -> dict[str, NDArray]:
    output: dict[str, NDArray] = {
        "B": model.B,
        "D": model.D,
        "policies": model.policies,
        "gamma": np.asarray((model.gamma,), dtype=np.float64),
        "use_utility": np.asarray((int(model.use_utility),), dtype=np.int8),
        "use_states_info_gain": np.asarray(
            (int(model.use_states_info_gain),), dtype=np.int8
        ),
    }
    for index, value in enumerate(model.A):
        output[f"A_{index}"] = value
    for index, value in enumerate(model.C):
        output[f"C_{index}"] = value
    if model.policy_prior is not None:
        output["policy_prior"] = model.policy_prior
    return output


def model_from_arrays(arrays: dict[str, NDArray]) -> CategoricalModel:
    model = CategoricalModel(
        A=tuple(
            np.asarray(arrays[f"A_{index}"], dtype=np.float64).copy()
            for index in range(len(OBSERVATION_SIZES))
        ),
        B=np.asarray(arrays["B"], dtype=np.float64).copy(),
        C=tuple(
            np.asarray(arrays[f"C_{index}"], dtype=np.float64).copy()
            for index in range(len(OBSERVATION_SIZES))
        ),
        D=np.asarray(arrays["D"], dtype=np.float64).copy(),
        policies=np.asarray(arrays["policies"], dtype=np.int64).copy(),
        gamma=float(np.asarray(arrays["gamma"])[0]),
        policy_prior=np.asarray(arrays["policy_prior"], dtype=np.float64).copy(),
        use_utility=bool(np.asarray(arrays["use_utility"])[0]),
        use_states_info_gain=bool(np.asarray(arrays["use_states_info_gain"])[0]),
    )
    model.validate()
    return model


def save_model(path: Path, model: CategoricalModel, counts: ModelCounts) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {f"model__{key}": value for key, value in model_to_arrays(model).items()}
    arrays.update({f"counts__{key}": value for key, value in counts.to_arrays().items()})
    temporary = path.with_name(f".{path.name}.tmp.npz")
    np.savez(temporary, **arrays)
    temporary.replace(path)


def load_model(path: Path) -> tuple[CategoricalModel, ModelCounts]:
    with np.load(path, allow_pickle=False) as archive:
        model_values = {
            name.removeprefix("model__"): archive[name].copy()
            for name in archive.files
            if name.startswith("model__")
        }
        count_values = {
            name.removeprefix("counts__"): archive[name].copy()
            for name in archive.files
            if name.startswith("counts__")
        }
    return model_from_arrays(model_values), ModelCounts.from_arrays(count_values)


def action_costs(config: ExperimentConfig) -> NDArray[np.float64]:
    return np.asarray(
        (0.0, config.action_cost_adapt, config.action_cost_adapt, config.action_cost_sample),
        dtype=np.float64,
    )


def adjust_policy_costs(
    model: CategoricalModel,
    result: PolicyResult,
    config: ExperimentConfig,
) -> PolicyResult:
    costs = action_costs(config)
    policy_cost = costs[model.policies].sum(axis=1)
    adjusted = np.asarray(result.neg_efe, dtype=np.float64) - policy_cost
    prior = (
        model.policy_prior
        if model.policy_prior is not None
        else np.full(len(model.policies), 1.0 / len(model.policies))
    )
    posterior = softmax(
        model.gamma * adjusted + np.log(np.maximum(prior, np.finfo(float).tiny))
    )
    return PolicyResult(
        policies=result.policies.copy(),
        expected_utility=result.expected_utility.copy(),
        state_info_gain=result.state_info_gain.copy(),
        neg_efe=adjusted,
        posterior=posterior,
    )


def reward_only(model: CategoricalModel) -> CategoricalModel:
    result = replace(model, use_states_info_gain=False)
    result.validate()
    return result


def reversed_preferences(model: CategoricalModel) -> CategoricalModel:
    preferences = list(model.C)
    preferences[0] = -preferences[0]
    result = replace(model, C=tuple(preferences))
    result.validate()
    return result


def scrambled_model(model: CategoricalModel, seed: int) -> CategoricalModel:
    permutation = np.random.default_rng(seed).permutation(model.n_states)
    likelihood = tuple(value[:, permutation].copy() for value in model.A)
    result = replace(model, A=likelihood)
    result.validate()
    return result


def model_digest(model: CategoricalModel) -> str:
    chunks: list[bytes] = []
    for name, value in sorted(model_to_arrays(model).items()):
        array = np.ascontiguousarray(value)
        chunks.extend((name.encode(), str(array.shape).encode(), array.dtype.str.encode(), array.tobytes()))
    return sha256_bytes(b"".join(chunks))
