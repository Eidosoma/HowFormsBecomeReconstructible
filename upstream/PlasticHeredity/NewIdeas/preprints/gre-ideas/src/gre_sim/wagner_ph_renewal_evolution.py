"""Paired renewal evolution and untouched mutation-neighborhood audit."""

from __future__ import annotations

import collections
import concurrent.futures
import multiprocessing
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    read_jsonl_gz,
    runtime_manifest,
    verify_checksums,
    write_checksums,
    write_json,
    write_jsonl_gz,
)
from .local_ph_config import LocalCarrierGenome, LocalConditionSpec, LocalStudySpec
from .local_ph_study import simulate_local_source
from .rng import rng_for
from .wagner import WagnerRulebook
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_bridge_evolution import (
    _deserialize_genotype,
    _mutate_genotype,
    _named_carrier,
    _sample_task,
    _serialize_genotype,
    _source,
)
from .wagner_ph_renewal_analysis import analyze_renewal_audit, render_audit_report
from .wagner_ph_renewal_config import (
    RENEWAL_AUDIT_FORMAT,
    RENEWAL_EVOLUTION_FORMAT,
    RENEWAL_TREATMENTS,
    MutationNeighborhoodSpec,
    RenewalEvolutionSpec,
)


EVOLUTION_REGISTRATION_FORMAT = "gre-wagner-ph-renewal-evolution-registration-v1"
EVOLUTION_MANIFEST_FORMAT = "gre-wagner-ph-renewal-evolution-manifest-v1"
AUDIT_REGISTRATION_FORMAT = "gre-wagner-ph-renewal-audit-registration-v1"
AUDIT_MANIFEST_FORMAT = "gre-wagner-ph-renewal-audit-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def renewal_resource_cost(
    carrier: LocalCarrierGenome, spec: RenewalEvolutionSpec, treatment: str
) -> float:
    """Frozen target-blind carrier cost with one explicitly doubled treatment."""

    base = float(
        spec.capacity_cost * carrier.k / spec.genes
        + spec.coupling_cost * carrier.coupling
        + spec.writing_cost * carrier.write_rate
    )
    multiplier = spec.high_cost_multiplier if treatment == "renewal_high_cost" else 1.0
    return multiplier * base


def _candidate(carrier: LocalCarrierGenome) -> LocalCarrierGenome:
    return replace(carrier, name="candidate")


def _noise_tuple(spec: RenewalEvolutionSpec) -> tuple[Any, ...]:
    values = [spec.selected_noise]
    if spec.harsher_noise.name != spec.selected_noise.name:
        values.append(spec.harsher_noise)
    return tuple(values)


def _conditions(panel: str, spec: RenewalEvolutionSpec) -> tuple[LocalConditionSpec, ...]:
    selected = spec.selected_noise.name
    harsher = spec.harsher_noise.name
    base = [
        LocalConditionSpec("candidate.intact", "candidate", "intact", selected, True),
        LocalConditionSpec("candidate.renewal-off", "candidate", "renewal_off", selected),
        LocalConditionSpec("zero", None, "zero", selected),
    ]
    if panel in {"renewal-training", "common-audit", "causal-audit"}:
        base.extend(
            (
                LocalConditionSpec("candidate.harsher", "candidate", "intact", harsher),
                LocalConditionSpec("zero.harsher", None, "zero", harsher),
            )
        )
    if panel == "causal-audit":
        base.extend(
            (
                LocalConditionSpec(
                    "candidate.founder-write-off", "candidate", "founder_write_off", selected
                ),
                LocalConditionSpec("candidate.reader-off", "candidate", "reader_off", selected),
                LocalConditionSpec("candidate.shuffle", "candidate", "shuffle", selected),
                LocalConditionSpec("candidate.erase-g2", "candidate", "erase_g2", selected),
                LocalConditionSpec("candidate.reverse-g2", "candidate", "reverse_g2", selected),
                LocalConditionSpec(
                    "candidate.erase-g2-rescue-g3",
                    "candidate",
                    "erase_g2_rescue_g3",
                    selected,
                ),
                LocalConditionSpec("perfect-latch", None, "perfect_latch", selected),
            )
        )
    if panel not in {
        "minimal",
        "renewal-training",
        "common-audit",
        "causal-audit",
    }:
        raise ValueError(f"unknown renewal assay panel: {panel}")
    return tuple(base)


