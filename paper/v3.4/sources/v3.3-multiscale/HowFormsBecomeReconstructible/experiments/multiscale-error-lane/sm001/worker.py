"""One (unit, block) task: DL002's acquisition of the unit's stripes at its side (sm001.sim.prepare), then for each patch
size one repair episode under every arm as branches (sm001.sim.run), then the fresh successor reading every arm's final
record, plus its paired no-record control (sm001.sim.successor). Writes an endpoint shard, a raw-state shard and a
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


def task(unit, block, purpose, tag=D.TAG):
    u = D.UNIT[unit]
    cases, V0, ema0, R0, th, T = sim.prepare(f"W{u['w']}", u["side"], block, purpose)
    k = len(cases)
    arms = D.unit_arms(unit)
    na = len(arms)
    ends, raw, timing = {}, {"R0": R0.astype(np.float32), "T": T.astype(np.int8)}, {}
    for L in u["sizes"]:
        rn = f"L{L}"
        t1 = time.time()
        o = sim.run(L, arms, cases, V0, ema0, R0, th, T, u["side"], u["w"], place=u["place"], dil=u["dil"], tag=tag)
        timing[rn] = round(time.time() - t1, 3)
        for e in sim.ENDS:
            ends[f"{rn}/{e}"] = o[e].reshape(len(D.READS), na, k)
        ends[f"{rn}/hit"], ends[f"{rn}/onset"] = o["hit"].reshape(na, k), o["onset"].reshape(na, k)
        ends[f"{rn}/wall"] = np.array([sim.wall_distance(T[j], o["m"][j], u["w"], c.message) for j, c in enumerate(cases)], float)
        ends[f"{rn}/n_anc"] = np.array([(o["m"][j] & sim.anchor_mask([c], u["side"], tag)[0]).sum() for j, c in enumerate(cases)], float)
        ends[f"{rn}/signal_updates"] = np.array(o["signal_updates"], float)
        pick = lambda x: np.concatenate([x, x[:k]])          # every arm's final record, then the control's (unread)
        t1 = time.time()
        o2 = sim.successor(pick(o["r"]), pick(o["H"]), pick(o["W"]), cases, th, T, o["m"], u["side"], u["w"],
                           [D.GAIN] * na + [0.0], tag=tag)
        timing[f"{rn}/succ"] = round(time.time() - t1, 3)
        for e in sim.ENDS2:
            ends[f"{rn}/s/{e}"] = o2[e].reshape(len(D.READS2), na + 1, k)
        side = u["side"]
        raw[f"{rn}/r"] = o["r"].reshape(na, k, side, side).astype(np.float32)
        raw[f"{rn}/H"] = o["H"].reshape(na, k, side, side).astype(np.int8)
        raw[f"{rn}/W"] = o["W"].reshape(na, k, side, side).astype(np.int8)
        raw[f"{rn}/m"] = o["m"]
        raw[f"{rn}/sV"] = o2["V"].reshape(na + 1, k, side, side).astype(np.float32)
    return ends, raw, timing, cases


def run_task(unit, block, purpose, root, tag=D.TAG):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases = task(unit, block, purpose, tag)
    bad = [kk for kk, v in ends.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite endpoints in {unit} {block}: {bad[:5]}")
    meta = {"unit": unit, "block": block, "purpose": purpose, "tag": tag, "design_digest": D.digest(),
            "numpy": np.__version__, "timing_s": timing, "arms": [a["name"] for a in D.unit_arms(unit)],
            "sizes": list(D.UNIT[unit]["sizes"]), "reads": list(D.READS), "reads2": list(D.READS2),
            "cases": [c.key() for c in cases]}
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
