"""P36c (python probes/p36c_be008_lead_check.py ROOT): the lead's check of BE008's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written and run by the lead after BE008's development read,
30 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_BE008.md from the frozen registration's words (not
from be008.predict / be008.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. be008.design is
imported for run names, arms and reads only. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be008/development). Output: probes/results/p36c_be008_lead_check.txt.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from be008 import design as D  # noqa: E402  (run names, arms and reads only)

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
DEL = {m: int(round(m * TSTAR)) for m in (0.5, 1, 2)}
assert DEL == {0.5: 979, 1: 1959, 2: 3918}, DEL
CLOCKS = ("AL", "AL-m", "AL-n", "SL-m", "SL")
Z = {(u, b, k): np.load(ROOT / "shards" / b / u / f"{k}.npz") for u, b in PAIRS for k in BLOCKS}
C = {}


def blk(u, b, k, key):
    if (u, b, k, key) not in C:
        C[(u, b, k, key)] = Z[(u, b, k)][key]
    return C[(u, b, k, key)]


def pooled(f):
    return np.array([np.mean([f(u, b, k) for u, b in PAIRS]) for k in BLOCKS])


def r(run, arm, t, e="r_in"):
    ai, ti = ARMS[run].index(arm), READS[run].index(t)
    return pooled(lambda u, b, k: blk(u, b, k, f"{run}/{e}")[ti, ai].mean())


def sens(c, m):
    run = f"memory4@{DEL[m]}"
    ai = ARMS[run].index(f"dial-{c}")
    return pooled(lambda u, b, k: blk(u, b, k, f"{run}/anc_on")[ai].mean() / blk(u, b, k, f"{run}/n_anc").mean())


def quiet(c, t):
    run, ai = "memory4@0", ARMS["memory4@0"].index(f"never-{c}")
    ti = READS[run].index(t)
    return pooled(lambda u, b, k: blk(u, b, k, f"{run}/n_anc_ok")[ti, ai].mean() / blk(u, b, k, f"{run}/n_anc").mean())


loss = lambda c, m: r("memory4@0", f"dial-{c}", 4000) - r(f"memory4@{DEL[m]}", f"dial-{c}", DEL[m] + 4000)
sheet = lambda c, t: r("memory4@0", f"never-{c}", t, "r_all")


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
    print(f"{name:52s} {ci(x)}  SD {sd:.4f} ({(d / sd if sd > 0 else float('inf')):.2f} SD; {nb}/{len(x)} blocks)  rule {sense} {thr}  {'ok' if ok else 'MISS'}")


print("\n== statements (pooled over the twelve unit-body pairs)")
part("N1 sensors(AL,1) - sensors(AL-n,1)", sens("AL", 1) - sens("AL-n", 1), 0.1, "ge")
part("N1 loss(AL,1) - loss(AL-n,1), equal elapsed", loss("AL", 1) - loss("AL-n", 1), 0.02, "ge")
part("N2 sensors(AL-n,0.5)", sens("AL-n", 0.5), 0.05, "le")
part("N2 sensors(AL-n,1)", sens("AL-n", 1), 0.05, "le")
part("N2 sensors(AL-n,2)", sens("AL-n", 2), 0.1, "ge")
part("N2 loss(AL-n,0.5)", loss("AL-n", 0.5), 0.02, "le")
part("N2 loss(AL-n,1)", loss("AL-n", 1), 0.02, "le")
part("N2 loss(AL-n,2)", loss("AL-n", 2), 0.03, "ge")
part("N3 sensors(AL,1) - sensors(AL-m,1)", sens("AL", 1) - sens("AL-m", 1), 0.1, "ge")
part("N4 (SL-m - SL) - (AL-m - AL-n) at T*", (sens("SL-m", 1) - sens("SL", 1)) - (sens("AL-m", 1) - sens("AL-n", 1)), 0.025, "ge")
part("N4 sensors(SL,1) - sensors(AL-n,1)", sens("SL", 1) - sens("AL-n", 1), 0.02, "abs")
part("N5 quiet(AL,1000) - quiet(AL-n,1000)", quiet("AL", 1000) - quiet("AL-n", 1000), 0.05, "ge")
part("N5 quiet(AL-n,1000)", quiet("AL-n", 1000), 0.04, "le")
part("N5 quiet(SL,1000)", quiet("SL", 1000), 0.04, "le")
part("N6 sheet(SL,4000) - sheet(SL-m,4000)", sheet("SL", 4000) - sheet("SL-m", 4000), 0.05, "ge")
part("N6 sheet(AL-n,4000) - sheet(AL-m,4000)", sheet("AL-n", 4000) - sheet("AL-m", 4000), 0.01, "abs")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== sensors repaired at a late signal's onset, and its loss at equal elapsed time (979 / 1,959 / 3,918 updates = 3.3 / 6.5 / 13.1 h)")
for c in CLOCKS:
    print(f"   {c:5s} sensors", " / ".join(ci(sens(c, m)) for m in (0.5, 1, 2)), "| loss", " / ".join(ci(loss(c, m)) for m in (0.5, 1, 2)))
print("\n== no signal: sensors repaired at 1,000 / 2,000 / 4,000 / 6,000 (3.3 / 6.7 / 13.3 / 20 h); sheet at 4,000 / 6,000; prompt and no-signal r_in at 4,000")
for c in CLOCKS:
    print(f"   {c:5s}", " / ".join("%.4f" % quiet(c, t).mean() for t in (1000, 2000, 4000, 6000)),
          "| sheet %.4f / %.4f" % (sheet(c, 4000).mean(), sheet(c, 6000).mean()),
          "| prompt %.4f, none %.4f" % (r("memory4@0", f"dial-{c}", 4000).mean(), r("memory4@0", f"never-{c}", 4000).mean()))
print("   onset share of the prompt signal:", " ".join(f"{c} {pooled(lambda u, b, k: blk(u, b, k, 'memory4@0/onset')[ARMS['memory4@0'].index('dial-' + c)].mean()).mean():.4f}" for c in CLOCKS))
print("   N4 intervals: interaction", ci((sens("SL-m", 1) - sens("SL", 1)) - (sens("AL-m", 1) - sens("AL-n", 1))), "| SL - AL-n", ci(sens("SL", 1) - sens("AL-n", 1)))
print("   N1/N3/N5/N6 intervals:", "N1 sensors", ci(sens("AL", 1) - sens("AL-n", 1)), "| N1 loss", ci(loss("AL", 1) - loss("AL-n", 1)), "| N3", ci(sens("AL", 1) - sens("AL-m", 1)),
      "| N5", ci(quiet("AL", 1000) - quiet("AL-n", 1000)), "| N6", ci(sheet("SL", 4000) - sheet("SL-m", 4000)), ci(sheet("AL-n", 4000) - sheet("AL-m", 4000)))
print("done")
