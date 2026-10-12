from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from fep_lab.seeds import derive_seed

from .config import ExperimentConfig, RegimeSpec, regime_specs
from .controllers import yoked_random_schedule
from .environment import EnvironmentDesign
from .gard import (
    apply_ranked_substitution,
    cosine_similarity,
    generate_beta,
    generate_initial_composition,
)
from .models import (
    ModelCounts,
    load_model,
    model_digest,
    model_from_counts,
    prior_counts_from_model,
    reversed_preferences,
    reward_only,
    scrambled_model,
)
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
    DIAGNOSTIC_CONTROLLERS,
    ActionChannel,
    ControllerName,
    EnvironmentFamily,
    ObservationThresholds,
)


@dataclass(frozen=True)
class ConditionSpec:
    candidate: str
    family: EnvironmentFamily
    channel: ActionChannel
    regime: RegimeSpec

    @property
    def key(self) -> str:
        return f"c{self.candidate}--{self.family}--{self.channel}--{self.regime.key}"


@dataclass(frozen=True)
class CellSpec:
    matrix_id: int
    condition: ConditionSpec

    @property
    def stem(self) -> str:
        return f"m{self.matrix_id:04d}--{self.condition.key}"


def conditions() -> tuple[ConditionSpec, ...]:
    return tuple(
        ConditionSpec(candidate, family, channel, regime)
        for candidate in ("02", "03")
        for family in EnvironmentFamily
        for channel in ActionChannel
        for regime in regime_specs()
    )


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph1.{domain}", *parts)


def _beta(config: ExperimentConfig, cohort: str, matrix_id: int) -> NDArray[np.float64]:
    return generate_beta(
        config.gard,
        np.random.default_rng(_seed(config, f"{cohort}.beta", matrix_id)),
    )


def _initial(
    config: ExperimentConfig,
    cohort: str,
    matrix_id: int,
    *parts: object,
) -> NDArray[np.int64]:
    return generate_initial_composition(
        config.gard,
        np.random.default_rng(_seed(config, f"{cohort}.initial", matrix_id, *parts)),
    )


def environment_design(
    config: ExperimentConfig, condition: ConditionSpec, matrix_id: int
) -> EnvironmentDesign:
    return EnvironmentDesign(
        family=condition.family,
        channel=condition.channel,
        regime=condition.regime,
        candidate=condition.candidate,
        partition_seed=_seed(
            config, "design.partition", condition.family, matrix_id
        ),
        permutation_seed=_seed(
            config, "design.permutation", condition.family, matrix_id
        ),
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
                _seed(
                    config,
                    f"{cohort}.behavior.{kind}",
                    condition.key,
                    matrix_id,
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
                    steps,
                    episode,
                )
            )
    return traces


def fit_pooled_condition(
    config: ExperimentConfig, condition: ConditionSpec
) -> tuple[ObservationThresholds, ModelCounts, object, dict[str, float]]:
    traces = behavior_traces(
        config,
        condition,
        "development",
        range(config.development_matrices),
        config.development_episodes,
        config.calibration_steps,
    )
    thresholds = fitted_thresholds(traces)
    counts = counts_from_behavior(traces, thresholds)
    model = model_from_counts(counts, config)
    completed_transitions = float(sum(len(trace.actions) for trace in traces))
    terminal_episodes = float(sum(bool(trace.terminal[-1]) for trace in traces))
    summary = {
        "behavior_episodes": float(len(traces)),
        "completed_transitions": completed_transitions,
        "terminal_episodes": terminal_episodes,
        "alignment_lower": thresholds.alignment[0],
        "alignment_upper": thresholds.alignment[1],
        "growth_lower": thresholds.growth[0],
        "growth_upper": thresholds.growth[1],
    }
    return thresholds, counts, model, summary


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
            config,
            "calibration",
            cell.matrix_id,
            cell.condition.key,
            episode,
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
    local_observations = counts_from_behavior(traces, thresholds)
    prior = prior_counts_from_model(pooled_model)  # type: ignore[arg-type]
    counts = prior.merge(local_observations)
    model = model_from_counts(counts, config)
    summary = {
        "calibration_episodes": float(len(traces)),
        "calibration_transitions": float(sum(len(trace.actions) for trace in traces)),
        "calibration_terminals": float(sum(bool(trace.terminal[-1]) for trace in traces)),
    }
    return model, summary


