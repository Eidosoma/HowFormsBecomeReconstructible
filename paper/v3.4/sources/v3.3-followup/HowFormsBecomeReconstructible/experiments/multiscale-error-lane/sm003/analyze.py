"""SM003's reader: the FIT and TEST rows, the reader-named model and its comparators, and the margin rule's SDs.

  E(cond, g)     the reader's agreement with the acquired template inside the injured patch at its last read (2,000
                 updates), per case; g the reader's grain (1, 2 or 4); a block's value the mean over its 8 cases
  x(cond, g)     (a, b, c, d, e) = (log2 lam_rest / w, log2 L / lam_rest, m, log2 tau_c / T*, log2 L / g)
  the model      logistic(beta . phi(x)), least squares on the FIT condition means (648: 324 dial conditions x g = 1, 2),
                 its form the candidate (design.CANDIDATES) with the smallest leave-one-block-out error on the 16 FIT
                 blocks, a smaller candidate within design.SELECT_TOL of the best chosen (the rule fixed in PLAN_SM003.md)
  comparators    SM001's frozen model (sm001/frozen/model.json, unchanged: it does not know g); a parametric model on the
                 absolute lengths and g (a quadratic in log2 lam, log2 w, log2 L, m, log2 g plus log2 tau linear: 22
                 terms; it nests the model); the 4-NN on (log2 lam, log2 w, log2 L, d, log2 tau, log2 g), standardised by
                 the FIT SDs
  the SDs        SD_T the max rule on a part's TEST-side case values (the larger of the SD over the blocks' means and the
                 SD over every case / sqrt 8); SD_F the model's own sampling error over the part's conditions (the larger
                 of the SD over single-FIT-block refits and sqrt(16 x the jackknife variance)); SD = sqrt(SD_T^2 + SD_F^2)

python -m sm003.analyze fit --fit-root RUN_ROOT/fit_reread --out FILE     (the model blob: model, comparators, selection)
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
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm001 import analyze as A1  # noqa: E402
from sm001 import design as S1D  # noqa: E402
from sm003 import design as D  # noqa: E402

READ = -1


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------- the rows

def x_vars(w, L, lam, m, tau, g):
    """(a, b, c, d, e) and the coarse-reader indicator k (used only by the reported sensitivity F5)."""
    return (math.log2(lam / w), math.log2(L / lam), float(m), math.log2(tau / D.T_STAR), math.log2(L / g), float(g > 1))


def fit_rows(fit_root, check=True):
    """The FIT rows: every SM001 FIT dial condition at g = 1 and 2, E from the rereads (the g = 1 values are SM001's own,
    bit for bit), r_in from SM001's FIT shards. Both stages' files are checked by sha256 against their manifests."""
    fit_root = Path(fit_root)
    RM = json.loads((fit_root / "manifest.json").read_text())
    FM = json.loads((Path(D.FIT_ROOT) / "manifest.json").read_text())
    if check:
        if RM["sm001_fit_manifest_sha256"] != sha(Path(D.FIT_ROOT) / "manifest.json"):
            raise ValueError("the rereads were made from another SM001 FIT manifest")
        for key, t in RM["tasks"].items():
            if sha(fit_root / t["file"]["path"]) != t["file"]["sha256"] or not t["bridge_all_equal"]:
                raise ValueError(f"FIT reread {key}: sha256 or the bridge fails")
        for key, t in FM["tasks"].items():
            if sha(Path(D.FIT_ROOT) / t["files"]["shards"]["path"]) != t["files"]["shards"]["sha256"]:
                raise ValueError(f"SM001 FIT shard {key}: sha256 differs")
    rows = []
    for u in D.FIT_UNITS:
        blocks = sorted(b for uu, b in FM["pairs"] if uu == u)
        cfg = S1D.UNIT[u]
        arms = S1D.unit_arms(u)
        Zr = {b: np.load(fit_root / "shards" / u / f"{b}.npz") for b in blocks}
        Zs = {b: np.load(Path(D.FIT_ROOT) / "shards" / u / f"{b}.npz") for b in blocks}
        for L in cfg["sizes"]:
            for ai, a in enumerate(arms):
                if a["never"]:
                    continue
                for g in D.FIT_GRAINS:
                    rows.append({"stage": "fit", "unit": u, "kind": "fit", "w": cfg["w"], "L": L, "arm": a["name"],
                                 "c": a["c"], "lam": a["lam_rest"], "m": a["m"], "tau": a["tau_c"], "g": g, "scale": 1,
                                 "blocks": blocks,
                                 "E": np.array([Zr[b][f"L{L}/g{g}/in"][ai] for b in blocks]),
                                 "E_gen": np.array([Zr[b][f"L{L}/g{g}/in_gen"][ai] for b in blocks]),
                                 "r_in": np.array([Zs[b][f"L{L}/r_in"][READ, ai] for b in blocks]),
                                 "x": x_vars(cfg["w"], L, a["lam_rest"], a["m"], a["tau_c"], g)})
    return rows


KEY = {1: "u/in", 2: "cg/in", 4: "g4/in"}
KEY_GEN = {1: "u/in_gen", 2: "cg/in_gen", 4: "g4/in_gen"}


def test_rows(root, check=True):
    """The TEST rows of a stage root (probe, preflight or test): every dial condition of the six units at each grain the
    unit is read at; refined rows carry their twins at g (same grain) and at g / 2 (the matched comparison)."""
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    if check:
        bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(root / f["path"]) != f["sha256"]]
        if bad:
            raise ValueError(f"sha256 differs: {bad[:5]}")
    pairs = [tuple(p) for p in M["pairs"]]
    rows = []
    for u in D.UNITS:
        blocks = sorted(b for uu, b in pairs if uu == u)
        if not blocks:
            continue
        cfg = S1D.UNIT[u]
        arms = D.unit_arms(u)
        Z = {b: np.load(root / "shards" / u / f"{b}.npz") for b in blocks}
        for b in blocks:
            meta = json.loads(str(Z[b]["__meta__"]))
            if meta["unit"] != u or meta["block"] != b or meta["design_digest"] != M["design_digest"]:
                raise ValueError(f"{u} {b}: the shard's meta does not match the manifest")
        for L in cfg["sizes"]:
            for ai, a in enumerate(arms):
                for g in D.unit_grains(u):
                    get = lambda key, j=ai: np.array([(Z[b][f"L{L}/{key}"][READ, j] if key.startswith("u/")
                                                       else Z[b][f"L{L}/{key}"][j]) for b in blocks])
                    rows.append({"stage": M["stage"], "unit": u, "kind": cfg["kind"], "w": cfg["w"], "L": L,
                                 "arm": a["name"], "c": a["c"], "lam": a["lam_rest"], "m": a["m"], "tau": a["tau_c"],
                                 "g": g, "scale": cfg["scale"], "blocks": blocks, "E": get(KEY[g]), "E_gen": get(KEY_GEN[g]),
                                 "E_ctrl": np.array([(Z[b][f"L{L}/{KEY[g]}"][READ, len(arms)] if g == 1
                                                      else Z[b][f"L{L}/{KEY[g]}"][len(arms)]) for b in blocks]),
                                 "r_in": np.array([Z[b][f"L{L}/r_in"][READ, ai] for b in blocks]),
                                 "x": x_vars(cfg["w"], L, a["lam_rest"], a["m"], a["tau_c"], g)})
    by = {(r["kind"], r["w"], r["L"], r["c"], r["m"], r["tau"], r["g"]): r for r in rows}
    for r in rows:
        if r["kind"] == "refine":
            for name, gg in (("twin", r["g"]), ("twin_half", r["g"] // 2 if r["g"] > 1 else None)):
                t = by.get(("transfer", r["w"] // 2, r["L"] // 2, r["c"] / 2, r["m"], r["tau"], gg)) if gg else None
                if t is not None and t["blocks"] != r["blocks"]:
                    raise ValueError("a twin on other blocks")
                r[name] = t
    return rows


# ------------------------------------------------------------------------------------------------------------ models

def phi(x, terms):
    a, b, c, d, e, k = x
    v = {"1": 1.0, "a": a, "b": b, "c": c, "d": d, "e": e, "k": k}
    out = []
    for t in terms:
        if "^" in t:
            s, p = t.split("^")
            out.append(v[s] ** int(p))
        elif "*" in t:
            s1, s2 = t.split("*")
            out.append(v[s1] * v[s2])
        else:
            out.append(v[t])
    return np.array(out)


PAR_TERMS = D.PAR_TERMS          # 21 terms: no (log2 g)^2 (the lead's ruling; see sm003.design)


def phi_par(r):
    v = {"1": 1.0, "A": math.log2(r["lam"]), "B": math.log2(r["w"]), "C": math.log2(r["L"]), "M": float(r["m"]),
         "G": math.log2(r["g"]), "T": math.log2(r["tau"])}
    out = []
    for t in PAR_TERMS:
        if "^" in t:
            s, p = t.split("^")
            out.append(v[s] ** int(p))
        elif "*" in t:
            s1, s2 = t.split("*")
            out.append(v[s1] * v[s2])
        else:
            out.append(v[t])
    return np.array(out)


def absf(r):
    return np.array([math.log2(r["lam"]), math.log2(r["w"]), math.log2(r["L"]), float(round(r["m"] * D.T_STAR)),
                     math.log2(r["tau"]), math.log2(r["g"])])


logistic = A1.logistic


def _fit(X, y, terms):
    sol = least_squares(lambda b: logistic(X @ b) - y, np.zeros(X.shape[1]), method="lm", xtol=1e-14, ftol=1e-14)
    return {"terms": list(terms), "beta": sol.x.tolist(), "n": len(y), "rss": float((sol.fun ** 2).sum()),
            "r2": float(1 - (sol.fun ** 2).sum() / ((y - y.mean()) ** 2).sum())}


def cond_means(rows, blocks=None):
    return np.array([(r["E"] if blocks is None else r["E"][blocks]).mean() for r in rows])


def fit_form(rows, terms, y=None):
    return _fit(np.array([phi(r["x"], terms) for r in rows]), cond_means(rows) if y is None else y, terms)


def predict(model, r):
    return float(logistic(phi(r["x"], model["terms"]) @ np.array(model["beta"])))


def fit_par(rows, y=None):
    return _fit(np.array([phi_par(r) for r in rows]), cond_means(rows) if y is None else y, PAR_TERMS)


def predict_par(par, r):
    return float(logistic(phi_par(r) @ np.array(par["beta"])))


def fit_nn(rows):
    X = np.array([absf(r) for r in rows])
    sd = X.std(0, ddof=0)
    sd = np.where(sd > 0, sd, 1.0)
    return {"k": D.K_NN, "sd": sd.tolist(), "train_X": (X / sd).tolist(), "train_y": [float(r["E"].mean()) for r in rows]}


def predict_nn(nn, r):
    """The mean of the k nearest FIT conditions, the squared standardised distance rounded to design.NN_ROUND decimals and
    ties broken by the FIT condition's index (equidistant neighbours are common on the grid)."""
    X, y = np.array(nn["train_X"]), np.array(nn["train_y"])
    d2 = np.round(((X - absf(r) / np.array(nn["sd"])) ** 2).sum(1), D.NN_ROUND)
    order = np.lexsort((np.arange(len(d2)), d2))[: nn["k"]]
    return float(y[order].mean())


