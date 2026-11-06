"""E2E004's tests (engineering; no successor value is read)."""
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from e2e004 import design as D  # noqa: E402
from e2e004 import predict as PR  # noqa: E402
from e2e004 import sim  # noqa: E402
from e2e004 import worker as WK  # noqa: E402
from lr005 import sim as L5S  # noqa: E402


def _prep(block=900729, unit="F0_t1"):
    pattern, theta = A.parse_unit(unit)
    return A1S.prepare(pattern, block, "engineering"), theta


def test_stages_and_tasks():
    assert len(D.stage_tasks("probe")) == 32 and len(D.stage_tasks("development")) == 128
    assert len(D.stage_tasks("debug")) == 8 and len(D.stage_tasks("preflight")) == 16
    for stage in D.STAGES:
        for src in D.STAGES[stage]:
            M = json.loads((Path(D.SOURCES[src]["root"]) / "manifest.json").read_text())
            for s, b, u, blk in D.stage_tasks(stage):
                if s == src:
                    assert f"{b}/{u}/{blk}" in M["tasks"]
    assert D.digest() == D.digest() and len(D.digest()) == 64


def test_lineages_declared():
    labels = [x["label"] for x in D.ALL]
    assert len(labels) == len(set(labels))
    for x in D.ALL:
        assert x["route"] in D.ROUTES and x["stop"] in (D.G_SIDE, D.G_MAIN)
    for pid, _w, _fn, _k in PR.parts():
        assert pid in ("G1", "G2", "G3", "G4")
    core = {x["label"] for x in D.CORE}
    assert {PR.B_P, PR.V_P, PR.R_P, PR.B_X, PR.V_X, PR.R_X} == core


def test_groups_partition_the_branches():
    g = sim.groups_of(["record", "vote", "body", "vote"], 4)
    assert [r for r, _ix in g] == ["body", "vote", "record"]
    ix = np.sort(np.concatenate([i for _r, i in g]))
    assert np.array_equal(ix, np.arange(16))
    assert list(dict(g)["vote"]) == list(range(4, 8)) + list(range(12, 16))


def test_generation_is_ar001_at_a_short_window():
    (cases, V0, ema0, R0, th, T), theta = _prep()
    arms = ["record", "body", "vote"]
    V, E, A_, B_ = sim.replay0("li4", "memory@0", arms, cases, V0, ema0, R0, th, T, theta, "mse-p53", window=40)
    res = A1S.run("li4", "memory", 0.0, arms, cases, V0, ema0, R0, th, T, theta, {40}, tag="mse-p53", window=40)
    for x, mine in (("V", V), ("r", A_[4]), ("H", A_[0]), ("W", A_[1])):
        assert np.array_equal(res[x], mine), x
    for x, mine in (("rB", B_[4]), ("HB", B_[0]), ("WB", B_[1])):
        assert np.array_equal(res[x], mine), x


def test_vote1_is_vote2r_with_the_second_copy_abstaining():
    rng = np.random.default_rng(1)
    V, r = rng.normal(0, 0.6, (3, D.SIDE, D.SIDE)), rng.normal(0, 0.6, (3, D.SIDE, D.SIDE))
    xh, xw, _ = L5S.targets("vote2r", V, r, np.zeros_like(r), None, None)
    sv, sr = L5S.vote_sign(V), L5S.vote_sign(r)
    a, b = L5S.rel(sv), L5S.rel(sr)
    assert np.array_equal(xh, np.sign(a[0] + b[0])) and np.array_equal(xw, np.sign(a[1] + b[1]))
    assert ((xh == 0) == ((a[0] + b[0]) == 0)).all()       # a tie (disagreement) is a target of 0: the bond is held


def test_packets_alias_by_route():
    raw, meta, _ = WK.load("ar005/debug", "dw", "S4_t0", 900799)
    pattern, _theta = A.parse_unit("S4_t0")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, 900799, "engineering")
    L = D.L
    lins = (L("a", "protected", "vote", 8), L("b", "protected", "vote", 3), L("c", "protected", "body", 8),
            L("d", "post/memory@0", "vote", 8))
    rows, labels, aliases, sources = sim.packets(raw, meta, cases, V0, ema0, R0, T, lins)
    assert labels["a"] == labels["b"] and len({labels[x] for x in "acd"}) == 3
    assert rows[labels["a"]]["stop"] == 8 and aliases == {"a": ["b"]}
    assert sources["d"] == "post/memory@0" and sources["a"] == "protected"


def test_rule_helpers():
    assert PR.narrowest(0.30, 0.05, [0.28, 0.31], "ge") == 0.21
    assert PR.registers("ge", 0.0) is False and PR.registers("in", [-0.01, 0.01]) is True
    v = PR.value(np.ones((4, 4)), [900729, 900739, 900749, 900759], "probe")
    assert v["sd"] == 0 and v["halves"] == [1.0, 1.0]
