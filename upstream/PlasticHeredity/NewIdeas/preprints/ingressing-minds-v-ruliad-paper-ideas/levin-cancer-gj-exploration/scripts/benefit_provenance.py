"""Read-only H3 recovery closeout gate and immutable H4 input copying."""

from pathlib import Path

import numpy as np

from analyze_commitment_components import FLAGS
from analyze_reliability import analyze, audit_source
from changing_environment_design import PREDECESSOR, source_case
from recover_reliability import (CASE_ID, ORIGINAL, ORIGINAL_JOB, check_hashes,
    combine_summary, partial_prefix, read, require, snapshot)
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, source_check


def audit_predecessor(previous):
    require(previous == ROOT / PREDECESSOR, "Unexpected H3 predecessor")
    source_check()
    stored_hash = file_hash(previous / "independent_audit.json")
    manifest = read(previous / "recovery_manifest.json")
    require(manifest["original_run"] == str(ORIGINAL) and manifest["original_job"] == str(ORIGINAL_JOB), "Recovery origin changed")
    require(snapshot(ORIGINAL) == manifest["original_artifacts_sha256"]
        and snapshot(ORIGINAL_JOB) == manifest["original_job_artifacts_sha256"], "Original H3 artifacts changed")
    require(check_hashes(ROOT, manifest["execution_hashes_sha256"]), "Recovery execution files changed")
    require(check_hashes(previous / "frozen", manifest["new_frozen_hashes_sha256"]), "Recovery freeze changed")
    legacy = read(previous / "original_failed_summary.json")
    require(file_hash(previous / "original_failed_summary.json") == manifest["original_summary_sha256"], "Preserved summary changed")
    require(read(previous / "summary.json") == combine_summary(legacy, read(previous / "replacement_record.json"),
        manifest, file_hash(previous / "recovery_manifest.json")), "Composite reconstruction failed")
    require(manifest["rerun_case"] == CASE_ID and manifest["reused_cases"] ==
        [c["id"] for c in legacy["config"]["cases"] if c["id"] != CASE_ID], "Recovery selection changed")
    require(all((previous / n).is_symlink() and (previous / n).resolve() == ORIGINAL / n for n in manifest["reused_cases"])
        and not (previous / CASE_ID).is_symlink(), "Unexpected reused/rerun paths")
    require(file_hash(previous / CASE_ID / "spec.json") == manifest["spec_sha256"] == file_hash(ORIGINAL / CASE_ID / "spec.json"), "Rerun spec changed")
    require(read(previous / CASE_ID / "design.json") == read(ORIGINAL / CASE_ID / "design.json"), "Rerun schedule changed")
    prefix = partial_prefix(ORIGINAL / CASE_ID, previous / CASE_ID)
    # The legacy analyzer is pure. Do NOT call audit_recovery, which saves into its input run.
    audit = analyze(previous)
    stored = read(previous / "independent_audit.json")
    require(audit["array_check_count"] == 79113 and all(audit[k] for k in FLAGS)
        and audit["quality_gate"] and audit["ready_for_benefit_design"], "H3 quality gate failed")
    require(all(stored[k] == audit[k] for k in (*FLAGS, "array_check_count", "array_checks", "branches",
        "historical_controls", "fine_comparisons", "panel", "quality_gate", "ready_for_benefit_design")), "Stored H3 audit disagrees")
    require(stored["recovery_provenance_pass"] and stored["original_artifacts_unchanged"] and
        stored["interrupted_prefix"] == prefix and stored["represented_panel_integrations"] == audit["new_integrations"] == 5148,
        "Recovery accounting/provenance disagrees")
    require(snapshot(ORIGINAL) == manifest["original_artifacts_sha256"]
        and snapshot(ORIGINAL_JOB) == manifest["original_job_artifacts_sha256"]
        and file_hash(previous / "independent_audit.json") == stored_hash, "Historical artifacts changed during read-only audit")
    return dict(h3_audit=audit, recovery_provenance_pass=True, original_artifacts_unchanged=True,
        historical_audit_not_rewritten=True, stored_audit_sha256=stored_hash, interrupted_prefix=prefix)


def freeze_inputs(run, config):
    previous = ROOT / config["input_run"]
    audit = audit_predecessor(previous)
    write_json(run / "predecessor_audit.json", audit)
    old = read(previous / "summary.json")
    paths = {n: previous / "inputs" / n for n in old["inputs"]}
    paths.update(h3_summary=previous / "summary.json", h3_audit=previous / "independent_audit.json",
        h3_recovery_manifest=previous / "recovery_manifest.json")
    for a in ("M", "E"):
        family = "protein_m_pair" if a == "M" else "pooled_rewritten_e_pair"
        for f in (False, True):
            suffix = "_fine" if f else ""
            paths[f"benchmark_{a}{suffix}.npz"] = previous / f"confirmation__{family}_none{suffix}/round_01/endpoints.npz"
    require(len(paths) == 72, "Unexpected H4 input count")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        digest = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        require(file_hash(path) == digest == file_hash(inputs / name), "Input changed during copying")
        manifest[name] = dict(source=str(path), sha256=digest)
    indices = read(inputs / "reference.json")["ion_indices"]
    for case in config["cases"]:
        packet, _, _, _, checks = audit_source(inputs, config, source_case(case), indices)
        require(all(checks.values()) and packet.shape == (17, 2) and np.isfinite(packet).all(), "H4 source audit failed")
    write_json(inputs / "manifest.json", manifest)
    return manifest