def sm001_model():
    return json.loads((LANE / "sm001" / "frozen" / "model.json").read_text())


def predict_sm001(blob, r):
    """SM001's frozen model at the row's SM001 variables (it does not know g)."""
    return float(A1.logistic(A1.phi(S1D.x_vars(r["w"], r["L"], r["lam"], r["m"], r["tau"])) @ np.array(blob["model"]["beta"])))


def lobo(rows, terms):
    """The leave-one-block-out error: refit on 15 FIT blocks, predict the held-out block's condition means; the mean
    absolute error over every held-out value."""
    n = len(rows[0]["blocks"])
    errs = []
    for b in range(n):
        keep = [i for i in range(n) if i != b]
        model = fit_form(rows, terms, cond_means(rows, keep))
        pred = np.array([predict(model, r) for r in rows])
        errs.append(np.abs(cond_means(rows, [b]) - pred))
    return float(np.mean(errs))


def select(rows):
    """The declared rule: the candidate with the smallest LOBO error, unless a smaller candidate is within SELECT_TOL."""
    err = {name: lobo(rows, terms) for name, terms in D.CANDIDATES.items()}
    best = min(err.values())
    chosen = next(name for name in D.CANDIDATES if err[name] <= best + D.SELECT_TOL)
    return chosen, err


