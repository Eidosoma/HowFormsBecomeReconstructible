"""DL001's registered statements, written before any development outcome.

python -m dl001.predict   (writes dl001/frozen/predictions.json)

Every threshold was set from engineering probes P12 and P12b (32 cases on blocks 900864-900867 under tag mse-p12,
disclosed in REGISTRATION_DL001.md), with margins for the step to 128 cases. Every statement is scored by
dl001.analyze on block means over the 16 development blocks: each block's mean over its 8 cases, then the mean over
blocks. 'sign' is the body's sign agreement with the template over the sheet; 'patch' the same inside the wound;
'spacing' the power-weighted mean wavelength over wavelengths of 4 sites or more.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl001 import design as D  # noqa: E402

STATEMENTS = [
    {"id": "D1", "kind": "design: what comes free", "panel": "F",
     "claim": "A self-organising body imposes its own spacing on every pattern; the double well keeps coarser structure",
     "rule": "HOLDS if in panel F at t = 8000 and sigma = 0.1 (theta x0 and x1, all four patterns) the spacing is within "
             "[6.5, 8.5] for li2 and li4 and above 8.5 for dw (block means), else FAILS",
     "inputs": "P12b: li2 and li4 6.89-8.05 (block SDs <= 0.24); dw 10.05-23.17"},
    {"id": "D2", "kind": "design: what comes free", "panel": "F",
     "claim": "In a quiet, clean tissue a self-organising body holds its native pattern without any record",
     "rule": "HOLDS if in unit S4_s0.1_t0 of panel F sign at t = 8000 is >= 0.98 for li2 and li4 and li4's exceeds dw's "
             "(block means), else FAILS",
     "inputs": "P12: li2 0.994, li4 0.998, dw 0.895 (dw block SD 0.115)"},
    {"id": "D3", "kind": "design: what disorder and noise take", "panel": "F",
     "claim": "With the environmental field or at high noise the native pattern's registration is lost without a record",
     "rule": "HOLDS if in panel F li4's sign on S4 at t = 8000 is <= 0.60 in units S4_s0.1_t1, S4_s0.3_t0 and S4_s0.3_t1, "
             "else FAILS",
     "inputs": "P12: 0.515, 0.504, 0.502"},
    {"id": "D4", "kind": "design is a commitment", "panel": "F,U",
     "claim": "A pattern off the body's scale becomes expensive to hold: free in the double well, out of reach of the "
              "strong self-organising body at a pull that holds everything else",
     "rule": "HOLDS if in unit F0_s0.1_t0 dw's sign at t = 2000 without a record (panel F) is >= 0.95 and li4's sign at "
             "t = 2000 with the held record at gain 0.2 (panel U) is <= 0.85, else FAILS",
     "inputs": "P12: dw 0.993; li4 0.781 (0.948 at gain 0.4, P12b)"},
    {"id": "D5", "kind": "cheap development", "panel": "B",
     "claim": "A native pattern is built from noise by a weak record, with less correction than the double well spends "
              "failing to build it",
     "rule": "HOLDS if in unit S4_s0.1_t0 of panel B at gain 0.05 sign at t = 2000 is >= 0.98 for li2 and li4 and <= 0.80 "
             "for dw, and li4's correction work is below dw's, else FAILS",
     "inputs": "P12: li2 0.999, li4 1.000, dw 0.587; work 0.0017 against 0.0082"},
    {"id": "D6", "kind": "free repair", "panel": "W",
     "claim": "Without any record a self-organising body repairs wounds in its native pattern, reset and flipped, which "
              "the double well does not",
     "rule": "HOLDS if in unit S4_s0.1_t0 of panel W without a record, patch at t = 2000 inside an 8 x 8 reset wound is "
             ">= 0.95 for li2 and li4 and <= 0.70 for dw, and inside an 8 x 8 flipped wound >= 0.85 for li4 and <= 0.50 "
             "for dw, else FAILS",
     "inputs": "P12: reset li2 0.994, li4 1.000, dw 0.507 (block SD 0.136); flip li4 0.952 (SD 0.056), dw 0.354"},
    {"id": "D7", "kind": "design: what disorder takes", "panel": "F,U,W",
     "claim": "Under the environmental field the self-organising body's advantage for registration and repair is gone",
     "rule": "HOLDS if in unit S4_s0.1_t1 |li4 - dw| sign at t = 2000 is <= 0.08 without a record (panel F) and at every "
             "gain of panel U, and in panel W li4's patch at t = 2000 inside an 8 x 8 reset wound without a record is "
             "<= 0.60, else FAILS",
     "inputs": "P12: largest difference 0.050; patch 0.489"},
    {"id": "D8", "kind": "the reversed match", "panel": "X",
     "claim": "What comes free follows the match between pattern and body: a body tuned to period 16 holds period 16 and "
              "not period 64, as the period-8 body holds period 8 and not period 16",
     "rule": "HOLDS if in panel X (64-site sheet, theta x0, sigma 0.1) without a record at t = 8000 li16's sign is >= 0.95 "
             "on S8 and <= 0.80 on F0, and li4's is >= 0.95 on S4 and <= 0.70 on S8, else FAILS",
     "inputs": "P12b: li16 1.000 and 0.666; li4 0.998 and 0.509"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
