"""P53c (python probes/p53c_ar005_lead_check.py ROOT): the lead's check of AR005, a second check against scattered false
alarms. LEAD_CHECK_NOT_REGISTERED; a read of the shards and of the raw final states, written by the lead in reviewing
AR005's phase A and committed before the freeze, dry-run first on the tuning block (900717) and on P53 (engineering
blocks 900729, 900739 | 900749, 900759; tag mse-p53); 2 November 2026; no simulation.

It checks, from PLAN_AR005.md's words (with its amendment of 15:34Z) and not from ar005.analyze, ar005.predict or
ar003.analyze:
0. the guard's arithmetic, independently of the integral images: on synthetic states, the lead's own loop over every
   periodic b x b window (boxes 2-12) counts the disagreeing live anchors, the live anchors, the ring of width 2 and the
   guard's count, and its windows must equal ar005.sim.guarded_windows' exactly for the body guard at f 1, 0.5 and 0 and
   the density guard at 1/4; with the pass-all guard (f 0) they must equal ar002.sim.cue_windows_multi's;
1. the sha256 of every shard and raw file against the run's manifest; the stage's blocks and tag; every shard's runs,
   arms and detectors (vms = DET_STAR; vpool = pool-n3-q1-r1; vguard = DET_POOL with the guard the tuning chose); at the
   development stage the run's digest and sources against ar005/frozen/design.json;
2. at the tuning stage, the tuning rule re-applied (the four eligibility conditions on the block's 64 lineage-cases and
   the choice: the largest Rc, ties within 0.005 to the grid's order);
3. from P53 on, the parts K1-K7 by the plan's words: u(arm, run) the record's agreement with the correct target inside
   the run's patch at t = 8,000 (r_in), pooled per case over the eight unit-body pairs, the vote's sigma-1 value its
   sigma-0 run's; the sheet's cost r_all(vote) - r_all(arm) (for a sigma-1 run the vote's sigma-0 run); the statements
   over the sizes 4 and 8; a block's value the mean of its 8 cases; SD_block the larger of the block SD and the case SD
   / sqrt 8; the 95% t interval; on P53 the margins (>= 3 sqrt(1/4 + 1/16)), both halves and the strictest round
   threshold the rule allows (sheet costs in thousandths; contrasts in hundredths, or 0.005 where the strictest value
   lies within 0.01 of zero; the share k in twentieths); the fixed bounds (0.01, 0.002, 0.01) kept only if supported;
4. from the raw final states, with the lead's own scoring (the patch from LR005's frozen draw, be001.sim.patch): every
   run's r_in and r_all recomputed from the final records; a vote-default arm that never fired equals the vote bit for
   bit (both records), at sigma 0 within its run and at sigma 1 against the vote's sigma-0 run of the same situation and
   size, wherever that run exists.
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
from ar002 import sim as A2S                                     # noqa: E402  (frozen: the cue channel's windows)
from ar005 import sim as A5S                                     # noqa: E402  (under check: the guarded windows)
from be001 import sim as B1S                                     # noqa: E402  (frozen: LR005's patch draw)
from lr005 import design as L5D                                  # noqa: E402  (frozen: VMIN)
from mse.assay import Case                                       # noqa: E402  (frozen engine: the case keys)

ROOT = Path(sys.argv[1])
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
STAR = {"boxes": list(range(2, 13)), "n": 3, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}
POOL = dict(STAR, ring_max=1)
GUARDS = {"g-body-f1": {"kind": "body", "f": 1.0}, "g-body-f05": {"kind": "body", "f": 0.5},
          "g-dense-25": {"kind": "dense", "delta": 0.25}}
GRID = ("g-body-f1", "g-body-f05", "g-dense-25")

# ------------------------------------------------------------------------------------- 0. the guard's arithmetic
assert L5D.VMIN == 0.2


def naive(V, r, am, aval, ch, guard):
    """The lead's loop: {box: (k, n, n) bool} by top-left corner, periodic."""
    k, n = r.shape[0], r.shape[-1]
    vs = lambda x: np.where(x >= 0.2, 1, np.where(x <= -0.2, -1, 0))
    sr, sv = vs(r), vs(V)
    ca = np.where(am, aval, 0)
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    bod = dis & (sv != 0) & (sv != sr)
    g, res = ch["ring"], {}
    for b in ch["boxes"]:
        f = np.zeros((k, n, n), bool)
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
                    ok = nd >= ch["n"] and nd >= ch["q"] * nl and (g == 0 or ring <= ch["ring_max"])
                    if guard is not None and guard["kind"] == "body":
                        ok = ok and int(bod[c][np.ix_(rows, cols)].sum()) >= guard["f"] * nd
                    elif guard is not None:
                        ok = ok and nl >= guard["delta"] * b * b
                    f[c, i, j] = ok
        res[b] = f
    return res


