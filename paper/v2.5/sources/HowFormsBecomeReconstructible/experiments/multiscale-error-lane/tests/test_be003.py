"""BE003's tests: python -m pytest tests/test_be003.py"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be002 import sim as B2S  # noqa: E402
from be003 import design as D  # noqa: E402
from be003 import sim  # noqa: E402
from cellpop import core as C  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from sc002 import sim as S2  # noqa: E402

BLOCK = 900676
SC002_ARMS = ("cue", "inst-1.5", "inst-3", "mat-300", "mat-1000")


def test_design():
    assert D.UNITS == ("S4_t0", "F0_t0") and len(D.RUNS) == 7 and set(D.JUNCTIONS) < set(D.ARMS)
    assert D.SIGNAL_ARMS == ("dial", "mat-dial") and D.run_arms("regrow", 0, "late") == D.SIGNAL_ARMS
    assert D.IDENTITIES["development"] == (910220, 910236) and len(D.digest()) == 64
    assert all(lo >= 900670 and hi <= 900678 for lo, hi in (D.PROBE_BLOCKS, D.IDENTITIES["preflight"], D.DEBUG_BLOCKS))
    assert D.on_window("regrow", 0, "prompt") == (1, 1000) and D.on_window("regrow", 0, "late") == (1001, 2000)
    assert D.on_window("twin", 300, "prompt") == (301, 1300)
    assert D.run_reads("twin", 1000, "prompt") == (1250, 2000, 3000) and D.run_window("twin", 1000, "prompt") == 3000
    assert all(d + D.HORIZON in D.READS for d in D.DELAYS)          # every twin run's counterfactual is read in regrow8


def test_regions():
    cases = sim.prepare("S4", BLOCK, "engineering")[0]
    reg = sim.regions(cases, D.TAG)
    for x, n in (("in", 64), ("young", 16), ("twin", 16), ("ring", 80)):
        assert (reg[x].sum((-2, -1)) == n).all()
    assert (reg["young"] <= reg["in"]).all() and np.array_equal(B2S.footprint(reg["young"], 2), reg["in"])
    assert not (reg["twin"] & B2S.footprint(reg["in"], 9)).any()
    assert not (reg["out"] & (reg["in"] | reg["ring"] | reg["twin"])).any()


def test_without_the_signal_equals_sc002():
    """The arms without the signal in the regrowing wound are sc002.sim.run's panel W arms bit for bit."""
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    for body, s in (("li4", "regrow"), ("dw", "regrow+cue")):
        a = sim.run(body, s, 0, "prompt", cases, V0, ema0, R0, th, T, 0.0, {150}, window=150, arms=SC002_ARMS)
        b = S2.run(body, 0.0, s, 8, cases, V0, ema0, R0, th, T, 0.0, {150}, tag=D.TAG, window=150, arms=SC002_ARMS)
        for x in ("V", "r", "H", "W", "occ"):
            assert np.array_equal(a[x], b[x])


def test_full_sheet_dial_equals_be002():
    """On a full sheet the dial is BE002's local dial (conjugate gradients against BE002's sparse LU)."""
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    a = sim.run("dw", "change", 0, "prompt", cases, V0, ema0, R0, th, T, 0.0, {150}, window=150, arms=("inst-3", "dial"), size=4)
    b = B2S.run("dw", "change", 4, "sig", cases, V0, ema0, R0, th, T, 0.0, {150}, tag=D.TAG, window=150, arms=("bio-3", "dial-local"))
    for x in ("V", "r", "H", "W"):
        assert np.abs(a[x] - b[x]).max() <= 1e-9
    assert a["solvers"]["dial"] == {"fft": 0, "cg": 150} and a["solvers"]["inst-3"] == {"fft": 150, "cg": 0}


