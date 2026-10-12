from pathlib import Path

import numpy as np
import pytest

from laws_confirmation.l12_audit import (
    EXPECTED_CONFIG_DIGESTS,
    batch_pair_analysis,
    e50_scattering_analysis,
    individual_pair_analysis,
    run_l12_audit,
    source_config_digests,
)


PLASTIC_ROOT = Path(__file__).resolve().parents[5]


def test_l12_source_config_digests_match_retained_summaries():
    assert source_config_digests() == EXPECTED_CONFIG_DIGESTS


def test_l12_batch_pair_analysis_keeps_tissues_as_clusters_and_uses_shift_null():
    base = np.zeros((4, 4), dtype=float)
    base[0, 0] = 1.0
    maps = np.stack((base, base, np.roll(base, 1, axis=0), np.roll(base, 1, axis=0)))
    tissues = np.asarray((0, 0, 1, 1))
    result = batch_pair_analysis(
        maps, tissues, exclude_zero=False, bootstrap_seed=7
    )

    assert result["pair_count"] == 2
    assert result["pair_count_by_tissue"] == {"0": 1, "1": 1}
    assert result["tissues_with_at_least_one_pair"] == 2
    assert result["equal_eligible_tissue_mean_raw_cosine"] == pytest.approx(1.0)
    assert result["raw_cosine"]["mean"] == pytest.approx(1.0)
    assert result["between_tissue"]["pair_count"] == 4
    assert result["between_tissue"]["raw_cosine"]["mean"] == pytest.approx(0.0)
    assert result["exact_nonzero_toroidal_translation_null"][
        "shifts_per_pair"
    ] == 15
    assert result["exact_nonzero_toroidal_translation_null"][
        "observed_minus_pair_null_mean_raw"
    ]["mean"] > 0.9
    assert len(result["tissue_cluster_bootstrap_95_mean_raw_cosine"]) == 2


def test_l12_individual_pair_analysis_reports_batch_and_endpoint_strata():
    maps = np.zeros((2, 2, 16, 16), dtype=float)
    maps[0, 0, 0, 0] = 1
    maps[0, 1, 0, 0] = 1
    maps[1, 0, 0, 0] = 1
    maps[1, 1, 1, 1] = 1
    result = individual_pair_analysis(
        maps,
        tissues=np.asarray((0, 0)),
        replicas=np.asarray((0, 1)),
        arrived=np.asarray(((True, True), (True, False))),
    )

    assert result["all"]["pair_count"] == 6
    assert result["same_replica_batch"]["pair_count"] == 2
    assert result["different_replica_batch"]["pair_count"] == 4
    assert result["both_arrived"]["pair_count"] == 3
    assert result["both_nonarrived"]["pair_count"] == 0
    assert result["discordant_endpoint"]["pair_count"] == 3


def test_l12_e50_scattering_distinguishes_clustered_support_descriptively():
    maps = np.zeros((2, 1, 16, 16), dtype=float)
    maps[0, 0, 0, :4] = 1
    maps[1, 0, (0, 4, 8, 12), (0, 4, 8, 12)] = 1
    result = e50_scattering_analysis(maps)

    assert result["individual_maps"] == 2
    assert result["active_pixels"]["median"] == pytest.approx(4.0)
    assert result["four_neighbour_toroidal_components"]["min"] == 1
    assert result["four_neighbour_toroidal_components"]["max"] == 4
    assert result["active_pixel_histogram"] == {"4": 2}
    assert result["maps_with_at_least_two_active_pixels"] == 2
    assert result["maps_with_adjacent_active_pixels"] == 1
    assert result["causal_noise_classification_identified"] is False


def test_l12_static_source_audit_preserves_measurement_and_causal_boundaries():
    audit, paths, arrays, hashes = run_l12_audit(PLASTIC_ROOT, replay=False)
    source = audit["source_audit"]

    assert audit["all_config_digests_match"] is True
    assert source["road_definitions_are_common_across_experiments"] is False
    assert source["E42"]["registered_map_is_batch_mean"] is True
    assert source["E42"]["registered_map_is_firing_event_history"] is False
    assert source["E42"]["configured_mid_fraction_is_used"] is False
    assert source["E42"]["computed_mid_sweep_selects_registered_map"] is False
    assert source["E46"]["persistent_cell_identity_or_net_displacement_tracked"] is False
    assert source["E46"]["explicit_random_axis_parity_proposal_acceptance"] is True
    assert source["E46"]["axis_and_parity_draws_shared_by_all_futures_in_a_batch"] is True
    assert source["E50"]["registered_map_accumulates_voltage_sign_flips"] is True
    assert source["E50"]["varying_means_gate_requires_endpoint_convergence"] is False
    assert source["E50"]["predeclared_noise_scattered_threshold"] is False
    assert source["error_geometry_causally_identified"] is False
    assert arrays == {}
    assert len(paths) == len(hashes)
    assert len(paths) >= 80
