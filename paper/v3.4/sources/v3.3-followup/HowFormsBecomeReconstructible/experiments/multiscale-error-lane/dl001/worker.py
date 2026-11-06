"""One (panel, unit, block) task: the acquisition, then every body and condition. Writes an endpoint shard, a
raw-state shard and a completion record, each atomically. Templates reach only the scoring code and the held
record's acquisition (as GW001); the body never reads them.
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


def _branches(panel, conds, cases, V0, ema0, R0, T, side):
    """Initial V, ema, r, gain, T and masks per branch, condition-major."""
    k = len(cases)
    Vs, Es, Rs, gains, Ms = [], [], [], [], []
    for c in conds:
        V, E = V0.copy(), ema0.copy()
        m = np.zeros((k, side, side), bool)
        if c.wound != "sham":
            m = sim.wound_mask(cases, c.size, side)
            if c.wound == "flip":
                V = np.where(m, -V, V)
            else:
                nb = sim.newborn_values(cases, c.size, side)
                V, E = np.where(m, nb, V), np.where(m, nb, E)
        Vs.append(V)
        Es.append(E)
        Rs.append(R0 if c.gain > 0 else np.zeros_like(R0))
        gains.append(np.full(k, c.gain))
        Ms.append(m)
    cat = lambda xs: np.concatenate(xs)
    return cat(Vs), cat(Es), cat(Rs), cat(gains), np.tile(T, (len(conds), 1, 1)), cat(Ms)


def task(panel, unit, block, purpose):
    pattern, sigma, theta, side = D.parse_unit(unit)
    spec = D.PANELS[panel]
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, side, block, purpose)
    k = len(cases)
    th = th * theta
    if spec["start"] == "newborn":
        V0 = sim.newborn_sheet(cases, side)
        ema0 = V0.copy()
    ends, raw, timing = {}, {"V0": V0, "R0": R0, "T": T}, {}
    groups = [(spec["conds"], spec["window"], spec["snaps"])]
    if panel == "X":                                       # no record for 8,000 updates; the held record for 2,000
        groups = [(spec["conds"][:1], D.WINDOW_X0, D.SNAPS_X0), (spec["conds"][1:], D.WINDOW_X, D.SNAPS_X)]
    for b in spec["bodies"]:
        t1 = time.time()
        for gi, (conds, window, snaps) in enumerate(groups):
            nc = len(conds)
            V, E, r, gain, Tb, M = _branches(panel, conds, cases, V0, ema0, R0, T, side)
            o = sim.run(b, V, E, r, gain, th, Tb, cases, sigma, window, set(snaps), M if panel == "W" else None)
            tag = f"{b}" if len(groups) == 1 else f"{b}/{'free' if gi == 0 else 'held'}"
            for key in ("sign", "shift", "spacing", "patch"):
                if key in o:
                    ends[f"{tag}/{key}"] = o[key].reshape(len(snaps), nc, k)
            for key in ("w_corr", "w_drift"):
                ends[f"{tag}/{key}"] = o[key].reshape(nc, k)
            ends[f"{tag}/qual"] = sim.qual(o["final"], Tb).reshape(nc, k)
            raw[f"{tag}/V"] = o["final"].reshape(nc, k, side, side)
            if panel == "W":
                raw["mask"] = M.reshape(nc, k, side, side)
        timing[b] = round(time.time() - t1, 3)
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
