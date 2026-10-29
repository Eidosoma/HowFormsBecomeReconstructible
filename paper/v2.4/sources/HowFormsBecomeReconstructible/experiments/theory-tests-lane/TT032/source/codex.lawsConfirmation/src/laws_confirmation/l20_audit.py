"""Outcome-known retained audit for L20's self-written-genome claim."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import canonical_digest, sha256_file
from .stats import close


EXPECTED_CONFIG_DIGESTS = {
    "E66_writable_landlord": "9def6662a2533a853811cbbcac8f0a069e35f6d1f9ef57da2f04ff193d63d982",
    "E67_alphabet": "33f6b18cc62c865f73fb4cd81c14970d7db34dee11d3a01729c7940d8b2e47c5",
    "E68_deep_eigen": "58f853b85b882d6744a6cadf7f9589cfb75fba04e6e427f9ae135e59b85f95e6",
}

TRACKED_PACKAGES = (
    "writable_landlord",
    "alphabet",
    "deep_eigen",
    "blueprint_web",
    "ladder_web",
    "voltage_web",
    "setpoint_rewrite",
    "assimilation",
    "two_headed_final",
    "contract_bridge",
)

E66_ARMS = ("writable_fast", "writable_slow", "frozen", "gain_matched")
E68_CORRS = (1.0, 0.95, 0.9, 0.8, 0.65, 0.5, 0.3, 0.1)


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
        "writable_landlord": "landlord_summary.json",
        "alphabet": "alphabet_summary.json",
        "deep_eigen": "deepeigen_summary.json",
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
    """Digest independently transcribed current E66--E68 defaults."""

    configs: dict[str, dict[str, Any]] = {
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
        "E67_alphabet": {
            "mode": "full",
            "norm_primary": 0.15,
            "norm_secondary": 0.3,
            "write_gain": 1.5,
            "express_sweeps": 300,
            "express_futures": 4,
            "form_seeds": [1, 3, 5, 7],
            "prescreen_half_mean": 0.15,
            "interaction_bar": 0.25,
            "n_donor_shuffles": 200,
            "repertoire_seeds": 10,
            "repertoire_distinct": 0.8,
            "k_max": 7,
            "write_lambda": 0.001,
            "hysteresis_write_sweeps": 1500,
            "hysteresis_futures": 2,
            "robustness_rhos": [0.001, 0.004],
            "trajectory_seed_tag": "alphabet-v1",
        },
        "E68_deep_eigen": {
            "mode": "full",
            "n_tissues": 3,
            "futures": 4,
            "norm": 0.3,
            "write_lambda": 0.001,
            "settle_sweeps": 120,
            "imprint_sweeps": 1000,
            "imprint_hold": 1.2,
            "cycles": 12,
            "inter_fission": 1000,
            "amp_threshold": 0.2,
            "chance": 0.5,
            "bootstrap": 200,
            "trajectory_seed_tag": "deep-eigen-v1",
        },
    }
    return {name: canonical_digest(config) for name, config in configs.items()}


def _seed_rng(tag: str, *parts: int) -> np.random.Generator:
    digest = hashlib.sha256(
        (tag + ":" + ":".join(map(str, parts))).encode()
    ).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "little"))


def native_theta_input_rows() -> list[dict[str, Any]]:
    """Rebuild tissue parameters and theta inputs, without running dynamics."""

    rows: list[dict[str, Any]] = []
    for tissue in range(4):
        parameter_rng = _seed_rng("voltage-tissue-params-v1", tissue)
        well_asym = float(parameter_rng.uniform(-0.05, 0.05))
        threshold_spread = float(parameter_rng.uniform(0.15, 0.30))
        native = threshold_spread * _seed_rng(
            "voltage-tissue-v1", tissue
        ).standard_normal((16, 16))
        sample_std = float(native.std())
        rows.append(
            {
                "tissue": tissue,
                "well_asym": well_asym,
                "configured_threshold_spread": threshold_spread,
                "native_theta_sample_mean": float(native.mean()),
                "native_theta_sample_std": sample_std,
                "writable_initial_theta_sample_mean": 0.0,
                "writable_initial_theta_sample_std": 0.3,
                "writable_projection_scale_factor": 0.3 / sample_std,
            }
        )
    return rows


def _audit_e66(
    root: Path, tracker: InputTracker, theta_rows: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = tracker.json(root / "results/full/landlord_summary.json")
    source = _read(tracker, root / "src/writable_landlord/pipeline.py")
    config_source = _read(tracker, root / "src/writable_landlord/config.py")
    assimilation_source = _read(
        tracker,
        root.parent / "assimilation/src/assimilation/pipeline.py",
    )
    blueprint_source = _read(
        tracker,
        root.parent / "blueprint_web/src/blueprint_web/engine.py",
    )
    ladder_source = _read(
        tracker,
        root.parent / "ladder_web/src/ladder_web/engine.py",
    )
    voltage_source = _read(
        tracker,
        root.parent / "voltage_web/src/voltage_web/engine.py",
    )
    gates = summary["gates"]

    capacity = gates["capacity"]
    chosen = next(
        (float(row["norm"]) for row in capacity["rows"] if row["pin"] >= 0.8),
        None,
    )
    gain = gates["gain_match"]
    zone_cells = 16 * (16 // 4)
    pullback_denominator = 4 * zone_cells
    target_increment = int(
        round(gain["writable_rate"] * 50 * pullback_denominator)
    )
    gain_rows = []
    for row in gain["rows"]:
        increment = int(round(row["rate"] * 50 * pullback_denominator))
        gain_rows.append(
            {
                "c_m": float(row["c_m"]),
                "rate": float(row["rate"]),
                "implied_net_recovered_signs_out_of_256": increment,
                "absolute_distance_from_writable_in_signs": abs(
                    increment - target_increment
                ),
            }
        )
    nearest_distance = min(
        row["absolute_distance_from_writable_in_signs"] for row in gain_rows
    )
    tied_nearest = [
        row["c_m"]
        for row in gain_rows
        if row["absolute_distance_from_writable_in_signs"] == nearest_distance
    ]

    fidelity = {key: float(value) for key, value in gates["fidelity"].items()}
    freedom = {key: float(value) for key, value in gates["freedom_cost"].items()}
    transplant = {
        key: float(value) for key, value in gates["transplant"].items()
    }
    f_delta = fidelity["writable_fast"] - fidelity["gain_matched"]
    freedom_delta = freedom["writable_fast"] - freedom["gain_matched"]
    repertoire = gates["repertoire"]
    fast_repertoire_loss = (
        repertoire["writable_fast"]["native_classes"]
        - repertoire["writable_fast"]["written_classes"]
    )
    fast_repertoire_loss_fraction = fast_repertoire_loss / repertoire[
        "writable_fast"
    ]["native_classes"]

    work = root / "results/full/work"
    lower_files = (
        sorted(path for path in work.rglob("*") if path.is_file())
        if work.is_dir()
        else []
    )
    metrics = [
        {
            "section": "capacity",
            "metric": "pin",
            "arm_or_condition": f"norm={row['norm']}",
            "value": float(row["pin"]),
            "comparison_or_note": "one tissue, four nested futures, aligned static theta",
            "evidence": "E2",
        }
        for row in capacity["rows"]
    ]
    metrics.extend(
        {
            "section": "fidelity",
            "metric": "tail_fixed_target_fidelity",
            "arm_or_condition": arm,
            "value": fidelity[arm],
            "comparison_or_note": "cycles 10-12 aggregate; lower rows absent",
            "evidence": "E2",
        }
        for arm in E66_ARMS
    )
    metrics.extend(
        {
            "section": "freedom",
            "metric": "whole_sheet_sign_turnover",
            "arm_or_condition": arm,
            "value": freedom[arm],
            "comparison_or_note": "300 sweeps after 8-sweep positive posterior clamp",
            "evidence": "E2",
        }
        for arm in E66_ARMS
    )
    metrics.extend(
        {
            "section": "transplant",
            "metric": "own_target_margin",
            "arm_or_condition": arm,
            "value": transplant[arm],
            "comparison_or_note": "tissue 0; two donors and two recipients each; aggregate only",
            "evidence": "E2",
        }
        for arm in E66_ARMS
    )
    metrics.extend(
        [
            {
                "section": "contrast",
                "metric": "fast_minus_gain_matched_fidelity",
                "arm_or_condition": "writable_fast-gain_matched",
                "value": f_delta,
                "comparison_or_note": "reported aggregate subtraction",
                "evidence": "E2",
            },
            {
                "section": "contrast",
                "metric": "fast_minus_gain_matched_freedom",
                "arm_or_condition": "writable_fast-gain_matched",
                "value": freedom_delta,
                "comparison_or_note": "registered lower tolerance is -0.05",
                "evidence": "E2",
            },
            {
                "section": "imprint",
                "metric": "two_headed_tail_fidelity",
                "arm_or_condition": "writable_fast",
                "value": float(gates["imprint_shot_fidelity"]),
                "comparison_or_note": "eight-cycle confirmatory shot; bar 0.75",
                "evidence": "E2",
            },
        ]
    )

    return {
        "retained_config_digest": summary["config_digest"],
        "aggregate_summary": gates,
        "capacity_audit": {
            "recalculated_first_passing_norm": chosen,
            "matches_reported_choice": chosen == capacity["chosen"] == gates["norm"],
            "target": "launch_pattern(1), a fixed horizontal-half template",
            "target_is_output_of_acquisition_cascade": False,
            "theta_is_hand_aligned_to_target": True,
            "tissues": 1,
            "nested_futures": 4,
            "settle_sweeps": 300,
            "metric": "whole-sheet sign agreement without amplitude threshold",
            "literal_native_theta_std_for_tissue_0": theta_rows[0][
                "native_theta_sample_std"
            ],
            "tested_projected_norm": 0.3,
            "tested_norm_is_literal_native_tissue_0_std": False,
        },
        "gain_match_audit": {
            "writable_rate": float(gain["writable_rate"]),
            "reported_matched_cm": float(gain["matched_cm"]),
            "reported_matched_rate": next(
                row["rate"]
                for row in gain_rows
                if close(row["c_m"], gain["matched_cm"])
            ),
            "absolute_rate_gap": abs(
                next(
                    row["rate"]
                    for row in gain_rows
                    if close(row["c_m"], gain["matched_cm"])
                )
                - gain["writable_rate"]
            ),
            "pullback_score_denominator": pullback_denominator,
            "writable_implied_net_recovered_signs": target_increment,
            "rows": gain_rows,
            "nearest_distance_in_recovered_signs": nearest_distance,
            "equally_nearest_cm_values_on_discrete_score_lattice": tied_nearest,
            "reported_choice_is_unique_nearest": len(tied_nearest) == 1,
            "reported_choice_equals_default_blueprint_cm": close(
                gain["matched_cm"], 0.2
            ),
            "c_m_grid_rate_is_monotone": all(
                gain_rows[index]["rate"] <= gain_rows[index + 1]["rate"]
                for index in range(len(gain_rows) - 1)
            ),
            "tissues": 1,
            "nested_futures": 4,
            "arms_share_random_stream": False,
            "configured_eight_sweep_zap_is_used": "config.pullback_zap_sweeps"
            in source.split("def _measure_pullback", 1)[1].split("def gain_match", 1)[0],
            "actual_perturbation": "instantaneous posterior-quarter sign inversion",
            "observer": "sign recovery at one 50-sweep endpoint",
            "matches_total_restoring_force_over_lineage": False,
        },
        "aggregate_effects": {
            "writable_fast_minus_gain_matched_fidelity": f_delta,
            "writable_fast_minus_frozen_fidelity": fidelity["writable_fast"]
            - fidelity["frozen"],
            "writable_slow_minus_gain_matched_fidelity": fidelity[
                "writable_slow"
            ]
            - fidelity["gain_matched"],
            "writable_fast_minus_writable_slow_fidelity": fidelity[
                "writable_fast"
            ]
            - fidelity["writable_slow"],
            "writable_fast_minus_gain_matched_freedom": freedom_delta,
            "freedom_tolerance": -0.05,
            "freedom_clause_slack": freedom_delta + 0.05,
            "fraction_of_allowed_freedom_decline_used": abs(freedom_delta) / 0.05,
            "fast_absolute_transplant_margin": transplant["writable_fast"],
            "slow_absolute_transplant_margin": transplant["writable_slow"],
            "frozen_absolute_transplant_margin": transplant["frozen"],
            "gain_matched_absolute_transplant_margin": transplant[
                "gain_matched"
            ],
            "fast_minus_frozen_transplant_margin": transplant["writable_fast"]
            - transplant["frozen"],
            "fast_minus_gain_matched_transplant_margin": transplant[
                "writable_fast"
            ]
            - transplant["gain_matched"],
            "frozen_minus_gain_matched_transplant_margin": transplant["frozen"]
            - transplant["gain_matched"],
            "fast_margin_above_absolute_0_1_gate": transplant["writable_fast"]
            - 0.1,
            "frozen_margin_as_fraction_of_fast_margin": transplant["frozen"]
            / transplant["writable_fast"],
            "fast_repertoire_class_loss": fast_repertoire_loss,
            "fast_repertoire_loss_fraction": fast_repertoire_loss_fraction,
            "imprint_shot_minus_registered_bar": float(
                gates["imprint_shot_fidelity"] - 0.75
            ),
        },
        "lineage_and_inheritance_audit": {
            "main_targets": [
                "launch_pattern(1): horizontal halves",
                "launch_pattern(3): vertical stripes",
            ],
            "targets_are_preselected_native_launch_recipes": True,
            "targets_are_empirically_acquired_spontaneous_forms": False,
            "teaching_overwrites_every_cell_to_plus_or_minus_1_2_before_each_step": True,
            "teaching_sweeps": 1000,
            "external_teaching_repeated_after_fission": False,
            "arms_use_common_random_numbers": False,
            "source_design_tissues": 4,
            "source_design_futures_per_tissue": 6,
            "future_target_counts": {"A": 3, "B": 3},
            "fission_keeps_half_V_and_resets_half_with_jitter": True,
            "fission_copies_R_whole_exactly": "Rf.copy()" in assimilation_source,
            "fission_function_accepts_theta": False,
            "theta_array_is_explicitly_copied_at_boundary": False,
            "theta_same_array_persists_in_single_successor_loop": True,
            "branching_parent_and_multiple_daughters_exist": False,
            "theta_writing_continues_in_every_descendant_sweep": True,
            "writer_updates_before_returned_theta_final": 13120,
            "writer_on_only_during_parental_acquisition_arm_present": False,
            "writer_on_but_theta_reset_each_fission_arm_present": False,
            "theta_persisted_but_writer_off_in_descendants_arm_present": False,
            "R_reset_or_noninheritance_factorial_present": False,
            "fidelity_human_cycle_numbers_averaged": [10, 11, 12],
            "fidelity_cycle_trajectory_retained": False,
            "fidelity_condition": "cells assigned to reset half at least twice",
            "fidelity_includes_amplitude_over_0_2": True,
            "target_group_specific_fidelity_retained": False,
            "writable_initial_theta_projected_to_std_0_3": True,
            "frozen_and_gain_initial_theta_left_native": True,
            "initial_theta_preprocessing_identical_across_arms": False,
            "source_checks": {
                "target_construction": "np.stack([tA] * (B // 2)" in source,
                "whole_body_hold": "V = np.where(np.abs(hold) > 0, hold, V)" in source,
                "theta_omitted_at_fission": "V, Rf, fresh = fission_with_mask(V, Rf, tissue, rng)"
                in source,
                "tail_only": "if cycle >= n_cycles - 3" in source,
                "multiply_reset_mask": "m2 = regrow_count >= 2" in source,
            },
        },
        "freedom_audit": {
            "registered_proxy_passes": freedom_delta >= -0.05,
            "posterior_fraction_directly_clamped": 0.25,
            "clamp_value": 1.5,
            "clamp_forces_positive_not_sign_inversion": True,
            "clamp_sweeps": 8,
            "endpoint_sweeps": 300,
            "scored_fraction_of_sheet": 1.0,
            "metric": "fraction of all cell signs changed from pre-zap state",
            "matched_no_zap_counterfactual_present": False,
            "specified_alternate_target_adoption_measured": False,
            "turnover_uniquely_attributable_to_zap": False,
            "survivor_condition": "mean absolute final V > 0.2",
            "survivor_counts_retained": False,
            "equal_freedom_demonstrated": False,
            "general_plasticity_equivalence_demonstrated": False,
            "source_clamp_is_positive": "np.where(clamp[None, :, :], 1.5, V)"
            in ladder_source,
        },
        "transplant_audit": {
            "tissues": 1,
            "donor_future_indices": [0, 5],
            "candidate_donors_per_target_used": 1,
            "fresh_recipients_per_donor": 2,
            "recipient_groups_share_random_stream": False,
            "component_matches_retained": False,
            "donor_theta_fields_retained": False,
            "replicate_variance_retained": False,
            "only_symmetric_aggregate_retained": True,
            "frozen_and_gain_matched_donor_theta_are_identical_native_fields": True,
            "transplant_forces_cm_zero_so_frozen_and_gain_conditions_are_otherwise_identical": True,
            "frozen_gain_margin_difference_due_only_to_rng_namespace": transplant[
                "frozen"
            ]
            - transplant["gain_matched"],
            "common_stream_identical_theta_symmetric_margin_would_equal": 0.0,
            "primary_uses_absolute_0_1_bar_not_control_contrast": True,
            "lineage_specific_content_proven": False,
        },
        "repertoire_audit": {
            "reported_fast_native_classes": int(
                repertoire["writable_fast"]["native_classes"]
            ),
            "reported_fast_written_classes": int(
                repertoire["writable_fast"]["written_classes"]
            ),
            "reported_fast_collapsed": bool(
                repertoire["writable_fast"]["collapsed"]
            ),
            "source_collapse_rule": "written <= 0.5 * native",
            "source_collapse_rule_recalculated": bool(
                repertoire["writable_fast"]["written_classes"]
                <= 0.5 * repertoire["writable_fast"]["native_classes"]
            ),
            "tissues": 1,
            "written_theta_donor_future": 0,
            "written_theta_target_group": "A",
            "launches": 8,
            "futures_per_launch": 2,
            "finals_used_per_launch": 1,
            "class_algorithm": "greedy representatives in launch order",
            "same_class_requires_agreement_strictly_greater_than": 0.8,
            "native_and_written_use_common_random_stream": False,
            "frozen_and_gain_use_identical_theta_but_report_written_counts": [
                int(repertoire["frozen"]["written_classes"]),
                int(repertoire["gain_matched"]["written_classes"]),
            ],
            "identical_theta_panels_show_one_class_rng_variation": True,
            "robust_narrowing_established": False,
        },
        "timescale_and_filter_audit": {
            "rho": 0.002,
            "R_raw_reciprocal_coefficient_clock": 500.0,
            "fast_lambda": 0.001,
            "slow_lambda": 0.0002,
            "fast_lambda_over_rho": 0.5,
            "slow_lambda_over_rho": 0.1,
            "fast_raw_reciprocal_coefficient_clock": 1000.0,
            "slow_raw_reciprocal_coefficient_clock": 5000.0,
            "theta_to_R_raw_clock_ratios": {"fast": 2.0, "slow": 10.0},
            "fast_lambda_is_quantitatively_much_less_than_rho": False,
            "theta_uses_nonlinear_tanh": True,
            "theta_global_mean_centered_each_update": True,
            "theta_projected_to_fixed_std_each_update": True,
            "V_is_a_linear_low_pass_filter": False,
            "frequency_response_measured": False,
            "layerwise_noise_variance_measured": False,
            "signal_noise_decomposition_measured": False,
            "copy_error_curve_measured_in_E66": False,
            "cascade_link_ablation_present": False,
            "direct_V_to_theta_writer_control_present": False,
            "each_layer_cleaner_claim_measured": False,
            "source_checks": {
                "R_update": "Rf = Rf + bp.rho * (V - Rf)" in blueprint_source,
                "theta_update": "lam * np.tanh(Rf)" in source,
                "projection": "theta = project_theta" in source,
                "configured_lambda_fractions": "LAMBDA_FRACS = (0.5, 0.1)"
                in config_source,
            },
        },
        "primary_and_retention_audit": {
            "reported_primary": bool(gates["gate_p66_1_primary"]),
            "reported_cm_in_disguise": bool(gates["cm_in_disguise"]),
            "visible_freedom_clause_passes": freedom_delta >= -0.05,
            "visible_absolute_transplant_clause_passes": transplant[
                "writable_fast"
            ]
            > 0.1,
            "frozen_tissue_fidelity_spread_used_by_gate_retained": False,
            "maximum_spread_compatible_with_reported_fidelity_clause": f_delta
            / 1.645,
            "full_primary_independently_reconstructable": False,
            "cm_in_disguise_boolean_is_mechanism_test": False,
            "cm_in_disguise_formula_relabels_fidelity_gate_failure": True,
            "lower_level_files": [str(path.relative_to(root)) for path in lower_files],
            "retained_resolution": "aggregate summary only",
            "evidence_level": "E2",
        },
        "register_and_implementation": {
            "wave14_registered_dimensions": [32, 32],
            "implemented_dimensions": [16, 16],
            "wave14_registered_lambda_fractions": [0.1, 0.02],
            "implemented_lambda_fractions": [0.5, 0.1],
            "current_expectations_describe_change": True,
            "registered_three_way_swap_components": 3,
            "implemented_three_way_swap_components": 1,
            "registered_written_theta_reseeded_VR_present": False,
            "registered_virgin_theta_kept_VR_present": False,
            "registered_cross_lineage_theta_transplant_present": True,
            "registered_consensus_correlation_secondary_present": False,
            "registered_end_of_run_knife_pair_present": False,
            "imprint_gate_reported": bool(gates["gate_p66_3_imprint"]),
            "imprint_failure_kept_separate": True,
            "source_target_recipes_confirmed": "def launch_pattern" in voltage_source,
        },
    }, metrics


def _audit_e67(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = tracker.json(root / "results/full/alphabet_summary.json")
    source = _read(tracker, root / "src/alphabet/pipeline.py")
    part_names = ("composition", "capacity", "discreteness", "robustness")
    parts: dict[str, Any] = {}
    part_digests: dict[str, Any] = {}
    for part in part_names:
        payload = tracker.json(root / "results/full/work" / f"{part}.json")
        parts[part] = payload["data"]
        part_digests[part] = payload["config_digest"]
    comp = parts["composition"]["primary"]
    reconstructed = {
        **parts,
        "gate_p67_1_primary": bool(comp["compositional"]),
        "interaction_share": comp["fit"]["interaction_share"],
    }

    rows = []
    for label in ("0.001", "0.004"):
        requested = float(label)
        lambda_actual = 0.5 * requested
        values = parts["robustness"][label]
        rows.append(
            {
                "experiment": "E67",
                "modifier": "advertised_rho_robustness",
                "condition": f"rho_label={label}",
                "reported_value": float(values["gap"]),
                "literal_interpretation": (
                    f"theta lambda={lambda_actual:g}; actual R rho=0.002; "
                    "fixed 1000-sweep windows"
                ),
                "admissible_use": "write-rate sensitivity only",
            }
        )

    capacity = parts["capacity"]
    discreteness = parts["discreteness"]
    robustness_rows = []
    for label in ("0.001", "0.004"):
        requested = float(label)
        values = parts["robustness"][label]
        robustness_rows.append(
            {
                "rho_label": requested,
                "actual_R_rho": 0.002,
                "actual_fast_theta_lambda": 0.5 * requested,
                "actual_lambda_over_R_rho": 0.5 * requested / 0.002,
                "actual_imprint_sweeps": 1000,
                "actual_inter_fission_sweeps": 1000,
                "two_over_labelled_rho": 2.0 / requested,
                "writable_fast": float(values["writable_fast"]),
                "gain_matched": float(values["gain_matched"]),
                "gap": float(values["gap"]),
            }
        )
    return {
        "retained_config_digest": summary["config_digest"],
        "part_config_digests": part_digests,
        "all_part_digests_match_summary": all(
            digest == summary["config_digest"] for digest in part_digests.values()
        ),
        "summary_reconstructs_from_part_caches": _recursive_close(
            reconstructed, summary["gates"]
        ),
        "retained_part_resolution": "aggregated part outputs; no trajectory rows",
        "robustness_rows": robustness_rows,
        "robustness_source_audit": {
            "advertised_as_rho_half_and_double": True,
            "monkeypatches_writable_landlord_module_RHO": "wl.RHO = rho" in source,
            "passes_rho_into_BlueprintConfig": False,
            "actual_R_update_rho_stays_0_002": True,
            "only_theta_lambda_changes_with_labelled_rho": True,
            "imprint_window_rescaled_with_labelled_rho": False,
            "inter_fission_window_rescaled_with_labelled_rho": False,
            "gain_match_recalibrated_at_each_labelled_rho": False,
            "matched_cm_hardcoded_to_0_2": "landlord_lineage(lc, i, arm, 0.3, 0.2)"
            in source,
            "source_tissues_per_arm": 2,
            "source_futures_per_tissue": 4,
            "source_cycles": 8,
            "tissue_rows_retained": False,
            "arms_share_random_stream": False,
            "rho_0_004_fast_theta_and_R_have_equal_raw_coefficients": True,
            "validates_rho_robustness": False,
            "validates_bounded_write_rate_sensitivity": True,
        },
        "capacity_modifier": {
            "ideal_write_not_E66_acquired_theta": True,
            "ceiling_from_ten_launches": int(capacity["ceiling"]),
            "largest_tested_K": int(max(row["K"] for row in capacity["rows"])),
            "all_reported_kway_accuracies": [
                float(row["kway_accuracy"]) for row in capacity["rows"]
            ],
            "all_K_through_7_report_one": all(
                close(float(row["kway_accuracy"]), 1.0)
                for row in capacity["rows"]
            ),
            "supports_E66_repertoire_as_capacity_bottleneck": False,
        },
        "follower_modifier": {
            "mean_start_dependence": float(
                discreteness["mean_start_dependence"]
            ),
            "store_bistable": bool(discreteness["store_bistable"]),
            "supports_intrinsic_theta_latch": False,
            "consistent_with_theta_following_current_body": True,
        },
    }, rows


def _slope(fidelities: Sequence[float | None], chance: float = 0.5) -> float | None:
    values = [
        (index, np.log(max(float(value) - chance, 1e-3)))
        for index, value in enumerate(fidelities[1:], start=1)
        if value is not None
    ]
    if len(values) < 4:
        return None
    xs = np.asarray([row[0] for row in values], dtype=float)
    ys = np.asarray([row[1] for row in values], dtype=float)
    return float(np.polyfit(xs, ys, 1)[0])


def _c_star(rows: Sequence[Mapping[str, Any]]) -> float | None:
    points = sorted(
        (float(row["realized"]), float(row["slope"]))
        for row in rows
        if row["slope"] is not None
    )
    for left, right in zip(points, points[1:]):
        x0, s0 = left
        x1, s1 = right
        if s0 < 0 <= s1:
            return float(x0 + (x1 - x0) * (-s0) / (s1 - s0))
    return None


def _audit_e68(
    root: Path, tracker: InputTracker
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = tracker.json(root / "results/full/deepeigen_summary.json")
    source = _read(tracker, root / "src/deep_eigen/pipeline.py")
    pre_payload = tracker.json(root / "results/full/work/preround.json")
    pre = pre_payload["data"]
    entries: list[dict[str, Any]] = []
    work_digests = {pre_payload["config_digest"]}
    cache_integrity = []
    for project in (True, False):
        for corr in E68_CORRS:
            path = root / "results/full/work" / f"lin_{corr}_{int(project)}.json"
            payload = tracker.json(path)
            work_digests.add(payload["config_digest"])
            rows = payload["data"]
            entries.extend(rows)
            cache_integrity.append(
                {
                    "project": project,
                    "c_target": corr,
                    "rows": len(rows),
                    "tissues": sorted(int(row["tissue"]) for row in rows),
                }
            )

    def curve(project: bool) -> list[dict[str, Any]]:
        output = []
        for corr in E68_CORRS:
            rows = [
                row
                for row in entries
                if bool(row["project"]) is project
                and close(float(row["c_target"]), corr)
            ]
            means = []
            for cycle in range(12):
                values = [
                    row["fidelity_by_cycle"][cycle]
                    for row in rows
                    if row["fidelity_by_cycle"][cycle] is not None
                ]
                # Every retained E68 row has an undefined first-cycle score.
                # The historical source emitted NaN through mean([]), then
                # excluded index zero from its slope. Preserve that value
                # without reproducing the avoidable RuntimeWarning.
                means.append(float(np.mean(values)) if values else float("nan"))
            output.append(
                {
                    "c_target": corr,
                    "realized": float(
                        np.mean([float(row["realized_corr"]) for row in rows])
                    ),
                    "slope": _slope(means),
                    "final_fid": means[-1],
                }
            )
        return output

    projected = curve(True)
    unbounded = curve(False)
    predicted = pre["predicted_c_star"]
    cs_projected = _c_star(projected)
    cs_unbounded = _c_star(unbounded)
    reconstructed = {
        "preround": pre,
        "curve_projected": projected,
        "curve_unbounded": unbounded,
        "c_star_projected": cs_projected,
        "c_star_unbounded": cs_unbounded,
        "predicted_c_star": predicted,
        "gate_p68_1_primary": bool(
            cs_projected is not None
            and predicted is not None
            and 0.5 * predicted <= cs_projected <= 2.0 * predicted
            and E68_CORRS[-1] < cs_projected < E68_CORRS[0]
        ),
        "cap_sets_threshold": bool(
            cs_projected is not None
            and cs_unbounded is not None
            and abs(cs_projected - cs_unbounded) > 0.15
        ),
    }
    unbounded_signs = [
        int(np.sign(row["slope"]))
        for row in sorted(unbounded, key=lambda row: row["realized"])
        if row["slope"] is not None
    ]
    sign_changes = sum(
        left != right for left, right in zip(unbounded_signs, unbounded_signs[1:])
    )
    modifier_rows = [
        {
            "experiment": "E68",
            "modifier": "coded_primary",
            "condition": "prediction-versus-observed c_star",
            "reported_value": bool(summary["gates"]["gate_p68_1_primary"]),
            "literal_interpretation": "pre-round prediction is null; primary fails",
            "admissible_use": "does not retroactively confirm E66 filtering",
        },
        {
            "experiment": "E68",
            "modifier": "theta_recovery",
            "condition": "pre-round c=0.3",
            "reported_value": float(pre["rows"][-1]["theta_recovery"]),
            "literal_interpretation": "theta correlation recovers while fidelity delta is negative",
            "admissible_use": "consistent with active rewrite restoration",
        },
        {
            "experiment": "E68",
            "modifier": "projected_zero_crossing",
            "condition": "three-tissue aggregate",
            "reported_value": cs_projected,
            "literal_interpretation": "source's first interpolated slope crossing",
            "admissible_use": "defer threshold validity to L22",
        },
    ]
    return {
        "retained_config_digest": summary["config_digest"],
        "work_config_digests": sorted(work_digests),
        "all_work_digests_match_summary": work_digests == {summary["config_digest"]},
        "cache_integrity": cache_integrity,
        "all_16_conditions_have_three_unique_tissues": all(
            row["rows"] == 3 and row["tissues"] == [0, 1, 2]
            for row in cache_integrity
        ),
        "lineage_rows": len(entries),
        "reconstructed": reconstructed,
        "all_reported_gates_reconstruct": _recursive_close(
            reconstructed, summary["gates"]
        ),
        "mechanism_modifier": {
            "reported_primary_passes": bool(
                summary["gates"]["gate_p68_1_primary"]
            ),
            "all_preround_fidelity_deltas_negative": all(
                float(row["fidelity_delta"]) < 0 for row in pre["rows"]
            ),
            "all_preround_theta_recoveries_positive": all(
                float(row["theta_recovery"]) > 0 for row in pre["rows"]
            ),
            "preround_includes_fission": False,
            "projected_slopes_positive_at_every_c_ge_0_3": all(
                float(row["slope"]) > 0
                for row in projected
                if float(row["realized"]) >= 0.3
            ),
            "projected_curve_monotone_in_correlation": all(
                left["slope"] <= right["slope"]
                for left, right in zip(
                    sorted(projected, key=lambda row: row["realized"]),
                    sorted(projected, key=lambda row: row["realized"])[1:],
                )
            ),
            "unbounded_slope_sign_changes": sign_changes,
            "unbounded_arm_skips_projection_only_at_corruption_instant": True,
            "cascade_reprojects_theta_on_first_subsequent_write_step": True,
            "unbounded_arm_is_unbounded_throughout_recovery": False,
            "projected_and_unbounded_arms_share_random_stream": False,
            "c_equals_1_conditions_differ_only_by_rng_namespace": True,
            "writer_off_mechanism_control_present": False,
            "R_link_ablation_present": False,
            "supports_active_theta_correlation_restoration": True,
            "proves_each_V_R_theta_layer_is_cleaner": False,
            "source_checks": {
                "mix_may_skip_projection": "if project:" in source,
                "cascade_always_projects": "theta = project_theta((1 - lam) * theta"
                in source,
                "project_flag_in_seed": "int(project)" in source,
            },
        },
    }, modifier_rows


def run_l20_audit(
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
    narrative_paths = (
        plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md",
        ideas_root / "LAWS.md",
        ideas_root / "WAVE14_PROPHECIES.md",
        ideas_root / "WAVE14_DESIGN_REVIEW.md",
        ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md",
        workspace / "SOURCE_BASELINE.md",
        workspace / "REVIEW_PROTOCOL.md",
        workspace / "protocols/L20_SELF_WRITTEN_GENOME_AUDIT_V1.md",
        workspace / "laws/L20_self_written_genome.md",
        workspace / "reviews/L19_INCORRUPTIBLE_REFERENCE_AUDIT_2026-09-03.md",
    )
    texts = {path.name: _read(tracker, path) for path in narrative_paths}
    for package in TRACKED_PACKAGES:
        _track_package(tracker, _experiment_root(plastic_root, package))

    theta_rows = native_theta_input_rows()
    e66, metric_rows = _audit_e66(
        _experiment_root(plastic_root, "writable_landlord"), tracker, theta_rows
    )
    e67, e67_modifier_rows = _audit_e67(
        _experiment_root(plastic_root, "alphabet"), tracker
    )
    e68, e68_modifier_rows = _audit_e68(
        _experiment_root(plastic_root, "deep_eigen"), tracker
    )
    modifier_rows = e67_modifier_rows + e68_modifier_rows

    source_digests = source_config_digests()
    retained_digests = {
        "E66_writable_landlord": e66["retained_config_digest"],
        "E67_alphabet": e67["retained_config_digest"],
        "E68_deep_eigen": e68["retained_config_digest"],
    }
    digest_matches = {
        name: source_digests[name]
        == retained_digests[name]
        == EXPECTED_CONFIG_DIGESTS[name]
        for name in EXPECTED_CONFIG_DIGESTS
    }
    effects = e66["aggregate_effects"]

    claims = [
        {
            "claim": "Writable-fast theta raises the retained 12-fission tail fidelity from about .484 to .603",
            "verdict": "CONFIRMED_AS_REPORTED_ONLY",
            "evidence_level": "E2",
            "reason": (
                "The aggregate subtraction is +.119484 and the current config digest matches. Only the four-tissue means survive: cycles 10-12, tissue/future/group rows, dispersion, and trajectories cannot be independently recalculated."
            ),
        },
        {
            "claim": "The gain-matched control matches total restoring force without hiding the same mechanism",
            "verdict": "NOT_CONFIRMED_AS_WORDED",
            "evidence_level": "E2",
            "reason": (
                "It matches one tissue's 50-sweep sign endpoint to one cell out of 256; c_m=.2 and .3 are tied on that discrete observer, .2 is the ordinary default, grid rates are non-monotone, streams differ, and the match is not repeated after imprinting or during lineages. The stored cm_in_disguise label is an outcome inequality, not a causal ablation."
            ),
        },
        {
            "claim": "Freedom cost remains within the registered tolerance",
            "verdict": "CONFIRMED_AS_CODED",
            "evidence_level": "E2",
            "reason": (
                "Fast writable turnover is .616048 versus .658203, a -.042155 difference that passes the allowed -.05 decline by .007845. The observer is unpaired whole-sheet sign turnover after a positive quarter-sheet clamp, not equal plasticity or alternate-form adoption."
            ),
        },
        {
            "claim": "Theta transplants prove lineage-specific form content at margins around .11-.15",
            "verdict": "NOT_CONFIRMED_AS_PROOF",
            "evidence_level": "E2",
            "reason": (
                "The stored fast/slow margins are .105469/.144531, but only two donors from tissue 0 feed two recipients each under different A/B streams. Frozen and gain-matched transplants have identical theta and c_m=0 yet differ by .085938 solely through RNG namespaces; frozen alone yields .083984, leaving fast only .021484 higher. Components and variance are absent."
            ),
        },
        {
            "claim": "Theta is inherited at fission",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "In each single-successor future, the same theta array persists while fission receives only V and R; R is exactly copied and theta resumes writing for 1,000 sweeps. There is no theta copy operation, daughter branching, copy-noise assay, reset, or no-inheritance factorial, so this establishes exact state persistence rather than measured copying fidelity."
            ),
        },
        {
            "claim": "V-to-R-to-theta is a chain of progressively slower, cleaner low-pass filters",
            "verdict": "NOT_CONFIRMED",
            "evidence_level": "E2",
            "reason": (
                "Raw coefficients give theta/R clock ratios 2 and 10, but the fast lambda is rho/2 and theta is nonlinearly tanh-transformed, mean-centred, and norm-projected. E66 measures no spectra, layerwise noise, copy error, or link ablation. E67's rho modifier changes only lambda; E68 is consistent with active rewriting but its primary fails and its unbounded arm is immediately reprojected."
            ),
        },
        {
            "claim": "The repertoire narrows from seven to five classes without collapse",
            "verdict": "CONFIRMED_AS_REPORTED_ONLY",
            "evidence_level": "E2",
            "reason": (
                "The stored one-tissue count is 7 to 5, a 28.6% loss and therefore short of the coded 50% collapse rule. It uses one A donor, eight launches, one final per launch, greedy ordering, and different RNGs; identical frozen/gain theta already yields 7 versus 8. E67's ideal-write ceiling 9 and perfect K<=7 panel rejects capacity bottleneck as the interpretation."
            ),
        },
        {
            "claim": "An acquired form becomes heritable through the E66 construction",
            "verdict": "CONFIRMED_WITH_NARROWER_WORDING",
            "evidence_level": "E2",
            "reason": (
                "After a preselected A or B launch template is externally imposed over every cell for 1,000 steps, the engineered writable-state arm has higher aggregate fixed-target tail fidelity across twelve fissions than writer-off controls. Continuous descendant rewriting, exact R persistence, unequal initial theta projection, and missing inheritance knives prevent attribution to a copied theta memory alone; the novel two-headed confirmatory shot also misses its .75 bar at .627."
            ),
        },
        {
            "claim": "The result realizes a genome and Waddington canalization",
            "verdict": "NOT_CONFIRMED_AS_LITERAL",
            "evidence_level": "E0/E1",
            "reason": (
                "Genome is a useful label for the deliberately writable slow field only by analogy. No biological chemistry, population mechanism, spontaneous writer origin, reaction norm, or genetic-assimilation endpoint is tested. Development writing a hand-designed inherited array is not itself a confirmation of Waddington's biological mechanism."
            ),
        },
    ]

    audit: dict[str, Any] = {
        "schema_version": 1,
        "law": "L20",
        "audit_kind": "outcome-known retained aggregate audit, source causal audit, and bounded E67/E68 modifier reconstruction",
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
            "law_claims_acquired_form_becomes_heritable": "ACQUIRED FORM BECOMES HERITABLE"
            in texts["LAWS.md"],
            "law_claims_each_layer_slower_and_cleaner": "each layer slower and cleaner"
            in texts["LAWS.md"],
            "law_keeps_imprint_failure_separate": "imprint gate\nstill fails at bar"
            in texts["LAWS.md"],
            "design_review_requires_three_way_swap": "three-way swap" in texts[
                "WAVE14_DESIGN_REVIEW.md"
            ],
            "v23_distinguishes_engineered_carrier_from_origin_and_necessity": "Neither result shows spontaneous carrier acquisition or universal necessity"
            in texts["PRE_PRINT_PAPER_DRAFT_V2.3.md"],
            "v23_has_separate_engineered_CA_and_Wagner_carriers": "compact CA payload and Wagner latch"
            in texts["PRE_PRINT_PAPER_DRAFT_V2.3.md"],
        },
        "native_theta_input_reconstruction": {
            "rows": theta_rows,
            "all_writable_projection_scale_factors_at_least_one": all(
                float(row["writable_projection_scale_factor"]) >= 1.0
                for row in theta_rows
            ),
            "three_of_four_scale_factors_exceed_1_4": sum(
                float(row["writable_projection_scale_factor"]) > 1.4
                for row in theta_rows
            )
            == 3,
            "this_is_a_static_seed_input_reconstruction": True,
            "simulator_trajectory_run": False,
        },
        "E66_writable_landlord": e66,
        "E67_limited_modifiers": e67,
        "E68_limited_modifier": e68,
        "manuscript_v2_3_boundary": {
            "separate_CA_and_Wagner_carriers_are_E66_replications": False,
            "contextual_support": "engineered writable/transmitted/read/renewed carriers can be sufficient in other reconstructed systems",
            "explicit_manuscript_limit": "neither spontaneous carrier acquisition nor universal necessity follows",
            "evidence_use_for_L20": "scope discipline and broad engineered-sufficiency context only",
        },
        "claim_assessment": claims,
        "strongest_supported_wording": (
            "In the E66 engineered 16x16 sheet, externally imposing one of two preselected launch templates over the full body for 1,000 updates while theta continuously writes from R produces a retained aggregate cycles-10-to-12 fixed-target fidelity of .603, versus .484 with writing off in the selected scalar control, across twelve fission/regrowth steps. The same per-future theta state persists exactly in each single-successor loop, and the registered turnover proxy remains within its allowed .05 decline. This demonstrates a bounded writable-state persistence construction. It does not independently establish equal total restoring force, robust lineage-specific transplant content, theta copying rather than continuous rewriting and R carryover, progressively cleaner cascade layers, stable repertoire narrowing, a general acquired-character law, biological genome identity, or Waddington canalization."
        ),
        "closer_pass_target": (
            "After L24's first pass, freeze a common-random-number, tissue-powered writer-by-boundary factorial with identical projected initialization; writer on only during acquisition versus only in descendants; theta persist/reset/noisy-copy branches; R inherit/reset branches; direct V-to-theta and R-link ablations; spectral noise inputs; all donor thetas paired on identical recipients across tissues; retained component rows; a no-zap freedom counterfactual and alternate-target adoption; repeated repertoire panels; and both native-menu and genuinely novel targets."
        ),
    }
    frozen_hashes = {path: sha256_file(path) for path in tracker.paths}
    audit["input_file_count"] = len(frozen_hashes)
    return (
        audit,
        sorted(tracker.paths),
        metric_rows,
        list(theta_rows),
        modifier_rows,
        frozen_hashes,
    )


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return buffer.getvalue()


METRIC_FIELDS = (
    "section",
    "metric",
    "arm_or_condition",
    "value",
    "comparison_or_note",
    "evidence",
)
THETA_FIELDS = (
    "tissue",
    "well_asym",
    "configured_threshold_spread",
    "native_theta_sample_mean",
    "native_theta_sample_std",
    "writable_initial_theta_sample_mean",
    "writable_initial_theta_sample_std",
    "writable_projection_scale_factor",
)
MODIFIER_FIELDS = (
    "experiment",
    "modifier",
    "condition",
    "reported_value",
    "literal_interpretation",
    "admissible_use",
)


def metric_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, METRIC_FIELDS)


def native_theta_inputs_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, THETA_FIELDS)


def modifier_ledger_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    return _csv(rows, MODIFIER_FIELDS)


def _fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def markdown_report(audit: Mapping[str, Any]) -> str:
    e66 = audit["E66_writable_landlord"]
    e67 = audit["E67_limited_modifiers"]
    e68 = audit["E68_limited_modifier"]
    gates = e66["aggregate_summary"]
    effects = e66["aggregate_effects"]
    gain = e66["gain_match_audit"]
    lines = [
        "# L20 retained self-written-genome audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`  ",
        f"**Work state:** `{audit['work_state']}`  ",
        "**Run type:** outcome-known retained/source audit; zero simulator replays and zero new scientific futures.",
        "",
        "## Plain-language result",
        "",
        "The compact positive survives, but the grand mechanism does not. In this engineered sheet, a continuously writable theta state accompanies better descendant target retention: the stored aggregate is .603 versus .484 after a full-body imposed target and twelve fissions. That is a real model construction at aggregate resolution. It is not yet evidence that a genome was copied, that the three layers progressively cleaned noise, or that Waddington canalization was realized.",
        "",
        "The strongest causal weaknesses are concrete. Writable and control arms start with differently scaled theta, use different random streams, and never turn inheritance and continued rewriting on and off separately. The gain match is a single early endpoint. The transplant's negative controls reveal seed noise almost as large as the headline margin. The repertoire count is one small stochastic panel. E67's claimed rho robustness changes theta lambda but not R's rho, and E68's later primary fails while its supposedly unbounded arm is reprojected on the first write step.",
        "",
        "## E66 retained numbers",
        "",
        "| Quantity | Value | Boundary |",
        "|---|---:|---:|",
        f"| Writable-fast tail fidelity | {_fmt(gates['fidelity']['writable_fast'])} | — |",
        f"| Gain-matched tail fidelity | {_fmt(gates['fidelity']['gain_matched'])} | — |",
        f"| Fast−gain fidelity | {_fmt(effects['writable_fast_minus_gain_matched_fidelity'])} | unretained 1.645× frozen spread |",
        f"| Writable-slow tail fidelity | {_fmt(gates['fidelity']['writable_slow'])} | — |",
        f"| Fast−slow fidelity | {_fmt(effects['writable_fast_minus_writable_slow_fidelity'])} | — |",
        f"| Fast−gain freedom | {_fmt(effects['writable_fast_minus_gain_matched_freedom'])} | ≥ −.050 |",
        f"| Freedom slack | {_fmt(effects['freedom_clause_slack'])} | — |",
        f"| Fast transplant margin | {_fmt(effects['fast_absolute_transplant_margin'])} | > .100 |",
        f"| Frozen transplant margin | {_fmt(effects['frozen_absolute_transplant_margin'])} | expected null contrast 0 |",
        f"| Fast−frozen transplant | {_fmt(effects['fast_minus_frozen_transplant_margin'])} | not gated |",
        f"| Two-headed imprint | {_fmt(gates['imprint_shot_fidelity'])} | ≥ .750 |",
        "",
        "Only `landlord_summary.json` remains. The source averaged cycles 10–12, over cells assigned to the reset half at least twice, across six futures in four tissue configurations. No tissue, future, target-group, cycle, transplant-component, or repertoire-class rows survive. The primary's fidelity clause uses the missing across-tissue frozen spread, so its stored true Boolean cannot be independently reconstructed.",
        "",
        "## What is acquired and what crosses a boundary",
        "",
        "A and B are preselected source recipes: horizontal halves and vertical stripes. Before lineage cycling, every cell is externally overwritten to the target's ±1.2 value for 1,000 updates. The intervention is therefore a strong full-body instruction, not spontaneous morphology. It is applied once before the fission series, which makes the subsequent fixed-target advantage scientifically interesting.",
        "",
        "At fission, half of V is kept, half is reset with jitter, and all of R is copied exactly. Theta is not passed to the fission function at all: the same per-future array simply remains in the one-successor Python loop and then continues writing for 1,000 updates. Across a main run it receives 13,120 update opportunities before `theta_final`. This implements exact state persistence, but it does not measure parent-to-daughter copying, branching, copy fidelity, or whether inherited theta rather than inherited R plus continued rewriting is required.",
        "",
        "Initialization is also unequal. The controls retain native theta, whose reconstructed sample standard deviations are .191, .296, .205, and .188 in tissues 0–3. Writable arms immediately centre and rescale each to .300—scale factors 1.57, 1.01, 1.46, and 1.59. Three of four writable tissues therefore start with at least 40% stronger quenched texture before acquisition begins.",
        "",
        "## Gain matching and freedom",
        "",
        f"The writable pullback endpoint corresponds to {gain['writable_implied_net_recovered_signs']} net recovered signs out of 256. Both c_m=.2 (150) and c_m=.3 (152) are one sign away; the source selects .2, the first discrete tie and the ordinary blueprint default. The configured eight-sweep pullback zap is unused—the assay performs one instantaneous sign inversion—and the c_m rates are non-monotone. Arms use different streams. This is a close match on one local 50-sweep sign observer, not a match of total restoring force during target writing and twelve lineages.",
        "",
        "`cm_in_disguise=False` adds no mechanistic test: its source formula labels a particular fidelity inequality after the same comparison. It does not ablate theta's spatial content, match time-varying force, or show that a scalar c_m control spans the writable field's causal action.",
        "",
        f"The registered freedom clause does pass: the decline is {_fmt(effects['writable_fast_minus_gain_matched_freedom'])}, consuming {_fmt(100 * effects['fraction_of_allowed_freedom_decline_used'], 1)}% of the allowed .05. But the assay positively clamps one quarter for eight updates and then scores sign turnover over the entire sheet 300 updates later, with no no-zap counterfactual and no specified alternate target. Values above .6 therefore combine perturbation response, propagation, and ordinary drift; they are not direct estimates of equivalent reprogrammability.",
        "",
        "## Transplant and repertoire",
        "",
        f"The fast margin {_fmt(effects['fast_absolute_transplant_margin'])} clears .1 by only {_fmt(effects['fast_margin_above_absolute_0_1_gate'])}. It exceeds frozen by {_fmt(effects['fast_minus_frozen_transplant_margin'])}. Only future 0 and future 5 from tissue 0 donate, each to two fresh recipients, and the two donor groups use different streams. Frozen and gain-matched donor theta are literally the same native field and transplant sets c_m=0 in both, yet their stored margins differ by {_fmt(effects['frozen_minus_gain_matched_transplant_margin'])} solely because their RNG namespaces differ. Under identical recipient streams their symmetric margin difference would be exactly zero. This retained probe is compatible with target-specific content but does not prove it.",
        "",
        f"The fast repertoire count is {gates['repertoire']['writable_fast']['native_classes']}→{gates['repertoire']['writable_fast']['written_classes']}, a {_fmt(100 * effects['fast_repertoire_loss_fraction'], 1)}% decrease, so the coded ≥50% collapse condition is false. It comes from one tissue, one A donor, eight ordered launches, two futures per launch but only future 0 retained, a greedy >.8 class rule, and different native/written streams. Identical frozen and gain-matched theta already gives written counts 7 and 8 under different streams. E67 later finds an ideal-write ceiling of {e67['capacity_modifier']['ceiling_from_ten_launches']} and reports perfect K-way choices through K=7, so capacity bottleneck is not a defensible explanation of this one 7→5 count.",
        "",
        "## The cascade and later modifiers",
        "",
        "E66's coefficient ordering is real: R uses rho=.002 (raw reciprocal clock 500), while fast and slow theta use .001 and .0002 (1,000 and 5,000). The fast layer is only 2× slower, and its fidelity is .0033 higher than the 10×-slower arm. Theta is not a simple linear filter: every update applies tanh, global centring, and fixed-standard-deviation projection. No spectra, layerwise noise variances, signal/noise ratios, copy-error trajectories, direct writer, or cascade-link ablations were measured. `each layer slower and cleaner` therefore remains an interpretation.",
        "",
        "E67 does not supply the advertised rho replication. Its global monkey-patch changes the lambda calculated inside E66, while each new `BlueprintConfig()` keeps R at rho=.002 and every teaching/regrowth window stays at 1,000. The rows are consequently lambda=.0005 and .002 write-rate variants; at the latter, theta and R have equal raw coefficients. Gain matching is not recalibrated, arm streams differ, and the two tissue values are discarded. The retained gaps +.130 and +.093 support limited write-rate sensitivity, not robustness to rho.",
        "",
        f"E68's 48 tissue rows reconstruct its stored summary, including projected c*={_fmt(e68['reconstructed']['c_star_projected'])}, but its registered primary is false because the pre-round predicts no crossing: fidelity changes are negative at every pre-round correlation even while theta correlation recovers. Its projected slopes are positive at sampled c≥.3, but the curve is non-monotone. The `unbounded` corruption skips projection only at the boundary; the next write update projects theta again, and even c=1 projected/unbounded rows use different RNGs. This is bounded evidence consistent with active theta restoration, not retrospective proof that E66's three layers passively clean noise.",
        "",
        "## Genome and canalization boundary",
        "",
        "Calling theta a proto-genome is intelligible if the word means a deliberately engineered, slowly writable state that affects phenotype and persists across modeled reproductive boundaries. It is not a literal biological identification. The simulation has no chemistry, autonomous origin of the writer/reader, population-level assimilation test, or declared reaction norm. Calling development's hard-coded write rule `Waddington canalization realized` therefore outruns the measurement.",
        "",
        "Manuscript v2.3 provides the right boundary: its separate compact-CA and Wagner carriers show that engineered writable, transmitted, read, and renewed states can be sufficient in other reconstructed systems, while explicitly withholding spontaneous acquisition and universal necessity. Those are useful contextual successes, not independent replications of E66's theta cascade.",
        "",
        "## Clause adjudication",
        "",
        "| Atomic claim | Verdict | Evidence | Finding |",
        "|---|---|---:|---|",
    ]
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
            "L21 is next for the first pass; the fresh E66 factorial remains deferred until L24 is complete.",
            "",
        ]
    )
    return "\n".join(lines)
