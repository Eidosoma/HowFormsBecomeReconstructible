"""ME001 v2 runner pieces against the engine, the probes and the design's own rules."""
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
sys.path.insert(0, str(LANE / "probes"))

from me001 import design as D  # noqa: E402
from me001 import worker as W  # noqa: E402
from me001.policies import Arbiter, Tap  # noqa: E402
from mse.assay import Noise, enrol, read  # noqa: E402
from mse.engine import ROUTES, State, run  # noqa: E402
from mse.native import NATIVE  # noqa: E402

CASES = enrol([900990], D.MESSAGES, D.PARENTS, "engineering")


def test_design_shape():
    assert len(D.CONDITIONS) == 28 and len(D.SINGLE) == 19 and len(D.ARMS) == 41
    assert len({a.name for a in D.ARMS}) == len(D.ARMS)
    names = set(D.ARM) | set(D.PACKETS)
    assert all(a in names and b in names for _, a, b in D.CONTRASTS)
    for lvl, perm in D.PERMUTATIONS.items():
        assert sorted(perm) == list(range(len(perm))) and all(p != i for i, p in enumerate(perm))
    assert all(sum(s.updates for s in a.segments) == D.WINDOW for a in D.ARMS)
    assert D.digest() == D.digest()
    lo, hi = D.IDENTITIES["development"]
    assert all(b in range(910000, 911000) for b in range(lo, hi))
    eng = [range(*D.IDENTITIES[k]) for k in ("calibration", "preflight")]
    assert not set(eng[0]) & set(eng[1]) and all(b in range(900900, 901000) for r in eng for b in r)


def test_precomputed_draws_equal_chunked_noise():
    Z = W.draws(CASES, "future", updates=250)
    noise = Noise(D.TAG, CASES, "future")
    assert all(np.array_equal(noise(t), Z[t - 1]) for t in range(1, 251))


def test_batched_reader_equals_assay_read():
    rng = np.random.default_rng(3)
    packets = rng.normal(size=(len(CASES), 16, 16))
    th = rng.normal(scale=0.2, size=(len(CASES), 16, 16))
    births, Z = W.recipients(CASES)
    ours = W.read_batch(packets, np.arange(len(CASES)), th, births, Z, NATIVE)
    theirs = read(D.TAG, CASES, packets, th, recipients=D.RECIPIENTS, updates=D.READ_UPDATES)
    assert np.array_equal(ours, theirs)
    # a case's reading depends on its packet and address only, not on its batch neighbours
    idx = np.array([3, 3, 0])
    again = W.read_batch(packets[idx], idx, th, births, Z, NATIVE)
    assert np.array_equal(again[0], ours[3]) and np.array_equal(again[2], ours[0])


def test_arbiter_matches_probe_p4b():
    import p4b_scale_trigger as probe
    rng = np.random.default_rng(5)
    n = 12
    ours, theirs = Arbiter(n, 0.01, 0.002), probe.ScaleArbiter(n, 0.01, 0.002, "region")
    for _ in range(400):
        Vt = rng.normal(size=(n, 16, 16))
        R = Vt + rng.normal(scale=rng.choice([0.05, 0.6]), size=(n, 16, 16))
        ema = Vt + rng.normal(scale=rng.choice([0.05, 0.3], p=[0.97, 0.03]), size=(n, 16, 16))
        (g1, r1), (g2, r2) = ours(Vt, ema, R), theirs(Vt, ema, R)
        assert np.array_equal(g1, g2) and np.array_equal(r1, r2)
    assert np.array_equal(ours.bursts, theirs.bursts) and ours.bursts.sum() > 0


def test_tap_is_bit_exact():
    rng = np.random.default_rng(7)
    V = rng.normal(size=(4, 16, 16))
    s = State(V, V.copy(), V + 0.1, np.zeros_like(V))
    th = rng.normal(scale=0.2, size=(4, 16, 16))
    Z = rng.normal(size=(60, 4, 16, 16))
    plain = run(s.copy(), th, lambda t: Z[t - 1], ROUTES["reciprocal"], 60)
    tapped = run(s.copy(), th, lambda t: Z[t - 1], ROUTES["reciprocal"], 60, policy=Tap(4))
    assert all(np.array_equal(getattr(plain, k), getattr(tapped, k)) for k in ("V", "ema", "R", "Q"))


def test_window_covariance():
    from scipy.linalg import solve_discrete_lyapunov
    from me001.predict import window_covariance
    rng = np.random.default_rng(11)
    A = rng.normal(size=(20, 20))
    A *= 0.9 / np.abs(np.linalg.eigvals(A)).max()
    B = rng.normal(size=(20, 20))
    Q = B @ B.T
    explicit = sum(np.linalg.matrix_power(A, k) @ Q @ np.linalg.matrix_power(A, k).T for k in range(5))
    np.testing.assert_allclose(window_covariance(A, Q, 5), explicit, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(window_covariance(A, Q, 1000), solve_discrete_lyapunov(A, Q), rtol=1e-8, atol=1e-10)


def test_write_window_schedule():
    """write20: comparison off and R rewritten at BURST_RATE for 20 updates, then R held."""
    rng = np.random.default_rng(9)
    n = len(CASES)
    V = rng.normal(size=(n, 16, 16))
    starts = [State(V, V.copy(), V + rng.normal(size=V.shape), np.zeros_like(V))]
    th = rng.normal(scale=0.2, size=(n, 16, 16))
    Zf = rng.normal(size=(D.WINDOW, n, 16, 16))
    arm = D.ARM["write20_site"]
    end, ledger, early, tap, inner = W.run_arm(arm, starts, (0,), th, Zf, NATIVE, None)
    check = D.Arm("w", "t", (D.Segment(D.BURST_UPDATES, reference=D.ch("site"), policy="burst"),
                              D.Segment(D.WINDOW - D.BURST_UPDATES)))
    held, *_ = W.run_arm(check, starts, (0,), th, Zf, NATIVE, None)
    s = State(V.copy(), V.copy(), starts[0].R.copy(), np.zeros_like(V))
    for t in range(1, D.BURST_UPDATES + 1):
        s = run(s, th, lambda u, t=t: Zf[t - 1], W.route(check.segments[0], "body"), 1, NATIVE,
                policy=lambda *x: (0.0, D.BURST_RATE))
    assert np.array_equal(held.R, s.R) and np.array_equal(end.R, s.R)
    assert ledger.ref_l1.min() > 0 and set(early) == set(D.EARLY)
