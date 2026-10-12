import numpy as np

from contract_bridge.artifacts import seed_rng
from voltage_web.config import VoltageConfig
from voltage_web.engine import (
    fission, launch_pattern, make_thresholds, run_seed, sheet_step,
)


def _quiet(config, **kw):
    from dataclasses import replace

    return replace(config, sigma=0.0, threshold_spread=0.0, copy_jitter=0.0, **kw)


def test_mean_potential_is_conserved_noiselessly():
    config = _quiet(VoltageConfig.tiny(), coupling=1.0)
    theta = np.zeros((config.height, config.width))
    rng = np.random.default_rng(0)
    V = np.tile(launch_pattern(2, config), (2, 1, 1)) * 0.7
    before = V.mean(axis=(-2, -1)).copy()
    for _ in range(200):
        V = sheet_step(V, theta, config, rng)
    np.testing.assert_allclose(V.mean(axis=(-2, -1)), before, atol=1e-6)


def test_field_bimodalizes_while_mean_holds():
    config = _quiet(VoltageConfig.tiny(), coupling=0.5)
    theta = np.zeros((config.height, config.width))
    rng = np.random.default_rng(1)
    V = 0.2 * rng.standard_normal((1, config.height, config.width))
    V -= V.mean()
    for _ in range(400):
        V = sheet_step(V, theta, config, rng)
    assert np.abs(V.mean()) < 1e-5
    assert np.mean(np.abs(V) > 0.6) > 0.6  # cells committed to wells


def test_half_domain_survives_strong_coupling():
    config = _quiet(VoltageConfig.tiny(), coupling=2.0)
    theta = np.zeros((config.height, config.width))
    rng = np.random.default_rng(0)
    V = np.tile(launch_pattern(0, config), (1, 1, 1))
    before = (V[0] > 0).mean()
    for _ in range(400):
        V = sheet_step(V, theta, config, rng)
    after = (V[0] > 0).mean()
    assert abs(after - before) < 0.15  # conservation holds the domain


def test_fission_keeps_exactly_one_half_and_resets_the_other():
    config = _quiet(VoltageConfig.tiny())
    rng = seed_rng("fission-test", 0)
    V = np.tile(launch_pattern(2, config), (4, 1, 1))
    kids = fission(V, config, rng)
    for b in range(4):
        resting_fraction = (np.abs(kids[b] - config.resting) < 1e-9).mean()
        assert abs(resting_fraction - 0.5) <= 0.55  # half reset (some overlap ok)
        assert kids[b].shape == V[b].shape


def test_run_seed_returns_seedstats_and_zap_hook_works():
    from xeno_bridge.lineage import SeedStats

    config = VoltageConfig.tiny()
    stats = run_seed(0, config, seed_rng("t", 0), n_futures=6)
    assert isinstance(stats, SeedStats)
    mask = np.zeros((config.height, config.width), dtype=bool)
    mask[:, -config.width // 4:] = True
    zapped = run_seed(
        0, config, seed_rng("t", 0), n_futures=6,
        zap={"generation": 1, "mask": mask, "sweeps": 4},
    )
    assert isinstance(zapped, SeedStats)
