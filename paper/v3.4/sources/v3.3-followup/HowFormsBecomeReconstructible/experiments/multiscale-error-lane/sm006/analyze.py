"""SM006's FIT rows with the erasure size, the model family's selection and the model blob.

  the variables  SM004's (a, b, c, d, e = log2 L/g, G = log2 g) and the reader's measured erasure size eps (design.EPS,
                 by side, grain and gain factor): z = log2(eps / g), E = e_eps = log2(L / eps)
  FIT rows       SM004's 864 (g 1, 2, 4 at the base gain: sm004.analyze.fit_rows) and the 972 gain variants (g 1 and 2,
                 m 0 and 2; sm006.fitread), 1,836 condition means over the 16 FIT blocks
  the rule       admissible candidates (full rank, condition number <= design.COND_MAX); the smallest leave-one-block-out
                 error; among those within design.SELECT_TOL of it the fewest terms, then the smaller error

python -m sm006.analyze fit --fit-gain-root RUN_ROOT/fit_gain --out FILE
python -m sm006.analyze sensitivity-u --fit-gain-root RUN_ROOT/fit_gain --model sm006/frozen/model.json --out FILE
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
from sm004 import analyze as A4  # noqa: E402
from sm004 import design as D4  # noqa: E402
from sm006 import design as D  # noqa: E402
from sm006 import fitread as FR  # noqa: E402

logistic = A3.logistic
cond_means = A3.cond_means
FIT_G4_ROOT = f"{D.RUNS}/sm004/fit_g4"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit_rows(fit_gain_root, check=True):
    rows = A4.fit_rows(FIT_G4_ROOT, check=check)
    for r in rows:
        r.update(f=1.0, side=32, eps=D.eps(32, r["g"], 1.0))
    root = Path(fit_gain_root)
    M = json.loads((root / "manifest.json").read_text())
    if check:
        if M["sm001_fit_manifest_sha256"] != sha(Path(D4.FIT_ROOT) / "manifest.json") or not M["bridge_all_equal"]:
            raise ValueError("the gain rereads' manifest or bridge fails")
        for key, t in M["tasks"].items():
            if sha(root / t["file"]["path"]) != t["file"]["sha256"]:
                raise ValueError(f"FIT gain reread {key}: sha256 differs")
    FM = json.loads((Path(D4.FIT_ROOT) / "manifest.json").read_text())
    for u in D4.FIT_UNITS:
        blocks = sorted(b for uu, b in FM["pairs"] if uu == u)
        cfg = S1D.UNIT[u]
        arms = S1D.unit_arms(u)
        idx = FR.arm_index(u)
        Z = {b: np.load(root / "shards" / u / f"{b}.npz") for b in blocks}
        Zs = {b: np.load(Path(D4.FIT_ROOT) / "shards" / u / f"{b}.npz") for b in blocks}
        for L in cfg["sizes"]:
            for j, ai in enumerate(idx):
                a = arms[ai]
                for g in D.FIT_GRAINS_VAR:
                    for f in D.F_GRID:
                        fn = D.F_NAME[f]
                        rows.append({"stage": "fit", "unit": u, "kind": "fit", "w": cfg["w"], "L": L, "arm": a["name"],
                                     "c": a["c"], "lam": a["lam_rest"], "m": a["m"], "tau": a["tau_c"], "g": g, "f": f,
                                     "side": 32, "eps": D.eps(32, g, f), "scale": 1, "blocks": blocks,
                                     "E": np.array([Z[b][f"L{L}/g{g}/{fn}/in"][j] for b in blocks]),
                                     "r_in": np.array([Zs[b][f"L{L}/r_in"][A3.READ, ai] for b in blocks]),
                                     "x": A3.x_vars(cfg["w"], L, a["lam_rest"], a["m"], a["tau_c"], g)})
    return rows


def gvars(r):
    v = A4.gvars(r)
    v.update(z=math.log2(r["eps"] / r["g"]), E=math.log2(r["L"] / r["eps"]))
    return v


def phi(r, terms):
    v = gvars(r)
    return np.array([A4._col(v, t) for t in terms])


def fit_form(rows, terms, y=None):
    return A3._fit(np.array([phi(r, terms) for r in rows]), cond_means(rows) if y is None else y, terms)


def predict(model, r):
    return float(logistic(phi(r, model["terms"]) @ np.array(model["beta"])))


def identification(rows, terms):
    X = np.array([phi(r, terms) for r in rows])
    Z = X.copy()
    Z[:, 1:] = (Z[:, 1:] - Z[:, 1:].mean(0)) / Z[:, 1:].std(0)
    s = np.linalg.svd(Z, compute_uv=False)
    rank = int(np.linalg.matrix_rank(Z, tol=1e-10 * s[0]))
    return {"terms": len(terms), "rank": rank, "cond": float(s[0] / s[-1]),
            "admissible": bool(rank == len(terms) and s[0] / s[-1] <= D.COND_MAX)}


def lobo(rows, terms):
    n = len(rows[0]["blocks"])
    errs = []
    for b in range(n):
        model = fit_form(rows, terms, cond_means(rows, [i for i in range(n) if i != b]))
        errs.append(np.abs(cond_means(rows, [b]) - np.array([predict(model, r) for r in rows])))
    return float(np.mean(errs))


def select(rows):
    ident = {name: identification(rows, terms) for name, terms in D.CANDIDATES.items()}
    err = {name: lobo(rows, terms) for name, terms in D.CANDIDATES.items() if ident[name]["admissible"]}
    best = min(err.values())
    near = [n for n in err if err[n] <= best + D.SELECT_TOL]
    chosen = min(near, key=lambda n: (len(D.CANDIDATES[n]), err[n]))
    return chosen, err, ident


def model_blob(rows, fit_gain_root):
    chosen, err, ident = select(rows)
    model = fit_form(rows, D.CANDIDATES[chosen])
    blob = {"study": D.STUDY, "design_digest": D.digest(), "chosen": chosen, "lobo": err, "identification": ident,
            "model": model, "candidates": {n: fit_form(rows, t) for n, t in D.CANDIDATES.items()},
            "fit_bias": {f"g{g}/{D.F_NAME[f]}": float(np.mean([r["E"].mean() - predict(model, r) for r in rows
                                                               if r["g"] == g and r["f"] == f]))
                         for g in (1, 2, 4) for f in (1.0,) + D.F_GRID if any(r["g"] == g and r["f"] == f for r in rows)},
            "n_fit": len(rows), "fit_blocks": rows[0]["blocks"],
            "fit_gain_manifest_sha256": sha(Path(fit_gain_root) / "manifest.json"),
            "fit_g4_manifest_sha256": sha(Path(FIT_G4_ROOT) / "manifest.json"),
            "fit12_manifest_sha256": sha(Path(D4.FIT12_ROOT) / "manifest.json"),
            "sm004_model_sha256": sha(LANE / "sm004" / "frozen" / "model.json"), "eps": D.EPS}
    blob["model_sha256"] = hashlib.sha256(json.dumps(blob["model"], sort_keys=True).encode()).hexdigest()
    return blob


# the FIT readers whose erasure size is censored at the largest island tested (design.EPS at side 32: g 4, and g 2 at gain
# x 1/4); the reported sensitivity U drops their means
U_CENSORED = ("32/4/f1", "32/2/f4")


def sensitivity_u(rows, blob):
    """The reported sensitivity U (the lead's ruling after P55's values, before the freeze; never computed on P55): the frozen
    model's terms refitted on the FIT means whose erasure size is not censored (dropping g 4 and g 2 x 1/4 at side 32)."""
    keep = [r for r in rows if f"{r['side']}/{r['g']}/{D.F_NAME[r['f']]}" not in U_CENSORED]
    fit = fit_form(keep, blob["model"]["terms"])
    model = {"terms": fit["terms"], "beta": fit["beta"]}
    return {"name": "U", "model": model,
            "excluded": {"readers": list(U_CENSORED), "means": len(rows) - len(keep), "kept": len(keep)},
            "model_sha256": hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest(),
            "fit": {"n": fit["n"], "rss": fit["rss"], "r2": fit["r2"]}, "of_model_sha256": blob["model_sha256"],
            "design_digest": D.digest()}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--fit-gain-root", type=Path, required=True)
    f.add_argument("--out", type=Path, required=True)
    u = sub.add_parser("sensitivity-u")
    u.add_argument("--fit-gain-root", type=Path, required=True)
    u.add_argument("--model", type=Path, required=True)
    u.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rows = fit_rows(a.fit_gain_root)
    if a.cmd == "sensitivity-u":
        su = sensitivity_u(rows, json.loads(a.model.read_text()))
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(su, indent=1) + "\n")
        print("sensitivity U:", su["excluded"], "model_sha256", su["model_sha256"][:16])
        return
    blob = model_blob(rows, a.fit_gain_root)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(blob, indent=1) + "\n")
    print("chosen", blob["chosen"], "lobo", json.dumps({k: round(v, 6) for k, v in blob["lobo"].items()}), "R2",
          round(blob["model"]["r2"], 6), "n", blob["n_fit"])


if __name__ == "__main__":
    main()
