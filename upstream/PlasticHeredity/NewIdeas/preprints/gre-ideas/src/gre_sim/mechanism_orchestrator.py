"""Resumable staged orchestration for the ambitious mechanism campaign."""

from __future__ import annotations

import shutil
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from .artifacts import (
    canonical_digest,
    read_json,
    verify_checksums,
    write_checksums,
    write_json,
)
from .mechanism_config import MechanismCondition, SourceSetSpec
from .mechanism_diagnostics import write_stage_a_mechanism_diagnostic
from .mechanism_protocols import phase_1_spec, phase_2_spec, phase_3_spec
from .mechanism_selection import (
    audit_compiled_bridge,
    phase_2_decision,
    write_stage_b_candidate,
)
from .mechanism_study import (
    recompute_mechanism_analysis,
    run_mechanism_study,
    verify_mechanism_run,
)
from .study import verify_run


MINIMUM_FREE_DISK_BYTES = 10 * 1024**3


def _mean_matching(mapping: dict[str, Any], *parts: str) -> float | None:
    values = [
        float(value["mean"])
        for name, value in mapping.items()
        if all(part in name for part in parts)
    ]
    return float(sum(values) / len(values)) if values else None


def select_phase_2_mechanism(phase_2: Path) -> dict[str, Any]:
    """Rank one-factor Wagner variants by a frozen Boolean discrepancy score."""

    analysis = read_json(phase_2 / "analysis.json")
    rates = analysis["rates"]
    contrasts = analysis["contrasts"]
    references = {
        "capture.self": _mean_matching(
            rates,
            "boolean-n6-sync.boolean_sync.N-6.acute_mismatch.lambda-1.theta-0.self.active_capture",
        ),
        "capture.donor": _mean_matching(
            rates,
            "boolean-n6-sync.boolean_sync.N-6.acute_mismatch.lambda-1.theta-0.donor_shuffled.active_capture",
        ),
        "strict.natural": _mean_matching(
            contrasts,
            "rate.interaction.acute-minus-natural.boolean-n6-sync.boolean_sync.N-6.lambda-1.theta-0.strict_library",
        ),
        "strict.anchor": _mean_matching(
            contrasts,
            "rate.interaction.acute-minus-target_aligned_own_anchor.boolean-n6-sync.boolean_sync.N-6.lambda-1.theta-0.strict_library",
        ),
        "destination.natural": _mean_matching(
            contrasts,
            "committor.interaction.acute-minus-natural.exact_point_state.boolean-n6-sync.boolean_sync.N-6.lambda-1.theta-0",
        ),
        "destination.anchor": _mean_matching(
            contrasts,
            "committor.interaction.acute-minus-target_aligned_own_anchor.exact_point_state.boolean-n6-sync.boolean_sync.N-6.lambda-1.theta-0",
        ),
    }
    tolerances = {
        "capture.self": 0.05,
        "capture.donor": 0.05,
        "strict.natural": 0.02,
        "strict.anchor": 0.02,
        "destination.natural": 0.01,
        "destination.anchor": 0.01,
    }
    candidates = []
    for genes in (6, 10):
        for update in ("sequential", "synchronous"):
            condition = f"wagner-n{genes}-{update}"
            variant = f"wagner_{update}"
            for variance in (0.0, 0.1):
                token = f"theta-{variance:g}"
                values = {
                    "capture.self": _mean_matching(
                        rates,
                        f"{condition}.{variant}.N-{genes}.acute_mismatch.lambda-1.{token}.self.active_capture",
                    ),
                    "capture.donor": _mean_matching(
                        rates,
                        f"{condition}.{variant}.N-{genes}.acute_mismatch.lambda-1.{token}.donor_shuffled.active_capture",
                    ),
                    "strict.natural": _mean_matching(
                        contrasts,
                        f"rate.interaction.acute-minus-natural.{condition}.{variant}.N-{genes}.lambda-1.{token}.strict_library",
                    ),
                    "strict.anchor": _mean_matching(
                        contrasts,
                        f"rate.interaction.acute-minus-target_aligned_own_anchor.{condition}.{variant}.N-{genes}.lambda-1.{token}.strict_library",
                    ),
                    "destination.natural": _mean_matching(
                        contrasts,
                        f"committor.interaction.acute-minus-natural.exact_point_state.{condition}.{variant}.N-{genes}.lambda-1.{token}",
                    ),
                    "destination.anchor": _mean_matching(
                        contrasts,
                        f"committor.interaction.acute-minus-target_aligned_own_anchor.exact_point_state.{condition}.{variant}.N-{genes}.lambda-1.{token}",
                    ),
                }
                required = tuple(tolerances)
                if not all(
                    values[name] is not None and references[name] is not None
                    for name in required
                ):
                    continue
                score = sum(
                    ((float(values[name]) - float(references[name])) / tolerances[name])
                    ** 2
                    for name in required
                ) / len(required)
                candidates.append(
                    {
                        "condition": condition,
                        "variant": variant,
                        "genes": genes,
                        "gamma_variance": variance,
                        "score": float(score),
                        "components": values,
                    }
                )
    if not candidates:
        return {
            "selected": None,
            "reason": "no complete Phase 2 candidate metrics",
            "references": references,
        }
    selected = min(
        candidates,
        key=lambda item: (
            item["score"],
            item["gamma_variance"],
            item["variant"] != "wagner_sequential",
            item["genes"],
        ),
    )
    return {
        "selected": selected,
        "references": references,
        "tolerances": tolerances,
        "candidates": sorted(candidates, key=lambda item: item["score"]),
        "outcome_signs_used": True,
        "role": "exploratory fresh-mechanism replication only",
    }


