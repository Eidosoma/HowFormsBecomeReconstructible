"""Six-hour orchestration for Wagner PH Interpreter Resilience v1."""

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
from .wagner_ph_cooption_evolution import run_cooption_evolution, verify_cooption_evolution
from .wagner_ph_depth_campaign import verify_wagner_ph_depth_campaign
from .wagner_ph_resilience_analysis import (
    analyze_resilience_phase,
    load_development_evidence,
    render_report,
)
from .wagner_ph_resilience_config import (
    RESILIENCE_FORMAT,
    ResilienceSpec,
    architecture_control,
    resilience_spec,
)
from .wagner_ph_resilience_evidence import (
    replay_resilience_pedigree,
    run_resilience_audit,
    run_resilience_diagnosis,
    run_resilience_pedigree,
    verify_resilience_audit,
    verify_resilience_diagnosis,
    verify_resilience_pedigree,
)
from .wagner_ph_resilience_evolution import (
    replay_resilience_population,
    run_resilience_evolution,
    verify_resilience_evolution,
)
from .wagner_ph_robustness_campaign import verify_wagner_ph_robustness_campaign


STAGES = (
    "resilience-diagnosis",
    "development-evolution",
    "development-audit-pedigree",
    "nomination",
    "confirmation-evolution",
    "confirmation-audit-pedigree",
    "sealing",
)


def _implementation_digest() -> str:
    root = Path(__file__).resolve().parents[2]
    names = (
        "WAGNER_PH_INTERPRETER_RESILIENCE_V1_PROTOCOL.md",
        "src/gre_sim/wagner.py",
        "src/gre_sim/wagner_ph_cooption_experiment.py",
        "src/gre_sim/wagner_ph_cooption_evolution.py",
        "src/gre_sim/wagner_ph_resilience_config.py",
        "src/gre_sim/wagner_ph_resilience_genome.py",
        "src/gre_sim/wagner_ph_resilience_evolution.py",
        "src/gre_sim/wagner_ph_resilience_evidence.py",
        "src/gre_sim/wagner_ph_resilience_analysis.py",
        "src/gre_sim/wagner_ph_resilience_campaign.py",
    )
    return canonical_digest({name: sha256_file(root / name) for name in names})


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _payload_digest(value: dict[str, Any], field: str) -> str:
    payload = dict(value); archived = payload.pop(field, None); digest = canonical_digest(payload)
    if archived != digest: raise ValueError(f"{field} mismatch")
    return digest


def _deadline(started: float, spec: ResilienceSpec) -> float:
    value = os.environ.get("GRE_WAGNER_PH_RESILIENCE_SOFT_DEADLINE_EPOCH")
    return float(value) if value is not None else started + spec.soft_wall_seconds


def _prior_consumed() -> float:
    value = float(os.environ.get("GRE_WAGNER_PH_RESILIENCE_PRIOR_CONSUMED_SECONDS", "0"))
    if value < 0: raise ValueError("resilience consumed time cannot be negative")
    return value


def _require_budget(deadline: float, reservation: int, stage: str) -> None:
    remaining = deadline - time.time()
    if remaining < reservation:
        raise TimeoutError(f"insufficient registered reserve for {stage}: {remaining:.1f}s remain; {reservation}s required")


def _initial_ledger(spec: ResilienceSpec) -> dict[str, Any]:
    return {
        "format": f"{RESILIENCE_FORMAT}-resource-ledger",
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
        "stages": {stage: {"reservation_seconds": reservation, "status": "pending", "attempts": 0, "elapsed_seconds": 0.0} for stage, reservation in zip(STAGES, spec.stage_reservations_seconds)},
    }


def _stage_begin(destination: Path, spec: ResilienceSpec, deadline: float, stage: str) -> float:
    _require_budget(deadline, spec.stage_reservations_seconds[STAGES.index(stage)], stage)
    path = destination / "resource-ledger.json"; ledger = read_json(path)
    entry = ledger["stages"][stage]; entry["status"] = "running"; entry["attempts"] += 1; entry["last_started_epoch"] = time.time()
    _atomic_json(path, ledger); return time.monotonic()


