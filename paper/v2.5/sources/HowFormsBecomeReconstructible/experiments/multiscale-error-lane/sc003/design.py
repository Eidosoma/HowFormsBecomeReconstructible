"""SC003: the birth check apart from the pooled coupling.

SC002's tissue unchanged in arithmetic (BE001's tissue, detector and commitment on cellpop's vacancy lattice; gap
junctions only between occupied neighbours, g_ij = lam^2 m(a_ij) with a_ij the updates since the contact formed;
turnover by death at mu and division into vacancies at P_DIV, daughters inheriting body, moving average and record,
starting uncommitted with untrained contacts; anchors at a quarter of the sites; a stationary start). SC002 found two
effects of young junctions: a pooled coupling (the bond effective-medium lam_eff of the population's conductances) and a
check at every birth (a newborn, uncoupled, reads only its own cue: below G* = (kappa - theta) / (1 + theta) an
anchored cell whose record disagrees with its cue triggers whatever its neighbours read). SC003 separates them by
intervention, in a 2 x 2 at each maturation time T (300, 1000) under steady turnover:
                          no birth check                  a birth check (ISO)
  pooled coupling lam 3   inst-3                          iso-3
  pooled coupling lam_eff emt-T                           iso-emt-T
and the population's own junctions, mat-T, against them:
  inst-3      instant junctions at lam 3 (no young junctions, no birth check)
  iso-3       instant junctions at lam 3, but a contact carries nothing in the first ISO updates after it forms: every
              newborn reads only its own cue on its first update, then joins at full strength (the birth check alone)
  emt-T       instant junctions at the bond effective-medium coupling of mat-T's stationary junctions at the run's mu
              (EMT_LAM; SC002's theory): the pooled coupling alone, with no young cell
  iso-emt-T   emt-T with iso-3's first-update isolation: the two scales SC002 named, and nothing else
  mat-T       SC002's maturing junctions, m = 1 - exp(-a / T): the population's own coupling
  cue         LR004's arbiter, no detector (turnover itself)
Probe-only laws (P26; not registered arms):
  gate-T      mat-T's junctions, but a cell does not trigger while its own junction conductance sum is below G*
  sister-T    mat-T's junctions, except that the contact between a daughter and its parent forms mature (cytoplasmic
              bridges, inherited plaques): a newborn's conductance is >= lam^2 > G* from birth
With no division every new switch is idle: iso arms equal their instant arms, gate-T and sister-T equal mat-T, and
SC002's arms (cue, inst-3, mat-T) equal sc002.sim.run's bit for bit in every situation (checks Q3, Q5).
Panels as SC002's: T (steady turnover at mu in MUS: none; scattered corruption of a quarter of the anchors; a legitimate
change of a 4 x 4 patch) and W (an 8 x 8 wound emptied at t = 0 and regrown by division from its rim, no turnover,
with or without scattered cue corruption; arms with an effective-medium coupling are not defined there and not run).
Patterns S4 and F0 in quiet tissue; bodies dw and li4.
"""
from __future__ import annotations

import hashlib
import json

from dl001 import design as DL
from sc002 import design as S2

TAG = "mse-sc003"
PROBE_TAG = "mse-p26"
STUDY = "SC003"
PROBE_BLOCKS = (900660, 900664)
IDENTITIES = {"preflight": (900664, 900666), "development": (910180, 910196)}
DEBUG_BLOCKS = (900666, 900668)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = S2.SIDE, S2.SIGMA, S2.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = S2.EPS, S2.KR, S2.SIGMA_R, S2.KC, S2.STRENGTH0, S2.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE, GAIN = S2.KILL_SD, S2.DENSITY, S2.VMIN, S2.PULL, S2.RATE, S2.GAIN
KAPPA, G_LEAK, TAU, S_MIN, CG_TOL, CG_MAXIT = S2.KAPPA, S2.G_LEAK, S2.TAU, S2.S_MIN, S2.CG_TOL, S2.CG_MAXIT
MESSAGES, PARENTS, NCASE = S2.MESSAGES, S2.PARENTS, S2.NCASE
BODIES = S2.BODIES
PATTERNS, THETAS = S2.PATTERNS, S2.THETAS
THETA = S2.THETA
G_STAR = (KAPPA - THETA) / (1.0 + THETA)  # sc002.theory.g_star(): 3.545

