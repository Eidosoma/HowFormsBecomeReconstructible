"""One (unit, block) task: both histories' acquisitions and the four references (nl002.sim.prepare), the tissue under
every label (arm x event) as branches, then the fresh recipients (a newborn dw body reading every branch's final L1
record, protected; A's and B's acquired records; nothing: 's/'), and again with each branch's coarse codes at its own
gains ('c/'). Writes an endpoint shard, a raw-state shard and a completion
record, each atomically. Templates reach only the acquisition and the scoring; no body reads one.
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

BRANCHES2 = tuple(f"{a}/{e}" for a, e in D.LABELS) + sim.SUCC


def task(unit, block, purpose, tag=D.TAG):
    cases = sim.cases_for(block, purpose)
    timing = {}
    t1 = time.time()
    P = sim.prepare(cases, tag)
    timing["prepare"] = round(time.time() - t1, 3)
    t1 = time.time()
    out, dose, final, _ = sim.run(cases, unit, prep=P, tag=tag)
    timing["tissue"] = round(time.time() - t1, 3)
    t1 = time.time()
    rec, coded = sim.successor(cases, final, P, tag=tag)
    timing["successor"] = round(time.time() - t1, 3)
    ends = {f"t/{w}/{e}": v for (w, e), v in out.items()}
    ends.update({f"s/{e}": v for e, v in rec.items()})
    ends.update({f"c/{e}": v for e, v in coded.items()})
    ends["dose"] = dose
    ends["ncorrupt"] = P["ncorrupt"].astype(float)
    mk = sim.masks(P["TA"], P["TB"], sim.N1S.event_units(cases, tag))
    ends["n_dreg"] = mk["dreg"].sum((-2, -1)).astype(float)
    ends["n_min_reg"] = mk["min_reg"].sum((-2, -1)).astype(float)
    ends["n_dcell"] = mk["dcell"].sum((-2, -1)).astype(float)
    raw = {"TA": P["TA"].astype(np.int8), "TB": P["TB"].astype(np.int8), "R0": P["R0"].astype(np.float32),
           "V0": P["V0"].astype(np.float32), "BgA": np.sign(P["refs"]["own"][0][:, ::D.REGION, ::D.REGION]).astype(np.int8),
           "BgB": np.sign(P["refs"]["foreign"][0][:, ::D.REGION, ::D.REGION]).astype(np.int8),
           "BgC": np.sign(P["refs"]["corrupt"][0][:, ::D.REGION, ::D.REGION]).astype(np.int8),
           "r": final["r"].astype(np.float32), "H": final["H"].astype(np.int8), "W": final["W"].astype(np.int8)}
    if "V" in final:
        raw["V"] = final["V"].astype(np.float32)
    return ends, raw, timing, cases


def run_task(unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(unit, block, purpose, tag)
    for arrays in (ends, raw):
        bad = [k for k, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating)
               and not np.isfinite(np.where(np.isnan(v), 0.0, v)).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {unit} {block}: {bad[:5]}")
    meta = {"unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "labels": [list(x) for x in D.LABELS],
            "branches2": BRANCHES2, "reads": D.READS, "reads2": D.READS2, "cases": [c.key() for c in cases]}
    out = {}
    for kind, arrays in (("shards", ends), ("raw", raw)):
        folder = root / kind / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                     "bytes": final.stat().st_size}
    record = {"unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
              "files": out, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
