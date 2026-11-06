"""P58c (python probes/p58c_e2e002_lead_check.py ROOT [READER]): the lead's check of E2E002, the policy acting in every
generation. LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved successor states and of the restored AR005
records, written by the lead in reviewing E2E002's phase A and committed before the freeze, dry-run first on P58
(AR005's P53 records, engineering blocks 900729, 900739 | 900749, 900759, parent 0's four cases, one future) and on the
debug run (900799, every row to generation 3); 4 November 2026; no simulation of the tissue. Adapted from P56c (E2E001).

It checks, from PLAN_E2E002.md's words (with its Amendment 1) and not from e2e002.sim, e2e002.predict, e2e002.checks or
e2e001.sim:
1. integrity: every stage file against its manifest by sha256, every restored record against its own run's manifest,
   the acquisition rebuilt by ar001.sim.prepare (the pilot's parent-0 subset where the stage reads it) equal to the
   record's V0, R0 and T; at the development stage the run's digest against e2e002/frozen/design.json;
2. the packets at generation 0, rebuilt by the lead from the restored files and the frozen functions: a policy arm's
   first record (r, H, W of its run; on P53, which ran no vms under none@0, the vote's none@0 record, as the shards
   name it); protected storage (R0 with its bonds, lr001.sim.edges_from(msegrid.core.bonds(R0, True))); post-damage
   copying (ar001.sim.event's record at sigma 0). Every label's generation-0 endpoints, scored by the lead with the
   arm's final body for a policy arm and the pre-injury body otherwise, must equal the stage's;
3. the successors: every endpoint at every saved horizon (1, 3, 8) re-scored by the lead from the saved states (V, r)
   and compared with the stage's;
4. the identities of the design:
   - a vote row (the "once" and passive lineages) never fires in any generation;
   - a birth cue at sigma 0 agrees with its incoming record at every anchor at birth, in every generation;
   - a lineage cue's disagreement at birth equals the lead's count, sign(R0) against the incoming record's signs at
     lr005.sim.anchor_mask's cells (generation 1 from the packet; generations 2 and 4 from the saved states at 1 and 3);
   - wherever a vms row never fired in generations 1..g, its saved state at g equals its vote partner's (the same
     packet; the vote-default identity carried through renewal) bit for bit (V, r, H, W);
5. the parts F1-F7 by the plan's words and Amendment 1: pooled per case over the eight unit-body pairs (one future), a
   block the mean of its cases, the part the mean over the blocks; SD = max(block SD, case SD / sqrt(cases a block));
   the 95% t interval; the development verdict the point value against the registered threshold or band; on P58 the
   margins (>= 3 sqrt(1/4 + 1/16)), both halves and the narrowest round thresholds (0.01 steps, 0.005 within 0.01 of
   zero), which must equal the registered ones;
6. reported: the levels (u_r and q_r) of every label at 0, 1, 3, 8 with their task counts, by item set (li4 x F0 first),
   the lineage cue against vms-every, and the firing per generation; with READER, the frozen reader's values.

The lead's scoring (the plan's endpoints, E2E001's): s = +1 where dl001.sim.sign(x, T) >= 0.5, else -1; u_r =
lr005.sim.inside(s r, T, m) with m the record's own 4 x 4 patch (be001.sim.patch under its tag); u_v the same for the
body; u_r_raw without s; a = max(sign, 1 - sign); q = (a - max over SR001's foreign placements of a) / 0.25; agree_in
the agreement of V and r inside the patch.
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
from ar001 import sim as A1S                                    # noqa: E402  (frozen: prepare, event)
from be001 import sim as B1S                                    # noqa: E402  (frozen: the patch)
from dl001 import sim as S                                      # noqa: E402  (frozen: sign)
from lr001.sim import edges_from                                # noqa: E402  (frozen)
from lr005 import sim as L5S                                    # noqa: E402  (frozen: inside, anchor_mask)
from msegrid.core import bonds                                  # noqa: E402  (frozen)
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
AR005_DEV = [910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798, 910799,
             910826, 910827, 910958]
WANT = {"probe": ("ar005/p53", [900729, 900739, 900749, 900759], "mse-p58", (0,)),
        "debug": ("ar005/debug", [900799], "mse-e2e002", (0, 1)),
        "preflight": ("ar005/preflight", [900779, 900789], "mse-e2e002", (0, 1)),
        "development": ("ar005/development", AR005_DEV, "mse-e2e002", (0, 1))}
SRC, BLOCKS, FTAG, PARENTS = WANT[STAGE]
SROOT = RUNS / SRC
NB = len(BLOCKS)
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert M["study"] == "E2E002" and not bad, bad[:5]
assert len(M["tasks"]) == len(PAIRS) * NB, len(M["tasks"])
SM = json.load(open(SROOT / "manifest.json"))
if STAGE == "development":
    fz = json.load(open(LANE / "e2e002" / "frozen" / "design.json"))
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
LABELS, KC = None, None
VAL = {}                     # (label, endpoint, g) -> (blocks, pairs, cases), NaN where the label's row did not run
FIRE = {}                    # (label, g) -> (blocks, pairs, cases) fired in generation g
ROWINFO = {}
d0 = dg = 0.0
n_pk = nraw = 0
idn = {"vote_never": [0, 0], "birth_cue_agrees": [0, 0], "lineage_cue_count": [0, 0], "every_eq_once": [0, 0],
       "fired_by_g": [0, 0]}
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
        purpose = "development" if STAGE == "development" else "engineering"
        cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, purpose)
        sel = [j for j, c in enumerate(cases) if c.parent in PARENTS]
        cases = [cases[j] for j in sel]
        V0, ema0, R0, T = (x[sel] for x in (V0, ema0, R0, T))
        raw = {k: (v[sel] if k in ("V0", "R0", "T") else v[:, sel]) for k, v in raw.items()}
        assert [list(c.key()) for c in cases] == [list(c) for c in meta["cases"]]
        assert np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"]) and np.array_equal(T, raw["T"])
        k = len(cases)
        KC = k if KC is None else KC
        assert k == KC
        tag = rmeta["tag"]
        m = B1S.patch(cases, 4, tag)
        Tf = SRS.foreign(T, pattern, cases)
        am = L5S.anchor_mask(cases, tag)
        arms_of = {name: list(a) for name, a in rmeta["runs"]}
        H0, W0 = edges_from(bonds(R0, True))
        labels, rows = meta["labels"], meta["rows"]
        if LABELS is None:
            LABELS = sorted(labels)
            ROWINFO = {lab: {x: rows[labels[lab]][x] for x in ("policy", "cue", "sigma")} for lab in LABELS}
        assert sorted(labels) == LABELS
        # 2. the packets and generation 0
        pkt = {}
        for lab, row in labels.items():
            src = meta["sources"][lab]
            if src == "protected":
                pk, Vb = (H0, W0, R0), V0
            elif src.startswith("post/"):
                ev = A1S.event("memory", 4, 0.0, cases, V0, ema0, R0, T, tag)
                assert np.array_equal(ev["m"], m) and src == "post/memory@0"
                pk, Vb = (ev["H"], ev["W"], ev["r"]), V0
            else:
                arm, sit = src.split("/")
                want = lab.split("/")[1] if "/" in lab else None
                assert sit == want, (lab, src)
                if arm != rows[row]["source"].split("/")[0] or arm not in arms_of[sit]:
                    raise AssertionError((lab, src, rows[row]["source"], arms_of[sit]))
                lab_arm = "vote" if lab.startswith("vote/") else "vms"
                assert arm == lab_arm or (arm == "vote" and lab_arm not in arms_of[sit]), (lab, src, arms_of[sit])
                j = arms_of[sit].index(arm)
                pk, Vb = (raw[f"{sit}/H"][j], raw[f"{sit}/W"][j], raw[f"{sit}/r"][j]), raw[f"{sit}/V"][j]
            pkt[lab] = pk
            sc = score(np.asarray(Vb, float), np.asarray(pk[2], float), T, Tf, m)
            for e in ENDS:
                d0 = max(d0, float(np.abs(sc[e] - z[f"g0/{e}"][row]).max()))
                VAL.setdefault((lab, e, 0), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"g0/{e}"][row]
            n_pk += 1
        # 3. the successors at every saved horizon
        st = {}
        for g in (1, 3, 8):
            if f"f0/g{g}/rows" not in z.files:
                continue
            rws = [int(x) for x in z[f"f0/g{g}/rows"]]
            assert rws == [int(x) for x in zr[f"f0/g{g}/rows"]]
            n = len(rws)
            st[g] = {x: zr[f"f0/g{g}/{x}"].reshape(n, k, *T.shape[1:]) for x in ("V", "r", "H", "W")}
            st[g]["rows"] = rws
            for p in range(n):
                sc = score(st[g]["V"][p], st[g]["r"][p], T, Tf, m)
                for e in ENDS:
                    dg = max(dg, float(np.abs(sc[e] - z[f"f0/g{g}/{e}"][p]).max()))
            for lab, row in labels.items():
                if row in rws:
                    for e in ENDS:
                        VAL.setdefault((lab, e, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"f0/g{g}/{e}"][rws.index(row)]
        # 4. the identities
        gens = sorted(int(x.split("/")[1][1:]) for x in z.files if x.startswith("f0/d") and x.endswith("/rows"))
        on_by = {}
        for g in gens:
            rws = [int(x) for x in z[f"f0/d{g}/rows"]]
            for lab, row in labels.items():
                if row not in rws:
                    continue
                p = rws.index(row)
                fired = z[f"f0/d{g}/det_on"][p] >= 0
                assert np.array_equal(fired, z[f"f0/d{g}/fired"][p] > 0), (lab, g)
                FIRE.setdefault((lab, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = fired
                on_by.setdefault(row, np.zeros(k, bool))
                if rows[row]["policy"] == "vote":
                    idn["vote_never"][0] += k
                    idn["vote_never"][1] += int(fired.sum())
                cd = z[f"f0/d{g}/cue_dis_birth"][p]
                if rows[row]["policy"] != "vote" and rows[row]["cue"] == "birth" and rows[row]["sigma"] == 0:
                    idn["birth_cue_agrees"][0] += k
                    idn["birth_cue_agrees"][1] += int((cd != 0).sum())
                if rows[row]["cue"] == "lineage" and rows[row]["sigma"] == 0 and rows[row]["policy"] != "vote":
                    r_in = pkt[lab][2] if g == 1 else (st[g - 1]["r"][st[g - 1]["rows"].index(row)]
                                                       if (g - 1) in st and row in st[g - 1]["rows"] else None)
                    if r_in is not None:
                        want = ((np.where(R0 > 0, 1, -1) != np.where(r_in > 0, 1, -1)) & am).sum((-2, -1))
                        idn["lineage_cue_count"][0] += k
                        idn["lineage_cue_count"][1] += int((want != cd).sum())
        # every = once where the vms row never fired (its vote partner: the same packet, the vote's policy)
        for lab, row in labels.items():
            if rows[row]["policy"] == "vote":
                continue
            partner = [l for l, r_ in labels.items() if rows[r_]["policy"] == "vote" and meta["sources"][l] == meta["sources"][lab]]
            if not partner:
                continue
            prow = labels[partner[0]]
            never = np.ones(k, bool)
            for g in gens:
                fz_ = FIRE.get((lab, g))
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
say(f"P58c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {len(M['tasks'])} "
    f"tasks, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; {M['started_utc']} - "
    f"{M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h; {nraw} restored records, every sha256 equal to {SRC}'s "
    f"manifest; the acquisition rebuilt by ar001.sim.prepare ({KC} cases a task) equal to every record's V0, R0 and T")
say(f"  the packets at generation 0 rebuilt by the lead ({n_pk} label-tasks; the policy arms from their runs, protected "
    f"storage from R0, post-damage copying from ar001.sim.event): every endpoint equal to the stage's within {d0:.1e}")
say(f"  the successors re-scored by the lead from the saved states at horizons 1, 3 and 8: largest |difference| {dg:.1e}")
say(f"  identities: a vote row fired in {idn['vote_never'][1]} of {idn['vote_never'][0]} lineage-case-generations; a birth "
    f"cue at sigma 0 disagreed with its incoming record at birth in {idn['birth_cue_agrees'][1]} of "
    f"{idn['birth_cue_agrees'][0]}; a lineage cue's count differed from the lead's in {idn['lineage_cue_count'][1]} of "
    f"{idn['lineage_cue_count'][0]}; a vms row that had not yet fired differed from its vote partner's saved state in "
    f"{idn['every_eq_once'][1]} of {idn['every_eq_once'][0]} lineage-case-horizons (it had fired by then in "
    f"{idn['fired_by_g'][1]} of {idn['fired_by_g'][0]})")
assert d0 < 1e-12 and dg < 1e-12
assert idn["vote_never"][1] == 0 and idn["birth_cue_agrees"][1] == 0 and idn["lineage_cue_count"][1] == 0
assert idn["every_eq_once"][1] == 0 and idn["every_eq_once"][0] > 0


def X(lab, e, g):
    """(blocks, cases): the mean over the pairs; the label's row must have run to g in every task."""
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
    st_ = lambda raw: 0.005 if abs(raw) <= 0.01 else 0.01
    lo = math.floor(round(lo_raw / st_(lo_raw), 9)) * st_(lo_raw)
    hi = math.ceil(round(hi_raw / st_(hi_raw), 9)) * st_(hi_raw)
    return round(lo, 3), round(hi, 3)


