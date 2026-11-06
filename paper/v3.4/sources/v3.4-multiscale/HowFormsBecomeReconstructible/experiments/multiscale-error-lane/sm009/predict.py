"""SM009's reader: the statement candidates Y1-Y4, the reported parts, the lane's margin rule and the freeze.

python -m sm009.predict --root STAGE_ROOT --out DIR       ->  DIR/predictions_scored.json
python -m sm009.predict --margins --root STAGE_ROOT [--out PATH]  ->  the rule's narrowest thresholds on the pilot (P65b)
python -m sm009.predict --freeze                         ->  sm009/frozen/predictions.json (on the lead's word)

SM008's reader machinery (sm008.predict, frozen; the same constants) over SM009's labels `composition/edge/arm`. Pooling
(PLAN_SM009.md): a part's value for a case j is the case's sheet at the named role and position, averaged over the futures;
Y3's terms average over the sheets with case index j of either role. Per block the mean of its 8 cases; a part the mean over
the blocks; SD = max(block SD, case SD / sqrt 8). The statements read li4; dw's versions are reported. On the pilot each part
must sit K_RULE SD inside its threshold and pass in both halves; thresholds are the narrowest round values the rule allows.

Amendment 1 (PLAN_SM009.md; the lead's rulings sent 22:58:43Z): R is dropped, so Y5 and every R item leave the reader.
Registered: Y1 at least 0.05, Y2 at most -0.005, Y4 within [0.02, 0.04]. Y3 keeps its declared kind ("at least") and is
reported, since it cannot register. Reported beside them: the decomposition Y1 = Y4 - X1/P and Y2 = (O - P)/k0 - X2/P case
by case, X1 under O (the identity), the lone struggler at an inner cell (k1-inner), every composition's group mean O - P,
and O's realized mean help against P's per composition; dw's versions; li4 first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sm008 import predict as P8  # noqa: E402  (frozen: load, sel, group, comb, block_matrix, value, narrowest, levels)
from sm009 import design as D  # noqa: E402

K_RULE = D.K_RULE
FROZEN = LANE / "sm009" / "frozen" / "predictions.json"
TH = {"Y1": 0.05, "Y2": -0.005, "Y4": (0.02, 0.04)}     # Amendment 1: the rule's narrowest on P65, as the lead ruled
HIST_BINS = P8.HIST_BINS
ARMS_READ = ("P", "O")                                 # Amendment 1: R dropped
load, sel, group, comb, block_matrix, value = P8.load, P8.sel, P8.group, P8.comb, P8.block_matrix, P8.value
narrowest, registers, levels = P8.narrowest, P8.registers, P8.levels


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lab(comp, arm, edge="absorbing"):
    return f"{comp}/{edge}/{arm}"


def at_corner(comp, role, arm, edge="absorbing", key="a_v"):
    return sel(lab(comp, arm, edge), role, 0, key=key)


def diff(a, b):
    return comb((a, 1), (b, -1))


def parts():
    return [
        ("Y1", "a(struggler at corner 0 | k1-corner) under O - under P: the lone struggler's own need against pooling",
         diff(at_corner("k1-corner", "struggling", "O"), at_corner("k1-corner", "struggling", "P")), "ge"),
        ("Y2", "a(healthy at corner 0 | k7-corner) under O - under P: the lone healthy sheet among strugglers",
         diff(at_corner("k7-corner", "healthy", "O"), at_corner("k7-corner", "healthy", "P")), "le"),
        ("Y3", "the group mean at k4-half, O - P",
         diff(group(lab("k4-half", "O")), group(lab("k4-half", "P"))), "ge"),
        ("Y4", "a(struggler at corner 0 | k8) under O - under P: the pure struggling group",
         diff(at_corner("k8", "struggling", "O"), at_corner("k8", "struggling", "P")), "in"),
    ]


def _x1(arm, edge="absorbing"):
    return diff(at_corner("k1-corner", "struggling", arm, edge), at_corner("k8", "struggling", arm, edge))


def _x2(arm):
    return diff(at_corner("k7-corner", "healthy", arm), at_corner("k0", "healthy", arm))


def _both(rid, words, fn):
    """li4's item, then dw's."""
    return [(rid, words, fn, ("li4",)), (f"{rid}/dw", f"dw (weaker S4_t1, stronger F0_t1): {words}", fn, ("dw",))]


def reported():
    rows = []
    for pid, words, fn, _kind in parts():
        rows.append((f"{pid}/dw", f"dw (weaker S4_t1, stronger F0_t1): {words}", fn, ("dw",)))
    # the decomposition's terms (Y1 = Y4 - X1/P; Y2 = (O - P)/k0 - X2/P), and X1 and X2 under O (the identity, exactly 0)
    for arm in ARMS_READ:
        rows += _both(f"X1/{arm}", f"X1 under {arm}: a(struggler at corner 0 | k1-corner) - a(the same | k8)", _x1(arm))
        rows += _both(f"X2/{arm}", f"X2 under {arm}: a(healthy at corner 0 | k7-corner) - a(the same | k0)", _x2(arm))
    rows += _both("O-P/k0", "a(healthy at corner 0 | k0), O - P: the pure healthy group (Y2's position term)",
                  diff(at_corner("k0", "healthy", "O"), at_corner("k0", "healthy", "P")))
    rows.append(("X3/P", "X1 under P with the edge sealed", _x1("P", "sealed"), ("li4",)))
    # the lone struggler at an inner cell: the role effect where P's geometry favours the cell
    rows += _both("Y1/inner", "a(struggler at inner 1 | k1-inner), O - P: the lone struggler at an inner cell",
                  diff(sel(lab("k1-inner", "O"), "struggling", 1), sel(lab("k1-inner", "P"), "struggling", 1)))
    # every composition's group mean, O - P
    for c in D.COMPOSITIONS:
        rows += _both(f"O-P/group/{c}", f"the group mean at {c}, O - P", diff(group(lab(c, "O")), group(lab(c, "P"))))
    for key, nm in (("gain_mean", "gain"), ("stress_mean", "stress"), ("expo_mean", "exposure")):
        rows += [(f"Y1/{nm}", f"Y1's {nm} (window mean): the lone struggler at corner 0, k1-corner, O - P",
                  diff(at_corner("k1-corner", "struggling", "O", key=key), at_corner("k1-corner", "struggling", "P", key=key)), ("li4",)),
                 (f"Y2/{nm}", f"Y2's {nm} (window mean): the lone healthy sheet at corner 0, k7-corner, O - P",
                  diff(at_corner("k7-corner", "healthy", "O", key=key), at_corner("k7-corner", "healthy", "P", key=key)), ("li4",))]
    return rows


def _score_one(tasks, pid, words, fn, kind, stage, th, bodies=("li4",)):
    return P8._score_one(tasks, pid, words, fn, kind, stage, th, bodies)


def score(tasks, th=None, stage=None):
    th = TH if th is None else th
    stage = stage or tasks[0]["stage"]
    return [_score_one(tasks, pid, w, fn, kind, stage, th) for pid, w, fn, kind in parts()]


def score_reported(tasks, stage=None):
    stage = stage or tasks[0]["stage"]
    return [_score_one(tasks, rid, w, fn, None, stage, {}, bodies) for rid, w, fn, bodies in reported()]


def o_exact(tasks):
    """O's identity, sheet by sheet: every sheet of an O arrangement equals the iso8/O sheet of the same future and case
    (every read of a_v and sign, the window's mean gain and stress; the exposure is computed but never read)."""
    worst, n = 0.0, 0
    for t in tasks:
        e, labs = t["ends"], t["labels"]
        if "iso8/absorbing/O" not in labs:
            return None
        iso = labs.index("iso8/absorbing/O")
        ref = {(int(f), int(c)): i for i, (f, c, a) in enumerate(zip(e["br_future"], e["br_case"], e["br_arr"])) if a == iso}
        for ai, lb in enumerate(labs):
            if not lb.endswith("/O") or ai == iso:
                continue
            for i in np.flatnonzero(e["br_arr"] == ai):
                j = ref[(int(e["br_future"][i]), int(e["br_case"][i]))]
                for key in ("a_v", "sign"):
                    worst = max(worst, float(np.abs(e[key][:, i] - e[key][:, j]).max()))
                for key in ("gain_mean", "stress_mean"):
                    worst = max(worst, abs(float(e[key][i] - e[key][j])))
                n += 1
    return {"sheets": n, "largest_difference": worst, "exact": worst == 0.0}


def decomposition(tasks):
    """Y1 = Y4 - X1/P and Y2 = (O - P)/k0 - X2/P, case by case (O's sheet does not depend on its neighbours): per body the
    terms' values and the largest per-case residual of each identity (0 when it holds exactly)."""
    def mat(fn, body):
        x, _blocks, _cov = block_matrix(tasks, fn, (body,))
        return x
    fn = {pid: f for pid, _w, f, _k in parts()}
    out = {}
    for body in D.BODIES:
        y1, y4, x1p = mat(fn["Y1"], body), mat(fn["Y4"], body), mat(_x1("P"), body)
        y2, x2p = mat(fn["Y2"], body), mat(_x2("P"), body)
        op0 = mat(diff(at_corner("k0", "healthy", "O"), at_corner("k0", "healthy", "P")), body)
        if any(v is None for v in (y1, y4, x1p, y2, x2p, op0)):
            out[body] = None
            continue
        out[body] = {"Y1": float(y1.mean()), "Y4 (position)": float(y4.mean()),
                     "-X1/P (undoing the dilution)": float(-x1p.mean()),
                     "Y1 - (Y4 - X1/P), largest |case|": float(np.abs(y1 - (y4 - x1p)).max()),
                     "Y2": float(y2.mean()), "(O - P)/k0 (position)": float(op0.mean()),
                     "-X2/P (undoing the mixing gain)": float(-x2p.mean()),
                     "Y2 - ((O - P)/k0 - X2/P), largest |case|": float(np.abs(y2 - (op0 - x2p)).max())}
    return out


def realized_help(tasks):
    """O's realized mean help against P's per composition: each arrangement's mean gain over all its sheets and futures
    (the mean over the body's tasks), P, O and O / P; iso8 too."""
    out = {}
    for body in D.BODIES:
        g = {}
        for t in tasks:
            if t["body"] != body:
                continue
            e = t["ends"]
            for ai, lb in enumerate(t["labels"]):
                g.setdefault(lb, []).append(float(e["gain_mean"][e["br_arr"] == ai].mean()))
        g = {k: float(np.mean(v)) for k, v in g.items()}
        for c in (*D.COMPOSITIONS, "iso8"):
            p_, o_ = g.get(lab(c, "P")), g.get(lab(c, "O"))
            if p_ is None or o_ is None:
                continue
            out[f"{body}|{c}"] = {"P": p_, "O": o_, "O/P": o_ / p_}
    return out


def gains(tasks):
    """The realized mean gain per arm and role (li4 and dw), every absorbing composition pooled."""
    out = {}
    for body in D.BODIES:
        for arm in ARMS_READ:
            for role in ("healthy", "struggling"):
                vals = []
                for t in tasks:
                    if t["body"] != body:
                        continue
                    e = t["ends"]
                    for ai, lb in enumerate(t["labels"]):
                        if lb.endswith(f"/absorbing/{arm}") and not lb.startswith("iso8"):
                            m = (e["br_arr"] == ai) & ((e["br_case"] >= D.NCASE) == (role == "struggling"))
                            vals.append(e["gain_mean"][m])
                out[f"{body}|{arm}|{role}"] = float(np.concatenate(vals).mean()) if vals else None
    return out


def extras(tasks):
    return {"o_exact": o_exact(tasks), "decomposition": decomposition(tasks), "realized_help": realized_help(tasks),
            "gains": gains(tasks), "levels": levels(tasks), "hist_bins": HIST_BINS.tolist()}


def margins(roots):
    """P65b: on the pilot, every part's value, SD, halves and the rule's narrowest threshold, and whether it registers."""
    tasks, M = load(roots)
    stage = M["stage"]
    sc = score(tasks, th={}, stage=stage)
    rep = score_reported(tasks, stage)
    print(f"P65b margins on {stage} ({len(tasks)} tasks), K_RULE {K_RULE:.4f}")
    for p in sc:
        if not p["available"]:
            print(f"{p['id']}: not available ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']} {p['kind']} {p['value']:+.5f} SD {p['sd']:.5f} (block {p['sd_block']:.5f}, case {p['sd_case']:.5f}) "
              f"halves {p['halves'][0]:+.5f} {p['halves'][1]:+.5f} narrowest {p['narrowest']} registers "
              f"{p['registers_at_narrowest']} zero-SD {p['zero_sd']}")
    return {"k_rule": K_RULE, "stage": stage, "root": str(roots), "design_digest": D.digest(), "parts": sc, "reported": rep,
            **extras(tasks)}


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P65's margins and the lead's ruling come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE,
           "thresholds": {k: (list(v) if isinstance(v, tuple) else v) for k, v in TH.items()},
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": (list(TH[p]) if isinstance(TH[p], tuple) else TH[p])}
                          for p, w, _f, k in parts() if p in TH],
           "candidates_reported": [{"id": p, "part": w, "kind": k} for p, w, _f, k in parts() if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _f, _b in reported()], "predict_sha256": sha(Path(__file__))}
    FROZEN.parent.mkdir(exist_ok=True)
    FROZEN.write_text(json.dumps(rec, indent=1) + "\n")
    print(FROZEN, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True, action="append")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    roots = a.root if len(a.root) > 1 else a.root[0]
    if a.margins:
        rec = margins(roots)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(rec, indent=1) + "\n")
        return
    tasks, M = load(roots)
    stage = M["stage"]
    scored = score(tasks, stage=stage)
    rep = score_reported(tasks, stage)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": str(a.root[0]) if len(a.root) == 1 else [str(r) for r in a.root],
         "design_digest": D.digest(), "parts": scored,
         "verdicts": {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p},
         "reported": rep, **extras(tasks),
         "thresholds": {k: (list(v) if isinstance(v, tuple) else v) for k, v in TH.items()}}, indent=1) + "\n")
    for p in scored:
        if not p["available"]:
            print(f"{p['id']:4s} not available on this stage ({p['tasks']} of {p['of']} tasks)")
            continue
        print(f"{p['id']:4s} {p['value']:+.5f} [{p['ci95'][0]:+.5f}, {p['ci95'][1]:+.5f}] SD {p['sd']:.5f} halves "
              f"{p['halves'][0]:+.5f} {p['halves'][1]:+.5f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
