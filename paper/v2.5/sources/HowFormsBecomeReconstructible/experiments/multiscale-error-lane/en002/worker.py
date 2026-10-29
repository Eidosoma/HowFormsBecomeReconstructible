"""One (panel, unit, block) task: the acquisition, then every body and condition. Writes an endpoint shard, a
raw-state shard and a completion record, each atomically. Templates reach only the scoring code and the held
record's acquisition (as DL001); the body never reads them.
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


def branches(conds, cases, V0, ema0, R0, T, tag=D.TAG):
    """Initial V, ema, r, T and wound masks per branch, condition-major."""
    k = len(cases)
    Vs, Es, Rs, Ms = [], [], [], []
    for c in conds:
        V, E = V0.copy(), ema0.copy()
        m = np.zeros((k, D.SIDE, D.SIDE), bool)
        if c.wound != "sham":
            m = sim.wound_mask(cases, c.size, tag)
            if c.wound == "flip":
                V = np.where(m, -V, V)
            else:
                nb = sim.newborn_values(cases, c.size, tag)
                V, E = np.where(m, nb, V), np.where(m, nb, E)
        Vs.append(V)
        Es.append(E)
        Rs.append(R0 if c.record == "held" else np.zeros_like(R0))
        Ms.append(m)
    cat = np.concatenate
    return cat(Vs), cat(Es), cat(Rs), np.tile(T, (len(conds), 1, 1)), cat(Ms)


def task(panel, unit, block, purpose, tag=D.TAG):
    pattern, theta = D.parse_unit(unit)
    spec = D.PANELS[panel]
    conds, snaps = spec["conds"], spec["snaps"]
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, purpose, tag)
    k, nc = len(cases), len(conds)
    th = th * theta
    ends, raw, timing = {}, {"V0": V0, "R0": R0, "T": T}, {}
    for b in D.BODIES:
        t1 = time.time()
        V, E, r, Tb, M = branches(conds, cases, V0, ema0, R0, T, tag)
        o = sim.run(b, conds, V, E, r, th, Tb, cases, set(snaps), M if panel == "W" else None, tag)
        for key in ("sign", "shift", "spacing", "patch"):
            if key in o:
                ends[f"{b}/{key}"] = o[key].reshape(len(snaps), nc, k)
        for key in ("w_drift", "w_corr"):
            ends[f"{b}/{key}"] = o[key].reshape(nc, k)
        raw[f"{b}/V"] = o["final"].reshape(nc, k, D.SIDE, D.SIDE)
        if panel == "W":
            raw["mask"] = M.reshape(nc, k, D.SIDE, D.SIDE)
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