rng = np.random.default_rng(530)
n_win, held = 0, {}
# (patches flipped in the record, the share of anchors with a scattered flip, the anchor density): small patches and
# light cue damage hold many windows under the ring; the last is AR004's scattered damage over a large patch
SETUPS = [([(2, 6, 2, 6), (9, 13, 9, 13)], 0.03, 0.25, -0.4), ([(3, 9, 5, 11)], 0.0, 0.4, -0.4),
          ([(2, 10, 2, 10)], 0.25, 0.55, -0.4), ([(1, 5, 10, 14), (8, 12, 2, 6)], 0.02, 0.5, -0.4),
          ([(2, 6, 2, 6), (9, 14, 8, 13)], 0.02, 0.4, 0.05)]                  # the last with a confident body
for trial, (patches, pflip, dens, vlo) in enumerate(SETUPS):
    k, n = 3, 16
    T = np.where(rng.random((k, n, n)) < 0.5, 1.0, -1.0)
    T[:, 4:12, 4:12] = 1.0                                       # a pattern with walls
    r = T * rng.uniform(0.1, 1.2, (k, n, n))                     # some sites below VMIN
    for a0, a1, b0, b1 in patches:
        r[:, a0:a1, b0:b1] *= -1                                 # the record flipped in the patch (memory damage)
    V = T * rng.uniform(vlo, 1.2, (k, n, n))                     # a body mostly right: sometimes unconfident or wrong
    am = rng.random((k, n, n)) < dens
    aval = T.copy()
    aval[rng.random((k, n, n)) < pflip] *= -1                    # scattered cue damage
    P = {"am": am, "aval": aval}
    for cname, ch in (("DET_POOL", POOL), ("n 2, q 0.75", dict(POOL, n=2, q=0.75))):
        for gname, guard in [("f 1", {"kind": "body", "f": 1.0}), ("f 0.5", {"kind": "body", "f": 0.5}),
                             ("f 0", {"kind": "body", "f": 0.0}), ("dense 1/4", {"kind": "dense", "delta": 0.25})]:
            a = A5S.guarded_windows(V, r, P, ch, guard)
            b_ = naive(V, r, am, aval, ch, guard)
            assert sorted(a) == sorted(b_) == ch["boxes"]
            for bx in ch["boxes"]:
                assert np.array_equal(a[bx], b_[bx]), (trial, cname, gname, bx, int((a[bx] != b_[bx]).sum()))
                n_win += a[bx].size
                held[(cname, gname)] = held.get((cname, gname), 0) + int(a[bx].sum())
        base = A2S.cue_windows_multi(r, P, ch)
        f0 = A5S.guarded_windows(V, r, P, ch, {"kind": "body", "f": 0.0})
        assert all(np.array_equal(base[bx], f0[bx]) for bx in ch["boxes"])
assert all(held[(c, "f 1")] < held[(c, "f 0.5")] < held[(c, "f 0")] for c in ("DET_POOL", "n 2, q 0.75")), held
assert held[("DET_POOL", "f 1")] >= 10 and held[("DET_POOL", "dense 1/4")] < held[("DET_POOL", "f 0")], held
say(f"0. the guard's arithmetic: on {len(SETUPS)} synthetic states (3 cases, 16 x 16, boxes 2-12; flipped record "
    f"patches, a body mostly right, scattered cue damage at several rates and anchor densities), the lead's loop equals ar005.sim.guarded_windows for the body guard at f 1, "
    f"0.5 and 0 and the density guard at 1/4, under DET_POOL's criterion and a second (n 2, q 0.75): {n_win} windows, "
    f"0 differ; windows held " + "; ".join(f"{c} {g} {v}" for (c, g), v in held.items())
    + "; the pass-all guard equals ar002.sim.cue_windows_multi exactly")

