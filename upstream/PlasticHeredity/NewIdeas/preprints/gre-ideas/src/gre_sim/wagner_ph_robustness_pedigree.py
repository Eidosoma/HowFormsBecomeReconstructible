"""Mutation pedigree with complete genotypes for every robustness arm."""

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
from .wagner_ph_robustness_config import (
    ROBUSTNESS_ARMS,
    ROBUSTNESS_PEDIGREE_FORMAT,
    RobustnessSpec,
)
from .wagner_ph_robustness_evolution import mutation_family, verify_robustness_evolution
from .wagner_ph_robustness_mechanisms import Genotype, mutate_for_arm, mutation_delta


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def pedigree_information(
    genotype: Genotype,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: RobustnessSpec,
    scope: str,
) -> float:
    rulebook, carrier = genotype
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
            master_seed=spec.pedigree_seed,
        )
        for intervention in ("natural", "independent_history")
    }
    generation = str(kernel.lineage_generations)
    return float(
        conditions["natural"]["checkpoints"][generation]["correct_rate"]
        - conditions["independent_history"]["checkpoints"][generation]["correct_rate"]
    )


def _population_pedigree(
    args: tuple[str, dict[str, Any], dict[str, Any], str, str]
) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, protocol_digest = args
    population = read_json(Path(population_text))
    spec = RobustnessSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    arm = str(population["arm"])
    task_index = int(population["population_index"])
    final_path = Path(output_text) / f"{arm}.task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"robustness pedigree registration differs: {final_path}")
    ranked = sorted(
        population["final_population"],
        key=lambda value: (-float(value["selection_score"]["fitness"]), str(value["genotype_id"])),
    )[: spec.pedigree_parents_per_task]
    rows: list[dict[str, Any]] = []
    ancestry: list[dict[str, Any]] = []
    family = mutation_family(arm)
    for parent_index, parent_value in enumerate(ranked):
        root = deserialize_genotype(parent_value)
        root_scope = f"robustness-pedigree.task-{task_index:03d}.parent-{parent_index:02d}"
        root_information = pedigree_information(root, population["task"], kernel, spec, root_scope)
        root_record: dict[str, Any] = {
            "parent_index": parent_index,
            "lineage_id": canonical_digest((arm, task_index, "root", parent_index))[:24],
            "genotype": serialize_genotype(*root),
            "information": root_information,
            "children": [],
        }
        for child_index in range(spec.pedigree_children_per_parent):
            child = mutate_for_arm(
                root,
                root,
                arm,
                rng_for(
                    spec.pedigree_seed,
                    "robustness-pedigree-child",
                    family,
                    task_index,
                    parent_index,
                    child_index,
                ),
            )
            child_scope = f"{root_scope}.child-{child_index:02d}"
            child_information = pedigree_information(
                child, population["task"], kernel, spec, child_scope
            )
            child_id = canonical_digest((arm, task_index, parent_index, child_index))[:24]
            child_record: dict[str, Any] = {
                "child_index": child_index,
                "lineage_id": child_id,
                "parent_lineage_id": root_record["lineage_id"],
                "genotype": serialize_genotype(*child),
                "mutation_delta": mutation_delta(root, child),
                "information": child_information,
                "grandchildren": [],
            }
            rows.append(
                {
                    "arm": arm,
                    "task_index": task_index,
                    "parent_index": parent_index,
                    "child_index": child_index,
                    "grandchild_index": None,
                    "pedigree_generation": 1,
                    "root_parent_information": root_information,
                    "immediate_parent_information": root_information,
                    "descendant_information": child_information,
                    "retained": root_information > 0.0
                    and child_information >= spec.retention_fraction * root_information,
                }
            )
            for grandchild_index in range(spec.pedigree_grandchildren_per_child):
                grandchild = mutate_for_arm(
                    child,
                    child,
                    arm,
                    rng_for(
                        spec.pedigree_seed,
                        "robustness-pedigree-grandchild",
                        family,
                        task_index,
                        parent_index,
                        child_index,
                        grandchild_index,
                    ),
                )
                grandchild_scope = f"{child_scope}.grandchild-{grandchild_index:02d}"
                grandchild_information = pedigree_information(
                    grandchild, population["task"], kernel, spec, grandchild_scope
                )
                grandchild_id = canonical_digest(
                    (arm, task_index, parent_index, child_index, grandchild_index)
                )[:24]
                child_record["grandchildren"].append(
                    {
                        "grandchild_index": grandchild_index,
                        "lineage_id": grandchild_id,
                        "parent_lineage_id": child_id,
                        "genotype": serialize_genotype(*grandchild),
                        "mutation_delta": mutation_delta(child, grandchild),
                        "information": grandchild_information,
                    }
                )
                rows.append(
                    {
                        "arm": arm,
                        "task_index": task_index,
                        "parent_index": parent_index,
                        "child_index": child_index,
                        "grandchild_index": grandchild_index,
                        "pedigree_generation": 2,
                        "root_parent_information": root_information,
                        "immediate_parent_information": child_information,
                        "descendant_information": grandchild_information,
                        "retained": root_information > 0.0
                        and grandchild_information
                        >= spec.retention_fraction * root_information,
                    }
                )
            root_record["children"].append(child_record)
        ancestry.append(root_record)
    result = {
        "format": ROBUSTNESS_PEDIGREE_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population["population_id"],
        "arm": arm,
        "mutation_family": family,
        "task_index": task_index,
        "task_digest": population["task"]["task_digest"],
        "descendant_count": len(rows),
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


def _analyze(results: list[dict[str, Any]], spec: RobustnessSpec) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for arm in spec.arms:
        rows = [row for result in results if result["arm"] == arm for row in result["rows"]]
        task_retention = {
            str(task_index): float(
                np.mean([value["retained"] for value in rows if value["task_index"] == task_index])
            )
            for task_index in range(spec.task_count)
        }
        roots = [float(value["root_parent_information"]) for value in rows]
        descendants = [float(value["descendant_information"]) for value in rows]
        arms[arm] = {
            "descendants": len(rows),
            "task_retention": task_retention,
            "retention_interval": _interval(
                task_retention.values(),
                spec.pedigree_seed,
                f"robustness-pedigree.{arm}.retention",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "task_centered_immediate_parent_offspring_slope": _task_centered_slope(
                rows, spec.task_count
            ),
            "mean_root_information": float(np.mean(roots)) if roots else None,
            "mean_descendant_information": float(np.mean(descendants)) if descendants else None,
        }
    result = {
        "format": f"{ROBUSTNESS_PEDIGREE_FORMAT}-analysis",
        "inferential_unit": "paired sealed founder task",
        "retention_definition": (
            "descendant information >= 0.70 times its positive root-parent information"
        ),
        "arms": arms,
        "descendant_genotypes": sum(value["descendants"] for value in arms.values()),
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def run_robustness_pedigree(
    spec: RobustnessSpec,
    evolution: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("robustness pedigree permits one to four CPU workers")
    evolution = evolution.resolve()
    verify_robustness_evolution(evolution)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_robustness_pedigree(destination)
        return destination
    started = time.monotonic()
    kernel = spec.kernel()
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": f"{ROBUSTNESS_PEDIGREE_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **payload,
        "evolution": str(evolution),
        "complete_descendant_genotypes_and_mutation_deltas_are_archived": True,
        "common_random_streams_are_shared_by_matched_mutation_families": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing robustness-pedigree registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    shards = destination / "populations"
    shards.mkdir(exist_ok=True)
    files = sorted(
        path
        for path in (evolution / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    work = [
        (str(path), spec.to_dict(), kernel.to_dict(), str(shards), protocol_digest)
        for path in files
    ]
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
            _atomic_json(
                destination / "progress.json",
                {
                    "format": f"{ROBUSTNESS_PEDIGREE_FORMAT}-progress",
                    "completed_populations": index,
                    "total_populations": len(work),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(work) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"robustness mutation pedigree {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (ROBUSTNESS_ARMS.index(value["arm"]), value["task_index"]))
    analysis = _analyze(completed, spec)
    if analysis["descendant_genotypes"] != spec.pedigree_descendant_count:
        raise RuntimeError("robustness pedigree descendant count differs from contract")
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{ROBUSTNESS_PEDIGREE_FORMAT}-manifest",
            "protocol_digest": protocol_digest,
            "populations": len(completed),
            "descendants": analysis["descendant_genotypes"],
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_robustness_pedigree(destination)
    return destination


def verify_robustness_pedigree(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != f"{ROBUSTNESS_PEDIGREE_FORMAT}-registration":
        raise ValueError("robustness-pedigree registration format mismatch")
    spec = RobustnessSpec.from_dict(registration["spec"])
    evolution = Path(registration["evolution"])
    if sha256_file(evolution / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed robustness evolution changed after pedigree")
    payload = {
        "spec": spec.to_dict(),
        "kernel": registration["kernel"],
        "evolution_checksum": registration["evolution_checksum"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("robustness-pedigree protocol digest mismatch")
    files = sorted((directory / "populations").glob("*.json"))
    if len(files) != spec.population_count or int(manifest["populations"]) != spec.population_count:
        raise ValueError("robustness-pedigree population count mismatch")
    descendants = 0
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"robustness pedigree shard protocol mismatch: {path.name}")
        archived = dict(value)
        result_digest = archived.pop("result_digest", None)
        if result_digest != canonical_digest(archived):
            raise ValueError(f"robustness pedigree shard result mismatch: {path.name}")
        descendants += int(value["descendant_count"])
    if descendants != spec.pedigree_descendant_count or int(manifest["descendants"]) != descendants:
        raise ValueError("robustness-pedigree descendant count mismatch")
    archived_analysis = dict(analysis)
    analysis_digest = archived_analysis.pop("analysis_digest", None)
    if analysis_digest != canonical_digest(archived_analysis):
        raise ValueError("robustness-pedigree analysis digest mismatch")
    return {
        "verified": True,
        "populations": len(files),
        "descendants": descendants,
        "checksums": len(checksums),
    }


def replay_pedigree_event(
    directory: Path,
    population_id: str,
    parent_index: int = 0,
    child_index: int = 0,
    grandchild_index: int | None = None,
) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    spec = RobustnessSpec.from_dict(registration["spec"])
    arm, task_text = population_id.split(".population-")
    task_index = int(task_text)
    shard = read_json(directory / "populations" / f"{arm}.task-{task_index:03d}.json")
    root = shard["complete_genotype_ancestry"][parent_index]
    child = root["children"][child_index]
    parent_genotype = deserialize_genotype(root["genotype"])
    replayed_child = mutate_for_arm(
        parent_genotype,
        parent_genotype,
        arm,
        rng_for(
            spec.pedigree_seed,
            "robustness-pedigree-child",
            mutation_family(arm),
            task_index,
            parent_index,
            child_index,
        ),
    )
    child_matches = canonical_digest(serialize_genotype(*replayed_child)) == canonical_digest(
        child["genotype"]
    )
    if grandchild_index is None:
        return {"population_id": population_id, "child_matches": child_matches, "matches": child_matches}
    grandchild = child["grandchildren"][grandchild_index]
    replayed_grandchild = mutate_for_arm(
        replayed_child,
        replayed_child,
        arm,
        rng_for(
            spec.pedigree_seed,
            "robustness-pedigree-grandchild",
            mutation_family(arm),
            task_index,
            parent_index,
            child_index,
            grandchild_index,
        ),
    )
    grandchild_matches = canonical_digest(
        serialize_genotype(*replayed_grandchild)
    ) == canonical_digest(grandchild["genotype"])
    return {
        "population_id": population_id,
        "child_matches": child_matches,
        "grandchild_matches": grandchild_matches,
        "matches": child_matches and grandchild_matches,
    }
