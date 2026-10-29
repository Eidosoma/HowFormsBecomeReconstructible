"""SC002: coupling set by the cells.

BE001's tissue, detector and commitment (LR005's tissue, events, action and scoring at read gain 0.2; anchors at a
quarter of the sites inject KAPPA * cue * the record's confident sign; g_l v_i + sum_j g_ij (v_i - v_j) = I_i at steady
state each update; a confident cell with v < -THETA commits through a slow state), on cellpop's vacancy lattice. Gap
junctions exist only between occupied neighbours (cellpop's contacts), and the population sets their conductance:
  maturing junctions   g_ij = lam^2 (1 - exp(-age_ij / tau_m))
  instant junctions    g_ij = lam^2
where age_ij counts the updates since the contact formed. A contact formed by a division starts at age 0 (no coupling),
and a contact is lost with either of its cells. Empty sites carry no current and no voltage (no contacts, no anchor
current; the leak alone holds them at 0).
Population (declared choices):
  turnover    every cell dies with probability mu per update; a cell with an empty neighbour divides into it with
              probability P_DIV per update (cellpop.core.divide); daughters copy their parent's body value, moving average
              and record value (SC001's inheritance), start uncommitted, and form untrained contacts (sign 0, strength 0);
  positional cue  anchors are sites (a quarter, LR005's draw): a daughter at an anchored site reads its site's cue;
  stationary start  at t = 0 the tissue has turned over at mu for ever: each cell's age is the floor of a standard
              exponential (one per site and case, the same for every mu, so regimes are paired) divided by mu, and a
              contact's age is its younger cell's; with mu = 0 every contact is mature (age infinite, m = 1).
Panels:
  T  steady turnover at mu in MUS with BE001's events at t = 0: none; scattered corruption of a quarter of the anchors
     (cue); a legitimate change of a 4 x 4 or 8 x 8 patch (change);
  W  a wound with no turnover: an 8 x 8 patch emptied at t = 0 (values 0, contacts lost, anchors kept) and regrown by
     division from its rim at P_REGROW per update (daughters inherit), with or without scattered cue corruption.
Arms: cue (LR004's arbiter, no detector); instant junctions at lam 1.5 and 3 (BE001's matched and long couplings,
threshold 0.1); maturing junctions at lam 3 with tau_m 300 and 1000. With every site occupied, no events and every
contact mature, an instant arm at lam is be001's bio-lam bit for bit and a maturing arm equals inst-3 (checks Q3, Q5).
Patterns S4 (stripes, many walls) and F0 (domains, few walls) in quiet tissue.
"""
from __future__ import annotations

import hashlib
import json

from be001 import design as B1
from dl001 import design as DL

TAG = "mse-sc002"
PROBE_TAG = "mse-p25"
STUDY = "SC002"
PROBE_BLOCKS = (900650, 900654)
IDENTITIES = {"preflight": (900654, 900656), "development": (910160, 910176)}
DEBUG_BLOCKS = (900656, 900658)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B1.SIDE, B1.SIGMA, B1.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B1.EPS, B1.KR, B1.SIGMA_R, B1.KC, B1.STRENGTH0, B1.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE, GAIN = B1.KILL_SD, B1.DENSITY, B1.VMIN, B1.PULL, B1.RATE, B1.GAIN
KAPPA, G_LEAK, TAU, S_MIN, CG_TOL, CG_MAXIT = B1.KAPPA, B1.G_LEAK, B1.TAU, B1.S_MIN, B1.CG_TOL, B1.CG_MAXIT
MESSAGES, PARENTS, NCASE = B1.MESSAGES, B1.PARENTS, B1.NCASE
BODIES = B1.BODIES
PATTERNS, THETAS = ("S4", "F0"), (0.0,)
THETA = 0.1                               # BE001's trigger threshold

JUNCTIONS = {"inst-1.5": {"lam": 1.5, "tau_m": 0.0}, "inst-3": {"lam": 3.0, "tau_m": 0.0},
             "mat-300": {"lam": 3.0, "tau_m": 300.0}, "mat-1000": {"lam": 3.0, "tau_m": 1000.0}}
ARMS = ("cue", *JUNCTIONS)

MUS = (0.0, 2.5e-4, 1e-3)                 # deaths per cell and update
P_DIV, P_REGROW = 0.1, 0.04               # refilling under turnover; regrowth of the wound (SC001's)
SITUATIONS_T = (("none", 8), ("cue", 8), ("change", 4), ("change", 8))
SITUATIONS_W = (("regrow", 8), ("regrow+cue", 8))
RUNS = tuple(("T", mu, s, z) for mu in MUS for s, z in SITUATIONS_T) + tuple(("W", 0.0, s, z) for s, z in SITUATIONS_W)
WINDOW, READS, TRACE = 4000, (250, 1000, 2000, 4000), 100
TRACE_READS = tuple(range(TRACE, WINDOW + 1, TRACE))


def run_name(panel, mu, situation, size):
    return f"{situation}{size}@{mu:g}"


RUNNAMES = tuple(run_name(*x) for x in RUNS)


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
    """One task per (unit, body): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "lr002.sim.prepare = dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "be001": "events (be001.sim.event), anchors, arbiter, currents, trigger, commitment, pull and learning as "
                     "be001.sim, unchanged in arithmetic; cellpop's contacts, deaths and divisions",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN,
            "cg_tol": CG_TOL, "cg_maxit": CG_MAXIT, "theta": THETA, "junctions": JUNCTIONS, "arms": ARMS,
            "mus": MUS, "p_div": P_DIV, "p_regrow": P_REGROW, "situations_t": SITUATIONS_T,
            "situations_w": SITUATIONS_W, "runs": RUNS, "bodies": {b: list(DL.BODIES[b]) for b in BODIES},
            "patterns": PATTERNS, "thetas": THETAS, "units": UNITS, "window": WINDOW, "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "cellpop", "sc002")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sc002.design  ->  sc002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sc002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
