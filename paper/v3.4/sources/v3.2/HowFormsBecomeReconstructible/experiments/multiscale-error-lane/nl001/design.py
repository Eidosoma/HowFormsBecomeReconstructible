"""NL001: the single source of truth for the runner, the reader and the checks.

Nested levels. The lane's first principle, "correct at every scale the body cannot regenerate, and no finer", was
tested two levels at a time (cell consensus or relations, plus one coarse code over 4 x 4 regions: BR001, BR002,
GW001, LR001). NL001 runs three nested levels at once on a 64 x 64 sheet, with damage at three scales together, and
the traffic between levels.

The tissue is LR001's record of relations alone (writing off, no body): r <- r + EPS [r (1 - (r/R*)^2) +
KR (sum_j J_ij r_j / 4 - r)] + SIGMA_R xi, with the bonds J holding the template's relations, then each level's code,
one clip (lr001.sim.step's arithmetic and constants; msegrid's bproj). The levels:
  L1  the per-cell record and its relations (always present);
  L2  a region code, one value per 4 x 4 region, in L1's gauge frame (LR001's gauge code): the region's frame sign;
  L3  a block code, one value per 16 x 16 block: the block's mean, restored by an even shift (BR002's plain code at
      the block scale).
Two ways to store L2:
  absolute  each region's own frame sign (its identity, redundant with L3's block mean);
  relative  each region's frame sign relative to its block's sign, read through L3's store (a pure hierarchy).
And a derived L3: the block mean implied by the region codes (L2's stores), not a store of its own.

The template has structure at every scale: 16 blocks of balanced signs; in each block 4 of 16 regions with the
block's opposite sign; in each region 2 of 16 cells with the region's opposite sign.

Events (each case's sites and units addressed by the case): scattered fine flips (F), coherent regional errors (R:
4 regions' records flipped with their boundary bonds, so L1 holds no trace), a coherent block error (B: one block's
records flipped with its boundary bonds and its absolute region codes, so L1 and absolute L2 hold no trace), all
three together (FRB), a corrupted block store (C3), a corrupted region store (C2), and none.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from br001 import design as B1

TAG = "mse-nl001"
PROBE_TAG = "mse-p34"
STUDY = "NL001"
IDENTITIES = {
    "preflight": (900564, 900566),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910380, 910396),   # the NL001 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900566, 900568)
PROBE_BLOCKS = (900560, 900564)       # engineering probe P34 (tag mse-p34), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = B1.MESSAGES, B1.PARENTS, B1.NCASE
AMPLITUDE = B1.AMPLITUDE
EPS, KR, SIGMA_R, KC, R_STAR = B1.EPS, B1.KR, B1.SIGMA_R, B1.KC, B1.R_STAR

SIDE, REGION, BLOCK = 64, 4, 16
MINORITY_REGIONS, MINORITY_CELLS = 4, 2          # per block, per region
FINE_SHARE = 0.05                                 # F: share of cells flipped
N_REGIONS = 4                                     # R: regions flipped coherently (outside B's block)


@dataclass(frozen=True)
class Arm:
    name: str
    l2: str = "none"       # none | abs | rel
    l3: str = "none"       # none | abs | derived
    k2: float = KC
    k3: float = KC


BASE = (Arm("L1"),
        Arm("L1L2", l2="abs"),
        Arm("L1L3", l3="abs"),
        Arm("L1L2L3", l2="abs", l3="abs"),
        Arm("L1L2rL3", l2="rel", l3="abs"),
        Arm("L1L2L3d", l2="abs", l3="derived"))
GAIN = (Arm("L1L2L3-k3x2", l2="abs", l3="abs", k3=2 * KC),        # the block code stronger than the region code
        Arm("L1L2L3-k3x3", l2="abs", l3="abs", k3=3 * KC),
        Arm("L1L2L3-k3x4", l2="abs", l3="abs", k3=4 * KC),
        Arm("L1L2L3-k3x5", l2="abs", l3="abs", k3=5 * KC),
        Arm("L1L2L3-k3x6", l2="abs", l3="abs", k3=6 * KC),
        Arm("L1L2L3-k3x8", l2="abs", l3="abs", k3=8 * KC),
        Arm("L1L3-k3x4", l3="abs", k3=4 * KC),                     # the block code alone, stronger
        Arm("L1L3-k3x8", l3="abs", k3=8 * KC),
        Arm("L1L2rL3-k3x0.25", l2="rel", l3="abs", k3=0.25 * KC),  # the relative hierarchy with a weak block code
        Arm("L1L2-k2x0.25", l2="abs", k2=0.25 * KC),               # the region code weaker than at the lane's KC
        Arm("L1L2-k2x0.5", l2="abs", k2=0.5 * KC),
        Arm("L1L2-k2x0.75", l2="abs", k2=0.75 * KC))
ARMS = BASE + GAIN
ARMNAMES = tuple(a.name for a in ARMS)
ARM = {a.name: a for a in ARMS}
EVENTS = ("none", "F", "R", "B", "FRB", "C3", "C2", "K")
_B3UP = ("L1L2L3-k3x2", "L1L2L3-k3x3", "L1L2L3-k3x4", "L1L2L3-k3x5", "L1L2L3-k3x6", "L1L2L3-k3x8")
_L3UP = ("L1L3-k3x4", "L1L3-k3x8")
_BASE = tuple(a.name for a in BASE)
RUNS = {"none": _BASE + _B3UP + _L3UP,                      # what a level costs where nothing is damaged
        "F": _BASE,
        "R": _BASE + _L3UP + ("L1L2-k2x0.25", "L1L2-k2x0.5", "L1L2-k2x0.75"),
        "B": _BASE + _B3UP + _L3UP + ("L1L2rL3-k3x0.25",),
        "FRB": _BASE + _B3UP + _L3UP,
        "C3": _BASE + _B3UP + ("L1L2rL3-k3x0.25",),
        "C2": _BASE + ("L1L2-k2x0.25", "L1L2-k2x0.5", "L1L2-k2x0.75"),
        "K": _BASE}
LABELS = tuple((ARM[a], e) for e in EVENTS for a in RUNS[e])
WINDOW, READS = 2000, (250, 1000, 2000)
CHUNK = 250
KILL = 2                                          # K: a KILL x KILL square of regions (8 x 8 cells) killed


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "amplitude": AMPLITUDE, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC, "r_star": R_STAR,
            "side": SIDE, "region": REGION, "block": BLOCK, "minority_regions": MINORITY_REGIONS,
            "minority_cells": MINORITY_CELLS, "fine_share": FINE_SHARE, "n_regions": N_REGIONS,
            "arms": [asdict(a) for a in ARMS], "events": EVENTS, "runs": RUNS, "window": WINDOW, "reads": READS,
            "chunk": CHUNK, "kill": KILL}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "msegrid").glob("*.py"), *(lane / "br001").glob("*.py"),
                    *(lane / "lr001").glob("*.py"), *(lane / "nl001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m nl001.design  ->  nl001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "nl001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
