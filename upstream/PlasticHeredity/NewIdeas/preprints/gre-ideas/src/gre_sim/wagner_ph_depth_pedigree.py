"""Four-mutation lineage pedigrees for Interpreter-Depth v1."""

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
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import deserialize_genotype, serialize_genotype
from .wagner_ph_cooption_experiment import simulate_ecology_condition
from .wagner_ph_depth_config import DEPTH_PEDIGREE_FORMAT, InterpreterDepthSpec
from .wagner_ph_depth_evolution import mutation_family, verify_depth_evolution
from .wagner_ph_depth_mechanisms import Genotype, mutate_for_arm, mutation_delta


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _phase_seed(spec: InterpreterDepthSpec, phase: str) -> str:
    return spec.pedigree_seed if phase == "development" else canonical_digest((spec.confirmation_seed, "mutation-pedigree"))


def pedigree_information(
    genotype: Genotype,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: InterpreterDepthSpec,
    scope: str,
    phase: str,
) -> float:
    rulebook, carrier = genotype
    seed = _phase_seed(spec, phase)
    conditions = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            carrier,
            kernel,
            intervention,
            spec.predictive_persistence,
            0.0,
            spec.pedigree_futures_per_history,
            kernel.lineage_generations,
            (kernel.lineage_generations,),
            scope,
            master_seed=seed,
        )
        for intervention in ("natural", "independent_history")
    }
    generation = str(kernel.lineage_generations)
    return float(
        conditions["natural"]["checkpoints"][generation]["correct_rate"]
        - conditions["independent_history"]["checkpoints"][generation]["correct_rate"]
    )


def _population_pedigree(
    args: tuple[str, dict[str, Any], dict[str, Any], str, str, str]
) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, protocol_digest, phase = args
    population = read_json(Path(population_text))
    spec = InterpreterDepthSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    arm = str(population["arm"])
    task_index = int(population["population_index"])
    final_path = Path(output_text) / f"{arm}.task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"interpreter-depth pedigree registration differs: {final_path}")
    ranked = sorted(
        population["final_population"],
        key=lambda value: (-float(value["selection_score"]["fitness"]), str(value["genotype_id"])),
    )[:spec.pedigree_roots_per_task]
    rows: list[dict[str, Any]] = []
    ancestry: list[dict[str, Any]] = []
    family = mutation_family(arm)
    seed = _phase_seed(spec, phase)
    max_depth = max(spec.pedigree_depths)
    for root_index, root_value in enumerate(ranked):
        root = deserialize_genotype(root_value)
        root_scope = f"interpreter-depth-{phase}-pedigree.task-{task_index:03d}.root-{root_index:02d}"
        root_information = pedigree_information(root, population["task"], kernel, spec, root_scope, phase)
        root_record = {
            "root_index": root_index,
            "lineage_id": canonical_digest((phase, arm, task_index, "root", root_index))[:24],
            "genotype": serialize_genotype(*root),
            "information": root_information,
            "lineages": [],
        }
        for lineage_index in range(spec.pedigree_lineages_per_root):
            current = root
            immediate_information = root_information
            chain: list[dict[str, Any]] = []
            for distance in range(1, max_depth + 1):
                descendant = mutate_for_arm(
                    current,
                    current,
                    arm,
                    rng_for(
                        seed,
                        "interpreter-depth-pedigree-mutation",
                        family,
                        task_index,
                        root_index,
                        lineage_index,
                        distance,
                    ),
                    local_sigma=spec.local_weight_sigma,
                )
                scope = f"{root_scope}.lineage-{lineage_index:02d}.distance-{distance:02d}"
                information = pedigree_information(
                    descendant, population["task"], kernel, spec, scope, phase
                )
                record = {
                    "distance": distance,
                    "lineage_id": canonical_digest((phase, arm, task_index, root_index, lineage_index, distance))[:24],
                    "parent_lineage_id": root_record["lineage_id"] if distance == 1 else chain[-1]["lineage_id"],
                    "genotype": serialize_genotype(*descendant),
                    "mutation_delta": mutation_delta(current, descendant),
                    "information": information,
                }
                chain.append(record)
                rows.append({
                    "phase": phase,
                    "arm": arm,
                    "task_index": task_index,
                    "root_index": root_index,
                    "lineage_index": lineage_index,
                    "distance": distance,
                    "root_information": root_information,
                    "immediate_parent_information": immediate_information,
                    "descendant_information": information,
                    "eligible_positive_root": root_information > 0.0,
                    "retained": root_information > 0.0 and information >= spec.retention_fraction * root_information,
                    "collapsed": root_information > 0.0 and information <= 0.0,
                    "changed_weight_indices": record["mutation_delta"]["changed_weight_indices"],
                })
                current = descendant
                immediate_information = information
            root_record["lineages"].append({"lineage_index": lineage_index, "chain": chain})
        ancestry.append(root_record)
    result = {
        "format": DEPTH_PEDIGREE_FORMAT,
        "protocol_digest": protocol_digest,
        "phase": phase,
        "population_id": population["population_id"],
        "arm": arm,
        "mutation_family": family,
        "task_index": task_index,
        "task_digest": population["task"]["task_digest"],
        "task": population["task"],
        "row_count": len(rows),
        "rows": rows,
        "complete_genotype_ancestry": ancestry,
        "mutation_stream_coordinates_are_replayable": True,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result)
    return result


