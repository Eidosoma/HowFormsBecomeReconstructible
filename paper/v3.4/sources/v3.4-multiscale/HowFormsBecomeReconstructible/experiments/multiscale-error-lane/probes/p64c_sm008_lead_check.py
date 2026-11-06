"""P64c (python probes/p64c_sm008_lead_check.py ROOT [READER]): the lead's check of SM008, mixed groups.
LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved final bodies and of the restored AR005 records, written
by the lead in reviewing SM008's phase A and committed before the freeze, dry-run first on P64 (AR005's P53 records,
engineering blocks 900729, 900739 | 900749, 900759) and on the debug run (900799); 5 November 2026; no simulation. It
reads PLAN_SM008.md's words (with its amendments) and imports nothing of sm008, sm007 or msefield.

It checks:
1. integrity: every stage file against its manifest by sha256; each task's two restored records (the healthy and the
   struggling unit of the body, the plan's roles) against their run's manifest by sha256; the acquisition rebuilt by
   ar001.sim.prepare for each unit equal to its record's V0, R0 and T; the task's 16 cases the healthy unit's 8 then the
   struggling unit's 8, in acquisition order, the two units sharing every case key; at development the frozen digest;
2. the layout from the plan's words: in every composition, group g = 0..7, position p = 0..7 holds case (g + p) mod 8 of
   the struggling unit where p is a struggling position of the composition, of the healthy unit otherwise; each (g, p)
   once a future; iso8 holds each of the 16 cases once;
3. the endpoint: a_v = max(sign, 1 - sign), sign = dl001.sim.sign of every saved final body against its case's T, equal to
   the shard's a_v and sign at the last read;
4. the parts by the plan's words, li4 (registered) and dw (reported): a part's value for a case is the case's sheet at the
   named (g, p), averaged over the futures (X4: over the sheets with that case index); a block the mean of its 8 cases;
   the part the mean over the blocks; SD = max(block SD, case SD / sqrt(8)); the 95% t interval:
   X1 a(struggler at corner 0 | k1-corner) - a(the same | k8), absorbing; X2 a(healthy at corner 0 | k7-corner) - a(the
   same | k0), absorbing; X3 X1 sealed; X4 the group mean at k4-half - the mean of k0's and k8's, per case index;
   X5 X1 under the preprint's stress (an identity: exactly 0 by the layout, every sheet); X6 a(struggler at inner 1 |
   k1-inner) - a(struggler at corner 0 | k1-corner);
5. reported: the same at lambda 2; the position effect in the pure groups; X1's and X2's exposure, gain and stress; the
   role means against k; on P64 the narrowest thresholds the rule allows (X1-X3 must equal the registered ones); with
   READER, the frozen reader's parts, thresholds, verdicts, levels and reported items.
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
assert M.get("study", "SM008") == "SM008" and not bad, bad[:5]
if STAGE == "development":
    fz = json.load(open(LANE / "sm008" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"
SM = json.load(open(RUNS / SRC / "manifest.json"))
NB = len(BLOCKS)

# A[(body, label)] -> {(g, p): {"a": (blocks, futures) , "gain"/"expo"/"stress": the window means}}; the role means
A, ROLEV, X5 = {}, {}, [0, 0.0]
cnt = {"tasks": 0, "sheets": 0, "maxdiff": 0.0, "futures": set(), "layout": 0}
for body in ("li4", "dw"):
    healthy, struggling = ROLES[body]
    for bi, blk in enumerate(BLOCKS):
        z = np.load(ROOT / "shards" / key(SRC) / body / f"{blk}.npz")
        meta = json.loads(str(z["__meta__"]))
        assert meta["body"] == body and int(meta["block"]) == blk and meta["source"] == SRC and meta["stage"] == STAGE
        assert meta["roles"] == {"healthy": healthy, "struggling": struggling}, meta["roles"]
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
        # X5: the identity under the preprint's stress (every sheet, every (g, p), k1-corner against k8 and k0)
        lab_of = {a[0]: ai for ai, a in enumerate(arrs)}
        if "k1-corner/absorbing/paper" in lab_of:
            for other in ("k8/absorbing/paper", "k0/absorbing/paper"):
                for fut in futs:
                    s1 = np.flatnonzero((br_arr == lab_of["k1-corner/absorbing/paper"]) & (br_f == fut))
                    s2 = np.flatnonzero((br_arr == lab_of[other]) & (br_f == fut))
                    o1 = sorted(s1, key=lambda b: (br_g[b], br_p[b]))
                    o2 = sorted(s2, key=lambda b: (br_g[b], br_p[b]))
                    # the same newborn and noise at every (g, p): where the unit is the same the bodies are equal
                    same = [(b1, b2) for b1, b2 in zip(o1, o2) if br_case[b1] == br_case[b2]]
                    X5[0] += len(same)
                    X5[1] = max(X5[1], max(float(np.abs(zr["V"][b1] - zr["V"][b2]).max()) for b1, b2 in same))
say(f"P64c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {cnt['tasks']} "
    f"task-files, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; futures {sorted(cnt['futures'])}; "
    f"every task's two restored records by sha256 and their rebuilt acquisitions equal; the 16 cases the healthy unit's 8 "
    f"then the struggling unit's 8, sharing every key")
say(f"  the layout from the plan's words: {cnt['layout']} sheets, group g position p holding case (g + p) mod 8 of its "
    f"position's role in every composition; iso8 each of the 16 cases once")
say(f"  the endpoint re-scored from the saved final bodies ({cnt['sheets']} sheets): largest |difference| {cnt['maxdiff']:.1e}")
assert cnt["maxdiff"] < 1e-12
say(f"  X5's identity under the preprint's stress: every sheet of k1-corner whose unit equals k8's or k0's at the same (g, p) "
    f"is the same body: {X5[0]} sheet pairs, largest |difference| in V {X5[1]:.1e}")
assert X5[1] == 0.0


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


PARTS = {
    "X1": lambda b: at(b, "k1-corner/absorbing", corner) - at(b, "k8/absorbing", corner),
    "X2": lambda b: at(b, "k7-corner/absorbing", corner) - at(b, "k0/absorbing", corner),
    "X3": lambda b: at(b, "k1-corner/sealed", corner) - at(b, "k8/sealed", corner),
    "X4": lambda b: X4fn(b),
    "X5": lambda b: at(b, "k1-corner/absorbing/paper", corner) - at(b, "k8/absorbing/paper", corner),
    "X6": lambda b: at(b, "k1-inner/absorbing", inner1) - at(b, "k1-corner/absorbing", corner)}
WORDS = {"X1": "a lone struggler among healthy neighbours against among strugglers (corner 0, absorbing)",
         "X2": "a lone healthy sheet among strugglers against among healthy sheets (corner 0, absorbing)",
         "X3": "X1 with the edge sealed", "X4": "the group's cost of mixing: k4-half against the pure groups' mean",
         "X5": "X1 under the preprint's stress (an identity)", "X6": "the lone struggler's position: inner 1 against corner 0"}
# the registration (REGISTRATION_SM008.md with its amendment; the lead's rulings sent 16:32:58Z, after P64's values):
# X1-X3 at the rule's narrowest; X4 an equivalence band with frozen margins; X5 an identity, X6 reported
TH = {"X1": ("most", -0.03), "X2": ("least", 0.01), "X3": ("most", -0.03), "X4": ("band", (-0.01, 0.01))}
say(f"\nTHE PARTS, li4 (S4 healthy, F0 struggling; {NB} blocks x {NC} cases; per case the sheet at the named position, "
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
    if STAGE == "probe" and pid != "X5":
        lo, hi = narrow_num(q)
        line += f"; the narrowest [{lo:+.3f}, {hi:+.3f}]"
        if pid in ("X1", "X2", "X3"):
            kd, th = TH[pid]
            assert abs((hi if kd == "most" else lo) - th) < 1e-9, (pid, lo, hi, th)
    if pid in TH:
        kd, th = TH[pid]
        OK[pid] = (th[0] <= q["v"] <= th[1]) if kd == "band" else (q["v"] <= th if kd == "most" else q["v"] >= th)
        line += (f"; registered {list(th) if kd == 'band' else ('<= ' if kd == 'most' else '>= ') + str(th)}: "
                 f"{'HOLDS' if OK[pid] else 'FAILS'}")
    elif pid == "X5":
        assert q["v"] == 0.0 and q["sd"] == 0.0, "X5 is not exactly 0"
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
for b, suf in (("li4", ""), ("dw", "/dw")):
    for nm, la, lb, f_ in (("X1/shared", "k1-corner/absorbing/shared", "k8/absorbing/shared", corner),
                           ("X2/shared", "k7-corner/absorbing/shared", "k0/absorbing/shared", corner)):
        try:
            REP[nm + suf] = est(at(b, la, f_) - at(b, lb, f_))
        except KeyError:
            pass
for nm, comp in (("P8", "k8"), ("P0", "k0")):
    for bnd in ("absorbing", "sealed"):
        try:
            REP[f"{nm}/{bnd}"] = est(at("li4", f"{comp}/{bnd}", inner1) - at("li4", f"{comp}/{bnd}", corner))
        except KeyError:
            pass
for q_ in ("expo", "gain", "stress"):
    try:
        REP[f"X1/{'exposure' if q_ == 'expo' else q_}"] = est(at("li4", "k1-corner/absorbing", corner, q_) - at("li4", "k8/absorbing", corner, q_))
        REP[f"X2/{'exposure' if q_ == 'expo' else q_}"] = est(at("li4", "k7-corner/absorbing", corner, q_) - at("li4", "k0/absorbing", corner, q_))
    except KeyError:
        pass
def struggling_by_case(body, lab, comp):
    """(blocks, cases): per case index c, the mean over the composition's struggling sheets with that index."""
    d = A[(body, lab)]
    sp = COMPOSITIONS[comp]
    return np.stack([np.mean([d[(g, p)]["a"].mean(1) for g in range(8) for p in sp if (g + p) % NC == c], axis=0)
                     for c in range(NC)], axis=1)


