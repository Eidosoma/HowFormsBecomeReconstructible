"""P61c (python probes/p61c_sm007_lead_check.py ROOT [READER]): the lead's check of SM007, geometry and a shared field.
LEAD_CHECK_NOT_REGISTERED; a read of the stage's shards and saved final bodies and of the restored AR005 records, written by
the lead in reviewing SM007's phase A and committed before the freeze, dry-run first on P61 (AR005's P53 records,
engineering blocks 900729, 900739 | 900749, 900759) and on the debug run (900799, window 2,000); 5 November 2026; no
simulation of the tissue. It reads PLAN_SM007.md's words (with its amendments) and imports nothing of sm007 or msefield.

It checks:
1. integrity: every stage file against its manifest by sha256, every restored record against its own run's manifest, the
   acquisition rebuilt by ar001.sim.prepare equal to the record's V0, R0 and T; at the development stage the run's digest
   against sm007/frozen/design.json;
2. the layout: in every task each arrangement holds each of the task's cases exactly once (one recipient a case), so the
   arrangements are paired by case;
3. the endpoint: a_v = max(sign, 1 - sign), sign = dl001.sim.sign(V, T) of each saved final body against its case's T,
   equal to the shard's a_v and sign at the last read;
4. the parts M1-M6 and M9 by the plan's words: an arrangement's value for a case is its case's recipient's a_v; per case
   the mean over the four unit-body pairs (and the futures); a block the mean of its cases; the part the mean over the
   blocks; SD = max(block SD, case SD / sqrt(cases a block)); the 95% t interval;
5. G and M7, M8, independently: L_eff = 1 / sqrt(mu_1), mu_1 the least eigenvalue of -lap on the shape's absorbing domain,
   from the lead's own 5-point operator at m 8 (Dirichlet ghosts at the first outside site); x = L_eff / lambda; G the
   isotonic (pool-adjacent-violators) piecewise-linear curve of the pooled a_v against x through the six pilot shapes
   absorbing at lambda 0.5 on P61, constant beyond its end points; M7 each block's mean over the shapes of
   |a_block(shape) - G(x)| (on P61 the leave-one-out over the four interior shapes); M8 the same at lambda2 0.4. At the
   development stage G is refitted by the lead from the P61 root and must equal the frozen knots. The headcount
   competitor G_N is reported beside G;
6. on P61, the narrowest thresholds the rule allows, which must equal the registered ones; with READER, the frozen
   reader's parts, thresholds, verdicts and levels.
"""
import hashlib
import json
import math
import re
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
P61_ROOT = RUNS / "sm007" / "p61"
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
key = lambda s: s.replace("/", "_")
AR005_DEV = [910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798, 910799,
             910826, 910827, 910958]
WANT = {"probe": ("ar005/p53", [900729, 900739, 900749, 900759], "mse-p61", "engineering"),
        "debug": ("ar005/debug", [900799], "mse-sm007", "engineering"),
        "preflight": ("ar005/preflight", [900779, 900789], "mse-sm007", "engineering"),
        "development": ("ar005/development", AR005_DEV, "mse-sm007", "development")}
PAIRS = [("dw", "S4_t1"), ("dw", "F0_t1"), ("li4", "S4_t1"), ("li4", "F0_t1")]
SETS = {"particular (li4 x F0)": {("li4", "F0_t1")}, "native (li4 x S4)": {("li4", "S4_t1")},
        "permissive (dw)": {("dw", "S4_t1"), ("dw", "F0_t1")}}
SHAPES = {"iso8": [(0, 2 * j) for j in range(8)], "1x2": [(0, j) for j in range(2)],
          "2x2": [(r, c) for r in range(2) for c in range(2)], "1x4": [(0, j) for j in range(4)],
          "2x4": [(r, c) for r in range(2) for c in range(4)], "1x8": [(0, j) for j in range(8)],
          "1x3": [(0, j) for j in range(3)], "2x3": [(r, c) for r in range(2) for c in range(3)],
          "1x6": [(0, j) for j in range(6)],
          # the new shapes as the plan declares them (PLAN_SM007.md's table; the cells written out by the lead)
          "L4": [(0, 0), (1, 0), (2, 0), (2, 1)], "T4": [(0, 0), (0, 1), (0, 2), (1, 1)],
          "plus5": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)], "L6": [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2)],
          "sq8": [(r, c) for r in range(3) for c in range(3) if (r, c) != (2, 2)]}
