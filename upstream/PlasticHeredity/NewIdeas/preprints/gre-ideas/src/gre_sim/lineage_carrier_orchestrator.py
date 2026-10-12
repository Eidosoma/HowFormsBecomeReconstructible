"""Guarded orchestration for the Wagner-primary lineage-carrier campaign."""

from __future__ import annotations

import shutil
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from .artifacts import canonical_digest, read_json, sha256_file, verify_checksums, write_json
from .lineage_carrier_analysis import (
    select_calibrated_carriers,
    select_discovery_candidate,
)
from .lineage_carrier_config import (
    LINEAGE_CAMPAIGN_FORMAT,
    LINEAGE_SELECTION_FORMAT,
    LineageWriterSpec,
)
from .lineage_carrier_evolution import (
    run_lineage_evolution,
    verify_lineage_evolution,
)
from .lineage_carrier_protocols import (
    carrier_calibration_spec,
    compatibility_spec,
    evolution_spec,
    lineage_confirmation_spec,
    lineage_discovery_spec,
    writer_calibration_spec,
)
from .lineage_carrier_study import (
    expected_lineage_records,
    replay_lineage_future,
    run_lineage_study,
    verify_lineage_study,
)
from .plastic_heredity_v2_analysis import select_weakest_balanced_cues
from .plastic_heredity_v2_protocols import carrier_grid
from .plastic_heredity_v2_study import (
    replay_v2_state_future,
    run_v2_state_study,
    verify_v2_state_study,
)


MINIMUM_FREE_DISK_BYTES = 40 * 1024**3
LINEAGE_RECORD_CAP = 15_000_000
MAXIMUM_WORKERS = 8
THROUGH_VALUES = ("discovery", "confirmation", "full")


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _progress(
    root: Path,
    active: str,
    completed: list[str],
    started: float,
    message: str,
) -> None:
    _atomic_json(
        root / "progress.json",
        {
            "format": "gre-wagner-lineage-campaign-progress-v1",
            "active_stage": active,
            "completed_stages": completed,
            "elapsed_seconds": time.monotonic() - started,
            "message": message,
        },
    )


def _writer_screen_spec(engine: str, smoke: bool) -> Any:
    spec = writer_calibration_spec(engine)
    if not smoke:
        return spec
    return replace(
        spec,
        source_count_per_engine=1,
        writers=spec.writers[:2],
        conditions=spec.conditions[:2],
        midpoint_count=1,
        horizon=12,
        strict_run=2,
        stable_run=2,
        bootstrap_repetitions=64,
    )


def _writer_from_dose(engine: str, dose: Any) -> LineageWriterSpec:
    return LineageWriterSpec(
        f"{engine}.selected-natural",
        engine,
        "natural",
        float(dose.fraction),
        int(dose.dwell),
    )


def _diagnostic_writer(engine: str, analysis: dict[str, Any], spec: Any) -> LineageWriterSpec:
    candidates: list[tuple[float, float, float, int, Any]] = []
    for writer in spec.writers:
        model = f"{engine}.{writer.name}"
        histories = analysis.get("acquisition", {}).get(model, {})
        means = [histories.get(history, {}).get("mean") for history in ("A", "B")]
        if not all(value is not None for value in means):
            continue
        candidates.append(
            (
                -min(float(means[0]), float(means[1])),
                abs(float(means[0]) - float(means[1])),
                float(writer.fraction),
                int(writer.dwell),
                writer,
            )
        )
    if not candidates:
        writer = spec.writers[-1]
    else:
        writer = min(candidates, key=lambda value: value[:4])[4]
    return LineageWriterSpec(
        f"{engine}.diagnostic-natural",
        engine,
        "natural",
        float(writer.fraction),
        int(writer.dwell),
    )


def _selected_writers(
    paths: dict[str, Path], smoke: bool
) -> tuple[tuple[LineageWriterSpec, ...], dict[str, Any]]:
    writers: list[LineageWriterSpec] = []
    summary: dict[str, Any] = {}
    for engine in ("wagner", "boolean"):
        spec = _writer_screen_spec(engine, smoke)
        analysis = read_json(paths[engine] / "analysis.json")
        selected = select_weakest_balanced_cues(analysis, spec)
        passed = engine in selected
        writer = (
            _writer_from_dose(engine, selected[engine])
            if passed
            else _diagnostic_writer(engine, analysis, spec)
        )
        writers.append(writer)
        summary[engine] = {
            "passed": passed,
            "writer": writer.to_dict() if hasattr(writer, "to_dict") else {
                "name": writer.name,
                "engine": writer.engine,
                "mode": writer.mode,
                "cue_fraction": writer.cue_fraction,
                "cue_dwell": writer.cue_dwell,
            },
            "diagnostic_only": not passed,
        }
    return tuple(writers), summary


