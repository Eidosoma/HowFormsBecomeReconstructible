"""SM005's statements and their scoring.

python -m sm005.predict --root STAGE_ROOT --out DIR [--margins]
python -m sm005.predict --freeze        (sm005/frozen/predictions.json, at the freeze, on the lead's word)

Per refined condition read at full resolution, per case: F = E_cg - E_base (the fully scaled reader's recovery) and
V_X = E_X - E_base for the variants C, E, B. Every part is linear in the case values: per case the mean over its
conditions, a block's value the mean of its 8 cases, the part the mean over the blocks. The rule (BE002's; PLAN_SM005.md):
on P54 (4 blocks) each part sits at least 3 sqrt(1/4 + 1/16) = 1.68 SD inside its threshold and passes in both halves
(900476-77, 900478-79); SD the max rule on the case values (no fitted model, no SD_F); thresholds the narrowest round
values (0.01 steps) the rule allows; every band part L1-L5, P1-P4 registers at its narrowest band. Amendment 1 (the
lead's ruling, before P54): K1 (B - E, late), K1p (B - E, prompt) and K2 (F - (V_C + V_B), late) register only if P54
supports them: their narrowest band's half-width at most SUPPORT x |P54's L4| (informative against the full recovery);
otherwise they are reported.
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
from sm005 import analyze as A  # noqa: E402
from sm005 import design as D  # noqa: E402

K_RULE = D.K_RULE
# the thresholds: the narrowest the rule allows on P54 (probes/results/p54b_sm005_margins.txt, read 2 November about
# 15:36Z), proposed for the lead's review. K1 (B - E, late) is not supported by P54 (its band's half-width 0.15 against
# 0.5 x |L4| = 0.115) and is reported; K1p and K2 are supported and register (Amendment 1).
TH = {"L1": (0.02, 0.10), "L2": (0.14, 0.32), "L3": (-0.12, 0.24), "L4": (0.13, 0.33), "L5": (-0.04, 0.28),
      "P1": (0.00, 0.07), "P2": (0.05, 0.22), "P3": (-0.10, 0.17), "P4": (0.05, 0.22), "K1p": (-0.20, -0.01),
      "K2": (0.00, 0.21)}
BOOT, BOOT_SEED = 10000, 20261102


def sel(rows, m=None):
    return [r for r in rows if m is None or r["m"] == m]


def V(x):
    return lambda r: r["E"][x] - r["E"]["base"]


F = lambda r: r["E"]["cg"] - r["E"]["base"]
ADD = lambda r: (r["E"]["C"] - r["E"]["base"]) + (r["E"]["E"] - r["E"]["base"]) + (r["E"]["B"] - r["E"]["base"]) - F(r)
# Amendment 1 (the lead's ruling, 2 November about 15:16Z, before P54): B carries the record's own erasure, so
BE = lambda r: r["E"]["B"] - r["E"]["E"]                              # B - E: the bond grain beyond its erasure
ADD2 = lambda r: F(r) - (r["E"]["C"] - r["E"]["base"]) - (r["E"]["B"] - r["E"]["base"])   # the overlap removed
SUPPORT = 0.5                    # K1, K1p, K2 register only if their narrowest band's half-width <= SUPPORT x |P54's L4|
AMENDED = ("K1", "K1p", "K2")


def parts(rows):
    late, prompt = sel(rows, D.LATE), sel(rows, D.PROMPT)
    return [("L1", "late (m 2): V_C = E_C - E_base, the coupling length's recovery", late, V("C")),
            ("L2", "late: V_E = E_E - E_base, the erasure size's recovery", late, V("E")),
            ("L3", "late: V_B = E_B - E_base, the bond grain's recovery", late, V("B")),
            ("L4", "late: F = E_cg - E_base, the fully scaled reader's recovery", late, F),
            ("L5", "late: A = V_C + V_E + V_B - F, the additivity", late, ADD),
            ("P1", "prompt (m 0): V_C", prompt, V("C")),
            ("P2", "prompt: V_E", prompt, V("E")),
            ("P3", "prompt: V_B", prompt, V("B")),
            ("P4", "prompt: F", prompt, F),
            ("K1", "late: B - E = E_B - E_E, the bond grain's recovery beyond the erasure it brings", late, BE),
            ("K1p", "prompt: B - E, the contrast", prompt, BE),
            ("K2", "late: F - (V_C + V_B), the additivity with the overlap removed (B already carries the erasure)", late, ADD2)]


def case_values(rr, f):
    if not rr:
        raise ValueError("a part with no conditions")
    return np.mean([f(r) for r in rr], axis=0)


def value(x):
    nb = x.shape[0]
    sd4, sdc, sd = A3.sd_rule(x)
    v = float(x.mean())
    hw = stats.t.ppf(0.975, nb - 1) * sd / math.sqrt(nb)
    return {"value": v, "ci95": [v - hw, v + hw], "sd": sd, "sd4": sd4, "sdc": sdc,
            "halves": [float(x[: nb // 2].mean()), float(x[nb // 2:].mean())], "blocks": x.mean(1).tolist()}


def narrowest(v, sd, halves, step=D.STEP):
    """sm003.predict.narrowest's arithmetic for a band."""
    need = K_RULE * sd
    lo = math.floor((min(v - need, *halves)) / step) * step
    hi = math.ceil((max(v + need, *halves)) / step) * step
    return [round(lo, 2), round(hi, 2)]