def test_signal_off_and_arm_independence():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    o = sim.run("li4", "twin", 20, "prompt", cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, on=(0, -1),
                arms=("inst-3", "mat-300", "dial", "mat-dial"))
    for x in ("V", "r", "H", "W"):
        assert np.array_equal(o[x][:k], o[x][2 * k:3 * k]) and np.array_equal(o[x][k:2 * k], o[x][3 * k:])
    a = sim.run("dw", "regrow", 0, "late", cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, on=(40, 90), arms=D.SIGNAL_ARMS)
    b = sim.run("dw", "regrow", 0, "late", cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, on=(40, 90), arms=D.ARMS)
    i0 = D.ARMS.index("dial")
    for x in ("V", "r", "H", "W"):
        assert np.array_equal(a[x], b[x][i0 * k:(i0 + 2) * k])


def test_twin_run_is_regrow8_until_the_change():
    """Before update d + 1 a twin run's arms without the signal are regrow8's, and its signal arms their aliases'."""
    cases, V0, ema0, R0, th, T = sim.prepare("F0", BLOCK, "engineering")
    k = len(cases)
    tw = sim.run("dw", "twin", 120, "prompt", cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=D.ARMS)
    rg = sim.run("dw", "regrow", 0, "prompt", cases, V0, ema0, R0, th, T, 0.0, {120}, window=120, arms=D.ARMS)
    for ai, arm in enumerate(D.ARMS):
        ref = D.ARMS.index(D.ALIAS.get(arm, arm))
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(tw[x][ai * k:(ai + 1) * k], rg[x][ref * k:(ref + 1) * k]), (arm, x)


def test_change_and_signal_timing():
    cases, V0, ema0, R0, th, T = sim.prepare("S4", BLOCK, "engineering")
    reg = sim.regions(cases, D.TAG)
    am = L5S.anchor_mask(cases, D.TAG)
    base = np.where(R0 > 0, 1.0, -1.0)
    log = []

    def observe(t, st, states, ageH, ageW, born, is_on, aval, fp):
        log.append((t, is_on, bool(np.array_equal((aval != base) & am, am & (reg["young"] | reg["twin"]))),
                    bool(((aval != base) & am).any()), bool(np.array_equal(fp, reg["in"] | B2S.footprint(reg["twin"], 2)))))

    sim.run("dw", "twin", 30, "prompt", cases, V0, ema0, R0, th, T, 0.0, {40}, window=40, arms=("cue",), observe=observe)
    for t, on, exact, anyflip, fp_ok in log:
        assert on == (t >= 31) and fp_ok
        assert (exact and anyflip) if t >= 31 else not anyflip


def test_signal_conductances():
    rng = np.random.default_rng(3)
    occ = rng.random((2, D.SIDE, D.SIDE)) > 0.05
    aH, aW = rng.integers(0, 900, occ.shape).astype(float), rng.integers(0, 900, occ.shape).astype(float)
    fp = np.zeros(occ.shape, bool)
    fp[:, 5:15, 5:15] = True
    touch = C.touching(fp)
    ch, cw = C.contacts(occ)
    m = S2.maturity(aH, 300.0)
    gH, _ = sim.conductance("mat-dial", aH, aW, occ, touch)
    assert np.array_equal(gH, np.where(ch, np.where(touch[0], 1.0, 9.0) * m, 0.0))
    gH0, _ = sim.conductance("mat-dial", aH, aW, occ)
    assert np.array_equal(gH0, sim.conductance("mat-300", aH, aW, occ)[0])
    gI, _ = sim.conductance("dial", aH, aW, occ, touch)
    assert set(np.unique(gI[ch])) <= {1.0, 9.0} and (gI[~ch] == 0.0).all()


def test_static_map_frozen():
    st = json.loads((Path(__file__).resolve().parents[1] / "be003" / "frozen" / "static_map.json").read_text())
    assert st["design_digest"] == D.digest()
    assert st["self_reading_newborns"]["mat-300"] == 1.0 and st["self_reading_newborns"]["inst-3"] == 0.0
    assert set(st["adoption"]) == set(D.JUNCTIONS) and all(str(d) in st["adoption"]["mat-300"] for d in D.DELAYS if d)
