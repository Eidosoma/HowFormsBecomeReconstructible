"""Task-clustered analyses and preregistered gates for Wagner PH co-option."""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

from .artifacts import canonical_digest
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_config import (
    COOPTION_ANALYSIS_FORMAT,
    CooptionSpec,
    matched_direct,
)


def _cell(result: dict[str, Any], persistence: float, cue_fraction: float) -> dict[str, Any]:
    return next(
        value
        for value in result["cells"]
        if abs(float(value["persistence"]) - persistence) < 1e-12
        and abs(float(value["cue_fraction"]) - cue_fraction) < 1e-12
    )


def _rate(
    result: dict[str, Any],
    persistence: float,
    cue_fraction: float,
    intervention: str,
    generation: int,
    field: str,
) -> float:
    return float(
        _cell(result, persistence, cue_fraction)["conditions"][intervention][
            "checkpoints"
        ][str(generation)][field]
    )


def _effect(
    result: dict[str, Any],
    persistence: float,
    cue_fraction: float,
    generation: int,
    left: str,
    right: str,
    field: str,
) -> float:
    return _rate(result, persistence, cue_fraction, left, generation, field) - _rate(
        result, persistence, cue_fraction, right, generation, field
    )


def population_effects(result: dict[str, Any], spec: CooptionSpec) -> dict[str, float]:
    generation = spec.lineage_generations
    high = 0.9
    low = 0.0
    cue = 0.0
    information_high = _effect(
        result, high, cue, generation, "natural", "independent_history", "correct_rate"
    )
    information_low = _effect(
        result, low, cue, generation, "natural", "independent_history", "correct_rate"
    )
    opposite = _cell(result, high, cue)["conditions"]["opposite_history"]["checkpoints"][
        str(generation)
    ]
    training = float(result["selected_training_score"]["performance"])
    heldout = _rate(result, high, cue, "natural", generation, "correct_rate")
    information = _cell(result, high, cue)["history_information"]
    return {
        "natural_minus_zero": _effect(
            result, high, cue, generation, "natural", "zero", "correct_rate"
        ),
        "generic_stabilization": _effect(
            result,
            high,
            cue,
            generation,
            "independent_history",
            "zero",
            "functional_rate",
        ),
        "information_high": information_high,
        "information_low": information_low,
        "predictability_interaction": information_high - information_low,
        "opposite_donor_following": float(opposite["wrong_rate"])
        - float(opposite["correct_rate"]),
        "reader_dependence": _effect(
            result, high, cue, generation, "natural", "reader_off", "correct_rate"
        ),
        "renewal_dependence": _effect(
            result, high, cue, generation, "natural", "renewal_off", "correct_rate"
        ),
        "founder_write_dependence": _effect(
            result,
            high,
            cue,
            spec.checkpoints[0],
            "natural",
            "founder_write_off",
            "correct_rate",
        ),
        "decoder_balanced_accuracy": float(information["decoder_balanced_accuracy"]),
        "mean_locus_mutual_information_bits": float(
            information["mean_locus_mutual_information_bits"]
        ),
        "natural_heldout_performance": heldout,
        "training_minus_heldout": training - heldout,
    }


