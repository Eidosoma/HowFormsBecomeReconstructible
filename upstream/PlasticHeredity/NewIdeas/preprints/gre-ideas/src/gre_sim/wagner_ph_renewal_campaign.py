"""Six-hour guarded orchestration for Wagner PH renewal/evolvability v1."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .artifacts import (
    canonical_digest,
    read_json,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .local_ph_study import replay_local_future, run_local_study, verify_local_study
from .wagner_ph_bridge_campaign import verify_wagner_ph_bridge_campaign
from .wagner_ph_renewal_analysis import (
    analyze_renewal_frontier_path,
    render_frontier_report,
)
from .wagner_ph_renewal_config import (
    RENEWAL_CAMPAIGN_FORMAT,
    RENEWAL_FRONTIER_FORMAT,
    RenewalCampaignSpec,
)
from .wagner_ph_renewal_evolution import (
    replay_renewal_audit_population,
    replay_renewal_population,
    run_renewal_audit,
    run_renewal_evolution,
    verify_renewal_audit,
    verify_renewal_evolution,
)
from .wagner_ph_renewal_protocols import (
    renewal_campaign_spec,
    selected_evolution_spec,
)


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _parent_provenance(parent: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    parent = parent.resolve()
    verification = verify_wagner_ph_bridge_campaign(parent)
    selection_path = parent / "evolution-selection.json"
    seal_path = parent / "SHA256SUMS"
    if not selection_path.is_file() or not seal_path.is_file():
        raise FileNotFoundError("renewal campaign requires the sealed Wagner-PH bridge")
    selection = read_json(selection_path)
    provenance = {
        "format": "gre-wagner-ph-renewal-parent-provenance-v1",
        "parent": str(parent),
        "parent_checksum_digest": sha256_file(seal_path),
        "parent_selection_digest": sha256_file(selection_path),
        "parent_verdict": verification["verdict"],
        "parent_is_read_only": True,
        "historical_verdicts_are_immutable": True,
        "claim_boundary": (
            "This campaign probes renewal dependence and evolvability of an engineered local "
            "carrier. It does not revise sealed bridge verdicts or establish a natural origin."
        ),
    }
    provenance["provenance_digest"] = canonical_digest(provenance)
    return provenance, selection


def prediction_ledger() -> dict[str, Any]:
    """Predictions frozen before frontier or evolution results are read."""

    return {
        "format": "gre-wagner-ph-renewal-prediction-ledger-v1",
        "frozen_before_new_data": True,
        "predictions": {
            "P1": {
                "statement": "Nominal copying will not require active descendant renewal.",
                "test": "the selected renewal frontier is gentler than nominal is false",
            },
            "P2": {
                "statement": "A damaged-copy environment will create a positive renewal contrast.",
                "test": "at least one registered frontier cell qualifies",
            },
            "P3": {
                "statement": "The smallest qualifying carrier will use at most seven loci.",
                "test": "frontier selected capacity is at most seven",
            },
            "P4": {
                "statement": "Renewal selection will beat memory-only, acute, and neutral controls.",
                "test": "all three primary held-out paired contrasts pass",
            },
            "P5": {
                "statement": "Renewal phenotype will persist through mutation without a Pearson gate.",
                "test": "clustered slope lower bound is positive and retention lower bound is at least 0.70",
            },
            "P6": {
                "statement": "Unconstrained doubled carrier cost can favor median k at most five.",
                "test": "the high-cost arm is both fully passing and has median k at most five",
            },
        },
    }


def _write_progress(
    root: Path,
    stage: str,
    message: str,
    started_epoch: float,
    prior_consumed: float,
    spec: RenewalCampaignSpec,
    effective_hard_seconds: float,
    effective_soft_seconds: float,
    amendment: dict[str, Any] | None,
) -> None:
    _atomic_json(
        root / "progress.json",
        {
            "format": "gre-wagner-ph-renewal-progress-v1",
            "active_stage": stage,
            "message": message,
            "run_started_epoch": started_epoch,
            "prior_consumed_seconds": prior_consumed,
            "elapsed_seconds": prior_consumed + time.time() - started_epoch,
            "hard_wall_seconds": effective_hard_seconds,
            "soft_wall_seconds": effective_soft_seconds,
            "original_hard_wall_seconds": spec.hard_wall_seconds,
            "completion_extension_active": amendment is not None,
            "completion_extension_seconds": int(amendment["extension_hard_seconds"])
            if amendment
            else 0,
            "projected_wall_seconds": spec.projected_wall_seconds,
        },
    )


def _extension_digest(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("amendment_digest", None)
    return canonical_digest(payload)


def prepare_completion_extension(
    destination: Path,
    spec: RenewalCampaignSpec,
    *,
    original_consumed_seconds: int,
    extension_hard_seconds: int = 7200,
    extension_soft_seconds: int = 6600,
) -> dict[str, Any]:
    """Register an operational extension without rewriting the six-hour failure."""

    destination = destination.resolve()
    if extension_hard_seconds != 7200 or extension_soft_seconds != 6600:
        raise ValueError("renewal completion extension is frozen at 7200/6600 seconds")
    if not spec.soft_wall_seconds <= original_consumed_seconds <= spec.hard_wall_seconds:
        raise ValueError("completion extension requires an exhausted original attempt")
    registration_path = destination / "registration.json"
    if not registration_path.is_file() or (destination / "SHA256SUMS").is_file():
        raise ValueError("completion extension requires an unsealed registered campaign")
    amendment_path = destination / "runtime-extension-registration.json"
    if amendment_path.is_file():
        amendment = read_json(amendment_path)
        if amendment.get("amendment_digest") != _extension_digest(amendment):
            raise ValueError("renewal completion-extension digest mismatch")
        expected = (
            original_consumed_seconds,
            extension_hard_seconds,
            extension_soft_seconds,
        )
        observed = (
            int(amendment["original_consumed_seconds"]),
            int(amendment["extension_hard_seconds"]),
            int(amendment["extension_soft_seconds"]),
        )
        if observed != expected:
            raise ValueError("existing renewal completion extension differs")
        return amendment
    units = destination / "heldout-mutation-audit" / "populations"
    treatment_counts = {
        treatment: len(list(units.glob(f"{treatment}.population-*.json")))
        for treatment in (
            "renewal_standard_cost",
            "renewal_high_cost",
            "renewal_k5_feasibility",
            "memory_standard_cost",
            "acute_standard_cost",
            "neutral_drift",
        )
    }
    amendment = {
        "format": "gre-wagner-ph-renewal-runtime-extension-v1",
        "registered_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "original_registration_digest": canonical_digest(read_json(registration_path)),
        "original_attempt_status": "time-budget-exhausted",
        "original_hard_wall_seconds": spec.hard_wall_seconds,
        "original_soft_wall_seconds": spec.soft_wall_seconds,
        "original_consumed_seconds": original_consumed_seconds,
        "extension_hard_seconds": extension_hard_seconds,
        "extension_soft_seconds": extension_soft_seconds,
        "total_cumulative_authorized_seconds": original_consumed_seconds
        + extension_hard_seconds,
        "completed_audit_files_before_extension": sum(treatment_counts.values()),
        "completed_audit_files_by_treatment": treatment_counts,
        "scientific_outcomes_examined_before_extension": False,
        "operational_information_examined": (
            "stage completion, timestamps, treatment filenames, and runtime only"
        ),
        "reason": (
            "the frozen runtime projection underestimated the final audit; resume only "
            "already registered computations without changing seeds, samples, gates, or analyses"
        ),
        "claim_boundary": (
            "Any completed verdict is an extension-completed exploratory result and did "
            "not complete under the original six-hour operational boundary."
        ),
        "user_authorized_resume": True,
    }
    amendment["amendment_digest"] = _extension_digest(amendment)
    _atomic_json(amendment_path, amendment)
    return amendment


def _run_frontier(
    directory: Path,
    spec: RenewalCampaignSpec,
    workers: int,
    progress: Callable[[str], None],
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "SHA256SUMS").is_file():
        _verify_frontier(directory)
        return read_json(directory / "analysis.json")
    started = time.monotonic()
    run_local_study(spec.frontier.study, directory / "study", workers, progress)
    analysis = analyze_renewal_frontier_path(
        directory / "study" / "futures.jsonl.gz", spec.frontier
    )
    _atomic_json(directory / "analysis.json", analysis)
    _atomic_json(directory / "selection.json", analysis["selection"])
    (directory / "report.md").write_text(
        render_frontier_report(analysis), encoding="utf-8"
    )
    local_manifest = read_json(directory / "study" / "manifest.json")
    _atomic_json(
        directory / "manifest.json",
        {
            "format": RENEWAL_FRONTIER_FORMAT,
            "protocol_digest": canonical_digest(spec.frontier.to_dict()),
            "analysis_digest": canonical_digest(analysis),
            "record_count": int(local_manifest["record_count"]),
            "elapsed_seconds": time.monotonic() - started,
        },
    )
    write_checksums(directory)
    _verify_frontier(directory)
    return analysis


def _verify_frontier(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    manifest = read_json(directory / "manifest.json")
    if manifest.get("format") != RENEWAL_FRONTIER_FORMAT:
        raise ValueError("renewal frontier manifest mismatch")
    verification = verify_local_study(directory / "study")
    analysis = read_json(directory / "analysis.json")
    if canonical_digest(analysis) != manifest.get("analysis_digest"):
        raise ValueError("renewal frontier analysis digest mismatch")
    if canonical_digest(read_json(directory / "selection.json")) != canonical_digest(
        analysis["selection"]
    ):
        raise ValueError("renewal frontier frozen selection mismatch")
    return {
        "verified": True,
        "records": verification["records"],
        "checksums": len(checksums),
    }


def _score_predictions(frontier: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    selection = frontier["selection"]
    standard = audit["renewal_treatments"]["renewal_standard_cost"]
    high = audit["renewal_treatments"]["renewal_high_cost"]
    return {
        "P1": selection["selected_environment"] != "nominal",
        "P2": bool(frontier["verdict"]["renewal_frontier_found"]),
        "P3": int(selection["selected_capacity"]) <= 7,
        "P4": all(
            standard["criteria"][key]
            for key in (
                "beats_memory_by_at_least_0_05_with_positive_lower",
                "beats_acute_by_at_least_0_05_with_positive_lower",
                "beats_neutral_by_at_least_0_05_with_positive_lower",
            )
        ),
        "P5": standard["criteria"][
            "clustered_parent_offspring_slope_lower_above_zero"
        ]
        and standard["criteria"]["offspring_retention_lower_at_least_0_70"],
        "P6": bool(
            high["passed"]
            and float(audit["treatments"]["renewal_high_cost"]["median_selected_capacity"])
            <= 5.0
        ),
    }


def run_wagner_ph_renewal_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
    completion_extension: bool = False,
    original_consumed_seconds: int | None = None,
    extension_hard_seconds: int = 7200,
    extension_soft_seconds: int = 6600,
) -> Path:
    if workers < 1 or workers > 4:
        raise ValueError("Wagner PH renewal permits one to four workers")
    parent = parent.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_renewal_campaign(destination)
        return destination
    provenance, prior_selection = _parent_provenance(parent)
    spec = renewal_campaign_spec(prior_selection, smoke=smoke)
    if spec.projected_wall_seconds > spec.soft_wall_seconds:
        raise RuntimeError("projected renewal campaign runtime exceeds soft wall budget")
    provenance_path = destination / "parent-provenance.json"
    if provenance_path.is_file() and canonical_digest(
        read_json(provenance_path)
    ) != canonical_digest(provenance):
        raise ValueError("existing renewal parent provenance differs")
    if not provenance_path.is_file():
        _atomic_json(provenance_path, provenance)
    ledger = prediction_ledger()
    registration = {
        "format": RENEWAL_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
        "prediction_ledger": ledger,
        "prediction_ledger_digest": canonical_digest(ledger),
        "all_stages_execute_even_after_frontier_fallback": True,
        "fallback_cannot_pass_primary_frontier_gate": True,
        "selected_environment_and_carrier_freeze_before_evolution": True,
        "heldout_seed_is_untouched_by_selection": True,
        "hard_k5_arm_is_engineering_feasibility_only": True,
        "historical_parent_verdicts_unchanged": True,
        "maximum_workers": 4,
        "hard_wall_seconds": 21_600,
        "runtime_projection": {
            "projected_seconds": spec.projected_wall_seconds,
            "basis": (
                "scaled from sealed bridge: 524288 local records in 2715 s, "
                "32 paired populations in 3545 s, plus high-precision audit reserve"
            ),
            "must_not_exceed_soft_seconds": spec.soft_wall_seconds,
        },
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(
        read_json(registration_path)
    ) != canonical_digest(registration):
        raise ValueError("existing renewal campaign registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    amendment: dict[str, Any] | None = None
    if completion_extension:
        if original_consumed_seconds is None:
            raise ValueError("completion extension requires original consumed seconds")
        amendment = prepare_completion_extension(
            destination,
            spec,
            original_consumed_seconds=original_consumed_seconds,
            extension_hard_seconds=extension_hard_seconds,
            extension_soft_seconds=extension_soft_seconds,
        )
    elif (destination / "runtime-extension-registration.json").is_file():
        amendment = read_json(destination / "runtime-extension-registration.json")
        if amendment.get("amendment_digest") != _extension_digest(amendment):
            raise ValueError("renewal completion-extension digest mismatch")
    started_epoch = time.time()
    if amendment is None:
        prior_consumed = float(
            os.environ.get("GRE_WAGNER_PH_RENEWAL_PRIOR_CONSUMED_SECONDS", "0")
        )
        effective_hard = float(spec.hard_wall_seconds)
        effective_soft = float(spec.soft_wall_seconds)
        soft_deadline = float(
            os.environ.get(
                "GRE_WAGNER_PH_RENEWAL_SOFT_DEADLINE_EPOCH",
                str(started_epoch + max(1.0, effective_soft - prior_consumed)),
            )
        )
    else:
        extension_prior = float(
            os.environ.get(
                "GRE_WAGNER_PH_RENEWAL_EXTENSION_PRIOR_CONSUMED_SECONDS", "0"
            )
        )
        prior_consumed = float(amendment["original_consumed_seconds"]) + extension_prior
        effective_hard = float(amendment["total_cumulative_authorized_seconds"])
        effective_soft = float(amendment["original_consumed_seconds"]) + float(
            amendment["extension_soft_seconds"]
        )
        soft_deadline = float(
            os.environ.get(
                "GRE_WAGNER_PH_RENEWAL_EXTENSION_SOFT_DEADLINE_EPOCH",
                str(
                    started_epoch
                    + max(
                        1.0,
                        float(amendment["extension_soft_seconds"])
                        - extension_prior,
                    )
                ),
            )
        )

    def announce(stage: str, message: str) -> None:
        _write_progress(
            destination,
            stage,
            message,
            started_epoch,
            prior_consumed,
            spec,
            effective_hard,
            effective_soft,
            amendment,
        )
        if progress:
            progress(message)
        if stage != "sealing" and time.time() >= soft_deadline:
            raise TimeoutError("Wagner PH renewal soft wall-time boundary reached")

    announce("renewal-frontier", "starting capacity-by-copy renewal frontier")
    frontier = _run_frontier(
        destination / "renewal-frontier",
        spec,
        workers,
        lambda message: announce("renewal-frontier", message),
    )
    frozen_selection = {
        "format": "gre-wagner-ph-renewal-evolution-selection-v1",
        **frontier["selection"],
        "frontier_analysis_digest": canonical_digest(frontier),
        "frozen_before_evolution": True,
        "fallback_is_diagnostic_only": not bool(
            frontier["selection"]["primary_frontier_passed"]
        ),
    }
    selection_path = destination / "evolution-selection.json"
    if selection_path.is_file() and canonical_digest(
        read_json(selection_path)
    ) != canonical_digest(frozen_selection):
        raise ValueError("existing renewal evolution selection differs")
    if not selection_path.is_file():
        _atomic_json(selection_path, frozen_selection)
    evolution_spec = selected_evolution_spec(spec, frozen_selection)
    announce("evolution", "starting six-arm paired renewal evolution")
    run_renewal_evolution(
        evolution_spec,
        destination / "evolution",
        workers,
        lambda message: announce("evolution", message),
    )
    announce(
        "heldout-mutation-audit",
        "starting untouched F12-like, causal, and mutation-neighborhood audit",
    )
    run_renewal_audit(
        destination / "evolution",
        spec.mutation_audit,
        destination / "heldout-mutation-audit",
        workers,
        lambda message: announce("heldout-mutation-audit", message),
    )
    audit = read_json(destination / "heldout-mutation-audit" / "analysis.json")
    predictions = _score_predictions(frontier, audit)
    elapsed = prior_consumed + time.time() - started_epoch
    primary_eligible = bool(frontier["selection"]["primary_frontier_passed"])
    verdict = {
        "renewal_frontier_found": primary_eligible,
        "renewal_evolvability_nominated": primary_eligible
        and bool(audit["verdict"]["renewal_evolvability_nominated"]),
        "compact_unconstrained_renewal_nominated": primary_eligible
        and bool(audit["verdict"]["compact_unconstrained_renewal_nominated"]),
        "hard_k5_feasibility_is_engineering_only": True,
    }
    frontier_manifest = read_json(destination / "renewal-frontier" / "manifest.json")
    manifest = {
        "format": RENEWAL_CAMPAIGN_FORMAT,
        "completed": True,
        "all_stages_complete": True,
        "verdict": verdict,
        "prediction_results": predictions,
        "predictions_passed": sum(bool(value) for value in predictions.values()),
        "predictions_total": len(predictions),
        "frontier_records": int(frontier_manifest["record_count"]),
        "evolution_populations": evolution_spec.population_count,
        "mutation_rows": int(
            read_json(destination / "heldout-mutation-audit" / "manifest.json")[
                "mutation_row_count"
            ]
        ),
        "elapsed_seconds": elapsed,
        "hard_wall_seconds": effective_hard,
        "original_hard_wall_seconds": spec.hard_wall_seconds,
        "completed_under_original_six_hour_boundary": amendment is None,
        "completed_under_authorized_extension": amendment is not None,
        "runtime_extension": amendment,
        "historical_parent_verdicts_unchanged": True,
        "claim_boundary": provenance["claim_boundary"],
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    (destination / "report.md").write_text(
        "\n".join(
            (
                "# Wagner PH Renewal and Evolvability v1",
                "",
                f"- Renewal frontier: **{'PASS' if verdict['renewal_frontier_found'] else 'fail'}**",
                f"- Renewal evolvability nomination: **{'PASS' if verdict['renewal_evolvability_nominated'] else 'fail'}**",
                f"- Compact unconstrained nomination: **{'PASS' if verdict['compact_unconstrained_renewal_nominated'] else 'fail'}**",
                f"- Prediction ledger: {manifest['predictions_passed']}/{manifest['predictions_total']} supported",
                f"- Evolution populations: {evolution_spec.population_count}",
                f"- Mutation offspring: {manifest['mutation_rows']}",
                f"- Cumulative wall time: {elapsed:.1f} seconds",
                f"- Completed under original six-hour boundary: `{amendment is None}`",
                f"- Completed under authorized extension: `{amendment is not None}`",
                "",
                "The hard-k5 arm is an engineering feasibility control and cannot establish spontaneous compression.",
                "",
                provenance["claim_boundary"],
                "",
            )
        ),
        encoding="utf-8",
    )
    announce("sealing", "verifying and sealing Wagner PH renewal campaign")
    write_checksums(destination)
    verify_wagner_ph_renewal_campaign(destination)
    if progress:
        progress("sealed Wagner PH renewal campaign")
    return destination


def verify_wagner_ph_renewal_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    if registration.get("format") != RENEWAL_CAMPAIGN_FORMAT or manifest.get(
        "format"
    ) != RENEWAL_CAMPAIGN_FORMAT:
        raise ValueError("Wagner PH renewal campaign format mismatch")
    spec = RenewalCampaignSpec.from_dict(registration["protocol"])
    if canonical_digest(spec.to_dict()) != registration.get("protocol_digest"):
        raise ValueError("Wagner PH renewal campaign protocol digest mismatch")
    if canonical_digest(registration["prediction_ledger"]) != registration.get(
        "prediction_ledger_digest"
    ):
        raise ValueError("Wagner PH renewal prediction ledger digest mismatch")
    _verify_frontier(directory / "renewal-frontier")
    frontier_manifest = read_json(directory / "renewal-frontier" / "manifest.json")
    if frontier_manifest.get("protocol_digest") != canonical_digest(
        spec.frontier.to_dict()
    ):
        raise ValueError("renewal frontier campaign protocol digest mismatch")
    verify_renewal_evolution(directory / "evolution")
    verify_renewal_audit(directory / "heldout-mutation-audit")
    if not manifest.get("all_stages_complete"):
        raise ValueError("partial renewal campaign cannot verify")
    amendment_path = directory / "runtime-extension-registration.json"
    amendment = read_json(amendment_path) if amendment_path.is_file() else None
    allowed_seconds = float(spec.hard_wall_seconds)
    if amendment is not None:
        if amendment.get("format") != "gre-wagner-ph-renewal-runtime-extension-v1":
            raise ValueError("renewal completion-extension format mismatch")
        if amendment.get("amendment_digest") != _extension_digest(amendment):
            raise ValueError("renewal completion-extension digest mismatch")
        if amendment.get("original_registration_digest") != canonical_digest(registration):
            raise ValueError("renewal completion-extension registration mismatch")
        if amendment.get("scientific_outcomes_examined_before_extension") is not False:
            raise ValueError("renewal completion extension outcome boundary mismatch")
        allowed_seconds = float(amendment["total_cumulative_authorized_seconds"])
        if manifest.get("completed_under_original_six_hour_boundary") is not False:
            raise ValueError("extended campaign incorrectly claims six-hour completion")
        if manifest.get("completed_under_authorized_extension") is not True:
            raise ValueError("extended campaign omitted its completion label")
    if float(manifest["elapsed_seconds"]) > allowed_seconds:
        raise ValueError("renewal campaign exceeded its cumulative authorized boundary")
    if float(manifest["hard_wall_seconds"]) != allowed_seconds:
        raise ValueError("renewal campaign recorded the wrong authorized boundary")
    return {
        "verified": True,
        "verdict": manifest["verdict"],
        "predictions": manifest["prediction_results"],
        "frontier_records": int(manifest["frontier_records"]),
        "evolution_populations": int(manifest["evolution_populations"]),
        "mutation_rows": int(manifest["mutation_rows"]),
        "checksums": len(checksums),
        "completed_under_authorized_extension": amendment is not None,
    }


def wagner_ph_renewal_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    progress = (
        read_json(directory / "progress.json")
        if (directory / "progress.json").is_file()
        else None
    )
    result: dict[str, Any] = {
        "format": RENEWAL_CAMPAIGN_FORMAT,
        "root": str(directory),
        "registered": (directory / "registration.json").is_file(),
        "sealed": (directory / "SHA256SUMS").is_file(),
        "progress": progress,
        "hard_cap_remaining_seconds": max(
            0.0,
            float(progress.get("hard_wall_seconds", 21_600))
            - float(progress["elapsed_seconds"]),
        )
        if progress
        else None,
        "selection": read_json(directory / "evolution-selection.json")
        if (directory / "evolution-selection.json").is_file()
        else None,
        "stages": {},
        "verdict": None,
    }
    frontier = directory / "renewal-frontier"
    result["stages"]["renewal-frontier"] = {
        "started": frontier.is_dir(),
        "sealed": (frontier / "SHA256SUMS").is_file(),
        "progress": read_json(frontier / "study" / "progress.json")
        if (frontier / "study" / "progress.json").is_file()
        else None,
    }
    for name in ("evolution", "heldout-mutation-audit"):
        stage = directory / name
        result["stages"][name] = {
            "started": stage.is_dir(),
            "sealed": (stage / "SHA256SUMS").is_file(),
            "progress": read_json(stage / "progress.json")
            if (stage / "progress.json").is_file()
            else None,
        }
    if (directory / "campaign-manifest.json").is_file():
        result["verdict"] = read_json(directory / "campaign-manifest.json")["verdict"]
    return result


def replay_wagner_ph_renewal_item(
    directory: Path, item_id: str
) -> dict[str, Any]:
    directory = directory.resolve()
    if item_id.startswith("evolution:"):
        population_id = item_id.split(":", 1)[1]
        return {
            "stage": "evolution",
            **replay_renewal_population(directory / "evolution", population_id),
        }
    if item_id.startswith("audit:"):
        population_id = item_id.split(":", 1)[1]
        return {
            "stage": "heldout-mutation-audit",
            **replay_renewal_audit_population(
                directory / "heldout-mutation-audit", population_id
            ),
        }
    study = directory / "renewal-frontier" / "study"
    try:
        return {"stage": "renewal-frontier", **replay_local_future(study, item_id)}
    except KeyError:
        population_path = directory / "evolution" / "populations" / f"{item_id}.json"
        if population_path.is_file():
            return {
                "stage": "evolution",
                **replay_renewal_population(directory / "evolution", item_id),
            }
    raise KeyError(f"unknown Wagner PH renewal item: {item_id}")
