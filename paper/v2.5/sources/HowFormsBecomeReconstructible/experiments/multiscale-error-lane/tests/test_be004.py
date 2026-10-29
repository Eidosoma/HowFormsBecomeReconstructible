"""BE004's tests: python -m pytest tests/test_be004.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be002 import sim as B2S  # noqa: E402
from be004 import design as D  # noqa: E402
from be004 import sim  # noqa: E402
from lr005 import sim as L5S  # noqa: E402

BLOCK = 900686
W = 150


def prepared(pattern="S4"):
    return sim.prepare(pattern, BLOCK, "engineering")


def test_design():
    assert len(D.UNITS) == 6 and len(D.tasks()) == 12 and len(D.RUNS) == 9 and len(D.digest()) == 64
    assert len(D.SIGNAL_ARMS) == 15 and D.SIGNAL_ARMS["dial-t1"]["dur"] == 1 and D.BASE["dur"] == D.SIG["duration"]
    assert D.IDENTITIES["development"] == (910240, 910256)
    assert all(lo >= 900680 and hi <= 900688 for lo, hi in (D.PROBE_BLOCKS, D.IDENTITIES["preflight"], D.DEBUG_BLOCKS))
    assert D.SIGNAL_ARMS["dial"] == D.BASE and all(set(p) == set(D.BASE) for p in D.SIGNAL_ARMS.values())
    assert sum(p != D.BASE for p in D.SIGNAL_ARMS.values()) == len(D.SIGNAL_ARMS) - 1     # each varies one property
    for a, p in D.SIGNAL_ARMS.items():
        assert sum(p[x] != D.BASE[x] for x in D.BASE) == (0 if a == "dial" else 1)
    assert D.on_window("memory", 4, 0) == (1, 1000) and D.on_window("memory", 4, 1000) == (1001, 2000)
    assert all(d in D.READS and d + 1000 in D.READS for d in D.DELAYS if d) and D.READS[-1] == D.WINDOW
    assert len(set(D.RUNNAMES)) == len(D.RUNS)


def test_footprints():
    cases = prepared()[0]
    m = sim.patch(cases, 4, D.TAG)
    for a, cells in (("dial", 64), ("dial-d0", 16), ("dial-d4", 144), ("dial-d8", 400), ("dial-s4", 64)):
        assert (sim.arm_footprint(a, m).sum((-2, -1)) == cells).all()
    assert np.array_equal(sim.arm_footprint("dial-d0", m), m)
    assert np.array_equal(sim.arm_footprint("dial", m), B2S.footprint(m))
    assert np.array_equal(sim.arm_footprint("dial-s6", m), np.roll(B2S.footprint(m), 6, -1))
    assert not (sim.arm_footprint("dial-s6", m) & m).any() and (sim.arm_footprint("dial-s4", m) & m).sum((-2, -1)).tolist() == [8] * len(cases)


def test_base_arms_equal_be002():
    """cue, bio-1, bio-3 and the dial are be002.sim.run's cue, bio-1, bio-3 and dial-local bit for bit (prompt and late)."""
    cases, V0, ema0, R0, th, T = prepared("LB")
    k = len(cases)
    for body, situation, onw in (("dw", "memory", (1, 100)), ("li4", "change", (1, 100)), ("dw", "cue", (51, 150))):
        b2 = ("cue", "bio-1", "bio-3", "dial-local")
        a = sim.run(body, situation, 4, onw[0] - 1, ("cue", "bio-1", "bio-3", "dial"), cases, V0, ema0, R0, th, T, 1.0, {W},
                    window=W, on_window=onw)
        b = B2S.run(body, situation, 4, "", cases, V0, ema0, R0, th, T, 1.0, {W}, tag=D.TAG, window=W, arms=b2, on_window=onw)
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(a[x], b[x])
        assert a["V"].shape[0] == 4 * k


def test_hold_is_the_dial_with_nothing_to_hold():
    cases, V0, ema0, R0, th, T = prepared()
    o = sim.run("li4", "memory", 4, 0, ("dial", "dial-hold"), cases, V0, ema0, R0, th, T, 0.0, {W}, window=W)
    k = len(cases)
    for x in ("V", "r", "H", "W"):
        assert np.array_equal(o[x][:k], o[x][k:])


