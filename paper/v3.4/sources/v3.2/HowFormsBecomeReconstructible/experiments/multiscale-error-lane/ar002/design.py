"""AR002: a signal the tissue makes (REPORT_AR001C.md, Next 1; the lane's other main line).

AR001 (confirmed by AR001C) found that a frozen controller, BE006's dial-SL, beats the best fixed policy (the vote) when a
regime signal of declared reliability (a hit rate h, a false-alarm rate f) tells it when to re-specify the patch to its
cue. AR002 asks whether the tissue can make that signal itself: a detector inside the tissue turns the controller on,
reading only what the tissue holds (the body, the record, the cue anchors and their recent history), never the
situation or the event time. Its rates per situation, its onset and its footprint become measured properties.

Everything but the signal's source is AR001's, imported unchanged (ar001.design, ar001.sim, and through them be006,
be005, be002, be001 and lr005): BE006's tissue at clock SL (T* = 1,959 updates), one event at t = 0 on a 4 x 4 patch,
8,000 updates, scored at t = 8,000; the eight unit-body pairs (S4 and F0 at theta x 0 and x 1, under dw and li4); the
seven situations and eight scorings (change scored as a legitimate change, change/new, and as coherent corruption,
change/old); equal weights; BEST = the vote, named from AR001's probe and frozen there.

The arms (paired: every branch reads the case's body, record and bond-noise streams):
  vote    BEST, AR001's (ar001.sim.run)
  rest    BE001's detector at coupling length 3 with the calibrated commitment: the controller with no signal (ar001)
  dial    the controller with AR001's declared signal: on at updates 1-1,000 over the patch dilated by 2 (ar001)
  det     the controller with the tissue's own signal (run_det): the primary detector below opens the dial's footprint
          (its zone dilated by 2, as AR001's patch) for 1,000 updates from its onset, once per case
  det-v   the same with the variant detector
  det-ms  reported only (the lead's ruling 1): det's cue channel at every box from 4 to 12, not tuned, not registered,
          not in AR002C; it measures det's size-specificity
dial and rest give the declared signal's exact expectation at the detector's own measured firing (U_pred).
Side arms: GC001's quenched misread of the cue (sigma 1) in none, memory and change, for the arms that read the cue
(rest, dial, det, det-v); the vote never reads the cue, so its outcome is the main grid's. The size arm (the lead's
ruling 2): memory and correlated damage on a 2 x 2 and an 8 x 8 patch at sigma 0, with vote, rest, dial, det and det-ms
(the patch's corner is the 4 x 4 patch's, so the three patches are nested).

The detectors (sim.detect; each sees this update's body, record and anchors only, as the controller's targets do):
  the cue channel   a window of box x box cells whose live anchors (anchor present, record confident) disagree with
                    the record in at least n cells and in at least a fraction q of them, with at most ring_max
                    disagreeing live anchors in the surround of width ring (a coherent island of disagreement)
  the body channel  a window whose confident body and record disagree in at least n cells and a fraction q of the cells
                    where both are confident (the copies' own mismatch: blind, by construction, to an error they share)
  a channel's window held for its dwell (consecutive updates) fires the detector, once per case; its zone is every
  cell of the windows held at that update, in either channel. A channel with boxes (det-ms) applies its criterion at
  every one of its boxes, and a window of any of them that holds fires it.
The primary and the variant are set from the tuning blocks (probes/p44a) by the rule declared in PLAN_AR002.md before
the tuning ran.
"""
from __future__ import annotations

import hashlib
import json

from ar001 import design as A

STUDY = "AR002"
TAG = "mse-ar002"
PROBE_TAG = "mse-p44"

# identities (the lead's assignment, 31 Oct: engineering 900350-900365, development 910664-910674 and 910646-910650,
# reserve 910817-910824; scanned free by the lead at about 11:15Z and again by fork A2)
SMOKE_BLOCK = 900350
TUNING_BLOCKS = (900350, 900351)
PROBE_BLOCKS = (900352, 900353, 900354, 900355)
PREFLIGHT_BLOCKS = (900356, 900357)
DEBUG_BLOCKS = (900358, 900359)
SPARE_ENGINEERING = tuple(range(900360, 900366))
DEVELOPMENT_BLOCKS = tuple(range(910646, 910651)) + tuple(range(910664, 910675))     # 16 blocks
RESERVE_BLOCKS = tuple(range(910817, 910825))                                       # held for the lead, not drawn
CONFIRMATION_FROM = 920128                                                          # AR002C, on the lead's word
IDENTITIES = {"preflight": PREFLIGHT_BLOCKS, "development": DEVELOPMENT_BLOCKS}
PURPOSE = {"preflight": "engineering", "development": "development", "probe": "engineering"}

