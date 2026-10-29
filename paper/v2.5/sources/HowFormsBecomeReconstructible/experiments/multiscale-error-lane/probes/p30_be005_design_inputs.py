"""Engineering probe P30 (python probes/p30_be005_design_inputs.py CPUS): BE005's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for BE005's registered statements, run before the freeze.

BE005's draft (be005/design.py, be005/sim.py) on engineering blocks 900620-900623 (32 cases) under the probe's tag
mse-p30: every run (memory4@0, the twelve delayed memory runs of panel D, change4@0, cue4@0) with its arms, both bodies,
BE001's six units; block means over each block's 8 cases at every read, the committed shares, the onset evidence, the
sensors right at the signal's onset, the patch's share ever triggered, the patch's anchor counts and the traces every
100 updates. Blocks 900620-900627 lie in mse.assay's reserved engineering range (900000-900999); a scan of the lane's
docs, code, results and scratch shard names on 29 October 2026 found 900617-900639 unused. Writes means and SDs over
blocks to probes/results/p30_be005_design_inputs.json and every block's values to the lane's scratch probes folder."""
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

from be005 import design as D  # noqa: E402
from be005 import worker as W  # noqa: E402

OUT = LANE / "probes" / "results" / "p30_be005_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p30_be005_design_inputs_full.json")
TAG = D.PROBE_TAG
BLOCKS = list(range(*D.PROBE_BLOCKS))


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def job(args):
    unit, body, block, run = args
    t0 = time.time()
    ends, _, signal = W.one(body, unit, block, "engineering", run, TAG)
    res = {k: np.asarray(v, float).mean(-1).tolist() for k, v in ends.items()}       # block means over the 8 cases
    return unit, body, block, D.run_name(*run), res, signal, round(time.time() - t0, 1)


def main():
    if sys.argv[1] == "--reslim":
        F = json.loads(FULL.read_text())
        write_slim(F["blocks_values"], {k: v for k, v in F.items() if k != "blocks_values"})
        return
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    print(f"{utc()} P30 start on cpus {cpus}, 1-min load {open('/proc/loadavg').read().split()[0]}", flush=True)
    jobs = sorted(((u, b, blk, run) for run in D.RUNS for u in D.UNITS for b in D.BODIES for blk in BLOCKS),
                  key=lambda j: -len(j[3][3]))
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    full, walls, sig = {}, {}, {}
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        futs = [pool.submit(job, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            u, b, blk, rn, res, signal, w = f.result()
            for key, v in res.items():
                full.setdefault(u, {}).setdefault(f"{b}/{key}", {})[blk] = v
            walls[f"{u}/{b}/{blk}/{rn}"] = w
            sig[f"{u}/{b}/{blk}/{rn}"] = signal
            if i % 12 == 0 or i == len(jobs):
                print(f"{utc()} done {i}/{len(jobs)} {u} {b} {blk} {rn} {w} s", flush=True)
    head = {"probe": "P30", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": BLOCKS,
            "design_digest_draft": D.digest(), "arms": D.ARMS, "runs": list(D.RUNNAMES),
            "run_arms": {D.run_name(*x): list(x[3]) for x in D.RUNS}, "reads": D.READS,
            "finished_utc": utc(), "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(walls.values()), 1),
            "job_wall_s": walls, "signal_updates": sig}
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps(dict(head, blocks_values=full), separators=(",", ":")) + "\n")
    write_slim(full, head)


def write_slim(full, head):
    """The lane's copy: means and SDs over blocks at t = 4,000 (and the per-arm scalars), no traces; every block's values
    stay in the scratch copy. (Also: python probes/p30_be005_design_inputs.py --reslim, from the scratch copy.)"""
    summary = {}
    for u, node in full.items():
        for key, per in node.items():
            x = np.array([per[blk] if blk in per else per[str(blk)] for blk in BLOCKS], float)
            summary.setdefault(u, {})[key] = {"mean": x.mean(0), "sd": x.std(0, ddof=1)}
    slim = {}
    for u, node in summary.items():
        for k, v in node.items():
            if k.rsplit("/", 1)[1] == "trace":
                continue
            pick = (lambda a: a) if v["mean"].ndim < 2 else (lambda a: a[-1])
            slim.setdefault(u, {})[k] = {s: np.round(pick(v[s]), 4).tolist() for s in ("mean", "sd")}
    OUT.write_text(json.dumps(dict(head, job_wall_s=None, signal_updates=None, summary=slim), separators=(",", ":")) + "\n")
    print(f"{utc()} wrote {OUT} ({OUT.stat().st_size} B) and {FULL}", flush=True)

if __name__ == "__main__":
    main()
