"""P57d (python probes/p57d_ar006c_lead_check.py ROOT [READER]): the lead's check of AR006C, AR006's confirmation on
fresh blocks. LEAD_CHECK_NOT_REGISTERED; a read of the shards and of the raw final states, written by the lead in
reviewing AR006C's phase A and committed before the freeze and before any confirmation block is drawn; self-tested
first on AR006's development root (its 16 blocks, where the criteria must equal P57c's values) and dry-run on AR006C's
debug run (engineering blocks, tag mse-ar006); 4 November 2026; no simulation. Adapted from P47d (AR003C) and P57c
(AR006).

It checks the sha256 of every shard and raw file against the run's manifest, the blocks, tag and purpose of every shard,
the detectors in every shard's meta against AR006's frozen ones, and AR006's, AR005's and AR003's frozen sources against
the files now; at the confirmation stage, the run's digest and sources against ar006c/frozen/design.json and the frozen
qualification receipt's PASS; then:
1. recomputes the registered criteria from REGISTRATION_AR006C.md's words, not from ar006c.analyze, ar006c.predict,
   ar006.analyze or ar003.analyze, unrounded:
   - u(arm, run): r_in, the record's agreement with the correct target inside the run's patch at t = 8,000; the sheet
     cost r_all(vote) - r_all(arm) at t = 8,000; per case the mean over the eight unit-body pairs;
   - K1 (the harm bound): vtol's sheet cost, 95% upper bounds at most 0.01 in cue@0 and at most 0.002 in none@0;
   - K3 (a): R1, the mean over 4 x 4 and 8 x 8 of u(vtol) - u(vms) in memory@1, 95% lower bound at least 0.04;
   - K5 (a): u(vtol) - u(vms) in correlated@0 (4 x 4), 95% lower bound at least -0.005;
   - a block's value the mean over its 8 cases; SD the larger of the SD over the n block values and the SD over the
     n x 8 case values / sqrt 8; the 95% interval mean +- t(0.975, n - 1) SD / sqrt n; CONFIRMED only if all hold;
2. from the raw final states, with the lead's own scoring (the patch from LR005's frozen draw, be001.sim.patch):
   - every run's r_in and r_all recomputed from the final records;
   - a vote-default arm that never fired equals the vote bit for bit (both records), where the vote ran beside it;
   - vtol's onset is never later than vms's (vtol's windows contain DET_STAR's); where the two fire at the same update
     with the same zone, vtol equals vms bit for bit (both records); the cases where vtol fires first (a guarded pooled
     window) or at once with a larger zone (a union) are counted;
3. reported: the SDs against the development's, each criterion's difference from the development with a z, vms's
   costs beside K1, vtol's cost less vms's in cue@0, R1 at each size, the halves, the criteria by block and by
   unit-body pair, and the rates by run;
4. with READER (the frozen reader's output): its values, bounds and verdict against this check's;
5. at the debug stage, the bridge, independently of ar006c.checks' Q3: every array of every debug task on 900948 and
   900929 against AR006's own full task there (its debug root on 900948 and its preflight root on 900929, both under
   AR006's frozen digest, 9 runs and 32 arm-runs a task), byte for byte; an array of the same arms compared whole, one
   with an arm axis arm slice by arm slice, the arms matched by name from each shard's meta; every compared file's
   sha256 against its own manifest.
Blocks are read in sorted order, which is the halves' order (the first and the last twelve).
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
DEV_BLOCKS = [925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621, 925622, 925624, 925626, 925627, 925628,
              925630, 925633, 925634]                            # AR006's development (the self-test)
DEBUG_BLOCKS = [900929, 900948]                                  # REGISTRATION_AR006C.md: the debug run (the bridge)
CONF_BLOCKS = list(range(920387, 920411))                        # REGISTRATION_AR006C.md: 24 blocks; reserve 920411-6
RUNROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
REFS = {900948: RUNROOT / "ar006" / "debug", 900929: RUNROOT / "ar006" / "preflight"}   # AR006's full task there
STAGE = M["stage"]
SELF = STAGE == "development"                                    # AR006's own development root: the self-test
WANT = {"development": (DEV_BLOCKS, None), "debug": (DEBUG_BLOCKS, "engineering"),
        "confirmation": (CONF_BLOCKS, "confirmation")}
assert STAGE in WANT and M["tag"] == "mse-ar006" and not bad, (STAGE, M["tag"], bad[:5])
BLOCKS, PURPOSE = sorted(M["blocks"]), WANT[STAGE][1]
assert len(set(M["blocks"])) == len(M["blocks"]) and BLOCKS == WANT[STAGE][0], M["blocks"]
NB = len(BLOCKS)
DIG = {"ar006": "963f47e2cf71", "ar005": "0176779a89e36a7e664b9b1cecbfe3c2abfa213a7422d6341243b170b8ae9b02",
       "ar003": "d392002671e648280d9746a336276d9fbf03e17d44c7d144802d9b7f9e84a47e"}
nsrc = {}
for frz, dg in DIG.items():
    FZ_ = json.load(open(LANE / frz / "frozen" / "design.json"))
    assert FZ_["digest"].startswith(dg), (frz, FZ_["digest"][:12])
    changed = [p for p, h in FZ_["sources"].items() if hashlib.sha256((LANE / p).read_bytes()).hexdigest() != h]
    assert not changed, (frz, changed)
    nsrc[frz] = len(FZ_["sources"])
AR006 = json.load(open(LANE / "ar006" / "frozen" / "design.json"))["digest"]
if SELF:
    assert M["design_digest"] == AR006
else:
    assert M.get("ar006_digest") == AR006 and M.get("purpose") == PURPOSE, "the run does not carry AR006's frozen digest"
if STAGE == "confirmation":
    FZ = json.load(open(LANE / "ar006c" / "frozen" / "design.json"))
    RC = json.load(open(LANE / "ar006c" / "frozen" / "qualification_receipt.json"))
    assert FZ["digest"] == M["design_digest"] == RC["design_digest"] and RC["status"] == "PASS", "not under the frozen design"
    assert M["sources"] == FZ["sources"], "the run's sources are not the frozen ones"
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
say(f"P57d on {ROOT} ({STAGE}{': the SELF-TEST on AR006s development' if SELF else ''}"
    f"{', DRY RUN on engineering blocks' if STAGE == 'debug' else ''}): {len(M['tasks'])} tasks, "
    f"{sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the manifest's; digest "
    f"{M['design_digest'][:12]}; AR006's {AR006[:12]} ({nsrc['ar006']} sources), AR005's and AR003's frozen sources "
    f"unchanged; {M['started_utc']} - {M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h, {M['workers']} workers")
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
assert len(M["tasks"]) == len(PAIRS) * NB
Z = {(b, u, k): dict(np.load(ROOT / "shards" / b / u / f"{k}.npz")) for b, u in PAIRS for k in BLOCKS}
META = {key: json.loads(str(z["__meta__"])) for key, z in Z.items()}
M0 = META[(*PAIRS[0], BLOCKS[0])]
RUNS = {rn: arms for rn, arms in M0["runs"]}
SIZES = M0["sizes"]
STAR = {"boxes": list(range(2, 13)), "n": 3, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}
POOL = dict(STAR, ring_max=1)
SPLIT = {"kind": "split", "f": 0.5, "free_ring_max": 0}
NEED = {"cue@0": ["vote", "vms", "vtol"], "none@0": ["vote", "vms", "vtol"], "memory@1": ["vms", "vtol"],
        "memory@1-L8": ["vms", "vtol"], "correlated@0": ["vms", "vtol"]}
if SELF:
    assert all(set(a) <= set(RUNS[r]) for r, a in NEED.items()), RUNS
else:
    assert {k: sorted(v) for k, v in RUNS.items()} == {k: sorted(v) for k, v in NEED.items()}, RUNS
assert SIZES["memory@1"] == 4 and SIZES["memory@1-L8"] == 8 and all(SIZES[r] == 4 for r in ("cue@0", "none@0", "correlated@0"))
for (b, u, k), m in META.items():
    assert {rn: a for rn, a in m["runs"]} == RUNS and m["sizes"] == SIZES and (m["body"], m["unit"], int(m["block"])) == (b, u, k)
    assert m["tag"] == M["tag"] and m["design_digest"] == M["design_digest"]
    if not SELF:
        assert m["ar006_digest"] == AR006 and m["ar005_digest"] == DIG["ar005"] and m["ar003_digest"] == DIG["ar003"]
    assert m["study"] == ("AR006" if SELF else "AR006C"), m["study"]
    if not SELF:
        assert m["purpose"] == PURPOSE, m.get("purpose")
    det = m["vd_detectors"]
    assert det["vms"] == {"cue": STAR, "body": None} and det["vtol"] == {"cue": POOL, "body": None, "guard": SPLIT}, det
    assert len(m["cases"]) == 8 and all(int(c[0]) == k for c in m["cases"])
RI = M0["reads"].index(8000)
say("runs: " + ", ".join(f"{r} (L {SIZES[r]}; {', '.join(a)})" for r, a in RUNS.items() if r in NEED)
    + ("  [the self-test reads only these of AR006's runs]" if SELF else ""))
say("detectors in every shard: vms DET_STAR; vtol DET_POOL with the split guard (the clean surround free, the tolerated "
    "window body-checked at f 0.5), AR006's frozen ones")


def lc(run, arm, e, ri=RI):
    """(blocks, pairs, cases): one endpoint per lineage-case; ri None for a scalar."""
    i = RUNS[run].index(arm)
    return np.array([[(Z[(b, u, k)][f"{run}/{e}"][ri, i] if ri is not None else Z[(b, u, k)][f"{run}/{e}"][i])
                      for b, u in PAIRS] for k in BLOCKS], float)


pool = lambda x: x.mean(1)
cost_lc = lambda run, arm: lc(run, "vote", "r_all") - lc(run, arm, "r_all")
R1_lc = lambda: ((lc("memory@1", "vtol", "r_in") - lc("memory@1", "vms", "r_in"))
                 + (lc("memory@1-L8", "vtol", "r_in") - lc("memory@1-L8", "vms", "r_in"))) / 2
K5_lc = lambda: lc("correlated@0", "vtol", "r_in") - lc("correlated@0", "vms", "r_in")
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
    return {"v": v, "lo": v - h, "hi": v + h, "h": h, "sd": sd, "sdb": sdb, "sdc": sdc,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean())), "blocks": [float(y) for y in blk]}


ci = lambda q: (f"{q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, case/sqrt8 "
                f"{q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
# AR006's development, 16 blocks (P57c, probes/results/p57c_ar006_lead_check.txt): value and the max-rule SD
DEV = {"k1_cue": (0.007730, 0.002883), "k1_none": (-0.000026, 0.000066), "k3a": (0.092422, 0.040717),
       "k5a": (0.000366, 0.001465)}
CRIT = {"k1_cue": ("K1, vtol's sheet cost, cue@0", "le", 0.01), "k1_none": ("K1, vtol's sheet cost, none@0", "le", 0.002),
        "k3a": ("K3 (a), R1 = mean over 4, 8 of u(vtol) - u(vms), memory@1", "ge", 0.04),
        "k5a": ("K5 (a), u(vtol) - u(vms), correlated@0", "ge", -0.005)}
say(f"\nREGISTERED CRITERIA ({NB} blocks; pooled over the eight unit-body pairs; 95% t interval, t(0.975, {NB - 1}) = "
    f"{T975:.4f}; SD the larger of the block SD and the case SD / sqrt 8)")
Q = {"k1_cue": est(pool(cost_lc("cue@0", "vtol"))), "k1_none": est(pool(cost_lc("none@0", "vtol"))),
     "k3a": est(pool(R1_lc())), "k5a": est(pool(K5_lc()))}
ok = {}
for key, (words, sense, th) in CRIT.items():
    q = Q[key]
    ok[key] = q["hi"] <= th if sense == "le" else q["lo"] >= th
    say(f"  {words}: {ci(q)}; {'upper' if sense == 'le' else 'lower'} bound {'<=' if sense == 'le' else '>='} {th:+}: "
        f"{'holds' if ok[key] else 'FAILS'}")
OKC = {"K1": ok["k1_cue"] and ok["k1_none"], "K3a": ok["k3a"], "K5a": ok["k5a"]}
VERDICT = "CONFIRMED" if all(OKC.values()) else "NOT CONFIRMED"
say(f"  VERDICT: {VERDICT}" + (f" (failed: {', '.join(k for k, v in OKC.items() if not v)})" if not all(OKC.values()) else "")
    + ("  [a dry run on engineering blocks: not a confirmation result]" if STAGE == "debug" else "")
    + ("  [the self-test on AR006's development: not a confirmation result]" if SELF else ""))
if SELF:                                                         # the criteria's arithmetic against P57c's printed values
    for key, (dv, dsd) in DEV.items():
        assert abs(Q[key]["v"] - dv) < 5e-7 and abs(Q[key]["sd"] - dsd) < 5e-7, (key, Q[key]["v"], Q[key]["sd"])
    say("  SELF-TEST: the four values and SDs equal P57c's on AR006's development (to its printed 6 decimals)")

# ---------- 2. the raw final states ----------
say("\nFROM THE RAW FINAL STATES (the lead's own scoring; the patch from be001.sim.patch)")
rin_max = rall_max = 0.0
n_checked = same_n = same_bad = 0
br = {"not_after_vms": [0, 0], "same_onset_same_zone_equal": [0, 0], "vtol_first": 0, "same_onset_union": 0,
      "neither": 0, "vms_only": 0}
for b, u in PAIRS:
    for k in BLOCKS:
        raw = np.load(ROOT / "raw" / b / u / f"{k}.npz")
        m = META[(b, u, k)]
        cases = [Case(*c) for c in m["cases"]]
        T = raw["T"]
        pt = {L: B1S.patch(cases, L, m["tag"]) for L in sorted({SIZES[r] for r in NEED})}
        ins = lambda x, mm: (((x > 0) == (T > 0)) & mm).sum((-2, -1)) / mm.sum((-2, -1))
        for run in NEED:
            arms = RUNS[run]
            r, rB = raw[f"{run}/r"], raw[f"{run}/rB"]
            L = SIZES[run]
            for i, a in enumerate(arms):
                rin_max = max(rin_max, float(np.abs(ins(r[i], pt[L]) - Z[(b, u, k)][f"{run}/r_in"][RI, i]).max()))
                rall_max = max(rall_max, float(np.abs(((r[i] > 0) == (T > 0)).mean((-2, -1))
                                                      - Z[(b, u, k)][f"{run}/r_all"][RI, i]).max()))
                n_checked += 1
            rb_arms = [x for x in m["parts"][run][0] if x == "vote"] + m["parts"][run][2]
            vd = m["parts"][run][2]
            on = {a: Z[(b, u, k)][f"{run}/det_on"][arms.index(a)] for a in arms if a != "vote"}
            if "vote" in arms:                                   # the vote-default identity
                iv = arms.index("vote")
                for a in [x for x in arms if x != "vote"]:
                    ia = arms.index(a)
                    for j in np.flatnonzero(on[a] < 0):
                        same_n += 1
                        same_bad += int(not (np.array_equal(r[ia, j], r[iv, j])
                                             and np.array_equal(rB[rb_arms.index(a), j], rB[rb_arms.index("vote"), j])))
            zone = raw[f"{run}/zone"]
            inf = lambda x: np.where(x < 0, np.inf, x)
            it, im = arms.index("vtol"), arms.index("vms")
            for j in range(len(cases)):
                ot, om = inf(on["vtol"])[j], inf(on["vms"])[j]
                br["not_after_vms"][0] += 1
                br["not_after_vms"][1] += int(ot > om)
                if np.isinf(ot) and np.isinf(om):
                    br["neither"] += 1
                elif ot < om:
                    br["vtol_first"] += 1
                elif ot == om:
                    zt, zm = zone[vd.index("vtol"), j], zone[vd.index("vms"), j]
                    if np.array_equal(zt, zm):
                        br["same_onset_same_zone_equal"][0] += 1
                        br["same_onset_same_zone_equal"][1] += int(not (
                            np.array_equal(r[it, j], r[im, j]) and np.array_equal(rB[rb_arms.index("vtol"), j], rB[rb_arms.index("vms"), j])))
                    else:
                        assert not (zm & ~zt).any(), "vms's zone outside vtol's at the same onset"
                        br["same_onset_union"] += 1
                else:
                    br["vms_only"] += 1
say(f"  r_in and r_all recomputed from the final records, {n_checked} arm-runs x 8 cases: largest difference "
    f"{rin_max:.2e} and {rall_max:.2e}")
say(f"  a vote-default arm where it never fired against the vote, both records, bit for bit: {same_n - same_bad} of "
    f"{same_n} lineage-cases equal (cue@0 and none@0)")
n_all = br["not_after_vms"][0]
say(f"  vtol against vms, {n_all} lineage-cases in the five runs: vtol's onset later than vms's in {br['not_after_vms'][1]}; "
    f"neither fired {br['neither']}; the same onset and zone {br['same_onset_same_zone_equal'][0]} (vtol equals vms, both "
    f"records, in {br['same_onset_same_zone_equal'][0] - br['same_onset_same_zone_equal'][1]}); the same onset, vtol's "
    f"zone the larger (a union) {br['same_onset_union']}; vtol first (a guarded pooled window) {br['vtol_first']}")
assert rin_max <= 1e-12 and rall_max <= 1e-12 and same_bad == 0
assert br["not_after_vms"][1] == 0 and br["same_onset_same_zone_equal"][1] == 0 and br["vms_only"] == 0

# ---------- 3. reported ----------
say("\nREPORTED (not registered)")
for key in CRIT:
    q, (dv, dsd) = Q[key], DEV[key]
    z = (q["v"] - dv) / math.sqrt(q["sd"] ** 2 / NB + dsd ** 2 / 16) if q["sd"] + dsd > 0 else float("nan")
    b_ = np.array(q["blocks"])
    say(f"  {CRIT[key][0]}: SD {q['sd']:.6f} against the development's {dsd:.6f} (ratio {q['sd'] / dsd:.3f}); difference "
        f"from the development {q['v'] - dv:+.6f}, z {z:+.2f}; by block from {b_.min():+.6f} to {b_.max():+.6f}")
for run in ("cue@0", "none@0"):
    say(f"  vms's sheet cost, {run}: {ci(est(pool(cost_lc(run, 'vms'))))}")
    say(f"  vtol's cost less vms's, {run}: {ci(est(pool(lc(run, 'vms', 'r_all') - lc(run, 'vtol', 'r_all'))))}")
for run, L in (("memory@1", 4), ("memory@1-L8", 8)):
    say(f"  R1 at {L} x {L}: {ci(est(pool(lc(run, 'vtol', 'r_in') - lc(run, 'vms', 'r_in'))))}")
say(f"  u(vtol) - u(vote) inside the patch, cue@0: {ci(est(pool(lc('cue@0', 'vtol', 'r_in') - lc('cue@0', 'vote', 'r_in'))))}")
say("  per unit-body pair: K1 cue@0, K3 (a), K5 (a) (each the mean over blocks and cases)")
kc, k3, k5 = cost_lc("cue@0", "vtol"), R1_lc(), K5_lc()
for p, (b, u) in enumerate(PAIRS):
    say(f"    {b:3s} {u}: K1 cue@0 {kc[:, p].mean():+.6f}  K3 (a) {k3[:, p].mean():+.6f}  K5 (a) {k5[:, p].mean():+.6f}")
# the lead's extension after the confirmation's results (4 November 2026, about 12:20Z; reported only, no criterion or
# check changed; git shows the diff): each criterion part's halves with their own 95% intervals (t(0.975, 11) over 12
# blocks, the same SD rule), and every lineage-case of correlated@0 where vtol's patch differs from vms's
if STAGE == "confirmation":
    say("  the halves, each with its own 95% interval (12 blocks, t(0.975, 11), the max-rule SD):")
    xs = {"k1_cue": pool(cost_lc("cue@0", "vtol")), "k1_none": pool(cost_lc("none@0", "vtol")), "k3a": pool(R1_lc()),
          "k5a": pool(K5_lc())}
    t11 = stats.t.ppf(0.975, NB // 2 - 1)
    for key, x in xs.items():
        cells = []
        for h, sl in (("920387-920398", slice(0, NB // 2)), ("920399-920410", slice(NB // 2, NB))):
            xh = x[sl]
            bh = xh.mean(1)
            sdh = max(float(bh.std(ddof=1)), float(xh.ravel().std(ddof=1)) / math.sqrt(xh.shape[1]))
            hw = t11 * sdh / math.sqrt(len(bh))
            cells.append(f"{h} {bh.mean():+.6f} [{bh.mean() - hw:+.6f}, {bh.mean() + hw:+.6f}]")
        say(f"    {CRIT[key][0]}: " + "; ".join(cells))
    d5 = K5_lc()                                                 # (blocks, pairs, cases)
    on_t, on_m = lc("correlated@0", "vtol", "det_on", None), lc("correlated@0", "vms", "det_on", None)
    nz = np.argwhere(d5 != 0)
    say(f"  correlated@0, the lineage-cases where u(vtol) differs from u(vms): {len(nz)} of {d5.size}")
    for bi_, pi_, ci_ in nz:
        b_, u_ = PAIRS[pi_]
        say(f"    {BLOCKS[bi_]} {b_} {u_} case {ci_}: u(vtol) - u(vms) {d5[bi_, pi_, ci_]:+.4f}; onset vtol "
            f"{on_t[bi_, pi_, ci_]:.0f}, vms {on_m[bi_, pi_, ci_]:.0f} (-1 never)")
say("  rates by run: fired at all / on the patch; median onset where fired; mean footprint cells")
for run in NEED:
    for a in [x for x in RUNS[run] if x in ("vms", "vtol")]:
        f, o = fire(a, run), onpatch(a, run)
        on = lc(run, a, "det_on", None)[f]
        fp = lc(run, a, "det_fp", None)[f]
        say(f"    {run:13s} {a:4s} {pool(f.astype(float)).mean():.4f} / {pool(o.astype(float)).mean():.4f}  onset "
            f"{np.median(on) if on.size else float('nan'):.0f}  footprint {fp.mean() if fp.size else float('nan'):.1f}")

# ---------- 4. against the frozen reader ----------
if len(sys.argv) > 2:
    rd = json.load(open(sys.argv[2]))
    assert rd["design_digest"] == M["design_digest"] and rd["blocks"] == BLOCKS and rd.get("purpose") == PURPOSE
    assert rd["study"] == "AR006C" and rd["tag"] == "mse-ar006"
    assert {k: (v[0], float(v[1])) for k, v in rd["thresholds"].items()} == {k: (c[1], c[2]) for k, c in CRIT.items()}
    worst = 0.0
    for key, q in Q.items():
        r_ = rd["intervals"][key]
        assert r_["n_blocks"] == NB and len(r_["blocks"]) == NB
        for a, b_ in (("mean", "v"), ("lo", "lo"), ("hi", "hi"), ("sd", "sd"), ("sd_block", "sdb"), ("sd_case8", "sdc"),
                      ("half_width", "h")):
            worst = max(worst, abs(r_[a] - q[b_]))
        worst = max(worst, max(abs(x - y) for x, y in zip(r_["blocks"], q["blocks"])))
    bounds = {"K1": (rd["criteria"]["K1"]["upper_bound_cue"] - Q["k1_cue"]["hi"],
                     rd["criteria"]["K1"]["upper_bound_none"] - Q["k1_none"]["hi"]),
              "K3a": (rd["criteria"]["K3a"]["lower_bound"] - Q["k3a"]["lo"],),
              "K5a": (rd["criteria"]["K5a"]["lower_bound"] - Q["k5a"]["lo"],)}
    worst = max(worst, max(abs(x) for v in bounds.values() for x in v))
    failed = sorted(k for k, v in OKC.items() if not v)
    same = (rd["verdict"] == VERDICT and {k: v["pass"] for k, v in rd["criteria"].items()} == OKC
            and sorted(rd.get("failed", [])) == failed)
    say(f"\nAGAINST THE FROZEN READER ({sys.argv[2]}): largest difference in the means, bounds, SDs and block values "
        f"{worst:.2e}; verdict and criteria {'the same' if same else 'DIFFERENT'} ({rd['verdict']})")
    assert worst <= 1e-12 and same

# ---------- 5. the bridge (the debug stage) ----------
if STAGE == "debug":
    PART_ARMS = {"zone": lambda p: p[1] + p[2], "fp": lambda p: p[1] + p[2],
                 "rB": lambda p: [x for x in p[0] if x == "vote"] + p[2]}
    PART_ARMS["HB"] = PART_ARMS["WB"] = PART_ARMS["rB"]
    n_arr = n_whole = n_sl = n_files = 0
    diffs, ref_only = [], set()
    for blk, F in REFS.items():
        MF = json.load(open(F / "manifest.json"))
        assert MF["stage"] in ("debug", "preflight") and blk in MF["blocks"] and MF["tag"] == "mse-ar006"
        assert MF["design_digest"] == AR006, "the reference is not under AR006's frozen digest"
        shaf = {f["path"]: f["sha256"] for t in MF["tasks"].values() for f in t["files"].values()}
        for b, u in PAIRS:
            for kind in ("shards", "raw"):
                rel = f"{kind}/{b}/{u}/{blk}.npz"
                assert hashlib.sha256((F / rel).read_bytes()).hexdigest() == shaf[rel], (F, rel)
                n_files += 1
                zc, zf = np.load(ROOT / rel), np.load(F / rel)
                mc, mf = json.loads(str(zc["__meta__"])), json.loads(str(zf["__meta__"]))
                assert mf["design_digest"] == AR006 and mf["study"] == "AR006" and mf["tag"] == "mse-ar006"
                assert mc["cases"] == mf["cases"] and int(mf["block"]) == blk
                assert sum(len(a) for _, a in mf["runs"]) == 32 and len(mf["runs"]) == 9, "the reference is AR006's full task"
                rc, rf = dict((r, a) for r, a in mc["runs"]), dict((r, a) for r, a in mf["runs"])
                assert all(r in rf and set(rc[r]) <= set(rf[r]) and mc["sizes"][r] == mf["sizes"][r] for r in rc)
                ref_only |= set(rf) - set(rc)
                for k in zc.files:
                    if k == "__meta__":
                        continue
                    a, f = zc[k], zf[k]                          # a KeyError here: an array absent from the reference
                    n_arr += 1
                    run, nm = k.split("/", 1) if "/" in k else (None, k)
                    sel = PART_ARMS.get(nm, lambda p: p[0] + p[1] + p[2])
                    ac, af = (sel(mc["parts"][run]), sel(mf["parts"][run])) if run else ([], [])
                    if a.dtype != f.dtype:
                        diffs.append((blk, b, u, kind, k, "dtype"))
                    elif ac == af or a.shape == f.shape:
                        assert ac == af or len(ac) != len(af), (k, ac, af)
                        n_whole += 1
                        if a.shape != f.shape or a.tobytes() != f.tobytes():
                            diffs.append((blk, b, u, kind, k, "whole array"))
                    else:
                        axes = [x for x in range(a.ndim) if a.shape[x] == len(ac) and f.shape[x] == len(af)
                                and a.shape[:x] + a.shape[x + 1:] == f.shape[:x] + f.shape[x + 1:]]
                        assert len(axes) == 1, (k, a.shape, f.shape, ac, af)
                        for i, arm in enumerate(ac):
                            n_sl += 1
                            if np.take(a, i, axis=axes[0]).tobytes() != np.take(f, af.index(arm), axis=axes[0]).tobytes():
                                diffs.append((blk, b, u, kind, k, arm))
    say(f"\nTHE BRIDGE (the lead's, not ar006c.checks' Q3): the 16 debug tasks on 900948 and 900929 against AR006's own "
        f"full task there (its debug and preflight roots, digest {AR006[:12]}), shards and raw states: {n_files} file pairs, "
        f"{n_arr} arrays ({n_whole} whole, the rest by {n_sl} arm slices), every reference file's sha256 equal to its "
        f"manifest's; AR006's runs not in AR006C: {', '.join(sorted(ref_only))}; differences: {len(diffs)}"
        + "".join(f"\n  DIFF {d}" for d in diffs[:20]))
    assert not diffs

name = f"p57d_ar006c_lead_check{'_' + STAGE if STAGE != 'confirmation' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
