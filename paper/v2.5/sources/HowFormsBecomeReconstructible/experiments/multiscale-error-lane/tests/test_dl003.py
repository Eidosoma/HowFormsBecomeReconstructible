"""DL003's tests: python -m pytest tests/test_dl003.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl001 import sim as S  # noqa: E402
from dl003 import design as D  # noqa: E402
from dl003 import sim  # noqa: E402
from mse.assay import enrol  # noqa: E402

CASES = enrol([900726], D.MESSAGES, D.PARENTS, "engineering")


def test_geometry():
    masks, dist = sim.geometry(CASES)
    for g in D.GEOMETRIES:
        assert (masks[g].sum((-2, -1)) == D.N_ANCHOR).all()
    for j, c in enumerate(CASES):
        t = S.template("S4", c.message, D.SIDE, 900726)
        assert set(np.unique(t[masks["par"][j]])) == {-1.0, 1.0}          # the par boundary straddles a wall
        assert (t[masks["perp"][j]] > 0).sum() == D.N_ANCHOR // 2         # the perp boundary crosses every stripe
        for g in ("par", "perp"):
            assert (np.bincount(dist[g][j].reshape(-1), minlength=16) == 2 * D.SIDE).all()
        assert (dist["cluster"][j][masks["cluster"][j]] == 0).all() and dist["cluster"][j].max() == D.DMAX["cluster"]


def test_front_schedule():
    cases, V0, ema0, R0, th, T = sim.prepare(900726, "engineering")
    arms = (D.Arm("perp/f25", "perp", 25),)
    o = sim.run("li4", arms, cases, V0, ema0, R0, th, T, 0.0, "B", {50}, window=50)
    d = sim.geometry(cases)[1]["perp"]
    nb = sim.newborn(cases)
    assert np.array_equal(o["final"][d == 2], nb[d == 2])
    assert (o["final"][d > 2] == 0).all() and (o["final_ema"][d > 2] == 0).all()
    assert (o["final"][d < 2] != 0).all()


def test_no_information_ignores_the_record():
    cases, V0, ema0, R0, th, T = sim.prepare(900726, "engineering")
    arms = (D.Arm("none", "none"), D.Arm("none/perp-f100", "none", 100, "perp"))
    a = sim.run("li4", arms, cases, V0, ema0, R0, th, T, 1.0, "B", {200}, window=200)
    b = sim.run("li4", arms, cases, V0, ema0, -R0, th, T, 1.0, "B", {200}, window=200)
    assert np.array_equal(a["final"], b["final"])
