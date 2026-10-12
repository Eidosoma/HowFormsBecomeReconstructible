"""Held-out causal audits and ordinary-mutation pedigrees for Architecture v1."""

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
from .wagner_ph_architecture_config import ARCHITECTURE_FORMAT, ArchitectureSpec, arm_settings
from .wagner_ph_architecture_evolution import verify_architecture_evolution
from .wagner_ph_architecture_genome import (
    ArchitectureInterpreter,
    Genome,
    deserialize_genome,
    effective_genotype,
    mutate_genome,
    mutation_delta,
    serialize_genome,
)
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import mutate_carrier
from .wagner_ph_cooption_experiment import history_information, simulate_ecology_condition


AUDIT_FORMAT = f"{ARCHITECTURE_FORMAT}-audit"
PEDIGREE_FORMAT = f"{ARCHITECTURE_FORMAT}-pedigree"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _phase_seed(spec: ArchitectureSpec, phase: str, domain: str) -> str:
    base = spec.audit_seed if domain == "audit" else spec.pedigree_seed
    return base if phase == "development" else canonical_digest((spec.confirmation_seed, domain))


def pedigree_information(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: ArchitectureSpec,
    scope: str,
    phase: str,
) -> float:
    rulebook, carrier = effective_genotype(genome)
    values = {
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
            master_seed=_phase_seed(spec, phase, "pedigree"),
        )
        for intervention in ("natural", "independent_history")
    }
    generation = str(kernel.lineage_generations)
    return float(
        values["natural"]["checkpoints"][generation]["correct_rate"]
        - values["independent_history"]["checkpoints"][generation]["correct_rate"]
    )


def _audit_population(args: tuple[Any, ...]) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, digest, phase = args
    archived = read_json(Path(population_text)); spec = ArchitectureSpec.from_dict(spec_value); kernel = CooptionSpec.from_dict(kernel_value)
    final_path = Path(output_text) / Path(population_text).name
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("architecture audit shard registration differs")
    genome = deserialize_genome(archived["selected"])
    rulebook, carrier = effective_genotype(genome)
    task_index = int(archived["population_index"])
    scope = f"interpreter-architecture-{phase}-audit.task-{task_index:03d}"
    cells = []
    for persistence in spec.audit_persistence:
        for cue_fraction in spec.audit_cue_fractions:
            conditions = {
                intervention: simulate_ecology_condition(
                    rulebook,
                    archived["task"],
                    carrier,
                    kernel,
                    intervention,
                    persistence,
                    cue_fraction,
                    spec.audit_futures_per_history,
                    kernel.lineage_generations,
                    kernel.checkpoints,
                    scope,
                    master_seed=_phase_seed(spec, phase, "audit"),
                )
                for intervention in kernel.meaning_interventions
            }
            cells.append({
                "cell_id": f"rho{persistence:.2f}.cue{cue_fraction:.2f}",
                "persistence": persistence,
                "cue_fraction": cue_fraction,
                "conditions": conditions,
                "history_information": history_information(
                    conditions["natural"]["final_carriers"]
                ),
            })
    result = {
        "format": AUDIT_FORMAT,
        "protocol_digest": digest,
        "phase": phase,
        "population_id": archived["population_id"],
        "population_index": task_index,
        "arm": archived["arm"],
        "arm_settings": archived["arm_settings"],
        "task": archived["task"],
        "selected": archived["selected"],
        "selected_effective_genotype": archived["selected_effective_genotype"],
        "selected_training_score": archived["selected_training_score"],
        "selected_selection_score": archived["selected_selection_score"],
        "audit_streams_are_held_out_from_selection": True,
        "cells": cells,
    }
    result["result_digest"] = canonical_digest({"selected": result["selected"], "cells": cells})
    _atomic_json(final_path, result); return result


