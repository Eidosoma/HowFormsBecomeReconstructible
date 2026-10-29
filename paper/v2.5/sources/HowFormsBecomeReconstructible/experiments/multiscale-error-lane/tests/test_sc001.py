"""SC001's draft tests: python -m pytest tests/test_sc001.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sc001 import design as D  # noqa: E402
from sc001 import sim  # noqa: E402

BLOCK = 900786


def test_design():
    names = [a.name for a in D.ARMS_G]
    assert len(names) == len(set(names)) and {"diff1.5/100", "diff6/100", "smooth/100"} <= set(names)
    conds = [c.name for c in D.CONDS_R]
    assert len(conds) == len(set(conds)) == len(D.RATES) * len(D.TEACHERS) * (2 + 2 * len(D.REGROW))
    assert D.tasks() == [("G", "S4_t0"), ("R", "S4_t0"), ("R", "F0_t0")]


def test_smooth_schedule():
    """Line d is filled within ((d - 1) s, d s], one cell at a time, each by its neighbour one line nearer the boundary."""
    cases = sim.prepare("S4", BLOCK, "engineering")[0]
    for geo in D.GEOMS:
        tf, pd = sim.smooth_schedule(cases, geo, 100)
        bd = sim.geometry(cases)[1][geo]
        assert (tf[bd == 0] == -1).all()
        for d in range(1, D.DMAX + 1):
            t = tf[bd == d]
            assert t.min() > (d - 1) * 100 and t.max() == d * 100
        from cellpop import core as C
        for d in range(4):
            sel = (pd == d) & (bd >= 1)
            assert (C.at(bd, d)[sel] == bd[sel] - 1).all()


def test_growth_arms_share_their_geometry():
    """grow, nb, none and diff divide at the same rate from the same seed and read the same streams, so their
    occupancy is identical at every step; the prescribed front fills exactly its schedule."""
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    arms = (D.GArm("grow", 100), D.GArm("nb", 100), D.GArm("none", 100), D.GArm("diff", 100, 6.0), D.GArm("front", 25))
    o = sim.run_G("li4", "perp", arms, cases, R0, th, T, 0.0, window=300, snaps=(300,))
    k = len(cases)
    occ = o["occ"].reshape(len(arms), k, D.SIDE, D.SIDE)
    for i in (1, 2, 3):
        assert np.array_equal(occ[0], occ[i])
    assert not np.array_equal(o["V"].reshape(len(arms), k, D.SIDE, D.SIDE)[0], o["V"].reshape(len(arms), k, D.SIDE, D.SIDE)[1])
    dist = sim.geometry(cases)[1]["perp"]
    assert np.array_equal(occ[4], dist * 25 <= 300)


def test_regrowth_pairs_and_the_record_never_reads_the_body():
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    conds = tuple(c for c in D.CONDS_R if c.rate == 0.001 and c.teacher == "record+parity")
    a = sim.run_R("li4", conds, cases, V0, ema0, R0, th, T, 0.0, window=300, reads=(300,))
    b = sim.run_R("dw", conds, cases, V0, ema0, R0, th, T, 0.0, window=300, reads=(300,))
    for sp in D.REGROW:
        assert np.array_equal(a[f"0.001/record+parity/regrow@{sp:g}"]["occ"], a[f"0.001/record+parity/regrow-nb@{sp:g}"]["occ"])
    m = sim.patch(cases)
    assert a["0.001/record+parity/regrow@0.04"]["occ"][m].mean() > 0.5      # the patch is refilling
    for c in conds:
        for key in ("r", "H", "W"):
            assert np.array_equal(a[c.name][key], b[c.name][key])
    nb = a["0.001/record+parity/regrow-nb@0.01"]
    assert (nb["r"][m & ~nb["occ"]] == 0).all()
