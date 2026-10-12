"""Streaming rulebook-level analysis for Wagner induction rescue."""

from __future__ import annotations

import collections
from typing import Any, Iterable

import numpy as np

from .rng import rng_for
from .wagner_rescue_config import (
    WAGNER_RESCUE_ANALYSIS_FORMAT,
    WagnerRescueSpec,
)


MetricKey = tuple[str, str, str]
HalfKey = tuple[str, str, str, str]


def _bootstrap(
    values: list[float],
    spec: WagnerRescueSpec,
    label: str,
    simultaneous: bool = False,
) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {
            "mean": None,
            "interval": [None, None],
            "lower": None,
            "sources": 0,
            "positive_sources": 0,
        }
    rng = rng_for(spec.master_seed, "wagner-rescue-bootstrap", label)
    indices = rng.integers(
        0, array.size, size=(spec.bootstrap_repetitions, array.size)
    )
    means = np.mean(array[indices], axis=1)
    ordinary_tail = (1.0 - spec.interval_level) / 2.0
    lower_tail = (
        (1.0 - spec.interval_level) / spec.simultaneous_tests
        if simultaneous
        else ordinary_tail
    )
    return {
        "mean": float(np.mean(array)),
        "interval": [
            float(np.quantile(means, ordinary_tail)),
            float(np.quantile(means, 1.0 - ordinary_tail)),
        ],
        "lower": float(np.quantile(means, lower_tail)),
        "sources": int(array.size),
        "positive_sources": int(np.sum(array > 0.0)),
    }


def _source_rate(
    counts: dict[MetricKey, list[float]],
    condition: str,
    source: str,
    history: str,
    field: str,
) -> float | None:
    total = counts.get((condition, source, f"{history}.{field}"), [0.0, 0.0])
    return float(total[0] / total[1]) if total[1] else None


def _history_values(
    counts: dict[MetricKey, list[float]],
    condition: str,
    sources: list[str],
    history: str,
    field: str,
) -> list[float]:
    output = []
    for source in sources:
        value = _source_rate(counts, condition, source, history, field)
        if value is not None:
            output.append(value)
    return output


def _reliability(
    halves: dict[HalfKey, list[float]], condition: str, sources: list[str]
) -> float | None:
    paired: list[tuple[float, float]] = []
    for source in sources:
        values = []
        for half in ("A", "B"):
            numerator = 0.0
            denominator = 0.0
            for history in ("A", "B"):
                amount = halves.get(
                    (condition, source, history, half), [0.0, 0.0]
                )
                numerator += amount[0]
                denominator += amount[1]
            if denominator == 0:
                break
            values.append(numerator / denominator)
        if len(values) == 2:
            paired.append((values[0], values[1]))
    if len(paired) < 3:
        return None
    left, right = np.asarray(paired, dtype=float).T
    if np.std(left) == 0.0 or np.std(right) == 0.0:
        return 1.0 if np.array_equal(left, right) else 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _mean_metric(cell: dict[str, Any], history: str, field: str) -> float | None:
    return cell["histories"][history][field]["mean"]


