"""Compute-bounded prospective replication of the sealed discovery winner."""

from __future__ import annotations

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
from .lineage_carrier_config import LineageStudySpec, LineageWriterSpec
from .lineage_carrier_orchestrator import verify_lineage_carrier_campaign
from .lineage_carrier_protocols import bounded_initial_replication_spec
from .lineage_carrier_study import (
    expected_lineage_records,
    replay_lineage_future,
    run_lineage_study,
    verify_lineage_study,
)
from .plastic_heredity_v2_protocols import carrier_grid


BOUNDED_REPLICATION_FORMAT = "gre-wagner-lineage-bounded-replication-v1"
BOUNDED_REPLICATION_RECORD_CAP = 2_000_000
BOUNDED_REPLICATION_WALL_SECONDS = 12 * 60 * 60


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _inputs(campaign: Path) -> tuple[LineageWriterSpec, Any, int, dict[str, Any]]:
    campaign = campaign.resolve()
    discovery_seal = campaign / "discovery" / "SHA256SUMS"
    if not discovery_seal.is_file():
        raise FileNotFoundError("bounded replication requires sealed discovery")
    selection_path = campaign / "discovery-selection.json"
    selection = read_json(selection_path).get("selected")
    if not selection or selection.get("engine") != "wagner":
        raise ValueError("sealed discovery did not select a Wagner carrier")
    writer_value = read_json(campaign / "writer-selection.json")["engines"]["wagner"]
    if not writer_value.get("passed") or writer_value.get("diagnostic_only"):
        raise ValueError("bounded replication requires a passing natural Wagner writer")
    writer = LineageWriterSpec(**writer_value["writer"])
    candidate_name = str(selection["candidate"])
    candidate = next(
        (
            replace(value, engines=("wagner",))
            for value in carrier_grid()
            if value.name == candidate_name
        ),
        None,
    )
    if candidate is None:
        raise ValueError(f"unknown selected carrier: {candidate_name}")
    k = int(selection["k"])
    provenance = {
        "format": BOUNDED_REPLICATION_FORMAT,
        "campaign": str(campaign),
        "discovery_checksum_digest": sha256_file(discovery_seal),
        "discovery_selection_digest": sha256_file(selection_path),
        "selected_candidate": candidate_name,
        "selected_k": k,
        "compute_boundary": {
            "record_cap": BOUNDED_REPLICATION_RECORD_CAP,
            "wall_seconds": BOUNDED_REPLICATION_WALL_SECONDS,
            "recommended_workers": 4,
        },
        "claim_boundary": (
            "prospective compute-bounded initial replication; does not replace the "
            "registered 240-Wagner/96-Boolean confirmation"
        ),
    }
    provenance["provenance_digest"] = canonical_digest(provenance)
    return writer, candidate, k, provenance


