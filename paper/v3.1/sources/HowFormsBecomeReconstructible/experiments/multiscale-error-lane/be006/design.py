"""BE006: the deadline and the commitment at calibrated clocks.

BE005's tissue (BE004's events, footprint, cable detector, commitment and local dial, LR004's arbiter, and BE005's
own rate for the arbiter's bonds; be005.sim, be004.sim, be002.sim and be001.sim unchanged and imported), at read gain
0.2 on BE001's twelve unit-body pairs, with three of the lane's clocks set per arm as CALIBRATION.md ("The clocks")
places them at tau_m = 300 updates = 1 h:

  eta_a  the arbiter's own relearning rate on the bonds that touch an arbiter cell (an anchored cell whose body and
         record disagree and which is not committed; BE005's): 0.01, so T* = ln(1.8) / -ln(1 - eta_a) = 58.5 updates
         (about 12 minutes), or 3e-4, so T* = 1,959 updates (about 6.5 h: the planarian evidence clock, half effect at
         3-6 h, closed by about 12 h)
  eta    every other bond's Hebbian rate, with the bond-noise rate scaled with it (p_b = 1e-3 x eta / 0.01, so that the
         record keeps the noise-to-repair ratio it was qualified at): 0.01 (the lane's), or 3e-4, the whole maintenance
         clock at the calibrated pace, so that carrying out a committed decision (its bonds relearned to the committed
         signs) also takes about T*(3e-4)
  tau_c  the commitment's decay time (BE001's TAU): 300 updates (1 h), or 15,000 (50 h: a planarian decision must
         hold until it is carried out, at least 48-72 h)

Clocks (each run as a signal arm 'dial-X', BE004's dial with no hold, and a no-signal arm 'never-X'):
  F    eta_a 0.01, eta 0.01, tau_c 300       BE005's dial-e0.01 and never-e0.01, bit for bit (checks Q3)
  A    eta_a 3e-4, eta 0.01, tau_c 300       the arbiter at the calibrated rate (BE005's convention)
  AL   eta_a 3e-4, eta 0.01, tau_c 15,000    the same, with a commitment that outlasts the execution
  S    eta_a 3e-4, eta 3e-4, tau_c 300       the whole maintenance clock calibrated, the commitment not
  SL   eta_a 3e-4, eta 3e-4, tau_c 15,000    the whole clock and the commitment calibrated

Runs (event, patch side 4, delay D; the arms each runs; the signal on at D + 1 to D + 1,000):
  memory4@0        a 4 x 4 memory damage: every clock's dial and never arm (window 12,000)
  memory4@D        F's dial at D = round(m T*(0.01)), m = 0.5, 1, 2, 4 (window 4,000, BE005's); for eta_a = 3e-4,
                   D = round(m T*(3e-4)): A's and SL's dials at m = 0.5, 1, 2, 4 and AL's at m = 1, 2 (window
                   8,000; 12,000 at m = 4)
  change4@0        a legitimate change of a 4 x 4 patch, the prompt signal: A, AL, S and SL, dial and never (window 8,000)
  cue4@0           scattered corruption of a quarter of the anchors, a prompt sham: the same arms (window 8,000)
F is scored at t = 4,000 (BE005's read); the calibrated clocks at t = 8,000, and at m = 4 at t = 12,000 against the
prompt signal read at 12,000. Every run reads the patch's record every 100 updates (the trace).
"""
from __future__ import annotations

import hashlib
import json
import math

from be001 import design as B1
from be005 import design as B5
from dl001 import design as DL

TAG = "mse-be006"
PROBE_TAG = "mse-p33"
STUDY = "BE006"
PROBE_BLOCKS = (900540, 900544)
IDENTITIES = {"preflight": (900544, 900546), "development": (910360, 910376)}
DEBUG_BLOCKS = (900546, 900548)  # the engine reserves 900000-900999 for engineering; 900536-900547 scanned free (the lead)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B5.SIDE, B5.SIGMA, B5.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B5.EPS, B5.KR, B5.SIGMA_R, B5.KC, B5.STRENGTH0, B5.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B5.KILL_SD, B5.DENSITY, B5.VMIN, B5.PULL, B5.RATE
BODIES, PATTERNS, THETAS = B5.BODIES, B5.PATTERNS, B5.THETAS
MESSAGES, PARENTS, NCASE = B5.MESSAGES, B5.PARENTS, B5.NCASE
GAIN, KAPPA, G_LEAK, TAU, S_MIN = B5.GAIN, B5.KAPPA, B5.G_LEAK, B5.TAU, B5.S_MIN
SIG = B5.SIG                                                    # BE002's footprint, duration, lengths and threshold

TAU_M = 300                                                     # updates per hour at the calibration's anchor
ETA_CAL = 3e-4                                                  # the calibrated arbiter (CALIBRATION.md: 1.6-6.5e-4)
TAU_LONG = 15000                                                # a commitment of 50 h


