"""Outcome-known retained/replay audit for L11's greedy-trap claim."""

from __future__ import annotations

import itertools
import math
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E46_james_test_3": "23793e8eeffc223a5ae82725a4e596028a47fa688b9354091376cd3975f4bfda",
    "E52_origin_of_development": "764afdc72db6f897b1a6d0556b6499ca719099d29d42f5d797dcf10466955610",
    "E57_assimilation": "a1aeadeb82501d395b22596dd6ea543f6c17564ea16963c17fe2255af30f40c2",
}

E46_REPLAY_ROWS = 4 * 10
E46_REPLAY_FUTURES = E46_REPLAY_ROWS * 16
E46_ARMS = ("D", "G", "H", "H_lesion")


def _experiment_root(plastic_root: Path, name: str) -> Path:
    return plastic_root / IDEAS_RELATIVE / name


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
        return close(left, right)
    return left == right


def _distribution(values: Iterable[float]) -> dict[str, Any]:
    data = np.asarray([float(value) for value in values], dtype=float)
    if data.size == 0:
        return {
            "n": 0,
            "min": None,
            "q25": None,
            "median": None,
            "mean": None,
            "q75": None,
            "max": None,
        }
    q25, median, q75 = np.quantile(data, (0.25, 0.5, 0.75))
    return {
        "n": int(data.size),
        "min": float(data.min()),
        "q25": float(q25),
        "median": float(median),
        "mean": float(data.mean()),
        "q75": float(q75),
        "max": float(data.max()),
    }


