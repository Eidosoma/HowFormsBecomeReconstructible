"""Reader: python -m or001.analyze --root RUN_ROOT --selection SEL_ROOT --out OUT_DIR

Evolved genes per environment and seed; development retention (body qualified agreement averaged
over generations 1..G_READ, per block, then summarised over blocks with a 95% t interval) of every
genome; paired contrasts of the evolved genomes against the references; the registered statements.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.stats import t as student

from or001 import design as O

FROZEN = Path(__file__).resolve().parent / "frozen"
SHORT = {"BENEFIT": "B", "HARM": "H", "NO MEANINGFUL DIFFERENCE": "=", "UNDECIDED": "?"}
PAIRS = (("evolved_s0", "native_hold"), ("evolved_s1", "native_hold"), ("evolved_s0", "none"),
         ("native_copy", "native_hold"), ("native_reciprocal", "native_hold"), ("native_hold", "none"),
         ("evolved_s0", "evolved_s1"))


def interval(b):
    nb = len(b)
    point = float(b.mean())
    half = float(student.ppf(0.975, nb - 1) * b.std(ddof=1) / np.sqrt(nb))
    return point, point - half, point + half


def reading(lo, hi):
    if lo > 0:
        return "BENEFIT"
    if hi < 0:
        return "HARM"
    if lo >= -O.MARGIN and hi <= O.MARGIN:
        return "NO MEANINGFUL DIFFERENCE"
    return "UNDECIDED"


def retention(arr, gi):
    """(blocks,) mean body qualified agreement over generations 1.. for genome gi."""
    return arr["v_qual"][:, 1:, gi].mean((1, 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    genes, rows, levels = {}, [], {}
    for e in O.ENV:
        genes[e] = {f"s{s}": json.loads((a.selection / "selection" / f"{e}_s{s}.json").read_text())["evolved_genes"]
                    for s in O.SEEDS}
        arr = dict(np.load(a.root / "read" / f"{e}.npz"))
        names = [str(x) for x in arr["genomes"]]
        levels[e] = {n: round(float(retention(arr, i).mean()), 4) for i, n in enumerate(names)}
        levels[e]["generation_curve"] = {n: [round(float(v), 4) for v in arr["v_qual"][:, :, i].mean((0, 2))]
                                         for i, n in enumerate(names)}
        for x, y in PAIRS:
            p, lo, hi = interval(retention(arr, names.index(x)) - retention(arr, names.index(y)))
            rows.append({"env": e, "arm": x, "ref": y, "point": p, "lo": lo, "hi": hi, "reading": reading(lo, hi)})
    with open(a.out / "genes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["env", "seed", *O.GENES])
        for e, d in genes.items():
            for s, g in d.items():
                w.writerow([e, s, *(f"{g[k]:.5f}" for k in O.GENES)])
    with open(a.out / "contrasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["env", "arm", "ref", "point", "lo", "hi", "reading"])
        for r in rows:
            w.writerow([r["env"], r["arm"], r["ref"], f"{r['point']:.4f}", f"{r['lo']:.4f}", f"{r['hi']:.4f}", SHORT[r["reading"]]])
    scored = score(genes, rows)
    (a.out / "statements_scored.json").write_text(json.dumps(scored, indent=1) + "\n")
    (a.out / "summary.json").write_text(json.dumps({"genes": genes, "retention": levels}, separators=(",", ":")) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in scored.items()}, indent=1))


def score(genes, rows):
    mean = lambda e, g: float(np.mean([genes[e][f"s{s}"][g] for s in O.SEEDS]))
    total = lambda e: mean(e, "g_site") + mean(e, "g_region") + mean(e, "g_sheet")
    name = lambda f, s, i, c: O.Env(f, s, i, c).name
    out = {}
    cells = [(f, i) for f in O.FAMILIES for i in O.INJURIES]
    hits = [total(name(f, 0.3, i, 0.05)) > total(name(f, 0.05, i, 0.05)) for f, i in cells]
    out["OS1a"] = {"verdict": "HOLDS" if sum(hits) >= 7 else "FAILS", "cells_hit": int(sum(hits)), "cells": len(cells),
                   "total_gain": {f"{f}_{i}": [round(total(name(f, s, i, 0.05)), 4) for s in O.SIGMAS] for f, i in cells}}
    dev = [mean(name(f, 0.05, i, 0.05), "m_dev") > 1.0 for f, i in cells]
    out["OS1b"] = {"verdict": "HOLDS" if sum(dev) >= 6 else "FAILS", "cells_hit": int(sum(dev)),
                   "m_dev": {f"{f}_{i}": round(mean(name(f, 0.05, i, 0.05), "m_dev"), 4) for f, i in cells}}
    c2 = [(f, s, i, c) for f in O.FAMILIES for s in (0.15, 0.3) for i in ("none", "body") for c in O.LAMBDAS]
    w = [mean(name(*x), "w") > 0.5 for x in c2]
    out["OS2"] = {"verdict": "HOLDS" if sum(w) >= 14 else "FAILS", "cells_hit": int(sum(w)), "cells": len(c2),
                  "w": {name(*x): round(mean(name(*x), "w"), 4) for x in c2}}
    c3 = [(f, s, i, c) for f in O.FAMILIES for s in O.SIGMAS for i in ("none", "body") for c in O.LAMBDAS]
    low = [mean(name(*x), "rho_w") < 0.002 for x in c3]
    pairs = [(f, s, c) for f in O.FAMILIES for s in O.SIGMAS for c in O.LAMBDAS]
    up = [mean(name(f, s, "record", c), "rho_w") > mean(name(f, s, "none", c), "rho_w") for f, s, c in pairs]
    out["OS3"] = {"verdict": "HOLDS" if np.mean(low) >= 0.75 and np.mean(up) >= 0.75 else "FAILS",
                  "low_fraction": round(float(np.mean(low)), 3), "record_above_none_fraction": round(float(np.mean(up)), 3)}
    c4 = [("BL", s, i, c) for s in (0.15, 0.3) for i in O.INJURIES for c in O.LAMBDAS]
    fine = [mean(name(*x), "g_site") > max(mean(name(*x), "g_region"), mean(name(*x), "g_sheet")) for x in c4]
    out["OS4"] = {"verdict": "HOLDS" if np.mean(fine) >= 0.75 else "FAILS", "fraction": round(float(np.mean(fine)), 3)}
    ok = [r["point"] >= -O.MARGIN for r in rows if r["ref"] == "native_hold" and r["arm"].startswith("evolved")]
    out["OS5"] = {"verdict": "HOLDS" if np.mean(ok) >= 0.9 else "FAILS", "fraction": round(float(np.mean(ok)), 3), "genomes": len(ok)}
    return out


if __name__ == "__main__":
    main()
