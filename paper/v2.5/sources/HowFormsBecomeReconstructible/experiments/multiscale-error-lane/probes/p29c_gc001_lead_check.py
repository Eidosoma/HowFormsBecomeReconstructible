"""P29c (python probes/p29c_gc001_lead_check.py ROOT): the lead's check of GC001's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written and run by the lead after the development read,
29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_GC001.md from the registration's words (not from
gc001.predict / gc001.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/gc001/development). Output: probes/results/p29c_gc001_lead_check.txt.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
ROOT = Path(sys.argv[1])
M = json.load(open(ROOT / "manifest.json"))
bad = []
for key, t in M["tasks"].items():
    for kind in ("shards", "raw"):
        f = t["files"][kind]
        if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            bad.append(f["path"])
print("tasks", len(M["tasks"]), "files checked", 2 * len(M["tasks"]), "sha256 mismatches", bad, "digest", M["design_digest"][:12])

BLOCKS = list(range(*M["blocks"]))
UNITS = sorted(p.name for p in (ROOT / "shards" / "G").iterdir())
PAIRS = [(u, b) for u in UNITS for b in ("dw", "li4")]
ARMS = ["cue", "bio-1", "bio-1.5", "bio-2", "bio-3"]
READS = [250, 1000, 2000, 4000]
Z = {(u, k): np.load(ROOT / "shards" / "G" / u / f"{k}.npz") for u in UNITS for k in BLOCKS}
SM = json.load(open(LANE / "gc001" / "frozen" / "static_map.json"))
nm = lambda s, sg: f"{s}@{sg:g}"


def v(u, b, run, arm, e="r_all"):
    ai = ARMS.index(arm)
    out = []
    for k in BLOCKS:
        x = Z[(u, k)][f"{b}/{run}/{e}"]
        out.append(x[ai].mean() if x.ndim == 2 else x[READS.index(4000), ai].mean())
    return np.array(out)


loss = lambda u, b, run, arm, e="r_all": v(u, b, run, "cue", e) - v(u, b, run, arm, e)
F0 = [p for p in PAIRS if p[0].startswith("F0")]
SL = [p for p in PAIRS if not p[0].startswith("F0")]
res = {}


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f] pos %d/%d" % (m, m - h, m + h, (x > 0).sum(), len(x))


def every(name, items, thr, sense):
    ms = {k: x.mean() for k, x in items.items()}
    ok = all({"ge": m >= thr, "le": m <= thr, "abs": abs(m) <= thr}[sense] for m in ms.values())
    res.setdefault(name.split()[0], []).append(ok)
    print(f"{name:52s} {min(ms.values()):+.6f}..{max(ms.values()):+.6f}  every item {sense} {thr}  {'ok' if ok else 'MISS'}")


def pooled(name, items, thr, sense):
    x = np.mean(list(items.values()), 0)
    m = x.mean()
    ok = {"ge": m >= thr, "le": m <= thr, "abs": abs(m) <= thr}[sense]
    res.setdefault(name.split()[0], []).append(ok)
    print(f"{name:52s} {ci(x)}  pooled {sense} {thr}  {'ok' if ok else 'MISS'}")


print("\n== statements (t = 4,000)")
every("G1 bio-3 - cue r_all, none8@0.5 and @1", {(p, s): -loss(*p, nm("none8", s), "bio-3") for p in PAIRS for s in (0.5, 1)}, 0.003, "abs")
every("G2 bio-1 loss none8@1", {p: loss(*p, nm("none8", 1), "bio-1") for p in PAIRS}, 0.003, "ge")
pooled("G2 pooled", {p: loss(*p, nm("none8", 1), "bio-1") for p in PAIRS}, 0.03, "ge")
pooled("G2 sigma 2 - sigma 1", {p: loss(*p, nm("none8", 2), "bio-1") - loss(*p, nm("none8", 1), "bio-1") for p in PAIRS}, 0.08, "ge")
for a1, a2 in (("bio-1.5", "bio-1"), ("bio-2", "bio-1.5"), ("bio-3", "bio-2")):
    pooled(f"G3 none8@2 {a1} - {a2}", {p: v(*p, nm("none8", 2), a1) - v(*p, nm("none8", 2), a2) for p in PAIRS}, 0.02, "ge")
pooled("G4 F0 graded - scatter (bio-1, 1.5; sigma 2, 3)", {(p, a, s): v(*p, nm("none8", s), a) - v(*p, nm("scatter8", s), a) for p in F0 for a in ("bio-1", "bio-1.5") for s in (2, 3)}, -0.006, "le")
pooled("G5 S4/LB graded - scatter (bio-1; sigma 1, 2)", {(p, s): v(*p, nm("none8", s), "bio-1") - v(*p, nm("scatter8", s), "bio-1") for p in SL for s in (1, 2)}, 0.008, "abs")
every("G6 band loss - interior loss, none8@1", {p: loss(*p, nm("none8", 1), "bio-1", "r_band") - loss(*p, nm("none8", 1), "bio-1", "r_int") for p in PAIRS}, 0.03, "ge")
every("G7 walls bio-1 - cue, none8@1", {p: v(*p, nm("none8", 1), "bio-1", "walls") - v(*p, nm("none8", 1), "cue", "walls") for p in PAIRS}, 0.09, "ge")
every("G8 F0 bio-1 r_in change4@0 - change4@2", {p: v(*p, nm("change4", 0), "bio-1", "r_in") - v(*p, nm("change4", 2), "bio-1", "r_in") for p in F0}, 0.15, "ge")
pooled("G9 cue r_in memory4@0 - memory4@2", {p: v(*p, nm("memory4", 0), "cue", "r_in") - v(*p, nm("memory4", 2), "cue", "r_in") for p in PAIRS}, 0.02, "ge")
ratios = []
for pt in ("S4", "LB", "F0"):
    for s in (0.5, 1, 2):
        for a in ("bio-1", "bio-1.5", "bio-2", "bio-3"):
            sh = SM["patterns"][pt]["sigmas"][f"{s:g}"]["trigger"][f"graded/{a}"]["all"]
            if sh >= 0.02:
                lo = np.mean([loss(*p, nm("none8", s), a).mean() for p in PAIRS if p[0].startswith(pt)])
                ratios.append((pt, s, a, round(float(sh), 4), round(float(lo / sh), 4)))
g10 = all(0.45 <= r[-1] <= 1.35 for r in ratios) and 0.8 <= np.mean([r[-1] for r in ratios]) <= 1.05
res["G10"] = [g10]
print(f"G10 {len(ratios)} items, ratio {min(r[-1] for r in ratios):.4f}..{max(r[-1] for r in ratios):.4f}, mean {np.mean([r[-1] for r in ratios]):.4f}  {'ok' if g10 else 'MISS'}")
print("   ", ratios)
every("G11 bio-3 loss none8@2, S4 and LB", {p: loss(*p, nm("none8", 2), "bio-3") for p in SL}, 0.014, "ge")
every("G11 F0 bio-3 - cue, none8@2 and @3", {(p, s): -loss(*p, nm("none8", s), "bio-3") for p in F0 for s in (2, 3)}, 0.003, "abs")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== pattern means, r_all at t = 4,000 (cue, bio-1, bio-1.5, bio-2, bio-3, bio-1 scattered)")
for pt in ("S4", "LB", "F0"):
    pp = [p for p in PAIRS if p[0].startswith(pt)]
    for s in (0, 0.5, 1, 2, 3):
        row = [np.mean([v(*p, nm("none8", s), a).mean() for p in pp]) for a in ARMS]
        sc = np.mean([v(*p, nm("scatter8", s), "bio-1").mean() for p in pp]) if s > 0 else float("nan")
        mis = np.mean([np.mean([Z[(p[0], k)][f"{p[1]}/{nm('none8', s)}/misread"].mean() for k in BLOCKS]) for p in pp])
        print(f"{pt} sigma {s:3g}: " + " ".join("%.6f" % x for x in row) + "  scattered %.6f  misread/anchor %.4f" % (sc, mis))
print("\n== band and interior losses of bio-1 at sigma 1 (pattern means)")
for pt in ("S4", "LB", "F0"):
    pp = [p for p in PAIRS if p[0].startswith(pt)]
    print(pt, "band %.6f interior %.6f walls bio-1 - cue %.6f" % tuple(np.mean([f(*p).mean() for p in pp]) for f in (
        lambda u, b: loss(u, b, nm("none8", 1), "bio-1", "r_band"), lambda u, b: loss(u, b, nm("none8", 1), "bio-1", "r_int"),
        lambda u, b: v(u, b, nm("none8", 1), "bio-1", "walls") - v(u, b, nm("none8", 1), "cue", "walls"))))
print("\n== adoption and repair (pattern means)")
for pt in ("S4", "LB", "F0"):
    pp = [p for p in PAIRS if p[0].startswith(pt)]
    print(pt, "bio-1 change4 r_in sigma 0/1/2:", " ".join("%.6f" % np.mean([v(*p, nm("change4", s), "bio-1", "r_in").mean() for p in pp]) for s in (0, 1, 2)),
          "| cue memory4 r_in sigma 0/1/2:", " ".join("%.6f" % np.mean([v(*p, nm("memory4", s), "cue", "r_in").mean() for p in pp]) for s in (0, 1, 2)),
          "| bio-3 change4 r_in sigma 0/2:", " ".join("%.6f" % np.mean([v(*p, nm("change4", s), "bio-3", "r_in").mean() for p in pp]) for s in (0, 2)))
print("\n== intervals")
print("G2 pooled", ci(np.mean([loss(*p, nm("none8", 1), "bio-1") for p in PAIRS], 0)))
print("G2 rise", ci(np.mean([loss(*p, nm("none8", 2), "bio-1") - loss(*p, nm("none8", 1), "bio-1") for p in PAIRS], 0)))
print("G4", ci(np.mean([v(*p, nm("none8", s), a) - v(*p, nm("scatter8", s), a) for p in F0 for a in ("bio-1", "bio-1.5") for s in (2, 3)], 0)))
print("G4 bio-1 sigma 2 only", ci(np.mean([v(*p, nm("none8", 2), "bio-1") - v(*p, nm("scatter8", 2), "bio-1") for p in F0], 0)))
print("G5", ci(np.mean([v(*p, nm("none8", s), "bio-1") - v(*p, nm("scatter8", s), "bio-1") for p in SL for s in (1, 2)], 0)))
print("G9", ci(np.mean([v(*p, nm("memory4", 0), "cue", "r_in") - v(*p, nm("memory4", 2), "cue", "r_in") for p in PAIRS], 0)))
print("committed share at sigma 1 and 2 (pattern means):", {(pt, s, a): round(float(np.mean([v(*p, nm("none8", s), a, "opened").mean() for p in PAIRS if p[0].startswith(pt)])), 4)
                                                             for pt in ("S4", "LB", "F0") for s in (1, 2) for a in ("bio-1", "bio-3")})
print("done")
