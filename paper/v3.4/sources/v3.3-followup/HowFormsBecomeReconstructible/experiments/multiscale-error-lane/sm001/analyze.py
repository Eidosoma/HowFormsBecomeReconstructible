"""SM001's reader, models and the margin rule's SDs.

  E(cond)        the endpoint: the fresh successor's agreement with the acquired template inside the injured patch after
                 2,000 updates of reading the episode's final record (protected), per case; a block's value is the mean
                 over its 8 cases, a condition's the mean over its blocks
  x(cond)        (lam_rest / w, L / lam_rest, d / T*, tau_c / T*), from the design (sm001.design.x_vars)
  the model      the dimensionless model, fitted on the FIT stage's condition means, frozen: E-hat = logistic(beta . phi),
                 phi quadratic in (a, b, c) = (log2 x1, log2 x2, x3) and linear in d = log2 x4 (MODEL_TERMS), least squares
                 on the condition means (the form chosen on P42's FIT pilot, before the freeze: R^2 0.69, against 0.45
                 for the main effects only; leave-one-block-out error 0.107 against a one-block noise floor of 0.088)
  the comparators two strong predictors on the absolute parameters, fitted on the same means and frozen with the model
                 (both reported): the k-nearest-neighbour mean (K_NN) on (log2 lam_rest, log2 w, log2 L, d, log2 tau_c),
                 each standardised by its FIT-stage SD; and a parametric one, the model's logistic least squares on a
                 quadratic in (log2 lam_rest, log2 w, log2 L, m) plus log2 tau_c linear (PAR_TERMS, 16 terms), which nests
                 the dimensionless model (its gain is what the reduction to x loses) and, unlike the 4-NN, extrapolates
  the SDs        a part's SD is sqrt(SD_T^2 + SD_F^2) (the lead's review, 31 October 2026): SD_T the max rule (sd_rule) on the
                 TEST-side case values with any FIT-stage reference held fixed; SD_F that reference's own sampling error,
                 0 where there is none (ref_sd): for an observed FIT mean the max rule on the FIT stage's per-block, per-case
                 reference, for the model the larger of the SD over single-block refits and sqrt(n x the jackknife variance)

python -m sm001.analyze --root ROOT --stage {probe,preflight,fit} [--write-model PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import least_squares

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import design as D  # noqa: E402

READ2 = -1                                    # the successor's last read (2,000 updates)
READ1 = -1                                    # the episode's last read (4,000 updates)
MODEL_TERMS = ("1", "a", "b", "c", "d", "a*b", "b^2", "a^2", "c*b", "c*a", "c^2")    # a log2 x1, b log2 x2, c x3, d log2 x4
K_NN = 4
ABS_TERMS = ("log2 lam", "log2 w", "log2 L", "d", "log2 tau")
PAR_TERMS = ("1", "A", "B", "C", "M", "A^2", "B^2", "C^2", "M^2", "A*B", "A*C", "A*M", "B*C", "B*M", "C*M", "T")
# A log2 lam_rest, B log2 w, C log2 L, M the delay multiple m, T log2 tau_c


def load(root, pairs):
    Z = {(u, b): dict(np.load(Path(root) / "shards" / u / f"{b}.npz")) for u, b in pairs}
    meta = {key: json.loads(str(z["__meta__"])) for key, z in Z.items()}
    return Z, meta


def stage_pairs(stage, root=None):
    """(FIT pairs, TEST pairs) of a stage; for preflight (and probe) with a manifest, its own (unit, block) pairs."""
    if root is not None and stage in ("preflight", "probe") and (Path(root) / "manifest.json").exists():
        pairs = [tuple(x) for x in json.loads((Path(root) / "manifest.json").read_text())["pairs"]]
        return [p for p in pairs if D.UNIT[p[0]]["stage"] == "fit"], [p for p in pairs if D.UNIT[p[0]]["stage"] == "test"]
    if stage == "probe":
        fit, test = (list(range(*D.PROBE_BLOCKS[s])) for s in ("fit", "test"))
        return [(u, b) for u in D.FIT_UNITS for b in fit], [(u, b) for u in D.TEST_UNITS for b in test]
    if stage == "preflight":
        bl = D.stage_blocks("preflight")
        return [(u, b) for u in D.FIT_UNITS for b in bl], [(u, b) for u in D.TEST_UNITS for b in bl]
    blocks = D.stage_blocks(stage)
    units = D.FIT_UNITS if stage == "fit" else D.TEST_UNITS
    return ([(u, b) for u in units for b in blocks], []) if stage == "fit" else ([], [(u, b) for u in units for b in blocks])


def conditions(Z, pairs, never=False):
    """One row per (unit, patch size, arm) over the pairs' blocks: the design's values and the per-block, per-case
    endpoints. Dial arms only unless never."""
    units = sorted({u for u, _ in pairs}, key=list(D.UNIT).index)
    rows = []
    for u in units:
        blocks = sorted(b for uu, b in pairs if uu == u)
        cfg = D.UNIT[u]
        arms = D.unit_arms(u)
        for L in cfg["sizes"]:
            rn = f"L{L}"
            for ai, a in enumerate(arms):
                if a["never"] != never:
                    continue
                g = lambda key, ri=-1, j=ai: np.array([Z[(u, b)][f"{rn}/{key}"][ri, j] for b in blocks])
                row = {"unit": u, "kind": cfg["kind"], "side": cfg["side"], "scale": cfg["scale"], "place": cfg["place"],
                       "w": cfg["w"], "L": L, "arm": a["name"], "c": a["c"], "lam": a["lam_rest"], "m": a["m"],
                       "d": a["delay"], "tau": a["tau_c"], "dil": cfg["dil"], "blocks": blocks,
                       "E": g("s/in", READ2), "E_ctrl": g("s/in", READ2, len(arms)), "E_gen": g("s/in_gen", READ2),
                       "r_in": g("r_in", READ1), "shape": g("s/shape", READ2), "spacing": g("s/spacing", READ2),
                       "wall": np.array([Z[(u, b)][f"{rn}/wall"] for b in blocks]),
                       "n_anc": np.array([Z[(u, b)][f"{rn}/n_anc"] for b in blocks]),
                       "hit": np.array([Z[(u, b)][f"{rn}/hit"][ai] for b in blocks])}
                if not never:
                    row["x"] = D.x_vars(cfg["w"], L, a["lam_rest"], a["m"], a["tau_c"])
                rows.append(row)
    return rows


def phi(x):
    a, b, c, d = np.log2(x[0]), np.log2(x[1]), float(x[2]), np.log2(x[3])
    return np.array([1.0, a, b, c, d, a * b, b * b, a * a, c * b, c * a, c * c])


def absf(row):
    return np.array([np.log2(row["lam"]), np.log2(row["w"]), np.log2(row["L"]), float(row["d"]), np.log2(row["tau"])])


def phi_par(row):
    A, B, C, M, T = np.log2(row["lam"]), np.log2(row["w"]), np.log2(row["L"]), float(row["m"]), np.log2(row["tau"])
    return np.array([1.0, A, B, C, M, A * A, B * B, C * C, M * M, A * B, A * C, A * M, B * C, B * M, C * M, T])


def logistic(z):
    return 1.0 / (1.0 + np.exp(-z))


def _fit_logistic(X, y, terms):
    sol = least_squares(lambda b: logistic(X @ b) - y, np.zeros(X.shape[1]), method="lm", xtol=1e-14, ftol=1e-14)
    return {"terms": list(terms), "beta": sol.x.tolist(), "n": len(y), "rss": float((sol.fun ** 2).sum()),
            "r2": float(1 - (sol.fun ** 2).sum() / ((y - y.mean()) ** 2).sum())}


def cond_means(rows, blocks=None, key="E"):
    """Each condition's mean over the given block indices (all by default) and their cases."""
    return np.array([(r[key] if blocks is None else r[key][blocks]).mean() for r in rows])


