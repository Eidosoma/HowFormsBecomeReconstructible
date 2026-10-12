"""Resumable orchestration for the staged Wagner induction-rescue funnel."""

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
from .wagner_rescue_protocols import replication_spec, screen_spec, validation_spec
from .wagner_rescue_selection import (
    select_replication_candidate,
    select_screen_finalists,
)
from .wagner_rescue_study import (
    recompute_rescue_analysis,
    replay_rescue_future,
    run_rescue_study,
    verify_rescue_run,
)


MINIMUM_FREE_DISK_BYTES = 10 * 1024**3


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _parent_diagnostic(parent: Path) -> dict[str, Any]:
    analysis = read_json(parent / "calibration" / "analysis.json")
    calibration = {
        name: value
        for name, value in analysis["calibration"].items()
        if name.startswith("wagner-primary.")
    }
    full_clamp = {
        name: value
        for name, value in calibration.items()
        if ".cue-1x" in name
    }
    best = max(
        calibration.items(),
        key=lambda item: float(item[1]["mean"] or float("-inf")),
    )
    return {
        "format": "gre-wagner-rescue-parent-diagnostic-v1",
        "source": str((parent / "calibration").resolve()),
        "parent_calibration_digest": canonical_digest(analysis),
        "best_exact_acquisition_cell": {"name": best[0], **best[1]},
        "full_clamp_cells": full_clamp,
        "interpretation": (
            "Full initialization clamps remain far below the 0.80 induction gate; "
            "longer dwell does not repair the theta=0.10 Wagner regime."
        ),
    }


