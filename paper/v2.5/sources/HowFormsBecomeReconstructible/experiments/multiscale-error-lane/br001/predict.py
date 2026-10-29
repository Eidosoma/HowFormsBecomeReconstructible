"""BR001's registered statements, written before any development outcome.

python -m br001.predict   (writes br001/frozen/predictions.json)

RL1 replicates engineering probe P7 (disclosed); the others follow from REVIEW_BIOLOGY.md, THEORY.md and
the mechanism of each rule. Every statement is scored by br001.analyze on block means over the 16
development blocks; intervals are 95% t intervals of paired block-mean contrasts.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from br001 import design as D  # noqa: E402

F0C = [D.regime("F0", 0.1), D.regime("F0", 0.3)]
STATEMENTS = [
    {"id": "RL1", "kind": "replication (P7)", "panel": "L",
     "claim": "Local redundancy and a coarse code repair complementary lesion sizes: a self-correcting record heals small wounds, "
              "a 16-value code heals large ones, and together they heal every size",
     "endpoint": "les_r (record sign inside the lesion, end of window)", "conditions": "both-SxS, S = 2, 4, 6, 8", "regimes": F0C,
     "rule": "HOLDS if in both regimes (block means): self >= 0.9 at 2x2 and <= 0.6 at 8x8; code <= 0.1 at 2x2 and >= 0.6 at 8x8; "
             "multi >= 0.9 at every size; else FAILS"},
    {"id": "RL2", "kind": "design", "panel": "L",
     "claim": "Multi-scale self-repair keeps the body as well as a full protected copy of the record",
     "contrast": "multi - protected", "endpoint": "v_qual", "conditions": "both-SxS, S = 2, 4, 6, 8", "regimes": F0C,
     "rule": "HOLDS if the lower bound of every 95% interval (8 contrasts) is above -0.02, else FAILS"},
    {"id": "RL3", "kind": "projection", "panel": "L",
     "claim": "A coarse code cannot restore fine content: for the multi-scale family it adds less repair to large lesions than for half-planes",
     "endpoint": "les_r, multi - self, both-8x8",
     "regimes": {"BL": [D.regime("BL", 0.1), D.regime("BL", 0.3)], "F0": F0C},
     "rule": "HOLDS if at each sigma (multi - self) for BL is below (multi - self) for F0 by more than 0.10 (block means), else FAILS"},
    {"id": "RL4", "kind": "physics", "panel": "L",
     "claim": "An open body heals large body wounds that a body with a conserved mean cannot fully heal",
     "endpoint": "les_v (body sign inside the lesion), protected record, body-8x8",
     "regimes": {"open": [D.regime("F0", 0.1, "o"), D.regime("F0", 0.3, "o")], "conserved": F0C},
     "rule": "HOLDS if at each sigma the open body's les_v exceeds the conserved body's by at least 0.05 (block means), else FAILS"},
    {"id": "RP1", "kind": "mechanism", "panel": "P",
     "claim": "Explicit damage tags separate damage from change where a duration latch cannot: under a permanent scar the tag rule keeps "
              "the record while the duration rule adopts the scar; both adopt a cued lasting change",
     "endpoints": {"scar-6x6": "les_r", "impose-inf-cued": "rg_sign"}, "regimes": "all 4 of panel P",
     "rule": "HOLDS if in every regime (block means): write_tags les_r >= 0.9 and write_duration les_r <= 0.5 under scar-6x6; "
             "write_tags and write_duration rg_sign >= 0.8 under impose-inf-cued; else FAILS"},
    {"id": "RP2", "kind": "mechanism", "panel": "P",
     "claim": "Every gate has a blind spot: tags adopt an untagged transient change, phase gating cannot adopt an uncued lasting "
              "change, and the duration latch rejects the transient but adopts every lasting change, scars included (RP1)",
     "endpoints": {"impose-300": "rg_sign", "impose-inf": "rg_sign"}, "regimes": "all 4 of panel P",
     "rule": "HOLDS if in every regime (block means): under impose-300, write_tags rg_sign exceeds write_duration rg_sign by at least 0.1; "
             "under impose-inf, write_phase rg_sign <= 0.6 and write_duration rg_sign >= 0.8; else FAILS"},
    {"id": "RP3", "kind": "mechanism", "panel": "P",
     "claim": "Writing without any gate copies damage into the record",
     "endpoint": "les_r under scar-6x6", "regimes": "all 4 of panel P",
     "rule": "HOLDS if write_always les_r <= 0.5 in every regime (block means), else FAILS"},
    {"id": "RT1", "kind": "mechanism", "panel": "T",
     "claim": "Turnover erases a static tissue-held record; a self-correcting record re-specifies new cells from their neighbours",
     "endpoint": "r_sign at the window's end, turnover-0.003", "regimes": [D.regime("F0", s) for s in (0.05, 0.1, 0.3)],
     "rule": "HOLDS if in each regime static r_sign <= 0.6 and self r_sign >= 0.95 (block means), else FAILS"},
    {"id": "RT2", "kind": "mechanism", "panel": "T",
     "claim": "Under turnover the body keeps its pattern only with a self-correcting record",
     "endpoint": "v_qual, turnover-0.003 minus turnover-0 (same arm, paired)", "regimes": [D.regime("F0", s) for s in (0.1, 0.3)],
     "rule": "HOLDS if in each regime the self arm loses less than 0.05 and the static arm loses more than 0.10 (block means), else FAILS"},
    {"id": "RT3", "kind": "question", "panel": "T",
     "claim": "Turnover makes a record necessary even where noise does not: at sigma = 0.05 the record's value to the body grows with turnover",
     "endpoint": "v_qual, self - inactive", "regime": D.regime("F0", 0.05),
     "rule": "HOLDS if (self - inactive) at turnover-0.003 exceeds (self - inactive) at turnover-0 by at least 0.05 (block means), else FAILS"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
