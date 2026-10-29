"""One (panel, regime, block) task: acquisition, every record arm under every budget and condition.

All branches of a case share its acquired state, wound position, kill newborns, turnover events (on the outside
clock), record noise and future draws. Targets reach only the scoring code. Writes an endpoint shard, a
raw-state shard and a completion record, each atomically.
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


def window_task(panel, name, block, purpose, cal):
    spec = D.PANELS[panel]
    conds, budgets = D.CONDS, spec["budgets"]
    cases, s0, th, p, conserved, T = sim.prepare(name, [block], purpose)
    k, nc, nb = len(cases), len(conds), len(budgets)
    masks = [None if not c.size else sim.patch_masks(cases, c.size) for c in conds]
    turn = [sim.turnover_events(cases, c.rate, D.WINDOW) if c.kind == "turnover" else None for c in conds]
    born = [sim.newborn(cases, c.size) if c.kind == "kill" else None for c in conds]
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    work = cal["regimes"][name]["work"] if panel == "E" else None
    idx = np.tile(np.arange(k), nb * nc)
    Tb = T[idx]
    ends, raw, timing = {}, {}, {}
    raw.update({"s0/V": s0.V, "s0/R": s0.R, "s0/ema": s0.ema, "theta": th, "targets": T,
                "mask": np.stack([m if m is not None else np.zeros((k, 16, 16), bool) for m in masks])})
    ends["events/turnover_count"] = np.array([[len(e[0]) for e in tr] if tr is not None else [0] * k for tr in turn], float)
    ends["events/patch_sites"] = raw["mask"].sum((-2, -1)).astype(float)
    store = np.repeat([b.scheme == "store" for b in budgets], nc * k)
    for arm in spec["arms"]:
        t1 = time.time()
        o = sim.simulate(D.ARMS[arm], budgets, conds, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, masks,
                         turn, born, work)
        m = o["mask"]
        vals = {"v_qual": sim.qual(o["V_s"], Tb), "v_sign": sim.sign(o["V_s"], Tb), "r_sign": sim.sign(o["R_s"], Tb),
                "les_r": sim.masked_sign(o["R_s"], Tb, m), "les_v": sim.masked_sign(o["V_s"], Tb, m),
                "v_qual_rec": sim.qual(o["V_r"], Tb), "r_sign_rec": sim.sign(o["R_r"], Tb),
                "les_r_rec": sim.masked_sign(o["R_r"], Tb, m), "les_v_rec": sim.masked_sign(o["V_r"], Tb, m),
                "t95": sim.t95(o["snap_r"], m.any((-2, -1))),
                "w_drift": o["w_drift"] / (D.STARVE * 256), "w_corr": o["w_corr"] / (D.STARVE * 256),
                "w_rec": o["w_rec"] / (D.STARVE * 256),
                "a_mean": np.where(store, o["a_mean"], np.nan), "a_patch": np.where(store, o["a_patch"], np.nan),
                "a_rest": np.where(store, o["a_rest"], np.nan)}
        t = vals["t95"]
        vals["healed"] = np.where(np.isnan(t), np.nan, (t <= D.STARVE).astype(float))
        for bi, b in enumerate(budgets):
            sl = slice(bi * nc * k, (bi + 1) * nc * k)
            for ep, x in vals.items():
                ends[f"{arm}/{b.name}/{ep}"] = np.asarray(x[sl], float).reshape(nc, k)
            for key in ("V_s", "R_s", "V_r", "R_r"):
                raw[f"{arm}/{b.name}/{key}"] = o[key][sl].reshape(nc, k, 16, 16)
            raw[f"{arm}/{b.name}/snap_r"] = o["snap_r"][sl].reshape(nc, k, -1)
            raw[f"{arm}/{b.name}/snap_v"] = o["snap_v"][sl].reshape(nc, k, -1)
        timing[arm] = round(time.time() - t1, 3)
    return ends, raw, timing, cases


def run_task(panel, name, block, purpose, calib, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = window_task(panel, name, block, purpose, calib)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating)
               and not kk.endswith(("t95", "healed", "a_mean", "a_patch", "a_rest")) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {panel} {name} {block}: {bad[:5]}")
    meta = {"panel": panel, "regime": name, "block": block, "purpose": purpose, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / panel / name
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"panel": panel, "regime": name, "block": block, "purpose": purpose, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / panel / name / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
