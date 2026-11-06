"""AR006's unit tests (test block 900949, short windows): the identities, the design as AR005's machinery with the split
guard, the routed sources, the split guard on synthetic and random states, run_vt against AR005's run_vg, the split's
limits (a free surround of 1 is vpool, a body share no window can meet is vms), and the worker's merge."""
import inspect
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import sim as A1S  # noqa: E402
from ar003 import sim as S3  # noqa: E402
from ar003 import worker as AW  # noqa: E402
from ar005 import design as A5  # noqa: E402
from ar005 import sim as S5  # noqa: E402
from ar006 import checks as Q  # noqa: E402
from ar006 import design as D  # noqa: E402
from ar006 import sim as S  # noqa: E402
from ar006 import worker as W  # noqa: E402
from mse.assay import RANGES  # noqa: E402

BLOCK = D.TEST_BLOCK


def test_identities():
    eng = D.PROBE_BLOCKS + D.PREFLIGHT_BLOCKS + D.DEBUG_BLOCKS + (D.TEST_BLOCK,) + D.SPARE_ENGINEERING
    assert len(eng) == len(set(eng)) == 10 and all(b in RANGES["engineering"] for b in eng)
    assert len(D.DEVELOPMENT_BLOCKS) == 16 == len(set(D.DEVELOPMENT_BLOCKS)) and list(D.DEVELOPMENT_BLOCKS) == sorted(D.DEVELOPMENT_BLOCKS)
    assert all(925000 <= b <= 925999 and b in RANGES["confirmation"] for b in D.DEVELOPMENT_BLOCKS)
    assert D.PURPOSE["development"] == "confirmation" and D.DEVELOPMENT_HALVES[0] + D.DEVELOPMENT_HALVES[1] == D.DEVELOPMENT_BLOCKS
    assert D.BRIDGE_BLOCKS == (900799,) and D.BRIDGE_TAG == A5.TAG and D.TAG == "mse-ar006" and D.PROBE_TAG == "mse-p57"


def test_design():
    assert D.DET_STAR == A5.DET_STAR and D.DET_POOL == A5.DET_POOL and D.VGUARD == A5.VGUARD
    assert dict(D.DET_POOL["cue"], ring_max=0) == D.DET_STAR["cue"]                     # they differ in ring_max alone
    assert D.VTOL["guard"] == {"kind": "split", "f": 0.5, "free_ring_max": 0} and D.VTOL["cue"] == D.DET_POOL["cue"]
    assert (D.arm_runs(D.RUNS), D.arm_runs(D.PROBE_RUNS), D.arm_runs(D.BRIDGE_RUNS)) == (32, 23, 41)
    assert all("vote" not in x[2] for x in D.RUNS + D.PROBE_RUNS if x[1] != 0.0)
    assert all("vtol" in x[4] for x in D.RUNS + D.PROBE_RUNS + D.BRIDGE_RUNS)


def test_routed_sources():
    assert inspect.getsource(S3.run_vd).count(S5.RUN_VD_CALL) == 1 and inspect.getsource(S5.detect).count(S.WINDOWS_CALL) == 1
    assert S.run_vt.__globals__["detect"] is S.detect and S.detect.__globals__["windows"] is S.windows
    assert W.one.__globals__["run_vt"] is S.run_vt and W.task.__globals__["one"] is W.one
    assert inspect.getsource(AW.one).count("sim.run_vd(") == 1


def test_split_guard_on_synthetic_and_random_states():
    items = Q.split_items()
    assert all(items.values()), [k for k, v in items.items() if not v]


def test_run_vt_equals_ar005s_run_vg():
    prep = A1S.prepare("S4", BLOCK, "engineering")
    arms = ("vote", "vms", "vpool", "vguard")
    for situation, sigma, L in (("correlated", 0.0, 4), ("memory", D.MISREAD_SIGMA, 8), ("cue", 0.0, 4)):
        a = S5.run_vg("li4", situation, sigma, arms, *prep, 1.0, {100, 200}, tag=D.TAG, window=200, size=L,
                      detectors=A5.VD_DETECTORS)
        b = S.run_vt("li4", situation, sigma, arms, *prep, 1.0, {100, 200}, tag=D.TAG, window=200, size=L,
                     detectors=D.VD_DETECTORS)
        assert a.keys() == b.keys()
        assert all(np.array_equal(a[x], b[x]) for x in a if x != "signal_updates") and a["signal_updates"] == b["signal_updates"]


def test_the_splits_limits():
    prep = A1S.prepare("F0", BLOCK, "engineering")
    dets = dict(D.VD_DETECTORS, vfree1=dict(D.VTOL, guard=dict(D.VTOL["guard"], free_ring_max=1)),
                vnobody=dict(D.VTOL, guard=dict(D.VTOL["guard"], f=1.01)))
    k = D.NCASE
    o = S.run_vt("dw", "cue", 0.0, ("vpool", "vfree1", "vms", "vnobody"), *prep, 1.0, {200}, tag=D.TAG, window=200,
                 detectors=dets)
    assert (o["det_on"][:k] > 0).any() and (o["det_on"][2 * k:3 * k] > 0).any()
    for i, j in ((0, 1), (2, 3)):
        assert all(np.array_equal(o[x][i * k:(i + 1) * k], o[x][j * k:(j + 1) * k]) for x in ("V", "r", "H", "W", "rB", "zone", "fp", "det_on"))
        assert all(np.array_equal(o[x][:, i * k:(i + 1) * k], o[x][:, j * k:(j + 1) * k]) for x in ("r_in", "r_all", "trace"))


def test_worker_merge():
    prep = A1S.prepare("S4", BLOCK, "engineering")
    run = D.RUNS[[D.run_name(*x) for x in D.RUNS].index("correlated@1")]
    e, raw, sig = W.one("li4", "S4_t1", BLOCK, "engineering", run, D.TAG, prep, window=200, reads=(100, 200),
                        vd_detectors=D.VD_DETECTORS)
    assert e["correlated@1/r_in"].shape == (2, 4, D.NCASE) and raw["correlated@1/rB"].shape[0] == 4
    o = S.run_vt("li4", "correlated", D.MISREAD_SIGMA, ("vms", "vpool", "vguard", "vtol"), *prep, 1.0, {100, 200}, tag=D.TAG,
                 window=200, detectors=D.VD_DETECTORS)
    assert np.array_equal(e["correlated@1/r_in"], o["r_in"].reshape(2, 4, D.NCASE)) and set(sig) == {"vms", "vpool", "vguard", "vtol"}
