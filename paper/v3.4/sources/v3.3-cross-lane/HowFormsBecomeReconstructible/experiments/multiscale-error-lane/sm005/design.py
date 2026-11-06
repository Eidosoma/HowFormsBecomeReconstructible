"""SM005: the reader's lengths, one at a time (SM003's next step 2, SM004's next step 1). DRAFT for the lead's review.

SM002's scaled reader (cg, every length of the reader doubled) reads the doubled tissue as the small reader reads the
half-scale one; SM004's grain-named model under-predicts the late loss under a FIXED reader. SM005 rereads the refined
units' saved final records with readers that double ONE of the reader's lengths at a time: C the body's coupling length
(coupling x 4 at dt 0.1, the gain x G_C to hold the erasure size), E the erasure size (the gain x G_E), B the record's
bond grain (the bonds coarse-grained 2 x 2 and lifted back); beside the base (SM001's successor) and cg (SM002's).
No episode is run and no block is drawn (the lead's constraint, 2 November 2026). See PLAN_SM005.md.
"""
from __future__ import annotations

import hashlib
import json
import math

from sm001 import design as S1D
from sm003 import design as D3
from sm004 import design as D4

STUDY = "SM005"
RUNS = "/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane"
# the saved records, by source: (run root, tag, purpose); each record is reread under its own study's tag and case set
SOURCES = {"sm003/p45": (f"{RUNS}/sm003/p45", D3.PROBE_TAG, "engineering"),
           "sm004/debug": (f"{RUNS}/sm004/debug", D4.TAG, "engineering"),
           "sm004/preflight": (f"{RUNS}/sm004/preflight", D4.TAG, "engineering"),
           "sm003/test": (f"{RUNS}/sm003/test", D3.TAG, "development"),
           "sm004/test": (f"{RUNS}/sm004/test", D4.TAG, "development")}
REFINE = D3.REFINE                                         # W8_x64_r2, W16_x64_r2, W32_x64_r2
STAGES = {"smoke": {"sm003/p45": (900476,)},
          "probe": {"sm003/p45": D3.PROBE_BLOCKS},          # P54: SM003's P45 records, 900476-900479
          "debug": {"sm004/debug": (900472,)},
          "preflight": {"sm004/preflight": D4.IDENTITIES["preflight"]},
          "development": {"sm003/test": D3.IDENTITIES["test"], "sm004/test": D4.IDENTITIES["test"]}}
HALVES = ((900476, 900477), (900478, 900479))              # P54's halves

# the readers (PLAN_SM005.md). The base's parameters are SM001's successor's; every reader's window ends at time 400.
BASE = {"coupling": 1.0, "dt": 0.2, "window": S1D.WINDOW2, "gain_x": 1.0, "sigma": S1D.SIGMA, "eps": S1D.EPS,
        "kr": S1D.KR, "sigma_r": S1D.SIGMA_R, "bonds": "fine"}
G_C_GRID = (1.0, math.sqrt(2), 2.0, 2 * math.sqrt(2))     # C's gain factor: the smallest holding the base's erasure size
G_E_GRID = (1 / math.sqrt(2), 0.5, 1 / (2 * math.sqrt(2)), 0.25)   # E's: the nearest 1 doubling it
# the calibration by the declared rule (probes/results/p54s_sm005_erasure.json, 2 November 15:12Z, before any variant
# value): erasure sizes base 3; C 6, 6, 4, 3 at gain x 1, sqrt 2, 2, 2 sqrt 2; E 3, 4, 6, 8 at x 1/sqrt 2, 1/2,
# 1/(2 sqrt 2), 1/4. B (the bond grain) erases 6, and 5 at every larger gain (p54s_sm005_erasure_b.json): the record with
# 2-site bonds erases on its own, so B is the bond grain with the record's own erasure (disclosed)
G_C = 2 * math.sqrt(2)
G_E = 1 / (2 * math.sqrt(2))
ISLAND_SIZES = (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 24)


def variant(name, g_c=None, g_e=None):
    """A variant's reader parameters (PLAN_SM005.md); g_c and g_e default to the calibrated factors."""
    g_c = G_C if g_c is None else g_c
    g_e = G_E if g_e is None else g_e
    if name == "C":
        return dict(BASE, coupling=4.0 * BASE["coupling"], dt=BASE["dt"] / 2, window=2 * BASE["window"], gain_x=g_c,
                    sigma=BASE["sigma"] / math.sqrt(2), eps=BASE["eps"] / 2, sigma_r=BASE["sigma_r"] / math.sqrt(2))
    if name == "E":
        return dict(BASE, gain_x=g_e)
    if name == "B":
        return dict(BASE, bonds="coarse2")
    raise ValueError(name)


VARIANTS = ("C", "E", "B")
READERS = ("base", "cg") + VARIANTS
STREAM = "dw"                                              # C, E and B draw from the base's stream (paired)

# the statements (PLAN_SM005.md): bands in 0.01 steps by BE002's rule on P54
K_RULE = 3 * math.sqrt(1 / 4 + 1 / 16)
STEP = 0.01
LATE, PROMPT = 2, 0


def design_dict():
    return {"study": STUDY, "sources": SOURCES, "refine": REFINE, "stages": STAGES, "halves": HALVES, "base": BASE,
            "g_c_grid": G_C_GRID, "g_e_grid": G_E_GRID, "g_c": G_C, "g_e": G_E, "island_sizes": ISLAND_SIZES,
            "variants": {v: variant(v) for v in VARIANTS} if G_C is not None and G_E is not None else None,
            "stream": STREAM, "k_rule": K_RULE, "step": STEP, "sm001_digest": S1D.digest(), "sm003_digest": D3.digest(),
            "sm004_digest": D4.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def stage_tasks(stage):
    return [(src, u, b) for src, blocks in STAGES[stage].items() for b in blocks for u in REFINE]


def sources(lane):
    files = sorted(f for d in ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001",
                               "be002", "be004", "be005", "be006", "np001", "sm001", "sm002", "sm003", "sm004", "sm005")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm005.design  ->  sm005/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm005" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
