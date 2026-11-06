"""SM007's reader: the statement candidates (M1-M9), the frozen predictor G, the reported parts, the lane's margin rule and
the freeze. DRAFT (phase A).

python -m sm007.predict --root STAGE_ROOT --out DIR     ->  DIR/predictions_scored.json
python -m sm007.predict --margins --root STAGE_ROOT     ->  the rule's narrowest thresholds on the pilot (P61b), and G
python -m sm007.predict --freeze                         ->  sm007/frozen/predictions.json (phase B, on the lead's word)

Pooling (the AR studies'): an arrangement's value for a case is the mean over that case's sheets in the arrangement; per
case the mean over the unit-body pairs; a block's value the mean of its cases; a part the mean over the blocks. SD =
max(block SD, case SD / sqrt(cases a block)). On the pilot each part must sit K_RULE SD inside its threshold and pass in
both halves; thresholds are the narrowest round values the rule allows (hundredths, or 0.005 within 0.01 of zero).
Development intervals: mean +- t(0.975, n - 1) SD / sqrt n. A part is pooled only where every task of the stage has every
term; anything less is marked unavailable with its task count.
G (PLAN_SM007.md): the isotonic (non-decreasing) piecewise-linear curve of the pooled a_v at 8,000 against x = L_eff /
lambda through the six pilot shapes absorbing at lambda 0.5 on P61, constant beyond its end points; frozen with the
thresholds. M7 and M8 are G's mean absolute errors, per block over the shapes; on P61 M7 is the leave-one-shape-out error
over the four interior pilot shapes and M8 the error on the six pilot shapes at lambda2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sm007 import design as D  # noqa: E402
from sm007 import sim  # noqa: E402

K_RULE = D.K_RULE
FROZEN = LANE / "sm007" / "frozen" / "predictions.json"
P61B = LANE / "probes" / "results" / "p61b_sm007_margins.json"
# the registered thresholds: P61b's narrowest by the rule, registered by the lead's phase-A ruling 1 (13:01:00Z)
TH = {"M1": 0.02, "M2": 0.01, "M3": 0.07, "M4": 0.05, "M5": (-0.02, 0.01), "M6": (-0.02, 0.02), "M7": 0.03, "M8": 0.03,
      "M9": (-0.005, 0.005)}
INTERIOR = ("1x2", "1x4", "1x8", "2x2")  # M7's leave-one-out shapes on P61


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(root, check=True):
    """Every task's endpoints and its branch maps, checked by sha256 against the stage's manifest."""
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    tasks = []
    for name, t in sorted(M["tasks"].items()):
        f = t["files"]["shards"]
        path = root / f["path"]
        if check and sha(path) != f["sha256"]:
            raise ValueError(f"{name}: the shard's sha256 differs from the manifest's")
        z = np.load(path)
        meta = json.loads(str(z["__meta__"]))
        ends = {k: z[k] for k in z.files if k != "__meta__"}
        labels = [a[0] for a in meta["arrangements"]]
        tasks.append({"name": name, "meta": meta, "ends": ends, "block": meta["block"], "body": meta["body"],
                      "unit": meta["unit"], "stage": meta["stage"], "labels": labels})
    return tasks, M


# ---------------------------------------------------------------- per-case vectors
def case_vec(t, label, key="a_v", read=None, fn=None):
    """Per case (0..k-1): the mean over that case's sheets in the arrangement; None if the arrangement is absent."""
    if label not in t["labels"]:
        return None
    ai = t["labels"].index(label)
    e = t["ends"]
    if key in ("a_v", "sign"):
        reads = list(e["reads"])
        r = reads.index(D.WINDOW if read is None else read) if (D.WINDOW if read is None else read) in reads else None
        if r is None:
            if read is None and reads:
                r = len(reads) - 1          # a short (debug) window: its last read
            else:
                return None
        v = e[key][r]
    else:
        v = e[key]
    if fn is not None:
        v = fn(v)
    k = len(t["meta"]["cases"])
    out = np.empty(k)
    for j in range(k):
        b = (e["br_arr"] == ai) & (e["br_case"] == j)
        if not b.any():
            raise ValueError(f"{t['name']} {label}: case {j} has no sheet")
        out[j] = v[b].mean()
    return out


