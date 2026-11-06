"""One (event, block) task: every arm the event runs (nl001.design.RUNS), batched and paired over the block's 8 cases.
Writes an endpoint shard (each endpoint as reads x arms x cases), a raw-state shard (the final records, arms x cases x
64 x 64) and a completion record, each atomically.
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


def task(event, block, purpose, tag=D.TAG):
    cases = sim.cases_for(block, purpose)
    labels = [(D.ARM[a], event) for a in D.RUNS[event]]
    ends, r = sim.run(cases, labels, tag=tag)
    return ends, {"r": r}, cases


def run_task(event, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, cases = task(event, block, purpose, tag)
    bad = [k for k, v in raw.items() if not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite arrays in {event} {block}: {bad}")
    meta = {"event": event, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "arms": list(D.RUNS[event]), "reads": list(D.READS), "ends": list(sim.ENDS),
            "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", {f"{event}/{k}": v for k, v in ends.items()}), ("raw", {f"{event}/{k}": v for k, v in raw.items()})):
        folder = root / kind / event
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"event": event, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / event / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
