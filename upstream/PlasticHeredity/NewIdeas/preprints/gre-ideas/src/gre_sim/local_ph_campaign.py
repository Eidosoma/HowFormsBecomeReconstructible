"""Guarded search-to-confirmation orchestration for Wagner local memory."""

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
from .lineage_carrier_orchestrator import verify_lineage_carrier_campaign
from .local_ph_config import LOCAL_PH_CAMPAIGN_FORMAT, LocalCarrierGenome, expected_local_records
from .local_ph_protocols import (
    local_confirmation_spec,
    local_failure_atlas_spec,
    local_search_spec,
)
from .local_ph_search import run_local_search, verify_local_search
from .local_ph_study import replay_local_future, run_local_study, verify_local_study


LOCAL_PH_WALL_SECONDS = 8 * 60 * 60
LOCAL_PH_SOFT_SECONDS = 15 * 30 * 60
LOCAL_PH_MAX_WORKERS = 4
LOCAL_PH_CONFIRMATION_RECORD_CAP = 1_250_000


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _parent_provenance(parent: Path) -> dict[str, Any]:
    parent = parent.resolve()
    verify_lineage_carrier_campaign(parent)
    discovery_seal = parent / "discovery" / "SHA256SUMS"
    writer_path = parent / "writer-selection.json"
    selection_path = parent / "discovery-selection.json"
    if not discovery_seal.is_file() or not writer_path.is_file() or not selection_path.is_file():
        raise FileNotFoundError("local PH campaign requires sealed lineage discovery")
    writer = read_json(writer_path)["engines"]["wagner"]
    if not writer.get("passed") or writer.get("diagnostic_only"):
        raise ValueError("local PH campaign requires the passing natural Wagner writer")
    selected = read_json(selection_path)["selected"]
    if selected.get("engine") != "wagner":
        raise ValueError("lineage discovery did not select Wagner")
    result = {
        "format": "gre-wagner-local-ph-parent-provenance-v1",
        "parent": str(parent),
        "discovery_checksum_digest": sha256_file(discovery_seal),
        "writer_selection_digest": sha256_file(writer_path),
        "lineage_selection_digest": sha256_file(selection_path),
        "writer": writer["writer"],
        "prior_ceiling": selected,
        "claim_boundary": (
            "The prior latch is an upper-bound control. This campaign tests evolved, "
            "target-blind local marks; it cannot establish natural historical origin."
        ),
    }
    result["provenance_digest"] = canonical_digest(result)
    return result


def _write_progress(
    root: Path,
    stage: str,
    message: str,
    run_started_epoch: float,
    prior_consumed_seconds: float,
) -> None:
    _atomic_json(
        root / "progress.json",
        {
            "format": "gre-wagner-local-ph-campaign-progress-v1",
            "active_stage": stage,
            "message": message,
            "run_started_epoch": run_started_epoch,
            "prior_consumed_seconds": prior_consumed_seconds,
            "elapsed_seconds": prior_consumed_seconds + time.time() - run_started_epoch,
            "maximum_wall_seconds": LOCAL_PH_WALL_SECONDS,
            "soft_deadline_seconds": LOCAL_PH_SOFT_SECONDS,
        },
    )


def _diagnostic_variants(values: list[dict[str, Any]]) -> tuple[LocalCarrierGenome, ...]:
    """Freeze k=3/5/10 versions of the top mechanisms for failure localization."""

    result: dict[str, LocalCarrierGenome] = {}
    for item in values:
        base = LocalCarrierGenome(**item)
        for k in (3, 5, 10):
            topology = base.topology if not (base.topology == "all" and k < 10) else "outgoing"
            payload = {
                "write_rate": base.write_rate,
                "decay": base.decay,
                "coupling": base.coupling,
                "hysteresis": base.hysteresis,
                "topology": topology,
                "k": k,
            }
            name = f"diagnostic-{canonical_digest(payload)[:12]}"
            genome = LocalCarrierGenome(name, **payload)
            result[genome.name] = genome
    return tuple(result.values())


