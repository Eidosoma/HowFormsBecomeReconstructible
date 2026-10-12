"""Performance-only evolution for Global Repair Ratchet v1."""

from __future__ import annotations

import concurrent.futures
import json
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
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .rng import rng_for
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import verify_cooption_evolution
from .wagner_ph_maintenance_config import MaintenanceSpec, arm_settings
from .wagner_ph_maintenance_evolution import maintenance_score
from .wagner_ph_maintenance_genome import (
    Genome,
    MaintenanceInterpreter,
    deserialize_genome,
    genome_id,
    initialize_from_source,
    mutate_genome,
    serialize_genome,
)
from .wagner_ph_repair_ratchet_config import (
    RATCHET_FORMAT,
    RepairRatchetSpec,
    RepairRoute,
)


EVOLUTION_FORMAT = f"{RATCHET_FORMAT}-evolution"


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _route_seed(spec: RepairRatchetSpec, route: RepairRoute) -> str:
    return canonical_digest((spec.master_seed, "route", route.name))


def _route_maintenance(
    base: MaintenanceSpec,
    route: RepairRoute,
    generation: int,
) -> MaintenanceSpec:
    return replace(
        base,
        repair_cost=route.repair_cost(generation),
        repair_mutation_sigma=route.repair_mutation_sigma(generation),
        lineage_count=route.virtual_lineages,
        tail_size=route.tail_size,
    )


def route_score(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    base: MaintenanceSpec,
    spec: RepairRatchetSpec,
    route: RepairRoute,
    task_index: int,
    generation: int,
) -> dict[str, Any]:
    result = maintenance_score(
        genome,
        task,
        kernel,
        _route_maintenance(base, route, generation),
        route.legacy_arm,
        task_index,
        generation,
        "development",
        seed=_route_seed(spec, route),
    )
    return {
        **result,
        "repair_cost_at_generation": route.repair_cost(generation),
        "repair_mutation_sigma_at_generation": route.repair_mutation_sigma(generation),
        "virtual_lineages_at_generation": route.virtual_lineages,
        "fitness_contains_memory_information_intervention_or_ph_metric": False,
    }


