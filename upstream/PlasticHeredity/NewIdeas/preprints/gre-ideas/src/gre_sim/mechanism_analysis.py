"""Streaming, rulebook-level analysis for exploratory mechanism phases."""

from __future__ import annotations

import collections
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import read_jsonl_gz
from .mechanism_config import MECHANISM_ANALYSIS_FORMAT, MechanismSpec
from .rng import rng_for


ENDPOINT_FIELDS = {
    "frozen_library": "frozen_destination",
    "exact_point_state": "point_state_destination",
    "realized_signature": "signature_destination",
    "competing_outcome": "competing_outcome",
}
RATE_FIELDS = (
    "active_capture",
    "stable_point_capture",
    "stable_signature_capture",
    "strict_library",
    "strict_state",
    "old_return",
)
KAPPA_GRID = (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)

CellKey = tuple[str, str, int, str, float, float, str]
StratumKey = tuple[str, str, int, str, float, float, str]
SelectorKey = tuple[str, str, float, float, str]
SourceGroupKey = tuple[str, str, str, float, float, str]


def _cell_key(record: dict[str, Any]) -> CellKey:
    return (
        str(record["condition"]),
        str(record["source_id"]),
        int(record["state_id"]),
        str(record["arm"]),
        float(record["carryover"]),
        float(record["gamma_variance"]),
        str(record["inheritance_mode"]),
    )


def _stratum_key(record: dict[str, Any]) -> StratumKey:
    return (
        str(record["condition"]),
        str(record["variant"]),
        int(record["genes"]),
        str(record["arm"]),
        float(record["carryover"]),
        float(record["gamma_variance"]),
        str(record["inheritance_mode"]),
    )


def _stratum_label(key: StratumKey) -> str:
    condition, variant, genes, arm, carryover, variance, mode = key
    return (
        f"{condition}.{variant}.N-{genes}.{arm}.lambda-{carryover:g}."
        f"theta-{variance:g}.{mode}"
    )


def _smoothed(
    counts: collections.Counter[str], categories: tuple[str, ...], alpha: float
) -> dict[str, float]:
    denominator = sum(counts.values()) + alpha * len(categories)
    if denominator <= 0.0:
        return {category: 1.0 / len(categories) for category in categories}
    return {
        category: (counts.get(category, 0) + alpha) / denominator
        for category in categories
    }


def _hierarchical(
    counts: collections.Counter[str],
    prior: dict[str, float],
    categories: tuple[str, ...],
    alpha: float,
    kappa: float,
) -> dict[str, float]:
    denominator = sum(counts.values()) + alpha * len(categories) + kappa
    return {
        category: (
            counts.get(category, 0) + alpha + kappa * prior[category]
        )
        / denominator
        for category in categories
    }


def _loss(probabilities: dict[str, float], label: str) -> float:
    return -math.log(max(probabilities.get(label, 0.0), np.finfo(float).tiny))


def _brier(
    probabilities: dict[str, float], label: str, categories: tuple[str, ...]
) -> float:
    return float(
        sum(
            (probabilities[category] - float(category == label)) ** 2
            for category in categories
        )
    )


def _bootstrap(
    values: list[float], spec: MechanismSpec, label: str
) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return float("nan"), float("nan")
    if array.size == 1:
        return float(array[0]), float(array[0])
    rng = rng_for(spec.master_seed, "mechanism-bootstrap", label)
    indices = rng.integers(
        0, array.size, size=(spec.bootstrap_repetitions, array.size)
    )
    means = np.mean(array[indices], axis=1)
    tail = (1.0 - spec.interval_level) / 2.0
    return float(np.quantile(means, tail)), float(np.quantile(means, 1.0 - tail))


def _selector_key(cell: CellKey) -> SelectorKey:
    return cell[0], cell[3], cell[4], cell[5], cell[6]


def _source_group_key(cell: CellKey) -> SourceGroupKey:
    return cell[0], cell[1], cell[3], cell[4], cell[5], cell[6]


