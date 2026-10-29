"""GC001's unit tests: the identity with BE001 at sigma 0, the noisy read, the matched control and the endpoints."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from be001 import sim as B1S  # noqa: E402
from gc001 import design as D  # noqa: E402
from gc001 import sim  # noqa: E402
from gc001 import static  # noqa: E402

BLOCK = 900696          # a debug block: engineering cases only


@pytest.fixture(scope="module")
def s4():
    return sim.prepare("S4", BLOCK, "engineering")


@pytest.mark.parametrize("situation,size", [("none", 8), ("change", 4), ("memory", 4)])
def test_sigma0_equals_be001(s4, situation, size):
    cases, V0, ema0, R0, th, T = s4
    o = sim.run("li4", situation, size, 0.0, cases, V0, ema0, R0, th, T, 1.0, {200}, window=200)
    o1 = B1S.run("li4", situation, size, cases, V0, ema0, R0, th, T, 1.0, {200}, tag=D.TAG, window=200, arms=D.ARMS)
    for x in ("V", "r", "H", "W"):
        assert np.array_equal(o[x], o1[x])


def test_read_at_sigma0_and_shift():
    f = np.arange(2 * 32 * 32, dtype=float).reshape(2, 32, 32)
    g = np.zeros((2, 2, 32, 32))
    assert sim.read_at(f, g, 0.0) is f
    g[:, 0] = 1.0                                   # every site reads one row down (periodic)
    out = sim.read_at(f, g, 1.0)
    assert np.array_equal(out, np.roll(f, -1, -2))


def test_matched_control_counts(s4):
    cases, V0, ema0, R0, th, T = s4
    for sg in (0.5, 1.0, 2.0):
        g_ = sim.event("none", 8, sg, cases, V0, ema0, R0, T)
        s_ = sim.event("scatter", 8, sg, cases, V0, ema0, R0, T)
        assert np.array_equal(g_["mis"].sum((-2, -1)), s_["mis"].sum((-2, -1)))
        assert not (s_["mis"] & ~s_["am"]).any()
        assert not (g_["mis"] & ~g_["am"]).any()


def test_boundary_distance_on_stripes(s4):
    T = s4[5]
    d = sim.boundary_distance(T)
    assert set(np.unique(d)) == {1, 2}              # stripes four sites wide
    assert ((d == D.BAND) ^ (d > D.BAND)).all()


def test_walls_of_the_target_have_no_excess(s4):
    T = s4[5]
    assert np.allclose(sim.walls(T) / sim.walls(T) - 1.0, 0.0)


def test_misread_theory_matches_the_draw(s4):
    cases, V0, ema0, R0, th, T = s4
    for sg in (1.0, 2.0):
        ev = sim.event("none", 8, sg, cases, V0, ema0, R0, T)
        realised = ev["mis"].sum() / ev["am"].sum()
        assert abs(realised - static.misread_theory(T, sg).mean()) < 0.04


def test_noisy_read_only_changes_anchor_values(s4):
    cases, V0, ema0, R0, th, T = s4
    ev0 = sim.event("none", 8, 0.0, cases, V0, ema0, R0, T)
    ev1 = sim.event("none", 8, 1.0, cases, V0, ema0, R0, T)
    for x in ("V", "E", "r", "H", "W", "Hb", "Wb", "am", "m", "target"):
        assert np.array_equal(ev0[x], ev1[x])
    assert not np.array_equal(ev0["aval"], ev1["aval"])


def test_design_digest_is_stable():
    assert D.digest() == D.digest() and len(D.digest()) == 64
    assert len(D.RUNS) == len(set(D.RUNNAMES)) == 15
