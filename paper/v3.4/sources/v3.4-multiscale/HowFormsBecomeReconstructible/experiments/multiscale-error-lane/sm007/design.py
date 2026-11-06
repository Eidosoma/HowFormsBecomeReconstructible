"""SM007's design: geometry and a shared field (PLAN_SM007.md; the PI's go, 5 November 2026; amended to the lead's ruling
on the emission and response, sent 12:26:39Z, shared with E2E006).

Fresh recipients (newborn dl001 bodies of the AR tissue) each read a fixed inherited record (the restored acquired
record R0) for one window, under a paired disturbance: the reading gain cut to G_DIST. Each sheet's stress is its mean
|r - V-tilde| over its cells (the record's pull on its body; E2E006's function, e2e006.sim.FieldAdapter.stress); it emits
that into a shared msefield medium; its reading gain is G_DIST x (1 + KAPPA x exposure), the exposure sampled at the
previous update. Groups of sheets sit on a square lattice in declared shapes, boundaries and decay lengths; the controls
are isolated sheets (one Medium of disconnected blocks), the group's mean exposure (uniform), the exposures permuted within
the group (rearranged), no field, and the undisturbed gain.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ar001 import design as A
from msefield.core import rectangle

STUDY = "SM007"
TAG = "mse-sm007"                      # the recipients' births and noise (debug, preflight, development)
PROBE_TAG = "mse-p61"                  # the pilot P61's (and P61k's)
RUNS = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane"

# ---------------------------------------------------------------- the tissue: the AR tissue's body and its clock
SIDE, SIGMA, CHUNK = A.SIDE, A.SIGMA, A.CHUNK
WINDOW = 8000                          # one generation of the E2E studies
READS = (1000, 2000, 4000, 8000)
PAIRS = (("dw", "S4_t1"), ("dw", "F0_t1"), ("li4", "S4_t1"), ("li4", "F0_t1"))   # theta x 1: the reading decides
RESCUED = 0.95                         # a sheet is rescued when its sign agreement with the template is at least this

# ---------------------------------------------------------------- the disturbance, the stress and the response
G_DIST = 0.05                          # the disturbed reading gain (the paper's teratogen; the lane's gain is G_LANE)
G_LANE = 0.2                           # the undisturbed gain: the "undisturbed" control only
STRESS = "a sheet's mean |r - V-tilde| over its cells (the record's pull on its body, per unit gain): its own state only"
EMISSION = "equal to the stress"
RESPONSE = "the body's reading gain x (1 + KAPPA x exposure), the exposure sampled at the previous update"
KAPPA = 1.5176391455197606             # P61k, 12:45:36Z (engineering, nothing scored): 1 / the reference's mean exposure 0.658918
KAPPA_RULE = ("KAPPA x the reference configuration's mean exposure = 1, the mean over the sheets, the 8,000 updates and "
              "the four theta x 1 tasks of AR005's debug block 900799, at kappa 0 (the field computed, no response), "
              "nothing scored (P61k)")

# ---------------------------------------------------------------- the field (msefield, fb934f1f10, unchanged)
GAMMA = 0.0625                         # first-order decay per update (E2E006's); D = GAMMA lambda^2 at every lambda
LAMBDA = 0.5                           # the main decay length, in sheet spacings
LAMBDA2 = 0.4                          # the second (the collapse test): iso8 here meets 1x2 at LAMBDA in L_eff / lambda
LAMBDA_SHARED = 2.0                    # E2E006's (D 0.25): the shared point and the reference configuration
SITES = {LAMBDA: 8, LAMBDA2: 10, LAMBDA_SHARED: 4}   # m: h = lambda / 4 at 0.5 and 0.4; E2E006's m 4 at 2
MARGIN = 0
LEAKS = {"absorbing": 1.0, "half": 0.5, "sealed": 0.0}


def d_field(lam):
    return GAMMA * lam ** 2


# ---------------------------------------------------------------- shapes (lattice cells)
SHAPES = {"iso8": [(0, 2 * j) for j in range(8)],   # eight disconnected cells: the isolated control (E2E006's positions)
          "1x2": rectangle(1, 2), "2x2": rectangle(2, 2), "1x4": rectangle(1, 4), "2x4": rectangle(2, 4),
          "1x8": rectangle(1, 8),
          "1x3": rectangle(1, 3), "2x3": rectangle(2, 3), "1x6": rectangle(1, 6),
          "L4": [(0, 0), (1, 0), (2, 0), (2, 1)], "T4": [(0, 0), (0, 1), (0, 2), (1, 1)],
          "plus5": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)], "L6": [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2)],
          "sq8": [(r, c) for r in range(3) for c in range(3) if (r, c) != (2, 2)]}
PILOT_SHAPES = ("iso8", "1x2", "2x2", "1x4", "2x4", "1x8")
NEW_SHAPES = ("1x3", "2x3", "1x6", "L4", "T4", "plus5", "L6", "sq8")
REFERENCE = "2x4/absorbing/shared"     # rectangle(2, 4), D 0.25, gamma 0.0625, leak 1, m 4, margin 0: E2E006's shared row


# ---------------------------------------------------------------- arrangements: (label, shape, boundary, kind, lambda)
#   kind: "field" (each sheet's own exposure), "uniform" (the group's mean exposure, every update), "rearranged" (the
#   group's exposures permuted among its sheets by a fixed derangement), "nofield" (G_DIST throughout, no medium),
#   "undisturbed" (G_LANE throughout, no medium)
def _pilot_set():
    L1, L2, LS = LAMBDA, LAMBDA2, LAMBDA_SHARED
    out = [(f"{s}/{b}", s, b, "field", L1) for s in PILOT_SHAPES for b in ("absorbing", "sealed")]
    out += [(f"{s}/half", s, "half", "field", L1) for s in ("2x4", "1x8")]
    out += [(f"{s}/absorbing/{k}", s, "absorbing", k, L1) for s in ("2x4", "1x8") for k in ("uniform", "rearranged")]
    out += [(f"{s}/absorbing/l2", s, "absorbing", "field", L2) for s in PILOT_SHAPES]
    out += [(f"{s}/absorbing/shared", s, "absorbing", "field", LS) for s in ("iso8", "2x4", "1x8")]
    out += [("2x4/sealed/shared", "2x4", "sealed", "field", LS)]
    out += [("nofield", "iso8", None, "nofield", None), ("undisturbed", "iso8", None, "undisturbed", None)]
    return tuple(out)


PILOT_SET = _pilot_set()
NEW_SET = (tuple((f"{s}/{b}", s, b, "field", LAMBDA) for s in NEW_SHAPES for b in ("absorbing", "sealed"))
           + tuple((f"{s}/absorbing/l2", s, "absorbing", "field", LAMBDA2) for s in NEW_SHAPES))
# ---------------------------------------------------------------- Amendment 2 (the lead's phase-A rulings, 13:01:00Z):
#   the paper's own stress as a reported arm. Manicka and Levin, Eq. 1: dS_i/dt = P_max S_i^n / (K^n + S_i^n) - delta_S S_i
#   (per second; n 2, P_max 0.2 /s, K 0.5, delta_S 0.1 /s), stepped k = 500 times per bio-step of 58 ms each (29 s); here
#   one bio-step is one tissue update. S_i(0) ~ N(0.3, 0.1) truncated below at the separatrix S* (redrawn), addressed per
#   case and future. The stress never reads the body, the record or the template; the emission equals it and the response
#   is the ruled one, with its own KAPPA_PAPER fixed by the same rule at the same reference configuration (P61p).
PAPER = {"P_max": 0.2, "K": 0.5, "n": 2, "delta_S": 0.1, "dt_sub": 0.058, "k": 500, "mu0": 0.3, "sd0": 0.1}


def paper_fixed_points(P=PAPER):
    """Eq. 1's separatrix and high state for n = 2: the roots of delta_S S^2 - P_max S + delta_S K^2 = 0."""
    a, b, c = P["delta_S"], -P["P_max"], P["delta_S"] * P["K"] ** 2
    disc = math.sqrt(b * b - 4 * a * c)
    return (-b - disc) / (2 * a), (-b + disc) / (2 * a)


