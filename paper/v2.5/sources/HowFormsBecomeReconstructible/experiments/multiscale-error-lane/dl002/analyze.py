"""DL002's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m dl002.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. Contrasts are paired
within block (same cases and noise), with 95% t intervals over blocks.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from dl002 import design as D  # noqa: E402

SNAP_EPS = ("sign", "patch", "shift", "spacing")


def load(root, blocks):
    data = {}
    for p, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / p / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(p, u)] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}      # block means over cases
    return data


def levels(data):
    """levels[panel][unit][body][record][endpoint@t] = [mean over blocks, SD over blocks]."""
    out = {}
    for (p, u), arrs in data.items():
        recs = [r.name for r in D.PANELS[p]["records"]]
        snaps = D.PANELS[p]["snaps"]
        for b in D.BODIES:
            node = out.setdefault(p, {}).setdefault(u, {}).setdefault(b, {})
            for ep in SNAP_EPS:
                x = arrs[f"{b}/{ep}"]
                for si, t in enumerate(snaps):
                    for ri, rec in enumerate(recs):
                        v = x[:, si, ri]
                        node.setdefault(rec, {})[f"{ep}@{t}"] = [round(float(v.mean()), 4), round(float(v.std(ddof=1)), 4) if len(v) > 1 else None]
            for ep in ("w_corr", "qual"):
                x = arrs[f"{b}/{ep}"]
                for ri, rec in enumerate(recs):
                    v = x[:, ri]
                    node[rec][ep] = [round(float(v.mean()), 6), round(float(v.std(ddof=1)), 6) if len(v) > 1 else None]
            for ep in ("r_sign", "r_patch"):
                x = arrs[f"{b}/{ep}"]
                for si, t in enumerate(snaps):
                    v = x[:, si]
                    node["rel"][f"{ep}@{t}"] = [round(float(v.mean()), 4), round(float(v.std(ddof=1)), 4) if len(v) > 1 else None]
    return out


def lv(L, p, u, b, rec, ep):
    return L[p][u][b][rec][ep][0]


def score(L):
    S = {}
    A = lambda pat, th, b, rec, ep="sign@4000": lv(L, "A", D.unit_name(pat, th), b, rec, ep)
    v = {f"{pat}/t{th:g}/{b}": A(pat, th, b, "rel") for pat in ("S4", "LB") for th in D.THETAS for b in D.BODIES}
    S["H1"] = {"verdict": "HOLDS" if min(v.values()) >= 0.94 else "FAILS", "rel_sign@4000": v}

    v = {f"{pat}/t{th:g}": round(A(pat, th, "li4", "rel") - A(pat, th, "dw", "rel"), 4) for pat in ("S4", "LB") for th in D.THETAS}
    S["H2"] = {"verdict": "HOLDS" if max(abs(x) for x in v.values()) <= 0.02 else "FAILS", "li4_minus_dw_rel": v}

    v = {f"t{th:g}": round(A("LB", th, "li4", "none") - A("LB", th, "dw", "none"), 4) for th in D.THETAS}
    S["H3"] = {"verdict": "HOLDS" if v["t0"] >= 0.15 and v["t1"] <= 0.05 else "FAILS", "LB_li4_minus_dw_none": v}

    gap = {f"{pat}/t{th:g}/{b}": round(A(pat, th, b, "rel") - A(pat, th, b, "a16"), 4)
           for pat in ("S4", "LB") for th in (0.5, 1.0) for b in D.BODIES}
    fa = {b: round(A("S4", 1.0, b, "full") - A("S4", 1.0, b, "a4"), 4) for b in D.BODIES}
    S["H4"] = {"verdict": "HOLDS" if min(gap.values()) >= 0.10 and min(fa.values()) >= 0.05 else "FAILS",
               "rel_minus_a16": gap, "S4_t1_full_minus_a4": fa}

    R = lambda w, b, rec: lv(L, "R", D.unit_name("S4", 1.0, w), b, rec, "patch@4000")
    v = {f"{w}/{b}/{rec}": R(w, b, rec) for w in ("flip", "reset") for b in D.BODIES for rec in ("rel", "a4", "full")}
    ok = all(v[f"{w}/{b}/rel"] >= 0.95 and v[f"{w}/{b}/a4"] <= 0.80 and v[f"{w}/{b}/full"] >= 0.90
             for w in ("flip", "reset") for b in D.BODIES)
    S["H5"] = {"verdict": "HOLDS" if ok else "FAILS", "S4_t1_patch@4000": v}

    v = {f"t{th:g}/{b}": A("F0", th, b, "rel") for th in (0.0, 1.0) for b in D.BODIES}
    ok = v["t0/li4"] <= 0.85 and v["t1/li4"] <= 0.85 and v["t0/dw"] >= 0.95 and v["t1/dw"] >= 0.95
    S["H6"] = {"verdict": "HOLDS" if ok else "FAILS", "F0_rel_sign@4000": v}

    v = {pat: round(A(pat, 0.25, "li4", "a16") - A(pat, 0.25, "dw", "a16"), 4) for pat in ("S4", "LB")}
    S["H7"] = {"verdict": "HOLDS" if v["LB"] >= 0.10 and v["S4"] >= 0.02 else "FAILS", "t0.25_a16_li4_minus_dw": v}
    return S


def contrasts(data, out):
    rows = []
    for (p, u), arrs in data.items():
        recs = [r.name for r in D.PANELS[p]["records"]]
        snaps = D.PANELS[p]["snaps"]
        ep = "patch" if p == "R" else "sign"
        pairs = [("li4", rec, "dw", rec) for rec in recs] + [(b, "rel", b, "a16") for b in D.BODIES if "a16" in recs] \
            + [(b, "rel", b, "full") for b in D.BODIES] + [(b, "full", b, "a4") for b in D.BODIES]
        for b1, r1, b2, r2 in pairs:
            d = arrs[f"{b1}/{ep}"][:, :, recs.index(r1)] - arrs[f"{b2}/{ep}"][:, :, recs.index(r2)]
            for si, t in enumerate(snaps):
                v = d[:, si]
                n = len(v)
                half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
                rows.append([p, u, f"{b1}/{r1}-{b2}/{r2}", ep, t, round(float(v.mean()), 4), round(float(v.mean()) - half, 4),
                             round(float(v.mean()) + half, 4), int((v > 0).sum()), int((v < 0).sum()), n])
    with open(out / "contrasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["panel", "unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"])
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "dl002")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "levels": L, "statements": S}
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
