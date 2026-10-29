"""BE005's tests: python -m pytest tests/test_be005.py"""
from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be001 import sim as B1S  # noqa: E402
from be004 import sim as B4S  # noqa: E402
from be005 import design as D  # noqa: E402
from be005 import sim  # noqa: E402
from lr005 import sim as L5S  # noqa: E402

BLOCK = 900626
W = 150


def prepared(pattern="S4"):
    return sim.prepare(pattern, BLOCK, "engineering")


def test_design():
    assert len(D.UNITS) == 6 and len(D.tasks()) == 12 and len(D.RUNS) == 15 and len(D.digest()) == 64
    assert len(D.SIGNAL_ARMS) == 27 and len(set(D.RUNNAMES)) == len(D.RUNS)
    assert D.IDENTITIES["development"] == (910280, 910296)
    assert all(900000 <= lo < hi <= 901000 for lo, hi in (D.PROBE_BLOCKS, D.IDENTITIES["preflight"], D.DEBUG_BLOCKS))
    assert abs(D.t_star(0.01) - math.log(1.8) / -math.log(0.99)) < 1e-12 and 58 < D.t_star(0.01) < 59
    for e in D.ETAS:                                    # each dial-e sits at every m, once, in the run of its delay
        for m in D.MULTS:
            rn, arm = D.where(e, m)
            run = dict((D.run_name(*x), x) for x in D.RUNS)[rn]
            assert arm in run[3] and run[2] == int(round(m * D.t_star(e)))
    assert sum(len(x[3]) for x in D.RUNS if x[0] == "memory" and x[2]) == len(D.ETAS) * (len(D.MULTS) - 1)
    assert D.SIGNAL_ARMS["dial-e0.01"] == D.BASE == D.SIGNAL_ARMS["dial-tv1"]
    assert D.SIGNAL_ARMS["never-tv100"]["never"] and D.SIGNAL_ARMS["dial-t10-tv10"]["dur"] == 10


def test_defaults_equal_be004():
    """At the defaults BE005's arms are BE004's bit for bit (prompt, late, brief and flicker)."""
    cases, V0, ema0, R0, th, T = prepared("LB")
    k = len(cases)
    for body, situation, delay, mine, theirs in (
            ("dw", "memory", 0, ("cue", "bio-3", "dial-e0.01", "never-e0.01"), ("cue", "bio-3", "dial", "bio-3")),
            ("li4", "change", 0, ("dial-t1-tv1", "dial-f0.25-tv1"), ("dial-t1", "dial-f0.25")),
            ("dw", "memory", 29, ("dial-e0.01",), ("dial",))):
        a = sim.run(body, situation, 4, delay, mine, cases, V0, ema0, R0, th, T, 1.0, {W}, window=W)
        b = B4S.run(body, situation, 4, delay, theirs, cases, V0, ema0, R0, th, T, 1.0, {W}, tag=D.TAG, window=W)
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(a[x], b[x])
        assert a["V"].shape[0] == len(mine) * k


def test_never_is_the_dial_without_its_signal():
    cases, V0, ema0, R0, th, T = prepared()
    k = len(cases)
    arms = ("never-e0.02", "dial-e0.02", "never-tv100", "dial-tv100", "dial-f0.5-tv100")
    o = sim.run("dw", "memory", 4, 0, arms, cases, V0, ema0, R0, th, T, 0.0, {W}, window=W, on_window=(0, -1))
    for j in ((0, 1), (2, 3), (2, 4)):
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(o[x][j[0] * k:(j[0] + 1) * k], o[x][j[1] * k:(j[1] + 1) * k])


def test_eta_a_changes_only_the_arbiter_cells_bonds():
    """With no arbiter cells (an intact sheet with every anchor agreeing) dial-e0.005 equals dial-e0.01; after a memory
    damage it differs, and its sensors are repaired later than dial-e0.02's."""
    cases, V0, ema0, R0, th, T = prepared("F0")
    k = len(cases)
    o = sim.run("li4", "memory", 4, 300, ("dial-e0.005", "dial-e0.01", "dial-e0.02"), cases, V0, ema0, R0, th, T, 0.0,
                {40, 80}, window=81)
    slow, mid, fast = (o["n_anc_ok"][1][j * k:(j + 1) * k].sum() for j in range(3))
    assert slow <= mid <= fast and fast > slow


def test_bond_clock():
    for e in D.ETAS:
        hb, n = D.STRENGTH0, 0
        while hb > 0:
            hb, n = hb + e * (-1.0 - hb), n + 1
        assert n == math.ceil(D.t_star(e))


def test_membrane_relaxes():
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    mq = np.zeros(Tq.shape, bool)
    mq[0, 12:16, 12:16] = True
    P = {"am": amq, "aval": np.sign(Tq)}
    st = sim.new_state(1, mq, v0=np.ones(Tq.shape))
    for _ in range(30):
        sim.sig_targets("dial-tv10", Tq.copy(), Tq.copy(), P, st, False)
    v_star = np.real(np.fft.ifft2(np.fft.fft2(D.KAPPA * np.where(amq, np.sign(Tq), 0.0) * L5S.vote_sign(Tq)) / B1S.cable_kernel(3.0)))
    assert np.abs(st["v"] - (v_star + (1.0 - v_star) * 0.9 ** 30)).max() < 1e-12
    st1 = sim.new_state(1, mq, v0=np.ones(Tq.shape))
    sim.sig_targets("dial-tv1", Tq.copy(), Tq.copy(), P, st1, False)
    assert np.array_equal(st1["v"], v_star)


def test_slow_membrane_delays_triggering():
    """A 1-update signal triggers the patch at tau 1 and not at tau 100; the steady signal eventually triggers both."""
    cases, V0, ema0, R0, th, T = prepared()
    k = len(cases)
    o = sim.run("dw", "change", 4, 0, ("dial-t1-tv1", "dial-t1-tv100", "dial-tv100"), cases, V0, ema0, R0, th, T, 0.0,
                {W}, window=600)
    hit = o["hit"].reshape(3, k).mean(1)
    assert hit[0] > 0.2 and hit[1] < 0.01 and hit[2] > 0.2


def test_pre_event_potential():
    cases, V0, ema0, R0, th, T = prepared()
    am = L5S.anchor_mask(cases, D.TAG)
    v = sim.pre_event_potential(R0, am)
    assert v.shape == R0.shape and abs(float(v.mean()) - 1.0) < 0.1     # kappa rho = 1: about 1 everywhere


def test_endpoints():
    cases, V0, ema0, R0, th, T = prepared()
    k = len(cases)
    arms = ("cue", "bio-3", "dial-e0.02", "never-e0.02", "dial-t10-tv10")
    o = sim.run("dw", "memory", 4, 20, arms, cases, V0, ema0, R0, th, T, 0.0, {50, W}, window=W)
    for e in sim.ENDS:
        if e != "r_in_old":
            assert o[e].shape == (2, len(arms) * k)
    for e in ("onset", "hit", "anc_on"):
        assert o[e].shape == (len(arms) * k,)
    on, hit, anc = (o[e].reshape(len(arms), k) for e in ("onset", "hit", "anc_on"))
    assert (on[:2] == -1).all() and (hit[:2] == -1).all() and (anc[:2] == -1).all()
    assert (on[3] == -1).all() and ((on[2] >= 0) & (on[2] <= 1)).all() and (anc[2:] >= 0).all()
    assert o["signal_updates"]["never-e0.02"] == 0 and o["signal_updates"]["dial-e0.02"] == (W - 20) * k
