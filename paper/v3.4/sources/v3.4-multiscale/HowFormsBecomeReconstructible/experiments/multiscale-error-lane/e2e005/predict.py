"""E2E005's reader: the statement candidates (C1-C4), the declared frontier reading, the reported parts, the switch's
figures per firing, the lane's margin rule and the freeze. DRAFT (phase A).

python -m e2e005.predict --root STAGE_ROOT --out DIR     ->  DIR/predictions_scored.json
python -m e2e005.predict --margins --root STAGE_ROOT     ->  the rule's narrowest thresholds on the stage (P62b)
python -m e2e005.predict --freeze                         ->  e2e005/frozen/predictions.json (phase B, on the lead's word)

Pooling (the AR studies', E2E004's, imported unchanged from e2e004.predict): per case (block, message, parent) the mean
over the unit-body pairs and the futures; a block's value the mean of its cases; a part the mean over the blocks.
SD = max(block SD, case SD / sqrt(cases a block)). The frontier reading C4 is a block statistic: each block's F from the
block's own points, then the mean over blocks with the blocks' SD. On the pilot each part must sit K_RULE SD inside its
threshold and pass in both halves; thresholds are the narrowest round values the rule allows (hundredths, or 0.005 within
0.01 of zero). Development intervals: mean +- t(0.975, n - 1) SD / sqrt n. Coverage (E2E001's lesson): a part or a level
is pooled only where every task of the stage has every term; anything less is marked partial, with its task count.
The switch's figures (firing shares, onsets, footprints, the costs over the lineages that fired) are reported per firing:
over the newborns that fired, never averaged over those that did not.
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
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from e2e004.predict import block_matrix, lin, load, narrowest, registers, sd_rule, val_f  # noqa: E402
from e2e005 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the thresholds, from P62 by the rule (P62b, probes/results/p62b_e2e005_margins.txt, 13:09Z on 5 November), registered
# on the lead's phase-A rulings (sent 13:23:43Z): C1 and C3 at the rule's narrowest bounds above 0, C2 at its narrowest
# band (on P62 the band excludes 0: the controller costs history, mostly in li4 x F0). C4's narrowest bound (-0.02) is not
# above 0, so C4 is reported, not registered, and no null is registered for it (ruling 2).
TH = {"C1": 0.06, "C2": [-0.08, -0.02], "C3": 0.4}
REPORTED_ONLY = ("C4",)
C_P, R_P, B_P, V_P = "ctl/protected", "record/protected", "body/protected", "vote/protected"
C_X, R_X, B_X, V_X, O_X = "ctl/post", "record/post", "body/post", "vote/post", "oracle/post"
FIXED_POINTS = (("record", R_P, R_X), ("vote", V_P, V_X), ("body", B_P, B_X))
SWITCHED = (C_P, C_X, O_X)
PATCH_CELLS = D.SIZE * D.SIZE


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


# the frontier reading -------------------------------------------------------------------------------------------------

def hull_heal(K, pts):
    """The fixed rules' line at keeping K: the largest healing any fixed rule, or mixture of two, reaches while keeping
    at least K (the convex hull's upper boundary with free disposal; above every point's keeping, the healing of the
    point that keeps most). pts: [(keep, heal)]."""
    cands = [h for k, h in pts if k >= K]
    for k1, h1 in pts:
        for k2, h2 in pts:
            if k1 < K < k2:
                lam = (k2 - K) / (k2 - k1)
                cands.append(lam * h1 + (1 - lam) * h2)
    if not cands:
        return max(pts)[1]
    return max(cands)


def points(tasks, g, subset=None):
    """{rule: (keep, heal) per block (arrays)}, the blocks, and the coverage; None where a term is missing."""
    out, blocks, cov = {}, None, None
    for name, lp, lx in FIXED_POINTS + (("ctl", C_P, C_X),):
        xk, bk, ck = block_matrix(tasks, lin((1, lp, "q_r", g)), subset)
        xh, bh, ch = block_matrix(tasks, lin((1, lx, "u_r", g)), subset)
        if xk is None or xh is None:
            return None, [], ck if xk is None else ch
        out[name] = (xk.mean(1), xh.mean(1))
        blocks, cov = bk, ck
    xo, _b, _c = block_matrix(tasks, lin((1, O_X, "u_r", g)), subset)
    if xo is not None:
        out["oracle"] = (out["record"][0], xo.mean(1))
    return out, blocks, cov


def frontier_blocks(P, chord=False):
    """Per block, F = H_ctl - h(K_ctl) against the fixed rules' line (the record-body chord alone with chord=True)."""
    names = ("record", "body") if chord else ("record", "vote", "body")
    nb = len(P["ctl"][0])
    return np.array([P["ctl"][1][b] - hull_heal(P["ctl"][0][b], [(P[n][0][b], P[n][1][b]) for n in names])
                     for b in range(nb)])


