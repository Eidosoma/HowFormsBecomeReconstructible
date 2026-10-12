"""Outcome-only multi-horizon evolution for Interpreter Architecture v1."""

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
from .wagner_ph_architecture_config import (
    ARCHITECTURE_ARMS,
    ARCHITECTURE_FORMAT,
    CONTROL_ARMS,
    ArchitectureSpec,
    arm_settings,
)
from .wagner_ph_architecture_genome import (
    Genome,
    ArchitectureInterpreter,
    architecture_cost,
    deserialize_genome,
    effective_genotype,
    genome_id,
    initialize_from_source,
    mutate_genome,
    serialize_genome,
)
from .wagner_ph_architecture_predictor import predicted_edge_ranking, verify_predictor
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import training_score


EVOLUTION_FORMAT = f"{ARCHITECTURE_FORMAT}-evolution"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _initial_genome(
    value: dict[str, Any],
    arm: str,
    task_index: int,
    individual_index: int,
    spec: ArchitectureSpec,
    phase: str,
    seed: str,
) -> Genome:
    architecture = arm_settings(arm)["architecture"]
    genome = initialize_from_source(value, architecture)
    if architecture == "repair" and phase == "confirmation":
        permutation = rng_for(seed, "architecture-repair-standing-variation", task_index).permutation(spec.population_size)
        position = int(np.where(permutation == individual_index)[0][0])
        repair = (0.0, 0.3, 0.6, 0.9)[position % 4]
        genome = ArchitectureInterpreter(genome[0].copies, "repair", repair), genome[1]
    return genome


def _focal_score(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: ArchitectureSpec,
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
        stream="interpreter-architecture-performance-training",
        master_seed=seed,
        predictive_persistence=spec.predictive_persistence,
    )
    extra = architecture_cost(genome[0], spec)
    return {
        **base,
        "fitness": float(base["fitness"] - extra),
        "resource_cost": float(base["resource_cost"] + extra),
        "architecture_cost": extra,
        "repair_strength": genome[0].repair_strength,
        "interpreter_architecture": genome[0].architecture,
    }


def _challenge_edge(
    genome: Genome,
    challenge: str,
    predictor: dict[str, Any],
    task_index: int,
    phase: str,
    random: np.random.Generator,
) -> tuple[int | None, dict[str, Any] | None]:
    if challenge == "ordinary":
        return None, None
    if challenge == "uniform":
        return int(random.integers(genome[0].effective_rulebook().weights.size)), None
    ranking = predicted_edge_ranking(effective_genotype(genome)[0], genome[1], predictor, task_index, phase)
    top = ranking["top_edges"]
    return int(top[int(random.integers(len(top)))]), {
        "top_edges": top,
        "carrier_mask": ranking["carrier_mask"],
        "training_tasks": ranking["training_tasks"],
        "target_task_excluded": ranking["target_task_excluded"],
    }