def _assay_genotype(
    rulebook: WagnerRulebook,
    carrier: LocalCarrierGenome,
    task: dict[str, Any],
    spec: RenewalEvolutionSpec,
    source_id: str,
    label: str,
    replicates: int,
    checkpoints: tuple[int, ...],
    challenges: tuple[str, ...],
    panel: str,
    *,
    master_seed: str | None = None,
) -> dict[str, Any]:
    """Run one target-blind genotype on an explicitly named common assay panel."""

    conditions = _conditions(panel, spec)
    study = LocalStudySpec(
        f"{spec.cohort_id}.{label}",
        f"renewal-assay.{label}",
        master_seed or spec.master_seed,
        1,
        (_candidate(carrier),),
        _noise_tuple(spec),
        conditions,
        checkpoint_generations=checkpoints,
        challenges=challenges,
        futures_per_history=replicates,
        generation_cycles=spec.generation_cycles,
        horizon=spec.horizon,
        strict_run=spec.strict_run,
        stable_run=spec.stable_run,
        expression_flip_probability=spec.expression_flip_probability,
        bootstrap_repetitions=64,
        exploratory=True,
    )
    study.validate()
    rows = simulate_local_source(_source(task, rulebook, source_id), study.to_dict())
    counts: dict[tuple[str, int, str], dict[str, float]] = collections.defaultdict(
        lambda: {"correct": 0.0, "wrong": 0.0, "acquired": 0.0, "n": 0.0}
    )
    for record in rows:
        key = (str(record["condition"]), int(record["generation"]), str(record["challenge"]))
        counts[key]["correct"] += float(record["correct_hold8"])
        counts[key]["wrong"] += float(record["wrong_hold8"])
        counts[key]["acquired"] += float(record["acquired"])
        counts[key]["n"] += 1.0
    cells: dict[str, Any] = {}
    for condition in (value.name for value in conditions):
        generations: dict[str, Any] = {}
        for generation in checkpoints:
            events: dict[str, Any] = {}
            for challenge in challenges:
                value = counts[(condition, generation, challenge)]
                denominator = value["n"]
                events[challenge] = {
                    "correct_rate": value["correct"] / denominator if denominator else None,
                    "wrong_rate": value["wrong"] / denominator if denominator else None,
                    "acquisition_rate": value["acquired"] / denominator
                    if denominator
                    else None,
                }
            generations[str(generation)] = events
        cells[condition] = generations
    for condition, generations in cells.items():
        if condition in {"zero", "zero.harsher"}:
            continue
        baseline = "zero.harsher" if condition == "candidate.harsher" else "zero"
        for generation, events in generations.items():
            for challenge, value in events.items():
                zero = cells[baseline][generation][challenge]
                value["risk_gain"] = float(value["correct_rate"]) - float(
                    zero["correct_rate"]
                )
    return {
        "panel": panel,
        "cells": cells,
        "record_count": len(rows),
        "digest": canonical_digest(cells),
    }


def _risk(
    assay: dict[str, Any],
    condition: str,
    generation: int,
    field: str = "risk_gain",
    challenge: str = "forced_break",
) -> float:
    return float(assay["cells"][condition][str(generation)][challenge][field])


