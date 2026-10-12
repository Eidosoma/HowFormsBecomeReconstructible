#!/usr/bin/env python3
"""Freeze the reviewed v0.13 text/metadata selection without executing science.

Copies retained summaries, reports and provenance. Does not import campaign
code, load trajectory arrays, fit models, recompute intervals or follow new runs.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT.parent / "PlasticHeredity/NewIdeas/preprints"
L20 = PROGRAM / "ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L20-extension-1"
FEP = PROGRAM / "fep-ideas"
EXT_L20 = Path("/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1")
EXT_FEP = Path("/mnt/bioIce1/fep-ideas/formal-checks")
DATA = ROOT / "paper_assets/data/prediction-fep-v0.13.json"
PACKAGE = ROOT / "paper_assets/data/prediction-fep-v0.13-source-records.zip"
RECORD = ROOT / "reviews/V0.13_SOURCES.json"

L20_DOCS = {
    "D160": ("difference-ablation", ("RESULTS.md", "PROTOCOL_V1.md")),
    "D161": ("confirmation", ("PLANNING_REPORT.md", "PLAN_V1.md")),
    "D162": ("confirmation", ("PILOT64_RESULTS.md", "PILOT64_PROTOCOL_V1.md", "PILOT64_TABLES.md", "PILOT64_EXECUTION.md")),
    "D163": ("asymmetry", ("RESULTS.md", "PROTOCOL_V1.md")),
    "D164": ("shared-decoder", ("RESULTS.md", "PROTOCOL_V1.md")),
    "D165": ("decoder-transport", ("RESULTS.md", "PROTOCOL_V1.md")),
    "D166": ("feature-support", ("RESULTS.md", "PROTOCOL_V1.md")),
    "D167": ("passive-stages", ("RESULTS.md", "PROTOCOL_V1.md")),
    "D168": ("passive-feedback", ("RESULTS.md", "PROTOCOL_V1.md")),
    "D169": ("address-swap", ("RESULTS.md", "PROTOCOL_V1.md", "TABLES.md", "WORKLOG.md")),
    "D170": ("address-aware-prediction", ("DESIGN_REVIEW.md", "PROPOSAL_V1.md")),
    "D171": ("address-aware-prediction", ("RESULTS.md", "EXECUTION_PROTOCOL_V1.md", "TABLES.md", "QUALIFICATION.md", "WORKLOG.md")),
}
L20_RUNS = {
    "D162": ("l20_extension1_pilot64_v1_attempt1", "d77470be6d251f4d42344a6acfe0173fe3a542b04be2649de6e998bcfd95da53"),
    "D169": ("l20_extension1_address_swap_v1_attempt1", "898fd26329f89d8123abf6561ded22876e258612195d1b748d18e5df79e8dcd2"),
    "D171": ("l20_extension1_settings_prediction_dev_v1_attempt1", "41a9fa1d8d63bdcdfab971b5470ab614bf4d2b13cd3a73555a8f239130db51d4"),
}
FEP_STUDIES = (
    "FACTOR_REVISION", "ADAPTIVE_CALIBRATION", "FORECAST_VALIDATION",
    "GENERALIZATION", "GENERALIZATION_ATTRIBUTION", "JOINT_DEPLOYMENT",
    "SECOND_FEEDBACK",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    entries, checks, extracted, seen = [], [], {}, {}

    def add(path, member, study, role):
        path = path.resolve()
        if path in seen:
            return
        if not path.is_file():
            raise FileNotFoundError(path)
        row = {"path": str(path), "archive_member": member, "study": study,
               "role": role, "bytes": path.stat().st_size, "sha256": digest(path)}
        entries.append(row)
        seen[path] = row

    def verify(path, expected, context):
        path = Path(path)
        actual = digest(path) if path.is_file() else None
        row = {"path": str(path), "expected_sha256": expected,
               "actual_sha256": actual, "context": context,
               "status": "match" if actual == expected else "missing" if actual is None else "mismatch"}
        checks.append(row)
        if row["status"] != "match":
            raise ValueError(row)

    for study, (folder, names) in L20_DOCS.items():
        for name in names:
            add(L20 / folder / name, f"L20/documents/{folder}/{name}", study, "report_or_protocol")

    for study, (run, expected) in L20_RUNS.items():
        completion_path = EXT_L20 / "runs" / run / "COMPLETE.json"
        verify(completion_path, expected, "completion quoted in reviewed report")
        completion = json.loads(completion_path.read_text())
        assert completion["status"] == "COMPLETE"
        add(completion_path, f"L20/{study}/COMPLETE.json", study, "completion")
        manifest_path = completion_path.with_name("MANIFEST.json")
        verify(manifest_path, completion["manifest_sha256"], "completion manifest binding")
        add(manifest_path, f"L20/{study}/MANIFEST.json", study, "manifest")
        for name in ("summary.json", "verification.json", "FORECAST_SEAL.json", "OUTCOMES_STARTED.json"):
            p = EXT_L20 / "outputs" / run / name
            if not p.exists():
                if name == "summary.json":
                    raise FileNotFoundError(p)
                continue
            verify(p, completion["output_sha256"][str(p)], "selected completion output binding")
            add(p, f"L20/{study}/{name}", study, "retained_summary_or_barrier")
            if name == "summary.json":
                extracted[study] = json.loads(p.read_text())
        audit_path = EXT_L20 / "logs" / f"{run}_saved_audit_v1.json"
        audit = json.loads(audit_path.read_text())
        assert audit["passes"]
        verify(completion_path, audit["complete_sha256"], "saved-audit completion binding")
        add(audit_path, f"L20/{study}/saved_audit.json", study, "retained_audit_not_rerun")

    for label in FEP_STUDIES:
        study = "FEP_" + label
        stem = f"FEP_{label}_V1"
        for suffix in (".md", "_REPORT.md"):
            add(FEP / (stem + suffix), f"FEP/{label}/{stem + suffix}", study, "report_or_protocol")
        if label == "GENERALIZATION":
            p = FEP / "FEP_GENERALIZATION_V1_CORRECTION.md"
            add(p, f"FEP/{label}/{p.name}", study, "preserved_correction")
        slug = "fep-" + label.lower().replace("_", "-") + "-v1"
        run = EXT_FEP / slug / ("attempt-02" if label == "GENERALIZATION" else "attempt-01")
        manifest = json.loads((run / "MANIFEST.json").read_text())
        add(run / "MANIFEST.json", f"FEP/{label}/MANIFEST.json", study, "manifest")
        for role in ("inputs", "outputs"):
            for row in manifest[role]:
                p = Path(row["path"])
                if not p.is_absolute():
                    p = run / p
                verify(p, row["sha256"], f"{study} manifest {role}")
                # Retain this study's scientific checker and selected portable
                # output metadata; full raw/dependency closure is not packaged.
                if role == "inputs" and p.suffix == ".py" and p.parent == FEP:
                    add(p, f"FEP/{label}/source/{p.name}", study, "declared_source_not_executed")
                if role == "outputs" and p.parent == run and p.name in {
                    "RESULTS.json", "QUALIFICATION.json", "POPULATION.json", "PREPARATION.json", "RUN_LOG.txt"
                }:
                    add(p, f"FEP/{label}/{p.name}", study, "retained_results_or_checks")
        results = json.loads((run / "RESULTS.json").read_text())
        if label == "GENERALIZATION":
            keys = ("new_panel", "known_Q_floors", "summary")
        elif label == "JOINT_DEPLOYMENT":
            keys = ("panel", "known_panel_control", "summary")
        elif label == "GENERALIZATION_ATTRIBUTION":
            keys = ("summary",)
        else:
            keys = tuple(results)
        extracted[study] = {k: results[k] for k in keys if k in results}

    data = {"version": "v0.13", "selected_on": "2026-09-24",
            "scope": "Native retained summaries; no fitting, simulation or uncertainty recalculation.",
            "results": extracted}
    DATA.write_text(json.dumps(data, indent=2) + "\n")
    # Freeze exact input bytes in the portable package, independently verifying
    # every archive member after writing. Never writes into a source campaign.
    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for row in entries:
            p = Path(row["path"])
            assert digest(p) == row["sha256"], p
            z.write(p, row["archive_member"])
    with zipfile.ZipFile(PACKAGE) as z:
        assert len(z.namelist()) == len(entries)
        for row in entries:
            raw = z.read(row["archive_member"])
            assert len(raw) == row["bytes"]
            assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    record = {
        "version": "v0.13", "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "D160–D171 documents; central D162/D169/D171 retained metadata; seven named FEP studies completed 21–23 September.",
        "model_runs_performed": False, "fits_performed": False, "statistics_recomputed": False,
        "original_scientific_audits_rerun": False,
        "source_files": entries, "source_checks": checks,
        "limitations": [
            "Selected L20 outputs and saved-audit bindings checked; full raw-array indexes were not freshly rehashed or replayed.",
            "FEP inputs/outputs in the selected manifests checked; preserved predecessor lists are not a new recursive audit.",
            "The package preserves selected text, metadata and native result JSON, not a complete executable dependency or trajectory archive.",
            "Earlier E013/P14–P16 availability limits remain unchanged; other new campaign results are outside this selection.",
        ],
        "data": {"path": str(DATA.relative_to(ROOT)), "bytes": DATA.stat().st_size, "sha256": digest(DATA)},
        "archive": {"path": str(PACKAGE.relative_to(ROOT)), "bytes": PACKAGE.stat().st_size, "sha256": digest(PACKAGE), "members_verified": len(entries)},
        "extractor_sha256": digest(Path(__file__)),
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"source_files": len(entries), "declared_hash_checks": len(checks),
                      "all_checks": "match", "data_bytes": DATA.stat().st_size,
                      "package_bytes": PACKAGE.stat().st_size}))


if __name__ == "__main__":
    main()
