"""LR004: the single source of truth for the runner, the reader and the checks.

A third copy as tie-breaker. LR003's tissue (DL002's preparation and DL001's bodies, unchanged; the relational record's
bonds, without the coarse code, under LR001's bond-sign noise; the body reads the record at gain 0.2), with the bonds
relearned at eta 0.01 from a source chosen per branch:
  record+parity  LR001's two layers (the record's co-activity, then the plaquette rule);
  body           the body's co-activity (LR002's);
  site           the body on every bond of a site with a frustrated bond, the record elsewhere (LR003's);
  pair           a second relational record, with its own bond and record noise; both records relearn each bond toward
                 their common relation where they agree and keep it where they disagree (two copies, no tie-breaker);
  vote           the same two records and the body: both records relearn each bond toward the majority of the three
                 relations, sign(V_i V_j), sign(rA_i rA_j) and sign(rB_i rB_j) (three copies);
  anchors4/16    positional anchors, the acquired record's sign held at a random quarter (sixteenth) of the cells,
                 decide where the body and the record disagree in sign; the record's sign is trusted where they disagree
                 at an unanchored cell, and the body's where they agree; each bond relearns toward the product of the
                 trusted signs at its ends.
The body reads the first record only. One update, in order: the body reads the record (dl001.sim.body); bond noise; the
record steps through the bonds (msegrid.record_step, k_c 0); relearning; parity. For record+parity, body and site the
arithmetic is lr003.sim.relations's (checks Q3).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from dl001 import design as DL
from lr003 import design as L3

TAG = "mse-lr004"
PROBE_TAG = "mse-p19"
STUDY = "LR004"
IDENTITIES = {
    "preflight": (900754, 900756),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910020, 910036),   # the LR004 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900756, 900758)
PROBE_BLOCKS = (900750, 900754)       # engineering probe P19 (tag mse-p19), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = L3.MESSAGES, L3.PARENTS, L3.NCASE
SIDE, SIGMA, CHUNK = L3.SIDE, L3.SIGMA, L3.CHUNK
EPS, KR, SIGMA_R, KC = L3.EPS, L3.KR, L3.SIGMA_R, L3.KC
GAIN, STRENGTH0, ETA = L3.GAIN, L3.STRENGTH0, L3.ETA
BODIES = L3.BODIES
PATTERNS = L3.PATTERNS
THETAS = (0.0, 1.0)
RATES = (0.0, 0.001, 0.003, 0.01, 0.03)
REPAIRS = ("record+parity", "body", "site", "pair", "vote", "anchors4", "anchors16")
SOURCES = dict(L3.SOURCES, pair=6, vote=7, anchors=8)     # LR003's ids kept, so lr003.sim.gates applies unchanged
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
        return "anchors" if s.startswith("anchors") else s

    @property
    def density(self):
        """Anchors: one cell in `density`; 0 for every other teacher."""
        return int(self.repair[7:]) if self.repair.startswith("anchors") else 0

    @property
    def two(self):
        """Whether the branch keeps a second relational record."""
        return self.source in ("pair", "vote")


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
                    *(lane / "lr002").glob("*.py"), *(lane / "lr003").glob("*.py"), *(lane / "lr004").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m lr004.design  ->  lr004/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "lr004" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
