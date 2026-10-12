"""Frozen diagnosis, causal audits, and mutation pedigrees for Resilience v1."""

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
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import deserialize_genotype as deserialize_base_genotype
from .wagner_ph_cooption_experiment import history_information, simulate_ecology_condition
from .wagner_ph_resilience_config import (
    DIAGNOSTIC_CONDITIONS,
    RESILIENCE_FORMAT,
    ResilienceSpec,
    arm_settings,
)
from .wagner_ph_resilience_evolution import verify_resilience_evolution
from .wagner_ph_resilience_genome import (
    Genome,
    deserialize_genome,
    effective_genotype,
    initialize_interpreter,
    mutate_genome,
    mutation_delta,
    serialize_genome,
)


DIAGNOSTIC_FORMAT = f"{RESILIENCE_FORMAT}-diagnosis"
AUDIT_FORMAT = f"{RESILIENCE_FORMAT}-audit"
PEDIGREE_FORMAT = f"{RESILIENCE_FORMAT}-pedigree"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _phase_seed(spec: ResilienceSpec, phase: str, domain: str) -> str:
    base = {"audit": spec.audit_seed, "pedigree": spec.pedigree_seed}[domain]
    return base if phase == "development" else canonical_digest((spec.confirmation_seed, domain))


def pedigree_information(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: ResilienceSpec,
    scope: str,
    phase: str,
    *,
    futures: int | None = None,
    seed_override: str | None = None,
) -> float:
    rulebook, carrier = effective_genotype(genome)
    seed = seed_override or _phase_seed(spec, phase, "pedigree")
    conditions = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            carrier,
            kernel,
            intervention,
            spec.predictive_persistence,
            0.0,
            futures or spec.pedigree_futures_per_history,
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


def _diagnostic_base(value: dict[str, Any], condition: str) -> Genome:
    rulebook, carrier = deserialize_base_genotype(value)
    if condition.startswith("repair_"):
        strength = int(condition.removeprefix("repair_")) / 10.0
        return initialize_interpreter(rulebook, "repair", strength), carrier
    architecture = "triplicate" if condition.startswith("triplicate") else "single"
    return initialize_interpreter(rulebook, architecture), carrier


def _fixed_diagnostic_mutation(
    genome: Genome, condition: str, random: np.random.Generator, spec: ResilienceSpec
) -> Genome:
    if condition.startswith("repair_"):
        strength = genome[0].repair_strength
        child = mutate_genome(genome, genome, "lineage4_repair", random, spec)
        return type(child[0])(child[0].copies, "repair", strength), child[1]
    if condition.startswith("triplicate"):
        return mutate_genome(
            genome,
            genome,
            "lineage4_triplicate",
            random,
            spec,
            mechanism_off=condition == "triplicate_concerted",
        )
    return mutate_genome(genome, genome, "lineage4_reset", random, spec)


