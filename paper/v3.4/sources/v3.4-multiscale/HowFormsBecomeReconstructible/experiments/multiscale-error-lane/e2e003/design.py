"""E2E003: repeated injury. A fresh injury in every generation, with the confirmed controllers acting in every generation.
DRAFT for the lead's review (phase A). See PLAN_E2E003.md.

E2E002 (PLAN_E2E002.md) had vms act in every generation with no new injury, and its pilot P58 found every = once: after
generation 0 the controller had nothing to repair. E2E003 injures every successor: memory damage on a fresh 4 x 4 patch at
each generation's update 0, disjoint from every earlier patch and generation 0's, and asks whether a confirmed controller
acting in every generation (vtol, AR006C's; vms, AR003C's) keeps the lineage's acquired form and history better than acting
once, better than the best fixed policy (the vote), and how close it comes to an uninjured lineage.

Generation 0 is restored: AR006's saved runs at t = 8,000 (its development blocks for the development; P57's records for
the pilot; its debug and preflight records for the debug run and the preflight). The successors run E2E002's machinery
(e2e002.sim.generation, ar003.sim.run_vd's update, its births, streams, handoff, second record and birth cue), with its one
detector call routed to ar006.sim.detect so that vtol's split guard runs (e2e003.sim), and e2e003.sim's own lineage loop
adds the injury. The policy is a parameter (POLICIES).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ar001 import design as A
from ar003 import design as A3
from ar006 import design as A6
from e2e002 import design as E2D

STUDY = "E2E003"
TAG = "mse-e2e003"                      # the successors' and the injuries' tag (debug, preflight, development)
PROBE_TAG = "mse-p59"                   # the pilot P59's
RUNS = E2D.RUNS

CLOCK, SIDE, GAIN, STRENGTH0, SIZE, T_GEN = E2D.CLOCK, E2D.SIDE, E2D.GAIN, E2D.STRENGTH0, E2D.SIZE, E2D.T_GEN
HORIZONS = (1, 3, 8)
G_MAIN = 8
G_DEBUG = 3

# the successors' policies: a vote-default arm's detector configuration (ar006.sim.detect)
POLICIES = {"vote": {"never": True},                    # "once" and the passive lineages: the vote
            "vms": A6.VD_DETECTORS["vms"],              # AR003C's confirmed controller (DET_STAR), as frozen
            "vtol": A6.VD_DETECTORS["vtol"]}            # AR006C's confirmed controller (the split guard), as frozen
CONTROLLER = "vtol"

# the injury: memory damage (the record flipped on the patch, its bonds kept consistent; the body and the cue right) on a
# fresh SIZE x SIZE patch in every generation g >= 1, at the generation's update 0 (after birth and the cue)
INJURY = {"situation": "memory", "size": SIZE, "stream": ("e2e003", "injury"),
          "rule": "per case and generation, the first attempt (address(tag, block, message, parent, 'e2e003', 'injury', "
                  "g, attempt)) whose patch is disjoint from generation 0's patch and every earlier generation's"}
MAX_ATTEMPTS = 10000

# the lineages: (label, generation-0 packet, successors' policy, the lineage's sigma, stop, injured in successors)
L = lambda *x: dict(zip(("label", "packet", "policy", "sigma", "stop", "injured"), x))
CORE = (L("vtol-every/memory@0", "vtol/memory@0", "vtol", 0.0, G_MAIN, True),
        L("vtol-once/memory@0", "vtol/memory@0", "vote", 0.0, G_MAIN, True),
        L("vote/memory@0", "vote/memory@0", "vote", 0.0, G_MAIN, True),
        L("uninjured", "vote/none@0", "vote", 0.0, G_MAIN, False),
        L("vtol-every/memory@1", "vtol/memory@1", "vtol", 1.0, G_MAIN, True),
        L("vms-every/memory@1", "vms/memory@1", "vms", 1.0, G_MAIN, True),
        L("vtol-once/memory@1", "vtol/memory@1", "vote", 1.0, G_MAIN, True),
        L("vote/memory@1", "vote/memory@0", "vote", 1.0, G_MAIN, True))     # the vote's sigma-1 run is its sigma-0 run
OPTIONAL = {"vms-every/memory@0": (L("vms-every/memory@0", "vms/memory@0", "vms", 0.0, G_MAIN, True),)}
ALL = CORE + tuple(x for v in OPTIONAL.values() for x in v)

# the restored sources (AR006's raw final states) and the stages
R6 = f"{RUNS}/ar006"
SOURCES = {"ar006/p57": {"root": f"{R6}/p57", "tag": A6.PROBE_TAG, "purpose": "engineering"},
           "ar006/debug": {"root": f"{R6}/debug", "tag": A6.TAG, "purpose": "engineering"},
           "ar006/preflight": {"root": f"{R6}/preflight", "tag": A6.TAG, "purpose": "engineering"},
           "ar006/development": {"root": f"{R6}/development", "tag": A6.TAG, "purpose": A6.PURPOSE["development"]}}
AR006_DEV = A6.DEVELOPMENT_BLOCKS
STAGES = {"probe": {"ar006/p57": A6.PROBE_BLOCKS},
          "debug": {"ar006/debug": A6.DEBUG_BLOCKS},
          "preflight": {"ar006/preflight": A6.PREFLIGHT_BLOCKS},
          "development": {"ar006/development": AR006_DEV}}
STAGE_TAG = {"probe": PROBE_TAG, "debug": TAG, "preflight": TAG, "development": TAG}
STAGE_LINEAGES = {"probe": CORE, "debug": ALL, "preflight": CORE, "development": CORE}
FUTURES = {"probe": 1, "debug": 1, "preflight": 1, "development": 1}
STAGE_PARENTS = {"probe": (0,)}          # the pilot reads parent 0's four cases of every task (phase A's cap)
STAGE_STOP_CAP = {"debug": G_DEBUG}      # the debug run caps every row at generation 3
HALVES = {"probe": (A6.PROBE_BLOCKS[:2], A6.PROBE_BLOCKS[2:]), "development": (AR006_DEV[:8], AR006_DEV[8:])}
BODIES, UNITS = A.BODIES, A.UNITS
ITEM_SETS = E2D.ITEM_SETS                # native (li4 S4), particular (li4 F0: read first), permissive (dw)

# the statements' rule (BE002's, the lane's, as in E2E001 and E2E002)
K_RULE, STEP, STEP_NEAR0, AT_MOST_MAX, C_Q = E2D.K_RULE, E2D.STEP, E2D.STEP_NEAR0, E2D.AT_MOST_MAX, E2D.C_Q


def lineages(stage):
    return STAGE_LINEAGES[stage]


def stage_tasks(stage):
    """(source, body, unit, block) for every raw file of the stage."""
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "clock": CLOCK, "t_gen": T_GEN, "horizons": HORIZONS,
            "g_main": G_MAIN, "g_debug": G_DEBUG, "policies": POLICIES, "controller": CONTROLLER, "injury": INJURY,
            "max_attempts": MAX_ATTEMPTS, "core": CORE, "optional": OPTIONAL, "sources": SOURCES, "stages": STAGES,
            "stage_tag": STAGE_TAG, "stage_lineages": {k: [x["label"] for x in v] for k, v in STAGE_LINEAGES.items()},
            "futures": FUTURES, "stage_parents": STAGE_PARENTS, "stage_stop_cap": STAGE_STOP_CAP, "halves": HALVES,
            "bodies": BODIES, "units": UNITS, "item_sets": ITEM_SETS, "k_rule": K_RULE, "step": STEP,
            "step_near0": STEP_NEAR0, "at_most_max": AT_MOST_MAX, "c_q": C_Q, "size": SIZE, "side": SIDE,
            "ar001_digest": A.digest(), "ar003_digest": A3.digest(), "ar006_digest": A6.digest(),
            "e2e002_digest": E2D.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    lane = Path(lane)
    dirs = ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002", "be005",
            "be006", "gc001", "np001", "ar001", "ar002", "ar003", "ar004", "ar005", "ar006", "sr001", "e2e001", "e2e002",
            "e2e003")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m e2e003.design  ->  e2e003/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "e2e003" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
