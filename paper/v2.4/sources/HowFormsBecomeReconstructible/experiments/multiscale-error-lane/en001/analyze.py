"""Reader: python -m en001.analyze --root RUN_ROOT --stage {preflight,development} --out OUT_DIR [--blocks LO,HI]

Units are source blocks: an endpoint is averaged over the block's 8 cases and summarised over block means;
contrasts are paired within case with a 95% t interval over block means. t95 (updates until the record kept in
a wound first reaches 0.95, snapshot grain 100) counts a wound never healed within the window as WINDOW + SNAP.
Compact tables to OUT_DIR (git), the full level table to RUN_ROOT/analysis.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from scipy.stats import t as student  # noqa: E402

from en001 import design as D  # noqa: E402

CONDS = [c.name for c in D.CONDS]
NEVER = D.WINDOW + D.SNAP


def load(root, panel, regimes, blocks):
    data = {}
    for r in regimes:
        per = [dict(np.load(root / "shards" / panel / r / f"{b}.npz")) for b in blocks]
        keys = set(per[0]) - {"__meta__"}
        data[r] = {k: np.stack([p[k] for p in per]) for k in keys}       # (blocks, conds, cases)
    return data


def get(dr, arm, budget, ep):
    x = dr[f"{arm}/{budget}/{ep}"].astype(float)
    return np.where(np.isinf(x), NEVER, x) if ep == "t95" else x


def bm(dr, arm, budget, ep, cond):
    """Block mean over blocks and cases, nan-aware (a_patch, t95 without a wound)."""
    x = get(dr, arm, budget, ep)[:, CONDS.index(cond)]
    return float(np.nanmean(x))


def interval(d):
    """d: (blocks, cases) paired differences -> point, lo, hi over block means."""
    b = np.nanmean(d, axis=1)
    point = float(b.mean())
    half = float(student.ppf(0.975, len(b) - 1) * b.std(ddof=1) / np.sqrt(len(b)))
    return point, point - half, point + half


def levels(panel, dr):
    out = {}
    for arm, b in D.branches(panel):
        for ep in D.ENDPOINTS:
            x = get(dr, arm, b.name, ep)
            vals = [None if np.isnan(x[:, ci]).all() else round(float(np.nanmean(x[:, ci])), 4) for ci in range(len(CONDS))]
            out.setdefault(arm, {}).setdefault(b.name, {})[ep] = vals
    return out


def score(data):
    out = {}
    v = lambda dr, arm, b, ep, c: bm(dr, arm, b, ep, c)
    verdict = lambda ok: "HOLDS" if ok else "FAILS"
    rnd = lambda d: {k: (round(x, 4) if isinstance(x, float) else x) for k, x in d.items()}
    spend = lambda dr, arm, b: sum(v(dr, arm, b, ep, "sham") for ep in ("w_drift", "w_corr", "w_rec"))
    pair = ("multi", "relcode")
    if "G" in data:
        G = data["G"]
        regs = list(D.PANELS["G"]["regimes"])
        f3 = D.regime("F0", 0.3)
        vals, ok = {}, True                                   # EB1: thermal dissolves, activity holds
        for r in regs:
            for arm in pair:
                d = {b: v(G[r], arm, b, "v_qual", "sham") for b in ("base", "B0.1", "C0.1")}
                ok &= d["B0.1"] <= d["base"] - 0.1 and d["C0.1"] >= d["base"] - 0.02
                vals[f"{r}/{arm}"] = rnd(d)
        out["EB1"] = {"verdict": verdict(ok), "v_qual_sham": vals}
        vals, ok = {}, True                                   # EB2: the plan outlives its expression
        for r in regs:
            for arm in ("hold", "multi", "relcode"):
                d = {"r_sign_B0.1": v(G[r], arm, "B0.1", "r_sign", "sham"),
                     "v_qual_rec_B0.1": v(G[r], arm, "B0.1", "v_qual_rec", "sham"),
                     "v_qual_rec_base": v(G[r], arm, "base", "v_qual_rec", "sham")}
                ok &= d["r_sign_B0.1"] >= 0.95 and d["v_qual_rec_B0.1"] >= d["v_qual_rec_base"] - 0.02
                vals[f"{r}/{arm}"] = rnd(d)
        out["EB2"] = {"verdict": verdict(ok), "values": vals}
        vals, ok = {}, True                                   # EB3: repair slows under activity noise and completes
        for r in regs:
            d = {"relcode_t95_base": v(G[r], "relcode", "base", "t95", "flip-6x6"),
                 "relcode_t95_C0.1": v(G[r], "relcode", "C0.1", "t95", "flip-6x6"),
                 "relcode_les_r_rec_C0.1": v(G[r], "relcode", "C0.1", "les_r_rec", "flip-6x6"),
                 "multi_les_r_rec_C0.1": v(G[r], "multi", "C0.1", "les_r_rec", "flip-6x6"),
                 "multi_les_r_rec_base": v(G[r], "multi", "base", "les_r_rec", "flip-6x6")}
            ok &= (d["relcode_t95_C0.1"] >= 3 * d["relcode_t95_base"] and d["relcode_les_r_rec_C0.1"] >= 0.98
                   and d["multi_les_r_rec_C0.1"] >= d["multi_les_r_rec_base"] - 0.03)
            vals[r] = rnd(d)
        out["EB3"] = {"verdict": verdict(ok), "flip_repair": vals}
        vals, ok = {}, True                                   # EB4: outside-clock turnover outruns re-specification
        for r in regs:
            for arm in pair:
                gap = lambda b: v(G[r], arm, b, "v_qual", "sham") - v(G[r], arm, b, "v_qual", "turnover-0.001")
                d = {"gap_base": gap("base"), "gap_C0.1": gap("C0.1")}
                ok &= d["gap_C0.1"] >= d["gap_base"] + 0.02
                vals[f"{r}/{arm}"] = rnd(d)
        out["EB4"] = {"verdict": verdict(ok), "sham_minus_turnover_v_qual": vals}
        vals, ok = {}, True                                   # EB5: reset wounds stay repairable on a budget, flips do not
        for r in regs:
            for arm in ("self", "multi"):
                d = {"flip": v(G[r], arm, "C0.1", "les_r", "flip-6x6"), "reset": v(G[r], arm, "C0.1", "les_r", "reset-6x6")}
                ok &= d["reset"] >= d["flip"] + 0.1
                vals[f"{r}/{arm}"] = rnd(d)
        out["EB5"] = {"verdict": verdict(ok), "les_r_at_C0.1": vals}
        vals, ok = {}, True                                   # EB6: what fails first
        for arm in pair:
            base = {k: v(G[f3], arm, "base", ep, c) for k, ep, c in (("sham", "v_qual", "sham"), ("flip", "les_r", "flip-6x6"),
                                                                    ("turn", "v_qual", "turnover-0.001"))}
            loss = lambda b, k, ep, c: 1 - v(G[f3], arm, b, ep, c) / base[k]
            d = {"C0.1_loss_flip": loss("C0.1", "flip", "les_r", "flip-6x6"),
                 "C0.1_loss_turnover": loss("C0.1", "turn", "v_qual", "turnover-0.001"),
                 "C0.1_loss_sham": loss("C0.1", "sham", "v_qual", "sham"),
                 "B0.5_loss_sham": loss("B0.5", "sham", "v_qual", "sham"), "B0.5_loss_flip": loss("B0.5", "flip", "les_r", "flip-6x6")}
            ok &= (d["C0.1_loss_flip"] > d["C0.1_loss_turnover"] > d["C0.1_loss_sham"] and d["C0.1_loss_sham"] <= 0.02
                   and d["B0.5_loss_sham"] >= 0.10 and d["B0.5_loss_flip"] <= 0.02)
            vals[f"{f3}/{arm}"] = rnd(d)
        out["EB6"] = {"verdict": verdict(ok), "relative_losses": vals}
    if "P" in data:
        P = data["P"]
        regs = list(D.PANELS["P"]["regimes"])
        vals, ok = {}, True                                   # EP1: under thermal noise the expression needs the body paid
        for r in regs:
            for arm in pair:
                d = {a: v(P[r], arm, f"thermal-{a}", "v_qual", "sham") for a in ("uniform", "record", "body")}
                d["base"] = v(P[r], arm, "base", "v_qual", "sham")
                ok &= d["body"] >= d["base"] - 0.02 and d["record"] <= d["uniform"] + 0.02
                vals[f"{r}/{arm}"] = rnd(d)
        out["EP1"] = {"verdict": verdict(ok), "thermal_v_qual_sham": vals}
        vals, ok = {}, True                                   # EP2: the record is cheap to protect and keeps repair
        for r in regs:
            for arm in pair:
                for n in ("thermal", "activity"):
                    d = {"les_r": v(P[r], arm, f"{n}-record", "les_r", "flip-6x6"), "les_r_base": v(P[r], arm, "base", "les_r", "flip-6x6"),
                         "spend_ratio": spend(P[r], arm, f"{n}-record") / spend(P[r], arm, "base")}
                    ok &= d["les_r"] >= d["les_r_base"] - 0.02 and d["spend_ratio"] <= 0.6
                    vals[f"{r}/{arm}/{n}"] = rnd(d)
        out["EP2"] = {"verdict": verdict(ok), "record_protected": vals}
        vals, ok = {}, True                                   # EP3: under activity noise protecting the body is wasted
        for r in regs:
            for arm in pair:
                d = {"v_body": v(P[r], arm, "activity-body", "v_qual", "sham"), "v_uniform": v(P[r], arm, "activity-uniform", "v_qual", "sham"),
                     "spend_ratio": spend(P[r], arm, "activity-body") / spend(P[r], arm, "activity-uniform")}
                ok &= d["v_body"] <= d["v_uniform"] + 0.01 and d["spend_ratio"] >= 3
                vals[f"{r}/{arm}"] = rnd(d)
        out["EP3"] = {"verdict": verdict(ok), "activity_body_protected": vals}
    if "E" in data:
        E = data["E"]
        regs = list(D.PANELS["E"]["regimes"])
        vals, ok = {}, True                                   # EE1: a per-cell store gives the same split
        for r in regs:
            for arm in pair:
                d = {b: v(E[r], arm, b, "v_qual", "sham") for b in ("store-thermal1", "store-thermal0.1", "store-activity1", "store-activity0.1")}
                ok &= d["store-thermal0.1"] <= d["store-thermal1"] - 0.1 and d["store-activity0.1"] >= d["store-activity1"] - 0.02
                vals[f"{r}/{arm}"] = rnd(d)
        out["EE1"] = {"verdict": verdict(ok), "v_qual_sham": vals}
        if "G" in data:                                       # EE2: a store that lets spending follow demand buffers repair
            vals, ok = {}, True
            for r in regs:
                for arm in pair:
                    d = {"store_flip": v(E[r], arm, "store-activity0.1", "les_r", "flip-6x6"),
                         "global_flip": v(data["G"][r], arm, "C0.1", "les_r", "flip-6x6"),
                         "store_availability": v(E[r], arm, "store-activity0.1", "a_rest", "sham")}
                    ok &= d["store_flip"] >= d["global_flip"] + 0.05 and d["store_availability"] >= 0.2
                    vals[f"{r}/{arm}"] = rnd(d)
            out["EE2"] = {"verdict": verdict(ok), "values": vals}
    return out


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
    data = {p: load(root, p, D.PANELS[p]["regimes"], blocks) for p in D.PANELS}
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "conditions": CONDS,
               "panels": {p: {r: levels(p, dr) for r, dr in data[p].items()} for p in D.PANELS}}
    summary["statements"] = score(data)
    (a.out / "predictions_scored.json").write_text(json.dumps(summary["statements"], indent=1) + "\n")
    (full / "summary_full.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    keep = ("v_qual", "r_sign", "les_r", "v_qual_rec", "les_r_rec", "t95", "a_patch")
    compact = {**{k: v for k, v in summary.items() if k != "panels"},
               "panels": {p: {r: {arm: {b: {ep: vals for ep, vals in eps.items() if ep in keep} for b, eps in bs.items()}
                                  for arm, bs in regs.items()} for r, regs in pv.items()} for p, pv in summary["panels"].items()}}
    (a.out / "summary.json").write_text(json.dumps(compact, separators=(",", ":")) + "\n")
    print(json.dumps({k: x["verdict"] for k, x in summary["statements"].items()}, indent=1))


if __name__ == "__main__":
    main()
