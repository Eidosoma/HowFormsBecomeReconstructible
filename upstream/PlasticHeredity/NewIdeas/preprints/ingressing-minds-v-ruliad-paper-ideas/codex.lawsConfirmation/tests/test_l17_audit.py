from pathlib import Path

import pytest

from laws_confirmation.l17_audit import (
    CHANNEL_TABLE_FIELDS,
    EXPECTED_CONFIG_DIGESTS,
    channel_table_csv,
    e54_flagship_rows_csv,
    e55_channel_curves_csv,
    e55_generation_trace_csv,
    e57_transport_rows_csv,
    markdown_report,
    run_l17_audit,
    source_config_digests,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l17_result():
    return run_l17_audit(PLASTIC_ROOT, WORKSPACE)


def test_l17_source_config_digests_match_retained_contract() -> None:
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l17_reconstructs_clock_and_flagship_with_literal_interventions(
    l17_result,
) -> None:
    audit = l17_result[0]
    e56 = audit["E56_post_scaffold_clock"]
    assert [row["half_life_sweeps"] for row in e56["primary_rows"]] == [
        550.0,
        600.0,
    ]
    assert e56["mean_half_life_sweeps"] == 575.0
    assert e56["mean_half_life_over_tau"] == pytest.approx(1.15)
    assert e56["rho_scaling_identified"] is False
    assert e56["threshold_uses_first_sample_at_50_sweeps"] is True
    assert e56["E50_same_clock"]["measured_same_clock_confirmed"] is False

    e54 = audit["E54_whole_R_flagship"]
    assert e54["headline"]["live"] == pytest.approx(0.5735677083333333)
    assert e54["headline"]["knife"] == pytest.approx(0.576904296875)
    assert e54["live_minus_knife_contrast"]["mean_difference"] == pytest.approx(
        -0.0033365885416667407
    )
    assert e54["live_minus_knife_contrast"]["directions"] == {
        "positive": 1,
        "tied": 0,
        "negative": 1,
    }
    assert e54["intervention_audit"]["copy_versus_reset_control_present"] is False
    assert e54["observer_audit"]["uses_batch_member_zero_target_for_all_futures"]


def test_l17_separates_fixed_ancestor_from_immediate_parent(l17_result) -> None:
    audit = l17_result[0]
    e55 = audit["E55_error_threshold"]
    exact = e55["exact_copy_channel"]
    assert e55["all_reported_gates_and_summaries_match"] is True
    assert e55["threshold_reconstruction"]["all_registered_gates_false"] is True
    assert exact["generation_1_ancestor_regrown_at_least_once"] == pytest.approx(
        0.5406901041666667
    )
    assert exact["generation_1_strict_ancestor_is_undefined"] is True
    assert exact["generation_2_strict_ancestor"] == pytest.approx(
        0.5005045572916667
    )
    assert exact["generation_10_to_12_strict_ancestor_mean"] == pytest.approx(
        0.4937518084490741
    )
    assert exact["generation_10_to_12_immediate_parent_mean"] == pytest.approx(
        0.9412434895833334
    )
    assert exact["parent_minus_fixed_ancestor"]["directions"]["positive"] == 2
    assert e55["observer_and_null_audit"]["chance_value_0_5_calibrated"] is False
    assert e55["copy_intervention"]["R_copy_versus_reset_arm_present"] is False
    assert e55["capacity_interpretation"]["substantive_zero_capacity_established"] is False
    assert e55["domain_counts"]["post_imprint_rendition_min"] == 13
    assert e55["domain_counts"]["post_imprint_rendition_max"] == 22
    assert e55["domain_counts"]["exact_copy_final_median"] == 5.0


def test_l17_preserves_e57_design_limits_and_e61_aggregate_boundary(
    l17_result,
) -> None:
    audit = l17_result[0]
    e57 = audit["E57_injury_corollary"]
    assert e57["full_summary_recalculation"][
        "all_reported_gates_and_summaries_match"
    ] is True
    assert e57["transport_contrasts"]["static"]["mean_difference"] == pytest.approx(
        -0.12630208333333334
    )
    assert e57["transport_contrasts"]["switching_k4"][
        "mean_difference"
    ] == pytest.approx(-0.09244791666666667)
    assert e57["transport_contrasts"]["static"]["directions"] == {
        "positive": 2,
        "tied": 0,
        "negative": 4,
    }
    assert e57["source_design_audit"]["common_random_number_arms"] is False
    assert e57["mechanism_observability"][
        "memorizes_then_defends_injury_identified"
    ] is False
    assert e57["speed_identification"]["selected_champions_at_exact_rho_0_002"] == 1
    assert e57["speed_identification"][
        "literal_no_selection_ever_visits_slow_rho_corner"
    ] is False

    e61 = audit["E61_alien_blueprint"]
    assert e61["all_reported_gates_and_summaries_match"] is True
    assert e61["inheritance"]["live_values"]["copy"] == pytest.approx(
        0.4947102864583333
    )
    assert e61["inheritance"]["copy_live_minus_reset_live"] == pytest.approx(
        -0.0070800781250000555
    )
    assert e61["inheritance"]["registered_gate_is_copy_versus_reset"] is False
    assert e61["inheritance"]["chance_value_0_5_calibrated"] is False
    assert e61["retention"]["all_four_half_lives_censored"] is True
    assert e61["retention"]["attributes_persistence_to_R_vault"] is False
    assert e61["evidence_level"] == "E2"


def test_l17_emits_complete_tables_and_mixed_verdict(l17_result) -> None:
    (
        audit,
        paths,
        channel_rows,
        e54_rows,
        e55_curves,
        e55_generations,
        e57_rows,
        frozen,
    ) = l17_result
    assert audit["all_source_config_digests_match"] is True
    assert audit["overall_verdict"] == "MIXED"
    assert len(audit["claim_assessment"]) == 9
    assert len(channel_rows) == 11
    assert len(e54_rows) == 3
    assert len(e55_curves) == 36
    assert len(e55_generations) == 96
    assert len(e57_rows) == 24
    assert len(paths) == len(frozen) >= 100

    channel_lines = channel_table_csv(channel_rows).splitlines()
    assert len(channel_lines) == 12
    assert channel_lines[0].split(",") == list(CHANNEL_TABLE_FIELDS)
    assert len(e54_flagship_rows_csv(e54_rows).splitlines()) == 4
    assert len(e55_channel_curves_csv(e55_curves).splitlines()) == 37
    assert len(e55_generation_trace_csv(e55_generations).splitlines()) == 97
    assert len(e57_transport_rows_csv(e57_rows).splitlines()) == 25
    report = markdown_report(audit)
    assert "ancestor identity from parent continuity" in report
    assert "do not observe injury memory" in report
    assert "zero simulator replays" in report
