"""P57c (python probes/p57c_ar006_lead_check.py ROOT): the lead's check of AR006, guard only the tolerance.
LEAD_CHECK_NOT_REGISTERED; a read of the shards and of the raw final states, written by the lead in reviewing AR006's
phase A and committed before the freeze, dry-run first on P57 (engineering blocks 900917, 900918 | 900919, 900928; tag
mse-p57); 3 November 2026; no simulation. Adapted from P53c (AR005).

It checks, from PLAN_AR006.md's words and not from ar006.analyze, ar006.predict or ar003.analyze:
0. the split guard's arithmetic, independently of the integral images: on synthetic states the lead's own loop over every
   periodic window gives W0 (DET_STAR's windows: the surround clean), W1 (DET_POOL's: one disagreeing anchor tolerated)
   and B (the confident body disagrees with the record at half or more of the window's disagreeing live anchors), and
   vtol's windows W0 | (W1 & B) must equal ar006.sim.windows exactly; also ar006.sim.windows must equal
   ar002.sim.cue_windows_multi (DET_STAR) united with ar005.sim.guarded_windows (DET_POOL, f 0.5), the plan's identity;
1. the sha256 of every shard and raw file; the stage's blocks and tag; every shard's runs, arms and detectors; AR003's
   and AR005's frozen sources unchanged; at the development stage the run's digest and sources against
   ar006/frozen/design.json;
2. the parts K1-K7 by the plan's words (u, sheet costs, the size means over 4 and 8, the max-rule SD, the 95% t
   interval; on P57 the margins, both halves and the strictest round thresholds; the fixed bounds kept only if supported;
   SD 0 the declared allowance -0.005);
3. from the raw final states: every r_in and r_all rescored; every vote-default arm that never fired equals the vote bit
   for bit (both records); and the derivation's branch identities, wherever vms and vguard ran beside vtol: vtol's onset
   is the earlier of theirs; where vms fires first (or vguard never), vtol equals vms bit for bit (both records, the zone);
   where vguard fires first, vtol equals vguard; where both fire at once, vtol's zone is the union of theirs. Wherever
   vpool ran beside vtol, vtol's onset is never earlier than vpool's; wherever vms ran, never later than vms's.
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
from ar002 import sim as A2S                                     # noqa: E402  (frozen: DET_STAR's windows)
from ar005 import sim as A5S                                     # noqa: E402  (frozen: the guarded windows)
from ar006 import sim as A6S                                     # noqa: E402  (under check: the split windows)
from be001 import sim as B1S                                     # noqa: E402  (frozen: LR005's patch draw)
from lr005 import design as L5D                                  # noqa: E402  (frozen: VMIN)
from mse.assay import Case                                       # noqa: E402  (frozen engine: the case keys)

ROOT = Path(sys.argv[1])
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
STAR = {"boxes": list(range(2, 13)), "n": 3, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}
POOL = dict(STAR, ring_max=1)
SPLIT = {"kind": "split", "f": 0.5, "free_ring_max": 0}
F05 = {"kind": "body", "f": 0.5}

# ------------------------------------------------------------------------------------- 0. the split's arithmetic
assert L5D.VMIN == 0.2


def naive(V, r, am, aval, ch, f):
    """The lead's loop: {box: (W0, W1, B)} by top-left corner, periodic."""
    k, n = r.shape[0], r.shape[-1]
    vs = lambda x: np.where(x >= 0.2, 1, np.where(x <= -0.2, -1, 0))
    sr, sv = vs(r), vs(V)
    ca = np.where(am, aval, 0)
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    bod = dis & (sv != 0) & (sv != sr)
    g, res = ch["ring"], {}
    for b in ch["boxes"]:
        W0, W1, B = (np.zeros((k, n, n), bool) for _ in range(3))
        for c in range(k):
            for i in range(n):
                rows = [(i + d) % n for d in range(b)]
                rows_o = [(i - g + d) % n for d in range(b + 2 * g)]
                for j in range(n):
                    cols = [(j + d) % n for d in range(b)]
                    cols_o = [(j - g + d) % n for d in range(b + 2 * g)]
                    nd = int(dis[c][np.ix_(rows, cols)].sum())
                    nl = int(live[c][np.ix_(rows, cols)].sum())
                    ring = int(dis[c][np.ix_(rows_o, cols_o)].sum()) - nd
                    base = nd >= ch["n"] and nd >= ch["q"] * nl
                    W0[c, i, j] = base and ring <= 0
                    W1[c, i, j] = base and ring <= ch["ring_max"]
                    B[c, i, j] = int(bod[c][np.ix_(rows, cols)].sum()) >= f * nd
        res[b] = (W0, W1, B)
    return res