def _carrier_lookup(name: str) -> Any:
    return next(value for value in carrier_grid() if value.name == name)


def _scoped_candidates(selections: dict[str, list[str] | tuple[str, ...]]) -> tuple[Any, ...]:
    engines_by_name: dict[str, set[str]] = {}
    for engine, names in selections.items():
        for name in names:
            engines_by_name.setdefault(str(name), set()).add(engine)
    return tuple(
        replace(
            _carrier_lookup(name),
            engines=tuple(engine for engine in ("boolean", "wagner") if engine in engines),
        )
        for name, engines in sorted(engines_by_name.items())
    )


def _record_count(path: Path) -> int:
    manifest = path / "manifest.json"
    return int(read_json(manifest)["record_count"]) if manifest.is_file() else 0


def _guard_budget(used: int, predicted: int) -> None:
    if used + predicted > LINEAGE_RECORD_CAP:
        raise RuntimeError(
            f"lineage record cap would be exceeded: {used + predicted:,} > "
            f"{LINEAGE_RECORD_CAP:,}"
        )


def _boundary(
    root: Path,
    requested: str,
    active: str,
    completed: list[str],
    started: float,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _atomic_json(root / "campaign-manifest.json", manifest)
    _progress(root, active, completed, started, "requested boundary reached")
    return manifest


def run_lineage_carrier_campaign(
    root: Path,
    parent: Path,
    through: str = "discovery",
    workers: int = 8,
    progress: Callable[[str], None] | None = None,
    *,
    smoke: bool = False,
) -> Path:
    """Run or resume the registered Wagner-primary lineage experiment."""

    if through not in THROUGH_VALUES:
        raise ValueError(f"lineage through must be one of {THROUGH_VALUES}")
    if workers < 1 or workers > MAXIMUM_WORKERS:
        raise ValueError("lineage campaign requires 1-8 aggregate workers")
    root = root.resolve()
    parent = parent.resolve()
    parent_seal = parent / "wave-1" / "SHA256SUMS"
    if not parent_seal.is_file():
        raise FileNotFoundError(f"sealed Plastic Heredity v2 Wave 1 not found: {parent}")
    fresh = not root.exists()
    if fresh and shutil.disk_usage(root.parent).free < MINIMUM_FREE_DISK_BYTES:
        raise RuntimeError("fresh lineage campaign requires at least 40 GiB free")
    root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    completed: list[str] = []
    parent_digest = sha256_file(parent_seal)
    registration = {
        "format": LINEAGE_CAMPAIGN_FORMAT,
        "protocol_family": "wagner-lineage-carrier-v1",
        "parent": str(parent),
        "parent_wave_1_checksum_digest": parent_digest,
        "engine_scope": "Wagner primary; reduced Boolean benchmark",
        "lineage_record_cap": LINEAGE_RECORD_CAP,
        "worker_cap": MAXIMUM_WORKERS,
        "scientific_boundaries": list(THROUGH_VALUES),
        "smoke": smoke,
    }
    registration["registration_digest"] = canonical_digest(registration)
    registration_path = root / "campaign-registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing lineage campaign registration differs")
    else:
        _atomic_json(registration_path, registration)
    if sha256_file(parent_seal) != parent_digest:
        raise ValueError("parent Wave 1 seal changed during lineage registration")
    used_records = 0

    fixture = root / "fixture"
    _progress(root, "fixture", completed, started, "deterministic lineage handoff fixture")
    fixture_writers = (
        LineageWriterSpec("wagner.fixture-natural", "wagner", "natural", 1.0, 4),
        LineageWriterSpec("boolean.fixture-natural", "boolean", "natural", 1.0, 4),
    )
    fixture_spec = carrier_calibration_spec(fixture_writers, smoke=True)
    run_lineage_study(fixture_spec, fixture, min(2, workers), progress)
    completed.append("fixture")
    used_records += _record_count(fixture)

    writer_paths = {
        engine: root / "writer-calibration" / engine for engine in ("wagner", "boolean")
    }
    for engine in ("wagner", "boolean"):
        _progress(
            root,
            f"writer-calibration/{engine}",
            completed,
            started,
            f"fresh {engine} acquisition-only natural-writer calibration",
        )
        run_v2_state_study(
            _writer_screen_spec(engine, smoke), writer_paths[engine], workers, progress
        )
        completed.append(f"writer-calibration/{engine}")
        used_records += _record_count(writer_paths[engine])
    writers, writer_summary = _selected_writers(writer_paths, smoke)
    _atomic_json(
        root / "writer-selection.json",
        {
            "format": LINEAGE_SELECTION_FORMAT,
            "selection_uses_acquisition_only": True,
            "engines": writer_summary,
        },
    )
    base_manifest: dict[str, Any] = {
        "format": LINEAGE_CAMPAIGN_FORMAT,
        "requested_through": through,
        "parent_wave_1_checksum_digest": parent_digest,
        "writer_selection": writer_summary,
        "carrier_selection": None,
        "discovery_selection": None,
        "confirmation": None,
        "compatibility": None,
        "evolution": None,
        "record_budget": {"used": used_records, "cap": LINEAGE_RECORD_CAP},
        "completed": False,
    }
    if not writer_summary["wagner"]["passed"] and not smoke:
        base_manifest["stopped_reason"] = "no balanced natural Wagner writer"
        _boundary(
            root,
            through,
            "stopped-after-writer-calibration",
            completed,
            started,
            base_manifest,
        )
        return root

    calibration = root / "carrier-calibration"
    calibration_spec = carrier_calibration_spec(writers, smoke=smoke)
    _guard_budget(used_records, expected_lineage_records(calibration_spec))
    _progress(
        root,
        "carrier-calibration",
        completed,
        started,
        "natural writing of trace, field, and latch candidates",
    )
    run_lineage_study(calibration_spec, calibration, workers, progress)
    completed.append("carrier-calibration")
    used_records += _record_count(calibration)
    calibration_analysis = read_json(calibration / "analysis.json")
    carrier_selection = select_calibrated_carriers(calibration_analysis)
    wagner_names = list(carrier_selection["wagner"])
    if smoke and not wagner_names and carrier_selection["wagner_benchmark"] is not None:
        wagner_names = [str(carrier_selection["wagner_benchmark"])]
    boolean_name = carrier_selection["boolean_benchmark"]
    selections = {"wagner": wagner_names, "boolean": [boolean_name] if boolean_name else []}
    candidates = _scoped_candidates(selections)
    _atomic_json(
        root / "carrier-selection.json",
        {
            "format": LINEAGE_SELECTION_FORMAT,
            "maximum_wagner": 2,
            "maximum_boolean_benchmark": 1,
            "selected": selections,
            "boolean_is_nonblocking_benchmark": True,
        },
    )
    base_manifest["carrier_selection"] = selections
    base_manifest["record_budget"] = {"used": used_records, "cap": LINEAGE_RECORD_CAP}
    if not wagner_names:
        base_manifest["stopped_reason"] = "no naturally written Wagner carrier calibrated"
        _boundary(
            root,
            through,
            "stopped-after-carrier-calibration",
            completed,
            started,
            base_manifest,
        )
        return root

    discovery = root / "discovery"
    discovery_spec = lineage_discovery_spec(writers, candidates, smoke=smoke)
    _guard_budget(used_records, expected_lineage_records(discovery_spec))
    _progress(
        root,
        "discovery",
        completed,
        started,
        "minimal bottleneck and multigeneration causal discovery",
    )
    run_lineage_study(discovery_spec, discovery, workers, progress)
    completed.append("discovery")
    used_records += _record_count(discovery)
    discovery_analysis = read_json(discovery / "analysis.json")
    discovery_selection = select_discovery_candidate(discovery_analysis)
    if smoke and discovery_selection is None:
        discovery_selection = {
            "engine": "wagner",
            "candidate": wagner_names[0],
            "arm": "natural-full",
            "k": 10,
            "generation_8_risk_lower": None,
            "smoke_fallback": True,
        }
    _atomic_json(
        root / "discovery-selection.json",
        {
            "format": LINEAGE_SELECTION_FORMAT,
            "selection_rule": "smallest passing k, then generation-8 risk lower bound",
            "selected": discovery_selection,
        },
    )
    base_manifest["discovery_selection"] = discovery_selection
    base_manifest["record_budget"] = {"used": used_records, "cap": LINEAGE_RECORD_CAP}
    if through == "discovery" or discovery_selection is None:
        if discovery_selection is None:
            base_manifest["stopped_reason"] = "no Wagner carrier passed discovery"
        _boundary(
            root,
            through,
            "paused-after-discovery",
            completed,
            started,
            base_manifest,
        )
        return root

    selected_name = str(discovery_selection["candidate"])
    selected_k = int(discovery_selection["k"])
    confirmation_selections = {"wagner": [selected_name], "boolean": []}
    if boolean_name is not None:
        confirmation_selections["boolean"] = [str(boolean_name)]
    confirmation_candidates = _scoped_candidates(confirmation_selections)
    confirmation = root / "confirmation"
    confirmation_spec = lineage_confirmation_spec(
        writers, confirmation_candidates, selected_k, smoke=smoke
    )
    _guard_budget(used_records, expected_lineage_records(confirmation_spec))
    _progress(
        root,
        "confirmation",
        completed,
        started,
        "untouched minimal-carrier multigeneration confirmation",
    )
    run_lineage_study(confirmation_spec, confirmation, workers, progress)
    completed.append("confirmation")
    used_records += _record_count(confirmation)
    confirmation_analysis = read_json(confirmation / "analysis.json")
    selected_arm = f"selected-targeted-k{selected_k}"
    matching_gates = [
        gate
        for gate in confirmation_analysis["lineage_gates"].values()
        if gate["engine"] == "wagner"
        and gate["candidate"] == selected_name
        and gate["arm"] == selected_arm
    ]
    observed_confirmed = bool(matching_gates and matching_gates[0]["passed"])
    confirmed = observed_confirmed or smoke
    base_manifest["confirmation"] = {
        "launched": True,
        "candidate": selected_name,
        "k": selected_k,
        "passed": observed_confirmed,
        "smoke_forced_advance": bool(smoke and not observed_confirmed),
        "failed_criteria": []
        if observed_confirmed or not matching_gates
        else [name for name, value in matching_gates[0]["criteria"].items() if not value],
    }
    base_manifest["record_budget"] = {"used": used_records, "cap": LINEAGE_RECORD_CAP}
    if through == "confirmation" or not confirmed:
        if not confirmed:
            base_manifest["stopped_reason"] = "Wagner minimal carrier did not confirm"
        _boundary(
            root,
            through,
            "paused-after-confirmation",
            completed,
            started,
            base_manifest,
        )
        return root

    selected_writer = next(value for value in writers if value.engine == "wagner")
    selected_candidate = replace(_carrier_lookup(selected_name), engines=("wagner",))
    compatibility = root / "compatibility"
    compatibility_protocol = compatibility_spec(
        selected_writer, selected_candidate, selected_k, smoke=smoke
    )
    _guard_budget(used_records, expected_lineage_records(compatibility_protocol))
    _progress(
        root,
        "compatibility",
        completed,
        started,
        "clone, destination-matched, and descriptor-matched recipients",
    )
    run_lineage_study(compatibility_protocol, compatibility, workers, progress)
    completed.append("compatibility")
    used_records += _record_count(compatibility)
    compatibility_analysis = read_json(compatibility / "analysis.json")
    base_manifest["compatibility"] = {
        "launched": True,
        "recipient_modes": list(compatibility_protocol.recipient_modes),
        "analysis_format": compatibility_analysis["format"],
    }

    evolution = root / "evolution-pilot"
    _progress(
        root,
        "evolution-pilot",
        completed,
        started,
        "prospective selection for generation-4 transmission fidelity",
    )
    run_lineage_evolution(
        evolution_spec(selected_writer, selected_candidate, selected_k, smoke=smoke),
        evolution,
        workers,
        progress,
    )
    completed.append("evolution-pilot")
    evolution_analysis = read_json(evolution / "analysis.json")
    base_manifest["evolution"] = {
        "launched": True,
        "passed": evolution_analysis["passed"],
        "claim_boundary": evolution_analysis["claim_boundary"],
    }
    base_manifest["record_budget"] = {"used": used_records, "cap": LINEAGE_RECORD_CAP}
    base_manifest["completed"] = True
    _boundary(
        root,
        through,
        "completed",
        completed,
        started,
        base_manifest,
    )
    return root


