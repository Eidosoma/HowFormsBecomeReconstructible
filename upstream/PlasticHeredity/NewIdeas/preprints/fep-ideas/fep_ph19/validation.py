from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from fep_ph18.environment import GardGoalAlignmentEnvironment
from fep_ph18.hybrid_model import expected_regime_information, posterior_for_cue

from .causal_pomdp import fit_exact_model, model_digest
from .config import ExperimentConfig
from .data import (
    beta_for,
    cohort_seed_domains,
    development_conditions,
    environment_design,
    initial_for,
    process_seeds,
    stage_a_conditions,
    stage_b_conditions,
)
from .types import Action, InformationArm, ObservationThresholds, SensingTiming


def _check(name: str, passed: bool, **evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def _synthetic_cells() -> list[tuple[dict[str, np.ndarray], dict[str, Any]]]:
    cells = []
    for candidate in ("02", "03"):
        rows = 4 * 2 * 7
        matrix = np.repeat(np.arange(4, dtype=np.int32), 14)
        action = np.tile(np.arange(7, dtype=np.int16), 8)
        regime = np.repeat(np.tile(np.asarray((0, 1), dtype=np.int16), 7), 4)
        correct = np.asarray(
            [
                value in ((1, 5) if current == 0 else (2, 6))
                for value, current in zip(action, regime, strict=True)
            ],
            dtype=np.int16,
        )
        next_similarity = np.where(correct == 1, 0.96, 0.72)
        completed = np.where(correct == 1, 1, (action == 0).astype(np.int16))
        arrays = {
            "matrix_id": matrix,
            "episode": np.zeros(rows, dtype=np.int16),
            "step": np.tile(np.arange(14, dtype=np.int16), 4),
            "action": action,
            "current_regime": regime,
            "next_regime": regime.copy(),
            "current_growth": np.full(rows, 220, dtype=np.int32),
            "next_growth": np.where(correct == 1, 180, 390).astype(np.int32),
            "current_similarity": np.full(rows, 0.84),
            "next_similarity": next_similarity,
            "completed": completed,
        }
        cells.append(
            (
                arrays,
                {
                    "candidate": candidate,
                    "growth_budget": 420,
                },
            )
        )
    return cells


def validate_experiment(config: ExperimentConfig, screen_root: Path) -> dict[str, Any]:
    config.validate()
    development = development_conditions(screen_root)
    stage_a = stage_a_conditions(screen_root)
    stage_b = stage_b_conditions(screen_root)
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "frozen_factorials",
            len(development) == 12 and len(stage_a) == 6 and len(stage_b) == 16,
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
            "same_cycle_primary_delayed_control_only",
            sum(value.sensing_timing == SensingTiming.SAME_CYCLE for value in stage_b) == 12
            and sum(value.sensing_timing == SensingTiming.DELAYED for value in stage_b) == 4
            and {
                value.switch_probability
                for value in stage_b
                if value.sensing_timing == SensingTiming.DELAYED
            }
            == {0.15},
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
    info_initial = initial_for(config, "stage-b", 0, informative, 0)
    sham_initial = initial_for(config, "stage-b", 0, sham, 0)
    info_seeds = process_seeds(config, "stage-b", informative, 0, 0)
    sham_seeds = process_seeds(config, "stage-b", sham, 0, 0)
    info_environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, informative, 0, "stage-b"),
        beta,
        info_initial,
        *info_seeds,
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
    regime_before = int(info_environment.regime)
    composition_before = info_environment.composition.copy()
    info_environment.sense_current()
    checks.append(
        _check(
            "same_cycle_sensing_does_not_advance_physics",
            regime_before == int(info_environment.regime)
            and np.array_equal(composition_before, info_environment.composition),
        )
    )
    checks.append(
        _check(
            "information_arms_share_physical_streams",
            np.array_equal(info_initial, sham_initial) and info_seeds == sham_seeds,
        )
    )
    belief = np.asarray((0.45, 0.45, 0.10))
    informative_gain = expected_regime_information(
        belief, 0.15, 0.05, 0.98, transition=False
    )
    passive_gain = expected_regime_information(
        belief, 0.15, 0.05, 0.50, transition=False
    )
    checks.append(
        _check(
            "informative_increment_positive_sham_increment_zero",
            informative_gain > passive_gain and passive_gain - passive_gain == 0.0,
            informative_increment=informative_gain - passive_gain,
            sham_increment=0.0,
        )
    )
    branches = [posterior_for_cue(belief, cue, 0.98) for cue in range(4)]
    checks.append(
        _check(
            "exact_bayes_branches",
            np.allclose(branches[0], belief)
            and np.array_equal(branches[1], np.asarray((1.0, 0.0, 0.0)))
            and np.array_equal(branches[2], np.asarray((0.0, 1.0, 0.0))),
        )
    )
    first = fit_exact_model(_synthetic_cells(), config)
    second = fit_exact_model(_synthetic_cells(), config)
    checks.append(
        _check(
            "exact_causal_fit_replays_bitwise",
            model_digest(first) == model_digest(second),
            digest=model_digest(first),
        )
    )
    checks.append(
        _check(
            "resource_contract",
            config.workers <= 4
            and (
                config.profile != "full"
                or config.wall_time_limit_seconds == 8 * 60 * 60
            ),
            workers=config.workers,
            hard_wall=config.wall_time_limit_seconds,
        )
    )
    return {
        "schema": "fep-ph19-validation-v1",
        "checks": checks,
        "all_passed": all(value["passed"] for value in checks),
    }


__all__ = ("validate_experiment",)
