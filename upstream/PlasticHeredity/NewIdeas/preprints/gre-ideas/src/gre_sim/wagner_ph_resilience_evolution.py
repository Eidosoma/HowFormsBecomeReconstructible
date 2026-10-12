"""Outcome-only resilience evolution with lower-tail descendant selection."""

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
from .wagner_ph_cooption_evolution import deserialize_genotype as deserialize_base_genotype, training_score
from .wagner_ph_resilience_config import REFERENCE_ARMS, RESILIENCE_ARMS, RESILIENCE_FORMAT, ResilienceSpec, arm_settings
from .wagner_ph_resilience_genome import (
    Genome,
    architecture_cost,
    deserialize_genome,
    effective_genotype,
    genome_id,
    initialize_interpreter,
    mutate_genome,
    serialize_genome,
)


EVOLUTION_FORMAT = f"{RESILIENCE_FORMAT}-evolution"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _initial_genome(
    value: dict[str, Any], arm: str, task_index: int, individual_index: int,
    spec: ResilienceSpec, initialization_seed: str,
) -> Genome:
    rulebook, carrier = deserialize_base_genotype(value)
    architecture = arm_settings(arm)["architecture"]
    repair = 0.0
    if architecture == "repair":
        permutation = rng_for(initialization_seed, "repair-standing-variation", task_index).permutation(spec.population_size)
        position = int(np.where(permutation == individual_index)[0][0])
        repair = (0.0, 0.3, 0.6, 0.9)[position % 4]
    return initialize_interpreter(rulebook, architecture, repair), carrier


def _focal_score(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: ResilienceSpec,
    task_index: int,
    generation: int,
    seed: str,
) -> dict[str, Any]:
    base = training_score(
        effective_genotype(genome),
        task,
        kernel,
        "direct_independent",
        task_index,
        generation,
        stream="interpreter-resilience-performance-training",
        master_seed=seed,
        predictive_persistence=spec.predictive_persistence,
    )
    extra = architecture_cost(genome[0], spec)
    return {
        **base,
        "fitness": float(base["fitness"] - extra),
        "resource_cost": float(base["resource_cost"] + extra),
        "resilience_architecture_cost": extra,
        "repair_strength": genome[0].repair_strength,
        "interpreter_architecture": genome[0].architecture,
    }