# ------------------------------------------------------------------------------------- 1. integrity and the design
M = json.load(open(ROOT / "manifest.json"))
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values()
       if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
DEV = [910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798, 910799, 910826,
       910827, 910958]
WANT = {"tuning": ("mse-p53", [900717]), "probe": ("mse-p53", [900729, 900739, 900749, 900759]),
        "debug": ("mse-ar005", [900799]), "preflight": ("mse-ar005", [900779, 900789]), "development": ("mse-ar005", DEV)}
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == WANT[STAGE][0] and not bad, (STAGE, M["tag"], bad[:5])
BLOCKS = list(M["blocks"])
assert BLOCKS == WANT[STAGE][1], BLOCKS
NB = len(BLOCKS)
AR004 = "7cd71b5b29cf573292c240f5245e1d0df45ca368c05b277079b7775631b94233"
AR003 = "d392002671e648280d9746a336276d9fbf03e17d44c7d144802d9b7f9e84a47e"
assert M["ar004_digest"] == AR004 and M["ar003_digest"] == AR003
for frz, dg in (("ar003", AR003), ("ar004", AR004)):
    FZ_ = json.load(open(LANE / frz / "frozen" / "design.json"))
    assert FZ_["digest"] == dg
    changed = [p for p, h in FZ_["sources"].items() if hashlib.sha256((LANE / p).read_bytes()).hexdigest() != h]
    assert not changed, (frz, changed)
if STAGE == "development":
    FZ = json.load(open(LANE / "ar005" / "frozen" / "design.json"))
    assert FZ["digest"] == M["design_digest"], "the draw is not under the frozen design"
    changed = [p for p, h in FZ["sources"].items() if hashlib.sha256((LANE / p).read_bytes()).hexdigest() != h]
    assert not changed, changed
say(f"\n1. P53c on {ROOT} ({STAGE}{', DRY RUN on engineering blocks' if STAGE != 'development' else ''}): "
    f"{len(M['tasks'])} tasks, {sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the "
    f"manifest's; digest {M['design_digest'][:12]} (AR004's {AR004[:12]} and AR003's {AR003[:12]}, their frozen sources "
    f"unchanged); {M['started_utc']} - {M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h, {M['workers']} workers")
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
assert len(M["tasks"]) == len(PAIRS) * NB
Z = {(b, u, k): dict(np.load(ROOT / "shards" / b / u / f"{k}.npz")) for b, u in PAIRS for k in BLOCKS}
META = {key: json.loads(str(z["__meta__"])) for key, z in Z.items()}
M0 = META[(*PAIRS[0], BLOCKS[0])]
RUNS = {rn: arms for rn, arms in M0["runs"]}
SIZES = M0["sizes"]
V1, ALL = ["vote"], ["vms", "vpool", "vguard"]
WANT_RUNS = {
    "tuning": {"cue@0": ["vote", "vpool", *GRID], "none@0": ["vote"], "none@1": list(GRID),
               "memory@1": ["vms", "vpool", *GRID], "memory@1-L8": ["vms", "vpool", *GRID], "memory@0": ["vms", *GRID],
               "correlated@1": ["vpool", *GRID]},
    "probe": {"memory@0": ["vote", "vms", "vguard"], "memory@0-L8": ["vote", "vms", "vguard"],
              "memory@1": ["vms", "vpool", "vguard"], "memory@1-L8": ["vms", "vpool", "vguard"],
              "none@0": ["vote", "vguard"], "none@1": ["vguard"], "cue@0": ["vote", "vguard"],
              "correlated@0": ["vote", "vpool", "vguard"], "correlated@1": ["vpool", "vguard"]}}
WANT_RUNS["development"] = {**{f"memory@0{s}": V1 + ALL for s in ("-L2", "", "-L8")},
                            **{f"memory@1{s}": ALL for s in ("-L2", "", "-L8")},
                            "none@0": V1 + ALL, "none@1": ALL, "cue@0": V1 + ALL, "correlated@0": V1 + ALL,
                            "correlated@1": ALL, "body@0": V1 + ALL}
