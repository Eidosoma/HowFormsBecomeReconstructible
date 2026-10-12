from pathlib import Path

import pytest

from laws_confirmation.l24_audit import (
    CLOCK_FIELDS,
    EVOLUTION_FIELDS,
    EXPECTED_CONFIG_DIGEST,
    PAIRED_FIELDS,
    PREROUND_FIELDS,
    TRAJECTORY_FIELDS,
    clock_ledger_csv,
    evolution_ledger_csv,
    markdown_report,
    paired_ledger_csv,
    preround_ledger_csv,
    run_l24_audit,
    source_config_digest,
    trajectory_ledger_csv,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l24_result():
    return run_l24_audit(PLASTIC_ROOT, WORKSPACE)


def test_l24_source_config_digest_matches_retained_contract() -> None:
    assert source_config_digest() == EXPECTED_CONFIG_DIGEST


def test_l24_reconstructs_complete_shards_and_selected_summary(l24_result) -> None:
    audit = l24_result[0]
    integrity = audit["shard_integrity"]
    assert audit["source_summary_preround_and_shard_digests_match"] is True
    assert audit["selected_summary_reconstructs_from_preround_and_shards"] is True
    assert integrity["n_shards"] == 10
    assert integrity["shard_ids"] == list(range(10))
    assert integrity["entries"] == integrity["unique_entries"] == 20
    assert integrity["entries_per_shard"] == [2] * 10
    assert integrity["elapsed_seconds_sum"] == pytest.approx(4863.319568872452)
    assert integrity["elapsed_seconds_max"] == pytest.approx(657.4691615104675)


def test_l24_literal_void_arithmetic_survives_but_was_not_enforced(
    l24_result,
) -> None:
    audit = l24_result[0]
    pre = audit["preround"]
    source = audit["source_checks"]
    assert pre["sealed_advantage"] == pytest.approx(0.04427083333333326)
    assert pre["s_min"] == pytest.approx(1 / 12)
    assert pre["advantage_minus_s_min"] == pytest.approx(-0.0390625)
    assert pre["literal_registered_void_inequality_met"] is True
    assert pre["advantage_below_registered_one_over_population_too"] is True
    assert pre["expected_range_upper_below_s_min"] is True
    assert pre["one_over_N_is_power_or_minimum_detectable_effect_calculation"] is False
    assert pre["effective_population_size_estimated"] is False
    assert pre["evaluation_variance_used_in_threshold"] is False
    assert pre["tournament_selection_uses_absolute_fitness_difference"] is False
    assert source["run_gates_contains_pre_evolution_void_return"] is False
    assert source["evolution_was_computed_despite_failed_preround"] is True
    assert audit["document_checks"]["register_says_void_before_compute"] is True
    assert audit["document_checks"]["closeout_says_implementation_ran_anyway"] is True


def test_l24_preround_is_eight_cycle_aggregate_not_one_generation(
    l24_result,
) -> None:
    pre = l24_result[0]["preround"]
    assert pre["lineage_evaluations"] == 9
    assert pre["fission_cycles_per_lineage_evaluation"] == 8
    assert pre["total_fission_cycles_executed"] == 72
    assert pre["scored_cycles_per_lineage_evaluation"] == 3
    assert pre["called_one_generation_in_register_but_eight_cycles_in_code"] is True
    assert pre["raw_lineage_values_retained"] == 0
    assert pre["raw_cycle_values_retained"] == 0
    assert pre["both_sealed_and_unsealed_inherit_theta"] is True
    assert pre["explicit_germline_sequestration_varied_in_preround"] is False


def test_l24_leak_is_opposite_signed_same_life_endpoint_without_units(
    l24_result,
) -> None:
    audit = l24_result[0]
    pre = audit["preround"]
    channel = audit["channel_audit"]
    assert pre["unsealed_leak"] == pytest.approx(0.15625)
    assert pre["sealed_leak"] == pytest.approx(0.16840277777777776)
    assert pre["unsealed_minus_sealed_leak"] == pytest.approx(-7 / 576)
    assert pre["fixed_leak_observation_slots_per_condition"] == 576
    assert pre["unsealed_total_agreements_reconstruct"] == 90
    assert pre["sealed_total_agreements_reconstruct"] == 97
    assert pre["sampling_uncertainty_calculable_from_retained_units"] is False
    assert pre["positive_fast_writer_leak_control_present"] is False
    assert pre["scrambled_condition_retains_leak"] is False
    assert channel["undamaged_descendant_between_zap_and_leak_score"] is False
    assert channel["leak_is_clean_inherited_damage_endpoint"] is False


def test_l24_clock_arithmetic_locates_weak_manipulation_not_mechanism(
    l24_result,
) -> None:
    audit = l24_result[0]
    clock = audit["clock"]
    rows = {row["u"]: row for row in audit["clock_rows"]}
    assert clock["zap_step_zero_based"] == 450
    assert clock["post_zap_updates_before_score_and_next_fission"] == 50
    assert clock["switch_step_min"] == 100
    assert clock["switch_step_max"] == 400
    assert clock["zap_is_always_in_late_phase"] is True
    assert rows[0.5]["lambda"] == pytest.approx(0.0005)
    assert rows[0.5]["discrete_e_folding_sweeps"] == pytest.approx(
        1999.4999583231336
    )
    assert rows[0.5]["preprojection_weight_after_50"] == pytest.approx(
        0.0246961856722111
    )
    assert rows[1.0]["preprojection_weight_after_50"] == pytest.approx(
        0.04879437180296864
    )
    assert clock["reference_R_update_weight_after_50_if_V_fixed"] == pytest.approx(
        0.09525318199596433
    )
    assert clock["weights_are_linear_preprojection_coefficients_not_causal_attribution"] is True
    assert audit["source_checks"]["zap_sweeps_configured"] is True
    assert audit["source_checks"]["zap_sweeps_consumed_by_pipeline"] is False


def test_l24_noinherit_leaves_exact_whole_R_channel(l24_result) -> None:
    audit = l24_result[0]
    source = audit["source_checks"]
    channel = audit["channel_audit"]
    assert source["R_is_copied_whole_at_fission"] is True
    assert source["R_drives_V_through_comparator"] is True
    assert source["R_is_updated_from_V"] is True
    assert source["noinherit_resets_theta_only"] is True
    assert channel["R_remains_soma_to_descendant_state_in_noinherit_arm"] is True
    assert channel["noinherit_is_complete_transmission_barrier"] is False
    assert channel["speed_by_sequestration_factorial_run"] is False


def test_l24_primary_fails_sign_drift_and_directionality(l24_result) -> None:
    audit = l24_result[0]
    selected = audit["selected_gates_reconstructed"]
    primary = audit["registered_primary_diagnostics"]
    assert selected["paired_damage_minus_clean"] == pytest.approx(
        [
            -0.10068604089212219,
            2.5763375855360744,
            -4.955727084722889,
            2.3377759148575277,
            -3.047439160503839,
        ]
    )
    assert selected["contrast"] == pytest.approx(-0.6379477571450496)
    assert primary["negative_pair_count"] == 3
    assert primary["registered_four_of_five_direction_met"] is False
    assert primary["drift_q05"] == pytest.approx(-1.1340224610994167)
    assert primary["contrast_below_registered_drift_q05"] is False
    assert primary["source_directionality_predicate_met"] is False
    assert primary["registered_complete_primary_met"] is False
    assert selected["gate_p70_1_primary"] is False
    assert audit["source_checks"]["drift_q05_is_computed"] is True
    assert audit["source_checks"]["drift_q05_is_retained_in_selected_gates"] is False
    assert audit["source_checks"]["drift_q05_is_used_in_source_primary"] is False


def test_l24_directionality_guard_does_not_measure_temporal_drop(
    l24_result,
) -> None:
    direction = l24_result[0]["directionality_audit"]
    assert direction["source_predicate_is_temporal_drop"] is False
    assert direction["damage_repeats_final_ll_less_final_le"] == 4
    assert direction["damage_repeats_final_ll_below_initial"] == 2
    assert direction["damage_repeats_final_le_below_initial"] == 0
    assert direction["damage_aggregate_final_le"] == pytest.approx(
        0.5356061944306776
    )
    assert direction["damage_aggregate_final_ll"] == pytest.approx(
        0.1874170931057198
    )
    assert direction["damage_aggregate_ll_temporally_drops"] is False


def test_l24_exact_paired_diagnostics_show_instability(l24_result) -> None:
    diagnostics = l24_result[0]["paired_damage_minus_clean_diagnostics"]
    assert diagnostics["median"] == pytest.approx(-0.10068604089212219)
    assert diagnostics["sample_sd"] == pytest.approx(3.3137621720848003)
    assert diagnostics["t_95_interval"] == pytest.approx(
        [-4.75252694483226, 3.4766314305421613]
    )
    assert diagnostics["exact_equal_weight_bootstrap_resamples"] == 3125
    assert diagnostics["bootstrap_quantiles"]["0.025"] == pytest.approx(
        -3.2214037062691157
    )
    assert diagnostics["bootstrap_quantiles"]["0.975"] == pytest.approx(
        1.9455081919790165
    )
    assert diagnostics["exact_sign_flip_assignments"] == 32
    assert diagnostics["sign_flip_two_sided_p_inclusive"] == pytest.approx(0.5625)
    assert diagnostics["leave_one_block_out_min"] == pytest.approx(
        -1.4415190928153305
    )
    assert diagnostics["leave_one_block_out_max"] == pytest.approx(
        0.44149707474941013
    )


def test_l24_retention_and_wave_constant_mismatch_are_explicit(l24_result) -> None:
    audit = l24_result[0]
    retention = audit["retention_inventory"]
    docs = audit["document_checks"]
    assert retention["result_file_count"] == 12
    assert retention["generation_aggregate_rows_retained"] == 320
    assert retention["individual_population_gene_rows_retained"] == 0
    assert retention["individual_ts_values_retained"] == 0
    assert retention["historical_total_life_fitness_calls"] == 2889
    assert (docs["register_population"], docs["coded_population"]) == (16, 12)
    assert (docs["register_generations"], docs["coded_generations"]) == (24, 16)
    assert (docs["register_inter_fission"], docs["coded_inter_fission"]) == (
        1000,
        500,
    )
    assert docs["frozen_wave_constants_match_code"] is False
    assert docs["formal_amendment_located"] is False


def test_l24_emits_complete_ledgers_and_not_confirmed_verdict(l24_result) -> None:
    (
        audit,
        paths,
        evolution_rows,
        paired_rows,
        trajectory_rows,
        clock_rows,
        preround_rows,
        frozen,
    ) = l24_result
    assert audit["overall_verdict"] == "NOT_CONFIRMED"
    assert audit["work_state"] == "RECALCULATED"
    assert len(audit["claim_assessment"]) == 5
    assert len(paths) == len(frozen) >= 100
    assert len(evolution_rows) == 20
    assert len(paired_rows) == 5
    assert len(trajectory_rows) == 320
    assert len(clock_rows) == 4
    assert len(preround_rows) == 3
    assert evolution_ledger_csv(evolution_rows).splitlines()[0].split(",") == list(
        EVOLUTION_FIELDS
    )
    assert paired_ledger_csv(paired_rows).splitlines()[0].split(",") == list(
        PAIRED_FIELDS
    )
    assert trajectory_ledger_csv(trajectory_rows).splitlines()[0].split(",") == list(
        TRAJECTORY_FIELDS
    )
    assert clock_ledger_csv(clock_rows).splitlines()[0].split(",") == list(
        CLOCK_FIELDS
    )
    assert preround_ledger_csv(preround_rows).splitlines()[0].split(",") == list(
        PREROUND_FIELDS
    )
    report = markdown_report(audit)
    assert "The void arithmetic survives; the law does not" in report
    assert "before the next fission" in report
    assert "R is copied whole" in report
    assert "does not fall below the registered drift 5th percentile" in report
    assert "zero simulator replays" in report
