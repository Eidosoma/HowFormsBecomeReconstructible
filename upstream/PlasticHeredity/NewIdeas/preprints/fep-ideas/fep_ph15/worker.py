from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import read_json
from fep_lab.seeds import derive_seed
from fep_ph1.gard import generate_beta, generate_initial_composition

from .config import ExperimentConfig, regime_specs
from .controllers import yoked_random_schedule
from .environment import EnvironmentDesign
from .models import (
    ModelCounts,
    load_model,
    model_digest,
    model_from_counts,
    prior_counts_from_model,
    scrambled_model,
    with_preferences,
)
from .screen import ScreenCombination
from .simulation import (
    BehaviorTrace,
    controller_for,
    counts_from_behavior,
    fitted_thresholds,
    run_behavior_trace,
    run_episode,
)
from .types import (
    CORE_CONTROLLERS,
    HARD_DIAGNOSTIC_CONTROLLERS,
    ActionChannel,
    ActuatorSetting,
    ChallengeSelection,
    ChallengeTier,
    ControllerName,
    EnvironmentFamily,
    ObservationThresholds,
    PreferenceMode,
)


@dataclass(frozen=True)
class ScreenDecision:
    combination: ScreenCombination
    challenge: ChallengeSelection
    actuator: ActuatorSetting


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
    def regime(self):
        return regime_specs()[self.regime_index]

    @property
    def key(self) -> str:
        return f"c{self.candidate}--{self.family}--{self.channel}--{self.tier}--{self.regime.volatility}"


@dataclass(frozen=True)
class CellSpec:
    matrix_id: int
    condition: ConditionSpec

    @property
    def stem(self) -> str:
        return f"m{self.matrix_id:04d}--{self.condition.key}"


def _screen_decision(path: Path) -> ScreenDecision:
    payload = read_json(path)
    combination = ScreenCombination(
        str(payload["candidate"]),
        EnvironmentFamily(str(payload["family"])),
        ActionChannel(str(payload["channel"])),
    )
    challenge = ChallengeSelection(**payload["challenge"])
    actuator = ActuatorSetting(**payload["actuator"])
    return ScreenDecision(combination, challenge, actuator)


def load_screen_decisions(screen_root: Path) -> tuple[ScreenDecision, ...]:
    decisions = tuple(
        _screen_decision(path)
        for path in sorted((Path(screen_root) / "cells").glob("*.json"))
    )
    if len(decisions) != 8:
        raise RuntimeError(f"expected 8 retained screen mechanisms, found {len(decisions)}")
    return decisions


def conditions(screen_root: Path) -> tuple[ConditionSpec, ...]:
    output = []
    for decision in load_screen_decisions(screen_root):
        for tier in ChallengeTier:
            for regime_index in range(len(regime_specs())):
                output.append(
                    ConditionSpec(
                        decision.combination.candidate,
                        decision.combination.family,
                        decision.combination.channel,
                        tier,
                        regime_index,
                        decision.challenge.budget(tier),
                        decision.actuator,
                    )
                )
    return tuple(output)


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph15.{domain}", *parts)


def cohort_seed_domains(config: ExperimentConfig) -> dict[str, int]:
    return {
        cohort: _seed(config, f"{cohort}.fixture", "disjointness")
        for cohort in ("development", "calibration", "evaluation")
    }


def _beta(config: ExperimentConfig, cohort: str, matrix_id: int) -> NDArray[np.float64]:
    return generate_beta(config.gard, np.random.default_rng(_seed(config, f"{cohort}.beta", matrix_id)))


def _initial(
    config: ExperimentConfig, cohort: str, matrix_id: int, *parts: object
) -> NDArray[np.int64]:
    return generate_initial_composition(
        config.gard,
        np.random.default_rng(_seed(config, f"{cohort}.initial", matrix_id, *parts)),
    )


def environment_design(
    config: ExperimentConfig, condition: ConditionSpec, matrix_id: int
) -> EnvironmentDesign:
    return EnvironmentDesign(
        condition.family,
        condition.channel,
        condition.regime,
        condition.candidate,
        _seed(config, "design.partition", condition.family, matrix_id),
        _seed(config, "design.permutation", condition.family, matrix_id),
        condition.growth_budget,
        condition.actuator,
    )