def frontier_fn(g, chord=False):
    """A part function for score(): returns (x (blocks, 1), blocks, coverage)."""
    def f(tasks, subset=None):
        P, blocks, cov = points(tasks, g, subset)
        if P is None:
            return None, [], cov
        return frontier_blocks(P, chord)[:, None], blocks, cov
    f.block_statistic = True
    return f


def beside(tasks, g, subset=None):
    """What the frontier reading is read beside (the lead's phase-A ruling 2), over the subset's tasks: the oracle's and
    the controller's healing (pooled u_r of post at g), and the detector on post-damage and protected storage through
    generation g: the share of lineages that fired by g, and over every firing in generations 1 to g, the footprint's
    cells, the share of the patch it covers and its cells outside the patch."""
    ts = [t for t in tasks if subset is None or (t["body"], t["unit"]) in subset]
    out = {}
    for lab in (O_X, C_X):
        x, _b, _c = block_matrix(ts, lin((1, lab, "u_r", g)))
        out[f"heal_{lab.split('/')[0]}"] = None if x is None else float(x.mean())
    for lab, name in ((C_X, "post"), (C_P, "protected")):
        ever, fp, fp_in, n = [], [], [], 0
        for t in ts:
            if lab not in t["meta"]["labels"]:
                continue
            e = np.zeros(len(t["meta"]["cases"]), bool)
            for gg in range(1, g + 1):
                fd = diag(t, lab, "fired", gg)
                if fd is None:
                    break
                f = fd > 0
                e |= f
                fp.append(diag(t, lab, "fp", gg)[f])
                fp_in.append(diag(t, lab, "fp_in", gg)[f])
            ever.append(e)
        if not ever:
            continue
        fpc, fic = np.concatenate(fp), np.concatenate(fp_in)
        rec = {"lineage_cases": int(sum(x.size for x in ever)), "fired_by_g": float(np.concatenate(ever).mean()),
               "firings": int(fpc.size)}
        if fpc.size:
            rec.update(footprint=float(fpc.mean()), patch_covered=float(fic.mean() / PATCH_CELLS),
                       outside_patch=float((fpc - fic).mean()))
        out[name] = rec
    return out


def frontier_reading(tasks, g):
    """The declared reading, overall and by item set: the pooled points, F and F_RB at the pooled points, and the
    normalized coordinates (x, y) of the controller, the vote and the oracle (beyond the chord where x + y > 1)."""
    out = {}
    for name, subset in (("all", None),) + tuple((n, set(s)) for n, s in D.ITEM_SETS.items()):
        P, blocks, cov = points(tasks, g, subset)
        if P is None:
            out[name] = {"available": False, "tasks": cov[0], "of": cov[1]}
            continue
        pt = {n: (float(np.mean(k)), float(np.mean(h))) for n, (k, h) in P.items()}
        fixed = [pt[n] for n in ("record", "vote", "body")]
        (kr, hr), (kb, hb) = pt["record"], pt["body"]
        norm = lambda p: ([(p[0] - kb) / (kr - kb), (p[1] - hr) / (hb - hr)] if kr != kb and hb != hr else None)
        out[name] = {"available": True, "tasks": cov[0], "of": cov[1], "points": pt,
                     "F_at_pooled": pt["ctl"][1] - hull_heal(pt["ctl"][0], fixed),
                     "F_RB_at_pooled": pt["ctl"][1] - hull_heal(pt["ctl"][0], [pt["record"], pt["body"]]),
                     "line_at_ctl_keep": hull_heal(pt["ctl"][0], fixed),
                     "vote_beyond_chord": bool(pt["vote"][1] > hull_heal(pt["vote"][0], [pt["record"], pt["body"]])),
                     "normalized": {n: norm(pt[n]) for n in ("ctl", "vote") + (("oracle",) if "oracle" in pt else ())},
                     "F_blocks_mean": float(frontier_blocks(P).mean()), "F_RB_blocks_mean": float(frontier_blocks(P, True).mean()),
                     "beside": beside(tasks, g, subset)}
    return out


