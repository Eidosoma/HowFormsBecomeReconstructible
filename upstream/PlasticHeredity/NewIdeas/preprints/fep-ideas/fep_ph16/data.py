from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import read_json
from fep_lab.seeds import derive_seed
from fep_ph1.gard import generate_beta, generate_initial_composition
from fep_ph15.config import regime_specs
from fep_ph15.environment import encode_observation
from fep_ph15.models import ModelCounts, hidden_state, model_from_counts
from fep_ph15.simulation import BehaviorTrace, fitted_thresholds
from fep_ph15.types import ActuatorSetting, ChallengeSelection, PreferenceMode

from .causal_model import TrainingData, transition_target
from .config import MECHANISM_KEYS, RIDGE_GRID, ExperimentConfig
from .environment import EnvironmentDesign, GardGoalAlignmentEnvironment
from .state import (
    advance_body_state,
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
    ObservationThresholds,
)


@dataclass(frozen=True)
class MechanismModels:
    coarse_path: Path
    rich_path: Path


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph16.{domain}", *parts)


def cohort_seed_domains(config: ExperimentConfig) -> dict[str, int]:
    return {
        cohort: _seed(config, f"{cohort}.fixture", "disjointness")
        for cohort in ("development", "calibration", "evaluation", "planning")
    }


def beta_for(config: ExperimentConfig, cohort: str, matrix_id: int) -> NDArray[np.float64]:
    basis = "evaluation" if cohort == "calibration" else cohort
    return generate_beta(
        config.gard,
        np.random.default_rng(_seed(config, f"{basis}.beta", matrix_id)),
    )


