"""AR003: a detector sized to the injury, with the vote as the controller's default (REPORT_AR002.md Next 2-3,
REPORT_AR002C.md Next 1-2; the PI's "lets go on both in parallel", 1 November 2026; PLAN_AR003.md).

AR002 found, and AR002C confirmed, that a tissue-made detector (det) drives AR001's controller past the vote. det is
sized to the 4 x 4 injury (at 8 x 8 it keeps a fifth of the declared signal's worth; at 2 x 2 no detector finds the
injury in time, and the vote is best), and the controller's default, rest, gives up the vote's advantage where nothing
needs correcting. AR003 registers a detector sized to the injury, tuned on engineering blocks by the rule fixed in
PLAN_AR003.md before the tuning ran, and gives the controller the vote as its default.

Everything else is AR002's and AR001's, imported unchanged (ar002.design, ar002.sim, ar001.design, ar001.sim and
through them be006, be005, be002, be001 and lr005): BE006's tissue at clock SL (T* = 1,959 updates), one event at t = 0,
8,000 updates, scored at t = 8,000; the eight unit-body pairs; the seven situations and eight scorings with equal
weights; BEST = the vote, AR001's, named from its probe P41 and frozen there.

The arms (paired: every branch reads the case's body, record, bond-noise and second-record streams):
  vote    BEST, AR001's (ar001.sim.run)
  det     AR002's controller: its det (cue-b4-n2-q1-r2) with the rest default (ar002.sim.run_det)
  ms      the tuned multi-size detector DET_STAR with the rest default (ar002.sim.run_det)
  vms     THE CONTROLLER: DET_STAR with the vote default (ar003.sim.run_vd)
  vdial   the declared signal under the vote default: an oracle that fires at update 1 over the patch (ar003.sim.run_vd)
Sizes: AR002's nested patches, 2 x 2, 4 x 4 and 8 x 8 (sharing the corner), with equal weights in the size mix. none and
scattered cue damage are run at 4 x 4 and scored on every size's patch (their events and every arm but vdial's
footprint are independent of the patch); the information-limit pair contributes 1/8 exactly at every size (the
identity) and is run at 4 x 4 only. The misread side arm: GC001's quenched misread (sigma 1) in none and memory, det and
vms.
"""
from __future__ import annotations

import hashlib
import json

from ar001 import design as A
from ar002 import design as A2

STUDY = "AR003"
TAG = "mse-ar003"
PROBE_TAG = "mse-p47"

# identities (the lead's assignment, 1 Nov ~11:00Z; scanned free by the lead and again by fork A3 at 11:26Z)
SMOKE_BLOCKS = (900160, 900161)
TUNING_BLOCKS = (900148, 900149)                               # stage 1, stage 2
TUNING_RESERVE = (900150, 900151)                              # unused, in reserve for the tuning
PROBE_BLOCKS = (900152, 900153, 900154, 900155)
PREFLIGHT_BLOCKS = (900156, 900157)
DEBUG_BLOCKS = (900158, 900159)
SPARE_ENGINEERING = tuple(range(900162, 900168))
DEVELOPMENT_BLOCKS = tuple(range(910548, 910553)) + tuple(range(910554, 910560)) + tuple(range(910587, 910592))
RESERVE_BLOCKS = (910577, 910578, 910580, 910581, 910582, 910584, 910585, 910592)   # held for the lead, not drawn
CONFIRMATION_FROM = 920148                                     # AR003C, on the lead's word; blocks assigned by the lead
IDENTITIES = {"preflight": PREFLIGHT_BLOCKS, "development": DEVELOPMENT_BLOCKS}
PURPOSE = {"preflight": "engineering", "development": "development", "probe": "engineering", "debug": "engineering",
           "smoke": "engineering"}

SIDE, NCASE, CHUNK = A.SIDE, A.NCASE, A.CHUNK
WINDOW, READS, T_READ, TRACE, SIZE = A.WINDOW, A.READS, A.T_READ, A.TRACE, A.SIZE
CLOCK, T_STAR, SIG = A.CLOCK, A.T_STAR, A.SIG
BODIES, PATTERNS, THETAS, UNITS = A.BODIES, A.PATTERNS, A.THETAS, A.UNITS
SITUATIONS, SCORINGS, WEIGHTS = A.SITUATIONS, A.SCORINGS, A.WEIGHTS
BEST = "vote"                                                  # AR001's, named from its probe P41 and frozen there
unit_name, parse_unit = A.unit_name, A.parse_unit

# the detectors ------------------------------------------------------------------------------------------------------
# DET_STAR: set from the tuning blocks by PLAN_AR003.md's rule (probes/p47a_ar003_detector_tuning.py; results in
# probes/results/p47a_ar003_detector_tuning.txt): ms-b2-n3-q1, by the rule's second tier (no shortlisted candidate met
# 0.005 under scattered cue damage; all three met the confirmed bounds 0.01 and 0.002; it had the largest Delta2,
# +0.0949 on 900149). Until the tuning ran it held AR002's det-ms (ms-b4-n2-q1) as a placeholder for the smoke and tests.
DET_STAR_NAME = "ms-b2-n3-q1"
DET_STAR = {"cue": {"boxes": tuple(range(2, 13)), "n": 3, "q": 1.0, "ring": 2, "ring_max": 0, "dwell": 1}, "body": None}
DETECTORS = {"det": A2.DETECTORS["det"], "ms": DET_STAR}                       # rest-default arms (ar002.sim.run_det)
VD_DETECTORS = {"vote": {"never": True}, "vdial": {"oracle": True}, "vms": DET_STAR}   # vote-default arms (ar003.sim)
CONTROLLER = "vms"


