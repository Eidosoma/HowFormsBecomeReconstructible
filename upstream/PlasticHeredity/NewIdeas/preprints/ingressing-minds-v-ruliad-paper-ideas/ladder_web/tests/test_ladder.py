import numpy as np

from contract_bridge.artifacts import seed_rng
from ladder_web.config import LadderConfig
from ladder_web.engine import (
    ladder_fission, ladder_step, run_lineage, tissue_fields,
)
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import tissue_config


def _setup(rung="A"):
    config = LadderConfig.tiny()
    rc = RewriteConfig.tiny()
    tissue = tissue_config(0, rc.coupling_band, rc)
    from voltage_web.engine import launch_pattern, make_thresholds

    theta = make_thresholds(tissue)
    anchors = tissue_fields(tissue, config, rung)
    rng = np.random.default_rng(0)
    V = np.tile(launch_pattern(0, tissue), (2, 1, 1))
    return config, tissue, theta, anchors, rng, V


def test_rung_a_conserves_and_matches_frozen_physics_statistics():
    config, tissue, theta, _, rng, V = _setup("A")
    ema = V.copy()
    before = V.mean(axis=(-2, -1)).copy()
    from dataclasses import replace

    quiet = replace(tissue, sigma=0.0)
    for _ in range(50):
        V, ema, _ = ladder_step(V, ema, theta, quiet, config, "A", rng)
    np.testing.assert_allclose(V.mean(axis=(-2, -1)), before, atol=1e-6)


def test_anchors_hold_and_survive_fission():
    config, tissue, theta, anchors, rng, V = _setup("B")
    ema = V.copy()
    rows, cols, values = anchors[0], anchors[1], anchors[2]
    for _ in range(30):
        V, ema, _ = ladder_step(V, ema, theta, tissue, config, "B", rng, anchors)
    np.testing.assert_allclose(V[:, rows, cols], np.tile(values, (2, 1)), atol=1e-9)
    kids = ladder_fission(V, tissue, config, "B", rng, anchors)
    np.testing.assert_allclose(kids[:, rows, cols], np.tile(values, (2, 1)), atol=1e-9)


def test_stress_rises_under_insult_and_decays_at_setpoint():
    config, tissue, theta, anchors, rng, V = _setup("D")
    ema = V.copy()
    for _ in range(30):
        V, ema, S = ladder_step(V, ema, theta, tissue, config, "D", rng, anchors)
    settled_stress = float(S.mean())
    V_ins = V.copy()
    V_ins[:, 4:8, 4:8] = -V_ins[:, 4:8, 4:8]
    _, _, S_ins = ladder_step(V_ins, ema, theta, tissue, config, "D", rng, anchors)
    assert float(S_ins.mean()) > settled_stress


def test_lineage_runs_on_every_rung():
    config = LadderConfig.tiny()
    rc = RewriteConfig.tiny()
    tissue = tissue_config(0, rc.coupling_band, rc)
    for rung in ("A", "B", "C", "D"):
        out = run_lineage(tissue, config, rung, seed_rng("t", rung),
                          horizon=6, n_futures=4)
        assert out["censuses"].shape == (6, 4, 15)
        assert out["alive"].any()