def initial_for(
    config: ExperimentConfig,
    cohort: str,
    matrix_id: int,
    condition: ConditionSpec,
    episode: int,
    branch: int = 0,
) -> NDArray[np.int64]:
    return generate_initial_composition(
        config.gard,
        np.random.default_rng(
            _seed(
                config,
                f"{cohort}.initial",
                matrix_id,
                condition.key,
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
    return tuple(
        _seed(
            config,
            f"{cohort}.{kind}",
            condition.key,
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
    basis = "evaluation" if cohort == "calibration" else cohort
    return EnvironmentDesign(
        condition.family,
        condition.channel,
        regime_specs()[condition.regime_index],
        condition.candidate,
        _seed(config, f"{basis}.design.partition", condition.family, matrix_id),
        _seed(config, f"{basis}.design.permutation", condition.family, matrix_id),
        condition.growth_budget,
        condition.actuator,
    )


def load_conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
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
            f"sealed FEP-PH1.5 screen did not provide the six frozen mechanisms: {sorted(decisions)}"
        )
    output = []
    for key in MECHANISM_KEYS:
        challenge, actuator, payload = decisions[key]
        for tier in ChallengeTier:
            for regime_index in range(2):
                output.append(
                    ConditionSpec(
                        str(payload["candidate"]),
                        EnvironmentFamily(str(payload["family"])),
                        ActionChannel(str(payload["channel"])),
                        tier,
                        regime_index,
                        challenge.budget(tier),
                        actuator,
                    )
                )
    if len(output) != 24:
        raise RuntimeError("FEP-PH1.6 condition factorial must contain 24 cells")
    return tuple(output)


def conditions_for_mechanism(
    conditions: Iterable[ConditionSpec], mechanism_key: str
) -> tuple[ConditionSpec, ...]:
    output = tuple(value for value in conditions if value.mechanism_key == mechanism_key)
    if len(output) != 4:
        raise RuntimeError(f"mechanism {mechanism_key} must have four conditions")
    return output


def _balanced_actions(
    config: ExperimentConfig,
    cohort: str,
    condition: ConditionSpec,
    matrix_id: int,
    episode: int,
    steps: int,
) -> NDArray[np.int8]:
    order = np.random.default_rng(
        _seed(config, f"{cohort}.action_cycle", condition.key, matrix_id, episode)
    ).permutation(4)
    return np.asarray([order[index % 4] for index in range(steps)], dtype=np.int8)


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
    regime = regime_specs()[condition.regime_index]
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
                config.passive_cue_accuracy,
                transition=False,
            )
            state = initial_body_state(first.composition, first.raw_observation, belief)
            actions = _balanced_actions(
                config, cohort, condition, matrix_id, episode, steps
            )
            current_regime = int(environment.regime)
            current_raw = first.raw_observation
            for step, action_value in enumerate(actions):
                action = int(action_value)
                result = environment.step(action)
                accuracy = (
                    config.sampled_cue_accuracy
                    if action == int(Action.SAMPLE)
                    else config.passive_cue_accuracy
                )
                following_belief = update_regime_belief(
                    state.regime_belief,
                    result.raw_observation.cue,
                    regime.switch_probability,
                    regime.shock_probability,
                    accuracy,
                )
                rows["matrix_id"].append(matrix_id)
                rows["episode"].append(episode)
                rows["step"].append(step)
                rows["action"].append(action)
                rows["coarse_features"].append(state_features(state, condition, rich=False))
                rows["rich_features"].append(state_features(state, condition, rich=True))
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
                rows["current_cue"].append(current_raw.cue)
                rows["next_growth"].append(result.raw_observation.growth_steps)
                rows["next_similarity"].append(result.raw_observation.boundary_similarity)
                rows["next_alignment"].append(result.raw_observation.alignment_score)
                rows["next_cue"].append(result.raw_observation.cue)
                rows["completed"].append(int(result.completed))
                if not result.completed:
                    break
                state = advance_body_state(
                    state,
                    result.composition,
                    result.raw_observation,
                    following_belief,
                    action,
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
        "schema": "fep-ph16-development-cell-v1",
        "condition": condition.key,
        "mechanism": condition.mechanism_key,
        "rows": int(len(arrays["action"])),
        "matrices": config.development_matrices,
        "episodes": config.development_episodes,
        "steps": config.development_steps,
        "action_counts": {
            str(action): int(np.count_nonzero(arrays["action"] == action))
            for action in range(4)
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


def thresholds_and_categorical_model(
    config: ExperimentConfig, development_path: Path
) -> tuple[ObservationThresholds, ModelCounts, object, dict[str, float]]:
    with np.load(development_path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    trace = BehaviorTrace(
        np.concatenate((arrays["current_regime"], arrays["next_regime"][-1:])),
        np.concatenate((arrays["current_growth"], arrays["next_growth"][-1:])),
        np.concatenate((arrays["current_similarity"], arrays["next_similarity"][-1:])),
        np.concatenate((arrays["current_alignment"], arrays["next_alignment"][-1:])),
        np.concatenate((arrays["current_cue"], arrays["next_cue"][-1:])),
        np.concatenate((np.zeros(len(arrays["action"]), dtype=np.int8), (1 - arrays["completed"][-1:]))),
        arrays["action"].astype(np.int8),
    )
    thresholds = fitted_thresholds([trace])
    counts = ModelCounts.empty()
    for index, action in enumerate(arrays["action"]):
        current_raw = (
            int(arrays["current_growth"][index]),
            float(arrays["current_similarity"][index]),
            float(arrays["current_alignment"][index]),
            int(arrays["current_cue"][index]),
            False,
        )
        next_raw = (
            int(arrays["next_growth"][index]),
            float(arrays["next_similarity"][index]),
            float(arrays["next_alignment"][index]),
            int(arrays["next_cue"][index]),
            not bool(arrays["completed"][index]),
        )
        from fep_ph1.types import RawObservation

        current_observation = encode_observation(RawObservation(*current_raw), thresholds)
        next_observation = encode_observation(RawObservation(*next_raw), thresholds)
        current_state = hidden_state(int(arrays["current_regime"][index]), int(current_observation[2]))
        next_state = hidden_state(int(arrays["next_regime"][index]), int(next_observation[2]))
        if int(arrays["step"][index]) == 0:
            counts.add_initial(current_state, current_observation)
        counts.add_transition(current_state, int(action), next_state, next_observation)
    model = model_from_counts(counts, config, PreferenceMode.BALANCED)
    summary = {
        "rows": float(len(arrays["action"])),
        "terminal_rows": float(np.count_nonzero(arrays["completed"] == 0)),
        "alignment_lower": thresholds.alignment[0],
        "alignment_upper": thresholds.alignment[1],
        "growth_lower": thresholds.growth[0],
        "growth_upper": thresholds.growth[1],
    }
    return thresholds, counts, model, summary


def calibration_data(
    config: ExperimentConfig, cell: CellSpec
) -> dict[str, NDArray[Any]]:
    return collect_transitions(
        config,
        cell.condition,
        cohort="calibration",
        matrix_ids=(cell.matrix_id,),
        episodes=config.calibration_episodes,
        steps=config.calibration_steps,
    )


def ridge_grid() -> tuple[float, ...]:
    return RIDGE_GRID
