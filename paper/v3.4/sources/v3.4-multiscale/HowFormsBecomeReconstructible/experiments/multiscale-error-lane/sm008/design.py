"""SM008's design: mixed groups (PLAN_SM008.md; the PI's word 15:42:49Z on 5 November 2026; the lead's brief, REPORT_SM007's
next step 3). Does a shared field help its weakest member?

SM007's tissue, field and ruled coupling, imported unchanged (sm007 is frozen): fresh AR-tissue newborns read a fixed
inherited record (AR005's restored R0, never written) at the disturbed gain, each emitting its stress (its mean |r - V-tilde|)
into a shared msefield medium and reading at G_DIST x (1 + KAPPA x its exposure at the previous update). A task is one body
and one block with both units' cases (16): the healthy unit's 8 (indices 0-7) and the struggling unit's 8 (8-15). Groups
of 8 sheets in a 2 x 4 rectangle mix k struggling members at declared positions; group g's position p holds case
(g + p) mod 8 of that position's role in every composition, so the compositions are paired by case and position.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from msefield.core import rectangle
from sm007 import design as D7

STUDY = "SM008"
TAG = "mse-sm008"                      # the recipients' births and noise (debug, preflight, development)
PROBE_TAG = "mse-p64"                  # the pilot P64's
RUNS = D7.RUNS

# ---------------------------------------------------------------- SM007's tissue, field and coupling (unchanged)
SIDE, SIGMA, CHUNK = D7.SIDE, D7.SIGMA, D7.CHUNK
WINDOW, READS = D7.WINDOW, D7.READS
RESCUED = D7.RESCUED
G_DIST, G_LANE = D7.G_DIST, D7.G_LANE
KAPPA = D7.KAPPA                       # SM007's frozen kappa (P61k), reused and declared, not recomputed
KAPPA_PAPER = D7.KAPPA_PAPER           # SM007's frozen kappa_p (P61p), for the preprint's stress arm
GAMMA, LAMBDA, LAMBDA_SHARED = D7.GAMMA, D7.LAMBDA, D7.LAMBDA_SHARED
SITES, MARGIN, LEAKS = D7.SITES, D7.MARGIN, D7.LEAKS
SM007_FROZEN = {"commit": "98e4de5ef1", "digest": "6f83374954e2fc02e8d09e4f2a3a65a9e74c54bb5401257be04d2f6494a4d8e4"}

# ---------------------------------------------------------------- the roles (SM007's development levels, declared)
BODIES = ("li4", "dw")                 # li4 the primary; dw secondary and reported
ROLES = {"li4": ("S4_t1", "F0_t1"),    # (healthy, struggling): SM007's isolated a 0.895 / 0.712
         "dw": ("F0_t1", "S4_t1")}     # (stronger, weaker): 0.962 / 0.848
ROLE_LEVELS_SM007 = {("li4", "S4_t1"): 0.8947, ("li4", "F0_t1"): 0.7118, ("dw", "F0_t1"): 0.9623, ("dw", "S4_t1"): 0.8477}
NCASE = 8                              # cases a unit a block (messages 0-3 x parents 0-1)

# ---------------------------------------------------------------- the group and the compositions
GROUP = "2x4"
POSITIONS = rectangle(2, 4)            # row-major: 0-3 the top row, 4-7 the bottom
CORNERS, INNER = (0, 3, 4, 7), (1, 2, 5, 6)
COMPOSITIONS = {"k0": (), "k1-corner": (0,), "k1-inner": (1,), "k2-adjacent": (1, 2), "k2-apart": (0, 7),
                "k4-half": (0, 1, 4, 5), "k4-checker": (0, 2, 5, 7), "k6": (0, 3, 4, 5, 6, 7),
                "k7-corner": (1, 2, 3, 4, 5, 6, 7), "k7-inner": (0, 2, 3, 4, 5, 6, 7), "k8": tuple(range(8))}
NGROUPS = 8                            # group g = 0..7: position p holds case (g + p) mod 8 of that position's role


# ---------------------------------------------------------------- arrangements: (label, composition, boundary, kind, lambda)
#   kind: "field" (each sheet's own exposure, the ruled stress), "paper" (the preprint's Eq. 1 stress, SM007's Amendment 2)
def _full_set():
    out = [(f"{c}/{b}", c, b, "field", LAMBDA) for b in ("absorbing", "sealed") for c in COMPOSITIONS]
    out += [("iso8/absorbing", "iso8", "absorbing", "field", LAMBDA)]
    out += [(f"{c}/absorbing/paper", c, "absorbing", "paper", LAMBDA) for c in ("k0", "k1-corner", "k8")]
    out += [(f"{c}/absorbing/shared", c, "absorbing", "field", LAMBDA_SHARED) for c in ("k0", "k1-corner", "k7-corner", "k8")]
    return tuple(out)


FULL_SET = _full_set()
STAGE_SETS = {"probe": FULL_SET, "debug": FULL_SET, "preflight": FULL_SET, "development": FULL_SET}
STAGE_WINDOW = {"debug": 2000}         # the debug run is short; every code path runs by then

# ---------------------------------------------------------------- the restored records (AR005's) and the stages
SOURCES = D7.SOURCES
AR005_DEV = D7.AR005_DEV
STAGES = {"probe": {"ar005/p53": (900729, 900739, 900749, 900759)},
          "debug": {"ar005/debug": (900799,)},
          "preflight": {"ar005/preflight": (900779, 900789)},
          "development": {"ar005/development": AR005_DEV}}
STAGE_TAG = {"probe": PROBE_TAG, "debug": TAG, "preflight": TAG, "development": TAG}
FUTURES = {"probe": 1, "debug": 2, "preflight": 1, "development": 1}   # Amendment 1: one future in phase B
HALVES = D7.HALVES

# the statements' rule (BE002's, the lane's)
K_RULE = D7.K_RULE
STEP, STEP_NEAR0 = D7.STEP, D7.STEP_NEAR0
AT_MOST_MAX = D7.AT_MOST_MAX


def stage_tasks(stage):
    return [(src, b, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "side": SIDE, "sigma": SIGMA, "chunk": CHUNK,
            "window": WINDOW, "reads": READS, "rescued": RESCUED, "g_dist": G_DIST, "g_lane": G_LANE, "kappa": KAPPA,
            "kappa_paper": KAPPA_PAPER, "gamma": GAMMA, "lambda": LAMBDA, "lambda_shared": LAMBDA_SHARED,
            "sites": {str(k): v for k, v in SITES.items()}, "margin": MARGIN, "leaks": LEAKS, "sm007": SM007_FROZEN,
            "bodies": BODIES, "roles": ROLES, "role_levels_sm007": {f"{b}/{u}": v for (b, u), v in ROLE_LEVELS_SM007.items()},
            "group": GROUP, "positions": POSITIONS, "corners": CORNERS, "inner": INNER, "compositions": COMPOSITIONS,
            "ngroups": NGROUPS, "stage_sets": STAGE_SETS, "stage_window": STAGE_WINDOW, "sources": SOURCES,
            "stages": STAGES, "stage_tag": STAGE_TAG, "futures": FUTURES, "halves": HALVES, "k_rule": K_RULE,
            "step": STEP, "step_near0": STEP_NEAR0, "at_most_max": AT_MOST_MAX}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    """Every source the recipients' arithmetic and the restoration can reach (SM007's list, with sm008)."""
    lane = Path(lane)
    dirs = ("mse", "msegrid", "msefield", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002",
            "be005", "be006", "gc001", "np001", "ar001", "sm007", "sm008")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm008.design  ->  sm008/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm008" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