def _training_score(
    genotype: tuple[WagnerRulebook, LocalCarrierGenome],
    task: dict[str, Any],
    spec: RenewalEvolutionSpec,
    treatment: str,
    population_index: int,
    generation: int,
) -> dict[str, float]:
    cost = renewal_resource_cost(genotype[1], spec, treatment)
    if treatment == "neutral_drift":
        return {
            "selected_gain": 0.0,
            "harsher_gain": 0.0,
            "renewal_contrast": 0.0,
            "resource_cost": cost,
            "fitness": 0.0,
        }
    panel = (
        "renewal-training"
        if treatment.startswith("renewal_")
        else "minimal"
    )
    endpoint = 0 if treatment == "acute_standard_cost" else 8
    checkpoints = (0,) if endpoint == 0 else (0, 8)
    source_id = f"training.population-{population_index:03d}.generation-{generation:03d}"
    assay = _assay_genotype(
        *genotype,
        task,
        spec,
        source_id,
        source_id,
        spec.training_replicates,
        checkpoints,
        ("forced_break",),
        panel,
    )
    selected = _risk(assay, "candidate.intact", endpoint)
    harsher = (
        _risk(assay, "candidate.harsher", 8)
        if treatment.startswith("renewal_")
        else 0.0
    )
    renewal = (
        _risk(assay, "candidate.intact", 8, "correct_rate")
        - _risk(assay, "candidate.renewal-off", 8, "correct_rate")
        if treatment.startswith("renewal_")
        else 0.0
    )
    phenotype = (
        0.50 * selected + 0.25 * harsher + 0.25 * renewal
        if treatment.startswith("renewal_")
        else selected
    )
    return {
        "selected_gain": selected,
        "harsher_gain": harsher,
        "renewal_contrast": renewal,
        "resource_cost": cost,
        "fitness": phenotype - cost,
    }


def _constrain_genotype(
    genotype: tuple[WagnerRulebook, LocalCarrierGenome],
    spec: RenewalEvolutionSpec,
) -> tuple[WagnerRulebook, LocalCarrierGenome]:
    carrier = genotype[1]
    if carrier.k <= spec.hard_capacity and carrier.topology != "all":
        return genotype
    payload = {
        "write_rate": carrier.write_rate,
        "decay": carrier.decay,
        "coupling": carrier.coupling,
        "hysteresis": carrier.hysteresis,
        "topology": "outgoing",
        "k": min(carrier.k, spec.hard_capacity),
    }
    return genotype[0], _named_carrier(payload)