def _summaries(
    values: list[dict[str, Any]], spec: CooptionSpec, label: str
) -> dict[str, Any]:
    effects = {str(value["population_id"]): population_effects(value, spec) for value in values}
    fields = tuple(next(iter(effects.values()))) if effects else ()
    return {
        "populations": len(values),
        "effects": effects,
        "intervals": {
            field: _interval(
                (effect[field] for effect in effects.values()),
                spec.master_seed,
                f"cooption-audit.{label}.{field}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            )
            for field in fields
        },
    }


def _passes_absolute(summary: dict[str, Any], spec: CooptionSpec) -> tuple[bool, dict[str, bool]]:
    intervals = summary["intervals"]

    def positive(name: str, threshold: float) -> bool:
        value = intervals[name]
        return bool(
            value["mean"] is not None
            and float(value["mean"]) >= threshold
            and float(value["lower"]) > 0.0
        )

    decoder_values = [
        float(value["decoder_balanced_accuracy"])
        for value in summary["effects"].values()
    ]
    decoder_pass = bool(
        decoder_values
        and float(np.mean(decoder_values)) >= spec.decoder_gate
        and sum(value > 0.5 for value in decoder_values)
        >= math.ceil(0.8 * len(decoder_values))
    )
    checks = {
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
        "history_decoding": decoder_pass,
    }
    return all(checks.values()), checks


def analyze_audit_results(
    results: list[dict[str, Any]], spec: CooptionSpec
) -> dict[str, Any]:
    by_treatment = {
        treatment: [value for value in results if value["treatment"] == treatment]
        for treatment in spec.treatments
        if any(value["treatment"] == treatment for value in results)
    }
    summaries = {
        treatment: _summaries(values, spec, treatment)
        for treatment, values in by_treatment.items()
    }
    tiers: dict[str, Any] = {}
    priority = (
        ("A", "cooption_independent"),
        ("B", "cooption_linked_ramp"),
        ("C", "cooption_linked"),
    )
    for tier, treatment in priority:
        if treatment not in summaries:
            continue
        direct = matched_direct(treatment)
        absolute_pass, checks = _passes_absolute(summaries[treatment], spec)
        indexed = {
            (value["treatment"], int(value["population_index"])): population_effects(value, spec)
            for value in results
        }
        task_indices = sorted(
            {index for arm, index in indexed if arm == treatment}
            & {index for arm, index in indexed if arm == direct}
        )
        differences = [
            indexed[(treatment, index)]["information_high"]
            - indexed[(direct, index)]["information_high"]
            for index in task_indices
        ]
        advantage = _interval(
            differences,
            spec.master_seed,
            f"cooption-advantage.{treatment}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        )
        advantage_pass = bool(
            differences
            and float(advantage["mean"]) >= spec.cooption_advantage_gate
            and float(advantage["lower"]) > 0.0
            and sum(value > 0.0 for value in differences)
            >= math.ceil(0.8 * len(differences))
        )
        tiers[tier] = {
            "treatment": treatment,
            "matched_direct": direct,
            "absolute_gate_pass": absolute_pass,
            "absolute_checks": checks,
            "cooption_advantage": advantage,
            "cooption_advantage_pass": advantage_pass,
            "passes": bool(absolute_pass and advantage_pass),
            "interpretation": (
                "ordinary independent-mutation accessibility"
                if tier == "A"
                else "conditional rescue by linked gradual activation"
                if tier == "B"
                else "conditional rescue by linked writer-reader activation"
            ),
        }
    passing = [tier for tier, value in tiers.items() if value["passes"]]
    nomination = None
    if passing:
        chosen = next(tier for tier, _ in priority if tier in passing)
        nomination = {
            "tier": chosen,
            "treatment": tiers[chosen]["treatment"],
            "matched_direct": tiers[chosen]["matched_direct"],
            "confirmation_authorized": False,
        }
    analysis = {
        "format": COOPTION_ANALYSIS_FORMAT,
        "inferential_unit": "paired founder task",
        "population_count": len(results),
        "treatments": summaries,
        "tiers": tiers,
        "nomination": nomination,
        "generic_stabilization_is_not_a_plastic_heredity_gate": True,
        "primary_independent_failure_cannot_be_rescued_or_relabelled_by_secondary_tiers": True,
        "confirmation_reserve": {
            "status": "eligible-but-not-authorized" if nomination else "untouched-no-finalist",
            "seed": spec.confirmation_seed,
            "rng_draws_consumed": 0,
        },
        "gate_thresholds": {
            "natural_minus_zero": spec.natural_zero_gate,
            "information_high": spec.information_gate,
            "predictability_interaction": spec.predictability_interaction_gate,
            "information_low_mean_at_most": spec.low_predictability_mean_gate,
            "opposite_donor_following": spec.donor_gate,
            "reader_dependence": spec.reader_gate,
            "renewal_dependence": spec.renewal_gate,
            "decoder_balanced_accuracy": spec.decoder_gate,
            "cooption_advantage": spec.cooption_advantage_gate,
        },
    }
    analysis["analysis_digest"] = canonical_digest(analysis)
    return analysis


def analyze_meaning_atlas(
    results: list[dict[str, Any]], spec: CooptionSpec
) -> dict[str, Any]:
    generation = spec.lineage_generations
    anchors = ("k5.b2", "k10.b8")
    cells: dict[str, Any] = {}
    for anchor in anchors:
        for persistence in spec.atlas_persistence:
            for cue in spec.cue_fractions:
                chosen = [
                    next(
                        value
                        for value in result["cells"]
                        if value["carrier"]["name"] == anchor
                        and abs(float(value["persistence"]) - persistence) < 1e-12
                        and abs(float(value["cue_fraction"]) - cue) < 1e-12
                    )
                    for result in results
                ]

                def contrast(left: str, right: str, field: str) -> list[float]:
                    return [
                        float(value["conditions"][left]["checkpoints"][str(generation)][field])
                        - float(value["conditions"][right]["checkpoints"][str(generation)][field])
                        for value in chosen
                    ]

                opposite = [
                    float(value["conditions"]["opposite_history"]["checkpoints"][str(generation)]["wrong_rate"])
                    - float(value["conditions"]["opposite_history"]["checkpoints"][str(generation)]["correct_rate"])
                    for value in chosen
                ]
                effects = {
                    "natural_minus_zero": contrast("natural", "zero", "correct_rate"),
                    "generic_stabilization": contrast(
                        "independent_history", "zero", "functional_rate"
                    ),
                    "inherited_information": contrast(
                        "natural", "independent_history", "correct_rate"
                    ),
                    "reader_dependence": contrast("natural", "reader_off", "correct_rate"),
                    "renewal_dependence": contrast("natural", "renewal_off", "correct_rate"),
                    "opposite_donor_following": opposite,
                    "decoder_balanced_accuracy": [
                        float(value["history_information"]["decoder_balanced_accuracy"])
                        for value in chosen
                    ],
                }
                cell_id = f"{anchor}.rho{persistence:.2f}.cue{cue:.2f}"
                cells[cell_id] = {
                    "anchor": anchor,
                    "persistence": persistence,
                    "cue_fraction": cue,
                    "effects": {
                        name: _interval(
                            values,
                            spec.master_seed,
                            f"meaning-atlas.{cell_id}.{name}",
                            spec.bootstrap_repetitions,
                            spec.interval_level,
                        )
                        for name, values in effects.items()
                    },
                    "task_values": effects,
                }
    interactions: dict[str, Any] = {}
    for anchor in anchors:
        for cue in spec.cue_fractions:
            low = cells[f"{anchor}.rho0.00.cue{cue:.2f}"]["task_values"]["inherited_information"]
            high = cells[f"{anchor}.rho0.90.cue{cue:.2f}"]["task_values"]["inherited_information"]
            values = [right - left for left, right in zip(low, high)]
            interactions[f"{anchor}.cue{cue:.2f}"] = _interval(
                values,
                spec.master_seed,
                f"meaning-atlas.interaction.{anchor}.{cue}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            )
    return {
        "format": "gre-wagner-ph-cooption-meaning-analysis-v1",
        "tasks": len(results),
        "checkpoint_generation": generation,
        "cells": cells,
        "predictability_interactions": interactions,
        "decomposition": {
            "generic_stabilization": "independent-history carrier minus zero for either functional form",
            "inherited_information": "natural parent carrier minus distribution-matched independent donor for the correct form",
        },
        "forced_break_state_not_used_for_pre_cue_prediction": True,
    }


def render_report(atlas: dict[str, Any], audit: dict[str, Any]) -> str:
    nomination = audit.get("nomination")
    lines = [
        "# Wagner PH Co-option v1 Report",
        "",
        "## Design boundary",
        "",
        "The pre-cue assay starts both environments from the same neutral state. Generic stabilization is measured separately from inherited information and cannot satisfy the PH gate.",
        "",
        "## Carrier-meaning atlas",
        "",
        f"- Fresh Wagner tasks: {atlas['tasks']}",
        "- Anchors: k5.b2 (minimal causal carrier) and k10.b8 (renewing carrier)",
        "- Independent donors are balanced, recipient-independent, and distribution matched by construction.",
        "",
        "## Co-option evolution and held-out audit",
        "",
        f"- Audited populations: {audit['population_count']}",
        "- Selection used developmental performance and carrier resource cost only.",
        "- Inference is clustered by paired founder task.",
        "",
        "## Preregistered outcome",
        "",
    ]
    if nomination is None:
        lines.append("No treatment passed every plastic-heredity and co-option-accessibility gate. The confirmation reserve remains untouched.")
    else:
        lines.append(
            f"Tier {nomination['tier']} ({nomination['treatment']}) passed exploration and is eligible—but not authorized—for fresh confirmation."
        )
    lines.extend(("", "## Tier checks", ""))
    for tier, value in audit["tiers"].items():
        lines.append(
            f"- Tier {tier}, `{value['treatment']}`: {'PASS' if value['passes'] else 'FAIL'} ({value['interpretation']})."
        )
    lines.extend(
        (
            "",
            "## Claim boundary",
            "",
            "A positive result would demonstrate an accessible simulated route to a renewable, causally readable parent-state carrier in Wagner GRNs. It would not establish that a particular molecular mechanism exists in nature.",
            "",
        )
    )
    return "\n".join(lines)