def _parallel(
    work: list[tuple[Any, ...]],
    function: Callable[[tuple[Any, ...]], dict[str, Any]],
    workers: int,
    update: Callable[[int, dict[str, Any]], None],
) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(function, work); executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
        futures = [executor.submit(function, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, value in enumerate(iterator, 1):
            completed.append(value); update(index, value)
    finally:
        if executor is not None:
            executor.shutdown()
    return completed


def run_architecture_audit(
    spec: ArchitectureSpec,
    evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_architecture_evolution(evolution)
    evolution_registration = read_json(evolution / "registration.json")
    phase, arms = evolution_registration["phase"], tuple(evolution_registration["selected_arms"])
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_architecture_audit(destination); return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "phase": phase,
        "selected_arms": list(arms),
    }
    digest = canonical_digest(payload)
    registration = {
        "format": f"{AUDIT_FORMAT}-registration", "protocol_digest": digest,
        **payload, "evolution": str(evolution),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing architecture audit registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    shards = destination / "populations"; shards.mkdir(exist_ok=True)
    files = sorted(path for path in (evolution / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json"))
    work = [(str(path), spec.to_dict(), kernel.to_dict(), str(shards), digest, phase) for path in files]
    started = time.monotonic()

    def update(index: int, _: dict[str, Any]) -> None:
        _atomic_json(destination / "progress.json", {"completed_populations": index, "total_populations": len(work), "elapsed_seconds": time.monotonic() - started})
        if progress:
            progress(f"interpreter-architecture {phase} audit {index}/{len(work)} populations")

    completed = _parallel(work, _audit_population, workers, update)
    summaries = {}
    for arm in arms:
        selected = [value for value in completed if value["arm"] == arm]
        effects = {str(value["population_index"]): population_effects(value, kernel) for value in selected}
        summaries[arm] = {
            "populations": len(selected),
            "task_effects": effects,
            "intervals": {
                field: _interval(
                    (row[field] for row in effects.values()),
                    _phase_seed(spec, phase, "audit"),
                    f"architecture-{phase}.{arm}.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in next(iter(effects.values()))
            },
        }
    analysis = {
        "format": f"{AUDIT_FORMAT}-analysis",
        "phase": phase,
        "summaries": summaries,
        "selection_data_are_not_used_as_ph_evidence": True,
    }
    analysis["analysis_digest"] = canonical_digest(analysis)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {
        "format": f"{AUDIT_FORMAT}-manifest",
        "protocol_digest": digest,
        "population_count": len(completed),
        "elapsed_seconds": time.monotonic() - started,
        "runtime": runtime_manifest(),
    })
    write_checksums(destination); verify_architecture_audit(destination); return destination


def verify_architecture_audit(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory); registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = ArchitectureSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{AUDIT_FORMAT}-registration":
        raise ValueError("architecture audit registration format mismatch")
    if manifest.get("format") != f"{AUDIT_FORMAT}-manifest":
        raise ValueError("architecture audit manifest format mismatch")
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed architecture evolution changed after audit")
    payload = {key: registration[key] for key in ("spec", "kernel", "evolution_checksum", "phase", "selected_arms")}
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("architecture audit protocol mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    files = sorted((directory / "populations").glob("*.json")); expected = task_count * len(registration["selected_arms"])
    values = [read_json(path) for path in files]
    for value in values:
        expected_digest = canonical_digest(
            {"selected": value["selected"], "cells": value["cells"]}
        )
        if (
            value.get("protocol_digest") != registration["protocol_digest"]
            or value.get("result_digest") != expected_digest
            or value.get("phase") != registration["phase"]
            or value.get("arm") not in registration["selected_arms"]
            or len(value.get("cells", ()))
            != len(spec.audit_persistence) * len(spec.audit_cue_fractions)
        ):
            raise ValueError("architecture audit population digest mismatch")
        deserialize_genome(value["selected"])
    analysis = read_json(directory / "analysis.json")
    analysis_payload = dict(analysis)
    analysis_digest = analysis_payload.pop("analysis_digest", None)
    if analysis_digest != canonical_digest(analysis_payload):
        raise ValueError("architecture audit analysis digest mismatch")
    if (
        len(files) != expected
        or manifest["population_count"] != expected
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or set(analysis["summaries"]) != set(registration["selected_arms"])
    ):
        raise ValueError("architecture audit is incomplete")
    return {"verified": True, "phase": registration["phase"], "populations": len(files), "checksums": len(checksums)}


def pedigree_modes(arm: str) -> tuple[str, ...]:
    architecture = arm_settings(arm)["architecture"]
    if architecture == "repair":
        return ("natural", "repair_off")
    if architecture == "median3":
        return ("natural", "mean_decoder", "concerted")
    return ("natural",)


def _mode_start(root: Genome, arm: str, mode: str) -> tuple[Genome, str, str]:
    if mode == "mean_decoder":
        if root[0].architecture != "median3":
            raise ValueError("mean decoder intervention requires median3")
        return (ArchitectureInterpreter(root[0].copies, "mean3"), root[1]), "mh_mean3_ordinary", "natural"
    return root, arm, mode


def _pedigree_child(
    current: Genome,
    mutation_arm: str,
    mechanism: str,
    seed: str,
    task_index: int,
    root_index: int,
    lineage_index: int,
    distance: int,
    spec: ArchitectureSpec,
) -> Genome:
    """Use paired interpreter and carrier shocks across arms and mechanisms."""

    child = mutate_genome(
        current,
        current,
        mutation_arm,
        rng_for(
            seed,
            "architecture-pedigree-interpreter-mutation",
            task_index,
            root_index,
            lineage_index,
            distance,
        ),
        spec,
        mechanism=mechanism,
    )
    carrier = mutate_carrier(
        current[1],
        current[1],
        "independent",
        rng_for(
            seed,
            "architecture-pedigree-carrier-mutation",
            task_index,
            root_index,
            lineage_index,
            distance,
        ),
    )
    return child[0], carrier


def _population_pedigree(args: tuple[Any, ...]) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, digest, phase = args
    population = read_json(Path(population_text)); spec = ArchitectureSpec.from_dict(spec_value); kernel = CooptionSpec.from_dict(kernel_value)
    arm, task_index = population["arm"], int(population["population_index"])
    final_path = Path(output_text) / f"{arm}.task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("architecture pedigree shard registration differs")
    ranked = sorted(population["final_population"], key=lambda value: (-float(value["selection_score"]["fitness"]), value["genotype_id"]))[: spec.pedigree_roots_per_task]
    rows, ancestry = [], []
    seed = _phase_seed(spec, phase, "pedigree")
    for root_index, value in enumerate(ranked):
        natural_root = deserialize_genome(value)
        root_record = {"root_index": root_index, "root": serialize_genome(natural_root), "modes": []}
        for mode in pedigree_modes(arm):
            root, mutation_arm, mechanism = _mode_start(natural_root, arm, mode)
            root_scope = f"architecture-{phase}-pedigree.task-{task_index:03d}.root-{root_index:02d}"
            root_information = pedigree_information(root, population["task"], kernel, spec, root_scope + ".distance-00", phase)
            mode_record = {"mode": mode, "root": serialize_genome(root), "root_information": root_information, "chains": []}
            for lineage_index in range(spec.pedigree_lineages_per_root):
                current, immediate, chain = root, root_information, []
                for distance in range(1, 5):
                    child = _pedigree_child(
                        current,
                        mutation_arm,
                        mechanism,
                        seed,
                        task_index,
                        root_index,
                        lineage_index,
                        distance,
                        spec,
                    )
                    information = pedigree_information(
                        child,
                        population["task"],
                        kernel,
                        spec,
                        root_scope + f".lineage-{lineage_index:02d}.distance-{distance:02d}",
                        phase,
                    )
                    chain.append({
                        "distance": distance,
                        "genotype": serialize_genome(child),
                        "mutation_delta": mutation_delta(current, child),
                        "information": information,
                    })
                    rows.append({
                        "phase": phase,
                        "arm": arm,
                        "mode": mode,
                        "task_index": task_index,
                        "root_index": root_index,
                        "lineage_index": lineage_index,
                        "distance": distance,
                        "root_information": root_information,
                        "immediate_parent_information": immediate,
                        "descendant_information": information,
                        "eligible_positive_root": root_information > 0.0,
                        "retained": root_information > 0.0 and information >= spec.retention_fraction * root_information,
                        "collapsed": root_information > 0.0 and information <= 0.0,
                    })
                    current, immediate = child, information
                mode_record["chains"].append({"lineage_index": lineage_index, "chain": chain})
            root_record["modes"].append(mode_record)
        ancestry.append(root_record)
    result = {
        "format": PEDIGREE_FORMAT,
        "protocol_digest": digest,
        "phase": phase,
        "population_id": population["population_id"],
        "arm": arm,
        "task_index": task_index,
        "task": population["task"],
        "rows": rows,
        "row_count": len(rows),
        "complete_ancestry": ancestry,
        "ordinary_mutation_assay_regardless_of_training_challenge": True,
        "mutation_and_assay_stream_coordinates_are_replayable": True,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result); return result


def _task_centered_slope(rows: list[dict[str, Any]], task_count: int) -> float | None:
    xs, ys = [], []
    for task in range(task_count):
        selected = [row for row in rows if row["task_index"] == task]
        x = np.asarray([row["immediate_parent_information"] for row in selected]); y = np.asarray([row["descendant_information"] for row in selected])
        if len(x):
            xs.extend((x - x.mean()).tolist()); ys.extend((y - y.mean()).tolist())
    x, y = np.asarray(xs), np.asarray(ys); denominator = float(np.sum(x * x))
    return float(np.sum(x * y) / denominator) if denominator > 0.0 else None


def _analyze_pedigrees(results: list[dict[str, Any]], spec: ArchitectureSpec, phase: str, arms: tuple[str, ...]) -> dict[str, Any]:
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = _phase_seed(spec, phase, "pedigree"); summaries = {}
    for arm in arms:
        mode_summaries = {}
        for mode in pedigree_modes(arm):
            rows = [row for value in results if value["arm"] == arm for row in value["rows"] if row["mode"] == mode]
            distances = {}
            for distance in spec.pedigree_depths:
                selected = [row for row in rows if row["distance"] == distance]
                retention, collapse, information = {}, {}, {}
                for task in range(task_count):
                    task_rows = [row for row in selected if row["task_index"] == task]
                    eligible = [row for row in task_rows if row["eligible_positive_root"]]
                    retention[str(task)] = float(np.mean([row["retained"] for row in eligible])) if eligible else 0.0
                    collapse[str(task)] = float(np.mean([row["collapsed"] for row in eligible])) if eligible else 1.0
                    information[str(task)] = float(np.mean([row["descendant_information"] for row in task_rows])) if task_rows else 0.0
                distances[str(distance)] = {
                    "task_retention": retention,
                    "task_collapse_probability": collapse,
                    "task_information": information,
                    "retention_interval": _interval(retention.values(), seed, f"architecture-{phase}.{arm}.{mode}.d{distance}.retention", spec.bootstrap_repetitions, spec.interval_level),
                    "collapse_interval": _interval(collapse.values(), seed, f"architecture-{phase}.{arm}.{mode}.d{distance}.collapse", spec.bootstrap_repetitions, spec.interval_level),
                    "information_interval": _interval(information.values(), seed, f"architecture-{phase}.{arm}.{mode}.d{distance}.information", spec.bootstrap_repetitions, spec.interval_level),
                }
            mode_summaries[mode] = {
                "rows": len(rows),
                "distances": distances,
                "task_centered_immediate_parent_offspring_slope": _task_centered_slope(rows, task_count),
            }
        summaries[arm] = {"modes": mode_summaries}
    result = {
        "format": f"{PEDIGREE_FORMAT}-analysis",
        "phase": phase,
        "arms": summaries,
        "retention_definition": "descendant information >= 0.70 times positive root information",
        "inferential_unit": "paired founder task",
    }
    result["analysis_digest"] = canonical_digest(result); return result


def run_architecture_pedigree(
    spec: ArchitectureSpec,
    evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_architecture_evolution(evolution)
    evolution_registration = read_json(evolution / "registration.json")
    phase, arms = evolution_registration["phase"], tuple(evolution_registration["selected_arms"])
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_architecture_pedigree(destination); return destination
    kernel = spec.kernel(confirmation=phase == "confirmation")
    payload = {
        "spec": spec.to_dict(), "kernel": kernel.to_dict(),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "phase": phase, "selected_arms": list(arms),
    }
    digest = canonical_digest(payload)
    registration = {
        "format": f"{PEDIGREE_FORMAT}-registration", "protocol_digest": digest,
        **payload, "evolution": str(evolution),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing architecture pedigree registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    shards = destination / "populations"; shards.mkdir(exist_ok=True)
    files = sorted(path for path in (evolution / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json"))
    work = [(str(path), spec.to_dict(), kernel.to_dict(), str(shards), digest, phase) for path in files]
    started = time.monotonic()

    def update(index: int, _: dict[str, Any]) -> None:
        _atomic_json(destination / "progress.json", {"completed_populations": index, "total_populations": len(work), "elapsed_seconds": time.monotonic() - started})
        if progress:
            progress(f"interpreter-architecture {phase} pedigree {index}/{len(work)} populations")

    completed = _parallel(work, _population_pedigree, workers, update)
    analysis = _analyze_pedigrees(completed, spec, phase, arms)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {
        "format": f"{PEDIGREE_FORMAT}-manifest",
        "protocol_digest": digest,
        "populations": len(completed),
        "rows": sum(value["row_count"] for value in completed),
        "elapsed_seconds": time.monotonic() - started,
        "runtime": runtime_manifest(),
    })
    write_checksums(destination); verify_architecture_pedigree(destination); return destination


def verify_architecture_pedigree(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory); registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = ArchitectureSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{PEDIGREE_FORMAT}-registration":
        raise ValueError("architecture pedigree registration format mismatch")
    if manifest.get("format") != f"{PEDIGREE_FORMAT}-manifest":
        raise ValueError("architecture pedigree manifest format mismatch")
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed architecture evolution changed after pedigree")
    payload = {key: registration[key] for key in ("spec", "kernel", "evolution_checksum", "phase", "selected_arms")}
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("architecture pedigree protocol mismatch")
    task_count = spec.confirmation_task_count if registration["phase"] == "confirmation" else spec.task_count
    files = sorted((directory / "populations").glob("*.json")); expected_populations = task_count * len(registration["selected_arms"])
    expected_rows = sum(
        task_count * spec.pedigree_roots_per_task * spec.pedigree_lineages_per_root * 4 * len(pedigree_modes(arm))
        for arm in registration["selected_arms"]
    )
    values = [read_json(path) for path in files]
    rows = sum(value["row_count"] for value in values)
    for value in values:
        payload = dict(value)
        archived = payload.pop("result_digest", None)
        if (
            value.get("protocol_digest") != registration["protocol_digest"]
            or archived != canonical_digest(payload)
            or value.get("phase") != registration["phase"]
            or value.get("arm") not in registration["selected_arms"]
        ):
            raise ValueError("architecture pedigree population digest mismatch")
    analysis = read_json(directory / "analysis.json")
    analysis_payload = dict(analysis)
    analysis_digest = analysis_payload.pop("analysis_digest", None)
    if analysis_digest != canonical_digest(analysis_payload):
        raise ValueError("architecture pedigree analysis digest mismatch")
    if (
        len(files) != expected_populations
        or rows != expected_rows
        or manifest["populations"] != expected_populations
        or manifest["rows"] != expected_rows
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or set(analysis["arms"]) != set(registration["selected_arms"])
    ):
        raise ValueError("architecture pedigree is incomplete")
    return {"verified": True, "phase": registration["phase"], "populations": len(files), "rows": rows, "checksums": len(checksums)}


def replay_architecture_pedigree(
    directory: Path,
    population_id: str,
    root_index: int,
    lineage_index: int,
    distance: int,
    mode: str = "natural",
) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = ArchitectureSpec.from_dict(registration["spec"]); phase = registration["phase"]
    arm, task_text = population_id.split(".population-"); task = int(task_text)
    shard = read_json(directory / "populations" / f"{arm}.task-{task:03d}.json")
    root_record = shard["complete_ancestry"][root_index]
    mode_record = next(value for value in root_record["modes"] if value["mode"] == mode)
    current = deserialize_genome(mode_record["root"])
    _, mutation_arm, mechanism = _mode_start(current if mode != "mean_decoder" else deserialize_genome(root_record["root"]), arm, mode)
    seed = _phase_seed(spec, phase, "pedigree"); matches = True
    for step in range(1, distance + 1):
        current = _pedigree_child(
            current,
            mutation_arm,
            mechanism,
            seed,
            task,
            root_index,
            lineage_index,
            step,
            spec,
        )
        archived = mode_record["chains"][lineage_index]["chain"][step - 1]["genotype"]
        matches &= canonical_digest(serialize_genome(current)) == canonical_digest(archived)
    return {"population_id": population_id, "mode": mode, "distance": distance, "matches": bool(matches)}
