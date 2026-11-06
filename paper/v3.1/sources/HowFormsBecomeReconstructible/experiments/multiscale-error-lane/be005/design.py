"""BE005: the deadline and the membrane.

BE004's tissue (be004.sim: BE002's events, cable detector, commitment, local dial and LR004's arbiter, unchanged and
imported), at read gain 0.2 on BE001's twelve unit-body pairs. Two questions:

Panel D, the deadline. BE004 found that a late regime signal repairs a 4 x 4 memory damage less once LR004's arbiter has
relearned the damaged patch's anchored cells, the detector's only sensors: a bond taught at strength s0 = 0.8 crosses zero
under relearning at rate eta after T*(eta) = ln(1 + s0) / -ln(1 - eta) updates (58.5 at the lane's eta = 0.01). The
lane has one Hebbian rate (ETA) for every bond; here the bonds that touch a cell whose target is the arbiter's cue (an
anchored cell whose body and record disagree and which is not committed) relearn at eta_a, and every other bond at ETA.
So eta_a is the arbiter's own clock, apart from the relearning that carries a commitment. eta_a in {0.005, 0.01, 0.02}
(T* = 117.3, 58.5, 29.1); the signal comes after D = round(m T*(eta_a)) updates, m in {0, 0.5, 1, 2, 4, 16}, and each
eta_a has its own no-signal arm. If the deadline is the arbiter's clock, the loss collapses on m and not on D.

Panel M, the membrane. BE001's potentials reach the cable equation's steady state every update, so BE004 found a signal's
steadiness and duration irrelevant. Here a signal arm's potentials relax toward the steady state with time constant
tau_v: v <- v + (v* - v) / tau_v (tau_v = 1 is BE004's arithmetic, bit for bit), starting from the pre-event steady
state (every anchor agreeing). tau_v in {1, 10, 100}; under each, the steady 1,000-update signal, signals on for only 1,
10 or 100 updates, flickering signals (p = 0.5, 0.25) and the no-signal arm, over a legitimate 4 x 4 change; the steady
signal and the no-signal arm over a 4 x 4 memory damage (does a slow membrane let the arbiter erase the evidence before
the potentials fall?) and over scattered cue corruption (a prompt sham).

Arms (every signal arm is BE004's dial with eta_a, tau_v, duration, flicker or "never" set; BE004's footprint, closure,
hold off):
  cue, bio-1, bio-3                    LR004's arbiter; BE001's detectors at coupling 1 and 3 (references, BE004's)
  dial-e{eta}                          the dial, the arbiter relearning at eta (dial-e0.01 is BE004's dial)
  never-e{eta}                         the same tissue, the signal never on (never-e0.01 is bio-3, bit for bit)
  dial-tv{tau}, never-tv{tau}          the dial and its no-signal arm with membrane time constant tau (tau 1: BE004's)
  dial-t{T}-tv{tau}                    on for its first T = 1, 10, 100 updates only
  dial-f{p}-tv{tau}                    on at each update of the window with probability p = 0.5, 0.25 (BE004's draws)
Runs (event, patch side, delay D; arms):
  memory4@0      the references, every dial-e and never-e, and dial-tv / never-tv at tau 10 and 100
  memory4@D      D > 0: the dial-e arms whose m T*(eta) rounds to D (twelve delays, fifteen arm-runs)
  change4@0      the references and every panel-M arm at tau 1, 10, 100
  cue4@0         dial-tv and never-tv at tau 1, 10, 100 (a prompt sham's cost against the same tissue without it)
"""
from __future__ import annotations

import hashlib
import json
import math

from be001 import design as B1
from be004 import design as B4
from dl001 import design as DL

TAG = "mse-be005"
PROBE_TAG = "mse-p30"
STUDY = "BE005"
PROBE_BLOCKS = (900620, 900624)
IDENTITIES = {"preflight": (900624, 900626), "development": (910280, 910296)}
DEBUG_BLOCKS = (900626, 900628)  # the engine reserves 900000-900999 for engineering; 900620-900627 scanned free
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B4.SIDE, B4.SIGMA, B4.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B4.EPS, B4.KR, B4.SIGMA_R, B4.KC, B4.STRENGTH0, B4.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B4.KILL_SD, B4.DENSITY, B4.VMIN, B4.PULL, B4.RATE
BODIES, PATTERNS, THETAS = B4.BODIES, B4.PATTERNS, B4.THETAS
MESSAGES, PARENTS, NCASE = B4.MESSAGES, B4.PARENTS, B4.NCASE
GAIN, KAPPA, G_LEAK, TAU, S_MIN = B4.GAIN, B4.KAPPA, B4.G_LEAK, B4.TAU, B4.S_MIN
SIG = B4.SIG                                                    # BE002's footprint, duration, lengths and threshold
REF = B4.REF

