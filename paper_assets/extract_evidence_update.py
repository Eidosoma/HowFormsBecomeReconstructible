#!/usr/bin/env python3
"""Freeze the reviewed 10 October v0.17 evidence; no simulation or inference."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CELL = "../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/levin-cancer-gj-exploration/"
L20 = "../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L20-extension-1/"
FEP = "../PlasticHeredity/NewIdeas/preprints/fep-ideas/"
SELECTION = ROOT / "reviews/V0.17_EVIDENCE_UPDATE_SOURCES.json"
PACKAGE = ROOT / "paper_assets/data/evidence-update-v0.17-source-records.zip"
EXTRACT = ROOT / "paper_assets/data/evidence-update-v0.17.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def main():
    if any(p.exists() for p in (SELECTION, PACKAGE, EXTRACT)):
        raise SystemExit("Dated selection already exists; preserve it rather than overwrite.")
    paths = []
    checks = []
    runs = {
        "E048_partial_rollback": "partial_v1",
        "E049_rollback_persistence": "persistence_v1",
        "E050_fresh_rollback_confirmation": "confirmation_v1",
        "E052_precision_normalization": "robustness_v1",
    }
    for experiment, run in runs.items():
        base = f"experiments/{experiment}/"
        folder = base + f"runs/{run}/"
        paths.append(base + "PROTOCOL.md")
        for name in ("REPORT.md", "summary.json", "COMPLETE.json", "INDEPENDENT_AUDIT.json"):
            paths.append(folder + name)
        complete = read(folder + "COMPLETE.json")
        audit = read(folder + "INDEPENDENT_AUDIT.json")
        assert audit["status"] == "PASS"
        assert audit["complete_sha256"] == sha(ROOT / folder / "COMPLETE.json")
        for name in ("REPORT.md", "summary.json"):
            assert sha(ROOT / folder / name) == complete["outputs_sha256"][name]
        checks.append({"run": folder, "selected_report_and_summary_bindings": True,
                       "recorded_audit_binds_completion": True, "audit_rerun": False})
    paths.append("experiments/E052_precision_normalization/analysis/closeout_v1.json")
    for study, run in (("TT008", "prospective_v2"), ("TT009", "audit_v1")):
        base = f"experiments/theory-tests-lane/{study}/"
        folder = base + f"runs/{run}/"
        paths.extend(base + n for n in ("PROTOCOL.md", "INTERPRETATION.md", "CLOSEOUT.json"))
        paths.extend(folder + n for n in ("REPORT.md", "COMPLETE.json", "NATIVE_AUDIT.json"))
        complete = read(folder + "COMPLETE.json")
        close = read(base + "CLOSEOUT.json")
        identity = "complete_sha256" if study == "TT008" else "completion_sha256"
        assert close[identity] == sha(ROOT / folder / "COMPLETE.json")
        for name in ("REPORT.md", "NATIVE_AUDIT.json"):
            assert sha(ROOT / folder / name) == complete["outputs_sha256"][name]
        checks.append({"run": folder, "selected_report_and_audit_bindings": True,
                       "closeout_binds_completion": True, "audit_rerun": False})
    paths.extend("experiments/theory-tests-lane/TT008/" + n for n in
                 ("DEVELOPMENT.md", "REGISTRATION.json", "runs/prospective_v2/SCORING_AUDIT.json",
                  "runs/prospective_v2/PREDICTION_SEAL.json", "runs/prospective_v2/analysis.json"))
    paths.extend("experiments/theory-tests-lane/TT009/" + n for n in
                 ("source/fixed/run/REPORT.md", "source/transfer/run/REPORT.md",
                  "runs/audit_v1/SCIENTIFIC_VERDICT.json"))
    paths.extend(CELL + n for n in ("PAPER_DELAYED_PAUSE_CONVERGENCE_RESULTS.md",
                 "PAPER_DELAYED_PAUSE_CONVERGENCE_PROTOCOL.md", "storage/p31-completion-integrity-20261008.json"))
    paths.extend(L20 + "recipient-variation/" + n for n in
                 ("PILOT_RESULTS.md", "PILOT_TABLES.md", "PROPOSAL_V1.md", "PILOT_CLOSEOUT.md"))
    paths.extend(FEP + n for n in ("FEP_WEAK_PRIOR_CONFIRMATION_V1.md",
                 "FEP_WEAK_PRIOR_CONFIRMATION_V1_REPORT.md", "FEP_UNEXPECTED_CHANGE_V1.md",
                 "FEP_UNEXPECTED_CHANGE_V1_REPORT.md"))
    external = {
        "/mnt/bioIce1/fep-ideas/formal-checks/fep-weak-prior-confirmation-v1/attempt-01/RESULTS.json":
            "external/fep-weak-prior-confirmation/RESULTS.json",
        "/mnt/bioIce1/fep-ideas/formal-checks/fep-unexpected-change-v1/attempt-01/RESULTS.json":
            "external/fep-unexpected-change/RESULTS.json",
    }
    ongoing = ["experiments/E053_combined_numerical_confirmation/PROTOCOL.md",
               CELL + "PAPER_CONVERGED_PAUSE_BOUNDARY_PROTOCOL.md",
               L20 + "recipient-repeats/PROTOCOL_V1.md", FEP + "FEP_ANYTIME_CHANGE_V1.md"]
    paths.extend(ongoing)
    paths.extend(external)

    numerical = read("experiments/E052_precision_normalization/runs/robustness_v1/summary.json")
    assert numerical["primary_decision"] is False
    assert sum(numerical["primary_gates"].values()) == 2
    terminal = {key: {"mean": value["mean"], "ci95": value["ci95"]}
                for key, value in numerical["statistics"].items()
                if key.startswith("assay/32/") and "/native/scattered" in key}
    expected = {"reference": 83.40, "arithmetic32": 81.25, "grid_2m16": 8.01,
                "record_noise_1e4": 63.67, "floor_1e4": 69.53}
    for regime, value in expected.items():
        assert round(100 * terminal[f"assay/32/paired/{regime}/native/scattered"]["mean"], 2) == value
    forecast = read("experiments/theory-tests-lane/TT008/CLOSEOUT.json")
    assert forecast["primary_passed"] is True
    assert forecast["strata"]["0"]["n"] == 672
    assert forecast["strata"]["0"]["terminal_successes"] == 292
    assert round(forecast["closeout_brier"]["candidate"], 6) == 0.129131
    for rival in ("expression_history", "expression_unsigned"):
        assert forecast["closeout_contrasts"][rival]["lower_one_sided95"] > 0.002
    injury = read("experiments/theory-tests-lane/TT009/CLOSEOUT.json")
    cellular = read(CELL + "storage/p31-completion-integrity-20261008.json")
    assert cellular["focused_repair_qualified"] is True
    assert cellular["qualified_onward_transmission_established"] is False
    confirm, timing = [read(p) for p in external]
    assert confirm["core_lead_confirmed"] is True and all(confirm["criteria"].values())
    assert timing["core_lead_confirmed"] is False and sum(timing["criteria"].values()) == 2
    confirmation_cost = confirm["primary"]["post_change"]["core_changed"]["cost"]
    unexpected_cost = timing["post_change"]["unexpected_core_changed"]["arms"]["CT3-flat"]
    assert round(confirmation_cost["mean"], 9) == 0.098875402
    assert round(unexpected_cost["mean"], 9) == 0.155330691
    extract = {
        "scope": "Selected saved native values; no recomputed fit, interval or scientific outcome.",
        "E052": {"primary_gates": numerical["primary_gates"], "terminal_native_scattered": terminal},
        "TT008": {k: forecast[k] for k in ("closeout_brier", "closeout_contrasts", "strata", "matched_decisions")},
        "TT009": {k: injury[k] for k in ("independent_effects", "scientific_verdict")},
        "P31": {k: cellular[k] for k in ("focused_repair_qualified", "qualified_onward_transmission_established", "independent_checks")},
        "FEP": {"confirmation_criteria": confirm["criteria"], "confirmation_recovery_cost": confirmation_cost,
                "timing_criteria": timing["criteria"], "unexpected_recovery_cost": unexpected_cost},
    }
    records = []
    for name in sorted(set(paths)):
        path = ROOT / name
        if not path.is_file():
            raise FileNotFoundError(name)
        member = external.get(name, name[3:] if name.startswith("../") else name)
        records.append({"path": name, "archive_member": member, "bytes": path.stat().st_size,
                        "sha256": sha(path), "role": "ongoing protocol only" if name in ongoing else "completed evidence"})
    with zipfile.ZipFile(PACKAGE, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for record in records:
            z.write(ROOT / record["path"], record["archive_member"])
    with zipfile.ZipFile(PACKAGE) as z:
        for record in records:
            assert hashlib.sha256(z.read(record["archive_member"])).hexdigest() == record["sha256"]
    EXTRACT.write_text(json.dumps(extract, indent=2) + "\n")
    selection = {
        "version": "0.17", "selected_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "completed_selection": ["E048", "E049", "E050", "E052", "TT008", "TT009/P03", "P31", "D180", "FEP weak-prior confirmation", "FEP unexpected timing"],
        "new_evidence_notes": ["E70", "E71", "E72", "E73", "E74"],
        "extended_evidence_notes": ["E64", "E68"], "ongoing_protocols_only": ongoing,
        "files": records, "identity_checks": checks,
        "source_package": {"path": str(PACKAGE.relative_to(ROOT)), "sha256": sha(PACKAGE), "members": len(records)},
        "native_extract": {"path": str(EXTRACT.relative_to(ROOT)), "sha256": sha(EXTRACT)},
        "extractor": {"path": "paper_assets/extract_evidence_update.py", "sha256": sha(Path(__file__))},
        "limits": ["Selected reports, native summaries and available audit bindings, not a complete raw/executable archive.",
                   "Source replay/verification claims are attributed to retained receipts; no original audit is rerun.",
                   "D180's native arrays and P31's external trajectory archive are not incorporated.",
                   "Fresh samples, exposed development and ongoing protocols remain separate."],
        "model_runs_performed": False, "new_statistical_inference": False, "original_audit_rerun": False,
    }
    SELECTION.write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "source_files": len(records), "binding_groups": len(checks),
                      "source_package": str(PACKAGE.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
