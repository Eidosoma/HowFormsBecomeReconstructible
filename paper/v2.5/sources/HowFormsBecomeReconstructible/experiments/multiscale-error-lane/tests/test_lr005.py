"""LR005's tests: python -m pytest tests/test_lr005.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr004 import design as L4D  # noqa: E402
from lr004 import sim as L4S  # noqa: E402
from lr005 import design as D  # noqa: E402
from lr005 import sim  # noqa: E402

BLOCK = 900766


def test_design():
    assert len(D.UNITS) == 6 and D.SITUATIONS[0] == "none" and set(D.COMMUNITY) <= set(D.ARMS)
    assert D.IDENTITIES["development"] == (910040, 910056) and len(D.digest()) == 64


def test_events():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    m, am = sim.patch(cases), sim.anchor_mask(cases)
    assert (m.sum((-2, -1)) == 64).all() and (am.sum((-2, -1)) == 256).all()
    ev = sim.event("memory", cases, V0, ema0, R0, T)
    assert np.array_equal(ev["r"], np.where(m, -R0, R0))
    ev = sim.event("shared", cases, V0, ema0, R0, T)
    assert (ev["r"][m] == 0).all() and not (ev["am"] & m).any()
    ev = sim.event("change", cases, V0, ema0, R0, T)
    assert np.array_equal(ev["target"], np.where(m, -T, T)) and np.array_equal(ev["old"], T)
    ev = sim.event("cue", cases, V0, ema0, R0, T)
    assert (((ev["aval"] != np.where(R0 > 0, 1.0, -1.0)) & am).sum((-2, -1)) == 64).all()


def test_reference_arms_equal_lr004():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    o5 = sim.run("li4", "none", cases, V0, ema0, R0, th, T, 1.0, 0.2, {300}, window=300, arms=("record+parity", "body"))
    o4 = L4S.run("li4", tuple(L4D.Cond(D.RATE, rep) for rep in ("record+parity", "body")), cases, V0, ema0, R0, th, T,
                 1.0, {300}, tag=D.TAG, window=300)
    for key in ("V", "r", "H", "W"):
        assert np.array_equal(o5[key][:2 * k], o4[key][:2 * k])


def test_cue_unread_and_community_rule():
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    blind = ("record+parity", "body", "vote2r")
    a = sim.run("dw", "none", cases, V0, ema0, R0, th, T, 0.0, 0.05, {300}, window=300, arms=blind)
    b = sim.run("dw", "cue", cases, V0, ema0, R0, th, T, 0.0, 0.05, {300}, window=300, arms=blind)
    for key in ("V", "r", "H", "W"):
        assert np.array_equal(a[key], b[key])
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    av = np.sign(Tq).copy()
    av[0, 8:16, 8:16] *= -1
    _, _, (zone, t) = sim.targets("community-s", Tq.copy(), Tq.copy(), None, {"am": amq, "aval": av},
                                  (np.zeros(Tq.shape, int), np.zeros(Tq.shape)))
    assert zone[0, 11, 11] and not zone[0, 0, 0] and t[0, 11, 11] == -np.sign(Tq[0, 11, 11])
