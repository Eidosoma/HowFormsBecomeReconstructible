"""Matched depth/breadth evolution for Wagner PH interpreter robustness."""

from __future__ import annotations

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
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .rng import rng_for
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import (
    deserialize_genotype,
    genotype_id,
    run_cooption_evolution,
    serialize_genotype,
    training_score,
    verify_cooption_evolution,
)
from .wagner_ph_depth_config import (
    DEPTH_ARMS,
    DEPTH_EVOLUTION_FORMAT,
    InterpreterDepthSpec,
    arm_settings,
)
from .wagner_ph_depth_mechanisms import Genotype, mutate_for_arm


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def mutation_family(arm: str) -> str:
    return f"weight-{arm_settings(arm)['weight_mutation']}.carrier-independent"


def _focal_score(
    genotype: Genotype,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: InterpreterDepthSpec,
    task_index: int,
    generation: int,
    seed: str,
    panel_indices: tuple[int, ...] | None,
) -> dict[str, Any]:
    return training_score(
        genotype,
        task,
        kernel,
        "direct_independent",
        task_index,
        generation,
        panel_indices=panel_indices,
        stream="interpreter-depth-performance-training",
        master_seed=seed,
        predictive_persistence=spec.predictive_persistence,
    )


def depth_score(
    genotype: Genotype,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: InterpreterDepthSpec,
    arm: str,
    task_index: int,
    generation: int,
    *,
    seed: str | None = None,
    panel_indices: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    """Score only observable function, optionally over a mutant lineage."""

    settings = arm_settings(arm)
    selected_seed = seed or spec.master_seed
    focal = _focal_score(
        genotype, task, kernel, spec, task_index, generation, selected_seed, panel_indices
    )
    if settings["selection_mode"] == "individual":
        return {
            "selection_mode": "individual",
            "fitness": focal["fitness"],
            "performance": focal["performance"],
            "resource_cost": focal["resource_cost"],
            "focal_score": focal,
            "virtual_descendants": [],
            "virtual_children": 0,
            "virtual_grandchildren": 0,
            "fitness_contains_memory_information_or_intervention_metric": False,
        }

    token = genotype_id(*genotype)
    descendants: list[dict[str, Any]] = []
    children: list[Genotype] = []
    for child_index in range(int(settings["virtual_children"])):
        child = mutate_for_arm(
            genotype,
            genotype,
            arm,
            rng_for(
                selected_seed,
                "interpreter-depth-virtual-child",
                mutation_family(arm),
                task_index,
                generation,
                token,
                child_index,
            ),
            local_sigma=spec.local_weight_sigma,
        )
        children.append(child)
        score = _focal_score(
            child, task, kernel, spec, task_index, generation, selected_seed, panel_indices
        )
        descendants.append({
            "pedigree_generation": 1,
            "child_index": child_index,
            "grandchild_index": None,
            "genotype_id": genotype_id(*child),
            "fitness": score["fitness"],
            "performance": score["performance"],
            "resource_cost": score["resource_cost"],
        })
    for child_index, child in enumerate(children):
        for grandchild_index in range(int(settings["virtual_grandchildren_per_child"])):
            grandchild = mutate_for_arm(
                child,
                child,
                arm,
                rng_for(
                    selected_seed,
                    "interpreter-depth-virtual-grandchild",
                    mutation_family(arm),
                    task_index,
                    generation,
                    token,
                    child_index,
                    grandchild_index,
                ),
                local_sigma=spec.local_weight_sigma,
            )
            score = _focal_score(
                grandchild,
                task,
                kernel,
                spec,
                task_index,
                generation,
                selected_seed,
                panel_indices,
            )
            descendants.append({
                "pedigree_generation": 2,
                "child_index": child_index,
                "grandchild_index": grandchild_index,
                "genotype_id": genotype_id(*grandchild),
                "fitness": score["fitness"],
                "performance": score["performance"],
                "resource_cost": score["resource_cost"],
            })
    return {
        "selection_mode": settings["selection_mode"],
        "fitness": float(np.mean([value["fitness"] for value in descendants])),
        "performance": float(np.mean([value["performance"] for value in descendants])),
        "resource_cost": float(np.mean([value["resource_cost"] for value in descendants])),
        "focal_score": focal,
        "virtual_descendants": descendants,
        "virtual_children": len(children),
        "virtual_grandchildren": sum(value["pedigree_generation"] == 2 for value in descendants),
        "fitness_contains_memory_information_or_intervention_metric": False,
    }


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(
    args: tuple[str, str, dict[str, Any], dict[str, Any], str, str, str, str]
) -> dict[str, Any]:
    (
        source_text,
        arm,
        spec_value,
        kernel_value,
        output_text,
        protocol_digest,
        phase,
        seed,
    ) = args
    source = read_json(Path(source_text))
    spec = InterpreterDepthSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(source["population_index"])
    population_id = f"{arm}.population-{task_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"interpreter-depth evolution registration differs: {final_path}")
    checkpoint_path = output / f"{population_id}.checkpoint.json"
    if checkpoint_path.is_file():
        saved = read_json(checkpoint_path)
        if saved.get("protocol_digest") != protocol_digest:
            raise ValueError("interpreter-depth checkpoint protocol differs")
        population = [deserialize_genotype(value) for value in saved["population"]]
        lineage_ids = [str(value) for value in saved["lineage_ids"]]
        scores = [dict(value) for value in saved["scores"]]
        ancestry = list(saved["ancestry"])
        trace = list(saved["trace"])
        start_generation = int(saved["generation"]) + 1
    else:
        population = [deserialize_genotype(value) for value in source["final_population"]]
        if len(population) != spec.population_size:
            raise ValueError("sealed source population has unexpected size")
        scores = [
            depth_score(value, source["task"], kernel, spec, arm, task_index, 0, seed=seed)
            for value in population
        ]
        lineage_ids = [
            canonical_digest((phase, population_id, 0, index, genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry = [{
            "generation": 0,
            "source_parent_generation": int(source["trace"][-1]["generation"]),
            "individuals": [
                {
                    "lineage_id": lineage_ids[index],
                    "parent_ids": [source["final_population"][index].get("genotype_id")],
                    "sealed_source_genotype_id": source["final_population"][index].get("genotype_id"),
                    **serialize_genotype(*value),
                    "selection_score": scores[index],
                }
                for index, value in enumerate(population)
            ],
        }]
        trace = []
        start_generation = 1

    def trace_item(generation: int) -> dict[str, Any]:
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        best = int(np.argmax(fitness))
        carriers = [value[1] for value in population]
        return {
            "generation": generation,
            "selection_mode": arm_settings(arm)["selection_mode"],
            "weight_mutation": arm_settings(arm)["weight_mutation"],
            "mean_selection_fitness": float(np.mean(fitness)),
            "best_selection_fitness": float(np.max(fitness)),
            "mean_selected_objective_performance": float(np.mean([value["performance"] for value in scores])),
            "best_focal_performance": float(scores[best]["focal_score"]["performance"]),
            "mean_focal_performance": float(np.mean([value["focal_score"]["performance"] for value in scores])),
            "mean_capacity": float(np.mean([value.k for value in carriers])),
            "mean_precision": float(np.mean([value.bits_per_mark for value in carriers])),
            "writer_active_fraction": float(np.mean([value.write_rate > 0.0 for value in carriers])),
            "reader_active_fraction": float(np.mean([value.coupling > 0.0 for value in carriers])),
        }

    if not trace:
        trace.append(trace_item(0))
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(seed, "interpreter-depth-generation", mutation_family(arm), task_index, generation)
        following: list[Genotype] = []
        parents: list[tuple[str, ...]] = []
        elites = sorted(range(len(population)), key=lambda index: (-fitness[index], index))[:spec.elite_count]
        for index in elites:
            following.append(population[index])
            parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            left = _tournament(fitness, random, spec.tournament_size)
            right = _tournament(fitness, random, spec.tournament_size)
            following.append(
                mutate_for_arm(
                    population[left], population[right], arm, random,
                    local_sigma=spec.local_weight_sigma,
                )
            )
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [
            depth_score(value, source["task"], kernel, spec, arm, task_index, generation, seed=seed)
            for value in population
        ]
        lineage_ids = [
            canonical_digest((phase, population_id, generation, index, genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry.append({
            "generation": generation,
            "individuals": [
                {
                    "lineage_id": lineage_ids[index],
                    "parent_ids": list(parents[index]),
                    **serialize_genotype(*value),
                    "selection_score": scores[index],
                }
                for index, value in enumerate(population)
            ],
        })
        trace.append(trace_item(generation))
        _atomic_json(checkpoint_path, {
            "format": f"{DEPTH_EVOLUTION_FORMAT}-checkpoint",
            "protocol_digest": protocol_digest,
            "generation": generation,
            "population": [serialize_genotype(*value) for value in population],
            "lineage_ids": lineage_ids,
            "scores": scores,
            "ancestry": ancestry,
            "trace": trace,
        })
    final_fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
    selected_index = int(np.argmax(final_fitness))
    result = {
        "format": DEPTH_EVOLUTION_FORMAT,
        "protocol_digest": protocol_digest,
        "phase": phase,
        "population_id": population_id,
        "population_index": task_index,
        "arm": arm,
        "arm_settings": arm_settings(arm),
        "mutation_family": mutation_family(arm),
        "task": source["task"],
        "task_is_paired_across_all_arms": True,
        "sealed_source_population_id": source["population_id"],
        "sealed_source_result_digest": source["result_digest"],
        "fitness_contains_only_observable_performance_and_ordinary_resource_cost": True,
        "fitness_contains_memory_information_intervention_or_renewal_metric": False,
        "selected": serialize_genotype(*population[selected_index]),
        "selected_selection_score": scores[selected_index],
        "selected_training_score": scores[selected_index]["focal_score"],
        "final_population": [
            {
                **serialize_genotype(*value),
                "selection_score": scores[index],
                "focal_training_score": scores[index]["focal_score"],
            }
            for index, value in enumerate(population)
        ],
        "trace": trace,
        "ancestry": ancestry,
    }
    result["result_digest"] = canonical_digest({
        "selected": result["selected"],
        "selected_selection_score": result["selected_selection_score"],
        "trace": trace,
    })
    _atomic_json(final_path, result)
    if checkpoint_path.is_file():
        checkpoint_path.unlink()
    return result


def run_confirmation_burnin(
    spec: InterpreterDepthSpec,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Generate fresh tasks and common predictive ancestors only after nomination."""

    kernel = spec.kernel(confirmation=True)
    burnin = replace(
        kernel,
        generations=spec.confirmation_burnin_generations,
        cooption_switch_generation=max(1, min(kernel.cooption_switch_generation, spec.confirmation_burnin_generations - 1)),
    )
    burnin.validate()
    return run_cooption_evolution(
        burnin,
        destination,
        workers,
        progress,
        treatments=("direct_independent",),
        task_count=spec.confirmation_task_count,
        master_seed=spec.confirmation_seed,
        predictive_persistence=spec.predictive_persistence,
    )


def run_depth_evolution(
    spec: InterpreterDepthSpec,
    source: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    phase: str = "development",
    selected_arms: tuple[str, ...] | None = None,
) -> Path:
    spec.validate()
    if phase not in {"development", "confirmation"}:
        raise ValueError("interpreter-depth evolution phase must be development or confirmation")
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("interpreter-depth evolution permits one to four CPU workers")
    arms = selected_arms or spec.arms
    if not arms or len(set(arms)) != len(arms) or not set(arms) <= set(spec.arms):
        raise ValueError("invalid interpreter-depth arm subset")
    source = source.resolve()
    source_checksum = sha256_file(source / "SHA256SUMS")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_depth_evolution(destination)
        return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = spec.confirmation_seed if phase == "confirmation" else spec.master_seed
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "source_checksum": source_checksum,
        "phase": phase,
        "selected_arms": list(arms),
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": f"{DEPTH_EVOLUTION_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **payload,
        "source": str(source),
        "all_arms_continue_complete_common_populations": True,
        "virtual_descendants_are_resampled_deterministically_by_genotype": True,
        "memory_labels_information_interventions_and_renewal_are_absent_from_fitness": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing interpreter-depth evolution registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    source_pattern = (
        "direct_independent.population-*.json"
        if phase == "confirmation" else "individual_independent.population-*.json"
    )
    source_files = sorted((source / "populations").glob(source_pattern))
    if len(source_files) != task_count:
        raise ValueError("interpreter-depth source task count mismatch")
    work = [
        (str(path), arm, spec.to_dict(), kernel.to_dict(), str(populations), protocol_digest, phase, seed)
        for arm in arms for path in source_files
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
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(destination / "progress.json", {
                "format": f"{DEPTH_EVOLUTION_FORMAT}-progress",
                "phase": phase,
                "completed_populations": index,
                "total_populations": len(work),
                "elapsed_seconds": elapsed,
                "populations_per_second": rate,
                "eta_seconds": (len(work) - index) / rate if rate else None,
            })
            if progress:
                progress(f"interpreter-depth {phase} evolution {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (arms.index(value["arm"]), value["population_index"]))
    _atomic_json(destination / "manifest.json", {
        "format": f"{DEPTH_EVOLUTION_FORMAT}-manifest",
        "protocol_digest": protocol_digest,
        "phase": phase,
        "selected_arms": list(arms),
        "population_count": len(completed),
        "expected_population_count": len(arms) * task_count,
        "workers": workers,
        "elapsed_seconds": time.monotonic() - started,
        "scientific_result_digest": canonical_digest([
            value["result_digest"] for value in completed
        ]),
        "runtime": runtime_manifest(),
    })
    write_checksums(destination)
    verify_depth_evolution(destination)
    return destination


def verify_depth_evolution(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != f"{DEPTH_EVOLUTION_FORMAT}-registration":
        raise ValueError("interpreter-depth evolution registration format mismatch")
    spec = InterpreterDepthSpec.from_dict(registration["spec"])
    source = Path(registration["source"])
    if sha256_file(source / "SHA256SUMS") != registration["source_checksum"]:
        raise ValueError("sealed source changed after interpreter-depth evolution")
    payload = {
        "spec": spec.to_dict(),
        "kernel": registration["kernel"],
        "source_checksum": registration["source_checksum"],
        "phase": registration["phase"],
        "selected_arms": registration["selected_arms"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("interpreter-depth evolution protocol digest mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    arms = tuple(registration["selected_arms"])
    files = sorted(
        path for path in (directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    if len(files) != len(arms) * task_count or int(manifest["population_count"]) != len(files):
        raise ValueError("interpreter-depth evolution population count mismatch")
    values = [read_json(path) for path in files]
    for value in values:
        if value.get("protocol_digest") != digest:
            raise ValueError("interpreter-depth population protocol mismatch")
        if value["arm"] not in arms or len(value["final_population"]) != spec.population_size:
            raise ValueError("interpreter-depth population payload mismatch")
        if value["fitness_contains_memory_information_intervention_or_renewal_metric"]:
            raise ValueError("forbidden PH-derived metric entered fitness")
    ordered = sorted(values, key=lambda value: (arms.index(value["arm"]), value["population_index"]))
    if manifest["scientific_result_digest"] != canonical_digest([value["result_digest"] for value in ordered]):
        raise ValueError("interpreter-depth evolution result digest mismatch")
    return {"verified": True, "phase": registration["phase"], "populations": len(files), "checksums": len(checksums)}


def replay_depth_population(directory: Path, population_id: str) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = InterpreterDepthSpec.from_dict(registration["spec"])
    kernel = CooptionSpec.from_dict(registration["kernel"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    genotype = deserialize_genotype(archived["selected"])
    phase = str(registration["phase"])
    seed = spec.confirmation_seed if phase == "confirmation" else spec.master_seed
    replayed = depth_score(
        genotype,
        archived["task"],
        kernel,
        spec,
        archived["arm"],
        int(archived["population_index"]),
        spec.generations,
        seed=seed,
    )
    matches = canonical_digest(replayed) == canonical_digest(archived["selected_selection_score"])
    return {"population_id": population_id, "matches": matches, "replayed_score": replayed}
