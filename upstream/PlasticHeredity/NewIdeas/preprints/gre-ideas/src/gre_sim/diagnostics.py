"""Post-hoc, rulebook-level diagnostics derived from an immutable GRE run."""

from __future__ import annotations

import collections
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
from scipy.stats import rankdata

from .analysis import (
    RegistryContexts,
    _bootstrap_interval,
    _crossfit_direction,
    _group,
    _local_categories,
)
from .artifacts import (
    atomic_destination,
    canonical_digest,
    runtime_manifest,
    sha256_file,
    write_checksums,
    write_json,
)
from .config import StudySpec
from .rng import rng_for
from .study import load_run, verify_run


DIAGNOSTIC_FORMAT = "gre-pilot-diagnostics-v1"
DIAGNOSTIC_INTERVAL = 0.95
MINIMUM_BOOTSTRAP_REPETITIONS = 4_096
PRIMARY_ARM = "acute_mismatch"
PRIMARY_CARRYOVER = 1.0
STRATUM_ORDER = (
    "boolean.sampled",
    "wagner.sampled",
    "boolean.evolved",
    "wagner.evolved",
)
CONTRAST_ARMS = {
    "acute_minus_natural": ("acute_mismatch", "natural"),
    "acute_minus_developed": ("acute_mismatch", "developed_under_target"),
    "isomorphic_minus_natural": ("joint_isomorphic", "natural"),
    "acute_minus_independent": ("acute_mismatch", "independent_target"),
}


def _stratum(record: dict[str, Any]) -> str:
    return f"{record['engine']}.{record['cohort']}"


def _lambda_label(value: float) -> str:
    return f"lambda-{float(value):g}"


def _mean(records: Iterable[dict[str, Any]], name: str) -> float:
    values = [float(record[name]) for record in records]
    return float(np.mean(values)) if values else 0.0


def _numeric_summary(
    values: list[float],
    source_ids: list[str],
    repetitions: int,
    interval_level: float,
    rng: np.random.Generator,
    threshold: float | None = None,
) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        raise ValueError("a diagnostic summary cannot be empty")
    interval = _bootstrap_interval(array, repetitions, interval_level, rng)
    result: dict[str, Any] = {
        "rulebooks": int(array.size),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "standard_deviation": (
            float(np.std(array, ddof=1)) if array.size > 1 else 0.0
        ),
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
        "interval_level": interval_level,
        "bootstrap_repetitions": repetitions,
        "interval": list(interval),
        "count_positive": int(np.sum(array > 0.0)),
        "fraction_positive": float(np.mean(array > 0.0)),
    }
    if threshold is not None:
        result["threshold"] = threshold
        result["count_above_threshold"] = int(np.sum(array > threshold))
        result["fraction_above_threshold"] = float(np.mean(array > threshold))

    if array.size > 1:
        full_mean = float(np.mean(array))
        leave_one_out = (float(np.sum(array)) - array) / (array.size - 1)
        shifts = np.abs(leave_one_out - full_mean)
        influential = int(np.argmax(shifts))
        result["leave_one_out"] = {
            "minimum_mean": float(np.min(leave_one_out)),
            "maximum_mean": float(np.max(leave_one_out)),
            "maximum_absolute_shift": float(shifts[influential]),
            "most_influential_source": source_ids[influential],
        }
    else:
        result["leave_one_out"] = None
    return result


