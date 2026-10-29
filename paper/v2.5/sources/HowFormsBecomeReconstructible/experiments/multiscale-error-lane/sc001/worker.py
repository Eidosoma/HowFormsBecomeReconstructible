"""One (panel, unit, block) task: SC001's preparation, then both bodies under every arm (panel G, both geometries) or
every condition (panel R). Writes an endpoint shard, a raw-state shard and a completion record, each atomically.
Templates reach only the record's acquisition and the scoring; the body never reads them.
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

G_SNAP = ("sign", "filled", "far", "near", "shift", "spacing")
G_TRACE = ("t_filled", "t_sign", "t_rough")
R_READ = ("patch", "r_patch", "filled", "sign", "r_sign", "bond_err")
R_TRACE = ("t_patch", "t_r_patch")
FUNC = ("intact", "defects", "islands", "walls")


def task(panel, unit, block, purpose, tag=D.TAG, arms=D.ARMS_G, conds=D.CONDS_R, window=D.WINDOW):
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, purpose, tag)
    k = len(cases)
    ends, raw, timing = {}, {"V0": V0, "R0": R0, "T": T}, {}
    for b in D.BODIES:
        if panel == "G":
            na = len(arms)
            for geo in D.GEOMS:
                t1 = time.time()
                o = sim.run_G(b, geo, arms, cases, R0, th, T, theta, tag, window, D.SNAPS)
                key = f"{b}/{geo}"
                for e in G_SNAP:
                    ends[f"{key}/{e}"] = o[e].reshape(len(D.SNAPS), na, k)
                for e in G_TRACE:
                    ends[f"{key}/{e}"] = o[e].reshape(-1, na, k)
                for e in FUNC:
                    ends[f"{key}/{e}"] = o[e].reshape(na, k)
                ends[f"{key}/profile"] = o["profile"].reshape(na, k, D.DMAX + 1)
                raw[f"{key}/V"] = o["V"].reshape(na, k, D.SIDE, D.SIDE)
                raw[f"{key}/occ"] = o["occ"].reshape(na, k, D.SIDE, D.SIDE)
                timing[key] = round(time.time() - t1, 3)
        else:
            t1 = time.time()
            res = sim.run_R(b, conds, cases, V0, ema0, R0, th, T, theta, tag, window, D.READS_R)
            for e in R_READ + R_TRACE:
                ends[f"{b}/{e}"] = np.stack([res[c.name][e] for c in conds], 1)        # (reads, conds, cases)
            for e in FUNC:
                ends[f"{b}/{e}"] = np.stack([res[c.name][e] for c in conds])           # (conds, cases)
            for e in ("V", "r", "H", "W", "occ"):
                raw[f"{b}/{e}"] = np.stack([res[c.name][e] for c in conds])
            timing[b] = round(time.time() - t1, 3)
    return ends, raw, timing, cases
def run_task(panel, unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(panel, unit, block, purpose, tag)
    for arrays in (ends, raw):
        # NaN marks an agreement over a region with no occupied cell yet (e.g. the far side before growth reaches it)
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and np.isinf(v).any()]
        if bad:
            raise FloatingPointError(f"infinite values in {panel} {unit} {block}: {bad[:5]}")
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
