"""P28c (python probes/p28c_be004_lead_check.py ROOT): the lead's check of BE004's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written and run by the lead after the development read,
29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_BE004.md from the registration's words (not from
be004.predict / be004.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be004/development). Output: probes/results/p28c_be004_lead_check.txt.
"""
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from be004 import design as D  # noqa: E402  (run names, arms and reads only)

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
PAIRS = [(u, b) for u in D.UNITS for b in ("dw", "li4")]
ARMS = {D.run_name(*r[:3]): list(r[3]) for r in D.RUNS}
READS = list(D.READS)
Z = {(u, b, k): np.load(ROOT / "shards" / b / u / f"{k}.npz") for u, b in PAIRS for k in BLOCKS}
SM = json.load(open(LANE / "be004" / "frozen" / "static_map.json"))
K = 3 * np.sqrt(1 / 4 + 1 / 16)


def v(u, b, run, arm, e="r_in", t=4000):
    """(16,) block means (over the 8 cases) of endpoint e of arm in run at read t."""
    ai = ARMS[run].index(arm)
    out = []
    for k in BLOCKS:
        x = Z[(u, b, k)][f"{run}/{e}"]
        out.append(x[ai].mean() if x.ndim == 2 else x[READS.index(t), ai].mean())
    return np.array(out)


def anc(u, b, run, arm, t):
    """Share of the patch's anchored cells whose record is right, per block (right over all)."""
    ai = ARMS[run].index(arm)
    return np.array([Z[(u, b, k)][f"{run}/n_anc_ok"][READS.index(t), ai].mean() / Z[(u, b, k)][f"{run}/n_anc"].mean() for k in BLOCKS])


def P(f):
    """Pooled per-block values: the mean over the twelve unit-body pairs."""
    return np.mean([f(u, b) for u, b in PAIRS], 0)


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f] pos %d/%d" % (m, m - h, m + h, (x > 0).sum(), len(x))


M_ = lambda d: f"memory4@{d}"
C, Q = "change4@0", "cue4@0"
cost = lambda u, b, arm: v(u, b, Q, "bio-3", "r_all") - v(u, b, Q, arm, "r_all")
res = {}


def part(name, x, thr, sense):
    m = x.mean()
    ok = {"ge": m >= thr, "le": m <= thr, "abs": abs(m) <= thr}[sense]
    res.setdefault(name.split()[0], []).append(bool(ok))
    print(f"{name:44s} {ci(x)}  rule {sense} {thr}  {'ok' if ok else 'MISS'}")


print("\n== statements (pooled over the twelve unit-body pairs; t = 4,000 unless named)")
part("E1 dial@50 - dial@0", P(lambda u, b: v(u, b, M_(50), "dial") - v(u, b, M_(0), "dial")), 0.015, "abs")
part("E1 dial@100 - dial@0", P(lambda u, b: v(u, b, M_(100), "dial") - v(u, b, M_(0), "dial")), -0.05, "le")
part("E1 dial@1000 - dial@0", P(lambda u, b: v(u, b, M_(1000), "dial") - v(u, b, M_(0), "dial")), -0.05, "le")
part("E1 dial@1000 - dial@250", P(lambda u, b: v(u, b, M_(1000), "dial") - v(u, b, M_(250), "dial")), 0.02, "abs")
for d in (50, 100, 250, 500, 1000):
    part(f"E2 hold@{d} - dial@0", P(lambda u, b, d=d: v(u, b, M_(d), "dial-hold") - v(u, b, M_(0), "dial")), 0.02, "abs")
