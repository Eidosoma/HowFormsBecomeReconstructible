"""One (body, unit, block) task: the conflict's preparation (the body from one acquisition, the record from another),
stage 1 (the body under every condition as branches: NP001's six at gain 0.2 and the race pairs at lower gains), and for
the spacing conflicts stage 2 (each successor body reading every handed stage-1 record, plus its paired no-record
control). Writes an endpoint shard, a raw-state shard and a completion record, each atomically. Templates reach only the
record's acquisition and the scoring; no body reads a template.

Besides NP001's endpoints, stage 1 stores the inversion-invariant agreements r_abs = |2 r_align - 1| and
r_abs_b = |2 r_align_b - 1| per case (and abs, abs_b for the body): a record of relations holds a pattern only up to its
global sign (phase K and phase K + 4 of period-8 stripes have the same relations), so a record's relational preference
is read from these. At the last read only it also stores bond_b, the share of the record's bonds that differ from the
relations of the body's initial pattern (NP001's bond_err is the same against the history's relations): the record's
state and its bonds can disagree, and the bonds are reported beside the state (reported, not registered).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from lr001.sim import bond_err, edges_from
from msegrid.core import bonds

from . import design as D
from . import sim

HANDED_IX = [D.CONDNAMES.index(c.name) for c in D.HANDED]
BRANCHES2 = tuple(c.name for c in D.HANDED) + ("none",)     # stage-2 branches: the handed records, then the control


def handed(o, k):
    """The handed records (r, H, W) of stage 1, branch-major, plus a copy of the first for the gain-0 control (it
    steps through its bonds but no body reads it)."""
    sel = HANDED_IX + HANDED_IX[:1]
    pick = lambda x: x.reshape(len(D.CONDS), k, D.SIDE, D.SIDE)[sel].reshape(-1, D.SIDE, D.SIDE)
    return pick(o["r"]), pick(o["H"]), pick(o["W"])


def task(body, unit, block, purpose, tag=D.TAG, succ=D.SUCC_BODIES):
    cases, V0, ema0, R0, th, T = sim.prepare(unit, block, purpose)
    T0 = sim.initial(unit, cases, block)
    k, nc, nr, nr2 = len(cases), len(D.CONDS), len(D.READS), len(D.READS2)
    timing = {}
    t1 = time.time()
    o = sim.stage1(body, D.CONDS, cases, V0, ema0, R0, th, T, set(D.READS), tag=tag, window=D.WINDOW, theta=D.THETA,
                   T0=T0)
    timing["stage1"] = round(time.time() - t1, 3)
    ends = {f"s1/{e}": o[e].reshape(nr, nc, k) for e in sim.ENDS1}
    for a, x in (("abs", "align"), ("abs_b", "align_b"), ("r_abs", "r_align"), ("r_abs_b", "r_align_b")):
        ends[f"s1/{a}"] = np.abs(2.0 * ends[f"s1/{x}"] - 1.0)
    Hb0, Wb0 = edges_from(bonds(T0, True))
    idx = np.tile(np.arange(k), nc)
    ends["s1/bond_b"] = bond_err(o["H"], o["W"], Hb0[idx], Wb0[idx]).reshape(1, nc, k)     # the last read only
    raw = {"V0": V0, "R0": R0, "T": T, "T0": T0, "s1/V": o["V"].reshape(nc, k, D.SIDE, D.SIDE),
           "s1/r": o["r"].reshape(nc, k, D.SIDE, D.SIDE)}
    raw.update({f"s1/{x}": o[x].reshape(nc, k, D.SIDE, D.SIDE).astype(np.int8) for x in ("H", "W")})
    if D.has_successors(unit):
        r, H, W = handed(o, k)
        gains = [c.gain for c in D.HANDED] + [0.0]
        for B in succ:
            t1 = time.time()
            o2 = sim.successor(B, r, H, W, cases, th, T, set(D.READS2), gains, tag=tag, window=D.WINDOW2,
                               theta=D.THETA, T0=T0)
            timing[f"s2/{B}"] = round(time.time() - t1, 3)
            ends.update({f"s2/{B}/{e}": o2[e].reshape(nr2, len(BRANCHES2), k) for e in sim.ENDS2})
            raw[f"s2/{B}/V"] = o2["V"].reshape(len(BRANCHES2), k, D.SIDE, D.SIDE)
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
            "numpy": np.__version__, "timing_s": timing, "conds": D.CONDNAMES,
            "branches2": BRANCHES2 if D.has_successors(unit) else [], "cases": [c.key() for c in cases]}
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
