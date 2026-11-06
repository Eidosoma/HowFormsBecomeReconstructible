"""NL003's tables: python -m nl003.tables --root RUN_ROOT --stage {probe,preflight,debug,development} [--out DIR]

Writes TABLES.md: the registered parts (value, 95% interval, SD_block, threshold, verdict), and the reported levels at the
last read for every arm and event in both units (record: ev, spec, k_spec, align_A, min_reg; the arbiter's refused
shares; the recipients' spec), each the mean over the blocks of the block means.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import warnings

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from nl003 import analyze as AN, design as D  # noqa: E402
from nl003.predict import score  # noqa: E402


def lv(data, u, key, br, read=-1):
    names = data[u]["_names"][key[:2]]
    if br not in names:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return float(np.mean(np.nanmean(data[u][key][:, read, names.index(br), :], axis=1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("probe", "preflight", "debug", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "nl003")
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage)
    data = AN.load(a.root.resolve(), blocks)
    S = score(data)
    out = [f"# NL003 tables ({a.stage}, blocks {blocks[0]}-{blocks[-1]}, {len(blocks)} blocks; rule {D.RULE})", "",
           "## Registered parts", "", "| Statement | Part | Value [95%] | SD_block | Rule | Verdict |", "|---|---|---|---|---|---|"]
    for sid, node in S.items():
        for name, p in node["parts"].items():
            th = "unset" if p["threshold"] is None else f"{p['sense']} {p['threshold']:+}"
            out.append(f"| {sid} | {name} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | {p['sd']:.4f} | {th} | {node['verdict']} |")
    for u in D.UNITS:
        out += ["", f"## Levels at the last read, unit {u}", "",
                "| Branch | ev | spec | k_spec | align_A | min_reg | refused (all, differing, other) | s/spec | c/spec | g/spec |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for br in data[u]["_names"]["t/"]:
            f = lambda key, b=br: lv(data, u, key, b)
            ref = "" if "+" not in br else f"{f('t/a/ref_all'):.3f}, {f('t/a/ref_dreg'):.3f}, {f('t/a/ref_other'):.3f}"
            g = f"{lv(data, u, 'g/spec_reg', br):+.3f}" if br in data[u]["_names"]["g/"] else ""
            out.append(f"| {br} | {f('t/r/ev_reg_ok'):.3f} | {f('t/r/spec_reg'):+.3f} | {f('t/r/k_spec_reg'):+.3f} | "
                       f"{f('t/r/align_A'):.3f} | {f('t/r/min_reg_ok_A'):.3f} | {ref} | {f('s/spec_reg'):+.3f} | {f('c/spec_reg'):+.3f} | {g} |")
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "TABLES.md").write_text("\n".join(out) + "\n")
    print("wrote", a.out / "TABLES.md")


if __name__ == "__main__":
    main()
