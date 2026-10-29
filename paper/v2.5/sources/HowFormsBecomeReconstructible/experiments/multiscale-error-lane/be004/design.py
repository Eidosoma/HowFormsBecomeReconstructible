"""BE004: protecting the evidence, and how precise a signal must be.

BE002's tissue, events, cable detector, commitment and local dial, unchanged and imported (be002.sim, be001.sim,
lr005.sim), at read gain 0.2 on BE001's twelve unit-body pairs. Two questions:

Panel E, the evidence. BE002's late signal repaired a 4 x 4 memory damage less, because while it waited LR004's arbiter
repaired the patch's anchored cells (the cue where body and record disagree), and those cells are the detector's only
sensors (THEORY 8.8). Here the signal comes after a delay D in {0, 50, 100, 250, 500, 1,000} (on at D + 1 to D + 1,000;
50 and 100 added after P28's first pass found the loss already full at 250), and one
arm adds a hold: an injury known at once stops the arbiter taking the cue inside the footprint until the signal comes
(where body and record disagree at an anchored cell there, the record's own sign is trusted instead of the cue; nothing
else changes). With D = 0 there is nothing to hold, and dial-hold is dial bit for bit (checks Q5).

Panel P, precision. The prompt signal over a legitimate 4 x 4 change (adoption) and over scattered cue corruption (a
sham: the cost), with the footprint, the closure or the signal's reliability varied, one arm each:
  offset       the footprint (the patch dilated by 2) shifted by s = 2, 4 or 6 sites along the rows (columns + s)
  size         the patch dilated by d = 0, 4 or 8 instead of 2
  closure      junctions touching the footprint at lam_sig = 1.5 or 2 instead of 1
  flicker      on each update of the window with probability p = 0.5 or 0.25 (one uniform per case and update, shared
               by the flicker arms, so the p = 0.25 updates are a subset of the p = 0.5 ones)
  duration     on for its first 1, 10 or 100 updates only, instead of 1,000 (added after P28's first pass found a
               flickering signal equal to a steady one)
Arms (every signal arm is BE002's dial-local with one property changed; without the signal every one is bio-3 bit for bit):
  cue, bio-1, bio-3   LR004's arbiter; BE001's cable detectors at coupling 1 and 3 (references)
  dial                BE002's dial-local: lam 3 at rest, junctions touching the footprint closed to 1 while on
  dial-hold           dial with the hold
  dial-s2/s4/s6       offset footprints
  dial-d0/d4/d8       footprints of other sizes
  dial-w1.5/w2        weaker closure
  dial-f0.5/f0.25     flickering signal
  dial-t1/t10/t100    a brief signal
Runs (event, patch side, delay D; the arms each runs):
  memory4@0      4 x 4 memory damage, signal at 1-1,000: cue, bio-1, bio-3, dial
  memory4@D      D = 50, 100, 250, 500, 1,000: dial, dial-hold (the reference arms never read the signal: memory4@0's)
  cue4@1000      scattered cue damage (the patch drawn at side 4 sets the footprint), a late sham at 1,001-2,000:
                 bio-3, dial, dial-hold (does the hold change a sham's cost?)
  change4@0      a legitimate change of a 4 x 4 patch, signal at 1-1,000: cue, bio-1, bio-3 and every dial but the hold
  cue4@0         scattered cue damage, a prompt sham: cue, bio-1, bio-3, dial, the size, closure, flicker and duration arms
                 (an offset footprint has the size of the dial's, so its expected cost is the dial's)
"""
from __future__ import annotations

import hashlib
import json

from be001 import design as B1
from be002 import design as B2
from dl001 import design as DL

