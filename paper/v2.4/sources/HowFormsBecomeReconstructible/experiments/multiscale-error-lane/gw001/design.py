"""GW001: the single source of truth for the runner, the reader and the checks.

Geometry and wound kind on a sheet of any side, after MODEL_LIMITS_AND_EXPANSION.md (sections 2.1-2.5, E1, E2).
The engine is msegrid/ (side-agnostic, equal to mse/, br001/ and br002/ bit for bit at side 16).
Panel R, the record alone (writing off, so the record never reads the body and needs no regime): which record
designs repair which wounds - flipped (an inverted, stable wrong state), reset (record 0, the unstable point) or
killed (reset, and the bonds between dead cells lost) - placed at declared distances from the pattern's walls,
on sheets of side 16, 32 and 64, and how fast. Panel B, the body: do the body's physics (conserved or open) and
the sheet's size change what the body keeps when body and record are wounded together.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from br001 import design as B1

TAG = "mse-gw001"
STUDY = "GW001"
IDENTITIES = {
    "preflight": (900860, 900862),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910500, 910516),   # the GW001 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900862, 900864)
PROBE_BLOCKS = (900852, 900860)       # engineering probe P10, before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = B1.MESSAGES, B1.PARENTS, B1.NCASE
SETTLE, TEACH, AMPLITUDE, RELEASE = B1.SETTLE, B1.TEACH, B1.AMPLITUDE, B1.RELEASE
EPS, SIGMA_R, KC = B1.EPS, B1.SIGMA_R, B1.KC
KILL_SD = 0.2
SIGMA_ACQ = 0.1                        # panel R: records are acquired in the conserved body at sigma 0.1
WINDOW_R, EVERY_R, READS_R = 8000, 250, (2000, 4000, 8000)
WINDOW_B, EVERY_B = 4000, 500
COMMIT = 0.2                           # 'committed kept': right sign and |r| > COMMIT


@dataclass(frozen=True)
class Cond:
    name: str
    wound: str = "sham"       # sham | flip | reset | kill
    size: int = 0
    place: str = "random"     # random | dK | mid | cross (F0 and S8 only for the last three)


@dataclass(frozen=True)
class Arm:
    name: str
    eps: float = 0.0
    kr: float = 1.0
    kc: float = 0.0
    rel: bool = False
    clamp: bool = False
    privileged: bool = False


def _wounds(spec, kinds=("flip", "reset")):
    return tuple(Cond(f"{w[0]}{s}-{pl}", w, s, pl) for w in kinds for s, pl in spec)


def geometry(family, side):
    return f"{family}_{side}"


def parse_geometry(name):
    family, side = name.split("_")
    return family, int(side)


GEOMETRIES = {
    geometry("F0", 16): (Cond("sham"), *_wounds(((4, "d0"), (4, "d1"), (4, "mid"), (4, "cross"), (8, "d0"), (8, "cross")))),
    geometry("F0", 32): (Cond("sham"), *_wounds(((4, "d0"), (4, "d2"), (4, "mid"), (4, "cross"), (8, "d0"), (8, "d2"),
                                                 (8, "mid"), (8, "cross"), (12, "d0"), (12, "mid"), (12, "cross"),
                                                 (6, "mid"), (10, "mid"))),
                         *_wounds(((8, "mid"), (12, "mid")), kinds=("kill",))),
    geometry("F0", 64): (Cond("sham"), *_wounds(((4, "mid"), (8, "mid"), (12, "mid"), (16, "mid"), (8, "d0"), (8, "cross"),
                                                 (16, "d0"), (16, "cross")))),
    geometry("S8", 32): (Cond("sham"), *_wounds(((4, "d0"), (4, "d1"), (4, "mid"), (4, "cross"), (8, "d0"), (8, "cross")))),
    **{geometry(f, s): (Cond("sham"), *_wounds(((4, "random"), (8, "random"))))
       for f, s in (("BL", 16), ("BL", 32), ("BLx2", 32), ("BLx4", 64))},
}
ARMS_R = (Arm("self", eps=EPS), Arm("self_kr2", eps=EPS, kr=2.0), Arm("code", kc=KC), Arm("multi", eps=EPS, kc=KC),
          Arm("rel", eps=EPS, rel=True), Arm("rel+code", eps=EPS, kc=KC, rel=True))

REGIMES_B = tuple(f"F0_{s}_s0.1_{b}" for s in (16, 32) for b in ("c", "o"))
COND_B = (Cond("sham"), *_wounds(((4, "mid"), (8, "d0"), (8, "cross"))))
ARMS_B = (Arm("static"), Arm("multi", eps=EPS, kc=KC), Arm("rel+code", eps=EPS, kc=KC, rel=True),
          Arm("protected", clamp=True, privileged=True))


def parse_regime(name):
    family, side, s, body = name.split("_")
    return family, int(side), float(s[1:]), body


PANELS = {
    "R": {"title": "the record alone: wound kind, placement and sheet size", "units": tuple(GEOMETRIES),
          "arms": ARMS_R, "window": WINDOW_R, "every": EVERY_R},
    "B": {"title": "the body: conserved or open, side 16 or 32, body and record wounded together", "units": REGIMES_B,
          "arms": ARMS_B, "window": WINDOW_B, "every": EVERY_B},
}
ARM = {p: {a.name: a for a in v["arms"]} for p, v in PANELS.items()}


def conditions(panel, unit):
    return GEOMETRIES[unit] if panel == "R" else COND_B


def tasks():
    return [(p, u) for p, v in PANELS.items() for u in v["units"]]


MARGIN = 0.02
CONTRASTS = (("R", "self_kr2", "self"), ("R", "multi", "self"), ("R", "rel", "self"), ("R", "rel+code", "multi"),
             ("B", "multi", "static"), ("B", "rel+code", "multi"), ("B", "rel+code", "protected"))


def design_dict():
    import numpy as np
    from msegrid.core import base
    th = hashlib.sha256(b"".join(np.ascontiguousarray(base(f, k, s)).tobytes()
                                 for f, s in (("F0", 16), ("F0", 32), ("F0", 64), ("S8", 32)) for k in MESSAGES)).hexdigest()
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
            "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS, "settle": SETTLE, "teach": TEACH,
            "amplitude": AMPLITUDE, "release": RELEASE, "eps": EPS, "sigma_r": SIGMA_R, "kc": KC, "kill_sd": KILL_SD,
            "sigma_acq": SIGMA_ACQ, "window_r": WINDOW_R, "every_r": EVERY_R, "reads_r": READS_R, "window_b": WINDOW_B,
            "every_b": EVERY_B, "commit": COMMIT, "fixed_template_sha256": th,
            "geometries": {g: [asdict(c) for c in cs] for g, cs in GEOMETRIES.items()},
            "arms_r": [asdict(a) for a in ARMS_R], "regimes_b": REGIMES_B, "conditions_b": [asdict(c) for c in COND_B],
            "arms_b": [asdict(a) for a in ARMS_B], "margin": MARGIN, "contrasts": CONTRASTS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me002").glob("*.py"), *(lane / "br001").glob("*.py"),
                    *(lane / "br002").glob("*.py"), *(lane / "msegrid").glob("*.py"), *(lane / "gw001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m gw001.design  ->  gw001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "gw001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
