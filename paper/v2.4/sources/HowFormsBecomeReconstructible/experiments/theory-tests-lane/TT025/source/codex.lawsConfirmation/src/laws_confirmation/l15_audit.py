"""Outcome-known retained and analytic audit for L15's timescale law."""

from __future__ import annotations

from collections import Counter
import csv
import io
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E48_blueprint_web": "fec508fdcefb9e7cf4c0eff45ec6f35a9ee25ccf2b4b366f8689af54397cf19b",
    "E49_triangle_final": "e5ecf2e981b236b1c2d9e0becc709013cba7da0d866d30298079bab4daffbd84",
    "E50_james_final": "673ad23f3661725b97aebaf33515850811dbc88d70a9c84209d7d118c66b2728",
}

RHO_VALUES = (0.002, 0.01, 0.05)
GAIN_VALUES = (0.2, 0.4, 0.8)
E49_ARMS = ("D", "T", "T_lesion")
E49_DISTANCES = (4, 6, 8)
E49_IMPRINT_GENERATIONS = (2, 4, 8)
DEFAULT_DT = 0.2

TRACKED_PACKAGES = (
    "blueprint_web",
    "triangle_final",
    "james_final",
    "voltage_web",
    "ladder_web",
    "setpoint_rewrite",
    "contract_bridge",
    "growing_web",
    "persuadability",
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


def source_config_digests() -> dict[str, str]:
    """Independently transcribed current defaults for E48--E50."""

    configs: dict[str, dict[str, Any]] = {
        "E48_blueprint_web": {
            "mode": "full",
            "rho": 0.002,
            "c_m": 0.2,
            "seed_side": 4,
            "coarse_weight": 0.5,
            "trajectory_seed_tag": "blueprint-traj-v1",
            "motility_seed_tag": "blueprint-motility-v1",
        },
        "E49_triangle_final": {
            "mode": "full",
            "n_tissues": 12,
            "futures": 16,
            "settle_sweeps": 120,
            "displacement_ladder": (4, 6, 8),
            "strip_width": 3,
            "displacement_magnitude": 0.8,
            "recovery_sweeps": 80,
            "imprint_generations": (2, 4, 8),
            "imprint_hold": 1.2,
            "steer_horizon": 20,
            "steer_bar": 0.75,
            "hold_generations": 4,
            "trajectory_seed_tag": "triangle-traj-v1",
        },
        "E50_james_final": {
            "mode": "full",
            "n_tissues": 10,
            "futures": 16,
            "settle_sweeps": 120,
            "zap_sweeps_ladder": (4, 8, 16),
            "recovery_horizon": 100,
            "arrival_cos_bar": 0.8,
            "cessation_lock": 3,
            "replica_streams": 5,
            "pre_gap": 10,
            "trap_horizon": 200,
            "trap_wall_width": 2,
            "trajectory_seed_tag": "jamesfinal-traj-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def ema_response(rho: float) -> dict[str, Any]:
    """Exact discrete EMA response when the body is held fixed."""

    if not 0.0 < rho < 1.0:
        raise ValueError("rho must lie strictly between zero and one")
    decay = 1.0 - rho
    thresholds = {
        "50_percent": 0.5,
        "one_over_e": math.exp(-1.0),
        "20_percent": 0.2,
        "5_percent": 0.05,
        "1_percent": 0.01,
    }
    times = (100, 200, 500, 800, 1200)
    return {
        "rho": rho,
        "one_over_rho": 1.0 / rho,
        "decay_factor": decay,
        "exact_discrete_e_folding_sweeps": -1.0 / math.log(decay),
        "residual_fraction": {str(t): decay**t for t in times},
        "first_integer_sweep_at_or_below": {
            label: int(math.ceil(math.log(level) / math.log(decay)))
            for label, level in thresholds.items()
        },
        "asymptotically_satisfiable_for_fixed_body": True,
        "finite_noise_floor_result_implied": False,
        "full_coupled_tissue_result_implied": False,
    }


def comparator_ema_substep(
    rho: float, c_m: float, *, dt: float = DEFAULT_DT
) -> dict[str, Any]:
    """Exact isolated linear substep for one centered spatial mode.

    This deliberately excludes the preceding plant update, noise, clipping,
    and the spatial-mean mode. It diagnoses what the comparator plus EMA does;
    it is not a solution of the full tissue model.
    """

    if not 0.0 < rho < 1.0:
        raise ValueError("rho must lie strictly between zero and one")
    if dt <= 0.0 or c_m < 0.0:
        raise ValueError("dt must be positive and c_m nonnegative")
    a = dt * c_m
    if not 0.0 <= a < 1.0:
        raise ValueError("isolated stable-substep calculation requires 0 <= dt*c_m < 1")
    q = (1.0 - rho) * (1.0 - a)
    denominator = a + rho * (1.0 - a)
    limiting_new_fraction = rho * (1.0 - a) / denominator if denominator else 1.0
    matrix = [
        [1.0 - a, a],
        [rho * (1.0 - a), 1.0 - rho * (1.0 - a)],
    ]
    return {
        "rho": rho,
        "c_m": c_m,
        "dt": dt,
        "a_dt_times_c_m": a,
        "matrix_V_R": matrix,
        "eigenvalues": [1.0, q],
        "mismatch_decay_q": q,
        "mismatch_e_folding_sweeps": -1.0 / math.log(q) if 0.0 < q < 1.0 else None,
        "conserved_left_weights_unnormalized": [rho * (1.0 - a), a],
        "limiting_new_body_fraction_after_unit_V_step": limiting_new_fraction,
        "limiting_old_reference_fraction": 1.0 - limiting_new_fraction,
        "scope": "zero-spatial-mean comparator/EMA substep; no plant, noise, clipping, or forcing",
    }


def _parse_cell_key(key: str) -> tuple[float, float]:
    rho, gain = key.split("|")
    return float(rho), float(gain)


def audit_e48(root: Path, tracker: InputTracker) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = tracker.json(root / "results/full/calibration_square.json")
    pipeline = _read(tracker, root / "src/blueprint_web/pipeline.py")
    current_config = source_config_digests()["E48_blueprint_web"]
    rows: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}
    for key, cell in summary["square"].items():
        rho, gain = _parse_cell_key(key)
        screen = bool(
            cell["h_above"] >= 0.30
            and cell["h_below"] >= 0.02
            and cell["survival_8"] >= 0.30
        )
        freedom = bool(cell["conversion"] >= 0.10)
        joint = screen and freedom
        math_row = comparator_ema_substep(rho, gain)
        row = {
            "cell": key,
            "rho": rho,
            "c_m": gain,
            "h_above": float(cell["h_above"]),
            "h_below": float(cell["h_below"]),
            "survival_8": float(cell["survival_8"]),
            "conversion": float(cell["conversion"]),
            "screen_pass_reported": bool(cell["screen_pass"]),
            "screen_pass_recalculated": screen,
            "freedom_pass_reported": bool(cell["freedom_pass"]),
            "freedom_pass_recalculated": freedom,
            "joint_pass_recalculated": joint,
            "screen_survival_margin": float(cell["survival_8"] - 0.30),
            "conversion_margin": float(cell["conversion"] - 0.10),
            "isolated_mismatch_q": math_row["mismatch_decay_q"],
            "isolated_limiting_new_fraction": math_row[
                "limiting_new_body_fraction_after_unit_V_step"
            ],
        }
        rows.append(row)
        checks[key] = {
            "screen_matches": screen == bool(cell["screen_pass"]),
            "freedom_matches": freedom == bool(cell["freedom_pass"]),
        }
    rows.sort(key=lambda row: (row["rho"], row["c_m"]))
    passing = sorted(row["cell"] for row in rows if row["joint_pass_recalculated"])
    source_choice = max(passing, key=lambda key: _parse_cell_key(key)[1])
    conversion_choice = max(
        passing,
        key=lambda key: float(summary["square"][key]["conversion"]),
    )

    by_rho: dict[str, Any] = {}
    for rho in RHO_VALUES:
        selected = {row["c_m"]: row for row in rows if row["rho"] == rho}
        conversions = [selected[gain]["conversion"] for gain in GAIN_VALUES]
        by_rho[str(rho)] = {
            "conversion_by_gain": {
                str(gain): selected[gain]["conversion"] for gain in GAIN_VALUES
            },
            "drop_0_2_to_0_4": conversions[0] - conversions[1],
            "drop_0_4_to_0_8": conversions[1] - conversions[2],
            "drop_0_2_to_0_8": conversions[0] - conversions[2],
            "monotone_nonincreasing": all(
                left >= right for left, right in zip(conversions, conversions[1:])
            ),
            "joint_pass_pattern": [
                selected[gain]["joint_pass_recalculated"] for gain in GAIN_VALUES
            ],
        }
    by_gain: dict[str, Any] = {}
    for gain in GAIN_VALUES:
        selected = [row for row in rows if row["c_m"] == gain]
        conversions = [row["conversion"] for row in selected]
        by_gain[str(gain)] = {
            "conversion_by_rho": {str(row["rho"]): row["conversion"] for row in selected},
            "range_across_rho": max(conversions) - min(conversions),
            "joint_pass_constant_across_rho": len(
                {row["joint_pass_recalculated"] for row in selected}
            ) == 1,
        }
    gain_drops = [by_rho[str(rho)]["drop_0_2_to_0_8"] for rho in RHO_VALUES]
    rho_ranges = [by_gain[str(gain)]["range_across_rho"] for gain in GAIN_VALUES]
    mean_gain_drop = float(np.mean(gain_drops))
    mean_rho_range = float(np.mean(rho_ranges))
    result_files = sorted(path for path in (root / "results/full").rglob("*") if path.is_file())
    return {
        "retained_config_digest": summary["config_digest"],
        "retained_digest_matches_expected": (
            summary["config_digest"] == EXPECTED_CONFIG_DIGESTS["E48_blueprint_web"]
        ),
        "current_source_config_digest": current_config,
        "current_source_digest_matches_retained": current_config == summary["config_digest"],
        "cell_count": len(rows),
        "all_cell_flags_recalculate": all(
            check["screen_matches"] and check["freedom_matches"]
            for check in checks.values()
        ),
        "cell_checks": checks,
        "passing_recalculated": passing,
        "passing_matches_retained": passing == summary["passing"],
        "chosen_reported": summary["chosen"],
        "chosen_by_source_rule": source_choice,
        "chosen_by_highest_conversion": conversion_choice,
        "selection_rule_uses_rho": False,
        "selection_rule_uses_conversion": False,
        "selection_rule_description": (
            "maximum c_m among passing cells; equal-gain ties retain mapping insertion order"
        ),
        "source_selection_rule_detected": (
            'best = max(passing, key=lambda k: float(k.split("|")[1]))' in pipeline
        ),
        "tested_rho_values": list(RHO_VALUES),
        "tested_gain_values": list(GAIN_VALUES),
        "finite_joint_pass_bracket": [0.2, 0.4],
        "axis_contrast": {
            "by_rho": by_rho,
            "by_gain": by_gain,
            "all_gain_sequences_monotone_nonincreasing": all(
                row["monotone_nonincreasing"] for row in by_rho.values()
            ),
            "all_joint_pass_patterns_equal_across_rho": len(
                {tuple(row["joint_pass_pattern"]) for row in by_rho.values()}
            ) == 1,
            "mean_conversion_drop_gain_0_2_to_0_8": mean_gain_drop,
            "mean_conversion_range_across_rho_within_gain": mean_rho_range,
            "descriptive_gain_drop_to_rho_range_ratio": (
                mean_gain_drop / mean_rho_range if mean_rho_range else None
            ),
            "inferential_factor_effect_estimated": False,
        },
        "frontier_claim": {
            "finite_pass_fail_bracket_observed": True,
            "boundary_localized_inside_0_2_to_0_4": False,
            "sharpness_or_discontinuity_estimated": False,
            "independent_square_replications": 0,
            "reproducibility_established": False,
            "uncertainty_recoverable_from_aggregate": False,
        },
        "retention": {
            "result_files": [str(path.relative_to(root)) for path in result_files],
            "calibration_square_machine_readable": True,
            "satisfiability_0_294_vs_0_351_machine_readable": False,
            "satisfiability_sign_0_948_machine_readable": False,
            "regrowth_0_711_vs_0_543_machine_readable": False,
            "whole_R_inheritance_cohort_machine_readable": False,
        },
    }, rows


def _load_e49_shards(root: Path, tracker: InputTracker) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = [
        root / "results/full/work" / f"triangle_shard_{index:02d}_of_04.json"
        for index in range(4)
    ]
    payloads = [tracker.json(path) for path in paths]
    digests = {payload.get("config_digest") for payload in payloads}
    if len(digests) != 1:
        raise ValueError(f"E49 shard digests differ: {digests}")
    entries = [entry for payload in payloads for entry in payload["entries"]]
    return entries, {
        "n_shards": len(paths),
        "inferred_shard_ids": list(range(4)),
        "config_digest": next(iter(digests)),
        "n_entries": len(entries),
    }


def _bootstrap_mean_interval(values: Sequence[float], *, seed: int) -> list[float]:
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("cannot bootstrap an empty contrast")
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(data), size=(4096, len(data)))
    return [float(x) for x in np.quantile(data[picks].mean(axis=1), (0.025, 0.975))]


def _contrast(values: Sequence[float], *, seed: int) -> dict[str, Any]:
    data = [float(value) for value in values]
    return {
        "n_tissues": len(data),
        "mean_difference": float(np.mean(data)),
        "paired_tissue_bootstrap_95": _bootstrap_mean_interval(data, seed=seed),
        "directions": {
            "positive": sum(value > 1e-12 for value in data),
            "tied": sum(abs(value) <= 1e-12 for value in data),
            "negative": sum(value < -1e-12 for value in data),
        },
        "tissue_differences": data,
    }


def audit_e49(root: Path, tracker: InputTracker) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries, integrity = _load_e49_shards(root, tracker)
    summary = tracker.json(root / "results/full/triangle_summary.json")
    source = _read(tracker, root / "src/triangle_final/pipeline.py")
    expected = {
        *(('transport', arm, tissue) for arm in E49_ARMS for tissue in range(12)),
        *(('adoption', tissue) for tissue in range(6)),
        *(("steer", arm, tissue, k)
          for arm in E49_ARMS for tissue in range(12) for k in E49_IMPRINT_GENERATIONS),
    }
    observed: list[tuple[Any, ...]] = []
    for row in entries:
        if row["kind"] == "transport":
            observed.append(("transport", str(row["arm"]), int(row["tissue"])))
        elif row["kind"] == "adoption":
            observed.append(("adoption", int(row["tissue"])))
        else:
            observed.append(
                ("steer", str(row["arm"]), int(row["tissue"]), int(row["k"]))
            )
    integrity.update(
        {
            "expected_entries": 150,
            "kind_counts": dict(Counter(str(row["kind"]) for row in entries)),
            "unique_jobs": len(set(observed)),
            "complete_expected_jobs": set(observed) == expected,
            "no_duplicate_jobs": len(observed) == len(set(observed)),
            "summary_digest_matches_shards": (
                summary["config_digest"] == integrity["config_digest"]
            ),
        }
    )

    transport = [row for row in entries if row["kind"] == "transport"]
    indexed = {(str(row["arm"]), int(row["tissue"])): row for row in transport}
    aggregate: dict[str, Any] = {}
    for arm in E49_ARMS:
        aggregate[arm] = {}
        rows = [row for row in transport if row["arm"] == arm]
        for distance in E49_DISTANCES:
            key = str(distance)
            aggregate[arm][key] = {
                "profile_recovery": float(
                    np.mean([row["by_distance"][key]["profile_recovery"] for row in rows])
                ),
                "sign_recovery": float(
                    np.mean([row["by_distance"][key]["sign_recovery"] for row in rows])
                ),
                "cone_median": float(np.median([row["spatial_cone"] for row in rows])),
            }

    tissue_rows: list[dict[str, Any]] = []
    for tissue in range(12):
        row: dict[str, Any] = {"tissue": tissue, "distance": 8}
        for arm in E49_ARMS:
            source_row = indexed[(arm, tissue)]["by_distance"]["8"]
            row[f"{arm}_profile"] = float(source_row["profile_recovery"])
            row[f"{arm}_sign"] = float(source_row["sign_recovery"])
        row["T_minus_D_profile"] = row["T_profile"] - row["D_profile"]
        row["T_minus_T_lesion_profile"] = row["T_profile"] - row["T_lesion_profile"]
        row["T_minus_D_sign"] = row["T_sign"] - row["D_sign"]
        row["T_minus_T_lesion_sign"] = row["T_sign"] - row["T_lesion_sign"]
        tissue_rows.append(row)

    adoption_rows = sorted(
        (row for row in entries if row["kind"] == "adoption"),
        key=lambda row: int(row["tissue"]),
    )
    adoption_curves = [list(map(float, row["adoption_curve"])) for row in adoption_rows]
    adoption_mean = np.asarray(adoption_curves).mean(axis=0).tolist()
    adoption_final = float(adoption_mean[-1])
    steering: dict[str, dict[str, float]] = {}
    for arm in E49_ARMS:
        steering[arm] = {}
        for k in E49_IMPRINT_GENERATIONS:
            selected = [
                row for row in entries
                if row["kind"] == "steer" and row["arm"] == arm and int(row["k"]) == k
            ]
            steering[arm][str(k)] = float(
                np.mean([row["success_rate"] for row in selected])
            )
    best_steer = {arm: max(values.values()) for arm, values in steering.items()}
    at_eight = {arm: aggregate[arm]["8"] for arm in E49_ARMS}
    residual = lambda arm: 1.0 - at_eight[arm]["profile_recovery"]
    recalculated_gates = {
        "transport": {
            arm: {
                "cone": at_eight[arm]["cone_median"],
                "profile_recovery": at_eight[arm]["profile_recovery"],
                "sign_recovery": at_eight[arm]["sign_recovery"],
            }
            for arm in E49_ARMS
        },
        "gate_p49_1_transport": bool(
            residual("T") <= 0.5 * max(residual("D"), 1e-9)
            and at_eight["T"]["sign_recovery"] >= 0.8
        ),
        "adoption_final_agreement": adoption_final,
        "gate_p49_2_freedom": bool(adoption_final >= 0.8),
        "steer": best_steer,
        "gate_p49_3_imprint_steering": bool(best_steer["T"] >= 0.5),
        "gate_p49_4_knife": bool(
            residual("T_lesion") >= 0.9 * residual("D")
            and best_steer["T_lesion"] < 0.1
        ),
    }
    contrasts = {
        "profile_T_minus_D": _contrast(
            [row["T_minus_D_profile"] for row in tissue_rows], seed=20260902151
        ),
        "profile_T_minus_T_lesion": _contrast(
            [row["T_minus_T_lesion_profile"] for row in tissue_rows], seed=20260902152
        ),
        "sign_T_minus_D": _contrast(
            [row["T_minus_D_sign"] for row in tissue_rows], seed=20260902153
        ),
        "sign_T_minus_T_lesion": _contrast(
            [row["T_minus_T_lesion_sign"] for row in tissue_rows], seed=20260902154
        ),
    }
    return {
        "integrity": integrity,
        "current_source_config_digest": source_config_digests()["E49_triangle_final"],
        "retained_config_digest": summary["config_digest"],
        "current_source_digest_matches_retained": (
            source_config_digests()["E49_triangle_final"] == summary["config_digest"]
        ),
        "transport_by_distance": aggregate,
        "recalculated_gates": recalculated_gates,
        "all_reported_gates_and_summaries_match": _recursive_close(
            recalculated_gates, summary["gates"]
        ),
        "distance_8_contrasts": contrasts,
        "registered_residual_error_ratio_T_over_D": residual("T") / residual("D"),
        "adoption": {
            "sample_sweeps": [200, 400, 600, 800, 1000, 1200],
            "n_tissues": len(adoption_rows),
            "tissue_curves": adoption_curves,
            "mean_curve": adoption_mean,
            "final_agreement": adoption_final,
            "registered_bar": 0.8,
            "gate_pass": adoption_final >= 0.8,
            "target_is_held_after_initial_overwrite": False,
            "target_is_resettled_or_attainability_checked": False,
            "new_pattern_defense_challenge_after_adoption": False,
        },
        "steering_rate_by_arm_and_k": steering,
        "timescale_identification": {
            "rho": 0.002,
            "c_m": 0.2,
            "repair_rho_values_tested": [0.002],
            "repair_has_rho_factor": False,
            "repair_timescale_effect_identified": False,
            "source_instantiates_default_blueprint": "bp = BlueprintConfig()" in source,
            "arm_in_transport_rng_namespace": (
                'seed_rng(config.trajectory_seed_tag + "-transport", arm, index)' in source
            ),
            "T_and_T_lesion_common_random_stream": False,
        },
    }, tissue_rows


def audit_e50(
    root: Path,
    tracker: InputTracker,
    prior_l10_audit: Path | None,
) -> dict[str, Any]:
    summary = tracker.json(root / "results/full/jamesfinal_summary.json")
    source = _read(tracker, root / "src/james_final/pipeline.py")
    gates = summary["gates"]
    replay: dict[str, Any] | None = None
    if prior_l10_audit is not None:
        prior = tracker.json(prior_l10_audit)
        e50 = prior["focused_replay"]["E50"]
        overall = e50["overall"]
        replay = {
            "source": str(prior_l10_audit.resolve()),
            "reconstructs_retained_cessation_fields": bool(
                e50["reconstructs_retained_cessation_fields"]
            ),
            "rows": int(overall["rows"]),
            "futures": int(overall["futures"]),
            "arrived_futures": int(overall["arrived_futures"]),
            "nonarrival_futures": int(overall["nonarrival_futures"]),
            "settling_eligible_rows": int(overall["settling_eligible_rows"]),
            "lock_eligible_rows": int(overall["lock_eligible_rows"]),
            "positive_chronic_rows": int(sum(
                row["chronic_excess"] is not None and row["chronic_excess"] > 0
                for row in e50["rows"]
            )),
            "chronic_excess": overall["chronic_excess"],
            "historical_simulator_futures_replayed_in_prior_audit": int(
                overall["futures"]
            ),
            "replayed_in_this_l15_run": False,
        }
    return {
        "current_source_config_digest": source_config_digests()["E50_james_final"],
        "retained_config_digest": summary["config_digest"],
        "current_source_digest_matches_retained": (
            source_config_digests()["E50_james_final"] == summary["config_digest"]
        ),
        "retained_gates": gates,
        "prior_l10_exact_replay": replay,
        "retention": {
            "aggregate_summary_machine_readable": True,
            "historical_lower_rows_retained_in_E50_package": False,
        },
        "category_audit": {
            "zap_endpoint_is_return_to_pre_zap_sign_map": (
                "pre_sign = V > 0" in source
                and "match = ((V > 0) == pre_sign)" in source
            ),
            "new_identity_target_defined_in_E50": False,
            "new_identity_adoption_measured_in_E50": False,
            "new_identity_defense_challenge_measured_in_E50": False,
            "gain_or_rho_varied_in_zap_assay": False,
            "zap_duration_varied": True,
            "injury_experience_factorial_present": False,
            "nonrecovery_logically_implies_adoption": False,
            "transient_stress_observed": False,
            "chronic_excess_retained": gates["chronic_excess_mean"],
            "recovery_horizon_sweeps": 100,
            "horizon_as_fraction_of_one_over_rho": 0.2,
        },
    }


def rows_csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return handle.getvalue()


def e48_surface_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "cell", "rho", "c_m", "h_above", "h_below", "survival_8",
            "conversion", "screen_pass_reported", "screen_pass_recalculated",
            "freedom_pass_reported", "freedom_pass_recalculated",
            "joint_pass_recalculated", "screen_survival_margin",
            "conversion_margin", "isolated_mismatch_q",
            "isolated_limiting_new_fraction",
        ),
    )


