"""AR001: which source to correct, frozen (the v2.5 review's experiment 6; the lane's ME002-ME004 question).

The body, the record and the cue can disagree. Can a frozen controller choose what to correct better than the best
fixed policy, at the same resource ceiling, when it is not told which source is wrong? It has a regime signal of
declared reliability, and the evidence may arrive late.

The tissue: BE006's at its calibrated clock SL (be006.sim, be005.sim, be002.sim, be001.sim and lr005.sim imported,
unchanged): LR004's record of relations read by DL001's bodies at gain 0.2 after DL002's acquisition, a positional cue
(anchors at a quarter of the cells holding the acquired record's signs) on BE001's 32 x 32 sheet; every bond's Hebbian
rate eta = 3e-4 with the bond noise scaled with it (p_b = 3e-5), as CALIBRATION.md places the clocks at tau_m = 300
updates = 1 h (T* = 1,959 updates, 6.5 h). One event at t = 0 on a 4 x 4 patch (scattered over the sheet for cue
damage), then 8,000 updates (26.7 h), scored at t = 8,000.

Situations (LR005's, on a 4 x 4 patch, plus correlated errors):
  none        nothing
  body        the body's values flipped in the patch (the record and the cue right)
  memory      the record flipped in the patch with consistent bonds (the body and the cue right)
  correlated  the body and the record both flipped in the patch (they agree on the error; the cue right)
  shared      the patch's cells killed with everything they held (record 0, bonds between dead cells lost, anchors lost)
  cue         a random quarter of the anchors flipped, scattered (the cue wrong; body and record right)
  change      the patch's anchors flipped: a legitimate change, scored against the new target; the same run scored
              against the old target is coherent cue corruption (the information-limit pair: identical observations,
              different correct answers)

Policies, every one at the calibrated clock (the same Hebbian rate, bond noise, pull and window: the resource ceiling):
  inactive  no correction: no relearning, no repair (the record drifts under the bond noise)
  record    always correct the body from the record: the record keeps itself (LR001's record+parity), the body reads it
  body      always correct the record from the body: its bonds relearn from the body (LR002)
  vote      three copies: LR004's two-record vote (a second record with its own noise; both relearn toward the
            majority of the body's and the two records' relations)
  arbiter   LR004's cue arbiter: the body where body and record agree, the cue at an anchored cell where they disagree,
            else the record
  latch     LR005's cue latch (community-s: the cue overrules where at least half the live anchors within 3 sites
            disagree), its latch held for the calibrated commitment (15,000 updates)
  rest      BE001's detector at coupling length 3 with the calibrated commitment (BE006's never-SL): the controller with
            no signal
  dial      the controller: BE006's dial-SL (BE002's local dial: the junctions touching the footprint, the patch
            dilated by 2, closed to coupling length 1 while the regime signal is on, updates 1-1,000), frozen as built
FIXED = every policy but dial. The controller is not told which source is wrong: it reads the regime signal only.

The signal's reliability is declared as a hit rate h (the probability that the signal is sent when re-specifying
the patch to the cue is right: memory, correlated, change scored as legitimate) and a false-alarm rate f (sent in the
other scorings: none, body, shared, scattered cue damage, the change run scored as coherent corruption). Every case's
outcome with the signal on (dial) and off (rest) is simulated on paired draws, so the controller's expected score
under any (h, f) is exact: p u(dial) + (1 - p) u(rest), with p = h or f by scoring. No signal draw is simulated.

Side arms (the controller only; every fixed policy never reads the signal, so its outcome is the main grid's):
  timing     the signal at D = 0.5, 1 and 2 T* after the event (dial-m0.5 / dial-m1 / dial-m2), in memory,
             correlated, change and cue (a late sham in none, body and shared was trimmed for cost: the prompt one cost
             those situations nothing measurable in the smoke)
  precision  the footprint shifted by 4 or 6 sites along the rows (dial-s4, dial-s6), or the patch dilated by 0 or 8
             instead of 2 (dial-d0, dial-d8), in memory, change and cue
  misread    GC001's quenched misread of the cue (sigma 1) in none, memory and change, for the policies that read the
             cue (arbiter, latch, rest, dial); the others never read it, so their outcomes are the main grid's
"""
from __future__ import annotations

import hashlib
import json
import math

from be006 import design as B6
from dl001 import design as DL
from lr005 import design as L5

TAG = "mse-ar001"
PROBE_TAG = "mse-p41"
STUDY = "AR001"
PROBE_BLOCKS = (900025, 900029)
IDENTITIES = {"preflight": (900029, 900031), "development": (910528, 910544)}
DEBUG_BLOCKS = (900031, 900033)   # the engine reserves 900000-900999 for engineering; 900025-900032 scanned free (fork A)
CONFIRMATION_RESERVED = (920000, 920128)   # reserved for a later confirmation; never drawn here (scanned free)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B6.SIDE, B6.SIGMA, B6.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B6.EPS, B6.KR, B6.SIGMA_R, B6.KC, B6.STRENGTH0, B6.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B6.KILL_SD, B6.DENSITY, B6.VMIN, B6.PULL, B6.RATE
GAIN, KAPPA, G_LEAK, S_MIN = B6.GAIN, B6.KAPPA, B6.G_LEAK, B6.S_MIN
SIG = B6.SIG                                                   # BE002's footprint, duration, lengths and threshold
RHO, MIN_ANCHORS = L5.RHO, L5.MIN_ANCHORS
Q_LATCH = L5.COMMUNITY["community-s"][0]                       # LR005's sensitive community rule
MESSAGES, PARENTS, NCASE = B6.MESSAGES, B6.PARENTS, B6.NCASE

