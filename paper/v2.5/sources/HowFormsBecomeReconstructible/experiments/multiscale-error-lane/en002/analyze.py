"""EN002's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m en002.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. Contrasts are paired
within block, with 95% t intervals over blocks: bodies against the double well under the same condition
(contrasts_bodies.csv), and each starved budget against the full budget within a body and record
(contrasts_budgets.csv).
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

from en002 import design as D  # noqa: E402

SNAP_EPS = ("sign", "shift", "spacing", "patch")
FINAL_EPS = ("w_drift", "w_corr")


def load(root, blocks):
    data = {}
    for p, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / p / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(p, u)] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}     # block means over cases
    return data


def levels(data):
    """levels[panel][unit][body][cond][endpoint@t] = [mean over blocks, SD over blocks]."""
    out = {}
    for (p, u), arrs in data.items():
        conds = [c.name for c in D.PANELS[p]["conds"]]
        snaps = D.PANELS[p]["snaps"]
        for body in D.BODIES:
            for ep in SNAP_EPS:
                x = arrs.get(f"{body}/{ep}")
                if x is None:
                    continue
                for si, t in enumerate(snaps):
                    for ci, c in enumerate(conds):
                        v = x[:, si, ci]
                        out.setdefault(p, {}).setdefault(u, {}).setdefault(body, {}).setdefault(c, {})[f"{ep}@{t}"] = \
                            [round(float(v.mean()), 4), round(float(v.std(ddof=1)), 4) if len(v) > 1 else None]
            for ep in FINAL_EPS:
                x = arrs[f"{body}/{ep}"]
                for ci, c in enumerate(conds):
                    v = x[:, ci]
                    out[p][u][body][c][ep] = [round(float(v.mean()), 6), round(float(v.std(ddof=1)), 6) if len(v) > 1 else None]
    return out


def lv(L, p, u, body, c, ep):
    return L[p][u][body][c][ep][0]


def score(L):
    S = {}
    g = lambda u, b, c, ep: lv(L, "G", u, b, c, ep)
    w = lambda u, b, c, ep: lv(L, "W", u, b, c, ep)
    bodies = tuple(D.BODIES)

    v = {b: {"B0.1": g("S4_t0", b, "B0.1/none", "sign@2000"), "C0.1": g("S4_t0", b, "C0.1/none", "sign@2000")} for b in bodies}
    S["E1"] = {"verdict": "HOLDS" if all(v[b]["B0.1"] <= 0.60 and v[b]["C0.1"] >= 0.95 for b in bodies) else "FAILS",
               "sign@2000": v}

    sp = {b: {bb: g("S4_t0", b, f"{bb}/none", "spacing@3000") for bb in ("B0.5", "B0.25", "B0.1")} for b in bodies}
    sg = {b: g("S4_t0", b, "B0.1/none", "sign@3000") for b in ("li2", "li4")}
    ok = all(7.0 <= sp[b][bb] <= 9.0 for b in ("li2", "li4") for bb in sp[b]) and all(sp["dw"][bb] >= 10 for bb in sp["dw"])
    ok = ok and all(x <= 0.60 for x in sg.values())
    S["E2"] = {"verdict": "HOLDS" if ok else "FAILS", "spacing@3000": sp, "li_sign@3000_B0.1": sg}

    v = {b: (g("S4_t0", b, "B0.5/none", "sign@2000"), g("S4_t0", b, "B0.5/none", "sign@3000")) for b in bodies}
    ok = (v["li4"][1] >= 0.95 and v["li4"][1] > v["li4"][0] and v["li2"][1] >= 0.90 and v["li2"][1] > v["li2"][0]
          and v["dw"][1] <= 0.85 and v["dw"][1] <= v["dw"][0] + 0.02)
    S["E3"] = {"verdict": "HOLDS" if ok else "FAILS", "sign@2000_and_@3000_B0.5": v}

    diffs = {u: {b: round(g(u, b, "B0.1/held", "sign@3000") - g(u, b, "base/held", "sign@3000"), 4) for b in bodies}
             for u in D.PANELS["G"]["units"]}
    S["E4"] = {"verdict": "HOLDS" if all(abs(x) <= 0.02 for d in diffs.values() for x in d.values()) else "FAILS",
               "held_B0.1_minus_base_sign@3000": diffs}

    r = {"reset_base@500": w("S4_t0", "li4", "base/none/reset8", "patch@500"),
         "reset_C0.1@500": w("S4_t0", "li4", "C0.1/none/reset8", "patch@500"),
         "reset_C0.1@3000": w("S4_t0", "li4", "C0.1/none/reset8", "patch@3000"),
         "flip_base@2000": w("S4_t0", "li4", "base/none/flip8", "patch@2000"),
         "flip_C0.1@2000": w("S4_t0", "li4", "C0.1/none/flip8", "patch@2000"),
         "flip_C0.1@3000": w("S4_t0", "li4", "C0.1/none/flip8", "patch@3000")}
    ok = (r["reset_C0.1@500"] <= r["reset_base@500"] - 0.10 and r["flip_C0.1@2000"] <= 0.70 and r["flip_base@2000"] >= 0.90
          and r["reset_C0.1@3000"] >= 0.95 and r["flip_C0.1@3000"] >= 0.80)
    S["E5"] = {"verdict": "HOLDS" if ok else "FAILS", "li4_patch": r}

    r = {f"{wd}/{rec}": w("S4_t0", "li4", f"B0.1/{rec}/{wd}8", "patch@3000") for wd in ("reset", "flip") for rec in ("none", "held")}
    ok = all(r[f"{wd}/none"] <= 0.60 and r[f"{wd}/held"] >= 0.98 for wd in ("reset", "flip"))
    S["E6"] = {"verdict": "HOLDS" if ok else "FAILS", "li4_patch@3000_B0.1": r}

    v = {b: g("S4_t0", b, "B0.1/held", "sign@2000") for b in bodies}
    S["E7"] = {"verdict": "HOLDS" if v["dw"] - v["li2"] >= 0.02 and v["dw"] - v["li4"] >= 0.02 else "FAILS",
               "held_B0.1_sign@2000": v}

    v = {"dw_F0@2000": g("F0_t0", "dw", "B0.1/none", "sign@2000"), "dw_F0@3000": g("F0_t0", "dw", "B0.1/none", "sign@3000"),
         "li4_S4@2000": g("S4_t0", "li4", "B0.1/none", "sign@2000"), "li4_S4@3000": g("S4_t0", "li4", "B0.1/none", "sign@3000")}
    ok = v["dw_F0@2000"] >= 0.70 and v["dw_F0@3000"] >= 0.85 and v["li4_S4@2000"] <= 0.60 and v["li4_S4@3000"] <= 0.60
    S["E8"] = {"verdict": "HOLDS" if ok else "FAILS", "sign_B0.1_no_record": v}
    return S


def _row(d):
    n = len(d)
    half = float(stats.t.ppf(0.975, n - 1) * d.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(d.mean())
    return [round(m, 4), round(m - half, 4), round(m + half, 4), int((d > 0).sum()), int((d < 0).sum()), n]


def contrasts(data, out):
    head = ["panel", "unit", "contrast", "endpoint", "condition", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows_b, rows_g = [], []
    for (p, u), arrs in data.items():
        conds = [c.name for c in D.PANELS[p]["conds"]]
        snaps = D.PANELS[p]["snaps"]
        eps = ("sign", "spacing") if p == "G" else ("patch",)
        for ep in eps:
            for a in ("li2", "li4"):
                d = arrs[f"{a}/{ep}"] - arrs[f"dw/{ep}"]
                for si, t in enumerate(snaps):
                    for ci, c in enumerate(conds):
                        rows_b.append([p, u, f"{a}-dw", ep, c, t, *_row(d[:, si, ci])])
            for body in D.BODIES:
                x = arrs[f"{body}/{ep}"]
                for ci, c in enumerate(conds):
                    bud, rest = c.split("/", 1)
                    if bud == "base":
                        continue
                    ref = conds.index(f"base/{rest}")
                    for si, t in enumerate(snaps):
                        rows_g.append([p, u, f"{body}:{bud}-base", ep, rest, t, *_row(x[:, si, ci] - x[:, si, ref])])
    for name, rows in (("contrasts_bodies.csv", rows_b), ("contrasts_budgets.csv", rows_g)):
        with open(out / name, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(head)
            wr.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "en002")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "levels": L,
               "statements": S}
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