def model_blob(rows, fit_reread_manifest_sha=None):
    chosen, err = select(rows)
    model = fit_form(rows, D.CANDIDATES[chosen])
    blob = {"study": D.STUDY, "design_digest": D.digest(), "chosen": chosen, "lobo": err, "model": model,
            "candidates": {name: fit_form(rows, terms) for name, terms in D.CANDIDATES.items()},
            "sensitivity": {name: dict(fit_form(rows, terms), lobo=lobo(rows, terms)) for name, terms in D.SENSITIVITY.items()},
            "parametric": fit_par(rows), "nn": fit_nn(rows),
            "fit_conditions": [[r["unit"], r["L"], r["arm"], r["g"]] for r in rows], "fit_blocks": rows[0]["blocks"],
            "fit_reread_manifest_sha256": fit_reread_manifest_sha,
            "sm001_fit_manifest_sha256": sha(Path(D.FIT_ROOT) / "manifest.json"),
            "sm001_model_sha256": sha(LANE / "sm001" / "frozen" / "model.json"),
            "fit_means": [[r["unit"], r["L"], r["arm"], r["g"], float(r["E"].mean())] for r in rows]}
    blob["model_sha256"] = hashlib.sha256(json.dumps(blob["model"], sort_keys=True).encode()).hexdigest()
    return blob


