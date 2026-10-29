"""LR005 (DRAFT, not frozen): four situations under shared damage.

LR004's tissue (DL002's preparation and DL001's bodies; the relational record's bonds, without the coarse code, read by
the body at gain 0.2; bonds relearned at eta 0.01), with three references of different kinds: the body, the record and
a positional cue (anchors at a quarter of the cells holding the acquired record's signs). One event at t = 0 on an
8 x 8 patch (or, for cue damage, scattered over the sheet), then background bond noise:
  body     the body's values flipped in the patch;
  memory   the record's values flipped in the patch with its bonds made consistent with them (no frustration anywhere);
  shared   the patch's cells killed: newborn body values, record 0, bonds between two dead cells lost, anchors lost
           (vote2r: both records);
  cue      a random quarter of the anchors flipped, scattered;
  change   the cue re-specified in the patch (its anchors flipped). Scored against the changed target (adoption) and
           against the old one (the same run is coherent cue damage: refusal).
Teachers (the bond target per arm):
  record+parity  LR001's two layers;      body   LR002's;
  vote2r         LR004's vote (a second record, sharing wounds);
  cue            LR004's anchors: body where body and record agree, the anchor where they disagree at an anchored cell,
                 else the record;
  vote3          the majority of body, record and anchor (ties to the record);
  community-s/c cue, but in a zone where at least Q of the live anchors within radius RHO disagree with the record
                 (at least MIN_ANCHORS present), the record is trusted inverted; the decision and its sign are held by a
                 slow latch for LATCH updates, and the record's values are pulled toward the trusted sign there at gain
                 PULL. Two settings: sensitive (s) and conservative (c).
A no-event control ('none') measures each arm's level and the community arms' false alarms without any event.
The body reads the first record at one of two gains (GAINS): weakly, so that it stays an independent copy, or at
LR004's 0.2.
A vote is cast only by a confident value (|x| >= VMIN); a dead cell casts none.
"""
from __future__ import annotations

import hashlib
import json

from dl001 import design as DL
from dl002 import design as DL2
from lr004 import design as L4

TAG = "mse-lr005"
PROBE_TAG = "mse-p20"
STUDY = "LR005"
PROBE_BLOCKS = (900760, 900764)
IDENTITIES = {"preflight": (900764, 900766), "development": (910040, 910056)}
DEBUG_BLOCKS = (900766, 900768)

SIDE, SIGMA, CHUNK = L4.SIDE, L4.SIGMA, L4.CHUNK
EPS, KR, SIGMA_R, KC, GAIN, STRENGTH0, ETA = L4.EPS, L4.KR, L4.SIGMA_R, L4.KC, L4.GAIN, L4.STRENGTH0, L4.ETA
BODIES, PATTERNS, THETAS = L4.BODIES, L4.PATTERNS, (0.0, 1.0)
KILL_SD = DL2.KILL_SD
PATCH = 8
DENSITY = 4
VMIN = 0.2
RHO, MIN_ANCHORS, PULL = 3, 4, 1.0
COMMUNITY = {"community-s": (0.5, 300), "community-c": (0.75, 300)}   # (Q, LATCH)
GAINS = (0.05, 0.2)
SITUATIONS = ("none", "body", "memory", "shared", "cue", "change")
ARMS = ("record+parity", "body", "vote2r", "cue", "vote3", "community-s", "community-c")
RATE = 0.001
WINDOW, READS = 4000, (250, 1000, 2000, 4000)
TRACE = 100
TRACE_READS = tuple(range(TRACE, WINDOW + 1, TRACE))
PURPOSE = {"preflight": "engineering", "development": "development"}
MESSAGES, PARENTS, NCASE = L4.MESSAGES, L4.PARENTS, L4.NCASE


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


def unit_name(pattern, theta):
    return f"{pattern}_t{theta:g}"


def parse_unit(name):
    pattern, t = name.split("_")
    return pattern, float(t[1:])


UNITS = tuple(unit_name(p, t) for p in PATTERNS for t in THETAS)


def tasks():
    return [("E", u) for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "lr002.sim.prepare = dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "patch": PATCH, "density": DENSITY, "vmin": VMIN,
            "rho": RHO, "min_anchors": MIN_ANCHORS, "pull": PULL, "community": COMMUNITY, "gains": GAINS,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS,
            "situations": SITUATIONS, "arms": ARMS, "rate": RATE, "units": UNITS, "window": WINDOW, "reads": READS,
            "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m lr005.design  ->  lr005/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "lr005" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
