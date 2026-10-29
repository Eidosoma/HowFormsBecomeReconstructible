"""BE002's tests: python -m pytest tests/test_be002.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be001 import sim as B1S  # noqa: E402
from be002 import design as D  # noqa: E402
from be002 import sim  # noqa: E402

BLOCK = 900646
REF_ARMS = ("cue", "bio-1", "bio-1.5", "bio-3")


def test_design():
    assert len(D.UNITS) == 6 and len(D.RUNS) == 11 and len(D.RUNNAMES) == len(set(D.RUNNAMES))
    assert D.SIGNALS["sig"] == (1, 1000) and D.SIGNALS["late"] == (1001, 2000)
    assert set(D.REF) <= set(D.ARMS) and set(D.SIGNAL_ARMS) <= set(D.ARMS)
    assert D.IDENTITIES["development"] == (910140, 910156) and len(D.digest()) == 64
    assert D.PROBE_BLOCKS == (900640, 900644) and D.DEBUG_BLOCKS == (900646, 900648)


def test_footprint_and_conductances():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    for z in (4, 8):
        m = sim.patch(cases, z, D.TAG)
        fp = sim.footprint(m)
        side = z + 2 * D.SIG["d"]
        assert (fp.sum((-2, -1)) == side * side).all() and (fp | ~m).all()
        gH, gW = sim.conductances(fp)
        closed = side * (side + 1)                        # bonds with an end in a side x side square, each direction
        assert ((gH == 1.0).sum((-2, -1)) == closed).all() and ((gW == 1.0).sum((-2, -1)) == closed).all()
        assert set(np.unique(gH)) == {1.0, 9.0}


def test_solvers():
    rng = np.random.default_rng(1)
    cur = rng.standard_normal((2, D.SIDE, D.SIDE))
    for lam in (1.0, 1.5, 3.0):
        g = np.full(cur.shape, lam ** 2)
        v_fft = np.real(np.fft.ifft2(np.fft.fft2(cur) / B1S.cable_kernel(lam)))
        assert np.abs(sim.solve(sim.factor(g, g), cur) - v_fft).max() < 1e-9
    m = np.zeros((2, D.SIDE, D.SIDE), bool)
    m[0, 3:7, 5:9] = True
    m[1, 30:32, 0:2] = True
    m[1, 0:2, 30:32] = True
    gH, gW = sim.conductances(sim.footprint(m))
    v_lu = sim.solve(sim.factor(gH, gW), cur)
    v_cg = B1S.cable_cg(cur, gH, gW, np.zeros_like(cur))
    assert np.abs(v_lu - v_cg).max() < 1e-9
    pt = np.zeros((2, D.SIDE, D.SIDE))
    pt[:, 4, 6] = 1.0
    assert np.abs(sim.solve(sim.factor(gH, gW), pt).sum((-2, -1)) - 1.0 / D.G_LEAK).max() < 1e-12


def test_reference_arms_equal_be001():
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    for s, z, sig in (("change", 4, "sig"), ("memory", 4, ""), ("cue", 8, "sig")):
        a = sim.run("li4", s, z, sig, cases, V0, ema0, R0, th, T, 1.0, {300}, window=300, arms=REF_ARMS)
        b = B1S.run("li4", s, z, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, window=300, arms=REF_ARMS)
        for key in ("V", "r", "H", "W"):
            assert np.array_equal(a[key], b[key])


def test_aliases_without_signal():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    for sig, on in (("", None), ("sig", (1, 0)), ("late", None)):           # no signal, an empty one, one after the window
        o = sim.run("dw", "change", 4, sig, cases, V0, ema0, R0, th, T, 0.0, {300}, window=300, on_window=on)
        for arm, alias in D.ALIAS.items():
            i, j = D.ARMS.index(arm), D.ARMS.index(alias)
            for key in ("V", "r", "H", "W"):
                assert np.array_equal(o[key][i * k:(i + 1) * k], o[key][j * k:(j + 1) * k]), (arm, key, sig)


def test_permit_commits_only_in_the_footprint():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    o = sim.run("li4", "cue", 8, "sig", cases, V0, ema0, R0, th, T, 0.0, {400}, window=400, on_window=(1, 200))
    i = D.ARMS.index("permit-local")
    assert float(o["opened_out"][i * k:(i + 1) * k].max()) == 0.0
    j = D.ARMS.index("dial-global")
    assert float(o["opened_out"][j * k:(j + 1) * k].sum()) > 0.0


def test_local_dial_triggers_a_small_group():
    """A coherent 4 x 4 disagreement inside a signalled footprint triggers dial-local at the patch centre; bio-3 nowhere."""
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True                               # a quarter of the cells, as the lane's anchors
    av = np.sign(Tq).copy()
    m = np.zeros(Tq.shape, bool)
    m[0, 12:16, 12:16] = True
    av[m] *= -1
    P = {"am": amq, "aval": av}
    st = sim.new_state("dial-local", 1, sim.footprint(m))
    _, _, (c, t) = sim.sig_targets("dial-local", Tq.copy(), Tq.copy(), P, st, True)
    assert c[0, 13, 13] and c[0, 14, 14] and not c[0, 0, 0] and t[0, 13, 13] == -np.sign(Tq[0, 13, 13])
    st3 = {"v": np.zeros(Tq.shape), "s": np.zeros(Tq.shape), "sgn": np.zeros(Tq.shape), "kernel": B1S.cable_kernel(3.0)}
    _, _, (c3, _) = B1S.bio_targets("bio-3", Tq.copy(), Tq.copy(), P, st3, np.zeros(Tq.shape))
    assert not c3.any()
    st_off = sim.new_state("dial-local", 1, sim.footprint(m))
    _, _, (c_off, _) = sim.sig_targets("dial-local", Tq.copy(), Tq.copy(), P, st_off, False)
    assert not c_off.any()
