"""Resumable four-hour orchestration for Wagner PH Origin Ladder v1."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterator

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .wagner_ph_ladder_analysis import (
    analyze_ladder_results,
    analyze_origin_autopsy,
    render_ladder_report,
)
from .wagner_ph_ladder_config import (
    LADDER_CAMPAIGN_FORMAT,
    LADDER_RESULT_FORMAT,
    LADDER_TASK_FORMAT,
    WagnerPHLadderSpec,
)
from .wagner_ph_ladder_experiment import sample_ladder_tasks, simulate_ladder_task
from .wagner_ph_ladder_protocols import wagner_ph_ladder_spec
from .wagner_ph_origin_campaign import verify_wagner_ph_origin_campaign


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


def _parent_provenance(parent: Path) -> dict[str, Any]:
    parent = parent.resolve()
    verification = verify_wagner_ph_origin_campaign(parent)
    seal = parent / "SHA256SUMS"
    manifest = parent / "campaign-manifest.json"
    if not seal.is_file() or not manifest.is_file():
        raise FileNotFoundError("Origin Ladder requires sealed origin-v1 parent")
    result = {
        "format": "gre-wagner-ph-origin-ladder-parent-v1",
        "parent": str(parent),
        "parent_checksum_digest": sha256_file(seal),
        "parent_manifest_digest": canonical_digest(read_json(manifest)),
        "parent_verification": verification,
        "role": "posthoc autopsy only; no parent outcome selects a fresh task",
    }
    result["provenance_digest"] = canonical_digest(result)
    return result


def _completed_result(path: Path, task: dict[str, Any]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = read_json(path)
    if (
        value.get("format") != LADDER_RESULT_FORMAT
        or value.get("task_id") != task["task_id"]
        or value.get("task_digest") != task["task_digest"]
    ):
        return None
    _payload_digest(value, "result_digest")
    return value


def _iter_results(
    tasks: list[dict[str, Any]],
    spec: WagnerPHLadderSpec,
    workers: int,
) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    if workers == 1:
        for task in tasks:
            yield task, simulate_ladder_task(task, spec.to_dict())
        return
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=context
    ) as executor:
        pending = {
            executor.submit(simulate_ladder_task, task, spec.to_dict()): task
            for task in tasks
        }
        for future in concurrent.futures.as_completed(pending):
            yield pending[future], future.result()


def _soft_deadline(started_epoch: float, spec: WagnerPHLadderSpec) -> float:
    registered = os.environ.get("GRE_WAGNER_PH_LADDER_SOFT_DEADLINE_EPOCH")
    if registered is not None:
        try:
            return float(registered)
        except ValueError as error:
            raise ValueError("invalid Origin Ladder soft deadline") from error
    return started_epoch + spec.soft_wall_seconds


def _prior_consumed_seconds() -> float:
    registered = os.environ.get("GRE_WAGNER_PH_LADDER_PRIOR_CONSUMED_SECONDS", "0")
    try:
        value = float(registered)
    except ValueError as error:
        raise ValueError("invalid Origin Ladder prior consumed time") from error
    if value < 0.0:
        raise ValueError("Origin Ladder prior consumed time cannot be negative")
    return value


def _write_progress(
    destination: Path,
    stage: str,
    completed: int,
    total: int,
    started: float,
) -> None:
    elapsed = max(time.monotonic() - started, 0.0)
    rate = completed / elapsed if completed and elapsed else 0.0
    _atomic_json(
        destination / "progress.json",
        {
            "format": "gre-wagner-ph-origin-ladder-progress-v1",
            "stage": stage,
            "completed_tasks": completed,
            "total_tasks": total,
            "elapsed_seconds": elapsed,
            "tasks_per_second": rate,
            "eta_seconds": (total - completed) / rate if rate else None,
        },
    )


def run_wagner_ph_ladder_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    """Run or resume the frozen exploratory ladder; never consume confirmation RNG."""

    spec = wagner_ph_ladder_spec(smoke=smoke)
    spec.validate()
    if workers < 1 or workers > spec.maximum_workers:
        raise ValueError("Origin Ladder permits one to four CPU workers")
    destination = destination.resolve()
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_ladder_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_monotonic = time.monotonic()
    started_epoch = time.time()
    prior_consumed = _prior_consumed_seconds()
    deadline = _soft_deadline(started_epoch, spec)
    protocol_digest = canonical_digest(spec.to_dict())
    provenance = _parent_provenance(parent)
    registration = {
        "format": LADDER_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "parent_provenance_digest": provenance["provenance_digest"],
        "cpu_only": True,
        "confirmation_authorized": False,
        "confirmation_rng_draws_consumed": 0,
    }
    registration_path = destination / "registration.json"
    provenance_path = destination / "parent-provenance.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing Origin Ladder registration differs")
    if provenance_path.is_file() and read_json(provenance_path) != provenance:
        raise ValueError("existing Origin Ladder parent provenance differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    if not provenance_path.is_file():
        _atomic_json(provenance_path, provenance)

    autopsy_path = destination / "origin-v1-autopsy.json"
    if not autopsy_path.is_file():
        if progress:
            progress("pairing origin-v1 training and heldout outcomes for the autopsy")
        _atomic_json(autopsy_path, analyze_origin_autopsy(parent))

    tasks_path = destination / "tasks.json"
    if tasks_path.is_file():
        registry = read_json(tasks_path)
        if (
            registry.get("format") != "gre-wagner-ph-origin-ladder-task-registry-v1"
            or registry.get("protocol_digest") != protocol_digest
        ):
            raise ValueError("existing Origin Ladder task registry differs")
        tasks = list(registry["tasks"])
    else:
        if progress:
            progress(f"sampling {spec.tasks} fresh outcome-blind Wagner tasks")
        tasks = sample_ladder_tasks(spec)
        registry = {
            "format": "gre-wagner-ph-origin-ladder-task-registry-v1",
            "protocol_digest": protocol_digest,
            "tasks": tasks,
            "task_count": len(tasks),
            "task_registry_digest": canonical_digest(tasks),
        }
        _atomic_json(tasks_path, registry)
    if len(tasks) != spec.tasks:
        raise ValueError("Origin Ladder task count differs from protocol")
    for task in tasks:
        if task.get("format") != LADDER_TASK_FORMAT:
            raise ValueError("Origin Ladder task format mismatch")
        _payload_digest(task, "task_digest")

    shards = destination / "task-results"
    shards.mkdir(exist_ok=True)
    completed: dict[str, dict[str, Any]] = {}
    for task in tasks:
        value = _completed_result(shards / f"{task['task_id']}.json", task)
        if value is not None:
            completed[str(task["task_id"])] = value
    _write_progress(
        destination, "diagnostic-grid", len(completed), spec.tasks, started_monotonic
    )
    missing = [task for task in tasks if task["task_id"] not in completed]
    if progress:
        progress(
            f"starting quantized capacity, coordination, and ecology grids "
            f"({len(completed)}/{spec.tasks} tasks already complete)"
        )
    for task, result in _iter_results(missing, spec, workers):
        _payload_digest(result, "result_digest")
        _atomic_json(shards / f"{task['task_id']}.json", result)
        completed[str(task["task_id"])] = result
        _write_progress(
            destination,
            "diagnostic-grid",
            len(completed),
            spec.tasks,
            started_monotonic,
        )
        if progress:
            progress(f"completed Origin Ladder task {len(completed)}/{spec.tasks}")
        if time.time() >= deadline and len(completed) < spec.tasks:
            raise TimeoutError("Origin Ladder soft wall-time boundary reached")

    ordered = [completed[str(task["task_id"])] for task in tasks]
    if progress:
        progress("analyzing barrier diagnoses and freezing the finalist rule")
    _write_progress(
        destination, "analysis", spec.tasks, spec.tasks, started_monotonic
    )
    autopsy = read_json(autopsy_path)
    analysis = analyze_ladder_results(ordered, spec, autopsy)
    _atomic_json(destination / "analysis.json", analysis)
    reserve = {
        **analysis["confirmation_reserve"],
        "format": "gre-wagner-ph-origin-ladder-confirmation-reserve-v1",
        "finalist": analysis["finalist"],
        "exploration_analysis_digest": canonical_digest(analysis),
        "note": "No confirmation task, environment sequence, or assay stream has been generated.",
    }
    _atomic_json(destination / "confirmation-reserve.json", reserve)
    elapsed = time.monotonic() - started_monotonic
    cumulative = prior_consumed + elapsed
    manifest = {
        "format": LADDER_CAMPAIGN_FORMAT,
        "protocol_digest": protocol_digest,
        "parent_provenance_digest": provenance["provenance_digest"],
        "task_registry_digest": registry["task_registry_digest"],
        "analysis_digest": canonical_digest(analysis),
        "tasks": spec.tasks,
        "capacity_cells_per_task": spec.capacity_cell_count,
        "coordination_cells_per_task": spec.coordination_cell_count,
        "ecology_cells_per_task": spec.ecology_cell_count,
        "maximum_workers": workers,
        "cpu_only": True,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior_consumed,
        "cumulative_wall_seconds": cumulative,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_four_hour_boundary": cumulative <= spec.hard_wall_seconds,
        "confirmation_status": "untouched",
        "confirmation_rng_draws_consumed": 0,
        "runtime": runtime_manifest(),
        "claim_boundary": analysis["claim_boundary"],
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    (destination / "report.md").write_text(
        render_ladder_report(analysis), encoding="utf-8"
    )
    _write_progress(destination, "sealing", spec.tasks, spec.tasks, started_monotonic)
    write_checksums(destination)
    verify_wagner_ph_ladder_campaign(destination)
    if progress:
        progress("sealed and independently verified Origin Ladder exploration")
    return destination


def verify_wagner_ph_ladder_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    provenance = read_json(directory / "parent-provenance.json")
    registry = read_json(directory / "tasks.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    reserve = read_json(directory / "confirmation-reserve.json")
    if registration.get("format") != LADDER_CAMPAIGN_FORMAT:
        raise ValueError("Origin Ladder registration format mismatch")
    if manifest.get("format") != LADDER_CAMPAIGN_FORMAT:
        raise ValueError("Origin Ladder manifest format mismatch")
    spec = WagnerPHLadderSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("Origin Ladder protocol digest mismatch")
    _payload_digest(provenance, "provenance_digest")
    if provenance["provenance_digest"] != registration["parent_provenance_digest"]:
        raise ValueError("Origin Ladder parent provenance mismatch")
    if sha256_file(Path(provenance["parent"]) / "SHA256SUMS") != provenance[
        "parent_checksum_digest"
    ]:
        raise ValueError("Origin Ladder sealed parent has changed")
    tasks = list(registry["tasks"])
    if len(tasks) != spec.tasks or registry["task_registry_digest"] != canonical_digest(
        tasks
    ):
        raise ValueError("Origin Ladder task registry mismatch")
    for task in tasks:
        _payload_digest(task, "task_digest")
        result = read_json(directory / "task-results" / f"{task['task_id']}.json")
        _payload_digest(result, "result_digest")
        if result["task_digest"] != task["task_digest"]:
            raise ValueError("Origin Ladder result/task mismatch")
    if manifest["analysis_digest"] != canonical_digest(analysis):
        raise ValueError("Origin Ladder analysis digest mismatch")
    if reserve.get("status") != "untouched" or reserve.get("rng_draws_consumed") != 0:
        raise ValueError("Origin Ladder confirmation reserve is not untouched")
    if registration.get("confirmation_authorized") is not False:
        raise ValueError("Origin Ladder exploration improperly authorized confirmation")
    return {
        "verified": True,
        "tasks": spec.tasks,
        "checksums": len(checksums),
        "confirmation_status": "untouched",
        "finalist": analysis.get("finalist"),
    }


def replay_wagner_ph_ladder_task(directory: Path, task_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    spec = WagnerPHLadderSpec.from_dict(registration["protocol"])
    task = next(
        (
            value
            for value in read_json(directory / "tasks.json")["tasks"]
            if value["task_id"] == task_id
        ),
        None,
    )
    if task is None:
        raise KeyError(f"unknown Origin Ladder task: {task_id}")
    archived = read_json(directory / "task-results" / f"{task_id}.json")
    replayed = simulate_ladder_task(task, spec.to_dict())
    return {
        "task_id": task_id,
        "matches": archived["result_digest"] == replayed["result_digest"],
        "archived_digest": archived["result_digest"],
        "replayed_digest": replayed["result_digest"],
    }


def wagner_ph_ladder_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    if (directory / "SHA256SUMS").is_file():
        try:
            verification = verify_wagner_ph_ladder_campaign(directory)
            manifest = read_json(directory / "campaign-manifest.json")
            analysis = read_json(directory / "analysis.json")
            return {
                "status": "completed",
                **verification,
                "elapsed_seconds": manifest["elapsed_seconds"],
                "barrier_diagnoses": analysis["barrier_diagnoses"],
            }
        except Exception as error:
            return {"status": "sealed-invalid", "error": str(error)}
    progress_path = directory / "progress.json"
    value = read_json(progress_path) if progress_path.is_file() else {}
    registration_path = directory / "registration.json"
    total = None
    if registration_path.is_file():
        total = WagnerPHLadderSpec.from_dict(
            read_json(registration_path)["protocol"]
        ).tasks
    completed = len(list((directory / "task-results").glob("task-*.json"))) if (
        directory / "task-results"
    ).is_dir() else 0
    return {
        "status": "running-or-resumable",
        "stage": value.get("stage", "preparing"),
        "completed_tasks": completed,
        "total_tasks": total,
        "elapsed_seconds": value.get("elapsed_seconds"),
        "eta_seconds": value.get("eta_seconds"),
        "confirmation_status": "untouched",
    }