def architecture_score(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: ArchitectureSpec,
    arm: str,
    task_index: int,
    generation: int,
    predictor: dict[str, Any],
    phase: str,
    *,
    seed: str | None = None,
) -> dict[str, Any]:
    """Score focal, immediate-tail, and depth-four-tail observable function."""

    selected_seed = seed or (spec.confirmation_seed if phase == "confirmation" else spec.master_seed)
    settings = arm_settings(arm)
    focal = _focal_score(genome, task, kernel, spec, task_index, generation, selected_seed)
    if settings["selection_mode"] == "individual":
        return {
            "selection_mode": "individual",
            "challenge": settings["challenge"],
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
    stable_key = canonical_digest({
        "rulebook": effective_genotype(genome)[0].uid,
        "carrier": genome[1].to_dict(),
        "repair": genome[0].repair_strength,
    })[:24]
    for lineage_index in range(4):
        current = genome
        chain = []
        for distance in range(1, 5):
            random = rng_for(
                selected_seed,
                "interpreter-architecture-virtual-lineage",
                settings["challenge"],
                task_index,
                generation,
                stable_key,
                lineage_index,
                distance,
            )
            forced_edge, ranking = _challenge_edge(
                current, settings["challenge"], predictor, task_index, phase, random
            )
            child = mutate_genome(current, current, arm, random, spec, forced_edge=forced_edge)
            record = {
                "lineage_index": lineage_index,
                "distance": distance,
                "genotype_id": genome_id(child),
                "forced_edge": forced_edge,
                "guided_ranking": ranking,
            }
            if distance in {1, 4}:
                record.update(_focal_score(child, task, kernel, spec, task_index, generation, selected_seed))
            chain.append(record)
            if distance == 1:
                immediate.append(record)
            if distance == 4:
                terminals.append(record)
            current = child
        trajectories.append({"lineage_index": lineage_index, "chain": chain})
    immediate_tail = sorted(immediate, key=lambda value: (value["fitness"], value["genotype_id"]))[:2]
    terminal_tail = sorted(terminals, key=lambda value: (value["fitness"], value["genotype_id"]))[:2]
    components = {
        "focal": float(focal["fitness"]),
        "immediate_tail": float(np.mean([value["fitness"] for value in immediate_tail])),
        "distance_four_tail": float(np.mean([value["fitness"] for value in terminal_tail])),
    }
    performance_components = {
        "focal": float(focal["performance"]),
        "immediate_tail": float(np.mean([value["performance"] for value in immediate_tail])),
        "distance_four_tail": float(np.mean([value["performance"] for value in terminal_tail])),
    }
    cost_components = {
        "focal": float(focal["resource_cost"]),
        "immediate_tail": float(np.mean([value["resource_cost"] for value in immediate_tail])),
        "distance_four_tail": float(np.mean([value["resource_cost"] for value in terminal_tail])),
    }
    return {
        "selection_mode": "multihorizon",
        "challenge": settings["challenge"],
        "fitness": float(np.mean(list(components.values()))),
        "performance": float(np.mean(list(performance_components.values()))),
        "resource_cost": float(np.mean(list(cost_components.values()))),
        "focal_score": focal,
        "virtual_descendants": trajectories,
        "selected_tail_size": 2,
        "fitness_components": components,
        "performance_components": performance_components,
        "resource_cost_components": cost_components,
        "fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric": False,
    }


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(args: tuple[Any, ...]) -> dict[str, Any]:
    source_text, arm, spec_value, kernel_value, predictor, output_text, digest, phase, seed = args
    source = read_json(Path(source_text))
    spec = ArchitectureSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(source["population_index"])
    population_id = f"{arm}.population-{task_index:03d}"
    final_path = Path(output_text) / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("architecture population registration differs")
    checkpoint = final_path.with_name(f"{population_id}.checkpoint.json")
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        if saved.get("protocol_digest") != digest:
            raise ValueError("architecture checkpoint protocol differs")
        population = [deserialize_genome(value) for value in saved["population"]]
        lineage_ids, scores = list(saved["lineage_ids"]), list(saved["scores"])
        trace, ancestry = list(saved["trace"]), list(saved["ancestry"])
        start_generation = int(saved["generation"]) + 1
    else:
        values = source["final_population"][: spec.population_size]
        population = [
            _initial_genome(value, arm, task_index, index, spec, phase, seed)
            for index, value in enumerate(values)
        ]
        if len(population) != spec.population_size:
            raise ValueError("architecture source population has unexpected size")
        scores = [architecture_score(value, source["task"], kernel, spec, arm, task_index, 0, predictor, phase, seed=seed) for value in population]
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
            "challenge": arm_settings(arm)["challenge"],
        }

    if not trace:
        trace.append(trace_item(0))
        ancestry.append({"generation": 0, "individuals": [
            {"lineage_id": lineage_ids[index], **serialize_genome(value), "selection_score": scores[index]}
            for index, value in enumerate(population)
        ]})
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(seed, "interpreter-architecture-generation", arm, task_index, generation)
        following: list[Genome] = []
        parents: list[tuple[str, ...]] = []
        elites = sorted(range(len(population)), key=lambda index: (-fitness[index], index))[: spec.elite_count]
        for index in elites:
            following.append(population[index]); parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            left = _tournament(fitness, random, spec.tournament_size)
            right = _tournament(fitness, random, spec.tournament_size)
            following.append(mutate_genome(population[left], population[right], arm, random, spec))
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [architecture_score(value, source["task"], kernel, spec, arm, task_index, generation, predictor, phase, seed=seed) for value in population]
        lineage_ids = [canonical_digest((phase, population_id, generation, index, genome_id(value)))[:24] for index, value in enumerate(population)]
        ancestry.append({"generation": generation, "individuals": [
            {"lineage_id": lineage_ids[index], "parent_ids": list(parents[index]), **serialize_genome(value), "selection_score": scores[index]}
            for index, value in enumerate(population)
        ]})
        trace.append(trace_item(generation))
        _atomic_json(checkpoint, {
            "protocol_digest": digest,
            "generation": generation,
            "population": [serialize_genome(value) for value in population],
            "lineage_ids": lineage_ids,
            "scores": scores,
            "trace": trace,
            "ancestry": ancestry,
        })
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
            {**serialize_genome(value), "selection_score": scores[index], "focal_training_score": scores[index]["focal_score"]}
            for index, value in enumerate(population)
        ],
        "trace": trace,
        "ancestry": ancestry,
        "fitness_contains_only_observable_performance_and_resource_cost": True,
        "fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric": False,
    }
    result["result_digest"] = canonical_digest({"selected": selected, "score": scores[best], "trace": trace})
    _atomic_json(final_path, result)
    if checkpoint.is_file():
        checkpoint.unlink()
    return result


