"""Four-hour guarded orchestration for Wagner PH origin/discrimination v1."""

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
from .wagner_ph_origin_audit import (
    replay_origin_audit_population,
    run_origin_audit,
    verify_origin_audit,
)
from .wagner_ph_origin_config import ORIGIN_CAMPAIGN_FORMAT, OriginCampaignSpec
from .wagner_ph_origin_evolution import (
    replay_origin_population,
    run_origin_evolution,
    verify_origin_evolution,
)
from .wagner_ph_origin_protocols import (
    origin_campaign_spec,
    selected_origin_evolution_spec,
)
from .wagner_ph_origin_screen import (
    replay_origin_screen_unit,
    run_origin_screen,
    verify_origin_screen,
)
from .wagner_ph_renewal_campaign import verify_wagner_ph_renewal_campaign


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _parent_provenance(parent: Path) -> dict[str, Any]:
    parent = parent.resolve()
    verification = verify_wagner_ph_renewal_campaign(parent)
    seal = parent / "SHA256SUMS"
    selection = parent / "evolution-selection.json"
    audit = parent / "heldout-mutation-audit" / "analysis.json"
    if not seal.is_file() or not selection.is_file() or not audit.is_file():
        raise FileNotFoundError("origin campaign requires sealed renewal-v1 parent")
    value = {
        "format": "gre-wagner-ph-origin-parent-provenance-v1",
        "parent": str(parent),
        "parent_checksum_digest": sha256_file(seal),
        "parent_selection_digest": sha256_file(selection),
        "parent_audit_digest": sha256_file(audit),
        "parent_verdict": verification["verdict"],
        "parent_completed_under_authorized_extension": bool(
            verification.get("completed_under_authorized_extension", True)
        ),
        "parent_is_read_only": True,
        "historical_verdicts_are_immutable": True,
        "claim_boundary": (
            "The origin campaign probes activation of a predefined target-blind carrier "
            "channel. It neither revises renewal-v1 nor establishes natural historical origin."
        ),
    }
    value["provenance_digest"] = canonical_digest(value)
    return value


def prediction_ledger() -> dict[str, Any]:
    return {
        "format": "gre-wagner-ph-origin-prediction-ledger-v1",
        "frozen_before_new_screen_data": True,
        "predictions": {
            "P1": {
                "statement": "A fresh copying regime will discriminate intact renewal from renewal-off.",
                "test": "the registered adaptive screen qualifies without fallback",
            },
            "P2": {
                "statement": "Explicit selection can activate writer and reader from the dormant scaffold.",
                "test": "all dormant-activation gates pass on held-out data",
            },
            "P3": {
                "statement": "Explicit renewal will outperform physically passive transmission.",
                "test": "dormant explicit-minus-passive mean is at least 0.10 with positive lower bound",
            },
            "P4": {
                "statement": "Performance-only selection can indirectly select renewal.",
                "test": "dormant permissive renewal and permissive-minus-passive gates both pass",
            },
            "P5": {
                "statement": "Explicit renewal selection adds value beyond permissive performance selection.",
                "test": "dormant explicit-minus-permissive mean is at least 0.05 with positive lower bound",
            },
            "P6": {
                "statement": "The inherited phenotype follows carrier state under causal intervention.",
                "test": "write/read/block/erase/rescue/shuffle/transplant causal gates pass",
            },
            "P7": {
                "statement": "Renewal remains robust over a two-generation mutation pedigree.",
                "test": "one-step 0.70, two-step 0.50, and both clustered slope gates pass",
            },
        },
    }