def resilience_score(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: ResilienceSpec,
    arm: str,
    task_index: int,
    generation: int,
    *,
    seed: str | None = None,
) -> dict[str, Any]:
    """Score observable development only, never an information or PH assay."""

    selected_seed = seed or spec.master_seed
    mode = arm_settings(arm)["selection_mode"]
    focal = _focal_score(genome, task, kernel, spec, task_index, generation, selected_seed)
    if mode == "individual":
        descendants: list[dict[str, Any]] = []
        selected = [focal]
    elif mode in {"cvar8", "mean8"}:
        descendants = []
        for child_index in range(8):
            child = mutate_genome(
                genome,
                genome,
                arm,
                rng_for(
                    selected_seed,
                    "interpreter-resilience-cvar8",
                    arm,
                    task_index,
                    generation,
                    genome_id(genome),
                    child_index,
                ),
                spec,
            )
            score = _focal_score(child, task, kernel, spec, task_index, generation, selected_seed)
            descendants.append({
                "lineage_index": child_index,
                "distance": 1,
                "genotype_id": genome_id(child),
                **score,
            })
        selected = (
            descendants
            if mode == "mean8"
            else sorted(descendants, key=lambda value: (value["fitness"], value["genotype_id"]))[:2]
        )
    else:
        descendants = []
        for lineage_index in range(4):
            current = genome
            for distance in range(1, 5):
                current = mutate_genome(
                    current,
                    current,
                    arm,
                    rng_for(
                        selected_seed,
                        "interpreter-resilience-lineage4",
                        arm,
                        task_index,
                        generation,
                        genome_id(genome),
                        lineage_index,
                        distance,
                    ),
                    spec,
                )
            score = _focal_score(current, task, kernel, spec, task_index, generation, selected_seed)
            descendants.append({
                "lineage_index": lineage_index,
                "distance": 4,
                "genotype_id": genome_id(current),
                **score,
            })
        selected = sorted(descendants, key=lambda value: (value["fitness"], value["genotype_id"]))[:2]
    return {
        "selection_mode": mode,
        "fitness": float(np.mean([value["fitness"] for value in selected])),
        "performance": float(np.mean([value["performance"] for value in selected])),
        "resource_cost": float(np.mean([value["resource_cost"] for value in selected])),
        "focal_score": focal,
        "virtual_descendants": descendants,
        "selected_tail_size": len(selected),
        "fitness_contains_memory_information_intervention_or_ph_metric": False,
    }


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(args: tuple[str, str, dict[str, Any], dict[str, Any], str, str, str, str]) -> dict[str, Any]:
    source_text, arm, spec_value, kernel_value, output_text, protocol_digest, phase, seed = args
    source = read_json(Path(source_text))
    spec = ResilienceSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(source["population_index"])
    population_id = f"{arm}.population-{task_index:03d}"
    final_path = Path(output_text) / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"resilience population registration differs: {final_path}")
    checkpoint = final_path.with_name(f"{population_id}.checkpoint.json")
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        if saved.get("protocol_digest") != protocol_digest:
            raise ValueError("resilience checkpoint protocol differs")
        population = [deserialize_genome(value) for value in saved["population"]]
        lineage_ids = list(saved["lineage_ids"])
        scores = list(saved["scores"])
        trace = list(saved["trace"])
        ancestry = list(saved["ancestry"])
        start_generation = int(saved["generation"]) + 1
    else:
        source_population = source["final_population"][:spec.population_size]
        population = [
            _initial_genome(value, arm, task_index, index, spec, seed)
            for index, value in enumerate(source_population)
        ]
        if len(population) != spec.population_size:
            raise ValueError("resilience source population has unexpected size")
        scores = [resilience_score(value, source["task"], kernel, spec, arm, task_index, 0, seed=seed) for value in population]
        lineage_ids = [canonical_digest((phase, population_id, 0, index, genome_id(value)))[:24] for index, value in enumerate(population)]
        trace, ancestry, start_generation = [], [], 1

    def trace_item(generation: int) -> dict[str, Any]:
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        return {
            "generation": generation,
            "mean_selection_fitness": float(np.mean(fitness)),
            "best_selection_fitness": float(np.max(fitness)),
            "mean_focal_performance": float(np.mean([value["focal_score"]["performance"] for value in scores])),
            "mean_repair_strength": float(np.mean([value[0].repair_strength for value in population])),
            "interpreter_architecture": population[0][0].architecture,
        }

    if not trace:
        trace.append(trace_item(0))
        ancestry.append({"generation": 0, "individuals": [
            {"lineage_id": lineage_ids[index], **serialize_genome(value), "selection_score": scores[index]}
            for index, value in enumerate(population)
        ]})
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(seed, "interpreter-resilience-generation", arm, task_index, generation)
        following: list[Genome] = []
        parents: list[tuple[str, ...]] = []
        elites = sorted(range(len(population)), key=lambda index: (-fitness[index], index))[:spec.elite_count]
        for index in elites:
            following.append(population[index])
            parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            left = _tournament(fitness, random, spec.tournament_size)
            right = _tournament(fitness, random, spec.tournament_size)
            following.append(mutate_genome(population[left], population[right], arm, random, spec))
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [resilience_score(value, source["task"], kernel, spec, arm, task_index, generation, seed=seed) for value in population]
        lineage_ids = [canonical_digest((phase, population_id, generation, index, genome_id(value)))[:24] for index, value in enumerate(population)]
        ancestry.append({"generation": generation, "individuals": [
            {"lineage_id": lineage_ids[index], "parent_ids": list(parents[index]), **serialize_genome(value), "selection_score": scores[index]}
            for index, value in enumerate(population)
        ]})
        trace.append(trace_item(generation))
        _atomic_json(checkpoint, {
            "protocol_digest": protocol_digest,
            "generation": generation,
            "population": [serialize_genome(value) for value in population],
            "lineage_ids": lineage_ids,
            "scores": scores,
            "trace": trace,
            "ancestry": ancestry,
        })
    best = int(np.argmax(np.asarray([value["fitness"] for value in scores], dtype=float)))
    result = {
        "format": EVOLUTION_FORMAT,
        "protocol_digest": protocol_digest,
        "phase": phase,
        "population_id": population_id,
        "population_index": task_index,
        "arm": arm,
        "arm_settings": arm_settings(arm),
        "task": source["task"],
        "selected": serialize_genome(population[best]),
        "selected_effective_genotype": serialize_genome(population[best])["effective_genotype"],
        "selected_selection_score": scores[best],
        "selected_training_score": scores[best]["focal_score"],
        "final_population": [
            {**serialize_genome(value), "selection_score": scores[index], "focal_training_score": scores[index]["focal_score"]}
            for index, value in enumerate(population)
        ],
        "trace": trace,
        "ancestry": ancestry,
        "fitness_contains_only_observable_performance_and_resource_cost": True,
        "fitness_contains_memory_information_intervention_or_ph_metric": False,
    }
    result["result_digest"] = canonical_digest({"selected": result["selected"], "score": scores[best], "trace": trace})
    _atomic_json(final_path, result)
    if checkpoint.is_file():
        checkpoint.unlink()
    return result


