"""DL001's engine tests: python -m pytest tests/test_dl001.py"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from br001.sim import body_step  # noqa: E402
from dl001 import design as D  # noqa: E402
from dl001 import sim  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import NATIVE  # noqa: E402


def test_alpha0_equals_br001_open_body():
    g = np.random.default_rng(1)
    for side in (16, 32):
        V, ema, r, th = (g.standard_normal((3, side, side)) for _ in range(4))
        p = replace(NATIVE, sigma=0.3)
        a, b = (V.copy(), ema.copy()), (V.copy(), ema.copy())
        for _ in range(100):
            z = g.standard_normal((3, side, side))
            a = sim.body(a[0], a[1], r, th, z, p, 0.2, 0.0, None)[:2]
            b = body_step(b[0], b[1], r, th, z, p, False, 0.2)[:2]
        assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_inhibitor_solves_the_screened_equation():
    g = np.random.default_rng(2)
    for side, L in ((32, 2.0), (32, 4.0), (64, 16.0)):
        V = g.standard_normal((side, side))
        w = sim.inhibit(V, sim.ghat(side, L))
        lap = sum(np.roll(w, s, a) for s in (1, -1) for a in (0, 1)) - 4 * w
        assert np.abs(w - L * L * lap - V).max() < 1e-10


def test_alpha_for_puts_the_fastest_mode_at_kstar():
    k = np.linspace(1e-4, 8.0, 800001)
    for L, kstar in ((2.0, D.K8), (4.0, D.K8), (16.0, D.K16)):
        a = D.alpha_for(L, kstar)
        growth = 1 - k / 4 - a / (1 + L * L * k)
        assert abs(k[growth.argmax()] - kstar) < 1e-3


def test_templates_and_spacing():
    s4 = sim.template("S4", 0, 32, 910700)
    assert s4.mean() == 0 and np.array_equal(s4, np.roll(s4, 8, 1)) and np.array_equal(s4, -np.roll(s4, 4, 1))
    assert abs(sim.spacing(s4[None])[0] - 8.0) < 1e-9
    s8 = sim.template("S8", 1, 32, 910700)
    assert 12.0 < sim.spacing(s8[None])[0] < 16.0          # the third harmonic of period 16 lies inside the band
    for kind in range(4):
        for fam in D.PATTERNS:
            t = sim.template(fam, kind, 32, 910700)
            assert set(np.unique(t)) == {-1.0, 1.0}


def test_wounds_and_determinism():
    cases = enrol([900874], D.MESSAGES, D.PARENTS, "engineering")
    for size in (4, 8, 12):
        m = sim.wound_mask(cases, size, 32)
        assert (m.sum((-2, -1)) == size * size).all()
    V = sim.newborn_sheet(cases, 32)
    th = np.zeros_like(V)
    T = np.stack([sim.template("S4", c.message, 32, c.block) for c in cases])
    runs = [sim.run("li4", V.copy(), V.copy(), np.zeros_like(V), np.zeros(len(cases)), th, T, cases, 0.1, 60, {60})
            for _ in range(2)]
    assert np.array_equal(runs[0]["final"], runs[1]["final"])
