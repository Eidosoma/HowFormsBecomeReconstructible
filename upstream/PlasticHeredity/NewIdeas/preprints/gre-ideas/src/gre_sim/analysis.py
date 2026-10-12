"""Cross-fitted destination-committor analysis at the rulebook level."""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from .campaign import _arm_values
from .config import ANALYSIS_FORMAT, StudySpec, analysis_format
from .landscape import Landscape, normalized_hamming
from .rng import rng_for


CELL_KEYS = ("engine", "cohort", "source_id", "state_id", "arm", "carryover")
V2_CELL_KEYS = (*CELL_KEYS, "inheritance_mode")
V2_SOURCE_KEYS = (
    "engine",
    "cohort",
    "source_id",
    "arm",
    "carryover",
    "inheritance_mode",
)
V2_STRATUM_KEYS = ("engine", "cohort", "arm", "carryover", "inheritance_mode")
SHRINKAGE_KAPPAS = (0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)


def _key(record: dict[str, Any], names: tuple[str, ...] = CELL_KEYS) -> tuple[Any, ...]:
    return tuple(record[name] for name in names)


def _group(records: Iterable[dict[str, Any]], names: tuple[str, ...]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    result: dict[tuple[Any, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for record in records:
        result[_key(record, names)].append(record)
    return dict(result)


def _smoothed_probabilities(
    counts: collections.Counter[str], categories: tuple[str, ...], alpha: float
) -> dict[str, float]:
    denominator = sum(counts.get(category, 0) for category in categories) + alpha * len(categories)
    if denominator <= 0:
        return {category: 1.0 / len(categories) for category in categories}
    return {
        category: (counts.get(category, 0) + alpha) / denominator
        for category in categories
    }


def _loss(probabilities: dict[str, float], destination: str) -> float:
    return -math.log(max(probabilities.get(destination, 0.0), 1e-15))


def _brier(
    probabilities: dict[str, float], destination: str, categories: tuple[str, ...]
) -> float:
    return float(
        sum(
            (probabilities.get(category, 0.0) - float(category == destination)) ** 2
            for category in categories
        )
    )


@dataclass
class ArmContext:
    landscape: Landscape
    base_state: int


class RegistryContexts:
    def __init__(self, registry: dict[str, Any]):
        self.bundles = {bundle["source_id"]: bundle for bundle in registry["sources"]}
        self.cache: dict[tuple[str, int, str], ArmContext] = {}

    def get(self, source_id: str, state_id: int, arm: str) -> ArmContext:
        cache_key = (source_id, state_id, arm)
        if cache_key not in self.cache:
            bundle = self.bundles[source_id]
            launch = next(
                value for value in bundle["launches"] if int(value["state_id"]) == state_id
            )
            rulebook, base_state, _, _ = _arm_values(bundle, launch, arm)
            self.cache[cache_key] = ArmContext(rulebook.landscape(), base_state)
        return self.cache[cache_key]


class MappingIndex:
    """O(1) leave-state/source destination counts for one cross-fit direction."""

    def __init__(self, records: list[dict[str, Any]]):
        self.records = records
        self.cell: dict[tuple[Any, ...], collections.Counter[str]] = collections.defaultdict(collections.Counter)
        self.source: dict[tuple[Any, ...], collections.Counter[str]] = collections.defaultdict(collections.Counter)
        self.stratum: dict[tuple[Any, ...], collections.Counter[str]] = collections.defaultdict(collections.Counter)
        for record in records:
            destination = record["destination"]
            self.cell[_key(record)][destination] += 1
            self.source[
                _key(record, ("engine", "cohort", "source_id", "arm", "carryover"))
            ][destination] += 1
            self.stratum[
                _key(record, ("engine", "cohort", "arm", "carryover"))
            ][destination] += 1

    @staticmethod
    def _difference(
        total: collections.Counter[str], removed: collections.Counter[str]
    ) -> collections.Counter[str]:
        return collections.Counter(
            {
                category: total.get(category, 0) - removed.get(category, 0)
                for category in set(total) | set(removed)
                if total.get(category, 0) - removed.get(category, 0) > 0
            }
        )

    def pooled_counts(self, record: dict[str, Any]) -> collections.Counter[str]:
        source_key = _key(
            record, ("engine", "cohort", "source_id", "arm", "carryover")
        )
        within = self._difference(self.source[source_key], self.cell[_key(record)])
        if sum(within.values()) > 0:
            return within
        stratum_key = _key(record, ("engine", "cohort", "arm", "carryover"))
        return self._difference(self.stratum[stratum_key], self.source[source_key])


class V2MappingIndex:
    """Mode-aware mapping counts for the v2 prototype."""

    def __init__(self, records: list[dict[str, Any]]):
        self.records = records
        self.cell: dict[
            tuple[Any, ...], collections.Counter[str]
        ] = collections.defaultdict(collections.Counter)
        self.source: dict[
            tuple[Any, ...], collections.Counter[str]
        ] = collections.defaultdict(collections.Counter)
        self.stratum: dict[
            tuple[Any, ...], collections.Counter[str]
        ] = collections.defaultdict(collections.Counter)
        for record in records:
            destination = record["destination"]
            self.cell[_key(record, V2_CELL_KEYS)][destination] += 1
            self.source[_key(record, V2_SOURCE_KEYS)][destination] += 1
            self.stratum[_key(record, V2_STRATUM_KEYS)][destination] += 1

    def pooled_counts(self, record: dict[str, Any]) -> collections.Counter[str]:
        source_key = _key(record, V2_SOURCE_KEYS)
        within = MappingIndex._difference(
            self.source[source_key], self.cell[_key(record, V2_CELL_KEYS)]
        )
        if sum(within.values()) > 0:
            return within
        return MappingIndex._difference(
            self.stratum[_key(record, V2_STRATUM_KEYS)], self.source[source_key]
        )


def _local_categories(context: ArmContext) -> tuple[str, ...]:
    return tuple(
        sorted(
            {attractor.label for attractor in context.landscape.attractors}
            | {
                "off_library",
                "noise_specific_cycle",
                "nonconvergent",
                "no_stable_destination",
            }
        )
    )


def _basin_probabilities(
    context: ArmContext,
    categories: tuple[str, ...],
    alpha: float,
) -> dict[str, float]:
    counts: collections.Counter[str] = collections.Counter()
    for attractor, size in zip(context.landscape.attractors, context.landscape.basin_sizes):
        counts[attractor.label] += int(size)
    return _smoothed_probabilities(counts, categories, alpha)


def _distance_probabilities(
    context: ArmContext,
    categories: tuple[str, ...],
    genes: int,
    temperature: float,
    alpha: float,
) -> dict[str, float]:
    weights: dict[str, float] = {category: alpha for category in categories}
    for attractor in context.landscape.attractors:
        distance = min(
            normalized_hamming(context.base_state, state, genes)
            for state in attractor.states
        )
        weights[attractor.label] = weights.get(attractor.label, alpha) + math.exp(
            -distance / temperature
        )
    denominator = sum(weights.values())
    return {category: weights[category] / denominator for category in categories}


def _pooled_probabilities(
    mapping_index: MappingIndex,
    record: dict[str, Any],
    categories: tuple[str, ...],
    alpha: float,
) -> dict[str, float]:
    return _smoothed_probabilities(mapping_index.pooled_counts(record), categories, alpha)


def _fit_temperature(
    mapping_records: list[dict[str, Any]],
    registry_contexts: RegistryContexts,
    spec: StudySpec,
) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    strata = sorted({(item["engine"], item["cohort"]) for item in mapping_records})
    for stratum in strata:
        relevant = [
            item
            for item in mapping_records
            if (item["engine"], item["cohort"]) == stratum
        ]
        genes = spec.boolean.genes if stratum[0] == "boolean" else spec.wagner.genes
        best_temperature = spec.distance_temperatures[0]
        best_loss = float("inf")
        for temperature in spec.distance_temperatures:
            losses = []
            for record in relevant:
                context = registry_contexts.get(
                    record["source_id"], int(record["state_id"]), record["arm"]
                )
                categories = _local_categories(context)
                probabilities = _distance_probabilities(
                    context,
                    categories,
                    genes,
                    temperature,
                    spec.dirichlet_alpha,
                )
                losses.append(_loss(probabilities, record["destination"]))
            mean_loss = float(np.mean(losses)) if losses else float("inf")
            if mean_loss < best_loss:
                best_loss = mean_loss
                best_temperature = temperature
        result[stratum] = float(best_temperature)
    return result


def _baseline_predictions(
    record: dict[str, Any],
    mapping_index: MappingIndex,
    registry_contexts: RegistryContexts,
    categories: tuple[str, ...],
    temperature: float,
    spec: StudySpec,
) -> dict[str, dict[str, float]]:
    context = registry_contexts.get(
        record["source_id"], int(record["state_id"]), record["arm"]
    )
    genes = spec.boolean.genes if record["engine"] == "boolean" else spec.wagner.genes
    return {
        "basin": _basin_probabilities(context, categories, spec.dirichlet_alpha),
        "distance": _distance_probabilities(
            context,
            categories,
            genes,
            temperature,
            spec.dirichlet_alpha,
        ),
        "pooled": _pooled_probabilities(
            mapping_index, record, categories, spec.dirichlet_alpha
        ),
    }


def _mapping_baseline_losses(
    mapping_records: list[dict[str, Any]],
    mapping_index: MappingIndex,
    registry_contexts: RegistryContexts,
    temperatures: dict[tuple[str, str], float],
    spec: StudySpec,
) -> tuple[dict[tuple[Any, ...], tuple[float, int]], dict[tuple[Any, ...], tuple[float, int]]]:
    totals: dict[tuple[Any, ...], list[float | int]] = collections.defaultdict(lambda: [0.0, 0])
    sources: dict[tuple[Any, ...], list[float | int]] = collections.defaultdict(lambda: [0.0, 0])
    for record in mapping_records:
        stratum = (record["engine"], record["cohort"])
        context = registry_contexts.get(
            record["source_id"], int(record["state_id"]), record["arm"]
        )
        predictions = _baseline_predictions(
            record,
            mapping_index,
            registry_contexts,
            _local_categories(context),
            temperatures[stratum],
            spec,
        )
        for name, probability in predictions.items():
            loss = _loss(probability, record["destination"])
            total_key = (
                record["engine"],
                record["cohort"],
                record["arm"],
                record["carryover"],
                name,
            )
            source_key = (
                record["engine"],
                record["cohort"],
                record["source_id"],
                record["arm"],
                record["carryover"],
                name,
            )
            totals[total_key][0] = float(totals[total_key][0]) + loss
            totals[total_key][1] = int(totals[total_key][1]) + 1
            sources[source_key][0] = float(sources[source_key][0]) + loss
            sources[source_key][1] = int(sources[source_key][1]) + 1
    return (
        {key: (float(value[0]), int(value[1])) for key, value in totals.items()},
        {key: (float(value[0]), int(value[1])) for key, value in sources.items()},
    )


def _select_baseline_from_losses(
    record: dict[str, Any],
    totals: dict[tuple[Any, ...], tuple[float, int]],
    sources: dict[tuple[Any, ...], tuple[float, int]],
) -> str:
    means: dict[str, float] = {}
    for name in ("basin", "distance", "pooled"):
        total_key = (
            record["engine"], record["cohort"], record["arm"], record["carryover"], name
        )
        source_key = (
            record["engine"],
            record["cohort"],
            record["source_id"],
            record["arm"],
            record["carryover"],
            name,
        )
        total_loss, total_count = totals.get(total_key, (0.0, 0))
        source_loss, source_count = sources.get(source_key, (0.0, 0))
        count = total_count - source_count
        means[name] = (total_loss - source_loss) / count if count else float("inf")
    if all(not np.isfinite(value) for value in means.values()):
        return "basin"
    return min(means, key=means.get)


def _crossfit_direction(
    records: list[dict[str, Any]],
    registry_contexts: RegistryContexts,
    mapping_half: str,
    spec: StudySpec,
) -> list[dict[str, Any]]:
    evaluation_half = "B" if mapping_half == "A" else "A"
    mapping_records = [record for record in records if record["half"] == mapping_half]
    evaluation_records = [record for record in records if record["half"] == evaluation_half]
    mapping_index = MappingIndex(mapping_records)
    temperatures = _fit_temperature(
        mapping_records, registry_contexts, spec
    )
    baseline_totals, baseline_sources = _mapping_baseline_losses(
        mapping_records,
        mapping_index,
        registry_contexts,
        temperatures,
        spec,
    )
    baseline_cache: dict[tuple[Any, ...], str] = {}
    output: list[dict[str, Any]] = []
    for record in evaluation_records:
        stratum = (record["engine"], record["cohort"])
        context = registry_contexts.get(
            record["source_id"], int(record["state_id"]), record["arm"]
        )
        categories = _local_categories(context)
        cell = _key(record)
        counts = mapping_index.cell.get(cell, collections.Counter())
        committor = _smoothed_probabilities(counts, categories, spec.dirichlet_alpha)
        selector_key = (
            mapping_half,
            record["engine"],
            record["cohort"],
            record["source_id"],
            record["arm"],
            record["carryover"],
        )
        if selector_key not in baseline_cache:
            baseline_cache[selector_key] = _select_baseline_from_losses(
                record, baseline_totals, baseline_sources
            )
        predictions = _baseline_predictions(
            record,
            mapping_index,
            registry_contexts,
            categories,
            temperatures[stratum],
            spec,
        )
        baseline_name = baseline_cache[selector_key]
        committor_loss = _loss(committor, record["destination"])
        baseline_loss = _loss(predictions[baseline_name], record["destination"])
        baseline = predictions[baseline_name]
        committor_label = max(categories, key=lambda category: committor[category])
        baseline_label = max(categories, key=lambda category: baseline[category])
        output.append(
            {
                **{name: record[name] for name in CELL_KEYS},
                "mapping_half": mapping_half,
                "destination": record["destination"],
                "committor_loss": committor_loss,
                "baseline_loss": baseline_loss,
                "gain": baseline_loss - committor_loss,
                "committor_probability": committor.get(record["destination"], 0.0),
                "baseline_probability": baseline.get(record["destination"], 0.0),
                "committor_brier": _brier(
                    committor, record["destination"], categories
                ),
                "baseline_brier": _brier(
                    baseline, record["destination"], categories
                ),
                "committor_confidence": committor[committor_label],
                "baseline_confidence": baseline[baseline_label],
                "committor_correct": committor_label == record["destination"],
                "baseline_correct": baseline_label == record["destination"],
                "category_count": len(categories),
                "baseline": baseline_name,
                "distance_temperature": temperatures[stratum],
            }
        )
    return output


def _hierarchical_probabilities(
    cell_counts: collections.Counter[str],
    source_prior: dict[str, float],
    categories: tuple[str, ...],
    alpha: float,
    kappa: float,
) -> dict[str, float]:
    """Dirichlet cell estimate shrunk toward a leave-state-out source prior."""

    count = sum(cell_counts.get(category, 0) for category in categories)
    denominator = count + alpha * len(categories) + kappa
    return {
        category: (
            cell_counts.get(category, 0)
            + alpha
            + kappa * source_prior.get(category, 0.0)
        )
        / denominator
        for category in categories
    }


def _fit_temperature_v2(
    mapping_records: list[dict[str, Any]],
    registry_contexts: RegistryContexts,
    spec: StudySpec,
) -> dict[tuple[str, str, str], float]:
    result: dict[tuple[str, str, str], float] = {}
    strata = sorted(
        {
            (item["engine"], item["cohort"], item["inheritance_mode"])
            for item in mapping_records
        }
    )
    for stratum in strata:
        relevant = [
            item
            for item in mapping_records
            if (
                item["engine"],
                item["cohort"],
                item["inheritance_mode"],
            )
            == stratum
        ]
        genes = spec.boolean.genes if stratum[0] == "boolean" else spec.wagner.genes
        best_temperature = spec.distance_temperatures[0]
        best_loss = float("inf")
        for temperature in spec.distance_temperatures:
            losses: list[float] = []
            for record in relevant:
                context = registry_contexts.get(
                    record["source_id"], int(record["state_id"]), record["arm"]
                )
                categories = _local_categories(context)
                probabilities = _distance_probabilities(
                    context,
                    categories,
                    genes,
                    temperature,
                    spec.dirichlet_alpha,
                )
                losses.append(_loss(probabilities, record["destination"]))
            mean_loss = float(np.mean(losses)) if losses else float("inf")
            if mean_loss < best_loss:
                best_loss = mean_loss
                best_temperature = temperature
        result[stratum] = float(best_temperature)
    return result


def _mapping_baseline_losses_v2(
    mapping_records: list[dict[str, Any]],
    mapping_index: V2MappingIndex,
    registry_contexts: RegistryContexts,
    temperatures: dict[tuple[str, str, str], float],
    spec: StudySpec,
) -> tuple[
    dict[tuple[Any, ...], tuple[float, int]],
    dict[tuple[Any, ...], tuple[float, int]],
]:
    totals: dict[tuple[Any, ...], list[float | int]] = collections.defaultdict(
        lambda: [0.0, 0]
    )
    sources: dict[tuple[Any, ...], list[float | int]] = collections.defaultdict(
        lambda: [0.0, 0]
    )
    for record in mapping_records:
        stratum = (
            record["engine"],
            record["cohort"],
            record["inheritance_mode"],
        )
        context = registry_contexts.get(
            record["source_id"], int(record["state_id"]), record["arm"]
        )
        predictions = _baseline_predictions(
            record,
            mapping_index,
            registry_contexts,
            _local_categories(context),
            temperatures[stratum],
            spec,
        )
        for name, probability in predictions.items():
            loss = _loss(probability, record["destination"])
            total_key = (
                record["engine"],
                record["cohort"],
                record["arm"],
                record["carryover"],
                record["inheritance_mode"],
                name,
            )
            source_key = (
                record["engine"],
                record["cohort"],
                record["source_id"],
                record["arm"],
                record["carryover"],
                record["inheritance_mode"],
                name,
            )
            totals[total_key][0] = float(totals[total_key][0]) + loss
            totals[total_key][1] = int(totals[total_key][1]) + 1
            sources[source_key][0] = float(sources[source_key][0]) + loss
            sources[source_key][1] = int(sources[source_key][1]) + 1
    return (
        {key: (float(value[0]), int(value[1])) for key, value in totals.items()},
        {key: (float(value[0]), int(value[1])) for key, value in sources.items()},
    )


def _select_baseline_from_losses_v2(
    record: dict[str, Any],
    totals: dict[tuple[Any, ...], tuple[float, int]],
    sources: dict[tuple[Any, ...], tuple[float, int]],
) -> str:
    means: dict[str, float] = {}
    for name in ("basin", "distance", "pooled"):
        total_key = (
            record["engine"],
            record["cohort"],
            record["arm"],
            record["carryover"],
            record["inheritance_mode"],
            name,
        )
        source_key = (
            record["engine"],
            record["cohort"],
            record["source_id"],
            record["arm"],
            record["carryover"],
            record["inheritance_mode"],
            name,
        )
        total_loss, total_count = totals.get(total_key, (0.0, 0))
        source_loss, source_count = sources.get(source_key, (0.0, 0))
        count = total_count - source_count
        means[name] = (total_loss - source_loss) / count if count else float("inf")
    if all(not np.isfinite(value) for value in means.values()):
        return "basin"
    return min(means, key=means.get)


def _tune_shrinkage_kappa(
    heldout_record: dict[str, Any],
    mapping_records: list[dict[str, Any]],
    registry_contexts: RegistryContexts,
    spec: StudySpec,
) -> float:
    """Choose kappa using only other rulebooks and mapping-half parity folds."""

    relevant = [
        record
        for record in mapping_records
        if record["engine"] == heldout_record["engine"]
        and record["cohort"] == heldout_record["cohort"]
        and record["source_id"] != heldout_record["source_id"]
        and record["arm"] == heldout_record["arm"]
        and float(record["carryover"]) == float(heldout_record["carryover"])
        and record["inheritance_mode"] == heldout_record["inheritance_mode"]
    ]
    if not relevant:
        return SHRINKAGE_KAPPAS[0]

    totals = {kappa: 0.0 for kappa in SHRINKAGE_KAPPAS}
    counts = {kappa: 0 for kappa in SHRINKAGE_KAPPAS}
    for validation_parity in (0, 1):
        training = [
            record
            for record in relevant
            if int(record["future_index"]) % 2 != validation_parity
        ]
        validation = [
            record
            for record in relevant
            if int(record["future_index"]) % 2 == validation_parity
        ]
        if not training or not validation:
            continue
        index = V2MappingIndex(training)
        for record in validation:
            context = registry_contexts.get(
                record["source_id"], int(record["state_id"]), record["arm"]
            )
            categories = _local_categories(context)
            cell_counts = index.cell.get(
                _key(record, V2_CELL_KEYS), collections.Counter()
            )
            source_prior = _smoothed_probabilities(
                index.pooled_counts(record), categories, spec.dirichlet_alpha
            )
            for kappa in SHRINKAGE_KAPPAS:
                probabilities = _hierarchical_probabilities(
                    cell_counts,
                    source_prior,
                    categories,
                    spec.dirichlet_alpha,
                    kappa,
                )
                totals[kappa] += _loss(probabilities, record["destination"])
                counts[kappa] += 1

    candidates = [kappa for kappa in SHRINKAGE_KAPPAS if counts[kappa]]
    if not candidates:
        return SHRINKAGE_KAPPAS[0]
    return min(candidates, key=lambda value: (totals[value] / counts[value], value))


def _crossfit_direction_v2(
    records: list[dict[str, Any]],
    registry_contexts: RegistryContexts,
    mapping_half: str,
    spec: StudySpec,
) -> list[dict[str, Any]]:
    evaluation_half = "B" if mapping_half == "A" else "A"
    mapping_records = [record for record in records if record["half"] == mapping_half]
    evaluation_records = [
        record for record in records if record["half"] == evaluation_half
    ]
    mapping_index = V2MappingIndex(mapping_records)
    temperatures = _fit_temperature_v2(mapping_records, registry_contexts, spec)
    baseline_totals, baseline_sources = _mapping_baseline_losses_v2(
        mapping_records,
        mapping_index,
        registry_contexts,
        temperatures,
        spec,
    )
    baseline_cache: dict[tuple[Any, ...], str] = {}
    kappa_cache: dict[tuple[Any, ...], float] = {}
    output: list[dict[str, Any]] = []
    for record in evaluation_records:
        stratum = (
            record["engine"],
            record["cohort"],
            record["inheritance_mode"],
        )
        context = registry_contexts.get(
            record["source_id"], int(record["state_id"]), record["arm"]
        )
        categories = _local_categories(context)
        counts = mapping_index.cell.get(
            _key(record, V2_CELL_KEYS), collections.Counter()
        )
        audit = _smoothed_probabilities(counts, categories, spec.dirichlet_alpha)
        source_prior = _smoothed_probabilities(
            mapping_index.pooled_counts(record), categories, spec.dirichlet_alpha
        )
        selector_key = (
            mapping_half,
            record["engine"],
            record["cohort"],
            record["source_id"],
            record["arm"],
            record["carryover"],
            record["inheritance_mode"],
        )
        if selector_key not in baseline_cache:
            baseline_cache[selector_key] = _select_baseline_from_losses_v2(
                record, baseline_totals, baseline_sources
            )
        if selector_key not in kappa_cache:
            kappa_cache[selector_key] = _tune_shrinkage_kappa(
                record, mapping_records, registry_contexts, spec
            )
        kappa = kappa_cache[selector_key]
        hierarchical = _hierarchical_probabilities(
            counts,
            source_prior,
            categories,
            spec.dirichlet_alpha,
            kappa,
        )
        predictions = _baseline_predictions(
            record,
            mapping_index,
            registry_contexts,
            categories,
            temperatures[stratum],
            spec,
        )
        baseline_name = baseline_cache[selector_key]
        baseline = predictions[baseline_name]
        audit_label = max(categories, key=lambda category: audit[category])
        hierarchical_label = max(
            categories, key=lambda category: hierarchical[category]
        )
        baseline_label = max(categories, key=lambda category: baseline[category])
        destination = record["destination"]
        baseline_loss = _loss(baseline, destination)
        output.append(
            {
                **{name: record[name] for name in V2_CELL_KEYS},
                "future_index": int(record["future_index"]),
                "mapping_half": mapping_half,
                "evaluation_half": evaluation_half,
                "destination": destination,
                "audit_committor_loss": _loss(audit, destination),
                "hierarchical_committor_loss": _loss(hierarchical, destination),
                "baseline_loss": baseline_loss,
                "audit_gain": baseline_loss - _loss(audit, destination),
                "hierarchical_gain": baseline_loss
                - _loss(hierarchical, destination),
                "audit_probability": audit.get(destination, 0.0),
                "hierarchical_probability": hierarchical.get(destination, 0.0),
                "baseline_probability": baseline.get(destination, 0.0),
                "audit_brier": _brier(audit, destination, categories),
                "hierarchical_brier": _brier(
                    hierarchical, destination, categories
                ),
                "baseline_brier": _brier(baseline, destination, categories),
                "audit_confidence": audit[audit_label],
                "hierarchical_confidence": hierarchical[hierarchical_label],
                "baseline_confidence": baseline[baseline_label],
                "audit_correct": audit_label == destination,
                "hierarchical_correct": hierarchical_label == destination,
                "baseline_correct": baseline_label == destination,
                "category_count": len(categories),
                "baseline": baseline_name,
                "distance_temperature": temperatures[stratum],
                "shrinkage_kappa": kappa,
            }
        )
    return output


def _bootstrap_interval(
    values: np.ndarray,
    repetitions: int,
    level: float,
    rng: np.random.Generator,
) -> tuple[float, float]:
    if values.size == 0:
        return float("nan"), float("nan")
    if values.size == 1:
        return float(values[0]), float(values[0])
    indices = rng.integers(0, values.size, size=(repetitions, values.size))
    means = np.mean(values[indices], axis=1)
    tail = (1.0 - level) / 2.0
    return float(np.quantile(means, tail)), float(np.quantile(means, 1.0 - tail))


def _js_reliability(
    records: list[dict[str, Any]],
    registry_contexts: RegistryContexts,
    alpha: float,
) -> dict[str, float]:
    groups = _group(records, CELL_KEYS)
    by_stratum: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    for key, cell_records in groups.items():
        engine, cohort = str(key[0]), str(key[1])
        context = registry_contexts.get(str(key[2]), int(key[3]), str(key[4]))
        categories = _local_categories(context)
        first = collections.Counter(
            item["destination"] for item in cell_records if item["half"] == "A"
        )
        second = collections.Counter(
            item["destination"] for item in cell_records if item["half"] == "B"
        )
        p = _smoothed_probabilities(first, categories, alpha)
        q = _smoothed_probabilities(second, categories, alpha)
        midpoint = {category: 0.5 * (p[category] + q[category]) for category in categories}
        js = 0.5 * sum(
            p[category] * math.log(p[category] / midpoint[category])
            + q[category] * math.log(q[category] / midpoint[category])
            for category in categories
        )
        by_stratum[(engine, cohort)].append(1.0 - js / math.log(2.0))
    return {
        f"{engine}.{cohort}": float(np.mean(values))
        for (engine, cohort), values in by_stratum.items()
    }


def _js_reliability_v2(
    records: list[dict[str, Any]],
    registry_contexts: RegistryContexts,
    alpha: float,
) -> dict[str, float]:
    groups = _group(records, V2_CELL_KEYS)
    by_stratum: dict[tuple[str, str, str], list[float]] = collections.defaultdict(
        list
    )
    for key, cell_records in groups.items():
        engine, cohort, mode = str(key[0]), str(key[1]), str(key[-1])
        context = registry_contexts.get(str(key[2]), int(key[3]), str(key[4]))
        categories = _local_categories(context)
        first = collections.Counter(
            item["destination"] for item in cell_records if item["half"] == "A"
        )
        second = collections.Counter(
            item["destination"] for item in cell_records if item["half"] == "B"
        )
        p = _smoothed_probabilities(first, categories, alpha)
        q = _smoothed_probabilities(second, categories, alpha)
        midpoint = {
            category: 0.5 * (p[category] + q[category])
            for category in categories
        }
        js = 0.5 * sum(
            p[category] * math.log(p[category] / midpoint[category])
            + q[category] * math.log(q[category] / midpoint[category])
            for category in categories
        )
        by_stratum[(engine, cohort, mode)].append(1.0 - js / math.log(2.0))
    return {
        f"{engine}.{cohort}.{mode}": float(np.mean(values))
        for (engine, cohort, mode), values in by_stratum.items()
    }


def _expected_calibration_error(
    records: list[dict[str, Any]],
    confidence_name: str,
    correct_name: str,
    bins: int = 10,
) -> float:
    if not records:
        return float("nan")
    grouped: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for record in records:
        confidence = float(record[confidence_name])
        grouped[min(int(confidence * bins), bins - 1)].append(record)
    total = len(records)
    return float(
        sum(
            len(values)
            / total
            * abs(
                float(np.mean([value[confidence_name] for value in values]))
                - float(np.mean([value[correct_name] for value in values]))
            )
            for values in grouped.values()
        )
    )


def _v2_primary(
    scored: list[dict[str, Any]], spec: StudySpec
) -> tuple[dict[str, Any], dict[str, Any]]:
    primary_records = [
        item
        for item in scored
        if item["arm"] == "acute_mismatch" and float(item["carryover"]) == 1.0
    ]
    primary: dict[str, Any] = {}
    source_gain_by_estimator: dict[
        str, dict[tuple[Any, ...], float]
    ] = {}
    for estimator in ("audit", "hierarchical"):
        gain_name = f"{estimator}_gain"
        brier_name = f"{estimator}_brier"
        source_groups = _group(
            primary_records,
            ("engine", "cohort", "source_id", "inheritance_mode"),
        )
        source_gains = {
            key: float(np.mean([item[gain_name] for item in values]))
            for key, values in source_groups.items()
        }
        source_gain_by_estimator[estimator] = source_gains
        strata = sorted(
            {
                (str(key[0]), str(key[1]), str(key[3]))
                for key in source_gains
            }
        )
        for engine, cohort, mode in strata:
            values = np.asarray(
                [
                    gain
                    for (value_engine, value_cohort, _, value_mode), gain in source_gains.items()
                    if value_engine == engine
                    and value_cohort == cohort
                    and value_mode == mode
                ],
                dtype=float,
            )
            interval = _bootstrap_interval(
                values,
                spec.bootstrap_repetitions,
                spec.pilot_interval,
                rng_for(
                    spec.master_seed,
                    "analysis",
                    "v2-primary-bootstrap",
                    engine,
                    cohort,
                    mode,
                    estimator,
                ),
            )
            relevant = [
                item
                for item in primary_records
                if item["engine"] == engine
                and item["cohort"] == cohort
                and item["inheritance_mode"] == mode
            ]
            baseline_counts = collections.Counter(item["baseline"] for item in relevant)
            primary[f"{engine}.{cohort}.{mode}.{estimator}"] = {
                "rulebooks": int(values.size),
                "mean_log_loss_gain": float(np.mean(values))
                if values.size
                else float("nan"),
                "interval_level": spec.pilot_interval,
                "interval": list(interval),
                "mean_brier_gain": float(
                    np.mean(
                        [item["baseline_brier"] - item[brier_name] for item in relevant]
                    )
                ),
                "committor_accuracy": float(
                    np.mean([item[f"{estimator}_correct"] for item in relevant])
                ),
                "baseline_accuracy": float(
                    np.mean([item["baseline_correct"] for item in relevant])
                ),
                "committor_ece": _expected_calibration_error(
                    relevant,
                    f"{estimator}_confidence",
                    f"{estimator}_correct",
                ),
                "baseline_ece": _expected_calibration_error(
                    relevant, "baseline_confidence", "baseline_correct"
                ),
                "baseline_counts": dict(sorted(baseline_counts.items())),
                "shrinkage_counts": dict(
                    sorted(
                        collections.Counter(
                            f"{float(item['shrinkage_kappa']):g}"
                            for item in relevant
                        ).items()
                    )
                )
                if estimator == "hierarchical"
                else {},
                "point_gate": False,
                "interval_gate": False,
            }

    history: dict[str, Any] = {}
    for estimator, source_gains in source_gain_by_estimator.items():
        strata = sorted(
            {(str(key[0]), str(key[1])) for key in source_gains}
        )
        for engine, cohort in strata:
            sources = sorted(
                {
                    str(key[2])
                    for key in source_gains
                    if key[0] == engine and key[1] == cohort
                }
            )
            contrasts = []
            for source_id in sources:
                self_key = (engine, cohort, source_id, "self")
                donor_key = (engine, cohort, source_id, "donor_shuffled")
                if self_key in source_gains and donor_key in source_gains:
                    contrasts.append(source_gains[self_key] - source_gains[donor_key])
            values = np.asarray(contrasts, dtype=float)
            interval = _bootstrap_interval(
                values,
                spec.bootstrap_repetitions,
                spec.pilot_interval,
                rng_for(
                    spec.master_seed,
                    "analysis",
                    "v2-history-bootstrap",
                    engine,
                    cohort,
                    estimator,
                ),
            )
            history[f"{engine}.{cohort}.{estimator}"] = {
                "rulebooks": int(values.size),
                "mean_self_minus_donor_gain": float(np.mean(values))
                if values.size
                else float("nan"),
                "interval_level": spec.pilot_interval,
                "interval": list(interval),
            }
    return primary, history


def _v2_control_contrasts(
    records: list[dict[str, Any]], spec: StudySpec
) -> dict[str, Any]:
    relevant = [record for record in records if float(record["carryover"]) == 1.0]
    grouped = _group(
        relevant,
        ("engine", "cohort", "source_id", "inheritance_mode", "arm"),
    )
    rates = {
        key: float(np.mean([record["strict_event"] for record in values]))
        for key, values in grouped.items()
    }
    output: dict[str, Any] = {}
    strata = sorted(
        {(str(key[0]), str(key[1]), str(key[3])) for key in rates}
    )
    comparisons = (
        ("natural", "acute-minus-natural"),
        ("target_aligned_own_anchor", "acute-minus-own-anchor"),
    )
    for engine, cohort, mode in strata:
        sources = sorted(
            {
                str(key[2])
                for key in rates
                if key[0] == engine and key[1] == cohort and key[3] == mode
            }
        )
        for control_arm, label in comparisons:
            contrasts = []
            for source_id in sources:
                acute_key = (engine, cohort, source_id, mode, "acute_mismatch")
                control_key = (engine, cohort, source_id, mode, control_arm)
                if acute_key in rates and control_key in rates:
                    contrasts.append(rates[acute_key] - rates[control_key])
            values = np.asarray(contrasts, dtype=float)
            interval = _bootstrap_interval(
                values,
                spec.bootstrap_repetitions,
                spec.pilot_interval,
                rng_for(
                    spec.master_seed,
                    "analysis",
                    "v2-control-bootstrap",
                    engine,
                    cohort,
                    mode,
                    label,
                ),
            )
            output[f"{engine}.{cohort}.{mode}.{label}"] = {
                "rulebooks": int(values.size),
                "mean_strict_rate_difference": float(np.mean(values))
                if values.size
                else float("nan"),
                "interval_level": spec.pilot_interval,
                "interval": list(interval),
            }
    return output


def _analyze_v2_records(
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    spec: StudySpec,
) -> dict[str, Any]:
    for record in records:
        if record.get("inheritance_mode") not in spec.inheritance_modes:
            raise ValueError("missing or invalid v2 inheritance mode")
    contexts = RegistryContexts(registry)
    scored = _crossfit_direction_v2(records, contexts, "A", spec)
    scored.extend(_crossfit_direction_v2(records, contexts, "B", spec))
    primary, history = _v2_primary(scored, spec)

    secondary_groups = _group(
        records,
        ("engine", "cohort", "inheritance_mode", "arm", "carryover"),
    )
    secondary: dict[str, Any] = {}
    for key, values in sorted(secondary_groups.items()):
        label = (
            f"{key[0]}.{key[1]}.{key[2]}.{key[3]}.lambda-{float(key[4]):g}"
        )
        secondary[label] = {
            "futures": len(values),
            "strict_rate": float(np.mean([item["strict_event"] for item in values])),
            "active_capture_rate": float(
                np.mean([item["active_capture"] for item in values])
            ),
            "old_return_rate": float(
                np.mean([item["old_return"] for item in values])
            ),
            "mean_nonconvergent_cycles": float(
                np.mean([item["nonconvergent_cycles"] for item in values])
            ),
        }
    return {
        "format": analysis_format(spec.protocol_format),
        "protocol_format": spec.protocol_format,
        "cohort_id": spec.cohort_id,
        "futures": len(records),
        "primary_endpoint": (
            "acute-mismatch audit and hierarchical destination committors at "
            "lambda=1, separated by inheritance mode"
        ),
        "primary": primary,
        "history_contrast": history,
        "control_contrasts": _v2_control_contrasts(records, spec),
        "secondary": secondary,
        "split_half_destination_reliability": _js_reliability_v2(
            records, contexts, spec.dirichlet_alpha
        ),
        "shrinkage": {
            "kappa_grid": list(SHRINKAGE_KAPPAS),
            "selection": "mapping-half parity cross-fit excluding held-out rulebook",
            "evaluation_half_used_for_selection": False,
        },
        "eligible_for_advancement_gate": False,
        "advance_to_confirmation": False,
        "gate_note": (
            "Stage A is a design-validation cohort and cannot pass a scientific "
            "advancement gate. Its outcome signs cannot determine Stage B readiness."
            if spec.mode == "stage-a"
            else "The v2 quick prototype is an engineering diagnostic and cannot "
            "pass a scientific advancement gate."
        ),
    }


def analyze_records(
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    spec: StudySpec,
) -> dict[str, Any]:
    if not records:
        raise ValueError("cannot analyze an empty campaign")
    if spec.is_v2:
        return _analyze_v2_records(records, registry, spec)
    contexts = RegistryContexts(registry)
    scored = _crossfit_direction(records, contexts, "A", spec)
    scored.extend(_crossfit_direction(records, contexts, "B", spec))

    primary_records = [
        item
        for item in scored
        if item["arm"] == "acute_mismatch" and float(item["carryover"]) == 1.0
    ]
    source_groups = _group(primary_records, ("engine", "cohort", "source_id"))
    source_gains = {
        key: float(np.mean([item["gain"] for item in values]))
        for key, values in source_groups.items()
    }
    primary: dict[str, Any] = {}
    for engine, cohort in sorted(
        {(str(key[0]), str(key[1])) for key in source_gains}
    ):
        values = np.asarray(
            [
                gain
                for (value_engine, value_cohort, _), gain in source_gains.items()
                if value_engine == engine and value_cohort == cohort
            ],
            dtype=float,
        )
        interval = _bootstrap_interval(
            values,
            spec.bootstrap_repetitions,
            spec.pilot_interval,
            rng_for(spec.master_seed, "analysis", engine, cohort, "primary-bootstrap"),
        )
        relevant = [
            item
            for item in primary_records
            if item["engine"] == engine and item["cohort"] == cohort
        ]
        baseline_counts = collections.Counter(item["baseline"] for item in relevant)
        primary[f"{engine}.{cohort}"] = {
            "rulebooks": int(values.size),
            "mean_log_loss_gain": float(np.mean(values)) if values.size else float("nan"),
            "interval_level": spec.pilot_interval,
            "interval": list(interval),
            "baseline_counts": dict(sorted(baseline_counts.items())),
            "point_gate": bool(
                values.size and float(np.mean(values)) > spec.advancement_log_loss_gain
            ),
            "interval_gate": bool(values.size and interval[0] > 0),
        }

    secondary_groups = _group(records, ("engine", "cohort", "arm", "carryover"))
    secondary: dict[str, Any] = {}
    for key, values in sorted(secondary_groups.items()):
        label = f"{key[0]}.{key[1]}.{key[2]}.lambda-{float(key[3]):g}"
        secondary[label] = {
            "futures": len(values),
            "strict_rate": float(np.mean([item["strict_event"] for item in values])),
            "active_capture_rate": float(
                np.mean([item["active_capture"] for item in values])
            ),
            "old_return_rate": float(np.mean([item["old_return"] for item in values])),
            "mean_nonconvergent_cycles": float(
                np.mean([item["nonconvergent_cycles"] for item in values])
            ),
        }

    sampled_cells = [f"{engine}.sampled" for engine in spec.engines]
    eligible_for_advancement = spec.mode == "pilot" and all(
        cell in primary for cell in sampled_cells
    )
    advancement = bool(
        eligible_for_advancement
        and all(
            primary[cell]["point_gate"] and primary[cell]["interval_gate"]
            for cell in sampled_cells
        )
    )
    return {
        "format": ANALYSIS_FORMAT,
        "protocol_format": spec.protocol_format,
        "cohort_id": spec.cohort_id,
        "futures": len(records),
        "primary_endpoint": "acute-mismatch destination committor at lambda=1",
        "primary": primary,
        "secondary": secondary,
        "split_half_destination_reliability": _js_reliability(
            records, contexts, spec.dirichlet_alpha
        ),
        "eligible_for_advancement_gate": eligible_for_advancement,
        "advance_to_confirmation": advancement,
        "gate_note": (
            "Quick runs are engineering checks and cannot pass the scientific gate."
            if spec.mode != "pilot"
            else "Evolved strata are reported separately and cannot rescue sampled-engine failure."
        ),
    }
