"""AR005's unit tests (test block 900817, short windows): the identities, the design as AR004's machinery with a
guarded pooled detector, the routed sources, the guards on synthetic and random states, run_vg against ar003.sim.run_vd,
a pass-all guarded arm against vpool, and the worker's merge."""
import inspect
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import sim as A1S  # noqa: E402
from ar003 import sim as S3  # noqa: E402
from ar003 import worker as AW  # noqa: E402
from ar004 import design as A4  # noqa: E402
from ar005 import checks as Q  # noqa: E402
from ar005 import design as D  # noqa: E402
from ar005 import sim as S  # noqa: E402
from ar005 import worker as W  # noqa: E402
from mse.assay import RANGES  # noqa: E402

BLOCK = D.TEST_BLOCK


def test_identities():
    eng = (D.TUNING_BLOCKS + D.TUNING_HELD + D.PROBE_BLOCKS + D.PREFLIGHT_BLOCKS + D.DEBUG_BLOCKS + (D.TEST_BLOCK,)
           + D.SPARE_ENGINEERING)
    assert len(eng) == len(set(eng)) == 13 and all(b in RANGES["engineering"] for b in eng)
    assert set(eng) == {900717, 900718, 900719, 900729, 900739, 900749, 900759, 900779, 900789, 900799, 900817, 900819, 900849}
    assert len(D.DEVELOPMENT_BLOCKS) == 16 == len(set(D.DEVELOPMENT_BLOCKS)) and all(b in RANGES["development"] for b in D.DEVELOPMENT_BLOCKS)
    assert list(D.DEVELOPMENT_BLOCKS) == sorted(D.DEVELOPMENT_BLOCKS) and set(D.RELEASED) <= set(D.DEVELOPMENT_BLOCKS)
    assert D.DEVELOPMENT_HALVES[0] + D.DEVELOPMENT_HALVES[1] == D.DEVELOPMENT_BLOCKS and len(D.DEVELOPMENT_HALVES[0]) == 8
    assert not set(D.DEVELOPMENT_BLOCKS) & set(A4.DEVELOPMENT_BLOCKS) and set(D.RELEASED) <= set(A4.RESERVE_BLOCKS)
    assert D.BRIDGE_BLOCKS == (900265,) and D.BRIDGE_TAG == A4.TAG and D.TAG == "mse-ar005" and D.PROBE_TAG == "mse-p53"


def test_design():
    assert D.DET_STAR == A4.DET_STAR and D.DET_POOL == A4.DET_POOL == A4.VD_DETECTORS["vpool"]
    assert D.VD_DETECTORS["vms"] == A4.VD_DETECTORS["vms"] and D.VD_DETECTORS["vguard"] == D.GUARDS[D.VGUARD_NAME]
    assert all({k: v for k, v in g.items() if k != "guard"} == D.DET_POOL for g in D.GUARDS.values())
    assert tuple(D.GUARDS) == D.GRID_ORDER and set(D.TUNING_DETECTORS) >= set(D.GUARDS) | set(D.VD_DETECTORS)
    assert (D.arm_runs(D.RUNS), D.arm_runs(D.PROBE_RUNS), D.arm_runs(D.BRIDGE_RUNS), D.arm_runs(D.TUNING_RUNS)) == (43, 22, 32, 27)
    assert all("vote" not in x[2] for x in D.RUNS + D.PROBE_RUNS + D.TUNING_RUNS if x[1] != 0.0)
    assert [D.run_name(*x) for x in D.BRIDGE_RUNS] == [A4.run_name(*x) for x in A4.RUNS]
    assert D.stage_detectors("tuning") is D.TUNING_DETECTORS and D.stage_detectors("probe") is D.VD_DETECTORS


def test_routed_sources():
    assert inspect.getsource(S3.run_vd).count(S.RUN_VD_CALL) == 1 and inspect.getsource(AW.one).count("sim.run_vd(") == 1
    assert W.task.__globals__["one"] is W.one and W.one.__globals__["run_vg"] is S.run_vg
    assert S.run_vg.__globals__["detect"] is S.detect


def test_guards_on_synthetic_and_random_states():
    items = Q.guard_items()
    assert all(items.values()), [k for k, v in items.items() if not v]


def test_run_vg_equals_run_vd():
    prep = A1S.prepare("S4", BLOCK, "engineering")
    for situation, sigma, L in (("memory", D.MISREAD_SIGMA, 8), ("cue", 0.0, 4)):
        a = S3.run_vd("li4", situation, sigma, ("vote", "vms", "vpool"), *prep, 1.0, {100, 200}, tag=D.TAG, window=200,
                      size=L, detectors=D.VD_DETECTORS)
        b = S.run_vg("li4", situation, sigma, ("vote", "vms", "vpool"), *prep, 1.0, {100, 200}, tag=D.TAG, window=200,
                     size=L, detectors=D.VD_DETECTORS)
        assert a.keys() == b.keys()
        assert all(np.array_equal(a[x], b[x]) for x in a if x != "signal_updates") and a["signal_updates"] == b["signal_updates"]


def test_pass_all_guard_equals_vpool():
    prep = A1S.prepare("F0", BLOCK, "engineering")
    dets = dict(D.VD_DETECTORS, vpass=D.guarded({"kind": "body", "f": 0.0}))
    o = S.run_vg("dw", "cue", 0.0, ("vpool", "vpass"), *prep, 1.0, {200}, tag=D.TAG, window=200, detectors=dets)
    k = D.NCASE
    assert (o["det_on"][:k] > 0).any()
    assert all(np.array_equal(o[x][:k], o[x][k:]) for x in ("V", "r", "H", "W", "rB", "zone", "fp", "det_on"))
    assert all(np.array_equal(o[x][:, :k], o[x][:, k:]) for x in ("r_in", "r_all", "trace"))


def test_worker_merge():
    prep = A1S.prepare("S4", BLOCK, "engineering")
    run = D.RUNS[[D.run_name(*x) for x in D.RUNS].index("correlated@1")]
    e, raw, sig = W.one("li4", "S4_t1", BLOCK, "engineering", run, D.TAG, prep, window=200, reads=(100, 200),
                        vd_detectors=D.VD_DETECTORS)
    assert e["correlated@1/r_in"].shape == (2, 3, D.NCASE) and raw["correlated@1/rB"].shape[0] == 3
    o = S.run_vg("li4", "correlated", D.MISREAD_SIGMA, ("vms", "vpool", "vguard"), *prep, 1.0, {100, 200}, tag=D.TAG,
                 window=200, detectors=D.VD_DETECTORS)
    assert np.array_equal(e["correlated@1/r_in"], o["r_in"].reshape(2, 3, D.NCASE)) and set(sig) == {"vms", "vpool", "vguard"}
