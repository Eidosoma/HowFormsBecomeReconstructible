"""P47d (python probes/p47d_ar003c_lead_check.py ROOT [READER]): the lead's check of AR003C, AR003's confirmation on
fresh blocks. LEAD_CHECK_NOT_REGISTERED; a read of the shards and of the raw final states, written by the lead in
reviewing AR003C's phase A and committed before the freeze and before any confirmation block is drawn, dry-run first on
AR003C's debug run (engineering blocks 900162-900163, tag mse-ar003); 1 November 2026; no simulation.

It checks the sha256 of every shard and raw file against the run's manifest, the blocks, tag and purpose of every shard,
the detectors in every shard's meta against AR003's frozen ones, and, at the confirmation stage, the run's digest and
sources against the frozen design's (ar003c/frozen/design.json), the frozen qualification receipt's PASS, and AR003's
frozen sources against the files now; then:
1. recomputes the three registered criteria from REGISTRATION_AR003C.md's words, not from ar003c.analyze,
   ar003c.predict or ar003.analyze, unrounded:
   - u_L(arm, s): the record's agreement with the scoring's correct target inside the L-patch at t = 8,000 (r_in; for
     none and cue at L 2 and 8, r_in_L<L> of the 4 x 4 run), pooled: per case the mean over the eight unit-body pairs;
     U_L the mean over the eight scorings, the information-limit pair contributing u(new) + u(old) of change@0 at L 4
     for the arms run there (the vote and vms) and exactly 1 otherwise; U_mix the mean of U_2, U_4, U_8;
   - C1 U_mix(vms) - U_mix(vote), lower bound above 0; C2 U_8(vms) - U_8(det), lower bound above 0; C3 the sheet cost
     r_all(vote) - r_all(vms) at t = 8,000, upper bounds at most 0.01 in cue@0 and at most 0.002 in none@0;
   - a block's value the mean over its 8 cases; SD the larger of the SD over the n block values and the SD over the
     n x 8 case values / sqrt 8; the 95% interval the mean +- t(0.975, n - 1) SD / sqrt n; CONFIRMED only if all three
     hold;
2. from the raw final states, with the lead's own scoring (the patch from LR005's frozen draw, be001.sim.patch):
   - every run's r_in (and r_in_L2, r_in_L8 for none and cue) and r_all recomputed from the final records;
   - a vote-default arm that never fired equals the vote bit for bit (both records), per lineage-case;
   - u(new) + u(old) = 1 in change@0, for every arm and case;
3. reported: U by arm and size, the half-widths against their targets, the SDs against the development's, C1's and
   C2's differences from the development with a z, the contrasts per unit-body pair, and the rates by run;
4. with READER (the frozen reader's confirmation.json): its bounds, means and verdict against this check's;
5. at the debug stage, the bridge, independently of ar003c.checks' Q3: every array of every debug task on 900162 against
   the reference stage's AR003 full task there (ROOT/../reference, ar003.worker.run_task, 17 runs and 63 arm-runs),
   byte for byte; an array of the same arms is compared whole, one with an arm axis arm slice by arm slice, the arms
   matched by name from each shard's meta (all arms for endpoints, scalars, traces and V, r, H, W; the detector parts'
   arms for zone and fp; the vote's and the vote-default arms' second records for rB, HB, WB).

Extended 1 November 2026, after the confirmation's results and before the lead's report (git shows the diff): reported
only, U_4(vms) - U_4(vote) in its terms (the hits, the four scorings where nothing needs correcting, the pair) and the
block ranges of the criteria. Nothing in the registered criteria or the checks changed.
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
WANT = {"debug": ([900162, 900163], "engineering"), "confirmation": (list(range(920365, 920381)), "confirmation")}
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == "mse-ar003" and not bad, (STAGE, M["tag"], bad[:5])
BLOCKS, PURPOSE = list(M["blocks"]), WANT[STAGE][1]
assert BLOCKS == WANT[STAGE][0], BLOCKS
NB = len(BLOCKS)
AR003 = "d392002671e648280d9746a336276d9fbf03e17d44c7d144802d9b7f9e84a47e"
FZ3 = json.load(open(LANE / "ar003" / "frozen" / "design.json"))
assert FZ3["digest"] == AR003 == M["ar003_digest"]
changed = [p for p, h in FZ3["sources"].items() if hashlib.sha256((LANE / p).read_bytes()).hexdigest() != h]
assert not changed, changed
if STAGE == "confirmation":
    FZ = json.load(open(LANE / "ar003c" / "frozen" / "design.json"))
    RC = json.load(open(LANE / "ar003c" / "frozen" / "qualification_receipt.json"))
    assert FZ["digest"] == M["design_digest"] == RC["design_digest"] and RC["status"] == "PASS", "not under the frozen design"
    assert M["sources"] == FZ["sources"], "the run's sources are not the frozen ones"
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
say(f"P47d on {ROOT} ({STAGE}{', DRY RUN on engineering blocks' if STAGE != 'confirmation' else ''}): {len(M['tasks'])} "
    f"tasks, {sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the manifest's; digest "
    f"{M['design_digest'][:12]} (AR003's {AR003[:12]}, its {len(FZ3['sources'])} frozen sources unchanged); "
    f"{M['started_utc']} - {M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h, {M['workers']} workers, peak "
    f"worker RSS {M['worker_maxrss_mb_peak']} MB")
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
assert len(M["tasks"]) == len(PAIRS) * NB
Z = {(b, u, k): dict(np.load(ROOT / "shards" / b / u / f"{k}.npz")) for b, u in PAIRS for k in BLOCKS}
META = {key: json.loads(str(z["__meta__"])) for key, z in Z.items()}
M0 = META[(*PAIRS[0], BLOCKS[0])]
RUNS = {rn: arms for rn, arms in M0["runs"]}
SIZES = M0["sizes"]
STAR = {"boxes": list(range(2, 13)), "n": 3, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}
DET = {"box": 4, "n": 2, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}
WANT_RUNS = {"none@0": ["vote", "det", "vms"], "body@0": ["vote", "vms"], "memory@0": ["vote", "vms"],
             "correlated@0": ["vote", "vms"], "shared@0": ["vote", "vms"], "cue@0": ["vote", "det", "vms"],
             "change@0": ["vote", "vms"], **{f"{s}@0-L2": ["vote", "vms"] for s in ("memory", "correlated", "body", "shared")},
             **{f"{s}@0-L8": ["vote", "det", "vms"] for s in ("memory", "correlated", "body", "shared")}}
assert RUNS == WANT_RUNS, RUNS
for (b, u, k), m in META.items():
    assert {rn: a for rn, a in m["runs"]} == RUNS and m["sizes"] == SIZES and (m["body"], m["unit"], int(m["block"])) == (b, u, k)
    assert m["study"] == "AR003C" and m["purpose"] == PURPOSE and m["tag"] == M["tag"]
    assert m["design_digest"] == M["design_digest"] and m["ar003_digest"] == AR003
    assert m["vd_detectors"] == {"vms": {"cue": STAR, "body": None}} and m["detectors"]["det"]["cue"] == DET
    assert len(m["cases"]) == 8 and all(int(c[0]) == k for c in m["cases"])
RI = M0["reads"].index(8000)
say("runs: " + ", ".join(f"{r} (L {SIZES[r]}; {', '.join(a)})" for r, a in RUNS.items()))


def lc(run, arm, e, ri=RI):
    """(blocks, pairs, cases): one endpoint per lineage-case; ri None for a scalar."""
    i = RUNS[run].index(arm)
    return np.array([[(Z[(b, u, k)][f"{run}/{e}"][ri, i] if ri is not None else Z[(b, u, k)][f"{run}/{e}"][i])
                      for b, u in PAIRS] for k in BLOCKS], float)


SC = ("none", "body", "memory", "correlated", "shared", "cue")
FREE = ("none", "cue")


def u_lc(arm, s, L):
    if s in FREE:                                               # r_in_L<L> is scored once, at the last read
        return lc(f"{s}@0", arm, "r_in") if L == 4 else lc(f"{s}@0", arm, f"r_in_L{L}", None)
    return lc(f"{s}@0" if L == 4 else f"{s}@0-L{L}", arm, "r_in")


def U_lc(arm, L):
    """(blocks, pairs, cases): U_L per lineage-case, before pooling."""
    tot = sum(u_lc(arm, s, L) for s in SC)
    if L == 4 and arm in RUNS["change@0"]:
        tot = tot + lc("change@0", arm, "r_in") + lc("change@0", arm, "r_in_old")
    else:
        tot = tot + 1.0                                         # the pair's exact contribution (the identity)
    return tot / 8


pool = lambda x: x.mean(1)
U = lambda arm, L: pool(U_lc(arm, L))
Umix_lc = lambda arm: (U_lc(arm, 2) + U_lc(arm, 4) + U_lc(arm, 8)) / 3
C1_lc = lambda: Umix_lc("vms") - Umix_lc("vote")
C2_lc = lambda: U_lc("vms", 8) - U_lc("det", 8)
cost_lc = lambda run, arm="vms": lc(run, "vote", "r_all") - lc(run, arm, "r_all")
fire = lambda arm, run: lc(run, arm, "det_on", None) > 0
onpatch = lambda arm, run: fire(arm, run) & (lc(run, arm, "det_fp_in", None) > 0)
T975 = stats.t.ppf(0.975, NB - 1)


def est(x):
    """x (blocks, cases), pooled: the registered interval."""
    blk = x.mean(1)
    v = float(blk.mean())
    sdb = float(blk.std(ddof=1)) if NB > 1 else 0.0
    sdc = float(x.ravel().std(ddof=1)) / math.sqrt(x.shape[1])
    sd = max(sdb, sdc)
    h = T975 * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "h": h, "sd": sd, "sdb": sdb, "sdc": sdc, "blocks": [float(y) for y in blk]}


ci = lambda q: f"{q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, case/sqrt8 {q['sdc']:.6f})"
DEV = {"c1": (0.108527, 0.011201), "c2": (0.149961, 0.021990), "sham_cue": (0.005635, 0.002433),
       "sham_none": (-0.000035, 0.000102)}                     # AR003's development, 16 blocks (ar003c.design.DEV)
TARGET = {"c1": 0.108527 / 3, "c2": 0.149961 / 3}

say(f"\nREGISTERED CRITERIA ({NB} blocks; pooled over the eight unit-body pairs; 95% t interval, t(0.975, {NB - 1}) = "
    f"{T975:.4f}; SD the larger of the block SD and the case SD / sqrt 8)")
Q = {"c1": est(pool(C1_lc())), "c2": est(pool(C2_lc())), "sham_cue": est(pool(cost_lc("cue@0"))),
     "sham_none": est(pool(cost_lc("none@0")))}
ok = {"C1": Q["c1"]["lo"] > 0, "C2": Q["c2"]["lo"] > 0, "C3": Q["sham_cue"]["hi"] <= 0.01 and Q["sham_none"]["hi"] <= 0.002}
say(f"  C1 U_mix(vms) - U_mix(vote): {ci(Q['c1'])}; lower bound > 0: {'holds' if ok['C1'] else 'FAILS'}")
say(f"  C2 U_8(vms) - U_8(det): {ci(Q['c2'])}; lower bound > 0: {'holds' if ok['C2'] else 'FAILS'}")
say(f"  C3 cue@0 r_all(vote) - r_all(vms): {ci(Q['sham_cue'])}; upper bound <= 0.01: "
    f"{'holds' if Q['sham_cue']['hi'] <= 0.01 else 'FAILS'}")
say(f"  C3 none@0 r_all(vote) - r_all(vms): {ci(Q['sham_none'])}; upper bound <= 0.002: "
    f"{'holds' if Q['sham_none']['hi'] <= 0.002 else 'FAILS'}")
VERDICT = "CONFIRMED" if all(ok.values()) else "NOT CONFIRMED"
say(f"  VERDICT: {VERDICT}" + (f" (failed: {', '.join(k for k, v in ok.items() if not v)})" if not all(ok.values()) else "")
    + ("  [a dry run on engineering blocks: not a confirmation result]" if STAGE != "confirmation" else ""))
ident = max(float(np.abs(Z[(b, u, k)]["change@0/r_in"][RI, i] + Z[(b, u, k)]["change@0/r_in_old"][RI, i] - 1).max())
            for b, u in PAIRS for k in BLOCKS for i in range(len(RUNS["change@0"])))
say(f"  the identity: largest |u(new) + u(old) - 1| over every arm and case in change@0: {ident:.3e}")
assert ident <= 1e-12

# ---------- 2. the raw final states ----------
say("\nFROM THE RAW FINAL STATES (the lead's own scoring; the patch from be001.sim.patch)")
rin_max = rall_max = 0.0
n_checked = same_n = same_bad = 0
for b, u in PAIRS:
    for k in BLOCKS:
        raw = np.load(ROOT / "raw" / b / u / f"{k}.npz")
        m = META[(b, u, k)]
        cases = [Case(*c) for c in m["cases"]]
        T = raw["T"]
        pt = {L: B1S.patch(cases, L, m["tag"]) for L in (2, 4, 8)}
        for run, arms in RUNS.items():
            if run.startswith("change"):
                continue
            r = raw[f"{run}/r"]
            L = SIZES[run]
            ins = lambda x, mm: (((x > 0) == (T > 0)) & mm).sum((-2, -1)) / mm.sum((-2, -1))
            for i, a in enumerate(arms):
                rin_max = max(rin_max, float(np.abs(ins(r[i], pt[L]) - Z[(b, u, k)][f"{run}/r_in"][RI, i]).max()))
                rall_max = max(rall_max, float(np.abs(((r[i] > 0) == (T > 0)).mean((-2, -1)) - Z[(b, u, k)][f"{run}/r_all"][RI, i]).max()))
                if run in ("none@0", "cue@0"):
                    for L2 in (2, 8):
                        rin_max = max(rin_max, float(np.abs(ins(r[i], pt[L2]) - Z[(b, u, k)][f"{run}/r_in_L{L2}"][i]).max()))
                n_checked += 1
            rb_arms = [a for p in m["parts"][run] for a in p if a in ("vote", "vms")]
            rB = raw[f"{run}/rB"]
            iv, im = arms.index("vote"), arms.index("vms")
            never = Z[(b, u, k)][f"{run}/det_on"][im] < 0
            for j in np.flatnonzero(never):
                same_n += 1
                same_bad += int(not (np.array_equal(r[iv, j], r[im, j])
                                     and np.array_equal(rB[rb_arms.index("vote"), j], rB[rb_arms.index("vms"), j])))
say(f"  r_in (and none's and cue's r_in_L2, r_in_L8) and r_all recomputed from the final records, {n_checked} arm-runs x 8 "
    f"cases: largest difference {rin_max:.2e} and {rall_max:.2e}")
say(f"  vms where it never fired against the vote, both records, bit for bit: {same_n - same_bad} of {same_n} lineage-cases equal")
assert rin_max <= 1e-12 and rall_max <= 1e-12 and same_bad == 0

# ---------- 3. reported ----------
say("\nREPORTED (not registered)")
for key, name in (("c1", "C1"), ("c2", "C2")):
    q, (dv, dsd) = Q[key], DEV[key]
    z = (q["v"] - dv) / math.sqrt(q["sd"] ** 2 / NB + dsd ** 2 / 16)
    say(f"  {name}: half-width {q['h']:.6f} against the target {TARGET[key]:.6f}; SD {q['sd']:.6f} against the "
        f"development's {dsd:.6f} (ratio {q['sd'] / dsd:.3f}); difference from the development {q['v'] - dv:+.6f}, z {z:+.2f}")
for key in ("sham_cue", "sham_none"):
    q, (dv, dsd) = Q[key], DEV[key]
    say(f"  {key}: SD {q['sd']:.6f} against the development's {dsd:.6f}; difference from the development {q['v'] - dv:+.6f}")
for a in ("vote", "vms"):
    say(f"  U({a}): " + "; ".join(f"U_{L} {U(a, L).mean():.4f}" for L in (2, 4, 8)) + f"; U_mix {pool(Umix_lc(a)).mean():.4f}")
say(f"  U(det): U_8 {U('det', 8).mean():.4f} (det runs at 8 x 8 and in none and cue only)")
for L in (2, 4, 8):
    say(f"  U_{L}(vms) - U_{L}(vote) {ci(est(U('vms', L) - U('vote', L)))}")
d4 = lambda s: pool(u_lc("vms", s, 4) - u_lc("vote", s, 4))
pair = pool(lc("change@0", "vms", "r_in") + lc("change@0", "vms", "r_in_old")
            - lc("change@0", "vote", "r_in") - lc("change@0", "vote", "r_in_old"))
say(f"  U_4(vms) - U_4(vote) in its terms (each / 8): the hits (memory, correlated) "
    f"{ci(est(sum(d4(s) for s in ('memory', 'correlated')) / 8))}; the four (none, body, shared, cue) "
    f"{ci(est(sum(d4(s) for s in ('none', 'body', 'shared', 'cue')) / 8))}; the pair {ci(est(pair / 8))}")
for key, name in (("c1", "C1"), ("c2", "C2"), ("sham_cue", "the cue@0 cost"), ("sham_none", "the none@0 cost")):
    b = np.array(Q[key]["blocks"])
    say(f"  {name} by block: {(b > 0).sum()} of {NB} positive, from {b.min():+.6f} to {b.max():+.6f}"
        + (f"; above 0.01 in {(b > 0.01).sum()}" if key == "sham_cue" else f"; above 0.002 in {(b > 0.002).sum()}" if key == "sham_none" else ""))
say("  u by scoring and size (pooled): arm: none body memory correlated shared cue")
for L in (2, 4, 8):
    for a in ("vote", "det", "vms"):
        vals = []
        for s in SC:
            try:
                vals.append(f"{pool(u_lc(a, s, L)).mean():.4f}")
            except ValueError:
                vals.append("  -   ")
        say(f"    L {L} {a:5s} " + " ".join(vals))
say("  per unit-body pair: C1, C2, the cue@0 sheet cost (each the mean over blocks and cases)")
c1p, c2p, ccp = C1_lc(), C2_lc(), cost_lc("cue@0")
for p, (b, u) in enumerate(PAIRS):
    say(f"    {b:3s} {u}: C1 {c1p[:, p].mean():+.6f}  C2 {c2p[:, p].mean():+.6f}  sheet cost {ccp[:, p].mean():+.6f}")
say("  rates by run: fired at all / on the patch; median onset where fired; mean footprint cells")
for run, arms in RUNS.items():
    for a in [x for x in arms if x in ("det", "vms")]:
        f, o = fire(a, run), onpatch(a, run)
        on = lc(run, a, "det_on", None)[f]
        fp = lc(run, a, "det_fp", None)[f]
        say(f"    {run:16s} {a:4s} {pool(f.astype(float)).mean():.4f} / {pool(o.astype(float)).mean():.4f}  onset "
            f"{np.median(on) if on.size else float('nan'):.0f}  footprint {fp.mean() if fp.size else float('nan'):.1f}")

# ---------- 4. against the frozen reader ----------
if len(sys.argv) > 2:
    rd = json.load(open(sys.argv[2]))
    assert rd["design_digest"] == M["design_digest"] and rd["blocks"] == BLOCKS and rd["purpose"] == PURPOSE
    worst = 0.0
    for key, q in Q.items():
        r_ = rd["intervals"][key]
        for a, b_ in (("mean", "v"), ("lo", "lo"), ("hi", "hi"), ("sd", "sd"), ("sd_block", "sdb"), ("sd_case8", "sdc")):
            worst = max(worst, abs(r_[a] - q[b_]))
        worst = max(worst, max(abs(x - y) for x, y in zip(r_["blocks"], q["blocks"])))
    same = rd["verdict"] == VERDICT and {k: v["pass"] for k, v in rd["criteria"].items()} == ok
    say(f"\nAGAINST THE FROZEN READER ({sys.argv[2]}): largest difference in the means, bounds, SDs and block values "
        f"{worst:.2e}; verdict and criteria {'the same' if same else 'DIFFERENT'} ({rd['verdict']})")
    assert worst <= 1e-12 and same

# ---------- 5. the bridge (the debug stage) ----------
if STAGE == "debug":
    F = ROOT.parent / "reference"
    MF = json.load(open(F / "manifest.json"))
    badf = [f["path"] for t in MF["tasks"].values() for f in t["files"].values()
            if hashlib.sha256((F / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
    assert MF["stage"] == "reference" and MF["blocks"] == [900162] and not badf and len(MF["tasks"]) == 8
    PART_ARMS = {"zone": lambda p: p[1] + p[2], "fp": lambda p: p[1] + p[2],   # ar002.sim.run_det, ar003.sim.run_vd
                 "rB": lambda p: [x for x in p[0] if x == "vote"] + p[2]}       # ar001.sim.run's vote, ar003.sim.run_vd
    PART_ARMS["HB"] = PART_ARMS["WB"] = PART_ARMS["rB"]
    n_arr = n_whole = n_sl = 0
    diffs, ref_only = [], set()
    for b, u in PAIRS:
        for kind in ("shards", "raw"):
            zc, zf = np.load(ROOT / kind / b / u / "900162.npz"), np.load(F / kind / b / u / "900162.npz")
            mc, mf = json.loads(str(zc["__meta__"])), json.loads(str(zf["__meta__"]))
            assert mf["design_digest"] == AR003 and mc["cases"] == mf["cases"] and mf["tag"] == "mse-ar003"
            assert sum(len(a) for _, a in mf["runs"]) == 63 and len(mf["runs"]) == 17, "the reference is AR003's full task"
            rc, rf = dict((r, a) for r, a in mc["runs"]), dict((r, a) for r, a in mf["runs"])
            assert all(r in rf and set(rc[r]) <= set(rf[r]) and mc["sizes"][r] == mf["sizes"][r] for r in rc)
            ref_only |= set(rf) - set(rc)
            for k in zc.files:
                if k == "__meta__":
                    continue
                a, f = zc[k], zf[k]                              # a KeyError here: an array absent from the reference
                n_arr += 1
                run, nm = k.split("/", 1) if "/" in k else (None, k)
                sel = PART_ARMS.get(nm, lambda p: p[0] + p[1] + p[2])
                ac, af = (sel(mc["parts"][run]), sel(mf["parts"][run])) if run else ([], [])
                if a.dtype != f.dtype:
                    diffs.append((b, u, kind, k, "dtype"))
                elif ac == af or a.shape == f.shape:             # no arm axis, or the same arms in the same order
                    assert ac == af or len(ac) != len(af), (k, ac, af)
                    n_whole += 1
                    if a.shape != f.shape or a.tobytes() != f.tobytes():
                        diffs.append((b, u, kind, k, "whole array"))
                else:
                    axes = [x for x in range(a.ndim) if a.shape[x] == len(ac) and f.shape[x] == len(af)
                            and a.shape[:x] + a.shape[x + 1:] == f.shape[:x] + f.shape[x + 1:]]
                    assert len(axes) == 1, (k, a.shape, f.shape, ac, af)
                    for i, arm in enumerate(ac):
                        n_sl += 1
                        if np.take(a, i, axis=axes[0]).tobytes() != np.take(f, af.index(arm), axis=axes[0]).tobytes():
                            diffs.append((b, u, kind, k, arm))
    say(f"\nTHE BRIDGE (the lead's, not ar003c.checks' Q3): the 8 debug tasks on 900162 against the reference's AR003 full "
        f"task there, shards and raw states: {n_arr} arrays ({n_whole} whole, the rest by {n_sl} arm slices), every "
        f"sha256 equal to the reference's manifest; the reference's runs not in AR003C: {', '.join(sorted(ref_only))}; "
        f"differences: {len(diffs)}" + "".join(f"\n  DIFF {d}" for d in diffs[:20]))
    assert not diffs

name = f"p47d_ar003c_lead_check{'_' + STAGE if STAGE != 'confirmation' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
