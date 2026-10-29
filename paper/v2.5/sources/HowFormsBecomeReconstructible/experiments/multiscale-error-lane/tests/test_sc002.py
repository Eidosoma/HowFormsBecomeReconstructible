"""SC002's tests: python -m pytest tests/test_sc002.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
from scipy.sparse.linalg import splu

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be001 import sim as B1S  # noqa: E402
from cellpop import core as C  # noqa: E402
from sc002 import design as D  # noqa: E402
from sc002 import sim  # noqa: E402
from sc002.cable import Cable  # noqa: E402

BLOCK = 900656


def test_design():
    assert D.UNITS == ("S4_t0", "F0_t0") and len(D.RUNS) == 14 and set(D.JUNCTIONS) < set(D.ARMS)
    assert D.IDENTITIES["development"] == (910160, 910176) and len(D.digest()) == 64
    assert all(lo >= 900650 and hi <= 900658 for lo, hi in (D.PROBE_BLOCKS, D.IDENTITIES["preflight"], D.DEBUG_BLOCKS))


def test_full_sheet_equals_be001():
    """No turnover, no wound, every contact mature: the cue arm and an instant arm at lam are be001's cue and bio-lam
    arms bit for bit, and the maturing arms equal inst-3."""
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    for body, s in (("li4", "change"), ("dw", "cue"), ("li4", "memory")):
        a = sim.run(body, 0.0, s, 8, cases, V0, ema0, R0, th, T, 0.0, {200}, window=200,
                    arms=("cue", "inst-1.5", "inst-3", "mat-300", "mat-1000"))
        b = B1S.run(body, s, 8, cases, V0, ema0, R0, th, T, 0.0, {200}, tag=D.TAG, window=200,
                    arms=("cue", "bio-1.5", "bio-3"))
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(a[x][:3 * k], b[x])
            assert np.array_equal(a[x][3 * k:4 * k], a[x][2 * k:3 * k]) and np.array_equal(a[x][4 * k:], a[x][2 * k:3 * k])
        assert a["solvers"]["mat-1000"] == {"fft": 200, "cg": 0}


def test_cable_solver():
    rng = np.random.default_rng(5)
    k = 3
    I = 4.0 * rng.choice([-1.0, 0.0, 0.0, 1.0], (k, D.SIDE, D.SIDE))
    cab = Cable(k)
    for lam in (1.5, 3.0):
        g = np.full(I.shape, lam ** 2)
        v_fft = np.real(np.fft.ifft2(np.fft.fft2(I) / B1S.cable_kernel(lam)))
        assert np.abs(cab.solve(I, g, g, np.zeros_like(I))[0] - v_fft).max() < 1e-9
    occ = rng.random(I.shape) > 0.1
    ch, cw = C.contacts(occ)
    gH, gW = np.where(ch, 9.0 * rng.random(I.shape), 0.0), np.where(cw, 9.0 * rng.random(I.shape), 0.0)
    Iw = np.where(occ, I, 0.0)
    v, _ = cab.solve(Iw, gH, gW, np.zeros_like(I))
    A, _ = cab.matrix(gH, gW)
    assert abs(A - A.T).max() == 0.0
    ref = splu(A.tocsc()).solve(Iw.reshape(-1)).reshape(I.shape)
    assert np.abs(v - ref).max() < 1e-9 and (v[~occ] == 0.0).all()


def test_isolated_newborn_reads_its_own_cue():
    """A cell whose contacts are all new has no coupling: an anchored cell disagreeing with its cue sits at
    -kappa / g_l and triggers, while with instant junctions its neighbours' agreeing anchors outvote it."""
    ages = np.full((1, D.SIDE, D.SIDE), np.inf)
    ages[0, 10, 10] = 0.0
    aH, aW = sim.contact_ages(ages)
    occ = np.ones(ages.shape, bool)
    gH, gW = sim.conductance("mat-300", aH, aW, occ)
    assert gH[0, 10, 10] == gH[0, 10, 9] == gW[0, 10, 10] == gW[0, 9, 10] == 0.0 and gH[0, 0, 0] == 9.0
    rec = np.ones(ages.shape)
    ca = np.zeros(ages.shape)
    ca[0, ::2, ::2] = 1.0                                   # a quarter of the sites anchored, agreeing
    ca[0, 10, 10] = -1.0                                    # but the newborn's cue disagrees with its record
    state = {"v": np.zeros(ages.shape), "s": np.zeros(ages.shape), "sgn": np.zeros(ages.shape),
             "kernel": B1S.cable_kernel(3.0), "cable": Cable(1)}
    _, _, (committed, t) = sim.detect("mat-300", rec, rec, ca, gH, gW, occ, state)
    assert abs(state["v"][0, 10, 10] + D.KAPPA / D.G_LEAK) < 1e-9
    assert committed[0, 10, 10] and t[0, 10, 10] == -1.0 and committed.sum() == 1
    gH3, gW3 = sim.conductance("inst-3", aH, aW, occ)
    state3 = dict(state, v=np.zeros(ages.shape), s=np.zeros(ages.shape), sgn=np.zeros(ages.shape))
    _, _, (c3, _) = sim.detect("inst-3", rec, rec, ca, gH3, gW3, occ, state3)
    assert not c3.any() and state3["v"][0, 10, 10] > 0.5


