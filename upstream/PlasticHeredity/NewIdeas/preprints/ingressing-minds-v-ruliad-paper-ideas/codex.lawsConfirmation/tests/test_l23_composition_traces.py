import importlib.util
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l23_composition_budget as old


@pytest.fixture(scope="module")
def audit():
    path = Path(__file__).resolve().parents[1]/"scripts/audit_l23_composition_traces.py"
    spec = importlib.util.spec_from_file_location("d082_trace", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_statistics_independent_and_offset_invariance(audit):
    ctx = old.context(402083)
    v = old.seeded(402083, "trace-test").normal(size=(3, 2, 16, 16))
    a = audit.statistics(v, ctx["forms"], ctx["mask"])
    b = audit.statistics(v+.3, ctx["forms"], ctx["mask"])
    assert audit.check_statistics(v, ctx["forms"], a)
    np.testing.assert_allclose(a["centered_alignment"], b["centered_alignment"], rtol=0, atol=1e-12)
    assert not np.array_equal(a["scores"], b["scores"])
    np.testing.assert_allclose(b["half_mean"]-a["half_mean"], .3, rtol=0, atol=1e-12)


@pytest.mark.parametrize("key", ("scores", "probabilities", "centered_alignment", "half_mean"))
def test_corruption_rejected(audit, key):
    ctx = old.context(402083)
    v = np.ones((2, 16, 16))
    row = audit.statistics(v, ctx["forms"], ctx["mask"])
    assert audit.check_statistics(v, ctx["forms"], row)
    assert (row["centered_alignment"] == 0).all()
    row[key].flat[0] += .1
    with pytest.raises(AssertionError):
        audit.check_statistics(v, ctx["forms"], row)


def test_aggregation_preserves_norm_time_pair_budget_reader_half(audit):
    x = np.arange(3*2*5*12*3*7*2*2*4).reshape(3, 2, 5, 12, 3, 7, 2, 2, 4)
    result = np.array(audit.aggregate({"scores": x})["scores"])
    assert result.shape == (2, 5, 12, 3, 7, 2, 4)
    np.testing.assert_array_equal(result, x.mean(axis=6).mean(axis=0))
