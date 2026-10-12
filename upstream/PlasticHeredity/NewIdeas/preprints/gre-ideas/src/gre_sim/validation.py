"""Fast deterministic implementation fixtures."""

from __future__ import annotations

from typing import Any

import numpy as np

from .accelerate import NUMBA_AVAILABLE
from .boolean import BooleanRulebook
from .endpoints import apply_carryover, apply_carryover_arrays
from .landscape import canonical_cycle, permute_state
from .wagner import WagnerRulebook, permute_wagner_noise


def validate_implementation() -> dict[str, Any]:
    checks: dict[str, bool] = {}

    boolean = BooleanRulebook.from_successor(np.asarray([0, 2, 1, 0], dtype=np.int64))
    landscape = boolean.landscape()
    checks["boolean_point_and_cycle"] = (
        {attractor.states for attractor in landscape.attractors} == {(0,), (1, 2)}
        and boolean.develop(3).final_state == 0
        and boolean.develop(1).status == "cycle"
    )

    zero = WagnerRulebook(
        np.zeros((3, 3)), np.zeros(3), np.arange(3, dtype=np.int64)
    )
    checks["wagner_zero_tie_retains_state"] = all(
        zero.step(state) == state for state in range(8)
    )
    constant = WagnerRulebook.constant(3, 5)
    checks["wagner_constant_control"] = all(
        constant.develop(state).final_state == 5 for state in range(8)
    )

    rng = np.random.default_rng(9182)
    permutation = np.asarray([2, 0, 3, 1], dtype=np.int64)
    random_boolean = BooleanRulebook.random(4, rng)
    permuted_boolean = random_boolean.permute(permutation)
    checks["boolean_joint_isomorphism"] = all(
        permuted_boolean.step(permute_state(state, permutation, 4))
        == permute_state(random_boolean.step(state), permutation, 4)
        for state in range(16)
    )
    checks["boolean_trajectory_isomorphism"] = all(
        (
            random_boolean.develop(state).status
            == permuted_boolean.develop(permute_state(state, permutation, 4)).status
            and permuted_boolean.develop(
                permute_state(state, permutation, 4)
            ).final_state
            == permute_state(random_boolean.develop(state).final_state, permutation, 4)
        )
        for state in range(16)
    )

    random_wagner = WagnerRulebook.random(4, rng)
    permuted_wagner = random_wagner.permute(permutation)
    multipliers = rng.gamma(10.0, 0.1, size=(4, 4))
    permuted_multipliers = permute_wagner_noise(multipliers, permutation)
    checks["wagner_joint_isomorphism"] = all(
        permuted_wagner.step(
            permute_state(state, permutation, 4), permuted_multipliers
        )
        == permute_state(random_wagner.step(state, multipliers), permutation, 4)
        for state in range(16)
    )
    wagner_trajectory_valid = True
    for state in range(16):
        left = random_wagner.develop(state, multipliers, 100)
        right = permuted_wagner.develop(
            permute_state(state, permutation, 4), permuted_multipliers, 100
        )
        expected_cycle = (
            canonical_cycle(
                tuple(permute_state(value, permutation, 4) for value in left.cycle)
            )
            if left.cycle
            else ()
        )
        if not (
            left.status == right.status
            and right.final_state == permute_state(left.final_state, permutation, 4)
            and right.cycle == expected_cycle
        ):
            wagner_trajectory_valid = False
            break
    checks["wagner_trajectory_isomorphism"] = wagner_trajectory_valid

    carry_rng = np.random.default_rng(44)
    checks["carryover_reset"] = apply_carryover(15, 3, 4, 0.0, 0.0, carry_rng) == 3
    carry_rng = np.random.default_rng(44)
    checks["carryover_full"] = apply_carryover(15, 3, 4, 1.0, 0.0, carry_rng) == 15
    choices = rng.random(4) < 0.5
    flips = rng.random(4) < 0.25
    moved_choices = np.empty_like(choices)
    moved_flips = np.empty_like(flips)
    for old_index, new_index in enumerate(permutation):
        moved_choices[new_index] = choices[old_index]
        moved_flips[new_index] = flips[old_index]
    left_carryover = apply_carryover_arrays(11, 5, 4, choices, flips)
    right_carryover = apply_carryover_arrays(
        permute_state(11, permutation, 4),
        permute_state(5, permutation, 4),
        4,
        moved_choices,
        moved_flips,
    )
    checks["carryover_noise_isomorphism"] = right_carryover == permute_state(
        left_carryover, permutation, 4
    )

    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise AssertionError(f"implementation validation failed: {failed}")
    return {
        "format": "gre-implementation-validation-v1",
        "passed": True,
        "checks": checks,
        "numba_available": NUMBA_AVAILABLE,
    }
