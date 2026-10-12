from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import read_json
from fep_lab.seeds import derive_seed
from fep_ph1.gard import generate_beta, generate_initial_composition
from fep_ph15.types import ActuatorSetting, ChallengeSelection
from fep_ph18.causal_model import transition_target
from fep_ph18.environment import EnvironmentDesign, GardGoalAlignmentEnvironment
from fep_ph18.state import (
    advance_body_state,
    cue_probabilities,
    initial_body_state,
    initial_regime_belief,
    state_features,
    update_regime_belief,
)
from fep_ph18.config import regime_spec

from .config import (
    DELAYED_CONTROL_PROBABILITY,
    MECHANISM_KEYS,
    MODEL_ACTIONS,
    SWITCH_PROBABILITIES,
    ExperimentConfig,
)
from .types import (
    Action,
    ActionChannel,
    ChallengeTier,
    ConditionSpec,
    EnvironmentFamily,
    ExperimentStage,
    InformationArm,
    ObservationThresholds,
    SensingTiming,
)


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph19.{domain}", *parts)


def cohort_seed_domains(config: ExperimentConfig) -> dict[str, int]:
    names = (
        "development",
        "timing",
        "stage-a",
        "stage-a-agent",
        "stage-b",
        "stage-b-agent",
        "stage-b-yoked",
        "bootstrap-stage-a",
        "bootstrap-stage-b",
    )
    return {name: _seed(config, f"{name}.fixture", "disjointness") for name in names}


def beta_for(
    config: ExperimentConfig, cohort: str, matrix_id: int
) -> NDArray[np.float64]:
    return generate_beta(
        config.gard,
        np.random.default_rng(_seed(config, f"{cohort}.beta", matrix_id)),
    )


def initial_for(
    config: ExperimentConfig,
    cohort: str,
    matrix_id: int,
    condition: ConditionSpec,
    episode: int,
    branch: int = 0,
) -> NDArray[np.int64]:
    key = condition.paired_exogenous_key if cohort == "stage-b" else condition.key
    return generate_initial_composition(
        config.gard,
        np.random.default_rng(
            _seed(config, f"{cohort}.initial", matrix_id, key, episode, branch)
        ),
    )


def process_seeds(
    config: ExperimentConfig,
    cohort: str,
    condition: ConditionSpec,
    matrix_id: int,
    episode: int,
    branch: int = 0,
) -> tuple[int, int, int]:
    key = condition.paired_exogenous_key if cohort == "stage-b" else condition.key
    return tuple(
        _seed(
            config,
            f"{cohort}.{kind}",
            key,
            matrix_id,
            episode,
            branch,
        )
        for kind in ("chemistry", "environment", "observation")
    )  # type: ignore[return-value]


def environment_design(
    config: ExperimentConfig,
    condition: ConditionSpec,
    matrix_id: int,
    cohort: str,
) -> EnvironmentDesign:
    return EnvironmentDesign(
        condition.family,
        condition.channel,
        regime_spec(condition.switch_probability),
        condition.candidate,
        _seed(config, f"{cohort}.design.partition", condition.family, matrix_id),
        _seed(config, f"{cohort}.design.permutation", condition.family, matrix_id),
        condition.growth_budget,
        condition.actuator,
        condition.authority_scale,
        condition.information_arm,
        condition.sensing_timing,
    )


def _screen_decisions(
    screen_root: Path,
) -> dict[str, tuple[ChallengeSelection, ActuatorSetting, dict[str, Any]]]:
    decisions: dict[str, tuple[ChallengeSelection, ActuatorSetting, dict[str, Any]]] = {}
    for path in sorted((Path(screen_root) / "cells").glob("*.json")):
        payload = read_json(path)
        key = f"c{payload['candidate']}--{payload['family']}--{payload['channel']}"
        if key in MECHANISM_KEYS:
            decisions[key] = (
                ChallengeSelection(**payload["challenge"]),
                ActuatorSetting(**payload["actuator"]),
                payload,
            )
    if tuple(sorted(decisions)) != tuple(sorted(MECHANISM_KEYS)):
        raise RuntimeError("the sealed FEP–PH1.5 screen lacks a PH1.9 mechanism")
    return decisions


def _condition(
    decision: tuple[ChallengeSelection, ActuatorSetting, dict[str, Any]],
    *,
    stage: ExperimentStage,
    switch: float,
    timing: SensingTiming,
    information: InformationArm,
) -> ConditionSpec:
    challenge, actuator, payload = decision
    return ConditionSpec(
        stage=stage,
        candidate=str(payload["candidate"]),
        family=EnvironmentFamily(str(payload["family"])),
        channel=ActionChannel(str(payload["channel"])),
        tier=ChallengeTier.HARD,
        switch_probability=float(switch),
        growth_budget=challenge.hard_budget,
        actuator=actuator,
        authority_scale=1.0,
        sensing_timing=timing,
        information_arm=information,
    )


