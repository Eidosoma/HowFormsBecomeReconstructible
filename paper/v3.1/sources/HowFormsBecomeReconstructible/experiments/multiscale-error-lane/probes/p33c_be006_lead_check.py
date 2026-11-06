"""P33c (python probes/p33c_be006_lead_check.py ROOT): the lead's check of BE006's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written by the lead while BE006's development ran (tried on
the preflight blocks first) and run after it, 29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_BE006.md from the frozen registration's words (not
from be006.predict / be006.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. be006.design is
imported for run names, arms and reads only. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be006/development). Output: probes/results/p33c_be006_lead_check.txt.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from be006 import design as D  # noqa: E402  (run names, arms and reads only)

ROOT = Path(sys.argv[1])
M = json.load(open(ROOT / "manifest.json"))
bad = []
for key, t in M["tasks"].items():
    for kind in ("shards", "raw"):
        f = t["files"][kind]
        if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            bad.append(f["path"])
print("tasks", len(M["tasks"]), "files checked", 2 * len(M["tasks"]), "sha256 mismatches", bad, "digest", M["design_digest"][:12])
print("run: %s to %s, wall %.0f s, cpu %.0f s (%.2f CPU-h), peak worker RSS %s MB, %d workers, 1-min load at start %s"
      % (M["started_utc"], M["finished_utc"], M["wall_s"], M["cpu_s_total"], M["cpu_s_total"] / 3600,
         M["worker_maxrss_mb_peak"], M["workers"], M["load_1min_start"]))

BLOCKS = list(range(*M["blocks"]))
UNITS = ["S4_t0", "S4_t1", "LB_t0", "LB_t1", "F0_t0", "F0_t1"]
PAIRS = [(u, b) for u in UNITS for b in ("dw", "li4")]
ARMS = {D.run_name(*r): list(r[3]) for r in D.RUNS}
READS = {D.run_name(*r): list(D.run_reads(*r)) for r in D.RUNS}
TSTAR = {0.01: np.log(1.8) / -np.log(1 - 0.01), 3e-4: np.log(1.8) / -np.log(1 - 3e-4)}
DEL = {e: {m: int(round(m * ts)) for m in (0.5, 1, 2, 4)} for e, ts in TSTAR.items()}
assert DEL[0.01] == {0.5: 29, 1: 58, 2: 117, 4: 234} and DEL[3e-4] == {0.5: 979, 1: 1959, 2: 3918, 4: 7836}, DEL
ETA = {"F": 0.01, "A": 3e-4, "AL": 3e-4, "S": 3e-4, "SL": 3e-4}
print("T* = %.2f and %.2f updates (%.2f h and %.2f h at 300 updates an hour)" % (TSTAR[0.01], TSTAR[3e-4], TSTAR[0.01] / 300, TSTAR[3e-4] / 300))
Z = {(u, b, k): np.load(ROOT / "shards" / b / u / f"{k}.npz") for u, b in PAIRS for k in BLOCKS}
C = {}


def blk(u, b, k, key):
    if (u, b, k, key) not in C:
        C[(u, b, k, key)] = Z[(u, b, k)][key]
    return C[(u, b, k, key)]


def v(run, arm, t, e="r_in"):
    """The pooled per-block value: the mean over the twelve unit-body pairs of each block's case mean."""
    ai, ti = ARMS[run].index(arm), READS[run].index(t)
    return np.array([np.mean([blk(u, b, k, f"{run}/{e}")[ti, ai].mean() for u, b in PAIRS]) for k in BLOCKS])


def sens(c, m):
    run = f"memory4@{DEL[ETA[c]][m]}"
    ai = ARMS[run].index(f"dial-{c}")
    return np.array([np.mean([blk(u, b, k, f"{run}/anc_on")[ai].mean() / blk(u, b, k, f"{run}/n_anc").mean() for u, b in PAIRS]) for k in BLOCKS])


