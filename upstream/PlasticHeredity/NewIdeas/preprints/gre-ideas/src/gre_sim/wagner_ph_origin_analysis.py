"""Held-out causal and pedigree analysis for Wagner PH origin v1."""

from __future__ import annotations

import collections
from typing import Any, Iterable

import numpy as np

from .rng import rng_for
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_origin_config import (
    EXPLICIT_TREATMENTS,
    ORIGIN_AUDIT_FORMAT,
    ORIGIN_TREATMENTS,
    OriginAuditSpec,
    OriginEvolutionSpec,
)


def _paired(
    results: list[dict[str, Any]], left: str, right: str, field: str
) -> list[float]:
    indexed = {
        (str(value["treatment"]), int(value["population_index"])): value
        for value in results
    }
    populations = sorted(
        {key[1] for key in indexed if key[0] == left}
        & {key[1] for key in indexed if key[0] == right}
    )
    return [
        float(indexed[(left, index)][field])
        - float(indexed[(right, index)][field])
        for index in populations
    ]


def _cluster_interval(
    clusters: dict[int, list[float]],
    seed: str,
    label: str,
    repetitions: int,
    level: float,
) -> dict[str, Any]:
    keys = sorted(clusters)
    flattened = [value for key in keys for value in clusters[key]]
    if not keys or not flattened:
        return {
            "mean": None,
            "interval": [None, None],
            "lower": None,
            "upper": None,
            "populations": 0,
            "observations": 0,
        }
    random = rng_for(seed, "origin-cluster-bootstrap", label)
    draws: list[float] = []
    for _ in range(repetitions):
        sampled = random.integers(0, len(keys), len(keys))
        values = [
            value for index in sampled for value in clusters[keys[int(index)]]
        ]
        draws.append(float(np.mean(values)))
    tail = (1.0 - level) / 2.0
    return {
        "mean": float(np.mean(flattened)),
        "interval": [
            float(np.quantile(draws, tail)),
            float(np.quantile(draws, 1.0 - tail)),
        ],
        "lower": float(np.quantile(draws, tail)),
        "upper": float(np.quantile(draws, 1.0 - tail)),
        "populations": len(keys),
        "observations": len(flattened),
    }


def _population_slope(rows: list[dict[str, Any]], generation: int) -> float | None:
    chosen = [
        value for value in rows if int(value["pedigree_generation"]) == generation
    ]
    grouped: dict[int, list[float]] = collections.defaultdict(list)
    roots: dict[int, float] = {}
    for value in chosen:
        rank = int(value["root_parent_rank"])
        roots[rank] = float(value["root_score"])
        grouped[rank].append(float(value["descendant_score"]))
    keys = sorted(roots)
    if len(keys) < 2:
        return None
    x = np.asarray([roots[key] for key in keys], dtype=float)
    y = np.asarray([float(np.mean(grouped[key])) for key in keys], dtype=float)
    if float(np.var(x)) <= 0.0:
        return None
    return float(np.cov(x, y, ddof=0)[0, 1] / np.var(x))


