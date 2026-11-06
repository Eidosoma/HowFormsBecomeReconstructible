"""P63c (python probes/p63c_e2e006_lead_check.py ROOT [ROOT ...] [--reader READER]): the lead's check of E2E006,
collective rescue through renewal. LEAD_CHECK_NOT_REGISTERED; a read of the stages' shards and saved successor states and
of the restored AR006 records, written by the lead in reviewing E2E006's phase A and committed before the freeze,
dry-run first on P63 (AR006's P57 records 900917 | 900919, all eight cases, one future; its rows in one or more roots
under the same tag) and on the debug run (900948, every row to generation 3); 5 November 2026; no simulation of the
tissue or of the field. Adapted from P59c (E2E003), whose integrity, schedule, packet and re-scoring sections it keeps.

It checks, from PLAN_E2E006.md's words (with its amendments) and not from e2e006.sim, e2e006.predict, e2e006.checks,
e2e003.sim, e2e002.sim or msefield:
1. integrity: every stage file against its manifest by sha256, every restored record against its own run's manifest,
   the acquisition rebuilt by ar001.sim.prepare equal to the record's V0, R0 and T; at the development stage the run's
   digest against e2e006/frozen/design.json; every label's row (policy, sigma, injury, field, medium, window, copying,
   kappa key, generation-0 packet) against the plan's table;
2. the injury schedule, recomputed by the lead (E2E003's rule under the stage's tag): the corners and attempts equal to
   the shard's, the patches disjoint; where several roots hold one task, the same schedule in each;
3. the packets at generation 0 rebuilt and scored by the lead (the vote's and vtol's memory@0 records; protected: R0 with
   its bonds and V0; the ceiling: the vote's none@0 record); every successor endpoint at every saved horizon re-scored
   from the saved states (own patch, the union of generation 0's and every injured patch so far, whole sheet); every
   fresh successor's endpoints re-scored from its saved final state where the stage saves it (the union of the lineage's
   patches through g, whole sheet);
4. the identities: a vote row never fires; a birth cue at sigma 0 agrees with its incoming record; every injured branch's
   injury check holds and the ceiling records none; a field-free row's exposures are exactly 0; kappa recomputed by the
   lead from P63k's reference exposures by the declared rule (1 / the mean exposure, four significant figures) equals the
   design's; every field branch's realized response equals its kappa x its window's mean exposure (kexp = kappa x
   exp_full, kappa_early x exp_early / 2, kappa_late x exp_late / 2), so the response acted only inside its window;
5. the parts by the registration's words (pooled per case over the eight unit-body pairs, a block the mean of its cases,
   the part the mean over the blocks; SD = max(block SD, case SD / sqrt(cases a block)); the 95% t interval); on P63 the
   narrowest thresholds the rule allows, which must equal the registered ones; at development the point value against
   the registered threshold or band;
6. reported: the levels (U_v, q_r, a_v and the fresh U_v) by item set, li4 x F0 first; the exposures and the realized
   integrated responses per generation, the matched ratios (isolated-matched / shared, early / late); the field-free and
   comparator contrasts; with READER, the frozen reader's parts, thresholds, verdicts, levels and exposures.

The lead's scoring (E2E001's endpoints, as P59c): s = +1 where dl001.sim.sign(x, T) >= 0.5, else -1; u_r = lr005.sim.
inside(s r, T, m); u_v the same for the body; u_r_raw without s; a = max(sign, 1 - sign); q = (a - max over SR001's
foreign placements of a) / 0.25; agree_in the agreement of V and r inside m; U, U_v, U_raw, agree_U the same on the union.
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
PROBE_STAGES = ("probe", "probe_x")                             # P63's rows in two roots: P63 and P63x (Amendment 2)
assert all((m_["stage"] == STAGE) or (STAGE in PROBE_STAGES and m_["stage"] in PROBE_STAGES) for m_ in MS)
SKEY = "probe" if STAGE in PROBE_STAGES else STAGE
AR006_DEV = [925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621, 925622, 925624, 925626, 925627, 925628,
             925630, 925633, 925634]
# stage -> (restored source, blocks, the successors' tag, parents read, the blocks' enrolment purpose)
WANT = {"probe": ("ar006/p57", [900917, 900919], "mse-p63", (0, 1), "engineering"),
        "debug": ("ar006/debug", [900948], "mse-e2e006", (0, 1), "engineering"),
        "preflight": ("ar006/preflight", [900929], "mse-e2e006", (0, 1), "engineering"),
        "development": ("ar006/development", AR006_DEV, "mse-e2e006", (0, 1), "confirmation")}
SRC, BLOCKS, FTAG, PARENTS, PURPOSE = WANT[SKEY]
SROOT = RUNS / SRC
NB = len(BLOCKS)
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
for r_, m_ in zip(ROOTS, MS):
    bad = [f["path"] for t in m_["tasks"].values() for f in t["files"].values() if sha(r_ / f["path"]) != f["sha256"]]
    assert m_["study"] == "E2E006" and not bad, (r_, bad[:5])
    assert len(m_["tasks"]) == len(PAIRS) * NB, (r_, len(m_["tasks"]))
DIGESTS = [m_["design_digest"] for m_ in MS]
# at the probe stage P63 ran under phase A's design and P63x under Amendment 2's (nothing that feeds the states changed:
# the fork's P63e, the shared row alone equal to P63's bit for bit); the lead checks the pairing it can see: the same tag,
# cases and injury schedule in every root, task by task. Every other stage is one run under one design.
assert SKEY == "probe" or len(set(DIGESTS)) == 1, "the roots ran under different designs"
SM = json.load(open(SROOT / "manifest.json"))
if STAGE == "development":
    fz = json.load(open(LANE / "e2e006" / "frozen" / "design.json"))
    assert fz["digest"] == MS[0]["design_digest"], "the run is not under the frozen design"
# the plan's lineage table: label -> (generation-0 packet, policy, injured, field, medium, window, copying, kappa key)
PLAN = {"vote/none": ("vote/memory@0", "vote", True, "none", "-", "-", False, None),
        "vote/isolated": ("vote/memory@0", "vote", True, "isolated", "reset", "full", False, None),
        "vote/shared": ("vote/memory@0", "vote", True, "shared", "reset", "full", False, None),
        "vote/shared-retained": ("vote/memory@0", "vote", True, "shared", "retain", "full", False, None),
        "vote/shared-early": ("vote/memory@0", "vote", True, "shared", "reset", "early", False, None),
        "vote/shared-late": ("vote/memory@0", "vote", True, "shared", "reset", "late", False, None),
        "vote/isolated-matched": ("vote/memory@0", "vote", True, "isolated", "reset", "full", False, "isolated"),
        "protected": ("protected", "vote", True, "none", "-", "-", True, None),
        "vtol-every": ("vtol/memory@0", "vtol", True, "none", "-", "-", False, None),
        "uninjured": ("vote/none@0", "vote", False, "none", "-", "-", False, None),
        "vtol-every/shared": ("vtol/memory@0", "vtol", True, "shared", "reset", "full", False, None)}
G = 8
SIDE, SIZE = 32, 4
T_GEN = 8000

# ------------------------------------------------------------------ kappa by the declared rule, from P63k's reference
P63K = json.load(open(LANE / "probes" / "results" / "p63k_e2e006_kappa.json"))
sig4 = lambda v: float(f"{v:.4g}")
ref_s, ref_i = P63K["vote/shared@k0"]["mean"], P63K["vote/isolated@k0"]["mean"]
KAPPA_LEAD = {"full": sig4(1 / ref_s["exp_full"]), "early": sig4(1 / ref_s["exp_early"]),
              "late": sig4(1 / ref_s["exp_late"]), "isolated": sig4(1 / ref_i["exp_full"])}


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
                src, pol, injd, fld, med, win, cp, kk = PLAN[lab]
                rr = rows[row]
                assert meta["sources"][lab] == src and rr["policy"] == pol and bool(rr["injured"]) == injd, lab
                assert (rr["field"], rr["medium"], rr["window"], bool(rr["copy"]), rr["kappa_key"]) == (fld, med, win, cp, kk), (lab, rr)
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
                    ok = z[f"f0/d{g}/injury_ok"][p].astype(bool)
                    nm = "injury_ok" if rr["injured"] else "ceiling_uninjured"
                    idn[nm][0] += k
                    idn[nm][1] += int((~ok).sum())
                    ex = {q: np.asarray(z[f"f0/d{g}/{q}"][p], float) for q in ("exp_full", "exp_early", "exp_late", "kexp")}
                    for q, v in ex.items():
                        EXPO.setdefault((lab, q, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = v
                    if rr["field"] == "none":
                        idn["fieldfree_zero"][0] += k
                        idn["fieldfree_zero"][1] += int(sum((v != 0).sum() for v in ex.values()))
                    else:
                        kap = KAPPA_LEAD["isolated" if rr["kappa_key"] == "isolated" else rr["window"]]
                        want = {"full": kap * ex["exp_full"], "early": kap * ex["exp_early"] / 2,
                                "late": kap * ex["exp_late"] / 2}[rr["window"]]
                        rel = float((np.abs(ex["kexp"] - want) / np.maximum(np.abs(want), 1e-300)).max())
                        idn["kexp_window"][0] += k
                        idn["kexp_window"][1] = max(idn["kexp_window"][1], rel)
LABELS = sorted(LABELS)
say(f"P63c on {', '.join(str(r_) for r_ in ROOTS)} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): "
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
say(f"  kappa by the declared rule from P63k's reference exposures (1 / the mean exposure, four significant figures): "
    + ", ".join(f"{w} {v}" for w, v in KAPPA_LEAD.items()))
fld = json.loads(str(np.load(next((ROOTS[0] / "shards").rglob("*.npz")))["__meta__"]))["field"]
assert (fld["kappa"], fld["kappa_early"], fld["kappa_late"], fld["kappa_isolated"]) == (
    KAPPA_LEAD["full"], KAPPA_LEAD["early"], KAPPA_LEAD["late"], KAPPA_LEAD["isolated"]), fld
say(f"    equal to the design's (kappa {fld['kappa']}, early {fld['kappa_early']}, late {fld['kappa_late']}, isolated "
    f"{fld['kappa_isolated']})")
say(f"  identities: a vote row fired in {idn['vote_never'][1]} of {idn['vote_never'][0]} lineage-case-generations; a vtol "
    f"birth cue disagreed at birth in {idn['birth_cue_agrees'][1]} of {idn['birth_cue_agrees'][0]}; an injury check failed "
    f"in {idn['injury_ok'][1]} of {idn['injury_ok'][0]} (the ceiling: {idn['ceiling_uninjured'][1]} of "
    f"{idn['ceiling_uninjured'][0]} not 'no injury'); a field-free row's exposure was not 0 in {idn['fieldfree_zero'][1]} "
    f"of {idn['fieldfree_zero'][0]} case-generations x 4 quantities; every field branch's realized response equals its "
    f"kappa x its window's mean exposure in {idn['kexp_window'][0]} case-generations (largest relative difference "
    f"{idn['kexp_window'][1]:.1e}: the response acted only inside its window)")
assert d0 < 1e-12 and dg < 1e-12 and dx < 1e-12
assert idn["vote_never"][1] == 0 and idn["birth_cue_agrees"][1] == 0 and idn["injury_ok"][1] == 0
assert idn["ceiling_uninjured"][1] == 0 and idn["fieldfree_zero"][1] == 0 and idn["kexp_window"][1] < 1e-12


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


# the registration's thresholds (REGISTRATION_E2E006.md with Amendment 2, df229acd1b; the lead's rulings sent 13:46:59Z,
# after P63's values): H1-H3 in the reversed direction at the rule's narrowest; N1-N3 (bands, inside the frozen margin
# [-0.03, 0.03]) and R1-R3 (at most) at the rule's narrowest on P63 with P63x, declared before P63x's values; H5 at g 3
TH = {"H1": ("most", -0.05), "H2": ("most", -0.04), "H3": ("most", -0.01),
      "N1": ("band", (-0.01, 0.01)), "N2": ("band", (-0.01, 0.02)), "N3": ("band", (-0.01, 0.01)),
      "R1": ("most", -0.09), "R2": ("most", -0.08), "R3": ("most", -0.02),
      "H5": ("band", (-0.04, 0.02))}
D2 = lambda a, b, e, g: (lambda f: f(a, e, g) - f(b, e, g))
SH, IS, IM, NO = "vote/shared", "vote/isolated", "vote/isolated-matched", "vote/none"
PARTS = [
    ("H1", "U_v(vote/shared) - U_v(vote/isolated), g 8", D2(SH, IS, "U_v", 8)),
    ("H2", "q_r(vote/shared) - q_r(vote/isolated), g 8", D2(SH, IS, "q_r", 8)),
    ("H3", "the fresh successor's U_v, vote/shared - vote/isolated, after g 8", D2("x:" + SH, "x:" + IS, "U_v", 8)),
    ("N1", "U_v(vote/shared) - U_v(vote/isolated-matched), g 8: the neighbours' signal at a matched response", D2(SH, IM, "U_v", 8)),
    ("N2", "q_r(vote/shared) - q_r(vote/isolated-matched), g 8", D2(SH, IM, "q_r", 8)),
    ("N3", "the fresh U_v, vote/shared - vote/isolated-matched, after g 8", D2("x:" + SH, "x:" + IM, "U_v", 8)),
    ("R1", "U_v(vote/isolated-matched) - U_v(vote/none), g 8: the response at the shared row's size, private signals", D2(IM, NO, "U_v", 8)),
    ("R2", "q_r(vote/isolated-matched) - q_r(vote/none), g 8", D2(IM, NO, "q_r", 8)),
    ("R3", "the fresh U_v, vote/isolated-matched - vote/none, after g 8", D2("x:" + IM, "x:" + NO, "U_v", 8)),
    ("H5", "U_v(vote/shared-early) - U_v(vote/shared-late), g 3: early against late at matched exposure",
     D2("vote/shared-early", "vote/shared-late", "U_v", 3))]
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
    say(f"  {lab} [{ROWINFO[lab]['policy']}; field {ROWINFO[lab]['field']}, {ROWINFO[lab]['medium']}, window "
        f"{ROWINFO[lab]['window']}; copy {ROWINFO[lab]['copy']}]: " + "; ".join(cells))
say("  the exposures per generation (the mean x a generation; the realized integrated response kappa x x, kexp x 8,000):")
for lab in [l for l in LABELS if ROWINFO[l]["field"] != "none"]:
    gs = sorted(g for (l, q_, g) in EXPO if l == lab and q_ == "kexp" and not np.isnan(EXPO[(l, q_, g)]).any())
    say(f"    {lab}: " + " ".join(f"g{g} {EXPO[(lab, 'exp_full', g)].mean():.3f}/{EXPO[(lab, 'kexp', g)].mean() * T_GEN:,.0f}" for g in gs))
for a, b in ((IM, SH), ("vote/shared-early", "vote/shared-late"), (IS, SH)):
    if a in LABELS and b in LABELS:
        gs = sorted(g for (l, q_, g) in EXPO if l == a and q_ == "kexp")
        say(f"    {a} / {b}, integrated response: " + " ".join(
            f"g{g} {EXPO[(a, 'kexp', g)].mean() / EXPO[(b, 'kexp', g)].mean():.3f}" for g in gs if (b, "kexp", g) in EXPO))
GR = max([g for g in range(1, G + 1) if any(cover(l, "U_v", g) == NB * len(PAIRS) for l in LABELS)], default=0)
say(f"  contrasts reported (g {GR}, the stage's last generation; the fresh after g {GR}): every field row against vote/none; "
    f"shared against the isolated rows; the comparators against vote/shared")
for a, b in ([(l, NO) for l in LABELS if ROWINFO[l]["field"] != "none" and l != NO]
             + [(SH, IM), (IM, IS), (SH, IS), ("protected", SH), ("vtol-every", SH)]):
    cells = []
    for e, lab_a, lab_b in (("U_v", a, b), ("q_r", a, b), ("U_v", "x:" + a, "x:" + b)):
        try:
            qq = est(X(lab_a, e, GR) - X(lab_b, e, GR))
            cells.append(f"{'fresh ' if lab_a.startswith('x:') else ''}{e} {qq['v']:+.4f} [{qq['lo']:+.4f}, {qq['hi']:+.4f}]")
        except (AssertionError, KeyError):
            pass
    if cells:
        say(f"    {a} - {b}: " + "; ".join(cells))

if READER is not None:
    rd = json.load(open(READER))
    assert rd["study"] == "E2E006" and rd["stage"] in (STAGE,) + (PROBE_STAGES if SKEY == "probe" else ()), "another stage"
    rroots = rd["root"] if isinstance(rd["root"], list) else [rd["root"]]
    assert sorted(Path(x).resolve() for x in rroots) == sorted(r_.resolve() for r_ in ROOTS), ("another run", rroots)
    if rd["design_digest"] not in DIGESTS:
        assert STAGE != "development", "the reader's design is not the run's"
        say(f"\n  (the reader ran under design {rd['design_digest'][:12]}, the run under {MS[0]['design_digest'][:12]})")
    NAMES = {"native": SETS["native (li4 x S4)"], "particular": SETS["particular (li4 x F0)"],
             "permissive": SETS["permissive (dw)"]}
    FN = {p: f for p, _w, f in PARTS}
    worst, n_cmp, n_th, n_nar = 0.0, 0, 0, 0
    GEN = {"H5": 3}
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

name = f"p63c_e2e006_lead_check{'_' + SKEY if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
