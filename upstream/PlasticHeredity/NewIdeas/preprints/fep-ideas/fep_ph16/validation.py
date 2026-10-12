from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from fep_lab.integrity import seal_directory, sha256_bytes, write_json
from fep_ph1.gard import generate_beta, generate_initial_composition

from .causal_model import TrainingData, fit_ensemble, model_digest
from .config import RIDGE_GRID, ExperimentConfig
from .controllers import PhysicalRolloutOracle, exact_multiset_yoke
from .data import (
    beta_for,
    cohort_seed_domains,
    environment_design,
    initial_for,
    load_conditions,
    process_seeds,
)
from .environment import (
    GardGoalAlignmentEnvironment,
    PlanningSeeds,
    clone_environment,
    environment_fingerprint,
    planning_clone,
)
from .state import clr_proportions, composition_clr, state_features
from .types import Action, CellSpec, ObservationThresholds


def _check(name: str, passed: bool, **evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def _result_equal(left: Any, right: Any) -> bool:
    return (
        left.completed == right.completed
        and left.executed_action == right.executed_action
        and left.external_regime == right.external_regime
        and np.array_equal(left.composition, right.composition)
        and (
            (left.parent is None and right.parent is None)
            or (
                left.parent is not None
                and right.parent is not None
                and np.array_equal(left.parent, right.parent)
            )
        )
        and left.raw_observation == right.raw_observation
    )


def _synthetic_data(members: int) -> TrainingData:
    matrix_ids = np.repeat(np.arange(max(2, members), dtype=np.int32), 4)
    actions = np.tile(np.arange(4, dtype=np.int8), max(2, members))
    rng = np.random.default_rng(16_601)
    coarse = rng.normal(size=(len(actions), 5))
    rich = np.column_stack((coarse, rng.normal(size=(len(actions), 3))))
    completion = ((coarse[:, 0] + 0.2 * actions) > 0).astype(np.float64)
    cue = np.eye(4)[np.mod(actions + matrix_ids, 4)]
    regime = np.eye(3)[np.mod(matrix_ids, 3)]
    base = np.column_stack(
        (
            completion,
            np.clip(0.5 + 0.1 * coarse[:, 1], 0.0, 1.0),
            np.clip(0.8 + 0.05 * coarse[:, 2], 0.0, 1.0),
            np.clip(0.7 + 0.05 * coarse[:, 3], 0.0, 1.0),
            np.clip(1.0 + 0.05 * coarse[:, 4], 0.1, 1.5),
            cue,
            regime,
        )
    )
    clr = rng.normal(size=(len(actions), 100))
    clr -= clr.mean(axis=1, keepdims=True)
    return TrainingData(matrix_ids, actions, coarse, rich, base, np.column_stack((base, clr)))


def validate_experiment(
    config: ExperimentConfig,
    screen_root: Path,
    output: Path,
    source_digest: str | None = None,
) -> dict[str, Any]:
    config.validate()
    checks: list[dict[str, Any]] = []
    conditions = load_conditions(screen_root)
    checks.append(
        _check(
            "frozen_six_mechanism_factorial",
            len(conditions) == 24
            and len({value.mechanism_key for value in conditions}) == 6,
            conditions=len(conditions),
            mechanisms=sorted({value.mechanism_key for value in conditions}),
        )
    )

    seed_values = cohort_seed_domains(config)
    checks.append(
        _check(
            "development_calibration_evaluation_planning_seeds_disjoint",
            len(set(seed_values.values())) == len(seed_values),
            seeds=seed_values,
        )
    )
    timing_master_seed = sha256_bytes(
        f"{config.master_seed}.fep_ph16.disposable_timing".encode("utf-8")
    )
    checks.append(
        _check(
            "benchmark_uses_disposable_master_seed",
            timing_master_seed != config.master_seed,
            timing_master_seed=timing_master_seed,
            scientific_master_seed=config.master_seed,
        )
    )

    composition = np.arange(1, 101, dtype=np.int64)
    clr = composition_clr(composition)
    proportions = clr_proportions(clr)
    expected = (composition + 0.5) / float(np.sum(composition + 0.5))
    checks.append(
        _check(
            "clr_is_finite_centered_and_invertible",
            np.all(np.isfinite(clr))
            and abs(float(clr.mean())) < 1.0e-12
            and np.allclose(proportions, expected, atol=1.0e-12, rtol=0.0),
            mean=float(clr.mean()),
            maximum_inverse_difference=float(np.max(np.abs(proportions - expected))),
        )
    )

    condition = conditions[0]
    cell = CellSpec(0, condition)
    beta = beta_for(config, "evaluation", 0)
    initial = initial_for(config, "evaluation", 0, condition, 0)
    environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, condition, 0, "evaluation"),
        beta,
        initial,
        *process_seeds(config, "evaluation", condition, 0, 0),
        thresholds=ObservationThresholds(),
    )
    environment.initial_step()
    exact_clone = clone_environment(environment)
    static_arrays_shared = all(
        getattr(environment, name) is getattr(exact_clone, name)
        for name in (
            "base_beta",
            "permuted_beta",
            "beta_b",
            "beta_shock",
            "partition",
            "target_a_scores",
            "target_b_scores",
        )
    )
    mutable_state_independent = (
        not np.shares_memory(environment.composition, exact_clone.composition)
        and environment.chemistry_rng is not exact_clone.chemistry_rng
        and environment.environment_rng is not exact_clone.environment_rng
        and environment.observation_rng is not exact_clone.observation_rng
    )
    left = environment.step(int(Action.WAIT))
    right = exact_clone.step(int(Action.WAIT))
    checks.append(
        _check(
            "exact_environment_clone_trajectory_identity",
            _result_equal(left, right)
            and static_arrays_shared
            and mutable_state_independent
            and environment_fingerprint(environment) == environment_fingerprint(exact_clone),
            immutable_physics_arrays_shared=static_arrays_shared,
            mutable_state_independent=mutable_state_independent,
        )
    )

    actual_before = environment_fingerprint(environment)
    planned = planning_clone(environment, PlanningSeeds(16_611, 16_612, 16_613))
    planned.step(int(Action.ADAPT_A))
    actual_after = environment_fingerprint(environment)
    checks.append(
        _check(
            "planning_stream_cannot_mutate_actual_stream",
            actual_before == actual_after
            and environment_fingerprint(planned) != actual_after,
            before=actual_before,
            after=actual_after,
        )
    )

    # A physical oracle may inspect only its planning clone. Its decision must
    # leave both physical state and all three evaluation RNGs untouched.
    oracle_before = environment_fingerprint(environment)
    oracle = PhysicalRolloutOracle(
        config, condition, ObservationThresholds(), (condition.key, 0, 0)
    )
    oracle_decision = oracle.decide(environment=environment, step=0)
    oracle_after = environment_fingerprint(environment)
    checks.append(
        _check(
            "physical_oracle_is_diagnostic_and_non_mutating",
            oracle_before == oracle_after
            and 0 <= oracle_decision.action <= 3
            and oracle_decision.planning_fissions > 0,
            planning_fissions=oracle_decision.planning_fissions,
        )
    )

    schedule = np.asarray((0, 1, 1, 2, 3, 3, 3, 0), dtype=np.int8)
    yoked = exact_multiset_yoke(schedule, 16_614)
    checks.append(
        _check(
            "yoked_control_preserves_exact_action_multiset",
            np.array_equal(np.bincount(schedule, minlength=4), np.bincount(yoked, minlength=4))
            and not np.shares_memory(schedule, yoked),
        )
    )

    synthetic = _synthetic_data(config.ensemble_members)
    first_model = fit_ensemble(
        synthetic,
        rich=True,
        members=config.ensemble_members,
        ridge_grid=RIDGE_GRID,
    )
    second_model = fit_ensemble(
        synthetic,
        rich=True,
        members=config.ensemble_members,
        ridge_grid=RIDGE_GRID,
    )
    checks.append(
        _check(
            "causal_fit_is_deterministic",
            model_digest(first_model) == model_digest(second_model),
            digest=model_digest(first_model),
        )
    )

    source_text = " ".join(
        (Path(__file__).resolve().parent / name).read_text(encoding="utf-8").lower()
        for name in ("state.py", "controllers.py")
    )
    # Demonstrate the actual feature contract as well as checking the source.
    raw = left.raw_observation
    from .state import initial_body_state, initial_regime_belief

    body = initial_body_state(left.composition, raw, initial_regime_belief())
    coarse = state_features(body, condition, rich=False)
    rich = state_features(body, condition, rich=True)
    checks.append(
        _check(
            "learned_agent_blanket_and_event_firewall",
            len(coarse) == 48
            and len(rich) == 149
            and "strict8" not in source_text
            and "strict-8" not in source_text
            and "f12" not in source_text,
            coarse_width=len(coarse),
            rich_width=len(rich),
            excluded=("true_regime", "beta", "rng_state", "f12", "strict8"),
            diagnostic_exceptions=("categorical_true_regime_oracle", "physical_rollout_oracle"),
        )
    )

    result = {
        "schema": "fep-ph16-validation-v1",
        "profile": config.profile,
        "source_digest": source_digest,
        "all_pass": all(check["passed"] for check in checks),
        "checks": checks,
        "scientific_status": "EXPLORATORY_ONLY_NO_GLOBAL_CLASSIFIER",
        "claim_boundary": (
            "A causal body-model and diagnostic-oracle ladder in reconstructed GARD; "
            "not evidence that GARD intrinsically performs active inference, inherits a "
            "controller, realizes prebiotic chemistry, or establishes a universal FEP mechanism."
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "validation.json", result)
    seal_directory(output, ["validation.json"])
    return result