def _criteria(cell: dict[str, Any]) -> tuple[dict[str, bool], dict[str, bool]]:
    acquisition = [
        _mean_metric(cell, history, "exact_acquisition") for history in ("A", "B")
    ]
    acquisition_lower = [
        cell["histories"][history]["exact_acquisition"]["lower"]
        for history in ("A", "B")
    ]
    hold = [_mean_metric(cell, history, "correct_hold8") for history in ("A", "B")]
    crossover = cell["metrics"]["correct_minus_wrong"]
    cue_gain = cell["metrics"]["cue_gain_over_no_cue"]
    screen = {
        "both_histories_exact_acquisition_at_least_0_80": all(
            value is not None and value >= 0.80 for value in acquisition
        ),
        "history_acquisition_imbalance_at_most_0_10": all(
            value is not None for value in acquisition
        )
        and abs(float(acquisition[0]) - float(acquisition[1])) <= 0.10,
        "both_histories_correct_hold8_at_least_0_20": all(
            value is not None and value >= 0.20 for value in hold
        ),
        "correct_minus_wrong_at_least_0_10": crossover["mean"] is not None
        and float(crossover["mean"]) >= 0.10,
    }
    replication = {
        **screen,
        "both_acquisition_lower_bounds_at_least_0_70": all(
            value is not None and value >= 0.70 for value in acquisition_lower
        ),
        "cue_gain_at_least_0_10": cue_gain["mean"] is not None
        and float(cue_gain["mean"]) >= 0.10,
        "cue_gain_simultaneous_lower_above_zero": cue_gain["lower"] is not None
        and float(cue_gain["lower"]) > 0.0,
        "crossover_simultaneous_lower_above_zero": crossover["lower"] is not None
        and float(crossover["lower"]) > 0.0,
        "split_half_reliability_at_least_0_80": cell[
            "split_half_reliability"
        ]
        is not None
        and float(cell["split_half_reliability"]) >= 0.80,
        "retention_at_least_0_70_of_injection_ceiling": cell[
            "injection_ceiling_fraction"
        ]
        is not None
        and float(cell["injection_ceiling_fraction"]) >= 0.70,
    }
    return screen, replication