WANT_RUNS["debug"] = WANT_RUNS["preflight"] = WANT_RUNS["development"]
assert {k: sorted(v) for k, v in RUNS.items()} == {k: sorted(v) for k, v in WANT_RUNS[STAGE].items()}, RUNS
VG = "g-body-f05"                                                # the tuning's choice, as ar005/design.py records it
for (b, u, k), m in META.items():
    assert {rn: a for rn, a in m["runs"]} == RUNS and m["sizes"] == SIZES and (m["body"], m["unit"], int(m["block"])) == (b, u, k)
    assert m["study"] == "AR005" and m["tag"] == M["tag"] and m["design_digest"] == M["design_digest"]
    det = m["vd_detectors"]
    assert det["vote"] == {"never": True}
    assert det["vms"] == {"cue": STAR, "body": None} and det["vpool"] == {"cue": POOL, "body": None}
    if STAGE == "tuning":
        assert all(det[g] == {"cue": POOL, "body": None, "guard": GUARDS[g]} for g in GRID)
    else:
        assert m["vguard_name"] == VG and det["vguard"] == {"cue": POOL, "body": None, "guard": GUARDS[VG]}
    assert len(m["cases"]) == 8 and all(int(c[0]) == k for c in m["cases"])
RI = M0["reads"].index(8000)
say("   runs: " + ", ".join(f"{r} (L {SIZES[r]}; {', '.join(a)})" for r, a in RUNS.items()))
say(f"   detectors in every shard: vms DET_STAR, vpool pool-n3-q1-r1"
    + (", the three candidates DET_POOL with their guards" if STAGE == "tuning" else f", vguard DET_POOL + {VG}"))


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
        assert arm == "vote" and sg == 1, (arm, run)
        run = rname(s, L, 0)                                    # the vote never reads the cue
    return pool(lc(run, arm, "r_in"))


def sham(run, arm):
    ref = run if "vote" in RUNS[run] else run.replace("@1", "@0")
    return pool(lc(ref, "vote", "r_all") - lc(run, arm, "r_all"))


located = lambda arm, run: pool(((lc(run, arm, "det_on", None) > 0) & (lc(run, arm, "det_fp_in", None) > 0)).astype(float))
fired = lambda arm, run: pool((lc(run, arm, "det_on", None) > 0).astype(float))
over = lambda a, b, sa, sb, Ls=(4, 8): sum(u(a, "memory", L, sa) - u(b, "memory", L, sb) for L in Ls) / len(Ls)

# ------------------------------------------------------------------------------------- 2. the tuning rule
if STAGE == "tuning":
    say("\n2. THE TUNING RULE re-applied (the block's 64 lineage-cases a run; means)")
    rows, elig = {}, []
    for c in GRID:
        cue = float(sham("cue@0", c).mean())
        n1 = float(pool(lc("none@0", "vote", "r_all") - lc("none@1", c, "r_all")).mean())
        hit = float((u(c, "memory", 4, 0) - u("vms", "memory", 4, 0)).mean())
        rc = float(over(c, "vms", 1, 1).mean())
        cor = float((u("vpool", "correlated", 4, 1) - u(c, "correlated", 4, 1)).mean())
        ok = cue <= 0.0075 and n1 <= 0.0075 and hit >= -0.01 and rc > 0
        rows[c] = (cue, n1, hit, rc, cor, ok)
        if ok:
            elig.append(c)
        say(f"   {c:10s} sheet cost cue@0 {cue:+.5f} (<= 0.0075 {cue <= 0.0075}); none@1 vs the vote's none@0 {n1:+.5f} "
            f"(<= 0.0075 {n1 <= 0.0075}); hits kept memory@0 4 x 4 {hit:+.4f} (>= -0.01 {hit >= -0.01}); Rc {rc:+.4f} "
            f"(> 0 {rc > 0}); reported corr1 u(vpool) - u(c) {cor:+.4f}: {'ELIGIBLE' if ok else 'not eligible'}")
    say(f"   vpool (the parent): sheet cost cue@0 {float(sham('cue@0', 'vpool').mean()):+.5f}; Rc "
        f"{float(over('vpool', 'vms', 1, 1).mean()):+.4f}")
    if elig:
        best = max(rows[c][3] for c in elig)
        choice = next(c for c in GRID if c in elig and rows[c][3] >= best - 0.005)
    else:
        choice = None
    from ar005 import design as A5D                              # the choice as the package records it
    say(f"   eligible {elig}; THE CHOICE by the rule: {choice}; ar005/design.py's VGUARD_NAME: {A5D.VGUARD_NAME}: "
        + ("equal" if choice == A5D.VGUARD_NAME else "DIFFERENT"))
    assert choice == A5D.VGUARD_NAME == VG

