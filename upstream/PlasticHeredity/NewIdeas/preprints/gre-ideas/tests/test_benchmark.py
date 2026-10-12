from __future__ import annotations

from gre_sim.benchmark import run_benchmark


def test_small_benchmark_exercises_both_engines() -> None:
    result = run_benchmark(20, seed=9)
    assert not result["scientific"]
    assert result["boolean_developments_per_second"] > 0
    assert result["wagner_developments_per_second"] > 0
    assert result["boolean_landscape_seconds"] >= 0
    assert result["wagner_landscape_seconds"] >= 0

