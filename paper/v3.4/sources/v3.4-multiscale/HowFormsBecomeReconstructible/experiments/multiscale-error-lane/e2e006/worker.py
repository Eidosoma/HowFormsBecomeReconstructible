"""One E2E006 task: a restored generation 0 (one AR006 raw file: one body, unit and block, eight cases) and its lineages
under repeated injury.

The raw file is checked by sha256 against its run's manifest; the acquisition (ar001.sim.prepare under the block's
enrolment purpose, deterministic) is recomputed and must equal the file's V0, R0 and T; the rows are built
(e2e006.sim.packets) and checked at generation 0 (e2e002.worker.generation0, unchanged: every restored packet is the file's
first record); the injury schedule is drawn (e2e006.sim.schedule, under the stage's tag, disjoint from generation 0's
patch); then each future's lineages run (e2e006.sim.lineage, the rows meeting SM007's field through
e2e006.sim.FieldAdapter, and the field-free fresh successors at FRESH_AT). Writes an endpoint shard (generation 0's
endpoints, every generation's reads and diagnostics, the fresh successors' reads, the schedule's corners and attempts), a
raw state shard (V, r, H, W at the horizons) and a completion record, each atomically.
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
from e2e002 import worker as W2
from gc001 import sim as GCS
from lr005 import sim as L5S
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


def task(source, body, unit, block, stage, futures=None, lineages=None, t_gen=D.T_GEN, save_fresh=None):
    t0 = time.process_time()
    raw, meta, rawfile = load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    parents = D.STAGE_PARENTS.get(stage)
    if parents is not None:                      # the pilot's case subset: every per-case array, and the raw file's
        sel = [j for j, c in enumerate(cases) if c.parent in parents]
        cases = [cases[j] for j in sel]
        V0, ema0, R0, th, T = (x[sel] for x in (V0, ema0, R0, th, T))
        raw = {k: (v[sel] if k in ("V0", "R0", "T") else v[:, sel]) for k, v in raw.items()}
    bridge = {"raw_sha256": True,
              "acquisition": bool(np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"])
                                  and np.array_equal(T, raw["T"]))}
    lins = D.lineages(stage) if lineages is None else lineages
    cap = D.STAGE_STOP_CAP.get(stage)
    if cap is not None:
        lins = tuple(dict(ln, stop=min(ln["stop"], cap)) for ln in lins)
    rows, labels, aliases, sources = sim.packets(raw, meta, cases, V0, ema0, R0, T, lins)
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m0 = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    am = L5S.anchor_mask(cases, meta["tag"])
    normals = GCS.unit_normals(cases, meta["tag"])
    g0, checks0 = W2.generation0(raw, meta, cases, rows, labels, R0, T, Tf, m0, V0)
    bridge["generation0"] = bool(all(checks0.values()))
    thf = th * theta
    tag = D.STAGE_TAG[stage]
    gmax = max(row["stop"] for row in rows)
    sched, corners, attempts = sim.schedule(cases, m0, tag, gmax)
    nf = D.FUTURES[stage] if futures is None else futures
    scored = D.STAGE_SCORED.get(stage, True)             # P63k: no read at all (the reference configuration)
    kappa_override = D.STAGE_KAPPA.get(stage)
    fresh_at = [g for g in D.STAGE_FRESH_AT.get(stage, D.FRESH_AT) if g <= gmax] if scored else []
    save_fresh = (stage in D.SAVE_FRESH_STAGES) if save_fresh is None else bool(save_fresh)
    ends = {f"g0/{e}": v for e, v in g0.items()} if scored else {}
    if scored:
        for e, src in sim.UNION_READS.items():                 # at generation 0 the union is generation 0's patch
            ends[f"g0/{e}"] = g0[src]
    ends["schedule/corners"], ends["schedule/attempts"] = corners, attempts
    states = {}
    timing = {"restore": round(time.process_time() - t0, 3)}
    adapter = sim.field_adapter() if any(row["field"] != "none" for row in rows) else None
    for f in range(nf):
        t1 = time.process_time()
        reads, alive_at, diags, kept, fresh = sim.lineage(body, rows, cases, thf, T, Tf, m0, am, normals, tag,
                                                          sim.GEN_NAMES(f), sim.BIRTH_NAMES(f), sched=sched, t_gen=t_gen,
                                                          keep=D.HORIZONS if scored else (), field=adapter, fresh_names=sim.FRESH_GEN(f),
                                                          fresh_birth=sim.FRESH_BIRTH(f),
                                                          fresh_at=fresh_at, kappa_override=kappa_override,
                                                          scored=scored, save_fresh=save_fresh)
        for g, rd in fresh.items():
            for e, v in rd.items():
                ends[f"f{f}/x{g}/{e}"] = v
            ends[f"f{f}/x{g}/rows"] = np.array(alive_at[g])
        for g, rd in reads.items():
            for e, v in rd.items():
                ends[f"f{f}/g{g}/{e}"] = v
            ends[f"f{f}/g{g}/rows"] = np.array(alive_at[g])
        for g, dg in diags.items():
            for e, v in dg.items():
                ends[f"f{f}/d{g}/{e}"] = v
            ends[f"f{f}/d{g}/rows"] = np.array(alive_at[g])
        for g, st in kept.items():                         # g: a generation (the lineage), or "x<g>" (its fresh test)
            kk = g if isinstance(g, str) else f"g{g}"
            for x in ("V", "r", "H", "W"):
                states[f"f{f}/{kk}/{x}"] = st[x]
            states[f"f{f}/{kk}/rows"] = np.array(st["rows"])
        timing[f"future{f}"] = round(time.process_time() - t1, 3)
    meta_out = {"study": D.STUDY, "stage": stage, "source": source, "body": body, "unit": unit, "block": block,
                "record_tag": meta["tag"], "tag": tag, "futures": nf, "design_digest": D.digest(),
                "rows": [{"labels": row["labels"], "stop": row["stop"], "policy": row["policy"], "sigma": row["sigma"],
                          "injured": row["injured"], "field": row["field"], "medium": row["medium"],
                          "window": row["window"], "copy": row["copy"], "kappa_key": row["kappa_key"],
                          "source": row["source"]} for row in rows],
                "field": D.FIELD, "kappa_override": kappa_override, "scored": scored, "fresh_at": fresh_at,
                "save_fresh": save_fresh,
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
           "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "pid": os.getpid(),
           "cpu": sorted(os.sched_getaffinity(0)), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / key(source) / body / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmpd = done.with_suffix(f".{os.getpid()}.tmp")
    tmpd.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmpd, done)
    return rec
