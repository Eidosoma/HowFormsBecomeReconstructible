"""SM003: a scaling model that names the reader (the PI's "Multiscale 2", with the length SM002 found missing put in).
DRAFT for the lead's review (phase A).

SM001 fitted a model of repair in the lane's ratios x = (lam_rest / w, L / lam_rest, m, tau_c / T*) on 32 x 32 sheets: it
transferred to 64 x 64 sheets at the same lengths and failed under refinement (every declared length doubled). SM002
found the missing length the reader's: a reader whose own lengths double with the tissue's (the half-scale reader at
twice the grain) reads the doubled tissue as the unscaled reader reads the twin.

SM003 names the reader's grain g (the side, in sites, of the reader's cell) in the model: e = log2(L / g), the injury
against the reader's grain, beside SM001's four ratios. The FIT stage is SM001's own FIT records (910628-910643, 32 x 32,
raw float32 records saved) reread at g = 1 (bit for bit SM001's saved successor) and g = 2 (sm002's cg reader), under
SM001's tag; the model and its comparators are fitted on the 648 condition means and frozen; the TEST stage runs SM002's
six units (the transfer twins W4/W8/W16 and the refined W8/W16/W32 at 64 x 64) on fresh blocks, reading every final
record at g = 1, 2 and (where w >= 8) 4. See PLAN_SM003.md and REGISTRATION_SM003.md.
"""
from __future__ import annotations

import hashlib
import json

from sm001 import design as S1D
from sm002 import design as S2D

TAG = "mse-sm003"
PROBE_TAG = "mse-p45"
STUDY = "SM003"
# the lead's assignment (31 October 2026, scanned free at about 20:14Z and again by fork M3 at about 20:25Z; inside
# mse.assay.RANGES): engineering 900476-900487, development 910879-910888 and 910894-910899, reserve 910790-910796
IDENTITIES = {"preflight": (900480, 900481), "test": tuple(range(910879, 910889)) + tuple(range(910894, 910900))}
RESERVE = tuple(range(910790, 910797))
PROBE_BLOCKS = (900476, 900477, 900478, 900479)        # P45, the TEST pilot (tag mse-p45)
DEBUG_BLOCKS = (900482, 900483)                        # preflight debugging
SMOKE_BLOCKS = (900484, 900485)                        # the smoke and the tests
SPARE_BLOCKS = (900486, 900487)
PURPOSE = {"probe": "engineering", "preflight": "engineering", "test": "development"}

# the FIT stage: SM001's own FIT records, reread (no block drawn)
FIT_TAG = S1D.TAG                                      # mse-sm001: the records' cases and draws are SM001's
FIT_BLOCKS = S1D.IDENTITIES["fit"]                     # 910628-910643
FIT_UNITS = S1D.FIT_UNITS                              # W4_x32, W8_x32, W16_x32
FIT_PURPOSE = S1D.PURPOSE["fit"]                       # development
FIT_ROOT = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm001/fit"
FIT_GRAINS = (1, 2)

# the TEST stage: SM002's six units (sm001's units), every final record read at g = 1, 2 and, where w >= 8, 4
REFINE = S2D.REFINE                                    # W8_x64_r2, W16_x64_r2, W32_x64_r2
TWINS = S2D.TWINS                                      # W4_x64, W8_x64, W16_x64 (the transfer units)
UNITS = TWINS + REFINE
GRAINS = (1, 2, 4)
G4_MIN_W = 8                                           # g = 4 only where w / 4 >= 2
STREAMS = {1: S1D.BODY, 2: S2D.CG_STREAM, 4: "dw-cg4"} # each reader's birth and noise addresses (independent)

GAIN, WINDOW2, READS2 = S1D.GAIN, S1D.WINDOW2, S1D.READS2
WINDOW, READS = S1D.WINDOW, S1D.READS
T_STAR = S1D.T_STAR

# the model: logistic(beta . phi) on (a, b, c, d, e) = (log2 lam/w, log2 L/lam, m, log2 tau/T*, log2 L/g); its form chosen
# from the nested candidates by the leave-one-block-out rule fixed in PLAN_SM003.md before any fit was seen
SM001_TERMS = ("1", "a", "b", "c", "d", "a*b", "b^2", "a^2", "c*b", "c*a", "c^2")
CANDIDATES = {"F1": SM001_TERMS + ("e",),
              "F2": SM001_TERMS + ("e", "e*c"),
              "F3": SM001_TERMS + ("e", "e*c", "e^2"),
              "F4": SM001_TERMS + ("e", "e*c", "e^2", "e*a", "e*b")}
