#!/usr/bin/env python3
"""Verify the portable v0.20 selection and transcribe retained native summaries.

No simulation, fitting, resampling or original scientific audit is rerun.
--check compares the existing extract without writing it.
"""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reviews/V0.20_EVIDENCE_UPDATE_SOURCES.json"
OUTPUT = ROOT / "paper_assets/data/evidence-update-v0.20.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract():
    manifest = json.loads(MANIFEST.read_text())
    package = ROOT / manifest["package"]["path"]
    assert digest(package.read_bytes()) == manifest["package"]["sha256"]
    raw = {}
    with zipfile.ZipFile(package) as archive:
        for item in manifest["sources"]:
            data = archive.read(item["member"])
            assert digest(data) == item["sha256"]
            assert len(data) == item["bytes"]
            raw[item["member"]] = data

    def read(member):
        return json.loads(raw[member])

    studies, checks = {}, []
    prefix = "WhereDoFormsComeFrom/experiments/"

    def bind_outputs(base, complete):
        checked = []
        for name, expected in complete["outputs_sha256"].items():
            member = base + name
            if member in raw:
                assert digest(raw[member]) == expected, member
                checked.append(name)
        assert "REPORT.md" in checked
        return checked

    for tag, run in (("TT015", "audit_v1"), ("TT016", "validation_v1")):
        base = prefix + f"theory-tests-lane/{tag}/"
        folder = base + f"runs/{run}/"
        complete, close = read(folder + "COMPLETE.json"), read(base + "CLOSEOUT.json")
        assert close["status"] == "PASS"
        assert close.get("completion_sha256", close.get("complete_sha256")) == digest(raw[folder + "COMPLETE.json"])
        outputs = bind_outputs(folder, complete)
        names = ["analysis.json"] if tag == "TT016" else ["serial_analysis.json", "noise_analysis.json"]
        studies[tag] = {name: read(folder + name) for name in names}
        checks.append({"study": tag, "bound_outputs": outputs, "closeout_binds_completion": True,
                       "verification_scope": "recorded full native replay; not rerun for paper"})

    tt = studies["TT016"]["analysis.json"]
    assert tt["blocks"] == 64 and tt["records"] == 1024
    assert tt["scientific_verdict"] == "PRACTICAL_SUPERIORITY_PASS"
    for arm, counts in {
        "independent_baseline": (794, 880), "independent_one_time": (856, 912),
        "independent_repeated": (920, 934), "independent_shuffled": (0, 87),
        "matched_baseline": (458, 823), "matched_one_time": (557, 868),
        "matched_repeated": (916, 945), "matched_shuffled": (0, 70),
    }.items():
        for metric, count in zip(("uninterrupted", "terminal"), counts):
            assert tt["rates"][arm][metric]["mean"] == count / 1024
    assert tt["primary_effect"]["mean"] == (920 - 794) / 1024
    assert tt["primary_effect"]["lower_one_sided95"] > .05

    for name, run in (
        ("E055_stress_capture_recovery", "capture_v1"),
        ("E056_sign_magnitude_substitution", "substitution_v1"),
        ("E057_fresh_capture_confirmation", "confirmation_v1"),
    ):
        tag = name[:4]
        base = prefix + f"{name}/runs/{run}/"
        complete, audit = read(base + "COMPLETE.json"), read(base + "INDEPENDENT_AUDIT.json")
        assert complete["status"] == "COMPLETE" and audit["status"] == "PASS"
        assert audit["complete_sha256"] == digest(raw[base + "COMPLETE.json"])
        outputs = bind_outputs(base, complete)
        assert "summary.json" in outputs
        studies[tag] = read(base + "summary.json")
        checks.append({"study": tag, "bound_outputs": outputs, "audit_binds_completion": True,
                       "verification_scope": "recorded independent replay; not rerun for paper"})
    assert studies["E057"]["independent_blocks"] == 32
    assert studies["E057"]["primary_confirmed"] and studies["E057"]["controls_pass"]
    assert studies["E057"]["status"] == "CONFIRMED"
    assert set(studies["E057"]["primary_effects"].values()) == {"POSITIVE_EFFECT"}
    assert not studies["E057"]["prior_cases_pooled"]

    for tag, run in (("H002", "h002_development_v1"), ("H003", "h003_development_v1"),
                     ("H004", "h004_confirmation_v1"), ("H005", "h005_development_v1"),
                     ("H006", "h006_development_v1"), ("H007", "h007_development_v1"),
                     ("H008", "h008_development_v1")):
        base = prefix + f"hopfield-lane/runs/{run}/"
        studies[tag] = read(base + "summary.json")
        if base + "checksums.json" in raw:
            checksum = read(base + "checksums.json")
            outputs = []
            for name, expected in checksum.items():
                if base + name in raw:
                    assert digest(raw[base + name]) == expected
                    outputs.append(name)
            assert "REPORT.md" in outputs and "summary.json" in outputs
            checks.append({"study": tag, "bound_outputs": outputs,
                           "verification_scope": "retained checksums and audit; not a new raw-array replay"})
    h = studies["H004"]
    assert h["blocks"] == 72 and h["primary_qualification"]["qualified"]
    assert h["early_intervention_contrast"]["qualified"] and h["audit_passed"]
    assert round(100*h["terminal"]["cue_gain4"]["renewal"]["mean"], 2) == 92.53
    assert round(100*h["terminal"]["cue_gain4"]["protected_copy"]["mean"], 2) == 98.87

    for name, run in (("p08_budgeted_repair_v0_1", "pilot_v1"),
                      ("p08_repair_frequency_v0_1", "pilot_v1"),
                      ("p08_repair_efficiency_v0_1", "prospective_v1")):
        base = prefix + f"theory-lane/{name}/runs/{run}/"
        complete = read(base + "COMPLETE.json")
        assert complete["status"] == "COMPLETE"
        outputs = bind_outputs(base, complete)
        studies[name] = read(base + "analysis.json")
        studies[name + "_verification"] = read(base + "VERIFICATION.json")
        checks.append({"study": name, "bound_outputs": outputs,
                       "verification_scope": "same-lane checks and selected flat-dynamics replay; not exhaustive continuation replay"})
    efficiency = studies["p08_repair_efficiency_v0_1"]
    assert efficiency["blocks"] == 132 and efficiency["records"] == 2112
    assert efficiency["primary"]["verdict"] == "UNRESOLVED"
    for calls, count in ((1, 1761), (6, 1833), (18, 1879)):
        assert efficiency["counts"][f"repairs_{calls}"]["uninterrupted"] == count
    base = prefix + "theory-lane/p08_failure_boundary_audit_v0_1/"
    complete = read(base + "COMPLETE.json")
    assert complete["status"] == "COMPLETE"
    assert complete["counts"] == {"rescue": 46, "both_fail": 0, "harm": 0, "both_pass": 0}
    for name, expected in complete["files_sha256"].items():
        if base + name in raw:
            assert digest(raw[base + name]) == expected
    studies["P08_failure_boundary"] = {"completion": complete, "verification": read(base + "VERIFICATION.json"),
                                       "selection": read(base + "SELECTION.json")}

    cell = "PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/levin-cancer-gj-exploration/"
    p32 = read(cell + "storage/p32-completion-integrity-20261012.json")
    assert p32["all_results_valid"] and p32["full_pause_panel_qualified"]
    assert all(p32["checks"].values())
    assert p32["result_files"] == 856 and p32["raw_phases"] == 7352
    assert p32["independent_checks"] == 525505
    studies["P32"] = p32
    checks.append({"study": "P32", "recorded_completion_checks_pass": True,
                   "verification_scope": "retained counts and completion-integrity record; external raw run unavailable locally"})

    base = "external/L20/"
    run = "l20_extension1_recipient_founders_population_v1_attempt1"
    complete = read(base + f"runs/{run}/COMPLETE.json")
    audit = read(base + f"logs/{run}_saved_audit_v1.json")
    assert complete["status"] == "COMPLETE" and audit["passes"]
    assert audit["complete_sha256"] == digest(raw[base + f"runs/{run}/COMPLETE.json"])
    for name in ("summary.json", "records.json"):
        rel = f"outputs/{run}/{name}"
        original = "/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/" + rel
        assert complete["output_sha256"][original] == digest(raw[base + rel])
    studies["D182"] = read(base + f"outputs/{run}/summary.json")
    checks.append({"study": "D182", "audit_binds_completion": True, "native_summary_and_records_bound": True,
                   "verification_scope": "recorded replay and saved audit; not rerun for paper"})
    return {"version": "0.20", "selection_utc": manifest["selection_utc"],
            "source_package_sha256": manifest["package"]["sha256"], "sources_verified": len(raw),
            "simulation_rerun": False, "new_inference": False, "original_audits_rerun": False,
            "checks": checks, "studies": studies}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = extract()
    if args.check:
        assert json.loads(OUTPUT.read_text()) == result
    else:
        OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Verified {result['sources_verified']} frozen records; native summaries {'match' if args.check else 'extracted'}. No new simulations or inference.")