prompt = lambda c, t=8000: v("memory4@0", f"dial-{c}", t)
none = lambda c, t=8000: v("memory4@0", f"never-{c}", t)
late = lambda c, m, t=8000: v(f"memory4@{DEL[ETA[c]][m]}", f"dial-{c}", t)
adopt = lambda c, arm="dial": v("change4@0", f"{arm}-{c}", 8000)
cost = lambda c: v("cue4@0", f"never-{c}", 8000, "r_all") - v("cue4@0", f"dial-{c}", 8000, "r_all")


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f] pos %d/%d" % (m, m - h, m + h, (x > 0).sum(), len(x))


res = {}


def part(name, x, thr, sense):
    m = x.mean()
    ok = {"ge": m >= thr, "le": m <= thr, "abs": abs(m) <= thr}[sense]
    sd = x.std(ddof=1)
    d = {"ge": m - thr, "le": thr - m, "abs": thr - abs(m)}[sense]
    res.setdefault(name.split()[0], []).append(bool(ok))
    print(f"{name:62s} {ci(x)}  SD {sd:.4f} ({(d / sd if sd > 0 else float('inf')):.2f} SD)  rule {sense} {thr}  {'ok' if ok else 'MISS'}")


print("\n== statements (pooled over the twelve unit-body pairs)")
part("K1 prompt(SL) - late(SL, 0.5) at 8000", prompt("SL") - late("SL", 0.5), 0.02, "le")
part("K1 prompt(SL) - late(SL, 1) at 8000", prompt("SL") - late("SL", 1), 0.02, "le")
part("K1 prompt(SL) - late(SL, 2) at 8000", prompt("SL") - late("SL", 2), 0.05, "ge")
part("K1 prompt(SL) - late(SL, 4) at 12000", prompt("SL", 12000) - late("SL", 4, 12000), 0.05, "ge")
part("K1 prompt(SL)@4000 - late(SL, 2)@8000 (equal elapsed)", prompt("SL", 4000) - late("SL", 2), 0.05, "ge")
part("K1 prompt(SL)@4000 - late(SL, 4)@12000 (equal elapsed)", prompt("SL", 4000) - late("SL", 4, 12000), 0.05, "ge")
part("K2 late(F, 0.5) - prompt(F) at 4000", late("F", 0.5, 4000) - prompt("F", 4000), 0.02, "abs")
part("K2 late(F, 1) - prompt(F) at 4000", late("F", 1, 4000) - prompt("F", 4000), 0.02, "abs")
part("K2 prompt(F) - late(F, 2) at 4000", prompt("F", 4000) - late("F", 2, 4000), 0.05, "ge")
part("K2 prompt(F) - late(F, 4) at 4000", prompt("F", 4000) - late("F", 4, 4000), 0.05, "ge")
part("K3 sensors(SL, 0.5)", sens("SL", 0.5), 0.05, "le")
part("K3 sensors(SL, 1)", sens("SL", 1), 0.05, "le")
part("K3 sensors(SL, 2)", sens("SL", 2), 0.15, "ge")
part("K4 sensors(A, 1) - sensors(SL, 1)", sens("A", 1) - sens("SL", 1), 0.1, "ge")
part("K4 loss(A, 1) - loss(SL, 1) at 8000", (prompt("A") - late("A", 1)) - (prompt("SL") - late("SL", 1)), 0.03, "ge")
part("K5 prompt(A) - none(A) at 8000", prompt("A") - none("A"), 0.2, "ge")
part("K5 prompt(SL) - none(SL) at 8000", prompt("SL") - none("SL"), 0.2, "ge")
part("K6 prompt(SL) - prompt(S) at 8000", prompt("SL") - prompt("S"), 0.1, "ge")
part("K6 adopt(SL) - adopt(S) at 8000", adopt("SL") - adopt("S"), 0.1, "ge")
part("K7 (prompt SL - S) - (prompt AL - A)", (prompt("SL") - prompt("S")) - (prompt("AL") - prompt("A")), 0.1, "ge")
part("K7 (adopt SL - S) - (adopt AL - A)", (adopt("SL") - adopt("S")) - (adopt("AL") - adopt("A")), 0.1, "ge")
part("K8 prompt(S) - none(S) at 8000", prompt("S") - none("S"), 0.05, "abs")
part("K8 adopt(S) - adopt(never-S) at 8000", adopt("S") - adopt("S", "never"), 0.05, "abs")
part("K9 cost(AL) - cost(A)", cost("AL") - cost("A"), 0.001, "ge")
part("K9 cost(SL) - cost(S)", cost("SL") - cost("S"), 0.001, "ge")
part("K10 prompt(AL) - prompt(A) at 8000", prompt("AL") - prompt("A"), 0.02, "ge")
part("K10 adopt(AL) - adopt(A) at 8000", adopt("AL") - adopt("A"), 0.05, "ge")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== the prompt signal over time: pooled r_in by read (hours at 300 updates an hour)")
for arm in ("dial-F", "never-F", "dial-A", "never-A", "dial-AL", "never-AL", "dial-S", "never-S", "dial-SL", "never-SL"):
    print(f"   {arm:9s}", " ".join(f"{t} ({t / 300:.1f} h): {v('memory4@0', arm, t).mean():.4f}" for t in READS["memory4@0"]))

