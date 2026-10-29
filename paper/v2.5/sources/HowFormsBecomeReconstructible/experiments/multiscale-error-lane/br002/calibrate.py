"""Panel C write thresholds: BR001's frozen panel P thresholds, carried unchanged as public settings.

python -m br002.calibrate   (writes br002/frozen/calibration.json)

BR001 calibrated them on engineering blocks 900953-900958 before any of its development outcomes (99.5%
quantiles of per-trajectory sham maxima of region mismatch and region surprise). Panel C's four regimes are
BR001 panel P's four regimes, so the same thresholds apply; carrying them keeps BR002 comparable with BR001
and P8. The file records the source's sha256 and is stamped with BR002's design digest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from br002 import design as D  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
SOURCE = LANE / "br001" / "frozen" / "calibration.json"

if __name__ == "__main__":
    src = json.loads(SOURCE.read_text())
    regimes = {r: src["regimes"][r] for r in D.PANELS["C"]["regimes"]}
    out = Path(__file__).resolve().parent / "frozen" / "calibration.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "CARRIED_FROM_BR001_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "source": str(SOURCE.relative_to(LANE)), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                               "source_blocks": src["blocks"], "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "regimes": regimes}, indent=1) + "\n")
    print(f"wrote {out}")
