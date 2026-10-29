"""P26c (python probes/p26c_sc003_lead_check.py ROOT): the lead's check of SC003's development numbers. LEAD_CHECK_NOT_REGISTERED;
a read of the development shards, written and run by the lead after the development read, 29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_SC003.md from the registration's words (not from
sc003.predict / sc003.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sc003/development). Output: probes/results/p26c_sc003_lead_check.txt."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path("/e/project1/e-aif-2026pg01-1345/Research/HowFormsBecomeReconstructible/experiments/multiscale-error-lane")
sys.path.insert(0, str(LANE))
from sc003 import design as D  # noqa: E402  (arm lists, run names, reads only)

ROOT = Path(sys.argv[1])
QUIET = "--quiet" in sys.argv
out = open("/dev/null", "w") if QUIET else sys.stdout


def say(*a):
    print(*a, file=out)


M = json.load(open(ROOT / "manifest.json"))
bad = []
for key, t in M["tasks"].items():
    for kind in ("shards", "raw"):
        f = t["files"][kind]
        if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            bad.append(f["path"])
print("tasks", len(M["tasks"]), "sha256 mismatches", bad, "digest", M["design_digest"][:12])

BLOCKS = list(range(*M["blocks"])) if isinstance(M["blocks"], list) and len(M["blocks"]) == 2 else M["blocks"]
PAIRS = [(u, b) for u in ("S4_t0", "F0_t0") for b in ("dw", "li4")]
HI, LO = "0.001", "0.00025"
Z = {(u, b, k): np.load(ROOT / "shards" / b / u / f"{k}.npz") for u, b in PAIRS for k in BLOCKS}
AT, AW = list(D.ARMS_T), list(D.ARMS_W)
READS = [250, 1000, 2000, 4000]
K = 3 * np.sqrt(1 / 4 + 1 / 16)


def arms(run):
    return AW if run.endswith("@0") else AT


def v(u, b, run, arm, e="r_in", t=4000):
    """(n_blocks,) block means of endpoint e of arm in run (at read t; trace at t; newc at age bin t)."""
    ai = arms(run).index(arm)
    vals = []
    for k in BLOCKS:
        x = Z[(u, b, k)][f"{run}/{e}"]
        if e.startswith("trace"):
            vals.append(x[t // 100 - 1, ai].mean())
        elif e == "newc":
            vals.append(x[t, ai].mean())
        elif x.ndim == 2:
            vals.append(x[ai].mean())
        else:
            vals.append(x[READS.index(t), ai].mean())
    return np.array(vals)


def extra(u, b, mu, arm):
    return ((v(u, b, f"none8@{mu}", arm, "r_all") - v(u, b, f"cue8@{mu}", arm, "r_all"))
            - (v(u, b, f"none8@{mu}", "cue", "r_all") - v(u, b, f"cue8@{mu}", "cue", "r_all")))


def d(u, b, run, a1, a2, e="r_in", t=4000):
    return v(u, b, run, a1, e, t) - v(u, b, run, a2, e, t)


def rng(xs, f="+.4f"):
    ms = [x.mean() for x in xs]
    return f"{min(ms):{f}} to {max(ms):{f}}"


def pool(xs):
    return np.mean(xs, 0)


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return f"{m:+.6f} [{m - h:+.6f}, {m + h:+.6f}] pos {int((x > 0).sum())}/{len(x)}"


say("\n== statements (t = 4,000 unless named)")
# B1: age-0 commitments, ratio mat/iso within 0.95-1.05, inst/iso <= 0.01, none8 and cue8 at both rates, every item
r1 = {(p, r, mu, a): v(*p, f"{r}@{mu}", a, "newc", 0).mean() / v(*p, f"{r}@{mu}", "iso-3", "newc", 0).mean()
      for p in PAIRS for r in ("none8", "cue8") for mu in (HI, LO) for a in ("mat-300", "mat-1000")}
r1i = {(p, r, mu): v(*p, f"{r}@{mu}", "inst-3", "newc", 0).mean() / v(*p, f"{r}@{mu}", "iso-3", "newc", 0).mean()
       for p in PAIRS for r in ("none8", "cue8") for mu in (HI, LO)}
ok = all(0.95 <= x <= 1.05 for x in r1.values()) and all(x <= 0.01 for x in r1i.values())
say("B1", "HOLDS" if ok else "FAILS", "| mat/iso age-0 %.4f to %.4f | inst/iso %.4f to %.4f" % (min(r1.values()), max(r1.values()), min(r1i.values()), max(r1i.values())))
# B2
b2h = [d(*p, f"change4@{HI}", "iso-3", "inst-3") for p in PAIRS]
b2l = [d(*p, f"change4@{LO}", "iso-3", "inst-3") for p in PAIRS]
ok = all(x.mean() >= 0.01 for x in b2h) and pool(b2h).mean() >= 0.15 and all(x.mean() >= 0.005 for x in b2l) and pool(b2l).mean() >= 0.06
say("B2", "HOLDS" if ok else "FAILS", "| 1e-3", rng(b2h), "mean %+.4f | 2.5e-4" % pool(b2h).mean(), rng(b2l), "mean %+.4f" % pool(b2l).mean())
# B3
b3 = [d(*p, f"none8@{HI}", "iso-3", "inst-3", "r_all") for p in PAIRS]
ok = all(x.mean() >= 0.001 for x in b3) and all(x.mean() >= 0.015 for x in b3[:2])
say("B3", "HOLDS" if ok else "FAILS", "| none8 1e-3 r_all", rng(b3), "| S4", rng(b3[:2]))
# B4
b4h = [extra(*p, HI, "iso-3") - extra(*p, HI, "inst-3") for p in PAIRS]
b4l = [extra(*p, LO, "iso-3") - extra(*p, LO, "inst-3") for p in PAIRS]
b4r = [extra(*p, HI, "iso-3") - extra(*p, LO, "iso-3") for p in PAIRS]
ok = all(x.mean() >= 0.04 for x in b4h) and all(x.mean() >= 0.02 for x in b4l) and all(x.mean() >= 0.02 for x in b4r)
say("B4", "HOLDS" if ok else "FAILS", "| 1e-3", rng(b4h), "| 2.5e-4", rng(b4l), "| rate", rng(b4r))
# B5: (mean over t and items of the equal-time gap) - |mean over t and items of the equal-births gap| >= 0.01
T5 = range(200, 1001, 100)
DD = lambda p, mu, t: d(*p, f"change4@{mu}", "iso-3", "inst-3", "trace", t)
et = pool([pool([DD(p, HI, t) - DD(p, LO, t) for t in T5]) for p in PAIRS])
eb = pool([pool([DD(p, HI, t) - DD(p, LO, 4 * t) for t in T5]) for p in PAIRS])
stat = et.mean() - abs(eb.mean())
rf = np.mean([np.mean([DD(p, HI, t).mean() for t in T5]) for p in PAIRS])
r_t = rf / np.mean([np.mean([DD(p, LO, t).mean() for t in T5]) for p in PAIRS])
r_b = rf / np.mean([np.mean([DD(p, LO, 4 * t).mean() for t in T5]) for p in PAIRS])
say("B5", "HOLDS" if stat >= 0.01 else "FAILS", "| equal time %+.4f equal births %+.4f statistic %+.4f | fast/slow %.2f (time) %.2f (births)" % (et.mean(), eb.mean(), stat, r_t, r_b))
# B6
b6a = pool([d(*p, f"change4@{HI}", "emt-1000", "inst-3", "trace", 200) for p in PAIRS]).mean()
g = lambda p, a: d(*p, f"change4@{HI}", a, "inst-3", "trace", 2000) - d(*p, f"change4@{HI}", a, "inst-3", "trace", 200)
b6b = {T: pool([g(p, "iso-3") - g(p, T) for p in PAIRS]).mean() for T in ("emt-300", "emt-1000")}
ok = b6a >= 0.15 and all(x >= 0.10 for x in b6b.values())
say("B6", "HOLDS" if ok else "FAILS", "| emt-1000 - inst-3 at t=200 %+.4f | growth iso-3 minus emt: %s" % (b6a, {k: round(x, 4) for k, x in b6b.items()}))
# B7
b7c = [d(*p, f"change4@{mu}", f"mat-{T}", f"iso-emt-{T}") for p in PAIRS for mu in (HI, LO) for T in ("300", "1000")]
b7e = [extra(*p, mu, f"mat-{T}") - extra(*p, mu, f"iso-emt-{T}") for p in PAIRS for mu in (HI, LO) for T in ("300", "1000")]
b7n = [d(*p, f"none8@{mu}", f"mat-{T}", f"iso-emt-{T}", "r_all") for p in PAIRS for mu in (HI, LO) for T in ("300", "1000")]
ok = all(abs(x.mean()) <= 0.03 for x in b7c) and all(abs(x.mean()) <= 0.005 for x in b7e) and all(abs(x.mean()) <= 0.001 for x in b7n)
say("B7", "HOLDS" if ok else "FAILS", "| change4", rng(b7c), "| extra loss", rng(b7e), "| none8", rng(b7n, "+.5f"))
# B8
b8 = pool([d(*p, f"change4@{HI}", "iso-emt-1000", "emt-1000") - d(*p, f"change4@{HI}", "iso-3", "inst-3") for p in PAIRS]).mean()
say("B8", "HOLDS" if b8 <= -0.08 else "FAILS", "| interaction %+.4f" % b8, "items", rng([d(*p, f"change4@{HI}", "iso-emt-1000", "emt-1000") - d(*p, f"change4@{HI}", "iso-3", "inst-3") for p in PAIRS]))
# B9
b9s = [d(*p, "regrow8@0", "iso-3", "inst-3") for p in PAIRS[:2]]
b9f = pool([d(*p, "regrow8@0", "iso-3", "inst-3") for p in PAIRS[2:]]).mean()
b9m = [d(*p, "regrow8@0", a, "iso-3") for p in PAIRS for a in ("mat-300", "mat-1000")]
ok = all(x.mean() >= 0.04 for x in b9s) and b9f >= 0.01 and all(x.mean() <= 0.045 for x in b9m)
say("B9", "HOLDS" if ok else "FAILS", "| S4", rng(b9s), "| F0 mean %+.4f" % b9f, "| mat - iso-3", rng(b9m))
# B10
b10 = pool([d(*p, "regrow8@0", "iso-3", "inst-3") - d(*p, "regrow+cue8@0", "iso-3", "inst-3") for p in PAIRS]).mean()
b10o = [d(*p, "regrow+cue8@0", "iso-3", "inst-3", "r_out") for p in PAIRS]
ok = b10 >= 0.03 and all(abs(x.mean()) <= 0.002 for x in b10o)
say("B10", "HOLDS" if ok else "FAILS", "| shrink %+.4f | r_out" % b10, rng(b10o, "+.5f"))

say("\n== panel T levels at t = 4,000 (ranges over the four pairs)")
for mu in (HI, LO):
    for a in AT:
        say(f"mu {mu:7s} {a:13s} change4 r_in {rng([v(*p, f'change4@{mu}', a) for p in PAIRS], '.3f'):>16s} | none8 r_all "
            f"{rng([v(*p, f'none8@{mu}', a, 'r_all') for p in PAIRS], '.3f'):>16s} | cue8 r_all {rng([v(*p, f'cue8@{mu}', a, 'r_all') for p in PAIRS], '.3f'):>16s}"
            + ("" if a == "cue" else f" | extra loss {rng([extra(*p, mu, a) for p in PAIRS], '+.4f')}"))
say("\n== new commitments per case by age bin (0, 1-31, 32-104, >=105), mean over the four pairs")
for mu in (HI, LO):
    for r in ("none8", "cue8", "change4"):
        say(mu, r, {a: [round(float(np.mean([v(*p, f"{r}@{mu}", a, "newc", k).mean() for p in PAIRS])), 2) for k in range(4)]
                    for a in ("inst-3", "iso-3", "mat-300", "mat-1000", "iso-emt-300", "iso-emt-1000")})
say("births per site over the window:", {mu: round(float(np.mean([np.mean([Z[(u, b, k)][f"none8@{mu}/births"].mean() for k in BLOCKS]) for u, b in PAIRS])), 4) for mu in (HI, LO)})

say("\n== time course at 1e-3, change4 r_in minus inst-3 (mean over pairs) at t = 100, 200, 500, 1000, 2000, 4000")
for a in ("iso-3", "emt-300", "iso-emt-300", "mat-300", "emt-1000", "iso-emt-1000", "mat-1000"):
    say(a, [round(float(pool([d(*p, f"change4@{HI}", a, "inst-3", "trace", t) for p in PAIRS]).mean()), 4) for t in (100, 200, 500, 1000, 2000, 4000)])
say("mat - iso-emt time course at 1e-3 (mean over pairs):",
    {T: [round(float(pool([d(*p, f"change4@{HI}", f"mat-{T}", f"iso-emt-{T}", "trace", t) for p in PAIRS]).mean()), 4) for t in (100, 200, 500, 1000, 4000)] for T in ("300", "1000")})

say("\n== panel W at t = 4,000")
for a in AW:
    say(f"{a:9s} regrow8 r_in S4 {rng([v(*p, 'regrow8@0', a) for p in PAIRS[:2]], '.3f')} F0 {rng([v(*p, 'regrow8@0', a) for p in PAIRS[2:]], '.3f')}"
        f" | regrow+cue8 r_in {rng([v(*p, 'regrow+cue8@0', a) for p in PAIRS], '.3f')} | r_out {rng([v(*p, 'regrow+cue8@0', a, 'r_out') for p in PAIRS], '.4f')}")

say("\n== intervals (95% t over blocks)")
for p in PAIRS:
    say(p, "B2 1e-3", ci(d(*p, f"change4@{HI}", "iso-3", "inst-3")), "| B2 2.5e-4", ci(d(*p, f"change4@{LO}", "iso-3", "inst-3")))
    say(p, "B9", ci(d(*p, "regrow8@0", "iso-3", "inst-3")), "| B8 item", ci(d(*p, f"change4@{HI}", "iso-emt-1000", "emt-1000") - d(*p, f"change4@{HI}", "iso-3", "inst-3")))


# ---- exact values for the report's tables (formerly verify_sc003_b.py) ----

def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x)); h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f]" % (m, m - h, m + h)
print("\n== change4 r_in at 4,000, mean of the four items (exact)")
for a in AT:
    print(f"{a:13s}", " ".join("%.6f" % pool([v(*p, f"change4@{mu}", a) for p in PAIRS]).mean() for mu in (HI, LO)))
print("\n== extra loss, mean of the four items (exact)")
for a in AT[1:]:
    print(f"{a:13s}", " ".join("%+.6f" % pool([extra(*p, mu, a) for p in PAIRS]).mean() for mu in (HI, LO)))
print("\n== contrasts (pooled over items, 95% t over blocks)")
for mu in (HI, LO):
    for T in ("300", "1000"):
        print(mu, T, "mat - emt", ci(pool([d(*p, f"change4@{mu}", f"mat-{T}", f"emt-{T}") for p in PAIRS])),
              "| emt - inst-3", ci(pool([d(*p, f"change4@{mu}", f"emt-{T}", "inst-3") for p in PAIRS])),
              "| mat - iso-emt", ci(pool([d(*p, f"change4@{mu}", f"mat-{T}", f"iso-emt-{T}") for p in PAIRS])))
    print(mu, "B2 iso-3 - inst-3", ci(pool([d(*p, f"change4@{mu}", "iso-3", "inst-3") for p in PAIRS])),
          "| B4 extra iso - inst", ci(pool([extra(*p, mu, "iso-3") - extra(*p, mu, "inst-3") for p in PAIRS])))
print("B8", ci(pool([d(*p, f"change4@{HI}", "iso-emt-1000", "emt-1000") - d(*p, f"change4@{HI}", "iso-3", "inst-3") for p in PAIRS])))
print("check on emt-1000 at 1e-3", ci(pool([d(*p, f"change4@{HI}", "iso-emt-1000", "emt-1000") for p in PAIRS])))
print("B6 emt-1000 at t=200", ci(pool([d(*p, f"change4@{HI}", "emt-1000", "inst-3", "trace", 200) for p in PAIRS])))
print("B9 mean", ci(pool([d(*p, "regrow8@0", "iso-3", "inst-3") for p in PAIRS])), "| B10", ci(pool([d(*p, "regrow8@0", "iso-3", "inst-3") - d(*p, "regrow+cue8@0", "iso-3", "inst-3") for p in PAIRS])))
print("B10 iso-3 - inst-3 under regrow+cue8", ci(pool([d(*p, "regrow+cue8@0", "iso-3", "inst-3") for p in PAIRS])))
print("B9 share of mat's advantage:", {T: round(float(pool([d(*p, "regrow8@0", "iso-3", "inst-3") for p in PAIRS]).mean() / pool([d(*p, "regrow8@0", f"mat-{T}", "inst-3") for p in PAIRS]).mean()), 4) for T in ("300", "1000")})
print("B7 tau1000 at 1e-3 / 2.5e-4", ci(pool([d(*p, f"change4@{HI}", "mat-1000", "iso-emt-1000") for p in PAIRS])), ci(pool([d(*p, f"change4@{LO}", "mat-1000", "iso-emt-1000") for p in PAIRS])))
print("\n== time course at 1e-3, change4 minus inst-3 (exact, mean over pairs)")
for a in ("iso-3", "emt-300", "emt-1000", "mat-300", "iso-emt-300", "mat-1000", "iso-emt-1000"):
    print(f"{a:13s}", " ".join("%+.6f" % pool([d(*p, f"change4@{HI}", a, "inst-3", "trace", t) for p in PAIRS]).mean() for t in (100, 200, 500, 1000, 2000, 3000, 4000)))
print("\n== age-0 commitments per case (x 1,024 sites), means by pattern")
for mu in (HI, LO):
    for r in ("none8", "cue8", "change4"):
        row = {}
        for a in ("inst-3", "iso-3", "mat-300", "mat-1000"):
            row[a] = [round(float(np.mean([v(*p, f"{r}@{mu}", a, "newc", 0).mean() for p in pp])) * 1024, 1) for pp in (PAIRS[:2], PAIRS[2:])]
        print(mu, r, row)
print("B1 exact inst/iso max", max(v(*p, f"{r}@{mu}", "inst-3", "newc", 0).mean() / v(*p, f"{r}@{mu}", "iso-3", "newc", 0).mean() for p in PAIRS for r in ("none8", "cue8") for mu in (HI, LO)))
print("births per site", {mu: float(np.mean([np.mean([Z[(u, b, k)][f"none8@{mu}/births"].mean() for k in BLOCKS]) for u, b in PAIRS])) for mu in (HI, LO)})
print("B3 exact", " ".join("%+.6f" % d(*p, f"none8@{HI}", "iso-3", "inst-3", "r_all").mean() for p in PAIRS))
print("B4 exact 1e-3", " ".join("%+.6f" % (extra(*p, HI, "iso-3") - extra(*p, HI, "inst-3")).mean() for p in PAIRS), "| 2.5e-4", " ".join("%+.6f" % (extra(*p, LO, "iso-3") - extra(*p, LO, "inst-3")).mean() for p in PAIRS), "| rate", " ".join("%+.6f" % (extra(*p, HI, "iso-3") - extra(*p, LO, "iso-3")).mean() for p in PAIRS))
print("B2 exact 1e-3", " ".join("%+.6f" % d(*p, f"change4@{HI}", "iso-3", "inst-3").mean() for p in PAIRS), "| 2.5e-4", " ".join("%+.6f" % d(*p, f"change4@{LO}", "iso-3", "inst-3").mean() for p in PAIRS))
print("B7 exact change4", sorted("%+.6f" % d(*p, f"change4@{mu}", f"mat-{T}", f"iso-emt-{T}").mean() for p in PAIRS for mu in (HI, LO) for T in ("300", "1000"))[::15])
print("B7 exact extra", sorted("%+.6f" % (extra(*p, mu, f"mat-{T}") - extra(*p, mu, f"iso-emt-{T}")).mean() for p in PAIRS for mu in (HI, LO) for T in ("300", "1000"))[::15])
print("B9 exact S4", " ".join("%+.6f" % d(*p, "regrow8@0", "iso-3", "inst-3").mean() for p in PAIRS), "| mat - iso", " ".join("%+.6f" % d(*p, "regrow8@0", a, "iso-3").mean() for p in PAIRS for a in ("mat-300", "mat-1000")))

# ---- B5 and B10 intervals (formerly verify_sc003_c.py) ----
def ci6(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x)); h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f] pos %d/%d" % (m, m - h, m + h, (x > 0).sum(), len(x))

T5 = range(200, 1001, 100)
DD = lambda p, mu, t: d(*p, f"change4@{mu}", "iso-3", "inst-3", "trace", t)
et = pool([pool([DD(p, HI, t) - DD(p, LO, t) for t in T5]) for p in PAIRS])
eb = pool([pool([DD(p, HI, t) - DD(p, LO, 4 * t) for t in T5]) for p in PAIRS])
print("\n== B5 equal time", ci6(et), "| equal births", ci6(eb), "| per-block stat", ci6(et - np.abs(eb)))
x = pool([d(*p, "regrow+cue8@0", "iso-3", "inst-3") for p in PAIRS]); print("B10 iso-3 - inst-3 under corruption", ci6(x), "neg blocks", int((x < 0).sum()))

print("done")
