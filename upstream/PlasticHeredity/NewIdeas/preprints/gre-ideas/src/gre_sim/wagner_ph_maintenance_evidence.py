"""Held-out causal audits and mutation pedigrees for Adaptive Maintenance v1."""

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
from .wagner_ph_cooption_evolution import mutate_carrier
from .wagner_ph_cooption_experiment import history_information, simulate_ecology_condition
from .wagner_ph_maintenance_config import MAINTENANCE_FORMAT, MaintenanceSpec, arm_settings
from .wagner_ph_maintenance_evolution import verify_maintenance_evolution
from .wagner_ph_maintenance_genome import (
    Genome,
    MaintenanceInterpreter,
    deserialize_genome,
    effective_genotype,
    mutate_genome,
    mutation_delta,
    serialize_genome,
)


AUDIT_FORMAT = f"{MAINTENANCE_FORMAT}-audit"
PEDIGREE_FORMAT = f"{MAINTENANCE_FORMAT}-pedigree"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _phase_seed(spec: MaintenanceSpec, phase: str, domain: str) -> str:
    if phase == "development":
        return spec.audit_seed if domain == "audit" else spec.pedigree_seed
    return canonical_digest((spec.confirmation_seed, domain))


def _parallel(
    work: list[tuple[Any, ...]],
    function: Callable[[tuple[Any, ...]], dict[str, Any]],
    workers: int,
    update: Callable[[int, dict[str, Any]], None],
) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(function, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(function, item) for item in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, value in enumerate(iterator, 1):
            completed.append(value)
            update(index, value)
    finally:
        if executor is not None:
            executor.shutdown()
    return completed


def pedigree_information(
    genome: Genome,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: MaintenanceSpec,
    scope: str,
    phase: str,
) -> float:
    rulebook, carrier = effective_genotype(genome)
    conditions = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            carrier,
            kernel,
            intervention,
            0.9,
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
        conditions["natural"]["checkpoints"][generation]["correct_rate"]
        - conditions["independent_history"]["checkpoints"][generation]["correct_rate"]
    )


