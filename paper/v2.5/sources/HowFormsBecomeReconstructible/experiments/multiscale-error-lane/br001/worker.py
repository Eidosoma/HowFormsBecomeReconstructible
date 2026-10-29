"""One (panel, regime, block) task: acquisition, every arm and condition, successors reading the record.

All arms of a case share its acquired state, lesion position, onset, turnover events, record noise and
future draws; recipients share births and draws across every packet. Targets reach only the scoring
code and the privileged protected arm. Writes an endpoint shard, a raw-state shard and a completion
record, each atomically.
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
    conds = spec["conditions"]
    cases, s0, th, p, conserved, T, Tf = sim.prepare(name, [block], purpose)
    k, nc = len(cases), len(conds)
    idx = np.tile(np.arange(k), nc)
    Tb, Tfb = T[idx], Tf[idx]
    tau = sim.onsets(cases, spec["onset"])
    masks = [sim.patch_masks(cases, c.size) if c.size else None for c in conds]
    turn = [sim.turnover_events(cases, c.rate, D.WINDOW) if c.kind == "turnover" and c.rate > 0 else None for c in conds]
    Z = sim.draws(cases, "future", updates=D.WINDOW)
    XI = sim.draws(cases, "record-noise", updates=D.WINDOW)
    births, Zr = sim.recipients(cases)
    mask = np.concatenate([m if m is not None else np.zeros((k, 16, 16), bool) for m in masks])
    ends, raw, timing = {}, {}, {}

    def put(key, values, rows=nc):
        for kk, v in values.items():
            ends[f"{key}/{kk}"] = np.asarray(v, dtype=float).reshape(rows, k)

    put("acq", {"v_qual": sim.qual(s0.V, T), "r_sign": sim.sign(s0.R, T)}, 1)
    put("events", {"turnover_count": np.concatenate([np.array([len(e[0]) for e in tr]) if tr is not None else np.zeros(k)
                                                    for tr in turn]),
                   "patch_sites": mask.sum((-2, -1)), "tau": np.tile(tau, nc)})
    raw.update({"s0/V": s0.V, "s0/R": s0.R, "s0/ema": s0.ema, "theta": th, "targets": T, "foreign": Tf, "tau": tau,
                "mask": mask.reshape(nc, k, 16, 16)})
    for arm in spec["arms"]:
        t1 = time.time()
        v, e, r, w_l1 = sim.simulate(arm, conds, k, s0.V, s0.ema, s0.R, s0.R, th, Z, XI, p, conserved, T, Tf, tau,
                                     masks, turn, cal)
        vals = {"v_qual": sim.qual(v, Tb), "v_sign": sim.sign(v, Tb), "r_sign": sim.sign(r, Tb),
                "les_r": sim.masked_sign(r, Tb, mask), "les_v": sim.masked_sign(v, Tb, mask), "w_l1": w_l1}
        if panel == "P":
            vals.update({"vg_qual": sim.qual(v, Tfb), "rg_sign": sim.sign(r, Tfb)})
        F = sim.read(r, idx, th, births, Zr, p, conserved)
        vals["fR_qual"] = sim.qual(F, Tb[:, None]).mean(1)
        if panel == "P":
            vals["gR_qual"] = sim.qual(F, Tfb[:, None]).mean(1)
        put(arm.name, vals)
        raw.update({f"{arm.name}/V": v.reshape(nc, k, 16, 16), f"{arm.name}/R": r.reshape(nc, k, 16, 16)})
        timing[arm.name] = round(time.time() - t1, 3)
    for pk, P in (("target", T), ("zero", np.zeros_like(T))):
        F = sim.read(P, np.arange(k), th, births, Zr, p, conserved)
        put(pk, {"fR_qual": sim.qual(F, T[:, None]).mean(1), "fR_sign": sim.sign(F, T[:, None]).mean(1)}, 1)
    return ends, raw, timing, cases


def run_task(panel, name, block, purpose, calib, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    cal = calib["regimes"].get(name) if panel == "P" else None
    ends, raw, timing, cases = window_task(panel, name, block, purpose, cal)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
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
