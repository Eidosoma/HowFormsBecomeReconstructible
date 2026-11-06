"""P66c (python probes/p66c_e2e007_lead_check.py ROOT [ROOT ...] [--reader READER]): the lead's check of E2E007, the
response's sign and the injury's target. LEAD_CHECK_NOT_REGISTERED; a read of the stages' shards and saved successor states
and of the restored AR006 records, written by the lead in reviewing E2E007's phase A and committed before the freeze,
dry-run first on P66 (AR006's P57 records 900917 | 900919, all eight cases, one future) and on the debug run (900948,
rows to generation 3); 5-6 November 2026; no simulation of the tissue or of the field. Adapted from P63c (E2E006), whose
integrity, schedule, packet, re-scoring and field identities it keeps.

It checks, from PLAN_E2E007.md's words (with its amendments) and not from e2e007, e2e006, e2e003, e2e002 or msefield:
1. integrity: every stage file and restored record by sha256; the acquisition rebuilt; at development the frozen digest;
   every label's row (policy, the injury's target, the response, field, medium, window) against the plan's table;
2. the injury schedule recomputed (E2E003's rule under the stage's tag), the same patches for both targets;
3. the packets at generation 0 rebuilt and scored; every successor endpoint at every saved horizon re-scored from the saved
   states (own patch, union, whole sheet); every fresh successor re-scored from its saved final state;
4. the identities: no vote row fires; every injury check holds (the memory flip on memory rows, the body flip on body
   rows); a field-free row's exposures are exactly 0; every field branch's recorded response equals its kappa x its
   mean exposure (raise and relax at E2E006's kappa 1.944, the size-matched relax at its declared kappa');
5. the parts by the registration's words (pooled per case over the eight pairs, blocks of 8 cases, SD = max(block SD,
   case SD / sqrt(8)), the 95% t interval) against the registered thresholds; on P66 the narrowest thresholds the rule
   allows, which must equal the registered ones;
6. reported: the size-matched relax row's contrasts; q_r under body injury and the q_r interaction; the observer's
   healing curve; the exposures; with READER, the frozen reader's values.
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
from ar001 import design as A1D                                 # noqa: E402  (frozen: parse_unit)
from ar001 import sim as A1S                                    # noqa: E402  (frozen: prepare)
from be001 import sim as B1S                                    # noqa: E402  (frozen: the patch)
from dl001 import sim as S                                      # noqa: E402  (frozen: sign)
from lr001.sim import edges_from                                # noqa: E402  (frozen)
from lr005 import sim as L5S                                    # noqa: E402  (frozen: inside)
from mse.native import address                                  # noqa: E402  (frozen engine: the addressed streams)
from msegrid.core import bonds                                  # noqa: E402  (frozen)
from sr001 import sim as SRS                                    # noqa: E402  (frozen: the foreign placements)

args = sys.argv[1:]
READER = None
if "--reader" in args:
    i = args.index("--reader")
    READER = Path(args[i + 1])
    args = args[:i] + args[i + 2:]
ROOTS = [Path(a) for a in args]
RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
key = lambda s: s.replace("/", "_")

MS = [json.load(open(r / "manifest.json")) for r in ROOTS]
STAGE = MS[0]["stage"]
PROBE_STAGES = ("probe", "probe_x")                             # P66's six rows and P66x's matched row (Amendment 1)
assert all((m_["stage"] == STAGE) or (STAGE in PROBE_STAGES and m_["stage"] in PROBE_STAGES) for m_ in MS)
SKEY = "probe" if STAGE in PROBE_STAGES else STAGE
AR006_DEV = [925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621, 925622, 925624, 925626, 925627, 925628,
             925630, 925633, 925634]
# stage -> (restored source, blocks, the successors' tag, parents read, the blocks' enrolment purpose)
WANT = {"probe": ("ar006/p57", [900917, 900919], "mse-p66", (0, 1), "engineering"),
        "debug": ("ar006/debug", [900948], "mse-e2e007", (0, 1), "engineering"),
        "preflight": ("ar006/preflight", [900929], "mse-e2e007", (0, 1), "engineering"),
        "development": ("ar006/development", AR006_DEV, "mse-e2e007", (0, 1), "confirmation")}
SRC, BLOCKS, FTAG, PARENTS, PURPOSE = WANT[SKEY]
SROOT = RUNS / SRC
NB = len(BLOCKS)
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
for r_, m_ in zip(ROOTS, MS):
    bad = [f["path"] for t in m_["tasks"].values() for f in t["files"].values() if sha(r_ / f["path"]) != f["sha256"]]
    assert m_["study"] == "E2E007" and not bad, (r_, bad[:5])
    assert len(m_["tasks"]) == len(PAIRS) * NB, (r_, len(m_["tasks"]))
DIGESTS = [m_["design_digest"] for m_ in MS]
# at the probe stage P63 ran under phase A's design and P63x under Amendment 2's (nothing that feeds the states changed:
# the fork's P63e, the shared row alone equal to P63's bit for bit); the lead checks the pairing it can see: the same tag,
# cases and injury schedule in every root, task by task. Every other stage is one run under one design.
assert SKEY == "probe" or len(set(DIGESTS)) == 1, "the roots ran under different designs"
SM = json.load(open(SROOT / "manifest.json"))
if STAGE == "development":
    fz = json.load(open(LANE / "e2e007" / "frozen" / "design.json"))
    assert fz["digest"] == MS[0]["design_digest"], "the run is not under the frozen design"
# the plan's lineage table: label -> (generation-0 packet, policy, the injury's target, the response, field, medium, window)
PLAN = {f"{resp}/{tgt}": ("vote/memory@0", "vote", tgt, resp, "none" if resp == "none" else "shared",
                          "-" if resp == "none" else "reset", "-" if resp == "none" else "full")
        for resp in ("none", "raise", "relax") for tgt in ("memory", "body")}
PLAN["relax-matched/memory"] = ("vote/memory@0", "vote", "memory", "relax", "shared", "reset", "full")
KAPPA = 1.944                          # E2E006's frozen kappa (P63k's rule), reused and declared
# the size-matched relax's kappa' (Amendment 1): the declared closed-loop rule on the debug record (P66k): the root of the
# quadratic through the three trials' pooled integrated kappa' x, at raise/memory's, rounded to four significant figures
P66K = json.load(open(LANE / "probes" / "results" / "p66k_e2e007_kappa.json")) if (LANE / "probes" / "results" / "p66k_e2e007_kappa.json").exists() else None
KAPPA_MATCHED = 1.4
G = 8
SIDE, SIZE = 32, 4
T_GEN = 8000

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


OWN = ("u_r", "u_v", "u_r_raw", "agree_in")                       # on the generation's own patch
SHEET = ("a_r", "a_v", "q_r", "q_v")                              # whole-sheet
UNION = {"U": "u_r", "U_v": "u_v", "U_raw": "u_r_raw", "agree_U": "agree_in"}
ENDS = OWN + SHEET + tuple(UNION)
FRESH_ENDS = SHEET + tuple(UNION)


def schedule_lead(cases, m0, tag, gens):
    """E2E003's rule, written by the lead (P59c): {g: (k, side, side)}, corners (k, gens, 2), attempts (k, gens)."""
    k = len(cases)
    sch = {g: np.zeros((k, SIDE, SIDE), bool) for g in range(1, gens + 1)}
    corners, attempts = np.zeros((k, gens, 2), np.int64), np.zeros((k, gens), np.int64)
    for j, c in enumerate(cases):
        used = m0[j].copy()
        for g in range(1, gens + 1):
            att = 0
            while True:
                a, b = address(tag, *c.key(), "e2e003", "injury", g, att).integers(0, SIDE, 2)
                p = np.zeros((SIDE, SIDE), bool)
                p[np.ix_((a + np.arange(SIZE)) % SIDE, (b + np.arange(SIZE)) % SIDE)] = True
                if not (p & used).any():
                    break
                att += 1
            sch[g][j], corners[j, g - 1], attempts[j, g - 1] = p, (a, b), att
            used |= p
    return sch, corners, attempts


