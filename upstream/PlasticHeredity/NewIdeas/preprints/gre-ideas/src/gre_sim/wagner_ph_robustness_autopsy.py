"""Exact replay and four-component factorial autopsy of the failed pedigree."""

from __future__ import annotations

import concurrent.futures
import math
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
from .wagner_ph_cooption_evolution import deserialize_genotype, mutate_genotype, serialize_genotype
from .wagner_ph_cooption_experiment import history_information, simulate_ecology_condition
from .wagner_ph_direct_campaign import (
    _pedigree_information,
    verify_wagner_ph_direct_prediction_campaign,
)
from .wagner_ph_direct_config import DirectPredictionSpec
from .wagner_ph_robustness_config import (
    AUTOPSY_COMPONENTS,
    ROBUSTNESS_AUTOPSY_FORMAT,
    RobustnessSpec,
)
from .wagner_ph_robustness_mechanisms import Genotype, hybrid_genotype, mutation_delta


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _payload_digest(value: dict[str, Any], field: str) -> str:
    payload = dict(value)
    archived = payload.pop(field, None)
    digest = canonical_digest(payload)
    if archived != digest:
        raise ValueError(f"{field} mismatch")
    return digest


def _row_key(row: dict[str, Any]) -> tuple[int, int, int, int | None]:
    return (
        int(row["task_index"]),
        int(row["parent_index"]),
        int(row["child_index"]),
        None if row["grandchild_index"] is None else int(row["grandchild_index"]),
    )


def _summary_only(condition: dict[str, Any], generation: int) -> dict[str, Any]:
    return {
        "intervention": condition["intervention"],
        "checkpoint": condition["checkpoints"][str(generation)],
        "history_information": history_information(condition["final_carriers"]),
    }


def _assess_hybrid(
    genotype: Genotype,
    task: dict[str, Any],
    kernel_value: dict[str, Any],
    spec: RobustnessSpec,
    scope: str,
) -> dict[str, Any]:
    kernel = spec.kernel().from_dict(kernel_value)
    rulebook, carrier = genotype
    cells: list[dict[str, Any]] = []
    for persistence in spec.autopsy_persistence:
        conditions = {
            intervention: simulate_ecology_condition(
                rulebook,
                task,
                carrier,
                kernel,
                intervention,
                persistence,
                0.0,
                spec.autopsy_futures_per_history,
                kernel.lineage_generations,
                (kernel.lineage_generations,),
                scope,
                master_seed=spec.autopsy_seed,
            )
            for intervention in spec.autopsy_interventions
        }
        cells.append(
            {
                "persistence": persistence,
                "conditions": {
                    name: _summary_only(value, kernel.lineage_generations)
                    for name, value in conditions.items()
                },
            }
        )
    by_rho = {float(value["persistence"]): value for value in cells}

    def rate(rho: float, intervention: str, field: str) -> float:
        return float(by_rho[rho]["conditions"][intervention]["checkpoint"][field])

    high_information = rate(0.9, "natural", "correct_rate") - rate(
        0.9, "independent_history", "correct_rate"
    )
    low_information = rate(0.0, "natural", "correct_rate") - rate(
        0.0, "independent_history", "correct_rate"
    )
    return {
        "cells": cells,
        "effects": {
            "information_high": high_information,
            "information_low": low_information,
            "predictability_interaction": high_information - low_information,
            "natural_minus_zero": rate(0.9, "natural", "correct_rate")
            - rate(0.9, "zero", "correct_rate"),
            "opposite_donor_following": rate(0.9, "opposite_history", "wrong_rate")
            - rate(0.9, "opposite_history", "correct_rate"),
            "reader_dependence": rate(0.9, "natural", "correct_rate")
            - rate(0.9, "reader_off", "correct_rate"),
            "renewal_dependence": rate(0.9, "natural", "correct_rate")
            - rate(0.9, "renewal_off", "correct_rate"),
        },
    }


