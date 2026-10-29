"""Reader: python -m br002.analyze --root RUN_ROOT --stage {preflight,development} --out OUT_DIR [--blocks LO,HI]

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

from br002 import design as D  # noqa: E402

FROZEN = Path(__file__).resolve().parent / "frozen"
SHORT = {"BENEFIT": "B", "HARM": "H", "NO MEANINGFUL DIFFERENCE": "=", "UNDECIDED": "?"}
ALL_ENDPOINTS = ("v_qual", "v_sign", "r_sign", "les_r", "les_v", "fR_qual", "vg_qual", "rg_sign", "adopt_flip", "gR_qual", "w_l1")


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
    cn = {p: [c.name for c in D.PANELS[p]["conditions"]] for p in D.PANELS}
    bm = lambda p, r, arm, ep, cond: float(get(data[p][r], arm, ep, len(cn[p]))[:, cn[p].index(cond)].mean())
    rnd = lambda d: {k: round(v, 4) for k, v in d.items()}
    verdict = lambda ok: "HOLDS" if ok else "FAILS"
    if "C" in data:
        c_all = list(D.PANELS["C"]["regimes"])
        high = [D.regime("F0", 0.3), D.regime("F0", 0.3, "o")]
        opn = [D.regime("F0", 0.1, "o"), D.regime("F0", 0.3, "o")]
        cons = [D.regime("F0", 0.1), D.regime("F0", 0.3)]
        vals, ok = {}, True
        for r in c_all:
            v = {a: bm("C", r, a, "adopt_flip", "impose-inf") for a in ("always", "always+h", "duration", "duration+h", "tags", "tags+h")}
            ok &= all(v[a] >= 0.95 for a in ("always+h", "duration+h", "tags+h"))
            if r in high:
                ok &= all(v[a] <= 0.5 for a in ("always", "duration", "tags"))
            vals[r] = rnd(v)
        out["RC1"] = {"verdict": verdict(ok), "adopt_flip_impose_inf": vals}
        vals, ok = {}, True
        for r in c_all:
            v = {"scar_les_r": bm("C", r, "duration+h", "les_r", "scar-6x6"),
                 "transient_adopt_flip": bm("C", r, "duration+h", "adopt_flip", "impose-300")}
            ok &= v["scar_les_r"] <= 0.5 and v["transient_adopt_flip"] <= 0.05
            vals[r] = rnd(v)
        out["RC2"] = {"verdict": verdict(ok), "duration+h": vals}
        vals = {r: round(bm("C", r, "tags+h", "les_r", "scar-6x6"), 4) for r in opn + cons}
        ok = all(vals[r] >= 0.85 for r in opn) and all(vals[r] <= 0.5 for r in cons)
        out["RC3"] = {"verdict": verdict(ok), "tags+h_scar_les_r": vals}
        vals = {r: round(bm("C", r, "phase", "les_r", "window-scar-6x6"), 4) for r in c_all}
        out["RC4"] = {"verdict": verdict(all(x <= 0.5 for x in vals.values())), "phase_window_scar_les_r": vals}
        vals, ok = {}, True
        for r in c_all:
            v = {"cued_adopt_flip": bm("C", r, "phase+tags", "adopt_flip", "impose-inf-cued"),
                 "window_scar_gain": bm("C", r, "phase+tags", "les_r", "window-scar-6x6") - bm("C", r, "phase", "les_r", "window-scar-6x6")}
            ok &= v["cued_adopt_flip"] >= 0.95
            ok &= v["window_scar_gain"] >= 0.3 if r in opn else v["window_scar_gain"] <= 0.1
            vals[r] = rnd(v)
        out["RC5"] = {"verdict": verdict(ok), "phase+tags": vals}
        vals, ok = {}, True
        for r in high:
            v = {a: bm("C", r, f"{a}+h", "w_l1", "impose-inf") / max(bm("C", r, a, "w_l1", "impose-inf"), 1e-12)
                 for a in ("always", "duration", "tags")}
            ok &= all(x <= 0.5 for x in v.values())
            vals[r] = rnd(v)
        out["RC6"] = {"verdict": verdict(ok), "w_l1_committed_over_uncommitted": vals}
    if "R" in data:
        r_all = list(D.PANELS["R"]["regimes"])
        fine = [r for r in r_all if r.startswith(("BL", "IS"))]
        for sid, cond in (("RR1", "sham"), ("RR3", "turnover-0.003")):
            vals = {r: {"rel": round(bm("R", r, "rel", "r_sign", cond), 4), "self": round(bm("R", r, "self", "r_sign", cond), 4)}
                    for r in r_all}
            ok = all(vals[r]["rel"] >= 0.98 for r in r_all) and all(vals[r]["self"] <= 0.9 for r in fine)
            out[sid] = {"verdict": verdict(ok), f"r_sign_{cond}": vals}
        vals, ok = {}, True
        for r in r_all:
            v = {f"rel/{s}": bm("R", r, "rel", "les_r", f"both-{s}x{s}") for s in (2, 4, 6, 8)}
            v["rel+code/8"] = bm("R", r, "rel+code", "les_r", "both-8x8")
            ok &= all(v[f"rel/{s}"] >= 0.95 for s in (2, 4, 6)) and v["rel/8"] >= 0.9 and v["rel+code/8"] >= 0.9
            vals[r] = rnd(v)
        out["RR2"] = {"verdict": verdict(ok), "les_r": vals}
        vals, ok = {}, True
        for r in r_all:
            v = {"rel": bm("R", r, "rel", "les_r", "kill-8x8"), "rel+code+relink": bm("R", r, "rel+code+relink", "les_r", "kill-8x8")}
            ok &= v["rel"] <= 0.8 and v["rel+code+relink"] >= 0.9
            vals[r] = rnd(v)
        out["RR4"] = {"verdict": verdict(ok), "les_r_kill_8x8": vals}
        rows, ok = {}, True
        for r in r_all:
            dr, nc = data["R"][r], len(cn["R"])
            row = summarize(get(dr, "rel", "v_qual", nc)[:, 0] - get(dr, "protected", "v_qual", nc)[:, 0])
            rows[r] = [round(row["point"], 4), round(row["lo"], 4), round(row["hi"], 4)]
            ok &= row["lo"] > 0
        out["RR5"] = {"verdict": verdict(ok), "rel_minus_protected_v_qual_sham": rows}
    if "G" in data:
        g_all = list(D.PANELS["G"]["regimes"])
        vals, ok = {}, True
        for r in g_all:
            v = {c: bm("G", r, "self", "les_r", c) for c in ("w6-d1", "w6-cross", "w4-d2", "w4-d0")}
            ok &= v["w6-d1"] <= 0.2 and v["w6-cross"] >= 0.8 and v["w4-d2"] >= 0.95 and v["w4-d0"] <= 0.75
            vals[r] = rnd(v)
        out["RG1"] = {"verdict": verdict(ok), "self_les_r": vals}
        vals, ok = {}, True
        for r in g_all:
            v = {}
            for c in D.COND_G:
                if not c.size:
                    continue
                v[f"rel+code/{c.name}"] = bm("G", r, "rel+code", "les_r", c.name)
                ok &= v[f"rel+code/{c.name}"] >= 0.98
                if c.size <= 6:
                    v[f"rel/{c.name}"] = bm("G", r, "rel", "les_r", c.name)
                    ok &= v[f"rel/{c.name}"] >= 0.95
            vals[r] = rnd(v)
        out["RG2"] = {"verdict": verdict(ok), "les_r": vals}
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
