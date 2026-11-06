"""One SM004 TEST (unit, block) task: sm003.worker.task unchanged (SM002's task for the unit plus the g = 4 read of the same
float64 final records), called with SM004's tag; this module writes its endpoint shard, raw-state shard and completion
record under SM004's design digest, each atomically, in sm003.worker.run_task's format. The bridges (Q3) check it against
sm003.worker.task in-process and, with P45's tag, against one of SM003's P45 records bit for bit.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from sm001 import design as S1D
from sm003 import worker as W3

from . import design as D


def task(unit, block, purpose, tag=D.TAG):
    return W3.task(unit, block, purpose, tag)


def run_task(unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(unit, block, purpose, tag)
    bad = [kk for kk, v in ends.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite endpoints in {unit} {block}: {bad[:5]}")
    meta = {"study": D.STUDY, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "arms": [a["name"] for a in S1D.unit_arms(unit)],
            "sizes": list(S1D.UNIT[unit]["sizes"]), "reads": list(S1D.READS), "reads2": list(S1D.READS2),
            "grains": list(D.unit_grains(unit)), "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(), "files": out,
              "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
