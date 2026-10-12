#!/usr/bin/env python3
"""Preserve E051's completed records for the v0.17 manuscript selection.

Read saved summaries and provenance only. Do not import experiment code,
replay dynamics, recompute uncertainty, or alter experimental artifacts.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
BASE = EXPERIMENTS / "E051_cue_pairing_robustness"
RUN = BASE / "runs/robustness_v1"
PACKAGE = ROOT / "paper_assets/data/cue-pairing-v0.17-source-records.zip"
DATA = ROOT / "paper_assets/data/cue-pairing-v0.17.json"
RECORD = ROOT / "reviews/V0.17_SOURCES.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for path in (PACKAGE, DATA, RECORD):
        if path.exists():
            raise FileExistsError(f"Preserve the dated selection rather than overwrite it: {path}")
    read = lambda path: json.loads(path.read_text())
    summary = read(RUN / "summary.json")
    complete = read(RUN / "COMPLETE.json")
    audit = read(RUN / "INDEPENDENT_AUDIT.json")
    manifest = read(RUN / "manifest.json")
    closeout = read(BASE / "analysis/closeout_v1.json")
    files, checks = {}, []

    def add(path, role):
        relative = str(path.relative_to(ROOT))
        if relative not in files:
            files[relative] = {"path": relative, "archive_member": relative,
                               "role": role, "bytes": path.stat().st_size,
                               "sha256": sha(path)}

    def verify(path, expected, role):
        actual = sha(path)
        if actual != expected:
            raise ValueError(f"Source identity mismatch: {path}")
        checks.append({"path": str(path.relative_to(ROOT)), "sha256": actual,
                       "binding": role, "status": "match"})
        add(path, role)

    for name in ("REPORT.md", "summary.json"):
        verify(RUN / name, complete["outputs_sha256"][name], "scientific completion output")
    verify(RUN / "COMPLETE.json", audit["complete_sha256"], "saved independent audit input")
    verify(BASE / "audit.py", audit["audit_code_sha256"], "saved independent auditor identity")
    for name, expected in manifest["inputs_sha256"].items():
        verify(RUN / "inputs" / name, expected, "frozen scientific input")
    for name, expected in closeout["evidence_sha256"].items():
        verify(EXPERIMENTS / name, expected, "saved closeout evidence")
    for name in ("README.md", "PROTOCOL.md", "SOURCE_DATA.json", "analysis/closeout_v1.json",
                 "analysis/freeze_v1/manifest.json", "analysis/technical_v1.json",
                 "runs/robustness_v1/manifest.json", "analysis/early_look_v1/REPORT.md"):
        add(BASE / name, "campaign context, protocol or status")
    for name in ("README.md", "DRAFT_PROTOCOL.md", "PLAN.json"):
        add(EXPERIMENTS / "E052_precision_normalization" / name, "planning only; no result selected")
    add(EXPERIMENTS / "REVIEW_2026-10-08_SECOND_REVIEWER.md", "mechanism interpretation; not experimental evidence")

    stats = summary["statistics"]
    assert summary["blocks"] == list(range(34000, 34032))
    assert summary["lineages_per_condition"] == 512 and len(summary["conditions"]) == 35
    assert not summary["prior_cases_pooled"]
    assert audit["status"] == closeout["status"] == "PASS"
    for key, value in stats.items():
        assert len(value["block_means"]) == 32, key
        assert math.isclose(sum(value["block_means"]) / 32, value["mean"],
                            rel_tol=1e-12, abs_tol=1e-12), key
    gates = {"paired_baseline_lower_above_075":
             stats["assay/32/paired/exact_rewrite/scattered"]["ci95"][0] > .75}
    for condition in ("noise_0999", "reset_099"):
        gates[condition + "_lower_above_075"] = stats[f"assay/32/{condition}/exact_rewrite/scattered"]["ci95"][0] > .75
        gates[condition + "_difference_lower_above_minus_005"] = stats[f"pairing_effect/{condition}/exact_rewrite"]["ci95"][0] > -.05
    assert gates == summary["primary_gates"] and all(gates.values()) and summary["primary_decision"]

    terminal = []
    for condition, reset_rho, noise_rho in summary["pairings"]:
        for policy in summary["writers"]:
            key = f"assay/32/{condition}/{policy}/scattered"
            value = stats[key]
            n_success = round(value["mean"] * 512)
            assert n_success / 512 == value["mean"]
            terminal.append({"pairing": condition, "reset_correlation": reset_rho,
                             "noise_correlation": noise_rho, "policy": policy,
                             "successes": n_success, "lineages": 512,
                             "native_statistic_key": key, **value})
    selected = {key: value for key, value in stats.items()
                if key.startswith(("pairing_effect/", "writer_effect/", "mechanism/"))}
    DATA.write_text(json.dumps({"experiment": "E051", "selection_date": "2026-10-09",
        "status": summary["status"], "independent_unit": "block", "blocks": summary["blocks"],
        "primary_gates": gates, "primary_perturbations": summary["primary_perturbations"],
        "terminal_results": terminal, "selected_native_statistics": selected,
        "interval_scope": summary["interval_scope"], "summary_sha256": sha(RUN / "summary.json"),
        "scope": "Native saved means and intervals; counts derived from 512 equal-sized lineage observations. No bootstrap recomputation or dynamics replay."}, indent=2) + "\n")
    with zipfile.ZipFile(PACKAGE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for item in files.values():
            archive.write(ROOT / item["path"], item["archive_member"])
    with zipfile.ZipFile(PACKAGE) as archive:
        assert archive.testzip() is None
        for item in files.values():
            assert hashlib.sha256(archive.read(item["archive_member"])).hexdigest() == item["sha256"]
    arrays = [name for name in complete["outputs_sha256"] if name.endswith(".npz")]
    record = {"version": "0.17", "selected_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit_at_selection": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "selected_experiments": ["E051"], "planning_only": ["E052"],
        "scope": "Add completed cue-pairing robustness only; ongoing follow-ups and E048–E050 are not new result selections in this revision.",
        "files": list(files.values()), "identity_checks": checks,
        "saved_block_means_checked": len(stats), "primary_decisions_checked": gates,
        "recorded_audit": {key: audit[key] for key in ("status", "utc", "blocks", "body_cue_observations", "terminal_cue_observations", "summaries_checked")},
        "recorded_closeout": {"status": closeout["status"], "utc": closeout["utc"], "scientific": closeout["runs"]["robustness_v1"]},
        "raw_array_availability": {"declared_npz_outputs": len(arrays), "present_locally": sum((RUN / name).is_file() for name in arrays)},
        "source_package": {"path": str(PACKAGE.relative_to(ROOT)), "sha256": sha(PACKAGE), "members": len(files)},
        "native_extract": {"path": str(DATA.relative_to(ROOT)), "sha256": sha(DATA)},
        "extractor": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": sha(Path(__file__))},
        "limits": "Portable text/code/metadata selection, not the full raw-array/runtime archive. Saved replay and closeout are attributed to their original execution. Technical legacy-match flags apply to excluded fixtures, not to a fresh scientific cohort.",
        "model_runs_performed": False, "new_statistical_inference": False, "original_audit_rerun": False}
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Preserved {len(files)} source records; verified {len(checks)} bindings, {len(stats)} saved means and five primary decisions.")


if __name__ == "__main__":
    main()
