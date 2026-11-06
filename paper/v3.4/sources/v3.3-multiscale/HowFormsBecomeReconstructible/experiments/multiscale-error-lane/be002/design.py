"""BE002: a regime signal that turns the bioelectric detector's coupling dial.

BE001's tissue, events, scoring, cable detector and commitment, unchanged and imported (be001.sim, lr005.sim), at read
gain 0.2. A regime signal is added: a per-site field, independent of the cue and the record, set at t = 0 over a
footprint (the event's patch dilated by SIG['d'] sites on the torus, square dilation) and held for SIG['duration']
updates, then off. It is delivered with or without the event ("_sig" runs); a signal with no event is a false
(sham) signal. Arms:
  cue           LR004's anchors as arbiter (no detector), as BE001;
  bio-1/1.5/3   BE001's cable detectors with fixed coupling lengths 1, 1.5 and 3 (threshold 0.1), as BE001;
  dial-local    coupling length 3 at rest; while the signal is on, every junction with an end in the footprint has
                conductance lam_sig^2 = 1 (junction closure); the potentials solve the cable equation with these
                conductances (a per-branch sparse LU factorisation, made once when the signal starts);
  dial-global   coupling length 3 at rest, 1 over the whole sheet while the signal is on (a systemic alarm);
  permit-local  coupling length 1.5; a cell may be newly triggered only inside the footprint while the signal is on
                (a permission gate); committed cells keep their commitment, which decays as in BE001.
Without the signal, dial-local and dial-global are bio-3 and permit-local is the cue arm, bit for bit (checks Q5).
Runs: none, scattered cue damage (cue), memory damage and legitimate change of a 4 x 4 patch, legitimate change of an
8 x 8 patch, each with and without the signal ("_sig": on for updates 1-1,000; none with it = a sham signal over clean
tissue; cue with it = a sham signal over scattered corruption), and memory damage of a 4 x 4 patch with a late signal
("_late": on for updates 1,001-2,000, after the damage has stood unrepaired for 1,000 updates). Coherent cue corruption is the change run read against the old target
(r_in_old): by construction it is the same evidence as a legitimate change (THEORY 8.4).
"""
from __future__ import annotations

import hashlib
import json

from be001 import design as B1
from dl001 import design as DL

TAG = "mse-be002"
PROBE_TAG = "mse-p24"
STUDY = "BE002"
PROBE_BLOCKS = (900640, 900644)
IDENTITIES = {"preflight": (900644, 900646), "development": (910140, 910156)}
DEBUG_BLOCKS = (900646, 900648)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B1.SIDE, B1.SIGMA, B1.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0, ETA = B1.EPS, B1.KR, B1.SIGMA_R, B1.KC, B1.STRENGTH0, B1.ETA
KILL_SD, DENSITY, VMIN, PULL, RATE = B1.KILL_SD, B1.DENSITY, B1.VMIN, B1.PULL, B1.RATE
BODIES, PATTERNS, THETAS = B1.BODIES, B1.PATTERNS, B1.THETAS
MESSAGES, PARENTS, NCASE = B1.MESSAGES, B1.PARENTS, B1.NCASE
GAIN, KAPPA, G_LEAK, TAU, S_MIN = B1.GAIN, B1.KAPPA, B1.G_LEAK, B1.TAU, B1.S_MIN

SIG = {"d": 2, "duration": 1000, "lam_rest": 3.0, "lam_sig": 1.0, "lam_permit": 1.5, "theta": 0.1}
REF = ("bio-1", "bio-1.5", "bio-3")                       # BE001's arms, unchanged (be001.design.BIO)
SIGNAL_ARMS = {"dial-local": {"kind": "local", "theta": SIG["theta"]},
               "dial-global": {"kind": "global", "theta": SIG["theta"]},
               "permit-local": {"kind": "permit", "theta": SIG["theta"]}}
ARMS = ("cue", *REF, *SIGNAL_ARMS)
ALIAS = {"dial-local": "bio-3", "dial-global": "bio-3", "permit-local": "cue"}     # without the signal
SIGNALS = {"": None, "sig": (1, SIG["duration"]), "late": (SIG["duration"] + 1, 2 * SIG["duration"])}   # (first, last)
RUNS = (("none", 8, ""), ("none", 8, "sig"), ("cue", 8, ""), ("cue", 8, "sig"), ("memory", 4, ""), ("memory", 4, "sig"),
        ("memory", 4, "late"), ("change", 4, ""), ("change", 4, "sig"), ("change", 8, ""), ("change", 8, "sig"))
WINDOW, READS, TRACE = B1.WINDOW, B1.READS, B1.TRACE
TRACE_READS = tuple(range(TRACE, WINDOW + 1, TRACE))


def run_name(situation, size, signal):
    return f"{situation}{size}" + (f"_{signal}" if signal else "")


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


unit_name, parse_unit, UNITS = B1.unit_name, B1.parse_unit, B1.UNITS


def tasks():
    return [("E", u) for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "lr002.sim.prepare = dl002.sim.prepare (DL002's tag, acquisition and templates, unchanged)",
            "be001": "events, cable kernel, bioelectric targets and commitment of be001.sim, unchanged; lr005's cue arm",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "strength0": STRENGTH0, "eta": ETA, "kill_sd": KILL_SD, "density": DENSITY, "vmin": VMIN, "pull": PULL,
            "rate": RATE, "gain": GAIN, "kappa": KAPPA, "g_leak": G_LEAK, "tau": TAU, "s_min": S_MIN,
            "ref_bio": {a: B1.BIO[a] for a in REF}, "sig": SIG, "signal_arms": SIGNAL_ARMS, "alias": ALIAS, "signals": SIGNALS,
            "arms": ARMS, "runs": RUNS, "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS,
            "thetas": THETAS, "units": UNITS, "window": WINDOW, "reads": READS, "trace": TRACE}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "be002")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m be002.design  ->  be002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "be002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
