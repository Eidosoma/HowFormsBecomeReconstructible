import pytest

from laws_confirmation.benchmark import (
    BENCHMARK_CONDITIONS,
    PARTICLE_TARGET_RULES,
    PanelTask,
    assert_blind_payload,
    benchmark_panel,
    benchmark_tasks,
    runtime_projection,
)


def test_frozen_benchmark_dimensions():
    tasks = benchmark_tasks()
    assert len(tasks) == 48
    assert sum(len(task.flip_noises) for task in tasks) == 72
    assert sum(
        len(task.flip_noises) * task.n_launches * task.futures_per_launch
        for task in tasks
    ) == 18_432
    assert len(PARTICLE_TARGET_RULES) == 28


def test_one_tiny_panel_serializes_only_permitted_benchmark_fields():
    result = benchmark_panel(
        PanelTask(
            observer="raw4",
            rule=90,
            width=8,
            flip_noises=(0.01,),
            namespace="unit-benchmark-firewall",
            n_launches=1,
            futures_per_launch=1,
        )
    )
    assert result["observer"] == "raw4"
    assert result["condition_timings"][0]["futures"] == 1
    assert_blind_payload(result)


def test_blind_serializer_fails_closed_on_outcome_key():
    with pytest.raises(ValueError, match="forbidden benchmark result key"):
        assert_blind_payload({"nested": {"strict_rate": 0.1}})


def test_projection_uses_frozen_a1_and_a2_cell_counts():
    results = []
    for observer in ("raw4", "particle4"):
        for width in BENCHMARK_CONDITIONS:
            results.append(
                {
                    "observer": observer,
                    "rule": 0,
                    "width": width,
                    "dictionary_elapsed_seconds": 0.5 if observer == "particle4" else 0.0,
                    "condition_timings": [
                        {
                            "flip_noise": 0.01,
                            "copy_error": 0.015,
                            "elapsed_seconds": 1.0,
                            "futures": 100,
                            "total_sweeps": 1000,
                        }
                    ],
                    "panel_elapsed_seconds": 1.0,
                    "worker_peak_rss_kib_at_return": 100,
                }
            )
    projection = runtime_projection(results)
    assert projection["a1_focused"]["rule_condition_cells"] == 1160
    assert projection["a1_focused"]["future_count"] == 2_375_680
    assert projection["a2_full_particle"]["rule_condition_cells"] == 1760
    assert projection["a2_full_particle"]["future_count"] == 3_604_480
    assert projection["a1_focused"]["detach_required"] is True
