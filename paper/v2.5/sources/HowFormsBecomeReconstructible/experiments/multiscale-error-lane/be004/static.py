"""BE004's static map: python -m be004.static  ->  be004/frozen/static_map.json

Computed before the freeze from the design's constants alone: no dynamics and no development outcome (BE002's static map,
be002/static.py, generalised to every footprint geometry and closure of this design).

Anchors sit at a random quarter of the cells, as the engine draws them, and inject kappa * (+1 where cue and record
agree, -1 where they disagree); the potentials solve the cable equation with each arm's conductances while its signal is
on (bio-1 and bio-3 at their uniform lengths). 4,000 draws, one seed; every arm sees the same draws. A 4 x 4 patch sits
at the corner (the torus is homogeneous); each arm's footprint is the patch dilated by its d and shifted by its offset
along the rows, as in be004.sim.arm_footprint.
  adoption      the whole patch disagrees (memory damage and a legitimate change give the same currents): the share of
                the patch below -theta
  false alarms  a random quarter of all anchors disagree (scattered corruption): the shares of cells below -theta inside
                the arm's footprint, outside it and over the sheet
  evidence      under the dial's conductances, each of the patch's anchors has been repaired (agrees again) independently
                with probability a, a in {0, 0.1, ..., 0.7}: the share of the patch below -theta at the signal's onset
                (THEORY 8.8's mean field: a 4 x 4 group's centre stops crossing at a* = 0.29 under lam 1)
The hold, flicker and duration arms have the dial's footprint and closure, so their static map is the dial's.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be001.sim import cable_kernel  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from be004 import design as D  # noqa: E402
from be004 import sim  # noqa: E402

DRAWS, SEED = 4000, 20261029
EVIDENCE = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
GEOMETRY = ("dial", "dial-s2", "dial-s4", "dial-s6", "dial-d0", "dial-d4", "dial-d8", "dial-w1.5", "dial-w2")
OUT = LANE / "be004" / "frozen" / "static_map.json"


def solver(arm, m):
    """A function from currents (n, n) to potentials with the arm's conductances while its signal is on."""
    if arm in ("bio-1", "bio-3"):
        kern = cable_kernel(1.0 if arm == "bio-1" else 3.0)
        return lambda cur: np.real(np.fft.ifft2(np.fft.fft2(cur) / kern)), None
    fp = sim.arm_footprint(arm, m[None])
    gH, gW = B2S.conductances(fp, D.SIG["lam_rest"], D.SIGNAL_ARMS[arm]["lam_sig"])
    lu = B2S.factor(gH, gW)[0]
    return (lambda cur: lu.solve(cur.ravel()).reshape(cur.shape)), fp[0]


def main():
    n, th = D.SIDE, D.SIG["theta"]
    rng = np.random.default_rng(SEED)
    m = np.zeros((n, n), bool)
    m[:4, :4] = True
    arms = ("bio-1", "bio-3", *GEOMETRY)
    solv = {a: solver(a, m) for a in arms}
    adopt = {a: [] for a in arms}
    fa = {a: {"in": [], "out": [], "all": []} for a in arms}
    ev = {a_: [] for a_ in EVIDENCE}
    dial, fp_dial = solv["dial"]
    for _ in range(DRAWS):
        anch = np.zeros(n * n, bool)
        anch[rng.permutation(n * n)[: n * n // D.DENSITY]] = True
        anch = anch.reshape(n, n)
        cur = D.KAPPA * anch * np.where(m, -1.0, 1.0)
        for a in arms:
            adopt[a].append(float((solv[a][0](cur)[m] < -th).mean()))
        idx = np.flatnonzero(anch)
        s = np.ones(n * n)
        s[rng.permutation(idx)[: len(idx) // 4]] = -1.0
        cur = D.KAPPA * anch * s.reshape(n, n)
        for a in arms:
            below = solv[a][0](cur) < -th
            fp = solv[a][1] if solv[a][1] is not None else fp_dial
            fa[a]["in"].append(float(below[fp].mean()))
            fa[a]["out"].append(float(below[~fp].mean()))
            fa[a]["all"].append(float(below.mean()))
        u = rng.random((n, n))
        for a_ in EVIDENCE:
            sign = np.where(m, np.where(u < a_, 1.0, -1.0), 1.0)
            ev[a_].append(float((dial(D.KAPPA * anch * sign)[m] < -th).mean()))
    res = {"note": "static map, no dynamics; computed before the freeze from the design's constants", "draws": DRAWS,
           "seed": SEED, "design_digest": D.digest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "patch": 4, "theta": th,
           "adoption": {a: round(float(np.mean(adopt[a])), 4) for a in arms},
           "false_alarms": {a: {k: round(float(np.mean(v)), 5) for k, v in fa[a].items()} for a in arms},
           "footprint_cells": {a: int(solv[a][1].sum()) for a in GEOMETRY},
           "evidence": {f"{a_:.1f}": round(float(np.mean(ev[a_])), 4) for a_ in EVIDENCE},
           "same_as_dial": ["dial-hold", "dial-f0.5", "dial-f0.25", "dial-t1", "dial-t10", "dial-t100"]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    for a in arms:
        f = res["false_alarms"][a]
        print(f"{a:10s} adoption {res['adoption'][a]:.3f}  false alarms in {f['in']:.4f} out {f['out']:.5f} all {f['all']:.4f}"
              + (f"  cells {res['footprint_cells'][a]}" if a in GEOMETRY else ""))
    print("evidence (share of the patch below -theta at onset, by the fraction of its anchors repaired):", res["evidence"])


if __name__ == "__main__":
    main()