def test_hold_keeps_the_sensors_unrepaired_while_pending():
    """During the wait the hold's anchored cells in the patch keep the damaged record at least as often as the dial's,
    and the evidence at the onset is at least the dial's."""
    cases, V0, ema0, R0, th, T = prepared("F0")
    k = len(cases)
    o = sim.run("dw", "memory", 4, 120, ("dial", "dial-hold"), cases, V0, ema0, R0, th, T, 0.0, {120}, window=121)
    assert o["n_anc_ok"][0][k:].sum() <= o["n_anc_ok"][0][:k].sum()
    assert o["onset"][k:].sum() >= o["onset"][:k].sum() and (o["onset"] >= 0).all()


def test_without_the_signal_every_dial_is_bio3():
    cases, V0, ema0, R0, th, T = prepared()
    arms = ("bio-3", "dial-s4", "dial-d8", "dial-w2", "dial-f0.5", "dial-hold")
    o = sim.run("dw", "change", 4, 0, arms, cases, V0, ema0, R0, th, T, 0.0, {W}, window=W, on_window=(0, -1))
    k = len(cases)
    for j in range(1, len(arms)):
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(o[x][:k], o[x][j * k:(j + 1) * k])


def test_flicker():
    cases = prepared()[0]
    u = sim.flicker(cases, 4000, D.TAG)
    on5, on25 = u < 0.5, u < 0.25
    assert (on25 <= on5).all() and abs(on5.mean() - 0.5) < 0.02 and abs(on25.mean() - 0.25) < 0.02
    assert np.array_equal(u, sim.flicker(cases, 4000, D.TAG))


def test_flicker_always_on_is_the_dial():
    """A flicker arm whose draws are all below p is the dial: the per-case path equals the steady path."""
    cases, V0, ema0, R0, th, T = prepared()
    k = len(cases)
    old = D.SIGNAL_ARMS["dial-f0.5"]["p_on"]
    try:
        D.SIGNAL_ARMS["dial-f0.5"]["p_on"] = 0.999999999
        o = sim.run("li4", "change", 4, 0, ("dial", "dial-f0.5"), cases, V0, ema0, R0, th, T, 0.0, {W}, window=W)
    finally:
        D.SIGNAL_ARMS["dial-f0.5"]["p_on"] = old
    u = sim.flicker(cases, W, D.TAG)
    if (u < 0.999999999).all():
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(o[x][:k], o[x][k:])


def test_endpoints_shapes_and_counts():
    cases, V0, ema0, R0, th, T = prepared()
    k = len(cases)
    arms = ("cue", "bio-3", "dial", "dial-d8")
    o = sim.run("dw", "change", 4, 0, arms, cases, V0, ema0, R0, th, T, 0.0, {50, W}, window=W)
    for e in sim.ENDS:
        assert o[e].shape == (2, len(arms) * k)
    ev = sim.event("change", 4, cases, V0, ema0, R0, T, D.TAG)
    assert np.array_equal(o["n_anc"], (ev["m"] & ev["am"]).sum((-2, -1)).astype(float))
    assert ((o["n_anc_ok"] >= 0) & (o["n_anc_ok"] <= np.tile(o["n_anc"], len(arms)))).all()
    assert (o["onset"][:2 * k] == -1).all() and (o["onset"][2 * k:] >= 0).all()
    assert np.allclose(o["r_in"][-1], L5S.inside(o["r"], np.tile(ev["target"], (len(arms), 1, 1)), np.tile(ev["m"], (len(arms), 1, 1))))


def test_brief_signals_and_counts():
    cases, V0, ema0, R0, th, T = prepared()
    k = len(cases)
    o = sim.run("dw", "change", 4, 0, ("dial", "dial-t1", "dial-t10", "dial-t100"), cases, V0, ema0, R0, th, T, 0.0, {W},
                window=W)
    assert o["signal_updates"] == {"dial": W * k, "dial-t1": k, "dial-t10": 10 * k, "dial-t100": 100 * k}


def test_arms_are_independent():
    """An arm's branch does not depend on which other arms share its run."""
    cases, V0, ema0, R0, th, T = prepared("F0")
    k = len(cases)
    a = sim.run("li4", "change", 4, 0, ("dial-f0.25",), cases, V0, ema0, R0, th, T, 1.0, {W}, window=W)
    b = sim.run("li4", "change", 4, 0, ("cue", "bio-3", "dial-t10", "dial-f0.25", "dial-s4"), cases, V0, ema0, R0, th, T, 1.0,
                {W}, window=W)
    for x in ("V", "r", "H", "W"):
        assert np.array_equal(a[x], b[x][3 * k:4 * k])
