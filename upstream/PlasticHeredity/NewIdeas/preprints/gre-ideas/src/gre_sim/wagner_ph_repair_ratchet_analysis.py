"""Frozen analysis for Global Repair Ratchet v1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import canonical_digest, read_json
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_maintenance_analysis import _absolute_checks, _summaries
from .wagner_ph_maintenance_config import MaintenanceSpec
from .wagner_ph_repair_ratchet_config import (
    RATCHET_FORMAT,
    RepairRatchetSpec,
    RepairRoute,
)


ANALYSIS_FORMAT = f"{RATCHET_FORMAT}-analysis"


def _files(directory: Path) -> list[dict[str, Any]]:
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def _finite(value: Any, fallback: float = float("-inf")) -> float:
    return fallback if value is None else float(value)


def _paired_effect(
    left: dict[str, Any],
    right: dict[str, Any],
    field: str,
    spec: RepairRatchetSpec,
    label: str,
) -> dict[str, Any]:
    if set(left) != set(right):
        raise ValueError("repair-ratchet audit contrast is not task paired")
    values = {key: float(left[key][field]) - float(right[key][field]) for key in left}
    return {
        "field": field,
        "task_values": values,
        "interval": _interval(
            values.values(),
            spec.audit_seed,
            f"repair-ratchet.{label}.{field}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _retention_effect(
    left: dict[str, Any],
    right: dict[str, Any],
    spec: RepairRatchetSpec,
    label: str,
    distance: int = 4,
) -> dict[str, Any]:
    left_values = left["distances"][str(distance)]["task_retention"]
    right_values = right["distances"][str(distance)]["task_retention"]
    if set(left_values) != set(right_values):
        raise ValueError("repair-ratchet pedigree contrast is not task paired")
    values = {key: float(left_values[key]) - float(right_values[key]) for key in left_values}
    return {
        "distance": distance,
        "task_values": values,
        "interval": _interval(
            values.values(),
            spec.pedigree_seed,
            f"repair-ratchet.{label}.d{distance}.retention",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _temporal_summary(
    summary: dict[str, Any],
    spec: RepairRatchetSpec,
    base: MaintenanceSpec,
    route: str,
) -> dict[str, Any]:
    task_values = summary["temporal_information"]
    checkpoints = {
        str(generation): _interval(
            (value[str(generation)] for value in task_values.values()),
            spec.audit_seed,
            f"repair-ratchet.{route}.temporal.f{generation}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        )
        for generation in base.lineage_checkpoints
    }
    first = base.lineage_checkpoints[0]
    final = base.lineage_checkpoints[-1]
    first_mean = _finite(checkpoints[str(first)]["mean"], 0.0)
    final_mean = _finite(checkpoints[str(final)]["mean"], 0.0)
    return {
        "checkpoints": checkpoints,
        "first_checkpoint": first,
        "final_checkpoint": final,
        "final_over_first_mean_fraction": final_mean / first_mean if first_mean > 0 else None,
    }


def _dose_response(
    pedigree: dict[str, Any],
    spec: RepairRatchetSpec,
    route: str,
) -> dict[str, Any]:
    modes = {
        0.0: "repair_off",
        0.25: "repair_025",
        0.50: "repair_050",
        0.75: "repair_075",
        1.0: "natural",
    }
    task_values: dict[str, float] = {}
    monotone: dict[str, bool] = {}
    for task_index in range(spec.task_count):
        key = str(task_index)
        values = np.asarray(
            [
                pedigree["modes"][modes[scale]]["distances"]["4"]["task_retention"][key]
                for scale in spec.dose_scales
            ],
            dtype=float,
        )
        task_values[key] = float(np.polyfit(np.asarray(spec.dose_scales), values, 1)[0])
        monotone[key] = bool(np.all(np.diff(values) >= -1e-12))
    return {
        "task_slopes": task_values,
        "slope_interval": _interval(
            task_values.values(),
            spec.pedigree_seed,
            f"repair-ratchet.{route}.dose-slope",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "monotone_task_fraction": float(np.mean(list(monotone.values()))),
        "task_monotonicity": monotone,
        "dose_scales": list(spec.dose_scales),
    }


def _route_summary(
    route: RepairRoute,
    audit: Path,
    base: MaintenanceSpec,
) -> dict[str, Any]:
    summaries = _summaries(
        _files(audit / route.name / "populations"), base, "development"
    )
    if set(summaries) != {route.legacy_arm}:
        raise ValueError(f"repair-ratchet audit arm mismatch for {route.name}")
    return summaries[route.legacy_arm]


def analyze_repair_ratchet(
    spec: RepairRatchetSpec,
    evolution: Path,
    audit: Path,
    pedigree: Path,
    reference: Path,
) -> dict[str, Any]:
    spec.validate()
    base = spec.maintenance()
    summaries = {
        route.name: _route_summary(route, audit, base) for route in spec.routes
    }
    pedigrees = {
        route.name: read_json(pedigree / route.name / "analysis.json")
        for route in spec.routes
    }
    ordinary_summary = summaries["ordinary_mh"]
    ordinary_pedigree = pedigrees["ordinary_mh"]["modes"]["natural"]
    absolute = {
        route.name: {
            "checks": _absolute_checks(summaries[route.name], base),
            "information_high_mean": summaries[route.name]["intervals"]["information_high"]["mean"],
        }
        for route in spec.routes
    }
    for value in absolute.values():
        value["passes"] = all(value["checks"].values())

    decisions: dict[str, Any] = {}
    for route in spec.routes:
        if not route.has_repair:
            continue
        summary = summaries[route.name]
        route_pedigree = pedigrees[route.name]
        natural = route_pedigree["modes"]["natural"]
        repair_off = route_pedigree["modes"]["repair_off"]
        information_advantage = _paired_effect(
            summary["effects"],
            ordinary_summary["effects"],
            "information_high",
            spec,
            f"{route.name}-minus-ordinary",
        )
        performance_loss_values = {
            key: float(ordinary_summary["effects"][key]["natural_heldout_performance"])
            - float(summary["effects"][key]["natural_heldout_performance"])
            for key in summary["effects"]
        }
        performance_loss = {
            "positive_means_route_is_worse": True,
            "task_values": performance_loss_values,
            "interval": _interval(
                performance_loss_values.values(),
                spec.audit_seed,
                f"repair-ratchet.{route.name}.performance-loss",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
        }
        retention = {
            distance: _finite(
                natural["distances"][str(distance)]["retention_interval"]["mean"], 0.0
            )
            for distance in base.pedigree_depths
        }
        information = {
            distance: _finite(
                natural["distances"][str(distance)]["information_interval"]["mean"], 0.0
            )
            for distance in base.pedigree_depths
        }
        distance_four_advantage = _retention_effect(
            natural,
            ordinary_pedigree,
            spec,
            f"{route.name}-minus-ordinary",
        )
        repair_off_effect = _retention_effect(
            natural,
            repair_off,
            spec,
            f"{route.name}.natural-minus-repair-off",
        )
        dose = _dose_response(route_pedigree, spec, route.name)
        temporal = _temporal_summary(summary, spec, base, route.name)
        repair_interval = summary["morphology_intervals"]["global_repair"]
        slope = natural["task_centered_immediate_parent_offspring_slope"]
        core_checks = {
            **{
                f"causal_{name}": bool(value)
                for name, value in absolute[route.name]["checks"].items()
            },
            "distance_one_retention_at_least_0_70": retention[1] >= base.retention_mean_gate,
            "distance_one_lower_above_0_50": _finite(
                natural["distances"]["1"]["retention_interval"]["lower"]
            ) > base.retention_lower_gate,
            "distance_two_retention_at_least_0_55": retention[2] >= base.distance_two_gate,
            "distance_four_retention_at_least_0_35": retention[4] >= base.distance_four_gate,
            "positive_parent_offspring_slope": slope is not None and float(slope) > 0.0,
            "information_positive_at_every_mutation_distance": all(
                information[distance] > 0.0 for distance in base.pedigree_depths
            ),
            "final_temporal_information_at_least_half_of_f1": temporal[
                "final_over_first_mean_fraction"
            ]
            is not None
            and float(temporal["final_over_first_mean_fraction"]) >= base.f12_fraction_gate,
            "information_advantage_at_least_0_08": _finite(
                information_advantage["interval"]["mean"]
            ) >= spec.information_advantage_gate,
            "information_advantage_lower_above_zero": _finite(
                information_advantage["interval"]["lower"]
            ) > 0.0,
            "distance_four_advantage_at_least_0_20": _finite(
                distance_four_advantage["interval"]["mean"]
            ) >= spec.distance_four_advantage_gate,
            "distance_four_advantage_lower_above_zero": _finite(
                distance_four_advantage["interval"]["lower"]
            ) > 0.0,
            "heldout_performance_loss_at_most_0_05": _finite(
                performance_loss["interval"]["mean"], float("inf")
            ) <= base.performance_loss_gate,
        }
        attribution_checks = {
            "repair_on_minus_off_at_least_0_15_with_positive_lower": bool(
                _finite(repair_off_effect["interval"]["mean"]) >= spec.repair_off_gate
                and _finite(repair_off_effect["interval"]["lower"]) > 0.0
            ),
            "repair_dose_slope_at_least_0_10_with_positive_lower": bool(
                _finite(dose["slope_interval"]["mean"]) >= spec.dose_slope_gate
                and _finite(dose["slope_interval"]["lower"]) > 0.0
            ),
        }
        if route.zero_start:
            attribution_checks.update(
                {
                    "repair_evolved_from_zero_above_0_05": _finite(
                        repair_interval["mean"], 0.0
                    ) > spec.repair_emergence_gate,
                    "repair_evolved_from_zero_lower_above_zero": _finite(
                        repair_interval["lower"]
                    ) > 0.0,
                }
            )
        decisions[route.name] = {
            "route": route.name,
            "route_settings": route.to_dict(),
            "evidence_tier": route.evidence_tier,
            "zero_start": route.zero_start,
            "absolute_ph": absolute[route.name],
            "retention": retention,
            "information_by_distance": information,
            "temporal_information": temporal,
            "global_repair": repair_interval,
            "information_advantage": information_advantage,
            "distance_four_retention_advantage": distance_four_advantage,
            "heldout_performance_loss": performance_loss,
            "repair_on_minus_off": repair_off_effect,
            "repair_dose_response": dose,
            "parent_offspring_slope": slope,
            "core_checks": core_checks,
            "core_gate_count": sum(core_checks.values()),
            "core_gate_total": len(core_checks),
            "core_passes": all(core_checks.values()),
            "attribution_checks": attribution_checks,
            "attribution_gate_count": sum(attribution_checks.values()),
            "attribution_gate_total": len(attribution_checks),
            "attribution_passes": all(attribution_checks.values()),
            "passes": all(core_checks.values()) and all(attribution_checks.values()),
        }

    eligible = [value for value in decisions.values() if value["zero_start"]]
    ranked = sorted(
        eligible,
        key=lambda value: (
            -int(value["passes"]),
            -(value["core_gate_count"] + value["attribution_gate_count"]),
            -_finite(value["repair_on_minus_off"]["interval"]["mean"]),
            -_finite(value["repair_dose_response"]["slope_interval"]["mean"]),
            -_finite(value["information_advantage"]["interval"]["mean"]),
            value["route"],
        ),
    )
    passing = [value for value in ranked if value["passes"]]
    candidate = passing[0]["route"] if passing else None
    reference_analysis = read_json(reference / "development" / "analysis.json")
    reference_decisions = reference_analysis["candidate_decisions"]
    result = {
        "format": ANALYSIS_FORMAT,
        "inferential_unit": "paired founder task",
        "selection_contains_no_ph_information_intervention_or_gate_metric": True,
        "summaries": summaries,
        "absolute_ph_by_route": absolute,
        "pedigrees_by_route": pedigrees,
        "route_decisions": decisions,
        "reference_adaptive_maintenance": {
            "analysis_digest": reference_analysis["analysis_digest"],
            "repair_zero_standard_reference": reference_decisions["mh_global_zero_rho90"],
            "repair_seeded_reference": reference_decisions["mh_global_seeded_rho90"],
            "reference_is_not_pooled_with_new_development": True,
        },
        "nomination": {
            "eligible_zero_start_rankings": [value["route"] for value in ranked],
            "candidate": candidate,
            "nominated": candidate is not None,
            "confirmation_authorized": False,
            "authorization_rule": "fresh confirmation requires a separate explicit command",
            "selection_rule": "complete pass, gate count, repair-off effect, dose slope, information advantage, route name",
        },
        "claim_boundary": (
            "This simulation tests whether performance-only selection can make global repair "
            "emerge and become causally load-bearing for a plastic-history carrier in a Wagner "
            "GRN. Accessibility routes are route-specific existence tests; they do not establish "
            "that natural cells use global repair or demonstrate plastic heredity in vivo."
        ),
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def render_repair_ratchet_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# Wagner PH Global Repair Ratchet v1",
        "",
        "## Development outcome",
        "",
        f"- Nominated zero-start route: `{analysis['nomination']['candidate']}`."
        if analysis["nomination"]["candidate"]
        else "- No zero-start route passed every frozen core and attribution gate.",
        "- Fresh confirmation remains unauthorized.",
        "",
        "## Routes",
        "",
    ]
    for route, decision in analysis["route_decisions"].items():
        failed_core = [key for key, value in decision["core_checks"].items() if not value]
        failed_attribution = [
            key for key, value in decision["attribution_checks"].items() if not value
        ]
        lines.append(
            f"- `{route}` ({decision['evidence_tier']}): "
            f"repair {decision['global_repair']['mean']:.3f}; "
            f"D4 repair-on/off {decision['repair_on_minus_off']['interval']['mean']:.3f}; "
            f"dose slope {decision['repair_dose_response']['slope_interval']['mean']:.3f}; "
            f"information advantage {decision['information_advantage']['interval']['mean']:.3f}; "
            f"{decision['core_gate_count']}/{decision['core_gate_total']} core and "
            f"{decision['attribution_gate_count']}/{decision['attribution_gate_total']} attribution; "
            f"overall {'PASS' if decision['passes'] else 'FAIL'}; "
            f"failed core: {failed_core}; failed attribution: {failed_attribution}."
        )
    lines.extend(["", "## Claim boundary", "", analysis["claim_boundary"], ""])
    return "\n".join(lines)


__all__ = (
    "ANALYSIS_FORMAT",
    "analyze_repair_ratchet",
    "render_repair_ratchet_report",
)