ETAS = (0.005, 0.01, 0.02)                                      # the arbiter's relearning rates
MULTS = (0, 0.5, 1, 2, 4, 16)                                   # the signal's delay in units of T*(eta_a)
TAUS = (1, 10, 100)                                             # membrane time constants (updates)
DURS = (1, 10, 100)                                             # brief signals
FLICKS = (0.5, 0.25)


def t_star(eta, s0=STRENGTH0):
    """Updates for a bond taught at strength s0 to cross zero under relearning toward the opposite sign at rate eta."""
    return math.log(1.0 + s0) / -math.log(1.0 - eta)


def delay(eta, m):
    return int(round(m * t_star(eta)))


def fmt(x):
    return f"{x:g}"


BASE = {"eta_a": ETA, "tau_v": 1, "p_on": 1.0, "dur": 1000, "never": False}
SIGNAL_ARMS = {}
for _e in ETAS:
    SIGNAL_ARMS[f"dial-e{fmt(_e)}"] = dict(BASE, eta_a=_e)
    SIGNAL_ARMS[f"never-e{fmt(_e)}"] = dict(BASE, eta_a=_e, never=True)
for _t in TAUS:
    SIGNAL_ARMS[f"dial-tv{_t}"] = dict(BASE, tau_v=_t)
    SIGNAL_ARMS[f"never-tv{_t}"] = dict(BASE, tau_v=_t, never=True)
    for _d in DURS:
        SIGNAL_ARMS[f"dial-t{_d}-tv{_t}"] = dict(BASE, tau_v=_t, dur=_d)
    for _p in FLICKS:
        SIGNAL_ARMS[f"dial-f{fmt(_p)}-tv{_t}"] = dict(BASE, tau_v=_t, p_on=_p)
ARMS = ("cue", *REF, *SIGNAL_ARMS)
EQUIV = {"dial-tv1": "dial-e0.01", "never-tv1": "never-e0.01"}  # the same arm under two names (tau 1, eta 0.01)

PANEL_M = tuple(a for t in TAUS for a in (f"dial-tv{t}", *(f"dial-t{d}-tv{t}" for d in DURS),
                                          *(f"dial-f{fmt(p)}-tv{t}" for p in FLICKS), f"never-tv{t}"))
MEM0 = ("cue", *REF, *(f"dial-e{fmt(e)}" for e in ETAS), *(f"never-e{fmt(e)}" for e in ETAS),
        *(f"dial-tv{t}" for t in TAUS[1:]), *(f"never-tv{t}" for t in TAUS[1:]))
DELAYED = {}                                                    # D -> the dial-e arms delayed by D, in ETAS order
for _e in ETAS:
    for _m in MULTS[1:]:
        DELAYED.setdefault(delay(_e, _m), []).append(f"dial-e{fmt(_e)}")
RUNS = (("memory", 4, 0, MEM0),
        *(("memory", 4, d, tuple(DELAYED[d])) for d in sorted(DELAYED)),
        ("change", 4, 0, ("cue", *REF, *PANEL_M)),
        ("cue", 4, 0, tuple(a for t in TAUS for a in (f"dial-tv{t}", f"never-tv{t}"))))
WINDOW, TRACE = 4000, 100
READS = (250, 1000, 2000, 4000)
FOOTPRINTS = (0, 2, 4, 8)


def run_name(situation, size, delay_, arms=None):
    return f"{situation}{size}@{delay_}"


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def run_arms(situation, size, delay_, arms):
    return tuple(arms)


def on_window(situation, size, delay_, arms=None):
    """(first, last) update with the signal on (an arm's duration, flicker and 'never' act inside it)."""
    return delay_ + 1, delay_ + SIG["duration"]


def where(eta, m):
    """(run name, arm) of the dial at eta_a delayed by m T*(eta)."""
    return run_name("memory", 4, delay(eta, m)), f"dial-e{fmt(eta)}"


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


unit_name, parse_unit, UNITS = B1.unit_name, B1.parse_unit, B1.UNITS


def tasks():
    """One task per (body, unit): every run and arm of that body on one block."""
    return [(b, u) for u in UNITS for b in BODIES]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "lr002.sim.prepare = dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "be004": "events, footprint, conductances, sparse LU, the local dial, the arbiter and BE001's references of "
                     "be004.sim / be002.sim / be001.sim, unchanged; the arbiter's relearning rate and the membrane are new",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN,
            "ref_bio": {a: B1.BIO[a] for a in REF}, "sig": SIG, "base": BASE, "signal_arms": SIGNAL_ARMS,
            "etas": ETAS, "mults": MULTS, "t_star": {fmt(e): t_star(e) for e in ETAS},
            "delays": {fmt(e): [delay(e, m) for m in MULTS] for e in ETAS}, "taus": TAUS, "durs": DURS,
            "flicks": FLICKS, "arms": ARMS, "runs": RUNS, "on_windows": {run_name(*x): on_window(*x) for x in RUNS},
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "units": UNITS,
            "window": WINDOW, "reads": READS, "trace": TRACE, "footprints": FOOTPRINTS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002", "be004", "be005")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be005.design  ->  be005/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be005" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
