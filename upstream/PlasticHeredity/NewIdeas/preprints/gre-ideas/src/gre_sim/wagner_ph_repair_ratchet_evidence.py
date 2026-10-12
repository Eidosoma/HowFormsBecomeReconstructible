"""Held-out causal evidence for Global Repair Ratchet v1."""

from __future__ import annotations

import concurrent.futures
import json
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
from .wagner import recombine_wagner
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import mutate_carrier
from .wagner_ph_maintenance_config import MaintenanceSpec
from .wagner_ph_maintenance_evidence import _audit_population, pedigree_information
from .wagner_ph_maintenance_genome import (
    Genome,
    MaintenanceInterpreter,
    _apply_mutation,
    _mutation_draws,
    deserialize_genome,
    mutation_delta,
    mutate_genome,
    serialize_genome,
)
from .wagner_ph_repair_ratchet_config import (
    RATCHET_FORMAT,
    RepairRatchetSpec,
    RepairRoute,
)
from .wagner_ph_repair_ratchet_evolution import verify_repair_ratchet_evolution


AUDIT_FORMAT = f"{RATCHET_FORMAT}-audit"
PEDIGREE_FORMAT = f"{RATCHET_FORMAT}-pedigree"
GLOBAL_DOSE_MODES = (
    "natural",
    "repair_075",
    "repair_050",
    "repair_025",
    "repair_off",
)
DOSE_SCALE = {
    "natural": 1.0,
    "repair_075": 0.75,
    "repair_050": 0.50,
    "repair_025": 0.25,
    "repair_off": 0.0,
}


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


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
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
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


def _route_registration(
    format_name: str,
    spec: RepairRatchetSpec,
    base: MaintenanceSpec,
    kernel: CooptionSpec,
    evolution: Path,
    route: RepairRoute,
) -> dict[str, Any]:
    payload = {
        "ratchet_spec": spec.to_dict(),
        "maintenance_spec": _json_value(base.to_dict()),
        "kernel": _json_value(kernel.to_dict()),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "route": route.to_dict(),
    }
    return {
        "format": f"{format_name}-registration",
        "protocol_digest": canonical_digest(payload),
        **payload,
        "evolution": str(evolution.resolve()),
    }


