from pathlib import Path

from laws_confirmation.l9_audit import (
    EXPECTED_CONFIG_DIGESTS,
    run_l9_audit,
    source_config_digests,
)


PLASTIC_ROOT = Path(__file__).resolve().parents[5]


def test_l9_source_config_digests_match_retained_defaults():
    observed = source_config_digests()
    for name, retained in EXPECTED_CONFIG_DIGESTS.items():
        if name != "E48_blueprint_web":
            assert observed[name] == retained
    assert observed["E48_blueprint_web"] == (
        "49c8fda1347f2ae7d930256144e7d0a997ac2cbe8bcca225ce196b86740721ff"
    )
    assert observed["E48_blueprint_web"] != EXPECTED_CONFIG_DIGESTS["E48_blueprint_web"]


def test_l9_reconstructs_rows_and_keeps_theorem_boundaries():
    audit, paths = run_l9_audit(PLASTIC_ROOT)

    assert audit["all_source_config_digests_match"] is False
    assert audit["source_config_digest_matches"]["E48_blueprint_web"] is False
    assert sum(not value for value in audit["source_config_digest_matches"].values()) == 1

    e43 = audit["E43_growing_web"]
    assert e43["reported_gates_match"] is True
    assert e43["carrier_implementation"]["motility_swaps_voltage_V"] is True
    assert e43["carrier_implementation"]["motility_swaps_ema_history"] is False
    assert e43["carrier_implementation"]["motility_swaps_theta"] is False

    e44 = audit["E44_lightcone_3"]
    assert e44["integrity"]["complete_expected_grid"] is True
    assert e44["all_reported_gates_and_summaries_match"] is True
    assert e44["distance_8_contrasts"]["H_minus_D"]["mean_difference"] < 0

    e48 = audit["E48_blueprint_web"]
    assert e48["current_source_digest_matches_retained"] is False
    assert e48["all_cell_flags_recalculate"] is True
    assert e48["passing_matches"] is True
    assert e48["retention"]["regrowth_0_711_vs_0_543_machine_readable"] is False

    e49 = audit["E49_triangle_final"]
    assert e49["integrity"]["complete_expected_jobs"] is True
    assert e49["all_reported_gates_and_summaries_match"] is True
    assert e49["recalculated_gates"]["gate_p49_1_transport"] is True
    assert e49["distance_8_contrasts"]["profile_T_minus_D"]["directions"]["positive"] == 12
    assert e49["knife_audit"]["D_and_T_lesion_aggregate_numbers_exactly_equal"] is False
    assert e49["target_and_dose_audit"]["maximum_imprint_sweeps"] == 256

    e51 = audit["E51_two_headed_final"]
    assert e51["integrity"]["complete_expected_jobs"] is True
    assert e51["all_reported_gates_and_summaries_match"] is True

    e53 = audit["E53_hidden_genome"]
    assert e53["mechanism_update"]["repair_timescale_carrier"] == "context"
    assert e53["mechanism_update"]["context_repair_drop"] > 0.25
    assert e53["mechanism_update"]["theta_repair_drop_max"] < 0.10

    e54 = audit["E54_repertoire"]
    assert e54["integrity"]["complete_jobs"] is True
    assert e54["all_reported_gates_and_summaries_match"] is True
    assert e54["mechanism_update"]["in_repertoire_advantage_over_cross_tissue"] < 0

    assert audit["proof_audit"]["formal_proof_artifact_found"] is False
    assert audit["claim_assessment"][
        "content_resolution_reference_necessarily_abolishes_freedom"
    ]["status"] == "REFUTED_ON_FINITE_OPERATIONALIZATION"
    assert audit["overall_verdict"] == "REFUTED"
    assert len(paths) >= 100
