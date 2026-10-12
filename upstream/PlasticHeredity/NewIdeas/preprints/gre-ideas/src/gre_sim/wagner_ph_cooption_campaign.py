"""Six-hour-bounded orchestration for Wagner PH carrier meaning and co-option."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import os
import time
from dataclasses import replace
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
from .wagner_ph_cooption_analysis import (
    analyze_meaning_atlas,
    render_report,
)
from .wagner_ph_cooption_audit import (
    replay_cooption_audit_population,
    run_cooption_audit,
    verify_cooption_audit,
)
from .wagner_ph_cooption_config import (
    COOPTION_ATLAS_RESULT_FORMAT,
    COOPTION_CAMPAIGN_FORMAT,
    COOPTION_TASK_FORMAT,
    CooptionSpec,
    matched_direct,
)
from .wagner_ph_cooption_evolution import (
    deserialize_genotype,
    mutate_genotype,
    replay_cooption_population,
    run_cooption_evolution,
    verify_cooption_evolution,
)
from .wagner_ph_cooption_experiment import (
    simulate_ecology_condition,
    sample_cooption_task,
    simulate_meaning_task,
    validate_task,
)
from .wagner_ph_cooption_protocols import wagner_ph_cooption_spec
from .wagner_ph_ladder_campaign import verify_wagner_ph_ladder_campaign


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


def _parent_provenance(parent: Path, spec: CooptionSpec) -> dict[str, Any]:
    parent = parent.resolve()
    verification = verify_wagner_ph_ladder_campaign(parent)
    registration = read_json(parent / "registration.json")
    if registration["protocol"]["cohort_id"] != spec.parent_cohort_id:
        raise ValueError("co-option parent is not the registered Origin Ladder cohort")
    result = {
        "format": "gre-wagner-ph-cooption-parent-v1",
        "parent": str(parent),
        "parent_checksum_digest": sha256_file(parent / "SHA256SUMS"),
        "parent_manifest_digest": canonical_digest(
            read_json(parent / "campaign-manifest.json")
        ),
        "parent_verification": verification,
        "role": "sealed evidence and anchor provenance only; fresh tasks are outcome blind",
        "origin_ladder_confirmation_reserve_remains_untouched": True,
    }
    result["provenance_digest"] = canonical_digest(result)
    return result


def _soft_deadline(started_epoch: float, spec: CooptionSpec) -> float:
    registered = os.environ.get("GRE_WAGNER_PH_COOPTION_SOFT_DEADLINE_EPOCH")
    if registered is None:
        return started_epoch + spec.soft_wall_seconds
    try:
        return float(registered)
    except ValueError as error:
        raise ValueError("invalid co-option soft deadline") from error


def _prior_consumed_seconds() -> float:
    registered = os.environ.get("GRE_WAGNER_PH_COOPTION_PRIOR_CONSUMED_SECONDS", "0")
    try:
        value = float(registered)
    except ValueError as error:
        raise ValueError("invalid co-option prior consumed time") from error
    if value < 0.0:
        raise ValueError("co-option prior consumed time cannot be negative")
    return value


def _require_stage_budget(deadline: float, reservation: int, stage: str) -> None:
    if deadline - time.time() < reservation:
        raise TimeoutError(
            f"insufficient registered soft-wall reserve to start {stage} "
            f"(requires {reservation} seconds)"
        )


def _write_progress(
    destination: Path,
    stage: str,
    completed: int,
    total: int,
    started: float,
    eta: float | None = None,
) -> None:
    elapsed = max(time.monotonic() - started, 0.0)
    rate = completed / elapsed if completed and elapsed else 0.0
    _atomic_json(
        destination / "progress.json",
        {
            "format": "gre-wagner-ph-cooption-progress-v1",
            "stage": stage,
            "completed_units": completed,
            "total_units": total,
            "elapsed_seconds": elapsed,
            "units_per_second": rate,
            "eta_seconds": eta if eta is not None else ((total - completed) / rate if rate else None),
        },
    )


def _runtime_benchmark(spec: CooptionSpec, destination: Path) -> dict[str, Any]:
    """Run one disjoint smoke atlas task for an operational throughput record."""

    path = destination / "runtime-benchmark.json"
    if path.is_file():
        return read_json(path)
    smoke = replace(
        spec.smoke(),
        master_seed=canonical_digest((spec.master_seed, "runtime-benchmark-smoke")),
        confirmation_seed=canonical_digest(
            (spec.confirmation_seed, "runtime-benchmark-unused-confirmation")
        ),
    )
    smoke.validate()
    task = sample_cooption_task(smoke, 0, "runtime-benchmark")
    started = time.monotonic()
    result = simulate_meaning_task(task, smoke.to_dict())
    elapsed = time.monotonic() - started
    benchmark = {
        "format": "gre-wagner-ph-cooption-runtime-benchmark-v1",
        "scientific_evidence": False,
        "seed_is_disjoint_from_production": smoke.master_seed != spec.master_seed,
        "smoke_protocol_digest": canonical_digest(smoke.to_dict()),
        "task_digest": task["task_digest"],
        "result_digest": result["result_digest"],
        "elapsed_seconds_single_worker": elapsed,
        "production_dimensions_are_not_adapted_from_benchmark": True,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "maximum_workers": spec.maximum_workers,
    }
    _atomic_json(path, benchmark)
    return benchmark


def _atlas_iterator(
    tasks: list[dict[str, Any]], spec: CooptionSpec, workers: int
) -> tuple[Iterator[tuple[dict[str, Any], dict[str, Any]]], concurrent.futures.ProcessPoolExecutor | None]:
    if workers == 1:
        return (
            ((task, simulate_meaning_task(task, spec.to_dict())) for task in tasks),
            None,
        )
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    )
    futures = {
        executor.submit(simulate_meaning_task, task, spec.to_dict()): task
        for task in tasks
    }
    return (
        ((futures[future], future.result()) for future in concurrent.futures.as_completed(futures)),
        executor,
    )


def _run_meaning_atlas(
    spec: CooptionSpec,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None,
    campaign_started: float,
) -> tuple[Path, dict[str, Any]]:
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_meaning_atlas(destination, spec)
        return destination, read_json(destination / "analysis.json")
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": "gre-wagner-ph-cooption-atlas-registration-v1",
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "tasks_are_fresh_and_outcome_blind": True,
        "neutral_pre_cue_state_is_shared_between_histories": True,
        "independent_donor_is_balanced_and_recipient_independent": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing meaning-atlas registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    tasks_path = destination / "tasks.json"
    if tasks_path.is_file():
        registry = read_json(tasks_path)
        if (
            registry.get("format")
            != "gre-wagner-ph-cooption-atlas-task-registry-v1"
            or registry.get("protocol_digest") != protocol_digest
            or registry.get("task_registry_digest")
            != canonical_digest(registry.get("tasks", []))
        ):
            raise ValueError("existing meaning-atlas task registry differs")
        tasks = list(registry["tasks"])
    else:
        tasks = [
            sample_cooption_task(spec, index, "meaning-atlas")
            for index in range(spec.atlas_tasks)
        ]
        registry = {
            "format": "gre-wagner-ph-cooption-atlas-task-registry-v1",
            "protocol_digest": protocol_digest,
            "tasks": tasks,
            "task_count": len(tasks),
            "task_registry_digest": canonical_digest(tasks),
        }
        _atomic_json(tasks_path, registry)
    if len(tasks) != spec.atlas_tasks:
        raise ValueError("meaning-atlas task count differs from protocol")
    for task in tasks:
        validate_task(task)
    shards = destination / "task-results"
    shards.mkdir(exist_ok=True)
    complete: dict[str, dict[str, Any]] = {}
    for task in tasks:
        path = shards / f"{task['task_id']}.json"
        if not path.is_file():
            continue
        value = read_json(path)
        if (
            value.get("format") == COOPTION_ATLAS_RESULT_FORMAT
            and value.get("task_digest") == task["task_digest"]
        ):
            _payload_digest(value, "result_digest")
            complete[str(task["task_id"])] = value
    missing = [task for task in tasks if task["task_id"] not in complete]
    iterator, executor = _atlas_iterator(missing, spec, workers)
    atlas_started = time.monotonic()
    try:
        for task, result in iterator:
            _payload_digest(result, "result_digest")
            _atomic_json(shards / f"{task['task_id']}.json", result)
            complete[str(task["task_id"])] = result
            elapsed = time.monotonic() - atlas_started
            rate = len(complete) / max(elapsed, 1e-9)
            _write_progress(
                destination.parent,
                "meaning-atlas",
                len(complete),
                len(tasks),
                campaign_started,
                (len(tasks) - len(complete)) / rate if rate else None,
            )
            if progress:
                progress(f"carrier-meaning atlas {len(complete)}/{len(tasks)} tasks")
    finally:
        if executor is not None:
            executor.shutdown()
    ordered = [complete[str(task["task_id"])] for task in tasks]
    analysis = analyze_meaning_atlas(ordered, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": "gre-wagner-ph-cooption-atlas-manifest-v1",
            "protocol_digest": protocol_digest,
            "task_registry_digest": registry["task_registry_digest"],
            "task_count": len(tasks),
            "elapsed_seconds": time.monotonic() - atlas_started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_meaning_atlas(destination, spec)
    return destination, analysis


def verify_meaning_atlas(directory: Path, spec: CooptionSpec) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    registry = read_json(directory / "tasks.json")
    manifest = read_json(directory / "manifest.json")
    digest = canonical_digest(spec.to_dict())
    if registration.get("format") != "gre-wagner-ph-cooption-atlas-registration-v1":
        raise ValueError("meaning-atlas registration format mismatch")
    if registration.get("protocol_digest") != digest or canonical_digest(
        registration.get("protocol")
    ) != digest:
        raise ValueError("meaning-atlas protocol digest mismatch")
    if manifest.get("format") != "gre-wagner-ph-cooption-atlas-manifest-v1" or manifest.get(
        "protocol_digest"
    ) != digest:
        raise ValueError("meaning-atlas manifest mismatch")
    tasks = list(registry.get("tasks", []))
    if (
        registry.get("protocol_digest") != digest
        or registry.get("task_registry_digest") != canonical_digest(tasks)
        or len(tasks) != spec.atlas_tasks
        or int(manifest.get("task_count", -1)) != spec.atlas_tasks
        or manifest.get("task_registry_digest") != registry.get("task_registry_digest")
    ):
        raise ValueError("meaning-atlas task registry mismatch")
    for task in tasks:
        validate_task(task)
        result = read_json(directory / "task-results" / f"{task['task_id']}.json")
        _payload_digest(result, "result_digest")
        if result.get("task_digest") != task["task_digest"]:
            raise ValueError("meaning-atlas task/result mismatch")
    return {"verified": True, "tasks": len(tasks), "checksums": len(checksums)}


def run_wagner_ph_cooption_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    spec = wagner_ph_cooption_spec(smoke=smoke)
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("co-option campaign permits one to four CPU workers")
    destination = destination.resolve()
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_cooption_campaign(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    started_monotonic = time.monotonic()
    started_epoch = time.time()
    deadline = _soft_deadline(started_epoch, spec)
    prior_consumed = _prior_consumed_seconds()
    provenance = _parent_provenance(parent, spec)
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": COOPTION_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "parent_provenance_digest": provenance["provenance_digest"],
        "cpu_only": True,
        "confirmation_authorized": False,
        "confirmation_rng_draws_consumed": 0,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
    }
    for path, value in (
        (destination / "registration.json", registration),
        (destination / "parent-provenance.json", provenance),
    ):
        if path.is_file() and read_json(path) != value:
            raise ValueError(f"existing co-option {path.name} differs")
        if not path.is_file():
            _atomic_json(path, value)

    benchmark = _runtime_benchmark(spec, destination)

    atlas_dir = destination / "meaning-atlas"
    if not (atlas_dir / "SHA256SUMS").is_file():
        _require_stage_budget(deadline, spec.stage_reservations_seconds[0], "meaning atlas")
    if progress:
        progress("starting fresh carrier-meaning decomposition")
    _, atlas_analysis = _run_meaning_atlas(
        spec, atlas_dir, workers, progress, started_monotonic
    )

    evolution_dir = destination / "evolution"
    if not (evolution_dir / "SHA256SUMS").is_file():
        _require_stage_budget(deadline, spec.stage_reservations_seconds[1], "co-option evolution")
    _write_progress(destination, "evolution", 0, spec.population_count, started_monotonic)
    if progress:
        progress("starting eight-arm performance-only co-option evolution")
    run_cooption_evolution(spec, evolution_dir, workers, progress)

    audit_dir = destination / "audit"
    if not (audit_dir / "SHA256SUMS").is_file():
        _require_stage_budget(deadline, spec.stage_reservations_seconds[2], "causal audit")
    _write_progress(destination, "causal-audit", 0, spec.population_count, started_monotonic)
    if progress:
        progress("starting untouched carrier-content and mechanism audit")
    run_cooption_audit(spec, evolution_dir, audit_dir, workers, progress)
    audit_analysis = read_json(audit_dir / "analysis.json")

    _require_stage_budget(deadline, spec.stage_reservations_seconds[3], "analysis and sealing")
    combined = {
        "format": "gre-wagner-ph-cooption-combined-analysis-v1",
        "meaning_atlas": atlas_analysis,
        "evolution": read_json(evolution_dir / "analysis.json"),
        "audit": audit_analysis,
        "nomination": audit_analysis.get("nomination"),
        "confirmation_reserve": audit_analysis["confirmation_reserve"],
    }
    combined["analysis_digest"] = canonical_digest(combined)
    _atomic_json(destination / "analysis.json", combined)
    _atomic_json(
        destination / "confirmation-reserve.json",
        {
            **audit_analysis["confirmation_reserve"],
            "format": "gre-wagner-ph-cooption-confirmation-reserve-v1",
            "exploration_analysis_digest": combined["analysis_digest"],
            "note": "No confirmation founder, environment, mutation, or assay stream has been generated.",
        },
    )
    elapsed = time.monotonic() - started_monotonic
    cumulative = prior_consumed + elapsed
    manifest = {
        "format": COOPTION_CAMPAIGN_FORMAT,
        "protocol_digest": protocol_digest,
        "parent_provenance_digest": provenance["provenance_digest"],
        "atlas_checksum_digest": sha256_file(atlas_dir / "SHA256SUMS"),
        "evolution_checksum_digest": sha256_file(evolution_dir / "SHA256SUMS"),
        "audit_checksum_digest": sha256_file(audit_dir / "SHA256SUMS"),
        "analysis_digest": combined["analysis_digest"],
        "runtime_benchmark_digest": canonical_digest(benchmark),
        "atlas_tasks": spec.atlas_tasks,
        "evolution_populations": spec.population_count,
        "maximum_workers": workers,
        "cpu_only": True,
        "elapsed_seconds": elapsed,
        "prior_consumed_seconds": prior_consumed,
        "cumulative_wall_seconds": cumulative,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_six_hour_boundary": cumulative <= spec.hard_wall_seconds,
        "confirmation_status": audit_analysis["confirmation_reserve"]["status"],
        "confirmation_rng_draws_consumed": 0,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    (destination / "report.md").write_text(
        render_report(atlas_analysis, audit_analysis), encoding="utf-8"
    )
    _write_progress(destination, "sealing", 1, 1, started_monotonic)
    write_checksums(destination)
    verify_wagner_ph_cooption_campaign(destination)
    if progress:
        progress("sealed and independently verified Wagner PH co-option exploration")
    return destination


def verify_wagner_ph_cooption_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    provenance = read_json(directory / "parent-provenance.json")
    manifest = read_json(directory / "campaign-manifest.json")
    analysis = read_json(directory / "analysis.json")
    reserve = read_json(directory / "confirmation-reserve.json")
    benchmark = read_json(directory / "runtime-benchmark.json")
    if registration.get("format") != COOPTION_CAMPAIGN_FORMAT or manifest.get("format") != COOPTION_CAMPAIGN_FORMAT:
        raise ValueError("co-option campaign format mismatch")
    spec = CooptionSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("co-option campaign protocol digest mismatch")
    _payload_digest(provenance, "provenance_digest")
    if provenance["provenance_digest"] != registration["parent_provenance_digest"]:
        raise ValueError("co-option parent provenance mismatch")
    if sha256_file(Path(provenance["parent"]) / "SHA256SUMS") != provenance["parent_checksum_digest"]:
        raise ValueError("sealed Origin Ladder parent changed")
    atlas = directory / "meaning-atlas"
    verify_meaning_atlas(atlas, spec)
    if sha256_file(atlas / "SHA256SUMS") != manifest["atlas_checksum_digest"]:
        raise ValueError("meaning atlas checksum changed")
    evolution_verification = verify_cooption_evolution(directory / "evolution")
    audit_verification = verify_cooption_audit(directory / "audit")
    archived_analysis = dict(analysis)
    archived_digest = archived_analysis.pop("analysis_digest", None)
    if archived_digest != canonical_digest(archived_analysis) or archived_digest != manifest["analysis_digest"]:
        raise ValueError("co-option combined analysis mismatch")
    if reserve.get("rng_draws_consumed") != 0 or registration.get("confirmation_authorized") is not False:
        raise ValueError("co-option confirmation reserve was consumed during exploration")
    if manifest.get("confirmation_rng_draws_consumed") != 0:
        raise ValueError("co-option manifest reports confirmation RNG use")
    if (
        benchmark.get("scientific_evidence") is not False
        or benchmark.get("seed_is_disjoint_from_production") is not True
        or manifest.get("runtime_benchmark_digest") != canonical_digest(benchmark)
    ):
        raise ValueError("co-option runtime benchmark provenance mismatch")
    return {
        "verified": True,
        "checksums": len(checksums),
        "atlas_tasks": spec.atlas_tasks,
        "evolution": evolution_verification,
        "audit": audit_verification,
        "nomination": analysis.get("nomination"),
        "confirmation_status": reserve["status"],
    }


def wagner_ph_cooption_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    if not directory.exists():
        return {"status": "not-started", "output": str(directory)}
    registration = (
        read_json(directory / "registration.json")
        if (directory / "registration.json").is_file()
        else {}
    )
    confirmation = (
        registration.get("format")
        == "gre-wagner-ph-cooption-confirmation-campaign-v1"
    )
    if (directory / "SHA256SUMS").is_file():
        try:
            verified = (
                verify_wagner_ph_cooption_confirmation(directory)
                if confirmation
                else verify_wagner_ph_cooption_campaign(directory)
            )
            manifest_path = (
                directory / "manifest.json"
                if confirmation
                else directory / "campaign-manifest.json"
            )
            manifest = read_json(manifest_path)
            return {
                "status": "completed",
                **verified,
                "elapsed_seconds": manifest["elapsed_seconds"],
                "cumulative_wall_seconds": manifest.get("cumulative_wall_seconds"),
            }
        except Exception as error:
            return {"status": "sealed-invalid", "error": str(error)}
    progress = read_json(directory / "progress.json") if (directory / "progress.json").is_file() else {}
    stage = str(
        progress.get(
            "stage",
            "causal-audit"
            if confirmation and (directory / "audit").is_dir()
            else "evolution"
            if confirmation and (directory / "evolution").is_dir()
            else "preparing",
        )
    )
    nested = None
    nested_path = (
        directory / "evolution" / "progress.json"
        if stage == "evolution"
        else directory / "audit" / "progress.json"
        if stage == "causal-audit"
        else None
    )
    if nested_path is not None and nested_path.is_file():
        nested = read_json(nested_path)
    return {
        "status": "running-or-resumable",
        "stage": stage,
        "completed_units": (nested or progress).get("completed_populations", progress.get("completed_units")),
        "total_units": (nested or progress).get("total_populations", progress.get("total_units")),
        "elapsed_seconds": (nested or progress).get("elapsed_seconds"),
        "eta_seconds": (nested or progress).get("eta_seconds"),
        "confirmation_status": "untouched",
    }


def replay_wagner_ph_cooption(
    directory: Path, stage: str, identifier: str
) -> dict[str, Any]:
    directory = directory.resolve()
    if stage == "evolution":
        return replay_cooption_population(directory / "evolution", identifier)
    if stage == "audit":
        return replay_cooption_audit_population(directory / "audit", identifier)
    if stage != "atlas":
        raise ValueError("replay stage must be atlas, evolution, or audit")
    spec = CooptionSpec.from_dict(read_json(directory / "registration.json")["protocol"])
    task = next(
        value
        for value in read_json(directory / "meaning-atlas" / "tasks.json")["tasks"]
        if value["task_id"] == identifier
    )
    archived = read_json(directory / "meaning-atlas" / "task-results" / f"{identifier}.json")
    replayed = simulate_meaning_task(task, spec.to_dict())
    return {
        "stage": stage,
        "identifier": identifier,
        "matches": archived["result_digest"] == replayed["result_digest"],
        "archived_digest": archived["result_digest"],
        "replayed_digest": replayed["result_digest"],
    }


def _pedigree_information_score(
    genotype: tuple[Any, Any],
    task: dict[str, Any],
    spec: CooptionSpec,
    task_index: int,
) -> float:
    rulebook, genome = genotype
    scope = f"confirmation-pedigree.population-{task_index:03d}"
    conditions = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            genome,
            spec,
            intervention,
            0.9,
            0.0,
            spec.audit_futures_per_history,
            spec.lineage_generations,
            (spec.lineage_generations,),
            scope,
            master_seed=spec.master_seed,
        )
        for intervention in ("natural", "independent_history")
    }
    generation = str(spec.lineage_generations)
    return float(
        conditions["natural"]["checkpoints"][generation]["correct_rate"]
        - conditions["independent_history"]["checkpoints"][generation]["correct_rate"]
    )


def _run_confirmation_pedigree(
    spec: CooptionSpec,
    evolution: Path,
    treatment: str,
    destination: Path,
) -> dict[str, Any]:
    """Assay exactly 72 descendants from two parents on each of six tasks."""

    architecture = next(
        read_json(path)["mutation_architecture"]
        for path in (evolution / "populations").glob(f"{treatment}.population-*.json")
    )
    rows: list[dict[str, Any]] = []
    for task_index in range(spec.confirmation_tasks):
        archived = read_json(
            evolution / "populations" / f"{treatment}.population-{task_index:03d}.json"
        )
        ranked = sorted(
            archived["final_population"],
            key=lambda value: (-float(value["training_score"]["fitness"]), value["genotype_id"]),
        )[:2]
        task = archived["task"]
        for parent_index, parent_value in enumerate(ranked):
            parent = deserialize_genotype(parent_value)
            parent_score = _pedigree_information_score(parent, task, spec, task_index)
            for child_index in range(2):
                child = mutate_genotype(
                    parent,
                    parent,
                    architecture,
                    np.random.default_rng(
                        int(
                            canonical_digest(
                                (
                                    spec.master_seed,
                                    "pedigree-child",
                                    task_index,
                                    parent_index,
                                    child_index,
                                )
                            )[:16],
                            16,
                        )
                    ),
                )
                child_score = _pedigree_information_score(child, task, spec, task_index)
                rows.append(
                    {
                        "task_index": task_index,
                        "parent_index": parent_index,
                        "child_index": child_index,
                        "grandchild_index": None,
                        "pedigree_generation": 1,
                        "parent_information": parent_score,
                        "descendant_information": child_score,
                        "retained": parent_score > 0.0
                        and child_score >= spec.pedigree_retention_gate * parent_score,
                    }
                )
                for grandchild_index in range(2):
                    grandchild = mutate_genotype(
                        child,
                        child,
                        architecture,
                        np.random.default_rng(
                            int(
                                canonical_digest(
                                    (
                                        spec.master_seed,
                                        "pedigree-grandchild",
                                        task_index,
                                        parent_index,
                                        child_index,
                                        grandchild_index,
                                    )
                                )[:16],
                                16,
                            )
                        ),
                    )
                    grandchild_score = _pedigree_information_score(
                        grandchild, task, spec, task_index
                    )
                    rows.append(
                        {
                            "task_index": task_index,
                            "parent_index": parent_index,
                            "child_index": child_index,
                            "grandchild_index": grandchild_index,
                            "pedigree_generation": 2,
                            "parent_information": parent_score,
                            "descendant_information": grandchild_score,
                            "retained": parent_score > 0.0
                            and grandchild_score
                            >= spec.pedigree_retention_gate * parent_score,
                        }
                    )
    if len(rows) != 72:
        raise RuntimeError(f"confirmation pedigree produced {len(rows)} descendants; expected 72")
    centered_x: list[float] = []
    centered_y: list[float] = []
    for task_index in range(spec.confirmation_tasks):
        chosen = [value for value in rows if value["task_index"] == task_index]
        xs = np.asarray([value["parent_information"] for value in chosen], dtype=float)
        ys = np.asarray([value["descendant_information"] for value in chosen], dtype=float)
        centered_x.extend((xs - np.mean(xs)).tolist())
        centered_y.extend((ys - np.mean(ys)).tolist())
    x = np.asarray(centered_x, dtype=float)
    y = np.asarray(centered_y, dtype=float)
    denominator = float(np.sum(x * x))
    slope = float(np.sum(x * y) / denominator) if denominator > 0.0 else None
    retention = float(np.mean([value["retained"] for value in rows]))
    result = {
        "format": "gre-wagner-ph-cooption-confirmation-pedigree-v1",
        "treatment": treatment,
        "parents_per_task": 2,
        "children_per_parent": 2,
        "grandchildren_per_child": 2,
        "descendant_genotypes": len(rows),
        "retention_definition": "descendant information effect >= 0.70 times its root parent's effect",
        "retention_fraction": retention,
        "task_centered_parent_offspring_slope": slope,
        "passes": bool(
            retention >= spec.pedigree_retention_gate
            and slope is not None
            and slope > 0.0
        ),
        "rows": rows,
    }
    result["pedigree_digest"] = canonical_digest(result)
    _atomic_json(destination, result)
    return result


def run_wagner_ph_cooption_confirmation(
    exploration: Path,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None,
    *,
    authorized: bool,
) -> Path:
    """Run a frozen fresh-seed confirmation only after an explicit authorization."""

    if not authorized:
        raise PermissionError("confirmation requires --authorize-confirmation")
    exploration = exploration.resolve()
    verify_wagner_ph_cooption_campaign(exploration)
    original = CooptionSpec.from_dict(read_json(exploration / "registration.json")["protocol"])
    nomination = read_json(exploration / "analysis.json").get("nomination")
    if nomination is None:
        raise ValueError("exploration produced no confirmation-eligible finalist")
    selected = str(nomination["treatment"])
    treatments = (
        selected,
        matched_direct(selected),
        "robustness_only_independent",
        "neutral_drift",
    )
    started = time.monotonic()
    confirmation = replace(
        original,
        cohort_id=f"{original.cohort_id}-confirmation",
        master_seed=original.confirmation_seed,
        confirmation_seed=canonical_digest(
            (original.confirmation_seed, "post-confirmation-unused-reserve")
        ),
        evolution_tasks=original.confirmation_tasks,
    )
    confirmation.validate()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    registration = {
        "format": "gre-wagner-ph-cooption-confirmation-campaign-v1",
        "protocol": confirmation.to_dict(),
        "exploration": str(exploration),
        "exploration_checksum": sha256_file(exploration / "SHA256SUMS"),
        "nomination": nomination,
        "treatments": list(treatments),
        "confirmation_authorized": True,
        "protocol_frozen_without_tuning": True,
    }
    path = destination / "registration.json"
    if path.is_file() and read_json(path) != registration:
        raise ValueError("existing confirmation registration differs")
    if not path.is_file():
        _atomic_json(path, registration)
    confirmation_deadline_text = os.environ.get(
        "GRE_WAGNER_PH_COOPTION_CONFIRM_SOFT_DEADLINE_EPOCH"
    )
    confirmation_deadline = (
        float(confirmation_deadline_text)
        if confirmation_deadline_text is not None
        else time.time() + confirmation.confirmation_soft_wall_seconds
    )
    if not (destination / "evolution" / "SHA256SUMS").is_file():
        _require_stage_budget(confirmation_deadline, 9600, "confirmation evolution")
    run_cooption_evolution(
        confirmation,
        destination / "evolution",
        workers,
        progress,
        treatments=treatments,
        task_count=confirmation.confirmation_tasks,
        master_seed=confirmation.master_seed,
    )
    if not (destination / "audit" / "SHA256SUMS").is_file():
        _require_stage_budget(confirmation_deadline, 3300, "confirmation causal audit")
    run_cooption_audit(
        confirmation, destination / "evolution", destination / "audit", workers, progress
    )
    audit = read_json(destination / "audit" / "analysis.json")
    replicated = bool(
        audit.get("nomination") and audit["nomination"]["treatment"] == selected
    )
    _require_stage_budget(confirmation_deadline, 600, "confirmation pedigree and sealing")
    pedigree = (
        _run_confirmation_pedigree(
            confirmation,
            destination / "evolution",
            selected,
            destination / "pedigree.json",
        )
        if replicated
        else None
    )
    _atomic_json(
        destination / "analysis.json",
        {
            "format": "gre-wagner-ph-cooption-confirmation-analysis-v1",
            "exploration_nomination": nomination,
            "audit": audit,
            "replicated": replicated,
            "pedigree": pedigree,
            "pedigree_status": "completed" if pedigree is not None else "not-run-no-replication",
        },
    )
    _atomic_json(
        destination / "manifest.json",
        {
            "format": "gre-wagner-ph-cooption-confirmation-campaign-v1",
            "populations": len(treatments) * confirmation.confirmation_tasks,
            "hard_wall_seconds": confirmation.confirmation_hard_wall_seconds,
            "soft_wall_seconds": confirmation.confirmation_soft_wall_seconds,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_wagner_ph_cooption_confirmation(destination)
    return destination


def verify_wagner_ph_cooption_confirmation(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != "gre-wagner-ph-cooption-confirmation-campaign-v1":
        raise ValueError("co-option confirmation registration format mismatch")
    if manifest.get("format") != "gre-wagner-ph-cooption-confirmation-campaign-v1":
        raise ValueError("co-option confirmation manifest format mismatch")
    if registration.get("confirmation_authorized") is not True:
        raise ValueError("co-option confirmation lacks explicit authorization")
    if sha256_file(Path(registration["exploration"]) / "SHA256SUMS") != registration[
        "exploration_checksum"
    ]:
        raise ValueError("sealed exploration changed after confirmation")
    evolution = verify_cooption_evolution(directory / "evolution")
    audit = verify_cooption_audit(directory / "audit")
    expected = len(registration["treatments"]) * int(manifest["populations"] / len(registration["treatments"]))
    if evolution["populations"] != expected or audit["populations"] != expected:
        raise ValueError("confirmation population count mismatch")
    if analysis["pedigree_status"] == "completed":
        pedigree = read_json(directory / "pedigree.json")
        archived = dict(pedigree)
        digest = archived.pop("pedigree_digest", None)
        if digest != canonical_digest(archived) or pedigree["descendant_genotypes"] != 72:
            raise ValueError("confirmation pedigree mismatch")
    return {
        "verified": True,
        "checksums": len(checksums),
        "populations": expected,
        "replicated": bool(analysis["replicated"]),
        "pedigree_status": analysis["pedigree_status"],
    }