def run_repair_ratchet_audit(
    spec: RepairRatchetSpec,
    evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_repair_ratchet_evolution(evolution)
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("repair-ratchet audit permits one to four CPU workers")
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_repair_ratchet_audit(destination)
        return destination
    base = spec.maintenance()
    kernel = base.kernel()
    evolution_checksum = sha256_file(evolution / "SHA256SUMS")
    top_payload = {
        "spec": spec.to_dict(),
        "maintenance_spec": _json_value(base.to_dict()),
        "kernel": _json_value(kernel.to_dict()),
        "evolution_checksum": evolution_checksum,
    }
    top_registration = {
        "format": f"{AUDIT_FORMAT}-registration",
        "protocol_digest": canonical_digest(top_payload),
        **top_payload,
        "evolution": str(evolution.resolve()),
    }
    top_path = destination / "registration.json"
    if top_path.is_file() and canonical_digest(read_json(top_path)) != canonical_digest(top_registration):
        raise ValueError("existing repair-ratchet audit registration differs")
    if not top_path.is_file():
        _atomic_json(top_path, top_registration)

    work: list[tuple[Any, ...]] = []
    route_registrations: dict[str, dict[str, Any]] = {}
    for route in spec.routes:
        route_dir = destination / route.name
        shards = route_dir / "populations"
        shards.mkdir(parents=True, exist_ok=True)
        registration = _route_registration(AUDIT_FORMAT, spec, base, kernel, evolution, route)
        route_registrations[route.name] = registration
        route_path = route_dir / "registration.json"
        if route_path.is_file() and canonical_digest(read_json(route_path)) != canonical_digest(registration):
            raise ValueError(f"existing audit registration differs for {route.name}")
        if not route_path.is_file():
            _atomic_json(route_path, registration)
        population_files = sorted(
            (evolution / "populations").glob(f"{route.name}.population-*.json")
        )
        if len(population_files) != spec.task_count:
            raise ValueError(f"evolution population count differs for {route.name}")
        work.extend(
            (
                str(path),
                _json_value(base.to_dict()),
                _json_value(kernel.to_dict()),
                str(shards),
                registration["protocol_digest"],
                "development",
            )
            for path in population_files
        )
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
            progress(f"repair-ratchet audit {index}/{len(work)} populations")

    completed = _parallel(work, _audit_population, workers, update)
    for route in spec.routes:
        route_dir = destination / route.name
        selected = [
            value
            for value in completed
            if value["population_id"].startswith(route.name + ".")
        ]
        _atomic_json(
            route_dir / "manifest.json",
            {
                "format": f"{AUDIT_FORMAT}-route-manifest",
                "route": route.name,
                "protocol_digest": route_registrations[route.name]["protocol_digest"],
                "populations": len(selected),
            },
        )
        write_checksums(route_dir)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{AUDIT_FORMAT}-manifest",
            "protocol_digest": top_registration["protocol_digest"],
            "populations": len(completed),
            "elapsed_seconds": time.monotonic() - started,
            "workers_used": workers,
            "cpu_only": True,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_repair_ratchet_audit(destination)
    return destination


def verify_repair_ratchet_audit(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = RepairRatchetSpec.from_dict(registration["spec"])
    MaintenanceSpec.from_dict(registration["maintenance_spec"])
    CooptionSpec.from_dict(registration["kernel"])
    if registration.get("format") != f"{AUDIT_FORMAT}-registration":
        raise ValueError("repair-ratchet audit format mismatch")
    payload = {
        key: registration[key]
        for key in ("spec", "maintenance_spec", "kernel", "evolution_checksum")
    }
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("repair-ratchet audit protocol mismatch")
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed repair-ratchet evolution changed after audit")
    total = 0
    for route in spec.routes:
        route_dir = directory / route.name
        verify_checksums(route_dir)
        route_registration = read_json(route_dir / "registration.json")
        route_manifest = read_json(route_dir / "manifest.json")
        files = sorted((route_dir / "populations").glob("*.json"))
        for path in files:
            value = read_json(path)
            if (
                value.get("protocol_digest") != route_registration["protocol_digest"]
                or value.get("result_digest")
                != canonical_digest({"selected": value["selected"], "cells": value["cells"]})
                or not value.get("population_id", "").startswith(route.name + ".")
            ):
                raise ValueError(f"repair-ratchet audit shard differs: {path}")
            deserialize_genome(value["selected"])
        if len(files) != spec.task_count or route_manifest.get("populations") != spec.task_count:
            raise ValueError(f"repair-ratchet audit incomplete for {route.name}")
        total += len(files)
    expected = spec.task_count * len(spec.routes)
    if (
        total != expected
        or manifest.get("populations") != expected
        or manifest.get("workers_used", 5) > spec.maximum_workers
        or not manifest.get("cpu_only")
    ):
        raise ValueError("repair-ratchet audit is incomplete")
    return {"verified": True, "populations": total, "checksums": len(checksums)}


def _modes(route: RepairRoute) -> tuple[str, ...]:
    return GLOBAL_DOSE_MODES if route.has_repair else ("natural",)


def _paired_child(
    current: Genome,
    route: RepairRoute,
    mode: str,
    base: MaintenanceSpec,
    seed: str,
    task_index: int,
    root_index: int,
    lineage_index: int,
    distance: int,
) -> Genome:
    random = rng_for(
        seed,
        "repair-ratchet-pedigree-interpreter-mutation",
        task_index,
        root_index,
        lineage_index,
        distance,
    )
    if not route.has_repair:
        child = mutate_genome(current, current, route.legacy_arm, random, base)
        interpreter = child[0]
    else:
        inherited = current[0].global_repair
        recombined = recombine_wagner(current[0].copies[0], current[0].copies[0], random)
        indices, targets = _mutation_draws(recombined, random)
        used = inherited * DOSE_SCALE[mode]
        repaired = np.full(recombined.genes, used, dtype=float)
        copy = _apply_mutation(recombined, indices, targets, repaired)
        evolved = float(
            np.clip(
                inherited + random.normal(0.0, base.repair_mutation_sigma),
                0.0,
                base.repair_maximum,
            )
        )
        interpreter = MaintenanceInterpreter(
            (copy,), "global_repair", global_repair=evolved
        )
    carrier = mutate_carrier(
        current[1],
        current[1],
        "independent",
        rng_for(
            seed,
            "repair-ratchet-pedigree-carrier-mutation",
            task_index,
            root_index,
            lineage_index,
            distance,
        ),
    )
    return interpreter, carrier


def _pedigree_population(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        population_text,
        route_value,
        maintenance_value,
        kernel_value,
        output_text,
        digest,
    ) = args
    population = read_json(Path(population_text))
    route = RepairRoute.from_dict(route_value)
    base = MaintenanceSpec.from_dict(maintenance_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(population["population_index"])
    output = Path(output_text) / Path(population_text).name
    if output.is_file():
        prior = read_json(output)
        if prior.get("protocol_digest") == digest:
            return prior
        raise ValueError("repair-ratchet pedigree shard registration differs")
    ranked = sorted(
        population["final_population"],
        key=lambda value: (-float(value["selection_score"]["fitness"]), value["genotype_id"]),
    )[: base.pedigree_roots_per_task]
    rows: list[dict[str, Any]] = []
    ancestry: list[dict[str, Any]] = []
    seed = base.pedigree_seed
    for root_index, value in enumerate(ranked):
        root = deserialize_genome(value)
        root_scope = f"repair-ratchet-pedigree.task-{task_index:03d}.root-{root_index:02d}"
        root_information = pedigree_information(
            root,
            population["task"],
            kernel,
            base,
            root_scope + ".distance-00",
            "development",
        )
        root_record: dict[str, Any] = {
            "root_index": root_index,
            "root": serialize_genome(root),
            "root_information": root_information,
            "modes": [],
        }
        for mode in _modes(route):
            mode_record: dict[str, Any] = {
                "mode": mode,
                "dose_scale": DOSE_SCALE.get(mode),
                "chains": [],
            }
            for lineage_index in range(base.pedigree_lineages_per_root):
                current = root
                immediate = root_information
                chain = []
                for distance in range(1, base.lineage_depth + 1):
                    child = _paired_child(
                        current,
                        route,
                        mode,
                        base,
                        seed,
                        task_index,
                        root_index,
                        lineage_index,
                        distance,
                    )
                    information = pedigree_information(
                        child,
                        population["task"],
                        kernel,
                        base,
                        root_scope
                        + f".lineage-{lineage_index:02d}.distance-{distance:02d}",
                        "development",
                    )
                    ratio = information / root_information if root_information > 0.0 else None
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
                            "route": route.name,
                            "mode": mode,
                            "dose_scale": DOSE_SCALE.get(mode),
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
                            and information >= base.retention_fraction * root_information,
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
        "population_id": population["population_id"],
        "population_index": task_index,
        "route": route.name,
        "route_settings": route.to_dict(),
        "task": population["task"],
        "rows": rows,
        "row_count": len(rows),
        "complete_ancestry": ancestry,
        "standard_mutation_assay_regardless_of_training_route": True,
        "regulatory_repair_carrier_and_ecology_streams_are_paired_across_doses": True,
        "dose_changes_attenuation_not_inherited_repair_trajectory": True,
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


def _analyze_route_pedigree(
    results: list[dict[str, Any]],
    route: RepairRoute,
    spec: RepairRatchetSpec,
    base: MaintenanceSpec,
) -> dict[str, Any]:
    modes: dict[str, Any] = {}
    for mode in _modes(route):
        rows = [row for result in results for row in result["rows"] if row["mode"] == mode]
        distances: dict[str, Any] = {}
        for distance in base.pedigree_depths:
            selected = [row for row in rows if row["distance"] == distance]
            retention: dict[str, float] = {}
            collapse: dict[str, float] = {}
            rescue: dict[str, float] = {}
            information: dict[str, float] = {}
            change: dict[str, float] = {}
            for task_index in range(spec.task_count):
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
                    spec.pedigree_seed,
                    f"repair-ratchet.{route.name}.{mode}.d{distance}.{label}",
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
            "dose_scale": DOSE_SCALE.get(mode),
            "rows": len(rows),
            "distances": distances,
            "task_centered_immediate_parent_offspring_slope": _task_centered_slope(
                rows, spec.task_count
            ),
        }
    result = {
        "format": f"{PEDIGREE_FORMAT}-route-analysis",
        "route": route.name,
        "modes": modes,
        "retention_definition": "descendant information >= 0.70 times positive root information",
        "inferential_unit": "paired founder task",
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def run_repair_ratchet_pedigree(
    spec: RepairRatchetSpec,
    evolution: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    verify_repair_ratchet_evolution(evolution)
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("repair-ratchet pedigree permits one to four CPU workers")
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_repair_ratchet_pedigree(destination)
        return destination
    base = spec.maintenance()
    kernel = base.kernel()
    evolution_checksum = sha256_file(evolution / "SHA256SUMS")
    top_payload = {
        "spec": spec.to_dict(),
        "maintenance_spec": _json_value(base.to_dict()),
        "kernel": _json_value(kernel.to_dict()),
        "evolution_checksum": evolution_checksum,
        "dose_modes": list(GLOBAL_DOSE_MODES),
    }
    top_registration = {
        "format": f"{PEDIGREE_FORMAT}-registration",
        "protocol_digest": canonical_digest(top_payload),
        **top_payload,
        "evolution": str(evolution.resolve()),
    }
    top_path = destination / "registration.json"
    if top_path.is_file() and canonical_digest(read_json(top_path)) != canonical_digest(top_registration):
        raise ValueError("existing repair-ratchet pedigree registration differs")
    if not top_path.is_file():
        _atomic_json(top_path, top_registration)

    work: list[tuple[Any, ...]] = []
    route_registrations: dict[str, dict[str, Any]] = {}
    for route in spec.routes:
        route_dir = destination / route.name
        shards = route_dir / "populations"
        shards.mkdir(parents=True, exist_ok=True)
        registration = _route_registration(PEDIGREE_FORMAT, spec, base, kernel, evolution, route)
        registration["dose_modes"] = list(_modes(route))
        registration["protocol_digest"] = canonical_digest(
            {key: registration[key] for key in ("ratchet_spec", "maintenance_spec", "kernel", "evolution_checksum", "route", "dose_modes")}
        )
        route_registrations[route.name] = registration
        route_path = route_dir / "registration.json"
        if route_path.is_file() and canonical_digest(read_json(route_path)) != canonical_digest(registration):
            raise ValueError(f"existing pedigree registration differs for {route.name}")
        if not route_path.is_file():
            _atomic_json(route_path, registration)
        population_files = sorted(
            (evolution / "populations").glob(f"{route.name}.population-*.json")
        )
        work.extend(
            (
                str(path),
                route.to_dict(),
                _json_value(base.to_dict()),
                _json_value(kernel.to_dict()),
                str(shards),
                registration["protocol_digest"],
            )
            for path in population_files
        )
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
            progress(f"repair-ratchet pedigree {index}/{len(work)} populations")

    completed = _parallel(work, _pedigree_population, workers, update)
    total_rows = 0
    for route in spec.routes:
        route_dir = destination / route.name
        selected = [value for value in completed if value["route"] == route.name]
        analysis = _analyze_route_pedigree(selected, route, spec, base)
        _atomic_json(route_dir / "analysis.json", analysis)
        rows = sum(value["row_count"] for value in selected)
        total_rows += rows
        _atomic_json(
            route_dir / "manifest.json",
            {
                "format": f"{PEDIGREE_FORMAT}-route-manifest",
                "route": route.name,
                "protocol_digest": route_registrations[route.name]["protocol_digest"],
                "populations": len(selected),
                "rows": rows,
            },
        )
        write_checksums(route_dir)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{PEDIGREE_FORMAT}-manifest",
            "protocol_digest": top_registration["protocol_digest"],
            "populations": len(completed),
            "rows": total_rows,
            "elapsed_seconds": time.monotonic() - started,
            "workers_used": workers,
            "cpu_only": True,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_repair_ratchet_pedigree(destination)
    return destination


def verify_repair_ratchet_pedigree(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = RepairRatchetSpec.from_dict(registration["spec"])
    base = MaintenanceSpec.from_dict(registration["maintenance_spec"])
    CooptionSpec.from_dict(registration["kernel"])
    if registration.get("format") != f"{PEDIGREE_FORMAT}-registration":
        raise ValueError("repair-ratchet pedigree format mismatch")
    payload = {
        key: registration[key]
        for key in ("spec", "maintenance_spec", "kernel", "evolution_checksum", "dose_modes")
    }
    if canonical_digest(payload) != registration["protocol_digest"]:
        raise ValueError("repair-ratchet pedigree protocol mismatch")
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed repair-ratchet evolution changed after pedigree")
    total_populations = 0
    total_rows = 0
    for route in spec.routes:
        route_dir = directory / route.name
        verify_checksums(route_dir)
        route_registration = read_json(route_dir / "registration.json")
        route_manifest = read_json(route_dir / "manifest.json")
        analysis = read_json(route_dir / "analysis.json")
        analysis_payload = dict(analysis)
        archived_analysis = analysis_payload.pop("analysis_digest", None)
        if archived_analysis != canonical_digest(analysis_payload):
            raise ValueError(f"repair-ratchet pedigree analysis differs for {route.name}")
        files = sorted((route_dir / "populations").glob("*.json"))
        rows = 0
        for path in files:
            value = read_json(path)
            payload_value = dict(value)
            archived = payload_value.pop("result_digest", None)
            if (
                value.get("protocol_digest") != route_registration["protocol_digest"]
                or archived != canonical_digest(payload_value)
                or value.get("route") != route.name
            ):
                raise ValueError(f"repair-ratchet pedigree shard differs: {path}")
            rows += int(value["row_count"])
        expected_modes = len(_modes(route))
        expected_rows = (
            spec.task_count
            * base.pedigree_roots_per_task
            * base.pedigree_lineages_per_root
            * base.lineage_depth
            * expected_modes
        )
        if (
            len(files) != spec.task_count
            or rows != expected_rows
            or route_manifest.get("populations") != spec.task_count
            or route_manifest.get("rows") != expected_rows
        ):
            raise ValueError(f"repair-ratchet pedigree incomplete for {route.name}")
        total_populations += len(files)
        total_rows += rows
    expected_populations = spec.task_count * len(spec.routes)
    if (
        total_populations != expected_populations
        or manifest.get("populations") != expected_populations
        or manifest.get("rows") != total_rows
        or manifest.get("workers_used", 5) > spec.maximum_workers
        or not manifest.get("cpu_only")
    ):
        raise ValueError("repair-ratchet pedigree is incomplete")
    return {
        "verified": True,
        "populations": total_populations,
        "rows": total_rows,
        "checksums": len(checksums),
    }


__all__ = (
    "AUDIT_FORMAT",
    "DOSE_SCALE",
    "GLOBAL_DOSE_MODES",
    "PEDIGREE_FORMAT",
    "run_repair_ratchet_audit",
    "run_repair_ratchet_pedigree",
    "verify_repair_ratchet_audit",
    "verify_repair_ratchet_pedigree",
)
