from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .causal_model import TrainingData
from .config import MODEL_ACTIONS, RIDGE_GRID, ExperimentConfig
from .controllers import exact_multiset_yoke
from .data import (
    beta_for,
    cohort_seed_domains,
    environment_design,
    initial_for,
    process_seeds,
    stage_a_conditions,
    stage_b_conditions,
    development_conditions,
)
from .environment import GardGoalAlignmentEnvironment, clone_environment
from .hybrid_model import (
    expected_regime_information,
    fit_hybrid_model,
    model_digest,
    posterior_for_cue,
)
from .types import Action, InformationArm, ObservationThresholds, SensingTiming


def _check(name: str, passed: bool, **evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def _physical_result_equal(left: Any, right: Any) -> bool:
    return (
        left.completed == right.completed
        and left.external_regime == right.external_regime
        and left.alignment_level == right.alignment_level
        and left.intended_action == right.intended_action
        and left.executed_action == right.executed_action
        and left.abstract_action_cost == right.abstract_action_cost
        and left.physical_action_cost == right.physical_action_cost
        and left.raw_observation.growth_steps == right.raw_observation.growth_steps
        and left.raw_observation.boundary_similarity
        == right.raw_observation.boundary_similarity
        and left.raw_observation.alignment_score == right.raw_observation.alignment_score
        and left.raw_observation.terminal == right.raw_observation.terminal
        and np.array_equal(left.composition, right.composition)
        and (
            (left.parent is None and right.parent is None)
            or (
                left.parent is not None
                and right.parent is not None
                and np.array_equal(left.parent, right.parent)
            )
        )
    )


def _synthetic_data(members: int, rows_per_matrix: int = 21) -> TrainingData:
    rng = np.random.default_rng(18_701)
    rows = members * rows_per_matrix
    matrix_ids = np.repeat(np.arange(members, dtype=np.int32), rows_per_matrix)
    actions = np.asarray(np.arange(rows) % MODEL_ACTIONS, dtype=np.int8)
    coarse = rng.normal(size=(rows, 48))
    clr = rng.normal(size=(rows, 100))
    clr -= clr.mean(axis=1, keepdims=True)
    rich = np.concatenate((clr, rng.normal(size=(rows, 49))), axis=1)
    # Preserve the frozen regime-belief feature positions.
    rich[:, 109:112] = rng.dirichlet(np.ones(3), size=rows)
    base = rng.normal(size=(rows, 12))
    action_signal = (actions == 1).astype(float) * 0.20 + (actions >= 4).astype(float) * 0.10
    base[:, 0] = (rng.random(rows) < 0.45 + action_signal).astype(float)
    base[:, 1] = np.clip(rng.normal(0.55, 0.10, rows), 0.0, 1.5)
    base[:, 2:4] = np.clip(rng.normal(0.8, 0.1, size=(rows, 2)), 0.0, 1.0)
    base[:, 4] = np.clip(rng.normal(1.0, 0.1, rows), 0.0, 1.5)
    base[:, 5:9] = 0.25
    base[:, 9:12] = np.asarray((0.475, 0.475, 0.05))
    next_clr = clr + rng.normal(0.0, 0.05, clr.shape)
    next_clr -= next_clr.mean(axis=1, keepdims=True)
    data = TrainingData(
        matrix_ids,
        actions,
        coarse,
        rich,
        base,
        np.concatenate((base, next_clr), axis=1),
    )
    data.validate()
    return data


def validate_experiment(config: ExperimentConfig, screen_root: Path) -> dict[str, Any]:
    config.validate()
    development = development_conditions(screen_root)
    stage_a = stage_a_conditions(screen_root)
    stage_b = stage_b_conditions(screen_root)
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "factorials",
            len(development) == 20 and len(stage_a) == 10 and len(stage_b) == 24,
            development=len(development),
            stage_a=len(stage_a),
            stage_b=len(stage_b),
        )
    )
    domains = cohort_seed_domains(config)
    checks.append(
        _check(
            "seed_domains_disjoint",
            len(set(domains.values())) == len(domains),
            domains=domains,
        )
    )
    checks.append(
        _check(
            "confirmation_has_three_volatility_bands_and_both_timings",
            {value.switch_probability for value in stage_b} == {0.08, 0.15, 0.25}
            and {value.sensing_timing for value in stage_b}
            == {SensingTiming.DELAYED, SensingTiming.SAME_CYCLE},
        )
    )

    informative = next(
        value
        for value in stage_b
        if value.information_arm == InformationArm.INFORMATIVE
        and value.sensing_timing == SensingTiming.SAME_CYCLE
    )
    sham = next(
        value
        for value in stage_b
        if value.candidate == informative.candidate
        and value.switch_probability == informative.switch_probability
        and value.sensing_timing == informative.sensing_timing
        and value.information_arm == InformationArm.SHAM
    )
    beta = beta_for(config, "stage-b", 0)
    informative_initial = initial_for(config, "stage-b", 0, informative, 0)
    sham_initial = initial_for(config, "stage-b", 0, sham, 0)
    informative_seeds = process_seeds(config, "stage-b", informative, 0, 0)
    sham_seeds = process_seeds(config, "stage-b", sham, 0, 0)
    info_environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, informative, 0, "stage-b"),
        beta,
        informative_initial,
        *informative_seeds,
        thresholds=ObservationThresholds(),
    )
    sham_environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, sham, 0, "stage-b"),
        beta,
        sham_initial,
        *sham_seeds,
        thresholds=ObservationThresholds(),
    )
    info_regime_before = int(info_environment.regime)
    info_composition_before = info_environment.composition.copy()
    info_cue = info_environment.sense_current()
    sham_cue = sham_environment.sense_current()
    checks.append(
        _check(
            "same_cycle_sensor_does_not_advance_process",
            info_regime_before == int(info_environment.regime)
            and np.array_equal(info_composition_before, info_environment.composition),
            cue=info_cue,
        )
    )
    info_step = info_environment.step_compound(int(Action.ADAPT_A), sensed=True)
    sham_step = sham_environment.step_compound(int(Action.ADAPT_A), sensed=True)
    checks.append(
        _check(
            "informative_and_sham_share_exact_physical_stream",
            np.array_equal(informative_initial, sham_initial)
            and informative_seeds == sham_seeds
            and _physical_result_equal(info_step, sham_step),
            informative_cue=info_cue,
            sham_cue=sham_cue,
        )
    )

    cloned = clone_environment(info_environment)
    original_composition = info_environment.composition.copy()
    cloned.step(int(Action.WAIT))
    checks.append(
        _check(
            "environment_clone_is_independent",
            np.array_equal(info_environment.composition, original_composition),
        )
    )

    data = _synthetic_data(max(2, min(config.ensemble_members, 4)))
    model_a = fit_hybrid_model(
        data,
        components=min(config.clr_components, 4),
        members=max(2, min(config.ensemble_members, 4)),
        ridge_grid=RIDGE_GRID,
        rff_widths=config.rff_widths,
        rff_seed=18_711,
    )
    model_b = fit_hybrid_model(
        data,
        components=min(config.clr_components, 4),
        members=max(2, min(config.ensemble_members, 4)),
        ridge_grid=RIDGE_GRID,
        rff_widths=config.rff_widths,
        rff_seed=18_711,
    )
    checks.append(
        _check(
            "nonlinear_model_and_full_svd_are_bitwise_deterministic",
            model_digest(model_a) == model_digest(model_b),
            digest=model_digest(model_a),
            rff_width=model_a.rff_width,
        )
    )

    belief = np.asarray((0.45, 0.45, 0.10))
    delayed = expected_regime_information(belief, 0.25, 0.05, 0.98, transition=True)
    same_cycle = expected_regime_information(
        belief, 0.25, 0.05, 0.98, transition=False
    )
    sham_information = expected_regime_information(
        belief, 0.25, 0.05, 0.50, transition=False
    )
    branches = [posterior_for_cue(belief, cue, 0.98) for cue in range(4)]
    checks.append(
        _check(
            "information_and_contingent_branches_are_explicit",
            0.0 <= sham_information < same_cycle <= 1.0
            and 0.0 <= delayed <= 1.0
            and not np.array_equal(branches[1], branches[2]),
            delayed=delayed,
            same_cycle=same_cycle,
            sham=sham_information,
        )
    )

    schedule = np.asarray((0, 3, 1, 2, 3, 0, 1, 2), dtype=np.int8)
    yoked = exact_multiset_yoke(schedule, 18_714)
    checks.append(
        _check(
            "legacy_timing_yoke_utility_remains_exact",
            np.array_equal(
                np.bincount(schedule, minlength=4),
                np.bincount(yoked, minlength=4),
            ),
        )
    )
    return {
        "schema": "fep-ph18-validation-v1",
        "checks": checks,
        "all_passed": all(value["passed"] for value in checks),
    }


__all__ = ("_synthetic_data", "validate_experiment")