def run_resilience_evolution(
    spec: ResilienceSpec,
    source: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
    *,
    phase: str = "development",
    selected_arms: tuple[str, ...] | None = None,
) -> Path:
    spec.validate()
    if phase not in {"development", "confirmation"} or not 1 <= workers <= spec.maximum_workers:
        raise ValueError("invalid resilience phase or worker count")
    arms = selected_arms or spec.arms
    if not arms or not set(arms) <= set(RESILIENCE_ARMS + REFERENCE_ARMS):
        raise ValueError("invalid resilience arm subset")
    source = source.resolve()
    source_checksum = sha256_file(source / "SHA256SUMS")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_resilience_evolution(destination)
        return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = spec.confirmation_seed if phase == "confirmation" else spec.master_seed
    payload = {"spec": spec.to_dict(), "kernel": kernel.to_dict(), "source_checksum": source_checksum, "phase": phase, "selected_arms": list(arms)}
    digest = canonical_digest(payload)
    registration = {"format": f"{EVOLUTION_FORMAT}-registration", "protocol_digest": digest, **payload, "source": str(source), "selection_excludes_all_ph_metrics": True}
    if (destination / "registration.json").is_file() and read_json(destination / "registration.json") != registration:
        raise ValueError("existing resilience evolution registration differs")
    if not (destination / "registration.json").is_file():
        _atomic_json(destination / "registration.json", registration)
    shards = destination / "populations"
    shards.mkdir(exist_ok=True)
    pattern = "direct_independent.population-*.json" if phase == "confirmation" else "individual_independent.population-*.json"
    source_files = sorted((source / "populations").glob(pattern))
    if len(source_files) < task_count:
        raise ValueError("resilience source task count mismatch")
    source_files = source_files[:task_count]
    work = [(str(path), arm, spec.to_dict(), kernel.to_dict(), str(shards), digest, phase, seed) for arm in arms for path in source_files]
    started = time.monotonic()
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
        futures = [executor.submit(_population_task, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, 1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(destination / "progress.json", {"completed_populations": index, "total_populations": len(work), "elapsed_seconds": elapsed, "eta_seconds": (len(work)-index)/rate})
            if progress:
                progress(f"interpreter-resilience {phase} evolution {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (arms.index(value["arm"]), value["population_index"]))
    _atomic_json(destination / "manifest.json", {
        "format": f"{EVOLUTION_FORMAT}-manifest", "protocol_digest": digest, "phase": phase,
        "selected_arms": list(arms), "population_count": len(completed), "workers": workers,
        "elapsed_seconds": time.monotonic()-started,
        "scientific_result_digest": canonical_digest([value["result_digest"] for value in completed]),
        "runtime": runtime_manifest(),
    })
    write_checksums(destination)
    verify_resilience_evolution(destination)
    return destination


def verify_resilience_evolution(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = ResilienceSpec.from_dict(registration["spec"])
    if sha256_file(Path(registration["source"]) / "SHA256SUMS") != registration["source_checksum"]:
        raise ValueError("sealed resilience source changed")
    payload = {key: registration[key] for key in ("spec", "kernel", "source_checksum", "phase", "selected_arms")}
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("resilience evolution protocol mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    files = sorted(path for path in (directory / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json"))
    expected = task_count * len(registration["selected_arms"])
    if len(files) != expected or manifest["population_count"] != expected:
        raise ValueError("resilience evolution is incomplete")
    values = [read_json(path) for path in files]
    if any(value["fitness_contains_memory_information_intervention_or_ph_metric"] for value in values):
        raise ValueError("forbidden PH metric entered resilience fitness")
    ordered = sorted(values, key=lambda value: (registration["selected_arms"].index(value["arm"]), value["population_index"]))
    if manifest["scientific_result_digest"] != canonical_digest([value["result_digest"] for value in ordered]):
        raise ValueError("resilience evolution result digest mismatch")
    return {"verified": True, "phase": registration["phase"], "populations": len(files), "checksums": len(checksums)}


def replay_resilience_population(directory: Path, population_id: str) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = ResilienceSpec.from_dict(registration["spec"])
    kernel = CooptionSpec.from_dict(registration["kernel"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    seed = spec.confirmation_seed if registration["phase"] == "confirmation" else spec.master_seed
    replayed = resilience_score(
        deserialize_genome(archived["selected"]), archived["task"], kernel, spec,
        archived["arm"], archived["population_index"], spec.generations, seed=seed,
    )
    return {"population_id": population_id, "matches": canonical_digest(replayed) == canonical_digest(archived["selected_selection_score"]), "replayed_score": replayed}
