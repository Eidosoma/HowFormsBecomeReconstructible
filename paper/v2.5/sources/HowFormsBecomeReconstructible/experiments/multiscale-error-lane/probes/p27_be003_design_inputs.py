"""Engineering probe P27 (python probes/p27_be003_design_inputs.py CPUS): BE003's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for BE003's registered statements, run before the freeze.

BE003's draft (be003/design.py, be003/sim.py) on engineering blocks 900670-900673 (32 cases) under the probe's tag
mse-p27: every run (regrow8, regrow8_late, regrow+cue8, twin4@0, twin4@300, twin4@2000) with its arms, both bodies, S4 and
F0 in quiet tissue; block means over each block's 8 cases at every read, the committed shares, and the traces every 100
updates. Blocks 900670-900677 lie in the span ENGINE.md reserved for P1-P4c (900000-900699) but were never drawn (a scan of
the lane's .py, .md and .json files on 28 October 2026 found 900600-900616, 900640-900648 and 900650-900658 in the 9006xx
range, and 900699 as a bound). Writes means and SDs over blocks to probes/results/p27_be003_design_inputs.json and every
block's values to the lane's scratch probes folder.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be003 import design as D  # noqa: E402
from be003 import worker as W  # noqa: E402

OUT = LANE / "probes" / "results" / "p27_be003_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p27_be003_design_inputs_full.json")
TAG = D.PROBE_TAG
BLOCKS = list(range(*D.PROBE_BLOCKS))


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def job(args):
    unit, body, block, run = args
    t0 = time.time()
    ends, _, solvers, signal = W.one(body, unit, block, "engineering", run, TAG)
    res = {k: np.asarray(v, float).mean(-1).tolist() for k, v in ends.items()}       # block means over the 8 cases
    return unit, body, block, D.run_name(*run), res, solvers, signal, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    print(f"{utc()} P27 start on cpus {cpus}", flush=True)
    jobs = sorted(((u, b, blk, run) for run in D.RUNS for u in D.UNITS for b in D.BODIES for blk in BLOCKS),
                  key=lambda j: -(D.run_window(*j[3]) * len(D.run_arms(*j[3]))))
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    full, walls, solv = {}, {}, {}
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        futs = [pool.submit(job, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            u, b, blk, rn, res, solvers, signal, w = f.result()
            for key, v in res.items():
                full.setdefault(u, {}).setdefault(f"{b}/{key}", {})[blk] = v
            walls[f"{u}/{b}/{blk}/{rn}"] = w
            solv[f"{u}/{b}/{blk}/{rn}"] = {"solvers": solvers, "signal_updates": signal}
            print(f"{utc()} done {i}/{len(jobs)} {u} {b} {blk} {rn} {w} s", flush=True)
    summary = {}
    for u, node in full.items():
        for key, per in node.items():
            x = np.array([per[blk] for blk in BLOCKS], float)
            summary.setdefault(u, {})[key] = {"mean": x.mean(0).tolist(), "sd": x.std(0, ddof=1).tolist()}
    head = {"probe": "P27", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": BLOCKS,
            "design_digest_draft": D.digest(), "arms": D.ARMS, "runs": list(D.RUNNAMES),
            "run_arms": {D.run_name(*x): D.run_arms(*x) for x in D.RUNS},
            "run_reads": {D.run_name(*x): D.run_reads(*x) for x in D.RUNS},
            "finished_utc": utc(), "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(walls.values()), 1),
            "job_wall_s": walls, "solvers": solv}
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps(dict(head, blocks_values=full), separators=(",", ":")) + "\n")
    keep = ("/r_", "/opened", "/maturity", "/filled")
    slim = {u: {k: {s: np.round(v[s], 5).tolist() for s in ("mean", "sd")} for k, v in node.items()
                if any(x in k for x in keep) and "/trace_" not in k} for u, node in summary.items()}
    OUT.write_text(json.dumps(dict(head, summary=slim), separators=(",", ":")) + "\n")
    print(f"{utc()} wrote {OUT} ({OUT.stat().st_size} B) and {FULL}", flush=True)


if __name__ == "__main__":
    main()
