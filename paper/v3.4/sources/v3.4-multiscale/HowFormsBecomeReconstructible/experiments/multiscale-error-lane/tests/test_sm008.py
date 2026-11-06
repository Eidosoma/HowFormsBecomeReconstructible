"""SM008's package: the mixed layout (coverage, the case at each position, the roles), the preprint stress's mixing identity
and sm007.sim.run's update where the layouts coincide (short runs on a restored P53 task), and the reader's code paths on
a synthetic stage (random endpoints, no tissue outcome)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sm007 import sim as S7  # noqa: E402
from sm008 import design as D  # noqa: E402
from sm008 import predict as P  # noqa: E402
from sm008 import sim  # noqa: E402
from sm008 import worker as W  # noqa: E402


def test_layout_counts_coverage_and_positions():
    bc, ba, bg, bp, groups = sim.layout(D.FULL_SET)
    assert len(bc) == 22 * 64 + 16 + 3 * 64 + 4 * 64 and len(groups) == 22 * 8 + 2 + 3 * 8 + 4 * 8
    for ai, (lab, comp, _b, _k, _l) in enumerate(D.FULL_SET):
        s = ba == ai
        if comp == "iso8":
            assert list(bc[s]) == list(range(16))
            continue
        P_ = set(D.COMPOSITIONS[comp])
        assert np.array_equal(bc[s], (bg[s] + bp[s]) % 8 + 8 * np.isin(bp[s], list(P_)))
        k = len(P_)
        assert int((bc[s] >= 8).sum()) == 8 * k
        for role_cases, n_pos in ((bc[s][bc[s] >= 8], k), (bc[s][bc[s] < 8], 8 - k)):
            if n_pos:
                assert sorted(set(role_cases % 8)) == list(range(8))
                assert all(int((role_cases % 8 == j).sum()) == n_pos for j in range(8))
    assert sim.members("k1-corner", 3) == [11, 4, 5, 6, 7, 0, 1, 2]
    assert sim.members("k7-inner", 0) == [8, 1, 10, 11, 12, 13, 14, 15]
    assert D.POSITIONS == [(r, c) for r in range(2) for c in range(4)]
    labels = [a[0] for a in D.FULL_SET]
    assert len(labels) == len(set(labels))


def test_roles_and_cases_share_keys():
    cases, R0, thf, T, bridge, _rf = W.inputs("ar005/p53", "li4", 900729)
    assert all(bridge.values()) and len(cases) == 16
    assert [c.key() for c in cases[:8]] == [c.key() for c in cases[8:]]
    assert not np.array_equal(R0[:8], R0[8:]) and np.array_equal(thf[:8], thf[8:])
    assert D.ROLES == {"li4": ("S4_t1", "F0_t1"), "dw": ("F0_t1", "S4_t1")}


@pytest.fixture(scope="module")
def short_runs():
    cases, R0, thf, T, _b, _rf = W.inputs("ar005/p53", "li4", 900729)
    arrs = [a for a in D.FULL_SET if a[0] in ("k0/absorbing", "k8/absorbing", "k1-corner/absorbing", "iso8/absorbing",
                                              "k0/absorbing/paper", "k1-corner/absorbing/paper", "k8/absorbing/paper")]
    r8 = sim.run("li4", arrs, cases, R0, thf, T, D.PROBE_TAG, window=60, reads=(30, 60), trace_until=60)
    r7 = {role: S7.run("li4", [("2x4/absorbing", "2x4", "absorbing", "field", D.LAMBDA),
                               ("iso8/absorbing", "iso8", "absorbing", "field", D.LAMBDA),
                               ("2x4/absorbing/paper", "2x4", "absorbing", "paper", D.LAMBDA)],
                       cases[sl], R0[sl], thf[sl], T[sl], D.PROBE_TAG, window=60, reads=(30, 60))
          for role, sl in (("healthy", slice(0, 8)), ("struggling", slice(8, 16)))}
    return arrs, r8, r7


def test_pure_groups_equal_sm007(short_runs):
    arrs, r8, r7 = short_runs
    lab = [a[0] for a in arrs]
    for l8, role, l7 in (("k0/absorbing", "healthy", 0), ("k8/absorbing", "struggling", 0),
                         ("k0/absorbing/paper", "healthy", 2), ("k8/absorbing/paper", "struggling", 2)):
        s8 = (r8["br_arr"] == lab.index(l8)) & (r8["br_group"] == 0)
        s7 = r7[role]["br_arr"] == l7
        assert np.array_equal(r8["V"][s8], r7[role]["V"][s7]) and np.array_equal(r8["a_v"][:, s8], r7[role]["a_v"][:, s7])
    for role, gi in (("healthy", 0), ("struggling", 1)):
        s8 = (r8["br_arr"] == lab.index("iso8/absorbing")) & (r8["br_group"] == gi)
        assert np.array_equal(r8["V"][s8], r7[role]["V"][r7[role]["br_arr"] == 1])


def test_paper_mixing_identity(short_runs):
    arrs, r8, _r7 = short_runs
    lab = [a[0] for a in arrs]
    def at(label):
        ai = lab.index(label)
        return {(int(g), int(p)): i for i, (g, p) in enumerate(zip(r8["br_group"], r8["br_pos"])) if r8["br_arr"][i] == ai}
    mix, h0, s8 = at("k1-corner/absorbing/paper"), at("k0/absorbing/paper"), at("k8/absorbing/paper")
    for kk, i in mix.items():
        j = s8[kk] if r8["br_case"][i] >= 8 else h0[kk]
        assert np.array_equal(r8["V"][i], r8["V"][j])
        assert np.array_equal(r8["trace"]["exposure"][:, i], r8["trace"]["exposure"][:, h0[kk]])
    # and the ruled stress does feel the neighbours: the struggler at corner 0 differs between k1-corner and k8
    m1, m8 = at("k1-corner/absorbing"), at("k8/absorbing")
    assert not np.array_equal(r8["trace"]["exposure"][:, m1[(0, 0)]], r8["trace"]["exposure"][:, m8[(0, 0)]])


def _synthetic_stage(tmp, stage="probe"):
    rng = np.random.default_rng(5)
    bc, ba, bg, bp, _g = sim.layout(D.FULL_SET)
    n = len(bc)
    tasks = {}
    for blk in D.STAGES[stage]["ar005/p53"]:
        for body in D.BODIES:
            ends = {"reads": np.array(D.READS), "a_v": rng.uniform(0.5, 1, (4, n)), "sign": rng.uniform(0, 1, (4, n)),
                    "gain_mean": rng.uniform(0.05, 0.3, n), "expo_mean": rng.uniform(0, 3, n), "stress_mean": rng.uniform(0, 1, n),
                    "br_case": bc, "br_arr": ba, "br_group": bg, "br_pos": bp, "br_future": np.zeros(n, int)}
            meta = {"stage": stage, "block": blk, "body": body, "arrangements": [list(a) for a in D.FULL_SET]}
            path = tmp / f"{body}_{blk}.npz"
            np.savez(path, __meta__=np.array(json.dumps(meta)), **ends)
            tasks[f"ar005/p53/{body}/{blk}"] = {"files": {"shards": {"path": path.name, "sha256": P.sha(path)}}}
    (tmp / "manifest.json").write_text(json.dumps({"stage": stage, "tasks": tasks}))
    return tmp


def test_reader_on_a_synthetic_stage(tmp_path):
    root = _synthetic_stage(tmp_path)
    tasks, M = P.load(root)
    sc = P.score(tasks, th={})
    assert [p["id"] for p in sc] == ["X1", "X2", "X3", "X4", "X5", "X6"] and all(p["available"] for p in sc)
    assert all(p["n_blocks"] == 4 and p["n_cases_a_block"] == 8 for p in sc)
    rep = P.score_reported(tasks)
    assert all(r["available"] for r in rep)
    ids = [r["id"] for r in rep]
    assert all(x in ids for x in ("CL/absorbing", "K2/absorbing", "CL/sealed/dw", "K2/sealed/dw", "X6/dw", "X5/dw"))
    reg = P.score(tasks)                                           # Amendment 1's registered thresholds
    assert [p["id"] for p in reg if "holds" in p] == ["X1", "X2", "X3", "X4"]
    assert reg[3]["threshold"] == [-0.01, 0.01] and reg[0]["threshold"] == -0.03 and reg[1]["threshold"] == 0.01
    lv = P.levels(tasks)
    assert f"li4|k1-corner/absorbing" in lv and lv["li4|k0/absorbing"]["struggling"] is None
    ex = P.x5_exact(tasks)
    assert ex["sheets"] == 4 * 2 * 64 and not ex["exact"]        # random endpoints: the identity must not hold
    from sm008 import tables
    text = tables.render({"stage": "probe", "root": str(root), "parts": sc, "reported": rep, "x5_exact": ex, "levels": lv})
    assert "## Parts (li4)" in text and len(text.encode()) < 256 * 1024


def test_amendment_1_one_future_in_phase_b():
    assert D.FUTURES == {"probe": 1, "debug": 2, "preflight": 1, "development": 1}
    assert P.TH == {"X1": -0.03, "X2": 0.01, "X3": -0.03, "X4": (-0.01, 0.01)}


def test_design_digest_is_stable():
    assert D.digest() == D.digest() and len(D.digest()) == 64
    json.dumps(D.design_dict(), default=list)
