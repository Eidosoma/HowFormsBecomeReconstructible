"""SM004: the reader's grain as itself (SM003's Next 1). DRAFT for the lead's review (phase A).

SM003's frozen model F4 names the reader only through e = log2(L / g), the injury against the reader's grain. At equal
ratios a coarser reader read better than it predicts (M4 +0.049, M5 +0.055; the g-2 offset R1 +0.047; the g-4 shortfall
M7 +0.090). SM004 adds G = log2 g as a term of its own, with its products where the FIT stage identifies them, to SM003's
model in the ratios; refits it on SM001's FIT records read at three grains (g 1 and 2: SM003's rereads; g 4: new, where
w >= 8, by SM003's g-4 rule); and tests it on fresh blocks against F4 (frozen) and the comparators. The TEST task is
sm003.worker.task unchanged under SM004's tag. P52 is SM003's P45 records, reread (the lead's ruling). See PLAN_SM004.md.
"""
from __future__ import annotations

import hashlib
import json
import math

from sm001 import design as S1D
from sm003 import design as D3

TAG = "mse-sm004"
STUDY = "SM004"
# fork H1's scan (1 November 2026, 23:27:45Z; PLAN_SM004.md): engineering 900468-900475, development 910617-910627,
# 910859-910861 and 910890-910891 (TEST), 910545-910547 and 910892-910893 (reserve); inside mse.assay.RANGES
IDENTITIES = {"preflight": (900470, 900471),
              "test": tuple(range(910617, 910628)) + (910859, 910860, 910861, 910890, 910891)}
RESERVE = (910545, 910546, 910547, 910892, 910893)
SMOKE_BLOCKS = (900468, 900469)                        # the smoke, the tests
DEBUG_BLOCKS = (900472, 900473)                        # preflight debugging
SPARE_BLOCKS = (900474, 900475)
PURPOSE = {"preflight": "engineering", "test": "development"}

# P52: SM003's P45 records reread (the lead's ruling, 1 November 2026); no block drawn. One task is rerun under SM004's
# code before P52 is read and must equal P45's shard and raw record bit for bit.
PROBE_ROOT = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm003/p45"
PROBE_TAG = D3.PROBE_TAG                               # mse-p45
PROBE_BLOCKS = D3.PROBE_BLOCKS                         # 900476-900479
PROBE_PURPOSE = "engineering"
PROBE_BRIDGE = ("W8_x64", 900476)                      # carries all three grains
HALVES = ((900476, 900477), (900478, 900479))

# the FIT stage: SM001's FIT records at three grains (no block drawn)
FIT_TAG = D3.FIT_TAG                                   # mse-sm001
FIT_BLOCKS = D3.FIT_BLOCKS                             # 910628-910643
FIT_UNITS = D3.FIT_UNITS                               # W4_x32, W8_x32, W16_x32
FIT_PURPOSE = D3.FIT_PURPOSE
FIT_ROOT = D3.FIT_ROOT                                 # SM001's FIT records (raw float32, shards, manifest)
FIT12_ROOT = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm003/fit_reread"   # SM003's g 1 and 2
FIT_GRAINS = (1, 2, 4)
FIT_G4_UNITS = tuple(u for u in FIT_UNITS if D3.g_ok(S1D.UNIT[u]["w"], 4))                  # W8_x32, W16_x32

# the TEST stage: SM003's six units and readers, unchanged
UNITS, REFINE, TWINS, GRAINS, STREAMS = D3.UNITS, D3.REFINE, D3.TWINS, D3.GRAINS, D3.STREAMS
T_STAR = D3.T_STAR

# the model family (PLAN_SM004.md, fixed before any fit): logistic(beta . phi) on SM003's (a, b, c, d, e) and G = log2 g
F4_TERMS = D3.CANDIDATES["F4"]
CANDIDATES = {"H0": F4_TERMS,
              "H1": F4_TERMS + ("G",),
              "H2": F4_TERMS + ("G", "G*c"),
              "H3": F4_TERMS + ("G", "G*c", "G*e"),
              "H4": F4_TERMS + ("G", "G*c", "G*e", "G^2"),
              "H5": F4_TERMS + ("G", "G*c", "G*e", "G^2", "G*a", "G*b"),
              "H6": F4_TERMS + ("G", "G*c", "G*e", "G^2", "G*a", "G*b", "G*d")}
SELECT_TOL = D3.SELECT_TOL                             # 0.002, SM003's
COND_MAX = 1000.0                                      # admissible: full rank, condition number <= this (standardised)
# the comparators, refitted on SM004's FIT means: SM003's 21-term parametric and its 4-NN; reported, the parametric with
# (log2 g)^2, identified on three grains
PAR_TERMS = D3.PAR_TERMS
PAR_TERMS_G2 = D3.PAR_TERMS + ("G^2",)
K_NN, NN_ROUND = D3.K_NN, D3.NN_ROUND

# the rule (BE002's): margin K_RULE SD on P52 and both halves; thresholds in STEP; N8/N9 register only above N89_MIN,
# N10 only at N10_MIN or higher
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP = 0.01
N89_MIN = 0.0
N10_MIN = -0.03


def unit_grains(name):
    return D3.unit_grains(name)


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "reserve": RESERVE, "smoke_blocks": SMOKE_BLOCKS,
            "debug_blocks": DEBUG_BLOCKS, "spare_blocks": SPARE_BLOCKS, "purpose": PURPOSE, "probe_root": PROBE_ROOT,
            "probe_tag": PROBE_TAG, "probe_blocks": PROBE_BLOCKS, "probe_bridge": PROBE_BRIDGE, "halves": HALVES,
            "fit_tag": FIT_TAG, "fit_blocks": FIT_BLOCKS, "fit_units": FIT_UNITS, "fit_root": FIT_ROOT,
            "fit12_root": FIT12_ROOT, "fit_grains": FIT_GRAINS, "fit_g4_units": FIT_G4_UNITS, "units": UNITS,
            "grains": GRAINS, "streams": STREAMS, "candidates": CANDIDATES, "select_tol": SELECT_TOL,
            "cond_max": COND_MAX, "par_terms": PAR_TERMS, "par_terms_g2": PAR_TERMS_G2, "k_nn": K_NN,
            "nn_round": NN_ROUND, "k_rule": K_RULE, "step": STEP, "n89_min": N89_MIN, "n10_min": N10_MIN,
            "unit_grains": {u: unit_grains(u) for u in UNITS}, "sm003_digest": D3.digest(), "sm001_digest": S1D.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def stage_blocks(stage, override=None):
    if override is not None:
        blocks = list(override)
        if stage != "preflight" or not set(blocks) <= set(DEBUG_BLOCKS + SMOKE_BLOCKS):
            raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS or SMOKE_BLOCKS only")
        return blocks
    return list(IDENTITIES[stage])


def sources(lane):
    files = sorted(f for d in ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001",
                               "be002", "be004", "be005", "be006", "np001", "sm001", "sm002", "sm003", "sm004")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm004.design  ->  sm004/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm004" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