CLOCK = dict(B6.CLOCKS["SL"])                                  # eta_a = eta = 3e-4, p_b = 3e-5, tau_c = 15,000
LANE_CLOCK = dict(B6.CLOCKS["F"])                              # eta 0.01, p_b 1e-3, tau_c 300 (the bridges only)
T_STAR = B6.t_star(CLOCK["eta"])                               # 1,959.3 updates (6.5 h)
TAU_M = B6.TAU_M

SIZE = 4
WINDOW = 8000
READS = (1000, 2000, 4000, 8000)
T_READ = 8000
TRACE = 200

BODIES = ("dw", "li4")
PATTERNS = ("S4", "F0")                                        # LB dropped for cost (reported)
THETAS = (0.0, 1.0)


def unit_name(pattern, theta):
    return f"{pattern}_t{theta:g}"


def parse_unit(name):
    pattern, t = name.split("_")
    return pattern, float(t[1:])


UNITS = tuple(unit_name(p, t) for p in PATTERNS for t in THETAS)

SITUATIONS = ("none", "body", "memory", "correlated", "shared", "cue", "change")
SCORINGS = ("none", "body", "memory", "correlated", "shared", "cue", "change/new", "change/old")
RIGHT = ("memory", "correlated", "change/new")                 # re-specifying the patch to the cue is right: P(on) = h
WRONG = ("none", "body", "shared", "cue", "change/old")        # it is not: P(on) = f
WEIGHTS = {s: 1.0 / len(SCORINGS) for s in SCORINGS}           # the declared utility mixture (equal weights)


def delay(m):
    return int(round(m * T_STAR))


MULTS = (0.5, 1, 2)
SHIFTS = (4, 6)
DILATIONS = (0, 8)
KINDS = ("inactive", "record", "body", "vote", "arbiter", "latch", "rest", "dial")
FIXED = ("inactive", "record", "body", "vote", "arbiter", "latch", "rest")
CUE_READERS = ("arbiter", "latch", "rest", "dial")
ARM = {k: {"kind": k, "delay": 0, "d": SIG["d"], "shift": 0} for k in KINDS}
for _m in MULTS:
    ARM[f"dial-m{_m:g}"] = {"kind": "dial", "delay": delay(_m), "d": SIG["d"], "shift": 0}
for _s in SHIFTS:
    ARM[f"dial-s{_s}"] = {"kind": "dial", "delay": 0, "d": SIG["d"], "shift": _s}
for _d in DILATIONS:
    ARM[f"dial-d{_d}"] = {"kind": "dial", "delay": 0, "d": _d, "shift": 0}
TIMING = tuple(f"dial-m{m:g}" for m in MULTS)
PRECISION = tuple(f"dial-s{s}" for s in SHIFTS) + tuple(f"dial-d{d}" for d in DILATIONS)
MAIN = FIXED + ("dial",)
MISREAD_SIGMA = 1.0

RUNS = (("none", 0.0, MAIN),
        ("body", 0.0, MAIN),
        ("memory", 0.0, MAIN + TIMING + PRECISION),
        ("correlated", 0.0, MAIN + TIMING),
        ("shared", 0.0, MAIN),
        ("cue", 0.0, MAIN + TIMING + PRECISION),
        ("change", 0.0, MAIN + TIMING + PRECISION),
        ("none", MISREAD_SIGMA, CUE_READERS),
        ("memory", MISREAD_SIGMA, CUE_READERS),
        ("change", MISREAD_SIGMA, CUE_READERS))


def run_name(situation, sigma, arms=None):
    return f"{situation}@{sigma:g}"


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def on_window(arm):
    a = ARM[arm]
    return a["delay"] + 1, a["delay"] + SIG["duration"]


def hours(updates):
    return updates / TAU_M


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


def tasks():
    """One task per (body, unit): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "confirmation_reserved": CONFIRMATION_RESERVED,
            "messages": MESSAGES, "parents": PARENTS,
            "preparation": "lr002.sim.prepare = dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "imports": "be006.sim.sig_targets (the dial and rest arms at clock SL), be002.sim footprint, conductances and "
                       "the sparse LU, be001.sim patch and cable kernel, lr005.sim targets, anchors, scattered damage and "
                       "newborns, gc001.sim's misread, unchanged; the event's correlated situation and the latch's hold "
                       "parameter are new",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "s_min": S_MIN, "sig": SIG, "rho": RHO,
            "min_anchors": MIN_ANCHORS, "q_latch": Q_LATCH, "clock": CLOCK, "lane_clock": LANE_CLOCK, "t_star": T_STAR,
            "tau_m": TAU_M, "size": SIZE, "window": WINDOW, "reads": READS, "t_read": T_READ, "trace": TRACE,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "situations": SITUATIONS, "scorings": SCORINGS, "right": RIGHT, "wrong": WRONG, "weights": WEIGHTS,
            "kinds": KINDS, "fixed": FIXED, "cue_readers": CUE_READERS, "arm": ARM, "mults": MULTS, "shifts": SHIFTS,
            "dilations": DILATIONS, "misread_sigma": MISREAD_SIGMA, "runs": RUNS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004", "be005", "be006", "gc001", "ar001")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m ar001.design  ->  ar001/frozen/design.json
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar001" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
