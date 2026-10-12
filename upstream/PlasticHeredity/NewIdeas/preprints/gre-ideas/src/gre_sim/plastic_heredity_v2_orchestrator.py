"""Resumable orchestration for the complete Plastic Heredity v2 program."""

from __future__ import annotations

import shutil
import time
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
from .plastic_heredity_v2_analysis import (
    passing_engines,
    select_weakest_balanced_cues,
)
from .plastic_heredity_v2_atlas import analyze_atlas_run, nominate_atlas_variants
from .plastic_heredity_v2_carriers import (
    expected_carrier_futures,
    replay_carrier_future,
    run_carrier_study,
    select_carrier_candidates,
    verify_carrier_study,
)
from .plastic_heredity_v2_config import (
    PLASTIC_HEREDITY_V2_REGISTRATION_FORMAT,
    PLASTIC_HEREDITY_V2_WAVE_FORMAT,
    CarrierV2Spec,
)
from .plastic_heredity_v2_evolution import run_v2_evolution, verify_v2_evolution
from .plastic_heredity_v2_gard import run_v2_gard_split
from .plastic_heredity_v2_protocols import (
    carrier_calibration_spec,
    carrier_confirmation_spec,
    carrier_discovery_spec,
    carrier_grid,
    exact_state_confirmation_spec,
    exact_state_discovery_spec,
    exact_state_fixture_spec,
    mechanism_atlas_confirmation_specs,
    mechanism_atlas_specs,
    natural_cue_calibration_spec,
    natural_cue_state_spec,
    posthoc_rescore_spec,
    prospective_evolution_spec,
    substrate_native_calibration_spec,
    substrate_native_carrier_grid,
    substrate_native_confirmation_spec,
    substrate_native_discovery_spec,
)
from .plastic_heredity_v2_rescore import (
    run_common_endpoint_rescore,
    verify_common_endpoint_rescore,
)
from .plastic_heredity_v2_study import (
    replay_v2_state_future,
    run_v2_state_study,
    verify_v2_state_study,
)
from .plastic_memory_campaign import expected_memory_source_futures
from .plastic_memory_gard import replay_gard_memory_future
from .plastic_memory_study import (
    replay_memory_future,
    run_memory_study,
    verify_memory_run,
)


MINIMUM_FREE_DISK_BYTES = 40 * 1024**3
MAXIMUM_WORKERS = 8
WAVE_2_FUTURE_CAP = 30_000_000
THROUGH_VALUES = ("wave-1", "wave-2", "full")


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
            "format": "gre-plastic-heredity-v2-progress-v1",
            "active_stage": active,
            "completed_stages": completed,
            "elapsed_seconds": time.monotonic() - started,
            "message": message,
        },
    )


def _memory_future_count(spec: Any) -> int:
    return sum(
        source.count * expected_memory_source_futures(spec, source.name)
        for source in spec.sources
    )


def _seal_wave(path: Path, manifest: dict[str, Any]) -> None:
    _atomic_json(path / "wave-manifest.json", manifest)
    write_checksums(path)
    verify_checksums(path)


