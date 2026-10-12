from pathlib import Path

import pytest

from laws_confirmation.l11_audit import (
    EXPECTED_CONFIG_DIGESTS,
    paired_tissue_diagnostic,
    run_l11_audit,
    source_config_digests,
)


PLASTIC_ROOT = Path(__file__).resolve().parents[5]


def test_l11_source_config_digests_match_retained_summaries():
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l11_paired_tissue_diagnostic_is_cluster_level_and_exact():
    result = paired_tissue_diagnostic([1.0, 2.0, 3.0], [0.0, 0.0, 0.0], seed=7, draws=32)
    assert result["n_tissues"] == 3
    assert result["left_minus_right_mean"] == pytest.approx(2.0)
    assert result["directions_positive_tie_negative"] == {
        "positive": 3,
        "tie": 0,
        "negative": 0,
    }
    assert result["exhaustive_sign_flip_assignments"] == 8
    assert result["exhaustive_two_sided_sign_flip_p"] == pytest.approx(0.25)
    assert result["outcome_known_descriptive_only"] is True


def test_l11_retained_reconstructions_preserve_failed_gates_and_repeat_spread():
    audit, paths = run_l11_audit(PLASTIC_ROOT, replay=False)
    e52 = audit["E52_retained_reconstruction"]
    e57 = audit["E57_retained_reconstruction"]

    assert audit["all_source_config_digests_match"] is True
    assert audit["shard_config_digest_matches"] == {"E52": True, "E57": True}
    assert e52["rows"] == 32
    assert e52["reconstructs_retained_gates"] is True
    assert e52["plasticity_repeat_medians_in_declared_band"] == 2
    assert e52["both_repeat_medians_in_declared_band"] == 0
    assert e52["calculated_gates"]["gate_p52_3_origin_of_development"] is False
    assert e52["per_regime"]["both"]["rho_median_at_upper_bound"] == 2
    assert e57["rows"] == 24
    assert e57["reconstructs_retained_p57_1"] is True
    assert e57["calculated_p57_1"]["gate_p57_1_horizon_law"] is False
    assert audit["E52_E57_horizon_comparison"]["only_evaluation_horizon_changes"] is False
    assert len(paths) >= 100


def test_l11_static_source_audit_rejects_escape_and_mechanism_overclaim():
    audit, _paths = run_l11_audit(PLASTIC_ROOT, replay=False)
    geometry = audit["E46_source_audit"]
    mechanism = audit["E46_mechanism_audit"]

    assert geometry["endpoint_labels_or_tracks_cells"] is False
    assert geometry["endpoint_requires_wall_crossing"] is False
    assert geometry["endpoint_requires_arrival_in_home_half"] is False
    assert geometry["home_mass0_used_after_assignment"] is False
    assert geometry["wall_is_closed_separator"] is False
    assert geometry["wall_is_clamped_after_construction"] is False
    assert geometry["D_motility_enabled"] is False
    assert mechanism["D_vs_H_is_chemotaxis_only"] is False
    assert mechanism["matched_chi_zero_knife_with_same_draws_retained"] is False
    assert audit["E52_source_audit"]["direct_useful_memory_assay"] is False
    assert audit["claim_assessment"][
        "chemotactic_tissue_escapes_geometric_trap_less_than_passive_tissue"
    ]["status"] == "NOT_CONFIRMED_ENDPOINT_DOES_NOT_MEASURE_CROSSING"
    assert audit["overall_verdict"] == "NOT_CONFIRMED"
