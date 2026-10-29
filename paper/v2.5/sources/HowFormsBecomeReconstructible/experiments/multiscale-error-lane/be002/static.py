"""BE002's static map: python -m be002.static  ->  be002/frozen/static_map.json

Computed before the freeze from the design's constants alone: no dynamics and no development outcome (THEORY 8.7's
calculation, which for BE001 was made only after the run, here registered before it).

Anchors sit at a random quarter of the cells, as the engine draws them, and inject kappa * (+1 where cue and record
agree, -1 where they disagree); the potentials solve the cable equation with each arm's conductances while the signal is
on. Two configurations, 4,000 draws each (one seed; every arm sees the same draws):
  adoption      a patch of side 4 or 8 disagrees (memory damage and a legitimate change give the same currents); the
                share of the patch whose potential is below -theta (the torus is homogeneous, so the patch's corner is
                fixed);
  false alarms  a random quarter of the anchors disagree (scattered corruption) under a sham footprint (an 8 x 8 patch
                dilated by d): the shares of cells below -theta inside the footprint, outside it and over the sheet
                (permit-local may commit inside the footprint only).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be001 import design as B1  # noqa: E402
from be001.sim import cable_kernel  # noqa: E402
from be002 import design as D  # noqa: E402
from be002 import sim  # noqa: E402

DRAWS, SEED = 4000, 20261028
OUT = LANE / "be002" / "frozen" / "static_map.json"


def solver(arm, fp):
    """A function from currents (n, n) to potentials with the arm's conductances while the signal is on."""
    lam = {"bio-1": 1.0, "bio-1.5": 1.5, "bio-3": 3.0, "dial-global": D.SIG["lam_sig"],
           "permit-local": D.SIG["lam_permit"]}.get(arm)
    if lam is not None:
        kern = cable_kernel(lam)
        return lambda cur: np.real(np.fft.ifft2(np.fft.fft2(cur) / kern))
    gH, gW = sim.conductances(fp[None])
    lu = sim.factor(gH, gW)[0]
    return lambda cur: lu.solve(cur.ravel()).reshape(cur.shape)


def theta(arm):
    return D.SIGNAL_ARMS[arm]["theta"] if arm in D.SIGNAL_ARMS else B1.BIO[arm]["theta"]


def main():
    n = D.SIDE
    rng = np.random.default_rng(SEED)
    arms = [a for a in D.ARMS if a != "cue"]
    res = {"note": "static map, no dynamics; computed before the freeze from the design's constants", "draws": DRAWS,
           "seed": SEED, "design_digest": D.digest(), "adoption": {}, "false_alarms": {},
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    patches = {}
    for z in (4, 8):
        m = np.zeros((n, n), bool)
        m[:z, :z] = True
        patches[z] = (m, sim.footprint(m[None])[0])
    solvers = {(a, z): solver(a, patches[z][1]) for a in arms for z in (4, 8)}
    adopt = {(a, z): [] for a in arms for z in (4, 8)}
    fa = {a: {"in": [], "out": [], "all": []} for a in arms}
    m8, fp8 = patches[8]
    for _ in range(DRAWS):
        anch = np.zeros(n * n, bool)
        anch[rng.permutation(n * n)[: n * n // D.DENSITY]] = True
        anch = anch.reshape(n, n)
        for z in (4, 8):
            m = patches[z][0]
            cur = D.KAPPA * anch * np.where(m, -1.0, 1.0)
            for a in arms:
                v = solvers[(a, z)](cur)
                adopt[(a, z)].append(float((v[m] < -theta(a)).mean()))
        idx = np.flatnonzero(anch)
        s = np.ones(n * n)
        s[rng.permutation(idx)[: len(idx) // 4]] = -1.0
        cur = D.KAPPA * anch * s.reshape(n, n)
        for a in arms:
            below = solvers[(a, 8)](cur) < -theta(a)
            if a == "permit-local":
                below &= fp8
            fa[a]["in"].append(float(below[fp8].mean()))
            fa[a]["out"].append(float(below[~fp8].mean()))
            fa[a]["all"].append(float(below.mean()))
    for a in arms:
        res["adoption"][a] = {str(z): round(float(np.mean(adopt[(a, z)])), 4) for z in (4, 8)}
        res["false_alarms"][a] = {k: round(float(np.mean(v)), 5) for k, v in fa[a].items()}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    for a in arms:
        print(f"{a:13s} adoption 4 / 8: {res['adoption'][a]['4']:.3f} / {res['adoption'][a]['8']:.3f}   false alarms "
              f"in {res['false_alarms'][a]['in']:.4f} out {res['false_alarms'][a]['out']:.5f} all {res['false_alarms'][a]['all']:.4f}")


if __name__ == "__main__":
    main()
