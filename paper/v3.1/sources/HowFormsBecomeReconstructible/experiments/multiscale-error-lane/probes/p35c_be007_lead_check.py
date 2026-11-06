"""P35c (python probes/p35c_be007_lead_check.py ROOT): the lead's check of BE007's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written by the lead while BE007's development ran (tried on
the preflight blocks first) and run after it, 29-30 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_BE007.md from the frozen registration's words (not
from be007.predict / be007.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. be007.design is
imported for run names, arms and reads only. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be007/development). Output: probes/results/p35c_be007_lead_check.txt.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from be007 import design as D  # noqa: E402  (run names, arms and reads only)

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
TSTAR = np.log(1.8) / -np.log(1 - 3e-4)
DEL = {m: int(round(m * TSTAR)) for m in (0.5, 1, 2, 4)}
assert DEL == {0.5: 979, 1: 1959, 2: 3918, 4: 7836}, DEL
print("runs:", {k: len(v) for k, v in ARMS.items()}, "| T* = %.2f updates (%.2f h)" % (TSTAR, TSTAR / 300))
Z = {(u, b, k): np.load(ROOT / "shards" / b / u / f"{k}.npz") for u, b in PAIRS for k in BLOCKS}
C = {}


def blk(u, b, k, key):
    if (u, b, k, key) not in C:
        C[(u, b, k, key)] = Z[(u, b, k)][key]
    return C[(u, b, k, key)]


def v(run, arm, t, e="r_in"):
    ai, ti = ARMS[run].index(arm), READS[run].index(t)
    return np.array([np.mean([blk(u, b, k, f"{run}/{e}")[ti, ai].mean() for u, b in PAIRS]) for k in BLOCKS])


def sc(run, arm, e):
    ai = ARMS[run].index(arm)
    return np.array([np.mean([blk(u, b, k, f"{run}/{e}")[ai].mean() for u, b in PAIRS]) for k in BLOCKS])


def sens(c, m):
    run = f"memory4@{DEL[m]}"
    ai = ARMS[run].index(f"dial-{c}")
    return np.array([np.mean([blk(u, b, k, f"{run}/anc_on")[ai].mean() / blk(u, b, k, f"{run}/n_anc").mean() for u, b in PAIRS]) for k in BLOCKS])


gain = lambda c, m: v(f"memory4@{DEL[m]}", f"dial-{c}", DEL[m] + 4000) - v("memory4@0", f"never-{c}", DEL[m] + 4000)
loss = lambda c, m: v("memory4@0", f"dial-{c}", 4000) - v(f"memory4@{DEL[m]}", f"dial-{c}", DEL[m] + 4000)
adopt = lambda c: v("change4@3918", f"dial-{c}", 7918) - v("change4@3918", f"never-{c}", 7918)
sham = lambda c: v("cue4@3918", f"never-{c}", 7918, "r_all") - v("cue4@3918", f"dial-{c}", 7918, "r_all")
rise = lambda c, t0: v("memory4@0", f"never-{c}", 12000) - v("memory4@0", f"never-{c}", t0)
hit = lambda c, m: sc(f"memory4@{DEL[m]}", f"dial-{c}", "hit")


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f]" % (m, m - h, m + h)


res = {}


def part(name, x, thr, sense):
    m = x.mean()
    ok = {"ge": m >= thr, "le": m <= thr, "abs": abs(m) <= thr}[sense]
    sd = x.std(ddof=1)
    d = {"ge": m - thr, "le": thr - m, "abs": thr - abs(m)}[sense]
    nb = int(sum({"ge": y >= thr, "le": y <= thr, "abs": abs(y) <= thr}[sense] for y in x))
    res.setdefault(name.split()[0], []).append(bool(ok))
    print(f"{name:46s} {ci(x)}  SD {sd:.4f} ({(d / sd if sd > 0 else float('inf')):.2f} SD; {nb}/{len(x)} blocks)  rule {sense} {thr}  {'ok' if ok else 'MISS'}")


print("\n== statements (pooled over the twelve unit-body pairs)")
for c, ms in (("SL", (0.5, 1)), ("C6", (0.5,)), ("C12", (0.5, 1)), ("F12", (0.5, 1))):
    for m in ms:
        part(f"E1 loss({c}, {m} T*), equal elapsed", loss(c, m), 0.02, "le")
for c, ms in (("C6", (1, 2, 4)), ("C12", (2, 4)), ("C24", (4,)), ("F12", (2, 4))):
    for m in ms:
        part(f"E2 gain({c}, {m} T*)", gain(c, m), 0.05, "le")
part("E3 gain(C12, 1) - gain(C6, 1)", gain("C12", 1) - gain("C6", 1), 0.2, "ge")
part("E3 gain(C24, 2) - gain(C12, 2)", gain("C24", 2) - gain("C12", 2), 0.2, "ge")
part("E3 gain(SL, 4) - gain(C24, 4)", gain("SL", 4) - gain("C24", 4), 0.2, "ge")
for c in ("C6", "C12", "F12"):
    part(f"E4 adopt({c}) late", adopt(c), 0.05, "le")
for c in ("SL", "C24"):
    part(f"E4 adopt({c}) late", adopt(c), 0.1, "ge")
for c in ("C6", "C12", "F12"):
    part(f"E5 sham({c}) late", sham(c), 0.001, "le")
for c in ("SL", "C24"):
    part(f"E5 sham({c}) late", sham(c), 0.001, "ge")
for c, t0 in (("C6", 2000), ("C12", 4000), ("C24", 7918)):
    part(f"E6 |rise({c}) from {t0}|", np.abs(rise(c, t0)), 0.005, "le")
part("E6 rise(SL) 2000 -> 12000", rise("SL", 2000), 0.02, "ge")
part("E6 rise(SL) - rise(F12) 4000 -> 12000", rise("SL", 4000) - rise("F12", 4000), 0.01, "ge")
for c, ms in (("C6", (1, 2, 4)), ("C12", (2, 4)), ("C24", (4,))):
    for m in ms:
        part(f"E7 hit({c}, {m} T*)", hit(c, m), 0.1, "ge")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== late signals: gain over no signal at D + 4,000 (the hours of D at 300 updates an hour)")
for c in ("SL", "C6", "C12", "C24", "F12"):
    print(f"   {c:4s}", " | ".join(f"{m} T* ({DEL[m] / 300:.1f} h): gain {gain(c, m).mean():+.4f}, loss {loss(c, m).mean():+.4f}, sensors {sens(c, m).mean():.4f}, hit {hit(c, m).mean():.4f}, executed {sc(f'memory4@{DEL[m]}', f'dial-{c}', 'executed').mean():.4f}" for m in (0.5, 1, 2, 4)))
print("   gain intervals at 2 T* and 4 T*:", " ".join(f"{c}: {ci(gain(c, 2))} / {ci(gain(c, 4))}" for c in ("SL", "C24")))
print("\n== the no-signal repair over 40 h (never-c's r_in in memory4@0)")
for c in ("SL", "C6", "C12", "C24", "F12"):
    print(f"   {c:4s}", " ".join(f"{t} ({t / 300:.1f} h): {v('memory4@0', f'never-{c}', t).mean():.4f}" for t in READS["memory4@0"]))
print("\n== the prompt signal over 40 h (dial-c's r_in in memory4@0)")
for c in ("SL", "C6", "C12", "C24", "F12"):
    print(f"   {c:4s}", " ".join(f"{t}: {v('memory4@0', f'dial-{c}', t).mean():.4f}" for t in READS["memory4@0"]))
print("\n== the late change and sham at 13.1 h (read at 7,918)")
print("   adoption over no signal:", " ".join(f"{c} {adopt(c).mean():+.4f}" for c in ("SL", "C6", "C12", "C24", "F12")))
print("   sham cost to the sheet:", " ".join(f"{c} {sham(c).mean():+.4f}" for c in ("SL", "C6", "C12", "C24", "F12")))
print("done")
