"""Performance-only evolution for Adaptive Maintenance v1."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
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
from .wagner_ph_cooption_evolution import training_score, verify_cooption_evolution
from .wagner_ph_maintenance_config import (
    DEVELOPMENT_ARMS,
    MAINTENANCE_FORMAT,
    MaintenanceSpec,
    arm_settings,
)
from .wagner_ph_maintenance_genome import (
    Genome,
    architecture_cost,
    deserialize_genome,
    effective_genotype,
    genome_id,
    initialize_from_source,
    mutate_genome,
    serialize_genome,
)


EVOLUTION_FORMAT = f"{MAINTENANCE_FORMAT}-evolution"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _focal_score(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: MaintenanceSpec,
    arm: str,
    task_index: int,
    generation: int,
    seed: str,
) -> dict[str, Any]:
    settings = arm_settings(arm)
    base = training_score(
        effective_genotype(genome),
        task,
        kernel,
        "direct_independent",
        task_index,
        generation,
        stream="adaptive-maintenance-performance-training",
        master_seed=seed,
        predictive_persistence=float(settings["predictive_persistence"]),
    )
    extra = architecture_cost(genome[0], spec)
    return {
        **base,
        "fitness": float(base["fitness"] - extra),
        "resource_cost": float(base["resource_cost"] + extra),
        "architecture_cost": extra,
        "interpreter_architecture": genome[0].architecture,
        "global_repair": genome[0].global_repair,
        "mean_node_repair": genome[0].mean_repair if genome[0].architecture == "node_repair" else 0.0,
        "copy_count": genome[0].copy_count,
        "decoder": genome[0].decoder,
    }


def maintenance_score(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: MaintenanceSpec,
    arm: str,
    task_index: int,
    generation: int,
    phase: str,
    *,
    seed: str | None = None,
) -> dict[str, Any]:
    """Score focal function and the lower tail of paired mutation lineages."""

    selected_seed = seed or (spec.confirmation_seed if phase == "confirmation" else spec.master_seed)
    settings = arm_settings(arm)
    focal = _focal_score(genome, task, kernel, spec, arm, task_index, generation, selected_seed)
    if settings["selection_mode"] == "individual":
        return {
            "selection_mode": "individual",
            "fitness": focal["fitness"],
            "performance": focal["performance"],
            "resource_cost": focal["resource_cost"],
            "focal_score": focal,
            "virtual_descendants": [],
            "selected_tail_size": 1,
            "fitness_components": {"focal": focal["fitness"]},
            "fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric": False,
        }

    immediate: list[dict[str, Any]] = []
    terminals: list[dict[str, Any]] = []
    trajectories: list[dict[str, Any]] = []
    stable_key = genome_id(genome)
    for lineage_index in range(spec.lineage_count):
        current = genome
        chain: list[dict[str, Any]] = []
        for distance in range(1, spec.lineage_depth + 1):
            random = rng_for(
                selected_seed,
                "adaptive-maintenance-virtual-lineage",
                phase,
                arm,
                task_index,
                generation,
                stable_key,
                lineage_index,
                distance,
            )
            child = mutate_genome(current, current, arm, random, spec)
            record: dict[str, Any] = {
                "lineage_index": lineage_index,
                "distance": distance,
                "genotype_id": genome_id(child),
            }
            if distance in {1, spec.lineage_depth}:
                record.update(
                    _focal_score(
                        child,
                        task,
                        kernel,
                        spec,
                        arm,
                        task_index,
                        generation,
                        selected_seed,
                    )
                )
            chain.append(record)
            if distance == 1:
                immediate.append(record)
            if distance == spec.lineage_depth:
                terminals.append(record)
            current = child
        trajectories.append({"lineage_index": lineage_index, "chain": chain})
    immediate_tail = sorted(
        immediate, key=lambda value: (value["fitness"], value["genotype_id"])
    )[: spec.tail_size]
    terminal_tail = sorted(
        terminals, key=lambda value: (value["fitness"], value["genotype_id"])
    )[: spec.tail_size]
    components = {
        "focal": float(focal["fitness"]),
        "immediate_tail": float(np.mean([value["fitness"] for value in immediate_tail])),
        "distance_four_tail": float(np.mean([value["fitness"] for value in terminal_tail])),
    }
    performances = {
        "focal": float(focal["performance"]),
        "immediate_tail": float(np.mean([value["performance"] for value in immediate_tail])),
        "distance_four_tail": float(np.mean([value["performance"] for value in terminal_tail])),
    }
    costs = {
        "focal": float(focal["resource_cost"]),
        "immediate_tail": float(np.mean([value["resource_cost"] for value in immediate_tail])),
        "distance_four_tail": float(np.mean([value["resource_cost"] for value in terminal_tail])),
    }
    return {
        "selection_mode": "multihorizon",
        "fitness": float(np.mean(list(components.values()))),
        "performance": float(np.mean(list(performances.values()))),
        "resource_cost": float(np.mean(list(costs.values()))),
        "focal_score": focal,
        "virtual_descendants": trajectories,
        "selected_tail_size": spec.tail_size,
        "fitness_components": components,
        "performance_components": performances,
        "resource_cost_components": costs,
        "fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric": False,
    }


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(args: tuple[Any, ...]) -> dict[str, Any]:
    source_text, arm, spec_value, kernel_value, output_text, digest, phase, seed = args
    source = read_json(Path(source_text))
    spec = MaintenanceSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(source["population_index"])
    population_id = f"{arm}.population-{task_index:03d}"
    final_path = Path(output_text) / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("maintenance population registration differs")
    checkpoint = final_path.with_name(f"{population_id}.checkpoint.json")
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        if saved.get("protocol_digest") != digest:
            raise ValueError("maintenance checkpoint registration differs")
        population = [deserialize_genome(value) for value in saved["population"]]
        lineage_ids = list(saved["lineage_ids"])
        scores = list(saved["scores"])
        trace = list(saved["trace"])
        ancestry = list(saved["ancestry"])
        start_generation = int(saved["generation"]) + 1
    else:
        population = [
            initialize_from_source(value, arm, spec)
            for value in source["final_population"][: spec.population_size]
        ]
        if len(population) != spec.population_size:
            raise ValueError("maintenance source population has unexpected size")
        scores = [
            maintenance_score(
                value,
                source["task"],
                kernel,
                spec,
                arm,
                task_index,
                0,
                phase,
                seed=seed,
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest((phase, population_id, 0, index, genome_id(value)))[:24]
            for index, value in enumerate(population)
        ]
        trace, ancestry, start_generation = [], [], 1

    def trace_item(generation: int) -> dict[str, Any]:
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        return {
            "generation": generation,
            "mean_selection_fitness": float(np.mean(fitness)),
            "best_selection_fitness": float(np.max(fitness)),
            "mean_focal_performance": float(
                np.mean([value["focal_score"]["performance"] for value in scores])
            ),
            "mean_global_repair": float(np.mean([value[0].global_repair for value in population])),
            "mean_node_repair": float(np.mean([value[0].mean_repair for value in population])),
            "mean_copy_count": float(np.mean([value[0].copy_count for value in population])),
            "median_decoder_fraction": float(
                np.mean([value[0].decoder == "median" for value in population])
            ),
            "interpreter_architecture": population[0][0].architecture,
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
            seed, "adaptive-maintenance-generation", phase, arm, task_index, generation
        )
        following: list[Genome] = []
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
                mutate_genome(population[left], population[right], arm, random, spec)
            )
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [
            maintenance_score(
                value,
                source["task"],
                kernel,
                spec,
                arm,
                task_index,
                generation,
                phase,
                seed=seed,
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest((phase, population_id, generation, index, genome_id(value)))[:24]
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
        "phase": phase,
        "population_id": population_id,
        "population_index": task_index,
        "arm": arm,
        "arm_settings": arm_settings(arm),
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
        "fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric": False,
    }
    result["result_digest"] = canonical_digest(
        {"selected": selected, "score": scores[best], "trace": trace}
    )
    _atomic_json(final_path, result)
    if checkpoint.is_file():
        checkpoint.unlink()
    return result


def run_maintenance_evolution(
    spec: MaintenanceSpec,
    source: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
    *,
    phase: str = "development",
    selected_arms: tuple[str, ...] | None = None,
    source_arm: str = "direct_independent",
) -> Path:
    spec.validate()
    if phase not in {"development", "confirmation"} or not 1 <= workers <= spec.maximum_workers:
        raise ValueError("invalid maintenance phase or worker count")
    arms = selected_arms or spec.arms
    if not arms or not set(arms) <= set(DEVELOPMENT_ARMS):
        raise ValueError("invalid maintenance arm subset")
    source = source.resolve()
    verify_cooption_evolution(source)
    source_checksum = sha256_file(source / "SHA256SUMS")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_maintenance_evolution(destination)
        return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = spec.confirmation_seed if phase == "confirmation" else spec.master_seed
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "source_checksum": source_checksum,
        "source_arm": source_arm,
        "phase": phase,
        "selected_arms": list(arms),
    }
    digest = canonical_digest(payload)
    registration = {
        "format": f"{EVOLUTION_FORMAT}-registration",
        "protocol_digest": digest,
        **payload,
        "source": str(source),
        "selection_excludes_memory_information_interventions_and_ph_metrics": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing maintenance evolution registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    shards = destination / "populations"
    shards.mkdir(exist_ok=True)
    files = sorted((source / "populations").glob(f"{source_arm}.population-*.json"))
    if len(files) < task_count:
        raise ValueError("maintenance source task count mismatch")
    files = files[:task_count]
    work = [
        (
            str(path),
            arm,
            spec.to_dict(),
            kernel.to_dict(),
            str(shards),
            digest,
            phase,
            seed,
        )
        for arm in arms
        for path in files
    ]
    started = time.monotonic()
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_population_task, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, 1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "completed_populations": index,
                    "total_populations": len(work),
                    "elapsed_seconds": elapsed,
                    "eta_seconds": (len(work) - index) / rate,
                },
            )
            if progress:
                progress(f"adaptive-maintenance {phase} evolution {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (arms.index(value["arm"]), value["population_index"]))
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{EVOLUTION_FORMAT}-manifest",
            "protocol_digest": digest,
            "phase": phase,
            "selected_arms": list(arms),
            "population_count": len(completed),
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "scientific_result_digest": canonical_digest(
                [value["result_digest"] for value in completed]
            ),
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_maintenance_evolution(destination)
    return destination


def verify_maintenance_evolution(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = MaintenanceSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{EVOLUTION_FORMAT}-registration":
        raise ValueError("maintenance evolution registration format mismatch")
    if manifest.get("format") != f"{EVOLUTION_FORMAT}-manifest":
        raise ValueError("maintenance evolution manifest format mismatch")
    if sha256_file(Path(registration["source"]) / "SHA256SUMS") != registration["source_checksum"]:
        raise ValueError("sealed maintenance source changed")
    payload = {
        key: registration[key]
        for key in ("spec", "kernel", "source_checksum", "source_arm", "phase", "selected_arms")
    }
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("maintenance evolution protocol mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    files = sorted(
        path
        for path in (directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    expected = task_count * len(registration["selected_arms"])
    if len(files) != expected or manifest["population_count"] != expected:
        raise ValueError("maintenance evolution is incomplete")
    values = [read_json(path) for path in files]
    for value in values:
        expected_digest = canonical_digest(
            {
                "selected": value["selected"],
                "score": value["selected_selection_score"],
                "trace": value["trace"],
            }
        )
        if (
            value.get("protocol_digest") != registration["protocol_digest"]
            or value.get("result_digest") != expected_digest
            or len(value.get("final_population", ())) != spec.population_size
        ):
            raise ValueError("maintenance evolution population digest mismatch")
        deserialize_genome(value["selected"])
        if value["fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric"]:
            raise ValueError("forbidden metric entered maintenance fitness")
    ordered = sorted(
        values,
        key=lambda value: (
            registration["selected_arms"].index(value["arm"]),
            value["population_index"],
        ),
    )
    if manifest["scientific_result_digest"] != canonical_digest(
        [value["result_digest"] for value in ordered]
    ):
        raise ValueError("maintenance evolution result digest mismatch")
    return {
        "verified": True,
        "phase": registration["phase"],
        "populations": len(files),
        "checksums": len(checksums),
    }


def replay_maintenance_population(directory: Path, population_id: str) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = MaintenanceSpec.from_dict(registration["spec"])
    kernel = CooptionSpec.from_dict(registration["kernel"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    seed = spec.confirmation_seed if registration["phase"] == "confirmation" else spec.master_seed
    replayed = maintenance_score(
        deserialize_genome(archived["selected"]),
        archived["task"],
        kernel,
        spec,
        archived["arm"],
        archived["population_index"],
        spec.generations,
        registration["phase"],
        seed=seed,
    )
    return {
        "population_id": population_id,
        "matches": canonical_digest(replayed)
        == canonical_digest(archived["selected_selection_score"]),
        "replayed_score": replayed,
    }


__all__ = (
    "maintenance_score",
    "replay_maintenance_population",
    "run_maintenance_evolution",
    "verify_maintenance_evolution",
)
