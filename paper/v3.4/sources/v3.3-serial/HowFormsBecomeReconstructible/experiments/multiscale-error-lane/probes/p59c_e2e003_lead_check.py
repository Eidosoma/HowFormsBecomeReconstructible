"""P59c (python probes/p59c_e2e003_lead_check.py ROOT [READER]): the lead's check of E2E003, repeated injury.
LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved successor states and of the restored AR006 records,
written by the lead in reviewing E2E003's phase A and committed before the freeze, dry-run first on P59 (AR006's P57
records, engineering blocks 900917, 900918 | 900919, 900928, parent 0's four cases, one future) and on the debug run
(900948, every row to generation 3); 4 November 2026; no simulation of the tissue. Adapted from P58c (E2E002).

It checks, from PLAN_E2E003.md's words (with its Amendment 1) and not from e2e003.sim, e2e003.predict, e2e003.checks,
e2e002.sim or e2e001.sim:
1. integrity: every stage file against its manifest by sha256, every restored record against its own run's manifest,
   the acquisition rebuilt by ar001.sim.prepare (under the block's enrolment purpose; the pilot's parent-0 subset where
   the stage reads it) equal to the record's V0, R0 and T; at the development stage the run's digest against
   e2e003/frozen/design.json;
2. the injury schedule, recomputed by the lead from the plan's words: per case and generation g = 1..8, the corner
   address(tag, block, message, parent, "e2e003", "injury", g, attempt).integers(0, 32, 2) of the first attempt whose
   4 x 4 patch (periodic) is disjoint from generation 0's patch (be001.sim.patch under the record's tag) and from every
   earlier generation's; the corners and attempts must equal the shard's, and the nine patches are disjoint;
3. the packets at generation 0, rebuilt by the lead from the restored files (a policy arm's first record r, H, W of its
   run; the vote's memory@1 lineage starts from its memory@0 record; the ceiling from the vote's none@0 record), scored
   by the lead with the arm's final body; every label's generation-0 endpoints (and U = u_r on generation 0's patch) must
   equal the stage's;
4. the successors: every endpoint at every saved horizon (1, 3, 8) re-scored by the lead from the saved states (V, r):
   on the generation's own patch, on the union of generation 0's patch and every patch injured so far (U, U_v, U_raw,
   agree_U), and whole-sheet (a, q);
5. the identities: a vote row never fires; a birth cue at sigma 0 agrees with its incoming record at birth; every
   injured branch's injury check holds in every generation, and the ceiling's records no injury; wherever vtol-every had
   not yet fired in generations 1..g, its saved state at g equals vtol-once's (the same packet and injuries, the vote's
   policy) bit for bit (V, r, H, W);
6. the parts J1-J5 by the plan's words and Amendment 1: pooled per case over the eight unit-body pairs (one future), a
   block the mean of its cases, the part the mean over the blocks; SD = max(block SD, case SD / sqrt(cases a block));
   the 95% t interval; the development verdict the point value against the registered threshold or band; on P59 the
   margins (>= 3 sqrt(1/4 + 1/16)), both halves and the narrowest round thresholds (0.01 steps, 0.005 within 0.01 of
   zero), which must equal the registered ones;
7. reported: the levels (U and q_r) of every label at 0, 1, 3, 8 with their task counts, by item set (li4 x F0 first),
   each generation's own-patch repair, the firing share and the onset distribution per generation; with READER, the
   frozen reader's values.

The lead's scoring (E2E001's endpoints): s = +1 where dl001.sim.sign(x, T) >= 0.5, else -1; u_r = lr005.sim.inside(s r,
T, m) with m the patch read; u_v the same for the body; u_r_raw without s; a = max(sign, 1 - sign); q = (a - max over
SR001's foreign placements of a) / 0.25; agree_in the agreement of V and r inside m.
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
from lr005 import sim as L5S                                    # noqa: E402  (frozen: inside)
from mse.native import address                                  # noqa: E402  (frozen engine: the addressed streams)
from sr001 import sim as SRS                                    # noqa: E402  (frozen: the foreign placements)

ROOT = Path(sys.argv[1])
READER = Path(sys.argv[2]) if len(sys.argv) > 2 else None
RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
key = lambda s: s.replace("/", "_")

M = json.load(open(ROOT / "manifest.json"))
STAGE = M["stage"]
AR006_DEV = [925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621, 925622, 925624, 925626, 925627, 925628,
             925630, 925633, 925634]
# stage -> (restored source, blocks, the successors' tag, parents read, the blocks' enrolment purpose)
WANT = {"probe": ("ar006/p57", [900917, 900918, 900919, 900928], "mse-p59", (0,), "engineering"),
        "debug": ("ar006/debug", [900948], "mse-e2e003", (0, 1), "engineering"),
        "preflight": ("ar006/preflight", [900929, 900947], "mse-e2e003", (0, 1), "engineering"),
        "development": ("ar006/development", AR006_DEV, "mse-e2e003", (0, 1), "confirmation")}
SRC, BLOCKS, FTAG, PARENTS, PURPOSE = WANT[STAGE]
SROOT = RUNS / SRC
NB = len(BLOCKS)
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert M["study"] == "E2E003" and not bad, bad[:5]
assert len(M["tasks"]) == len(PAIRS) * NB, len(M["tasks"])
SM = json.load(open(SROOT / "manifest.json"))
if STAGE == "development":
    fz = json.load(open(LANE / "e2e003" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"
# the plan's lineage table: label -> (generation-0 source, successors' policy, sigma, injured)
PLAN = {"vtol-every/memory@0": ("vtol/memory@0", "vtol", 0.0, True), "vtol-once/memory@0": ("vtol/memory@0", "vote", 0.0, True),
        "vote/memory@0": ("vote/memory@0", "vote", 0.0, True), "uninjured": ("vote/none@0", "vote", 0.0, False),
        "vtol-every/memory@1": ("vtol/memory@1", "vtol", 1.0, True), "vms-every/memory@1": ("vms/memory@1", "vms", 1.0, True),
        "vtol-once/memory@1": ("vtol/memory@1", "vote", 1.0, True), "vote/memory@1": ("vote/memory@0", "vote", 1.0, True),
        "vms-every/memory@0": ("vms/memory@0", "vms", 0.0, True)}
G = 8
SIDE, SIZE = 32, 4


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


def schedule_lead(cases, m0, tag, gens):
    """The plan's rule, written by the lead: {g: (k, side, side)}, corners (k, gens, 2), attempts (k, gens). A
    generation's patch depends only on the earlier ones, so a stage capped at gens draws the first gens of the full
    schedule."""
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


LABELS, KC = None, None
VAL = {}                     # (label, endpoint, g) -> (blocks, pairs, cases), NaN where the label's row did not run
FIRE, ONSET = {}, {}         # (label, g) -> (blocks, pairs, cases)
ROWINFO = {}
d0 = dg = 0.0
n_pk = nraw = n_sched = 0
max_att = 0
idn = {"vote_never": [0, 0], "birth_cue_agrees": [0, 0], "injury_ok": [0, 0], "ceiling_uninjured": [0, 0],
       "every_eq_once": [0, 0], "fired_by_g": [0, 0]}
for pi, (body, unit) in enumerate(PAIRS):
    for bi, blk in enumerate(BLOCKS):
        z = np.load(ROOT / "shards" / key(SRC) / body / unit / f"{blk}.npz")
        zr = np.load(ROOT / "raw" / key(SRC) / body / unit / f"{blk}.npz")
        meta = json.loads(str(z["__meta__"]))
        assert meta["source"] == SRC and meta["body"] == body and meta["unit"] == unit and int(meta["block"]) == blk
        assert meta["tag"] == FTAG and meta["stage"] == STAGE and meta["futures"] == 1, (meta["tag"], meta["futures"])
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
        raw = {k: (v[sel] if k in ("V0", "R0", "T") else v[:, sel]) for k, v in raw.items()}
        assert [list(c.key()) for c in cases] == [list(c) for c in meta["cases"]]
        assert np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"]) and np.array_equal(T, raw["T"])
        k = len(cases)
        KC = k if KC is None else KC
        assert k == KC
        rtag = rmeta["tag"]
        m0 = B1S.patch(cases, SIZE, rtag)
        Tf = SRS.foreign(T, pattern, cases)
        arms_of = {name: list(a) for name, a in rmeta["runs"]}
        labels, rows = meta["labels"], meta["rows"]
        if LABELS is None:
            LABELS = sorted(labels)
            ROWINFO = {lab: {x: rows[labels[lab]][x] for x in ("policy", "sigma", "injured")} for lab in LABELS}
        assert sorted(labels) == LABELS
        for lab, row in labels.items():
            src, pol, sg, injd = PLAN[lab]
            assert meta["sources"][lab] == src and rows[row]["policy"] == pol and bool(rows[row]["injured"]) == injd, lab
            assert rows[row]["policy"] == "vote" or float(rows[row]["sigma"]) == sg, lab
        # 2. the schedule
        GS = int(z["schedule/corners"].shape[1])                  # the stage's generations (the debug caps at 3)
        assert GS == max(int(r_["stop"]) for r_ in rows), GS
        sch, corners, attempts = schedule_lead(cases, m0, FTAG, GS)
        assert np.array_equal(corners, z["schedule/corners"]) and np.array_equal(attempts, z["schedule/attempts"])
        allp = m0.astype(int) + sum(sch[g].astype(int) for g in range(1, GS + 1))
        assert allp.max() == 1 and (allp.sum((-2, -1)) == SIZE * SIZE * (GS + 1)).all(), "the patches are not disjoint"
        n_sched += k
        max_att = max(max_att, int(attempts.max()))
        union = {0: m0.copy()}
        for g in range(1, GS + 1):
            union[g] = union[g - 1] | sch[g]
        own = {0: m0, **sch}
        # 3. the packets and generation 0
        pkt = {}
        for lab, row in labels.items():
            arm, sit = meta["sources"][lab].split("/")
            j = arms_of[sit].index(arm)
            pk, Vb = (raw[f"{sit}/H"][j], raw[f"{sit}/W"][j], raw[f"{sit}/r"][j]), raw[f"{sit}/V"][j]
            pkt[lab] = pk
            sc = score(np.asarray(Vb, float), np.asarray(pk[2], float), T, Tf, m0)
            for e in OWN + SHEET:
                d0 = max(d0, float(np.abs(sc[e] - z[f"g0/{e}"][row]).max()))
                VAL.setdefault((lab, e, 0), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"g0/{e}"][row]
            for e, src_e in UNION.items():
                d0 = max(d0, float(np.abs(sc[src_e] - z[f"g0/{e}"][row]).max()))
                VAL.setdefault((lab, e, 0), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"g0/{e}"][row]
            n_pk += 1
        # 4. the successors: every generation's reads; the saved states re-scored at the horizons
        st = {}
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
                st[g] = {x: zr[f"f0/g{g}/{x}"].reshape(n, k, *T.shape[1:]) for x in ("V", "r", "H", "W")}
                st[g]["rows"] = rws
                for p in range(n):
                    so = score(st[g]["V"][p], st[g]["r"][p], T, Tf, own[g])
                    su = score(st[g]["V"][p], st[g]["r"][p], T, Tf, union[g])
                    for e in OWN + SHEET:
                        dg = max(dg, float(np.abs(so[e] - z[f"f0/g{g}/{e}"][p]).max()))
                    for e, src_e in UNION.items():
                        dg = max(dg, float(np.abs(su[src_e] - z[f"f0/g{g}/{e}"][p]).max()))
        # 5. the identities
        gens = sorted(int(x.split("/")[1][1:]) for x in z.files if x.startswith("f0/d") and x.endswith("/rows"))
        for g in gens:
            rws = [int(x) for x in z[f"f0/d{g}/rows"]]
            for lab, row in labels.items():
                if row not in rws:
                    continue
                p = rws.index(row)
                on = z[f"f0/d{g}/det_on"][p]
                fired = on >= 0
                assert np.array_equal(fired, z[f"f0/d{g}/fired"][p] > 0), (lab, g)
                FIRE.setdefault((lab, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = fired
                ONSET.setdefault((lab, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = on
                pol = rows[row]["policy"]
                if pol == "vote":
                    idn["vote_never"][0] += k
                    idn["vote_never"][1] += int(fired.sum())
                cd = z[f"f0/d{g}/cue_dis_birth"][p]
                if pol != "vote" and float(rows[row]["sigma"]) == 0:
                    idn["birth_cue_agrees"][0] += k
                    idn["birth_cue_agrees"][1] += int((cd != 0).sum())
                ok = z[f"f0/d{g}/injury_ok"][p].astype(bool)
                if rows[row]["injured"]:
                    idn["injury_ok"][0] += k
                    idn["injury_ok"][1] += int((~ok).sum())
                else:
                    idn["ceiling_uninjured"][0] += k
                    idn["ceiling_uninjured"][1] += int((~ok).sum())
        for every, once in (("vtol-every/memory@0", "vtol-once/memory@0"), ("vtol-every/memory@1", "vtol-once/memory@1")):
            if every not in labels or once not in labels:
                continue
            row, prow = labels[every], labels[once]
            never = np.ones(k, bool)
            for g in gens:
                fz_ = FIRE.get((every, g))
                if fz_ is None or np.isnan(fz_[bi, pi]).any():
                    break
                never &= ~(fz_[bi, pi].astype(bool))
                if g in st and row in st[g]["rows"] and prow in st[g]["rows"]:
                    a_, b_ = st[g]["rows"].index(row), st[g]["rows"].index(prow)
                    for c in np.flatnonzero(never):
                        idn["every_eq_once"][0] += 1
                        idn["every_eq_once"][1] += int(not all(np.array_equal(st[g][x][a_, c], st[g][x][b_, c]) for x in ("V", "r", "H", "W")))
                    idn["fired_by_g"][0] += k
                    idn["fired_by_g"][1] += int((~never).sum())
say(f"P59c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {len(M['tasks'])} "
    f"tasks, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; {M['started_utc']} - "
    f"{M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h; {nraw} restored records, every sha256 equal to {SRC}'s "
    f"manifest; the acquisition rebuilt by ar001.sim.prepare (purpose {PURPOSE}; {KC} cases a task) equal to every record's")
say(f"  the injury schedule recomputed by the lead from its addresses ({n_sched} cases x {GS} generations; at most "
    f"{max_att} rejected attempts): every corner and attempt equal to the shard's; generation 0's patch and the {GS} "
    f"injured ones disjoint in every case")
say(f"  the packets at generation 0 rebuilt by the lead ({n_pk} label-tasks): every endpoint, U included, equal to the "
    f"stage's within {d0:.1e}")
say(f"  the successors re-scored by the lead from the saved states (own patch, the union of injured patches, whole sheet): "
    f"largest |difference| {dg:.1e}")
say(f"  identities: a vote row fired in {idn['vote_never'][1]} of {idn['vote_never'][0]} lineage-case-generations; a birth "
    f"cue at sigma 0 disagreed at birth in {idn['birth_cue_agrees'][1]} of {idn['birth_cue_agrees'][0]}; an injury check "
    f"failed in {idn['injury_ok'][1]} of {idn['injury_ok'][0]} injured branch-generations (the ceiling: "
    f"{idn['ceiling_uninjured'][1]} of {idn['ceiling_uninjured'][0]} records not 'no injury'); vtol-every that had not "
    f"yet fired differed from vtol-once's saved state in {idn['every_eq_once'][1]} of {idn['every_eq_once'][0]} "
    f"lineage-case-horizons (it had fired by then in {idn['fired_by_g'][1]} of {idn['fired_by_g'][0]})")
assert d0 < 1e-12 and dg < 1e-12
assert idn["vote_never"][1] == 0 and idn["birth_cue_agrees"][1] == 0 and idn["injury_ok"][1] == 0
assert idn["ceiling_uninjured"][1] == 0 and idn["every_eq_once"][1] == 0


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


# the registration's thresholds (REGISTRATION_E2E003.md with Amendment 1, the lead's ruling after P59's values and
# before any development value): eight parts at the rule's narrowest; the four misread nulls as equivalence bands
TH = {"J1a": ("least", 0.31), "J1b": ("least", 0.05), "J2a": ("least", 0.08), "J2b": ("band", (-0.04, 0.02)),
      "J3a": ("least", 0.28), "J3b": ("least", 0.04), "J3c": ("least", 0.06), "J3d": ("band", (-0.04, 0.03)),
      "J4a": ("band", (-0.02, 0.02)), "J4b": ("band", (-0.03, 0.01)), "J5a": ("band", (0.09, 0.25)),
      "J5b": ("band", (0.06, 0.13))}
D2 = lambda a, b, e: (lambda f: f(a, e, 8) - f(b, e, 8))
PARTS = [
    ("J1a", "U(vtol-every) - U(vote), memory@0, g 8", D2("vtol-every/memory@0", "vote/memory@0", "U")),
    ("J1b", "q_r(vtol-every) - q_r(vote), memory@0, g 8", D2("vtol-every/memory@0", "vote/memory@0", "q_r")),
    ("J2a", "U(vtol-every) - U(vote), memory@1, g 8", D2("vtol-every/memory@1", "vote/memory@1", "U")),
    ("J2b", "q_r(vtol-every) - q_r(vote), memory@1, g 8", D2("vtol-every/memory@1", "vote/memory@1", "q_r")),
    ("J3a", "U(vtol-every) - U(vtol-once), memory@0, g 8", D2("vtol-every/memory@0", "vtol-once/memory@0", "U")),
    ("J3b", "q_r(vtol-every) - q_r(vtol-once), memory@0, g 8", D2("vtol-every/memory@0", "vtol-once/memory@0", "q_r")),
    ("J3c", "U(vtol-every) - U(vtol-once), memory@1, g 8", D2("vtol-every/memory@1", "vtol-once/memory@1", "U")),
    ("J3d", "q_r(vtol-every) - q_r(vtol-once), memory@1, g 8", D2("vtol-every/memory@1", "vtol-once/memory@1", "q_r")),
    ("J4a", "U(vtol-every) - U(vms-every), memory@1, g 8", D2("vtol-every/memory@1", "vms-every/memory@1", "U")),
    ("J4b", "q_r(vtol-every) - q_r(vms-every), memory@1, g 8", D2("vtol-every/memory@1", "vms-every/memory@1", "q_r")),
    ("J5a", "U(uninjured) - U(vtol-every), memory@0, g 8", D2("uninjured", "vtol-every/memory@0", "U")),
    ("J5b", "q_r(uninjured) - q_r(vtol-every), memory@0, g 8", D2("uninjured", "vtol-every/memory@0", "q_r"))]
SETS = {"particular (li4 x F0)": {("li4", "F0_t0"), ("li4", "F0_t1")}, "native (li4 x S4)": {("li4", "S4_t0"), ("li4", "S4_t1")},
        "permissive (dw)": {("dw", u) for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")}}
full = lambda lab, e, g: X(lab, e, g)
sub_ = lambda sub: (lambda lab, e, g: X_sub(lab, e, g, sub))
say(f"\nTHE PARTS ({NB} blocks x {KC} cases; pooled over the eight unit-body pairs, one future; [95% t interval]"
    + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
Q, OK = {}, {}
for pid, words, fn in PARTS:
    try:
        x = fn(full)
    except (AssertionError, KeyError):
        say(f"  {pid} {words}: not available at this stage (its rows stop before its generation)")
        continue
    q = Q[pid] = est(x)
    line = (f"  {pid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
            f"case/sqrt{KC} {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
    kd, th = TH[pid]
    if STAGE == "probe":
        lo, hi = narrow_num(q)
        line += f"; the narrowest [{lo:+.3f}, {hi:+.3f}]"
        assert (lo, hi) == th if kd == "band" else abs(lo - th) < 1e-9, (pid, lo, hi, th)
    OK[pid] = (th[0] <= q["v"] <= th[1]) if kd == "band" else q["v"] >= th
    line += f"; registered {list(th) if kd == 'band' else '>= ' + str(th)}: {'HOLDS' if OK[pid] else 'FAILS'}"
    say(line)
    say("      by item set: " + "; ".join(f"{nm} {est(fn(sub_(sb)))['v']:+.6f}" for nm, sb in SETS.items()))
if OK:
    say("  VERDICTS (development: the point value against the registered threshold or band): "
        + ", ".join(f"{p} {'HOLDS' if v else 'FAILS'}" for p, v in OK.items())
        + ("" if STAGE == "development" else "  [not a development result]"))

say("\nREPORTED (the lead's): levels by label, U and q_r (all pairs; li4 x F0 in parentheses), with partial cells marked")
for lab in LABELS:
    cells = []
    for g in (0, 1, 3, 8):
        c = cover(lab, "U", g)
        if c == NB * len(PAIRS):
            cells.append(f"g{g} U {X(lab, 'U', g).mean():.4f} ({X_sub(lab, 'U', g, SETS['particular (li4 x F0)']).mean():.4f}) "
                         f"q_r {X(lab, 'q_r', g).mean():+.4f}")
        elif c:
            cells.append(f"g{g} PARTIAL ({c} of {NB * len(PAIRS)} tasks; not pooled)")
    say(f"  {lab} [{ROWINFO[lab]['policy']}, sigma {ROWINFO[lab]['sigma']}, injured {ROWINFO[lab]['injured']}]: " + "; ".join(cells))
say("  each generation's own patch at the end of that generation, u_r (generations 1-8):")
for lab in LABELS:
    gs = [g for g in range(1, G + 1) if cover(lab, "u_r", g) == NB * len(PAIRS)]
    say(f"    {lab}: " + " ".join(f"g{g} {X(lab, 'u_r', g).mean():.3f}" for g in gs))
say("  the controllers per generation: the share firing; of those, the share whose onset is update <= 1; median onset")
for lab in [l for l in LABELS if ROWINFO[l]["policy"] != "vote"]:
    cells = []
    for g in sorted(g_ for (l, g_) in FIRE if l == lab):
        fz_, on_ = FIRE[(lab, g)], ONSET[(lab, g)]
        if np.isnan(fz_).any():
            continue
        f_ = fz_.astype(bool)
        early = float((on_[f_] <= 1).mean()) if f_.any() else float("nan")
        med = float(np.median(on_[f_])) if f_.any() else float("nan")
        cells.append(f"g{g} {f_.mean():.3f}/{early:.3f}/{med:.0f}")
    say(f"    {lab}: " + " ".join(cells))

if READER is not None:
    rd = json.load(open(READER))
    assert rd["study"] == "E2E003" and rd["stage"] == STAGE and Path(rd["root"]).resolve() == ROOT.resolve(), "another run"
    if rd["design_digest"] != M["design_digest"]:
        assert STAGE != "development", "the reader's design is not the run's"
        say(f"\n  (the reader ran under design {rd['design_digest'][:12]}, the run under {M['design_digest'][:12]})")
    NAMES = {"native": SETS["native (li4 x S4)"], "particular": SETS["particular (li4 x F0)"],
             "permissive": SETS["permissive (dw)"]}
    FN = {p: f for p, _w, f in PARTS}
    worst, n_cmp, n_th = 0.0, 0, 0
    for rp in rd["parts"]:
        pid = rp["id"]
        if not rp["available"]:
            assert pid not in Q, pid
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
        if rp.get("threshold") is not None or STAGE == "development":
            kd, th = TH[pid]
            assert rp["kind"] == {"band": "in", "least": "ge"}[kd], (pid, rp["kind"])
            assert (list(rp["threshold"]) == list(th)) if kd == "band" else abs(rp["threshold"] - th) < 1e-12, (pid, rp["threshold"])
            assert rp["holds"] == OK[pid] and rd["verdicts"][pid] == ("HOLDS" if OK[pid] else "FAILS"), pid
            n_th += 1
        n_cmp += 1
    lw, nl, partial = 0.0, 0, []
    for kk, rec in rd["levels"].items():
        lab, e, g = kk.split("|")
        if g.startswith("d") or e not in ENDS:
            continue
        g = int(g)
        c = cover(lab, e, g)
        assert rec["tasks"] == c, (kk, rec["tasks"], c)
        if c < NB * len(PAIRS):
            partial.append(kk)
            continue
        lw = max(lw, abs(rec["all"] - float(X(lab, e, g).mean())))
        for nm, sb in NAMES.items():
            lw = max(lw, abs(rec[nm] - float(X_sub(lab, e, g, sb).mean())))
        nl += 1
    say(f"\nAGAINST THE FROZEN READER ({READER}): {n_cmp} parts (values, intervals, SDs, halves, blocks, item sets; "
        f"{n_th} registered thresholds, kinds and verdicts) largest difference {worst:.2e}; {nl} levels, largest "
        f"difference {lw:.2e}; partial levels (not pooled here): {len(partial)}")
    assert worst < 1e-12 and lw < 1e-12

name = f"p59c_e2e003_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