def lin(*terms, key="a_v", read=None, fn=None):
    """A per-case linear combination of arrangements' per-case values: terms (label, coefficient)."""
    def f(t):
        vals = [(c, case_vec(t, lab, key, read, fn)) for lab, c in terms]
        if any(v is None for _c, v in vals):
            return None
        return sum(c * v for c, v in vals)
    return f


def block_matrix(tasks, fn, subset=None):
    """(blocks, cases): per case the mean over the unit-body pairs; the block order ascending; and the coverage
    (tasks with every term, tasks in scope). None for x if any task in scope lacks a term (partial coverage)."""
    by, have, scope = {}, 0, 0
    for t in tasks:
        if subset is not None and (t["body"], t["unit"]) not in subset:
            continue
        scope += 1
        v = fn(t)
        if v is not None:
            have += 1
            by.setdefault(t["block"], []).append(v)
    if not by or have < scope:
        return None, [], (have, scope)
    blocks = sorted(by)
    return np.array([np.mean(by[b], axis=0) for b in blocks]), blocks, (have, scope)


def sd_rule(x):
    nb, nc = x.shape
    blk = x.mean(1)
    sd_b = float(blk.std(ddof=1)) if nb > 1 else float("nan")
    sd_c = float(x.ravel().std(ddof=1) / math.sqrt(nc)) if x.size > 1 else float("nan")
    if nc == 1:                              # a block-level quantity (G's errors): the block SD alone
        return sd_b, sd_b, sd_b
    return (max(sd_b, sd_c) if nb > 1 else sd_c), sd_b, sd_c


def value(x, blocks, stage):
    nb = x.shape[0]
    sd, sd_b, sd_c = sd_rule(x)
    v = float(x.mean())
    hw = stats.t.ppf(0.975, nb - 1) * sd / math.sqrt(nb) if nb > 1 else float("nan")
    H = D.HALVES.get(stage)
    if H is not None and all(b in blocks for h in H for b in h):
        halves = [float(np.mean([x[blocks.index(b)].mean() for b in h])) for h in H]
    else:
        halves = [float("nan"), float("nan")]
    return {"value": v, "ci95": [v - hw, v + hw], "sd": sd, "sd_block": sd_b, "sd_case": sd_c, "halves": halves,
            "blocks": x.mean(1).tolist(), "n_blocks": nb, "n_cases_a_block": int(x.shape[1])}


def _step(edge):
    return D.STEP_NEAR0 if abs(edge) < 0.01 else D.STEP


def narrowest(v, sd, halves, kind):
    need = K_RULE * sd
    lo, hi = min(v - need, *halves), max(v + need, *halves)
    flo = lambda x: round(math.floor(round(x / _step(x), 9)) * _step(x), 3)
    cei = lambda x: round(math.ceil(round(x / _step(x), 9)) * _step(x), 3)
    if kind == "in":
        return [flo(lo), cei(hi)]
    if kind == "ge":
        return flo(lo)
    return cei(hi)


def registers(kind, nar):
    if nar is None:
        return None
    return kind == "in" or (kind == "ge" and nar > 0) or (kind == "le" and nar <= D.AT_MOST_MAX)


# ---------------------------------------------------------------- G, the predictor of a against x = L_eff / lambda
LEFF = {}


def x_of(shape, lam):
    if shape not in LEFF:
        LEFF[shape] = sim.l_eff(shape)
    return LEFF[shape] / lam


def isotonic(y):
    """Pool-adjacent-violators, equal weights: the non-decreasing fit to y (in the given order)."""
    blocks = [[float(v), 1] for v in y]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            m = (blocks[i][0] * blocks[i][1] + blocks[i + 1][0] * blocks[i + 1][1]) / (blocks[i][1] + blocks[i + 1][1])
            blocks[i] = [m, blocks[i][1] + blocks[i + 1][1]]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return np.array([m for m, w in blocks for _ in range(w)])


