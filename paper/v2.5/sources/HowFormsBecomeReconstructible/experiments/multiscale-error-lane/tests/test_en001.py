"""EN001 unit checks: equivalence with BR002's simulator at the full budget, the body step, budgets at phi = 1,
a store that never runs short, and shared draws."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from br001 import sim as S1
from br002 import design as D2
from br002 import sim as S2
from en001 import design as D
from en001 import sim

BLOCK = [900890]          # EN001's debug block (engineering)


def _setup(name):
    cases, s0, th, p, conserved, T = sim.prepare(name, BLOCK, "engineering")
    k = len(cases)
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    masks = [None if not c.size else sim.patch_masks(cases, c.size) for c in D.CONDS]
    turn = [sim.turnover_events(cases, c.rate, D.WINDOW) if c.kind == "turnover" else None for c in D.CONDS]
    born = [sim.newborn(cases, c.size) if c.kind == "kill" else None for c in D.CONDS]
    return cases, s0, th, p, conserved, T, k, Z, XI, masks, turn, born


def test_design_shape():
    for p, v in D.PANELS.items():
        names = [b.name for b in v["budgets"]]
        assert len(names) == len(set(names)), p
        assert all(a in D.ARMS for a in v["arms"])
    assert D.WINDOW == D.STARVE + D.RECOVER and D.WINDOW % D.SNAP == 0


def test_body_step_equals_br001_at_unit_rates():
    cases, s0, th, p, conserved, T, k, Z, XI, *_ = _setup(D.regime("F0", 0.3))
    for cons in (True, False):
        a = S1.body_step(s0.V, s0.ema, s0.R, th, Z[0], p, cons, 0.2)
        one = np.ones((k, 1, 1))
        b = sim.body_step(s0.V, s0.ema, s0.R, th, Z[0], p, cons, 0.2, one, one, one)
        assert all(np.array_equal(x, y) for x, y in zip(a, b[:3])), cons


def test_full_budget_equals_br002_simulator():
    """At phi = 1 the starvation phase is br002.sim.simulate's first 2000 updates, bit for bit."""
    name = D.regime("BL", 0.1)
    cases, s0, th, p, conserved, T, k, Z, XI, masks, turn, born = _setup(name)
    c2 = (D2.Cond("sham"), D2.Cond("flip", "lesion", 6), D2.Cond("reset", "kill", 6), D2.Cond("turn", "turnover", rate=1e-3))
    a2 = {"self": D2.ARM["R"]["self"], "multi": D2.ARM["R"]["multi"], "relcode": D2.ARM["R"]["rel+code+relink"]}
    for name_a, arm2 in a2.items():
        v2, _, r2, _ = S2.simulate(arm2, c2, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, T,
                                   np.ones(k, int), masks, turn, born)
        out = sim.simulate(D.ARMS[name_a], (D.BASE,), D.CONDS, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T,
                           masks, turn, born)
        assert np.array_equal(out["V_s"], v2) and np.array_equal(out["R_s"], r2), name_a


def test_every_accounting_at_phi_one_is_the_base():
    name = D.regime("F0", 0.3)
    cases, s0, th, p, conserved, T, k, Z, XI, masks, turn, born = _setup(name)
    budgets = (D.BASE, D.Budget("A1", paid="corr", phi=1.0), D.Budget("C1", noise="activity", phi=1.0),
               D.Budget("R1", alloc="record", phi=1.0), D.Budget("S1", scheme="store", phi=1.0))
    out = sim.simulate(D.ARMS["multi"], budgets, D.CONDS[:2], k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T,
                       masks[:2], turn[:2], born[:2], work=1e6)          # a store with unlimited supply never dips
    nb = 2 * k
    for key in ("V_s", "R_s", "V_r", "R_r"):
        x = out[key].reshape(len(budgets), nb, 16, 16)
        assert all(np.array_equal(x[0], x[i]) for i in range(1, len(budgets))), key


def test_budget_slows_paid_rates():
    name = D.regime("F0", 0.3)
    cases, s0, th, p, conserved, T, k, Z, XI, masks, turn, born = _setup(name)
    out = sim.simulate(D.ARMS["multi"], (D.BASE, D.Budget("B0.1", phi=0.1)), D.CONDS[:1], k, s0.V, s0.ema, s0.R, s0.R,
                       th, Z, XI, p, conserved, T, masks[:1], turn[:1], born[:1])
    wr = out["w_rec"].reshape(2, k).mean(1)
    assert wr[1] < 0.5 * wr[0]                      # the record pays less at a tenth of the budget


def test_draws_shared_and_sized():
    cases, *_ = sim.prepare(D.regime("F0", 0.1), BLOCK, "engineering")
    a = sim.turnover_events(cases, 1e-3, D.WINDOW)
    b = sim.turnover_events(cases, 1e-3, D.WINDOW)
    assert all(np.array_equal(x[0], y[0]) for x, y in zip(a, b))
    n = np.mean([len(x[0]) for x in a])
    assert 0.6 * 1e-3 * D.WINDOW * 256 < n < 1.4 * 1e-3 * D.WINDOW * 256
    assert np.array_equal(sim.newborn(cases, 6), sim.newborn(cases, 6))