def _process_seeds(
    config: ExperimentConfig, cell: CellSpec, branch: int
) -> tuple[int, int, int]:
    return tuple(
        _seed(
            config,
            f"evaluation.{kind}",
            cell.condition.key,
            cell.matrix_id,
            branch,
        )
        for kind in ("chemistry", "environment", "observation")
    )  # type: ignore[return-value]


def _model_variants(
    config: ExperimentConfig,
    cell: CellSpec,
    pooled_model: object,
    local_model: object,
) -> dict[str, object]:
    return {
        "reward_pooled": reward_only(pooled_model),  # type: ignore[arg-type]
        "reward_local": reward_only(local_model),  # type: ignore[arg-type]
        "scrambled": scrambled_model(
            pooled_model,  # type: ignore[arg-type]
            _seed(config, "model.scramble", cell.condition.key, cell.matrix_id),
        ),
        "reversed": reversed_preferences(pooled_model),  # type: ignore[arg-type]
    }


def _run_named_episode(
    config: ExperimentConfig,
    cell: CellSpec,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    thresholds: ObservationThresholds,
    name: ControllerName,
    pooled_model: object,
    local_model: object,
    variants: dict[str, object],
    branch: int,
    schedule: NDArray[np.int64] | None = None,
) -> dict[str, NDArray]:
    controller = controller_for(
        name,
        config,
        pooled_model,  # type: ignore[arg-type]
        local_model,  # type: ignore[arg-type]
        variants,  # type: ignore[arg-type]
        schedule,
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
        _seed(
            config,
            "evaluation.agent",
            cell.condition.key,
            cell.matrix_id,
            branch,
            name,
        ),
    )


def _amplification_probe(
    config: ExperimentConfig,
    cell: CellSpec,
    beta: NDArray[np.float64],
    thresholds: ObservationThresholds,
    pooled_model: object,
    variants: dict[str, object],
) -> float:
    probe_config = replace(config, horizon=min(8, config.horizon))
    initial = _initial(config, "probe", cell.matrix_id, cell.condition.key)
    scores = np.linspace(-1.0, 1.0, config.gard.n_types)
    perturbed, _remove, _add = apply_ranked_substitution(initial, scores)
    seeds = tuple(
        _seed(config, f"probe.{kind}", cell.condition.key, cell.matrix_id)
        for kind in ("chemistry", "environment", "observation")
    )
    left_controller = controller_for(
        ControllerName.NOOP,
        probe_config,
        pooled_model,  # type: ignore[arg-type]
        pooled_model,  # type: ignore[arg-type]
        variants,  # type: ignore[arg-type]
    )
    right_controller = controller_for(
        ControllerName.NOOP,
        probe_config,
        pooled_model,  # type: ignore[arg-type]
        pooled_model,  # type: ignore[arg-type]
        variants,  # type: ignore[arg-type]
    )
    design = environment_design(config, cell.condition, cell.matrix_id)
    left = run_episode(
        probe_config,
        design,
        beta,
        initial,
        thresholds,
        ControllerName.NOOP,
        left_controller,
        seeds,  # type: ignore[arg-type]
        _seed(config, "probe.agent.left", cell.condition.key, cell.matrix_id),
    )
    right = run_episode(
        probe_config,
        design,
        beta,
        perturbed,
        thresholds,
        ControllerName.NOOP,
        right_controller,
        seeds,  # type: ignore[arg-type]
        _seed(config, "probe.agent.right", cell.condition.key, cell.matrix_id),
    )
    distances = []
    for index in range(probe_config.horizon):
        if left["completed"][index] and right["completed"][index]:
            distances.append(
                1.0
                - cosine_similarity(
                    left["compositions"][index], right["compositions"][index]
                )
            )
        else:
            distances.append(1.0)
    return float(np.mean(distances))


