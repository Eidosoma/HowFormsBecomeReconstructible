"""DL002's tests: python -m pytest tests/test_dl002.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl001 import sim as S  # noqa: E402
from dl002 import design as D  # noqa: E402
from dl002 import sim  # noqa: E402
from mse.assay import enrol  # noqa: E402

CASES = enrol([900898], D.MESSAGES, D.PARENTS, "engineering")


def test_labyrinth_templates():
    for kind in (0, 1):
        t = sim.template("LB", kind, 900898)
        assert set(np.unique(t)) == {-1.0, 1.0}
        assert abs(t.mean()) <= 0.1 and abs(S.spacing(t[None])[0] - 8.0) <= 1.6
        assert np.array_equal(sim.template("LB", kind + 2, 900898), -t)


def test_anchor_densities_and_wounds():
    for density in (16, 4):
        frac = sim.anchors(CASES, density).mean()
        assert abs(frac - 1 / density) < 0.03
    V0 = np.ones((len(CASES), D.SIDE, D.SIDE))
    R0 = 1.2 * V0
    V, E, r, gain, m = sim.branches(D.RECORDS_R, CASES, V0, V0.copy(), R0, "flip")
    k = len(CASES)
    assert (m.sum((-2, -1)) == 64).all()
    for i, rec in enumerate(D.RECORDS_R):
        sl = slice(i * k, (i + 1) * k)
        assert (V[sl][m] == -1).all() and (V[sl][~m] == 1).all()
        if rec.kind == "anchors":
            assert not gain[sl][m].any()
        if rec.kind == "rel":
            assert (r[sl][m] == -1.2).all()
        if rec.kind == "full":
            assert (gain[sl] == 0.2).all() and (r[sl] == 1.2).all()


def test_relational_record_never_reads_the_body():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", 900898, "engineering")
    recs = (D.Rec("rel", "rel", 0.2),)
    a = sim.run("dw", recs, cases, V0, ema0, R0, th, T, 1.0, "flip", {50})
    b = sim.run("li4", recs, cases, V0, ema0, R0, th, T, 1.0, "flip", {50})
    assert np.array_equal(a["r_rel"], b["r_rel"])
    c = sim.run("li4", recs, cases, V0, ema0, R0, th, T, 1.0, "flip", {50})
    assert np.array_equal(b["final"], c["final"])
