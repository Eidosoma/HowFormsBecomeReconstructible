"""AR006C's unit tests (engineering block 900948 for the short bridge; no confirmation block is ever drawn)."""
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import sim as A1S  # noqa: E402
from ar006 import design as A6  # noqa: E402
from ar006 import worker as W6  # noqa: E402
from ar006c import analyze as CZ  # noqa: E402
from ar006c import design as D  # noqa: E402
from mse.assay import RANGES  # noqa: E402


def test_identities_and_purpose():
    blocks = D.IDENTITIES["confirmation"]
    assert blocks == tuple(range(920387, 920411)) and len(blocks) == 24 and D.RESERVE == tuple(range(920411, 920417))
    assert all(b in RANGES["confirmation"] and b <= 924999 for b in blocks + D.RESERVE) and not set(blocks) & set(D.RESERVE)
    assert not any(lo <= b <= hi for b in blocks + D.RESERVE for lo, hi in D.TAKEN.values())
    assert D.HALVES == (blocks[:12], blocks[12:])
    assert D.DEBUG_BLOCKS == (A6.DEBUG_BLOCKS[0], A6.PREFLIGHT_BLOCKS[0]) and D.PREFLIGHT_BLOCKS == A6.SPARE_ENGINEERING
    assert all(b in RANGES["engineering"] for b in D.DEBUG_BLOCKS + D.PREFLIGHT_BLOCKS) and D.TEST_BLOCK in D.DEBUG_BLOCKS
    assert D.PURPOSE == {"debug": "engineering", "preflight": "engineering", "confirmation": "confirmation"}


def test_runs_are_ar006s_reduced():
    full = {A6.run_name(*x): x for x in A6.RUNS}
    for x in D.RUNS:
        f = full[D.run_name(*x)]
        assert x[:2] == f[:2] and x[5] == f[5] and all(set(x[i]) <= set(f[i]) for i in (2, 3, 4))
    arms = [a for x in D.RUNS for a in D.arms_of(x)]
    assert set(arms) == {"vote", "vms", "vtol"} and D.ARM_RUNS == 12 == len(arms)
    assert D.VD_DETECTORS == {"vms": A6.VD_DETECTORS["vms"], "vtol": A6.VD_DETECTORS["vtol"]}
    assert D.TAG == A6.TAG and D.BEST == A6.BEST and D.CONTROLLER == A6.CONTROLLER


def test_interval_and_criteria_constants():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(24, 8))
    iv = CZ.interval(x)
    sd = max(float(x.mean(1).std(ddof=1)), float(x.ravel().std(ddof=1) / math.sqrt(8)))
    assert abs(iv["half_width"] - stats.t.ppf(0.975, 23) * sd / math.sqrt(24)) < 1e-12 and iv["n_blocks"] == 24
    assert D.THRESHOLDS == {"k1_cue": ("le", 0.01), "k1_none": ("le", 0.002), "k3a": ("ge", 0.04), "k5a": ("ge", -0.005)}
    assert abs(D.SD_UPPER - math.sqrt(15 / stats.chi2.ppf(0.025, 15))) < 1e-4


def test_reduced_task_equals_full_task_short():
    """Two runs at 200 updates on one pair: the reduced runs' branches equal AR006's full runs', bit for bit."""
    prep = A1S.prepare("S4", D.TEST_BLOCK, "engineering")
    for rn in ("cue@0", "memory@1-L8"):
        red = D.RUNS[D.RUNNAMES.index(rn)]
        fullrun = A6.RUNS[[A6.run_name(*x) for x in A6.RUNS].index(rn)]
        e1, r1, s1 = W6.one("li4", "S4_t1", D.TEST_BLOCK, "engineering", red, D.TAG, prep, window=200, reads=(100, 200),
                            vd_detectors=D.VD_DETECTORS)
        e2, r2, s2 = W6.one("li4", "S4_t1", D.TEST_BLOCK, "engineering", fullrun, D.TAG, prep, window=200,
                            reads=(100, 200), vd_detectors=A6.VD_DETECTORS)
        ra, rf = list(D.arms_of(red)), list(A6.arms_of(fullrun))
        for i, a in enumerate(ra):
            j = rf.index(a)
            assert np.array_equal(e1[f"{rn}/r_in"][:, i], e2[f"{rn}/r_in"][:, j])
            assert np.array_equal(e1[f"{rn}/r_all"][:, i], e2[f"{rn}/r_all"][:, j])
            assert np.array_equal(e1[f"{rn}/det_on"][i], e2[f"{rn}/det_on"][j])
            for x in ("V", "r", "H", "W"):
                assert np.array_equal(r1[f"{rn}/{x}"][i], r2[f"{rn}/{x}"][j])
            if a != "vote":
                assert s1[a] == s2[a]
