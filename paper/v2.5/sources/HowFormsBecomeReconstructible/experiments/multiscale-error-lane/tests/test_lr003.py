"""LR003's tests: python -m pytest tests/test_lr003.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr001 import sim as S1  # noqa: E402
from lr002 import design as L2D  # noqa: E402
from lr002 import sim as L2S  # noqa: E402
from lr003 import design as D  # noqa: E402
from lr003 import sim  # noqa: E402
from msegrid.core import bonds  # noqa: E402

BLOCK = 900746


def stripes():
    return np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)[None]


def test_design_conditions():
    names = [c.name for c in D.CONDS]
    assert len(names) == len(set(names)) == len(D.RATES) * len(D.REPAIRS)
    want = {"record": ("record", False), "record+parity": ("record", True), "body": ("body", False),
            "body+parity": ("body", True), "agree": ("agree", False), "syndrome": ("syndrome", False),
            "site": ("site", False), "site+parity": ("site", True)}
    for rep, (source, par) in want.items():
        c = D.Cond(0.001, rep)
        assert (c.source, c.parity) == (source, par)
    src = D.sources(Path(__file__).resolve().parents[1])
    assert "lr002/sim.py" in src and "lr003/sim.py" in src


def test_gates():
    T = stripes()
    H0, W0 = S1.edges_from(bonds(T, True))
    H = H0.copy()
    H[0, 5, 9] *= -1
    uh, uw = sim.gates(H, W0, 1.2 * T, 1.2 * T, np.array([D.SOURCES["syndrome"]])[:, None, None])
    assert uh.sum() == 1 and uh[0, 5, 9] and not uw.any()
    V = 1.2 * T.copy()
    V[0, 7, 12] *= -1
    uh, uw = sim.gates(H0, W0, 1.2 * T, V, np.array([D.SOURCES["agree"]])[:, None, None])
    assert (~uh).sum() == 2 and not uh[0, 7, 12] and not uh[0, 7, 11]
    assert (~uw).sum() == 2 and not uw[0, 7, 12] and not uw[0, 6, 12]
    uh, uw = sim.gates(H, W0, 1.2 * T, 1.2 * T, np.array([D.SOURCES["site"]])[:, None, None])
    assert uh.sum() == 3 and uh[0, 5, 8] and uh[0, 5, 9] and uh[0, 5, 10]
    assert uw.sum() == 4 and uw[0, 4, 9] and uw[0, 5, 9] and uw[0, 4, 10] and uw[0, 5, 10]
    uh, uw = sim.gates(H, W0, 1.2 * T, V, np.array([D.SOURCES["body"]])[:, None, None])
    assert uh.all() and uw.all()
    uh, uw = sim.gates(H, W0, 1.2 * T, V, np.array([D.SOURCES["record"]])[:, None, None])
    assert not uh.any() and not uw.any()


def test_record_and_body_teachers_equal_lr002():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    reps = ("record", "record+parity", "body", "body+parity")
    c3 = tuple(D.Cond(r, rep) for r in (0.003, 0.03) for rep in reps)
    c2 = tuple(L2D.Cond(r, rep) for r in (0.003, 0.03) for rep in reps)
    o3 = sim.run("li4", c3, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, window=300)
    o2 = L2S.run("li4", c2, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, kc=D.KC, window=300)
    for key in ("V", "r", "H", "W"):
        assert np.array_equal(o3[key], o2[key])


def test_frustration_gates_are_record_relearning_without_noise():
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    conds = (D.Cond(0.0, "record"), D.Cond(0.0, "syndrome"), D.Cond(0.0, "site"), D.Cond(0.0, "site+parity"))
    o = sim.run("li4", conds, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, window=300)
    k = len(cases)
    assert not o["opened"].any()
    for key in ("V", "r", "H", "W"):
        for j in (1, 2, 3):
            assert np.array_equal(o[key][j * k:(j + 1) * k], o[key][:k])
