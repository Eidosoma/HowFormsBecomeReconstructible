"""E2E001: the lane's first end-to-end test (the charter's ME003 in a minimal form). DRAFT for the lead's review (phase A).

Generation 0 is restored: AR005's saved runs at t = 8,000 (the AR tissue: AR001's at its calibrated clock). Its outgoing
record (SR001's packet: the first record's values r and bond signs H, W; the strengths restart at STRENGTH0 x sign)
crosses to newborn successors, which run SR001's body route at the AR tissue's clock for generations of 8,000 updates.
Every policy arm is "removal after one rescue": the controller acted in generation 0 only. No tissue block is drawn: the
records' blocks are the population units, and the futures are new draws on them under a new tag. See PLAN_E2E001.md.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ar001 import design as A
from sr001 import design as SR

STUDY = "E2E001"
TAG = "mse-e2e001"                      # the futures' tag (debug, preflight, development)
PROBE_TAG = "mse-p56"                   # the pilot P56's futures
RUNS = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane"

# the AR tissue (AR001's, at its calibrated clock) and the successors' route (SR001's body route at that clock)
CLOCK = dict(A.CLOCK)                   # eta 3e-4, bond noise 3e-5, tau_c 15,000
SIDE, GAIN, STRENGTH0, SIZE = A.SIDE, A.GAIN, A.STRENGTH0, A.SIZE
assert (SIDE, GAIN, STRENGTH0) == (SR.SIDE, SR.GAIN, SR.STRENGTH0)
ROUTE = SR.Route("body@3e-05", CLOCK["rate"], "body", False, GAIN)        # read at gain 0.2, written by the body
NOREAD = SR.Route("noread@3e-05", CLOCK["rate"], "body", False, 0.0)      # disabled reading: the native baseline
T_GEN = A.WINDOW                        # 8,000 updates: generation 0's own life, from the injury to the handoff
HORIZONS = (1, 3, 8)
G_MAIN, G_SIDE = 8, 3                   # the main lineages run to 8; the second tier, the controls and Q to 3

# the restored sources (the AR runs' raw final states) and their tags
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
FUTURES = {"probe": 1, "debug": 1, "preflight": 2, "development": 2}
SIDE_FUTURES = 1                         # the second tier, the controls and Q run in the first future only; later futures
                                         # run the main rows (to G_MAIN) only (the lead's ruling, about 13:45Z on 3 November)
HALVES = {"probe": ((900729, 900739), (900749, 900759)), "development": (AR005_DEV[:8], AR005_DEV[8:])}
BODIES, UNITS = A.BODIES, A.UNITS        # dw, li4; S4_t0, S4_t1, F0_t0, F0_t1: the eight unit-body pairs
ITEM_SETS = {"native": (("li4", "S4_t0"), ("li4", "S4_t1")),
             "particular": (("li4", "F0_t0"), ("li4", "F0_t1")),       # non-native: li4 would not make two domains
             "permissive": tuple(("dw", u) for u in UNITS)}

# situations (4 x 4 patch) and arms
MAIN = ("memory@0", "memory@1", "none@0")
SECOND = ("cue@0", "correlated@0")
POLICIES = ("vote", "vms", "vguard")    # vpool restored and hashed, not run (the lead's ruling)
CONTROLLER = "vguard"                    # AR005's: the foreign row and the statements' controller
PERM = lambda m: (m + 1) % 4             # own against foreign: the fixed orthogonal-message permutation
RECORD_HIT = {"memory": True, "correlated": True, "none": False, "cue": False, "body": False}

# the statements (declared in PLAN_E2E001.md before any value); the rule (BE002's)
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP, STEP_NEAR0 = 0.01, 0.005
AT_MOST_MAX = 0.05
C_Q = 0.75                               # SR001's largest inversion-invariant agreement between T and a foreign placement


def stage_tasks(stage):
    """(source, body, unit, block) for every raw file of the stage."""
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "clock": CLOCK, "route": ROUTE.__dict__,
            "noread": NOREAD.__dict__, "t_gen": T_GEN, "horizons": HORIZONS, "g_main": G_MAIN, "g_side": G_SIDE,
            "sources": SOURCES, "stages": STAGES, "stage_tag": STAGE_TAG, "futures": FUTURES, "side_futures": SIDE_FUTURES, "halves": HALVES,
            "bodies": BODIES, "units": UNITS, "item_sets": ITEM_SETS, "main": MAIN, "second": SECOND,
            "policies": POLICIES, "controller": CONTROLLER, "perm": [PERM(m) for m in range(4)], "k_rule": K_RULE,
            "step": STEP, "step_near0": STEP_NEAR0, "at_most_max": AT_MOST_MAX, "c_q": C_Q, "size": SIZE,
            "ar001_digest": A.digest(), "sr001_digest": SR.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    lane = Path(lane)
    dirs = ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002", "be005",
            "be006", "gc001", "np001", "ar001", "ar002", "ar003", "ar004", "ar005", "sr001", "e2e001")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m e2e001.design  ->  e2e001/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "e2e001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
