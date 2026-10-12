"""Resumable orchestration for the complete Wagner heredity evidence ladder."""

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
from .plastic_memory_gard import run_gard_memory_mirror
from .wagner_heredity_analysis import (
    passing_state_writers,
    select_mark_candidate,
)
from .wagner_heredity_evolution import (
    confirmatory_evolution_spec,
    exploratory_evolution_spec,
    run_heredity_evolution,
)
from .wagner_heredity_protocols import (
    confirmation_spec,
    discovery_spec,
    mark_confirmation_spec,
    mark_discovery_spec,
    quick_spec,
    weakest_writer,
)
from .wagner_heredity_study import (
    replay_heredity_future,
    run_heredity_study,
    verify_heredity_run,
)
from .wagner_rescue_orchestrator import verify_wagner_rescue_campaign


MINIMUM_FREE_DISK_BYTES = 10 * 1024**3


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _campaign_progress(
    output_root: Path,
    active_stage: str,
    completed_stages: list[str],
    started: float,
) -> None:
    _atomic_json(
        output_root / "progress.json",
        {
            "format": "gre-full-wagner-heredity-progress-v1",
            "active_stage": active_stage,
            "completed_stages": completed_stages,
            "elapsed_seconds": time.monotonic() - started,
        },
    )


def _tier_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        gate["tier"]: {
            "writer": name,
            "passed": gate["passed"],
            "failed_criteria": [
                criterion
                for criterion, passed in gate["criteria"].items()
                if not passed
            ],
        }
        for name, gate in analysis["state_transfer_gates"].items()
        if gate["primary"]
    }