# ------------------------------------------------------------------------------------- 3. the parts
K = 3 * math.sqrt(1 / 4 + 1 / 16)
# the registration's thresholds as the lead ruled on phase A (REGISTRATION_AR005.md): sense, threshold
TH = {"K1": ("le", 0.01), "K2a": ("le", 0.002), "K2b": ("le", 0.01), "K3a": ("ge", 0.01), "K3b": ("ge", 0.0),
      "K4": ("ge", -0.01), "K5": ("ge", 0.12), "K6a": ("le", 0.40), "K6b": ("le", 0.37), "K6c0": ("ge", 0.08),
      "K6c1": ("ge", 0.02), "K7a": ("ge", -0.005), "K7b": ("ge", -0.005)}
KSHARE = 0.25                     # K3b's share of vpool's recovery: the largest twentieth the rule allowed on P53
FIXED = {"K1", "K2a", "K2b"}      # the confirmed bounds, kept because P53 supports them
ALLOW = {"K7a", "K7b"}            # SD 0 on P53: the declared allowance -0.005 (AR003's E8, AR004's G5n)
if STAGE == "development":
    PR = json.load(open(LANE / "ar005" / "frozen" / "predictions.json"))
    assert PR["design_digest"] == M["design_digest"] and PR["k_share"] == KSHARE, "the frozen predictions differ"
    assert {x["key"]: (x["sense"], float(x["threshold"])) for x in PR["parts"]} == TH, "the frozen thresholds differ"
T975 = stats.t.ppf(0.975, NB - 1) if NB > 1 else float("nan")


def est(x):
    blk = x.mean(1)
    v = float(blk.mean())
    sdc = float(x.ravel().std(ddof=1)) / math.sqrt(x.shape[1])
    sdb = float(blk.std(ddof=1)) if NB > 1 else float("nan")
    sd = max(sdb, sdc) if NB > 1 else sdc
    h = T975 * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sdb": sdb, "sdc": sdc, "x": x,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean())) if NB > 1 else (v, v)}


def strictest(q, sense, kind):
    """The strictest round threshold the rule allows on P53 (sense 'ge' a floor, 'le' a ceiling)."""
    raw = min(q["v"] - K * q["sd"], *q["halves"]) if sense == "ge" else max(q["v"] + K * q["sd"], *q["halves"])
    step = 0.001 if kind == "cost" else (0.005 if abs(raw) <= 0.01 else 0.01)
    t = (math.floor(round(raw / step, 9)) if sense == "ge" else math.ceil(round(raw / step, 9))) * step
    return raw, step, round(t, 4)


