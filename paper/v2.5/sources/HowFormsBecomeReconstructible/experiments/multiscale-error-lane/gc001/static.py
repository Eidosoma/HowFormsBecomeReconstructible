"""GC001's static map, registered with the statements: no dynamics, the record taken equal to the target.

python -m gc001.static   (writes gc001/frozen/static_map.json)

On the static cases (engineering blocks STATIC_BLOCKS, 8 cases each, per pattern), for every sigma:
  misread_theory  the expected share of sites whose noisy read differs from their own value: sum over displacements
                  (dx, dy) of p(dx) p(dy) [T(x + d) != T(x)], with p(n) = Phi((n + 1/2)/sigma) - Phi((n - 1/2)/sigma)
  misread         the realised share of anchors misread (the quenched draw), and its share in the boundary band
and, for the graded cue and its matched scattered control, for every coupling length of the ladder: the share of sites
whose steady potential (g_l + lam^2 L) v = kappa * cue * sign(T) lies below -theta (a confident cell there would trigger),
over the sheet, in the band and in the interior. That share is the static map's false-alarm prediction.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from scipy.stats import norm  # noqa: E402

from be001 import sim as B1S  # noqa: E402
from gc001 import design as D  # noqa: E402
from gc001 import sim  # noqa: E402
from lr005 import sim as L5S  # noqa: E402


def misread_map(T, sigma):
    """Per site, the probability that its rounded-Gaussian displaced read of sign(T) differs from its own value."""
    if sigma == 0:
        return np.zeros(T.shape)
    K = int(np.ceil(6 * sigma)) + 1
    n = np.arange(-K, K + 1)
    p = norm.cdf((n + 0.5) / sigma) - norm.cdf((n - 0.5) / sigma)
    s = np.sign(T)
    exp = np.zeros(T.shape)
    for a, pa in zip(n, p):
        for b, pb in zip(n, p):
            exp += pa * pb * (np.roll(s, (-a, -b), (-2, -1)) != s)
    return exp


def misread_theory(T, sigma):
    """Expected share of sites (per case) whose rounded-Gaussian displaced read of sign(T) differs from their own."""
    return misread_map(T, sigma).mean((-2, -1))


def static_case_set(pattern):
    cases, R0, T = [], [], []
    for blk in range(*D.STATIC_BLOCKS):
        c, V0, ema0, r0, th, t = sim.prepare(pattern, blk, "engineering")
        cases += list(c)
        R0.append(r0)
        T.append(t)
    return cases, np.concatenate(R0), np.concatenate(T)


def shares(v, theta, band, interior):
    trig = v < -theta
    return {"all": round(float(trig.mean()), 5), "band": round(float((trig & band).sum() / band.sum()), 5),
            "interior": round(float((trig & interior).sum() / max(interior.sum(), 1)), 5)}


def compute():
    out = {"note": "static map, no dynamics; the record equal to the target; computed before the freeze on engineering "
                   "blocks only", "static_blocks": list(D.STATIC_BLOCKS), "design_digest": D.digest(), "patterns": {}}
    theta = D.BIO["bio-1"]["theta"]
    for pattern in D.PATTERNS:
        cases, R0, T = static_case_set(pattern)
        k = len(cases)
        V0 = np.zeros_like(R0)
        ev0 = B1S.event("none", 8, cases, V0, V0, R0, T, D.TAG)
        am, exact = ev0["am"], ev0["aval"]
        g = sim.unit_normals(cases, D.TAG)
        dist = sim.boundary_distance(T)
        band, interior = dist == D.BAND, dist > D.BAND
        sr = np.sign(T)
        node = {"cases": k, "band_share": round(float(band.mean()), 4), "sigmas": {}}
        for sigma in D.SIGMAS:
            noisy = sim.read_at(exact, g, sigma)
            mis = (noisy != exact) & am
            counts = mis.sum((-2, -1))
            scat = np.where(sim.matched_flips(cases, am, counts, D.TAG), -exact, exact)
            s_node = {"misread_theory": round(float(misread_theory(T, sigma).mean()), 4),
                      "misread": round(float(mis.sum() / am.sum()), 4),
                      "misread_band_share": round(float((mis & band).sum() / max(mis.sum(), 1)), 4), "trigger": {}}
            for cond, field in (("graded", noisy), ("scatter", scat)):
                if sigma == 0 and cond == "scatter":
                    continue
                cur = D.KAPPA * np.where(am, field, 0.0) * sr
                for arm, prm in D.BIO.items():
                    v = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(prm["lam"])))
                    s_node["trigger"][f"{cond}/{arm}"] = shares(v, theta, band, interior)
            node["sigmas"][f"{sigma:g}"] = s_node
        out["patterns"][pattern] = node
    return out


if __name__ == "__main__":
    t0 = time.time()
    res = compute()
    res["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    res["seconds"] = round(time.time() - t0, 1)
    path = Path(__file__).resolve().parent / "frozen" / "static_map.json"
    path.write_text(json.dumps(res, indent=1) + "\n")
    for p, node in res["patterns"].items():
        for s, sn in node["sigmas"].items():
            tr = {k: v["all"] for k, v in sn["trigger"].items()}
            print(p, s, "misread theory %.3f realised %.3f band %.3f" % (sn["misread_theory"], sn["misread"], sn["misread_band_share"]), tr)
