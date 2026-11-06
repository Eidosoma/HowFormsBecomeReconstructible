"""P60c (python probes/p60c_e2e004_lead_check.py ROOT [READER]): the lead's check of E2E004, what keeps a record through
renewal. LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved successor states and of the restored AR005
records, written by the lead in reviewing E2E004's phase A and committed before the freeze, dry-run first on P60 (AR005's
P53 records, engineering blocks 900729, 900739 | 900749, 900759, parent 0's four cases, one future) and on the debug run
(900799, every row to generation 3); 4 November 2026; no simulation of the tissue. Adapted from P58c (E2E002).

It checks, from PLAN_E2E004.md's words and not from e2e004.sim, e2e004.predict, e2e004.checks, e2e002.sim or e2e001.sim:
1. integrity: every stage file against its manifest by sha256, every restored record against its own run's manifest,
   the acquisition rebuilt by ar001.sim.prepare (the pilot's parent-0 subset where the stage reads it) equal to the
   record's V0, R0 and T; at the development stage the run's digest against e2e004/frozen/design.json;
2. the packets at generation 0, rebuilt by the lead from the restored files and the frozen functions: protected storage
   (R0 with its bonds, lr001.sim.edges_from(msegrid.core.bonds(R0, True))); post-damage copying (ar001.sim.event's record
   at sigma 0); vms's memory@0 record where it runs. Every label's generation-0 endpoints, scored by the lead with the
   pre-injury body (V0) for protected and post and the arm's final body for a restored arm, must equal the stage's;
3. the successors: every endpoint at every saved horizon (1, 3, 8) re-scored by the lead from the saved states (V, r);
4. the labels against the plan's table: each label's route and packet;
5. the parts G1-G4 by the plan's words: pooled per case over the eight unit-body pairs (one future), a block the mean of
   its cases, the part the mean over the blocks; SD = max(block SD, case SD / sqrt(cases a block)); the 95% t interval;
   the development verdict the point value against the registered threshold or band; on P60 the margins
   (>= 3 sqrt(1/4 + 1/16)), both halves and the narrowest round thresholds (0.01 steps, 0.005 within 0.01 of zero),
   which must equal the registered ones;
6. the declared trade-off reading (reported): at generation 8 the routes ranked by q_r(protected), most first, and by
   u_r(post), least first; the trade-off holds where the two orders coincide; over every route run (vote1 included where
   it runs, as declared) and over the three fixed rules (body, vote, record; added to the reader after P60's values),
   overall and by item set;
7. reported: the levels of every label at 0, 1, 3, 8 with their task counts, by item set (li4 x F0 first); with READER,
   the frozen reader's values, levels and readings.

The lead's scoring (E2E001's endpoints): s = +1 where dl001.sim.sign(x, T) >= 0.5, else -1; u_r = lr005.sim.inside(s r,
T, m) with m generation 0's 4 x 4 patch (be001.sim.patch under the record's tag); u_v the same for the body; u_r_raw
without s; a = max(sign, 1 - sign); q = (a - max over SR001's foreign placements of a) / 0.25; agree_in the agreement of
V and r inside m.
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
WANT = {"probe": ("ar005/p53", [900729, 900739, 900749, 900759], "mse-p60", (0,)),
        "debug": ("ar005/debug", [900799], "mse-e2e004", (0, 1)),
        "preflight": ("ar005/preflight", [900779, 900789], "mse-e2e004", (0, 1)),
        "development": ("ar005/development", AR005_DEV, "mse-e2e004", (0, 1))}
SRC, BLOCKS, FTAG, PARENTS = WANT[STAGE]
SROOT = RUNS / SRC
NB = len(BLOCKS)
PAIRS = [(b, u) for b in ("dw", "li4") for u in ("S4_t0", "S4_t1", "F0_t0", "F0_t1")]
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert M["study"] == "E2E004" and not bad, bad[:5]
assert len(M["tasks"]) == len(PAIRS) * NB, len(M["tasks"])
SM = json.load(open(SROOT / "manifest.json"))
if STAGE == "development":
    fz = json.load(open(LANE / "e2e004" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"
# the plan's lineage table: label -> (route, generation-0 packet)
PLAN = {f"{r}/{p}": (r, src) for r in ("body", "vote", "record", "vote1") for p, src in
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
            for p in range(n):
                sc = score(Vg[p], rg[p], T, Tf, m)
                for e in ENDS:
                    dg = max(dg, float(np.abs(sc[e] - z[f"f0/g{g}/{e}"][p]).max()))
                n_states += 1
            for lab, row in labels.items():
                if row in rws:
                    for e in ENDS:
                        VAL.setdefault((lab, e, g), np.full((NB, len(PAIRS), k), np.nan))[bi, pi] = z[f"f0/g{g}/{e}"][rws.index(row)]
say(f"P60c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {len(M['tasks'])} "
    f"tasks, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; {M['started_utc']} - "
    f"{M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h; {nraw} restored records, every sha256 equal to {SRC}'s "
    f"manifest; the acquisition rebuilt by ar001.sim.prepare ({KC} cases a task) equal to every record's V0, R0 and T")
say(f"  the labels: every route and packet as the plan's table ({', '.join(LABELS)})")
say(f"  the packets at generation 0 rebuilt by the lead ({n_pk} label-tasks; protected storage from R0, post-damage copying "
    f"from ar001.sim.event, a restored arm from its run): every endpoint equal to the stage's within {d0:.1e}")
say(f"  the successors re-scored by the lead from the saved states at horizons 1, 3 and 8 ({n_states} row-task-horizons): "
    f"largest |difference| {dg:.1e}")
assert d0 < 1e-12 and dg < 1e-12


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


# the registration's thresholds (REGISTRATION_E2E004.md): the four parts at the rule's narrowest on P60
TH = {"G1": ("least", 0.18), "G2": ("least", 0.20), "G3": ("band", (0.19, 0.27)), "G4": ("band", (-0.28, -0.10))}
D2 = lambda a, b, e: (lambda f: f(a, e, 8) - f(b, e, 8))
PARTS = [("G1", "q_r(vote/protected) - q_r(body/protected), g 8: the vote keeps more history", D2("vote/protected", "body/protected", "q_r")),
         ("G2", "u_r(body/post) - u_r(vote/post), g 8: the body route heals more", D2("body/post", "vote/post", "u_r")),
         ("G3", "q_r(record/protected) - q_r(vote/protected), g 8: the record route against the vote, keeping", D2("record/protected", "vote/protected", "q_r")),
         ("G4", "u_r(record/post) - u_r(vote/post), g 8: the record route against the vote, healing", D2("record/post", "vote/post", "u_r"))]
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

# the declared trade-off reading (reported)
TRADE = {}
G_T = 8 if all(cover(f"{r}/protected", "q_r", 8) for r in ("body", "vote", "record")) else None
if G_T is not None:
    say("\nTHE DECLARED TRADE-OFF READING (reported; generation 8): the routes by q_r(protected), most first, and by "
        "u_r(post), least first; it holds where the two orders coincide")
    routes_run = [r for r in ("body", "vote", "record", "vote1") if f"{r}/protected" in LABELS and f"{r}/post" in LABELS]
    for which, routes in (("every route run (as declared)", routes_run), ("the three fixed rules (added after P60's values)", ["body", "vote", "record"])):
        for nm, sb in (("all", None),) + tuple(SETS.items()):
            f_ = (lambda lab, e: float(X(lab, e, G_T).mean())) if sb is None else (lambda lab, e, sb=sb: float(X_sub(lab, e, G_T, sb).mean()))
            keep = {r: f_(f"{r}/protected", "q_r") for r in routes}
            heal = {r: f_(f"{r}/post", "u_r") for r in routes}
            ok_ = sorted(routes, key=lambda r: -keep[r])
            oh_ = sorted(routes, key=lambda r: heal[r])
            TRADE[(which, nm)] = (keep, heal, ok_, oh_)
            say(f"  {which}, {nm}: keeping {', '.join(f'{r} {keep[r]:.4f}' for r in ok_)}; healing (least first) "
                f"{', '.join(f'{r} {heal[r]:.4f}' for r in oh_)}: {'HOLDS' if ok_ == oh_ else 'does not hold'}")

# the lead's extension after the development's results (4 November 2026, about 18:00Z; reported only, nothing registered
# or checked changed; git shows the diff): vote1's two declared reported contrasts with their intervals, at generation 8
if all(f"vote1/{p}" in LABELS for p in ("protected", "post")) and cover("vote1/protected", "q_r", 8) == NB * len(PAIRS):
    say("\nVOTE1, THE SECOND COPY AND THE RULE (reported, as declared; generation 8)")
    for other, what in (("vote", "against the vote: the second copy"), ("body", "against the body: the rule")):
        for e, p in (("q_r", "protected"), ("u_r", "post")):
            x = X(f"vote1/{p}", e, 8) - X(f"{other}/{p}", e, 8)
            q = est(x)
            say(f"  vote1 {what}, {e}({p}): {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}]; by item set "
                + "; ".join(f"{nm} {X_sub(f'vote1/{p}', e, 8, sb).mean() - X_sub(f'{other}/{p}', e, 8, sb).mean():+.6f}"
                            for nm, sb in SETS.items()))

say("\nREPORTED (the lead's): levels by label, u_r and q_r (all pairs; li4 x F0 u_r in parentheses), with partial cells marked")
for lab in LABELS:
    cells = []
    for g in (0, 1, 3, 8):
        c = cover(lab, "u_r", g)
        if c == NB * len(PAIRS):
            cells.append(f"g{g} u_r {X(lab, 'u_r', g).mean():.4f} ({X_sub(lab, 'u_r', g, SETS['particular (li4 x F0)']).mean():.4f}) "
                         f"q_r {X(lab, 'q_r', g).mean():+.4f}")
        elif c:
            cells.append(f"g{g} PARTIAL ({c} of {NB * len(PAIRS)} tasks; not pooled)")
    say(f"  {lab} [{ROUTE[lab]}]: " + "; ".join(cells))

if READER is not None:
    rd = json.load(open(READER))
    assert rd["study"] == "E2E004" and rd["stage"] == STAGE and Path(rd["root"]).resolve() == ROOT.resolve(), "another run"
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
    tw, nt = 0.0, 0
    for rk, which in (("trade_off", "every route run (as declared)"), ("trade_off_core", "the three fixed rules (added after P60's values)")):
        if rk not in rd or not TRADE:
            continue
        for nm, rec in rd[rk].items():
            keep, heal, ok_, oh_ = TRADE[(which, {"all": "all", "native": "native (li4 x S4)", "particular": "particular (li4 x F0)",
                                                  "permissive": "permissive (dw)"}[nm])]
            tw = max(tw, max(abs(rec["keep_q_r"][r] - keep[r]) for r in keep), max(abs(rec["heal_u_r"][r] - heal[r]) for r in heal))
            assert rec["order_by_keeping"] == ok_ and rec["order_by_healing_least_first"] == oh_, (rk, nm)
            nt += 1
    say(f"\nAGAINST THE FROZEN READER ({READER}): {n_cmp} parts (values, intervals, SDs, halves, blocks, item sets; "
        f"{n_th} registered thresholds, kinds and verdicts) largest difference {worst:.2e}; {nl} levels, largest "
        f"difference {lw:.2e}; partial levels (not pooled here): {len(partial)}; {nt} trade-off readings (both orders "
        f"equal), largest difference {tw:.2e}")
    assert worst < 1e-12 and lw < 1e-12 and tw < 1e-12

name = f"p60c_e2e004_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
