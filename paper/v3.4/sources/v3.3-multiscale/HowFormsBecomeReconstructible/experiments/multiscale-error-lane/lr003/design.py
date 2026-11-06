"""LR003: the single source of truth for the runner, the reader and the checks.

Gated teaching. LR002's tissue (DL002's preparation and DL001's bodies, unchanged; the relational record's bonds, without
the coarse code, under LR001's bond-sign noise; the body reads the record at gain 0.2), with the bonds relearned at
eta 0.01 from a source chosen per branch and, for the gates, per bond:
  record    the record's co-activity r_i r_j / R*^2 (LR001's);
  body      the body's co-activity V_i V_j (LR002's);
  agree     the body's where the body agrees in sign with the record at both ends of the bond, the record's elsewhere;
  syndrome  the body's where the bond is frustrated, J_ij s(r_i) s(r_j) < 0 (it disagrees with the record's current
            values), the record's elsewhere;
  site      the body's on every bond touching a site with a frustrated bond, the record's elsewhere.
'+parity' adds LR001's plaquette rule after the learning. One update, in order: the body reads the record
(dl001.sim.body); bond noise; the record step through the bonds (msegrid.record_step, k_c 0); relearning; parity.
For the record and body sources the arithmetic is lr002.sim.relations's (checks Q3).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from dl001 import design as DL
from lr002 import design as L2

TAG = "mse-lr003"
PROBE_TAG = "mse-p18"
STUDY = "LR003"
IDENTITIES = {
    "preflight": (900744, 900746),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910980, 910996),   # the LR003 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900746, 900748)
PROBE_BLOCKS = (900740, 900744)       # engineering probe P18 (tag mse-p18), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = L2.MESSAGES, L2.PARENTS, L2.NCASE
SIDE, SIGMA, CHUNK = L2.SIDE, L2.SIGMA, L2.CHUNK
EPS, KR, SIGMA_R, KC = L2.EPS, L2.KR, L2.SIGMA_R, L2.KC
GAIN, STRENGTH0, ETA = L2.GAIN, L2.STRENGTH0, L2.ETA
BODIES = L2.BODIES
PATTERNS = L2.PATTERNS
THETAS = (0.0, 1.0)
RATES = (0.0, 0.001, 0.003, 0.01, 0.03)
REPAIRS = ("record", "record+parity", "body", "body+parity", "agree", "syndrome", "site", "site+parity")
SOURCES = {"": 0, "record": 1, "body": 2, "agree": 3, "syndrome": 4, "site": 5}
WINDOW, READS = 4000, (1000, 2000, 4000)


@dataclass(frozen=True)
class Cond:
    rate: float
    repair: str

    @property
    def name(self):
        return f"{self.rate:g}/{self.repair}"

    @property
    def parity(self):
        return self.repair.endswith("parity")

    @property
    def source(self):
        s = self.repair.split("+")[0]
        return s if s in SOURCES else ""


CONDS = tuple(Cond(r, rep) for r in RATES for rep in REPAIRS)


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
            "gain": GAIN, "strength0": STRENGTH0, "eta": ETA,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS,
            "rates": RATES, "repairs": REPAIRS, "sources": SOURCES, "conds": [c.name for c in CONDS], "units": UNITS,
            "window": WINDOW, "reads": READS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "dl002").glob("*.py"), *(lane / "lr001").glob("*.py"),
                    *(lane / "lr002").glob("*.py"), *(lane / "lr003").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m lr003.design  ->  lr003/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "lr003" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
