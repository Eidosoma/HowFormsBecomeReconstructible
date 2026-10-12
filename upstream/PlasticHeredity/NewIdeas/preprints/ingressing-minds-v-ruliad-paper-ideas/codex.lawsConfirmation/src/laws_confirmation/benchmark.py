"""Scientifically blind Stage-C runtime benchmark for the A1 ECA panel."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import resource
import time
from typing import Callable, Iterable

from .eca_math import CLASS_1, CLASS_3_CORE, CLASS_4
from .eca_sim import LineageContract, build_domain_dictionary, evaluate_condition


BENCHMARK_NAMESPACE = "laws-confirmation-benchmark-l01-l02-a1-v1"
BENCHMARK_RULES = (0, 18, 35, 110, 150, 184)
BENCHMARK_CONDITIONS = {
    63: (0.01,),
    64: (0.0025, 0.01, 0.04),
    65: (0.01,),
    128: (0.01,),
}
RAW_CHAMPIONS = (35, 43, 11, 57, 184)
PARTICLE_TARGET_RULES = tuple(
    sorted(CLASS_1 | CLASS_3_CORE | CLASS_4 | frozenset(RAW_CHAMPIONS))
)

FORBIDDEN_RESULT_KEY_FRAGMENTS = (
    "strict",
    "break",
    "form_support",
    "rank",
    "class",
    "gate",
)


@dataclass(frozen=True)
class PanelTask:
    observer: str
    rule: int
    width: int
    flip_noises: tuple[float, ...]
    namespace: str = BENCHMARK_NAMESPACE
    n_launches: int = 8
    futures_per_launch: int = 32


def benchmark_tasks() -> tuple[PanelTask, ...]:
    return tuple(
        PanelTask(observer, rule, width, tuple(noises))
        for observer in ("raw4", "particle4")
        for rule in BENCHMARK_RULES
        for width, noises in BENCHMARK_CONDITIONS.items()
    )


def _peak_rss_kib() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def benchmark_panel(task: PanelTask) -> dict[str, object]:
    """Execute a panel while returning timing/work fields and no outcomes."""

    if "benchmark" not in task.namespace.lower():
        raise ValueError("benchmark namespaces must contain 'benchmark'")
    if task.observer not in ("raw4", "particle4"):
        raise ValueError(f"unknown observer: {task.observer}")
    panel_started = time.perf_counter()
    dictionary_elapsed = 0.0
    domain_codes: frozenset[int] | None = None
    if task.observer == "particle4":
        dictionary_started = time.perf_counter()
        dictionary = build_domain_dictionary(
            task.rule,
            task.width,
            task.namespace + ":particle-domain",
        )
        dictionary_elapsed = time.perf_counter() - dictionary_started
        domain_codes = dictionary.codes

    timings: list[dict[str, object]] = []
    for flip_noise in task.flip_noises:
        contract = LineageContract(
            width=task.width,
            flip_noise=flip_noise,
            copy_error=1.5 * flip_noise,
            n_launches=task.n_launches,
            futures_per_launch=task.futures_per_launch,
            namespace=task.namespace,
            launch_split="benchmark",
        )
        started = time.perf_counter()
        result = evaluate_condition(
            task.rule,
            contract,
            observer=task.observer,  # type: ignore[arg-type]
            domain_codes=domain_codes,
        )
        elapsed = time.perf_counter() - started
        timings.append(
            {
                "flip_noise": flip_noise,
                "copy_error": 1.5 * flip_noise,
                "elapsed_seconds": elapsed,
                "futures": result.n_futures,
                "total_sweeps": result.total_sweeps,
            }
        )

    sanitized = {
        "observer": task.observer,
        "rule": task.rule,
        "width": task.width,
        "dictionary_elapsed_seconds": dictionary_elapsed,
        "condition_timings": timings,
        "panel_elapsed_seconds": time.perf_counter() - panel_started,
        "worker_peak_rss_kib_at_return": _peak_rss_kib(),
    }
    assert_blind_payload(sanitized)
    return sanitized


def _task(task: PanelTask) -> dict[str, object]:
    return benchmark_panel(task)


def run_benchmark(
    workers: int,
    *,
    progress: Callable[[dict[str, object], int, int], None] | None = None,
) -> list[dict[str, object]]:
    if not 1 <= workers <= 4:
        raise ValueError("workers must lie in [1, 4]")
    tasks = benchmark_tasks()
    completed: list[dict[str, object]] = []
    if workers == 1:
        for task in tasks:
            result = benchmark_panel(task)
            completed.append(result)
            if progress is not None:
                progress(result, len(completed), len(tasks))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_task, task): task for task in tasks}
            for future in as_completed(futures):
                result = future.result()
                completed.append(result)
                if progress is not None:
                    progress(result, len(completed), len(tasks))
    completed.sort(key=lambda row: (str(row["observer"]), int(row["rule"]), int(row["width"])))
    return completed


def _percentile_75(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot take percentile of an empty group")
    position = 0.75 * (len(ordered) - 1)
    lower = math_floor(position)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def math_floor(value: float) -> int:
    """Small local floor avoiding an otherwise unused heavy dependency."""

    return int(value // 1)


def runtime_projection(results: list[dict[str, object]], workers: int = 4) -> dict[str, object]:
    """Apply the projection formula frozen in the Stage-C protocol."""

    if not 1 <= workers <= 4:
        raise ValueError("workers must lie in [1, 4]")
    rates: dict[str, dict[int, list[float]]] = {
        "raw4": {width: [] for width in BENCHMARK_CONDITIONS},
        "particle4": {width: [] for width in BENCHMARK_CONDITIONS},
    }
    dictionaries: dict[int, list[float]] = {
        width: [] for width in BENCHMARK_CONDITIONS
    }
    for panel in results:
        observer = str(panel["observer"])
        width = int(panel["width"])
        for timing in panel["condition_timings"]:  # type: ignore[union-attr]
            seconds = float(timing["elapsed_seconds"])
            futures = int(timing["futures"])
            rates[observer][width].append(seconds / futures)
        if observer == "particle4":
            dictionaries[width].append(float(panel["dictionary_elapsed_seconds"]))

    p75_rates = {
        observer: {
            str(width): _percentile_75(values)
            for width, values in by_width.items()
        }
        for observer, by_width in rates.items()
    }
    p75_dictionaries = {
        str(width): _percentile_75(values)
        for width, values in dictionaries.items()
    }

    raw_cells = {64: 88 * 7, 63: 88, 65: 88, 128: 88}
    focused_particle_cells = {64: 28 * 7, 63: 28, 65: 28, 128: 28}
    full_particle_cells = {64: 88 * 7, 63: 88, 65: 88, 128: 88}
    futures_per_cell = 32 * 64

    def simulation_seconds(observer: str, cells: dict[int, int]) -> float:
        return sum(
            float(p75_rates[observer][str(width)]) * count * futures_per_cell
            for width, count in cells.items()
        )

    def dictionary_seconds(n_rules: int) -> float:
        return sum(float(p75_dictionaries[str(width)]) * n_rules for width in dictionaries)

    raw_seconds = simulation_seconds("raw4", raw_cells)
    focused_particle_seconds = simulation_seconds("particle4", focused_particle_cells)
    full_particle_seconds = simulation_seconds("particle4", full_particle_cells)
    focused_dictionary_seconds = dictionary_seconds(28)
    full_dictionary_seconds = dictionary_seconds(88)

    def scenario(
        particle_seconds: float,
        particle_dictionary_seconds: float,
        particle_cells: dict[int, int],
    ) -> dict[str, object]:
        serial = raw_seconds + particle_seconds + particle_dictionary_seconds
        conservative = serial / workers * 2.0
        cell_count = sum(raw_cells.values()) + sum(particle_cells.values())
        return {
            "rule_condition_cells": cell_count,
            "future_count": cell_count * futures_per_cell,
            "estimated_serial_seconds": serial,
            "conservative_wall_seconds": conservative,
            "workers": workers,
            "safety_factor": 2.0,
            "detach_threshold_seconds": 600.0,
            "detach_required": conservative > 600.0,
        }

    projection = {
        "seconds_per_future_p75_by_observer_width": p75_rates,
        "dictionary_seconds_p75_by_width": p75_dictionaries,
        "a1_focused": scenario(
            focused_particle_seconds,
            focused_dictionary_seconds,
            focused_particle_cells,
        ),
        "a2_full_particle": scenario(
            full_particle_seconds,
            full_dictionary_seconds,
            full_particle_cells,
        ),
    }
    assert_blind_payload(projection)
    return projection


def assert_blind_payload(value: object, path: str = "root") -> None:
    """Fail closed if an outcome-bearing field reaches benchmark output."""

    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in FORBIDDEN_RESULT_KEY_FRAGMENTS):
                raise ValueError(f"forbidden benchmark result key at {path}.{key}")
            assert_blind_payload(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_blind_payload(child, f"{path}[{index}]")