SELECT_TOL = 0.002                                     # a smaller candidate within this of the best is chosen
# reported, not in the declared selection: F4 with an indicator k for a coarse reader (g > 1), added after the FIT
# diagnostics (the pure-ratio model biased -0.025 at g 1 and +0.025 at g 2) and before any TEST value was read, for
# the lead's ruling (register F4 as declared, or F5)
SENSITIVITY = {"F5": CANDIDATES["F4"] + ("k",)}
# the comparators: the parametric (a quadratic in A, B, C, M = log2 lam, log2 w, log2 L, m, with G = log2 g linear and in
# its products with the others, plus T = log2 tau linear: 21 terms) and the 4-NN on (log2 lam, log2 w, log2 L, d,
# log2 tau, log2 g), standardised by the FIT SDs. The lead's ruling (31 October 2026, after P45 was read): the draft's
# (log2 g)^2 term is removed. On the FIT's two grains log2 g is 0 or 1, so that column equals log2 g's and only their sum
# is identified; the draft's fit left the pair at +995.1486 and -995.2450, which at g = 4 put the linear predictor near
# -1,990 (a prediction of 0). The 4-NN's squared standardised distances are rounded to NN_ROUND decimals before the
# lexsort, ties then broken by the FIT condition's index: equidistant neighbours are common on the grid, and unrounded
# floating-point order picked different ones under algebraically equal arithmetic.
PAR_VARS = ("A", "B", "C", "M", "G")
PAR_TERMS = (("1",) + PAR_VARS + ("A^2", "B^2", "C^2", "M^2")
             + tuple(f"{PAR_VARS[i]}*{PAR_VARS[j]}" for i in range(5) for j in range(i + 1, 5)) + ("T",))
K_NN = 4
NN_ROUND = 9


def g_ok(w, g):
    """A reader of grain g reads a unit of width w only if the stripes are at least two coarse cells wide (g = 4) and the
    side and width divide (g = 2)."""
    return g == 1 or (g == 2 and w % 2 == 0) or (g == 4 and w >= G4_MIN_W and w % 4 == 0)


def unit(name):
    return S1D.UNIT[name]


def unit_arms(name):
    return S1D.unit_arms(name)


def twin_unit(name):
    return S2D.twin_unit(name)


def unit_grains(name):
    return tuple(g for g in GRAINS if g_ok(S1D.UNIT[name]["w"], g))


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "reserve": RESERVE,
            "probe_blocks": PROBE_BLOCKS, "debug_blocks": DEBUG_BLOCKS, "smoke_blocks": SMOKE_BLOCKS,
            "purpose": PURPOSE, "fit_tag": FIT_TAG, "fit_blocks": FIT_BLOCKS, "fit_units": FIT_UNITS,
            "fit_purpose": FIT_PURPOSE, "fit_grains": FIT_GRAINS, "units": UNITS, "refine": REFINE, "twins": TWINS,
            "grains": GRAINS, "g4_min_w": G4_MIN_W, "streams": STREAMS, "gain": GAIN, "window2": WINDOW2,
            "reads2": READS2, "window": WINDOW, "reads": READS, "candidates": CANDIDATES, "select_tol": SELECT_TOL, "sensitivity": SENSITIVITY,
            "par_vars": PAR_VARS, "par_terms": PAR_TERMS, "k_nn": K_NN, "nn_round": NN_ROUND, "unit_grains": {u: unit_grains(u) for u in UNITS},
            "sm001_units": {u: S1D.UNIT[u] for u in UNITS + FIT_UNITS},
            "arms": {u: [a["name"] for a in unit_arms(u)] for u in UNITS + FIT_UNITS},
            "sm001_digest": S1D.digest(), "sm002_digest": S2D.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def stage_blocks(stage, override=None):
    if override is not None:
        blocks = list(override)
        if stage != "preflight" or not set(blocks) <= set(DEBUG_BLOCKS + SMOKE_BLOCKS):
            raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS or SMOKE_BLOCKS only")
        return blocks
    if stage == "probe":
        return list(PROBE_BLOCKS)
    return list(IDENTITIES[stage])


def sources(lane):
    files = sorted(f for d in ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001",
                               "be002", "be004", "be005", "be006", "np001", "sm001", "sm002", "sm003")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm003.design  ->  sm003/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm003" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