def _write_root_report(output_root: Path, manifest: dict[str, Any]) -> None:
    tiers = manifest.get("confirmed_tiers", {})
    lines = [
        "# Wagner plastic-heredity evidence ladder",
        "",
        "The verdict is tiered: hard state transfer, soft induction, noise robustness, "
        "slow-mark causality, evolvability, and GARD generality are not pooled.",
        "",
        f"- Completed: {manifest.get('completed', False)}",
        f"- Stopped at: `{manifest.get('stopped_at') or 'none'}`",
        f"- Confirmed writers: {manifest.get('confirmed_writers', [])}",
        f"- Confirmed slow mark: {manifest.get('confirmed_mark')}",
        f"- Evolution confirmation launched: {manifest.get('evolution_confirmation_launched', False)}",
        f"- GARD mirror launched: {manifest.get('gard_mirror_launched', False)}",
        "",
        "## Confirmed state tiers",
        "",
    ]
    if not tiers:
        lines.append("No state-transfer tier confirmed.")
    for tier, value in sorted(tiers.items()):
        lines.append(
            f"- `{tier}` / `{value['writer']}`: {'PASS' if value['passed'] else 'fail'}"
        )
    lines.extend(
        (
            "",
            "## Interpretation",
            "",
            "A hard-only pass is minimal engineered state heredity. It does not imply "
            "a hidden carrier. Each later tier is a separate stronger result, and a "
            "null at one tier remains part of the result.",
            "",
        )
    )
    (output_root / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _finish(
    output_root: Path,
    manifest: dict[str, Any],
    progress: Callable[[str], None] | None,
) -> Path:
    _atomic_json(output_root / "campaign-manifest.json", manifest)
    _write_root_report(output_root, manifest)
    write_checksums(output_root)
    verify_wagner_heredity_campaign(output_root)
    if progress is not None:
        progress("completed and sealed Wagner plastic-heredity evidence ladder")
    return output_root


def run_full_wagner_heredity_campaign(
    parent_run: Path,
    output_root: Path,
    workers: int = 8,
    gard_root: Path | None = None,
    include_evolution: bool = True,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or resume every causally permitted rung of the evidence ladder."""

    if workers < 1 or workers > 8:
        raise ValueError("full Wagner heredity campaign requires 1-8 workers")
    parent = parent_run.resolve()
    verify_wagner_rescue_campaign(parent)
    candidate = read_json(parent / "candidate.json")
    if not candidate.get("ready"):
        raise ValueError("Wagner heredity requires a sealed ready rescue candidate")
    selected = candidate.get("selected", {})
    if (
        selected.get("model", {}).get("variant") != "wagner_sequential"
        or float(selected.get("model", {}).get("gamma_variance", -1.0)) != 0.0
        or selected.get("intervention", {}).get("mode") != "persistent_hard"
        or float(selected.get("intervention", {}).get("fraction", 0.0)) != 1.0
    ):
        raise ValueError("sealed rescue candidate is not the registered hard theta-zero parent")
    parent_checksum_digest = sha256_file(parent / "SHA256SUMS")
    candidate_digest = canonical_digest(candidate)
    output_root = output_root.resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output_root.parent).free < MINIMUM_FREE_DISK_BYTES:
        raise OSError("less than 10 GiB free; refusing Wagner heredity campaign")
    output_root.mkdir(parents=True, exist_ok=True)
    discovery = discovery_spec(candidate_digest)
    registration = {
        "format": "gre-full-wagner-heredity-registration-v1",
        "parent_run": str(parent),
        "parent_checksum_digest": parent_checksum_digest,
        "parent_candidate_digest": candidate_digest,
        "discovery_protocol_digest": canonical_digest(discovery.to_dict()),
        "confirmation_builder": "fresh-240-rulebook-minimal-heredity-v1",
        "mark_builder": "fresh-96-then-240-causal-mark-v1",
        "evolution_builder": "weakest-confirmed-writer-three-treatment-v1",
        "gard_root": str(gard_root.resolve()) if gard_root is not None else None,
        "include_evolution": include_evolution,
        "workers": workers,
        "maximum_workers": 8,
        "automatic_downstream_launch": True,
    }
    registration_path = output_root / "campaign-registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing heredity campaign uses a different registration")
    else:
        _atomic_json(registration_path, registration)
    if (output_root / "SHA256SUMS").is_file():
        verify_wagner_heredity_campaign(output_root)
        if progress is not None:
            progress("Wagner heredity campaign already sealed; verified without mutation")
        return output_root

    started = time.monotonic()
    completed: list[str] = []
    phase_verification: dict[str, Any] = {}
    _campaign_progress(output_root, "fixture", completed, started)
    if progress is not None:
        progress("Wagner heredity stage 1: deterministic end-to-end fixture")
    fixture = run_heredity_study(
        quick_spec(candidate_digest), output_root / "fixture", min(2, workers), progress
    )
    phase_verification["fixture"] = verify_heredity_run(fixture)
    completed.append("fixture")

    _atomic_json(output_root / "discovery-protocol.json", discovery.to_dict())
    _campaign_progress(output_root, "discovery", completed, started)
    if progress is not None:
        progress("Wagner heredity stage 2: fresh transfer and noise-boundary discovery")
    discovery_dir = run_heredity_study(
        discovery, output_root / "discovery", workers, progress
    )
    phase_verification["discovery"] = verify_heredity_run(discovery_dir)
    completed.append("discovery")
    discovery_analysis = read_json(discovery_dir / "analysis.json")
    selected_writers = passing_state_writers(discovery_analysis)
    discovery_selection = {
        "format": "gre-wagner-heredity-state-selection-v1",
        "selected_writers": list(selected_writers),
        "tiers": _tier_summary(discovery_analysis),
        "selection_uses_primary_anchors_only": True,
    }
    _atomic_json(output_root / "discovery-selection.json", discovery_selection)
    if not selected_writers:
        return _finish(
            output_root,
            {
                "format": "gre-full-wagner-heredity-manifest-v1",
                "completed": True,
                "stopped_at": "discovery-state-transfer-gate",
                "confirmed_writers": [],
                "confirmed_tiers": {},
                "confirmed_mark": None,
                "evolution_confirmation_launched": False,
                "gard_mirror_launched": False,
                "elapsed_seconds": time.monotonic() - started,
                "phase_verification": phase_verification,
            },
            progress,
        )

    confirmation = confirmation_spec(candidate_digest, selected_writers)
    _atomic_json(output_root / "confirmation-protocol.json", confirmation.to_dict())
    _campaign_progress(output_root, "confirmation", completed, started)
    if progress is not None:
        progress("Wagner heredity stage 3: untouched 240-rulebook state confirmation")
    confirmation_dir = run_heredity_study(
        confirmation, output_root / "confirmation", workers, progress
    )
    phase_verification["confirmation"] = verify_heredity_run(confirmation_dir)
    completed.append("confirmation")
    confirmation_analysis = read_json(confirmation_dir / "analysis.json")
    confirmed_writers = passing_state_writers(confirmation_analysis)
    confirmed_tiers = _tier_summary(confirmation_analysis)
    _atomic_json(
        output_root / "confirmation-selection.json",
        {
            "format": "gre-wagner-heredity-confirmed-state-v1",
            "confirmed_writers": list(confirmed_writers),
            "tiers": confirmed_tiers,
        },
    )
    if not confirmed_writers:
        return _finish(
            output_root,
            {
                "format": "gre-full-wagner-heredity-manifest-v1",
                "completed": True,
                "stopped_at": "untouched-state-confirmation",
                "confirmed_writers": [],
                "confirmed_tiers": confirmed_tiers,
                "confirmed_mark": None,
                "evolution_confirmation_launched": False,
                "gard_mirror_launched": False,
                "elapsed_seconds": time.monotonic() - started,
                "phase_verification": phase_verification,
            },
            progress,
        )

    weakest = weakest_writer(confirmed_writers)
    mark_discovery = mark_discovery_spec(candidate_digest, weakest)
    _atomic_json(output_root / "mark-discovery-protocol.json", mark_discovery.to_dict())
    _campaign_progress(output_root, "mark-discovery", completed, started)
    if progress is not None:
        progress(f"Wagner heredity stage 4a: slow-mark screen under {weakest}")
    mark_discovery_dir = run_heredity_study(
        mark_discovery, output_root / "mark-discovery", workers, progress
    )
    phase_verification["mark-discovery"] = verify_heredity_run(mark_discovery_dir)
    completed.append("mark-discovery")
    mark_name = select_mark_candidate(
        read_json(mark_discovery_dir / "analysis.json"), weakest
    )
    _atomic_json(
        output_root / "mark-selection.json",
        {
            "format": "gre-wagner-heredity-mark-selection-v1",
            "writer": weakest,
            "selected_mark": mark_name,
        },
    )
    confirmed_mark: str | None = None
    if mark_name is not None:
        mark_confirmation = mark_confirmation_spec(
            candidate_digest, weakest, mark_name
        )
        _atomic_json(
            output_root / "mark-confirmation-protocol.json",
            mark_confirmation.to_dict(),
        )
        _campaign_progress(output_root, "mark-confirmation", completed, started)
        if progress is not None:
            progress("Wagner heredity stage 4b: untouched slow-mark confirmation")
        mark_confirmation_dir = run_heredity_study(
            mark_confirmation,
            output_root / "mark-confirmation",
            workers,
            progress,
        )
        phase_verification["mark-confirmation"] = verify_heredity_run(
            mark_confirmation_dir
        )
        completed.append("mark-confirmation")
        mark_gate = read_json(mark_confirmation_dir / "analysis.json")[
            "mark_transfer_gates"
        ][weakest][mark_name]
        if mark_gate["passed"]:
            confirmed_mark = mark_name

    writer = confirmation.writer(weakest)
    active_mark = (
        mark_confirmation_spec(candidate_digest, weakest, confirmed_mark).mark(
            confirmed_mark
        )
        if confirmed_mark is not None
        else None
    )
    evolution_confirmation_launched = False
    evolution_confirmed_carriers: list[str] = []
    if include_evolution:
        evolution = exploratory_evolution_spec(
            candidate_digest, writer, active_mark
        )
        _atomic_json(
            output_root / "evolution-exploratory-protocol.json", evolution.to_dict()
        )
        _campaign_progress(output_root, "evolution-exploratory", completed, started)
        if progress is not None:
            progress("Wagner heredity stage 5a: checkpointed evolutionary response")
        evolution_dir = run_heredity_evolution(
            evolution, output_root / "evolution-exploratory", workers, progress
        )
        completed.append("evolution-exploratory")
        evolution_analysis = read_json(evolution_dir / "analysis.json")
        passing_carriers = tuple(
            key.split(".", 1)[1]
            for key, gate in evolution_analysis["response_gates"].items()
            if gate["passed"]
        )
        if passing_carriers:
            evolution_confirmation = confirmatory_evolution_spec(
                candidate_digest,
                writer,
                active_mark,
                passing_carriers,
            )
            _atomic_json(
                output_root / "evolution-confirmation-protocol.json",
                evolution_confirmation.to_dict(),
            )
            _campaign_progress(
                output_root, "evolution-confirmation", completed, started
            )
            if progress is not None:
                progress("Wagner heredity stage 5b: untouched evolutionary confirmation")
            evolution_confirmation_dir = run_heredity_evolution(
                evolution_confirmation,
                output_root / "evolution-confirmation",
                workers,
                progress,
            )
            completed.append("evolution-confirmation")
            evolution_confirmation_launched = True
            evolution_confirmed_carriers = [
                key.split(".", 1)[1]
                for key, gate in read_json(
                    evolution_confirmation_dir / "analysis.json"
                )["response_gates"].items()
                if gate["passed"]
            ]

    gard_launched = False
    gard_general_transfer: bool | None = None
    if gard_root is not None:
        _campaign_progress(output_root, "gard-mirror", completed, started)
        if progress is not None:
            progress("Wagner heredity stage 6: independent GARD composition mirror")
        gard_dir = run_gard_memory_mirror(
            gard_root, output_root / "gard-mirror", workers, progress
        )
        completed.append("gard-mirror")
        gard_launched = True
        gard_manifest = read_json(gard_dir / "manifest.json")
        gard_general_transfer = gard_manifest.get("general_gard_transfer")

    return _finish(
        output_root,
        {
            "format": "gre-full-wagner-heredity-manifest-v1",
            "completed": True,
            "stopped_at": None,
            "confirmed_writers": list(confirmed_writers),
            "confirmed_tiers": confirmed_tiers,
            "weakest_confirmed_writer": weakest,
            "confirmed_mark": confirmed_mark,
            "evolution_confirmation_launched": evolution_confirmation_launched,
            "evolution_confirmed_carriers": evolution_confirmed_carriers,
            "gard_mirror_launched": gard_launched,
            "gard_general_transfer": gard_general_transfer,
            "elapsed_seconds": time.monotonic() - started,
            "phase_verification": phase_verification,
        },
        progress,
    )


def verify_wagner_heredity_campaign(output_root: Path) -> dict[str, Any]:
    files = verify_checksums(output_root)
    manifest = read_json(output_root / "campaign-manifest.json")
    if manifest.get("format") != "gre-full-wagner-heredity-manifest-v1" or not manifest.get(
        "completed"
    ):
        raise ValueError("Wagner heredity campaign manifest is incomplete")
    phases = {}
    for name in (
        "fixture",
        "discovery",
        "confirmation",
        "mark-discovery",
        "mark-confirmation",
    ):
        directory = output_root / name
        if directory.is_dir():
            phases[name] = verify_heredity_run(directory)
    for name in ("evolution-exploratory", "evolution-confirmation", "gard-mirror"):
        directory = output_root / name
        if directory.is_dir():
            verify_checksums(directory)
            phases[name] = {"verified": True}
    return {"verified": True, "files": len(files), "phases": phases}


def replay_wagner_heredity_campaign_future(
    output_root: Path, future_id: str
) -> dict[str, Any]:
    for stage in (
        "fixture",
        "discovery",
        "confirmation",
        "mark-discovery",
        "mark-confirmation",
    ):
        directory = output_root / stage
        if not (directory / "futures.jsonl.gz").is_file():
            continue
        try:
            result = replay_heredity_future(directory, future_id)
        except KeyError:
            continue
        return {"stage": stage, **result}
    raise KeyError(f"unknown Wagner heredity campaign future: {future_id}")
