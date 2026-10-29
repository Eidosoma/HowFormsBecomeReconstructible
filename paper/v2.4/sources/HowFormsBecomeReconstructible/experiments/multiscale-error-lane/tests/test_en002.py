"""EN002's engine tests: python -m pytest tests/test_en002.py"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl001 import sim as DLS  # noqa: E402
from en001.sim import body_step as en001_body_step  # noqa: E402
from en002 import design as D  # noqa: E402
from en002 import sim  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import NATIVE  # noqa: E402


def test_unit_multipliers_equal_dl001_body():
    g = np.random.default_rng(1)
    p = replace(NATIVE, sigma=0.1)
    one = np.ones((3, 1, 1))
    for body in ("dw", "li2", "li4"):
        alpha, L = D.BODIES[body]
        G = DLS.ghat(32, L) if alpha else None
        V, ema, r, th = (g.standard_normal((3, 32, 32)) for _ in range(4))
        gain = np.full((3, 1, 1), 0.2)
        a, b = (V.copy(), ema.copy()), (V.copy(), ema.copy())
        for _ in range(60):
            z = g.standard_normal((3, 32, 32))
            a = sim.body(a[0], a[1], r, th, z, p, gain, alpha, G, one, one, one)[:2]
            b = DLS.body(b[0], b[1], r, th, z, p, gain, alpha, G)[:2]
        assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_alpha0_equals_en001_paid_body_step():
    g = np.random.default_rng(2)
    p = replace(NATIVE, sigma=0.1)
    V, ema, r, th = (g.standard_normal((3, 32, 32)) for _ in range(4))
    for m, n in ((0.25, 1.0), (0.1, 0.1)):
        mm, nn = np.full((3, 1, 1), m), np.full((3, 1, 1), n)
        a, b = (V.copy(), ema.copy()), (V.copy(), ema.copy())
        for _ in range(60):
            z = g.standard_normal((3, 32, 32))
            a = sim.body(a[0], a[1], r, th, z, p, 0.2, 0.0, None, mm, mm, nn)[:2]
            b = en001_body_step(b[0], b[1], r, th, z, p, False, 0.2, mm, mm, nn)[:2]
        assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_multipliers_follow_the_budget():
    k = 2
    md, mc, nb = sim.multipliers(D.COND_G, k)
    for ci, c in enumerate(D.COND_G):
        sl = slice(ci * k, (ci + 1) * k)
        want = c.budget.phi if c.budget.acct in ("B", "C") else 1.0
        assert np.all(md[sl] == want) and np.all(mc[sl] == want)
        assert np.all(nb[sl] == (c.budget.phi if c.budget.acct == "C" else 1.0))


def test_templates():
    for fam in D.PATTERNS:
        for kind in range(4):
            t = sim.template(fam, kind, 32)
            assert t.mean() == 0 and set(np.unique(t)) == {-1.0, 1.0}
    assert np.array_equal(sim.template("S4", 0, 32), DLS.template("S4", 0, 32, 910700))


def test_wounds_and_determinism():
    cases = enrol([900924], D.MESSAGES, D.PARENTS, "engineering")
    for size in (4, 8):
        assert (sim.wound_mask(cases, size).sum((-2, -1)) == size * size).all()
    conds = [c for c in D.COND_G if c.name in ("B0.1/held", "C0.25/none")]
    V = np.tile(0.1 * np.stack([sim.template("S4", c.message, 32) for c in cases]), (len(conds), 1, 1))
    T = np.tile(np.stack([sim.template("S4", c.message, 32) for c in cases]), (len(conds), 1, 1))
    th = np.zeros((len(cases), 32, 32))
    runs = [sim.run("li4", conds, V.copy(), V.copy(), T.copy(), th, T, cases, {40}, window=40) for _ in range(2)]
    assert np.array_equal(runs[0]["final"], runs[1]["final"])
