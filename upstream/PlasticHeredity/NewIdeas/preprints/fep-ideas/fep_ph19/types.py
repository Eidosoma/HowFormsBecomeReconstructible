from __future__ import annotations

from enum import StrEnum

from fep_ph18.types import (
    Action,
    ActionChannel,
    ActuatorSetting,
    CellSpec,
    ChallengeTier,
    ConditionSpec,
    EnvironmentFamily,
    ExperimentStage,
    InformationArm,
    ObservationThresholds,
    SenseDecision,
    SensingTiming,
)


class ControllerName(StrEnum):
    NOOP = "noop"
    REACTIVE = "passive_cue_reactive"
    TRUE_REGIME_ORACLE = "true_regime_oracle"
    ALWAYS_SENSE = "always_sense_cue_map_reflex"
    EXACT_UTILITY = "exact_pomdp_pragmatic"
    EXACT_EFE = "exact_pomdp_efe_selective"
    EXACT_LESION = "exact_pomdp_sensing_lesion"
    ENTROPY_HEURISTIC = "entropy_threshold_sensing"
    SENSING_YOKE = "sensing_count_timing_yoke"
    LEGACY_PH18 = "frozen_ph18_contingent_efe"
    RECURRENT_UTILITY = "recurrent_pragmatic"
    RECURRENT_EFE = "recurrent_efe_selective"


CORE_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.NOOP,
    ControllerName.REACTIVE,
    ControllerName.TRUE_REGIME_ORACLE,
    ControllerName.ALWAYS_SENSE,
    ControllerName.EXACT_UTILITY,
    ControllerName.EXACT_EFE,
    ControllerName.EXACT_LESION,
    ControllerName.ENTROPY_HEURISTIC,
    ControllerName.SENSING_YOKE,
    ControllerName.LEGACY_PH18,
)


def stage_b_controllers(recurrent_qualified: bool) -> tuple[ControllerName, ...]:
    if not recurrent_qualified:
        return CORE_CONTROLLERS
    return CORE_CONTROLLERS + (
        ControllerName.RECURRENT_UTILITY,
        ControllerName.RECURRENT_EFE,
    )


STAGE_A_CONTROLLERS: tuple[ControllerName, ...] = (
    ControllerName.NOOP,
    ControllerName.REACTIVE,
    ControllerName.TRUE_REGIME_ORACLE,
    ControllerName.ALWAYS_SENSE,
)


__all__ = (
    "Action",
    "ActionChannel",
    "ActuatorSetting",
    "CellSpec",
    "ChallengeTier",
    "ConditionSpec",
    "ControllerName",
    "CORE_CONTROLLERS",
    "EnvironmentFamily",
    "ExperimentStage",
    "InformationArm",
    "ObservationThresholds",
    "SenseDecision",
    "SensingTiming",
    "STAGE_A_CONTROLLERS",
    "stage_b_controllers",
)

