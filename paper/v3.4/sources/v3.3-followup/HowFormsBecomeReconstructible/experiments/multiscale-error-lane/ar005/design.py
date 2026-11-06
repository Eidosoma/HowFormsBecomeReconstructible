"""AR005: a second check against scattered false alarms (REPORT_AR004.md; the PI's "lets start the two next one in
parallel", 2 November 2026; PLAN_AR005.md, committed 41e3d890ca before any tuning value).

AR004 found a trade-off: vpool (DET_POOL, DET_STAR with one disagreeing live anchor tolerated in the surround) wins back
much of what misread cues cost vms, but its false alarms under scattered cue damage cost the sheet +0.0177, against
the confirmed bound of 0.01. AR005 asks whether a second, independent check on the pooled detector's firing rejects
scattered-damage clusters and keeps the misread recovery. vguard is DET_POOL plus one guard, chosen on tuning block
900717 by PLAN_AR005.md's rule from a grid of three: the body as the second source (g-body-f1, g-body-f05: the confident
body disagrees with the record at every, or at half or more, of the window's disagreeing live anchors) and cluster
shape (g-dense-25: the window holds live anchors at a density of at least a quarter).

The machinery is AR004's, imported unchanged (ar004, ar003, ar002, ar001); the guarded detector and the run that
carries it are ar005.sim's. The arms: the vote (ar001.sim.run; sigma-0 runs only), vms (AR003's frozen DET_STAR), vpool
(AR004's frozen DET_POOL) and vguard, each a vote-default arm through ar005.sim.run_vg.
"""
from __future__ import annotations

import hashlib
import json

from ar003 import design as A3
from ar004 import design as A4

STUDY = "AR005"
TAG = "mse-ar005"
PROBE_TAG = "mse-p53"                                          # the tuning and P53
BRIDGE_TAG = A4.TAG                                            # the bridge redraws AR004's debug block under AR004's tag

# identities (fork A3's scan, 12:09-12:11Z; approved by the lead; PLAN_AR005.md)
TUNING_BLOCKS = (900717,)
TUNING_HELD = (900718, 900719)                                 # a second tuning stage only on the lead's word
PROBE_BLOCKS = (900729, 900739, 900749, 900759)                # halves 900729, 900739 and 900749, 900759
PREFLIGHT_BLOCKS = (900779, 900789)
DEBUG_BLOCKS = (900799,)
TEST_BLOCK = 900817
SPARE_ENGINEERING = (900819, 900849)
BRIDGE_BLOCKS = A4.DEBUG_BLOCKS                                # 900265, AR004's debug block (its full outputs exist there)
BRIDGE_TASKS = (("li4", "S4_t1"), ("dw", "F0_t0"))
DEVELOPMENT_BLOCKS = (910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798,
                      910799, 910826, 910827, 910958)          # 16 blocks
DEVELOPMENT_HALVES = (DEVELOPMENT_BLOCKS[:8], DEVELOPMENT_BLOCKS[8:])
RELEASED = (910138, 910139)                                    # AR004's undrawn reserve, released by the lead about 12:12Z
IDENTITIES = {"preflight": PREFLIGHT_BLOCKS, "development": DEVELOPMENT_BLOCKS}
PURPOSE = {"bridge": "engineering", "tuning": "engineering", "probe": "engineering", "debug": "engineering",
           "preflight": "engineering", "development": "development"}

SIDE, NCASE, CHUNK = A4.SIDE, A4.NCASE, A4.CHUNK
WINDOW, READS, T_READ, TRACE, SIZE = A4.WINDOW, A4.READS, A4.T_READ, A4.TRACE, A4.SIZE
CLOCK, T_STAR, SIG = A4.CLOCK, A4.T_STAR, A4.SIG
BODIES, PATTERNS, THETAS, UNITS = A4.BODIES, A4.PATTERNS, A4.THETAS, A4.UNITS
MISREAD_SIGMA = A4.MISREAD_SIGMA
BEST = A4.BEST                                                 # the vote
unit_name, parse_unit = A4.unit_name, A4.parse_unit

# the detectors ------------------------------------------------------------------------------------------------------
DET_STAR = A4.DET_STAR                                         # AR003's, frozen (vms)
DET_POOL = A4.DET_POOL                                         # AR004's, frozen (vpool: pool-n3-q1-r1)


def guarded(guard):
    """DET_POOL's cue channel (boxes 2-12, n 3, q 1, ring 2, ring_max 1, dwell 1) with one guard (ar005.sim.detect)."""
    return dict(DET_POOL, guard=guard)


GUARDS = {"g-body-f1": guarded({"kind": "body", "f": 1.0}),
          "g-body-f05": guarded({"kind": "body", "f": 0.5}),
          "g-dense-25": guarded({"kind": "dense", "delta": 0.25})}
GRID_ORDER = ("g-body-f1", "g-body-f05", "g-dense-25")
# VGUARD: set from tuning block 900717 by PLAN_AR005.md's rule (probes/p53a_ar005_guard_tuning.py; results in
# probes/results/p53a_ar005_guard_tuning.txt): g-body-f05, the only eligible candidate (g-body-f1 gave up sigma-0 hits,
# -0.119 at 4 x 4; g-dense-25's cost under scattered cue damage, +0.0184, exceeded 0.0075). Until the tuning ran it held
# a placeholder (g-body-f1) for the bridge and tests.
VGUARD_NAME = "g-body-f05"
VGUARD = GUARDS[VGUARD_NAME]
VD_DETECTORS = {"vote": {"never": True}, "vms": A4.VD_DETECTORS["vms"], "vpool": DET_POOL, "vguard": VGUARD}
TUNING_DETECTORS = dict(VD_DETECTORS, **GUARDS)
CONTROLLER = "vguard"

