from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from fep_ph15.types import (
    Action, ActionChannel, ActuatorSetting, ChallengeTier,
    EnvironmentFamily, ObservationThresholds,
)


class ExperimentStage(StrEnum):
    HEADROOM = "stage-a"
    INFORMATION = "stage-b"


class InformationArm(StrEnum):
    NONE = "none"
    INFORMATIVE = "informative"
    SHAM = "sham"


class SensingTiming(StrEnum):
    DELAYED = "delayed"
    SAME_CYCLE = "same-cycle"


class SenseDecision(IntEnum):
    NO_SENSE = 0
    SENSE = 1


class ControllerName(StrEnum):
    NOOP = "noop"
    REACTIVE = "passive_cue_reactive"
    TRUE_REGIME_ORACLE = "true_regime_oracle"
    POSTERIOR_REFLEX = "posterior_map_reflex"
    ALWAYS_SENSE = "always_sense_cue_map_reflex"
    CONTINGENT_UTILITY = "contingent_utility_planner"
    CONTINGENT_EFE = "contingent_efe_planner"
    OPEN_LOOP_EFE = "open_loop_efe_bonus_planner"
    SAMPLE_LESION = "contingent_efe_sample_lesion"
    SHUFFLED = "contingent_efe_shuffled_actions"


STAGE_A_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.NOOP, ControllerName.REACTIVE, ControllerName.TRUE_REGIME_ORACLE,
)
STAGE_B_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.NOOP, ControllerName.REACTIVE, ControllerName.TRUE_REGIME_ORACLE,
    ControllerName.POSTERIOR_REFLEX, ControllerName.ALWAYS_SENSE,
    ControllerName.CONTINGENT_UTILITY, ControllerName.CONTINGENT_EFE,
    ControllerName.OPEN_LOOP_EFE, ControllerName.SAMPLE_LESION,
    ControllerName.SHUFFLED,
)


@dataclass(frozen=True)
class ConditionSpec:
    stage: ExperimentStage
    candidate: str
    family: EnvironmentFamily
    channel: ActionChannel
    tier: ChallengeTier
    switch_probability: float
    growth_budget: int
    actuator: ActuatorSetting
    authority_scale: float
    sensing_timing: SensingTiming = SensingTiming.DELAYED
    information_arm: InformationArm = InformationArm.NONE

    @property
    def volatility(self) -> str:
        return f"p{self.switch_probability:.2f}".replace(".", "p")

    @property
    def mechanism_key(self) -> str:
        return f"c{self.candidate}--{self.family}--{self.channel}"

    @property
    def key(self) -> str:
        authority = f"a{self.authority_scale:.1f}".replace(".", "p")
        return (
            f"{self.stage}--{self.mechanism_key}--{self.tier}--{self.volatility}--"
            f"{authority}--{self.sensing_timing}--{self.information_arm}"
        )

    @property
    def paired_information_key(self) -> str:
        return self.paired_exogenous_key

    @property
    def paired_exogenous_key(self) -> str:
        authority = f"a{self.authority_scale:.1f}".replace(".", "p")
        return (
            f"{self.stage}--{self.mechanism_key}--{self.tier}--{self.volatility}--"
            f"{authority}--paired-timing-information"
        )


@dataclass(frozen=True)
class CellSpec:
    matrix_id: int
    condition: ConditionSpec

    @property
    def stem(self) -> str:
        return f"m{self.matrix_id:04d}--{self.condition.key}"


__all__ = (
    "Action", "ActionChannel", "ActuatorSetting", "CellSpec", "ChallengeTier",
    "ConditionSpec", "ControllerName", "EnvironmentFamily", "ExperimentStage",
    "InformationArm", "ObservationThresholds", "SenseDecision", "SensingTiming",
    "STAGE_A_CONTROLLERS", "STAGE_B_CONTROLLERS",
)
