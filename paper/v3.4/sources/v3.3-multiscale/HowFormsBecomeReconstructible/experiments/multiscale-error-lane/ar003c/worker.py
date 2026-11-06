"""One AR003C (body, unit, block) task: ar003.worker.task, imported unchanged, with AR003C's reduced runs (the vote through
ar001.sim.run, det through ar002.sim.run_det and vms through ar003.sim.run_vd, in only the runs C1-C3 need), and the
detectors as frozen in ar003.design. Writes an endpoint shard, a raw-state shard and a completion record, each
atomically, in ar003.worker.run_task's layout; the meta names AR003C's runs and digests (AR003C's and AR003's).

reference_task: AR003's full development task (ar003.worker.run_task, imported unchanged, every one of its 63 arm-runs)
on an engineering block, the bridge's reference.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from ar003 import design as A3
from ar003 import worker as AW

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
            "design_digest": D.digest(), "ar003_digest": A3.digest(), "numpy": np.__version__, "timing_cpu_s": timing,
            "signal_updates": signal, "cases": [c.key() for c in cases], "detectors": D.DETECTORS,
            "vd_detectors": D.VD_DETECTORS, "runs": [[D.run_name(*x), list(D.arms_of(x))] for x in D.RUNS],
            "parts": {D.run_name(*x): [list(x[2]), list(x[3]), list(x[4])] for x in D.RUNS},
            "sizes": {D.run_name(*x): x[5] for x in D.RUNS}, "reads": list(D.READS)}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / body / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta, default=list)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_cpu_s": timing, "signal_updates": signal,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record


def reference_task(body, unit, block, purpose, root, tag=D.TAG):
    """AR003's full development task on an engineering block (ar003.worker.run_task, unchanged): the bridge's reference."""
    assert purpose == "engineering" and block in D.REFERENCE_BLOCKS
    return AW.run_task(body, unit, block, purpose, root, tag)
