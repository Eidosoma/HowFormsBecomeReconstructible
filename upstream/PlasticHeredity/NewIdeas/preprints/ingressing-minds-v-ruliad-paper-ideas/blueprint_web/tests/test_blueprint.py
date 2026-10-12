import numpy as np
from dataclasses import replace

from blueprint_web.config import BlueprintConfig
from blueprint_web.engine import (
    blueprint_fission, blueprint_step, settle_with_blueprint,
)
from contract_bridge.artifacts import seed_rng
from ladder_web.config import LadderConfig
from setpoint_rewrite.config import RewriteConfig
from setpoint_rewrite.runner import tissue_config
from voltage_web.engine import launch_pattern, make_thresholds


def test_ema_reference_tracks_slow_and_satisfiability():
    bp = BlueprintConfig()
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    rng = seed_rng("bp-t1", 0)
    # Fair steady-state form: settle the body first, then initialize R and
    # let it track at its own slow clock before measuring.
    V, ema, Rf, theta, ladder = settle_with_blueprint(
        tissue, bp, "A", rng, None, futures=4, sweeps=120)
    Rf = V.copy()
    from blueprint_web.engine import blueprint_step

    for _ in range(200):
        V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder, bp,
                                    "T", rng)
    # Satisfiability: the reference lives INSIDE the tissue's own thermal
    # fluctuation scale (the E42 disease was an off-manifold OFFSET).
    ref_err = float(np.abs(Rf - V).mean())
    fluct = float(np.abs(V - np.sign(V)).mean())
    assert ref_err <= 1.5 * fluct
    # At the freedom-compatible clock the reference LAGS the drifting
    # self (~17% of cells) — memory must be slow to be free. The
    # satisfiability claim is drift-envelope, not instantaneous identity.
    assert float(((Rf > 0) == (V > 0)).mean()) > 0.8


def test_blueprint_inherited_whole_through_fission():
    bp = BlueprintConfig()
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    rng = seed_rng("bp-t2", 0)
    V, ema, Rf, theta, ladder = settle_with_blueprint(
        tissue, bp, "T", rng, None, futures=2, sweeps=40)
    kids, R_kid = blueprint_fission(V, Rf, tissue, rng)
    np.testing.assert_allclose(R_kid, Rf)          # whole blueprint
    resting_frac = (np.abs(kids - tissue.resting) < 0.2).mean()
    assert resting_frac > 0.2                       # body genuinely halved


def test_regrowth_toward_inherited_blueprint():
    bp = BlueprintConfig()
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    rng = seed_rng("bp-t3", 0)
    V, ema, Rf, theta, ladder = settle_with_blueprint(
        tissue, bp, "T", rng, None, futures=4, sweeps=120)
    kids, R_kid = blueprint_fission(V, Rf, tissue, rng)
    ema_k = kids.copy()
    Va = kids.copy(); Ra = None                     # ablated control
    ema_a = kids.copy()
    for _ in range(80):
        kids, ema_k, R_kid = blueprint_step(
            kids, ema_k, R_kid, theta, tissue, ladder, bp, "T", rng)
        Va, ema_a, Ra = blueprint_step(
            Va, ema_a, None, theta, tissue, ladder, bp, "A", rng)
    match_bp = float(((kids > 0) == (R_kid > 0)).mean())
    match_ab = float(((Va > 0) == (Rf > 0)).mean())
    assert match_bp > match_ab + 0.1
    assert match_bp > 0.75


def test_lesion_is_stream_exact():
    bp = BlueprintConfig()
    rc = RewriteConfig()
    tissue = tissue_config(0, rc.coupling_band, rc)
    ladder = LadderConfig()
    theta = make_thresholds(tissue)
    V0 = np.tile(launch_pattern(0, tissue), (1, 1, 1))
    Va, ema_a = V0.copy(), V0.copy()
    Ra = V0.copy()
    Vb, ema_b = V0.copy(), V0.copy()
    rng_a, rng_b = np.random.default_rng(5), np.random.default_rng(5)
    from ladder_web.engine import ladder_step

    for _ in range(20):
        Va, ema_a, Ra = blueprint_step(Va, ema_a, Ra, theta, tissue, ladder,
                                       bp, "T", rng_a, c_m=0.0)
        Vb, ema_b, _ = ladder_step(Vb, ema_b, theta, tissue, ladder, "A",
                                   rng_b, None)
    np.testing.assert_allclose(Va, Vb, atol=1e-12)