def e49_tissue_contrasts_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return rows_csv(
        rows,
        (
            "tissue", "distance", "D_profile", "T_profile", "T_lesion_profile",
            "T_minus_D_profile", "T_minus_T_lesion_profile", "D_sign", "T_sign",
            "T_lesion_sign", "T_minus_D_sign", "T_minus_T_lesion_sign",
        ),
    )


def run_l15_audit(
    plastic_root: Path,
    workspace: Path,
    *,
    prior_l10_audit: Path | None = None,
) -> tuple[
    dict[str, Any],
    list[Path],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[Path, str],
]:
    tracker = InputTracker()
    ideas_root = plastic_root / IDEAS_RELATIVE
    narrative = (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas_root / "LAWS.md",
        ideas_root / "WAVE11_PROPHECIES.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        workspace / "laws/L15_timescale.md",
        workspace / "reviews/L09_RETAINED_AUDIT_2026-09-02.md",
        workspace / "reviews/L10_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        workspace / "reviews/L14_PRICE_ORDER_LEDGER_AUDIT_2026-09-02.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    e48, e48_rows = audit_e48(_experiment_root(plastic_root, "blueprint_web"), tracker)
    e49, e49_rows = audit_e49(_experiment_root(plastic_root, "triangle_final"), tracker)
    e50 = audit_e50(
        _experiment_root(plastic_root, "james_final"), tracker, prior_l10_audit
    )
    fixed_ema = {str(rho): ema_response(rho) for rho in RHO_VALUES}
    coupled = {
        f"{rho}|{gain}": comparator_ema_substep(rho, gain)
        for rho in RHO_VALUES for gain in GAIN_VALUES
    }
    current_digests = source_config_digests()
    retained_digests = {
        "E48_blueprint_web": e48["retained_config_digest"],
        "E49_triangle_final": e49["retained_config_digest"],
        "E50_james_final": e50["retained_config_digest"],
    }
    digest_matches = {
        name: current_digests[name] == retained_digests[name]
        for name in current_digests
    }

    criterion_revision = {
        "original_registered_gate": "settled abs(R-V) <= 10% of insult-scale signal",
        "adjudicated_gate": (
            "settled abs(R-V) within 1.5x tissue thermal fluctuation and sign agreement > 0.9"
        ),
        "revision_explicit_in_wave11_scorecard": "criterion revision recorded" in texts[
            "WAVE11_PROPHECIES.md"
        ],
        "same_numerical_gate": False,
        "reported_values_machine_readable": False,
    }
    design_coverage = {
        "E48_freedom": {
            "rho_levels": 3,
            "gain_levels": 3,
            "endpoint": "lineage heredity screen plus excess persistent census rewrite",
        },
        "E49_repair": {
            "rho_levels": 1,
            "gain_levels_for_live_T": 1,
            "comparator_ablation_present": True,
            "endpoint": "profile and positional-sign restoration after displacement",
        },
        "E49_adoption": {
            "rho_levels": 1,
            "gain_levels": 1,
            "target_held": False,
            "endpoint": "reference sign agreement with initial imposed raw pattern",
        },
        "E50_zap": {
            "rho_levels": 1,
            "gain_levels": 1,
            "zap_duration_levels": 3,
            "endpoint": "return to pre-zap positional sign map and batch mean abs(R-V)",
        },
        "rho_varied_on_repair": False,
        "rho_varied_on_stress": False,
        "gain_varied_on_common_injury_experience_endpoint": False,
        "target_compatibility_varied_independently": False,
        "new_identity_defense_tested": False,
        "necessity_and_sufficiency_design_present": False,
    }
    claims = [
        {
            "claim": "A slow EMA reference is satisfiable by construction",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "For a body held fixed and 0<rho<1, the coded recurrence converges "
                "asymptotically. This identity does not solve the coupled noisy tissue."
            ),
        },
        {
            "claim": "E48 empirically settles inside the defined noise floor",
            "verdict": "NOT_CONFIRMED_FROM_RETAINED_ARTIFACT",
            "evidence_level": "E1/E2",
            "reason": (
                "The 0.294 vs 0.351 and sign 0.948 values are absent from E48's only "
                "retained JSON; the registered 10%-of-insult gate was revised to a noise-floor gate."
            ),
        },
        {
            "claim": "The gain sweep contains a reproducible sharp freedom frontier",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "The retained 3x3 aggregate exactly recalculates a pass/fail bracket between "
                "c_m 0.2 and 0.4 at all three rho values. It has no independent rerun, cell-level "
                "uncertainty, or points that localize sharpness."
            ),
        },
        {
            "claim": "At a freedom-compatible point, the reference improves positional repair",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E3",
            "reason": (
                "At rho=0.002 and c_m=0.2, E49's T-minus-lesion profile and sign effects "
                "are positive in all 12 tissues and the registered repair gate passes."
            ),
        },
        {
            "claim": "The same dial partitions perturbations into injury and experience",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E4",
            "reason": (
                "No common dial-by-perturbation factorial exists. E49's adoption gate fails; "
                "E50 defines only return to the pre-zap state, and its exact prior replay has "
                "no arrivals, no settling, and no challenge of an alleged new identity."
            ),
        },
        {
            "claim": "The reference escapes L9 exactly insofar as it tracks a slower self",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E3",
            "reason": (
                "Repair never varies rho, all three rho values share the same E48 pass pattern, "
                "and the construction changes full-field content and comparator gain as well as time. "
                "No necessity-and-sufficiency proof or design is present."
            ),
        },
        {
            "claim": "Planarian reprogramming should show transient stress then defense of the new pattern",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E0",
            "reason": (
                "No biological experiment is present; E50 itself observes neither settling nor "
                "defense of a newly adopted model state within its horizon."
            ),
        },
    ]
    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L15",
        "audit_kind": "outcome-known retained recalculation plus exact limited-case analysis",
        "work_state": "RECALCULATED",
        "overall_verdict": "MIXED",
        "fresh_scientific_futures_generated": 0,
        "historical_simulator_futures_replayed_this_run": 0,
        "prior_replayed_futures_reused_as_audited_input": (
            1120 if prior_l10_audit is not None else 0
        ),
        "source_config_digests": current_digests,
        "retained_config_digests": retained_digests,
        "source_config_digest_matches": digest_matches,
        "all_source_config_digests_match": all(digest_matches.values()),
        "E48_freedom_surface": e48,
        "E48_surface_rows": e48_rows,
        "satisfiability_criterion_revision": criterion_revision,
        "exact_update_analysis": {
            "fixed_body_ema": fixed_ema,
            "centered_mode_comparator_ema_substep": coupled,
            "coded_update_has_two_distinct_dials": True,
            "rho_role": "reference update rate",
            "c_m_role": "body-to-reference enforcement gain",
            "declining_R_minus_V_identifies_adoption": False,
        },
        "E49_repair_and_adoption": e49,
        "E50_stress_and_category": e50,
        "cross_experiment_design_coverage": design_coverage,
        "claim_assessment": claims,
        "manuscript_v2_3_independent_support": False,
        "strongest_supported_wording": (
            "In this conserved voltage-sheet implementation, a full-field reference updated by "
            "a coded EMA has a built-in slow fixed-body tracking response. One retained 3x3 "
            "calibration places the combined lineage-rewrite pass at c_m=0.2 and failures at "
            "0.4 and 0.8 for all three tested rho values. At the selected rho=0.002, c_m=0.2 "
            "point, the comparator produces a large, tissue-consistent positional-repair effect. "
            "These results do not establish a sharp reproducible frontier, a rho-dependent repair "
            "law, or an injury/experience partition."
        ),
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return audit, sorted(tracker.paths), e48_rows, e49_rows, frozen_hashes


