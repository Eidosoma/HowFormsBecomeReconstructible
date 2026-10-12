from pathlib import Path

import pytest

from laws_confirmation.l18_audit import (
    E57_FIELDS,
    EXPECTED_CONFIG_DIGESTS,
    KNIFE_FIELDS,
    SCHEDULE_FIELDS,
    e56_knife_rows_csv,
    e56_schedule_rows_csv,
    e57_regime_repeats_csv,
    markdown_report,
    run_l18_audit,
    source_config_digests,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l18_result():
    return run_l18_audit(PLASTIC_ROOT, WORKSPACE)


def test_l18_source_config_digests_match_retained_contract() -> None:
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l18_reconstructs_knife_bracket_without_promoting_midpoint(
    l18_result,
) -> None:
    audit = l18_result[0]
    e56 = audit["E56_scaffold"]
    knife = e56["knife_crossover"]
    assert e56["all_reported_gates_and_summaries_match"] is True
    assert knife["crossing_bracket"] == [0.75, 1.0]
    assert knife["source_reported_midpoint"] == pytest.approx(0.875)
    assert knife["source_value_is_tested_fraction"] is False
    assert knife["aggregate_linear_interpolation_root"] == pytest.approx(
        0.8821596244131455
    )
    assert [row["linear_root"] for row in knife["tissue_linear_roots"]] == pytest.approx(
        [0.8728991596638656, 0.8896434634974533]
    )
    assert knife["bracket_left_directions"] == {
        "positive": 2,
        "tied": 0,
        "negative": 0,
    }
    assert knife["bracket_right_directions"] == {
        "positive": 0,
        "tied": 0,
        "negative": 2,
    }
    assert knife["theta_curve_strictly_falls_at_every_grid_step"] is False
    assert knife["cm_curve_strictly_rises_at_every_grid_step"] is True
    assert knife["unknifed_change_fraction_1_minus_0"] == pytest.approx(
        -0.41764322916666663
    )
    assert e56["intervention_audit"]["literal_carrier_content_is_read_or_transplanted"] is False
    assert e56["intervention_audit"]["e56_contains_fission_or_lineage_inheritance"] is False


def test_l18_reconstructs_schedule_and_exposure_mismatch(l18_result) -> None:
    e56 = l18_result[0]["E56_scaffold"]
    comparisons = e56["schedule"]["comparisons"]
    primary = comparisons["1000"]
    assert primary["gradual_mean_half_life"] == 575.0
    assert primary["instant_mean_half_life"] == 725.0
    assert primary["instant_minus_gradual_half_life"]["mean_difference"] == 150.0
    assert primary["instant_minus_gradual_half_life"]["directions"] == {
        "positive": 2,
        "tied": 0,
        "negative": 0,
    }
    assert primary["gradual_strong_scaffold_coefficient_sweeps"] == 1499.5
    assert primary["instant_strong_scaffold_coefficient_sweeps"] == 2000.0
    assert primary["instant_minus_gradual_strong_exposure"] == 500.5
    assert e56["schedule"]["source_label_exposure_equalized_is_literal_dose_match"] is False
    assert e56["schedule"]["schedule_arms_use_common_random_numbers"] is False
    assert e56["schedule"]["half_life_threshold_is_run_specific_from_first_50_sweep_sample"] is True
    assert e56["schedule"]["instant_removes_scaffold_R_coexistence"] is False
    assert e56["schedule"]["supports_gradual_anneal_is_necessary"] is False
    assert e56["schedule"]["supports_total_exposure_is_all"] is False
    assert e56["clock_boundary"]["mean_over_one_over_rho"] == pytest.approx(1.15)
    assert e56["clock_boundary"]["rho_scaling_identified"] is False


def test_l18_bounds_static_assimilation_and_fixed_norm_explanation(
    l18_result,
) -> None:
    audit = l18_result[0]
    e57 = audit["E57_assimilation"]
    assimilation = e57["assimilation"]
    assert e57["all_reported_gates_and_summaries_match"] is True
    assert assimilation["static_target0_corr_gain"]["mean_difference"] == pytest.approx(
        -0.04356289519671518
    )
    assert assimilation["static_target0_corr_gain"]["directions"] == {
        "positive": 1,
        "tied": 0,
        "negative": 5,
    }
    assert assimilation["implemented_baseline_is_actual_initial_population_or_ancestor"] is False
    assert assimilation["registered_gate_passed"] is False
    assert assimilation["selection_impossibility_identified"] is False
    modifier = audit["E66_fixed_norm_modifier"]
    assert modifier["same_nominal_norm_as_E57"] is True
    assert modifier["aligned_theta_pin"] == pytest.approx(0.9736328125)
    assert modifier["shows_norm_0_3_is_absolute_amplitude_barrier"] is False


def test_l18_distinguishes_period_effect_from_downward_pull(l18_result) -> None:
    e57 = l18_result[0]["E57_assimilation"]
    regimes = e57["regime_summary"]
    enforcement = e57["enforcement"]
    assert regimes["static"]["median_final_cm"] == pytest.approx(1.218050084899351)
    assert regimes["switching_k2"]["median_final_cm"] == pytest.approx(
        0.41216887523780443
    )
    assert regimes["switching_k4"]["median_final_cm"] == pytest.approx(
        1.1791336433081754
    )
    assert enforcement["reported_static_over_k2_median_ratio"] == pytest.approx(
        2.9552209253951705
    )
    assert enforcement["k4_minus_k2_final_cm"]["directions"] == {
        "positive": 6,
        "tied": 0,
        "negative": 0,
    }
    assert enforcement["k4_minus_k2_cm_change"]["directions"] == {
        "positive": 5,
        "tied": 0,
        "negative": 1,
    }
    assert regimes["switching_k2"]["median_initial_cm"] == pytest.approx(
        0.3075018360612555
    )
    assert enforcement["k2_final_median_is_below_its_initial_median"] is False
    assert regimes["switching_k2"]["cm_change_directions"] == {
        "positive": 3,
        "tied": 0,
        "negative": 3,
    }
    assert enforcement["registered_source_switching_summary_uses_k4"] is True
    assert enforcement["substituted_k2_gate"]["all_components_pass"] is False
    assert enforcement["continuous_switch_period_threshold_identified"] is False


def test_l18_corrects_readoption_regime_and_gate_semantics(l18_result) -> None:
    e57 = l18_result[0]["E57_assimilation"]
    readoption = e57["readoption"]
    assert readoption["reported_value"] == pytest.approx(0.7431640625)
    assert readoption["reported_value_matches_k4"] is True
    assert readoption["reported_value_matches_k2"] is False
    assert readoption["regime_means"]["switching_k2"] == pytest.approx(0.7041015625)
    assert readoption["regime_means"]["static"] == pytest.approx(0.7431640625)
    assert readoption["static_mean_equals_k4_mean"] is True
    assert readoption["all_k2_repeats_above_0_5"] is True
    assert readoption["k2_minus_static"]["mean_difference"] == pytest.approx(-0.0390625)
    assert readoption["k2_minus_static"]["directions"] == {
        "positive": 3,
        "tied": 0,
        "negative": 3,
    }
    assert readoption["selection_specific_preservation_identified"] is False
    p57_3 = e57["P57_3_semantics"]
    assert p57_3["implemented_switching_regime"] == "switching_k4"
    assert p57_3["implemented_gate_passed"] is True
    assert p57_3["static_also_has_cm_lethality_gt_theta_lethality"] is True
    assert p57_3["registered_theta_correlation_clause_implemented_in_gate"] is False
    assert p57_3["registered_arm_by_knife_interaction_implemented_in_gate"] is False


def test_l18_emits_complete_tables_and_mixed_verdict(l18_result) -> None:
    audit, paths, knife_rows, schedule_rows, e57_rows, frozen = l18_result
    assert audit["all_source_config_digests_match"] is True
    assert audit["overall_verdict"] == "MIXED"
    assert len(audit["claim_assessment"]) == 11
    assert len(knife_rows) == 10
    assert len(schedule_rows) == 20
    assert len(e57_rows) == 24
    assert len(paths) == len(frozen) >= 80
    knife_lines = e56_knife_rows_csv(knife_rows).splitlines()
    schedule_lines = e56_schedule_rows_csv(schedule_rows).splitlines()
    e57_lines = e57_regime_repeats_csv(e57_rows).splitlines()
    assert knife_lines[0].split(",") == list(KNIFE_FIELDS)
    assert schedule_lines[0].split(",") == list(SCHEDULE_FIELDS)
    assert e57_lines[0].split(",") == list(E57_FIELDS)
    assert len(knife_lines) == 11
    assert len(schedule_lines) == 21
    assert len(e57_lines) == 25
    report = markdown_report(audit)
    assert "midpoint of that sign-change bracket" in report
    assert "belongs to switching-k4, not k2" in report
    assert "zero simulator replays" in report