rng = np.random.default_rng(570)
SETUPS = [([(2, 6, 2, 6), (9, 13, 9, 13)], 0.03, 0.25, -0.4), ([(3, 9, 5, 11)], 0.0, 0.4, -0.4),
          ([(2, 10, 2, 10)], 0.25, 0.55, -0.4), ([(1, 5, 10, 14), (8, 12, 2, 6)], 0.02, 0.5, -0.4),
          ([(2, 6, 2, 6), (9, 14, 8, 13)], 0.02, 0.4, 0.05)]
n_win, held = 0, {"W0": 0, "W1": 0, "W1&B": 0, "vtol": 0, "added": 0}
for trial, (patches, pflip, dens, vlo) in enumerate(SETUPS):
    k, n = 3, 16
    T = np.where(rng.random((k, n, n)) < 0.5, 1.0, -1.0)
    T[:, 4:12, 4:12] = 1.0
    r = T * rng.uniform(0.1, 1.2, (k, n, n))
    for a0, a1, b0, b1 in patches:
        r[:, a0:a1, b0:b1] *= -1
    V = T * rng.uniform(vlo, 1.2, (k, n, n))
    am = rng.random((k, n, n)) < dens
    aval = T.copy()
    aval[rng.random((k, n, n)) < pflip] *= -1
    P = {"am": am, "aval": aval}
    got = A6S.windows(V, r, P, POOL, SPLIT)
    lead = naive(V, r, am, aval, POOL, 0.5)
    star = A2S.cue_windows_multi(r, P, STAR)
    guard = A5S.guarded_windows(V, r, P, POOL, F05)
    assert sorted(got) == POOL["boxes"]
    for bx in POOL["boxes"]:
        W0, W1, B = lead[bx]
        want = W0 | (W1 & B)
        assert np.array_equal(got[bx], want), (trial, bx, int((got[bx] != want).sum()))
        assert np.array_equal(got[bx], star[bx] | guard[bx]), (trial, bx)
        assert np.array_equal(star[bx], W0) and np.array_equal(guard[bx], W1 & B), (trial, bx)
        n_win += got[bx].size
        for kk, v in (("W0", W0), ("W1", W1), ("W1&B", W1 & B), ("vtol", want), ("added", want & ~W0)):
            held[kk] += int(v.sum())
assert held["added"] > 0 and held["W0"] > 0 and held["vtol"] < held["W1"], held
say(f"0. the split guard's arithmetic: on {len(SETUPS)} synthetic states (3 cases, 16 x 16, boxes 2-12), the lead's loop's "
    f"W0 | (W1 & B) equals ar006.sim.windows at every box, {n_win} windows, 0 differ; ar006.sim.windows equals "
    f"ar002.sim.cue_windows_multi (DET_STAR) united with ar005.sim.guarded_windows (DET_POOL, f 0.5) exactly; windows held: "
    + ", ".join(f"{kk} {v}" for kk, v in held.items()) + " (added: the guarded pooled-only windows vtol holds beyond DET_STAR)")

# ------------------------------------------------------------------------------------- 1. integrity and the design
M = json.load(open(ROOT / "manifest.json"))
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values()
       if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
DEV = [925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621, 925622, 925624, 925626, 925627, 925628, 925630,
       925633, 925634]
WANT = {"probe": ("mse-p57", [900917, 900918, 900919, 900928]), "debug": ("mse-ar006", [900948]),
        "preflight": ("mse-ar006", [900929, 900947]), "development": ("mse-ar006", DEV)}
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == WANT[STAGE][0] and not bad, (STAGE, M["tag"], bad[:5])
BLOCKS = list(M["blocks"])
assert BLOCKS == WANT[STAGE][1], BLOCKS
NB = len(BLOCKS)
AR005 = "0176779a89e36a7e664b9b1cecbfe3c2abfa213a7422d6341243b170b8ae9b02"
AR003 = "d392002671e648280d9746a336276d9fbf03e17d44c7d144802d9b7f9e84a47e"
assert M["ar005_digest"] == AR005 and M["ar003_digest"] == AR003
for frz, dg in (("ar003", AR003), ("ar005", AR005)):
    FZ_ = json.load(open(LANE / frz / "frozen" / "design.json"))
    assert FZ_["digest"] == dg
    changed = [p for p, h in FZ_["sources"].items() if hashlib.sha256((LANE / p).read_bytes()).hexdigest() != h]
    assert not changed, (frz, changed)
if STAGE == "development":
    FZ = json.load(open(LANE / "ar006" / "frozen" / "design.json"))
    assert FZ["digest"] == M["design_digest"], "the draw is not under the frozen design"
    changed = [p for p, h in FZ["sources"].items() if hashlib.sha256((LANE / p).read_bytes()).hexdigest() != h]
    assert not changed, changed
