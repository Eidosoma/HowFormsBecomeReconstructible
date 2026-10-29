"""T2: the body with a held record. Conserved against open, gain, and noise colour. ENGINEERING_PROBE_NOT_EVIDENCE.

BR001's acquisition (settle, teach the template, release on the hold route) on engineering blocks
900833-900836 (32 cases) under the tag 'mse-expansion', for F0 and BL at sigma 0.05, 0.1, 0.2, 0.3. Then 2000
updates of the body reading a held record r = R0 (BR001's 'static' arm) with gain c, or a record carrying a
6 x 6 flipped patch, in the conserved and the open body (xcommon.body_step = br001.sim.body_step, qualified
in T1). All arms of a case share the same draws. Part N repeats the gains 0 and 0.2 in the conserved body with
spatially correlated noise (white noise smoothed by a Gaussian of sd 1 or 2 sites, rescaled to unit variance
per site).

Endpoints at t = 2000: sign agreement with the template; 'qual' (sign and |V| > 0.2, BR001's v_qual); the best
agreement over all 256 cyclic shifts (form kept but displaced); uniform (|mean sign| > 0.8, the pattern gone).
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

BLOCKS = list(X.BLOCKS[1:5])
UPDATES = 2000


def shift_best(V, T):
    """max over cyclic shifts of sign agreement, via FFT cross-correlation of the sign fields."""
    a, b = np.sign(V), np.sign(T)
    c = np.real(np.fft.ifft2(np.fft.fft2(a) * np.conj(np.fft.fft2(b)))) / (V.shape[-1] * V.shape[-2])
    return (1 + c.max(axis=(-2, -1))) / 2


def scores(V, T, damaged=None):
    s = {"sign": ((V > 0) == (T > 0)).mean((-2, -1)), "qual": (((V > 0) == (T > 0)) & (np.abs(V) > 0.2)).mean((-2, -1)),
         "shift_best": shift_best(V, T), "uniform": (np.abs(np.sign(V).mean((-2, -1))) > 0.8).astype(float)}
    if damaged is not None:
        s["sign_in_patch"] = (((V > 0) == (T > 0)) & damaged).sum((-2, -1)) / damaged.sum((-2, -1))
        s["sign_outside"] = (((V > 0) == (T > 0)) & ~damaged).sum((-2, -1)) / (~damaged).sum((-2, -1))
    return s


def kernel_norm(sd, side=16):
    k = np.fft.fftfreq(side) * 2 * np.pi
    kx, ky = np.meshgrid(k, k, indexing="ij")
    K = np.exp(-0.5 * sd ** 2 * (kx ** 2 + ky ** 2))
    return float(np.sqrt((K ** 2).mean()))


def run_arms(s0, th, T, cases, p, conserved, arms, colour=0.0):
    """arms: list of (name, gain, record). One batch, the cases' draws tiled across arms."""
    k, na = len(cases), len(arms)
    noise = Noise(X.TAG, cases, "t2-future")
    norm = kernel_norm(colour) if colour else 1.0
    v = np.tile(s0.V, (na, 1, 1))
    e = np.tile(s0.ema, (na, 1, 1))
    r = np.concatenate([a[2] for a in arms])
    g = np.repeat([a[1] for a in arms], k)[:, None, None]
    thb = np.tile(th, (na, 1, 1))
    for t in range(1, UPDATES + 1):
        z = noise(t)
        if colour:
            z = X.smooth(z, colour) / norm
        v, e, _ = X.body_step(v, e, r, thb, np.tile(z, (na, 1, 1)), p, conserved, g)
    return v.reshape(na, k, 16, 16)


def main():
    t0 = time.time()
    cases = enrol(BLOCKS, D.MESSAGES, D.PARENTS, "engineering")
    k = len(cases)
    patch = np.zeros((k, 16, 16), bool)
    for i, c in enumerate(cases):
        a, b = address(X.TAG, *c.key(), "t2-record-lesion").integers(0, 16, 2)
        patch[i][np.ix_(np.arange(a, a + 6) % 16, np.arange(b, b + 6) % 16)] = True
    out = {"test": "T2 bodies", "blocks": BLOCKS, "cases": k, "updates": UPDATES, "levels": {}}
    for fam in ("F0", "BL"):
        for sigma in (0.05, 0.1, 0.2, 0.3):
            p = replace(NATIVE, sigma=sigma)
            s0, th, T, _ = acquire(cases, p, fam)
            R0 = s0.R
            Rd = np.where(patch, -R0, R0)
            arms = [(f"g{g:g}", g, R0) for g in (0.0, 0.05, 0.2, 0.8)] + [(f"dmg_g{g:g}", g, Rd) for g in (0.05, 0.2, 0.8)]
            for conserved in (True, False):
                V = run_arms(s0, th, T, cases, p, conserved, arms)
                key = f"{fam}_s{sigma:g}_{'c' if conserved else 'o'}"
                out["levels"][key] = {}
                for i, (name, g, _) in enumerate(arms):
                    sc = scores(V[i], T, patch if name.startswith("dmg") else None)
                    out["levels"][key][name] = {m: round(float(x.mean()), 4) for m, x in sc.items()}
                print(key, f"{time.time() - t0:.0f}s", {n: (d["sign"], d["shift_best"], d["uniform"])
                                                      for n, d in out["levels"][key].items()}, flush=True)
            if sigma in (0.1, 0.3):
                for colour in (1.0, 2.0):
                    arms2 = [("g0", 0.0, R0), ("g0.2", 0.2, R0)]
                    V = run_arms(s0, th, T, cases, p, True, arms2, colour)
                    key = f"{fam}_s{sigma:g}_c_colour{colour:g}"
                    out["levels"][key] = {name: {m: round(float(x.mean()), 4) for m, x in scores(V[i], T).items()}
                                          for i, (name, _, _) in enumerate(arms2)}
                    print(key, {n: (d["sign"], d["shift_best"]) for n, d in out["levels"][key].items()}, flush=True)
            out["wall_s"] = round(time.time() - t0, 1)
            X.save("t2_bodies.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
