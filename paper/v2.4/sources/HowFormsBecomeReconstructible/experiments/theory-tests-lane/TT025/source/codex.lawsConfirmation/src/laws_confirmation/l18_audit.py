"""Outcome-known retained audit for L18's bounded takeover claim."""

from __future__ import annotations

from collections import Counter
import csv
import io
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .l16_audit import audit_e56, audit_e57, audit_e66
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E56_scaffold": "fe2a28f7c0dae8e904d3e05f0b799a1ad4c96b7a7accff5c8d8af7534487a22b",
    "E57_assimilation": "a1aeadeb82501d395b22596dd6ea543f6c17564ea16963c17fe2255af30f40c2",
    "E66_writable_landlord": "9def6662a2533a853811cbbcac8f0a069e35f6d1f9ef57da2f04ff193d63d982",
}

TRACKED_PACKAGES = (
    "scaffold",
    "assimilation",
    "writable_landlord",
    "blueprint_web",
    "voltage_web",
    "setpoint_rewrite",
    "ladder_web",
    "contract_bridge",
)
ANNEAL_SWEEPS = (250, 500, 1000, 2000)
KNIFE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
REGIMES = ("static", "switching_k2", "switching_k4", "drift")
FREEDOM_BAND = (0.1, 0.3)


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


def _load_shards(
    root: Path,
    tracker: InputTracker,
    *,
    prefix: str,
    expected_shards: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = [
        root / "results/full/work" / f"{prefix}_{index:02d}_of_{expected_shards:02d}.json"
        for index in range(expected_shards)
    ]
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"shard config digests differ for {prefix}: {digests}")
    return [entry for payload in payloads for entry in payload["entries"]], {
        "n_shards": len(paths),
        "config_digest": next(iter(digests)),
        "n_entries": sum(len(payload["entries"]) for payload in payloads),
        "shard_ids_inferred_from_filenames": list(range(expected_shards)),
        "shard_ids_stored_in_payloads": False,
    }


def _bootstrap_mean_interval(
    values: Sequence[float], *, seed: int, draws: int = 4096
) -> list[float]:
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("cannot bootstrap an empty contrast")
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, data.size, size=(draws, data.size))
    return [float(x) for x in np.quantile(data[picks].mean(axis=1), (0.025, 0.975))]


def _directions(values: Sequence[float], *, tolerance: float = 1e-12) -> dict[str, int]:
    return {
        "positive": sum(float(value) > tolerance for value in values),
        "tied": sum(abs(float(value)) <= tolerance for value in values),
        "negative": sum(float(value) < -tolerance for value in values),
    }


def _contrast(values: Sequence[float], *, seed: int, unit: str) -> dict[str, Any]:
    data = [float(value) for value in values]
    return {
        f"n_{unit}s": len(data),
        "mean_difference": float(np.mean(data)),
        f"{unit}_bootstrap_95": _bootstrap_mean_interval(data, seed=seed),
        "bootstrap_draws": 4096,
        "bootstrap_seed": seed,
        "directions": _directions(data),
        f"{unit}_differences": data,
    }