say(f"\n1. P57c on {ROOT} ({STAGE}{', DRY RUN on engineering blocks' if STAGE != 'development' else ''}): "
    f"{len(M['tasks'])} tasks, {sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the "
    f"manifest's; digest {M['design_digest'][:12]} (AR005's {AR005[:12]} and AR003's {AR003[:12]}, their frozen sources "
    f"unchanged); {M['started_utc']} - {M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h, {M['workers']} workers")
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
assert len(M["tasks"]) == len(PAIRS) * NB
Z = {(b, u, k): dict(np.load(ROOT / "shards" / b / u / f"{k}.npz")) for b, u in PAIRS for k in BLOCKS}
META = {key: json.loads(str(z["__meta__"])) for key, z in Z.items()}
M0 = META[(*PAIRS[0], BLOCKS[0])]
RUNS = {rn: arms for rn, arms in M0["runs"]}
SIZES = M0["sizes"]
ALL4 = ["vms", "vpool", "vguard", "vtol"]
WANT_RUNS = {
    "probe": {"memory@0": ["vote", "vms", "vtol"], "memory@0-L8": ["vote", "vms", "vtol"],
              "memory@1": ["vms", "vpool", "vtol"], "memory@1-L8": ["vms", "vpool", "vtol"], "none@0": ["vote", "vtol"],
              "none@1": ["vtol"], "cue@0": ["vote", "vtol"], "correlated@0": ["vms", "vguard", "vtol"],
              "correlated@1": ["vms", "vguard", "vtol"]},
    "development": {"memory@0": ["vote", "vms", "vtol"], "memory@0-L8": ["vote", "vms", "vtol"], "memory@1": ALL4,
                    "memory@1-L8": ALL4, "none@0": ["vote", "vms", "vtol"], "none@1": ["vms", "vtol"],
                    "cue@0": ["vote", "vms", "vpool", "vtol"], "correlated@0": ["vote"] + ALL4, "correlated@1": ALL4}}
WANT_RUNS["debug"] = WANT_RUNS["preflight"] = WANT_RUNS["development"]
assert {k: sorted(v) for k, v in RUNS.items()} == {k: sorted(v) for k, v in WANT_RUNS[STAGE].items()}, RUNS
for (b, u, k), m in META.items():
    assert {rn: a for rn, a in m["runs"]} == RUNS and m["sizes"] == SIZES and (m["body"], m["unit"], int(m["block"])) == (b, u, k)
    assert m["study"] == "AR006" and m["tag"] == M["tag"] and m["design_digest"] == M["design_digest"]
    det = m["vd_detectors"]
    assert det["vote"] == {"never": True}
    assert det["vms"] == {"cue": STAR, "body": None} and det["vpool"] == {"cue": POOL, "body": None}
    assert det["vguard"] == {"cue": POOL, "body": None, "guard": F05}
    assert det["vtol"] == {"cue": POOL, "body": None, "guard": SPLIT}
    assert len(m["cases"]) == 8 and all(int(c[0]) == k for c in m["cases"])
RI = M0["reads"].index(8000)
say("   runs: " + ", ".join(f"{r} (L {SIZES[r]}; {', '.join(a)})" for r, a in RUNS.items()))
say("   detectors in every shard: vms DET_STAR, vpool pool-n3-q1-r1, vguard DET_POOL + g-body-f05, vtol DET_POOL + the split "
    "(the clean surround free, the tolerated window body-checked at f 0.5)")


def lc(run, arm, e, ri=RI):
    i = RUNS[run].index(arm)
    return np.array([[(Z[(b, u, k)][f"{run}/{e}"][ri, i] if ri is not None else Z[(b, u, k)][f"{run}/{e}"][i])
                      for b, u in PAIRS] for k in BLOCKS], float)


pool = lambda x: x.mean(1)
rname = lambda s, L, sg: f"{s}@{sg}" + ("" if L == 4 else f"-L{L}")


def u(arm, s, L=4, sg=0):
    run = rname(s, L, sg)
    if arm not in RUNS[run]:
        assert arm == "vote" and sg == 1, (arm, run)
        run = rname(s, L, 0)
    return pool(lc(run, arm, "r_in"))


def sham(run, arm):
    ref = run if "vote" in RUNS[run] else run.replace("@1", "@0")
    return pool(lc(ref, "vote", "r_all") - lc(run, arm, "r_all"))


located = lambda arm, run: pool(((lc(run, arm, "det_on", None) > 0) & (lc(run, arm, "det_fp_in", None) > 0)).astype(float))
fired = lambda arm, run: pool((lc(run, arm, "det_on", None) > 0).astype(float))
over = lambda a, b, sa, sb, Ls=(4, 8): sum(u(a, "memory", L, sa) - u(b, "memory", L, sb) for L in Ls) / len(Ls)

