"""SC001: scale that emerges from a growing, dying and moving cell population.

The engine is cellpop (a vacancy lattice: cells divide into empty neighbours, die, exchange places; contacts are the
bonds between occupied neighbours; empty sites hold 0, as DL003's inactive cells did), with DL001's bodies and the
relational record of LR001-LR005 on the occupied sites. Two panels on a 32-site periodic sheet:

  G  growth from a boundary (DL003's question with real growth). Stripes of period 8 (S4); the acquired record held at
     the boundary's 64 cells (two lines, gain 1.0), which are also the seed: every arm starts from those two lines of
     newborn cells, the rest of the sheet empty. Arms:
       front/s   DL003's prescribed front: one line activated every s updates, with newborn values (the reference);
       grow/s    real growth: margin cells divide into empty neighbours at p = 1/s per update; daughters copy their
                 parent's body value and moving average;
       nb/s      the same divisions (the same geometry, paired), daughters starting from newborn values;
       smooth/s  growth by division at the same mean speed with a flat margin: the cells of each line of growth are
                 added one at a time, in a random order drawn per line, within that line's s updates, each a daughter
                 of its neighbour in the previous line (copying it), so the margin is never more than one line uneven;
       turn/s    grow/s plus turnover: deaths and neighbour exchanges of non-seed cells (refilled by division);
       none/s    grow/s with no boundary record (the seed lines are there but read nothing);
       diffL/s   grow/s with the boundary's record spread as a diffusing signal over the contact graph (decay length
                 L sites), read by every cell as a field, instead of read at the boundary's cells.
     Geometries par (a boundary along the stripes: new stripes are added parallel to the margin) and perp (across the
     stripes: stripes lengthen away from it). Quiet tissue (theta x0) only.
  R  regrowth of a killed patch. The acquired pattern (S4 or F0) and its relational record (values and bonds), read by
     the body at gain 0.2, under bond noise; at t = 0 an 8 x 8 patch:
       none       no event;
       reset      killed in place (FN001's kill with untrained contacts): newborn body values, record 0;
       regrow     emptied, then refilled by division from its rim (p = 0.04 or 0.01 per update); daughters copy the
                  parent's body value, moving average and record value;
       regrow-nb  emptied and refilled by the same divisions, daughters with newborn values and record 0;
     each with the record relearning from itself (record+parity) or from the body (body).

Declared choices: empty sites hold 0 (DL003's inactive cells; they pull margin cells toward 0 through the coupling, a
free-boundary choice kept for the equality with DL003); contacts formed by a division or touching a killed cell are
untrained (sign 0, strength 0; FN001 gave them random signs at strength 0); the turnover arm is descriptive only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from dl001 import design as DL
from lr004 import design as L4

TAG = "mse-sc001"
PROBE_TAG = "mse-p22"
STUDY = "SC001"
IDENTITIES = {"preflight": (900784, 900786), "development": (910080, 910096)}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900786, 900788)
PROBE_BLOCKS = (900780, 900784)


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = DL.MESSAGES, DL.PARENTS, DL.NCASE
SETTLE, TEACH, AMPLITUDE, RELEASE, SIGMA_ACQ = DL.SETTLE, DL.TEACH, DL.AMPLITUDE, DL.RELEASE, DL.SIGMA_ACQ
SIDE, SIGMA, CHUNK, KILL_SD = 32, 0.1, 250, DL.KILL_SD
EPS, KR, SIGMA_R, KC, GAIN, STRENGTH0, ETA = L4.EPS, L4.KR, L4.SIGMA_R, L4.KC, L4.GAIN, L4.STRENGTH0, L4.ETA
BODIES = ("dw", "li4")
WINDOW, SNAPS, TRACE = 4000, (1000, 2000, 4000), 100

# panel G
G_ANCHOR = 1.0
GEOMS = ("perp", "par")
THETAS_G = (0.0,)
TURN = 0.001                      # turnover: deaths and exchanges per cell and update
KAPPA, G_SIG = 0.2, 0.25
DMAX, FAR, NEAR = 15, (12, 16), (0, 2)


@dataclass(frozen=True)
class GArm:
    mode: str                     # front | grow | nb | turn | none | diff
    speed: int                    # updates per line (front) or 1 / division probability (the others)
    lam: float = 0.0              # diff: the signal's decay length along a line of cells

    @property
    def name(self):
        return f"{self.mode}{self.lam:g}/{self.speed}" if self.mode == "diff" else f"{self.mode}/{self.speed}"


ARMS_G = (GArm("front", 25), GArm("front", 100), GArm("front", 200), GArm("grow", 25), GArm("grow", 100),
          GArm("grow", 200), GArm("nb", 100), GArm("smooth", 100), GArm("turn", 100), GArm("none", 100),
          GArm("diff", 100, 1.5), GArm("diff", 100, 6.0))

# panel R
PATTERNS_R = ("S4", "F0")
MODES = ("none", "reset", "regrow", "regrow-nb")
TEACHERS = ("record+parity", "body")
RATES = (0.0, 0.001)
PATCH, REGROW = 8, (0.04, 0.01)        # regrowth: division probability per update at the patch's rim
READS_R = (250, 1000, 2000, 4000)


@dataclass(frozen=True)
class RCond:
    rate: float
    teacher: str
    mode: str
    speed: float = 0.0                  # regrow modes: the division probability

    @property
    def name(self):
        return f"{self.rate:g}/{self.teacher}/{self.mode}" + (f"@{self.speed:g}" if self.speed else "")


CONDS_R = tuple(RCond(r, t, m, sp) for r in RATES for t in TEACHERS
                for m, sp in [("none", 0.0), ("reset", 0.0)] + [(m, sp) for sp in REGROW for m in ("regrow", "regrow-nb")])


def unit_name(pattern, theta):
    return f"{pattern}_t{theta:g}"


def parse_unit(name):
    pattern, t = name.split("_")
    return pattern, float(t[1:])


UNITS = {"G": tuple(unit_name("S4", t) for t in THETAS_G), "R": tuple(unit_name(p, 0.0) for p in PATTERNS_R)}


def tasks():
    return [(p, u) for p in ("G", "R") for u in UNITS[p]]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "settle": SETTLE, "teach": TEACH, "amplitude": AMPLITUDE, "release": RELEASE, "sigma_acq": SIGMA_ACQ,
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "kill_sd": KILL_SD, "eps": EPS, "kr": KR,
            "sigma_r": SIGMA_R, "kc": KC, "gain": GAIN, "strength0": STRENGTH0, "eta": ETA,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "window": WINDOW, "snaps": SNAPS, "trace": TRACE,
            "g_anchor": G_ANCHOR, "geoms": GEOMS, "thetas_g": THETAS_G, "turn": TURN, "kappa": KAPPA,
            "g_sig": G_SIG, "dmax": DMAX, "far": FAR, "near": NEAR,
            "arms_g": [asdict(a) for a in ARMS_G], "patterns_r": PATTERNS_R, "modes": MODES, "teachers": TEACHERS,
            "rates": RATES, "patch": PATCH, "regrow": REGROW, "reads_r": READS_R,
            "conds_r": [c.name for c in CONDS_R], "units": UNITS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl003", "lr001", "lr004", "fn001", "cellpop", "sc001")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sc001.design  ->  sc001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sc001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