# the parts ------------------------------------------------------------------------------------------------------------

def parts():
    return [
        ("C1", "the controller heals more than the record rule: u_r(ctl/post) - u_r(record/post), g 8",
         lin((1, C_X, "u_r", 8), (-1, R_X, "u_r", 8)), "ge"),
        ("C2", "the controller keeps the history as the record rule does: q_r(ctl/protected) - q_r(record/protected), g 8",
         lin((1, C_P, "q_r", 8), (-1, R_P, "q_r", 8)), "in"),
        ("C3", "the controller keeps more than the body rule: q_r(ctl/protected) - q_r(body/protected), g 8",
         lin((1, C_P, "q_r", 8), (-1, B_P, "q_r", 8)), "ge"),
        ("C4", "the controller's healing beyond the fixed rules' line at its own keeping: F = u_r(ctl/post) - "
               "h(q_r(ctl/protected)), g 8 (a block statistic)", frontier_fn(8), "ge"),
    ]


PAIRS = {"C1": (C_X, R_X), "C2": (C_P, R_P), "C3": (C_P, B_P), "C4": (C_X, R_X)}


def reported():
    out = []
    E = ("u_r", "q_r", "u_v")
    for g in D.HORIZONS:
        for e in E:
            for tag, a, b, words in (("heal-cr", C_X, R_X, "the controller against the record rule, post"),
                                     ("heal-cb", C_X, B_X, "the controller against the body rule, post"),
                                     ("heal-cv", C_X, V_X, "the controller against the vote, post"),
                                     ("keep-cr", C_P, R_P, "the controller against the record rule, protected"),
                                     ("keep-cb", C_P, B_P, "the controller against the body rule, protected"),
                                     ("keep-cv", C_P, V_P, "the controller against the vote, protected"),
                                     ("oracle-c", O_X, C_X, "the oracle against the controller (where-to-switch), post"),
                                     ("oracle-r", O_X, R_X, "the oracle against the record rule, post"),
                                     ("oracle-b", O_X, B_X, "the oracle against the body rule, post")):
                out.append((f"R-{tag}-{e}-{g}", f"{e}({a}) - {e}({b}), g {g}: {words}", lin((1, a, e, g), (-1, b, e, g))))
    for g in (1, 3):
        out.append((f"R-frontier-{g}", f"F, the controller's healing beyond the fixed rules' line, g {g}", frontier_fn(g)))
    for g in D.HORIZONS:
        out.append((f"R-frontier-RB-{g}", f"F_RB, beyond the record-body chord alone, g {g}", frontier_fn(g, chord=True)))
    return out


def run_fn(tasks, fn, subset=None):
    if getattr(fn, "block_statistic", False):
        return fn(tasks, subset)
    return block_matrix(tasks, fn, subset)


def score(tasks, th=None, stage=None):
    th = TH if th is None else th
    stage = stage or tasks[0]["stage"]
    out = []
    for pid, words, fn, kind in parts():
        x, blocks, cov = run_fn(tasks, fn)
        if x is None:
            out.append({"id": pid, "part": words, "kind": kind, "available": False, "tasks": cov[0], "of": cov[1]})
            continue
        rec = {"id": pid, "part": words, "kind": kind, "available": True, "tasks": cov[0], "of": cov[1],
               **value(x, blocks, stage)}
        fin = all(math.isfinite(z) for z in (rec["value"], rec["sd"], *rec["halves"]))
        nar = narrowest(rec["value"], rec["sd"], rec["halves"], kind) if fin else None
        rec.update(narrowest=nar, registers_at_narrowest=registers(kind, nar), zero_sd=bool(rec["sd"] == 0))
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
        by_set = {}
        for name, subset in D.ITEM_SETS.items():
            xs, _bs, _c = run_fn(tasks, fn, set(subset))
            if xs is not None:
                by_set[name] = {"value": float(xs.mean()), "blocks": xs.mean(1).tolist()}
        rec["by_item_set"] = by_set
        rec["registered"] = pid in th and pid not in REPORTED_ONLY
        out.append(rec)
    return out


