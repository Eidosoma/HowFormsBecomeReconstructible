from __future__ import annotations

import numpy as np
import pytest

from fep_surprise.config import PHASE_GRID
from fep_surprise.tracing import traced_advance, traced_fission_only_advance
from fep_surprise import compat as _compat  # noqa: F401
from plastic_heredity.config import CANDIDATES, GardConfig
from plastic_heredity.simulator import (
    FissionRecord,
    _fission,
    advance_fission,
    cosine_similarity,
    generate_beta,
    generate_initial_composition,
)


def ordinary_fission_only(initial, cfg, contract, rng):
    parent = initial.copy()
    arrivals = cfg.n_max - int(parent.sum())
    parent += rng.multinomial(arrivals, np.full(cfg.n_types, 1 / cfg.n_types))
    daughter = _fission(parent, cfg, contract, rng)
    return FissionRecord(parent, daughter, cosine_similarity(parent, daughter), arrivals)


@pytest.mark.parametrize("candidate", ["02", "03"])
def test_traced_advance_is_bit_exact(candidate: str) -> None:
    cfg = GardConfig()
    beta = generate_beta(cfg, np.random.default_rng(10))
    initial = generate_initial_composition(cfg, np.random.default_rng(11))
    left = np.random.default_rng(12)
    right = np.random.default_rng(12)
    ordinary = advance_fission(initial, beta, cfg, CANDIDATES[candidate], left)
    traced = traced_advance(
        initial, beta, cfg, CANDIDATES[candidate], right, PHASE_GRID
    )
    assert np.array_equal(ordinary.parent, traced.record.parent)
    assert np.array_equal(ordinary.daughter, traced.record.daughter)
    assert ordinary.h == traced.record.h
    assert ordinary.growth_steps == traced.record.growth_steps
    assert np.array_equal(left.bit_generator.state["state"]["state"], right.bit_generator.state["state"]["state"])
    assert np.array_equal(traced.phase_compositions[0], initial)
    assert np.array_equal(traced.phase_compositions[-1], ordinary.parent)


@pytest.mark.parametrize("candidate", ["02", "03"])
def test_fission_only_trace_preserves_parent_and_rng(candidate: str) -> None:
    cfg = GardConfig()
    initial = generate_initial_composition(cfg, np.random.default_rng(21))
    beta = np.ones((cfg.n_types, cfg.n_types))
    left = np.random.default_rng(22)
    right = np.random.default_rng(22)
    ordinary = ordinary_fission_only(initial, cfg, CANDIDATES[candidate], left)
    traced = traced_fission_only_advance(
        initial, beta, cfg, CANDIDATES[candidate], right, PHASE_GRID
    )
    assert np.array_equal(ordinary.parent, traced.record.parent)
    assert np.array_equal(ordinary.daughter, traced.record.daughter)
    assert ordinary.h == traced.record.h
    assert np.array_equal(left.bit_generator.state["state"]["state"], right.bit_generator.state["state"]["state"])
