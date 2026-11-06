"""One (panel, unit, block) task: the acquisition, then both bodies under every record. Writes an endpoint shard, a
raw-state shard and a completion record, each atomically. Templates reach only the scoring, the experimenter's wound
placement and the held record's acquisition (as GW001 and DL001); the body never reads them.
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


def task(panel, unit, block, purpose):
    pattern, theta, wound = D.parse_unit(unit)
    spec = D.PANELS[panel]
    records = spec["records"]
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, purpose)
    k, nb = len(cases), len(records)
    ends, raw, timing = {}, {"V0": V0, "R0": R0, "T": T}, {}
    for b in D.BODIES:
        t1 = time.time()
        o = sim.run(b, records, cases, V0, ema0, R0, th, T, theta, wound, set(spec["snaps"]))
        ns = len(spec["snaps"])
        for key in ("sign", "patch", "shift", "spacing"):
            ends[f"{b}/{key}"] = o[key].reshape(ns, nb, k)
        for key in ("r_sign", "r_patch"):
            ends[f"{b}/{key}"] = o[key].reshape(ns, k)
        ends[f"{b}/w_corr"] = o["w_corr"].reshape(nb, k)
        ends[f"{b}/qual"] = o["qual"].reshape(nb, k)
        raw[f"{b}/V"] = o["final"].reshape(nb, k, D.SIDE, D.SIDE)
        raw[f"{b}/r_rel"] = o["r_rel"]
        timing[b] = round(time.time() - t1, 3)
    if wound:
        raw["mask"] = sim.wound_mask(cases)
    return ends, raw, timing, cases


def run_task(panel, unit, block, purpose, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(panel, unit, block, purpose)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {panel} {unit} {block}: {bad[:5]}")
    meta = {"panel": panel, "unit": unit, "block": block, "purpose": purpose, "design_digest": D.digest(),
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
    record = {"panel": panel, "unit": unit, "block": block, "purpose": purpose, "design_digest": D.digest(),
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