# the runs -----------------------------------------------------------------------------------------------------------
SIZES = A4.SIZES                                               # 2, 4, 8: run in the registered set
STATEMENT_SIZES = (4, 8)                                       # the statements' size means (2 x 2 reported)
S1 = MISREAD_SIGMA


def R(situation, sigma, a1, vd, size=SIZE):
    return (situation, sigma, tuple(a1), (), tuple(vd), size)


V, ALL = ("vote",), ("vms", "vpool", "vguard")
RUNS = (tuple(R("memory", 0.0, V, ALL, L) for L in SIZES) + tuple(R("memory", S1, (), ALL, L) for L in SIZES)
        + (R("none", 0.0, V, ALL), R("none", S1, (), ALL), R("cue", 0.0, V, ALL), R("correlated", 0.0, V, ALL),
           R("correlated", S1, (), ALL), R("body", 0.0, V, ALL)))          # 43 arm-runs: debug, preflight, development
PROBE_RUNS = (tuple(R("memory", 0.0, V, ("vms", "vguard"), L) for L in STATEMENT_SIZES)
              + tuple(R("memory", S1, (), ("vms", "vpool", "vguard"), L) for L in STATEMENT_SIZES)
              + (R("none", 0.0, V, ("vguard",)), R("none", S1, (), ("vguard",)), R("cue", 0.0, V, ("vguard",)),
                 R("correlated", 0.0, V, ("vpool", "vguard")), R("correlated", S1, (), ("vpool", "vguard"))))  # 22
BRIDGE_RUNS = tuple((s, z, a1, (), tuple(vd) + ("vguard",), L) for s, z, a1, _, vd, L in A4.RUNS)      # 32
TUNING_RUNS = (R("cue", 0.0, V, ("vpool",) + GRID_ORDER), R("none", 0.0, V, ()), R("none", S1, (), GRID_ORDER),
               R("memory", S1, (), ("vms", "vpool") + GRID_ORDER, 4), R("memory", S1, (), ("vms", "vpool") + GRID_ORDER, 8),
               R("memory", 0.0, (), ("vms",) + GRID_ORDER, 4), R("correlated", S1, (), ("vpool",) + GRID_ORDER))  # 27
STAGE_RUNS = {"bridge": BRIDGE_RUNS, "tuning": TUNING_RUNS, "probe": PROBE_RUNS, "debug": RUNS, "preflight": RUNS,
              "development": RUNS}


def run_name(situation, sigma, a1=None, det=None, vd=None, size=SIZE):
    return A3.run_name(situation, sigma, size=size)


def arms_of(run):
    return A3.arms_of(run)


def arm_runs(runs):
    return sum(len(arms_of(x)) for x in runs)


def stage_blocks(stage):
    return list({"bridge": BRIDGE_BLOCKS, "tuning": TUNING_BLOCKS, "probe": PROBE_BLOCKS, "debug": DEBUG_BLOCKS,
                 "preflight": PREFLIGHT_BLOCKS, "development": DEVELOPMENT_BLOCKS}[stage])


def stage_tag(stage):
    return {"bridge": BRIDGE_TAG, "tuning": PROBE_TAG, "probe": PROBE_TAG}.get(stage, TAG)


def stage_detectors(stage):
    return TUNING_DETECTORS if stage == "tuning" else VD_DETECTORS


def tasks(stage=None):
    if stage == "bridge":
        return list(BRIDGE_TASKS)
    return A3.tasks()


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "bridge_tag": BRIDGE_TAG, "identities": IDENTITIES,
            "purpose": PURPOSE, "tuning_blocks": TUNING_BLOCKS, "tuning_held": TUNING_HELD, "probe_blocks": PROBE_BLOCKS,
            "debug_blocks": DEBUG_BLOCKS, "test_block": TEST_BLOCK, "spare_engineering": SPARE_ENGINEERING,
            "bridge_blocks": BRIDGE_BLOCKS, "bridge_tasks": BRIDGE_TASKS, "development_halves": DEVELOPMENT_HALVES,
            "released": RELEASED, "ar004_digest": A4.digest(), "det_star": DET_STAR, "det_pool": DET_POOL,
            "guards": GUARDS, "grid_order": GRID_ORDER, "vguard_name": VGUARD_NAME, "vguard": VGUARD,
            "vd_detectors": VD_DETECTORS, "controller": CONTROLLER, "best": BEST, "runs": RUNS, "probe_runs": PROBE_RUNS,
            "bridge_runs": BRIDGE_RUNS, "tuning_runs": TUNING_RUNS,
            "stage_runs": {k: [run_name(*x) for x in v] for k, v in STAGE_RUNS.items()}, "sizes": SIZES,
            "statement_sizes": STATEMENT_SIZES, "misread_sigma": MISREAD_SIGMA, "window": WINDOW, "reads": READS,
            "t_read": T_READ, "trace": TRACE, "units": UNITS, "bodies": BODIES, "clock": CLOCK, "sig": SIG}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A4.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar005").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar005.design  ->  ar005/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar005" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