# ------------------------------------------------------------------------------------- 2. the parts
K = 3 * math.sqrt(1 / 4 + 1 / 16)
T975 = stats.t.ppf(0.975, NB - 1) if NB > 1 else float("nan")


def est(x):
    blk = x.mean(1)
    v = float(blk.mean())
    sdc = float(x.ravel().std(ddof=1)) / math.sqrt(x.shape[1])
    sdb = float(blk.std(ddof=1)) if NB > 1 else float("nan")
    sd = max(sdb, sdc) if NB > 1 else sdc
    h = T975 * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sdb": sdb, "sdc": sdc,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean())) if NB > 1 else (v, v)}


def strictest(q, sense, kind):
    raw = min(q["v"] - K * q["sd"], *q["halves"]) if sense == "ge" else max(q["v"] + K * q["sd"], *q["halves"])
    step = 0.001 if kind == "cost" else (0.005 if abs(raw) <= 0.01 else 0.01)
    t = (math.floor(round(raw / step, 9)) if sense == "ge" else math.ceil(round(raw / step, 9))) * step
    return raw, step, round(t, 4)


# the registration's thresholds as the lead ruled on phase A (REGISTRATION_AR006.md); K1 dropped by the rule, reported
TH = {"K2a": ("le", 0.002), "K2b": ("le", 0.01), "K3a": ("ge", 0.04), "K3b": ("ge", 0.0), "K4": ("ge", -0.005),
      "K5a": ("ge", -0.005), "K5b": ("ge", 0.25), "K5c": ("ge", -0.03), "K5d": ("ge", 0.0), "K6": ("ge", 0.12),
      "K7a": ("ge", -0.005), "K7b": ("ge", -0.005)}
KSHARE = 0.5
FIXED, ALLOW = {"K2a", "K2b"}, {"K5a", "K7a"}
if STAGE == "development":
    PRZ = json.load(open(LANE / "ar006" / "frozen" / "predictions.json"))
    assert PRZ["design_digest"] == M["design_digest"] and PRZ["k_share"] == KSHARE, "the frozen predictions differ"
    assert {x["key"]: (x["sense"], float(x["threshold"])) for x in PRZ["parts"]} == TH, "the frozen thresholds differ"