def lineage_carrier_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    result: dict[str, Any] = {
        "format": "gre-wagner-lineage-status-v1",
        "root": str(root),
        "registered": (root / "campaign-registration.json").is_file(),
        "progress": read_json(root / "progress.json")
        if (root / "progress.json").is_file()
        else None,
        "stages": {},
        "active_eta_seconds": None,
    }
    stages = (
        root / "fixture",
        root / "writer-calibration" / "wagner",
        root / "writer-calibration" / "boolean",
        root / "carrier-calibration",
        root / "discovery",
        root / "confirmation",
        root / "compatibility",
        root / "evolution-pilot",
    )
    for stage in stages:
        if not stage.exists():
            continue
        label = str(stage.relative_to(root))
        progress_path = stage / "progress.json"
        stage_progress = read_json(progress_path) if progress_path.is_file() else None
        result["stages"][label] = {
            "sealed": (stage / "SHA256SUMS").is_file(),
            "progress": stage_progress,
        }
        if stage_progress and not (stage / "SHA256SUMS").is_file():
            eta = stage_progress.get("eta_seconds")
            if eta is not None:
                result["active_eta_seconds"] = float(eta)
    if (root / "campaign-manifest.json").is_file():
        manifest = read_json(root / "campaign-manifest.json")
        result["campaign"] = {
            "completed": manifest.get("completed", False),
            "stopped_reason": manifest.get("stopped_reason"),
            "writer_selection": manifest.get("writer_selection"),
            "carrier_selection": manifest.get("carrier_selection"),
            "discovery_selection": manifest.get("discovery_selection"),
            "confirmation": manifest.get("confirmation"),
            "evolution": manifest.get("evolution"),
            "record_budget": manifest.get("record_budget"),
        }
    return result


