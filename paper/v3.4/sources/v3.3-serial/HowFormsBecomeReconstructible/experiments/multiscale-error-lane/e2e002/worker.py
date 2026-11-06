"""One E2E002 task: a restored generation 0 (one AR raw file: one body, unit and block, eight cases) and its lineages.

The raw file is checked by sha256 against its run's manifest; the acquisition (ar001.sim.prepare, deterministic) is
recomputed and must equal the file's V0, R0 and T; the rows are built (e2e002.sim.packets) and checked at generation 0
(every restored packet is the file's first record; protected is R0 with its bonds; post-damage is R0 outside the patch
and flipped inside it); then each future's lineages run (e2e002.sim.lineage). Writes an endpoint shard (the endpoints at
generation 0 and at the horizons, and the detectors' diagnostics of every generation), a raw state shard (V, r, H, W at
the horizons) and a completion record, each atomically.
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


def generation0(raw, meta, cases, rows, labels, R0, T, Tf, m, V0):
    """The checks at generation 0 and every row's endpoints there (the restored record; the body: the saved final body
    for a restored packet, the pre-injury body otherwise)."""
    arms_of = {name: list(arms) for name, arms in meta["runs"]}
    H0, W0, _ = sim.protected(R0)
    checks, ends = {}, {}
    for i, row in enumerate(rows):
        H, W, r = row["packet"]
        src = row["source"]
        Vb = V0
        if src == "protected":
            checks[f"row{i}:{src}"] = bool(np.array_equal(H, H0) and np.array_equal(W, W0) and np.array_equal(r, R0))
        elif src.startswith("post/"):
            checks[f"row{i}:{src}"] = bool(np.array_equal(r[~m], R0[~m]) and np.array_equal(r[m], -R0[m]))
        else:
            arm, sit = src.split("/")
            j = arms_of[sit].index(arm)
            checks[f"row{i}:{src}"] = bool(np.array_equal(H, raw[f"{sit}/H"][j]) and np.array_equal(W, raw[f"{sit}/W"][j])
                                           and np.array_equal(r, raw[f"{sit}/r"][j]))
            Vb = raw[f"{sit}/V"][j]
        for e, v in sim.score(Vb, r, T, Tf, m).items():
            ends.setdefault(e, []).append(v)
    return {e: np.stack(v) for e, v in ends.items()}, checks


def task(source, body, unit, block, stage, futures=None, lineages=None, t_gen=D.T_GEN):
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
    _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    am = L5S.anchor_mask(cases, meta["tag"])
    normals = GCS.unit_normals(cases, meta["tag"])
    exact0 = np.where(R0 > 0, 1.0, -1.0)
    cue0 = {s: (GCS.read_at(exact0, normals, s) if s else exact0) for s in sorted({row["sigma"] for row in rows})}
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
        sel = list(range(len(rows))) if f == 0 else [i for i, row in enumerate(rows)
                                                     if set(row["labels"]) & set(D.SECOND_FUTURE)]
        if not sel:
            continue
        sub = [rows[i] for i in sel]
        reads, alive_at, diags, kept = sim.lineage(body, sub, cases, thf, T, Tf, m, am, normals, cue0, tag,
                                                   sim.GEN_NAMES(f), sim.BIRTH_NAMES(f), t_gen=t_gen, keep=D.HORIZONS)
        for g, rd in reads.items():
            for e, v in rd.items():
                ends[f"f{f}/g{g}/{e}"] = v
            ends[f"f{f}/g{g}/rows"] = np.array([sel[j] for j in alive_at[g]])
        for g, dg in diags.items():
            for e, v in dg.items():
                ends[f"f{f}/d{g}/{e}"] = v
            ends[f"f{f}/d{g}/rows"] = np.array([sel[j] for j in alive_at[g]])
        for g, st in kept.items():
            for x in ("V", "r", "H", "W"):
                states[f"f{f}/g{g}/{x}"] = st[x]
            states[f"f{f}/g{g}/rows"] = np.array([sel[j] for j in st["rows"]])
        timing[f"future{f}"] = round(time.process_time() - t1, 3)
    meta_out = {"study": D.STUDY, "stage": stage, "source": source, "body": body, "unit": unit, "block": block,
                "record_tag": meta["tag"], "tag": tag, "futures": nf, "design_digest": D.digest(),
                "rows": [{"labels": row["labels"], "stop": row["stop"], "policy": row["policy"], "cue": row["cue"],
                          "sigma": row["sigma"], "source": row["source"]} for row in rows],
                "labels": labels, "aliases": aliases, "sources": sources, "checks0": checks0, "rawfile": rawfile,
                "second_future": list(D.SECOND_FUTURE), "cases": [c.key() for c in cases], "numpy": np.__version__,
                "timing_cpu_s": timing}
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
