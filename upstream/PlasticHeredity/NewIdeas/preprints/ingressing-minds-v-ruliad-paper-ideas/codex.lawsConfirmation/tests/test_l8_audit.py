from pathlib import Path

from laws_confirmation.l8_audit import (
    EXPECTED_CONFIG_DIGESTS,
    run_l8_audit,
    source_config_digests,
)


PLASTIC_ROOT = Path(__file__).resolve().parents[5]


def test_l8_source_config_digests_match_retained_defaults():
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l8_retained_replay_audit_keeps_registration_and_mechanism_boundaries():
    audit, paths = run_l8_audit(PLASTIC_ROOT)

    e37 = audit["E37_persuadability"]
    assert e37["integrity"]["complete_expected_grid"] is True
    assert e37["all_64_reported_cells_match"] is True
    assert e37["all_reported_gates_match"] is True
    assert e37["all_B_C_D_cell_means_below_half"] is True
    assert e37["implementation_audit"][
        "L1_and_L4_have_identical_voltage_update_expression"
    ] is True
    assert e37["maximum_rate_cell_by_rung"]["B"]["rate"] == 0.42578125

    e38 = audit["E38_james_test"]
    assert e38["all_reported_gate_fields_match"] is True
    assert e38["executed_registry"]["diagonal_called_by_main_run"] is False
    assert e38["retention_limits"]["calibration_rows"] is False

    e39 = audit["E39_excitable_web"]
    assert e39["later_absolute_gate"]["replayed_pass"] is True
    assert e39["current_source_amplification_matches_retained"] is False
    assert e39["current_source_replay"]["current_source_amplification"][
        "caused_supra"
    ] == 14.389482701938455
    assert e39["current_source_replay"]["lesion_golden"][
        "max_abs_voltage_delta"
    ] == 0.0
    assert e39["current_source_replay"]["conservation_golden"][
        "all_current_source_test_assertions_pass"
    ] is False
    assert e39["original_WAVE9_registered_gate"]["status"] == (
        "NOT_ADJUDICABLE_FROM_RETAINED_RESULT"
    )

    e40 = audit["E40_lightcone_2"]
    assert e40["integrity"]["complete_expected_grid"] is True
    assert e40["all_reported_gates_and_summaries_match"] is True
    assert e40["longest_distance_diagnostics"]["F_minus_D"][
        "mean_recovery_fraction_difference"
    ] < 0
    assert e40["longest_distance_diagnostics"]["F_minus_F_lesion"][
        "paired_tissue_bootstrap_95"
    ][1] < 0

    e41 = audit["E41_persuadability_2"]
    assert e41["all_reported_gate_fields_match"] is True
    assert e41["coupling_and_content_audit"][
        "current_coupling_transmits_cue_channel_sign_to_voltage"
    ] is False
    assert e41["knife_diagnostics"]["E_active_minus_lesion"] == 0.0

    assert audit["E47_amplifier_seal"]["recalculated_gate"] is True
    assert audit["claim_assessment"][
        "amplification_without_amplifiable_content_is_identified_mechanism"
    ]["status"] == "NOT_CONFIRMED"
    assert audit["overall_verdict"] == "MIXED"
    assert len(paths) >= 160