def score(rows, th=None):
    th = TH if th is None else th
    out = []
    for pid, words, rr, f in parts(rows):
        x = case_values(rr, f)
        rec = {"id": pid, "part": words, "n_conditions": len(rr), **value(x)}
        fin = all(math.isfinite(z) for z in (rec["value"], rec["sd"], *rec["halves"]))
        rec["narrowest"] = narrowest(rec["value"], rec["sd"], rec["halves"]) if fin else None
        if pid in AMENDED:
            l4 = next(p for p in out if p["id"] == "L4")
            rec["supported"] = bool(fin and (rec["narrowest"][1] - rec["narrowest"][0]) / 2 <= SUPPORT * abs(l4["value"]))
        t = th.get(pid)
        if t is not None:
            lo, hi = t
            v, sd = rec["value"], rec["sd"]
            rec.update(threshold=list(t), holds=lo <= v <= hi, margins=[(v - lo) / sd, (hi - v) / sd],
                       rule_ok=min((v - lo) / sd, (hi - v) / sd) >= K_RULE and all(lo <= h <= hi for h in rec["halves"]))
        out.append(rec)
    return out


def shares(rows, m):
    """V_X / F with a whole-block bootstrap (BOOT resamples, a declared seed), read as a ratio only if F's 95% lower bound
    (its t interval) is at least half F (HS001's ratio rule)."""
    rr = sel(rows, m)
    f = case_values(rr, F).mean(1)
    fv = value(case_values(rr, F))
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, len(f), size=(BOOT, len(f)))
    out = {"F": fv["value"], "F_ci95": fv["ci95"], "ratio_read": bool(fv["ci95"][0] >= 0.5 * fv["value"] > 0)}
    for x in D.VARIANTS:
        v = case_values(rr, V(x)).mean(1)
        boot = v[idx].mean(1) / f[idx].mean(1)
        out[x] = {"share": float(v.mean() / f.mean()), "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]}
    return out


def reported(rows):
    late, prompt = sel(rows, D.LATE), sel(rows, D.PROMPT)
    rep = {"shares_late": shares(rows, D.LATE), "shares_prompt": shares(rows, D.PROMPT),
           "additivity_prompt": value(case_values(prompt, ADD)),
           "late_less_prompt": {x: value(case_values(late, V(x)) - case_values(prompt, V(x))) for x in D.VARIANTS},
           "levels": {sig: {rd: {"E": float(np.mean([r["E"][rd].mean() for r in rr])),
                                 "gen": float(np.mean([r["gen"][rd].mean() for r in rr])),
                                 "phase": float(np.mean([(r["E"][rd] - r["gen"][rd]).mean() for r in rr]))}
                            for rd in D.READERS} for sig, rr in (("late", late), ("prompt", prompt))},
           "by_unit": {}, "by_size": {}}
    for u in D.REFINE:
        rr = [r for r in late if r["unit"] == u]
        rep["by_unit"][u] = {pid: value(case_values(rr, f))["value"] for pid, _w, _rr, f in parts(rows)[:5]}
    for L in sorted({r["L"] for r in rows}):
        rr = [r for r in late if r["L"] == L]
        rep["by_size"][str(L)] = {pid: value(case_values(rr, f))["value"] for pid, _w, _rr, f in parts(rows)[:5]}
    return rep


def verdicts(scored):
    return {p["id"]: ("HOLDS" if p["holds"] else "FAILS") for p in scored if "holds" in p}


def freeze():
    import hashlib
    import time
    if not TH:
        sys.exit("no thresholds: P54's margins come first")
    rec = {"study": D.STUDY, "design_digest": D.digest(), "k_rule": K_RULE, "thresholds": TH,
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "registered": [{"id": pid, "part": words, "kind": "band", "threshold": TH[pid]} for pid, words, _rr, _f in parts([])
                          if pid in TH],
           "candidates_reported": [{"id": pid, "part": words, "why": "not supported by P54 (Amendment 1's condition)"}
                                   for pid, words, _rr, _f in parts([]) if pid not in TH],
           "reported": ["shares late and prompt (whole-block bootstrap, HS001's ratio rule)", "the prompt additivity",
                        "late less prompt per variant", "each reader's E, generic recovery and phase",
                        "L1-L5 by unit and by patch size", "the halves by source (SM003's 16, SM004's 16)"],
           "boot": BOOT, "boot_seed": BOOT_SEED, "predict_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out = LANE / "sm005" / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out, len(rec["registered"]), "registered parts")


def main():
    if "--freeze" in sys.argv:
        return freeze()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--margins", action="store_true")
    a = ap.parse_args()
    rows = A.rows(a.root)
    scored = score(rows)
    rep = reported(rows)
    a.out.mkdir(parents=True, exist_ok=True)
    stage = json.loads((a.root / "manifest.json").read_text())["stage"]
    (a.out / "predictions_scored.json").write_text(json.dumps({"study": D.STUDY, "stage": stage, "root": str(a.root),
                                                               "parts": scored, "verdicts": verdicts(scored),
                                                               "reported": rep}, indent=1) + "\n")
    for p in scored:
        print(f"{p['id']:3s} {p['part'][:62]:62s} {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] SD {p['sd']:.4f} "
              f"halves {p['halves'][0]:+.4f} {p['halves'][1]:+.4f}" + (f" narrowest {p['narrowest']}" if a.margins else "")
              + (f" {'HOLDS' if p['holds'] else 'FAILS'}" if "holds" in p else ""))


if __name__ == "__main__":
    main()