def behavior_traces(
    config: ExperimentConfig,
    condition: ConditionSpec,
    cohort: str,
    matrix_ids: range | tuple[int, ...],
    episodes: int,
    steps: int,
) -> list[BehaviorTrace]:
    traces: list[BehaviorTrace] = []
    for matrix_id in matrix_ids:
        beta = _beta(config, cohort, matrix_id)
        design = environment_design(config, condition, matrix_id)
        for episode in range(episodes):
            initial = _initial(config, cohort, matrix_id, condition.key, episode)
            seeds = tuple(
                _seed(config, f"{cohort}.behavior.{kind}", condition.key, matrix_id, episode)
                for kind in ("chemistry", "environment", "observation")
            )
            traces.append(
                run_behavior_trace(
                    config, design, beta, initial, seeds, steps, episode
                )  # type: ignore[arg-type]
            )
    return traces


def fit_pooled_condition(
    config: ExperimentConfig, condition: ConditionSpec
) -> tuple[ObservationThresholds, ModelCounts, object, dict[str, float]]:
    traces = behavior_traces(
        config, condition, "development", range(config.development_matrices),
        config.development_episodes, config.development_steps,
    )
    thresholds = fitted_thresholds(traces)
    counts = counts_from_behavior(traces, thresholds)
    model = model_from_counts(counts, config, PreferenceMode.BALANCED)
    return thresholds, counts, model, {
        "behavior_episodes": float(len(traces)),
        "completed_transitions": float(sum(len(trace.actions) for trace in traces)),
        "terminal_episodes": float(sum(bool(trace.terminal[-1]) for trace in traces)),
        "alignment_lower": thresholds.alignment[0],
        "alignment_upper": thresholds.alignment[1],
        "growth_lower": thresholds.growth[0],
        "growth_upper": thresholds.growth[1],
    }


def _local_model(
    config: ExperimentConfig,
    cell: CellSpec,
    pooled_model: object,
    thresholds: ObservationThresholds,
) -> tuple[object, dict[str, float]]:
    traces: list[BehaviorTrace] = []
    beta = _beta(config, "evaluation", cell.matrix_id)
    design = environment_design(config, cell.condition, cell.matrix_id)
    for episode in range(config.calibration_episodes):
        initial = _initial(
            config, "calibration", cell.matrix_id, cell.condition.key, episode
        )
        seeds = tuple(
            _seed(
                config,
                f"calibration.behavior.{kind}",
                cell.condition.key,
                cell.matrix_id,
                episode,
            )
            for kind in ("chemistry", "environment", "observation")
        )
        traces.append(
            run_behavior_trace(
                config,
                design,
                beta,
                initial,
                seeds,  # type: ignore[arg-type]
                config.calibration_steps,
                episode,
            )
        )
    observations = counts_from_behavior(traces, thresholds)
    counts = prior_counts_from_model(pooled_model).merge(observations)  # type: ignore[arg-type]
    model = model_from_counts(counts, config, PreferenceMode.BALANCED)
    return model, {
        "calibration_episodes": float(len(traces)),
        "calibration_transitions": float(sum(len(trace.actions) for trace in traces)),
        "calibration_terminals": float(sum(bool(trace.terminal[-1]) for trace in traces)),
    }


def _variants(
    config: ExperimentConfig,
    cell: CellSpec,
    pooled_model: object,
    local_model: object,
) -> dict[str, object]:
    pooled = pooled_model  # type: ignore[assignment]
    local = local_model  # type: ignore[assignment]
    return {
        "balanced_ai_local": with_preferences(local, PreferenceMode.BALANCED, information_gain=True),
        "balanced_reward_local": with_preferences(local, PreferenceMode.BALANCED, information_gain=False),
        "growth_ai_local": with_preferences(local, PreferenceMode.GROWTH, information_gain=True),
        "growth_reward_local": with_preferences(local, PreferenceMode.GROWTH, information_gain=False),
        "balanced_ai_pooled": with_preferences(pooled, PreferenceMode.BALANCED, information_gain=True),
        "balanced_reward_pooled": with_preferences(pooled, PreferenceMode.BALANCED, information_gain=False),
        "scrambled_local": scrambled_model(
            with_preferences(local, PreferenceMode.BALANCED, information_gain=True),
            _seed(config, "model.scramble", cell.condition.key, cell.matrix_id),
        ),
    }


def _adapt_cost(config: ExperimentConfig, condition: ConditionSpec) -> float:
    return config.action_cost_uptake if condition.channel == ActionChannel.UPTAKE else config.molecular_base_cost + config.molecular_increment_cost * (condition.actuator.molecular_dose - 1)


def _process_seeds(config: ExperimentConfig, cell: CellSpec, branch: int) -> tuple[int, int, int]:
    return tuple(
        _seed(config, f"evaluation.{kind}", cell.condition.key, cell.matrix_id, branch)
        for kind in ("chemistry", "environment", "observation")
    )  # type: ignore[return-value]


