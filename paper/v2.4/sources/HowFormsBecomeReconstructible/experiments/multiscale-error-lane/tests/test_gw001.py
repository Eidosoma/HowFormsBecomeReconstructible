"""GW001 unit checks: design shape, and both simulators against br002.sim.simulate at side 16, bit for bit."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from br002 import design as D2
from br002 import sim as S2
from gw001 import design as D
from gw001 import sim

BLOCK = [900863]


def test_design_shape():
    for p in D.PANELS:
        names = [a.name for a in D.PANELS[p]["arms"]]
        assert len(names) == len(set(names))
        for unit in D.PANELS[p]["units"]:
            cs = D.conditions(p, unit)
            assert len({c.name for c in cs}) == len(cs)
    for p, a, b in D.CONTRASTS:
        assert a in D.ARM[p] and b in D.ARM[p]
    assert D.parse_regime(D.REGIMES_B[0]) == ("F0", 16, 0.1, "c")


def _br002_state(name):
    cases, s0, th, p, conserved, T, Tf = S2.prepare(name, BLOCK, "engineering")
    return cases, s0, th, p, conserved, T, Tf


def test_record_panel_equals_br002_record_path():
    """Panel R's record (writing off) against br002's record under a both-lesion and a kill, same inputs."""
    cases, s0, th, p, conserved, T, Tf = _br002_state(D2.regime("F0", 0.1))
    k = len(cases)
    m4 = S2.patch_masks(cases, 4)
    m8 = S2.patch_masks(cases, 8)
    Z = S2.draws(cases, "future", updates=2000)
    XI = S2.draws(cases, "record-noise", updates=2000)
    born = S2.newborn(cases, 8)
    c2 = (D2.Cond("both-4x4", "lesion", 4), D2.Cond("kill-8x8", "kill", 8))
    cg = (D.Cond("f4", "flip", 4), D.Cond("k8", "kill", 8))
    for a in ("self", "multi", "rel", "rel+code"):
        ref = D2.ARM["R"][a]
        _, _, r2, _ = S2.simulate(ref, c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, Tf, np.ones(k, int),
                                  [m4, m8], [None, None], [None, born])
        r, _, _ = sim.simulate_R(D.ARM["R"][a], cg, k, s0.R, T, [m4, m8], cases, 2000, 250, tag=D2.TAG)
        assert np.array_equal(r, r2), a


def test_body_panel_equals_br002():
    """Panel B (flip, reset) against br002's both-lesion and kill (J = 1 arms: kill = reset), both bodies."""
    for name in (D2.regime("F0", 0.3), D2.regime("F0", 0.3, "o")):
        cases, s0, th, p, conserved, T, Tf = _br002_state(name)
        k = len(cases)
        m4 = S2.patch_masks(cases, 4)
        Z = S2.draws(cases, "future", updates=2000)
        XI = S2.draws(cases, "record-noise", updates=2000)
        born = S2.newborn(cases, 4)
        c2 = (D2.Cond("both-4x4", "lesion", 4), D2.Cond("kill-4x4", "kill", 4))
        cg = (D.Cond("f4", "flip", 4), D.Cond("r4", "reset", 4))
        for a in ("static", "multi", "protected"):
            ref = D2.ARM["R"][a]
            v2, _, r2, _ = S2.simulate(ref, c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, Tf, np.ones(k, int),
                                       [m4, m4], [None, None], [None, born])
            v, _, r, _ = sim.simulate_B(D.ARM["B"][a], cg, k, s0.V, s0.ema, s0.R, th, T, p, conserved, [m4, m4], [None, born],
                                        cases, 2000, 500, tag=D2.TAG)
            assert np.array_equal(v, v2) and np.array_equal(r, r2), (name, a)


def test_masks_are_paired_across_sizes_and_kinds():
    cases, R0, T = sim.prepare_R("F0_32", 900863, "engineering")
    conds = D.GEOMETRIES["F0_32"]
    masks = sim.masks_for(cases, conds, "F0", 32)
    byname = {c.name: m for c, m in zip(conds, masks)}
    assert np.array_equal(byname["f8-mid"], byname["r8-mid"]) and np.array_equal(byname["f8-mid"], byname["k8-mid"])
    small, big = byname["f4-d0"], byname["f8-d0"]
    assert (small.sum((-2, -1)) == 16).all() and (big.sum((-2, -1)) == 64).all()
