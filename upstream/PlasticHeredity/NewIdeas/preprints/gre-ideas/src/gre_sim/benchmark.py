"""Small non-scientific kernel benchmark for workstation sizing."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from .accelerate import NUMBA_AVAILABLE
from .boolean import BooleanRulebook
from .wagner import WagnerRulebook, gamma_multipliers


def run_benchmark(iterations: int = 2_000, seed: int = 7341) -> dict[str, Any]:
    if iterations < 10:
        raise ValueError("benchmark needs at least ten iterations")
    rng = np.random.default_rng(seed)
    boolean = BooleanRulebook.random(6, rng)
    wagner = WagnerRulebook.random(10, rng)

    # Warm compilation and caches outside timed regions.
    boolean.step(0)
    wagner.step(0)

    states_boolean = rng.integers(0, boolean.state_count, size=iterations)
    started = time.perf_counter()
    for state in states_boolean:
        boolean.develop(int(state))
    boolean_seconds = time.perf_counter() - started

    states_wagner = rng.integers(0, wagner.state_count, size=iterations)
    noises = [gamma_multipliers(10, 0.1, rng) for _ in range(iterations)]
    started = time.perf_counter()
    for state, noise in zip(states_wagner, noises):
        wagner.develop(int(state), noise, 100)
    wagner_seconds = time.perf_counter() - started

    started = time.perf_counter()
    boolean.landscape()
    boolean_landscape_seconds = time.perf_counter() - started
    started = time.perf_counter()
    wagner.landscape()
    wagner_landscape_seconds = time.perf_counter() - started

    return {
        "format": "gre-kernel-benchmark-v1",
        "scientific": False,
        "iterations": iterations,
        "numba_available": NUMBA_AVAILABLE,
        "boolean_developments_per_second": iterations / boolean_seconds,
        "wagner_developments_per_second": iterations / wagner_seconds,
        "boolean_landscape_seconds": boolean_landscape_seconds,
        "wagner_landscape_seconds": wagner_landscape_seconds,
    }

