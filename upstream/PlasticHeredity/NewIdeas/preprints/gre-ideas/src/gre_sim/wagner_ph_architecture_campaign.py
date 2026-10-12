"""Eight-hour orchestration for Wagner PH Interpreter Architecture v1."""

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
from .wagner_ph_architecture_analysis import (
    analyze_architecture_phase,
    load_development_evidence,
    render_report,
)
from .wagner_ph_architecture_config import (
    ARCHITECTURE_FORMAT,
    ArchitectureSpec,
    architecture_spec,
    arm_settings,
    uniform_control,
)
from .wagner_ph_architecture_diagnosis import (
    run_architecture_diagnosis,
    verify_architecture_diagnosis,
)
from .wagner_ph_architecture_evidence import (
    replay_architecture_pedigree,
    run_architecture_audit,
    run_architecture_pedigree,
    verify_architecture_audit,
    verify_architecture_pedigree,
)
from .wagner_ph_architecture_evolution import (
    replay_architecture_population,
    run_architecture_evolution,
    verify_architecture_evolution,
)
from .wagner_ph_cooption_evolution import (
    run_cooption_evolution,
    verify_cooption_evolution,
)
from .wagner_ph_depth_campaign import verify_wagner_ph_depth_campaign
from .wagner_ph_resilience_campaign import verify_wagner_ph_resilience_campaign


STAGES = (
    "architecture-diagnosis",
    "development-evolution",
    "development-audit-pedigree",
    "two-candidate-nomination",
    "confirmation-evolution",
    "confirmation-audit-pedigree",
    "sealing",
)


def _implementation_digest() -> str:
    root = Path(__file__).resolve().parents[2]
    names = (
        "WAGNER_PH_INTERPRETER_ARCHITECTURE_V1_PROTOCOL.md",
        "src/gre_sim/wagner.py",
        "src/gre_sim/wagner_ph_cooption_experiment.py",
        "src/gre_sim/wagner_ph_cooption_evolution.py",
        "src/gre_sim/wagner_ph_architecture_config.py",
        "src/gre_sim/wagner_ph_architecture_genome.py",
        "src/gre_sim/wagner_ph_architecture_predictor.py",
        "src/gre_sim/wagner_ph_architecture_diagnosis.py",
        "src/gre_sim/wagner_ph_architecture_evolution.py",
        "src/gre_sim/wagner_ph_architecture_evidence.py",
        "src/gre_sim/wagner_ph_architecture_analysis.py",
        "src/gre_sim/wagner_ph_architecture_campaign.py",
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


def _deadline(started_epoch: float, spec: ArchitectureSpec) -> float:
    value = os.environ.get("GRE_WAGNER_PH_ARCHITECTURE_SOFT_DEADLINE_EPOCH")
    return float(value) if value is not None else started_epoch + spec.soft_wall_seconds


def _prior_consumed() -> float:
    value = float(
        os.environ.get("GRE_WAGNER_PH_ARCHITECTURE_PRIOR_CONSUMED_SECONDS", "0")
    )
    if value < 0.0:
        raise ValueError("architecture consumed time cannot be negative")
    return value


def _require_budget(deadline: float, reservation: int, stage: str) -> None:
    remaining = deadline - time.time()
    if remaining < reservation:
        raise TimeoutError(
            f"insufficient registered reserve for {stage}: "
            f"{remaining:.1f}s remain; {reservation}s required"
        )


def _initial_ledger(spec: ArchitectureSpec) -> dict[str, Any]:
    return {
        "format": f"{ARCHITECTURE_FORMAT}-resource-ledger",
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "unreserved_soft_contingency_seconds": spec.soft_wall_seconds
        - sum(spec.stage_reservations_seconds),
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
    spec: ArchitectureSpec,
    deadline: float,
    stage: str,
) -> float:
    _require_budget(
        deadline, spec.stage_reservations_seconds[STAGES.index(stage)], stage
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
            "format": f"{ARCHITECTURE_FORMAT}-progress",
            "stage": stage,
            "elapsed_seconds": time.monotonic() - started,
            "updated_epoch": time.time(),
        },
    )


def _jsons(directory: Path) -> list[dict[str, Any]]:
    return [read_json(path) for path in sorted(directory.glob("*.json"))]


