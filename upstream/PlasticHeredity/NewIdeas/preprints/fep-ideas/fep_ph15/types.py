from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np

from fep_ph1.types import (
    Action,
    ActionChannel,
    AlignmentLevel,
    ControllerDecision,
    EnvironmentFamily,
    ExternalRegime,
    GardStep,
    ObservationThresholds,
    RawObservation,
)


class ChallengeTier(StrEnum):
    TRANSITION = "transition"
    HARD = "hard"


class PreferenceMode(StrEnum):
    BALANCED = "balanced"
    GROWTH = "growth"


class ControllerName(StrEnum):
    BALANCED_AI_LOCAL = "balanced_ai_local"
    BALANCED_REWARD_LOCAL = "balanced_reward_local"
    BALANCED_YOKED_LOCAL = "balanced_yoked_random_local"
    GROWTH_AI_LOCAL = "growth_ai_local"
    GROWTH_REWARD_LOCAL = "growth_reward_local"
    BALANCED_AI_POOLED = "balanced_ai_pooled"
    BALANCED_REWARD_POOLED = "balanced_reward_pooled"
    REACTIVE = "reactive"
    NOOP = "noop"
    ORACLE_BALANCED = "true_regime_balanced_oracle"
    SCRAMBLED_LOCAL = "balanced_local_scrambled_likelihood"
    SENSORY_LESION = "balanced_local_sensory_lesion"
    ACTION_LESION = "balanced_local_action_lesion"


CORE_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.BALANCED_AI_LOCAL,
    ControllerName.BALANCED_REWARD_LOCAL,
    ControllerName.BALANCED_YOKED_LOCAL,
    ControllerName.GROWTH_AI_LOCAL,
    ControllerName.GROWTH_REWARD_LOCAL,
    ControllerName.BALANCED_AI_POOLED,
    ControllerName.BALANCED_REWARD_POOLED,
    ControllerName.REACTIVE,
    ControllerName.NOOP,
    ControllerName.ORACLE_BALANCED,
)

HARD_DIAGNOSTIC_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.SCRAMBLED_LOCAL,
    ControllerName.SENSORY_LESION,
    ControllerName.ACTION_LESION,
)


@dataclass(frozen=True)
class ActuatorSetting:
    polarity: str
    molecular_dose: int
    actionability: str
    oracle_gain_transition: float
    oracle_gain_hard: float

    def validate(self) -> None:
        if self.polarity not in {"direct", "inverted"}:
            raise ValueError("actuator polarity must be direct or inverted")
        if self.molecular_dose not in {1, 2, 4, 8}:
            raise ValueError("molecular dose is outside the frozen screen")
        if self.actionability not in {"ACTIONABLE", "MIXED", "NON_ACTIONABLE"}:
            raise ValueError("unknown actionability label")


@dataclass(frozen=True)
class ChallengeSelection:
    transition_budget: int
    hard_budget: int
    transition_survival: float
    hard_survival: float

    def budget(self, tier: ChallengeTier) -> int:
        return self.hard_budget if tier == ChallengeTier.HARD else self.transition_budget

    def validate(self, allowed: tuple[int, ...]) -> None:
        if self.transition_budget == self.hard_budget:
            raise ValueError("challenge tiers must use distinct growth budgets")
        if self.transition_budget not in allowed or self.hard_budget not in allowed:
            raise ValueError("selected challenge budget is outside the frozen grid")


def json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, StrEnum):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_ready(item) for item in value]
    return value


__all__ = (
    "Action",
    "ActionChannel",
    "ActuatorSetting",
    "AlignmentLevel",
    "ChallengeSelection",
    "ChallengeTier",
    "ControllerDecision",
    "ControllerName",
    "CORE_CONTROLLERS",
    "EnvironmentFamily",
    "ExternalRegime",
    "GardStep",
    "HARD_DIAGNOSTIC_CONTROLLERS",
    "ObservationThresholds",
    "PreferenceMode",
    "RawObservation",
    "json_ready",
)

