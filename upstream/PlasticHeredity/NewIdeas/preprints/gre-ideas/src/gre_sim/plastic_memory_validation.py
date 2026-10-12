"""Deterministic implementation audits for the plastic-memory extension."""

from __future__ import annotations

import numpy as np

from .boolean import BooleanRulebook
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import (
    apply_mark_bias,
    clamp_state,
    develop_memory_cycle,
    update_mark,
)
from .validation import validate_implementation


def validate_memory_implementation() -> dict[str, object]:
    base = validate_implementation()
    rulebook = MechanismRulebook(
        BooleanRulebook.from_successor(np.asarray([0, 0, 3, 3], dtype=np.int64)),
        "boolean_sync",
    )
    zero_mark = np.zeros(2, dtype=float)
    direct = rulebook.develop(1)
    cycle = develop_memory_cycle(
        rulebook,
        previous_state=1,
        base_state=1,
        mark=zero_mark,
        carryover=1.0,
        expression_flip_probability=0.0,
        mark_rho=0.0,
        mark_coupling=0.0,
        gamma_variance=0.0,
        wagner_max_sweeps=100,
        carry_rng=np.random.default_rng(1),
        mark_rng=np.random.default_rng(2),
        dynamics_rng=np.random.default_rng(3),
        write_mark=False,
    )
    zero_coupling_equal = (
        cycle.state == direct.final_state and cycle.status == direct.status
    )
    bounded = update_mark(np.asarray([1.0, -1.0]), 3, 2, 0.5)
    mark_bounded = bool(np.all(bounded >= -1.0) and np.all(bounded <= 1.0))
    inert = apply_mark_bias(1, np.ones(2), 0.0, np.random.default_rng(4)) == 1
    clamped = clamp_state(0, 3, (0, 1)) == 3
    audits = {
        "base_gre_validation": base,
        "zero_mark_pathwise_equal": zero_coupling_equal,
        "zero_coupling_inert": inert,
        "mark_bounded": mark_bounded,
        "cue_override_exact": clamped,
    }
    if not all(
        audits[name]
        for name in (
            "zero_mark_pathwise_equal",
            "zero_coupling_inert",
            "mark_bounded",
            "cue_override_exact",
        )
    ):
        raise AssertionError("plastic-memory implementation validation failed")
    return audits

