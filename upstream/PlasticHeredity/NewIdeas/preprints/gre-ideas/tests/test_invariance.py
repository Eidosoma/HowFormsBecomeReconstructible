from __future__ import annotations

import numpy as np

from gre_sim.boolean import BooleanRulebook
from gre_sim.landscape import canonical_cycle, permute_state
from gre_sim.validation import validate_implementation
from gre_sim.wagner import WagnerRulebook, permute_wagner_noise


def test_bundled_validation_fixtures_pass() -> None:
    result = validate_implementation()
    assert result["passed"]
    assert all(result["checks"].values())


def test_boolean_full_trajectory_is_conjugate() -> None:
    rng = np.random.default_rng(80)
    rulebook = BooleanRulebook.random(5, rng)
    permutation = np.asarray([2, 4, 1, 0, 3])
    permuted = rulebook.permute(permutation)
    for state in range(32):
        left = rulebook.develop(state)
        right = permuted.develop(permute_state(state, permutation, 5))
        assert left.status == right.status
        assert right.final_state == permute_state(left.final_state, permutation, 5)
        if left.cycle:
            expected = canonical_cycle(
                tuple(permute_state(value, permutation, 5) for value in left.cycle)
            )
            assert right.cycle == expected


def test_wagner_noisy_development_is_conjugate_when_noise_and_order_move() -> None:
    rng = np.random.default_rng(81)
    rulebook = WagnerRulebook.random(5, rng)
    permutation = np.asarray([2, 4, 1, 0, 3])
    permuted = rulebook.permute(permutation)
    noise = rng.gamma(10.0, 0.1, size=(5, 5))
    moved_noise = permute_wagner_noise(noise, permutation)
    for state in range(32):
        left = rulebook.develop(state, noise, 100)
        right = permuted.develop(
            permute_state(state, permutation, 5), moved_noise, 100
        )
        assert left.status == right.status
        assert right.final_state == permute_state(left.final_state, permutation, 5)
        if left.cycle:
            expected = canonical_cycle(
                tuple(permute_state(value, permutation, 5) for value in left.cycle)
            )
            assert right.cycle == expected

