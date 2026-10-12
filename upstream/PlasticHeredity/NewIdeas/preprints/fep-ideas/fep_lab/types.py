from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping, Protocol, Sequence

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class NutrientRegime(IntEnum):
    LEAN = 0
    RICH = 1


class Reservoir(IntEnum):
    DEPLETED = 0
    VIABLE = 1
    OVERLOADED = 2


class SensorMode(IntEnum):
    PASSIVE = 0
    SAMPLING = 1


class Action(IntEnum):
    WAIT = 0
    ADMIT = 1
    EXPEL = 2
    SAMPLE = 3


@dataclass(frozen=True)
class CategoricalModel:
    """Immutable discrete active-inference model in dense joint-state form."""

    A: tuple[FloatArray, ...]
    B: FloatArray
    C: tuple[FloatArray, ...]
    D: FloatArray
    policies: IntArray
    gamma: float = 16.0
    policy_prior: FloatArray | None = None
    use_utility: bool = True
    use_states_info_gain: bool = True
    labels: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def n_states(self) -> int:
        return int(self.D.shape[0])

    @property
    def n_actions(self) -> int:
        return int(self.B.shape[2])

    @property
    def horizon(self) -> int:
        return int(self.policies.shape[1])

    def validate(self, atol: float = 1e-12) -> None:
        if self.D.ndim != 1 or self.B.ndim != 3:
            raise ValueError("D must be one-dimensional and B must be three-dimensional")
        if self.B.shape[:2] != (self.n_states, self.n_states):
            raise ValueError("B must have shape (next_state, current_state, action)")
        if self.policies.ndim != 2:
            raise ValueError("policies must have shape (policy, horizon)")
        if np.any(self.policies < 0) or np.any(self.policies >= self.n_actions):
            raise ValueError("policy contains an invalid action")
        _validate_distribution(self.D, axis=0, name="D", atol=atol)
        _validate_distribution(self.B, axis=0, name="B", atol=atol)
        if len(self.A) != len(self.C):
            raise ValueError("A and C must contain the same observation modalities")
        for index, (likelihood, preference) in enumerate(zip(self.A, self.C)):
            if likelihood.ndim != 2 or likelihood.shape[1] != self.n_states:
                raise ValueError(f"A[{index}] has an incompatible state dimension")
            if preference.shape != (likelihood.shape[0],):
                raise ValueError(f"C[{index}] has an incompatible observation dimension")
            _validate_distribution(likelihood, axis=0, name=f"A[{index}]", atol=atol)
            if not np.all(np.isfinite(preference)):
                raise ValueError(f"C[{index}] contains a non-finite preference")
        prior = self.policy_prior
        if prior is not None:
            if prior.shape != (len(self.policies),):
                raise ValueError("policy_prior has an incompatible shape")
            _validate_distribution(prior, axis=0, name="policy_prior", atol=atol)
        if not np.isfinite(self.gamma) or self.gamma <= 0.0:
            raise ValueError("gamma must be finite and positive")


def _validate_distribution(
    values: FloatArray, axis: int, name: str, atol: float
) -> None:
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError(f"{name} must contain finite nonnegative probabilities")
    totals = np.sum(values, axis=axis)
    if not np.allclose(totals, 1.0, atol=atol, rtol=0.0):
        raise ValueError(f"{name} is not normalized along axis {axis}")


@dataclass(frozen=True)
class StepResult:
    observation: tuple[int, ...]
    state: int
    action_cost: float
    terminal: bool = False
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InferenceResult:
    posterior: FloatArray
    predictive_prior: FloatArray
    log_evidence: float
    vfe: float


@dataclass(frozen=True)
class PolicyResult:
    policies: IntArray
    expected_utility: FloatArray
    state_info_gain: FloatArray
    neg_efe: FloatArray
    posterior: FloatArray


@dataclass(frozen=True)
class EpisodeTrace:
    states: IntArray
    observations: IntArray
    beliefs: FloatArray
    predictive_priors: FloatArray
    vfe: FloatArray
    log_evidence: FloatArray
    expected_utility: FloatArray
    state_info_gain: FloatArray
    neg_efe: FloatArray
    policy_posterior: FloatArray
    intended_actions: IntArray
    executed_actions: IntArray
    action_costs: FloatArray


class Environment(Protocol):
    def reset(self, rng: np.random.Generator) -> StepResult: ...

    def step(
        self, state: int, action: int, rng: np.random.Generator
    ) -> StepResult: ...


class InferenceBackend(Protocol):
    name: str

    def infer_states(
        self,
        model: CategoricalModel,
        observation: Sequence[int],
        predictive_prior: FloatArray,
    ) -> InferenceResult: ...

    def score_policies(
        self, model: CategoricalModel, posterior: FloatArray
    ) -> PolicyResult: ...

    def sample_action(
        self,
        result: PolicyResult,
        n_actions: int,
        rng: np.random.Generator,
    ) -> int: ...
