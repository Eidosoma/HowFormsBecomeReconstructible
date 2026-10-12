from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fep_ph15.types import (
    Action,
    ActionChannel,
    ActuatorSetting,
    ChallengeTier,
    EnvironmentFamily,
    ObservationThresholds,
)


class ControllerName(StrEnum):
    NOOP = "noop"
    REACTIVE = "reactive"
    CATEGORICAL_AI = "categorical_ai_reference"
    CATEGORICAL_ORACLE = "true_regime_categorical_oracle"
    PHYSICAL_ORACLE = "full_state_rollout_oracle_d3"
    COARSE_REWARD = "coarse_causal_reward_mpc"
    RICH_REWARD = "rich_causal_reward_mpc"
    RICH_EFE = "rich_causal_efe_mpc"
    RICH_EFE_YOKED = "rich_causal_efe_yoked"
    RICH_EFE_SHUFFLED = "rich_causal_efe_shuffled_actions"


CONTROLLERS: tuple[ControllerName, ...] = tuple(ControllerName)


@dataclass(frozen=True)
class ConditionSpec:
    candidate: str
    family: EnvironmentFamily
    channel: ActionChannel
    tier: ChallengeTier
    regime_index: int
    growth_budget: int
    actuator: ActuatorSetting

    @property
    def volatility(self) -> str:
        return "slow" if self.regime_index == 0 else "fast"

    @property
    def mechanism_key(self) -> str:
        return f"c{self.candidate}--{self.family}--{self.channel}"

    @property
    def key(self) -> str:
        return f"{self.mechanism_key}--{self.tier}--{self.volatility}"


@dataclass(frozen=True)
class CellSpec:
    matrix_id: int
    condition: ConditionSpec

    @property
    def stem(self) -> str:
        return f"m{self.matrix_id:04d}--{self.condition.key}"


__all__ = (
    "Action",
    "ActionChannel",
    "ActuatorSetting",
    "CellSpec",
    "ChallengeTier",
    "ConditionSpec",
    "CONTROLLERS",
    "ControllerName",
    "EnvironmentFamily",
    "ObservationThresholds",
)