PILOT_SHAPES = ("iso8", "1x2", "2x2", "1x4", "2x4", "1x8")
NEW_SHAPES = ("1x3", "2x3", "1x6", "L4", "T4", "plus5", "L6", "sq8")
LAMBDA, LAMBDA2 = 0.5, 0.4
GAMMA, SITES, LEAKS = 0.0625, {0.5: 8, 0.4: 10, 2.0: 4}, {"absorbing": 1.0, "half": 0.5, "sealed": 0.0}
RESCUED = 0.95                       # the plan: a sheet is rescued where a_v >= 0.95


def load_stage(root):
    M = json.load(open(root / "manifest.json"))
    stage = M["stage"]
    src, blocks, ftag, purpose = WANT[stage]
    bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(root / f["path"]) != f["sha256"]]
    assert M.get("study", "SM007") == "SM007" and not bad, bad[:5]
    return M, stage, src, blocks, ftag, purpose


def read_stage(root, check=True):
    """{label: (blocks, pairs, futures, cases) a_v at the last read}, the arrangements, and the counters."""
    M, stage, src, blocks, ftag, purpose = load_stage(root)
    SM = json.load(open(RUNS / src / "manifest.json"))
    val, valr, arrs, cnt = {}, {}, None, {"tasks": 0, "rescored": 0, "sheets": 0, "maxdiff": 0.0, "futures": set()}
    files = sorted((root / "shards" / key(src)).glob("*/*/*.npz"))
    for f in files:
        z = np.load(f)
        meta = json.loads(str(z["__meta__"]))
        body, unit, blk = meta["body"], meta["unit"], int(meta["block"])
        assert meta["source"] == src and meta["tag"] == ftag and meta["stage"] == stage and (body, unit) in PAIRS
        assert blk in blocks
        if arrs is None:
            arrs = [tuple(a) for a in meta["arrangements"]]
        assert [tuple(a) for a in meta["arrangements"]] == arrs
        if check:
            f_src = SM["tasks"][f"{body}/{unit}/{blk}"]["files"]["raw"]
            assert sha(RUNS / src / f_src["path"]) == f_src["sha256"] == meta["rawfile"]["sha256"]
            raw = np.load(RUNS / src / f_src["path"])
            pattern, theta = A1D.parse_unit(unit)
            cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, purpose)
            assert [list(c.key()) for c in cases] == [list(c) for c in meta["cases"]]
            assert np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"]) and np.array_equal(T, raw["T"])
        k = len(meta["cases"])
        br_case_all, br_arr_all = z["br_case"], z["br_arr"]
        # two layouts: one future a file (meta "future"), or the futures concatenated future-major with br_future
        br_fut = z["br_future"] if "br_future" in z.files else np.full(len(br_case_all), int(meta.get("future", 0)))
        if "br_future" in z.files:
            nf_ = int(meta["futures"])
            bpf = int(meta["branches_a_future"])
            assert br_fut.tolist() == [f_ for f_ in range(nf_) for _ in range(bpf)], "not future-major"
        for fut in sorted(set(br_fut.tolist())):
          cnt["futures"].add(fut)
          fsel = br_fut == fut
          br_case, br_arr = br_case_all[fsel], br_arr_all[fsel]
          for ai, (lab_, shape_, _b, kind_, _l) in enumerate(arrs):
            # the plan's layout: a field arrangement covers the task's cases in ceil(k / N) groups of N taken cyclically
            # (every case at least once); a no-field arrangement is one group of all k
            if kind_ in ("nofield", "undisturbed"):
                want = list(range(k))
            else:
                n_ = len(SHAPES[shape_])
                want = [(g * n_ + i) % k for g in range(math.ceil(k / n_)) for i in range(n_)]
            assert br_case[br_arr == ai].tolist() == want, (f, ai, lab_, fut)
          a_last, s_last = z["a_v"][-1][fsel], z["sign"][-1][fsel]
          if check:
            zr = np.load(root / "raw" / key(src) / body / unit / f"{blk}.npz")
            V = zr["V"][fsel]
            assert np.array_equal(zr["br_case"][fsel], br_case)
            sg = S.sign(V, np.asarray(T, float)[br_case])
            a = np.maximum(sg, 1 - sg)
            cnt["maxdiff"] = max(cnt["maxdiff"], float(np.abs(sg - s_last).max()), float(np.abs(a - a_last).max()))
            cnt["rescored"] += len(br_case)
          cnt["sheets"] += len(br_case)
          bi, pi = blocks.index(blk), PAIRS.index((body, unit))
          for ai, a_ in enumerate(arrs):
            lab = a_[0]
            arr = val.setdefault(lab, {})
            sel = np.flatnonzero(br_arr == ai)
            v = np.array([a_last[sel][br_case[sel] == c].mean() for c in range(k)])   # the mean over the case's sheets
            arr[(bi, pi, fut)] = v
            valr.setdefault(lab, {})[(bi, pi, fut)] = np.array(
                [(a_last[sel][br_case[sel] == c] >= RESCUED).mean() for c in range(k)])   # the plan's "rescued"
        cnt["tasks"] += 1
    futs = sorted(cnt["futures"])
    nb = len(blocks)
    VAL, VALR = {}, {}
    for out_, src_ in ((VAL, val), (VALR, valr)):
        for lab, d in src_.items():
            A = np.full((nb, len(PAIRS), len(futs), len(next(iter(d.values())))), np.nan)
            for (bi, pi, fut), v in d.items():
                A[bi, pi, futs.index(fut)] = v
            assert not np.isnan(A).any(), (lab, "an arrangement missing in some task")
            out_[lab] = A
    cnt["VALR"] = VALR
    return M, stage, blocks, arrs, VAL, cnt


