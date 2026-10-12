"""Transparent observer-law calculations used by the L04 audit."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .stats import mean, median, spearman


def in_band(value: float, band: Sequence[float]) -> bool:
    if len(band) != 2:
        raise ValueError("band must contain exactly two bounds")
    return float(band[0]) <= float(value) <= float(band[1])


def nearest_centroid_accuracy(
    features: np.ndarray,
    labels: np.ndarray,
    train_mask: np.ndarray,
) -> float:
    """Nearest-centroid accuracy with explicit train/test validation."""

    features = np.asarray(features, dtype=np.float64)
    labels = np.asarray(labels)
    train_mask = np.asarray(train_mask, dtype=bool)
    if features.ndim != 2:
        raise ValueError("features must be a two-dimensional matrix")
    if len(features) != len(labels) or len(labels) != len(train_mask):
        raise ValueError("features, labels, and train mask must have equal rows")
    if not train_mask.any() or train_mask.all():
        raise ValueError("train and test partitions must both be non-empty")
    classes = np.unique(labels)
    missing = [value.item() if hasattr(value, "item") else value for value in classes
               if not np.any(train_mask & (labels == value))]
    if missing:
        raise ValueError(f"classes absent from training partition: {missing}")
    centroids = np.stack([
        features[train_mask & (labels == value)].mean(axis=0)
        for value in classes
    ])
    distances = np.linalg.norm(
        features[~train_mask, None, :] - centroids[None, :, :], axis=2
    )
    predictions = classes[np.argmin(distances, axis=1)]
    return float(np.mean(predictions == labels[~train_mask]))


def e25_gate_recalculation(
    rows: Iterable[Mapping[str, Any]],
    *,
    class4: Sequence[int],
    core3: Sequence[int],
    champions: Sequence[int],
    band: Sequence[float] = (0.005, 0.5),
) -> dict[str, Any]:
    by_rule = {int(row["rule"]): row for row in rows}
    required = set(class4) | set(core3) | set(champions)
    missing = sorted(required - set(by_rule))
    if missing:
        raise ValueError(f"E25 rows missing rules: {missing}")
    class4_rates = {str(rule): float(by_rule[rule]["strict"]) for rule in class4}
    core_rates = {str(rule): float(by_rule[rule]["strict"]) for rule in core3}
    champion_rates = {
        str(rule): float(by_rule[rule]["strict"]) for rule in champions
    }
    return {
        "gate_redemption_110": in_band(float(by_rule[110]["strict"]), band),
        "all_four_class4_in_band": all(
            in_band(float(by_rule[rule]["strict"]), band) for rule in class4
        ),
        "gate_chaos_stays_chaos": all(
            float(by_rule[rule]["strict"]) < float(band[0]) for rule in core3
        ),
        "gate_champions_stable": all(
            float(by_rule[rule]["strict"]) >= float(band[0])
            for rule in champions
        ),
        "class4_strict": class4_rates,
        "core3_strict": core_rates,
        "core3_strict_max": max(core_rates.values()),
        "champions_strict": champion_rates,
    }


def coverage_diagnostics(
    rows: Iterable[Mapping[str, Any]],
    *,
    band: Sequence[float] = (0.005, 0.5),
    target: float = 0.9,
) -> dict[str, Any]:
    data = list(rows)
    if not data:
        raise ValueError("coverage diagnostics need at least one row")
    coverage = [float(row["coverage"]) for row in data]
    sizes = [float(row["dictionary_size"]) for row in data]
    strict = [float(row["strict"]) for row in data]
    achieved = [value >= target for value in coverage]
    capable = [in_band(value, band) for value in strict]

    def finite_or_none(value: float) -> float | None:
        return float(value) if math.isfinite(value) else None

    high = [i for i, value in enumerate(achieved) if value]
    low = [i for i, value in enumerate(achieved) if not value]
    return {
        "n_rows": len(data),
        "coverage_target": float(target),
        "n_target_achieved": sum(achieved),
        "n_target_missed": len(data) - sum(achieved),
        "n_capable": sum(capable),
        "capable_among_target_achieved": sum(capable[i] for i in high),
        "capable_among_target_missed": sum(capable[i] for i in low),
        "capable_fraction_target_achieved": (
            mean(capable[i] for i in high) if high else None
        ),
        "capable_fraction_target_missed": (
            mean(capable[i] for i in low) if low else None
        ),
        "spearman_coverage_vs_strict": finite_or_none(spearman(coverage, strict)),
        "spearman_negative_size_vs_strict": finite_or_none(
            spearman([-value for value in sizes], strict)
        ),
    }


def paired_accuracy_diagnostics(
    raw: Sequence[float], figure: Sequence[float], *, chance: float
) -> dict[str, Any]:
    if len(raw) != len(figure) or not raw:
        raise ValueError("paired accuracy vectors must be non-empty and equal length")
    differences = [float(f) - float(r) for r, f in zip(raw, figure)]
    return {
        "n_tissues": len(differences),
        "raw_mean": mean(raw),
        "figure_mean": mean(figure),
        "figure_minus_raw_mean": mean(differences),
        "figure_minus_raw_median": median(differences),
        "figure_wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "raw_wins": sum(value < 0 for value in differences),
        "raw_minus_chance": mean(raw) - chance,
        "figure_minus_chance": mean(figure) - chance,
        "per_tissue_figure_minus_raw": differences,
    }


def e28_gate_recalculation(payload: Mapping[str, Any]) -> dict[str, Any]:
    gate1 = payload["gate1"]
    gate2 = payload["gate2"]
    gate3 = payload["gate3"]
    ladder = gate3["ladder"]
    sides = sorted(int(value) for value in ladder)
    nonzero = [value for value in sides if value]
    whole = [float(ladder[str(value)]["mean_h"]) for value in sides]
    biggest = str(max(nonzero))
    gate1_value = float(gate1["figure_accuracy"]) > float(gate1["raw_accuracy"])
    gate2_value = (
        float(gate2["rho_coverage_vs_capability"]) > float(gate2["null_q95"])
    )
    monotone = all(whole[i] >= whole[i + 1] for i in range(len(whole) - 1))
    figure_rises = (
        float(ladder[biggest]["figure_in"]) > float(ladder["0"]["figure_in"])
    )
    patch_below_rest = (
        float(ladder[biggest]["patch_h"]) < float(ladder[biggest]["rest_h"])
    )
    gate3_value = monotone and figure_rises and patch_below_rest
    calculated = {
        "gate_memory_at_boundaries": gate1_value,
        "gate_compressibility_law": gate2_value,
        "gate_decoupled_tumor": gate3_value,
    }
    stored = {key: bool(value) for key, value in payload["gates"].items()}
    return {
        "calculated": calculated,
        "stored": stored,
        "all_stored_gates_match": calculated == stored,
        "gate1_paired": paired_accuracy_diagnostics(
            gate1["per_tissue_raw"], gate1["per_tissue_figure"], chance=1 / 6
        ),
        "gate2": {
            "n_tissues": int(gate2["n_tissues"]),
            "rho": float(gate2["rho_coverage_vs_capability"]),
            "null_q95": float(gate2["null_q95"]),
        },
        "gate3_components": {
            "whole_fidelity_nonincreasing": monotone,
            "largest_patch_figure_rises": figure_rises,
            "largest_patch_below_rest": patch_below_rest,
            "whole_fidelity_by_side": {
                str(side): float(ladder[str(side)]["mean_h"]) for side in sides
            },
        },
    }


def e63_criteria(row: Mapping[str, Any]) -> dict[str, Any]:
    clone_bar = float(row["clone_bar"])
    clone_dt = float(row["clone_dt_mean"])
    clone_noise = float(row["clone_noise_mean"])
    within = float(row["within_mean"])
    same = float(row["same_tissue_mean"])
    ci = [float(value) for value in row["gap_within_minus_same_ci90"]]
    original_instrumented = clone_dt > clone_bar and clone_noise > clone_bar
    original_individuality = original_instrumented and ci[0] > 0
    revised_headroom = clone_noise > max(within, same)
    revised_power = int(row["n_within"]) >= 200
    revised_instrumented = revised_headroom and revised_power
    revised_individuality = revised_instrumented and ci[0] > 0
    return {
        "within_minus_same_mean": within - same,
        "reported_ci90": ci,
        "registered": {
            "clone_dt_beats_bar": clone_dt > clone_bar,
            "clone_noise_beats_bar": clone_noise > clone_bar,
            "instrumented": original_instrumented,
            "individuality": original_individuality,
        },
        "round4_revision": {
            "synthetic_noise_headroom": revised_headroom,
            "pair_count_power": revised_power,
            "instrumented": revised_instrumented,
            "individuality": revised_individuality,
        },
    }


def screen_census(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    data = list(rows)
    measured = [row for row in data if "h_above" in row]
    instrumented = [row for row in measured if row.get("instrumented") is True]
    return {
        "n_rows": len(data),
        "n_passing": sum(row.get("pass") is True for row in data),
        "n_instrumented": len(instrumented),
        "n_explicitly_uninstrumented": sum(
            row.get("instrumented") is False for row in measured
        ),
        "n_without_instrument_decision": len(data) - len(measured),
        "max_h_above": max((float(row["h_above"]) for row in measured), default=None),
        "max_h_above_instrumented": max(
            (float(row["h_above"]) for row in instrumented), default=None
        ),
        "n_tripwire_failed": sum(row.get("tripped") is True for row in measured),
    }