TAG = "mse-be004"
PROBE_TAG = "mse-p28"
STUDY = "BE004"
PROBE_BLOCKS = (900680, 900684)
IDENTITIES = {"preflight": (900684, 900686), "development": (910240, 910256)}
DEBUG_BLOCKS = (900686, 900688)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B2.SIDE, B2.SIGMA, B2.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B2.EPS, B2.KR, B2.SIGMA_R, B2.KC, B2.STRENGTH0, B2.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B2.KILL_SD, B2.DENSITY, B2.VMIN, B2.PULL, B2.RATE
BODIES, PATTERNS, THETAS = B2.BODIES, B2.PATTERNS, B2.THETAS
MESSAGES, PARENTS, NCASE = B2.MESSAGES, B2.PARENTS, B2.NCASE
GAIN, KAPPA, G_LEAK, TAU, S_MIN = B2.GAIN, B2.KAPPA, B2.G_LEAK, B2.TAU, B2.S_MIN

SIG = {"d": 2, "duration": 1000, "lam_rest": 3.0, "lam_sig": 1.0, "theta": 0.1}     # BE002's, unchanged
REF = ("bio-1", "bio-3")                                                              # BE001's, unchanged
BASE = {"shift": 0, "d": 2, "lam_sig": 1.0, "p_on": 1.0, "dur": 1000, "hold": False}  # BE002's dial-local
SIGNAL_ARMS = {"dial": dict(BASE),
               "dial-hold": dict(BASE, hold=True),
               "dial-s2": dict(BASE, shift=2), "dial-s4": dict(BASE, shift=4), "dial-s6": dict(BASE, shift=6),
               "dial-d0": dict(BASE, d=0), "dial-d4": dict(BASE, d=4), "dial-d8": dict(BASE, d=8),
               "dial-w1.5": dict(BASE, lam_sig=1.5), "dial-w2": dict(BASE, lam_sig=2.0),
               "dial-f0.5": dict(BASE, p_on=0.5), "dial-f0.25": dict(BASE, p_on=0.25),
               "dial-t1": dict(BASE, dur=1), "dial-t10": dict(BASE, dur=10), "dial-t100": dict(BASE, dur=100)}
ARMS = ("cue", *REF, *SIGNAL_ARMS)
ALIAS = {a: "bio-3" for a in SIGNAL_ARMS}                                             # without the signal
DELAYS = (0, 50, 100, 250, 500, 1000)
PRECISION = tuple(a for a in SIGNAL_ARMS if a != "dial-hold")
SHAM = ("cue", *REF, "dial", "dial-d0", "dial-d4", "dial-d8", "dial-w1.5", "dial-w2", "dial-f0.5", "dial-f0.25",
        "dial-t1", "dial-t10", "dial-t100")
RUNS = (("memory", 4, 0, ("cue", *REF, "dial")),
        *(("memory", 4, d, ("dial", "dial-hold")) for d in DELAYS[1:]),
        ("cue", 4, 1000, ("bio-3", "dial", "dial-hold")),
        ("change", 4, 0, ("cue", *REF, *PRECISION)),
        ("cue", 4, 0, SHAM))
WINDOW, TRACE = 4000, 100
READS = (50, 100, 250, 500, 1000, 1050, 1100, 1250, 1500, 2000, 4000)    # every delay's onset and end of signal,
                                                                            # and BE002's reads
FOOTPRINTS = (0, 2, 4, 8)                                 # the nested regions read in every run (the patch dilated by d)


def run_name(situation, size, delay, arms=None):
    return f"{situation}{size}@{delay}"


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def run_arms(situation, size, delay, arms):
    return tuple(arms)


def on_window(situation, size, delay, arms=None):
    """(first, last) update with the signal on."""
    return delay + 1, delay + SIG["duration"]


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
            "be002": "events, cable kernel, footprint, conductances, sparse LU, bioelectric targets, commitment and the "
                     "local dial of be002.sim / be001.sim, unchanged; lr005's cue arm",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN,
            "ref_bio": {a: B1.BIO[a] for a in REF}, "sig": SIG, "base": BASE, "signal_arms": SIGNAL_ARMS,
            "alias": ALIAS, "delays": DELAYS, "arms": ARMS, "runs": RUNS,
            "on_windows": {run_name(*x): on_window(*x) for x in RUNS},
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "window": WINDOW, "reads": READS, "trace": TRACE, "footprints": FOOTPRINTS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be004.design  ->  be004/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be004" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
