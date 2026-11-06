"""Reader: python -m lr001.analyze --root RUN_ROOT --stage {preflight,development} --out OUT_DIR [--blocks LO,HI]

Units are source blocks: an endpoint is averaged over the block's 8 cases (cases without the scored sites, such as
region-minority cells in F0, are left out) and summarised over block means. Contrasts are paired within case, with
95% t intervals over blocks, positive = the first arm better (E: bond_ok = 1 - bond_err and record sign; C: kept;
T: minority agreement). Compact outputs to OUT_DIR (git): summary.json, predictions_scored.json, three contrast files.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from scipy.stats import t as student  # noqa: E402

from lr001 import design as D  # noqa: E402
from lr001.scoring import score  # noqa: E402

warnings.filterwarnings("ignore", message="Mean of empty slice")
SHORT = {"BENEFIT": "B", "HARM": "H", "NO MEANINGFUL DIFFERENCE": "=", "UNDECIDED": "?"}
READS = {"A": D.A_READS, "E": D.E_READS, "C": D.C_READS, "T": D.T_READS, "L": D.L_READS}
ENDPOINTS = {"E": ("sign", "bond_err", "minority", "majority"), "C": ("kept", "kept_min", "kept_maj", "sign", "minority", "majority"),
             "T": ("sign", "minority", "majority", "bond_err"), "L": ("record_kept", "body_kept", "record_sign", "body_sign", "bond_err")}


def load(root, panel, unit, blocks):
    per = [dict(np.load(root / "shards" / panel / unit / f"{b}.npz")) for b in blocks]
    keys = set(per[0]) - {"__meta__"}
    return {k: np.stack([p[k] for p in per]) for k in keys}          # leading axis: blocks


def block_mean(x):
    """x: (blocks, cases) -> mean over blocks of the per-block case means (NaN cases and NaN blocks left out)."""
    b = np.nanmean(x, axis=-1)
    return None if not np.isfinite(b).any() else float(np.nanmean(b))


def levels(data):
    out = {}
    for panel, units in data.items():
        for unit, d in units.items():
            row = {}
            if panel == "A":
                for s in D.A_SIGMAS:
                    x = d[f"s{s:g}/bond_accuracy"]                      # (blocks, reads, cases)
                    row[f"s{s:g}"] = {f"bond_accuracy@{t}": round(block_mean(x[:, i]), 4) for i, t in enumerate(D.A_READS)}
            else:
                for bi, br in enumerate(D.branches(panel)):
                    row[br] = {}
                    for ep in ENDPOINTS[panel]:
                        for ri, t in enumerate(READS[panel]):
                            m = block_mean(d[ep][:, ri, bi])
                            row[br][f"{ep}@{t}"] = None if m is None else round(m, 4)
            out.setdefault(panel, {})[unit] = row
    return out


def reading(lo, hi):
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "UNDECIDED"
    if lo > 0:
        return "BENEFIT"
    if hi < 0:
        return "HARM"
    if lo >= -D.MARGIN and hi <= D.MARGIN:
        return "NO MEANINGFUL DIFFERENCE"
    return "UNDECIDED"


def summarize(d):
    """d: (blocks, cases) paired differences (NaN where a case lacks the sites) -> one row."""
    b = np.nanmean(d, axis=1)
    b = b[np.isfinite(b)]
    nb = len(b)
    if nb == 0:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"), "blocks_pos": 0, "blocks_neg": 0,
                "reading": "UNDECIDED"}
    point = float(b.mean())
    half = float(student.ppf(0.975, nb - 1) * b.std(ddof=1) / np.sqrt(nb)) if nb > 1 else float("nan")
    return {"point": point, "lo": point - half, "hi": point + half, "blocks_pos": int((b > 0).sum()),
            "blocks_neg": int((b < 0).sum()), "reading": reading(point - half, point + half)}


def contrasts(data):
    rows = []
    for panel, a, b in D.CONTRASTS:
        brs = D.branches(panel)
        for unit, d in data[panel].items():
            if panel == "C":
                for c in D.C_CONDS:
                    if c.wound == "sham":
                        continue
                    ia, ib = brs.index(f"{a}/{c.name}"), brs.index(f"{b}/{c.name}")
                    for ep in ("kept", "kept_min"):
                        x = d[ep][:, D.C_READS.index(4000)]
                        rows.append({"panel": panel, "arm": a, "ref": b, "unit": unit, "context": c.name, "endpoint": f"{ep}@4000",
                                     **summarize(x[:, ia] - x[:, ib])})
            elif panel == "E":
                for rate in D.E_RATES:
                    ia, ib = brs.index(f"{rate:g}/{a}"), brs.index(f"{rate:g}/{b}")
                    ri = D.E_READS.index(8000)
                    ok = 1.0 - d["bond_err"][:, ri]
                    rows.append({"panel": panel, "arm": a, "ref": b, "unit": unit, "context": f"{rate:g}", "endpoint": "bond_ok@8000",
                                 **summarize(ok[:, ia] - ok[:, ib])})
                    x = d["sign"][:, ri]
                    rows.append({"panel": panel, "arm": a, "ref": b, "unit": unit, "context": f"{rate:g}", "endpoint": "sign@8000",
                                 **summarize(x[:, ia] - x[:, ib])})
            else:
                for rate in sorted({r for r, _ in D.T_BRANCHES if r > 0}):
                    ia, ib = brs.index(f"{rate:g}/{a}"), brs.index(f"{rate:g}/{b}")
                    x = d["minority"][:, D.T_READS.index(8000)]
                    rows.append({"panel": panel, "arm": a, "ref": b, "unit": unit, "context": f"{rate:g}", "endpoint": "minority@8000",
                                 **summarize(x[:, ia] - x[:, ib])})
    return rows


def write_csv(path, rows):
    cols = ["panel", "arm", "ref", "unit", "context", "endpoint", "point", "lo", "hi", "blocks_pos", "blocks_neg", "reading"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] if c not in ("point", "lo", "hi", "reading") else (f"{r[c]:.4f}" if c != "reading" else SHORT[r[c]])
                        for c in cols])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    root = a.root.resolve()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    a.out.mkdir(parents=True, exist_ok=True)
    data = {p: {u: load(root, p, u, blocks) for u in D.PANELS[p]["units"]} for p in D.PANELS}
    lev = levels(data)
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "levels": lev,
               "flip_rate": {u: {br: round(float(data["E"][u]["flip_rate"][:, i].mean()), 6) for i, br in enumerate(D.branches("E"))}
                             for u in D.E_UNITS},
               "turnovers_per_case": {u: {br: round(float(data["T"][u]["turnovers"][:, i].mean()), 1)
                                          for i, br in enumerate(D.branches("T"))} for u in D.T_UNITS}}
    rows = contrasts(data)
    for p in ("C", "E", "T"):
        write_csv(a.out / f"contrasts_{p}.csv", [r for r in rows if r["panel"] == p])
    summary["statements"] = score(lev)
    (a.out / "predictions_scored.json").write_text(json.dumps(summary["statements"], indent=1) + "\n")
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":"), default=float) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in summary["statements"].items()}, indent=1))


if __name__ == "__main__":
    main()
