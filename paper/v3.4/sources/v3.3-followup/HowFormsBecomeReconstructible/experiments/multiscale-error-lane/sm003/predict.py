"""SM003's statements and their scoring.

python -m sm003.predict --root TEST_ROOT --model MODEL_JSON --fit-root FIT_REREAD_ROOT --out DIR [--margins]

Every part is linear in the case values (for the |error| parts, in the per-case absolute errors): per case, the mean over
the part's conditions of a paired difference; a block's value is the mean over its 8 cases; the part is the mean over the
blocks, unrounded. "The model" is the frozen reader-named model (sm003.analyze.model_blob), a fixed number per condition;
SM001's model is sm001/frozen/model.json; "the parametric" is the frozen absolute-length comparator. "The twin at g / 2"
of a refined condition (w, L, c, m, tau) read at grain g is the transfer condition (w/2, L/2, c/2, m, tau) read at g / 2:
every declared length of tissue and reader halved, the same blocks, cases, acquisition draws, noise streams, anchors and
patch corner.

The rule (BE002's, the lead's statement for SM001 and SM002): on P45 each part sits at least 3 sqrt(1/4 + 1/16) = 1.68 SD
inside its threshold and passes in both halves of P45 (900476-77, 900478-79), SD = sqrt(SD_T^2 + SD_F^2): SD_T the max
rule on the part's case values, SD_F the model's own sampling error in the part (the larger of the SD over the 16
single-FIT-block refits and sqrt(16 x the jackknife variance); 0 for a part without the model). --margins prints, for
every part, the narrowest threshold (0.01 steps) the rule allows on the stage given, for drafting.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm003 import analyze as A  # noqa: E402
from sm003 import design as D  # noqa: E402

K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
# the proposed thresholds (from P45; see parts)
TH = {"M1": (-0.09, 0.08), "M2": (-0.11, 0.07), "M3": (-0.04, 0.1), "M4": (0.02, 0.16), "M5": (0.02, 0.14),
      "M7": 0.04}                   # M6 withdrawn on the lead's ruling (the comparator's defect): reported as R12


def sel(rows, kind, g, m=None, L=None, need=None):
    out = [r for r in rows if r["kind"] == kind and r["g"] == g and (m is None or r["m"] == m) and (L is None or r["L"] == L)]
    return [r for r in out if need is None or r.get(need) is not None]


# each part: (statement, words, selection, f(row, P) -> per-case values (blocks, cases), uses the model, kind, threshold);
# P carries the predictions: P["new"][id(row)], P["sm1"][id(row)], P["par"][id(row)]; "twin" is the transfer condition
# at half every length read at the same grain, "twin_half" the same read at g / 2. The thresholds are the narrowest round
# values the rule allows on P45 (probes/results/p45b_sm003_margins.txt), proposed for the lead's review.
def parts(rows):
    late = lambda kind, g, need=None: sel(rows, kind, g, m=2, need=need)
    prompt = lambda kind, g, need=None: sel(rows, kind, g, m=0, need=need)
    every = lambda kind, g, need=None: sel(rows, kind, g, need=need)
    err = lambda key: (lambda r, P: r["E"] - P[key][id(r)])
    aerr = lambda k1, k2: (lambda r, P: np.abs(r["E"] - P[k1][id(r)]) - np.abs(r["E"] - P[k2][id(r)]))
    loss = lambda r, P: (r["E"] - r["twin"]["E"]) - (P["new"][id(r)] - P["new"][id(r["twin"])])
    half = lambda r, P: r["E"] - r["twin_half"]["E"]
    return [
        ("M1", "transfer, g = 1 and 2: E - the model", every("transfer", 1) + every("transfer", 2), err("new"), True, "in", TH["M1"]),
        ("M2", "refinement read at g = 1, late (m 2): (E - E twin) - (the model - the model's twin)", late("refine", 1, "twin"),
         loss, True, "in", TH["M2"]),
        ("M3", "refinement read at g = 1, prompt (m 0): (E - E twin) - (the model - the model's twin)", prompt("refine", 1, "twin"),
         loss, True, "in", TH["M3"]),
        ("M4", "refinement read at g = 2 against the twin read at g = 1 (the model: 0)", every("refine", 2, "twin_half"), half,
         False, "in", TH["M4"]),
        ("M5", "refinement read at g = 4 against the twin read at g = 2 (the model: 0)", every("refine", 4, "twin_half"), half,
         False, "in", TH["M5"]),
        ("M7", "refinement, g = 4: E - the model", every("refine", 4), err("new"), True, "ge", TH["M7"]),
    ]


# the reported parts (not registered), scored the same way
def reported_parts(rows):
    every = lambda kind, g, need=None: sel(rows, kind, g, need=need)
    late = lambda kind, g, need=None: sel(rows, kind, g, m=2, need=need)
    err = lambda key: (lambda r, P: r["E"] - P[key][id(r)])
    aerr = lambda k1, k2: (lambda r, P: np.abs(r["E"] - P[k1][id(r)]) - np.abs(r["E"] - P[k2][id(r)]))
    obs = lambda r, P: r["E"] - r["twin"]["E"]
    return [
        ("R1", "refinement, g = 2: E - the model", every("refine", 2), err("new"), True),
        ("R2", "refinement, g = 1: E - the model", every("refine", 1), err("new"), True),
        ("R3", "refinement, g = 1, late: E - the model", late("refine", 1), err("new"), True),
        ("R4", "refinement, g = 1: |E - SM001's model| - |E - the model|", every("refine", 1), aerr("sm1", "new"), True),
        ("R5", "refinement, g = 1: E - SM001's model", every("refine", 1), err("sm1"), False),
        ("R6", "refinement read at g = 1, late: E - E twin (observed)", late("refine", 1, "twin"), obs, False),
        ("R7", "transfer, g = 4: E - the model", every("transfer", 4), err("new"), True),
        ("R8", "refinement, g = 1: |E - the parametric| - |E - the model|", every("refine", 1), aerr("par", "new"), True),
        ("R9", "refinement, g = 2: |E - the parametric| - |E - the model|", every("refine", 2), aerr("par", "new"), True),
        ("R10", "refinement, g = 2: |E - the 4-NN (ties exact)| - |E - the model|", every("refine", 2), aerr("nn", "new"), True),
        ("R11", "refinement, g = 4: |E - the 4-NN (ties exact)| - |E - the model|", every("refine", 4), aerr("nn", "new"), True),
        ("R12", "refinement, g = 4: |E - the parametric (21 terms)| - |E - the model| (the withdrawn M6)", every("refine", 4),
         aerr("par", "new"), True),
        ("R13", "transfer, g = 1: E - the model", every("transfer", 1), err("new"), True),
        ("R14", "transfer, g = 2: E - the model", every("transfer", 2), err("new"), True),
        ("R15", "refinement read at g = 2 against the twin read at g = 1, late (m 2): SM002's T2 on fresh blocks",
         late("refine", 2, "twin_half"), lambda r, P: r["E"] - r["twin_half"]["E"], False),
    ]


def predictions(rows, blob, model=None):
    model = blob["model"] if model is None else model
    sm1 = A.sm001_model()
    return {"new": {id(r): A.predict(model, r) for r in rows}, "sm1": {id(r): A.predict_sm001(sm1, r) for r in rows},
            "par": {id(r): A.predict_par(blob["parametric"], r) for r in rows},
            "nn": {id(r): A.predict_nn(blob["nn"], r) for r in rows}}


def case_values(sel_rows, f, P):
    if not sel_rows:
        raise ValueError("a part with no conditions")
    return np.mean([f(r, P) for r in sel_rows], axis=0)


def refits(blob, fitrows):
    """The 16 single-block refits and the 16 jackknife refits of the chosen form (cached by the caller)."""
    terms = blob["model"]["terms"]
    n = len(fitrows[0]["blocks"])
    single = [A.fit_form(fitrows, terms, A.cond_means(fitrows, [b])) for b in range(n)]
    jack = [A.fit_form(fitrows, terms, A.cond_means(fitrows, [i for i in range(n) if i != b])) for b in range(n)]
    return single, jack


def _value(rows, rr, f, uses, P, refit):
    """A part's case values, value, SD_T parts, SD_F (the model's refits) and halves."""
    x = case_values(rr, f, P)
    nb = x.shape[0]
    sd4, sdc, sdT = A.sd_rule(x)
    sdF = {"sd_F": 0.0}
    if uses and refit is not None:
        single, jack = refit
        val = lambda model: float(case_values(rr, f, dict(P, new={id(r): A.predict(model, r) for r in rows})).mean())
        s_vals = np.array([val(mm) for mm in single])
        j_vals = np.array([val(mm) for mm in jack])
        sd_single = float(s_vals.std(ddof=1))
        sd_jack = float(math.sqrt((len(j_vals) - 1) * ((j_vals - j_vals.mean()) ** 2).sum()))
        sdF = {"sd_F": max(sd_single, sd_jack), "sd_single_F": sd_single, "sd_jack_F": sd_jack}
    sd = math.sqrt(sdT ** 2 + sdF["sd_F"] ** 2)
    v = float(x.mean())
    hw = stats.t.ppf(0.975, nb - 1) * sd / math.sqrt(nb)
    return x, {"value": v, "ci95": [v - hw, v + hw], "sd": sd, "sd4_T": sd4, "sdc_T": sdc, "sd_T": sdT, **sdF,
               "halves": [float(x[: nb // 2].mean()), float(x[nb // 2:].mean())], "n_conditions": len(rr),
               "blocks": x.mean(1).tolist()}


def score(rows, blob, fitrows=None, refit=None, margins=False):
    P = predictions(rows, blob)
    out = []
    if refit is None and fitrows is not None:
        refit = refits(blob, fitrows)
    for sid, words, rr, f, uses, kind, th in parts(rows):
        x, rec = _value(rows, rr, f, uses, P, refit)
        v, sd, (h1, h2) = rec["value"], rec["sd"], rec["halves"]
        if kind == "in":
            lo, hi = th
            ok = lo <= v <= hi
            marg = ((v - lo) / sd, (hi - v) / sd)
            halves_ok = all(lo <= h <= hi for h in (h1, h2))
        else:
            ok = v >= th
            marg = ((v - th) / sd,)
            halves_ok = h1 >= th and h2 >= th
        rec = {"id": sid, "part": words, **rec, "kind": kind, "threshold": list(th) if kind == "in" else th, "holds": ok,
               "margins": list(marg), "rule_ok": min(marg) >= K_RULE and halves_ok}
        if margins:
            rec["narrowest"] = narrowest(v, sd, (h1, h2), kind)
        out.append(rec)
    return out


def score_reported(rows, blob, fitrows=None, refit=None):
    P = predictions(rows, blob)
    if refit is None and fitrows is not None:
        refit = refits(blob, fitrows)
    return [{"id": rid, "part": words, **_value(rows, rr, f, uses, P, refit)[1]} for rid, words, rr, f, uses in reported_parts(rows)]


def narrowest(v, sd, halves, kind, step=0.01):
    """The narrowest round threshold (step) the rule allows: a band's each side, or a 'ge' part's largest lower bound."""
    need = K_RULE * sd
    if kind == "in":
        lo = math.floor((min(v - need, *halves)) / step) * step
        hi = math.ceil((max(v + need, *halves)) / step) * step
        return [round(lo, 2), round(hi, 2)]
    lb = math.floor((min(v - need, *halves)) / step) * step
    return round(lb, 2)


def verdicts(scored):
    by = {}
    for p in scored:
        by.setdefault(p["id"], []).append(p["holds"])
    return {k: "HOLDS" if all(v) else "FAILS" for k, v in by.items()}


def freeze():
    """sm003/frozen/predictions.json: every registered part's id, words, kind and threshold, the reported parts, and the
    rule (python -m sm003.predict --freeze; at the freeze, on the lead's word)."""
    import hashlib
    import time
    dummy = []
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": sid, "part": words, "uses_model": uses, "kind": kind, "threshold": th}
                          for sid, words, _rr, _f, uses, kind, th in parts(dummy)],
           "reported": [{"id": rid, "part": words, "uses_model": uses} for rid, words, _rr, _f, uses in reported_parts(dummy)],
           "predict_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out = LANE / "sm003" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts,", len(rec["reported"]), "reported")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--fit-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    rows = A.test_rows(a.root)
    blob = json.loads(a.model.read_text())
    fitrows = A.fit_rows(a.fit_root)
    refit = refits(blob, fitrows)
    scored = score(rows, blob, refit=refit, margins=a.margins)
    rep = score_reported(rows, blob, refit=refit)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps({"parts": scored, "verdicts": verdicts(scored),
                                                               "reported": rep}, indent=1) + "\n")
    for p in scored:
        print(f"{p['id']:3s} {p['part'][:70]:70s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] "
              f"SD {p['sd']:.4f} (T {p['sd_T']:.4f}, F {p['sd_F']:.4f}) margins {', '.join(f'{m:.2f}' for m in p['margins'])} "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} {'HOLDS' if p['holds'] else 'FAILS'}"
              + (f" narrowest {p['narrowest']}" if a.margins else ""))


if __name__ == "__main__":
    main()
