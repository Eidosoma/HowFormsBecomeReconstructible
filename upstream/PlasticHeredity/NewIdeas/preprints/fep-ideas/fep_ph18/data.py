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

from .causal_model import TrainingData, transition_target
from .config import (
    CONFIRM_SWITCH_PROBABILITIES,
    MECHANISM_KEYS,
    MODEL_ACTIONS,
    SCREEN_SWITCH_PROBABILITIES,
    ExperimentConfig,
    regime_spec,
)
from .environment import EnvironmentDesign, GardGoalAlignmentEnvironment
from .state import (
    advance_body_state,
    cue_probabilities,
    initial_body_state,
    initial_regime_belief,
    state_features,
    update_regime_belief,
)
from .types import (
    Action,
    ActionChannel,
    CellSpec,
    ChallengeTier,
    ConditionSpec,
    EnvironmentFamily,
    ExperimentStage,
    InformationArm,
    ObservationThresholds,
    SensingTiming,
)


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph18.{domain}", *parts)


def cohort_seed_domains(config: ExperimentConfig) -> dict[str, int]:
    return {
        cohort: _seed(config, f"{cohort}.fixture", "disjointness")
        for cohort in (
            "development",
            "timing",
            "stage-a",
            "stage-a-planning",
            "stage-a-agent",
            "stage-b",
            "stage-b-agent",
            "stage-b-yoked",
            "bootstrap-stage-a",
            "bootstrap-stage-b",
        )
    }


