from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray


class EnvironmentFamily(StrEnum):
    NUTRIENT = "nutrient"
    CATALYTIC = "catalytic"


class ActionChannel(StrEnum):
    UPTAKE = "uptake"
    MOLECULAR = "molecular"


class KnowledgeMode(StrEnum):
    POOLED = "pooled"
    LOCAL = "local"


class Action(IntEnum):
    WAIT = 0
    ADAPT_A = 1
    ADAPT_B = 2
    SAMPLE = 3


class ExternalRegime(IntEnum):
    A = 0
    B = 1
    SHOCK = 2


class AlignmentLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class ControllerName(StrEnum):
    AI_POOLED = "ai_pooled"
    REWARD_POOLED = "reward_only_pooled"
    RANDOM_POOLED = "yoked_random_pooled"
    AI_LOCAL = "ai_local"
    REWARD_LOCAL = "reward_only_local"
    RANDOM_LOCAL = "yoked_random_local"
    REACTIVE = "reactive"
    NOOP = "noop"
    ORACLE = "oracle"
    SCRAMBLED = "scrambled_model_pooled"
    SENSORY_LESION = "sensory_lesion_pooled"
    ACTION_LESION = "action_lesion_pooled"
    REVERSED = "reversed_preferences_pooled"


CORE_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.AI_POOLED,
    ControllerName.REWARD_POOLED,
    ControllerName.RANDOM_POOLED,
    ControllerName.AI_LOCAL,
    ControllerName.REWARD_LOCAL,
    ControllerName.RANDOM_LOCAL,
    ControllerName.REACTIVE,
    ControllerName.NOOP,
    ControllerName.ORACLE,
)

DIAGNOSTIC_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.SCRAMBLED,
    ControllerName.SENSORY_LESION,
    ControllerName.ACTION_LESION,
    ControllerName.REVERSED,
)


@dataclass(frozen=True)
class RegimeSpec:
    severity_index: int
    volatility: str
    switch_probability: float
    shock_probability: float
    nutrient_contrast: float
    shock_supply_multiplier: float
    catalytic_morph: float
    catalytic_shock_morph: float

    @property
    def key(self) -> str:
        return f"s{self.severity_index}-{self.volatility}"


@dataclass(frozen=True)
class ObservationThresholds:
    alignment: tuple[float, float] = (1.0 / 3.0, 2.0 / 3.0)
    growth: tuple[float, float] = (100.0, 300.0)

    def validate(self) -> None:
        if not self.alignment[0] < self.alignment[1]:
            raise ValueError("alignment thresholds must be increasing")
        if not 0.0 < self.growth[0] < self.growth[1]:
            raise ValueError("growth thresholds must be positive and increasing")


@dataclass(frozen=True)
class RawObservation:
    growth_steps: int
    boundary_similarity: float
    alignment_score: float
    cue: int
    terminal: bool


@dataclass(frozen=True)
class GardStep:
    composition: NDArray[np.int64]
    parent: NDArray[np.int64] | None
    raw_observation: RawObservation
    external_regime: int
    alignment_level: int
    intended_action: int
    executed_action: int
    abstract_action_cost: float
    physical_action_cost: float
    completed: bool
    edit_remove: int = -1
    edit_add: int = -1


@dataclass(frozen=True)
class ControllerDecision:
    intended_action: int
    posterior: NDArray[np.float64]
    predictive_prior: NDArray[np.float64]
    vfe: float
    log_evidence: float
    expected_utility: NDArray[np.float64]
    state_information_gain: NDArray[np.float64]
    adjusted_neg_efe: NDArray[np.float64]
    policy_posterior: NDArray[np.float64]


class Controller(Protocol):
    def reset(self) -> None: ...

    def decide(
        self,
        observation: tuple[int, ...],
        true_regime: int | None,
        rng: np.random.Generator,
    ) -> ControllerDecision: ...

    def advance(self, posterior: NDArray[np.float64], executed_action: int) -> None: ...


def json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (EnvironmentFamily, ActionChannel, KnowledgeMode, ControllerName)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_ready(item) for item in value]
    return value

