"""P51c (python probes/p51c_ar004_lead_check.py ROOT): the lead's check of AR004, the confirmed controller under misread
cues with a pooling detector. LEAD_CHECK_NOT_REGISTERED; a read of the shards and of the raw final states, written by
the lead in reviewing AR004's phase A and committed before the freeze, dry-run first on P51 (engineering blocks
900259-900262, tag mse-p51); 1 November 2026; no simulation.

It checks the sha256 of every shard and raw file against the run's manifest, the blocks, tag, runs, arms and detectors
of every shard (vms = DET_STAR; vpool = pool-n3-q1-r1, DET_STAR with one disagreeing anchor tolerated in the surround),
and at the development stage the run's digest against ar004/frozen/design.json and the thresholds against
ar004/frozen/predictions.json; then:
1. recomputes the parts from REGISTRATION_AR004.md's words, not from ar004.analyze, ar004.predict or ar003.analyze,
   unrounded:
   - u(arm, run): the record's agreement with the correct target inside the run's patch at t = 8,000 (r_in), pooled per
     case over the eight unit-body pairs; the vote's sigma-1 value is its sigma-0 run's (it never reads the cue);
   - R1, R0 and W1 the means over the sizes 2, 4 and 8 of u(vpool, memory@1) - u(vms, memory@1), of u(vpool, memory@0) -
     u(vms, memory@0), and of u(vpool, memory@1) - u(vote, memory@0);
   - the sheet's cost r_all(vote) - r_all(arm) at t = 8,000 (for a sigma-1 run, the vote's sigma-0 run); give = u(arm) -
     u(vote) in the 4 x 4 patch; located = fired at all (det_on > 0) with the footprint on a patch cell (det_fp_in > 0),
     pooled per case;
   - a block's value the mean over its 8 cases; SD_block the larger of the SD over the block values and the SD over every
     case / sqrt 8; the 95% t interval; on the probe the margins (>= 3 sqrt(1/4 + 1/16)) and both halves;
   - registered as the lead ruled on phase A: G1, G2, G3 (a, b and c, the last the confirmed 0.002 bound with no event),
     G5 (none@0, none@1), G6 (4 x 4, 8 x 8, the difference at 4 x 4), G7; reported: G5's cue@0 part (the trade-off inside
     the patch) and the dropped G4 (the sheet's cost under misreads with no event);
2. from the raw final states, with the lead's own scoring (the patch from LR005's frozen draw, be001.sim.patch):
   - every run's r_in and r_all recomputed from the final records;
   - a vote-default arm that never fired equals the vote bit for bit (both records): at sigma 0 within its own run, and at
     sigma 1 against the vote's sigma-0 run of the same situation and size (the vote never reads the cue);
3. reported: the recovery fraction, the misread losses of both arms, the rates by run.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from be001 import sim as B1S                                     # noqa: E402  (frozen: LR005's patch draw)
from mse.assay import Case                                       # noqa: E402  (frozen engine: the case keys)

ROOT = Path(sys.argv[1])
M = json.load(open(ROOT / "manifest.json"))
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values()
       if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
DEV = [910017, 910018, 910019, 910057, 910058, 910059, 910077, 910078, 910079, 910097, 910098, 910099, 910117, 910118,
       910119, 910137]
WANT = {"probe": ("mse-p51", [900259, 900260, 900261, 900262]), "development": ("mse-ar004", DEV)}
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == WANT[STAGE][0] and not bad, (STAGE, M["tag"], bad[:5])
BLOCKS = list(M["blocks"])
assert BLOCKS == WANT[STAGE][1], BLOCKS
NB = len(BLOCKS)
AR003 = "d392002671e648280d9746a336276d9fbf03e17d44c7d144802d9b7f9e84a47e"
FZ3 = json.load(open(LANE / "ar003" / "frozen" / "design.json"))
assert FZ3["digest"] == AR003 == M["ar003_digest"]
changed = [p for p, h in FZ3["sources"].items() if hashlib.sha256((LANE / p).read_bytes()).hexdigest() != h]
assert not changed, changed
# the parts and thresholds (REGISTRATION_AR004.md, as the lead ruled on phase A); sense, threshold
TH = {"G1": ("ge", 0.04), "G2": ("ge", -0.005), "G3a": ("ge", 0.008), "G3b": ("le", 0.029), "G3c": ("le", 0.002),
      "G5n": ("ge", -0.005), "G5n1": ("ge", -0.03), "G6_4": ("ge", 0.25), "G6_8": ("ge", 0.30), "G6d": ("ge", 0.04),
      "G7": ("ge", 0.09)}
if STAGE == "development":
    FZ = json.load(open(LANE / "ar004" / "frozen" / "design.json"))
    assert FZ["digest"] == M["design_digest"], "the draw is not under the frozen design"
    PR = json.load(open(LANE / "ar004" / "frozen" / "predictions.json"))
    got = {p["key"]: (p["sense"], float(p["threshold"])) for p in PR["parts"]}
    assert got == TH, ("the frozen thresholds differ from the registration's as the lead read it", got)
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
say(f"P51c on {ROOT} ({STAGE}{', DRY RUN on engineering blocks' if STAGE != 'development' else ''}): {len(M['tasks'])} "
    f"tasks, {sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the manifest's; digest "
    f"{M['design_digest'][:12]} (AR003's {AR003[:12]}, its {len(FZ3['sources'])} frozen sources unchanged); "
    f"{M['started_utc']} - {M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h, {M['workers']} workers")
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
assert len(M["tasks"]) == len(PAIRS) * NB
Z = {(b, u, k): dict(np.load(ROOT / "shards" / b / u / f"{k}.npz")) for b, u in PAIRS for k in BLOCKS}
META = {key: json.loads(str(z["__meta__"])) for key, z in Z.items()}
M0 = META[(*PAIRS[0], BLOCKS[0])]
RUNS = {rn: arms for rn, arms in M0["runs"]}
SIZES = M0["sizes"]
STAR = {"boxes": list(range(2, 13)), "n": 3, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}
POOL = dict(STAR, ring_max=1)
WANT_RUNS = {**{f"memory@0{s}": ["vote", "vms", "vpool"] for s in ("-L2", "", "-L8")}, "none@0": ["vote", "vms", "vpool"],
             "cue@0": ["vote", "vms", "vpool"], **{f"memory@1{s}": ["vms", "vpool"] for s in ("-L2", "", "-L8")},
             "none@1": ["vms", "vpool"]}
assert {k: v for k, v in RUNS.items() if "-L6" not in k} == WANT_RUNS, RUNS
for (b, u, k), m in META.items():
    assert {rn: a for rn, a in m["runs"]} == RUNS and m["sizes"] == SIZES and (m["body"], m["unit"], int(m["block"])) == (b, u, k)
    assert m["study"] == "AR004" and m["tag"] == M["tag"] and m["design_digest"] == M["design_digest"]
    assert m["vd_detectors"]["vms"] == {"cue": STAR, "body": None} and m["vd_detectors"]["vpool"] == {"cue": POOL, "body": None}
    assert m["det_pool_name"] == "pool-n3-q1-r1" and len(m["cases"]) == 8 and all(int(c[0]) == k for c in m["cases"])
RI = M0["reads"].index(8000)
say("runs: " + ", ".join(f"{r} (L {SIZES[r]}; {', '.join(a)})" for r, a in RUNS.items()))


def lc(run, arm, e, ri=RI):
    """(blocks, pairs, cases): one endpoint per lineage-case; ri None for a scalar."""
    i = RUNS[run].index(arm)
    return np.array([[(Z[(b, u, k)][f"{run}/{e}"][ri, i] if ri is not None else Z[(b, u, k)][f"{run}/{e}"][i])
                      for b, u in PAIRS] for k in BLOCKS], float)


pool = lambda x: x.mean(1)
rname = lambda s, L, sg: f"{s}@{sg}" + ("" if L == 4 else f"-L{L}")


def u(arm, s, L=4, sg=0):
    run = rname(s, L, sg)
    if arm not in RUNS[run]:
        assert arm == "vote"
        run = rname(s, L, 0)                                    # the vote never reads the cue
    return pool(lc(run, arm, "r_in"))


def sham(run, arm):
    ref = run if "vote" in RUNS[run] else run.replace("@1", "@0")
    return pool(lc(ref, "vote", "r_all") - lc(run, arm, "r_all"))


located = lambda arm, run: pool(((lc(run, arm, "det_on", None) > 0) & (lc(run, arm, "det_fp_in", None) > 0)).astype(float))
fired = lambda arm, run: pool((lc(run, arm, "det_on", None) > 0).astype(float))
over = lambda a, b, sa, sb: sum(u(a, "memory", L, sa) - u(b, "memory", L, sb) for L in (2, 4, 8)) / 3
X = {"G1": over("vpool", "vms", 1, 1), "G2": over("vpool", "vms", 0, 0),
     "G3a": sham("cue@0", "vpool") - sham("cue@0", "vms"), "G3b": sham("cue@0", "vpool"), "G3c": sham("none@0", "vpool"),
     "G5n": u("vpool", "none") - u("vote", "none"), "G5n1": u("vpool", "none", 4, 1) - u("vote", "none"),
     "G6_4": located("vpool", "memory@1"), "G6_8": located("vpool", "memory@1-L8"),
     "G6d": located("vpool", "memory@1") - located("vms", "memory@1"), "G7": over("vpool", "vote", 1, 0)}
REP = {"G5c (reported: the trade-off inside the patch) u(vpool) - u(vote), cue@0": u("vpool", "cue") - u("vote", "cue"),
       "G4 (dropped) sheet cost under misreads with no event, vpool": sham("none@1", "vpool"),
       "sheet cost none@1, vms": sham("none@1", "vms"), "sheet cost cue@0, vms": sham("cue@0", "vms"),
       "sheet cost none@0, vms": sham("none@0", "vms"), "W1 vms": over("vms", "vote", 1, 0),
       "vms misread loss (sigma 1 - sigma 0)": over("vms", "vms", 1, 0),
       "vpool misread loss (sigma 1 - sigma 0)": over("vpool", "vpool", 1, 0),
       **{f"R1 at {L} x {L}": u("vpool", "memory", L, 1) - u("vms", "memory", L, 1) for L in (2, 4, 8)},
       **{f"R0 at {L} x {L}": u("vpool", "memory", L, 0) - u("vms", "memory", L, 0) for L in (2, 4, 8)}}
WORDS = {"G1": "R1 = (1/3) sum over sizes of u(vpool, memory@1) - u(vms, memory@1)",
         "G2": "R0 = (1/3) sum over sizes of u(vpool, memory@0) - u(vms, memory@0)",
         "G3a": "the trade-off: sheet cost under cue@0, vpool less vms", "G3b": "vpool's sheet cost under cue@0",
         "G3c": "vpool's sheet cost with no event, none@0 (the confirmed 0.002 bound)",
         "G5n": "u(vpool) - u(vote) in the 4 x 4 patch, none@0", "G5n1": "u(vpool, none@1) - u(vote, none@0), 4 x 4 patch",
         "G6_4": "p(vpool on the patch | memory@1, 4 x 4)", "G6_8": "p(vpool on the patch | memory@1, 8 x 8)",
         "G6d": "p(on the patch | memory@1, 4 x 4), vpool - vms", "G7": "W1 = (1/3) sum over sizes of u(vpool, memory@1) - u(vote, memory@0)"}
T975 = stats.t.ppf(0.975, NB - 1)
KR = 3 * math.sqrt(1 / 4 + 1 / 16)


def est(x):
    blk = x.mean(1)
    v = float(blk.mean())
    sdb, sdc = float(blk.std(ddof=1)), float(x.ravel().std(ddof=1)) / math.sqrt(x.shape[1])
    sd = max(sdb, sdc)
    h = T975 * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sdb": sdb, "sdc": sdc,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean()))}


ci = lambda q: f"{q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, case/sqrt8 {q['sdc']:.6f})"
say(f"\nREGISTERED PARTS ({NB} blocks; pooled over the eight unit-body pairs; [95% t interval], t(0.975, {NB - 1}) = "
    f"{T975:.4f}; SD_block the larger of the block SD and the case SD / sqrt 8"
    + (f"; the rule: margin >= {KR:.4f} and both halves" if STAGE == "probe" else "") + ")")
res = {}
for key, (sense, th) in TH.items():
    q = est(X[key])
    ok = q["v"] >= th if sense == "ge" else q["v"] <= th
    res.setdefault(key[:2], []).append(ok)                      # the statement: G1 ... G7
    say(f"  {key:5s} {WORDS[key]}: {ci(q)}  {'>=' if sense == 'ge' else '<='} {th:+}: {'holds' if ok else 'FAILS'}")
    if STAGE == "probe":
        marg = ((q["v"] - th) if sense == "ge" else (th - q["v"])) / q["sd"] if q["sd"] > 0 else math.inf
        hok = all((h >= th) if sense == "ge" else (h <= th) for h in q["halves"])
        say(f"        margin {marg:.4f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f}; rule "
            f"{'ok' if hok and marg >= KR else 'NOT MET'}{' (SD 0: a declared allowance)' if q['sd'] == 0 else ''}")
say("  VERDICTS: " + ", ".join(f"{k} {'HOLDS' if all(v) else 'FAILS'}" for k, v in res.items())
    + ("  [a dry run on engineering blocks: not a development result]" if STAGE != "development" else ""))
say("\nREPORTED (not registered)")
for name, x in REP.items():
    say(f"  {name}: {ci(est(x))}")
num, den = over("vpool", "vms", 1, 1), over("vms", "vms", 0, 1)
say(f"  the recovery fraction, pooled over the sizes: {num.mean() / den.mean():.4f}; by size: "
    + "; ".join(f"{L} x {L} {(u('vpool', 'memory', L, 1) - u('vms', 'memory', L, 1)).mean() / (u('vms', 'memory', L, 0) - u('vms', 'memory', L, 1)).mean():.4f}"
                for L in (2, 4, 8)))
say("  rates by run (fired at all / on the patch):")
for run, arms in RUNS.items():
    for a in [x for x in arms if x != "vote"]:
        say(f"    {run:13s} {a:5s} {fired(a, run).mean():.4f} / {located(a, run).mean():.4f}")

# ---------- 2. the raw final states ----------
rin_max = rall_max = 0.0
n_checked = same_n = same_bad = 0
for b, u_ in PAIRS:
    for k in BLOCKS:
        raw = np.load(ROOT / "raw" / b / u_ / f"{k}.npz")
        m = META[(b, u_, k)]
        cases = [Case(*c) for c in m["cases"]]
        T = raw["T"]
        pt = {L: B1S.patch(cases, L, m["tag"]) for L in (2, 4, 6, 8)}
        ins = lambda x, mm: (((x > 0) == (T > 0)) & mm).sum((-2, -1)) / mm.sum((-2, -1))
        for run, arms in RUNS.items():
            r = raw[f"{run}/r"]
            L = SIZES[run]
            for i, a in enumerate(arms):
                rin_max = max(rin_max, float(np.abs(ins(r[i], pt[L]) - Z[(b, u_, k)][f"{run}/r_in"][RI, i]).max()))
                rall_max = max(rall_max, float(np.abs(((r[i] > 0) == (T > 0)).mean((-2, -1)) - Z[(b, u_, k)][f"{run}/r_all"][RI, i]).max()))
                n_checked += 1
            ref = run if "vote" in arms else run.replace("@1", "@0")
            rv, rbv = raw[f"{ref}/r"][RUNS[ref].index("vote")], raw[f"{ref}/rB"][0]      # the vote's rB row comes first
            rb_arms = [x for x in m["parts"][run][0] if x == "vote"] + m["parts"][run][2]
            rB = raw[f"{run}/rB"]
            for a in ("vms", "vpool"):
                ia, never = arms.index(a), Z[(b, u_, k)][f"{run}/det_on"][arms.index(a)] < 0
                for j in np.flatnonzero(never):
                    same_n += 1
                    same_bad += int(not (np.array_equal(r[ia, j], rv[j]) and np.array_equal(rB[rb_arms.index(a), j], rbv[j])))
say(f"\nFROM THE RAW FINAL STATES (the lead's own scoring; the patch from be001.sim.patch): r_in and r_all recomputed "
    f"from the final records, {n_checked} arm-runs x 8 cases: largest difference {rin_max:.2e} and {rall_max:.2e}; a "
    f"vote-default arm that never fired against the vote (at sigma 1 the vote's sigma-0 run), both records, bit for bit: "
    f"{same_n - same_bad} of {same_n} lineage-cases equal")
assert rin_max <= 1e-12 and rall_max <= 1e-12 and same_bad == 0

name = f"p51c_ar004_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