def _pooled_totals(
    counts: dict[CellKey, collections.Counter[str]],
) -> dict[SourceGroupKey, collections.Counter[str]]:
    totals: dict[SourceGroupKey, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    for cell, value in counts.items():
        totals[_source_group_key(cell)].update(value)
    return totals


def _other_state_counts(
    counts: dict[CellKey, collections.Counter[str]],
    totals: dict[SourceGroupKey, collections.Counter[str]],
    cell: CellKey,
) -> collections.Counter[str]:
    pooled = totals.get(_source_group_key(cell), collections.Counter()).copy()
    pooled.subtract(counts.get(cell, collections.Counter()))
    return +pooled


def _tuned_kappas(
    endpoint: str,
    mapping_half: str,
    parity_counts: dict[
        str,
        dict[str, dict[int, dict[CellKey, collections.Counter[str]]]],
    ],
    categories: dict[tuple[str, str, str], set[str]],
    alpha: float,
) -> dict[tuple[SelectorKey, str], float]:
    """Tune leave-one-rulebook-out shrinkage in linear time per endpoint."""

    losses: dict[SelectorKey, np.ndarray] = collections.defaultdict(
        lambda: np.zeros(len(KAPPA_GRID), dtype=float)
    )
    observations: collections.Counter[SelectorKey] = collections.Counter()
    source_losses: dict[tuple[SelectorKey, str], np.ndarray] = (
        collections.defaultdict(
            lambda: np.zeros(len(KAPPA_GRID), dtype=float)
        )
    )
    source_observations: collections.Counter[tuple[SelectorKey, str]] = (
        collections.Counter()
    )
    selector_sources: dict[SelectorKey, set[str]] = collections.defaultdict(set)
    endpoint_counts = parity_counts[endpoint][mapping_half]
    for validation_parity in (0, 1):
        training = endpoint_counts[1 - validation_parity]
        validation = endpoint_counts[validation_parity]
        pooled_totals = _pooled_totals(training)
        for cell, valid_counts in validation.items():
            selector = _selector_key(cell)
            source = cell[1]
            selector_sources[selector].add(source)
            scope = (endpoint, cell[0], cell[1])
            local_categories = tuple(sorted(categories[scope]))
            prior = _smoothed(
                _other_state_counts(training, pooled_totals, cell),
                local_categories,
                alpha,
            )
            cell_counts = training.get(cell, collections.Counter())
            observation_count = sum(valid_counts.values())
            observations[selector] += observation_count
            source_observations[(selector, source)] += observation_count
            for index, kappa in enumerate(KAPPA_GRID):
                probabilities = _hierarchical(
                    cell_counts, prior, local_categories, alpha, kappa
                )
                loss = sum(
                    amount * _loss(probabilities, label)
                    for label, amount in valid_counts.items()
                )
                losses[selector][index] += loss
                source_losses[(selector, source)][index] += loss
    selected: dict[tuple[SelectorKey, str], float] = {}
    for selector, sources in selector_sources.items():
        for heldout_source in sources:
            heldout = (selector, heldout_source)
            count = observations[selector] - source_observations[heldout]
            if count <= 0:
                selected[heldout] = KAPPA_GRID[0]
                continue
            heldout_losses = losses[selector] - source_losses[heldout]
            best = min(
                range(len(KAPPA_GRID)),
                key=lambda index: (heldout_losses[index] / count, KAPPA_GRID[index]),
            )
            selected[heldout] = KAPPA_GRID[best]
    return selected


def _collect(
    records: Iterable[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, dict[CellKey, collections.Counter[str]]]],
    dict[str, dict[str, dict[int, dict[CellKey, collections.Counter[str]]]]],
    dict[tuple[str, str, str], set[str]],
    dict[tuple[StratumKey, str, str], list[float]],
    dict[tuple[StratumKey, str, str], list[float]],
    dict[tuple[StratumKey, str], collections.Counter[str]],
    int,
]:
    cell_counts: dict[
        str, dict[str, dict[CellKey, collections.Counter[str]]]
    ] = {
        endpoint: {
            "A": collections.defaultdict(collections.Counter),
            "B": collections.defaultdict(collections.Counter),
        }
        for endpoint in ENDPOINT_FIELDS
    }
    parity_counts: dict[
        str,
        dict[str, dict[int, dict[CellKey, collections.Counter[str]]]],
    ] = {
        endpoint: {
            half: {
                0: collections.defaultdict(collections.Counter),
                1: collections.defaultdict(collections.Counter),
            }
            for half in ("A", "B")
        }
        for endpoint in ENDPOINT_FIELDS
    }
    categories: dict[tuple[str, str, str], set[str]] = collections.defaultdict(set)
    source_rates: dict[tuple[StratumKey, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    source_runs: dict[tuple[StratumKey, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    outcomes: dict[tuple[StratumKey, str], collections.Counter[str]] = (
        collections.defaultdict(collections.Counter)
    )
    record_count = 0
    for record in records:
        record_count += 1
        cell = _cell_key(record)
        stratum = _stratum_key(record)
        half = str(record["half"])
        parity = int(record["future_index"]) % 2
        for endpoint, field in ENDPOINT_FIELDS.items():
            label = str(record[field])
            cell_counts[endpoint][half][cell][label] += 1
            parity_counts[endpoint][half][parity][cell][label] += 1
            categories[(endpoint, cell[0], cell[1])].add(label)
        for field in RATE_FIELDS:
            values = source_rates[(stratum, str(record["source_id"]), field)]
            values[0] += float(record[field])
            values[1] += 1.0
        for family, field in (
            ("library", "strict_library_by_run"),
            ("state", "strict_state_by_run"),
        ):
            for index, value in enumerate(record[field], start=1):
                values = source_runs[
                    (stratum, str(record["source_id"]), f"{family}.run-{index}")
                ]
                values[0] += float(value)
                values[1] += 1.0
        outcomes[(stratum, str(record["source_id"]))][
            str(record["competing_outcome"])
        ] += 1
    return (
        cell_counts,
        parity_counts,
        categories,
        source_rates,
        source_runs,
        outcomes,
        record_count,
    )


def _score_committors(
    spec: MechanismSpec,
    cell_counts: dict[str, dict[str, dict[CellKey, collections.Counter[str]]]],
    parity_counts: dict[
        str,
        dict[str, dict[int, dict[CellKey, collections.Counter[str]]]],
    ],
    categories: dict[tuple[str, str, str], set[str]],
    alpha: float = 0.5,
) -> tuple[dict[str, Any], dict[tuple[str, StratumKey, str], float]]:
    source_metrics: dict[
        tuple[str, StratumKey, str], list[float]
    ] = collections.defaultdict(lambda: [0.0] * 7)
    kappa_counts: collections.Counter[str] = collections.Counter()
    for endpoint in ENDPOINT_FIELDS:
        for mapping_half, evaluation_half in (("A", "B"), ("B", "A")):
            mapping = cell_counts[endpoint][mapping_half]
            evaluation = cell_counts[endpoint][evaluation_half]
            pooled_totals = _pooled_totals(mapping)
            tuned_kappas = _tuned_kappas(
                endpoint,
                mapping_half,
                parity_counts,
                categories,
                alpha,
            )
            for cell, evaluation_counts in evaluation.items():
                scope = (endpoint, cell[0], cell[1])
                local_categories = tuple(sorted(categories[scope]))
                prior = _smoothed(
                    _other_state_counts(mapping, pooled_totals, cell),
                    local_categories,
                    alpha,
                )
                kappa = tuned_kappas.get(
                    (_selector_key(cell), cell[1]), KAPPA_GRID[0]
                )
                kappa_counts[f"{endpoint}.kappa-{kappa:g}"] += 1
                hierarchical = _hierarchical(
                    mapping.get(cell, collections.Counter()),
                    prior,
                    local_categories,
                    alpha,
                    kappa,
                )
                condition, source_id, _, arm, carryover, variance, mode = cell
                # Variant and gene count are constant within each condition/source.
                matching_strata = [
                    key
                    for key in _SOURCE_STRATA[source_id]
                    if key[0] == condition
                    and key[3] == arm
                    and key[4] == carryover
                    and key[5] == variance
                    and key[6] == mode
                ]
                if len(matching_strata) != 1:
                    raise RuntimeError("could not resolve mechanism analysis stratum")
                stratum = matching_strata[0]
                metrics = source_metrics[(endpoint, stratum, source_id)]
                for label, amount in evaluation_counts.items():
                    base_loss = _loss(prior, label)
                    hier_loss = _loss(hierarchical, label)
                    metrics[0] += amount * (base_loss - hier_loss)
                    metrics[1] += amount * (
                        _brier(prior, label, local_categories)
                        - _brier(hierarchical, label, local_categories)
                    )
                    metrics[2] += amount
                    metrics[3] += amount * hier_loss
                    metrics[4] += amount * base_loss
                    prediction = max(local_categories, key=hierarchical.get)
                    baseline_prediction = max(local_categories, key=prior.get)
                    metrics[5] += amount * float(prediction == label)
                    metrics[6] += amount * float(baseline_prediction == label)
    source_gains: dict[tuple[str, StratumKey, str], float] = {}
    grouped: dict[tuple[str, StratumKey], list[list[float]]] = collections.defaultdict(list)
    for key, metrics in source_metrics.items():
        count = metrics[2]
        if not count:
            continue
        source_gains[key] = metrics[0] / count
        grouped[(key[0], key[1])].append(metrics)
    output: dict[str, Any] = {}
    for (endpoint, stratum), values in sorted(grouped.items(), key=lambda item: str(item[0])):
        source_values = [value[0] / value[2] for value in values]
        interval = _bootstrap(source_values, spec, f"committor:{endpoint}:{stratum}")
        total = sum(value[2] for value in values)
        output[f"{endpoint}.{_stratum_label(stratum)}"] = {
            "rulebooks": len(values),
            "futures": int(total),
            "mean_log_loss_gain": float(np.mean(source_values)),
            "interval": list(interval),
            "mean_brier_gain": float(sum(value[1] for value in values) / total),
            "committor_log_loss": float(sum(value[3] for value in values) / total),
            "baseline_log_loss": float(sum(value[4] for value in values) / total),
            "committor_accuracy": float(sum(value[5] for value in values) / total),
            "baseline_accuracy": float(sum(value[6] for value in values) / total),
        }
    output["shrinkage_selection_counts"] = dict(sorted(kappa_counts.items()))
    return output, source_gains


# Populated once per analysis pass so the scoring loop need not retain full records.
_SOURCE_STRATA: dict[str, set[StratumKey]] = collections.defaultdict(set)


def _rate_tables(
    spec: MechanismSpec,
    source_rates: dict[tuple[StratumKey, str, str], list[float]],
    source_runs: dict[tuple[StratumKey, str, str], list[float]],
    outcomes: dict[tuple[StratumKey, str], collections.Counter[str]],
) -> tuple[dict[str, Any], dict[tuple[StratumKey, str, str], float]]:
    source_values: dict[tuple[StratumKey, str, str], float] = {}
    grouped: dict[tuple[StratumKey, str], list[float]] = collections.defaultdict(list)
    for (stratum, source, field), values in {**source_rates, **source_runs}.items():
        value = float(values[0] / values[1]) if values[1] else float("nan")
        source_values[(stratum, source, field)] = value
        grouped[(stratum, field)].append(value)
    rates: dict[str, Any] = {}
    for (stratum, field), values in sorted(grouped.items(), key=lambda item: str(item[0])):
        rates[f"{_stratum_label(stratum)}.{field}"] = {
            "rulebooks": len(values),
            "mean": float(np.mean(values)),
            "interval": list(_bootstrap(values, spec, f"rate:{stratum}:{field}")),
        }
    outcome_totals: dict[StratumKey, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    for (stratum, _), counter in outcomes.items():
        outcome_totals[stratum].update(counter)
    composition = {}
    for stratum, counter in sorted(outcome_totals.items(), key=lambda item: str(item[0])):
        total = sum(counter.values())
        composition[_stratum_label(stratum)] = {
            "futures": total,
            "counts": dict(sorted(counter.items())),
            "rates": {
                name: value / total for name, value in sorted(counter.items())
            },
        }
    return {"rates": rates, "outcome_composition": composition}, source_values


def _reliability(
    cell_counts: dict[str, dict[str, dict[CellKey, collections.Counter[str]]]],
    categories: dict[tuple[str, str, str], set[str]],
    alpha: float = 0.5,
) -> dict[str, float]:
    values: dict[tuple[str, StratumKey], list[float]] = collections.defaultdict(list)
    for endpoint in ENDPOINT_FIELDS:
        keys = set(cell_counts[endpoint]["A"]) | set(cell_counts[endpoint]["B"])
        for cell in keys:
            scope = (endpoint, cell[0], cell[1])
            local = tuple(sorted(categories[scope]))
            left = _smoothed(cell_counts[endpoint]["A"].get(cell, collections.Counter()), local, alpha)
            right = _smoothed(cell_counts[endpoint]["B"].get(cell, collections.Counter()), local, alpha)
            midpoint = {name: 0.5 * (left[name] + right[name]) for name in local}
            js = 0.5 * sum(
                left[name] * math.log(left[name] / midpoint[name])
                + right[name] * math.log(right[name] / midpoint[name])
                for name in local
            )
            matching = [
                key
                for key in _SOURCE_STRATA[cell[1]]
                if key[0] == cell[0]
                and key[3] == cell[3]
                and key[4] == cell[4]
                and key[5] == cell[5]
                and key[6] == cell[6]
            ]
            if len(matching) == 1:
                values[(endpoint, matching[0])].append(1.0 - js / math.log(2.0))
    return {
        f"{endpoint}.{_stratum_label(stratum)}": float(np.mean(scores))
        for (endpoint, stratum), scores in sorted(values.items(), key=lambda item: str(item[0]))
    }


def _paired_contrasts(
    spec: MechanismSpec,
    source_values: dict[tuple[StratumKey, str, str], float],
    source_gains: dict[tuple[str, StratumKey, str], float],
) -> dict[str, Any]:
    output: dict[str, Any] = {}

    def add(label: str, values: list[float]) -> None:
        output[label] = {
            "rulebooks": len(values),
            "mean": float(np.mean(values)) if values else float("nan"),
            "interval": list(_bootstrap(values, spec, f"contrast:{label}")),
        }

    strata = {key[0] for key in source_values}
    base_groups = sorted({key[:6] for key in strata}, key=str)
    fields = sorted({key[2] for key in source_values})
    for base in base_groups:
        condition, variant, genes, arm, carryover, variance = base
        self_key = (*base, "self")
        donor_key = (*base, "donor_shuffled")
        sources = sorted(
            {
                source
                for stratum, source, _ in source_values
                if stratum in {self_key, donor_key}
            }
        )
        for field in fields:
            values = [
                source_values[(self_key, source, field)]
                - source_values[(donor_key, source, field)]
                for source in sources
                if (self_key, source, field) in source_values
                and (donor_key, source, field) in source_values
            ]
            if values:
                add(
                    f"rate.self-minus-donor.{condition}.{variant}.N-{genes}."
                    f"{arm}.lambda-{carryover:g}.theta-{variance:g}.{field}",
                    values,
                )
    for endpoint in ENDPOINT_FIELDS:
        endpoint_keys = {key[1] for key in source_gains if key[0] == endpoint}
        endpoint_bases = sorted({key[:6] for key in endpoint_keys}, key=str)
        for base in endpoint_bases:
            condition, variant, genes, arm, carryover, variance = base
            self_key = (*base, "self")
            donor_key = (*base, "donor_shuffled")
            sources = sorted(
                {
                    key[2]
                    for key in source_gains
                    if key[0] == endpoint and key[1] in {self_key, donor_key}
                }
            )
            values = [
                source_gains[(endpoint, self_key, source)]
                - source_gains[(endpoint, donor_key, source)]
                for source in sources
                if (endpoint, self_key, source) in source_gains
                and (endpoint, donor_key, source) in source_gains
            ]
            if values:
                add(
                    f"committor.self-minus-donor.{endpoint}.{condition}.{variant}."
                    f"N-{genes}.{arm}.lambda-{carryover:g}.theta-{variance:g}",
                    values,
                )
        for condition, variant, genes, carryover, variance in sorted(
            {
                (key[0], key[1], key[2], key[4], key[5])
                for key in endpoint_keys
                if key[3] == "acute_mismatch"
            },
            key=str,
        ):
            for control in ("natural", "target_aligned_own_anchor"):
                keys = {
                    "as": (
                        condition,
                        variant,
                        genes,
                        "acute_mismatch",
                        carryover,
                        variance,
                        "self",
                    ),
                    "ad": (
                        condition,
                        variant,
                        genes,
                        "acute_mismatch",
                        carryover,
                        variance,
                        "donor_shuffled",
                    ),
                    "cs": (
                        condition,
                        variant,
                        genes,
                        control,
                        carryover,
                        variance,
                        "self",
                    ),
                    "cd": (
                        condition,
                        variant,
                        genes,
                        control,
                        carryover,
                        variance,
                        "donor_shuffled",
                    ),
                }
                sources = sorted(
                    set.intersection(
                        *(
                            {
                                source
                                for value_endpoint, stratum, source in source_gains
                                if value_endpoint == endpoint and stratum == key
                            }
                            for key in keys.values()
                        )
                    )
                )
                values = [
                    (
                        source_gains[(endpoint, keys["as"], source)]
                        - source_gains[(endpoint, keys["ad"], source)]
                    )
                    - (
                        source_gains[(endpoint, keys["cs"], source)]
                        - source_gains[(endpoint, keys["cd"], source)]
                    )
                    for source in sources
                ]
                if values:
                    add(
                        f"committor.interaction.acute-minus-{control}.{endpoint}."
                        f"{condition}.{variant}.N-{genes}.lambda-{carryover:g}."
                        f"theta-{variance:g}",
                        values,
                    )

    # Difference-in-differences against both registered controls.
    for field in fields:
        for condition, variant, genes, carryover, variance in sorted(
            {
                (key[0], key[1], key[2], key[4], key[5])
                for key in strata
                if key[3] == "acute_mismatch"
            },
            key=str,
        ):
            for control in ("natural", "target_aligned_own_anchor"):
                keys = {
                    "as": (condition, variant, genes, "acute_mismatch", carryover, variance, "self"),
                    "ad": (condition, variant, genes, "acute_mismatch", carryover, variance, "donor_shuffled"),
                    "cs": (condition, variant, genes, control, carryover, variance, "self"),
                    "cd": (condition, variant, genes, control, carryover, variance, "donor_shuffled"),
                }
                sources = sorted(
                    set.intersection(
                        *(
                            {
                                source
                                for stratum, source, value_field in source_values
                                if stratum == key and value_field == field
                            }
                            for key in keys.values()
                        )
                    )
                )
                values = [
                    (source_values[(keys["as"], source, field)] - source_values[(keys["ad"], source, field)])
                    - (source_values[(keys["cs"], source, field)] - source_values[(keys["cd"], source, field)])
                    for source in sources
                ]
                if values:
                    add(
                        f"rate.interaction.acute-minus-{control}.{condition}.{variant}."
                        f"N-{genes}.lambda-{carryover:g}.theta-{variance:g}.{field}",
                        values,
                    )
    return output


def analyze_mechanism_records(
    records_path: Path, spec: MechanismSpec
) -> dict[str, Any]:
    """Analyze one sealed raw mechanism stream without materializing all futures."""

    global _SOURCE_STRATA
    _SOURCE_STRATA = collections.defaultdict(set)
    # A light first scan resolves variant/gene strata without retaining records.
    for record in read_jsonl_gz(records_path):
        _SOURCE_STRATA[str(record["source_id"])].add(_stratum_key(record))
    (
        cell_counts,
        parity_counts,
        categories,
        source_rates,
        source_runs,
        outcomes,
        record_count,
    ) = _collect(read_jsonl_gz(records_path))
    committor, source_gains = _score_committors(
        spec, cell_counts, parity_counts, categories
    )
    rate_output, source_values = _rate_tables(
        spec, source_rates, source_runs, outcomes
    )
    return {
        "format": MECHANISM_ANALYSIS_FORMAT,
        "protocol_format": spec.protocol_format,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "exploratory": True,
        "futures": record_count,
        "endpoint_families": ENDPOINT_FIELDS,
        **rate_output,
        "committor": committor,
        "contrasts": _paired_contrasts(spec, source_values, source_gains),
        "split_half_reliability": _reliability(cell_counts, categories),
        "analysis_contract": {
            "independent_unit": "rulebook",
            "interval": spec.interval_level,
            "bootstrap_repetitions": spec.bootstrap_repetitions,
            "evaluation_half_used_for_shrinkage_selection": False,
            "kappa_grid": list(KAPPA_GRID),
            "outcomes_dropped": False,
        },
    }