def _mutate_for_treatment(
    left: tuple[WagnerRulebook, LocalCarrierGenome],
    right: tuple[WagnerRulebook, LocalCarrierGenome],
    random: np.random.Generator,
    treatment: str,
    spec: RenewalEvolutionSpec,
) -> tuple[WagnerRulebook, LocalCarrierGenome]:
    result = _mutate_genotype(left, right, random)
    return (
        _constrain_genotype(result, spec)
        if treatment == "renewal_k5_feasibility"
        else result
    )


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(args: tuple[dict[str, Any], str, int, str, str]) -> dict[str, Any]:
    spec_value, treatment, population_index, output_text, protocol_digest = args
    spec = RenewalEvolutionSpec.from_dict(spec_value)
    population_id = f"{treatment}.population-{population_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"renewal evolution registration differs: {final_path}")
    checkpoint_path = output / f"{population_id}.checkpoint.json"
    task = _sample_task(spec, population_index)
    if checkpoint_path.is_file():
        checkpoint = read_json(checkpoint_path)
        if checkpoint.get("protocol_digest") != protocol_digest:
            raise ValueError("renewal evolution checkpoint protocol differs")
        population = [_deserialize_genotype(value) for value in checkpoint["population"]]
        lineage_ids = [str(value) for value in checkpoint["lineage_ids"]]
        scores = [{key: float(item[key]) for key in item} for item in checkpoint["scores"]]
        ancestry = list(checkpoint["ancestry"])
        trace = list(checkpoint["trace"])
        start_generation = int(checkpoint["generation"]) + 1
    else:
        founder = (WagnerRulebook.from_dict(task["founder"]), spec.initial_carrier)
        if treatment == "renewal_k5_feasibility":
            founder = _constrain_genotype(founder, spec)
        population = [founder]
        for index in range(1, spec.population_size):
            random = rng_for(
                spec.master_seed, "renewal-evolution-initial", treatment, population_index, index
            )
            population.append(
                _mutate_for_treatment(founder, founder, random, treatment, spec)
            )
        scores = [
            _training_score(value, task, spec, treatment, population_index, 0)
            for value in population
        ]
        lineage_ids = [
            canonical_digest((population_id, 0, index, value[0].to_dict(), value[1].to_dict()))[:24]
            for index, value in enumerate(population)
        ]
        ancestry = [
            {
                "generation": 0,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        "parent_ids": [],
                        **_serialize_genotype(*value),
                        "training_score": scores[index],
                    }
                    for index, value in enumerate(population)
                ],
            }
        ]
        trace = []
        start_generation = 1
    if not trace:
        trace.append(
            {
                "generation": 0,
                "mean_fitness": float(np.mean([value["fitness"] for value in scores])),
                "best_fitness": float(np.max([value["fitness"] for value in scores])),
                "mean_renewal_contrast": float(
                    np.mean([value["renewal_contrast"] for value in scores])
                ),
                "mean_capacity": float(np.mean([value[1].k for value in population])),
            }
        )
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(
            spec.master_seed,
            "renewal-evolution-generation",
            treatment,
            population_index,
            generation,
        )
        following: list[tuple[WagnerRulebook, LocalCarrierGenome]] = []
        parents: list[tuple[str, ...]] = []
        if treatment != "neutral_drift":
            elites = sorted(
                range(len(population)), key=lambda index: (-fitness[index], index)
            )[: spec.elite_count]
            for index in elites:
                following.append(population[index])
                parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            if treatment == "neutral_drift":
                left = int(random.integers(len(population)))
                right = int(random.integers(len(population)))
            else:
                left = _tournament(fitness, random, spec.tournament_size)
                right = _tournament(fitness, random, spec.tournament_size)
            following.append(
                _mutate_for_treatment(
                    population[left], population[right], random, treatment, spec
                )
            )
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [
            _training_score(value, task, spec, treatment, population_index, generation)
            for value in population
        ]
        lineage_ids = [
            canonical_digest(
                (population_id, generation, index, value[0].to_dict(), value[1].to_dict())
            )[:24]
            for index, value in enumerate(population)
        ]
        ancestry.append(
            {
                "generation": generation,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        "parent_ids": list(parents[index]),
                        **_serialize_genotype(*value),
                        "training_score": scores[index],
                    }
                    for index, value in enumerate(population)
                ],
            }
        )
        trace.append(
            {
                "generation": generation,
                "mean_fitness": float(np.mean([value["fitness"] for value in scores])),
                "best_fitness": float(np.max([value["fitness"] for value in scores])),
                "mean_renewal_contrast": float(
                    np.mean([value["renewal_contrast"] for value in scores])
                ),
                "mean_capacity": float(np.mean([value[1].k for value in population])),
            }
        )
        _atomic_json(
            checkpoint_path,
            {
                "format": "gre-wagner-ph-renewal-evolution-checkpoint-v1",
                "protocol_digest": protocol_digest,
                "generation": generation,
                "population": [_serialize_genotype(*value) for value in population],
                "lineage_ids": lineage_ids,
                "scores": scores,
                "ancestry": ancestry,
                "trace": trace,
            },
        )
    selected_index = (
        0
        if treatment == "neutral_drift"
        else int(np.argmax([value["fitness"] for value in scores]))
    )
    founder = (WagnerRulebook.from_dict(task["founder"]), spec.initial_carrier)
    if treatment == "renewal_k5_feasibility":
        founder = _constrain_genotype(founder, spec)
    result = {
        "format": RENEWAL_EVOLUTION_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "population_index": population_index,
        "treatment": treatment,
        "task": task,
        "task_is_frozen_across_treatments": True,
        "selection_uses_target_label_inside_carrier": False,
        "common_training_stream_pattern": (
            f"training.population-{population_index:03d}.generation-GGG"
        ),
        "hard_k5_constraint": treatment == "renewal_k5_feasibility",
        "founder": _serialize_genotype(*founder),
        "selected": _serialize_genotype(*population[selected_index]),
        "selected_training_score": scores[selected_index],
        "final_population": [
            {**_serialize_genotype(*value), "training_score": scores[index]}
            for index, value in enumerate(population)
        ],
        "trace": trace,
        "ancestry": ancestry,
    }
    result["result_digest"] = canonical_digest(
        {
            "selected": result["selected"],
            "score": result["selected_training_score"],
            "trace": result["trace"],
        }
    )
    _atomic_json(final_path, result)
    if checkpoint_path.is_file():
        checkpoint_path.unlink()
    return result


