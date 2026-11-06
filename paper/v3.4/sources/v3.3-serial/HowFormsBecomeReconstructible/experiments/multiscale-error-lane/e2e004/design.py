"""E2E004: what keeps a record through renewal. DRAFT for the lead's review (phase A). See PLAN_E2E004.md.

Generation 0 is restored, as in E2E001 and E2E002: AR005's saved runs at t = 8,000 (no tissue episode, no block drawn).
The outgoing record (SR001's packet: r, H, W; the strengths restart at STRENGTH0 x sign) crosses to newborn successors.
The successors run one fixed rule in every generation (no detector, no controller), a route:
  body    the record learns the body's co-activity (AR001's "body" policy; bit for bit E2E001's successors, SR001's body
          route at the AR clock: P60s)
  vote    the vote: vote2r, the majority of the body's and two record copies' relations, the second a copy of the incoming
          record at birth (AR001's "vote" policy; bit for bit E2E002's "once" successors: P60s)
  record  the record keeping itself: AR001's "record" policy (LR001's record+parity: the record relearns its own
          relations, and parity repairs its bonds)
  vote1   (optional) the vote with one record: vote2r's arithmetic without the second copy's term; where the body and the
          record disagree the relation's sum is 0, and AR001's learning mask (a target of 0 learns nothing) holds the bond
All routes' successors share the births and the noise streams (a future's names under E2E004's tag), so route contrasts
pair within futures.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ar001 import design as A
from sr001 import design as SR

STUDY = "E2E004"
TAG = "mse-e2e004"                      # the futures' tag (debug, preflight, development)
PROBE_TAG = "mse-p60"                   # the pilot P60's futures
RUNS = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane"

CLOCK = dict(A.CLOCK)                   # eta 3e-4, bond noise 3e-5, tau_c 15,000
SIDE, GAIN, STRENGTH0, SIZE = A.SIDE, A.GAIN, A.STRENGTH0, A.SIZE
assert (SIDE, GAIN, STRENGTH0) == (SR.SIDE, SR.GAIN, SR.STRENGTH0)
T_GEN = A.WINDOW                        # 8,000 updates: generation 0's own life, from the injury to the handoff
HORIZONS = (1, 3, 8)
G_MAIN, G_SIDE = 8, 3

# the successors' routes: AR001's fixed policies (ar001.sim.run's kinds), plus the one-record vote
ROUTES = ("body", "vote", "record", "vote1")
TWO = ("vote",)                          # the routes that carry a second record

# the lineages: (label, generation-0 packet, route, stop)
L = lambda *x: dict(zip(("label", "packet", "route", "stop"), x))
CORE = (L("body/protected", "protected", "body", G_MAIN),
        L("vote/protected", "protected", "vote", G_MAIN),
        L("record/protected", "protected", "record", G_MAIN),
        L("body/post", "post/memory@0", "body", G_MAIN),
        L("vote/post", "post/memory@0", "vote", G_MAIN),
        L("record/post", "post/memory@0", "record", G_MAIN))
OPTIONAL = {"vote1": (L("vote1/protected", "protected", "vote1", G_MAIN), L("vote1/post", "post/memory@0", "vote1", G_MAIN)),
            "vms": (L("body/vms", "vms/memory@0", "body", G_MAIN), L("vote/vms", "vms/memory@0", "vote", G_MAIN),
                    L("record/vms", "vms/memory@0", "record", G_MAIN))}
ALL = CORE + tuple(x for v in OPTIONAL.values() for x in v)

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
STAGE_LINEAGES = {"probe": CORE + OPTIONAL["vote1"], "debug": ALL, "preflight": CORE + OPTIONAL["vote1"],
                  "development": CORE + OPTIONAL["vote1"]}
FUTURES = {"probe": 1, "debug": 1, "preflight": 1, "development": 1}
STAGE_PARENTS = {"probe": (0,)}          # the pilot reads parent 0's four cases of every task (as P58); every other stage all eight
STAGE_STOP_CAP = {"debug": G_SIDE}       # the debug run caps every row at generation 3 (every code path runs by then)
HALVES = {"probe": ((900729, 900739), (900749, 900759)), "development": (AR005_DEV[:8], AR005_DEV[8:])}
BODIES, UNITS = A.BODIES, A.UNITS
ITEM_SETS = {"native": (("li4", "S4_t0"), ("li4", "S4_t1")),
             "particular": (("li4", "F0_t0"), ("li4", "F0_t1")),       # read first (the lead's ruling)
             "permissive": tuple(("dw", u) for u in UNITS)}
RECORD_HIT = {"memory": True, "correlated": True, "none": False, "cue": False, "body": False}

# the statements' rule (BE002's, as in E2E001 and E2E002)
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP, STEP_NEAR0 = 0.01, 0.005
AT_MOST_MAX = 0.05
C_Q = 0.75


def lineages(stage):
    return STAGE_LINEAGES[stage]


def stage_tasks(stage):
    """(source, body, unit, block) for every raw file of the stage."""
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "clock": CLOCK, "t_gen": T_GEN, "horizons": HORIZONS,
            "g_main": G_MAIN, "g_side": G_SIDE, "routes": ROUTES, "two": TWO, "core": CORE, "optional": OPTIONAL,
            "sources": SOURCES, "stages": STAGES, "stage_tag": STAGE_TAG,
            "stage_lineages": {k: [x["label"] for x in v] for k, v in STAGE_LINEAGES.items()}, "futures": FUTURES,
            "stage_parents": STAGE_PARENTS, "stage_stop_cap": STAGE_STOP_CAP, "halves": HALVES, "bodies": BODIES,
            "units": UNITS, "item_sets": ITEM_SETS, "k_rule": K_RULE, "step": STEP, "step_near0": STEP_NEAR0,
            "at_most_max": AT_MOST_MAX, "c_q": C_Q, "size": SIZE, "ar001_digest": A.digest(), "sr001_digest": SR.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    lane = Path(lane)
    dirs = ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002", "be005",
            "be006", "gc001", "np001", "ar001", "ar002", "ar003", "ar004", "ar005", "sr001", "e2e001", "e2e002", "e2e004")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m e2e004.design  ->  e2e004/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "e2e004" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
