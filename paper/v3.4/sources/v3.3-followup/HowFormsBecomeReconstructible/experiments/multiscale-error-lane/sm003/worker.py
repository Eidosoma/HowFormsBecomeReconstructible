"""One SM003 TEST (unit, block) task: SM002's task for the unit exactly (sm002.worker.task's body, here so that the g = 4
reader reads the same float64 final records; sm001.sim.prepare, sm001.sim.run per patch size, the unscaled reader and
the cg reader on every arm's final record plus its no-record control), then the g = 4 reader (sm003.readers.read_g4)
on the same records where the unit's width allows it. Q3 checks this task's every SM002 endpoint and raw state against
sm002.worker.task bit for bit. Writes an endpoint shard, a raw-state shard and a completion record, each atomically.
Templates reach only the record's acquisition and the scoring; no body reads one.
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
from sm002 import coarse as C

from . import design as D
from . import readers as RD


def task(unit, block, purpose, tag=D.TAG, grains=None):
    u = S1D.UNIT[unit]
    grains = D.unit_grains(unit) if grains is None else grains
    cases, V0, ema0, R0, th, T = S1.prepare(f"W{u['w']}", u["side"], block, purpose)
    k = len(cases)
    arms = D.unit_arms(unit)
    na = len(arms)
    side = u["side"]
    ends, raw, timing = {}, {"R0": R0.astype(np.float32), "T": T.astype(np.int8)}, {}
    for L in u["sizes"]:
        rn = f"L{L}"
        t1 = time.time()
        o = S1.run(L, arms, cases, V0, ema0, R0, th, T, side, u["w"], place=u["place"], dil=u["dil"], tag=tag)
        timing[rn] = round(time.time() - t1, 3)
        for e in S1.ENDS:
            ends[f"{rn}/{e}"] = o[e].reshape(len(S1D.READS), na, k)
        ends[f"{rn}/hit"], ends[f"{rn}/onset"] = o["hit"].reshape(na, k), o["onset"].reshape(na, k)
        ends[f"{rn}/wall"] = np.array([S1.wall_distance(T[j], o["m"][j], u["w"], c.message) for j, c in enumerate(cases)], float)
        ends[f"{rn}/signal_updates"] = np.array(o["signal_updates"], float)
        pick = lambda x: np.concatenate([x, x[:k]])          # every arm's final record, then the control's (unread)
        rr, HH, WW = pick(o["r"]), pick(o["H"]), pick(o["W"])
        gains = [D.GAIN] * na + [0.0]
        t1 = time.time()
        o2 = S1.successor(rr, HH, WW, cases, th, T, o["m"], side, u["w"], gains, tag=tag)
        timing[f"{rn}/u"] = round(time.time() - t1, 3)
        for e in S1.ENDS2:
            ends[f"{rn}/u/{e}"] = o2[e].reshape(len(S1D.READS2), na + 1, k)
        t1 = time.time()
        o3 = C.read_cg(rr, HH, WW, cases, th, T, o["m"], side, u["w"], gains, tag=tag)
        timing[f"{rn}/cg"] = round(time.time() - t1, 3)
        for e in C.ENDS_CG:
            ends[f"{rn}/cg/{e}"] = o3[e].reshape(na + 1, k)
        for e in C.ENDS_C:
            ends[f"{rn}/cg/c/{e}"] = o3[f"c/{e}"].reshape(len(S1D.READS2), na + 1, k)
        ends[f"{rn}/cg/ties"] = o3["ties"][: na * k].reshape(na, k).astype(float)
        raw[f"{rn}/r"] = o["r"].reshape(na, k, side, side).astype(np.float32)
        raw[f"{rn}/H"] = o["H"].reshape(na, k, side, side).astype(np.int8)
        raw[f"{rn}/W"] = o["W"].reshape(na, k, side, side).astype(np.int8)
        raw[f"{rn}/m"] = o["m"]
        raw[f"{rn}/uV"] = o2["V"].reshape(na + 1, k, side, side).astype(np.float32)
        raw[f"{rn}/cgV"] = o3["Vc"].reshape(na + 1, k, side // 2, side // 2).astype(np.float32)
        if 4 in grains:
            t1 = time.time()
            o4 = RD.read_g4(rr, HH, WW, cases, th, T, o["m"], side, u["w"], gains, tag)
            timing[f"{rn}/g4"] = round(time.time() - t1, 3)
            for e in RD.ENDS:
                ends[f"{rn}/g4/{e}"] = o4[e].reshape(na + 1, k)
            raw[f"{rn}/g4V"] = o4["V"].reshape(na + 1, k, side // 4, side // 4).astype(np.float32)
    return ends, raw, timing, cases


def run_task(unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(unit, block, purpose, tag)
    bad = [kk for kk, v in ends.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite endpoints in {unit} {block}: {bad[:5]}")
    meta = {"study": D.STUDY, "unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "arms": [a["name"] for a in D.unit_arms(unit)],
            "sizes": list(S1D.UNIT[unit]["sizes"]), "reads": list(S1D.READS), "reads2": list(S1D.READS2),
            "grains": list(D.unit_grains(unit)), "cases": [c.key() for c in cases]}
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
    record = {"unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(), "files": out,
              "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
              "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
              "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
              "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, done)
    return record