def _event_record(
    *,
    event_id: str,
    task_index: int,
    task: dict[str, Any],
    parent: Genotype,
    descendant: Genotype,
    archived_row: dict[str, Any],
    replayed_parent_information: float,
    replayed_descendant_information: float,
    kernel_value: dict[str, Any],
    spec: RobustnessSpec,
) -> dict[str, Any]:
    tolerance = 1e-12
    parent_matches = abs(
        replayed_parent_information - float(archived_row["immediate_parent_information"])
    ) <= tolerance
    descendant_matches = abs(
        replayed_descendant_information - float(archived_row["descendant_information"])
    ) <= tolerance
    hybrids: list[dict[str, Any]] = []
    scope = f"mutation-autopsy.task-{task_index:03d}.{event_id}"
    for mask in range(1 << len(AUTOPSY_COMPONENTS)):
        genotype = hybrid_genotype(parent, descendant, mask)
        hybrids.append(
            {
                "mask": mask,
                "sources": {
                    component: "descendant" if mask & (1 << index) else "parent"
                    for index, component in enumerate(AUTOPSY_COMPONENTS)
                },
                "genotype": serialize_genotype(*genotype),
                **_assess_hybrid(genotype, task, kernel_value, spec, scope),
            }
        )
    return {
        "event_id": event_id,
        "task_index": task_index,
        "pedigree_generation": int(archived_row["pedigree_generation"]),
        "coordinates": {
            "parent_index": int(archived_row["parent_index"]),
            "child_index": int(archived_row["child_index"]),
            "grandchild_index": archived_row["grandchild_index"],
        },
        "parent": serialize_genotype(*parent),
        "descendant": serialize_genotype(*descendant),
        "mutation_delta": mutation_delta(parent, descendant),
        "archived_information": {
            "immediate_parent": archived_row["immediate_parent_information"],
            "descendant": archived_row["descendant_information"],
        },
        "exact_replay": {
            "immediate_parent": replayed_parent_information,
            "descendant": replayed_descendant_information,
            "parent_matches": parent_matches,
            "descendant_matches": descendant_matches,
            "matches": parent_matches and descendant_matches,
        },
        "hybrids": hybrids,
    }


def _autopsy_task(
    args: tuple[str, str, dict[str, Any], dict[str, Any], str, str]
) -> dict[str, Any]:
    (
        population_text,
        pedigree_text,
        robustness_value,
        direct_value,
        output_text,
        protocol_digest,
    ) = args
    population = read_json(Path(population_text))
    pedigree = read_json(Path(pedigree_text))
    spec = RobustnessSpec.from_dict(robustness_value)
    direct = DirectPredictionSpec.from_dict(direct_value)
    kernel = direct.cooption_spec()
    task_index = int(population["population_index"])
    final_path = Path(output_text) / f"task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"autopsy shard registration differs: {final_path}")
    archived_rows = {_row_key(row): row for row in pedigree["rows"]}
    ranked = sorted(
        population["final_population"],
        key=lambda value: (-float(value["training_score"]["fitness"]), str(value["genotype_id"])),
    )[: direct.pedigree_parents_per_task]
    events: list[dict[str, Any]] = []
    for parent_index, parent_value in enumerate(ranked):
        root = deserialize_genotype(parent_value)
        root_scope = f"direct-pedigree.task-{task_index:03d}.parent-{parent_index:02d}"
        root_information = _pedigree_information(
            root, population["task"], kernel, direct.pedigree_seed, root_scope
        )
        for child_index in range(direct.pedigree_children_per_parent):
            child = mutate_genotype(
                root,
                root,
                "independent",
                rng_for(
                    direct.pedigree_seed,
                    "direct-pedigree-child",
                    task_index,
                    parent_index,
                    child_index,
                ),
            )
            child_scope = f"{root_scope}.child-{child_index:02d}"
            child_information = _pedigree_information(
                child, population["task"], kernel, direct.pedigree_seed, child_scope
            )
            child_row = archived_rows[(task_index, parent_index, child_index, None)]
            events.append(
                _event_record(
                    event_id=f"parent-{parent_index:02d}.child-{child_index:02d}",
                    task_index=task_index,
                    task=population["task"],
                    parent=root,
                    descendant=child,
                    archived_row=child_row,
                    replayed_parent_information=root_information,
                    replayed_descendant_information=child_information,
                    kernel_value=kernel.to_dict(),
                    spec=spec,
                )
            )
            for grandchild_index in range(direct.pedigree_grandchildren_per_child):
                grandchild = mutate_genotype(
                    child,
                    child,
                    "independent",
                    rng_for(
                        direct.pedigree_seed,
                        "direct-pedigree-grandchild",
                        task_index,
                        parent_index,
                        child_index,
                        grandchild_index,
                    ),
                )
                grandchild_scope = f"{child_scope}.grandchild-{grandchild_index:02d}"
                grandchild_information = _pedigree_information(
                    grandchild,
                    population["task"],
                    kernel,
                    direct.pedigree_seed,
                    grandchild_scope,
                )
                grandchild_row = archived_rows[
                    (task_index, parent_index, child_index, grandchild_index)
                ]
                events.append(
                    _event_record(
                        event_id=(
                            f"parent-{parent_index:02d}.child-{child_index:02d}."
                            f"grandchild-{grandchild_index:02d}"
                        ),
                        task_index=task_index,
                        task=population["task"],
                        parent=child,
                        descendant=grandchild,
                        archived_row=grandchild_row,
                        replayed_parent_information=child_information,
                        replayed_descendant_information=grandchild_information,
                        kernel_value=kernel.to_dict(),
                        spec=spec,
                    )
                )
    result = {
        "format": ROBUSTNESS_AUTOPSY_FORMAT,
        "protocol_digest": protocol_digest,
        "task_index": task_index,
        "task_digest": population["task"]["task_digest"],
        "event_count": len(events),
        "hybrids_per_event": 16,
        "events": events,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result)
    return result


