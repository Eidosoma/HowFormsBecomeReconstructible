"""BE010: a decision that can be reset. What reopens an executed decision?
BE007's tissue and clock C12, imported unchanged (BE006's fully calibrated clock SL with the commit form at tau_x = 3,600
updates, 12 h: every footprint cell not already committed commits to its record's sign, and a later trigger refreshes it
but cannot flip it), at read gain 0.2 on BE001's twelve unit-body pairs. BE007 found that once C12 has executed, no late
signal changes the 4 x 4 memory-damaged patch. In planaria a new wound with an opposite signal can reset a decision
(Durant et al. 2017: SCH-28080 at a new cut reset 34 % of 102 two-headed worms); a new cut alone does not.
The addition, a second event at update T_W = 7,836 (4 T*, 26.1 h, BE007's longest delay), applied at the start of update
T_W + 1, per arm:
  W   a new wound at the patch with instant regrowth: the patch's cells are newborn (body and moving average KILL_SD x
      N(0, 1), the lane's newborn values, stream 'newborn'; record 0; uncommitted), every contact touching the patch
      untrained (sign 0, strength 0: SC002's rule for newborn cells); the anchors stay (the cue is positional, SC002's)
  K   the same wound with the rim's contacts kept: only contacts with both ends in the patch untrained (LR005's 'shared'
      rule); where the executed state lives (the rim's junctions or the cells) is the contrast with W
  R   a reset drug: every commitment in the tissue cleared (decision state 0, trusted sign 0; commitments exist only where
      the tissue executed or triggered); cells, records and bonds untouched
  N   no second event: BE007's C12, bit for bit (the bridge, checks Q3)
After a reset the tissue executes again (re-execution: C12's commit at T_W + 3,600, 12 h after the reset); W0 and R0 are W
and R with no re-execution (the window-closing control).
Runs (event, patch side 4, d = the signal's delay after T_W; the signal, BE004's dial, on at T_W + d + 1 to T_W + d +
1,000):
  memory4@w+d    the 4 x 4 memory damage, d = 0, 979, 1,959 (0, 0.5, 1 T*: before re-execution): dial-N, -W, -K, -R
  memory4@w+3918 d = 3,918 (2 T*, 13.1 h after the reset, after re-execution): the same dials, dial-W0 and dial-R0, and
                 every reset's never arm (no signal; read at each T_W + d + 4,000: equal elapsed time with each dial)
  none4@w+0      no damage: every reset's never arm, the reset's own cost where nothing was wrong (window T_W + 4,000)
  cue4@w+0       BE007's sham: a quarter of the anchors corrupted at 0 (scattered), the reset at T_W and a sham signal at
                 once after it: dial and never arms of N, W and R (K dropped for cost), read at T_W + 4,000
Every dial is read at T_W + d + 4,000 (equal elapsed time with its never arm); every run reads the patch's record every
100 updates (the trace).
"""
from __future__ import annotations

import hashlib
import json

from be001 import design as B1
from be007 import design as B7
from dl001 import design as DL

TAG = "mse-be010"
PROBE_TAG = "mse-p38"
STUDY = "BE010"
PROBE_BLOCKS = (900588, 900592)
IDENTITIES = {"preflight": (900592, 900594), "development": (910480, 910496)}
DEBUG_BLOCKS = (900594, 900596)  # the engine reserves 900000-900999 for engineering; 900588-900595 checked free (the lead)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B7.SIDE, B7.SIGMA, B7.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B7.EPS, B7.KR, B7.SIGMA_R, B7.KC, B7.STRENGTH0, B7.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B7.KILL_SD, B7.DENSITY, B7.VMIN, B7.PULL, B7.RATE
BODIES, PATTERNS, THETAS = B7.BODIES, B7.PATTERNS, B7.THETAS
MESSAGES, PARENTS, NCASE = B7.MESSAGES, B7.PARENTS, B7.NCASE
GAIN, KAPPA, G_LEAK, TAU, S_MIN = B7.GAIN, B7.KAPPA, B7.G_LEAK, B7.TAU, B7.S_MIN
SIG = B7.SIG
TAU_M, ETA_CAL, TAU_LONG = B7.TAU_M, B7.ETA_CAL, B7.TAU_LONG
T_STAR = B7.T_STAR                                              # 1,958.99 updates, 6.53 h
C12 = B7.CLOCKS["C12"]                                          # SL with commit at 3,600 (12 h)
T_W = B7.DELAYS[-1]                                             # 7,836 = 4 T* (26.1 h): the second event
RE_X = T_W + C12["tau_x"]                                       # 11,436: re-execution, 12 h after the reset