# ------------------------------------------------------------------------------------------------------------- SDs

def sd_rule(x):
    blk = x.mean(1)
    sd4 = float(blk.std(ddof=1))
    sdc = float(x.ravel().std(ddof=1) / math.sqrt(x.shape[1]))
    return sd4, sdc, max(sd4, sdc)


def model_sd(conds, fitrows, terms, sign=1.0):
    """SD_F: the model's own sampling error of its mean prediction over the conditions conds (the larger of the SD over
    single-block refits and sqrt(n x the jackknife variance) on the n FIT blocks)."""
    n = len(fitrows[0]["blocks"])
    mean_at = lambda bl: float(np.mean([predict(fit_form(fitrows, terms, cond_means(fitrows, bl)), c) for c in conds]))
    single = np.array([mean_at([b]) for b in range(n)])
    jack = np.array([mean_at([i for i in range(n) if i != b]) for b in range(n)])
    sd_single = float(single.std(ddof=1))
    sd_jack = float(math.sqrt((n - 1) * ((jack - jack.mean()) ** 2).sum()))
    return {"sd_F": max(sd_single, sd_jack), "sd_single_F": sd_single, "sd_jack_F": sd_jack}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--fit-root", type=Path, required=True)
    f.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rows = fit_rows(a.fit_root)
    blob = model_blob(rows, sha(a.fit_root / "manifest.json"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(blob, indent=1) + "\n")
    print("chosen", blob["chosen"], "lobo", json.dumps(blob["lobo"]), "R2", round(blob["model"]["r2"], 6),
          "parametric R2", round(blob["parametric"]["r2"], 6))


if __name__ == "__main__":
    main()
