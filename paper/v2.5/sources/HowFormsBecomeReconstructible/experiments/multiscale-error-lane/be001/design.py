"""BE001: a bioelectric controller.

LR005's tissue, events, action and scoring, unchanged and imported, at read gain 0.2. The community rule's two abstract
parts are replaced by bioelectric mechanisms:
  detection   each anchored cell injects a current kappa * cue * (the record's confident sign): hyperpolarising where they
              agree, depolarising where they disagree; gap junctions (conductance lam^2, optionally voltage-gated) and a leak
              (1) integrate it, g_l v_i + sum_j g_ij (v_i - v_j) = I_i, solved at steady state each update (FFT when the
              junctions are uniform, conjugate gradients when gated, with the previous update's voltages setting the gates);
              a confident cell with v (plus channel noise) below -theta is triggered;
  commitment  a triggered cell sets a slow state to 1 and, if it was not already committed, stores the inverted record sign;
              otherwise the state decays by exp(-1/TAU) per update; a cell is committed while the state is >= exp(-1). A
              committed cell's stored sign is its trusted sign, and its record value is pulled toward it (LR005's action).
Arms: cue (LR004's anchors as arbiter), community-s / -c (LR005's window count and timer), and the bioelectric arms in BIO.
Situations: none, cue damage, memory damage and legitimate change on patches of side 4, 8 and 12, shared damage at 8.
"""
from __future__ import annotations

import hashlib
import json
import math

from dl001 import design as DL
from lr005 import design as L5

TAG = "mse-be001"
PROBE_TAG = "mse-p23"
STUDY = "BE001"
PROBE_BLOCKS = (900790, 900794)
IDENTITIES = {"preflight": (900794, 900796), "development": (910120, 910136)}
DEBUG_BLOCKS = (900796, 900798)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = L5.SIDE, L5.SIGMA, L5.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = L5.EPS, L5.KR, L5.SIGMA_R, L5.KC, L5.STRENGTH0, L5.ETA
KILL_SD, DENSITY, VMIN, RHO, MIN_ANCHORS, PULL = L5.KILL_SD, L5.DENSITY, L5.VMIN, L5.RHO, L5.MIN_ANCHORS, L5.PULL
COMMUNITY, RATE = L5.COMMUNITY, L5.RATE
BODIES, PATTERNS, THETAS = L5.BODIES, L5.PATTERNS, L5.THETAS
MESSAGES, PARENTS, NCASE = L5.MESSAGES, L5.PARENTS, L5.NCASE
GAIN = 0.2

KAPPA, G_LEAK = 4.0, 1.0                 # with a quarter of the cells anchored: v = 1 - 2f for a fraction f disagreeing
TAU = 300.0
S_MIN = math.exp(-1.0)
GATE = {"g_min": 0.1, "d0": 0.5, "w": 0.1}
CG_TOL, CG_MAXIT = 1e-11, 1000
BIO = {"bio-1": {"lam": 1.0, "theta": 0.1, "gate": False, "noise": 0.0},           # a ladder of coupling lengths
       "bio-1.5": {"lam": 1.5, "theta": 0.1, "gate": False, "noise": 0.0},         # matched to community-s's static zone
       "bio-2": {"lam": 2.0, "theta": 0.1, "gate": False, "noise": 0.0},
       "bio-3": {"lam": 3.0, "theta": 0.1, "gate": False, "noise": 0.0},
       "bio-2-gated": {"lam": 2.0, "theta": 0.1, "gate": True, "noise": 0.0},      # voltage-gated junctions
       "bio-2-noisy": {"lam": 2.0, "theta": 0.1, "gate": False, "noise": 0.2},     # channel noise
       "bio-1.5-cautious": {"lam": 1.5, "theta": 0.5, "gate": False, "noise": 0.0}}
ARMS = ("cue", "community-s", "community-c", *BIO)
SIZES = (4, 8, 12)
RUNS = (("none", 8), ("cue", 8), *(("memory", s) for s in SIZES), *(("change", s) for s in SIZES), ("shared", 8))
WINDOW, READS, TRACE = 4000, (250, 1000, 2000, 4000), 100
TRACE_READS = tuple(range(TRACE, WINDOW + 1, TRACE))


def run_name(situation, size):
    return f"{situation}{size}"


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


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
            "lr005": "events, cue and community rules, action and scoring from lr005.sim, unchanged",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "rho": RHO,
            "min_anchors": MIN_ANCHORS, "pull": PULL, "community": COMMUNITY, "rate": RATE, "gain": GAIN,
            "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN, "gate": GATE, "cg_tol": CG_TOL,
            "cg_maxit": CG_MAXIT, "bio": BIO, "arms": ARMS, "sizes": SIZES, "runs": RUNS,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "window": WINDOW, "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be001.design  ->  be001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
