"""One SM007 task: a restored AR005 raw file (one body, unit and block, eight cases) and every arrangement of its recipients.

The raw file is checked by sha256 against its run's manifest; the acquisition (ar001.sim.prepare under the block's
enrolment purpose, deterministic) is recomputed and must equal the file's V0, R0 and T. Then sm007.sim.run simulates the
stage's arrangements in one batch. Writes an endpoint shard (each branch's a_v and sign at every read, its window-mean gain
and exposure, the branch maps), a raw state shard (the final bodies) and a completion record, each atomically.
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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(source):
    return source.replace("/", "_")


def load(source, body, unit, block):
    """The restored raw file, checked by sha256 against its run's manifest."""
    root = Path(D.SOURCES[source]["root"])
    M = json.loads((root / "manifest.json").read_text())
    f = M["tasks"][f"{body}/{unit}/{block}"]["files"]["raw"]
    path = root / f["path"]
    got = sha(path)
    if got != f["sha256"]:
        raise ValueError(f"{source} {body}/{unit}/{block}: the raw file's sha256 differs from its manifest's")
    z = np.load(path)
    raw = {k: z[k] for k in ("V0", "R0", "T")}
    return raw, json.loads(str(z["__meta__"])), {"path": str(path), "sha256": got}


def task(source, body, unit, block, stage, futures=None, arrangements=None, window=None, kappa=None, reads=None,
         keep_final=True):
    """Every future of the stage (D.FUTURES), each a sim.run of the whole arrangement set, laid out future-major along
    the branch axis: branches [f n, (f + 1) n) are future f's, with br_future, br_case and br_arr per branch."""
    raw, meta, rawfile = load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    bridge = {"raw_sha256": True,
              "acquisition": bool(np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"])
                                  and np.array_equal(T, raw["T"]))}
    arrs = D.STAGE_SETS[stage] if arrangements is None else arrangements
    win = D.STAGE_WINDOW.get(stage, D.WINDOW) if window is None else window
    if reads is None:
        reads = tuple(r for r in D.READS if r <= win) or (win,)
    F = D.FUTURES[stage] if futures is None else futures
    tag = D.STAGE_TAG[stage]
    outs = [sim.run(body, arrs, cases, R0, th * theta, T, tag, kappa=kappa, future=f, window=win, reads=reads,
                    keep_final=keep_final) for f in range(F)]
    n = len(outs[0]["br_case"])
    cat = lambda key, axis=0: np.concatenate([o[key] for o in outs], axis=axis)
    ends = {"reads": outs[0]["reads"],
            "a_v": cat("a_v", 1) if len(reads) else outs[0]["a_v"], "sign": cat("sign", 1) if len(reads) else outs[0]["sign"],
            "gain_mean": cat("gain_mean"), "expo_mean": cat("expo_mean"), "stress_mean": cat("stress_mean"),
            "br_case": cat("br_case"), "br_arr": cat("br_arr"), "br_future": np.repeat(np.arange(F), n)}
    states = ({"V": cat("V").astype(np.float64), "br_case": ends["br_case"], "br_future": ends["br_future"]}
              if keep_final else {})
    meta_out = {"study": D.STUDY, "stage": stage, "source": source, "body": body, "unit": unit, "block": block,
                "record_tag": meta["tag"], "tag": tag, "futures": F, "branches_a_future": n, "window": win,
                "kappa": outs[0]["kappa"], "kappa_paper": outs[0]["kappa_paper"], "design_digest": D.digest(),
                "arrangements": [list(a) for a in arrs], "rawfile": rawfile, "cases": [c.key() for c in cases],
                "n_groups": int(outs[0]["n_groups"]), "numpy": np.__version__}
    return ends, states, meta_out, bridge


def run_task(source, body, unit, block, stage, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, states, meta, bridge = task(source, body, unit, block, stage)
    bad = [k for k, v in ends.items() if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite endpoints in {source} {body} {unit} {block}: {bad[:5]}")
    out = {}
    for kind, arrays in (("shards", ends), ("raw", states)):
        folder = root / kind / key(source) / body / unit
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / f"{block}.npz"
        tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta)), **arrays)
        os.replace(tmp, final)
        out[kind] = {"path": str(final.relative_to(root)), "sha256": sha(final), "bytes": final.stat().st_size}
    rec = {"source": source, "body": body, "unit": unit, "block": block, "stage": stage, "design_digest": D.digest(),
           "files": out, "bridge": bridge, "bridge_all_equal": all(bridge.values()), "n_rows": int(len(ends["br_case"])),
           "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
           "cpu": sorted(os.sched_getaffinity(0)), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / key(source) / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmpd = done.with_suffix(f".{os.getpid()}.tmp")
    tmpd.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmpd, done)
    return rec
