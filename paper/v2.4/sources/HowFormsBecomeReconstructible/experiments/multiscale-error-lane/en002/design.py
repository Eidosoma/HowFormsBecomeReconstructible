"""EN002: the single source of truth for the runner, the reader and the checks.

The energy budget on the self-organising body: does starvation keep the spacing and lose the placement?
DL001's bodies (dl001/design.py, unchanged: the open double well dw, and lateral inhibition tuned to period 8, li2
weak and li4 strong) run a starvation phase of STARVE updates on a reduced budget, then a recovery phase of
RECOVER updates on the full budget, as in EN001. A budget factor phi multiplies the paid rates:
    body drift      the double well, coupling, theta and the inhibitor (paid in accountings B and C)
    correction      the body reading its held record (always paid)
and decides the noise: thermal (B: unchanged by the budget) or activity-driven (C: variance scaled with the paid
rate, an exact slowing of time in the continuum limit). The held record is DL001's protected copy of the acquired
record, read at gain GAIN; with no record the gain is 0. Records and bodies are acquired as in DL001 (msegrid's
acquisition, conserved body, sigma 0.1) under EN002's tag; after acquisition theta is kept (x1) or removed (x0).
Panels, on the open body at sigma = SIGMA:
  G  the global budget: S4 (native to li) and F0 (native to dw), no record or the held record;
  W  wounds under starvation: S4 with an 8 x 8 body wound (reset to newborn noise, or flipped) at t = 1.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from dl001 import design as DL

TAG = "mse-en002"
PROBE_TAG = "mse-p15"
STUDY = "EN002"
IDENTITIES = {
    "preflight": (900922, 900924),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910920, 910936),   # the EN002 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900924, 900926)
PROBE_BLOCKS = (900884, 900888)       # engineering probe P15 (tag mse-p15), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


# Unchanged from DL001 (imported, so the studies cannot drift apart)
MESSAGES, PARENTS, NCASE = DL.MESSAGES, DL.PARENTS, DL.NCASE
SETTLE, TEACH, AMPLITUDE, RELEASE, SIGMA_ACQ, KILL_SD = DL.SETTLE, DL.TEACH, DL.AMPLITUDE, DL.RELEASE, DL.SIGMA_ACQ, DL.KILL_SD
SIDE, QMAX, CHUNK = DL.SIDE, DL.QMAX, DL.CHUNK
BODIES = {k: DL.BODIES[k] for k in DL.BODIES_MAIN}

# New in EN002
SIGMA = 0.1
THETAS = (0.0, 1.0)
PATTERNS = ("S4", "F0")
STARVE, RECOVER = 2000, 1000
WINDOW = STARVE + RECOVER
PHIS = (0.5, 0.25, 0.1)
GAIN = 0.2
WOUND = 8
SNAPS_G = (500, 2000, 3000)
SNAPS_W = (250, 500, 2000, 3000)


@dataclass(frozen=True)
class Budget:
    name: str
    acct: str = "base"        # base | B (every drift paid, thermal noise) | C (every drift paid, activity noise)
    phi: float = 1.0


@dataclass(frozen=True)
class Cond:
    name: str
    budget: Budget
    record: str = "none"      # none | held (the acquired record, read at GAIN; the correction is paid)
    wound: str = "sham"       # sham | reset | flip  (body wounds at t = 1)
    size: int = 0


BUDGETS = (Budget("base"), *(Budget(f"{a}{phi:g}", a, phi) for a in ("B", "C") for phi in PHIS))
COND_G = tuple(Cond(f"{b.name}/{rec}", b, rec) for b in BUDGETS for rec in ("none", "held"))
COND_W = tuple(Cond(f"{b.name}/{rec}/{w}{WOUND}", b, rec, w, WOUND) for b in BUDGETS for rec in ("none", "held")
               for w in ("reset", "flip"))


def unit_name(pattern, theta):
    return f"{pattern}_t{theta:g}"


def parse_unit(name):
    pattern, t = name.split("_")
    return pattern, float(t[1:])


PANELS = {
    "G": {"title": "the global budget: S4 and F0, no record or the held record", "conds": COND_G, "snaps": SNAPS_G,
          "units": tuple(unit_name(p, t) for p in PATTERNS for t in THETAS)},
    "W": {"title": "8 x 8 body wounds in S4 under starvation, reset or flipped, no record or the held record",
          "conds": COND_W, "snaps": SNAPS_W, "units": tuple(unit_name("S4", t) for t in THETAS)},
}


def tasks():
    return [(p, u) for p, v in PANELS.items() for u in v["units"]]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "settle": SETTLE, "teach": TEACH, "amplitude": AMPLITUDE, "release": RELEASE, "sigma_acq": SIGMA_ACQ,
            "kill_sd": KILL_SD, "side": SIDE, "qmax": QMAX, "chunk": CHUNK,
            "bodies": {k: list(v) for k, v in BODIES.items()}, "sigma": SIGMA, "thetas": THETAS, "patterns": PATTERNS,
            "phases": {"starve": STARVE, "recover": RECOVER}, "phis": PHIS, "gain": GAIN, "wound": WOUND,
            "budgets": [asdict(b) for b in BUDGETS],
            "panels": {p: {"title": v["title"], "conds": [asdict(c) for c in v["conds"]], "snaps": v["snaps"],
                           "units": v["units"]} for p, v in PANELS.items()}}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "en002").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m en002.design  ->  en002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "en002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
