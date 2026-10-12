"""Bounded orchestration for direct predictive origin of Wagner PH."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import os
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
from .wagner_ph_cooption_audit import run_cooption_audit, verify_cooption_audit
from .wagner_ph_cooption_campaign import verify_wagner_ph_cooption_campaign
from .wagner_ph_cooption_evolution import (
    deserialize_genotype,
    mutate_genotype,
    run_cooption_evolution,
    verify_cooption_evolution,
)
from .wagner_ph_cooption_experiment import simulate_ecology_condition
from .wagner_ph_direct_analysis import analyze_direct_prediction, render_direct_report
from .wagner_ph_direct_config import (
    DIRECT_CAMPAIGN_FORMAT,
    DIRECT_EMERGENCE_FORMAT,
    DIRECT_PEDIGREE_FORMAT,
    DIRECT_VARIANTS,
    DirectPredictionSpec,
    direct_prediction_spec,
    variant_settings,
)


EMERGENCE_INTERVENTIONS = (
    "natural",
    "independent_history",
    "opposite_history",
    "zero",
    "reader_off",
    "renewal_off",
)


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _payload_digest(value: dict[str, Any], field: str) -> str:
    payload = dict(value)
    archived = payload.pop(field, None)
    actual = canonical_digest(payload)
    if archived != actual:
        raise ValueError(f"{field} mismatch")
    return actual


def _soft_deadline(started: float, spec: DirectPredictionSpec) -> float:
    value = os.environ.get("GRE_WAGNER_PH_DIRECT_SOFT_DEADLINE_EPOCH")
    if value is None:
        return started + spec.soft_wall_seconds
    try:
        return float(value)
    except ValueError as error:
        raise ValueError("invalid direct-prediction soft deadline") from error


def _prior_consumed_seconds() -> float:
    value = os.environ.get("GRE_WAGNER_PH_DIRECT_PRIOR_CONSUMED_SECONDS", "0")
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError("invalid direct-prediction consumed-time ledger") from error
    if result < 0.0:
        raise ValueError("direct-prediction consumed time cannot be negative")
    return result


def _require_budget(deadline: float, reservation: int, stage: str) -> None:
    if deadline - time.time() < reservation:
        raise TimeoutError(
            f"insufficient registered soft-wall reserve to start {stage} "
            f"(requires {reservation} seconds)"
        )


def _write_progress(
    destination: Path,
    stage: str,
    completed: int,
    total: int,
    started: float,
    detail: str | None = None,
) -> None:
    elapsed = max(time.monotonic() - started, 0.0)
    rate = completed / elapsed if completed and elapsed else 0.0
    _atomic_json(
        destination / "progress.json",
        {
            "format": "gre-wagner-ph-direct-prediction-progress-v1",
            "stage": stage,
            "detail": detail,
            "completed_units": completed,
            "total_units": total,
            "elapsed_seconds": elapsed,
            "units_per_second": rate,
            "eta_seconds": (total - completed) / rate if rate else None,
        },
    )


def _parent_diagnostic(parent: Path) -> dict[str, Any]:
    """Record the post-hoc signal that prospectively motivates this experiment."""

    verification = verify_wagner_ph_cooption_campaign(parent)
    registration = read_json(parent / "registration.json")
    if registration["protocol"]["cohort_id"] != "wagner-ph-cooption-v1":
        raise ValueError("direct-prediction parent is not co-option v1")
    audit = read_json(parent / "audit" / "analysis.json")
    treatments = audit["treatments"]
    fields = (
        "information_high",
        "information_low",
        "predictability_interaction",
        "natural_minus_zero",
        "opposite_donor_following",
        "reader_dependence",
        "renewal_dependence",
        "decoder_balanced_accuracy",
    )
    extracted = {
        treatment: {
            field: treatments[treatment]["intervals"][field] for field in fields
        }
        for treatment in (
            "direct_independent",
            "cooption_independent",
            "direct_linked",
            "cooption_linked",
            "direct_linked_ramp",
            "cooption_linked_ramp",
        )
    }
    trajectories: dict[str, Any] = {}
    for treatment in extracted:
        populations = [
            read_json(path)
            for path in sorted(
                (parent / "evolution" / "populations").glob(
                    f"{treatment}.population-*.json"
                )
            )
        ]
        generation_summaries: dict[str, Any] = {}
        for generation in (0, 15, 30):
            rows = [value["trace"][generation] for value in populations]
            generation_summaries[str(generation)] = {
                field: float(np.mean([row[field] for row in rows]))
                for field in (
                    "mean_capacity",
                    "mean_precision",
                    "writer_active_fraction",
                    "reader_active_fraction",
                    "validation_best_performance",
                    "training_minus_validation",
                )
            }
        trajectories[treatment] = generation_summaries
    result = {
        "format": "gre-wagner-ph-direct-prediction-parent-diagnostic-v1",
        "parent": str(parent.resolve()),
        "parent_checksum_digest": sha256_file(parent / "SHA256SUMS"),
        "parent_analysis_digest": read_json(parent / "analysis.json")["analysis_digest"],
        "parent_verification": verification,
        "outcome_was_known_before_this_fresh_seed_protocol": True,
        "direct_independent_was_not_the_cooption_nominee": True,
        "protected_cooption_confirmation_remains_untouched": True,
        "heldout_effects": extracted,
        "selection_trajectories": trajectories,
    }
    result["diagnostic_digest"] = canonical_digest(result)
    return result


def _selected_at_generation(population: dict[str, Any], generation: int) -> dict[str, Any]:
    record = next(
        value for value in population["ancestry"] if int(value["generation"]) == generation
    )
    return sorted(
        record["individuals"],
        key=lambda value: (
            -float(value["training_score"]["fitness"]),
            str(value["genotype_id"]),
        ),
    )[0]


def _emergence_task(
    args: tuple[
        str,
        dict[str, Any],
        dict[str, Any],
        str,
        str,
    ]
) -> dict[str, Any]:
    population_path_text, direct_value, kernel_value, output_text, protocol_digest = args
    population = read_json(Path(population_path_text))
    spec = DirectPredictionSpec.from_dict(direct_value)
    kernel = spec.cooption_spec().from_dict(kernel_value)
    task_index = int(population["population_index"])
    final_path = Path(output_text) / f"task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"emergence shard registration differs: {final_path}")
    generations: list[dict[str, Any]] = []
    for evolutionary_generation in spec.emergence_generations:
        selected = _selected_at_generation(population, evolutionary_generation)
        rulebook, genome = deserialize_genotype(selected)
        scope = (
            f"direct-emergence.task-{task_index:03d}."
            f"generation-{evolutionary_generation:03d}"
        )
        cells = []
        for persistence in (0.0, 0.9):
            conditions = {
                intervention: simulate_ecology_condition(
                    rulebook,
                    population["task"],
                    genome,
                    kernel,
                    intervention,
                    persistence,
                    0.0,
                    spec.emergence_futures_per_history,
                    kernel.lineage_generations,
                    (kernel.lineage_generations,),
                    scope,
                    master_seed=spec.emergence_seed,
                )
                for intervention in EMERGENCE_INTERVENTIONS
            }
            cells.append({"persistence": persistence, "conditions": conditions})
        generations.append(
            {
                "evolutionary_generation": evolutionary_generation,
                "selected": selected,
                "carrier": selected["carrier"],
                "cells": cells,
            }
        )
    result = {
        "format": DIRECT_EMERGENCE_FORMAT,
        "protocol_digest": protocol_digest,
        "task_index": task_index,
        "task_digest": population["task"]["task_digest"],
        "assay_seed_family": spec.emergence_seed,
        "assay_was_untouched_by_selection": True,
        "generations": generations,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result)
    return result


def _emergence_effect(row: dict[str, Any], kernel_generation: int) -> dict[str, float]:
    cells = {float(value["persistence"]): value for value in row["cells"]}

    def rate(rho: float, intervention: str, field: str) -> float:
        return float(
            cells[rho]["conditions"][intervention]["checkpoints"]
            [str(kernel_generation)][field]
        )

    high_information = rate(0.9, "natural", "correct_rate") - rate(
        0.9, "independent_history", "correct_rate"
    )
    low_information = rate(0.0, "natural", "correct_rate") - rate(
        0.0, "independent_history", "correct_rate"
    )
    return {
        "information_high": high_information,
        "information_low": low_information,
        "predictability_interaction": high_information - low_information,
        "natural_minus_zero": rate(0.9, "natural", "correct_rate")
        - rate(0.9, "zero", "correct_rate"),
        "reader_dependence": rate(0.9, "natural", "correct_rate")
        - rate(0.9, "reader_off", "correct_rate"),
        "renewal_dependence": rate(0.9, "natural", "correct_rate")
        - rate(0.9, "renewal_off", "correct_rate"),
        "opposite_donor_following": rate(0.9, "opposite_history", "wrong_rate")
        - rate(0.9, "opposite_history", "correct_rate"),
    }


def _run_emergence(
    spec: DirectPredictionSpec,
    baseline_evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_direct_emergence(destination)
        return read_json(destination / "analysis.json")
    kernel = spec.cooption_spec()
    evolution_checksum = sha256_file(baseline_evolution / "SHA256SUMS")
    protocol_payload = {
        "direct_spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "baseline_evolution_checksum": evolution_checksum,
        "interventions": EMERGENCE_INTERVENTIONS,
    }
    protocol_digest = canonical_digest(protocol_payload)
    registration = {
        "format": f"{DIRECT_EMERGENCE_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **protocol_payload,
    }
    path = destination / "registration.json"
    if path.is_file() and read_json(path) != registration:
        raise ValueError("existing emergence registration differs")
    if not path.is_file():
        _atomic_json(path, registration)
    shards = destination / "tasks"
    shards.mkdir(exist_ok=True)
    population_files = sorted(
        (baseline_evolution / "populations").glob("direct_independent.population-*.json")
    )
    work = [
        (
            str(path),
            spec.to_dict(),
            kernel.to_dict(),
            str(shards),
            protocol_digest,
        )
        for path in population_files
    ]
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_emergence_task, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_emergence_task, item) for item in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            if progress:
                progress(f"untouched emergence assay {index}/{len(work)} tasks")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: int(value["task_index"]))
    by_generation: dict[str, Any] = {}
    for generation in spec.emergence_generations:
        effects: dict[str, dict[str, float]] = {}
        carriers: dict[str, dict[str, Any]] = {}
        for task in completed:
            row = next(
                value
                for value in task["generations"]
                if int(value["evolutionary_generation"]) == generation
            )
            key = str(task["task_index"])
            effects[key] = _emergence_effect(row, kernel.lineage_generations)
            carriers[key] = row["carrier"]
        fields = tuple(next(iter(effects.values())))
        by_generation[str(generation)] = {
            "effects": effects,
            "intervals": {
                field: _interval(
                    (value[field] for value in effects.values()),
                    spec.emergence_seed,
                    f"direct-emergence.g{generation}.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in fields
            },
            "carriers": carriers,
            "writer_active_tasks": sum(
                float(value["write_rate"]) > 0.0 for value in carriers.values()
            ),
            "reader_active_tasks": sum(
                float(value["coupling"]) > 0.0 for value in carriers.values()
            ),
        }
    founder = by_generation[str(spec.emergence_generations[0])]["effects"]
    final = by_generation[str(spec.emergence_generations[-1])]["effects"]
    differences = {
        key: final[key]["information_high"] - founder[key]["information_high"]
        for key in sorted(set(founder) & set(final), key=int)
    }
    difference_interval = _interval(
        differences.values(),
        spec.emergence_seed,
        "direct-emergence.founder-to-final-information",
        spec.bootstrap_repetitions,
        spec.interval_level,
    )
    analysis = {
        "format": DIRECT_EMERGENCE_FORMAT,
        "tasks": len(completed),
        "by_evolutionary_generation": by_generation,
        "analysis": {
            "founder_to_final_information": {
                "task_values": differences,
                "interval": difference_interval,
                "passes": bool(
                    float(difference_interval["mean"]) >= spec.contrast_gate
                    and float(difference_interval["lower"]) > 0.0
                ),
            }
        },
        "assay_was_untouched_by_selection": True,
    }
    analysis["emergence_digest"] = canonical_digest(analysis)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{DIRECT_EMERGENCE_FORMAT}-manifest",
            "protocol_digest": protocol_digest,
            "task_count": len(completed),
            "workers": workers,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_direct_emergence(destination)
    return analysis


def verify_direct_emergence(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != f"{DIRECT_EMERGENCE_FORMAT}-registration":
        raise ValueError("emergence registration format mismatch")
    payload = {
        "direct_spec": registration["direct_spec"],
        "kernel": registration["kernel"],
        "baseline_evolution_checksum": registration["baseline_evolution_checksum"],
        "interventions": tuple(registration["interventions"]),
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("emergence protocol digest mismatch")
    spec = DirectPredictionSpec.from_dict(registration["direct_spec"])
    files = sorted((directory / "tasks").glob("*.json"))
    if len(files) != spec.task_count or int(manifest["task_count"]) != spec.task_count:
        raise ValueError("emergence task count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"emergence shard protocol mismatch: {path.name}")
        _payload_digest(value, "result_digest")
    _payload_digest(analysis, "emergence_digest")
    return {"verified": True, "tasks": len(files), "checksums": len(checksums)}


def _pedigree_information(
    genotype: tuple[Any, Any],
    task: dict[str, Any],
    kernel: Any,
    seed: str,
    scope: str,
) -> float:
    rulebook, genome = genotype
    conditions = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            genome,
            kernel,
            intervention,
            0.9,
            0.0,
            kernel.audit_futures_per_history,
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


def _pedigree_task(
    args: tuple[str, dict[str, Any], dict[str, Any], str, str]
) -> dict[str, Any]:
    population_text, direct_value, kernel_value, output_text, protocol_digest = args
    population = read_json(Path(population_text))
    spec = DirectPredictionSpec.from_dict(direct_value)
    kernel = spec.cooption_spec().from_dict(kernel_value)
    task_index = int(population["population_index"])
    final_path = Path(output_text) / f"task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"pedigree shard registration differs: {final_path}")
    ranked = sorted(
        population["final_population"],
        key=lambda value: (
            -float(value["training_score"]["fitness"]),
            str(value["genotype_id"]),
        ),
    )[: spec.pedigree_parents_per_task]
    rows: list[dict[str, Any]] = []
    for parent_index, parent_value in enumerate(ranked):
        parent = deserialize_genotype(parent_value)
        root_scope = f"direct-pedigree.task-{task_index:03d}.parent-{parent_index:02d}"
        root_score = _pedigree_information(
            parent, population["task"], kernel, spec.pedigree_seed, root_scope
        )
        for child_index in range(spec.pedigree_children_per_parent):
            child = mutate_genotype(
                parent,
                parent,
                "independent",
                rng_for(
                    spec.pedigree_seed,
                    "direct-pedigree-child",
                    task_index,
                    parent_index,
                    child_index,
                ),
            )
            child_scope = f"{root_scope}.child-{child_index:02d}"
            child_score = _pedigree_information(
                child, population["task"], kernel, spec.pedigree_seed, child_scope
            )
            rows.append(
                {
                    "task_index": task_index,
                    "parent_index": parent_index,
                    "child_index": child_index,
                    "grandchild_index": None,
                    "pedigree_generation": 1,
                    "root_parent_information": root_score,
                    "immediate_parent_information": root_score,
                    "descendant_information": child_score,
                    "retained": root_score > 0.0
                    and child_score >= spec.pedigree_retention_fraction * root_score,
                }
            )
            for grandchild_index in range(spec.pedigree_grandchildren_per_child):
                grandchild = mutate_genotype(
                    child,
                    child,
                    "independent",
                    rng_for(
                        spec.pedigree_seed,
                        "direct-pedigree-grandchild",
                        task_index,
                        parent_index,
                        child_index,
                        grandchild_index,
                    ),
                )
                grandchild_scope = (
                    f"{child_scope}.grandchild-{grandchild_index:02d}"
                )
                grandchild_score = _pedigree_information(
                    grandchild,
                    population["task"],
                    kernel,
                    spec.pedigree_seed,
                    grandchild_scope,
                )
                rows.append(
                    {
                        "task_index": task_index,
                        "parent_index": parent_index,
                        "child_index": child_index,
                        "grandchild_index": grandchild_index,
                        "pedigree_generation": 2,
                        "root_parent_information": root_score,
                        "immediate_parent_information": child_score,
                        "descendant_information": grandchild_score,
                        "retained": root_score > 0.0
                        and grandchild_score
                        >= spec.pedigree_retention_fraction * root_score,
                    }
                )
    result = {
        "format": DIRECT_PEDIGREE_FORMAT,
        "protocol_digest": protocol_digest,
        "task_index": task_index,
        "rows": rows,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result)
    return result


def _run_pedigree(
    spec: DirectPredictionSpec,
    baseline_evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_direct_pedigree(destination)
        return read_json(destination / "analysis.json")
    kernel = spec.cooption_spec()
    protocol_payload = {
        "direct_spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "baseline_evolution_checksum": sha256_file(
            baseline_evolution / "SHA256SUMS"
        ),
    }
    protocol_digest = canonical_digest(protocol_payload)
    registration = {
        "format": f"{DIRECT_PEDIGREE_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **protocol_payload,
    }
    path = destination / "registration.json"
    if path.is_file() and read_json(path) != registration:
        raise ValueError("existing direct-prediction pedigree registration differs")
    if not path.is_file():
        _atomic_json(path, registration)
    shards = destination / "tasks"
    shards.mkdir(exist_ok=True)
    population_files = sorted(
        (baseline_evolution / "populations").glob("direct_independent.population-*.json")
    )
    work = [
        (
            str(path),
            spec.to_dict(),
            kernel.to_dict(),
            str(shards),
            protocol_digest,
        )
        for path in population_files
    ]
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_pedigree_task, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_pedigree_task, item) for item in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            if progress:
                progress(f"mutation pedigree {index}/{len(work)} tasks")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: int(value["task_index"]))
    rows = [row for task in completed for row in task["rows"]]
    if len(rows) != spec.descendant_count:
        raise RuntimeError(
            f"pedigree produced {len(rows)} descendants; expected {spec.descendant_count}"
        )
    task_retention = {
        str(task_index): float(
            np.mean([value["retained"] for value in rows if value["task_index"] == task_index])
        )
        for task_index in range(spec.task_count)
    }
    retention_interval = _interval(
        task_retention.values(),
        spec.pedigree_seed,
        "direct-pedigree.task-retention",
        spec.bootstrap_repetitions,
        spec.interval_level,
    )
    centered_x: list[float] = []
    centered_y: list[float] = []
    for task_index in range(spec.task_count):
        selected = [value for value in rows if value["task_index"] == task_index]
        x = np.asarray(
            [value["immediate_parent_information"] for value in selected], dtype=float
        )
        y = np.asarray([value["descendant_information"] for value in selected], dtype=float)
        centered_x.extend((x - np.mean(x)).tolist())
        centered_y.extend((y - np.mean(y)).tolist())
    x = np.asarray(centered_x, dtype=float)
    y = np.asarray(centered_y, dtype=float)
    denominator = float(np.sum(x * x))
    slope = float(np.sum(x * y) / denominator) if denominator > 0.0 else None
    analysis = {
        "format": DIRECT_PEDIGREE_FORMAT,
        "tasks": spec.task_count,
        "descendant_genotypes": len(rows),
        "rows": rows,
        "analysis": {
            "retention_definition": (
                "descendant information >= 0.70 times its positive root-parent effect"
            ),
            "task_retention": task_retention,
            "retention_interval": retention_interval,
            "task_centered_immediate_parent_offspring_slope": slope,
            "passes": bool(
                float(retention_interval["mean"]) >= spec.pedigree_retention_fraction
                and slope is not None
                and slope > 0.0
            ),
        },
    }
    analysis["pedigree_digest"] = canonical_digest(analysis)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{DIRECT_PEDIGREE_FORMAT}-manifest",
            "protocol_digest": protocol_digest,
            "tasks": spec.task_count,
            "descendants": len(rows),
            "workers": workers,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_direct_pedigree(destination)
    return analysis


def verify_direct_pedigree(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != f"{DIRECT_PEDIGREE_FORMAT}-registration":
        raise ValueError("pedigree registration format mismatch")
    payload = {
        "direct_spec": registration["direct_spec"],
        "kernel": registration["kernel"],
        "baseline_evolution_checksum": registration["baseline_evolution_checksum"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("pedigree protocol digest mismatch")
    spec = DirectPredictionSpec.from_dict(registration["direct_spec"])
    files = sorted((directory / "tasks").glob("*.json"))
    if len(files) != spec.task_count or int(manifest["descendants"]) != spec.descendant_count:
        raise ValueError("pedigree task or descendant count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"pedigree shard protocol mismatch: {path.name}")
        _payload_digest(value, "result_digest")
    _payload_digest(analysis, "pedigree_digest")
    return {
        "verified": True,
        "tasks": len(files),
        "descendants": spec.descendant_count,
        "checksums": len(checksums),
    }


def run_wagner_ph_direct_prediction_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = direct_prediction_spec(smoke=smoke)
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("direct-prediction campaign permits one to four CPU workers")
    parent = parent.resolve()
    destination = destination.resolve()
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_direct_prediction_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_monotonic = time.monotonic()
    started_epoch = time.time()
    deadline = _soft_deadline(started_epoch, spec)
    prior_consumed = _prior_consumed_seconds()
    kernel = spec.cooption_spec()
    parent_diagnostic = _parent_diagnostic(parent)
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": DIRECT_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "simulation_kernel": kernel.to_dict(),
        "simulation_kernel_digest": canonical_digest(kernel.to_dict()),
        "parent": str(parent),
        "parent_checksum_digest": parent_diagnostic["parent_checksum_digest"],
        "parent_diagnostic_digest": parent_diagnostic["diagnostic_digest"],
        "cpu_only": True,
        "workers_requested": workers,
        "protected_cooption_confirmation_authorized": False,
        "protected_cooption_confirmation_rng_draws_consumed": 0,
        "post_hoc_parent_signal_is_not_counted_as_replication": True,
    }
    for path, value in (
        (destination / "registration.json", registration),
        (destination / "parent-diagnostic.json", parent_diagnostic),
    ):
        if path.is_file() and read_json(path) != value:
            raise ValueError(f"existing direct-prediction {path.name} differs")
        if not path.is_file():
            _atomic_json(path, value)

    _require_budget(deadline, spec.stage_reservations_seconds[0], "parent diagnosis")
    _write_progress(destination, "parent-diagnosis", 1, 1, started_monotonic)

    _require_budget(deadline, spec.stage_reservations_seconds[1], "paired evolution")
    evolution_root = destination / "evolution"
    evolution_root.mkdir(exist_ok=True)
    for index, name in enumerate(spec.variants, start=1):
        settings = variant_settings(name)
        if progress:
            progress(f"direct predictive evolution variant {index}/{len(spec.variants)}: {name}")
        run_cooption_evolution(
            kernel,
            evolution_root / name,
            workers,
            progress,
            treatments=("direct_independent",),
            task_count=spec.task_count,
            master_seed=spec.master_seed,
            carrier_constraint=settings["carrier_constraint"],
            predictive_persistence=float(settings["predictive_persistence"]),
            resource_cost_multiplier=float(settings["resource_cost_multiplier"]),
        )
        _write_progress(
            destination,
            "paired-evolution",
            index,
            len(spec.variants),
            started_monotonic,
            name,
        )

    _require_budget(deadline, spec.stage_reservations_seconds[2], "untouched causal audit")
    audit_root = destination / "audit"
    audit_root.mkdir(exist_ok=True)
    audits: dict[str, list[dict[str, Any]]] = {}
    for index, name in enumerate(spec.variants, start=1):
        if progress:
            progress(f"untouched causal audit variant {index}/{len(spec.variants)}: {name}")
        run_cooption_audit(
            kernel,
            evolution_root / name,
            audit_root / name,
            workers,
            progress,
        )
        audits[name] = [
            read_json(path)
            for path in sorted((audit_root / name / "populations").glob("*.json"))
        ]
        _write_progress(
            destination,
            "causal-audit",
            index,
            len(spec.variants),
            started_monotonic,
            name,
        )

    baseline = evolution_root / "rho90_full"
    _require_budget(deadline, spec.stage_reservations_seconds[3], "emergence assay")
    if progress:
        progress("starting untouched generation-by-generation emergence assay")
    emergence = _run_emergence(
        spec, baseline, destination / "emergence", workers, progress
    )
    _write_progress(destination, "emergence", 1, 1, started_monotonic)

    _require_budget(deadline, spec.stage_reservations_seconds[4], "mutation pedigree")
    if progress:
        progress("starting child and grandchild mutation pedigree")
    pedigree = _run_pedigree(
        spec, baseline, destination / "pedigree", workers, progress
    )
    _write_progress(destination, "pedigree", 1, 1, started_monotonic)

    _require_budget(deadline, spec.stage_reservations_seconds[5], "analysis and sealing")
    analysis = analyze_direct_prediction(
        audits, spec, emergence, pedigree, parent_diagnostic
    )
    _atomic_json(destination / "analysis.json", analysis)
    elapsed = time.monotonic() - started_monotonic
    cumulative = prior_consumed + elapsed
    manifest = {
        "format": DIRECT_CAMPAIGN_FORMAT,
        "protocol_digest": protocol_digest,
        "simulation_kernel_digest": canonical_digest(kernel.to_dict()),
        "parent_checksum_digest": parent_diagnostic["parent_checksum_digest"],
        "analysis_digest": analysis["analysis_digest"],
        "variant_evolution_checksums": {
            name: sha256_file(evolution_root / name / "SHA256SUMS")
            for name in spec.variants
        },
        "variant_audit_checksums": {
            name: sha256_file(audit_root / name / "SHA256SUMS")
            for name in spec.variants
        },
        "emergence_checksum": sha256_file(destination / "emergence" / "SHA256SUMS"),
        "pedigree_checksum": sha256_file(destination / "pedigree" / "SHA256SUMS"),
        "populations": spec.population_count,
        "descendants": spec.descendant_count,
        "maximum_workers": workers,
        "cpu_only": True,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior_consumed,
        "cumulative_wall_seconds": cumulative,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_four_hour_boundary": cumulative <= spec.hard_wall_seconds,
        "protected_cooption_confirmation_rng_draws_consumed": 0,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    (destination / "report.md").write_text(
        render_direct_report(analysis), encoding="utf-8"
    )
    _write_progress(destination, "sealing", 1, 1, started_monotonic)
    write_checksums(destination)
    verify_wagner_ph_direct_prediction_campaign(destination)
    if progress:
        progress("sealed and independently verified direct-prediction PH campaign")
    return destination


def verify_wagner_ph_direct_prediction_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    diagnostic = read_json(directory / "parent-diagnostic.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != DIRECT_CAMPAIGN_FORMAT or manifest.get("format") != DIRECT_CAMPAIGN_FORMAT:
        raise ValueError("direct-prediction campaign format mismatch")
    spec = DirectPredictionSpec.from_dict(registration["protocol"])
    protocol_digest = canonical_digest(spec.to_dict())
    if protocol_digest != registration["protocol_digest"] or protocol_digest != manifest["protocol_digest"]:
        raise ValueError("direct-prediction protocol digest mismatch")
    kernel = spec.cooption_spec()
    kernel_digest = canonical_digest(kernel.to_dict())
    if kernel_digest != registration["simulation_kernel_digest"] or kernel_digest != manifest["simulation_kernel_digest"]:
        raise ValueError("direct-prediction simulation kernel mismatch")
    _payload_digest(diagnostic, "diagnostic_digest")
    if diagnostic["diagnostic_digest"] != registration["parent_diagnostic_digest"]:
        raise ValueError("direct-prediction parent diagnostic mismatch")
    parent = Path(registration["parent"])
    if sha256_file(parent / "SHA256SUMS") != registration["parent_checksum_digest"]:
        raise ValueError("sealed co-option parent changed")
    verify_wagner_ph_cooption_campaign(parent)
    evolution_root = directory / "evolution"
    audit_root = directory / "audit"
    for name in spec.variants:
        verify_cooption_evolution(evolution_root / name)
        verify_cooption_audit(audit_root / name)
        if sha256_file(evolution_root / name / "SHA256SUMS") != manifest["variant_evolution_checksums"][name]:
            raise ValueError(f"evolution checksum changed: {name}")
        if sha256_file(audit_root / name / "SHA256SUMS") != manifest["variant_audit_checksums"][name]:
            raise ValueError(f"audit checksum changed: {name}")
    verify_direct_emergence(directory / "emergence")
    verify_direct_pedigree(directory / "pedigree")
    if sha256_file(directory / "emergence" / "SHA256SUMS") != manifest["emergence_checksum"]:
        raise ValueError("emergence checksum changed")
    if sha256_file(directory / "pedigree" / "SHA256SUMS") != manifest["pedigree_checksum"]:
        raise ValueError("pedigree checksum changed")
    _payload_digest(analysis, "analysis_digest")
    if analysis["analysis_digest"] != manifest["analysis_digest"]:
        raise ValueError("direct-prediction analysis digest mismatch")
    if (
        registration.get("protected_cooption_confirmation_rng_draws_consumed") != 0
        or manifest.get("protected_cooption_confirmation_rng_draws_consumed") != 0
        or analysis.get("protected_cooption_confirmation_seed_consumed") is not False
    ):
        raise ValueError("protected co-option confirmation reserve was consumed")
    if not 1 <= int(manifest["maximum_workers"]) <= 4:
        raise ValueError("direct-prediction worker cap violated")
    return {
        "verified": True,
        "checksums": len(checksums),
        "populations": spec.population_count,
        "descendants": spec.descendant_count,
        "direct_origin_replicated": analysis["direct_origin_replicated"],
        "all_six_predictions_pass": analysis["all_six_predictions_pass"],
    }


def wagner_ph_direct_prediction_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    if (directory / "SHA256SUMS").is_file():
        try:
            verification = verify_wagner_ph_direct_prediction_campaign(directory)
            manifest = read_json(directory / "campaign-manifest.json")
            return {
                "status": "completed",
                **verification,
                "elapsed_seconds": manifest["elapsed_seconds"],
                "cumulative_wall_seconds": manifest["cumulative_wall_seconds"],
            }
        except Exception as error:
            return {"status": "sealed-invalid", "error": str(error)}
    progress = (
        read_json(directory / "progress.json")
        if (directory / "progress.json").is_file()
        else {}
    )
    return {
        "status": "running-or-resumable",
        "stage": progress.get("stage", "preparing"),
        "detail": progress.get("detail"),
        "completed_units": progress.get("completed_units", 0),
        "total_units": progress.get("total_units"),
        "elapsed_seconds": progress.get("elapsed_seconds"),
        "eta_seconds": progress.get("eta_seconds"),
    }
