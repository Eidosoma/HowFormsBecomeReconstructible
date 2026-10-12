from __future__ import annotations

import numpy as np

from gre_sim.landscape import enumerate_landscape
from gre_sim.plastic_memory_dynamics import (
    ablate_mark,
    apply_mark_bias,
    balanced_midpoints,
    clamp_state,
    damage_state,
    descriptor_matched_state,
    forced_break_state,
    permute_state,
    select_attractor_pair,
    update_mark,
)


def two_form_landscape():
    # 00/01 flow to 00 and 10/11 flow to 11.
    return enumerate_landscape(np.asarray([0, 0, 3, 3], dtype=np.int64))


def test_pair_midpoint_clamp_and_forced_break_are_deterministic() -> None:
    landscape = two_form_landscape()
    pair = select_attractor_pair(landscape, 2, 0.25, 0.5)
    assert pair is not None
    assert {pair.left_state, pair.right_state} == {0, 3}
    midpoints = balanced_midpoints(pair, 2, np.asarray([0, 1]), 2)
    assert set(midpoints) == {1, 2}
    nodes = (0,)
    assert clamp_state(0, 3, nodes) == 1
    broken = forced_break_state(
        landscape, pair.left_index, pair.left_state, genes=2
    )
    assert int(landscape.attractor_index[broken]) != pair.left_index


def test_mark_update_is_bounded_and_zero_coupling_is_inert() -> None:
    mark = np.asarray([0.8, -0.8])
    updated = update_mark(mark, adult_state=3, genes=2, rho=0.5)
    assert np.all(updated <= 1.0)
    assert np.all(updated >= -1.0)
    assert np.allclose(updated, [0.9, 0.1])
    assert apply_mark_bias(1, updated, 0.0, np.random.default_rng(1)) == 1
    assert apply_mark_bias(0, np.ones(2), 1.0, np.random.default_rng(2)) == 3


def test_damage_ablation_and_descriptor_control_preserve_contracts() -> None:
    damaged, nodes = damage_state(0, 4, 0.5, np.random.default_rng(4))
    assert len(nodes) == 2
    assert damaged.bit_count() == 2
    assert np.array_equal(ablate_mark(np.ones(4), (1, 3)), [1, 0, 1, 0])
    landscape = two_form_landscape()
    pair = select_attractor_pair(landscape, 2, 0.25, 0.5)
    assert pair is not None
    matched, exact = descriptor_matched_state(landscape, 1, pair, 2, 0)
    assert matched != 1
    assert isinstance(exact, bool)
    assert permute_state(1, 2, np.asarray([1, 0])) == 2
