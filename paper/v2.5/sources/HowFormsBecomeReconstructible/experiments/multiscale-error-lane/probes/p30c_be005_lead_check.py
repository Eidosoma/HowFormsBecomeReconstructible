"""P30c (python probes/p30c_be005_lead_check.py ROOT): the lead's check of BE005's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written and run by the lead after the development read,
29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_BE005.md from the registration's words (not from
be005.predict / be005.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/be005/development). Output: probes/results/p30c_be005_lead_check.txt.
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
from be005 import design as D  # noqa: E402  (run names, arms and reads only)

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
SM = json.load(open(LANE / "be005" / "frozen" / "static_map.json"))
DEL = {0.005: {0.5: 59, 1: 117, 2: 235, 4: 469, 16: 1876}, 0.01: {0.5: 29, 1: 58, 2: 117, 4: 234, 16: 936},
       0.02: {0.5: 15, 1: 29, 2: 58, 4: 116, 16: 466}}
for eta, row in DEL.items():           # the delays are round(m T*(eta)) with the design's own T*
    for m, dl in row.items():
        assert dl == round(m * D.t_star(eta)), (eta, m, dl, D.t_star(eta))


def v(u, b, run, arm, e="r_in", t=4000):
    ai = ARMS[run].index(arm)
    out = []
    for k in BLOCKS:
        x = Z[(u, b, k)][f"{run}/{e}"]
        out.append(x[ai].mean() if x.ndim == 2 else x[READS.index(t), ai].mean())
    return np.array(out)


def sens(u, b, run, arm):
    ai = ARMS[run].index(arm)
    return np.array([Z[(u, b, k)][f"{run}/anc_on"][ai].mean() / Z[(u, b, k)][f"{run}/n_anc"].mean() for k in BLOCKS])


def P(f):
    return np.mean([f(u, b) for u, b in PAIRS], 0)


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f] pos %d/%d" % (m, m - h, m + h, (x > 0).sum(), len(x))


res = {}


def part(name, x, thr, sense):
    m = x.mean()
    ok = {"ge": m >= thr, "le": m <= thr, "abs": abs(m) <= thr}[sense]
    res.setdefault(name.split()[0], []).append(bool(ok))
    print(f"{name:48s} {ci(x)}  rule {sense} {thr}  {'ok' if ok else 'MISS'}")


E = lambda eta: f"dial-e{eta}"
late = lambda u, b, eta, m: v(u, b, f"memory4@{DEL[eta][m]}", E(eta))
prompt = lambda u, b, eta: v(u, b, "memory4@0", E(eta))
loss = lambda u, b, eta, m: prompt(u, b, eta) - late(u, b, eta, m)
C = "change4@0"
a = lambda u, b, arm: v(u, b, C, arm)
print("\n== statements (pooled over the twelve unit-body pairs; t = 4,000)")
for eta in (0.005, 0.01, 0.02):
    for m in (0.5, 1):
        part(f"D1 late({eta},{m}) - prompt", P(lambda u, b: late(u, b, eta, m) - prompt(u, b, eta)), 0.02, "abs")
for eta in (0.005, 0.01, 0.02):
    for m in (2, 16):
        part(f"D2 late({eta},{m}) - prompt", P(lambda u, b: late(u, b, eta, m) - prompt(u, b, eta)), -0.05, "le")
part("D3 loss(0.02,2) - loss(0.005,0.5)", P(lambda u, b: loss(u, b, 0.02, 2) - loss(u, b, 0.005, 0.5)), 0.05, "ge")
for m in (2, 4, 16):
    part(f"D4 loss(0.02,{m}) - loss(0.005,{m})", P(lambda u, b: loss(u, b, 0.02, m) - loss(u, b, 0.005, m)), 0.02, "ge")
for eta in (0.005, 0.01, 0.02):
    for m in (0.5, 1):
        part(f"D5 sensors({eta},{m})", P(lambda u, b: sens(u, b, f"memory4@{DEL[eta][m]}", E(eta))), 0.05, "le")
    part(f"D5 sensors({eta},2)", P(lambda u, b: sens(u, b, f"memory4@{DEL[eta][2]}", E(eta))), 0.15, "ge")
part("D5 sensors(0.02,4) - sensors(0.005,4)", P(lambda u, b: sens(u, b, f"memory4@{DEL[0.02][4]}", E(0.02)) - sens(u, b, f"memory4@{DEL[0.005][4]}", E(0.005))), 0.1, "ge")
for eta in (0.005, 0.01, 0.02):
    part(f"D6 prompt({eta}) - never", P(lambda u, b: prompt(u, b, eta) - v(u, b, "memory4@0", f"never-e{eta}")), 0.2, "ge")
part("M1 tv100 - t1-tv100", P(lambda u, b: a(u, b, "dial-tv100") - a(u, b, "dial-t1-tv100")), 0.1, "ge")
part("M1 tv100 - t10-tv100", P(lambda u, b: a(u, b, "dial-tv100") - a(u, b, "dial-t10-tv100")), 0.1, "ge")
part("M1 t1-tv1 - tv1", P(lambda u, b: a(u, b, "dial-t1-tv1") - a(u, b, "dial-tv1")), 0.005, "abs")
part("M2 tv100 - f0.25-tv100", P(lambda u, b: a(u, b, "dial-tv100") - a(u, b, "dial-f0.25-tv100")), 0.05, "ge")
part("M2 f0.25-tv1 - tv1", P(lambda u, b: a(u, b, "dial-f0.25-tv1") - a(u, b, "dial-tv1")), 0.005, "abs")
part("M3 t10-tv10 - t1-tv10", P(lambda u, b: a(u, b, "dial-t10-tv10") - a(u, b, "dial-t1-tv10")), 0.05, "ge")
part("M3 t100-tv10 - t10-tv10", P(lambda u, b: a(u, b, "dial-t100-tv10") - a(u, b, "dial-t10-tv10")), 0.05, "ge")
part("M3 t100-tv100 - t10-tv100", P(lambda u, b: a(u, b, "dial-t100-tv100") - a(u, b, "dial-t10-tv100")), 0.03, "ge")
chg = lambda u, b: a(u, b, "dial-tv1") - a(u, b, "dial-tv100")
mem = lambda u, b: v(u, b, "memory4@0", "dial-e0.01") - v(u, b, "memory4@0", "dial-tv100")
part("M4 change: tv1 - tv100", P(chg), 0.1, "ge")
part("M4 memory: tv1 - tv100", P(mem), 0.1, "ge")
part("M4 memory - change", P(lambda u, b: mem(u, b) - chg(u, b)), 0.03, "abs")
cost = lambda u, b, tv: v(u, b, "cue4@0", f"never-tv{tv}", "r_all") - v(u, b, "cue4@0", f"dial-tv{tv}", "r_all")
part("M6 cost(10) - cost(1)", P(lambda u, b: cost(u, b, 10) - cost(u, b, 1)), 0.0005, "le")
part("M6 cost(100) - cost(1)", P(lambda u, b: cost(u, b, 100) - cost(u, b, 1)), 0.0005, "le")
rel = SM["relaxation"]
lab = lambda tv: {"dial": f"dial-tv{tv}", "t1": f"dial-t1-tv{tv}", "t10": f"dial-t10-tv{tv}", "t100": f"dial-t100-tv{tv}",
                  "f0.5": f"dial-f0.5-tv{tv}", "f0.25": f"dial-f0.25-tv{tv}", "never": f"never-tv{tv}"}
m5 = []
for tv in ("1", "10"):
    names = lab(tv)
    for x, y in itertools.permutations(names, 2):
        if rel[tv][x] - rel[tv][y] >= 0.15:
            m5.append((tv, x, y, P(lambda u, b, x=x, y=y: a(u, b, names[x]) - a(u, b, names[y])).mean()))
res["M5"] = [all(g >= 0 for *_, g in m5)]
print(f"M5 {len(m5)} pairs; smallest run gap {min(g for *_, g in m5):+.6f} ({[p[:3] for p in m5 if p[3] == min(g for *_, g in m5)]}); {'ok' if res['M5'][0] else 'MISS'}")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== tables")
for eta in (0.005, 0.01, 0.02):
    print(f"eta {eta}: loss m 0.5/1/2/4/16:", " ".join("%.6f" % P(lambda u, b, m=m: loss(u, b, eta, m)).mean() for m in (0.5, 1, 2, 4, 16)),
          "| sensors m 0.5/1/2/4/16:", " ".join("%.6f" % P(lambda u, b, m=m: sens(u, b, f"memory4@{DEL[eta][m]}", E(eta))).mean() for m in (0.5, 1, 2, 4, 16)),
          "| onset m 0/0.5/1/2/4/16:", " ".join("%.6f" % P(lambda u, b, r=r: v(u, b, r, E(eta), "onset")).mean() for r in ["memory4@0"] + [f"memory4@{DEL[eta][m]}" for m in (0.5, 1, 2, 4, 16)]),
          "| prompt %.6f never %.6f" % (P(lambda u, b: prompt(u, b, eta)).mean(), P(lambda u, b: v(u, b, "memory4@0", f"never-e{eta}")).mean()))
    for m in (2, 16):
        print(f"   loss({eta},{m})", ci(P(lambda u, b: loss(u, b, eta, m))))
    print(f"   prompt gain({eta})", ci(P(lambda u, b: prompt(u, b, eta) - v(u, b, "memory4@0", f"never-e{eta}"))))
print("D3", ci(P(lambda u, b: loss(u, b, 0.02, 2) - loss(u, b, 0.005, 0.5))))
for m in (2, 4, 16):
    print(f"D4 m={m}", ci(P(lambda u, b: loss(u, b, 0.02, m) - loss(u, b, 0.005, m))))
print("D5 m=4 fast - slow", ci(P(lambda u, b: sens(u, b, f"memory4@{DEL[0.02][4]}", E(0.02)) - sens(u, b, f"memory4@{DEL[0.005][4]}", E(0.005)))))
print("D1 largest |late - prompt|:", max(abs(P(lambda u, b, e=e, m=m: late(u, b, e, m) - prompt(u, b, e)).mean()) for e in (0.005, 0.01, 0.02) for m in (0.5, 1)))
print("\nmembrane: adoption of a 4 x 4 change (pooled)")
for tv in (1, 10, 100):
    names = lab(str(tv))
    print(f"   tau_v {tv:3d}:", " ".join(f"{k} %.6f" % P(lambda u, b, n=n: a(u, b, n)).mean() for k, n in names.items()),
          "| triggered share (hit):", " ".join(f"{k} %.6f" % P(lambda u, b, n=n: v(u, b, C, n, "hit")).mean() for k, n in names.items() if k != "never"))
for nm_, f in (("M1 tv100 - t1", lambda u, b: a(u, b, "dial-tv100") - a(u, b, "dial-t1-tv100")), ("M1 t1-tv1 - tv1", lambda u, b: a(u, b, "dial-t1-tv1") - a(u, b, "dial-tv1")),
               ("M2 tv100 - f0.25", lambda u, b: a(u, b, "dial-tv100") - a(u, b, "dial-f0.25-tv100")), ("M2 f0.25-tv1 - tv1", lambda u, b: a(u, b, "dial-f0.25-tv1") - a(u, b, "dial-tv1")),
               ("M3 t10 - t1 @10", lambda u, b: a(u, b, "dial-t10-tv10") - a(u, b, "dial-t1-tv10")), ("M3 t100 - t10 @10", lambda u, b: a(u, b, "dial-t100-tv10") - a(u, b, "dial-t10-tv10")),
               ("M3 t100 - t10 @100", lambda u, b: a(u, b, "dial-t100-tv100") - a(u, b, "dial-t10-tv100")), ("M4 change", chg), ("M4 memory", mem),
               ("M4 memory - change", lambda u, b: mem(u, b) - chg(u, b)), ("M6 @10", lambda u, b: cost(u, b, 10) - cost(u, b, 1)), ("M6 @100", lambda u, b: cost(u, b, 100) - cost(u, b, 1))):
    print(f"   {nm_:22s}", ci(P(f)))
print("sham costs tau_v 1/10/100:", " ".join("%.6f" % P(lambda u, b, tv=tv: cost(u, b, tv)).mean() for tv in (1, 10, 100)))
print("memory4@0 triggered share (hit): dial-e0.01 %.6f  dial-tv100 %.6f" % (P(lambda u, b: v(u, b, "memory4@0", "dial-e0.01", "hit")).mean(), P(lambda u, b: v(u, b, "memory4@0", "dial-tv100", "hit")).mean()))
print("prompt onset (dial-e0.01, memory4@0)", ci(P(lambda u, b: v(u, b, "memory4@0", "dial-e0.01", "onset"))), "static", SM.get("evidence", {}).get("0.0", SM.get("evidence")))
r100 = lab("100")
pairs100 = [(x, y) for x, y in itertools.permutations(r100, 2) if rel["100"][x] - rel["100"][y] >= 0.15]
print("tau_v 100 (not registered):", len(pairs100), "pairs at >= 0.15; smallest run gap %+.6f" % min(P(lambda u, b, x=x, y=y: a(u, b, r100[x]) - a(u, b, r100[y])).mean() for x, y in pairs100),
      "| t100 - f0.5 at tau_v 100:", ci(P(lambda u, b: a(u, b, "dial-t100-tv100") - a(u, b, "dial-f0.5-tv100"))))
print("done")