def _audit_population(args: tuple[Any, ...]) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, digest, phase = args
    population = read_json(Path(population_text))
    spec = MaintenanceSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    output = Path(output_text) / Path(population_text).name
    if output.is_file():
        prior = read_json(output)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("maintenance audit shard registration differs")
    genome = deserialize_genome(population["selected"])
    rulebook, carrier = effective_genotype(genome)
    task_index = int(population["population_index"])
    scope = f"adaptive-maintenance-{phase}-audit.task-{task_index:03d}"
    cells = []
    for persistence in spec.audit_persistence:
        for cue_fraction in spec.cue_fractions:
            conditions = {
                intervention: simulate_ecology_condition(
                    rulebook,
                    population["task"],
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
            cells.append(
                {
                    "cell_id": f"rho{persistence:.2f}.cue{cue_fraction:.2f}",
                    "persistence": persistence,
                    "cue_fraction": cue_fraction,
                    "conditions": conditions,
                    "history_information": history_information(
                        conditions["natural"]["final_carriers"]
                    ),
                }
            )
    result = {
        "format": AUDIT_FORMAT,
        "protocol_digest": digest,
        "phase": phase,
        "population_id": population["population_id"],
        "population_index": task_index,
        "arm": population["arm"],
        "arm_settings": population["arm_settings"],
        "task": population["task"],
        "selected": population["selected"],
        "selected_effective_genotype": population["selected_effective_genotype"],
        "selected_training_score": population["selected_training_score"],
        "selected_selection_score": population["selected_selection_score"],
        "audit_streams_are_held_out_from_selection": True,
        "cells": cells,
    }
    result["result_digest"] = canonical_digest(
        {"selected": result["selected"], "cells": cells}
    )
    _atomic_json(output, result)
    return result


def run_maintenance_audit(
    spec: MaintenanceSpec,
    evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_maintenance_evolution(evolution)
    evolution_registration = read_json(evolution / "registration.json")
    phase = str(evolution_registration["phase"])
    arms = tuple(evolution_registration["selected_arms"])
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_maintenance_audit(destination)
        return destination
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
        "format": f"{AUDIT_FORMAT}-registration",
        "protocol_digest": digest,
        **payload,
        "evolution": str(evolution.resolve()),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing maintenance audit registration differs")
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
        (str(path), spec.to_dict(), kernel.to_dict(), str(shards), digest, phase)
        for path in files
    ]
    started = time.monotonic()

    def update(index: int, _: dict[str, Any]) -> None:
        elapsed = time.monotonic() - started
        _atomic_json(
            destination / "progress.json",
            {
                "completed_populations": index,
                "total_populations": len(work),
                "elapsed_seconds": elapsed,
                "eta_seconds": (len(work) - index) * elapsed / max(index, 1),
            },
        )
        if progress:
            progress(f"adaptive-maintenance {phase} audit {index}/{len(work)} populations")

    completed = _parallel(work, _audit_population, workers, update)
    summaries: dict[str, Any] = {}
    for arm in arms:
        selected = [value for value in completed if value["arm"] == arm]
        effects = {
            str(value["population_index"]): population_effects(value, kernel)
            for value in selected
        }
        summaries[arm] = {
            "populations": len(selected),
            "task_effects": effects,
            "intervals": {
                field: _interval(
                    (row[field] for row in effects.values()),
                    _phase_seed(spec, phase, "audit"),
                    f"maintenance-{phase}.{arm}.{field}",
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
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{AUDIT_FORMAT}-manifest",
            "protocol_digest": digest,
            "population_count": len(completed),
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_maintenance_audit(destination)
    return destination


def verify_maintenance_audit(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = MaintenanceSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{AUDIT_FORMAT}-registration":
        raise ValueError("maintenance audit registration format mismatch")
    if manifest.get("format") != f"{AUDIT_FORMAT}-manifest":
        raise ValueError("maintenance audit manifest format mismatch")
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed maintenance evolution changed after audit")
    payload = {
        key: registration[key]
        for key in ("spec", "kernel", "evolution_checksum", "phase", "selected_arms")
    }
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("maintenance audit protocol mismatch")
    task_count = (
        spec.confirmation_task_count
        if registration["phase"] == "confirmation"
        else spec.task_count
    )
    files = sorted((directory / "populations").glob("*.json"))
    expected = task_count * len(registration["selected_arms"])
    for path in files:
        value = read_json(path)
        expected_digest = canonical_digest(
            {"selected": value["selected"], "cells": value["cells"]}
        )
        if (
            value.get("protocol_digest") != registration["protocol_digest"]
            or value.get("result_digest") != expected_digest
            or value.get("arm") not in registration["selected_arms"]
            or len(value.get("cells", ()))
            != len(spec.audit_persistence) * len(spec.cue_fractions)
        ):
            raise ValueError("maintenance audit population digest mismatch")
        deserialize_genome(value["selected"])
    analysis = read_json(directory / "analysis.json")
    analysis_payload = dict(analysis)
    archived = analysis_payload.pop("analysis_digest", None)
    if archived != canonical_digest(analysis_payload):
        raise ValueError("maintenance audit analysis digest mismatch")
    if (
        len(files) != expected
        or manifest["population_count"] != expected
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or set(analysis["summaries"]) != set(registration["selected_arms"])
    ):
        raise ValueError("maintenance audit is incomplete")
    return {
        "verified": True,
        "phase": registration["phase"],
        "populations": len(files),
        "checksums": len(checksums),
    }


def pedigree_modes(arm: str) -> tuple[str, ...]:
    architecture = arm_settings(arm)["architecture"]
    return {
        "single": ("natural",),
        "global_repair": ("natural", "repair_off"),
        "node_repair": ("natural", "repair_off", "uniform_repair", "shuffled_repair"),
        "duplication": ("natural", "concerted", "mean_decoder", "single_copy"),
        "median3": ("natural", "concerted", "mean_decoder"),
    }[str(architecture)]


def _mode_start(root: Genome, mode: str) -> Genome:
    interpreter, carrier = root
    if mode == "mean_decoder":
        return (
            MaintenanceInterpreter(
                interpreter.copies,
                interpreter.architecture,
                interpreter.global_repair,
                interpreter.node_repair,
                "mean",
            ),
            carrier,
        )
    if mode == "single_copy":
        return (
            MaintenanceInterpreter(
                (interpreter.effective_rulebook(),), "duplication", decoder="mean"
            ),
            carrier,
        )
    return root


def _pedigree_child(
    current: Genome,
    arm: str,
    mechanism: str,
    seed: str,
    task_index: int,
    root_index: int,
    lineage_index: int,
    distance: int,
    spec: MaintenanceSpec,
) -> Genome:
    child = mutate_genome(
        current,
        current,
        arm,
        rng_for(
            seed,
            "maintenance-pedigree-interpreter-mutation",
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
            "maintenance-pedigree-carrier-mutation",
            task_index,
            root_index,
            lineage_index,
            distance,
        ),
    )
    return child[0], carrier


def _population_pedigree(args: tuple[Any, ...]) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, digest, phase = args
    population = read_json(Path(population_text))
    spec = MaintenanceSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    arm = str(population["arm"])
    task_index = int(population["population_index"])
    output = Path(output_text) / f"{arm}.task-{task_index:03d}.json"
    if output.is_file():
        prior = read_json(output)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("maintenance pedigree shard registration differs")
    ranked = sorted(
        population["final_population"],
        key=lambda value: (-float(value["selection_score"]["fitness"]), value["genotype_id"]),
    )[: spec.pedigree_roots_per_task]
    rows: list[dict[str, Any]] = []
    ancestry = []
    seed = _phase_seed(spec, phase, "pedigree")
    for root_index, value in enumerate(ranked):
        natural_root = deserialize_genome(value)
        root_record = {
            "root_index": root_index,
            "natural_root": serialize_genome(natural_root),
            "modes": [],
        }
        for mode in pedigree_modes(arm):
            root = _mode_start(natural_root, mode)
            # Keep assay futures identical across mechanism counterfactuals.  The
            # genotype and mutation law change; the sampled ecological futures do not.
            root_scope = (
                f"maintenance-{phase}-pedigree.task-{task_index:03d}"
                f".root-{root_index:02d}"
            )
            root_information = pedigree_information(
                root, population["task"], kernel, spec, root_scope + ".distance-00", phase
            )
            mode_record = {
                "mode": mode,
                "root": serialize_genome(root),
                "root_information": root_information,
                "chains": [],
            }
            for lineage_index in range(spec.pedigree_lineages_per_root):
                current = root
                immediate = root_information
                chain = []
                for distance in range(1, spec.lineage_depth + 1):
                    child = _pedigree_child(
                        current,
                        arm,
                        mode,
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
                        root_scope
                        + f".lineage-{lineage_index:02d}.distance-{distance:02d}",
                        phase,
                    )
                    ratio = (
                        information / root_information if root_information > 0.0 else None
                    )
                    chain.append(
                        {
                            "distance": distance,
                            "genotype": serialize_genome(child),
                            "mutation_delta": mutation_delta(current, child),
                            "information": information,
                        }
                    )
                    rows.append(
                        {
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
                            "information_change_from_root": information - root_information,
                            "retention_ratio": ratio,
                            "eligible_positive_root": root_information > 0.0,
                            "retained": root_information > 0.0
                            and information >= spec.retention_fraction * root_information,
                            "collapsed": root_information > 0.0 and information <= 0.0,
                            "rescued": root_information <= 0.0 and information > 0.0,
                        }
                    )
                    current, immediate = child, information
                mode_record["chains"].append(
                    {"lineage_index": lineage_index, "chain": chain}
                )
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
        "carrier_mutation_stream_is_paired_across_mechanism_modes": True,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(output, result)
    return result


def _task_centered_slope(rows: list[dict[str, Any]], task_count: int) -> float | None:
    xs: list[float] = []
    ys: list[float] = []
    for task_index in range(task_count):
        selected = [row for row in rows if row["task_index"] == task_index]
        x = np.asarray([row["immediate_parent_information"] for row in selected])
        y = np.asarray([row["descendant_information"] for row in selected])
        if len(x):
            xs.extend((x - x.mean()).tolist())
            ys.extend((y - y.mean()).tolist())
    x = np.asarray(xs)
    y = np.asarray(ys)
    denominator = float(np.sum(x * x))
    return float(np.sum(x * y) / denominator) if denominator > 0.0 else None


def _analyze_pedigrees(
    results: list[dict[str, Any]],
    spec: MaintenanceSpec,
    phase: str,
    arms: tuple[str, ...],
) -> dict[str, Any]:
    task_count = spec.confirmation_task_count if phase == "confirmation" else spec.task_count
    seed = _phase_seed(spec, phase, "pedigree")
    summaries: dict[str, Any] = {}
    for arm in arms:
        modes: dict[str, Any] = {}
        for mode in pedigree_modes(arm):
            rows = [
                row
                for result in results
                if result["arm"] == arm
                for row in result["rows"]
                if row["mode"] == mode
            ]
            distances: dict[str, Any] = {}
            for distance in spec.pedigree_depths:
                selected = [row for row in rows if row["distance"] == distance]
                retention: dict[str, float] = {}
                collapse: dict[str, float] = {}
                rescue: dict[str, float] = {}
                information: dict[str, float] = {}
                change: dict[str, float] = {}
                for task_index in range(task_count):
                    task_rows = [row for row in selected if row["task_index"] == task_index]
                    eligible = [row for row in task_rows if row["eligible_positive_root"]]
                    rescue_eligible = [row for row in task_rows if not row["eligible_positive_root"]]
                    key = str(task_index)
                    retention[key] = float(np.mean([row["retained"] for row in eligible])) if eligible else 0.0
                    collapse[key] = float(np.mean([row["collapsed"] for row in eligible])) if eligible else 1.0
                    rescue[key] = float(np.mean([row["rescued"] for row in rescue_eligible])) if rescue_eligible else 0.0
                    information[key] = float(np.mean([row["descendant_information"] for row in task_rows])) if task_rows else 0.0
                    change[key] = float(np.mean([row["information_change_from_root"] for row in task_rows])) if task_rows else 0.0
                def interval(values: dict[str, float], label: str) -> dict[str, Any]:
                    return _interval(
                        values.values(),
                        seed,
                        f"maintenance-{phase}.{arm}.{mode}.d{distance}.{label}",
                        spec.bootstrap_repetitions,
                        spec.interval_level,
                    )
                distances[str(distance)] = {
                    "task_retention": retention,
                    "task_collapse_probability": collapse,
                    "task_rescue_probability": rescue,
                    "task_information": information,
                    "task_information_change": change,
                    "retention_interval": interval(retention, "retention"),
                    "collapse_interval": interval(collapse, "collapse"),
                    "rescue_interval": interval(rescue, "rescue"),
                    "information_interval": interval(information, "information"),
                    "information_change_interval": interval(change, "information-change"),
                }
            modes[mode] = {
                "rows": len(rows),
                "distances": distances,
                "task_centered_immediate_parent_offspring_slope": _task_centered_slope(
                    rows, task_count
                ),
            }
        summaries[arm] = {"modes": modes}
    result = {
        "format": f"{PEDIGREE_FORMAT}-analysis",
        "phase": phase,
        "arms": summaries,
        "retention_definition": "descendant information >= 0.70 times positive root information",
        "continuous_information_change_and_rescue_are_reported": True,
        "inferential_unit": "paired founder task",
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def run_maintenance_pedigree(
    spec: MaintenanceSpec,
    evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_maintenance_evolution(evolution)
    evolution_registration = read_json(evolution / "registration.json")
    phase = str(evolution_registration["phase"])
    arms = tuple(evolution_registration["selected_arms"])
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_maintenance_pedigree(destination)
        return destination
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
        "format": f"{PEDIGREE_FORMAT}-registration",
        "protocol_digest": digest,
        **payload,
        "evolution": str(evolution.resolve()),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing maintenance pedigree registration differs")
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
        (str(path), spec.to_dict(), kernel.to_dict(), str(shards), digest, phase)
        for path in files
    ]
    started = time.monotonic()

    def update(index: int, _: dict[str, Any]) -> None:
        elapsed = time.monotonic() - started
        _atomic_json(
            destination / "progress.json",
            {
                "completed_populations": index,
                "total_populations": len(work),
                "elapsed_seconds": elapsed,
                "eta_seconds": (len(work) - index) * elapsed / max(index, 1),
            },
        )
        if progress:
            progress(f"adaptive-maintenance {phase} pedigree {index}/{len(work)} populations")

    completed = _parallel(work, _population_pedigree, workers, update)
    _atomic_json(destination / "analysis.json", _analyze_pedigrees(completed, spec, phase, arms))
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{PEDIGREE_FORMAT}-manifest",
            "protocol_digest": digest,
            "populations": len(completed),
            "rows": sum(value["row_count"] for value in completed),
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_maintenance_pedigree(destination)
    return destination


def verify_maintenance_pedigree(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = MaintenanceSpec.from_dict(registration["spec"])
    if registration.get("format") != f"{PEDIGREE_FORMAT}-registration":
        raise ValueError("maintenance pedigree registration format mismatch")
    if manifest.get("format") != f"{PEDIGREE_FORMAT}-manifest":
        raise ValueError("maintenance pedigree manifest format mismatch")
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed maintenance evolution changed after pedigree")
    payload = {
        key: registration[key]
        for key in ("spec", "kernel", "evolution_checksum", "phase", "selected_arms")
    }
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("maintenance pedigree protocol mismatch")
    task_count = (
        spec.confirmation_task_count
        if registration["phase"] == "confirmation"
        else spec.task_count
    )
    expected_populations = task_count * len(registration["selected_arms"])
    expected_rows = sum(
        task_count
        * spec.pedigree_roots_per_task
        * spec.pedigree_lineages_per_root
        * spec.lineage_depth
        * len(pedigree_modes(arm))
        for arm in registration["selected_arms"]
    )
    files = sorted((directory / "populations").glob("*.json"))
    rows = 0
    for path in files:
        value = read_json(path)
        archived = value.get("result_digest")
        payload_value = dict(value)
        payload_value.pop("result_digest", None)
        if (
            value.get("protocol_digest") != registration["protocol_digest"]
            or archived != canonical_digest(payload_value)
            or value.get("arm") not in registration["selected_arms"]
        ):
            raise ValueError("maintenance pedigree population digest mismatch")
        rows += int(value["row_count"])
    analysis = read_json(directory / "analysis.json")
    analysis_payload = dict(analysis)
    archived_analysis = analysis_payload.pop("analysis_digest", None)
    if archived_analysis != canonical_digest(analysis_payload):
        raise ValueError("maintenance pedigree analysis digest mismatch")
    if (
        len(files) != expected_populations
        or rows != expected_rows
        or manifest["populations"] != expected_populations
        or manifest["rows"] != expected_rows
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or set(analysis["arms"]) != set(registration["selected_arms"])
    ):
        raise ValueError("maintenance pedigree is incomplete")
    return {
        "verified": True,
        "phase": registration["phase"],
        "populations": len(files),
        "rows": rows,
        "checksums": len(checksums),
    }


def replay_maintenance_pedigree(
    directory: Path,
    population_id: str,
    root_index: int,
    lineage_index: int,
    distance: int,
    mode: str = "natural",
) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = MaintenanceSpec.from_dict(registration["spec"])
    phase = str(registration["phase"])
    arm, task_text = population_id.split(".population-")
    task_index = int(task_text)
    shard = read_json(directory / "populations" / f"{arm}.task-{task_index:03d}.json")
    root_record = shard["complete_ancestry"][root_index]
    mode_record = next(value for value in root_record["modes"] if value["mode"] == mode)
    current = deserialize_genome(mode_record["root"])
    seed = _phase_seed(spec, phase, "pedigree")
    matches = True
    for step in range(1, distance + 1):
        current = _pedigree_child(
            current,
            arm,
            mode,
            seed,
            task_index,
            root_index,
            lineage_index,
            step,
            spec,
        )
        archived = mode_record["chains"][lineage_index]["chain"][step - 1]["genotype"]
        matches &= canonical_digest(serialize_genome(current)) == canonical_digest(archived)
    return {
        "population_id": population_id,
        "mode": mode,
        "distance": distance,
        "matches": bool(matches),
    }


__all__ = (
    "pedigree_information",
    "pedigree_modes",
    "replay_maintenance_pedigree",
    "run_maintenance_audit",
    "run_maintenance_pedigree",
    "verify_maintenance_audit",
    "verify_maintenance_pedigree",
)