print("\n== late signals: loss against the prompt signal at the scoring read, and the sensors repaired at the signal")
for c in ("F", "A", "AL", "SL"):
    row = []
    for m in (0.5, 1, 2, 4):
        run = f"memory4@{DEL[ETA[c]][m]}"
        if f"dial-{c}" not in ARMS.get(run, []):
            continue
        t = 4000 if c == "F" else (12000 if m == 4 else 8000)
        row.append(f"m {m} (D {DEL[ETA[c]][m]}, {DEL[ETA[c]][m] / 300:.1f} h): loss {(prompt(c, t) - late(c, m, t)).mean():+.4f}, sensors {sens(c, m).mean():.4f}")
    print(f"   {c:3s}", " | ".join(row))
print("   SL at equal elapsed time since each signal's start (prompt read at 4,000 - D... as registered, and the early m):")
print("     m 0.5: prompt@1000 - late@2000 %+.4f; m 1: prompt@2000 - late@4000 %+.4f; m 2: prompt@4000 - late@8000 %+.4f; m 4: prompt@4000 - late@12000 %+.4f"
      % ((prompt("SL", 1000) - late("SL", 0.5, 2000)).mean(), (prompt("SL", 2000) - late("SL", 1, 4000)).mean(),
         (prompt("SL", 4000) - late("SL", 2)).mean(), (prompt("SL", 4000) - late("SL", 4, 12000)).mean()))
g8 = (prompt("SL") - none("SL")).mean()
g12 = (prompt("SL", 12000) - none("SL", 12000)).mean()
print("   SL keeps of the prompt gain over no signal: at 2 T* (8,000) %.4f of %.4f = %.4f; at 4 T* (12,000) %.4f of %.4f = %.4f"
      % ((late("SL", 2) - none("SL")).mean(), g8, (late("SL", 2) - none("SL")).mean() / g8,
         (late("SL", 4, 12000) - none("SL", 12000)).mean(), g12, (late("SL", 4, 12000) - none("SL", 12000)).mean() / g12))
print("   A at 4 T* (12,000): loss %+.4f" % (prompt("A", 12000) - late("A", 4, 12000)).mean())

print("\n== adoption of a legitimate 4 x 4 change at 8,000, and a prompt sham's cost to the sheet")
print("   adoption:", " ".join(f"{k}-{c} {adopt(c, k).mean():.4f}" for c in ("A", "AL", "S", "SL") for k in ("dial", "never")))
print("   sham cost:", " ".join(f"{c} {cost(c).mean():+.4f}" for c in ("A", "AL", "S", "SL")))
print("   S's dip: prompt(S) - none(S) at 2,000 %+.4f; at 1,000 %+.4f" % ((prompt("S", 2000) - none("S", 2000)).mean(), (prompt("S", 1000) - none("S", 1000)).mean()))
print("done")
