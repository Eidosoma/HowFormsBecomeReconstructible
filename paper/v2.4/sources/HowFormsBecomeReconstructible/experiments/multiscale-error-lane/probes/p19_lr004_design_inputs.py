"""Engineering probe P19 (python probes/p19_lr004_design_inputs.py CPUS): LR004's worker on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for LR004's registered statements, run before the freeze.

LR004's draft worker on engineering blocks 900750-900753 (32 cases) under the probe's own tag mse-p19: bond-flip rates
0, 1e-3, 3e-3, 1e-2 and 3e-2; the seven teachers (record+parity, body, site, pair, vote, anchors4,
anchors16); S4, LB and F0 at theta x0 and x1; reads at t = 1,000, 2,000 and 4,000. Nothing is written to
scratch; this script saves the block means (and the SD of the four block means) of every endpoint, for each body and
condition.
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

from lr004 import design as D  # noqa: E402
from lr004 import worker as W  # noqa: E402

OUT = LANE / "probes" / "results" / "p19_lr004_design_inputs.json"
THETAS = (0.0, 1.0)
UNITS = tuple(D.unit_name(p, t) for p in D.PATTERNS for t in THETAS)
ENDS = ("sign", "r_sign", "agree", "bond_err")


def job(args):
    unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    ends, raw, timing, cases = W.task("E", unit, block, "engineering", tag=D.PROBE_TAG)
    return unit, block, {k: v.mean(-1) for k, v in ends.items()}, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    blocks = list(range(*D.PROBE_BLOCKS))
    jobs = [(u, b) for u in UNITS for b in blocks]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        res = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    levels = {}
    for u in UNITS:
        rows = sorted((r for r in res if r[0] == u), key=lambda r: r[1])
        for b in D.BODIES:
            node = levels.setdefault(u, {}).setdefault(b, {})
            for ep in ENDS:
                x = np.stack([r[2][f"{b}/{ep}"] for r in rows])              # (blocks, reads, conds)
                node[ep] = {"mean": np.round(x.mean(0), 4).tolist(), "sd": np.round(x.std(0, ddof=1), 4).tolist()}
            for ep in ("flip_rate", "opened"):
                x = np.stack([r[2][f"{b}/{ep}"] for r in rows])              # (blocks, conds)
                node[ep] = np.round(x.mean(0), 6).tolist()
    out = {"probe": "P19", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
           "draft_digest": D.digest(), "conds": [c.name for c in D.CONDS], "reads": list(D.READS), "units": list(UNITS),
           "levels": levels, "task_wall_s": {f"{r[0]}/{r[1]}": r[3] for r in res},
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) in {out['wall_s']} s")


if __name__ == "__main__":
    main()
