"""One (panel, unit, block) task: acquisition, every arm and condition. Writes an endpoint shard, a raw-state
shard and a completion record, each atomically. Targets reach only the scoring code, the experimenter's lesion
placement and the privileged protected arm.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from msegrid.core import wall_distance

from . import design as D
from . import sim


def task_R(unit, block, purpose):
    family, side = D.parse_geometry(unit)
    conds = D.GEOMETRIES[unit]
    cases, R0, T = sim.prepare_R(unit, block, purpose)
    k, nc = len(cases), len(conds)
    idx = np.tile(np.arange(k), nc)
    Tb = T[idx]
    masks = sim.masks_for(cases, conds, family, side)
    mask = np.concatenate([m if m is not None else np.zeros((k, side, side), bool) for m in masks])
    ends, raw, timing = {}, {}, {}
    nsnap = D.WINDOW_R // D.EVERY_R
    ends["events/patch_sites"] = mask.sum((-2, -1)).reshape(nc, k).astype(float)
    if family in ("F0", "S8"):
        ends["events/wall_distance"] = np.array([[wall_distance(T[j], masks[ci][j], family, cases[j].message) if masks[ci] is not None
                                                  else -2 for j in range(k)] for ci in range(nc)], float)
    ends["acq/r_sign"] = sim.sign(R0, T).reshape(1, k)
    raw.update({"R0": R0, "T": T, "mask": mask.reshape(nc, k, side, side)})
    for arm in D.ARMS_R:
        t1 = time.time()
        r, kept, rsign = sim.simulate_R(arm, conds, k, R0, T, masks, cases, D.WINDOW_R, D.EVERY_R)
        ends[f"{arm.name}/kept_curve"] = kept.reshape(nsnap, nc, k)
        ends[f"{arm.name}/rsign_curve"] = rsign.reshape(nsnap, nc, k)
        ends[f"{arm.name}/committed"] = sim.committed_kept(r, Tb, mask).reshape(nc, k)
        ends[f"{arm.name}/undecided"] = ((((np.abs(r) <= D.COMMIT) & mask).sum((-2, -1)))
                                         / np.maximum(mask.sum((-2, -1)), 1)).reshape(nc, k)
        raw[f"{arm.name}/R"] = r.reshape(nc, k, side, side)
        timing[arm.name] = round(time.time() - t1, 3)
    return ends, raw, timing, cases


def task_B(unit, block, purpose):
    family, side, sigma, body = D.parse_regime(unit)
    conds = D.COND_B
    cases, V, ema, R0, th, T, p, conserved = sim.prepare_B(unit, block, purpose)
    k, nc = len(cases), len(conds)
    idx = np.tile(np.arange(k), nc)
    Tb = T[idx]
    masks = sim.masks_for(cases, conds, family, side)
    born = [sim.newborn(cases, c.size, side) if c.wound in ("reset", "kill") else None for c in conds]
    mask = np.concatenate([m if m is not None else np.zeros((k, side, side), bool) for m in masks])
    ends, raw, timing = {}, {}, {}
    ends["events/patch_sites"] = mask.sum((-2, -1)).reshape(nc, k).astype(float)
    ends["events/wall_distance"] = np.array([[wall_distance(T[j], masks[ci][j], family, cases[j].message) if masks[ci] is not None
                                              else -2 for j in range(k)] for ci in range(nc)], float)
    ends["acq/v_qual"] = sim.qual(V, T).reshape(1, k)
    ends["acq/r_sign"] = sim.sign(R0, T).reshape(1, k)
    raw.update({"V0": V, "R0": R0, "T": T, "mask": mask.reshape(nc, k, side, side)})
    for arm in D.ARMS_B:
        t1 = time.time()
        v, e, r, les_v = sim.simulate_B(arm, conds, k, V, ema, R0, th, T, p, conserved, masks, born, cases, D.WINDOW_B, D.EVERY_B)
        vals = {"v_qual": sim.qual(v, Tb), "v_sign": sim.sign(v, Tb), "v_out": sim.outside_agree(v, Tb, mask),
                "les_v": sim.masked_sign(v, Tb, mask), "les_r": sim.masked_sign(r, Tb, mask), "r_sign": sim.sign(r, Tb)}
        for kk, x in vals.items():
            ends[f"{arm.name}/{kk}"] = np.asarray(x, float).reshape(nc, k)
        ends[f"{arm.name}/les_v_curve"] = les_v.reshape(-1, nc, k)
        raw.update({f"{arm.name}/V": v.reshape(nc, k, side, side), f"{arm.name}/R": r.reshape(nc, k, side, side)})
        timing[arm.name] = round(time.time() - t1, 3)
    return ends, raw, timing, cases


def run_task(panel, unit, block, purpose, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = (task_R if panel == "R" else task_B)(unit, block, purpose)
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
