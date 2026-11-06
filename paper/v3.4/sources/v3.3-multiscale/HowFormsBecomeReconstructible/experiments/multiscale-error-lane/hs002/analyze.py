"""HS002's reader: python -m hs002.analyze ROOT [--out DIR]  ->  DIR/summary.json and DIR/arrays.npz.

The curves join HS001's frozen shards for rewrites 1-256 (the stage's HS001 source root, read by hs001.analyze.load,
unchanged) and HS002's for 320-1,024. hs001.analyze's endpoints and intervals are used unchanged (E014's bootstrap
generator; the ratio rule), and hs002.fit gives the fit over all 24 checkpoints and rule AH's readings (with the drift bound and the
reading as first declared beside), for D(n), R_H(n) (only where HS001's ratio rule resolves the reference) and the
floor Q(rewrite) - Q(erased). The basins reading: the replicate-concordance excess at 1,024 for rewrite
and foreign against the founder-free arms.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
sys.dont_write_bytecode = True

from hs001 import analyze as A1  # noqa: E402
from hs001.sim import own_scores  # noqa: E402
from hs002 import design as D, fit as F  # noqa: E402


def load(root):
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    blocks = list(M["blocks"])
    d1 = A1.load(D.SOURCE_ROOT[M["stage"]])
    idx = [d1["blocks"].index(b) for b in blocks]
    z0 = np.load(root / "shards" / f"{blocks[0]}.npz")
    m0 = json.loads(str(z0["__meta__"]))
    factors = tuple(m0["factors"])
    out = {"blocks": blocks, "manifest": M, "factors": factors, "checkpoints": list(d1["checkpoints"]) + list(m0["checkpoints"]),
           "formation_qualified": d1["formation_qualified"][idx]}
    for f in factors:
        zs = [np.load(root / "shards" / f"{b}.npz") for b in blocks]
        for z, b in zip(zs, blocks):
            m = json.loads(str(z["__meta__"]))
            assert m["block"] == b and m["design_digest"] == M["design_digest"] and tuple(m["lineage"]) == D.LINEAGE
        ck2 = np.stack([100 * own_scores(z[f"f{f}/ck_scores"]) for z in zs])
        g2 = np.stack([100 * own_scores(z[f"f{f}/g_scores"]) for z in zs])
        cs = np.stack([100 * z[f"f{f}/conc_same"] for z in zs]); cc = np.stack([100 * z[f"f{f}/conc_cross"] for z in zs])
        rs = np.stack([z[f"f{f}/corr_same"] for z in zs]); rc = np.stack([z[f"f{f}/corr_cross"] for z in zs])
        sd = np.stack([z[f"f{f}/field_sd"] for z in zs])
        a = d1[f]
        cat = lambda x, y: np.concatenate([x[idx], y], 1)
        out[f] = {"ck": cat(a["ck"], ck2), "pr": a["pr"][idx], "g": cat(a["g"], g2), "conc": cat(a["conc"], cs - cc),
                  "conc_same": cat(a["conc_same"], cs), "conc_cross": cat(a["conc_cross"], cc), "corr": cat(a["corr"], rs - rc),
                  "field_sd": cat(a["field_sd"], sd)}
        if "S" in a:
            out[f]["S"] = cat(a["S"], np.stack([100 * own_scores(z[f"f{f}/ck_sign_scores"]) for z in zs]))
            out[f]["A"] = cat(a["A"], np.stack([100 * z[f"f{f}/ck_amp"] for z in zs]))
            out[f]["pS"], out[f]["pA"] = a["pS"][idx], a["pA"][idx]
    return out


def basins(g, C):
    i = C.index(1024)
    ex = {arm: g[f"conc_{arm}"]["ci95"][i] for arm in D.LINEAGE}
    kept = ex["rewrite"][0] > 0 and ex["foreign"][0] > 0 and all(ex[a][0] <= 0 <= ex[a][1] for a in ("erased", "background"))
    mixed = ex["rewrite"][0] <= 0 <= ex["rewrite"][1] or ex["foreign"][0] <= 0 <= ex["foreign"][1]
    return "basins kept to 1,024" if kept else "replicates mixed by 1,024" if mixed else "neither reading"


def analyze(root, do_fit=True):
    d = load(root)
    nb = len(d["blocks"])
    sets = A1.boot_sets(nb)
    C = d["checkpoints"]
    S = {"study": D.STUDY, "root": str(root), "blocks": d["blocks"], "n_blocks": nb, "checkpoints": C,
         "design_digest": d["manifest"]["design_digest"], "stage": d["manifest"]["stage"], "factors": list(d["factors"]),
         "formation_qualified": float(d["formation_qualified"].mean()), "units": "percentage points of E014's Q"}
    arrays = {}
    for f in d["factors"]:
        e = A1.endpoints(d, f)
        bm = {k: v.mean(-1) for k, v in e.items()}
        for k, v in e.items():
            arrays[f"f{f}/{k}"] = v
        den = bm["ref"]
        resolved = A1.ci(den[sets].mean(1))[0] >= D.DENOM_MIN_FRACTION * den.mean()
        num = bm["D"]
        rat = num[sets].mean(1) / den[sets].mean(1)[:, None]
        g = {"bytes": {1: 2048, 4: 128}[f], "reference": A1.stat(den, sets), "reference_resolved": bool(resolved),
             "D": A1.stat(num, sets),
             "R_H": {"ratio": (num.mean(0) / den.mean()).tolist(), "ci95": [A1.ci(rat[:, k]) for k in range(len(C))],
                     "reported_as_ratio": bool(resolved)}}
        for k in ("rewrite_minus_erased", "rewrite_minus_background", "foreign_minus_erased", "foreign_minus_background",
                  "deficit") + tuple(f"Q_{a}" for a in D.LINEAGE) + tuple(f"conc_{a}" for a in D.LINEAGE) + tuple(f"corr_{a}" for a in D.LINEAGE):
            g[k] = A1.stat(bm[k], sets)
        for k in ("S_D", "A_D"):
            if k in bm:
                g[k] = A1.stat(bm[k], sets)
        g["G_D"] = {"mean": bm["G_D"].mean(0).tolist()}
        g["basins"] = basins(g, C)
        if do_fit:
            g["fit_D"] = F.summarise(num.mean(0), num[sets].mean(1), C)
            g["fit_R_H"] = F.summarise(num.mean(0) / den.mean(), num[sets].mean(1) / den[sets].mean(1)[:, None], C)
            if not resolved:                            # HS001's ratio rule: no ratio reading without a resolved reference
                for k in ("reading", "reading_declared"):
                    g["fit_R_H"][k] = "not read: the reference is not resolved (HS001's ratio rule)"
                g["fit_R_H"]["reasons"] = g["fit_R_H"]["reasons_declared"] = []
            fl = bm["rewrite_minus_erased"]
            g["fit_floor"] = F.summarise(fl.mean(0), fl[sets].mean(1), C)
        S[str(f)] = g
    return S, arrays


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--no-fit", action="store_true")
    a = ap.parse_args()
    out = a.out or (a.root.parent / f"{a.root.name}_read")
    out.mkdir(parents=True, exist_ok=True)
    S, arrays = analyze(a.root, not a.no_fit)
    (out / "summary.json").write_text(json.dumps(S, indent=1) + "\n")
    np.savez_compressed(out / "arrays.npz", **arrays)
    print(f"-> {out}/summary.json, arrays.npz")


if __name__ == "__main__":
    main()
