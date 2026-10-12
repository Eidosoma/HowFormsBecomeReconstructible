"""Gated orchestration for Global Repair Ratchet v1."""

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
from .wagner_ph_cooption_evolution import verify_cooption_evolution
from .wagner_ph_maintenance_campaign import verify_wagner_ph_maintenance_campaign
from .wagner_ph_repair_ratchet_analysis import (
    analyze_repair_ratchet,
    render_repair_ratchet_report,
)
from .wagner_ph_repair_ratchet_config import (
    RATCHET_FORMAT,
    RepairRatchetSpec,
    repair_ratchet_spec,
)
from .wagner_ph_repair_ratchet_evidence import (
    run_repair_ratchet_audit,
    run_repair_ratchet_pedigree,
    verify_repair_ratchet_audit,
    verify_repair_ratchet_pedigree,
)
from .wagner_ph_repair_ratchet_evolution import (
    replay_repair_ratchet_population,
    run_repair_ratchet_evolution,
    verify_repair_ratchet_evolution,
)


STAGES = ("development-evolution", "development-evidence", "analysis-sealing")


def _implementation_digest() -> str:
    root = Path(__file__).resolve().parents[2]
    names = (
        "WAGNER_PH_GLOBAL_REPAIR_RATCHET_V1_PROTOCOL.md",
        "src/gre_sim/wagner.py",
        "src/gre_sim/wagner_ph_cooption_evolution.py",
        "src/gre_sim/wagner_ph_maintenance_config.py",
        "src/gre_sim/wagner_ph_maintenance_genome.py",
        "src/gre_sim/wagner_ph_maintenance_evolution.py",
        "src/gre_sim/wagner_ph_maintenance_evidence.py",
        "src/gre_sim/wagner_ph_maintenance_analysis.py",
        "src/gre_sim/wagner_ph_repair_ratchet_config.py",
        "src/gre_sim/wagner_ph_repair_ratchet_evolution.py",
        "src/gre_sim/wagner_ph_repair_ratchet_evidence.py",
        "src/gre_sim/wagner_ph_repair_ratchet_analysis.py",
        "src/gre_sim/wagner_ph_repair_ratchet_campaign.py",
        "src/gre_sim/wagner_ph_repair_ratchet_cli.py",
    )
    return canonical_digest({name: sha256_file(root / name) for name in names})


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _atomic_text(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _payload_digest(value: dict[str, Any], field: str) -> str:
    payload = dict(value)
    archived = payload.pop(field, None)
    digest = canonical_digest(payload)
    if archived != digest:
        raise ValueError(f"{field} mismatch")
    return digest


def _deadline(started: float, spec: RepairRatchetSpec) -> float:
    value = os.environ.get("GRE_WAGNER_PH_REPAIR_RATCHET_SOFT_DEADLINE_EPOCH")
    return float(value) if value is not None else started + spec.soft_wall_seconds


def _prior_consumed() -> float:
    value = float(os.environ.get("GRE_WAGNER_PH_REPAIR_RATCHET_PRIOR_CONSUMED_SECONDS", "0"))
    if value < 0.0:
        raise ValueError("repair-ratchet consumed wall time cannot be negative")
    return value


def _initial_ledger(spec: RepairRatchetSpec, workers: int) -> dict[str, Any]:
    return {
        "format": f"{RATCHET_FORMAT}-resource-ledger",
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "maximum_workers": spec.maximum_workers,
        "workers_requested": workers,
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


def _stage_begin(destination: Path, deadline: float, stage: str, reservation: int) -> float:
    remaining = deadline - time.time()
    if remaining < reservation:
        raise TimeoutError(
            f"insufficient registered reserve for {stage}: {remaining:.1f}s remain; "
            f"{reservation}s required"
        )
    path = destination / "resource-ledger.json"
    ledger = read_json(path)
    entry = ledger["stages"][stage]
    entry["status"] = "running"
    entry["attempts"] += 1
    entry["last_started_epoch"] = time.time()
    _atomic_json(path, ledger)
    return time.monotonic()


def _stage_complete(destination: Path, stage: str, started: float) -> None:
    path = destination / "resource-ledger.json"
    ledger = read_json(path)
    entry = ledger["stages"][stage]
    entry["elapsed_seconds"] += time.monotonic() - started
    entry["status"] = "completed"
    entry["last_completed_epoch"] = time.time()
    _atomic_json(path, ledger)


def _recover(destination: Path, stage: str) -> None:
    path = destination / "resource-ledger.json"
    ledger = read_json(path)
    if ledger["stages"][stage]["status"] != "completed":
        ledger["stages"][stage]["status"] = "completed"
        ledger["stages"][stage]["recovered_from_sealed_stage"] = True
        _atomic_json(path, ledger)


def _progress(destination: Path, stage: str, started: float) -> None:
    _atomic_json(
        destination / "progress.json",
        {
            "format": f"{RATCHET_FORMAT}-progress",
            "stage": stage,
            "elapsed_seconds": time.monotonic() - started,
            "updated_epoch": time.time(),
        },
    )


def run_wagner_ph_repair_ratchet_campaign(
    reference: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = repair_ratchet_spec(smoke=smoke)
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("repair-ratchet campaign permits one to four CPU workers")
    reference = reference.resolve()
    destination = destination.resolve()
    started_mono = time.monotonic()
    started_epoch = time.time()
    prior = _prior_consumed()
    deadline = _deadline(started_epoch, spec)
    reference_verification = verify_wagner_ph_maintenance_campaign(reference)
    reference_registration = read_json(reference / "registration.json")
    source = Path(reference_registration["source_burnin"]).resolve()
    verify_cooption_evolution(source)
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_repair_ratchet_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    registration = {
        "format": RATCHET_FORMAT,
        "campaign_kind": "exploratory-development",
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
        "implementation_digest": _implementation_digest(),
        "adaptive_maintenance_reference": str(reference),
        "adaptive_maintenance_reference_checksum": sha256_file(reference / "SHA256SUMS"),
        "adaptive_maintenance_reference_verification": reference_verification,
        "reference_analysis_digest": read_json(reference / "analysis.json")["analysis_digest"],
        "source_burnin": str(source),
        "source_burnin_checksum": sha256_file(source / "SHA256SUMS"),
        "confirmation_seed_commitment": canonical_digest(
            (spec.confirmation_seed, "global-repair-ratchet-confirmation-commitment")
        ),
        "confirmation_requires_separate_explicit_authorization": True,
        "workers_requested": workers,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(read_json(registration_path)) != canonical_digest(registration):
        raise ValueError("existing repair-ratchet campaign registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    if not (destination / "resource-ledger.json").is_file():
        _atomic_json(destination / "resource-ledger.json", _initial_ledger(spec, workers))

    evolution = destination / "development" / "evolution"
    stage = STAGES[0]
    if not (evolution / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, deadline, stage, spec.stage_reservations_seconds[0])
        if progress:
            progress("starting eight-route global-repair accessibility evolution")
        run_repair_ratchet_evolution(spec, source, evolution, workers, progress)
        _stage_complete(destination, stage, stage_started)
    else:
        verify_repair_ratchet_evolution(evolution)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    audit = destination / "development" / "audit"
    pedigree = destination / "development" / "pedigree"
    stage = STAGES[1]
    if not (audit / "SHA256SUMS").is_file() or not (pedigree / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, deadline, stage, spec.stage_reservations_seconds[1])
        if progress:
            progress("starting held-out F1/F4/F12 audits and five-dose repair pedigrees")
        run_repair_ratchet_audit(spec, evolution, audit, workers, progress)
        run_repair_ratchet_pedigree(spec, evolution, pedigree, workers, progress)
        _stage_complete(destination, stage, stage_started)
    else:
        verify_repair_ratchet_audit(audit)
        verify_repair_ratchet_pedigree(pedigree)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    stage = STAGES[2]
    stage_started = _stage_begin(destination, deadline, stage, spec.stage_reservations_seconds[2])
    analysis_path = destination / "analysis.json"
    if not analysis_path.is_file():
        analysis = analyze_repair_ratchet(spec, evolution, audit, pedigree, reference)
        _atomic_json(analysis_path, analysis)
        _atomic_json(
            destination / "nomination.json",
            {
                **analysis["nomination"],
                "analysis_digest": analysis["analysis_digest"],
                "confirmation_seed_generated_zero_tasks": True,
            },
        )
        _atomic_text(destination / "report.md", render_repair_ratchet_report(analysis))
    else:
        analysis = read_json(analysis_path)
        _payload_digest(analysis, "analysis_digest")
    _stage_complete(destination, stage, stage_started)
    _progress(destination, "sealed-development", started_mono)
    elapsed = time.monotonic() - started_mono
    _atomic_json(
        destination / "campaign-manifest.json",
        {
            "format": RATCHET_FORMAT,
            "campaign_kind": "exploratory-development",
            "protocol_digest": registration["protocol_digest"],
            "implementation_digest": registration["implementation_digest"],
            "reference_checksum": registration["adaptive_maintenance_reference_checksum"],
            "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
            "audit_checksum": sha256_file(audit / "SHA256SUMS"),
            "pedigree_checksum": sha256_file(pedigree / "SHA256SUMS"),
            "analysis_digest": analysis["analysis_digest"],
            "nomination": analysis["nomination"],
            "development_populations": spec.task_count * len(spec.routes),
            "elapsed_seconds": elapsed,
            "prior_consumed_seconds": prior,
            "cumulative_wall_seconds": prior + elapsed,
            "hard_wall_seconds": spec.hard_wall_seconds,
            "soft_wall_seconds": spec.soft_wall_seconds,
            "completed_within_eight_hour_boundary": prior + elapsed <= spec.hard_wall_seconds,
            "workers_used": workers,
            "maximum_workers": spec.maximum_workers,
            "cpu_only": True,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_wagner_ph_repair_ratchet_campaign(destination)
    if progress:
        progress("sealed and independently verified Global Repair Ratchet v1")
    return destination


def verify_wagner_ph_repair_ratchet_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    nomination = read_json(directory / "nomination.json")
    ledger = read_json(directory / "resource-ledger.json")
    if registration.get("format") != RATCHET_FORMAT or manifest.get("format") != RATCHET_FORMAT:
        raise ValueError("repair-ratchet campaign format mismatch")
    spec = RepairRatchetSpec.from_dict(registration["protocol"])
    if (
        canonical_digest(spec.to_dict()) != registration["protocol_digest"]
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or registration["implementation_digest"] != _implementation_digest()
        or manifest["implementation_digest"] != registration["implementation_digest"]
    ):
        raise ValueError("repair-ratchet protocol or implementation changed")
    reference = Path(registration["adaptive_maintenance_reference"])
    if (
        sha256_file(reference / "SHA256SUMS")
        != registration["adaptive_maintenance_reference_checksum"]
    ):
        raise ValueError("sealed Adaptive Maintenance reference changed")
    reference_verification = verify_wagner_ph_maintenance_campaign(reference)
    if reference_verification != registration["adaptive_maintenance_reference_verification"]:
        raise ValueError("Adaptive Maintenance reference verification differs")
    source = Path(registration["source_burnin"])
    if sha256_file(source / "SHA256SUMS") != registration["source_burnin_checksum"]:
        raise ValueError("sealed repair-ratchet source changed")
    nested = {
        "evolution": verify_repair_ratchet_evolution(directory / "development" / "evolution"),
        "audit": verify_repair_ratchet_audit(directory / "development" / "audit"),
        "pedigree": verify_repair_ratchet_pedigree(directory / "development" / "pedigree"),
    }
    _payload_digest(analysis, "analysis_digest")
    if (
        manifest["analysis_digest"] != analysis["analysis_digest"]
        or nomination["analysis_digest"] != analysis["analysis_digest"]
        or nomination["candidate"] != analysis["nomination"]["candidate"]
        or nomination["confirmation_authorized"]
        or not nomination["confirmation_seed_generated_zero_tasks"]
    ):
        raise ValueError("repair-ratchet analysis or confirmation lock differs")
    checksum_fields = {
        "evolution_checksum": directory / "development" / "evolution" / "SHA256SUMS",
        "audit_checksum": directory / "development" / "audit" / "SHA256SUMS",
        "pedigree_checksum": directory / "development" / "pedigree" / "SHA256SUMS",
    }
    if any(manifest[field] != sha256_file(path) for field, path in checksum_fields.items()):
        raise ValueError("repair-ratchet nested checksum reference differs")
    expected_reservations = dict(zip(STAGES, spec.stage_reservations_seconds))
    if any(
        ledger["stages"][stage]["status"] != "completed"
        or ledger["stages"][stage]["reservation_seconds"] != expected_reservations[stage]
        for stage in STAGES
    ):
        raise ValueError("repair-ratchet resource ledger is incomplete")
    if (
        manifest["cumulative_wall_seconds"] > spec.hard_wall_seconds
        or manifest["workers_used"] > spec.maximum_workers
        or not manifest["cpu_only"]
        or not registration["cpu_only"]
    ):
        raise ValueError("repair-ratchet exceeded its resource boundary")
    return {
        "verified": True,
        "checksums": len(checksums),
        "development_populations": manifest["development_populations"],
        "candidate": analysis["nomination"]["candidate"],
        "nested": nested,
    }


def wagner_ph_repair_ratchet_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    if (directory / "SHA256SUMS").is_file():
        try:
            verification = verify_wagner_ph_repair_ratchet_campaign(directory)
        except Exception as error:
            return {"status": "sealed-invalid", "output": str(directory), "error": str(error)}
        manifest = read_json(directory / "campaign-manifest.json")
        return {
            "status": "complete",
            "output": str(directory),
            "elapsed_seconds": manifest["elapsed_seconds"],
            "candidate": manifest["nomination"]["candidate"],
            "verification": verification,
        }
    result: dict[str, Any] = {"status": "incomplete", "output": str(directory)}
    for name in ("progress.json", "resource-ledger.json", "registration.json"):
        if (directory / name).is_file():
            result[name.removesuffix(".json").replace("-", "_")] = read_json(directory / name)
    progress_paths = {
        "evolution": directory / "development" / "evolution" / "progress.json",
        "audit": directory / "development" / "audit" / "progress.json",
        "pedigree": directory / "development" / "pedigree" / "progress.json",
    }
    result["stage_progress"] = {
        name: read_json(path) for name, path in progress_paths.items() if path.is_file()
    }
    return result


__all__ = (
    "run_wagner_ph_repair_ratchet_campaign",
    "verify_wagner_ph_repair_ratchet_campaign",
    "wagner_ph_repair_ratchet_status",
    "replay_repair_ratchet_population",
)
