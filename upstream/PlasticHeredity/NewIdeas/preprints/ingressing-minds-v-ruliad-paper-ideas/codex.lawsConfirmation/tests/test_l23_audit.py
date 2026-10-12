from pathlib import Path

import pytest

from laws_confirmation.l23_audit import (
    CAPACITY_FIELDS,
    CURVE_FIELDS,
    EXPECTED_CONFIG_DIGEST,
    FORM_FIELDS,
    HYSTERESIS_FIELDS,
    PAIR_FIELDS,
    capacity_ledger_csv,
    discreteness_curve_csv,
    form_ledger_csv,
    hysteresis_ledger_csv,
    markdown_report,
    pair_ledger_csv,
    run_l23_audit,
    source_config_digest,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l23_result():
    return run_l23_audit(PLASTIC_ROOT, WORKSPACE)


def test_l23_source_config_digest_matches_retained_contract() -> None:
    assert source_config_digest() == EXPECTED_CONFIG_DIGEST


def test_l23_reconstructs_all_parts_and_selected_summary(l23_result) -> None:
    audit = l23_result[0]
    assert audit["source_and_retained_config_digest_match"] is True
    assert audit["all_part_config_digests_match"] is True
    assert audit["selected_summary_reconstructs_from_part_caches"] is True
    assert audit["retention_inventory"]["result_file_count"] == 5
    assert audit["retention_inventory"]["composition_score_rows_retained"] == 0
    assert audit["retention_inventory"]["donor_shuffle_draws_retained"] == 0
    assert audit["document_checks"]["register_declares_partition_control"] is True


def test_l23_pre_screen_selects_only_two_orientations_of_one_pair(
    l23_result,
) -> None:
    audit = l23_result[0]
    pair = audit["pair_eligibility"]
    assert pair["passing_pairs"] == ["AB", "BA"]
    assert pair["passing_ordered_pairs"] == 2
    assert pair["passing_unordered_pair_count"] == 1
    assert pair["passing_unordered_pairs"] == ["AB"]
    assert pair["rejected_before_expression"] == 10
    assert pair["rejected_expression_outcomes_observed"] == 0
    assert pair["third_composite_condition_redundant_given_half_conditions"] is True
    assert pair["prospective_expectation_met"] is False
    assert pair["partition_checkerboard_control_present"] is False
    assert pair["conservation_causal_effect_identified"] is False


def test_l23_static_form_means_explain_selection(l23_result) -> None:
    audit = l23_result[0]
    forms = {row["form"]: row for row in audit["form_rows"]}
    assert forms["A"]["whole_mean"] == 0
    assert forms["B"]["whole_mean"] == 0
    assert forms["A"]["left_half_mean"] == 0
    assert forms["A"]["right_half_mean"] == 0
    assert forms["B"]["left_half_mean"] == 0
    assert forms["B"]["right_half_mean"] == 0
    assert forms["C"]["left_half_mean"] == pytest.approx(-0.203125)
    assert forms["C"]["right_half_mean"] == pytest.approx(-0.40625)
    assert forms["D"]["left_half_mean"] == pytest.approx(-0.578125)
    assert forms["D"]["right_half_mean"] == pytest.approx(-0.46875)
    assert sum(row["expression_simulated"] for row in audit["pair_eligibility"]["rows"]) == 2


def test_l23_fit_is_residual_not_interaction_but_implies_correct_decoding(
    l23_result,
) -> None:
    composition = l23_result[0]["composition"]
    primary = composition["diagnostics"]["primary"]
    secondary = composition["diagnostics"]["secondary"]
    assert primary["own_mean"] == pytest.approx(0.9140625)
    assert primary["other_mean"] == pytest.approx(0.48046875)
    assert primary["neither_mean"] == pytest.approx(0.548828125)
    assert primary["residual_ss"] == pytest.approx(0.067291259765625)
    assert primary["residual_share_of_total"] == pytest.approx(
        0.1266222579533709
    )
    assert primary["minimum_own_minus_any_nonown_row"] == pytest.approx(
        0.034555834542442376
    )
    assert secondary["minimum_own_minus_any_nonown_row"] == pytest.approx(
        0.058722690226875596
    )
    assert primary["all_four_own_rows_must_exceed_every_nonown_row"] is True
    assert secondary["all_four_own_rows_must_exceed_every_nonown_row"] is True
    assert primary["reported_gate_reconstructs_from_retained_aggregates"] is True
    assert primary["design_contains_explicit_interaction_column"] is False
    assert primary["interaction_share_is_residual_ss_over_total_ss"] is True
    assert primary["interaction_share_is_share_of_explained_variance"] is False
    assert primary["null_share_q05_used_in_gate"] is False
    assert primary["raw_rows_available_for_independent_fit"] is False
    assert composition["general_four_form_composition_supported"] is False


def test_l23_capacity_is_bounded_batch_discrimination_not_a_ceiling(
    l23_result,
) -> None:
    capacity = l23_result[0]["capacity"]
    assert capacity["reported_ceiling"] == 9
    assert capacity["candidate_starts"] == 10
    assert capacity["candidate_future_indices_used_for_repertoire"] == [0]
    assert capacity["reported_ceiling_is_empirical_upper_bound"] is False
    assert capacity["all_reported_kway_accuracies_one"] is True
    assert capacity["largest_tested_K"] == 7
    assert capacity["all_nine_representatives_tested_together"] is False
    assert capacity["class_batch_decisions_across_K"] == 27
    assert capacity["expression_futures_averaged_before_each_argmax"] == 4
    assert capacity["per_future_predictions_retained"] == 0
    assert capacity["held_out_classes_tested"] == 0
    assert capacity["supports_engineered_seven_prototype_batch_discrimination"] is True
    assert capacity["supports_capacity_of_at_least_nine_written_classes"] is False


def test_l23_within_channel_curve_does_not_identify_no_interference(
    l23_result,
) -> None:
    capacity = l23_result[0]["capacity"]
    assert capacity["within_channel_K7_minus_K2"] == pytest.approx(
        0.010323660714285698
    )
    assert capacity["within_channel_range"] == pytest.approx(0.03949652777777768)
    assert capacity["within_channel_linear_slope_per_K"] == pytest.approx(
        0.002776892006802755
    )
    assert capacity["within_channel_monotonically_decreases"] is False
    assert capacity["band_row_sizes"]["7"] == [3, 3, 2, 2, 2, 2, 2]
    assert capacity["unequal_band_sizes_present"] is True
    assert capacity["composite_multiband_theta_reprojected"] is False
    assert capacity["matched_single_form_band_controls_present"] is False
    assert capacity["absence_of_interference_identified"] is False


def test_l23_reader_width_ties_control_and_is_resolution_limited(
    l23_result,
) -> None:
    discrete = l23_result[0]["discreteness"]
    assert discrete["transition_width_reconstructs"] is True
    assert discrete["reported_transition_width"] == 0
    assert discrete["control_width"] == 0
    assert discrete["reader_width_strictly_beats_control"] is False
    assert discrete["reader_and_control_width_tie"] is True
    assert discrete["interior_grid_point_count"] == 1
    assert discrete["interior_alphas"] == [0.6]
    assert discrete["zero_width_is_single_point_resolution_artifact"] is True
    assert discrete["m_strictly_decreases_on_grid"] is True
    assert len(discrete["sign_crossings"]) == 1
    crossing = discrete["sign_crossings"][0]
    assert crossing["alpha"] == pytest.approx(0.6422330097087379)
    assert crossing["input_corr_A"] == pytest.approx(0.4867975841125721)
    assert crossing["local_corr_grid_spacing"] == pytest.approx(
        0.1607808976460614
    )
    assert discrete["theta_A_B_correlation"] == pytest.approx(0.0, abs=1e-12)
    assert discrete["input_coordinate_exact_for_tested_A_B_pair"] is True


def test_l23_start_dependence_is_not_a_hysteresis_loop(l23_result) -> None:
    discrete = l23_result[0]["discreteness"]
    assert discrete["mean_start_dependence_reconstructed"] == pytest.approx(
        1.959162180269724
    )
    assert discrete["store_bistable_reconstructed"] is False
    assert discrete["store_bistable_reported"] is False
    assert discrete["fresh_endpoint_strictly_decreases"] is True
    assert discrete["forward_reverse_alpha_continuation_loop_present"] is False
    assert discrete["independent_run_per_alpha_and_start"] is True
    assert discrete["theta_V_and_R_coevolve_during_assay"] is True
    assert discrete["supports_theta_endpoint_dependence_on_initial_V_R"] is True
    assert discrete["proves_analog_storage"] is False
    assert discrete["localizes_all_discreteness_to_reader"] is False


def test_l23_emits_ledgers_report_and_mixed_verdict(l23_result) -> None:
    audit, paths, form_rows, pair_rows, capacity_rows, curve_rows, hyst_rows, frozen = (
        l23_result
    )
    assert audit["overall_verdict"] == "MIXED"
    assert audit["work_state"] == "RECALCULATED"
    assert len(audit["claim_assessment"]) == 7
    assert len(paths) == len(frozen) >= 90
    assert form_ledger_csv(form_rows).splitlines()[0].split(",") == list(FORM_FIELDS)
    assert pair_ledger_csv(pair_rows).splitlines()[0].split(",") == list(PAIR_FIELDS)
    assert capacity_ledger_csv(capacity_rows).splitlines()[0].split(",") == list(
        CAPACITY_FIELDS
    )
    assert discreteness_curve_csv(curve_rows).splitlines()[0].split(",") == list(
        CURVE_FIELDS
    )
    assert hysteresis_ledger_csv(hyst_rows).splitlines()[0].split(",") == list(
        HYSTERESIS_FIELDS
    )
    report = markdown_report(audit)
    assert "The narrow two-composite result survives" in report
    assert "only `AB` and `BA`" in report
    assert "regression has no interaction term" in report
    assert "Nine is a greedy repertoire count" in report
    assert "reader and control widths are tied at zero" in report
    assert "zero simulator replays" in report
