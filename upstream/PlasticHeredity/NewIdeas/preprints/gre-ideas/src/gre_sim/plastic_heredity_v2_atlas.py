"""Mechanism-atlas summaries and within-rulebook variant nominations."""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import read_json, read_jsonl_gz
from .landscape import normalized_hamming
from .plastic_memory_analysis import (
    _bootstrap,
    _cell,
    _outcome_key,
    _source_metric_values,
)
from .plastic_memory_config import PlasticMemorySpec


ATLAS_ANALYSIS_FORMAT = "gre-plastic-heredity-v2-mechanism-atlas-analysis-v1"


def _effect_inputs(
    path: Path, spec: PlasticMemorySpec
) -> tuple[
    dict[str, dict[str, dict[str, float]]],
    dict[str, dict[str, float]],
]:
    source_rates: dict[tuple[Any, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    outcomes: dict[Any, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    dynamics: dict[str, dict[str, float]] = collections.defaultdict(
        lambda: collections.defaultdict(float)
    )
    for record in read_jsonl_gz(path):
        cell = _cell(record)
        source = str(record["source_id"])
        for field in ("correct_hold8",):
            value = source_rates[(cell, source, field)]
            value[0] += float(record[field])
            value[1] += 1.0
        outcomes[_outcome_key(record)][str(record["form_destination"])] += 1
        model = str(record["model"])
        dynamics[model]["records"] += 1.0
        dynamics[model]["point_cycles"] += float(record["point_cycles"])
        dynamics[model]["cycle_cycles"] += float(record["cycle_cycles"])
        dynamics[model]["nonconvergent_cycles"] += float(record["nonconvergent_cycles"])
        dynamics[model]["returned"] += float(record["returned"])
    effects: dict[str, dict[str, dict[str, float]]] = {}
    for model in spec.models:
        raw = _source_metric_values(
            source_rates,
            outcomes,
            model.name,
            "none",
            "state_transplant",
            "reset_both",
            0,
            "neutral_damage",
        )
        effects[model.name] = {
            source: {
                metric: float(raw[metric][index])
                for metric in ("risk_difference", "crossover", "log_loss_gain")
            }
            for index, source in enumerate(raw["sources"])
        }
    normalized_dynamics = {
        model: {
            key: value / max(1.0, values["records"])
            for key, value in values.items()
            if key != "records"
        }
        for model, values in dynamics.items()
    }
    return effects, normalized_dynamics


def _geometry(registry: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, float]]] = collections.defaultdict(list)
    for source in registry["sources"]:
        genes = int(source["genes"])
        for model, metadata in source["models"].items():
            landscape = metadata["landscape"]
            attractors = landscape["attractors"]
            point_count = sum(len(value) == 1 for value in attractors)
            cycle_count = len(attractors) - point_count
            pair = metadata["pair"]
            breaks = metadata["forced_breaks"]
            break_distance = np.mean(
                [
                    normalized_hamming(
                        int(pair["left_state"] if history == "A" else pair["right_state"]),
                        int(breaks[history]),
                        genes,
                    )
                    for history in ("A", "B")
                ]
            )
            grouped[model].append(
                {
                    "point_attractors": float(point_count),
                    "cycle_attractors": float(cycle_count),
                    "basin_entropy": float(landscape["basin_entropy"]),
                    "mean_transient": float(landscape["mean_transient"]),
                    "pair_distance": normalized_hamming(
                        int(pair["left_state"]), int(pair["right_state"]), genes
                    ),
                    "forced_break_distance": float(break_distance),
                }
            )
    return {
        model: {
            key: float(np.mean([row[key] for row in rows]))
            for key in rows[0]
        }
        for model, rows in grouped.items()
    }


def analyze_atlas_run(directory: Path) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = PlasticMemorySpec.from_dict(registration["protocol"])
    registry = read_json(directory / "rulebooks.json")
    effects, dynamics = _effect_inputs(directory / "futures.jsonl.gz", spec)
    baselines = {
        "boolean": "boolean.sync",
        "wagner": "wagner.sequential.theta-0",
    }
    candidates: dict[str, Any] = {}
    comparisons = max(1, (len(spec.models) - 2) * 3)
    for model in spec.models:
        engine = "boolean" if model.name.startswith("boolean") else "wagner"
        baseline = baselines[engine]
        if model.name == baseline:
            continue
        shared = sorted(set(effects[model.name]) & set(effects[baseline]))
        deltas = {
            metric: [
                effects[model.name][source][metric] - effects[baseline][source][metric]
                for source in shared
            ]
            for metric in ("risk_difference", "crossover", "log_loss_gain")
        }
        estimates = {
            metric: _bootstrap(
                values,
                spec,
                f"plastic-heredity-v2-atlas.{spec.expression_flip_probability}.{model.name}.{metric}",
                comparisons,
            )
            for metric, values in deltas.items()
        }
        criteria = {
            "within_source_risk_gain_at_least_0_02": estimates["risk_difference"]["mean"]
            is not None
            and float(estimates["risk_difference"]["mean"]) >= 0.02,
            "adjusted_risk_lower_above_zero": estimates["risk_difference"]["lower"]
            is not None
            and float(estimates["risk_difference"]["lower"]) > 0.0,
            "crossover_direction_agrees": estimates["crossover"]["mean"] is not None
            and float(estimates["crossover"]["mean"]) > 0.0,
        }
        candidates[model.name] = {
            "engine": engine,
            "candidate": model.name,
            "baseline": baseline,
            "expression_flip_probability": spec.expression_flip_probability,
            "metrics": estimates,
            "paired_sources": len(shared),
            "criteria": criteria,
            "eligible": all(criteria.values()),
        }
    return {
        "format": ATLAS_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "expression_flip_probability": spec.expression_flip_probability,
        "geometry": _geometry(registry),
        "dynamics": dynamics,
        "candidate_contrasts": candidates,
        "compiled_wagner_boolean_role": "pathwise fixture only; not a scientific candidate",
    }


def nominate_atlas_variants(
    analyses: list[dict[str, Any]], maximum: int = 2
) -> tuple[dict[str, object], ...]:
    candidates = [
        value
        for analysis in analyses
        for value in analysis["candidate_contrasts"].values()
        if value["eligible"]
    ]
    candidates.sort(
        key=lambda value: (
            -float(value["metrics"]["risk_difference"]["mean"]),
            -float(value["metrics"]["crossover"]["mean"]),
            str(value["candidate"]),
        )
    )
    return tuple(
        {
            "engine": value["engine"],
            "candidate": value["candidate"],
            "baseline": value["baseline"],
            "expression_flip_probability": value["expression_flip_probability"],
        }
        for value in candidates[:maximum]
    )
