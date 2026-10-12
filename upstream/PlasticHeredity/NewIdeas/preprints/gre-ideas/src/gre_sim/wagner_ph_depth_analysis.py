"""Registered decisions for Wagner PH Interpreter-Depth v1."""

from __future__ import annotations

from typing import Any

import numpy as np

from .artifacts import canonical_digest
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_direct_analysis import _absolute_checks
from .wagner_ph_depth_config import (
    DEPTH_ANALYSIS_FORMAT,
    DEPTH_ARMS,
    InterpreterDepthSpec,
    matched_control,
)


CANDIDATE_ARMS = (
    "offspring3_reset",
    "offspring8_reset",
    "lineage2x2_reset",
    "offspring8_local",
)


def _summary(rows: list[dict[str, Any]], spec: InterpreterDepthSpec, phase: str, arm: str) -> dict[str, Any]:
    kernel = spec.kernel(confirmation=phase == "confirmation")
    seed = spec.audit_seed if phase == "development" else canonical_digest((spec.confirmation_seed, "causal-audit"))
    effects = {str(value["population_index"]): population_effects(value, kernel) for value in rows}
    fields = tuple(next(iter(effects.values()))) if effects else ()
    return {
        "populations": len(rows),
        "effects": effects,
        "intervals": {
            field: _interval(
                (row[field] for row in effects.values()),
                seed,
                f"interpreter-depth-{phase}.{arm}.{field}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            )
            for field in fields
        },
    }


def _paired(
    left: dict[str, Any],
    right: dict[str, Any],
    field: str,
    spec: InterpreterDepthSpec,
    phase: str,
    label: str,
) -> dict[str, Any]:
    indices = sorted(set(left) & set(right), key=int)
    values = {index: float(left[index][field]) - float(right[index][field]) for index in indices}
    seed = spec.audit_seed if phase == "development" else canonical_digest((spec.confirmation_seed, "causal-audit"))
    return {
        "field": field,
        "task_values": values,
        "interval": _interval(
            values.values(), seed,
            f"interpreter-depth-{phase}.contrast.{label}.{field}",
            spec.bootstrap_repetitions, spec.interval_level,
        ),
    }


def _candidate_decision(
    candidate: str,
    summaries: dict[str, Any],
    absolute: dict[str, Any],
    pedigree: dict[str, Any],
    spec: InterpreterDepthSpec,
    phase: str,
) -> dict[str, Any]:
    control = matched_control(candidate)
    candidate_effects = summaries[candidate]["effects"]
    control_effects = summaries[control]["effects"]
    information_advantage = _paired(
        candidate_effects, control_effects, "information_high", spec, phase,
        f"{candidate}-minus-{control}",
    )
    candidate_pedigree = pedigree["arms"][candidate]
    control_pedigree = pedigree["arms"][control]
    distance_one = candidate_pedigree["distances"]["1"]
    control_distance_one = control_pedigree["distances"]["1"]
    retention_values = {
        key: float(distance_one["task_retention"][key])
        - float(control_distance_one["task_retention"][key])
        for key in distance_one["task_retention"]
    }
    pedigree_seed = spec.pedigree_seed if phase == "development" else canonical_digest((spec.confirmation_seed, "mutation-pedigree"))
    retention_advantage = {
        "task_values": retention_values,
        "interval": _interval(
            retention_values.values(), pedigree_seed,
            f"interpreter-depth-{phase}.{candidate}-minus-{control}.retention-distance-1",
            spec.bootstrap_repetitions, spec.interval_level,
        ),
    }
    performance_loss_values = {
        key: float(control_effects[key]["natural_heldout_performance"])
        - float(candidate_effects[key]["natural_heldout_performance"])
        for key in candidate_effects
    }
    performance_loss = {
        "positive_means_candidate_is_worse": True,
        "task_values": performance_loss_values,
        "interval": _interval(
            performance_loss_values.values(),
            spec.audit_seed if phase == "development" else canonical_digest((spec.confirmation_seed, "causal-audit")),
            f"interpreter-depth-{phase}.{candidate}-minus-{control}.performance-loss",
            spec.bootstrap_repetitions, spec.interval_level,
        ),
    }
    retention_means = {
        distance: float(candidate_pedigree["distances"][str(distance)]["retention_interval"]["mean"])
        for distance in spec.pedigree_depths
    }
    information_means = {
        distance: float(candidate_pedigree["distances"][str(distance)]["information_interval"]["mean"])
        for distance in spec.pedigree_depths
    }
    information_declines_but_remains_positive = bool(
        information_means[1] >= information_means[2] >= information_means[4] > 0.0
    )
    slope = candidate_pedigree["task_centered_immediate_parent_offspring_slope"]
    checks = {
        "eight_causal_ph_gates": bool(absolute[candidate]["passes"]),
        "distance_one_retention_at_least_0_70": float(distance_one["retention_interval"]["mean"])
        >= spec.retention_mean_gate,
        "distance_one_retention_lower_above_0_50": float(distance_one["retention_interval"]["lower"])
        > spec.retention_lower_gate,
        "distance_two_retention_at_least_0_55": retention_means[2] >= spec.distance_two_retention_gate,
        "distance_four_retention_at_least_0_35": retention_means[4] >= spec.distance_four_retention_gate,
        "positive_task_centered_parent_offspring_slope": slope is not None and float(slope) > 0.0,
        "information_advantage_at_least_0_08": float(information_advantage["interval"]["mean"])
        >= spec.information_advantage_gate,
        "information_advantage_lower_above_zero": float(information_advantage["interval"]["lower"]) > 0.0,
        "retention_advantage_at_least_0_30": float(retention_advantage["interval"]["mean"])
        >= spec.retention_advantage_gate,
        "retention_advantage_lower_above_zero": float(retention_advantage["interval"]["lower"]) > 0.0,
        "heldout_performance_loss_at_most_0_05": float(performance_loss["interval"]["mean"])
        <= spec.performance_loss_gate,
        "information_declines_monotonically_but_remains_positive_through_distance_four":
        information_declines_but_remains_positive,
    }
    return {
        "candidate": candidate,
        "matched_individual_control": control,
        "evidence_tier": "ordinary_full_reset" if candidate.endswith("_reset") else "conditional_local_mutation_geometry",
        "checks": checks,
        "passes": all(checks.values()),
        "absolute_ph": absolute[candidate],
        "information_advantage": information_advantage,
        "retention_advantage_distance_one": retention_advantage,
        "heldout_performance_loss": performance_loss,
        "retention_by_distance": retention_means,
        "information_by_distance": information_means,
        "pedigree": candidate_pedigree,
    }


def nominate_candidate(decisions: dict[str, Any]) -> dict[str, Any]:
    qualifying_reset = [name for name in CANDIDATE_ARMS[:-1] if decisions[name]["passes"]]
    if qualifying_reset:
        ranked = sorted(
            qualifying_reset,
            key=lambda name: (
                -float(decisions[name]["retention_by_distance"][4]),
                -float(decisions[name]["absolute_ph"]["information_high_mean"]),
                CANDIDATE_ARMS.index(name),
            ),
        )
        return {
            "nominated": True,
            "candidate": ranked[0],
            "matched_control": matched_control(ranked[0]),
            "evidence_tier": "ordinary_full_reset",
            "selection_rule": "qualifying full-reset mechanism with highest distance-four retention",
        }
    local = "offspring8_local"
    if decisions[local]["passes"]:
        return {
            "nominated": True,
            "candidate": local,
            "matched_control": matched_control(local),
            "evidence_tier": "conditional_local_mutation_geometry",
            "selection_rule": "local mutation geometry is eligible only when no full-reset mechanism qualifies",
        }
    return {
        "nominated": False,
        "candidate": None,
        "matched_control": None,
        "evidence_tier": None,
        "selection_rule": "no mechanism satisfied every registered development gate",
    }


def _failure_clustering(
    pedigree_shards: list[dict[str, Any]], atlas_shards: list[dict[str, Any]]
) -> dict[str, Any]:
    vulnerable: dict[int, set[int]] = {}
    for shard in atlas_shards:
        task = int(shard["task_index"])
        by_edge: dict[int, list[float]] = {}
        for root in shard["roots"]:
            for row in root["rows"]:
                by_edge.setdefault(int(row["edge_index"]), []).append(float(row["delta"]["information_high"]))
        ranked = sorted(by_edge, key=lambda edge: (float(np.mean(by_edge[edge])), edge))
        vulnerable[task] = set(ranked[:max(1, len(ranked) // 10)])
    rows = [row for shard in pedigree_shards for row in shard["rows"]]
    groups = {"vulnerable_edge_hit": [], "no_vulnerable_edge_hit": []}
    for row in rows:
        indices = {int(target) * 10 + int(source) for target, source in row["changed_weight_indices"]}
        hit = bool(indices & vulnerable.get(int(row["task_index"]), set()))
        groups["vulnerable_edge_hit" if hit else "no_vulnerable_edge_hit"].append(row)
    result: dict[str, Any] = {}
    for name, selected in groups.items():
        eligible = [row for row in selected if row["eligible_positive_root"]]
        result[name] = {
            "events": len(selected),
            "eligible_positive_root_events": len(eligible),
            "collapse_probability": float(np.mean([row["collapsed"] for row in eligible])) if eligible else None,
            "mean_information_change": float(np.mean([
                float(row["descendant_information"]) - float(row["immediate_parent_information"])
                for row in selected
            ])) if selected else None,
        }
    hit = result["vulnerable_edge_hit"]["collapse_probability"]
    miss = result["no_vulnerable_edge_hit"]["collapse_probability"]
    result["collapse_risk_difference_hit_minus_no_hit"] = (
        float(hit) - float(miss) if hit is not None and miss is not None else None
    )
    result["diagnostic_not_a_selection_term"] = True
    return result


def analyze_depth_phase(
    audit_rows: list[dict[str, Any]],
    pedigree: dict[str, Any],
    spec: InterpreterDepthSpec,
    phase: str,
    *,
    forced_candidate: str | None = None,
    pedigree_shards: list[dict[str, Any]] | None = None,
    atlas_shards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if phase not in {"development", "confirmation"}:
        raise ValueError("analysis phase must be development or confirmation")
    arms = tuple(sorted({value["arm"] for value in audit_rows}, key=DEPTH_ARMS.index))
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    grouped = {arm: [value for value in audit_rows if value["arm"] == arm] for arm in arms}
    if any(len(values) != task_count for values in grouped.values()):
        raise ValueError("interpreter-depth audit is incomplete or unpaired")
    summaries = {arm: _summary(grouped[arm], spec, phase, arm) for arm in arms}
    kernel = spec.kernel(confirmation=phase == "confirmation")
    absolute: dict[str, Any] = {}
    for arm in arms:
        checks = _absolute_checks(summaries[arm], kernel)
        absolute[arm] = {
            "checks": checks,
            "passes": all(checks.values()),
            "information_high_mean": summaries[arm]["intervals"]["information_high"]["mean"],
        }
    candidates = (forced_candidate,) if forced_candidate else tuple(name for name in CANDIDATE_ARMS if name in arms)
    decisions = {
        candidate: _candidate_decision(candidate, summaries, absolute, pedigree, spec, phase)
        for candidate in candidates
    }
    if phase == "development":
        nomination = nominate_candidate(decisions)
        confirmation_passes = None
    else:
        if forced_candidate is None or forced_candidate not in decisions:
            raise ValueError("confirmation analysis requires the frozen nominated candidate")
        nomination = {
            "nominated": True,
            "candidate": forced_candidate,
            "matched_control": matched_control(forced_candidate),
            "evidence_tier": decisions[forced_candidate]["evidence_tier"],
            "selection_rule": "candidate was frozen by development before fresh tasks were generated",
        }
        confirmation_passes = bool(decisions[forced_candidate]["passes"])
    result = {
        "format": DEPTH_ANALYSIS_FORMAT,
        "phase": phase,
        "inferential_unit": "paired founder task",
        "summaries": summaries,
        "absolute_ph_by_arm": absolute,
        "candidate_decisions": decisions,
        "nomination": nomination,
        "confirmation_passes": confirmation_passes,
        "local_mutation_result_cannot_be_relabelled_as_ordinary_wagner_robustness": True,
        "claim_boundary": (
            "Development identifies a simulated mechanism only. Fresh confirmation can replicate that mechanism, "
            "but neither phase identifies a natural molecular carrier or proves plastic heredity in living cells."
        ),
    }
    if phase == "development" and pedigree_shards is not None and atlas_shards is not None:
        result["atlas_pedigree_failure_clustering"] = _failure_clustering(pedigree_shards, atlas_shards)
    result["analysis_digest"] = canonical_digest(result)
    return result


def render_depth_report(
    development: dict[str, Any],
    confirmation: dict[str, Any] | None,
) -> str:
    nomination = development["nomination"]
    lines = [
        "# Wagner PH Interpreter-Depth v1",
        "",
        "## Development outcome",
        "",
        f"- Nominee: `{nomination['candidate']}`." if nomination["nominated"] else "- No mechanism passed every nomination gate.",
    ]
    for name, decision in development["candidate_decisions"].items():
        failed = [key for key, passed in decision["checks"].items() if not passed]
        lines.append(
            f"- `{name}`: {'PASS' if decision['passes'] else 'FAIL'}; "
            f"failed checks: {', '.join(failed) if failed else 'none'}."
        )
    lines.extend(("", "## Fresh confirmation", ""))
    if confirmation is None:
        lines.append("- Not run because development produced no eligible nominee; the fresh seed consumed zero tasks.")
    else:
        candidate = confirmation["nomination"]["candidate"]
        lines.append(f"- `{candidate}` fresh-task confirmation: {'PASS' if confirmation['confirmation_passes'] else 'FAIL'}.")
    lines.extend(("", "## Claim boundary", "", development["claim_boundary"], ""))
    return "\n".join(lines)
