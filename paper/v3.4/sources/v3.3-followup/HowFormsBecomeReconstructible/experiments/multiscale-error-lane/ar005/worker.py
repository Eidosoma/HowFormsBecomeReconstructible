"""One AR005 (body, unit, block) task: ar003.worker's one and task, from their own source (imported unchanged), with
one's single vote-default call routed to ar005.sim.run_vg (which carries the guarded detector); the stage's runs and
vote-default detectors (vms: AR003's frozen DET_STAR; vpool: AR004's frozen DET_POOL; vguard: DET_POOL plus the
tuning's guard; in the tuning, the grid's candidates too). Writes an endpoint shard, a raw-state shard and a completion
record, each atomically, in AR004's layout; the meta names AR005's runs, detectors and digests (AR005's, AR004's and
AR003's).
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
from ar004 import design as A4

from . import design as D
from . import sim

_NS = dict(vars(AW), run_vg=sim.run_vg)
one = sim.derive(AW.one, _NS, "sim.run_vd(", "run_vg(")
task = sim.derive(AW.task, _NS)                                # its one() is the routed one above


def run_task(body, unit, block, purpose, root, tag=D.TAG, runs=D.RUNS, detectors=None):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    detectors = D.VD_DETECTORS if detectors is None else detectors
    ends, raw, timing, signal, cases = task(body, unit, block, purpose, tag, runs=runs, vd_detectors=detectors)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {body} {unit} {block}: {bad[:5]}")
    meta = {"study": D.STUDY, "body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag,
            "design_digest": D.digest(), "ar004_digest": A4.digest(), "ar003_digest": A3.digest(),
            "numpy": np.__version__, "timing_cpu_s": timing, "signal_updates": signal, "cases": [c.key() for c in cases],
            "vd_detectors": detectors, "vguard_name": D.VGUARD_NAME,
            "runs": [[D.run_name(*x), list(D.arms_of(x))] for x in runs],
            "parts": {D.run_name(*x): [list(x[2]), list(x[3]), list(x[4])] for x in runs},
            "sizes": {D.run_name(*x): x[5] for x in runs}, "reads": list(D.READS)}
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
