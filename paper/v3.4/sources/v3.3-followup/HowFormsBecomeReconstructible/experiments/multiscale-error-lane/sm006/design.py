"""SM006: the reader's erasure size in the scaling model (SM005's next step 1). DRAFT for the lead's review (phase A).

SM004's model (H1 = F4 + G) under-predicts the late loss under a fixed reader at the doubled scale; SM005 found the
reader's erasure size carries it. SM006 varies the erasure size at fixed grain and coupling through the gain (SM005's E
calibration), rereads SM001's FIT records with it, selects a model naming the erasure size by leave-one-block-out on FIT,
freezes it, and tests it on the 32 TEST blocks' saved records, reread. No block is drawn. See PLAN_SM006.md.
"""
from __future__ import annotations

import hashlib
import json
import math

from sm001 import design as S1D
from sm003 import design as D3
from sm004 import design as D4
from sm005 import design as D5

STUDY = "SM006"
RUNS = D5.RUNS
F_GRID = (0.5, 1 / (2 * math.sqrt(2)), 0.25)              # the gain factors: erasure 4, 6, 8 at side 64 and g 1 (SM005)
F_NAME = {1.0: "f1", 0.5: "f2", 1 / (2 * math.sqrt(2)): "f2r2", 0.25: "f4"}
FIT_GRAINS_VAR = (1, 2)                                    # the FIT's gain variants at g 1 and g 2
FIT_MS = (0, 2)                                            # on the dial arms with m 0 and 2 (the TEST signals)
TEST_FACTORS = {"transfer": F_GRID, "refine": (0.5, 0.25)}  # new g-1 reads; E(6) on the refined units is SM005's
SOURCES = D5.SOURCES                                       # the saved TEST-shape records (SM003's, SM004's)
SM005_ROOTS = {"sm003/p45": f"{RUNS}/sm005/probe", "sm004/debug": f"{RUNS}/sm005/debug",
               "sm004/preflight": f"{RUNS}/sm005/preflight", "sm003/test": f"{RUNS}/sm005/development",
               "sm004/test": f"{RUNS}/sm005/development"}
UNITS = D3.UNITS
STAGES = {"probe": {"sm003/p45": D3.PROBE_BLOCKS},          # P55: SM003's P45 records
          "debug": {"sm004/debug": (900472,)},
          "preflight": {"sm004/preflight": D4.IDENTITIES["preflight"]},
          "development": {"sm003/test": D3.IDENTITIES["test"], "sm004/test": D4.IDENTITIES["test"]}}
HALVES = ((900476, 900477), (900478, 900479))
ISLAND_SIZES = {32: (1, 2, 3, 4, 5, 6, 8, 10, 12, 16), 64: D5.ISLAND_SIZES}
# the erasure sizes, measured by SM002's island test before any fit (probes/results/p55s_sm006_erasure_32.json and _64.json,
# 2 November 17:41:45-17:46:29Z); "side/g/f". At side 64 the g-1 rows equal SM005's exactly. Three values are censored at the
# largest island tested (agreement still >= 0.5 there, so the erasure is at least that): g 4 at side 32 (16; 0.64) and at
# side 64 (24; 0.5625), and g 2 at gain x 1/4 at side 32 (16; 0.72; at side 64 it is 16 uncensored, 0.59 at 16, 0.22 at
# 24). At side 32 the g-1 reader at gain x 1/4 erases 6 (agreement 0.29 at 8); at side 64 it erases 8 (0.60 at 8)
EPS = {"32/1/f1": 3, "32/1/f2": 4, "32/1/f2r2": 6, "32/1/f4": 6, "32/2/f1": 8, "32/2/f2": 10, "32/2/f2r2": 12, "32/2/f4": 16,
       "32/4/f1": 16,
       "64/1/f1": 3, "64/1/f2": 4, "64/1/f2r2": 6, "64/1/f4": 8, "64/2/f1": 8, "64/2/f2": 10, "64/2/f2r2": 12, "64/2/f4": 16,
       "64/4/f1": 24}

# the model family (PLAN_SM006.md): z = log2(eps / g), e_eps = log2(L / eps)
H1 = D4.CANDIDATES["H1"]
F4_EPS = tuple(t.replace("e", "E") if t in ("e", "e*c", "e^2", "e*a", "e*b") else t for t in D3.CANDIDATES["F4"])
CANDIDATES = {"J0": H1,
              "J1": H1 + ("z",),
              "J2": H1 + ("z", "z*c"),
              "J3": H1 + ("z", "z*c", "z*e"),
              "J4": F4_EPS + ("G",),
              "J5": F4_EPS + ("G", "z"),
              "J6": F4_EPS + ("G", "z", "z*c")}
SELECT_TOL = 0.002
COND_MAX = 1000.0
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP = 0.01


def eps(side, g, f):
    return EPS[f"{side}/{g}/{F_NAME[f]}"]


def design_dict():
    return {"study": STUDY, "f_grid": F_GRID, "fit_grains_var": FIT_GRAINS_VAR, "fit_ms": FIT_MS,
            "test_factors": TEST_FACTORS, "sources": SOURCES, "sm005_roots": SM005_ROOTS, "units": UNITS, "stages": STAGES,
            "halves": HALVES, "island_sizes": ISLAND_SIZES, "eps": EPS, "candidates": CANDIDATES, "select_tol": SELECT_TOL,
            "cond_max": COND_MAX, "k_rule": K_RULE, "step": STEP, "sm004_digest": D4.digest(), "sm005_digest": D5.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def reread_digest():
    """The design's digest with EPS blanked: the FIT gain rereads (sm006.fitread) never read EPS, which enters only the
    analysis, so their shards, done records and resume key carry this one. It equals the design's digest before EPS was
    set (0a422b0fe0cd...), under which 32 of the 48 FIT tasks ran before the session stall at about 17:58Z on 2 November."""
    d = dict(design_dict(), eps=None)
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def stage_tasks(stage):
    return [(src, u, b) for src, blocks in STAGES[stage].items() for b in blocks for u in UNITS]


def sources(lane):
    files = sorted(f for d in ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001",
                               "be002", "be004", "be005", "be006", "np001", "sm001", "sm002", "sm003", "sm004", "sm005",
                               "sm006")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm006.design  ->  sm006/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm006" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
