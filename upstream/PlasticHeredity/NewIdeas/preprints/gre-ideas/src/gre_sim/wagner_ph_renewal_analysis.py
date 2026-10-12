"""Renewal-frontier and held-out evolvability analyses."""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import read_jsonl_gz
from .rng import rng_for
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_renewal_config import (
    RENEWAL_AUDIT_FORMAT,
    RENEWAL_TREATMENTS,
    MutationNeighborhoodSpec,
    RenewalEvolutionSpec,
    RenewalFrontierSpec,
)


def _source_rates(
    records: Iterable[dict[str, Any]],
    condition: str,
    generation: int,
    challenge: str,
    field: str,
) -> dict[str, float]:
    counts: dict[str, list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    for record in records:
        if (
            str(record["condition"]) == condition
            and int(record["generation"]) == generation
            and str(record["challenge"]) == challenge
        ):
            counts[str(record["source_id"])][0] += float(record[field])
            counts[str(record["source_id"])][1] += 1.0
    return {
        source: value[0] / value[1]
        for source, value in counts.items()
        if value[1]
    }


def _paired_values(left: dict[str, float], right: dict[str, float]) -> list[float]:
    return [left[key] - right[key] for key in sorted(set(left) & set(right))]


def analyze_renewal_frontier_path(
    path: Path, spec: RenewalFrontierSpec
) -> dict[str, Any]:
    """Locate the gentlest environment where descendant rewriting is necessary."""

    spec.validate()
    records = list(read_jsonl_gz(path))
    zero = {
        (generation, challenge): _source_rates(
            records, "zero", generation, challenge, "correct_hold8"
        )
        for generation in spec.study.checkpoint_generations
        for challenge in spec.study.challenges
    }
    cells: dict[str, Any] = {}
    simultaneous = len(spec.capacities) * len(spec.environment_order)
    for k in spec.capacities:
        for environment in spec.environment_order:
            prefix = f"k{k}.{environment}"
            intact_name = f"{prefix}.intact"
            off_name = f"{prefix}.renewal-off"
            checkpoints: dict[str, Any] = {}
            for generation in spec.study.checkpoint_generations:
                events: dict[str, Any] = {}
                for challenge in spec.study.challenges:
                    intact = _source_rates(
                        records, intact_name, generation, challenge, "correct_hold8"
                    )
                    gain = _paired_values(intact, zero[(generation, challenge)])
                    events[challenge] = _interval(
                        gain,
                        spec.study.master_seed,
                        f"renewal-frontier.{prefix}.g{generation}.{challenge}",
                        spec.study.bootstrap_repetitions,
                        spec.study.interval_level,
                        simultaneous,
                    )
                checkpoints[str(generation)] = events
            intact_g8 = _source_rates(
                records, intact_name, 8, "forced_break", "correct_hold8"
            )
            renewal_off_g8 = _source_rates(
                records, off_name, 8, "forced_break", "correct_hold8"
            )
            renewal_contrast = _interval(
                _paired_values(intact_g8, renewal_off_g8),
                spec.study.master_seed,
                f"renewal-frontier.{prefix}.renewal-contrast",
                spec.study.bootstrap_repetitions,
                spec.study.interval_level,
                simultaneous,
            )
            criteria = {
                "generation_8_gain_at_least_0_15": checkpoints["8"]["forced_break"]["mean"]
                is not None
                and float(checkpoints["8"]["forced_break"]["mean"])
                >= spec.minimum_generation_8_gain,
                "generation_8_gain_lower_above_zero": checkpoints["8"]["forced_break"]["lower"]
                is not None
                and float(checkpoints["8"]["forced_break"]["lower"]) > 0.0,
                "generation_12_gain_lower_above_zero": checkpoints["12"]["forced_break"]["lower"]
                is not None
                and float(checkpoints["12"]["forced_break"]["lower"]) > 0.0,
                "generation_16_gain_lower_above_zero": checkpoints["16"]["forced_break"]["lower"]
                is not None
                and float(checkpoints["16"]["forced_break"]["lower"]) > 0.0,
                "renewal_contrast_at_least_0_10": renewal_contrast["mean"] is not None
                and float(renewal_contrast["mean"])
                >= spec.minimum_renewal_contrast,
                "renewal_contrast_lower_above_zero": renewal_contrast["lower"] is not None
                and float(renewal_contrast["lower"]) > 0.0,
            }
            cells[prefix] = {
                "capacity": k,
                "environment": environment,
                "genome": spec.study.genome(f"renewal-k{k}").to_dict(),
                "checkpoints": checkpoints,
                "generation_8_renewal_contrast": renewal_contrast,
                "criteria": criteria,
                "qualified": all(criteria.values()),
            }

    selected: dict[str, Any] | None = None
    mode = "qualified-frontier"
    for environment in spec.environment_order:
        candidates = [
            value
            for value in cells.values()
            if value["environment"] == environment and value["qualified"]
        ]
        if candidates:
            selected = min(candidates, key=lambda value: int(value["capacity"]))
            break
    if selected is None:
        mode = "mixed-moderate-diagnostic-fallback"
        candidates = [
            value
            for value in cells.values()
            if value["environment"] == spec.fallback_environment
        ]
        selected = max(
            candidates,
            key=lambda value: (
                float(value["generation_8_renewal_contrast"]["mean"] or -1.0),
                float(value["checkpoints"]["8"]["forced_break"]["mean"] or -1.0),
                -int(value["capacity"]),
            ),
        )
    environment_index = spec.environment_order.index(str(selected["environment"]))
    next_environment = spec.environment_order[
        min(environment_index + 1, len(spec.environment_order) - 1)
    ]
    acquisition = {
        (
            str(record["source_id"]),
            str(record["history"]),
            int(record["future_index"]),
        ): bool(record["acquired"])
        for record in records
    }
    selection = {
        "mode": mode,
        "primary_frontier_passed": mode == "qualified-frontier",
        "selected_environment": selected["environment"],
        "next_harsher_environment": next_environment,
        "selected_capacity": int(selected["capacity"]),
        "selected_genome": selected["genome"],
        "selected_cell": f"k{selected['capacity']}.{selected['environment']}",
        "rule": (
            "gentlest environment with a qualifying cell, then smallest capacity; "
            "otherwise the strongest mixed-moderate diagnostic cell"
        ),
    }
    return {
        "format": "gre-wagner-ph-renewal-frontier-analysis-v1",
        "record_count": len(records),
        "acquisition_rate": float(np.mean(tuple(acquisition.values())))
        if acquisition
        else 0.0,
        "environment_order": list(spec.environment_order),
        "cells": cells,
        "selection": selection,
        "verdict": {"renewal_frontier_found": mode == "qualified-frontier"},
        "claim_boundary": (
            "A passing cell identifies an engineered renewal-dependent regime in fresh "
            "Wagner simulations; it does not establish that such machinery occurs in nature."
        ),
    }


def render_frontier_report(analysis: dict[str, Any]) -> str:
    selection = analysis["selection"]
    return "\n".join(
        (
            "# Wagner renewal frontier",
            "",
            f"- Registered frontier found: **{'PASS' if analysis['verdict']['renewal_frontier_found'] else 'fail'}**",
            f"- Selection mode: `{selection['mode']}`",
            f"- Selected cell: `{selection['selected_cell']}`",
            f"- Next-harsher challenge: `{selection['next_harsher_environment']}`",
            "",
            analysis["claim_boundary"],
            "",
        )
    )


def _audit_cell(
    result: dict[str, Any],
    state: str,
    condition: str,
    generation: int,
    field: str = "risk_gain",
    challenge: str = "forced_break",
) -> float:
    return float(
        result[state]["cells"][condition][str(generation)][challenge][field]
    )


def _cluster_interval(
    population_values: dict[int, list[float]],
    seed: str,
    label: str,
    repetitions: int,
    level: float,
) -> dict[str, Any]:
    """Bootstrap populations, retaining all observations inside each cluster."""

    clusters = sorted(population_values)
    flattened = [
        value for key in clusters for value in population_values[key]
    ]
    if not clusters or not flattened:
        return {
            "mean": None,
            "interval": [None, None],
            "lower": None,
            "upper": None,
            "populations": 0,
            "observations": 0,
        }
    random = rng_for(seed, "renewal-cluster-bootstrap", label)
    draws: list[float] = []
    for _ in range(repetitions):
        sampled = random.integers(0, len(clusters), len(clusters))
        values = [
            value
            for index in sampled
            for value in population_values[clusters[int(index)]]
        ]
        draws.append(float(np.mean(values)))
    tail = (1.0 - level) / 2.0
    return {
        "mean": float(np.mean(flattened)),
        "interval": [float(np.quantile(draws, tail)), float(np.quantile(draws, 1.0 - tail))],
        "lower": float(np.quantile(draws, tail)),
        "upper": float(np.quantile(draws, 1.0 - tail)),
        "populations": len(clusters),
        "observations": len(flattened),
    }


def _paired_treatment(
    results: list[dict[str, Any]], left: str, right: str, field: str
) -> list[float]:
    indexed = {
        (str(value["treatment"]), int(value["population_index"])): value
        for value in results
    }
    values: list[float] = []
    for population in sorted(
        set(key[1] for key in indexed if key[0] == left)
        & set(key[1] for key in indexed if key[0] == right)
    ):
        values.append(
            float(indexed[(left, population)][field])
            - float(indexed[(right, population)][field])
        )
    return values


def _causal_summary(
    values: list[dict[str, Any]], spec: RenewalEvolutionSpec, treatment: str
) -> dict[str, Any]:
    controls: dict[str, list[float]] = {
        "founder-write-off": [],
        "reader-off": [],
        "renewal-off": [],
        "shuffle": [],
    }
    erase: list[float] = []
    rescue: list[float] = []
    reverse: list[float] = []
    for value in values:
        if not value.get("full_causal_panel"):
            continue
        intact_g8 = _audit_cell(value, "selected_heldout", "candidate.intact", 8, "correct_rate")
        for suffix in controls:
            controls[suffix].append(
                intact_g8
                - _audit_cell(
                    value,
                    "selected_heldout",
                    f"candidate.{suffix}",
                    8,
                    "correct_rate",
                )
            )
        intact_g4 = _audit_cell(value, "selected_heldout", "candidate.intact", 4, "correct_rate")
        zero_g4 = _audit_cell(value, "selected_heldout", "zero", 4, "correct_rate")
        erased = _audit_cell(value, "selected_heldout", "candidate.erase-g2", 4, "correct_rate")
        rescued = _audit_cell(
            value, "selected_heldout", "candidate.erase-g2-rescue-g3", 4, "correct_rate"
        )
        if intact_g4 > zero_g4:
            erase.append((intact_g4 - erased) / (intact_g4 - zero_g4))
        if intact_g4 > erased:
            rescue.append((rescued - erased) / (intact_g4 - erased))
        reverse.append(
            _audit_cell(value, "selected_heldout", "candidate.reverse-g2", 4, "wrong_rate")
            - _audit_cell(value, "selected_heldout", "candidate.intact", 4, "wrong_rate")
        )
    return {
        "controls": {
            key: _interval(
                items,
                spec.master_seed,
                f"renewal-audit.{treatment}.causal.{key}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            )
            for key, items in controls.items()
        },
        "erasure_reduction": _interval(
            erase,
            spec.master_seed,
            f"renewal-audit.{treatment}.erase",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "rescue_fraction": _interval(
            rescue,
            spec.master_seed,
            f"renewal-audit.{treatment}.rescue",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "reversal_wrong_form_gain": _interval(
            reverse,
            spec.master_seed,
            f"renewal-audit.{treatment}.reverse",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _treatment_gate(
    treatment: str,
    summaries: dict[str, Any],
    contrasts: dict[str, dict[str, Any]],
    causal: dict[str, Any],
    mutation: dict[str, Any],
    minimum_positive_fraction: float,
) -> dict[str, bool]:
    value = summaries[treatment]
    return {
        "founder_improvement_at_least_0_05": value["founder_to_selected_g8"]["mean"]
        is not None
        and float(value["founder_to_selected_g8"]["mean"]) >= 0.05,
        "founder_improvement_lower_above_zero": value["founder_to_selected_g8"]["lower"]
        is not None
        and float(value["founder_to_selected_g8"]["lower"]) > 0.0,
        "beats_memory_by_at_least_0_05_with_positive_lower": contrasts["memory_standard_cost"]["mean"]
        is not None
        and float(contrasts["memory_standard_cost"]["mean"]) >= 0.05
        and float(contrasts["memory_standard_cost"]["lower"] or -1.0) > 0.0,
        "beats_acute_by_at_least_0_05_with_positive_lower": contrasts["acute_standard_cost"]["mean"]
        is not None
        and float(contrasts["acute_standard_cost"]["mean"]) >= 0.05
        and float(contrasts["acute_standard_cost"]["lower"] or -1.0) > 0.0,
        "beats_neutral_by_at_least_0_05_with_positive_lower": contrasts["neutral_drift"]["mean"]
        is not None
        and float(contrasts["neutral_drift"]["mean"]) >= 0.05
        and float(contrasts["neutral_drift"]["lower"] or -1.0) > 0.0,
        "generation_12_lower_above_zero": value["selected_g12"]["lower"] is not None
        and float(value["selected_g12"]["lower"]) > 0.0,
        "generation_16_lower_above_zero": value["selected_g16"]["lower"] is not None
        and float(value["selected_g16"]["lower"]) > 0.0,
        "renewal_contrast_at_least_0_10_with_positive_lower": value["renewal_contrast_g8"]["mean"]
        is not None
        and float(value["renewal_contrast_g8"]["mean"]) >= 0.10
        and float(value["renewal_contrast_g8"]["lower"] or -1.0) > 0.0,
        "next_harsher_generation_8_lower_above_zero": value["next_harsher_g8"]["lower"]
        is not None
        and float(value["next_harsher_g8"]["lower"]) > 0.0,
        "causal_write_read_renew_shuffle_lower_above_zero": all(
            item["lower"] is not None and float(item["lower"]) > 0.0
            for item in causal["controls"].values()
        ),
        "erasure_removes_at_least_0_70": causal["erasure_reduction"]["mean"]
        is not None
        and float(causal["erasure_reduction"]["mean"]) >= 0.70,
        "rescue_restores_at_least_0_70": causal["rescue_fraction"]["mean"]
        is not None
        and float(causal["rescue_fraction"]["mean"]) >= 0.70,
        "reversal_lower_above_zero": causal["reversal_wrong_form_gain"]["lower"]
        is not None
        and float(causal["reversal_wrong_form_gain"]["lower"]) > 0.0,
        "positive_populations_at_least_0_80": float(value["positive_population_fraction"])
        >= minimum_positive_fraction,
        "clustered_parent_offspring_slope_lower_above_zero": mutation["slope"]["lower"]
        is not None
        and float(mutation["slope"]["lower"]) > 0.0,
        "offspring_retention_lower_at_least_0_70": mutation["retention"]["lower"]
        is not None
        and float(mutation["retention"]["lower"]) >= 0.70,
    }


def analyze_renewal_audit(
    population_results: list[dict[str, Any]],
    mutation_rows: list[dict[str, Any]],
    evolution_spec: RenewalEvolutionSpec,
    audit_spec: MutationNeighborhoodSpec,
) -> dict[str, Any]:
    """Analyze populations as the unit and mutations with cluster resampling."""

    grouped = {
        treatment: sorted(
            [value for value in population_results if value["treatment"] == treatment],
            key=lambda value: int(value["population_index"]),
        )
        for treatment in RENEWAL_TREATMENTS
    }
    summaries: dict[str, Any] = {}
    for treatment, values in grouped.items():
        selected_g8 = [float(value["selected_g8"]) for value in values]
        founder_g8 = [float(value["founder_g8"]) for value in values]
        improvements = [a - b for a, b in zip(selected_g8, founder_g8)]
        renewal = [float(value["renewal_contrast_g8"]) for value in values]
        summaries[treatment] = {
            "selected_g8": _interval(
                selected_g8,
                evolution_spec.master_seed,
                f"renewal-audit.{treatment}.selected-g8",
                evolution_spec.bootstrap_repetitions,
                evolution_spec.interval_level,
            ),
            "founder_to_selected_g8": _interval(
                improvements,
                evolution_spec.master_seed,
                f"renewal-audit.{treatment}.improvement",
                evolution_spec.bootstrap_repetitions,
                evolution_spec.interval_level,
            ),
            "selected_g12": _interval(
                (float(value["selected_g12"]) for value in values),
                evolution_spec.master_seed,
                f"renewal-audit.{treatment}.selected-g12",
                evolution_spec.bootstrap_repetitions,
                evolution_spec.interval_level,
            ),
            "selected_g16": _interval(
                (float(value["selected_g16"]) for value in values),
                evolution_spec.master_seed,
                f"renewal-audit.{treatment}.selected-g16",
                evolution_spec.bootstrap_repetitions,
                evolution_spec.interval_level,
            ),
            "renewal_contrast_g8": _interval(
                renewal,
                evolution_spec.master_seed,
                f"renewal-audit.{treatment}.renewal-g8",
                evolution_spec.bootstrap_repetitions,
                evolution_spec.interval_level,
            ),
            "next_harsher_g8": _interval(
                (float(value["harsher_g8"]) for value in values),
                evolution_spec.master_seed,
                f"renewal-audit.{treatment}.harsher-g8",
                evolution_spec.bootstrap_repetitions,
                evolution_spec.interval_level,
            ),
            "positive_population_fraction": float(
                np.mean(
                    [a > 0.0 and b > 0.0 for a, b in zip(selected_g8, renewal)]
                )
            )
            if values
            else 0.0,
            "median_selected_capacity": float(
                np.median([int(value["selected_capacity"]) for value in values])
            )
            if values
            else None,
        }

    mutation_summaries: dict[str, Any] = {}
    for treatment in RENEWAL_TREATMENTS[:3]:
        treatment_rows = [row for row in mutation_rows if row["treatment"] == treatment]
        slope_clusters: dict[int, list[float]] = {}
        retention_clusters: dict[int, list[float]] = collections.defaultdict(list)
        for population in sorted({int(row["population_index"]) for row in treatment_rows}):
            rows = [row for row in treatment_rows if int(row["population_index"]) == population]
            parents: dict[int, float] = {}
            offspring: dict[int, list[float]] = collections.defaultdict(list)
            for row in rows:
                parent_index = int(row["parent_rank"])
                parents[parent_index] = float(row["parent_score"])
                offspring[parent_index].append(float(row["offspring_score"]))
                threshold = audit_spec.retention_fraction * max(float(row["parent_score"]), 0.0)
                retention_clusters[population].append(
                    float(
                        float(row["offspring_score"]) >= threshold
                        and float(row["offspring_renewal_contrast"]) > 0.0
                    )
                )
            x = np.asarray([parents[key] for key in sorted(parents)], dtype=float)
            y = np.asarray(
                [float(np.mean(offspring[key])) for key in sorted(parents)], dtype=float
            )
            if len(x) >= 2 and float(np.var(x)) > 0.0:
                slope = float(np.cov(x, y, ddof=0)[0, 1] / np.var(x))
                slope_clusters[population] = [slope]
        mutation_summaries[treatment] = {
            "slope": _cluster_interval(
                slope_clusters,
                audit_spec.master_seed,
                f"mutation.{treatment}.slope",
                audit_spec.bootstrap_repetitions,
                audit_spec.interval_level,
            ),
            "retention": _cluster_interval(
                dict(retention_clusters),
                audit_spec.master_seed,
                f"mutation.{treatment}.retention",
                audit_spec.bootstrap_repetitions,
                audit_spec.interval_level,
            ),
        }

    treatment_analyses: dict[str, Any] = {}
    for treatment in RENEWAL_TREATMENTS[:2]:
        contrasts = {
            control: _interval(
                _paired_treatment(population_results, treatment, control, "selected_g8"),
                evolution_spec.master_seed,
                f"renewal-audit.{treatment}.versus.{control}",
                evolution_spec.bootstrap_repetitions,
                evolution_spec.interval_level,
                3,
            )
            for control in (
                "memory_standard_cost",
                "acute_standard_cost",
                "neutral_drift",
            )
        }
        causal = _causal_summary(grouped[treatment], evolution_spec, treatment)
        criteria = _treatment_gate(
            treatment,
            summaries,
            contrasts,
            causal,
            mutation_summaries[treatment],
            audit_spec.minimum_positive_population_fraction,
        )
        treatment_analyses[treatment] = {
            "contrasts": contrasts,
            "causal": causal,
            "mutation": mutation_summaries[treatment],
            "criteria": criteria,
            "passed": all(criteria.values()),
        }

    standard_passed = treatment_analyses["renewal_standard_cost"]["passed"]
    high_passed = treatment_analyses["renewal_high_cost"]["passed"]
    high_capacity = summaries["renewal_high_cost"]["median_selected_capacity"]
    return {
        "format": RENEWAL_AUDIT_FORMAT,
        "population_count": len(population_results),
        "mutation_rows": len(mutation_rows),
        "population_is_inferential_unit": True,
        "raw_pearson_is_primary": False,
        "common_tasks_and_streams_verified": all(
            bool(value["common_streams_verified"]) for value in population_results
        ),
        "treatments": summaries,
        "renewal_treatments": treatment_analyses,
        "k5_feasibility_mutation": mutation_summaries["renewal_k5_feasibility"],
        "verdict": {
            "renewal_evolvability_nominated": bool(standard_passed),
            "compact_unconstrained_renewal_nominated": bool(
                high_passed and high_capacity is not None and high_capacity <= 5.0
            ),
            "hard_k5_feasibility_is_engineering_only": True,
        },
        "claim_boundary": (
            "A nomination is an exploratory in-silico result about evolvability under the "
            "registered objective, not evidence of a natural biological origin."
        ),
    }


def render_audit_report(analysis: dict[str, Any]) -> str:
    verdict = analysis["verdict"]
    standard = analysis["renewal_treatments"]["renewal_standard_cost"]
    failed = [key for key, value in standard["criteria"].items() if not value]
    return "\n".join(
        (
            "# Wagner renewal and evolvability held-out audit",
            "",
            f"- Renewal evolvability nomination: **{'PASS' if verdict['renewal_evolvability_nominated'] else 'fail'}**",
            f"- Compact unconstrained nomination: **{'PASS' if verdict['compact_unconstrained_renewal_nominated'] else 'fail'}**",
            f"- Common tasks and streams verified: `{analysis['common_tasks_and_streams_verified']}`",
            f"- Failed standard-cost criteria: {failed or 'none'}",
            "",
            analysis["claim_boundary"],
            "",
        )
    )