# the registration's thresholds (REGISTRATION_E2E002.md with Amendment 1, the lead's ruling after P58's values and
# before any development value): F1-F4 equivalence bands at the rule's narrowest; F5 the band; F6 at most 0.005 (P58
# does not support the fixed 0.002); F7 reported (SD 0 on P58)
TH = {"F1": ("band", (-0.005, 0.01)), "F2": ("band", (-0.01, 0.005)), "F3": ("band", (-0.01, 0.01)),
      "F4": ("band", (-0.005, 0.01)), "F5": ("band", (0.02, 0.25)), "F6": ("most", 0.005)}
PARTS = [
    ("F1", "u_r(vms-every) - u_r(vms-once), memory@0, g 8", lambda f, a: f("vms-every/memory@0", "u_r", 8, a) - f("vms-once/memory@0", "u_r", 8, a)),
    ("F2", "q_r(vms-every) - q_r(vms-once), memory@0, g 8", lambda f, a: f("vms-every/memory@0", "q_r", 8, a) - f("vms-once/memory@0", "q_r", 8, a)),
    ("F3", "q_r(protected+vms-every) - q_r(protected), g 8", lambda f, a: f("protected+vms-every", "q_r", 8, a) - f("protected", "q_r", 8, a)),
    ("F4", "u_r(protected+vms-every) - u_r(protected), g 8", lambda f, a: f("protected+vms-every", "u_r", 8, a) - f("protected", "u_r", 8, a)),
    ("F5", "u_r(protected) - u_r(vms-every), memory@0, g 8", lambda f, a: f("protected", "u_r", 8, a) - f("vms-every/memory@0", "u_r", 8, a)),
    ("F6", "a_r(vms-once) - a_r(vms-every), none@0, g 8", lambda f, a: f("vms-once/none@0", "a_r", 8, a) - f("vms-every/none@0", "a_r", 8, a)),
    ("F7", "u_r(vms-every) - u_r(vms-once), memory@0, g 1", lambda f, a: f("vms-every/memory@0", "u_r", 1, a) - f("vms-once/memory@0", "u_r", 1, a))]
