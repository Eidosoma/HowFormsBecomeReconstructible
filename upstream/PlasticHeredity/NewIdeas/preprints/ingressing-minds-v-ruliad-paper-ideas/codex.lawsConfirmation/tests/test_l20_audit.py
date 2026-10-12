from pathlib import Path

import pytest

from laws_confirmation.l20_audit import (
    EXPECTED_CONFIG_DIGESTS,
    METRIC_FIELDS,
    MODIFIER_FIELDS,
    THETA_FIELDS,
    markdown_report,
    metric_ledger_csv,
    modifier_ledger_csv,
    native_theta_input_rows,
    native_theta_inputs_csv,
    run_l20_audit,
    source_config_digests,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l20_result():
    return run_l20_audit(PLASTIC_ROOT, WORKSPACE)


def test_l20_source_config_digests_match_retained_contract() -> None:
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l20_reconstructs_unequal_initial_theta_inputs(l20_result) -> None:
    rows = native_theta_input_rows()
    assert [row["native_theta_sample_std"] for row in rows] == pytest.approx(
        [
            0.19114875266661344,
            0.29600210972602,
            0.20501547789792549,
            0.18847799986477587,
        ]
    )
    initial = l20_result[0]["native_theta_input_reconstruction"]
    assert initial["all_writable_projection_scale_factors_at_least_one"] is True
    assert initial["three_of_four_scale_factors_exceed_1_4"] is True
    lineage = l20_result[0]["E66_writable_landlord"][
        "lineage_and_inheritance_audit"
    ]
    assert lineage["initial_theta_preprocessing_identical_across_arms"] is False
    assert lineage["theta_array_is_explicitly_copied_at_boundary"] is False
    assert lineage["theta_same_array_persists_in_single_successor_loop"] is True
    assert lineage["writer_updates_before_returned_theta_final"] == 13120
    assert lineage["fidelity_human_cycle_numbers_averaged"] == [10, 11, 12]


def test_l20_bounds_e66_fidelity_and_primary_retention(l20_result) -> None:
    e66 = l20_result[0]["E66_writable_landlord"]
    effects = e66["aggregate_effects"]
    assert effects["writable_fast_minus_gain_matched_fidelity"] == pytest.approx(
        0.11948423032407401
    )
    assert effects["writable_fast_minus_writable_slow_fidelity"] == pytest.approx(
        0.0033275462962962807
    )
    assert effects["imprint_shot_minus_registered_bar"] == pytest.approx(
        -0.12261284722222232
    )
    retained = e66["primary_and_retention_audit"]
    assert retained["reported_primary"] is True
    assert retained["full_primary_independently_reconstructable"] is False
    assert retained["retained_resolution"] == "aggregate summary only"
    assert retained["cm_in_disguise_boolean_is_mechanism_test"] is False


def test_l20_finds_discrete_gain_match_tie_and_default_cm(l20_result) -> None:
    gain = l20_result[0]["E66_writable_landlord"]["gain_match_audit"]
    assert gain["pullback_score_denominator"] == 256
    assert gain["writable_implied_net_recovered_signs"] == 151
    assert gain["equally_nearest_cm_values_on_discrete_score_lattice"] == [
        0.2,
        0.3,
    ]
    assert gain["reported_choice_is_unique_nearest"] is False
    assert gain["reported_choice_equals_default_blueprint_cm"] is True
    assert gain["c_m_grid_rate_is_monotone"] is False
    assert gain["configured_eight_sweep_zap_is_used"] is False
    assert gain["matches_total_restoring_force_over_lineage"] is False


def test_l20_confines_freedom_transplant_and_repertoire(l20_result) -> None:
    e66 = l20_result[0]["E66_writable_landlord"]
    effects = e66["aggregate_effects"]
    assert effects["writable_fast_minus_gain_matched_freedom"] == pytest.approx(
        -0.04215494791666674
    )
    assert effects["freedom_clause_slack"] == pytest.approx(
        0.007845052083333262
    )
    assert e66["freedom_audit"]["registered_proxy_passes"] is True
    assert e66["freedom_audit"]["matched_no_zap_counterfactual_present"] is False
    assert e66["freedom_audit"]["specified_alternate_target_adoption_measured"] is False

    transplant = e66["transplant_audit"]
    assert effects["fast_minus_frozen_transplant_margin"] == pytest.approx(
        0.021484375
    )
    assert transplant["frozen_gain_margin_difference_due_only_to_rng_namespace"] == pytest.approx(
        0.0859375
    )
    assert transplant["common_stream_identical_theta_symmetric_margin_would_equal"] == 0.0
    assert transplant["lineage_specific_content_proven"] is False

    repertoire = e66["repertoire_audit"]
    assert repertoire["reported_fast_native_classes"] == 7
    assert repertoire["reported_fast_written_classes"] == 5
    assert repertoire["reported_fast_collapsed"] is False
    assert repertoire["frozen_and_gain_use_identical_theta_but_report_written_counts"] == [
        7,
        8,
    ]
    assert repertoire["robust_narrowing_established"] is False


def test_l20_rejects_unmeasured_filter_cleanliness(l20_result) -> None:
    filt = l20_result[0]["E66_writable_landlord"]["timescale_and_filter_audit"]
    assert filt["theta_to_R_raw_clock_ratios"] == {"fast": 2.0, "slow": 10.0}
    assert filt["fast_lambda_is_quantitatively_much_less_than_rho"] is False
    assert filt["theta_projected_to_fixed_std_each_update"] is True
    assert filt["frequency_response_measured"] is False
    assert filt["layerwise_noise_variance_measured"] is False
    assert filt["cascade_link_ablation_present"] is False
    assert filt["each_layer_cleaner_claim_measured"] is False


def test_l20_detects_e67_rho_robustness_misimplementation(l20_result) -> None:
    e67 = l20_result[0]["E67_limited_modifiers"]
    assert e67["summary_reconstructs_from_part_caches"] is True
    assert [row["gap"] for row in e67["robustness_rows"]] == pytest.approx(
        [0.13015407986111105, 0.09315321180555552]
    )
    assert [row["actual_R_rho"] for row in e67["robustness_rows"]] == [
        0.002,
        0.002,
    ]
    assert [row["actual_lambda_over_R_rho"] for row in e67["robustness_rows"]] == pytest.approx(
        [0.25, 1.0]
    )
    source = e67["robustness_source_audit"]
    assert source["only_theta_lambda_changes_with_labelled_rho"] is True
    assert source["inter_fission_window_rescaled_with_labelled_rho"] is False
    assert source["gain_match_recalibrated_at_each_labelled_rho"] is False
    assert source["validates_rho_robustness"] is False
    assert e67["capacity_modifier"]["supports_E66_repertoire_as_capacity_bottleneck"] is False
    assert e67["follower_modifier"]["store_bistable"] is False


def test_l20_reconstructs_e68_but_does_not_upgrade_e66(l20_result) -> None:
    e68 = l20_result[0]["E68_limited_modifier"]
    assert e68["all_16_conditions_have_three_unique_tissues"] is True
    assert e68["lineage_rows"] == 48
    assert e68["all_reported_gates_reconstruct"] is True
    assert e68["reconstructed"]["c_star_projected"] == pytest.approx(
        0.2421966730451237
    )
    mechanism = e68["mechanism_modifier"]
    assert mechanism["reported_primary_passes"] is False
    assert mechanism["all_preround_fidelity_deltas_negative"] is True
    assert mechanism["all_preround_theta_recoveries_positive"] is True
    assert mechanism["preround_includes_fission"] is False
    assert mechanism["projected_curve_monotone_in_correlation"] is False
    assert mechanism["unbounded_arm_is_unbounded_throughout_recovery"] is False
    assert mechanism["c_equals_1_conditions_differ_only_by_rng_namespace"] is True
    assert mechanism["proves_each_V_R_theta_layer_is_cleaner"] is False


def test_l20_emits_ledgers_report_and_mixed_verdict(l20_result) -> None:
    audit, paths, metrics, theta_rows, modifiers, frozen = l20_result
    assert audit["all_source_config_digests_match"] is True
    assert audit["overall_verdict"] == "MIXED"
    assert audit["work_state"] == "RECALCULATED"
    assert len(audit["claim_assessment"]) == 9
    assert len(metrics) == 18
    assert len(theta_rows) == 4
    assert len(modifiers) == 5
    assert len(paths) == len(frozen) >= 65
    assert metric_ledger_csv(metrics).splitlines()[0].split(",") == list(
        METRIC_FIELDS
    )
    assert native_theta_inputs_csv(theta_rows).splitlines()[0].split(",") == list(
        THETA_FIELDS
    )
    assert modifier_ledger_csv(modifiers).splitlines()[0].split(",") == list(
        MODIFIER_FIELDS
    )
    report = markdown_report(audit)
    assert "The compact positive survives" in report
    assert "one sign away" in report
    assert "does not supply the advertised rho replication" in report
    assert "zero simulator replays" in report
