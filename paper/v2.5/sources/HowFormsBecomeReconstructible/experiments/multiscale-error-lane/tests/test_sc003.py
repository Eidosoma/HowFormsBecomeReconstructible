"""SC003's tests: python -m pytest tests/test_sc003.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be001 import sim as B1S  # noqa: E402
from cellpop import core as C  # noqa: E402
from sc002 import sim as S2S  # noqa: E402
from sc002 import theory as T2  # noqa: E402
from sc002.cable import Cable  # noqa: E402
from sc003 import design as D  # noqa: E402
from sc003 import sim  # noqa: E402
from sc003 import theory as TH  # noqa: E402

BLOCK = 900666
SC002_ARMS = ("cue", "inst-3", "mat-300", "mat-1000")


def test_design():
    assert D.UNITS == ("S4_t0", "F0_t0") and len(D.RUNS) == 8 and len(D.digest()) == 64
    assert set(D.ARMS_T) - {"cue"} == set(D.JUNCTIONS) and set(D.ARMS_W) < set(D.ARMS_T)
    assert not any(D.LAWS[a]["emt"] for a in D.ARMS_W if a in D.LAWS)
    assert D.IDENTITIES["development"] == (910180, 910196)
    assert all(lo >= 900660 and hi <= 900668 for lo, hi in (D.PROBE_BLOCKS, D.IDENTITIES["preflight"], D.DEBUG_BLOCKS))
    for (mu, tau), lam in D.EMT_LAM.items():
        assert abs(lam - T2.lam_eff(mu, tau)) < 5e-5
    assert abs(D.G_STAR - T2.g_star()) < 1e-12


def test_sc002_arms_equal_sc002():
    """With its new switches off SC003 is SC002: SC002's arms equal sc002.sim.run bit for bit, under turnover and in a
    regrowing wound."""
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    for body, mu, s, z in (("li4", 1e-3, "cue", 8), ("dw", 2.5e-4, "change", 4), ("li4", 0.0, "regrow+cue", 8)):
        a = sim.run(body, mu, s, z, cases, V0, ema0, R0, th, T, 0.0, {60, 120}, window=120, arms=SC002_ARMS, tag=D.TAG)
        b = S2S.run(body, mu, s, z, cases, V0, ema0, R0, th, T, 0.0, {60, 120}, window=120, arms=SC002_ARMS, tag=D.TAG)
        for x in ("V", "r", "H", "W", "occ", "opened", "trace", "trace_all", "r_in", "r_all", "r_out", "maturity", "filled"):
            assert np.array_equal(a[x], b[x]), (s, x)
        assert a["solvers"] == b["solvers"]


def test_no_division_aliases():
    """With no division every new switch is idle: iso-3 = inst-3 and gate-300 = sister-300 = mat-300 (= inst-3)."""
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    arms = ("inst-3", "iso-3", "mat-300", "gate-300", "sister-300")
    o = sim.run("dw", 0.0, "change", 4, cases, V0, ema0, R0, th, T, 0.0, {150}, window=150, arms=arms)
    for x in ("V", "r", "H", "W"):
        for q in range(1, len(arms)):
            assert np.array_equal(o[x][:k], o[x][q * k:(q + 1) * k]), (x, arms[q])
    assert all(v == {"fft": 150, "cg": 0} for v in o["solvers"].values())
    assert float(o["newc"].sum()) == float(o["newc"][3].sum())          # every commitment by a cell of age >= 105


def test_parents_match_divide():
    rng = np.random.default_rng(3)
    for p in (0.04, 0.1, 1.0):
        occ = rng.random((5, D.SIDE, D.SIDE)) > 0.3
        u, w = rng.random(occ.shape), rng.random(occ.shape)
        st = {"occ": occ.copy(), "V": rng.random(occ.shape), "E": rng.random(occ.shape)}
        st2, born = C.divide(st, p, u, w, True)
        mine, pdir = sim.parents(occ, p, u, w)
        assert np.array_equal(mine, born) and born.any()
        assert ((pdir >= 0) == born).all()
        for d in range(4):                                  # each daughter's parent sits in pdir, occupied before
            m = pdir == d
            assert occ[C.push(m, d)].all()
            assert np.array_equal(st2["V"][m], C.at(st["V"], d)[m])  # the daughter copied the cell in direction d


def test_sister_bonds():
    for d, bond, (i, j) in ((C.RIGHT, "H", (3, 3)), (C.LEFT, "H", (3, 2)), (C.DOWN, "W", (3, 3)), (C.UP, "W", (2, 3))):
        pdir = np.full((1, D.SIDE, D.SIDE), -1, np.int8)
        pdir[0, 3, 3] = d
        sh, sw = sim.sister_bonds(pdir)
        x = sh if bond == "H" else sw
        assert x.sum() == 1 and x[0, i, j] and (sw if bond == "H" else sh).sum() == 0


def test_laws():
    """iso: nothing at ages below ISO, lam^2 after; emt arms at EMT_LAM; gate and sister keep mat's conductances where
    no daughter-parent contact is flagged."""
    age = np.array([[[0.0, 1.0, 5.0, np.inf]]]).repeat(D.SIDE // 4, -1).repeat(D.SIDE, -2)
    occ = np.ones(age.shape, bool)
    gH, gW = sim.conductance("iso-3", age, age, occ, mu=1e-3)
    assert (gH[age == 0] == 0).all() and (gH[age >= 1] == 9.0).all()
    gH, _ = sim.conductance("iso-emt-1000", age, age, occ, mu=1e-3)
    assert (gH[age == 0] == 0).all() and np.allclose(gH[age >= 1], 1.4788 ** 2)
    gH, _ = sim.conductance("emt-300", age, age, occ, mu=2.5e-4)
    assert np.allclose(gH, 2.7245 ** 2)
    sis = np.zeros(age.shape, bool)
    m300 = sim.conductance("mat-300", age, age, occ, sis, sis, 1e-3)
    for a in ("gate-300", "sister-300"):
        assert all(np.array_equal(x, y) for x, y in zip(sim.conductance(a, age, age, occ, sis, sis, 1e-3), m300))
    sis[0, 0, 0] = True
    gs, _ = sim.conductance("sister-300", age, age, occ, sis, sis, 1e-3)
    assert gs[0, 0, 0] == 9.0 and m300[0][0, 0, 0] == 0.0


def test_isolated_newborn_and_gate():
    """A newborn whose contacts are all new and whose record disagrees with its cue triggers alone under iso-3 and
    mat-300, not under inst-3 or emt-1000 (its neighbours outvote it) and not under gate-300 (masked below G*)."""
    ages = np.full((1, D.SIDE, D.SIDE), np.inf)
    ages[0, 10, 10] = 0.0
    aH, aW = sim.contact_ages(ages)
    occ = np.ones(ages.shape, bool)
    rec, ca = np.ones(ages.shape), np.zeros(ages.shape)
    ca[0, ::2, ::2] = 1.0
    ca[0, 10, 10] = -1.0
    got = {}
    for arm in ("iso-3", "mat-300", "inst-3", "emt-1000", "gate-300"):
        gH, gW = sim.conductance(arm, aH, aW, occ, mu=1e-3)
        lam = D.lam_of(arm, 1e-3)
        st = {"v": np.zeros(ages.shape), "s": np.zeros(ages.shape), "sgn": np.zeros(ages.shape),
              "kernel": B1S.cable_kernel(lam), "lam": lam, "cable": Cable(1)}
        _, _, (committed, t), new = sim.detect(arm, rec, rec, ca, gH, gW, occ, st)
        got[arm] = (int(committed.sum()), bool(committed[0, 10, 10]), float(st["v"][0, 10, 10]), int(new.sum()))
    for arm in ("iso-3", "mat-300"):
        assert got[arm][:2] == (1, True) and abs(got[arm][2] + D.KAPPA / D.G_LEAK) < 1e-9 and got[arm][3] == 1
    for arm in ("inst-3", "emt-1000", "gate-300"):
        assert got[arm][0] == 0, arm
    assert got["gate-300"][2] == got["mat-300"][2]                       # the gate leaves the potentials alone


def test_population_bookkeeping():
    """Under turnover and in a regrowing wound: one population history for every arm; every newborn has exactly one
    daughter-parent contact, with its parent; flagged contacts are contacts; contacts touching a newborn start at age 0
    and the cell at age 0; the sister arm's flagged contacts are mature; empty sites hold nothing."""
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    k = len(cases)
    arms = ("cue", "iso-3", "mat-300", "sister-300", "gate-300")
    for mu, s in ((1e-2, "cue"), (0.0, "regrow")):
        log = {"births": 0, "deaths": 0}

        def observe(t, st, states, ageH, ageW, born, dead, extra):
            occ = st["occ"]
            for ai in range(1, len(arms)):
                assert np.array_equal(occ[ai * k:(ai + 1) * k], occ[:k])
            for x in ("V", "E", "r"):
                assert (st[x][~occ] == 0.0).all()
            ch, cw = C.contacts(occ[:k])
            sisH, sisW, pdir, age = extra["sisH"], extra["sisW"], extra["pdir"], extra["age"]
            assert not (sisH & ~ch).any() and not (sisW & ~cw).any()
            nh, nw = C.touching(born)
            assert (ageH[nh] == 0.0).all() and (ageW[nw] == 0.0).all() and (age[born] == 0.0).all()
            per = sisH.astype(int) + np.roll(sisH, 1, -1) + sisW + np.roll(sisW, 1, -2)
            assert (per[born] == 1).all()                                # one daughter-parent contact each
            sh, sw = sim.sister_bonds(pdir)
            assert (sisH[sh]).all() and (sisW[sw]).all()
            gH, gW = sim.conductance("sister-300", ageH, ageW, occ[:k], sisH, sisW, mu)
            assert (gH[sisH] == 9.0).all() and (gW[sisW] == 9.0).all()
            for s_ in states.values():
                assert (s_["s"][~occ[:k]] == 0.0).all() and (s_["v"][~occ[:k]] == 0.0).all()
            log["births"] += int(born.sum())
            log["deaths"] += int(dead.sum())

        o = sim.run("li4", mu, s, 8, cases, V0, ema0, R0, th, T, 0.0, {150}, window=150, arms=arms, observe=observe)
        assert log["births"] > 0 and (log["deaths"] > 0) == (mu > 0)
        assert abs(o["births"].sum() * D.SIDE * D.SIDE - log["births"]) < 1e-6