def run_local_ph_campaign(
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    if workers < 1 or workers > LOCAL_PH_MAX_WORKERS:
        raise ValueError("local PH campaign permits one to four workers")
    parent = parent.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_local_ph_campaign(destination)
        return destination
    provenance = _parent_provenance(parent)
    provenance_path = destination / "parent-provenance.json"
    if provenance_path.is_file() and read_json(provenance_path) != provenance:
        raise ValueError("existing local PH parent provenance differs")
    if not provenance_path.is_file():
        _atomic_json(provenance_path, provenance)
    run_started_epoch = time.time()
    prior_consumed_seconds = float(
        os.environ.get("GRE_LOCAL_PH_PRIOR_CONSUMED_SECONDS", "0")
    )
    soft_deadline_epoch = float(
        os.environ.get(
            "GRE_LOCAL_PH_SOFT_DEADLINE_EPOCH",
            str(run_started_epoch + max(1.0, LOCAL_PH_SOFT_SECONDS - prior_consumed_seconds)),
        )
    )

    def announce(stage: str, message: str) -> None:
        _write_progress(
            destination,
            stage,
            message,
            run_started_epoch,
            prior_consumed_seconds,
        )
        if progress:
            progress(message)
        if stage != "sealing" and time.time() >= soft_deadline_epoch:
            raise TimeoutError("local PH soft wall-time boundary reached")

    search_spec = local_search_spec(smoke=smoke)
    registration = {
        "format": LOCAL_PH_CAMPAIGN_FORMAT,
        "search_protocol": search_spec.to_dict(),
        "search_protocol_digest": canonical_digest(search_spec.to_dict()),
        "fresh_confirmation_seed_frozen_before_search": True,
        "maximum_workers": LOCAL_PH_MAX_WORKERS,
        "hard_wall_seconds": LOCAL_PH_WALL_SECONDS,
        "soft_wall_seconds": LOCAL_PH_SOFT_SECONDS,
        "claim_boundary": provenance["claim_boundary"],
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing local PH campaign registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    search = destination / "search"
    announce("search", "starting target-blind local writer/reader evolution")
    run_local_search(
        search_spec,
        search,
        workers,
        lambda message: announce("search", message),
    )
    selection = read_json(search / "selection.json")
    frozen_selection = {
        "format": "gre-wagner-local-ph-frozen-selection-v1",
        "search_checksum_digest": sha256_file(search / "SHA256SUMS"),
        "selection_digest": sha256_file(search / "selection.json"),
        **selection,
    }
    frozen_path = destination / "frozen-selection.json"
    if frozen_path.is_file() and read_json(frozen_path) != frozen_selection:
        raise ValueError("existing frozen local PH selection differs")
    if not frozen_path.is_file():
        _atomic_json(frozen_path, frozen_selection)
    if selection["eligible"]:
        nominees = tuple(LocalCarrierGenome(**value) for value in selection["nominees"])
        study_spec = local_confirmation_spec(nominees, smoke=smoke)
        if expected_local_records(study_spec) > LOCAL_PH_CONFIRMATION_RECORD_CAP:
            raise RuntimeError("local PH confirmation exceeds its frozen record cap")
        stage_name = "confirmation"
        stage = destination / stage_name
        announce(stage_name, "starting untouched local-memory causal confirmation")
        run_local_study(
            study_spec,
            stage,
            workers,
            lambda message: announce(stage_name, message),
        )
    else:
        variants = _diagnostic_variants(selection["diagnostic_top_two"])
        study_spec = local_failure_atlas_spec(variants, smoke=smoke)
        stage_name = "failure-atlas"
        stage = destination / stage_name
        search_registry = read_json(search / "rulebooks.json")
        atlas_registry = dict(search_registry)
        atlas_registry["sources"] = list(search_registry["sources"])[-study_spec.source_count :]
        announce(stage_name, "no nominee qualified; starting preregistered failure atlas")
        run_local_study(
            study_spec,
            stage,
            workers,
            lambda message: announce(stage_name, message),
            registry=atlas_registry,
        )
    analysis = read_json(stage / "analysis.json")
    verdict = analysis["verdict"] if stage_name == "confirmation" else {
        "causal_local_ph": False,
        "compressed_robust_ph": False,
        "confirmation_launched": False,
    }
    manifest = {
        "format": LOCAL_PH_CAMPAIGN_FORMAT,
        "completed": True,
        "stage": stage_name,
        "search_selection": selection,
        "verdict": verdict,
        "record_count": int(read_json(stage / "manifest.json")["record_count"]),
        "elapsed_seconds": prior_consumed_seconds + time.time() - run_started_epoch,
        "hard_wall_seconds": LOCAL_PH_WALL_SECONDS,
        "claim_boundary": provenance["claim_boundary"],
    }
    _atomic_json(destination / "campaign-manifest.json", manifest)
    report = "\n".join(
        (
            "# Wagner local-memory PH campaign",
            "",
            f"- Terminal stage: `{stage_name}`",
            f"- Causal local PH: **{'PASS' if verdict['causal_local_ph'] else 'fail'}**",
            f"- Compressed robust PH: **{'PASS' if verdict['compressed_robust_ph'] else 'fail'}**",
            f"- Search produced an eligible nominee: `{selection['eligible']}`",
            f"- Total campaign wall time: {manifest['elapsed_seconds']:.1f} seconds",
            "",
            "## Interpretation boundary",
            "",
            provenance["claim_boundary"],
            "",
            f"Detailed stage report: [{stage_name}/report.md]({stage_name}/report.md)",
            "",
        )
    )
    (destination / "report.md").write_text(report, encoding="utf-8")
    announce("sealing", "verifying and sealing complete local-PH campaign")
    write_checksums(destination)
    verify_local_ph_campaign(destination)
    if progress:
        progress("sealed Wagner local-memory PH campaign")
    return destination


def verify_local_ph_campaign(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "campaign-manifest.json")
    if registration.get("format") != LOCAL_PH_CAMPAIGN_FORMAT or manifest.get("format") != LOCAL_PH_CAMPAIGN_FORMAT:
        raise ValueError("local PH campaign format mismatch")
    verify_local_search(directory / "search")
    stage = str(manifest["stage"])
    verify_local_study(directory / stage)
    if float(manifest["elapsed_seconds"]) > LOCAL_PH_WALL_SECONDS:
        raise ValueError("local PH campaign exceeded its eight-hour claim boundary")
    return {
        "verified": True,
        "stage": stage,
        "verdict": manifest["verdict"],
        "checksums": len(checksums),
    }


def local_ph_status(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    result: dict[str, Any] = {
        "format": LOCAL_PH_CAMPAIGN_FORMAT,
        "root": str(directory),
        "registered": (directory / "registration.json").is_file(),
        "sealed": (directory / "SHA256SUMS").is_file(),
        "progress": read_json(directory / "progress.json") if (directory / "progress.json").is_file() else None,
        "search": None,
        "active_study": None,
        "verdict": None,
    }
    if (directory / "search" / "checkpoint.json").is_file():
        checkpoint = read_json(directory / "search" / "checkpoint.json")
        protocol = read_json(directory / "search" / "registration.json")["protocol"]
        result["search"] = {
            "generation": checkpoint["generation"],
            "total_generations": protocol["generations"],
            "sealed": (directory / "search" / "SHA256SUMS").is_file(),
        }
    for name in ("confirmation", "failure-atlas"):
        stage = directory / name
        if stage.is_dir():
            result["active_study"] = {
                "name": name,
                "sealed": (stage / "SHA256SUMS").is_file(),
                "progress": read_json(stage / "progress.json") if (stage / "progress.json").is_file() else None,
            }
    if (directory / "campaign-manifest.json").is_file():
        result["verdict"] = read_json(directory / "campaign-manifest.json")["verdict"]
    return result


def replay_local_campaign_future(directory: Path, future_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    for name in ("confirmation", "failure-atlas"):
        if (directory / name / "futures.jsonl.gz").is_file():
            try:
                return replay_local_future(directory / name, future_id)
            except KeyError:
                pass
    raise KeyError(f"unknown local PH future: {future_id}")