def t_star(eta, s0=STRENGTH0):
    """Updates for a bond taught at strength s0 to cross zero under relearning toward the opposite sign at rate eta."""
    return math.log(1.0 + s0) / -math.log(1.0 - eta)


def delay(eta, m):
    return int(round(m * t_star(eta)))


def fmt(x):
    return f"{x:g}"


def clock(eta_a, eta, tau_c):
    """A clock's rates; the bond-noise rate keeps the lane's p_b exactly wherever eta is the lane's."""
    return {"eta_a": eta_a, "eta": eta, "rate": RATE if eta == ETA else RATE * eta / ETA, "tau_c": tau_c}


CLOCKS = {"F": clock(ETA, ETA, TAU), "A": clock(ETA_CAL, ETA, TAU), "AL": clock(ETA_CAL, ETA, TAU_LONG),
          "S": clock(ETA_CAL, ETA_CAL, TAU), "SL": clock(ETA_CAL, ETA_CAL, TAU_LONG)}
SIGNAL_ARMS = {}
for _c, _p in CLOCKS.items():
    SIGNAL_ARMS[f"dial-{_c}"] = dict(_p, never=False)
    SIGNAL_ARMS[f"never-{_c}"] = dict(_p, never=True)
ARMS = tuple(SIGNAL_ARMS)
EQUIV5 = {"dial-F": "dial-e0.01", "never-F": "never-e0.01"}     # BE005's names for the same arms

MULTS = (0.5, 1, 2, 4)
LATE = {"F": MULTS, "A": MULTS, "AL": (1, 2), "SL": MULTS}       # the delayed dials
CAL = ("A", "AL", "S", "SL")
WINDOW_F, WINDOW_S, WINDOW_L = 4000, 8000, 12000
READS = (500, 1000, 2000, 3000, 4000, 6000, 8000, 10000, 12000)
TRACE = 100
T_SCORE = {"F": 4000, "slow": 8000, "m4": 12000}               # the scoring reads


def eta_of(c):
    return CLOCKS[c]["eta_a"]


def run_window(situation, size, delay_, arms):
    if situation != "memory" or delay_ == 0:
        return WINDOW_L if situation == "memory" else WINDOW_S
    if all(a.endswith("-F") for a in arms):
        return WINDOW_F
    return WINDOW_L if delay_ >= delay(ETA_CAL, 4) else WINDOW_S


def run_reads(situation, size, delay_, arms):
    w = run_window(situation, size, delay_, arms)
    return tuple(t for t in READS if t <= w)


DELAYED = {}                                                    # D -> the delayed dial arms
for _c, _ms in LATE.items():
    for _m in _ms:
        DELAYED.setdefault(delay(eta_of(_c), _m), []).append(f"dial-{_c}")
RUNS = (("memory", 4, 0, ARMS),
        *(("memory", 4, d, tuple(DELAYED[d])) for d in sorted(DELAYED)),
        ("change", 4, 0, tuple(f"{k}-{c}" for c in CAL for k in ("dial", "never"))),
        ("cue", 4, 0, tuple(f"{k}-{c}" for c in CAL for k in ("dial", "never"))))


def run_name(situation, size, delay_, arms=None):
    return f"{situation}{size}@{delay_}"


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def on_window(situation, size, delay_, arms=None):
    """(first, last) update with the signal on."""
    return delay_ + 1, delay_ + SIG["duration"]


def where(c, m):
    """(run name, arm) of clock c's dial delayed by m T*(eta_a)."""
    return run_name("memory", 4, delay(eta_of(c), m)), f"dial-{c}"


def hours(updates):
    return updates / TAU_M


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


unit_name, parse_unit, UNITS = B1.unit_name, B1.parse_unit, B1.UNITS


def tasks():
    """One task per (body, unit): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "lr002.sim.prepare = dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "be005": "events, footprint, conductances, sparse LU, the local dial, LR004's arbiter and the arbiter's own "
                     "relearning rate of be005.sim / be004.sim / be002.sim / be001.sim, unchanged; per-arm base relearning "
                     "rate, bond-noise rate and commitment decay are new",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN, "sig": SIG,
            "tau_m": TAU_M, "eta_cal": ETA_CAL, "tau_long": TAU_LONG, "clocks": CLOCKS, "signal_arms": SIGNAL_ARMS,
            "t_star": {fmt(e): t_star(e) for e in (ETA, ETA_CAL)}, "mults": MULTS, "late": LATE,
            "delays": {c: [delay(eta_of(c), m) for m in ms] for c, ms in LATE.items()}, "arms": ARMS, "runs": RUNS,
            "run_windows": {run_name(*x): run_window(*x) for x in RUNS},
            "run_reads": {run_name(*x): run_reads(*x) for x in RUNS},
            "on_windows": {run_name(*x): on_window(*x) for x in RUNS}, "t_score": T_SCORE,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004", "be005", "be006")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be006.design  ->  be006/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be006" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