def _extension_digest(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("amendment_digest", None)
    return canonical_digest(payload)


def prepare_completion_extension(
    destination: Path,
    spec: OriginCampaignSpec,
    *,
    original_consumed_seconds: int,
    extension_hard_seconds: int = 14_400,
    extension_soft_seconds: int = 13_500,
) -> dict[str, Any]:
    """Register a bounded completion window without rewriting the first attempt."""

    destination = destination.resolve()
    if extension_hard_seconds != 14_400 or extension_soft_seconds != 13_500:
        raise ValueError("origin completion extension is frozen at 14400/13500 seconds")
    if not spec.soft_wall_seconds <= original_consumed_seconds <= spec.hard_wall_seconds:
        raise ValueError("origin completion extension requires an exhausted original attempt")
    registration_path = destination / "registration.json"
    if not registration_path.is_file() or (destination / "SHA256SUMS").is_file():
        raise ValueError("origin completion extension requires an unsealed registered campaign")
    amendment_path = destination / "runtime-extension-registration.json"
    if amendment_path.is_file():
        amendment = read_json(amendment_path)
        if amendment.get("amendment_digest") != _extension_digest(amendment):
            raise ValueError("origin completion-extension digest mismatch")
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
            raise ValueError("existing origin completion extension differs")
        return amendment

    units = destination / "evolution" / "populations"
    treatments = (
        "dormant_explicit_renewal",
        "dormant_permissive_performance",
        "dormant_passive_locked",
        "weak_explicit_renewal",
        "weak_permissive_performance",
        "weak_passive_locked",
    )
    treatment_counts = {
        treatment: sum(
            1
            for path in units.glob(f"{treatment}.population-*.json")
            if not path.name.endswith(".checkpoint.json")
        )
        for treatment in treatments
    }
    checkpoint_counts = {
        treatment: len(
            list(units.glob(f"{treatment}.population-*.checkpoint.json"))
        )
        for treatment in treatments
    }
    amendment = {
        "format": "gre-wagner-ph-origin-runtime-extension-v1",
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
        "completed_evolution_populations_before_extension": sum(treatment_counts.values()),
        "completed_evolution_populations_by_treatment": treatment_counts,
        "partial_evolution_checkpoints_before_extension": sum(
            checkpoint_counts.values()
        ),
        "partial_evolution_checkpoints_by_treatment": checkpoint_counts,
        "screen_outcome_examined_before_extension": True,
        "screen_result_known_before_extension": "qualified d095-p002 selection",
        "evolution_scores_examined_before_extension": False,
        "audit_outcomes_examined_before_extension": False,
        "final_verdict_existed_before_extension": False,
        "extension_decision_basis": (
            "runtime exhaustion, completed population count, and the user-authorized "
            "request to finish; no partial evolution scores were opened"
        ),
        "reason": (
            "the frozen runtime projection underestimated factorial evolution; resume "
            "only registered computations without changing seeds, samples, objectives, "
            "gates, interventions, or analyses"
        ),
        "claim_boundary": (
            "Any completed verdict is extension-completed exploratory evidence and did "
            "not finish under the original four-hour boundary. The screen pass was known "
            "before extension, while evolution and audit outcomes remained unexamined."
        ),
        "user_authorized_resume": True,
    }
    amendment["amendment_digest"] = _extension_digest(amendment)
    _atomic_json(amendment_path, amendment)
    return amendment


def _write_progress(
    root: Path,
    stage: str,
    message: str,
    started_epoch: float,
    prior_consumed: float,
    spec: OriginCampaignSpec,
    effective_hard: float,
    effective_soft: float,
    amendment: dict[str, Any] | None,
) -> None:
    _atomic_json(
        root / "progress.json",
        {
            "format": "gre-wagner-ph-origin-progress-v1",
            "active_stage": stage,
            "message": message,
            "run_started_epoch": started_epoch,
            "prior_consumed_seconds": prior_consumed,
            "elapsed_seconds": prior_consumed + time.time() - started_epoch,
            "hard_wall_seconds": effective_hard,
            "soft_wall_seconds": effective_soft,
            "original_hard_wall_seconds": spec.hard_wall_seconds,
            "original_soft_wall_seconds": spec.soft_wall_seconds,
            "completed_under_authorized_extension": amendment is not None,
            "runtime_extension_digest": amendment.get("amendment_digest")
            if amendment is not None
            else None,
            "projected_wall_seconds": spec.projected_wall_seconds,
            "maximum_workers": spec.maximum_workers,
            "cpu_only": True,
        },
    )


def _score_predictions(screen: dict[str, Any], audit: dict[str, Any]) -> dict[str, bool]:
    verdict = audit["verdict"]
    return {
        "P1": bool(screen["verdict"]["discriminating_environment_found"]),
        "P2": bool(verdict["dormant_activation_nominated"]),
        "P3": bool(verdict["renewal_necessity_nominated"]),
        "P4": bool(verdict["implicit_renewal_explanation_supported"]),
        "P5": bool(verdict["explicit_selection_advantage_nominated"]),
        "P6": bool(verdict["causal_ph_mechanism_nominated"]),
        "P7": bool(verdict["mutation_robustness_nominated"]),
    }


def run_wagner_ph_origin_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
    completion_extension: bool = False,
    original_consumed_seconds: int | None = None,
    extension_hard_seconds: int = 14_400,
    extension_soft_seconds: int = 13_500,
) -> Path:
    if workers < 1 or workers > 4:
        raise ValueError("Wagner PH origin permits one to four CPU workers")
    parent = parent.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_origin_campaign(destination)
        return destination
    provenance = _parent_provenance(parent)
    spec = origin_campaign_spec(smoke=smoke)
    if spec.projected_wall_seconds > spec.soft_wall_seconds:
        raise RuntimeError("projected origin campaign runtime exceeds soft wall")
    provenance_path = destination / "parent-provenance.json"
    if provenance_path.is_file() and canonical_digest(
        read_json(provenance_path)
    ) != canonical_digest(provenance):
        raise ValueError("existing origin parent provenance differs")
    if not provenance_path.is_file():
        _atomic_json(provenance_path, provenance)
    ledger = prediction_ledger()
    registration = {
        "format": ORIGIN_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
        "prediction_ledger": ledger,
        "prediction_ledger_digest": canonical_digest(ledger),
        "parent_provenance_digest": provenance["provenance_digest"],
        "adaptive_selection_rule_frozen_before_screen": True,
        "selected_environment_frozen_before_evolution": True,
        "heldout_seed_is_untouched_by_screen_and_selection": True,
        "all_stages_run_after_diagnostic_fallback": True,
        "fallback_cannot_pass_primary_origin_nomination": True,
        "layered_verdicts_not_single_omnibus": True,
        "dormant_channel_is_predefined_but_inactive": True,
        "maximum_workers": 4,
        "cpu_only": True,
        "hard_wall_seconds": 14_400,
        "no_runtime_extension_authorized": True,
        "runtime_projection": {
            "projected_seconds": spec.projected_wall_seconds,
            "basis": (
                "renewal-v1 calibration scaled to 36 populations of size 24 for 28 "
                "generations, plus a bounded screen and two-arm causal pedigree audit"
            ),
            "must_not_exceed_soft_seconds": spec.soft_wall_seconds,
        },
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(
        read_json(registration_path)
    ) != canonical_digest(registration):
        raise ValueError("existing origin campaign registration differs")
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
            raise ValueError("origin completion-extension digest mismatch")
    started_epoch = time.time()
    if amendment is None:
        prior_consumed = float(
            os.environ.get("GRE_WAGNER_PH_ORIGIN_PRIOR_CONSUMED_SECONDS", "0")
        )
        effective_hard = float(spec.hard_wall_seconds)
        effective_soft = float(spec.soft_wall_seconds)
        soft_deadline = float(
            os.environ.get(
                "GRE_WAGNER_PH_ORIGIN_SOFT_DEADLINE_EPOCH",
                str(started_epoch + max(1.0, effective_soft - prior_consumed)),
            )
        )
    else:
        extension_prior = float(
            os.environ.get(
                "GRE_WAGNER_PH_ORIGIN_EXTENSION_PRIOR_CONSUMED_SECONDS", "0"
            )
        )
        prior_consumed = float(amendment["original_consumed_seconds"]) + extension_prior
        effective_hard = float(amendment["total_cumulative_authorized_seconds"])
        effective_soft = float(amendment["original_consumed_seconds"]) + float(
            amendment["extension_soft_seconds"]
        )
        soft_deadline = float(
            os.environ.get(
                "GRE_WAGNER_PH_ORIGIN_EXTENSION_SOFT_DEADLINE_EPOCH",
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
            raise TimeoutError("Wagner PH origin soft wall-time boundary reached")

    announce("discrimination-screen", "starting fresh renewal discrimination screen")
    run_origin_screen(
        parent,
        spec.screen,
        destination / "discrimination-screen",
        workers,
        lambda message: announce("discrimination-screen", message),
    )
    screen = read_json(destination / "discrimination-screen" / "analysis.json")
    frozen_selection = {
        **screen["selection"],
        "screen_analysis_digest": canonical_digest(screen),
        "fallback_is_diagnostic_only": not bool(
            screen["selection"]["primary_screen_passed"]
        ),
    }
    selection_path = destination / "environment-selection.json"
    if selection_path.is_file() and canonical_digest(
        read_json(selection_path)
    ) != canonical_digest(frozen_selection):
        raise ValueError("existing origin environment selection differs")
    if not selection_path.is_file():
        _atomic_json(selection_path, frozen_selection)
    evolution = selected_origin_evolution_spec(spec, frozen_selection)
    announce("factorial-evolution", "starting six-arm dormant/weak factorial evolution")
    run_origin_evolution(
        evolution,
        destination / "evolution",
        workers,
        lambda message: announce("factorial-evolution", message),
    )
    announce(
        "causal-pedigree-audit",
        "starting untouched causal, state-transplant, and mutation-pedigree audit",
    )
    run_origin_audit(
        destination / "evolution",
        spec.audit,
        destination / "heldout-causal-pedigree-audit",
        workers,
        lambda message: announce("causal-pedigree-audit", message),
    )
    audit = read_json(
        destination / "heldout-causal-pedigree-audit" / "analysis.json"
    )
    predictions = _score_predictions(screen, audit)
    primary_eligible = bool(screen["selection"]["primary_screen_passed"])
    verdict = {
        "discriminating_environment_found": primary_eligible,
        **{
            key: primary_eligible and bool(value)
            for key, value in audit["verdict"].items()
        },
    }
    elapsed = prior_consumed + time.time() - started_epoch
    manifest = {
        "format": ORIGIN_CAMPAIGN_FORMAT,
        "protocol_digest": canonical_digest(spec.to_dict()),
        "parent_provenance_digest": provenance["provenance_digest"],
        "screen_analysis_digest": canonical_digest(screen),
        "environment_selection_digest": canonical_digest(frozen_selection),
        "evolution_analysis_digest": canonical_digest(
            read_json(destination / "evolution" / "analysis.json")
        ),
        "audit_analysis_digest": canonical_digest(audit),
        "prediction_results": predictions,
        "supported_predictions": sum(predictions.values()),
        "prediction_count": len(predictions),
        "verdict": verdict,
        "population_count": evolution.population_count,
        "pedigree_rows": int(audit["pedigree_rows"]),
        "cumulative_wall_seconds": elapsed,
        "hard_wall_seconds": effective_hard,
        "soft_wall_seconds": effective_soft,
        "original_hard_wall_seconds": spec.hard_wall_seconds,
        "original_soft_wall_seconds": spec.soft_wall_seconds,
        "completed_within_four_hour_boundary": amendment is None
        and elapsed <= spec.hard_wall_seconds,
        "completed_under_extension": amendment is not None,
        "completed_under_authorized_extension": amendment is not None,
        "runtime_extension": amendment,
        "cpu_only": True,
        "maximum_workers": workers,
        "claim_boundary": audit["claim_boundary"],
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    lines = [
        "# Wagner PH Origin and Discrimination v1",
        "",
        f"- Discrimination screen: **{'PASS' if verdict['discriminating_environment_found'] else 'fallback'}**",
        f"- Dormant activation: **{'PASS' if verdict['dormant_activation_nominated'] else 'fail'}**",
        f"- Renewal necessity: **{'PASS' if verdict['renewal_necessity_nominated'] else 'fail'}**",
        f"- Implicit-renewal explanation: **{'PASS' if verdict['implicit_renewal_explanation_supported'] else 'fail'}**",
        f"- Explicit-selection advantage: **{'PASS' if verdict['explicit_selection_advantage_nominated'] else 'fail'}**",
        f"- Causal PH mechanism: **{'PASS' if verdict['causal_ph_mechanism_nominated'] else 'fail'}**",
        f"- Mutation robustness: **{'PASS' if verdict['mutation_robustness_nominated'] else 'fail'}**",
        f"- Prediction ledger: {sum(predictions.values())}/{len(predictions)} supported",
        f"- Evolution populations: {evolution.population_count}",
        f"- Pedigree rows: {audit['pedigree_rows']}",
        f"- Cumulative wall time: {elapsed:.1f} seconds",
        f"- Completed within four-hour boundary: `{amendment is None and elapsed <= spec.hard_wall_seconds}`",
        f"- Completed under authorized extension: `{amendment is not None}`",
        "",
        audit["claim_boundary"],
        "",
    ]
    (destination / "report.md").write_text("\n".join(lines), encoding="utf-8")
    announce("sealing", "verifying and sealing Wagner PH origin campaign")
    write_checksums(destination)
    verify_wagner_ph_origin_campaign(destination)
    if progress:
        progress("sealed Wagner PH origin campaign")
    return destination


def verify_wagner_ph_origin_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    if registration.get("format") != ORIGIN_CAMPAIGN_FORMAT:
        raise ValueError("origin campaign registration format mismatch")
    if manifest.get("format") != ORIGIN_CAMPAIGN_FORMAT:
        raise ValueError("origin campaign manifest format mismatch")
    spec = OriginCampaignSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("origin campaign protocol digest mismatch")
    if canonical_digest(registration["prediction_ledger"]) != registration.get(
        "prediction_ledger_digest"
    ):
        raise ValueError("origin prediction ledger digest mismatch")
    verify_origin_screen(directory / "discrimination-screen")
    evolution_verification = verify_origin_evolution(directory / "evolution")
    audit_verification = verify_origin_audit(
        directory / "heldout-causal-pedigree-audit"
    )
    screen = read_json(directory / "discrimination-screen" / "analysis.json")
    audit = read_json(
        directory / "heldout-causal-pedigree-audit" / "analysis.json"
    )
    selection = read_json(directory / "environment-selection.json")
    if canonical_digest(screen) != manifest.get("screen_analysis_digest"):
        raise ValueError("origin screen analysis digest mismatch")
    if canonical_digest(selection) != manifest.get("environment_selection_digest"):
        raise ValueError("origin environment selection digest mismatch")
    predictions = _score_predictions(screen, audit)
    if canonical_digest(predictions) != canonical_digest(
        manifest["prediction_results"]
    ):
        raise ValueError("origin prediction results mismatch")
    elapsed = float(manifest["cumulative_wall_seconds"])
    amendment_path = directory / "runtime-extension-registration.json"
    amendment = read_json(amendment_path) if amendment_path.is_file() else None
    allowed_seconds = float(spec.hard_wall_seconds)
    if amendment is None:
        if not bool(manifest["completed_within_four_hour_boundary"]):
            raise ValueError("origin campaign omitted four-hour completion label")
        if bool(manifest.get("completed_under_extension")):
            raise ValueError("origin campaign incorrectly claims an extension")
    else:
        if amendment.get("format") != "gre-wagner-ph-origin-runtime-extension-v1":
            raise ValueError("origin completion-extension format mismatch")
        if amendment.get("amendment_digest") != _extension_digest(amendment):
            raise ValueError("origin completion-extension digest mismatch")
        if amendment.get("original_registration_digest") != canonical_digest(
            registration
        ):
            raise ValueError("origin completion-extension registration mismatch")
        if amendment.get("screen_outcome_examined_before_extension") is not True:
            raise ValueError("origin extension must disclose the known screen outcome")
        if amendment.get("evolution_scores_examined_before_extension") is not False:
            raise ValueError("origin extension evolution-outcome boundary mismatch")
        if amendment.get("audit_outcomes_examined_before_extension") is not False:
            raise ValueError("origin extension audit-outcome boundary mismatch")
        if amendment.get("final_verdict_existed_before_extension") is not False:
            raise ValueError("origin extension final-verdict boundary mismatch")
        allowed_seconds = float(amendment["total_cumulative_authorized_seconds"])
        if manifest.get("completed_within_four_hour_boundary") is not False:
            raise ValueError("extended origin campaign incorrectly claims four-hour completion")
        if manifest.get("completed_under_extension") is not True:
            raise ValueError("extended origin campaign omitted its extension label")
        if manifest.get("completed_under_authorized_extension") is not True:
            raise ValueError("extended origin campaign omitted authorization label")
    if elapsed > allowed_seconds:
        raise ValueError("origin campaign exceeded its cumulative authorized boundary")
    if float(manifest["hard_wall_seconds"]) != allowed_seconds:
        raise ValueError("origin campaign recorded the wrong authorized boundary")
    return {
        "verified": True,
        "checksums": len(checksums),
        "populations": evolution_verification["populations"],
        "pedigree_rows": audit_verification["pedigree_rows"],
        "verdict": manifest["verdict"],
        "prediction_results": predictions,
        "cumulative_wall_seconds": elapsed,
        "completed_within_four_hour_boundary": amendment is None,
        "completed_under_authorized_extension": amendment is not None,
    }


def wagner_ph_origin_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    registration_path = directory / "registration.json"
    progress_path = directory / "progress.json"
    result: dict[str, Any] = {
        "format": ORIGIN_CAMPAIGN_FORMAT,
        "root": str(directory),
        "registered": registration_path.is_file(),
        "sealed": (directory / "SHA256SUMS").is_file(),
        "progress": read_json(progress_path) if progress_path.is_file() else None,
        "selection": read_json(directory / "environment-selection.json")
        if (directory / "environment-selection.json").is_file()
        else None,
        "verdict": read_json(directory / "campaign-manifest.json")["verdict"]
        if (directory / "campaign-manifest.json").is_file()
        else None,
        "runtime_extension": read_json(
            directory / "runtime-extension-registration.json"
        )
        if (directory / "runtime-extension-registration.json").is_file()
        else None,
    }
    progress_value = result["progress"] or {}
    if progress_value:
        result["hard_cap_remaining_seconds"] = max(
            0.0,
            float(progress_value.get("hard_wall_seconds", 14_400))
            - float(progress_value.get("elapsed_seconds", 0.0)),
        )
    stages = {}
    for name, child in (
        ("discrimination-screen", "discrimination-screen"),
        ("factorial-evolution", "evolution"),
        ("causal-pedigree-audit", "heldout-causal-pedigree-audit"),
    ):
        path = directory / child
        stages[name] = {
            "started": path.is_dir(),
            "sealed": (path / "SHA256SUMS").is_file(),
            "progress": read_json(path / "progress.json")
            if (path / "progress.json").is_file()
            else None,
        }
    result["stages"] = stages
    return result


def replay_wagner_ph_origin_item(
    directory: Path, item: str
) -> dict[str, Any]:
    if item.startswith("screen:"):
        return {
            "stage": "discrimination-screen",
            **replay_origin_screen_unit(
                directory / "discrimination-screen", item.split(":", 1)[1]
            ),
        }
    if item.startswith("evolution:"):
        return {
            "stage": "factorial-evolution",
            **replay_origin_population(
                directory / "evolution", item.split(":", 1)[1]
            ),
        }
    if item.startswith("audit:"):
        return {
            "stage": "causal-pedigree-audit",
            **replay_origin_audit_population(
                directory / "heldout-causal-pedigree-audit",
                item.split(":", 1)[1],
            ),
        }
    raise ValueError("origin replay item must start with screen:, evolution:, or audit:")
