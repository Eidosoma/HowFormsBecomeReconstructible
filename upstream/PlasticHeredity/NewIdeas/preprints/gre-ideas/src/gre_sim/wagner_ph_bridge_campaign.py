"""Eight-hour guarded orchestration for the Wagner–PH bridge."""

from __future__ import annotations

import os
import time
from dataclasses import replace
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
from .local_ph_campaign import verify_local_ph_campaign
from .local_ph_config import LocalCarrierGenome
from .local_ph_study import replay_local_future, run_local_study, verify_local_study
from .wagner_ph_bridge_analysis import (
    analyze_causal_path,
    analyze_phase_path,
    analyze_precision_path,
    render_bridge_stage_report,
)
from .wagner_ph_bridge_config import (
    BRIDGE_CAMPAIGN_FORMAT,
    BRIDGE_STAGE_FORMAT,
    BridgeCampaignSpec,
)
from .wagner_ph_bridge_evolution import (
    replay_coevolution_population,
    run_bridge_coevolution,
    verify_bridge_coevolution,
)
from .wagner_ph_bridge_protocols import (
    bridge_campaign_spec,
    causal_confirmation_spec,
)


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _parent_provenance(parent: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    parent = parent.resolve()
    verification = verify_local_ph_campaign(parent)
    selection_path = parent / "search" / "selection.json"
    seal = parent / "SHA256SUMS"
    if not selection_path.is_file() or not seal.is_file():
        raise FileNotFoundError("bridge campaign requires the sealed local-PH v1 parent")
    selection = read_json(selection_path)
    if selection.get("eligible"):
        raise ValueError("bridge v1 is registered against the prior reliability failure")
    provenance = {
        "format": "gre-wagner-ph-bridge-parent-provenance-v1",
        "parent": str(parent),
        "parent_checksum_digest": sha256_file(seal),
        "selection_digest": sha256_file(selection_path),
        "parent_stage": verification["stage"],
        "parent_verdict": verification["verdict"],
        "historical_verdict_is_immutable": True,
        "claim_boundary": (
            "The bridge prospectively diagnoses the old reliability failure and explores "
            "causal/evolvable local carriers. It does not retroactively change the parent verdict "
            "or establish a natural historical origin."
        ),
    }
    provenance["provenance_digest"] = canonical_digest(provenance)
    return provenance, selection


def _write_progress(
    root: Path,
    stage: str,
    message: str,
    started_epoch: float,
    prior_consumed: float,
    spec: BridgeCampaignSpec,
) -> None:
    _atomic_json(
        root / "progress.json",
        {
            "format": "gre-wagner-ph-bridge-progress-v1",
            "active_stage": stage,
            "message": message,
            "run_started_epoch": started_epoch,
            "prior_consumed_seconds": prior_consumed,
            "elapsed_seconds": prior_consumed + time.time() - started_epoch,
            "hard_wall_seconds": spec.hard_wall_seconds,
            "soft_wall_seconds": spec.soft_wall_seconds,
        },
    )


def _verify_local_wrapper(directory: Path, kind: str) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    manifest = read_json(directory / "manifest.json")
    if manifest.get("format") != BRIDGE_STAGE_FORMAT or manifest.get("stage") != kind:
        raise ValueError("bridge local-stage manifest mismatch")
    verified = verify_local_study(directory / "study")
    analysis = read_json(directory / "analysis.json")
    if canonical_digest(analysis) != manifest.get("analysis_digest"):
        raise ValueError("bridge local-stage analysis digest mismatch")
    return {
        "verified": True,
        "stage": kind,
        "records": verified["records"],
        "checksums": len(checksums),
    }


def _run_local_wrapper(
    directory: Path,
    kind: str,
    study: Any,
    analyzer: Callable[[Path], dict[str, Any]],
    workers: int,
    progress: Callable[[str], None],
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "SHA256SUMS").is_file():
        _verify_local_wrapper(directory, kind)
        return read_json(directory / "analysis.json")
    started = time.monotonic()
    run_local_study(study, directory / "study", workers, progress)
    analysis = analyzer(directory / "study" / "futures.jsonl.gz")
    _atomic_json(directory / "analysis.json", analysis)
    (directory / "report.md").write_text(
        render_bridge_stage_report(analysis), encoding="utf-8"
    )
    local_manifest = read_json(directory / "study" / "manifest.json")
    _atomic_json(
        directory / "manifest.json",
        {
            "format": BRIDGE_STAGE_FORMAT,
            "stage": kind,
            "analysis_digest": canonical_digest(analysis),
            "study_protocol_digest": canonical_digest(study.to_dict()),
            "record_count": int(local_manifest["record_count"]),
            "elapsed_seconds": time.monotonic() - started,
        },
    )
    write_checksums(directory)
    _verify_local_wrapper(directory, kind)
    return analysis


def _freeze_causal_nominees(
    precision: dict[str, Any], phase: dict[str, Any], maximum: int
) -> dict[str, Any]:
    values: list[dict[str, Any]] = []
    precision_nominees = list(precision["selection"]["nominees"])
    if precision_nominees:
        smallest = min(
            precision_nominees,
            key=lambda value: (int(value["k"]), value["name"]),
        )
        values.append(smallest)
    for value in phase["selection"]["nominees"]:
        if value["name"] not in {item["name"] for item in values}:
            values.append(value)
        if len(values) >= maximum:
            break
    if not values:
        values.extend(precision["selection"]["diagnostic_fallback"][:maximum])
    return {
        "format": "gre-wagner-ph-bridge-causal-selection-v1",
        "nominees": values[:maximum],
        "precision_stable_candidate_available": bool(precision_nominees),
        "phase_selection_mode": phase["selection"]["mode"],
        "rule": (
            "include the smallest prospectively stable precision candidate, then the strongest "
            "fresh phase-map nominee; use registered diagnostic fallbacks only if necessary"
        ),
    }


def _freeze_evolution_carrier(
    causal: dict[str, Any], causal_selection: dict[str, Any]
) -> dict[str, Any]:
    passing = [
        value for value in causal["nominees"].values() if value["causal_local_ph_passed"]
    ]
    candidates = passing or list(causal["nominees"].values())
    ranked = sorted(
        candidates,
        key=lambda value: (
            0 if value["causal_local_ph_passed"] else 1,
            int(value["genome"]["k"]),
            -float(value["primary_generation_4"]["mean"] or -1.0),
            value["genome"]["name"],
        ),
    )
    if not ranked:
        genome = causal_selection["nominees"][0]
        mode = "registered-fallback"
    else:
        genome = ranked[0]["genome"]
        mode = "causal-pass" if passing else "diagnostic-best"
    return {
        "format": "gre-wagner-ph-bridge-evolution-selection-v1",
        "genome": genome,
        "mode": mode,
        "rule": "smallest causal passer, otherwise strongest diagnostic nominee; no evolution data used",
    }


def run_wagner_ph_bridge_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    if workers < 1 or workers > 4:
        raise ValueError("Wagner–PH bridge permits one to four workers")
    parent = parent.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_wagner_ph_bridge_campaign(destination)
        return destination
    provenance, prior_selection = _parent_provenance(parent)
    spec = bridge_campaign_spec(prior_selection, smoke=smoke)
    provenance_path = destination / "parent-provenance.json"
    if provenance_path.is_file() and read_json(provenance_path) != provenance:
        raise ValueError("existing bridge parent provenance differs")
    if not provenance_path.is_file():
        _atomic_json(provenance_path, provenance)
    registration = {
        "format": BRIDGE_CAMPAIGN_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
        "all_stages_execute": True,
        "later_claims_remain_gated": True,
        "causal_selection_rule_frozen_before_precision": True,
        "evolution_selection_rule_frozen_before_causal_results": True,
        "historical_parent_verdict_unchanged": True,
        "maximum_workers": 4,
        "hard_wall_seconds": 28_800,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing bridge registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    run_started_epoch = time.time()
    prior_consumed = float(
        os.environ.get("GRE_WAGNER_PH_BRIDGE_PRIOR_CONSUMED_SECONDS", "0")
    )
    soft_deadline_epoch = float(
        os.environ.get(
            "GRE_WAGNER_PH_BRIDGE_SOFT_DEADLINE_EPOCH",
            str(
                run_started_epoch
                + max(1.0, spec.soft_wall_seconds - prior_consumed)
            ),
        )
    )

    def announce(stage: str, message: str) -> None:
        _write_progress(
            destination, stage, message, run_started_epoch, prior_consumed, spec
        )
        if progress:
            progress(message)
        if stage != "sealing" and time.time() >= soft_deadline_epoch:
            raise TimeoutError("Wagner–PH bridge soft wall-time boundary reached")

    announce("precision", "starting four-block precision and repeatability audit")
    precision = _run_local_wrapper(
        destination / "precision",
        "precision",
        spec.precision.study,
        lambda path: analyze_precision_path(path, spec.precision),
        workers,
        lambda message: announce("precision", message),
    )
    announce("phase-map", "starting thirty-cell carrier phase diagram")
    phase = _run_local_wrapper(
        destination / "phase-map",
        "phase-map",
        spec.phase_diagram.screening,
        lambda path: analyze_phase_path(path, spec.phase_diagram),
        workers,
        lambda message: announce("phase-map", message),
    )
    causal_selection = _freeze_causal_nominees(
        precision, phase, spec.phase_diagram.maximum_nominees
    )
    causal_selection_path = destination / "causal-selection.json"
    if causal_selection_path.is_file() and read_json(causal_selection_path) != causal_selection:
        raise ValueError("existing frozen causal selection differs")
    if not causal_selection_path.is_file():
        _atomic_json(causal_selection_path, causal_selection)
    causal_nominees = tuple(
        LocalCarrierGenome(**value) for value in causal_selection["nominees"]
    )
    causal_spec = causal_confirmation_spec(
        spec.phase_diagram, causal_nominees, smoke=smoke
    )
    announce("causal-confirmation", "starting fresh causal and information confirmation")
    causal = _run_local_wrapper(
        destination / "causal-confirmation",
        "causal-confirmation",
        causal_spec,
        lambda path: analyze_causal_path(path, causal_spec),
        workers,
        lambda message: announce("causal-confirmation", message),
    )
    evolution_selection = _freeze_evolution_carrier(causal, causal_selection)
    evolution_selection_path = destination / "evolution-selection.json"
    if evolution_selection_path.is_file() and read_json(evolution_selection_path) != evolution_selection:
        raise ValueError("existing frozen evolution selection differs")
    if not evolution_selection_path.is_file():
        _atomic_json(evolution_selection_path, evolution_selection)
    evolution_spec = replace(
        spec.coevolution_template,
        initial_carrier=LocalCarrierGenome(**evolution_selection["genome"]),
    )
    evolution_spec.validate()
    announce("coevolution", "starting joint Wagner-weight/local-carrier evolution")
    run_bridge_coevolution(
        evolution_spec,
        destination / "coevolution",
        workers,
        lambda message: announce("coevolution", message),
    )
    evolution = read_json(destination / "coevolution" / "analysis.json")
    elapsed = prior_consumed + time.time() - run_started_epoch
    verdict = {
        "repeatable_local_effect": bool(precision["verdict"]["repeatable_local_effect"]),
        "causal_local_ph": bool(causal["verdict"]["causal_local_ph"]),
        "compressed_robust_ph": bool(causal["verdict"]["compressed_robust_ph"]),
        "evolved_bridge_nominated": bool(evolution["evolved_bridge_nominated"]),
        "compact_evolved_bridge_nominated": bool(
            evolution["compact_evolved_bridge_nominated"]
        ),
    }
    local_records = sum(
        int(read_json(destination / name / "manifest.json")["record_count"])
        for name in ("precision", "phase-map", "causal-confirmation")
    )
    manifest = {
        "format": BRIDGE_CAMPAIGN_FORMAT,
        "completed": True,
        "all_stages_complete": True,
        "verdict": verdict,
        "local_record_count": local_records,
        "evolution_populations": evolution_spec.population_count,
        "elapsed_seconds": elapsed,
        "hard_wall_seconds": spec.hard_wall_seconds,
        "historical_parent_verdict_unchanged": True,
        "claim_boundary": provenance["claim_boundary"],
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    report = "\n".join(
        (
            "# Wagner–Plastic Heredity Bridge v1",
            "",
            f"- Repeatable local effect: **{'PASS' if verdict['repeatable_local_effect'] else 'fail'}**",
            f"- Fresh causal local PH: **{'PASS' if verdict['causal_local_ph'] else 'fail'}**",
            f"- Compact robust local PH: **{'PASS' if verdict['compressed_robust_ph'] else 'fail'}**",
            f"- Exploratory evolved bridge nomination: **{'PASS' if verdict['evolved_bridge_nominated'] else 'fail'}**",
            f"- Exploratory compact evolved nomination: **{'PASS' if verdict['compact_evolved_bridge_nominated'] else 'fail'}**",
            f"- Local-study records: {local_records}",
            f"- Joint-evolution populations: {evolution_spec.population_count}",
            f"- Cumulative wall time: {elapsed:.1f} seconds",
            "",
            "The parent reliability verdict has not been rewritten. The new precision result is a prospectively registered diagnosis using block stability, while co-evolution remains exploratory even if nominated.",
            "",
            provenance["claim_boundary"],
            "",
        )
    )
    (destination / "report.md").write_text(report, encoding="utf-8")
    announce("sealing", "verifying and sealing all Wagner–PH bridge stages")
    write_checksums(destination)
    verify_wagner_ph_bridge_campaign(destination)
    if progress:
        progress("sealed Wagner–PH bridge campaign")
    return destination


def verify_wagner_ph_bridge_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    if registration.get("format") != BRIDGE_CAMPAIGN_FORMAT or manifest.get("format") != BRIDGE_CAMPAIGN_FORMAT:
        raise ValueError("Wagner–PH bridge campaign format mismatch")
    spec = BridgeCampaignSpec.from_dict(registration["protocol"])
    if canonical_digest(spec.to_dict()) != registration.get("protocol_digest"):
        raise ValueError("Wagner–PH bridge protocol digest mismatch")
    for name in ("precision", "phase-map", "causal-confirmation"):
        _verify_local_wrapper(directory / name, name)
    verify_bridge_coevolution(directory / "coevolution")
    if not manifest.get("all_stages_complete"):
        raise ValueError("Wagner–PH bridge cannot verify an incomplete campaign")
    if float(manifest["elapsed_seconds"]) > spec.hard_wall_seconds:
        raise ValueError("Wagner–PH bridge exceeded its cumulative eight-hour boundary")
    return {
        "verified": True,
        "verdict": manifest["verdict"],
        "local_records": int(manifest["local_record_count"]),
        "evolution_populations": int(manifest["evolution_populations"]),
        "checksums": len(checksums),
    }


def wagner_ph_bridge_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    progress = read_json(directory / "progress.json") if (directory / "progress.json").is_file() else None
    result: dict[str, Any] = {
        "format": BRIDGE_CAMPAIGN_FORMAT,
        "root": str(directory),
        "registered": (directory / "registration.json").is_file(),
        "sealed": (directory / "SHA256SUMS").is_file(),
        "progress": progress,
        "hard_cap_remaining_seconds": (
            max(0.0, 28_800 - float(progress["elapsed_seconds"])) if progress else None
        ),
        "stages": {},
        "verdict": None,
    }
    for name in ("precision", "phase-map", "causal-confirmation"):
        stage = directory / name
        study_progress = stage / "study" / "progress.json"
        result["stages"][name] = {
            "started": stage.is_dir(),
            "sealed": (stage / "SHA256SUMS").is_file(),
            "progress": read_json(study_progress) if study_progress.is_file() else None,
        }
    evolution = directory / "coevolution"
    result["stages"]["coevolution"] = {
        "started": evolution.is_dir(),
        "sealed": (evolution / "SHA256SUMS").is_file(),
        "progress": read_json(evolution / "progress.json")
        if (evolution / "progress.json").is_file()
        else None,
    }
    if (directory / "campaign-manifest.json").is_file():
        result["verdict"] = read_json(directory / "campaign-manifest.json")["verdict"]
    return result


def replay_wagner_ph_bridge_item(directory: Path, item_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    for name in ("precision", "phase-map", "causal-confirmation"):
        study = directory / name / "study"
        if (study / "futures.jsonl.gz").is_file():
            try:
                return {"stage": name, **replay_local_future(study, item_id)}
            except KeyError:
                pass
    population_path = directory / "coevolution" / "populations" / f"{item_id}.json"
    if population_path.is_file():
        return {
            "stage": "coevolution",
            **replay_coevolution_population(directory / "coevolution", item_id),
        }
    raise KeyError(f"unknown Wagner–PH bridge item: {item_id}")
