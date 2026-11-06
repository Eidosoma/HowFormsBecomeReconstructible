"""P56c (python probes/p56c_e2e001_lead_check.py ROOT): the lead's check of E2E001, the first end-to-end test.
LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved successor states and of the restored AR005 records,
written by the lead in reviewing E2E001's phase A and committed before the freeze, dry-run first on P56 (AR005's P53
records, engineering blocks 900729, 900739 | 900749, 900759, one future); 3 November 2026; no simulation.

It checks, from PLAN_E2E001.md's words (with its Amendment 1) and not from e2e001.sim, e2e001.predict or e2e001.checks:
1. integrity: every stage file against its manifest by sha256, and every restored record against its own run's manifest;
   the acquisition rebuilt by ar001.sim.prepare equal to the record's V0, R0 and T;
2. the packets at generation 0, rebuilt by the lead from the restored files and the frozen functions: each policy arm's
   first record (its r, H, W in its run, the vote's sigma-0 run for the vote under misreads); protected storage (R0 with
   its bonds, lr001.sim.edges_from(msegrid.core.bonds(R0, True))); post-damage copying (ar001.sim.event's record at
   sigma 0). Every label's generation-0 endpoints, scored by the lead (below) with the arm's final body for a policy
   arm and the pre-injury body otherwise, must equal the stage's;
3. the successors: every endpoint at every saved horizon (1, 3, 8) re-scored by the lead from the saved successor
   states (V, r) and compared with the stage's;
4. the parts E1-E9 by the plan's words: pooled per case over the eight unit-body pairs and the futures, a block the mean
   of its 8 cases, the part the mean over the blocks; SD = max(block SD, case SD / sqrt 8); the 95% t interval; on P56
   the margins (>= 3 sqrt(1/4 + 1/16)), both halves and the narrowest round thresholds (0.01 steps, 0.005 within 0.01 of
   zero); "at least" registers only above 0, "at most" only at 0.05 or less.

The lead's scoring (the plan's endpoints): s = +1 where dl001.sim.sign(x, T) >= 0.5, else -1; u_r = lr005.sim.inside(s r,
T, m) with m the record's own 4 x 4 patch (be001.sim.patch under its tag); u_v the same for the body; u_r_raw without s;
a = max(sign, 1 - sign); q = (a - max over SR001's foreign placements of a) / 0.25; agree_in the agreement of V and r
inside the patch.
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
from ar001 import sim as A1S                                    # noqa: E402  (frozen: prepare, event)
from ar001 import design as A5D                                 # noqa: E402  (frozen: parse_unit)
from be001 import sim as B1S                                    # noqa: E402  (frozen: the patch)
from dl001 import sim as S                                      # noqa: E402  (frozen: sign)
from lr001.sim import edges_from                                # noqa: E402  (frozen)
from lr005 import sim as L5S                                    # noqa: E402  (frozen: inside)
from msegrid.core import bonds                                  # noqa: E402  (frozen)
from sr001 import sim as SRS                                    # noqa: E402  (frozen: the foreign placements)

ROOT = Path(sys.argv[1])
RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
key = lambda s: s.replace("/", "_")

M = json.load(open(ROOT / "manifest.json"))
STAGE = M["stage"]
WANT = {"probe": ("ar005/p53", [900729, 900739, 900749, 900759]), "debug": ("ar005/debug", [900799]),
        "preflight": ("ar005/preflight", [900779, 900789]),
        "development": ("ar005/development", [910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785,
                                              910786, 910787, 910798, 910799, 910826, 910827, 910958])}
SRC, BLOCKS = WANT[STAGE]
SROOT = RUNS / SRC
NB = len(BLOCKS)
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert not bad, bad[:5]
assert len(M["tasks"]) == len(PAIRS) * NB, len(M["tasks"])
SM = json.load(open(SROOT / "manifest.json"))
if STAGE == "development":
    fz = json.load(open(LANE / "e2e001" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"


def orient(x, T):
    return np.where(S.sign(x, T) >= 0.5, 1.0, -1.0)[:, None, None]


inv = lambda a: np.maximum(a, 1 - a)


def score(V, r, T, Tf, m):
    a_r, a_v = inv(S.sign(r, T)), inv(S.sign(V, T))
    return {"u_r": L5S.inside(orient(r, T) * r, T, m), "u_v": L5S.inside(orient(V, T) * V, T, m),
            "u_r_raw": L5S.inside(r, T, m), "a_r": a_r, "a_v": a_v,
            "q_r": (a_r - np.max([inv(S.sign(r, t)) for t in Tf], axis=0)) / 0.25,
            "q_v": (a_v - np.max([inv(S.sign(V, t)) for t in Tf], axis=0)) / 0.25,
            "agree_in": (((V > 0) == (r > 0)) & m).sum((-2, -1)) / m.sum((-2, -1))}


ENDS = ("u_r", "u_v", "u_r_raw", "a_r", "a_v", "q_r", "q_v", "agree_in")
LABELS = None
VAL = {}                     # (label, endpoint, g) -> (blocks, pairs, futures, cases)
ROWS = {}                    # (block, pair) -> {label: row}: the aliases (the extension below)
d0 = dg = 0.0
n_pk = nraw = 0
for pi, (body, unit) in enumerate(PAIRS):
    for bi, blk in enumerate(BLOCKS):
        z = np.load(ROOT / "shards" / key(SRC) / body / unit / f"{blk}.npz")
        zr = np.load(ROOT / "raw" / key(SRC) / body / unit / f"{blk}.npz")
        meta = json.loads(str(z["__meta__"]))
        assert meta["source"] == SRC and meta["body"] == body and meta["unit"] == unit and int(meta["block"]) == blk
        f_src = SM["tasks"][f"{body}/{unit}/{blk}"]["files"]["raw"]
        assert sha(SROOT / f_src["path"]) == f_src["sha256"]
        nraw += 1
        raw = np.load(SROOT / f_src["path"])
        rmeta = json.loads(str(raw["__meta__"]))
        pattern, theta = A5D.parse_unit(unit)
        purpose = "development" if STAGE == "development" else "engineering"
        cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, purpose)
        assert np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"]) and np.array_equal(T, raw["T"])
        tag = rmeta["tag"]
        m = B1S.patch(cases, 4, tag)
        Tf = SRS.foreign(T, pattern, cases)
        arms_of = {name: list(a) for name, a in rmeta["runs"]}
        H0, W0 = edges_from(bonds(R0, True))
        labels = meta["labels"]
        if LABELS is None:
            LABELS = sorted(labels)
        assert sorted(labels) == LABELS
        # 2. the packets and generation 0
        for lab, row in labels.items():
            parts = lab.split("/")
            if parts[0] in ("vote", "vms", "vguard"):
                arm, sit = parts
                src = sit if arm in arms_of.get(sit, []) else sit.replace("@1", "@0")
                j = arms_of[src].index(arm)
                pk = (raw[f"{src}/H"][j], raw[f"{src}/W"][j], raw[f"{src}/r"][j])
                Vb = raw[f"{src}/V"][j]
            elif lab == "protected":
                pk, Vb = (H0, W0, R0), V0
            elif parts[0] == "post":
                base = parts[1].split("@")[0]
                if base in ("memory", "correlated"):
                    ev = A1S.event(base, 4, 0.0, cases, V0, ema0, R0, T, tag)
                    pk = (ev["H"], ev["W"], ev["r"])
                    assert np.array_equal(ev["m"], m)
                else:
                    pk = (H0, W0, R0)
                Vb = V0
            else:
                continue                          # the controls (foreign, noread, unint, Q): their successors only
            sc = score(np.asarray(Vb, float), np.asarray(pk[2], float), T, Tf, m)
            for e in ENDS:
                d0 = max(d0, float(np.abs(sc[e] - z[f"g0/{e}"][row]).max()))
            n_pk += 1
        # 3. the successors at every saved horizon, every future
        nf = meta["futures"]
        for f in range(nf):
            for g in (1, 3, 8):
                rows = list(z[f"f{f}/g{g}/rows"])
                n = len(rows)
                Vg = zr[f"f{f}/g{g}/V"].reshape(n, len(cases), *T.shape[1:])
                rg = zr[f"f{f}/g{g}/r"].reshape(n, len(cases), *T.shape[1:])
                for p in range(n):
                    sc = score(Vg[p], rg[p], T, Tf, m)
                    for e in ENDS:
                        dg = max(dg, float(np.abs(sc[e] - z[f"f{f}/g{g}/{e}"][p]).max()))
        # the values by label
        ROWS[(bi, pi)] = dict(labels)
        for lab, row in labels.items():
            for e in ENDS:
                VAL.setdefault((lab, e, 0), np.full((NB, len(PAIRS), 1, 8), np.nan))[bi, pi, 0] = z[f"g0/{e}"][row]
                for g in (1, 3, 8):
                    for f in range(nf):
                        rows = list(z[f"f{f}/g{g}/rows"])
                        arr = VAL.setdefault((lab, e, g), np.full((NB, len(PAIRS), nf, 8), np.nan))
                        if row in rows:
                            arr[bi, pi, f] = z[f"f{f}/g{g}/{e}"][rows.index(row)]
say(f"P56c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {len(M['tasks'])} "
    f"tasks, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; {M['started_utc']} - "
    f"{M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h; {nraw} restored records, every sha256 equal to {SRC}'s "
    f"manifest; the acquisition rebuilt by ar001.sim.prepare equal to every record's V0, R0 and T")
say(f"  the packets at generation 0 rebuilt by the lead ({n_pk} label-tasks; the policy arms from their runs, protected "
    f"storage from R0, post-damage copying from ar001.sim.event): every endpoint equal to the stage's within {d0:.1e}")
say(f"  the successors re-scored by the lead from the saved states at horizons 1, 3 and 8: largest |difference| {dg:.1e}")
assert d0 < 1e-12 and dg < 1e-12


def X(lab, e, g):
    """(blocks, cases): the mean over the pairs and the futures the label's row ran in. Under the lead's trim (13:45Z)
    the second future runs on the main rows only, so a side row has one future; a future is used for a label only if
    the row ran in it in every task, and a row may not be present in some tasks of a future and absent in others."""
    a = VAL[(lab, e, g)]
    full = [f for f in range(a.shape[2]) if not np.isnan(a[:, :, f]).any()]
    gone = [f for f in range(a.shape[2]) if np.isnan(a[:, :, f]).all()]
    assert full and len(full) + len(gone) == a.shape[2], (lab, e, g, full, gone)
    return a[:, :, full].mean(axis=(1, 2))


K = 3 * math.sqrt(1 / 4 + 1 / 16)
T975 = stats.t.ppf(0.975, NB - 1) if NB > 1 else float("nan")


def est(x):
    blk = x.mean(1)
    v = float(blk.mean())
    sdc = float(x.ravel().std(ddof=1)) / math.sqrt(x.shape[1])
    sdb = float(blk.std(ddof=1)) if NB > 1 else float("nan")
    sd = max(sdb, sdc) if NB > 1 else sdc
    h = T975 * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean())) if NB > 1 else (v, v)}


def narrow_num(q):
    lo_raw, hi_raw = min(q["v"] - K * q["sd"], *q["halves"]), max(q["v"] + K * q["sd"], *q["halves"])
    st = lambda raw: 0.005 if abs(raw) <= 0.01 else 0.01
    lo = math.floor(round(lo_raw / st(lo_raw), 9)) * st(lo_raw)
    hi = math.ceil(round(hi_raw / st(hi_raw), 9)) * st(hi_raw)
    return round(lo, 3), round(hi, 3)


def narrow(q, kind):
    lo, hi = narrow_num(q)
    if kind == "band":
        return f"[{lo:+.3f}, {hi:+.3f}]"
    if kind == "least":
        return f">= {lo:+.3f}: " + ("registers" if lo > 0 else "NOT above 0: reported")
    return f"<= {hi:+.3f}: " + ("registers" if hi <= 0.05 else "above 0.05: reported")


# the registration's thresholds as the lead ruled on phase A (REGISTRATION_E2E001.md); E7 reported; E8 the confirmed
# no-event bound 0.002 (AR005's K2a), fixed, since P56's E8 is exactly 0 with SD 0 (the lead's ruling, about 13:50Z)
TH = {"E1": ("least", 0.20), "E2": ("least", 0.08), "E3": ("least", 0.07), "E4": ("band", (-0.35, -0.15)),
      "E5": ("band", (0.005, 0.18)), "E6": ("least", 0.15), "E8": ("most", 0.002), "E9": ("least", 0.18)}
FIXED = {"E8"}
if STAGE == "development":
    PRZ = json.load(open(LANE / "e2e001" / "frozen" / "predictions.json"))
    got = {x["id"]: (tuple(x["threshold"]) if isinstance(x["threshold"], list) else float(x["threshold"])) for x in PRZ["registered"]}
    assert got == {k: v[1] for k, v in TH.items()} and PRZ["design_digest"] == M["design_digest"], ("the frozen thresholds differ", got)


D = lambda A, g, sit="memory@0": X(f"{A}/{sit}", "u_r", g) - X(f"vote/{sit}", "u_r", g)
PARTS = [
    ("E1", "Delta_vguard(1): the repair crosses the first renewal", D("vguard", 1), "least"),
    ("E2", "Delta_vguard(8): it lasts eight renewals", D("vguard", 8), "least"),
    ("E3", "Delta_vms(8): the confirmed controller's", D("vms", 8), "least"),
    ("E4", "Delta_vguard(8) - Delta_vguard(0): the advantage's change through renewal", D("vguard", 8) - D("vguard", 0), "band"),
    ("E5", "u_r(protected, 8) - u_r(vguard, memory@0, 8): protected storage's lead",
     X("protected", "u_r", 8) - X("vguard/memory@0", "u_r", 8), "band"),
    ("E6", "u_r(vguard, memory@0, 8) - u_r(post-damage, memory@0, 8)",
     X("vguard/memory@0", "u_r", 8) - X("post/memory@0", "u_r", 8), "least"),
    ("E7", "u_r(vguard, memory@1, 8) - u_r(vms, memory@1, 8): the misread recovery after renewal",
     X("vguard/memory@1", "u_r", 8) - X("vms/memory@1", "u_r", 8), "least"),
    ("E8", "a_r(vote, none@0, 8) - a_r(vguard, none@0, 8): the no-event cost in later generations",
     X("vote/none@0", "a_r", 8) - X("vguard/none@0", "a_r", 8), "most"),
    ("E9", "u_v(vguard, memory@0, 1) - u_v(vote, memory@0, 1): the first successor's own reconstruction",
     X("vguard/memory@0", "u_v", 1) - X("vote/memory@0", "u_v", 1), "least")]
say(f"\nTHE PARTS ({NB} blocks x 8 cases; pooled over the eight unit-body pairs and the futures; [95% t interval]"
    + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
for pid, words, x, kind in PARTS:
    q = est(x)
    line = (f"  {pid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}; halves "
            f"{q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
    if STAGE == "probe":
        line += f"; the narrowest {narrow(q, kind)}"
        if pid in TH and pid not in FIXED:
            lo, hi = narrow_num(q)
            want = TH[pid][1]
            assert (lo, hi) == tuple(want) if kind == "band" else abs((lo if kind == "least" else hi) - want) < 1e-9, (pid, lo, hi, want)
    if pid in TH:
        kd, th = TH[pid]
        ok = (th[0] <= q["v"] <= th[1]) if kd == "band" else (q["v"] >= th if kd == "least" else q["v"] <= th)
        line += f"; registered {th if kd == 'band' else ('>= ' if kd == 'least' else '<= ') + str(th)}: {'HOLDS' if ok else 'FAILS'}"
    else:
        line += "; reported"
    say(line)

say("\nREPORTED (the lead's)")
for sit in ("memory@0", "memory@1", "none@0", "cue@0", "correlated@0"):
    for g in (0, 1, 3, 8):
        labs = [l for l in ("protected", f"post/{sit}", f"vote/{sit}", f"vms/{sit}", f"vguard/{sit}") if (l, "u_r", g) in VAL]
        vals = []
        for l in labs:
            try:
                vals.append(f"{l.split('/')[0]} {X(l, 'u_r', g).mean():.4f}")
            except AssertionError:
                vals.append(f"{l.split('/')[0]} (not run to {g})")
        say(f"  u_r {sit:12s} g {g}: " + "; ".join(vals))
for g in (1, 3):
    say(f"  controls at g {g}: own protected {X('protected', 'u_r', g).mean():.4f}, foreign protected "
        f"{X('foreign/protected', 'u_r', g).mean():.4f}, no reading {X('noread/protected', 'u_r', g).mean():.4f}; "
        f"q_r own {X('protected', 'q_r', g).mean():+.4f}, foreign {X('foreign/protected', 'q_r', g).mean():+.4f}")

# ---------- the reported parts, paired within futures (the lead's extension; written after the development's values,
# 3 November 2026 about 17:25Z; not registered and changing no verdict). Under the trim (13:45Z) a side row runs in the
# first future only, and a label aliased to a main row in one task may have its own side row in another. So, per task, a
# contrast is the mean over the futures in which every term with g > 0 ran its row (a generation-0 term enters every
# future alike), and a level is the mean over the futures that ran its row; then pooled as the parts. The definitions are
# the registration's part names (e2e001/frozen/predictions.json "reported"), written out here by the lead.
SETS = {"native (li4 x S4)": {("li4", "S4_t0"), ("li4", "S4_t1")},
        "particular (li4 x F0)": {("li4", "F0_t0"), ("li4", "F0_t1")},
        "permissive (dw)": {("dw", u) for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")}}


def lin_bc(terms, subset=None, partial=False):
    """(blocks, cases): sum of c x endpoint over terms (c, label, e, g), paired within each task's futures. partial=True
    mirrors the frozen reader's levels: a task where some term ran in no future is skipped, and a block with no task
    left is dropped (returns (block values, the tasks used))."""
    res = np.full((NB, 8), np.nan)
    used = 0
    for bi in range(NB):
        acc = []
        for pi, pair in enumerate(PAIRS):
            if subset is not None and pair not in subset:
                continue
            futs = None
            for _c, lab, e, g in terms:
                if g == 0:
                    continue
                a = VAL[(lab, e, g)][bi, pi]                       # (futures, cases)
                ok = {f for f in range(a.shape[0]) if not np.isnan(a[f]).any()}
                assert all(np.isnan(a[f]).all() for f in range(a.shape[0]) if f not in ok), (lab, e, g, bi, pi)
                futs = ok if futs is None else futs & ok
            if partial and futs is not None and not futs:
                continue
            assert futs is None or futs, ("no future ran every term", terms, bi, pi)
            used += 1
            vals = [sum(c * (VAL[(lab, e, g)][bi, pi, 0] if g == 0 else VAL[(lab, e, g)][bi, pi, f])
                        for c, lab, e, g in terms) for f in (sorted(futs) if futs is not None else [None])]
            acc.append(np.mean(vals, axis=0))
        if acc:
            res[bi] = np.mean(acc, axis=0)
    if partial:
        return res[~np.isnan(res).any(axis=1)], used
    assert not np.isnan(res).any(), terms
    return res


def d_(a, b, e, g):
    return [(1.0, a, e, g), (-1.0, b, e, g)]


REP = {f"R-vms-{g}": d_("vms/memory@0", "vote/memory@0", "u_r", g) for g in (0, 1, 3, 8)}
REP["R-mismatch0"] = d_("vote/memory@0", "vguard/memory@0", "agree_in", 0)    # (1 - agree(vguard)) - (1 - agree(vote))
for g in (1, 3):
    REP[f"R-own-foreign-q-{g}"] = d_("protected", "foreign/protected", "q_r", g)
    REP[f"R-own-foreign-u-{g}"] = d_("vguard/memory@0", "foreign/vguard/memory@0", "u_r", g)
    REP[f"R-noread-q-{g}"] = d_("protected", "noread/protected", "q_r", g)
    for arm in ("vote", "vms", "vguard"):
        REP[f"R-unint-{arm}-{g}"] = d_(f"unint/{arm}/memory@0", f"{arm}/memory@0", "u_r", g)
        REP[f"R-Q-{arm}-{g}"] = d_(f"Q/{arm}/memory@0", f"{arm}/memory@0", "u_r", g)
REP["R-protected-q-8"] = [(1.0, "protected", "q_r", 8)]
REP["R-protected-noread-q-3"] = [(1.0, "noread/protected", "q_r", 3)]
for sit in ("cue@0", "correlated@0"):
    for g in (1, 3):
        REP[f"R-{sit}-{g}"] = d_(f"vguard/{sit}", f"vote/{sit}", "u_r", g)
REP["R-E7-at-0"] = d_("vguard/memory@1", "vms/memory@1", "u_r", 0)
REGT = {"E1": d_("vguard/memory@0", "vote/memory@0", "u_r", 1), "E2": d_("vguard/memory@0", "vote/memory@0", "u_r", 8),
        "E3": d_("vms/memory@0", "vote/memory@0", "u_r", 8),
        "E4": d_("vguard/memory@0", "vote/memory@0", "u_r", 8) + [(-1.0, "vguard/memory@0", "u_r", 0),
                                                                    (1.0, "vote/memory@0", "u_r", 0)],
        "E5": d_("protected", "vguard/memory@0", "u_r", 8), "E6": d_("vguard/memory@0", "post/memory@0", "u_r", 8),
        "E7": d_("vguard/memory@1", "vms/memory@1", "u_r", 8), "E8": d_("vote/none@0", "vguard/none@0", "a_r", 8),
        "E9": d_("vguard/memory@0", "vote/memory@0", "u_v", 1)}
if STAGE == "development":
    want_ids = [r["id"] for r in PRZ["reported"]]
    assert sorted(want_ids) == sorted(REP), (sorted(set(want_ids) ^ set(REP)))
say()
say("REPORTED PARTS, paired within futures (the lead's extension after the development's values; by item set)")
MINE = {}
for pid, terms in list(REGT.items()) + list(REP.items()):
    r = est(lin_bc(terms))
    r["sets"] = {k: float(lin_bc(terms, sub).mean()) for k, sub in SETS.items()}
    MINE[pid] = r
    say(f"  {pid:24s} {r['v']:+.6f} [{r['lo']:+.6f}, {r['hi']:+.6f}] (SD {r['sd']:.6f}; halves {r['halves'][0]:+.6f} "
        f"{r['halves'][1]:+.6f}); " + "; ".join(f"{k.split()[0]} {v:+.4f}" for k, v in r["sets"].items()))
say("  levels, the mean over the futures that ran the row in each task (u_r):")
for sit in ("memory@0", "memory@1", "none@0", "cue@0", "correlated@0"):
    for g in (1, 3, 8):
        vals = []
        for lab in ("protected", f"post/{sit}", f"vote/{sit}", f"vms/{sit}", f"vguard/{sit}"):
            try:
                vals.append(f"{lab.split('/')[0]} {lin_bc([(1.0, lab, 'u_r', g)]).mean():.4f}")
            except AssertionError:
                vals.append(f"{lab.split('/')[0]} (not run to {g})")
        say(f"    {sit:12s} g {g}: " + "; ".join(vals))
for lab in ("foreign/protected", "foreign/vguard/memory@0", "noread/protected", "unint/vote/memory@0",
            "unint/vms/memory@0", "unint/vguard/memory@0", "Q/vote/memory@0", "Q/vms/memory@0", "Q/vguard/memory@0"):
    say(f"    {lab:24s} u_r g 1 {lin_bc([(1.0, lab, 'u_r', 1)]).mean():.4f}, g 3 {lin_bc([(1.0, lab, 'u_r', 3)]).mean():.4f};"
        f" q_r g 1 {lin_bc([(1.0, lab, 'q_r', 1)]).mean():+.4f}, g 3 {lin_bc([(1.0, lab, 'q_r', 3)]).mean():+.4f}")
spread = {}
for lab in ("protected", "vote/memory@0", "vms/memory@0", "vguard/memory@0", "post/memory@0"):
    a = VAL[(lab, "u_r", 8)]                                       # (blocks, pairs, futures, cases)
    if a.shape[2] > 1 and not np.isnan(a).any():
        spread[lab] = float(a.std(axis=2, ddof=1).mean())
own = sum(ROWS[k]["vguard/none@0"] != ROWS[k]["vote/none@0"] for k in ROWS)
e8 = (VAL[("vote/none@0", "a_r", 8)] - VAL[("vguard/none@0", "a_r", 8)]).mean(axis=2)     # (blocks, pairs, cases)
say(f"  E8's rows: vguard's none@0 packet its own (not the vote's) in {own} of {len(ROWS)} tasks; a_r(vote) - a_r(vguard) "
    f"at g 8 nonzero in {int((e8 != 0).sum())} of {e8.size} cases (mean over the futures), largest |difference| "
    f"{float(np.abs(e8).max()):.4f}")
_, n_cue8 = lin_bc([(1.0, "vguard/cue@0", "u_r", 8)], partial=True)
say(f"  vguard/cue@0 at g 8 exists in {n_cue8} of {len(ROWS)} tasks (where its packet is the vote's and rides a main row)")
say("  the futures' spread at g 8 (the SD of u_r across the futures per case, ddof 1, the mean): "
    + "; ".join(f"{k} {v:.4f}" for k, v in spread.items()))
SCORED = LANE / "results" / "e2e001" / "predictions_scored.json"
if STAGE == "development" and SCORED.exists():
    fr = json.load(open(SCORED))
    assert fr["design_digest"] == M["design_digest"]
    worst = {"value": 0.0, "interval": 0.0, "halves": 0.0, "sets": 0.0}
    for r in fr["parts"] + fr["reported"]:
        mi = MINE[r["id"]]
        worst["value"] = max(worst["value"], abs(mi["v"] - r["value"]))
        worst["interval"] = max(worst["interval"], abs(mi["lo"] - r["ci95"][0]), abs(mi["hi"] - r["ci95"][1]))
        worst["halves"] = max(worst["halves"], *(abs(a - b) for a, b in zip(mi["halves"], r["halves"])))
        fs = {k: (v["value"] if isinstance(v, dict) else v) for k, v in r["by_item_set"].items()}
        for k, sub in zip(("native", "particular", "permissive"), SETS):
            worst["sets"] = max(worst["sets"], abs(mi["sets"][sub] - fs[k]))
    nlev = dlev = 0
    part_lv = set()
    for k, v in fr["levels"].items():
        lab, e, g = k.split("|")
        for sk, sub in (("all", None),) + tuple(zip(("native", "particular", "permissive"), SETS.values())):
            x = v.get(sk)
            xm, used = lin_bc([(1.0, lab, e, int(g))], sub, partial=True)
            if x is None:
                assert used == 0, (k, sk, used)
                continue
            dlev = max(dlev, abs(float(xm.mean()) - x))
            nlev += 1
            if used < NB * len(PAIRS if sub is None else sub):
                part_lv.add(f"{lab} g {g}")
    dsp = max(abs(spread[k] - v) for k, v in fr["futures_spread"].items()) if fr["futures_spread"] else float("nan")
    say(f"  AGAINST THE FROZEN READER (results/e2e001/predictions_scored.json; {len(fr['parts'])} parts, "
        f"{len(fr['reported'])} reported, {nlev} levels): largest |difference| value {worst['value']:.1e}, interval "
        f"{worst['interval']:.1e}, halves {worst['halves']:.1e}, item sets {worst['sets']:.1e}; levels {dlev:.1e}; "
        f"the futures' spread {dsp:.1e}")
    say(f"  the frozen reader's levels over only some tasks (a side label aliased to a main row in some tasks and run "
        f"to g 3 in the rest; not a level, used by no part): {sorted(part_lv)}")
    assert max(worst.values()) < 1e-9 and dlev < 1e-9, (worst, dlev)

name = f"p56c_e2e001_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
