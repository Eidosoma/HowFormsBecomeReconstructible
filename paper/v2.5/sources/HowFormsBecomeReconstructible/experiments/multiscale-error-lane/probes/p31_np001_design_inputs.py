"""Engineering probe P31 (python probes/p31_np001_design_inputs.py CPUS): NP001's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for NP001's registered statements, run before the freeze.

NP001's draft (np001/design.py, np001/sim.py, np001/worker.py) on engineering blocks 900628-900631 (32 cases) under the
probe's tag mse-p31: every task (four bodies x nine units: six patterns and three phase conflicts), stage 1 under every
condition and stage 2 with every successor body reading every handed record and the paired no-record control. Version 2
(after the lead's review: li2 and the phase conflicts added); version 1's shards are kept in the scratch np001/p31_v1
folder, and every endpoint and state version 1 wrote is compared bit for bit with version 2's. Block means over each block's 8 cases at
every read. Blocks 900628-900635 lie in mse.assay's reserved engineering range (900000-900999); a scan of the lane's
design files, documents and scratch shard names on 29 October 2026 found them unused (BE005 ends at 900627). Writes
means and SDs over blocks at the last reads to probes/results/p31_np001_design_inputs.json and every block's values at
every read to the lane's scratch probes folder; the shards stay in the scratch np001/p31 folder."""
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

from np001 import design as D  # noqa: E402
from np001 import sim  # noqa: E402
from np001 import worker as W  # noqa: E402

OUT = LANE / "probes" / "results" / "p31_np001_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p31_np001_design_inputs_full.json")
ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/np001/p31")
TAG = D.PROBE_TAG
BLOCKS = list(range(*D.PROBE_BLOCKS))


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def job(body, unit, block):
    done = ROOT / "done" / body / unit / f"{block}.json"
    if done.exists():
        return json.loads(done.read_text())
    return W.run_task(body, unit, block, "engineering", str(ROOT), tag=TAG)


def values(body, unit, block):
    """Block means over the block's cases of every endpoint at every read: s1[cond][end][read], s2[B][branch][end][read]."""
    e = np.load(ROOT / "shards" / body / unit / f"{block}.npz")
    s1 = {c: {x: [round(float(v), 6) for v in e[f"s1/{x}"][:, i].mean(-1)] for x in sim.ENDS1}
          for i, c in enumerate(D.CONDNAMES)}
    s2 = {B: {c: {x: [round(float(v), 6) for v in e[f"s2/{B}/{x}"][:, i].mean(-1)] for x in sim.ENDS2}
              for i, c in enumerate(W.BRANCHES2)} for B in D.SUCC_BODIES}
    return {"s1": s1, "s2": s2}


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    os.sched_setaffinity(0, cpus)
    t0, start = time.time(), utc()
    load = float(open("/proc/loadavg").read().split()[0])
    todo = [(b, u, blk) for b, u in D.tasks() for blk in BLOCKS]
    print(f"{start} P31: {len(todo)} tasks on cpus {cpus} (1-min load {load})", flush=True)
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    recs = {}
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        futures = {pool.submit(job, *t): t for t in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            t = futures[fut]
            rec = fut.result()
            recs[t] = rec
            print(f"{utc()} done {i}/{len(todo)} {t} wall {rec['wall_s']} s cpu {rec['cpu_s']} s", flush=True)
    full = {f"{b}/{u}": {str(blk): values(b, u, blk) for blk in BLOCKS} for b, u in D.tasks()}
    cpu_s = sum(r["cpu_s"] for r in recs.values())
    meta = {"probe": "P31", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": BLOCKS,
            "cases_per_block": D.NCASE, "design_digest": D.digest(), "started_utc": start, "finished_utc": utc(),
            "wall_s": round(time.time() - t0, 1), "cpu_s": round(cpu_s, 1), "cpus": cpus, "load_1min_start": load,
            "worker_maxrss_mb_peak": max(r["maxrss_mb"] for r in recs.values()),
            "task_cpu_s": {f"{b}/{u}": round(float(np.mean([recs[(b, u, blk)]["cpu_s"] for blk in BLOCKS])), 2)
                           for b, u in D.tasks()},
            "reads": D.READS, "reads2": D.READS2, "conds": D.CONDNAMES, "branches2": W.BRANCHES2}
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps({"meta": meta, "values": full}) + "\n")
    summ = {}
    for key, per in full.items():
        blocks = [per[str(blk)] for blk in BLOCKS]
        s1 = {c: {x: [round(float(np.mean([v["s1"][c][x][-1] for v in blocks])), 4),
                      round(float(np.std([v["s1"][c][x][-1] for v in blocks], ddof=1)), 4)]
                  for x in ("align", "r_align", "shape", "spacing", "align_b", "r_align_b")} for c in D.CONDNAMES}
        s2 = {B: {c: {x: [round(float(np.mean([v["s2"][B][c][x][-1] for v in blocks])), 4),
                          round(float(np.std([v["s2"][B][c][x][-1] for v in blocks], ddof=1)), 4)]
                      for x in ("align", "shape", "align_b")} for c in W.BRANCHES2} for B in D.SUCC_BODIES}
        summ[key] = {"s1_t4000": s1, "s2_t2000": s2}
    OUT.write_text(json.dumps({"meta": meta, "mean_sd_over_blocks": summ}, indent=0) + "\n")
    print(f"{utc()} P31 finished: wall {meta['wall_s']} s, cpu {cpu_s:.0f} s; {OUT} ({OUT.stat().st_size} bytes)",
          flush=True)


if __name__ == "__main__":
    main()
