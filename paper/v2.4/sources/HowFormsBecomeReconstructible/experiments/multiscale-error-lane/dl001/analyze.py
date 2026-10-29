"""DL001's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m dl001.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. Contrasts are paired
within block (body minus body on the same cases and noise), with 95% t intervals over blocks. The price of holding
(descriptive, not registered) is the least gain at which panel U's sign at t = 2000 reaches 0.95, interpolated on log
gain between grid points (gain 0 from panel F at t = 2000, the same noise; linear between 0 and 0.005).
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

from dl001 import design as D  # noqa: E402

FROZEN = LANE / "dl001" / "frozen"
SNAPS = {"F": D.SNAPS_F, "U": D.SNAPS_U, "W": D.SNAPS_W, "B": D.SNAPS_B, "X/free": D.SNAPS_X0, "X/held": D.SNAPS_X}
CONDS = {"F": [c.name for c in D.COND_F], "U": [c.name for c in D.COND_U], "W": [c.name for c in D.COND_W],
         "B": [c.name for c in D.COND_B], "X/free": [D.COND_X[0].name], "X/held": [c.name for c in D.COND_X[1:]]}
SNAP_EPS = ("sign", "shift", "spacing", "patch")
FINAL_EPS = ("qual", "w_corr", "w_drift")


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


def groups(panel, body):
    return [(f"{body}/free", "X/free"), (f"{body}/held", "X/held")] if panel == "X" else [(body, panel)]


def levels(data):
    """levels[panel][unit][tag][cond][endpoint@t] = [mean over blocks, SD over blocks]."""
    out = {}
    for (p, u), arrs in data.items():
        for body in D.PANELS[p]["bodies"]:
            for tag, key in groups(p, body):
                for ep in SNAP_EPS:
                    x = arrs.get(f"{tag}/{ep}")
                    if x is None:
                        continue
                    for si, t in enumerate(SNAPS[key]):
                        for ci, c in enumerate(CONDS[key]):
                            v = x[:, si, ci]
                            out.setdefault(p, {}).setdefault(u, {}).setdefault(tag, {}).setdefault(c, {})[f"{ep}@{t}"] = \
                                [round(float(v.mean()), 4), round(float(v.std(ddof=1)), 4) if len(v) > 1 else None]
                for ep in FINAL_EPS:
                    x = arrs[f"{tag}/{ep}"]
                    for ci, c in enumerate(CONDS[key]):
                        v = x[:, ci]
                        out[p][u][tag][c][ep] = [round(float(v.mean()), 6), round(float(v.std(ddof=1)), 6) if len(v) > 1 else None]
    return out


def lv(L, p, u, tag, c, ep):
    return L[p][u][tag][c][ep][0]


def price(L, u, body):
    pts = [(0.0, lv(L, "F", u, body, "free", "sign@2000"))] + [(g, lv(L, "U", u, body, f"g{g:g}", "sign@2000")) for g in D.GAINS_U]
    if pts[0][1] >= 0.95:
        return 0.0
    for (g0, y0), (g1, y1) in zip(pts, pts[1:]):
        if y1 >= 0.95:
            if y1 == y0:
                return g1
            f = (0.95 - y0) / (y1 - y0)
            return round(g0 + f * (g1 - g0), 5) if g0 == 0 else round(float(np.exp(np.log(g0) + f * (np.log(g1) - np.log(g0)))), 5)
    return None                                                     # not reached at the largest gain


def score(L):
    S = {}
    s01 = [D.unit_name(pt, 0.1, t) for pt in D.PATTERNS for t in D.THETAS]
    sp = {b: {u: lv(L, "F", u, b, "free", "spacing@8000") for u in s01} for b in D.BODIES_MAIN}
    ok = all(6.5 <= sp[b][u] <= 8.5 for b in ("li2", "li4") for u in s01) and all(sp["dw"][u] > 8.5 for u in s01)
    S["D1"] = {"verdict": "HOLDS" if ok else "FAILS", "spacing@8000": sp}

    u = "S4_s0.1_t0"
    v = {b: lv(L, "F", u, b, "free", "sign@8000") for b in D.BODIES_MAIN}
    S["D2"] = {"verdict": "HOLDS" if v["li2"] >= 0.98 and v["li4"] >= 0.98 and v["li4"] > v["dw"] else "FAILS", "sign@8000": v}

    v = {x: lv(L, "F", x, "li4", "free", "sign@8000") for x in ("S4_s0.1_t1", "S4_s0.3_t0", "S4_s0.3_t1")}
    S["D3"] = {"verdict": "HOLDS" if all(y <= 0.60 for y in v.values()) else "FAILS", "li4_sign@8000": v}

    u = "F0_s0.1_t0"
    v = {"dw_free_sign@2000": lv(L, "F", u, "dw", "free", "sign@2000"), "li4_g0.2_sign@2000": lv(L, "U", u, "li4", "g0.2", "sign@2000")}
    S["D4"] = {"verdict": "HOLDS" if v["dw_free_sign@2000"] >= 0.95 and v["li4_g0.2_sign@2000"] <= 0.85 else "FAILS", "values": v}

    u = "S4_s0.1_t0"
    v = {b: lv(L, "B", u, b, "g0.05", "sign@2000") for b in D.BODIES_MAIN}
    w = {b: lv(L, "B", u, b, "g0.05", "w_corr") for b in ("dw", "li4")}
    S["D5"] = {"verdict": "HOLDS" if v["li2"] >= 0.98 and v["li4"] >= 0.98 and v["dw"] <= 0.80 and w["li4"] < w["dw"] else "FAILS",
               "sign@2000": v, "w_corr": w}

    u = "S4_s0.1_t0"
    rs = {b: lv(L, "W", u, b, "reset8-g0", "patch@2000") for b in D.BODIES_MAIN}
    fl = {b: lv(L, "W", u, b, "flip8-g0", "patch@2000") for b in D.BODIES_MAIN}
    ok = rs["li2"] >= 0.95 and rs["li4"] >= 0.95 and rs["dw"] <= 0.70 and fl["li4"] >= 0.85 and fl["dw"] <= 0.50
    S["D6"] = {"verdict": "HOLDS" if ok else "FAILS", "reset8_patch@2000": rs, "flip8_patch@2000": fl}

    u = "S4_s0.1_t1"
    diffs = {"g0": round(lv(L, "F", u, "li4", "free", "sign@2000") - lv(L, "F", u, "dw", "free", "sign@2000"), 4)}
    diffs |= {f"g{g:g}": round(lv(L, "U", u, "li4", f"g{g:g}", "sign@2000") - lv(L, "U", u, "dw", f"g{g:g}", "sign@2000"), 4)
              for g in D.GAINS_U}
    pr = lv(L, "W", u, "li4", "reset8-g0", "patch@2000")
    S["D7"] = {"verdict": "HOLDS" if max(abs(x) for x in diffs.values()) <= 0.08 and pr <= 0.60 else "FAILS",
               "li4_minus_dw_sign@2000": diffs, "li4_reset8_patch@2000": pr}

    x = lambda pt, b: lv(L, "X", D.unit_name(pt, 0.1, 0.0, D.SIDE_X), f"{b}/free", "g0", "sign@8000")
    v = {"li16_S8": x("S8", "li16"), "li16_F0": x("F0", "li16"), "li4_S4": x("S4", "li4"), "li4_S8": x("S8", "li4")}
    ok = v["li16_S8"] >= 0.95 and v["li16_F0"] <= 0.80 and v["li4_S4"] >= 0.95 and v["li4_S8"] <= 0.70
    S["D8"] = {"verdict": "HOLDS" if ok else "FAILS", "sign@8000": v}
    return S


def contrasts(data, out):
    pairs = {"F": (("li4", "dw"), ("li2", "dw")), "U": (("li4", "dw"), ("li2", "dw")), "W": (("li4", "dw"), ("li2", "dw")),
             "B": (("li4", "dw"), ("li2", "dw")), "X": (("li16", "dw"), ("li4", "dw"))}
    rows = []
    for (p, u), arrs in data.items():
        for a, b in pairs[p]:
            for (ta, key), (tb, _) in zip(groups(p, a), groups(p, b)):
                for ep in ("sign", "patch", "spacing"):
                    if f"{ta}/{ep}" not in arrs:
                        continue
                    d = arrs[f"{ta}/{ep}"] - arrs[f"{tb}/{ep}"]
                    for si, t in enumerate(SNAPS[key]):
                        for ci, c in enumerate(CONDS[key]):
                            v = d[:, si, ci]
                            n = len(v)
                            half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
                            rows.append([p, u, f"{ta}-{tb}", ep, c, t, round(float(v.mean()), 4),
                                         round(float(v.mean()) - half, 4), round(float(v.mean()) + half, 4), n])
    with open(out / "contrasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["panel", "unit", "contrast", "endpoint", "condition", "t", "mean", "lo95", "hi95", "blocks"])
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "dl001")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    prices = {u: {b: price(L, u, b) for b in D.BODIES_MAIN} for u in D.PANELS["U"]["units"]}
    S = score(L)
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "levels": L,
               "price_gain_for_sign_0.95": prices, "statements": S}
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