def _agent_pair(name: ControllerName) -> str:
    if name in (ControllerName.BALANCED_AI_LOCAL, ControllerName.BALANCED_REWARD_LOCAL):
        return "balanced-local"
    if name in (ControllerName.GROWTH_AI_LOCAL, ControllerName.GROWTH_REWARD_LOCAL):
        return "growth-local"
    if name in (ControllerName.BALANCED_AI_POOLED, ControllerName.BALANCED_REWARD_POOLED):
        return "balanced-pooled"
    return str(name)


def _run_named(
    config: ExperimentConfig,
    cell: CellSpec,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    thresholds: ObservationThresholds,
    name: ControllerName,
    pooled: object,
    local: object,
    variants: dict[str, object],
    branch: int,
    schedule: NDArray[np.int64] | None = None,
) -> dict[str, NDArray]:
    controller = controller_for(
        name, config, pooled, local, variants, _adapt_cost(config, cell.condition), schedule  # type: ignore[arg-type]
    )
    return run_episode(
        config,
        environment_design(config, cell.condition, cell.matrix_id),
        beta,
        initial,
        thresholds,
        name,
        controller,
        _process_seeds(config, cell, branch),
        _seed(config, "evaluation.agent", cell.condition.key, cell.matrix_id, branch, _agent_pair(name)),
    )


def generate_evaluation_cell(
    config: ExperimentConfig,
    cell: CellSpec,
    model_path: Path,
    thresholds: ObservationThresholds,
) -> tuple[dict[str, NDArray], dict[str, object]]:
    pooled, _counts = load_model(model_path)
    local, calibration = _local_model(config, cell, pooled, thresholds)
    variants = _variants(config, cell, pooled, local)
    beta = _beta(config, "evaluation", cell.matrix_id)
    names = list(CORE_CONTROLLERS)
    if cell.condition.tier == ChallengeTier.HARD:
        names.extend(HARD_DIAGNOSTIC_CONTROLLERS)
    episodes: dict[tuple[ControllerName, int], dict[str, NDArray]] = {}
    for branch in range(config.branches):
        initial = _initial(config, "evaluation", cell.matrix_id, cell.condition.key, branch)
        for name in (
            ControllerName.BALANCED_AI_LOCAL,
            ControllerName.GROWTH_AI_LOCAL,
            ControllerName.BALANCED_AI_POOLED,
        ):
            episodes[(name, branch)] = _run_named(
                config, cell, beta, initial, thresholds, name, pooled, local,
                variants, branch,
            )
        schedule = yoked_random_schedule(
            episodes[(ControllerName.BALANCED_AI_LOCAL, branch)]["intended_actions"],
            _seed(config, "evaluation.yoked", cell.condition.key, cell.matrix_id, branch),
        )
        for name in names:
            if (name, branch) in episodes:
                continue
            episodes[(name, branch)] = _run_named(
                config, cell, beta, initial, thresholds, name, pooled, local,
                variants, branch,
                schedule if name == ControllerName.BALANCED_YOKED_LOCAL else None,
            )
    arrays: dict[str, NDArray] = {
        "controller_names": np.asarray([str(name) for name in names]),
        "matrix_id": np.asarray((cell.matrix_id,), dtype=np.int32),
        "local_model_digest": np.asarray((model_digest(local),)),
        "threshold_alignment": np.asarray(thresholds.alignment),
        "threshold_growth": np.asarray(thresholds.growth),
        "growth_budget": np.asarray((cell.condition.growth_budget,), dtype=np.int32),
    }
    schema = tuple(next(iter(episodes.values())))
    for array_name in schema:
        arrays[array_name] = np.stack(
            [
                np.stack([episodes[(controller, branch)][array_name] for branch in range(config.branches)])
                for controller in names
            ]
        )
    metadata: dict[str, object] = {
        "schema": "fep-ph15-evaluation-cell-v1",
        "stem": cell.stem,
        "matrix_id": cell.matrix_id,
        "candidate": cell.condition.candidate,
        "family": str(cell.condition.family),
        "channel": str(cell.condition.channel),
        "tier": str(cell.condition.tier),
        "volatility": cell.condition.regime.volatility,
        "growth_budget": cell.condition.growth_budget,
        "actionability": cell.condition.actuator.actionability,
        "actuator_polarity": cell.condition.actuator.polarity,
        "molecular_dose": cell.condition.actuator.molecular_dose,
        "controllers": [str(name) for name in names],
        "pooled_model_digest": model_digest(pooled),
        "local_model_digest": model_digest(local),
        "calibration": calibration,
    }
    return arrays, metadata