def development_conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
    decisions = _screen_decisions(screen_root)
    return tuple(
        _condition(
            decisions[key],
            stage=ExperimentStage.INFORMATION,
            switch=switch,
            timing=timing,
            information=InformationArm.INFORMATIVE,
        )
        for key in MECHANISM_KEYS
        for switch in SWITCH_PROBABILITIES
        for timing in (SensingTiming.DELAYED, SensingTiming.SAME_CYCLE)
    )


def stage_a_conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
    decisions = _screen_decisions(screen_root)
    return tuple(
        _condition(
            decisions[key],
            stage=ExperimentStage.HEADROOM,
            switch=switch,
            timing=SensingTiming.SAME_CYCLE,
            information=InformationArm.NONE,
        )
        for key in MECHANISM_KEYS
        for switch in SWITCH_PROBABILITIES
    )


def stage_b_conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
    decisions = _screen_decisions(screen_root)
    primary = [
        _condition(
            decisions[key],
            stage=ExperimentStage.INFORMATION,
            switch=switch,
            timing=SensingTiming.SAME_CYCLE,
            information=information,
        )
        for key in MECHANISM_KEYS
        for switch in SWITCH_PROBABILITIES
        for information in (InformationArm.INFORMATIVE, InformationArm.SHAM)
    ]
    delayed = [
        _condition(
            decisions[key],
            stage=ExperimentStage.INFORMATION,
            switch=DELAYED_CONTROL_PROBABILITY,
            timing=SensingTiming.DELAYED,
            information=information,
        )
        for key in MECHANISM_KEYS
        for information in (InformationArm.INFORMATIVE, InformationArm.SHAM)
    ]
    output = tuple(primary + delayed)
    if len(output) != 16:
        raise RuntimeError("FEP–PH1.9 evaluation factorial must contain 16 conditions")
    return output


def _balanced_actions(
    config: ExperimentConfig,
    cohort: str,
    condition: ConditionSpec,
    matrix_id: int,
    episode: int,
    steps: int,
) -> NDArray[np.int8]:
    alphabet = np.asarray(
        (0, 1, 2, 3)
        if condition.sensing_timing == SensingTiming.DELAYED
        else (0, 1, 2, 4, 5, 6),
        dtype=np.int8,
    )
    order = np.random.default_rng(
        _seed(config, f"{cohort}.action-cycle", condition.key, matrix_id, episode)
    ).permutation(alphabet)
    return np.asarray([order[index % len(order)] for index in range(steps)], dtype=np.int8)


def cue_accuracy(
    config: ExperimentConfig, condition: ConditionSpec, action: int
) -> float:
    sampled = int(action) in (int(Action.SAMPLE), 4, 5, 6)
    if condition.information_arm == InformationArm.NONE:
        return config.stage_a_sample_accuracy if sampled else config.stage_a_passive_cue_accuracy
    if not sampled:
        return config.passive_cue_accuracy
    return (
        config.informative_sample_accuracy
        if condition.information_arm == InformationArm.INFORMATIVE
        else config.sham_sample_accuracy
    )


