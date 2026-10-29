"""The restated identity route against the legacy native engine, bit for bit.

Legacy packages are imported read-only from their source trees; nothing is patched and
no bytecode is written next to them.
"""
from pathlib import Path
import sys

import numpy as np
import pytest

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
LEGACY = LANE.parents[2] / "PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas"
PACKAGES = ("voltage_web", "ladder_web", "blueprint_web", "growing_web",
            "contract_bridge", "glider_test", "xeno_bridge")

from mse.engine import ROUTES, Route, State, run, step  # noqa: E402
from mse.native import NATIVE, half_plane  # noqa: E402


@pytest.fixture(scope="module")
def legacy():
    sys.dont_write_bytecode = True
    for name in PACKAGES:
        src = LEGACY / name / "src"
        if not src.is_dir():
            pytest.skip(f"legacy source absent: {src}")
        sys.path.insert(0, str(src))
    from blueprint_web.config import BlueprintConfig
    from blueprint_web.engine import blueprint_step
    from ladder_web.config import LadderConfig
    from voltage_web.config import VoltageConfig
    from voltage_web.engine import launch_pattern, make_thresholds
    tissue = VoltageConfig()
    return dict(step=blueprint_step, tissue=tissue, ladder=LadderConfig(), bp=BlueprintConfig,
                theta=make_thresholds(tissue), launch=launch_pattern)


def start(legacy, batch=6, seed=7):
    rng = np.random.default_rng(seed)
    V = np.stack([legacy["launch"](i % 6, legacy["tissue"]) for i in range(batch)])
    V = V + legacy["tissue"].copy_jitter * rng.standard_normal(V.shape)
    return V, V.copy(), V.copy() + 0.1 * rng.standard_normal(V.shape)


@pytest.mark.parametrize("route,c_m,rho", [("reciprocal", None, None),
                                           ("reference", 0.0, None),
                                           ("body", None, 0.0)])
def test_identity_routes_bit_exact(legacy, route, c_m, rho):
    V, ema, R = start(legacy)
    bp = legacy["bp"]() if rho is None else legacy["bp"](rho=rho)
    a, b = np.random.default_rng(11), np.random.default_rng(11)
    lv, le, lr = V.copy(), ema.copy(), R.copy()
    s = State(V.copy(), ema.copy(), R.copy(), np.zeros_like(V))
    for _ in range(300):
        lv, le, lr = legacy["step"](lv, le, lr, legacy["theta"], legacy["tissue"], legacy["ladder"],
                                    bp, "T", a, c_m=c_m)
        s = step(s, legacy["theta"], b.standard_normal(V.shape), ROUTES[route])
    assert np.array_equal(s.V, lv) and np.array_equal(s.ema, le) and np.array_equal(s.R, lr)


def test_constants_match_legacy(legacy):
    t, lad, bp = legacy["tissue"], legacy["ladder"], legacy["bp"]()
    assert (t.dt, t.coupling, t.sigma, t.well_asym, t.threshold_spread) == (
        NATIVE.dt, NATIVE.coupling, NATIVE.sigma, NATIVE.well_asym, NATIVE.threshold_spread)
    assert (lad.ema_rate, bp.c_m, bp.rho) == (NATIVE.ema_rate, NATIVE.gain, NATIVE.rho)
    for k in (0, 1):
        assert np.array_equal(half_plane(k, 1.0), legacy["launch"](k, t))


def test_capture_identity_and_isolation(legacy):
    """L17 checks: R_t - Q_t = (1 - rho)^t R_0 for a live R; Q never feeds V or R."""
    V, ema, R = start(legacy)
    theta = legacy["theta"]
    noise = np.random.default_rng(3)
    draws = [noise.standard_normal(V.shape) for _ in range(400)]
    with_q = run(State(V.copy(), ema.copy(), R.copy(), np.zeros_like(V)), theta,
                 lambda t: draws[t - 1], ROUTES["reciprocal"], 400)
    no_q = run(State(V.copy(), ema.copy(), R.copy(), np.zeros_like(V)), theta,
               lambda t: draws[t - 1], Route(capture=None), 400)
    assert np.array_equal(with_q.V, no_q.V) and np.array_equal(with_q.R, no_q.R)
    assert not np.any(no_q.Q)
    np.testing.assert_allclose(with_q.R - with_q.Q, (1 - NATIVE.rho) ** 400 * R, atol=1e-12, rtol=0)


def test_policy_with_native_constants_is_bit_exact(legacy):
    """The policy hook adds nothing when it returns the native gain and rate."""
    V, ema, R = start(legacy)
    draws = [np.random.default_rng(17).standard_normal(V.shape) for _ in range(200)]
    noise = lambda t: draws[t - 1]
    s0 = State(V.copy(), ema.copy(), R.copy(), np.zeros_like(V))
    plain = run(s0.copy(), legacy["theta"], noise, ROUTES["reciprocal"], 200)
    scalar = run(s0.copy(), legacy["theta"], noise, ROUTES["reciprocal"], 200,
                 policy=lambda Vt, e, r: (NATIVE.gain, NATIVE.rho))
    full = lambda x: np.full((len(V), 1, 1), x)
    arrays = run(s0.copy(), legacy["theta"], noise, ROUTES["reciprocal"], 200,
                 policy=lambda Vt, e, r: (full(NATIVE.gain), full(NATIVE.rho)))
    for other in (scalar, arrays):
        assert all(np.array_equal(getattr(plain, k), getattr(other, k)) for k in ("V", "ema", "R", "Q"))


def test_off_reader_is_packet_independent(legacy):
    """With comparison off, V and ema do not depend on R at all."""
    V, ema, R = start(legacy)
    draws = [np.random.default_rng(5).standard_normal(V.shape)]
    a = step(State(V, ema, R, np.zeros_like(V)), legacy["theta"], draws[0], ROUTES["reference"])
    b = step(State(V, ema, -3 * R, np.zeros_like(V)), legacy["theta"], draws[0], ROUTES["reference"])
    assert np.array_equal(a.V, b.V) and np.array_equal(a.ema, b.ema)


def test_imposed_teaching_matches_legacy_hold(legacy):
    """L15 full-field hold: the body is overwritten with the template before each step."""
    V, ema, R = start(legacy)
    template = half_plane(1, 1.2)
    a, b = np.random.default_rng(13), np.random.default_rng(13)
    lv, le, lr = V.copy(), ema.copy(), R.copy()
    for _ in range(50):
        lv = np.broadcast_to(template, V.shape).copy()
        lv, le, lr = legacy["step"](lv, le, lr, legacy["theta"], legacy["tissue"], legacy["ladder"],
                                    legacy["bp"](), "T", a)
    s = run(State(V.copy(), ema.copy(), R.copy(), np.zeros_like(V)), legacy["theta"],
            lambda t: b.standard_normal(V.shape), ROUTES["reciprocal"], 50, imposed=template)
    assert np.array_equal(s.V, lv) and np.array_equal(s.R, lr) and np.array_equal(s.ema, le)
