"""Engineering probe P14b (python probes/p14b_dl002_disorder_axis.py CPUS): P14's anchors along the disorder axis.
ENGINEERING_PROBE_NOT_EVIDENCE.

P14 (theta spread 0.2) found sparse anchors no more useful on the stripe body than on the double well. Placement
should reach further through a stiff pattern at weaker disorder (a random field pins a soft mode over a length that
grows as the field weakens), so this repeats P14's panel A for dw and li4 on S4 and LB at theta x0.25 and x0.5
(spreads 0.05 and 0.1), on P14's blocks and tag.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import p14_dl002_design_inputs as P  # noqa: E402

OUT = P.LANE / "probes" / "results" / "p14b_dl002_disorder_axis.json"


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    jobs = [(b, pat, th, "") for b in ("dw", "li4") for pat in ("S4", "LB") for th in (0.25, 0.5)]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(P.task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P14b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": P.TAG, "blocks": list(P.BLOCKS),
           "records": P.RECORDS, "rows": rows, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "wall_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
