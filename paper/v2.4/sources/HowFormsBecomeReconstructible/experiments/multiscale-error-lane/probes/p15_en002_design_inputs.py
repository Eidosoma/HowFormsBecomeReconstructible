"""Engineering probe P15 (python probes/p15_en002_design_inputs.py CPUS): EN002's worker on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for EN002's registered statements, run before the freeze.

Every (panel, unit) task of en002/design.py's draft on engineering blocks 900884-900887 (32 cases) under the probe's
own tag mse-p15 (EN002's code with tag=PROBE_TAG). Nothing is written to scratch; this script prints and saves the
block means (and SDs of the four block means) of every endpoint, for each body and condition.
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

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from en002 import design as D  # noqa: E402
from en002 import worker as W  # noqa: E402

OUT = LANE / "probes" / "results" / "p15_en002_design_inputs.json"


def job(args):
    panel, unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    ends, raw, timing, cases = W.task(panel, unit, block, "engineering", tag=D.PROBE_TAG)
    return panel, unit, block, {k: v.mean(-1) for k, v in ends.items()}, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    blocks = list(range(*D.PROBE_BLOCKS))
    jobs = [(p, u, b) for p, u in D.tasks() for b in blocks]
    jobs.sort(key=lambda j: j[0] != "W")
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        res = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    levels = {}
    for p, u in D.tasks():
        rows = [r for r in res if r[0] == p and r[1] == u]
        rows.sort(key=lambda r: r[2])
        conds = [c.name for c in D.PANELS[p]["conds"]]
        snaps = D.PANELS[p]["snaps"]
        for key in rows[0][3]:
            x = np.stack([r[3][key] for r in rows])                     # (blocks, [snaps,] conds)
            body, ep = key.split("/")
            for ci, c in enumerate(conds):
                d = levels.setdefault(p, {}).setdefault(u, {}).setdefault(body, {}).setdefault(c, {})
                if x.ndim == 3:
                    for si, t in enumerate(snaps):
                        v = x[:, si, ci]
                        d[f"{ep}@{t}"] = [round(float(v.mean()), 4), round(float(v.std(ddof=1)), 4)]
                else:
                    v = x[:, ci]
                    d[ep] = [round(float(v.mean()), 6), round(float(v.std(ddof=1)), 6)]
    out = {"probe": "P15", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
           "draft_digest": D.digest(), "levels": levels, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(r[4] for r in res), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(res), "tasks;", out["wall_s"], "s wall")


if __name__ == "__main__":
    main()