def _shapley(values: dict[int, float], component: int) -> float:
    n = len(AUTOPSY_COMPONENTS)
    total = 0.0
    for mask in range(1 << n):
        if mask & (1 << component):
            continue
        size = int(mask.bit_count())
        weight = math.factorial(size) * math.factorial(n - size - 1) / math.factorial(n)
        total += weight * (values[mask | (1 << component)] - values[mask])
    return float(total)


def _analyze(tasks: list[dict[str, Any]], spec: RobustnessSpec) -> dict[str, Any]:
    events = [event for task in tasks for event in task["events"]]
    task_component_changes: dict[str, dict[str, list[float]]] = {
        component: {str(index): [] for index in range(spec.task_count)}
        for component in AUTOPSY_COMPONENTS
    }
    event_rows: list[dict[str, Any]] = []
    for event in events:
        values = {
            int(row["mask"]): float(row["effects"]["information_high"])
            for row in event["hybrids"]
        }
        contributions = {
            component: _shapley(values, index)
            for index, component in enumerate(AUTOPSY_COMPONENTS)
        }
        for component, value in contributions.items():
            task_component_changes[component][str(event["task_index"])].append(value)
        event_rows.append(
            {
                "event_id": event["event_id"],
                "task_index": event["task_index"],
                "parent_information": values[0],
                "descendant_information": values[15],
                "total_information_change": values[15] - values[0],
                "shapley_information_change": contributions,
                "shapley_sum_matches_total": abs(
                    sum(contributions.values()) - (values[15] - values[0])
                ) <= 1e-12,
            }
        )
    component_summary: dict[str, Any] = {}
    for component, by_task in task_component_changes.items():
        task_means = {
            key: float(np.mean(values)) if values else 0.0 for key, values in by_task.items()
        }
        component_summary[component] = {
            "task_mean_information_change": task_means,
            "interval": _interval(
                task_means.values(),
                spec.autopsy_seed,
                f"mutation-autopsy.shapley.{component}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "negative_means_damage": True,
        }
    result = {
        "format": f"{ROBUSTNESS_AUTOPSY_FORMAT}-analysis",
        "inferential_unit": "sealed founder task",
        "tasks": len(tasks),
        "mutation_events": len(events),
        "factorial_hybrids": len(events) * 16,
        "all_archived_scores_exactly_replayed": all(
            event["exact_replay"]["matches"] for event in events
        ),
        "all_shapley_sums_close": all(row["shapley_sum_matches_total"] for row in event_rows),
        "component_summary": component_summary,
        "events": event_rows,
        "diagnostic_only": True,
        "diagnostic_did_not_select_or_modify_later_arms": True,
        "fresh_confirmation_tasks_consumed": False,
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def run_mutation_autopsy(
    spec: RobustnessSpec,
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("mutation autopsy permits one to four CPU workers")
    parent = parent.resolve()
    verify_wagner_ph_direct_prediction_campaign(parent)
    direct_registration = read_json(parent / "registration.json")
    direct = DirectPredictionSpec.from_dict(direct_registration["protocol"])
    if direct.task_count != spec.task_count:
        raise ValueError("autopsy and sealed parent task counts differ")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_mutation_autopsy(destination)
        return destination
    started = time.monotonic()
    payload = {
        "spec": spec.to_dict(),
        "direct_parent_checksum": sha256_file(parent / "SHA256SUMS"),
        "direct_pedigree_checksum": sha256_file(parent / "pedigree" / "SHA256SUMS"),
        "parent_variant": spec.parent_variant,
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": f"{ROBUSTNESS_AUTOPSY_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **payload,
        "direct_parent": str(parent),
        "direct_protocol": direct.to_dict(),
        "full_factorial_masks": list(range(16)),
        "common_random_streams_across_hybrids": True,
        "diagnostic_cannot_select_robustness_arms": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing mutation-autopsy registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    shards = destination / "tasks"
    shards.mkdir(exist_ok=True)
    population_files = sorted(
        (parent / "evolution" / spec.parent_variant / "populations").glob(
            "direct_independent.population-*.json"
        )
    )
    work = [
        (
            str(path),
            str(parent / "pedigree" / "tasks" / f"task-{index:03d}.json"),
            spec.to_dict(),
            direct.to_dict(),
            str(shards),
            protocol_digest,
        )
        for index, path in enumerate(population_files)
    ]
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_autopsy_task, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_autopsy_task, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": f"{ROBUSTNESS_AUTOPSY_FORMAT}-progress",
                    "completed_tasks": index,
                    "total_tasks": len(work),
                    "elapsed_seconds": elapsed,
                    "eta_seconds": (len(work) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"mutation autopsy {index}/{len(work)} tasks")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: int(value["task_index"]))
    analysis = _analyze(completed, spec)
    if not analysis["all_archived_scores_exactly_replayed"]:
        raise RuntimeError("mutation autopsy failed exact archived pedigree replay")
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{ROBUSTNESS_AUTOPSY_FORMAT}-manifest",
            "protocol_digest": protocol_digest,
            "tasks": len(completed),
            "mutation_events": analysis["mutation_events"],
            "factorial_hybrids": analysis["factorial_hybrids"],
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_mutation_autopsy(destination)
    return destination


def verify_mutation_autopsy(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != f"{ROBUSTNESS_AUTOPSY_FORMAT}-registration":
        raise ValueError("mutation-autopsy registration format mismatch")
    spec = RobustnessSpec.from_dict(registration["spec"])
    parent = Path(registration["direct_parent"])
    if sha256_file(parent / "SHA256SUMS") != registration["direct_parent_checksum"]:
        raise ValueError("sealed direct parent changed after mutation autopsy")
    payload = {
        "spec": spec.to_dict(),
        "direct_parent_checksum": registration["direct_parent_checksum"],
        "direct_pedigree_checksum": registration["direct_pedigree_checksum"],
        "parent_variant": registration["parent_variant"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("mutation-autopsy protocol digest mismatch")
    files = sorted((directory / "tasks").glob("task-*.json"))
    if len(files) != spec.task_count or int(manifest["tasks"]) != spec.task_count:
        raise ValueError("mutation-autopsy task count mismatch")
    events = 0
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"mutation-autopsy shard protocol mismatch: {path.name}")
        _payload_digest(value, "result_digest")
        events += int(value["event_count"])
        if any(len(event["hybrids"]) != 16 for event in value["events"]):
            raise ValueError(f"mutation-autopsy factorial incomplete: {path.name}")
    if events != int(manifest["mutation_events"]):
        raise ValueError("mutation-autopsy event count mismatch")
    if events * 16 != int(manifest["factorial_hybrids"]):
        raise ValueError("mutation-autopsy hybrid count mismatch")
    _payload_digest(analysis, "analysis_digest")
    if not analysis["all_archived_scores_exactly_replayed"]:
        raise ValueError("mutation-autopsy exact replay did not pass")
    return {
        "verified": True,
        "tasks": len(files),
        "mutation_events": events,
        "factorial_hybrids": events * 16,
        "checksums": len(checksums),
    }
