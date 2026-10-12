"""Registered inference and nomination for Interpreter Resilience v1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import canonical_digest, read_json
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_direct_analysis import _absolute_checks
from .wagner_ph_resilience_config import (
    CANDIDATE_ARMS,
    RESILIENCE_FORMAT,
    ResilienceSpec,
    architecture_control,
    arm_settings,
    evidence_tier,
)


ANALYSIS_FORMAT = f"{RESILIENCE_FORMAT}-analysis"
TIER_ORDER = {
    "ordinary_full_reset": 0,
    "engineered_global_repair": 1,
    "engineered_regulatory_redundancy": 2,
}


def _seed(spec: ResilienceSpec, phase: str, domain: str) -> str:
    if phase == "development":
        return spec.audit_seed if domain == "audit" else spec.pedigree_seed
    return canonical_digest((spec.confirmation_seed, domain))


def _summaries(rows: list[dict[str, Any]], spec: ResilienceSpec, phase: str) -> dict[str, Any]:
    kernel = spec.kernel(confirmation=phase == "confirmation")
    result = {}
    for arm in sorted({row["arm"] for row in rows}):
        selected = [row for row in rows if row["arm"] == arm]
        effects = {str(row["population_index"]): population_effects(row, kernel) for row in selected}
        result[arm] = {
            "populations": len(selected),
            "effects": effects,
            "intervals": {
                field: _interval(
                    (value[field] for value in effects.values()),
                    _seed(spec, phase, "audit"),
                    f"resilience-{phase}.{arm}.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in next(iter(effects.values()))
            },
        }
    return result


def _paired(
    left: dict[str, Any], right: dict[str, Any], field: str, spec: ResilienceSpec,
    phase: str, domain: str, label: str,
) -> dict[str, Any]:
    indices = sorted(set(left) & set(right), key=int)
    values = {index: float(left[index][field]) - float(right[index][field]) for index in indices}
    return {
        "field": field,
        "task_values": values,
        "interval": _interval(
            values.values(), _seed(spec, phase, domain), f"resilience-{phase}.{label}.{field}",
            spec.bootstrap_repetitions, spec.interval_level,
        ),
    }


def _pedigree_arm(pedigree: dict[str, Any], arm: str, mode: str = "natural") -> dict[str, Any]:
    value = pedigree["arms"][arm]
    return value["modes"][mode] if "modes" in value else value


def _retention_contrast(
    left: dict[str, Any], right: dict[str, Any], distance: int,
    spec: ResilienceSpec, phase: str, label: str,
) -> dict[str, Any]:
    lvalues = left["distances"][str(distance)]["task_retention"]
    rvalues = right["distances"][str(distance)]["task_retention"]
    values = {key: float(lvalues[key]) - float(rvalues[key]) for key in lvalues}
    return {
        "task_values": values,
        "interval": _interval(
            values.values(), _seed(spec, phase, "pedigree"),
            f"resilience-{phase}.{label}.distance-{distance}.retention",
            spec.bootstrap_repetitions, spec.interval_level,
        ),
    }


def _decision(
    candidate: str,
    summaries: dict[str, Any],
    absolute: dict[str, Any],
    pedigree: dict[str, Any],
    spec: ResilienceSpec,
    phase: str,
) -> dict[str, Any]:
    control = "individual_reset"
    candidate_effects, control_effects = summaries[candidate]["effects"], summaries[control]["effects"]
    information_advantage = _paired(
        candidate_effects, control_effects, "information_high", spec, phase, "audit",
        f"{candidate}-minus-{control}",
    )
    performance_loss_values = {
        key: float(control_effects[key]["natural_heldout_performance"])
        - float(candidate_effects[key]["natural_heldout_performance"])
        for key in candidate_effects
    }
    performance_loss = {
        "positive_means_candidate_is_worse": True,
        "task_values": performance_loss_values,
        "interval": _interval(
            performance_loss_values.values(), _seed(spec, phase, "audit"),
            f"resilience-{phase}.{candidate}.performance-loss",
            spec.bootstrap_repetitions, spec.interval_level,
        ),
    }
    candidate_pedigree = _pedigree_arm(pedigree, candidate)
    control_pedigree = _pedigree_arm(pedigree, control)
    retention = {
        distance: float(candidate_pedigree["distances"][str(distance)]["retention_interval"]["mean"])
        for distance in spec.pedigree_depths
    }
    information = {
        distance: float(candidate_pedigree["distances"][str(distance)]["information_interval"]["mean"])
        for distance in spec.pedigree_depths
    }
    d1_advantage = _retention_contrast(candidate_pedigree, control_pedigree, 1, spec, phase, f"{candidate}-minus-{control}")
    d4_advantage = _retention_contrast(candidate_pedigree, control_pedigree, 4, spec, phase, f"{candidate}-minus-{control}")
    architecture = arm_settings(candidate)["architecture"]
    mechanism_off = None
    mechanism_check = True
    if architecture != "single":
        off_pedigree = _pedigree_arm(pedigree, candidate, "mechanism_off")
        mechanism_off = _retention_contrast(candidate_pedigree, off_pedigree, 4, spec, phase, f"{candidate}.mechanism-on-minus-off")
        mechanism_check = (
            float(mechanism_off["interval"]["mean"]) >= spec.mechanism_off_gate
            and float(mechanism_off["interval"]["lower"]) > 0.0
        )
    slope = candidate_pedigree["task_centered_immediate_parent_offspring_slope"]
    checks = {
        "eight_causal_ph_gates": bool(absolute[candidate]["passes"]),
        "distance_one_retention_at_least_0_70": retention[1] >= spec.retention_mean_gate,
        "distance_one_lower_above_0_50": float(candidate_pedigree["distances"]["1"]["retention_interval"]["lower"]) > spec.retention_lower_gate,
        "distance_two_retention_at_least_0_55": retention[2] >= spec.distance_two_gate,
        "distance_four_retention_at_least_0_35": retention[4] >= spec.distance_four_gate,
        "positive_parent_offspring_slope": slope is not None and float(slope) > 0.0,
        "information_advantage_at_least_0_08": float(information_advantage["interval"]["mean"]) >= spec.information_advantage_gate,
        "information_advantage_lower_above_zero": float(information_advantage["interval"]["lower"]) > 0.0,
        "distance_one_advantage_at_least_0_30": float(d1_advantage["interval"]["mean"]) >= spec.distance_one_advantage_gate,
        "distance_one_advantage_lower_above_zero": float(d1_advantage["interval"]["lower"]) > 0.0,
        "distance_four_advantage_at_least_0_20": float(d4_advantage["interval"]["mean"]) >= spec.distance_four_advantage_gate,
        "distance_four_advantage_lower_above_zero": float(d4_advantage["interval"]["lower"]) > 0.0,
        "heldout_performance_loss_at_most_0_05": float(performance_loss["interval"]["mean"]) <= spec.performance_loss_gate,
        "information_declines_but_remains_positive": information[1] >= information[2] >= information[4] > 0.0,
        "mechanism_off_reduces_distance_four_retention": mechanism_check,
    }
    same_architecture = architecture_control(candidate)
    incremental = None
    if same_architecture != candidate and same_architecture in summaries and same_architecture in pedigree["arms"]:
        incremental = {
            "information": _paired(candidate_effects, summaries[same_architecture]["effects"], "information_high", spec, phase, "audit", f"{candidate}-minus-{same_architecture}"),
            "distance_four_retention": _retention_contrast(candidate_pedigree, _pedigree_arm(pedigree, same_architecture), 4, spec, phase, f"{candidate}-minus-{same_architecture}"),
        }
    return {
        "candidate": candidate,
        "ordinary_control": control,
        "same_architecture_control": same_architecture,
        "evidence_tier": evidence_tier(candidate),
        "checks": checks,
        "passes": all(checks.values()),
        "absolute_ph": absolute[candidate],
        "information_advantage": information_advantage,
        "distance_one_retention_advantage": d1_advantage,
        "distance_four_retention_advantage": d4_advantage,
        "mechanism_on_minus_off": mechanism_off,
        "incremental_tail_selection": incremental,
        "heldout_performance_loss": performance_loss,
        "retention_by_distance": retention,
        "information_by_distance": information,
        "pedigree": candidate_pedigree,
    }


def nominate_candidate(decisions: dict[str, Any]) -> dict[str, Any]:
    qualifying = [name for name in CANDIDATE_ARMS if name in decisions and decisions[name]["passes"]]
    if not qualifying:
        return {"nominated": False, "candidate": None, "ordinary_control": None, "same_architecture_control": None, "evidence_tier": None, "selection_rule": "no mechanism satisfied every registered resilience gate"}
    best_tier = min(TIER_ORDER[decisions[name]["evidence_tier"]] for name in qualifying)
    eligible = [name for name in qualifying if TIER_ORDER[decisions[name]["evidence_tier"]] == best_tier]
    ranked = sorted(eligible, key=lambda name: (
        -float(decisions[name]["pedigree"]["distances"]["4"]["retention_interval"]["lower"]),
        -float(decisions[name]["information_advantage"]["interval"]["mean"]),
        CANDIDATE_ARMS.index(name),
    ))
    selected = ranked[0]
    return {
        "nominated": True,
        "candidate": selected,
        "ordinary_control": "individual_reset",
        "same_architecture_control": architecture_control(selected),
        "evidence_tier": decisions[selected]["evidence_tier"],
        "selection_rule": "first passing evidence tier, then distance-four lower bound and information advantage",
    }


def analyze_resilience_phase(
    audit_rows: list[dict[str, Any]],
    pedigree: dict[str, Any],
    spec: ResilienceSpec,
    phase: str,
    *,
    forced_candidate: str | None = None,
) -> dict[str, Any]:
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    summaries = _summaries(audit_rows, spec, phase)
    if any(value["populations"] != task_count for value in summaries.values()):
        raise ValueError("resilience audit is incomplete or unpaired")
    kernel = spec.kernel(confirmation=phase == "confirmation")
    absolute = {}
    for arm, summary in summaries.items():
        checks = _absolute_checks(summary, kernel)
        absolute[arm] = {"checks": checks, "passes": all(checks.values()), "information_high_mean": summary["intervals"]["information_high"]["mean"]}
    candidates = (forced_candidate,) if forced_candidate else tuple(name for name in CANDIDATE_ARMS if name in summaries)
    decisions = {name: _decision(name, summaries, absolute, pedigree, spec, phase) for name in candidates}
    nomination = nominate_candidate(decisions) if phase == "development" else {
        "nominated": True, "candidate": forced_candidate, "ordinary_control": "individual_reset",
        "same_architecture_control": architecture_control(str(forced_candidate)),
        "evidence_tier": evidence_tier(str(forced_candidate)),
        "selection_rule": "candidate frozen before fresh task generation",
    }
    result = {
        "format": ANALYSIS_FORMAT, "phase": phase, "inferential_unit": "paired founder task",
        "summaries": summaries, "absolute_ph_by_arm": absolute, "candidate_decisions": decisions,
        "nomination": nomination,
        "confirmation_passes": bool(decisions[str(forced_candidate)]["passes"]) if phase == "confirmation" else None,
        "claim_boundary": "Reset, repair, and triplicate results are distinct simulated evidence tiers; none identifies a natural molecular carrier or proves plastic heredity in living cells.",
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def load_development_evidence(destination: Path, reference: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    new_rows = [read_json(path) for path in sorted((destination / "development" / "audit" / "populations").glob("*.json"))]
    pedigree = read_json(destination / "development" / "pedigree" / "analysis.json")
    if any(row["arm"] == "individual_reset" for row in new_rows):
        return new_rows, pedigree
    task_count = len({row["population_index"] for row in new_rows})
    control_rows = [read_json(path) for path in sorted((reference / "development" / "audit" / "populations").glob("individual_reset.population-*.json"))[:task_count]]
    reference_pedigree = read_json(reference / "development" / "pedigree" / "analysis.json")
    pedigree["arms"]["individual_reset"] = reference_pedigree["arms"]["individual_reset"]
    return new_rows + control_rows, pedigree


def render_report(development: dict[str, Any], confirmation: dict[str, Any] | None) -> str:
    lines = ["# Wagner PH Interpreter Resilience v1", "", "## Development outcome", ""]
    nomination = development["nomination"]
    if nomination["nominated"]:
        lines.append(f"- Nominated `{nomination['candidate']}` in tier `{nomination['evidence_tier']}`.")
    else:
        lines.append("- No mechanism passed every registered resilience gate.")
    for name, decision in development["candidate_decisions"].items():
        failed = [key for key, value in decision["checks"].items() if not value]
        lines.append(f"- `{name}`: {'PASS' if decision['passes'] else 'FAIL'}; failed checks: {', '.join(failed) if failed else 'none'}.")
    lines.extend(["", "## Fresh confirmation", ""])
    if confirmation is None:
        lines.append("- Not generated because development produced no eligible nominee; the fresh seed consumed zero tasks.")
    else:
        lines.append(f"- Frozen nominee: `{confirmation['nomination']['candidate']}`; {'PASS' if confirmation['confirmation_passes'] else 'FAIL'}.")
    lines.extend(["", "## Claim boundary", "", development["claim_boundary"], ""])
    return "\n".join(lines)