def verify_lineage_carrier_campaign(root: Path) -> dict[str, Any]:
    root = root.resolve()
    registration = read_json(root / "campaign-registration.json")
    if registration.get("format") != LINEAGE_CAMPAIGN_FORMAT:
        raise ValueError("lineage campaign registration format mismatch")
    parent_seal = Path(registration["parent"]) / "wave-1" / "SHA256SUMS"
    if sha256_file(parent_seal) != registration["parent_wave_1_checksum_digest"]:
        raise ValueError("lineage campaign parent Wave 1 checksum changed")
    verified: dict[str, Any] = {}
    writer_stages = (
        root / "writer-calibration" / "wagner",
        root / "writer-calibration" / "boolean",
    )
    for stage in writer_stages:
        if (stage / "SHA256SUMS").is_file():
            verified[str(stage.relative_to(root))] = verify_v2_state_study(stage)
    for name in ("fixture", "carrier-calibration", "discovery", "confirmation", "compatibility"):
        stage = root / name
        if (stage / "SHA256SUMS").is_file():
            verified[name] = verify_lineage_study(stage)
    evolution = root / "evolution-pilot"
    if (evolution / "SHA256SUMS").is_file():
        verified["evolution-pilot"] = verify_lineage_evolution(evolution)
    return {
        "verified": bool(verified),
        "registration_digest": registration["registration_digest"],
        "stages": verified,
    }


def replay_lineage_campaign_future(root: Path, future_id: str) -> dict[str, Any]:
    root = root.resolve()
    for stage in (
        root / "fixture",
        root / "carrier-calibration",
        root / "discovery",
        root / "confirmation",
        root / "compatibility",
    ):
        if not (stage / "futures.jsonl.gz").is_file():
            continue
        try:
            return replay_lineage_future(stage, future_id)
        except KeyError:
            pass
    for stage in (
        root / "writer-calibration" / "wagner",
        root / "writer-calibration" / "boolean",
    ):
        if not (stage / "executor" / "futures.jsonl.gz").is_file():
            continue
        try:
            return replay_v2_state_future(stage, future_id)
        except KeyError:
            pass
    raise KeyError(f"unknown lineage campaign future: {future_id}")
