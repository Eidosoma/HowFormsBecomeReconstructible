"""LR001 unit checks: design shape, the bond algebra, and the record and body paths against gw001.sim, bit for bit."""
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from gw001 import design as GD
from gw001 import sim as GS
from lr001 import design as D
from lr001 import sim
from mse.native import NATIVE

BLOCK = 900857        # an LR001 debug block (engineering)


def test_design_shape():
    for p in D.PANELS:
        b = D.branches(p)
        assert len(b) == len(set(b)), p
    for p, a, b in D.CONTRASTS:
        names = {x.split("/")[0] if p == "C" else x.split("/")[-1] for x in D.branches(p)}
        assert a in names and b in names, (p, a, b)
    assert len({c.name for c in D.C_CONDS}) == len(D.C_CONDS)


def test_bond_algebra():
    cases, V, ema, R0, th, T = sim.prepare("IS", BLOCK, "engineering")
    H, W = sim.edges_from(sim.bonds(R0, True))
    assert (sim.flux(H, W) == 1).all()
    for i, j in ((0, 0), (5, 15), (15, 3)):
        H2 = H.copy()
        H2[1, i, j] *= -1
        assert int((sim.flux(H2, W)[1] < 0).sum()) == 2
        H3, W3 = sim.parity_repair(H2, W)
        assert np.array_equal(H3, H) and np.array_equal(W3, W)
    s = np.sign(R0)
    corner = np.repeat(np.repeat(s[:, ::4, ::4], 4, 1), 4, 2)
    assert np.array_equal(sim.gauge_frame(H, W), s * corner)
    assert all(np.array_equal(x, y) for x, y in zip(sim.halves(H, W), sim.bonds(R0, True)))


def test_codes_equal_gw001_record_path():
    cases, V, ema, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    k = len(cases)
    m = sim.patch(cases, 8)
    conds = (D.Cond("flip8", "flip", 8), D.Cond("kill8", "kill", 8))
    _, fin = sim.simulate_C(cases, R0, T, {8: m}, window=500, reads=(500,), codes=("none", "plain"), conds=conds)
    cg = (GD.Cond("f8", "flip", 8), GD.Cond("k8", "kill", 8))
    for ci, arm in enumerate((GD.Arm("rel", eps=GD.EPS, rel=True), GD.Arm("rel+code", eps=GD.EPS, kc=GD.KC, rel=True))):
        rg, _, _ = GS.simulate_R(arm, cg, k, R0, T, [m, m], cases, 500, 250, tag=D.TAG)
        assert np.array_equal(fin["r"][2 * ci:2 * ci + 2].reshape(-1, 16, 16), rg), arm.name


def test_learning_panel_equals_gw001_body_path():
    cases, V, ema, R0, th, T = sim.prepare("IS", BLOCK, "engineering")
    p = replace(NATIVE, sigma=D.L_SIGMA)
    v, _, r, _ = GS.simulate_B(GD.Arm("rel", eps=GD.EPS, rel=True), (GD.Cond("sham"),), len(cases), V, ema, R0, th, T, p, True,
                               [None], [None], cases, 500, 500, tag=D.TAG)
    _, fin = sim.simulate_L(cases, V, ema, R0, th, T, window=500, reads=(500,), learns=("none",), scar_until=0)
    assert np.array_equal(fin["v"][0], v) and np.array_equal(fin["r"][0], r)


def test_trust_alias_on_flips_and_kills():
    cases, V, ema, R0, th, T = sim.prepare("BL", BLOCK, "engineering")
    masks = {s: sim.patch(cases, s) for s in (0, 8)}
    conds = (D.Cond("flip8", "flip", 8), D.Cond("kill8", "kill", 8), D.Cond("relink8", "relink", 8))
    _, fin = sim.simulate_C(cases, R0, T, masks, window=300, reads=(300,), codes=("hybrid", "hybrid+trust"), conds=conds)
    assert np.array_equal(fin["r"][0], fin["r"][3]) and np.array_equal(fin["r"][1], fin["r"][4])
    assert not np.array_equal(fin["r"][2], fin["r"][5])