def _initialize(value: dict[str, Any], route: RepairRoute, base: MaintenanceSpec) -> Genome:
    genome = initialize_from_source(value, route.legacy_arm, base)
    if not route.has_repair:
        return genome
    interpreter, carrier = genome
    return (
        MaintenanceInterpreter(
            interpreter.copies,
            "global_repair",
            global_repair=route.initial_repair,
        ),
        carrier,
    )


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        source_text,
        route_value,
        ratchet_value,
        maintenance_value,
        kernel_value,
        output_text,
        digest,
    ) = args
    source = read_json(Path(source_text))
    route = RepairRoute.from_dict(route_value)
    spec = RepairRatchetSpec.from_dict(ratchet_value)
    base = MaintenanceSpec.from_dict(maintenance_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    route.validate(spec.generations)
    task_index = int(source["population_index"])
    population_id = f"{route.name}.population-{task_index:03d}"
    final_path = Path(output_text) / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("repair-ratchet population registration differs")
    checkpoint = final_path.with_name(f"{population_id}.checkpoint.json")
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        if saved.get("protocol_digest") != digest:
            raise ValueError("repair-ratchet checkpoint registration differs")
        population = [deserialize_genome(value) for value in saved["population"]]
        lineage_ids = list(saved["lineage_ids"])
        scores = list(saved["scores"])
        trace = list(saved["trace"])
        ancestry = list(saved["ancestry"])
        start_generation = int(saved["generation"]) + 1
    else:
        population = [
            _initialize(value, route, base)
            for value in source["final_population"][: spec.population_size]
        ]
        if len(population) != spec.population_size:
            raise ValueError("repair-ratchet source population has unexpected size")
        scores = [
            route_score(value, source["task"], kernel, base, spec, route, task_index, 0)
            for value in population
        ]
        lineage_ids = [
            canonical_digest((route.name, population_id, 0, index, genome_id(value)))[:24]
            for index, value in enumerate(population)
        ]
        trace, ancestry, start_generation = [], [], 1

    def trace_item(generation: int) -> dict[str, Any]:
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        repairs = np.asarray([value[0].global_repair for value in population], dtype=float)
        return {
            "generation": generation,
            "mean_selection_fitness": float(np.mean(fitness)),
            "best_selection_fitness": float(np.max(fitness)),
            "mean_focal_performance": float(
                np.mean([value["focal_score"]["performance"] for value in scores])
            ),
            "mean_global_repair": float(np.mean(repairs)),
            "maximum_global_repair": float(np.max(repairs)),
            "repair_cost": route.repair_cost(generation),
            "repair_mutation_sigma": route.repair_mutation_sigma(generation),
            "virtual_lineages": route.virtual_lineages,
        }

    if not trace:
        trace.append(trace_item(0))
        ancestry.append(
            {
                "generation": 0,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        **serialize_genome(value),
                        "selection_score": scores[index],
                    }
                    for index, value in enumerate(population)
                ],
            }
        )
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(
            spec.master_seed,
            "repair-ratchet-generation",
            route.name,
            task_index,
            generation,
        )
        following: list[Genome] = []
        parents: list[tuple[str, ...]] = []
        elites = sorted(
            range(len(population)), key=lambda index: (-fitness[index], index)
        )[: spec.elite_count]
        for index in elites:
            following.append(population[index])
            parents.append((lineage_ids[index],))
        mutation_spec = _route_maintenance(base, route, generation)
        while len(following) < spec.population_size:
            left = _tournament(fitness, random, spec.tournament_size)
            right = _tournament(fitness, random, spec.tournament_size)
            following.append(
                mutate_genome(
                    population[left],
                    population[right],
                    route.legacy_arm,
                    random,
                    mutation_spec,
                )
            )
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [
            route_score(
                value,
                source["task"],
                kernel,
                base,
                spec,
                route,
                task_index,
                generation,
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest(
                (route.name, population_id, generation, index, genome_id(value))
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
                        **serialize_genome(value),
                        "selection_score": scores[index],
                    }
                    for index, value in enumerate(population)
                ],
            }
        )
        trace.append(trace_item(generation))
        _atomic_json(
            checkpoint,
            {
                "protocol_digest": digest,
                "generation": generation,
                "route": route.name,
                "population": [serialize_genome(value) for value in population],
                "lineage_ids": lineage_ids,
                "scores": scores,
                "trace": trace,
                "ancestry": ancestry,
            },
        )
    best = int(np.argmax(np.asarray([value["fitness"] for value in scores], dtype=float)))
    selected = serialize_genome(population[best])
    result = {
        "format": EVOLUTION_FORMAT,
        "protocol_digest": digest,
        "population_id": population_id,
        "population_index": task_index,
        "route": route.name,
        "route_settings": route.to_dict(),
        "arm": route.legacy_arm,
        "arm_settings": {
            **arm_settings(route.legacy_arm),
            "repair_ratchet_route": route.name,
        },
        "task": source["task"],
        "selected": selected,
        "selected_effective_genotype": selected["effective_genotype"],
        "selected_selection_score": scores[best],
        "selected_training_score": scores[best]["focal_score"],
        "final_population": [
            {
                **serialize_genome(value),
                "selection_score": scores[index],
                "focal_training_score": scores[index]["focal_score"],
            }
            for index, value in enumerate(population)
        ],
        "trace": trace,
        "ancestry": ancestry,
        "fitness_contains_only_observable_performance_and_resource_cost": True,
        "fitness_contains_memory_information_intervention_or_ph_metric": False,
        "actual_reproduction_uses_ordinary_wagner_redraws": True,
    }
    result["result_digest"] = canonical_digest(
        {
            "route": route.name,
            "selected": selected,
            "score": scores[best],
            "trace": trace,
        }
    )
    _atomic_json(final_path, result)
    if checkpoint.is_file():
        checkpoint.unlink()
    return result


