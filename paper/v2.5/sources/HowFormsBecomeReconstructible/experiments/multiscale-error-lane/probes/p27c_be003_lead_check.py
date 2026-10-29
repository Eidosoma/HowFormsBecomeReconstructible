"""P27c (python probes/p27c_be003_lead_check.py): the lead's check of BE003's development numbers. LEAD_CHECK_NOT_REGISTERED;
a read of the development shards, written and run by the lead after the development read, 28 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_BE003.md from the registration's words (not from
be003.predict / be003.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. Output:
probes/results/p27c_be003_lead_check.txt."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path("/e/project1/e-aif-2026pg01-1345/Research/HowFormsBecomeReconstructible/experiments/multiscale-error-lane")
sys.path.insert(0, str(LANE))
from be003 import design as D  # noqa: E402  (arm and read lists only)

ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be003/development")
M = json.load(open(ROOT / "manifest.json"))
bad = []
for key, t in M["tasks"].items():
    for kind in ("shards", "raw"):
        f = t["files"][kind]
        if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            bad.append(f["path"])
print("tasks", len(M["tasks"]), "sha256 mismatches", bad, "digest", M["design_digest"][:12])

BLOCKS = list(range(910220, 910236))
PAIRS = [(u, b) for u in ("S4_t0", "F0_t0") for b in ("dw", "li4")]
ARMS = {D.run_name(*r): list(D.run_arms(*r)) for r in D.RUNS}
READS = {D.run_name(*r): list(D.run_reads(*r)) for r in D.RUNS}
Z = {(u, b, k): np.load(ROOT / "shards" / b / u / f"{k}.npz") for u, b in PAIRS for k in BLOCKS}
R8, RL, RC = "regrow8", "regrow8_late", "regrow+cue8"
TW = {d: f"twin4@{d}" for d in D.DELAYS}
assert set(ARMS) == {R8, RL, RC, *TW.values()}, ARMS


def v(u, b, run, arm, e="r_in", t=None):
    """(16,) block means (over the 8 cases) of endpoint e of arm in run at read t (the last read if None)."""
    ai = ARMS[run].index(arm)
    out = []
    for k in BLOCKS:
        x = Z[(u, b, k)][f"{run}/{e}"]
        if e.startswith("trace_"):
            out.append(x[t // 100 - 1, ai].mean())
        elif x.ndim == 2:
            out.append(x[ai].mean())
        else:
            ti = len(READS[run]) - 1 if t is None else READS[run].index(t)
            out.append(x[ti, ai].mean())
    return np.array(out)


def extra(u, b, arm, e):
    return (v(u, b, R8, arm, e) - v(u, b, RC, arm, e)) - (v(u, b, R8, "cue", e) - v(u, b, RC, "cue", e))


def net(u, b, arm, d):
    cf = D.ALIAS.get(arm, arm)
    return v(u, b, TW[d], arm, "r_young") - (1 - v(u, b, R8, cf, "r_young", d + D.HORIZON))


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return f"{m:+.4f} [{m - h:+.4f}, {m + h:+.4f}] pos {int((x > 0).sum())}/{len(x)}"


def rng(xs, f="+.4f"):
    ms = [x.mean() for x in xs]
    return f"{min(ms):{f}} to {max(ms):{f}}"


def pool(xs):
    return np.mean(xs, 0).mean()


S = {}
print("\n== statements (t = 4,000 unless named; unrounded block means)")
a = [v(*p, R8, "mat-300") - v(*p, R8, "dial") for p in PAIRS]
b_ = [v(*p, R8, "mat-300") - v(*p, R8, "inst-1") for p in PAIRS]
s4 = [v(*p, R8, x) - v(*p, R8, "inst-3") for p in PAIRS[:2] for x in ("mat-300", "dial")]
f0 = pool([v(*p, R8, x) - v(*p, R8, "inst-3") for p in PAIRS[2:] for x in ("mat-300", "dial")])
ok = all(abs(x.mean()) <= 0.012 for x in a + b_) and all(x.mean() >= 0.025 for x in s4) and f0 >= 0.003
print("W1", "HOLDS" if ok else "FAILS", "| mat-300 - dial", rng(a), "| - inst-1", rng(b_), "| S4 over inst-3", rng(s4), "| F0 mean %+.4f" % f0)
inter = pool([(v(*p, R8, "mat-dial") - v(*p, R8, "mat-300")) - (v(*p, R8, "dial") - v(*p, R8, "inst-3")) for p in PAIRS])
stack = pool([v(*p, R8, "mat-dial") - v(*p, R8, "mat-300") for p in PAIRS])
print("W2", "HOLDS" if inter <= -0.025 and stack <= 0 else "FAILS", "| interaction %+.4f" % inter,
      "| per pair", rng([(v(*p, R8, "mat-dial") - v(*p, R8, "mat-300")) - (v(*p, R8, "dial") - v(*p, R8, "inst-3")) for p in PAIRS]),
      "| mat-dial - mat-300 %+.4f" % stack, "per pair", rng([v(*p, R8, "mat-dial") - v(*p, R8, "mat-300") for p in PAIRS]))
same = [v(*p, RL, "mat-dial") - v(*p, R8, "mat-300") for p in PAIRS]
over = pool([v(*p, RL, "dial") - v(*p, R8, "inst-3") for p in PAIRS])
defi = pool([v(*p, RL, "dial") - v(*p, R8, "dial") for p in PAIRS])
print("W3", "HOLDS" if all(abs(x.mean()) <= 0.005 for x in same) and over >= 0.01 and defi >= -0.035 else "FAILS",
      "| mat-dial late - mat-300", rng(same), "| dial late - inst-3 %+.4f | late - prompt %+.4f" % (over, defi))
w4 = {x: [extra(*p, x, "r_in") for p in PAIRS] for x in ("mat-300", "dial")}
print("W4", "HOLDS" if all(y.mean() >= 0.015 for ys in w4.values() for y in ys) else "FAILS",
      "| extra loss inside mat-300", rng(w4["mat-300"]), "dial", rng(w4["dial"]))
ring_d = [extra(*p, "dial", "r_ring") for p in PAIRS]
ring_f = [extra(*p, x, "r_ring") for p in PAIRS for x in ("mat-300", "mat-1000")]
outs = [v(*p, RC, x, "r_out") - v(*p, RC, "inst-3", "r_out") for p in PAIRS for x in ("mat-300", "mat-1000", "dial", "mat-dial")]
print("W5", "HOLDS" if all(y.mean() >= 0.045 for y in ring_d) and all(abs(y.mean()) <= 0.01 for y in ring_f)
      and all(abs(y.mean()) <= 0.0025 for y in outs) else "FAILS",
      "| ring dial", rng(ring_d), "| ring free", rng(ring_f), "| r_out", rng(outs))
tf = [v(*p, TW[d], x, "r_twin") - v(*p, TW[d], "inst-3", "r_twin") for p in PAIRS for d in D.DELAYS for x in ("mat-300", "mat-1000")]
td = [v(*p, TW[d], "dial", "r_twin") - v(*p, TW[d], "inst-3", "r_twin") for p in PAIRS for d in D.DELAYS]
print("W6", "HOLDS" if all(abs(y.mean()) <= 0.02 for y in tf) and all(y.mean() >= 0.23 for y in td) else "FAILS",
      "| twin free", rng(tf), "| twin dial", rng(td))
w7 = [net(*p, "mat-300", 0) - net(*p, "inst-3", 0) for p in PAIRS]
print("W7", "HOLDS" if all(y.mean() >= 0.035 for y in w7) and pool(w7) >= 0.11 else "FAILS", "| per pair", rng(w7), "| mean %+.4f" % pool(w7))
d300 = pool([net(*p, "mat-1000", 300) - net(*p, "mat-300", 300) for p in PAIRS])
c3 = pool([net(*p, "mat-300", 2000) - net(*p, "inst-3", 2000) for p in PAIRS])
c10 = pool([net(*p, "mat-1000", 2000) - net(*p, "inst-3", 2000) for p in PAIRS])
op = pool([net(*p, "dial", 2000) - net(*p, "inst-3", 2000) for p in PAIRS])
print("W8", "HOLDS" if d300 >= 0.07 and abs(c3) <= 0.04 and abs(c10) <= 0.04 and op >= 0.12 else "FAILS",
      "| d300 mat-1000 - mat-300 %+.4f (pairs %s) | d2000 mat-300 %+.4f mat-1000 %+.4f dial %+.4f" % (
          d300, rng([net(*p, "mat-1000", 300) - net(*p, "mat-300", 300) for p in PAIRS]), c3, c10, op))

print("\n== intervals (95% t over 16 blocks)")
for p in PAIRS:
    print(p, "W7", ci(net(*p, "mat-300", 0) - net(*p, "inst-3", 0)), "| W8 d300", ci(net(*p, "mat-1000", 300) - net(*p, "mat-300", 300)),
          "| d2000 mat-300 - inst-3", ci(net(*p, "mat-300", 2000) - net(*p, "inst-3", 2000)))
for p in PAIRS:
    print(p, "late - prompt (dial)", ci(v(*p, RL, "dial") - v(*p, R8, "dial")), "| W2 interaction",
          ci((v(*p, R8, "mat-dial") - v(*p, R8, "mat-300")) - (v(*p, R8, "dial") - v(*p, R8, "inst-3"))))

print("\n== the wound table (t = 4,000; ranges over the four pairs; S4 / F0 split for levels)")
for x in D.ARMS:
    s4l = rng([v(*p, R8, x) for p in PAIRS[:2]], ".3f")
    f0l = rng([v(*p, R8, x) for p in PAIRS[2:]], ".3f")
    cost = rng([v(*p, R8, x) - v(*p, RC, x) for p in PAIRS], ".3f")
    ex = rng([extra(*p, x, "r_in") for p in PAIRS]) if x != "cue" else "-"
    er = rng([extra(*p, x, "r_ring") for p in PAIRS]) if x != "cue" else "-"
    oo = rng([v(*p, RC, x, "r_out") - v(*p, RC, "inst-3", "r_out") for p in PAIRS])
    print(f"{x:9s} S4 {s4l} | F0 {f0l} | cost in {cost} | extra in {ex} | extra ring {er} | out-inst3 {oo}")
print("mat-300 r_in at 250", rng([v(*p, R8, "mat-300", "r_in", 250) for p in PAIRS], ".3f"), "at 4000", rng([v(*p, R8, "mat-300") for p in PAIRS], ".3f"))
print("filled at 250 (every arm, every pair) min %.4f" % min(v(*p, R8, x, "filled", 250).min() for p in PAIRS for x in D.ARMS))
for x in ("mat-300", "mat-1000"):
    print("maturity in wound", x, {t: round(pool([v(*p, R8, x, "maturity", t) for p in PAIRS]), 3) for t in (250, 1000, 2000)})
print("committed share under corruption (mean over pairs): sheet / outside",
      {x: (round(pool([v(*p, RC, x, "opened") for p in PAIRS]), 5), round(pool([v(*p, RC, x, "opened_out") for p in PAIRS]), 5))
       for x in D.ARMS if x != "cue"})

print("\n== the late signal")
for x in ("dial", "mat-dial"):
    print(x, "late", rng([v(*p, RL, x) for p in PAIRS], ".3f"), "prompt", rng([v(*p, R8, x) for p in PAIRS], ".3f"))
print("dial late at t = 1,000 minus inst-3 (max abs over blocks and pairs) %.2e" %
      max(np.abs(v(*p, RL, "dial", "r_in", 1000) - v(*p, R8, "inst-3", "r_in", 1000)).max() for p in PAIRS))
print("dial late - prompt at t = 2,000", rng([v(*p, RL, "dial", "r_in", 2000) - v(*p, R8, "dial", "r_in", 2000) for p in PAIRS]))
print("inst-3 r_in(1000) - r_in(250)", rng([v(*p, R8, "inst-3", "r_in", 1000) - v(*p, R8, "inst-3", "r_in", 250) for p in PAIRS]))

print("\n== re-specification (levels of r_twin over pairs and delays; nets over pairs per delay)")
for x in D.ARMS:
    tw = rng([v(*p, TW[d], x, "r_twin") for p in PAIRS for d in D.DELAYS], ".3f")
    nets = {d: rng([net(*p, x, d) for p in PAIRS], ".3f") for d in D.DELAYS}
    print(f"{x:9s} twin {tw} | net {nets}")
print("young patch with no change at 2,000: inst-3", rng([v(*p, R8, "inst-3", "r_young", 2000) for p in PAIRS], ".3f"),
      "mat-300", rng([v(*p, R8, "mat-300", "r_young", 2000) for p in PAIRS], ".3f"))

print("\n== static map against the run")
SM = json.load(open(LANE / "be003/frozen/static_map.json"))
for x in ("mat-300", "mat-1000", "inst-1.5", "inst-1"):
    row = {d: (SM["adoption"][x][str(d)]["young"], rng([net(*p, x, d) - net(*p, "inst-3", d) for p in PAIRS], ".3f")) for d in (300, 1000, 2000)}
    print(x, row)
for x in ("mat-300", "dial", "inst-1"):
    print("false alarms static", x, SM["false_alarms"][x]["250"], "| run extra loss inside", rng([extra(*p, x, "r_in") for p in PAIRS], ".3f"))


print("\n== exact per-pair values behind the report's intervals (S4/dw, S4/li4, F0/dw, F0/li4)")
def ci6(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f]" % (m, m - h, m + h)
for p in PAIRS:
    print(p, "late-prompt", ci6(v(*p, RL, "dial") - v(*p, R8, "dial")), "| W7", ci6(net(*p, "mat-300", 0) - net(*p, "inst-3", 0)),
          "| W8 d300", ci6(net(*p, "mat-1000", 300) - net(*p, "mat-300", 300)), "| d2000", ci6(net(*p, "mat-300", 2000) - net(*p, "inst-3", 2000)))
print("W2 per pair", " ".join("%+.6f" % ((v(*p, R8, "mat-dial") - v(*p, R8, "mat-300")) - (v(*p, R8, "dial") - v(*p, R8, "inst-3"))).mean() for p in PAIRS),
      "| stack", " ".join("%+.6f" % (v(*p, R8, "mat-dial") - v(*p, R8, "mat-300")).mean() for p in PAIRS))
print("ring extra loss, mat-dial", " ".join("%+.6f" % extra(*p, "mat-dial", "r_ring").mean() for p in PAIRS))

print("\n== the twin patch by delay: r_twin at d + 2,000, mean over the four pairs")
for x in ("inst-3", "dial"):
    print(x, {d: round(float(np.mean([v(*p, TW[d], x, "r_twin").mean() for p in PAIRS])), 4) for d in D.DELAYS})