def fit_model(rows, y=None):
    """The dimensionless model: least squares of logistic(beta . phi(x)) on the condition means (equal weights)."""
    return _fit_logistic(np.array([phi(r["x"]) for r in rows]), cond_means(rows) if y is None else y, MODEL_TERMS)


def fit_param(rows, y=None):
    """The parametric comparator: the same least squares on PAR_TERMS of the absolute parameters."""
    return _fit_logistic(np.array([phi_par(r) for r in rows]), cond_means(rows) if y is None else y, PAR_TERMS)


def fit_comparator(rows):
    """The absolute comparator: the training conditions' absolute features (standardised by their SDs) and means."""
    A = np.array([absf(r) for r in rows])
    sd = A.std(0, ddof=0)
    sd = np.where(sd > 0, sd, 1.0)
    return {"terms": list(ABS_TERMS), "k": K_NN, "sd": sd.tolist(), "train_A": (A / sd).tolist(),
            "train_y": [float(r["E"].mean()) for r in rows]}


def predict_model(model, row):
    return float(logistic(phi(row["x"]) @ np.array(model["beta"])))


def predict_comparator(comp, row):
    A, y = np.array(comp["train_A"]), np.array(comp["train_y"])
    q = absf(row) / np.array(comp["sd"])
    dist = np.sqrt(((A - q) ** 2).sum(1))
    order = np.lexsort((np.arange(len(dist)), dist))[: comp["k"]]
    return float(y[order].mean())


