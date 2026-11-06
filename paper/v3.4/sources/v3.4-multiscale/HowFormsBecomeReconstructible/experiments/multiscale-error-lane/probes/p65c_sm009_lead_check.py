"""P65c (python probes/p65c_sm009_lead_check.py ROOT [READER]): the lead's check of SM009, a signal of need.
LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved final bodies and of the restored AR005 records, written
by the lead in reviewing SM009's phase A and committed before the freeze, dry-run first on P65 (AR005's P53 records,
engineering blocks 900729, 900739 | 900749, 900759) and on the debug run (900799); 5 November 2026; no simulation. It
reads PLAN_SM009.md's words (with its amendments) and imports nothing of sm009, sm008, sm007 or msefield. Adapted from P64c
(SM008), whose integrity, layout and endpoint sections it keeps.

It checks:
1. integrity: every stage file and each task's two restored records by sha256; both units' acquisitions rebuilt; the 16
   cases; at development the frozen digest;
2. the layout from SM008's words, in every composition of every response arm (P pooled, O own need; R where the stage
   ran it): group g's position p holds case (g + p) mod 8 of its position's role; iso8 each case once;
3. the endpoint re-scored from every saved final body;
4. kappa_O by the declared rule from P65k's reference driver means (kappa_O x mean(s) = kappa x mean(x) at kappa 0),
   equal to the run's; O's identity: under O no sheet reads the field, so every sheet of every O composition equals the
   iso8/O sheet of the same case and unit, bit for bit (and X1 under O is exactly 0);
5. the parts by the plan's words, li4 (registered) and dw (reported): Y1 a(struggler at corner 0 | k1-corner), O - P;
   Y2 a(healthy at corner 0 | k7-corner), O - P; Y4 a(struggler at corner 0 | k8), O - P; Y3 the group mean at
   k4-half, O - P (reported); the decomposition Y1 = Y4 - X1(P) case by case; per case the sheet at the named position;
   a block the mean of its 8 cases; the part the mean over the blocks; SD = max(block SD, case SD / sqrt(8)); the 95% t
   interval; on P65 the narrowest thresholds the rule allows (Y1, Y2 and Y4 must equal the registered ones);
6. reported: the struggler at an inner cell (k1-inner), every composition's group mean O - P, O's realized mean help
   against P's, the role means; with READER, the frozen reader's parts, thresholds, verdicts, reported items and levels.
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
from dl001 import sim as S                                      # noqa: E402  (frozen: sign)

ROOT = Path(sys.argv[1])
READER = Path(sys.argv[2]) if len(sys.argv) > 2 else None
RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
key = lambda s: s.replace("/", "_")
AR005_DEV = [910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798, 910799,
             910826, 910827, 910958]
WANT = {"probe": ("ar005/p53", [900729, 900739, 900749, 900759], "engineering"),
        "debug": ("ar005/debug", [900799], "engineering"),
        "preflight": ("ar005/preflight", [900779, 900789], "engineering"),
        "development": ("ar005/development", AR005_DEV, "development")}
# the plan's roles (from SM007's development levels of isolated sheets) and compositions, written out by the lead
ROLES = {"li4": ("S4_t1", "F0_t1"), "dw": ("F0_t1", "S4_t1")}            # (healthy, struggling)
COMPOSITIONS = {"k0": (), "k1-corner": (0,), "k1-inner": (1,), "k2-adjacent": (1, 2), "k2-apart": (0, 7),
                "k4-half": (0, 1, 4, 5), "k4-checker": (0, 2, 5, 7), "k6": (0, 3, 4, 5, 6, 7),
                "k7-corner": (1, 2, 3, 4, 5, 6, 7), "k7-inner": (0, 2, 3, 4, 5, 6, 7), "k8": tuple(range(8))}
NC = 8
M = json.load(open(ROOT / "manifest.json"))
STAGE = M["stage"]
SRC, BLOCKS, PURPOSE = WANT[STAGE]
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert M.get("study", "SM009") == "SM009" and not bad, bad[:5]
if STAGE == "development":
    fz = json.load(open(LANE / "sm009" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"
SM = json.load(open(RUNS / SRC / "manifest.json"))
NB = len(BLOCKS)

# A[(body, label)] -> {(g, p): {"a": (blocks, futures) , "gain"/"expo"/"stress": the window means}}; the role means
A, ROLEV, X5, OID = {}, {}, [0, 0.0], [0, 0.0]
KAP = {}
cnt = {"tasks": 0, "sheets": 0, "maxdiff": 0.0, "futures": set(), "layout": 0}
for body in ("li4", "dw"):
    healthy, struggling = ROLES[body]
    for bi, blk in enumerate(BLOCKS):
        z = np.load(ROOT / "shards" / key(SRC) / body / f"{blk}.npz")
        meta = json.loads(str(z["__meta__"]))
        assert meta["body"] == body and int(meta["block"]) == blk and meta["source"] == SRC and meta["stage"] == STAGE
        assert meta["roles"] == {"healthy": healthy, "struggling": struggling}, meta["roles"]
        KAP[(body, blk)] = (meta["kappa"], meta.get("kappa_o"), meta.get("kappa_r"))
        # 1. the restored records and the acquisition, both units
        Ts, keys = [], []
        for unit in (healthy, struggling):
            f_src = SM["tasks"][f"{body}/{unit}/{blk}"]["files"]["raw"]
            assert sha(RUNS / SRC / f_src["path"]) == f_src["sha256"] == meta["rawfiles"][unit]["sha256"]
            raw = np.load(RUNS / SRC / f_src["path"])
            pattern, theta = A1D.parse_unit(unit)
            cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, PURPOSE)
            assert np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"]) and np.array_equal(T, raw["T"])
            assert len(cases) == NC
            Ts.append(np.asarray(T, float))
            keys += [list(c.key()) for c in cases]
        assert keys == [list(c) for c in meta["cases"]] and keys[:NC] == keys[NC:], "the 16 cases"
        T16 = np.concatenate(Ts)
        # 2. the layout
        arrs = [tuple(a) for a in meta["arrangements"]]
        br_case, br_arr, br_g, br_p, br_f = (z[k_] for k_ in ("br_case", "br_arr", "br_group", "br_pos", "br_future"))
        for ai, (lab, comp, bnd, kind, lam) in enumerate(arrs):
            for fut in sorted(set(br_f.tolist())):
                sel = np.flatnonzero((br_arr == ai) & (br_f == fut))
                if comp == "iso8":
                    assert sorted(br_case[sel].tolist()) == list(range(2 * NC)), (lab, fut)
                    continue
                gp = sorted(zip(br_g[sel].tolist(), br_p[sel].tolist()))
                assert gp == [(g, p) for g in range(8) for p in range(8)], (lab, fut)
                for b in sel:
                    g, p = int(br_g[b]), int(br_p[b])
                    want = (g + p) % NC + (NC if p in COMPOSITIONS[comp] else 0)
                    assert int(br_case[b]) == want, (lab, g, p, int(br_case[b]), want)
                cnt["layout"] += len(sel)
        # 3. the endpoint from the saved final bodies
        zr = np.load(ROOT / "raw" / key(SRC) / body / f"{blk}.npz")
        assert np.array_equal(zr["br_case"], br_case) and np.array_equal(zr["br_future"], br_f)
        sg = S.sign(zr["V"], T16[br_case])
        a_ = np.maximum(sg, 1 - sg)
        cnt["maxdiff"] = max(cnt["maxdiff"], float(np.abs(sg - z["sign"][-1]).max()), float(np.abs(a_ - z["a_v"][-1]).max()))
        cnt["sheets"] += len(br_case)
        cnt["tasks"] += 1
        futs = sorted(set(br_f.tolist()))
        cnt["futures"] |= set(futs)
        a_last = z["a_v"][-1]
        for ai, (lab, comp, bnd, kind, lam) in enumerate(arrs):
            d = A.setdefault((body, lab), {})
            for b in np.flatnonzero(br_arr == ai):
                g, p, fut = int(br_g[b]), int(br_p[b]), int(br_f[b])
                cell = d.setdefault((g, p) if comp != "iso8" else (int(br_case[b]), -1),
                                    {q: np.full((NB, len(futs)), np.nan) for q in ("a", "gain", "expo", "stress", "case")})
                cell["a"][bi, futs.index(fut)] = a_last[b]
                cell["gain"][bi, futs.index(fut)] = z["gain_mean"][b]
                cell["expo"][bi, futs.index(fut)] = z["expo_mean"][b]
                cell["stress"][bi, futs.index(fut)] = z["stress_mean"][b]
                cell["case"][bi, futs.index(fut)] = br_case[b]
            for role, lo, hi in (("healthy", 0, NC), ("struggling", NC, 2 * NC), ("all", 0, 2 * NC)):
                sel = np.flatnonzero((br_arr == ai) & (br_case >= lo) & (br_case < hi))
                if len(sel):
                    r_ = ROLEV.setdefault((body, lab, role), {q: [] for q in ("a", "gain", "expo", "stress")})
                    r_["a"] += a_last[sel].tolist()
                    r_["gain"] += z["gain_mean"][sel].tolist()
                    r_["expo"] += z["expo_mean"][sel].tolist()
                    r_["stress"] += z["stress_mean"][sel].tolist()
        # O's identity: no O sheet reads the field, so every sheet of an O composition equals the iso8/O sheet of its case
        lab_of = {a[0]: ai for ai, a in enumerate(arrs)}
        if "iso8/absorbing/O" in lab_of:
            for fut in futs:
                iso = {int(br_case[b]): b for b in np.flatnonzero((br_arr == lab_of["iso8/absorbing/O"]) & (br_f == fut))}
                for ai, (lab, comp, bnd, kind, lam) in enumerate(arrs):
                    if kind != "own" or comp == "iso8" or bnd != "absorbing":
                        continue
                    for b in np.flatnonzero((br_arr == ai) & (br_f == fut)):
                        OID[0] += 1
                        OID[1] = max(OID[1], float(np.abs(zr["V"][b] - zr["V"][iso[int(br_case[b])]]).max()))
say(f"P65c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {cnt['tasks']} "
    f"task-files, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; futures {sorted(cnt['futures'])}; "
    f"every task's two restored records by sha256 and their rebuilt acquisitions equal; the 16 cases the healthy unit's 8 "
    f"then the struggling unit's 8, sharing every key")
say(f"  the layout from the plan's words: {cnt['layout']} sheets, group g position p holding case (g + p) mod 8 of its "
    f"position's role in every composition; iso8 each of the 16 cases once")
say(f"  the endpoint re-scored from the saved final bodies ({cnt['sheets']} sheets): largest |difference| {cnt['maxdiff']:.1e}")
assert cnt["maxdiff"] < 1e-12
say(f"  O's identity: every sheet of every absorbing O composition equals the iso8/O sheet of its case and unit: {OID[0]} "
    f"sheets, largest |difference| in V {OID[1]:.1e}")
assert OID[1] == 0.0 and OID[0] > 0
P65K = json.load(open(LANE / "probes" / "results" / "p65k_sm009_kappa.json"))
k_lead = P65K["kappa"] * P65K["driver_means"]["P"] / P65K["driver_means"]["O"]
k_run = {v[1] for v in KAP.values()}
assert len(k_run) == 1 and abs(next(iter(k_run)) - k_lead) < 1e-9 * k_lead, (k_run, k_lead)
say(f"  kappa_O by the declared rule from P65k's reference (kappa x mean(x) / mean(s) = {P65K['kappa']} x "
    f"{P65K['driver_means']['P']:.6f} / {P65K['driver_means']['O']:.6f}): {k_lead:.12f}, equal to the run's")


K = 3 * math.sqrt(1 / 4 + 1 / 16)
T975 = stats.t.ppf(0.975, NB - 1) if NB > 1 else float("nan")


def est(x):
    """x: (blocks, cases)."""
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


def at(body, lab, gp_of_case, q="a"):
    """(blocks, cases): the sheet of case j at the (g, p) gp_of_case(j), averaged over the futures."""
    d = A[(body, lab)]
    return np.stack([d[gp_of_case(j)][q].mean(1) for j in range(NC)], axis=1)


corner = lambda j: (j, 0)                       # case j sits at corner 0 in group j
inner1 = lambda j: ((j - 1) % NC, 1)            # case j sits at inner cell 1 in group j - 1


def by_case_index(body, lab):
    """(blocks, cases): per case index c, the mean over the sheets with that index, both roles, every position."""
    d = A[(body, lab)]
    return np.stack([np.mean([d[(g, p)]["a"].mean(1) for g in range(8) for p in range(8) if (g + p) % NC == c], axis=0)
                     for c in range(NC)], axis=1)


def X4fn(body, bnd="absorbing"):
    return by_case_index(body, f"k4-half/{bnd}") - 0.5 * (by_case_index(body, f"k0/{bnd}") + by_case_index(body, f"k8/{bnd}"))


OP = lambda b, comp, f_: at(b, f"{comp}/absorbing/O", f_) - at(b, f"{comp}/absorbing/P", f_)
PARTS = {
    "Y1": lambda b: OP(b, "k1-corner", corner),
    "Y2": lambda b: OP(b, "k7-corner", corner),
    "Y4": lambda b: OP(b, "k8", corner),
    "Y3": lambda b: by_case_index(b, "k4-half/absorbing/O") - by_case_index(b, "k4-half/absorbing/P"),
    "X1/O": lambda b: at(b, "k1-corner/absorbing/O", corner) - at(b, "k8/absorbing/O", corner)}
WORDS = {"Y1": "the lone struggler at corner 0 (k1-corner), O - P", "Y2": "the lone healthy sheet at corner 0 (k7-corner), O - P",
         "Y4": "the struggler at corner 0 in the pure struggling group (k8), O - P",
         "Y3": "the group mean at k4-half (per case index), O - P", "X1/O": "X1 under O (an identity: exactly 0)"}
# the registration (REGISTRATION_SM009.md with its amendment; the lead's rulings sent 22:58:43Z, after P65's values)
TH = {"Y1": ("least", 0.05), "Y2": ("most", -0.005), "Y4": ("band", (0.02, 0.04))}
say(f"\nTHE PARTS, li4 (S4 healthy, F0 struggling; the responses P pooled and O own need at a matched open-loop response; {NB} blocks x {NC} cases; per case the sheet at the named position, "
    f"averaged over the futures; [95% t interval]" + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
Q, OK = {}, {}
for pid, fn in PARTS.items():
    try:
        x = fn("li4")
    except KeyError:
        say(f"  {pid} {WORDS[pid]}: not available at this stage")
        continue
    q = Q[pid] = est(x)
    line = (f"  {pid} {WORDS[pid]}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
            f"case/sqrt8 {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
    if STAGE == "probe" and pid != "X1/O":
        lo, hi = narrow_num(q)
        line += f"; the narrowest [{lo:+.3f}, {hi:+.3f}]"
        if pid in TH:
            kd, th = TH[pid]
            assert ((lo, hi) == th) if kd == "band" else abs((hi if kd == "most" else lo) - th) < 1e-9, (pid, lo, hi, th)
    if pid in TH:
        kd, th = TH[pid]
        OK[pid] = (th[0] <= q["v"] <= th[1]) if kd == "band" else (q["v"] <= th if kd == "most" else q["v"] >= th)
        line += (f"; registered {list(th) if kd == 'band' else ('<= ' if kd == 'most' else '>= ') + str(th)}: "
                 f"{'HOLDS' if OK[pid] else 'FAILS'}")
    elif pid == "X1/O":
        assert q["v"] == 0.0 and q["sd"] == 0.0, "X1 under O is not exactly 0"
        line += "; exactly 0 (the identity)"
    else:
        line += "; reported"
    say(line)
if OK:
    say("  VERDICTS (development: the point value against the registered threshold or band): "
        + ", ".join(f"{p} {'HOLDS' if v else 'FAILS'}" for p, v in OK.items()) + ("" if STAGE == "development" else "  [not a development result]"))

say("\nREPORTED (the lead's)")
REP = {}
for pid, fn in PARTS.items():
    try:
        REP[f"{pid}/dw"] = est(fn("dw"))
    except KeyError:
        pass
xa = {}
for b in ("li4", "dw"):
    try:
        x1p = at(b, "k1-corner/absorbing/P", corner) - at(b, "k8/absorbing/P", corner)
        d_ = PARTS["Y1"](b) - (PARTS["Y4"](b) - x1p)
        xa[b] = float(np.abs(d_).max())
        REP["X1/P" + ("" if b == "li4" else "/dw")] = est(x1p)
    except KeyError:
        pass
say("  the decomposition Y1 = Y4 - X1(P), case by case: largest |difference| " + ", ".join(f"{b} {v:.1e}" for b, v in xa.items()))
assert all(v < 1e-12 for v in xa.values())
for b, suf in (("li4", ""), ("dw", "/dw")):
    try:
        REP["Y1/inner" + suf] = est(OP(b, "k1-inner", inner1))
    except KeyError:
        pass
    for comp in COMPOSITIONS:
        try:
            REP[f"O-P/group/{comp}{suf}"] = est(by_case_index(b, f"{comp}/absorbing/O") - by_case_index(b, f"{comp}/absorbing/P"))
        except KeyError:
            pass
for b, suf in (("li4", ""), ("dw", "/dw")):
    for arm in ("P", "O"):
        try:
            REP[f"X1/{arm}{suf}"] = est(at(b, f"k1-corner/absorbing/{arm}", corner) - at(b, f"k8/absorbing/{arm}", corner))
            REP[f"X2/{arm}{suf}"] = est(at(b, f"k7-corner/absorbing/{arm}", corner) - at(b, f"k0/absorbing/{arm}", corner))
        except KeyError:
            pass
    try:
        REP["O-P/k0" + suf] = est(OP(b, "k0", corner))
    except KeyError:
        pass
try:
    REP["X3/P"] = est(at("li4", "k1-corner/sealed/P", corner) - at("li4", "k8/sealed/P", corner))
except KeyError:
    pass
try:
    for q_, nm_ in (("gain", "gain"), ("stress", "stress"), ("expo", "exposure")):
        REP[f"Y1/{nm_}"] = est(at("li4", "k1-corner/absorbing/O", corner, q_) - at("li4", "k1-corner/absorbing/P", corner, q_))
        REP[f"Y2/{nm_}"] = est(at("li4", "k7-corner/absorbing/O", corner, q_) - at("li4", "k7-corner/absorbing/P", corner, q_))
except KeyError:
    pass
for k_, q_ in REP.items():
    say(f"  {k_}: {q_['v']:+.6f} [{q_['lo']:+.6f}, {q_['hi']:+.6f}]")
say("  O's realized mean help (the mean gain) against P's, per composition (li4, absorbing): " + "; ".join(
    f"{comp} {np.mean(ROLEV[('li4', f'{comp}/absorbing/O', 'all')]['gain']) / np.mean(ROLEV[('li4', f'{comp}/absorbing/P', 'all')]['gain']):.4f}"
    for comp in COMPOSITIONS if ("li4", f"{comp}/absorbing/O", "all") in ROLEV and ("li4", f"{comp}/absorbing/P", "all") in ROLEV))
say("  the role means against k (li4, absorbing; a at the last read: struggling / healthy / the group; P then O):")
for comp, arm in [(c, a) for c in COMPOSITIONS for a in ("P", "O")]:
    lab = f"{comp}/absorbing/{arm}"
    if ("li4", lab, "all") not in ROLEV:
        continue
    cells = []
    for role in ("struggling", "healthy", "all"):
        r_ = ROLEV.get(("li4", lab, role))
        cells.append(f"{np.mean(r_['a']):.4f}" if r_ else "-")
    say(f"    {comp} {arm} (k {len(COMPOSITIONS[comp])}): " + " / ".join(cells))

if READER is not None:
    rd = json.load(open(READER))
    assert rd["stage"] == STAGE and Path(rd["root"]).resolve() == ROOT.resolve(), "another run"
    if rd["design_digest"] != M["design_digest"]:
        assert STAGE != "development", "the reader's design is not the run's"
        say(f"\n  (the reader ran under design {rd['design_digest'][:12]}, the run under {M['design_digest'][:12]})")
    worst, n_cmp, n_th = 0.0, 0, 0
    for rp in rd["parts"]:
        pid = rp["id"]
        if not rp.get("available", True) or pid not in Q:
            continue
        q = Q[pid]
        worst = max(worst, abs(rp["value"] - q["v"]), abs(rp["sd"] - q["sd"]),
                    max(abs(x - y) for x, y in zip(rp["blocks"], q["blocks"])))
        if NB > 1:
            worst = max(worst, abs(rp["ci95"][0] - q["lo"]), abs(rp["ci95"][1] - q["hi"]),
                        max(abs(x - y) for x, y in zip(rp["halves"], q["halves"])))
        if rp.get("threshold") is not None:
            kd, th = TH[pid]
            assert rp["kind"] == {"band": "in", "least": "ge", "most": "le"}[kd], (pid, rp["kind"])
            assert (list(rp["threshold"]) == list(th)) if kd == "band" else abs(rp["threshold"] - th) < 1e-12, (pid, rp["threshold"])
            assert rp["holds"] == OK[pid] and rd["verdicts"][pid] == ("HOLDS" if OK[pid] else "FAILS"), pid
            n_th += 1
        n_cmp += 1
    rw, nr, skipped = 0.0, 0, []
    for it in rd.get("reported", []):
        if it["id"] in REP and it.get("available", True):
            q = REP[it["id"]]
            rw = max(rw, abs(it["value"] - q["v"]))
            if NB > 1 and it.get("ci95") and not any(isinstance(v, float) and math.isnan(v) for v in it["ci95"]):
                rw = max(rw, abs(it["ci95"][0] - q["lo"]), abs(it["ci95"][1] - q["hi"]))
            nr += 1
        else:
            skipped.append(it["id"])
    lw, nl = 0.0, 0
    WIN = int(json.loads(str(np.load(next((ROOT / "shards").rglob("*.npz")))["__meta__"]))["window"])
    for kk, rec in rd.get("levels", {}).items():
        body, lab = kk.split("|")
        for role, rk in (("healthy", "healthy"), ("struggling", "struggling")):
            r_ = ROLEV.get((body, lab, role))
            if rec.get(rk) is None:
                assert r_ is None, (kk, role)
                continue
            for q_, rq in (("a", f"a_{WIN}"), ("gain", "gain_mean"), ("expo", "expo_mean"), ("stress", "stress_mean")):
                lw = max(lw, abs(rec[rk][rq] - float(np.mean(r_[q_]))))
                nl += 1
        if rec.get("group_mean") is not None:
            lw = max(lw, abs(rec["group_mean"] - float(np.mean(ROLEV[(body, lab, "all")]["a"]))))
            nl += 1
    x5 = None
    say(f"\nAGAINST THE FROZEN READER ({READER}): {n_cmp} parts (values, intervals, SDs, halves, blocks; {n_th} thresholds, "
        f"kinds and verdicts) largest difference {worst:.2e}; {nr} reported items largest difference {rw:.2e}"
        + (f" (not recomputed: {', '.join(skipped)})" if skipped else "") + f"; {nl} level readings largest difference "
        f"{lw:.2e}")
    assert worst < 1e-12 and rw < 1e-12 and lw < 1e-12 and (x5 is None or (x5["exact"] and x5["largest_difference"] == 0.0))

name = f"p65c_sm009_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
