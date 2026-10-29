"""BE003: the free window against the prescribed signal.

SC002's tissue (BE001's tissue, detector and commitment on cellpop's vacancy lattice; gap junctions only between occupied
neighbours; sc002.sim's arithmetic, unchanged) with no turnover, so the only births are a wound's regrowth (SC002's
panel W). BE002's regime signal is added as a property of two arms: while the signal is on, every junction with an end in
the footprint has full-strength conductance lam_sig^2 = 1 instead of lam^2 = 9 (BE002's closure, be002.sim.conductances),
and a junction's maturity scales whatever full strength it has: g = lam_sig^2 (1 - exp(-age / tau_m)). Channels
assembled (maturation) times channels open (gating) is a product, so closure acts on young and mature junctions alike.
Arms:
  cue            LR004's anchors as arbiter (no detector)
  inst-1/1.5/3   instant junctions at coupling length 1, 1.5 and 3 (BE001's ladder; 1 and 1.5 are the rulers for "as
                 short coupling does", 1 being the signal's own length)
  mat-300/1000   junctions at lam 3 maturing as 1 - exp(-age / tau_m) from each contact's formation (SC002's): the free
                 window a regrowing wound opens by itself
  dial           inst-3 with the signal (BE002's local dial on the population lattice): the prescribed window
  mat-dial       mat-300 with the signal: both windows
Every arm uses threshold 0.1, kappa 4, tau 300 and pull 1 (BE001's). Without the signal, dial and mat-dial are inst-3
and mat-300 bit for bit (checks Q5).
Events. Every run empties an 8 x 8 wound at t = 0 (values 0, contacts lost, anchors kept), regrown by division from its
rim at 0.04 per update with the daughters inheriting (SC002's panel W, unchanged):
  regrow8        clean cues; the signal over the wound dilated by 2 (a 12 x 12 footprint), on at updates 1-1,000: an
                 injury signal
  regrow8_late   the same with the signal on at updates 1,001-2,000; only the two signal arms are run (every other arm
                 is regrow8's, bit for bit: one population history per case, arms independent)
  regrow+cue8    BE001's scattered corruption of a quarter of the anchors as well; the injury signal prompt
  twin4@d        after update d the cue of two 4 x 4 patches is re-specified (BE001's legitimate change, the target
                 with it): 'young' at the wound's centre (its cells regrown; the patch dilated by 2 is exactly the wound)
                 and its 'twin' 16 columns away in old tissue (10 columns from the wound on either side; the same stripe
                 phase). The signal accompanies the change, over both patches dilated by 2 (the wound and the twin's
                 8 x 8), on at updates d + 1 to d + 1,000. d = 0 (the cue changed while the wound regrows), 300 (the
                 wound refilled, its junctions young), 1,000 and 2,000 (maturing: about 3 and 6 tau_m for mat-300, 1
                 and 2 for mat-1000). Read at d + 250, d + 1,000 and d + 2,000.
Regions: in (the wound), young and twin (the 4 x 4 patches), ring (the wound dilated by 2, less the wound), out
(outside the wound dilated by 2 and the twin dilated by 2). Until update d a twin run's arms without the signal are
regrow8's bit for bit, and its signal arms (their signal off until d + 1) are their aliases'; so regrow8 read at
d + 2,000 gives each arm without the signal its exact no-change counterfactual, and the change's net effect on the young
patch is r_young(twin4@d) - (1 - r_young(regrow8 at d + 2,000)) (the signal arms: change and signal together, against
their alias with neither). Patterns S4 (stripes) and F0 (domains) in quiet tissue
(theta x 0), both bodies.
"""
from __future__ import annotations

import hashlib
import json

from dl001 import design as DL
from sc002 import design as S2D

TAG = "mse-be003"
PROBE_TAG = "mse-p27"
STUDY = "BE003"
PROBE_BLOCKS = (900670, 900674)
IDENTITIES = {"preflight": (900674, 900676), "development": (910220, 910236)}
DEBUG_BLOCKS = (900676, 900678)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = S2D.SIDE, S2D.SIGMA, S2D.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = S2D.EPS, S2D.KR, S2D.SIGMA_R, S2D.KC, S2D.STRENGTH0, S2D.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE, GAIN = S2D.KILL_SD, S2D.DENSITY, S2D.VMIN, S2D.PULL, S2D.RATE, S2D.GAIN
KAPPA, G_LEAK, TAU, S_MIN, CG_TOL, CG_MAXIT = S2D.KAPPA, S2D.G_LEAK, S2D.TAU, S2D.S_MIN, S2D.CG_TOL, S2D.CG_MAXIT
MESSAGES, PARENTS, NCASE = S2D.MESSAGES, S2D.PARENTS, S2D.NCASE
BODIES = S2D.BODIES
PATTERNS, THETAS = ("S4", "F0"), (0.0,)
THETA = S2D.THETA                                  # BE001's trigger threshold, 0.1