def _first_commit(repo_root: Path, path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
        rows = subprocess.run(
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
    return rows[-1] if rows else None


def _git_provenance(
    plastic_root: Path, package_results: Mapping[str, str]
) -> dict[str, Any]:
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
    packages: dict[str, Any] = {}
    for package, result_name in package_results.items():
        root = _experiment_root(plastic_root, package)
        expectation_commit = _first_commit(repository_root, root / "EXPECTATIONS.md")
        result_commit = _first_commit(repository_root, root / "results/full" / result_name)
        packages[package] = {
            "expectations_first_commit": expectation_commit,
            "selected_result_first_commit": result_commit,
            "same_first_commit_snapshot": (
                expectation_commit is not None and expectation_commit == result_commit
            ),
            "prose_date_is_git_verified_temporal_seal": False,
        }
    return {"repository_root": str(repository_root), "packages": packages}


def source_config_digests() -> dict[str, str]:
    """Digest independently transcribed current E56, E57, and E66 defaults."""

    configs: dict[str, dict[str, Any]] = {
        "E56_scaffold": {
            "mode": "full",
            "n_tissues": 2,
            "futures": 6,
            "pattern_domains": 4,
            "scaffold_era": 1000,
            "retention_horizon": 2500,
            "retention_stride": 50,
            "amp_threshold": 0.2,
            "calibration_settle": 300,
            "calibration_bar": 0.9,
            "zap_at": 1000,
            "zap_sweeps": 8,
            "zap_recover": 300,
            "knife_horizon": 1000,
            "trajectory_seed_tag": "scaffold-v1",
        },
        "E57_assimilation": {
            "mode": "full",
            "population": 10,
            "generations": 16,
            "n_repeats": 6,
            "futures": 2,
            "tournament": 3,
            "rho_init": [0.002, 0.05],
            "rho_range": [0.002, 0.05],
            "cm_init": [0.1, 0.8],
            "cm_range": [0.05, 1.6],
            "mutation_sigma": 0.3,
            "theta_mutation": 0.05,
            "theta_norm": 0.3,
            "eval_settle": 100,
            "eval_instruct": 200,
            "eval_free": 200,
            "eval_regrow": 250,
            "eval_cycles": 2,
            "imprint_hold": 1.2,
            "amp_threshold": 0.2,
            "n_targets": 3,
            "target_settle": 400,
            "assay_evals": 2,
            "consensus_launches": 4,
            "readopt_horizon": 1000,
            "transport_shift": 8,
            "transport_recover": 300,
            "trajectory_seed_tag": "assimilation-v1",
        },
        "E66_writable_landlord": {
            "mode": "full",
            "n_tissues": 4,
            "futures": 6,
            "settle_sweeps": 120,
            "imprint_sweeps": 1000,
            "imprint_hold": 1.2,
            "cycles": 12,
            "inter_fission": 1000,
            "amp_threshold": 0.2,
            "capacity_settle": 300,
            "capacity_bar": 0.8,
            "pullback_zap_sweeps": 8,
            "pullback_window": 50,
            "consensus_launches": 4,
            "consensus_settle": 300,
            "repertoire_seeds": 8,
            "repertoire_distinct": 0.8,
            "zap_recover": 300,
            "imprint_gate_cycles": 8,
            "imprint_gate_bar": 0.75,
            "trajectory_seed_tag": "writable-landlord-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def _linear_zero(left_x: float, left_y: float, right_x: float, right_y: float) -> float:
    if left_y == right_y:
        raise ValueError("cannot interpolate a zero across equal effects")
    return float(left_x - left_y * (right_x - left_x) / (right_y - left_y))


def _audit_e56(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    base = audit_e56(root, tracker)
    entries, shard_integrity = _load_shards(
        root, tracker, prefix="scaffold_shard", expected_shards=3
    )
    runs = [row for row in entries if row["kind"] == "run"]
    knives = [row for row in entries if row["kind"] == "knife"]
    summary = tracker.json(root / "results/full/scaffold_summary.json")

    knife_rows: list[dict[str, Any]] = []
    for block in sorted(knives, key=lambda row: int(row["tissue"])):
        for row in sorted(block["rows"], key=lambda item: float(item["fraction"])):
            unknifed = float(row["unknifed"])
            theta = float(row["theta_lethality"])
            cm = float(row["cm_lethality"])
            knife_rows.append(
                {
                    "tissue": int(block["tissue"]),
                    "fraction": float(row["fraction"]),
                    "unknifed": unknifed,
                    "theta_lethality": theta,
                    "cm_lethality": cm,
                    "theta_minus_cm": theta - cm,
                    "theta_lethality_over_unknifed": theta / unknifed,
                    "cm_lethality_over_unknifed": cm / unknifed,
                }
            )

    curves: dict[str, dict[str, float]] = {}
    for fraction in KNIFE_FRACTIONS:
        rows = [row for row in knife_rows if row["fraction"] == fraction]
        curves[str(fraction)] = {
            "unknifed": float(np.mean([row["unknifed"] for row in rows])),
            "theta_lethality": float(
                np.mean([row["theta_lethality"] for row in rows])
            ),
            "cm_lethality": float(np.mean([row["cm_lethality"] for row in rows])),
            "theta_minus_cm": float(np.mean([row["theta_minus_cm"] for row in rows])),
        }
    differences = [curves[str(fraction)]["theta_minus_cm"] for fraction in KNIFE_FRACTIONS]
    crossing_bracket: list[float] | None = None
    source_midpoint: float | None = None
    for index in range(len(KNIFE_FRACTIONS) - 1):
        if differences[index] >= 0 > differences[index + 1]:
            crossing_bracket = [KNIFE_FRACTIONS[index], KNIFE_FRACTIONS[index + 1]]
            source_midpoint = float(sum(crossing_bracket) / 2)
            break
    if crossing_bracket is None or source_midpoint is None:
        raise ValueError("E56 retained mean knife curves do not cross")

    left, right = crossing_bracket
    aggregate_linear_root = _linear_zero(
        left,
        curves[str(left)]["theta_minus_cm"],
        right,
        curves[str(right)]["theta_minus_cm"],
    )
    tissue_roots = []
    left_directions = []
    right_directions = []
    for tissue in sorted({int(row["tissue"]) for row in knife_rows}):
        left_row = next(
            row for row in knife_rows if row["tissue"] == tissue and row["fraction"] == left
        )
        right_row = next(
            row for row in knife_rows if row["tissue"] == tissue and row["fraction"] == right
        )
        left_directions.append(float(left_row["theta_minus_cm"]))
        right_directions.append(float(right_row["theta_minus_cm"]))
        tissue_roots.append(
            {
                "tissue": tissue,
                "linear_root": _linear_zero(
                    left,
                    float(left_row["theta_minus_cm"]),
                    right,
                    float(right_row["theta_minus_cm"]),
                ),
            }
        )

    schedule_rows: list[dict[str, Any]] = []
    for row in sorted(
        runs,
        key=lambda item: (
            int(item["tissue"]),
            int(item["t_anneal"]),
            str(item["schedule"]),
            bool(item["lesioned"]),
        ),
    ):
        duration = int(row["t_anneal"])
        gradual_exposure = 1000.0 + (duration - 1.0) / 2.0
        instant_exposure = 1000.0 + duration
        schedule_rows.append(
            {
                "tissue": int(row["tissue"]),
                "schedule": str(row["schedule"]),
                "t_anneal": duration,
                "lesioned": bool(row["lesioned"]),
                "retention_at_scaffold_gone": float(row["retention_at_scaffold_gone"]),
                "half_life": row["half_life"],
                "pre_release_duration": 1000 + duration,
                "strong_scaffold_coefficient_sweeps": (
                    gradual_exposure if row["schedule"] == "gradual" else instant_exposure
                ),
            }
        )

    schedule_comparisons: dict[str, Any] = {}
    for offset, duration in enumerate(ANNEAL_SWEEPS):
        gradual = {
            int(row["tissue"]): row
            for row in runs
            if row["schedule"] == "gradual"
            and int(row["t_anneal"]) == duration
            and not row["lesioned"]
        }
        instant = {
            int(row["tissue"]): row
            for row in runs
            if row["schedule"] == "instant"
            and int(row["t_anneal"]) == duration
            and not row["lesioned"]
        }
        if set(gradual) != {0, 1} or set(instant) != {0, 1}:
            raise ValueError(f"incomplete E56 schedule rows at T={duration}")
        half_life_differences = [
            float(instant[tissue]["half_life"] - gradual[tissue]["half_life"])
            for tissue in (0, 1)
        ]
        retention_differences = [
            float(
                instant[tissue]["retention_at_scaffold_gone"]
                - gradual[tissue]["retention_at_scaffold_gone"]
            )
            for tissue in (0, 1)
        ]
        gradual_exposure = 1000.0 + (duration - 1.0) / 2.0
        instant_exposure = 1000.0 + duration
        schedule_comparisons[str(duration)] = {
            "gradual_mean_half_life": float(
                np.mean([float(gradual[tissue]["half_life"]) for tissue in (0, 1)])
            ),
            "instant_mean_half_life": float(
                np.mean([float(instant[tissue]["half_life"]) for tissue in (0, 1)])
            ),
            "instant_minus_gradual_half_life": _contrast(
                half_life_differences,
                seed=20260903182 + offset,
                unit="tissue",
            ),
            "instant_minus_gradual_retention_at_removal": {
                "mean_difference": float(np.mean(retention_differences)),
                "directions": _directions(retention_differences),
                "tissue_differences": retention_differences,
            },
            "equal_pre_release_duration_sweeps": 1000 + duration,
            "gradual_strong_scaffold_coefficient_sweeps": gradual_exposure,
            "instant_strong_scaffold_coefficient_sweeps": instant_exposure,
            "instant_minus_gradual_strong_exposure": instant_exposure
            - gradual_exposure,
            "instant_over_gradual_strong_exposure": instant_exposure
            / gradual_exposure,
        }

    primary = schedule_comparisons["1000"]
    return {
        "integrity": {
            **shard_integrity,
            "kind_counts": dict(Counter(str(row["kind"]) for row in entries)),
            "base_integrity": base["integrity"],
            "summary_digest_matches_shards": summary["config_digest"]
            == shard_integrity["config_digest"],
        },
        "source_summary_recalculation": base,
        "all_reported_gates_and_summaries_match": base[
            "all_reported_gates_and_summaries_match"
        ],
        "knife_crossover": {
            "mean_curves": curves,
            "crossing_bracket": crossing_bracket,
            "source_reported_midpoint": source_midpoint,
            "retained_summary_crossing_fraction": summary["gates"]["crossing_fraction"],
            "midpoint_matches_retained_summary": close(
                source_midpoint, summary["gates"]["crossing_fraction"]
            ),
            "source_value_is_tested_fraction": source_midpoint in KNIFE_FRACTIONS,
            "source_value_is_bracket_midpoint": True,
            "aggregate_linear_interpolation_root": aggregate_linear_root,
            "tissue_linear_roots": tissue_roots,
            "mean_tissue_linear_root": float(
                np.mean([row["linear_root"] for row in tissue_roots])
            ),
            "tissue_root_bootstrap_95": _bootstrap_mean_interval(
                [row["linear_root"] for row in tissue_roots], seed=20260903181
            ),
            "bootstrap_draws": 4096,
            "bootstrap_seed": 20260903181,
            "bracket_left_directions": _directions(left_directions),
            "bracket_right_directions": _directions(right_directions),
            "theta_curve_strictly_falls_at_every_grid_step": all(
                curves[str(a)]["theta_lethality"] > curves[str(b)]["theta_lethality"]
                for a, b in zip(KNIFE_FRACTIONS[:-1], KNIFE_FRACTIONS[1:])
            ),
            "cm_curve_strictly_rises_at_every_grid_step": all(
                curves[str(a)]["cm_lethality"] < curves[str(b)]["cm_lethality"]
                for a, b in zip(KNIFE_FRACTIONS[:-1], KNIFE_FRACTIONS[1:])
            ),
            "unknifed_change_fraction_1_minus_0": curves["1.0"]["unknifed"]
            - curves["0.0"]["unknifed"],
        },
        "intervention_audit": {
            "fractions_are_separately_prepared_trajectories": True,
            "fractions_are_longitudinal_measurements_of_one_trajectory": False,
            "theta_knife": "spatial permutation of the current theta field",
            "cm_knife": "sets R-to-V feedback gain to zero while R remains and updates",
            "arms_copy_same_fraction_specific_starting_V_ema_R": True,
            "knife_arms_use_common_random_numbers": False,
            "literal_carrier_content_is_read_or_transplanted": False,
            "crossover_identifies_changing_functional_dependence": True,
            "crossover_identifies_literal_information_motion": False,
            "e56_contains_fission_or_lineage_inheritance": False,
        },
        "schedule": {
            "comparisons": schedule_comparisons,
            "primary_T1000_instant_mean_half_life": primary[
                "instant_mean_half_life"
            ],
            "primary_T1000_gradual_mean_half_life": primary[
                "gradual_mean_half_life"
            ],
            "source_label_exposure_equalized_is_literal_dose_match": False,
            "arms_match_pre_release_duration": True,
            "instant_is_upper_bound_on_strong_scaffold_exposure": True,
            "schedule_arms_use_common_random_numbers": False,
            "half_life_threshold_is_run_specific_from_first_50_sweep_sample": True,
            "R_active_during_scaffold_in_both_schedules": True,
            "instant_removes_gradual_annealing_transition": True,
            "instant_removes_scaffold_R_coexistence": False,
            "supports_gradual_anneal_is_necessary": False,
            "supports_total_exposure_is_all": False,
        },
        "clock_boundary": {
            "rho": 0.002,
            "one_over_rho": 500.0,
            "primary_tissue_half_lives": [550.0, 600.0],
            "mean_half_life": 575.0,
            "mean_over_one_over_rho": 1.15,
            "rho_values_tested": 1,
            "retention_stride_sweeps": 50,
            "rho_scaling_identified": False,
            "exact_clock_law_identified": False,
        },
    }, knife_rows, schedule_rows


def _rows_by_regime(entries: Sequence[dict[str, Any]], regime: str) -> list[dict[str, Any]]:
    return sorted(
        (row for row in entries if row["regime"] == regime),
        key=lambda row: int(row["repeat"]),
    )


def _audit_e57(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base, _ = audit_e57(root, tracker)
    entries, shard_integrity = _load_shards(
        root, tracker, prefix="assim_shard", expected_shards=6
    )
    summary = tracker.json(root / "results/full/assimilation_summary.json")
    source = _read(tracker, root / "src/assimilation/pipeline.py")
    expectations = _read(tracker, root / "EXPECTATIONS.md")

    repeat_rows: list[dict[str, Any]] = []
    for row in sorted(
        entries, key=lambda item: (REGIMES.index(str(item["regime"])), int(item["repeat"]))
    ):
        initial_cm = float(row["trajectory"][0]["median_cm"])
        final_cm = float(row["median_cm"])
        theta_lethality = float(row["knife"]["none"] - row["knife"]["theta_scramble"])
        cm_lethality = float(row["knife"]["none"] - row["knife"]["cm_zero"])
        target0_gain = float(row["theta_target_corr"][0] - row["native_target_corr"][0])
        max_gain = float(max(row["theta_target_corr"]) - max(row["native_target_corr"]))
        repeat_rows.append(
            {
                "regime": str(row["regime"]),
                "repeat": int(row["repeat"]),
                "initial_median_rho": float(row["trajectory"][0]["median_rho"]),
                "final_median_rho": float(row["median_rho"]),
                "initial_median_cm": initial_cm,
                "final_median_cm": final_cm,
                "cm_change": final_cm - initial_cm,
                "cm_final_over_initial": final_cm / initial_cm,
                "final_cm_in_freedom_band": FREEDOM_BAND[0]
                <= final_cm
                <= FREEDOM_BAND[1],
                "champion_rho": float(row["champion"]["rho"]),
                "champion_cm": float(row["champion"]["cm"]),
                "readoption": float(row["readoption"]),
                "knife_none": float(row["knife"]["none"]),
                "theta_knife_lethality": theta_lethality,
                "cm_knife_lethality": cm_lethality,
                "cm_minus_theta_lethality": cm_lethality - theta_lethality,
                "target0_theta_corr_gain_over_native": target0_gain,
                "max_theta_corr_gain_over_native": max_gain,
            }
        )

    def selected(regime: str) -> list[dict[str, Any]]:
        return [row for row in repeat_rows if row["regime"] == regime]

    regime_summary: dict[str, Any] = {}
    for regime in REGIMES:
        rows = selected(regime)
        changes = [float(row["cm_change"]) for row in rows]
        regime_summary[regime] = {
            "median_initial_cm": float(np.median([row["initial_median_cm"] for row in rows])),
            "median_final_cm": float(np.median([row["final_median_cm"] for row in rows])),
            "median_final_over_median_initial": float(
                np.median([row["final_median_cm"] for row in rows])
                / np.median([row["initial_median_cm"] for row in rows])
            ),
            "mean_within_repeat_cm_change": float(np.mean(changes)),
            "median_within_repeat_cm_change": float(np.median(changes)),
            "cm_change_directions": _directions(changes),
            "freedom_band_fraction": float(
                np.mean([row["final_cm_in_freedom_band"] for row in rows])
            ),
            "median_final_rho": float(np.median([row["final_median_rho"] for row in rows])),
            "mean_readoption": float(np.mean([row["readoption"] for row in rows])),
            "mean_theta_knife_lethality": float(
                np.mean([row["theta_knife_lethality"] for row in rows])
            ),
            "mean_cm_knife_lethality": float(
                np.mean([row["cm_knife_lethality"] for row in rows])
            ),
            "mean_cm_minus_theta_lethality": float(
                np.mean([row["cm_minus_theta_lethality"] for row in rows])
            ),
            "mean_target0_theta_corr_gain_over_native": float(
                np.mean([row["target0_theta_corr_gain_over_native"] for row in rows])
            ),
            "mean_max_theta_corr_gain_over_native": float(
                np.mean([row["max_theta_corr_gain_over_native"] for row in rows])
            ),
        }

    static_corr_values = [
        float(row["target0_theta_corr_gain_over_native"]) for row in selected("static")
    ]

    def indexed_differences(
        left_regime: str, right_regime: str, field: str
    ) -> list[float]:
        left = {int(row["repeat"]): float(row[field]) for row in selected(left_regime)}
        right = {int(row["repeat"]): float(row[field]) for row in selected(right_regime)}
        if set(left) != set(right) or set(left) != set(range(6)):
            raise ValueError(f"repeat mismatch for {left_regime} and {right_regime}")
        return [left[index] - right[index] for index in sorted(left)]

    enforcement = {
        "reported_static_over_k2_median_ratio": regime_summary["static"][
            "median_final_cm"
        ]
        / regime_summary["switching_k2"]["median_final_cm"],
        "reported_k4_over_k2_median_ratio": regime_summary["switching_k4"][
            "median_final_cm"
        ]
        / regime_summary["switching_k2"]["median_final_cm"],
        "static_minus_k2_final_cm": _contrast(
            indexed_differences("static", "switching_k2", "final_median_cm"),
            seed=20260903187,
            unit="repeat",
        ),
        "k4_minus_k2_final_cm": _contrast(
            indexed_differences("switching_k4", "switching_k2", "final_median_cm"),
            seed=20260903188,
            unit="repeat",
        ),
        "static_minus_k2_cm_change": _contrast(
            indexed_differences("static", "switching_k2", "cm_change"),
            seed=20260903189,
            unit="repeat",
        ),
        "k4_minus_k2_cm_change": _contrast(
            indexed_differences("switching_k4", "switching_k2", "cm_change"),
            seed=20260903190,
            unit="repeat",
        ),
        "regime_streams_are_common_random_numbers": False,
        "repeat_index_matches_tissue_configuration": True,
        "switch_periods_tested": [2, 4],
        "rigidity_tracking_time_measured": False,
        "continuous_switch_period_threshold_identified": False,
        "sixteen_generations_establish_equilibrium": False,
        "k2_was_predeclared_arm": "switching_k2 / switching_k4 / drift" in expectations,
        "registered_source_switching_summary_uses_k4": 'switching = "switching_k4"' in source,
        "k2_is_outcome_known_secondary_contrast": True,
        "k2_final_median_is_below_its_initial_median": regime_summary["switching_k2"][
            "median_final_cm"
        ]
        < regime_summary["switching_k2"]["median_initial_cm"],
        "k2_mean_change_is_negative": regime_summary["switching_k2"][
            "mean_within_repeat_cm_change"
        ]
        < 0,
        "k2_negative_change_is_majority_direction": regime_summary["switching_k2"][
            "cm_change_directions"
        ]["negative"]
        > regime_summary["switching_k2"]["cm_change_directions"]["positive"],
    }

    max_selected_rho = max(
        regime_summary[regime]["median_final_rho"]
        for regime in ("static", "switching_k2", "switching_k4")
    )
    substituted_k2_gate = {
        "static_to_k2_ratio_at_least_1_5": enforcement[
            "reported_static_over_k2_median_ratio"
        ]
        >= 1.5,
        "k2_in_band_at_least_half": regime_summary["switching_k2"][
            "freedom_band_fraction"
        ]
        >= 0.5,
        "k2_in_band_exceeds_drift_by_0_25": regime_summary["switching_k2"][
            "freedom_band_fraction"
        ]
        >= regime_summary["drift"]["freedom_band_fraction"] + 0.25,
        "max_selected_regime_median_rho_at_most_0_02": max_selected_rho <= 0.02,
    }
    substituted_k2_gate["all_components_pass"] = all(substituted_k2_gate.values())
    enforcement["substituted_k2_gate"] = substituted_k2_gate

    readoption = {
        "regime_means": {
            regime: regime_summary[regime]["mean_readoption"] for regime in REGIMES
        },
        "reported_value": summary["gates"]["readoption_switching"],
        "reported_source_regime": "switching_k4",
        "reported_value_matches_k4": close(
            summary["gates"]["readoption_switching"],
            regime_summary["switching_k4"]["mean_readoption"],
        ),
        "reported_value_matches_k2": close(
            summary["gates"]["readoption_switching"],
            regime_summary["switching_k2"]["mean_readoption"],
        ),
        "static_mean_equals_k4_mean": close(
            regime_summary["static"]["mean_readoption"],
            regime_summary["switching_k4"]["mean_readoption"],
        ),
        "all_k2_repeats_above_0_5": all(
            float(row["readoption"]) > 0.5 for row in selected("switching_k2")
        ),
        "k2_minus_static": _contrast(
            indexed_differences("switching_k2", "static", "readoption"),
            seed=20260903191,
            unit="repeat",
        ),
        "k2_minus_k4": _contrast(
            indexed_differences("switching_k2", "switching_k4", "readoption"),
            seed=20260903192,
            unit="repeat",
        ),
        "k2_minus_drift": _contrast(
            indexed_differences("switching_k2", "drift", "readoption"),
            seed=20260903193,
            unit="repeat",
        ),
        "forced_instruction_sweeps": 200,
        "free_sweeps_before_only_measurement": 1000,
        "whole_sheet_scoring": True,
        "fission_in_probe": False,
        "time_to_readoption_measured": False,
        "pre_evolution_or_ancestor_control": False,
        "calibrated_half_null": False,
        "selection_specific_preservation_identified": False,
    }

    assimilation = {
        "static_target0_corr_gain": _contrast(
            static_corr_values, seed=20260903186, unit="repeat"
        ),
        "reported_static_mean": summary["gates"]["theta_corr_gain"]["static"],
        "recalculated_mean_matches_reported": close(
            float(np.mean(static_corr_values)),
            summary["gates"]["theta_corr_gain"]["static"],
        ),
        "registered_threshold": 0.2,
        "registered_gate_passed": summary["gates"]["gate_p57_2_assimilation"],
        "implemented_baseline": "projected native theta field",
        "implemented_baseline_is_actual_initial_population_or_ancestor": False,
        "initial_theta_fields_retained": False,
        "finite_search": {
            "population": 10,
            "generations": 16,
            "independent_repeats": 6,
            "theta_cells": 256,
            "theta_fixed_standard_deviation": 0.3,
        },
        "matched_optimizer_positive_control": False,
        "failure_to_install_under_this_search": True,
        "selection_impossibility_identified": False,
    }

    p57_3 = {
        "implemented_switching_regime": "switching_k4",
        "implemented_gate_passed": summary["gates"]["gate_p57_3_plasticity_retained"],
        "implemented_conditions": {
            "k4_cm_lethality_gt_theta_lethality": regime_summary["switching_k4"][
                "mean_cm_knife_lethality"
            ]
            > regime_summary["switching_k4"]["mean_theta_knife_lethality"],
            "k4_readoption_at_least_0_5": regime_summary["switching_k4"][
                "mean_readoption"
            ]
            >= 0.5,
        },
        "static_also_has_cm_lethality_gt_theta_lethality": regime_summary["static"][
            "mean_cm_knife_lethality"
        ]
        > regime_summary["static"]["mean_theta_knife_lethality"],
        "registered_theta_correlation_clause_implemented_in_gate": False,
        "registered_arm_by_knife_interaction_implemented_in_gate": False,
        "knife_assay_arms_use_common_random_numbers": False,
    }

    return {
        "integrity": {
            **shard_integrity,
            "complete_regime_repeat_keys": {
                (str(row["regime"]), int(row["repeat"])) for row in entries
            }
            == {(regime, repeat) for regime in REGIMES for repeat in range(6)},
            "all_trajectories_have_16_generations": all(
                len(row["trajectory"]) == 16 for row in entries
            ),
            "summary_digest_matches_shards": summary["config_digest"]
            == shard_integrity["config_digest"],
            "base_integrity": base["integrity"],
        },
        "source_summary_recalculation": base,
        "all_reported_gates_and_summaries_match": base[
            "all_reported_gates_and_summaries_match"
        ],
        "regime_summary": regime_summary,
        "assimilation": assimilation,
        "enforcement": enforcement,
        "readoption": readoption,
        "P57_3_semantics": p57_3,
    }, repeat_rows


def run_l18_audit(
    plastic_root: Path, workspace: Path
) -> tuple[
    dict[str, Any],
    list[Path],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[Path, str],
]:
    tracker = InputTracker()
    ideas_root = plastic_root / IDEAS_RELATIVE
    narrative = (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas_root / "LAWS.md",
        ideas_root / "WAVE12_PROPHECIES.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        workspace / "SOURCE_BASELINE.md",
        workspace / "REVIEW_PROTOCOL.md",
        workspace / "protocols/L18_TAKEOVER_BOUNDED_AUDIT_V1.md",
        workspace / "laws/L18_takeover_bounded.md",
        workspace / "reviews/L16_LANDLORD_TENANT_AUDIT_2026-09-02.md",
        workspace / "reviews/L17_DEVELOPMENT_HEREDITY_AUDIT_2026-09-03.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    e56, knife_rows, schedule_rows = _audit_e56(
        _experiment_root(plastic_root, "scaffold"), tracker
    )
    e57, e57_rows = _audit_e57(
        _experiment_root(plastic_root, "assimilation"), tracker
    )
    e66 = audit_e66(_experiment_root(plastic_root, "writable_landlord"), tracker)

    source_digests = source_config_digests()
    retained_digests = {
        "E56_scaffold": e56["integrity"]["config_digest"],
        "E57_assimilation": e57["integrity"]["config_digest"],
        "E66_writable_landlord": e66["retained_config_digest"],
    }
    digest_matches = {
        name: source_digests[name]
        == retained_digests[name]
        == EXPECTED_CONFIG_DIGESTS[name]
        for name in EXPECTED_CONFIG_DIGESTS
    }
    provenance = _git_provenance(
        plastic_root,
        {
            "scaffold": "scaffold_summary.json",
            "assimilation": "assimilation_summary.json",
            "writable_landlord": "landlord_summary.json",
        },
    )
    e66_modifier = {
        "retained_audit": e66,
        "aligned_theta_norm": e66["capacity"]["chosen"],
        "aligned_theta_pin": e66["pin_at_chosen"],
        "same_nominal_norm_as_E57": close(e66["capacity"]["chosen"], 0.3),
        "shows_norm_0_3_is_absolute_amplitude_barrier": False,
        "directly_comparable_to_E57_consensus_correlation": False,
        "evidence_level": "E2",
    }

    claims = [
        {
            "claim": "The E56 theta- and c_m-knife raw effects cross at an interior anneal interval",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "Both tissues have theta-minus-c_m lethality above zero at f=.75 and below zero at f=1. "
                "The retained .875 is the midpoint of that grid bracket, not a tested fraction; linear interpolation of the tissue means gives about .882."
            ),
        },
        {
            "claim": "The crossover directly measures a pattern moving between storage media",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "It measures changing dependence on theta spatial structure versus active R feedback across separately prepared states. "
                "R content is neither read nor transplanted, c_m=0 leaves R present, and unknifed retention falls substantially across fractions."
            ),
        },
        {
            "claim": "A gradual anneal is necessary for the tested handoff",
            "verdict": "REFUTED",
            "evidence_level": "E3",
            "reason": (
                "At T=1000 the instant schedule's coded mean half-life is 725 versus 575 for gradual, so a gradual transition is not necessary in this construction. "
                "The schedules use distinct random streams and each half-life has its own first-sample threshold."
            ),
        },
        {
            "claim": "The handoff needs no overlap era; total exposure is all and gradualness is irrelevant",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "R is active alongside the scaffold in both schedules. The instant arm removes the fading transition but has 2000 strong-field coefficient-sweeps at T=1000 versus 1499.5 for gradual. "
                "This upper-bound arm is not dose matched and no exposure factorial establishes sufficiency or exclusivity."
            ),
        },
        {
            "claim": "The receiving ledger holds the pattern exactly about 1/rho",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "The two half-lives are 550 and 600 sweeps (mean 575) at rho=.002, or 1.15 times 1/rho. "
                "Only one rho and a 50-sweep threshold grid were tested, so neither scaling nor exactness is identified."
            ),
        },
        {
            "claim": "Sixteen generations of E57 static selection fail to install the target in theta",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "The retained static mean correlation gain is -0.04356 and the registered gate fails. "
                "The comparator is projected native theta rather than the actual starting genes, so this is a finite operational failure, not literal no writing."
            ),
        },
        {
            "claim": "Selection cannot complete takeover because native fixed norm .3 lacks instance capacity",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2/E3",
            "reason": (
                "E57 has no matched optimizer-positive-control and searches a 256-cell field with population 10 for 16 generations. "
                "Later E66 shows an engineered target-aligned theta at the same norm .3 can pin above .973, so norm alone is not an absolute capacity barrier."
            ),
        },
        {
            "claim": "World switching period affects evolved enforcement in the retained k2/k4 panel",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "Final k4-minus-k2 c_m is positive in all six tissue-index comparisons, while static-minus-k2 is positive in five of six. "
                "The k2 arm was predeclared, but this was promoted after the registered k4 gate failed and does not locate a rigidity threshold or equilibrium."
            ),
        },
        {
            "claim": "Only the k2 world pulls enforcement down threefold toward freedom",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "The 2.96 ratio compares final regime medians. K2's own median rises from its generation-0 value and its six changes split three up/three down; drift is in the freedom band more often. "
                "Two periods and no measured rigidity time do not establish 'only' or a clock threshold."
            ),
        },
        {
            "claim": "Fast-world k2 lineages have re-adoption competence 0.743 preserved by selection",
            "verdict": "REFUTED_AS_QUANTIFIED_AND_NOT_CAUSALLY_IDENTIFIED",
            "evidence_level": "E3",
            "reason": (
                "The .743164 summary is hard-coded from k4 and is numerically identical in static; k2 averages .704102. "
                "All k2 repeats exceed .5, but the whole-sheet endpoint has no fission, ancestor baseline, neutral matched control, or calibrated .5 null, so preservation by fast-world selection is not identified."
            ),
        },
        {
            "claim": "Together E56 and E57 constitute genetic takeover",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "E56 is a continuous within-life scaffold withdrawal without fission, while E57's registered assimilation gate fails. "
                "The Wave-12 closeout itself labels the joint P53.0 headline not fulfilled."
            ),
        },
    ]

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L18",
        "audit_kind": "outcome-known retained recalculation and source-level takeover audit",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "source_config_digests": source_digests,
        "retained_config_digests": retained_digests,
        "expected_config_digests": EXPECTED_CONFIG_DIGESTS,
        "source_config_digest_matches": digest_matches,
        "all_source_config_digests_match": all(digest_matches.values()),
        "git_provenance": provenance,
        "document_checks": {
            "law_contains_f_0_875": "f = 0.875" in texts["LAWS.md"],
            "law_contains_static_k2_values": "static c_m 1.22 vs switching_k2 0.41"
            in texts["LAWS.md"],
            "law_contains_readoption_0_743": "re-adoption competence (0.743)"
            in texts["LAWS.md"],
            "wave_close_says_joint_headline_not_fulfilled": "joint headline as written: NOT FULFILLED"
            in texts["WAVE12_PROPHECIES.md"],
            "manuscript_v2_3_claims_l18": "takeover" in texts["PRE_PRINT_PAPER_DRAFT_V2.3.md"].lower(),
        },
        "E56_scaffold": e56,
        "E57_assimilation": e57,
        "E66_fixed_norm_modifier": e66_modifier,
        "claim_assessment": claims,
        "strongest_supported_wording": (
            "Across two separately prepared E56 tissues, raw theta-scramble dependence exceeds feedback-off dependence at anneal fraction .75 and is lower at 1.0; .875 is the bracket midpoint, while a linear interpolation of the tissue-mean effects is about .882. "
            "An abrupt switch after longer strong-scaffold exposure retains at least as long as a gradual anneal in this construction, and the gradual-arm pattern half-life is 550-600 sweeps at rho=.002. "
            "In E57, 16 generations of static selection do not improve the implemented theta-versus-native correlation, while the retained k2 populations end at lower c_m than k4 in all six tissue-index comparisons. "
            "These are bounded intervention, finite-search, and environment-period results; they do not directly track information moving between carriers, establish an exposure-only or 1/rho law, prove selection incapable of writing theta, or show that k2 selection preserved the reported .743 re-adoption score."
        ),
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        knife_rows,
        schedule_rows,
        e57_rows,
        frozen_hashes,
    )


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return buffer.getvalue()


