"""Fresh Stage-D A1 campaign and frozen L01/L02 adjudication.

This module contains scientific serialization and gates.  The Stage-C
benchmark imports only :mod:`eca_sim` and has a fail-closed outcome firewall.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from statistics import median, stdev
import time
from typing import Callable, Iterable, Sequence

from .eca_math import CLASS_1, CLASS_3_CORE, CLASS_4, canonical_rules, wolfram_class
from .eca_sim import (
    ConditionResult,
    DomainDictionary,
    LaunchResult,
    LineageContract,
    build_domain_dictionary,
    evaluate_condition,
    simulate_launch,
)
from .io import canonical_digest


SCIENTIFIC_NAMESPACE = "laws-confirmation-scientific-l01-l02-a1-v1"
REGISTERED_NOISES = (0.0025, 0.005, 0.01, 0.02, 0.04)
HOLDOUT_NOISES = (0.03, 0.08)
WIDTH64_NOISES = tuple(sorted(REGISTERED_NOISES + HOLDOUT_NOISES))
WIDTH_NOISES = {
    63: (0.01,),
    64: WIDTH64_NOISES,
    65: (0.01,),
    128: (0.01,),
}
RAW_RULES = canonical_rules()
RAW_CHAMPIONS = (35, 43, 11, 57, 184)
PARTICLE_RULES = tuple(
    sorted(CLASS_1 | CLASS_3_CORE | CLASS_4 | frozenset(RAW_CHAMPIONS))
)
PARTITIONS = ("combined", "primary", "holdout")
T_CRITICAL_95 = {16: 2.131449546, 32: 2.039513446}
STRICT_LOWER = 0.005
STRICT_UPPER = 0.5


@dataclass(frozen=True)
class A1PanelTask:
    observer: str
    rule: int
    width: int
    flip_noises: tuple[float, ...]

    @property
    def key(self) -> str:
        return panel_key(self.observer, self.rule, self.width)


def panel_key(observer: str, rule: int, width: int) -> str:
    return f"{observer}:r{rule:03d}:w{width:03d}"


def campaign_tasks() -> tuple[A1PanelTask, ...]:
    return tuple(
        A1PanelTask(observer, rule, width, tuple(noises))
        for observer, rules in (("raw4", RAW_RULES), ("particle4", PARTICLE_RULES))
        for rule in rules
        for width, noises in WIDTH_NOISES.items()
    )


def design_contract() -> dict[str, object]:
    tasks = campaign_tasks()
    raw_cells = len(RAW_RULES) * sum(len(values) for values in WIDTH_NOISES.values())
    particle_cells = len(PARTICLE_RULES) * sum(
        len(values) for values in WIDTH_NOISES.values()
    )
    return {
        "schema_version": 1,
        "namespace": SCIENTIFIC_NAMESPACE,
        "launch_split": "a1-all",
        "primary_launch_indices": list(range(16)),
        "holdout_launch_indices": list(range(16, 32)),
        "launches_per_cell": 32,
        "futures_per_launch": 64,
        "futures_per_cell": 2048,
        "width_noises": {
            str(width): list(noises) for width, noises in WIDTH_NOISES.items()
        },
        "copy_error_ratio": 1.5,
        "raw_rules": list(RAW_RULES),
        "particle_rules": list(PARTICLE_RULES),
        "raw_cells": raw_cells,
        "particle_cells": particle_cells,
        "total_cells": raw_cells + particle_cells,
        "total_futures": (raw_cells + particle_cells) * 2048,
        "panel_tasks": len(tasks),
        "dynamics": LineageContract(
            width=64,
            flip_noise=0.01,
            copy_error=0.015,
            n_launches=32,
            futures_per_launch=64,
            namespace=SCIENTIFIC_NAMESPACE,
            launch_split="a1-all",
        ).to_dict()["execution_semantics"],
        "activity_budget": "4*width",
        "min_sweeps": 4,
        "max_sweeps": 128,
        "horizon": 32,
        "thresholds": {
            "inherit": 0.9,
            "coherence": 0.9,
            "distinct": 0.85,
            "strict_run": 8,
            "capability_band": [STRICT_LOWER, STRICT_UPPER],
        },
        "particle_dictionary": {
            "namespace": SCIENTIFIC_NAMESPACE + ":particle-domain",
            "densities": [0.2, 0.4, 0.6, 0.8],
            "burnin": 64,
            "collect": 16,
            "coverage_target": 0.9,
            "cap": 64,
        },
    }


def _student_interval(
    values: Sequence[float], *, lower: float | None = None, upper: float | None = None
) -> list[float]:
    if len(values) not in T_CRITICAL_95:
        raise ValueError(f"no frozen t critical value for n={len(values)}")
    centre = sum(values) / len(values)
    half_width = T_CRITICAL_95[len(values)] * stdev(values) / (len(values) ** 0.5)
    lo = centre - half_width
    hi = centre + half_width
    if lower is not None:
        lo = max(lower, lo)
    if upper is not None:
        hi = min(upper, hi)
    return [lo, hi]


def _rate_record(counts: Sequence[int], denominator_each: int) -> dict[str, object]:
    rates = [count / denominator_each for count in counts]
    return {
        "count": sum(counts),
        "rate": sum(counts) / (len(counts) * denominator_each),
        "launch_student_ci95": _student_interval(rates, lower=0.0, upper=1.0),
    }


def _launch_summary(result: LaunchResult, futures_per_launch: int) -> dict[str, object]:
    histogram = Counter(result.first_generation_times)
    return {
        "launch_index": result.launch_index,
        "partition": "primary" if result.launch_index < 16 else "holdout",
        "n_futures": futures_per_launch,
        "strict_count": result.strict_count,
        "strict_rate": result.strict_count / futures_per_launch,
        "break_by_8_count": result.break_by_8_count,
        "break_by_8_rate": result.break_by_8_count / futures_per_launch,
        "survival_sum": result.survival_sum,
        "mean_survival": result.survival_sum / futures_per_launch,
        "first_generation_sweep_median": float(median(result.first_generation_times)),
        "first_generation_sweep_histogram": {
            str(key): value for key, value in sorted(histogram.items())
        },
        "form_support": result.form_support,
        "form_n_futures": result.form_n_futures,
        "total_sweeps": result.total_sweeps,
        "death_counts": result.death_counts,
    }


def _partition_summary(
    launches: Sequence[LaunchResult], futures_per_launch: int
) -> dict[str, object]:
    strict_counts = [item.strict_count for item in launches]
    break_counts = [item.break_by_8_count for item in launches]
    survival_means = [item.survival_sum / futures_per_launch for item in launches]
    first_times = [value for item in launches for value in item.first_generation_times]
    death_counts: Counter[str] = Counter()
    for item in launches:
        death_counts.update(item.death_counts)
    library = sorted(
        {
            item.form_support
            for item in launches
            if item.form_n_futures > 0 and item.form_support != 0
        }
    )
    return {
        "n_launches": len(launches),
        "n_futures": len(launches) * futures_per_launch,
        "strict": _rate_record(strict_counts, futures_per_launch),
        "break_by_8": _rate_record(break_counts, futures_per_launch),
        "mean_survival": sum(survival_means) / len(survival_means),
        "first_generation_sweep_median": float(median(first_times)),
        "form_library": library,
        "form_library_size": len(library),
        "total_sweeps": sum(item.total_sweeps for item in launches),
        "death_counts": dict(sorted(death_counts.items())),
    }


def condition_summary(result: ConditionResult, elapsed_seconds: float) -> dict[str, object]:
    primary = result.launches[:16]
    holdout = result.launches[16:]
    if len(primary) != 16 or len(holdout) != 16:
        raise ValueError("Stage-D conditions require exactly 32 launch profiles")
    return {
        "flip_noise": result.flip_noise,
        "copy_error": result.copy_error,
        "elapsed_seconds": elapsed_seconds,
        "total_sweeps": result.total_sweeps,
        "partitions": {
            "combined": _partition_summary(result.launches, 64),
            "primary": _partition_summary(primary, 64),
            "holdout": _partition_summary(holdout, 64),
        },
        "per_launch": [_launch_summary(item, 64) for item in result.launches],
    }


def _dictionary_summary(dictionary: DomainDictionary) -> dict[str, object]:
    return {
        "codes": sorted(dictionary.codes),
        "coverage": dictionary.coverage,
        "dictionary_size": len(dictionary.codes),
        "n_distinct_codes": dictionary.n_distinct_codes,
        "counts": [[code, count] for code, count in dictionary.counts],
        "seed_rows_hex": list(dictionary.seed_rows_hex),
    }


def run_panel(task: A1PanelTask) -> dict[str, object]:
    if task.observer not in ("raw4", "particle4"):
        raise ValueError(f"unknown observer: {task.observer}")
    panel_started = time.perf_counter()
    dictionary: DomainDictionary | None = None
    domain_codes: frozenset[int] | None = None
    dictionary_elapsed = 0.0
    if task.observer == "particle4":
        dictionary_started = time.perf_counter()
        dictionary = build_domain_dictionary(
            task.rule,
            task.width,
            SCIENTIFIC_NAMESPACE + ":particle-domain",
        )
        dictionary_elapsed = time.perf_counter() - dictionary_started
        domain_codes = dictionary.codes

    conditions = []
    for flip_noise in task.flip_noises:
        contract = LineageContract(
            width=task.width,
            flip_noise=flip_noise,
            copy_error=1.5 * flip_noise,
            n_launches=32,
            futures_per_launch=64,
            namespace=SCIENTIFIC_NAMESPACE,
            launch_split="a1-all",
        )
        condition_started = time.perf_counter()
        result = evaluate_condition(
            task.rule,
            contract,
            observer=task.observer,  # type: ignore[arg-type]
            domain_codes=domain_codes,
        )
        conditions.append(
            condition_summary(result, time.perf_counter() - condition_started)
        )
    return {
        "panel_key": task.key,
        "observer": task.observer,
        "rule": task.rule,
        "wolfram_class": wolfram_class(task.rule),
        "width": task.width,
        "dictionary_elapsed_seconds": dictionary_elapsed,
        "dictionary": _dictionary_summary(dictionary) if dictionary is not None else None,
        "conditions": conditions,
        "panel_elapsed_seconds": time.perf_counter() - panel_started,
    }


def _panel_task(task: A1PanelTask) -> dict[str, object]:
    return run_panel(task)


def run_campaign(
    workers: int,
    completed: dict[str, dict[str, object]],
    *,
    progress: Callable[[dict[str, object], int, int], None],
) -> list[dict[str, object]]:
    if not 1 <= workers <= 4:
        raise ValueError("workers must lie in [1, 4]")
    tasks = campaign_tasks()
    known_keys = {task.key for task in tasks}
    unexpected = set(completed) - known_keys
    if unexpected:
        raise ValueError(f"unexpected completed panel keys: {sorted(unexpected)}")
    missing = [task for task in tasks if task.key not in completed]
    count = len(completed)
    if workers == 1:
        for task in missing:
            result = run_panel(task)
            completed[task.key] = result
            count += 1
            progress(result, count, len(tasks))
    elif missing:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_panel_task, task): task for task in missing}
            for future in as_completed(futures):
                result = future.result()
                key = str(result["panel_key"])
                completed[key] = result
                count += 1
                progress(result, count, len(tasks))
    return [completed[task.key] for task in tasks]


def _index_panels(
    panels: Sequence[dict[str, object]],
) -> dict[tuple[str, int, int, float], dict[str, object]]:
    index: dict[tuple[str, int, int, float], dict[str, object]] = {}
    for panel in panels:
        for condition in panel["conditions"]:  # type: ignore[union-attr]
            key = (
                str(panel["observer"]),
                int(panel["rule"]),
                int(panel["width"]),
                float(condition["flip_noise"]),
            )
            if key in index:
                raise ValueError(f"duplicate condition: {key}")
            index[key] = condition
    return index


def _partition_rate(condition: dict[str, object], partition: str) -> float:
    return float(condition["partitions"][partition]["strict"]["rate"])  # type: ignore[index]


def _capable(condition: dict[str, object], partition: str) -> bool:
    value = _partition_rate(condition, partition)
    return STRICT_LOWER <= value <= STRICT_UPPER


def _regime_slice(
    index: dict[tuple[str, int, int, float], dict[str, object]],
    width: int,
    eta: float,
    partition: str,
) -> dict[str, object]:
    capable_rules = [
        rule
        for rule in RAW_RULES
        if _capable(index[("raw4", rule, width, eta)], partition)
    ]
    class2_count = sum(wolfram_class(rule) == 2 for rule in capable_rules)
    core = sorted(set(capable_rules) & CLASS_3_CORE)
    ordered = sorted(set(capable_rules) & CLASS_1)
    fraction = class2_count / len(capable_rules) if capable_rules else 0.0
    return {
        "width": width,
        "flip_noise": eta,
        "partition": partition,
        "capable_count": len(capable_rules),
        "capable_rules": capable_rules,
        "class2_count": class2_count,
        "class2_fraction": fraction,
        "core3_in_band": core,
        "class1_in_band": ordered,
        "passes_regime": bool(capable_rules) and fraction > 0.5 and not core,
    }


def _unimodal(values: Sequence[float], tolerance: float = 0.01) -> bool:
    peak = max(range(len(values)), key=lambda index: values[index])
    reversal_before = any(
        values[index + 1] - values[index] < -tolerance for index in range(peak)
    )
    reversal_after = any(
        values[index + 1] - values[index] > tolerance
        for index in range(peak, len(values) - 1)
    )
    return not (reversal_before or reversal_after)


def _ridge_summary(
    index: dict[tuple[str, int, int, float], dict[str, object]],
    noises: Sequence[float],
    partition: str,
) -> dict[str, object]:
    profiles = {
        rule: [
            _partition_rate(index[("raw4", rule, 64, eta)], partition)
            for eta in noises
        ]
        for rule in RAW_RULES
    }
    ever = [
        rule
        for rule, values in profiles.items()
        if any(STRICT_LOWER <= value <= STRICT_UPPER for value in values)
    ]
    flags = {rule: _unimodal(profiles[rule]) for rule in ever}
    fraction = sum(flags.values()) / len(flags) if flags else 0.0
    peak_eta = {
        str(rule): noises[max(range(len(noises)), key=lambda position: profiles[rule][position])]
        for rule in ever
    }
    return {
        "partition": partition,
        "noise_grid": list(noises),
        "ever_capable_count": len(ever),
        "unimodal_count": sum(flags.values()),
        "unimodal_fraction": fraction,
        "passes_two_thirds": bool(ever) and fraction >= 2 / 3,
        "unimodal_by_rule": {str(rule): value for rule, value in flags.items()},
        "peak_eta_by_rule": peak_eta,
    }


def _named_observer_gate(
    index: dict[tuple[str, int, int, float], dict[str, object]], rule: int
) -> dict[str, object]:
    raw = index[("raw4", rule, 64, 0.01)]
    particle = index[("particle4", rule, 64, 0.01)]
    rows = {}
    for partition in PARTITIONS:
        raw_rate = _partition_rate(raw, partition)
        particle_rate = _partition_rate(particle, partition)
        rows[partition] = {
            "raw_rate": raw_rate,
            "particle_rate": particle_rate,
            "raw_below_band": raw_rate < STRICT_LOWER,
            "particle_in_band": STRICT_LOWER <= particle_rate <= STRICT_UPPER,
            "passes": raw_rate < STRICT_LOWER
            and STRICT_LOWER <= particle_rate <= STRICT_UPPER,
        }
    return {
        "rule": rule,
        "by_partition": rows,
        "passes_all_partitions": all(row["passes"] for row in rows.values()),
    }


def _library_rank(
    index: dict[tuple[str, int, int, float], dict[str, object]], partition: str
) -> dict[str, object]:
    sizes = {
        rule: int(
            index[("raw4", rule, 64, 0.01)]["partitions"][partition][
                "form_library_size"
            ]
        )
        for rule in RAW_RULES
    }
    target = sizes[110]
    minimum = 1 + sum(size > target for size in sizes.values())
    maximum = sum(size >= target for size in sizes.values())
    return {
        "partition": partition,
        "rule110_library_size": target,
        "minimum_tie_rank": minimum,
        "maximum_tie_rank": maximum,
        "average_tie_rank": (minimum + maximum) / 2,
        "top_decile_cutoff": 9,
        "passes_top_decile": minimum <= 9,
        "library_sizes_by_rule": {str(rule): size for rule, size in sizes.items()},
    }


def _paired_observer_rows(
    index: dict[tuple[str, int, int, float], dict[str, object]]
) -> list[dict[str, object]]:
    rows = []
    for rule in PARTICLE_RULES:
        for width, noises in WIDTH_NOISES.items():
            for eta in noises:
                raw = index[("raw4", rule, width, eta)]
                particle = index[("particle4", rule, width, eta)]
                raw_launches = raw["per_launch"]
                particle_launches = particle["per_launch"]
                if len(raw_launches) != 32 or len(particle_launches) != 32:  # type: ignore[arg-type]
                    raise ValueError("paired observer panel lacks 32 launches")
                differences = [
                    float(particle_row["strict_rate"]) - float(raw_row["strict_rate"])
                    for raw_row, particle_row in zip(  # type: ignore[arg-type]
                        raw_launches, particle_launches, strict=True
                    )
                ]
                rows.append(
                    {
                        "rule": rule,
                        "width": width,
                        "flip_noise": eta,
                        "mean_particle_minus_raw": sum(differences) / len(differences),
                        "launch_student_ci95": _student_interval(
                            differences, lower=-1.0, upper=1.0
                        ),
                    }
                )
    return rows


def adjudicate(panels: Sequence[dict[str, object]]) -> dict[str, object]:
    index = _index_panels(panels)
    expected_cells = design_contract()["total_cells"]
    if len(index) != expected_cells:
        raise ValueError(f"expected {expected_cells} cells, found {len(index)}")

    registered_slices = [
        _regime_slice(index, 64, eta, partition)
        for partition in PARTITIONS
        for eta in REGISTERED_NOISES
    ]
    holdout_slices = [
        _regime_slice(index, 64, eta, partition)
        for partition in PARTITIONS
        for eta in HOLDOUT_NOISES
    ]
    width_slices = [
        _regime_slice(index, width, 0.01, partition)
        for partition in PARTITIONS
        for width in WIDTH_NOISES
    ]
    all_raw_cells = [
        (rule, width, eta, index[("raw4", rule, width, eta)])
        for rule in RAW_RULES
        for width, noises in WIDTH_NOISES.items()
        for eta in noises
    ]

    class1_entries = {
        partition: [
            {"rule": rule, "width": width, "flip_noise": eta}
            for rule, width, eta, condition in all_raw_cells
            if rule in CLASS_1 and _capable(condition, partition)
        ]
        for partition in PARTITIONS
    }
    core3_entries = {
        partition: [
            {"rule": rule, "width": width, "flip_noise": eta}
            for rule, width, eta, condition in all_raw_cells
            if rule in CLASS_3_CORE and _capable(condition, partition)
        ]
        for partition in PARTITIONS
    }

    ridge = {
        "registered_five": {
            partition: _ridge_summary(index, REGISTERED_NOISES, partition)
            for partition in PARTITIONS
        },
        "extended_seven": {
            partition: _ridge_summary(index, WIDTH64_NOISES, partition)
            for partition in PARTITIONS
        },
    }
    named_122 = _named_observer_gate(index, 122)
    named_110 = _named_observer_gate(index, 110)
    named_18 = _named_observer_gate(index, 18)

    champions = {}
    for partition in PARTITIONS:
        values = {
            str(rule): _partition_rate(
                index[("particle4", rule, 64, 0.01)], partition
            )
            for rule in RAW_CHAMPIONS
        }
        champions[partition] = {
            "rates": values,
            "passes": all(value >= STRICT_LOWER for value in values.values()),
        }

    particle_class1_entries = {
        partition: [
            {
                "rule": rule,
                "width": width,
                "flip_noise": eta,
                "strict_rate": _partition_rate(
                    index[("particle4", rule, width, eta)], partition
                ),
            }
            for rule in sorted(CLASS_1)
            for width, noises in WIDTH_NOISES.items()
            for eta in noises
            if _capable(index[("particle4", rule, width, eta)], partition)
        ]
        for partition in PARTITIONS
    }

    raw_110_anchor = index[("raw4", 110, 64, 0.01)]
    raw_110_zero = {
        partition: int(
            raw_110_anchor["partitions"][partition]["strict"]["count"]  # type: ignore[index]
        )
        == 0
        for partition in PARTITIONS
    }
    raw_110_below = {
        partition: all(
            _partition_rate(index[("raw4", 110, width, eta)], partition)
            < STRICT_LOWER
            for width, noises in WIDTH_NOISES.items()
            for eta in noises
        )
        for partition in PARTITIONS
    }

    library_ranks = {
        partition: _library_rank(index, partition) for partition in PARTITIONS
    }
    gates = {
        "raw_registered_regime_replication": all(
            row["passes_regime"] for row in registered_slices
        ),
        "raw_holdout_regime_extension": all(
            row["passes_regime"] for row in holdout_slices
        ),
        "raw_width_regime_replication": all(
            row["passes_regime"] for row in width_slices
        ),
        "raw_class1_exclusion": all(not values for values in class1_entries.values()),
        "raw_core3_exclusion": all(not values for values in core3_entries.values()),
        "raw_registered_ridge_replication": all(
            value["passes_two_thirds"]
            for value in ridge["registered_five"].values()
        ),
        "raw_extended_ridge_replication": all(
            value["passes_two_thirds"]
            for value in ridge["extended_seven"].values()
        ),
        "particle_rule122_counterexample": named_122["passes_all_partitions"],
        "particle_rule110_redemption": named_110["passes_all_partitions"],
        "particle_champions_stable": all(
            value["passes"] for value in champions.values()
        ),
        "raw_rule110_exact_zero_anchor": all(raw_110_zero.values()),
        "raw_rule110_below_band_panel": all(raw_110_below.values()),
        "raw_rule110_library_top_decile": all(
            value["passes_top_decile"] for value in library_ranks.values()
        ),
    }
    return {
        "gates": gates,
        "registered_regime_slices": registered_slices,
        "holdout_regime_slices": holdout_slices,
        "width_regime_slices": width_slices,
        "raw_class1_capable_entries": class1_entries,
        "raw_core3_capable_entries": core3_entries,
        "ridge": ridge,
        "named_rule122": named_122,
        "named_rule110": named_110,
        "named_rule18_secondary": named_18,
        "particle_champions": champions,
        "particle_class1_capable_entries": particle_class1_entries,
        "raw_rule110_zero_by_partition": raw_110_zero,
        "raw_rule110_below_band_panel_by_partition": raw_110_below,
        "raw_rule110_library_ranks": library_ranks,
        "paired_observer_strict_differences": _paired_observer_rows(index),
    }


def replay_integrity_checks(
    panels: Sequence[dict[str, object]],
) -> dict[str, object]:
    """Replay the four preregistered launch-zero batches exactly."""

    index = _index_panels(panels)
    checks = []
    for observer in ("raw4", "particle4"):
        for rule in (110, 122):
            domain_codes = None
            dictionary_match = True
            if observer == "particle4":
                dictionary = build_domain_dictionary(
                    rule,
                    64,
                    SCIENTIFIC_NAMESPACE + ":particle-domain",
                )
                domain_codes = dictionary.codes
                panel = next(
                    item
                    for item in panels
                    if item["observer"] == observer
                    and int(item["rule"]) == rule
                    and int(item["width"]) == 64
                )
                dictionary_match = canonical_digest(_dictionary_summary(dictionary)) == canonical_digest(
                    panel["dictionary"]
                )
            contract = LineageContract(
                width=64,
                flip_noise=0.01,
                copy_error=0.015,
                n_launches=32,
                futures_per_launch=64,
                namespace=SCIENTIFIC_NAMESPACE,
                launch_split="a1-all",
            )
            replay = simulate_launch(
                rule,
                0,
                contract,
                observer=observer,  # type: ignore[arg-type]
                domain_codes=domain_codes,
            )
            replay_summary = _launch_summary(replay, 64)
            original = next(
                row
                for row in index[(observer, rule, 64, 0.01)]["per_launch"]  # type: ignore[union-attr]
                if int(row["launch_index"]) == 0
            )
            launch_match = canonical_digest(replay_summary) == canonical_digest(original)
            checks.append(
                {
                    "observer": observer,
                    "rule": rule,
                    "width": 64,
                    "flip_noise": 0.01,
                    "launch_index": 0,
                    "launch_exact_match": launch_match,
                    "dictionary_exact_match": dictionary_match,
                    "passes": launch_match and dictionary_match,
                }
            )
    return {"passes": all(row["passes"] for row in checks), "checks": checks}


def markdown_report(result: dict[str, object]) -> str:
    adjudication = result["adjudication"]
    gates = adjudication["gates"]  # type: ignore[index]
    lines = [
        "# L01/L02 Stage-D A1 fresh ECA result",
        "",
        f"Run: `{result['run_id']}`  ",
        f"Contract digest: `{result['contract_digest']}`  ",
        f"Scientific futures: {result['scientific_future_count']:,}  ",
        f"Runtime: {result['elapsed_seconds']:.3f} seconds  ",
        f"Replay integrity: `{result['replay_integrity']['passes']}`",
        "",
        "## Frozen gates",
        "",
        "| Gate | Result |",
        "|---|---:|",
    ]
    lines.extend(
        f"| `{name}` | **{str(value).upper()}** |" for name, value in gates.items()
    )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "These gates adjudicate only the frozen ECA observer, width, noise, and rule panels. ",
            "They cannot confirm all-substrate necessity, origin-of-life chemistry, Conway Life, ",
            "or population-level computational orthogonality. See the frozen Stage-D protocol ",
            "and machine-readable result for split checks, intervals, rule lists, and tie ranks.",
            "",
        ]
    )
    return "\n".join(lines)
