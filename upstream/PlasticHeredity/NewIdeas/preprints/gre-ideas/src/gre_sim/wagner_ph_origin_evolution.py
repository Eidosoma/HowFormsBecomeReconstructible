"""Paired factorial evolution for Wagner PH origin/discrimination v1."""

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
    runtime_manifest,
    verify_checksums,
    write_checksums,
    write_json,
)
from .local_ph_config import LocalCarrierGenome, LocalConditionSpec, LocalStudySpec
from .local_ph_study import simulate_local_source
from .rng import rng_for
from .wagner import WagnerRulebook
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_bridge_evolution import (
    _deserialize_genotype,
    _mutate_genotype,
    _sample_task,
    _serialize_genotype,
    _source,
)
from .wagner_ph_origin_config import (
    ORIGIN_EVOLUTION_FORMAT,
    ORIGIN_TREATMENTS,
    OriginEvolutionSpec,
    treatment_objective,
    treatment_scaffold,
)


EVOLUTION_REGISTRATION_FORMAT = "gre-wagner-ph-origin-evolution-registration-v1"
EVOLUTION_MANIFEST_FORMAT = "gre-wagner-ph-origin-evolution-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def origin_resource_cost(carrier: LocalCarrierGenome, spec: OriginEvolutionSpec) -> float:
    return float(
        spec.capacity_cost * carrier.k / spec.genes
        + spec.coupling_cost * carrier.coupling
        + spec.writing_cost * carrier.write_rate
    )


def _candidate(carrier: LocalCarrierGenome) -> LocalCarrierGenome:
    return replace(carrier, name="candidate")


def _conditions(spec: OriginEvolutionSpec) -> tuple[LocalConditionSpec, ...]:
    selected = spec.selected_noise.name
    harsher = spec.harsher_noise.name
    return (
        LocalConditionSpec("candidate.intact", "candidate", "intact", selected, True),
        LocalConditionSpec(
            "candidate.renewal-off", "candidate", "renewal_off", selected
        ),
        LocalConditionSpec("zero", None, "zero", selected),
        LocalConditionSpec("candidate.harsher", "candidate", "intact", harsher),
        LocalConditionSpec(
            "candidate.harsher-renewal-off",
            "candidate",
            "renewal_off",
            harsher,
        ),
        LocalConditionSpec("zero.harsher", None, "zero", harsher),
    )


