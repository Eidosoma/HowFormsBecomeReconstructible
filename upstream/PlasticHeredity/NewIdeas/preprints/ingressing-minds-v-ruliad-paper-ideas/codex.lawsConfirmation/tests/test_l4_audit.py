from laws_confirmation.l4_audit import (
    E28_CONTROL_GENERATION,
    E28_HORIZONS,
    E28_POSTHOC_HORIZONS,
    E28_REPLAY_TRAJECTORIES,
    source_config_digests,
)


def test_l4_e28_replay_contract_uses_one_shared_historical_cohort():
    assert E28_POSTHOC_HORIZONS == (2, 4, 6)
    assert E28_CONTROL_GENERATION == 10
    assert E28_HORIZONS == (2, 4, 6, 10)
    assert E28_REPLAY_TRAJECTORIES == 12 * 6 * 64


def test_l4_source_config_digests_match_retained_defaults():
    assert source_config_digests() == {
        "particle_observer": "152bd40bedd74b094b4c8d714bd2a60eca961e7e88de85b422d4cbdea2ac170e",
        "figure_ground_voltage": "0e03a32324300adbf45a64672f1fcaed892b6ce6e65fdbb5f9f8a5ca874c1da9",
        "position_observer": "c53b33bfd4941f56b0cdcb4393f1c519c1332b282c851fcb37594bfe7658893c",
        "kuramoto_web": "aea0f4f86eeba44d44c1aa1a0f52d8cac3aeeac868e7ab134d29a85afa6a30bb",
        "grayscott_web": "15dd2c065af707c4e33e5138028b3f072ebd9d49b4e47407c8bd6a5f88b2e9a3",
    }
