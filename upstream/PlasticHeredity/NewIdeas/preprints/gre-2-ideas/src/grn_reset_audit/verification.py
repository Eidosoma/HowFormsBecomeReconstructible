"""Artifact and invariant verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import read_jsonl, verify_checksums
from .upstream import PINNED_COMMIT


RECORD_FILES = [
    "source-replay.jsonl",
    "independent-correction.jsonl",
    "washout.jsonl",
    "sentinel-exhaustive.jsonl",
    "classifications.jsonl",
]

ATLAS_RECORD_FILES = [
    "calibration.jsonl",
    "histories.jsonl",
    "probes.jsonl",
    "reinstatement.jsonl",
    "relearning.jsonl",
    "observer-scores.jsonl",
    "mechanism-labels.jsonl",
]

RENEWAL_RECORD_FILES = [
    "native-renewal.jsonl",
    "carrier-screen.jsonl",
    "native-recurrence.jsonl",
    "mark-grid.jsonl",
    "mark-validation.jsonl",
]

HISTORY_RENEWAL_RECORD_FILES = [
    "fingerprint-reference.jsonl",
    "carrier-audit.jsonl",
    "natural-lineage.jsonl",
    "mark-grid.jsonl",
    "mark-validation.jsonl",
]

CONTINGENCY_RECORD_FILES = [
    "timing-discovery.jsonl",
    "contingency-validation.jsonl",
    "exposure-validation.jsonl",
    "cue-calibration.jsonl",
    "two-cue-reversal.jsonl",
    "native-transfer.jsonl",
    "carrier-discovery.jsonl",
    "carrier-validation.jsonl",
    "active-renewal.jsonl",
]


def verify_run(output: Path, require_sealed: bool = True) -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    state = json.loads((output / "state.json").read_text(encoding="utf-8"))
    kind = registration.get("protocol", {}).get("experiment_kind")
    renewal = kind == "latent-memory-renewal"
    history_renewal = kind == "history-carrier-renewal"
    ca_bridge = kind == "ca-bridge-carrier-ladder"
    contingency = kind == "contingency-memory-campaign"
    constrained_basin = kind == "constrained-basin-recovery"
    resource_limited = (
        renewal or history_renewal or ca_bridge or contingency or constrained_basin
    )
    ledger_name = "resource-ledger.json" if resource_limited else "cpu-ledger.json"
    ledger = json.loads((output / ledger_name).read_text(encoding="utf-8"))
    if registration["upstream"]["commit"] != PINNED_COMMIT:
        raise ValueError("upstream commit mismatch")
    if resource_limited:
        if float(ledger["aggregate_cpu_seconds"]) >= float(
            registration["protocol"]["hard_aggregate_cpu_seconds"]
        ):
            raise ValueError("renewal CPU ledger reached its hard boundary")
        if float(ledger["active_wall_seconds"]) >= float(
            registration["protocol"]["hard_wall_seconds"]
        ):
            raise ValueError("renewal wall ledger reached its hard boundary")
    elif float(ledger["cpu_seconds"]) >= float(
        registration["protocol"]["hard_cpu_seconds"]
    ):
        raise ValueError("CPU ledger reached or exceeded its hard boundary")
    atlas = kind == "observer-atlas"
    counts: dict[str, int] = {}
    record_files = (
        list(registration.get("record_files", ()))
        if ca_bridge or contingency or constrained_basin
        else HISTORY_RENEWAL_RECORD_FILES
        if history_renewal
        else RENEWAL_RECORD_FILES
        if renewal
        else ATLAS_RECORD_FILES
        if atlas
        else RECORD_FILES
    )
    for name in record_files:
        path = output / name
        if renewal and not path.is_file():
            continue
        if (history_renewal or ca_bridge or contingency or constrained_basin) and not path.is_file():
            raise FileNotFoundError(f"missing required record artifact: {name}")
        records = list(read_jsonl(path))
        task_ids = [record["task_id"] for record in records]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError(f"duplicate task IDs in {name}")
        counts[name] = len(records)
    if constrained_basin:
        expected_files = [
            "no-op.jsonl",
            "axial-return.jsonl",
            "transverse-return.jsonl",
            "coordinate-return.jsonl",
        ]
        if list(registration.get("record_files", ())) != expected_files:
            raise ValueError("constrained-basin record manifest differs from the protocol")
        parent_gate = json.loads((output / "parent-gate.json").read_text(encoding="utf-8"))
        incidents = json.loads(
            (output / "runtime-incidents.json").read_text(encoding="utf-8")
        )
        analysis = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
        geometry = json.loads(
            (output / "feasible-geometry.json").read_text(encoding="utf-8")
        )
        expected_counts = {
            str(name): int(value)
            for name, value in registration["protocol"]["registered_record_counts"].items()
        }
        if counts != expected_counts:
            raise ValueError("constrained-basin registered record counts differ")
        if state["status"] == "completed" and not (
            parent_gate["pass"] and analysis["minimum_completion_gate"]
        ):
            raise ValueError("completed constrained-basin run has a failed required gate")
        if analysis["run_status"] != state["status"]:
            raise ValueError("constrained-basin analysis/state status mismatch")
        if int(registration["workers"]) > 4:
            raise ValueError("constrained-basin worker cap exceeded")
        if not isinstance(incidents.get("incidents"), list):
            raise ValueError("invalid constrained-basin runtime incident ledger")
        if not isinstance(decision.get("pass"), bool):
            raise ValueError("constrained-basin decision lacks a Boolean gate")
        if geometry.get("frozen_before_dynamic_assays") is not True:
            raise ValueError("constrained-basin geometry was not frozen before assays")
        metric_count = sum(1 for _ in read_jsonl(output / "recovery-metrics.jsonl"))
        if metric_count != int(registration["protocol"]["registered_condition_count"]) - counts[
            "no-op.jsonl"
        ]:
            raise ValueError("constrained-basin recovery metric count differs")
    elif contingency:
        if list(registration.get("record_files", ())) != CONTINGENCY_RECORD_FILES:
            raise ValueError("contingency record manifest differs from the frozen protocol")
        parent_gate = json.loads((output / "parent-gate.json").read_text(encoding="utf-8"))
        incidents = json.loads(
            (output / "runtime-incidents.json").read_text(encoding="utf-8")
        )
        analysis = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
        if state["status"] == "completed" and not (
            parent_gate["pass"] and analysis["minimum_completion_gate"]
        ):
            raise ValueError("completed contingency campaign has a failed required gate")
        if analysis["run_status"] != state["status"]:
            raise ValueError("contingency analysis/state status mismatch")
        if int(registration["workers"]) > 4:
            raise ValueError("contingency worker cap exceeded")
        if not isinstance(incidents.get("incidents"), list):
            raise ValueError("invalid contingency runtime incident ledger")
        if not isinstance(decision.get("pass"), bool):
            raise ValueError("contingency decision lacks a Boolean gate")
        for name in record_files:
            for row in read_jsonl(output / name):
                if row.get("rulebook_inherited") is not None and row.get(
                    "rulebook_inherited"
                ) is not False:
                    raise ValueError("contingency recipient inherited the c rulebook")
                if (
                    row.get("recipient_c_hash") is not None
                    and row.get("child_c_hash") != row.get("recipient_c_hash")
                ):
                    raise ValueError("contingency recipient c rulebook changed")
                if row.get("founder_reused"):
                    generation = int(row["generation"])
                    if not (
                        generation == 1
                        or (
                            row.get("condition") == "rescue_g3"
                            and generation == 3
                            and row.get("donor_source") == "explicit-founder-rescue"
                        )
                    ):
                        raise ValueError("unregistered contingency founder reuse")
                if (
                    row.get("condition") == "passive"
                    and int(row.get("generation", 1)) > 1
                    and not str(row.get("donor_source", "")).startswith(
                        "damaged-copy-g"
                    )
                ):
                    raise ValueError("passive contingency lineage reused its founder")
        codebooks = json.loads((output / "codebooks.json").read_text(encoding="utf-8"))
        discovery = set(codebooks["discovery_seed_indices"])
        validation = set(codebooks["validation_seed_indices"])
        if discovery & validation or codebooks.get("leakage_allowed") is not False:
            raise ValueError("contingency carrier discovery/validation leakage")
    elif ca_bridge:
        parent_gate = json.loads((output / "parent-gate.json").read_text(encoding="utf-8"))
        incidents = json.loads(
            (output / "runtime-incidents.json").read_text(encoding="utf-8")
        )
        analysis = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
        if state["status"] == "completed" and not (
            parent_gate["pass"] and analysis["minimum_completion_gate"]
        ):
            raise ValueError("completed CA-bridge stage has a failed required gate")
        if analysis["run_status"] != state["status"]:
            raise ValueError("CA-bridge analysis/state status mismatch")
        if registration.get("stage") not in registration["protocol"].get("stages", ()):
            raise ValueError("invalid CA-bridge stage registration")
        if int(registration["workers"]) > 4:
            raise ValueError("CA-bridge worker cap exceeded")
        if not isinstance(incidents.get("incidents"), list):
            raise ValueError("invalid CA-bridge runtime incident ledger")
        if not isinstance(decision.get("pass"), bool):
            raise ValueError("CA-bridge decision lacks a Boolean gate")
        for name in record_files:
            for row in read_jsonl(output / name):
                if row.get("rulebook_inherited") is not None and row.get(
                    "rulebook_inherited"
                ) is not False:
                    raise ValueError("CA-bridge recipient inherited the c rulebook")
                if (
                    row.get("recipient_c_hash") is not None
                    and row.get("child_c_hash") != row.get("recipient_c_hash")
                ):
                    raise ValueError("CA-bridge recipient c rulebook changed")
                if row.get("founder_reused"):
                    generation = int(row["generation"])
                    if not (
                        generation == 1
                        or (
                            generation == 3
                            and row.get("donor_source")
                            == "explicit-founder-rescue"
                        )
                    ):
                        raise ValueError("unregistered CA-bridge founder reuse")
                if (
                    row.get("condition") == "renewal_off"
                    and int(row.get("generation", 1)) > 1
                    and not str(row.get("donor_source", "")).startswith(
                        "damaged-copy-g"
                    )
                ):
                    raise ValueError("renewal-off silently reused its founder")
        if registration["stage"] == "compression":
            codebooks = json.loads(
                (output / "codebooks.json").read_text(encoding="utf-8")
            )
            discovery = set(codebooks["discovery_seed_indices"])
            validation = set(codebooks["validation_seed_indices"])
            if discovery & validation or codebooks.get("leakage_allowed") is not False:
                raise ValueError("compression discovery/validation leakage")
    elif history_renewal:
        parent_gate = json.loads((output / "parent-gate.json").read_text(encoding="utf-8"))
        incidents = json.loads(
            (output / "runtime-incidents.json").read_text(encoding="utf-8")
        )
        analysis = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        audit = json.loads(
            (output / "carrier-audit-decision.json").read_text(encoding="utf-8")
        )
        natural = json.loads(
            (output / "natural-lineage-decision.json").read_text(encoding="utf-8")
        )
        branch = json.loads((output / "branch-decision.json").read_text(encoding="utf-8"))
        if state["status"] == "completed" and not (
            parent_gate["pass"] and analysis["minimum_completion_gate"]
        ):
            raise ValueError("completed history-renewal run has a failed required gate")
        if analysis["run_status"] != state["status"]:
            raise ValueError("history-renewal analysis/state status mismatch")
        if int(registration["workers"]) > 2:
            raise ValueError("history-renewal worker cap exceeded")
        if not isinstance(incidents.get("incidents"), list):
            raise ValueError("invalid history-renewal runtime incident ledger")
        if natural["pass"] and branch["engineered_branch_entered"]:
            raise ValueError("engineered branch ran after a native pass")
        if branch["engineered_branch_entered"] and not audit["pass"]:
            raise ValueError("engineered branch ran without an immediate carrier")
        natural_rows = list(read_jsonl(output / "natural-lineage.jsonl"))
        for row in natural_rows:
            generation = int(row["generation"])
            if row.get("founder_reused") and not (
                generation == 1
                or (
                    row.get("condition") == "rescue_g3"
                    and generation == 3
                    and row.get("donor_source") == "explicit-founder-rescue"
                )
            ):
                raise ValueError("unregistered founder reuse in native lineage")
            if (
                row.get("condition") == "passive_no_rewrite"
                and generation > 1
                and not str(row.get("donor_source", "")).startswith("post-copy-g")
            ):
                raise ValueError("passive lineage does not descend from the damaged copy")
        for name in ("mark-grid.jsonl", "mark-validation.jsonl"):
            for row in read_jsonl(output / name):
                if (
                    row.get("condition") == "renewal_off"
                    and int(row["generation"]) > 1
                    and not str(row.get("donor_source", "")).startswith("damaged-copy-g")
                ):
                    raise ValueError("mark renewal-off lineage silently reused its founder")
    elif renewal:
        parent_gate = json.loads((output / "parent-gate.json").read_text(encoding="utf-8"))
        analysis = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        if state["status"] == "completed" and not (
            parent_gate["pass"] and analysis["minimum_completion_gate"]
        ):
            raise ValueError("completed renewal run has a failed required gate")
        if analysis["run_status"] != state["status"]:
            raise ValueError("renewal analysis/state status mismatch")
        if int(registration["workers"]) > 4:
            raise ValueError("renewal worker cap exceeded")
    elif atlas:
        parent_gate = json.loads((output / "parent-gate.json").read_text(encoding="utf-8"))
        calibration_gate = json.loads(
            (output / "calibration-gate.json").read_text(encoding="utf-8")
        )
        analysis = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        if state["status"] == "completed" and not (
            parent_gate["pass"]
            and calibration_gate["pass"]
            and analysis["minimum_completion_gate"]
        ):
            raise ValueError("completed atlas has a failed required gate")
        if analysis["run_status"] != state["status"]:
            raise ValueError("atlas analysis/state status mismatch")
    else:
        source_gate = json.loads((output / "source-gate.json").read_text(encoding="utf-8"))
        if state["status"] == "completed" and not source_gate["pass"]:
            raise ValueError("completed run has a failed source gate")
    checksum_count = 0
    if require_sealed:
        checksum_count = len(verify_checksums(output))
    return {
        "valid": True,
        "status": state["status"],
        "cpu_seconds": ledger.get("cpu_seconds", ledger.get("aggregate_cpu_seconds")),
        "active_wall_seconds": ledger.get("active_wall_seconds"),
        "record_counts": counts,
        "checksum_count": checksum_count,
        "experiment_kind": kind or "washout-audit",
    }