def assay_origin_genotype(
    rulebook: WagnerRulebook,
    carrier: LocalCarrierGenome,
    task: dict[str, Any],
    spec: OriginEvolutionSpec,
    source_id: str,
    label: str,
    replicates: int,
    checkpoints: tuple[int, ...],
    challenges: tuple[str, ...],
    *,
    master_seed: str | None = None,
    conditions_override: tuple[LocalConditionSpec, ...] | None = None,
) -> dict[str, Any]:
    """Assay intact and physically renewal-locked states on common streams."""

    conditions = conditions_override or _conditions(spec)
    noises = (
        (spec.selected_noise,)
        if spec.selected_noise.name == spec.harsher_noise.name
        else (spec.selected_noise, spec.harsher_noise)
    )
    study = LocalStudySpec(
        cohort_id=f"{spec.cohort_id}.{label}",
        phase=f"origin-assay.{label}",
        master_seed=master_seed or spec.master_seed,
        source_count=1,
        genomes=(_candidate(carrier),),
        noises=noises,
        conditions=conditions,
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
        key = (
            str(record["condition"]),
            int(record["generation"]),
            str(record["challenge"]),
        )
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
        baseline = "zero.harsher" if "harsher" in condition else "zero"
        for generation, events in generations.items():
            for challenge, value in events.items():
                zero = cells[baseline][generation][challenge]
                value["risk_gain"] = float(value["correct_rate"]) - float(
                    zero["correct_rate"]
                )
    return {
        "panel": "origin-intact-locked-common",
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


def origin_training_score(
    genotype: tuple[WagnerRulebook, LocalCarrierGenome],
    task: dict[str, Any],
    spec: OriginEvolutionSpec,
    treatment: str,
    population_index: int,
    generation: int,
) -> dict[str, float]:
    objective = treatment_objective(treatment)
    source_id = f"origin-training.population-{population_index:03d}.generation-{generation:03d}"
    assay = assay_origin_genotype(
        *genotype,
        task,
        spec,
        source_id,
        source_id,
        spec.training_replicates,
        (0, 8),
        ("forced_break",),
    )
    intact_selected = _risk(assay, "candidate.intact", 8)
    intact_harsher = _risk(assay, "candidate.harsher", 8)
    passive_selected = _risk(assay, "candidate.renewal-off", 8)
    passive_harsher = _risk(assay, "candidate.harsher-renewal-off", 8)
    renewal = _risk(assay, "candidate.intact", 8, "correct_rate") - _risk(
        assay, "candidate.renewal-off", 8, "correct_rate"
    )
    if objective == "explicit_renewal":
        selected = intact_selected
        harsher = intact_harsher
        phenotype = 0.50 * selected + 0.25 * harsher + 0.25 * renewal
    elif objective == "permissive_performance":
        selected = intact_selected
        harsher = intact_harsher
        phenotype = (2.0 / 3.0) * selected + (1.0 / 3.0) * harsher
    else:
        selected = passive_selected
        harsher = passive_harsher
        phenotype = (2.0 / 3.0) * selected + (1.0 / 3.0) * harsher
    cost = origin_resource_cost(genotype[1], spec)
    return {
        "selected_gain": selected,
        "harsher_gain": harsher,
        "renewal_contrast": renewal,
        "intact_selected_gain": intact_selected,
        "passive_selected_gain": passive_selected,
        "resource_cost": cost,
        "fitness": phenotype - cost,
    }


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(args: tuple[dict[str, Any], str, int, str, str]) -> dict[str, Any]:
    spec_value, treatment, population_index, output_text, protocol_digest = args
    spec = OriginEvolutionSpec.from_dict(spec_value)
    population_id = f"{treatment}.population-{population_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"origin evolution registration differs: {final_path}")
    checkpoint_path = output / f"{population_id}.checkpoint.json"
    task = _sample_task(spec, population_index)
    scaffold_name = treatment_scaffold(treatment)
    scaffold = spec.scaffold(scaffold_name)
    if checkpoint_path.is_file():
        checkpoint = read_json(checkpoint_path)
        if checkpoint.get("protocol_digest") != protocol_digest:
            raise ValueError("origin evolution checkpoint protocol differs")
        population = [_deserialize_genotype(value) for value in checkpoint["population"]]
        lineage_ids = [str(value) for value in checkpoint["lineage_ids"]]
        scores = [
            {key: float(item[key]) for key in item} for item in checkpoint["scores"]
        ]
        ancestry = list(checkpoint["ancestry"])
        trace = list(checkpoint["trace"])
        start_generation = int(checkpoint["generation"]) + 1
    else:
        founder = (WagnerRulebook.from_dict(task["founder"]), scaffold)
        population = [founder]
        for index in range(1, spec.population_size):
            random = rng_for(
                spec.master_seed,
                "origin-evolution-initial",
                treatment,
                population_index,
                index,
            )
            population.append(_mutate_genotype(founder, founder, random))
        scores = [
            origin_training_score(
                value, task, spec, treatment, population_index, 0
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest(
                (population_id, 0, index, value[0].to_dict(), value[1].to_dict())
            )[:24]
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

    def trace_item(generation: int) -> dict[str, Any]:
        return {
            "generation": generation,
            "mean_fitness": float(np.mean([value["fitness"] for value in scores])),
            "best_fitness": float(np.max([value["fitness"] for value in scores])),
            "mean_renewal_contrast": float(
                np.mean([value["renewal_contrast"] for value in scores])
            ),
            "mean_capacity": float(np.mean([value[1].k for value in population])),
            "writer_active_fraction": float(
                np.mean([value[1].write_rate > 0.0 for value in population])
            ),
            "reader_active_fraction": float(
                np.mean([value[1].coupling > 0.0 for value in population])
            ),
        }

    if not trace:
        trace.append(trace_item(0))
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(
            spec.master_seed,
            "origin-evolution-generation",
            treatment,
            population_index,
            generation,
        )
        following: list[tuple[WagnerRulebook, LocalCarrierGenome]] = []
        parents: list[tuple[str, ...]] = []
        elites = sorted(
            range(len(population)), key=lambda index: (-fitness[index], index)
        )[: spec.elite_count]
        for index in elites:
            following.append(population[index])
            parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            left = _tournament(fitness, random, spec.tournament_size)
            right = _tournament(fitness, random, spec.tournament_size)
            following.append(
                _mutate_genotype(population[left], population[right], random)
            )
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [
            origin_training_score(
                value, task, spec, treatment, population_index, generation
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest(
                (
                    population_id,
                    generation,
                    index,
                    value[0].to_dict(),
                    value[1].to_dict(),
                )
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
        trace.append(trace_item(generation))
        _atomic_json(
            checkpoint_path,
            {
                "format": "gre-wagner-ph-origin-evolution-checkpoint-v1",
                "protocol_digest": protocol_digest,
                "generation": generation,
                "population": [_serialize_genotype(*value) for value in population],
                "lineage_ids": lineage_ids,
                "scores": scores,
                "ancestry": ancestry,
                "trace": trace,
            },
        )
    selected_index = int(np.argmax([value["fitness"] for value in scores]))
    founder = (WagnerRulebook.from_dict(task["founder"]), scaffold)
    result = {
        "format": ORIGIN_EVOLUTION_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "population_index": population_index,
        "treatment": treatment,
        "scaffold": scaffold_name,
        "objective": treatment_objective(treatment),
        "task": task,
        "task_is_frozen_across_treatments": True,
        "selection_uses_target_label_inside_carrier": False,
        "common_training_stream_pattern": (
            f"origin-training.population-{population_index:03d}.generation-GGG"
        ),
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


def analyze_origin_training(
    results: list[dict[str, Any]], spec: OriginEvolutionSpec
) -> dict[str, Any]:
    treatments: dict[str, Any] = {}
    for treatment in spec.treatments:
        values = [value for value in results if value["treatment"] == treatment]
        treatments[treatment] = {
            "scaffold": treatment_scaffold(treatment),
            "objective": treatment_objective(treatment),
            "selected_training_fitness": _interval(
                (float(value["selected_training_score"]["fitness"]) for value in values),
                spec.master_seed,
                f"origin-training.{treatment}.fitness",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "selected_training_renewal_contrast": _interval(
                (
                    float(value["selected_training_score"]["renewal_contrast"])
                    for value in values
                ),
                spec.master_seed,
                f"origin-training.{treatment}.renewal",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "writer_reader_active_populations": sum(
                float(value["selected"]["carrier"]["write_rate"]) > 0.0
                and float(value["selected"]["carrier"]["coupling"]) > 0.0
                for value in values
            ),
            "median_selected_capacity": float(
                np.median([int(value["selected"]["carrier"]["k"]) for value in values])
            )
            if values
            else None,
        }
    return {
        "format": "gre-wagner-ph-origin-evolution-analysis-v1",
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


def run_origin_evolution(
    spec: OriginEvolutionSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 4:
        raise ValueError("origin evolution permits one to four workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_origin_evolution(destination)
        return destination
    started = time.monotonic()
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": EVOLUTION_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
        "carrier_receives_target_label": False,
        "tasks_are_paired_by_population_index": True,
        "assay_streams_are_common_by_population_and_generation": True,
        "selection_and_heldout_data_are_separate": True,
        "objectives_have_identical_costs": True,
        "passive_locked_physically_disables_descendant_rewriting": True,
        "dormant_scaffold_contains_a_predefined_but_inactive_channel": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(
        read_json(registration_path)
    ) != canonical_digest(registration):
        raise ValueError("existing origin evolution registration differs")
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
    executor: concurrent.futures.ProcessPoolExecutor | None = None
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, tasks)
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
                    "format": "gre-wagner-ph-origin-evolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"origin factorial evolution {index}/{len(tasks)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    analysis = analyze_origin_training(results, spec)
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
    verify_origin_evolution(destination)
    return destination


def verify_origin_evolution(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != EVOLUTION_REGISTRATION_FORMAT:
        raise ValueError("origin evolution registration format mismatch")
    if manifest.get("format") != EVOLUTION_MANIFEST_FORMAT:
        raise ValueError("origin evolution manifest format mismatch")
    spec = OriginEvolutionSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("origin evolution protocol digest mismatch")
    files = [
        path
        for path in (directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    ]
    if len(files) != spec.population_count or int(manifest["population_count"]) != spec.population_count:
        raise ValueError("origin evolution population count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"origin evolution population digest mismatch: {path.name}")
        expected = canonical_digest(
            {
                "selected": value["selected"],
                "score": value["selected_training_score"],
                "trace": value["trace"],
            }
        )
        if value.get("result_digest") != expected:
            raise ValueError(f"origin evolution result digest mismatch: {path.name}")
        if treatment_scaffold(str(value["treatment"])) != value["scaffold"]:
            raise ValueError(f"origin scaffold mismatch: {path.name}")
    return {
        "verified": True,
        "populations": spec.population_count,
        "checksums": len(checksums),
    }


def replay_origin_population(directory: Path, population_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    spec = OriginEvolutionSpec.from_dict(registration["protocol"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    selected = _deserialize_genotype(archived["selected"])
    score = origin_training_score(
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
