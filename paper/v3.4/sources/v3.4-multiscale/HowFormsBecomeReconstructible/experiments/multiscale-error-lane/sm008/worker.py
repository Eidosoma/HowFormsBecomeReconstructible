"""One SM008 task: one body and one block, both units' restored AR005 raw files (16 cases), and every arrangement.

Each raw file is checked by sha256 against its run's manifest (sm007.worker.load); each unit's acquisition (ar001.sim.prepare
under the block's enrolment purpose) is recomputed and must equal its file's V0, R0 and T. The cases are the healthy unit's
8 then the struggling unit's 8 (design.ROLES). sm008.sim.run simulates the stage's arrangements in one batch per future.
Writes an endpoint shard, a raw state shard (the final bodies) and a completion record, each atomically.
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
from sm007 import worker as W7

from . import design as D
from . import sim


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


key = W7.key


def inputs(source, body, block, check=True):
    """The task's 16 cases (healthy then struggling), R0, th x theta and T; the bridge flags and the raw files."""
    cases, R0s, ths, Ts, bridge, rawfiles = [], [], [], [], {}, {}
    for role, unit in zip(("healthy", "struggling"), D.ROLES[body]):
        pattern, theta = A.parse_unit(unit)
        c, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
        if check:
            raw, meta, rawfile = W7.load(source, body, unit, block)
            bridge[f"acquisition/{unit}"] = bool(np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"])
                                                 and np.array_equal(T, raw["T"]))
            rawfiles[unit] = dict(rawfile, record_tag=meta["tag"])
        cases += list(c)
        R0s.append(R0)
        ths.append(th * theta)
        Ts.append(T)
    assert [x.key() for x in cases[:D.NCASE]] == [x.key() for x in cases[D.NCASE:]], "the two units' cases differ"
    bridge["raw_sha256"] = bool(check)
    return cases, np.concatenate(R0s), np.concatenate(ths), np.concatenate(Ts), bridge, rawfiles


def task(source, body, block, stage, futures=None, arrangements=None, window=None, kappa=None, reads=None, keep_final=True):
    """Every future of the stage, each a sim.run of the whole arrangement set, laid out future-major along the branch axis."""
    cases, R0, thf, T, bridge, rawfiles = inputs(source, body, block)
    arrs = D.STAGE_SETS[stage] if arrangements is None else arrangements
    win = D.STAGE_WINDOW.get(stage, D.WINDOW) if window is None else window
    if reads is None:
        reads = tuple(r for r in D.READS if r <= win) or (win,)
    F = D.FUTURES[stage] if futures is None else futures
    tag = D.STAGE_TAG[stage]
    outs = [sim.run(body, arrs, cases, R0, thf, T, tag, kappa=kappa, future=f, window=win, reads=reads,
                    keep_final=keep_final) for f in range(F)]
    n = len(outs[0]["br_case"])
    cat = lambda k_, axis=0: np.concatenate([o[k_] for o in outs], axis=axis)
    ends = {"reads": outs[0]["reads"], "a_v": cat("a_v", 1), "sign": cat("sign", 1),
            "gain_mean": cat("gain_mean"), "expo_mean": cat("expo_mean"), "stress_mean": cat("stress_mean"),
            "br_case": cat("br_case"), "br_arr": cat("br_arr"), "br_group": cat("br_group"), "br_pos": cat("br_pos"),
            "br_future": np.repeat(np.arange(F), n)}
    states = ({"V": cat("V").astype(np.float64), "br_case": ends["br_case"], "br_future": ends["br_future"]}
              if keep_final else {})
    meta_out = {"study": D.STUDY, "stage": stage, "source": source, "body": body, "block": block,
                "roles": {"healthy": D.ROLES[body][0], "struggling": D.ROLES[body][1]}, "tag": tag, "futures": F,
                "branches_a_future": n, "window": win, "kappa": outs[0]["kappa"], "kappa_paper": outs[0]["kappa_paper"],
                "design_digest": D.digest(), "arrangements": [list(a) for a in arrs], "rawfiles": rawfiles,
                "cases": [c.key() for c in cases], "n_groups": int(outs[0]["n_groups"]), "numpy": np.__version__}
    return ends, states, meta_out, bridge


def run_task(source, body, block, stage, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, states, meta, bridge = task(source, body, block, stage)
    bad = [k for k, v in ends.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite endpoints in {source} {body} {block}: {bad[:5]}")
    out = {}
    for kind, arrays in (("shards", ends), ("raw", states)):
        folder = root / kind / key(source) / body
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": sha(final), "bytes": final.stat().st_size}
    rec = {"source": source, "body": body, "block": block, "stage": stage, "design_digest": D.digest(), "files": out,
           "bridge": bridge, "bridge_all_equal": all(bridge.values()), "n_rows": int(len(ends["br_case"])),
           "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
           "cpu": sorted(os.sched_getaffinity(0)), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / key(source) / body / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmpd = done.with_suffix(f".{os.getpid()}.tmp")
    tmpd.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmpd, done)
    return rec