def run_repair_ratchet_evolution(
    spec: RepairRatchetSpec,
    source: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("repair-ratchet evolution permits one to four CPU workers")
    source = source.resolve()
    verify_cooption_evolution(source)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_repair_ratchet_evolution(destination)
        return destination
    base = spec.maintenance()
    kernel = base.kernel()
    payload = {
        "spec": spec.to_dict(),
        "maintenance_spec": _json_value(base.to_dict()),
        "kernel": _json_value(kernel.to_dict()),
        "source_checksum": sha256_file(source / "SHA256SUMS"),
        "source_arm": "direct_independent",
        "routes": [route.to_dict() for route in spec.routes],
    }
    digest = canonical_digest(payload)
    registration = {
        "format": f"{EVOLUTION_FORMAT}-registration",
        "protocol_digest": digest,
        **payload,
        "source": str(source),
        "selection_excludes_history_labels_ph_information_interventions_and_gates": True,
    }
    path = destination / "registration.json"
    if path.is_file() and canonical_digest(read_json(path)) != canonical_digest(registration):
        raise ValueError("existing repair-ratchet evolution registration differs")
    if not path.is_file():
        _atomic_json(path, registration)
    shards = destination / "populations"
    shards.mkdir(exist_ok=True)
    files = sorted((source / "populations").glob("direct_independent.population-*.json"))
    if len(files) < spec.task_count:
        raise ValueError("repair-ratchet source task count mismatch")
    files = files[: spec.task_count]
    work = [
        (
            str(source_path),
            route.to_dict(),
            spec.to_dict(),
            _json_value(base.to_dict()),
            _json_value(kernel.to_dict()),
            str(shards),
            digest,
        )
        for route in spec.routes
        for source_path in files
    ]
    started = time.monotonic()
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
        )
        futures = [executor.submit(_population_task, item) for item in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, value in enumerate(iterator, 1):
            completed.append(value)
            elapsed = time.monotonic() - started
            _atomic_json(
                destination / "progress.json",
                {
                    "completed_populations": index,
                    "total_populations": len(work),
                    "elapsed_seconds": elapsed,
                    "eta_seconds": (len(work) - index) * elapsed / max(index, 1),
                },
            )
            if progress:
                progress(f"repair-ratchet evolution {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    route_summary = {
        route.name: {
            "populations": sum(value["route"] == route.name for value in completed),
            "final_mean_repair": float(
                np.mean(
                    [
                        value["selected"]["interpreter"]["global_repair"]
                        for value in completed
                        if value["route"] == route.name
                    ]
                )
            ),
        }
        for route in spec.routes
    }
    _atomic_json(
        destination / "analysis.json",
        {
            "format": f"{EVOLUTION_FORMAT}-analysis",
            "routes": route_summary,
            "analysis_digest": canonical_digest(route_summary),
        },
    )
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{EVOLUTION_FORMAT}-manifest",
            "protocol_digest": digest,
            "populations": len(completed),
            "elapsed_seconds": time.monotonic() - started,
            "maximum_workers": spec.maximum_workers,
            "workers_used": workers,
            "cpu_only": True,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_repair_ratchet_evolution(destination)
    return destination


def verify_repair_ratchet_evolution(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = RepairRatchetSpec.from_dict(registration["spec"])
    base = MaintenanceSpec.from_dict(registration["maintenance_spec"])
    CooptionSpec.from_dict(registration["kernel"])
    if registration.get("format") != f"{EVOLUTION_FORMAT}-registration":
        raise ValueError("repair-ratchet evolution format mismatch")
    payload = {
        key: registration[key]
        for key in (
            "spec",
            "maintenance_spec",
            "kernel",
            "source_checksum",
            "source_arm",
            "routes",
        )
    }
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("repair-ratchet evolution protocol mismatch")
    if sha256_file(Path(registration["source"]) / "SHA256SUMS") != registration["source_checksum"]:
        raise ValueError("repair-ratchet source changed")
    if canonical_digest(_json_value(base.to_dict())) != canonical_digest(registration["maintenance_spec"]):
        raise ValueError("repair-ratchet maintenance kernel changed")
    files = sorted(
        path
        for path in (directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    expected = spec.task_count * len(spec.routes)
    for path in files:
        value = read_json(path)
        archived = canonical_digest(
            {
                "route": value["route"],
                "selected": value["selected"],
                "score": value["selected_selection_score"],
                "trace": value["trace"],
            }
        )
        if (
            value.get("format") != EVOLUTION_FORMAT
            or value.get("protocol_digest") != registration["protocol_digest"]
            or value.get("result_digest") != archived
            or value.get("route") not in {route.name for route in spec.routes}
            or len(value.get("trace", ())) != spec.generations + 1
            or len(value.get("final_population", ())) != spec.population_size
        ):
            raise ValueError(f"repair-ratchet population digest mismatch: {path}")
        deserialize_genome(value["selected"])
    if (
        len(files) != expected
        or manifest.get("populations") != expected
        or manifest.get("protocol_digest") != registration["protocol_digest"]
        or manifest.get("workers_used", 5) > spec.maximum_workers
        or not manifest.get("cpu_only")
    ):
        raise ValueError("repair-ratchet evolution is incomplete")
    return {"verified": True, "populations": len(files), "checksums": len(checksums)}


def replay_repair_ratchet_population(directory: Path, population_id: str) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = RepairRatchetSpec.from_dict(registration["spec"])
    base = MaintenanceSpec.from_dict(registration["maintenance_spec"])
    kernel = CooptionSpec.from_dict(registration["kernel"])
    population = read_json(directory / "populations" / f"{population_id}.json")
    route = next(route for route in spec.routes if route.name == population["route"])
    genome = deserialize_genome(population["selected"])
    replayed = route_score(
        genome,
        population["task"],
        kernel,
        base,
        spec,
        route,
        int(population["population_index"]),
        spec.generations,
    )
    return {
        "population_id": population_id,
        "matches": canonical_digest(replayed)
        == canonical_digest(population["selected_selection_score"]),
        "archived_digest": canonical_digest(population["selected_selection_score"]),
        "replayed_digest": canonical_digest(replayed),
    }


__all__ = (
    "EVOLUTION_FORMAT",
    "replay_repair_ratchet_population",
    "route_score",
    "run_repair_ratchet_evolution",
    "verify_repair_ratchet_evolution",
)
