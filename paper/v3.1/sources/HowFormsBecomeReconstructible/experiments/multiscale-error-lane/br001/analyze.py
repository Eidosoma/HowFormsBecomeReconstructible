"""Reader: python -m br001.analyze --root RUN_ROOT --stage {preflight,development} --out OUT_DIR [--blocks LO,HI]

Units are source blocks: an endpoint is paired within case, averaged over the block's 8 cases and
summarised over block means with a 95% t interval. Readings as ME002 (BENEFIT, HARM, NO MEANINGFUL
DIFFERENCE within +-0.02, UNDECIDED). Compact tables to OUT_DIR (git), full tables to RUN_ROOT/analysis.
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

from br001 import design as D  # noqa: E402

FROZEN = Path(__file__).resolve().parent / "frozen"
SHORT = {"BENEFIT": "B", "HARM": "H", "NO MEANINGFUL DIFFERENCE": "=", "UNDECIDED": "?"}
ALL_ENDPOINTS = ("v_qual", "v_sign", "r_sign", "les_r", "les_v", "fR_qual", "vg_qual", "rg_sign", "gR_qual", "w_l1")


def load(root, panel, regimes, blocks):
    data = {}
    for r in regimes:
        per = [dict(np.load(root / "shards" / panel / r / f"{b}.npz")) for b in blocks]
        keys = set(per[0]) - {"__meta__"}
        data[r] = {k: np.stack([p[k] for p in per]) for k in keys}
    return data


def get(dr, name, ep, nc):
    x = dr.get(f"{name}/{ep}")
    if x is None:
        return None
    return np.broadcast_to(x, (x.shape[0], nc, x.shape[2])).astype(float) if x.shape[1] == 1 else x.astype(float)


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
            "blocks_neg": int((b < 0).sum()), "case_rescue": int((d > D.MARGIN).sum()),
            "case_harm": int((d < -D.MARGIN).sum()), "reading": reading(point - half, point + half)}


def contrasts(panel, data, endpoints):
    rows = []
    conds = [c.name for c in D.PANELS[panel]["conditions"]]
    for p, fam, a, b in D.CONTRASTS:
        if p != panel:
            continue
        for r, dr in data.items():
            for ep in endpoints:
                x, y = get(dr, a, ep, len(conds)), get(dr, b, ep, len(conds))
                if x is None or y is None:
                    continue
                for ci, c in enumerate(conds):
                    rows.append({"panel": panel, "family": fam.split()[0], "arm": a, "ref": b, "regime": r,
                                 "condition": c, "endpoint": ep, **summarize(x[:, ci] - y[:, ci])})
    return rows


def levels(panel, dr, endpoints):
    nc = len(D.PANELS[panel]["conditions"])
    out = {}
    for ep in endpoints:
        for a in D.PANELS[panel]["arms"]:
            x = get(dr, a.name, ep, nc)
            if x is not None:
                out.setdefault(ep, {})[a.name] = [round(float(v), 4) for v in x.mean((0, 2))]
    return out


def write_csv(path, rows):
    cols = ["panel", "family", "arm", "ref", "regime", "condition", "endpoint", "point", "lo", "hi",
            "blocks_pos", "blocks_neg", "case_rescue", "case_harm", "reading"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] if c not in ("point", "lo", "hi") else f"{r[c]:.4f}" for c in cols[:-1]] + [SHORT[r["reading"]]])


def score(data):
    out = {}
    cl = [c.name for c in D.COND_L]
    cp = [c.name for c in D.COND_P]
    ct = [c.name for c in D.COND_T]
    bm = lambda panel, r, arm, ep, cond, conds: float(get(data[panel][r], arm, ep, len(conds))[:, conds.index(cond)].mean())
    if "L" in data:
        F0C = [D.regime("F0", 0.1), D.regime("F0", 0.3)]
        vals, ok = {}, True
        for r in F0C:
            v = {f"{a}/{s}": bm("L", r, a, "les_r", f"both-{s}x{s}", cl) for a in ("self", "code", "multi") for s in D.SIZES}
            ok &= v["self/2"] >= 0.9 and v["self/8"] <= 0.6 and v["code/2"] <= 0.1 and v["code/8"] >= 0.6
            ok &= all(v[f"multi/{s}"] >= 0.9 for s in D.SIZES)
            vals[r] = {k: round(x, 4) for k, x in v.items()}
        out["RL1"] = {"verdict": "HOLDS" if ok else "FAILS", "les_r": vals}
        rows, ok = {}, True
        for r in F0C:
            dr = data["L"][r]
            for s in D.SIZES:
                ci = cl.index(f"both-{s}x{s}")
                row = summarize(get(dr, "multi", "v_qual", len(cl))[:, ci] - get(dr, "protected", "v_qual", len(cl))[:, ci])
                rows[f"{r}/{s}x{s}"] = [round(row["point"], 4), round(row["lo"], 4), round(row["hi"], 4)]
                ok &= row["lo"] > -0.02
        out["RL2"] = {"verdict": "HOLDS" if ok else "FAILS", "multi_minus_protected": rows}
        gap, ok = {}, True
        for s_ in (0.1, 0.3):
            f0 = bm("L", D.regime("F0", s_), "multi", "les_r", "both-8x8", cl) - bm("L", D.regime("F0", s_), "self", "les_r", "both-8x8", cl)
            bl = bm("L", D.regime("BL", s_), "multi", "les_r", "both-8x8", cl) - bm("L", D.regime("BL", s_), "self", "les_r", "both-8x8", cl)
            gap[f"sigma{s_:g}"] = {"F0": round(f0, 4), "BL": round(bl, 4)}
            ok &= bl < f0 - 0.10
        out["RL3"] = {"verdict": "HOLDS" if ok else "FAILS", "multi_minus_self_8x8": gap}
        heal, ok = {}, True
        for s_ in (0.1, 0.3):
            o = bm("L", D.regime("F0", s_, "o"), "protected", "les_v", "body-8x8", cl)
            c = bm("L", D.regime("F0", s_), "protected", "les_v", "body-8x8", cl)
            heal[f"sigma{s_:g}"] = {"open": round(o, 4), "conserved": round(c, 4)}
            ok &= o >= c + 0.05
        out["RL4"] = {"verdict": "HOLDS" if ok else "FAILS", "les_v_body8x8_protected": heal}
    if "P" in data:
        v1, v2, v3, ok1, ok2, ok3 = {}, {}, {}, True, True, True
        for r in D.PANELS["P"]["regimes"]:
            g = lambda a, ep, c: bm("P", r, a, ep, c, cp)
            a = {"tags_scar_les_r": g("write_tags", "les_r", "scar-6x6"), "duration_scar_les_r": g("write_duration", "les_r", "scar-6x6"),
                 "tags_cued_rg": g("write_tags", "rg_sign", "impose-inf-cued"), "duration_cued_rg": g("write_duration", "rg_sign", "impose-inf-cued")}
            ok1 &= a["tags_scar_les_r"] >= 0.9 and a["duration_scar_les_r"] <= 0.5 and a["tags_cued_rg"] >= 0.8 and a["duration_cued_rg"] >= 0.8
            b = {"tags_transient_rg": g("write_tags", "rg_sign", "impose-300"), "duration_transient_rg": g("write_duration", "rg_sign", "impose-300"),
                 "phase_uncued_rg": g("write_phase", "rg_sign", "impose-inf"), "duration_uncued_rg": g("write_duration", "rg_sign", "impose-inf")}
            ok2 &= b["tags_transient_rg"] >= b["duration_transient_rg"] + 0.1 and b["phase_uncued_rg"] <= 0.6 and b["duration_uncued_rg"] >= 0.8
            c = g("write_always", "les_r", "scar-6x6")
            ok3 &= c <= 0.5
            v1[r], v2[r], v3[r] = {k: round(x, 4) for k, x in a.items()}, {k: round(x, 4) for k, x in b.items()}, round(c, 4)
        out["RP1"] = {"verdict": "HOLDS" if ok1 else "FAILS", "values": v1}
        out["RP2"] = {"verdict": "HOLDS" if ok2 else "FAILS", "values": v2}
        out["RP3"] = {"verdict": "HOLDS" if ok3 else "FAILS", "always_scar_les_r": v3}
    if "T" in data:
        hi = "turnover-0.003"
        v1, ok1 = {}, True
        for s_ in (0.05, 0.1, 0.3):
            r = D.regime("F0", s_)
            st, se = bm("T", r, "static", "r_sign", hi, ct), bm("T", r, "self", "r_sign", hi, ct)
            v1[r] = {"static": round(st, 4), "self": round(se, 4)}
            ok1 &= st <= 0.6 and se >= 0.95
        out["RT1"] = {"verdict": "HOLDS" if ok1 else "FAILS", "r_sign_turnover_0.003": v1}
        v2, ok2 = {}, True
        for s_ in (0.1, 0.3):
            r = D.regime("F0", s_)
            loss = {a: bm("T", r, a, "v_qual", "turnover-0", ct) - bm("T", r, a, "v_qual", hi, ct) for a in ("self", "static")}
            v2[r] = {k: round(x, 4) for k, x in loss.items()}
            ok2 &= loss["self"] < 0.05 and loss["static"] > 0.10
        out["RT2"] = {"verdict": "HOLDS" if ok2 else "FAILS", "v_qual_loss": v2}
        r = D.regime("F0", 0.05)
        val = {c: bm("T", r, "self", "v_qual", c, ct) - bm("T", r, "inactive", "v_qual", c, ct) for c in ("turnover-0", hi)}
        out["RT3"] = {"verdict": "HOLDS" if val[hi] >= val["turnover-0"] + 0.05 else "FAILS",
                      "self_minus_inactive": {k: round(x, 4) for k, x in val.items()}}
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
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "panels": {}}
    for p in D.PANELS:
        for ep in D.PRIMARY_ENDPOINTS[p]:
            write_csv(a.out / f"contrasts_{p}_{ep}.csv", contrasts(p, data[p], (ep,)))
        write_csv(full / f"contrasts_{p}_all.csv", contrasts(p, data[p], ALL_ENDPOINTS))
        summary["panels"][p] = {"conditions": [c.name for c in D.PANELS[p]["conditions"]],
                                "levels": {r: levels(p, dr, ALL_ENDPOINTS) for r, dr in data[p].items()}}
    summary["statements"] = score(data)
    (a.out / "predictions_scored.json").write_text(json.dumps(summary["statements"], indent=1) + "\n")
    (a.out / "summary.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in summary["statements"].items()}, indent=1))


if __name__ == "__main__":
    main()
