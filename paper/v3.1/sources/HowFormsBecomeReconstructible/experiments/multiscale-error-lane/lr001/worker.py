"""One (panel, unit, block) task: acquisition, every branch. Writes an endpoint shard, a raw-state shard and a
completion record, each atomically. Templates reach only the scoring code and the experimenter's wound placement."""
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


def task_arrays(panel, unit, block, purpose):
    cases, V, ema, R0, th, T = sim.prepare(unit, block, purpose)
    ends, raw = {}, {"R0": R0, "T": T}
    if panel == "A":
        for s in D.A_SIGMAS:
            ends[f"s{s:g}/bond_accuracy"] = sim.simulate_A(cases, T, th, s, D.A_READS)
    elif panel == "E":
        out, fin = sim.simulate_E(cases, R0, T)
        ends.update(out)
        raw.update(fin)
    elif panel == "C":
        masks = {s: sim.patch(cases, s) for s in (0, *D.C_SIZES)}
        out, fin = sim.simulate_C(cases, R0, T, masks)
        ends.update(out)
        raw.update(fin)
        ends["events/patch_sites"] = np.array([masks[c.size].sum((-2, -1)) for c in D.C_CONDS], float)
    elif panel == "T":
        out, fin = sim.simulate_T(cases, R0, T)
        ends.update(out)
        raw.update(fin)
    else:
        out, fin = sim.simulate_L(cases, V, ema, R0, th, T)
        ends.update(out)
        raw.update(fin)
        raw.update({"V0": V, "ema0": ema, "theta": th})
    return ends, raw, cases


def run_task(panel, unit, block, purpose, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, cases = task_arrays(panel, unit, block, purpose)
    for arrays in (ends, raw):
        bad = [k for k, v in arrays.items()
               if np.issubdtype(np.asarray(v).dtype, np.floating) and np.isinf(np.asarray(v)).any()]
        if bad:
            raise FloatingPointError(f"infinite arrays in {panel} {unit} {block}: {bad[:5]}")
    meta = {"panel": panel, "unit": unit, "block": block, "purpose": purpose, "design_digest": D.digest(),
            "numpy": np.__version__, "branches": D.branches(panel), "cases": [c.key() for c in cases]}
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
    record = {"panel": panel, "unit": unit, "block": block, "purpose": purpose, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / panel / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