def predict_param(par, row):
    return float(logistic(phi_par(row) @ np.array(par["beta"])))


def fkey(r):
    return (r["w"], r["L"], r["c"], r["m"], r["tau"])


def key32(r):
    """The FIT condition with the same dimensionless x: the same lengths for transfer, every length halved for
    refinement (the scale), the same delay and commitment."""
    s = r["scale"]
    return (r["w"] // s, r["L"] // s, r["c"] / s, r["m"], r["tau"])


def model_blob(fit_rows, fit_manifest_sha=None):
    m = {"design_digest": D.digest(), "model": fit_model(fit_rows), "comparator": fit_comparator(fit_rows),
         "comparator_param": fit_param(fit_rows),
         "fit_conditions": [[r["unit"], r["L"], r["arm"]] for r in fit_rows], "fit_blocks": fit_rows[0]["blocks"],
         "fit_manifest_sha256": fit_manifest_sha,
         "fit_means": [[list(fkey(r)), float(r["E"].mean())] for r in fit_rows],
         "fit_rin": [[list(fkey(r)), float(r["r_in"].mean())] for r in fit_rows]}
    m["model_sha256"] = hashlib.sha256(json.dumps(m["model"], sort_keys=True).encode()).hexdigest()
    return m


# the margin rule's SDs ----------------------------------------------------------------------------------------------

def sd_rule(x):
    """(SD over the blocks' means, SD over every case / sqrt(cases a block), the larger) for case values x (blocks,
    cases): BE002's block SD with the lead's case floor (BE009)."""
    blk = x.mean(1)
    sd4 = float(blk.std(ddof=1))
    sdc = float(x.ravel().std(ddof=1) / math.sqrt(x.shape[1]))
    return sd4, sdc, max(sd4, sdc)


def ref_cases(conds, fit_rows, key):
    """The FIT stage's per-block, per-case reference of an observed mean: the mean over the TEST conditions of the
    matching FIT condition's values (blocks, cases)."""
    by = {fkey(r): r for r in fit_rows}
    return np.mean([by[key32(c)][key] for c in conds], axis=0)


def ref_model_mean(conds, fit_rows, blocks):
    """The model refitted on the condition means over the given FIT block indices, averaged over the TEST conditions."""
    model = fit_model(fit_rows, cond_means(fit_rows, blocks))
    return float(np.mean([predict_model(model, c) for c in conds]))


def ref_sd(kind, key, conds, fit_rows):
    """SD_F of a FIT-stage reference over the TEST conditions conds, with its parts: ('obs', key) the max rule on
    ref_cases; ('model', None) the larger of the SD over single-block refits and sqrt(n x the jackknife variance)."""
    if kind == "obs":
        sd4, sdc, sd = sd_rule(ref_cases(conds, fit_rows, key))
        return {"sd_F": sd, "sd4_F": sd4, "sdc_F": sdc}
    n = len(fit_rows[0]["blocks"])
    single = np.array([ref_model_mean(conds, fit_rows, [b]) for b in range(n)])
    jack = np.array([ref_model_mean(conds, fit_rows, [i for i in range(n) if i != b]) for b in range(n)])
    sd_single = float(single.std(ddof=1))
    sd_jack = float(math.sqrt((n - 1) * ((jack - jack.mean()) ** 2).sum()))
    return {"sd_F": max(sd_single, sd_jack), "sd_single_F": sd_single, "sd_jack_F": sd_jack}


def ref_mean(kind, key, conds, fit_rows, blocks=None):
    """The reference averaged over the TEST conditions, from the given FIT block indices (all by default)."""
    if kind == "obs":
        x = ref_cases(conds, fit_rows, key)
        return float((x if blocks is None else x[blocks]).mean())
    return ref_model_mean(conds, fit_rows, list(range(len(fit_rows[0]["blocks"]))) if blocks is None else blocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("probe", "preflight", "fit"), required=True)
    ap.add_argument("--write-model", type=Path, default=None)
    a = ap.parse_args()
    fit_pairs, _ = stage_pairs(a.stage, a.root)
    Z, _ = load(a.root, fit_pairs)
    rows = conditions(Z, fit_pairs)
    man = a.root / "manifest.json"
    blob = model_blob(rows, hashlib.sha256(man.read_bytes()).hexdigest() if (man.exists() and a.stage == "fit") else None)
    print("model:", json.dumps(blob["model"]))
    if a.write_model is not None:
        a.write_model.write_text(json.dumps(blob, indent=1) + "\n")


if __name__ == "__main__":
    main()
