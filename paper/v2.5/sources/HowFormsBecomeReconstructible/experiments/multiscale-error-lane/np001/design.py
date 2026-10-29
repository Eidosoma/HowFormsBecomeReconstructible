"""NP001: the single source of truth for the runner, the reader and the checks.

Does the body preserve an acquired pattern that differs from its native preference? LR002's tissue (lr002.sim.relations,
dl001.sim.body and dl002.sim.prepare, unchanged and imported): DL001's bodies reading a record of relations at gain 0.2
with no coarse code (k_c 0), so nothing positional holds the pattern; the record's bonds under bond-sign noise, relearned
from the body (LR002's 'body' repair) or from the record with plaquette parity (LR001's two layers), on a 32-site sheet.

Native preference, operationally (P31, PLAN_NP001.md): what a body does with no record read.
  dw     holds any acquired pattern; from newborn noise it coarsens without a preferred spacing: permissive.
  li2    holds stripes of period 8 (S4) and breaks period 16 (S8: 0.54) and two domains (F0: 0.58); from noise period
         8 at chance registration: imposing (a short inhibitor range, L 2; the same period as li4).
  li4    holds stripes of period 8 (S4) and breaks S8 (0.52) and F0 (0.55) into its own period 8; from noise period 8
         at chance registration: imposing (L 4).
  li16   holds every acquired pattern on this sheet; from noise period about 14: permissive here.
No body in DL001's set imposes a spacing other than 8 on this sheet.
Acquired patterns (units, quiet tissue theta x 0): S4 (period-8 stripes, DL002's), S4 shifted by 1, 2 and 3 sites
across the stripes (S4s1-S4s3; the same acquisition noise, only the taught template moved), S8 (period 16) and F0 (two
domains). DL002's message kinds already give both orientations and the inverse (a shift of 4) of each.
Phase conflicts (C4s1-C4s3): the body and its moving average from S4's acquisition (phase 0), the record from S4sK's
(phase K; the same acquisition noise): the body's current organization against the record's history at the same
spacing. T is the record's template (phase K, the history); T0 the body's initial one (phase 0). For every other unit
T0 = T.

Stage 1 (4,000 updates from the acquired state, one body under every condition as branches):
  alone    the record is not read (gain 0): the body's own dynamics
  intact   the record read at 0.2, no bond noise, no relearning (LR002's 0/none)
  body1    bond noise 1e-3, bonds relearned from the body (LR002's 0.001/body)
  record1  bond noise 1e-3, bonds relearned from the record, plus parity (LR002's 0.001/record+parity)
  body     bond noise 1e-2, bonds relearned from the body (LR002's 0.01/body: the reported 0.97)
  body3    bond noise 3e-2, bonds relearned from the body (LR002's 0.03/body)
Stage 2, fresh successors (2,000 updates): each of dw, li2, li4 and li16, born from newborn noise, reads a stage-1 record
(every condition but 'alone') at gain 0.2 with the record protected (no bond noise, no relearning); and the same newborn
body with no record read (gain 0), the paired control. Successors of one body share their birth and noise across
conditions and against the control, so contrasts isolate what each record carries.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from dl001 import design as DL
from dl002 import design as D2
from lr002 import design as L2

TAG = "mse-np001"
PROBE_TAG = "mse-p31"
STUDY = "NP001"
IDENTITIES = {
    "preflight": (900632, 900634),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910320, 910336),   # the NP001 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900634, 900636)
PROBE_BLOCKS = (900628, 900632)       # engineering probe P31 (tag mse-p31), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = D2.MESSAGES, D2.PARENTS, D2.NCASE
SIDE, SIGMA, CHUNK = D2.SIDE, D2.SIGMA, D2.CHUNK
EPS, KR, SIGMA_R, KC = L2.EPS, L2.KR, L2.SIGMA_R, L2.KC      # LR002's record of relations, no coarse code
GAIN, STRENGTH0, ETA = L2.GAIN, L2.STRENGTH0, L2.ETA
BODIES = ("dw", "li2", "li4", "li16")
PATTERNS = ("S4", "S4s1", "S4s2", "S4s3", "S8", "F0")
CONFLICTS = ("C4s1", "C4s2", "C4s3")                       # body at S4's phase 0, record at S4's phase K
THETA = 0.0                                                # quiet tissue only


@dataclass(frozen=True)
class Cond:
    name: str
    gain: float
    rate: float
    repair: str        # LR002's repairs: none | record+parity | body

    @property
    def parity(self):
        return self.repair.endswith("parity")

    @property
    def learn(self):
        head = self.repair.split("+")[0]
        return head if head in ("record", "body") else ""


CONDS = (Cond("alone", 0.0, 0.0, "none"), Cond("intact", GAIN, 0.0, "none"), Cond("body1", GAIN, 0.001, "body"),
         Cond("record1", GAIN, 0.001, "record+parity"), Cond("body", GAIN, 0.01, "body"), Cond("body3", GAIN, 0.03, "body"))
CONDNAMES = tuple(c.name for c in CONDS)
HANDED = tuple(c for c in CONDS if c.name != "alone")       # the records handed to successors
SUCC_BODIES = BODIES
WINDOW, READS = 4000, (1000, 2000, 4000)
WINDOW2, READS2 = 2000, (500, 1000, 2000)
NATIVE_OF = {"dw": "none", "li2": "period 8", "li4": "period 8", "li16": "period about 14 from noise"}


def shift_of(pattern):
    """The record's phase shift (S4sK and C4sK)."""
    return int(pattern[3:]) if pattern[:3] in ("S4s", "C4s") else 0


def is_conflict(unit):
    return unit.startswith("C4s")


def unit_name(pattern):
    return pattern


def parse_unit(name):
    return name, THETA


UNITS = PATTERNS + CONFLICTS


def tasks():
    return [(b, u) for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged); S4s1-S4s3: the same "
                           "acquisition with the S4 template rolled across its stripes; C4s1-C4s3: the body and moving "
                           "average from S4's acquisition, the record from S4sK's",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "gain": GAIN, "strength0": STRENGTH0, "eta": ETA,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "conflicts": CONFLICTS,
            "theta": THETA,
            "conds": [[c.name, c.gain, c.rate, c.repair] for c in CONDS], "handed": [c.name for c in HANDED],
            "successor_bodies": SUCC_BODIES, "window": WINDOW, "reads": READS, "window2": WINDOW2, "reads2": READS2}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "dl002").glob("*.py"), *(lane / "lr001").glob("*.py"),
                    *(lane / "lr002").glob("*.py"), *(lane / "np001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m np001.design  ->  np001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "np001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