PAPER_SSTAR, PAPER_SHIGH = paper_fixed_points()
KAPPA_PAPER = 0.4463801628467049     # P61p, 13:09:11Z (engineering, no body simulated): 1 / the reference's mean exposure 2.24024
KAPPA_PAPER_RULE = ("KAPPA_PAPER x the reference configuration's mean exposure under the paper's stress = 1, the mean over "
                    "its eight sheets and the 8,000 updates of AR005's debug block 900799's cases under the probe tag, "
                    "future 0 (the stress never reads the body, so the four tasks' exposures are identical) (P61p)")
PAPER_SET = tuple((f"{s}/{b}/paper", s, b, "paper", LAMBDA)
                  for s, b in (("iso8", "absorbing"), ("2x4", "absorbing"), ("2x4", "sealed"), ("1x8", "absorbing")))
STAGE_SETS = {"probe": PILOT_SET, "debug": PILOT_SET + NEW_SET + PAPER_SET, "preflight": PILOT_SET + NEW_SET + PAPER_SET,
              "development": PILOT_SET + NEW_SET + PAPER_SET}
STAGE_WINDOW = {"debug": 2000}         # the debug run is short; every code path runs by then

# ---------------------------------------------------------------- the restored records (AR005's) and the stages
SOURCES = {"ar005/p53": {"root": f"{RUNS}/ar005/p53", "tag": "mse-p53", "purpose": "engineering"},
           "ar005/debug": {"root": f"{RUNS}/ar005/debug", "tag": "mse-ar005", "purpose": "engineering"},
           "ar005/preflight": {"root": f"{RUNS}/ar005/preflight", "tag": "mse-ar005", "purpose": "engineering"},
           "ar005/development": {"root": f"{RUNS}/ar005/development", "tag": "mse-ar005", "purpose": "development"}}
