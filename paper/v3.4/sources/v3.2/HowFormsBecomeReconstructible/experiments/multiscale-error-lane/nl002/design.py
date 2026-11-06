"""NL002: the single source of truth for the runner, the reader and the checks.

Does the larger-scale reference preserve history or overwrite it? (the PI's "Multiscale 1", 30 October 2026.)
NL001 put three nested stores on a 64 x 64 sheet with no body and perfect templates: a region code (L2) that repaired
coherent regional errors also imposed a corrupted store, at the same gain (gain decides, not truth). NL002 puts those
stores into a developing body and lets them be ACQUIRED in an earlier episode, then asks whether the same descending
pathway restores the acquired pattern when its reference is right and erases history when it is wrong.

The tissue (64 x 64, NL001's scales: regions 4 x 4, blocks 16 x 16):
  body  DL001's double well dw (dl001.sim.body, unchanged: coupling 1, noise 0.1, quiet theta 0), reading the record
        at gain 0.2. At the lane's coupling it erases single-cell minorities at once and rounds the corners of 4 x 4
        islands slowly: a developing body that does not keep the finest scale by itself.
  L1    LR001's record of relations r with bonds H, W; one update in LR002's order: the record step (NL001's arithmetic:
        self-correction through the bonds, then the descending codes, one clip), then Hebbian relearning of the bonds
        from the body (LR002's 'body' repair, eta 0.01). No bond noise (declared: a gauge frame read from noisy bonds
        would mislead the region code).
  L2    a region code in the record's gauge frame (NL001's, absolute), and L3 a block code (NL001's, absolute).
  unit 'none'  the same stores with no body and no relearning: NL001's tissue (bit for bit with nl001.sim.run when the
        references are NL001's exact ones, Q3), here with acquired references.

Histories. A is NL001's template (16 balanced blocks; 4 of 16 regions per block with the block's opposite sign; 2 of 16
cells per region with the region's opposite sign). B shares A's block signs and draws its own minority regions and
cells (the same counts: matched statistics). Each is acquired from the same birth and noise (msegrid.acquire: settle,
teach, release), so they differ only in what was taught.

Acquisition and references (the information budget, per case):
  the tissue starts from A's acquired body, moving average and record R0_A; L1's bonds are R0_A's sign relations;
  the codes are READ FROM THE BODY at the end of acquisition: L2 = region means of (gauge frame x V0), L3 = block means
  of V0, each plus a declared read noise (SD READ_SD, addressed by case). Stored: L1 (r and two bond signs per cell),
  L2 (one value per region, 256), L3 (one per block, 16). Orientation: none stored; the gauge frame is a fixed rule
  (+1 at each region's corner, then along the region's own bonds).

The coarse reference (L2 and L3) in five arms, the same starting body and damage:
  own      A's acquired codes, read from A's body (the embodied acquisition: it carries what the body eroded);
  copy     A's codes read from A's acquired record R0_A instead (a faithful copy of the acquired history);
  foreign  B's acquired codes (another history, matched statistics);
  corrupt  A's L2 with the signs of as many regions flipped, at random, as differ in sign between A's and B's L2 (a
           matched count), and A's L3;
  off      no descending correction (k2 = k3 = 0); the body and L1's relearning kept.
Descending gain k2 in GAINS2 x KC (L3 at KC), under a declared resource limit: the descending increment per cell and
update is capped at CAP (it binds only at the top of the sweep); the dose (sum of |increment|) is recorded.

Events: none (an intact tissue: what a reference imposes); R (four regions of the record AND the body flipped
coherently, with the record's boundary bonds: a coherent regional error that L1 cannot see; NL001's R regions); K (a
2 x 2 square of regions holding one of A's minority regions killed, NL001's K square: the record 0, the bonds between
two dead cells 0 with strength 0, the body and its moving average newborn, KILL_SD x N(0, 1); the coarse codes are
kept, as the reference from above, where NL001's K also killed the region codes).

Successor, twice (the second added after the lead's review of P40, before the freeze): a fresh dw body born from
newborn noise reads, at gain 0.2, the record protected (no noise, no relearning: it steps through its bonds), for
WINDOW2 updates,
  L1-only  the tissue's final L1 record (r, H, W): the codes stay behind; beside A's and B's acquired records and the
           same newborn reading nothing (gain 0);
  coded    the same record together with the branch's coarse codes, its reference's L2 and L3 at its own gains k2, k3
           (NL001's arithmetic, the cap, the gauge frame of the inherited bonds); 'off' passes no codes.
The coded packet adds L2 (256 one-bit codes), L3 (16 values) and the two gains to the information budget.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from nl001 import design as N1

TAG = "mse-nl002"
PROBE_TAG = "mse-p40"
STUDY = "NL002"
IDENTITIES = {
    "preflight": (900808, 900810),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910720, 910736),   # the NL002 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900810, 900812)       # the engine reserves 900000-900999 for engineering; 900804-900811 scanned free (the lead)
PROBE_BLOCKS = (900804, 900808)       # engineering probe P40 (tag mse-p40), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = N1.MESSAGES, N1.PARENTS, N1.NCASE
AMPLITUDE = N1.AMPLITUDE
EPS, KR, SIGMA_R, KC, R_STAR = N1.EPS, N1.KR, N1.SIGMA_R, N1.KC, N1.R_STAR
SIDE, REGION, BLOCK = N1.SIDE, N1.REGION, N1.BLOCK
MINORITY_REGIONS, MINORITY_CELLS = N1.MINORITY_REGIONS, N1.MINORITY_CELLS
N_REGIONS = N1.N_REGIONS
CHUNK = N1.CHUNK

SETTLE, TEACH, RELEASE, SIGMA_ACQ = 120, 1000, 200, 0.1   # BR001's acquisition (msegrid.acquire), as DL002
SIGMA = 0.1                                                # the body's noise (DL002, LR002, NP001)
GAIN = 0.2                                                 # the body reads the record (DL002's rel gain)
STRENGTH0, ETA = 0.8, 0.01                                 # a taught bond's strength; Hebbian relearning (LR001, LR002)
READ_SD = 0.1                                              # the declared noise on each code read from the body
GAINS2 = (0.25, 0.5, 0.75, 1.0, 2.0)                       # k2 in units of KC
CAP = 0.06                                                 # the resource limit: |descending increment| per cell, update
UNITS = ("dw", "none")                                     # the developing body; NL001's stores with no body


@dataclass(frozen=True)
class Arm:
    name: str
    ref: str           # own | foreign | corrupt | off
    k2: float          # in units of KC
    k3: float          # in units of KC


REFS = ("own", "copy", "foreign", "corrupt")
ARMS = (Arm("off", "off", 0.0, 0.0),
        *(Arm(f"{ref}-k{g:g}", ref, g, 1.0) for ref in REFS for g in GAINS2))
ARMNAMES = tuple(a.name for a in ARMS)
ARM = {a.name: a for a in ARMS}
EVENTS = ("none", "R", "K")
KILL_SD = 0.2                                              # newborn body values in a killed square (DL001)
LABELS = tuple((a, e) for e in EVENTS for a in ARMNAMES)        # event-major
WINDOW, READS = 2000, (250, 1000, 2000)
WINDOW2, READS2 = 2000, (500, 1000, 2000)


def unit_name(u):
    return u


def parse_unit(name):
    return name


def tasks():
    return [(u,) for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "amplitude": AMPLITUDE, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC, "r_star": R_STAR,
            "side": SIDE, "region": REGION, "block": BLOCK, "minority_regions": MINORITY_REGIONS,
            "minority_cells": MINORITY_CELLS, "n_regions": N_REGIONS, "chunk": CHUNK,
            "acquisition": {"settle": SETTLE, "teach": TEACH, "release": RELEASE, "sigma_acq": SIGMA_ACQ},
            "sigma": SIGMA, "gain": GAIN, "strength0": STRENGTH0, "eta": ETA, "bond_noise": 0.0, "read_sd": READ_SD,
            "gains2": GAINS2, "refs": REFS, "cap": CAP, "kill_sd": KILL_SD, "units": UNITS, "body": "dw (dl001.sim.body, alpha 0)",
            "arms": [asdict(a) for a in ARMS], "events": EVENTS, "labels": LABELS,
            "window": WINDOW, "reads": READS, "window2": WINDOW2, "reads2": READS2,
            "packet": {"l1_only": "the final L1 record (r, H, W); the codes stay behind",
                       "coded": "the final L1 record with the branch's L2 and L3 at its own k2, k3; off passes none"}}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "msegrid", "br001", "lr001", "lr002", "dl001", "dl002", "nl001", "nl002")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m nl002.design  ->  nl002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "nl002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
