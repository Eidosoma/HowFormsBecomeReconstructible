"""SM004's statements and their scoring.

python -m sm004.predict --root STAGE_ROOT --model MODEL_JSON --fit-g4-root FIT_G4_ROOT --out DIR [--margins]
python -m sm004.predict --freeze      (sm004/frozen/predictions.json, at the freeze, on the lead's word)

Every part is linear in the case values (for the |error| parts, in the per-case absolute errors): per case, the mean over
the part's conditions of a paired difference; a block's value is the mean over its 8 cases; the part is the mean over
the blocks, unrounded. "The model" ("new") is SM004's frozen model; "F4" ("f4") SM003's frozen model; "the twin" of a
refined condition read at g is its transfer condition at half every length read at g, "the twin at g/2" the same read at
g / 2 (sm003.analyze.test_rows). A loss error is (E - E twin) - (the prediction - the prediction at the twin).

The rule (BE002's; PLAN_SM004.md): on P52 (SM003's P45 records, 4 blocks) each part sits at least 3 sqrt(1/4 + 1/16) =
1.68 SD inside its threshold and passes in both halves (900476-77, 900478-79); SD = sqrt(SD_T^2 + SD_F^2), SD_T the max
rule on the part's case values, SD_F the fitted predictors' sampling error: the larger of the SD over the 16
single-FIT-block refits and sqrt(16 x the jackknife variance), every fitted predictor the part uses refitted on the same
FIT block set (the model on that set's 864 means; F4 on SM003's 648 by SM003's procedure; the parametric, its g^2
variant and the 4-NN on the 864); SM001's model is held fixed. The thresholds are the narrowest round values
(design.STEP) the rule allows on P52 (--margins prints them); N8 and N9 register only above design.N89_MIN, N10 only at
design.N10_MIN or higher; a candidate that cannot register is reported.
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

from sm003 import analyze as A3  # noqa: E402
from sm004 import analyze as A  # noqa: E402
from sm004 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the thresholds: the narrowest the rule allows on P52 (probes/results/p52b_sm004_margins.txt, read 1 November 2026 after
# the P45 bridge and the model commit), proposed for the lead's review. N9 (narrowest -0.01, not above 0) and N10
# (narrowest -0.04, under -0.03) cannot register by the declared rule and are reported.
TH = {"N1": (-0.10, 0.05), "N2": (-0.05, 0.08), "N3": (-0.16, 0.01), "N4": (-0.07, 0.06), "N5": (-0.07, 0.06),
      "N6": (-0.10, 0.08), "N7": (-0.05, 0.09), "N8": 0.02}
FITTED = ("new", "f4", "par", "par2", "nn")
# two REPORTED sensitivities (the lead's ruling, 1 November 2026 about 23:53Z, after P52's H1 values were read; Amendment 1 in
# PLAN_SM004.md): H2 = H1 + G*c and H5, the leave-one-block-out best, each fitted on FIT exactly as the selection did
# (python -m sm004.analyze sensitivity) and frozen in its own file. They set no threshold, change no registered part, and
# are computed on the TEST stage only: their only out-of-sample values are TEST's.
SENSITIVITIES = ("H2", "H5")
SENS_SHA256 = {"H2": "6268fcb6d56ccaad4dfb130245dd86961900f60df8aaa8948ca82cba32336bfc",
               "H5": "d645f17c4298c9a94a08a461ab11ae1f465280875c24b0591cd0f1aa0fb7b18c"}


def sel(rows, kind, g, m=None, need=None):
    out = [r for r in rows if r["kind"] == kind and r["g"] == g and (m is None or r["m"] == m)]
    return [r for r in out if need is None or r.get(need) is not None]


def _fns():
    err = lambda key: (lambda r, P: r["E"] - P[key][id(r)])
    loss = lambda key, tw: (lambda r, P: (r["E"] - r[tw]["E"]) - (P[key][id(r)] - P[key][id(r[tw])]))
    aerr = lambda k1, k2: (lambda r, P: np.abs(r["E"] - P[k1][id(r)]) - np.abs(r["E"] - P[k2][id(r)]))
    aloss = lambda k1, k2: (lambda r, P: np.abs(loss(k1, "twin")(r, P)) - np.abs(loss(k2, "twin")(r, P)))
    obs = lambda tw: (lambda r, P: r["E"] - r[tw]["E"])
    return err, loss, aerr, aloss, obs


# each registered candidate: (id, words, conditions, f(row, P) -> per-case values, the fitted predictors it uses, kind)
def parts(rows):
    err, loss, aerr, aloss, _ = _fns()
    every = lambda kind, g, need=None: sel(rows, kind, g, need=need)
    late = lambda kind, g, need=None: sel(rows, kind, g, m=2, need=need)
    prompt = lambda kind, g, need=None: sel(rows, kind, g, m=0, need=need)
    return [
        ("N1", "the g-2 offset: refinement at g = 2, E - the model", every("refine", 2), err("new"), ("new",), "in"),
        ("N2", "the g-4 shortfall: refinement at g = 4, E - the model", every("refine", 4), err("new"), ("new",), "in"),
        ("N3", "the late loss: refinement read at g = 1, late (m 2): (E - E twin) - (the model - the model at the twin)",
         late("refine", 1, "twin"), loss("new", "twin"), ("new",), "in"),
        ("N4", "the prompt loss: refinement read at g = 1, prompt (m 0): the same", prompt("refine", 1, "twin"),
         loss("new", "twin"), ("new",), "in"),
        ("N5", "the larger sheet: transfer at g = 1, 2 and 4, E - the model",
         every("transfer", 1) + every("transfer", 2) + every("transfer", 4), err("new"), ("new",), "in"),
        ("N6", "the matched-reader gain at g = 2: (E - E twin at g/2) - (the model - the model at the twin at g/2)",
         every("refine", 2, "twin_half"), loss("new", "twin_half"), ("new",), "in"),
        ("N7", "the same at g = 4", every("refine", 4, "twin_half"), loss("new", "twin_half"), ("new",), "in"),
        ("N8", "closer than F4 at g = 4: refinement, |E - F4| - |E - the model|", every("refine", 4), aerr("f4", "new"),
         ("new", "f4"), "ge"),
        ("N9", "closer than F4 at g = 2: refinement, |E - F4| - |E - the model|", every("refine", 2), aerr("f4", "new"),
         ("new", "f4"), "ge"),
        ("N10", "the late loss kept against F4: refinement read at g = 1, late: |F4's loss error| - |the model's loss error|",
         late("refine", 1, "twin"), aloss("f4", "new"), ("new", "f4"), "ge"),
    ]


def reported_parts(rows):
    err, loss, aerr, aloss, obs = _fns()
    every = lambda kind, g, need=None: sel(rows, kind, g, need=need)
    late = lambda kind, g, need=None: sel(rows, kind, g, m=2, need=need)
    prompt = lambda kind, g, need=None: sel(rows, kind, g, m=0, need=need)
    return [
        ("R1", "refinement, g = 1: E - the model", every("refine", 1), err("new"), ("new",)),
        ("R2", "refinement, g = 1, late: E - the model", late("refine", 1), err("new"), ("new",)),
        ("R3", "refinement, g = 1, prompt: E - the model", prompt("refine", 1), err("new"), ("new",)),
        ("R4", "transfer, g = 1: E - the model", every("transfer", 1), err("new"), ("new",)),
        ("R5", "transfer, g = 2: E - the model", every("transfer", 2), err("new"), ("new",)),
        ("R6", "transfer, g = 4: E - the model", every("transfer", 4), err("new"), ("new",)),
        ("R7", "refinement, g = 2: E - F4 (SM003's R1)", every("refine", 2), err("f4"), ("f4",)),
        ("R8", "refinement, g = 4: E - F4 (SM003's M7)", every("refine", 4), err("f4"), ("f4",)),
        ("R9", "refinement, g = 1: |E - the parametric| - |E - the model|", every("refine", 1), aerr("par", "new"), ("par", "new")),
        ("R10", "refinement, g = 2: |E - the parametric| - |E - the model|", every("refine", 2), aerr("par", "new"), ("par", "new")),
        ("R11", "refinement, g = 4: |E - the parametric| - |E - the model|", every("refine", 4), aerr("par", "new"), ("par", "new")),
        ("R12", "refinement, g = 2: |E - the 4-NN| - |E - the model|", every("refine", 2), aerr("nn", "new"), ("nn", "new")),
        ("R13", "refinement, g = 4: |E - the 4-NN| - |E - the model|", every("refine", 4), aerr("nn", "new"), ("nn", "new")),
        ("R14", "refinement, g = 1: |E - SM001's model| - |E - the model|", every("refine", 1), aerr("sm1", "new"), ("new",)),
        ("R15", "refinement, g = 4: |E - the parametric with (log2 g)^2| - |E - the model|", every("refine", 4),
         aerr("par2", "new"), ("par2", "new")),
        ("R16", "refinement read at g = 1, late: E - E twin (the observed loss)", late("refine", 1, "twin"), obs("twin"), ()),
        ("R17", "refinement at g = 2: E - E twin at g/2 (SM003's M4)", every("refine", 2, "twin_half"), obs("twin_half"), ()),
        ("R18", "refinement at g = 4: E - E twin at g/2 (SM003's M5)", every("refine", 4, "twin_half"), obs("twin_half"), ()),
        ("R19", "the same at g = 2, late", late("refine", 2, "twin_half"), obs("twin_half"), ()),
        ("R20", "the same at g = 2, prompt", prompt("refine", 2, "twin_half"), obs("twin_half"), ()),
        ("R21", "the same at g = 4, late", late("refine", 4, "twin_half"), obs("twin_half"), ()),
        ("R22", "the same at g = 4, prompt", prompt("refine", 4, "twin_half"), obs("twin_half"), ()),
    ]


def frozen_fits(blob):
    return {"new": blob["model"], "f4": A.f4_blob()["model"], "par": blob["parametric"], "par2": blob["parametric_g2"],
            "nn": blob["nn"]}


def predict_all(rows, fits, keys=FITTED):
    out = {}
    for key in keys:
        if key == "new":
            out[key] = {id(r): A.predict(fits[key], r) for r in rows}
        elif key == "f4":
            out[key] = {id(r): A3.predict(fits[key], r) for r in rows}
        elif key in ("par", "par2"):
            out[key] = {id(r): A.predict_par(fits[key], r) for r in rows}
        else:
            out[key] = {id(r): A.predict_nn(fits[key], r) for r in rows}
    return out


def predictions(rows, blob):
    P = predict_all(rows, frozen_fits(blob))
    sm1 = A3.sm001_model()
    P["sm1"] = {id(r): A3.predict_sm001(sm1, r) for r in rows}
    return P


def refit_predictions(rows, blob, fitrows):
    """Every fitted predictor refitted on the 16 single FIT blocks and the 16 jackknife sets, its predictions on rows."""
    terms = blob["model"]["terms"]
    rows12 = [r for r in fitrows if r["g"] in (1, 2)]
    f4_terms = A.f4_blob()["model"]["terms"]
    n = len(fitrows[0]["blocks"])
    sets = {"single": [[b] for b in range(n)], "jack": [[i for i in range(n) if i != b] for b in range(n)]}
    out = {}
    for name, subsets in sets.items():
        out[name] = []
        for S in subsets:
            y = A.cond_means(fitrows, S)
            fits = {"new": A.fit_form(fitrows, terms, y), "f4": A3.fit_form(rows12, f4_terms, A.cond_means(rows12, S)),
                    "par": A.fit_par(fitrows, D.PAR_TERMS, y), "par2": A.fit_par(fitrows, D.PAR_TERMS_G2, y),
                    "nn": A.fit_nn(fitrows, y)}
            out[name].append(predict_all(rows, fits))
    return out


def sensitivity_fits():
    """The frozen sensitivities, each checked against its recorded sha256."""
    import hashlib
    out = {}
    for name in SENSITIVITIES:
        path = LANE / "sm004" / "frozen" / f"sensitivity_{name}.json"
        if hashlib.sha256(path.read_bytes()).hexdigest() != SENS_SHA256[name]:
            raise ValueError(f"{path}: not the frozen sensitivity")
        out[name] = json.loads(path.read_text())
    return out


def add_sensitivities(rows, fitrows, P, RP):
    """The sensitivities' predictions (keys s_H2, s_H5) beside the model's, frozen and refitted on the same FIT block sets
    (for SD_F); for the TEST stage only."""
    sens = sensitivity_fits()
    n = len(fitrows[0]["blocks"])
    sets = {"single": [[b] for b in range(n)], "jack": [[i for i in range(n) if i != b] for b in range(n)]}
    for name, blob in sens.items():
        key = f"s_{name}"
        P[key] = {id(r): A.predict(blob["model"], r) for r in rows}
        for set_name, subsets in sets.items():
            for Q, S in zip(RP[set_name], subsets):
                m = A.fit_form(fitrows, blob["model"]["terms"], A.cond_means(fitrows, S))
                Q[key] = {id(r): A.predict(m, r) for r in rows}
    return {name: {"model_sha256": b["model_sha256"], "terms": len(b["model"]["terms"]), "lobo": b["lobo"]}
            for name, b in sens.items()}


def score_with(rows, P, RP, key):
    """Every candidate part (N1-N10) as a number, with the model's predictions and refits replaced by key's: a
    sensitivity's values on the same parts, no thresholds (score_with(.., "new") is the model's own)."""
    Pk = dict(P, new=P[key])
    RPk = {name: [dict(Q, new=Q[key]) for Q in sets] for name, sets in RP.items()}
    return [{"id": pid, "part": words, **_value(rr, f, uses, Pk, RPk)} for pid, words, rr, f, uses, _kind in parts(rows)]


def case_values(sel_rows, f, P):
    if not sel_rows:
        raise ValueError("a part with no conditions")
    return np.mean([f(r, P) for r in sel_rows], axis=0)


def _value(rr, f, uses, P, RP):
    x = case_values(rr, f, P)
    nb = x.shape[0]
    sd4, sdc, sdT = A.sd_rule(x)
    sdF = {"sd_F": 0.0}
    if uses and RP is not None:
        val = lambda Q: float(case_values(rr, f, dict(P, **{k: Q[k] for k in uses})).mean())
        s_vals = np.array([val(Q) for Q in RP["single"]])
        j_vals = np.array([val(Q) for Q in RP["jack"]])
        sd_single = float(s_vals.std(ddof=1))
        sd_jack = float(math.sqrt((len(j_vals) - 1) * ((j_vals - j_vals.mean()) ** 2).sum()))
        sdF = {"sd_F": max(sd_single, sd_jack), "sd_single_F": sd_single, "sd_jack_F": sd_jack}
    sd = math.sqrt(sdT ** 2 + sdF["sd_F"] ** 2)
    v = float(x.mean())
    hw = stats.t.ppf(0.975, nb - 1) * sd / math.sqrt(nb)
    return {"value": v, "ci95": [v - hw, v + hw], "sd": sd, "sd4_T": sd4, "sdc_T": sdc, "sd_T": sdT, **sdF,
            "halves": [float(x[: nb // 2].mean()), float(x[nb // 2:].mean())], "n_conditions": len(rr),
            "blocks": x.mean(1).tolist()}


def narrowest(v, sd, halves, kind, step=D.STEP):
    """The narrowest round threshold (step) the rule allows: a band's each side, or a 'ge' part's largest lower bound."""
    need = K_RULE * sd                                   # sm003.predict.narrowest's arithmetic, unchanged
    if kind == "in":
        lo = math.floor((min(v - need, *halves)) / step) * step
        hi = math.ceil((max(v + need, *halves)) / step) * step
        return [round(lo, 2), round(hi, 2)]
    return round(math.floor((min(v - need, *halves)) / step) * step, 2)


def registers(pid, kind, th):
    if kind == "in":
        return True
    if pid in ("N8", "N9"):
        return th > D.N89_MIN
    if pid == "N10":
        return th >= D.N10_MIN
    return False


def score(rows, P, RP, th=None):
    th = TH if th is None else th
    out = []
    for pid, words, rr, f, uses, kind in parts(rows):
        rec = _value(rr, f, uses, P, RP)
        v, sd, halves = rec["value"], rec["sd"], rec["halves"]
        # on a single block (the debug run) the block SD and the halves are undefined (nan): no narrowest threshold
        nar = narrowest(v, sd, halves, kind) if all(math.isfinite(x) for x in (v, sd, *halves)) else None
        t = th.get(pid)
        rec = {"id": pid, "part": words, "kind": kind, "uses": list(uses), **rec, "narrowest": nar,
               "registers_at_narrowest": None if nar is None else registers(pid, kind, nar)}
        if t is not None:
            if kind == "in":
                lo, hi = t
                rec.update(threshold=list(t), holds=lo <= v <= hi, margins=[(v - lo) / sd, (hi - v) / sd],
                           rule_ok=min((v - lo) / sd, (hi - v) / sd) >= K_RULE and all(lo <= h <= hi for h in halves))
            else:
                rec.update(threshold=t, holds=v >= t, margins=[(v - t) / sd],
                           rule_ok=(v - t) / sd >= K_RULE and all(h >= t for h in halves))
        out.append(rec)
    return out


def score_reported(rows, P, RP):
    return [{"id": rid, "part": words, "uses": list(uses), **_value(rr, f, uses, P, RP)}
            for rid, words, rr, f, uses in reported_parts(rows)]


def predicted_contrasts(rows, P):
    """The contrasts the frozen fits predict from FIT alone (no E): the refinement losses at g 1 and the matched-reader
    gains at g 2 and 4, for the model and F4."""
    late = sel(rows, "refine", 1, m=2, need="twin")
    prompt = sel(rows, "refine", 1, m=0, need="twin")
    out = {}
    for key in ("new", "f4"):
        d = lambda rr, tw: float(np.mean([P[key][id(r)] - P[key][id(r[tw])] for r in rr]))
        out[key] = {"late_loss_g1": d(late, "twin"), "prompt_loss_g1": d(prompt, "twin"),
                    "matched_gain_g2": d(sel(rows, "refine", 2, need="twin_half"), "twin_half"),
                    "matched_gain_g4": d(sel(rows, "refine", 4, need="twin_half"), "twin_half")}
    return out


def verdicts(scored):
    return {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p}


def freeze():
    """sm004/frozen/predictions.json: the registered parts' ids, words, kinds and thresholds, the reported parts, the
    rule (python -m sm004.predict --freeze; at the freeze, on the lead's word)."""
    import hashlib
    import time
    if not TH:
        sys.exit("no thresholds: P52's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": pid, "part": words, "uses": list(uses), "kind": kind, "threshold": TH[pid]}
                          for pid, words, _rr, _f, uses, kind in parts([]) if pid in TH],
           "candidates_reported": [{"id": pid, "part": words, "uses": list(uses), "kind": kind}
                                   for pid, words, _rr, _f, uses, kind in parts([]) if pid not in TH],
           "reported": [{"id": rid, "part": words, "uses": list(uses)} for rid, words, _rr, _f, uses in reported_parts([])],
           "sensitivities": {name: {"file": f"sm004/frozen/sensitivity_{name}.json", "sha256": SENS_SHA256[name],
                                    "scored": "N1-N10 as numbers on TEST, no thresholds"} for name in SENSITIVITIES},
           "predict_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out = LANE / "sm004" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts,", len(rec["reported"]), "reported")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--fit-g4-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    rows = A.test_rows(a.root)
    blob = json.loads(a.model.read_text())
    fitrows = A.fit_rows(a.fit_g4_root)
    P = predictions(rows, blob)
    RP = refit_predictions(rows, blob, fitrows)
    scored = score(rows, P, RP)
    rep = score_reported(rows, P, RP)
    stage = json.loads((a.root / "manifest.json").read_text())["stage"]
    if stage == "test":
        sens_meta = add_sensitivities(rows, fitrows, P, RP)
        sens = {name: {**sens_meta[name], "parts": score_with(rows, P, RP, f"s_{name}")} for name in SENSITIVITIES}
    else:
        sens = "not computed before TEST (the lead's ruling, 1 November 2026 about 23:53Z: their only out-of-sample values are TEST's)"
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": str(a.root),
         "model_sha256": blob["model_sha256"], "chosen": blob["chosen"], "parts": scored, "verdicts": verdicts(scored),
         "reported": rep, "predicted_contrasts": predicted_contrasts(rows, P), "sensitivities": sens}, indent=1) + "\n")
    for p in scored:
        print(f"{p['id']:4s} {p['part'][:66]:66s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] "
              f"SD {p['sd']:.4f} (T {p['sd_T']:.4f}, F {p['sd_F']:.4f}) halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f}"
              + (f" narrowest {p['narrowest']} registers {p['registers_at_narrowest']}" if a.margins else "")
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
