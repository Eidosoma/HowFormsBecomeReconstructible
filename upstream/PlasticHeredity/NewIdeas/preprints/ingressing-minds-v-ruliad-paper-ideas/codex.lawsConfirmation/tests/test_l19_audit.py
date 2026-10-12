from pathlib import Path

import pytest

from laws_confirmation.l19_audit import (
    ARCHITECTURE_FIELDS,
    CORNER_FIELDS,
    E64_FIELDS,
    E65_FIELDS,
    EXPECTED_CONFIG_DIGESTS,
    architecture_inventory_csv,
    barcode_observer_geometry,
    e64_corner_rows_csv,
    e64_regime_repeats_csv,
    e65_arm_rows_csv,
    markdown_report,
    run_l19_audit,
    source_config_digests,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l19_result():
    return run_l19_audit(PLASTIC_ROOT, WORKSPACE)


def test_l19_source_config_digests_match_retained_contract() -> None:
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l19_reconstructs_e64_and_bounds_clock_claim(l19_result) -> None:
    audit = l19_result[0]
    e64 = audit["E64_injury_clock"]
    clock = e64["clock_association"]
    assert e64["all_reported_gates_and_summaries_match"] is True
    assert e64["integrity"]["complete_regime_repeat_grid"] is True
    assert e64["integrity"]["sixteen_generations_each"] is True
    assert e64["recalculated_gates"]["gate_p64_1_primary"] is False
    assert e64["recalculated_gates"]["gate_p64_2_resonance"] is False
    assert clock["aggregate_rho_strictly_decreases_with_interval"] is True
    assert clock["three_point_log_log_slope_tau_on_interval"] == pytest.approx(
        0.7026623588073464
    )
    assert clock["interval_times_rho_values"] == pytest.approx(
        [4.835263507375837, 7.959844924608199, 7.30188929883256]
    )
    assert clock["tau_within_20_percent_of_interval_over_five"] == 1
    assert clock["fast_minus_mid_rho"]["directions"] == {
        "positive": 2,
        "tied": 0,
        "negative": 3,
    }
    assert clock["mid_minus_slow_rho"]["directions"] == {
        "positive": 4,
        "tied": 0,
        "negative": 1,
    }
    assert clock["strict_fast_gt_mid_gt_slow_repeat_count"] == 1


def test_l19_e64_does_not_vary_target_depth(l19_result) -> None:
    e64 = l19_result[0]["E64_injury_clock"]
    objective = e64["objective_audit"]
    assert objective["fitness_target"] == "each insult's immediate pre-state"
    assert objective["fitness_target_age_at_score_sweeps"] == 150
    assert objective["fitness_target_age_varied_across_injury_regimes"] is False
    assert objective["distant_ancestor_fitness_arm_implemented"] is False
    assert objective["static_selection_still_scores_150_sweep_immediate_pre_state_retention"] is True
    assert objective["selection_and_audit_semantics_match_for_static"] is False
    assert objective["mask_is_quarter_of_cells"] is False
    deviations = e64["register_implementation_deviations"]
    assert deviations["wave14_registered_repeats"] == 6
    assert deviations["implemented_repeats"] == 5
    assert deviations["ancestor_referenced_secondary_implemented"] is False
    assert deviations["quenched_swap_injury_arm_implemented"] is False


def test_l19_reconstructs_e65_broadcast_and_parent_results(l19_result) -> None:
    e65 = l19_result[0]["E65_teaching"]
    gates = e65["recalculated_gates"]
    comparisons = e65["paired_tissue_comparisons"]
    assert e65["all_reported_gates_and_summaries_match"] is True
    assert e65["integrity"]["sixty_entries"] is True
    assert gates["broadcast"]["500"] == pytest.approx(0.6885172526041666)
    assert gates["parent_chain"]["200"] == pytest.approx(0.5072835286458334)
    assert comparisons["500"]["broadcast_minus_parent"]["mean_difference"] == pytest.approx(
        0.17631022135416663
    )
    assert comparisons["500"]["broadcast_minus_parent"]["directions"] == {
        "positive": 4,
        "tied": 0,
        "negative": 0,
    }
    assert comparisons["broadcast_dose"]["500_minus_50"]["directions"] == {
        "positive": 4,
        "tied": 0,
        "negative": 0,
    }
    intervention = e65["intervention_and_null_audit"]
    assert intervention["broadcast_alone_transmitted_by_organism"] is False
    assert intervention["broadcast_withdrawal_arm_present"] is False
    assert intervention["teacher_clamps_entire_sheet_every_teaching_sweep"] is True
    assert intervention["parent_200_exceeds_source_floor_q95"] is True
    assert intervention["source_primary_fidelity_clause_passes"] is True
    assert intervention["source_primary_divergence_clause_passes"] is True
    assert intervention["source_primary_barcode_clause_passes"] is False


def test_l19_detects_e65_barcode_shape_error(l19_result) -> None:
    actual = barcode_observer_geometry(16, 16, 4)
    registered = barcode_observer_geometry(32, 32, 4)
    assert actual["boolean_extracted_target_shape"] == [16]
    assert actual["reported_comparison_shape_after_broadcast"] == [16, 16]
    assert actual["reported_positions_scored_per_lineage"] == 256
    assert actual["intended_patch_positions"] == 16
    assert registered["broadcast_compatible"] is False
    observer = l19_result[0]["E65_teaching"]["barcode_observer_audit"]
    assert observer["reported_score_is_patch_restricted"] is False
    assert observer["registered_32_by_32_shape_would_be_compatible"] is False
    assert observer["cycles_after_injection_before_only_barcode_score"] == 7
    assert observer["one_reteaching_cycle_barcode_score_retained"] is False
    assert observer["reported_values_admissible_for_patch_propagation"] is False


def test_l19_bounds_e66_aggregate_cascade_result(l19_result) -> None:
    e66 = l19_result[0]["E66_writable_landlord"]
    effects = e66["aggregate_effects"]
    clocks = e66["timescale_and_update_audit"]
    assert e66["capacity_recalculation"]["chosen_norm"] == pytest.approx(0.3)
    assert e66["gain_match_recalculation"]["matches_reported"] is True
    assert e66["gain_match_recalculation"]["absolute_rate_gap"] == pytest.approx(
        0.000078125
    )
    assert effects["writable_fast_minus_gain_matched_fidelity"] == pytest.approx(
        0.11948423032407401
    )
    assert effects["writable_fast_minus_gain_matched_freedom"] == pytest.approx(
        -0.04215494791666674
    )
    assert effects["freedom_clause_slack"] == pytest.approx(0.007845052083333262)
    assert effects["fast_minus_frozen_transplant_margin"] == pytest.approx(
        0.021484375
    )
    assert effects["fast_margin_above_absolute_0_1_gate"] == pytest.approx(
        0.00546875
    )
    assert clocks["theta_to_R_raw_clock_ratios"] == {
        "writable_fast": 2.0,
        "writable_slow": 10.0,
    }
    assert clocks["layer_cleanliness_or_copy_error_directly_measured"] is False
    assert e66["inheritance_and_control_audit"]["theta_copy_noise_or_reset_factorial_present"] is False
    assert e66["transplant_audit"]["group_A_and_group_B_use_common_recipient_random_stream"] is False
    assert e66["transplant_audit"]["robust_lineage_content_proven"] is False
    assert e66["primary_gate_retention_audit"]["full_gate_independently_reconstructable"] is False
    assert e66["retention"]["retained_resolution"] == "aggregate summary only"


def test_l19_counterexample_screen_and_architecture_boundary(l19_result) -> None:
    audit = l19_result[0]
    screen = audit["counterexample_screen"]
    universe = audit["architecture_search_space"]
    assert screen["generation_10_to_12_immediate_parent_similarity"] == pytest.approx(
        0.9412434895833333
    )
    assert screen["generation_10_to_12_fixed_ancestor_similarity"] == pytest.approx(
        0.49375169542100694
    )
    assert screen["counterexamples_broad_rolling_continuity_reading"] is True
    assert screen["counterexamples_narrow_fixed_ancestor_instance_reading"] is False
    assert screen["screen_is_exhaustive_architecture_search"] is False
    assert universe["E64_is_architecture_search"] is False
    assert universe["architecture_menu_exhaustive"] is False
    assert universe["necessity_identified"] is False
    assert universe["uniqueness_identified"] is False


def test_l19_emits_complete_tables_report_and_mixed_verdict(l19_result) -> None:
    audit, paths, e64_rows, corner_rows, e65_rows, architectures, frozen = l19_result
    assert audit["all_source_config_digests_match"] is True
    assert audit["overall_verdict"] == "MIXED"
    assert len(audit["claim_assessment"]) == 6
    assert len(e64_rows) == 25
    assert len(corner_rows) == 9
    assert len(e65_rows) == 60
    assert len(architectures) == 8
    assert len(paths) == len(frozen) >= 140
    assert e64_regime_repeats_csv(e64_rows).splitlines()[0].split(",") == list(E64_FIELDS)
    assert e64_corner_rows_csv(corner_rows).splitlines()[0].split(",") == list(CORNER_FIELDS)
    assert e65_arm_rows_csv(e65_rows).splitlines()[0].split(",") == list(E65_FIELDS)
    assert architecture_inventory_csv(architectures).splitlines()[0].split(",") == list(
        ARCHITECTURE_FIELDS
    )
    report = markdown_report(audit)
    assert "recurrence association, not target-depth law" in report
    assert "scores 256 cells" in report
    assert "zero simulator replays" in report
