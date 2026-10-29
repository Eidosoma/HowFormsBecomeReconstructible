"""Reader: python -m gw001.analyze --root RUN_ROOT --stage {preflight,development} --out OUT_DIR [--blocks LO,HI]

Units are source blocks: an endpoint is paired within case, averaged over the block's 8 cases and summarised
over block means with a 95% t interval, as BR001 and BR002. Panel R endpoints: kept at t = 2000, 4000, 8000
(sign agreement inside the patch), t95 (first snapshot at which kept >= 0.95, a median over cases; inf if never),
committed kept and undecided sites at 8000, and the undamaged record's agreement (sham) at each read. Compact
tables to OUT_DIR (git), full tables to RUN_ROOT/analysis.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from scipy.stats import t as student  # noqa: E402

from gw001 import design as D  # noqa: E402
from gw001 import sim  # noqa: E402
from gw001.scoring import score  # noqa: E402

SHORT = {"BENEFIT": "B", "HARM": "H", "NO MEANINGFUL DIFFERENCE": "=", "UNDECIDED": "?"}
SNAP = {t: t // D.EVERY_R - 1 for t in D.READS_R}
B_ENDPOINTS = ("v_qual", "v_out", "les_v", "les_r", "r_sign")


def load(root, panel, unit, blocks):
    per = [dict(np.load(root / "shards" / panel / unit / f"{b}.npz")) for b in blocks]
    keys = set(per[0]) - {"__meta__"}
    return {k: np.stack([p[k] for p in per]) for k in keys}          # leading axis: blocks


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
    """d: (blocks, cases) paired differences -> one row."""
    b = d.mean(1)
    nb = len(b)
    point = float(b.mean())
    half = float(student.ppf(0.975, nb - 1) * b.std(ddof=1) / np.sqrt(nb)) if nb > 1 else float("nan")
    return {"point": point, "lo": point - half, "hi": point + half, "blocks_pos": int((b > 0).sum()),
            "blocks_neg": int((b < 0).sum()), "reading": reading(point - half, point + half)}


def r_endpoints(dr, arm):
    """Per-branch panel R endpoints, each (blocks, conditions, cases)."""
    curve = dr[f"{arm}/kept_curve"]                                   # (blocks, snap, cond, cases)
    rs = dr[f"{arm}/rsign_curve"]
    out = {f"kept@{t}": curve[:, i] for t, i in SNAP.items()}
    out.update({f"rsign@{t}": rs[:, i] for t, i in SNAP.items()})
    out["t95"] = np.stack([sim.t95(curve[b], D.EVERY_R) for b in range(curve.shape[0])])
    out["committed@8000"] = dr[f"{arm}/committed"]
    out["undecided@8000"] = dr[f"{arm}/undecided"]
    return out


def levels_R(data):
    out = {}
    for unit, dr in data.items():
        conds = [c.name for c in D.GEOMETRIES[unit]]
        for a in D.ARMS_R:
            ep = r_endpoints(dr, a.name)
            row = {}
            for ci, c in enumerate(conds):
                if c == "sham":
                    row[c] = {k: round(float(ep[k][:, ci].mean()), 4) for k in ep if k.startswith("rsign")}
                    row[c]["rsign@2000_block_sd"] = round(float(ep["rsign@2000"][:, ci].mean(1).std(ddof=1)), 4)
                    par = ep["rsign@2000"][:, ci].reshape(-1, len(D.MESSAGES), len(D.PARENTS))
                    row[c]["rsign@2000_parent_sd"] = round(float(np.sqrt((par.var(axis=2, ddof=1)).mean())), 4)
                else:
                    row[c] = {k: round(float(ep[k][:, ci].mean()), 4) for k in ep if k.startswith(("kept", "committed", "undecided"))}
                    t = ep["t95"][:, ci]
                    row[c]["t95_median"] = float(np.median(t))
                    row[c]["t95_censored"] = round(float(np.isinf(t).mean()), 4)
            out.setdefault(unit, {})[a.name] = row
    return out


def levels_B(data):
    out = {}
    for unit, dr in data.items():
        conds = [c.name for c in D.COND_B]
        for a in D.ARMS_B:
            out.setdefault(unit, {})[a.name] = {ep: {c: round(float(dr[f"{a.name}/{ep}"][:, ci].mean()), 4)
                                                      for ci, c in enumerate(conds)} for ep in B_ENDPOINTS}
    return out


def contrasts(panel, data, endpoint):
    rows = []
    for p, a, b in D.CONTRASTS:
        if p != panel:
            continue
        for unit, dr in data.items():
            conds = [c.name for c in D.conditions(panel, unit)]
            if panel == "R":
                x, y = r_endpoints(dr, a)[endpoint], r_endpoints(dr, b)[endpoint]
            else:
                x, y = dr[f"{a}/{endpoint}"], dr[f"{b}/{endpoint}"]
            for ci, c in enumerate(conds):
                if panel == "R" and (c == "sham") != endpoint.startswith("rsign"):
                    continue
                rows.append({"panel": panel, "arm": a, "ref": b, "unit": unit, "condition": c, "endpoint": endpoint,
                             **summarize(x[:, ci] - y[:, ci])})
    return rows


def write_csv(path, rows):
    cols = ["panel", "arm", "ref", "unit", "condition", "endpoint", "point", "lo", "hi", "blocks_pos", "blocks_neg", "reading"]
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
    full = root / "analysis"
    full.mkdir(exist_ok=True)
    data = {p: {u: load(root, p, u, blocks) for u in D.PANELS[p]["units"]} for p in D.PANELS}
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(),
               "panels": {"R": {"levels": levels_R(data["R"])}, "B": {"levels": levels_B(data["B"])}}}
    for ep in ("kept@2000", "kept@8000"):
        write_csv(a.out / f"contrasts_R_{ep.replace('@', '')}.csv", contrasts("R", data["R"], ep))
    write_csv(a.out / "contrasts_B.csv", [row for ep in B_ENDPOINTS for row in contrasts("B", data["B"], ep)])
    write_csv(full / "contrasts_R_all.csv", [row for ep in (*[f"kept@{t}" for t in D.READS_R], "committed@8000", "rsign@2000",
                                                             "rsign@8000") for row in contrasts("R", data["R"], ep)])
    summary["statements"] = score(data, summary)
    (a.out / "predictions_scored.json").write_text(json.dumps(summary["statements"], indent=1) + "\n")
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":"), default=float) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in summary["statements"].items()}, indent=1))


if __name__ == "__main__":
    main()
