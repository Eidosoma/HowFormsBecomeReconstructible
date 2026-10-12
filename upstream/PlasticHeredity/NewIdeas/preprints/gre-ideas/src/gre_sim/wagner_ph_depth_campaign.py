"""Six-hour orchestration for Wagner PH Interpreter-Depth v1."""

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
from .wagner_ph_depth_analysis import analyze_depth_phase, render_depth_report
from .wagner_ph_depth_atlas import (
    replay_atlas_cell,
    run_interpreter_atlas,
    verify_interpreter_atlas,
)
from .wagner_ph_depth_audit import run_depth_audit, verify_depth_audit
from .wagner_ph_depth_config import (
    DEPTH_CAMPAIGN_FORMAT,
    InterpreterDepthSpec,
    interpreter_depth_spec,
)
from .wagner_ph_depth_evolution import (
    replay_depth_population,
    run_confirmation_burnin,
    run_depth_evolution,
    verify_depth_evolution,
)
from .wagner_ph_depth_pedigree import (
    replay_pedigree_event,
    run_depth_pedigree,
    verify_depth_pedigree,
)
from .wagner_ph_robustness_campaign import verify_wagner_ph_robustness_campaign


STAGES = (
    "interface-atlas",
    "development-evolution",
    "development-audit-pedigree",
    "nomination",
    "confirmation-evolution",
    "confirmation-audit-pedigree",
    "sealing",
)


def _implementation_digest() -> str:
    root = Path(__file__).resolve().parents[2]
    relative_files = (
        "WAGNER_PH_INTERPRETER_DEPTH_V1_PROTOCOL.md",
        "src/gre_sim/wagner.py",
        "src/gre_sim/wagner_ph_cooption_experiment.py",
        "src/gre_sim/wagner_ph_cooption_evolution.py",
        "src/gre_sim/wagner_ph_depth_config.py",
        "src/gre_sim/wagner_ph_depth_mechanisms.py",
        "src/gre_sim/wagner_ph_depth_atlas.py",
        "src/gre_sim/wagner_ph_depth_evolution.py",
        "src/gre_sim/wagner_ph_depth_audit.py",
        "src/gre_sim/wagner_ph_depth_pedigree.py",
        "src/gre_sim/wagner_ph_depth_analysis.py",
        "src/gre_sim/wagner_ph_depth_campaign.py",
    )
    return canonical_digest({name: sha256_file(root / name) for name in relative_files})


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


def _soft_deadline(started: float, spec: InterpreterDepthSpec) -> float:
    value = os.environ.get("GRE_WAGNER_PH_DEPTH_SOFT_DEADLINE_EPOCH")
    if value is None:
        return started + spec.soft_wall_seconds
    try:
        return float(value)
    except ValueError as error:
        raise ValueError("invalid interpreter-depth soft deadline") from error


def _prior_consumed_seconds() -> float:
    value = os.environ.get("GRE_WAGNER_PH_DEPTH_PRIOR_CONSUMED_SECONDS", "0")
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError("invalid interpreter-depth consumed-time ledger") from error
    if result < 0.0:
        raise ValueError("interpreter-depth consumed time cannot be negative")
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
    _atomic_json(destination / "progress.json", {
        "format": "gre-wagner-ph-interpreter-depth-progress-v1",
        "stage": stage,
        "detail": detail,
        "completed_units": completed,
        "total_units": total,
        "elapsed_seconds": elapsed,
        "units_per_second": rate,
        "eta_seconds": (total - completed) / rate if rate else None,
    })


