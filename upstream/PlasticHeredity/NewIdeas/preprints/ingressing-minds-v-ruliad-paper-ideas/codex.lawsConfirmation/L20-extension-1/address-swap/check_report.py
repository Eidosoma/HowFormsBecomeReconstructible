"""D169 documentation/provenance check; no fits, forecasts or tissue dynamics."""

import argparse
import json
from pathlib import Path
import re
import sys

import numpy as np

from l20_extension1 import address_swap_check as independent
from l20_extension1 import asymmetry_run as source


HERE = Path(__file__).resolve().parent
ROOT = source.ROOT
RUN = "l20_extension1_address_swap_v1_attempt1"
OLD = "l20_extension1_passive_feedback_v1_attempt1"
PINS = {
    "complete": "898fd26329f89d8123abf6561ded22876e258612195d1b748d18e5df79e8dcd2",
    "audit": "f6a78b24b80bb5b1c953b234315e1457dc9cb54ca79da90565dcafafe28505fa",
}


def specs(summary):
    """Every fixed response, contrast, founder and q-pair, including empty pairs."""
    contrasts = summary["contrasts"]
    cell_header = ["Cohort", "Group", "Response", "Y00", "Y01", "Y10", "Y11"]
    contrast_header = ["Cohort", "Group", "Response", "Contrast", "Mean",
                       "95% low", "95% high", "Positive", "Negative", "Zero",
                       "Omit min", "Omit max"]
    cells, effects, founders, support, pair_effects = [], [], [], [], []
    for row in summary["rows"]:
        label = [row[k] for k in ("cohort", "group", "response")]
        cells.append(label + [v for body in row["cell_mean"] for v in body])
        for name in contrasts:
            effect = row["contrasts"][name]
            effects.append(label + [name, effect["mean"],
                           *effect["pointwise_founder_bootstrap_95"],
                           *[effect[k] for k in ("positive", "negative", "numerical_zero",
                                                "omission_minimum", "omission_maximum")]])
        for i, founder in enumerate(summary["ids"][row["cohort"]]):
            founders.append([row["cohort"], founder, row["group"], row["response"],
                             *[v for body in row["founder_cell_mean"][i] for v in body],
                             *[row["contrasts"][k]["founder_values"][i] for k in contrasts]])
    for row in summary["q_pair_rows"]:
        label = [row[k] for k in ("cohort", "group", "q0", "q1")]
        support.append(label + [row["cases"], row["founders"]])
        for i, response in enumerate(summary["responses"]):
            pair_effects.append(label + [response, row["cases"], *row["contrast_means"][i]])
    controls, stages = [], []
    for row in summary["rows"]:
        e = row["contrasts"]
        if row["response"] == "outgoing_own":
            controls.append([row["cohort"], row["group"],
                             e["original_gap"]["mean"], e["swapped_gap"]["mean"],
                             e["address"]["mean"], *e["address"]["pointwise_founder_bootstrap_95"],
                             e["background"]["mean"], *e["background"]["pointwise_founder_bootstrap_95"],
                             e["interaction"]["mean"]])
        if row["group"] == "B_ordinary":
            stages.append([row["cohort"], row["response"],
                           e["original_gap"]["mean"], e["swapped_gap"]["mean"],
                           e["address"]["mean"], *e["address"]["pointwise_founder_bootstrap_95"],
                           e["background"]["mean"], e["interaction"]["mean"]])
    focus = lambda r: r[1:3] == ["B_ordinary", "outgoing_own"]
    return {
        "all-cells": (cell_header, cells),
        "all-contrasts": (contrast_header, effects),
        "all-founders": (["Cohort", "Founder", "Group", "Response", "Y00", "Y01", "Y10", "Y11", *contrasts], founders),
        "all-q-support": (["Cohort", "Group", "q0", "q1", "Cases", "Founders"], support),
        "all-q-effects": (["Cohort", "Group", "q0", "q1", "Response", "Cases", *contrasts], pair_effects),
        "result-b-cells": (cell_header, [r for r in cells if focus(r)]),
        "result-b-contrasts": (contrast_header, [r for r in effects if focus(r)]),
        "result-own-controls": (["Cohort", "Group", "Original gap", "Swapped gap", "Address",
                                  "Address low", "Address high", "Background", "Background low",
                                  "Background high", "Interaction"], controls),
        "result-b-stages": (["Cohort", "Response", "Original gap", "Swapped gap", "Address",
                              "Address low", "Address high", "Background", "Interaction"], stages),
    }


