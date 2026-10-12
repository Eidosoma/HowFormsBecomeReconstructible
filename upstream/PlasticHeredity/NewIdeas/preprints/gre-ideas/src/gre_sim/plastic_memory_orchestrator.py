"""Resumable orchestration for the full plastic-memory evidence ladder."""

from __future__ import annotations

import concurrent.futures
import shutil
import time
from pathlib import Path
from typing import Any, Callable

from .artifacts import (
    canonical_digest,
    read_json,
    verify_checksums,
    write_checksums,
    write_json,
)
from .plastic_memory_analysis import select_calibrated_cues, select_mark_candidates
from .plastic_memory_config import CueDose, MarkSetting
from .plastic_memory_evolution import (
    confirmatory_evolution_spec,
    exploratory_evolution_spec,
    run_memory_evolution,
)
from .plastic_memory_protocols import (
    MARK_GRID,
    NO_MARK,
    calibration_spec,
    confirmation_spec,
    discovery_spec,
    quick_spec,
)
from .plastic_memory_study import run_memory_study, verify_memory_run
from .plastic_memory_validation import validate_memory_implementation


MINIMUM_FREE_DISK_BYTES = 10 * 1024**3


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _cue_values(selection: dict[str, Any]) -> dict[str, CueDose]:
    output = {}
    for model, value in selection["models"].items():
        if not value["ready"] or value["cue"] is None:
            continue
        output[model] = CueDose(**value["cue"])
    return output


def _selected_marks(selection: dict[str, Any]) -> dict[str, str | None]:
    common = selection.get("common_selected")
    if common is not None:
        return {model: common for model in selection["models"]}
    return {
        model: value.get("selected") for model, value in selection["models"].items()
    }


def _advance_from_discovery(analysis: dict[str, Any]) -> bool:
    state = any(gate["passed"] for gate in analysis["state_transfer_gates"].values())
    marks = any(
        gate["passed"]
        for model in analysis["mark_transfer_gates"].values()
        for gate in model.values()
    )
    return state or marks


def _confirmed_carriers(
    analysis: dict[str, Any], selected_marks: dict[str, str | None]
) -> tuple[tuple[str, str, MarkSetting], ...]:
    output: list[tuple[str, str, MarkSetting]] = []
    for model, gate in analysis["state_transfer_gates"].items():
        if gate["passed"]:
            output.append((model, "state", NO_MARK))
    for model, mark_name in selected_marks.items():
        if mark_name is None:
            continue
        gate = analysis["mark_transfer_gates"].get(model, {}).get(mark_name)
        if gate and gate["passed"]:
            output.append((
                model,
                "slow_mark",
                next(mark for mark in MARK_GRID if mark.name == mark_name),
            ))
    return tuple(output)


def _write_root_report(output_root: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Plastic-memory evidence ladder",
        "",
        "> State transfer, slow-mark recovery, persistence, evolution, and GARD are separate gates.",
        "",
        f"- Completed: {manifest['completed']}",
        f"- Stopped at: `{manifest.get('stopped_at') or 'none'}`",
        f"- Confirmation launched: {manifest.get('confirmation_launched', False)}",
        f"- Confirmed carriers: {manifest.get('confirmed_carriers', {})}",
        f"- GARD mirror launched: {manifest.get('gard_mirror_launched', False)}",
        "",
        "See each sealed stage for raw futures, replay IDs, causal gates, and checksums.",
        "",
    ]
    (output_root / "report.md").write_text("\n".join(lines), encoding="utf-8")


