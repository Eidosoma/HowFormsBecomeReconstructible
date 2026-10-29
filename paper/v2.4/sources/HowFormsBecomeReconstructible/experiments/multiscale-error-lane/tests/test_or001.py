"""OR001 unit checks: the genome controller against the engine, and the developmental gene."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from mse.engine import Ledger, Route, run
from mse.native import address
from or001 import design as O
from or001 import sim

TAG = "mse-or001-test"


def _founders():
    return sim.founders(TAG, "F0", 0.3, [900974], "engineering", (0,))


def test_native_hold_genome_is_the_engine_hold_route():
    cases, s0, th, p, T = _founders()
    genes = {g: np.array([O.REFERENCES["native_hold"][g]]) for g in O.GENES}
    res = sim.chain(TAG, genes, cases, s0, th, p, T, "none", 0)
    Z = np.stack([address(TAG, *c.key(), "gen", 0, "life").standard_normal((O.LIFE, 16, 16)) for c in cases], 1)
    ledger = Ledger.zeros(len(cases))
    ref = run(s0, th, lambda t: Z[t - 1], Route(reference=None), O.LIFE, p, ledger=ledger)
    m, a = (ref.V > 0) == (T > 0), np.abs(ref.V) > 0.2
    assert np.array_equal(res["v_qual"][0, 0], (m & a).mean((-2, -1)))
    assert np.array_equal(res["p_sign"][0, 0], ((ref.Q > 0) == (T > 0)).mean((-2, -1)))
    assert np.allclose(res["dose"][0, 0], ledger.body_l1, rtol=1e-12, atol=0)


def test_developmental_multiplier_acts_only_on_newborns():
    cases, s0, th, p, T = _founders()
    base = {g: np.array([O.REFERENCES["native_hold"][g]] * 2) for g in O.GENES}
    base["m_dev"] = np.array([1.0, 3.0])
    res = sim.chain(TAG, base, cases, s0, th, p, T, "none", 1)
    assert np.array_equal(res["v_qual"][0, 0], res["v_qual"][0, 1])          # the founder is an adult
    assert not np.array_equal(res["dose"][1, 0], res["dose"][1, 1])          # the newborn's early gain differs


def test_decode_ranges_and_x0():
    g = O.decode(np.array(O.X0))
    assert abs(g["g_site"] - 0.02) < 1e-6 and abs(g["m_dev"] - 1.0) < 1e-5 and abs(g["w"] - 0.5) < 1e-12
    big = O.decode(np.full(6, 50.0))
    assert big["g_site"] <= O.G_MAX and big["m_dev"] <= O.M_MAX and big["rho_w"] <= O.RHO_MAX