def _phase_3_with_selected_mechanism(selection: dict[str, Any]):
    spec = phase_3_spec()
    selected = selection.get("selected")
    if selected is None:
        return spec
    genes = int(selected["genes"])
    source_name = f"fresh_selected_wagner_n{genes}"
    source = SourceSetSpec(
        source_name,
        "wagner",
        genes,
        32,
        "sampled",
        require_both_update_modes=selected["variant"] == "wagner_synchronous",
    )
    condition = MechanismCondition(
        "fresh-selected-wagner-mechanism",
        source_name,
        str(selected["variant"]),
        ("natural", "acute_mismatch", "target_aligned_own_anchor"),
        (1.0,),
        ("self", "donor_shuffled"),
        (float(selected["gamma_variance"]),),
        32,
    )
    return replace(
        spec,
        source_sets=(*spec.source_sets, source),
        conditions=(*spec.conditions, condition),
    )


def _ensure_phase(
    directory: Path,
    spec: Any,
    parent_run: Path | None,
    workers: int,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    if directory.exists():
        verification = verify_mechanism_run(directory)
    else:
        run_mechanism_study(spec, directory, parent_run, workers, progress)
        verification = verify_mechanism_run(directory)
    expected_digest = canonical_digest(spec.to_dict())
    if verification["protocol_digest"] != expected_digest:
        raise ValueError(
            f"existing phase uses a different protocol and cannot be resumed: "
            f"{directory}"
        )
    recomputation = recompute_mechanism_analysis(directory)
    if not recomputation["matches"]:
        raise ValueError(f"independent mechanism reanalysis failed for {directory}")
    return {
        "verification": verification,
        "independent_analysis_recomputation": True,
    }


def run_full_mechanism_campaign(
    parent_run: Path,
    output_root: Path,
    workers: int = 8,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or safely resume all registered exploratory phases."""

    if workers < 1 or workers > 8:
        raise ValueError("full mechanism campaign requires 1-8 workers")
    parent_verification = verify_run(parent_run)
    if parent_verification["protocol_digest"] != phase_1_spec().parent_protocol_digest:
        raise ValueError("full mechanism campaign requires the sealed Stage A v2 run")
    disk = shutil.disk_usage(output_root.parent.resolve())
    if disk.free < MINIMUM_FREE_DISK_BYTES:
        raise OSError("less than 10 GiB free; refusing full mechanism launch")
    output_root.mkdir(parents=True, exist_ok=True)
    registration_path = output_root / "campaign-registration.json"
    registration = {
        "format": "gre-full-mechanism-campaign-registration-v1",
        "parent_run": str(parent_run.resolve()),
        "parent_protocol_digest": parent_verification["protocol_digest"],
        "phase_1_protocol_digest": canonical_digest(phase_1_spec().to_dict()),
        "phase_2_protocol_digest": canonical_digest(phase_2_spec().to_dict()),
        "phase_3_base_protocol_digest": canonical_digest(phase_3_spec().to_dict()),
        "workers": workers,
        "maximum_workers": 8,
        "exploratory": True,
    }
    if registration_path.exists():
        if read_json(registration_path) != registration:
            raise ValueError("existing campaign root uses a different registration")
    else:
        write_json(registration_path, registration)
    completed_manifest = output_root / "campaign-manifest.json"
    if completed_manifest.is_file() and (output_root / "SHA256SUMS").is_file():
        manifest = read_json(completed_manifest)
        if manifest.get("completed") is True:
            verify_checksums(output_root)
            if progress is not None:
                progress("campaign was already complete; verified without mutation")
            return output_root.resolve()
    started = time.monotonic()
    audit: dict[str, Any] = {}

    diagnostic = output_root / "stage-a-diagnostic"
    if diagnostic.exists():
        verify_checksums(diagnostic)
    else:
        if progress is not None:
            progress("sealing formal Stage A mechanism diagnostic")
        write_stage_a_mechanism_diagnostic(parent_run, diagnostic)

    phase_1 = output_root / "phase-1"
    if progress is not None:
        progress("Phase 1/3: Stage A paired mechanism decomposition")
    audit["phase_1"] = _ensure_phase(
        phase_1, phase_1_spec(), parent_run, workers, progress
    )
    decision = phase_2_decision(phase_1)
    write_json(output_root / "phase-2-decision.json", decision)

    phase_2 = output_root / "phase-2"
    mechanism_selection: dict[str, Any] = {"selected": None, "phase_2_skipped": True}
    if decision["phase_2_required"]:
        if progress is not None:
            progress("Phase 2/3: matched-N, matched-update causal factorial")
        audit["phase_2"] = _ensure_phase(
            phase_2, phase_2_spec(), None, workers, progress
        )
        phase_2_bridge = audit_compiled_bridge(phase_2)
        if not phase_2_bridge["pathwise_equal"]:
            raise ValueError("a matched-architecture compiled bridge failed")
        write_json(output_root / "phase-2-compiled-bridge.json", phase_2_bridge)
        audit["phase_2"]["compiled_bridge"] = phase_2_bridge
        mechanism_selection = select_phase_2_mechanism(phase_2)
        write_json(output_root / "phase-2-mechanism-selection.json", mechanism_selection)

    phase_3_spec_value = _phase_3_with_selected_mechanism(mechanism_selection)
    write_json(output_root / "phase-3-protocol.json", phase_3_spec_value.to_dict())
    phase_3 = output_root / "phase-3"
    if progress is not None:
        progress("Phase 3/3: fresh-cohort mechanism replication")
    audit["phase_3"] = _ensure_phase(
        phase_3, phase_3_spec_value, None, workers, progress
    )
    candidate = output_root / "stage-b-candidate"
    if candidate.exists():
        verify_checksums(candidate)
    else:
        write_stage_b_candidate(phase_3, candidate)

    manifest = {
        "format": "gre-full-mechanism-campaign-manifest-v1",
        "completed": True,
        "elapsed_seconds": time.monotonic() - started,
        "workers": workers,
        "phases": audit,
        "phase_2_decision": decision,
        "mechanism_selection": mechanism_selection,
        "stage_b_candidate": read_json(candidate / "stage-b-candidate.json"),
    }
    write_json(output_root / "campaign-manifest.json", manifest)
    selected_value = mechanism_selection.get("selected")
    selected_label = (
        "none"
        if selected_value is None
        else (
            f"{selected_value['variant']} at N={selected_value['genes']}, "
            f"theta={selected_value['gamma_variance']:g}"
        )
    )
    report_lines = [
        "# Full Boolean–Wagner mechanism campaign",
        "",
        "> Exploratory staged campaign; no result in this directory is confirmatory.",
        "",
        f"- Phase 2 required: {decision['phase_2_required']}",
        f"- Fresh mechanism variant: `{selected_label}`",
        f"- Stage B candidate ready: {manifest['stage_b_candidate']['ready']}",
        f"- Selected endpoint: `{manifest['stage_b_candidate']['selected_endpoint']}`",
        "",
        "See each independently sealed phase for raw futures, analysis, figures, replay identifiers, and checksums.",
        "",
    ]
    (output_root / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    write_checksums(output_root)
    if progress is not None:
        progress("completed and sealed full mechanism campaign")
    return output_root.resolve()
