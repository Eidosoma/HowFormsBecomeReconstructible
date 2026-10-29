"""One (body, unit, block) task: DL002's acquisition, then one body under every run (situation, delay, signal timing),
each with its arms. Writes an endpoint shard, a raw-state shard and a completion record, each atomically. Templates reach
only the record's acquisition, the event's target and the scoring; the anchors hold the acquired record's signs; the body
never reads the templates.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from . import design as D
from . import sim

ENDS = sim.ENDS


def one(body, unit, block, purpose, run, tag=D.TAG, prepared=None):
    """One run of one task: its endpoints (reads x arms x cases), traces and final states."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = prepared if prepared is not None else sim.prepare(pattern, block, purpose)
    k, arms, reads = len(cases), D.run_arms(*run), D.run_reads(*run)
    na, nr = len(arms), len(reads)
    o = sim.run(body, run[0], run[1], run[2], cases, V0, ema0, R0, th, T, theta, set(reads), tag=tag, arms=arms)
    key = D.run_name(*run)
    ends = {f"{key}/{e}": o[e].reshape(nr, na, k) for e in ENDS if e in o}
    ends[f"{key}/opened"] = o["opened"].reshape(na, k)
    ends[f"{key}/opened_out"] = o["opened_out"].reshape(na, k)
    for x in sim.TRACED:
        ends[f"{key}/trace_{x}"] = o[f"trace_{x}"].reshape(-1, na, k)
    raw = {f"{key}/{x}": o[x].reshape(na, k, D.SIDE, D.SIDE).astype(np.int8 if x in ("H", "W") else o[x].dtype)
           for x in ("V", "r", "H", "W")}
    raw[f"{key}/occ"] = o["occ"].reshape(na, k, D.SIDE, D.SIDE)[0]
    return ends, raw, o["solvers"], o["signal_updates"]


def task(body, unit, block, purpose, tag=D.TAG, runs=D.RUNS):
    pattern, theta = D.parse_unit(unit)
    prepared = sim.prepare(pattern, block, purpose)
    ends, raw, timing, solvers, signal = {}, {"V0": prepared[1], "R0": prepared[3], "T": prepared[5]}, {}, {}, {}
    for run in runs:
        t1 = time.time()
        e, r, s, n = one(body, unit, block, purpose, run, tag, prepared)
        ends.update(e)
        raw.update(r)
        key = D.run_name(*run)
        timing[key], solvers[key], signal[key] = round(time.time() - t1, 3), s, n
    return ends, raw, timing, solvers, signal, prepared[0]


def run_task(body, unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, solvers, signal, cases = task(body, unit, block, purpose, tag)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {body} {unit} {block}: {bad[:5]}")
    meta = {"body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "solvers": solvers, "signal_updates": signal,
            "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / body / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing, "solvers": solvers, "signal_updates": signal,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
