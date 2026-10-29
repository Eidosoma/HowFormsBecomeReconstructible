"""BE001's tests: python -m pytest tests/test_be001.py"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be001 import design as D  # noqa: E402
from be001 import sim  # noqa: E402
from lr005 import sim as L5S  # noqa: E402

BLOCK = 900796


def test_design():
    assert len(D.UNITS) == 6 and len(D.RUNS) == 9 and set(D.BIO) <= set(D.ARMS)
    assert D.IDENTITIES["development"] == (910120, 910136) and len(D.digest()) == 64


def test_patches_and_events():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    for z in D.SIZES:
        assert (sim.patch(cases, z).sum((-2, -1)) == z * z).all()
    assert np.array_equal(sim.patch(cases, 8, D.TAG), L5S.patch(cases, D.TAG))
    for s in ("none", "cue", "memory", "change", "shared"):
        a, b = sim.event(s, 8, cases, V0, ema0, R0, T), L5S.event(s, cases, V0, ema0, R0, T, D.TAG)
        for key in ("V", "r", "H", "W", "Hb", "Wb", "aval", "am", "m", "target"):
            assert np.array_equal(a[key], b[key])


def test_shared_arms_equal_lr005():
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    arms = ("cue", "community-s", "community-c")
    for s in ("change", "memory"):
        a = sim.run("li4", s, 8, cases, V0, ema0, R0, th, T, 1.0, {300}, window=300, arms=arms)
        b = L5S.run("li4", s, cases, V0, ema0, R0, th, T, 1.0, D.GAIN, {300}, tag=D.TAG, window=300, arms=arms)
        for key in ("V", "r", "H", "W"):
            assert np.array_equal(a[key], b[key])


def test_cable_and_trigger():
    pt = np.zeros((1, D.SIDE, D.SIDE))
    pt[0, 3, 4] = 1.0
    for lam in (1.0, 2.0, 3.0):
        v = np.real(np.fft.ifft2(np.fft.fft2(pt) / sim.cable_kernel(lam)))
        assert abs(v.sum() - 1.0) < 1e-12 and v[0, 3, 4] == v.max()
        g = np.full(pt.shape, lam ** 2)
        assert np.abs(sim.cable_cg(pt, g, g, np.zeros_like(pt)) - v).max() < 1e-9
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    av = np.sign(Tq).copy()
    av[0, 8:16, 8:16] *= -1
    st = {"v": np.zeros(Tq.shape), "s": np.zeros(Tq.shape), "sgn": np.zeros(Tq.shape), "kernel": sim.cable_kernel(2.0)}
    _, _, (c, t) = sim.bio_targets("bio-2", Tq.copy(), Tq.copy(), {"am": amq, "aval": av}, st, np.zeros(Tq.shape))
    assert c[0, 11, 11] and not c[0, 0, 0] and t[0, 11, 11] == -np.sign(Tq[0, 11, 11])


def test_unreachable_threshold_is_the_cue_arm():
    saved = D.BIO
    try:
        D.BIO = copy.deepcopy(saved)
        D.BIO["bio-1"]["theta"] = 1e300
        cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
        o = sim.run("dw", "change", 8, cases, V0, ema0, R0, th, T, 0.0, {300}, window=300, arms=("cue", "bio-1"))
        k = len(cases)
        for key in ("V", "r", "H", "W"):
            assert np.array_equal(o[key][:k], o[key][k:])
    finally:
        D.BIO = saved
