"""LR002: the single source of truth for the runner, the reader and the checks.

Body and record correcting each other. DL002's tissue (dl002.sim.prepare, unchanged: DL001's bodies, the acquired
record, the templates S4, LB and F0 on a 32-site sheet; dl001.sim.body, unchanged) with its relational record's bonds
under LR001's bond-sign noise: every bond's sign flips at rate p_b per update (one standard normal per site and update:
the right bond flips if z > cut, the lower bond if z < -cut; lr001.sim.cut_for). The body reads the relational record
at gain 0.2 (DL002's rel). The record of relations is kept alone, without the coarse code (as LR001's panel E), so
nothing positional holds the pattern. Repairs, per branch (parity: LR001's plaquette rule every update, flipping
every bond whose two plaquettes are both frustrated):
  none;
  record         Hebbian relearning of every bond from the record's co-activity r_i r_j / R*^2 at eta 0.01 (LR001's);
  record+parity  LR001's two layers;
  body           Hebbian relearning from the body's co-activity V_i V_j at eta 0.01: physics teaching the record;
  body+parity    body relearning and parity.
One update, in order: the body reads the record (dl001.sim.body); the bonds take their noise; the record steps through
its bonds (msegrid.record_step: eps 0.05, k_r 1, sigma_r 0.02, k_c 0); the bonds relearn; parity. The record never
reads the body's values; with body relearning its bonds do.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from dl001 import design as DL
from dl002 import design as D2

TAG = "mse-lr002"
PROBE_TAG = "mse-p17"
STUDY = "LR002"
IDENTITIES = {
    "preflight": (900734, 900736),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910960, 910976),   # the LR002 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900736, 900738)
PROBE_BLOCKS = (900730, 900734)       # engineering probe P17 (tag mse-p17), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = D2.MESSAGES, D2.PARENTS, D2.NCASE
SIDE, SIGMA, CHUNK = D2.SIDE, D2.SIGMA, D2.CHUNK
EPS, KR, SIGMA_R = D2.EPS, D2.KR, D2.SIGMA_R  # the relational record (BR001, BR002, DL002)
KC = 0.0                               # no coarse code: the record of relations alone
GAIN = 0.2                             # the body reads the record at DL002's rel gain
STRENGTH0 = 0.8                        # a taught bond's strength (LR001)
ETA = 0.01                             # Hebbian relearning rate (LR001)
BODIES = ("dw", "li4")
PATTERNS = ("S4", "LB", "F0")
THETAS = (0.0, 1.0)
RATES = (0.0, 0.001, 0.003, 0.01, 0.03)
REPAIRS = ("none", "record", "record+parity", "body", "body+parity")
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
    def learn(self):
        return self.repair.split("+")[0] if self.repair.split("+")[0] in ("record", "body") else ""


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
            "preparation": "dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "gain": GAIN, "strength0": STRENGTH0, "eta": ETA,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS,
            "rates": RATES, "repairs": REPAIRS, "conds": [c.name for c in CONDS], "units": UNITS,
            "window": WINDOW, "reads": READS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "dl002").glob("*.py"), *(lane / "lr001").glob("*.py"),
                    *(lane / "lr002").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m lr002.design  ->  lr002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "lr002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
