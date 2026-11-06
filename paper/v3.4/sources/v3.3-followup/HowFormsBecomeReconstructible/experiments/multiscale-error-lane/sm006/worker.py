"""One SM006 TEST-shape reread task (source, unit, block): the unit's saved final records (r, H, W per patch size, 9 arms
and the no-record control, 8 cases) read at g 1 by SM001's successor with every branch's gain x f (design.TEST_FACTORS:
1/2, 1/(2 sqrt 2), 1/4 on the transfer units; 1/2 and 1/4 on the refined, whose 1/(2 sqrt 2) reads are SM005's). On the
first patch size two bridges: the base reread (gain x 1) against the saved g 1 reads (every sign-based endpoint at every
read), and on the refined units the 1/(2 sqrt 2) read against SM005's E read (every endpoint, bit for bit). Inputs are
checked by sha256 (sm005.worker.load_task). Writes an endpoint shard, a body shard (float32) and a completion record.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from sm001 import design as S1D
from sm001 import sim as S1
from sm004 import fitread4 as F4R
from sm005 import worker as W5

from . import design as D

ENDS = ("in", "in_gen", "align", "shape", "spacing")
SIGN = ("in", "in_gen", "align", "r_align", "shape", "agree")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def task(source, unit, block):
    raw, shard, cases, tag, src_digest = W5.load_task(source, unit, block)
    cfg = S1D.UNIT[unit]
    side, w, na, k = cfg["side"], cfg["w"], len(S1D.unit_arms(unit)), len(cases)
    T = raw["T"].astype(np.float64)
    th = np.zeros_like(T)
    factors = D.TEST_FACTORS[cfg["kind"]]
    ends, bodies, bridge, timing = {}, {}, {}, {}
    L0 = cfg["sizes"][0]
    for L in cfg["sizes"]:
        rn = f"L{L}"
        r, H, W = F4R.branches(raw, rn, na, k, side)
        m = raw[f"{rn}/m"]
        if L == L0:
            o = S1.successor(r, H, W, cases, th, T, m, side, w, [S1D.GAIN] * na + [0.0], tag=tag, reads=S1D.READS2)
            got = {e: o[e].reshape(len(S1D.READS2), na + 1, k) for e in S1.ENDS2}
            bridge["base"] = all(np.array_equal(got[e], shard[f"{rn}/u/{e}"]) for e in SIGN)
            if cfg["kind"] == "refine":
                f6 = D.F_GRID[1]
                z5 = np.load(Path(D.SM005_ROOTS[source]) / "shards" / source.replace("/", "_") / unit / f"{block}.npz")
                o6 = S1.successor(r, H, W, cases, th, T, m, side, w, [S1D.GAIN * f6] * na + [0.0], tag=tag,
                                  reads=(S1D.WINDOW2,))
                bridge["E6_sm005"] = all(np.array_equal(o6[e][-1].reshape(na + 1, k), z5[f"{rn}/E/{e}"]) for e in ENDS)
        for f in factors:
            fn = D.F_NAME[f]
            t1 = time.time()
            o = S1.successor(r, H, W, cases, th, T, m, side, w, [S1D.GAIN * f] * na + [0.0], tag=tag, reads=(S1D.WINDOW2,))
            timing[f"{rn}/{fn}"] = round(time.time() - t1, 3)
            for e in ENDS:
                ends[f"{rn}/g1/{fn}/{e}"] = o[e][-1].reshape(na + 1, k)
            bodies[f"{rn}/g1/{fn}/V"] = o["V"].reshape(na + 1, k, side, side).astype(np.float32)
    return ends, bodies, bridge, timing, {"tag": tag, "source_digest": src_digest, "cases": [c.key() for c in cases]}


def key(source):
    return source.replace("/", "_")


def run_task(source, unit, block, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, bodies, bridge, timing, info = task(source, unit, block)
    if not all(np.isfinite(v).all() for v in ends.values()):
        raise FloatingPointError(f"non-finite endpoints in {source} {unit} {block}")
    meta = {"study": D.STUDY, "source": source, "unit": unit, "block": block, "design_digest": D.digest(),
            "factors": list(D.TEST_FACTORS[S1D.UNIT[unit]["kind"]]), "numpy": np.__version__, "timing_s": timing, **info}
    out = {}
    for kind, arrays in (("shards", ends), ("bodies", bodies)):
        folder = root / kind / key(source) / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": sha(final), "bytes": final.stat().st_size}
    rec = {"source": source, "unit": unit, "block": block, "design_digest": D.digest(), "files": out, "bridge": bridge,
           "bridge_all_equal": all(bridge.values()), "wall_s": round(time.time() - t_wall, 2),
           "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
           "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / key(source) / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmp, done)
    return rec