def source_config_digests() -> dict[str, str]:
    """Independently transcribed defaults for E46, E52, and E57."""

    configs: dict[str, dict[str, Any]] = {
        "E46_james_test_3": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 16,
            "settle_sweeps": 40,
            "zap_sweeps_ladder": (4, 8, 16),
            "recovery_horizon": 100,
            "arrival_cos": 0.9,
            "activity_window": 10,
            "cessation_lock": 5,
            "replica_streams": 5,
            "pre_gap": 10,
            "trap_horizon": 200,
            "trap_wall_width": 2,
            "backtrack_margin": 2.0,
            "trajectory_seed_tag": "james3-traj-v2",
            "motility_seed_tag": "james3-motility-v2",
        },
        "E52_origin_of_development": {
            "mode": "full",
            "population": 16,
            "generations": 30,
            "n_repeats": 8,
            "tournament": 3,
            "mutation_sigma": 0.3,
            "rho_range": (0.0005, 0.2),
            "cm_range": (0.05, 1.6),
            "init_rho": (0.002, 0.05),
            "init_cm": (0.1, 0.8),
            "body_sweeps": 30,
            "eval_sweeps": 40,
            "band_cm": (0.1, 0.3),
            "trajectory_seed_tag": "origin-traj-v1",
        },
        "E57_assimilation": {
            "mode": "full",
            "population": 10,
            "generations": 16,
            "n_repeats": 6,
            "futures": 2,
            "tournament": 3,
            "rho_init": (0.002, 0.05),
            "rho_range": (0.002, 0.05),
            "cm_init": (0.1, 0.8),
            "cm_range": (0.05, 1.6),
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
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def _load_shards(
    tracker: InputTracker,
    directory: Path,
    pattern: str,
    expected_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(directory.glob(pattern))
    if len(paths) != expected_count:
        raise ValueError(
            f"expected {expected_count} shards matching {directory / pattern}, "
            f"found {len(paths)}"
        )
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"shard config digests differ: {sorted(digests)}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    return entries, {
        "files": [str(path.resolve()) for path in paths],
        "n_shards": len(paths),
        "config_digest": next(iter(digests)),
        "n_entries": len(entries),
        "source_elapsed_seconds_sum": float(
            sum(float(payload.get("elapsed_seconds", 0.0)) for payload in payloads)
        ),
    }


def _validate_factorial_entries(
    entries: list[dict[str, Any]], regimes: tuple[str, ...], repeats: int
) -> None:
    observed = [(str(row["regime"]), int(row["repeat"])) for row in entries]
    expected = [(regime, repeat) for regime in regimes for repeat in range(repeats)]
    if len(observed) != len(set(observed)):
        raise ValueError("duplicate regime/repeat row in retained shards")
    if sorted(observed) != sorted(expected):
        raise ValueError("retained shard rows do not form the required factorial")


def reconstruct_e52(
    entries: list[dict[str, Any]], retained_gates: Mapping[str, Any]
) -> dict[str, Any]:
    regimes = ("anatomy", "plasticity", "both", "drift")
    _validate_factorial_entries(entries, regimes, 8)

    def rows(regime: str) -> list[dict[str, Any]]:
        return sorted(
            (row for row in entries if row["regime"] == regime),
            key=lambda row: int(row["repeat"]),
        )

    def med(regime: str, key: str) -> float:
        return float(np.median([float(row[key]) for row in rows(regime)]))

    band_lo, band_hi = 0.1, 0.3
    band_fraction = {
        regime: float(
            np.mean(
                [
                    band_lo <= float(row["median_cm"]) <= band_hi
                    for row in rows(regime)
                ]
            )
        )
        for regime in regimes
    }
    medians = {
        regime: {
            "rho": med(regime, "median_rho"),
            "cm": med(regime, "median_cm"),
        }
        for regime in regimes
    }
    calculated_gates = {
        "median_genes": medians,
        "gate_p52_1_anatomy_corner": bool(
            medians["anatomy"]["cm"] > medians["drift"]["cm"]
            and medians["anatomy"]["rho"] < medians["drift"]["rho"]
        ),
        "gate_p52_2_plasticity_corner": bool(
            medians["plasticity"]["cm"] < medians["anatomy"]["cm"]
        ),
        "both_repeats_in_band": band_fraction["both"],
        "drift_repeats_in_band": band_fraction["drift"],
        "gate_p52_3_origin_of_development": bool(
            band_fraction["both"] >= 0.5
            and band_fraction["both"] >= band_fraction["drift"] + 0.25
        ),
    }
    per_regime: dict[str, Any] = {}
    for regime in regimes:
        regime_rows = rows(regime)
        rho_values = [float(row["median_rho"]) for row in regime_rows]
        cm_values = [float(row["median_cm"]) for row in regime_rows]
        per_regime[regime] = {
            "repeat_rows": [
                {
                    "repeat": int(row["repeat"]),
                    "median_rho": float(row["median_rho"]),
                    "median_cm": float(row["median_cm"]),
                    "cm_iqr": [float(value) for value in row["cm_iqr"]],
                }
                for row in regime_rows
            ],
            "rho_distribution_across_repeat_medians": _distribution(rho_values),
            "cm_distribution_across_repeat_medians": _distribution(cm_values),
            "repeat_medians_in_cm_band": int(
                sum(band_lo <= value <= band_hi for value in cm_values)
            ),
            "fraction_repeat_medians_in_cm_band": band_fraction[regime],
            "rho_median_at_lower_bound": int(sum(value == 0.0005 for value in rho_values)),
            "rho_median_at_upper_bound": int(sum(value == 0.2 for value in rho_values)),
            "cm_median_at_lower_bound": int(sum(value == 0.05 for value in cm_values)),
            "cm_median_at_upper_bound": int(sum(value == 1.6 for value in cm_values)),
        }
    both_rho = medians["both"]["rho"]
    return {
        "rows": len(entries),
        "experimental_unit": "evolutionary repeat",
        "per_regime": per_regime,
        "calculated_gates": calculated_gates,
        "retained_gates": dict(retained_gates),
        "reconstructs_retained_gates": _recursive_close(calculated_gates, retained_gates),
        "plasticity_repeat_medians_in_declared_band": per_regime["plasticity"][
            "repeat_medians_in_cm_band"
        ],
        "both_repeat_medians_in_declared_band": per_regime["both"][
            "repeat_medians_in_cm_band"
        ],
        "both_median_rho": both_rho,
        "both_median_fixed_V_memory_scale_one_over_rho": 1.0 / both_rho,
        "fixed_V_residual_after_40_updates_at_both_median_rho": (1.0 - both_rho) ** 40,
    }


def reconstruct_e57(
    entries: list[dict[str, Any]], retained_gates: Mapping[str, Any]
) -> dict[str, Any]:
    regimes = ("static", "switching_k2", "switching_k4", "drift")
    _validate_factorial_entries(entries, regimes, 6)

    def rows(regime: str) -> list[dict[str, Any]]:
        return sorted(
            (row for row in entries if row["regime"] == regime),
            key=lambda row: int(row["repeat"]),
        )

    def med(regime: str, key: str) -> float:
        return float(np.median([float(row[key]) for row in rows(regime)]))

    medians = {
        regime: {
            "rho": med(regime, "median_rho"),
            "cm": med(regime, "median_cm"),
        }
        for regime in regimes
    }
    band_lo, band_hi = 0.1, 0.3
    switching = "switching_k4"
    switching_in_band = float(
        np.mean(
            [
                band_lo <= float(row["median_cm"]) <= band_hi
                for row in rows(switching)
            ]
        )
    )
    drift_in_band = float(
        np.mean(
            [band_lo <= float(row["median_cm"]) <= band_hi for row in rows("drift")]
        )
    )
    static_cm = medians["static"]["cm"]
    switching_cm = medians[switching]["cm"]
    max_selected_regime_median_rho = max(
        medians[regime]["rho"]
        for regime in ("static", "switching_k2", "switching_k4")
    )
    gate = bool(
        (
            static_cm / max(switching_cm, 1e-9) >= 1.5
            or switching_cm / max(static_cm, 1e-9) >= 1.5
        )
        and switching_in_band >= 0.5
        and switching_in_band >= drift_in_band + 0.25
        and max_selected_regime_median_rho <= 0.02
    )
    calculated_p57_1 = {
        "medians": medians,
        "switching_in_band": switching_in_band,
        "drift_in_band": drift_in_band,
        "gate_p57_1_horizon_law": gate,
    }
    retained_p57_1 = {
        key: retained_gates[key]
        for key in (
            "medians",
            "switching_in_band",
            "drift_in_band",
            "gate_p57_1_horizon_law",
        )
    }
    per_regime: dict[str, Any] = {}
    for regime in regimes:
        regime_rows = rows(regime)
        rho_values = [float(row["median_rho"]) for row in regime_rows]
        cm_values = [float(row["median_cm"]) for row in regime_rows]
        per_regime[regime] = {
            "repeat_rows": [
                {
                    "repeat": int(row["repeat"]),
                    "median_rho": float(row["median_rho"]),
                    "median_cm": float(row["median_cm"]),
                }
                for row in regime_rows
            ],
            "rho_distribution_across_repeat_medians": _distribution(rho_values),
            "cm_distribution_across_repeat_medians": _distribution(cm_values),
            "rho_repeat_medians_above_registered_0_02_clause": int(
                sum(value > 0.02 for value in rho_values)
            ),
        }
    return {
        "rows": len(entries),
        "experimental_unit": "evolutionary repeat",
        "per_regime": per_regime,
        "calculated_p57_1": calculated_p57_1,
        "retained_p57_1": retained_p57_1,
        "reconstructs_retained_p57_1": _recursive_close(
            calculated_p57_1, retained_p57_1
        ),
        "max_selected_regime_median_rho": max_selected_regime_median_rho,
        "gate_failed": not gate,
    }


def paired_tissue_diagnostic(
    left: Iterable[float],
    right: Iterable[float],
    *,
    seed: int = 2026090211,
    draws: int = 4096,
) -> dict[str, Any]:
    left_array = np.asarray(list(left), dtype=float)
    right_array = np.asarray(list(right), dtype=float)
    if left_array.shape != right_array.shape or left_array.ndim != 1:
        raise ValueError("paired arms must be one-dimensional with equal length")
    if left_array.size == 0:
        raise ValueError("paired arms cannot be empty")
    differences = left_array - right_array
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, differences.size, size=(draws, differences.size))
    bootstrap = differences[indices].mean(axis=1)
    observed = float(differences.mean())
    sign_flipped = np.asarray(
        [
            float(np.mean(differences * np.asarray(signs, dtype=float)))
            for signs in itertools.product((-1.0, 1.0), repeat=differences.size)
        ],
        dtype=float,
    )
    tolerance = 1e-15
    return {
        "n_tissues": int(differences.size),
        "left_minus_right_mean": observed,
        "left_minus_right_median": float(np.median(differences)),
        "differences": [float(value) for value in differences],
        "directions_positive_tie_negative": {
            "positive": int((differences > tolerance).sum()),
            "tie": int((np.abs(differences) <= tolerance).sum()),
            "negative": int((differences < -tolerance).sum()),
        },
        "paired_tissue_bootstrap_95_percentile": [
            float(np.quantile(bootstrap, 0.025)),
            float(np.quantile(bootstrap, 0.975)),
        ],
        "bootstrap_draws": draws,
        "bootstrap_seed": seed,
        "exhaustive_sign_flip_assignments": int(sign_flipped.size),
        "exhaustive_two_sided_sign_flip_p": float(
            np.mean(np.abs(sign_flipped) >= abs(observed) - tolerance)
        ),
        "outcome_known_descriptive_only": True,
    }


