"""Gated orchestration for Wagner PH Adaptive Maintenance v1."""

from __future__ import annotations

import os
import time
from dataclasses import replace
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
from .wagner_ph_architecture_campaign import verify_wagner_ph_architecture_campaign
from .wagner_ph_cooption_evolution import run_cooption_evolution, verify_cooption_evolution
from .wagner_ph_maintenance_analysis import analyze_maintenance_phase, render_report
from .wagner_ph_maintenance_config import (
    MAINTENANCE_FORMAT,
    MaintenanceSpec,
    arm_settings,
    maintenance_spec,
    matched_ecology_control,
    matched_individual_control,
)
from .wagner_ph_maintenance_diagnosis import (
    run_maintenance_diagnosis,
    verify_maintenance_diagnosis,
)
from .wagner_ph_maintenance_evidence import (
    replay_maintenance_pedigree,
    run_maintenance_audit,
    run_maintenance_pedigree,
    verify_maintenance_audit,
    verify_maintenance_pedigree,
)
from .wagner_ph_maintenance_evolution import (
    replay_maintenance_population,
    run_maintenance_evolution,
    verify_maintenance_evolution,
)


DEVELOPMENT_STAGES = (
    "sealed-parent-diagnosis",
    "development-evolution",
    "development-evidence",
    "development-analysis-sealing",
)
CONFIRMATION_STAGES = (
    "fresh-burnin",
    "confirmation-evolution",
    "confirmation-evidence",
    "confirmation-analysis-sealing",
)
CONFIRMATION_FORMAT = f"{MAINTENANCE_FORMAT}-confirmation"


def _implementation_digest() -> str:
    root = Path(__file__).resolve().parents[2]
    names = (
        "WAGNER_PH_ADAPTIVE_MAINTENANCE_V1_PROTOCOL.md",
        "src/gre_sim/wagner.py",
        "src/gre_sim/wagner_ph_cooption_experiment.py",
        "src/gre_sim/wagner_ph_cooption_evolution.py",
        "src/gre_sim/wagner_ph_maintenance_config.py",
        "src/gre_sim/wagner_ph_maintenance_genome.py",
        "src/gre_sim/wagner_ph_maintenance_diagnosis.py",
        "src/gre_sim/wagner_ph_maintenance_evolution.py",
        "src/gre_sim/wagner_ph_maintenance_evidence.py",
        "src/gre_sim/wagner_ph_maintenance_analysis.py",
        "src/gre_sim/wagner_ph_maintenance_campaign.py",
        "src/gre_sim/wagner_ph_maintenance_cli.py",
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


def _jsons(directory: Path) -> list[dict[str, Any]]:
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def _deadline(started: float, seconds: int, environment: str) -> float:
    value = os.environ.get(environment)
    return float(value) if value is not None else started + seconds


def _prior_consumed(environment: str) -> float:
    value = float(os.environ.get(environment, "0"))
    if value < 0.0:
        raise ValueError("maintenance consumed wall time cannot be negative")
    return value


def _initial_ledger(
    format_name: str,
    hard: int,
    soft: int,
    stages: tuple[str, ...],
    reservations: tuple[int, ...],
    workers: int,
) -> dict[str, Any]:
    return {
        "format": f"{format_name}-resource-ledger",
        "hard_wall_seconds": hard,
        "soft_wall_seconds": soft,
        "unreserved_soft_contingency_seconds": soft - sum(reservations),
        "maximum_workers": 4,
        "workers_requested": workers,
        "cpu_only": True,
        "stages": {
            stage: {
                "reservation_seconds": reservation,
                "status": "pending",
                "attempts": 0,
                "elapsed_seconds": 0.0,
            }
            for stage, reservation in zip(stages, reservations)
        },
    }


def _stage_begin(
    destination: Path,
    deadline: float,
    stage: str,
    reservation: int,
) -> float:
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
            "format": f"{MAINTENANCE_FORMAT}-progress",
            "stage": stage,
            "elapsed_seconds": time.monotonic() - started,
            "updated_epoch": time.time(),
        },
    )