def analyze_rescue_records(
    records: Iterable[dict[str, Any]], spec: WagnerRescueSpec
) -> dict[str, Any]:
    """Aggregate induction and released-history outcomes at rulebook level."""

    spec.validate()
    fields = (
        "acquired",
        "basin_acquired",
        "correct_hold8",
        "wrong_hold8",
        "returned",
        "training_point",
        "training_nonconvergent",
    )
    counts: dict[MetricKey, list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    halves: dict[HalfKey, list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    sources_by_condition: dict[str, set[str]] = collections.defaultdict(set)
    future_ids: set[str] = set()
    record_count = 0
    for record in records:
        record_count += 1
        future_id = str(record["future_id"])
        if future_id in future_ids:
            raise ValueError(f"duplicate Wagner rescue future id: {future_id}")
        future_ids.add(future_id)
        condition = str(record["condition"])
        source = str(record["source_id"])
        history = str(record["history"])
        sources_by_condition[condition].add(source)
        values = {
            "acquired": float(record["acquired"]),
            "basin_acquired": float(record["basin_acquired"]),
            "correct_hold8": float(record["correct_hold8"]),
            "wrong_hold8": float(record["wrong_hold8"]),
            "returned": float(record["returned"]),
            "training_point": float(record["training_status"] == "point"),
            "training_nonconvergent": float(
                record["training_status"] == "nonconvergent"
            ),
        }
        for field in fields:
            amount = counts[(condition, source, f"{history}.{field}")]
            amount[0] += values[field]
            amount[1] += 1.0
        half = halves[(condition, source, history, str(record["half"]))]
        half[0] += values["correct_hold8"]
        half[1] += 1.0

    no_cue = {
        condition.model: condition.name
        for condition in spec.conditions
        if condition.role == "no_cue"
    }
    injection = {
        condition.model: condition.name
        for condition in spec.conditions
        if condition.role == "target_injection"
    }
    cells: dict[str, Any] = {}
    field_names = {
        "acquired": "exact_acquisition",
        "basin_acquired": "target_basin_acquisition",
        "correct_hold8": "correct_hold8",
        "wrong_hold8": "wrong_hold8",
        "returned": "returned",
        "training_point": "training_point_rate",
        "training_nonconvergent": "training_nonconvergent_rate",
    }
    for condition in spec.conditions:
        model = spec.model(condition.model)
        sources = sorted(sources_by_condition.get(condition.name, set()))
        histories: dict[str, Any] = {}
        for history in ("A", "B"):
            histories[history] = {
                public: _bootstrap(
                    _history_values(
                        counts, condition.name, sources, history, archived
                    ),
                    spec,
                    f"{condition.name}.{history}.{archived}",
                    simultaneous=archived == "acquired",
                )
                for archived, public in field_names.items()
            }

        crossover_values: list[float] = []
        cue_gain_values: list[float] = []
        no_cue_name = no_cue.get(condition.model)
        for source in sources:
            correct = []
            wrong = []
            baseline = []
            for history in ("A", "B"):
                correct_value = _source_rate(
                    counts, condition.name, source, history, "correct_hold8"
                )
                wrong_value = _source_rate(
                    counts, condition.name, source, history, "wrong_hold8"
                )
                if correct_value is not None:
                    correct.append(correct_value)
                if wrong_value is not None:
                    wrong.append(wrong_value)
                if no_cue_name is not None:
                    baseline_value = _source_rate(
                        counts, no_cue_name, source, history, "correct_hold8"
                    )
                    if baseline_value is not None:
                        baseline.append(baseline_value)
            if len(correct) == len(wrong) == 2:
                crossover_values.append(float(np.mean(correct) - np.mean(wrong)))
            if len(correct) == len(baseline) == 2:
                cue_gain_values.append(float(np.mean(correct) - np.mean(baseline)))

        injection_name = injection.get(condition.model)
        candidate_hold = np.mean(
            [
                histories[history]["correct_hold8"]["mean"]
                for history in ("A", "B")
                if histories[history]["correct_hold8"]["mean"] is not None
            ]
        )
        injection_hold_values: list[float] = []
        if injection_name is not None:
            for source in sources:
                for history in ("A", "B"):
                    value = _source_rate(
                        counts, injection_name, source, history, "correct_hold8"
                    )
                    if value is not None:
                        injection_hold_values.append(value)
        injection_hold = (
            float(np.mean(injection_hold_values)) if injection_hold_values else None
        )
        ceiling_fraction = (
            float(candidate_hold / injection_hold)
            if injection_hold is not None and injection_hold > 0.0
            else None
        )
        cell = {
            "condition": condition.name,
            "role": condition.role,
            "model": {
                "name": model.name,
                "variant": model.variant,
                "gamma_variance": model.gamma_variance,
            },
            "intervention": {
                "mode": condition.intervention.mode,
                "fraction": condition.intervention.fraction,
                "dwell": condition.intervention.dwell,
                "field_strength": condition.intervention.field_strength,
            },
            "histories": histories,
            "metrics": {
                "correct_minus_wrong": _bootstrap(
                    crossover_values,
                    spec,
                    f"{condition.name}.correct-minus-wrong",
                    simultaneous=True,
                ),
                "cue_gain_over_no_cue": _bootstrap(
                    cue_gain_values,
                    spec,
                    f"{condition.name}.cue-gain-over-no-cue",
                    simultaneous=True,
                ),
            },
            "split_half_reliability": _reliability(
                halves, condition.name, sources
            ),
            "injection_ceiling_hold8": injection_hold,
            "injection_ceiling_fraction": ceiling_fraction,
            "sources": len(sources),
        }
        screen, replication = _criteria(cell)
        cell["screen_criteria"] = screen
        cell["screen_passed"] = condition.role == "candidate" and all(
            screen.values()
        )
        cell["replication_criteria"] = replication
        cell["replication_passed"] = condition.role == "candidate" and all(
            replication.values()
        )
        cells[condition.name] = cell

    return {
        "format": WAGNER_RESCUE_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "exploratory": spec.exploratory,
        "record_count": record_count,
        "unique_future_ids": len(future_ids),
        "cells": cells,
        "thresholds": {
            "exact_acquisition": 0.80,
            "acquisition_balance": 0.10,
            "acquisition_lower": 0.70,
            "correct_hold8": 0.20,
            "correct_minus_wrong": 0.10,
            "cue_gain": 0.10,
            "split_half_reliability": 0.80,
            "injection_ceiling_fraction": 0.70,
            "interval_level": spec.interval_level,
            "simultaneous_tests": spec.simultaneous_tests,
        },
    }
