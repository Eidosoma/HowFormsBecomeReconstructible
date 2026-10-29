"""Lead's spot check of MODEL_LIMITS_AND_EXPANSION.md section 2.1 (python probes/expansion/check_br002_reset_vs_flip.py).
ENGINEERING_PROBE_NOT_EVIDENCE. Independent of the study's own engine: BR002's simulator (br002/sim.py, unchanged),
consensus alone (panel G's 'self'), F0 at sigma 0.1 (conserved), wounds at declared distances from the walls, flipped
(record and body inverted) against reset (BR002's kill: record 0, newborn body), engineering blocks 900850-900851
under BR002's tag. Run 25 October 2026: flip/reset kept 6x6 centred 0.000/1.000, 4x4 touching 0.617/0.812,
6x6 straddling 0.880/0.991, 8x8 spanning the domain 0.000/0.437.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from br002 import design as D, sim  # noqa: E402

name = D.regime("F0", 0.1)
cases, s0, th, p, conserved, T, Tf = sim.prepare(name, [900850, 900851], "engineering")
k = len(cases)
Z = sim.draws(cases, "future", updates=D.WINDOW)
XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
conds = []
for s, pl in ((6, "d1"), (4, "d0"), (6, "cross"), (8, "d0")):
    conds += [D.Cond(f"flip-{s}-{pl}", "lesion", s, place=pl), D.Cond(f"reset-{s}-{pl}", "kill", s, place=pl)]
masks = sim.masks_for(cases, conds)
born = [sim.newborn(cases, c.size) if c.kind == "kill" else None for c in conds]
v, e, r, w = sim.simulate(D.ARM["G"]["self"], tuple(conds), k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, Tf,
                          np.ones(k, int), masks, [None] * len(conds), born)
idx = np.tile(np.arange(k), len(conds))
kept = sim.masked_sign(r, T[idx], np.concatenate(masks)).reshape(len(conds), k).mean(1)
for c, x in zip(conds, kept):
    print(f"{c.name:14s} kept {x:.3f}")