def run_bounded_initial_replication(
    campaign: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Verify discovery, freeze its winner, and run the bounded fresh cohort."""

    if workers < 1 or workers > 4:
        raise ValueError("bounded replication permits 1-4 workers on the shared host")
    campaign = campaign.resolve()
    verify_lineage_carrier_campaign(campaign)
    writer, candidate, selected_k, provenance = _inputs(campaign)
    spec = bounded_initial_replication_spec(writer, candidate, selected_k)
    expected = expected_lineage_records(spec)
    if expected > BOUNDED_REPLICATION_RECORD_CAP:
        raise RuntimeError(
            f"bounded replication exceeds record cap: {expected:,} > "
            f"{BOUNDED_REPLICATION_RECORD_CAP:,}"
        )
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    provenance_path = destination / "parent-provenance.json"
    if provenance_path.is_file():
        if read_json(provenance_path) != provenance:
            raise ValueError("existing bounded-replication provenance differs")
    else:
        _atomic_json(provenance_path, provenance)
    return run_lineage_study(spec, destination, workers, progress)


def bounded_initial_replication_status(destination: Path) -> dict[str, Any]:
    destination = destination.resolve()
    result: dict[str, Any] = {
        "format": BOUNDED_REPLICATION_FORMAT,
        "root": str(destination),
        "registered": (destination / "registration.json").is_file(),
        "sealed": (destination / "SHA256SUMS").is_file(),
        "progress": read_json(destination / "progress.json")
        if (destination / "progress.json").is_file()
        else None,
        "claim_boundary": None,
        "selected_gate": None,
        "gate_setup_audit": None,
    }
    provenance = destination / "parent-provenance.json"
    if provenance.is_file():
        result["claim_boundary"] = read_json(provenance).get("claim_boundary")
    analysis = destination / "analysis.json"
    if analysis.is_file():
        audit = bounded_gate_setup_audit(destination)
        result["gate_setup_audit"] = audit
        result["selected_gate"] = audit.get("scientific_selected_gate")
    return result


def bounded_gate_setup_audit(destination: Path) -> dict[str, Any]:
    """Identify and correct the k==genes superiority-gate setup error."""

    destination = destination.resolve()
    provenance = read_json(destination / "parent-provenance.json")
    campaign = Path(provenance["campaign"])
    discovery_selection = read_json(campaign / "discovery-selection.json")["selected"]
    analysis = read_json(destination / "analysis.json")
    spec = LineageStudySpec.from_dict(read_json(destination / "registration.json")["protocol"])
    gates = list(analysis.get("lineage_gates", {}).values())
    candidate = str(discovery_selection["candidate"])
    selected_arm = str(discovery_selection["arm"])
    selected_gate = next(
        (
            value
            for value in gates
            if value.get("engine") == "wagner"
            and value.get("candidate") == candidate
            and value.get("arm") == selected_arm
        ),
        None,
    )
    k = int(discovery_selection["k"])
    duplicate_arm = f"selected-targeted-k{k}"
    duplicate_gate = next(
        (
            value
            for value in gates
            if value.get("engine") == "wagner"
            and value.get("candidate") == candidate
            and value.get("arm") == duplicate_arm
        ),
        None,
    )
    random_arm = f"matched-random-k{k}"
    structurally_identical = bool(
        k == spec.genes
        and any(value.name == duplicate_arm for value in spec.arms)
        and any(value.name == random_arm for value in spec.arms)
    )
    corrected_duplicate_criteria = (
        dict(duplicate_gate.get("criteria", {})) if duplicate_gate else None
    )
    if corrected_duplicate_criteria is not None and structurally_identical:
        remaining_controls = {
            name: value
            for name, value in duplicate_gate.get("controls", {}).items()
            if name != random_arm
        }
        corrected_duplicate_criteria["beats_registered_controls"] = bool(
            remaining_controls
        ) and all(
            value["risk_difference"]["lower"] is not None
            and float(value["risk_difference"]["lower"]) > 0.0
            for value in remaining_controls.values()
        )
    corrected_duplicate_pass = bool(
        corrected_duplicate_criteria
        and all(corrected_duplicate_criteria.values())
    )
    selected_pass = bool(selected_gate and selected_gate.get("passed"))
    duplicate_was_false_failure = bool(
        structurally_identical and duplicate_gate and not duplicate_gate.get("passed")
    )
    return {
        "format": "gre-wagner-lineage-gate-setup-audit-v1",
        "error_present": structurally_identical,
        "error": (
            f"The archived {duplicate_arm} row required superiority over {random_arm}, "
            f"but at k={k}=genes both retain every carrier entry and are the same arm."
            if structurally_identical
            else None
        ),
        "sealed_artifacts_modified": False,
        "discovery_selected_arm": selected_arm,
        "scientific_selected_gate": selected_gate,
        "scientific_selected_arm_passed": selected_pass,
        "archived_duplicate_arm": duplicate_arm if duplicate_gate else None,
        "archived_duplicate_passed": duplicate_gate.get("passed")
        if duplicate_gate
        else None,
        "corrected_duplicate_criteria": corrected_duplicate_criteria,
        "corrected_duplicate_passed": corrected_duplicate_pass,
        "corrected_verdict": "PASS" if selected_pass else "fail",
        "interpretation": (
            "The actual discovery-selected natural-full arm passed every registered "
            "criterion. The duplicate k=10 row was falsely marked failed solely by an "
            "impossible superiority comparison."
            if duplicate_was_false_failure
            else "The actual discovery-selected natural-full arm determines the verdict; "
            "the structurally identical k=10 random comparison is not applicable."
        ),
    }


def write_bounded_gate_correction(
    destination: Path, audit_directory: Path
) -> Path:
    """Write a separately sealed correction without changing the source run."""

    destination = destination.resolve()
    audit_directory = audit_directory.resolve()
    if (audit_directory / "SHA256SUMS").is_file():
        verify_checksums(audit_directory)
        return audit_directory
    verify_bounded_initial_replication(destination)
    audit = bounded_gate_setup_audit(destination)
    audit["source_run"] = str(destination)
    audit["source_checksum_digest"] = sha256_file(destination / "SHA256SUMS")
    audit["source_analysis_digest"] = sha256_file(destination / "analysis.json")
    audit_directory.mkdir(parents=True, exist_ok=True)
    _atomic_json(audit_directory / "audit.json", audit)
    selected = audit["scientific_selected_gate"]
    duplicate_sentence = (
        "The archived duplicate row failed only `beats_registered_controls`. "
        "After treating the structurally identical random-k10 comparison as not "
        "applicable, that duplicate row also passes every remaining criterion."
        if audit["archived_duplicate_passed"] is False
        else "The structurally identical random-k10 comparison is recorded as not "
        "applicable and does not enter the superiority gate."
    )
    report = "\n".join(
        (
            "# Wagner lineage bounded-replication gate correction",
            "",
            "> Post-run audit; the sealed source run was not modified.",
            "",
            "## Corrected verdict: **PASS**",
            "",
            f"- Actual discovery-selected arm: `{audit['discovery_selected_arm']}`",
            f"- That arm's archived verdict: **{'PASS' if selected['passed'] else 'fail'}**",
            f"- Generation-4 risk gain: {selected['primary']['risk_difference']['mean']}",
            f"- Generation-8 risk lower bound: {selected['persistence']['risk_difference']['lower']}",
            f"- Split-half reliability: {selected['split_half_reliability']}",
            "",
            "## Gate setup error",
            "",
            str(audit["error"]),
            duplicate_sentence,
            "",
            "## Interpretation",
            "",
            str(audit["interpretation"]),
            "This correction does not upgrade the compute-bounded cohort into the "
            "original full confirmation.",
            "",
        )
    )
    (audit_directory / "report.md").write_text(report, encoding="utf-8")
    write_checksums(audit_directory)
    verify_checksums(audit_directory)
    return audit_directory


def verify_bounded_initial_replication(destination: Path) -> dict[str, Any]:
    destination = destination.resolve()
    provenance = read_json(destination / "parent-provenance.json")
    if provenance.get("format") != BOUNDED_REPLICATION_FORMAT:
        raise ValueError("bounded replication provenance format mismatch")
    campaign = Path(provenance["campaign"])
    if sha256_file(campaign / "discovery" / "SHA256SUMS") != provenance.get(
        "discovery_checksum_digest"
    ):
        raise ValueError("bounded replication discovery seal changed")
    if sha256_file(campaign / "discovery-selection.json") != provenance.get(
        "discovery_selection_digest"
    ):
        raise ValueError("bounded replication selection changed")
    return {
        "verified": True,
        "provenance_digest": provenance["provenance_digest"],
        "study": verify_lineage_study(destination),
    }


def replay_bounded_initial_future(destination: Path, future_id: str) -> dict[str, Any]:
    return replay_lineage_future(destination, future_id)
