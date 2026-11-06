"""BE008: what erodes the evidence when only the local corrector is slowed.

BE006 (REPORT_BE006.md, K4) found that slowing only the arbiter (clock A: the arbiter's bonds at eta_a = 3e-4, every other
bond at the lane's eta = 0.01 with bond noise p_b = 1e-3) blurs the deadline: the damaged patch's anchored cells, the
detector's only sensors, were already 15% repaired at 3.3 h and 27% at T* = 6.5 h, where the fully calibrated clock SL
(eta = 3e-4, p_b = 3e-5) kept them intact to T*. A and SL differ in eta, p_b and the commitment tau_c; AL against A showed
that tau_c does not move the sensors. BE008 crosses the other bonds' relearning rate eta with the bond noise p_b, the
arbiter at 3e-4 and the commitment at 15,000 updates throughout, on BE006's tissue (be006.sim.run, unchanged, with the
clocks passed as its per-arm params).

Clocks (each a signal arm 'dial-X', BE004's dial with no hold, and a no-signal arm 'never-X'):
  AL     eta 0.01, p_b 1e-3     BE006's AL, bit for bit (checks Q3)
  AL-m   eta 0.01, p_b 1e-4     the noise at a tenth of the lane's
  AL-n   eta 0.01, p_b 3e-5     the noise scaled as in SL (1e-3 x 3e-4 / 0.01), the relearning not
  SL-m   eta 3e-4, p_b 1e-4     the relearning slowed, the noise at a tenth of the lane's
  SL     eta 3e-4, p_b 3e-5     BE006's SL, bit for bit (checks Q3)
AL-m, AL-n, SL-m and SL cross eta {0.01, 3e-4} with p_b {1e-4, 3e-5}; AL, AL-m and AL-n step the noise at the lane's eta.
The fourth corner of the sketch, eta 3e-4 with p_b 1e-3 (SL-p), dissolved the sheet's record in the engineering smoke
(r_all 0.98 -> 0.56 by 2,000 updates), so its sensors were randomised rather than repaired; it was replaced by the
p_b 1e-4 pair (disclosed in REGISTRATION_BE008.md).

Runs (event, patch side 4, delay D; the signal on at D + 1 to D + 1,000):
  memory4@0        a 4 x 4 memory damage: every clock's dial and never arm, 6,000 updates (the sensors' course without a
                   signal, the prompt repair)
  memory4@D        every clock's dial at D = round(m T*(3e-4)), m = 0.5, 1, 2 (979, 1,959, 3,918 updates; 3.3, 6.5 and
                   13.1 h), each for D + 4,000 updates, so a late signal is read 4,000 updates after it starts, as the
                   prompt one is at 4,000 (equal elapsed time, BE006's lesson)
"""
from __future__ import annotations

import hashlib
import json

from be006 import design as B6
from dl001 import design as DL

TAG = "mse-be008"
PROBE_TAG = "mse-p36"
STUDY = "BE008"
PROBE_BLOCKS = (900580, 900584)
IDENTITIES = {"preflight": (900584, 900586), "development": (910440, 910456)}
DEBUG_BLOCKS = (900586, 900588)  # mse.assay reserves 900000-900999 for engineering; 900580-900587 scanned free (the lead)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK, NCASE = B6.SIDE, B6.SIGMA, B6.CHUNK, B6.NCASE
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA, RATE = B6.EPS, B6.KR, B6.SIGMA_R, B6.KC, B6.STRENGTH0, B6.ETA, B6.RATE
DENSITY, VMIN, PULL, GAIN, KAPPA, S_MIN = B6.DENSITY, B6.VMIN, B6.PULL, B6.GAIN, B6.KAPPA, B6.S_MIN
BODIES, PATTERNS, THETAS, UNITS = B6.BODIES, B6.PATTERNS, B6.THETAS, B6.UNITS
SIG, TAU_M, ETA_CAL, TAU_LONG, TRACE = B6.SIG, B6.TAU_M, B6.ETA_CAL, B6.TAU_LONG, B6.TRACE
P_SCALED = B6.CLOCKS["SL"]["rate"]                              # BE006's 1e-3 x 3e-4 / 0.01, the same float
P_MID = 1e-4
t_star, delay, hours, run_name, on_window = B6.t_star, B6.delay, B6.hours, B6.run_name, B6.on_window
unit_name, parse_unit = B6.unit_name, B6.parse_unit


def clock(eta, rate):
    return {"eta_a": ETA_CAL, "eta": eta, "rate": rate, "tau_c": TAU_LONG}


CLOCKS = {"AL": clock(ETA, RATE), "AL-m": clock(ETA, P_MID), "AL-n": clock(ETA, P_SCALED),
          "SL-m": clock(ETA_CAL, P_MID), "SL": clock(ETA_CAL, P_SCALED)}
assert CLOCKS["AL"] == B6.CLOCKS["AL"] and CLOCKS["SL"] == B6.CLOCKS["SL"]
SIGNAL_ARMS = {}
for _c, _p in CLOCKS.items():
    SIGNAL_ARMS[f"dial-{_c}"] = dict(_p, never=False)
    SIGNAL_ARMS[f"never-{_c}"] = dict(_p, never=True)
ARMS = tuple(SIGNAL_ARMS)
DIALS = tuple(f"dial-{c}" for c in CLOCKS)
MULTS = (0.5, 1, 2)
DELAYS = tuple(delay(ETA_CAL, m) for m in MULTS)
W0, AFTER = 6000, 4000
READS0 = (500, 1000, 2000, 3000, 4000, 6000)


def run_window(situation, size, delay_, arms=None):
    return W0 if delay_ == 0 else delay_ + AFTER


def run_reads(situation, size, delay_, arms=None):
    return READS0 if delay_ == 0 else (delay_ + 1000, delay_ + 2000, delay_ + AFTER)


RUNS = (("memory", 4, 0, ARMS), *(("memory", 4, d, DIALS) for d in DELAYS))
RUNNAMES = tuple(run_name(*x) for x in RUNS)


def where(c, m):
    """(run name, arm) of clock c's dial delayed by m T*(3e-4)."""
    return run_name("memory", 4, delay(ETA_CAL, m)), f"dial-{c}"


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


def tasks():
    """One task per (body, unit): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS,
            "base": "be006.sim.run unchanged (BE005's events, footprint, cable detector, commitment and local dial, LR004's "
                    "arbiter and its own relearning rate), the clocks passed as its per-arm params",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "rate": RATE, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "gain": GAIN, "kappa": KAPPA, "s_min": S_MIN, "sig": SIG, "tau_m": TAU_M, "eta_cal": ETA_CAL,
            "tau_long": TAU_LONG, "p_scaled": P_SCALED, "p_mid": P_MID, "clocks": CLOCKS, "signal_arms": SIGNAL_ARMS,
            "t_star": t_star(ETA_CAL), "mults": MULTS, "delays": DELAYS, "w0": W0, "after": AFTER, "reads0": READS0,
            "arms": ARMS, "runs": RUNS, "run_windows": {run_name(*x): run_window(*x) for x in RUNS},
            "run_reads": {run_name(*x): run_reads(*x) for x in RUNS},
            "on_windows": {run_name(*x): on_window(*x) for x in RUNS},
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004", "be005", "be006", "be008")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be008.design  ->  be008/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be008" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