def test_stationary_ages():
    cases = sim.prepare("S4", BLOCK, "engineering")[0]
    a = sim.cell_ages(cases, 1e-3)
    assert abs(a.mean() / 1000.0 - 1.0) < 0.05
    e = np.stack([sim.address(D.TAG, *c.key(), "ages").standard_exponential((D.SIDE, D.SIDE)) for c in cases])
    assert np.array_equal(sim.cell_ages(cases, 2.5e-4), np.floor(e / 2.5e-4)) and np.isinf(sim.cell_ages(cases, 0.0)).all()
    aH, aW = sim.contact_ages(a)
    assert np.array_equal(aH, np.minimum(a, np.roll(a, -1, -1))) and np.array_equal(aW, np.minimum(a, np.roll(a, -1, -2)))


def test_population_bookkeeping():
    """Under turnover and in a regrowing wound: one population history for every arm; empty sites hold nothing (values,
    bonds, commitment, potential); a contact touching a newborn starts at age 0, every other contact ages by one; no
    conductance across an empty site."""
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    k = len(cases)
    arms = ("cue", "inst-3", "mat-300")
    for mu, s in ((1e-2, "cue"), (0.0, "regrow")):
        log = {"prev": None, "births": 0, "deaths": 0}

        def observe(t, st, states, ageH, ageW, born, dead):
            occ = st["occ"]
            for ai in range(1, len(arms)):
                assert np.array_equal(occ[ai * k:(ai + 1) * k], occ[:k])
            for x in ("V", "E", "r"):
                assert (st[x][~occ] == 0.0).all()
            ch, cw = C.contacts(occ)
            for x in ("H", "Hb"):
                assert (st[x][~ch] == 0.0).all()
            for x in ("W", "Wb"):
                assert (st[x][~cw] == 0.0).all()
            for s_ in states.values():
                assert (s_["s"][~occ[:k]] == 0.0).all() and (s_["sgn"][~occ[:k]] == 0.0).all()
                assert (s_["v"][~occ[:k]] == 0.0).all()
            nh, nw = C.touching(born)
            if log["prev"] is not None:
                pH, pW = log["prev"]
                assert (ageH[nh] == 0.0).all() and (ageW[nw] == 0.0).all()
                assert np.array_equal(ageH[~nh], pH[~nh] + 1.0) and np.array_equal(ageW[~nw], pW[~nw] + 1.0)
            gH, gW = sim.conductance("mat-300", ageH, ageW, occ[:k])
            assert (gH[~ch[:k]] == 0.0).all() and (gW[~cw[:k]] == 0.0).all()
            log["prev"] = (ageH.copy(), ageW.copy())
            log["births"] += int(born.sum())
            log["deaths"] += int(dead.sum())

        sim.run("li4", mu, s, 8, cases, V0, ema0, R0, th, T, 0.0, {150}, window=150, arms=arms, observe=observe)
        assert log["births"] > 0 and (log["deaths"] > 0) == (mu > 0)


def test_determinism_and_arm_independence():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    a = sim.run("dw", 1e-3, "change", 4, cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=("cue", "inst-3", "mat-1000"))
    b = sim.run("dw", 1e-3, "change", 4, cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=("mat-1000",))
    c = sim.run("dw", 1e-3, "change", 4, cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=("cue", "inst-3", "mat-1000"))
    for x in ("V", "r", "H", "W", "occ"):
        assert np.array_equal(a[x], c[x]) and np.array_equal(a[x][2 * k:], b[x])