SIDE, NCASE, CHUNK = A.SIDE, A.NCASE, A.CHUNK
WINDOW, READS, T_READ, TRACE, SIZE = A.WINDOW, A.READS, A.T_READ, A.TRACE, A.SIZE
CLOCK, T_STAR, SIG = A.CLOCK, A.T_STAR, A.SIG
BODIES, PATTERNS, THETAS, UNITS = A.BODIES, A.PATTERNS, A.THETAS, A.UNITS
SITUATIONS, SCORINGS, RIGHT, WRONG, WEIGHTS = A.SITUATIONS, A.SCORINGS, A.RIGHT, A.WRONG, A.WEIGHTS
BEST = "vote"                                                  # AR001's, named from its probe P41 and frozen there
unit_name, parse_unit = A.unit_name, A.parse_unit

# the detectors ------------------------------------------------------------------------------------------------------
# a configuration: per channel (cue, body) None or {box (window side), n (cells), q (fraction), dwell (updates); cue also
# ring (surround width) and ring_max (disagreeing live anchors allowed in the surround)}; set from the tuning blocks
DETECTORS = {
    "det": {"cue": {"box": 4, "n": 2, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1},
             "body": None},   # cue-b4-n2-q1-r2
    "det-v": {"cue": None,
               "body": {"box": 4, "n": 6, "q": 0.5, "dwell": 1}},   # body-b4-n6-q0.5-w1
    "det-ms": {"cue": {"boxes": tuple(range(4, 13)), "n": 2, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1},
               "body": None},   # the lead's ruling 1: det's cue channel at every box from 4 to 12 (reported only)
}
DET_ARMS = tuple(DETECTORS)
REGISTERED_DET = ("det", "det-v")                              # in the registered statements
REPORTED_DET = ("det-ms",)                                     # reported only; not in AR002C
A1_ARMS = ("vote", "rest", "dial")
ARMS = A1_ARMS + DET_ARMS
CONTROLLERS = ("dial",) + DET_ARMS

MISREAD_SIGMA = A.MISREAD_SIGMA                                # GC001's quenched misread (sigma 1), a side arm
MISREAD = ("none", "memory", "change")
SIZES = (2, 8)                                                 # the size arm's patch sides (the main grid's is SIZE, 4)
SIZE_SITUATIONS = ("memory", "correlated")
SIZE_DET = ("det", "det-ms")
# a run: (situation, sigma, AR001's arms, the detector arms, the patch's side)
RUNS = (tuple((s, 0.0, A1_ARMS, DET_ARMS, SIZE) for s in SITUATIONS)
        + tuple((s, MISREAD_SIGMA, ("rest", "dial"), REGISTERED_DET, SIZE) for s in MISREAD)
        + tuple((s, 0.0, A1_ARMS, SIZE_DET, L) for L in SIZES for s in SIZE_SITUATIONS))


def run_name(situation, sigma, a1=None, det=None, size=SIZE):
    """AR001's run name (situation@sigma), with -L<side> for a patch other than SIZE."""
    base = A.run_name(situation, sigma)
    return base if size == SIZE else f"{base}-L{size}"


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def stage_blocks(stage, override=None):
    if override is not None:
        if stage != "preflight" or not set(override) <= set(DEBUG_BLOCKS):
            raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
        return list(override)
    if stage == "probe":
        return list(PROBE_BLOCKS)
    return list(IDENTITIES[stage])


def tasks():
    """One task per (body, unit): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "smoke_block": SMOKE_BLOCK, "tuning_blocks": TUNING_BLOCKS, "probe_blocks": PROBE_BLOCKS,
            "debug_blocks": DEBUG_BLOCKS, "spare_engineering": SPARE_ENGINEERING, "reserve_blocks": RESERVE_BLOCKS,
            "confirmation_from": CONFIRMATION_FROM, "ar001_digest": A.digest(), "best": BEST,
            "detectors": DETECTORS, "a1_arms": A1_ARMS, "det_arms": DET_ARMS, "runs": RUNS, "window": WINDOW,
            "reads": READS, "t_read": T_READ, "trace": TRACE, "size": SIZE, "clock": CLOCK, "t_star": T_STAR,
            "sig": SIG, "units": UNITS, "bodies": BODIES, "scorings": SCORINGS, "right": RIGHT, "wrong": WRONG,
            "weights": WEIGHTS, "misread_sigma": MISREAD_SIGMA, "misread": MISREAD, "registered_det": REGISTERED_DET,
            "reported_det": REPORTED_DET, "sizes": SIZES, "size_situations": SIZE_SITUATIONS, "size_det": SIZE_DET}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar002").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar002.design  ->  ar002/frozen/design.json
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar002" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
