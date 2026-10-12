from __future__ import annotations

import numpy as np

from gre_sim.boolean import BooleanRulebook
from gre_sim.engines import rulebook_from_dict
from gre_sim.landscape import (
    canonical_cycle,
    enumerate_landscape,
    int_to_signs,
    normalized_hamming,
    signs_to_int,
)
from gre_sim.wagner import WagnerRulebook, gamma_multipliers


def test_functional_graph_resolves_point_cycle_basins_and_distances() -> None:
    landscape = enumerate_landscape(np.asarray([0, 2, 1, 0]))
    assert [attractor.states for attractor in landscape.attractors] == [(0,), (1, 2)]
    assert landscape.basin_sizes.tolist() == [2, 2]
    assert landscape.distance.tolist() == [0, 0, 0, 1]
    assert canonical_cycle((2, 1)) == (1, 2)


def test_boolean_successor_roundtrip_and_serialization() -> None:
    successor = np.asarray([0, 2, 1, 0], dtype=np.int64)
    rulebook = BooleanRulebook.from_successor(successor)
    assert rulebook.successor.tolist() == successor.tolist()
    restored = rulebook_from_dict(rulebook.to_dict())
    assert isinstance(restored, BooleanRulebook)
    assert restored.uid == rulebook.uid
    assert restored.develop(1).cycle == (1, 2)


def test_wagner_tie_rule_and_constant_control() -> None:
    zero = WagnerRulebook(np.zeros((3, 3)), np.zeros(3), np.arange(3))
    assert [zero.step(state) for state in range(8)] == list(range(8))
    constant = WagnerRulebook.constant(3, 6)
    assert all(constant.develop(state).final_state == 6 for state in range(8))
    restored = rulebook_from_dict(constant.to_dict())
    assert isinstance(restored, WagnerRulebook)
    assert restored.uid == constant.uid


def test_state_encoding_hamming_and_gamma_zero_limit() -> None:
    for state in range(16):
        assert signs_to_int(int_to_signs(state, 4)) == state
    assert normalized_hamming(0b0000, 0b1010, 4) == 0.5
    assert np.array_equal(
        gamma_multipliers(3, 0.0, np.random.default_rng(1)), np.ones((3, 3))
    )