def _stage_complete(destination: Path, stage: str, started: float) -> None:
    path = destination / "resource-ledger.json"; ledger = read_json(path); entry = ledger["stages"][stage]
    entry["elapsed_seconds"] += time.monotonic() - started; entry["status"] = "completed"; entry["last_completed_epoch"] = time.time(); _atomic_json(path, ledger)


def _stage_skip(destination: Path, stage: str, reason: str) -> None:
    path = destination / "resource-ledger.json"; ledger = read_json(path); entry = ledger["stages"][stage]
    entry["status"] = "skipped"; entry["skip_reason"] = reason; _atomic_json(path, ledger)


def _recover(destination: Path, stage: str, skipped: bool = False) -> None:
    path = destination / "resource-ledger.json"; ledger = read_json(path); expected = "skipped" if skipped else "completed"
    if ledger["stages"][stage]["status"] != expected:
        ledger["stages"][stage]["status"] = expected; ledger["stages"][stage]["recovered_from_sealed_stage"] = True; _atomic_json(path, ledger)


def _progress(destination: Path, stage: str, started: float) -> None:
    _atomic_json(destination / "progress.json", {"format": f"{RESILIENCE_FORMAT}-progress", "stage": stage, "elapsed_seconds": time.monotonic()-started})


def _jsons(directory: Path) -> list[dict[str, Any]]:
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def _confirmation_arms(candidate: str) -> tuple[str, ...]:
    values = ["individual_reset"]
    same = architecture_control(candidate)
    if same not in values and same != candidate: values.append(same)
    if candidate not in values: values.append(candidate)
    return tuple(values)


