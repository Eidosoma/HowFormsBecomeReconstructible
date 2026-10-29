"""DL003: the single source of truth for the runner, the reader and the checks.

Can a boundary register a self-organised pattern? DL001's double well (dw) and its strong period-8 lateral-inhibition
body (li4) (dl001.sim.body, unchanged), on a 32-site sheet of stripes of period 8 (S4, four kinds: two orientations,
two signs), read positional information at 64 cells (1/16 of the sheet), each holding the acquired record at gain 1.0:
  scatter  64 random cells (DL002's sparse anchors, at an exact count);
  par      a boundary along the stripes: two adjacent lines straddling a wall of the pattern (a random wall);
  perp     a boundary across the stripes: two adjacent lines at a random offset;
  cluster  one 8 x 8 block at a random position (an organiser);
with the references none and full (the held record at every cell, gain 0.2, DL001's). Panels:
  H  holding the acquired pattern;
  B  building it from newborn noise, with the whole sheet active from the start or with activation spreading from a
     boundary at one line per `front` updates (cells ahead of the front held at 0, starting from their newborn values
     when the front reaches them); "none" arms with a front spread from a boundary's position without anchors.
The environmental field theta at x0, x0.25, x0.5 and x1 (per-tissue spread 0.15-0.30 at x1); sigma 0.1; records and
bodies acquired as in DL001 and DL002 (msegrid.acquire), shared by every body and arm of a case.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from dl001 import design as DL

TAG = "mse-dl003"
STUDY = "DL003"
IDENTITIES = {
    "preflight": (900724, 900726),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910940, 910956),   # the DL003 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900726, 900728)
PROBE_BLOCKS = (900720, 900724)       # engineering probe P16 (tag mse-p16), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = DL.MESSAGES, DL.PARENTS, DL.NCASE
SETTLE, TEACH, AMPLITUDE, RELEASE, SIGMA_ACQ = DL.SETTLE, DL.TEACH, DL.AMPLITUDE, DL.RELEASE, DL.SIGMA_ACQ
SIDE, SIGMA, CHUNK = 32, 0.1, 250
N_ANCHOR, G_ANCHOR, G_FULL = 64, 1.0, 0.2
GEOMETRIES = ("scatter", "par", "perp", "cluster")
BODIES = ("dw", "li4")
THETAS = (0.0, 0.25, 0.5, 1.0)
WINDOW, SNAPS = 4000, (1000, 2000, 4000)


@dataclass(frozen=True)
class Arm:
    name: str
    geo: str             # none | scatter | par | perp | cluster | full
    front: int = 0       # updates per line of an activation front from a boundary (0: the whole sheet from the start)
    origin: str = ""     # the boundary a front spreads from when the arm has none of its own (geo none)

    @property
    def home(self):
        """The distance map the arm's profile is read on: its boundary, its front's origin, or its cluster."""
        return self.origin or (self.geo if self.geo in ("par", "perp", "cluster") else "")


ARMS_H = (Arm("none", "none"), Arm("scatter", "scatter"), Arm("par", "par"), Arm("perp", "perp"),
          Arm("cluster", "cluster"), Arm("full", "full"))
ARMS_B = ARMS_H + (Arm("par/f25", "par", 25), Arm("par/f50", "par", 50), Arm("par/f100", "par", 100),
                   Arm("perp/f25", "perp", 25), Arm("perp/f100", "perp", 100), Arm("perp/f200", "perp", 200),
                   Arm("none/perp-f100", "none", 100, "perp"))
DMAX = {"par": 15, "perp": 15, "cluster": 12}     # the largest distance on each map (32-site ring; 8 x 8 cluster)
FAR, NEAR, BEYOND = (12, 16), (0, 2), 8          # distance windows: the far side, the boundary's own lines, >= 8


def unit_name(theta):
    return f"S4_t{theta:g}"


def parse_unit(name):
    return float(name.split("_t")[1])


PANELS = {
    "H": {"title": "holding the acquired stripes", "arms": ARMS_H, "units": tuple(unit_name(t) for t in THETAS)},
    "B": {"title": "building the stripes from newborn noise", "arms": ARMS_B, "units": tuple(unit_name(t) for t in THETAS)},
}


def tasks():
    return [(p, u) for p, v in PANELS.items() for u in v["units"]]


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
            "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS, "settle": SETTLE, "teach": TEACH,
            "amplitude": AMPLITUDE, "release": RELEASE, "sigma_acq": SIGMA_ACQ, "side": SIDE, "sigma": SIGMA,
            "chunk": CHUNK, "n_anchor": N_ANCHOR, "g_anchor": G_ANCHOR, "g_full": G_FULL, "geometries": GEOMETRIES,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "thetas": THETAS, "window": WINDOW, "snaps": SNAPS,
            "dmax": DMAX, "far": FAR, "near": NEAR, "beyond": BEYOND,
            "panels": {p: {"title": v["title"], "arms": [asdict(a) for a in v["arms"]], "units": v["units"]}
                       for p, v in PANELS.items()}}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "dl003").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m dl003.design  ->  dl003/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "dl003" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
