"""BR002 unit checks: equivalence with BR001's simulator, the gauge identity, wall geometry, killed bonds and
window damage."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from br001 import design as D1
from br001 import sim as S1
from br002 import design as D
from br002 import sim
from mse.native import neighbours

BLOCK = [900830]          # BR002's debug block (engineering)


def test_design_shape():
    for p, v in D.PANELS.items():
        names = [a.name for a in v["arms"]]
        assert len(names) == len(set(names))
        assert len({c.name for c in v["conditions"]}) == len(v["conditions"])
        for panel, fam, a, b in D.CONTRASTS:
            if panel == p:
                assert a in names and b in names, (p, a, b)
    for s, places in D.PLACES.items():
        for pl in places:
            assert pl == "cross" or 2 * int(pl[1:]) + s <= D.DOMAIN


def test_equals_br001_simulator_with_new_elements_off():
    """Panel P and L arms and conditions of BR001 against br002.simulate on BR001's own prepared state."""
    name = D1.regime("F0", 0.3)
    cases, s0, th, p, conserved, T, Tf = S1.prepare(name, [900978], "engineering")
    k = len(cases)
    Z = S1.draws(cases, "future", updates=D1.WINDOW)
    XI = S1.draws(cases, "record-noise", updates=D1.WINDOW)
    cal = {"mismatch": 2.33, "surprise": 0.24}
    pairs = [(D1.COND_P[i], D.COND_C[j]) for i, j in ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (6, 6))]
    tau = S1.onsets(cases, "random")
    for a1, a2 in (("write_none", "none"), ("write_always", "always"), ("write_duration", "duration"),
                   ("write_tags", "tags"), ("write_phase", "phase")):
        c1, c2 = tuple(x for x, _ in pairs), tuple(y for _, y in pairs)
        masks = [S1.patch_masks(cases, c.size) if c.size else None for c in c1]
        v1, e1, r1, w1 = S1.simulate(D1.ARM["P"][a1], c1, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, True, T, Tf, tau,
                                     masks, [None] * len(c1), cal)
        v2, e2, r2, w2 = sim.simulate(D.ARM["C"][a2], c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, True, T, Tf, tau,
                                      masks, [None] * len(c2), [None] * len(c2), cal)
        assert np.array_equal(v1, v2) and np.array_equal(r1, r2) and np.array_equal(w1, w2), a1
    c1 = (D1.COND_L[0], D1.COND_L[2])            # sham, both-4x4
    c2 = (D.COND_R[0], D.COND_R[2])
    masks = [None, S1.patch_masks(cases, 4)]
    one = np.ones(k, int)
    for a in ("static", "self", "multi", "protected"):
        v1, _, r1, _ = S1.simulate(D1.ARM["L"][a], c1, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, True, T, Tf, one,
                                   masks, [None, None])
        v2, _, r2, _ = sim.simulate(D.ARM["R"][a], c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, True, T, Tf, one,
                                    masks, [None, None], [None, None])
        assert np.array_equal(v1, v2) and np.array_equal(r1, r2), a


def test_bond_sum_is_the_gauge_of_consensus():
    rng = np.random.default_rng(0)
    R0 = rng.standard_normal((3, 16, 16))
    r = rng.standard_normal((3, 16, 16))
    s = np.where(R0 >= 0, 1.0, -1.0)
    assert np.array_equal(sim.bond_sum(sim.bonds(R0, False), r), neighbours(r))
    assert np.array_equal(sim.bond_sum(sim.bonds(R0, True), r), s * neighbours(s * r))


def test_geometry_masks_sit_where_declared():
    cases, *_ = sim.prepare(D.regime("F0", 0.1), BLOCK, "engineering")
    T = D.TEMPLATES["F0"]
    for size, places in D.PLACES.items():
        for pl in places:
            m = sim.geometry_masks(cases, size, pl)
            assert (m.sum((-2, -1)) == size * size).all()
            for i, c in enumerate(cases):
                inside = T[c.message][m[i]]
                across = np.where(m[i].any(0 if c.message % 2 == 0 else 1))[0]
                if pl == "cross":
                    assert (inside > 0).any() and (inside < 0).any()
                    assert {7, 8} <= set(across) or {15, 0} <= set(across)
                else:
                    assert (inside > 0).all() or (inside < 0).all()
                    dist = min(min(x % D.DOMAIN, D.DOMAIN - 1 - x % D.DOMAIN) for x in across)
                    assert dist == int(pl[1:]), (size, pl, i)


def test_killed_bonds():
    R0 = np.where(np.random.default_rng(1).standard_normal((1, 16, 16)) > 0, 1.2, -1.2)
    J = sim.bonds(R0, True)
    kill = np.zeros((1, 16, 16), bool)
    kill[0, 4:8, 4:8] = True
    for relink, lost in ((False, 0.0), (True, 1.0)):
        K = sim.kill_bonds(J, kill, relink)
        for d, (sh, ax) in enumerate(sim.SHIFTS):
            both = kill & np.roll(kill, sh, ax)
            assert (K[d][both] == lost).all() and np.array_equal(K[d][~both], J[d][~both])
    K = sim.kill_bonds(J, kill, False)
    assert np.array_equal(K[0], np.roll(K[1], 1, -2))          # the bond (i, i-1) is the bond (i-1, i)


def test_window_damage_is_the_same_damage_delayed():
    """Without window writing, a scar inside an open window equals the same scar WINDOW_DELAY later."""
    cases, s0, th, p, conserved, T, Tf = sim.prepare(D.regime("F0", 0.3, "o"), BLOCK, "engineering")
    k = len(cases)
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    tau = sim.onsets(cases, "random")
    m = [sim.patch_masks(cases, 6)]
    cal = {"mismatch": 2.86, "surprise": 0.25}
    for a in ("none", "tags+h", "duration"):
        x = sim.simulate(D.ARM["C"][a], (D.COND_C[7],), k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, False, T, Tf, tau, m,
                         [None], [None], cal)
        y = sim.simulate(D.ARM["C"][a], (D.COND_C[2],), k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, False, T, Tf,
                         tau + D.WINDOW_DELAY, m, [None], [None], cal)
        assert np.array_equal(x[0], y[0]) and np.array_equal(x[2], y[2]), a


def test_turnover_and_kill_draws_are_shared_and_sized():
    cases, *_ = sim.prepare(D.regime("F0", 0.1), BLOCK, "engineering")
    a = sim.turnover_events(cases, 1e-3, D.WINDOW)
    b = sim.turnover_events(cases, 1e-3, D.WINDOW)
    assert all(np.array_equal(x[0], y[0]) and np.array_equal(x[1], y[1]) for x, y in zip(a, b))
    n = np.mean([len(x[0]) for x in a])
    assert 0.6 * 1e-3 * D.WINDOW * 256 < n < 1.4 * 1e-3 * D.WINDOW * 256
    assert np.array_equal(sim.newborn(cases, 4), sim.newborn(cases, 4))
    assert not np.array_equal(sim.newborn(cases, 4), sim.newborn(cases, 8))