M, STAGE, BLOCKS, ARRS, VAL, CNT = read_stage(ROOT)
NB = len(BLOCKS)
KC = next(iter(VAL.values())).shape[-1]
if STAGE == "development":
    fz = json.load(open(LANE / "sm007" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"
say(f"P61c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): {CNT['tasks']} "
    f"task-files, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; {len(ARRS)} arrangements; "
    f"futures {sorted(CNT['futures'])}; every restored record's sha256 and rebuilt acquisition equal")
say(f"  the layout: in every task every arrangement covers its {KC} cases in the plan's cyclic groups (every case at least "
    f"once; a case's value the mean over its sheets), the same births and noise per case in every arrangement")
say(f"  the endpoint rescored from the saved final bodies ({CNT['rescored']} sheets): largest |difference| in sign and "
    f"a_v {CNT['maxdiff']:.1e}")
assert CNT["maxdiff"] < 1e-12


def X(lab):
    """(blocks, cases): per case the mean over the pairs and the futures."""
    return VAL[lab].mean(axis=(1, 2))


def X_sub(lab, sub):
    ix = [i for i, p in enumerate(PAIRS) if p in sub]
    return VAL[lab][:, ix].mean(axis=(1, 2))


T975 = stats.t.ppf(0.975, NB - 1) if NB > 1 else float("nan")
K = 3 * math.sqrt(1 / 4 + 1 / 16)


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


# ------------------------------------------------------------------------------------------- L_eff, x and G (the lead's)
def shape_cells(shape):
    return SHAPES[shape]


def l_eff(cells, m=8):
    """1 / sqrt(mu_1), mu_1 the least eigenvalue of -lap (5-point, spacing 1/m, Dirichlet ghosts outside the cells)."""
    cells = [tuple(c) for c in cells]
    r0, c0 = min(r for r, _ in cells), min(c for _, c in cells)
    sites = {}
    for (r, c) in cells:
        for i in range(m):
            for j in range(m):
                sites[((r - r0) * m + i, (c - c0) * m + j)] = None
    idx = {s: n for n, s in enumerate(sorted(sites))}
    n = len(idx)
    A = np.zeros((n, n))
    h2 = (1.0 / m) ** 2
    for (i, j), a in idx.items():
        A[a, a] = 4.0 / h2
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b = idx.get((i + di, j + dj))
            if b is not None:
                A[a, b] = -1.0 / h2
    return 1.0 / math.sqrt(float(np.linalg.eigvalsh(A).min()))


def isotonic(y):
    blocks = [[float(v), 1] for v in y]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            w = blocks[i][1] + blocks[i + 1][1]
            blocks[i] = [(blocks[i][0] * blocks[i][1] + blocks[i + 1][0] * blocks[i + 1][1]) / w, w]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return np.array([v for v, w in blocks for _ in range(w)])


def fit(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    ux = np.unique(xs)
    uy = np.array([ys[xs == u].mean() for u in ux])
    return {"x": ux.tolist(), "y": isotonic(uy).tolist()}


curve = lambda kn, x: float(np.interp(x, kn["x"], kn["y"]))
LEFF = {}


def leff_of(shape, cells=None):
    if shape not in LEFF:
        LEFF[shape] = l_eff([(0, 0)] if shape == "iso8" else (cells if cells is not None else shape_cells(shape)))
    return LEFF[shape]


def field_f(shape, lam, boundary="absorbing"):
    """The plan's f, written by the lead: each sheet's steady exposure under a uniform emission, in units of the
    boundary-free level emission / gamma, from the lead's own 5-point operator: spacing 1/m (m = the plan's sites a cell
    at lam), D = gamma lam^2, decay gamma, a ghost (1 - leak) c at the first outside site; the arrangement's mean over its
    sheets (iso8: one isolated cell, its eight cells disconnected)."""
    m, Dd, leak = SITES[lam], GAMMA * lam ** 2, LEAKS[boundary]
    cells = [(0, 0)] if shape == "iso8" else [tuple(c) for c in SHAPES[shape]]
    site_cell = {}
    for ci, (r, c) in enumerate(cells):
        for i in range(m):
            for j in range(m):
                site_cell[(r * m + i, c * m + j)] = ci
    idx = {st: n for n, st in enumerate(sorted(site_cell))}
    n = len(idx)
    h2 = (1.0 / m) ** 2
    A = np.zeros((n, n))
    for (i, j), a_ in idx.items():
        diag = 4.0
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b_ = idx.get((i + di, j + dj))
            if b_ is not None:
                A[a_, b_] = -Dd / h2
            else:
                diag -= 1.0 - leak
        A[a_, a_] = Dd * diag / h2 + GAMMA
    cval = np.linalg.solve(A, np.full(n, GAMMA))
    cell_of = np.array([site_cell[st] for st in sorted(site_cell)])
    return float(np.mean([cval[cell_of == ci].mean() for ci in range(len(cells))]))


FF = {}


def ff_of(shape, lam):
    if (shape, lam) not in FF:
        FF[(shape, lam)] = field_f(shape, lam)
    return FF[(shape, lam)]


def pilot_knots():
    """G refitted by the lead from P61's pooled pilot values (the probe root)."""
    if STAGE == "probe":
        vals = {s: float(X(f"{s}/absorbing").mean()) for s in PILOT_SHAPES}
    else:
        _M, _st, _b, _a, V61, _c = read_stage(P61_ROOT, check=False)
        vals = {s: float(V61[f"{s}/absorbing"].mean(axis=(1, 2)).mean()) for s in PILOT_SHAPES}
    return fit([leff_of(s) / LAMBDA for s in PILOT_SHAPES], [vals[s] for s in PILOT_SHAPES]), vals


KNOTS, PILOT_VALS = pilot_knots()
KNOTS_N = fit([1.0 if t == "iso8" else float(len(SHAPES[t])) for t in PILOT_SHAPES], [PILOT_VALS[t] for t in PILOT_SHAPES])
KNOTS_F = fit([ff_of(t, LAMBDA) for t in PILOT_SHAPES], [PILOT_VALS[t] for t in PILOT_SHAPES])


def g_error(which, knots, cov="x"):
    """(blocks, 1): each block's mean over the shapes of |a_block - curve(covariate)|."""
    if which == "M7":
        cells = [(s, LAMBDA, f"{s}/absorbing") for s in (("1x2", "1x4", "1x8", "2x2") if STAGE == "probe" else NEW_SHAPES)]
    else:
        cells = [(s, LAMBDA2, f"{s}/absorbing/l2") for s in (PILOT_SHAPES if STAGE == "probe" else PILOT_SHAPES + NEW_SHAPES)]
    errs = []
    for s, lam, lab in cells:
        if lab not in VAL:
            return None
        lv = X(lab).mean(1)
        if which == "M7" and STAGE == "probe" and cov == "x":
            shapes = [t for t in PILOT_SHAPES if t != s]
            kn = fit([leff_of(t) / LAMBDA for t in shapes], [PILOT_VALS[t] for t in shapes])
        elif cov == "N":
            shapes = [t for t in PILOT_SHAPES if not (which == "M7" and STAGE == "probe" and t == s)]   # leave-one-out as G
            kn = fit([1.0 if t == "iso8" else float(len(SHAPES[t])) for t in shapes], [PILOT_VALS[t] for t in shapes])
        elif cov == "f":
            shapes = [t for t in PILOT_SHAPES if not (which == "M7" and STAGE == "probe" and t == s)]   # leave-one-out as G
            kn = fit([ff_of(t, LAMBDA) for t in shapes], [PILOT_VALS[t] for t in shapes])
        else:
            kn = knots
        xv = {"N": lambda: 1.0 if s == "iso8" else float(len(SHAPES[s])), "f": lambda: ff_of(s, lam),
              "x": lambda: leff_of(s) / lam}[cov]()
        errs.append(np.abs(lv - curve(kn, xv)))
    return np.mean(errs, axis=0)[:, None]


say(f"\n  G refitted by the lead from P61's pilot values (x = L_eff / lambda from the lead's own operator, m 8): knots "
    + ", ".join(f"({x:.4f}, {y:.4f})" for x, y in zip(KNOTS["x"], KNOTS["y"])))
if STAGE == "development":
    pz = json.load(open(LANE / "sm007" / "frozen" / "predictions.json"))
    fk = pz.get("G") or pz.get("knots")
    assert fk is not None and np.allclose(fk["x"], KNOTS["x"], atol=1e-9) and np.allclose(fk["y"], KNOTS["y"], atol=1e-12), (fk, KNOTS)
    say("  the frozen G equals the lead's refit")
    for nm_, kn_ in (("G_N", KNOTS_N), ("G_f", KNOTS_F)):
        fk_ = pz[nm_]
        assert np.allclose(fk_["x"], kn_["x"], atol=1e-9) and np.allclose(fk_["y"], kn_["y"], atol=1e-12), (nm_, fk_, kn_)
    say("  the frozen G_N and G_f equal the lead's refits (G_f against the lead's own f)")

TH = {"M1": ("least", 0.02), "M2": ("least", 0.01), "M3": ("least", 0.07), "M4": ("least", 0.05),
      "M5": ("band", (-0.02, 0.01)), "M6": ("band", (-0.02, 0.02)), "M7": ("most", 0.03), "M8": ("most", 0.03),
      "M9": ("band", (-0.005, 0.005))}
D2 = lambda a, b: (lambda f: f(a) - f(b))
PARTS = [("M1", "a(2x4/absorbing) - a(1x8/absorbing)", D2("2x4/absorbing", "1x8/absorbing")),
         ("M2", "a(2x2/absorbing) - a(1x4/absorbing)", D2("2x2/absorbing", "1x4/absorbing")),
         ("M3", "a(1x8/sealed) - a(1x8/absorbing)", D2("1x8/sealed", "1x8/absorbing")),
         ("M4", "a(2x4/absorbing) - a(iso8/absorbing)", D2("2x4/absorbing", "iso8/absorbing")),
         ("M5", "a(2x4/absorbing) - a(2x4/absorbing/uniform)", D2("2x4/absorbing", "2x4/absorbing/uniform")),
         ("M6", "a(2x4/absorbing/rearranged) - a(2x4/absorbing)", D2("2x4/absorbing/rearranged", "2x4/absorbing")),
         ("M7", "G's mean absolute error, the new shapes at lambda (P61: interior leave-one-out)", "M7"),
         ("M8", "G's mean absolute error, absorbing at lambda2", "M8"),
         ("M9", "a(2x4/sealed) - a(1x8/sealed)", D2("2x4/sealed", "1x8/sealed"))]
say(f"\nTHE PARTS ({NB} blocks x {KC} cases; per case the mean over the four pairs and the futures; [95% t interval]"
    + (f"; the rule: margin >= {K:.4f} and both halves" if STAGE == "probe" else "") + ")")
Q, OK = {}, {}
for pid, words, fn in PARTS:
    if isinstance(fn, str):
        x = g_error(fn, KNOTS)
        if x is None:
            say(f"  {pid} {words}: not available at this stage")
            continue
    else:
        try:
            x = fn(X)
        except KeyError:
            say(f"  {pid} {words}: not available at this stage")
            continue
    q = Q[pid] = est(x)
    kd, th = TH[pid]
    line = (f"  {pid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD {q['sd']:.6f}: block {q['sdb']:.6f}, "
            f"case/sqrt{x.shape[1]} {q['sdc']:.6f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})")
    if STAGE == "probe":
        lo, hi = narrow_num(q)
        line += f"; the narrowest [{lo:+.3f}, {hi:+.3f}]"
        assert ((lo, hi) == th) if kd == "band" else (abs(lo - th) < 1e-9 if kd == "least" else abs(hi - th) < 1e-9), (pid, lo, hi, th)
    OK[pid] = (th[0] <= q["v"] <= th[1]) if kd == "band" else (q["v"] >= th if kd == "least" else q["v"] <= th)
    line += f"; registered {list(th) if kd == 'band' else ('>= ' if kd == 'least' else '<= ') + str(th)}: {'HOLDS' if OK[pid] else 'FAILS'}"
    say(line)
    if not isinstance(fn, str):
        say("      by item set: " + "; ".join(f"{nm} {est(fn(lambda l, sb=sb: X_sub(l, sb)))['v']:+.6f}" for nm, sb in SETS.items()))
if OK:
    say("  VERDICTS (development: the point value against the registered threshold or band): "
        + ", ".join(f"{p} {'HOLDS' if v else 'FAILS'}" for p, v in OK.items()) + ("" if STAGE == "development" else "  [not a development result]"))

say("\nREPORTED (the lead's)")
say("  the plan's f by the lead's operator, checked against the plan's own values: sealed "
    + ", ".join(f"{s_} {field_f(s_, LAMBDA, 'sealed'):.12f}" for s_ in ("2x4", "1x8")) + "; half leak at lambda 0.5 "
    + ", ".join(f"{s_} {field_f(s_, LAMBDA, 'half'):.3f}" for s_ in ("2x4", "1x8")) + " (the plan: 0.557 and 0.391)")
assert all(abs(field_f(s_, LAMBDA, "sealed") - 1) < 1e-12 for s_ in ("2x4", "1x8"))
assert abs(round(field_f("2x4", LAMBDA, "half"), 3) - 0.557) < 1e-9 and abs(round(field_f("1x8", LAMBDA, "half"), 3) - 0.391) < 1e-9
say("  f absorbing at lambda (the lead's): " + ", ".join(f"{s_} {ff_of(s_, LAMBDA):.4f}" for s_ in PILOT_SHAPES + NEW_SHAPES))
COMP = {}
for which in ("M7", "M8"):
    errs = {cv: g_error(which, {"x": KNOTS, "N": KNOTS_N, "f": KNOTS_F}[cv], cov=cv) for cv in ("x", "N", "f")}
    if any(v is None for v in errs.values()):
        continue
    for cv, v in errs.items():
        COMP[f"C{which[1]}/{cv}"] = est(v)
    for o in ("N", "f"):
        COMP[f"C{which[1]}/x-{o}"] = est(errs["x"] - errs[o])
    say(f"  {which}'s cells: G's error {errs['x'].mean():.6f}, the headcount curve G_N's {errs['N'].mean():.6f}, the "
        f"field-factor curve G_f's {errs['f'].mean():.6f}; G - G_N by block {COMP[f'C{which[1]}/x-N']['v']:+.6f} "
        f"[{COMP[f'C{which[1]}/x-N']['lo']:+.6f}, {COMP[f'C{which[1]}/x-N']['hi']:+.6f}]; G - G_f "
        f"{COMP[f'C{which[1]}/x-f']['v']:+.6f} [{COMP[f'C{which[1]}/x-f']['lo']:+.6f}, {COMP[f'C{which[1]}/x-f']['hi']:+.6f}]")
VALR = CNT["VALR"]
XR = lambda lab: VALR[lab].mean(axis=(1, 2))
XR_sub = lambda lab, sub: VALR[lab][:, [i for i, p in enumerate(PAIRS) if p in sub]].mean(axis=(1, 2))
PAT = re.compile(r"\b(a|rescued)\(([^)]+)\) - (a|rescued)\(([^)]+)\)")   # after any prefix ("shared point: ", ...)


def contrast(words, sub=None):
    """'a(X) - a(Y)' or 'rescued(X) - rescued(Y)' by the plan's pooling; None if the words are another kind."""
    mt = PAT.search(words)
    if not mt or mt.group(1) != mt.group(3):
        return None
    if mt.group(1) == "a":
        f_ = X if sub is None else (lambda l: X_sub(l, sub))
    else:
        f_ = XR if sub is None else (lambda l: XR_sub(l, sub))
    return f_(mt.group(2)) - f_(mt.group(4))


DECL = json.load(open(LANE / "sm007" / "frozen" / "predictions.json"))["reported"] if (LANE / "sm007" / "frozen" / "predictions.json").exists() else []
say("  the paper's stress (reported; all pairs [95% t]; li4 x F0):")
for it in DECL:
    if it["id"].startswith("RP"):
        try:
            x_ = contrast(it["part"])
        except KeyError:
            x_ = None
        if x_ is not None:
            q_ = est(x_)
            say(f"    {it['id']} {it['part']}: {q_['v']:+.6f} [{q_['lo']:+.6f}, {q_['hi']:+.6f}]; li4 x F0 "
                f"{est(contrast(it['part'], SETS['particular (li4 x F0)']))['v']:+.6f}")
say("  x = L_eff / lambda (the lead's operator): " + ", ".join(f"{s} {leff_of(s) / LAMBDA:.4f}" for s in PILOT_SHAPES + NEW_SHAPES))
say("  the levels at 8,000 (all pairs; li4 x F0): " + "; ".join(
    f"{lab} {X(lab).mean():.4f} ({X_sub(lab, SETS['particular (li4 x F0)']).mean():.4f})" for lab in sorted(VAL)))

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
        for a, b in (("value", q["v"]), ("sd", q["sd"])):
            worst = max(worst, abs(rp[a] - b))
        worst = max(worst, max(abs(x - y) for x, y in zip(rp["blocks"], q["blocks"])))
        if NB > 1:
            worst = max(worst, abs(rp["ci95"][0] - q["lo"]), abs(rp["ci95"][1] - q["hi"]),
                        max(abs(x - y) for x, y in zip(rp["halves"], q["halves"])))
        if rp.get("threshold") is not None:
            kd, th = TH[pid]
            assert (list(rp["threshold"]) == list(th)) if kd == "band" else abs(rp["threshold"] - th) < 1e-12, (pid, rp["threshold"])
            assert rp["holds"] == OK[pid], pid
            n_th += 1
        n_cmp += 1
    lw, nl = 0.0, 0
    WIN = int(json.loads(str(np.load(next((ROOT / "shards").rglob("*.npz")))["__meta__"]))["window"])
    for lab, rec in rd.get("levels", {}).items():
        if lab in VAL and isinstance(rec, dict) and f"a_{WIN}" in rec:
            lw = max(lw, abs(rec[f"a_{WIN}"] - float(X(lab).mean())))
            nl += 1
    NAMES = {"native": SETS["native (li4 x S4)"], "particular": SETS["particular (li4 x F0)"],
             "permissive": SETS["permissive (dw)"]}
    rw, nrep, ncomp, skipped = 0.0, 0, 0, []
    for it in rd.get("reported", []):
        if not it.get("available", True):
            continue
        if it["id"] in COMP:
            q_ = COMP[it["id"]]
            rw = max(rw, abs(it["value"] - q_["v"]))
            if NB > 1 and it.get("ci95") and not any(isinstance(v, float) and math.isnan(v) for v in it["ci95"]):
                rw = max(rw, abs(it["ci95"][0] - q_["lo"]), abs(it["ci95"][1] - q_["hi"]))
            ncomp += 1
            continue
        try:
            x_ = contrast(it["part"])
        except KeyError:
            x_ = None
        if x_ is None:
            skipped.append(it["id"])
            continue
        q_ = est(x_)
        rw = max(rw, abs(it["value"] - q_["v"]), max(abs(a_ - b_) for a_, b_ in zip(it["blocks"], q_["blocks"])))
        if NB > 1:
            rw = max(rw, abs(it["sd"] - q_["sd"]), abs(it["ci95"][0] - q_["lo"]), abs(it["ci95"][1] - q_["hi"]))
        for nm_, sb in NAMES.items():
            if "by_item_set" in it:
                rw = max(rw, abs(it["by_item_set"][nm_]["value"] - est(contrast(it["part"], sb))["v"]))
        nrep += 1
    say(f"\n  the reader's reported items: {nrep} contrasts (a and rescued; values, SDs, intervals, blocks, item sets) and "
        f"{ncomp} competitor errors recomputed by the lead, largest difference {rw:.2e}"
        + (f"; not recomputed: {', '.join(skipped)}" if skipped else ""))
    assert rw < 1e-12 and nrep > 0
    for nm_, kn_ in (("G_N", KNOTS_N), ("G_f", KNOTS_F)):
        if rd.get(nm_):
            assert np.allclose(rd[nm_]["x"], kn_["x"], atol=1e-9) and np.allclose(rd[nm_]["y"], kn_["y"], atol=1e-12), (nm_, rd[nm_], kn_)
            say(f"  the reader's {nm_} equals the lead's refit")
    gk = rd.get("G")
    if gk is None and rd.get("G_source"):
        src_ = json.load(open(LANE / rd["G_source"]))
        gk = src_.get("G") or (src_.get("knots") if isinstance(src_.get("knots"), dict) else None)
    gw = max(max(abs(a - b) for a, b in zip(gk["x"], KNOTS["x"])), max(abs(a - b) for a, b in zip(gk["y"], KNOTS["y"]))) if gk else float("nan")
    say(f"\nAGAINST THE FROZEN READER ({READER}): {n_cmp} parts (values, intervals, SDs, halves, blocks; {n_th} thresholds and "
        f"verdicts) largest difference {worst:.2e}; {nl} levels, largest difference {lw:.2e}; G's knots {gw:.2e}")
    assert worst < 1e-12 and lw < 1e-12 and (gk is None or gw < 1e-9)

name = f"p61c_sm007_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
