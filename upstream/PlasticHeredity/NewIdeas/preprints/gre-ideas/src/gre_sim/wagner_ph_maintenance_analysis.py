"""Registered inference and evidence-tier ranking for Adaptive Maintenance v1."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import canonical_digest, read_json
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_maintenance_config import (
    EMERGENT_CANDIDATES,
    ENGINEERED_CANDIDATES,
    MAINTENANCE_FORMAT,
    MaintenanceSpec,
    arm_settings,
    evidence_tier,
    matched_ecology_control,
    matched_individual_control,
    matched_single_control,
)


ANALYSIS_FORMAT = f"{MAINTENANCE_FORMAT}-analysis"


def _seed(spec: MaintenanceSpec, phase: str, domain: str) -> str:
    if phase == "development":
        return spec.audit_seed if domain == "audit" else spec.pedigree_seed
    return canonical_digest((spec.confirmation_seed, domain))


def _finite(value: Any, fallback: float = float("-inf")) -> float:
    return fallback if value is None else float(value)


def _summaries(
    rows: list[dict[str, Any]], spec: MaintenanceSpec, phase: str
) -> dict[str, Any]:
    kernel = spec.kernel(confirmation=phase == "confirmation")
    summaries: dict[str, Any] = {}
    for arm in sorted({str(row["arm"]) for row in rows}):
        selected = [row for row in rows if row["arm"] == arm]
        effects = {
            str(row["population_index"]): population_effects(row, kernel)
            for row in selected
        }
        temporal: dict[str, dict[str, float]] = {}
        morphology: dict[str, dict[str, float]] = {}
        for row in selected:
            task = str(row["population_index"])
            cell = next(
                value
                for value in row["cells"]
                if abs(float(value["persistence"]) - 0.9) < 1e-12
                and abs(float(value["cue_fraction"])) < 1e-12
            )
            temporal[task] = {
                str(generation): float(
                    cell["conditions"]["natural"]["checkpoints"][str(generation)][
                        "correct_rate"
                    ]
                )
                - float(
                    cell["conditions"]["independent_history"]["checkpoints"][
                        str(generation)
                    ]["correct_rate"]
                )
                for generation in spec.lineage_checkpoints
            }
            interpreter = row["selected"]["interpreter"]
            node = interpreter.get("node_repair", ())
            morphology[task] = {
                "global_repair": float(interpreter.get("global_repair", 0.0)),
                "mean_node_repair": float(np.mean(node)) if node else 0.0,
                "maximum_node_repair": float(max(node)) if node else 0.0,
                "node_repair_dispersion": float(np.std(node)) if node else 0.0,
                "copy_count": float(interpreter["copy_count"]),
                "median_decoder": float(interpreter["decoder"] == "median"),
            }
        summaries[arm] = {
            "populations": len(selected),
            "effects": effects,
            "temporal_information": temporal,
            "morphology": morphology,
            "intervals": {
                field: _interval(
                    (value[field] for value in effects.values()),
                    _seed(spec, phase, "audit"),
                    f"maintenance-{phase}.{arm}.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in next(iter(effects.values()))
            },
            "morphology_intervals": {
                field: _interval(
                    (value[field] for value in morphology.values()),
                    _seed(spec, phase, "audit"),
                    f"maintenance-{phase}.{arm}.morphology.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in next(iter(morphology.values()))
            },
        }
    return summaries


def _absolute_checks(summary: dict[str, Any], spec: MaintenanceSpec) -> dict[str, bool]:
    intervals = summary["intervals"]

    def positive(name: str, threshold: float) -> bool:
        value = intervals[name]
        return bool(
            value["mean"] is not None
            and float(value["mean"]) >= threshold
            and float(value["lower"]) > 0.0
        )

    decoder = [
        float(value["decoder_balanced_accuracy"])
        for value in summary["effects"].values()
    ]
    return {
        "natural_minus_zero": positive("natural_minus_zero", spec.natural_zero_gate),
        "information_high": positive("information_high", spec.information_gate),
        "predictability_interaction": positive(
            "predictability_interaction", spec.predictability_interaction_gate
        ),
        "low_predictability_is_harmful": bool(
            intervals["information_low"]["mean"] is not None
            and float(intervals["information_low"]["mean"])
            <= spec.low_predictability_mean_gate
        ),
        "opposite_donor_following": positive("opposite_donor_following", spec.donor_gate),
        "reader_dependence": positive("reader_dependence", spec.reader_gate),
        "renewal_dependence": positive("renewal_dependence", spec.renewal_gate),
        "history_decoding": bool(
            decoder
            and float(np.mean(decoder)) >= spec.decoder_gate
            and sum(value > 0.5 for value in decoder) >= math.ceil(0.8 * len(decoder))
        ),
    }


def _paired_effect(
    left: dict[str, Any],
    right: dict[str, Any],
    field: str,
    spec: MaintenanceSpec,
    phase: str,
    label: str,
) -> dict[str, Any]:
    if set(left) != set(right):
        raise ValueError("adaptive-maintenance audit contrast is not task paired")
    values = {key: float(left[key][field]) - float(right[key][field]) for key in left}
    return {
        "field": field,
        "task_values": values,
        "interval": _interval(
            values.values(),
            _seed(spec, phase, "audit"),
            f"maintenance-{phase}.{label}.{field}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _pedigree_mode(pedigree: dict[str, Any], arm: str, mode: str = "natural") -> dict[str, Any]:
    return pedigree["arms"][arm]["modes"][mode]


def _retention_contrast(
    left: dict[str, Any],
    right: dict[str, Any],
    distance: int,
    spec: MaintenanceSpec,
    phase: str,
    label: str,
) -> dict[str, Any]:
    left_values = left["distances"][str(distance)]["task_retention"]
    right_values = right["distances"][str(distance)]["task_retention"]
    if set(left_values) != set(right_values):
        raise ValueError("adaptive-maintenance pedigree contrast is not task paired")
    values = {
        key: float(left_values[key]) - float(right_values[key]) for key in left_values
    }
    return {
        "distance": distance,
        "task_values": values,
        "interval": _interval(
            values.values(),
            _seed(spec, phase, "pedigree"),
            f"maintenance-{phase}.{label}.d{distance}.retention",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _interval_pass(value: dict[str, Any], threshold: float) -> bool:
    interval = value["interval"]
    return bool(
        interval["mean"] is not None
        and float(interval["mean"]) >= threshold
        and float(interval["lower"]) > 0.0
    )


def _mechanism_attribution(
    candidate: str,
    pedigree: dict[str, Any],
    spec: MaintenanceSpec,
    phase: str,
) -> dict[str, Any]:
    architecture = str(arm_settings(candidate)["architecture"])
    natural = _pedigree_mode(pedigree, candidate)
    contrasts: dict[str, Any] = {}
    checks: dict[str, bool] = {}

    def add(name: str, mode: str, threshold: float) -> None:
        contrast = _retention_contrast(
            natural,
            _pedigree_mode(pedigree, candidate, mode),
            4,
            spec,
            phase,
            f"{candidate}.natural-minus-{mode}",
        )
        contrasts[name] = contrast
        checks[f"{name}_at_least_{threshold:.2f}_with_positive_lower"] = _interval_pass(
            contrast, threshold
        )

    if architecture == "global_repair":
        add("repair_on_minus_off", "repair_off", spec.mechanism_gate)
    elif architecture == "node_repair":
        add("repair_on_minus_off", "repair_off", spec.mechanism_gate)
        add("localized_minus_uniform", "uniform_repair", spec.localization_gate)
        add("localized_minus_shuffled", "shuffled_repair", spec.localization_gate)
    elif architecture == "duplication":
        add("redundancy_minus_single_copy", "single_copy", spec.mechanism_gate)
        add("independent_minus_concerted", "concerted", spec.mechanism_gate)
    elif architecture == "median3":
        add("median_minus_mean_decoder", "mean_decoder", spec.mechanism_gate)
        add("independent_minus_concerted", "concerted", spec.mechanism_gate)
    return {
        "applicable": bool(checks),
        "checks": checks,
        "contrasts": contrasts,
        "passes": all(checks.values()),
    }


def _emergence_checks(candidate: str, summary: dict[str, Any]) -> dict[str, bool]:
    architecture = str(arm_settings(candidate)["architecture"])
    intervals = summary["morphology_intervals"]
    if architecture == "global_repair" and arm_settings(candidate)["initialization"] == "zero":
        return {"repair_evolved_from_zero": _finite(intervals["global_repair"]["mean"], 0.0) > 0.05}
    if architecture == "node_repair":
        return {
            "node_repair_evolved_from_zero": _finite(intervals["mean_node_repair"]["mean"], 0.0) > 0.05,
            "node_repair_became_nonuniform": _finite(intervals["node_repair_dispersion"]["mean"], 0.0) > 0.01,
        }
    if architecture == "duplication":
        return {"copy_number_evolved_above_one": _finite(intervals["copy_count"]["mean"], 1.0) > 1.25}
    return {}


def _temporal_summary(
    summary: dict[str, Any], spec: MaintenanceSpec, phase: str, candidate: str
) -> dict[str, Any]:
    task_values = summary["temporal_information"]
    intervals = {
        str(generation): _interval(
            (value[str(generation)] for value in task_values.values()),
            _seed(spec, phase, "audit"),
            f"maintenance-{phase}.{candidate}.temporal.f{generation}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        )
        for generation in spec.lineage_checkpoints
    }
    first = spec.lineage_checkpoints[0]
    last = spec.lineage_checkpoints[-1]
    first_mean = _finite(intervals[str(first)]["mean"], 0.0)
    last_mean = _finite(intervals[str(last)]["mean"], 0.0)
    return {
        "checkpoints": intervals,
        "first_checkpoint": first,
        "final_checkpoint": last,
        "final_over_first_mean_fraction": last_mean / first_mean if first_mean > 0.0 else None,
    }


def _decision(
    candidate: str,
    summaries: dict[str, Any],
    absolute: dict[str, Any],
    pedigree: dict[str, Any],
    spec: MaintenanceSpec,
    phase: str,
) -> dict[str, Any]:
    control = matched_single_control(candidate)
    candidate_effects = summaries[candidate]["effects"]
    control_effects = summaries[control]["effects"]
    information_advantage = _paired_effect(
        candidate_effects,
        control_effects,
        "information_high",
        spec,
        phase,
        f"{candidate}-minus-{control}",
    )
    performance_values = {
        key: float(control_effects[key]["natural_heldout_performance"])
        - float(candidate_effects[key]["natural_heldout_performance"])
        for key in candidate_effects
    }
    performance_loss = {
        "positive_means_candidate_is_worse": True,
        "task_values": performance_values,
        "interval": _interval(
            performance_values.values(),
            _seed(spec, phase, "audit"),
            f"maintenance-{phase}.{candidate}.performance-loss",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }
    candidate_pedigree = _pedigree_mode(pedigree, candidate)
    control_pedigree = _pedigree_mode(pedigree, control)
    retention = {
        distance: _finite(
            candidate_pedigree["distances"][str(distance)]["retention_interval"]["mean"],
            0.0,
        )
        for distance in spec.pedigree_depths
    }
    information = {
        distance: _finite(
            candidate_pedigree["distances"][str(distance)]["information_interval"]["mean"],
            0.0,
        )
        for distance in spec.pedigree_depths
    }
    d1_advantage = _retention_contrast(
        candidate_pedigree,
        control_pedigree,
        1,
        spec,
        phase,
        f"{candidate}-minus-{control}",
    )
    d4_advantage = _retention_contrast(
        candidate_pedigree,
        control_pedigree,
        4,
        spec,
        phase,
        f"{candidate}-minus-{control}",
    )
    temporal = _temporal_summary(summaries[candidate], spec, phase, candidate)
    slope = candidate_pedigree["task_centered_immediate_parent_offspring_slope"]
    core_checks = {
        **{f"causal_{name}": bool(value) for name, value in absolute[candidate]["checks"].items()},
        "distance_one_retention_at_least_0_70": retention[1] >= spec.retention_mean_gate,
        "distance_one_lower_above_0_50": _finite(candidate_pedigree["distances"]["1"]["retention_interval"]["lower"]) > spec.retention_lower_gate,
        "distance_two_retention_at_least_0_55": retention[2] >= spec.distance_two_gate,
        "distance_four_retention_at_least_0_35": retention[4] >= spec.distance_four_gate,
        "positive_parent_offspring_slope": slope is not None and float(slope) > 0.0,
        "information_advantage_at_least_0_08": _finite(information_advantage["interval"]["mean"]) >= spec.information_advantage_gate,
        "information_advantage_lower_above_zero": _finite(information_advantage["interval"]["lower"]) > 0.0,
        "distance_four_advantage_at_least_0_20": _finite(d4_advantage["interval"]["mean"]) >= spec.distance_four_advantage_gate,
        "distance_four_advantage_lower_above_zero": _finite(d4_advantage["interval"]["lower"]) > 0.0,
        "heldout_performance_loss_at_most_0_05": _finite(performance_loss["interval"]["mean"], float("inf")) <= spec.performance_loss_gate,
        "information_positive_at_every_mutation_distance": all(information[value] > 0.0 for value in spec.pedigree_depths),
        "final_temporal_information_at_least_half_of_f1": temporal["final_over_first_mean_fraction"] is not None and float(temporal["final_over_first_mean_fraction"]) >= spec.f12_fraction_gate,
    }
    emergence = _emergence_checks(candidate, summaries[candidate])
    ecology_control = matched_ecology_control(candidate)
    ecology = None
    ecology_checks: dict[str, bool] = {}
    if ecology_control is not None and ecology_control in pedigree["arms"]:
        ecology = _retention_contrast(
            candidate_pedigree,
            _pedigree_mode(pedigree, ecology_control),
            4,
            spec,
            phase,
            f"{candidate}-minus-{ecology_control}",
        )
        ecology_checks["predictable_ecology_improves_distance_four_retention"] = _interval_pass(
            ecology, spec.localization_gate
        )
    individual_control = matched_individual_control(candidate)
    individual_selection = None
    if individual_control is not None and individual_control in pedigree["arms"]:
        individual_selection = _retention_contrast(
            candidate_pedigree,
            _pedigree_mode(pedigree, individual_control),
            4,
            spec,
            phase,
            f"{candidate}-minus-{individual_control}",
        )
    mechanism = _mechanism_attribution(candidate, pedigree, spec, phase)
    attribution_checks = {
        **emergence,
        **ecology_checks,
        **mechanism["checks"],
    }
    core_passes = all(core_checks.values())
    attribution_passes = all(attribution_checks.values())
    return {
        "candidate": candidate,
        "ordinary_control": control,
        "evidence_tier": evidence_tier(candidate),
        "core_checks": core_checks,
        "core_gate_count": sum(core_checks.values()),
        "core_gate_total": len(core_checks),
        "core_passes": core_passes,
        "emergence_checks": emergence,
        "mechanism_attribution": mechanism,
        "ecology_specificity": ecology,
        "individual_vs_multihorizon_selection": individual_selection,
        "attribution_checks": attribution_checks,
        "attribution_passes": attribution_passes,
        "passes": core_passes and attribution_passes,
        "absolute_ph": absolute[candidate],
        "information_advantage": information_advantage,
        "distance_one_retention_advantage": d1_advantage,
        "distance_four_retention_advantage": d4_advantage,
        "heldout_performance_loss": performance_loss,
        "retention_by_distance": retention,
        "information_by_distance": information,
        "temporal_information": temporal,
        "pedigree": candidate_pedigree,
        "morphology": summaries[candidate]["morphology_intervals"],
    }


def _rank(candidates: Iterable[str], decisions: dict[str, Any]) -> list[str]:
    return sorted(
        (name for name in candidates if name in decisions),
        key=lambda name: (
            -int(decisions[name]["passes"]),
            -int(decisions[name]["core_gate_count"]),
            -sum(decisions[name]["attribution_checks"].values()),
            -_finite(decisions[name]["pedigree"]["distances"]["4"]["retention_interval"]["lower"]),
            -_finite(decisions[name]["information_advantage"]["interval"]["mean"]),
            name,
        ),
    )


def nominate(decisions: dict[str, Any]) -> dict[str, Any]:
    emergent = _rank(EMERGENT_CANDIDATES, decisions)
    engineered = _rank(ENGINEERED_CANDIDATES, decisions)
    passing_emergent = [name for name in emergent if decisions[name]["passes"]]
    passing_engineered = [name for name in engineered if decisions[name]["passes"]]
    candidates = tuple((passing_emergent[:1] + passing_engineered[:1]))
    return {
        "nominated": bool(candidates),
        "candidates": list(candidates),
        "emergent_candidate": passing_emergent[0] if passing_emergent else None,
        "engineered_candidate": passing_engineered[0] if passing_engineered else None,
        "rankings": {"emergent": emergent, "engineered": engineered},
        "confirmation_authorized": False,
        "authorization_rule": "confirmation requires a separate explicit --authorize-confirmation invocation",
        "selection_rule": "pass all core and attribution gates, then registered gate-count and interval tie-breakers",
    }


def analyze_maintenance_phase(
    audit_rows: list[dict[str, Any]],
    pedigree: dict[str, Any],
    spec: MaintenanceSpec,
    phase: str,
    *,
    forced_candidates: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if phase not in {"development", "confirmation"}:
        raise ValueError("unknown adaptive-maintenance analysis phase")
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    summaries = _summaries(audit_rows, spec, phase)
    if any(value["populations"] != task_count for value in summaries.values()):
        raise ValueError("adaptive-maintenance audit is incomplete or not task paired")
    if "mh_single_rho90" not in summaries or "mh_single_rho90" not in pedigree["arms"]:
        raise ValueError("adaptive-maintenance ordinary control is missing")
    absolute = {
        arm: {
            "checks": _absolute_checks(summary, spec),
            "passes": all(_absolute_checks(summary, spec).values()),
            "information_high_mean": summary["intervals"]["information_high"]["mean"],
        }
        for arm, summary in summaries.items()
    }
    candidates = (
        tuple(forced_candidates)
        if forced_candidates is not None
        else tuple(
            name
            for name in EMERGENT_CANDIDATES + ENGINEERED_CANDIDATES
            if name in summaries
        )
    )
    if any(name not in summaries or name not in pedigree["arms"] for name in candidates):
        raise ValueError("adaptive-maintenance candidate evidence is incomplete")
    decisions = {
        name: _decision(name, summaries, absolute, pedigree, spec, phase)
        for name in candidates
    }
    if phase == "development":
        nomination = nominate(decisions)
        confirmation = None
    else:
        if forced_candidates is None or not forced_candidates:
            raise ValueError("confirmation requires candidates frozen before fresh tasks")
        nomination = {
            "nominated": True,
            "candidates": list(forced_candidates),
            "selection_does_not_use_confirmation_results": True,
        }
        confirmation = {
            "candidate_passes": {name: decisions[name]["passes"] for name in candidates},
            "all_candidates_pass": all(decisions[name]["passes"] for name in candidates),
        }
    result = {
        "format": ANALYSIS_FORMAT,
        "phase": phase,
        "inferential_unit": "paired founder task",
        "ordinary_control": "mh_single_rho90",
        "summaries": summaries,
        "absolute_ph_by_arm": absolute,
        "candidate_decisions": decisions,
        "nomination": nomination,
        "confirmation": confirmation,
        "core_and_mechanism_attribution_gates_are_separate": True,
        "emergent_and_engineered_evidence_tiers_are_not_pooled": True,
        "claim_boundary": (
            "This simulated study tests whether observable selection can evolve or maintain "
            "a Wagner-GRN interpreter that preserves causally readable plastic-history "
            "information. Dormant-start mechanisms are emergence evidence; seeded repair "
            "and fixed median triplication are engineered sufficiency controls. Neither "
            "tier identifies a natural molecular carrier or demonstrates plastic heredity "
            "in living cells."
        ),
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def render_report(
    development: dict[str, Any], diagnosis: dict[str, Any], confirmation: dict[str, Any] | None = None
) -> str:
    lines = ["# Wagner PH Adaptive Maintenance v1", "", "## Sealed-parent diagnosis", ""]
    repair = diagnosis["continuous_repair_insurance"]["by_distance"]["4"]
    lines.append(
        "- Architecture-v1 repair-on minus repair-off distance-four information effect: "
        f"{repair['repair_information_effect']['interval']['mean']}."
    )
    predictor = diagnosis["network_predictor"]
    lines.append(
        "- Leave-one-task-out structural predictor correlation: "
        f"{predictor['leave_one_task_out_correlation']}."
    )
    lines.extend(["", "## Development", ""])
    nomination = development["nomination"]
    lines.append(f"- Confirmation candidates passing every frozen gate: {nomination['candidates']}.")
    lines.append("- Confirmation remains unauthorized until a separate explicit command.")
    for name, value in development["candidate_decisions"].items():
        failed_core = [key for key, passed in value["core_checks"].items() if not passed]
        failed_attribution = [key for key, passed in value["attribution_checks"].items() if not passed]
        lines.append(
            f"- `{name}` ({value['evidence_tier']}): "
            f"{value['core_gate_count']}/{value['core_gate_total']} core gates; "
            f"overall {'PASS' if value['passes'] else 'FAIL'}; "
            f"failed core: {failed_core or 'none'}; failed attribution: {failed_attribution or 'none'}."
        )
    if confirmation is not None:
        lines.extend(["", "## Explicitly authorized fresh confirmation", ""])
        for name, passed in confirmation["confirmation"]["candidate_passes"].items():
            lines.append(f"- `{name}`: {'PASS' if passed else 'FAIL'}.")
    lines.extend(["", "## Claim boundary", "", development["claim_boundary"], ""])
    return "\n".join(lines)


__all__ = ("analyze_maintenance_phase", "nominate", "render_report")
