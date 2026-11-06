"""One AR001C (body, unit, block) task: ar001.worker.task, imported unchanged, with AR001C's reduced runs (the vote, rest and
dial in AR001's seven sigma-0 situations). Writes an endpoint shard, a raw-state shard and a completion record, each
atomically, in ar001.worker.run_task's layout; the meta names AR001C's runs and digests (AR001C's and AR001's).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from ar001 import design as A
from ar001 import worker as AW

from . import design as D


def run_task(body, unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, signal, cases = AW.task(body, unit, block, purpose, tag, runs=D.RUNS)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {body} {unit} {block}: {bad[:5]}")
    meta = {"study": D.STUDY, "body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag,
            "design_digest": D.digest(), "ar001_digest": A.digest(), "numpy": np.__version__, "timing_s": timing,
            "signal_updates": signal, "cases": [c.key() for c in cases],
            "runs": [[D.run_name(*x), list(x[2])] for x in D.RUNS], "reads": list(A.READS)}
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
