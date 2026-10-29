"""Engineering probe P20 (python probes/p20_lr005_design_inputs.py CPUS): LR005's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for LR005's registered statements, run before the freeze.

LR005's draft (lr005/design.py, lr005/sim.py) on engineering blocks 900760-900763 (32 cases) under the probe's tag
mse-p20: both bodies; S4, LB and F0 at theta x0 and x1; read gains 0.05 and 0.2; six situations (none, body, memory,
shared, cue, change); seven arms; p_b = 1e-3; reads at t = 250, 1,000, 2,000 and 4,000. Writes block means to
probes/results/p20_lr005_design_inputs.json (means only) and, with the SDs over blocks and the patch traces, to the
lane's scratch probes folder.
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

from lr005 import design as D  # noqa: E402
from lr005 import sim  # noqa: E402

OUT = LANE / "probes" / "results" / "p20_lr005_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p20_lr005_design_inputs_full.json")
UNITS = tuple(f"{p}_t{t:g}" for p in D.PATTERNS for t in D.THETAS)
ENDS = ("r_all", "r_in", "v_all", "v_in", "r_in_old", "v_in_old")


def job(args):
    unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    pattern, theta = unit.split("_")[0], float(unit.split("_t")[1])
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, na = len(cases), len(D.ARMS)
    res = {}
    for body in D.BODIES:
        for gain in D.GAINS:
            for s in D.SITUATIONS:
                o = sim.run(body, s, cases, V0, ema0, R0, th, T, theta, gain, set(D.READS), tag=D.PROBE_TAG)
                key = f"{body}/{gain:g}/{s}"
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
    jobs = [(u, b) for u in UNITS for b in blocks]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        out = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    means, full = {}, {}
    for u in UNITS:
        rows = sorted((r for r in out if r[0] == u), key=lambda r: r[1])
        for key in rows[0][2]:
            x = np.stack([r[2][key] for r in rows])
            full.setdefault(u, {})[key] = {"mean": np.round(x.mean(0), 4).tolist(), "sd": np.round(x.std(0, ddof=1), 4).tolist()}
            if not key.endswith("/trace"):
                means.setdefault(u, {})[key] = np.round(x.mean(0), 3).tolist()
    head = {"probe": "P20", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
            "layout": "levels[unit]['body/gain/situation/endpoint'][read][arm] (opened: [arm]); block means",
            "arms": list(D.ARMS), "situations": list(D.SITUATIONS), "gains": list(D.GAINS), "reads": list(D.READS),
            "rate": D.RATE, "community": D.COMMUNITY, "units": list(UNITS),
            "task_wall_s": {f"{r[0]}/{r[1]}": r[3] for r in out},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({**head, "levels": means}, separators=(",", ":")) + "\n")
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps({**head, "levels": full}, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) and {FULL} in {head['wall_s']} s")


if __name__ == "__main__":
    main()