def evidence():
    """Rehash the existing closure and recheck arithmetic, not simulation physics."""
    run, out = ROOT / "runs" / RUN, ROOT / "outputs" / RUN
    paths = {"complete": run / "COMPLETE.json",
             "audit": ROOT / "logs" / f"{RUN}_saved_audit_v1.json"}
    assert {k: source.sha256_file(v) for k, v in paths.items()} == PINS
    done, audit = [source.io.read_json(paths[k]) for k in ("complete", "audit")]
    manifest = source.io.read_json(run / "MANIFEST.json")
    freeze_path = ROOT / "tmp" / f"{RUN}_freeze.json"
    bench_path = ROOT / "tmp" / f"{RUN}_benchmark.json"
    freeze, bench = [source.io.read_json(p) for p in (freeze_path, bench_path)]
    assert done["status"] == "COMPLETE" and audit["passes"]
    assert audit["complete_sha256"] == PINS["complete"]
    assert done["manifest_sha256"] == source.sha256_file(run / "MANIFEST.json")
    assert done["freeze_sha256"] == audit["freeze_sha256"] == manifest["freeze_sha256"]
    assert bench["freeze_sha256"] == done["freeze_sha256"] == source.sha256_file(freeze_path)
    assert manifest["timing_sha256"] == source.sha256_file(bench_path)
    inputs = {**freeze["input_sha256"], **source.io.hashes([freeze_path, bench_path]),
              **bench["artifact_sha256"]}
    assert manifest["input_sha256"] == inputs and len(freeze["input_sha256"]) == 327
    assert len(inputs) == audit["inputs"] == 333
    source.check_hashes(inputs)
    source.check_hashes(done["output_sha256"])
    assert {str(p) for p in out.iterdir()} == set(done["output_sha256"])
    assert len(done["output_sha256"]) == audit["outputs"] == 163
    assert sum(Path(p).stat().st_size for p in done["output_sha256"]) == done["output_bytes"]
    assert audit["full_physics_replayed"] and audit["all_cases_retained"]
    assert not audit["actual_lineage_outcomes_used"] and not done["actual_lineage_outcomes_used"]
    summary = source.io.read_json(out / "summary.json")
    packed = source.io.load_npz(out / "responses.npz")
    ids = {"development": list(range(90000, 90016)), "pilot": list(range(100000, 100064))}
    assert set(packed) == {co + "_" + k for co in ids for k in ("response", "q")}
    panels = {co: {k: packed[co + "_" + k] for k in ("response", "q")} for co in ids}
    proof = source.io.read_json(out / "verification.json")
    assert independent.check_summary(summary, panels, ids) == proof["summary"] == audit["summary"]
    assert len(proof["blocks"]) == 80 and proof["original_paths_reproduced"] == 2560
    assert proof["aligned_swap_aliases"] == 1280
    for row in proof["blocks"]:
        assert row["passes"] and row["full_physics_replayed"]
        assert row["writer_max_abs"] == row["reader_max_abs"] == 0
    old_path = ROOT / "outputs" / OLD / "geometry.npz"
    assert str(old_path) in inputs
    old = source.io.load_npz(old_path)
    values = 0
    for co in ids:
        for copy in range(2):
            diagonal = panels[co]["response"][:, :, :, copy, copy]
            np.testing.assert_allclose(diagonal, old[co + "_response"][:, :, :, copy], atol=2e-10, rtol=0)
            values += diagonal.size
        np.testing.assert_array_equal(panels[co]["q"], old[co + "_q"][..., 0])
    assert values == proof["bridge"]["original_values"] == 17920
    return summary


