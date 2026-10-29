"""Engineering check P24b (python probes/p24b_be002_late_evidence.py): why does BE002's late signal repair less?
ENGINEERING_POSTHOC_NOT_EVIDENCE; written after BE002's development read (28 October 2026), by the BE002 fork, moved
into the lane by the lead.

Engineering block 900640 under the probe's tag mse-p24 (8 cases); units S4_t0, LB_t0, F0_t0 and F0_t1; both bodies.
Inside a 4 x 4 memory-damaged patch, at t = 0 and at t = 1,000 (when the late signal starts; until then dial-local is
bio-3, run here): the record's agreement with the target at anchored and at unanchored cells, the share of the patch's
anchors still disagreeing with their cues (the detector's only evidence), and the static share of the patch below
-theta under dial-local's footprint conductances, from the record's confident signs at that time.
Writes probes/results/p24b_be002_late_evidence.json.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be002 import design as D, sim  # noqa: E402
from lr005 import sim as L5S  # noqa: E402

BLOCK = 900640
UNITS = ("S4_t0", "LB_t0", "F0_t0", "F0_t1")


def main():
    out = {}
    for unit in UNITS:
        pattern, theta = D.parse_unit(unit)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, BLOCK, "engineering")
        ev = sim.event("memory", 4, cases, V0, ema0, R0, T, D.PROBE_TAG)
        m, am, aval = ev["m"], ev["am"], ev["aval"]
        lus = sim.factor(*sim.conductances(sim.footprint(m)))
        for body in D.BODIES:
            o = sim.run(body, "memory", 4, "", cases, V0, ema0, R0, th, T, theta, {1000}, tag=D.PROBE_TAG, window=1000,
                        arms=("bio-3",))
            res = {}
            for name, r in (("t0", ev["r"]), ("t1000", o["r"])):
                sr = L5S.vote_sign(r)
                ok = (r > 0) == (T > 0)
                cur = D.KAPPA * np.where(am, aval, 0.0) * sr
                v = sim.solve(lus, cur)
                res[name] = {"anchored_right": round(float((ok & m & am).sum() / (m & am).sum()), 3),
                             "unanchored_right": round(float((ok & m & ~am).sum() / (m & ~am).sum()), 3),
                             "anchors_disagreeing": round(float(((cur < 0) & m).sum() / (m & am).sum()), 3),
                             "static_share_below_theta": round(float(((v < -0.1) & m & (sr != 0)).sum() / m.sum()), 3)}
            out[f"{unit}/{body}"] = res
            print(unit, body, res, flush=True)
    path = LANE / "probes" / "results" / "p24b_be002_late_evidence.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
