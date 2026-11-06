"""SM002's registered statements and their scoring.

python -m sm002.predict --root ROOT --stage {probe,preflight,dev} --out DIR
python -m sm002.predict --freeze      (writes sm002/frozen/predictions.json)

Every part is linear in the case values: per case, the mean over the part's conditions of a paired difference (the same
case's acquisition and draws in every condition of a block); a block's value is the mean over its 8 cases; the part is
the mean over the blocks, unrounded. The twin of a refined condition (w, L, c, m, tau) is the transfer condition
(w/2, L/2, c/2, m, tau) (sm002.analyze.attach_twins). Late is m 2 (the signal at 2 T*, commitment 3,000); prompt is m 0
(commitments 30 and 3,000), as in SM001's S3 and S4.

DIR gets predictions_scored.json (the registered parts, each with its SDs, both halves of the blocks, its 95% interval
and its margin) and reported.json (every contrast in CONTRASTS, the same way, without a threshold; and a summary: T2's
95% interval and the fraction of T1's loss it leaves, T2 / T1, with its interval's bounds divided by T1). A 95% interval
is the mean over the blocks +- t(0.975, blocks - 1) x the max-rule SD / sqrt(blocks), the lane's interval (P42c).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.stats import t as student_t

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm002 import analyze as A  # noqa: E402
from sm002 import design as D  # noqa: E402

FROZEN = LANE / "sm002" / "frozen"
RULE = 3 * math.sqrt(1 / 4 + 1 / 16)          # 1.68: each part this many SDs inside its threshold, at the probe


def _rows(R, kind, m=None, L=None, x2=None):
    out = [r for r in R if r["kind"] == kind and (m is None or r["m"] == m) and (L is None or r["L"] == L)]
    if x2 == "lt":
        out = [r for r in out if r["x2"] < 1]
    elif x2 == "gt":
        out = [r for r in out if r["x2"] > 1]
    if not out:
        raise ValueError(f"no rows for {kind} m {m} L {L} x2 {x2}")
    return out


def twin_diff(R, m, f, g, L=None, x2=None):
    """Per case, the mean over the refined conditions at m (and L, x2 side) of f(row) - g(its twin)."""
    return np.mean([f(r) - g(r["twin"]) for r in _rows(R, "refine", m, L, x2)], axis=0)


def same_diff(R, kind, m, f, g, x2=None):
    """Per case, the mean over the conditions of a kind at m of f(row) - g(row) (both readers on the same records)."""
    return np.mean([f(r) - g(r) for r in _rows(R, kind, m, None, x2)], axis=0)


def mean_of(R, kind, m, f, x2=None):
    return np.mean([f(r) for r in _rows(R, kind, m, None, x2)], axis=0)


K = lambda key: (lambda r: r[key])                                                     # noqa: E731
SHARE_U = lambda r: r["E_u"] - r["r_in"]                                               # noqa: E731
SHARE_CG = lambda r: r["E_cg"] - r["r_in"]                                             # noqa: E731
PHASE_U = lambda r: r["E_u"] - r["gen_u"]                                              # noqa: E731
PHASE_CG = lambda r: r["E_cg"] - r["gen_cg"]                                           # noqa: E731

# every contrast computed (reported); the registered parts below name some of them
CONTRASTS = {}
for _m, _s in ((2, "late"), (0, "prompt")):
    for _x2 in (None, "lt", "gt"):
        _t = "" if _x2 is None else f", x2 {'< 1' if _x2 == 'lt' else '> 1'}"
        CONTRASTS[f"{_s}{'' if _x2 is None else '_' + _x2}: E_u - E_u(twin)"] = (lambda R, m=_m, x=_x2: twin_diff(R, m, K("E_u"), K("E_u"), x2=x))
        CONTRASTS[f"{_s}{'' if _x2 is None else '_' + _x2}: E_cg - E_u(twin)"] = (lambda R, m=_m, x=_x2: twin_diff(R, m, K("E_cg"), K("E_u"), x2=x))
        CONTRASTS[f"{_s}{'' if _x2 is None else '_' + _x2}: E_cg - E_u (refined)"] = (lambda R, m=_m, x=_x2: same_diff(R, "refine", m, K("E_cg"), K("E_u"), x))
        CONTRASTS[f"{_s}{'' if _x2 is None else '_' + _x2}: E_cg(twin) - E_u(twin)"] = (lambda R, m=_m, x=_x2: same_diff(R, "transfer", m, K("E_cg"), K("E_u"), x))
    for _x2 in (None, "lt", "gt"):
        # the scaled reader against the midpoint of the unscaled reader's two readings: >= 0 when it recovers at least
        # half of the loss under doubling (linear in the case values)
        CONTRASTS[f"{_s}{'' if _x2 is None else '_' + _x2}: E_cg - (E_u + E_u(twin)) / 2"] = (
            lambda R, m=_m, x=_x2: np.mean([r["E_cg"] - (r["E_u"] + r["twin"]["E_u"]) / 2 for r in _rows(R, "refine", m, None, x)], axis=0))
    for _x2 in (None, "lt", "gt"):
        # the difference in differences: the scaled reader's gain at the doubled lengths less its gain at the twin's
        # (0 if its advantage were the same at both scales and the loss lay elsewhere)
        CONTRASTS[f"{_s}{'' if _x2 is None else '_' + _x2}: (E_cg - E_u) - (E_cg - E_u)(twin)"] = (
            lambda R, m=_m, x=_x2: twin_diff(R, m, lambda r: r["E_cg"] - r["E_u"], lambda r: r["E_cg"] - r["E_u"], x2=x))
    CONTRASTS[f"{_s}: r_in - r_in(twin)"] = (lambda R, m=_m: twin_diff(R, m, K("r_in"), K("r_in")))
    CONTRASTS[f"{_s}: share_u - share_u(twin)"] = (lambda R, m=_m: twin_diff(R, m, SHARE_U, SHARE_U))
    CONTRASTS[f"{_s}: share_cg - share_u(twin)"] = (lambda R, m=_m: twin_diff(R, m, SHARE_CG, SHARE_U))
    CONTRASTS[f"{_s}: gen_u - gen_u(twin)"] = (lambda R, m=_m: twin_diff(R, m, K("gen_u"), K("gen_u")))
    CONTRASTS[f"{_s}: gen_cg - gen_u(twin)"] = (lambda R, m=_m: twin_diff(R, m, K("gen_cg"), K("gen_u")))
    CONTRASTS[f"{_s}: phase_cg - phase_u(twin)"] = (lambda R, m=_m: twin_diff(R, m, PHASE_CG, PHASE_U))
    CONTRASTS[f"{_s}: phase_u - phase_u(twin)"] = (lambda R, m=_m: twin_diff(R, m, PHASE_U, PHASE_U))
    CONTRASTS[f"{_s}: E_cg_ctrl - E_u_ctrl (refined)"] = (lambda R, m=_m: same_diff(R, "refine", m, K("E_cg_ctrl"), K("E_u_ctrl")))
    for _L in (4, 8, 16):
        CONTRASTS[f"{_s}, L {_L}: E_u - E_u(twin)"] = (lambda R, m=_m, L=_L: twin_diff(R, m, K("E_u"), K("E_u"), L=L))
        CONTRASTS[f"{_s}, L {_L}: E_cg - E_u(twin)"] = (lambda R, m=_m, L=_L: twin_diff(R, m, K("E_cg"), K("E_u"), L=L))
    for _k, _key in (("refine", "E_u"), ("refine", "E_cg"), ("transfer", "E_u"), ("transfer", "E_cg"),
                     ("refine", "r_in"), ("transfer", "r_in"), ("refine", "gen_u"), ("refine", "gen_cg"),
                     ("transfer", "gen_u"), ("transfer", "gen_cg"), ("refine", "ties")):
        CONTRASTS[f"{_s}: mean {_key} ({_k})"] = (lambda R, m=_m, k=_k, key=_key: mean_of(R, k, m, K(key)))

# the registered parts: (statement, part name, contrast, threshold, sense), set from P43 under BE002's rule as the lead
# stated it for SM001: each part >= 3 sqrt(1/4 + 1/16) = 1.68 SDs inside its threshold, both halves of P43 passing
# (the lead's review, 31 October 2026: T4 >= 0.04 and T2 within [-0.06, 0.09], each the narrowest round value the rule
# allows on P43)
T = {"T1": -0.05, "T2lo": -0.06, "T2hi": 0.09, "T3": 0.10, "T4": 0.04, "T5": 0.0, "T6": 0.1, "T7u": -0.05, "T7cg": -0.05,
     "T8": -0.05}
PARTS = [
    ("T1", "T1 late (m 2), unscaled reader: mean (E_u - E_u(twin)) <= -0.05", "late: E_u - E_u(twin)", T["T1"], "le"),
    ("T2", "T2 late (m 2), scaled reader: mean (E_cg - E_u(twin)) >= -0.06", "late: E_cg - E_u(twin)", T["T2lo"], "ge"),
    ("T2", "T2 late (m 2), scaled reader: mean (E_cg - E_u(twin)) <= 0.09", "late: E_cg - E_u(twin)", T["T2hi"], "le"),
    ("T3", "T3 late (m 2), the same records: mean (E_cg - E_u) >= 0.10", "late: E_cg - E_u (refined)", T["T3"], "ge"),
    ("T4", "T4 late (m 2): mean ((E_cg - E_u) - (E_cg - E_u)(twin)) >= 0.04", "late: (E_cg - E_u) - (E_cg - E_u)(twin)",
     T["T4"], "ge"),
    ("T5", "T5 late (m 2), the twins: mean (E_cg(twin) - E_u(twin)) >= 0", "late: E_cg(twin) - E_u(twin)", T["T5"], "ge"),
    ("T6", "T6 prompt (m 0), scaled reader: mean (E_cg - E_u(twin)) >= -0.1", "prompt: E_cg - E_u(twin)", -T["T6"], "ge"),
    ("T6", "T6 prompt (m 0), scaled reader: mean (E_cg - E_u(twin)) <= 0.1", "prompt: E_cg - E_u(twin)", T["T6"], "le"),
    ("T7", "T7 prompt (m 0), x2 < 1, unscaled reader: mean (E_u - E_u(twin)) <= -0.05", "prompt_lt: E_u - E_u(twin)",
     T["T7u"], "le"),
    ("T7", "T7 prompt (m 0), x2 < 1, scaled reader: mean (E_cg - E_u(twin)) >= -0.05", "prompt_lt: E_cg - E_u(twin)",
     T["T7cg"], "ge"),
    ("T8", "T8 late (m 2), unscaled reader: mean ((E_u - gen_u) - (E_u - gen_u)(twin)) <= -0.05",
     "late: phase_u - phase_u(twin)", T["T8"], "le"),
]
STATEMENTS = [
    {"id": "T1", "claim": "doubling every declared length lowers the late signal's reconstruction under the unscaled reader "
                          "(SM001's S4 on fresh blocks)",
     "rule": "HOLDS if, over the 27 refined conditions with the signal at 2 T* (m 2), the mean of E_u less E_u of the twin is "
             "<= -0.05, else FAILS"},
    {"id": "T2", "claim": "with the reader scaled with the lengths, at most 0.06 of the late loss remains",
     "rule": "HOLDS if, over the refined conditions with m 2, the mean of E_cg less E_u of the twin lies within "
             "[-0.06, 0.09], else FAILS"},
    {"id": "T3", "claim": "on the same records, the scaled reader recovers the late loss",
     "rule": "HOLDS if, over the refined conditions with m 2, the mean of E_cg less E_u is >= 0.10, else FAILS"},
    {"id": "T4", "claim": "the scaled reader's gain is specific to the doubled lengths",
     "rule": "HOLDS if, over the refined conditions with m 2, the mean of (E_cg - E_u) less the twin's (E_cg - E_u) is "
             ">= 0.04, else FAILS"},
    {"id": "T5", "claim": "a reader at twice the grain also reads the half-scale tissue better (the control)",
     "rule": "HOLDS if, over the twins of the refined conditions with m 2, the mean of E_cg less E_u is >= 0, else FAILS"},
    {"id": "T6", "claim": "under the prompt signal, the doubled lengths read with the scaled reader as the twin reads with "
                          "the unscaled one",
     "rule": "HOLDS if, over the 54 refined conditions with m 0, the mean of E_cg less E_u of the twin lies within "
             "[-0.1, 0.1], else FAILS"},
    {"id": "T7", "claim": "where the patch is smaller than the coupling length, the unscaled reader loses even under the "
                          "prompt signal, and the scaled reader loses at most 0.05",
     "rule": "HOLDS if, over the refined conditions with m 0 and L / lam_rest < 1, the mean of E_u less E_u of the twin is "
             "<= -0.05 and the mean of E_cg less E_u of the twin is >= -0.05, else FAILS"},
    {"id": "T8", "claim": "the unscaled reader's late loss is a loss of the acquired phase (SM001's P42d on fresh blocks)",
     "rule": "HOLDS if, over the refined conditions with m 2, the mean of (E_u - gen_u) less the twin's (E_u - gen_u) is "
             "<= -0.05, else FAILS"},
]


def part_record(x, thr=None, sense=None):
    """A part's value, block values, SDs (the max rule), both halves of the blocks, its 95% interval, and against a
    threshold the pass, the margin in SDs and the halves' passes."""
    blk = x.mean(1)
    sd4, sdc, sd = A.sd_rule(x)
    n = len(blk)
    halves = [float(blk[: n // 2].mean()), float(blk[n // 2:].mean())] if n >= 2 else []
    half = float(student_t.ppf(0.975, n - 1) * sd / math.sqrt(n))
    rec = {"value": float(blk.mean()), "blocks": blk.tolist(), "sd4": sd4, "sdc": sdc, "sd": sd, "halves": halves,
           "ci95": [float(blk.mean()) - half, float(blk.mean()) + half]}
    if thr is not None:
        ok = (lambda v: v >= thr) if sense == "ge" else (lambda v: v <= thr)
        rec.update(threshold=thr, sense=sense, **{"pass": bool(ok(rec["value"]))},
                   margin=((rec["value"] - thr) if sense == "ge" else (thr - rec["value"])) / sd if sd > 0 else math.inf,
                   halves_pass=[bool(ok(h)) for h in halves])
    return rec


def score(rows, parts=None):
    parts = PARTS if parts is None else parts
    out = {}
    for sid, name, contrast, thr, sense in parts:
        st = out.setdefault(sid, {"verdict": None, "parts": {}})
        st["parts"][name] = part_record(CONTRASTS[contrast](rows), thr, sense) | {"contrast": contrast}
    for st in out.values():
        recs = list(st["parts"].values())
        st["verdict"] = "HOLDS" if all(p["pass"] for p in recs) else "FAILS"
    return out


def reported(rows):
    return {name: part_record(f(rows)) for name, f in CONTRASTS.items()}


def summary(scored):
    """T2's 95% interval and the fraction of T1's loss it leaves (T2 / T1; <= 0 where none remains), with the interval's
    bounds divided by T1."""
    t1 = next(iter(scored["T1"]["parts"].values()))["value"]
    t2 = next(iter(scored["T2"]["parts"].values()))
    return {"T1": t1, "T2": t2["value"], "T2_ci95": t2["ci95"], "T2_over_T1": t2["value"] / t1,
            "T2_ci95_over_T1": sorted(b / t1 for b in t2["ci95"])}


def freeze():
    FROZEN.mkdir(exist_ok=True)
    out = FROZEN / "predictions.json"
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thresholds": T,
                               "parts": [{"stmt": s, "name": n, "contrast": c, "threshold": t, "sense": se}
                                         for s, n, c, t, se in PARTS],
                               "reported": sorted(CONTRASTS), "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path)
    ap.add_argument("--stage", choices=("probe", "preflight", "dev"))
    ap.add_argument("--out", type=Path)
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args()
    if a.freeze:
        freeze()
        return
    a.out.mkdir(parents=True, exist_ok=True)
    pairs = A.stage_pairs(a.stage, a.root)
    Z, _ = A.load(a.root, pairs)
    rows = A.attach_twins(A.conditions(Z, pairs))
    scored = score(rows)
    (a.out / "predictions_scored.json").write_text(json.dumps(scored, indent=1) + "\n")
    (a.out / "reported.json").write_text(json.dumps({"parts": reported(rows), "summary": summary(scored)}, indent=1) + "\n")
    print({k: v["verdict"] for k, v in sorted(scored.items())})


if __name__ == "__main__":
    main()