part("E3 hold@1000 - dial@1000", P(lambda u, b: v(u, b, M_(1000), "dial-hold") - v(u, b, M_(1000), "dial")), 0.05, "ge")
part("E4 anc_right dial@50 at t=50", P(lambda u, b: anc(u, b, M_(50), "dial", 50)), 0.01, "le")
part("E4 anc_right dial@100 at t=100", P(lambda u, b: anc(u, b, M_(100), "dial", 100)), 0.2, "ge")
part("E4 anc_right hold@1000 at t=1000", P(lambda u, b: anc(u, b, M_(1000), "dial-hold", 1000)), 0.01, "le")
part("E4 onset dial@0 - dial@1000", P(lambda u, b: v(u, b, M_(0), "dial", "onset") - v(u, b, M_(1000), "dial", "onset")), 0.1, "ge")
part("E4 onset hold@1000 - dial@0", P(lambda u, b: v(u, b, M_(1000), "dial-hold", "onset") - v(u, b, M_(0), "dial", "onset")), 0.03, "abs")
part("E5 r_in at t=1000, dial - hold", P(lambda u, b: v(u, b, M_(1000), "dial", "r_in", 1000) - v(u, b, M_(1000), "dial-hold", "r_in", 1000)), 0.05, "ge")
part("E5 v_in at t=1000, dial - hold", P(lambda u, b: v(u, b, M_(1000), "dial", "v_in", 1000) - v(u, b, M_(1000), "dial-hold", "v_in", 1000)), 0.03, "ge")
part("E6 late sham r_all hold - dial", P(lambda u, b: v(u, b, "cue4@1000", "dial-hold", "r_all") - v(u, b, "cue4@1000", "dial", "r_all")), 0.002, "abs")
part("P1 s2 - dial", P(lambda u, b: v(u, b, C, "dial-s2") - v(u, b, C, "dial")), 0.03, "abs")
part("P1 dial - s4", P(lambda u, b: v(u, b, C, "dial") - v(u, b, C, "dial-s4")), 0.1, "ge")
part("P1 s4 - s6", P(lambda u, b: v(u, b, C, "dial-s4") - v(u, b, C, "dial-s6")), 0.05, "ge")
part("P2 d4 - dial", P(lambda u, b: v(u, b, C, "dial-d4") - v(u, b, C, "dial")), 0.01, "abs")
part("P2 d8 - dial", P(lambda u, b: v(u, b, C, "dial-d8") - v(u, b, C, "dial")), 0.01, "abs")
part("P2 dial - d0", P(lambda u, b: v(u, b, C, "dial") - v(u, b, C, "dial-d0")), 0.02, "ge")
part("P3 cost dial - d0", P(lambda u, b: cost(u, b, "dial") - cost(u, b, "dial-d0")), 0.002, "ge")
part("P3 cost d4 - dial", P(lambda u, b: cost(u, b, "dial-d4") - cost(u, b, "dial")), 0.003, "ge")
part("P3 cost d8 - d4", P(lambda u, b: cost(u, b, "dial-d8") - cost(u, b, "dial-d4")), 0.012, "ge")
part("P4 dial - w1.5", P(lambda u, b: v(u, b, C, "dial") - v(u, b, C, "dial-w1.5")), 0.1, "ge")
part("P4 w1.5 - w2", P(lambda u, b: v(u, b, C, "dial-w1.5") - v(u, b, C, "dial-w2")), 0.07, "ge")
part("P4 cost dial - w1.5", P(lambda u, b: cost(u, b, "dial") - cost(u, b, "dial-w1.5")), 0.001, "ge")
for a in ("dial-f0.5", "dial-f0.25"):
    part(f"P5 {a} - dial adoption", P(lambda u, b, a=a: v(u, b, C, a) - v(u, b, C, "dial")), 0.005, "abs")
    part(f"P5 {a} - dial cost", P(lambda u, b, a=a: cost(u, b, a) - cost(u, b, "dial")), 0.001, "abs")
for a in ("dial-t1", "dial-t10", "dial-t100"):
    part(f"P6 {a} - dial adoption", P(lambda u, b, a=a: v(u, b, C, a) - v(u, b, C, "dial")), 0.005, "abs")
    part(f"P6 {a} - dial cost", P(lambda u, b, a=a: cost(u, b, a) - cost(u, b, "dial")), 0.001, "abs")
st = SM["adoption"] if isinstance(SM["adoption"], dict) else eval(SM["adoption"])
SARMS = ["bio-1", "bio-3", "dial", "dial-s2", "dial-s4", "dial-s6", "dial-d0", "dial-d4", "dial-d8", "dial-w1.5", "dial-w2"]
for gap in (0.15, 0.05):
    items = [(a1, a2) for a1, a2 in itertools.permutations(SARMS, 2) if st[a1] - st[a2] >= gap]
    runs = [P(lambda u, b, a1=a1, a2=a2: v(u, b, C, a1) - v(u, b, C, a2)).mean() for a1, a2 in items]
    ok = all(r >= 0 for r in runs)
    if gap == 0.15:
        res.setdefault("P7", []).append(ok)
    print(f"P7 static gap >= {gap}: {len(items)} pairs, smallest run gap {min(runs):+.4f}, {'all in order' if ok else 'NOT all in order'}")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== per-pair ranges and extra numbers")
for d in (50, 100, 250, 500, 1000):
    x = [(v(u, b, M_(d), "dial") - v(u, b, M_(0), "dial")).mean() for u, b in PAIRS]
    y = [(v(u, b, M_(d), "dial-hold") - v(u, b, M_(0), "dial")).mean() for u, b in PAIRS]
    print(f"delay {d:4d}: late - prompt per pair {min(x):+.4f}..{max(x):+.4f} | held - prompt per pair {min(y):+.4f}..{max(y):+.4f}")
