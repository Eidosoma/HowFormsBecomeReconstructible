"""SM001: can a repair rule learned at one scale predict another? (the PI's "Multiscale 2"; REVIEW_V25_NEXT_EXPERIMENTS.md,
section SM001). DRAFT for the lead's review (phase A).

The tissue: BE006's at clock F (sm001.sim: be006.sim.sig_targets unchanged, the builders rewritten at any side), dw
reading the record at gain 0.2 in quiet tissue, after DL002's acquisition of stripes of width w. One repair episode: a
coherent memory damage of an L x L patch (the record flipped, its bonds consistent), then BE002's local dial (the
junctions touching the footprint, the patch dilated by DIL, closed from lam_rest to lam_sig = lam_rest / 3) on for 1,000
updates from a delay d, with the commitment decaying over tau_c; read at 4,000 updates. Then a fresh dw body reads the
final record (protected) for 2,000 updates: the endpoint.

The dimensionless variables (the PI's):
  x1 = lam_rest / w     communication range relative to feature width
  x2 = L / lam_rest     injury size relative to communication range
  x3 = d / T*           signal delay relative to the evidence lifetime, T* = ln 1.8 / -ln(1 - eta) = 58.5 updates
  x4 = tau_c / T*       commitment relative to the corrective action's time (the bonds relearned to the committed
                        signs take about T* at eta; BE006)
  x5 = D_wall / lam_rest   the patch's distance to the nearest wall (GW001), -1 / lam_rest across a wall (reported
                        covariate; see the registration)

Stages: FIT (side 32, development blocks) -> the model and the comparators fitted, frozen and committed -> TEST (side 64,
fresh blocks): transfer (more cells, fixed lengths), refinement (every length doubled from the FIT units: w, L, lam, the
footprint's dilation, the sheet; scored against its half-scale twin, the transfer unit on the same blocks, so that the
registered contrast doubles every declared length at a fixed sheet; against the 32 x 32 means, reported), and geometry
(walls or none: patches mid-stripe or across a wall). Run apart, reported apart. "Fresh patterns" are fresh acquisitions
of the stripe family on fresh blocks, plus one new width (W32, refinement only), not new pattern families.
"""
from __future__ import annotations

import hashlib
import json
import math

from be006 import design as B6
from dl001 import design as DL
from dl002 import design as D2

TAG = "mse-sm001"
PROBE_TAG = "mse-p42"
STUDY = "SM001"
# every stage's blocks, listed (Amendment 1, 31 October 2026: the phase-A cohorts 911824-911855 lay outside the engine's
# reserved development range, mse.assay.RANGES 910000-910999, and were refused before any draw; these are free inside it)
IDENTITIES = {"preflight": (900042, 900043), "fit": tuple(range(910628, 910644)),
              "test": (910644,) + tuple(range(910843, 910858))}
PROBE_BLOCKS = {"fit": (900034, 900038), "test": (900038, 900042)}
DEBUG_BLOCKS = (900044, 900046)     # the engine reserves 900000-900999 for engineering; 900034-900045 scanned free (fork M)
PURPOSE = {"probe": "engineering", "preflight": "engineering", "fit": "development", "test": "development"}

SIGMA, CHUNK = B6.SIGMA, B6.CHUNK
EPS, KR, SIGMA_R, KC, STRENGTH0 = B6.EPS, B6.KR, B6.SIGMA_R, B6.KC, B6.STRENGTH0
DENSITY, PULL, GAIN = B6.DENSITY, B6.PULL, B6.GAIN
MESSAGES, PARENTS, NCASE = D2.MESSAGES, D2.PARENTS, D2.NCASE
BODY, THETA = "dw", 0.0
ETA, P_B = B6.CLOCKS["F"]["eta"], B6.CLOCKS["F"]["rate"]       # clock F: eta_a = eta = 0.01, bond noise 1e-3
T_STAR = B6.t_star(ETA)                                        # 58.5 updates
DURATION = B6.SIG["duration"]                                  # 1,000 updates
LAM_RATIO = B6.SIG["lam_rest"] / B6.SIG["lam_sig"]             # 3: the signal closes the footprint's junctions to lam / 3
LAM0 = B6.SIG["lam_rest"]                                      # 3
DIL = B6.SIG["d"]                                              # 2
WINDOW, READS = 4000, (1000, 2000, 4000)
WINDOW2, READS2 = 2000, (500, 1000, 2000)
T_READ, T_READ2 = 4000, 2000

# the FIT grid (side 32)
WIDTHS = (4, 8, 16)
SIZES = (2, 4, 8)
COUPLINGS = (0.5, 1.0, 2.0)                                    # lam_rest = 3 c, lam_sig = c
MULTS = (0, 1, 2, 4)                                           # d = round(m T*)
TAUS = (30.0, 300.0, 3000.0)


def delay(m):
    return int(round(m * T_STAR))


def fmt(x):
    return f"{x:g}"


def arm_name(c, m, tau, never=False):
    return f"never-c{fmt(c)}-t{fmt(tau)}" if never else f"dial-c{fmt(c)}-m{fmt(m)}-t{fmt(tau)}"


