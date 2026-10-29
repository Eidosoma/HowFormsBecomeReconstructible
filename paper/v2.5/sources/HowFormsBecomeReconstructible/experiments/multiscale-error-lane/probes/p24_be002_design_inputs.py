"""Engineering probe P24 (python probes/p24_be002_design_inputs.py CPUS): BE002's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for BE002's registered statements, run before the freeze.

BE002's draft (be002/design.py, be002/sim.py) on engineering blocks 900640-900643 (32 cases) under the probe's tag
mse-p24: both bodies; S4, LB and F0 at theta x0 and x1; read gain 0.2; eleven runs (none, scattered cue damage, memory
damage and legitimate change of a 4 x 4 patch, legitimate change of an 8 x 8 patch, each with and without the regime
signal, and memory damage of a 4 x 4 patch with a late signal); seven arms; p_b = 1e-3; reads at t = 250, 1,000, 2,000
and 4,000. Writes block means of the record's endpoints to probes/results/p24_be002_design_inputs.json and, with the
SDs over blocks, each block's values (for paired contrasts), the body's endpoints and the patch traces, to the lane's
scratch probes folder.
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

from be002 import design as D  # noqa: E402
from be002 import sim  # noqa: E402
from be002.worker import ENDS  # noqa: E402

OUT = LANE / "probes" / "results" / "p24_be002_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p24_be002_design_inputs_full.json")
GIT_ENDS = ("r_all", "r_in", "r_fp", "r_out", "r_in_old", "opened", "opened_out")


def job(args):
    unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, na = len(cases), len(D.ARMS)
    res = {}
    for body in D.BODIES:
        for s, size, sig in D.RUNS:
            o = sim.run(body, s, size, sig, cases, V0, ema0, R0, th, T, theta, set(D.READS), tag=D.PROBE_TAG)
            key = f"{body}/{D.run_name(s, size, sig)}"
            for e in ENDS:
                if e in o:
                    res[f"{key}/{e}"] = o[e].reshape(len(D.READS), na, k).mean(-1)
            res[f"{key}/opened"] = o["opened"].reshape(na, k).mean(-1)
            res[f"{key}/opened_out"] = o["opened_out"].reshape(na, k).mean(-1)
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
            full.setdefault(u, {})[key] = {"mean": np.round(x.mean(0), 4).tolist(), "sd": np.round(x.std(0, ddof=1), 4).tolist(),
                                           "blocks": np.round(x, 5).tolist()}
            if key.split("/")[-1] in GIT_ENDS:
                means.setdefault(u, {})[key] = np.round(x.mean(0), 3 if not key.split("/")[-1].startswith("opened") else 5).tolist()
    head = {"probe": "P24", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
            "layout": "levels[unit]['body/run/endpoint'][read][arm] (opened, opened_out: [arm]); block means; "
                      "run = situation + patch side + signal ('_sig' on at 1-1,000, '_late' at 1,001-2,000)",
            "arms": list(D.ARMS), "runs": list(D.RUNNAMES), "reads": list(D.READS), "sig": D.SIG,
            "draft_digest": D.digest(), "units": list(D.UNITS), "task_wall_s": {f"{r[0]}/{r[1]}": r[3] for r in out},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({**head, "levels": means}, separators=(",", ":")) + "\n")
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps({**head, "levels": full}, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) and {FULL} in {head['wall_s']} s")


if __name__ == "__main__":
    main()
