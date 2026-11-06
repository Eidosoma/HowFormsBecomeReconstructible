"""AR006: guard only the tolerance (REPORT_AR005.md, next step 1; the PI's "go with your recommendations", 3 November
2026; PLAN_AR006.md, committed 8406003667 before any run).

AR005's vguard (DET_POOL plus the body check g-body-f05) removed vpool's scattered false alarms and kept most of the
misread recovery, but its blind spot is damage the body shares: in correlated damage it trails vms, whose DET_STAR fires
unguarded at update 1 and repairs it. vtol guards only the tolerance: every window DET_STAR holds (ring_max 0) fires
unguarded, as in vms, and the windows pooling adds (held at ring_max 1 but not at 0) need the body's confirmation by
g-body-f05; the vote is the default. DET_STAR and DET_POOL differ in ring_max alone, so vtol's windows are exactly vms's
united with vguard's (PLAN_AR006.md). No free choice is left, so there is no tuning stage.

The machinery is AR005's, imported unchanged (ar005, and through it ar004, ar003, ar002, ar001); the split guard and the
run that carries it are ar006.sim's. The arms: the vote (ar001.sim.run; sigma-0 runs only), vms, vpool, vguard and
vtol, each a vote-default arm through ar006.sim.run_vt. The development blocks come from 925000-925999, enrolled through
mse.assay.enrol under the confirmation purpose (the PI's decision, ENGINE.md).
"""
from __future__ import annotations

import hashlib
import json

from ar003 import design as A3
from ar005 import design as A5

STUDY = "AR006"
TAG = "mse-ar006"
PROBE_TAG = "mse-p57"
BRIDGE_TAG = A5.TAG                                            # the bridge redraws AR005's debug block under AR005's tag

# identities (fork A3's scan, 12:29-12:31Z on 3 November; PLAN_AR006.md)
PROBE_BLOCKS = (900917, 900918, 900919, 900928)                # halves 900917, 900918 and 900919, 900928
PREFLIGHT_BLOCKS = (900929, 900947)
DEBUG_BLOCKS = (900948,)
TEST_BLOCK = 900949
SPARE_ENGINEERING = (900969, 900989)
BRIDGE_BLOCKS = A5.DEBUG_BLOCKS                                # 900799, AR005's debug block (its full outputs exist there)
BRIDGE_TASKS = (("li4", "S4_t1"), ("dw", "F0_t0"))
DEVELOPMENT_BLOCKS = (925614, 925615, 925616, 925617, 925618, 925619, 925620, 925621, 925622, 925624, 925626, 925627,
                      925628, 925630, 925633, 925634)          # 16 blocks from 925000-925999
DEVELOPMENT_HALVES = (DEVELOPMENT_BLOCKS[:8], DEVELOPMENT_BLOCKS[8:])
IDENTITIES = {"preflight": PREFLIGHT_BLOCKS, "development": DEVELOPMENT_BLOCKS}
PURPOSE = {"bridge": "engineering", "probe": "engineering", "debug": "engineering", "preflight": "engineering",
           "development": "confirmation"}                      # the development's enrolment purpose (ENGINE.md)

SIDE, NCASE, CHUNK = A5.SIDE, A5.NCASE, A5.CHUNK
WINDOW, READS, T_READ, TRACE, SIZE = A5.WINDOW, A5.READS, A5.T_READ, A5.TRACE, A5.SIZE
CLOCK, T_STAR, SIG = A5.CLOCK, A5.T_STAR, A5.SIG
BODIES, PATTERNS, THETAS, UNITS = A5.BODIES, A5.PATTERNS, A5.THETAS, A5.UNITS
MISREAD_SIGMA = A5.MISREAD_SIGMA
BEST = A5.BEST                                                 # the vote
unit_name, parse_unit = A5.unit_name, A5.parse_unit

# the detectors ------------------------------------------------------------------------------------------------------
DET_STAR = A5.DET_STAR                                         # AR003's, frozen (vms)
DET_POOL = A5.DET_POOL                                         # AR004's, frozen (vpool)
VGUARD = A5.VGUARD                                             # AR005's, frozen (vguard: DET_POOL plus g-body-f05)
VTOL = dict(DET_POOL, guard={"kind": "split", "f": VGUARD["guard"]["f"], "free_ring_max": DET_STAR["cue"]["ring_max"]})
VD_DETECTORS = {"vote": {"never": True}, "vms": A5.VD_DETECTORS["vms"], "vpool": DET_POOL, "vguard": VGUARD, "vtol": VTOL}
CONTROLLER = "vtol"

