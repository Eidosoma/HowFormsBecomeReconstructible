from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from fep_ph15.environment import (
    EnvironmentDesign as LegacyDesign,
    GardGoalAlignmentEnvironment as LegacyEnvironment,
)
from fep_ph16.config import profile_config as ph16_profile_config

from .causal_model import TrainingData
from .config import RIDGE_GRID, ExperimentConfig
from .controllers import exact_multiset_yoke
from .data import (
    beta_for,
    cohort_seed_domains,
    environment_design,
    initial_for,
    process_seeds,
    stage_a_conditions,
    stage_b_conditions,
)
from .environment import (
    GardGoalAlignmentEnvironment,
    PlanningSeeds,
    environment_fingerprint,
    planning_clone,
)
from .hybrid_model import (
    expected_regime_information,
    fit_hybrid_model,
    model_digest,
)
from .types import Action, ObservationThresholds


def _check(name: str, passed: bool, **evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def _result_equal(left: Any, right: Any) -> bool:
    return (
        left.completed == right.completed
        and left.external_regime == right.external_regime
        and left.alignment_level == right.alignment_level
        and left.intended_action == right.intended_action
        and left.executed_action == right.executed_action
        and left.abstract_action_cost == right.abstract_action_cost
        and left.physical_action_cost == right.physical_action_cost
        and left.edit_remove == right.edit_remove
        and left.edit_add == right.edit_add
        and left.raw_observation == right.raw_observation
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


def _physical_result_equal(left: Any, right: Any) -> bool:
    """Compare all realized fields except the deliberately manipulated cue."""

    return (
        left.completed == right.completed
        and left.external_regime == right.external_regime
        and left.alignment_level == right.alignment_level
        and left.intended_action == right.intended_action
        and left.executed_action == right.executed_action
        and left.abstract_action_cost == right.abstract_action_cost
        and left.physical_action_cost == right.physical_action_cost
        and left.raw_observation.growth_steps
        == right.raw_observation.growth_steps
        and left.raw_observation.boundary_similarity
        == right.raw_observation.boundary_similarity
        and left.raw_observation.alignment_score
        == right.raw_observation.alignment_score
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


def _synthetic_data(members: int, rows_per_matrix: int = 16) -> TrainingData:
    rng = np.random.default_rng(17_701)
    rows = members * rows_per_matrix
    matrix_ids = np.repeat(np.arange(members, dtype=np.int32), rows_per_matrix)
    actions = np.tile(np.arange(4, dtype=np.int8), rows // 4)
    coarse = rng.normal(size=(rows, 51))
    clr = rng.normal(size=(rows, 100))
    clr -= clr.mean(axis=1, keepdims=True)
    rich = np.concatenate((clr, rng.normal(size=(rows, 52))), axis=1)
    base = rng.normal(size=(rows, 12))
    base[:, 0] = (rng.random(rows) > 0.25).astype(float)
    base[:, 1] = np.clip(rng.normal(0.5, 0.1, rows), 0.0, 1.0)
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
    stage_a = stage_a_conditions(screen_root)
    stage_b = stage_b_conditions(screen_root, 1.0)
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "factorials",
            len(stage_a) == 10 and len(stage_b) == 4,
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

    condition = next(
        value
        for value in stage_a
        if value.authority_scale == 1.0
        and value.tier == "hard"
        and value.volatility == "fast"
    )
    beta = beta_for(config, "stage-a", 0)
    initial = initial_for(config, "stage-a", 0, condition, 0)
    seeds = process_seeds(config, "stage-a", condition, 0, 0)
    design = environment_design(config, condition, 0, "stage-a")
    current = GardGoalAlignmentEnvironment(
        config,
        design,
        beta,
        initial,
        *seeds,
        thresholds=ObservationThresholds(),
    )
    legacy_config = replace(
        ph16_profile_config("smoke"),
        master_seed=config.master_seed,
        gard=config.gard,
    )
    legacy_design = LegacyDesign(
        design.family,
        design.channel,
        design.regime,
        design.candidate,
        design.partition_seed,
        design.permutation_seed,
        design.growth_budget,
        design.actuator,
    )
    legacy = LegacyEnvironment(
        legacy_config,
        legacy_design,
        beta,
        initial,
        *seeds,
        thresholds=ObservationThresholds(),
    )
    actions = (int(Action.ADAPT_A), int(Action.WAIT), int(Action.SAMPLE))
    compatible = True
    for action in actions:
        left, right = current.step(action), legacy.step(action)
        compatible = compatible and _result_equal(left, right)
        if not left.completed or not right.completed:
            break
    checks.append(_check("authority_one_matches_ph16_physics", compatible))

    zero = next(
        value
        for value in stage_a
        if value.authority_scale == 0.0
        and value.candidate == condition.candidate
    )
    zero_design = environment_design(config, zero, 0, "stage-a")
    zero_seeds = process_seeds(config, "stage-a", zero, 0, 0)
    wait_environment = GardGoalAlignmentEnvironment(
        config,
        zero_design,
        beta,
        initial,
        *zero_seeds,
        thresholds=ObservationThresholds(),
    )
    adapt_environment = GardGoalAlignmentEnvironment(
        config,
        zero_design,
        beta,
        initial,
        *zero_seeds,
        thresholds=ObservationThresholds(),
    )
    wait = wait_environment.step(int(Action.WAIT))
    adapt = adapt_environment.step(int(Action.ADAPT_A))
    checks.append(
        _check(
            "authority_zero_is_physical_noop",
            wait.completed == adapt.completed
            and wait.raw_observation == adapt.raw_observation
            and wait.physical_action_cost == adapt.physical_action_cost == 0.0
            and np.array_equal(wait.composition, adapt.composition)
            and (
                wait.parent is None
                or adapt.parent is not None
                and np.array_equal(wait.parent, adapt.parent)
            ),
        )
    )

    strong = next(
        value
        for value in stage_a
        if value.authority_scale == 1.5
        and value.candidate == condition.candidate
    )
    strong_environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, strong, 0, "stage-a"),
        beta,
        initial,
        *process_seeds(config, "stage-a", strong, 0, 0),
        thresholds=ObservationThresholds(),
    )
    exposures = [strong_environment.exposure_multiplier(action) for action in range(4)]
    checks.append(
        _check(
            "strengthened_authority_is_bounded",
            all(0.05 <= value <= 1.50 for value in exposures),
            exposures=exposures,
        )
    )

    planning_environment = GardGoalAlignmentEnvironment(
        config,
        design,
        beta,
        initial,
        *seeds,
        thresholds=ObservationThresholds(),
    )
    before = environment_fingerprint(planning_environment)
    planned = planning_clone(
        planning_environment, PlanningSeeds(17_711, 17_712, 17_713)
    )
    planned.step(int(Action.ADAPT_B))
    checks.append(
        _check(
            "planning_clone_does_not_mutate_evaluation",
            before == environment_fingerprint(planning_environment),
        )
    )

    data = _synthetic_data(max(2, min(config.ensemble_members, 4)))
    model_a = fit_hybrid_model(
        data,
        components=min(config.clr_components, 4),
        members=max(2, min(config.ensemble_members, 4)),
        ridge_grid=RIDGE_GRID,
    )
    model_b = fit_hybrid_model(
        data,
        components=min(config.clr_components, 4),
        members=max(2, min(config.ensemble_members, 4)),
        ridge_grid=RIDGE_GRID,
    )
    checks.append(
        _check(
            "hybrid_model_and_full_svd_are_deterministic",
            model_digest(model_a) == model_digest(model_b),
            digest=model_digest(model_a),
            solver=model_a.cross_validation,
        )
    )

    belief = np.asarray((0.45, 0.45, 0.10))
    passive = expected_regime_information(belief, 0.25, 0.05, 0.50)
    informative = expected_regime_information(belief, 0.25, 0.05, 0.98)
    sham = expected_regime_information(belief, 0.25, 0.05, 0.50)
    checks.append(
        _check(
            "information_manipulation_is_specific",
            0.0 <= passive == sham < informative <= 1.0,
            passive=passive,
            sham=sham,
            informative=informative,
        )
    )

    informative_condition = stage_b[0]
    sham_condition = next(
        value
        for value in stage_b
        if value.candidate == informative_condition.candidate
        and value.information_arm != informative_condition.information_arm
    )
    informative_initial = initial_for(
        config, "stage-b", 0, informative_condition, 0
    )
    sham_initial = initial_for(config, "stage-b", 0, sham_condition, 0)
    informative_seeds = process_seeds(
        config, "stage-b", informative_condition, 0, 0
    )
    sham_seeds = process_seeds(config, "stage-b", sham_condition, 0, 0)
    stage_b_beta = beta_for(config, "stage-b", 0)
    informative_environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, informative_condition, 0, "stage-b"),
        stage_b_beta,
        informative_initial,
        *informative_seeds,
        thresholds=ObservationThresholds(),
    )
    sham_environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, sham_condition, 0, "stage-b"),
        stage_b_beta,
        sham_initial,
        *sham_seeds,
        thresholds=ObservationThresholds(),
    )
    informative_sample = informative_environment.step(int(Action.SAMPLE))
    sham_sample = sham_environment.step(int(Action.SAMPLE))
    checks.append(
        _check(
            "informative_and_sham_share_exact_physical_stream",
            np.array_equal(informative_initial, sham_initial)
            and informative_seeds == sham_seeds
            and _physical_result_equal(informative_sample, sham_sample),
            informative_cue=informative_sample.raw_observation.cue,
            sham_cue=sham_sample.raw_observation.cue,
        )
    )

    schedule = np.asarray((0, 3, 1, 2, 3, 0, 1, 2), dtype=np.int8)
    yoked = exact_multiset_yoke(schedule, 17_714)
    checks.append(
        _check(
            "exact_action_multiset_yoke",
            np.array_equal(
                np.bincount(schedule, minlength=4),
                np.bincount(yoked, minlength=4),
            ),
        )
    )
    return {
        "schema": "fep-ph17-validation-v1",
        "checks": checks,
        "all_passed": all(value["passed"] for value in checks),
    }


__all__ = ("_synthetic_data", "validate_experiment")
