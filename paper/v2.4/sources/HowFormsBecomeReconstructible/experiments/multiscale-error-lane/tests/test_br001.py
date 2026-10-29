"""BR001 unit checks: the tissue-held record against the engine, events, gates and turnover."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from br001 import design as D
from br001 import sim
from mse.engine import Route, run

BLOCK = [900978]


def _prep(name=None):
    return sim.prepare(name or D.regime("F0", 0.3), BLOCK, "engineering")


def test_design_shape():
    for p, v in D.PANELS.items():
        names = [a.name for a in v["arms"]]
        assert len(names) == len(set(names))
        for panel, fam, a, b in D.CONTRASTS:
            if panel == p:
                assert a in names and b in names, (p, a, b)
    assert D.parse(D.regime("BL", 0.05, "o")) == ("BL", 0.05, "o")


def test_conserved_static_record_is_the_engine_hold_route():
    cases, s0, th, p, conserved, T, Tf = _prep()
    k = len(cases)
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    v, e, r, w = sim.simulate(D.ARM["L"]["static"], (D.COND_L[0],), k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, True,
                              T, Tf, np.ones(k, int), [None], [None])
    ref = run(s0, th, lambda t: Z[t - 1], Route(reference=None, capture=None), D.WINDOW, p)
    assert np.array_equal(v, ref.V) and np.array_equal(e, ref.ema) and np.array_equal(r, s0.R)


def test_open_body_differs_and_protected_record_is_restored():
    cases, s0, th, p, conserved, T, Tf = _prep()
    k = len(cases)
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    masks = [sim.patch_masks(cases, 6)]
    cond = (D.Cond("both-6x6", "lesion", "both", 6),)
    v1, _, r1, _ = sim.simulate(D.ARM["L"]["protected"], cond, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, True, T, Tf,
                                np.ones(k, int), masks, [None])
    assert np.array_equal(r1, s0.R)
    v2, _, _, _ = sim.simulate(D.ARM["L"]["static"], (D.COND_L[0],), k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, False,
                               T, Tf, np.ones(k, int), [None], [None])
    ref = run(s0, th, lambda t: Z[t - 1], Route(reference=None, capture=None), D.WINDOW, p)
    assert not np.array_equal(v2, ref.V)


def test_lesion_flips_exactly_the_patch_once():
    cases, s0, th, p, conserved, T, Tf = _prep()
    m = sim.patch_masks(cases, 4)
    assert (m.sum((-2, -1)) == 16).all()
    m2 = sim.patch_masks(cases, 8)
    assert (m2 | m == m2).all()             # the patch grows from the same corner


def test_turnover_events_are_shared_and_sized():
    cases, *_ = _prep()
    a = sim.turnover_events(cases, 1e-3, D.WINDOW)
    b = sim.turnover_events(cases, 1e-3, D.WINDOW)
    assert all(np.array_equal(x[0], y[0]) and np.array_equal(x[1], y[1]) for x, y in zip(a, b))
    n = np.mean([len(x[0]) for x in a])
    assert 0.6 * 1e-3 * D.WINDOW * 256 < n < 1.4 * 1e-3 * D.WINDOW * 256