AR005_DEV = (910138, 910139, 910699, 910717, 910718, 910719, 910782, 910783, 910785, 910786, 910787, 910798, 910799,
             910826, 910827, 910958)
STAGES = {"probe": {"ar005/p53": (900729, 900739, 900749, 900759)},
          "debug": {"ar005/debug": (900799,)},
          "preflight": {"ar005/preflight": (900779, 900789)},
          "development": {"ar005/development": AR005_DEV}}
KAPPA_STAGE = {"ar005/debug": (900799,)}           # P61k's records (engineering; nothing scored)
STAGE_TAG = {"probe": PROBE_TAG, "debug": TAG, "preflight": TAG, "development": TAG}
FUTURES = {"probe": 1, "debug": 2, "preflight": 2, "development": 2}   # Amendment 2: a second future (debug: its code path)
HALVES = {"probe": ((900729, 900739), (900749, 900759)), "development": (AR005_DEV[:8], AR005_DEV[8:])}
ITEM_SETS = {"native": (("li4", "S4_t1"),), "particular": (("li4", "F0_t1"),), "permissive": (("dw", "S4_t1"), ("dw", "F0_t1"))}

# the statements' rule (BE002's, the lane's)
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP, STEP_NEAR0 = 0.01, 0.005
AT_MOST_MAX = 0.05


def stage_tasks(stage):
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b, u in PAIRS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "side": SIDE, "sigma": SIGMA, "chunk": CHUNK,
            "window": WINDOW, "reads": READS, "pairs": PAIRS, "rescued": RESCUED, "g_dist": G_DIST, "g_lane": G_LANE,
            "stress": STRESS, "emission": EMISSION, "response": RESPONSE, "kappa": KAPPA, "kappa_rule": KAPPA_RULE,
            "gamma": GAMMA, "lambda": LAMBDA, "lambda2": LAMBDA2, "lambda_shared": LAMBDA_SHARED,
            "sites": {str(k): v for k, v in SITES.items()}, "margin": MARGIN, "leaks": LEAKS, "shapes": SHAPES,
            "pilot_shapes": PILOT_SHAPES, "new_shapes": NEW_SHAPES, "reference": REFERENCE, "stage_sets": STAGE_SETS,
            "stage_window": STAGE_WINDOW, "sources": SOURCES, "stages": STAGES, "kappa_stage": KAPPA_STAGE,
            "stage_tag": STAGE_TAG, "futures": FUTURES, "halves": HALVES, "item_sets": ITEM_SETS, "k_rule": K_RULE,
            "paper": PAPER, "paper_sstar": PAPER_SSTAR, "paper_shigh": PAPER_SHIGH, "kappa_paper": KAPPA_PAPER,
            "kappa_paper_rule": KAPPA_PAPER_RULE, "paper_set": PAPER_SET,
            "step": STEP, "step_near0": STEP_NEAR0, "at_most_max": AT_MOST_MAX}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    """Every source the recipients' arithmetic and the restoration can reach (E2E004's list, with msefield and sm007)."""
    lane = Path(lane)
    dirs = ("mse", "msegrid", "msefield", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002",
            "be005", "be006", "gc001", "np001", "ar001", "sm007")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm007.design  ->  sm007/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm007" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