def fit_curve(xs, ys):
    """The knots of a monotone piecewise-linear curve through (xs, ys): sorted, isotonic, ties in x averaged first."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    ux = np.unique(xs)
    uy = np.array([ys[xs == u].mean() for u in ux])
    return {"x": ux.tolist(), "y": isotonic(uy).tolist()}


def curve(knots, x):
    return float(np.interp(x, knots["x"], knots["y"]))       # constant beyond the end points


def pooled(tasks, label):
    x, _b, _c = block_matrix(tasks, lin((label, 1.0)))
    return None if x is None else float(x.mean())


def block_levels(tasks, label):
    x, blocks, _c = block_matrix(tasks, lin((label, 1.0)))
    return (None, []) if x is None else (x.mean(1), blocks)


def fit_by(tasks, cov="x", exclude=()):
    """The monotone curve of the pilot shapes' pooled a (absorbing, lambda 0.5) against cov: "x" (G), "N" (headcount,
    G_N) or "f" (the field factor, G_f); exclude: shapes left out (the leave-one-out on P61)."""
    shapes = [s for s in D.PILOT_SHAPES if s not in exclude]
    ys = [pooled(tasks, f"{s}/absorbing") for s in shapes]
    if any(y is None for y in ys):
        return None
    return fit_curve([covariate(s, D.LAMBDA, cov) for s in shapes], ys)


def fit_G(tasks, exclude=()):
    return fit_by(tasks, "x", exclude)


def covariate(shape, lam, cov):
    if cov == "x":
        return x_of(shape, lam)
    if cov == "N":
        return 1.0 if shape == "iso8" else float(len(D.SHAPES[shape]))
    return float(sim.field_factor(shape, "absorbing", lam).mean())


def g_error(tasks, which, knots=None, cov="x"):
    """(blocks, 1): each block's mean over the shapes of |a_block(shape) - curve(covariate(shape))|. which: "M7" or "M8";
    on the probe stage M7 is the leave-one-out error over INTERIOR (G refitted from the pooled pilot values)."""
    stage = tasks[0]["stage"]
    loo = which == "M7" and stage == "probe"
    if which == "M7":
        cells = [(s, D.LAMBDA, f"{s}/absorbing") for s in (INTERIOR if stage == "probe" else D.NEW_SHAPES)]
    else:
        cells = [(s, D.LAMBDA2, f"{s}/absorbing/l2") for s in (D.PILOT_SHAPES if stage == "probe" else
                                                               D.PILOT_SHAPES + D.NEW_SHAPES)]
    errs, blocks0 = [], None
    for s, lam, label in cells:
        lv, blocks = block_levels(tasks, label)
        if lv is None:
            return None, [], (0, len(tasks))
        kn = fit_by(tasks, cov, exclude=(s,)) if loo else knots
        if kn is None:
            return None, [], (0, len(tasks))
        errs.append(np.abs(lv - curve(kn, covariate(s, lam, cov))))
        blocks0 = blocks
    return np.mean(errs, axis=0)[:, None], blocks0, (len(tasks), len(tasks))


def frozen_G():
    """G's knots: the frozen record's, else P61b's (phase A), else None."""
    for path in (FROZEN, P61B):
        if path.exists():
            rec = json.loads(path.read_text())
            if rec.get("G"):
                return rec["G"], rec.get("G_N"), rec.get("G_f"), str(path.relative_to(LANE))
    return None, None, None, None


# ---------------------------------------------------------------- the parts
def parts():
    """(id, words, fn or a G error, kind): kind "ge" (at least), "in" (band), "le" (at most)."""
    return [
        ("M1", "a(2x4/absorbing) - a(1x8/absorbing): geometry at equal membership, N 8", lin(("2x4/absorbing", 1), ("1x8/absorbing", -1)), "ge"),
        ("M2", "a(2x2/absorbing) - a(1x4/absorbing): geometry at equal membership, N 4", lin(("2x2/absorbing", 1), ("1x4/absorbing", -1)), "ge"),
        ("M3", "a(1x8/sealed) - a(1x8/absorbing): sealing rescues the elongated group", lin(("1x8/sealed", 1), ("1x8/absorbing", -1)), "ge"),
        ("M4", "a(2x4/absorbing) - a(iso8/absorbing): the shared group against isolated sheets", lin(("2x4/absorbing", 1), ("iso8/absorbing", -1)), "ge"),
        ("M5", "a(2x4/absorbing) - a(2x4/absorbing/uniform): the distribution against the mean", lin(("2x4/absorbing", 1), ("2x4/absorbing/uniform", -1)), "in"),
        ("M6", "a(2x4/absorbing/rearranged) - a(2x4/absorbing): where the signal arrives", lin(("2x4/absorbing/rearranged", 1), ("2x4/absorbing", -1)), "in"),
        ("M7", "G's mean absolute error over the eight new absorbing shapes at lambda (P61: interior leave-one-out)", "M7", "le"),
        ("M8", "G's mean absolute error over the shapes absorbing at lambda2 (P61: the six pilot shapes)", "M8", "le"),
        ("M9", "a(2x4/sealed) - a(1x8/sealed): geometry without leakage", lin(("2x4/sealed", 1), ("1x8/sealed", -1)), "in"),
    ]


