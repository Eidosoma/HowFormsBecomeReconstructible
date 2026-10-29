"""Engineering probe P23 (python probes/p23_be001_design_inputs.py CPUS): BE001's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for BE001's registered statements, run before the freeze.

BE001's draft (be001/design.py, be001/sim.py) on engineering blocks 900790-900793 (32 cases) under the probe's tag
mse-p23: both bodies; S4, LB and F0 at theta x0 and x1; read gain 0.2; nine runs (none, scattered cue damage, memory
damage and legitimate change on patches of side 4, 8 and 12, shared damage at 8); ten arms; p_b = 1e-3; reads at
t = 250, 1,000, 2,000 and 4,000. Writes block means to probes/results/p23_be001_design_inputs.json (means only) and, with
the SDs over blocks and the patch traces, to the lane's scratch probes folder.
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

from be001 import design as D  # noqa: E402
from be001 import sim  # noqa: E402

OUT = LANE / "probes" / "results" / "p23_be001_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p23_be001_design_inputs_full.json")
ENDS = ("r_all", "r_in", "v_all", "v_in", "r_in_old", "v_in_old")


def job(args):
    unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, na = len(cases), len(D.ARMS)
    res = {}
    for body in D.BODIES:
        for s, size in D.RUNS:
            o = sim.run(body, s, size, cases, V0, ema0, R0, th, T, theta, set(D.READS), tag=D.PROBE_TAG)
            key = f"{body}/{D.run_name(s, size)}"
            for e in ENDS:
                if e in o:
                    res[f"{key}/{e}"] = o[e].reshape(len(D.READS), na, k).mean(-1)
            res[f"{key}/opened"] = o["opened"].reshape(na, k).mean(-1)
            res[f"{key}/trace"] = o["trace"].reshape(-1, na, k).mean(-1)
    return unit, block, res, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    blocks = list(range(*D.PROBE_BLOCKS))
    jobs = [(u, b) for u in D.UNITS for b in blocks]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        out = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    means, full = {}, {}
    for u in D.UNITS:
        rows = sorted((r for r in out if r[0] == u), key=lambda r: r[1])
        for key in rows[0][2]:
            x = np.stack([r[2][key] for r in rows])
            full.setdefault(u, {})[key] = {"mean": np.round(x.mean(0), 4).tolist(), "sd": np.round(x.std(0, ddof=1), 4).tolist()}
            if not key.endswith("/trace"):
                means.setdefault(u, {})[key] = np.round(x.mean(0), 3 if not key.endswith("/opened") else 5).tolist()
    head = {"probe": "P23", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
            "layout": "levels[unit]['body/run/endpoint'][read][arm] (opened: [arm]); block means; run = situation + patch side",
            "arms": list(D.ARMS), "runs": [D.run_name(s, z) for s, z in D.RUNS], "reads": list(D.READS), "bio": D.BIO,
            "draft_digest": D.digest(), "units": list(D.UNITS), "task_wall_s": {f"{r[0]}/{r[1]}": r[3] for r in out},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({**head, "levels": means}, separators=(",", ":")) + "\n")
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps({**head, "levels": full}, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) and {FULL} in {head['wall_s']} s")


if __name__ == "__main__":
    main()
