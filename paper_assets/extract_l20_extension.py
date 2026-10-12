#!/usr/bin/env python3
"""Package selected completed L20 records and extract existing summary fields.

This imports no simulator and computes no statistical estimates or intervals.
The earlier review pins the selection; this does not follow new experiments.
"""

from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT.parent / "PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L20-extension-1"
DEFAULT_RUN_ROOT = Path("/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1")
SUBDIRS = {"D141": "", "D142": "repeated-futures", "D143": "crossed-address-noise",
           "D144": "compatible-feedback", "D145": "serial-compatible-feedback",
           "D146": "phase-budget"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    args = parser.parse_args()
    review_path = ROOT / "reviews/L20_EXTENSION_1_REVIEW_CHECKS_2026-09-18.json"
    review = json.loads(review_path.read_text())
    entries, payloads, summaries, runs = [], {}, {}, []

    def add(path, member, expected=None):
        data = path.read_bytes()
        digest = sha(data)
        if expected is not None and digest != expected:
            raise ValueError(f"Selected source changed: {path}")
        if member in payloads:
            raise ValueError(f"Duplicate package member: {member}")
        entries.append({"source": str(path.resolve()), "member": member,
                        "sha256": digest, "bytes": len(data)})
        payloads[member] = data
        return data

    for reviewed in review["runs"]:
        exp, rid = reviewed["experiment"], reviewed["run_id"]
        run, out = args.run_root / "runs" / rid, args.run_root / "outputs" / rid
        complete = json.loads(add(run / "COMPLETE.json", f"{exp}/run/COMPLETE.json",
                                 reviewed["complete_sha256"]))
        add(run / "MANIFEST.json", f"{exp}/run/MANIFEST.json", complete["manifest_sha256"])
        report = PROGRAM / SUBDIRS[exp] / "RESULTS.md"
        add(report, f"{exp}/program/RESULTS.md", reviewed["report_sha256"])
        input_hashes = {}
        for line in (out / "input_hashes.sha256").read_text().splitlines():
            digest, filename = line.split(maxsplit=1)
            input_hashes[filename] = digest
        protocol = PROGRAM / SUBDIRS[exp] / "PROTOCOL_V1.md"
        if str(protocol) not in input_hashes:
            raise ValueError(f"Protocol absent from recorded input set: {protocol}")
        add(protocol, f"{exp}/program/PROTOCOL_V1.md", input_hashes[str(protocol)])
        summary = json.loads(add(out / "summary.json", f"{exp}/output/summary.json",
                                 complete["summary_sha256"]))
        summaries[exp] = summary
        # Preserve indexed metadata, without duplicating large raw block files.
        for original, expected in complete["output_sha256"].items():
            filename = Path(original).name
            if filename in {"summary.json", "input_hashes.sha256", "output_hashes.sha256"} or filename.startswith(("block_", "diagnostic_", "outcome_", "founder_")):
                continue
            if filename.endswith(".npz"):
                continue
            add(out / filename, f"{exp}/output/{filename}", expected)
        input_pin = next((h for p, h in complete["output_sha256"].items()
                          if Path(p).name == "input_hashes.sha256"), None)
        add(out / "input_hashes.sha256", f"{exp}/output/input_hashes.sha256", input_pin)
        add(out / "output_hashes.sha256", f"{exp}/output/output_hashes.sha256",
            complete["hash_file_sha256"])
        runs.append({"experiment": exp, "run_id": rid,
                     "complete_sha256": reviewed["complete_sha256"],
                     "completed_utc": complete["completed_utc"],
                     "status": complete["status"],
                     "prior_indexed_output_count": reviewed["indexed_output_count"],
                     "primary": summary.get("primary"), "label": summary.get("label")})

    for relative in ["serial-compatible-feedback/SAVED_STATE_REVIEW_PLAN_V1.md",
                     "serial-compatible-feedback/SAVED_STATE_REVIEW_V1.md",
                     "reviews/CROSSED_ADDRESS_GEOMETRY_2026-09-17.md",
                     "reviews/REPEATED_STAGE_DIVERGENCE_2026-09-17.md"]:
        add(PROGRAM / relative, f"saved_reviews/program/{relative}")
    saved = args.run_root / "outputs/l20_extension1_serial_compatible_feedback_v1_attempt1_saved_review_v1_attempt1"
    # These pins are given in the completed saved-review report.
    add(saved / "COMPLETE.json", "saved_reviews/D145/COMPLETE.json",
        "dc01aa9034ac2f6640183ff112bae5233d3796f4e3c487e7f74902eb2daebb11")
    add(saved / "summary.json", "saved_reviews/D145/summary.json",
        "512ae18dbdef74f92247827aea0fadbd83d143928bf039badb164182812be40a")
    add(args.run_root / "logs/d145_saved_review_audit_v1.json",
        "saved_reviews/D145/audit.json",
        "8ee0632141d9fda524ec53c3b8c56702996ed6643392e740be816209e0e43660")

    extract = {
        "scope": "Selection of existing summary fields; native units and original intervals. No new inference.",
        "preference_points_multiplier": 100,
        "primary": {k: v.get("primary") for k, v in summaries.items() if "primary" in v},
        "D142_groups": summaries["D142"]["groups"],
        "D143_groups": summaries["D143"]["groups"],
        "D145_B_table_groups": [g for g in summaries["D145"]["groups"]
                               if g["role"] == 1 and g["condition"] in {"zero", "q4", "copy"}],
        "D145_B_terminal_contrasts": [g for g in summaries["D145"]["contrasts"]
                                      if g["role"] == 1 and g["condition"] == "q4" and g["generation"] == 3],
        "D145_B_terminal_copy_contrast": [g for g in summaries["D145"]["copy_contrasts"]
                                         if g["role"] == 1 and g["generation"] == 3],
        "D145_B_compatible_serial_change": [g for g in summaries["D145"]["serial_changes"]
                                            if g["role"] == 1 and g["condition"] == "q4"],
        "D146_B_terminal_groups": [g for g in summaries["D146"]["groups"]
                                   if g["role"] == 1 and g["generation"] == 3],
        "D146_B_terminal_contrasts": [g for g in summaries["D146"]["contrasts"]
                                      if g["role"] == 1 and g["generation"] == 3],
        "source_summaries": [{"experiment": x["experiment"], "run_id": x["run_id"],
                              "sha256": next(e["sha256"] for e in entries
                                             if e["member"] == x["experiment"] + "/output/summary.json")}
                             for x in runs],
    }
    extract_path = ROOT / "paper_assets/data/l20-extension-v1.json"
    extract_path.write_text(json.dumps(extract, indent=2) + "\n")
    package = ROOT / "paper_assets/data/l20-extension-v0.11-source-records.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for member, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(member, (2026, 9, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        assert all(sha(z.read(e["member"])) == e["sha256"] for e in entries)
    selection = {
        "selection_date": "2026-09-18", "working_version": "v0.11",
        "included_experiments": list(SUBDIRS), "evidence_notes": ["E38", "E39", "E40", "E41"],
        "scope": "Completed selected reports/protocols and retained metadata. No raw arrays or complete executable dependency closure; not a standalone runnable archive.",
        "review_checks": str(review_path.relative_to(ROOT)), "review_checks_sha256": sha(review_path.read_bytes()),
        "runs": runs, "files": entries,
        "package": str(package.relative_to(ROOT)), "package_sha256": sha(package.read_bytes()),
        "package_files": len(entries), "extract": str(extract_path.relative_to(ROOT)),
        "extract_sha256": sha(extract_path.read_bytes()),
        "extractor": str(Path(__file__).resolve().relative_to(ROOT)), "extractor_sha256": sha(Path(__file__).read_bytes()),
        "model_runs_performed": False, "new_inferential_analysis": False,
        "original_scientific_audits_rerun": False,
    }
    path = ROOT / "reviews/V0.11_L20_SOURCES.json"
    path.write_text(json.dumps(selection, indent=2) + "\n")
    print(f"Packaged {len(entries)} selected records; extracted D145 table and native summary fields.")


if __name__ == "__main__":
    main()
