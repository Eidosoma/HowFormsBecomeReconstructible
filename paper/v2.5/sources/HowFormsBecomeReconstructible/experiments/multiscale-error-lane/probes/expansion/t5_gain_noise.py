"""T5: where does the setpoint's value peak, and does the native gain put it there? ENGINEERING_PROBE_NOT_EVIDENCE.

ME002 panel C: the setpoint's value (hold - none, sham) is non-monotone in noise, peaking at sigma 0.3 for F0 and
lower for S4, at the native gain 0.2. Here the same acquisition as T2 (blocks 900843-900844, 16 cases) for F0 and
S4 at sigma 0.1 ... 0.6, conserved body, gains 0, 0.05, 0.2, 0.8 reading the held record; 2000 updates.
Value(g) = sign agreement with gain g minus with gain 0.
"""
from __future__ import annotations

from dataclasses import replace
import time

import numpy as np

import xcommon as X
from xcommon import NATIVE

from br001 import design as D
from me002.families import templates
from mse.assay import Noise, birth, enrol, theta
from mse.engine import ROUTES, Route, State, run

from t2_bodies import run_arms, scores

BLOCKS = list(X.BLOCKS[11:13])
TEMPL = {f: templates(f, "mse-me002", D.AMPLITUDE) for f in ("F0", "S4")}


def acquire_t(cases, p, fam):
    T = TEMPL[fam][[c.message for c in cases]]
    th = theta(X.TAG, cases, p, per_tissue=D.PER_TISSUE_THETA)
    V = birth(X.TAG, cases, "birth")
    s = State(V, V.copy(), V.copy(), np.zeros_like(V))
    s = run(s, th, Noise(X.TAG, cases, "settle"), Route(capture=None), D.SETTLE, p)
    s = run(s, th, Noise(X.TAG, cases, "teach"), Route(capture=None), D.TEACH, p, imposed=T)
    s = run(s, th, Noise(X.TAG, cases, "release"), ROUTES["body"], D.RELEASE, p)
    return State(s.V, s.ema, s.R, np.zeros_like(s.V)), th, T


def main():
    t0 = time.time()
    cases = enrol(BLOCKS, D.MESSAGES, D.PARENTS, "engineering")
    out = {"test": "T5 gain x noise", "blocks": BLOCKS, "levels": {}}
    for fam in ("F0", "S4"):
        for sigma in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
            p = replace(NATIVE, sigma=sigma)
            s0, th, T = acquire_t(cases, p, fam)
            arms = [(f"g{g:g}", g, s0.R) for g in (0.0, 0.05, 0.2, 0.8)]
            V = run_arms(s0, th, T, cases, p, True, arms)
            lv = {name: {m: round(float(x.mean()), 4) for m, x in scores(V[i], T).items()} for i, (name, _, _) in enumerate(arms)}
            for name in list(lv):
                lv[name]["value_sign"] = round(lv[name]["sign"] - lv["g0"]["sign"], 4)
            out["levels"][f"{fam}_s{sigma:g}"] = lv
            print(fam, sigma, f"{time.time() - t0:.0f}s", {n: (d["sign"], d["value_sign"]) for n, d in lv.items()}, flush=True)
            X.save("t5_gain_noise.json", out)
    out["wall_s"] = round(time.time() - t0, 1)
    X.save("t5_gain_noise.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
