"""One (body, unit, block) task: DL002's acquisition of the unit's pattern (np001.sim.prepare), the lineage of GENS
renewals under every route as branches, then the fresh recipients (a newborn of each kind in RECIPIENTS reading every
route's last record, protected, plus its paired no-record control). Writes an endpoint shard, a raw-state shard and a
completion record, each atomically. Templates reach only the record's acquisition and the scoring; no body reads one.
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

KEEP = (1, 16)                                                   # the generations whose states are saved raw
BRANCHES2 = D.ROUTENAMES + ("none",)                             # recipients: every route's last record, then the control
VOTE = tuple(r.name for r in D.ROUTES if r.two)


def task(body, unit, block, purpose, tag=D.TAG, recipients=D.RECIPIENTS, gens=D.GENS, t_gen=D.T_GEN):
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, purpose)
    Tf = sim.foreign(T, unit, cases)
    k, nr = len(cases), len(D.ROUTES)
    timing = {}
    t1 = time.time()
    res, kept, A, B = sim.lineage(body, D.ROUTES, cases, R0, th, T, Tf, tag=tag, gens=gens, t_gen=t_gen, keep=KEEP)
    timing["lineage"] = round(time.time() - t1, 3)
    ends = {f"g/{e}": res[e].reshape(gens, nr, k) for e in sim.ENDS}
    ends.update({f"g/{e}": res[e].reshape(gens, D.NFOREIGN, nr, k) for e in sim.FENDS})
    ends["g/rB_a"] = res["rB_a"].reshape(gens, len(VOTE), k)
    raw = {"R0": R0, "T": T.astype(np.int8), "Tf": Tf.astype(np.int8)}
    for g, st in kept.items():
        raw[f"g{g}/V"] = st["V"].reshape(nr, k, D.SIDE, D.SIDE)
        raw[f"g{g}/r"] = st["r"].reshape(nr, k, D.SIDE, D.SIDE)
        raw[f"g{g}/H"] = st["H"].reshape(nr, k, D.SIDE, D.SIDE)
        raw[f"g{g}/W"] = st["W"].reshape(nr, k, D.SIDE, D.SIDE)
    if B is not None:
        raw[f"g{gens}/rB"] = B[4].reshape(len(VOTE), k, D.SIDE, D.SIDE)
    H, W, r = A[0], A[1], A[4]
    pick = lambda x: np.concatenate([x, x[:k]])                  # every route's record, then the control's (unread)
    gains = [D.GAIN] * nr + [0.0]
    nb2 = len(BRANCHES2)
    for RB in recipients:
        t1 = time.time()
        o2 = sim.recipient(RB, pick(r), pick(H), pick(W), cases, th, T, Tf, set(D.READS2), gains, tag=tag)
        timing[f"rec/{RB}"] = round(time.time() - t1, 3)
        ends.update({f"rec/{RB}/{e}": o2[e].reshape(len(D.READS2), nb2, k) for e in sim.ENDS2})
        ends[f"rec/{RB}/v_f"] = o2["v_f"].reshape(len(D.READS2), D.NFOREIGN, nb2, k)
        raw[f"rec/{RB}/V"] = o2["V"].reshape(nb2, k, D.SIDE, D.SIDE)
    return ends, raw, timing, cases


def run_task(body, unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(body, unit, block, purpose, tag)
    for arrays in (ends, raw):
        bad = [kk for kk, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {body} {unit} {block}: {bad[:5]}")
    meta = {"body": body, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "routes": D.ROUTENAMES, "branches2": BRANCHES2,
            "vote": VOTE, "keep": KEEP, "cases": [c.key() for c in cases]}
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
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
