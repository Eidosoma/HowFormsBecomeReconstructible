"""LR002's tests: python -m pytest tests/test_lr002.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl002 import design as D2  # noqa: E402
from dl002 import sim as S2  # noqa: E402
from lr001 import design as D1  # noqa: E402
from lr001 import sim as S1  # noqa: E402
from lr002 import design as D  # noqa: E402
from lr002 import sim  # noqa: E402
from msegrid.core import Stream, bonds  # noqa: E402

BLOCK = 900736


def stripes():
    return np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)[None]


def test_design_conditions():
    names = [c.name for c in D.CONDS]
    assert len(names) == len(set(names)) == len(D.RATES) * len(D.REPAIRS)
    want = {"none": ("", False), "parity": ("", True), "record": ("record", False), "record+parity": ("record", True),
            "body": ("body", False), "body+parity": ("body", True)}
    for rep, (learn, par) in want.items():
        c = D.Cond(0.001, rep)
        assert (c.learn, c.parity) == (learn, par)
    assert D.digest() == D.digest()
    src = D.sources(Path(__file__).resolve().parents[1])
    assert "lr001/sim.py" in src and "dl002/sim.py" in src and "lr002/sim.py" in src


def test_parity_and_learning_mechanics():
    T = stripes()
    H0, W0 = S1.edges_from(bonds(T, True))
    zero = np.zeros_like(T)
    H = H0.copy()
    H[0, 5, 9] *= -1
    P = sim.params((D.Cond(0.0, "parity"),), 1)
    Hr, Wr, Hb, Wb, _ = sim.relations(H, W0.copy(), 0.8 * H, 0.8 * W0, 1.2 * T, zero, zero, None, P)
    assert np.array_equal(Hr, H0) and np.array_equal(Wr, W0) and np.array_equal(np.sign(Hb), H0)
    P = sim.params((D.Cond(0.0, "record"),), 1)
    Hr, Wr, _, _, _ = sim.relations(H0.copy(), W0.copy(), 0.8 * H0, 0.8 * W0, 1.2 * T, zero, zero, None, P)
    assert np.array_equal(Hr, H0) and np.array_equal(Wr, W0)
    V = np.random.default_rng(0).standard_normal(T.shape)
    P = sim.params((D.Cond(0.0, "body"),), 1)
    _, _, Hb, Wb, _ = sim.relations(H0.copy(), W0.copy(), 0.8 * H0, 0.8 * W0, 1.2 * T, zero, zero, V, P)
    assert np.allclose(Hb, 0.8 * H0 + D.ETA * (np.clip(V * np.roll(V, -1, -1), -1, 1) - 0.8 * H0), atol=1e-15)
    assert np.allclose(Wb, 0.8 * W0 + D.ETA * (np.clip(V * np.roll(V, -1, -2), -1, 1) - 0.8 * W0), atol=1e-15)


def test_equals_dl002_rel_branch():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    o = sim.run("li4", (D.Cond(0.0, "none"),), cases, V0, ema0, R0, th, T, 1.0, {D2.WINDOW}, tag=D2.TAG, kc=D2.KC,
                window=D2.WINDOW)
    o2 = S2.run("li4", (D2.Rec("rel", "rel", 0.2),), cases, V0, ema0, R0, th, T, 1.0, "", {D2.WINDOW})
    assert np.array_equal(o["V"], o2["final"]) and np.array_equal(o["r"], o2["r_rel"])


def test_record_never_reads_the_body_and_flip_rate():
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    conds = (D.Cond(0.01, "record+parity"), D.Cond(0.01, "body"))
    a = sim.run("dw", conds, cases, V0, ema0, R0, th, T, 1.0, {300}, window=300)
    b = sim.run("li4", conds, cases, V0, ema0, R0, th, T, 1.0, {300}, window=300)
    k = len(cases)
    for key in ("r", "H", "W"):
        assert np.array_equal(a[key][:k], b[key][:k])
    assert not np.array_equal(a["H"][k:], b["H"][k:])
    assert abs(a["flip_rate"].mean() - 0.01) < 0.001


def test_relations_equal_lr001_simulate_E():
    cases = S1.cases_for(BLOCK, "engineering")
    _, _, _, R0, _, T = S1.prepare("F0", BLOCK, "engineering")
    window = 200
    _, fin = S1.simulate_E(cases, R0, T, window=window, reads=(window,))
    rename = {"none": "none", "hebb": "record", "parity": "parity", "both": "record+parity"}
    conds = [D.Cond(r_, rename[rep]) for r_ in D1.E_RATES for rep in D1.E_REPAIRS]
    k = len(cases)
    idx = np.tile(np.arange(k), len(conds))
    P = sim.params(conds, k)
    H0, W0 = S1.edges_from(bonds(R0, True))
    H, W = H0[idx].copy(), W0[idx].copy()
    Hb, Wb, r = D.STRENGTH0 * H, D.STRENGTH0 * W, R0[idx].copy()
    xs, zs = Stream(D1.TAG, cases, "record-noise", "E", side=D1.SIDE), Stream(D1.TAG, cases, "bond-noise", side=D1.SIDE)
    for t in range(1, window + 1):
        i = (t - 1) % 100
        if i == 0:
            xb, zb = xs.take(100), zs.take(100)
        H, W, Hb, Wb, r = sim.relations(H, W, Hb, Wb, r, xb[i][idx], zb[i][idx], None, P, 0.0, None)
    shape = (len(conds), k, D1.SIDE, D1.SIDE)
    assert np.array_equal(r.reshape(shape), fin["r"])
    assert np.array_equal(H.reshape(shape), fin["H"]) and np.array_equal(W.reshape(shape), fin["W"])
