"""Fixed ordinary forecasts with explicitly specified injury curvature."""
import math
import numpy as np
from scipy.special import expit
from it_common import ROOT, C, ev, read, require
import ec_models

FAMILIES = ("condition0", "boundary0", "direct8", "direct64", "successor64")
BASE_NAMES = tuple(f"{curve}_{family}" for curve in ("linear", "quadratic") for family in FAMILIES)
CORRECTION_NAMES = tuple(f"{head}_{family}" for head in ec_models.HEADS for family in ec_models.FAMILIES)
NAMES = BASE_NAMES + CORRECTION_NAMES
READS = dict(condition0=0, boundary0=0, direct8=8, direct64=64, successor64=64)


def feature(row, name):
    curve, family = name.split("_", 1)
    require(name in BASE_NAMES, "Undeclared ordinary model")
    d, n = (row["injury"] - 24) / 12, float(row["regime"] == "independent")
    require(row["regime"] in ("matched", "independent"), "Undeclared noise")
    base = [d, n, d*n]
    if family != "condition0":
        require(len(row["boundary"]) == 11, "Original B11 required")
        base = [*row["boundary"], *base]
    if family in ("direct8", "direct64", "successor64"):
        q = row["fractions"]["successor32" if family == "successor64" else family]
        require(0 <= q <= 1, "Invalid measured fraction")
        base += [q, d*q, n*q]
    if curve == "quadratic":
        base += [d*d, n*d*d]
    require(np.isfinite(base).all(), "Nonfinite model input")
    return base


def models():
    path = ROOT / "FROZEN_CANDIDATES.json"
    require(ev.sha(path) == C["candidate_models_sha256"], "Candidate coefficients changed")
    value = read(path)
    require(set(value["models"]) == set(BASE_NAMES), "Incomplete candidate models")
    require(value["training_blocks"] == C["training_blocks"] and
            value["training_injuries"] == C["training_injuries"], "Wrong training domain")
    return value["models"]


def calibration():
    path = ROOT / "FROZEN_CALIBRATION.json"
    require(ev.sha(path) == C["calibration_models_sha256"], "Calibration coefficients changed")
    value = read(path)
    require(value["base_models"] == models(), "Calibration uses different base models")
    require(set(value["corrections"]) == set(CORRECTION_NAMES), "Incomplete fixed corrections")
    require(value["training_rows_sha256"] == ev.sha(ROOT / "context/TRAINING_ROWS.json"),
            "Correction training source differs")
    output = read(ROOT / "context/CALIBRATION_OUTPUTS.json")["sha256"]
    complete = read(ROOT / "context/CALIBRATION_COMPLETE.json")
    require(complete["status"] == "COMPLETE" and complete["output_manifest_sha256"] ==
            ev.sha(ROOT / "context/CALIBRATION_OUTPUTS.json") and
            output["FROZEN_MODELS.json"] == C["calibration_models_sha256"], "Calibration source is unbound")
    for name in ("VERIFICATION", "FIT_AUDITS", "ACCOUNTING", "FORECAST_SEAL"):
        require(ev.sha(ROOT / f"context/CALIBRATION_{name}.json") == output[name+".json"],
                "Calibration source receipt changed: " + name)
    require(read(ROOT / "context/CALIBRATION_VERIFICATION.json")["status"] == "PASS" and
            read(ROOT / "context/CALIBRATION_FIT_AUDITS.json")["qualified_new_fits"] == 44,
            "Calibration numerical qualification missing")
    return value["corrections"]


def probabilities(row, fitted=None, corrections=None):
    require(len(row["boundary"]) == 11 and row["current_pass"] in (0, 1) and
            row["current_pass"] == row["boundary"][5], "Original expression metadata differs from B11")
    fitted = models() if fitted is None else fitted
    corrections = calibration() if corrections is None else corrections
    result, logits = {}, {}
    for name in BASE_NAMES:
        model = fitted[name]
        x = feature(row, name)
        z = [(v-m)/s for v, m, s in zip(x, model["mean"], model["scale"], strict=True)]
        eta = math.fsum([model["coefficients"][0], *[
            a*b for a, b in zip(z, model["coefficients"][1:], strict=True)]])
        scalar = 1/(1+math.exp(-eta)) if eta >= 0 else math.exp(eta)/(1+math.exp(eta))
        vector = float(expit(np.r_[1., (np.asarray(x)-model["mean"])/model["scale"]]
                            @ model["coefficients"]))
        require(abs(scalar-vector) < 1e-12 and math.isfinite(vector), "Scalar candidate probability differs")
        result[name] = vector
        logits[name] = float(np.r_[1., (np.asarray(x)-model["mean"])/model["scale"]] @ model["coefficients"])
    for name in CORRECTION_NAMES:
        head, family = name.split("_", 1)
        ell = logits["quadratic_" + family]
        model = corrections[name]
        x = ec_models.correction_feature(row, ell, head)
        predicted = float(expit(ell + ec_models.logit([x], model)[0]))
        raw = ec_models.correction_functions(model, head, row["injury"], row["regime"])
        scalar = float(expit(math.fsum([raw["A"], raw["effective_logit_slope"]*ell,
                                       raw["C"]*(2*row["current_pass"]-1)])))
        require(math.isfinite(predicted) and abs(scalar-predicted) < 1e-12,
                "Independent raw correction equation differs")
        result[name] = predicted
    return result


def forecasts(ordinary_forecasts):
    fitted = models()
    corrections = calibration()
    return [dict(key=f["key"], block=f["block"], current_pass=f["current_pass"],
                 injury=f["injury"], regime=f["regime"], probabilities=probabilities(f, fitted, corrections))
            for f in ordinary_forecasts]


def check_sealed(ordinary, candidates):
    require(candidates == forecasts(ordinary), "Frozen candidate seal differs")
    return len(candidates) * len(NAMES)
