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


class ExperimentStage(StrEnum):
    HEADROOM = "stage-a"
    INFORMATION = "stage-b"


class InformationArm(StrEnum):
    NONE = "none"
    INFORMATIVE = "informative"
    SHAM = "sham"


class ControllerName(StrEnum):
    NOOP = "noop"
    REACTIVE = "reactive"
    TRUE_REGIME_ORACLE = "true_regime_matched_action_oracle"
    LEGACY_PROXY_D3 = "legacy_proxy_physical_oracle_d3"
    GOAL_D3 = "goal_aligned_physical_oracle_d3"
    GOAL_D8 = "goal_aligned_physical_oracle_d8"
    PRAGMATIC = "hybrid_pragmatic_planner"
    ACTIVE_INFERENCE = "hybrid_active_inference_planner"
    SAMPLE_LESION = "hybrid_active_inference_sample_lesion"
    EFE_YOKED = "hybrid_active_inference_multiset_yoke"
    EFE_SHUFFLED = "hybrid_active_inference_shuffled_actions"


STAGE_A_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.NOOP,
    ControllerName.REACTIVE,
    ControllerName.TRUE_REGIME_ORACLE,
    ControllerName.LEGACY_PROXY_D3,
    ControllerName.GOAL_D3,
    ControllerName.GOAL_D8,
)

STAGE_B_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.NOOP,
    ControllerName.REACTIVE,
    ControllerName.TRUE_REGIME_ORACLE,
    ControllerName.PRAGMATIC,
    ControllerName.ACTIVE_INFERENCE,
    ControllerName.SAMPLE_LESION,
    ControllerName.EFE_YOKED,
    ControllerName.EFE_SHUFFLED,
)


@dataclass(frozen=True)
class ConditionSpec:
    stage: ExperimentStage
    candidate: str
    family: EnvironmentFamily
    channel: ActionChannel
    tier: ChallengeTier
    regime_index: int
    growth_budget: int
    actuator: ActuatorSetting
    authority_scale: float
    information_arm: InformationArm = InformationArm.NONE

    @property
    def volatility(self) -> str:
        return "slow" if self.regime_index == 0 else "fast"

    @property
    def mechanism_key(self) -> str:
        return f"c{self.candidate}--{self.family}--{self.channel}"

    @property
    def key(self) -> str:
        authority = f"a{self.authority_scale:.1f}".replace(".", "p")
        return (
            f"{self.stage}--{self.mechanism_key}--{self.tier}--"
            f"{self.volatility}--{authority}--{self.information_arm}"
        )

    @property
    def paired_information_key(self) -> str:
        """Common-random-number key for informative and sham evaluation arms."""

        if self.stage != ExperimentStage.INFORMATION:
            return self.key
        authority = f"a{self.authority_scale:.1f}".replace(".", "p")
        return (
            f"{self.stage}--{self.mechanism_key}--{self.tier}--"
            f"{self.volatility}--{authority}--paired-information"
        )


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
    "ControllerName",
    "EnvironmentFamily",
    "ExperimentStage",
    "InformationArm",
    "ObservationThresholds",
    "STAGE_A_CONTROLLERS",
    "STAGE_B_CONTROLLERS",
)