def _trap_run_diagnostic(config: Any, arm: str, index: int) -> dict[str, Any]:
    """Replay E46 trap_run with exact draws and expose endpoint internals."""

    from contract_bridge.artifacts import seed_rng
    from growing_web.config import GrowConfig
    from growing_web.engine import interface_length
    from james_test_3.pipeline import ARMS, step_traced
    from ladder_web.config import LadderConfig
    from ladder_web.engine import tissue_fields
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config
    from voltage_web.engine import launch_pattern, make_thresholds

    _arm_name, rung, motility_on = next(candidate for candidate in ARMS if candidate[0] == arm)
    ladder, grow = LadderConfig(), GrowConfig()
    rewrite = RewriteConfig()
    tissue = tissue_config(index, rewrite.coupling_band, rewrite)
    theta = make_thresholds(tissue)
    fields = tissue_fields(tissue, ladder, "D")
    rng = seed_rng(config.trajectory_seed_tag + "-trap", arm, index)
    mrng = seed_rng(config.motility_seed_tag + "-trap", arm, index)
    V = np.tile(launch_pattern(0, tissue), (config.futures, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema = V.copy()
    for _ in range(config.settle_sweeps):
        V, ema, _ = step_traced(
            V,
            ema,
            theta,
            tissue,
            ladder,
            grow,
            rung,
            rng,
            mrng,
            fields,
            motility_on,
        )

    w = tissue.width
    pre_overwrite_total = V.sum(axis=(-2, -1)).copy()
    V[:, 6:10, w - 2 :] = 1.2
    V[:, :, w - 2 - config.trap_wall_width : w - 2] = -1.2
    post_overwrite_total = V.sum(axis=(-2, -1)).copy()
    home_mass0 = np.clip(V[:, :, : w // 2], 0, None).sum(axis=(-2, -1))
    displaced0 = np.clip(V[:, :, w - 2 :], 0, None).sum(axis=(-2, -1))
    wall0 = np.clip(
        V[:, :, w - 2 - config.trap_wall_width : w - 2], 0, None
    ).sum(axis=(-2, -1))
    iface0 = interface_length(V)
    max_excursion = np.zeros(config.futures)
    swap_events = np.zeros(config.futures, dtype=np.int64)
    for _ in range(config.trap_horizon):
        V, ema, swap_map = step_traced(
            V,
            ema,
            theta,
            tissue,
            ladder,
            grow,
            rung,
            rng,
            mrng,
            fields,
            motility_on,
        )
        swap_events += swap_map.sum(axis=(-2, -1)).astype(np.int64)
        max_excursion = np.maximum(max_excursion, interface_length(V) - iface0)

    displaced_end = np.clip(V[:, :, w - 2 :], 0, None).sum(axis=(-2, -1))
    home_mass_end = np.clip(V[:, :, : w // 2], 0, None).sum(axis=(-2, -1))
    wall_end = np.clip(
        V[:, :, w - 2 - config.trap_wall_width : w - 2], 0, None
    ).sum(axis=(-2, -1))
    escaped = displaced_end < 0.5 * np.maximum(displaced0, 1e-9)
    backtracked = max_excursion > config.backtrack_margin
    return {
        "arm": arm,
        "tissue": index,
        "futures": int(config.futures),
        "motility_on": bool(motility_on and rung != "D"),
        "chemotaxis_on": bool(motility_on and rung == "H"),
        "escaped": [bool(value) for value in escaped],
        "backtracked": [bool(value) for value in backtracked],
        "escape_rate": float(escaped.mean()),
        "backtrack_given_escape": (
            float(backtracked[escaped].mean()) if escaped.any() else None
        ),
        "swap_events": [int(value) for value in swap_events],
        "escaped_without_any_accepted_swap": int((escaped & (swap_events == 0)).sum()),
        "home_mass_increased": [
            bool(value) for value in (home_mass_end > home_mass0)
        ],
        "escaped_without_home_mass_increase": int(
            (escaped & (home_mass_end <= home_mass0)).sum()
        ),
        "pre_overwrite_total_V": [float(value) for value in pre_overwrite_total],
        "post_overwrite_total_V": [float(value) for value in post_overwrite_total],
        "construction_total_V_change": [
            float(value) for value in (post_overwrite_total - pre_overwrite_total)
        ],
        "initial_home_positive_mass": [float(value) for value in home_mass0],
        "final_home_positive_mass": [float(value) for value in home_mass_end],
        "initial_displaced_positive_mass": [float(value) for value in displaced0],
        "final_displaced_positive_mass": [float(value) for value in displaced_end],
        "initial_wall_positive_mass": [float(value) for value in wall0],
        "final_wall_positive_mass": [float(value) for value in wall_end],
        "max_global_interface_excursion": [float(value) for value in max_excursion],
    }


def replay_e46_traps(retained: Mapping[str, Any]) -> dict[str, Any]:
    from james_test_3.config import James3Config

    started = time.monotonic()
    config = James3Config()
    rows = [
        _trap_run_diagnostic(config, arm, tissue)
        for arm in E46_ARMS
        for tissue in range(config.n_tissues)
    ]

    def arm_rows(arm: str) -> list[dict[str, Any]]:
        return sorted(
            (row for row in rows if row["arm"] == arm),
            key=lambda row: int(row["tissue"]),
        )

    arm_summaries: dict[str, Any] = {}
    reconstructed_trap_escape: dict[str, Any] = {}
    for arm in E46_ARMS:
        selected = arm_rows(arm)
        escaped = np.asarray(
            [value for row in selected for value in row["escaped"]], dtype=bool
        )
        backtracked = np.asarray(
            [value for row in selected for value in row["backtracked"]], dtype=bool
        )
        conditional_rows = [
            float(row["backtrack_given_escape"])
            for row in selected
            if row["backtrack_given_escape"] is not None
        ]
        registered_escape = float(np.mean([row["escape_rate"] for row in selected]))
        registered_backtrack = (
            float(np.mean(conditional_rows)) if conditional_rows else None
        )
        reconstructed_trap_escape[arm] = registered_escape
        arm_summaries[arm] = {
            "rows": len(selected),
            "futures": int(escaped.size),
            "escaped_futures": int(escaped.sum()),
            "registered_equal_tissue_escape_rate": registered_escape,
            "pooled_future_escape_rate": float(escaped.mean()),
            "tissue_escape_rates": [float(row["escape_rate"]) for row in selected],
            "registered_mean_tissue_conditional_backtrack_given_escape": registered_backtrack,
            "pooled_backtrack_given_escape": (
                float(backtracked[escaped].mean()) if escaped.any() else None
            ),
            "pooled_global_interface_excursion_rate_all_futures": float(
                backtracked.mean()
            ),
            "escaped_without_any_accepted_swap": int(
                sum(int(row["escaped_without_any_accepted_swap"]) for row in selected)
            ),
            "escaped_without_home_mass_increase": int(
                sum(int(row["escaped_without_home_mass_increase"]) for row in selected)
            ),
            "mean_accepted_swap_events_per_future": float(
                np.mean([value for row in selected for value in row["swap_events"]])
            ),
            "mean_construction_total_V_change": float(
                np.mean(
                    [
                        value
                        for row in selected
                        for value in row["construction_total_V_change"]
                    ]
                )
            ),
            "mean_final_wall_positive_mass": float(
                np.mean(
                    [
                        value
                        for row in selected
                        for value in row["final_wall_positive_mass"]
                    ]
                )
            ),
            "motility_on": bool(selected[0]["motility_on"]),
            "chemotaxis_on": bool(selected[0]["chemotaxis_on"]),
        }

    reconstructed_trap_escape["backtrack_H"] = arm_summaries["H"][
        "registered_mean_tissue_conditional_backtrack_given_escape"
    ]
    retained_trap_escape = dict(retained["gates"]["trap_escape"])
    matches = {
        key: close(reconstructed_trap_escape[key], retained_trap_escape[key])
        for key in retained_trap_escape
    }
    tissue_rates = {
        arm: arm_summaries[arm]["tissue_escape_rates"] for arm in E46_ARMS
    }
    contrast_specs = (
        ("D_minus_H", "D", "H"),
        ("G_minus_H", "G", "H"),
        ("D_minus_G", "D", "G"),
        ("D_minus_H_lesion", "D", "H_lesion"),
    )
    contrasts = {
        name: {
            "left_arm": left,
            "right_arm": right,
            **paired_tissue_diagnostic(tissue_rates[left], tissue_rates[right]),
        }
        for name, left, right in contrast_specs
    }
    return {
        "status": "COMPLETE",
        "elapsed_seconds": time.monotonic() - started,
        "historical_rows_replayed": len(rows),
        "historical_simulator_futures_replayed": sum(
            int(row["futures"]) for row in rows
        ),
        "retained_trap_escape": retained_trap_escape,
        "reconstructed_trap_escape": reconstructed_trap_escape,
        "retained_field_matches": matches,
        "all_retained_trap_fields_reconstruct": all(matches.values()),
        "arms": arm_summaries,
        "paired_tissue_contrasts": contrasts,
        "rows": rows,
    }


def _source_audits(source_texts: Mapping[str, str]) -> dict[str, Any]:
    trap = source_texts["E46"]
    grow = source_texts["GROWING"]
    e52 = source_texts["E52"]
    return {
        "E46_geometry_and_endpoint": {
            "grid": [16, 16],
            "boundary_condition": "periodic/toroidal via numpy.roll",
            "displaced_columns": [14, 15],
            "wall_columns": [12, 13],
            "rightmost_displaced_column_adjacent_to_home_column_zero": True,
            "wall_is_closed_separator": False,
            "wall_is_clamped_after_construction": False,
            "trap_construction_overwrites_voltage_instead_of_moving_labeled_cells": True,
            "construction_is_charge_conserving": False,
            "endpoint": "positive voltage mass in columns 14-15 falls below half its post-overwrite value",
            "endpoint_labels_or_tracks_cells": False,
            "endpoint_requires_wall_crossing": False,
            "endpoint_requires_arrival_in_home_half": False,
            "home_mass0_assignment_count": trap.count("home_mass0 ="),
            "home_mass0_total_token_count": trap.count("home_mass0"),
            "home_mass0_used_after_assignment": trap.count("home_mass0") > 1,
            "D_motility_enabled": False,
            "H_lesion_motility_enabled": False,
            "backtrack_variable": "maximum global interface_length(V)-interface_length(V_at_trap_start)",
            "backtrack_tracks_labeled_cell_path": False,
            "backtrack_margin_bonds": 2.0,
            "periodic_neighbor_operations_present": "np.roll" in grow,
        },
        "E46_mechanism": {
            "D": "identity dynamics only; no motility",
            "G": "identity dynamics plus differential-adhesion Metropolis swaps",
            "H": "G swap energy plus sign(E) chemotaxis",
            "H_lesion": "H-labelled arm with motility phase disabled",
            "D_vs_H_is_chemotaxis_only": False,
            "G_vs_H_is_nearest_chemotaxis_contrast": True,
            "G_H_trajectory_stream_paired": False,
            "G_H_motility_stream_paired": False,
            "arm_name_enters_both_seed_namespaces": (
                '"-trap", arm, index' in trap
            ),
            "matched_chi_zero_knife_with_same_draws_retained": False,
            "wall_crossing_flux_retained": False,
            "local_chemotactic_energy_trace_retained": False,
            "transiently_worse_move_observed": False,
        },
        "E52_endpoint_and_retention": {
            "anatomy_endpoint": "post-fission body sign agreement to live updating inherited R",
            "anatomy_uses_external_fixed_target": False,
            "plasticity_endpoint": "body sign change from pre-zap map among amplitude-defined survivors",
            "plasticity_measures_memory_retention": False,
            "both_is_product_of_anatomy_and_plasticity": "fits.append(a * p)" in e52,
            "last_returned_population_was_evaluated": False,
            "reason_last_population_unevaluated": (
                "each generation evaluates genes, produces next_genes, assigns genes=next_genes, "
                "then the function returns medians after the loop"
            ),
            "retained_fitness_values": False,
            "retained_generation_trajectories": False,
            "retained_full_final_populations": False,
            "retained_rho_iqr": False,
            "direct_useful_memory_assay": False,
            "direct_long_horizon_competence_assay": False,
            "metric_gaming_registered_endpoint": False,
        },
    }


def run_l11_audit(
    plastic_root: Path, *, replay: bool = True
) -> tuple[dict[str, Any], list[Path]]:
    tracker = InputTracker()
    workspace = Path(__file__).resolve().parents[2]
    ideas = plastic_root / IDEAS_RELATIVE
    roots = {
        name: _experiment_root(plastic_root, name)
        for name in (
            "james_test_3",
            "growing_web",
            "ladder_web",
            "voltage_web",
            "setpoint_rewrite",
            "origin_of_development",
            "blueprint_web",
            "assimilation",
            "contract_bridge",
            "glider_test",
            "xeno_bridge",
        )
    }
    for root in roots.values():
        _track_package(tracker, root)

    documents = {
        "LAWS": ideas / "LAWS.md",
        "WAVE10": ideas / "WAVE10_PROPHECIES.md",
        "WAVE11": ideas / "WAVE11_PROPHECIES.md",
        "WAVE12": ideas / "WAVE12_PROPHECIES.md",
        "DISCOVERY": ideas / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        "DISCUSSION": ideas / "RULIAD_DISCUSSION.md",
        "SYNTHESIS": ideas / "RELATED_PAPERS_THEORY_SYNTHESIS.md",
        "MANUSCRIPT": plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        "PROTOCOL": workspace / "protocols/L11_RETAINED_REPLAY_AUDIT_V1.md",
        "LAW_CASE": workspace / "laws/L11_greedy_trap.md",
        "L09_REVIEW": workspace / "reviews/L09_RETAINED_AUDIT_2026-09-02.md",
        "L10_REVIEW": workspace / "reviews/L10_RETAINED_REPLAY_AUDIT_2026-09-02.md",
    }
    texts = {name: _read(tracker, path) for name, path in documents.items()}
    source_texts = {
        "E46": _read(
            tracker, roots["james_test_3"] / "src/james_test_3/pipeline.py"
        ),
        "GROWING": _read(
            tracker, roots["growing_web"] / "src/growing_web/engine.py"
        ),
        "VOLTAGE": _read(
            tracker, roots["voltage_web"] / "src/voltage_web/engine.py"
        ),
        "E52": _read(
            tracker,
            roots["origin_of_development"]
            / "src/origin_of_development/pipeline.py",
        ),
        "BLUEPRINT": _read(
            tracker, roots["blueprint_web"] / "src/blueprint_web/engine.py"
        ),
        "E57": _read(
            tracker, roots["assimilation"] / "src/assimilation/pipeline.py"
        ),
    }

    e46_summary_path = roots["james_test_3"] / "results/full/james3_summary.json"
    e52_summary_path = (
        roots["origin_of_development"] / "results/full/origin_summary.json"
    )
    e57_summary_path = roots["assimilation"] / "results/full/assimilation_summary.json"
    e46_retained = tracker.json(e46_summary_path)
    e52_retained = tracker.json(e52_summary_path)
    e57_retained = tracker.json(e57_summary_path)

    e52_entries, e52_shards = _load_shards(
        tracker,
        roots["origin_of_development"] / "results/full/work",
        "origin_shard_*_of_08.json",
        8,
    )
    e57_entries, e57_shards = _load_shards(
        tracker,
        roots["assimilation"] / "results/full/work",
        "assim_shard_*_of_06.json",
        6,
    )
    e52 = reconstruct_e52(e52_entries, e52_retained["gates"])
    e57 = reconstruct_e57(e57_entries, e57_retained["gates"])

    digests = source_config_digests()
    retained_digests = {
        "E46_james_test_3": e46_retained["config_digest"],
        "E52_origin_of_development": e52_retained["config_digest"],
        "E57_assimilation": e57_retained["config_digest"],
    }
    digest_matches = {
        name: digests[name] == EXPECTED_CONFIG_DIGESTS[name] == retained_digests[name]
        for name in EXPECTED_CONFIG_DIGESTS
    }
    shard_digest_matches = {
        "E52": e52_shards["config_digest"] == e52_retained["config_digest"],
        "E57": e57_shards["config_digest"] == e57_retained["config_digest"],
    }

    replay_result = replay_e46_traps(e46_retained) if replay else {
        "status": "NOT_RUN",
        "historical_rows_replayed": 0,
        "historical_simulator_futures_replayed": 0,
        "all_retained_trap_fields_reconstruct": False,
    }
    replay_matches = bool(
        replay and replay_result["all_retained_trap_fields_reconstruct"]
    )
    source_audits = _source_audits(source_texts)

    horizon_comparison = {
        "classification": "descriptive cross-protocol comparison; not a horizon intervention",
        "only_evaluation_horizon_changes": False,
        "direct_short_vs_long_horizon_factorial": False,
        "E52": {
            "evaluation_horizon_sweeps": 40,
            "genotype": ["rho", "c_m"],
            "rho_range": [0.0005, 0.2],
            "population": 16,
            "evolutionary_generations": 30,
            "futures_per_fitness_call": 4,
            "fitness": "separate anatomy/body-change scores or their product",
            "tissue_and_target_schedule": "new random tissue index each generation; live R target",
            "regimes": ["anatomy", "plasticity", "both", "drift"],
        },
        "E57": {
            "evaluation_horizon_sweeps": 1000,
            "genotype": ["rho", "c_m", "theta field"],
            "rho_range": [0.002, 0.05],
            "population": 10,
            "evolutionary_generations": 16,
            "futures_per_fitness_call": 2,
            "fitness": "adopt frozen instructed target then defend it through two cuts",
            "tissue_and_target_schedule": "one tissue per repeat; static or k-generation target switching",
            "regimes": ["static", "switching_k2", "switching_k4", "drift"],
        },
        "E52_fast_corner_rho_0_174_accessible_in_E57": False,
        "E57_rho_upper_bound": 0.05,
        "E57_registered_horizon_gate_passed": not e57["gate_failed"],
        "narrow_supported_association": (
            "the different 1000-sweep E57 protocol ended with selected regime-level "
            "median rho values at or below 0.016086, versus E52 BOTH's 0.174198"
        ),
        "horizon_causally_identified": False,
    }

    claim_assessment = {
        "reported_H_0_56875_vs_D_0_725_proxy_rates": {
            "status": (
                "CONFIRMED_CURRENT_SOURCE_REPLAY" if replay_matches else "NOT_CONFIRMED"
            ),
            "reason": (
                "The arithmetic reproduces, but the endpoint is positive-voltage loss "
                "from two columns, not verified cell transport."
            ),
        },
        "chemotactic_tissue_escapes_geometric_trap_less_than_passive_tissue": {
            "status": "NOT_CONFIRMED_ENDPOINT_DOES_NOT_MEASURE_CROSSING",
            "reason": (
                "The non-motile D arm scores escape, home arrival is unused, the wall "
                "can evolve, and the toroidal seam bypasses it."
            ),
        },
        "local_gradient_causes_the_difference": {
            "status": "NOT_CONFIRMED",
            "reason": (
                "H-versus-D changes motion and adhesion as well as chemotaxis. G-versus-H "
                "is the nearest comparator but uses independent arm-specific streams and "
                "still measures the invalid proxy endpoint."
            ),
        },
        "gradient_opposes_a_transiently_worse_escape_move": {
            "status": "NOT_MEASURED",
            "reason": (
                "No labeled path, wall-crossing flux, local energy trace, or matched "
                "gradient knife was retained."
            ),
        },
        "effect_generalises_to_local_optimum_escape": {
            "status": "NOT_CONFIRMED",
            "reason": "Only one periodic, dissolving-wall geometry and one proxy endpoint were tested.",
        },
        "E52_is_the_same_greedy_trap_at_an_evolutionary_level": {
            "status": "NOT_CONFIRMED",
            "reason": (
                "E52 has no shared state, barrier, intervention, or outcome with E46, and "
                "its registered origin-of-development gate failed."
            ),
        },
        "E52_BOTH_ends_fast_and_strong_under_its_40_sweep_objective": {
            "status": "CONFIRMED_WITH_NARROWER_WORDING",
            "reason": (
                "Eight retained repeat medians reconstruct the fast/high-gain final "
                "offspring aggregate; the returned offspring were not themselves evaluated."
            ),
        },
        "E52_fast_solution_games_metrics_by_abolishing_useful_memory": {
            "status": "NOT_MEASURED",
            "reason": (
                "No useful-memory endpoint, long-horizon competence assay, retained fitness "
                "trajectory, or matched rho intervention is present."
            ),
        },
        "short_horizon_selection_generally_erodes_developmental_timescale_separation": {
            "status": "NOT_CONFIRMED",
            "reason": (
                "E52 and E57 differ on many design axes, E57 excludes rho=0.17 by range, "
                "and E57's registered horizon-law gate failed."
            ),
        },
        "biological_benchmark_predictions": {
            "status": "NOT_CONFIRMED",
            "reason": "No retained biological experiment tests either benchmark.",
        },
    }

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L11",
        "audit_kind": "outcome-known retained-source audit with focused E46 historical replay",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed": replay_result[
            "historical_simulator_futures_replayed"
        ],
        "source_config_digests": digests,
        "retained_config_digests": retained_digests,
        "source_config_digest_matches": digest_matches,
        "all_source_config_digests_match": all(digest_matches.values()),
        "shard_config_digest_matches": shard_digest_matches,
        "E46_focused_replay": replay_result,
        "E46_source_audit": source_audits["E46_geometry_and_endpoint"],
        "E46_mechanism_audit": source_audits["E46_mechanism"],
        "E52_retained_reconstruction": e52,
        "E52_source_audit": source_audits["E52_endpoint_and_retention"],
        "E52_shard_integrity": e52_shards,
        "E57_retained_reconstruction": e57,
        "E57_shard_integrity": e57_shards,
        "E52_E57_horizon_comparison": horizon_comparison,
        "claim_assessment": claim_assessment,
        "overall_verdict": "MIXED" if replay_matches else "NOT_CONFIRMED",
        "replacement_wording": (
            "In the current E46 implementation, the H arm is less likely than "
            "the non-motile D arm to lose half of the positive voltage amplitude "
            "from the two rightmost columns by sweep 200. That proxy does not "
            "verify material escape: non-motile tissue can satisfy it, the home "
            "measurement is unused, the wall evolves, and periodic boundaries "
            "provide a bypass. E52's 40-sweep product-fitness runs end with fast, "
            "high-gain BOTH offspring, while a substantially different 1000-sweep "
            "E57 protocol ends at lower rho. These bounded results do not identify "
            "a greedy-gradient mechanism, demonstrate local-optimum escape, show "
            "metric gaming by loss of useful memory, or isolate a general selection-"
            "horizon law."
        ),
        "manuscript_v2_3_independent_support": any(
            phrase in texts["MANUSCRIPT"].lower()
            for phrase in ("greedy trap", "delayed gratification", "myopic selection")
        ),
    }
    audit["input_file_count"] = len(tracker.paths)
    return audit, sorted(tracker.paths)


def markdown_report(audit: Mapping[str, Any]) -> str:
    replay = audit["E46_focused_replay"]
    e52 = audit["E52_retained_reconstruction"]
    e57 = audit["E57_retained_reconstruction"]
    lines = [
        "# L11 retained/replay greedy-trap audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`.",
        "",
        "The two headline numerical patterns survive as bounded model outputs, but "
        "the greedy-trap law does not. E46's endpoint can call a non-moving tissue "
        "an escape, and E52 does not measure the same mechanism or isolate selection "
        "horizon.",
        "",
        "## E46 proxy reversal",
        "",
        "| Arm | Machinery | Escaped futures | Proxy rate | Global-interface excursion, all futures |",
        "|---|---|---:|---:|---:|",
    ]
    if replay.get("status") != "NOT_RUN":
        for arm in E46_ARMS:
            row = replay["arms"][arm]
            machinery = (
                "adhesion + chemotaxis"
                if row["chemotaxis_on"]
                else "adhesion motility"
                if row["motility_on"]
                else "no motility"
            )
            lines.append(
                f"| {arm} | {machinery} | {row['escaped_futures']} / {row['futures']} | "
                f"{row['registered_equal_tissue_escape_rate']:.6f} | "
                f"{row['pooled_global_interface_excursion_rate_all_futures']:.6f} |"
            )
        lines.extend(
            [
                "",
                f"All retained trap fields reconstruct: "
                f"`{replay['all_retained_trap_fields_reconstruct']}`.",
                "",
                "| Contrast | Mean difference | 95% paired-tissue bootstrap | Exact sign-flip p |",
                "|---|---:|---:|---:|",
            ]
        )
        for name in ("D_minus_H", "G_minus_H", "D_minus_G", "D_minus_H_lesion"):
            item = replay["paired_tissue_contrasts"][name]
            interval = item["paired_tissue_bootstrap_95_percentile"]
            lines.append(
                f"| {name.replace('_', ' ')} | {item['left_minus_right_mean']:.6f} | "
                f"[{interval[0]:.6f}, {interval[1]:.6f}] | "
                f"{item['exhaustive_two_sided_sign_flip_p']:.6f} |"
            )
    geometry = audit["E46_source_audit"]
    lines.extend(
        [
            "",
            "## Why this is not verified geometric escape",
            "",
            "- `escaped` is loss of positive voltage amplitude from columns 14--15, "
            "not transport of labeled cells or arrival at home.",
            "- D and H-lesion have no motility, yet the endpoint can score them as "
            "escaped.",
            "- `home_mass0` is assigned but never used by the endpoint or gate.",
            "- The wall at columns 12--13 is not clamped and can change.",
            "- The grid is toroidal: column 15 directly neighbors home-side column 0, "
            "so the wall is not a closed separator.",
            "- Backtracking is a global interface-length excursion, not an escaping "
            "cell's path.",
            "",
            f"Source check: home variable used after assignment = "
            f"`{geometry['home_mass0_used_after_assignment']}`; wall closed = "
            f"`{geometry['wall_is_closed_separator']}`.",
            "",
            "## E52 retained evolutionary result",
            "",
            "| Regime | Median rho | Median c_m | Repeat medians in c_m band |",
            "|---|---:|---:|---:|",
        ]
    )
    for regime in ("anatomy", "plasticity", "both", "drift"):
        medians = e52["calculated_gates"]["median_genes"][regime]
        count = e52["per_regime"][regime]["repeat_medians_in_cm_band"]
        lines.append(
            f"| {regime} | {medians['rho']:.6f} | {medians['cm']:.6f} | "
            f"{count} / 8 |"
        )
    lines.extend(
        [
            "",
            f"E52 gates reconstruct: `{e52['reconstructs_retained_gates']}`. "
            f"P52.3 passed: "
            f"`{e52['calculated_gates']['gate_p52_3_origin_of_development']}`. "
            f"Only {e52['plasticity_repeat_medians_in_declared_band']}/8 plasticity "
            "repeat medians lie in the declared band despite the pooled median being "
            "near 0.2.",
            "",
            "E52 retained no fitness trajectory, useful-memory assay, or long-horizon "
            "competence outcome. Its returned final offspring population was produced "
            "after the last evaluated generation and was not itself evaluated.",
            "",
            "## E57 horizon context",
            "",
            "| Regime | Median rho | Median c_m |",
            "|---|---:|---:|",
        ]
    )
    for regime in ("static", "switching_k2", "switching_k4", "drift"):
        medians = e57["calculated_p57_1"]["medians"][regime]
        lines.append(
            f"| {regime} | {medians['rho']:.6f} | {medians['cm']:.6f} |"
        )
    lines.extend(
        [
            "",
            f"E57 P57.1 reconstructs: `{e57['reconstructs_retained_p57_1']}`; "
            f"registered horizon gate passed: "
            f"`{e57['calculated_p57_1']['gate_p57_1_horizon_law']}`.",
            "",
            "E52 versus E57 is not a horizon-only comparison: genotype, objective, "
            "rho range, population, generation count, futures, tissue/target schedule, "
            "and regimes all change. In particular E57 caps rho at 0.05 and cannot "
            "reach E52's approximately 0.17 corner.",
            "",
            "## Claim verdicts",
            "",
            "| Claim | Verdict |",
            "|---|---|",
        ]
    )
    for claim, finding in audit["claim_assessment"].items():
        lines.append(f"| {claim.replace('_', ' ')} | `{finding['status']}` |")
    lines.extend(
        [
            "",
            "## Replacement wording",
            "",
            str(audit["replacement_wording"]),
            "",
            "## Reproducibility",
            "",
            f"- Inputs hashed: {audit['input_file_count']}",
            f"- Final config digests match: {audit['all_source_config_digests_match']}",
            f"- E52/E57 retained rows reconstruct: "
            f"{e52['reconstructs_retained_gates']} / "
            f"{e57['reconstructs_retained_p57_1']}",
            f"- E46 retained trap fields replay: "
            f"{replay.get('all_retained_trap_fields_reconstruct', False)}",
            "- Fresh scientific futures: 0",
            f"- Historical simulator futures replayed: "
            f"{audit['historical_simulator_futures_replayed']}",
            "",
        ]
    )
    return "\n".join(lines)
