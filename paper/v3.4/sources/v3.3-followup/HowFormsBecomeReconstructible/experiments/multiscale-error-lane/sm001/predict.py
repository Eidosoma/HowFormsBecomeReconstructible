"""SM001's registered statements and their scoring.

python -m sm001.predict --root ROOT --stage {probe,preflight,fit,test} --out DIR [--model PATH] [--fit-root ROOT]
python -m sm001.predict --freeze      (writes sm001/frozen/predictions.json)

Two stages. FIT: the model and both comparators are fitted on the FIT stage's condition means (sm001.analyze.model_blob)
and S8 is scored; both go to DIR/model.json, which fork M commits as sm001/frozen/model.json before any TEST block is
drawn (sm001.run refuses the test stage otherwise). TEST: S1-S7 are scored on the 16 fresh blocks with the frozen file
(--model); S8 is carried from it, scored at FIT. Probe and preflight: both in one pass, the model fitted on the stage's
FIT-unit blocks and S1-S8 scored on its blocks.

Every part is linear in the case values: per case, the mean over the part's conditions of a paired difference (the same
case's acquisition and draws in every condition of a block); a block's value is the mean over its 8 cases; the part is
the mean over the blocks, unrounded. The twin of a refined condition (w, L, c, m, tau) is the transfer condition
(w/2, L/2, c/2, m, tau): the same side 64, blocks, cases, acquisition draws, noise streams, anchors and patch corner,
with every declared length halved. Refinement is scored against its twin inside the TEST stage; against the 32 x 32
means it is reported (F3-F6: the statements S3-S6 before the lead's review of 31 October 2026).

DIR also gets reported.json: the reported parts (F3-F6, R1-R3, the comparators C against the model on each TEST set),
each with its SD_T and, where FIT rows are at hand (probe, preflight, or the TEST stage with --fit-root), its SD_F; and a
summary (the FIT R^2 of the model and of the parametric comparator; each predictor's error on each TEST set).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import analyze as A  # noqa: E402
from sm001 import design as D  # noqa: E402

FROZEN = LANE / "sm001" / "frozen"

# the thresholds, set from P42 under BE002's rule as the lead's review states it: each part >= 3 sqrt(1/4 + 1/16) = 1.68
# SDs inside its threshold, SD = sqrt(SD_T^2 + SD_F^2) (sm001.analyze), and both P42 halves passing
T = {"S1": 0.15, "S2": 0.15, "S3": 0.1, "S4": -0.05, "S5": 0.0, "S6": -0.05, "S7": 0.0, "S8": 0.0}
SETS = ("transfer", "refine", "mid", "cross")


def attach(test_rows, blob):
    """Each TEST row's predictions (the frozen model, the 4-NN, the parametric comparator), the FIT stage's means at the
    same x (E_32, rin_32) and, for a refined row, its twin (the transfer row at half every length, the same blocks)."""
    model, comp, par = blob["model"], blob["comparator"], blob["comparator_param"]
    obs = {tuple(k): v for k, v in blob["fit_means"]}
    rin = {tuple(k): v for k, v in blob["fit_rin"]}
    by = {(r["kind"],) + A.fkey(r): r for r in test_rows}
    for r in test_rows:
        r["E_dim"], r["E_abs"], r["E_par"] = A.predict_model(model, r), A.predict_comparator(comp, r), A.predict_param(par, r)
        r["E_32"], r["rin_32"] = obs.get(A.key32(r)), rin.get(A.key32(r))
        r["twin"] = by.get(("transfer",) + A.key32(r)) if r["kind"] == "refine" else None
        if r["twin"] is not None and r["twin"]["blocks"] != r["blocks"]:
            raise ValueError(f"the twin of {r['unit']} L{r['L']} {r['arm']} is on other blocks")
    return test_rows


def cases_of(rows, f):
    return np.mean([f(r) for r in rows], axis=0)


def _kind(rows, kind, **kw):
    return [r for r in rows if r["kind"] == kind and all(r[k] == v for k, v in kw.items())]


def _twin(rows, m, f, L=None):
    """Per case, the mean over the refined conditions at delay multiple m (and patch size L) of f(row) - f(its twin)."""
    rr = [r for r in _kind(rows, "refine", m=m) if L is None or r["L"] == L]
    if not rr or any(r["twin"] is None for r in rr):
        raise ValueError("a refined condition without its twin")
    return np.mean([f(r) - f(r["twin"]) for r in rr], axis=0)


def _pairs_geo(rows):
    mid, cross = _kind(rows, "mid"), _kind(rows, "cross")
    return [(a, b) for a in mid for b in cross if (a["L"], a["arm"]) == (b["L"], b["arm"])]


def _doubling(fit_rows):
    by = {A.fkey(r): r for r in fit_rows}
    return [(by[k2], by[k]) for k in by for k2 in [(2 * k[0], 2 * k[1], 2 * k[2], k[3], k[4])] if k2 in by and k[3] >= 2]


E = lambda r: r["E"]                                          # noqa: E731
RIN = lambda r: r["r_in"]                                     # noqa: E731
SHARE = lambda r: r["E"] - r["r_in"]                          # noqa: E731  the successor's own share
TRANSFER = lambda R: _kind(R, "transfer")                     # noqa: E731
REFINE0 = lambda R: _kind(R, "refine", m=0)                   # noqa: E731
REFINE2 = lambda R: _kind(R, "refine", m=2)                   # noqa: E731
GEO = lambda R: np.mean([a["E"] - b["E"] for a, b in _pairs_geo(R)], axis=0)            # noqa: E731
DOUBLE = lambda R: np.mean([a["E"] - b["E"] for a, b in _doubling(R)], axis=0)          # noqa: E731
LESS_32 = lambda R, sel: cases_of(sel(R), lambda r: r["E"] - r["E_32"])                 # noqa: E731
LESS_MODEL = lambda R, sel: cases_of(sel(R), lambda r: r["E"] - r["E_dim"])             # noqa: E731

# (statement, part name, the stage of its rows, rows -> case values (blocks, cases), threshold, sense, reference):
# the reference is None (inside one stage: SD_F 0), ('obs', key, conditions) for an observed FIT mean subtracted, or
# ('model', None, conditions) for the frozen model subtracted
PARTS = [
    ("S1", "S1 transfer: mean (E_64 - E_32 at the same lengths) >= -0.15", "test",
     lambda R: LESS_32(R, TRANSFER), -T["S1"], "ge", ("obs", "E", TRANSFER)),
    ("S1", "S1 transfer: mean (E_64 - E_32 at the same lengths) <= 0.15", "test",
     lambda R: LESS_32(R, TRANSFER), T["S1"], "le", ("obs", "E", TRANSFER)),
    ("S2", "S2 transfer: mean (E - model) >= -0.15", "test",
     lambda R: LESS_MODEL(R, TRANSFER), -T["S2"], "ge", ("model", None, TRANSFER)),
    ("S2", "S2 transfer: mean (E - model) <= 0.15", "test",
     lambda R: LESS_MODEL(R, TRANSFER), T["S2"], "le", ("model", None, TRANSFER)),
    ("S3", "S3 refinement, prompt (m 0): mean (E - E_twin) >= -0.1", "test", lambda R: _twin(R, 0, E), -T["S3"], "ge", None),
    ("S3", "S3 refinement, prompt (m 0): mean (E - E_twin) <= 0.1", "test", lambda R: _twin(R, 0, E), T["S3"], "le", None),
    ("S4", "S4 refinement, late (m 2): mean (E - E_twin) <= -0.05", "test", lambda R: _twin(R, 2, E), T["S4"], "le", None),
    ("S5", "S5 refinement, prompt (m 0): mean (episode r_in - r_in_twin) >= 0", "test",
     lambda R: _twin(R, 0, RIN), T["S5"], "ge", None),
    ("S6", "S6 refinement, late (m 2): mean ((E - r_in) - (E_twin - r_in_twin)) <= -0.05", "test",
     lambda R: _twin(R, 2, SHARE), T["S6"], "le", None),
    ("S7", "S7 geometry (w 16): mean (E_mid - E_cross) >= 0", "test", GEO, T["S7"], "ge", None),
    ("S8", "S8 FIT, late (m 2, 4): mean (E at (2 lam, 2 w, 2 L) - E at (lam, w, L)) <= 0", "fit", DOUBLE, T["S8"], "le", None),
]

STATEMENTS = [
    {"id": "S1", "claim": "more cells at the same lengths leave the reconstruction unchanged",
     "rule": "HOLDS if, over the transfer conditions, the mean of E at 64 x 64 less the FIT stage's E at the same lengths "
             "lies within [-0.15, 0.15], else FAILS"},
    {"id": "S2", "claim": "the frozen model predicts the larger sheet at the same lengths",
     "rule": "HOLDS if, over the transfer conditions, the mean of E less the frozen model lies within [-0.15, 0.15], "
             "else FAILS"},
    {"id": "S3", "claim": "doubling every declared length leaves the prompt signal's reconstruction unchanged",
     "rule": "HOLDS if, over the refined conditions with the prompt signal (m 0), the mean of E less E of the twin lies "
             "within [-0.1, 0.1], else FAILS"},
    {"id": "S4", "claim": "doubling every declared length lowers the late signal's reconstruction",
     "rule": "HOLDS if, over the refined conditions with the signal at 2 T* (m 2), the mean of E less E of the twin is "
             "<= -0.05, else FAILS"},
    {"id": "S5", "claim": "doubling every declared length does not lower the episode's own repair under the prompt signal",
     "rule": "HOLDS if, over the refined conditions with m 0, the mean of the episode's r_in less the twin's is >= 0, "
             "else FAILS"},
    {"id": "S6", "claim": "the late signal's loss under doubling is the successor's, not the episode's",
     "rule": "HOLDS if, over the refined conditions with m 2, the mean of (E - r_in) less the twin's (E - r_in) is "
             "<= -0.05, else FAILS"},
    {"id": "S7", "claim": "a wall costs the reconstruction",
     "rule": "HOLDS if, at w 16, the mean over (L, arm) of E with the patch mid-stripe less E with it straddling a wall "
             "is >= 0, else FAILS"},
    {"id": "S8", "claim": "within one sheet, doubling every declared length lowers a late signal's reconstruction",
     "rule": "HOLDS if, on the FIT stage, over every pair of conditions with the same delay (m 2 or 4) and commitment, one "
             "at (2 lam, 2 w, 2 L) and one at (lam, w, L), the mean of E at the doubled lengths less E at the undoubled "
             "is <= 0, else FAILS"},
]

# reported, not registered: the full refinement against the 32 x 32 means (the statements S3-S6 before the review, with
# their thresholds then), the twin's other contrasts, and the comparators against the model on each TEST set
REPORTED = [
    ("F3", "F3 full refinement, prompt (m 0): mean (E_refined - E_32 at the same x) >= -0.1", "test",
     lambda R: LESS_32(R, REFINE0), -0.1, "ge", ("obs", "E", REFINE0)),
    ("F3", "F3 full refinement, prompt (m 0): mean (E_refined - E_32 at the same x) <= 0.1", "test",
     lambda R: LESS_32(R, REFINE0), 0.1, "le", ("obs", "E", REFINE0)),
    ("F4", "F4 full refinement, late (m 2): mean (E_refined - E_32 at the same x) <= -0.02", "test",
     lambda R: LESS_32(R, REFINE2), -0.02, "le", ("obs", "E", REFINE2)),
    ("F5", "F5 full refinement, prompt (m 0): mean (episode r_in refined - r_in at 32, the same x) >= 0.02", "test",
     lambda R: cases_of(REFINE0(R), lambda r: r["r_in"] - r["rin_32"]), 0.02, "ge", ("obs", "r_in", REFINE0)),
    ("F6", "F6 full refinement, late (m 2): mean (E - model) <= -0.04", "test",
     lambda R: LESS_MODEL(R, REFINE2), -0.04, "le", ("model", None, REFINE2)),
    ("R1", "R1 refinement, late (m 2): mean (episode r_in - r_in_twin)", "test", lambda R: _twin(R, 2, RIN), None, None, None),
    ("R2", "R2 refinement, prompt (m 0): mean ((E - r_in) - (E_twin - r_in_twin)) <= 0", "test",
     lambda R: _twin(R, 0, SHARE), 0.0, "le", None),
    *(("R3", f"R3 refinement, late (m 2), L {L}: mean (E - E_twin)", "test",
       lambda R, L=L: _twin(R, 2, E, L), None, None, None) for L in (4, 8, 16)),
    *(("C", f"C {k}: mean (|E - {name}| - |E - model|)", "test",
       lambda R, k=k, key=key: cases_of(_kind(R, k), lambda r: np.abs(r["E"] - r[key]) - np.abs(r["E"] - r["E_dim"])),
       None, None, "na") for k in SETS for name, key in (("4-NN", "E_abs"), ("parametric", "E_par"))),
]


def part_record(stage, f, thr, sense, ref, test_rows, fit_rows):
    """A part's value and block values, SD_T (the max rule on its case values), SD_F (0 inside one stage; from the FIT
    rows for a FIT-stage reference, when at hand; not computed for 'na'), the combined SD, and against a threshold the
    pass and the margin in combined SDs."""
    x = f(test_rows if stage == "test" else fit_rows)
    blk = x.mean(1)
    rec = {"value": float(blk.mean()), "blocks": blk.tolist()}
    sd4, sdc, sd_t = A.sd_rule(x)
    rec.update(sd4_T=sd4, sdc_T=sdc, sd_T=sd_t)
    if ref is None:
        rec["sd_F"] = 0.0
    elif ref != "na" and fit_rows is not None:
        rec.update(A.ref_sd(ref[0], ref[1], ref[2](test_rows), fit_rows))
    if "sd_F" in rec:
        rec["sd"] = math.sqrt(sd_t ** 2 + rec["sd_F"] ** 2)
    if thr is not None:
        ok = rec["value"] >= thr if sense == "ge" else rec["value"] <= thr
        rec.update(threshold=thr, sense=sense, **{"pass": bool(ok)})
        if "sd" in rec:
            rec["margin"] = ((rec["value"] - thr) if sense == "ge" else (thr - rec["value"])) / rec["sd"]
    return rec


def score(test_rows, fit_rows, parts=PARTS, stages=("fit", "test")):
    out = {}
    for sid, name, stage, f, thr, sense, ref in parts:
        if stage not in stages or (test_rows if stage == "test" else fit_rows) is None:
            continue
        st = out.setdefault(sid, {"verdict": None, "parts": {}})
        st["parts"][name] = part_record(stage, f, thr, sense, ref, test_rows, fit_rows)
    for st in out.values():
        recs = [p for p in st["parts"].values() if "pass" in p]
        st["verdict"] = ("HOLDS" if all(p["pass"] for p in recs) else "FAILS") if recs else "REPORTED"
    return out


def summary(test_rows, blob):
    """The FIT R^2 of both fitted models; each predictor's condition-level error (mean |pooled E - prediction|) and bias
    on each TEST set."""
    out = {"fit_r2": {"model": blob["model"]["r2"], "parametric": blob["comparator_param"]["r2"]}, "sets": {}}
    for k in SETS:
        rows = _kind(test_rows, k) if test_rows else []
        if not rows:
            continue
        e = np.array([r["E"].mean() for r in rows])
        out["sets"][k] = {"conditions": len(rows), **{f"mae_{n}": float(np.abs(e - np.array([r[key] for r in rows])).mean())
                                                       for n, key in (("model", "E_dim"), ("4nn", "E_abs"), ("parametric", "E_par"))},
                          **{f"bias_{n}": float((e - np.array([r[key] for r in rows])).mean())
                             for n, key in (("model", "E_dim"), ("4nn", "E_abs"), ("parametric", "E_par"))}}
    return out


def freeze():
    FROZEN.mkdir(exist_ok=True)
    out = FROZEN / "predictions.json"
    rec = lambda sid, name, stage, thr, sense, ref: {"stmt": sid, "name": name, "stage": stage, "threshold": thr,  # noqa: E731
                                                     "sense": sense, "reference": ref if ref in (None, "na") else list(ref[:2])}
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thresholds": T,
                               "parts": [rec(s, n, st, t, se, r) for s, n, st, f, t, se, r in PARTS],
                               "reported": [rec(s, n, st, t, se, r) for s, n, st, f, t, se, r in REPORTED],
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path)
    ap.add_argument("--stage", choices=("probe", "preflight", "fit", "test"))
    ap.add_argument("--model", type=Path, default=FROZEN / "model.json")
    ap.add_argument("--fit-root", type=Path, default=None, help="the TEST stage: the FIT stage's root, for the SD_F")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args()
    if a.freeze:
        freeze()
        return
    a.out.mkdir(parents=True, exist_ok=True)
    fit_pairs, test_pairs = A.stage_pairs(a.stage, a.root)
    fit_rows = test_rows = None
    if fit_pairs:
        Zf, _ = A.load(a.root, fit_pairs)
        fit_rows = A.conditions(Zf, fit_pairs)
    elif a.fit_root is not None:
        fp, _ = A.stage_pairs("fit")
        Zf, _ = A.load(a.fit_root, fp)
        fit_rows = A.conditions(Zf, fp)
    if a.stage == "test":
        blob = json.loads(a.model.read_text())
        if blob["design_digest"] != D.digest():
            sys.exit("the frozen model's design digest differs from the design's")
    else:
        man = a.root / "manifest.json"
        blob = A.model_blob(fit_rows, hashlib.sha256(man.read_bytes()).hexdigest() if (a.stage == "fit" and man.exists()) else None)
    if test_pairs:
        Zt, _ = A.load(a.root, test_pairs)
        test_rows = attach(A.conditions(Zt, test_pairs), blob)
    stages = {"fit": ("fit",), "test": ("test",)}.get(a.stage, ("fit", "test"))
    scored = score(test_rows, fit_rows, PARTS, stages)
    if a.stage == "fit":
        blob["s8"] = scored                                       # S8, scored at FIT, frozen with the model
    if a.stage == "test":
        scored.update({k: dict(v, scored_at="FIT (carried from the frozen model.json)") for k, v in blob["s8"].items()})
    if a.stage != "test":
        (a.out / "model.json").write_text(json.dumps(blob, indent=1) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(scored, indent=1) + "\n")
    reported = {"parts": score(test_rows, fit_rows, REPORTED, ("test",)) if test_rows else {}, "summary": summary(test_rows, blob)}
    (a.out / "reported.json").write_text(json.dumps(reported, indent=1) + "\n")
    print({k: v["verdict"] for k, v in sorted(scored.items())})


if __name__ == "__main__":
    main()
