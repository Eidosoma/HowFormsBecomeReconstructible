"""Prospective task-clustered analysis for direct predictive PH origin."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .artifacts import canonical_digest
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_direct_config import (
    DIRECT_ANALYSIS_FORMAT,
    DIRECT_VARIANTS,
    DirectPredictionSpec,
    variant_settings,
)


def _cell(result: dict[str, Any], persistence: float) -> dict[str, Any]:
    return next(
        value
        for value in result["cells"]
        if abs(float(value["persistence"]) - persistence) < 1e-12
        and abs(float(value["cue_fraction"])) < 1e-12
    )


def _rate(
    result: dict[str, Any],
    persistence: float,
    intervention: str,
    generation: int,
    field: str,
) -> float:
    return float(
        _cell(result, persistence)["conditions"][intervention]["checkpoints"]
        [str(generation)][field]
    )


def information_at(
    result: dict[str, Any], persistence: float, generation: int
) -> float:
    return _rate(result, persistence, "natural", generation, "correct_rate") - _rate(
        result,
        persistence,
        "independent_history",
        generation,
        "correct_rate",
    )


def _summary(
    results: list[dict[str, Any]], kernel: CooptionSpec, spec: DirectPredictionSpec, label: str
) -> dict[str, Any]:
    effects = {
        str(value["population_index"]): population_effects(value, kernel)
        for value in results
    }
    fields = tuple(next(iter(effects.values()))) if effects else ()
    settings = variant_settings(label)
    selected_persistence = float(settings["predictive_persistence"])
    selected_ecology = {
        str(value["population_index"]): information_at(
            value, selected_persistence, kernel.lineage_generations
        )
        for value in results
    }
    return {
        "populations": len(results),
        "selection_settings": settings,
        "effects": effects,
        "intervals": {
            field: _interval(
                (row[field] for row in effects.values()),
                spec.master_seed,
                f"direct-prediction.{label}.{field}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            )
            for field in fields
        },
        "information_at_selected_ecology": {
            "task_values": selected_ecology,
            "interval": _interval(
                selected_ecology.values(),
                spec.master_seed,
                f"direct-prediction.{label}.selected-ecology",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
        },
        "selected_carriers": {
            str(value["population_index"]): value["carrier"] for value in results
        },
    }


def _absolute_checks(summary: dict[str, Any], kernel: CooptionSpec) -> dict[str, bool]:
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
        "natural_minus_zero": positive("natural_minus_zero", kernel.natural_zero_gate),
        "information_high": positive("information_high", kernel.information_gate),
        "predictability_interaction": positive(
            "predictability_interaction", kernel.predictability_interaction_gate
        ),
        "low_predictability_is_harmful": bool(
            intervals["information_low"]["mean"] is not None
            and float(intervals["information_low"]["mean"])
            <= kernel.low_predictability_mean_gate
        ),
        "opposite_donor_following": positive(
            "opposite_donor_following", kernel.donor_gate
        ),
        "reader_dependence": positive("reader_dependence", kernel.reader_gate),
        "renewal_dependence": positive("renewal_dependence", kernel.renewal_gate),
        "history_decoding": bool(
            decoder
            and float(np.mean(decoder)) >= kernel.decoder_gate
            and sum(value > 0.5 for value in decoder)
            >= math.ceil(0.8 * len(decoder))
        ),
    }


def _paired_contrast(
    summaries: dict[str, dict[str, Any]],
    left: str,
    right: str,
    field: str,
    spec: DirectPredictionSpec,
) -> dict[str, Any]:
    left_values = summaries[left]["effects"]
    right_values = summaries[right]["effects"]
    indices = sorted(set(left_values) & set(right_values), key=int)
    values = {
        index: float(left_values[index][field]) - float(right_values[index][field])
        for index in indices
    }
    return {
        "left": left,
        "right": right,
        "field": field,
        "task_values": values,
        "interval": _interval(
            values.values(),
            spec.master_seed,
            f"direct-prediction.contrast.{left}.{right}.{field}",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def analyze_direct_prediction(
    audits: dict[str, list[dict[str, Any]]],
    spec: DirectPredictionSpec,
    emergence: dict[str, Any],
    pedigree: dict[str, Any],
    parent_diagnostic: dict[str, Any],
) -> dict[str, Any]:
    """Analyze all predeclared arms without using individual futures as replicates."""

    spec.validate()
    kernel = spec.cooption_spec()
    if tuple(audits) != DIRECT_VARIANTS:
        raise ValueError("direct-prediction audit variants are incomplete or reordered")
    summaries = {
        name: _summary(audits[name], kernel, spec, name) for name in DIRECT_VARIANTS
    }
    baseline_checks = _absolute_checks(summaries["rho90_full"], kernel)
    control_names = (
        "rho90_inert",
        "rho90_writer_only",
        "rho90_reader_only",
    )
    component_contrasts = {
        name: _paired_contrast(
            summaries, "rho90_full", name, "information_high", spec
        )
        for name in control_names
    }
    ecology_contrast = _paired_contrast(
        summaries, "rho90_full", "rho50_full", "information_high", spec
    )
    capacity_contrast = _paired_contrast(
        summaries, "rho90_full", "rho90_fixed_k1", "information_high", spec
    )
    cost_contrast = _paired_contrast(
        summaries, "rho90_full", "rho90_cost2", "information_high", spec
    )

    ecology_variants = (
        "rho50_full",
        "rho75_full",
        "rho90_full",
        "rho100_full",
    )
    x = np.asarray(
        [variant_settings(name)["predictive_persistence"] for name in ecology_variants],
        dtype=float,
    )
    centered_x = x - np.mean(x)
    denominator = float(np.sum(centered_x * centered_x))
    slopes: dict[str, float] = {}
    for task_index in range(spec.task_count):
        key = str(task_index)
        y = np.asarray(
            [
                summaries[name]["information_at_selected_ecology"]["task_values"][key]
                for name in ecology_variants
            ],
            dtype=float,
        )
        slopes[key] = float(np.sum(centered_x * (y - np.mean(y))) / denominator)
    ecology_slope = {
        "task_values": slopes,
        "interval": _interval(
            slopes.values(),
            spec.master_seed,
            "direct-prediction.ecology-gradient-slope",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }

    def contrast_pass(value: dict[str, Any]) -> bool:
        interval = value["interval"]
        return bool(
            float(interval["mean"]) >= spec.contrast_gate
            and float(interval["lower"]) > 0.0
        )

    predictions = {
        "P1_fresh_direct_origin": {
            "passes": all(baseline_checks.values()),
            "checks": baseline_checks,
            "meaning": "ordinary independent mutations reproduce all absolute PH gates",
        },
        "P2_writer_and_reader_are_jointly_necessary": {
            "passes": all(contrast_pass(value) for value in component_contrasts.values()),
            "contrasts": component_contrasts,
            "meaning": "full carrier beats inert, writer-only, and reader-only evolution",
        },
        "P3_predictability_selects_information": {
            "passes": bool(
                contrast_pass(ecology_contrast)
                and float(ecology_slope["interval"]["lower"]) > 0.0
            ),
            "rho90_minus_rho50": ecology_contrast,
            "task_clustered_gradient_slope": ecology_slope,
            "meaning": "more predictable parent-offspring environments select more useful inherited information",
        },
        "P4_more_than_one_locus_is_needed": {
            "passes": contrast_pass(capacity_contrast),
            "contrast": capacity_contrast,
            "meaning": "the unconstrained carrier beats evolution restricted to one two-bit locus",
        },
        "P5_information_emerges_during_selection": {
            "passes": bool(emergence["analysis"]["founder_to_final_information"]["passes"]),
            "evidence": emergence["analysis"]["founder_to_final_information"],
            "meaning": "fresh causal assays rise from generation zero to generation thirty",
        },
        "P6_mutational_pedigree_retains_information": {
            "passes": bool(pedigree["analysis"]["passes"]),
            "evidence": pedigree["analysis"],
            "meaning": "children and grandchildren retain the evolved information effect",
        },
    }
    result = {
        "format": DIRECT_ANALYSIS_FORMAT,
        "inferential_unit": "paired fresh Wagner founder task",
        "population_count": spec.population_count,
        "summaries": summaries,
        "baseline_absolute_checks": baseline_checks,
        "component_contrasts": component_contrasts,
        "ecology_contrast": ecology_contrast,
        "ecology_gradient_slope": ecology_slope,
        "capacity_contrast": capacity_contrast,
        "cost_sensitivity_contrast": cost_contrast,
        "predictions": predictions,
        "direct_origin_replicated": bool(predictions["P1_fresh_direct_origin"]["passes"]),
        "all_six_predictions_pass": all(value["passes"] for value in predictions.values()),
        "parent_diagnostic_digest": parent_diagnostic["diagnostic_digest"],
        "emergence_digest": emergence["emergence_digest"],
        "pedigree_digest": pedigree["pedigree_digest"],
        "protected_cooption_confirmation_seed_consumed": False,
        "claim_boundary": (
            "A pass establishes an accessible mechanism in this simulated Wagner model; "
            "it does not identify a natural molecular carrier."
        ),
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def render_direct_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# Wagner PH Direct Prediction v1 Report",
        "",
        "## Prospective question",
        "",
        "Can ordinary performance selection in a predictable parent–offspring environment originate a writable, readable, renewable carrier in Wagner GRNs without rewarding a memory label?",
        "",
        "## Outcome",
        "",
        f"- Fresh direct-origin replication: {'PASS' if analysis['direct_origin_replicated'] else 'FAIL'}.",
        f"- Complete six-prediction package: {'PASS' if analysis['all_six_predictions_pass'] else 'PARTIAL/FAIL'}.",
        "- The protected co-option confirmation seed was not consumed.",
        "",
        "## Registered predictions",
        "",
    ]
    for name, value in analysis["predictions"].items():
        lines.append(
            f"- `{name}`: {'PASS' if value['passes'] else 'FAIL'} — {value['meaning']}."
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