def run_wagner_ph_resilience_campaign(
    parent: Path,
    reference: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = resilience_spec(smoke=smoke); spec.validate()
    if not 1 <= workers <= spec.maximum_workers: raise ValueError("resilience campaign permits one to four CPU workers")
    parent, reference, destination = parent.resolve(), reference.resolve(), destination.resolve()
    parent_verification = verify_wagner_ph_robustness_campaign(parent)
    reference_verification = verify_wagner_ph_depth_campaign(reference)
    if (destination / "SHA256SUMS").is_file(): verify_wagner_ph_resilience_campaign(destination); return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_mono, started_epoch, prior = time.monotonic(), time.time(), _prior_consumed(); deadline = _deadline(started_epoch, spec)
    kernel = spec.kernel(); protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": RESILIENCE_FORMAT, "protocol": spec.to_dict(), "protocol_digest": protocol_digest,
        "kernel": kernel.to_dict(), "kernel_digest": canonical_digest(kernel.to_dict()),
        "implementation_digest": _implementation_digest(),
        "robustness_parent": str(parent), "robustness_parent_checksum": sha256_file(parent / "SHA256SUMS"), "robustness_parent_verification": parent_verification,
        "interpreter_depth_reference": str(reference), "interpreter_depth_reference_checksum": sha256_file(reference / "SHA256SUMS"), "interpreter_depth_reference_verification": reference_verification,
        "confirmation_seed_commitment": canonical_digest((spec.confirmation_seed, "commitment")),
        "confirmation_inaccessible_until_nomination": True, "workers_requested": workers, "cpu_only": True,
    }
    if (destination / "registration.json").is_file() and read_json(destination / "registration.json") != registration: raise ValueError("existing resilience campaign registration differs")
    if not (destination / "registration.json").is_file(): _atomic_json(destination / "registration.json", registration)
    if not (destination / "resource-ledger.json").is_file(): _atomic_json(destination / "resource-ledger.json", _initial_ledger(spec))

    diagnosis = destination / "diagnosis"
    if not (diagnosis / "SHA256SUMS").is_file():
        stage = _stage_begin(destination, spec, deadline, "resilience-diagnosis")
        if progress: progress("starting frozen interpreter-resilience diagnosis")
        run_resilience_diagnosis(spec, reference, diagnosis, workers, progress); _stage_complete(destination, "resilience-diagnosis", stage)
    else: verify_resilience_diagnosis(diagnosis); _recover(destination, "resilience-diagnosis")
    _progress(destination, "resilience-diagnosis", started_mono)

    development = destination / "development"; evolution = development / "evolution"
    if not (evolution / "SHA256SUMS").is_file():
        stage = _stage_begin(destination, spec, deadline, "development-evolution")
        if progress: progress("starting six-arm interpreter-resilience evolution")
        development_arms = spec.arms + (("individual_reset",) if smoke else ())
        run_resilience_evolution(spec, parent / "evolution", evolution, workers, progress, selected_arms=development_arms); _stage_complete(destination, "development-evolution", stage)
    else: verify_resilience_evolution(evolution); _recover(destination, "development-evolution")
    _progress(destination, "development-evolution", started_mono)

    audit, pedigree = development / "audit", development / "pedigree"
    if not (audit / "SHA256SUMS").is_file() or not (pedigree / "SHA256SUMS").is_file():
        stage = _stage_begin(destination, spec, deadline, "development-audit-pedigree")
        if progress: progress("starting held-out resilience audit and paired mechanism-off pedigrees")
        run_resilience_audit(spec, evolution, audit, workers, progress); run_resilience_pedigree(spec, evolution, pedigree, workers, progress)
        _stage_complete(destination, "development-audit-pedigree", stage)
    else: verify_resilience_audit(audit); verify_resilience_pedigree(pedigree); _recover(destination, "development-audit-pedigree")
    _progress(destination, "development-audit-pedigree", started_mono)

    analysis_path, nomination_path = development / "analysis.json", development / "nomination.json"
    if not analysis_path.is_file() or not nomination_path.is_file():
        stage = _stage_begin(destination, spec, deadline, "nomination")
        audit_rows, pedigree_analysis = load_development_evidence(destination, reference)
        development_analysis = analyze_resilience_phase(audit_rows, pedigree_analysis, spec, "development")
        _atomic_json(analysis_path, development_analysis)
        nomination = {**development_analysis["nomination"], "development_analysis_digest": development_analysis["analysis_digest"], "confirmation_seed_generated_zero_tasks_before_nomination": True}
        nomination["nomination_digest"] = canonical_digest(nomination); _atomic_json(nomination_path, nomination); _stage_complete(destination, "nomination", stage)
    else:
        development_analysis, nomination = read_json(analysis_path), read_json(nomination_path); _payload_digest(development_analysis, "analysis_digest"); _payload_digest(nomination, "nomination_digest"); _recover(destination, "nomination")
    _progress(destination, "nomination", started_mono)

    confirmation_analysis = None; confirmation = destination / "confirmation"
    if nomination["nominated"]:
        candidate = nomination["candidate"]; burnin, confirmation_evolution = confirmation / "burnin", confirmation / "evolution"
        if not (confirmation_evolution / "SHA256SUMS").is_file():
            _require_budget(deadline, sum(spec.stage_reservations_seconds[4:]), "complete confirmation and sealing")
            stage = _stage_begin(destination, spec, deadline, "confirmation-evolution")
            if progress: progress(f"generating fresh confirmation for {candidate}")
            burnin_kernel = replace(spec.kernel(confirmation=True), cohort_id=spec.cohort_id+"-confirmation-burnin", generations=spec.confirmation_burnin_generations)
            run_cooption_evolution(burnin_kernel, burnin, workers, progress, treatments=("direct_independent",), task_count=spec.confirmation_task_count, master_seed=spec.confirmation_seed, predictive_persistence=spec.predictive_persistence)
            run_resilience_evolution(spec, burnin, confirmation_evolution, workers, progress, phase="confirmation", selected_arms=_confirmation_arms(candidate))
            _stage_complete(destination, "confirmation-evolution", stage)
        else: verify_cooption_evolution(burnin); verify_resilience_evolution(confirmation_evolution); _recover(destination, "confirmation-evolution")
        confirmation_audit, confirmation_pedigree = confirmation / "audit", confirmation / "pedigree"
        if not (confirmation_audit / "SHA256SUMS").is_file() or not (confirmation_pedigree / "SHA256SUMS").is_file() or not (confirmation / "analysis.json").is_file():
            stage = _stage_begin(destination, spec, deadline, "confirmation-audit-pedigree")
            run_resilience_audit(spec, confirmation_evolution, confirmation_audit, workers, progress); run_resilience_pedigree(spec, confirmation_evolution, confirmation_pedigree, workers, progress)
            confirmation_analysis = analyze_resilience_phase(_jsons(confirmation_audit / "populations"), read_json(confirmation_pedigree / "analysis.json"), spec, "confirmation", forced_candidate=candidate)
            _atomic_json(confirmation / "analysis.json", confirmation_analysis); _stage_complete(destination, "confirmation-audit-pedigree", stage)
        else: verify_resilience_audit(confirmation_audit); verify_resilience_pedigree(confirmation_pedigree); confirmation_analysis = read_json(confirmation / "analysis.json"); _payload_digest(confirmation_analysis, "analysis_digest"); _recover(destination, "confirmation-audit-pedigree")
    else:
        _stage_skip(destination, "confirmation-evolution", "development produced no eligible nominee")
        _stage_skip(destination, "confirmation-audit-pedigree", "development produced no eligible nominee")
    _progress(destination, "confirmation", started_mono)

    stage = _stage_begin(destination, spec, deadline, "sealing")
    combined = {
        "format": RESILIENCE_FORMAT, "development_analysis": development_analysis,
        "development_analysis_digest": development_analysis["analysis_digest"], "nomination": nomination,
        "fresh_confirmation_generated": bool(nomination["nominated"]),
        "fresh_confirmation_task_count": spec.confirmation_task_count if nomination["nominated"] else 0,
        "confirmation_analysis": confirmation_analysis,
        "confirmation_passes": confirmation_analysis["confirmation_passes"] if confirmation_analysis else None,
        "claim_boundary": development_analysis["claim_boundary"],
    }
    combined["analysis_digest"] = canonical_digest(combined); _atomic_json(destination / "analysis.json", combined)
    elapsed = time.monotonic()-started_mono
    manifest = {
        "format": RESILIENCE_FORMAT, "protocol_digest": protocol_digest, "implementation_digest": registration["implementation_digest"],
        "diagnosis_checksum": sha256_file(diagnosis / "SHA256SUMS"), "development_evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "development_audit_checksum": sha256_file(audit / "SHA256SUMS"), "development_pedigree_checksum": sha256_file(pedigree / "SHA256SUMS"),
        "nomination_digest": nomination["nomination_digest"], "confirmation_generated": bool(nomination["nominated"]),
        "analysis_digest": combined["analysis_digest"], "development_populations": (len(spec.arms)+(1 if smoke else 0))*spec.task_count,
        "maximum_workers": workers, "cpu_only": True, "elapsed_seconds": elapsed, "prior_consumed_seconds": prior,
        "cumulative_wall_seconds": prior+elapsed, "hard_wall_seconds": spec.hard_wall_seconds, "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_six_hour_boundary": prior+elapsed <= spec.hard_wall_seconds, "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest); (destination / "report.md").write_text(render_report(development_analysis, confirmation_analysis), encoding="utf-8")
    _stage_complete(destination, "sealing", stage); _progress(destination, "sealed", started_mono); write_checksums(destination); verify_wagner_ph_resilience_campaign(destination)
    if progress: progress("sealed and independently verified Interpreter Resilience v1")
    return destination


def verify_wagner_ph_resilience_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve(); checksums = verify_checksums(directory); registration = read_json(directory / "registration.json"); manifest = read_json(directory / "campaign-manifest.json"); analysis = read_json(directory / "analysis.json"); nomination = read_json(directory / "development" / "nomination.json"); ledger = read_json(directory / "resource-ledger.json")
    if registration["format"] != RESILIENCE_FORMAT or manifest["format"] != RESILIENCE_FORMAT: raise ValueError("resilience campaign format mismatch")
    spec = ResilienceSpec.from_dict(registration["protocol"])
    if canonical_digest(spec.to_dict()) != registration["protocol_digest"] or manifest["protocol_digest"] != registration["protocol_digest"]: raise ValueError("resilience protocol mismatch")
    if registration["implementation_digest"] != _implementation_digest() or manifest["implementation_digest"] != registration["implementation_digest"]: raise ValueError("resilience implementation changed after registration")
    if sha256_file(Path(registration["robustness_parent"]) / "SHA256SUMS") != registration["robustness_parent_checksum"]: raise ValueError("sealed robustness parent changed")
    if sha256_file(Path(registration["interpreter_depth_reference"]) / "SHA256SUMS") != registration["interpreter_depth_reference_checksum"]: raise ValueError("sealed Interpreter-Depth reference changed")
    nested = {
        "diagnosis": verify_resilience_diagnosis(directory / "diagnosis"),
        "development_evolution": verify_resilience_evolution(directory / "development" / "evolution"),
        "development_audit": verify_resilience_audit(directory / "development" / "audit"),
        "development_pedigree": verify_resilience_pedigree(directory / "development" / "pedigree"),
    }
    _payload_digest(read_json(directory / "development" / "analysis.json"), "analysis_digest"); _payload_digest(nomination, "nomination_digest"); _payload_digest(analysis, "analysis_digest")
    if manifest["analysis_digest"] != analysis["analysis_digest"] or manifest["nomination_digest"] != nomination["nomination_digest"]: raise ValueError("resilience analysis references differ")
    if nomination["nominated"]:
        nested.update({"confirmation_burnin": verify_cooption_evolution(directory / "confirmation" / "burnin"), "confirmation_evolution": verify_resilience_evolution(directory / "confirmation" / "evolution"), "confirmation_audit": verify_resilience_audit(directory / "confirmation" / "audit"), "confirmation_pedigree": verify_resilience_pedigree(directory / "confirmation" / "pedigree")})
        _payload_digest(read_json(directory / "confirmation" / "analysis.json"), "analysis_digest")
    elif (directory / "confirmation").exists(): raise ValueError("confirmation artifacts exist without nomination")
    for stage in STAGES:
        expected = "skipped" if not nomination["nominated"] and stage.startswith("confirmation-") else "completed"
        if ledger["stages"][stage]["status"] != expected: raise ValueError(f"resilience ledger stage incomplete: {stage}")
    return {"verified": True, "top_level_checksums": len(checksums), "development_populations": manifest["development_populations"], "confirmation_generated": bool(nomination["nominated"]), "nested": nested}


def wagner_ph_resilience_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists(): return {"status": "not-started", "output": str(directory)}
    if (directory / "SHA256SUMS").is_file():
        try: verification = verify_wagner_ph_resilience_campaign(directory)
        except Exception as error: return {"status": "sealed-invalid", "output": str(directory), "error": str(error)}
        analysis = read_json(directory / "analysis.json"); manifest = read_json(directory / "campaign-manifest.json")
        return {"status": "complete", "output": str(directory), "elapsed_seconds": manifest["elapsed_seconds"], "nominee": analysis["nomination"]["candidate"], "confirmation_generated": analysis["fresh_confirmation_generated"], "confirmation_passes": analysis["confirmation_passes"], "verification": verification}
    result: dict[str, Any] = {"status": "incomplete", "output": str(directory)}
    for name in ("progress.json", "resource-ledger.json", "registration.json"):
        if (directory / name).is_file(): result[name.removesuffix(".json").replace("-", "_")] = read_json(directory / name)
    result["completed_shards"] = {
        "diagnosis": len(list((directory / "diagnosis" / "tasks").glob("*.json"))),
        "development_evolution": len([path for path in (directory / "development" / "evolution" / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json")]),
        "development_audit": len(list((directory / "development" / "audit" / "populations").glob("*.json"))),
        "development_pedigree": len(list((directory / "development" / "pedigree" / "populations").glob("*.json"))),
        "confirmation_evolution": len([path for path in (directory / "confirmation" / "evolution" / "populations").glob("*.json") if not path.name.endswith(".checkpoint.json")]),
    }
    return result


def replay_wagner_ph_resilience(
    directory: Path, population_id: str, *, phase: str = "development", pedigree: bool = False,
    root_index: int = 0, lineage_index: int = 0, distance: int = 1, mode: str = "natural",
) -> dict[str, Any]:
    base = directory / phase
    return (
        replay_resilience_pedigree(base / "pedigree", population_id, root_index, lineage_index, distance, mode)
        if pedigree else replay_resilience_population(base / "evolution", population_id)
    )
