"""ME002 unit checks: the generalised arbiter, the event loop, clamps, schedules and the design."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from me001.policies import Arbiter as Arbiter001
from me002 import design as D
from me002 import sim
from me002.policies import Arbiter2, Gain, Oracle2
from mse.assay import Noise, acquire, enrol
from mse.engine import ROUTES, Route, State, run
from mse.native import NATIVE

BLOCK = [900994]


def test_design_shape():
    assert len(D.tasks()) == sum(len(v["regimes"]) for v in D.PANELS.values())
    for p, v in D.PANELS.items():
        names = [a.name for a in v["arms"]]
        assert len(names) == len(set(names)), p
        for fam, a, b in ((c[1], c[2], c[3]) for c in D.CONTRASTS if c[0] == p):
            known = set(names) | set(v.get("packets", ()))
            assert a in known and b in known, (p, fam, a, b)
    for f, T in D.TEMPLATES.items():
        assert T.shape == (4, 16, 16) and all((t > 0).sum() == 128 for t in T), f
        assert np.array_equal(T[2], -T[0]) and np.array_equal(T[3], -T[1])
    assert len(set(map(tuple, (D.IDENTITIES[k] for k in D.IDENTITIES)))) == 3


def test_arbiter2_equals_me001_rule():
    rng = np.random.default_rng(3)
    n = 6
    a, b = Arbiter001(n, 0.3, 0.02), Arbiter2(n, 0.3, 0.02)
    for t in range(400):
        scale = 1.5 if t % 97 < 3 else 0.3
        Vt, ema, R = (rng.standard_normal((n, 16, 16)) * scale for _ in range(3))
        ga, ra = a(Vt, ema, R)
        gb, rb = b(Vt, ema, R)
        assert np.array_equal(ga, gb) and np.array_equal(ra, rb)
        for k in ("latch", "burst", "refractory", "bursts", "first"):
            assert np.array_equal(getattr(a, k), getattr(b, k)), k


def test_simulate_without_events_equals_engine_run():
    name = D.regime("F0", 0.3)
    cases, s0, th, p, T, Tf = sim.prepare(name, BLOCK, "engineering")
    Z = sim.draws(cases, "future", updates=60)
    idx = np.arange(len(cases))
    for arm in (D.ARM["C"]["hold_site"], D.ARM["C"]["reciprocal"], D.ARM["C"]["inactive"]):
        got, _, _ = sim.simulate(s0, th, Z, idx, p, 60, sim.route(arm))
        ref = run(s0, th, lambda t: Z[t - 1], sim.route(arm), 60, p)
        assert all(np.array_equal(getattr(got, f), getattr(ref, f)) for f in ("V", "ema", "R", "Q"))


def test_prepare_matches_assay_acquisition_for_half_planes():
    name = D.regime("F0", 0.1)
    cases, s0, th, p, T, Tf = sim.prepare(name, BLOCK, "engineering")
    s, th2 = acquire(D.TAG, enrol(BLOCK), D.SETTLE, D.TEACH, D.AMPLITUDE, p, (0, 0), per_tissue=True)
    s = run(s, th2, Noise(D.TAG, enrol(BLOCK), "release"), ROUTES["body"], D.RELEASE, p)
    assert np.array_equal(th, th2) and np.array_equal(s0.V, s.V) and np.array_equal(s0.R, s.R)


def test_events_fire_once_and_impositions_span_their_duration():
    name = D.regime("F0", 0.3)
    cases, s0, th, p, T, Tf = sim.prepare(name, BLOCK, "engineering")
    k = len(cases)
    conds = (D.SHAM, D.single("reference", "collective", 2), D.Condition("impose-5", (D.Event("impose", duration=5),)))
    tau = np.full(k, 3)
    prog = sim.condition_program(conds, cases, tau, Tf, 20)
    V, R = np.tile(s0.V, (3, 1, 1)), np.tile(s0.R, (3, 1, 1))
    changes = []
    for t in range(1, 12):
        V2, R2 = prog.apply(t, V, R)
        changes.append((t, bool((R2 != R).any()), bool((V2 != V).any())))
        V, R = V2, R2
    assert [t for t, dr, _ in changes if dr] == [3]
    imposed = (V[2 * k:] == np.tile(Tf, (1, 1, 1))).all()
    assert imposed


def test_clamps_are_exact_no_ops_without_damage():
    name = D.regime("F4", 0.3)
    cases, s0, th, p, T, Tf = sim.prepare(name, BLOCK, "engineering")
    Z = sim.draws(cases, "future", updates=40)
    idx = np.arange(len(cases))
    arm = D.ARM["D"]["hold_site"]
    ref, _, _ = sim.simulate(s0, th, Z, idx, p, 40, sim.route(arm))
    for level in ("site", "region", "sheet"):
        from me002.worker import backup
        got, _, _ = sim.simulate(s0, th, Z, idx, p, 40, sim.route(arm), clamp=(level, backup(s0.R, level)))
        assert np.array_equal(got.V, ref.V) and np.array_equal(got.R, ref.R), level


def test_native_gain_policy_is_bit_exact():
    name = D.regime("F0", 0.3)
    cases, s0, th, p, T, Tf = sim.prepare(name, BLOCK, "engineering")
    Z = sim.draws(cases, "future", updates=30)
    idx = np.arange(len(cases))
    arm = D.ARM["E"]["sign_sheet_site"]
    a, _, _ = sim.simulate(s0, th, Z, idx, p, 30, sim.route(arm))
    b, _, _ = sim.simulate(s0, th, Z, idx, p, 30, sim.route(arm), controller=Gain(NATIVE.gain))
    assert np.array_equal(a.V, b.V)


def test_oracle_schedule():
    k = 2
    conds = (D.SHAM, D.single("reference", "regional", 2), D.single("both", "regional", 2),
             D.Condition("impose-inf", (D.Event("impose", duration=0),)))
    tau = np.array([5, 9])
    on = sim.oracle_schedule(conds, tau, k, 60)
    o = Oracle2(on)
    assert on[:, :2].sum() == 0 and on[:, 4:6].sum() == 0
    assert on[4:24, 2].all() and on[8:28, 3].all() and on[:, 2].sum() == D.BURST_UPDATES
    assert on[24:44, 6].all() and on[28:48, 7].all()
    assert list(o.first) == [-1, -1, 5, 9, -1, -1, 25, 29]


def test_vote_is_a_no_op_until_a_record_differs_and_repairs_the_outlier():
    rng = np.random.default_rng(5)
    R = np.sign(rng.standard_normal((3, 16, 16))) * 1.2
    V = R + 0.3 * rng.standard_normal(R.shape)
    a, b = sim.vote(V, R, R.copy())
    assert np.array_equal(a, R) and np.array_equal(b, R)
    bad = R.copy()
    bad[0, 4:8, 8:12] -= 2.0                      # one region of record 1 in case 0
    a, b = sim.vote(V, bad, R.copy())
    assert np.array_equal(a, R) and np.array_equal(b, R)
    a, b = sim.vote(V, R.copy(), bad)            # the same injury to record 2
    assert np.array_equal(a, R) and np.array_equal(b, R)


def test_first_after():
    a = Arbiter2(3, 0.0, 1e9)
    a.starts = [(4, np.array([0, 1])), (30, np.array([1, 2]))]
    assert list(a.first_after(np.array([1, 10, 40]))) == [3, 20, -1]