def generate_evaluation_cell(
    config: ExperimentConfig,
    cell: CellSpec,
    model_path: Path,
    thresholds: ObservationThresholds,
) -> tuple[dict[str, NDArray], dict[str, object]]:
    pooled_model, _pooled_counts = load_model(model_path)
    local_model, calibration_summary = _local_model(
        config, cell, pooled_model, thresholds
    )
    variants = _model_variants(config, cell, pooled_model, local_model)
    beta = _beta(config, "evaluation", cell.matrix_id)
    controller_names = list(CORE_CONTROLLERS)
    if cell.condition.regime.severity_index == 2:
        controller_names.extend(DIAGNOSTIC_CONTROLLERS)
    episodes: dict[tuple[ControllerName, int], dict[str, NDArray]] = {}
    for branch in range(config.branches):
        initial = _initial(
            config, "evaluation", cell.matrix_id, cell.condition.key, branch
        )
        for name in (ControllerName.AI_POOLED, ControllerName.AI_LOCAL):
            episodes[(name, branch)] = _run_named_episode(
                config,
                cell,
                beta,
                initial,
                thresholds,
                name,
                pooled_model,
                local_model,
                variants,
                branch,
            )
        pooled_schedule = yoked_random_schedule(
            episodes[(ControllerName.AI_POOLED, branch)]["intended_actions"],
            _seed(config, "yoked.pooled", cell.condition.key, cell.matrix_id, branch),
        )
        local_schedule = yoked_random_schedule(
            episodes[(ControllerName.AI_LOCAL, branch)]["intended_actions"],
            _seed(config, "yoked.local", cell.condition.key, cell.matrix_id, branch),
        )
        for name in controller_names:
            if (name, branch) in episodes:
                continue
            schedule = (
                pooled_schedule
                if name == ControllerName.RANDOM_POOLED
                else local_schedule
                if name == ControllerName.RANDOM_LOCAL
                else None
            )
            episodes[(name, branch)] = _run_named_episode(
                config,
                cell,
                beta,
                initial,
                thresholds,
                name,
                pooled_model,
                local_model,
                variants,
                branch,
                schedule,
            )

    arrays: dict[str, NDArray] = {
        "controller_names": np.asarray([str(name) for name in controller_names]),
        "matrix_id": np.asarray((cell.matrix_id,), dtype=np.int32),
        "local_model_digest": np.asarray((model_digest(local_model),)),
        "threshold_alignment": np.asarray(thresholds.alignment, dtype=np.float64),
        "threshold_growth": np.asarray(thresholds.growth, dtype=np.float64),
        "amplification_probe": np.asarray(
            (
                _amplification_probe(
                    config, cell, beta, thresholds, pooled_model, variants
                ),
            ),
            dtype=np.float64,
        ),
    }
    schema = tuple(next(iter(episodes.values())))
    for name in schema:
        arrays[name] = np.stack(
            [
                np.stack(
                    [episodes[(controller, branch)][name] for branch in range(config.branches)],
                    axis=0,
                )
                for controller in controller_names
            ],
            axis=0,
        )
    metadata: dict[str, object] = {
        "stem": cell.stem,
        "matrix_id": cell.matrix_id,
        "candidate": cell.condition.candidate,
        "environment_family": str(cell.condition.family),
        "action_channel": str(cell.condition.channel),
        "regime": cell.condition.regime.key,
        "controllers": [str(name) for name in controller_names],
        "pooled_model_digest": model_digest(pooled_model),
        "local_model_digest": model_digest(local_model),
        "calibration": calibration_summary,
    }
    return arrays, metadata
