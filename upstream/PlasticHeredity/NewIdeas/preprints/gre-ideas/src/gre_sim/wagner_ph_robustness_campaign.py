"""Bounded orchestration for mutation autopsy and robustness-ratchet evolution."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .wagner_ph_direct_campaign import verify_wagner_ph_direct_prediction_campaign
from .wagner_ph_robustness_analysis import (
    analyze_robustness_campaign,
    render_robustness_report,
)
from .wagner_ph_robustness_audit import run_robustness_audit, verify_robustness_audit
from .wagner_ph_robustness_autopsy import run_mutation_autopsy, verify_mutation_autopsy
from .wagner_ph_robustness_config import (
    ROBUSTNESS_CAMPAIGN_FORMAT,
    RobustnessSpec,
    robustness_spec,
)
from .wagner_ph_robustness_evolution import (
    replay_robustness_population,
    run_robustness_evolution,
    verify_robustness_evolution,
)
from .wagner_ph_robustness_pedigree import (
    replay_pedigree_event,
    run_robustness_pedigree,
    verify_robustness_pedigree,
)


STAGES = ("mutation-autopsy", "robustness-evolution", "causal-audit", "pedigree", "analysis")


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


def _soft_deadline(started: float, spec: RobustnessSpec) -> float:
    value = os.environ.get("GRE_WAGNER_PH_ROBUSTNESS_SOFT_DEADLINE_EPOCH")
    if value is None:
        return started + spec.soft_wall_seconds
    try:
        return float(value)
    except ValueError as error:
        raise ValueError("invalid robustness soft deadline") from error


def _prior_consumed_seconds() -> float:
    value = os.environ.get("GRE_WAGNER_PH_ROBUSTNESS_PRIOR_CONSUMED_SECONDS", "0")
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError("invalid robustness consumed-time ledger") from error
    if result < 0.0:
        raise ValueError("robustness consumed time cannot be negative")
    return result


def _require_budget(deadline: float, reservation: int, stage: str) -> None:
    remaining = deadline - time.time()
    if remaining < reservation:
        raise TimeoutError(
            f"insufficient registered soft-wall reserve to start {stage}: "
            f"{remaining:.1f}s remain; {reservation}s required"
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
            "format": "gre-wagner-ph-robustness-progress-v1",
            "stage": stage,
            "detail": detail,
            "completed_units": completed,
            "total_units": total,
            "elapsed_seconds": elapsed,
            "units_per_second": rate,
            "eta_seconds": (total - completed) / rate if rate else None,
        },
    )


def _initial_ledger(spec: RobustnessSpec) -> dict[str, Any]:
    return {
        "format": "gre-wagner-ph-robustness-resource-ledger-v1",
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
        "stages": {
            stage: {
                "reservation_seconds": reservation,
                "status": "pending",
                "attempts": 0,
                "elapsed_seconds": 0.0,
            }
            for stage, reservation in zip(STAGES, spec.stage_reservations_seconds)
        },
    }


def _stage_begin(
    destination: Path,
    spec: RobustnessSpec,
    deadline: float,
    stage: str,
) -> float:
    index = STAGES.index(stage)
    reservation = spec.stage_reservations_seconds[index]
    _require_budget(deadline, reservation, stage)
    path = destination / "resource-ledger.json"
    ledger = read_json(path) if path.is_file() else _initial_ledger(spec)
    entry = ledger["stages"][stage]
    entry["status"] = "running"
    entry["attempts"] = int(entry.get("attempts", 0)) + 1
    entry["last_started_epoch"] = time.time()
    _atomic_json(path, ledger)
    return time.monotonic()


def _stage_complete(destination: Path, stage: str, started: float) -> None:
    path = destination / "resource-ledger.json"
    ledger = read_json(path)
    entry = ledger["stages"][stage]
    entry["elapsed_seconds"] = float(entry.get("elapsed_seconds", 0.0)) + (
        time.monotonic() - started
    )
    entry["status"] = "completed"
    entry["last_completed_epoch"] = time.time()
    _atomic_json(path, ledger)


def _recover_completed_stage(destination: Path, stage: str) -> None:
    path = destination / "resource-ledger.json"
    ledger = read_json(path) if path.is_file() else None
    if ledger is None:
        return
    entry = ledger["stages"][stage]
    if entry["status"] != "completed":
        entry["status"] = "completed"
        entry["recovered_from_sealed_stage"] = True
        _atomic_json(path, ledger)


def run_wagner_ph_robustness_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = robustness_spec(smoke=smoke)
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("robustness campaign permits one to four CPU workers")
    parent = parent.resolve()
    parent_verification = verify_wagner_ph_direct_prediction_campaign(parent)
    parent_registration = read_json(parent / "registration.json")
    expected_parent = spec.parent_cohort_id + ("-smoke" if smoke else "")
    if parent_registration["protocol"]["cohort_id"] != expected_parent:
        raise ValueError("robustness parent is not the matching sealed direct-prediction cohort")
    destination = destination.resolve()
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_robustness_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_monotonic = time.monotonic()
    started_epoch = time.time()
    deadline = _soft_deadline(started_epoch, spec)
    prior_consumed = _prior_consumed_seconds()
    kernel = spec.kernel()
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": ROBUSTNESS_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "simulation_kernel": kernel.to_dict(),
        "simulation_kernel_digest": canonical_digest(kernel.to_dict()),
        "direct_parent": str(parent),
        "direct_parent_checksum": sha256_file(parent / "SHA256SUMS"),
        "direct_parent_verification": parent_verification,
        "source_variant": spec.parent_variant,
        "development_reuses_sealed_tasks": True,
        "fresh_confirmation_tasks_consumed": False,
        "unused_confirmation_seed": spec.unused_confirmation_seed,
        "cpu_only": True,
        "workers_requested": workers,
        "stage_reservations_seconds": dict(zip(STAGES, spec.stage_reservations_seconds)),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing robustness campaign registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    ledger_path = destination / "resource-ledger.json"
    if not ledger_path.is_file():
        _atomic_json(ledger_path, _initial_ledger(spec))

    autopsy_dir = destination / "mutation-autopsy"
    if not (autopsy_dir / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, spec, deadline, "mutation-autopsy")
        if progress:
            progress("starting exact mutation replay and 2^4 factorial autopsy")
        run_mutation_autopsy(spec, parent, autopsy_dir, workers, progress)
        _stage_complete(destination, "mutation-autopsy", stage_started)
    else:
        verify_mutation_autopsy(autopsy_dir)
        _recover_completed_stage(destination, "mutation-autopsy")
    _write_progress(destination, "mutation-autopsy", 1, 1, started_monotonic)

    evolution_dir = destination / "evolution"
    if not (evolution_dir / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, spec, deadline, "robustness-evolution")
        if progress:
            progress("starting eight-arm robustness-ratchet continuation evolution")
        run_robustness_evolution(spec, parent, evolution_dir, workers, progress)
        _stage_complete(destination, "robustness-evolution", stage_started)
    else:
        verify_robustness_evolution(evolution_dir)
        _recover_completed_stage(destination, "robustness-evolution")
    _write_progress(destination, "robustness-evolution", 1, 1, started_monotonic)

    audit_dir = destination / "audit"
    if not (audit_dir / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, spec, deadline, "causal-audit")
        if progress:
            progress("starting held-out four-persistence causal audit")
        run_robustness_audit(spec, evolution_dir, audit_dir, workers, progress)
        _stage_complete(destination, "causal-audit", stage_started)
    else:
        verify_robustness_audit(audit_dir)
        _recover_completed_stage(destination, "causal-audit")
    _write_progress(destination, "causal-audit", 1, 1, started_monotonic)

    pedigree_dir = destination / "pedigree"
    if not (pedigree_dir / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, spec, deadline, "pedigree")
        if progress:
            progress("starting complete-genotype child/grandchild pedigree")
        run_robustness_pedigree(spec, evolution_dir, pedigree_dir, workers, progress)
        _stage_complete(destination, "pedigree", stage_started)
    else:
        verify_robustness_pedigree(pedigree_dir)
        _recover_completed_stage(destination, "pedigree")
    _write_progress(destination, "pedigree", 1, 1, started_monotonic)

    stage_started = _stage_begin(destination, spec, deadline, "analysis")
    audit_rows = [
        read_json(path) for path in sorted((audit_dir / "populations").glob("*.json"))
    ]
    pedigree = read_json(pedigree_dir / "analysis.json")
    autopsy = read_json(autopsy_dir / "analysis.json")
    analysis = analyze_robustness_campaign(audit_rows, pedigree, autopsy, spec)
    _atomic_json(destination / "analysis.json", analysis)
    elapsed = time.monotonic() - started_monotonic
    cumulative = prior_consumed + elapsed
    manifest = {
        "format": ROBUSTNESS_CAMPAIGN_FORMAT,
        "protocol_digest": protocol_digest,
        "simulation_kernel_digest": canonical_digest(kernel.to_dict()),
        "direct_parent_checksum": registration["direct_parent_checksum"],
        "autopsy_checksum": sha256_file(autopsy_dir / "SHA256SUMS"),
        "evolution_checksum": sha256_file(evolution_dir / "SHA256SUMS"),
        "audit_checksum": sha256_file(audit_dir / "SHA256SUMS"),
        "pedigree_checksum": sha256_file(pedigree_dir / "SHA256SUMS"),
        "analysis_digest": analysis["analysis_digest"],
        "populations": spec.population_count,
        "descendants": spec.pedigree_descendant_count,
        "factorial_hybrids": autopsy["factorial_hybrids"],
        "maximum_workers": workers,
        "cpu_only": True,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior_consumed,
        "cumulative_wall_seconds": cumulative,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_four_hour_boundary": cumulative <= spec.hard_wall_seconds,
        "fresh_confirmation_tasks_consumed": False,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    (destination / "report.md").write_text(
        render_robustness_report(analysis), encoding="utf-8"
    )
    _stage_complete(destination, "analysis", stage_started)
    _write_progress(destination, "sealed", 1, 1, started_monotonic)
    write_checksums(destination)
    verify_wagner_ph_robustness_campaign(destination)
    if progress:
        progress("sealed and independently verified robustness-ratchet campaign")
    return destination


def verify_wagner_ph_robustness_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    ledger = read_json(directory / "resource-ledger.json")
    if registration.get("format") != ROBUSTNESS_CAMPAIGN_FORMAT:
        raise ValueError("robustness campaign registration format mismatch")
    if manifest.get("format") != ROBUSTNESS_CAMPAIGN_FORMAT:
        raise ValueError("robustness campaign manifest format mismatch")
    spec = RobustnessSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("robustness campaign protocol digest mismatch")
    parent = Path(registration["direct_parent"])
    if sha256_file(parent / "SHA256SUMS") != registration["direct_parent_checksum"]:
        raise ValueError("sealed direct parent changed after robustness campaign")
    nested = {
        "autopsy": verify_mutation_autopsy(directory / "mutation-autopsy"),
        "evolution": verify_robustness_evolution(directory / "evolution"),
        "audit": verify_robustness_audit(directory / "audit"),
        "pedigree": verify_robustness_pedigree(directory / "pedigree"),
    }
    expected_checksums = {
        "autopsy_checksum": sha256_file(directory / "mutation-autopsy" / "SHA256SUMS"),
        "evolution_checksum": sha256_file(directory / "evolution" / "SHA256SUMS"),
        "audit_checksum": sha256_file(directory / "audit" / "SHA256SUMS"),
        "pedigree_checksum": sha256_file(directory / "pedigree" / "SHA256SUMS"),
    }
    for field, expected in expected_checksums.items():
        if manifest[field] != expected:
            raise ValueError(f"robustness campaign {field} mismatch")
    _payload_digest(analysis, "analysis_digest")
    if manifest["analysis_digest"] != analysis["analysis_digest"]:
        raise ValueError("robustness campaign analysis reference mismatch")
    if int(manifest["populations"]) != spec.population_count:
        raise ValueError("robustness campaign population count mismatch")
    if int(manifest["descendants"]) != spec.pedigree_descendant_count:
        raise ValueError("robustness campaign descendant count mismatch")
    if manifest["fresh_confirmation_tasks_consumed"] or analysis[
        "fresh_confirmation_seed_consumed"
    ]:
        raise ValueError("fresh confirmation reserve was unexpectedly consumed")
    if ledger.get("format") != "gre-wagner-ph-robustness-resource-ledger-v1":
        raise ValueError("robustness resource ledger format mismatch")
    if any(ledger["stages"][stage]["status"] != "completed" for stage in STAGES):
        raise ValueError("robustness resource ledger contains incomplete stages")
    return {
        "verified": True,
        "top_level_checksums": len(checksums),
        "populations": spec.population_count,
        "descendants": spec.pedigree_descendant_count,
        "factorial_hybrids": int(manifest["factorial_hybrids"]),
        "nested": nested,
    }


def wagner_ph_robustness_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    if (directory / "SHA256SUMS").is_file():
        try:
            verification = verify_wagner_ph_robustness_campaign(directory)
        except Exception as error:
            return {"status": "sealed-invalid", "output": str(directory), "error": str(error)}
        manifest = read_json(directory / "campaign-manifest.json")
        analysis = read_json(directory / "analysis.json")
        return {
            "status": "complete",
            "output": str(directory),
            "verification": verification,
            "elapsed_seconds": manifest["elapsed_seconds"],
            "tier_A_passes": analysis["tier_A_passes"],
            "tier_passes": {name: value["passes"] for name, value in analysis["tiers"].items()},
        }
    result: dict[str, Any] = {"status": "incomplete", "output": str(directory)}
    for name in ("progress.json", "resource-ledger.json", "registration.json"):
        path = directory / name
        if path.is_file():
            try:
                result[name.removesuffix(".json").replace("-", "_")] = read_json(path)
            except Exception as error:
                result[f"{name}_error"] = str(error)
    stage_counts: dict[str, Any] = {}
    for stage, relative in (
        ("mutation-autopsy", "mutation-autopsy/tasks"),
        ("robustness-evolution", "evolution/populations"),
        ("causal-audit", "audit/populations"),
        ("pedigree", "pedigree/populations"),
    ):
        path = directory / relative
        stage_counts[stage] = len(
            [value for value in path.glob("*.json") if not value.name.endswith(".checkpoint.json")]
        ) if path.is_dir() else 0
    result["completed_shards"] = stage_counts
    return result


def replay_wagner_ph_robustness(
    directory: Path,
    population_id: str,
    *,
    pedigree: bool = False,
    parent_index: int = 0,
    child_index: int = 0,
    grandchild_index: int | None = None,
) -> dict[str, Any]:
    if pedigree:
        return replay_pedigree_event(
            directory / "pedigree",
            population_id,
            parent_index,
            child_index,
            grandchild_index,
        )
    return replay_robustness_population(directory / "evolution", population_id)