PAPER_TWINS = [(a[0], a[0].rsplit("/paper", 1)[0]) for a in D.PAPER_SET]


def rescued_fn(v):
    return (v >= D.RESCUED).astype(float)


def reported():
    rows = [
            ("RP1a", "paper's stress: a(2x4/absorbing/paper) - a(1x8/absorbing/paper)", lin(("2x4/absorbing/paper", 1), ("1x8/absorbing/paper", -1))),
            ("RP1b", "paper's stress: a(2x4/sealed/paper) - a(2x4/absorbing/paper)", lin(("2x4/sealed/paper", 1), ("2x4/absorbing/paper", -1))),
            ("RP1c", "paper's stress: a(2x4/absorbing/paper) - a(iso8/absorbing/paper)", lin(("2x4/absorbing/paper", 1), ("iso8/absorbing/paper", -1)))]
    rows += [(f"RP2/{tw}", f"a({pa}) - a({tw}): the paper's stress against the ruled one", lin((pa, 1), (tw, -1)))
             for pa, tw in PAPER_TWINS]
    rows += [(f"RP3/{tw}", f"rescued({pa}) - rescued({tw})", lin((pa, 1), (tw, -1), fn=rescued_fn)) for pa, tw in PAPER_TWINS]
    rows += [("R1a", "a(2x4/half) - a(2x4/absorbing)", lin(("2x4/half", 1), ("2x4/absorbing", -1))),
            ("R1b", "a(1x8/half) - a(1x8/absorbing)", lin(("1x8/half", 1), ("1x8/absorbing", -1))),
            ("R2", "a(iso8/sealed) - a(iso8/absorbing): sealing without a group", lin(("iso8/sealed", 1), ("iso8/absorbing", -1))),
            ("R3", "a(iso8/absorbing) - a(nofield): a sheet's own field", lin(("iso8/absorbing", 1), ("nofield", -1))),
            ("R4", "a(undisturbed) - a(nofield): the disturbance", lin(("undisturbed", 1), ("nofield", -1))),
            ("R5a", "shared point: a(2x4/absorbing/shared) - a(iso8/absorbing/shared)", lin(("2x4/absorbing/shared", 1), ("iso8/absorbing/shared", -1))),
            ("R5b", "shared point: a(2x4/sealed/shared) - a(2x4/absorbing/shared)", lin(("2x4/sealed/shared", 1), ("2x4/absorbing/shared", -1))),
            ("R5c", "shared point: a(2x4/absorbing/shared) - a(1x8/absorbing/shared)", lin(("2x4/absorbing/shared", 1), ("1x8/absorbing/shared", -1))),
            ("R6a", "a(sq8/absorbing) - a(1x8/absorbing)", lin(("sq8/absorbing", 1), ("1x8/absorbing", -1))),
            ("R6b", "a(2x3/absorbing) - a(1x6/absorbing)", lin(("2x3/absorbing", 1), ("1x6/absorbing", -1))),
            ("R7a", "equal x: a(iso8/absorbing/l2) - a(1x2/absorbing)", lin(("iso8/absorbing/l2", 1), ("1x2/absorbing", -1))),
            ("R7b", "equal x: a(2x2/absorbing/l2) - a(2x4/absorbing)", lin(("2x2/absorbing/l2", 1), ("2x4/absorbing", -1))),
            ("R8a", "at lambda2: a(2x4/absorbing/l2) - a(1x8/absorbing/l2)", lin(("2x4/absorbing/l2", 1), ("1x8/absorbing/l2", -1))),
            ("R8b", "at lambda2: a(2x2/absorbing/l2) - a(1x4/absorbing/l2)", lin(("2x2/absorbing/l2", 1), ("1x4/absorbing/l2", -1))),
            ("R9a", "a(1x8/absorbing) - a(1x8/absorbing/uniform)", lin(("1x8/absorbing", 1), ("1x8/absorbing/uniform", -1))),
            ("R9b", "a(1x8/absorbing/rearranged) - a(1x8/absorbing)", lin(("1x8/absorbing/rearranged", 1), ("1x8/absorbing", -1)))]
    return rows


