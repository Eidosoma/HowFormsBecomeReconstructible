"""DL003's frozen reader: block means of every endpoint and profile, the registered statements, paired contrasts.

python -m dl003.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. Profiles are the mean
agreement at each distance from a boundary or cluster, block means likewise (means only). Contrasts are paired within
block (same cases and noise), with 95% t intervals over blocks.
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

from dl003 import design as D  # noqa: E402

SNAP_EPS = ("sign", "shift", "spacing")


def load(root, blocks):
    data = {}
    for p, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / p / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(p, u)] = {k: np.stack(v) for k, v in arrs.items()}      # (blocks, ..., cases[, distance])
    return data


def case_mean(x, prof=False):
    """Block means over the cases axis: the last axis, or the one before the distance axis for profiles."""
    return x.mean(-2) if prof else x.mean(-1)


def levels(data):
    """levels[panel][unit][body][arm][endpoint@t] = [mean over blocks, SD over blocks]; profiles as mean lists."""
    out = {}
    for (p, u), arrs in data.items():
        arms = [a.name for a in D.PANELS[p]["arms"]]
        for b in D.BODIES:
            node = out.setdefault(p, {}).setdefault(u, {}).setdefault(b, {})
            for ep in SNAP_EPS:
                x = case_mean(arrs[f"{b}/{ep}"])                          # (blocks, snaps, arms)
                for si, t in enumerate(D.SNAPS):
                    for ai, arm in enumerate(arms):
                        v = x[:, si, ai]
                        node.setdefault(arm, {})[f"{ep}@{t}"] = [round(float(v.mean()), 4), round(float(v.std(ddof=1)), 4) if len(v) > 1 else None]
            for ep in ("w_corr", "qual"):
                x = case_mean(arrs[f"{b}/{ep}"])                          # (blocks, arms)
                for ai, arm in enumerate(arms):
                    v = x[:, ai]
                    node[arm][ep] = [round(float(v.mean()), 6), round(float(v.std(ddof=1)), 6) if len(v) > 1 else None]
            for g in D.DMAX:
                x = case_mean(arrs[f"{b}/prof_{g}"], prof=True)           # (blocks, arms, distance)
                for ai, arm in enumerate(arms):
                    node[arm][f"prof_{g}"] = [round(float(v), 4) for v in x[:, ai].mean(0)]
    return out


def window_mean(prof, win):
    return float(np.mean(prof[win[0]:win[1]]))


def score(L):
    S = {}
    U = lambda th: D.unit_name(th)
    sign = lambda p, th, b, arm: L[p][U(th)][b][arm]["sign@4000"][0]
    prof = lambda p, th, b, arm, home=None: L[p][U(th)][b][arm][f"prof_{home or arm_home(p, arm)}"]
    far = lambda p, th, b, arm: round(window_mean(prof(p, th, b, arm), D.FAR), 4)
    near = lambda p, th, b, arm: round(window_mean(prof(p, th, b, arm), D.NEAR), 4)

    v = {"sign": sign("B", 0.0, "li4", "perp/f100"), "far": far("B", 0.0, "li4", "perp/f100")}
    S["B1"] = {"verdict": "HOLDS" if v["sign"] >= 0.97 and v["far"] >= 0.95 else "FAILS", "li4_t0_perp/f100": v}

    v = {"sign": sign("B", 0.0, "li4", "perp"), "far": far("B", 0.0, "li4", "perp"),
         "f100_minus_perp": round(sign("B", 0.0, "li4", "perp/f100") - sign("B", 0.0, "li4", "perp"), 4)}
    S["B2"] = {"verdict": "HOLDS" if v["sign"] <= 0.80 and v["far"] <= 0.65 and v["f100_minus_perp"] >= 0.20 else "FAILS",
               "li4_t0_perp": v}

    v = round(sign("B", 0.0, "li4", "perp/f100") - sign("B", 0.0, "li4", "scatter"), 4)
    S["B3"] = {"verdict": "HOLDS" if v >= 0.05 else "FAILS", "li4_t0_perp/f100_minus_scatter": v}

    v = {arm: far("B", 0.0, "li4", arm) for arm in ("perp/f25", "perp/f100", "perp/f200")}
    S["B4"] = {"verdict": "HOLDS" if v["perp/f25"] <= 0.90 and v["perp/f100"] >= 0.95 and v["perp/f200"] >= 0.95 else "FAILS",
               "li4_t0_far": v}

    v = {arm: sign("B", 0.0, "li4", arm) for arm in ("par/f25", "par/f50", "par/f100")}
    gap = round(sign("B", 0.0, "li4", "perp/f100") - max(v.values()), 4)
    S["B5"] = {"verdict": "HOLDS" if max(v.values()) <= 0.90 and gap >= 0.08 else "FAILS", "li4_t0_sign": v,
               "perp/f100_minus_best_par_front": gap}

    v = sign("B", 0.0, "li4", "none/perp-f100")
    S["B6"] = {"verdict": "HOLDS" if v <= 0.60 else "FAILS", "li4_t0_none/perp-f100": v}

    v = {f"t{th:g}": round(sign("B", th, "li4", "scatter") - max(sign("B", th, "li4", "perp/f100"), sign("B", th, "li4", "perp/f200")), 4)
         for th in (0.5, 1.0)}
    S["B7"] = {"verdict": "HOLDS" if min(v.values()) >= 0.03 else "FAILS", "li4_scatter_minus_best_perp_front": v}

    d = round(sign("B", 0.0, "li4", "perp/f100") - sign("B", 0.0, "dw", "perp/f100"), 4)
    dw = {arm: sign("B", 0.0, "dw", arm) for arm in ("scatter", "par", "perp", "cluster")}
    S["B8"] = {"verdict": "HOLDS" if d >= 0.15 and max(dw.values()) <= 0.62 else "FAILS",
               "t0_perp/f100_li4_minus_dw": d, "dw_t0_sign": dw}

    v = {f"{b}/t{th:g}": round(sign("H", th, b, "scatter") - max(sign("H", th, b, a) for a in ("par", "perp", "cluster")), 4)
         for b in D.BODIES for th in (0.5, 1.0)}
    S["B9"] = {"verdict": "HOLDS" if min(v.values()) >= 0.005 else "FAILS", "scatter_minus_best_other": v}

    v = {}
    for th in (0.5, 1.0):
        for arm in ("par", "perp"):
            mine, base = prof("H", th, "li4", arm), prof("H", th, "li4", "none", arm)
            beyond = round(float(np.mean(np.array(mine[D.BEYOND:]) - np.array(base[D.BEYOND:]))), 4)
            v[f"t{th:g}/{arm}"] = {"near": near("H", th, "li4", arm), "beyond": beyond}
    S["B10"] = {"verdict": "HOLDS" if all(x["near"] >= 0.85 and x["beyond"] <= 0.05 for x in v.values()) else "FAILS",
                "li4": v}
    return S


def arm_home(panel, name):
    return [a for a in D.PANELS[panel]["arms"] if a.name == name][0].home


def contrasts(data, out):
    rows = []
    for (p, u), arrs in data.items():
        arms = [a.name for a in D.PANELS[p]["arms"]]
        pairs = [("li4", a, "dw", a) for a in arms] + [(b, a, b, "scatter") for b in D.BODIES for a in arms if a != "scatter"]
        if p == "B":
            pairs += [(b, "perp/f100", b, a) for b in D.BODIES for a in ("perp", "perp/f25", "perp/f200", "par/f25", "par/f50", "par/f100")]
        for b1, a1, b2, a2 in pairs:
            x1 = case_mean(arrs[f"{b1}/sign"])[:, :, arms.index(a1)]
            x2 = case_mean(arrs[f"{b2}/sign"])[:, :, arms.index(a2)]
            d = x1 - x2
            for si, t in enumerate(D.SNAPS):
                v = d[:, si]
                n = len(v)
                half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
                rows.append([p, u, f"{b1}/{a1}-{b2}/{a2}", "sign", t, round(float(v.mean()), 4), round(float(v.mean()) - half, 4),
                             round(float(v.mean()) + half, 4), int((v > 0).sum()), int((v < 0).sum()), n])
    with open(out / "contrasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["panel", "unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"])
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "dl003")
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
