"""One (body, unit, block) task: DL002's acquisition, then one body under every run (event, patch side, delay), each with
its arms. Writes an endpoint shard, a raw-state shard and a completion record, each atomically. Templates reach only the
record's acquisition, the event's target and the scoring; the anchors hold the acquired record's signs; the body never
reads the templates; the signal reads neither.
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
SCALARS = ("opened", "opened_out", "onset", "hit", "anc_on")   # per arm and case over the run


def one(body, unit, block, purpose, run, tag=D.TAG, prepared=None):
    """One run of one task: its endpoints (reads x arms x cases), trace, per-arm scalars and final states."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = prepared if prepared is not None else sim.prepare(pattern, block, purpose)
    situation, size, delay, arms = run
    k, na, nr = len(cases), len(arms), len(D.READS)
    o = sim.run(body, situation, size, delay, arms, cases, V0, ema0, R0, th, T, theta, set(D.READS), tag=tag)
    key = D.run_name(*run)
    ends = {f"{key}/{e}": o[e].reshape(nr, na, k) for e in ENDS if e in o}
    for e in SCALARS:
        ends[f"{key}/{e}"] = o[e].reshape(na, k)
    ends[f"{key}/n_anc"] = o["n_anc"]
    ends[f"{key}/trace"] = o["trace"].reshape(-1, na, k)
    raw = {f"{key}/{x}": o[x].reshape(na, k, D.SIDE, D.SIDE).astype(np.int8 if x in ("H", "W") else o[x].dtype)
           for x in ("V", "r", "H", "W")}
    return ends, raw, o["signal_updates"]


def task(body, unit, block, purpose, tag=D.TAG, runs=D.RUNS):
    pattern, theta = D.parse_unit(unit)
    prepared = sim.prepare(pattern, block, purpose)
    ends, raw, timing, signal = {}, {"V0": prepared[1], "R0": prepared[3], "T": prepared[5]}, {}, {}
    for run in runs:
        t1 = time.time()
        e, r, n = one(body, unit, block, purpose, run, tag, prepared)
        ends.update(e)
        raw.update(r)
        key = D.run_name(*run)
        timing[key], signal[key] = round(time.time() - t1, 3), n
    return ends, raw, timing, signal, prepared[0]


def run_task(body, unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, signal, cases = task(body, unit, block, purpose, tag)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {body} {unit} {block}: {bad[:5]}")
    meta = {"body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "signal_updates": signal, "cases": [c.key() for c in cases]}
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
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing, "signal_updates": signal,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
