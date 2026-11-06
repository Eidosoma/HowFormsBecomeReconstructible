"""HS001's reader: python -m hs001.analyze ROOT [--out DIR] [--no-fit]  ->  DIR/summary.json and DIR/arrays.npz.

Every value is E014's observer (qualified agreement against the own founder's prototype), in percent, from the shards:
per block the mean over 4 founders x 2 recipient lineages; the lineage-level values are kept for the lane's SD rule.
- D(n) = Q(rewrite) - Q(foreign) after n rewrites; the reference Delta_P = Q(copy) - Q(copy_foreign);
  R_H(n) = mean_b D_b(n) / mean_b Delta_P,b (the ratio of block averages);
- floors Q(rewrite) - Q(erased), Q(rewrite) - Q(background), Q(foreign) - Q(erased), Q(foreign) - Q(background);
  E014's protected-copy deficit Q(rewrite) - Q(copy);
- the replicate-concordance excess: same-founder less cross-founder sign agreement (and correlation) of the decoded
  records, per founder, then per block;
- the lineage reads G1-G256;
- intervals: 10,000 whole-block resamples with E014's generator rng("E014", "bootstrap").integers(0, NB, (10000, NB)),
  the ratio's numerator and denominator over the same resampled blocks; the reference's ratio reported only if its
  95% lower bound is at least half its estimate;
- the asymptote (hs001.fit) on the D curve and the R_H curve at each budget.
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

from hs001 import design as D, fit as F  # noqa: E402
from hs001.sim import own_scores, rng  # noqa: E402

A = {a: i for i, a in enumerate(D.LINEAGE)}
P = {p: i for i, p in enumerate(D.PROBES)}


def load(root):
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    blocks = list(M["blocks"])
    out = {"blocks": blocks, "manifest": M}
    for f in D.FACTORS:
        ck, pr, g, cs, cc, rs, rc, sd = [], [], [], [], [], [], [], []
        for b in blocks:
            z = np.load(root / "shards" / f"{b}.npz")
            m = json.loads(str(z["__meta__"]))
            assert m["block"] == b and m["design_digest"] == M["design_digest"] and tuple(m["lineage"]) == D.LINEAGE
            ck.append(100 * own_scores(z[f"f{f}/ck_scores"]))                     # (C, 4, 2, A)
            pr.append(100 * own_scores(z[f"f{f}/probe_scores"][None])[0])         # (4, 2, P)
            g.append(100 * own_scores(z[f"f{f}/g_scores"]))                       # (H, 4, 2, A)
            cs.append(100 * z[f"f{f}/conc_same"]); cc.append(100 * z[f"f{f}/conc_cross"])   # (C, 4, A)
            rs.append(z[f"f{f}/corr_same"]); rc.append(z[f"f{f}/corr_cross"])
            sd.append(z[f"f{f}/field_sd"])                                        # (C, 4, 2, A)
        out[f] = {"ck": np.stack(ck), "pr": np.stack(pr), "g": np.stack(g), "conc": np.stack(cs) - np.stack(cc),
                  "conc_same": np.stack(cs), "conc_cross": np.stack(cc), "corr": np.stack(rs) - np.stack(rc),
                  "field_sd": np.stack(sd)}
        z0 = np.load(root / "shards" / f"{blocks[0]}.npz")
        if f"f{f}/ck_sign_scores" in z0.files:          # E014's sign-only and amplitude outcomes (not in P49's shards)
            zs = [np.load(root / "shards" / f"{b}.npz") for b in blocks]
            out[f]["S"] = np.stack([100 * own_scores(z[f"f{f}/ck_sign_scores"]) for z in zs])
            out[f]["A"] = np.stack([100 * z[f"f{f}/ck_amp"] for z in zs])
            out[f]["pS"] = np.stack([100 * own_scores(z[f"f{f}/probe_sign_scores"][None])[0] for z in zs])
            out[f]["pA"] = np.stack([100 * z[f"f{f}/probe_amp"] for z in zs])
    q = [np.load(root / "shards" / f"{b}.npz")["formation_qualified"] for b in blocks]
    out["formation_qualified"] = np.stack(q)
    out["checkpoints"] = list(json.loads(str(np.load(root / "shards" / f"{blocks[0]}.npz")["__meta__"]))["checkpoints"])
    return out


def lineages(x):
    """(NB, ..., 4, 2) -> (NB, ..., 8): the eight lineages of a block."""
    return x.reshape(*x.shape[:-2], 8)


def endpoints(d, f):
    """Lineage-level arrays (NB, [C,] 8) of every named endpoint at budget f."""
    ck, pr = d[f]["ck"], d[f]["pr"]
    L = lambda arm: lineages(np.moveaxis(ck[..., A[arm]], 1, 1))                  # (NB, C, 8)
    Pl = lambda p: lineages(pr[..., P[p]])                                         # (NB, 8)
    e = {"D": L("rewrite") - L("foreign"), "ref": Pl("copy") - Pl("copy_foreign"),
         "rewrite_minus_erased": L("rewrite") - L("erased"), "rewrite_minus_background": L("rewrite") - L("background"),
         "foreign_minus_erased": L("foreign") - L("erased"), "foreign_minus_background": L("foreign") - L("background"),
         "deficit": L("rewrite") - Pl("copy")[:, None, :]}
    for arm in D.LINEAGE:
        e[f"Q_{arm}"] = L(arm)
    for p in D.PROBES:
        e[f"Q_{p}"] = Pl(p)
    for arm in D.LINEAGE:
        e[f"conc_{arm}"] = d[f]["conc"][..., A[arm]]                               # (NB, C, 4): founders
        e[f"corr_{arm}"] = d[f]["corr"][..., A[arm]]
    g = d[f]["g"]
    e["G_D"] = lineages(g[..., A["rewrite"]] - g[..., A["foreign"]])                # (NB, H, 8)
    if "S" in d[f]:                                                                # the preserved outcomes, reported
        for name, x, px in (("S", d[f]["S"], d[f]["pS"]), ("A", d[f]["A"], d[f]["pA"])):
            for arm in ("rewrite", "foreign"):
                e[f"{name}_{arm}"] = lineages(x[..., A[arm]])
            e[f"{name}_D"] = lineages(x[..., A["rewrite"]] - x[..., A["foreign"]])
            e[f"{name}_ref"] = lineages(px[..., P["copy"]] - px[..., P["copy_foreign"]])
    return e


def boot_sets(nb):
    return rng("E014", "bootstrap").integers(0, nb, (D.BOOT, nb))


def ci(x):
    return [float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))]


def stat(block_values, sets):
    """mean, 95% whole-block interval, block SD, positive blocks: for (NB,) or (NB, K) block values."""
    v = np.asarray(block_values, float)
    bs = v[sets].mean(1)
    if v.ndim == 1:
        return {"mean": float(v.mean()), "ci95": ci(bs), "block_sd": float(v.std(ddof=1)), "positive_blocks": int((v > 0).sum())}
    return {"mean": v.mean(0).tolist(), "ci95": [ci(bs[:, k]) for k in range(v.shape[1])],
            "block_sd": v.std(0, ddof=1).tolist()}


def analyze(root, do_fit=True):
    d = load(root)
    nb = len(d["blocks"])
    sets = boot_sets(nb)
    C = d["checkpoints"]
    S = {"study": D.STUDY, "root": str(root), "blocks": d["blocks"], "n_blocks": nb, "checkpoints": C,
         "design_digest": d["manifest"]["design_digest"], "stage": d["manifest"]["stage"],
         "formation_qualified": float(d["formation_qualified"].mean()), "units": "percentage points of E014's Q"}
    arrays = {}
    for f in D.FACTORS:
        e = endpoints(d, f)
        bm = {k: v.mean(-1) for k, v in e.items()}                                   # block means
        for k, v in e.items():
            arrays[f"f{f}/{k}"] = v
        den = bm["ref"]
        dlo = ci(den[sets].mean(1))[0]
        resolved = dlo >= D.DENOM_MIN_FRACTION * den.mean()
        num = bm["D"]                                                                # (NB, C)
        rat = num[sets].mean(1) / den[sets].mean(1)[:, None]                        # (BOOT, C)
        g = {"bytes": D.BYTES[f], "reference": stat(den, sets), "reference_resolved": bool(resolved),
             "D": stat(num, sets),
             "R_H": {"ratio": (num.mean(0) / den.mean()).tolist(), "ci95": [ci(rat[:, k]) for k in range(len(C))],
                     "reported_as_ratio": bool(resolved)}}
        for k in ("rewrite_minus_erased", "rewrite_minus_background", "foreign_minus_erased", "foreign_minus_background",
                  "deficit") + tuple(f"Q_{a}" for a in D.LINEAGE):
            g[k] = stat(bm[k], sets)
        for p in D.PROBES:
            g[f"Q_{p}"] = stat(bm[f"Q_{p}"], sets)
        for arm in D.LINEAGE:
            g[f"conc_{arm}"] = stat(bm[f"conc_{arm}"], sets)
            g[f"corr_{arm}"] = stat(bm[f"corr_{arm}"], sets)
        for k in ("S_rewrite", "S_foreign", "S_D", "S_ref", "A_rewrite", "A_foreign", "A_D", "A_ref"):
            if k in bm:
                g[k] = stat(bm[k], sets)
        g["G_D"] = {"mean": bm["G_D"].mean(0).tolist()}
        g["G_Q"] = {arm: d[f]["g"][..., A[arm]].mean((0, 2, 3)).tolist() for arm in D.LINEAGE}
        i1, i16 = C.index(1), C.index(16) if 16 in C else None
        if i16 is not None:
            g["D16_minus_D1"] = stat(num[:, i16] - num[:, i1], sets)
        if do_fit and len(C) == len(D.CHECKPOINTS):
            curve, boot = num.mean(0), num[sets].mean(1)
            g["fit_D"] = F.summarise(curve, boot)
            g["fit_R_H"] = F.summarise(curve / den.mean(), boot / den[sets].mean(1)[:, None])
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
