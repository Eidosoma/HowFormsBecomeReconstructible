"""T7: a zero-order 'slow the energy budget' pilot. ENGINEERING_PROBE_NOT_EVIDENCE.

The model has no energy. This pilot asks only how the answer to 'would the plan hold?' depends on which
processes are paid for. A budget factor phi (1, 0.5, 0.25, 0.1) multiplies the rates of the paid processes,
under three accountings:
  A  only correction is paid: the body's gain c, the record's self-correction eps and code pull kc
  B  every drift is paid (body dt, so the double well, coupling, theta and correction; record eps and kc),
     noise is thermal and unchanged
  C  as B, and the noise is activity-driven: body sigma and record sigma_r scaled by sqrt(phi), an exact
     time rescaling in the continuum limit
plus C at matched metabolic time (2000 / phi updates) with wall-clock turnover.
The tissue: BR001's record in the cells ('multi' arm: eps 0.05, k_r 1, sigma_r 0.02, code kc 0.02), the
conserved body reading it with c = 0.2; F0 and BL at sigma 0.1 and 0.3; conditions sham, a 6 x 6 lesion of body
and record at t = 1, and turnover 0.001 per cell per update (wall-clock: newborn v ~ 0.2 N(0,1), r = 0).
Blocks 900841-900842 (16 cases), tag 'mse-expansion'. Endpoints at the end: body sign and qual, record sign,
the lesion patch's record kept.
"""
from __future__ import annotations

from dataclasses import replace
import time

import numpy as np

import xcommon as X
from xcommon import NATIVE, address

from br001 import design as D
from mse.assay import Noise, enrol

from t1_geometry import acquire

BLOCKS = list(X.BLOCKS[9:11])
RATE = 1e-3


def events(cases, updates):
    out = []
    for c in cases:
        g = address(X.TAG, *c.key(), "t7-turnover", updates)
        n = int(g.poisson(RATE * updates * 256))
        t, site, val = g.integers(1, updates + 1, n), g.integers(0, 256, n), 0.2 * g.standard_normal(n)
        o = np.argsort(t, kind="stable")
        out.append((t[o], site[o], val[o]))
    return out


def simulate(s0, th, R0, mask, turn, cases, p, gain, eps, kc, sr, updates, nc):
    k = len(cases)
    v, e, r = np.tile(s0.V, (nc, 1, 1)), np.tile(s0.ema, (nc, 1, 1)), np.tile(R0, (nc, 1, 1))
    thb = np.tile(th, (nc, 1, 1))
    B = X.bproj(np.tile(R0, (nc, 1, 1)), 4)
    lesion = mask[1]
    v[k:2 * k] = np.where(lesion, -v[k:2 * k], v[k:2 * k])
    r[k:2 * k] = np.where(lesion, -r[k:2 * k], r[k:2 * k])
    zf, xf = Noise(X.TAG, cases, "t7-future"), Noise(X.TAG, cases, "t7-record-noise")
    ptr = [0] * k
    for t in range(1, updates + 1):
        v, e, _ = X.body_step(v, e, r, thb, np.tile(zf(t), (nc, 1, 1)), p, True, gain)
        r = X.record_step(r, np.tile(xf(t), (nc, 1, 1)), eps, D.KR, sr, kc, B)
        for j in range(k):                   # condition 2 (rows 2k..3k) carries turnover
            tt, site, val = turn[j]
            lo = ptr[j]
            hi = np.searchsorted(tt, t, "right")
            if hi > lo:
                ii, jj = np.divmod(site[lo:hi], 16)
                b = 2 * k + j
                v[b, ii, jj], e[b, ii, jj], r[b, ii, jj] = val[lo:hi], val[lo:hi], 0.0
                ptr[j] = hi
    return v.reshape(nc, k, 16, 16), r.reshape(nc, k, 16, 16)


def main():
    t0 = time.time()
    cases = enrol(BLOCKS, D.MESSAGES, D.PARENTS, "engineering")
    k = len(cases)
    lesion = np.zeros((k, 16, 16), bool)
    for i, c in enumerate(cases):
        a, b = address(X.TAG, *c.key(), "t7-lesion").integers(0, 16, 2)
        lesion[i][np.ix_(np.arange(a, a + 6) % 16, np.arange(b, b + 6) % 16)] = True
    mask = [None, lesion, None]
    out = {"test": "T7 budget pilot", "blocks": BLOCKS, "turnover_rate": RATE, "levels": {}}
    for fam in ("F0", "BL"):
        for sigma in (0.1, 0.3):
            p = replace(NATIVE, sigma=sigma)
            s0, th, T, _ = acquire(cases, p, fam)
            R0 = s0.R
            runs = []
            for phi in (1.0, 0.5, 0.25, 0.1):
                runs.append(("A", phi, p, NATIVE.gain * phi, D.EPS * phi, D.KC * phi, D.SIGMA_R, 2000))
                pb = replace(p, dt=p.dt * phi)
                runs.append(("B", phi, pb, NATIVE.gain, D.EPS * phi, D.KC * phi, D.SIGMA_R, 2000))
                pc = replace(p, dt=p.dt * phi, sigma=sigma * np.sqrt(phi))
                runs.append(("C", phi, pc, NATIVE.gain, D.EPS * phi, D.KC * phi, D.SIGMA_R * np.sqrt(phi), 2000))
                if phi in (0.5, 0.25):
                    runs.append(("C_matched", phi, pc, NATIVE.gain, D.EPS * phi, D.KC * phi, D.SIGMA_R * np.sqrt(phi),
                                 int(round(2000 / phi))))
            for scen, phi, pp, gain, eps, kc, sr, updates in runs:
                if scen == "A" and phi == 1.0:
                    pass
                elif phi == 1.0:
                    continue                     # B and C at phi = 1 are A at phi = 1
                turn = events(cases, updates)
                V, R = simulate(s0, th, R0, mask, turn, cases, pp, gain, eps, kc, sr, updates, 3)
                key = f"{fam}_s{sigma:g}"
                res = {}
                for ci, cond in enumerate(("sham", "lesion-6x6", "turnover-0.001")):
                    vs = ((V[ci] > 0) == (T > 0)).mean((-2, -1))
                    vq = (((V[ci] > 0) == (T > 0)) & (np.abs(V[ci]) > 0.2)).mean((-2, -1))
                    rs = ((R[ci] > 0) == (T > 0)).mean((-2, -1))
                    d = {"v_sign": round(float(vs.mean()), 4), "v_qual": round(float(vq.mean()), 4),
                         "r_sign": round(float(rs.mean()), 4)}
                    if cond.startswith("lesion"):
                        d["les_r"] = round(float(((((R[ci] > 0) == (T > 0)) & lesion).sum((-2, -1)) / lesion.sum((-2, -1))).mean()), 4)
                    res[cond] = d
                name = "base" if phi == 1.0 else f"{scen}_phi{phi:g}"
                out["levels"].setdefault(key, {})[name] = res
                print(key, name, updates, f"{time.time() - t0:.0f}s", res, flush=True)
                X.save("t7_budget.json", out)
    out["wall_s"] = round(time.time() - t0, 1)
    X.save("t7_budget.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