def collect_transitions(
    config: ExperimentConfig,
    condition: ConditionSpec,
    *,
    cohort: str,
    matrix_ids: Iterable[int],
    episodes: int,
    steps: int,
) -> dict[str, NDArray[Any]]:
    rows: dict[str, list[Any]] = {
        name: []
        for name in (
            "matrix_id",
            "episode",
            "step",
            "action",
            "coarse_features",
            "rich_features",
            "coarse_targets",
            "rich_targets",
            "current_regime",
            "next_regime",
            "current_growth",
            "current_similarity",
            "current_alignment",
            "current_cue",
            "next_growth",
            "next_similarity",
            "next_alignment",
            "next_cue",
            "completed",
        )
    }
    regime = regime_spec(condition.switch_probability)
    for matrix_id in matrix_ids:
        beta = beta_for(config, cohort, matrix_id)
        design = environment_design(config, condition, matrix_id, cohort)
        for episode in range(episodes):
            environment = GardGoalAlignmentEnvironment(
                config,
                design,
                beta,
                initial_for(config, cohort, matrix_id, condition, episode),
                *process_seeds(config, cohort, condition, matrix_id, episode),
                thresholds=ObservationThresholds(),
            )
            first = environment.initial_step()
            belief = update_regime_belief(
                initial_regime_belief(),
                first.raw_observation.cue,
                regime.switch_probability,
                regime.shock_probability,
                cue_accuracy(config, condition, int(Action.WAIT)),
                transition=False,
            )
            state = initial_body_state(first.composition, first.raw_observation, belief)
            actions = _balanced_actions(config, cohort, condition, matrix_id, episode, steps)
            current_regime = int(environment.regime)
            current_raw = first.raw_observation
            for step, action_value in enumerate(actions):
                model_action = int(action_value)
                sensed_cue = -1
                if model_action >= 4:
                    sensed_cue = int(environment.sense_current())
                    decision_belief = update_regime_belief(
                        state.regime_belief,
                        sensed_cue,
                        regime.switch_probability,
                        regime.shock_probability,
                        cue_accuracy(config, condition, model_action),
                        transition=False,
                    )
                    decision_state = replace(
                        state,
                        regime_belief=decision_belief,
                        cue_probs=cue_probabilities(sensed_cue),
                    )
                    physical_action = model_action - 4
                    result = environment.step_compound(physical_action, sensed=True)
                    result_accuracy = config.passive_cue_accuracy
                else:
                    decision_belief = state.regime_belief
                    decision_state = state
                    physical_action = model_action
                    result = environment.step(physical_action)
                    result_accuracy = cue_accuracy(config, condition, model_action)
                following_belief = update_regime_belief(
                    decision_belief,
                    result.raw_observation.cue,
                    regime.switch_probability,
                    regime.shock_probability,
                    result_accuracy,
                )
                values = {
                    "matrix_id": matrix_id,
                    "episode": episode,
                    "step": step,
                    "action": model_action,
                    "coarse_features": state_features(decision_state, condition, rich=False),
                    "rich_features": state_features(decision_state, condition, rich=True),
                    "coarse_targets": transition_target(
                        result.composition,
                        result.raw_observation,
                        result.completed,
                        result.external_regime,
                        condition.growth_budget,
                        rich=False,
                    ),
                    "rich_targets": transition_target(
                        result.composition,
                        result.raw_observation,
                        result.completed,
                        result.external_regime,
                        condition.growth_budget,
                        rich=True,
                    ),
                    "current_regime": current_regime,
                    "next_regime": int(result.external_regime),
                    "current_growth": current_raw.growth_steps,
                    "current_similarity": current_raw.boundary_similarity,
                    "current_alignment": current_raw.alignment_score,
                    "current_cue": sensed_cue if model_action >= 4 else current_raw.cue,
                    "next_growth": result.raw_observation.growth_steps,
                    "next_similarity": result.raw_observation.boundary_similarity,
                    "next_alignment": result.raw_observation.alignment_score,
                    "next_cue": result.raw_observation.cue,
                    "completed": int(result.completed),
                }
                for name, value in values.items():
                    rows[name].append(value)
                if not result.completed:
                    break
                state = advance_body_state(
                    decision_state,
                    result.composition,
                    result.raw_observation,
                    following_belief,
                    physical_action,
                    condition.growth_budget,
                )
                current_regime = int(result.external_regime)
                current_raw = result.raw_observation
    if not rows["action"]:
        raise RuntimeError(f"no transitions for {condition.key}")
    float_names = {
        "coarse_features",
        "rich_features",
        "coarse_targets",
        "rich_targets",
        "current_similarity",
        "current_alignment",
        "next_similarity",
        "next_alignment",
    }
    int32_names = {"matrix_id", "current_growth", "next_growth"}
    return {
        name: np.asarray(
            values,
            dtype=np.float64
            if name in float_names
            else np.int32
            if name in int32_names
            else np.int16,
        )
        for name, values in rows.items()
    }


def development_cell(
    config: ExperimentConfig, condition: ConditionSpec
) -> tuple[dict[str, NDArray[Any]], dict[str, Any]]:
    arrays = collect_transitions(
        config,
        condition,
        cohort="development",
        matrix_ids=range(config.development_matrices),
        episodes=config.development_episodes,
        steps=config.development_steps,
    )
    metadata = {
        "schema": "fep-ph19-development-cell-v1",
        "condition": condition.key,
        "candidate": condition.candidate,
        "switch_probability": condition.switch_probability,
        "sensing_timing": str(condition.sensing_timing),
        "growth_budget": condition.growth_budget,
        "rows": int(len(arrays["action"])),
        "matrices": config.development_matrices,
        "episodes": config.development_episodes,
        "steps": config.development_steps,
        "action_counts": {
            str(action): int(np.count_nonzero(arrays["action"] == action))
            for action in range(MODEL_ACTIONS)
        },
        "true_regime_is_development_qualification_only": True,
        "runtime_feature_firewall": [
            "true_regime",
            "beta",
            "rng_state",
            "future_outcomes",
            "f12",
            "strict8",
        ],
    }
    return arrays, metadata


__all__ = (
    "beta_for",
    "cohort_seed_domains",
    "cue_accuracy",
    "development_cell",
    "development_conditions",
    "environment_design",
    "initial_for",
    "process_seeds",
    "stage_a_conditions",
    "stage_b_conditions",
)
