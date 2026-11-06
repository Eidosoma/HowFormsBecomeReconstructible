"""E2E005: a controller over the keeping rule. DRAFT for the lead's review (phase A). See PLAN_E2E005.md.

E2E004 found that no fixed rule in the newborns both keeps the acquired history and heals an inherited error: the record
keeping itself keeps everything and heals nothing, the body rewriting the record heals most and keeps least, and the vote
lies between. E2E005 asks whether a controller in each newborn, reading only that newborn's own state, keeps the history
as the record rule does and heals an inherited error as the body rule does: does its (keeping, healing) point land beyond
the fixed rules' line? li4 x F0 is read first: there the body's own preference erases the history.

Generation 0 is restored on E2E004's cohort: AR005's saved runs at t = 8,000 (no tissue episode, no block drawn). The
packets (e2e002.sim.packet_of, unchanged): protected storage (R0 with its bonds: keeping) and post-damage copying (the
record with memory@0's 4 x 4 patch flipped and its bonds consistent: healing). The outgoing record crosses each boundary
(SR001's packet: r, H, W; the strengths restart at STRENGTH0 x sign); nothing else crosses. The successors run E2E004's
batched generation of AR001's own update (e2e004.sim.generation's source, compiled with two declared substitutions, each
asserted to apply once: e2e005.sim). The routes:
  ctl     THE CONTROLLER, one per newborn: the record rule (record+parity) by default, and the body rule on the bonds
          touching a footprint while its switch is on. Its detector reads only the newborn's own body V and record r,
          every READ_EVERY updates from read_from: the windows (DET_STAR's geometry, AR003: boxes 2-12; at least n cells
          where the confident body disagrees with the confident record, |x| >= c; every cell of the window where both are
          confident disagreeing, q 1; none in the ring of width 2 around it, ring_max 0) that have held for `dwell`
          consecutive reads. The first time one holds, the detector fires (once a newborn): the footprint is every cell
          of the windows held at that read, dilated by 2 (BE002's footprint, AR002's dial), and the bonds touching it
          (BE002's junction rule) follow the body rule from that update to the generation's end. It never sees the
          template, the patch, the injury's site or a damage label.
  record  AR001's "record" policy (LR001's record+parity), E2E004's route, unchanged
  body    AR001's "body" policy, E2E004's route, unchanged
  vote    AR001's "vote" policy (vote2r with the second copy of the incoming record), E2E004's route, unchanged
  oracle  the same switch over the inherited patch itself (the patch dilated by 2, its touching bonds), on at the
          controller's first read, in the post-damage lineage only: it uses information the controller does not have,
          so it is reported only, as the ceiling of where-to-switch. On protected storage there is no inherited patch,
          so the oracle never switches there and would be the record rule's row (not run).
The detector's parameters (n, c, dwell, read_from) are chosen on AR005's tuning block 900717 by PLAN_E2E005.md's rule,
fixed before any tuning value (P62a); the geometry, READ_EVERY, the footprint and the duration are fixed in the plan.
Every rule reads the same births and noise streams (a future's names under E2E005's tag), so rows pair within cases.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ar001 import design as A
from e2e004 import design as D4
from sr001 import design as SR

STUDY = "E2E005"
TAG = "mse-e2e005"                      # the futures' tag (debug, preflight, development)
PROBE_TAG = "mse-p62"                   # the pilot P62's futures
TUNING_TAG = "mse-p62a"                 # the tuning P62a's futures
RUNS = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane"

CLOCK = dict(D4.CLOCK)                  # eta 3e-4, bond noise 3e-5, tau_c 15,000 (E2E004's, AR001's)
SIDE, GAIN, STRENGTH0, SIZE = D4.SIDE, D4.GAIN, D4.STRENGTH0, D4.SIZE
assert (SIDE, GAIN, STRENGTH0) == (SR.SIDE, SR.GAIN, SR.STRENGTH0)
T_GEN = D4.T_GEN                        # 8,000 updates a generation
HORIZONS = (1, 3, 8)
G_MAIN, G_SIDE = 8, 3
VMIN = A.VMIN                           # the AR line's confidence (lr005.sim.vote_sign): 0.2

# the routes: E2E004's fixed rules, the controller and the oracle
FIXED = ("body", "vote", "record")
ROUTES = FIXED + ("ctl", "oracle")
PARITY = ("record", "ctl", "oracle")    # the routes whose record-rule bonds take LR001's parity repair

# the controller's detector -----------------------------------------------------------------------------------------
GEOMETRY = {"boxes": tuple(range(2, 13)), "q": 1.0, "ring": 2, "ring_max": 0}   # DET_STAR's (AR003), fixed
READ_EVERY = 10                          # the detector reads every 10th update from read_from (fixed)
FOOT_D = A.SIG["d"]                      # 2: the footprint is the held windows' cells dilated by 2 (BE002's), fixed
DURATION = None                          # the switch holds from the firing to the generation's end (fixed)


def candidate(n, c, dwell, read_from):
    """A detector: DET_STAR's geometry on the newborn's body-record disagreement, at least n disagreeing cells, the
    confidence |x| >= c for body and record, `dwell` consecutive reads, reading from update read_from."""
    return dict(GEOMETRY, n=n, c=c, dwell=dwell, read_from=read_from, read_every=READ_EVERY, d=FOOT_D, duration=DURATION)


# the tuning grid, in its declared order (the AR line's own values first: n 3, c 0.2 and dwell 1 are DET_STAR's)
GRID = tuple((n, c, w, t) for t in (250, 1000) for w in (1, 20) for c in (0.2, 0.6) for n in (3, 2))
CANDIDATES = {f"n{n}-c{c:g}-w{w}-t{t}": candidate(n, c, w, t) for n, c, w, t in GRID}
TUNING_TOL = 0.005                       # the rule's tie band on the frontier excess (PLAN_E2E005.md)
# DETECTOR: chosen from the tuning block 900717 by PLAN_E2E005.md's rule (probes/p62a_e2e005_tuning.py; results in
# probes/results/p62a_e2e005_tuning.txt, 12:53Z on 5 November): n3-c0.6-w1-t1000, the largest frontier excess at g 1
# (E +0.0574: K -0.0068, H +0.0762, s 2.75); n2-c0.6-w1-t1000 (E +0.0554) lay within 0.005 of it and fired in more
# protected newborns (0.531 against 0.266). Until the tuning ran it held the grid's first candidate (n3-c0.2-w1-t250) as
# a placeholder for the engineering bridges and tests (P62s's timing read the placeholder's reads).
DETECTOR_NAME = "n3-c0.6-w1-t1000"
DETECTOR = CANDIDATES[DETECTOR_NAME]
ORACLE = {"oracle": True, "read_from": DETECTOR["read_from"], "d": FOOT_D, "duration": DURATION}

# the lineages: (label, generation-0 packet, route, stop)
L = lambda *x: dict(zip(("label", "packet", "route", "stop"), x))
POST = "post/memory@0"
CORE = (L("ctl/protected", "protected", "ctl", G_MAIN),
        L("record/protected", "protected", "record", G_MAIN),
        L("body/protected", "protected", "body", G_MAIN),
        L("vote/protected", "protected", "vote", G_MAIN),
        L("ctl/post", POST, "ctl", G_MAIN),
        L("record/post", POST, "record", G_MAIN),
        L("body/post", POST, "body", G_MAIN),
        L("vote/post", POST, "vote", G_MAIN),
        L("oracle/post", POST, "oracle", G_MAIN))
OPTIONAL = {"vms": (L("ctl/vms", "vms/memory@0", "ctl", G_MAIN), L("record/vms", "vms/memory@0", "record", G_MAIN),
                    L("body/vms", "vms/memory@0", "body", G_MAIN), L("vote/vms", "vms/memory@0", "vote", G_MAIN))}
TUNING = (L("record/protected", "protected", "record", 1), L("body/protected", "protected", "body", 1),
          L("record/post", POST, "record", 1), L("body/post", POST, "body", 1), L("oracle/post", POST, "oracle", 1)) + \
    tuple(L(f"ctl:{nm}/{lab}", pk, f"ctl:{nm}", 1) for nm in CANDIDATES for lab, pk in (("protected", "protected"),
                                                                                       ("post", POST)))
ALL = CORE + tuple(x for v in OPTIONAL.values() for x in v)

# the restored sources (AR005's raw final states) and the stages
SOURCES = {"ar005/tuning": {"root": f"{RUNS}/ar005/tuning", "tag": "mse-p53", "purpose": "engineering"},
           "ar005/p53": {"root": f"{RUNS}/ar005/p53", "tag": "mse-p53", "purpose": "engineering"},
           "ar005/debug": {"root": f"{RUNS}/ar005/debug", "tag": "mse-ar005", "purpose": "engineering"},
           "ar005/preflight": {"root": f"{RUNS}/ar005/preflight", "tag": "mse-ar005", "purpose": "engineering"},
           "ar005/development": {"root": f"{RUNS}/ar005/development", "tag": "mse-ar005", "purpose": "development"}}
AR005_DEV = D4.AR005_DEV
STAGES = {"tuning": {"ar005/tuning": (900717,)},
          "probe": {"ar005/p53": (900729, 900739, 900749, 900759)},
          "debug": {"ar005/debug": (900799,)},
          "preflight": {"ar005/preflight": (900779, 900789)},
          "development": {"ar005/development": AR005_DEV}}
STAGE_TAG = {"tuning": TUNING_TAG, "probe": PROBE_TAG, "debug": TAG, "preflight": TAG, "development": TAG}
STAGE_LINEAGES = {"tuning": TUNING, "probe": CORE, "debug": ALL, "preflight": CORE, "development": CORE}
FUTURES = {"tuning": 1, "probe": 1, "debug": 1, "preflight": 1, "development": 1}
STAGE_PARENTS = {"probe": (0,)}          # the pilot reads parent 0's four cases of every task (as E2E004's P60)
STAGE_STOP_CAP = {"tuning": 1, "debug": G_SIDE}   # the tuning reads generation 1; the debug run caps every row at g 3
HALVES = {"probe": ((900729, 900739), (900749, 900759)), "development": (AR005_DEV[:8], AR005_DEV[8:])}
BODIES, UNITS = A.BODIES, A.UNITS
ITEM_SETS = D4.ITEM_SETS                 # native li4 x S4; particular li4 x F0 (read first); permissive dw

# the statements' rule (BE002's, as in E2E001-E2E004)
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP, STEP_NEAR0 = 0.01, 0.005
AT_MOST_MAX = 0.05
C_Q = 0.75


def lineages(stage):
    return STAGE_LINEAGES[stage]


def stage_tasks(stage):
    """(source, body, unit, block) for every raw file of the stage."""
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES for u in UNITS]


def route_cfg(route):
    """The switch configuration of a switched route: 'ctl' (the design's detector), 'ctl:<candidate>' (the tuning) or
    'oracle'."""
    if route == "ctl":
        return DETECTOR
    if route == "oracle":
        return ORACLE
    if route.startswith("ctl:"):
        return CANDIDATES[route[4:]]
    raise KeyError(route)


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "tuning_tag": TUNING_TAG, "clock": CLOCK, "t_gen": T_GEN,
            "horizons": HORIZONS, "g_main": G_MAIN, "g_side": G_SIDE, "vmin": VMIN, "fixed": FIXED, "routes": ROUTES,
            "parity": PARITY, "geometry": GEOMETRY, "read_every": READ_EVERY, "foot_d": FOOT_D, "duration": DURATION,
            "grid": GRID, "candidates": CANDIDATES, "tuning_tol": TUNING_TOL, "detector_name": DETECTOR_NAME,
            "detector": DETECTOR, "oracle": ORACLE, "core": CORE, "optional": OPTIONAL, "tuning": TUNING,
            "sources": SOURCES, "stages": STAGES, "stage_tag": STAGE_TAG,
            "stage_lineages": {k: [x["label"] for x in v] for k, v in STAGE_LINEAGES.items()}, "futures": FUTURES,
            "stage_parents": STAGE_PARENTS, "stage_stop_cap": STAGE_STOP_CAP, "halves": HALVES, "bodies": BODIES,
            "units": UNITS, "item_sets": ITEM_SETS, "k_rule": K_RULE, "step": STEP, "step_near0": STEP_NEAR0,
            "at_most_max": AT_MOST_MAX, "c_q": C_Q, "size": SIZE, "ar001_digest": A.digest(), "sr001_digest": SR.digest(),
            "e2e004_digest": D4.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    lane = Path(lane)
    dirs = ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002", "be005",
            "be006", "gc001", "np001", "ar001", "ar002", "ar003", "ar004", "ar005", "sr001", "e2e001", "e2e002", "e2e004",
            "e2e005")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m e2e005.design  ->  e2e005/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "e2e005" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