for b, suf in (("li4", ""), ("dw", "/dw")):
    for bnd in ("absorbing", "sealed"):
        for nm, ca, cb in (("CL", "k4-half", "k4-checker"), ("K2", "k2-adjacent", "k2-apart")):
            try:
                REP[f"{nm}/{bnd}{suf}"] = est(struggling_by_case(b, f"{ca}/{bnd}", ca) - struggling_by_case(b, f"{cb}/{bnd}", cb))
            except KeyError:
                pass
for k_, q_ in REP.items():
    say(f"  {k_}: {q_['v']:+.6f} [{q_['lo']:+.6f}, {q_['hi']:+.6f}]")
say("  the role means against k (li4, absorbing; a at the last read: struggling / healthy / the group):")
for comp in COMPOSITIONS:
    lab = f"{comp}/absorbing"
    cells = []
    for role in ("struggling", "healthy", "all"):
        r_ = ROLEV.get(("li4", lab, role))
        cells.append(f"{np.mean(r_['a']):.4f}" if r_ else "-")
    say(f"    {comp} (k {len(COMPOSITIONS[comp])}): " + " / ".join(cells))

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
    x5 = rd.get("x5_exact")
    say(f"\nAGAINST THE FROZEN READER ({READER}): {n_cmp} parts (values, intervals, SDs, halves, blocks; {n_th} thresholds, "
        f"kinds and verdicts) largest difference {worst:.2e}; {nr} reported items largest difference {rw:.2e}"
        + (f" (not recomputed: {', '.join(skipped)})" if skipped else "") + f"; {nl} level readings largest difference "
        f"{lw:.2e}; the reader's X5 record: {x5}")
    assert worst < 1e-12 and rw < 1e-12 and lw < 1e-12 and (x5 is None or (x5["exact"] and x5["largest_difference"] == 0.0))

name = f"p64c_sm008_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
