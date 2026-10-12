from pathlib import Path

import pytest

from laws_confirmation.l21_audit import (
    EXPECTED_CONFIG_DIGESTS,
    POPULATION_FIELDS,
    RACE_FIELDS,
    markdown_report,
    population_ledger_csv,
    race_ledger_csv,
    reference_ages,
    run_l21_audit,
    source_config_digests,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l21_result():
    return run_l21_audit(PLASTIC_ROOT, WORKSPACE)


def test_l21_source_config_digests_match_retained_contract() -> None:
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l21_reconstructs_complete_e69_grid_and_summary(l21_result) -> None:
    audit, _paths, population_rows, _race_rows, _frozen = l21_result
    e69 = audit["E69_ancestry_world"]
    assert e69["all_work_digests_match_summary"] is True
    assert e69["all_shards_match_source_stride"] is True
    assert e69["retained_cells"] == e69["unique_cells"] == 25
    assert e69["trajectory_records"] == 25 * 16
    assert e69["preround_cache_matches_summary"] is True
    assert e69["all_reported_gates_reconstruct"] is True
    assert len(population_rows) == 25


def test_l21_reconstructs_reported_arithmetic_dose_row(l21_result) -> None:
    regimes = l21_result[0]["E69_ancestry_world"]["regime_statistics"]
    assert regimes["recent"]["arithmetic_mean"] == pytest.approx(
        0.034313201188859624
    )
    assert regimes["depth2"]["arithmetic_mean"] == pytest.approx(
        0.05063452300496546
    )
    assert regimes["ancestry"]["arithmetic_mean"] == pytest.approx(
        0.24253424117359837
    )
    assert regimes["knife"]["arithmetic_mean"] == pytest.approx(
        0.07330908793484933
    )
    assert regimes["drift"]["arithmetic_mean"] == pytest.approx(
        0.04770836293641327
    )
    assert regimes["depth2"]["median"] < regimes["recent"]["median"]
    assert regimes["depth2"]["geometric_mean"] < regimes["recent"][
        "geometric_mean"
    ]


def test_l21_reconstructs_primary_and_uncertainty_diagnostics(l21_result) -> None:
    primary = l21_result[0]["E69_ancestry_world"]["contrasts"][
        "ancestry_minus_knife"
    ]
    assert primary["differences_by_repeat"] == pytest.approx(
        [
            0.05647924896761339,
            0.5564076906520781,
            0.040366807368237445,
            -0.04879031065999816,
            0.24166232986581423,
        ]
    )
    assert primary["mean"] == pytest.approx(0.169225153238749)
    assert primary["median"] == pytest.approx(0.05647924896761339)
    assert primary["positive"] == 4
    assert primary["exhaustive_block_bootstrap_95"] == pytest.approx(
        [0.007926448476818393, 0.3724190182324101]
    )
    assert primary["exact_sign_flip_upper_tail"] == pytest.approx(0.09375)
    assert primary["exact_sign_test_upper_tail"] == pytest.approx(0.1875)
    assert primary["approximate_t_95_interval_df4"][0] < 0
    assert primary["all_leave_one_repeat_out_means_positive"] is True
    assert primary["largest_positive_contribution_fraction_of_sum"] == pytest.approx(
        0.6575945478590619
    )
    assert l21_result[0]["E69_ancestry_world"]["reconstructed_gates"][
        "gate_p69_1_primary"
    ] is True


def test_l21_finds_founder_above_drift_in_every_block(l21_result) -> None:
    contrast = l21_result[0]["E69_ancestry_world"]["contrasts"][
        "ancestry_minus_drift"
    ]
    assert contrast["mean"] == pytest.approx(0.19482587823718506)
    assert contrast["positive"] == 5
    assert contrast["exact_sign_flip_upper_tail"] == pytest.approx(0.03125)
    assert contrast["exhaustive_block_bootstrap_95"][0] > 0


def test_l21_reconstructs_actual_reference_ages_and_rejects_depth_shape(
    l21_result,
) -> None:
    assert reference_ages(8, 1) == [1, 1, 1]
    assert reference_ages(8, 2) == [2, 1, 2]
    assert reference_ages(8, 8) == [6, 7, 8]
    depth = l21_result[0]["E69_ancestry_world"]["depth_audit"]
    assert depth["arithmetic_mean_order_recent_depth2_ancestry"] is True
    assert depth["median_order_recent_depth2_ancestry"] is False
    assert depth["geometric_mean_order_recent_depth2_ancestry"] is False
    assert depth["full_within_repeat_order_count"] == 0
    assert depth["depth2_above_recent_repeat_count"] == 1
    assert depth["ancestry_above_depth2_repeat_count"] == 4
    assert depth["missing_registered_depths"] == [4, 12]
    assert depth["restoring_force_covariate_implemented"] is False


def test_l21_confines_preround_and_generation_bookkeeping(l21_result) -> None:
    e69 = l21_result[0]["E69_ancestry_world"]
    pre = e69["preround_audit"]
    assert pre["functional_bar"] == 1.0
    assert pre["functional_bar_is_grid_top"] is True
    assert pre["functional_bar_is_gene_box_ceiling"] is True
    assert pre["positive_control_advantage"] == pytest.approx(
        0.08940972222222232
    )
    assert pre["positive_control_slack_over_s_min"] == pytest.approx(
        0.006076388888888988
    )
    assert pre["fitness_strictly_monotone_over_grid"] is False
    assert pre["u_levels_share_random_streams"] is False
    assert pre["raw_fidelity_gap_is_tournament_selection_coefficient"] is False
    assert all(
        row["final_population_means_at_or_above_functional_bar"] == 0
        for row in e69["regime_statistics"].values()
    )
    source = e69["source_and_endpoint_audit"]
    assert source["unclipped_arithmetic_offspring_multiplier"] == pytest.approx(
        1.046027859908717
    )
    assert source["reported_endpoint_completed_evolutionary_transitions"] == 15
    assert source["reported_final_mean_generation"] == 15
    assert source["reported_drift_max_generation"] == 16
    assert source["drift_mean_and_max_share_endpoint"] is False
    assert source["pairs_are_common_random_number_pairs"] is False
    assert source["pairs_are_tissue_parameter_blocks"] is True


def test_l21_limits_heritability_decomposition_and_E64_converse(l21_result) -> None:
    audit = l21_result[0]
    inheritance = audit["E69_ancestry_world"]["inheritance_audit"]
    assert inheritance[
        "posthoc_ancestry_minus_knife_fraction_of_ancestry"
    ] == pytest.approx(0.6977371624719291)
    assert inheritance[
        "posthoc_contrast_fraction_of_ancestry_excess_over_drift"
    ] == pytest.approx(0.8685968967260642)
    assert inheritance["ordinary_theta_explicitly_copied_at_fission"] is False
    assert inheritance[
        "ordinary_theta_same_array_persists_in_single_successor_loop"
    ] is True
    assert inheritance["knife_resets_theta_after_every_fission"] is True
    assert inheritance["knife_writing_resumes_for_each_regrowth_window"] is True
    assert inheritance["additive_heritable_share_identified"] is False
    converse = audit["E64_claimed_converse"]
    assert converse["target_is_immediate_pre_insult_state"] is True
    assert converse["score_always_read_at_fixed_lag"] is True
    assert converse["target_age_varies_across_injury_regimes"] is False
    assert converse["ancestor_referenced_secondary_implemented"] is False
    assert converse["can_supply_target_depth_converse"] is False


def test_l21_reconstructs_but_does_not_upgrade_E71(l21_result) -> None:
    e71 = l21_result[0]["E71_bounded_modifier"]
    assert e71["all_work_digests_match_summary"] is True
    assert e71["all_shards_match_source_stride"] is True
    assert e71["retained_rows"] == e71["unique_rows"] == 30
    assert e71["all_reported_gates_reconstruct"] is True
    primary = e71["primary_audit"]
    assert primary["reported_primary_passes"] is False
    assert primary["positive_main_slopes"] == primary["main_repeat_count"] == 8
    assert primary["main_slope_mean"] == pytest.approx(0.12539965820710847)
    assert primary["null_q95_minus_main_mean"] == pytest.approx(
        0.005307701375464491
    )
    assert primary["frozen_wave15_main_repeat_count"] == 12
    assert primary["source_computes_pooled_slope"] is False
    assert primary["registered_confidence_interval_computed"] is False
    winner = e71["functional_winner_audit"]
    assert winner["source_threshold"] == 0.01
    assert winner["E69_functional_bar"] == 1.0
    assert winner["main_means_at_or_above_E69_functional_bar"] == 0
    assert winner["source_threshold_matches_E69_functional_bar"] is False
    control = e71["control_audit"]
    assert control["churn_theta_is_explicitly_unaligned"] is False
    assert control["churn_magnitude_is_measured_and_matched"] is False
    assert control["churn_supports_alignment_not_churn_claim"] is False
    assert control["race_uses_at_least_eight_fissions"] is False


def test_l21_emits_ledgers_report_and_mixed_verdict(l21_result) -> None:
    audit, paths, population_rows, race_rows, frozen = l21_result
    assert audit["all_source_config_digests_match"] is True
    assert audit["overall_verdict"] == "MIXED"
    assert audit["work_state"] == "RECALCULATED"
    assert len(audit["claim_assessment"]) == 5
    assert len(paths) == len(frozen) >= 100
    assert len(population_rows) == 25
    assert len(race_rows) == 30
    assert population_ledger_csv(population_rows).splitlines()[0].split(",") == list(
        POPULATION_FIELDS
    )
    assert race_ledger_csv(race_rows).splitlines()[0].split(",") == list(
        RACE_FIELDS
    )
    report = markdown_report(audit)
    assert "bounded signal survives" in report
    assert "aggregate illusion" in report
    assert "E64 is not the converse" in report
    assert "remains false" in report
    assert "zero simulator replays" in report