def _diagnostic_task(args: tuple[str, str, dict[str, Any], dict[str, Any], str, str]) -> dict[str, Any]:
    reference_population_text, atlas_task_text, spec_value, kernel_value, output_text, digest = args
    population = read_json(Path(reference_population_text))
    atlas = read_json(Path(atlas_task_text))
    spec = ResilienceSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(population["population_index"])
    final_path = Path(output_text) / f"task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("resilience diagnostic shard registration differs")
    ranked = sorted(
        population["final_population"],
        key=lambda value: (-float(value["selection_score"]["fitness"]), str(value["genotype_id"])),
    )[:spec.diagnostic_roots_per_task]
    concentration: list[dict[str, Any]] = []
    for root in atlas["roots"][:spec.diagnostic_roots_per_task]:
        by_edge: dict[int, list[float]] = {}
        for row in root["rows"]:
            by_edge.setdefault(int(row["edge_index"]), []).append(min(float(row["delta"]["information_high"]), 0.0))
        damage = sorted((-float(np.mean(values)) for values in by_edge.values()), reverse=True)
        total = sum(damage)
        concentration.append({
            "root_index": int(root["root_index"]),
            "top_1_share": sum(damage[:1]) / total if total else 0.0,
            "top_5_share": sum(damage[:5]) / total if total else 0.0,
            "top_10_share": sum(damage[:10]) / total if total else 0.0,
            "total_negative_information_damage": total,
        })
    rows: list[dict[str, Any]] = []
    ancestry: list[dict[str, Any]] = []
    for root_index, value in enumerate(ranked):
        for condition in DIAGNOSTIC_CONDITIONS:
            root = _diagnostic_base(value, condition)
            root_scope = f"resilience-diagnosis.task-{task_index:03d}.root-{root_index:02d}.{condition}"
            root_information = pedigree_information(
                root, population["task"], kernel, spec, root_scope, "development",
                futures=spec.diagnostic_futures_per_history, seed_override=spec.diagnostic_seed,
            )
            condition_record = {"root_index": root_index, "condition": condition, "root": serialize_genome(root), "root_information": root_information, "chains": []}
            for lineage_index in range(spec.diagnostic_chains_per_root):
                current = root
                chain = []
                for distance in range(1, 5):
                    child = _fixed_diagnostic_mutation(
                        current,
                        condition,
                        rng_for(spec.diagnostic_seed, "resilience-diagnostic-mutation", condition, task_index, root_index, lineage_index, distance),
                        spec,
                    )
                    information = None
                    if distance in spec.pedigree_depths:
                        information = pedigree_information(
                            child, population["task"], kernel, spec,
                            f"{root_scope}.lineage-{lineage_index:02d}.distance-{distance:02d}",
                            "development", futures=spec.diagnostic_futures_per_history,
                            seed_override=spec.diagnostic_seed,
                        )
                        rows.append({
                            "task_index": task_index, "root_index": root_index, "condition": condition,
                            "lineage_index": lineage_index, "distance": distance,
                            "root_information": root_information, "descendant_information": information,
                            "eligible_positive_root": root_information > 0.0,
                            "retained": root_information > 0.0 and information >= spec.retention_fraction * root_information,
                            "collapsed": root_information > 0.0 and information <= 0.0,
                        })
                    chain.append({"distance": distance, "genotype": serialize_genome(child), "mutation_delta": mutation_delta(current, child), "information": information})
                    current = child
                condition_record["chains"].append({"lineage_index": lineage_index, "chain": chain})
            ancestry.append(condition_record)
    result = {
        "format": DIAGNOSTIC_FORMAT, "protocol_digest": digest, "task_index": task_index,
        "task": population["task"], "edge_damage_concentration": concentration,
        "rows": rows, "row_count": len(rows), "complete_ancestry": ancestry,
        "diagnosis_cannot_change_later_arms_costs_thresholds_or_mutation_targeting": True,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result)
    return result


