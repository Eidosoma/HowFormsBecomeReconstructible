"""SM009's package: the arrangements and arms, the field factor's uniform identity (R's driver 0), every arm's response
arithmetic from the trace, P against sm008.sim.run, O's identity across compositions, and the declared kappas against P65k.
Amendment 1: phase B's set without R (its shards record no kappa_R), the registered thresholds, and the reader's items.
Short runs on a restored P53 task; no tissue outcome is read."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from sm007 import sim as S7  # noqa: E402
from sm008 import design as D8  # noqa: E402
from sm008 import sim as S8  # noqa: E402
from sm009 import design as D  # noqa: E402
from sm009 import predict as P  # noqa: E402
from sm009 import sim  # noqa: E402
from sm009 import worker as W  # noqa: E402


def test_arrangements_and_arms():
    # phase A's set (P65 and the debug run): 28 arrangements, R included
    bc, ba, bg, bp, groups = sim.layout(D.PHASE_A_SET)
    assert len(D.PHASE_A_SET) == 28 and len(bc) == 1696
    assert {a[3] for a in D.PHASE_A_SET} == {"field", "own", "relative"}
    assert sum(a[3] == "own" for a in D.PHASE_A_SET) == 9 and sum(a[3] == "relative" for a in D.PHASE_A_SET) == 8
    # Amendment 1: phase B's set, R dropped: P and O in every composition, iso8 under both, sealed k1-corner and k8 under P
    bc, ba, bg, bp, groups = sim.layout(D.FULL_SET)
    assert len(D.FULL_SET) == 20 and len(bc) == 1184
    assert D.FULL_SET == tuple(a for a in D.PHASE_A_SET if a[3] != "relative")
    assert D.STAGE_SETS == {"probe": D.PHASE_A_SET, "debug": D.PHASE_A_SET, "preflight": D.FULL_SET,
                            "development": D.FULL_SET}
    labels = [a[0] for a in D.FULL_SET]
    assert len(labels) == len(set(labels))
    assert {a[3] for a in D.FULL_SET} == {"field", "own"}
    assert sum(a[3] == "own" for a in D.FULL_SET) == 9 and sum(a[3] == "field" for a in D.FULL_SET) == 11
    assert {f"{c}/absorbing/{arm}" for c in D.COMPOSITIONS for arm in ("P", "O")} <= set(labels)
    assert {"iso8/absorbing/P", "iso8/absorbing/O", "k1-corner/sealed/P", "k8/sealed/P"} <= set(labels)
    for ai, (lab, comp, _b, _k, _l) in enumerate(D.FULL_SET):
        s = ba == ai
        if comp == "iso8":
            assert list(bc[s]) == list(range(16))
            continue
        assert np.array_equal(bc[s], (bg[s] + bp[s]) % 8 + 8 * np.isin(bp[s], list(D.COMPOSITIONS[comp])))
    assert [p[0] for p in P.parts()] == ["Y1", "Y2", "Y3", "Y4"]
    assert [p[3] for p in P.parts()] == ["ge", "le", "ge", "in"]          # Y3's declared kind kept after the pilot
    assert P.TH == {"Y1": 0.05, "Y2": -0.005, "Y4": (0.02, 0.04)}


def test_the_reader_after_amendment_1():
    ids = [r[0] for r in P.reported()]
    assert len(ids) == len(set(ids))
    assert not [i for i in ids if "R" in i.split("/")[0] or i.startswith(("Y5", "X1/R", "X2/R"))]
    want = {"X1/O", "X1/O/dw", "X1/P", "X1/P/dw", "X2/P", "X2/P/dw", "O-P/k0", "O-P/k0/dw", "X3/P", "Y1/inner",
            "Y1/inner/dw", "Y1/dw", "Y2/dw", "Y3/dw", "Y4/dw"} | {f"O-P/group/{c}" for c in D.COMPOSITIONS} \
        | {f"O-P/group/{c}/dw" for c in D.COMPOSITIONS}
    assert want <= set(ids)
    assert ids.index("X1/P") < ids.index("X1/P/dw")                     # li4 first


def test_phase_b_set_records_no_R_kappa(task):
    from sm009 import checks as K
    cases, R0, thf, T, _b, _rf = task
    assert K.arms_in(D.FULL_SET) == ("P", "O") and K.arms_in(D.PHASE_A_SET) == ("P", "O", "R")
    r = sim.run("li4", D.FULL_SET, cases, R0, thf, T, D.PROBE_TAG, window=2, reads=(), keep_final=False)
    assert (r["kappa"], r["kappa_o"], r["kappa_r"]) == K.expected_kappas(D.FULL_SET) == (D.KAPPA, D.KAPPA_O, None)
    assert K.expected_kappas(D.PHASE_A_SET) == (D.KAPPA, D.KAPPA_O, D.KAPPA_R)
    assert K.CAP == 8.0 and K.HEADROOM == 1.25


def test_field_factor_makes_a_uniform_group_drive_nothing():
    f = sim.field_factor("2x4", "absorbing", D.LAMBDA)
    M = S7.medium("2x4", "absorbing", D.LAMBDA)
    e = 0.41
    x = M.sample(M.steady_state(np.full(8, e)))
    assert np.allclose(np.maximum(0.0, e - D.GAMMA * x / f), 0.0, atol=1e-12)
    assert f[1] > f[0]                                # an inner cell keeps more than a corner


def test_declared_kappas_are_p65k():
    rec = json.loads((LANE / "probes" / "results" / "p65k_sm009_kappa.json").read_text())
    assert rec["kappa_o"] == D.KAPPA_O and rec["kappa_r"] == D.KAPPA_R and rec["reads_computed"] == 0
    m = rec["driver_means"]
    assert abs(D.KAPPA_O * m["O"] - D.KAPPA * m["P"]) < 1e-12 and abs(D.KAPPA_R * m["R"] - D.KAPPA * m["P"]) < 1e-9


@pytest.fixture(scope="module")
def task():
    return W.inputs("ar005/p53", "li4", 900729)


def test_response_arithmetic_from_the_trace(task):
    cases, R0, thf, T, _b, _rf = task
    arrs = [a for a in D.PHASE_A_SET if a[0] in ("k1-corner/absorbing/P", "k1-corner/absorbing/O", "k1-corner/absorbing/R")]
    r = sim.run("li4", arrs, cases, R0, thf, T, D.PROBE_TAG, window=60, reads=(60,), trace_until=60, keep_final=False)
    tr = r["trace"]
    f = sim.field_factor("2x4", "absorbing", D.LAMBDA)
    ff = np.tile(f, 24)
    kind = np.array([arrs[i][3] for i in r["br_arr"]])
    kap = np.where(kind == "field", D.KAPPA, np.where(kind == "own", D.KAPPA_O, D.KAPPA_R))
    for t in range(60):
        s_prev = tr["emission"][t - 1] if t else np.zeros(len(ff))
        x_prev = tr["exposure"][t - 1] if t else np.zeros(len(ff))
        drv = np.where(kind == "field", x_prev, np.where(kind == "own", s_prev, np.maximum(0.0, s_prev - D.GAMMA * x_prev / ff)))
        assert np.array_equal(tr["driver"][t], drv)
        assert np.array_equal(tr["gain"][t], D.G_DIST * (1.0 + kap * drv))
    assert np.array_equal(tr["gain"][0], np.full(len(ff), D.G_DIST))


def test_P_equals_sm008_and_O_reads_no_field(task):
    cases, R0, thf, T, _b, _rf = task
    arr8 = [a for a in D8.FULL_SET if a[0] in ("k0/absorbing", "k1-corner/absorbing", "k8/sealed", "iso8/absorbing")]
    r9 = sim.run("li4", arr8, cases, R0, thf, T, D.PROBE_TAG, window=80, reads=(80,))
    r8 = S8.run("li4", arr8, cases, R0, thf, T, D.PROBE_TAG, window=80, reads=(80,))
    assert np.array_equal(r9["V"], r8["V"]) and np.array_equal(r9["a_v"], r8["a_v"])
    assert all(np.array_equal(r9[x], r8[x]) for x in ("gain_mean", "expo_mean", "stress_mean"))
    arrO = [a for a in D.FULL_SET if a[3] == "own"]
    rO = sim.run("li4", arrO, cases, R0, thf, T, D.PROBE_TAG, window=80, reads=(80,))
    iso = [a[0] for a in arrO].index("iso8/absorbing/O")
    ref = {int(rO["br_case"][b]): b for b in np.flatnonzero(rO["br_arr"] == iso)}
    for b in range(len(rO["br_case"])):
        assert np.array_equal(rO["V"][b], rO["V"][ref[int(rO["br_case"][b])]])


def test_O_and_R_refuse_without_their_kappas(task, monkeypatch):
    cases, R0, thf, T, _b, _rf = task
    monkeypatch.setattr(D, "KAPPA_O", None)
    with pytest.raises(RuntimeError):
        sim.run("li4", [D.FULL_SET[8]], cases, R0, thf, T, D.PROBE_TAG, window=2, reads=())
