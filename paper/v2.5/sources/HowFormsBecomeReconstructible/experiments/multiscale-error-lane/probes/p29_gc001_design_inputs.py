"""P29 (python probes/p29_gc001_design_inputs.py --cpus LIST): GC001's design inputs. ENGINEERING_PROBE_NOT_EVIDENCE.

Engineering blocks 900690-900693 under tag mse-p29 (not GC001's development tag), 8 cases each: every unit, body, run and
arm of the draft design for the full window. Saves each block's case means of every endpoint (per unit, body and run)
to scratch (p29_gc001_design_inputs_full.json, the per-block values the margins need) and the means and SDs over the
four blocks to probes/results/p29_gc001_design_inputs.json.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from gc001 import design as D  # noqa: E402
from gc001 import sim  # noqa: E402

BLOCKS = tuple(range(*D.PROBE_BLOCKS))
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p29_gc001_design_inputs_full.json")
OUT = LANE / "probes" / "results" / "p29_gc001_design_inputs.json"


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def job(unit, body, block):
    t0, c0 = time.time(), time.process_time()
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, na = len(cases), len(D.ARMS)
    vals = {}
    for s, size, sigma in D.RUNS:
        key = f"{body}/{D.run_name(s, size, sigma)}"
        o = sim.run(body, s, size, sigma, cases, V0, ema0, R0, th, T, theta, set(D.READS), tag=D.PROBE_TAG)
        for e in sim.ENDS:
            if e in o:
                vals[f"{key}/{e}"] = o[e].reshape(len(D.READS), na, k).mean(-1).tolist()
        vals[f"{key}/opened"] = o["opened"].reshape(na, k).mean(-1).tolist()
        vals[f"{key}/trace_all"] = o["trace_all"].reshape(-1, na, k).mean(-1)[1::2].tolist()
        for e in ("misread", "misread_band"):
            vals[f"{key}/{e}"] = float(o[e].mean())
    return unit, body, block, vals, time.time() - t0, time.process_time() - c0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpus", required=True)
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    jobs = [(u, b, blk) for u in D.UNITS for b in D.BODIES for blk in BLOCKS]
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    values, walls, cpu_s = {}, {}, 0.0
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        futs = [pool.submit(job, *j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            u, b, blk, vals, wall, cpu = f.result()
            for key, v in vals.items():
                values.setdefault(u, {}).setdefault(key, {})[str(blk)] = v
            walls[f"{u}/{b}/{blk}"] = round(wall, 1)
            cpu_s += cpu
            print(f"{time.strftime('%H:%M:%SZ', time.gmtime())} done {i}/{len(jobs)} {u} {b} {blk} {wall:.0f} s", flush=True)
    head = {"probe": "P29", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": list(BLOCKS),
            "design_digest_draft": D.digest(), "arms": D.ARMS, "runs": D.RUNNAMES, "reads": D.READS,
            "started_utc": started, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cpu_s": round(cpu_s, 1), "job_wall_s": walls}
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps(dict(head, blocks_values=values), separators=(",", ":")) + "\n")
    summarize(head, values)
    print("wrote", FULL, FULL.stat().st_size, "and", OUT, OUT.stat().st_size, "cpu_h", round(cpu_s / 3600, 2))


def summarize(head, values):
    """Means and SDs over the four blocks at t = 4,000 (endpoints read at several times keep only the last read), so the
    git file stays under 256 KB; the full per-block values stay in scratch."""
    summary = {}
    for u, node in values.items():
        for key, per in node.items():
            if key.endswith("trace_all"):
                continue
            x = np.array([per[str(blk)] for blk in BLOCKS], float)
            if x.ndim == 3:
                x = x[:, -1]
            summary.setdefault(u, {})[key] = {"mean": np.round(x.mean(0), 5).tolist(), "sd": np.round(x.std(0, ddof=1), 5).tolist()}
    OUT.write_text(json.dumps(dict(head, summary_at=D.READS[-1], summary=summary), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["--summarize"]:            # rebuild the git summary from the scratch file, no simulation
        F = json.loads(FULL.read_text())
        summarize({k: v for k, v in F.items() if k != "blocks_values"}, F["blocks_values"])
        print("wrote", OUT, OUT.stat().st_size)
    else:
        main()
