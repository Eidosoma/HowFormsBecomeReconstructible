#!/usr/bin/env python3
"""Verify the frozen v0.19 selection and extract native summaries.

Reads the portable source package only. No simulations, fitting, resampling,
or original audit is rerun. --check compares the extract without writing it.
"""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reviews/V0.19_EVIDENCE_UPDATE_SOURCES.json"
OUTPUT = ROOT / "paper_assets/data/evidence-update-v0.19.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract():
    manifest = json.loads(MANIFEST.read_text())
    package = ROOT / manifest["package"]["path"]
    assert digest(package.read_bytes()) == manifest["package"]["sha256"]
    with zipfile.ZipFile(package) as z:
        raw = {}
        for item in manifest["sources"]:
            data = z.read(item["member"])
            assert digest(data) == item["sha256"]
            assert len(data) == item["bytes"]
            raw[item["member"]] = data

    def read(member):
        return json.loads(raw[member])

    checks = []
    studies = {}
    for study, folder, run in (
        ("E053", "E053_combined_numerical_confirmation", "robustness_v1"),
        ("E054", "E054_record_interventions", "interventions_v1"),
    ):
        base = f"WhereDoFormsComeFrom/experiments/{folder}/runs/{run}/"
        complete, audit = read(base + "COMPLETE.json"), read(base + "INDEPENDENT_AUDIT.json")
        assert complete["status"] == "COMPLETE" and audit["status"] == "PASS"
        assert audit["complete_sha256"] == digest(raw[base + "COMPLETE.json"])
        for name in ("REPORT.md", "summary.json"):
            assert complete["outputs_sha256"][name] == digest(raw[base + name])
        summary = read(base + "summary.json")
        studies[study] = summary
        checks.append({"study": study, "completion_and_selected_outputs_bound": True,
                       "recorded_audit_passes": True, "audit_rerun": False})
    assert len(studies["E053"]["blocks"]) == 32
    assert not studies["E053"]["primary_decision"]
    assert sum(studies["E053"]["primary_gates"].values()) == 2
    assert studies["E054"]["controls_pass"]
    assert studies["E054"]["independent_blocks"] == 32

    for number in range(10, 15):
        study = f"TT{number:03d}"
        base = f"WhereDoFormsComeFrom/experiments/theory-tests-lane/{study}/"
        run = base + ("runs/validation_v1/" if number == 14 else "runs/audit_v1/")
        complete, close = read(run + "COMPLETE.json"), read(base + "CLOSEOUT.json")
        assert close["status"] == "PASS"
        assert close.get("completion_sha256", close.get("complete_sha256")) == digest(raw[run + "COMPLETE.json"])
        checked = []
        for member, data in raw.items():
            if member.startswith(run) and member[len(run):] in complete["outputs_sha256"]:
                assert digest(data) == complete["outputs_sha256"][member[len(run):]]
                checked.append(member[len(run):])
        assert "REPORT.md" in checked and "analysis.json" in checked
        studies[study] = read(run + "analysis.json")
        checks.append({"study": study, "closeout_binds_completion": True,
                       "checked_outputs": checked, "audit_rerun": False,
                       "full_native_replay_recorded": number != 11})
    tt = studies["TT014"]
    assert tt["blocks"] == 64 and tt["cohort_records"] == 1024 and tt["conjunction_pass"]
    for arm, count in (("outgoing", 6678), ("recipient_completion", 7164), ("recipient_shuffled", 2116), ("erased", 0)):
        rate = tt["rate_summaries"][arm]["intended"]
        assert rate["successes"] == count and rate["reads"] == 8192
        assert rate["mean"] == count / 8192
    assert tt["primary_effects"]["recipient_minus_outgoing"]["mean"] == (7164 - 6678) / 8192

    for study in ("p05_serial_repair_v0_1", "p05_cue_noise_repair_v0_1", "p05_noise_repair_withdrawal_v0_1"):
        base = f"WhereDoFormsComeFrom/experiments/theory-lane/{study}/runs/pilot_v1/"
        complete = read(base + "COMPLETE.json")
        assert complete["status"] == "COMPLETE" and complete["records"] == 256
        for name in ("REPORT.md", "analysis.json"):
            assert complete["outputs_sha256"][name] == digest(raw[base + name])
        studies[study] = read(base + "analysis.json")
        checks.append({"study": study, "selected_outputs_bound": True,
                       "verification_scope": "internal checks and sampled native replay; not full independent serial validation",
                       "audit_rerun": False})

    base = "external/L20/"
    run = "l20_extension1_recipient_repeats_population_v1_attempt1"
    complete = read(base + f"runs/{run}/COMPLETE.json")
    assert complete["status"] == "COMPLETE"
    audit = read(base + f"logs/{run}_saved_audit_v1.json")
    assert audit["passes"] and audit["complete_sha256"] == digest(raw[base + f"runs/{run}/COMPLETE.json"])
    for name in ("summary.json", "records.json"):
        member = base + f"outputs/{run}/{name}"
        original = "/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/" + f"outputs/{run}/{name}"
        assert digest(raw[member]) == complete["output_sha256"][original]
    studies["D181"] = read(base + f"outputs/{run}/summary.json")
    assert studies["D181"]["source_records"] == 32
    assert len(studies["D181"]["blocks"]) == 4
    checks.append({"study": "D181", "selected_outputs_bound": True,
                   "recorded_audit_binds_completion": True, "audit_rerun": False})

    base = "external/FEP/"
    manifest_fep = read(base + "attempt-02/MANIFEST.json")
    rb = read(base + "readback-2026-10-11/READBACK.json")
    assert manifest_fep["status"] == "COMPLETE" and rb["status"] == "PASS"
    assert rb["manifest"]["sha256"] == digest(raw[base + "attempt-02/MANIFEST.json"])
    assert not rb["core_lead_confirmed"] and rb["independent_blocks"] == 27648
    result_identity = [x for x in manifest_fep["outputs"] if x["path"].endswith("/RESULTS.json")]
    assert len(result_identity) == 1
    assert result_identity[0]["sha256"] == digest(raw[base + "attempt-02/RESULTS.json"])
    studies["FEP_anytime"] = read(base + "attempt-02/RESULTS.json")
    studies["FEP_anytime_readback"] = {k: rb[k] for k in
        ("status", "assertions", "independent_blocks", "core_lead_confirmed", "criteria", "CT3_anytime_unexpected_core_recovery")}
    checks.append({"study": "FEP_anytime", "readback_binds_completion": True, "audit_rerun": False})
    return {"version": "0.19", "selection_utc": manifest["selection_utc"],
            "source_package_sha256": manifest["package"]["sha256"],
            "sources_verified": len(raw), "simulation_rerun": False, "new_inference": False,
            "checks": checks, "studies": studies}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    result = extract()
    if args.check:
        assert json.loads(OUTPUT.read_text()) == result
    else:
        OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Verified {result['sources_verified']} frozen records; native summaries {'match' if args.check else 'extracted'}. No simulations or new inference.")
