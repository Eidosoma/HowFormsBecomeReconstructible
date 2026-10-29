"""FN001's tests (draft): python -m pytest tests/test_fn001.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fn001 import design as D  # noqa: E402
from fn001 import sim  # noqa: E402
from lr004 import design as L4D  # noqa: E402
from lr004 import sim as L4S  # noqa: E402

BLOCK = 900776
STRIPES = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.0, -1.0)[None, :].repeat(D.SIDE, 0)


def test_design_conditions():
    names = [c.name for c in D.CONDS]
    assert len(names) == len(set(names)) == len(D.RATES) * len(D.REPAIRS) * len(D.SCHEDULES)
    c = D.Cond(0.001, "vote", "W12x")
    assert c.teacher == L4D.Cond(0.001, "vote") and c.wounds == ((D.T_W1, "a"), (D.T_W2, "b"))
    assert D.Cond(0.0, "body", "W2").wounds == ((D.T_W2, "a"),)
    assert set(D.READS) <= set(range(1, D.WINDOW + 1)) and D.T_W1 in D.READS and D.T_W2 in D.READS


def test_topology_periodic():
    assert sim.topology(STRIPES) == (4, 4, 0)                  # stripes wrap: one domain each
    s = STRIPES.copy()
    s[:, 4:8][10] = 1.0                                         # a bridge across a minus stripe merges two plus stripes
    assert sim.topology(s) == (3, 4, 0)                        # the cut minus stripe still wraps
    s = STRIPES.copy()
    s[10, 1] = -1.0                                             # an island inside a plus stripe
    assert sim.topology(s) == (4, 4, 1)
    s = STRIPES.copy()
    s[:, 0:4][3:5] = -1.0                                       # a plus stripe cut through: still one (it wraps) ...
    assert sim.topology(s)[0] == 4
    s[:, 0:4][20:22] = -1.0                                     # ... cut twice: two pieces, and the minus stripes join
    p, q, _ = sim.topology(s)
    assert p == 5 and q == 3
    assert sim.walls(STRIPES[None])[0] == 8 * D.SIDE                # eight walls per row


def test_kill():
    m = np.zeros((D.SIDE, D.SIDE), bool)
    m[2:4, 2:4] = True
    one = np.ones((D.SIDE, D.SIDE))
    sh, sw = -one, -one
    H, W, Hb, Wb, r = sim.kill((one, one, 0.8 * one, 0.8 * one, one), m, sh, sw)
    th, tw = sim.touching(m)
    assert th.sum() == 4 + 2 and tw.sum() == 4 + 2
    assert (H[th] == -1).all() and (H[~th] == 1).all() and (Hb[th] == 0).all() and (Wb[~tw] == 0.8).all()
    assert (r[m] == 0).all() and (r[~m] == 1).all()


def test_equals_lr004_before_any_wound():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    conds = tuple(D.Cond(0.003, rep, s) for rep in ("site", "vote") for s in ("W12", "W2"))
    o = sim.run("li4", conds, cases, V0, ema0, R0, th, T, 1.0, {300}, window=300)
    o4 = L4S.run("li4", tuple(c.teacher for c in conds), cases, V0, ema0, R0, th, T, 1.0, {300}, tag=D.TAG, window=300)
    for key in ("V", "r", "H", "W"):
        assert np.array_equal(o[key], o4[key])
    assert np.array_equal(o["sign"], o4["sign"]) and np.array_equal(o["r_sign"], o4["r_sign"])


def test_defects_graded_and_flood_fill_agrees():
    from fn001.checks import flood_function
    ttop = np.array([sim.topology(STRIPES)[:2]])
    tw = sim.walls(STRIPES[None])
    x = STRIPES.copy()
    x[10, 4:8] = 1.0                                            # one bridge: not intact, one defect
    x[20, 1] = -1.0                                             # and one island: two defects
    intact, defects, isl, wex = (float(v[0]) for v in sim.function(x[None], ttop, tw))
    assert (intact, defects, isl) == (0.0, 2.0, 1.0) and wex > 0
    fl = flood_function(x, STRIPES)
    assert (fl["intact"], fl["defects"], fl["islands"], fl["walls"]) == (intact, defects, isl, wex)