rec = [(v(u, b, M_(1000), "dial-hold") - v(u, b, M_(1000), "dial")).mean() for u, b in PAIRS]
print("E3 per pair", " ".join("%+.4f" % x for x in rec), "| pairs:", PAIRS)
print("held anc_right over the wait (pooled):", {t: round(float(P(lambda u, b, t=t: anc(u, b, M_(1000), "dial-hold", t)).mean()), 4) for t in (50, 100, 250, 500, 1000)})
print("plain anc_right over the wait (pooled):", {t: round(float(P(lambda u, b, t=t: anc(u, b, M_(1000), "dial", t)).mean()), 4) for t in (50, 100, 250, 500, 1000)})
print("held record in the patch over the wait (pooled):", {t: round(float(P(lambda u, b, t=t: v(u, b, M_(1000), "dial-hold", "r_in", t)).mean()), 4) for t in (50, 100, 250, 500, 1000)})
print("onset (pooled): prompt %.4f, late 1000 %.4f, held 1000 %.4f" % tuple(P(lambda u, b, r=r, a=a: v(u, b, r, a, "onset")).mean() for r, a in ((M_(0), "dial"), (M_(1000), "dial"), (M_(1000), "dial-hold"))))
print("E5 levels at t=1000 (pooled): record plain %.4f held %.4f | body plain %.4f held %.4f" % tuple(
    P(lambda u, b, a=a, e=e: v(u, b, M_(1000), a, e, 1000)).mean() for e in ("r_in", "v_in") for a in ("dial", "dial-hold")))
print("late sham cost vs bio-3 (pooled): dial %.5f hold %.5f" % tuple(
    P(lambda u, b, a=a: v(u, b, "cue4@1000", "bio-3", "r_all") - v(u, b, "cue4@1000", a, "r_all")).mean() for a in ("dial", "dial-hold")))
x = P(lambda u, b: v(u, b, "cue4@1000", "dial-hold", "r_all") - v(u, b, "cue4@1000", "dial", "r_all"))
print("E6 blocks negative", int((x < 0).sum()), "of", len(x))
print("\nadoption (pooled), change4@0:")
for a in ["cue", "bio-1", "bio-3", "dial", "dial-s2", "dial-s4", "dial-s6", "dial-d0", "dial-d4", "dial-d8", "dial-w1.5", "dial-w2", "dial-f0.5", "dial-f0.25", "dial-t1", "dial-t10", "dial-t100"]:
    m = P(lambda u, b, a=a: v(u, b, C, a)).mean()
    print(f"   {a:11s} {m:.6f}" + (f"  static {st[a]:.4f}  run - static {m - st[a]:+.4f}" if a in st else ""))
x = [(v(u, b, C, "dial-s2") - v(u, b, C, "dial")).mean() for u, b in PAIRS]
print("P1 shift-2 per pair %+.4f..%+.4f" % (min(x), max(x)), "| pooled", ci(P(lambda u, b: v(u, b, C, "dial-s2") - v(u, b, C, "dial"))))
fc = SM["footprint_cells"] if isinstance(SM["footprint_cells"], dict) else eval(SM["footprint_cells"])
fa = SM["false_alarms"] if isinstance(SM["false_alarms"], dict) else eval(SM["false_alarms"])
print("\nsham cost (pooled), cue4@0, and per footprint cell (x 1e-5; the sheet has 1,024 sites):")
for a in ("dial-d0", "dial", "dial-d4", "dial-d8", "dial-w1.5", "dial-w2", "bio-1"):
    c = P(lambda u, b, a=a: cost(u, b, a)).mean()
    cells = fc.get(a)
    print(f"   {a:9s} cost {c:.6f}" + (f"  per cell {1e5 * c * 1024 / cells:.2f}  static per cell {1e5 * (fa[a]['all'] - fa['bio-3']['all']) * 1024 / cells:.2f}" if cells else ""))
print("outside the largest footprint (r_out8), cue4@0, arm minus bio-3 (pooled, max abs):",
      max(abs(P(lambda u, b, a=a: v(u, b, Q, a, "r_out8") - v(u, b, Q, "bio-3", "r_out8")).mean()) for a in ARMS[Q] if a not in ("cue", "bio-1", "bio-3")))
print("\nintervals")
print("E1 delay 100", ci(P(lambda u, b: v(u, b, M_(100), "dial") - v(u, b, M_(0), "dial"))))
print("E1 delay 1000", ci(P(lambda u, b: v(u, b, M_(1000), "dial") - v(u, b, M_(0), "dial"))))
print("E3", ci(P(lambda u, b: v(u, b, M_(1000), "dial-hold") - v(u, b, M_(1000), "dial"))))
print("E4 held sensors at t=1000", ci(P(lambda u, b: anc(u, b, M_(1000), "dial-hold", 1000))))
print("P2 dial - d0", ci(P(lambda u, b: v(u, b, C, "dial") - v(u, b, C, "dial-d0"))))
print("done")
