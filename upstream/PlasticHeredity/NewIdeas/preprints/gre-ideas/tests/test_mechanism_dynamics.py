from __future__ import annotations

import numpy as np

from gre_sim.boolean import BooleanRulebook
from gre_sim.mechanism_dynamics import (
    MechanismRulebook,
    boolean_sequential_step,
    compile_wagner,
    successor_table,
    wagner_synchronous_step,
)
from gre_sim.wagner import WagnerRulebook


def test_boolean_sequential_exposes_in_sweep_updates() -> None:
    # Gene 0 always turns on; gene 1 copies the newly updated gene 0.
    table = np.zeros((2, 4), dtype=np.uint8)
    table[0, :] = 1
    table[1, 1] = 1
    table[1, 3] = 1
    rulebook = BooleanRulebook(table)
    assert rulebook.step(0) == 1
    assert boolean_sequential_step(rulebook, 0) == 3


def test_wagner_synchronous_differs_from_sequential_when_order_matters() -> None:
    weights = np.asarray([[0.0, 1.0], [1.0, 0.0]])
    rulebook = WagnerRulebook(weights, np.zeros(2), np.asarray([0, 1]))
    state = 1  # (+1, -1)
    assert rulebook.step(state) != wagner_synchronous_step(rulebook, state)


def test_compiled_wagner_has_identical_successor_and_trajectories() -> None:
    rng = np.random.default_rng(82)
    rulebook = WagnerRulebook.random(5, rng)
    for update in ("sequential", "synchronous"):
        variant = f"wagner_{update}"
        compiled = compile_wagner(rulebook, update)
        assert np.array_equal(compiled.successor, successor_table(rulebook, variant))
        original = MechanismRulebook(rulebook, variant)
        bridge = MechanismRulebook(rulebook, "wagner_compiled", update)
        for state in range(rulebook.state_count):
            assert original.develop(state, None, 100) == bridge.develop(state, None, 100)