OK = {}
ci = lambda q: (f"{q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
                f"case/sqrt8 {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
R1t, R1p = over("vtol", "vms", 1, 1), over("vpool", "vms", 1, 1)
corr = lambda a, b, sg: u(a, "correlated", 4, sg) - u(b, "correlated", 4, sg)
PARTS = {
    "K1": ("vtol's sheet cost under scattered cue damage, cue@0", sham("cue@0", "vtol"), "le", "cost", 0.01),
    "K2a": ("vtol's sheet cost with no event, none@0", sham("none@0", "vtol"), "le", "cost", 0.002),
    "K2b": ("vtol's sheet cost, none@1 against the vote's none@0", sham("none@1", "vtol"), "le", "cost", 0.01),
    "K3a": ("R1 = mean over 4, 8 of u(vtol, memory@1) - u(vms, memory@1)", R1t, "ge", "contrast", None),
    "K4": ("R0 = mean over 4, 8 of u(vtol, memory@0) - u(vms, memory@0)", over("vtol", "vms", 0, 0), "ge", "contrast", None),
    "K5a": ("correlated@0: u(vtol) - u(vms)", corr("vtol", "vms", 0), "ge", "contrast", None),
    "K5b": ("correlated@0: u(vtol) - u(vguard)", corr("vtol", "vguard", 0), "ge", "contrast", None),
    "K5c": ("correlated@1: u(vtol) - u(vms)", corr("vtol", "vms", 1), "ge", "contrast", None),
    "K5d": ("correlated@1: u(vtol) - u(vguard)", corr("vtol", "vguard", 1), "ge", "contrast", None),
    "K6": ("W1 = mean over 4, 8 of u(vtol, memory@1) - u(vote, memory@0)", over("vtol", "vote", 1, 0), "ge", "contrast", None),
    "K7a": ("u(vtol) - u(vote) in the 4 x 4 patch, none@0", u("vtol", "none") - u("vote", "none"), "ge", "contrast", None),
    "K7b": ("u(vtol, none@1) - u(vote, none@0), 4 x 4 patch", u("vtol", "none", 4, 1) - u("vote", "none"), "ge", "contrast", None)}
say(f"\n2. THE PARTS ({NB} blocks; pooled over the eight unit-body pairs; [95% t interval], t(0.975, {NB - 1}) = {T975:.4f}; "
    f"SD_block the max rule" + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
Q = {}
for pid, (words, x, sense, kind, fixed) in PARTS.items():
    q = Q[pid] = est(x)
    line = f"   {pid:4s} {words}: {ci(q)}"
    if pid in TH:
        th = TH[pid][1]
        OK[pid] = q["v"] <= th if TH[pid][0] == "le" else q["v"] >= th
        line += f"  {'<=' if TH[pid][0] == 'le' else '>='} {th:+}: {'holds' if OK[pid] else 'FAILS'}"
    else:
        line += "  [reported: dropped by the rule]"
    if STAGE == "probe":
        raw, step, t = strictest(q, sense, kind)
        line += f"\n        the strictest {'floor' if sense == 'ge' else 'ceiling'} the rule allows {t:+.4f} (raw {raw:+.6f}, step {step})"
        if q["sd"] == 0:
            line += "; SD 0: the declared allowance -0.005"
        if fixed is not None:
            sup = t <= fixed + 1e-12
            line += f"; the fixed bound {fixed}: {'SUPPORTED' if sup else 'NOT supported (dropped and reported)'}"
        if pid in TH and pid not in FIXED and pid not in ALLOW:
            assert abs(t - TH[pid][1]) < 1e-9, (pid, t, TH[pid])
        if pid in ALLOW:
            assert q["sd"] == 0, pid
    say(line)
say("   K3b  R1(vtol) - k R1(vpool) >= 0" + (", the largest twentieth k the rule allows on P57:" if STAGE == "probe" else ":"))
if STAGE == "probe":
    kk = next((j / 20 for j in range(20, 0, -1) if (lambda qq: qq["v"] - K * qq["sd"] >= 0 and min(qq["halves"]) >= 0)(
        est(R1t - (j / 20) * R1p))), None)
    say(f"        k = {kk}" + (f": {ci(est(R1t - kk * R1p))}" if kk else ": no twentieth allowed"))
    assert kk == KSHARE, kk
qk = est(R1t - KSHARE * R1p)
OK["K3b"] = qk["v"] >= 0
say(f"        at the registered k {KSHARE}: {ci(qk)}  >= 0: {'holds' if OK['K3b'] else 'FAILS'}")
ST = {"K2": ["K2a", "K2b"], "K3": ["K3a", "K3b"], "K4": ["K4"], "K5": ["K5a", "K5b", "K5c", "K5d"], "K6": ["K6"],
      "K7": ["K7a", "K7b"]}
say("   VERDICTS: " + ", ".join(f"{k} {'HOLDS' if all(OK[x] for x in v) else 'FAILS'}" for k, v in ST.items())
    + "; K1 reported (dropped by the rule)" + ("" if STAGE == "development" else "  [not a development result]"))
if STAGE == "probe":
    assert all(OK.values()), OK
if STAGE == "development" and "vms" in RUNS["cue@0"]:
    say(f"   reported: vtol's cost less vms's under cue@0: {ci(est(sham('cue@0', 'vtol') - sham('cue@0', 'vms')))}")
q1 = est(R1p)
say(f"        (R1(vpool): {ci(q1)}; the share R1(vtol) / R1(vpool) {Q['K3a']['v'] / q1['v']:.4f})")

say("\n   REPORTED (not registered)")
for name, (run, arm) in {"vms's sheet cost, cue@0": ("cue@0", "vms"), "vpool's sheet cost, cue@0": ("cue@0", "vpool"),
                         "vms's sheet cost, none@0": ("none@0", "vms"), "vms's sheet cost, none@1": ("none@1", "vms")}.items():
    if run in RUNS and arm in RUNS[run]:
        say(f"   {name}: {ci(est(sham(run, arm)))}")
if "vote" in RUNS["cue@0"]:
    say(f"   u(vtol) - u(vote) inside the patch, cue@0: {ci(est(u('vtol', 'cue') - u('vote', 'cue')))}")
for L in (4, 8):
    say(f"   R1 at {L} x {L}: vtol {ci(est(u('vtol', 'memory', L, 1) - u('vms', 'memory', L, 1)))}")
say("   rates by run (fired at all / on the patch):")
for run, arms in RUNS.items():
    for a in [x for x in arms if x != "vote"]:
        say(f"     {run:13s} {a:6s} {fired(a, run).mean():.4f} / {located(a, run).mean():.4f}")

# ------------------------------------------------------------------------------------- 3. the raw final states
rin_max = rall_max = 0.0
n_checked = same_n = same_bad = 0
br = {"onset_min": [0, 0], "vms_branch": [0, 0], "vguard_branch": [0, 0], "union_zone": [0, 0], "not_before_vpool": [0, 0],
      "not_after_vms": [0, 0]}
BRT = {}                     # run -> vtol's branch counts (the lead's extension at the report, section 4)
for b, u_ in PAIRS:
    for k in BLOCKS:
        raw = np.load(ROOT / "raw" / b / u_ / f"{k}.npz")
        m = META[(b, u_, k)]
        cases = [Case(*c) for c in m["cases"]]
        T = raw["T"]
        pt = {L: B1S.patch(cases, L, m["tag"]) for L in sorted(set(SIZES.values()))}
        ins = lambda x, mm: (((x > 0) == (T > 0)) & mm).sum((-2, -1)) / mm.sum((-2, -1))
        for run, arms in RUNS.items():
            r = raw[f"{run}/r"]
            rB = raw[f"{run}/rB"]
            L = SIZES[run]
            for i, a in enumerate(arms):
                rin_max = max(rin_max, float(np.abs(ins(r[i], pt[L]) - Z[(b, u_, k)][f"{run}/r_in"][RI, i]).max()))
                rall_max = max(rall_max, float(np.abs(((r[i] > 0) == (T > 0)).mean((-2, -1)) - Z[(b, u_, k)][f"{run}/r_all"][RI, i]).max()))
                n_checked += 1
            rb_arms = [x for x in m["parts"][run][0] if x == "vote"] + m["parts"][run][2]
            vd = m["parts"][run][2]
            on = {a: Z[(b, u_, k)][f"{run}/det_on"][arms.index(a)] for a in arms if a != "vote"}
            inf = lambda x: np.where(x < 0, np.inf, x)
            # the vote-default identity
            ref = run if "vote" in arms else run.replace("@1", "@0")
            if ref in RUNS and "vote" in RUNS[ref]:
                rv, rbv = raw[f"{ref}/r"][RUNS[ref].index("vote")], raw[f"{ref}/rB"][0]
                for a in [x for x in arms if x != "vote"]:
                    ia = arms.index(a)
                    for j in np.flatnonzero(on[a] < 0):
                        same_n += 1
                        same_bad += int(not (np.array_equal(r[ia, j], rv[j]) and np.array_equal(rB[rb_arms.index(a), j], rbv[j])))
            # the branch identities
            zone = raw[f"{run}/zone"]
            zi = lambda a: vd.index(a)
            it, ib = arms.index("vtol"), rb_arms.index("vtol")
            if "vms" in arms and "vguard" in arms:
                for j in range(len(cases)):
                    om, og, ot = inf(on["vms"])[j], inf(on["vguard"])[j], inf(on["vtol"])[j]
                    br["onset_min"][0] += 1
                    br["onset_min"][1] += int(ot != min(om, og))
                    if np.isinf(ot):
                        continue
                    if om < og:
                        im, ibm = arms.index("vms"), rb_arms.index("vms")
                        br["vms_branch"][0] += 1
                        br["vms_branch"][1] += int(not (np.array_equal(r[it, j], r[im, j]) and np.array_equal(rB[ib, j], rB[ibm, j])
                                                        and np.array_equal(zone[zi("vtol"), j], zone[zi("vms"), j])))
                    elif og < om:
                        ig, ibg = arms.index("vguard"), rb_arms.index("vguard")
                        br["vguard_branch"][0] += 1
                        br["vguard_branch"][1] += int(not (np.array_equal(r[it, j], r[ig, j]) and np.array_equal(rB[ib, j], rB[ibg, j])
                                                           and np.array_equal(zone[zi("vtol"), j], zone[zi("vguard"), j])))
                    else:
                        br["union_zone"][0] += 1
                        br["union_zone"][1] += int(not np.array_equal(zone[zi("vtol"), j], zone[zi("vms"), j] | zone[zi("vguard"), j]))
            if "vpool" in arms:
                for j in range(len(cases)):
                    br["not_before_vpool"][0] += 1
                    br["not_before_vpool"][1] += int(inf(on["vtol"])[j] < inf(on["vpool"])[j])
            if "vms" in arms:
                for j in range(len(cases)):
                    br["not_after_vms"][0] += 1
                    br["not_after_vms"][1] += int(inf(on["vtol"])[j] > inf(on["vms"])[j])
            # the branch accounting (the lead's extension at the report): per lineage-case vtol on the vote's branch (it
            # never fired), on vms's or vguard's exactly (the same onset, and the final records and zone bit for bit),
            # on another (a union branch), or not compared (a run with neither reference arm)
            refs = [a for a in ("vms", "vguard") if a in arms]
            cnt = BRT.setdefault(run, {"n": 0, "vote": 0, "vms": 0, "vguard": 0, "other": 0, "not_compared": 0})
            for j in range(len(cases)):
                cnt["n"] += 1
                if on["vtol"][j] < 0:
                    cnt["vote"] += 1
                    continue
                if not refs:
                    cnt["not_compared"] += 1
                    continue
                for a in refs:
                    ia, iba = arms.index(a), rb_arms.index(a)
                    if (on[a][j] == on["vtol"][j] and np.array_equal(r[it, j], r[ia, j]) and np.array_equal(rB[ib, j], rB[iba, j])
                            and np.array_equal(zone[zi("vtol"), j], zone[zi(a), j])):
                        cnt[a] += 1
                        break
                else:
                    cnt["other"] += 1
say(f"\n3. FROM THE RAW FINAL STATES (the lead's own scoring; the patch from be001.sim.patch): r_in and r_all recomputed "
    f"from the final records, {n_checked} arm-runs x 8 cases: largest difference {rin_max:.2e} and {rall_max:.2e}; a "
    f"vote-default arm that never fired against the vote, both records, bit for bit: {same_n - same_bad} of {same_n} "
    f"lineage-cases equal")
say("   the derivation's branch identities (checked, failures): " + "; ".join(f"{k} {v[0]} checked, {v[1]} fail" for k, v in br.items()))
assert rin_max <= 1e-12 and rall_max <= 1e-12 and same_bad == 0
assert all(v[1] == 0 for v in br.values()), br

# ---------- 4. the reported contrasts, levels, recovery fractions and branches (the lead's extension; written after the
# development's values, 3 November 2026 about 17:45Z; not registered, changing no verdict), from the plan's words
say("\n4. REPORTED (the lead's extension after the development's values)")
CON = {
    "K3 R1 vtol (misread recovery over vms, sizes 4 and 8)": over("vtol", "vms", 1, 1),
    "R1 vpool (sizes 4 and 8)": over("vpool", "vms", 1, 1),
    "R1 vtol less vpool": over("vtol", "vpool", 1, 1),
    "R1 vguard (sizes 4 and 8)": over("vguard", "vms", 1, 1),
    "R1 vtol less vguard": over("vtol", "vguard", 1, 1),
    "K4 R0 vtol (sigma-0 hits against vms)": over("vtol", "vms", 0, 0),
    "vms misread loss (sigma 1 - sigma 0)": over("vms", "vms", 1, 0),
    "K6 W1 vtol (worth over the vote under misreads)": over("vtol", "vote", 1, 0),
    "W1 vms": over("vms", "vote", 1, 0), "W1 vpool": over("vpool", "vote", 1, 0), "W1 vguard": over("vguard", "vote", 1, 0),
    "sham cue@0 vms": sham("cue@0", "vms"), "sham cue@0 vpool": sham("cue@0", "vpool"),
    "K1 (not registered: beside the confirmed 0.01) sham cue@0 vtol": sham("cue@0", "vtol"),
    "sham cue@0: vtol less vms (the extra false-alarm cost)": sham("cue@0", "vtol") - sham("cue@0", "vms"),
    "sham none@0 vms": sham("none@0", "vms"), "K2a sham none@0 vtol": sham("none@0", "vtol"),
    "sham none@0: vtol less vms (the extra false-alarm cost)": sham("none@0", "vtol") - sham("none@0", "vms"),
    "sham none@1 vms": sham("none@1", "vms"), "K2b sham none@1 vtol": sham("none@1", "vtol"),
    "sham none@1: vtol less vms (the extra false-alarm cost)": sham("none@1", "vtol") - sham("none@1", "vms"),
    "K7a give none@0 vtol": u("vtol", "none") - u("vote", "none"),
    "K7b give none@1 vtol": u("vtol", "none", 4, 1) - u("vote", "none", 4, 1),
    "give cue@0 (reported: inside the patch) vtol": u("vtol", "cue") - u("vote", "cue"),
    "K5a corr@0: u(vtol) - u(vms)": u("vtol", "correlated") - u("vms", "correlated"),
    "K5b corr@0: u(vtol) - u(vguard)": u("vtol", "correlated") - u("vguard", "correlated"),
    "corr@0: u(vtol) - u(vpool)": u("vtol", "correlated") - u("vpool", "correlated"),
    "K5c corr@1: u(vtol) - u(vms)": u("vtol", "correlated", 4, 1) - u("vms", "correlated", 4, 1),
    "K5d corr@1: u(vtol) - u(vguard)": u("vtol", "correlated", 4, 1) - u("vguard", "correlated", 4, 1),
    "corr@1: u(vtol) - u(vpool)": u("vtol", "correlated", 4, 1) - u("vpool", "correlated", 4, 1)}
for L in (4, 8):
    for sg, others in ((0, ("vms",)), (1, ("vms", "vpool", "vguard"))):
        for o in others:
            CON[f"u(vtol) - u({o}), memory@{sg} L{L}"] = u("vtol", "memory", L, sg) - u(o, "memory", L, sg)
MINE = {k: est(v) for k, v in CON.items()}
for k, q in MINE.items():
    say(f"   {k}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}; halves {q['halves'][0]:+.6f} "
        f"{q['halves'][1]:+.6f})")
ploss = -MINE["vms misread loss (sigma 1 - sigma 0)"]["v"]
REC = {a: MINE[n]["v"] / ploss for a, n in (("vpool", "R1 vpool (sizes 4 and 8)"), ("vguard", "R1 vguard (sizes 4 and 8)"),
                                            ("vtol", "K3 R1 vtol (misread recovery over vms, sizes 4 and 8)"))}
say("   the recovery fraction (R1 over vms's own misread loss, sizes 4 and 8): " + ", ".join(f"{a} {v:.4f}" for a, v in REC.items()))
ULEV = {f"{a}/{run}": float(pool(lc(run, a, "r_in")).mean()) for run, arms in RUNS.items() for a in arms}
say("   u by arm and run: " + "; ".join(f"{k} {v:.4f}" for k, v in ULEV.items()))
# the same accounting by outcome (the frozen tables' stated rule, written out by the lead): on vms's or vguard's branch
# when the onset, the 40-point trace and every endpoint at every read equal that arm's (vms tried first)
ENDS6 = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
BRO = {}
for run, arms in RUNS.items():
    if "vtol" not in arms:
        continue
    ai = arms.index("vtol")
    refs = [a for a in ("vms", "vguard") if a in arms]
    c = BRO.setdefault(run, {"n": 0, "vote": 0, "vms": 0, "vguard": 0, "other": 0, "not_compared": 0})
    for key, z in Z.items():
        ont = z[f"{run}/det_on"][ai]
        for j in range(len(ont)):
            c["n"] += 1
            if ont[j] < 0:
                c["vote"] += 1
                continue
            if not refs:
                c["not_compared"] += 1
                continue
            for a in refs:
                ja = arms.index(a)
                if (z[f"{run}/det_on"][ja][j] == ont[j] and np.array_equal(z[f"{run}/trace"][:, ai, j], z[f"{run}/trace"][:, ja, j])
                        and all(np.array_equal(z[f"{run}/{e}"][:, ai, j], z[f"{run}/{e}"][:, ja, j]) for e in ENDS6)):
                    c[a] += 1
                    break
            else:
                c["other"] += 1
fmt = lambda D: "; ".join(f"{run} {c['vote']}/{c['vms']}/{c['vguard']}/{c['other']}/{c['not_compared']} of {c['n']}"
                          for run, c in D.items())
say("   vtol's branch per lineage-case, by outcome (onset, trace and every endpoint at every read equal; the vote's / vms's "
    "/ vguard's / another / not compared, of n): " + fmt(BRO))
say("   the same by state (the same onset, and the final records and zone bit for bit): " + fmt(BRT))
say("   (the two differ only where vms and vguard both fire at vtol's onset: its zone is then their union, checked in "
    "section 3, which may equal one arm's zone, and its outcome may equal vms's where its state does not; vms is tried first)")
UT = LANE / "results" / "ar006" / "utilities.json"
if STAGE == "development" and UT.exists():
    fr = json.load(open(UT))
    assert sorted(fr["contrasts"]) == sorted(MINE), sorted(set(fr["contrasts"]) ^ set(MINE))
    dv = max(abs(MINE[k]["v"] - x["mean"]) for k, x in fr["contrasts"].items())
    di = max(max(abs(MINE[k]["lo"] - x["lo"]), abs(MINE[k]["hi"] - x["hi"])) for k, x in fr["contrasts"].items())
    db = max(float(np.abs(CON[k].mean(1) - np.array(x["blocks"])).max()) for k, x in fr["contrasts"].items())
    dr = max(abs(REC[a] - fr["recovery_fraction"][a]) for a in REC)
    assert sorted(fr["u"]) == sorted(ULEV)
    du = max(abs(ULEV[k] - v) for k, v in fr["u"].items())
    keys = ("n", "vote", "vms", "vguard", "other", "not_compared")
    same_br = {run: {k: c[k] for k in keys} for run, c in BRO.items()} == {run: {k: c[k] for k in keys} for run, c in fr["branches"].items()}
    say(f"   AGAINST THE FROZEN READER (results/ar006/utilities.json; {len(MINE)} contrasts, {len(ULEV)} levels): largest "
        f"|difference| value {dv:.1e}, interval {di:.1e}, block values {db:.1e}; recovery fractions {dr:.1e}; levels "
        f"{du:.1e}; the branch table by outcome {'equal in every run' if same_br else 'DIFFERS'}")
    assert dv < 1e-9 and di < 1e-9 and db < 1e-9 and dr < 1e-9 and du < 1e-9 and same_br

name = f"p57c_ar006_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
