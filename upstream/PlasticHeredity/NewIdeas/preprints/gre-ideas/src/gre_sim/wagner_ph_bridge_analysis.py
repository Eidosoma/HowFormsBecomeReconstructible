"""Prospective repeatability, information, phase, and causal analyses."""

from __future__ import annotations

import collections
import itertools
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import canonical_digest, read_jsonl_gz
from .local_ph_config import LocalCarrierGenome, LocalStudySpec
from .rng import rng_for
from .wagner_ph_bridge_config import (
    BRIDGE_ANALYSIS_FORMAT,
    PhaseDiagramSpec,
    PrecisionReplicationSpec,
)


CellKey = tuple[str, int, str, str, int | None, str]


def _index_records(
    records: Iterable[dict[str, Any]], block_size: int | None = None
) -> tuple[dict[CellKey, list[float]], list[dict[str, Any]], float]:
    counts: dict[CellKey, list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    retained: list[dict[str, Any]] = []
    acquired: dict[tuple[str, str, int], bool] = {}
    for record in records:
        retained.append(record)
        block = (
            int(record["future_index"]) // block_size if block_size is not None else None
        )
        for field in ("correct_hold8", "wrong_hold8", "returned"):
            keys = [
                (
                    str(record["condition"]),
                    int(record["generation"]),
                    str(record["challenge"]),
                    str(record["source_id"]),
                    block,
                    field,
                )
            ]
            if block_size is not None:
                keys.append((*keys[0][:4], None, field))
            for key in keys:
                counts[key][0] += float(record[field])
                counts[key][1] += 1.0
        acquired[
            (
                str(record["source_id"]),
                str(record["history"]),
                int(record["future_index"]),
            )
        ] = bool(record["acquired"])
    acquisition_rate = float(np.mean(list(acquired.values()))) if acquired else 0.0
    return counts, retained, acquisition_rate


def _source_differences(
    counts: dict[CellKey, list[float]],
    left: str,
    right: str,
    generation: int,
    challenge: str,
    field: str = "correct_hold8",
    block: int | None = None,
) -> dict[str, float]:
    sources = sorted({key[3] for key in counts})
    result: dict[str, float] = {}
    for source in sources:
        rates: dict[str, float] = {}
        for condition in (left, right):
            matched = [
                value
                for key, value in counts.items()
                if key[0] == condition
                and key[1] == generation
                and key[2] == challenge
                and key[3] == source
                and key[4] == block
                and key[5] == field
            ]
            numerator = sum(value[0] for value in matched)
            denominator = sum(value[1] for value in matched)
            if denominator:
                rates[condition] = numerator / denominator
        if len(rates) == 2:
            result[source] = rates[left] - rates[right]
    return result


def _interval(
    values: Iterable[float],
    seed: str,
    label: str,
    repetitions: int,
    level: float,
    simultaneous: int = 1,
) -> dict[str, Any]:
    array = np.asarray(tuple(values), dtype=float)
    if not array.size:
        return {
            "mean": None,
            "interval": [None, None],
            "lower": None,
            "upper": None,
            "sources": 0,
            "positive_sources": 0,
        }
    random = rng_for(seed, "wagner-ph-bridge-bootstrap", label)
    indices = random.integers(0, array.size, size=(repetitions, array.size))
    means = np.mean(array[indices], axis=1)
    tail = (1.0 - level) / 2.0
    simultaneous_tail = (1.0 - level) / max(2, 2 * simultaneous)
    return {
        "mean": float(np.mean(array)),
        "interval": [
            float(np.quantile(means, tail)),
            float(np.quantile(means, 1.0 - tail)),
        ],
        "lower": float(np.quantile(means, simultaneous_tail)),
        "upper": float(np.quantile(means, 1.0 - simultaneous_tail)),
        "sources": int(array.size),
        "positive_sources": int(np.sum(array > 0.0)),
    }


def _pairwise_correlations(matrix: np.ndarray) -> list[float]:
    values: list[float] = []
    if matrix.ndim != 2:
        return values
    for left, right in itertools.combinations(range(matrix.shape[1]), 2):
        a = matrix[:, left]
        b = matrix[:, right]
        if len(a) < 3 or float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
            continue
        values.append(float(np.corrcoef(a, b)[0, 1]))
    return values


def icc_2_1(matrix: np.ndarray) -> float | None:
    """Two-way random, absolute-agreement ICC(2,1)."""

    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or min(values.shape) < 2:
        return None
    subjects, raters = values.shape
    grand = float(np.mean(values))
    row_means = np.mean(values, axis=1)
    column_means = np.mean(values, axis=0)
    ms_rows = raters * float(np.sum((row_means - grand) ** 2)) / (subjects - 1)
    ms_columns = subjects * float(np.sum((column_means - grand) ** 2)) / (raters - 1)
    residual = values - row_means[:, None] - column_means[None, :] + grand
    ms_error = float(np.sum(residual**2)) / ((subjects - 1) * (raters - 1))
    denominator = (
        ms_rows
        + (raters - 1) * ms_error
        + raters * (ms_columns - ms_error) / subjects
    )
    return float((ms_rows - ms_error) / denominator) if denominator else None


def _rate_matrix(
    counts: dict[CellKey, list[float]],
    condition: str,
    generation: int,
    challenge: str,
    blocks: int,
    field: str = "correct_hold8",
) -> tuple[list[str], np.ndarray]:
    sources = sorted({key[3] for key in counts})
    matrix = np.full((len(sources), blocks), np.nan, dtype=float)
    for row, source in enumerate(sources):
        for block in range(blocks):
            value = counts.get((condition, generation, challenge, source, block, field))
            if value and value[1]:
                matrix[row, block] = value[0] / value[1]
    complete = np.all(np.isfinite(matrix), axis=1)
    return [source for source, keep in zip(sources, complete) if keep], matrix[complete]


def analyze_precision_path(path: Path, spec: PrecisionReplicationSpec) -> dict[str, Any]:
    spec.validate()
    counts, records, acquisition_rate = _index_records(
        read_jsonl_gz(path), spec.reliability.block_size
    )
    candidates: dict[str, Any] = {}
    simultaneous = max(1, len(spec.study.genomes) * spec.reliability.blocks)
    for genome in spec.study.genomes:
        condition = f"{genome.name}.intact"
        block_differences = [
            _source_differences(
                counts, condition, "zero", 4, "forced_break", block=block
            )
            for block in range(spec.reliability.blocks)
        ]
        block_effects = [
            _interval(
                values.values(),
                spec.study.master_seed,
                f"precision.{genome.name}.block-{block}",
                spec.study.bootstrap_repetitions,
                spec.reliability.interval_level,
                simultaneous,
            )
            for block, values in enumerate(block_differences)
        ]
        aggregate_values = _source_differences(
            counts, condition, "zero", 4, "forced_break", block=None
        )
        aggregate = _interval(
            aggregate_values.values(),
            spec.study.master_seed,
            f"precision.{genome.name}.aggregate",
            spec.study.bootstrap_repetitions,
            spec.reliability.interval_level,
            len(spec.study.genomes),
        )
        equivalence: list[dict[str, Any]] = []
        for left, right in itertools.combinations(range(spec.reliability.blocks), 2):
            common = sorted(set(block_differences[left]) & set(block_differences[right]))
            contrast = _interval(
                (
                    block_differences[left][source] - block_differences[right][source]
                    for source in common
                ),
                spec.study.master_seed,
                f"precision.{genome.name}.equivalence.{left}.{right}",
                spec.study.bootstrap_repetitions,
                spec.reliability.equivalence_interval_level,
                1,
            )
            passed = (
                contrast["interval"][0] is not None
                and float(contrast["interval"][0]) > -spec.reliability.equivalence_margin
                and float(contrast["interval"][1]) < spec.reliability.equivalence_margin
            )
            equivalence.append(
                {"left_block": left, "right_block": right, "passed": passed, **contrast}
            )
        sources, local_rates = _rate_matrix(
            counts,
            condition,
            4,
            "forced_break",
            spec.reliability.blocks,
        )
        gain_matrix = np.asarray(
            [
                [block_differences[block][source] for block in range(spec.reliability.blocks)]
                for source in sources
            ],
            dtype=float,
        )
        concordant = int(
            np.sum(
                np.sum(gain_matrix > 0.0, axis=1)
                >= spec.reliability.minimum_positive_blocks
            )
        ) if gain_matrix.size else 0
        concordance = concordant / len(sources) if sources else 0.0
        raw_correlations = _pairwise_correlations(local_rates)
        gain_correlations = _pairwise_correlations(gain_matrix)
        criteria = {
            "founder_acquisition_at_least_0_80": acquisition_rate >= 0.80,
            "aggregate_risk_gain_at_least_0_05": aggregate["mean"] is not None
            and float(aggregate["mean"]) >= spec.reliability.minimum_risk_gain,
            "all_block_lower_bounds_above_zero": all(
                value["lower"] is not None and float(value["lower"]) > 0.0
                for value in block_effects
            ),
            "all_block_pairs_equivalent_within_margin": bool(equivalence)
            and all(value["passed"] for value in equivalence),
            "source_sign_concordance_at_least_0_80": concordance
            >= spec.reliability.minimum_sign_concordance,
        }
        candidates[genome.name] = {
            "genome": genome.to_dict(),
            "aggregate_generation_4_risk_gain": aggregate,
            "block_effects": block_effects,
            "block_equivalence": equivalence,
            "source_sign_concordance": concordance,
            "concordant_sources": concordant,
            "sources": len(sources),
            "raw_absolute_rate_pairwise_pearson": raw_correlations,
            "mean_raw_absolute_rate_pearson": float(np.mean(raw_correlations))
            if raw_correlations
            else None,
            "gain_pairwise_pearson": gain_correlations,
            "icc_2_1_absolute_rates": icc_2_1(local_rates),
            "icc_2_1_risk_gains": icc_2_1(gain_matrix),
            "criteria": criteria,
            "stable_effect": all(criteria.values()),
        }
    stable = [value for value in candidates.values() if value["stable_effect"]]
    strongest = sorted(
        stable,
        key=lambda value: (
            -float(value["aggregate_generation_4_risk_gain"]["mean"]),
            int(value["genome"]["k"]),
            value["genome"]["name"],
        ),
    )
    simplest = sorted(
        stable,
        key=lambda value: (
            int(value["genome"]["k"]),
            -float(value["aggregate_generation_4_risk_gain"]["mean"]),
            value["genome"]["name"],
        ),
    )
    nominees: list[dict[str, Any]] = []
    for group in (strongest, simplest):
        if group and group[0]["genome"]["name"] not in {value["name"] for value in nominees}:
            nominees.append(group[0]["genome"])
    descriptive = sorted(
        candidates.values(),
        key=lambda value: (
            -float(value["aggregate_generation_4_risk_gain"]["mean"] or -1.0),
            int(value["genome"]["k"]),
        ),
    )
    return {
        "format": BRIDGE_ANALYSIS_FORMAT,
        "analysis": "precision-repeatability",
        "record_count": len(records),
        "acquisition_rate": acquisition_rate,
        "old_local_ph_verdict_unchanged": True,
        "pearson_role": "descriptive-only-because-saturation-can-collapse-between-source-variance",
        "candidates": candidates,
        "selection": {
            "stable_candidate_found": bool(stable),
            "nominees": nominees,
            "diagnostic_fallback": [value["genome"] for value in descriptive[:3]],
            "rule": "strongest and smallest stable effect; otherwise descriptive top three",
        },
        "verdict": {"repeatable_local_effect": bool(stable)},
    }


def _entropy(values: list[Any]) -> float:
    if not values:
        return 0.0
    counts = collections.Counter(values)
    total = float(sum(counts.values()))
    return float(-sum((amount / total) * math.log2(amount / total) for amount in counts.values()))


def _mutual_information(left: list[Any], right: list[Any]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    pairs = list(zip(left, right))
    return _entropy(left) + _entropy(right) - _entropy(pairs)


def _conditional_mutual_information(
    left: list[Any], right: list[Any], conditioned: list[Any]
) -> float:
    if not left or len(left) != len(right) or len(left) != len(conditioned):
        return 0.0
    return (
        _entropy(list(zip(left, conditioned)))
        + _entropy(list(zip(right, conditioned)))
        - _entropy(conditioned)
        - _entropy(list(zip(left, right, conditioned)))
    )


def _mark_code(values: list[float]) -> tuple[int, ...]:
    return tuple(1 if value > 1e-9 else -1 if value < -1e-9 else 0 for value in values)


def _crossvalidated_history_accuracy(rows: list[dict[str, Any]]) -> float | None:
    accuracies: list[float] = []
    for training_half, testing_half in (("A", "B"), ("B", "A")):
        training = [value for value in rows if value["half"] == training_half]
        testing = [value for value in rows if value["half"] == testing_half]
        mapping: dict[tuple[int, ...], collections.Counter[str]] = collections.defaultdict(
            collections.Counter
        )
        for record in training:
            mapping[_mark_code(record.get("carrier_values", []))][str(record["history"])] += 1
        if not mapping or not testing:
            continue
        correct = 0
        for record in testing:
            counts = mapping.get(_mark_code(record.get("carrier_values", [])))
            predicted = (
                min(("A", "B"), key=lambda value: (-counts[value], value))
                if counts
                else "A"
            )
            correct += int(predicted == str(record["history"]))
        accuracies.append(correct / len(testing))
    return float(np.mean(accuracies)) if accuracies else None


def carrier_information(
    records: list[dict[str, Any]], condition: str, generation: int, challenge: str
) -> dict[str, Any]:
    rows = [
        value
        for value in records
        if value["condition"] == condition
        and int(value["generation"]) == generation
        and value["challenge"] == challenge
        and "carrier_values" in value
    ]
    histories = [str(value["history"]) for value in rows]
    marks = [_mark_code(value["carrier_values"]) for value in rows]
    descendants = [str(value["form_destination"]) for value in rows]
    starts = [int(value.get("assay_initial_state", -1)) for value in rows]
    loci = [
        _mutual_information(histories, [mark[index] for mark in marks])
        for index in range(len(marks[0]) if marks else 0)
    ]
    pair_synergy: list[float] = []
    for left, right in itertools.combinations(range(len(loci)), 2):
        joint = _mutual_information(
            histories, [(mark[left], mark[right]) for mark in marks]
        )
        pair_synergy.append(joint - loci[left] - loci[right])
    return {
        "records": len(rows),
        "history_mark_mutual_information_bits": _mutual_information(histories, marks),
        "history_mark_conditional_on_assay_start_bits": _conditional_mutual_information(
            histories, marks, starts
        ),
        "mark_descendant_mutual_information_bits": _mutual_information(marks, descendants),
        "crossvalidated_history_decoding_accuracy": _crossvalidated_history_accuracy(rows),
        "per_locus_history_information_bits": loci,
        "maximum_pairwise_synergy_bits": max(pair_synergy) if pair_synergy else None,
        "carrier_code_entropy_bits": _entropy(marks),
    }


def analyze_phase_path(path: Path, spec: PhaseDiagramSpec) -> dict[str, Any]:
    spec.validate()
    counts, records, acquisition_rate = _index_records(read_jsonl_gz(path))
    cell_results: dict[str, Any] = {}
    simultaneous = max(1, (len(spec.cells) - 1) * 5)
    by_name = {value.name: value for value in spec.screening.genomes}
    for cell in spec.cells:
        if cell.condition == "zero":
            continue
        generations: dict[str, Any] = {}
        for generation in (1, 2, 4, 8, 16):
            differences = _source_differences(
                counts, cell.condition, "zero", generation, "forced_break"
            )
            generations[str(generation)] = _interval(
                differences.values(),
                spec.screening.master_seed,
                f"phase.{cell.condition}.g{generation}",
                spec.screening.bootstrap_repetitions,
                spec.screening.interval_level,
                simultaneous,
            )
        genome = by_name[str(cell.genome)]
        eligible_design = cell.intervention == "intact" and cell.noise == "nominal"
        criteria = {
            "generation_4_mean_at_least_0_05": generations["4"]["mean"] is not None
            and float(generations["4"]["mean"]) >= 0.05,
            "generation_4_lower_above_zero": generations["4"]["lower"] is not None
            and float(generations["4"]["lower"]) > 0.0,
            "generation_8_lower_above_zero": generations["8"]["lower"] is not None
            and float(generations["8"]["lower"]) > 0.0,
        }
        cell_results[cell.name] = {
            "design": {
                "axis": cell.axis,
                "level": cell.level,
                "noise": cell.noise,
                "intervention": cell.intervention,
            },
            "genome": genome.to_dict(),
            "risk_gain": generations,
            "information_generation_4": carrier_information(
                records, cell.condition, 4, "forced_break"
            ),
            "information_generation_8": carrier_information(
                records, cell.condition, 8, "forced_break"
            ),
            "nomination_eligible_design": eligible_design,
            "criteria": criteria,
            "screen_passed": eligible_design and all(criteria.values()),
        }
    eligible = [value for value in cell_results.values() if value["screen_passed"]]
    strongest = sorted(
        eligible,
        key=lambda value: (
            -float(value["risk_gain"]["8"]["mean"]),
            int(value["genome"]["k"]),
            value["genome"]["name"],
        ),
    )
    simplest = sorted(
        eligible,
        key=lambda value: (
            int(value["genome"]["k"]),
            -float(value["risk_gain"]["8"]["mean"]),
            value["genome"]["name"],
        ),
    )
    nominees: list[dict[str, Any]] = []
    for group in (strongest, simplest):
        if group and group[0]["genome"]["name"] not in {value["name"] for value in nominees}:
            nominees.append(group[0]["genome"])
    diagnostic = sorted(
        (value for value in cell_results.values() if value["nomination_eligible_design"]),
        key=lambda value: (
            -float(value["risk_gain"]["8"]["mean"] or -1.0),
            int(value["genome"]["k"]),
        ),
    )
    if not nominees:
        nominees = [value["genome"] for value in diagnostic[: spec.maximum_nominees]]
    boundaries: dict[str, Any] = {}
    for axis in sorted({value.axis for value in spec.cells if value.axis != "control"}):
        values = [
            {
                "level": result["design"]["level"],
                "generation_4_mean": result["risk_gain"]["4"]["mean"],
                "generation_8_lower": result["risk_gain"]["8"]["lower"],
                "passed": result["screen_passed"],
            }
            for result in cell_results.values()
            if result["design"]["axis"] == axis
        ]
        boundaries[axis] = values
    return {
        "format": BRIDGE_ANALYSIS_FORMAT,
        "analysis": "causal-phase-diagram",
        "record_count": len(records),
        "acquisition_rate": acquisition_rate,
        "cells": cell_results,
        "phase_boundaries": boundaries,
        "selection": {
            "screen_passing_candidate_found": bool(eligible),
            "nominees": nominees[: spec.maximum_nominees],
            "mode": "fresh-screen-pass" if eligible else "diagnostic-fallback",
            "rule": "strongest and smallest fresh passing nominal intact cell; otherwise top descriptive cells",
        },
    }


def _overall_rate(
    counts: dict[CellKey, list[float]],
    condition: str,
    generation: int,
    challenge: str,
    field: str,
) -> float | None:
    matched = [
        value
        for key, value in counts.items()
        if key[0] == condition
        and key[1] == generation
        and key[2] == challenge
        and key[5] == field
    ]
    denominator = sum(value[1] for value in matched)
    return sum(value[0] for value in matched) / denominator if denominator else None


def analyze_causal_path(path: Path, spec: LocalStudySpec) -> dict[str, Any]:
    spec.validate()
    counts, records, acquisition_rate = _index_records(read_jsonl_gz(path))
    nominees: dict[str, Any] = {}
    simultaneous = max(1, len(spec.genomes) * 24)
    for genome in spec.genomes:
        prefix = genome.name

        def risk(condition: str, generation: int, challenge: str = "forced_break", field: str = "correct_hold8") -> dict[str, Any]:
            values = _source_differences(
                counts, condition, "zero", generation, challenge, field
            )
            return _interval(
                values.values(),
                spec.master_seed,
                f"causal.{condition}.g{generation}.{challenge}.{field}",
                spec.bootstrap_repetitions,
                spec.interval_level,
                simultaneous,
            )

        intact = f"{prefix}.intact"
        primary = risk(intact, 4)
        persistence8 = risk(intact, 8)
        persistence16 = risk(intact, 16)
        strong8 = risk(f"{prefix}.strong", 8)
        controls: dict[str, Any] = {}
        control_suffixes = (
            "founder-write-off",
            "renewal-off",
            "reader-off",
            "shuffle",
        ) + (("random-mask",) if genome.k < spec.genes else ())
        for suffix in control_suffixes:
            control = f"{prefix}.{suffix}"
            differences = _source_differences(
                counts, intact, control, 4, "forced_break"
            )
            controls[suffix] = _interval(
                differences.values(),
                spec.master_seed,
                f"causal.{prefix}.control.{suffix}",
                spec.bootstrap_repetitions,
                spec.interval_level,
                simultaneous,
            )
        controls["zero"] = primary
        reverse_values = _source_differences(
            counts,
            f"{prefix}.reverse-g2",
            intact,
            4,
            "forced_break",
            "wrong_hold8",
        )
        reversal = _interval(
            reverse_values.values(),
            spec.master_seed,
            f"causal.{prefix}.reversal",
            spec.bootstrap_repetitions,
            spec.interval_level,
            simultaneous,
        )
        intact_rate = _overall_rate(counts, intact, 4, "forced_break", "correct_hold8")
        zero_rate = _overall_rate(counts, "zero", 4, "forced_break", "correct_hold8")
        erase_rate = _overall_rate(
            counts, f"{prefix}.erase-g2", 4, "forced_break", "correct_hold8"
        )
        rescue_rate = _overall_rate(
            counts,
            f"{prefix}.erase-g2-rescue-g3",
            4,
            "forced_break",
            "correct_hold8",
        )
        ablation_reduction = None
        rescue_fraction = None
        if None not in (intact_rate, zero_rate, erase_rate) and float(intact_rate) > float(zero_rate):
            ablation_reduction = (float(intact_rate) - float(erase_rate)) / (
                float(intact_rate) - float(zero_rate)
            )
        if None not in (intact_rate, erase_rate, rescue_rate) and float(intact_rate) > float(erase_rate):
            rescue_fraction = (float(rescue_rate) - float(erase_rate)) / (
                float(intact_rate) - float(erase_rate)
            )
        locus_importance: list[dict[str, Any]] = []
        for locus in range(spec.genes):
            condition = f"{prefix}.ablate-locus-{locus}-g2"
            differences = _source_differences(
                counts, intact, condition, 4, "forced_break"
            )
            locus_importance.append(
                {
                    "locus": locus,
                    **_interval(
                        differences.values(),
                        spec.master_seed,
                        f"causal.{prefix}.locus.{locus}",
                        spec.bootstrap_repetitions,
                        spec.interval_level,
                        simultaneous,
                    ),
                }
            )
        criteria = {
            "founder_acquisition_at_least_0_80": acquisition_rate >= 0.80,
            "generation_4_risk_at_least_0_05": primary["mean"] is not None
            and float(primary["mean"]) >= 0.05,
            "generation_4_lower_above_zero": primary["lower"] is not None
            and float(primary["lower"]) > 0.0,
            "generation_8_lower_above_zero": persistence8["lower"] is not None
            and float(persistence8["lower"]) > 0.0,
            "generation_16_lower_above_zero": persistence16["lower"] is not None
            and float(persistence16["lower"]) > 0.0,
            "beats_applicable_controls": bool(controls)
            and all(value["lower"] is not None and float(value["lower"]) > 0.0 for value in controls.values()),
            "sign_reversal_reverses_prediction": reversal["lower"] is not None
            and float(reversal["lower"]) > 0.0,
            "erasure_removes_at_least_0_70": ablation_reduction is not None
            and ablation_reduction >= 0.70,
            "rescue_restores_at_least_0_70": rescue_fraction is not None
            and rescue_fraction >= 0.70,
        }
        causal = all(criteria.values())
        robust_criteria = {
            "causal_local_ph_passed": causal,
            "capacity_at_most_5": genome.k <= 5,
            "strong_noise_generation_8_lower_above_zero": strong8["lower"] is not None
            and float(strong8["lower"]) > 0.0,
        }
        nominees[prefix] = {
            "genome": genome.to_dict(),
            "primary_generation_4": primary,
            "persistence_generation_8": persistence8,
            "persistence_generation_16": persistence16,
            "strong_noise_generation_8": strong8,
            "controls": controls,
            "random_mask_control_applicable": genome.k < spec.genes,
            "sign_reversal": reversal,
            "erasure_reduction": ablation_reduction,
            "rescue_fraction": rescue_fraction,
            "locus_ablation_importance": locus_importance,
            "effective_causal_loci": sum(
                value["lower"] is not None and float(value["lower"]) > 0.0
                for value in locus_importance
            ),
            "information_generation_4": carrier_information(
                records, intact, 4, "forced_break"
            ),
            "information_generation_8": carrier_information(
                records, intact, 8, "forced_break"
            ),
            "criteria": criteria,
            "causal_local_ph_passed": causal,
            "compressed_robust_criteria": robust_criteria,
            "compressed_robust_ph_passed": all(robust_criteria.values()),
        }
    return {
        "format": BRIDGE_ANALYSIS_FORMAT,
        "analysis": "fresh-causal-confirmation",
        "record_count": len(records),
        "acquisition_rate": acquisition_rate,
        "carrier_target_access": False,
        "expression_reset_verified": all(bool(value["expression_reset"]) for value in records),
        "nominees": nominees,
        "verdict": {
            "causal_local_ph": any(value["causal_local_ph_passed"] for value in nominees.values()),
            "compressed_robust_ph": any(
                value["compressed_robust_ph_passed"] for value in nominees.values()
            ),
        },
        "legacy_pearson_gate_role": "not-used-in-this-prospective-causal-verdict",
        "claim_boundary": "constructive Wagner mechanism evidence, not evidence of natural historical origin",
    }


def render_bridge_stage_report(analysis: dict[str, Any]) -> str:
    kind = analysis["analysis"]
    lines = ["# Wagner–PH bridge stage", "", f"- Analysis: `{kind}`"]
    if kind == "precision-repeatability":
        lines.extend(
            (
                f"- Repeatable local effect: **{'PASS' if analysis['verdict']['repeatable_local_effect'] else 'fail'}**",
                f"- Stable candidates: {len(analysis['selection']['nominees'])}",
                "- Pearson is retained descriptively; it is not the prospective gate.",
            )
        )
    elif kind == "causal-phase-diagram":
        lines.extend(
            (
                f"- Fresh screen found a passing cell: `{analysis['selection']['screen_passing_candidate_found']}`",
                f"- Selection mode: `{analysis['selection']['mode']}`",
                f"- Nominees: {[value['name'] for value in analysis['selection']['nominees']]}",
            )
        )
    else:
        lines.extend(
            (
                f"- Causal local PH: **{'PASS' if analysis['verdict']['causal_local_ph'] else 'fail'}**",
                f"- Compressed robust PH: **{'PASS' if analysis['verdict']['compressed_robust_ph'] else 'fail'}**",
                "- The historical Pearson verdict remains unchanged and is not reused here.",
            )
        )
    lines.extend(("", f"- Analysis digest: `{canonical_digest(analysis)}`", ""))
    return "\n".join(lines)
