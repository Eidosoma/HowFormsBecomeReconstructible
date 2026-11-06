"""SM006's TEST rows, statements and scoring.

python -m sm006.predict --root STAGE_ROOT --model MODEL_JSON --fit-gain-root FIT_GAIN_ROOT --out DIR
python -m sm006.predict --freeze      (sm006/frozen/predictions.json, at the freeze, on the lead's word)

The rows of a stage: every condition of the six units read by the base readers (g 1, 2, 4: the saved reads of SM003 and
SM004) and at g 1 with the gain x f (f 1/2 and 1/4 everywhere and 1/(2 sqrt 2) on the transfer units from SM006's
rereads; 1/(2 sqrt 2) on the refined units from SM005's), each with its measured erasure size. Every part is linear in
the case values (per case the mean over its conditions; a block's value the mean of its 8 cases; the part the mean over
the blocks). "new" is SM006's frozen model, "h1" SM004's H1. The rule (BE002's; PLAN_SM006.md): on P55 each part at
least 1.68 SD inside its threshold and both halves; SD = sqrt(SD_T^2 + SD_F^2), SD_F over the 16 single-FIT-block refits
and the jackknife of every fitted predictor the part uses; band parts register at their narrowest band, S2 and S7 only
above 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm001 import design as S1D  # noqa: E402
from sm003 import analyze as A3  # noqa: E402
from sm003 import design as D3  # noqa: E402
from sm004 import analyze as A4  # noqa: E402
from sm006 import analyze as A  # noqa: E402
from sm006 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the thresholds, from P55 by the rule (probes/p55b_sm006_margins.py, 18:31Z on 2 November, under the frozen J4): every
# band at its narrowest; S2 (narrowest bound -0.01) and S7 (0.00) do not register (a bound above 0 is required): reported
TH = {"S1": [-0.16, 0.08], "S3": [-0.05, 0.11], "S4": [-0.02, 0.15], "S5": [-0.01, 0.28], "S6": [0.01, 0.17], "S8": [-0.1, 0.02], "S9": [0.0, 0.14], "S10": [-0.08, 0.09], "S11": [-0.05, 0.08]}
GE = ("S2", "S7")
F2, F2R2, F4 = 0.5, D.F_GRID[1], 0.25


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _check(root):
    M = json.loads((Path(root) / "manifest.json").read_text())
    bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(Path(root) / f["path"]) != f["sha256"]]
    if bad or not M.get("bridge_all_equal", True):
        raise ValueError(f"{root}: sha256 or a bridge fails {bad[:3]}")
    return M


def test_rows(root, check=True):
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    if check:
        _check(root)
    tasks = sorted(tuple(k.rsplit("/", 2)) for k in M["tasks"])
    blocks = sorted({(s, int(b)) for s, _, b in tasks})
    src = {}
    for s, _b in blocks:
        if s not in src:
            src[s] = _check(D.SOURCES[s][0]) if check else None
            if check:
                _check(D.SM005_ROOTS[s])
    rows = []
    for u in D.UNITS:
        cfg = S1D.UNIT[u]
        Zs = {(s, b): np.load(Path(D.SOURCES[s][0]) / "shards" / u / f"{b}.npz") for s, b in blocks}
        Z6 = {(s, b): np.load(root / "shards" / s.replace("/", "_") / u / f"{b}.npz") for s, b in blocks}
        Z5 = ({(s, b): np.load(Path(D.SM005_ROOTS[s]) / "shards" / s.replace("/", "_") / u / f"{b}.npz") for s, b in blocks}
              if cfg["kind"] == "refine" else None)
        readers = [(g, 1.0, lambda z6, zs, z5, L, ai, key=k: (zs[f"L{L}/{key}"][-1, ai] if key == "u/in" else zs[f"L{L}/{key}"][ai]))
                   for g, k in ((1, "u/in"), (2, "cg/in"), (4, "g4/in")) if g in D3.unit_grains(u)]
        for f in (F2, F2R2, F4):
            fn = D.F_NAME[f]
            if f == F2R2 and cfg["kind"] == "refine":
                readers.append((1, f, lambda z6, zs, z5, L, ai: z5[f"L{L}/E/in"][ai]))
            else:
                readers.append((1, f, lambda z6, zs, z5, L, ai, fn=fn: z6[f"L{L}/g1/{fn}/in"][ai]))
        for L in cfg["sizes"]:
            for ai, a in enumerate(S1D.unit_arms(u)):
                for g, f, get in readers:
                    rows.append({"unit": u, "kind": cfg["kind"], "w": cfg["w"], "L": L, "arm": a["name"], "c": a["c"],
                                 "lam": a["lam_rest"], "m": a["m"], "tau": a["tau_c"], "g": g, "f": f, "side": 64,
                                 "eps": D.eps(64, g, f), "blocks": [list(x) for x in blocks],
                                 "E": np.array([get(Z6[x], Zs[x], Z5[x] if Z5 else None, L, ai) for x in blocks]),
                                 "x": A3.x_vars(cfg["w"], L, a["lam_rest"], a["m"], a["tau_c"], g)})
    by = {(r["kind"], r["w"], r["L"], r["c"], r["m"], r["tau"], r["g"], r["f"]): r for r in rows}
    for r in rows:
        r["base"] = by.get((r["kind"], r["w"], r["L"], r["c"], r["m"], r["tau"], 1, 1.0)) if r["f"] != 1.0 else None
        if r["kind"] == "refine":
            r["twin"] = by.get(("transfer", r["w"] // 2, r["L"] // 2, r["c"] / 2, r["m"], r["tau"], r["g"], r["f"]))
            r["twin_half"] = (by.get(("transfer", r["w"] // 2, r["L"] // 2, r["c"] / 2, r["m"], r["tau"], r["g"] // 2, 1.0))
                              if r["g"] > 1 and r["f"] == 1.0 else None)
    return rows


def sel(rows, kind=None, g=None, f=None, m=None, need=None):
    kinds = (kind,) if isinstance(kind, str) else kind
    fs = (f,) if isinstance(f, float) else f
    gs = (g,) if isinstance(g, int) else g
    out = [r for r in rows if (kinds is None or r["kind"] in kinds) and (gs is None or r["g"] in gs)
           and (fs is None or r["f"] in fs) and (m is None or r["m"] == m)]
    return [r for r in out if need is None or r.get(need) is not None]


def _fns():
    err = lambda key: (lambda r, P: r["E"] - P[key][id(r)])
    loss = lambda key, tw="twin": (lambda r, P: (r["E"] - r[tw]["E"]) - (P[key][id(r)] - P[key][id(r[tw])]))
    rec = lambda key: (lambda r, P: (r["E"] - r["base"]["E"]) - (P[key][id(r)] - P[key][id(r["base"])]))
    aerr = lambda k1, k2: (lambda r, P: np.abs(r["E"] - P[k1][id(r)]) - np.abs(r["E"] - P[k2][id(r)]))
    aloss = lambda k1, k2: (lambda r, P: np.abs(loss(k1)(r, P)) - np.abs(loss(k2)(r, P)))
    return err, loss, rec, aerr, aloss


BOTH, REF, TRA = ("transfer", "refine"), "refine", "transfer"


def parts(rows):
    err, loss, rec, aerr, aloss = _fns()
    return [
        ("S1", "the late loss from FIT alone: refinement, base g 1, late: (E - E twin) - (the model - the model at the twin)",
         sel(rows, REF, 1, 1.0, 2, "twin"), loss("new"), ("new",), "in"),
        ("S2", "the late loss against H1: |H1's loss error| - |the model's loss error|", sel(rows, REF, 1, 1.0, 2, "twin"),
         aloss("h1", "new"), ("new", "h1"), "ge"),
        ("S3", "E(4), blind: every unit, g 1, gain x 1/2: E - the model", sel(rows, BOTH, 1, F2), err("new"), ("new",), "in"),
        ("S4", "E(8), blind: every unit, g 1, gain x 1/4: E - the model", sel(rows, BOTH, 1, F4), err("new"), ("new",), "in"),
        ("S5", "the erasure's recovery at eps 8, blind: refinement, late: (E(8) - E base) - (the model at 8 - at the base)",
         sel(rows, REF, 1, F4, 2, "base"), rec("new"), ("new",), "in"),
        ("S6", "the same at eps 4", sel(rows, REF, 1, F2, 2, "base"), rec("new"), ("new",), "in"),
        ("S7", "closer than H1 at the blind targets: every unit, g 1, eps 4 and 8: |E - H1| - |E - the model|",
         sel(rows, BOTH, 1, (F2, F4)), aerr("h1", "new"), ("new", "h1"), "ge"),
        ("S8", "the g-2 offset kept: refinement, g 2: E - the model", sel(rows, REF, 2, 1.0), err("new"), ("new",), "in"),
        ("S9", "the g-4 shortfall kept: refinement, g 4: E - the model", sel(rows, REF, 4, 1.0), err("new"), ("new",), "in"),
        ("S10", "the prompt loss kept: refinement, base g 1, prompt: as S1", sel(rows, REF, 1, 1.0, 0, "twin"), loss("new"),
         ("new",), "in"),
        ("S11", "the larger sheet kept: transfer, base g 1, 2 and 4: E - the model", sel(rows, TRA, (1, 2, 4), 1.0),
         err("new"), ("new",), "in"),
    ]


def reported_parts(rows):
    err, loss, rec, aerr, aloss = _fns()
    return [
        ("R1", "E(6), refinement (not blind): E - the model", sel(rows, REF, 1, F2R2), err("new"), ("new",)),
        ("R2", "E(6), transfer (blind): E - the model", sel(rows, TRA, 1, F2R2), err("new"), ("new",)),
        ("R3", "the erasure's recovery at eps 6 (SM005's V_E): refinement, late", sel(rows, REF, 1, F2R2, 2, "base"),
         rec("new"), ("new",)),
        ("R4", "the matched-reader gain at g 2: (E - E twin at g/2) - (the model - at the twin at g/2)",
         sel(rows, REF, 2, 1.0, need="twin_half"), loss("new", "twin_half"), ("new",)),
        ("R5", "the same at g 4", sel(rows, REF, 4, 1.0, need="twin_half"), loss("new", "twin_half"), ("new",)),
        ("R6", "H1 on S1: the late loss", sel(rows, REF, 1, 1.0, 2, "twin"), loss("h1"), ("h1",)),
        ("R7", "H1 on S3: E(4)", sel(rows, BOTH, 1, F2), err("h1"), ("h1",)),
        ("R8", "H1 on S4: E(8)", sel(rows, BOTH, 1, F4), err("h1"), ("h1",)),
        ("R9", "H1 on S5: the recovery at eps 8", sel(rows, REF, 1, F4, 2, "base"), rec("h1"), ("h1",)),
        ("R10", "the observed late loss, base g 1: E - E twin", sel(rows, REF, 1, 1.0, 2, "twin"),
         lambda r, P: r["E"] - r["twin"]["E"], ()),
        ("R11", "the observed recovery at eps 8: E(8) - E base, refinement, late", sel(rows, REF, 1, F4, 2, "base"),
         lambda r, P: r["E"] - r["base"]["E"], ()),
        # H1 beside every part (the lead's ruling after P55's values, before the freeze): R6-R9 above, and the rest
        ("R12", "H1 on S6: the recovery at eps 4", sel(rows, REF, 1, F2, 2, "base"), rec("h1"), ("h1",)),
        ("R13", "H1 on S8: g 2, refinement", sel(rows, REF, 2, 1.0), err("h1"), ("h1",)),
        ("R14", "H1 on S9: g 4, refinement", sel(rows, REF, 4, 1.0), err("h1"), ("h1",)),
        ("R15", "H1 on S10: the prompt loss", sel(rows, REF, 1, 1.0, 0, "twin"), loss("h1"), ("h1",)),
        ("R16", "H1 on S11: the larger sheet", sel(rows, TRA, (1, 2, 4), 1.0), err("h1"), ("h1",)),
        ("R17", "S2's first term: |H1's late-loss error|", sel(rows, REF, 1, 1.0, 2, "twin"),
         lambda r, P: np.abs(loss("h1")(r, P)), ("h1",)),
        ("R18", "S2's second term: |the model's late-loss error|", sel(rows, REF, 1, 1.0, 2, "twin"),
         lambda r, P: np.abs(loss("new")(r, P)), ("new",)),
        ("R19", "S7's first term: |E - H1| at the blind targets", sel(rows, BOTH, 1, (F2, F4)),
         lambda r, P: np.abs(err("h1")(r, P)), ("h1",)),
        ("R20", "S7's second term: |E - the model| at the blind targets", sel(rows, BOTH, 1, (F2, F4)),
         lambda r, P: np.abs(err("new")(r, P)), ("new",)),
    ]


# H1's value beside each part (S2 and S7 compare the two: their first terms, |H1's error|)
H1_BESIDE = {"S1": "R6", "S2": "R17", "S3": "R7", "S4": "R8", "S5": "R9", "S6": "R12", "S7": "R19", "S8": "R13", "S9": "R14",
             "S10": "R15", "S11": "R16"}
SENSITIVITY_U = LANE / "sm006" / "frozen" / "sensitivity_U.json"


def sensitivity_values(rows, P, su):
    """The reported sensitivity U's value on every part, numbers only (no SD, no verdict): the part with U in the model's
    place. Never computed on P55 (the lead's ruling)."""
    PU = dict(P, new={id(r): A.predict(su["model"], r) for r in rows})
    return [{"id": pid, "value": float(case_values(rr, f, PU).mean())} for pid, _w, rr, f, _u, _k in parts(rows)]


def frozen_h1():
    return json.loads((LANE / "sm004" / "frozen" / "model.json").read_text())["model"]


def predictions(rows, blob):
    return {"new": {id(r): A.predict(blob["model"], r) for r in rows},
            "h1": {id(r): A4.predict(frozen_h1(), r) for r in rows}}


def refit_predictions(rows, blob, fitrows):
    h1rows = A4.fit_rows(A.FIT_G4_ROOT)
    h1t = frozen_h1()["terms"]
    n = len(fitrows[0]["blocks"])
    sets = {"single": [[b] for b in range(n)], "jack": [[i for i in range(n) if i != b] for b in range(n)]}
    out = {}
    for name, subsets in sets.items():
        out[name] = []
        for S in subsets:
            mn = A.fit_form(fitrows, blob["model"]["terms"], A.cond_means(fitrows, S))
            mh = A4.fit_form(h1rows, h1t, A.cond_means(h1rows, S))
            out[name].append({"new": {id(r): A.predict(mn, r) for r in rows}, "h1": {id(r): A4.predict(mh, r) for r in rows}})
    return out


def case_values(rr, f, P):
    if not rr:
        raise ValueError("a part with no conditions")
    return np.mean([f(r, P) for r in rr], axis=0)


def _value(rr, f, uses, P, RP):
    x = case_values(rr, f, P)
    nb = x.shape[0]
    sd4, sdc, sdT = A3.sd_rule(x)
    sdF = {"sd_F": 0.0}
    if uses and RP is not None:
        val = lambda Q: float(case_values(rr, f, dict(P, **{k: Q[k] for k in uses})).mean())
        s = np.array([val(Q) for Q in RP["single"]])
        j = np.array([val(Q) for Q in RP["jack"]])
        sdF = {"sd_F": max(float(s.std(ddof=1)), float(math.sqrt((len(j) - 1) * ((j - j.mean()) ** 2).sum()))),
               "sd_single_F": float(s.std(ddof=1)), "sd_jack_F": float(math.sqrt((len(j) - 1) * ((j - j.mean()) ** 2).sum()))}
    sd = math.sqrt(sdT ** 2 + sdF["sd_F"] ** 2)
    v = float(x.mean())
    hw = stats.t.ppf(0.975, nb - 1) * sd / math.sqrt(nb)
    return {"value": v, "ci95": [v - hw, v + hw], "sd": sd, "sd4_T": sd4, "sdc_T": sdc, "sd_T": sdT, **sdF,
            "halves": [float(x[: nb // 2].mean()), float(x[nb // 2:].mean())], "n_conditions": len(rr),
            "blocks": x.mean(1).tolist()}


def narrowest(v, sd, halves, kind, step=D.STEP):
    need = K_RULE * sd                                   # sm003.predict.narrowest's arithmetic
    if kind == "in":
        return [round(math.floor((min(v - need, *halves)) / step) * step, 2),
                round(math.ceil((max(v + need, *halves)) / step) * step, 2)]
    return round(math.floor((min(v - need, *halves)) / step) * step, 2)


def score(rows, P, RP, th=None):
    th = TH if th is None else th
    out = []
    for pid, words, rr, f, uses, kind in parts(rows):
        rec = _value(rr, f, uses, P, RP)
        fin = all(math.isfinite(z) for z in (rec["value"], rec["sd"], *rec["halves"]))
        nar = narrowest(rec["value"], rec["sd"], rec["halves"], kind) if fin else None
        rec = {"id": pid, "part": words, "kind": kind, "uses": list(uses), **rec, "narrowest": nar,
               "registers_at_narrowest": None if nar is None else (kind == "in" or nar > 0)}
        t = th.get(pid)
        if t is not None:
            v, sd = rec["value"], rec["sd"]
            if kind == "in":
                rec.update(threshold=list(t), holds=t[0] <= v <= t[1], margins=[(v - t[0]) / sd, (t[1] - v) / sd])
            else:
                rec.update(threshold=t, holds=v >= t, margins=[(v - t) / sd])
        out.append(rec)
    return out


def score_reported(rows, P, RP):
    return [{"id": rid, "part": words, **_value(rr, f, uses, P, RP)} for rid, words, rr, f, uses in reported_parts(rows)]


def verdicts(scored):
    return {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p}


def freeze():
    import time
    if not TH:
        sys.exit("no thresholds: P55's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": p, "part": w, "kind": k, "threshold": TH[p]} for p, w, _r, _f, _u, k in parts([]) if p in TH],
           "candidates_reported": [{"id": p, "part": w} for p, w, _r, _f, _u, _k in parts([]) if p not in TH],
           "reported": [{"id": r, "part": w} for r, w, _rr, _f, _u in reported_parts([])],
           "predict_sha256": sha(Path(__file__))}
    out = LANE / "sm006" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--fit-gain-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rows = test_rows(a.root)
    blob = json.loads(a.model.read_text())
    P = predictions(rows, blob)
    RP = refit_predictions(rows, blob, A.fit_rows(a.fit_gain_root))
    scored = score(rows, P, RP)
    rep = score_reported(rows, P, RP)
    stage = json.loads((a.root / "manifest.json").read_text())["stage"]
    su = json.loads(SENSITIVITY_U.read_text()) if SENSITIVITY_U.exists() and stage != "probe" else None
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "predictions_scored.json").write_text(json.dumps(
        {"study": D.STUDY, "stage": stage, "root": str(a.root),
         "model_sha256": blob["model_sha256"], "chosen": blob["chosen"], "parts": scored, "verdicts": verdicts(scored),
         "reported": rep, "h1_beside": H1_BESIDE,
         "sensitivity_U": None if su is None else {"model_sha256": su["model_sha256"], "excluded": su["excluded"],
                                                   "values": sensitivity_values(rows, P, su)}}, indent=1) + "\n")
    for p in scored:
        print(f"{p['id']:4s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} (T {p['sd_T']:.4f}, "
              f"F {p['sd_F']:.4f}) halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f} narrowest {p['narrowest']}"
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
