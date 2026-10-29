#!/usr/bin/env python3
"""Transpose retained E046 report counts; no raw fields or new simulations."""

import hashlib
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    prior = json.loads((ROOT / "paper_assets/data/functional-renewal-history-v1.json").read_text())
    archive = ROOT / prior["source_archive"]
    member = prior["source_archive_member"]
    with zipfile.ZipFile(archive) as saved:
        report = saved.read(member)
        complete = json.loads(saved.read(str(Path(member).with_name("COMPLETE.json"))))
    report_hash = hashlib.sha256(report).hexdigest()
    assert report_hash == prior["source_report_sha256"]
    assert report_hash == complete["outputs_sha256"]["REPORT.md"]
    groups = {
        name: (int(total), int(ever))
        for name, total, ever in re.findall(
            r"^\| (all|terminal_success|terminal_failure) \| (\d+) \| (\d+) \|",
            report.decode(), re.MULTILINE,
        )
    }
    assert set(groups) == {"all", "terminal_success", "terminal_failure"}
    total, ever = groups["all"]
    success, success_ever = groups["terminal_success"]
    failure, failure_ever = groups["terminal_failure"]
    assert (total, ever, success) == (
        prior["lineages"], prior["ever_body_failure"], prior["terminal_success_lineages"]
    )
    assert success + failure == total
    assert success_ever + failure_ever == ever
    assert all(0 <= e <= n for n, e in groups.values())
    rows = [
        {"history": "All 32 recorded body readouts pass", "terminal_success": success - success_ever,
         "terminal_failure": failure - failure_ever, "total": total - ever},
        {"history": "At least one recorded body readout fails", "terminal_success": success_ever,
         "terminal_failure": failure_ever, "total": ever},
    ]
    for row in rows:
        assert row["terminal_success"] + row["terminal_failure"] == row["total"]
        row["terminal_success_percent"] = 100 * row["terminal_success"] / row["total"]
    output = {
        "version": "v0.18", "source_archive": prior["source_archive"],
        "source_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "source_archive_member": member, "source_report_sha256": report_hash,
        "source_completion_report_hash_verified": True,
        "derivation": "Transpose the first report table; always-passing cells are group total minus ever-failed.",
        "independent_blocks": prior["independent_blocks"], "rows": rows,
        "totals": {"terminal_success": success, "terminal_failure": failure, "lineages": total},
        "endpoint": "Fresh-recipient terminal assay after additional injury; separate from all 32 saved rebuilding-body readouts.",
        "scope": "Descriptive same-cohort cross-tabulation; no individual-record repeated-future capacity estimate.",
        "model_runs": False, "raw_array_recount": False, "new_intervals": False,
    }
    dest = ROOT / "paper_assets/data/functional-history-crosstab-v0.18.json"
    dest.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"output": str(dest.relative_to(ROOT)), "rows": rows, "totals": output["totals"]}, indent=2))


if __name__ == "__main__":
    main()