def _score_one(tasks, pid, words, fn, kind, stage, th, knots):
    if isinstance(fn, str):
        x, blocks, cov = g_error(tasks, fn, knots)
    else:
        x, blocks, cov = block_matrix(tasks, fn)
    if x is None:
        return {"id": pid, "part": words, "kind": kind, "available": False, "tasks": cov[0], "of": cov[1]}
    rec = {"id": pid, "part": words, "kind": kind, "available": True, "tasks": cov[0], "of": cov[1], **value(x, blocks, stage)}
    fin = all(math.isfinite(z) for z in (rec["value"], rec["sd"], *rec["halves"]))
    nar = narrowest(rec["value"], rec["sd"], rec["halves"], kind) if (fin and kind) else None
    rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar) if kind else None, zero_sd=bool(rec["sd"] == 0))
    t = th.get(pid)
    if t is not None:
        v, sd = rec["value"], rec["sd"]
        dv = lambda z: z / sd if sd > 0 else (float("inf") if z > 0 else (0.0 if z == 0 else float("-inf")))
        if kind == "in":
            rec.update(threshold=list(t), holds=t[0] <= v <= t[1], margins=[dv(v - t[0]), dv(t[1] - v)])
        elif kind == "ge":
            rec.update(threshold=t, holds=v >= t, margins=[dv(v - t)])
        else:
            rec.update(threshold=t, holds=v <= t, margins=[dv(t - v)])
    if not isinstance(fn, str):
        by_set = {}
        for name, subset in D.ITEM_SETS.items():
            xs, _bs, _c = block_matrix(tasks, fn, set(subset))
            if xs is not None:
                by_set[name] = {"value": float(xs.mean()), "blocks": xs.mean(1).tolist()}
        rec["by_item_set"] = by_set
    return rec


def score(tasks, th=None, stage=None, knots=None):
    th = TH if th is None else th
    stage = stage or tasks[0]["stage"]
    if knots is None and stage != "probe":
        knots = frozen_G()[0]
    if stage == "probe" and knots is None:
        knots = fit_G(tasks)
    return [_score_one(tasks, pid, w, fn, kind, stage, th, knots) for pid, w, fn, kind in parts()]


def score_reported(tasks, stage=None, knots=None):
    stage = stage or tasks[0]["stage"]
    return competitors(tasks, stage) + [_score_one(tasks, rid, w, fn, None, stage, {}, None) for rid, w, fn in reported()]


def competitors(tasks, stage):
    """The lead's ruling 6: G's, G_N's (headcount's) and G_f's (the field factor's) errors side by side on M7's and M8's
    cells, with the blockwise differences G - G_N and G - G_f and their intervals. On P61, M7's cells are each curve's
    leave-one-out; elsewhere the curves are P61's, frozen."""
    curves = ({"x": fit_by(tasks, "x"), "N": fit_by(tasks, "N"), "f": fit_by(tasks, "f")} if stage == "probe" else
              dict(zip(("x", "N", "f"), frozen_G()[:3])))
    names = {"x": "G (x = L_eff / lambda)", "N": "G_N (headcount)", "f": "G_f (the field factor)"}
    out = []
    for which in ("M7", "M8"):
        errs = {}
        for cov in ("x", "N", "f"):
            if curves[cov] is None:
                continue
            x, blocks, _c = g_error(tasks, which, curves[cov], cov)
            if x is None:
                continue
            errs[cov] = (x, blocks)
            out.append({"id": f"C{which[1]}/{cov}", "part": f"{names[cov]}: mean absolute error on {which}'s cells",
                        "available": True, **value(x, blocks, stage)})
        for other in ("N", "f"):
            if "x" in errs and other in errs:
                d = errs["x"][0] - errs[other][0]
                out.append({"id": f"C{which[1]}/x-{other}", "part": f"G's error minus {names[other]}'s, blockwise, on {which}'s cells",
                            "available": True, **value(d, errs["x"][1], stage)})
    return out


