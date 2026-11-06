"""One AR002 (body, unit, block) task: DL002's acquisition (through ar001.sim.prepare), then one body under every run,
each with AR001's arms (ar001.sim.run, imported unchanged) and the detector-driven arms (ar002.sim.run_det) on the same
cases and streams, merged arm-major in design order. Writes an endpoint shard, a raw-state shard and a completion record,
each atomically, in ar001.worker's layout; the meta names AR002's runs, arms, patch sides, detectors and digests
(AR002's, AR001's).
Templates reach only the record's acquisition, the event's target and the scoring; the detectors read the body, the
record and the anchors only; no arm is told the situation or the event time.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from ar001 import design as A
from ar001 import sim as A1S

from . import design as D
from . import sim

ENDS, SCALARS, DET_SCALARS = sim.ENDS, sim.SCALARS, sim.DET_SCALARS


def one(body, unit, block, purpose, run, tag=D.TAG, prepared=None, window=D.WINDOW, reads=D.READS, detectors=None):
    """One run of one task: endpoints (reads x arms x cases), trace, per-arm scalars and final states."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = prepared if prepared is not None else sim.prepare(pattern, block, purpose)
    situation, sigma, a1_arms, det_arms, size = run
    k, nr = len(cases), len(reads)
    parts = []
    if a1_arms:
        parts.append(A1S.run(body, situation, sigma, a1_arms, cases, V0, ema0, R0, th, T, theta, set(reads), tag=tag,
                             window=window, size=size))
    if det_arms:
        parts.append(sim.run_det(body, situation, sigma, det_arms, cases, V0, ema0, R0, th, T, theta, set(reads), tag=tag,
                                 window=window, size=size, detectors=detectors))
    arms = tuple(a1_arms) + tuple(det_arms)
    na = len(arms)
    key = D.run_name(*run)
    cat = lambda x, ax: np.concatenate([o[x] for o in parts], ax)
    ends = {f"{key}/{e}": cat(e, 1).reshape(nr, na, k) for e in ENDS if e in parts[0]}
    for e in SCALARS:
        ends[f"{key}/{e}"] = cat(e, 0).reshape(na, k)
    for e in DET_SCALARS:
        vals = [o[e] if e in o else np.full(len(a1_arms) * k, -1.0) for o in parts]
        ends[f"{key}/{e}"] = np.concatenate(vals).reshape(na, k)
    ends[f"{key}/n_anc"] = parts[0]["n_anc"]
    ends[f"{key}/n_mis"] = parts[0]["n_mis"]
    ends[f"{key}/trace"] = cat("trace", 1).reshape(-1, na, k)
    raw = {f"{key}/{x}": cat(x, 0).reshape(na, k, D.SIDE, D.SIDE).astype(np.int8 if x in ("H", "W") else np.float64)
           for x in ("V", "r", "H", "W")}
    if det_arms:
        o = parts[-1]
        raw[f"{key}/zone"] = o["zone"].reshape(len(det_arms), k, D.SIDE, D.SIDE)
        raw[f"{key}/fp"] = o["fp"].reshape(len(det_arms), k, D.SIDE, D.SIDE)
    if a1_arms and "rB" in parts[0]:
        raw[f"{key}/rB"] = parts[0]["rB"]
        raw[f"{key}/HB"], raw[f"{key}/WB"] = parts[0]["HB"].astype(np.int8), parts[0]["WB"].astype(np.int8)
    signal = {}
    for o in parts:
        signal.update(o["signal_updates"])
    return ends, raw, signal


def task(body, unit, block, purpose, tag=D.TAG, runs=D.RUNS, window=D.WINDOW, reads=D.READS, detectors=None):
    pattern, theta = D.parse_unit(unit)
    prepared = sim.prepare(pattern, block, purpose)
    ends, raw, timing, signal = {}, {"V0": prepared[1], "R0": prepared[3], "T": prepared[5]}, {}, {}
    for run in runs:
        t1 = time.time()
        e, r, n = one(body, unit, block, purpose, run, tag, prepared, window, reads, detectors)
        ends.update(e)
        raw.update(r)
        key = D.run_name(*run)
        timing[key], signal[key] = round(time.time() - t1, 3), n
    return ends, raw, timing, signal, prepared[0]


def run_task(body, unit, block, purpose, root, tag=D.TAG, runs=D.RUNS, detectors=None):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, signal, cases = task(body, unit, block, purpose, tag, runs, detectors=detectors)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {body} {unit} {block}: {bad[:5]}")
    dets = D.DETECTORS if detectors is None else detectors
    meta = {"study": D.STUDY, "body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag,
            "design_digest": D.digest(), "ar001_digest": A.digest(), "numpy": np.__version__, "timing_s": timing,
            "signal_updates": signal, "cases": [c.key() for c in cases], "detectors": dets,
            "runs": [[D.run_name(*x), list(x[2]) + list(x[3])] for x in runs],
            "sizes": {D.run_name(*x): x[4] for x in runs}, "reads": list(D.READS)}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / body / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing, "signal_updates": signal,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