def confirmation_arms(candidates: tuple[str, str]) -> tuple[str, ...]:
    """Return both focal arms and all preregistered, deduplicated controls."""

    if len(set(candidates)) != 2:
        raise ValueError("confirmation requires two distinct candidates")
    values = ["individual_single"]

    def add(name: str | None) -> None:
        if name is not None and name not in values:
            values.append(name)

    for candidate in candidates:
        settings = arm_settings(candidate)
        architecture = settings["architecture"]
        if architecture in {"single", "repair"}:
            add(f"mh_{architecture}_ordinary")
        if settings["challenge"] == "guided":
            add(uniform_control(candidate))
        if architecture == "repair":
            add("individual_repair")
        elif architecture == "median3":
            add("individual_mean3")
            add("mh_mean3_ordinary")
        add(candidate)
    return tuple(values)


def run_wagner_ph_architecture_campaign(
    reference: Path,
    resilience: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = architecture_spec(smoke=smoke)
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("architecture campaign permits one to four CPU workers")
    reference = reference.resolve()
    resilience = resilience.resolve()
    destination = destination.resolve()
    reference_verification = verify_wagner_ph_depth_campaign(reference)
    resilience_verification = verify_wagner_ph_resilience_campaign(resilience)
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_architecture_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_mono = time.monotonic()
    started_epoch = time.time()
    prior = _prior_consumed()
    deadline = _deadline(started_epoch, spec)
    kernel = spec.kernel()
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": ARCHITECTURE_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "kernel": kernel.to_dict(),
        "kernel_digest": canonical_digest(kernel.to_dict()),
        "implementation_digest": _implementation_digest(),
        "interpreter_depth_reference": str(reference),
        "interpreter_depth_reference_checksum": sha256_file(
            reference / "SHA256SUMS"
        ),
        "interpreter_depth_reference_verification": reference_verification,
        "interpreter_resilience_source": str(resilience),
        "interpreter_resilience_source_checksum": sha256_file(
            resilience / "SHA256SUMS"
        ),
        "interpreter_resilience_source_verification": resilience_verification,
        "confirmation_seed_commitment": canonical_digest(
            (spec.confirmation_seed, "architecture-confirmation-commitment")
        ),
        "confirmation_inaccessible_until_two_candidate_nomination": True,
        "workers_requested": workers,
        "maximum_workers": spec.maximum_workers,
        "cpu_only": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing architecture campaign registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    if not (destination / "resource-ledger.json").is_file():
        _atomic_json(destination / "resource-ledger.json", _initial_ledger(spec))

    diagnosis = destination / "diagnosis"
    if not (diagnosis / "SHA256SUMS").is_file():
        stage_started = _stage_begin(
            destination, spec, deadline, "architecture-diagnosis"
        )
        if progress:
            progress("starting cross-fitted predictor and causal architecture diagnosis")
        run_architecture_diagnosis(
            spec, reference, resilience, diagnosis, workers, progress
        )
        _stage_complete(destination, "architecture-diagnosis", stage_started)
    else:
        verify_architecture_diagnosis(diagnosis)
        _recover(destination, "architecture-diagnosis")
    predictor = read_json(diagnosis / "registration.json")["predictor"]
    _progress(destination, "architecture-diagnosis", started_mono)

    development = destination / "development"
    evolution = development / "evolution"
    if not (evolution / "SHA256SUMS").is_file():
        stage_started = _stage_begin(
            destination, spec, deadline, "development-evolution"
        )
        if progress:
            progress("starting seven-arm outcome-only architecture evolution")
        development_arms = spec.arms + (("individual_single",) if smoke else ())
        run_architecture_evolution(
            spec,
            resilience / "development" / "evolution",
            evolution,
            workers,
            predictor,
            progress,
            selected_arms=development_arms,
        )
        _stage_complete(destination, "development-evolution", stage_started)
    else:
        verify_architecture_evolution(evolution)
        _recover(destination, "development-evolution")
    _progress(destination, "development-evolution", started_mono)

    audit = development / "audit"
    pedigree = development / "pedigree"
    if not (audit / "SHA256SUMS").is_file() or not (
        pedigree / "SHA256SUMS"
    ).is_file():
        stage_started = _stage_begin(
            destination, spec, deadline, "development-audit-pedigree"
        )
        if progress:
            progress("starting held-out PH audits and ordinary-mutation pedigrees")
        run_architecture_audit(spec, evolution, audit, workers, progress)
        run_architecture_pedigree(spec, evolution, pedigree, workers, progress)
        _stage_complete(
            destination, "development-audit-pedigree", stage_started
        )
    else:
        verify_architecture_audit(audit)
        verify_architecture_pedigree(pedigree)
        _recover(destination, "development-audit-pedigree")
    _progress(destination, "development-audit-pedigree", started_mono)

    analysis_path = development / "analysis.json"
    nomination_path = development / "nomination.json"
    if not analysis_path.is_file() or not nomination_path.is_file():
        stage_started = _stage_begin(
            destination, spec, deadline, "two-candidate-nomination"
        )
        audit_rows, pedigree_analysis = load_development_evidence(
            destination, reference, spec
        )
        development_analysis = analyze_architecture_phase(
            audit_rows, pedigree_analysis, spec, "development"
        )
        _atomic_json(analysis_path, development_analysis)
        candidates = tuple(development_analysis["nomination"]["candidates"])
        nomination = {
            **development_analysis["nomination"],
            "confirmation_arms": list(confirmation_arms(candidates)),
            "development_analysis_digest": development_analysis[
                "analysis_digest"
            ],
            "predictor_digest": predictor["predictor_digest"],
            "confirmation_seed_generated_zero_tasks_before_nomination": True,
        }
        nomination["nomination_digest"] = canonical_digest(nomination)
        _atomic_json(nomination_path, nomination)
        _stage_complete(destination, "two-candidate-nomination", stage_started)
    else:
        development_analysis = read_json(analysis_path)
        nomination = read_json(nomination_path)
        _payload_digest(development_analysis, "analysis_digest")
        _payload_digest(nomination, "nomination_digest")
        _recover(destination, "two-candidate-nomination")
    candidates = tuple(nomination["candidates"])
    if len(candidates) != 2:
        raise ValueError("two-candidate nomination is malformed")
    _progress(destination, "two-candidate-nomination", started_mono)

    confirmation = destination / "confirmation"
    burnin = confirmation / "burnin"
    confirmation_evolution = confirmation / "evolution"
    if not (confirmation_evolution / "SHA256SUMS").is_file():
        _require_budget(
            deadline,
            sum(spec.stage_reservations_seconds[4:]),
            "complete mandatory confirmation and sealing",
        )
        stage_started = _stage_begin(
            destination, spec, deadline, "confirmation-evolution"
        )
        if progress:
            progress(
                "generating sixteen untouched tasks for both frozen candidates"
            )
        burnin_kernel = replace(
            spec.kernel(confirmation=True),
            cohort_id=spec.cohort_id + "-confirmation-burnin",
            generations=spec.confirmation_burnin_generations,
        )
        run_cooption_evolution(
            burnin_kernel,
            burnin,
            workers,
            progress,
            treatments=("direct_independent",),
            task_count=spec.confirmation_task_count,
            master_seed=spec.confirmation_seed,
            predictive_persistence=spec.predictive_persistence,
        )
        run_architecture_evolution(
            spec,
            burnin,
            confirmation_evolution,
            workers,
            predictor,
            progress,
            phase="confirmation",
            selected_arms=tuple(nomination["confirmation_arms"]),
            source_arm="direct_independent",
        )
        _stage_complete(destination, "confirmation-evolution", stage_started)
    else:
        verify_cooption_evolution(burnin)
        verify_architecture_evolution(confirmation_evolution)
        _recover(destination, "confirmation-evolution")
    _progress(destination, "confirmation-evolution", started_mono)

    confirmation_audit = confirmation / "audit"
    confirmation_pedigree = confirmation / "pedigree"
    confirmation_analysis_path = confirmation / "analysis.json"
    if (
        not (confirmation_audit / "SHA256SUMS").is_file()
        or not (confirmation_pedigree / "SHA256SUMS").is_file()
        or not confirmation_analysis_path.is_file()
    ):
        stage_started = _stage_begin(
            destination, spec, deadline, "confirmation-audit-pedigree"
        )
        if progress:
            progress("starting fresh audits, pedigrees, and mechanism contrasts")
        run_architecture_audit(
            spec, confirmation_evolution, confirmation_audit, workers, progress
        )
        run_architecture_pedigree(
            spec, confirmation_evolution, confirmation_pedigree, workers, progress
        )
        confirmation_analysis = analyze_architecture_phase(
            _jsons(confirmation_audit / "populations"),
            read_json(confirmation_pedigree / "analysis.json"),
            spec,
            "confirmation",
            forced_candidates=(str(candidates[0]), str(candidates[1])),
        )
        _atomic_json(confirmation_analysis_path, confirmation_analysis)
        _stage_complete(
            destination, "confirmation-audit-pedigree", stage_started
        )
    else:
        verify_architecture_audit(confirmation_audit)
        verify_architecture_pedigree(confirmation_pedigree)
        confirmation_analysis = read_json(confirmation_analysis_path)
        _payload_digest(confirmation_analysis, "analysis_digest")
        _recover(destination, "confirmation-audit-pedigree")
    _progress(destination, "confirmation-audit-pedigree", started_mono)

    stage_started = _stage_begin(destination, spec, deadline, "sealing")
    diagnosis_analysis = read_json(diagnosis / "analysis.json")
    combined = {
        "format": ARCHITECTURE_FORMAT,
        "development_analysis": development_analysis,
        "development_analysis_digest": development_analysis["analysis_digest"],
        "diagnosis_analysis": diagnosis_analysis,
        "diagnosis_analysis_digest": diagnosis_analysis["analysis_digest"],
        "nomination": nomination,
        "fresh_confirmation_generated": True,
        "fresh_confirmation_task_count": spec.confirmation_task_count,
        "confirmation_analysis": confirmation_analysis,
        "confirmation_analysis_digest": confirmation_analysis["analysis_digest"],
        "confirmation_passes": confirmation_analysis["confirmation"],
        "claim_boundary": development_analysis["claim_boundary"],
    }
    combined["analysis_digest"] = canonical_digest(combined)
    _atomic_json(destination / "analysis.json", combined)
    _atomic_text(
        destination / "report.md",
        render_report(development_analysis, confirmation_analysis, diagnosis_analysis),
    )
    _stage_complete(destination, "sealing", stage_started)
    _progress(destination, "sealed", started_mono)
    elapsed = time.monotonic() - started_mono
    manifest = {
        "format": ARCHITECTURE_FORMAT,
        "protocol_digest": protocol_digest,
        "implementation_digest": registration["implementation_digest"],
        "diagnosis_checksum": sha256_file(diagnosis / "SHA256SUMS"),
        "development_evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "development_audit_checksum": sha256_file(audit / "SHA256SUMS"),
        "development_pedigree_checksum": sha256_file(pedigree / "SHA256SUMS"),
        "nomination_digest": nomination["nomination_digest"],
        "confirmation_burnin_checksum": sha256_file(burnin / "SHA256SUMS"),
        "confirmation_evolution_checksum": sha256_file(
            confirmation_evolution / "SHA256SUMS"
        ),
        "confirmation_audit_checksum": sha256_file(
            confirmation_audit / "SHA256SUMS"
        ),
        "confirmation_pedigree_checksum": sha256_file(
            confirmation_pedigree / "SHA256SUMS"
        ),
        "analysis_digest": combined["analysis_digest"],
        "development_populations": (
            len(spec.arms) + (1 if smoke else 0)
        )
        * spec.task_count,
        "confirmation_populations": len(nomination["confirmation_arms"])
        * spec.confirmation_task_count,
        "maximum_workers": workers,
        "cpu_only": True,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior,
        "cumulative_wall_seconds": prior + elapsed,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_eight_hour_boundary": prior + elapsed
        <= spec.hard_wall_seconds,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    write_checksums(destination)
    verify_wagner_ph_architecture_campaign(destination)
    if progress:
        progress("sealed and independently verified Interpreter Architecture v1")
    return destination


def verify_wagner_ph_architecture_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    nomination = read_json(directory / "development" / "nomination.json")
    ledger = read_json(directory / "resource-ledger.json")
    if (
        registration["format"] != ARCHITECTURE_FORMAT
        or manifest["format"] != ARCHITECTURE_FORMAT
    ):
        raise ValueError("architecture campaign format mismatch")
    spec = ArchitectureSpec.from_dict(registration["protocol"])
    if (
        canonical_digest(spec.to_dict()) != registration["protocol_digest"]
        or manifest["protocol_digest"] != registration["protocol_digest"]
        or canonical_digest(registration["kernel"])
        != registration["kernel_digest"]
    ):
        raise ValueError("architecture protocol mismatch")
    if (
        registration["implementation_digest"] != _implementation_digest()
        or manifest["implementation_digest"]
        != registration["implementation_digest"]
    ):
        raise ValueError("architecture implementation changed after registration")
    if (
        sha256_file(Path(registration["interpreter_depth_reference"]) / "SHA256SUMS")
        != registration["interpreter_depth_reference_checksum"]
    ):
        raise ValueError("sealed Interpreter-Depth reference changed")
    if (
        sha256_file(
            Path(registration["interpreter_resilience_source"]) / "SHA256SUMS"
        )
        != registration["interpreter_resilience_source_checksum"]
    ):
        raise ValueError("sealed Interpreter-Resilience source changed")
    candidates = tuple(nomination["candidates"])
    if (
        len(candidates) != 2
        or arm_settings(candidates[0])["architecture"] != "single"
        or arm_settings(candidates[1])["architecture"] == "single"
    ):
        raise ValueError("architecture candidate families are malformed")
    if tuple(nomination["confirmation_arms"]) != confirmation_arms(candidates):
        raise ValueError("architecture confirmation control set changed")
    nested = {
        "diagnosis": verify_architecture_diagnosis(directory / "diagnosis"),
        "development_evolution": verify_architecture_evolution(
            directory / "development" / "evolution"
        ),
        "development_audit": verify_architecture_audit(
            directory / "development" / "audit"
        ),
        "development_pedigree": verify_architecture_pedigree(
            directory / "development" / "pedigree"
        ),
        "confirmation_burnin": verify_cooption_evolution(
            directory / "confirmation" / "burnin"
        ),
        "confirmation_evolution": verify_architecture_evolution(
            directory / "confirmation" / "evolution"
        ),
        "confirmation_audit": verify_architecture_audit(
            directory / "confirmation" / "audit"
        ),
        "confirmation_pedigree": verify_architecture_pedigree(
            directory / "confirmation" / "pedigree"
        ),
    }
    development_analysis = read_json(directory / "development" / "analysis.json")
    confirmation_analysis = read_json(directory / "confirmation" / "analysis.json")
    _payload_digest(development_analysis, "analysis_digest")
    _payload_digest(nomination, "nomination_digest")
    _payload_digest(confirmation_analysis, "analysis_digest")
    _payload_digest(analysis, "analysis_digest")
    if (
        manifest["analysis_digest"] != analysis["analysis_digest"]
        or manifest["nomination_digest"] != nomination["nomination_digest"]
        or nomination["development_analysis_digest"]
        != development_analysis["analysis_digest"]
        or tuple(development_analysis["nomination"]["candidates"]) != candidates
        or tuple(confirmation_analysis["nomination"]["candidates"]) != candidates
        or analysis["development_analysis_digest"]
        != development_analysis["analysis_digest"]
        or analysis["confirmation_analysis_digest"]
        != confirmation_analysis["analysis_digest"]
    ):
        raise ValueError("architecture analysis references differ")
    checksum_fields = {
        "diagnosis_checksum": directory / "diagnosis" / "SHA256SUMS",
        "development_evolution_checksum": directory
        / "development"
        / "evolution"
        / "SHA256SUMS",
        "development_audit_checksum": directory
        / "development"
        / "audit"
        / "SHA256SUMS",
        "development_pedigree_checksum": directory
        / "development"
        / "pedigree"
        / "SHA256SUMS",
        "confirmation_burnin_checksum": directory
        / "confirmation"
        / "burnin"
        / "SHA256SUMS",
        "confirmation_evolution_checksum": directory
        / "confirmation"
        / "evolution"
        / "SHA256SUMS",
        "confirmation_audit_checksum": directory
        / "confirmation"
        / "audit"
        / "SHA256SUMS",
        "confirmation_pedigree_checksum": directory
        / "confirmation"
        / "pedigree"
        / "SHA256SUMS",
    }
    if any(
        manifest[field] != sha256_file(path)
        for field, path in checksum_fields.items()
    ):
        raise ValueError("architecture nested checksum reference differs")
    if not analysis["fresh_confirmation_generated"]:
        raise ValueError("mandatory architecture confirmation was not generated")
    expected_reservations = dict(zip(STAGES, spec.stage_reservations_seconds))
    if any(
        ledger["stages"][stage]["status"] != "completed"
        or ledger["stages"][stage]["reservation_seconds"]
        != expected_reservations[stage]
        for stage in STAGES
    ):
        raise ValueError("architecture resource ledger is incomplete")
    if (
        manifest["cumulative_wall_seconds"] > spec.hard_wall_seconds
        or manifest["maximum_workers"] > spec.maximum_workers
        or not manifest["cpu_only"]
        or not registration["cpu_only"]
    ):
        raise ValueError("architecture campaign exceeded its hard wall boundary")
    return {
        "verified": True,
        "top_level_checksums": len(checksums),
        "development_populations": manifest["development_populations"],
        "confirmation_populations": manifest["confirmation_populations"],
        "candidates": list(candidates),
        "nested": nested,
    }


def wagner_ph_architecture_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    if (directory / "SHA256SUMS").is_file():
        try:
            verification = verify_wagner_ph_architecture_campaign(directory)
        except Exception as error:
            return {
                "status": "sealed-invalid",
                "output": str(directory),
                "error": str(error),
            }
        analysis = read_json(directory / "analysis.json")
        manifest = read_json(directory / "campaign-manifest.json")
        return {
            "status": "complete",
            "output": str(directory),
            "elapsed_seconds": manifest["elapsed_seconds"],
            "candidates": analysis["nomination"]["candidates"],
            "confirmation_passes": analysis["confirmation_passes"],
            "verification": verification,
        }
    result: dict[str, Any] = {"status": "incomplete", "output": str(directory)}
    for name in ("progress.json", "resource-ledger.json", "registration.json"):
        if (directory / name).is_file():
            result[name.removesuffix(".json").replace("-", "_")] = read_json(
                directory / name
            )
    shard_directories = {
        "diagnosis": directory / "diagnosis" / "tasks",
        "development_evolution": directory / "development" / "evolution" / "populations",
        "development_audit": directory / "development" / "audit" / "populations",
        "development_pedigree": directory / "development" / "pedigree" / "populations",
        "confirmation_burnin": directory / "confirmation" / "burnin" / "populations",
        "confirmation_evolution": directory / "confirmation" / "evolution" / "populations",
        "confirmation_audit": directory / "confirmation" / "audit" / "populations",
        "confirmation_pedigree": directory / "confirmation" / "pedigree" / "populations",
    }
    result["completed_shards"] = {
        name: len(
            [path for path in location.glob("*.json") if not path.name.endswith(".checkpoint.json")]
        )
        for name, location in shard_directories.items()
    }
    progress_paths = {
        "diagnosis": directory / "diagnosis" / "progress.json",
        "development_evolution": directory
        / "development"
        / "evolution"
        / "progress.json",
        "development_audit": directory
        / "development"
        / "audit"
        / "progress.json",
        "development_pedigree": directory
        / "development"
        / "pedigree"
        / "progress.json",
        "confirmation_burnin": directory
        / "confirmation"
        / "burnin"
        / "progress.json",
        "confirmation_evolution": directory
        / "confirmation"
        / "evolution"
        / "progress.json",
        "confirmation_audit": directory
        / "confirmation"
        / "audit"
        / "progress.json",
        "confirmation_pedigree": directory
        / "confirmation"
        / "pedigree"
        / "progress.json",
    }
    stage_progress: dict[str, Any] = {}
    for name, path in progress_paths.items():
        if not path.is_file():
            continue
        value = read_json(path)
        if "eta_seconds" not in value:
            completed = value.get("completed_populations", value.get("completed_tasks"))
            total = value.get("total_populations", value.get("total_tasks"))
            elapsed = value.get("elapsed_seconds")
            if completed and total is not None and elapsed is not None:
                rate = float(completed) / max(float(elapsed), 1e-9)
                value["eta_seconds"] = (float(total) - float(completed)) / rate
        stage_progress[name] = value
    result["stage_progress"] = stage_progress
    return result


def replay_wagner_ph_architecture(
    directory: Path,
    population_id: str,
    *,
    phase: str = "development",
    pedigree: bool = False,
    root_index: int = 0,
    lineage_index: int = 0,
    distance: int = 1,
    mode: str = "natural",
) -> dict[str, Any]:
    base = directory / phase
    if pedigree:
        return replay_architecture_pedigree(
            base / "pedigree",
            population_id,
            root_index,
            lineage_index,
            distance,
            mode,
        )
    return replay_architecture_population(base / "evolution", population_id)


__all__ = (
    "STAGES",
    "confirmation_arms",
    "replay_wagner_ph_architecture",
    "run_wagner_ph_architecture_campaign",
    "verify_wagner_ph_architecture_campaign",
    "wagner_ph_architecture_status",
)
