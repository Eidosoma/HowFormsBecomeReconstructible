from laws_confirmation.l3_audit import (
    _bridge_phase_recalculation,
    _e12_transitivity_gate,
    _e20_transitivity_gate,
    _recursive_close,
    source_config_digests,
)


def test_source_config_digests_match_retained_defaults():
    assert source_config_digests() == {
        "rosetta_atlas": "571bd16bbb2ad8fb44806147392ae46e3fa9b7633bdbc6d2fe6ed6bec0784a23",
        "eca_bridge": "fa026ade5018fd87384c4980272e07f1ad8ffe2839511951c27f5df3a8e2d1da",
        "life_family": "781392f8a62bf21d148c65dcb066cbf930b8448c535ae462e300ccc1da79a45d",
        "morpho_gps": "2b95f98e2ae2eb2f092cf8a1f46868ba4879f093e88027513f02d3bbe9ffc4fc",
        "sealed_battery_2": "4109c2f23d1dadce602ae199443b6a6f214aad5fb6383aad9b42dfba5091b82b",
        "form_atlas_scale": "9f4b9a4f5ed084d04c46d3c368420d7d402e88179bc6fa0868302171826dabee",
    }


def test_bridge_phase_recalculation_uses_conjunction_not_marginals():
    payload = {
        "summary": {"phase": "confirm"},
        "pairs": [
            {
                "beats_occupancy": True,
                "beats_shuffled": True,
                "beats_random_median": True,
            },
            {
                "beats_occupancy": True,
                "beats_shuffled": False,
                "beats_random_median": True,
            },
        ],
    }
    result = _bridge_phase_recalculation(payload)
    assert result["beats_occupancy_fraction"] == 1.0
    assert result["beats_all_nulls_fraction"] == 0.5
    assert result["gate_bridge"] is False


def test_transitivity_thresholds_are_experiment_specific():
    e20 = {
        "composed_beats_all_nulls_fraction": 0.7,
        "composed_beats_ci_low": 0.6,
        "mean_agreement_direct_vs_composed": 0.6,
        "mean_shuffled_agreement": 0.3,
        "retains_direct_advantage_fraction": 0.5,
    }
    assert _e20_transitivity_gate(e20)["transitivity_confirmed"] is True
    e12 = {
        "composed_beats_all_nulls_fraction": 0.7,
        "composed_beats_ci_low": 0.6,
        "mean_agreement_direct_vs_composed": 0.5,
        "shuffled_agreement_baseline": 0.3,
        "retains_direct_advantage_fraction": 2 / 3,
    }
    assert _e12_transitivity_gate(e12)["transitivity_confirmed"] is True


def test_missing_json_number_matches_historical_nan_sentinel():
    assert _recursive_close(None, float("nan"))
