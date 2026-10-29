"""EN001's registered statements, written before any development outcome.

python -m en001.predict   (writes en001/frozen/predictions.json)

Every threshold was set from engineering probe P11 (32 cases; v2, disclosed) with a margin, before the 128
development cases were drawn; the reader en001.analyze.score computes each rule exactly as written here, on
block means over the 16 development blocks. 'base' is the full budget; Bphi and Cphi are a global budget phi
with every drift paid, under thermal (B) and activity-driven (C) noise; t95 counts a wound never healed as 3,100.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from en001 import design as D  # noqa: E402

G_ALL = list(D.PANELS["G"]["regimes"])
P_ALL = list(D.PANELS["P"]["regimes"])
E_ALL = list(D.PANELS["E"]["regimes"])
F03 = D.regime("F0", 0.3)

STATEMENTS = [
    {"id": "EB1", "kind": "the PI's question (P11, T7)", "panel": "G",
     "claim": "Slowing the budget dissolves the pattern if the noise is thermal and leaves it intact if the noise is "
              "driven by the cell's own activity",
     "endpoint": "v_qual, sham, end of starvation", "arms": ["multi", "relcode"], "regimes": G_ALL,
     "rule": "HOLDS if in every panel G regime, for multi and relcode, v_qual at B0.1 is at least 0.1 below base and v_qual "
             "at C0.1 is at most 0.02 below base (block means), else FAILS"},
    {"id": "EB2", "kind": "mechanism (P11)", "panel": "G",
     "claim": "The plan outlives its expression: under thermal starvation the record survives while the body's pattern "
              "dissolves, and the body re-forms when the budget returns",
     "endpoints": ["r_sign, sham, end of starvation", "v_qual_rec, sham, after recovery"], "arms": ["hold", "multi", "relcode"],
     "regimes": G_ALL,
     "rule": "HOLDS if in every panel G regime, for hold, multi and relcode, r_sign at B0.1 >= 0.95 and v_qual_rec at B0.1 >= "
             "v_qual_rec at base - 0.02 (block means), else FAILS"},
    {"id": "EB3", "kind": "mechanism (P11, T7)", "panel": "G",
     "claim": "Under activity noise, repair is what a small budget costs: wounds heal later, and heal once the budget returns",
     "endpoints": ["t95, flip-6x6", "les_r_rec, flip-6x6"], "regimes": G_ALL,
     "rule": "HOLDS if in every panel G regime relcode t95 at C0.1 >= 3 x relcode t95 at base, relcode les_r_rec at C0.1 >= "
             "0.98, and multi les_r_rec at C0.1 >= multi les_r_rec at base - 0.03 (block means), else FAILS"},
    {"id": "EB4", "kind": "mechanism (P11, T7)", "panel": "G",
     "claim": "Cell turnover on an outside clock outruns re-specification when the budget is low",
     "endpoint": "v_qual, sham minus turnover-0.001, end of starvation", "arms": ["multi", "relcode"], "regimes": G_ALL,
     "rule": "HOLDS if in every panel G regime, for multi and relcode, the gap (sham - turnover) at C0.1 is at least 0.02 "
             "larger than at base (block means), else FAILS"},
    {"id": "EB5", "kind": "mechanism (MODEL_LIMITS 2.1; P11)", "panel": "G",
     "claim": "Reset wounds stay repairable on a small budget where flipped wounds do not",
     "endpoint": "les_r at C0.1, end of starvation", "arms": ["self", "multi"], "regimes": G_ALL,
     "rule": "HOLDS if in every panel G regime, for self and multi, les_r of reset-6x6 is at least 0.1 above les_r of flip-6x6 "
             "at C0.1 (block means), else FAILS"},
    {"id": "EB6", "kind": "order of failure (P11)", "panel": "G",
     "claim": "What fails first depends on the noise: under activity noise, repair first, then turnover maintenance, never the "
              "undamaged pattern; under thermal noise, the undamaged pattern first, before repair",
     "endpoints": "relative losses against base: les_r flip-6x6; v_qual turnover-0.001; v_qual sham", "arms": ["multi", "relcode"],
     "regimes": [F03],
     "rule": "HOLDS if in F0 at sigma 0.3, for multi and relcode, at C0.1 loss(flip repair) > loss(turnover) > loss(sham) and "
             "loss(sham) <= 0.02, and at B0.5 loss(sham) >= 0.10 and loss(flip repair) <= 0.02 (block means; loss = 1 - level / "
             "base level), else FAILS"},
    {"id": "EP1", "kind": "allocation (P11)", "panel": "P",
     "claim": "Under thermal noise the pattern's expression needs the body's own physics paid: protecting the body keeps it, "
              "protecting the record does not",
     "endpoint": "v_qual, sham, at a quarter of the budget", "arms": ["multi", "relcode"], "regimes": P_ALL,
     "rule": "HOLDS if in every panel P regime, for multi and relcode, thermal-body v_qual >= base v_qual - 0.02 and thermal-record "
             "v_qual <= thermal-uniform v_qual + 0.02 (block means), else FAILS"},
    {"id": "EP2", "kind": "allocation (P11)", "panel": "P",
     "claim": "The record is the cheap thing to protect: protecting it keeps wound repair at its full-budget level for a "
              "fraction of the full spend",
     "endpoints": ["les_r, flip-6x6", "spend per cell and update, sham"], "arms": ["multi", "relcode"], "regimes": P_ALL,
     "rule": "HOLDS if in every panel P regime, for multi and relcode and both noises, les_r with the record protected >= base les_r "
             "- 0.02 and its sham spend <= 0.6 x the base sham spend (block means), else FAILS"},
    {"id": "EP3", "kind": "allocation (P11)", "panel": "P",
     "claim": "Under activity noise protecting the body is wasted: it spends several times more for no better pattern",
     "endpoints": ["v_qual, sham", "spend, sham"], "arms": ["multi", "relcode"], "regimes": P_ALL,
     "rule": "HOLDS if in every panel P regime, for multi and relcode, activity-body v_qual <= activity-uniform v_qual + 0.01 and "
             "its sham spend >= 3 x activity-uniform's (block means), else FAILS"},
    {"id": "EE1", "kind": "replication with a store (P11)", "panel": "E",
     "claim": "A per-cell energy store gives the same split: a low supply dissolves the pattern under thermal noise, not under "
              "activity noise",
     "endpoint": "v_qual, sham", "arms": ["multi", "relcode"], "regimes": E_ALL,
     "rule": "HOLDS if in every panel E regime, for multi and relcode, store-thermal0.1 v_qual <= store-thermal1 v_qual - 0.1 and "
             "store-activity0.1 v_qual >= store-activity1 v_qual - 0.02 (block means), else FAILS"},
    {"id": "EE2", "kind": "design (P11)", "panel": "E and G",
     "claim": "A store whose spending follows demand buffers repair: at a tenth of the supply its cells keep more availability "
              "than the supply factor and repair more than under a uniform cut to a tenth",
     "endpoints": ["les_r, flip-6x6: store-activity0.1 (panel E) against C0.1 (panel G)", "a_rest, sham, store-activity0.1"],
     "arms": ["multi", "relcode"], "regimes": E_ALL,
     "rule": "HOLDS if in every panel E regime, for multi and relcode, store-activity0.1 les_r >= C0.1 les_r + 0.05 and the store's "
             "mean availability in sham >= 0.2 (block means), else FAILS"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
