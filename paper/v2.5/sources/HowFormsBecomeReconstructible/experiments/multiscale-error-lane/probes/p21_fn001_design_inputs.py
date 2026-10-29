"""Engineering probe P21 (python probes/p21_fn001_design_inputs.py CPUS): FN001's draft worker on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for FN001's registered statements, run before any freeze.

FN001's draft worker on engineering blocks 900770-900773 (32 cases) under the probe's own tag mse-p21: bond-flip rates
0, 1e-3 and 3e-3; four teachers (record+parity, body, site, vote); three injury schedules (W12 re-injury at the same
place, W12x a second wound elsewhere, W2 naive tissue wounded once at T_W2); S4, LB and F0 at theta x0 and x1; reads
at t = 1,000 to 5,000. The block means of every endpoint go to git (probes/results/p21_fn001_design_inputs.json); the
means with the SD of the four block means go to scratch (the same name under RUNS).
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

from fn001 import design as D  # noqa: E402
from fn001 import worker as W  # noqa: E402

OUT = LANE / "probes" / "results" / "p21_fn001_design_inputs.json"
RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes")
ENDS = ("sign", "r_sign", "patch", "r_patch", "intact", "islands", "walls", "bond_err")


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
    jobs = [(u, b) for u in D.UNITS for b in blocks]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        res = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    slim, full = {}, {}
    for u in D.UNITS:
        rows = sorted((r for r in res if r[0] == u), key=lambda r: r[1])
        for b in D.BODIES:
            for ep in ENDS:
                x = np.stack([r[2][f"{b}/{ep}"] for r in rows])              # (blocks, reads, conds)
                slim.setdefault(u, {}).setdefault(b, {})[ep] = np.round(x.mean(0), 4).tolist()
                full.setdefault(u, {}).setdefault(b, {})[ep] = {"mean": np.round(x.mean(0), 4).tolist(),
                                                                "sd": np.round(x.std(0, ddof=1), 4).tolist()}
    head = {"probe": "P21", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
            "draft_digest": D.digest(), "conds": [c.name for c in D.CONDS], "reads": list(D.READS),
            "units": list(D.UNITS), "layout": "levels[unit][body][endpoint][read][cond], block means",
            "task_wall_s": {f"{r[0]}/{r[1]}": r[3] for r in res},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(dict(head, levels=slim), separators=(",", ":")) + "\n")
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / OUT.name).write_text(json.dumps(dict(head, levels=full), separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) in {head['wall_s']} s")


if __name__ == "__main__":
    main()
