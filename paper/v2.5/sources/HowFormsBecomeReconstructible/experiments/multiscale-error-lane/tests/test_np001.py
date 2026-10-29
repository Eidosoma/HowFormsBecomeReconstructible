"""NP001's tests: python -m pytest tests/test_np001.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl001 import sim as S  # noqa: E402
from dl002 import sim as S2  # noqa: E402
from lr002 import design as L2  # noqa: E402
from lr002 import sim as L2S  # noqa: E402
from np001 import design as D  # noqa: E402
from np001 import predict as P  # noqa: E402
from np001 import sim  # noqa: E402
from np001 import worker as W  # noqa: E402

BLOCK = 900634
WIN = 150


def prepared(pattern="S4"):
    return sim.prepare(pattern, BLOCK, "engineering")


def test_design():
    assert len(D.UNITS) == 9 and len(D.tasks()) == 36 and len(D.CONDS) == 6 and len(D.digest()) == 64
    assert D.BODIES == D.SUCC_BODIES == ("dw", "li2", "li4", "li16") and D.CONFLICTS == ("C4s1", "C4s2", "C4s3")
    assert D.IDENTITIES["development"] == (910320, 910336)
    assert all(900000 <= lo < hi <= 901000 for lo, hi in (D.PROBE_BLOCKS, D.IDENTITIES["preflight"], D.DEBUG_BLOCKS))
    assert [c.name for c in D.HANDED] == ["intact", "body1", "record1", "body", "body3"]
    assert D.CONDS[0].gain == 0.0 and all(c.gain == D.GAIN == 0.2 for c in D.HANDED)
    assert [(c.rate, c.learn, c.parity) for c in D.CONDS] == [(0.0, "", False), (0.0, "", False), (0.001, "body", False),
                                                              (0.001, "record", True), (0.01, "body", False),
                                                              (0.03, "body", False)]
    assert W.BRANCHES2 == ("intact", "body1", "record1", "body", "body3", "none")
    assert [D.shift_of(u) for u in D.UNITS] == [0, 1, 2, 3, 0, 0, 1, 2, 3]
    assert [D.is_conflict(u) for u in D.UNITS] == [False] * 6 + [True] * 3


def test_shift_templates():
    for X in (1, 2, 3):
        for kind in range(4):
            a, b = sim.template(f"S4s{X}", kind, BLOCK), sim.template("S4", kind, BLOCK)
            assert abs((a == b).mean() - (1 - X / 4)) < 1e-12
            assert abs(S.best_shift(a[None], b[None])[0] - 1) < 1e-12
    assert np.array_equal(sim.template("S4", 1, BLOCK), S2.template("S4", 1, BLOCK))


def test_prepare_s4_is_dl002s():
    a, b = prepared("S4"), S2.prepare("S4", BLOCK, "engineering")
    assert all(np.array_equal(x, y) for x, y in zip(a[1:], b[1:]))
    cases, V0, ema0, R0, th, T = prepared("S4s2")
    assert S.sign(V0, T).mean() > 0.90 and abs(S.sign(V0, b[5]).mean() - 0.5) < 0.05
    assert np.array_equal(S.sign(R0, T), np.ones(len(cases))) and np.array_equal(S.sign(R0, b[5]), np.full(len(cases), 0.5))


def test_conflict_preparation():
    s4, s4s2, c = prepared("S4"), prepared("S4s2"), prepared("C4s2")
    for i in (1, 2, 4):                                     # the body, its moving average and theta: S4's (phase 0)
        assert np.array_equal(c[i], s4[i])
    for i in (3, 5):                                        # the record and the history: S4s2's (phase 2)
        assert np.array_equal(c[i], s4s2[i])
    T0 = sim.initial("C4s2", c[0], BLOCK)
    assert np.array_equal(T0, s4[5]) and np.array_equal(sim.initial("S8", c[0], BLOCK), prepared("S8")[5])
    o = sim.stage1("li4", D.CONDS[:2], c[0], *c[1:], {WIN}, window=WIN, T0=T0)
    o2 = sim.stage1("li4", D.CONDS[:2], c[0], *c[1:], {WIN}, window=WIN)
    assert all(np.array_equal(o[x], o2[x]) for x in ("V", "r", "H", "W", "align", "r_align"))   # T0 only scores
    assert np.array_equal(o2["align_b"], o2["align"]) and not np.array_equal(o["align_b"], o["align"])


def test_stage1_equals_lr002():
    cases, V0, ema0, R0, th, T = prepared("S4")
    conds = tuple(L2.Cond(c.rate, c.repair) for c in D.HANDED)
    for body in ("li4", "dw"):
        o = sim.stage1(body, D.CONDS, cases, V0, ema0, R0, th, T, {WIN}, window=WIN)
        ref = L2S.run(body, conds, cases, V0, ema0, R0, th, T, D.THETA, {WIN}, tag=D.TAG, kc=D.KC, window=WIN)
        k = len(cases)
        for x in ("V", "r", "H", "W"):
            assert np.array_equal(o[x][k:], ref[x])
        assert np.array_equal(o["align"][0][k:], ref["sign"][0]) and np.array_equal(o["r_align"][0][k:], ref["r_sign"][0])


def test_alone_reads_nothing_and_records_ignore_the_body():
    cases, V0, ema0, R0, th, T = prepared("F0")
    k = len(cases)
    outs = {b: sim.stage1(b, D.CONDS, cases, V0, ema0, R0, th, T, {WIN}, window=WIN) for b in ("li4", "dw")}
    for c in ("alone", "intact", "record1"):
        j = D.CONDNAMES.index(c)
        for x in ("r", "H", "W"):
            assert np.array_equal(outs["li4"][x][j * k:(j + 1) * k], outs["dw"][x][j * k:(j + 1) * k])
    j = D.CONDNAMES.index("body")
    assert not np.array_equal(outs["li4"]["r"][j * k:(j + 1) * k], outs["dw"]["r"][j * k:(j + 1) * k])
    blank = sim.stage1("li4", (D.CONDS[0],), cases, V0, ema0, R0 * 0 + 1.0, th, T, {WIN}, window=WIN)
    assert np.array_equal(blank["V"], outs["li4"]["V"][:k])           # a gain-0 body ignores what the record holds


def test_successor_pairing_and_control():
    cases, V0, ema0, R0, th, T = prepared("S8")
    k = len(cases)
    o = sim.stage1("dw", D.CONDS[1:2], cases, V0, ema0, R0, th, T, {WIN}, window=WIN)
    r, H, Wb = (np.tile(o[x], (3, 1, 1)) for x in ("r", "H", "W"))
    for B in ("dw", "li4"):
        o2 = sim.successor(B, r, H, Wb, cases, th, T, {WIN}, [D.GAIN, D.GAIN, 0.0], window=WIN)
        assert np.array_equal(o2["V"][:k], o2["V"][k:2 * k])
        o3 = sim.successor(B, r * 0, H, Wb, cases, th, T, {WIN}, [D.GAIN, D.GAIN, 0.0], window=WIN)
        assert np.array_equal(o2["V"][2 * k:], o3["V"][2 * k:])        # the control reads nothing
        assert not np.array_equal(o2["V"][:k], o2["V"][2 * k:])


def test_handed_records_and_statements():
    k = 2
    fake = {x: np.arange(len(D.CONDS) * k)[:, None, None] * np.ones((1, D.SIDE, D.SIDE)) for x in ("r", "H", "W")}
    r, H, Wb = W.handed(fake, k)
    assert r.shape == (len(W.BRANCHES2) * k, D.SIDE, D.SIDE)
    assert [int(r[i * k, 0, 0]) // k for i in range(len(W.BRANCHES2))] == W.HANDED_IX + W.HANDED_IX[:1]
    assert {s["id"] for s in P.STATEMENTS} == {f"N{i}" for i in range(1, 10)} and all("{" not in s["rule"] for s in P.STATEMENTS)
    assert {p["stmt"] for p in P.PARTS} == {s["id"] for s in P.STATEMENTS}
