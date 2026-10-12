from pathlib import Path

import pytest

from laws_confirmation.l16_audit import (
    EXPECTED_CONFIG_DIGESTS,
    ROLE_TABLE_FIELDS,
    e53_tissue_contrasts_csv,
    e54_class_dose_csv,
    e57_regime_repeats_csv,
    markdown_report,
    role_table_csv,
    run_l16_audit,
    source_config_digests,
)


WORKSPACE = Path(__file__).resolve().parents[1]
PLASTIC_ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def l16_result():
    return run_l16_audit(PLASTIC_ROOT, WORKSPACE)


def test_l16_source_config_digests_match_retained_contract() -> None:
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l16_recalculates_e53_interventions_without_mislabeling_r_ablation(
    l16_result,
) -> None:
    audit = l16_result[0]
    e53 = audit["E53_hidden_genome"]
    assert e53["all_shard_derived_reported_fields_match"] is True
    assert e53["all_reported_gate_booleans_match"] is True
    assert e53["reconstructed_from_shards"]["drops"]["context_reset"] == pytest.approx(
        0.3466796875
    )
    assert e53["reconstructed_from_shards"]["r_marginal"] == pytest.approx(
        0.171875
    )
    assert e53["tissue_threshold_consistency"]["feedback_increment_positive"] == 6
    assert e53["tissue_threshold_consistency"][
        "context_drop_exceeds_both_theta_drops"
    ] == 6
    assert e53["content_transfer_control"]["favors_alternative_target"] is False
    intervention = e53["intervention_audit"]
    assert intervention["R_off_actually_sets_c_m_zero"] is True
    assert intervention["R_still_passed_to_regrow_in_feedback_off_arm"] is True
    assert intervention["R_still_updates_when_c_m_zero"] is True
    assert intervention["context_reset_leaves_any_original_V_fabric"] is False


def test_l16_preserves_equivalence_alignment_and_horizon_boundaries(
    l16_result,
) -> None:
    audit = l16_result[0]
    e54 = audit["E54_repertoire"]
    order = e54["recalculated_gates"]["order_mean_top2"]
    assert order["cross_tissue"] > order["in_repertoire"]
    assert e54["recalculated_gates"]["gate_p54_1_adoption_splits"] is False
    assert e54["equivalence_audit"]["class_blindness_confirmed"] is False
    assert e54["positive_control_audit"][
        "all_lineage_steering_rates_zero_including_floor"
    ] is True

    assert audit["E56_scaffold"]["calibration_retention"]["pin_at_chosen"] == pytest.approx(
        0.966796875
    )
    assert audit["E66_alignment_modifier"]["pin_at_chosen"] == pytest.approx(
        0.9736328125
    )
    assert audit["metric_comparability"][
        "controlled_alignment_by_norm_factorial_present"
    ] is False

    horizon = audit["E52_E57_horizon_comparison"]
    assert horizon["E52_both_median_rho"] == pytest.approx(0.1741983212333068)
    assert horizon["E57_max_selected_regime_median_rho"] == pytest.approx(
        0.016085507930321284
    )
    assert horizon["E57_coded_clause_at_0_02_passes"] is True
    assert horizon["E57_literal_law_clause_at_0_016_passes"] is False
    assert horizon["E52_value_permitted_by_E57_search_range"] is False
    assert horizon["horizon_causally_isolated"] is False


def test_l16_emits_complete_tables_and_mixed_clause_verdict(l16_result) -> None:
    audit, paths, role_rows, e53_rows, e54_rows, e57_rows, frozen = l16_result
    assert audit["all_source_config_digests_match"] is True
    assert audit["overall_verdict"] == "MIXED"
    assert len(audit["claim_assessment"]) == 7
    assert len(role_rows) == 20
    assert len(e53_rows) == 6
    assert len(e54_rows) == 48
    assert len(e57_rows) == 24
    assert len(paths) == len(frozen) >= 150

    role_lines = role_table_csv(role_rows).splitlines()
    assert len(role_lines) == 21
    assert role_lines[0].split(",") == list(ROLE_TABLE_FIELDS)
    assert len(e53_tissue_contrasts_csv(e53_rows).splitlines()) == 7
    assert len(e54_class_dose_csv(e54_rows).splitlines()) == 49
    assert len(e57_regime_repeats_csv(e57_rows).splitlines()) == 25
    report = markdown_report(audit)
    assert "active R-to-V feedback" in report
    assert "ordering failure, not equivalence" in report
    assert "zero simulator replays" in report
