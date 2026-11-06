"""P62c (python probes/p62c_e2e005_lead_check.py ROOT [READER]): the lead's check of E2E005, a controller over the keeping
rule. LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved successor states and of the restored AR005 records,
written by the lead in reviewing E2E005's phase A and committed before the freeze, dry-run first on P62 (AR005's P53
records, parent 0's four cases) and on the debug run (900799, rows to g 3); 5 November 2026; no simulation of the tissue.
Adapted from P60c (E2E004), whose integrity, packet and re-scoring sections it keeps.

It checks, from PLAN_E2E005.md's words and not from e2e005.sim, e2e005.predict, e2e005.checks, e2e004.sim, e2e002.sim or
e2e001.sim:
1. integrity, every label's rule and packet against the plan's table, every generation-0 packet rebuilt and scored, every
   successor endpoint re-scored from the saved states at generations 1, 3 and 8 (P60c's sections, unchanged);
2. the controller's identity: wherever it has not fired in generations 1..g, its saved state at g equals the record
   rule's on the same packet bit for bit (V, r, H, W), its default being the record rule;
3. the parts C1-C3 by the plan's words (pooled per case over the eight pairs, a block the mean of its cases, the part the
   mean over the blocks, SD = max(block SD, case SD / sqrt(cases a block)), the 95% t interval) against the registered
   thresholds; C4, the frontier excess F = H_ctl - h(K_ctl), each block's from its own points, h the upper boundary of
   the convex hull of the record's, vote's and body's (K, H) points with free disposal (computed by the lead over every
   single rule and every two-rule mixture), reported;
4. reported: the (K, H) points of every rule and the oracle; F_RB against the record-body chord; the firing share, the
   ever-fired share and the footprint's share of the patch per firing, by generation and item set (li4 x F0 first);
5. on P62 the narrowest thresholds the rule allows equal the registered ones; with READER, the frozen reader's parts,
   thresholds, verdicts, levels and frontier points.
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
from lr005 import sim as L5S                                    # noqa: E402  (frozen: inside)
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
WANT = {"probe": ("ar005/p53", [900729, 900739, 900749, 900759], "mse-p62", (0,)),
        "debug": ("ar005/debug", [900799], "mse-e2e005", (0, 1)),
        "preflight": ("ar005/preflight", [900779, 900789], "mse-e2e005", (0, 1)),
        "development": ("ar005/development", AR005_DEV, "mse-e2e005", (0, 1))}
SRC, BLOCKS, FTAG, PARENTS = WANT[STAGE]
SROOT = RUNS / SRC
NB = len(BLOCKS)
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert M["study"] == "E2E005" and not bad, bad[:5]
assert len(M["tasks"]) == len(PAIRS) * NB, len(M["tasks"])
SM = json.load(open(SROOT / "manifest.json"))
if STAGE == "development":
    fz = json.load(open(LANE / "e2e005" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"
# the plan's lineage table: label -> (route, generation-0 packet); ctl the controller, oracle its patch-located twin
PLAN = {f"{r}/{p}": (r, src) for r in ("ctl", "record", "body", "vote", "oracle") for p, src in
        (("protected", "protected"), ("post", "post/memory@0"), ("vms", "vms/memory@0"))}


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
STATES, DIAG, META, PATCH = {}, {}, {}, {}
VAL = {}                     # (label, endpoint, g) -> (blocks, pairs, cases), NaN where the label's row did not run
ROUTE = {}
d0 = dg = 0.0
n_pk = nraw = n_states = 0
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
        arms_of = {name: list(a) for name, a in rmeta["runs"]}
        H0, W0 = edges_from(bonds(R0, True))
        labels, rows = meta["labels"], meta["rows"]
        META[(bi, pi)] = (labels, rows, k)
        PATCH[(bi, pi)] = m.sum((-2, -1)).astype(float)
        for gd in range(1, 9):
            if f"f0/d{gd}/rows" in z.files:
                DIAG[(bi, pi, gd)] = {x.split("/")[-1]: z[x] for x in z.files if x.startswith(f"f0/d{gd}/")}
        if LABELS is None:
            LABELS = sorted(labels)
        assert sorted(labels) == LABELS
        for lab, row in labels.items():
            rt, src = PLAN[lab]
            assert rows[row]["route"] == rt and meta["sources"][lab] == src, (lab, rows[row], meta["sources"][lab])
            ROUTE[lab] = rt
            if src == "protected":
                pk, Vb = (H0, W0, R0), V0
            elif src == "post/memory@0":
                ev = A1S.event("memory", 4, 0.0, cases, V0, ema0, R0, T, tag)
                assert np.array_equal(ev["m"], m)
                assert np.array_equal(ev["r"][~m], R0[~m]) and np.array_equal(ev["r"][m], -R0[m])
                pk, Vb = (ev["H"], ev["W"], ev["r"]), V0
            else:
                arm, sit = src.split("/")
                j = arms_of[sit].index(arm)
                pk, Vb = (raw[f"{sit}/H"][j], raw[f"{sit}/W"][j], raw[f"{sit}/r"][j]), raw[f"{sit}/V"][j]
            sc = score(np.asarray(Vb, float), np.asarray(pk[2], float), T, Tf, m)
            for e in ENDS:
                d0 = max(d0, float(np.abs(sc[e] - z[f"g0/{e}"][row]).max()))
                VAL.setdefault((lab, e, 0), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"g0/{e}"][row]
            n_pk += 1
        for g in (1, 3, 8):
            if f"f0/g{g}/rows" not in z.files:
                continue
            rws = [int(x) for x in z[f"f0/g{g}/rows"]]
            assert rws == [int(x) for x in zr[f"f0/g{g}/rows"]]
            n = len(rws)
            Vg = zr[f"f0/g{g}/V"].reshape(n, k, *T.shape[1:])
            rg = zr[f"f0/g{g}/r"].reshape(n, k, *T.shape[1:])
            STATES[(bi, pi, g)] = {"rows": rws, "V": Vg, "r": rg, "H": zr[f"f0/g{g}/H"].reshape(n, k, *T.shape[1:]),
                                   "W": zr[f"f0/g{g}/W"].reshape(n, k, *T.shape[1:])}
            for p in range(n):
                sc = score(Vg[p], rg[p], T, Tf, m)
                for e in ENDS:
                    dg = max(dg, float(np.abs(sc[e] - z[f"f0/g{g}/{e}"][p]).max()))
                n_states += 1
            for lab, row in labels.items():
                if row in rws:
                    for e in ENDS:
                        VAL.setdefault((lab, e, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"f0/g{g}/{e}"][rws.index(row)]
say(f"P62c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {len(M['tasks'])} "
    f"tasks, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; {M['started_utc']} - "
    f"{M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h; {nraw} restored records, every sha256 equal to {SRC}'s "
    f"manifest; the acquisition rebuilt by ar001.sim.prepare ({KC} cases a task) equal to every record's V0, R0 and T")
say(f"  the labels: every rule and packet as the plan's table ({', '.join(LABELS)})")
say(f"  the packets at generation 0 rebuilt by the lead ({n_pk} label-tasks): every endpoint equal to the stage's within {d0:.1e}")
say(f"  the successors re-scored by the lead from the saved states at horizons 1, 3 and 8 ({n_states} row-task-horizons): "
    f"largest |difference| {dg:.1e}")
assert d0 < 1e-12 and dg < 1e-12

# ------------------------------------------------------------------- the controller's identity and its firing
idn = [0, 0]
FIRED = {}                  # (label, g) -> (blocks, pairs, cases) fired in generation g; FPIN the footprint's share of
#                             the patch (fp_in, a count of cells, over the patch's cells), NaN where it did not fire
FPIN, FPC, BND = {}, {}, {}           # the patch share, the footprint's cells and the open bonds, per firing
for (bi, pi), (labels, rows, k) in META.items():
    for lab in [l for l in labels if l.startswith(("ctl/", "oracle/"))]:
        row = labels[lab]
        partner = "record/" + lab.split("/", 1)[1]
        # the identity is the controller's (its default is the record rule); the oracle's firing is only tabulated
        prow = labels[partner] if (lab.startswith("ctl/") and partner in labels) else None
        never = np.ones(k, bool)
        for g in range(1, 9):
            d = DIAG.get((bi, pi, g))
            if d is None or row not in [int(x) for x in d["rows"]]:
                break
            p_ = [int(x) for x in d["rows"]].index(row)
            fired = np.asarray(d["fired"][p_]) > 0
            FIRED.setdefault((lab, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = fired
            FPIN.setdefault((lab, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = np.where(
                fired, np.asarray(d["fp_in"][p_], float) / PATCH[(bi, pi)], np.nan)
            FPC.setdefault((lab, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = np.where(fired, np.asarray(d["fp"][p_], float), np.nan)
            if "bonds" in d:
                BND.setdefault((lab, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = np.where(fired, np.asarray(d["bonds"][p_], float), np.nan)
            never &= ~fired
            st = STATES.get((bi, pi, g))
            if prow is not None and st is not None and row in st["rows"] and prow in st["rows"]:
                a_, b_ = st["rows"].index(row), st["rows"].index(prow)
                for c in np.flatnonzero(never):
                    idn[0] += 1
                    idn[1] += int(not all(np.array_equal(st[x][a_, c], st[x][b_, c]) for x in ("V", "r", "H", "W")))
say(f"  the controller's identity: where it had not yet fired, its saved state equals the record rule's on the same packet "
    f"in {idn[0] - idn[1]} of {idn[0]} lineage-case-horizons")
assert idn[1] == 0 and idn[0] > 0


def X(lab, e, g):
    a = VAL[(lab, e, g)]
    assert not np.isnan(a).any(), (lab, e, g)
    return a.mean(axis=1)


def X_sub(lab, e, g, sub):
    a = VAL[(lab, e, g)]
    ix = [i for i, p in enumerate(PAIRS) if p in sub]
    return a[:, ix].mean(axis=1)


K = 3 * math.sqrt(1 / 4 + 1 / 16)
T975 = stats.t.ppf(0.975, NB - 1) if NB > 1 else float("nan")


def est(x):
    blk = x.mean(1)
    v = float(blk.mean())
    sdc = float(x.ravel().std(ddof=1)) / math.sqrt(x.shape[1]) if x.shape[1] > 1 else (float(blk.std(ddof=1)) if NB > 1 else 0.0)
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


def h_line(Kq, pts):
    """The fixed rules' line at keeping Kq: the largest healing any rule or two-rule mixture reaches keeping >= Kq; above
    every rule's keeping, the most-keeping rule's healing (the plan's convention)."""
    best = -np.inf
    for (k1, h1) in pts:
        if k1 >= Kq:
            best = max(best, h1)
        for (k2, h2) in pts:
            if k1 < Kq <= k2 and k2 > k1:          # the mixture of rule 1 and rule 2 that keeps exactly Kq
                best = max(best, h1 + (h2 - h1) * (Kq - k1) / (k2 - k1))
    if best == -np.inf:
        best = max(pts, key=lambda p: p[0])[1]
    return best


def frontier_blocks(g=8, sub=None):
    """(blocks, 1): F per block from the block's own points; also F_RB against the record-body chord."""
    fx = (lambda l, e: X(l, e, g).mean(1)) if sub is None else (lambda l, e: X_sub(l, e, g, sub).mean(1))
    pts = {r: (fx(f"{r}/protected", "q_r"), fx(f"{r}/post", "u_r")) for r in ("record", "vote", "body", "ctl")}
    F, FRB = [], []
    for b in range(NB):
        P = [(pts[r][0][b], pts[r][1][b]) for r in ("record", "vote", "body")]
        Kc, Hc = pts["ctl"][0][b], pts["ctl"][1][b]
        F.append(Hc - h_line(Kc, P))
        FRB.append(Hc - h_line(Kc, [P[0], P[2]]))
    return np.array(F)[:, None], np.array(FRB)[:, None], pts


TH = {"C1": ("least", 0.06), "C2": ("band", (-0.08, -0.02)), "C3": ("least", 0.40)}
D2 = lambda a, b, e: (lambda f: f(a, e, 8) - f(b, e, 8))
PARTS = [("C1", "u_r(ctl/post) - u_r(record/post), g 8: the controller heals more than the record rule", D2("ctl/post", "record/post", "u_r")),
         ("C2", "q_r(ctl/protected) - q_r(record/protected), g 8: the controller's keeping against the record rule's", D2("ctl/protected", "record/protected", "q_r")),
         ("C3", "q_r(ctl/protected) - q_r(body/protected), g 8: the controller keeps more than the body rule", D2("ctl/protected", "body/protected", "q_r"))]
SETS = {"particular (li4 x F0)": {("li4", "F0_t0"), ("li4", "F0_t1")}, "native (li4 x S4)": {("li4", "S4_t0"), ("li4", "S4_t1")},
        "permissive (dw)": {("dw", u) for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")}}
have8 = all((f"{r}/{p}", "q_r", 8) in VAL for r in ("ctl", "record", "body", "vote") for p in ("protected", "post"))
say(f"\nTHE PARTS ({NB} blocks x {KC} cases; pooled over the eight unit-body pairs, one future; [95% t interval]"
    + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
Q, OK = {}, {}
for pid, words, fn in PARTS:
    try:
        x = fn(lambda l, e, g: X(l, e, g))
    except (AssertionError, KeyError):
        say(f"  {pid} {words}: not available at this stage")
        continue
    q = Q[pid] = est(x)
    kd, th = TH[pid]
    line = (f"  {pid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
            f"case/sqrt{KC} {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
    if STAGE == "probe":
        lo, hi = narrow_num(q)
        line += f"; the narrowest [{lo:+.3f}, {hi:+.3f}]"
        assert ((lo, hi) == th) if kd == "band" else abs(lo - th) < 1e-9, (pid, lo, hi, th)
    OK[pid] = (th[0] <= q["v"] <= th[1]) if kd == "band" else q["v"] >= th
    line += f"; registered {list(th) if kd == 'band' else '>= ' + str(th)}: {'HOLDS' if OK[pid] else 'FAILS'}"
    say(line)
    say("      by item set: " + "; ".join(f"{nm} {est(fn(lambda l, e, g, sb=sb: X_sub(l, e, g, sb)))['v']:+.6f}" for nm, sb in SETS.items()))
if have8:
    Fb, FRBb, pts = frontier_blocks()
    q = Q["C4"] = est(Fb)
    lo, hi = narrow_num(q)
    say(f"  C4 F = u_r(ctl/post) - h(q_r(ctl/protected)), g 8, each block's from its own points (reported): {q['v']:+.6f} "
        f"[{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f}); the "
        f"narrowest lower bound {lo:+.3f}: {'registers' if lo > 0 else 'does not register (reported)'}")
    say("      by item set: " + "; ".join(f"{nm} {est(frontier_blocks(sub=sb)[0])['v']:+.6f}" for nm, sb in SETS.items()))
    qr = est(FRBb)
    say(f"      F_RB against the record-body chord: {qr['v']:+.6f} [{qr['lo']:+.6f}, {qr['hi']:+.6f}]")
if OK:
    say("  VERDICTS (development: the point value against the registered threshold or band): "
        + ", ".join(f"{p} {'HOLDS' if v else 'FAILS'}" for p, v in OK.items()) + "; C4 reported"
        + ("" if STAGE == "development" else "  [not a development result]"))

say("\nREPORTED (the lead's): the (keeping, healing) points at g 8 (all pairs; li4 x F0)")
if have8:
    for r in ("record", "vote", "body", "ctl"):
        say(f"  {r}: K {X(f'{r}/protected', 'q_r', 8).mean():.4f} ({X_sub(f'{r}/protected', 'q_r', 8, SETS['particular (li4 x F0)']).mean():.4f}), "
            f"H {X(f'{r}/post', 'u_r', 8).mean():.4f} ({X_sub(f'{r}/post', 'u_r', 8, SETS['particular (li4 x F0)']).mean():.4f})")
    if ("oracle/post", "u_r", 8) in VAL:
        say(f"  oracle: H {X('oracle/post', 'u_r', 8).mean():.4f} ({X_sub('oracle/post', 'u_r', 8, SETS['particular (li4 x F0)']).mean():.4f})")
say("  the controller's firing by generation: the share firing / the ever-fired share by then / the footprint's mean share "
    "of the patch per firing (li4 x F0: the share firing / the patch share)")
RSET = {"all": None, "particular": SETS["particular (li4 x F0)"], "native": SETS["native (li4 x S4)"],
        "permissive": SETS["permissive (dw)"]}
FIRE = {}                    # (label, set, g) -> (share firing, ever-fired share, the patch share per firing)
for lab in sorted({l for (l, g) in FIRED}):
    for sn, sub in RSET.items():
        ix = [i for i, p in enumerate(PAIRS) if sub is None or p in sub]
        ever = None
        for g in sorted(g_ for (l, g_) in FIRED if l == lab):
            f_ = FIRED[(lab, g)][:, ix]
            if np.isnan(f_).any():
                break
            ever = f_.astype(bool) if ever is None else (ever | f_.astype(bool))
            fp = FPIN[(lab, g)][:, ix]
            FIRE[(lab, sn, g)] = (float(f_.mean()), float(ever.mean()),
                                  float(np.nanmean(fp)) if np.isfinite(fp).any() else float("nan"))
    cells = [f"g{g} {FIRE[(lab, 'all', g)][0]:.3f}/{FIRE[(lab, 'all', g)][1]:.3f}/{FIRE[(lab, 'all', g)][2]:.3f} "
             f"({FIRE[(lab, 'particular', g)][0]:.3f}/{FIRE[(lab, 'particular', g)][2]:.3f})"
             for g in range(1, 9) if (lab, "all", g) in FIRE]
    say(f"    {lab}: " + " ".join(cells))

if READER is not None:
    rd = json.load(open(READER))
    assert rd["study"] == "E2E005" and rd["stage"] == STAGE and Path(rd["root"]).resolve() == ROOT.resolve(), "another run"
    if rd["design_digest"] != M["design_digest"]:
        assert STAGE != "development", "the reader's design is not the run's"
        say(f"\n  (the reader ran under design {rd['design_digest'][:12]}, the run under {M['design_digest'][:12]})")
    worst, n_cmp, n_th = 0.0, 0, 0
    for rp in rd["parts"]:
        pid = rp["id"]
        if not rp.get("available", True) or pid not in Q:
            continue
        q = Q[pid]
        for a, b in (("value", q["v"]), ("sd", q["sd"])):
            worst = max(worst, abs(rp[a] - b))
        worst = max(worst, max(abs(x - y) for x, y in zip(rp["blocks"], q["blocks"])))
        if NB > 1:
            worst = max(worst, abs(rp["ci95"][0] - q["lo"]), abs(rp["ci95"][1] - q["hi"]),
                        max(abs(x - y) for x, y in zip(rp["halves"], q["halves"])))
        if pid in TH and (rp.get("threshold") is not None or STAGE == "development"):
            kd, th = TH[pid]
            assert (list(rp["threshold"]) == list(th)) if kd == "band" else abs(rp["threshold"] - th) < 1e-12, (pid, rp["threshold"])
            assert rp["holds"] == OK[pid] and rd["verdicts"][pid] == ("HOLDS" if OK[pid] else "FAILS"), pid
            n_th += 1
        n_cmp += 1
    lw, nl, nl_eq = 0.0, 0, 0
    for kk, rec in rd["levels"].items():
        lab, e, g = kk.split("|")
        if g.startswith("d") or e not in ENDS:
            continue
        g = int(g)
        if (lab, e, g) not in VAL or np.isnan(VAL[(lab, e, g)]).any():
            continue
        for sn, sub in RSET.items():
            if sn not in rec:
                continue
            mine = float(X(lab, e, g).mean()) if sub is None else float(X_sub(lab, e, g, sub).mean())
            lw = max(lw, abs(rec[sn] - mine))
            nl += 1
            nl_eq += int(round(mine, 5) == rec[sn])
    fw, nf = 0.0, 0
    FBY = {}
    for gs, fr in rd.get("frontier", {}).items():
        g = int(gs)
        for sn, sub in RSET.items():
            rec = fr.get(sn)
            if not rec or not rec.get("available") or (("ctl/post", "u_r", g) not in VAL):
                continue
            fx = (lambda l, e: X(l, e, g).mean()) if sub is None else (lambda l, e: X_sub(l, e, g, sub).mean())
            pts = {r: (fx(f"{r}/protected", "q_r"), fx(f"{r}/post", "u_r")) for r in ("record", "vote", "body", "ctl")}
            if ("oracle/post", "u_r", g) in VAL:
                pts["oracle"] = (pts["record"][0], fx("oracle/post", "u_r"))
            for r, (kq, hq) in pts.items():
                fw = max(fw, abs(rec["points"][r][0] - kq), abs(rec["points"][r][1] - hq))
            P3 = [pts[r] for r in ("record", "vote", "body")]
            line = h_line(pts["ctl"][0], P3)
            fw = max(fw, abs(rec["line_at_ctl_keep"] - line), abs(rec["F_at_pooled"] - (pts["ctl"][1] - line)),
                     abs(rec["F_RB_at_pooled"] - (pts["ctl"][1] - h_line(pts["ctl"][0], [P3[0], P3[2]]))))
            if "F_blocks_mean" in rec:          # every horizon the reader gives (extended after the results: g 1 and 3)
                fb_ = frontier_blocks(g=g, sub=sub)
                fw = max(fw, abs(rec["F_blocks_mean"] - est(fb_[0])["v"]), abs(rec["F_RB_blocks_mean"] - est(fb_[1])["v"]))
                if sn in ("all", "particular"):
                    qf = est(fb_[0])
                    FBY[(g, sn)] = qf
            nf += 1
    rw, nr = 0.0, 0
    for kk, rec in rd.get("firing", {}).items():
        lab, sn, gs = kk.split("|")
        if (lab, sn, int(gs)) not in FIRE:
            continue
        sh, ev, pc = FIRE[(lab, sn, int(gs))]
        rw = max(rw, abs(rec["share"] - sh), abs(rec["ever_by_g"] - ev),
                 0.0 if (np.isnan(pc) and rec.get("patch_covered") is None) else abs(rec["patch_covered"] - pc))
        nr += 1
    # extended after the results (5 November, disclosed): every reported contrast "e(A) - e(B), g N" and every per-firing
    # cost, recomputed by the plan's pooling from the lead's own values
    import re as _re
    PATR = _re.compile(r"^(\w+)\(([\w/]+)\) - (\w+)\(([\w/]+)\), g (\d)")
    NM = {"native": SETS["native (li4 x S4)"], "particular": SETS["particular (li4 x F0)"], "permissive": SETS["permissive (dw)"]}
    rpw, nrp, skipped = 0.0, 0, []
    REPV = {}
    for it in rd.get("reported", []):
        mt = PATR.match(it.get("part", ""))
        if not mt or mt.group(1) != mt.group(3) or not it.get("available", True):
            skipped.append(it.get("id"))
            continue
        e_, la, lb, g_ = mt.group(1), mt.group(2), mt.group(4), int(mt.group(5))
        if (la, e_, g_) not in VAL or (lb, e_, g_) not in VAL:
            skipped.append(it.get("id"))
            continue
        q_ = est(X(la, e_, g_) - X(lb, e_, g_))
        REPV[it["id"]] = q_
        rpw = max(rpw, abs(it["value"] - q_["v"]))
        if NB > 1:
            rpw = max(rpw, abs(it["ci95"][0] - q_["lo"]), abs(it["ci95"][1] - q_["hi"]), abs(it["sd"] - q_["sd"]))
        if "blocks" in it:
            rpw = max(rpw, max(abs(x - y) for x, y in zip(it["blocks"], q_["blocks"])))
        if "halves" in it and NB > 1:
            rpw = max(rpw, max(abs(x - y) for x, y in zip(it["halves"], q_["halves"])))
        for nm_, sb in NM.items():
            bis = (it.get("by_item_set") or {}).get(nm_)
            if bis is not None:
                v_ = bis["value"] if isinstance(bis, dict) else bis
                rpw = max(rpw, abs(v_ - est(X_sub(la, e_, g_, sb) - X_sub(lb, e_, g_, sb))["v"]))
        nrp += 1
    pfw, npf = 0.0, 0
    for kk, rec in rd.get("per_firing_costs", {}).items():
        lab_c, e_, gs, sn = kk.split("|")
        g_ = int(gs)
        lab_r = "record/" + lab_c.split("/", 1)[1]
        if (lab_c, e_, g_) not in VAL or (lab_r, e_, g_) not in VAL:      # a horizon the stage's rows do not reach
            assert rec["mean_over_fired"] is None and rec["lineage_cases"] == 0, (kk, rec)
            continue
        ix = [i for i, p_ in enumerate(PAIRS) if RSET[sn] is None or p_ in RSET[sn]]
        ever = np.zeros(VAL[(lab_c, e_, g_)][:, ix].shape, bool)
        for gg in range(1, g_ + 1):
            ever |= FIRED[(lab_c, gg)][:, ix].astype(bool)
        d_ = (VAL[(lab_c, e_, g_)] - VAL[(lab_r, e_, g_)])[:, ix]
        assert rec["lineage_cases"] == d_.size and rec["fired_by_g"] == int(ever.sum()), (kk, rec, d_.size, int(ever.sum()))
        mine = float(d_[ever].mean()) if ever.any() else None
        if mine is None:
            assert rec["mean_over_fired"] is None, kk
        else:
            pfw = max(pfw, abs(rec["mean_over_fired"] - mine))
        npf += 1
    # the per-firing footprint pooled over generations 1-8 (the reader's frontier 'beside' block) and the open bonds
    bw, nb_ = 0.0, 0
    OPEN = {}
    for sn, sub in RSET.items():
        ix = [i for i, p_ in enumerate(PAIRS) if sub is None or p_ in sub]
        for pk in ("post", "protected"):
            lab = f"ctl/{pk}"
            gs_ = [g_ for g_ in range(1, 9) if (lab, g_) in FPC]
            fp_ = np.concatenate([FPC[(lab, g_)][:, ix].ravel() for g_ in gs_])
            pin = np.concatenate([FPIN[(lab, g_)][:, ix].ravel() for g_ in gs_])
            ok_ = ~np.isnan(fp_)
            rec = rd.get("frontier", {}).get("8", {}).get(sn, {}).get("beside", {}).get(pk)
            if rec is not None:
                assert rec["firings"] == int(ok_.sum()), (sn, pk, rec["firings"], int(ok_.sum()))
                bw = max(bw, abs(rec["footprint"] - float(fp_[ok_].mean())), abs(rec["patch_covered"] - float(pin[ok_].mean())),
                         abs(rec["outside_patch"] - float((fp_[ok_] - pin[ok_] * 16).mean())))
                nb_ += 1
            if all((lab, g_) in BND for g_ in gs_):
                bd = np.concatenate([BND[(lab, g_)][:, ix].ravel() for g_ in gs_])
                OPEN[(sn, pk)] = (float(np.nanmean(bd)), float(fp_[ok_].mean()), float(pin[ok_].mean()), int(ok_.sum()))
    for kk, rec in rd.get("firing", {}).items():
        lab, sn, gs = kk.split("|")
        if (lab, int(gs)) in BND and rec.get("open_bonds") is not None:
            ix = [i for i, p_ in enumerate(PAIRS) if RSET[sn] is None or p_ in RSET[sn]]
            bw = max(bw, abs(rec["open_bonds"] - float(np.nanmean(BND[(lab, int(gs))][:, ix]))))
            nb_ += 1
    say(f"  the footprints per firing (pooled over generations 1-8, and the open bonds by generation): {nb_} readings, "
        f"largest difference {bw:.2e}")
    assert bw < 1e-9
    for (sn, pk), (ob, fpm, pcm, nf_) in OPEN.items():
        say(f"    ctl/{pk} {sn}: {nf_} firings; per firing {fpm:.1f} footprint cells, {pcm:.3f} of the patch, {ob:.1f} open bonds")
    say(f"\n  the reader's reported items (extended after the results): {nrp} contrasts (values, intervals, SDs, blocks, item sets) "
        f"and {npf} per-firing costs (counts and means) recomputed by the lead, largest differences {rpw:.2e} and {pfw:.2e}"
        + (f"; not recomputed: {', '.join(map(str, skipped))}" if skipped else ""))
    assert rpw < 1e-12 and pfw < 1e-12 and nrp > 0 and npf > 0
    say("  F (each block's from its own points) by horizon: " + "; ".join(
        f"g {g_} {sn_} {q_['v']:+.4f} [{q_['lo']:+.4f}, {q_['hi']:+.4f}]" for (g_, sn_), q_ in sorted(FBY.items())))
    for rid in ("R-oracle-b-u_r-8", "R-oracle-c-u_r-8", "R-oracle-r-u_r-8", "R-oracle-b-q_r-8", "R-heal-cv-u_r-8", "R-keep-cv-q_r-8"):
        if rid in REPV:
            q_ = REPV[rid]
            say(f"    {rid}: {q_['v']:+.4f} [{q_['lo']:+.4f}, {q_['hi']:+.4f}]")
    say(f"\nAGAINST THE FROZEN READER ({READER}): {n_cmp} parts (C4 included; values, intervals, SDs, halves, blocks; {n_th} "
        f"thresholds and verdicts) largest difference {worst:.2e}; {nl} levels (overall and by item set; the reader rounds "
        f"to 5 decimals) largest difference {lw:.1e}, {nl_eq} of {nl} equal after the same rounding; {nf} frontier "
        f"readings (the points, the line at the controller's keeping, F and F_RB at the pooled points and over the blocks) "
        f"largest difference {fw:.2e}; {nr} firing rows (the share firing, the ever-fired share, the patch share per "
        f"firing) largest difference {rw:.2e}")
    assert worst < 1e-12 and lw <= 5e-6 + 1e-12 and fw < 1e-12 and rw < 1e-12 and nf > 0 and nr > 0

name = f"p62c_e2e005_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
