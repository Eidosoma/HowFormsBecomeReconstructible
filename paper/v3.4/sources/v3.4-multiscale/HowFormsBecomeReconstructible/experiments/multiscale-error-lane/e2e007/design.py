"""E2E007: the response's sign and the injury's target. DRAFT for the lead's review (phase A). See PLAN_E2E007.md.

E2E006's renewal under repeated injury with SM007's shared field (imported unchanged: e2e006 is frozen), crossed in six
paired rows: the response {none, raise, relax} x the injury's target {memory, body}; from Amendment 1 a seventh,
relax-matched/memory (relax at the kappa' that matches raise's realized integrated response, reported only). raise is E2E006's ruled response (the
reading gain x (1 + kappa x)), relax its opposite sign (the reading gain / (1 + kappa x)), with E2E006's kappa. memory is
E2E003's injury (the generation's patch flipped in the incoming record at update 0); body flips the same scheduled patch
in the newborn's body (V and its smoothed state E) at update T_GEN / 4, the record untouched.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ar001 import design as A
from ar006 import design as A6
from e2e002 import design as E2D
from e2e003 import design as E3D
from e2e006 import design as D6

STUDY = "E2E007"
TAG = "mse-e2e007"                      # the successors', the injuries' and the fresh successors' tag
PROBE_TAG = "mse-p66"                   # the pilot P66's
BRIDGE_TAG = "mse-p66s"                 # P66s's short engineering runs
RUNS = E2D.RUNS

CLOCK, SIDE, GAIN, STRENGTH0, SIZE, T_GEN = D6.CLOCK, D6.SIDE, D6.GAIN, D6.STRENGTH0, D6.SIZE, D6.T_GEN
HORIZONS = (1, 3, 8)
G_MAIN = 8
G_DEBUG = 3
POLICIES = D6.POLICIES                   # vote, vms, vtol (E2E003's, as frozen); E2E007's rows all run the vote
INJURY = D6.INJURY                       # E2E003's repeated injury, its schedule drawn under the stage's tag
FIELD = D6.FIELD                         # SM007's msefield as E2E006 bound it (kappa 1.944 by P63k), unchanged

# the response: "none" (no field: E2E006's vote/none), "raise" (the reading gain x (1 + kappa x): E2E006's vote/shared),
# "relax" (the reading gain / (1 + kappa x): the opposite sign, symmetric in log gain, never below 0), x the sheet's exposure
# at the previous update, kappa FIELD's; the field rows meet E2E006's shared 2 x 4 medium, reset at every birth, the
# response acting in every update
RESPONSES = ("none", "raise", "relax")
SIGN = {"raise": 1, "relax": -1}
# the injury's target: "memory" (E2E003's: the generation's patch flipped in the incoming record at update 0, its bonds kept
# consistent), "body" (the same scheduled patch flipped in the newborn's body, V -> -V and E -> -E, just before the body step
# of update T_GEN / 4, the record, its bonds and the second record untouched)
TARGETS = ("memory", "body")
BODY_FRAC = 4                            # the body injury at update t_gen // BODY_FRAC (2,000 of 8,000)
# the observer (reported, output only): the body's agreement with its own record on the generation's patch at these updates,
# as fractions of the generation's length t_gen: t_body - 1, t_body + t_gen/80, + t_gen/16, + t_gen/4, and t_gen
OBS = ("pre", "p80", "p16", "p4", "end")


def t_body(t_gen=T_GEN):
    return t_gen // BODY_FRAC


def obs_updates(t_gen=T_GEN):
    tb = t_body(t_gen)
    return {"pre": tb - 1, "p80": tb + t_gen // 80, "p16": tb + t_gen // 16, "p4": tb + t_gen // 4, "end": t_gen}


def _row(response, target, kappa_key=None, label=None):
    field = response != "none"
    return {"label": label or f"{response}/{target}", "packet": "vote/memory@0", "policy": "vote", "sigma": 0.0,
            "stop": G_MAIN, "injured": True, "target": target, "response": response, "field": "shared" if field else "none",
            "medium": "reset" if field else "-", "window": "full" if field else "-", "kappa_key": kappa_key}


ROWS = tuple(_row(r, t) for t in TARGETS for r in RESPONSES)        # the six (phase A; the registered parts)
# Amendment 1 (the lead's ruling 4): a size-matched relax row on memory injury, reported and not registered. Its kappa'
# is fixed by P66k's closed-loop rule: its realized integrated kappa' x equals raise/memory's realized integrated kappa x,
# pooled over the debug record's eight tasks, their cases and generations 1-3 (unscored, under KAPPA_TAG)
MATCHED = _row("relax", "memory", kappa_key="matched", label="relax-matched/memory")
ROWS7 = ROWS + (MATCHED,)                                           # phase B's seven rows
ALL = ROWS7
_A = {x["label"]: x for x in ROWS7}
KAPPA_MATCHED = 1.4                      # P66k (23:31:59-23:35:13Z, probes/results/p66k_e2e007_kappa.json): the root 1.400
                                         # to four significant figures; its confirmation f / T = 0.99980 (6,712.5 / 6,713.9)
KAPPA_TAG = "mse-p66k"
KAPPA_G = 3                              # generations 1-3
KAPPA_TRIALS = (1.0, 1.4, 1.8)
KAPPA_EXTEND = 0.4                       # the grid's extension when the target is not bracketed
KAPPA_TOL = 0.002                        # the confirmation: f / T within 1 +- KAPPA_TOL
KAPPA_MAX_CONFIRM = 3
# P66h (the healing curve; engineering): the observer at every update from t_body - 1 to t_body + HEAL_SPAN, generation 1
HEAL_SPAN = 200

# the fresh-successor test: after generation g in FRESH_AT, a field-free newborn reads the outgoing record for one
# generation (the vote, no injury, no medium) under E2E007's names, and is scored; its final states are saved
FRESH_AT = (G_MAIN,)
FRESH = {"policy": "vote", "injured": False, "field": "none", "names": ("e2e007", "fresh")}
STAGE_FRESH_AT = {"debug": (G_DEBUG,)}

# the restored sources (AR006's raw final states: E2E003's and E2E006's cohort) and the stages
SOURCES = E3D.SOURCES
AR006_DEV = E3D.AR006_DEV
PROBE_BLOCKS = D6.PROBE_BLOCKS            # 900917, 900919 (two of P57's four blocks, as P63)
STAGES = {"probe": {"ar006/p57": PROBE_BLOCKS}, "probe_x": {"ar006/p57": PROBE_BLOCKS},
          "debug": dict(E3D.STAGES["debug"]),
          "preflight": {"ar006/preflight": (E3D.STAGES["preflight"]["ar006/preflight"][0],)},   # 900929
          "development": {"ar006/development": AR006_DEV}}
STAGE_TAG = {"probe": PROBE_TAG, "probe_x": PROBE_TAG, "debug": TAG, "preflight": TAG, "development": TAG}
# probe: P66 as run in phase A (the six rows); probe_x: P66x (the matched row alone, merged per task with P66); debug: the
# seven rows from Amendment 1 (root e2e007/debug_a1; phase A's debug run held the six)
STAGE_LINEAGES = {"probe": ROWS, "probe_x": (MATCHED,), "debug": ROWS7, "preflight": ROWS7, "development": ROWS7}
FUTURES = {"probe": 1, "probe_x": 1, "debug": 1, "preflight": 1, "development": 1}
STAGE_STOP_CAP = {"debug": G_DEBUG}
HALVES = {"probe": ((PROBE_BLOCKS[0],), (PROBE_BLOCKS[1],)), "development": (AR006_DEV[:8], AR006_DEV[8:])}
BODIES, UNITS = A.BODIES, A.UNITS
ITEM_SETS = E2D.ITEM_SETS                # native (li4 S4), particular (li4 F0: read first), permissive (dw)
K_RULE, STEP, STEP_NEAR0, AT_MOST_MAX, C_Q = E2D.K_RULE, E2D.STEP, E2D.STEP_NEAR0, E2D.AT_MOST_MAX, E2D.C_Q


def lineages(stage):
    return STAGE_LINEAGES[stage]


def stage_tasks(stage):
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "bridge_tag": BRIDGE_TAG, "clock": CLOCK, "t_gen": T_GEN,
            "horizons": HORIZONS, "g_main": G_MAIN, "g_debug": G_DEBUG, "policies": POLICIES, "injury": INJURY,
            "field": FIELD, "responses": RESPONSES, "sign": SIGN, "targets": TARGETS, "body_frac": BODY_FRAC,
            "t_body": t_body(), "obs": OBS, "obs_updates": obs_updates(), "rows": ROWS7, "fresh_at": FRESH_AT,
            "kappa_matched": KAPPA_MATCHED, "kappa_tag": KAPPA_TAG, "kappa_g": KAPPA_G, "kappa_trials": KAPPA_TRIALS,
            "kappa_extend": KAPPA_EXTEND, "kappa_tol": KAPPA_TOL, "kappa_max_confirm": KAPPA_MAX_CONFIRM,
            "heal_span": HEAL_SPAN,
            "fresh": FRESH, "stage_fresh_at": STAGE_FRESH_AT, "sources": SOURCES, "stages": STAGES,
            "stage_tag": STAGE_TAG, "stage_lineages": {k: [x["label"] for x in v] for k, v in STAGE_LINEAGES.items()},
            "futures": FUTURES, "stage_stop_cap": STAGE_STOP_CAP, "halves": HALVES, "bodies": BODIES, "units": UNITS,
            "item_sets": ITEM_SETS, "k_rule": K_RULE, "step": STEP, "step_near0": STEP_NEAR0,
            "at_most_max": AT_MOST_MAX, "c_q": C_Q, "size": SIZE, "side": SIDE, "ar001_digest": A.digest(),
            "ar006_digest": A6.digest(), "e2e002_digest": E2D.digest(), "e2e003_digest": E3D.digest(),
            "e2e006_digest": D6.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    lane = Path(lane)
    dirs = ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002", "be005",
            "be006", "gc001", "np001", "ar001", "ar002", "ar003", "ar004", "ar005", "ar006", "sr001", "e2e001", "e2e002",
            "e2e003", "msefield", "e2e006", "e2e007")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m e2e007.design  ->  e2e007/frozen/design.json (phase B, on the lead's word)
    import time
    if KAPPA_MATCHED is None:
        raise SystemExit("KAPPA_MATCHED is not set: P66k comes first")
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "e2e007" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