def check_markdown(body, tables):
    observed = {}
    pattern = r"<!-- d169-table:([a-z-]+) -->\n(.*?)\n<!-- d169-end -->"
    for key, block in re.findall(pattern, body, re.S):
        assert key not in observed and key in tables, key
        header, expected = tables[key]
        rows = [[v.strip() for v in line.strip()[1:-1].split("|")]
                for line in block.splitlines() if line.startswith("|")]
        assert rows[0] == header and len(rows) == len(expected) + 2, key
        assert len(rows[1]) == len(header) and all(re.fullmatch(r":?-{3,}:?", s) for s in rows[1])
        for got, want in zip(rows[2:], expected):
            assert len(got) == len(want), key
            for text, value in zip(got, want):
                if value is None:
                    assert text == "undefined", (key, text, value)
                elif isinstance(value, str):
                    assert text == value, (key, text, value)
                else:
                    assert np.isfinite(float(text)) and abs(float(text) - value) <= 5.1e-10, (key, text, value)
        observed[key] = len(expected)
    assert body.count("<!-- d169-table:") == len(observed)
    assert body.count("<!-- d169-end -->") == len(observed)
    return observed


def main():
    assert not sys.flags.optimize, "assertions required"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specs", action="store_true")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    assert not (args.specs and args.write_receipt)
    summary = evidence()
    tables = specs(summary)
    if args.specs:
        print(json.dumps(tables))
        return
    probe = {"probe": (["Label", "Value", "Missing"], [["test", 0.125, None]])}
    good = ("<!-- d169-table:probe -->\n| Label | Value | Missing |\n"
            "| --- | --- | --- |\n| test | 0.125000000 | undefined |\n<!-- d169-end -->")
    assert check_markdown(good, probe) == {"probe": 1}
    malformed = [good.replace("0.125000000", "0.125000010"),
                 good.replace("0.125000000", "nan"), good.replace("undefined", "0"),
                 good.replace("| test |", "| wrong |"), good.replace("| Label |", "| Wrong |"),
                 good + good, good.replace("<!-- d169-end -->", "")]
    for bad in malformed:
        try:
            check_markdown(bad, probe)
        except AssertionError:
            pass
        else:
            raise AssertionError("malformed synthetic table accepted")
    observed, links = {}, 0
    for name in ("RESULTS.md", "TABLES.md"):
        body = (HERE / name).read_text()
        rows = check_markdown(body, tables)
        assert not set(observed).intersection(rows)
        observed.update(rows)
        for target in re.findall(r"\]\(([^)]+)\)", body):
            assert not target.startswith(("http:", "https:", "file:"))
            assert (HERE / target.split("#")[0]).is_file(), target
            links += 1
    assert set(observed) == set(tables) and sum(observed.values()) == 6118
    report = dict(passes=True, checked_utc=source.utc_now(), tables=len(observed),
                  numeric_rows=sum(observed.values()), rows_by_table=observed, local_links=links,
                  complete_sha256=PINS["complete"], audit_sha256=PINS["audit"],
                  documentation_sha256=source.io.hashes([HERE / k for k in ("RESULTS.md", "TABLES.md", "check_report.py")]),
                  inputs=333, outputs=163, original_values=17920,
                  synthetic_transcription_checks=1 + len(malformed),
                  independent_summary_arithmetic=True, new_fits=0, new_forecasts=0,
                  actual_lineage_outcomes_used=False, new_dynamics=0, automatic_successor=False)
    if args.write_receipt:
        source.io.write_json(ROOT / "logs" / f"{RUN}_documentation_v1.json", report, ROOT)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
