"""One (panel, unit, block) task: DL002's acquisition, then both bodies under every condition. Writes an endpoint
shard, a raw-state shard and a completion record, each atomically. Templates reach only the scoring and the record's
acquisition (as DL002 and LR002); the anchors hold the acquired record's signs, as DL002's anchors did; the body never
reads the templates.
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


def task(panel, unit, block, purpose, tag=D.TAG, conds=D.CONDS, reads=D.READS, window=D.WINDOW):
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, purpose)
    k, nc, nr = len(cases), len(conds), len(reads)
    ends, raw, timing = {}, {"V0": V0, "R0": R0, "T": T}, {}
    for b in D.BODIES:
        t1 = time.time()
        o = sim.run(b, conds, cases, V0, ema0, R0, th, T, theta, set(reads), tag, window=window)
        for key in ("sign", "r_sign", "agree", "bond_err"):
            ends[f"{b}/{key}"] = o[key].reshape(nr, nc, k)
        ends[f"{b}/flip_rate"] = o["flip_rate"].reshape(nc, k)
        ends[f"{b}/opened"] = o["opened"].reshape(nc, k)
        raw[f"{b}/V"] = o["V"].reshape(nc, k, D.SIDE, D.SIDE)
        raw[f"{b}/r"] = o["r"].reshape(nc, k, D.SIDE, D.SIDE)
        raw[f"{b}/H"] = o["H"].reshape(nc, k, D.SIDE, D.SIDE).astype(np.int8)
        raw[f"{b}/W"] = o["W"].reshape(nc, k, D.SIDE, D.SIDE).astype(np.int8)
        timing[b] = round(time.time() - t1, 3)
    return ends, raw, timing, cases


def run_task(panel, unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(panel, unit, block, purpose, tag)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {panel} {unit} {block}: {bad[:5]}")
    meta = {"panel": panel, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / panel / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"panel": panel, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / panel / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