def _notify(progress: Callable[[str], None] | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _state_report_summary(path: Path) -> dict[str, Any]:
    analysis = read_json(path / "analysis.json")
    return {
        "passing_engines": list(passing_engines(analysis)),
        "fair_engine_verdict": analysis["fair_engine_verdict"],
        "gates": {
            gate["engine"]: {
                "passed": gate["passed"],
                "failed_criteria": [
                    name for name, passed in gate["criteria"].items() if not passed
                ],
            }
            for gate in analysis["state_channel_gates"].values()
        },
    }


def _run_wave_1(
    root: Path,
    parent_evolution: Path,
    workers: int,
    progress: Callable[[str], None] | None,
    completed: list[str],
    campaign_started: float,
) -> dict[str, Any]:
    wave = root / "wave-1"
    wave.mkdir(exist_ok=True)
    if (wave / "SHA256SUMS").is_file():
        verify_checksums(wave)
        return read_json(wave / "wave-manifest.json")
    fixture = root / "fixture"
    _progress(root, "fixture", completed, campaign_started, "deterministic v2 fixture")
    run_v2_state_study(exact_state_fixture_spec(), fixture, min(2, workers), progress)
    completed.append("fixture")

    discovery = wave / "state-discovery"
    _progress(
        root,
        "wave-1/state-discovery",
        completed,
        campaign_started,
        "matched exact-state Boolean/Wagner discovery",
    )
    run_v2_state_study(exact_state_discovery_spec(), discovery, workers, progress)
    completed.append("wave-1/state-discovery")
    discovery_summary = _state_report_summary(discovery)

    confirmation_summary = None
    confirmation_launched = bool(discovery_summary["passing_engines"])
    if confirmation_launched:
        confirmation = wave / "state-confirmation"
        _progress(
            root,
            "wave-1/state-confirmation",
            completed,
            campaign_started,
            "untouched fair-engine exact-state confirmation",
        )
        # If either engine advances, both are carried forward. This preserves the
        # registered fair-engine contrast and avoids asymmetric survivor selection.
        run_v2_state_study(exact_state_confirmation_spec(), confirmation, workers, progress)
        completed.append("wave-1/state-confirmation")
        confirmation_summary = _state_report_summary(confirmation)

    rescore = wave / "evolution-common-rescore"
    _progress(
        root,
        "wave-1/evolution-common-rescore",
        completed,
        campaign_started,
        "post-hoc common-endpoint rescore of 192 archived populations",
    )
    run_common_endpoint_rescore(
        posthoc_rescore_spec(str(parent_evolution.resolve())),
        rescore,
        workers,
        progress,
    )
    completed.append("wave-1/evolution-common-rescore")
    manifest = {
        "format": PLASTIC_HEREDITY_V2_WAVE_FORMAT,
        "wave": 1,
        "completed": True,
        "state_discovery": discovery_summary,
        "state_confirmation_launched": confirmation_launched,
        "state_confirmation": confirmation_summary,
        "common_rescore": read_json(rescore / "analysis.json"),
        "interpretation": (
            "Exact-state capacity and the corrected evolutionary rescore are separate. "
            "The rescore is post-hoc and cannot confirm evolutionary response."
        ),
    }
    _seal_wave(wave, manifest)
    return manifest


def _unique_carriers(names: list[str]) -> tuple[CarrierV2Spec, ...]:
    catalog = {
        value.name: value
        for value in (*carrier_grid(), *substrate_native_carrier_grid())
    }
    result: list[CarrierV2Spec] = []
    for name in names:
        if name not in catalog:
            raise ValueError(f"unknown selected v2 carrier: {name}")
        if catalog[name] not in result:
            result.append(catalog[name])
    return tuple(result)


def _run_wave_2(
    root: Path,
    workers: int,
    progress: Callable[[str], None] | None,
    completed: list[str],
    campaign_started: float,
) -> dict[str, Any]:
    wave = root / "wave-2"
    wave.mkdir(exist_ok=True)
    if (wave / "SHA256SUMS").is_file():
        verify_checksums(wave)
        return read_json(wave / "wave-manifest.json")
    actual_future_budget = 0

    calibration_spec = natural_cue_calibration_spec()
    calibration = wave / "natural-cue-calibration"
    _progress(root, "wave-2/natural-cue-calibration", completed, campaign_started, "natural cue calibration")
    run_v2_state_study(calibration_spec, calibration, workers, progress)
    completed.append("wave-2/natural-cue-calibration")
    actual_future_budget += int(read_json(calibration / "manifest.json")["record_count"])
    cue_selection = select_weakest_balanced_cues(
        read_json(calibration / "analysis.json"), calibration_spec
    )
    _atomic_json(
        wave / "natural-cue-selection.json",
        {
            "format": "gre-plastic-heredity-v2-natural-cue-selection-v1",
            "selection_uses_acquisition_only": True,
            "selected": {
                engine: {"fraction": dose.fraction, "dwell": dose.dwell}
                for engine, dose in cue_selection.items()
            },
        },
    )
    natural_summary: dict[str, Any] = {
        "calibrated_engines": sorted(cue_selection),
        "discovery_launched": False,
        "confirmation_launched": False,
    }
    if set(cue_selection) == {"boolean", "wagner"}:
        natural_discovery_spec = natural_cue_state_spec(cue_selection, False)
        natural_discovery = wave / "natural-cue-discovery"
        _progress(root, "wave-2/natural-cue-discovery", completed, campaign_started, "natural writer transfer discovery")
        run_v2_state_study(natural_discovery_spec, natural_discovery, workers, progress)
        completed.append("wave-2/natural-cue-discovery")
        actual_future_budget += int(read_json(natural_discovery / "manifest.json")["record_count"])
        natural_summary["discovery_launched"] = True
        natural_summary["discovery"] = _state_report_summary(natural_discovery)
        if natural_summary["discovery"]["passing_engines"]:
            natural_confirmation_spec = natural_cue_state_spec(cue_selection, True)
            predicted = _memory_future_count(natural_confirmation_spec.memory_spec())
            if actual_future_budget + predicted > WAVE_2_FUTURE_CAP:
                raise RuntimeError("registered Wave 2 future cap would be exceeded")
            natural_confirmation = wave / "natural-cue-confirmation"
            _progress(root, "wave-2/natural-cue-confirmation", completed, campaign_started, "untouched natural writer confirmation")
            run_v2_state_study(natural_confirmation_spec, natural_confirmation, workers, progress)
            completed.append("wave-2/natural-cue-confirmation")
            actual_future_budget += int(read_json(natural_confirmation / "manifest.json")["record_count"])
            natural_summary["confirmation_launched"] = True
            natural_summary["confirmation"] = _state_report_summary(natural_confirmation)

    atlas_root = wave / "mechanism-atlas"
    atlas_root.mkdir(exist_ok=True)
    atlas_analyses: list[dict[str, Any]] = []
    for index, atlas_spec in enumerate(mechanism_atlas_specs()):
        predicted = _memory_future_count(atlas_spec)
        if actual_future_budget + predicted > WAVE_2_FUTURE_CAP:
            raise RuntimeError("registered Wave 2 future cap would be exceeded by atlas")
        stage = atlas_root / f"discovery-flip-{atlas_spec.expression_flip_probability:g}"
        _progress(root, str(stage.relative_to(root)), completed, campaign_started, "mechanism atlas discovery")
        run_memory_study(atlas_spec, stage, workers, progress)
        completed.append(str(stage.relative_to(root)))
        actual_future_budget += int(read_json(stage / "manifest.json")["record_count"])
        analysis = analyze_atlas_run(stage)
        atlas_analyses.append(analysis)
        _atomic_json(atlas_root / f"analysis-{index}.json", analysis)
    nominations = nominate_atlas_variants(atlas_analyses)
    _atomic_json(
        atlas_root / "nominations.json",
        {
            "format": "gre-plastic-heredity-v2-atlas-nominations-v1",
            "maximum": 2,
            "nominations": list(nominations),
        },
    )
    atlas_confirmation_summaries: list[dict[str, Any]] = []
    if nominations:
        for index, atlas_spec in enumerate(mechanism_atlas_confirmation_specs(nominations)):
            predicted = _memory_future_count(atlas_spec)
            if actual_future_budget + predicted > WAVE_2_FUTURE_CAP:
                raise RuntimeError("registered Wave 2 future cap would be exceeded by atlas confirmation")
            stage = atlas_root / f"confirmation-{index}"
            _progress(root, str(stage.relative_to(root)), completed, campaign_started, "untouched mechanism variant confirmation")
            run_memory_study(atlas_spec, stage, workers, progress)
            completed.append(str(stage.relative_to(root)))
            actual_future_budget += int(read_json(stage / "manifest.json")["record_count"])
            analysis = analyze_atlas_run(stage)
            atlas_confirmation_summaries.append(analysis)
            _atomic_json(atlas_root / f"confirmation-analysis-{index}.json", analysis)

    carrier_calibration = wave / "carrier-calibration"
    carrier_cal_spec = carrier_calibration_spec()
    predicted = expected_carrier_futures(carrier_cal_spec)
    if actual_future_budget + predicted > WAVE_2_FUTURE_CAP:
        raise RuntimeError("registered Wave 2 future cap would be exceeded by carrier calibration")
    _progress(root, "wave-2/carrier-calibration", completed, campaign_started, "trace, field, and latch calibration")
    run_carrier_study(carrier_cal_spec, carrier_calibration, workers, progress)
    completed.append("wave-2/carrier-calibration")
    actual_future_budget += int(read_json(carrier_calibration / "manifest.json")["record_count"])
    carrier_selection = select_carrier_candidates(
        read_json(carrier_calibration / "analysis.json"), 2
    )
    _atomic_json(
        wave / "carrier-calibration-selection.json",
        {
            "format": "gre-plastic-heredity-v2-carrier-selection-v1",
            "maximum_per_engine": 2,
            "selected": {key: list(value) for key, value in carrier_selection.items()},
        },
    )
    discovery_candidates = _unique_carriers(
        [name for engine in ("boolean", "wagner") for name in carrier_selection[engine]]
    )
    carrier_summary: dict[str, Any] = {
        "calibration_selection": {key: list(value) for key, value in carrier_selection.items()},
        "discovery_launched": False,
        "confirmation_launched": False,
    }
    if discovery_candidates:
        carrier_disc_spec = carrier_discovery_spec(discovery_candidates)
        predicted = expected_carrier_futures(carrier_disc_spec)
        if actual_future_budget + predicted > WAVE_2_FUTURE_CAP:
            raise RuntimeError("registered Wave 2 future cap would be exceeded by carrier discovery")
        carrier_discovery = wave / "carrier-discovery"
        _progress(root, "wave-2/carrier-discovery", completed, campaign_started, "causal carrier discovery")
        run_carrier_study(carrier_disc_spec, carrier_discovery, workers, progress)
        completed.append("wave-2/carrier-discovery")
        actual_future_budget += int(read_json(carrier_discovery / "manifest.json")["record_count"])
        carrier_summary["discovery_launched"] = True
        discovery_analysis = read_json(carrier_discovery / "analysis.json")
        confirmation_names: list[str] = []
        for engine in ("boolean", "wagner"):
            passing = [
                gate
                for gate in discovery_analysis["carrier_gates"].values()
                if gate["engine"] == engine and gate["passed"]
            ]
            passing.sort(
                key=lambda gate: (
                    -float(gate["primary"]["risk_difference"]["mean"]),
                    gate["candidate"],
                )
            )
            if passing:
                confirmation_names.append(str(passing[0]["candidate"]))
        confirmation_candidates = _unique_carriers(confirmation_names)
        if confirmation_candidates:
            carrier_conf_spec = carrier_confirmation_spec(confirmation_candidates)
            predicted = expected_carrier_futures(carrier_conf_spec)
            if actual_future_budget + predicted > WAVE_2_FUTURE_CAP:
                raise RuntimeError("registered Wave 2 future cap would be exceeded by carrier confirmation")
            carrier_confirmation = wave / "carrier-confirmation"
            _progress(root, "wave-2/carrier-confirmation", completed, campaign_started, "untouched causal carrier confirmation")
            run_carrier_study(carrier_conf_spec, carrier_confirmation, workers, progress)
            completed.append("wave-2/carrier-confirmation")
            actual_future_budget += int(read_json(carrier_confirmation / "manifest.json")["record_count"])
            carrier_summary["confirmation_launched"] = True
            carrier_summary["confirmed"] = [
                gate["candidate"]
                for gate in read_json(carrier_confirmation / "analysis.json")["carrier_gates"].values()
                if gate["passed"]
            ]

    if actual_future_budget > WAVE_2_FUTURE_CAP:
        raise RuntimeError("Wave 2 exceeded its registered 30-million-future cap")
    manifest = {
        "format": PLASTIC_HEREDITY_V2_WAVE_FORMAT,
        "wave": 2,
        "completed": True,
        "future_budget": {
            "actual": actual_future_budget,
            "cap": WAVE_2_FUTURE_CAP,
        },
        "natural_cue": natural_summary,
        "mechanism_atlas": {
            "nominations": list(nominations),
            "confirmation_analyses": atlas_confirmation_summaries,
        },
        "engine_neutral_carriers": carrier_summary,
    }
    _seal_wave(wave, manifest)
    return manifest


def _run_wave_3(
    root: Path,
    wave_1: dict[str, Any],
    wave_2: dict[str, Any],
    gard_root: Path | None,
    workers: int,
    progress: Callable[[str], None] | None,
    completed: list[str],
    campaign_started: float,
) -> dict[str, Any]:
    wave = root / "wave-3"
    wave.mkdir(exist_ok=True)
    if (wave / "SHA256SUMS").is_file():
        verify_checksums(wave)
        return read_json(wave / "wave-manifest.json")
    confirmed_state = wave_1.get("state_confirmation") or {}
    confirmed_engines = set(confirmed_state.get("passing_engines", []))
    confirmed_carriers = set(
        wave_2.get("engine_neutral_carriers", {}).get("confirmed", [])
    )
    native_summary: dict[str, Any] = {
        "required": not bool(confirmed_carriers),
        "calibration_launched": False,
        "discovery_launched": False,
        "confirmation_launched": False,
        "claim_scope": "substrate-specific only",
    }
    if not confirmed_carriers:
        native_calibration = wave / "native-carrier-calibration"
        native_cal_spec = substrate_native_calibration_spec()
        _progress(root, "wave-3/native-carrier-calibration", completed, campaign_started, "substrate-native edge and transition trace calibration")
        run_carrier_study(native_cal_spec, native_calibration, workers, progress)
        completed.append("wave-3/native-carrier-calibration")
        native_summary["calibration_launched"] = True
        selection = select_carrier_candidates(
            read_json(native_calibration / "analysis.json"), 1
        )
        native_summary["calibration_selection"] = {
            key: list(value) for key, value in selection.items()
        }
        candidates = _unique_carriers(
            [name for engine in ("boolean", "wagner") for name in selection[engine]]
        )
        if candidates:
            native_discovery = wave / "native-carrier-discovery"
            _progress(root, "wave-3/native-carrier-discovery", completed, campaign_started, "substrate-native carrier causal discovery")
            run_carrier_study(
                substrate_native_discovery_spec(candidates),
                native_discovery,
                workers,
                progress,
            )
            completed.append("wave-3/native-carrier-discovery")
            native_summary["discovery_launched"] = True
            discovery_analysis = read_json(native_discovery / "analysis.json")
            passing_names = [
                gate["candidate"]
                for gate in discovery_analysis["carrier_gates"].values()
                if gate["passed"]
            ]
            confirmation_candidates = _unique_carriers(passing_names)
            if confirmation_candidates:
                native_confirmation = wave / "native-carrier-confirmation"
                _progress(root, "wave-3/native-carrier-confirmation", completed, campaign_started, "untouched substrate-native carrier confirmation")
                run_carrier_study(
                    substrate_native_confirmation_spec(confirmation_candidates),
                    native_confirmation,
                    workers,
                    progress,
                )
                completed.append("wave-3/native-carrier-confirmation")
                native_summary["confirmation_launched"] = True
                native_summary["confirmed"] = [
                    gate["candidate"]
                    for gate in read_json(native_confirmation / "analysis.json")[
                        "carrier_gates"
                    ].values()
                    if gate["passed"]
                ]
    evolution_launched = "wagner" in confirmed_engines or bool(confirmed_carriers)
    evolution_confirmation_launched = False
    evolution_summary = None
    if evolution_launched:
        exploratory = prospective_evolution_spec(str(root), False)
        stage = wave / "evolution-discovery"
        _progress(root, "wave-3/evolution-discovery", completed, campaign_started, "prospective common-assay evolution")
        run_v2_evolution(exploratory, stage, workers, progress)
        completed.append("wave-3/evolution-discovery")
        analysis = read_json(stage / "analysis.json")
        evolution_summary = analysis
        if analysis["response_gate"]["passed"]:
            confirmation = prospective_evolution_spec(str(root), True)
            stage = wave / "evolution-confirmation"
            _progress(root, "wave-3/evolution-confirmation", completed, campaign_started, "untouched common-assay evolution confirmation")
            run_v2_evolution(confirmation, stage, workers, progress)
            completed.append("wave-3/evolution-confirmation")
            evolution_confirmation_launched = True
            evolution_summary = read_json(stage / "analysis.json")
    gard_launched = gard_root is not None
    gard_summary = None
    if gard_root is not None:
        stage = wave / "gard-split"
        _progress(root, "wave-3/gard-split", completed, campaign_started, "GARD exact capacity and natural writer split")
        run_v2_gard_split(gard_root, stage, workers, progress)
        completed.append("wave-3/gard-split")
        gard_summary = read_json(stage / "manifest.json")
    manifest = {
        "format": PLASTIC_HEREDITY_V2_WAVE_FORMAT,
        "wave": 3,
        "completed": True,
        "evolution_launched": evolution_launched,
        "evolution_confirmation_launched": evolution_confirmation_launched,
        "evolution": evolution_summary,
        "gard_launched": gard_launched,
        "gard": gard_summary,
        "substrate_native_fallback": native_summary,
    }
    _seal_wave(wave, manifest)
    return manifest


def _render_root_report(manifest: dict[str, Any]) -> str:
    wave_1 = manifest["waves"]["wave-1"]
    wave_2 = manifest["waves"]["wave-2"]
    wave_3 = manifest["waves"]["wave-3"]
    confirmation = wave_1.get("state_confirmation")
    verdict = (
        confirmation["fair_engine_verdict"]["verdict"]
        if confirmation is not None
        else wave_1["state_discovery"]["fair_engine_verdict"]["verdict"]
    )
    return "\n".join(
        (
            "# Plastic Heredity v2 campaign",
            "",
            f"- Completed: {manifest['completed']}",
            f"- Fair exact-state engine verdict: **{verdict}**",
            f"- Wave 2 futures: {wave_2['future_budget']['actual']:,}",
            f"- Prospective evolution launched: {wave_3['evolution_launched']}",
            f"- GARD split launched: {wave_3['gard_launched']}",
            "",
            "The campaign separates writing, state-channel capacity, engineered carrier "
            "causality, evolutionary response, and cross-substrate generality. A positive "
            "result at one level is not silently promoted to a stronger level.",
            "",
        )
    )


def run_plastic_heredity_v2_campaign(
    output_root: Path,
    through: str = "wave-1",
    workers: int = 8,
    parent_evolution: Path = Path("runs/wagner-heredity-v1/evolution-confirmation"),
    gard_root: Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or resume the registered one-day then two-to-three-day program."""

    if through not in THROUGH_VALUES:
        raise ValueError(f"through must be one of {THROUGH_VALUES}")
    if workers < 1 or workers > MAXIMUM_WORKERS:
        raise ValueError("Plastic Heredity v2 campaign requires 1-8 workers")
    parent_evolution = parent_evolution.resolve()
    verify_checksums(parent_evolution)
    output_root = output_root.resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    if not output_root.exists() and shutil.disk_usage(output_root.parent).free < MINIMUM_FREE_DISK_BYTES:
        raise OSError("less than 40 GiB free; refusing Plastic Heredity v2 campaign")
    output_root.mkdir(parents=True, exist_ok=True)
    if (output_root / "SHA256SUMS").is_file():
        verify_plastic_heredity_v2_campaign(output_root)
        return output_root
    registration = {
        "format": PLASTIC_HEREDITY_V2_REGISTRATION_FORMAT,
        "program": "one-day-wave-1-plus-two-to-three-day-extension-v1",
        "parent_evolution": str(parent_evolution),
        "parent_evolution_checksum_digest": sha256_file(parent_evolution / "SHA256SUMS"),
        "gard_root": str(gard_root.resolve()) if gard_root is not None else None,
        "source_access": {"parent_evolution": "read-only", "gard": "read-only"},
        "protocol_digests": {
            "fixture": canonical_digest(exact_state_fixture_spec().to_dict()),
            "state_discovery": canonical_digest(exact_state_discovery_spec().to_dict()),
            "state_confirmation": canonical_digest(exact_state_confirmation_spec().to_dict()),
            "cue_calibration": canonical_digest(natural_cue_calibration_spec().to_dict()),
            "carrier_calibration": canonical_digest(carrier_calibration_spec().to_dict()),
            "atlas_discovery": [canonical_digest(value.to_dict()) for value in mechanism_atlas_specs()],
            "common_rescore": canonical_digest(posthoc_rescore_spec(str(parent_evolution)).to_dict()),
        },
        "maximum_workers": MAXIMUM_WORKERS,
        "minimum_free_disk_bytes_at_start": MINIMUM_FREE_DISK_BYTES,
        "wave_2_future_cap": WAVE_2_FUTURE_CAP,
        "through_is_operational_not_scientific": True,
    }
    registration_path = output_root / "campaign-registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing Plastic Heredity v2 campaign registration differs")
    else:
        _atomic_json(registration_path, registration)
    started = time.monotonic()
    completed: list[str] = []
    wave_1 = _run_wave_1(
        output_root,
        parent_evolution,
        workers,
        progress,
        completed,
        started,
    )
    if through == "wave-1":
        _atomic_json(
            output_root / "campaign-state.json",
            {"completed_through": "wave-1", "resumable": True},
        )
        _progress(output_root, "paused-after-wave-1", completed, started, "requested boundary reached")
        return output_root
    wave_2 = _run_wave_2(output_root, workers, progress, completed, started)
    if through == "wave-2":
        _atomic_json(
            output_root / "campaign-state.json",
            {"completed_through": "wave-2", "resumable": True},
        )
        _progress(output_root, "paused-after-wave-2", completed, started, "requested boundary reached")
        return output_root
    wave_3 = _run_wave_3(
        output_root,
        wave_1,
        wave_2,
        gard_root,
        workers,
        progress,
        completed,
        started,
    )
    manifest = {
        "format": "gre-plastic-heredity-v2-campaign-manifest-v1",
        "completed": True,
        "elapsed_seconds": time.monotonic() - started,
        "waves": {"wave-1": wave_1, "wave-2": wave_2, "wave-3": wave_3},
    }
    _atomic_json(output_root / "campaign-manifest.json", manifest)
    _atomic_json(
        output_root / "campaign-state.json",
        {"completed_through": "full", "resumable": False},
    )
    _progress(output_root, "completed", completed, started, "all requested waves sealed")
    (output_root / "report.md").write_text(_render_root_report(manifest), encoding="utf-8")
    write_checksums(output_root)
    verify_plastic_heredity_v2_campaign(output_root)
    _notify(progress, "sealed complete Plastic Heredity v2 campaign")
    return output_root


def verify_plastic_heredity_v2_campaign(root: Path) -> dict[str, Any]:
    root = root.resolve()
    registration = read_json(root / "campaign-registration.json")
    if registration.get("format") != PLASTIC_HEREDITY_V2_REGISTRATION_FORMAT:
        raise ValueError("Plastic Heredity v2 registration format mismatch")
    parent = Path(registration["parent_evolution"])
    if sha256_file(parent / "SHA256SUMS") != registration.get(
        "parent_evolution_checksum_digest"
    ):
        raise ValueError("Plastic Heredity v2 parent checksum digest changed")
    complete = (root / "SHA256SUMS").is_file()
    checksums = verify_checksums(root) if complete else {}
    if (root / "fixture" / "SHA256SUMS").is_file():
        verify_v2_state_study(root / "fixture")
    verified_waves: list[str] = []
    for wave_name in ("wave-1", "wave-2", "wave-3"):
        wave = root / wave_name
        if (wave / "SHA256SUMS").is_file():
            verify_checksums(wave)
            verified_waves.append(wave_name)
    if "wave-1" in verified_waves:
        verify_v2_state_study(root / "wave-1" / "state-discovery")
        verify_common_endpoint_rescore(root / "wave-1" / "evolution-common-rescore")
        if (root / "wave-1" / "state-confirmation").is_dir():
            verify_v2_state_study(root / "wave-1" / "state-confirmation")
    if complete:
        manifest = read_json(root / "campaign-manifest.json")
        if manifest.get("format") != "gre-plastic-heredity-v2-campaign-manifest-v1":
            raise ValueError("Plastic Heredity v2 manifest format mismatch")
    return {
        "verified": True,
        "files": len(checksums),
        "completed": complete,
        "verified_waves": verified_waves,
    }


def plastic_heredity_v2_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    stages: dict[str, Any] = {}
    stage_paths = [
        root / "fixture",
        root / "wave-1" / "state-discovery",
        root / "wave-1" / "state-confirmation",
        root / "wave-1" / "evolution-common-rescore",
        root / "wave-2" / "natural-cue-calibration",
        root / "wave-2" / "natural-cue-discovery",
        root / "wave-2" / "natural-cue-confirmation",
        root / "wave-2" / "carrier-calibration",
        root / "wave-2" / "carrier-discovery",
        root / "wave-2" / "carrier-confirmation",
        root / "wave-3" / "evolution-discovery",
        root / "wave-3" / "evolution-confirmation",
        root / "wave-3" / "native-carrier-calibration",
        root / "wave-3" / "native-carrier-discovery",
        root / "wave-3" / "native-carrier-confirmation",
        root / "wave-3" / "gard-split",
    ]
    stage_paths.extend(sorted((root / "wave-2" / "mechanism-atlas").glob("discovery-*")))
    stage_paths.extend(sorted((root / "wave-2" / "mechanism-atlas").glob("confirmation-*")))
    active_etas: list[float] = []
    for path in stage_paths:
        try:
            label = str(path.relative_to(root))
        except ValueError:
            label = str(path)
        value: dict[str, Any] = {"state": "pending"}
        if (path / "SHA256SUMS").is_file():
            value = {"state": "sealed"}
            if (path / "manifest.json").is_file():
                manifest = read_json(path / "manifest.json")
                for key in ("record_count", "populations", "elapsed_seconds"):
                    if key in manifest:
                        value[key] = manifest[key]
        else:
            progress_files = [path / "progress.json", path / "executor" / "progress.json"]
            progress_path = next((candidate for candidate in progress_files if candidate.is_file()), None)
            if progress_path is not None:
                progress_value = read_json(progress_path)
                value = {"state": "running", **progress_value}
                eta = progress_value.get("eta_seconds")
                if eta is not None:
                    active_etas.append(float(eta))
            elif path.is_dir():
                value = {"state": "started"}
        stages[label] = value
    result: dict[str, Any] = {
        "format": "gre-plastic-heredity-v2-status-v1",
        "run": str(root),
        "stages": stages,
        "active_stage_eta_seconds": max(active_etas) if active_etas else None,
    }
    if (root / "progress.json").is_file():
        result["campaign_progress"] = read_json(root / "progress.json")
    if (root / "campaign-state.json").is_file():
        result["campaign_state"] = read_json(root / "campaign-state.json")
    if (root / "campaign-manifest.json").is_file():
        result["campaign_manifest"] = read_json(root / "campaign-manifest.json")
    return result


def replay_plastic_heredity_v2(root: Path, future_id: str) -> dict[str, Any]:
    root = root.resolve()
    state_stages = [
        root / "fixture",
        root / "wave-1" / "state-discovery",
        root / "wave-1" / "state-confirmation",
        root / "wave-2" / "natural-cue-calibration",
        root / "wave-2" / "natural-cue-discovery",
        root / "wave-2" / "natural-cue-confirmation",
    ]
    for stage in state_stages:
        if not (stage / "executor" / "futures.jsonl.gz").is_file():
            continue
        try:
            return replay_v2_state_future(stage, future_id)
        except KeyError:
            pass
    for stage in (
        root / "wave-2" / "carrier-calibration",
        root / "wave-2" / "carrier-discovery",
        root / "wave-2" / "carrier-confirmation",
        root / "wave-3" / "native-carrier-calibration",
        root / "wave-3" / "native-carrier-discovery",
        root / "wave-3" / "native-carrier-confirmation",
    ):
        if not (stage / "futures.jsonl.gz").is_file():
            continue
        try:
            return replay_carrier_future(stage, future_id)
        except KeyError:
            pass
    atlas = root / "wave-2" / "mechanism-atlas"
    for stage in sorted(atlas.glob("discovery-*")) + sorted(atlas.glob("confirmation-*")):
        if not (stage / "futures.jsonl.gz").is_file():
            continue
        try:
            return replay_memory_future(stage, future_id)
        except KeyError:
            pass
    gard = root / "wave-3" / "gard-split"
    for stage_name in ("exact-capacity", "natural-calibration", "natural-confirmation"):
        stage = gard / stage_name
        if not (stage / "futures.jsonl.gz").is_file():
            continue
        try:
            return replay_gard_memory_future(stage, future_id)
        except KeyError:
            pass
    raise KeyError(f"unknown Plastic Heredity v2 future: {future_id}")
