"""GW001's registered statements, written before any development outcome.

python -m gw001.predict   (writes gw001/frozen/predictions.json)

Every threshold was set from engineering probe P10 (16 cases, disclosed) and, for G1-G4, from the model-limits
study's T1/T1b/T1c (MODEL_LIMITS_AND_EXPANSION.md), with margins. Every statement is scored by gw001.scoring on
block means over the 16 development blocks (t95: medians over all 128 cases; inf if never within the window).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gw001 import design as D  # noqa: E402

STATEMENTS = [
    {"id": "G1", "kind": "replication (T1, P10)", "panel": "R",
     "claim": "Consensus alone heals closed flipped wounds of every size tested once they have room; it cannot heal a large "
              "flipped wound that touches a wall, at any sheet size",
     "rule": "HOLDS if self kept@8000 >= 0.95 for f4-, f6-, f8- and f10-mid at side 32 and f4-, f8- and f12-mid at side 64, and "
             "self kept@8000 <= 0.7 for f8-d0 at sides 16, 32 and 64 (block means), else FAILS"},
    {"id": "G2", "kind": "replication (T1b, P10)", "panel": "R",
     "claim": "Reset wounds (cells lost, record at its unstable point) heal fast under consensus alone wherever they clear the walls",
     "rule": "HOLDS if self kept@2000 >= 0.95 for every reset wound at mid and d2 placements at sides 32 and 64, and the median "
             "t95 of each is <= 1000 updates, else FAILS"},
    {"id": "G3", "kind": "scaling (T1c, P10)", "panel": "R",
     "claim": "The healing time of a closed flipped wound grows faster than its area",
     "rule": "HOLDS if the least-squares slope of ln(median t95) on ln(side) for self is >= 2.0 over f4/f6/f8/f10-mid at side 32 "
             "and over f4/f8/f12-mid at side 64 (FAILS if any of these medians is censored), and self kept@8000 <= 0.7 for f16-mid "
             "at side 64, else FAILS"},
    {"id": "G4", "kind": "mechanism", "panel": "R",
     "claim": "The coarse code's job is wounds at walls, and speed: its gain over consensus is large where a wound touches a wall, "
              "and for a large closed wound it is gained time, not a different end state",
     "rule": "HOLDS if at side 32 (multi - self) kept@2000 averaged over f4-d0 and f8-d0 exceeds the same average over f4-mid and "
             "f8-mid by >= 0.3, and for f12-mid at sides 32 and 64 (multi - self) is >= 0.5 at t = 2000 and <= 0.1 at t = 8000 "
             "(block means), else FAILS"},
    {"id": "G5", "kind": "mechanism", "panel": "R",
     "claim": "Stronger consensus heals closed wounds faster when they have room, but pins them when the margin is thin",
     "rule": "HOLDS if for f12-mid self_kr2's median t95 at side 64 is at most half of self's, and self_kr2 kept@8000 <= 0.1 at "
             "side 32 while self kept@8000 >= 0.9 there, else FAILS"},
    {"id": "G6", "kind": "geometry", "panel": "R",
     "claim": "Domain thickness, not sheet size, decides consensus repair: 8-thick stripes on a 32-site sheet repair flipped "
              "wounds as 8-thick half-planes on a 16-site sheet do",
     "rule": "HOLDS if |self kept@2000 on S8_32 - on F0_16| <= 0.08 for every flipped condition the two share, else FAILS"},
    {"id": "G7", "kind": "geometry", "panel": "R",
     "claim": "Consensus's loss of multi-scale detail is set by feature size on the lattice, not by sheet size, and differs "
              "between patterns more than between replicates",
     "rule": "HOLDS if for self's undamaged record at t = 2000 |BL_32 - BL_16| <= 0.03 and BLx2_32 - BL_32 >= 0.08, and on "
             "BL_16 the SD of block means (fresh patterns) is >= 2.5 x the replicate SD between the two births of a pattern, else FAILS"},
    {"id": "G8", "kind": "replication (P8, BR002) at scale", "panel": "R",
     "claim": "A relational record with the coarse code repairs every flipped and reset wound at every size and placement, and "
              "a relational record keeps multi-scale detail at every resolution",
     "rule": "HOLDS if rel+code kept@8000 >= 0.98 for every flipped and reset wound on F0_16, F0_32, F0_64 and S8_32, and rel's "
             "undamaged record agreement at t = 8000 is >= 0.98 on every BL geometry, else FAILS"},
    {"id": "G9", "kind": "physics", "panel": "B",
     "claim": "The conserved body's failure to heal a wound that touches a wall is diluted on a larger sheet, as the mean shift "
              "scales with wound area over sheet area",
     "rule": "HOLDS if with the protected record, for f8-d0, (conserved - open) les_v is <= -0.3 at side 16 and >= -0.15 at "
             "side 32, and (conserved - open) v_out is <= -0.05 at side 16 and >= -0.04 at side 32 (block means), else FAILS"},
    {"id": "G10", "kind": "mechanism", "panel": "B",
     "claim": "With a record that cannot repair itself, the body heals a reset wound but not a flipped one",
     "rule": "HOLDS if at side 32 static les_v under r8-d0 exceeds that under f8-d0 by >= 0.4 in both bodies (block means), else FAILS"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
