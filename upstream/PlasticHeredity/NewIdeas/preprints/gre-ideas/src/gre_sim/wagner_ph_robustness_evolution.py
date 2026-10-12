"""Continuation evolution selecting either individuals or their ordinary mutant offspring."""

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
from .wagner_ph_cooption_evolution import (
    deserialize_genotype,
    genotype_id,
    serialize_genotype,
    training_score,
)
from .wagner_ph_direct_campaign import verify_wagner_ph_direct_prediction_campaign
from .wagner_ph_robustness_config import (
    ROBUSTNESS_ARMS,
    ROBUSTNESS_EVOLUTION_FORMAT,
    RobustnessSpec,
    arm_settings,
)
from .wagner_ph_robustness_mechanisms import Genotype, initialize_for_arm, mutate_for_arm


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def mutation_family(arm: str) -> str:
    settings = arm_settings(arm)
    constraint = settings["carrier_constraint"] or "full"
    return (
        f"{settings['mutation_architecture']}."
        f"carrier-p{settings['carrier_mutation_multiplier']:.2f}.{constraint}"
    )


def robustness_score(
    genotype: Genotype,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: RobustnessSpec,
    arm: str,
    task_index: int,
    generation: int,
    *,
    panel_indices: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    """Score observable performance only, optionally averaged over mutant children."""

    settings = arm_settings(arm)
    focal = training_score(
        genotype,
        task,
        kernel,
        "direct_independent",
        task_index,
        generation,
        panel_indices=panel_indices,
        stream="robustness-performance-training",
        master_seed=spec.master_seed,
        predictive_persistence=spec.predictive_persistence,
    )
    if settings["selection_mode"] == "individual":
        return {
            "selection_mode": "individual",
            "fitness": focal["fitness"],
            "performance": focal["performance"],
            "resource_cost": focal["resource_cost"],
            "focal_score": focal,
            "virtual_offspring": [],
            "virtual_offspring_count": 0,
            "fitness_contains_memory_information_or_intervention_metric": False,
        }
    token = genotype_id(*genotype)
    descendants: list[dict[str, Any]] = []
    for child_index in range(spec.virtual_offspring):
        child = mutate_for_arm(
            genotype,
            genotype,
            arm,
            rng_for(
                spec.master_seed,
                "robustness-virtual-offspring",
                mutation_family(arm),
                task_index,
                generation,
                token,
                child_index,
            ),
        )
        child_score = training_score(
            child,
            task,
            kernel,
            "direct_independent",
            task_index,
            generation,
            panel_indices=panel_indices,
            stream="robustness-performance-training",
            master_seed=spec.master_seed,
            predictive_persistence=spec.predictive_persistence,
        )
        descendants.append(
            {
                "child_index": child_index,
                "genotype_id": genotype_id(*child),
                "fitness": child_score["fitness"],
                "performance": child_score["performance"],
                "resource_cost": child_score["resource_cost"],
            }
        )
    return {
        "selection_mode": "offspring",
        "fitness": float(np.mean([value["fitness"] for value in descendants])),
        "performance": float(np.mean([value["performance"] for value in descendants])),
        "resource_cost": float(np.mean([value["resource_cost"] for value in descendants])),
        "focal_score": focal,
        "virtual_offspring": descendants,
        "virtual_offspring_count": len(descendants),
        "fitness_contains_memory_information_or_intervention_metric": False,
    }


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(
    args: tuple[str, str, dict[str, Any], dict[str, Any], str, str]
) -> dict[str, Any]:
    parent_text, arm, spec_value, kernel_value, output_text, protocol_digest = args
    parent = read_json(Path(parent_text))
    spec = RobustnessSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(parent["population_index"])
    population_id = f"{arm}.population-{task_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"robustness evolution registration differs: {final_path}")
    checkpoint_path = output / f"{population_id}.checkpoint.json"
    if checkpoint_path.is_file():
        saved = read_json(checkpoint_path)
        if saved.get("protocol_digest") != protocol_digest:
            raise ValueError("robustness evolution checkpoint protocol differs")
        population = [deserialize_genotype(value) for value in saved["population"]]
        lineage_ids = [str(value) for value in saved["lineage_ids"]]
        scores = [dict(value) for value in saved["scores"]]
        ancestry = list(saved["ancestry"])
        trace = list(saved["trace"])
        start_generation = int(saved["generation"]) + 1
    else:
        source = [deserialize_genotype(value) for value in parent["final_population"]]
        if len(source) != spec.population_size:
            raise ValueError("sealed source population has unexpected size")
        population = [initialize_for_arm(value, arm) for value in source]
        scores = [
            robustness_score(value, parent["task"], kernel, spec, arm, task_index, 0)
            for value in population
        ]
        lineage_ids = [
            canonical_digest((population_id, 0, index, genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry = [
            {
                "generation": 0,
                "source_parent_generation": 30 if spec.task_count > 1 else 2,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        "parent_ids": [parent["final_population"][index].get("genotype_id")],
                        "sealed_source_genotype_id": parent["final_population"][index].get(
                            "genotype_id"
                        ),
                        **serialize_genotype(*value),
                        "selection_score": scores[index],
                    }
                    for index, value in enumerate(population)
                ],
            }
        ]
        trace = []
        start_generation = 1

    def trace_item(generation: int) -> dict[str, Any]:
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        best = int(np.argmax(fitness))
        carrier_values = [value[1] for value in population]
        return {
            "generation": generation,
            "selection_mode": arm_settings(arm)["selection_mode"],
            "mean_selection_fitness": float(np.mean(fitness)),
            "best_selection_fitness": float(np.max(fitness)),
            "mean_selected_objective_performance": float(
                np.mean([value["performance"] for value in scores])
            ),
            "best_focal_performance": float(scores[best]["focal_score"]["performance"]),
            "mean_focal_performance": float(
                np.mean([value["focal_score"]["performance"] for value in scores])
            ),
            "mean_capacity": float(np.mean([value.k for value in carrier_values])),
            "mean_precision": float(np.mean([value.bits_per_mark for value in carrier_values])),
            "writer_active_fraction": float(
                np.mean([value.write_rate > 0.0 for value in carrier_values])
            ),
            "reader_active_fraction": float(
                np.mean([value.coupling > 0.0 for value in carrier_values])
            ),
        }

    if not trace:
        trace.append(trace_item(0))
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(
            spec.master_seed,
            "robustness-generation",
            mutation_family(arm),
            task_index,
            generation,
        )
        following: list[Genotype] = []
        parents: list[tuple[str, ...]] = []
        elites = sorted(range(len(population)), key=lambda index: (-fitness[index], index))[
            : spec.elite_count
        ]
        for index in elites:
            following.append(population[index])
            parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            left = _tournament(fitness, random, spec.tournament_size)
            right = _tournament(fitness, random, spec.tournament_size)
            following.append(mutate_for_arm(population[left], population[right], arm, random))
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [
            robustness_score(
                value, parent["task"], kernel, spec, arm, task_index, generation
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest((population_id, generation, index, genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry.append(
            {
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
            }
        )
        trace.append(trace_item(generation))
        _atomic_json(
            checkpoint_path,
            {
                "format": f"{ROBUSTNESS_EVOLUTION_FORMAT}-checkpoint",
                "protocol_digest": protocol_digest,
                "generation": generation,
                "population": [serialize_genotype(*value) for value in population],
                "lineage_ids": lineage_ids,
                "scores": scores,
                "ancestry": ancestry,
                "trace": trace,
            },
        )
    final_fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
    selected_index = int(np.argmax(final_fitness))
    result = {
        "format": ROBUSTNESS_EVOLUTION_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "population_index": task_index,
        "arm": arm,
        "arm_settings": arm_settings(arm),
        "mutation_family": mutation_family(arm),
        "task": parent["task"],
        "task_is_paired_across_all_arms": True,
        "sealed_source_population_id": parent["population_id"],
        "sealed_source_result_digest": parent["result_digest"],
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
    result["result_digest"] = canonical_digest(
        {
            "selected": result["selected"],
            "selected_selection_score": result["selected_selection_score"],
            "trace": trace,
        }
    )
    _atomic_json(final_path, result)
    if checkpoint_path.is_file():
        checkpoint_path.unlink()
    return result


def run_robustness_evolution(
    spec: RobustnessSpec,
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("robustness evolution permits one to four CPU workers")
    parent = parent.resolve()
    verify_wagner_ph_direct_prediction_campaign(parent)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_robustness_evolution(destination)
        return destination
    started = time.monotonic()
    kernel = spec.kernel()
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "direct_parent_checksum": sha256_file(parent / "SHA256SUMS"),
        "source_evolution_checksum": sha256_file(
            parent / "evolution" / spec.parent_variant / "SHA256SUMS"
        ),
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": f"{ROBUSTNESS_EVOLUTION_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **payload,
        "direct_parent": str(parent),
        "source_evolution": str(parent / "evolution" / spec.parent_variant),
        "all_arms_continue_the_complete_sealed_final_populations": True,
        "virtual_offspring_are_resampled_deterministically_by_genotype": True,
        "validation_and_audit_streams_never_affect_selection": True,
        "memory_labels_information_interventions_and_renewal_are_absent_from_fitness": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing robustness-evolution registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    parent_files = sorted(
        (parent / "evolution" / spec.parent_variant / "populations").glob(
            "direct_independent.population-*.json"
        )
    )
    if len(parent_files) != spec.task_count:
        raise ValueError("sealed source task count differs from robustness contract")
    work = [
        (str(path), arm, spec.to_dict(), kernel.to_dict(), str(populations), protocol_digest)
        for arm in spec.arms
        for path in parent_files
    ]
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
            _atomic_json(
                destination / "progress.json",
                {
                    "format": f"{ROBUSTNESS_EVOLUTION_FORMAT}-progress",
                    "completed_populations": index,
                    "total_populations": len(work),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(work) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"robustness evolution {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (ROBUSTNESS_ARMS.index(value["arm"]), value["population_index"]))
    paired = all(
        len(
            {
                value["task"]["task_digest"]
                for value in completed
                if int(value["population_index"]) == task_index
            }
        )
        == 1
        for task_index in range(spec.task_count)
    )
    _atomic_json(
        destination / "analysis.json",
        {
            "format": f"{ROBUSTNESS_EVOLUTION_FORMAT}-analysis",
            "selection_data_are_not_heldout_ph_evidence": True,
            "paired_task_indices": paired,
            "population_count": len(completed),
            "arms": list(spec.arms),
        },
    )
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{ROBUSTNESS_EVOLUTION_FORMAT}-manifest",
            "protocol_digest": protocol_digest,
            "population_count": len(completed),
            "expected_population_count": spec.population_count,
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_robustness_evolution(destination)
    return destination


def verify_robustness_evolution(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != f"{ROBUSTNESS_EVOLUTION_FORMAT}-registration":
        raise ValueError("robustness-evolution registration format mismatch")
    spec = RobustnessSpec.from_dict(registration["spec"])
    parent = Path(registration["direct_parent"])
    if sha256_file(parent / "SHA256SUMS") != registration["direct_parent_checksum"]:
        raise ValueError("sealed direct parent changed after robustness evolution")
    payload = {
        "spec": spec.to_dict(),
        "kernel": registration["kernel"],
        "direct_parent_checksum": registration["direct_parent_checksum"],
        "source_evolution_checksum": registration["source_evolution_checksum"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("robustness-evolution protocol digest mismatch")
    files = sorted(
        path
        for path in (directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    if len(files) != spec.population_count or int(manifest["population_count"]) != spec.population_count:
        raise ValueError("robustness-evolution population count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"robustness population protocol mismatch: {path.name}")
        expected = canonical_digest(
            {
                "selected": value["selected"],
                "selected_selection_score": value["selected_selection_score"],
                "trace": value["trace"],
            }
        )
        if value.get("result_digest") != expected:
            raise ValueError(f"robustness population result mismatch: {path.name}")
        if value["selected_selection_score"][
            "fitness_contains_memory_information_or_intervention_metric"
        ]:
            raise ValueError("forbidden memory-derived term entered robustness fitness")
    return {"verified": True, "populations": len(files), "checksums": len(checksums)}


def replay_robustness_population(directory: Path, population_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    spec = RobustnessSpec.from_dict(registration["spec"])
    kernel = CooptionSpec.from_dict(registration["kernel"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    replayed = robustness_score(
        deserialize_genotype(archived["selected"]),
        archived["task"],
        kernel,
        spec,
        archived["arm"],
        int(archived["population_index"]),
        spec.generations,
    )
    return {
        "population_id": population_id,
        "matches": canonical_digest(replayed)
        == canonical_digest(archived["selected_selection_score"]),
        "archived_score": archived["selected_selection_score"],
        "replayed_score": replayed,
    }
