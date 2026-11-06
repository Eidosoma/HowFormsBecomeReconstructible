"""DL001: the single source of truth for the runner, the reader and the checks.

The design ledger (PLAN_DL001.md): what a self-organising body gives for free, and what must still be paid for.
The body is br001.sim.body_step's open double well with lateral inhibition: drift -= alpha (G_L * V), with
G_L = (1 - L^2 Lap)^-1 on the periodic lattice, applied by FFT. alpha = 0 is br001.sim.body_step bit for bit. The
linear growth rate at V = 0 is g(k) = 1 - c k / 4 - alpha / (1 + L^2 k) (k = 4 - 2 cos qx - 2 cos qy), so a body
prefers the mode k* when alpha = c (1 + L^2 k*)^2 / (4 L^2); for alpha > 1 the double well keeps no uniform state.
Records and bodies are acquired as in GW001 (msegrid.acquire: conserved body, sigma 0.1), shared by every body and
condition of a case (paired); afterwards the environmental field theta is kept (x1, spread 0.2) or removed (x0).
Panels, all on the open body:
  F  free memory: no record; t = 500, 2,000, 8,000: registration (sign), layout (best shift), spacing (centroid);
  U  the price of holding: the taught record held unchanged at gains 0.005-0.4; t = 2,000;
  W  free repair: S4 body wounds (reset to newborn noise, or flipped) of side 4, 8 and 12, no record or held record;
  B  build: from newborn noise with the held record at gains 0.02, 0.05 and 0.2;
  X  the reversed match on a 64-site sheet: dw, li4 and li16 on S4, S8 and F0, no record and the held record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from br001 import design as B1

TAG = "mse-dl001"
STUDY = "DL001"
IDENTITIES = {
    "preflight": (900872, 900874),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910700, 910716),   # the DL001 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900874, 900876)
PROBE_BLOCKS = (900864, 900868)       # engineering probes P12 and P12b (tag mse-p12), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = B1.MESSAGES, B1.PARENTS, B1.NCASE
SETTLE, TEACH, AMPLITUDE, RELEASE = B1.SETTLE, B1.TEACH, B1.AMPLITUDE, B1.RELEASE
SIGMA_ACQ = 0.1                        # records are acquired in the conserved body at sigma 0.1 (GW001)
KILL_SD = 0.2                          # newborn cells of a reset wound: KILL_SD x N(0, 1) in V and ema
SIDE, SIDE_X = 32, 64
QMAX = math.pi / 2                     # the spacing endpoint reads wavelengths of 4 sites or more


def alpha_for(L, kstar, coupling=1.0):
    return coupling * (1.0 + L * L * kstar) ** 2 / (4.0 * L * L)


K8 = 2.0 - 2.0 * math.cos(2 * math.pi / 8)
K16 = 2.0 - 2.0 * math.cos(2 * math.pi / 16)
BODIES = {"dw": (0.0, 0.0), "li2": (alpha_for(2, K8), 2.0), "li4": (alpha_for(4, K8), 4.0),
          "li16": (alpha_for(16, K16), 16.0)}
BODIES_MAIN = ("dw", "li2", "li4")
BODIES_X = ("dw", "li4", "li16")

PATTERNS = ("S4", "S8", "F0", "BL")
SIGMAS, THETAS = (0.1, 0.3), (0.0, 1.0)
GAINS_U = (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4)
GAINS_B = (0.02, 0.05, 0.2)
GAINS_X = (0.0, 0.02, 0.05, 0.2, 0.4)
WINDOW_F, SNAPS_F = 8000, (500, 2000, 8000)
WINDOW_U, SNAPS_U = 2000, (2000,)
WINDOW_W, SNAPS_W = 2000, (250, 500, 2000)
WINDOW_B, SNAPS_B = 2000, (500, 2000)
WINDOW_X0, SNAPS_X0 = 8000, (2000, 8000)
WINDOW_X, SNAPS_X = 2000, (2000,)
CHUNK = 250                            # noise draws per chunk


@dataclass(frozen=True)
class Cond:
    name: str
    gain: float = 0.0          # the held record's pull (0: no record)
    wound: str = "sham"        # sham | reset | flip  (panel W)
    size: int = 0


COND_F = (Cond("free"),)
COND_U = tuple(Cond(f"g{g:g}", gain=g) for g in GAINS_U)
COND_W = tuple(Cond(f"{w}{s}-g{g:g}", gain=g, wound=w, size=s) for w in ("reset", "flip") for s in (4, 8, 12) for g in (0.0, 0.2))
COND_B = tuple(Cond(f"g{g:g}", gain=g) for g in GAINS_B)
COND_X = tuple(Cond(f"g{g:g}", gain=g) for g in GAINS_X)


def unit_name(pattern, sigma, theta, side=SIDE):
    return f"{pattern}_s{sigma:g}_t{theta:g}" + ("" if side == SIDE else f"_x{side}")


def parse_unit(name):
    parts = name.split("_")
    side = int(parts[3][1:]) if len(parts) > 3 else SIDE
    return parts[0], float(parts[1][1:]), float(parts[2][1:]), side


PANELS = {
    "F": {"title": "free memory: no record", "bodies": BODIES_MAIN, "conds": COND_F, "window": WINDOW_F, "snaps": SNAPS_F,
          "start": "acquired", "units": tuple(unit_name(p, s, t) for p in PATTERNS for s in SIGMAS for t in THETAS)},
    "U": {"title": "the price of holding: the held record at gains 0.005-0.4", "bodies": BODIES_MAIN, "conds": COND_U,
          "window": WINDOW_U, "snaps": SNAPS_U, "start": "acquired",
          "units": tuple(unit_name(p, s, t) for p in PATTERNS for s in SIGMAS for t in THETAS)},
    "W": {"title": "free repair: S4 body wounds", "bodies": BODIES_MAIN, "conds": COND_W, "window": WINDOW_W,
          "snaps": SNAPS_W, "start": "acquired", "units": tuple(unit_name("S4", s, t) for s in SIGMAS for t in THETAS)},
    "B": {"title": "build: from newborn noise with the held record", "bodies": BODIES_MAIN, "conds": COND_B,
          "window": WINDOW_B, "snaps": SNAPS_B, "start": "newborn",
          "units": tuple(unit_name(p, 0.1, t) for p in ("S4", "F0", "BL") for t in THETAS)},
    "X": {"title": "the reversed match on a 64-site sheet", "bodies": BODIES_X, "conds": COND_X, "window": WINDOW_X0,
          "snaps": SNAPS_X0, "start": "acquired", "units": tuple(unit_name(p, 0.1, 0.0, SIDE_X) for p in ("S4", "S8", "F0"))},
}


def tasks():
    return [(p, u) for p, v in PANELS.items() for u in v["units"]]


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
            "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS, "settle": SETTLE, "teach": TEACH,
            "amplitude": AMPLITUDE, "release": RELEASE, "sigma_acq": SIGMA_ACQ, "kill_sd": KILL_SD, "side": SIDE,
            "side_x": SIDE_X, "qmax": QMAX, "bodies": {k: list(v) for k, v in BODIES.items()},
            "bodies_main": BODIES_MAIN, "bodies_x": BODIES_X, "patterns": PATTERNS, "sigmas": SIGMAS, "thetas": THETAS,
            "chunk": CHUNK, "x_split": {"no_record_window": WINDOW_X0, "no_record_snaps": SNAPS_X0,
                                        "held_window": WINDOW_X, "held_snaps": SNAPS_X},
            "panels": {p: {"title": v["title"], "bodies": v["bodies"], "conds": [asdict(c) for c in v["conds"]],
                           "window": v["window"], "snaps": v["snaps"], "start": v["start"], "units": v["units"]}
                       for p, v in PANELS.items()}}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m dl001.design  ->  dl001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "dl001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