def score_reported(tasks, stage=None):
    stage = stage or tasks[0]["stage"]
    out = []
    for rid, words, fn in reported():
        x, blocks, cov = run_fn(tasks, fn)
        if x is None:
            out.append({"id": rid, "part": words, "available": False, "tasks": cov[0], "of": cov[1]})
            continue
        rec = {"id": rid, "part": words, "available": True, "tasks": cov[0], "of": cov[1], **value(x, blocks, stage)}
        rec.pop("blocks")
        rec["by_item_set"] = {}
        for name, subset in D.ITEM_SETS.items():
            xs, _bs, _c = run_fn(tasks, fn, set(subset))
            if xs is not None:
                rec["by_item_set"][name] = float(xs.mean())
        out.append(rec)
    return out


def aliases(tasks):
    """Per part, the tasks in which its two lineages ran on one row (an alias: the difference is exactly 0 there)."""
    out = {}
    for pid, (a, b) in PAIRS.items():
        out[pid] = sum(1 for t in tasks if a in t["meta"]["labels"] and b in t["meta"]["labels"]
                       and t["meta"]["labels"][a] == t["meta"]["labels"][b])
    return out


# the levels and the switch's figures per firing -------------------------------------------------------------------------

LEVEL_ENDS = ("u_r", "u_v", "a_r", "q_r", "q_v", "u_r_raw", "agree_in")


def labels_of(tasks):
    out = []
    for t in tasks:
        for lab in t["meta"]["labels"]:
            if lab not in out:
                out.append(lab)
    return out


def pooled(tasks, fn):
    x, _b, cov = block_matrix(tasks, fn)
    rec = {"tasks": cov[0], "of": cov[1]}
    if x is None:
        rec["partial"] = cov[0] > 0
        return rec
    rec["all"] = round(float(x.mean()), 5)
    for name, subset in D.ITEM_SETS.items():
        xs, _bs, _c = block_matrix(tasks, fn, set(subset))
        if xs is not None:
            rec[name] = round(float(xs.mean()), 5)
    return rec


def levels(tasks):
    out = {}
    for label in labels_of(tasks):
        for e in LEVEL_ENDS:
            for g in (0,) + D.HORIZONS:
                rec = pooled(tasks, lin((1, label, e, g)))
                if rec["tasks"]:
                    out[f"{label}|{e}|{g}"] = rec
    return out


def diag(task, label, e, g):
    v = val_f(task, label, e, g, "d")
    return None if v is None else v[0]


def firing(tasks):
    """Per switched lineage and generation, overall and by item set: the share of newborns that fired, and over the
    firings only the onset quartiles, the footprint's cells, its cells outside the patch, the share of the patch it
    covers, the zone's cells and the windows held; the share of lineages that have fired by g."""
    out = {}
    gens = sorted({int(k.split("/")[1][1:]) for t in tasks for k in t["ends"] if k.startswith("f0/d") and k.endswith("/rows")})
    for label in SWITCHED:
        if not any(label in t["meta"]["labels"] for t in tasks):
            continue
        for name, subset in (("all", None),) + tuple((n, set(s)) for n, s in D.ITEM_SETS.items()):
            ts = [t for t in tasks if (subset is None or (t["body"], t["unit"]) in subset) and label in t["meta"]["labels"]]
            ever = {id(t): np.zeros(len(t["meta"]["cases"]), bool) for t in ts}
            keys = ("fired", "t_on", "fp", "fp_in", "zone", "nwin") + (("bonds",) if ts and all(
                "f0/d1/bonds" in t["ends"] for t in ts) else ())
            for g in gens:
                vals = {e: [] for e in keys}
                ev = []
                for t in ts:
                    d = {e: diag(t, label, e, g) for e in vals}
                    if d["fired"] is None:
                        continue
                    for e in vals:
                        vals[e].append(d[e])
                    ever[id(t)] |= d["fired"] > 0
                    ev.append(ever[id(t)].copy())
                if not vals["fired"]:
                    continue
                fired = np.concatenate(vals["fired"]) > 0
                cat = {e: np.concatenate(v) for e, v in vals.items()}
                rec = {"newborns": int(fired.size), "fired": int(fired.sum()), "share": float(fired.mean()),
                       "ever_by_g": float(np.concatenate(ev).mean())}
                if fired.any():
                    on = cat["t_on"][fired]
                    rec.update(onset_q=[float(np.percentile(on, q)) for q in (25, 50, 75)],
                               footprint=float(cat["fp"][fired].mean()),
                               footprint_outside_patch=float((cat["fp"] - cat["fp_in"])[fired].mean()),
                               patch_covered=float(cat["fp_in"][fired].mean() / PATCH_CELLS),
                               zone=float(cat["zone"][fired].mean()), windows=float(cat["nwin"][fired].mean()))
                    if "bonds" in cat:
                        rec["open_bonds"] = float(cat["bonds"][fired].mean())
                out[f"{label}|{name}|{g}"] = rec
    return out


