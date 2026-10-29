"""Outcome-known retained audit for L21's ancestry-selects-the-pen claim."""

from __future__ import annotations

import csv
import io
import itertools
import math
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E69_ancestry_world": "00591e27961e0153932653bfb3642207f6f21ef77834960d7c20737c9f42b010",
    "E71_takeover_race": "e013ff3fbba4e9e34f0ab489010c455042b55c3685b53277b2291fd5e76729de",
}

E69_REGIMES = ("ancestry", "depth2", "recent", "knife", "drift")
E69_DEPTHS = {"ancestry": 8, "depth2": 2, "recent": 1, "knife": 8}
E71_ARMS = ("main", "neutral", "invasion", "churn")
E71_ARM_REPEATS = {"main": 8, "neutral": 8, "invasion": 4, "churn": 4}
TRACKED_PACKAGES = (
    "ancestry_world",
    "takeover_race",
    "injury_clock",
    "blueprint_web",
    "ladder_web",
    "voltage_web",
    "setpoint_rewrite",
    "assimilation",
    "writable_landlord",
    "contract_bridge",
)


def _experiment_root(plastic_root: Path, package: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / package


def _track_package(tracker: InputTracker, root: Path) -> None:
    for relative in ("EXPECTATIONS.md", "pyproject.toml"):
        path = root / relative
        if path.is_file():
            tracker.add(path)
    for directory in ("src", "tests"):
        source = root / directory
        if source.is_dir():
            for path in sorted(source.rglob("*.py")):
                tracker.add(path)


def _read(tracker: InputTracker, path: Path) -> str:
    return tracker.add(path).read_text(encoding="utf-8")


def _recursive_close(left: Any, right: Any) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _recursive_close(left[key], right[key]) for key in left
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            _recursive_close(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return close(float(left), float(right))
    return left == right


def _first_commit(repo_root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
        commits = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                "--follow",
                "--format=%H",
                "--",
                str(relative),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None
    return commits[-1] if commits else None


def _git_provenance(plastic_root: Path) -> dict[str, Any]:
    try:
        repository_root = Path(
            subprocess.run(
                ["git", "-C", str(plastic_root), "rev-parse", "--show-toplevel"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        repository_root = plastic_root.parent
    selected = {
        "ancestry_world": "ancestry_summary.json",
        "takeover_race": "race_summary.json",
    }
    rows: dict[str, Any] = {}
    for package, result in selected.items():
        root = _experiment_root(plastic_root, package)
        expectation_commit = _first_commit(repository_root, root / "EXPECTATIONS.md")
        result_commit = _first_commit(
            repository_root, root / "results/full" / result
        )
        rows[package] = {
            "expectations_first_commit": expectation_commit,
            "selected_result_first_commit": result_commit,
            "same_first_commit_snapshot": bool(
                expectation_commit is not None and expectation_commit == result_commit
            ),
            "prose_date_is_git_verified_temporal_seal": False,
        }
    return {"repository_root": str(repository_root), "packages": rows}


def source_config_digests() -> dict[str, str]:
    """Digest independently transcribed current E69 and E71 defaults."""

    configs: dict[str, dict[str, Any]] = {
        "E69_ancestry_world": {
            "mode": "full",
            "population": 12,
            "generations": 16,
            "n_repeats": 5,
            "tournament": 3,
            "u_box": [0.001, 1.0],
            "mutation_sigma": 0.3,
            "settle_sweeps": 120,
            "cycles": 8,
            "inter_fission": 500,
            "amp_threshold": 0.2,
            "norm": 0.3,
            "rho": 0.002,
            "functional_gap": 0.03,
            "trajectory_seed_tag": "ancestry-world-v1",
        },
        "E71_takeover_race": {
            "mode": "full",
            "n_lineages": 64,
            "generations": 20,
            "invasion_p0": 0.1,
            "fitness_floor": 0.01,
            "u_init": 0.3,
            "u_box": [0.001, 1.0],
            "mutation_sigma": 0.3,
            "settle_sweeps": 120,
            "cycles": 5,
            "inter_fission": 500,
            "amp_threshold": 0.2,
            "norm": 0.3,
            "rho": 0.002,
            "n_shuffle_null": 6,
            "fairness_lives": 12,
            "trajectory_seed_tag": "takeover-race-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def _sample_sd(values: Sequence[float]) -> float:
    return float(np.std(np.asarray(values, dtype=float), ddof=1))


def _geometric_mean(values: Sequence[float]) -> float:
    return float(np.exp(np.mean(np.log(np.asarray(values, dtype=float)))))


def _exhaustive_bootstrap_interval(values: Sequence[float]) -> list[float]:
    """Exact ordinary n-out-of-n percentile bootstrap for the five blocks."""

    data = np.asarray(values, dtype=float)
    means = np.asarray(
        [float(np.mean(data[list(indices)])) for indices in itertools.product(
            range(len(data)), repeat=len(data)
        )],
        dtype=float,
    )
    return [float(value) for value in np.quantile(means, [0.025, 0.975])]


def _exact_sign_flip_upper(values: Sequence[float]) -> float:
    data = np.asarray(values, dtype=float)
    observed = float(np.mean(data))
    null = [
        float(np.mean(data * np.asarray(signs, dtype=float)))
        for signs in itertools.product((-1.0, 1.0), repeat=len(data))
    ]
    return sum(value >= observed - 1e-15 for value in null) / len(null)


def _exact_sign_upper(values: Sequence[float]) -> float:
    nonzero = [value for value in values if not close(value, 0.0)]
    positive = sum(value > 0 for value in nonzero)
    denominator = 2 ** len(nonzero)
    return sum(
        math.comb(len(nonzero), count)
        for count in range(positive, len(nonzero) + 1)
    ) / denominator


def _contrast(name: str, left: Sequence[float], right: Sequence[float]) -> dict[str, Any]:
    differences = [float(a - b) for a, b in zip(left, right)]
    leave_one_out = [
        float(np.mean(differences[:index] + differences[index + 1 :]))
        for index in range(len(differences))
    ]
    return {
        "contrast": name,
        "differences_by_repeat": differences,
        "mean": float(np.mean(differences)),
        "median": float(np.median(differences)),
        "sample_sd": _sample_sd(differences),
        "positive": sum(value > 0 for value in differences),
        "negative": sum(value < 0 for value in differences),
        "zero": sum(close(value, 0.0) for value in differences),
        "exhaustive_block_bootstrap_95": _exhaustive_bootstrap_interval(differences),
        "exact_sign_flip_upper_tail": _exact_sign_flip_upper(differences),
        "exact_sign_test_upper_tail": _exact_sign_upper(differences),
        "leave_one_repeat_out_means": leave_one_out,
        "all_leave_one_repeat_out_means_positive": all(
            value > 0 for value in leave_one_out
        ),
    }


def reference_ages(cycles: int, depth: int, tail_cycles: int = 3) -> list[int]:
    """Age in fissions of the active reference when each tail score is read."""

    age = 0
    ages: list[int] = []
    for cycle in range(cycles):
        age += 1
        if cycle >= cycles - tail_cycles:
            ages.append(age)
        if (cycle + 1) % depth == 0 and cycle < cycles - 1:
            age = 0
    return ages


def _load_e69(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    summary = tracker.json(root / "results/full/ancestry_summary.json")
    pre_payload = tracker.json(root / "results/full/work/preround.json")
    shard_paths = sorted(
        (root / "results/full/work").glob("anc_shard_*_of_10.json")
    )
    if len(shard_paths) != 10:
        raise ValueError(f"expected ten E69 shards, found {len(shard_paths)}")
    expected_jobs = [
        (regime, repeat)
        for regime in E69_REGIMES
        for repeat in range(5)
    ]
    entries: list[dict[str, Any]] = []
    shard_integrity = []
    work_digests = {pre_payload["config_digest"]}
    for shard, path in enumerate(shard_paths):
        payload = tracker.json(path)
        work_digests.add(payload["config_digest"])
        actual = [(entry["regime"], int(entry["repeat"])) for entry in payload["entries"]]
        expected = expected_jobs[shard::10]
        shard_integrity.append(
            {
                "shard": shard,
                "rows": len(actual),
                "actual_jobs": actual,
                "expected_stride_jobs": expected,
                "matches_source_stride": actual == expected,
            }
        )
        entries.extend(payload["entries"])

    keys = [(entry["regime"], int(entry["repeat"])) for entry in entries]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate E69 regime/repeat cell")
    if set(keys) != set(expected_jobs):
        raise ValueError("incomplete or unexpected E69 regime/repeat grid")
    for entry in entries:
        trajectory = entry["trajectory"]
        if [int(row["gen"]) for row in trajectory] != list(range(16)):
            raise ValueError(f"malformed E69 trajectory: {entry['regime']}/{entry['repeat']}")

    by_key = {(entry["regime"], int(entry["repeat"])): entry for entry in entries}
    values = {
        regime: [
            float(by_key[(regime, repeat)]["final_mean_u"])
            for repeat in range(5)
        ]
        for regime in E69_REGIMES
    }
    final_means = {
        regime: float(np.mean(regime_values))
        for regime, regime_values in values.items()
    }
    paired = [
        values["ancestry"][repeat] - values["knife"][repeat]
        for repeat in range(5)
    ]
    contrast = float(np.mean(paired))
    n_positive = sum(value > 0 for value in paired)
    drift_max = [
        float(by_key[("drift", repeat)]["final_max_u"])
        for repeat in range(5)
    ]
    reconstructed = {
        "preround": pre_payload["data"],
        "final_mean_u": final_means,
        "paired_ancestry_minus_knife": paired,
        "contrast": contrast,
        "n_positive_pairs": n_positive,
        "drift_max_u_distribution": drift_max,
        "dose_response": {
            regime: final_means[regime]
            for regime in ("recent", "depth2", "ancestry")
        },
        "gate_p69_1_primary": bool(contrast > 0 and n_positive >= 4),
    }

    initial_u = math.sqrt(0.001)
    population_rows: list[dict[str, Any]] = []
    for regime in E69_REGIMES:
        for repeat in range(5):
            entry = by_key[(regime, repeat)]
            trajectory = entry["trajectory"]
            population_rows.append(
                {
                    "regime": regime,
                    "repeat": repeat,
                    "initial_mean_u": float(trajectory[0]["mean_u"]),
                    "reported_final_mean_u_gen15": float(entry["final_mean_u"]),
                    "change_from_initial": float(entry["final_mean_u"] - initial_u),
                    "final_recorded_mean_fitness_gen15": float(
                        trajectory[-1]["mean_fit"]
                    ),
                    "post_final_reproduction_max_u_gen16": float(entry["final_max_u"]),
                    "trajectory_records": len(trajectory),
                    "completed_transitions_in_reported_mean": len(trajectory) - 1,
                }
            )

    regime_statistics = {}
    functional_bar = float(pre_payload["data"]["functional_bar"])
    for regime, regime_values in values.items():
        regime_statistics[regime] = {
            "values_by_repeat": regime_values,
            "arithmetic_mean": float(np.mean(regime_values)),
            "median": float(np.median(regime_values)),
            "geometric_mean": _geometric_mean(regime_values),
            "sample_sd": _sample_sd(regime_values),
            "arithmetic_mean_minus_initial": float(
                np.mean(regime_values) - initial_u
            ),
            "directions_above_initial": sum(value > initial_u for value in regime_values),
            "final_population_means_at_or_above_functional_bar": sum(
                value >= functional_bar for value in regime_values
            ),
            "all_generation_mean_fitness": float(
                np.mean(
                    [
                        row["mean_fit"]
                        for repeat in range(5)
                        for row in by_key[(regime, repeat)]["trajectory"]
                    ]
                )
            ),
        }

    contrasts = {
        "ancestry_minus_knife": _contrast(
            "ancestry-minus-knife", values["ancestry"], values["knife"]
        ),
        "ancestry_minus_drift": _contrast(
            "ancestry-minus-drift", values["ancestry"], values["drift"]
        ),
        "ancestry_minus_depth2": _contrast(
            "ancestry-minus-depth2", values["ancestry"], values["depth2"]
        ),
        "depth2_minus_recent": _contrast(
            "depth2-minus-recent", values["depth2"], values["recent"]
        ),
        "recent_minus_drift": _contrast(
            "recent-minus-drift", values["recent"], values["drift"]
        ),
        "depth2_minus_drift": _contrast(
            "depth2-minus-drift", values["depth2"], values["drift"]
        ),
        "knife_minus_drift": _contrast(
            "knife-minus-drift", values["knife"], values["drift"]
        ),
    }
    primary = contrasts["ancestry_minus_knife"]
    total_primary = sum(primary["differences_by_repeat"])
    largest_index = int(np.argmax(primary["differences_by_repeat"]))
    primary["largest_positive_repeat"] = largest_index
    primary["largest_positive_contribution_fraction_of_sum"] = float(
        primary["differences_by_repeat"][largest_index] / total_primary
    )
    primary["approximate_t_95_interval_df4"] = [
        float(primary["mean"] - 2.7764451051977987 * primary["sample_sd"] / math.sqrt(5)),
        float(primary["mean"] + 2.7764451051977987 * primary["sample_sd"] / math.sqrt(5)),
    ]

    pre_rows = pre_payload["data"]["rows"]
    pre_base = float(pre_rows[0]["fitness"])
    pre_advantage = float(pre_payload["data"]["positive_control_advantage"])
    s_min = float(pre_payload["data"]["s_min"])
    pre_audit = {
        "rows": pre_rows,
        "fitness_minus_u_min": [float(row["fitness"] - pre_base) for row in pre_rows],
        "functional_bar": functional_bar,
        "functional_bar_is_grid_top": functional_bar == max(
            float(row["u"]) for row in pre_rows
        ),
        "functional_bar_is_gene_box_ceiling": close(functional_bar, 1.0),
        "positive_control_advantage": pre_advantage,
        "s_min_labelled_1_over_population": s_min,
        "positive_control_slack_over_s_min": pre_advantage - s_min,
        "relative_fitness_advantage_over_u_min": pre_advantage / pre_base,
        "fitness_strictly_monotone_over_grid": all(
            float(right["fitness"]) > float(left["fitness"])
            for left, right in zip(pre_rows, pre_rows[1:])
        ),
        "lives_per_u": 3,
        "u_levels_share_random_streams": False,
        "raw_fidelity_gap_is_tournament_selection_coefficient": False,
        "effective_population_size_estimated": False,
    }

    depth_audit = {
        "reference_age_in_fissions_at_tail_scores": {
            regime: reference_ages(8, depth)
            for regime, depth in (
                ("recent", 1),
                ("depth2", 2),
                ("ancestry", 8),
            )
        },
        "arithmetic_mean_order_recent_depth2_ancestry": (
            final_means["recent"] < final_means["depth2"] < final_means["ancestry"]
        ),
        "median_order_recent_depth2_ancestry": (
            regime_statistics["recent"]["median"]
            < regime_statistics["depth2"]["median"]
            < regime_statistics["ancestry"]["median"]
        ),
        "geometric_mean_order_recent_depth2_ancestry": (
            regime_statistics["recent"]["geometric_mean"]
            < regime_statistics["depth2"]["geometric_mean"]
            < regime_statistics["ancestry"]["geometric_mean"]
        ),
        "full_within_repeat_order_count": sum(
            values["recent"][repeat]
            < values["depth2"][repeat]
            < values["ancestry"][repeat]
            for repeat in range(5)
        ),
        "depth2_above_recent_repeat_count": sum(
            values["depth2"][repeat] > values["recent"][repeat]
            for repeat in range(5)
        ),
        "ancestry_above_depth2_repeat_count": sum(
            values["ancestry"][repeat] > values["depth2"][repeat]
            for repeat in range(5)
        ),
        "registered_depths": [1, 2, 4, 8, 12],
        "implemented_depths": [1, 2, 8],
        "missing_registered_depths": [4, 12],
        "restoring_force_covariate_implemented": False,
        "three_irregular_points_establish_proportionality": False,
    }

    inheritance = {
        "ancestry_arithmetic_mean": final_means["ancestry"],
        "knife_arithmetic_mean": final_means["knife"],
        "drift_arithmetic_mean": final_means["drift"],
        "posthoc_ancestry_minus_knife_fraction_of_ancestry": (
            (final_means["ancestry"] - final_means["knife"])
            / final_means["ancestry"]
        ),
        "posthoc_contrast_fraction_of_ancestry_excess_over_drift": (
            (final_means["ancestry"] - final_means["knife"])
            / (final_means["ancestry"] - final_means["drift"])
        ),
        "ordinary_theta_explicitly_copied_at_fission": False,
        "ordinary_theta_same_array_persists_in_single_successor_loop": True,
        "knife_resets_theta_after_every_fission": True,
        "knife_writing_resumes_for_each_regrowth_window": True,
        "regrowth_write_opportunities_per_cycle": 500,
        "fixed_u_ancestry_knife_fitness_factorial_retained": False,
        "additive_heritable_share_identified": False,
        "founder_captured_after_u_dependent_settle": True,
    }

    source_audit = {
        "population": 12,
        "generations_evaluated": 16,
        "reported_endpoint_completed_evolutionary_transitions": 15,
        "inter_fission_sweeps": 500,
        "wave15_frozen_population": 16,
        "wave15_frozen_generations": 24,
        "wave15_frozen_inter_fission_sweeps": 1000,
        "expectations_record_reduced_12_by_16_budget": True,
        "expectations_record_inter_fission_budget_calibration": True,
        "formal_wave15_amendment_located": False,
        "selection_operator": "tournament-of-three on one stochastic life per candidate",
        "individual_u_fitness_rows_retained": False,
        "genotype_fitness_covariance_reconstructable": False,
        "selection_differential_reconstructable": False,
        "mutation_is_zero_mean_in_log_u": True,
        "unclipped_arithmetic_offspring_multiplier": math.exp(0.3**2 / 2),
        "drift_arithmetic_mean_minus_initial": final_means["drift"] - initial_u,
        "reported_final_mean_generation": 15,
        "reported_drift_max_generation": 16,
        "drift_mean_and_max_share_endpoint": False,
        "regime_and_eval_seed_addresses_include_regime": True,
        "repeat_index_reuses_tissue_parameters": True,
        "pairs_are_common_random_number_pairs": False,
        "pairs_are_tissue_parameter_blocks": True,
    }

    e69 = {
        "retained_config_digest": summary["config_digest"],
        "work_config_digests": sorted(work_digests),
        "all_work_digests_match_summary": work_digests == {summary["config_digest"]},
        "shard_integrity": shard_integrity,
        "all_shards_match_source_stride": all(
            row["matches_source_stride"] for row in shard_integrity
        ),
        "retained_cells": len(entries),
        "unique_cells": len(set(keys)),
        "trajectory_records": sum(len(entry["trajectory"]) for entry in entries),
        "preround_cache_matches_summary": _recursive_close(
            pre_payload["data"], summary["gates"]["preround"]
        ),
        "reconstructed_gates": reconstructed,
        "reported_gates": summary["gates"],
        "all_reported_gates_reconstruct": _recursive_close(
            reconstructed, summary["gates"]
        ),
        "initial_u": initial_u,
        "regime_statistics": regime_statistics,
        "contrasts": contrasts,
        "preround_audit": pre_audit,
        "depth_audit": depth_audit,
        "inheritance_audit": inheritance,
        "source_and_endpoint_audit": source_audit,
    }
    return e69, population_rows, entries


def _slope_s(freqs: Sequence[float]) -> float | None:
    points = [
        (time, math.log(float(p) / (1.0 - float(p))))
        for time, p in enumerate(freqs)
        if 0.02 < float(p) < 0.98
    ]
    if len(points) < 4:
        return None
    xs = np.asarray([point[0] for point in points], dtype=float)
    ys = np.asarray([point[1] for point in points], dtype=float)
    return float(np.polyfit(xs, ys, 1)[0])


def _load_e71(
    root: Path, tracker: InputTracker, e69_functional_bar: float
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = tracker.json(root / "results/full/race_summary.json")
    fair_payload = tracker.json(root / "results/full/work/fairness.json")
    shard_paths = sorted(
        (root / "results/full/work").glob("race_shard_*_of_12.json")
    )
    if len(shard_paths) != 12:
        raise ValueError(f"expected twelve E71 shards, found {len(shard_paths)}")
    jobs = [
        (arm, repeat)
        for arm in E71_ARMS
        for repeat in range(E71_ARM_REPEATS[arm])
    ] + [("shuffled", repeat) for repeat in range(6)]
    entries: list[dict[str, Any]] = []
    shard_integrity = []
    work_digests = {fair_payload["config_digest"]}
    for shard, path in enumerate(shard_paths):
        payload = tracker.json(path)
        work_digests.add(payload["config_digest"])
        actual = [(entry["arm"], int(entry["repeat"])) for entry in payload["entries"]]
        expected = jobs[shard::12]
        shard_integrity.append(
            {
                "shard": shard,
                "rows": len(actual),
                "actual_jobs": actual,
                "expected_stride_jobs": expected,
                "matches_source_stride": actual == expected,
            }
        )
        entries.extend(payload["entries"])
    keys = [(entry["arm"], int(entry["repeat"])) for entry in entries]
    if len(set(keys)) != len(keys) or set(keys) != set(jobs):
        raise ValueError("incomplete, duplicate, or unexpected E71 arm/repeat grid")

    def rows(arm: str) -> list[dict[str, Any]]:
        # Preserve concatenated shard order because the historical summary did.
        return [entry for entry in entries if entry["arm"] == arm]

    main_slopes = [
        slope for slope in (_slope_s(entry["freqs"]) for entry in rows("main"))
        if slope is not None
    ]
    null_slopes = [
        slope
        for slope in (_slope_s(entry["freqs"]) for entry in rows("shuffled"))
        if slope is not None
    ]
    mean_s = float(np.mean(main_slopes))
    null_q95 = float(np.quantile(null_slopes, 0.95))
    u_ok_source = all(
        (entry["mean_u_cascade_final"] or 0) > 0.01
        for entry in rows("main")
        if entry["final_freq"] > 0.5
    )
    reconstructed = {
        "fairness": fair_payload["data"],
        "s_main_per_repeat": main_slopes,
        "s_mean": mean_s,
        "s_null_distribution": null_slopes,
        "s_null_q95": null_q95,
        "final_freqs": {
            arm: [float(entry["final_freq"]) for entry in rows(arm)]
            for arm in list(E71_ARMS) + ["shuffled"]
        },
        "invasion_establishment": float(
            np.mean([entry["final_freq"] > 0.5 for entry in rows("invasion")])
        ),
        "winners_u_functional": bool(u_ok_source),
        "gate_p71_1_primary": bool(
            mean_s > null_q95 and min(main_slopes) > 0 and u_ok_source
        ),
    }
    main_rows_sorted = sorted(rows("main"), key=lambda row: int(row["repeat"]))
    main_final_u = [float(row["mean_u_cascade_final"]) for row in main_rows_sorted]
    race_rows = [
        {
            "arm": entry["arm"],
            "repeat": int(entry["repeat"]),
            "trajectory_points": len(entry["freqs"]),
            "initial_frequency": float(entry["freqs"][0]),
            "reported_final_frequency": float(entry["final_freq"]),
            "effective_log_odds_slope": _slope_s(entry["freqs"]),
            "reported_final_mean_u_cascade": (
                None
                if entry["mean_u_cascade_final"] is None
                else float(entry["mean_u_cascade_final"])
            ),
        }
        for entry in entries
    ]
    e71 = {
        "retained_config_digest": summary["config_digest"],
        "work_config_digests": sorted(work_digests),
        "all_work_digests_match_summary": work_digests == {summary["config_digest"]},
        "shard_integrity": shard_integrity,
        "all_shards_match_source_stride": all(
            row["matches_source_stride"] for row in shard_integrity
        ),
        "retained_rows": len(entries),
        "unique_rows": len(set(keys)),
        "reconstructed_gates": reconstructed,
        "reported_gates": summary["gates"],
        "all_reported_gates_reconstruct": _recursive_close(
            reconstructed, summary["gates"]
        ),
        "primary_audit": {
            "reported_primary_passes": bool(summary["gates"]["gate_p71_1_primary"]),
            "main_slope_mean": mean_s,
            "main_slope_median": float(np.median(main_slopes)),
            "main_slope_range": [min(main_slopes), max(main_slopes)],
            "positive_main_slopes": sum(value > 0 for value in main_slopes),
            "main_repeat_count": len(main_slopes),
            "frozen_wave15_main_repeat_count": 12,
            "exact_all_positive_sign_probability": 0.5 ** len(main_slopes),
            "shuffled_null_draws": len(null_slopes),
            "null_q95_minus_main_mean": null_q95 - mean_s,
            "empirical_null_values_at_or_above_main_mean": sum(
                value >= mean_s for value in null_slopes
            ),
            "source_computes_pooled_slope": False,
            "source_averages_per_repeat_slopes": True,
            "registered_confidence_interval_computed": False,
            "failed_gate_may_be_upgraded_from_directions": False,
        },
        "functional_winner_audit": {
            "source_threshold": 0.01,
            "E69_functional_bar": e69_functional_bar,
            "main_final_mean_u_by_repeat": main_final_u,
            "all_source_winner_checks_pass": u_ok_source,
            "main_means_at_or_above_E69_functional_bar": sum(
                value >= e69_functional_bar for value in main_final_u
            ),
            "source_threshold_matches_E69_functional_bar": close(
                0.01, e69_functional_bar
            ),
        },
        "control_audit": {
            "churn_description": "unaligned theta perturbation of matched magnitude",
            "churn_implementation": "ordinary endogenous life_fitness writer at u=0.02",
            "churn_theta_is_explicitly_unaligned": False,
            "churn_magnitude_is_measured_and_matched": False,
            "churn_supports_alignment_not_churn_claim": False,
            "fairness_arms_share_random_streams": False,
            "fairness_gen0_gap": float(fair_payload["data"]["gen0_gap"]),
            "ancestry_tail_reference_ages_with_five_cycles": reference_ages(5, 8),
            "race_uses_at_least_eight_fissions": False,
            "nonfixed_last_reproduction_is_recorded_in_final_frequency": False,
        },
    }
    return e71, race_rows


def _e64_converse_audit(root: Path, tracker: InputTracker) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/injury_summary.json")
    source = _read(tracker, root / "src/injury_clock/pipeline.py")
    return {
        "retained_config_digest": summary["config_digest"],
        "score_lag_sweeps": 150,
        "injury_intervals": [150, 300, 600],
        "target_is_immediate_pre_insult_state": "pre = V.copy()" in source,
        "score_always_read_at_fixed_lag": "sweep == config.score_lag - 1" in source,
        "target_age_varies_across_injury_regimes": False,
        "unscored_post_score_sweeps_per_insult": [0, 150, 450],
        "ancestor_referenced_secondary_implemented": False,
        "prior_L19_work_state": "RECALCULATED",
        "can_supply_target_depth_converse": False,
    }


def run_l21_audit(
    plastic_root: Path, workspace: Path
) -> tuple[
    dict[str, Any],
    list[Path],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[Path, str],
]:
    tracker = InputTracker()
    ideas_root = plastic_root / IDEAS_RELATIVE
    narrative_paths = (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas_root / "LAWS.md",
        ideas_root / "WAVE14_PROPHECIES.md",
        ideas_root / "WAVE15_PROPHECIES.md",
        ideas_root / "WAVE15_DESIGN_REVIEW.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        workspace / "SOURCE_BASELINE.md",
        workspace / "REVIEW_PROTOCOL.md",
        workspace / "protocols/L21_ANCESTRY_SELECTS_PEN_AUDIT_V1.md",
        workspace / "laws/L21_ancestry_selects_pen.md",
        workspace / "reviews/L19_INCORRUPTIBLE_REFERENCE_AUDIT_2026-09-03.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative_paths}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    e69, population_rows, _ = _load_e69(
        _experiment_root(plastic_root, "ancestry_world"), tracker
    )
    e71, race_rows = _load_e71(
        _experiment_root(plastic_root, "takeover_race"),
        tracker,
        float(e69["preround_audit"]["functional_bar"]),
    )
    e64 = _e64_converse_audit(
        _experiment_root(plastic_root, "injury_clock"), tracker
    )

    source_digests = source_config_digests()
    retained_digests = {
        "E69_ancestry_world": e69["retained_config_digest"],
        "E71_takeover_race": e71["retained_config_digest"],
    }
    digest_matches = {
        name: source_digests[name]
        == retained_digests[name]
        == EXPECTED_CONFIG_DIGESTS[name]
        for name in EXPECTED_CONFIG_DIGESTS
    }
    primary = e69["contrasts"]["ancestry_minus_knife"]
    dose = e69["depth_audit"]

    claims = [
        {
            "claim": "Arithmetic population-mean u is ordered recent .034 < depth2 .051 < founder .243",
            "verdict": "CONFIRMED_AS_REPORTED_ONLY",
            "evidence_level": "E3",
            "reason": (
                "All 25 rows reconstruct those three means exactly. No matched block has the full three-level order, depth2 exceeds recent in only 1/5, and median and geometric-mean summaries reverse the recent/depth2 step. Depths 4 and 12 and the promised restoring-force covariate are absent, so proportional depth response is not established."
            ),
        },
        {
            "claim": "Founder scoring selects more writing than the theta-reset knife under the registered paired gate",
            "verdict": "CONFIRMED_AS_CODED",
            "evidence_level": "E3",
            "reason": (
                "The retained arithmetic contrast is +.169225 with 4/5 positive tissue blocks, exactly satisfying the source Boolean; ancestry also exceeds neutral drift in 5/5 blocks. The primary sign-flip tail is .09375, sign-test tail .1875, and approximate t interval includes zero. Blocks share tissue parameters but not evolutionary or evaluation random streams."
            ),
        },
        {
            "claim": "Most selected value is attributable to heritable transmission rather than within-life pinning",
            "verdict": "NOT_CONFIRMED_AS_WORDED",
            "evidence_level": "E3",
            "reason": (
                "The post-hoc arithmetic ratio (ancestry-knifed)/ancestry is about 70%, but it is not an identified additive decomposition. The ordinary arm persistently retains one theta array; the knife resets it after fission and then resumes writing for 500 sweeps. There is no fixed-u paired fitness factorial, noisy copy, branch, or retained genotype-fitness covariance, and all evolved means remain below the pre-round functional bar u=1."
            ),
        },
        {
            "claim": "The world's scoring horizon controls both memory speed and writability",
            "verdict": "NOT_CONFIRMED_AS_WORDED",
            "evidence_level": "E3",
            "reason": (
                "E69 changes reference refresh schedules but its tail target ages are 1/1/1, 2/1/2, and 6/7/8 fissions; it does not evolve R's rho. E64 evolves rho across injury recurrence/exposure while always scoring the immediate pre-insult state at age 150. These are separate confounded experiments, not a crossed horizon-by-speed/writing design or a converse."
            ),
        },
        {
            "claim": "Writing is selected if and only if deep ancestry is scored",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "One engineered founder-reference contrast cannot establish necessity or sufficiency over a declared world class. Only three schedules were implemented, shallow nulls lack a calibrated absence test, the founder mean is below the coarse functional bar, and the direct E71 race failed its registered certification. Other environments capable of selecting writing were not searched."
            ),
        },
    ]

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L21",
        "audit_kind": "outcome-known E69 retained-row reconstruction, source causal audit, E64 converse check, and bounded E71 modifier",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "source_config_digests": source_digests,
        "retained_config_digests": retained_digests,
        "expected_config_digests": EXPECTED_CONFIG_DIGESTS,
        "source_config_digest_matches": digest_matches,
        "all_source_config_digests_match": all(digest_matches.values()),
        "git_provenance": _git_provenance(plastic_root),
        "document_checks": {
            "law_uses_if_and_only_if": "if and only if" in texts["LAWS.md"],
            "wave15_requires_depths_1_2_4_8_12": "{1,2,4,8,12}" in texts[
                "WAVE15_PROPHECIES.md"
            ],
            "wave15_requires_restoring_force_covariate": "restoring-force covariate"
            in texts["WAVE15_PROPHECIES.md"],
            "discovery_records_evolved_mean_below_functional_bar": "evolved mean sits below"
            in texts["DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md"],
            "L19_records_E64_target_depth_error": "target-depth error"
            in texts["L19_INCORRUPTIBLE_REFERENCE_AUDIT_2026-09-03.md"],
            "v23_places_population_selection_as_next_layer": "Population competition and repeated mutation–selection cycles are the next experimental layer"
            in texts["PRE_PRINT_PAPER_DRAFT_V2.3.md"],
        },
        "E69_ancestry_world": e69,
        "E64_claimed_converse": e64,
        "E71_bounded_modifier": e71,
        "quantifier_audit": {
            "implemented_E69_reference_schedules": 3,
            "registered_reference_schedules": 5,
            "declared_universe_of_worlds": False,
            "necessity_tested": False,
            "sufficiency_beyond_this_engineered_sheet_tested": False,
            "E64_supplies_independent_deep_target_speed_result": False,
            "E71_registered_primary_passes": False,
            "if_and_only_if_supported": False,
        },
        "claim_assessment": claims,
        "strongest_supported_wording": (
            "In E69's engineered 16x16 sheet, five retained tissue-block runs reconstruct the preregistered arithmetic endpoint: final population-mean u is .034 for immediate-reference refresh, .051 for refresh interval two, .243 for a fixed founder, and .073 when theta is reset after every fission in the founder world. Founder minus reset is +.169 with 4/5 directions, and founder exceeds neutral drift in 5/5 blocks. This is bounded evidence that retaining writable theta across fissions can be favoured when fitness rewards similarity to each candidate's fixed founder. It does not establish a proportional depth law, a functional evolved write level, an additive mostly-heritable share, a target-depth converse with E64, or an if-and-only-if origin of writability."
        ),
        "closer_pass_target": (
            "After L24's first pass, freeze a common-random-number depth-by-boundary factorial with target ages 1, 2, 4, 8, and 12 under equal cycle count, exposure, score count, baseline difficulty, and common prescribed founders; population and generation budgets powered before launch; theta persist/reset/noisy-copy and writer-on/off phases crossed at fixed u; R reset/inherit controls; individual genotype, fitness, parent, and offspring rows retained; selection differentials and restoring-force covariates measured; neutral mutation controls on log and arithmetic scales; and a prospectively powered direct takeover race. Necessity wording additionally requires a declared environment class and counterexample search."
        ),
        "headline_diagnostics": {
            "primary_mean": primary["mean"],
            "primary_median": primary["median"],
            "primary_positive_blocks": primary["positive"],
            "primary_exact_sign_flip_upper_tail": primary[
                "exact_sign_flip_upper_tail"
            ],
            "primary_exact_sign_test_upper_tail": primary[
                "exact_sign_test_upper_tail"
            ],
            "primary_approximate_t_interval": primary[
                "approximate_t_95_interval_df4"
            ],
            "full_within_block_depth_order_count": dose[
                "full_within_repeat_order_count"
            ],
            "E71_gate_passes": e71["primary_audit"]["reported_primary_passes"],
        },
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return audit, sorted(tracker.paths), population_rows, race_rows, frozen_hashes


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return buffer.getvalue()


POPULATION_FIELDS = (
    "regime",
    "repeat",
    "initial_mean_u",
    "reported_final_mean_u_gen15",
    "change_from_initial",
    "final_recorded_mean_fitness_gen15",
    "post_final_reproduction_max_u_gen16",
    "trajectory_records",
    "completed_transitions_in_reported_mean",
)
RACE_FIELDS = (
    "arm",
    "repeat",
    "trajectory_points",
    "initial_frequency",
    "reported_final_frequency",
    "effective_log_odds_slope",
    "reported_final_mean_u_cascade",
)


def population_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, POPULATION_FIELDS)


def race_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, RACE_FIELDS)


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e69 = audit["E69_ancestry_world"]
    regimes = e69["regime_statistics"]
    primary = e69["contrasts"]["ancestry_minus_knife"]
    anc_drift = e69["contrasts"]["ancestry_minus_drift"]
    depth = e69["depth_audit"]
    pre = e69["preround_audit"]
    source = e69["source_and_endpoint_audit"]
    inheritance = e69["inheritance_audit"]
    e71 = audit["E71_bounded_modifier"]
    e64 = audit["E64_claimed_converse"]
    lines = [
        "# L21 retained ancestry-selection audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained/source audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "A bounded signal survives, but the law does not. E69's complete retained rows exactly reproduce the registered founder-minus-reset arithmetic contrast: +.169 with four of five tissue blocks positive. Founder scoring also finishes above neutral drift in all five blocks. Within this engineered task, keeping writable theta across fissions is therefore a credible contributor when fitness rewards resemblance to an organism's own fixed founder.",
        "",
        "The advertised depth law is an aggregate illusion at this resolution. None of the five matched tissue blocks has recent < depth2 < founder. Depth2 beats recent in only one block; their medians and geometric means reverse. The run omitted registered depths 4 and 12 and the restoring-force covariate, used smaller budgets than Wave 15 froze, and never established that evolved u was functional. E64 did not run a deep-target arm, so it cannot be the converse. The `if and only if` is unsupported.",
        "",
        "## Retained E69 endpoints",
        "",
        "| Regime | Arithmetic mean u | Median u | Geometric mean u | Above initial, blocks | At functional bar, blocks |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for regime in E69_REGIMES:
        row = regimes[regime]
        lines.append(
            f"| {regime} | {_fmt(row['arithmetic_mean'])} | {_fmt(row['median'])} | {_fmt(row['geometric_mean'])} | {row['directions_above_initial']}/5 | {row['final_population_means_at_or_above_functional_bar']}/5 |"
        )
    lines.extend(
        [
            "",
            f"Every summary field and Boolean reconstructs from 25 unique regime/repeat rows and {e69['trajectory_records']} generation records. All ten shard strides and the pre-round cache match the retained digest. The common initial u is {_fmt(e69['initial_u'])}.",
            "",
            "The arithmetic endpoint is the one registered, so its exact reconstruction matters. But u mutates symmetrically in log space, not arithmetic space. Before clipping, neutral mutation alone multiplies expected arithmetic u by "
            f"{_fmt(source['unclipped_arithmetic_offspring_multiplier'])} per transition; retained drift rises from {_fmt(e69['initial_u'])} to {_fmt(regimes['drift']['arithmetic_mean'])}. Medians and geometric means are therefore essential sensitivity summaries, not replacements smuggled into the gate.",
            "",
            "## Primary founder-minus-reset contrast",
            "",
            "| Diagnostic | Result |",
            "|---|---:|",
            f"| Mean ancestry−knife | {_fmt(primary['mean'])} |",
            f"| Median ancestry−knife | {_fmt(primary['median'])} |",
            f"| Positive blocks | {primary['positive']}/5 |",
            f"| Exhaustive block-bootstrap 95% interval | [{_fmt(primary['exhaustive_block_bootstrap_95'][0])}, {_fmt(primary['exhaustive_block_bootstrap_95'][1])}] |",
            f"| Exact sign-flip upper tail | {_fmt(primary['exact_sign_flip_upper_tail'])} |",
            f"| Exact sign-test upper tail | {_fmt(primary['exact_sign_test_upper_tail'])} |",
            f"| Approximate t 95% interval (df=4) | [{_fmt(primary['approximate_t_95_interval_df4'][0])}, {_fmt(primary['approximate_t_95_interval_df4'][1])}] |",
            f"| Mean ancestry−drift | {_fmt(anc_drift['mean'])} ({anc_drift['positive']}/5 positive) |",
            "",
            "The five ancestry-minus-knife differences are "
            + ", ".join(_fmt(value) for value in primary["differences_by_repeat"])
            + ". Repeat 1 contributes "
            + _fmt(100 * primary["largest_positive_contribution_fraction_of_sum"], 1)
            + "% of their sum, although every leave-one-block mean remains positive (range "
            + _fmt(min(primary["leave_one_repeat_out_means"]))
            + " to "
            + _fmt(max(primary["leave_one_repeat_out_means"]))
            + "). The exact source gate asks only for a positive mean and at least four positive directions, so it passes and is confirmed as coded. The diagnostics show why that is not equivalent to a precise, conventionally certified population effect.",
            "",
            "Equal repeat numbers reuse the same tissue-parameter index. They do not reuse the same random stream: regime appears in the evolutionary stream and in every genotype evaluation address. These are tissue-block contrasts, not common-random-number pairs. E69 retains only population mean u and mean fitness, so genotype-fitness covariance, parent choices, and selection differentials cannot be reconstructed.",
            "",
            "## The coarse functional pre-round",
            "",
            "| u | Mean fitness | Difference from u=.001 |",
            "|---:|---:|---:|",
        ]
    )
    for row, difference in zip(pre["rows"], pre["fitness_minus_u_min"]):
        lines.append(
            f"| {_fmt(row['u'], 3)} | {_fmt(row['fitness'])} | {_fmt(difference)} |"
        )
    lines.extend(
        [
            "",
            f"Only u=1 clears the source's +.03 functional rule. It is both the coarse grid top and gene-box ceiling. Its advantage {_fmt(pre['positive_control_advantage'])} clears the labelled 1/N value {_fmt(pre['s_min_labelled_1_over_population'])} by {_fmt(pre['positive_control_slack_over_s_min'])}. Each u uses only three lives and a different RNG namespace; the response is non-monotone below the top.",
            "",
            "More fundamentally, E69 selects by tournament rank. A raw 0-to-1 fidelity difference is not a selection coefficient on the 1/N scale, and no effective population size was estimated. Every retained final population mean—including founder—lies below u=1. The data leave open a useful gradient somewhere in the unsampled .2–1 interval, but they do not show that the selected endpoint crosses the pre-round's own within-life functional bar.",
            "",
            "## What `depth` actually means",
            "",
            "| Label | Refresh interval | Reference ages at scored tail cycles | Arithmetic mean u |",
            "|---|---:|---|---:|",
            f"| recent | 1 | {depth['reference_age_in_fissions_at_tail_scores']['recent']} | {_fmt(regimes['recent']['arithmetic_mean'])} |",
            f"| depth2 | 2 | {depth['reference_age_in_fissions_at_tail_scores']['depth2']} | {_fmt(regimes['depth2']['arithmetic_mean'])} |",
            f"| founder | 8/no refresh | {depth['reference_age_in_fissions_at_tail_scores']['ancestry']} | {_fmt(regimes['ancestry']['arithmetic_mean'])} |",
            "",
            "Scoring occurs before refresh. Thus depth2's three tail scores use references aged 2, 1, and 2 fissions; the founder scores use ages 6, 7, and 8. `Depth` is a refresh interval, not a constant score age, and only one founder score reaches eight fissions.",
            "",
            f"The arithmetic means are ordered, but full recent < depth2 < founder order occurs in {depth['full_within_repeat_order_count']}/5 blocks. Depth2 exceeds recent in {depth['depth2_above_recent_repeat_count']}/5; founder exceeds depth2 in {depth['ancestry_above_depth2_repeat_count']}/5. Median depth2 {_fmt(regimes['depth2']['median'])} is below recent {_fmt(regimes['recent']['median'])}, as is geometric mean depth2 {_fmt(regimes['depth2']['geometric_mean'])} versus recent {_fmt(regimes['recent']['geometric_mean'])}. The promised depth-4/depth-12 points and restoring-force covariate do not exist.",
            "",
            "The objectives also differ greatly in ceiling and noise: mean fitness across all retained generations is "
            + ", ".join(
                f"{regime} {_fmt(regimes[regime]['all_generation_mean_fitness'])}"
                for regime in E69_REGIMES
            )
            + ". Each candidate's founder is captured after u-dependent settling, rather than being a common prescribed target. Horizon, target difficulty, self-reference, and credit assignment are consequently entangled.",
            "",
            "## Persistent theta is not an additive heritable percentage",
            "",
            f"Ancestry mean u is {_fmt(inheritance['ancestry_arithmetic_mean'])}; knife is {_fmt(inheritance['knife_arithmetic_mean'])}. Their difference is {100 * inheritance['posthoc_ancestry_minus_knife_fraction_of_ancestry']:.1f}% of the ancestry mean and {100 * inheritance['posthoc_contrast_fraction_of_ancestry_excess_over_drift']:.1f}% of ancestry's excess over drift. Those are post-hoc ratios of evolved endpoints, not a causal partition.",
            "",
            "In the ordinary arm, theta is not copied by the fission function; the same array persists in one Python successor loop. The knife resets theta to projected native immediately after every fission, then permits 500 ordinary write updates during regrowth. This is a meaningful persist-versus-reset intervention. But separate populations and streams evolve under nonlinear fitness, with no fixed-u ancestry/knife assay, branch-copy operation, noise dose, or writer-phase factorial. The defensible inference is a contribution from persistent writable state in this construction—not that 70% of selection is transmission.",
            "",
            "## Budget and endpoint departures",
            "",
            "Wave 15 froze population 16, 24 generations, and 1,000 inter-fission sweeps. The E69 expectation file records a reduced 12 × 16 × 500 budget before the full run, but no formal amendment to the frozen wave contract was located. The reduction matters because the result has only five noisy blocks and the pre-round barely clears its sensitivity label.",
            "",
            "The source records generations 0–15, then reproduces once more. `final_mean_u` is generation 15 before that reproduction and therefore includes 15 completed transitions; `final_max_u` is taken from the unscored generation-16 offspring. The primary means are internally aligned, but the highlighted drift-max distribution is one transition later.",
            "",
            "## E64 is not the converse",
            "",
            f"E64 uses injury intervals {e64['injury_intervals']} but always copies the immediate pre-insult V and scores it {e64['score_lag_sweeps']} sweeps later. Longer intervals add 0, 150, or 450 unscored sweeps per insult and alter recurrence, exposure, and evaluation cost. Its promised ancestor-referenced secondary was not run. E64 may have motivated E69; it did not independently show target depth selecting memory speed.",
            "",
            "## E71 remains an uncertified modifier",
            "",
            f"The retained direct race reconstructs exactly: all {e71['primary_audit']['positive_main_slopes']}/{e71['primary_audit']['main_repeat_count']} main effective log-odds slopes are positive, mean {_fmt(e71['primary_audit']['main_slope_mean'])}, but the six-draw shuffled-null q95 is {_fmt(e71['reconstructed_gates']['s_null_q95'])}. The primary misses by {_fmt(e71['primary_audit']['null_q95_minus_main_mean'])} and remains false. The all-positive sign pattern is descriptively notable (symmetric-sign probability {_fmt(e71['primary_audit']['exact_all_positive_sign_probability'])}), but it does not replace the frozen gate.",
            "",
            "E71 also implements eight main repeats rather than the wave's twelve, averages per-repeat slopes rather than fitting the declared pooled slope, and computes no confidence interval. Its `functional` winner threshold is u>.01, while E69's measured bar is u=1; all main mean-u endpoints are below that bar. The churn arm is ordinary endogenous writing at u=.02, not an explicitly unaligned theta perturbation of measured matched magnitude. It cannot confirm alignment-versus-churn. The race is useful directional follow-on evidence, not certification of L21.",
            "",
            "## Clause adjudication",
            "",
            "| Atomic claim | Verdict | Evidence | Finding |",
            "|---|---|---:|---|",
        ]
    )
    for claim in audit["claim_assessment"]:
        lines.append(
            f"| {claim['claim']} | `{claim['verdict']}` | {claim['evidence_level']} | {claim['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Strongest supported wording",
            "",
            audit["strongest_supported_wording"],
            "",
            "## Closer-pass target",
            "",
            audit["closer_pass_target"],
            "",
            "L22 is next for the first pass; the fresh depth-by-boundary selection factorial remains deferred until L24 is complete.",
            "",
        ]
    )
    return "\n".join(lines)
