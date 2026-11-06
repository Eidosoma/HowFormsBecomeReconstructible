"""BE007: does carrying out the decision close a late signal's window?

BE006's fully calibrated tissue (clock SL: the arbiter and every other bond relearning at 3e-4 per update, the bond noise
scaled with it, a commitment of 15,000 updates; be006.sim's arithmetic, unchanged, re-implemented in be007.sim with one
addition and checked bit for bit against be006.sim.run), at read gain 0.2 on BE001's twelve unit-body pairs. BE006 found
that a late signal there loses nothing within T* (1,959 updates, 6.5 h at 300 updates an hour) and only a fifth to a
quarter of its gain at 13-26 h, where planarian blockade has lost most of its effect after 12 h and all of it later.

The addition, execution: at update tau_x after the event the wounded region (the signal's footprint: the patch dilated by
2) carries out the tissue's default outcome, set per arm:
  commit   every footprint cell not already committed commits to its current record sign (BE001's decision state set
           to 1, the trusted sign to the record's), as if triggered toward keeping its record: it pulls its record to
           that sign and relearns its bonds toward it, a later trigger refreshes it but cannot flip it (BE001's rule),
           and it lapses after tau_c (15,000) unless refreshed
  lock     footprint cells can no longer trigger from tau_x on (competence ends); nothing else changes
  fade     the positional cue at the footprint's anchored cells is gone from tau_x on (the wound's transient
           positional information ends): no current to the detector, no cue to the arbiter
With no execution an arm is BE006's dial-SL or never-SL bit for bit (checks Q3).

Clocks (each run as a signal arm 'dial-X', BE004's dial with no hold, and a no-signal arm 'never-X'; all at SL's rates):
  SL    no execution (BE006's dial-SL and never-SL, the bridge)
  C6    commit at tau_x = 1,800 updates (6 h: before the evidence clock T* = 1,959, 6.5 h)
  C12   commit at 3,600 (12 h: when planarian blockade has lost much of its effect)
  C24   commit at 7,200 (24 h)
  F12   fade at 3,600 (12 h: the planarian wound-induced genes are off by about 12 h), the comparison form
Runs (event, patch side 4, delay D; the signal on at D + 1 to D + 1,000):
  memory4@0        a 4 x 4 memory damage and the prompt signal: every clock's dial and never arm (window 12,000)
  memory4@D        the same damage with the signal D = round(m T*) late, m = 0.5, 1, 2, 4 (D = 979, 1,959, 3,918,
                   7,836: 3.3, 6.5, 13.1, 26.1 h): every clock's dial (window D + 4,000)
  change4@3918     a legitimate change of a 4 x 4 patch with the signal 2 T* (13.1 h) late: dial and never arms of every
                   clock (window 7,918)
  cue4@3918        scattered corruption of a quarter of the anchors with a sham signal 13.1 h late: the same arms
Every late signal is read at D + 4,000 (equal elapsed time with the prompt signal's read at 4,000), where memory4@0's
never arms are read too (the same time: no signal); every run reads the patch's record every 100 updates (the trace).
"""
from __future__ import annotations

import hashlib
import json

from be001 import design as B1
from be006 import design as B6
from dl001 import design as DL

TAG = "mse-be007"
PROBE_TAG = "mse-p35"
STUDY = "BE007"
PROBE_BLOCKS = (900570, 900574)
IDENTITIES = {"preflight": (900574, 900576), "development": (910420, 910436)}
DEBUG_BLOCKS = (900576, 900578)  # the engine reserves 900000-900999 for engineering; 900570-900577 checked free (the lead)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B6.SIDE, B6.SIGMA, B6.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B6.EPS, B6.KR, B6.SIGMA_R, B6.KC, B6.STRENGTH0, B6.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B6.KILL_SD, B6.DENSITY, B6.VMIN, B6.PULL, B6.RATE
BODIES, PATTERNS, THETAS = B6.BODIES, B6.PATTERNS, B6.THETAS
MESSAGES, PARENTS, NCASE = B6.MESSAGES, B6.PARENTS, B6.NCASE
GAIN, KAPPA, G_LEAK, TAU, S_MIN = B6.GAIN, B6.KAPPA, B6.G_LEAK, B6.TAU, B6.S_MIN
SIG = B6.SIG
TAU_M, ETA_CAL, TAU_LONG = B6.TAU_M, B6.ETA_CAL, B6.TAU_LONG
SL = B6.CLOCKS["SL"]                                            # eta_a = eta = 3e-4, rate scaled, tau_c = 15,000
T_STAR = B6.t_star(ETA_CAL)                                     # 1,958.99 updates, 6.53 h


