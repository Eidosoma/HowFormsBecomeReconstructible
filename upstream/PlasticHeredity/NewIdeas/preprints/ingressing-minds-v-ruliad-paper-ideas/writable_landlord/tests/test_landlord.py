from dataclasses import replace

import numpy as np

from contract_bridge.artifacts import seed_rng
from writable_landlord.config import LandlordConfig
from writable_landlord.pipeline import (capacity_gate, cascade_step,
                                        landlord_lineage, project_theta)


def _small():
    return replace(LandlordConfig(), n_tissues=1, futures=4,
                   settle_sweeps=6, imprint_sweeps=6, cycles=3,
                   inter_fission=6, capacity_settle=20,
                   pullback_window=5, consensus_settle=6,
                   repertoire_seeds=3, zap_recover=6,
                   imprint_gate_cycles=2)


def test_project_theta_per_future():
    rng = seed_rng("p", 0)
    theta = 5.0 * rng.standard_normal((3, 8, 8)) + 2.0
    out = project_theta(theta, 0.3)
    assert np.allclose(out.mean(axis=(-2, -1)), 0.0, atol=1e-9)
    assert np.allclose(out.std(axis=(-2, -1)), 0.3, atol=1e-9)


def test_cascade_step_batched_theta():
    from setpoint_rewrite.config import RewriteConfig
    from setpoint_rewrite.runner import tissue_config
    from ladder_web.config import LadderConfig
    from blueprint_web.config import BlueprintConfig
    from voltage_web.engine import make_thresholds

    config = _small()
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    theta = np.tile(make_thresholds(tissue), (4, 1, 1))
    rng = seed_rng("c", 0)
    V = rng.standard_normal((4, tissue.height, tissue.width))
    ema, Rf = V.copy(), V.copy()
    V2, ema2, Rf2, th2 = cascade_step(V, ema, Rf, theta, tissue,
                                      LadderConfig(), BlueprintConfig(),
                                      rng, 0.001, 0.3)
    assert V2.shape == V.shape and th2.shape == theta.shape
    assert not np.allclose(th2, theta)
    _, _, _, th3 = cascade_step(V, ema.copy(), Rf.copy(), theta, tissue,
                                LadderConfig(), BlueprintConfig(),
                                seed_rng("c", 0), 0.0, 0.3)
    assert np.array_equal(th3, theta)


def test_capacity_gate_reports_rows():
    config = _small()
    out = capacity_gate(config)
    assert len(out["rows"]) == 3
    for r in out["rows"]:
        assert 0.0 <= r["pin"] <= 1.0


def test_lineage_small_runs():
    config = _small()
    out = landlord_lineage(config, 0, "writable_fast", 0.4, 0.3)
    assert out["arm"] == "writable_fast"
    assert out["theta_final"].shape[0] == config.futures
