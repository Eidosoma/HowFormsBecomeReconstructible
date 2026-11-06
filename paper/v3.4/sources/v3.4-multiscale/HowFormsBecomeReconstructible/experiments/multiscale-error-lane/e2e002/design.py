"""E2E002: the policy acting in every generation (ME003's full arm, PROTOCOL.md §9: "the frozen policy" against "its
removal after one rescue"). DRAFT for the lead's review (phase A). See PLAN_E2E002.md.

Generation 0 is restored, as in E2E001: AR005's saved runs at t = 8,000 (no tissue episode, no block drawn). The outgoing
record (SR001's packet: r, H, W; the strengths restart at STRENGTH0 x sign) crosses to newborn successors. Unlike
E2E001's successors (SR001's body route), E2E002's run the AR tissue itself, the vote-default arm of ar003.sim.run_vd, for
generations of 8,000 updates: "every" with the controller's detector (vms, AR003C's confirmed controller, as frozen),
"once" and the passive lineages with the vote's never-firing detector (the vote, bit for bit: AR003's Q3). Each successor
makes its own cue at birth from its incoming record (the lead's ruling 3). The policy is a parameter (POLICIES).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ar001 import design as A
from ar003 import design as A3
from ar005 import design as A5
from sr001 import design as SR

STUDY = "E2E002"
TAG = "mse-e2e002"                      # the futures' tag (debug, preflight, development)
PROBE_TAG = "mse-p58"                   # the pilot P58's futures
RUNS = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane"

# the AR tissue at its calibrated clock, in generation 0 and in every successor
CLOCK = dict(A.CLOCK)                   # eta 3e-4, bond noise 3e-5, tau_c 15,000
SIDE, GAIN, STRENGTH0, SIZE = A.SIDE, A.GAIN, A.STRENGTH0, A.SIZE
assert (SIDE, GAIN, STRENGTH0) == (SR.SIDE, SR.GAIN, SR.STRENGTH0)
T_GEN = A.WINDOW                        # 8,000 updates: generation 0's own life, from the injury to the handoff
HORIZONS = (1, 3, 8)
G_MAIN, G_SIDE = 8, 3

# the successors' policies: a vote-default arm's detector configuration (ar005.sim.detect); a parameter of the package
POLICIES = {"vote": {"never": True},                    # "once" and the passive lineages: the vote
            "vms": A3.VD_DETECTORS["vms"],              # AR003C's confirmed controller (DET_STAR), as frozen
            "vguard": A5.VGUARD}                        # AR005's (only if the price allows; not in the draft's rows)
CONTROLLER = "vms"

# the lineages: (label, generation-0 packet, successors' policy, successors' cue, the lineage's sigma, stop)
#   packet: "<arm>/<situation>" (the restored first record), "protected" (R0 with its bonds) or "post/<situation>"
#   cue: "birth" (each successor's own, from its incoming record: the lead's ruling 3) or "lineage" (generation 0's cue,
#        carried: a second heritable channel, a reported side arm)
L = lambda *x: dict(zip(("label", "packet", "policy", "cue", "sigma", "stop"), x))
CORE = (L("vms-every/memory@0", "vms/memory@0", "vms", "birth", 0.0, G_MAIN),
        L("vms-once/memory@0", "vms/memory@0", "vote", "birth", 0.0, G_MAIN),
        L("protected", "protected", "vote", "birth", 0.0, G_MAIN),
        L("protected+vms-every", "protected", "vms", "birth", 0.0, G_MAIN),
        L("vms-every/none@0", "vms/none@0", "vms", "birth", 0.0, G_MAIN),
        L("vms-once/none@0", "vms/none@0", "vote", "birth", 0.0, G_MAIN))
CONTEXT = (L("vote/memory@0", "vote/memory@0", "vote", "birth", 0.0, G_MAIN),
           L("post/memory@0", "post/memory@0", "vote", "birth", 0.0, G_MAIN))
OPTIONAL = {"post+vms-every": (L("post+vms-every/memory@0", "post/memory@0", "vms", "birth", 0.0, G_SIDE),),
            "memory@1": (L("vms-every/memory@1", "vms/memory@1", "vms", "birth", 1.0, G_MAIN),
                         L("vms-once/memory@1", "vms/memory@1", "vote", "birth", 1.0, G_MAIN)),
            "lineage-cue": (L("vms-every+lineage-cue/memory@0", "vms/memory@0", "vms", "lineage", 0.0, G_MAIN),)}
ALL = CORE + CONTEXT + tuple(x for v in OPTIONAL.values() for x in v)
SITUATION_SIGMA = {"memory@0": 0.0, "memory@1": 1.0, "none@0": 0.0}

# the restored sources (AR005's raw final states) and the stages
SOURCES = {"ar005/p53": {"root": f"{RUNS}/ar005/p53", "tag": "mse-p53", "purpose": "engineering"},
           "ar005/debug": {"root": f"{RUNS}/ar005/debug", "tag": "mse-ar005", "purpose": "engineering"},
           "ar005/preflight": {"root": f"{RUNS}/ar005/preflight", "tag": "mse-ar005", "purpose": "engineering"},
           "ar005/development": {"root": f"{RUNS}/ar005/development", "tag": "mse-ar005", "purpose": "development"}}
AR005_DEV = (910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798, 910799,
             910826, 910827, 910958)
STAGES = {"probe": {"ar005/p53": (900729, 900739, 900749, 900759)},
          "debug": {"ar005/debug": (900799,)},
          "preflight": {"ar005/preflight": (900779, 900789)},
          "development": {"ar005/development": AR005_DEV}}
STAGE_TAG = {"probe": PROBE_TAG, "debug": TAG, "preflight": TAG, "development": TAG}
# phase B's rows (the lead's ruling 3, about 11:10Z on 4 November): the base (the six core rows and the two context rows)
# plus the lineage's cue to g 8, reported only (a second channel); post+vms-every, the memory@1 pair, a second future and
# vguard-every are not run
PHASE_B = CORE + CONTEXT + OPTIONAL["lineage-cue"]
STAGE_LINEAGES = {"probe": CORE, "debug": ALL, "preflight": PHASE_B, "development": PHASE_B}
FUTURES = {"probe": 1, "debug": 1, "preflight": 1, "development": 1}
STAGE_PARENTS = {"probe": (0,)}          # the pilot reads parent 0's four cases of every task (the plan: phase A's cap);
                                         # every other stage all eight
STAGE_STOP_CAP = {"debug": G_SIDE}       # the debug run caps every row at generation 3 (every code path runs by then)
SECOND_FUTURE = ()                       # labels run in futures after the first (empty: one future; priced in the plan)
HALVES = {"probe": ((900729, 900739), (900749, 900759)), "development": (AR005_DEV[:8], AR005_DEV[8:])}
BODIES, UNITS = A.BODIES, A.UNITS        # dw, li4; S4_t0, S4_t1, F0_t0, F0_t1: the eight unit-body pairs
ITEM_SETS = {"native": (("li4", "S4_t0"), ("li4", "S4_t1")),
             "particular": (("li4", "F0_t0"), ("li4", "F0_t1")),       # read first (the lead's ruling)
             "permissive": tuple(("dw", u) for u in UNITS)}
RECORD_HIT = {"memory": True, "correlated": True, "none": False, "cue": False, "body": False}

# the statements' rule (BE002's, as in E2E001)
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP, STEP_NEAR0 = 0.01, 0.005
AT_MOST_MAX = 0.05
C_Q = 0.75                               # SR001's largest inversion-invariant agreement between T and a foreign placement


def lineages(stage):
    return STAGE_LINEAGES[stage]


def stage_tasks(stage):
    """(source, body, unit, block) for every raw file of the stage."""
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "clock": CLOCK, "t_gen": T_GEN, "horizons": HORIZONS,
            "g_main": G_MAIN, "g_side": G_SIDE, "policies": POLICIES, "controller": CONTROLLER, "core": CORE,
            "context": CONTEXT, "optional": OPTIONAL, "situation_sigma": SITUATION_SIGMA, "sources": SOURCES,
            "stages": STAGES, "stage_tag": STAGE_TAG, "stage_lineages": {k: [x["label"] for x in v] for k, v in
                                                                         STAGE_LINEAGES.items()},
            "futures": FUTURES, "second_future": SECOND_FUTURE, "stage_parents": STAGE_PARENTS,
            "stage_stop_cap": STAGE_STOP_CAP, "halves": HALVES, "bodies": BODIES, "units": UNITS,
            "item_sets": ITEM_SETS, "k_rule": K_RULE, "step": STEP, "step_near0": STEP_NEAR0, "at_most_max": AT_MOST_MAX,
            "c_q": C_Q, "size": SIZE, "ar001_digest": A.digest(), "ar003_digest": A3.digest(), "ar005_digest": A5.digest(),
            "sr001_digest": SR.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    lane = Path(lane)
    dirs = ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002", "be005",
            "be006", "gc001", "np001", "ar001", "ar002", "ar003", "ar004", "ar005", "sr001", "e2e001", "e2e002")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m e2e002.design  ->  e2e002/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "e2e002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
