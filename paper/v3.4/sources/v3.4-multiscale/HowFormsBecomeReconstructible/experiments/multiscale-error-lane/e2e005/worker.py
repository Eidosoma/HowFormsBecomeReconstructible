"""One E2E005 task: a restored generation 0 (one AR005 raw file: one body, unit and block, eight cases) and its lineages.

E2E004's worker (e2e004.worker), with E2E005's sources, rows and switch diagnostics: the raw file is checked by sha256
against its run's manifest; the acquisition (ar001.sim.prepare, deterministic) is recomputed and must equal the file's V0,
R0 and T; the rows are built (e2e004.sim.packets, unchanged) and checked at generation 0 (e2e004.worker.generation0,
unchanged: every restored packet is the file's first record; protected is R0 with its bonds; post-damage is R0 outside the
patch and flipped inside it); then each future's lineages run (e2e005.sim.lineage). Writes an endpoint shard (the
endpoints at generation 0 and at the horizons, and every generation's switch diagnostics), a raw state shard (V, r, H, W
at the horizons) and a completion record, each atomically.
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
from e2e004.worker import generation0
from sr001 import sim as SRS

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
    raw = {k: z[k] for k in z.files if k != "__meta__"}
    return raw, json.loads(str(z["__meta__"])), {"path": str(path), "sha256": got}


def inputs(source, body, unit, block, stage):
    """The task's restored raw file, its acquisition and (for a stage with a parent subset) the subset's cases."""
    raw, meta, rawfile = load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    parents = D.STAGE_PARENTS.get(stage)
    if parents is not None:                      # the pilot's case subset: every per-case array, and the raw file's
        sel = [j for j, c in enumerate(cases) if c.parent in parents]
        cases = [cases[j] for j in sel]
        V0, ema0, R0, th, T = (x[sel] for x in (V0, ema0, R0, th, T))
        raw = {k: (v[sel] if k in ("V0", "R0", "T") else v[:, sel]) for k, v in raw.items()}
    return raw, meta, rawfile, cases, V0, ema0, R0, th, T, pattern, theta


def stage_lineages(stage, lineages=None):
    lins = D.lineages(stage) if lineages is None else lineages
    cap = D.STAGE_STOP_CAP.get(stage)
    if cap is not None:
        lins = tuple(dict(ln, stop=min(ln["stop"], cap)) for ln in lins)
    return lins


def task(source, body, unit, block, stage, futures=None, lineages=None, t_gen=D.T_GEN):
    t0 = time.process_time()
    raw, meta, rawfile, cases, V0, ema0, R0, th, T, pattern, theta = inputs(source, body, unit, block, stage)
    bridge = {"raw_sha256": True,
              "acquisition": bool(np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"])
                                  and np.array_equal(T, raw["T"]))}
    lins = stage_lineages(stage, lineages)
    rows, labels, aliases, sources = sim.packets(raw, meta, cases, V0, ema0, R0, T, lins)
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    g0, checks0 = generation0(raw, meta, cases, rows, labels, R0, T, Tf, m, V0)
    bridge["generation0"] = bool(all(checks0.values()))
    thf = th * theta
    tag = D.STAGE_TAG[stage]
    nf = D.FUTURES[stage] if futures is None else futures
    ends = {f"g0/{e}": v for e, v in g0.items()}
    states = {}
    timing = {"restore": round(time.process_time() - t0, 3)}
    for f in range(nf):
        t1 = time.process_time()
        reads, alive_at, kept, diags = sim.lineage(body, rows, cases, thf, T, Tf, m, tag, sim.GEN_NAMES(f),
                                                   sim.BIRTH_NAMES(f), t_gen=t_gen, keep=D.HORIZONS)
        for g, rd in reads.items():
            for e, v in rd.items():
                ends[f"f{f}/g{g}/{e}"] = v
            ends[f"f{f}/g{g}/rows"] = np.array(alive_at[g])
        for g, dg in diags.items():
            for e, v in dg.items():
                ends[f"f{f}/d{g}/{e}"] = v
            ends[f"f{f}/d{g}/rows"] = np.array(alive_at[g])
        for g, st in kept.items():
            for x in ("V", "r", "H", "W"):
                states[f"f{f}/g{g}/{x}"] = st[x]
            states[f"f{f}/g{g}/rows"] = np.array(st["rows"])
        timing[f"future{f}"] = round(time.process_time() - t1, 3)
    meta_out = {"study": D.STUDY, "stage": stage, "source": source, "body": body, "unit": unit, "block": block,
                "record_tag": meta["tag"], "tag": tag, "futures": nf, "design_digest": D.digest(),
                "detector_name": D.DETECTOR_NAME,
                "rows": [{"labels": row["labels"], "stop": row["stop"], "route": row["route"], "source": row["source"]}
                         for row in rows],
                "labels": labels, "aliases": aliases, "sources": sources, "checks0": checks0, "rawfile": rawfile,
                "cases": [c.key() for c in cases], "numpy": np.__version__, "timing_cpu_s": timing}
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
           "files": out, "bridge": bridge, "bridge_all_equal": all(bridge.values()), "n_rows": len(meta["rows"]),
           "branch_generations": len(meta["cases"]) * sum(r["stop"] for r in meta["rows"]) * meta["futures"],
           "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
           "cpu": sorted(os.sched_getaffinity(0)), "load_1min": float(open("/proc/loadavg").read().split()[0]),
           "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / key(source) / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmpd = done.with_suffix(f".{os.getpid()}.tmp")
    tmpd.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmpd, done)
    return rec