def _calibration(records: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    if prefix not in {"committor", "baseline"}:
        raise ValueError(prefix)
    bin_count = 10
    bins: list[list[dict[str, Any]]] = [[] for _ in range(bin_count)]
    for record in records:
        confidence = float(record[f"{prefix}_confidence"])
        index = min(int(confidence * bin_count), bin_count - 1)
        bins[index].append(record)

    rendered: list[dict[str, Any]] = []
    ece = 0.0
    total = len(records)
    for index, values in enumerate(bins):
        if not values:
            continue
        confidence = _mean(values, f"{prefix}_confidence")
        accuracy = _mean(values, f"{prefix}_correct")
        count = len(values)
        ece += count / total * abs(accuracy - confidence)
        rendered.append(
            {
                "lower": index / bin_count,
                "upper": (index + 1) / bin_count,
                "count": count,
                "mean_confidence": confidence,
                "accuracy": accuracy,
                "absolute_gap": abs(accuracy - confidence),
            }
        )
    return {
        "records": total,
        "mean_log_loss": _mean(records, f"{prefix}_loss"),
        "mean_brier": _mean(records, f"{prefix}_brier"),
        "accuracy": _mean(records, f"{prefix}_correct"),
        "mean_confidence": _mean(records, f"{prefix}_confidence"),
        "mean_probability_assigned_to_observed": _mean(
            records, f"{prefix}_probability"
        ),
        "expected_calibration_error": float(ece),
        "bins": rendered,
    }


def _normalized_entropy(
    records: list[dict[str, Any]], categories: tuple[str, ...]
) -> tuple[float, int]:
    counts = collections.Counter(str(record["destination"]) for record in records)
    total = sum(counts.values())
    probabilities = [count / total for count in counts.values() if count]
    entropy = -sum(value * math.log(value) for value in probabilities)
    denominator = math.log(len(categories)) if len(categories) > 1 else 1.0
    return float(entropy / denominator), len(counts)


def _source_primary_diagnostics(
    records: list[dict[str, Any]],
    scored: list[dict[str, Any]],
    registry: dict[str, Any],
    contexts: RegistryContexts,
) -> list[dict[str, Any]]:
    primary_records = [
        record
        for record in records
        if record["arm"] == PRIMARY_ARM
        and float(record["carryover"]) == PRIMARY_CARRYOVER
    ]
    primary_scored = [
        record
        for record in scored
        if record["arm"] == PRIMARY_ARM
        and float(record["carryover"]) == PRIMARY_CARRYOVER
    ]
    raw_groups = _group(primary_records, ("engine", "cohort", "source_id"))
    scored_groups = _group(primary_scored, ("engine", "cohort", "source_id"))
    bundles = {str(bundle["source_id"]): bundle for bundle in registry["sources"]}
    output: list[dict[str, Any]] = []

    for key, scored_values in sorted(scored_groups.items()):
        engine, cohort, source_id = str(key[0]), str(key[1]), str(key[2])
        raw_values = raw_groups[(key[0], key[1], key[2])]
        cell_groups = _group(raw_values, ("state_id",))
        entropies: list[float] = []
        destination_counts: list[int] = []
        for (state_id,), cell_values in sorted(cell_groups.items()):
            context = contexts.get(source_id, int(state_id), PRIMARY_ARM)
            entropy, count = _normalized_entropy(
                cell_values, _local_categories(context)
            )
            entropies.append(entropy)
            destination_counts.append(count)

        landscape = bundles[source_id]["source_landscape"]
        attractors = list(landscape["attractors"])
        output.append(
            {
                "engine": engine,
                "cohort": cohort,
                "stratum": f"{engine}.{cohort}",
                "source_id": source_id,
                "evaluation_records": len(scored_values),
                "mean_gain": _mean(scored_values, "gain"),
                "mean_committor_loss": _mean(scored_values, "committor_loss"),
                "mean_baseline_loss": _mean(scored_values, "baseline_loss"),
                "mean_committor_brier": _mean(scored_values, "committor_brier"),
                "mean_baseline_brier": _mean(scored_values, "baseline_brier"),
                "committor_accuracy": _mean(scored_values, "committor_correct"),
                "baseline_accuracy": _mean(scored_values, "baseline_correct"),
                "baseline_counts": dict(
                    sorted(
                        collections.Counter(
                            str(record["baseline"]) for record in scored_values
                        ).items()
                    )
                ),
                "active_capture_rate": _mean(raw_values, "active_capture"),
                "strict_rate": _mean(raw_values, "strict_event"),
                "old_return_rate": _mean(raw_values, "old_return"),
                "normalized_destination_entropy": float(np.mean(entropies)),
                "mean_observed_destination_count": float(
                    np.mean(destination_counts)
                ),
                "landscape": {
                    "point_attractors": sum(len(value) == 1 for value in attractors),
                    "total_attractors": len(attractors),
                    "basin_entropy": float(landscape["basin_entropy"]),
                    "mean_transient": float(landscape["mean_transient"]),
                },
            }
        )
    return output


def _rank_correlation(left: list[float], right: list[float]) -> float | None:
    x = np.asarray(left, dtype=float)
    y = np.asarray(right, dtype=float)
    if x.size < 3 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    correlation = float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
    return correlation if np.isfinite(correlation) else None


def _geometry_correlations(sources: list[dict[str, Any]]) -> dict[str, Any]:
    gains = [float(source["mean_gain"]) for source in sources]
    metrics = {
        "active_capture_rate": [float(source["active_capture_rate"]) for source in sources],
        "strict_rate": [float(source["strict_rate"]) for source in sources],
        "normalized_destination_entropy": [
            float(source["normalized_destination_entropy"]) for source in sources
        ],
        "mean_observed_destination_count": [
            float(source["mean_observed_destination_count"]) for source in sources
        ],
        "point_attractors": [
            float(source["landscape"]["point_attractors"]) for source in sources
        ],
        "total_attractors": [
            float(source["landscape"]["total_attractors"]) for source in sources
        ],
        "basin_entropy": [
            float(source["landscape"]["basin_entropy"]) for source in sources
        ],
        "mean_transient": [
            float(source["landscape"]["mean_transient"]) for source in sources
        ],
    }
    return {
        name: {
            "spearman_gain_correlation": _rank_correlation(gains, values),
            "rulebooks": len(sources),
        }
        for name, values in metrics.items()
    }


def _primary_diagnostics(
    records: list[dict[str, Any]],
    scored: list[dict[str, Any]],
    registry: dict[str, Any],
    contexts: RegistryContexts,
    spec: StudySpec,
    repetitions: int,
) -> dict[str, Any]:
    sources = _source_primary_diagnostics(records, scored, registry, contexts)
    primary_scored = [
        record
        for record in scored
        if record["arm"] == PRIMARY_ARM
        and float(record["carryover"]) == PRIMARY_CARRYOVER
    ]
    result: dict[str, Any] = {"strata": {}, "per_rulebook": sources}
    available = sorted({source["stratum"] for source in sources})
    ordered = [name for name in STRATUM_ORDER if name in available]
    ordered.extend(name for name in available if name not in ordered)
    for stratum in ordered:
        source_values = [source for source in sources if source["stratum"] == stratum]
        scored_values = [record for record in primary_scored if _stratum(record) == stratum]
        ids = [str(source["source_id"]) for source in source_values]
        gains = [float(source["mean_gain"]) for source in source_values]
        result["strata"][stratum] = {
            "gain": _numeric_summary(
                gains,
                ids,
                repetitions,
                DIAGNOSTIC_INTERVAL,
                rng_for(spec.master_seed, "diagnostic", "gain", stratum),
                spec.advancement_log_loss_gain,
            ),
            "baseline_counts": dict(
                sorted(
                    collections.Counter(
                        str(record["baseline"]) for record in scored_values
                    ).items()
                )
            ),
            "calibration": {
                "committor": _calibration(scored_values, "committor"),
                "baseline": _calibration(scored_values, "baseline"),
            },
            "geometry_correlations": _geometry_correlations(source_values),
        }
    return result


def _rulebook_rates(
    records: list[dict[str, Any]],
) -> dict[tuple[str, str, str, str, float], dict[str, float]]:
    groups = _group(
        records, ("engine", "cohort", "source_id", "arm", "carryover")
    )
    return {
        (str(key[0]), str(key[1]), str(key[2]), str(key[3]), float(key[4])): {
            "strict_rate": _mean(values, "strict_event"),
            "active_capture_rate": _mean(values, "active_capture"),
            "old_return_rate": _mean(values, "old_return"),
        }
        for key, values in groups.items()
    }


def _paired_controls(
    records: list[dict[str, Any]], spec: StudySpec, repetitions: int
) -> dict[str, Any]:
    rates = _rulebook_rates(records)
    source_ids: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for engine, cohort, source_id, arm, carryover in rates:
        if arm == "natural" and carryover == float(spec.carryover_values[0]):
            source_ids[(engine, cohort)].append(source_id)
    for key in source_ids:
        source_ids[key] = sorted(set(source_ids[key]))

    cells: dict[str, Any] = {}
    contrasts: dict[str, Any] = {}
    interactions: dict[str, Any] = {}
    for (engine, cohort), ids in sorted(source_ids.items()):
        stratum = f"{engine}.{cohort}"
        for carryover in spec.carryover_values:
            carry = float(carryover)
            for arm in spec.arms:
                values = [
                    rates[(engine, cohort, source_id, arm, carry)]
                    for source_id in ids
                    if (engine, cohort, source_id, arm, carry) in rates
                ]
                if not values:
                    continue
                strict_values = [value["strict_rate"] for value in values]
                label = f"{stratum}.{arm}.{_lambda_label(carry)}"
                cells[label] = {
                    "rulebooks": len(values),
                    "strict_rate": float(np.mean(strict_values)),
                    "strict_interval": list(
                        _bootstrap_interval(
                            np.asarray(strict_values),
                            repetitions,
                            DIAGNOSTIC_INTERVAL,
                            rng_for(spec.master_seed, "diagnostic", "cell", label),
                        )
                    ),
                    "active_capture_rate": float(
                        np.mean([value["active_capture_rate"] for value in values])
                    ),
                    "old_return_rate": float(
                        np.mean([value["old_return_rate"] for value in values])
                    ),
                }

            for name, (first_arm, second_arm) in CONTRAST_ARMS.items():
                paired = []
                paired_ids = []
                for source_id in ids:
                    first_key = (engine, cohort, source_id, first_arm, carry)
                    second_key = (engine, cohort, source_id, second_arm, carry)
                    if first_key in rates and second_key in rates:
                        paired.append(
                            rates[first_key]["strict_rate"]
                            - rates[second_key]["strict_rate"]
                        )
                        paired_ids.append(source_id)
                label = f"{stratum}.{_lambda_label(carry)}.{name}"
                summary = _numeric_summary(
                    paired,
                    paired_ids,
                    repetitions,
                    DIAGNOSTIC_INTERVAL,
                    rng_for(spec.master_seed, "diagnostic", "contrast", label),
                )
                summary["per_rulebook"] = [
                    {"source_id": source_id, "difference": value}
                    for source_id, value in zip(paired_ids, paired)
                ]
                contrasts[label] = summary

        if 0.0 in spec.carryover_values and 1.0 in spec.carryover_values:
            for name, (first_arm, second_arm) in CONTRAST_ARMS.items():
                paired = []
                paired_ids = []
                for source_id in ids:
                    keys = [
                        (engine, cohort, source_id, first_arm, 1.0),
                        (engine, cohort, source_id, second_arm, 1.0),
                        (engine, cohort, source_id, first_arm, 0.0),
                        (engine, cohort, source_id, second_arm, 0.0),
                    ]
                    if all(key in rates for key in keys):
                        paired.append(
                            (rates[keys[0]]["strict_rate"] - rates[keys[1]]["strict_rate"])
                            - (rates[keys[2]]["strict_rate"] - rates[keys[3]]["strict_rate"])
                        )
                        paired_ids.append(source_id)
                label = f"{stratum}.{name}"
                summary = _numeric_summary(
                    paired,
                    paired_ids,
                    repetitions,
                    DIAGNOSTIC_INTERVAL,
                    rng_for(spec.master_seed, "diagnostic", "interaction", label),
                )
                summary["per_rulebook"] = [
                    {"source_id": source_id, "difference_in_differences": value}
                    for source_id, value in zip(paired_ids, paired)
                ]
                interactions[label] = summary
    return {"cells": cells, "contrasts": contrasts, "interactions": interactions}


def diagnose_records(
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    archived_analysis: dict[str, Any],
    spec: StudySpec,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Compute deterministic post-hoc diagnostics without changing the frozen gate."""

    repetitions = max(spec.bootstrap_repetitions, MINIMUM_BOOTSTRAP_REPETITIONS)
    contexts = RegistryContexts(registry)
    if progress is not None:
        progress("cross-fitting diagnostic direction A to B")
    scored = _crossfit_direction(records, contexts, "A", spec)
    if progress is not None:
        progress("cross-fitting diagnostic direction B to A")
    scored.extend(_crossfit_direction(records, contexts, "B", spec))
    if progress is not None:
        progress("summarizing rulebooks, calibration, geometry, and paired controls")
    return {
        "format": DIAGNOSTIC_FORMAT,
        "status": "post-hoc exploratory; cannot alter the frozen pilot decision",
        "cohort_id": spec.cohort_id,
        "protocol_format": spec.protocol_format,
        "source_futures": len(records),
        "diagnostic_contract": {
            "primary_arm": PRIMARY_ARM,
            "primary_carryover": PRIMARY_CARRYOVER,
            "interval_level": DIAGNOSTIC_INTERVAL,
            "bootstrap_repetitions": repetitions,
            "inference_unit": "source rulebook",
        },
        "archived_decision": {
            "eligible_for_advancement_gate": archived_analysis[
                "eligible_for_advancement_gate"
            ],
            "advance_to_confirmation": archived_analysis["advance_to_confirmation"],
            "primary": archived_analysis["primary"],
        },
        "primary_rulebook_diagnostics": _primary_diagnostics(
            records, scored, registry, contexts, spec, repetitions
        ),
        "paired_controls": _paired_controls(records, spec, repetitions),
    }


def _interval_text(summary: dict[str, Any], scale: float = 1.0) -> str:
    lower, upper = summary["interval"]
    return (
        f"{scale * summary['mean']:.3f} "
        f"[{scale * lower:.3f}, {scale * upper:.3f}]"
    )


def _correlation_text(value: float | None) -> str:
    return "—" if value is None else f"{value:+.3f}"


def render_diagnostic_report(diagnostic: dict[str, Any], source_run: Path) -> str:
    primary = diagnostic["primary_rulebook_diagnostics"]["strata"]
    paired = diagnostic["paired_controls"]
    available = [name for name in STRATUM_ORDER if name in primary]
    lines = [
        "# Pilot v1 diagnostic report",
        "",
        "> This is a deterministic post-hoc diagnostic of the sealed pilot. It cannot revise the frozen advancement decision and is not confirmatory evidence.",
        "",
        f"- Source run: `{source_run.resolve()}`",
        f"- Source futures: {diagnostic['source_futures']:,}",
        f"- Inference unit: source rulebook",
        f"- Diagnostic interval: {100 * DIAGNOSTIC_INTERVAL:.0f}% rulebook bootstrap",
        "",
        "## Frozen outcome",
        "",
        f"**Advance to confirmation: {'yes' if diagnostic['archived_decision']['advance_to_confirmation'] else 'no'}.**",
        "",
        "Randomly sampled networks failed the frozen primary gate in both engines. Evolved networks remain positive controls for an evolvable, selection-conditioned effect; they cannot rescue sampled failure.",
        "",
        "## Rulebook-level committor gains",
        "",
        "Positive gain means the state-specific committor beats the cross-rulebook-selected baseline on held-out futures.",
        "",
        "| Stratum | Rulebooks | Mean and 95% diagnostic interval | Median | Positive | Above +0.02 | Leave-one-out mean range |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for stratum in available:
        gain = primary[stratum]["gain"]
        leave = gain["leave_one_out"]
        leave_text = (
            "—"
            if leave is None
            else f"{leave['minimum_mean']:.4f} to {leave['maximum_mean']:.4f}"
        )
        lines.append(
            f"| {stratum} | {gain['rulebooks']} | {_interval_text(gain)} | "
            f"{gain['median']:.4f} | {gain['count_positive']}/{gain['rulebooks']} | "
            f"{gain['count_above_threshold']}/{gain['rulebooks']} | {leave_text} |"
        )
    lines.extend(
        [
            "",
            "![Rulebook-level gains](figures/rulebook_committor_gains.png)",
            "",
            "## Predictive calibration",
            "",
            "Lower log loss, Brier score, and calibration error are better; higher accuracy is better.",
            "",
            "| Stratum | Model | Log loss | Brier | Accuracy | Calibration error |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for stratum in available:
        for model in ("committor", "baseline"):
            value = primary[stratum]["calibration"][model]
            lines.append(
                f"| {stratum} | {model} | {value['mean_log_loss']:.4f} | "
                f"{value['mean_brier']:.4f} | {value['accuracy']:.4f} | "
                f"{value['expected_calibration_error']:.4f} |"
            )
    lines.extend(
        [
            "",
            "![Calibration](figures/primary_calibration.png)",
            "",
            "## Paired strict-event controls",
            "",
            "Contrasts are paired within source rulebook and reported in percentage points. They are diagnostic, not replacements for the frozen committor endpoint.",
            "",
            "| Stratum | Carryover | Acute − natural | Acute − developed | Isomorphic − natural | Single-attractor rate | Acute capture |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for stratum in available:
        for carry in (0.0, 1.0):
            carry_label = _lambda_label(carry)
            prefix = f"{stratum}.{carry_label}"
            acute_natural = paired["contrasts"][f"{prefix}.acute_minus_natural"]
            acute_developed = paired["contrasts"][f"{prefix}.acute_minus_developed"]
            iso_natural = paired["contrasts"][f"{prefix}.isomorphic_minus_natural"]
            single = paired["cells"][f"{stratum}.single_attractor.{carry_label}"]
            acute = paired["cells"][f"{stratum}.acute_mismatch.{carry_label}"]
            lines.append(
                f"| {stratum} | {carry:g} | {_interval_text(acute_natural, 100.0)} | "
                f"{_interval_text(acute_developed, 100.0)} | "
                f"{_interval_text(iso_natural, 100.0)} | "
                f"{100 * single['strict_rate']:.2f}% | "
                f"{100 * acute['active_capture_rate']:.2f}% |"
            )
    lines.extend(
        [
            "",
            "![Paired strict-event contrasts](figures/paired_strict_contrasts.png)",
            "",
            "The exact-isomorphic contrast checks the permutation implementation. The single-attractor arm is a forced-convergence control: its high strict rate demonstrates that raw strict-event occurrence is not specific evidence of plastic heredity.",
            "",
            "## Geometry and capture associations",
            "",
            "Spearman correlations below relate rulebook-level primary gain to pre-existing landscape or outcome summaries. They are descriptive and unadjusted for multiple exploration.",
            "",
            "| Stratum | Active capture | Destination entropy | Point attractors | Basin entropy | Mean transient |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for stratum in available:
        correlations = primary[stratum]["geometry_correlations"]
        lines.append(
            f"| {stratum} | "
            f"{_correlation_text(correlations['active_capture_rate']['spearman_gain_correlation'])} | "
            f"{_correlation_text(correlations['normalized_destination_entropy']['spearman_gain_correlation'])} | "
            f"{_correlation_text(correlations['point_attractors']['spearman_gain_correlation'])} | "
            f"{_correlation_text(correlations['basin_entropy']['spearman_gain_correlation'])} | "
            f"{_correlation_text(correlations['mean_transient']['spearman_gain_correlation'])} |"
        )

    single_rates = [
        value["strict_rate"]
        for name, value in paired["cells"].items()
        if ".single_attractor." in name
    ]
    full_developed = [
        abs(
            paired["contrasts"][
                f"{stratum}.lambda-1.acute_minus_developed"
            ]["mean"]
        )
        for stratum in available
    ]
    lines.extend(
        [
            "",
            "## Interpretation and next decision",
            "",
            "1. The sampled-network failure is not an evolved-cohort power problem: the diagnostic keeps every stratum separate and preserves the frozen no-advance decision.",
            "2. Evolved gains motivate a new evolutionary question—whether selection creates state-conditioned destination information—not a retroactive generic-rehoming claim.",
            f"3. Under full carryover, acute and developed-under-target strict rates differ by at most {100 * max(full_developed):.2f} percentage points across strata. Raw acute mismatch is therefore not a unique mechanism indicator.",
            f"4. Single-attractor strict rates span {100 * min(single_rates):.2f}% to {100 * max(single_rates):.2f}%. The strict endpoint must remain secondary and contrast-based.",
            "5. Pilot v2 should increase independent rulebooks, add a history-erasure control, retain exact isomorphism, and require both held-out committor gain and a mismatch-specific paired effect before confirmation is considered.",
            "",
            "All per-rulebook values, paired contrasts, calibration bins, correlations, source provenance, and checksums are retained in `diagnostics.json` and `SHA256SUMS`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_diagnostic_figures(directory: Path, diagnostic: dict[str, Any]) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    primary = diagnostic["primary_rulebook_diagnostics"]
    strata = [name for name in STRATUM_ORDER if name in primary["strata"]]
    with tempfile.TemporaryDirectory(prefix="gre-diagnostic-mpl-") as cache:
        os.environ.setdefault("MPLCONFIGDIR", cache)
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axis = plt.subplots(figsize=(9, 5))
        for index, stratum in enumerate(strata):
            sources = [
                source
                for source in primary["per_rulebook"]
                if source["stratum"] == stratum
            ]
            sources.sort(key=lambda source: (source["mean_gain"], source["source_id"]))
            offsets = np.linspace(-0.18, 0.18, len(sources))
            axis.scatter(
                index + offsets,
                [source["mean_gain"] for source in sources],
                s=24,
                alpha=0.75,
                color="#4472c4",
            )
            summary = primary["strata"][stratum]["gain"]
            axis.errorbar(
                index,
                summary["mean"],
                yerr=[
                    [summary["mean"] - summary["interval"][0]],
                    [summary["interval"][1] - summary["mean"]],
                ],
                fmt="D",
                color="black",
                capsize=4,
                zorder=3,
            )
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.axhline(0.02, color="#c00000", linestyle="--", linewidth=0.9)
        axis.set_xticks(np.arange(len(strata)), strata, rotation=20, ha="right")
        axis.set_ylabel("Held-out log-loss gain (nats)")
        axis.set_title("Rulebook-level destination-committor gains")
        figure.tight_layout()
        figure.savefig(directory / "rulebook_committor_gains.png", dpi=160)
        plt.close(figure)

        figure, axes = plt.subplots(2, 2, figsize=(9, 8), sharex=True, sharey=True)
        for axis, stratum in zip(axes.flat, strata):
            for model, color in (("committor", "#4472c4"), ("baseline", "#ed7d31")):
                bins = primary["strata"][stratum]["calibration"][model]["bins"]
                axis.plot(
                    [value["mean_confidence"] for value in bins],
                    [value["accuracy"] for value in bins],
                    marker="o",
                    label=model,
                    color=color,
                )
            axis.plot([0, 1], [0, 1], color="black", linestyle=":", linewidth=0.8)
            axis.set_title(stratum)
            axis.set_xlim(0, 1)
            axis.set_ylim(0, 1)
        for axis in axes[-1, :]:
            axis.set_xlabel("Mean confidence")
        for axis in axes[:, 0]:
            axis.set_ylabel("Observed accuracy")
        axes[0, 0].legend()
        figure.suptitle("Primary-cell multiclass calibration")
        figure.tight_layout()
        figure.savefig(directory / "primary_calibration.png", dpi=160)
        plt.close(figure)

        paired = diagnostic["paired_controls"]["contrasts"]
        labels: list[str] = []
        values: list[dict[str, Any]] = []
        colors: list[str] = []
        for stratum in strata:
            for carry in (0.0, 1.0):
                for name, short, color in (
                    ("acute_minus_natural", "A−N", "#70ad47"),
                    ("acute_minus_developed", "A−D", "#ed7d31"),
                ):
                    labels.append(f"{stratum} λ={carry:g} {short}")
                    values.append(
                        paired[f"{stratum}.{_lambda_label(carry)}.{name}"]
                    )
                    colors.append(color)
        positions = np.arange(len(labels))
        means = np.asarray([100 * value["mean"] for value in values])
        lower = np.asarray([100 * value["interval"][0] for value in values])
        upper = np.asarray([100 * value["interval"][1] for value in values])
        figure, axis = plt.subplots(figsize=(9, 8))
        for position, mean, low, high, color in zip(
            positions, means, lower, upper, colors
        ):
            axis.errorbar(
                mean,
                position,
                xerr=[[mean - low], [high - mean]],
                fmt="none",
                ecolor=color,
                capsize=3,
            )
        axis.scatter(means, positions, color=colors, s=28, zorder=3)
        axis.axvline(0.0, color="black", linewidth=0.8)
        axis.set_yticks(positions, labels)
        axis.invert_yaxis()
        axis.set_xlabel("Paired strict-rate difference (percentage points)")
        axis.set_title("Post-hoc strict-event control contrasts")
        figure.tight_layout()
        figure.savefig(directory / "paired_strict_contrasts.png", dpi=160)
        plt.close(figure)

    return [
        "figures/rulebook_committor_gains.png",
        "figures/primary_calibration.png",
        "figures/paired_strict_contrasts.png",
    ]


def derive_diagnostics(
    source_run: Path,
    destination: Path,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Verify a sealed run and write immutable derived diagnostics elsewhere."""

    if progress is not None:
        progress("verifying sealed source artifacts")
    verification = verify_run(source_run)
    if progress is not None:
        progress("loading frozen rulebooks and future summaries")
    spec, registry, records, archived = load_run(source_run)
    diagnostic = diagnose_records(records, registry, archived, spec, progress)
    source_checksum = sha256_file(source_run / "SHA256SUMS")
    with atomic_destination(destination) as temporary:
        if progress is not None:
            progress("rendering diagnostic report and figures")
        write_json(temporary / "diagnostics.json", diagnostic)
        figures = write_diagnostic_figures(temporary / "figures", diagnostic)
        manifest = {
            "format": "gre-derived-diagnostic-manifest-v1",
            "source_run": str(source_run.resolve()),
            "source_checksum_manifest_sha256": source_checksum,
            "source_analysis_digest": canonical_digest(archived),
            "source_verification": verification,
            "diagnostic_format": DIAGNOSTIC_FORMAT,
            "diagnostic_digest": canonical_digest(diagnostic),
            "runtime": runtime_manifest(),
            "figures": figures,
        }
        write_json(temporary / "manifest.json", manifest)
        (temporary / "PILOT_V1_DIAGNOSTIC_REPORT.md").write_text(
            render_diagnostic_report(diagnostic, source_run), encoding="utf-8"
        )
        write_checksums(temporary)
        if progress is not None:
            progress("sealed derived diagnostics and checksums")
    return destination.resolve()