HIST_BINS = np.linspace(0.5, 1.0, 11)      # per-sheet a_v at the last read, pooled over the tasks (the all-or-none read)


def levels(tasks):
    """Every arrangement's pooled level at every read, its rescue fraction and mean gain, exposure and stress, by item set."""
    labels = tasks[0]["labels"]
    reads = [int(r) for r in tasks[0]["ends"]["reads"]]
    out = {}
    for lab in labels:
        rec = {}
        for r in reads:
            x, _b, _c = block_matrix(tasks, lin((lab, 1.0), read=r))
            rec[f"a_{r}"] = None if x is None else float(x.mean())
        x, _b, _c = block_matrix(tasks, lin((lab, 1.0), fn=lambda v: (v >= D.RESCUED).astype(float)))
        rec["rescued"] = None if x is None else float(x.mean())
        for key in ("gain_mean", "expo_mean", "stress_mean"):
            x, _b, _c = block_matrix(tasks, lin((lab, 1.0), key=key))
            rec[key] = None if x is None else float(x.mean())
        for name, subset in D.ITEM_SETS.items():
            xs, _b, _c = block_matrix(tasks, lin((lab, 1.0)), set(subset))
            rec[f"a_{name}"] = None if xs is None else float(xs.mean())
        ai = labels.index(lab)
        sheets = np.concatenate([t["ends"]["a_v"][-1][t["ends"]["br_arr"] == ai] for t in tasks if t["labels"] == labels])
        rec["hist"] = np.histogram(sheets, bins=HIST_BINS)[0].tolist()
        out[lab] = rec
    return out


def margins(root):
    """P61b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers; G
    and its competitors' knots."""
    tasks, M = load(root)
    stage = M["stage"]
    G = fit_G(tasks)
    sc = score(tasks, th={}, stage=stage, knots=G)
    rep = score_reported(tasks, stage)
    print(f"P61b margins on {stage} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.4f} SD {p['sd']:.4f} (block {p['sd_block']:.4f}, case {p['sd_case']:.4f}) "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} zero-SD {p['zero_sd']}"
              + ("  by set " + ", ".join(f"{n} {b['value']:+.4f}" for n, b in p.get("by_item_set", {}).items())))
    print("G knots (x, a):", [(round(a, 4), round(b, 4)) for a, b in zip(G["x"], G["y"])])
    return {"k_rule": K_RULE, "stage": stage, "root": str(root), "design_digest": D.digest(), "parts": sc,
            "reported": rep, "levels": levels(tasks), "G": G, "G_N": fit_by(tasks, "N"), "G_f": fit_by(tasks, "f"),
            "hist_bins": HIST_BINS.tolist(),
            "x": {f"{s}@{lam}": x_of(s, lam) for s in D.PILOT_SHAPES + D.NEW_SHAPES for lam in (D.LAMBDA, D.LAMBDA2)}}


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P61's margins come first")
    G, GN, Gf, src = frozen_G()
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH, "G": G, "G_N": GN, "G_f": Gf,
           "G_source": src, "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f in reported()], "predict_sha256": sha(Path(__file__))}
    FROZEN.parent.mkdir(exist_ok=True)
    FROZEN.write_text(json.dumps(rec, indent=1) + "\n")
    print(FROZEN, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    if a.margins:
        rec = margins(a.root)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(rec, indent=1) + "\n")
        return
    tasks, M = load(a.root)
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": str(a.root), "design_digest": D.digest(), "G_source": frozen_G()[3],
         "parts": scored, "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "reported": rep, "levels": levels(tasks), "hist_bins": HIST_BINS.tolist(), "thresholds": TH}, indent=1) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']:4s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} halves "
              f"{p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
