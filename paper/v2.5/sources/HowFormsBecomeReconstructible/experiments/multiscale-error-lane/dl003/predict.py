"""DL003's registered statements, written before any development outcome.

python -m dl003.predict   (writes dl003/frozen/predictions.json)

Thresholds were set from engineering probes P16 and P16b (32 cases on blocks 900720-900723 under tag mse-p16,
disclosed in REGISTRATION_DL003.md), with margins for 128 cases. Scored by dl003.analyze on block means over the 16
development blocks, at t = 4,000. 'sign' is the body's agreement with the template over the sheet. 'far' is the
agreement on the four lines farthest from an arm's boundary (distances 12-15 across it); 'near' on its own two lines
and their neighbours (distances 0-1); 'beyond' the mean over distances 8-15 of the arm's agreement minus the none arm's
agreement on the same distance map. theta x0, x0.25, x0.5, x1 scale the environmental field (spread 0.15-0.30 at x1).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl003 import design as D  # noqa: E402

STATEMENTS = [
    {"id": "B1", "kind": "growth from a boundary registers the whole pattern", "panel": "B",
     "claim": "In quiet tissue, stripes grown slowly out from a boundary across them are registered across the whole sheet",
     "rule": "HOLDS if on li4 at theta x0, perp/f100's sign is >= 0.97 and its far agreement >= 0.95, else FAILS",
     "inputs": "P16: sign 0.998, far 0.997"},
    {"id": "B2", "kind": "without growth a boundary reaches only its neighbourhood", "panel": "B",
     "claim": "Built everywhere at once, the same boundary registers only the stripes near it",
     "rule": "HOLDS if on li4 at theta x0, perp's sign is <= 0.80 and its far agreement <= 0.65, and perp/f100 - perp "
             "in sign is >= 0.20, else FAILS",
     "inputs": "P16: sign 0.687, far 0.505; difference 0.311"},
    {"id": "B3", "kind": "a grown boundary beats scattered cells in quiet tissue", "panel": "B",
     "claim": "In quiet tissue a boundary that the pattern grows out from registers it better than the same number of "
              "scattered cells",
     "rule": "HOLDS if on li4 at theta x0, perp/f100 - scatter in sign is >= 0.05, else FAILS",
     "inputs": "P16: +0.107"},
    {"id": "B4", "kind": "growth must be slow enough", "panel": "B",
     "claim": "A fast front outruns the pattern and loses registration with distance; slower fronts keep it",
     "rule": "HOLDS if on li4 at theta x0, the far agreement is <= 0.90 for perp/f25 and >= 0.95 for perp/f100 and "
             "perp/f200, else FAILS",
     "inputs": "P16/P16b: 0.810; 0.997 and 0.996"},
    {"id": "B5", "kind": "elongating stripes register better than adding them", "panel": "B",
     "claim": "Growth that adds stripes one at a time, from a boundary along them, registers them less well than growth "
              "along the stripes",
     "rule": "HOLDS if on li4 at theta x0, the sign of par/f25, par/f50 and par/f100 is each <= 0.90, and perp/f100's "
             "sign exceeds the largest of them by >= 0.08, else FAILS",
     "inputs": "P16/P16b: 0.848, 0.826, 0.772; difference 0.150"},
    {"id": "B6", "kind": "growth alone gives no registration", "panel": "B",
     "claim": "A front spreading from the boundary's position without anchor cells does not register the pattern",
     "rule": "HOLDS if on li4 at theta x0, none/perp-f100's sign is <= 0.60, else FAILS",
     "inputs": "P16b: 0.443 (P16's none/par-f100: 0.503)"},
    {"id": "B7", "kind": "disorder favours scattered information", "panel": "B",
     "claim": "Under the environmental field, scattered cells register the pattern better than growth from a boundary",
     "rule": "HOLDS if on li4 at theta x0.5 and x1, scatter's sign exceeds the larger of perp/f100 and perp/f200 by >= 0.03, "
             "else FAILS",
     "inputs": "P16/P16b: +0.063 and +0.070 (x0.25: -0.025, not registered)"},
    {"id": "B8", "kind": "self-organisation completes what growth starts", "panel": "B",
     "claim": "The stripe body turns growth from a boundary into a registered pattern far better than the double well, "
              "which builds no stripes from sparse cells at once",
     "rule": "HOLDS if at theta x0, li4 - dw in perp/f100's sign is >= 0.15, and dw's sign under scatter, par, perp and "
             "cluster is each <= 0.62, else FAILS",
     "inputs": "P16: +0.238; dw 0.557, 0.566, 0.545, 0.534"},
    {"id": "B9", "kind": "holding under disorder favours scattered cells", "panel": "H",
     "claim": "Under the environmental field, scattered cells hold the acquired stripes better than a boundary or a "
              "cluster of the same number of cells, on either body",
     "rule": "HOLDS if in panel H at theta x0.5 and x1, on dw and li4, scatter's sign exceeds the largest of par, perp "
             "and cluster by >= 0.005, else FAILS",
     "inputs": "P16: +0.036, +0.038 (li4); +0.057, +0.018 (dw)"},
    {"id": "B10", "kind": "a boundary's reach is short under disorder", "panel": "H",
     "claim": "Under the environmental field a boundary holds its own neighbourhood and adds nothing eight lines away",
     "rule": "HOLDS if in panel H on li4 at theta x0.5 and x1, for par and perp, near agreement is >= 0.85 and beyond "
             "is <= 0.05, else FAILS",
     "inputs": "P16: near 0.996, 0.955, 0.941, 0.884; beyond +0.022, -0.002, +0.011, -0.002"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