def _pedigree_summary(
    rows: list[dict[str, Any]], treatment: str, spec: OriginAuditSpec
) -> dict[str, Any]:
    chosen = [value for value in rows if value["treatment"] == treatment]
    one_step: dict[int, list[float]] = collections.defaultdict(list)
    two_step: dict[int, list[float]] = collections.defaultdict(list)
    slope_one: dict[int, list[float]] = {}
    slope_two: dict[int, list[float]] = {}
    for population in sorted(
        {int(value["population_index"]) for value in chosen}
    ):
        population_rows = [
            value
            for value in chosen
            if int(value["population_index"]) == population
        ]
        for value in population_rows:
            generation = int(value["pedigree_generation"])
            if generation == 1:
                one_step[population].append(float(value["retained_from_immediate"]))
            elif generation == 2:
                two_step[population].append(float(value["retained_from_root"]))
        first = _population_slope(population_rows, 1)
        second = _population_slope(population_rows, 2)
        if first is not None:
            slope_one[population] = [first]
        if second is not None:
            slope_two[population] = [second]
    return {
        "one_step_retention": _cluster_interval(
            dict(one_step),
            spec.master_seed,
            f"origin-pedigree.{treatment}.one-retention",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "two_step_retention": _cluster_interval(
            dict(two_step),
            spec.master_seed,
            f"origin-pedigree.{treatment}.two-retention",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "one_step_slope": _cluster_interval(
            slope_one,
            spec.master_seed,
            f"origin-pedigree.{treatment}.one-slope",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "two_step_slope": _cluster_interval(
            slope_two,
            spec.master_seed,
            f"origin-pedigree.{treatment}.two-slope",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
    }


def _causal_summary(
    values: list[dict[str, Any]],
    treatment: str,
    evolution: OriginEvolutionSpec,
) -> dict[str, Any]:
    keys = (
        "founder_write_off_g8",
        "reader_off_g8",
        "renewal_off_g8",
        "renewal_block_g1_g4_g8",
        "renewal_block_g9_g12_g12",
        "shuffle_g8",
        "erasure_reduction_g8",
        "rescue_fraction_g8",
        "donor_following_g0",
    )
    collected = {key: [] for key in keys}
    for value in values:
        causal = value.get("causal_metrics")
        if causal is None:
            continue
        for key in keys:
            collected[key].append(float(causal[key]))
    return {
        key: _interval(
            items,
            evolution.master_seed,
            f"origin-causal.{treatment}.{key}",
            evolution.bootstrap_repetitions,
            evolution.interval_level,
            len(keys),
        )
        for key, items in collected.items()
    }


def _positive_lower(value: dict[str, Any]) -> bool:
    return value["lower"] is not None and float(value["lower"]) > 0.0


def analyze_origin_audit(
    population_results: list[dict[str, Any]],
    pedigree_rows: list[dict[str, Any]],
    evolution: OriginEvolutionSpec,
    audit: OriginAuditSpec,
) -> dict[str, Any]:
    """Compute layered exploratory verdicts with population-level inference."""

    grouped = {
        treatment: sorted(
            [value for value in population_results if value["treatment"] == treatment],
            key=lambda value: int(value["population_index"]),
        )
        for treatment in ORIGIN_TREATMENTS
    }
    summaries: dict[str, Any] = {}
    simultaneous = len(ORIGIN_TREATMENTS)
    for treatment, values in grouped.items():
        selected_g8 = [float(value["selected_g8"]) for value in values]
        founder_g8 = [float(value["founder_g8"]) for value in values]
        renewal = [float(value["renewal_contrast_g8"]) for value in values]
        summaries[treatment] = {
            "selected_g8": _interval(
                selected_g8,
                evolution.master_seed,
                f"origin-audit.{treatment}.selected-g8",
                evolution.bootstrap_repetitions,
                evolution.interval_level,
                simultaneous,
            ),
            "founder_to_selected_g8": _interval(
                (left - right for left, right in zip(selected_g8, founder_g8)),
                evolution.master_seed,
                f"origin-audit.{treatment}.improvement",
                evolution.bootstrap_repetitions,
                evolution.interval_level,
                simultaneous,
            ),
            "selected_g12": _interval(
                (float(value["selected_g12"]) for value in values),
                evolution.master_seed,
                f"origin-audit.{treatment}.selected-g12",
                evolution.bootstrap_repetitions,
                evolution.interval_level,
                simultaneous,
            ),
            "selected_g16": _interval(
                (float(value["selected_g16"]) for value in values),
                evolution.master_seed,
                f"origin-audit.{treatment}.selected-g16",
                evolution.bootstrap_repetitions,
                evolution.interval_level,
                simultaneous,
            ),
            "renewal_contrast_g8": _interval(
                renewal,
                evolution.master_seed,
                f"origin-audit.{treatment}.renewal-g8",
                evolution.bootstrap_repetitions,
                evolution.interval_level,
                simultaneous,
            ),
            "next_harsher_g8": _interval(
                (float(value["harsher_g8"]) for value in values),
                evolution.master_seed,
                f"origin-audit.{treatment}.harsher-g8",
                evolution.bootstrap_repetitions,
                evolution.interval_level,
                simultaneous,
            ),
            "writer_reader_active_populations": sum(
                bool(value["selected_writer_active"])
                and bool(value["selected_reader_active"])
                for value in values
            ),
            "population_count": len(values),
            "primary_condition": values[0]["primary_condition"] if values else None,
        }
    contrasts: dict[str, Any] = {}
    for scaffold in ("dormant", "weak"):
        explicit = f"{scaffold}_explicit_renewal"
        permissive = f"{scaffold}_permissive_performance"
        passive = f"{scaffold}_passive_locked"
        for label, left, right in (
            ("explicit_minus_permissive", explicit, permissive),
            ("explicit_minus_passive", explicit, passive),
            ("permissive_minus_passive", permissive, passive),
        ):
            contrasts[f"{scaffold}.{label}"] = _interval(
                _paired(population_results, left, right, "selected_g8"),
                evolution.master_seed,
                f"origin-audit.{scaffold}.{label}",
                evolution.bootstrap_repetitions,
                evolution.interval_level,
                6,
            )
    causal = {
        treatment: _causal_summary(grouped[treatment], treatment, evolution)
        for treatment in EXPLICIT_TREATMENTS
    }
    pedigree = {
        treatment: _pedigree_summary(pedigree_rows, treatment, audit)
        for treatment in EXPLICIT_TREATMENTS
    }
    scaffold_criteria: dict[str, dict[str, bool]] = {}
    for scaffold in ("dormant", "weak"):
        explicit_name = f"{scaffold}_explicit_renewal"
        permissive_name = f"{scaffold}_permissive_performance"
        explicit = summaries[explicit_name]
        permissive = summaries[permissive_name]
        explicit_passive = contrasts[f"{scaffold}.explicit_minus_passive"]
        permissive_passive = contrasts[f"{scaffold}.permissive_minus_passive"]
        explicit_permissive = contrasts[f"{scaffold}.explicit_minus_permissive"]
        causal_value = causal[explicit_name]
        pedigree_value = pedigree[explicit_name]
        scaffold_criteria[scaffold] = {
            "writer_reader_active_in_at_least_5_of_6": explicit[
                "writer_reader_active_populations"
            ]
            >= 5,
            "founder_improvement_mean_at_least_0_05": float(
                explicit["founder_to_selected_g8"]["mean"] or -1.0
            )
            >= 0.05,
            "founder_improvement_lower_above_zero": _positive_lower(
                explicit["founder_to_selected_g8"]
            ),
            "renewal_contrast_mean_at_least_0_10": float(
                explicit["renewal_contrast_g8"]["mean"] or -1.0
            )
            >= 0.10,
            "renewal_contrast_lower_above_zero": _positive_lower(
                explicit["renewal_contrast_g8"]
            ),
            "generation_12_lower_above_zero": _positive_lower(explicit["selected_g12"]),
            "generation_16_lower_above_zero": _positive_lower(explicit["selected_g16"]),
            "explicit_beats_passive_by_0_10": float(
                explicit_passive["mean"] or -1.0
            )
            >= 0.10
            and _positive_lower(explicit_passive),
            "permissive_has_renewal_contrast": float(
                permissive["renewal_contrast_g8"]["mean"] or -1.0
            )
            >= 0.10
            and _positive_lower(permissive["renewal_contrast_g8"]),
            "permissive_beats_passive_by_0_10": float(
                permissive_passive["mean"] or -1.0
            )
            >= 0.10
            and _positive_lower(permissive_passive),
            "explicit_beats_permissive_by_0_05": float(
                explicit_permissive["mean"] or -1.0
            )
            >= 0.05
            and _positive_lower(explicit_permissive),
            "write_read_renew_shuffle_and_windows_positive": all(
                _positive_lower(causal_value[key])
                for key in (
                    "founder_write_off_g8",
                    "reader_off_g8",
                    "renewal_off_g8",
                    "renewal_block_g1_g4_g8",
                    "renewal_block_g9_g12_g12",
                    "shuffle_g8",
                )
            ),
            "erasure_removes_at_least_0_70": float(
                causal_value["erasure_reduction_g8"]["mean"] or -1.0
            )
            >= 0.70,
            "rescue_restores_at_least_0_70": float(
                causal_value["rescue_fraction_g8"]["mean"] or -1.0
            )
            >= 0.70,
            "donor_following_at_least_0_20": float(
                causal_value["donor_following_g0"]["mean"] or -1.0
            )
            >= 0.20
            and _positive_lower(causal_value["donor_following_g0"]),
            "one_step_retention_lower_at_least_0_70": float(
                pedigree_value["one_step_retention"]["lower"] or -1.0
            )
            >= 0.70,
            "two_step_retention_lower_at_least_0_50": float(
                pedigree_value["two_step_retention"]["lower"] or -1.0
            )
            >= 0.50,
            "one_and_two_step_slopes_positive": _positive_lower(
                pedigree_value["one_step_slope"]
            )
            and _positive_lower(pedigree_value["two_step_slope"]),
        }
    dormant = scaffold_criteria["dormant"]
    activation_keys = (
        "writer_reader_active_in_at_least_5_of_6",
        "founder_improvement_mean_at_least_0_05",
        "founder_improvement_lower_above_zero",
        "renewal_contrast_mean_at_least_0_10",
        "renewal_contrast_lower_above_zero",
        "generation_12_lower_above_zero",
        "generation_16_lower_above_zero",
    )
    causal_keys = (
        "write_read_renew_shuffle_and_windows_positive",
        "erasure_removes_at_least_0_70",
        "rescue_restores_at_least_0_70",
        "donor_following_at_least_0_20",
    )
    mutation_keys = (
        "one_step_retention_lower_at_least_0_70",
        "two_step_retention_lower_at_least_0_50",
        "one_and_two_step_slopes_positive",
    )
    return {
        "format": ORIGIN_AUDIT_FORMAT,
        "population_count": len(population_results),
        "pedigree_rows": len(pedigree_rows),
        "population_is_inferential_unit": True,
        "descendants_are_not_independent_replicates": True,
        "common_tasks_and_streams_verified": all(
            bool(value["common_streams_verified"]) for value in population_results
        ),
        "descendants_receive_no_inducing_cue": True,
        "treatments": summaries,
        "paired_contrasts": contrasts,
        "causal": causal,
        "pedigree": pedigree,
        "criteria_by_scaffold": scaffold_criteria,
        "verdict": {
            "dormant_activation_nominated": all(dormant[key] for key in activation_keys),
            "renewal_necessity_nominated": dormant[
                "explicit_beats_passive_by_0_10"
            ],
            "implicit_renewal_explanation_supported": dormant[
                "permissive_has_renewal_contrast"
            ]
            and dormant["permissive_beats_passive_by_0_10"],
            "explicit_selection_advantage_nominated": dormant[
                "explicit_beats_permissive_by_0_05"
            ],
            "causal_ph_mechanism_nominated": all(dormant[key] for key in causal_keys),
            "mutation_robustness_nominated": all(
                dormant[key] for key in mutation_keys
            ),
            "weak_scaffold_replication_passed": all(
                scaffold_criteria["weak"][key]
                for key in (*activation_keys, *causal_keys)
            ),
        },
        "claim_boundary": (
            "This exploratory in-silico campaign can show activation of a predefined "
            "target-blind carrier channel. It cannot show de-novo molecular invention or "
            "establish that the mechanism arose in nature."
        ),
    }


def render_origin_audit_report(analysis: dict[str, Any]) -> str:
    verdict = analysis["verdict"]
    lines = [
        "# Wagner PH origin held-out causal and pedigree audit",
        "",
    ]
    labels = (
        ("Dormant activation", "dormant_activation_nominated"),
        ("Renewal necessity", "renewal_necessity_nominated"),
        ("Implicit-renewal explanation", "implicit_renewal_explanation_supported"),
        ("Explicit-selection advantage", "explicit_selection_advantage_nominated"),
        ("Causal PH mechanism", "causal_ph_mechanism_nominated"),
        ("Mutation robustness", "mutation_robustness_nominated"),
        ("Weak-scaffold replication", "weak_scaffold_replication_passed"),
    )
    lines.extend(
        f"- {label}: **{'PASS' if verdict[key] else 'fail'}**"
        for label, key in labels
    )
    lines.extend(
        (
            f"- Population count: {analysis['population_count']}",
            f"- Pedigree rows: {analysis['pedigree_rows']}",
            f"- Common streams verified: `{analysis['common_tasks_and_streams_verified']}`",
            "",
            analysis["claim_boundary"],
            "",
        )
    )
    return "\n".join(lines)