def _ensure_phase(
    directory: Path,
    spec: Any,
    workers: int,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    run_rescue_study(spec, directory, workers, progress)
    verification = verify_rescue_run(directory)
    expected_digest = canonical_digest(spec.to_dict())
    if verification["protocol_digest"] != expected_digest:
        raise ValueError(f"existing rescue phase uses a different protocol: {directory}")
    recomputation = recompute_rescue_analysis(directory)
    if not recomputation["matches"]:
        raise ValueError(f"independent rescue reanalysis failed for {directory}")
    return {
        "verification": verification,
        "independent_analysis_recomputation": True,
    }


def _candidate_record(
    parent_digest: str,
    selection: dict[str, Any],
    validation_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    selected = selection.get("selected")
    if selected is None:
        return {
            "format": "gre-wagner-rescue-candidate-v1",
            "ready": False,
            "selected": None,
            "reason": "no narrow-replication cell passed every exploratory gate",
            "parent_digest": parent_digest,
            "exploratory": True,
            "downstream_launch_authorized": False,
        }
    if validation_analysis is None:
        raise ValueError("selected rescue candidate requires validation analysis")
    validation_cells = [
        cell
        for cell in validation_analysis["cells"].values()
        if cell["role"] == "candidate"
    ]
    if len(validation_cells) != 1:
        raise ValueError("validation phase must contain exactly one candidate cell")
    validation = validation_cells[0]
    return {
        "format": "gre-wagner-rescue-candidate-v1",
        "ready": bool(validation["replication_passed"]),
        "selected": {
            "model": validation["model"],
            "intervention": validation["intervention"],
            "validation_condition": validation["condition"],
        },
        "validation_metrics": {
            "histories": validation["histories"],
            "correct_minus_wrong": validation["metrics"]["correct_minus_wrong"],
            "cue_gain_over_no_cue": validation["metrics"][
                "cue_gain_over_no_cue"
            ],
            "split_half_reliability": validation["split_half_reliability"],
            "injection_ceiling_fraction": validation[
                "injection_ceiling_fraction"
            ],
            "criteria": validation["replication_criteria"],
        },
        "reason": (
            "all fresh validation gates passed"
            if validation["replication_passed"]
            else "fresh validation did not pass every exploratory gate"
        ),
        "parent_digest": parent_digest,
        "exploratory": True,
        "downstream_launch_authorized": False,
    }


def _write_report(output: Path, manifest: dict[str, Any], candidate: dict[str, Any]) -> None:
    selected = candidate.get("selected")
    if selected is None:
        selected_text = "none"
    else:
        model = selected["model"]
        cue = selected["intervention"]
        selected_text = (
            f"{model['variant']} at theta={model['gamma_variance']:g}; "
            f"{cue['mode']} fraction={cue['fraction']:g}, dwell={cue['dwell']}"
        )
    lines = [
        "# Wagner induction-rescue campaign",
        "",
        "> Explicitly exploratory staged mechanism search; not a plastic-heredity confirmation.",
        "",
        f"- Completed: {manifest['completed']}",
        f"- Stopped at: `{manifest['stopped_at']}`",
        f"- Candidate ready: {candidate['ready']}",
        f"- Selected regimen: `{selected_text}`",
        "- Downstream launch authorized: False",
        "",
        "The sealed parent campaign was read only. Each completed phase contains raw "
        "futures, replay identifiers, rulebook-level analysis, and independent checksums.",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def run_full_wagner_rescue_campaign(
    parent_run: Path,
    output_root: Path,
    workers: int = 8,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or safely resume the complete exploratory rescue funnel."""

    if workers < 1 or workers > 8:
        raise ValueError("full Wagner rescue campaign requires 1-8 workers")
    parent = parent_run.resolve()
    verify_checksums(parent)
    parent_manifest = read_json(parent / "campaign-manifest.json")
    cue_selection = read_json(parent / "cue-selection.json")
    if not parent_manifest.get("completed") or parent_manifest.get("stopped_at") != "cue-calibration":
        raise ValueError("Wagner rescue requires a campaign stopped at cue calibration")
    if cue_selection.get("models", {}).get("wagner-primary", {}).get("ready") is not False:
        raise ValueError("parent campaign does not contain the Wagner induction failure")
    parent_digest = sha256_file(parent / "SHA256SUMS")
    output_root = output_root.resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output_root.parent).free < MINIMUM_FREE_DISK_BYTES:
        raise OSError("less than 10 GiB free; refusing Wagner rescue campaign")
    output_root.mkdir(parents=True, exist_ok=True)
    screen = screen_spec()
    registration = {
        "format": "gre-full-wagner-rescue-registration-v1",
        "parent_run": str(parent),
        "parent_checksum_digest": parent_digest,
        "parent_cue_selection_digest": canonical_digest(cue_selection),
        "screen_protocol_digest": canonical_digest(screen.to_dict()),
        "selection_protocol": "diverse-top-four-then-fresh-gated-winner-v1",
        "workers": workers,
        "maximum_workers": 8,
        "exploratory": True,
        "automatic_downstream_launch": False,
    }
    registration_path = output_root / "campaign-registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing rescue campaign root uses a different registration")
    else:
        _atomic_json(registration_path, registration)
    if (output_root / "SHA256SUMS").is_file():
        verify_wagner_rescue_campaign(output_root)
        if progress is not None:
            progress("Wagner rescue campaign already complete; verified without mutation")
        return output_root
    started = time.monotonic()
    audit: dict[str, Any] = {}
    diagnostic_path = output_root / "parent-calibration-diagnostic.json"
    diagnostic = _parent_diagnostic(parent)
    if diagnostic_path.is_file():
        if read_json(diagnostic_path) != diagnostic:
            raise ValueError("parent calibration diagnostic changed during resume")
    else:
        _atomic_json(diagnostic_path, diagnostic)

    if progress is not None:
        progress("Wagner rescue stage 1/3: broad mechanism screen")
    _atomic_json(output_root / "screen-protocol.json", screen.to_dict())
    screen_dir = output_root / "screen"
    audit["screen"] = _ensure_phase(screen_dir, screen, workers, progress)
    screen_analysis = read_json(screen_dir / "analysis.json")
    screen_selection = select_screen_finalists(screen_analysis)
    _atomic_json(output_root / "screen-selection.json", screen_selection)
    finalists = list(screen_selection["selected"])
    if not finalists:
        raise RuntimeError("screen selection produced no diagnostic finalists")

    narrow = replication_spec(finalists)
    _atomic_json(output_root / "replication-protocol.json", narrow.to_dict())
    if progress is not None:
        progress("Wagner rescue stage 2/3: fresh narrow replication")
    narrow_dir = output_root / "replication"
    audit["replication"] = _ensure_phase(narrow_dir, narrow, workers, progress)
    narrow_analysis = read_json(narrow_dir / "analysis.json")
    candidate_selection = select_replication_candidate(narrow_analysis)
    _atomic_json(output_root / "replication-selection.json", candidate_selection)

    validation_analysis: dict[str, Any] | None = None
    selected = candidate_selection.get("selected")
    stopped_at = "narrow-replication"
    if selected is not None:
        validation = validation_spec(selected)
        _atomic_json(output_root / "validation-protocol.json", validation.to_dict())
        if progress is not None:
            progress("Wagner rescue stage 3/3: untouched candidate validation")
        validation_dir = output_root / "validation"
        audit["validation"] = _ensure_phase(
            validation_dir, validation, workers, progress
        )
        validation_analysis = read_json(validation_dir / "analysis.json")
        stopped_at = "candidate-validation"
    candidate = _candidate_record(
        parent_digest, candidate_selection, validation_analysis
    )
    _atomic_json(output_root / "candidate.json", candidate)
    manifest = {
        "format": "gre-full-wagner-rescue-manifest-v1",
        "completed": True,
        "stopped_at": stopped_at,
        "elapsed_seconds": time.monotonic() - started,
        "workers": workers,
        "phases": audit,
        "screen_selection": screen_selection,
        "replication_selection": candidate_selection,
        "candidate_ready": candidate["ready"],
        "automatic_downstream_launch": False,
    }
    _atomic_json(output_root / "campaign-manifest.json", manifest)
    _write_report(output_root, manifest, candidate)
    write_checksums(output_root)
    verify_wagner_rescue_campaign(output_root)
    if progress is not None:
        progress("completed and sealed Wagner induction-rescue campaign")
    return output_root


def verify_wagner_rescue_campaign(output_root: Path) -> dict[str, Any]:
    files = verify_checksums(output_root)
    manifest = read_json(output_root / "campaign-manifest.json")
    if manifest.get("format") != "gre-full-wagner-rescue-manifest-v1" or not manifest.get(
        "completed"
    ):
        raise ValueError("Wagner rescue campaign manifest is incomplete")
    phases = {}
    for name in ("screen", "replication", "validation"):
        directory = output_root / name
        if directory.is_dir():
            phases[name] = verify_rescue_run(directory)
    if set(phases) != set(manifest["phases"]):
        raise ValueError("Wagner rescue phase set disagrees with campaign manifest")
    return {"verified": True, "files": len(files), "phases": phases}


def replay_wagner_rescue_campaign_future(
    output_root: Path, future_id: str
) -> dict[str, Any]:
    for stage in ("screen", "replication", "validation"):
        directory = output_root / stage
        if not (directory / "futures.jsonl.gz").is_file():
            continue
        try:
            result = replay_rescue_future(directory, future_id)
        except KeyError:
            continue
        return {"stage": stage, **result}
    raise KeyError(f"unknown Wagner rescue campaign future: {future_id}")