def test_effective_medium_arms_only_under_turnover():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    try:
        sim.run("dw", 0.0, "regrow", 8, cases, V0, ema0, R0, th, T, 0.0, {10}, window=10, arms=("cue", "emt-300"))
    except ValueError:
        return
    raise AssertionError("an effective-medium arm ran in a wound")


def test_theory():
    assert abs(TH.lam_eff("iso-3", 1e-3) - 3.0 * np.sqrt(1 - 2 * (1 - np.exp(-2e-3)))) < 1e-12
    assert TH.lam_eff("emt-1000", 1e-3) == 1.4788 and TH.lam_eff("inst-3", 1e-3) == 3.0
    for mu in D.MUS:
        assert TH.lam_eff("sister-300", mu) > TH.lam_eff("mat-300", mu)
        assert abs(TH.lam_eff("mat-300", mu) - T2.lam_eff(mu, 300.0)) < 1e-12
    cases = sim.prepare("S4", BLOCK, "engineering")[0]
    occ, aH, aW, sH, sW = TH.stationary_sisters(cases, 1e-2, 400, "mse-test")
    ch, cw = C.contacts(occ)
    share = ((sH & ch).sum() + (sW & cw).sum()) / (ch.sum() + cw.sum())
    assert 0.22 < share < 0.28


def test_determinism_and_arm_independence():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    arms = ("cue", "iso-emt-300", "mat-1000")
    a = sim.run("dw", 1e-3, "change", 4, cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=arms)
    b = sim.run("dw", 1e-3, "change", 4, cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=("mat-1000",))
    c = sim.run("dw", 1e-3, "change", 4, cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=arms)
    for x in ("V", "r", "H", "W", "occ", "newc"):
        assert np.array_equal(a[x], c[x])
    for x in ("V", "r", "H", "W", "occ"):
        assert np.array_equal(a[x][2 * k:], b[x])
    assert np.array_equal(a["newc"][:, 2 * k:], b["newc"])
