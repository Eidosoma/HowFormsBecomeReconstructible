"""LR004's tests: python -m pytest tests/test_lr004.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr001 import sim as S1  # noqa: E402
from lr003 import design as L3D  # noqa: E402
from lr003 import sim as L3S  # noqa: E402
from lr004 import design as D  # noqa: E402
from lr004 import sim  # noqa: E402
from msegrid.core import bonds  # noqa: E402

BLOCK = 900756
TQ = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)[None]
HQ, WQ = S1.edges_from(bonds(TQ, True))
ZERO, INF = np.zeros_like(TQ), np.full((1, 1, 1), np.inf)


def rec(r):
    return HQ.copy(), WQ.copy(), 0.8 * HQ, 0.8 * WQ, r


def pq(src, two, vote, amask):
    return {"cut": INF, "src": np.array([D.SOURCES[src]])[:, None, None], "par": np.zeros((1, 1, 1), bool),
            "two_idx": np.array([0]) if two else np.array([], int), "cut_two": INF,
            "vote_two": np.full((1 if two else 0, 1, 1), vote), "amask": amask}


def test_design_conditions():
    names = [c.name for c in D.CONDS]
    assert len(names) == len(set(names)) == len(D.RATES) * len(D.REPAIRS)
    c = D.Cond(0.001, "anchors16")
    assert (c.source, c.density, c.two, c.parity) == ("anchors", 16, False, False)
    assert D.Cond(0.0, "vote").two and D.Cond(0.0, "pair").two and not D.Cond(0.0, "site").two
    assert all(D.SOURCES[k] == v for k, v in L3D.SOURCES.items())


def test_vote_pair_and_anchor_rules():
    Vf = 1.2 * TQ.copy()
    Vf[0, :, 2] *= -1
    for rB, side_with in ((1.2 * TQ, "records"), (Vf.copy(), "body")):
        A, B, _ = sim.relations(rec(1.2 * TQ), rec(rB), ZERO, ZERO, ZERO, ZERO, Vf, pq("vote", True, True, np.zeros_like(TQ, bool)), np.sign(TQ))
        sV, sA = sim.signs(Vf)[0], sim.signs(A[4])[0]
        m = np.sign(sV + sA + sim.signs(B[4])[0])
        assert np.array_equal(m, sA if side_with == "records" else sV)
        assert np.array_equal(A[2], 0.8 * HQ + D.ETA * (m - 0.8 * HQ))
    A, B, _ = sim.relations(rec(1.2 * TQ), rec(Vf.copy()), ZERO, ZERO, ZERO, ZERO, 1.2 * TQ, pq("pair", True, False, np.zeros_like(TQ, bool)), np.sign(TQ))
    dis = sim.signs(A[4])[0] != sim.signs(B[4])[0]
    assert dis.any() and np.array_equal(A[2][dis], (0.8 * HQ)[dis])
    am = np.zeros_like(TQ, bool)
    am[0, 5, 2] = True
    Vd = 1.2 * TQ.copy()
    Vd[0, 5, 2] *= -1
    Vd[0, 9, 2] *= -1
    aval = np.sign(TQ).copy()
    aval[0, 5, 2] *= -1
    A, _, op = sim.relations(rec(1.2 * TQ), None, ZERO, ZERO, None, None, Vd, pq("anchors", False, False, am), aval)
    tq = np.sign(TQ).copy()
    tq[0, 5, 2] *= -1
    assert np.array_equal(A[2], 0.8 * HQ + D.ETA * (tq * np.roll(tq, -1, -1) - 0.8 * HQ))
    assert float(op[0]) == 1 / (D.SIDE * D.SIDE)


def test_reference_teachers_equal_lr003():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    reps = ("record+parity", "body", "site")
    c4 = tuple(D.Cond(r, rep) for r in (0.003, 0.03) for rep in reps)
    c3 = tuple(L3D.Cond(r, rep) for r in (0.003, 0.03) for rep in reps)
    o4 = sim.run("li4", c4, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, window=300)
    o3 = L3S.run("li4", c3, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, window=300)
    for key in ("V", "r", "H", "W"):
        assert np.array_equal(o4[key], o3[key])


def test_aliases_without_noise():
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    conds = tuple(D.Cond(0.0, rep) for rep in ("pair", "vote", "anchors4", "anchors16"))
    o = sim.run("li4", conds, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, window=300)
    k = len(cases)
    for key in ("V", "r", "H", "W"):
        assert np.array_equal(o[key][:k], o[key][k:2 * k])
        assert np.array_equal(o[key][2 * k:3 * k], o[key][3 * k:])
    H0 = S1.edges_from(bonds(R0, True))[0]
    assert np.array_equal(o["H"][k:2 * k], H0)
