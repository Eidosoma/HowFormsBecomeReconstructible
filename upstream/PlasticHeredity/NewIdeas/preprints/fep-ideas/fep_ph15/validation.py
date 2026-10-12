from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from fep_lab.integrity import seal_directory, write_json
from fep_lab.reference import ReferenceBackend
from fep_ph1.gard import generate_beta, generate_initial_composition
from fep_ph1.models import adjust_policy_costs
from fep_ph1.validation import NEUTRAL_REFERENCE, _neutral_digest

from .analysis import safe_spearman
from .config import ExperimentConfig, regime_specs
from .environment import EnvironmentDesign, GardGoalAlignmentEnvironment, apply_molecular_dose
from .inference import FastInferenceBackend
from .models import ModelCounts, action_costs, model_from_counts, with_preferences
from .screen import choose_actuator, screen_seed_domains, select_challenges
from .simulation import controller_for, run_episode
from .types import (
    Action,
    ActionChannel,
    ActuatorSetting,
    ChallengeTier,
    ControllerName,
    EnvironmentFamily,
    ObservationThresholds,
    PreferenceMode,
)
from .worker import CellSpec, ConditionSpec, _variants, cohort_seed_domains


def _check(name: str, passed: bool, **evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def _counts() -> ModelCounts:
    counts = ModelCounts.empty()
    for state in range(9):
        observation = (state % 4, state % 3, state % 3, state % 4)
        counts.add_initial(state, observation)
        for action in range(4):
            counts.add_transition(state, action, (state + action + 1) % 9, observation)
    return counts


def _design(config: ExperimentConfig, channel: ActionChannel, dose: int = 1) -> EnvironmentDesign:
    return EnvironmentDesign(
        EnvironmentFamily.CATALYTIC,
        channel,
        regime_specs()[0],
        "02",
        15_801,
        15_802,
        150,
        ActuatorSetting("direct", dose, "NON_ACTIONABLE", 0.0, 0.0),
    )


def validate_experiment(
    config: ExperimentConfig, output: Path, source_digest: str | None = None
) -> dict[str, Any]:
    config.validate()
    checks: list[dict[str, Any]] = []
    for candidate in ("02", "03"):
        observed = _neutral_digest(config, candidate)
        checks.append(_check(f"neutral_retained_identity_{candidate}", observed == NEUTRAL_REFERENCE[candidate], record_digest=observed[0], rng_digest=observed[1]))

    beta = generate_beta(config.gard, np.random.default_rng(15_803))
    initial = generate_initial_composition(config.gard, np.random.default_rng(15_804))
    uptake = GardGoalAlignmentEnvironment(config, _design(config, ActionChannel.UPTAKE), beta, initial, 15_805, 15_806, 15_807)
    uptake.regime = 0
    normal = {action: uptake.exposure_multiplier(int(action)) for action in Action}
    uptake.regime = 2
    shock = {action: uptake.exposure_multiplier(int(action)) for action in Action}
    checks.append(_check(
        "uptake_exposure_ordering_and_shock",
        normal[Action.ADAPT_A] > normal[Action.WAIT] > normal[Action.ADAPT_B]
        and normal[Action.SAMPLE] < normal[Action.WAIT]
        and shock[Action.WAIT] == 0.50 and shock[Action.ADAPT_A] == 0.40
        and shock[Action.SAMPLE] == 0.475,
        normal={str(key): value for key, value in normal.items()},
        shock={str(key): value for key, value in shock.items()},
    ))

    scores = np.linspace(-1.0, 1.0, config.gard.n_types)
    molecular, edits = apply_molecular_dose(initial, scores, 8)
    molecular_again, edits_again = apply_molecular_dose(initial, scores, 8)
    checks.append(_check(
        "molecular_dose_mass_conservation_and_ties",
        int(molecular.sum()) == int(initial.sum()) and np.all(molecular >= 0)
        and len(edits) == 8 and np.array_equal(molecular, molecular_again)
        and edits == edits_again,
        substitutions=len(edits), l1_change=int(np.abs(molecular - initial).sum()),
    ))

    synthetic_growth = np.asarray([[[[50, 70, 90, 110]], [[60, 80, 100, 130]]]], dtype=np.int32)
    synthetic_completed = np.ones_like(synthetic_growth, dtype=np.int8)
    first_selection = select_challenges(synthetic_growth, synthetic_completed)
    second_selection = select_challenges(synthetic_growth, synthetic_completed)
    settings = (
        ActuatorSetting("direct", 1, "NON_ACTIONABLE", 0.0, 0.0),
        ActuatorSetting("inverted", 1, "NON_ACTIONABLE", 0.0, 0.0),
    )
    non_actionable = choose_actuator(
        ActionChannel.UPTAKE, settings,
        np.asarray([[0.2, 0.2], [0.1, 0.1]]), np.asarray([0.3, 0.3]),
    )
    checks.append(_check(
        "deterministic_challenge_selection_and_retention",
        first_selection == second_selection
        and first_selection.transition_budget != first_selection.hard_budget
        and non_actionable.actionability == "NON_ACTIONABLE",
        transition_budget=first_selection.transition_budget,
        hard_budget=first_selection.hard_budget,
        label=non_actionable.actionability,
    ))

    seed_values = {**{f"screen.{key}": value for key, value in screen_seed_domains(config).items()}, **{f"cohort.{key}": value for key, value in cohort_seed_domains(config).items()}}
    checks.append(_check("screen_development_calibration_evaluation_seeds_disjoint", len(set(seed_values.values())) == len(seed_values), seeds=seed_values))

    balanced = model_from_counts(_counts(), config, PreferenceMode.BALANCED)
    growth = with_preferences(balanced, PreferenceMode.GROWTH, information_gain=True)
    objective_sources = " ".join(
        (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")
        for name in ("models.py", "controllers.py", "screen.py", "worker.py")
    ).lower()
    firewall = (
        np.array_equal(balanced.C[0], growth.C[0])
        and np.array_equal(balanced.C[1], np.asarray((-0.5, 0.0, 0.5)))
        and np.all(growth.C[1] == 0.0)
        and np.all(balanced.C[2] == 0.0) and np.all(balanced.C[3] == 0.0)
        and "strict8" not in objective_sources and "strict-8" not in objective_sources
        and "f12" not in objective_sources
    )
    checks.append(_check("preference_and_heldout_event_firewall", firewall))

    reference = ReferenceBackend()
    observation = (0, 0, 0, 0)
    inferred = reference.infer_states(balanced, observation, balanced.D)
    reference_policy = adjust_policy_costs(balanced, reference.score_policies(balanced, inferred.posterior), config)
    fast = FastInferenceBackend(balanced, action_costs(config, config.action_cost_adapt))
    fast_inferred = fast.infer_states(observation, balanced.D)
    fast_policy = fast.score_policies(fast_inferred.posterior)
    checks.append(_check(
        "inference_reference_agreement",
        np.allclose(inferred.posterior, fast_inferred.posterior, atol=1e-12, rtol=0.0)
        and np.allclose(reference_policy.neg_efe, fast_policy.neg_efe, atol=1e-12, rtol=0.0)
        and np.allclose(reference_policy.posterior, fast_policy.posterior, atol=1e-12, rtol=0.0),
        posterior_max_difference=float(np.max(np.abs(inferred.posterior - fast_inferred.posterior))),
        policy_max_difference=float(np.max(np.abs(reference_policy.posterior - fast_policy.posterior))),
    ))

    condition = ConditionSpec(
        "02", EnvironmentFamily.CATALYTIC, ActionChannel.UPTAKE,
        ChallengeTier.HARD, 0, 150,
        ActuatorSetting("direct", 1, "NON_ACTIONABLE", 0.0, 0.0),
    )
    cell = CellSpec(0, condition)
    variants = _variants(config, cell, balanced, balanced)
    lesion_controller = controller_for(ControllerName.ACTION_LESION, config, balanced, balanced, variants, config.action_cost_uptake)
    noop_controller = controller_for(ControllerName.NOOP, config, balanced, balanced, variants, config.action_cost_uptake)
    process = (15_808, 15_809, 15_810)
    lesion = run_episode(config, environment_design_for_validation(config, condition), beta, initial, ObservationThresholds(), ControllerName.ACTION_LESION, lesion_controller, process, 15_811)
    noop = run_episode(config, environment_design_for_validation(config, condition), beta, initial, ObservationThresholds(), ControllerName.NOOP, noop_controller, process, 15_812)
    physical_names = ("completed", "growth_steps", "similarity", "result_regime", "executed_actions", "parents", "compositions")
    exact = all(np.array_equal(lesion[name], noop[name], equal_nan=True) for name in physical_names)
    checks.append(_check("action_lesion_noop_physics_identity", exact and np.all(lesion["executed_actions"] == 0)))

    correlation = safe_spearman(np.ones(4), np.arange(4.0))
    checks.append(_check(
        "constant_statistics_are_labeled_null",
        correlation["rho"] is None and correlation["p_exploratory"] is None
        and correlation["undefined_reason"] == "constant_predictor",
        result=correlation,
    ))

    result = {
        "schema": "fep-ph15-validation-v1", "profile": config.profile,
        "source_digest": source_digest,
        "all_pass": all(check["passed"] for check in checks), "checks": checks,
        "claim_boundary": "Validation of an engineered goal-aligned active-inference/GARD coupling; not evidence of intrinsic GARD inference, inherited control, an emergent blanket, or prebiotic chemistry.",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "validation.json", result)
    seal_directory(output, ["validation.json"])
    return result


def environment_design_for_validation(config: ExperimentConfig, condition: ConditionSpec) -> EnvironmentDesign:
    return EnvironmentDesign(
        condition.family, condition.channel, condition.regime, condition.candidate,
        15_813, 15_814, condition.growth_budget, condition.actuator,
    )