ci = lambda q: (f"{q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
                f"case/sqrt8 {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
if STAGE != "tuning":
    R1g, R1p = over("vguard", "vms", 1, 1), over("vpool", "vms", 1, 1)
    # id: (words, values, sense, kind, the fixed bound or None)
    PARTS = {
        "K1": ("vguard's sheet cost under scattered cue damage, cue@0", sham("cue@0", "vguard"), "le", "cost", 0.01),
        "K2a": ("vguard's sheet cost with no event, none@0", sham("none@0", "vguard"), "le", "cost", 0.002),
        "K2b": ("vguard's sheet cost, none@1 against the vote's none@0", sham("none@1", "vguard"), "le", "cost", 0.01),
        "K3a": ("R1g = mean over 4, 8 of u(vguard, memory@1) - u(vms, memory@1)", R1g, "ge", "contrast", None),
        "K4": ("R0g = mean over 4, 8 of u(vguard, memory@0) - u(vms, memory@0)", over("vguard", "vms", 0, 0), "ge",
               "contrast", None),
        "K5": ("W1g = mean over 4, 8 of u(vguard, memory@1) - u(vote, memory@0)", over("vguard", "vote", 1, 0), "ge",
               "contrast", None),
        "K6a": ("u(vpool) - u(vguard), correlated@0", u("vpool", "correlated") - u("vguard", "correlated"), "le",
                "contrast", None),
        "K6b": ("u(vpool) - u(vguard), correlated@1", u("vpool", "correlated", 4, 1) - u("vguard", "correlated", 4, 1),
                "le", "contrast", None),
        "K6c0": ("u(vguard) - u(vote), correlated@0", u("vguard", "correlated") - u("vote", "correlated"), "ge",
                 "contrast", None),
        "K6c1": ("u(vguard, correlated@1) - u(vote, correlated@0)", u("vguard", "correlated", 4, 1) - u("vote", "correlated"),
                 "ge", "contrast", None),
        "K7a": ("u(vguard) - u(vote) in the 4 x 4 patch, none@0", u("vguard", "none") - u("vote", "none"), "ge",
                "contrast", None),
        "K7b": ("u(vguard, none@1) - u(vote, none@0), 4 x 4 patch", u("vguard", "none", 4, 1) - u("vote", "none"), "ge",
                "contrast", None)}
    say(f"\n3. THE PARTS ({NB} blocks; pooled over the eight unit-body pairs; [95% t interval], t(0.975, {NB - 1}) = "
        f"{T975:.4f}; SD_block the max rule" + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
    Q, OK = {}, {}
    for pid, (words, x, sense, kind, fixed) in PARTS.items():
        q = Q[pid] = est(x)
        assert TH[pid][0] == sense
        th = TH[pid][1]
        OK[pid] = q["v"] <= th if sense == "le" else q["v"] >= th
        line = f"   {pid:4s} {words}: {ci(q)}  {'<=' if sense == 'le' else '>='} {th:+}: {'holds' if OK[pid] else 'FAILS'}"
        if STAGE == "probe":
            raw, step, t = strictest(q, sense, kind)
            if pid in ALLOW:
                assert q["sd"] == 0, pid
            elif pid not in FIXED:
                assert abs(t - th) < 1e-9, (pid, t, th)
            line += f"\n        the strictest {'floor' if sense == 'ge' else 'ceiling'} the rule allows {t:+.4f} (raw {raw:+.6f}, step {step})"
            if fixed is not None:
                sup = t <= fixed + 1e-12
                line += f"; the fixed bound {fixed}: {'SUPPORTED' if sup else 'NOT supported (dropped and reported)'}"
                if sup:
                    mg = (fixed - q["v"]) / q["sd"] if q["sd"] > 0 else math.inf
                    line += f", margin {mg:.3f}"
        say(line)
    # K3b: R1g - k R1p >= 0 at the registered k; on P53 the largest twentieth the rule allows must be that k
    q = Q["K3b"] = est(R1g - KSHARE * R1p)
    OK["K3b"] = q["v"] >= TH["K3b"][1]
    say(f"   K3b  R1g - {KSHARE} R1p: {ci(q)}  >= 0: {'holds' if OK['K3b'] else 'FAILS'}"
        + (f"; margin {q['v'] / q['sd']:.3f}" if q["sd"] > 0 else ""))
    if STAGE == "probe":
        kk = next((j / 20 for j in range(20, 0, -1) if (lambda qq: qq["v"] - K * qq["sd"] >= 0 and min(qq["halves"]) >= 0)(
            est(R1g - (j / 20) * R1p))), None)
        say(f"        the largest twentieth k the rule allows on P53: {kk}")
        assert kk == KSHARE, kk
    q1 = est(R1p)
    say(f"        (R1p, vpool's contrast: {ci(q1)}; the share R1g / R1p {Q['K3a']['v'] / q1['v']:.4f})")
    ST = {"K1": ["K1"], "K2": ["K2a", "K2b"], "K3": ["K3a", "K3b"], "K4": ["K4"], "K5": ["K5"],
          "K6": ["K6a", "K6b", "K6c0", "K6c1"], "K7": ["K7a", "K7b"]}
    say("   VERDICTS: " + ", ".join(f"{k} {'HOLDS' if all(OK[x] for x in v) else 'FAILS'}" for k, v in ST.items())
        + ("" if STAGE == "development" else "  [not a development result]"))
    if STAGE == "probe":
        assert all(OK.values()), OK

    say("\n   REPORTED (not registered)")
    rep = {"vpool's sheet cost, cue@0": ("cue@0", "vpool"), "vms's sheet cost, cue@0": ("cue@0", "vms"),
           "vpool's sheet cost, none@0": ("none@0", "vpool"), "vms's sheet cost, none@0": ("none@0", "vms"),
           "vpool's sheet cost, none@1": ("none@1", "vpool"), "vms's sheet cost, none@1": ("none@1", "vms")}
    for name, (run, arm) in rep.items():
        if run in RUNS and arm in RUNS[run]:
            say(f"   {name}: {ci(est(sham(run, arm)))}")
    if "vote" in RUNS["cue@0"]:
        say(f"   u(vguard) - u(vote) inside the patch, cue@0: {ci(est(u('vguard', 'cue') - u('vote', 'cue')))}")
    if "body@0" in RUNS:
        say(f"   u(vguard) - u(vote), body@0: {ci(est(u('vguard', 'body') - u('vote', 'body')))}")
        say(f"   vguard's sheet cost, body@0: {ci(est(sham('body@0', 'vguard')))}")
    if "memory@1-L2" in RUNS:
        say(f"   R1g at 2 x 2: {ci(est(u('vguard', 'memory', 2, 1) - u('vms', 'memory', 2, 1)))}")
    for L in (4, 8):
        say(f"   R1g at {L} x {L}: {ci(est(u('vguard', 'memory', L, 1) - u('vms', 'memory', L, 1)))}; "
            f"R1p: {ci(est(u('vpool', 'memory', L, 1) - u('vms', 'memory', L, 1)))}")
    num, den = over("vguard", "vms", 1, 1), over("vms", "vms", 0, 1)
    say(f"   the recovery fraction (vguard over vms's misread loss), sizes 4 and 8: {num.mean() / den.mean():.4f}")
    say("   rates by run (fired at all / on the patch):")
    for run, arms in RUNS.items():
        for a in [x for x in arms if x != "vote"]:
            say(f"     {run:13s} {a:6s} {fired(a, run).mean():.4f} / {located(a, run).mean():.4f}")

# ------------------------------------------------------------------------------------- 4. the raw final states
rin_max = rall_max = 0.0
n_checked = same_n = same_bad = 0
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
            L = SIZES[run]
            for i, a in enumerate(arms):
                rin_max = max(rin_max, float(np.abs(ins(r[i], pt[L]) - Z[(b, u_, k)][f"{run}/r_in"][RI, i]).max()))
                rall_max = max(rall_max, float(np.abs(((r[i] > 0) == (T > 0)).mean((-2, -1)) - Z[(b, u_, k)][f"{run}/r_all"][RI, i]).max()))
                n_checked += 1
            ref = run if "vote" in arms else run.replace("@1", "@0")
            if ref not in RUNS or "vote" not in RUNS[ref]:
                continue
            rv, rbv = raw[f"{ref}/r"][RUNS[ref].index("vote")], raw[f"{ref}/rB"][0]      # the vote's rB row comes first
            assert m["parts"][ref][0] == ["vote"]
            rb_arms = [x for x in m["parts"][run][0] if x == "vote"] + m["parts"][run][2]
            rB = raw[f"{run}/rB"]
            for a in [x for x in arms if x != "vote"]:
                ia, never = arms.index(a), Z[(b, u_, k)][f"{run}/det_on"][arms.index(a)] < 0
                for j in np.flatnonzero(never):
                    same_n += 1
                    same_bad += int(not (np.array_equal(r[ia, j], rv[j]) and np.array_equal(rB[rb_arms.index(a), j], rbv[j])))
say(f"\n4. FROM THE RAW FINAL STATES (the lead's own scoring; the patch from be001.sim.patch): r_in and r_all recomputed "
    f"from the final records, {n_checked} arm-runs x 8 cases: largest difference {rin_max:.2e} and {rall_max:.2e}; a "
    f"vote-default arm that never fired against the vote (at sigma 1 the vote's sigma-0 run, where it exists), both "
    f"records, bit for bit: {same_n - same_bad} of {same_n} lineage-cases equal")
assert rin_max <= 1e-12 and rall_max <= 1e-12 and same_bad == 0

name = f"p53c_ar005_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