def _fmt(value: float | int | None, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e48 = audit["E48_freedom_surface"]
    e49 = audit["E49_repair_and_adoption"]
    e50 = audit["E50_stress_and_category"]
    lines = [
        "# L15 retained timescale audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained recalculation and exact limited-case analysis; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "There is a real repair result here, but not yet a timescale law.",
        "",
        "The E48 table cleanly separates the tested gains: every `c_m=0.2` cell passes "
        "the stored lineage/freedom rules and every `0.4` or `0.8` cell fails, regardless "
        "of which of the three rho values was used. E49 then shows a large positional-repair "
        "benefit at the selected `rho=0.002, c_m=0.2` point. Those are the two bounded findings "
        "that survive.",
        "",
        "What does not follow is the title's causal emphasis. Repair was never run at a second "
        "rho. The clean empirical boundary is across enforcement gain, not reference speed. "
        "The model has both dials, and its coupled update lets a shrinking `|R-V|` arise through "
        "body reversion, reference adoption, or both.",
        "",
        "The injury/experience claim is also untested as a partition. E49's explicit adoption "
        "gate fails at 0.489. E50 has no return-to-old-state arrivals, but non-recovery alone is "
        "not adoption; it defines no new target and never challenges the alleged new state. Its "
        "prior exact replay has positive chronic excess in all 70 T rows and no stress settling "
        "within 100 sweeps.",
        "",
        "## Provenance boundary",
        "",
        f"The audit hashed {audit['input_file_count']} consumed inputs. E49 and E50's current "
        "default configuration digests match their retained summaries; E48's current default "
        "digest does not match the historical retained digest. E48 retains only its calibration "
        "square. The reported satisfiability `0.294 vs 0.351`, sign `0.948`, regrowth "
        "`0.711 vs 0.543`, and whole-R cohort are not machine-readable retained results.",
        "",
        "The registered P48.1 criterion was `|R-V| <= 10%` of an insult-scale signal. The "
        "scorecard explicitly records a revision to a tissue-noise-floor comparison. That may be "
        "a useful diagnostic, but it is not the same frozen numerical gate.",
        "",
        "## E48: the finite surface",
        "",
        "| rho | c_m | h>.9 | h<.85 | survival | conversion | screen | freedom | joint |",
        "|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in sorted(
        audit["E48_surface_rows"], key=lambda item: (item["rho"], item["c_m"])
    ):
        lines.append(
            f"| {row['rho']:.3g} | {row['c_m']:.1f} | {row['h_above']:.3f} | "
            f"{row['h_below']:.3f} | {row['survival_8']:.3f} | "
            f"{row['conversion']:.3f} | {row['screen_pass_recalculated']} | "
            f"{row['freedom_pass_recalculated']} | {row['joint_pass_recalculated']} |"
        )
    axis = e48["axis_contrast"]
    lines.extend(
        [
            "",
            f"All three gain sequences are monotone non-increasing: "
            f"`{axis['all_gain_sequences_monotone_nonincreasing']}`. The mean conversion drop "
            f"from gain 0.2 to 0.8 is `{axis['mean_conversion_drop_gain_0_2_to_0_8']:.4f}`; "
            f"the mean range across rho within a gain is "
            f"`{axis['mean_conversion_range_across_rho_within_gain']:.4f}`. Their descriptive "
            f"ratio is `{axis['descriptive_gain_drop_to_rho_range_ratio']:.2f}`. This exposes "
            "scale in the observed table; it is not a factorial effect estimate because lower-level "
            "uncertainty is unavailable.",
            "",
            "The table locates a finite tested bracket between gains 0.2 and 0.4. It does not "
            "sample inside that interval, estimate a discontinuity, or independently repeat the "
            "square, so `sharp` and `reproducible` remain unsupported.",
            "",
            "## Exact update analysis",
            "",
            "### Fixed body",
            "",
            "| rho | 1/rho | exact e-fold | residual @100 | @500 | @1200 | 20% sweep | 5% sweep |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for rho in RHO_VALUES:
        row = audit["exact_update_analysis"]["fixed_body_ema"][str(rho)]
        residual = row["residual_fraction"]
        threshold = row["first_integer_sweep_at_or_below"]
        lines.append(
            f"| {rho:.3g} | {row['one_over_rho']:.0f} | "
            f"{row['exact_discrete_e_folding_sweeps']:.3f} | {residual['100']:.4g} | "
            f"{residual['500']:.4g} | {residual['1200']:.4g} | "
            f"{threshold['20_percent']} | {threshold['5_percent']} |"
        )
    lines.extend(
        [
            "",
            "This is exact only when V is held fixed. It confirms a coded exponential lag and "
            "asymptotic agreement, not E48's finite noise-floor statistic.",
            "",
            "### Isolated centered comparator/EMA mode",
            "",
            "For `a=dt*c_m`, the no-plant, no-noise, unclipped centered mode has mismatch factor "
            "`q=(1-rho)(1-a)`. Its two eigenvalues are 1 and q. A one-time unit V change with "
            "old R=0 converges to `rho(1-a)/(a+rho(1-a))`; the rest is reversion toward the old "
            "reference in this limited subsystem.",
            "",
            "| rho | c_m | a | q | mismatch e-fold | limiting new fraction |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for rho in RHO_VALUES:
        for gain in GAIN_VALUES:
            row = audit["exact_update_analysis"]["centered_mode_comparator_ema_substep"][
                f"{rho}|{gain}"
            ]
            lines.append(
                f"| {rho:.3g} | {gain:.1f} | {row['a_dt_times_c_m']:.3f} | "
                f"{row['mismatch_decay_q']:.5f} | {row['mismatch_e_folding_sweeps']:.2f} | "
                f"{row['limiting_new_body_fraction_after_unit_V_step']:.4f} |"
            )
    lines.extend(
        [
            "",
            "At the selected point the isolated mismatch e-fold is about 23 sweeps, not 500, "
            "because comparator gain moves V while rho moves R. This is not a full-model forecast; "
            "it demonstrates why stress decay cannot be equated with experience adoption without "
            "measuring both trajectories.",
            "",
            "## E49: selected-point repair survives",
            "",
            "| Arm | Profile recovery at d=8 | Sign recovery | Cone |",
            "|---|---:|---:|---:|",
        ]
    )
    for arm in E49_ARMS:
        row = e49["recalculated_gates"]["transport"][arm]
        lines.append(
            f"| {arm} | {row['profile_recovery']:.4f} | {row['sign_recovery']:.4f} | "
            f"{row['cone']:.0f} |"
        )
    contrasts = e49["distance_8_contrasts"]
    lines.extend(
        [
            "",
            f"T minus T-lesion is `{contrasts['profile_T_minus_T_lesion']['mean_difference']:+.4f}` "
            f"for profile recovery (tissue bootstrap "
            f"`[{contrasts['profile_T_minus_T_lesion']['paired_tissue_bootstrap_95'][0]:+.4f}, "
            f"{contrasts['profile_T_minus_T_lesion']['paired_tissue_bootstrap_95'][1]:+.4f}]`) and "
            f"`{contrasts['sign_T_minus_T_lesion']['mean_difference']:+.4f}` for sign recovery "
            f"(`[{contrasts['sign_T_minus_T_lesion']['paired_tissue_bootstrap_95'][0]:+.4f}, "
            f"{contrasts['sign_T_minus_T_lesion']['paired_tissue_bootstrap_95'][1]:+.4f}]`). "
            "All 12 tissue differences are positive for both endpoints.",
            "",
            "This confirms repair at one selected setting. Because E49 instantiates the default "
            "blueprint and never crosses rho, it supplies no repair-timescale curve.",
            "",
            "### Adoption and steering do not pass",
            "",
            f"E49's mean reference-to-initial-target sign curve at sweeps 200--1200 is "
            f"`{[round(value, 4) for value in e49['adoption']['mean_curve']]}`. The final "
            f"value is `{e49['adoption']['final_agreement']:.4f}` against the registered `0.8` "
            "bar. The raw target is imposed once, not held or checked for attainability under "
            "native dynamics. Every imprint-steering rate is zero.",
            "",
            "## E50 does not establish an injury/experience partition",
            "",
            f"The retained E50 summary reports naive arrival `{e50['retained_gates']['naive_arrival']}`, "
            f"stress-arrival lock `{e50['retained_gates']['median_stress_arrival_lock']}`, and mean "
            f"chronic excess `{e50['retained_gates']['chronic_excess_mean']:.4f}`. Its cessation, "
            "trap-without-greed, and generalization gates fail; only the noisy-road diversity gate passes.",
            "",
        ]
    )
    replay = e50["prior_l10_exact_replay"]
    if replay is not None:
        lines.extend(
            [
                f"The separately completed L10 replay reconstructs the E50 aggregate from "
                f"`{replay['rows']}` T rows and `{replay['futures']}` historical futures: "
                f"`{replay['arrived_futures']}` arrivals, `{replay['settling_eligible_rows']}` "
                f"settling rows, and `{replay['positive_chronic_rows']}` positive-chronic rows. "
                "L15 does not rerun those futures; it consumes the immutable prior audit as a hashed input.",
                "",
            ]
        )
    lines.extend(
        [
            "E50 asks only whether V returns to its pre-zap sign map. It defines no candidate new "
            "identity and applies no later challenge to test defense. E48's census conversion and "
            "E50's positional non-arrival also use different observers and timescales. Calling the "
            "latter `experience` is therefore a post-hoc category, not a discriminated outcome.",
            "",
            "## Clause adjudication",
            "",
            "| Atomic claim | Verdict | Level | Reason |",
            "|---|---|---:|---|",
        ]
    )
    for claim in audit["claim_assessment"]:
        lines.append(
            f"| {claim['claim']} | `{claim['verdict']}` | {claim['evidence_level']} | "
            f"{claim['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Strongest wording supported",
            "",
            audit["strongest_supported_wording"],
            "",
            "## Next closer-pass experiment",
            "",
            "Freeze a common factorial before running it: cross rho and c_m on the same repair, "
            "old-state resistance, held-new-target adoption, post-adoption challenge, and `|R-V|` "
            "trajectories. Independently vary insult duration/amplitude and target compatibility. "
            "That design can distinguish body reversion from reference adoption and can test whether "
            "one dial really partitions injury from experience.",
            "",
        ]
    )
    return "\n".join(lines)