SETS = {"particular (li4 x F0)": {("li4", "F0_t0"), ("li4", "F0_t1")}, "native (li4 x S4)": {("li4", "S4_t0"), ("li4", "S4_t1")},
        "permissive (dw)": {("dw", u) for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")}}
full = lambda lab, e, g, _a=None: X(lab, e, g)
sub_ = lambda sub: (lambda lab, e, g, _a=None: X_sub(lab, e, g, sub))
has8 = all(cover(l, "u_r", 8) == NB * len(PAIRS) for l in ("vms-every/memory@0", "vms-once/memory@0", "protected"))
say(f"\nTHE PARTS ({NB} blocks x {KC} cases; pooled over the eight unit-body pairs, one future; [95% t interval]"
    + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
Q, OK = {}, {}
for pid, words, fn in PARTS:
    try:
        x = fn(full, None)
    except (AssertionError, KeyError):
        say(f"  {pid} {words}: not available at this stage (its rows stop before its generation)")
        continue
    q = Q[pid] = est(x)
    line = (f"  {pid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
            f"case/sqrt{KC} {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
    if STAGE == "probe":
        lo, hi = narrow_num(q)
        line += f"; the narrowest [{lo:+.3f}, {hi:+.3f}]"
        if pid in TH:
            kd, th = TH[pid]
            assert (lo, hi) == th if kd == "band" else abs(hi - th) < 1e-9, (pid, lo, hi, th)
    if pid in TH:
        kd, th = TH[pid]
        OK[pid] = (th[0] <= q["v"] <= th[1]) if kd == "band" else q["v"] <= th
        line += f"; registered {list(th) if kd == 'band' else '<= ' + str(th)}: {'HOLDS' if OK[pid] else 'FAILS'}"
    else:
        line += "; reported"
    say(line)
    say("      by item set: " + "; ".join(f"{nm} {est(fn(sub_(sb), None))['v']:+.6f}" for nm, sb in SETS.items()))
if OK:
    say("  VERDICTS (development: the point value against the registered threshold): "
        + ", ".join(f"{p} {'HOLDS' if v else 'FAILS'}" for p, v in OK.items())
        + ("" if STAGE == "development" else "  [not a development result]"))

say("\nREPORTED (the lead's): levels by label (all pairs; li4 x F0), with the tasks covering each cell")
for lab in LABELS:
    cells = []
    for g in (0, 1, 3, 8):
        c = cover(lab, "u_r", g)
        if c == NB * len(PAIRS):
            cells.append(f"g{g} u_r {X(lab, 'u_r', g).mean():.4f} q_r {X(lab, 'q_r', g).mean():+.4f} "
                         f"({X_sub(lab, 'u_r', g, SETS['particular (li4 x F0)']).mean():.4f})")
        elif c:
            cells.append(f"g{g} PARTIAL ({c} of {NB * len(PAIRS)} tasks; not pooled)")
    say(f"  {lab} [{ROWINFO[lab]['policy']}, cue {ROWINFO[lab]['cue']}, sigma {ROWINFO[lab]['sigma']}]: " + "; ".join(cells))
if "vms-every+lineage-cue/memory@0" in LABELS:
    for g in (1, 3, 8):
        if cover("vms-every+lineage-cue/memory@0", "u_r", g) == NB * len(PAIRS):
            for e in ("u_r", "q_r"):
                xx = X("vms-every+lineage-cue/memory@0", e, g) - X("vms-every/memory@0", e, g)
                q = est(xx)
                say(f"  the lineage cue (a second channel) less vms-every, {e} g {g}: {q['v']:+.6f} [{q['lo']:+.6f}, "
                    f"{q['hi']:+.6f}]; li4 x F0 {X_sub('vms-every+lineage-cue/memory@0', e, g, SETS['particular (li4 x F0)']).mean() - X_sub('vms-every/memory@0', e, g, SETS['particular (li4 x F0)']).mean():+.6f}")
say("  the firing per generation (the share of lineage-cases that fired in that generation), vms rows:")
for lab in [l for l in LABELS if ROWINFO[l]["policy"] != "vote"]:
    gs = sorted(g for (l, g) in FIRE if l == lab)
    say(f"    {lab}: " + " ".join(f"g{g} {np.nanmean(FIRE[(lab, g)]):.3f}" for g in gs))
# the lead's extension after the development's results (4 November 2026, about 15:00Z; reported only, nothing registered
# or checked changed; git shows the diff): the detectors' footprint, zone and committed cells PER FIRING (over the
# lineage-cases that fired in that generation), and the footprint's share of the patch, from the shards' diagnostics;
# the frozen registration quoted P58's branch means (0 where vms never fired) as if per firing
if STAGE == "development":
    say("  per firing (over the lineage-cases that fired in that generation; g 1-8 pooled): footprint cells, zone cells, "
        "committed cells at the generation's end, the footprint's share of the patch")
    for lab in [l for l in LABELS if ROWINFO[l]["policy"] != "vote"]:
        acc = {x: [] for x in ("det_fp", "det_zone", "committed_end", "det_fp_in")}
        for pi, (body, unit) in enumerate(PAIRS):
            for bi, blk in enumerate(BLOCKS):
                z = np.load(ROOT / "shards" / key(SRC) / body / unit / f"{blk}.npz")
                meta = json.loads(str(z["__meta__"]))
                row = meta["labels"][lab]
                for g in range(1, 9):
                    if f"f0/d{g}/rows" not in z.files:
                        continue
                    rws = [int(x) for x in z[f"f0/d{g}/rows"]]
                    if row not in rws:
                        continue
                    p = rws.index(row)
                    f_ = z[f"f0/d{g}/det_on"][p] >= 0
                    for x in acc:
                        acc[x].extend(np.asarray(z[f"f0/d{g}/{x}"][p], float)[f_].tolist())
        n_f = len(acc["det_fp"])
        say(f"    {lab}: {n_f} firings; footprint {np.mean(acc['det_fp']):.1f}, zone {np.mean(acc['det_zone']):.1f}, "
            f"committed {np.mean(acc['committed_end']):.2f}, share of the patch {np.mean(acc['det_fp_in']):.3f}")

if READER is not None:
    rd = json.load(open(READER))
    assert rd["study"] == "E2E002" and rd["stage"] == STAGE and Path(rd["root"]).resolve() == ROOT.resolve(), "another run"
    if rd["design_digest"] != M["design_digest"]:                # a dry run read under a later (amended) design
        assert STAGE != "development", "the reader's design is not the run's"
        say(f"\n  (the reader ran under design {rd['design_digest'][:12]}, the run under {M['design_digest'][:12]}: an "
            f"engineering stage read again after an amendment)")
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
            worst = max(worst, abs(rp["by_item_set"][nm]["value"] - est(FN[pid](sub_(sb), None))["v"]))
        if rp.get("threshold") is not None or STAGE == "development":
            kd, th = TH.get(pid, (None, None))
            if kd is None:
                assert rp.get("threshold") is None, (pid, rp.get("threshold"))
            else:
                assert rp["kind"] == {"band": "in", "most": "le"}[kd], (pid, rp["kind"])
                assert (list(rp["threshold"]) == list(th)) if kd == "band" else abs(rp["threshold"] - th) < 1e-12, (pid, rp["threshold"])
                assert rp["holds"] == OK[pid] and rd["verdicts"][pid] == ("HOLDS" if OK[pid] else "FAILS"), pid
                n_th += 1
        n_cmp += 1
    lw, nl, partial, nfire = 0.0, 0, [], 0
    for kk, rec in rd["levels"].items():
        lab, e, g = kk.split("|")
        if g.startswith("d"):
            if e == "fired" and (lab, int(g[1:])) in FIRE:
                fz_ = FIRE[(lab, int(g[1:]))]
                if not np.isnan(fz_).any():
                    lw = max(lw, abs(rec["all"] - float(fz_.mean())))
                    nfire += 1
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
        f"{n_th} registered thresholds, kinds and verdicts) largest difference {worst:.2e}; {nl} levels and {nfire} firing "
        f"shares by generation, largest difference {lw:.2e}; partial levels (not pooled here): {len(partial)}"
        + (f" ({', '.join(partial[:6])}{', ...' if len(partial) > 6 else ''})" if partial else ""))
    assert worst < 1e-12 and lw < 1e-12

name = f"p58c_e2e002_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
