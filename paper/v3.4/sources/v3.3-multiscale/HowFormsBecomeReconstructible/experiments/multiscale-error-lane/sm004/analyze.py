"""SM004's reader: the FIT rows at three grains, the grain-named model's selection and fit, the predictors, the SDs.

  E(cond, g)     the reader's agreement with the acquired template inside the injured patch at its last read, per case
                 (SM003's); g the reader's grain (1, 2 or 4); a block's value the mean over its 8 cases
  the variables  SM003's (a, b, c, d, e) = (log2 lam_rest / w, log2 L / lam_rest, m, log2 tau_c / T*, log2 L / g) and
                 G = log2 g, the grain as itself
  the model      logistic(beta . phi), least squares on the 864 FIT condition means (324 dial conditions at g 1 and 2, 216
                 at g 4), its form the admissible candidate (design.CANDIDATES; full rank and condition number <=
                 design.COND_MAX on the FIT conditions) with the smallest leave-one-block-out error, a smaller candidate
                 within design.SELECT_TOL of the best chosen (the rule fixed in PLAN_SM004.md before any fit)
  predictors     "new" the model; "f4" SM003's frozen F4 (sm003/frozen/model.json, unchanged); "sm1" SM001's frozen
                 model; "par" SM003's 21-term parametric and "par2" the same with (log2 g)^2, refitted on SM004's FIT
                 means; "nn" SM003's 4-NN on SM004's FIT conditions
  the SDs        SD_T the max rule on a part's case values (sm003.analyze.sd_rule); SD_F the fitted predictors' sampling
                 error (sm004.predict: every fitted predictor a part uses refitted on the same FIT block set)

python -m sm004.analyze fit --fit-g4-root RUN_ROOT/fit_g4 --out FILE     (the model blob: selection, model, comparators)
python -m sm004.analyze sensitivity --fit-g4-root RUN_ROOT/fit_g4 --name H2 --out FILE     (a reported sensitivity's
    blob: the candidate fitted on the 864 FIT means exactly as the selection fitted it; the lead's ruling, 1 November)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm001 import design as S1D  # noqa: E402
from sm003 import analyze as A3  # noqa: E402
from sm004 import design as D  # noqa: E402

READ = A3.READ
logistic = A3.logistic
cond_means = A3.cond_means
sd_rule = A3.sd_rule
test_rows = A3.test_rows


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------- the rows

def fit_rows(fit_g4_root, fit12_root=D.FIT12_ROOT, check=True):
    """The 864 FIT rows: SM003's 648 (g 1 and 2, its rereads, sha256-checked by sm003.analyze.fit_rows, in SM003's order),
    then the 216 g-4 rows of W8_x32 and W16_x32 from SM004's rereads (sha256-checked against their manifest, which must
    name SM001's FIT manifest), r_in from SM001's FIT shards."""
    rows = A3.fit_rows(fit12_root, check)
    fit_g4_root = Path(fit_g4_root)
    RM = json.loads((fit_g4_root / "manifest.json").read_text())
    FM = json.loads((Path(D.FIT_ROOT) / "manifest.json").read_text())
    if check:
        if RM["sm001_fit_manifest_sha256"] != sha(Path(D.FIT_ROOT) / "manifest.json"):
            raise ValueError("the g-4 rereads were made from another SM001 FIT manifest")
        for key, t in RM["tasks"].items():
            if sha(fit_g4_root / t["file"]["path"]) != t["file"]["sha256"]:
                raise ValueError(f"g-4 FIT reread {key}: sha256 differs")
    for u in D.FIT_G4_UNITS:
        blocks = sorted(b for uu, b in FM["pairs"] if uu == u)
        if sorted(int(k.split("/")[1]) for k in RM["tasks"] if k.split("/")[0] == u) != blocks:
            raise ValueError(f"{u}: the g-4 rereads do not cover SM001's FIT blocks")
        cfg = S1D.UNIT[u]
        Z4 = {b: np.load(fit_g4_root / "shards" / u / f"{b}.npz") for b in blocks}
        Zs = {b: np.load(Path(D.FIT_ROOT) / "shards" / u / f"{b}.npz") for b in blocks}
        for L in cfg["sizes"]:
            for ai, a in enumerate(S1D.unit_arms(u)):
                if a["never"]:
                    continue
                rows.append({"stage": "fit", "unit": u, "kind": "fit", "w": cfg["w"], "L": L, "arm": a["name"],
                             "c": a["c"], "lam": a["lam_rest"], "m": a["m"], "tau": a["tau_c"], "g": 4, "scale": 1,
                             "blocks": blocks, "E": np.array([Z4[b][f"L{L}/g4/in"][ai] for b in blocks]),
                             "E_gen": np.array([Z4[b][f"L{L}/g4/in_gen"][ai] for b in blocks]),
                             "r_in": np.array([Zs[b][f"L{L}/r_in"][READ, ai] for b in blocks]),
                             "x": A3.x_vars(cfg["w"], L, a["lam_rest"], a["m"], a["tau_c"], 4)})
    return rows


# ------------------------------------------------------------------------------------------------------------ models

def gvars(r):
    return {"1": 1.0, "a": math.log2(r["lam"] / r["w"]), "b": math.log2(r["L"] / r["lam"]), "c": float(r["m"]),
            "d": math.log2(r["tau"] / D.T_STAR), "e": math.log2(r["L"] / r["g"]), "G": math.log2(r["g"])}


def pvars(r):
    return {"1": 1.0, "A": math.log2(r["lam"]), "B": math.log2(r["w"]), "C": math.log2(r["L"]), "M": float(r["m"]),
            "G": math.log2(r["g"]), "T": math.log2(r["tau"])}


def _col(v, t):
    if "^" in t:
        s, p = t.split("^")
        return v[s] ** int(p)
    if "*" in t:
        s1, s2 = t.split("*")
        return v[s1] * v[s2]
    return v[t]


def phi(r, terms):
    v = gvars(r)
    return np.array([_col(v, t) for t in terms])


def phi_par(r, terms):
    v = pvars(r)
    return np.array([_col(v, t) for t in terms])


def fit_form(rows, terms, y=None):
    return A3._fit(np.array([phi(r, terms) for r in rows]), cond_means(rows) if y is None else y, terms)


def predict(model, r):
    return float(logistic(phi(r, model["terms"]) @ np.array(model["beta"])))


def fit_par(rows, terms, y=None):
    return A3._fit(np.array([phi_par(r, terms) for r in rows]), cond_means(rows) if y is None else y, terms)


def predict_par(par, r):
    return float(logistic(phi_par(r, par["terms"]) @ np.array(par["beta"])))


def fit_nn(rows, y=None):
    """SM003's 4-NN (sm003.analyze.fit_nn) on these rows, its targets the condition means (or y, a refit's)."""
    nn = A3.fit_nn(rows)
    if y is not None:
        nn["train_y"] = [float(v) for v in y]
    return nn


predict_nn = A3.predict_nn


def identification(rows, terms):
    """The FIT design's identification from the x's alone: the column rank and the condition number with the
    non-constant columns centred and scaled to unit SD (the constant kept)."""
    X = np.array([phi(r, terms) for r in rows])
    Z = X.copy()
    Z[:, 1:] = (Z[:, 1:] - Z[:, 1:].mean(0)) / Z[:, 1:].std(0)
    s = np.linalg.svd(Z, compute_uv=False)
    rank = int(np.linalg.matrix_rank(Z, tol=1e-10 * s[0]))
    cond = float(s[0] / s[-1])
    return {"terms": len(terms), "rank": rank, "cond": cond, "admissible": rank == len(terms) and cond <= D.COND_MAX}


def lobo(rows, terms):
    """The leave-one-block-out error: refit on 15 FIT blocks, predict the held-out block's condition means; the mean
    absolute error over every held-out value."""
    n = len(rows[0]["blocks"])
    errs = []
    for b in range(n):
        model = fit_form(rows, terms, cond_means(rows, [i for i in range(n) if i != b]))
        pred = np.array([predict(model, r) for r in rows])
        errs.append(np.abs(cond_means(rows, [b]) - pred))
    return float(np.mean(errs))


def select(rows):
    """The declared rule: among the admissible candidates, the smallest LOBO error, unless a smaller candidate is within
    SELECT_TOL of it (then the smallest such)."""
    ident = {name: identification(rows, terms) for name, terms in D.CANDIDATES.items()}
    err = {name: lobo(rows, terms) for name, terms in D.CANDIDATES.items() if ident[name]["admissible"]}
    best = min(err.values())
    chosen = next(name for name in D.CANDIDATES if name in err and err[name] <= best + D.SELECT_TOL)
    return chosen, err, ident


def f4_blob():
    return json.loads((LANE / "sm003" / "frozen" / "model.json").read_text())


def model_blob(rows, fit_g4_root):
    chosen, err, ident = select(rows)
    model = fit_form(rows, D.CANDIDATES[chosen])
    by_g = {g: [r for r in rows if r["g"] == g] for g in D.FIT_GRAINS}
    bias = {str(g): float(np.mean([r["E"].mean() - predict(model, r) for r in rr])) for g, rr in by_g.items()}
    blob = {"study": D.STUDY, "design_digest": D.digest(), "chosen": chosen, "lobo": err, "identification": ident,
            "model": model, "fit_bias_by_grain": bias,
            "candidates": {name: fit_form(rows, terms) for name, terms in D.CANDIDATES.items()},
            "parametric": fit_par(rows, D.PAR_TERMS), "parametric_g2": fit_par(rows, D.PAR_TERMS_G2), "nn": fit_nn(rows),
            "fit_conditions": [[r["unit"], r["L"], r["arm"], r["g"]] for r in rows], "fit_blocks": rows[0]["blocks"],
            "fit_means": [[r["unit"], r["L"], r["arm"], r["g"], float(r["E"].mean())] for r in rows],
            "fit12_manifest_sha256": sha(Path(D.FIT12_ROOT) / "manifest.json"),
            "fit_g4_manifest_sha256": sha(Path(fit_g4_root) / "manifest.json"),
            "sm001_fit_manifest_sha256": sha(Path(D.FIT_ROOT) / "manifest.json"),
            "sm003_model_sha256": sha(LANE / "sm003" / "frozen" / "model.json"),
            "sm001_model_sha256": sha(LANE / "sm001" / "frozen" / "model.json")}
    blob["model_sha256"] = hashlib.sha256(json.dumps(blob["model"], sort_keys=True).encode()).hexdigest()
    return blob


def sensitivity_blob(rows, fit_g4_root, name):
    """A reported sensitivity (the lead's ruling, 1 November 2026 about 23:53Z: H2 and H5): the candidate fitted on the 864 FIT means
    exactly as the selection fitted it (fit_form on every FIT block), with its leave-one-block-out error; FIT only."""
    terms = D.CANDIDATES[name]
    model = fit_form(rows, terms)
    blob = {"study": D.STUDY, "design_digest": D.digest(), "name": name, "reported_sensitivity": True, "model": model,
            "lobo": lobo(rows, terms), "identification": identification(rows, terms),
            "fit12_manifest_sha256": sha(Path(D.FIT12_ROOT) / "manifest.json"),
            "fit_g4_manifest_sha256": sha(Path(fit_g4_root) / "manifest.json"),
            "sm001_fit_manifest_sha256": sha(Path(D.FIT_ROOT) / "manifest.json")}
    blob["model_sha256"] = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
    return blob


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--fit-g4-root", type=Path, required=True)
    f.add_argument("--out", type=Path, required=True)
    sv = sub.add_parser("sensitivity")
    sv.add_argument("--fit-g4-root", type=Path, required=True)
    sv.add_argument("--name", choices=tuple(D.CANDIDATES), required=True)
    sv.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rows = fit_rows(a.fit_g4_root)
    if a.cmd == "sensitivity":
        blob = sensitivity_blob(rows, a.fit_g4_root, a.name)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(blob, indent=1) + "\n")
        print(a.name, "lobo", round(blob["lobo"], 6), "R2", round(blob["model"]["r2"], 6), "model_sha256", blob["model_sha256"][:16])
        return
    blob = model_blob(rows, a.fit_g4_root)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(blob, indent=1) + "\n")
    print("chosen", blob["chosen"], "lobo", json.dumps({k: round(v, 6) for k, v in blob["lobo"].items()}), "R2",
          round(blob["model"]["r2"], 6), "fit bias by g", json.dumps({k: round(v, 4) for k, v in blob["fit_bias_by_grain"].items()}),
          "parametric R2", round(blob["parametric"]["r2"], 6))


if __name__ == "__main__":
    main()
