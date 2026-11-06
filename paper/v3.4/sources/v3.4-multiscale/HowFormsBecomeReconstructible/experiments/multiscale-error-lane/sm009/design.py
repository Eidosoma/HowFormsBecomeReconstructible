"""SM009's design: a signal of need (PLAN_SM009.md; the PI's word 22:10:26Z on 5 November 2026; the lead's brief,
REPORT_SM008's next step 1). Can a response route a shared field's help to the group's weakest member?

SM008's setting, imported unchanged (sm008 and sm007 are frozen): SM007's tissue and field, SM008's mixed tasks (16 cases:
the healthy unit's 8, then the struggling unit's 8) and its paired 2 x 4 layout (group g's position p holds case
(g + p) mod 8 of that position's role). Only the response differs between the arms:
  P (kind "field")    gain = G_DIST x (1 + KAPPA x_i)                            SM008's ruled response
  O (kind "own")      gain = G_DIST x (1 + KAPPA_O s_i)                          the sheet's own stress; the field not read
  R (kind "relative") gain = G_DIST x (1 + KAPPA_R max(0, s_i - GAMMA x_i / f_i)) its stress against its group's
x_i the exposure and s_i the own stress at the previous update; f_i the position's field factor (a constant of the medium).
Amendment 1 (PLAN_SM009.md): R is dropped after the pilot P65 (it starves uniform groups); phase B runs P and O only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sm007 import design as D7
from sm008 import design as D8

STUDY = "SM009"
TAG = "mse-sm009"                      # the recipients' births and noise (debug, preflight, development)
PROBE_TAG = "mse-p65"                  # the pilot P65's
KAPPA_TAG = "mse-p65k"                 # P65k's (engineering only; its noise used nowhere else)
RUNS = D7.RUNS

# ---------------------------------------------------------------- SM007's tissue and field, SM008's layout (unchanged)
SIDE, SIGMA, CHUNK = D7.SIDE, D7.SIGMA, D7.CHUNK
WINDOW, READS = D7.WINDOW, D7.READS
RESCUED = D7.RESCUED
G_DIST = D7.G_DIST
KAPPA = D7.KAPPA                       # SM007's frozen kappa (P61k): P's, reused and declared
GAMMA, LAMBDA = D7.GAMMA, D7.LAMBDA
SITES, MARGIN, LEAKS = D7.SITES, D7.MARGIN, D7.LEAKS
SM007_FROZEN = D8.SM007_FROZEN
SM008_FROZEN = {"commit": "1c74a528e8", "digest": "d69d35868e45fd5c4f2688507fc6ba4b7e9357ba53d2998d092fe42fd605c3b0"}
BODIES, ROLES, NCASE = D8.BODIES, D8.ROLES, D8.NCASE
GROUP, POSITIONS, CORNERS, INNER = D8.GROUP, D8.POSITIONS, D8.CORNERS, D8.INNER
COMPOSITIONS = {c: D8.COMPOSITIONS[c] for c in ("k0", "k1-corner", "k1-inner", "k2-apart", "k4-half", "k4-checker",
                                                "k7-corner", "k8")}
NGROUPS = D8.NGROUPS

# ---------------------------------------------------------------- the responses
ARMS = {"P": "field", "O": "own", "R": "relative"}
KIND_ARM = {v: k for k, v in ARMS.items()}
# KAPPA_O and KAPPA_R: P65k's open-loop matching (PLAN_SM009.md section 3; probes/results/p65k_sm009_kappa.json, 22:22:54Z
# on 5 November), set before any outcome value: in the reference (k4-half, absorbing, li4 and dw, AR005's 900799, kappa 0)
# the mean drivers are P 4.197386928362144, O 0.5515645114717922, R 0.027042227297126555; kappa_O x O = kappa_R x R = KAPPA x P
KAPPA_O = 11.549181607745833
KAPPA_R = 235.56190994860148
KAPPA_REF = {"source": "ar005/debug", "blocks": (900799,), "bodies": BODIES, "arrangement": "k4-half/absorbing",
             "futures": 1, "window": WINDOW, "tag": KAPPA_TAG}


# ---------------------------------------------------------------- arrangements: (label, composition, boundary, kind, lambda)
def _phase_a_set():
    out = [(f"{c}/absorbing/{arm}", c, "absorbing", ARMS[arm], LAMBDA) for arm in ("P", "O", "R") for c in COMPOSITIONS]
    out += [(f"iso8/absorbing/{arm}", "iso8", "absorbing", ARMS[arm], LAMBDA) for arm in ("P", "O")]
    out += [(f"{c}/sealed/P", c, "sealed", "field", LAMBDA) for c in ("k1-corner", "k8")]
    return tuple(out)


# PLAN_SM009.md Amendment 1 (the lead's rulings, sent 22:58:43Z; written 23:01:22Z): R is dropped. P65 and the debug run
# ran PHASE_A_SET (28 arrangements, 1,696 sheets a task-future, R included) under digest a35d609d5c07; phase B runs
# FULL_SET: P and O in every composition, iso8 under both, sealed k1-corner and k8 under P (20, 1,184 sheets).
PHASE_A_SET = _phase_a_set()
FULL_SET = tuple(a for a in PHASE_A_SET if a[3] != "relative")
STAGE_SETS = {"probe": PHASE_A_SET, "debug": PHASE_A_SET, "preflight": FULL_SET, "development": FULL_SET}
STAGE_WINDOW = {"debug": 2000}         # the debug run is short; every code path runs by then

# ---------------------------------------------------------------- the restored records (AR005's) and the stages
SOURCES = D7.SOURCES
AR005_DEV = D7.AR005_DEV
STAGES = {"probe": {"ar005/p53": (900729, 900739, 900749, 900759)},
          "debug": {"ar005/debug": (900799,)},
          "preflight": {"ar005/preflight": (900779, 900789)},
          "development": {"ar005/development": AR005_DEV}}
STAGE_TAG = {"probe": PROBE_TAG, "debug": TAG, "preflight": TAG, "development": TAG}
FUTURES = {"probe": 1, "debug": 2, "preflight": 1, "development": 1}
HALVES = D7.HALVES

# the statements' rule (BE002's, the lane's)
K_RULE = D7.K_RULE
STEP, STEP_NEAR0 = D7.STEP, D7.STEP_NEAR0
AT_MOST_MAX = D7.AT_MOST_MAX


def stage_tasks(stage):
    return [(src, b, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "kappa_tag": KAPPA_TAG, "side": SIDE, "sigma": SIGMA,
            "chunk": CHUNK, "window": WINDOW, "reads": READS, "rescued": RESCUED, "g_dist": G_DIST, "kappa": KAPPA,
            "kappa_o": KAPPA_O, "kappa_r": KAPPA_R, "kappa_ref": KAPPA_REF, "gamma": GAMMA, "lambda": LAMBDA,
            "sites": {str(k): v for k, v in SITES.items()}, "margin": MARGIN, "leaks": LEAKS, "sm007": SM007_FROZEN,
            "sm008": SM008_FROZEN, "bodies": BODIES, "roles": ROLES, "group": GROUP, "positions": POSITIONS,
            "corners": CORNERS, "inner": INNER, "compositions": COMPOSITIONS, "ngroups": NGROUPS, "arms": ARMS,
            "stage_sets": STAGE_SETS, "stage_window": STAGE_WINDOW, "sources": SOURCES, "stages": STAGES,
            "stage_tag": STAGE_TAG, "futures": FUTURES, "halves": HALVES, "k_rule": K_RULE, "step": STEP,
            "step_near0": STEP_NEAR0, "at_most_max": AT_MOST_MAX}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    """Every source the recipients' arithmetic and the restoration can reach (SM008's list, with sm009)."""
    lane = Path(lane)
    dirs = ("mse", "msegrid", "msefield", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002",
            "be005", "be006", "gc001", "np001", "ar001", "sm007", "sm008", "sm009")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm009.design  ->  sm009/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm009" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
