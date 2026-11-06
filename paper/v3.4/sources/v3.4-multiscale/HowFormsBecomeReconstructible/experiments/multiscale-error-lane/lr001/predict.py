"""LR001's registered statements, written before any development outcome.

python -m lr001.predict   (writes lr001/frozen/predictions.json)

Every threshold was set from engineering probes P13 (v1 and v2), P13b (v1 and v2) and P13c on 32 cases (blocks
900868-900871; P13 and P13b under tag mse-p13, P13c with lr001's simulator under its tag; disclosed in
REGISTRATION_LR001.md), with margins for 128 cases. Every statement is scored by
lr001.scoring on block means over the 16 development blocks (cases without the scored sites are left out of a
block's mean). Branch names: E 'rate/repair', C 'code/condition' (flipN, killN, relinkN), T 'rate/mode', L 'learning'.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lr001 import design as D  # noqa: E402

STATEMENTS = [
    {"id": "L1", "kind": "acquisition (P13 A)", "panel": "A",
     "claim": "Relations are easy to learn from a teacher: bonds learned as a running average of the body's co-activity "
              "while the teacher holds it are right after 20 updates, even at high noise",
     "rule": "HOLDS if bond_accuracy@20 >= 0.99 for sigma 0.1, 0.3 and 0.6 on F0 and IS, else FAILS"},
    {"id": "L2", "kind": "replication (P13 E)", "panel": "E",
     "claim": "Relations left without repair decay: at a bond flip rate of 3e-4 per update the bonds drift toward "
              "chance and the record is lost",
     "rule": "HOLDS if for '0.0003/none' bond_err@4000 >= 0.40 and sign@4000 <= 0.65 on F0, BL and IS, else FAILS"},
    {"id": "L3", "kind": "mechanism (P13 E)", "panel": "E",
     "claim": "Two layers of repair beat one: Hebbian relearning from the record and plaquette parity together keep "
              "the relations and the record at a flip rate where either alone does not",
     "rule": "HOLDS if at rate 0.001, 'both' has bond_err@4000 <= 0.06 and sign@4000 >= 0.95, 'hebb' has "
             "bond_err@4000 >= 0.20 and 'parity' has bond_err@4000 >= 0.08, on F0, BL and IS, else FAILS"},
    {"id": "L4", "kind": "threshold (P13 E, P13b D)", "panel": "E",
     "claim": "There is a threshold: at a flip rate of 3e-3 no single-scale repair keeps the record",
     "rule": "HOLDS if at rate 0.003 sign@8000 <= 0.75 for every repair on F0, BL and IS, else FAILS"},
    {"id": "L5", "kind": "mechanism (P13 G, P13c)", "panel": "C",
     "claim": "A coarse code applied in the relations' own frame repairs flipped wounds without fighting region-minority "
              "cells, which BR002's plain code does on the islands pattern (BR002's RR2 mechanism removed)",
     "rule": "HOLDS if on IS 'gauge/flip8' and 'hybrid/flip8' have kept@4000 >= 0.99 and kept_min@4000 >= 0.98 while "
             "'plain/flip8' has kept_min@4000 <= 0.98, and on every family and flipped size 'gauge' and 'hybrid' keep "
             "kept@4000 >= 'plain' - 0.005, else FAILS"},
    {"id": "L6", "kind": "mechanism (P13 G v2)", "panel": "C",
     "claim": "The gauge-frame code cannot reach killed cells; the hybrid (gauge frame where live bonds reach a cell, "
              "plain code where they do not) keeps the plain code's repair of kills",
     "rule": "HOLDS if on F0, BL, S4 and IS, kept@4000 for 'hybrid/kill8' >= 'plain/kill8' - 0.02 and for 'gauge/kill8' "
             "<= 'plain/kill8' - 0.10, else FAILS"},
    {"id": "L7", "kind": "mechanism (P13b K)", "panel": "C",
     "claim": "A bond re-formed by default is not a relation: passed into the gauge frame it misleads the hybrid code; "
              "kept out of the frame by a trust flag it does not",
     "rule": "HOLDS if kept@4000 for 'hybrid/relink8' <= 'plain/relink8' - 0.03 on BL and IS, and for "
             "'hybrid+trust/relink8' >= 'plain/relink8' - 0.02 on F0, BL, S4 and IS, else FAILS"},
    {"id": "L8", "kind": "limit (P13 G, P13b K)", "panel": "C",
     "claim": "What no layer stores is lost: region-minority cells inside a killed patch are not recovered by any code",
     "rule": "HOLDS if on BL and IS kept_min@4000 <= 0.92 for every code under kill8 and relink8, else FAILS"},
    {"id": "L9", "kind": "turnover (P13b T)", "panel": "T",
     "claim": "Relations survive cell renewal only if the newborn inherits them: relearned or default bonds lose the "
              "region-minority cells",
     "rule": "HOLDS if on BL and IS at rates 0.001 and 0.003, 'inherit' has sign@8000 >= 0.99 and minority@8000 >= 0.98, "
             "and 'relearn' and 'default' have minority@8000 <= 0.85, else FAILS"},
    {"id": "L10", "kind": "learning in life (P13b L)", "panel": "L",
     "claim": "Relations that keep learning from the body adopt a lasting body scar into the record; relations that learn "
              "from the record do not; a slower learner adopts less",
     "rule": "HOLDS if at t = 2000 on F0 and IS, 'body' has record_kept@2000 <= 0.85, 'record' and 'none' have "
             "record_kept@2000 >= 0.99, and 'body_slow' has record_kept@2000 above 'body', else FAILS"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