def candidate(b_min, n, q):
    """A tuning candidate: det's cue rule at every box from b_min to 12 (surround of width 2, none disagreeing), dwell 1."""
    return {"cue": {"boxes": tuple(range(b_min, 13)), "n": n, "q": q, "ring": 2, "ring_max": 0, "dwell": 1}, "body": None}


CANDIDATES = {f"ms-b{b}-n{n}-q{q:g}": candidate(b, n, q) for b in (2, 3, 4) for n in (2, 3) for q in (1.0, 0.75)}

# the runs -----------------------------------------------------------------------------------------------------------
SIZES = (2, 4, 8)                                              # the size mix, equal weights
SIZE_WEIGHTS = {L: 1.0 / len(SIZES) for L in SIZES}
MISREAD_SIGMA = A.MISREAD_SIGMA
SIZE_FREE = ("none", "cue")                                    # run at SIZE, scored on every size's patch
FOUR = ("none", "body", "shared", "cue")                       # where nothing needs correcting (AR002's gap)
HITS = ("memory", "correlated")
PAIR = ("change/new", "change/old")


def R(situation, sigma, a1, det, vd, size=SIZE):
    return (situation, sigma, tuple(a1), tuple(det), tuple(vd), size)


RUNS = (R("none", 0.0, ("vote",), ("det", "ms"), ("vms",)),
        R("body", 0.0, ("vote",), ("det", "ms"), ("vms",)),
        R("memory", 0.0, ("vote",), ("det", "ms"), ("vms", "vdial")),
        R("correlated", 0.0, ("vote",), ("det", "ms"), ("vms", "vdial")),
        R("shared", 0.0, ("vote",), ("det", "ms"), ("vms",)),
        R("cue", 0.0, ("vote",), ("det", "ms"), ("vms",)),
        R("change", 0.0, ("vote",), ("det",), ("vms",)),
        R("memory", 0.0, ("vote",), ("det", "ms"), ("vms",), 2),
        R("correlated", 0.0, ("vote",), ("det", "ms"), ("vms",), 2),
        R("body", 0.0, ("vote",), ("det", "ms"), ("vms",), 2),
        R("shared", 0.0, ("vote",), ("det", "ms"), ("vms",), 2),
        R("memory", 0.0, ("vote",), ("det",), ("vms", "vdial"), 8),
        R("correlated", 0.0, ("vote",), ("det",), ("vms", "vdial"), 8),
        R("body", 0.0, ("vote",), ("det",), ("vms",), 8),
        R("shared", 0.0, ("vote",), ("det",), ("vms",), 8),
        R("none", MISREAD_SIGMA, (), ("det",), ("vms",)),
        R("memory", MISREAD_SIGMA, (), ("det",), ("vms",)))


def run_name(situation, sigma, a1=None, det=None, vd=None, size=SIZE):
    """AR001's run name (situation@sigma), with -L<side> for a patch other than SIZE (AR002's)."""
    return A2.run_name(situation, sigma, size=size)


def arms_of(run):
    return tuple(run[2]) + tuple(run[3]) + tuple(run[4])


RUNNAMES = tuple(run_name(*x) for x in RUNS)
ARM_RUNS = sum(len(arms_of(x)) for x in RUNS)


def stage_blocks(stage, override=None):
    if override is not None:
        if stage != "preflight" or not set(override) <= set(DEBUG_BLOCKS):
            raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
        return list(override)
    if stage == "probe":
        return list(PROBE_BLOCKS)
    if stage == "debug":
        return [DEBUG_BLOCKS[0]]
    return list(IDENTITIES[stage])


def tasks():
    """One task per (body, unit): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "smoke_blocks": SMOKE_BLOCKS, "tuning_blocks": TUNING_BLOCKS, "tuning_reserve": TUNING_RESERVE,
            "probe_blocks": PROBE_BLOCKS, "debug_blocks": DEBUG_BLOCKS, "spare_engineering": SPARE_ENGINEERING,
            "reserve_blocks": RESERVE_BLOCKS, "confirmation_from": CONFIRMATION_FROM, "ar001_digest": A.digest(),
            "ar002_digest": A2.digest(), "best": BEST, "det_star_name": DET_STAR_NAME, "detectors": DETECTORS,
            "vd_detectors": VD_DETECTORS, "controller": CONTROLLER, "candidates": CANDIDATES, "runs": RUNS,
            "window": WINDOW, "reads": READS, "t_read": T_READ, "trace": TRACE, "size": SIZE, "sizes": SIZES,
            "size_weights": SIZE_WEIGHTS, "size_free": SIZE_FREE, "clock": CLOCK, "t_star": T_STAR, "sig": SIG,
            "units": UNITS, "bodies": BODIES, "scorings": SCORINGS, "weights": WEIGHTS, "misread_sigma": MISREAD_SIGMA,
            "four": FOUR, "hits": HITS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A2.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar003").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar003.design  ->  ar003/frozen/design.json
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar003" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
