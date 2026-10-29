"""OR001's registered statements, written before any selection outcome.

python -m or001.predict   (writes or001/frozen/predictions.json)

The expectations come from THEORY.md section 7 (a setpoint is an investment that pays where native
physics forgets faster than a lifetime, concentrated on the scales the body cannot restore) and from
ME001/ME002 (copying the record beats capturing the body; writing the record from the body imports
body noise). Every statement is scored by or001.analyze.score on the evolved genes (seed means) or
on the development reading.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from or001 import design as O  # noqa: E402

STATEMENTS = [
    {"id": "OS1a", "claim": "A maintained setpoint is bought where physics forgets: the evolved maintenance gain is larger at sigma = 0.3 than at sigma = 0.05",
     "genes": "g_site + g_region + g_sheet, mean of the two seeds", "cells": "2 families x 4 injury regimes at dose cost 0.05",
     "rule": "HOLDS if total gain(sigma 0.3) > total gain(sigma 0.05) in >= 7 of 8 cells, else FAILS"},
    {"id": "OS1b", "claim": "Where physics holds a formed pattern, selection buys a developmental programme instead: newborns read their record hard early",
     "genes": "m_dev, mean of the two seeds", "cells": "sigma 0.05 at dose cost 0.05, 2 families x 4 injury regimes",
     "rule": "HOLDS if m_dev > 1 in >= 6 of 8 cells, else FAILS"},
    {"id": "OS2", "claim": "Copying the record evolves where the record is safe: the packet is mostly the record, not the captured body",
     "genes": "w (packet = w R + (1 - w) Q), mean of the two seeds",
     "cells": "sigma 0.15 and 0.3 x injuries none and body x 2 families x 2 costs = 16",
     "rule": "HOLDS if w > 0.5 in >= 14 of 16 cells, else FAILS"},
    {"id": "OS3", "claim": "Writing the record from the body is selected against unless the record itself is injured",
     "genes": "rho_w, mean of the two seeds",
     "rule": "HOLDS if rho_w < 0.002 (the native rate) in >= 75% of the cells without record injuries (none, body; 24 cells) and "
             "rho_w(record) > rho_w(none) in >= 75% of the 12 (family, sigma, cost) pairs, else FAILS"},
    {"id": "OS4", "claim": "Fine features need fine gains: for the multi-scale family the evolved site gain exceeds both coarse gains",
     "genes": "g_site vs g_region and g_sheet, mean of the two seeds", "cells": "BL at sigma 0.15 and 0.3 x 4 injury regimes x 2 costs = 16",
     "rule": "HOLDS if g_site > max(g_region, g_sheet) in >= 75% of cells, else FAILS"},
    {"id": "OS5", "claim": "Selection finds at least the native architecture: evolved genomes keep forms on fresh blocks as well as the native hold route",
     "endpoint": "development retention: body qualified agreement averaged over generations 1-6, paired by case, block means",
     "rule": "HOLDS if evolved - native_hold >= -0.02 (point estimate) for >= 90% of the 96 evolved genomes, else FAILS"},
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_SELECTION_OUTCOMES", "design_digest": O.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
