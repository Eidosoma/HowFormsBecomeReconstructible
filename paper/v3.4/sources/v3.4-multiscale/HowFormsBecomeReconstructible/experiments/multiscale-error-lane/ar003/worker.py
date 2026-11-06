"""One AR003 (body, unit, block) task: DL002's acquisition (through ar001.sim.prepare), then one body under every run,
each with AR001's vote (ar001.sim.run), AR002's rest-default detector arms (ar002.sim.run_det) and the vote-default arms
(ar003.sim.run_vd) on the same cases and streams, merged arm-major in design order. none and scattered cue damage, run at
the 4 x 4 patch, are also scored at the last read on every other size's patch (r_in_L<side>, from the final record).
Writes an endpoint shard, a raw-state shard and a completion record, each atomically, in ar002.worker's layout; the
meta names AR003's runs, arms, patch sides, detectors and digests (AR003's, AR002's, AR001's).
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
from ar002 import design as A2
from ar002 import sim as A2S
from be001 import sim as B1S
from lr005 import sim as L5S

from . import design as D
from . import sim

ENDS, SCALARS, DET_SCALARS = sim.ENDS, sim.SCALARS, sim.DET_SCALARS


def one(body, unit, block, purpose, run, tag=D.TAG, prepared=None, window=D.WINDOW, reads=D.READS, detectors=None,
        vd_detectors=None):
    """One run of one task: endpoints (reads x arms x cases), trace, per-arm scalars and final states."""
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = prepared if prepared is not None else A1S.prepare(pattern, block, purpose)
    situation, sigma, a1_arms, det_arms, vd_arms, size = run
    detectors = D.DETECTORS if detectors is None else detectors
    vd_detectors = D.VD_DETECTORS if vd_detectors is None else vd_detectors
    k, nr = len(cases), len(reads)
    parts = []
    if a1_arms:
        parts.append(A1S.run(body, situation, sigma, a1_arms, cases, V0, ema0, R0, th, T, theta, set(reads), tag=tag,
                             window=window, size=size))
    if det_arms:
        parts.append(A2S.run_det(body, situation, sigma, det_arms, cases, V0, ema0, R0, th, T, theta, set(reads), tag=tag,
                                 window=window, size=size, detectors=detectors))
    if vd_arms:
        parts.append(sim.run_vd(body, situation, sigma, vd_arms, cases, V0, ema0, R0, th, T, theta, set(reads), tag=tag,
                                window=window, size=size, detectors=vd_detectors))
    arms = tuple(a1_arms) + tuple(det_arms) + tuple(vd_arms)
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
    r_fin = cat("r", 0).reshape(na, k, D.SIDE, D.SIDE)
    if situation in D.SIZE_FREE and size == D.SIZE and window == D.T_READ:
        for L in D.SIZES:
            if L != size:
                mL = B1S.patch(cases, L, tag)
                ends[f"{key}/r_in_L{L}"] = np.stack([L5S.inside(r_fin[a], T, mL) for a in range(na)])
    raw = {f"{key}/{x}": cat(x, 0).reshape(na, k, D.SIDE, D.SIDE).astype(np.int8 if x in ("H", "W") else np.float64)
           for x in ("V", "r", "H", "W")}
    zf = [o for o in parts if "zone" in o]
    if zf:
        nz = sum(len(o["zone"]) for o in zf) // k
        raw[f"{key}/zone"] = np.concatenate([o["zone"] for o in zf]).reshape(nz, k, D.SIDE, D.SIDE)
        raw[f"{key}/fp"] = np.concatenate([o["fp"] for o in zf]).reshape(nz, k, D.SIDE, D.SIDE)
    rb = [o for o in parts if "rB" in o]
    if rb:
        nb = sum(len(o["rB"]) for o in rb) // k
        raw[f"{key}/rB"] = np.concatenate([o["rB"] for o in rb]).reshape(nb, k, D.SIDE, D.SIDE)
        raw[f"{key}/HB"] = np.concatenate([o["HB"] for o in rb]).astype(np.int8).reshape(nb, k, D.SIDE, D.SIDE)
        raw[f"{key}/WB"] = np.concatenate([o["WB"] for o in rb]).astype(np.int8).reshape(nb, k, D.SIDE, D.SIDE)
    signal = {}
    for o in parts:
        signal.update(o["signal_updates"])
    return ends, raw, signal


def task(body, unit, block, purpose, tag=D.TAG, runs=D.RUNS, window=D.WINDOW, reads=D.READS, detectors=None,
         vd_detectors=None):
    pattern, theta = D.parse_unit(unit)
    prepared = A1S.prepare(pattern, block, purpose)
    ends, raw, timing, signal = {}, {"V0": prepared[1], "R0": prepared[3], "T": prepared[5]}, {}, {}
    for run in runs:
        t1 = time.process_time()
        e, r, n = one(body, unit, block, purpose, run, tag, prepared, window, reads, detectors, vd_detectors)
        ends.update(e)
        raw.update(r)
        key = D.run_name(*run)
        timing[key], signal[key] = round(time.process_time() - t1, 3), n
    return ends, raw, timing, signal, prepared[0]


def meta_of(body, unit, block, purpose, tag, runs, timing, signal, cases, detectors, vd_detectors):
    return {"study": D.STUDY, "body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag,
            "design_digest": D.digest(), "ar002_digest": A2.digest(), "ar001_digest": A.digest(), "numpy": np.__version__,
            "timing_cpu_s": timing, "signal_updates": signal, "cases": [c.key() for c in cases],
            "detectors": detectors, "vd_detectors": vd_detectors,
            "runs": [[D.run_name(*x), list(D.arms_of(x))] for x in runs],
            "parts": {D.run_name(*x): [list(x[2]), list(x[3]), list(x[4])] for x in runs},
            "sizes": {D.run_name(*x): x[5] for x in runs}, "reads": list(D.READS)}


def run_task(body, unit, block, purpose, root, tag=D.TAG, runs=D.RUNS, detectors=None, vd_detectors=None):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    dets = D.DETECTORS if detectors is None else detectors
    vds = D.VD_DETECTORS if vd_detectors is None else vd_detectors
    ends, raw, timing, signal, cases = task(body, unit, block, purpose, tag, runs, detectors=dets, vd_detectors=vds)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {body} {unit} {block}: {bad[:5]}")
    meta = meta_of(body, unit, block, purpose, tag, runs, timing, signal, cases, dets, vds)
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