def arms(couplings=COUPLINGS, mults=MULTS, taus=TAUS, never=True, pairs=None):
    """Every coupling x commitment x delay (or the given (delay multiple, commitment) pairs), then per coupling and
    commitment a 'never' arm (the signal never on) when never."""
    out = []
    for c in couplings:
        for tau in taus:
            for m in mults:
                if pairs is not None and (m, tau) not in pairs:
                    continue
                out.append({"name": arm_name(c, m, tau), "c": c, "lam_rest": LAM0 * c, "lam_sig": LAM0 * c / LAM_RATIO,
                            "m": m, "delay": delay(m), "tau_c": tau, "never": False})
            if never:
                out.append({"name": arm_name(c, None, tau, True), "c": c, "lam_rest": LAM0 * c,
                            "lam_sig": LAM0 * c / LAM_RATIO, "m": None, "delay": 0, "tau_c": tau, "never": True})
    return out


def unit_name(w, side, scale=1, place="random"):
    return f"W{w}_x{side}" + ("" if scale == 1 else f"_r{scale}") + ("" if place == "random" else f"_{place}")


# the TEST stage (side 64, fresh blocks): per coupling three (delay, commitment) pairs: prompt with a long commitment,
# late with a long one, prompt with a short one (late with a short one dropped for cost, before P42)
TEST_MULTS = (0, 2)
TEST_TAUS = (30.0, 3000.0)
TEST_PAIRS = ((0, 3000.0), (2, 3000.0), (0, 30.0))
SIDE_FIT, SIDE_TEST = 32, 64


def _unit(stage, kind, w, side, scale, place, sizes, couplings, dil, mults, taus, never):
    return {"stage": stage, "kind": kind, "w": w, "side": side, "scale": scale, "place": place, "sizes": tuple(sizes),
            "couplings": tuple(couplings), "dil": dil, "mults": tuple(mults), "taus": tuple(taus), "never": never}


UNIT = {}
for _w in WIDTHS:                                              # FIT: side 32, the full grid, 'never' arms reported
    UNIT[unit_name(_w, SIDE_FIT)] = _unit("fit", "fit", _w, SIDE_FIT, 1, "random", SIZES, COUPLINGS, DIL, MULTS, TAUS, True)
for _w in WIDTHS:                                              # transfer: more cells at the same lengths
    UNIT[unit_name(_w, SIDE_TEST)] = _unit("test", "transfer", _w, SIDE_TEST, 1, "random", SIZES, COUPLINGS, DIL,
                                           TEST_MULTS, TEST_TAUS, False)
for _w in WIDTHS:                                              # refinement: every length doubled
    UNIT[unit_name(2 * _w, SIDE_TEST, 2)] = _unit("test", "refine", 2 * _w, SIDE_TEST, 2, "random",
                                                  tuple(2 * s for s in SIZES), tuple(2 * c for c in COUPLINGS), 2 * DIL,
                                                  TEST_MULTS, TEST_TAUS, False)
for _pl in ("mid", "cross"):                                   # geometry: away from walls, or across one
    UNIT[unit_name(16, SIDE_TEST, 1, _pl)] = _unit("test", _pl, 16, SIDE_TEST, 1, _pl, (4, 8), COUPLINGS, DIL,
                                                   TEST_MULTS, TEST_TAUS, False)
FIT_UNITS = tuple(u for u, v in UNIT.items() if v["stage"] == "fit")
TEST_UNITS = tuple(u for u, v in UNIT.items() if v["stage"] == "test")


def unit_arms(unit):
    u = UNIT[unit]
    return arms(u["couplings"], u["mults"], u["taus"], u["never"], None if u["stage"] == "fit" else TEST_PAIRS)


def tasks(stage):
    return [u for u in (FIT_UNITS if stage in ("fit",) else TEST_UNITS if stage == "test" else FIT_UNITS + TEST_UNITS)]


def x_vars(w, L, lam, m, tau):
    return (lam / w, L / lam, m, tau / T_STAR)


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "probe_blocks": PROBE_BLOCKS,
            "debug_blocks": DEBUG_BLOCKS, "purpose": PURPOSE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR,
            "sigma_r": SIGMA_R, "kc": KC, "strength0": STRENGTH0, "density": DENSITY, "pull": PULL, "gain": GAIN,
            "messages": MESSAGES, "parents": PARENTS, "body": BODY, "theta": THETA, "eta": ETA, "p_b": P_B,
            "t_star": T_STAR, "duration": DURATION, "lam_ratio": LAM_RATIO, "lam0": LAM0, "dil": DIL, "window": WINDOW,
            "reads": READS, "window2": WINDOW2, "reads2": READS2, "widths": WIDTHS, "sizes": SIZES,
            "couplings": COUPLINGS, "mults": MULTS, "taus": TAUS, "bodies": {BODY: list(DL.BODIES[BODY])},
            "test_mults": TEST_MULTS, "test_taus": TEST_TAUS, "test_pairs": TEST_PAIRS, "side_fit": SIDE_FIT, "side_test": SIDE_TEST,
            "units": UNIT, "arms": {u: [a["name"] for a in unit_arms(u)] for u in UNIT}}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def stage_blocks(stage, override=None):
    if override is not None:
        lo, hi = override
        if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
            raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
        return list(range(lo, hi))
    return list(IDENTITIES[stage])


def sources(lane):
    files = sorted(f for d in ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001",
                               "be002", "be004", "be005", "be006", "np001", "sm001")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm001.design  ->  sm001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
