"""FN001 (DRAFT, not frozen): the single source of truth for the runner, the reader and the checks.

Restored function and retained capacity. LR004's tissue (DL002's preparation and DL001's bodies, unchanged; the
relational record's bonds, without the coarse code, under LR001's bond-sign noise; the body reads the record at gain
0.2; the bonds relearned at eta 0.01 by lr004.sim.relations, unchanged), injured by killing cells: an 8 x 8 square
whose cells die with their body state, their record values and every bond they touch, and are replaced by newborns.
In the vote's branches the wound takes both records (a wound is shared damage).

Each branch follows one injury schedule, all from the same acquired tissue and the same noise streams:
  W12   a first wound after update T_W1 and a second wound at the same place after update T_W2 (re-injury);
  W12x  the same first wound, and a second wound elsewhere (shifted by half the sheet in both directions);
  W2    no first wound, the second wound only: naive tissue of the same age (W12's reference);
  W2x   no first wound, a wound at W12x's second place only (W12x's reference: the same place, naive tissue).
Retained capacity is read at the same place: W12 - W2 (a re-injured scar) and W12x - W2x (a past wound elsewhere).
Endpoints at every read: appearance (the body's and the record's agreement with the template, overall and in the
current wound) and function, read without the template's registration:
  intact   1 if, for each sign, the body has as many large connected domains (at least MINCOMP cells, periodic,
           4-neighbour) as the template: no stripe broken, no barrier breached, no domain lost;
  defects  the graded version: |large + domains - the template's| + |large - domains - the template's| + islands;
  islands  the number of small domains (fewer than MINCOMP cells) of either sign;
  walls    the length of the body's walls (unlike nearest-neighbour pairs) over the template's, minus 1.
The read at T_W1 (before the first wound) is every branch's pre-wound baseline.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from dl001 import design as DL
from lr004 import design as L4

TAG = "mse-fn001"
PROBE_TAG = "mse-p21"
STUDY = "FN001"
IDENTITIES = {
    "preflight": (900774, 900776),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910060, 910076),   # the FN001 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900776, 900778)
PROBE_BLOCKS = (900770, 900774)       # engineering probe P21 (tag mse-p21), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = L4.MESSAGES, L4.PARENTS, L4.NCASE
SIDE, SIGMA, CHUNK = L4.SIDE, L4.SIGMA, L4.CHUNK
EPS, KR, SIGMA_R, KC = L4.EPS, L4.KR, L4.SIGMA_R, L4.KC
GAIN, STRENGTH0, ETA = L4.GAIN, L4.STRENGTH0, L4.ETA
BODIES = L4.BODIES
PATTERNS = L4.PATTERNS
SOURCES = L4.SOURCES
THETAS = (0.0, 1.0)
RATES = (0.0, 0.001, 0.003)
REPAIRS = ("record+parity", "body", "site", "vote")
SCHEDULES = ("W12", "W12x", "W2", "W2x")
WOUND, KILL_SD = 8, 0.2                # side of the square wound; newborn body values ~ KILL_SD x N(0, 1)
T_W1, T_W2, WINDOW = 1000, 2000, 3000  # wounds applied after the reads of updates T_W1 and T_W2
READS = (1000, 1250, 1500, 2000, 2250, 2500, 3000)
MINCOMP = 8                            # a domain of fewer cells is an island (a defect)
ENDPOINTS = ("sign", "r_sign", "patch", "r_patch", "intact", "defects", "islands", "walls", "bond_err")


@dataclass(frozen=True)
class Cond:
    rate: float
    repair: str
    schedule: str

    @property
    def name(self):
        return f"{self.rate:g}/{self.repair}/{self.schedule}"

    @property
    def teacher(self):
        """LR004's condition for the relearning (lr004.sim.params and lr004.sim.relations, unchanged)."""
        return L4.Cond(self.rate, self.repair)

    @property
    def wounds(self):
        """The wounds this branch receives, as (after update, which mask): 'a' the first mask, 'b' the shifted one."""
        return {"W12": ((T_W1, "a"), (T_W2, "a")), "W12x": ((T_W1, "a"), (T_W2, "b")), "W2": ((T_W2, "a"),),
                "W2x": ((T_W2, "b"),)}[self.schedule]


CONDS = tuple(Cond(r, rep, s) for r in RATES for rep in REPAIRS for s in SCHEDULES)


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
            "relations": "lr004.sim.relations and lr004.sim.params (unchanged)",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "gain": GAIN, "strength0": STRENGTH0, "eta": ETA,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS,
            "rates": RATES, "repairs": REPAIRS, "schedules": SCHEDULES, "wound": WOUND, "kill_sd": KILL_SD,
            "t_w1": T_W1, "t_w2": T_W2, "window": WINDOW, "reads": READS, "mincomp": MINCOMP, "endpoints": ENDPOINTS,
            "conds": [c.name for c in CONDS], "units": UNITS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "dl002").glob("*.py"), *(lane / "lr001").glob("*.py"),
                    *(lane / "lr002").glob("*.py"), *(lane / "lr003").glob("*.py"), *(lane / "lr004").glob("*.py"),
                    *(lane / "fn001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m fn001.design  ->  fn001/frozen/design.json (at the freeze only)
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "fn001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