LABELS, KC = set(), None
VAL = {}                     # (label, endpoint, g) -> (blocks, pairs, cases); fresh reads under ("x:" + label, e, g)
EXPO = {}                    # (label, quantity, g) -> (blocks, pairs, cases)
OBS = {}                     # (label, the observer's read, g) -> (blocks, pairs, cases): the patch's agreement around the flip
ROWINFO, SCHED = {}, {}
d0 = dg = dx = 0.0
n_pk = nraw = n_sched = n_states = n_fresh = 0
max_att = 0
idn = {"vote_never": [0, 0], "birth_cue_agrees": [0, 0], "injury_ok": [0, 0], "ceiling_uninjured": [0, 0],
       "fieldfree_zero": [0, 0], "kexp_window": [0, 0.0]}
for root, man in zip(ROOTS, MS):
    for pi, (body, unit) in enumerate(PAIRS):
        for bi, blk in enumerate(BLOCKS):
            z = np.load(root / "shards" / key(SRC) / body / unit / f"{blk}.npz")
            zr = np.load(root / "raw" / key(SRC) / body / unit / f"{blk}.npz")
            meta = json.loads(str(z["__meta__"]))
            assert meta["source"] == SRC and meta["body"] == body and meta["unit"] == unit and int(meta["block"]) == blk
            assert meta["tag"] == FTAG and meta["futures"] == 1, (meta["tag"], meta["futures"])
            f_src = SM["tasks"][f"{body}/{unit}/{blk}"]["files"]["raw"]
            assert sha(SROOT / f_src["path"]) == f_src["sha256"] == meta["rawfile"]["sha256"]
            nraw += 1
            raw = dict(np.load(SROOT / f_src["path"]))
            rmeta = json.loads(str(raw.pop("__meta__")))
            assert rmeta["tag"] == meta["record_tag"]
            pattern, theta = A1D.parse_unit(unit)
            cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, PURPOSE)
            sel = [j for j, c in enumerate(cases) if c.parent in PARENTS]
            cases = [cases[j] for j in sel]
            V0, R0, T = (x[sel] for x in (V0, R0, T))
            raw = {k_: (v[sel] if k_ in ("V0", "R0", "T") else v[:, sel]) for k_, v in raw.items()}
            assert [list(c.key()) for c in cases] == [list(c) for c in meta["cases"]]
            assert np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"]) and np.array_equal(T, raw["T"])
            k = len(cases)
            KC = k if KC is None else KC
            assert k == KC
            rtag = rmeta["tag"]
            m0 = B1S.patch(cases, SIZE, rtag)
            Tf = SRS.foreign(T, pattern, cases)
            arms_of = {name: list(a) for name, a in rmeta["runs"]}
            H0, W0 = edges_from(bonds(R0, True))
            labels = meta["labels"]
            rows = meta["rows"]
            for lab, row in labels.items():
                src, pol, tgt, resp, fld, med, win = PLAN[lab]
                rr = rows[row]
                assert meta["sources"][lab] == src and rr["policy"] == pol and bool(rr["injured"]), lab
                assert (rr["target"], rr["response"], rr["field"], rr["medium"], rr["window"]) == (tgt, resp, fld, med, win), (lab, rr)
                assert float(rr["sigma"]) == 0.0, lab
                ROWINFO[lab] = rr
                LABELS.add(lab)
            # 2. the schedule
            GS = int(z["schedule/corners"].shape[1])
            assert GS == max(int(r_["stop"]) for r_ in rows), GS
            sch, corners, attempts = schedule_lead(cases, m0, FTAG, GS)
            assert np.array_equal(corners, z["schedule/corners"]) and np.array_equal(attempts, z["schedule/attempts"])
            if (bi, pi) in SCHED:
                assert np.array_equal(SCHED[(bi, pi)], corners), "two roots, two schedules"
            SCHED[(bi, pi)] = corners
            allp = m0.astype(int) + sum(sch[g].astype(int) for g in range(1, GS + 1))
            assert allp.max() == 1 and (allp.sum((-2, -1)) == SIZE * SIZE * (GS + 1)).all(), "the patches are not disjoint"
            n_sched += k
            max_att = max(max_att, int(attempts.max()))
            union = {0: m0.copy()}
            for g in range(1, GS + 1):
                union[g] = union[g - 1] | sch[g]
            own = {0: m0, **sch}
            # 3. the packets at generation 0
            for lab, row in labels.items():
                src = meta["sources"][lab]
                if src == "protected":
                    pk, Vb = (H0, W0, R0), V0
                else:
                    arm, sit = src.split("/")
                    j = arms_of[sit].index(arm)
                    pk, Vb = (raw[f"{sit}/H"][j], raw[f"{sit}/W"][j], raw[f"{sit}/r"][j]), raw[f"{sit}/V"][j]
                sc = score(np.asarray(Vb, float), np.asarray(pk[2], float), T, Tf, m0)
                for e in OWN + SHEET:
                    d0 = max(d0, float(np.abs(sc[e] - z[f"g0/{e}"][row]).max()))
                    VAL.setdefault((lab, e, 0), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"g0/{e}"][row]
                for e, src_e in UNION.items():
                    d0 = max(d0, float(np.abs(sc[src_e] - z[f"g0/{e}"][row]).max()))
                    VAL.setdefault((lab, e, 0), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"g0/{e}"][row]
                n_pk += 1
            # the successors: every generation's reads; the saved states re-scored at the horizons
            for g in range(1, GS + 1):
                if f"f0/g{g}/rows" not in z.files:
                    continue
                rws = [int(x) for x in z[f"f0/g{g}/rows"]]
                for lab, row in labels.items():
                    if row in rws:
                        for e in ENDS:
                            VAL.setdefault((lab, e, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"f0/g{g}/{e}"][rws.index(row)]
                if f"f0/g{g}/V" in zr.files:
                    assert rws == [int(x) for x in zr[f"f0/g{g}/rows"]]
                    n = len(rws)
                    Vg = zr[f"f0/g{g}/V"].reshape(n, k, *T.shape[1:])
                    rg = zr[f"f0/g{g}/r"].reshape(n, k, *T.shape[1:])
                    for p in range(n):
                        so = score(Vg[p], rg[p], T, Tf, own[g])
                        su = score(Vg[p], rg[p], T, Tf, union[g])
                        for e in OWN + SHEET:
                            dg = max(dg, float(np.abs(so[e] - z[f"f0/g{g}/{e}"][p]).max()))
                        for e, src_e in UNION.items():
                            dg = max(dg, float(np.abs(su[src_e] - z[f"f0/g{g}/{e}"][p]).max()))
                        n_states += 1
                # the fresh successors after g: their reads; their saved final states re-scored where saved
                if f"f0/x{g}/rows" in z.files:
                    xr = [int(x) for x in z[f"f0/x{g}/rows"]]
                    for lab, row in labels.items():
                        if row in xr:
                            for e in FRESH_ENDS:
                                VAL.setdefault(("x:" + lab, e, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"f0/x{g}/{e}"][xr.index(row)]
                    if f"f0/x{g}/V" in zr.files:
                        assert xr == [int(x) for x in zr[f"f0/x{g}/rows"]]
                        n = len(xr)
                        Vx = zr[f"f0/x{g}/V"].reshape(n, k, *T.shape[1:])
                        rx = zr[f"f0/x{g}/r"].reshape(n, k, *T.shape[1:])
                        for p in range(n):
                            su = score(Vx[p], rx[p], T, Tf, union[g])
                            for e in SHEET:
                                dx = max(dx, float(np.abs(su[e] - z[f"f0/x{g}/{e}"][p]).max()))
                            for e, src_e in UNION.items():
                                dx = max(dx, float(np.abs(su[src_e] - z[f"f0/x{g}/{e}"][p]).max()))
                            n_fresh += 1
            # 4. the identities, from every generation's diagnostics
            gens = sorted(int(x.split("/")[1][1:]) for x in z.files if x.startswith("f0/d") and x.endswith("/rows"))
            for g in gens:
                rws = [int(x) for x in z[f"f0/d{g}/rows"]]
                for lab, row in labels.items():
                    if row not in rws:
                        continue
                    p = rws.index(row)
                    rr = rows[row]
                    fired = z[f"f0/d{g}/det_on"][p] >= 0
                    assert np.array_equal(fired, z[f"f0/d{g}/fired"][p] > 0), (lab, g)
                    if rr["policy"] == "vote":
                        idn["vote_never"][0] += k
                        idn["vote_never"][1] += int(fired.sum())
                    else:
                        idn["birth_cue_agrees"][0] += k
                        idn["birth_cue_agrees"][1] += int((z[f"f0/d{g}/cue_dis_birth"][p] != 0).sum())
                    ok = z[f"f0/d{g}/injury_ok"][p].astype(bool) & z[f"f0/d{g}/body_injury_ok"][p].astype(bool)
                    idn["injury_ok"][0] += k
                    idn["injury_ok"][1] += int((~ok).sum())
                    for q_ in ("agree_pre", "agree_p80", "agree_p16", "agree_p4", "agree_end"):
                        if f"f0/d{g}/{q_}" in z.files:
                            OBS.setdefault((lab, q_, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"f0/d{g}/{q_}"][p]
                    ex = {q: np.asarray(z[f"f0/d{g}/{q}"][p], float) for q in ("exp_full", "exp_early", "exp_late", "kexp")}
                    for q, v in ex.items():
                        EXPO.setdefault((lab, q, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = v
                    if rr["field"] == "none":
                        idn["fieldfree_zero"][0] += k
                        idn["fieldfree_zero"][1] += int(sum((v != 0).sum() for v in ex.values()))
                    else:
                        kap = float(rr["kappa_used"]) if "kappa_used" in rr else KAPPA
                        assert abs(kap - (KAPPA_MATCHED if lab == "relax-matched/memory" else KAPPA)) < 1e-12, (lab, kap)
                        want = kap * ex["exp_full"]
                        rel = float((np.abs(ex["kexp"] - want) / np.maximum(np.abs(want), 1e-300)).max())
                        idn["kexp_window"][0] += k
                        idn["kexp_window"][1] = max(idn["kexp_window"][1], rel)
LABELS = sorted(LABELS)
say(f"P66c on {', '.join(str(r_) for r_ in ROOTS)} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): "
    f"{sum(len(m_['tasks']) for m_ in MS)} task-files, every sha256 equal to its manifest's; digest"
    f"{'s' if len(set(DIGESTS)) > 1 else ''} {', '.join(d[:12] for d in DIGESTS)}; " + "; ".join(f"{m_['started_utc']} - {m_['finished_utc']}, {m_['cpu_s_total'] / 3600:.2f} CPU-h" for m_ in MS)
    + f"; {nraw} restored records, every sha256 equal to {SRC}'s manifest; the acquisition rebuilt by ar001.sim.prepare "
    f"(purpose {PURPOSE}; {KC} cases a task) equal to every record's V0, R0 and T")
say(f"  the labels: every row as the plan's table ({', '.join(LABELS)})")
say(f"  the injury schedule recomputed by the lead ({n_sched} case-tasks x {GS} generations; at most {max_att} rejected "
    f"attempts): every corner and attempt equal to the shard's, the same in every root; the patches disjoint")
say(f"  the packets at generation 0 rebuilt by the lead ({n_pk} label-tasks): every endpoint equal to the stage's within {d0:.1e}")
say(f"  the successors re-scored by the lead from the saved states ({n_states} row-task-horizons; own patch, union, whole "
    f"sheet): largest |difference| {dg:.1e}")
say(f"  the fresh successors re-scored from their saved final states: "
    + (f"{n_fresh} row-task-tests, largest |difference| {dx:.1e}" if n_fresh else "not saved at this stage (their reads are taken as written)"))
if P66K is not None:
    c0 = P66K["calls"][0]["pooled"]
    xs_ = [1.0, 1.4, 1.8]
    ys_ = [c0[f"relax@{k_:g}"]["integrated"] for k_ in xs_]
    T_ = c0["raise/memory"]["integrated"]
    co = np.polyfit(xs_, ys_, 2)
    roots = [r_.real for r_ in np.roots([co[0], co[1], co[2] - T_]) if abs(r_.imag) < 1e-12 and xs_[0] <= r_.real <= xs_[-1]]
    assert len(roots) == 1 and float(f"{roots[0]:.4g}") == KAPPA_MATCHED, (roots, KAPPA_MATCHED)
    say(f"  kappa' by the declared closed-loop rule from P66k's trials (the quadratic through kappa' 1.0, 1.4, 1.8 at raise's "
        f"integrated {T_:,.1f}): root {roots[0]:.5f}, rounded {float(f'{roots[0]:.4g}')}, equal to the design's {KAPPA_MATCHED}")
say(f"  kappa: E2E006's {KAPPA}, declared; the size-matched relax's kappa' {KAPPA_MATCHED}; every row's recorded kappa "
    f"equal to its declared one")
say(f"  identities: a vote row fired in {idn['vote_never'][1]} of {idn['vote_never'][0]} lineage-case-generations; an "
    f"injury check (the memory flip and the body flip) failed in {idn['injury_ok'][1]} of {idn['injury_ok'][0]}; a "
    f"field-free row's exposure was not 0 in {idn['fieldfree_zero'][1]} "
    f"of {idn['fieldfree_zero'][0]} case-generations x 4 quantities; every field branch's realized response equals its "
    f"kappa x its window's mean exposure in {idn['kexp_window'][0]} case-generations (largest relative difference "
    f"{idn['kexp_window'][1]:.1e}: the response acted only inside its window)")
assert d0 < 1e-12 and dg < 1e-12 and dx < 1e-12
assert idn["vote_never"][1] == 0 and idn["birth_cue_agrees"][1] == 0 and idn["injury_ok"][1] == 0
assert idn["fieldfree_zero"][1] == 0 and idn["kexp_window"][1] < 1e-12


def X(lab, e, g):
    a = VAL[(lab, e, g)]
    assert not np.isnan(a).any(), (lab, e, g)
    return a.mean(axis=1)


def X_sub(lab, e, g, sub):
    a = VAL[(lab, e, g)]
    ix = [i for i, p in enumerate(PAIRS) if p in sub]
    return a[:, ix].mean(axis=1)


def cover(lab, e, g):
    a = VAL.get((lab, e, g))
    return 0 if a is None else int((~np.isnan(a).any(axis=2)).sum())


K = 3 * math.sqrt(1 / 4 + 1 / 16)
T975 = stats.t.ppf(0.975, NB - 1) if NB > 1 else float("nan")


def est(x):
    blk = x.mean(1)
    v = float(blk.mean())
    sdc = float(x.ravel().std(ddof=1)) / math.sqrt(x.shape[1])
    sdb = float(blk.std(ddof=1)) if NB > 1 else float("nan")
    sd = max(sdb, sdc) if NB > 1 else sdc
    h = T975 * sd / math.sqrt(NB) if NB > 1 else float("nan")
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sdb": sdb, "sdc": sdc, "blocks": [float(y) for y in blk],
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean())) if NB > 1 else (v, v)}


def narrow_num(q):
    lo_raw, hi_raw = min(q["v"] - K * q["sd"], *q["halves"]), max(q["v"] + K * q["sd"], *q["halves"])
    st_ = lambda raw: 0.005 if abs(raw) < 0.01 else 0.01
    lo = math.floor(round(lo_raw / st_(lo_raw), 9)) * st_(lo_raw)
    hi = math.ceil(round(hi_raw / st_(hi_raw), 9)) * st_(hi_raw)
    return round(lo, 3), round(hi, 3)


# the registration (REGISTRATION_E2E007.md with its amendment; the lead's rulings sent 23:16:21Z, after P66's values):
# Z1, Z2, Z4, Z5, Z1x as declared at the rule's narrowest; Z3 and Z3x in the direction P66 showed, disclosed
TH = {"Z1": ("least", 0.17), "Z2": ("least", 0.09), "Z3": ("most", 0.02), "Z4": ("least", 0.07), "Z5": ("most", -0.03),
      "Z1x": ("least", 0.19), "Z3x": ("most", -0.01)}
D2 = lambda a, b, e, g: (lambda f: f(a, e, g) - f(b, e, g))
PARTS = [
    ("Z1", "U_v(relax) - U_v(none), memory injury, g 8", D2("relax/memory", "none/memory", "U_v", 8)),
    ("Z2", "q_r(relax) - q_r(none), memory injury, g 8", D2("relax/memory", "none/memory", "q_r", 8)),
    ("Z3", "U_v(raise) - U_v(none), body injury, g 8", D2("raise/body", "none/body", "U_v", 8)),
    ("Z4", "the interaction: [U_v(raise) - U_v(none)] body - [the same] memory, g 8",
     lambda f: (f("raise/body", "U_v", 8) - f("none/body", "U_v", 8)) - (f("raise/memory", "U_v", 8) - f("none/memory", "U_v", 8))),
    ("Z5", "U_v(relax) - U_v(none), body injury, g 8", D2("relax/body", "none/body", "U_v", 8)),
    ("Z1x", "the fresh successor's U_v, relax - none, memory injury, after g 8", D2("x:relax/memory", "x:none/memory", "U_v", 8)),
    ("Z3x", "the fresh successor's U_v, raise - none, body injury, after g 8", D2("x:raise/body", "x:none/body", "U_v", 8))]
SETS = {"particular (li4 x F0)": {("li4", "F0_t0"), ("li4", "F0_t1")}, "native (li4 x S4)": {("li4", "S4_t0"), ("li4", "S4_t1")},
        "permissive (dw)": {("dw", u) for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")}}
full = lambda lab, e, g: X(lab, e, g)
sub_ = lambda sub: (lambda lab, e, g: X_sub(lab, e, g, sub))
say(f"\nTHE PARTS ({NB} blocks x {KC} cases; pooled over the eight unit-body pairs, one future; [95% t interval]"
    + (f"; the rule: margin >= {K:.4f} and both halves" if SKEY == "probe" else "") + ")")
Q, OK, NARROW = {}, {}, {}
for pid, words, fn in PARTS:
    try:
        x = fn(full)
    except (AssertionError, KeyError):
        say(f"  {pid} {words}: not available at this stage")
        continue
    q = Q[pid] = est(x)
    line = (f"  {pid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
            f"case/sqrt{KC} {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
    kd, th = TH[pid]
    if SKEY == "probe":
        lo, hi = NARROW[pid] = narrow_num(q)
        line += f"; the narrowest [{lo:+.3f}, {hi:+.3f}]"
        if th is not None:
            assert (lo, hi) == th if kd == "band" else abs((hi if kd == "most" else lo) - th) < 1e-9, (pid, lo, hi, th)
    if th is not None:
        OK[pid] = (th[0] <= q["v"] <= th[1]) if kd == "band" else (q["v"] <= th if kd == "most" else q["v"] >= th)
        line += (f"; registered {list(th) if kd == 'band' else ('<= ' if kd == 'most' else '>= ') + str(th)}: "
                 f"{'HOLDS' if OK[pid] else 'FAILS'}")
    else:
        line += "; its threshold not yet registered"
    say(line)
    say("      by item set: " + "; ".join(f"{nm} {est(fn(sub_(sb)))['v']:+.6f}" for nm, sb in SETS.items()))
if OK:
    say("  VERDICTS (development: the point value against the registered threshold or band): "
        + ", ".join(f"{p} {'HOLDS' if v else 'FAILS'}" for p, v in OK.items())
        + ("" if STAGE == "development" else "  [not a development result]"))

say("\nREPORTED (the lead's)")
say("  the levels (all pairs; li4 x F0 in parentheses): U_v, q_r, a_v at g 0, 1, 3, 8; the fresh U_v after 1, 3, 8")
for lab in LABELS:
    cells = []
    for g in (0, 1, 3, 8):
        if cover(lab, "U_v", g) == NB * len(PAIRS):
            cells.append(f"g{g} U_v {X(lab, 'U_v', g).mean():.4f} ({X_sub(lab, 'U_v', g, SETS['particular (li4 x F0)']).mean():.4f}) "
                         f"q_r {X(lab, 'q_r', g).mean():+.4f} ({X_sub(lab, 'q_r', g, SETS['particular (li4 x F0)']).mean():+.4f}) "
                         f"a_v {X(lab, 'a_v', g).mean():.4f}")
    for g in (1, 3, 8):
        if cover("x:" + lab, "U_v", g) == NB * len(PAIRS):
            cells.append(f"x{g} U_v {X('x:' + lab, 'U_v', g).mean():.4f} ({X_sub('x:' + lab, 'U_v', g, SETS['particular (li4 x F0)']).mean():.4f})")
    say(f"  {lab} [{ROWINFO[lab]['policy']}; target {ROWINFO[lab]['target']}; response {ROWINFO[lab]['response']}; field "
        f"{ROWINFO[lab]['field']}]: " + "; ".join(cells))
say("  the exposures per generation (the mean x a generation; the recorded response kappa x x, kexp x 8,000):")
for lab in [l for l in LABELS if ROWINFO[l]["field"] != "none"]:
    gs = sorted(g for (l, q_, g) in EXPO if l == lab and q_ == "kexp" and not np.isnan(EXPO[(l, q_, g)]).any())
    say(f"    {lab}: " + " ".join(f"g{g} {EXPO[(lab, 'exp_full', g)].mean():.3f}/{EXPO[(lab, 'kexp', g)].mean() * 8000:,.0f}" for g in gs))
for a, b in (("relax/memory", "raise/memory"), ("relax-matched/memory", "raise/memory"), ("relax/body", "raise/body")):
    if a in LABELS and b in LABELS:
        gs = sorted(g for (l, q_, g) in EXPO if l == a and q_ == "kexp")
        say(f"    {a} / {b}, the recorded response: " + " ".join(
            f"g{g} {EXPO[(a, 'kexp', g)].mean() / EXPO[(b, 'kexp', g)].mean():.3f}" for g in gs if (b, "kexp", g) in EXPO))
say("  the observer: the patch's agreement around the body flip, the mean over generations (pre / +100 / +500 / +2,000 / end):")
for lab in LABELS:
    cells = []
    for q_ in ("agree_pre", "agree_p80", "agree_p16", "agree_p4", "agree_end"):
        vals = [OBS[(lab, q_, g)] for g in range(1, G + 1) if (lab, q_, g) in OBS and not np.isnan(OBS[(lab, q_, g)]).any()]
        cells.append(f"{np.mean(vals):.3f}" if vals else "-")
    say(f"    {lab}: " + " / ".join(cells))
GR = max([g for g in range(1, G + 1) if any(cover(l, "U_v", g) == NB * len(PAIRS) for l in LABELS)], default=0)
say(f"  contrasts reported (g {GR}; the fresh after g {GR}): every response against none under each target; the size-matched relax")
for a, b in [(f"{r}/{t}", f"none/{t}") for t in ("memory", "body") for r in ("raise", "relax")] + [
        ("relax-matched/memory", "none/memory"), ("relax-matched/memory", "relax/memory")]:
    cells = []
    for e, lab_a, lab_b in (("U_v", a, b), ("q_r", a, b), ("U_v", "x:" + a, "x:" + b)):
        try:
            qq = est(X(lab_a, e, GR) - X(lab_b, e, GR))
            qp = est(X_sub(lab_a, e, GR, SETS["particular (li4 x F0)"]) - X_sub(lab_b, e, GR, SETS["particular (li4 x F0)"]))
            cells.append(f"{'fresh ' if lab_a.startswith('x:') else ''}{e} {qq['v']:+.4f} [{qq['lo']:+.4f}, {qq['hi']:+.4f}]"
                         f" (li4 x F0 {qp['v']:+.4f})")
        except (AssertionError, KeyError):
            pass
    if cells:
        say(f"    {a} - {b}: " + "; ".join(cells))
try:
    qi = est((X("raise/body", "q_r", GR) - X("none/body", "q_r", GR)) - (X("raise/memory", "q_r", GR) - X("none/memory", "q_r", GR)))
    say(f"    the q_r interaction [raise - none] body - memory: {qi['v']:+.4f} [{qi['lo']:+.4f}, {qi['hi']:+.4f}]")
except (AssertionError, KeyError):
    pass

if READER is not None:
    rd = json.load(open(READER))
    assert rd["study"] == "E2E007" and rd["stage"] in (STAGE,) + (PROBE_STAGES if SKEY == "probe" else ()), "another stage"
    rroots = rd["root"] if isinstance(rd["root"], list) else [rd["root"]]
    assert sorted(Path(x).resolve() for x in rroots) == sorted(r_.resolve() for r_ in ROOTS), ("another run", rroots)
    if rd["design_digest"] not in DIGESTS:
        assert STAGE != "development", "the reader's design is not the run's"
        say(f"\n  (the reader ran under design {rd['design_digest'][:12]}, the run under {MS[0]['design_digest'][:12]})")
    NAMES = {"native": SETS["native (li4 x S4)"], "particular": SETS["particular (li4 x F0)"],
             "permissive": SETS["permissive (dw)"]}
    FN = {p: f for p, _w, f in PARTS}
    worst, n_cmp, n_th, n_nar = 0.0, 0, 0, 0
    GEN = {}
    other = []
    for rp in rd["parts"]:
        pid = rp["id"]
        if not rp["available"] or pid not in Q:
            continue
        if f"g {GEN.get(pid, 8)}" not in rp["part"]:
            other.append(f"{pid} ('{rp['part']}')")       # a reader before the amendment defines the part otherwise
            assert STAGE != "development", (pid, "the frozen reader's part is not the registered one")
            continue
        q = Q[pid]
        assert rp["n_blocks"] == NB and rp["n_cases_a_block"] == KC
        for a, b in (("value", q["v"]), ("sd", q["sd"]), ("sd_case", q["sdc"])):
            worst = max(worst, abs(rp[a] - b))
        worst = max(worst, max(abs(x - y) for x, y in zip(rp["blocks"], q["blocks"])))
        if NB > 1:
            worst = max(worst, abs(rp["sd_block"] - q["sdb"]), abs(rp["ci95"][0] - q["lo"]), abs(rp["ci95"][1] - q["hi"]),
                        max(abs(x - y) for x, y in zip(rp["halves"], q["halves"])))
        for nm, sb in NAMES.items():
            worst = max(worst, abs(rp["by_item_set"][nm]["value"] - est(FN[pid](sub_(sb)))["v"]))
        if SKEY == "probe" and rp.get("narrowest") is not None and pid in NARROW:
            # the reader's narrowest in the reader's own kind (the phase-A reader states H1-H3 in the declared direction)
            nr, rk = rp["narrowest"], rp["kind"]
            mine = list(NARROW[pid]) if rk == "in" else (NARROW[pid][1] if rk == "le" else NARROW[pid][0])
            assert (list(nr) == mine) if rk == "in" else abs(nr - mine) < 1e-9, (pid, rk, nr, mine)
            n_nar += 1
        if rp.get("threshold") is not None:
            kd, th = TH[pid]
            assert th is not None, (pid, "the reader registers a threshold the lead's table lacks")
            assert rp["kind"] == {"band": "in", "least": "ge", "most": "le"}[kd], (pid, rp["kind"])
            assert (list(rp["threshold"]) == list(th)) if kd == "band" else abs(rp["threshold"] - th) < 1e-12, (pid, rp["threshold"])
            assert rp["holds"] == OK[pid] and rd["verdicts"][pid] == ("HOLDS" if OK[pid] else "FAILS"), pid
            n_th += 1
        n_cmp += 1
    lw, nl, partial = 0.0, 0, []
    lv = READER.parent / "levels.json"
    if lv.exists():
        LV = json.load(open(lv))["levels"]
        for kk, rec in LV.items():
            lab, e, g = kk.split("|")
            if g.startswith("d"):
                continue
            if g.startswith("x"):
                lab, g = "x:" + lab, g[1:]
            g = int(g)
            if e not in ENDS or (lab, e, g) not in VAL:
                continue
            c = cover(lab, e, g)
            assert rec["tasks"] == c, (kk, rec["tasks"], c)
            if c < NB * len(PAIRS):
                partial.append(kk)
                continue
            lw = max(lw, abs(rec["all"] - float(X(lab, e, g).mean())))
            for nm, sb in NAMES.items():
                lw = max(lw, abs(rec[nm] - float(X_sub(lab, e, g, sb).mean())))
            nl += 1
    ew, ne = 0.0, 0
    for lab, byg in rd.get("exposures", {}).items():
        if not isinstance(byg, dict) or lab not in LABELS:
            continue
        for gs, rec in byg.items():
            g = int(gs)
            for q_ in ("exp_full", "exp_early", "exp_late", "kexp"):
                if (lab, q_, g) in EXPO:
                    ew = max(ew, abs(rec[q_] - float(EXPO[(lab, q_, g)].mean())))
                    ne += 1
    say(f"\nAGAINST THE FROZEN READER ({READER}): {n_cmp} parts (values, intervals, SDs, halves, blocks, item sets; "
        f"{n_th} registered thresholds, kinds and verdicts; {n_nar} narrowest thresholds in the reader's kind) largest "
        f"difference {worst:.2e}; {nl} levels (lineage and fresh), "
        f"largest difference {lw:.2e}; partial levels (not pooled here): {len(partial)}; {ne} exposure means, largest "
        f"difference {ew:.2e}")
    if other:
        say("  not compared (the reader's own definition differs, as before the amendment): " + "; ".join(other))
    assert worst < 1e-12 and lw < 1e-12 and ew < 1e-12

name = f"p66c_e2e007_lead_check{'_' + SKEY if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