def hours(updates):
    return updates / TAU_M


def clock(form=None, tau_x=None):
    return dict(SL, form=form, tau_x=tau_x)


CLOCKS = {"SL": clock(), "C6": clock("commit", 6 * TAU_M), "C12": clock("commit", 12 * TAU_M),
          "C24": clock("commit", 24 * TAU_M), "F12": clock("fade", 12 * TAU_M)}
SIGNAL_ARMS = {}
for _c, _p in CLOCKS.items():
    SIGNAL_ARMS[f"dial-{_c}"] = dict(_p, never=False)
    SIGNAL_ARMS[f"never-{_c}"] = dict(_p, never=True)
ARMS = tuple(SIGNAL_ARMS)
DIALS = tuple(f"dial-{c}" for c in CLOCKS)

MULTS = (0.5, 1, 2, 4)
DELAYS = tuple(int(round(m * T_STAR)) for m in MULTS)          # 979, 1,959, 3,918, 7,836
LATE_CN = DELAYS[2]                                             # the late change and sham: 2 T*, 13.1 h
AFTER = 4000                                                    # every late signal read at D + 4,000; the prompt's at 4,000
WINDOW_0 = 12000
READS = (500, 1000, 2000, 3000, 4000, 6000, 8000, 10000, 12000)
TRACE = 100


def run_name(situation, size, delay_, arms=None):
    return f"{situation}{size}@{delay_}"


def run_window(situation, size, delay_, arms=None):
    return WINDOW_0 if (situation == "memory" and delay_ == 0) else delay_ + AFTER


def run_reads(situation, size, delay_, arms=None):
    w = run_window(situation, size, delay_, arms)
    extra = {d + AFTER for d in DELAYS} if (situation == "memory" and delay_ == 0) else {delay_ + AFTER}
    return tuple(sorted({t for t in READS if t <= w} | extra))


def on_window(situation, size, delay_, arms=None):
    """(first, last) update with the signal on."""
    return delay_ + 1, delay_ + SIG["duration"]


RUNS = (("memory", 4, 0, ARMS),
        *(("memory", 4, d, DIALS) for d in DELAYS),
        ("change", 4, LATE_CN, ARMS),
        ("cue", 4, LATE_CN, ARMS))
RUNNAMES = tuple(run_name(*x) for x in RUNS)


def where(c, m):
    """(run name, arm) of clock c's dial delayed by m T*."""
    return run_name("memory", 4, int(round(m * T_STAR))), f"dial-{c}"


def executed_by(c, d):
    """True if clock c has executed before a signal that starts at update d + 1."""
    tx = CLOCKS[c]["tau_x"]
    return tx is not None and tx <= d


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
            "be006": "be006.sim's arithmetic for clock SL, re-implemented in be007.sim with execution added",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN, "sig": SIG,
            "tau_m": TAU_M, "eta_cal": ETA_CAL, "tau_long": TAU_LONG, "t_star": T_STAR, "clocks": CLOCKS,
            "signal_arms": SIGNAL_ARMS, "arms": ARMS, "mults": MULTS, "delays": DELAYS, "late_cn": LATE_CN,
            "after": AFTER, "window_0": WINDOW_0, "runs": RUNS,
            "run_windows": {run_name(*x): run_window(*x) for x in RUNS},
            "run_reads": {run_name(*x): run_reads(*x) for x in RUNS},
            "on_windows": {run_name(*x): on_window(*x) for x in RUNS},
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004", "be005", "be006", "be007")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be007.design  ->  be007/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be007" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
