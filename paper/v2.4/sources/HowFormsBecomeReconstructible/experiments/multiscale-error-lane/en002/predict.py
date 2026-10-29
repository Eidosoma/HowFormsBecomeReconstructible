"""EN002's registered statements, written before any development outcome.

python -m en002.predict   (writes en002/frozen/predictions.json)

Every threshold was set from engineering probe P15 (32 cases on blocks 900884-900887 under tag mse-p15, disclosed in
REGISTRATION_EN002.md), with margins for the step to 128 cases. Every statement is scored by en002.analyze on block
means over the 16 development blocks: each block's mean over its 8 cases, then the mean over blocks. 'sign' is the
body's sign agreement with the template over the sheet; 'patch' the same inside the wound; 'spacing' DL001's
power-weighted mean wavelength over wavelengths of 4 sites or more. t = 2000 is the end of starvation; t = 3000 is
after 1,000 updates of recovery at the full budget. Budgets: B = every drift paid, thermal noise; C = every drift
paid, activity-driven noise; the number is phi.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from en002 import design as D  # noqa: E402

STATEMENTS = [
    {"id": "E1", "kind": "the noise decides", "panel": "G",
     "claim": "Thermal starvation erases the native stripes' placement in every body; starvation with activity-driven noise does not",
     "rule": "HOLDS if in unit S4_t0 of panel G without a record, sign at t = 2000 is <= 0.60 at B0.1 and >= 0.95 at C0.1 "
             "for dw, li2 and li4 (block means), else FAILS",
     "inputs": "P15: B0.1 0.502-0.513; C0.1 0.978 (dw, block SD 0.026), 0.989, 0.995"},
    {"id": "E2", "kind": "design survives starvation", "panel": "G",
     "claim": "The spacing lives in the physics: after thermal starvation it returns in full in the self-organising bodies, "
              "whose placement does not return; the double well's fine stripes coarsen",
     "rule": "HOLDS if in unit S4_t0 of panel G without a record, spacing at t = 3000 is within [7.0, 9.0] for li2 and li4 at "
             "B0.5, B0.25 and B0.1, and >= 10 for dw at all three; and sign at t = 3000 at B0.1 is <= 0.60 for li2 and li4, "
             "else FAILS",
     "inputs": "P15: li 7.80-7.99 (block SDs <= 0.07); dw 12.59 (SD 2.39), 17.52, 18.51; li sign 0.486, 0.495"},
    {"id": "E3", "kind": "self-repair after mild starvation", "panel": "G",
     "claim": "After mild thermal starvation a self-organising body re-registers its native stripes on recovery; the double "
              "well does not",
     "rule": "HOLDS if in unit S4_t0 of panel G without a record at B0.5, sign at t = 3000 is >= 0.95 for li4 and >= 0.90 "
             "for li2 and exceeds each body's sign at t = 2000, while dw's sign at t = 3000 is <= 0.85 and at most 0.02 above "
             "its sign at t = 2000, else FAILS",
     "inputs": "P15: li4 0.922 -> 0.986; li2 0.878 -> 0.954; dw 0.797 -> 0.755 (block SD 0.046)"},
    {"id": "E4", "kind": "the record outlives expression", "panel": "G",
     "claim": "With the held record, registration after thermal starvation at a tenth of the budget returns to its "
              "unstarved level in every body and unit",
     "rule": "HOLDS if with the held record |sign at t = 3000 at B0.1 - sign at t = 3000 at base| <= 0.02 for dw, li2 and "
             "li4 in all four units of panel G, else FAILS",
     "inputs": "P15: largest difference 0.008 (dw, S4_t1)"},
    {"id": "E5", "kind": "repair is what an activity budget costs", "panel": "W",
     "claim": "Starvation with activity-driven noise slows the self-organising body's free repair, which completes on recovery",
     "rule": "HOLDS if in unit S4_t0 of panel W without a record, li4's patch under C0.1 is at least 0.10 below its base "
             "level at t = 500 inside the reset 8 x 8 wound, and <= 0.70 at t = 2000 inside the flipped 8 x 8 wound (base "
             ">= 0.90 there), and at t = 3000 >= 0.95 (reset) and >= 0.80 (flipped), else FAILS",
     "inputs": "P15: reset 0.807 against 0.981 at t = 500, 0.997 at t = 3000; flipped 0.461 against 0.947 at t = 2000, "
               "0.907 at t = 3000 (block SD 0.067)"},
    {"id": "E6", "kind": "heat takes the free repair", "panel": "W",
     "claim": "Thermal starvation destroys the self-organising body's free repair for good unless a record holds the pattern",
     "rule": "HOLDS if in unit S4_t0 of panel W at B0.1, li4's patch at t = 3000 is <= 0.60 without a record and >= 0.98 "
             "with the held record, for the reset and the flipped 8 x 8 wound, else FAILS",
     "inputs": "P15: 0.481 and 0.485 without; 1.000 and 1.000 with"},
    {"id": "E7", "kind": "who keeps registration through heat", "panel": "G",
     "claim": "Through thermal starvation the held record keeps more of the double well's registration than of the "
              "self-organising bodies'",
     "rule": "HOLDS if in unit S4_t0 of panel G with the held record at B0.1, dw's sign at t = 2000 exceeds li2's and "
             "li4's by >= 0.02, else FAILS",
     "inputs": "P15: dw 0.869, li4 0.829, li2 0.814 (block SDs <= 0.005)"},
    {"id": "E8", "kind": "what heat takes first", "panel": "G",
     "claim": "Coarse native patterns survive heating better than fine ones: the double well's two domains keep most of "
              "their placement through thermal starvation, the period-8 body's stripes lose theirs",
     "rule": "HOLDS if without a record at B0.1, dw's sign on F0 (unit F0_t0) is >= 0.70 at t = 2000 and >= 0.85 at "
             "t = 3000, while li4's sign on S4 (unit S4_t0) is <= 0.60 at both, else FAILS",
     "inputs": "P15: dw F0 0.791 and 0.912; li4 S4 0.503 and 0.495"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