def analyze_training_evolution(
    results: list[dict[str, Any]], spec: RenewalEvolutionSpec
) -> dict[str, Any]:
    treatments: dict[str, Any] = {}
    for treatment in spec.treatments:
        values = [value for value in results if value["treatment"] == treatment]
        treatments[treatment] = {
            "selected_training_fitness": _interval(
                (float(value["selected_training_score"]["fitness"]) for value in values),
                spec.master_seed,
                f"renewal-training.{treatment}.fitness",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "selected_training_renewal_contrast": _interval(
                (
                    float(value["selected_training_score"]["renewal_contrast"])
                    for value in values
                ),
                spec.master_seed,
                f"renewal-training.{treatment}.renewal",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "median_selected_capacity": float(
                np.median([int(value["selected"]["carrier"]["k"]) for value in values])
            )
            if values
            else None,
        }
    return {
        "format": "gre-wagner-ph-renewal-evolution-analysis-v1",
        "population_count": len(results),
        "selection_data_are_not_heldout_evidence": True,
        "carrier_target_access": False,
        "paired_task_indices": all(
            len(
                {
                    canonical_digest(value["task"])
                    for value in results
                    if int(value["population_index"]) == index
                }
            )
            == 1
            for index in range(spec.populations_per_treatment)
        ),
        "treatments": treatments,
    }


def run_renewal_evolution(
    spec: RenewalEvolutionSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 4:
        raise ValueError("renewal evolution permits one to four workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_renewal_evolution(destination)
        return destination
    started = time.monotonic()
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": EVOLUTION_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
        "carrier_receives_target_label": False,
        "tasks_are_paired_by_population_index": True,
        "assay_random_streams_are_common_by_population_and_generation": True,
        "selection_and_heldout_data_are_separate": True,
        "hard_k5_arm_is_engineering_feasibility_only": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(
        read_json(registration_path)
    ) != canonical_digest(registration):
        raise ValueError("existing renewal evolution registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    tasks = [
        (spec.to_dict(), treatment, index, str(populations), digest)
        for treatment in spec.treatments
        for index in range(spec.populations_per_treatment)
    ]
    results: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, tasks)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        iterator = executor.map(_population_task, tasks)
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-ph-renewal-evolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"renewal evolution {index}/{len(tasks)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    analysis = analyze_training_evolution(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": EVOLUTION_MANIFEST_FORMAT,
            "protocol_digest": digest,
            "population_count": len(results),
            "expected_population_count": len(tasks),
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_renewal_evolution(destination)
    return destination


def verify_renewal_evolution(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != EVOLUTION_REGISTRATION_FORMAT:
        raise ValueError("renewal evolution registration format mismatch")
    if manifest.get("format") != EVOLUTION_MANIFEST_FORMAT:
        raise ValueError("renewal evolution manifest format mismatch")
    spec = RenewalEvolutionSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("renewal evolution protocol digest mismatch")
    if int(manifest["population_count"]) != spec.population_count:
        raise ValueError("renewal evolution population count mismatch")
    files = [
        path
        for path in (directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    ]
    if len(files) != spec.population_count:
        raise ValueError("renewal evolution population file count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"renewal evolution population digest mismatch: {path.name}")
        if value["treatment"] == "renewal_k5_feasibility":
            if any(
                int(item["carrier"]["k"]) > spec.hard_capacity
                for item in value["final_population"]
            ):
                raise ValueError("hard-k5 treatment contains an oversized carrier")
        expected_result_digest = canonical_digest(
            {
                "selected": value["selected"],
                "score": value["selected_training_score"],
                "trace": value["trace"],
            }
        )
        if value.get("result_digest") != expected_result_digest:
            raise ValueError(f"renewal evolution result digest mismatch: {path.name}")
    return {"verified": True, "populations": spec.population_count, "checksums": len(checksums)}


def replay_renewal_population(directory: Path, population_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    spec = RenewalEvolutionSpec.from_dict(registration["protocol"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    selected = _deserialize_genotype(archived["selected"])
    score = _training_score(
        selected,
        archived["task"],
        spec,
        str(archived["treatment"]),
        int(archived["population_index"]),
        spec.generations,
    )
    return {
        "population_id": population_id,
        "matches": canonical_digest(score)
        == canonical_digest(archived["selected_training_score"]),
        "archived_score": archived["selected_training_score"],
        "replayed_score": score,
    }


def _heldout_metrics(
    selected: dict[str, Any], founder: dict[str, Any]
) -> dict[str, float]:
    return {
        "selected_g8": _risk(selected, "candidate.intact", 8),
        "selected_g12": _risk(selected, "candidate.intact", 12),
        "selected_g16": _risk(selected, "candidate.intact", 16),
        "harsher_g8": _risk(selected, "candidate.harsher", 8),
        "renewal_contrast_g8": _risk(
            selected, "candidate.intact", 8, "correct_rate"
        )
        - _risk(selected, "candidate.renewal-off", 8, "correct_rate"),
        "founder_g8": _risk(founder, "candidate.intact", 8),
    }


def _quantile_parent_indices(population: list[dict[str, Any]], count: int) -> list[int]:
    ordered = sorted(
        range(len(population)),
        key=lambda index: (
            float(population[index]["training_score"]["fitness"]),
            str(population[index]["genotype_id"]),
        ),
    )
    positions = np.rint(np.linspace(0, len(ordered) - 1, count)).astype(int)
    return [ordered[int(position)] for position in positions]


def _compute_audit_population(
    archived: dict[str, Any],
    evolution_spec: RenewalEvolutionSpec,
    audit_spec: MutationNeighborhoodSpec,
) -> dict[str, Any]:
    treatment = str(archived["treatment"])
    population_index = int(archived["population_index"])
    selected = _deserialize_genotype(archived["selected"])
    founder = _deserialize_genotype(archived["founder"])
    source_id = f"heldout.population-{population_index:03d}"
    full_causal = treatment in {"renewal_standard_cost", "renewal_high_cost"}
    selected_assay = _assay_genotype(
        *selected,
        archived["task"],
        evolution_spec,
        source_id,
        source_id,
        audit_spec.futures_per_history,
        audit_spec.checkpoint_generations,
        audit_spec.challenges,
        "causal-audit" if full_causal else "common-audit",
        master_seed=audit_spec.master_seed,
    )
    founder_assay = _assay_genotype(
        *founder,
        archived["task"],
        evolution_spec,
        source_id,
        source_id,
        audit_spec.futures_per_history,
        audit_spec.checkpoint_generations,
        audit_spec.challenges,
        "common-audit",
        master_seed=audit_spec.master_seed,
    )
    mutation_rows: list[dict[str, Any]] = []
    if treatment in RENEWAL_TREATMENTS[:3]:
        parent_indices = _quantile_parent_indices(
            archived["final_population"], audit_spec.parents_per_population
        )
        for parent_rank, parent_index in enumerate(parent_indices):
            parent_item = archived["final_population"][parent_index]
            parent = _deserialize_genotype(parent_item)
            mutation_source = f"mutation.population-{population_index:03d}.parent-{parent_rank:02d}"
            parent_assay = _assay_genotype(
                *parent,
                archived["task"],
                evolution_spec,
                mutation_source,
                mutation_source,
                audit_spec.futures_per_history,
                (0, 8),
                ("forced_break",),
                "minimal",
                master_seed=audit_spec.master_seed,
            )
            parent_score = _risk(parent_assay, "candidate.intact", 8)
            parent_renewal = _risk(
                parent_assay, "candidate.intact", 8, "correct_rate"
            ) - _risk(parent_assay, "candidate.renewal-off", 8, "correct_rate")
            for offspring_index in range(audit_spec.offspring_per_parent):
                random = rng_for(
                    audit_spec.master_seed,
                    "mutation-neighborhood",
                    treatment,
                    population_index,
                    parent_rank,
                    offspring_index,
                )
                offspring = _mutate_for_treatment(
                    parent, parent, random, treatment, evolution_spec
                )
                offspring_assay = _assay_genotype(
                    *offspring,
                    archived["task"],
                    evolution_spec,
                    mutation_source,
                    mutation_source,
                    audit_spec.futures_per_history,
                    (0, 8),
                    ("forced_break",),
                    "minimal",
                    master_seed=audit_spec.master_seed,
                )
                offspring_score = _risk(offspring_assay, "candidate.intact", 8)
                offspring_renewal = _risk(
                    offspring_assay, "candidate.intact", 8, "correct_rate"
                ) - _risk(
                    offspring_assay,
                    "candidate.renewal-off",
                    8,
                    "correct_rate",
                )
                mutation_rows.append(
                    {
                        "population_id": archived["population_id"],
                        "population_index": population_index,
                        "treatment": treatment,
                        "parent_rank": parent_rank,
                        "parent_population_index": parent_index,
                        "offspring_index": offspring_index,
                        "parent_genotype_id": parent_item["genotype_id"],
                        "offspring_genotype_id": _serialize_genotype(*offspring)[
                            "genotype_id"
                        ],
                        "parent_capacity": int(parent[1].k),
                        "offspring_capacity": int(offspring[1].k),
                        "parent_score": parent_score,
                        "parent_renewal_contrast": parent_renewal,
                        "offspring_score": offspring_score,
                        "offspring_renewal_contrast": offspring_renewal,
                        "common_stream_id": mutation_source,
                    }
                )
    result = {
        "format": RENEWAL_AUDIT_FORMAT,
        "population_id": archived["population_id"],
        "population_index": population_index,
        "treatment": treatment,
        "full_causal_panel": full_causal,
        "common_heldout_source_id": source_id,
        "common_streams_verified": source_id
        == f"heldout.population-{population_index:03d}",
        "selected_capacity": int(selected[1].k),
        "selected_heldout": selected_assay,
        "founder_heldout": founder_assay,
        "mutation_rows": mutation_rows,
        **_heldout_metrics(selected_assay, founder_assay),
    }
    result["audit_digest"] = canonical_digest(
        {
            "selected": selected_assay,
            "founder": founder_assay,
            "mutations": mutation_rows,
        }
    )
    return result


def _audit_population_task(
    args: tuple[str, str, dict[str, Any], dict[str, Any], str]
) -> dict[str, Any]:
    archive_text, output_text, evolution_value, audit_value, protocol_digest = args
    archive_path = Path(archive_text)
    output = Path(output_text)
    final_path = output / archive_path.name
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"renewal audit registration differs: {final_path}")
    evolution_spec = RenewalEvolutionSpec.from_dict(evolution_value)
    audit_spec = MutationNeighborhoodSpec.from_dict(audit_value)
    result = _compute_audit_population(
        read_json(archive_path), evolution_spec, audit_spec
    )
    result["protocol_digest"] = protocol_digest
    _atomic_json(final_path, result)
    return result


def run_renewal_audit(
    evolution_directory: Path,
    audit_spec: MutationNeighborhoodSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    audit_spec.validate()
    if workers < 1 or workers > 4:
        raise ValueError("renewal audit permits one to four workers")
    evolution_directory = evolution_directory.resolve()
    verify_renewal_evolution(evolution_directory)
    evolution_registration = read_json(evolution_directory / "registration.json")
    evolution_spec = RenewalEvolutionSpec.from_dict(evolution_registration["protocol"])
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_renewal_audit(destination)
        return destination
    started = time.monotonic()
    protocol = {
        "evolution": evolution_spec.to_dict(),
        "audit": audit_spec.to_dict(),
    }
    digest = canonical_digest(protocol)
    registration = {
        "format": AUDIT_REGISTRATION_FORMAT,
        "protocol": protocol,
        "protocol_digest": digest,
        "untouched_random_seed": True,
        "all_final_populations_receive_common_64-future_panel": True,
        "full_causal_panel_treatments": [
            "renewal_standard_cost",
            "renewal_high_cost",
        ],
        "mutation_sampling": "six fitness-quantile parents times four offspring",
        "population_cluster_is_inferential_unit": True,
        "raw_pearson_is_not_a_gate": True,
        "hard_k5_arm_is_engineering_feasibility_only": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(
        read_json(registration_path)
    ) != canonical_digest(registration):
        raise ValueError("existing renewal audit registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    units = destination / "populations"
    units.mkdir(exist_ok=True)
    archives = sorted(
        path
        for path in (evolution_directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    tasks = [
        (
            str(path),
            str(units),
            evolution_spec.to_dict(),
            audit_spec.to_dict(),
            digest,
        )
        for path in archives
    ]
    results: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_audit_population_task, tasks)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        iterator = executor.map(_audit_population_task, tasks)
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-ph-renewal-audit-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"held-out renewal/mutation audit {index}/{len(tasks)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    mutation_rows = [row for value in results for row in value["mutation_rows"]]
    write_jsonl_gz(destination / "mutation-neighborhood.jsonl.gz", mutation_rows)
    analysis = analyze_renewal_audit(
        results, mutation_rows, evolution_spec, audit_spec
    )
    _atomic_json(destination / "analysis.json", analysis)
    (destination / "report.md").write_text(
        render_audit_report(analysis), encoding="utf-8"
    )
    _atomic_json(
        destination / "manifest.json",
        {
            "format": AUDIT_MANIFEST_FORMAT,
            "protocol_digest": digest,
            "population_count": len(results),
            "expected_population_count": evolution_spec.population_count,
            "mutation_row_count": len(mutation_rows),
            "expected_mutation_row_count": 3
            * evolution_spec.populations_per_treatment
            * audit_spec.parents_per_population
            * audit_spec.offspring_per_parent,
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_renewal_audit(destination)
    return destination


def verify_renewal_audit(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != AUDIT_REGISTRATION_FORMAT:
        raise ValueError("renewal audit registration format mismatch")
    if manifest.get("format") != AUDIT_MANIFEST_FORMAT:
        raise ValueError("renewal audit manifest format mismatch")
    evolution_spec = RenewalEvolutionSpec.from_dict(
        registration["protocol"]["evolution"]
    )
    audit_spec = MutationNeighborhoodSpec.from_dict(
        registration["protocol"]["audit"]
    )
    digest = canonical_digest(registration["protocol"])
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("renewal audit protocol digest mismatch")
    if int(manifest["population_count"]) != evolution_spec.population_count:
        raise ValueError("renewal audit population count mismatch")
    expected_rows = (
        3
        * evolution_spec.populations_per_treatment
        * audit_spec.parents_per_population
        * audit_spec.offspring_per_parent
    )
    if int(manifest["mutation_row_count"]) != expected_rows:
        raise ValueError("renewal audit mutation row count mismatch")
    files = list((directory / "populations").glob("*.json"))
    if len(files) != evolution_spec.population_count:
        raise ValueError("renewal audit population file count mismatch")
    analysis = read_json(directory / "analysis.json")
    if analysis.get("format") != RENEWAL_AUDIT_FORMAT:
        raise ValueError("renewal audit analysis format mismatch")
    archived_rows = list(read_jsonl_gz(directory / "mutation-neighborhood.jsonl.gz"))
    if len(archived_rows) != expected_rows:
        raise ValueError("renewal audit archived mutation count mismatch")
    for path in files:
        value = read_json(path)
        expected_digest = canonical_digest(
            {
                "selected": value["selected_heldout"],
                "founder": value["founder_heldout"],
                "mutations": value["mutation_rows"],
            }
        )
        if value.get("audit_digest") != expected_digest:
            raise ValueError(f"renewal audit population digest mismatch: {path.name}")
    return {
        "verified": True,
        "populations": evolution_spec.population_count,
        "mutation_rows": expected_rows,
        "checksums": len(checksums),
    }


def replay_renewal_audit_population(
    directory: Path, population_id: str
) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    evolution_spec = RenewalEvolutionSpec.from_dict(
        registration["protocol"]["evolution"]
    )
    audit_spec = MutationNeighborhoodSpec.from_dict(
        registration["protocol"]["audit"]
    )
    archived = read_json(directory / "populations" / f"{population_id}.json")
    evolution_root = directory.parent / "evolution" / "populations"
    population = read_json(evolution_root / f"{population_id}.json")
    replayed = _compute_audit_population(population, evolution_spec, audit_spec)
    return {
        "population_id": population_id,
        "matches": replayed["audit_digest"] == archived["audit_digest"],
        "archived_digest": archived["audit_digest"],
        "replayed_digest": replayed["audit_digest"],
    }