def _parallel(
    work: list[tuple[Any, ...]], worker: Callable[[tuple[Any, ...]], dict[str, Any]], workers: int,
    callback: Callable[[int, dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(worker, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
        futures = [executor.submit(worker, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, 1):
            completed.append(result)
            if callback:
                callback(index, result)
    finally:
        if executor is not None:
            executor.shutdown()
    return completed


def run_resilience_diagnosis(
    spec: ResilienceSpec, reference: Path, destination: Path, workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_resilience_diagnosis(destination)
        return destination
    reference = reference.resolve()
    reference_checksum = sha256_file(reference / "SHA256SUMS")
    kernel = spec.kernel()
    payload = {"spec": spec.to_dict(), "kernel": kernel.to_dict(), "reference_checksum": reference_checksum}
    digest = canonical_digest(payload)
    registration = {"format": f"{DIAGNOSTIC_FORMAT}-registration", "protocol_digest": digest, **payload, "reference": str(reference)}
    _atomic_json(destination / "registration.json", registration)
    shards = destination / "tasks"
    shards.mkdir(exist_ok=True)
    population_files = sorted((reference / "development" / "evolution" / "populations").glob("individual_reset.population-*.json"))
    atlas_files = sorted((reference / "atlas" / "tasks").glob("task-*.json"))
    if len(population_files) < spec.task_count or len(atlas_files) < spec.task_count:
        raise ValueError("sealed Interpreter-Depth reference is incomplete")
    population_files = population_files[:spec.task_count]
    atlas_files = atlas_files[:spec.task_count]
    work = [(str(population_files[index]), str(atlas_files[index]), spec.to_dict(), kernel.to_dict(), str(shards), digest) for index in range(spec.task_count)]
    started = time.monotonic()
    def update(index: int, _: dict[str, Any]) -> None:
        _atomic_json(destination / "progress.json", {"completed_tasks": index, "total_tasks": len(work), "elapsed_seconds": time.monotonic()-started})
        if progress:
            progress(f"interpreter-resilience diagnosis {index}/{len(work)} tasks")
    completed = _parallel(work, _diagnostic_task, workers, update)
    rows = [row for value in completed for row in value["rows"]]
    summaries: dict[str, Any] = {}
    for condition in DIAGNOSTIC_CONDITIONS:
        distances = {}
        for distance in spec.pedigree_depths:
            selected = [row for row in rows if row["condition"] == condition and row["distance"] == distance]
            task_values = {}
            for task in range(spec.task_count):
                eligible = [row for row in selected if row["task_index"] == task and row["eligible_positive_root"]]
                task_values[str(task)] = float(np.mean([row["retained"] for row in eligible])) if eligible else 0.0
            distances[str(distance)] = {"task_retention": task_values, "interval": _interval(task_values.values(), spec.diagnostic_seed, f"resilience-diagnosis.{condition}.d{distance}", spec.bootstrap_repetitions, spec.interval_level)}
        summaries[condition] = {"distances": distances}
    concentration = [row for value in completed for row in value["edge_damage_concentration"]]
    analysis = {
        "format": f"{DIAGNOSTIC_FORMAT}-analysis", "conditions": summaries,
        "edge_damage_concentration": {
            field: float(np.mean([row[field] for row in concentration]))
            for field in ("top_1_share", "top_5_share", "top_10_share")
        },
        "diagnostic_only": True,
    }
    analysis["analysis_digest"] = canonical_digest(analysis)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {"format": f"{DIAGNOSTIC_FORMAT}-manifest", "protocol_digest": digest, "tasks": len(completed), "rows": len(rows), "elapsed_seconds": time.monotonic()-started, "runtime": runtime_manifest()})
    write_checksums(destination)
    verify_resilience_diagnosis(destination)
    return destination


def verify_resilience_diagnosis(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    spec = ResilienceSpec.from_dict(registration["spec"])
    if sha256_file(Path(registration["reference"]) / "SHA256SUMS") != registration["reference_checksum"]:
        raise ValueError("sealed Interpreter-Depth reference changed")
    payload = {"spec": registration["spec"], "kernel": registration["kernel"], "reference_checksum": registration["reference_checksum"]}
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("resilience diagnosis protocol mismatch")
    files = sorted((directory / "tasks").glob("task-*.json"))
    expected_rows = spec.task_count * spec.diagnostic_roots_per_task * len(DIAGNOSTIC_CONDITIONS) * spec.diagnostic_chains_per_root * len(spec.pedigree_depths)
    if len(files) != spec.task_count or sum(read_json(path)["row_count"] for path in files) != expected_rows:
        raise ValueError("resilience diagnosis is incomplete")
    return {"verified": True, "tasks": len(files), "rows": expected_rows, "checksums": len(checksums)}


def _audit_population(args: tuple[str, dict[str, Any], dict[str, Any], str, str, str]) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, digest, phase = args
    archived = read_json(Path(population_text))
    spec = ResilienceSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    final_path = Path(output_text) / Path(population_text).name
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("resilience audit shard registration differs")
    genome = deserialize_genome(archived["selected"])
    rulebook, carrier = effective_genotype(genome)
    task_index = int(archived["population_index"])
    seed = _phase_seed(spec, phase, "audit")
    scope = f"interpreter-resilience-{phase}-audit.task-{task_index:03d}"
    cells = []
    for persistence in spec.audit_persistence:
        for cue_fraction in spec.audit_cue_fractions:
            conditions = {
                intervention: simulate_ecology_condition(
                    rulebook, archived["task"], carrier, kernel, intervention, persistence,
                    cue_fraction, spec.audit_futures_per_history, kernel.lineage_generations,
                    kernel.checkpoints, scope, master_seed=seed,
                )
                for intervention in kernel.meaning_interventions
            }
            cells.append({
                "cell_id": f"rho{persistence:.2f}.cue{cue_fraction:.2f}",
                "persistence": persistence, "cue_fraction": cue_fraction,
                "conditions": conditions,
                "history_information": history_information(conditions["natural"]["final_carriers"]),
            })
    result = {
        "format": AUDIT_FORMAT, "protocol_digest": digest, "phase": phase,
        "population_id": archived["population_id"], "population_index": task_index,
        "arm": archived["arm"], "arm_settings": archived["arm_settings"],
        "task": archived["task"], "selected": archived["selected"],
        "selected_effective_genotype": archived["selected_effective_genotype"],
        "selected_training_score": archived["selected_training_score"],
        "selected_selection_score": archived["selected_selection_score"],
        "audit_streams_are_held_out_from_selection": True, "cells": cells,
    }
    result["result_digest"] = canonical_digest({"selected": result["selected"], "cells": cells})
    _atomic_json(final_path, result)
    return result


def run_resilience_audit(
    spec: ResilienceSpec, evolution: Path, destination: Path, workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_resilience_evolution(evolution)
    registration_evolution = read_json(evolution / "registration.json")
    phase, arms = registration_evolution["phase"], tuple(registration_evolution["selected_arms"])
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_resilience_audit(destination)
        return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    payload = {"spec": spec.to_dict(), "kernel": kernel.to_dict(), "evolution_checksum": sha256_file(evolution / "SHA256SUMS"), "phase": phase, "selected_arms": list(arms)}
    digest = canonical_digest(payload)
    _atomic_json(destination / "registration.json", {"format": f"{AUDIT_FORMAT}-registration", "protocol_digest": digest, **payload, "evolution": str(evolution)})
    shards = destination / "populations"; shards.mkdir(exist_ok=True)
    files = sorted(path for path in (evolution / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json"))
    work = [(str(path), spec.to_dict(), kernel.to_dict(), str(shards), digest, phase) for path in files]
    started = time.monotonic()
    def update(index: int, _: dict[str, Any]) -> None:
        _atomic_json(destination / "progress.json", {"completed_populations": index, "total_populations": len(work), "elapsed_seconds": time.monotonic()-started})
        if progress: progress(f"interpreter-resilience {phase} audit {index}/{len(work)} populations")
    completed = _parallel(work, _audit_population, workers, update)
    summaries = {}
    for arm in arms:
        selected = [value for value in completed if value["arm"] == arm]
        effects = {str(value["population_index"]): population_effects(value, kernel) for value in selected}
        summaries[arm] = {"populations": len(selected), "task_effects": effects, "intervals": {
            field: _interval((row[field] for row in effects.values()), _phase_seed(spec, phase, "audit"), f"resilience-{phase}.{arm}.{field}", spec.bootstrap_repetitions, spec.interval_level)
            for field in next(iter(effects.values()))
        }}
    analysis = {"format": f"{AUDIT_FORMAT}-analysis", "phase": phase, "summaries": summaries, "selection_data_are_not_used_as_ph_evidence": True}
    analysis["analysis_digest"] = canonical_digest(analysis)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {"format": f"{AUDIT_FORMAT}-manifest", "protocol_digest": digest, "population_count": len(completed), "elapsed_seconds": time.monotonic()-started, "runtime": runtime_manifest()})
    write_checksums(destination); verify_resilience_audit(destination)
    return destination


def verify_resilience_audit(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory); registration = read_json(directory / "registration.json")
    spec = ResilienceSpec.from_dict(registration["spec"])
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed resilience evolution changed after audit")
    payload = {key: registration[key] for key in ("spec", "kernel", "evolution_checksum", "phase", "selected_arms")}
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("resilience audit protocol mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    files = sorted((directory / "populations").glob("*.json")); expected = task_count * len(registration["selected_arms"])
    if len(files) != expected:
        raise ValueError("resilience audit is incomplete")
    return {"verified": True, "phase": registration["phase"], "populations": len(files), "checksums": len(checksums)}


def _population_pedigree(args: tuple[str, dict[str, Any], dict[str, Any], str, str, str]) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, digest, phase = args
    population = read_json(Path(population_text)); spec = ResilienceSpec.from_dict(spec_value); kernel = CooptionSpec.from_dict(kernel_value)
    arm, task_index = population["arm"], int(population["population_index"])
    final_path = Path(output_text) / f"{arm}.task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest: return prior
        raise ValueError("resilience pedigree shard registration differs")
    ranked = sorted(population["final_population"], key=lambda value: (-float(value["selection_score"]["fitness"]), value["genotype_id"]))[:spec.pedigree_roots_per_task]
    modes = ("natural", "mechanism_off") if arm_settings(arm)["architecture"] != "single" else ("natural",)
    rows, ancestry = [], []
    seed = _phase_seed(spec, phase, "pedigree")
    for root_index, root_value in enumerate(ranked):
        root = deserialize_genome(root_value)
        root_scope = f"resilience-{phase}-pedigree.task-{task_index:03d}.root-{root_index:02d}"
        root_information = pedigree_information(root, population["task"], kernel, spec, root_scope, phase)
        root_record = {"root_index": root_index, "root": serialize_genome(root), "root_information": root_information, "modes": []}
        for mode in modes:
            mode_record = {"mode": mode, "chains": []}
            for lineage_index in range(spec.pedigree_lineages_per_root):
                current, immediate, chain = root, root_information, []
                for distance in range(1, 5):
                    child = mutate_genome(
                        current, current, arm,
                        rng_for(seed, "resilience-pedigree-mutation", arm, task_index, root_index, lineage_index, distance),
                        spec, mechanism_off=mode == "mechanism_off",
                    )
                    information = pedigree_information(child, population["task"], kernel, spec, f"{root_scope}.{mode}.lineage-{lineage_index:02d}.distance-{distance:02d}", phase)
                    chain.append({"distance": distance, "genotype": serialize_genome(child), "mutation_delta": mutation_delta(current, child), "information": information})
                    rows.append({
                        "phase": phase, "arm": arm, "mode": mode, "task_index": task_index,
                        "root_index": root_index, "lineage_index": lineage_index, "distance": distance,
                        "root_information": root_information, "immediate_parent_information": immediate,
                        "descendant_information": information, "eligible_positive_root": root_information > 0.0,
                        "retained": root_information > 0.0 and information >= spec.retention_fraction * root_information,
                        "collapsed": root_information > 0.0 and information <= 0.0,
                    })
                    current, immediate = child, information
                mode_record["chains"].append({"lineage_index": lineage_index, "chain": chain})
            root_record["modes"].append(mode_record)
        ancestry.append(root_record)
    result = {"format": PEDIGREE_FORMAT, "protocol_digest": digest, "phase": phase, "population_id": population["population_id"], "arm": arm, "task_index": task_index, "task": population["task"], "rows": rows, "row_count": len(rows), "complete_ancestry": ancestry, "mutation_stream_coordinates_are_replayable": True}
    result["result_digest"] = canonical_digest(result); _atomic_json(final_path, result); return result


def _task_centered_slope(rows: list[dict[str, Any]], task_count: int) -> float | None:
    xs, ys = [], []
    for task in range(task_count):
        selected = [row for row in rows if row["task_index"] == task]
        x = np.asarray([row["immediate_parent_information"] for row in selected]); y = np.asarray([row["descendant_information"] for row in selected])
        if len(x): xs.extend((x-x.mean()).tolist()); ys.extend((y-y.mean()).tolist())
    x, y = np.asarray(xs), np.asarray(ys); denominator = float(np.sum(x*x))
    return float(np.sum(x*y)/denominator) if denominator > 0 else None


def _analyze_pedigrees(results: list[dict[str, Any]], spec: ResilienceSpec, phase: str, arms: tuple[str, ...]) -> dict[str, Any]:
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = _phase_seed(spec, phase, "pedigree"); summaries = {}
    for arm in arms:
        arm_modes = sorted({row["mode"] for value in results if value["arm"] == arm for row in value["rows"]}, key=lambda value: (value != "natural", value))
        mode_summaries = {}
        for mode in arm_modes:
            rows = [row for value in results if value["arm"] == arm for row in value["rows"] if row["mode"] == mode]
            distances = {}
            for distance in spec.pedigree_depths:
                selected = [row for row in rows if row["distance"] == distance]; retention, collapse, information = {}, {}, {}
                for task in range(task_count):
                    task_rows = [row for row in selected if row["task_index"] == task]; eligible = [row for row in task_rows if row["eligible_positive_root"]]
                    retention[str(task)] = float(np.mean([row["retained"] for row in eligible])) if eligible else 0.0
                    collapse[str(task)] = float(np.mean([row["collapsed"] for row in eligible])) if eligible else 1.0
                    information[str(task)] = float(np.mean([row["descendant_information"] for row in task_rows])) if task_rows else 0.0
                distances[str(distance)] = {
                    "task_retention": retention, "task_collapse_probability": collapse, "task_information": information,
                    "retention_interval": _interval(retention.values(), seed, f"resilience-{phase}.{arm}.{mode}.d{distance}.retention", spec.bootstrap_repetitions, spec.interval_level),
                    "collapse_interval": _interval(collapse.values(), seed, f"resilience-{phase}.{arm}.{mode}.d{distance}.collapse", spec.bootstrap_repetitions, spec.interval_level),
                    "information_interval": _interval(information.values(), seed, f"resilience-{phase}.{arm}.{mode}.d{distance}.information", spec.bootstrap_repetitions, spec.interval_level),
                }
            mode_summaries[mode] = {"rows": len(rows), "distances": distances, "task_centered_immediate_parent_offspring_slope": _task_centered_slope(rows, task_count)}
        summaries[arm] = {"modes": mode_summaries}
    result = {"format": f"{PEDIGREE_FORMAT}-analysis", "phase": phase, "arms": summaries, "retention_definition": "descendant information >= 0.70 times positive root information", "inferential_unit": "paired founder task"}
    result["analysis_digest"] = canonical_digest(result); return result


def run_resilience_pedigree(
    spec: ResilienceSpec, evolution: Path, destination: Path, workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_resilience_evolution(evolution); evolution_registration = read_json(evolution / "registration.json")
    phase, arms = evolution_registration["phase"], tuple(evolution_registration["selected_arms"])
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file(): verify_resilience_pedigree(destination); return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    payload = {"spec": spec.to_dict(), "kernel": kernel.to_dict(), "evolution_checksum": sha256_file(evolution / "SHA256SUMS"), "phase": phase, "selected_arms": list(arms)}
    digest = canonical_digest(payload); _atomic_json(destination / "registration.json", {"format": f"{PEDIGREE_FORMAT}-registration", "protocol_digest": digest, **payload, "evolution": str(evolution)})
    shards = destination / "populations"; shards.mkdir(exist_ok=True)
    files = sorted(path for path in (evolution / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json")); work = [(str(path), spec.to_dict(), kernel.to_dict(), str(shards), digest, phase) for path in files]
    started = time.monotonic()
    def update(index: int, _: dict[str, Any]) -> None:
        _atomic_json(destination / "progress.json", {"completed_populations": index, "total_populations": len(work), "elapsed_seconds": time.monotonic()-started})
        if progress: progress(f"interpreter-resilience {phase} pedigree {index}/{len(work)} populations")
    completed = _parallel(work, _population_pedigree, workers, update)
    analysis = _analyze_pedigrees(completed, spec, phase, arms); _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {"format": f"{PEDIGREE_FORMAT}-manifest", "protocol_digest": digest, "populations": len(completed), "rows": sum(value["row_count"] for value in completed), "elapsed_seconds": time.monotonic()-started, "runtime": runtime_manifest()})
    write_checksums(destination); verify_resilience_pedigree(destination); return destination


def verify_resilience_pedigree(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory); registration = read_json(directory / "registration.json"); spec = ResilienceSpec.from_dict(registration["spec"])
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]: raise ValueError("sealed resilience evolution changed after pedigree")
    payload = {key: registration[key] for key in ("spec", "kernel", "evolution_checksum", "phase", "selected_arms")}
    if canonical_digest(payload) != registration["protocol_digest"]: raise ValueError("resilience pedigree protocol mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    expected_populations = task_count * len(registration["selected_arms"]); files = sorted((directory / "populations").glob("*.json"))
    expected_rows = 0
    for arm in registration["selected_arms"]:
        modes = 1 if arm_settings(arm)["architecture"] == "single" else 2
        expected_rows += task_count * spec.pedigree_roots_per_task * spec.pedigree_lineages_per_root * 4 * modes
    rows = sum(read_json(path)["row_count"] for path in files)
    if len(files) != expected_populations or rows != expected_rows: raise ValueError("resilience pedigree is incomplete")
    return {"verified": True, "phase": registration["phase"], "populations": len(files), "rows": rows, "checksums": len(checksums)}


def replay_resilience_pedigree(directory: Path, population_id: str, root_index: int, lineage_index: int, distance: int, mode: str = "natural") -> dict[str, Any]:
    registration = read_json(directory / "registration.json"); spec = ResilienceSpec.from_dict(registration["spec"]); phase = registration["phase"]
    arm, task_text = population_id.split(".population-"); task = int(task_text)
    shard = read_json(directory / "populations" / f"{arm}.task-{task:03d}.json"); root_record = shard["complete_ancestry"][root_index]
    current = deserialize_genome(root_record["root"]); seed = _phase_seed(spec, phase, "pedigree"); matches = True
    mode_record = next(value for value in root_record["modes"] if value["mode"] == mode)
    for step in range(1, distance+1):
        current = mutate_genome(current, current, arm, rng_for(seed, "resilience-pedigree-mutation", arm, task, root_index, lineage_index, step), spec, mechanism_off=mode == "mechanism_off")
        archived = mode_record["chains"][lineage_index]["chain"][step-1]["genotype"]
        matches &= canonical_digest(serialize_genome(current)) == canonical_digest(archived)
    return {"population_id": population_id, "mode": mode, "distance": distance, "matches": bool(matches)}
