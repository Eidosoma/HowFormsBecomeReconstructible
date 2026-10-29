"""BR002's registered statements, written before any development outcome.

python -m br002.predict   (writes br002/frozen/predictions.json)

Every statement replicates or sharpens an engineering probe (P8, P9; disclosed): the thresholds were set
from the probes' 32 engineering cases with margins, before the 128 development cases were drawn. Every
statement is scored by br002.analyze on block means over the 16 development blocks; RR5's intervals are
95% t intervals of paired block-mean contrasts.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from br002 import design as D  # noqa: E402

C_ALL = list(D.PANELS["C"]["regimes"])
C_HIGH = [D.regime("F0", 0.3), D.regime("F0", 0.3, "o")]
C_OPEN = [D.regime("F0", 0.1, "o"), D.regime("F0", 0.3, "o")]
C_CONS = [D.regime("F0", 0.1), D.regime("F0", 0.3)]
R_ALL = list(D.PANELS["R"]["regimes"])
R_FINE = [r for r in R_ALL if r.startswith(("BL", "IS"))]
G_ALL = list(D.PANELS["G"]["regimes"])

STATEMENTS = [
    {"id": "RC1", "kind": "replication (P8, P9)", "panel": "C",
     "claim": "A committed write adopts a lasting change completely, where BR001's uncommitted gates stall at high noise",
     "endpoint": "adopt_flip (record agreement with the imposed message where it differs from the original), impose-inf",
     "regimes": {"committed": C_ALL, "uncommitted": C_HIGH},
     "rule": "HOLDS if always+h, duration+h and tags+h adopt_flip >= 0.95 in every regime, and always, duration and tags "
             "adopt_flip <= 0.5 in both sigma = 0.3 regimes (block means), else FAILS"},
    {"id": "RC2", "kind": "mechanism", "panel": "C",
     "claim": "With commitment the duration latch is a pure duration filter: it adopts every lasting change, scars included, "
              "and rejects a transient one",
     "endpoints": {"scar-6x6": "les_r", "impose-300": "adopt_flip"}, "regimes": C_ALL,
     "rule": "HOLDS if in every regime duration+h les_r <= 0.5 under scar-6x6 and duration+h adopt_flip <= 0.05 under "
             "impose-300 (block means), else FAILS"},
    {"id": "RC3", "kind": "mechanism", "panel": "C",
     "claim": "Damage tags protect the record from a scar only where the damage stays local: in the open body, not in the "
              "conserved one, where the scar's damage spreads through the conserved mean to untagged tissue",
     "endpoint": "les_r, tags+h, scar-6x6", "regimes": {"open": C_OPEN, "conserved": C_CONS},
     "rule": "HOLDS if tags+h les_r >= 0.85 in both open regimes and <= 0.5 in both conserved regimes (block means), else FAILS"},
    {"id": "RC4", "kind": "prediction (REPORT_BR001; seen in P9)", "panel": "C",
     "claim": "The plastic window's blind spot: damage arriving inside an open window is adopted",
     "endpoint": "les_r, phase, window-scar-6x6 (scar 100 updates after the cue)", "regimes": C_ALL,
     "rule": "HOLDS if phase les_r <= 0.5 in every regime (block means), else FAILS"},
    {"id": "RC5", "kind": "design", "panel": "C",
     "claim": "A window that refuses tagged sites closes the blind spot where damage stays local: it adopts the cued change and "
              "keeps the record under a scar inside the window in the open body, but not in the conserved one",
     "endpoints": {"impose-inf-cued": "adopt_flip", "window-scar-6x6": "les_r, phase+tags - phase"},
     "regimes": {"all": C_ALL, "open": C_OPEN, "conserved": C_CONS},
     "rule": "HOLDS if phase+tags adopt_flip >= 0.95 under impose-inf-cued in every regime, and (phase+tags - phase) les_r under "
             "window-scar-6x6 is >= 0.3 in both open regimes and <= 0.1 in both conserved regimes (block means), else FAILS"},
    {"id": "RC6", "kind": "cost", "panel": "C",
     "claim": "Committed writes are cheaper at high noise: an uncommitted writer stalls and keeps paying",
     "endpoint": "w_l1 (total |write|), impose-inf", "regimes": C_HIGH,
     "rule": "HOLDS if in both sigma = 0.3 regimes w_l1 of always+h, duration+h and tags+h is at most 0.5 x w_l1 of always, "
             "duration and tags respectively (block means), else FAILS"},
    {"id": "RR1", "kind": "replication (P8, P9)", "panel": "R",
     "claim": "A relational record keeps fine detail that consensus erases",
     "endpoint": "r_sign, sham", "regimes": {"rel": R_ALL, "self": R_FINE},
     "rule": "HOLDS if rel r_sign >= 0.98 in every regime and self r_sign <= 0.9 in every BL and IS regime (block means), else FAILS"},
    {"id": "RR2", "kind": "replication (P8, P9)", "panel": "R",
     "claim": "A relational record repairs wounds of every size, and with the coarse code the largest",
     "endpoint": "les_r, both-SxS", "regimes": R_ALL,
     "rule": "HOLDS if in every regime rel les_r >= 0.95 at 2x2, 4x4 and 6x6 and >= 0.9 at 8x8, and rel+code les_r >= 0.9 at "
             "8x8 (block means), else FAILS"},
    {"id": "RR3", "kind": "replication (P8, P9)", "panel": "R",
     "claim": "Under turnover the bonds re-specify newborn cells; consensus loses fine detail",
     "endpoint": "r_sign, turnover-0.003", "regimes": {"rel": R_ALL, "self": R_FINE},
     "rule": "HOLDS if rel r_sign >= 0.98 in every regime and self r_sign <= 0.9 in every BL and IS regime (block means), else FAILS"},
    {"id": "RR4", "kind": "mechanism", "panel": "R",
     "claim": "Cells dying together with their bonds is the relational record's weak point; re-forming the lost bonds as "
              "consensus, with the coarse code, repairs it",
     "endpoint": "les_r, kill-8x8", "regimes": R_ALL,
     "rule": "HOLDS if in every regime rel les_r <= 0.8 and rel+code+relink les_r >= 0.9 (block means), else FAILS"},
    {"id": "RR5", "kind": "design", "panel": "R",
     "claim": "A relational record gives the body more than a protected copy of the taught record",
     "contrast": "rel - protected", "endpoint": "v_qual, sham", "regimes": R_ALL,
     "rule": "HOLDS if the lower bound of the 95% interval is above 0 in every regime (7 contrasts), else FAILS"},
    {"id": "RG1", "kind": "mechanism (corrected after P8; P9)", "panel": "G",
     "claim": "What consensus cannot repair is a thick wound that merges with the opposite domain: a 6x6 wound centred in a "
              "domain with a one-site margin is lost, while one straddling a wall heals; a 4x4 wound with a two-site margin "
              "heals and one touching a wall does not fully",
     "endpoint": "les_r, self", "regimes": G_ALL,
     "rule": "HOLDS if in both regimes self les_r <= 0.2 at w6-d1, >= 0.8 at w6-cross, >= 0.95 at w4-d2 and <= 0.75 at w4-d0 "
             "(block means), else FAILS"},
    {"id": "RG2", "kind": "mechanism", "panel": "G",
     "claim": "A relational record repairs wounds wherever they sit; with the coarse code, also the largest",
     "endpoint": "les_r", "regimes": G_ALL,
     "rule": "HOLDS if in both regimes rel+code les_r >= 0.98 at every placement and rel les_r >= 0.95 at every placement of "
             "sides 2-6 (block means), else FAILS"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