ISO = 1                                   # iso arms: a contact carries nothing at ages < ISO


def junction(lam, tau_m=0.0, iso=0, gate=False, sister=False, emt=0.0):
    return {"lam": lam, "tau_m": tau_m, "iso": iso, "gate": gate, "sister": sister, "emt": emt}


MUS = (2.5e-4, 1e-3)                      # deaths per cell and update
# the bond-EMT coupling of mat-T's stationary junctions (sc002.theory.lam_eff(mu, T), rounded to 4 decimals)
EMT_LAM = {(2.5e-4, 300.0): 2.7245, (2.5e-4, 1000.0): 2.2782, (1e-3, 300.0): 2.1837, (1e-3, 1000.0): 1.4788}
JUNCTIONS = {"inst-3": junction(3.0), "iso-3": junction(3.0, iso=ISO),
             "emt-300": junction(None, emt=300.0), "iso-emt-300": junction(None, iso=ISO, emt=300.0),
             "mat-300": junction(3.0, 300.0),
             "emt-1000": junction(None, emt=1000.0), "iso-emt-1000": junction(None, iso=ISO, emt=1000.0),
             "mat-1000": junction(3.0, 1000.0)}
PROBE_ONLY = {"gate-300": junction(3.0, 300.0, gate=True), "sister-300": junction(3.0, 300.0, sister=True)}
LAWS = {**JUNCTIONS, **PROBE_ONLY}
ARMS_T = ("cue", *JUNCTIONS)
ARMS_W = ("cue", "inst-3", "iso-3", "mat-300", "mat-1000")
ARMS = ARMS_T


def lam_of(arm, mu):
    """An arm's coupling length at turnover mu (emt arms: EMT_LAM at the run's mu)."""
    prm = LAWS[arm]
    return EMT_LAM[(mu, prm["emt"])] if prm["emt"] else prm["lam"]


P_DIV, P_REGROW = S2.P_DIV, S2.P_REGROW
SITUATIONS_T = (("none", 8), ("cue", 8), ("change", 4))
SITUATIONS_W = S2.SITUATIONS_W
RUNS = tuple(("T", mu, s, z) for mu in MUS for s, z in SITUATIONS_T) + tuple(("W", 0.0, s, z) for s, z in SITUATIONS_W)


def arms_of(run):
    return ARMS_T if run[0] == "T" else ARMS_W
WINDOW, READS, TRACE = S2.WINDOW, S2.READS, S2.TRACE
TRACE_READS = tuple(range(TRACE, WINDOW + 1, TRACE))
AGE_BINS = (0, 1, 32, 105)                # new commitments counted by the cell's age: 0, 1-31, 32-104, >= 105
                                          # (a* = 31.1 at tau_m 300 and 103.7 at 1000)


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
            "sc002": "events, stationary ages, contact ages, maturity, arbiter, solver (sc002.cable) and agreement as "
                     "sc002.sim, unchanged in arithmetic; be001's detector, commitment, pull and learning; cellpop's "
                     "contacts, deaths and divisions",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN,
            "cg_tol": CG_TOL, "cg_maxit": CG_MAXIT, "theta": THETA, "g_star": G_STAR, "iso": ISO,
            "junctions": JUNCTIONS, "probe_only": PROBE_ONLY, "emt_lam": {f"{m:g}/{tau:g}": v for (m, tau), v in EMT_LAM.items()},
            "arms_t": ARMS_T, "arms_w": ARMS_W, "mus": MUS, "p_div": P_DIV, "p_regrow": P_REGROW,
            "situations_t": SITUATIONS_T, "situations_w": SITUATIONS_W, "runs": RUNS, "age_bins": AGE_BINS,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "window": WINDOW, "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "cellpop", "sc002", "sc003")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sc003.design  ->  sc003/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sc003" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