def _initial_ledger(spec: InterpreterDepthSpec) -> dict[str, Any]:
    return {
        "format": "gre-wagner-ph-interpreter-depth-resource-ledger-v1",
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


def _stage_begin(destination: Path, spec: InterpreterDepthSpec, deadline: float, stage: str) -> float:
    reservation = spec.stage_reservations_seconds[STAGES.index(stage)]
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
    entry["elapsed_seconds"] = float(entry.get("elapsed_seconds", 0.0)) + time.monotonic() - started
    entry["status"] = "completed"
    entry["last_completed_epoch"] = time.time()
    _atomic_json(path, ledger)


def _stage_skip(destination: Path, stage: str, reason: str) -> None:
    path = destination / "resource-ledger.json"
    ledger = read_json(path)
    entry = ledger["stages"][stage]
    entry["status"] = "skipped"
    entry["skip_reason"] = reason
    entry["elapsed_seconds"] = 0.0
    _atomic_json(path, ledger)


def _recover_stage(destination: Path, stage: str, *, skipped: bool = False) -> None:
    path = destination / "resource-ledger.json"
    ledger = read_json(path)
    entry = ledger["stages"][stage]
    expected = "skipped" if skipped else "completed"
    if entry["status"] != expected:
        entry["status"] = expected
        entry["recovered_from_sealed_stage"] = True
        _atomic_json(path, ledger)


def _load_jsons(path: Path) -> list[dict[str, Any]]:
    return [read_json(value) for value in sorted(path.glob("*.json"))]


def _analyze_development(destination: Path, spec: InterpreterDepthSpec) -> dict[str, Any]:
    audit_rows = _load_jsons(destination / "development" / "audit" / "populations")
    pedigree = read_json(destination / "development" / "pedigree" / "analysis.json")
    pedigree_shards = _load_jsons(destination / "development" / "pedigree" / "populations")
    atlas_shards = _load_jsons(destination / "atlas" / "tasks")
    return analyze_depth_phase(
        audit_rows,
        pedigree,
        spec,
        "development",
        pedigree_shards=pedigree_shards,
        atlas_shards=atlas_shards,
    )


def run_wagner_ph_depth_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = interpreter_depth_spec(smoke=smoke)
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("interpreter-depth campaign permits one to four CPU workers")
    parent = parent.resolve()
    parent_verification = verify_wagner_ph_robustness_campaign(parent)
    parent_registration = read_json(parent / "registration.json")
    expected_parent = spec.parent_cohort_id + ("-smoke" if smoke else "")
    if parent_registration["protocol"]["cohort_id"] != expected_parent:
        raise ValueError("interpreter-depth parent is not the matching sealed robustness cohort")
    destination = destination.resolve()
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_depth_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_monotonic = time.monotonic()
    started_epoch = time.time()
    deadline = _soft_deadline(started_epoch, spec)
    prior_consumed = _prior_consumed_seconds()
    kernel = spec.kernel()
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": DEPTH_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "simulation_kernel": kernel.to_dict(),
        "simulation_kernel_digest": canonical_digest(kernel.to_dict()),
        "implementation_digest": _implementation_digest(),
        "robustness_parent": str(parent),
        "robustness_parent_checksum": sha256_file(parent / "SHA256SUMS"),
        "robustness_parent_verification": parent_verification,
        "confirmation_is_inaccessible_until_a_sealed_nomination_pass": True,
        "confirmation_seed_commitment": canonical_digest((spec.confirmation_seed, "commitment")),
        "cpu_only": True,
        "workers_requested": workers,
        "stage_reservations_seconds": dict(zip(STAGES, spec.stage_reservations_seconds)),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing interpreter-depth campaign registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    ledger_path = destination / "resource-ledger.json"
    if not ledger_path.is_file():
        _atomic_json(ledger_path, _initial_ledger(spec))

    atlas_dir = destination / "atlas"
    if not (atlas_dir / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, spec, deadline, "interface-atlas")
        if progress:
            progress("starting 100-edge causal interpreter atlas")
        run_interpreter_atlas(spec, parent, atlas_dir, workers, progress)
        _stage_complete(destination, "interface-atlas", stage_started)
    else:
        verify_interpreter_atlas(atlas_dir)
        _recover_stage(destination, "interface-atlas")
    _write_progress(destination, "interface-atlas", 1, 1, started_monotonic)

    development = destination / "development"
    evolution_dir = development / "evolution"
    if not (evolution_dir / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, spec, deadline, "development-evolution")
        if progress:
            progress("starting six-arm matched interpreter-depth evolution")
        run_depth_evolution(spec, parent / "evolution", evolution_dir, workers, progress)
        _stage_complete(destination, "development-evolution", stage_started)
    else:
        verify_depth_evolution(evolution_dir)
        _recover_stage(destination, "development-evolution")
    _write_progress(destination, "development-evolution", 1, 1, started_monotonic)

    audit_dir = development / "audit"
    pedigree_dir = development / "pedigree"
    if not (audit_dir / "SHA256SUMS").is_file() or not (pedigree_dir / "SHA256SUMS").is_file():
        stage_started = _stage_begin(destination, spec, deadline, "development-audit-pedigree")
        if progress:
            progress("starting held-out development audit and four-mutation pedigrees")
        run_depth_audit(spec, evolution_dir, audit_dir, workers, progress)
        run_depth_pedigree(spec, evolution_dir, pedigree_dir, workers, progress)
        _stage_complete(destination, "development-audit-pedigree", stage_started)
    else:
        verify_depth_audit(audit_dir)
        verify_depth_pedigree(pedigree_dir)
        _recover_stage(destination, "development-audit-pedigree")
    _write_progress(destination, "development-audit-pedigree", 1, 1, started_monotonic)

    development_analysis_path = development / "analysis.json"
    nomination_path = development / "nomination.json"
    if not development_analysis_path.is_file() or not nomination_path.is_file():
        stage_started = _stage_begin(destination, spec, deadline, "nomination")
        development_analysis = _analyze_development(destination, spec)
        _atomic_json(development_analysis_path, development_analysis)
        nomination = {
            **development_analysis["nomination"],
            "development_analysis_digest": development_analysis["analysis_digest"],
            "confirmation_seed_generated_no_task_environment_mutation_or_assay_draw_before_nomination": True,
        }
        nomination["nomination_digest"] = canonical_digest(nomination)
        _atomic_json(nomination_path, nomination)
        _stage_complete(destination, "nomination", stage_started)
    else:
        development_analysis = read_json(development_analysis_path)
        _payload_digest(development_analysis, "analysis_digest")
        nomination = read_json(nomination_path)
        _payload_digest(nomination, "nomination_digest")
        _recover_stage(destination, "nomination")
    _write_progress(destination, "nomination", 1, 1, started_monotonic)

    confirmation_analysis: dict[str, Any] | None = None
    confirmation = destination / "confirmation"
    if nomination["nominated"]:
        candidate = str(nomination["candidate"])
        control = str(nomination["matched_control"])
        burnin_dir = confirmation / "burnin"
        confirmation_evolution = confirmation / "evolution"
        if not (confirmation_evolution / "SHA256SUMS").is_file():
            _require_budget(
                deadline,
                sum(spec.stage_reservations_seconds[4:]),
                "complete gated confirmation and sealing path",
            )
            stage_started = _stage_begin(destination, spec, deadline, "confirmation-evolution")
            if progress:
                progress(f"development nominated {candidate}; generating fresh tasks and ancestors")
            run_confirmation_burnin(spec, burnin_dir, workers, progress)
            run_depth_evolution(
                spec,
                burnin_dir,
                confirmation_evolution,
                workers,
                progress,
                phase="confirmation",
                selected_arms=(control, candidate),
            )
            _stage_complete(destination, "confirmation-evolution", stage_started)
        else:
            verify_cooption_evolution(burnin_dir)
            verify_depth_evolution(confirmation_evolution)
            _recover_stage(destination, "confirmation-evolution")
        confirmation_audit = confirmation / "audit"
        confirmation_pedigree = confirmation / "pedigree"
        confirmation_analysis_path = confirmation / "analysis.json"
        if (
            not (confirmation_audit / "SHA256SUMS").is_file()
            or not (confirmation_pedigree / "SHA256SUMS").is_file()
            or not confirmation_analysis_path.is_file()
        ):
            stage_started = _stage_begin(destination, spec, deadline, "confirmation-audit-pedigree")
            if progress:
                progress("starting untouched fresh-task causal audit and mutation pedigree")
            run_depth_audit(spec, confirmation_evolution, confirmation_audit, workers, progress)
            run_depth_pedigree(spec, confirmation_evolution, confirmation_pedigree, workers, progress)
            confirmation_analysis = analyze_depth_phase(
                _load_jsons(confirmation_audit / "populations"),
                read_json(confirmation_pedigree / "analysis.json"),
                spec,
                "confirmation",
                forced_candidate=candidate,
            )
            _atomic_json(confirmation_analysis_path, confirmation_analysis)
            _stage_complete(destination, "confirmation-audit-pedigree", stage_started)
        else:
            verify_depth_audit(confirmation_audit)
            verify_depth_pedigree(confirmation_pedigree)
            confirmation_analysis = read_json(confirmation_analysis_path)
            _payload_digest(confirmation_analysis, "analysis_digest")
            _recover_stage(destination, "confirmation-audit-pedigree")
    else:
        _stage_skip(destination, "confirmation-evolution", "development produced no eligible nominee")
        _stage_skip(destination, "confirmation-audit-pedigree", "development produced no eligible nominee")
    _write_progress(destination, "confirmation", 1, 1, started_monotonic)

    stage_started = _stage_begin(destination, spec, deadline, "sealing")
    combined = {
        "format": DEPTH_CAMPAIGN_FORMAT,
        "development_analysis": development_analysis,
        "development_analysis_digest": development_analysis["analysis_digest"],
        "nomination": nomination,
        "fresh_confirmation_generated": bool(nomination["nominated"]),
        "fresh_confirmation_task_count": spec.confirmation_task_count if nomination["nominated"] else 0,
        "confirmation_analysis": confirmation_analysis,
        "confirmation_passes": confirmation_analysis["confirmation_passes"] if confirmation_analysis else None,
        "claim_boundary": development_analysis["claim_boundary"],
    }
    combined["analysis_digest"] = canonical_digest(combined)
    _atomic_json(destination / "analysis.json", combined)
    elapsed = time.monotonic() - started_monotonic
    cumulative = prior_consumed + elapsed
    manifest = {
        "format": DEPTH_CAMPAIGN_FORMAT,
        "protocol_digest": protocol_digest,
        "simulation_kernel_digest": registration["simulation_kernel_digest"],
        "implementation_digest": registration["implementation_digest"],
        "robustness_parent_checksum": registration["robustness_parent_checksum"],
        "atlas_checksum": sha256_file(atlas_dir / "SHA256SUMS"),
        "development_evolution_checksum": sha256_file(evolution_dir / "SHA256SUMS"),
        "development_audit_checksum": sha256_file(audit_dir / "SHA256SUMS"),
        "development_pedigree_checksum": sha256_file(pedigree_dir / "SHA256SUMS"),
        "nomination_digest": nomination["nomination_digest"],
        "confirmation_generated": bool(nomination["nominated"]),
        "confirmation_checksums": ({
            "burnin": sha256_file(confirmation / "burnin" / "SHA256SUMS"),
            "evolution": sha256_file(confirmation / "evolution" / "SHA256SUMS"),
            "audit": sha256_file(confirmation / "audit" / "SHA256SUMS"),
            "pedigree": sha256_file(confirmation / "pedigree" / "SHA256SUMS"),
        } if nomination["nominated"] else None),
        "analysis_digest": combined["analysis_digest"],
        "development_populations": spec.development_population_count,
        "atlas_perturbations": (
            spec.task_count * spec.atlas_roots_per_task * spec.atlas_edge_limit
            * len(spec.atlas_perturbations)
        ),
        "maximum_workers": workers,
        "cpu_only": True,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior_consumed,
        "cumulative_wall_seconds": cumulative,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_six_hour_boundary": cumulative <= spec.hard_wall_seconds,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    (destination / "report.md").write_text(
        render_depth_report(development_analysis, confirmation_analysis), encoding="utf-8"
    )
    _stage_complete(destination, "sealing", stage_started)
    _write_progress(destination, "sealed", 1, 1, started_monotonic)
    write_checksums(destination)
    verify_wagner_ph_depth_campaign(destination)
    if progress:
        progress("sealed and independently verified Interpreter-Depth v1")
    return destination


def verify_wagner_ph_depth_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    nomination = read_json(directory / "development" / "nomination.json")
    ledger = read_json(directory / "resource-ledger.json")
    if registration.get("format") != DEPTH_CAMPAIGN_FORMAT or manifest.get("format") != DEPTH_CAMPAIGN_FORMAT:
        raise ValueError("interpreter-depth campaign format mismatch")
    spec = InterpreterDepthSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("interpreter-depth campaign protocol digest mismatch")
    if registration["implementation_digest"] != _implementation_digest() or manifest["implementation_digest"] != registration["implementation_digest"]:
        raise ValueError("interpreter-depth implementation changed after campaign registration")
    parent = Path(registration["robustness_parent"])
    if sha256_file(parent / "SHA256SUMS") != registration["robustness_parent_checksum"]:
        raise ValueError("sealed robustness parent changed after interpreter-depth campaign")
    nested: dict[str, Any] = {
        "atlas": verify_interpreter_atlas(directory / "atlas"),
        "development_evolution": verify_depth_evolution(directory / "development" / "evolution"),
        "development_audit": verify_depth_audit(directory / "development" / "audit"),
        "development_pedigree": verify_depth_pedigree(directory / "development" / "pedigree"),
    }
    _payload_digest(read_json(directory / "development" / "analysis.json"), "analysis_digest")
    _payload_digest(nomination, "nomination_digest")
    _payload_digest(analysis, "analysis_digest")
    if manifest["analysis_digest"] != analysis["analysis_digest"] or manifest["nomination_digest"] != nomination["nomination_digest"]:
        raise ValueError("interpreter-depth analysis or nomination reference mismatch")
    if bool(manifest["confirmation_generated"]) != bool(nomination["nominated"]):
        raise ValueError("interpreter-depth confirmation accounting mismatch")
    if nomination["nominated"]:
        nested.update({
            "confirmation_burnin": verify_cooption_evolution(directory / "confirmation" / "burnin"),
            "confirmation_evolution": verify_depth_evolution(directory / "confirmation" / "evolution"),
            "confirmation_audit": verify_depth_audit(directory / "confirmation" / "audit"),
            "confirmation_pedigree": verify_depth_pedigree(directory / "confirmation" / "pedigree"),
        })
        _payload_digest(read_json(directory / "confirmation" / "analysis.json"), "analysis_digest")
    elif (directory / "confirmation").exists():
        raise ValueError("fresh confirmation artifacts exist despite failed nomination")
    if ledger.get("format") != "gre-wagner-ph-interpreter-depth-resource-ledger-v1":
        raise ValueError("interpreter-depth resource ledger format mismatch")
    for stage in STAGES:
        expected = "skipped" if not nomination["nominated"] and stage.startswith("confirmation-") else "completed"
        if ledger["stages"][stage]["status"] != expected:
            raise ValueError(f"interpreter-depth resource ledger stage is incomplete: {stage}")
    return {
        "verified": True,
        "top_level_checksums": len(checksums),
        "atlas_perturbations": int(manifest["atlas_perturbations"]),
        "development_populations": int(manifest["development_populations"]),
        "confirmation_generated": bool(manifest["confirmation_generated"]),
        "nested": nested,
    }


def wagner_ph_depth_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    if (directory / "SHA256SUMS").is_file():
        try:
            verification = verify_wagner_ph_depth_campaign(directory)
        except Exception as error:
            return {"status": "sealed-invalid", "output": str(directory), "error": str(error)}
        manifest = read_json(directory / "campaign-manifest.json")
        analysis = read_json(directory / "analysis.json")
        return {
            "status": "complete",
            "output": str(directory),
            "verification": verification,
            "elapsed_seconds": manifest["elapsed_seconds"],
            "nominee": analysis["nomination"]["candidate"],
            "confirmation_generated": analysis["fresh_confirmation_generated"],
            "confirmation_passes": analysis["confirmation_passes"],
        }
    result: dict[str, Any] = {"status": "incomplete", "output": str(directory)}
    for name in ("progress.json", "resource-ledger.json", "registration.json"):
        path = directory / name
        if path.is_file():
            try:
                result[name.removesuffix(".json").replace("-", "_")] = read_json(path)
            except Exception as error:
                result[f"{name}_error"] = str(error)
    result["completed_shards"] = {
        "atlas": len(list((directory / "atlas" / "tasks").glob("*.json"))),
        "development_evolution": len([
            value for value in (directory / "development" / "evolution" / "populations").glob("*.json")
            if not value.name.endswith(".checkpoint.json")
        ]),
        "development_audit": len(list((directory / "development" / "audit" / "populations").glob("*.json"))),
        "development_pedigree": len(list((directory / "development" / "pedigree" / "populations").glob("*.json"))),
        "confirmation_evolution": len([
            value for value in (directory / "confirmation" / "evolution" / "populations").glob("*.json")
            if not value.name.endswith(".checkpoint.json")
        ]),
    }
    return result


def replay_wagner_ph_depth(
    directory: Path,
    population_id: str | None = None,
    *,
    phase: str = "development",
    pedigree: bool = False,
    root_index: int = 0,
    lineage_index: int = 0,
    distance: int = 1,
    atlas_task: int | None = None,
    atlas_edge: int = 0,
    atlas_operation: str = "reset",
) -> dict[str, Any]:
    if atlas_task is not None:
        return replay_atlas_cell(directory / "atlas", atlas_task, root_index, atlas_edge, atlas_operation)
    if population_id is None:
        raise ValueError("population_id is required outside atlas replay")
    base = directory / phase
    if pedigree:
        return replay_pedigree_event(base / "pedigree", population_id, root_index, lineage_index, distance)
    return replay_depth_population(base / "evolution", population_id)