def per_firing_costs(tasks):
    """At each horizon, over the cases whose controller fired at least once by then (per lineage): the mean paired
    difference against the record rule, q_r on protected storage and u_r on post-damage copying, with their counts. A
    case that never fired is the record rule bit for bit (Q4), so its difference is exactly 0."""
    out = {}
    for lab_c, lab_r, e in ((C_P, R_P, "q_r"), (C_X, R_X, "u_r"), (C_X, R_X, "q_r")):
        for g in D.HORIZONS:
            for name, subset in (("all", None),) + tuple((n, set(s)) for n, s in D.ITEM_SETS.items()):
                diffs, n_all = [], 0
                for t in tasks:
                    if subset is not None and (t["body"], t["unit"]) not in subset:
                        continue
                    if lab_c not in t["meta"]["labels"] or lab_r not in t["meta"]["labels"]:
                        continue
                    a, b = val_f(t, lab_c, e, g), val_f(t, lab_r, e, g)
                    if a is None or b is None:
                        continue
                    ever = np.zeros(len(t["meta"]["cases"]), bool)
                    for gg in range(1, g + 1):
                        fd = diag(t, lab_c, "fired", gg)
                        if fd is not None:
                            ever |= fd > 0
                    d = a[0] - b[0]
                    n_all += d.size
                    diffs.append(d[ever])
                dd = np.concatenate(diffs) if diffs else np.zeros(0)
                out[f"{lab_c}|{e}|{g}|{name}"] = {"lineage_cases": n_all, "fired_by_g": int(dd.size),
                                                  "mean_over_fired": float(dd.mean()) if dd.size else None}
    return out


def margins(root):
    """P62b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers."""
    tasks, M = load(root)
    stage = M["stage"]
    sc = score(tasks, th={}, stage=stage)
    al = aliases(tasks)
    print(f"P62b margins on {stage} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.4f} SD {p['sd']:.4f} (block {p['sd_block']:.4f}, case {p['sd_case']:.4f}) "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} zero-SD {p['zero_sd']} tasks {p['tasks']} of {p['of']} aliased tasks "
              f"{al[p['id']]}" + "  by set " + ", ".join(f"{n} {b['value']:+.4f}" for n, b in p["by_item_set"].items()))
    return sc, al


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P62's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _f, _k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f in reported()],
           "predict_sha256": sha(Path(__file__))}
    out = LANE / "e2e005" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    if a.margins:
        sc, al = margins(a.root)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps({"k_rule": K_RULE, "parts": sc, "aliased_tasks": al}, indent=1) + "\n")
        return
    tasks, M = load(a.root)
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": str(a.root), "design_digest": D.digest(), "detector": D.DETECTOR_NAME,
         "parts": scored, "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "aliased_tasks": aliases(tasks), "frontier": {g: frontier_reading(tasks, g) for g in D.HORIZONS},
         "reported": rep, "firing": firing(tasks), "per_firing_costs": per_firing_costs(tasks), "levels": levels(tasks)},
        separators=(",", ":")) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']:4s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} halves "
              f"{p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
