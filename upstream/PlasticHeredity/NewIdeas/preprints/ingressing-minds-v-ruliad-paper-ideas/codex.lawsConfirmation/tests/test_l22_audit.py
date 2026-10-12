from pathlib import Path

import pytest

from laws_confirmation.l22_audit import (
    CURVE_FIELDS,
    HIERARCHY_FIELDS,
    TISSUE_FIELDS,
    EXPECTED_CONFIG_DIGESTS,
    curve_ledger_csv,
    hierarchy_currency_csv,
    markdown_report,
    run_l22_audit,
    source_config_digests,
    tissue_trajectory_csv,
    trend_slope,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l22_result():
    return run_l22_audit(PLASTIC_ROOT, WORKSPACE)


def test_l22_source_config_digests_match_retained_contract() -> None:
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l22_source_trend_contract() -> None:
    assert trend_slope([None] + [0.7] * 11) == pytest.approx(0.0, abs=1e-12)
    decay = [None] + [0.5 + 0.2 * 0.7**index for index in range(1, 12)]
    assert trend_slope(decay) < -0.1


def test_l22_reconstructs_complete_e68_archive_and_summary(l22_result) -> None:
    audit, _paths, curve_rows, tissue_rows, _hierarchy, _frozen = l22_result
    e68 = audit["E68_deep_eigen"]
    assert e68["all_work_digests_match_summary"] is True
    assert e68["all_16_conditions_complete"] is True
    assert e68["retained_tissue_rows"] == 48
    assert len(curve_rows) == 16
    assert len(tissue_rows) == 48
    assert e68["all_reported_gates_reconstruct"] is True
    assert e68["reconstructed_gates"]["gate_p68_1_primary"] is False
    assert e68["reconstructed_gates"]["predicted_c_star"] is None


def test_l22_reconstructs_first_crossings_but_finds_unbounded_reversals(
    l22_result,
) -> None:
    e68 = l22_result[0]["E68_deep_eigen"]
    gate = e68["reconstructed_gates"]
    assert gate["c_star_projected"] == pytest.approx(0.2421966730451237)
    assert gate["c_star_unbounded"] == pytest.approx(0.216345196881116)
    assert gate["cap_sets_threshold"] is False
    projected = e68["source_crossings"]["projected"]
    unbounded = e68["source_crossings"]["unbounded"]
    assert projected["single_threshold_shape"] is True
    assert projected["upward"][0]["bracket"] == pytest.approx([0.1, 0.3])
    assert len(unbounded["upward"]) == 2
    assert len(unbounded["downward"]) == 2
    assert unbounded["single_threshold_shape"] is False
    assert unbounded["signs_ascending_c"] == [-1, 1, 1, 1, -1, 1, -1, -1]


def test_l22_threshold_changes_with_window_and_floor(l22_result) -> None:
    e68 = l22_result[0]["E68_deep_eigen"]
    trends = e68["trend_sensitivity"]["projected"]
    assert trends["drop_first"]["crossings"]["first_upward"] == pytest.approx(
        0.283562110995022
    )
    assert len(trends["drop_first"]["crossings"]["upward"]) == 2
    assert trends["late_six"]["crossings"]["first_upward"] == pytest.approx(
        0.4482248511447761
    )
    assert trends["late_six"]["crossings"]["single_threshold_shape"] is False
    c03 = e68["condition_details"]["projected"]["0.3"]
    assert c03["source_log_excess_slope"] == pytest.approx(0.20943334715204645)
    assert c03["late_six_log_excess_slope"] == pytest.approx(
        -0.06713443767641632
    )
    floors = e68["log_floor_sensitivity"]["projected"]
    assert floors["1e-06"]["first_upward"] == pytest.approx(0.2226061055778465)
    assert floors["0.05"]["first_upward"] == pytest.approx(0.30175354430527823)


def test_l22_tissue_diagnostics_do_not_show_clean_threshold(l22_result) -> None:
    e68 = l22_result[0]["E68_deep_eigen"]
    assert sum(
        row["crossings"]["single_threshold_shape"]
        for row in e68["tissue_thresholds"]["projected"]
    ) == 0
    projected = e68["exact_tissue_block_bootstrap"]["projected"]
    assert projected["resamples"] == projected["finite_first_crossings"] == 27
    assert projected["exactly_one_upward_crossing"] == 19
    assert projected["multiple_upward_crossings"] == 8
    assert projected["conditional_first_crossing_range"] == pytest.approx(
        [0.19379776863195453, 0.3133391454923261]
    )
    unbounded = e68["exact_tissue_block_bootstrap"]["unbounded"]
    assert unbounded["exactly_one_upward_crossing"] == 8
    assert unbounded["multiple_upward_crossings"] == 19
    assert unbounded["any_downward_crossing"] == 27


def test_l22_projection_labels_are_not_an_intervention_contrast(l22_result) -> None:
    e68 = l22_result[0]["E68_deep_eigen"]
    identity = e68["projection_identity_diagnostic"]
    mechanism = e68["source_and_mechanism_audit"]
    assert identity["identity_within_1e_12"] is True
    assert identity["max_abs_difference"] < 1e-12
    assert mechanism["projected_and_unbounded_share_streams"] is False
    assert mechanism["project_flag_enters_seed_before_preparation"] is True
    assert mechanism[
        "mixture_rescaled_to_parent_norm_before_optional_projection"
    ] is True
    assert mechanism["unbounded_at_corruption_instant"] is False
    assert mechanism["unbounded_remains_unprojected_during_recovery"] is False
    assert mechanism["genuinely_unbounded_arm_present"] is False
    assert mechanism["both_labels_project_on_first_recovery_step"] is True
    assert mechanism["c1_mix_theta_called"] is False
    assert mechanism["c1_labels_have_same_physical_intervention"] is True
    assert mechanism["c1_projected_source_slope"] == pytest.approx(
        0.2787239109569312
    )
    assert mechanism["c1_unbounded_source_slope"] == pytest.approx(
        -0.07119566686514804
    )
    assert mechanism["c1_labels_have_opposite_slope_signs"] is True
    assert e68["trend_sensitivity"]["pooled_noop_labels"]["source"][
        "crossings"
    ]["single_threshold_shape"] is False


def test_l22_limits_restoration_to_programmed_rewrite(l22_result) -> None:
    e68 = l22_result[0]["E68_deep_eigen"]
    pre = e68["preround_audit"]
    mechanism = e68["source_and_mechanism_audit"]
    assert pre["all_fidelity_deltas_negative"] is True
    assert pre["all_theta_recoveries_positive"] is True
    assert pre["contains_fission"] is False
    assert pre["supports_beneficial_phenotype_correction"] is False
    assert pre["supports_programmed_theta_restoration"] is True
    assert mechanism["R_copied_whole_without_noise_at_fission"] is True
    assert mechanism["theta_updated_toward_tanh_R_each_recovery_sweep"] is True
    assert mechanism["writer_off_arm_present"] is False
    assert mechanism["R_reset_or_scramble_arm_present"] is False
    assert mechanism["V_or_context_scramble_arm_present"] is False
    assert mechanism["R_to_theta_link_ablation_present"] is False
    assert mechanism["score_mask_expands_with_cycle"] is True
    assert mechanism["per_cycle_mask_counts_retained"] is False
    assert mechanism["bootstrap_used_by_pipeline"] is False
    assert mechanism["reported_threshold_CI_present"] is False
    assert mechanism["cycle_13_or_extension_retained"] is False


def test_l22_reconstructs_E67_but_keeps_it_bounded(l22_result) -> None:
    e67 = l22_result[0]["E67_follower_modifier"]
    assert e67["cache_and_summary_digests_match"] is True
    assert e67["reported_discreteness_reconstructs"] is True
    assert e67["mean_start_dependence"] == pytest.approx(1.959162180269724)
    assert e67["store_bistable"] is False
    assert e67["tissues"] == 1
    assert e67["fission_present"] is False
    assert e67["theta_corruption_present"] is False
    assert e67["start_labels_share_random_streams"] is False
    assert e67["identifies_error_correction"] is False
    assert e67["establishes_E68_threshold"] is False


def test_l22_rejects_claimed_common_currency(l22_result) -> None:
    audit = l22_result[0]
    e55 = audit["E55_V_claim_comparator"]
    e65 = audit["E65_culture_claim_comparator"]
    assert e55["all_shards_match_summary"] is True
    assert e55["complete_tissue_complexity_grid"] is True
    assert e55["exact_R_copy_all_complexity_fixed_ancestor_tail"] == pytest.approx(
        0.49375180844907407
    )
    assert e55["exact_R_copy_all_complexity_immediate_parent_tail"] == pytest.approx(
        0.9412434895833333
    )
    assert e55["V_copy_correlation_swept"] is False
    assert e55["no_V_channel_at_any_fidelity_supported"] is False
    assert e65["all_shards_match_summary"] is True
    assert e65["selected_summary_values_reconstruct"] is True
    assert e65["parent_chain_T200"] == pytest.approx(0.5072835286458333)
    assert e65["parent_T200_minus_source_floor_q95"] > 0
    assert e65["barcode_target_shape"] == [16]
    assert e65["barcode_reported_positions"] == 256
    assert e65["barcode_intended_positions"] == 16
    assert e65["barcode_erasure_admissible"] is False
    assert e65["culture_erased_at_perfect_transmission_supported"] is False
    assert audit["hierarchy_is_one_currency"] is False
    assert all(
        row["common_currency_with_E68"] is (row["experiment"] == "E68")
        for row in audit["hierarchy_currency_table"]
    )


def test_l22_emits_ledgers_report_and_mixed_verdict(l22_result) -> None:
    audit, paths, curve_rows, tissue_rows, hierarchy_rows, frozen = l22_result
    assert audit["all_source_config_digests_match"] is True
    assert audit["overall_verdict"] == "MIXED"
    assert audit["work_state"] == "RECALCULATED"
    assert len(audit["claim_assessment"]) == 7
    assert len(paths) == len(frozen) >= 150
    assert curve_ledger_csv(curve_rows).splitlines()[0].split(",") == list(
        CURVE_FIELDS
    )
    assert tissue_trajectory_csv(tissue_rows).splitlines()[0].split(",") == list(
        TISSUE_FIELDS
    )
    assert hierarchy_currency_csv(hierarchy_rows).splitlines()[0].split(",") == list(
        HIERARCHY_FIELDS
    )
    report = markdown_report(audit)
    assert "The `.242` number is reproducible" in report
    assert "projection comparison is a no-op" in report
    assert "Restoration is not identified proofreading" in report
    assert "hierarchy is not in one currency" in report
    assert "zero simulator replays" in report
