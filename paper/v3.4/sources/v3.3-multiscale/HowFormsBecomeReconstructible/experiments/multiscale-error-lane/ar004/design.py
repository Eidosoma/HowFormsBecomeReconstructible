"""AR004: the confirmed controller under misread cues (REPORT_AR003C.md, Next; the PI's "lets go" and "lets work in
parallel", 1 November 2026; PLAN_AR004.md, committed 33688da33b before any tuning).

AR003C confirmed vms (DET_STAR with the vote default) at sigma 0. Under GC001's quenched misread of the cue (sigma 1)
its detector loses hits: DET_STAR needs every live anchor of a window to disagree with the record (q 1) and no
disagreeing live anchor in the surround (ring_max 0), and anchors near the pattern's walls read the other side of the
wall. AR004 asks whether a detector that pools its anchors (q < 1, ring_max > 0, n >= 3, the same boxes 2-12) recovers
the controller's worth under misreads, within the confirmed harm bounds at sigma 0 and giving up nothing to the vote
where nothing needs correcting. The pooled detector DET_POOL is chosen on tuning blocks by PLAN_AR004.md's rule.

The machinery is AR003's, imported unchanged (ar003.worker.task, ar003.sim.run_vd, and ar002 and ar001 under them).
The arms: the vote (ar001.sim.run; sigma-0 runs only, since it never reads the cue), vms (AR003's frozen DET_STAR with
the vote default) and vpool (DET_POOL with the vote default), both through ar003.sim.run_vd.
"""
from __future__ import annotations

import hashlib
import json

from ar003 import design as A3

STUDY = "AR004"
TAG = "mse-ar004"
PROBE_TAG = "mse-p51"
BRIDGE_TAG = A3.TAG                                            # the bridge redraws AR003's debug block under AR003's tag

# identities (fork A3's scan, 20:48-20:51Z: 900256-900268 a free window; the development blocks the first 16 free)
TUNING_BLOCKS = (900256, 900257)                               # stage 1, stage 2
PROBE_BLOCKS = (900259, 900260, 900261, 900262)                # halves 900259-60 and 900261-62
PREFLIGHT_BLOCKS = (900263, 900264)
DEBUG_BLOCKS = (900265,)
TEST_BLOCK = 900266
SPARE_ENGINEERING = (900258, 900267, 900268)
BRIDGE_BLOCKS = (A3.DEBUG_BLOCKS[0],)                          # 900158, AR003's debug block (its full outputs exist there)
BRIDGE_TASKS = (("li4", "S4_t1"), ("dw", "F0_t0"))
DEVELOPMENT_BLOCKS = (910017, 910018, 910019, 910057, 910058, 910059, 910077, 910078, 910079, 910097, 910098, 910099,
                      910117, 910118, 910119, 910137)          # 16 blocks
RESERVE_BLOCKS = (910138, 910139, 910157, 910158, 910159)      # held for the lead, not drawn
IDENTITIES = {"preflight": PREFLIGHT_BLOCKS, "development": DEVELOPMENT_BLOCKS}
PURPOSE = {"bridge": "engineering", "probe": "engineering", "debug": "engineering", "preflight": "engineering",
           "development": "development"}

SIDE, NCASE, CHUNK = A3.SIDE, A3.NCASE, A3.CHUNK
WINDOW, READS, T_READ, TRACE, SIZE = A3.WINDOW, A3.READS, A3.T_READ, A3.TRACE, A3.SIZE
CLOCK, T_STAR, SIG = A3.CLOCK, A3.T_STAR, A3.SIG
BODIES, PATTERNS, THETAS, UNITS = A3.BODIES, A3.PATTERNS, A3.THETAS, A3.UNITS
MISREAD_SIGMA = A3.MISREAD_SIGMA
BEST = A3.BEST                                                 # the vote
unit_name, parse_unit = A3.unit_name, A3.parse_unit

# the detectors ------------------------------------------------------------------------------------------------------
DET_STAR = A3.DET_STAR                                         # AR003's, frozen (ms-b2-n3-q1)


def candidate(n, q, ring_max):
    """DET_STAR's rule (boxes 2-12, surround of width 2, dwell 1) with pooling: n, q and ring_max."""
    return {"cue": {"boxes": tuple(range(2, 13)), "n": n, "q": q, "ring": 2, "ring_max": ring_max, "dwell": 1}, "body": None}