def run_architecture_evolution(
    spec: ArchitectureSpec,
    source: Path,
    destination: Path,
    workers: int,
    predictor: dict[str, Any],
    progress: Callable[[str], None] | None = None,
    *,
    phase: str = "development",
    selected_arms: tuple[str, ...] | None = None,
    source_arm: str | None = None,
) -> Path:
    spec.validate()
    if phase not in {"development", "confirmation"} or not 1 <= workers <= spec.maximum_workers:
        raise ValueError("invalid architecture phase or worker count")
    arms = selected_arms or spec.arms
    if not arms or not set(arms) <= set(ARCHITECTURE_ARMS + CONTROL_ARMS):
        raise ValueError("invalid architecture arm subset")
    expected_source_arm = source_arm or ("direct_independent" if phase == "confirmation" else "lineage4_repair")
    source = source.resolve()
    source_checksum = sha256_file(source / "SHA256SUMS")
    destination = destination.resolve(); destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_architecture_evolution(destination); return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = spec.confirmation_seed if phase == "confirmation" else spec.master_seed
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "source_checksum": source_checksum,
        "source_arm": expected_source_arm,
        "phase": phase,
        "selected_arms": list(arms),
        "predictor_digest": predictor["predictor_digest"],
    }
    digest = canonical_digest(payload)
    registration = {
        "format": f"{EVOLUTION_FORMAT}-registration",
        "protocol_digest": digest,
        **payload,
        "source": str(source),
        "predictor": predictor,
        "selection_excludes_all_ph_and_atlas_damage_metrics": True,
    }
    if (destination / "registration.json").is_file() and read_json(destination / "registration.json") != registration:
        raise ValueError("existing architecture evolution registration differs")
    if not (destination / "registration.json").is_file():
        _atomic_json(destination / "registration.json", registration)
    shards = destination / "populations"; shards.mkdir(exist_ok=True)
    files = sorted((source / "populations").glob(f"{expected_source_arm}.population-*.json"))
    if len(files) < task_count:
        raise ValueError("architecture source task count mismatch")
    files = files[:task_count]
    work = [
        (str(path), arm, spec.to_dict(), kernel.to_dict(), predictor, str(shards), digest, phase, seed)
        for arm in arms for path in files
    ]
    started = time.monotonic(); completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, work); executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
        futures = [executor.submit(_population_task, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, 1):
            completed.append(result)
            elapsed = time.monotonic() - started; rate = index / max(elapsed, 1e-9)
            _atomic_json(destination / "progress.json", {
                "completed_populations": index,
                "total_populations": len(work),
                "elapsed_seconds": elapsed,
                "eta_seconds": (len(work) - index) / rate,
            })
            if progress:
                progress(f"interpreter-architecture {phase} evolution {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (arms.index(value["arm"]), value["population_index"]))
    _atomic_json(destination / "manifest.json", {
        "format": f"{EVOLUTION_FORMAT}-manifest",
        "protocol_digest": digest,
        "phase": phase,
        "selected_arms": list(arms),
        "population_count": len(completed),
        "workers": workers,
        "elapsed_seconds": time.monotonic() - started,
        "scientific_result_digest": canonical_digest([value["result_digest"] for value in completed]),
        "runtime": runtime_manifest(),
    })
    write_checksums(destination); verify_architecture_evolution(destination); return destination


def verify_architecture_evolution(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = ArchitectureSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{EVOLUTION_FORMAT}-registration":
        raise ValueError("architecture evolution registration format mismatch")
    if manifest.get("format") != f"{EVOLUTION_FORMAT}-manifest":
        raise ValueError("architecture evolution manifest format mismatch")
    if sha256_file(Path(registration["source"]) / "SHA256SUMS") != registration["source_checksum"]:
        raise ValueError("sealed architecture source changed")
    if canonical_digest({key: registration[key] for key in (
        "spec", "kernel", "source_checksum", "source_arm", "phase", "selected_arms", "predictor_digest"
    )}) != registration["protocol_digest"]:
        raise ValueError("architecture evolution protocol mismatch")
    verify_predictor(registration["predictor"])
    if registration["predictor"]["predictor_digest"] != registration["predictor_digest"]:
        raise ValueError("architecture predictor digest mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    files = sorted(path for path in (directory / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json"))
    expected = task_count * len(registration["selected_arms"])
    if (
        len(files) != expected
        or manifest["population_count"] != expected
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or manifest["phase"] != registration["phase"]
        or manifest["selected_arms"] != registration["selected_arms"]
    ):
        raise ValueError("architecture evolution is incomplete")
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
            raise ValueError("architecture evolution population digest mismatch")
        deserialize_genome(value["selected"])
    if any(value["fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric"] for value in values):
        raise ValueError("forbidden metric entered architecture fitness")
    ordered = sorted(values, key=lambda value: (registration["selected_arms"].index(value["arm"]), value["population_index"]))
    if manifest["scientific_result_digest"] != canonical_digest([value["result_digest"] for value in ordered]):
        raise ValueError("architecture evolution result digest mismatch")
    return {"verified": True, "phase": registration["phase"], "populations": len(files), "checksums": len(checksums)}


def replay_architecture_population(directory: Path, population_id: str) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = ArchitectureSpec.from_dict(registration["spec"])
    kernel = CooptionSpec.from_dict(registration["kernel"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    seed = spec.confirmation_seed if registration["phase"] == "confirmation" else spec.master_seed
    replayed = architecture_score(
        deserialize_genome(archived["selected"]), archived["task"], kernel, spec,
        archived["arm"], archived["population_index"], spec.generations,
        registration["predictor"], registration["phase"], seed=seed,
    )
    return {
        "population_id": population_id,
        "matches": canonical_digest(replayed) == canonical_digest(archived["selected_selection_score"]),
        "replayed_score": replayed,
    }
