"""Registered inference, two-family ranking, and reporting for Architecture v1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .artifacts import canonical_digest, read_json
from .wagner_ph_architecture_config import (
    ARCHITECTURE_ARMS,
    ARCHITECTURE_FORMAT,
    ENGINEERED_CANDIDATES,
    SINGLE_CANDIDATES,
    ArchitectureSpec,
    arm_settings,
    evidence_family,
    uniform_control,
)
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_direct_analysis import _absolute_checks


ANALYSIS_FORMAT = f"{ARCHITECTURE_FORMAT}-analysis"


def _seed(spec: ArchitectureSpec, phase: str, domain: str) -> str:
    if phase == "development":
        return spec.audit_seed if domain == "audit" else spec.pedigree_seed
    return canonical_digest((spec.confirmation_seed, domain))


def _finite(value: Any, fallback: float = float("-inf")) -> float:
    return fallback if value is None else float(value)


def _summaries(
    rows: list[dict[str, Any]], spec: ArchitectureSpec, phase: str
) -> dict[str, Any]:
    kernel = spec.kernel(confirmation=phase == "confirmation")
    summaries: dict[str, Any] = {}
    for arm in sorted({str(row["arm"]) for row in rows}):
        selected = [row for row in rows if row["arm"] == arm]
        effects = {
            str(row["population_index"]): population_effects(row, kernel)
            for row in selected
        }
        if not effects:
            continue
        summaries[arm] = {
            "populations": len(selected),
            "effects": effects,
            "intervals": {
                field: _interval(
                    (value[field] for value in effects.values()),
                    _seed(spec, phase, "audit"),
                    f"architecture-{phase}.{arm}.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in next(iter(effects.values()))
            },
        }
    return summaries


def _paired_values(
    left: dict[str, Any], right: dict[str, Any], field: str
) -> dict[str, float]:
    indices = sorted(set(left) & set(right), key=int)
    if set(indices) != set(left) or set(indices) != set(right):
        raise ValueError("architecture contrast is not task paired")
    return {
        index: float(left[index][field]) - float(right[index][field])
        for index in indices
    }


def _paired_effect(
    left: dict[str, Any],
    right: dict[str, Any],
    field: str,
    spec: ArchitectureSpec,
    phase: str,
    domain: str,
    label: str,
) -> dict[str, Any]:
    values = _paired_values(left, right, field)
    return {
        "field": field,
        "task_values": values,
        "interval": _interval(
            values.values(),
            _seed(spec, phase, domain),
            f"architecture-{phase}.{label}.{field}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _pedigree_arm(
    pedigree: dict[str, Any], arm: str, mode: str = "natural"
) -> dict[str, Any]:
    value = pedigree["arms"][arm]
    if "modes" not in value:
        if mode != "natural":
            raise KeyError(f"historical pedigree {arm!r} has no mode {mode!r}")
        return value
    return value["modes"][mode]


def _retention_contrast(
    left: dict[str, Any],
    right: dict[str, Any],
    distance: int,
    spec: ArchitectureSpec,
    phase: str,
    label: str,
) -> dict[str, Any]:
    lvalues = left["distances"][str(distance)]["task_retention"]
    rvalues = right["distances"][str(distance)]["task_retention"]
    if set(lvalues) != set(rvalues):
        raise ValueError("architecture pedigree contrast is not task paired")
    values = {
        key: float(lvalues[key]) - float(rvalues[key]) for key in lvalues
    }
    return {
        "distance": distance,
        "task_values": values,
        "interval": _interval(
            values.values(),
            _seed(spec, phase, "pedigree"),
            f"architecture-{phase}.{label}.distance-{distance}.retention",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _interval_gate(
    contrast: dict[str, Any], threshold: float, *, positive_lower: bool = True
) -> bool:
    interval = contrast["interval"]
    return bool(
        interval["mean"] is not None
        and float(interval["mean"]) >= threshold
        and (not positive_lower or float(interval["lower"]) > 0.0)
    )


def _mechanism_attribution(
    candidate: str,
    pedigree: dict[str, Any],
    spec: ArchitectureSpec,
    phase: str,
) -> dict[str, Any]:
    settings = arm_settings(candidate)
    natural = _pedigree_arm(pedigree, candidate)
    contrasts: dict[str, Any] = {}
    checks: dict[str, bool] = {}

    if settings["architecture"] == "repair":
        contrast = _retention_contrast(
            natural,
            _pedigree_arm(pedigree, candidate, "repair_off"),
            4,
            spec,
            phase,
            f"{candidate}.repair-on-minus-off",
        )
        contrasts["repair_on_minus_off"] = contrast
        checks["repair_off_reduces_distance_four_retention_by_0_15"] = (
            _interval_gate(contrast, spec.repair_attribution_gate)
        )

    if settings["challenge"] == "guided":
        control = uniform_control(candidate)
        if control is None or control not in pedigree["arms"]:
            raise ValueError("guided candidate lacks its frozen uniform control")
        contrast = _retention_contrast(
            natural,
            _pedigree_arm(pedigree, control),
            4,
            spec,
            phase,
            f"{candidate}-minus-{control}",
        )
        contrasts["guided_minus_uniform"] = contrast
        checks["guided_beats_uniform_by_0_10_at_distance_four"] = (
            _interval_gate(contrast, spec.guided_attribution_gate)
        )

    if settings["architecture"] == "median3":
        mean_contrast = _retention_contrast(
            natural,
            _pedigree_arm(pedigree, candidate, "mean_decoder"),
            4,
            spec,
            phase,
            f"{candidate}.median-minus-mean-decoder",
        )
        concerted_contrast = _retention_contrast(
            natural,
            _pedigree_arm(pedigree, candidate, "concerted"),
            4,
            spec,
            phase,
            f"{candidate}.independent-minus-concerted",
        )
        contrasts["median_minus_mean_decoder"] = mean_contrast
        contrasts["independent_minus_concerted"] = concerted_contrast
        checks["median_beats_mean_decoder_by_0_15_at_distance_four"] = (
            _interval_gate(mean_contrast, spec.median_attribution_gate)
        )
        checks["independent_beats_concerted_by_0_15_at_distance_four"] = (
            _interval_gate(concerted_contrast, spec.median_attribution_gate)
        )

    return {
        "applicable": bool(checks),
        "checks": checks,
        "contrasts": contrasts,
        "passes": all(checks.values()),
    }


def _decision(
    candidate: str,
    control: str,
    summaries: dict[str, Any],
    absolute: dict[str, Any],
    pedigree: dict[str, Any],
    spec: ArchitectureSpec,
    phase: str,
) -> dict[str, Any]:
    candidate_effects = summaries[candidate]["effects"]
    control_effects = summaries[control]["effects"]
    information_advantage = _paired_effect(
        candidate_effects,
        control_effects,
        "information_high",
        spec,
        phase,
        "audit",
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
            f"architecture-{phase}.{candidate}.performance-loss",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }
    candidate_pedigree = _pedigree_arm(pedigree, candidate)
    control_pedigree = _pedigree_arm(pedigree, control)
    retention = {
        distance: _finite(
            candidate_pedigree["distances"][str(distance)]["retention_interval"][
                "mean"
            ],
            0.0,
        )
        for distance in spec.pedigree_depths
    }
    information = {
        distance: _finite(
            candidate_pedigree["distances"][str(distance)]["information_interval"][
                "mean"
            ],
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
    slope = candidate_pedigree["task_centered_immediate_parent_offspring_slope"]
    core_checks = {
        **{
            f"causal_{name}": bool(passed)
            for name, passed in absolute[candidate]["checks"].items()
        },
        "distance_one_retention_at_least_0_70": retention[1]
        >= spec.retention_mean_gate,
        "distance_one_lower_above_0_50": _finite(
            candidate_pedigree["distances"]["1"]["retention_interval"]["lower"]
        )
        > spec.retention_lower_gate,
        "distance_two_retention_at_least_0_55": retention[2]
        >= spec.distance_two_gate,
        "distance_four_retention_at_least_0_35": retention[4]
        >= spec.distance_four_gate,
        "positive_parent_offspring_slope": slope is not None
        and float(slope) > 0.0,
        "information_advantage_at_least_0_08": _finite(
            information_advantage["interval"]["mean"]
        )
        >= spec.information_advantage_gate,
        "information_advantage_lower_above_zero": _finite(
            information_advantage["interval"]["lower"]
        )
        > 0.0,
        "distance_one_advantage_at_least_0_30": _finite(
            d1_advantage["interval"]["mean"]
        )
        >= spec.distance_one_advantage_gate,
        "distance_one_advantage_lower_above_zero": _finite(
            d1_advantage["interval"]["lower"]
        )
        > 0.0,
        "distance_four_advantage_at_least_0_20": _finite(
            d4_advantage["interval"]["mean"]
        )
        >= spec.distance_four_advantage_gate,
        "distance_four_advantage_lower_above_zero": _finite(
            d4_advantage["interval"]["lower"]
        )
        > 0.0,
        "heldout_performance_loss_at_most_0_05": _finite(
            performance_loss["interval"]["mean"], float("inf")
        )
        <= spec.performance_loss_gate,
        "information_positive_at_every_registered_distance": all(
            information[distance] > 0.0 for distance in spec.pedigree_depths
        ),
        "distance_four_information_at_least_half_distance_one": information[4]
        >= spec.distance_four_information_fraction_gate * information[1],
    }
    attribution = _mechanism_attribution(
        candidate, pedigree, spec, phase
    )
    core_passes = all(core_checks.values())
    return {
        "candidate": candidate,
        "ordinary_control": control,
        "evidence_tier": evidence_family(candidate),
        "core_checks": core_checks,
        "core_gate_count": sum(core_checks.values()),
        "core_gate_total": len(core_checks),
        "core_passes": core_passes,
        "mechanism_attribution": attribution,
        "attribution_passes": attribution["passes"],
        "passes": core_passes and attribution["passes"],
        "absolute_ph": absolute[candidate],
        "information_advantage": information_advantage,
        "distance_one_retention_advantage": d1_advantage,
        "distance_four_retention_advantage": d4_advantage,
        "heldout_performance_loss": performance_loss,
        "retention_by_distance": retention,
        "information_by_distance": information,
        "pedigree": candidate_pedigree,
    }


def _rank_family(
    candidates: Iterable[str], decisions: dict[str, Any]
) -> list[str]:
    available = [name for name in candidates if name in decisions]
    return sorted(
        available,
        key=lambda name: (
            -int(decisions[name]["core_gate_count"]),
            -_finite(
                decisions[name]["pedigree"]["distances"]["4"][
                    "retention_interval"
                ]["lower"]
            ),
            -_finite(
                decisions[name]["pedigree"]["distances"]["1"][
                    "retention_interval"
                ]["lower"]
            ),
            -_finite(decisions[name]["information_advantage"]["interval"]["mean"]),
            ARCHITECTURE_ARMS.index(name),
        ),
    )


def nominate_two(decisions: dict[str, Any]) -> dict[str, Any]:
    single_ranking = _rank_family(SINGLE_CANDIDATES, decisions)
    engineered_ranking = _rank_family(ENGINEERED_CANDIDATES, decisions)
    if not single_ranking or not engineered_ranking:
        raise ValueError("both candidate families must be complete before nomination")
    candidates = (single_ranking[0], engineered_ranking[0])
    return {
        "nominated": True,
        "candidates": list(candidates),
        "single_candidate": candidates[0],
        "engineered_candidate": candidates[1],
        "candidate_evidence_tiers": {
            name: decisions[name]["evidence_tier"] for name in candidates
        },
        "rankings": {
            "single": single_ranking,
            "engineered": engineered_ranking,
        },
        "selection_rule": (
            "within each frozen family: core gates passed, distance-four retention "
            "lower bound, distance-one lower bound, information advantage, frozen arm order"
        ),
        "selection_does_not_require_development_pass": True,
    }


def analyze_architecture_phase(
    audit_rows: list[dict[str, Any]],
    pedigree: dict[str, Any],
    spec: ArchitectureSpec,
    phase: str,
    *,
    forced_candidates: tuple[str, str] | None = None,
) -> dict[str, Any]:
    if phase not in {"development", "confirmation"}:
        raise ValueError("unknown architecture analysis phase")
    task_count = (
        spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    )
    summaries = _summaries(audit_rows, spec, phase)
    if any(value["populations"] != task_count for value in summaries.values()):
        raise ValueError("architecture audit is incomplete or not task paired")
    control = (
        "individual_single"
        if phase == "confirmation" or "individual_single" in summaries
        else "individual_reset"
    )
    if control not in summaries or control not in pedigree["arms"]:
        raise ValueError("architecture ordinary control is missing")
    kernel = spec.kernel(confirmation=phase == "confirmation")
    absolute = {}
    for arm, summary in summaries.items():
        checks = _absolute_checks(summary, kernel)
        absolute[arm] = {
            "checks": checks,
            "passes": all(checks.values()),
            "information_high_mean": summary["intervals"]["information_high"][
                "mean"
            ],
        }
    candidates = (
        tuple(forced_candidates)
        if forced_candidates is not None
        else tuple(name for name in ARCHITECTURE_ARMS if name in summaries)
    )
    if any(name not in summaries or name not in pedigree["arms"] for name in candidates):
        raise ValueError("architecture candidate evidence is incomplete")
    decisions = {
        name: _decision(
            name, control, summaries, absolute, pedigree, spec, phase
        )
        for name in candidates
    }
    if phase == "development":
        nomination = nominate_two(decisions)
    else:
        if forced_candidates is None or len(set(forced_candidates)) != 2:
            raise ValueError("confirmation requires two distinct frozen candidates")
        nomination = {
            "nominated": True,
            "candidates": list(forced_candidates),
            "single_candidate": forced_candidates[0],
            "engineered_candidate": forced_candidates[1],
            "selection_rule": "frozen before generation of any confirmation task",
            "selection_does_not_use_confirmation_results": True,
        }
    confirmation = (
        {
            "candidate_passes": {
                name: decisions[name]["passes"] for name in candidates
            },
            "all_candidates_pass": all(
                decisions[name]["passes"] for name in candidates
            ),
        }
        if phase == "confirmation"
        else None
    )
    result = {
        "format": ANALYSIS_FORMAT,
        "phase": phase,
        "inferential_unit": "paired founder task",
        "ordinary_control": control,
        "summaries": summaries,
        "absolute_ph_by_arm": absolute,
        "candidate_decisions": decisions,
        "nomination": nomination,
        "confirmation": confirmation,
        "mechanism_attribution_is_separate_from_core_gates": True,
        "engineered_median_results_are_a_separate_evidence_tier": True,
        "claim_boundary": (
            "These are simulated Wagner-GRN routes to persistent, causally readable "
            "plastic-history effects. Repair and median triplication are engineered "
            "sufficiency results; none identifies a natural molecular carrier or proves "
            "plastic heredity in living cells."
        ),
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def load_development_evidence(
    destination: Path, reference: Path, spec: ArchitectureSpec
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    new_rows = [
        read_json(path)
        for path in sorted(
            (destination / "development" / "audit" / "populations").glob("*.json")
        )
    ]
    pedigree = read_json(destination / "development" / "pedigree" / "analysis.json")
    if any(row["arm"] == "individual_single" for row in new_rows):
        return new_rows, pedigree
    control_rows = [
        read_json(path)
        for path in sorted(
            (reference / "development" / "audit" / "populations").glob(
                "individual_reset.population-*.json"
            )
        )[: spec.task_count]
    ]
    if len(control_rows) != spec.task_count:
        raise ValueError("sealed Depth individual-reset audit is incomplete")
    reference_pedigree = read_json(
        reference / "development" / "pedigree" / "analysis.json"
    )
    pedigree["arms"]["individual_reset"] = reference_pedigree["arms"][
        "individual_reset"
    ]
    return new_rows + control_rows, pedigree


def render_report(
    development: dict[str, Any],
    confirmation: dict[str, Any] | None,
    diagnosis: dict[str, Any],
) -> str:
    nomination = development["nomination"]
    lines = [
        "# Wagner PH Interpreter Architecture v1",
        "",
        "## Development ranking",
        "",
        (
            f"- Frozen single candidate: `{nomination['single_candidate']}`; "
            f"engineered candidate: `{nomination['engineered_candidate']}`."
        ),
    ]
    for name in nomination["candidates"]:
        decision = development["candidate_decisions"][name]
        failed_core = [
            key for key, passed in decision["core_checks"].items() if not passed
        ]
        failed_attribution = [
            key
            for key, passed in decision["mechanism_attribution"]["checks"].items()
            if not passed
        ]
        lines.append(
            f"- `{name}` ({decision['evidence_tier']}): "
            f"{decision['core_gate_count']}/{decision['core_gate_total']} core gates; "
            f"overall {'PASS' if decision['passes'] else 'FAIL'}; "
            f"failed core: {', '.join(failed_core) if failed_core else 'none'}; "
            f"failed attribution: {', '.join(failed_attribution) if failed_attribution else 'none'}."
        )
    lines.extend(
        [
            "",
            "## Frozen diagnosis",
            "",
            (
                "- Cross-fitted predictor mean top-ten damage capture: "
                f"{diagnosis['predictor']['mean_top_k_damage_capture']}."
            ),
            "- Repair/topology factorials and median/mean/concerted contrasts are diagnostic, not selection evidence.",
            "",
            "## Fresh confirmation",
            "",
        ]
    )
    if confirmation is None:
        lines.append("- Fresh confirmation has not been completed.")
    else:
        for name in nomination["candidates"]:
            decision = confirmation["candidate_decisions"][name]
            lines.append(
                f"- `{name}`: {'PASS' if decision['passes'] else 'FAIL'} "
                f"({decision['core_gate_count']}/{decision['core_gate_total']} core gates)."
            )
        lines.append(
            "- Joint confirmation: "
            + (
                "PASS."
                if confirmation["confirmation"]["all_candidates_pass"]
                else "FAIL."
            )
        )
    lines.extend(["", "## Claim boundary", "", development["claim_boundary"], ""])
    return "\n".join(lines)


__all__ = (
    "ANALYSIS_FORMAT",
    "analyze_architecture_phase",
    "load_development_evidence",
    "nominate_two",
    "render_report",
)