def confirmation_arms(candidates: tuple[str, ...]) -> tuple[str, ...]:
    if not candidates or len(candidates) != len(set(candidates)):
        raise ValueError("confirmation candidates must be nonempty and unique")
    values = ["individual_single_rho90", "mh_single_rho90"]

    def add(name: str | None) -> None:
        if name is not None and name not in values:
            values.append(name)

    for candidate in candidates:
        arm_settings(candidate)
        add(matched_individual_control(candidate))
        add(matched_ecology_control(candidate))
        add(candidate)
    return tuple(values)


def run_wagner_ph_maintenance_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = maintenance_spec(smoke=smoke)
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("adaptive-maintenance campaign permits one to four CPU workers")
    parent = parent.resolve()
    destination = destination.resolve()
    parent_verification = verify_wagner_ph_architecture_campaign(parent)
    source = parent / "confirmation" / "burnin"
    verify_cooption_evolution(source)
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_maintenance_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_mono = time.monotonic()
    started_epoch = time.time()
    prior = _prior_consumed("GRE_WAGNER_PH_MAINTENANCE_PRIOR_CONSUMED_SECONDS")
    deadline = _deadline(
        started_epoch,
        spec.soft_wall_seconds,
        "GRE_WAGNER_PH_MAINTENANCE_SOFT_DEADLINE_EPOCH",
    )
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": MAINTENANCE_FORMAT,
        "campaign_kind": "development",
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "kernel": spec.kernel().to_dict(),
        "kernel_digest": canonical_digest(spec.kernel().to_dict()),
        "implementation_digest": _implementation_digest(),
        "architecture_parent": str(parent),
        "architecture_parent_checksum": sha256_file(parent / "SHA256SUMS"),
        "architecture_parent_verification": parent_verification,
        "source_burnin": str(source),
        "source_burnin_checksum": sha256_file(source / "SHA256SUMS"),
        "confirmation_seed_commitment": canonical_digest(
            (spec.confirmation_seed, "adaptive-maintenance-confirmation-commitment")
        ),
        "confirmation_requires_separate_explicit_authorization": True,
        "workers_requested": workers,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing adaptive-maintenance registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    if not (destination / "resource-ledger.json").is_file():
        _atomic_json(
            destination / "resource-ledger.json",
            _initial_ledger(
                MAINTENANCE_FORMAT,
                spec.hard_wall_seconds,
                spec.soft_wall_seconds,
                DEVELOPMENT_STAGES,
                spec.stage_reservations_seconds,
                workers,
            ),
        )

    diagnosis = destination / "diagnosis"
    stage = DEVELOPMENT_STAGES[0]
    if not (diagnosis / "SHA256SUMS").is_file():
        stage_started = _stage_begin(
            destination, deadline, stage, spec.stage_reservations_seconds[0]
        )
        if progress:
            progress("starting sealed Architecture-v1 rescue/collapse diagnosis")
        run_maintenance_diagnosis(spec, parent, diagnosis)
        _stage_complete(destination, stage, stage_started)
    else:
        verify_maintenance_diagnosis(diagnosis)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    development = destination / "development"
    evolution = development / "evolution"
    stage = DEVELOPMENT_STAGES[1]
    if not (evolution / "SHA256SUMS").is_file():
        stage_started = _stage_begin(
            destination, deadline, stage, spec.stage_reservations_seconds[1]
        )
        if progress:
            progress("starting ten-arm performance-only adaptive-maintenance evolution")
        run_maintenance_evolution(spec, source, evolution, workers, progress)
        _stage_complete(destination, stage, stage_started)
    else:
        verify_maintenance_evolution(evolution)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    audit = development / "audit"
    pedigree = development / "pedigree"
    stage = DEVELOPMENT_STAGES[2]
    if not (audit / "SHA256SUMS").is_file() or not (pedigree / "SHA256SUMS").is_file():
        stage_started = _stage_begin(
            destination, deadline, stage, spec.stage_reservations_seconds[2]
        )
        if progress:
            progress("starting held-out F1/F4/F12 audits and four-step mutation pedigrees")
        run_maintenance_audit(spec, evolution, audit, workers, progress)
        run_maintenance_pedigree(spec, evolution, pedigree, workers, progress)
        _stage_complete(destination, stage, stage_started)
    else:
        verify_maintenance_audit(audit)
        verify_maintenance_pedigree(pedigree)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    analysis_path = development / "analysis.json"
    nomination_path = development / "nomination.json"
    stage = DEVELOPMENT_STAGES[3]
    stage_started = _stage_begin(
        destination, deadline, stage, spec.stage_reservations_seconds[3]
    )
    if not analysis_path.is_file() or not nomination_path.is_file():
        analysis = analyze_maintenance_phase(
            _jsons(audit / "populations"),
            read_json(pedigree / "analysis.json"),
            spec,
            "development",
        )
        _atomic_json(analysis_path, analysis)
        candidates = tuple(analysis["nomination"]["candidates"])
        nomination = {
            **analysis["nomination"],
            "confirmation_arms": list(confirmation_arms(candidates)) if candidates else [],
            "development_analysis_digest": analysis["analysis_digest"],
            "confirmation_seed_generated_zero_tasks": True,
            "confirmation_authorized": False,
        }
        nomination["nomination_digest"] = canonical_digest(nomination)
        _atomic_json(nomination_path, nomination)
    else:
        analysis = read_json(analysis_path)
        nomination = read_json(nomination_path)
        _payload_digest(analysis, "analysis_digest")
        _payload_digest(nomination, "nomination_digest")
    diagnosis_analysis = read_json(diagnosis / "analysis.json")
    combined = {
        "format": MAINTENANCE_FORMAT,
        "development_analysis": analysis,
        "development_analysis_digest": analysis["analysis_digest"],
        "diagnosis_analysis": diagnosis_analysis,
        "diagnosis_analysis_digest": diagnosis_analysis["analysis_digest"],
        "nomination": nomination,
        "fresh_confirmation_generated": False,
        "confirmation_requires_separate_explicit_authorization": True,
        "claim_boundary": analysis["claim_boundary"],
    }
    combined["analysis_digest"] = canonical_digest(combined)
    _atomic_json(destination / "analysis.json", combined)
    _atomic_text(destination / "report.md", render_report(analysis, diagnosis_analysis))
    _stage_complete(destination, stage, stage_started)
    _progress(destination, "sealed-development", started_mono)
    elapsed = time.monotonic() - started_mono
    manifest = {
        "format": MAINTENANCE_FORMAT,
        "campaign_kind": "development",
        "protocol_digest": protocol_digest,
        "implementation_digest": registration["implementation_digest"],
        "diagnosis_checksum": sha256_file(diagnosis / "SHA256SUMS"),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "audit_checksum": sha256_file(audit / "SHA256SUMS"),
        "pedigree_checksum": sha256_file(pedigree / "SHA256SUMS"),
        "analysis_digest": combined["analysis_digest"],
        "nomination_digest": nomination["nomination_digest"],
        "development_populations": len(spec.arms) * spec.task_count,
        "workers_used": workers,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior,
        "cumulative_wall_seconds": prior + elapsed,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_eight_hour_boundary": prior + elapsed <= spec.hard_wall_seconds,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    write_checksums(destination)
    verify_wagner_ph_maintenance_campaign(destination)
    if progress:
        progress("sealed and independently verified Adaptive Maintenance development")
    return destination


def verify_wagner_ph_maintenance_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    nomination = read_json(directory / "development" / "nomination.json")
    ledger = read_json(directory / "resource-ledger.json")
    if registration.get("format") != MAINTENANCE_FORMAT or manifest.get("format") != MAINTENANCE_FORMAT:
        raise ValueError("adaptive-maintenance campaign format mismatch")
    spec = MaintenanceSpec.from_dict(registration["protocol"])
    if (
        canonical_digest(spec.to_dict()) != registration["protocol_digest"]
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or canonical_digest(registration["kernel"]) != registration["kernel_digest"]
    ):
        raise ValueError("adaptive-maintenance protocol mismatch")
    if registration["implementation_digest"] != _implementation_digest() or manifest["implementation_digest"] != registration["implementation_digest"]:
        raise ValueError("adaptive-maintenance implementation changed after registration")
    parent = Path(registration["architecture_parent"])
    if sha256_file(parent / "SHA256SUMS") != registration["architecture_parent_checksum"]:
        raise ValueError("sealed Architecture-v1 parent changed")
    verify_wagner_ph_architecture_campaign(parent)
    if sha256_file(Path(registration["source_burnin"]) / "SHA256SUMS") != registration["source_burnin_checksum"]:
        raise ValueError("sealed source burnin changed")
    nested = {
        "diagnosis": verify_maintenance_diagnosis(directory / "diagnosis"),
        "evolution": verify_maintenance_evolution(directory / "development" / "evolution"),
        "audit": verify_maintenance_audit(directory / "development" / "audit"),
        "pedigree": verify_maintenance_pedigree(directory / "development" / "pedigree"),
    }
    development = read_json(directory / "development" / "analysis.json")
    for value, field in (
        (development, "analysis_digest"),
        (nomination, "nomination_digest"),
        (analysis, "analysis_digest"),
    ):
        _payload_digest(value, field)
    if (
        analysis["fresh_confirmation_generated"]
        or nomination["confirmation_authorized"]
        or analysis["development_analysis_digest"] != development["analysis_digest"]
        or analysis["nomination"]["nomination_digest"] != nomination["nomination_digest"]
        or manifest["analysis_digest"] != analysis["analysis_digest"]
        or manifest["nomination_digest"] != nomination["nomination_digest"]
    ):
        raise ValueError("adaptive-maintenance development authorization boundary differs")
    checksum_fields = {
        "diagnosis_checksum": directory / "diagnosis" / "SHA256SUMS",
        "evolution_checksum": directory / "development" / "evolution" / "SHA256SUMS",
        "audit_checksum": directory / "development" / "audit" / "SHA256SUMS",
        "pedigree_checksum": directory / "development" / "pedigree" / "SHA256SUMS",
    }
    if any(manifest[field] != sha256_file(path) for field, path in checksum_fields.items()):
        raise ValueError("adaptive-maintenance nested checksum reference differs")
    expected = dict(zip(DEVELOPMENT_STAGES, spec.stage_reservations_seconds))
    if any(
        ledger["stages"][stage]["status"] != "completed"
        or ledger["stages"][stage]["reservation_seconds"] != reservation
        for stage, reservation in expected.items()
    ):
        raise ValueError("adaptive-maintenance resource ledger is incomplete")
    if manifest["development_populations"] != len(spec.arms) * spec.task_count:
        raise ValueError("adaptive-maintenance population count differs")
    return {
        "verified": True,
        "campaign_kind": "development",
        "candidates": nomination["candidates"],
        "checksums": len(checksums),
        "nested": nested,
    }


def run_wagner_ph_maintenance_confirmation(
    development: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    authorize_confirmation: bool = False,
) -> Path:
    if not authorize_confirmation:
        raise PermissionError("fresh confirmation requires explicit --authorize-confirmation")
    development = development.resolve()
    destination = destination.resolve()
    verify_wagner_ph_maintenance_campaign(development)
    development_registration = read_json(development / "registration.json")
    spec = MaintenanceSpec.from_dict(development_registration["protocol"])
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("adaptive-maintenance confirmation permits one to four CPU workers")
    nomination = read_json(development / "development" / "nomination.json")
    candidates = tuple(nomination["candidates"])
    if not candidates:
        raise ValueError("no development mechanism passed all gates; confirmation remains locked")
    arms = confirmation_arms(candidates)
    if tuple(nomination["confirmation_arms"]) != arms:
        raise ValueError("confirmation arms differ from the frozen nomination")
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_maintenance_confirmation(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_mono = time.monotonic()
    started_epoch = time.time()
    prior = _prior_consumed("GRE_WAGNER_PH_MAINTENANCE_CONFIRM_PRIOR_CONSUMED_SECONDS")
    deadline = _deadline(
        started_epoch,
        spec.confirmation_soft_wall_seconds,
        "GRE_WAGNER_PH_MAINTENANCE_CONFIRM_SOFT_DEADLINE_EPOCH",
    )
    payload = {
        "spec": spec.to_dict(),
        "development_checksum": sha256_file(development / "SHA256SUMS"),
        "nomination_digest": nomination["nomination_digest"],
        "candidates": list(candidates),
        "selected_arms": list(arms),
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": CONFIRMATION_FORMAT,
        "campaign_kind": "explicitly-authorized-confirmation",
        "protocol_digest": protocol_digest,
        **payload,
        "development": str(development),
        "implementation_digest": _implementation_digest(),
        "explicit_confirmation_authorization": True,
        "workers_requested": workers,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing adaptive-maintenance confirmation registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    if not (destination / "resource-ledger.json").is_file():
        _atomic_json(
            destination / "resource-ledger.json",
            _initial_ledger(
                CONFIRMATION_FORMAT,
                spec.confirmation_hard_wall_seconds,
                spec.confirmation_soft_wall_seconds,
                CONFIRMATION_STAGES,
                spec.confirmation_stage_reservations_seconds,
                workers,
            ),
        )

    burnin = destination / "burnin"
    stage = CONFIRMATION_STAGES[0]
    if not (burnin / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, deadline, stage, spec.confirmation_stage_reservations_seconds[0])
        kernel = replace(
            spec.kernel(confirmation=True),
            cohort_id=spec.cohort_id + "-fresh-confirmation-burnin",
            generations=spec.confirmation_burnin_generations,
        )
        run_cooption_evolution(
            kernel,
            burnin,
            workers,
            progress,
            treatments=("direct_independent",),
            task_count=spec.confirmation_task_count,
            master_seed=spec.confirmation_seed,
            predictive_persistence=0.9,
        )
        _stage_complete(destination, stage, stage_started)
    else:
        verify_cooption_evolution(burnin)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    evolution = destination / "evolution"
    stage = CONFIRMATION_STAGES[1]
    if not (evolution / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, deadline, stage, spec.confirmation_stage_reservations_seconds[1])
        run_maintenance_evolution(
            spec,
            burnin,
            evolution,
            workers,
            progress,
            phase="confirmation",
            selected_arms=arms,
        )
        _stage_complete(destination, stage, stage_started)
    else:
        verify_maintenance_evolution(evolution)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    audit = destination / "audit"
    pedigree = destination / "pedigree"
    stage = CONFIRMATION_STAGES[2]
    if not (audit / "SHA256SUMS").is_file() or not (pedigree / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, deadline, stage, spec.confirmation_stage_reservations_seconds[2])
        run_maintenance_audit(spec, evolution, audit, workers, progress)
        run_maintenance_pedigree(spec, evolution, pedigree, workers, progress)
        _stage_complete(destination, stage, stage_started)
    else:
        verify_maintenance_audit(audit)
        verify_maintenance_pedigree(pedigree)
        _recover(destination, stage)
    _progress(destination, stage, started_mono)

    stage = CONFIRMATION_STAGES[3]
    stage_started = _stage_begin(destination, deadline, stage, spec.confirmation_stage_reservations_seconds[3])
    analysis = analyze_maintenance_phase(
        _jsons(audit / "populations"),
        read_json(pedigree / "analysis.json"),
        spec,
        "confirmation",
        forced_candidates=candidates,
    )
    _atomic_json(destination / "analysis.json", analysis)
    diagnosis = read_json(development / "diagnosis" / "analysis.json")
    development_analysis = read_json(development / "development" / "analysis.json")
    _atomic_text(destination / "report.md", render_report(development_analysis, diagnosis, analysis))
    _stage_complete(destination, stage, stage_started)
    _progress(destination, "sealed-confirmation", started_mono)
    elapsed = time.monotonic() - started_mono
    manifest = {
        "format": CONFIRMATION_FORMAT,
        "protocol_digest": protocol_digest,
        "implementation_digest": registration["implementation_digest"],
        "burnin_checksum": sha256_file(burnin / "SHA256SUMS"),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "audit_checksum": sha256_file(audit / "SHA256SUMS"),
        "pedigree_checksum": sha256_file(pedigree / "SHA256SUMS"),
        "analysis_digest": analysis["analysis_digest"],
        "confirmation_populations": len(arms) * spec.confirmation_task_count,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior,
        "cumulative_wall_seconds": prior + elapsed,
        "hard_wall_seconds": spec.confirmation_hard_wall_seconds,
        "completed_within_four_hour_boundary": prior + elapsed <= spec.confirmation_hard_wall_seconds,
        "workers_used": workers,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    write_checksums(destination)
    verify_wagner_ph_maintenance_confirmation(destination)
    if progress:
        progress("sealed and independently verified Adaptive Maintenance confirmation")
    return destination


def verify_wagner_ph_maintenance_confirmation(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != CONFIRMATION_FORMAT or manifest.get("format") != CONFIRMATION_FORMAT:
        raise ValueError("adaptive-maintenance confirmation format mismatch")
    spec = MaintenanceSpec.from_dict(registration["spec"])
    payload = {
        key: registration[key]
        for key in ("spec", "development_checksum", "nomination_digest", "candidates", "selected_arms")
    }
    if canonical_digest(payload) != registration["protocol_digest"] or manifest["protocol_digest"] != registration["protocol_digest"]:
        raise ValueError("adaptive-maintenance confirmation protocol mismatch")
    if registration["implementation_digest"] != _implementation_digest() or manifest["implementation_digest"] != registration["implementation_digest"]:
        raise ValueError("adaptive-maintenance confirmation implementation changed")
    development = Path(registration["development"])
    if sha256_file(development / "SHA256SUMS") != registration["development_checksum"]:
        raise ValueError("sealed development campaign changed")
    verify_wagner_ph_maintenance_campaign(development)
    nomination = read_json(development / "development" / "nomination.json")
    candidates = tuple(registration["candidates"])
    if nomination["nomination_digest"] != registration["nomination_digest"] or tuple(nomination["candidates"]) != candidates or confirmation_arms(candidates) != tuple(registration["selected_arms"]):
        raise ValueError("adaptive-maintenance confirmation nomination differs")
    nested = {
        "burnin": verify_cooption_evolution(directory / "burnin"),
        "evolution": verify_maintenance_evolution(directory / "evolution"),
        "audit": verify_maintenance_audit(directory / "audit"),
        "pedigree": verify_maintenance_pedigree(directory / "pedigree"),
    }
    _payload_digest(analysis, "analysis_digest")
    if tuple(analysis["nomination"]["candidates"]) != candidates or manifest["analysis_digest"] != analysis["analysis_digest"]:
        raise ValueError("adaptive-maintenance confirmation analysis differs")
    checksum_fields = {
        "burnin_checksum": directory / "burnin" / "SHA256SUMS",
        "evolution_checksum": directory / "evolution" / "SHA256SUMS",
        "audit_checksum": directory / "audit" / "SHA256SUMS",
        "pedigree_checksum": directory / "pedigree" / "SHA256SUMS",
    }
    if any(manifest[field] != sha256_file(path) for field, path in checksum_fields.items()):
        raise ValueError("adaptive-maintenance confirmation nested checksum differs")
    ledger = read_json(directory / "resource-ledger.json")
    expected = dict(zip(CONFIRMATION_STAGES, spec.confirmation_stage_reservations_seconds))
    if any(
        ledger["stages"][stage]["status"] != "completed"
        or ledger["stages"][stage]["reservation_seconds"] != reservation
        for stage, reservation in expected.items()
    ):
        raise ValueError("adaptive-maintenance confirmation ledger is incomplete")
    return {
        "verified": True,
        "campaign_kind": "confirmation",
        "candidates": list(candidates),
        "all_candidates_pass": analysis["confirmation"]["all_candidates_pass"],
        "checksums": len(checksums),
        "nested": nested,
    }


def wagner_ph_maintenance_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    registration_path = directory / "registration.json"
    kind = "development"
    if registration_path.is_file() and read_json(registration_path).get("format") == CONFIRMATION_FORMAT:
        kind = "confirmation"
    if (directory / "SHA256SUMS").is_file():
        try:
            verification = (
                verify_wagner_ph_maintenance_confirmation(directory)
                if kind == "confirmation"
                else verify_wagner_ph_maintenance_campaign(directory)
            )
        except Exception as error:
            return {"status": "sealed-invalid", "output": str(directory), "error": str(error)}
        analysis = read_json(directory / "analysis.json")
        manifest = read_json(directory / "campaign-manifest.json")
        return {
            "status": "complete",
            "campaign_kind": kind,
            "output": str(directory),
            "elapsed_seconds": manifest["elapsed_seconds"],
            "candidates": (
                analysis["nomination"]["candidates"]
                if kind == "confirmation"
                else analysis["nomination"]["candidates"]
            ),
            "confirmation": analysis.get("confirmation"),
            "verification": verification,
        }
    result: dict[str, Any] = {"status": "incomplete", "campaign_kind": kind, "output": str(directory)}
    for name in ("progress.json", "resource-ledger.json", "registration.json"):
        if (directory / name).is_file():
            result[name.removesuffix(".json").replace("-", "_")] = read_json(directory / name)
    base = directory / "development" if kind == "development" else directory
    locations = {
        "evolution": base / "evolution" / "populations",
        "audit": base / "audit" / "populations",
        "pedigree": base / "pedigree" / "populations",
    }
    if kind == "confirmation":
        locations["burnin"] = directory / "burnin" / "populations"
    result["completed_shards"] = {
        name: len([path for path in location.glob("*.json") if not path.name.endswith(".checkpoint.json")])
        for name, location in locations.items()
    }
    progress_values = {}
    for name, location in locations.items():
        path = location.parent / "progress.json"
        if path.is_file():
            progress_values[name] = read_json(path)
    result["stage_progress"] = progress_values
    return result


def replay_wagner_ph_maintenance(
    directory: Path,
    population_id: str,
    *,
    pedigree: bool = False,
    root_index: int = 0,
    lineage_index: int = 0,
    distance: int = 1,
    mode: str = "natural",
) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    base = directory / "development" if registration.get("format") == MAINTENANCE_FORMAT else directory
    if pedigree:
        return replay_maintenance_pedigree(
            base / "pedigree", population_id, root_index, lineage_index, distance, mode
        )
    return replay_maintenance_population(base / "evolution", population_id)


__all__ = (
    "CONFIRMATION_STAGES",
    "DEVELOPMENT_STAGES",
    "confirmation_arms",
    "replay_wagner_ph_maintenance",
    "run_wagner_ph_maintenance_campaign",
    "run_wagner_ph_maintenance_confirmation",
    "verify_wagner_ph_maintenance_campaign",
    "verify_wagner_ph_maintenance_confirmation",
    "wagner_ph_maintenance_status",
)