CANDIDATES = {f"pool-n{n}-q{q:g}-r{rm}": candidate(n, q, rm) for n in (3, 4) for q in (1.0, 0.75) for rm in (0, 1, 2)}
BASELINE = "pool-n3-q1-r0"                                     # DET_STAR itself (vms's detector), not eligible
# DET_POOL: set from the tuning blocks by PLAN_AR004.md's rule (probes/p51a_ar004_detector_tuning.py; results in
# probes/results/p51a_ar004_detector_tuning.txt): pool-n3-q1-r1, the only eligible candidate of stage 1, chosen by the
# rule's fallback (stage 2 on 900257: its cost under scattered cue damage, +0.0209, exceeded both tiers' bounds). Until the
# tuning ran it held a placeholder (pool-n3-q0.75-r1) for the bridge and tests.
DET_POOL_NAME = "pool-n3-q1-r1"
DET_POOL = CANDIDATES[DET_POOL_NAME]
VD_DETECTORS = {"vote": {"never": True}, "vms": A3.VD_DETECTORS["vms"], "vpool": DET_POOL}
CONTROLLER = "vpool"

# the runs -----------------------------------------------------------------------------------------------------------
SIZES = A3.SIZES                                               # 2, 4, 8 (equal weights in the size means)
SIDE_SIZE = 6                                                  # the 6 x 6 side arm (reported)


def R(situation, sigma, a1, vd, size=SIZE):
    return (situation, sigma, tuple(a1), (), tuple(vd), size)


V, B = ("vote",), ("vms", "vpool")
RUNS = (tuple(R("memory", 0.0, V, B, L) for L in SIZES) + (R("none", 0.0, V, B), R("cue", 0.0, V, B))
        + tuple(R("memory", MISREAD_SIGMA, (), B, L) for L in SIZES) + (R("none", MISREAD_SIGMA, (), B),))
SIDE_RUNS = (R("memory", 0.0, V, B, SIDE_SIZE), R("memory", MISREAD_SIGMA, (), B, SIDE_SIZE))
RUNS_FULL = RUNS + SIDE_RUNS                                   # debug, preflight, development; the probe and bridge run RUNS
STAGE_RUNS = {"bridge": RUNS, "probe": RUNS, "debug": RUNS_FULL, "preflight": RUNS_FULL, "development": RUNS_FULL}


def run_name(situation, sigma, a1=None, det=None, vd=None, size=SIZE):
    return A3.run_name(situation, sigma, size=size)


def arms_of(run):
    return A3.arms_of(run)


RUNNAMES = tuple(run_name(*x) for x in RUNS_FULL)
ARM_RUNS = sum(len(arms_of(x)) for x in RUNS)
ARM_RUNS_FULL = sum(len(arms_of(x)) for x in RUNS_FULL)


def stage_blocks(stage):
    return list({"bridge": BRIDGE_BLOCKS, "probe": PROBE_BLOCKS, "debug": DEBUG_BLOCKS, "preflight": PREFLIGHT_BLOCKS,
                 "development": DEVELOPMENT_BLOCKS}[stage])


def stage_tag(stage):
    return {"bridge": BRIDGE_TAG, "probe": PROBE_TAG}.get(stage, TAG)


def tasks(stage=None):
    if stage == "bridge":
        return list(BRIDGE_TASKS)
    return A3.tasks()


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "bridge_tag": BRIDGE_TAG, "identities": IDENTITIES,
            "purpose": PURPOSE, "tuning_blocks": TUNING_BLOCKS, "probe_blocks": PROBE_BLOCKS, "debug_blocks": DEBUG_BLOCKS,
            "test_block": TEST_BLOCK, "spare_engineering": SPARE_ENGINEERING, "bridge_blocks": BRIDGE_BLOCKS,
            "bridge_tasks": BRIDGE_TASKS, "reserve_blocks": RESERVE_BLOCKS, "ar003_digest": A3.digest(),
            "det_star": DET_STAR, "candidates": CANDIDATES, "baseline": BASELINE, "det_pool_name": DET_POOL_NAME,
            "det_pool": DET_POOL, "vd_detectors": VD_DETECTORS, "controller": CONTROLLER, "best": BEST, "runs": RUNS,
            "side_runs": SIDE_RUNS, "stage_runs": {k: [run_name(*x) for x in v] for k, v in STAGE_RUNS.items()},
            "sizes": SIZES, "side_size": SIDE_SIZE, "misread_sigma": MISREAD_SIGMA, "window": WINDOW, "reads": READS,
            "t_read": T_READ, "trace": TRACE, "units": UNITS, "bodies": BODIES, "clock": CLOCK, "sig": SIG}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A3.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar004").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar004.design  ->  ar004/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar004" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