def hours(updates):
    return updates / TAU_M


RESETS = {"N": dict(reset=None, rexec=False),                   # BE007's C12 (the bridge)
          "W": dict(reset="wound", rexec=True),                 # newborn patch, every touching contact untrained
          "K": dict(reset="wound-kept", rexec=True),            # newborn patch, the rim's contacts kept
          "R": dict(reset="decommit", rexec=True),              # every commitment cleared
          "W0": dict(reset="wound", rexec=False),
          "R0": dict(reset="decommit", rexec=False)}
SIGNAL_ARMS = {}
for _x, _p in RESETS.items():
    SIGNAL_ARMS[f"dial-{_x}"] = dict(C12, never=False, **_p)
    SIGNAL_ARMS[f"never-{_x}"] = dict(C12, never=True, **_p)
ARMS = tuple(SIGNAL_ARMS)
MAIN = ("N", "W", "K", "R")
DIALS = tuple(f"dial-{x}" for x in MAIN)
NEVERS = tuple(f"never-{x}" for x in RESETS)
MULTS = (0, 0.5, 1, 2)
AFTER_W = tuple(int(round(m * T_STAR)) for m in MULTS)         # 0, 979, 1,959, 3,918 after T_W
AFTER = 4000                                                    # every dial read at T_W + d + 4,000, as BE007's
READS = (500, 1000, 2000, 3000, 3600, 4000, 6000, 7836, 7837, 8336, 8836, 9836, 10836, 11436, 11836, 13836)
TRACE = 100


def run_name(situation, size, d, arms=None):
    return f"{situation}{size}@w+{d}"


def run_window(situation, size, d, arms=None):
    return T_W + d + AFTER


def run_reads(situation, size, d, arms=None):
    w = run_window(situation, size, d, arms)
    nev = arms is not None and any(SIGNAL_ARMS[a]["never"] for a in arms)
    extra = {T_W + x + AFTER for x in AFTER_W if T_W + x + AFTER <= w} if nev else {T_W + d + AFTER}
    return tuple(sorted({t for t in READS if t <= w} | extra))


def on_window(situation, size, d, arms=None):
    """(first, last) update with the signal on (never arms ignore it)."""
    return T_W + d + 1, T_W + d + SIG["duration"]


RUNS = (*(("memory", 4, d, DIALS) for d in AFTER_W[:3]),
        ("memory", 4, AFTER_W[3], DIALS + ("dial-W0", "dial-R0") + NEVERS),
        ("none", 4, 0, tuple(f"never-{x}" for x in MAIN)),
        ("cue", 4, 0, ("dial-N", "never-N", "dial-W", "never-W", "dial-R", "never-R")))
RUNNAMES = tuple(run_name(*x) for x in RUNS)


def where(x, m):
    """(run name, arm) of reset x's dial m T* after T_W."""
    return run_name("memory", 4, int(round(m * T_STAR))), f"dial-{x}"


NEVER_RUN = run_name(*RUNS[3])                                  # memory4@w+3918: every never arm
SHAM_RUN = run_name(*RUNS[4])                                   # none4@w+0
CUE_RUN = run_name(*RUNS[5])                                    # cue4@w+0: the sham signal after the reset


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


unit_name, parse_unit, UNITS = B1.unit_name, B1.parse_unit, B1.UNITS


def tasks():
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "be007": "be007.sim's arithmetic for clock C12, re-implemented in be010.sim with the second event added",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN, "sig": SIG,
            "tau_m": TAU_M, "eta_cal": ETA_CAL, "tau_long": TAU_LONG, "t_star": T_STAR, "c12": C12, "t_w": T_W,
            "re_x": RE_X, "resets": RESETS, "signal_arms": SIGNAL_ARMS, "arms": ARMS, "mults": MULTS,
            "after_w": AFTER_W, "after": AFTER, "runs": RUNS,
            "run_windows": {run_name(*x): run_window(*x) for x in RUNS},
            "run_reads": {run_name(*x): run_reads(*x) for x in RUNS},
            "on_windows": {run_name(*x): on_window(*x) for x in RUNS},
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004", "be005", "be006", "be007", "cellpop", "be010")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be010.design  ->  be010/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be010" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