def _task_centered_slope(rows: list[dict[str, Any]], task_count: int) -> float | None:
    centered_x: list[float] = []
    centered_y: list[float] = []
    for task_index in range(task_count):
        selected = [value for value in rows if int(value["task_index"]) == task_index]
        x = np.asarray([value["immediate_parent_information"] for value in selected], dtype=float)
        y = np.asarray([value["descendant_information"] for value in selected], dtype=float)
        if len(x):
            centered_x.extend((x - np.mean(x)).tolist())
            centered_y.extend((y - np.mean(y)).tolist())
    x = np.asarray(centered_x, dtype=float)
    y = np.asarray(centered_y, dtype=float)
    denominator = float(np.sum(x * x))
    return float(np.sum(x * y) / denominator) if denominator > 0.0 else None


def _analyze(
    results: list[dict[str, Any]],
    spec: InterpreterDepthSpec,
    phase: str,
    arms: tuple[str, ...],
) -> dict[str, Any]:
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = _phase_seed(spec, phase)
    summaries: dict[str, Any] = {}
    for arm in arms:
        rows = [row for result in results if result["arm"] == arm for row in result["rows"]]
        distances: dict[str, Any] = {}
        for distance in spec.pedigree_depths:
            selected = [row for row in rows if int(row["distance"]) == distance]
            task_retention: dict[str, float] = {}
            task_collapse: dict[str, float] = {}
            task_information: dict[str, float] = {}
            for task_index in range(task_count):
                task_rows = [row for row in selected if int(row["task_index"]) == task_index]
                eligible = [row for row in task_rows if row["eligible_positive_root"]]
                task_retention[str(task_index)] = float(np.mean([row["retained"] for row in eligible])) if eligible else 0.0
                task_collapse[str(task_index)] = float(np.mean([row["collapsed"] for row in eligible])) if eligible else 1.0
                task_information[str(task_index)] = float(np.mean([row["descendant_information"] for row in task_rows])) if task_rows else 0.0
            distances[str(distance)] = {
                "eligible_descendants": sum(row["eligible_positive_root"] for row in selected),
                "task_retention": task_retention,
                "retention_interval": _interval(
                    task_retention.values(), seed,
                    f"interpreter-depth-{phase}-pedigree.{arm}.distance-{distance}.retention",
                    spec.bootstrap_repetitions, spec.interval_level,
                ),
                "task_collapse_probability": task_collapse,
                "collapse_interval": _interval(
                    task_collapse.values(), seed,
                    f"interpreter-depth-{phase}-pedigree.{arm}.distance-{distance}.collapse",
                    spec.bootstrap_repetitions, spec.interval_level,
                ),
                "task_information": task_information,
                "information_interval": _interval(
                    task_information.values(), seed,
                    f"interpreter-depth-{phase}-pedigree.{arm}.distance-{distance}.information",
                    spec.bootstrap_repetitions, spec.interval_level,
                ),
            }
        summaries[arm] = {
            "rows": len(rows),
            "distances": distances,
            "task_centered_immediate_parent_offspring_slope": _task_centered_slope(rows, task_count),
            "mean_root_information": float(np.mean([row["root_information"] for row in rows])) if rows else None,
        }
    result = {
        "format": f"{DEPTH_PEDIGREE_FORMAT}-analysis",
        "phase": phase,
        "inferential_unit": "paired founder task",
        "retention_definition": "descendant information >= 0.70 times positive root information",
        "nonpositive_roots_are_not_counted_as_retention_successes": True,
        "arms": summaries,
        "rows": sum(value["rows"] for value in summaries.values()),
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def run_depth_pedigree(
    spec: InterpreterDepthSpec,
    evolution: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("interpreter-depth pedigree permits one to four CPU workers")
    evolution = evolution.resolve()
    verify_depth_evolution(evolution)
    evolution_registration = read_json(evolution / "registration.json")
    phase = str(evolution_registration["phase"])
    arms = tuple(evolution_registration["selected_arms"])
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_depth_pedigree(destination)
        return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "phase": phase,
        "selected_arms": list(arms),
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": f"{DEPTH_PEDIGREE_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **payload,
        "evolution": str(evolution),
        "pedigree_seed": _phase_seed(spec, phase),
        "complete_descendant_genotypes_and_mutation_deltas_are_archived": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing interpreter-depth pedigree registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    shards = destination / "populations"
    shards.mkdir(exist_ok=True)
    files = sorted(
        path for path in (evolution / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    work = [
        (str(path), spec.to_dict(), kernel.to_dict(), str(shards), protocol_digest, phase)
        for path in files
    ]
    started = time.monotonic()
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_pedigree, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_population_pedigree, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(destination / "progress.json", {
                "format": f"{DEPTH_PEDIGREE_FORMAT}-progress",
                "phase": phase,
                "completed_populations": index,
                "total_populations": len(work),
                "elapsed_seconds": elapsed,
                "populations_per_second": rate,
                "eta_seconds": (len(work) - index) / rate if rate else None,
            })
            if progress:
                progress(f"interpreter-depth {phase} pedigree {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (arms.index(value["arm"]), value["task_index"]))
    analysis = _analyze(completed, spec, phase, arms)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {
        "format": f"{DEPTH_PEDIGREE_FORMAT}-manifest",
        "protocol_digest": protocol_digest,
        "phase": phase,
        "populations": len(completed),
        "rows": sum(value["row_count"] for value in completed),
        "workers": workers,
        "elapsed_seconds": time.monotonic() - started,
        "runtime": runtime_manifest(),
    })
    write_checksums(destination)
    verify_depth_pedigree(destination)
    return destination


def verify_depth_pedigree(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != f"{DEPTH_PEDIGREE_FORMAT}-registration":
        raise ValueError("interpreter-depth pedigree registration format mismatch")
    spec = InterpreterDepthSpec.from_dict(registration["spec"])
    evolution = Path(registration["evolution"])
    if sha256_file(evolution / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed evolution changed after interpreter-depth pedigree")
    payload = {
        "spec": spec.to_dict(),
        "kernel": registration["kernel"],
        "evolution_checksum": registration["evolution_checksum"],
        "phase": registration["phase"],
        "selected_arms": registration["selected_arms"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("interpreter-depth pedigree protocol digest mismatch")
    phase = str(registration["phase"])
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    arms = tuple(registration["selected_arms"])
    expected_populations = len(arms) * task_count
    expected_rows = (
        expected_populations * spec.pedigree_roots_per_task
        * spec.pedigree_lineages_per_root * max(spec.pedigree_depths)
    )
    files = sorted((directory / "populations").glob("*.json"))
    rows = 0
    for path in files:
        value = read_json(path)
        archived = dict(value)
        result_digest = archived.pop("result_digest", None)
        if result_digest != canonical_digest(archived):
            raise ValueError(f"interpreter-depth pedigree result mismatch: {path.name}")
        rows += int(value["row_count"])
    if len(files) != expected_populations or rows != expected_rows or int(manifest["rows"]) != expected_rows:
        raise ValueError("interpreter-depth pedigree dimensions are incomplete")
    archived_analysis = dict(analysis)
    analysis_digest = archived_analysis.pop("analysis_digest", None)
    if analysis_digest != canonical_digest(archived_analysis):
        raise ValueError("interpreter-depth pedigree analysis digest mismatch")
    return {"verified": True, "phase": phase, "populations": len(files), "rows": rows, "checksums": len(checksums)}


def replay_pedigree_event(
    directory: Path,
    population_id: str,
    root_index: int = 0,
    lineage_index: int = 0,
    distance: int = 1,
) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = InterpreterDepthSpec.from_dict(registration["spec"])
    phase = str(registration["phase"])
    arm, task_text = population_id.split(".population-")
    task_index = int(task_text)
    shard = read_json(directory / "populations" / f"{arm}.task-{task_index:03d}.json")
    root_record = shard["complete_genotype_ancestry"][root_index]
    current = deserialize_genotype(root_record["genotype"])
    seed = _phase_seed(spec, phase)
    matches = True
    replayed = None
    for step in range(1, distance + 1):
        replayed = mutate_for_arm(
            current,
            current,
            arm,
            rng_for(
                seed,
                "interpreter-depth-pedigree-mutation",
                mutation_family(arm),
                task_index,
                root_index,
                lineage_index,
                step,
            ),
            local_sigma=spec.local_weight_sigma,
        )
        archived = root_record["lineages"][lineage_index]["chain"][step - 1]["genotype"]
        matches = matches and canonical_digest(serialize_genotype(*replayed)) == canonical_digest(archived)
        current = replayed
    return {
        "population_id": population_id,
        "root_index": root_index,
        "lineage_index": lineage_index,
        "distance": distance,
        "matches": matches,
    }
