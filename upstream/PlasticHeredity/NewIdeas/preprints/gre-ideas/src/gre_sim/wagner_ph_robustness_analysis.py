"""Task-clustered decisions for the mutation-autopsy/robustness experiment."""

from __future__ import annotations

from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_direct_analysis import _absolute_checks
from .wagner_ph_robustness_config import (
    ROBUSTNESS_ANALYSIS_FORMAT,
    RobustnessSpec,
)


TIER_ARMS = {
    "A_ordinary_mutation_robustness": (
        "offspring_independent",
        "individual_independent",
    ),
    "B_protected_carrier_robustness": (
        "offspring_protected",
        "individual_protected",
    ),
    "C_linked_writer_reader_robustness": (
        "offspring_linked",
        "individual_linked",
    ),
}


def _summary(
    rows: list[dict[str, Any]], spec: RobustnessSpec, arm: str
) -> dict[str, Any]:
    kernel = spec.kernel()
    effects = {
        str(value["population_index"]): population_effects(value, kernel) for value in rows
    }
    fields = tuple(next(iter(effects.values()))) if effects else ()
    return {
        "populations": len(rows),
        "effects": effects,
        "intervals": {
            field: _interval(
                (row[field] for row in effects.values()),
                spec.audit_seed,
                f"robustness-analysis.{arm}.{field}",
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
    spec: RobustnessSpec,
    label: str,
) -> dict[str, Any]:
    indices = sorted(set(left) & set(right), key=int)
    values = {
        index: float(left[index][field]) - float(right[index][field]) for index in indices
    }
    return {
        "field": field,
        "task_values": values,
        "interval": _interval(
            values.values(),
            spec.audit_seed,
            f"robustness-analysis.contrast.{label}.{field}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _information_at_cue(row: dict[str, Any], cue: float, generation: int) -> float:
    cell = next(
        value
        for value in row["cells"]
        if abs(float(value["persistence"]) - 0.9) < 1e-12
        and abs(float(value["cue_fraction"]) - cue) < 1e-12
    )
    natural = cell["conditions"]["natural"]["checkpoints"][str(generation)]["correct_rate"]
    independent = cell["conditions"]["independent_history"]["checkpoints"][str(generation)][
        "correct_rate"
    ]
    return float(natural) - float(independent)


def analyze_robustness_campaign(
    audit_rows: list[dict[str, Any]],
    pedigree: dict[str, Any],
    autopsy: dict[str, Any],
    spec: RobustnessSpec,
) -> dict[str, Any]:
    spec.validate()
    kernel = spec.kernel()
    grouped = {
        arm: [value for value in audit_rows if value["arm"] == arm] for arm in spec.arms
    }
    if any(len(values) != spec.task_count for values in grouped.values()):
        raise ValueError("robustness audit is incomplete or unpaired")
    summaries = {arm: _summary(grouped[arm], spec, arm) for arm in spec.arms}
    absolute = {
        arm: {
            "checks": _absolute_checks(summaries[arm], kernel),
        }
        for arm in spec.arms
    }
    for arm in spec.arms:
        absolute[arm]["passes"] = all(absolute[arm]["checks"].values())

    cue_sensitivity: dict[str, Any] = {}
    for arm, rows in grouped.items():
        task_values = {
            str(value["population_index"]): _information_at_cue(
                value, 0.25, kernel.lineage_generations
            )
            - _information_at_cue(value, 0.0, kernel.lineage_generations)
            for value in rows
        }
        cue_sensitivity[arm] = {
            "task_values": task_values,
            "interval": _interval(
                task_values.values(),
                spec.audit_seed,
                f"robustness-analysis.{arm}.cue25-minus-precue",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
        }

    negative_controls = {
        arm: {
            "does_not_pass_complete_ph_signature": not absolute[arm]["passes"],
            "information_high_mean": summaries[arm]["intervals"]["information_high"]["mean"],
        }
        for arm in ("offspring_fixed_k1", "offspring_inert")
    }
    negative_controls_pass = all(
        value["does_not_pass_complete_ph_signature"] for value in negative_controls.values()
    )

    tiers: dict[str, Any] = {}
    pedigree_arms = pedigree["arms"]
    for tier, (candidate, control) in TIER_ARMS.items():
        candidate_effects = summaries[candidate]["effects"]
        control_effects = summaries[control]["effects"]
        information_advantage = _paired(
            candidate_effects,
            control_effects,
            "information_high",
            spec,
            f"{candidate}-minus-{control}",
        )
        retention_values = {
            key: float(pedigree_arms[candidate]["task_retention"][key])
            - float(pedigree_arms[control]["task_retention"][key])
            for key in pedigree_arms[candidate]["task_retention"]
        }
        retention_advantage = {
            "task_values": retention_values,
            "interval": _interval(
                retention_values.values(),
                spec.pedigree_seed,
                f"robustness-analysis.{candidate}-minus-{control}.retention",
                spec.bootstrap_repetitions,
                spec.interval_level,
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
                spec.audit_seed,
                f"robustness-analysis.{candidate}-minus-{control}.performance-loss",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
        }
        retention = pedigree_arms[candidate]["retention_interval"]
        slope = pedigree_arms[candidate][
            "task_centered_immediate_parent_offspring_slope"
        ]
        checks = {
            "eight_causal_ph_gates": bool(absolute[candidate]["passes"]),
            "at_least_70_percent_retention": float(retention["mean"])
            >= spec.retention_mean_gate,
            "task_bootstrap_retention_lower_above_50_percent": float(retention["lower"])
            > spec.retention_lower_gate,
            "positive_task_centered_parent_offspring_slope": slope is not None
            and float(slope) > 0.0,
            "information_advantage_at_least_0_08": float(
                information_advantage["interval"]["mean"]
            )
            >= spec.information_advantage_gate,
            "information_advantage_lower_above_zero": float(
                information_advantage["interval"]["lower"]
            )
            > 0.0,
            "retention_advantage_at_least_0_30": float(
                retention_advantage["interval"]["mean"]
            )
            >= spec.retention_advantage_gate,
            "retention_advantage_lower_above_zero": float(
                retention_advantage["interval"]["lower"]
            )
            > 0.0,
            "heldout_natural_performance_loss_at_most_0_05": float(
                performance_loss["interval"]["mean"]
            )
            <= spec.performance_loss_gate,
            "fixed_k1_and_inert_remain_negative": negative_controls_pass,
        }
        tiers[tier] = {
            "candidate": candidate,
            "matched_individual_control": control,
            "checks": checks,
            "passes": all(checks.values()),
            "absolute_ph": absolute[candidate],
            "retention": pedigree_arms[candidate],
            "information_advantage": information_advantage,
            "retention_advantage": retention_advantage,
            "heldout_performance_loss": performance_loss,
            "claim": (
                "ordinary mutation robustness" if tier.startswith("A_") else
                "protected-carrier robustness" if tier.startswith("B_") else
                "linked writer-reader robustness"
            ),
        }

    result = {
        "format": ROBUSTNESS_ANALYSIS_FORMAT,
        "inferential_unit": "paired sealed founder task",
        "development_not_confirmation": True,
        "fresh_confirmation_seed_consumed": False,
        "summaries": summaries,
        "absolute_ph_by_arm": absolute,
        "cue25_sensitivity": cue_sensitivity,
        "negative_controls": negative_controls,
        "negative_controls_pass": negative_controls_pass,
        "tiers": tiers,
        "tier_A_passes": tiers["A_ordinary_mutation_robustness"]["passes"],
        "any_engineered_robustness_tier_passes": any(
            tiers[name]["passes"]
            for name in (
                "B_protected_carrier_robustness",
                "C_linked_writer_reader_robustness",
            )
        ),
        "tier_B_or_C_cannot_be_relabelled_as_tier_A": True,
        "autopsy_digest": autopsy["analysis_digest"],
        "pedigree_digest": pedigree["analysis_digest"],
        "claim_boundary": (
            "This development cohort can identify a simulated robustness mechanism. "
            "It cannot establish natural molecular plastic heredity or count as fresh confirmation."
        ),
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def render_robustness_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# Wagner PH Mutation Autopsy and Robustness Ratchet v1",
        "",
        "## Outcome",
        "",
        f"- Tier A (ordinary mutation robustness): {'PASS' if analysis['tier_A_passes'] else 'FAIL'}.",
        "- This is a development experiment; fresh confirmation tasks remain untouched.",
        "",
        "## Mechanism tiers",
        "",
    ]
    for name, value in analysis["tiers"].items():
        failed = [key for key, passed in value["checks"].items() if not passed]
        lines.append(
            f"- `{name}`: {'PASS' if value['passes'] else 'FAIL'}; "
            f"failed checks: {', '.join(failed) if failed else 'none'}."
        )
    lines.extend(
        (
            "",
            "## Claim boundary",
            "",
            analysis["claim_boundary"],
            "",
        )
    )
    return "\n".join(lines)