# the runs -----------------------------------------------------------------------------------------------------------
STATEMENT_SIZES = A5.STATEMENT_SIZES                           # 4 and 8 (2 x 2 not run)
S1 = MISREAD_SIGMA


def R(situation, sigma, a1, vd, size=SIZE):
    return (situation, sigma, tuple(a1), (), tuple(vd), size)


V = ("vote",)
RUNS = (tuple(R("memory", 0.0, V, ("vms", "vtol"), L) for L in STATEMENT_SIZES)
        + tuple(R("memory", S1, (), ("vms", "vpool", "vguard", "vtol"), L) for L in STATEMENT_SIZES)
        + (R("none", 0.0, V, ("vms", "vtol")), R("none", S1, (), ("vms", "vtol")), R("cue", 0.0, V, ("vms", "vpool", "vtol")),
           R("correlated", 0.0, V, ("vms", "vpool", "vguard", "vtol")),
           R("correlated", S1, (), ("vms", "vpool", "vguard", "vtol"))))           # 32 arm-runs: debug, preflight, development
PROBE_RUNS = (tuple(R("memory", 0.0, V, ("vms", "vtol"), L) for L in STATEMENT_SIZES)
              + tuple(R("memory", S1, (), ("vms", "vpool", "vtol"), L) for L in STATEMENT_SIZES)
              + (R("none", 0.0, V, ("vtol",)), R("none", S1, (), ("vtol",)), R("cue", 0.0, V, ("vtol",)),
                 R("correlated", 0.0, (), ("vms", "vguard", "vtol")), R("correlated", S1, (), ("vms", "vguard", "vtol"))))  # 23
_USED = {A3.run_name(*x) for x in RUNS}
BRIDGE_RUNS = tuple((s, z, a1, (), tuple(vd) + ("vtol",), L) for s, z, a1, _, vd, L in A5.RUNS
                    if A3.run_name(s, z, size=L) in _USED)                           # 41
STAGE_RUNS = {"bridge": BRIDGE_RUNS, "probe": PROBE_RUNS, "debug": RUNS, "preflight": RUNS, "development": RUNS}


def run_name(situation, sigma, a1=None, det=None, vd=None, size=SIZE):
    return A3.run_name(situation, sigma, size=size)


def arms_of(run):
    return A3.arms_of(run)


def arm_runs(runs):
    return sum(len(arms_of(x)) for x in runs)


def stage_blocks(stage):
    return list({"bridge": BRIDGE_BLOCKS, "probe": PROBE_BLOCKS, "debug": DEBUG_BLOCKS, "preflight": PREFLIGHT_BLOCKS,
                 "development": DEVELOPMENT_BLOCKS}[stage])


def stage_tag(stage):
    return {"bridge": BRIDGE_TAG, "probe": PROBE_TAG}.get(stage, TAG)


def stage_detectors(stage):
    return VD_DETECTORS


def tasks(stage=None):
    if stage == "bridge":
        return list(BRIDGE_TASKS)
    return A3.tasks()


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "bridge_tag": BRIDGE_TAG, "identities": IDENTITIES,
            "purpose": PURPOSE, "probe_blocks": PROBE_BLOCKS, "debug_blocks": DEBUG_BLOCKS, "test_block": TEST_BLOCK,
            "spare_engineering": SPARE_ENGINEERING, "bridge_blocks": BRIDGE_BLOCKS, "bridge_tasks": BRIDGE_TASKS,
            "development_halves": DEVELOPMENT_HALVES, "ar005_digest": A5.digest(), "det_star": DET_STAR,
            "det_pool": DET_POOL, "vguard": VGUARD, "vtol": VTOL, "vd_detectors": VD_DETECTORS, "controller": CONTROLLER,
            "best": BEST, "runs": RUNS, "probe_runs": PROBE_RUNS, "bridge_runs": BRIDGE_RUNS,
            "stage_runs": {k: [run_name(*x) for x in v] for k, v in STAGE_RUNS.items()},
            "statement_sizes": STATEMENT_SIZES, "misread_sigma": MISREAD_SIGMA, "window": WINDOW, "reads": READS,
            "t_read": T_READ, "trace": TRACE, "units": UNITS, "bodies": BODIES, "clock": CLOCK, "sig": SIG}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A5.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar006").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar006.design  ->  ar006/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar006" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