KNIFE_FIELDS = (
    "tissue",
    "fraction",
    "unknifed",
    "theta_lethality",
    "cm_lethality",
    "theta_minus_cm",
    "theta_lethality_over_unknifed",
    "cm_lethality_over_unknifed",
)
SCHEDULE_FIELDS = (
    "tissue",
    "schedule",
    "t_anneal",
    "lesioned",
    "retention_at_scaffold_gone",
    "half_life",
    "pre_release_duration",
    "strong_scaffold_coefficient_sweeps",
)
E57_FIELDS = (
    "regime",
    "repeat",
    "initial_median_rho",
    "final_median_rho",
    "initial_median_cm",
    "final_median_cm",
    "cm_change",
    "cm_final_over_initial",
    "final_cm_in_freedom_band",
    "champion_rho",
    "champion_cm",
    "readoption",
    "knife_none",
    "theta_knife_lethality",
    "cm_knife_lethality",
    "cm_minus_theta_lethality",
    "target0_theta_corr_gain_over_native",
    "max_theta_corr_gain_over_native",
)


def e56_knife_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, KNIFE_FIELDS)


def e56_schedule_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, SCHEDULE_FIELDS)


def e57_regime_repeats_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, E57_FIELDS)


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def _interval(contrast: Mapping[str, Any], unit: str) -> str:
    low, high = contrast[f"{unit}_bootstrap_95"]
    return f"[{_fmt(low)}, {_fmt(high)}]"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e56 = audit["E56_scaffold"]
    e57 = audit["E57_assimilation"]
    knife = e56["knife_crossover"]
    regimes = e57["regime_summary"]
    enforce = e57["enforcement"]
    readopt = e57["readoption"]
    static_corr = e57["assimilation"]["static_target0_corr_gain"]
    lines = [
        "# L18 retained takeover audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained recalculation and source audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "A narrower and genuinely interesting result survives: the two E56 knife effects reverse order between the last two sampled anneal fractions, and E57's evolved enforcement differs strongly between its k=2 and k=4 environments. The data do not establish the law's literal genetic-takeover, exposure-only, exact-clock, or selection-preserved-plasticity interpretation.",
        "",
        f"E56 sampled f=.75 and f=1.0, not f=.875. The source assigns {_fmt(knife['source_reported_midpoint'], 3)} as the midpoint of that sign-change bracket. A straight-line interpolation of the tissue-mean effects would put the zero at {_fmt(knife['aggregate_linear_interpolation_root'], 6)}, but the experiment does not justify that precision. The knives show changing functional dependence: theta is spatially permuted, while c_m=0 merely prevents a still-present, still-updating R from acting on V.",
        "",
        f"E57's exact numeric miscitation is decisive. The reported re-adoption value {_fmt(readopt['reported_value'], 6)} belongs to switching-k4, not k2, and static has the identical mean. K2 averages {_fmt(readopt['regime_means']['switching_k2'], 6)}. Its six scores all exceed .5, but there is no ancestral baseline or matched neutral control showing that fast-world selection preserved them.",
        "",
        "## E56 knife crossover",
        "",
        "| Anneal fraction | Unknifed | Theta lethality | c_m lethality | Theta - c_m |",
        "|---:|---:|---:|---:|---:|",
    ]
    for fraction in KNIFE_FRACTIONS:
        row = knife["mean_curves"][str(fraction)]
        lines.append(
            f"| {_fmt(fraction, 2)} | {_fmt(row['unknifed'])} | {_fmt(row['theta_lethality'])} | {_fmt(row['cm_lethality'])} | {_fmt(row['theta_minus_cm'])} |"
        )
    lines.extend(
        [
            "",
            f"Both tissues are positive at f=.75 and negative at f=1. Their separately interpolated roots are {', '.join(_fmt(row['linear_root']) for row in knife['tissue_linear_roots'])}; the descriptive tissue bootstrap is [{_fmt(knife['tissue_root_bootstrap_95'][0])}, {_fmt(knife['tissue_root_bootstrap_95'][1])}]. With only two tissues, this is a sensitivity description, not calibrated uncertainty.",
            "",
            f"The theta mean is not strictly decreasing at every grid step: it rises slightly from {_fmt(knife['mean_curves']['0.0']['theta_lethality'])} to {_fmt(knife['mean_curves']['0.25']['theta_lethality'])} before falling. The c_m curve is strictly increasing on this grid. Meanwhile unknifed retention changes by {_fmt(knife['unknifed_change_fraction_1_minus_0'])} from f=0 to f=1, so the raw drops do not have constant headroom.",
            "",
            "Each fraction was prepared afresh from a strong-scaffold run. This is a sequence of separate snapshots, not one organism watched continuously. E56 also has no fission. Calling the result a functional-dependence crossover is warranted; calling it genetic information visibly moving is not.",
            "",
            "## E56 schedule: abrupt versus gradual",
            "",
            "| T | Gradual mean half-life | Instant mean half-life | Instant - gradual | Bootstrap | Strong exposure gradual / instant |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for duration in ANNEAL_SWEEPS:
        row = e56["schedule"]["comparisons"][str(duration)]
        contrast = row["instant_minus_gradual_half_life"]
        lines.append(
            f"| {duration} | {_fmt(row['gradual_mean_half_life'], 1)} | {_fmt(row['instant_mean_half_life'], 1)} | {_fmt(contrast['mean_difference'], 1)} | {_interval(contrast, 'tissue')} | {_fmt(row['gradual_strong_scaffold_coefficient_sweeps'], 1)} / {_fmt(row['instant_strong_scaffold_coefficient_sweeps'], 1)} |"
        )
    lines.extend(
        [
            "",
            "At T=1000 the abrupt arm's coded half-life is 725 sweeps after release versus 575 for gradual. This refutes necessity of a gradual fading transition in the tested construction. The arms have different random streams and each threshold is anchored to its own first 50-sweep sample, so it is not a tightly paired estimate of an advantage. It also does not test the absence of overlap between carriers: R runs beside the scaffold throughout both pre-release eras.",
            "",
            "The label ‘exposure-equalized’ is also too strong. Both schedules have the same pre-release duration, but the gradual strong-field coefficient integrates to `1000 + (T-1)/2`; instant receives `1000 + T`. At T=1000 that is 1499.5 versus 2000. The design deliberately makes instant an upper-exposure bound. It cannot establish that total exposure is all, because exposure was neither matched nor independently varied.",
            "",
            "The gradual-arm half-lives remain 550 and 600 sweeps at rho=.002: mean 575, or 1.15 times 1/rho. That is one nearby point on a 50-sweep grid, not an exact scaling law.",
            "",
            "## E57 finite assimilation result",
            "",
            f"Static target-0 correlation gain is {_fmt(static_corr['mean_difference'])}, with directions {static_corr['directions']['positive']} positive / {static_corr['directions']['tied']} tied / {static_corr['directions']['negative']} negative and descriptive bootstrap {_interval(static_corr, 'repeat')}. The registered +.2 gate fails cleanly.",
            "",
            "But the code compares the evolved champion with projected native theta, not with its initial population or ancestor, and initial theta fields were not retained. Thus ‘final > initial’ was not literally tested. A population of 10 searched a 256-cell fixed-norm field for 16 generations without a matched optimizer-positive-control. The safe result is failure of this search, not that selection cannot write theta.",
            "",
            f"Later E66 supplies a useful boundary: engineered target-aligned theta at the same norm .3 pins at {_fmt(audit['E66_fixed_norm_modifier']['aligned_theta_pin'])}. Its metric and design differ, so it does not demonstrate E57 assimilation; it does rule out norm .3 itself as an absolute instance-capacity barrier.",
            "",
            "## E57 environment period and enforcement",
            "",
            "| Regime | Initial median c_m | Final median c_m | Final / initial | Mean within-repeat change | Changes + / = / - | Freedom-band fraction |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for regime in REGIMES:
        row = regimes[regime]
        directions = row["cm_change_directions"]
        lines.append(
            f"| {regime} | {_fmt(row['median_initial_cm'])} | {_fmt(row['median_final_cm'])} | {_fmt(row['median_final_over_median_initial'], 3)} | {_fmt(row['mean_within_repeat_cm_change'])} | {directions['positive']} / {directions['tied']} / {directions['negative']} | {_fmt(row['freedom_band_fraction'], 3)} |"
        )
    lines.extend(
        [
            "",
            f"The reported static/k2 final-median ratio is {_fmt(enforce['reported_static_over_k2_median_ratio'], 3)}. Static-minus-k2 final c_m is positive in {enforce['static_minus_k2_final_cm']['directions']['positive']}/6 tissue-index contrasts; k4-minus-k2 is positive in {enforce['k4_minus_k2_final_cm']['directions']['positive']}/6. The latter mean difference is {_fmt(enforce['k4_minus_k2_final_cm']['mean_difference'])}, bootstrap {_interval(enforce['k4_minus_k2_final_cm'], 'repeat')}. This is credible descriptive evidence that switching period affected selection outcomes.",
            "",
            f"It is not literally a downward pull within k2. K2's central endpoint rises from {_fmt(regimes['switching_k2']['median_initial_cm'])} to {_fmt(regimes['switching_k2']['median_final_cm'])}; individual changes split 3 up and 3 down. Drift lands in the freedom band in {_fmt(regimes['drift']['freedom_band_fraction'], 3)} of repeats versus {_fmt(regimes['switching_k2']['freedom_band_fraction'], 3)} for k2. Substituting k2 into the registered compound gate still fails its drift-comparison component.",
            "",
            "K2 and k4 were both named before the run, but the implemented primary switching summary and P57.3 gate hard-code k4. The k2 contrast was promoted after that primary failed. It is an informative outcome-known secondary analysis, not evidence that the registered gate passed. Two periods, no independently measured rigidity time, and 16 generations without a stationarity test do not establish ‘only’, a crossover threshold, or equilibrium.",
            "",
            "## Re-adoption and the .743 attribution",
            "",
            "| Regime | Mean re-adoption | Theta lethality | c_m lethality |",
            "|---|---:|---:|---:|",
        ]
    )
    for regime in REGIMES:
        row = regimes[regime]
        lines.append(
            f"| {regime} | {_fmt(row['mean_readoption'])} | {_fmt(row['mean_theta_knife_lethality'])} | {_fmt(row['mean_cm_knife_lethality'])} |"
        )
    lines.extend(
        [
            "",
            f"The published `.743` is switching-k4 ({_fmt(readopt['regime_means']['switching_k4'])}), not the promoted fast k2 arm ({_fmt(readopt['regime_means']['switching_k2'])}). Static is also {_fmt(readopt['regime_means']['static'])}. K2-minus-static averages {_fmt(readopt['k2_minus_static']['mean_difference'])} with three positive and three negative tissue-index differences.",
            "",
            "The assay forcibly instructs target 1 for 200 sweeps and measures one whole-sheet endpoint after 1,000 free sweeps. It has no fission, readoption time course, initial-lineage baseline, or matched no-selection ancestor. All six k2 scores exceed .5, which is a bounded competence observation, but .5 was not calibrated as the relevant null and selection-specific preservation does not follow.",
            "",
            f"The coded P57.3 gate uses k4 and passes because k4 c_m lethality ({_fmt(regimes['switching_k4']['mean_cm_knife_lethality'])}) exceeds theta lethality ({_fmt(regimes['switching_k4']['mean_theta_knife_lethality'])}) while re-adoption exceeds .5. Static has the same ordering. The implementation omits the register's theta-correlation clause and does not calculate the promised arm-by-knife interaction, so this green gate does not uniquely support switching-retained plasticity.",
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
            "After all laws receive a first pass, the clean test should cross scaffold schedule with matched integrated target-aligned dose, independently vary rho, and retain carrier-content readouts or transplant probes. For selection, use common founder panels, a neutral evolution control per environment, more switch periods spanning a measured rigidity time, preregistered contrasts, actual ancestral theta correlations, and a matched optimizer-positive-control. Re-adoption needs a time course and pre-evolution comparator. That work is deferred; L19 is next.",
            "",
        ]
    )
    return "\n".join(lines)