def run_full_plastic_memory_campaign(
    output_root: Path,
    workers: int = 8,
    gard_root: Path | None = None,
    include_evolution: bool = True,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or resume the precommitted staged causal campaign."""

    if workers < 1 or workers > 8:
        raise ValueError("plastic-memory campaign requires 1-8 workers")
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if (output_root / "SHA256SUMS").is_file():
        verify_checksums(output_root)
        return output_root
    if shutil.disk_usage(output_root).free < MINIMUM_FREE_DISK_BYTES:
        raise OSError("less than 10 GiB free; refusing plastic-memory campaign")
    validation = validate_memory_implementation()
    registration = {
        "format": "gre-full-plastic-memory-campaign-registration-v1",
        "fixture_protocol_digest": canonical_digest(quick_spec().to_dict()),
        "calibration_protocol_digest": canonical_digest(calibration_spec().to_dict()),
        "conditional_discovery_builder": "plastic-memory-v1",
        "conditional_confirmation_builder": "plastic-memory-v1",
        "workers": workers,
        "maximum_workers": 8,
        "include_evolution": include_evolution,
        "gard_root": str(gard_root.resolve()) if gard_root is not None else None,
        "validation": validation,
    }
    registration_path = output_root / "campaign-registration.json"
    if registration_path.is_file():
        if canonical_digest(read_json(registration_path)) != canonical_digest(
            registration
        ):
            raise ValueError("existing plastic-memory campaign registration differs")
    else:
        _atomic_json(registration_path, registration)
    started = time.monotonic()

    if progress is not None:
        progress("plastic-memory fixture stage")
    fixture = run_memory_study(
        quick_spec(), output_root / "fixture", min(workers, 2), progress
    )
    if progress is not None:
        progress("plastic-memory cue calibration")
    calibration = run_memory_study(
        calibration_spec(), output_root / "calibration", workers, progress
    )
    cue_selection = select_calibrated_cues(read_json(calibration / "analysis.json"))
    _atomic_json(output_root / "cue-selection.json", cue_selection)
    if not cue_selection["all_primary_ready"]:
        manifest = {
            "format": "gre-full-plastic-memory-campaign-manifest-v1",
            "completed": True,
            "stopped_at": "cue-calibration",
            "confirmation_launched": False,
            "gard_mirror_launched": False,
            "elapsed_seconds": time.monotonic() - started,
        }
        _atomic_json(output_root / "campaign-manifest.json", manifest)
        _write_root_report(output_root, manifest)
        write_checksums(output_root)
        return output_root
    cues = _cue_values(cue_selection)
    discovery_value = discovery_spec(cues)
    _atomic_json(output_root / "discovery-protocol.json", discovery_value.to_dict())

    memory_workers = workers if not include_evolution or workers == 1 else max(1, workers - 3)
    evolution_workers = 0 if not include_evolution else max(1, workers - memory_workers)
    if progress is not None:
        progress(
            f"plastic-memory discovery ({memory_workers} workers)"
            + (
                f" and exploratory evolution ({evolution_workers} workers) in parallel"
                if include_evolution
                else ""
            )
        )
    if include_evolution:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            memory_future = executor.submit(
                run_memory_study,
                discovery_value,
                output_root / "discovery",
                memory_workers,
                progress,
            )
            evolution_future = executor.submit(
                run_memory_evolution,
                exploratory_evolution_spec(cues),
                output_root / "evolution-exploratory",
                evolution_workers,
                progress,
            )
            discovery = memory_future.result()
            evolution_future.result()
    else:
        discovery = run_memory_study(
            discovery_value, output_root / "discovery", memory_workers, progress
        )
    discovery_analysis = read_json(discovery / "analysis.json")
    mark_selection = select_mark_candidates(discovery_analysis)
    _atomic_json(output_root / "mark-selection.json", mark_selection)
    selected_marks = _selected_marks(mark_selection)
    if not _advance_from_discovery(discovery_analysis):
        manifest = {
            "format": "gre-full-plastic-memory-campaign-manifest-v1",
            "completed": True,
            "stopped_at": "discovery-transfer-gate",
            "confirmation_launched": False,
            "gard_mirror_launched": False,
            "selected_marks": selected_marks,
            "elapsed_seconds": time.monotonic() - started,
        }
        _atomic_json(output_root / "campaign-manifest.json", manifest)
        _write_root_report(output_root, manifest)
        write_checksums(output_root)
        return output_root

    confirmation_value = confirmation_spec(cues, selected_marks)
    _atomic_json(output_root / "confirmation-protocol.json", confirmation_value.to_dict())
    if progress is not None:
        progress("automatic untouched 200-rulebook transfer confirmation")
    confirmation = run_memory_study(
        confirmation_value, output_root / "confirmation", workers, progress
    )
    confirmation_analysis = read_json(confirmation / "analysis.json")
    confirmed = _confirmed_carriers(confirmation_analysis, selected_marks)

    evolution_confirmation_path: str | None = None
    if include_evolution and confirmed:
        if progress is not None:
            progress("confirmatory evolution for confirmed memory carriers")
        evolution_confirmation = run_memory_evolution(
            confirmatory_evolution_spec(cues, confirmed),
            output_root / "evolution-confirmation",
            workers,
            progress,
        )
        evolution_confirmation_path = str(evolution_confirmation)

    gard_launched = False
    gard_path: str | None = None
    if gard_root is not None and confirmed:
        if progress is not None:
            progress("conditional GARD composition-transplant mirror")
        from .plastic_memory_gard import run_gard_memory_mirror

        gard = run_gard_memory_mirror(
            gard_root, output_root / "gard-mirror", workers, progress
        )
        gard_launched = True
        gard_path = str(gard)

    manifest = {
        "format": "gre-full-plastic-memory-campaign-manifest-v1",
        "completed": True,
        "stopped_at": None,
        "confirmation_launched": True,
        "confirmed_carriers": [
            {"model": model, "carrier": carrier, "mark": mark.name}
            for model, carrier, mark in confirmed
        ],
        "evolution_confirmation": evolution_confirmation_path,
        "gard_mirror_launched": gard_launched,
        "gard_mirror": gard_path,
        "selected_marks": selected_marks,
        "elapsed_seconds": time.monotonic() - started,
        "phase_verification": {
            "fixture": verify_memory_run(fixture),
            "calibration": verify_memory_run(calibration),
            "discovery": verify_memory_run(discovery),
            "confirmation": verify_memory_run(confirmation),
        },
    }
    _atomic_json(output_root / "campaign-manifest.json", manifest)
    _write_root_report(output_root, manifest)
    write_checksums(output_root)
    if progress is not None:
        progress("completed and sealed full plastic-memory evidence ladder")
    return output_root
