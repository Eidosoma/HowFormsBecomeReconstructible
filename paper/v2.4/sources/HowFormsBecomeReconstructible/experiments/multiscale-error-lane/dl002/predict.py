"""DL002's registered statements, written before any development outcome.

python -m dl002.predict   (writes dl002/frozen/predictions.json)

Thresholds were set from engineering probes P14 and P14b (32 cases on blocks 900892-900895 under tag mse-p14,
disclosed in REGISTRATION_DL002.md), with margins for 128 cases. Scored by dl002.analyze on block means over the 16
development blocks. 'sign' is the body's agreement with the template over the sheet at t = 4,000 (panel A); 'patch' the
same inside the wound (panel R). theta x0, x0.25, x0.5, x1 are environmental-field spreads 0, 0.05, 0.1, 0.2.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dl002 import design as D  # noqa: E402

STATEMENTS = [
    {"id": "H1", "kind": "a record of relations suffices", "panel": "A",
     "claim": "A tissue-held relational record holds the native patterns on either body at every level of disorder",
     "rule": "HOLDS if rel's sign at t = 4000 is >= 0.94 for S4 and LB on dw and li4 at theta x0, x0.25, x0.5 and x1, else FAILS",
     "inputs": "P14/P14b: lowest 0.962 (LB, dw, theta x1)"},
    {"id": "H2", "kind": "relations replace physics", "panel": "A",
     "claim": "With a record of relations the body's own physics no longer matters for native patterns",
     "rule": "HOLDS if |li4 - dw| in rel's sign at t = 4000 is <= 0.02 for S4 and LB at every theta, else FAILS",
     "inputs": "P14/P14b: largest 0.005"},
    {"id": "H3", "kind": "physics supplies relations only where disorder is weak", "panel": "A",
     "claim": "Without a record the stripe body holds its own labyrinth far better than the double well in a clean sheet, "
              "and no better under the full environmental field",
     "rule": "HOLDS if without a record (li4 - dw) sign at t = 4000 on LB is >= 0.15 at theta x0 and <= 0.05 at theta x1, else FAILS",
     "inputs": "P14: +0.296 and -0.021 (x0.25 +0.178, x0.5 +0.064)"},
    {"id": "H4", "kind": "anchors are a poor substitute", "panel": "A",
     "claim": "Under disorder, positional anchors at a sixteenth of the sites fall well short of a record of relations, "
              "and anchors at a quarter of the sites fall short of the full held record",
     "rule": "HOLDS if at theta x0.5 and x1 (rel - a16) sign at t = 4000 is >= 0.10 for S4 and LB on both bodies, and at "
             "theta x1 (full - a4) on S4 is >= 0.05 on both bodies, else FAILS",
     "inputs": "P14/P14b: rel - a16 0.204-0.358; full - a4 0.108 (li4), 0.115 (dw)"},
    {"id": "H5", "kind": "repair under disorder needs a self-repairing record", "panel": "R",
     "claim": "Under the full environmental field only a record that repairs itself restores a wounded stripe pattern; "
              "anchors do not, and the held record nearly does",
     "rule": "HOLDS if in panel R at theta x1 on S4, for flipped and reset 8 x 8 wounds, patch at t = 4000 is >= 0.95 for rel, "
             "<= 0.80 for a4 and >= 0.90 for full, on both bodies, else FAILS",
     "inputs": "P14: rel 0.98-0.99; a4 0.44-0.68; full 0.95-0.96"},
    {"id": "H6", "kind": "design is still a commitment", "panel": "A",
     "claim": "Even a record of relations cannot hold a pattern off the stripe body's scale, which the double well holds",
     "rule": "HOLDS if rel's sign at t = 4000 on F0 is <= 0.85 for li4 and >= 0.95 for dw, at theta x0 and x1, else FAILS",
     "inputs": "P14: li4 0.800 and 0.761; dw 1.000 and 0.997"},
    {"id": "H7", "kind": "physics extends sparse anchors at weak disorder", "panel": "A",
     "claim": "At weak disorder the stripe body makes more of sparse anchors than the double well",
     "rule": "HOLDS if at theta x0.25 with a16 (li4 - dw) sign at t = 4000 is >= 0.10 on LB and >= 0.02 on S4, else FAILS",
     "inputs": "P14b: +0.175 and +0.064"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