SIG = {"d": 2, "duration": 1000, "lam_sig": 1.0}   # BE002's footprint dilation, duration and closed length
JUNCTIONS = {"inst-1": {"lam": 1.0, "tau_m": 0.0, "signal": False},
             "inst-1.5": {"lam": 1.5, "tau_m": 0.0, "signal": False},
             "inst-3": {"lam": 3.0, "tau_m": 0.0, "signal": False},
             "mat-300": {"lam": 3.0, "tau_m": 300.0, "signal": False},
             "mat-1000": {"lam": 3.0, "tau_m": 1000.0, "signal": False},
             "dial": {"lam": 3.0, "tau_m": 0.0, "signal": True},
             "mat-dial": {"lam": 3.0, "tau_m": 300.0, "signal": True}}
ARMS = ("cue", *JUNCTIONS)
SIGNAL_ARMS = tuple(a for a, p in JUNCTIONS.items() if p["signal"])
ALIAS = {"dial": "inst-3", "mat-dial": "mat-300"}          # without the signal

WOUND, PATCH, TWIN_SHIFT, P_REGROW = 8, 4, 16, S2D.P_REGROW
YOUNG_OFFSET = (WOUND - PATCH) // 2                          # the young patch sits 2 sites inside the wound's rim
WINDOW, READS, TRACE = 4000, (250, 1000, 2000, 2300, 3000, 4000), 100     # regrow runs; 2,300 and 3,000: the twin runs'
                                                                          # last reads, for their no-change counterfactual
HORIZON = 2000                                               # twin runs: read d + 250, d + 1,000 and d + 2,000
DELAYS = (0, 300, 1000, 2000)
RUNS = (("regrow", 0, "prompt"), ("regrow", 0, "late"), ("regrow+cue", 0, "prompt"),
        *(("twin", d, "prompt") for d in DELAYS))


def run_name(situation, delay, signal):
    if situation == "twin":
        return f"twin{PATCH}@{delay}"
    return f"{situation}{WOUND}" + ("_late" if signal == "late" else "")


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def run_arms(situation, delay, signal):
    """The arms run: every arm, except the late run, whose other arms are regrow8's bit for bit."""
    return SIGNAL_ARMS if signal == "late" else ARMS


def run_window(situation, delay, signal):
    return delay + HORIZON if situation == "twin" else WINDOW


def run_reads(situation, delay, signal):
    return (delay + 250, delay + 1000, delay + HORIZON) if situation == "twin" else READS


def on_window(situation, delay, signal):
    """(first, last) update with the signal on."""
    if signal == "late":
        return SIG["duration"] + 1, 2 * SIG["duration"]
    return delay + 1, delay + SIG["duration"]


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
    """One task per (body, unit): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "lr002.sim.prepare = dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "sc002": "sc002.sim's tissue, events, contacts, maturity, arbiter, solver and population, unchanged in "
                     "arithmetic; be002.sim.footprint; the signal on the population lattice as declared",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN,
            "cg_tol": CG_TOL, "cg_maxit": CG_MAXIT, "theta": THETA, "sig": SIG, "junctions": JUNCTIONS, "arms": ARMS,
            "signal_arms": SIGNAL_ARMS, "alias": ALIAS, "wound": WOUND, "patch": PATCH, "twin_shift": TWIN_SHIFT,
            "young_offset": YOUNG_OFFSET, "p_regrow": P_REGROW, "delays": DELAYS, "horizon": HORIZON, "runs": RUNS,
            "run_arms": {run_name(*x): run_arms(*x) for x in RUNS},
            "run_windows": {run_name(*x): run_window(*x) for x in RUNS},
            "run_reads": {run_name(*x): run_reads(*x) for x in RUNS},
            "on_windows": {run_name(*x): on_window(*x) for x in RUNS},
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "window": WINDOW, "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "cellpop", "sc002", "be003")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be003.design  ->  be003/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be003" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