def beta_for(config: ExperimentConfig, cohort: str, matrix_id: int) -> NDArray[np.float64]:
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
    condition_key = condition.paired_exogenous_key if cohort == "stage-b" else condition.key
    return generate_initial_composition(
        config.gard,
        np.random.default_rng(
            _seed(
                config,
                f"{cohort}.initial",
                matrix_id,
                condition_key,
                episode,
                branch,
            )
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
    condition_key = condition.paired_exogenous_key if cohort == "stage-b" else condition.key
    return tuple(
        _seed(
            config,
            f"{cohort}.{kind}",
            condition_key,
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
        if key not in MECHANISM_KEYS:
            continue
        decisions[key] = (
            ChallengeSelection(**payload["challenge"]),
            ActuatorSetting(**payload["actuator"]),
            payload,
        )
    if tuple(sorted(decisions)) != tuple(sorted(MECHANISM_KEYS)):
        raise RuntimeError(
            "sealed FEP-PH1.5 screen did not provide the frozen FEP-PH1.8 "
            f"mechanisms: {sorted(decisions)}"
        )
    return decisions


def _condition(
    decision: tuple[ChallengeSelection, ActuatorSetting, dict[str, Any]],
    *,
    stage: ExperimentStage,
    tier: ChallengeTier,
    switch_probability: float,
    timing: SensingTiming,
    information: InformationArm,
) -> ConditionSpec:
    challenge, actuator, payload = decision
    return ConditionSpec(
        stage=stage,
        candidate=str(payload["candidate"]),
        family=EnvironmentFamily(str(payload["family"])),
        channel=ActionChannel(str(payload["channel"])),
        tier=tier,
        switch_probability=float(switch_probability),
        growth_budget=challenge.budget(tier),
        actuator=actuator,
        authority_scale=1.0,
        sensing_timing=timing,
        information_arm=information,
    )


def stage_a_conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
    decisions = _screen_decisions(screen_root)
    output: list[ConditionSpec] = []
    for key in MECHANISM_KEYS:
        decision = decisions[key]
        for switch_probability in SCREEN_SWITCH_PROBABILITIES:
            output.append(
                _condition(
                    decision,
                    stage=ExperimentStage.HEADROOM,
                    tier=ChallengeTier.HARD,
                    switch_probability=switch_probability,
                    timing=SensingTiming.DELAYED,
                    information=InformationArm.NONE,
                )
            )
    if len(output) != 10:
        raise RuntimeError("FEP-PH1.8 Stage A factorial must contain ten conditions")
    return tuple(output)


def stage_b_conditions(
    screen_root: Path, authority: float = 1.0
) -> tuple[ConditionSpec, ...]:
    if float(authority) != 1.0:
        raise ValueError("FEP-PH1.8 freezes normal action authority")
    decisions = _screen_decisions(screen_root)
    output = tuple(
        _condition(
            decisions[key],
            stage=ExperimentStage.INFORMATION,
            tier=ChallengeTier.HARD,
            switch_probability=switch_probability,
            timing=timing,
            information=information,
        )
        for key in MECHANISM_KEYS
        for switch_probability in CONFIRM_SWITCH_PROBABILITIES
        for timing in (SensingTiming.DELAYED, SensingTiming.SAME_CYCLE)
        for information in (InformationArm.INFORMATIVE, InformationArm.SHAM)
    )
    if len(output) != 24:
        raise RuntimeError("FEP-PH1.8 Stage B factorial must contain 24 conditions")
    return output


def development_conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
    decisions = _screen_decisions(screen_root)
    output = tuple(
        _condition(
            decisions[key],
            stage=ExperimentStage.INFORMATION,
            tier=ChallengeTier.HARD,
            switch_probability=switch_probability,
            timing=timing,
            information=InformationArm.INFORMATIVE,
        )
        for key in MECHANISM_KEYS
        for switch_probability in SCREEN_SWITCH_PROBABILITIES
        for timing in (SensingTiming.DELAYED, SensingTiming.SAME_CYCLE)
    )
    return output


def load_conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
    """Compatibility alias for the frozen 20-condition development corpus."""

    return development_conditions(screen_root)


def conditions_for_mechanism(
    conditions: Iterable[ConditionSpec], mechanism_key: str
) -> tuple[ConditionSpec, ...]:
    output = tuple(value for value in conditions if value.mechanism_key == mechanism_key)
    if not output:
        raise RuntimeError(f"mechanism {mechanism_key} has no conditions")
    return output


def _balanced_actions(
    config: ExperimentConfig,
    cohort: str,
    condition: ConditionSpec,
    matrix_id: int,
    episode: int,
    steps: int,
) -> NDArray[np.int8]:
    alphabet = (
        np.asarray((0, 1, 2, 3), dtype=np.int8)
        if condition.sensing_timing == SensingTiming.DELAYED
        else np.asarray((0, 1, 2, 4, 5, 6), dtype=np.int8)
    )
    order = np.random.default_rng(
        _seed(config, f"{cohort}.action_cycle", condition.key, matrix_id, episode)
    ).permutation(alphabet)
    return np.asarray([order[index % len(order)] for index in range(steps)], dtype=np.int8)


def cue_accuracy(
    config: ExperimentConfig, condition: ConditionSpec, action: int
) -> float:
    sampled = int(action) in (int(Action.SAMPLE), 4, 5, 6)
    if condition.information_arm == InformationArm.NONE:
        return (
            config.stage_a_sample_accuracy
            if sampled
            else config.stage_a_passive_cue_accuracy
        )
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
        "matrix_id": [],
        "episode": [],
        "step": [],
        "action": [],
        "coarse_features": [],
        "rich_features": [],
        "coarse_targets": [],
        "rich_targets": [],
        "current_regime": [],
        "next_regime": [],
        "current_growth": [],
        "current_similarity": [],
        "current_alignment": [],
        "current_cue": [],
        "next_growth": [],
        "next_similarity": [],
        "next_alignment": [],
        "next_cue": [],
        "completed": [],
    }
    regime = regime_spec(condition.switch_probability)
    for matrix_id in matrix_ids:
        beta = beta_for(config, cohort, matrix_id)
        design = environment_design(config, condition, matrix_id, cohort)
        for episode in range(episodes):
            initial = initial_for(config, cohort, matrix_id, condition, episode)
            environment = GardGoalAlignmentEnvironment(
                config,
                design,
                beta,
                initial,
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
            actions = _balanced_actions(
                config, cohort, condition, matrix_id, episode, steps
            )
            current_regime = int(environment.regime)
            current_raw = first.raw_observation
            for step, action_value in enumerate(actions):
                model_action = int(action_value)
                if model_action >= 4:
                    sensed_cue = environment.sense_current()
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
                rows["matrix_id"].append(matrix_id)
                rows["episode"].append(episode)
                rows["step"].append(step)
                rows["action"].append(model_action)
                rows["coarse_features"].append(
                    state_features(decision_state, condition, rich=False)
                )
                rows["rich_features"].append(
                    state_features(decision_state, condition, rich=True)
                )
                rows["coarse_targets"].append(
                    transition_target(
                        result.composition,
                        result.raw_observation,
                        result.completed,
                        result.external_regime,
                        condition.growth_budget,
                        rich=False,
                    )
                )
                rows["rich_targets"].append(
                    transition_target(
                        result.composition,
                        result.raw_observation,
                        result.completed,
                        result.external_regime,
                        condition.growth_budget,
                        rich=True,
                    )
                )
                rows["current_regime"].append(current_regime)
                rows["next_regime"].append(result.external_regime)
                rows["current_growth"].append(current_raw.growth_steps)
                rows["current_similarity"].append(current_raw.boundary_similarity)
                rows["current_alignment"].append(current_raw.alignment_score)
                rows["current_cue"].append(
                    sensed_cue if model_action >= 4 else current_raw.cue
                )
                rows["next_growth"].append(result.raw_observation.growth_steps)
                rows["next_similarity"].append(result.raw_observation.boundary_similarity)
                rows["next_alignment"].append(result.raw_observation.alignment_score)
                rows["next_cue"].append(result.raw_observation.cue)
                rows["completed"].append(int(result.completed))
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
        raise RuntimeError(f"transition collection produced no rows for {condition.key}")
    float_names = {
        "coarse_features", "rich_features", "coarse_targets", "rich_targets",
        "current_similarity", "current_alignment", "next_similarity", "next_alignment",
    }
    int32_names = {"matrix_id", "current_growth", "next_growth"}
    output: dict[str, NDArray[Any]] = {}
    for name, values in rows.items():
        dtype: Any = np.float64 if name in float_names else np.int32 if name in int32_names else np.int16
        output[name] = np.asarray(values, dtype=dtype)
    return output


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
        "schema": "fep-ph18-development-cell-v1",
        "condition": condition.key,
        "mechanism": condition.mechanism_key,
        "rows": int(len(arrays["action"])),
        "matrices": config.development_matrices,
        "episodes": config.development_episodes,
        "steps": config.development_steps,
        "action_counts": {
            str(action): int(np.count_nonzero(arrays["action"] == action))
            for action in range(MODEL_ACTIONS)
        },
        "terminal_rows": int(np.count_nonzero(arrays["completed"] == 0)),
        "true_regime_is_training_target_only": True,
        "learned_feature_firewall": ["true_regime", "beta", "rng_state", "f12", "strict8"],
    }
    return arrays, metadata


def training_data_from_cells(paths: Iterable[Path]) -> TrainingData:
    collected: dict[str, list[NDArray[Any]]] = {
        name: []
        for name in (
            "matrix_id", "action", "coarse_features", "rich_features",
            "coarse_targets", "rich_targets",
        )
    }
    for path in paths:
        with np.load(path, allow_pickle=False) as archive:
            for name in collected:
                collected[name].append(archive[name].copy())
    if not collected["matrix_id"]:
        raise RuntimeError("no development cells were supplied")
    data = TrainingData(
        np.concatenate(collected["matrix_id"]).astype(np.int32),
        np.concatenate(collected["action"]).astype(np.int8),
        np.concatenate(collected["coarse_features"]).astype(np.float64),
        np.concatenate(collected["rich_features"]).astype(np.float64),
        np.concatenate(collected["coarse_targets"]).astype(np.float64),
        np.concatenate(collected["rich_targets"]).astype(np.float64),
    )
    data.validate()
    return data
