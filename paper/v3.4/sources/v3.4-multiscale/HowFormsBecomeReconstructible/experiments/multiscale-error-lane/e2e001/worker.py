"""One E2E001 task: a restored generation 0 (one AR raw file: one body, unit and block, eight cases) and its successors.

The raw file is checked by sha256 against its run's manifest; the acquisition (ar001.sim.prepare, deterministic) is
recomputed and must equal the file's V0, R0 and T; the rows are built (e2e001.sim.packets) and checked at generation 0
(every policy row is the file's first record; protected is R0 with its bonds; post-damage is R0 outside the patch and
flipped inside it under memory); then each future's lineage runs (e2e001.sim.lineage). Writes an endpoint shard, a raw
state shard and a completion record, each atomically.
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
    for policy rows, the pre-injury body otherwise)."""
    arms_of = {name: list(arms) for name, arms in meta["runs"]}
    H0, W0, _ = sim.protected(R0)
    checks = {}
    for label, i in labels.items():
        H, W, r = rows[i]["packet"]
        parts = label.split("/")
        if parts[0] in D.POLICIES:
            arm, sit = parts
            src = sit if arm in arms_of.get(sit, []) else sit.replace("@1", "@0")
            j = arms_of[src].index(arm)
            checks[label] = bool(np.array_equal(H, raw[f"{src}/H"][j]) and np.array_equal(W, raw[f"{src}/W"][j])
                                 and np.array_equal(r, raw[f"{src}/r"][j]))
        elif label == "protected":
            checks[label] = bool(np.array_equal(H, H0) and np.array_equal(W, W0) and np.array_equal(r, R0))
        elif parts[0] == "post":
            base = parts[1].split("@")[0]
            if D.RECORD_HIT[base]:
                checks[label] = bool(np.array_equal(r[~m], R0[~m]) and np.array_equal(r[m], -R0[m]))
            else:
                checks[label] = bool(np.array_equal(r, R0) and np.array_equal(H, H0) and np.array_equal(W, W0))
    ends = {}
    for i, row in enumerate(rows):
        H, W, r = row["packet"]
        lab = row["labels"][0]
        Vb = row["V0"] if row["V0"] is not None else V0
        if lab.split("/")[0] in D.POLICIES:
            arm, sit = lab.split("/")
            src = sit if arm in arms_of.get(sit, []) else sit.replace("@1", "@0")
            Vb = raw[f"{src}/V"][arms_of[src].index(arm)]
        sc = sim.score(Vb, r, T, Tf, m)
        for e, v in sc.items():
            ends.setdefault(e, []).append(v)
    return {e: np.stack(v) for e, v in ends.items()}, checks


def task(source, body, unit, block, stage, futures=None, situations=None, gen_fn=None, t_gen=D.T_GEN):
    t0 = time.process_time()
    raw, meta, rawfile = load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    purpose = D.SOURCES[source]["purpose"]
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, purpose)
    bridge = {"raw_sha256": True,
              "acquisition": bool(np.array_equal(V0, raw["V0"]) and np.array_equal(R0, raw["R0"])
                                  and np.array_equal(T, raw["T"]))}
    runs = {name for name, _ in meta["runs"]}
    sits = [s for s in (situations or D.MAIN + D.SECOND) if s in runs or s.replace("@1", "@0") in runs]
    rows, labels, aliases = sim.packets(raw, meta, cases, V0, ema0, R0, T, sits, meta["tag"])
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    H0, W0, _ = sim.protected(R0)
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
        sel = list(range(len(rows))) if f < D.SIDE_FUTURES else [i for i, row in enumerate(rows) if row["stop"] >= D.G_MAIN]
        sub = [rows[i] for i in sel]
        reads, alive_at, kept, _final = sim.lineage(body, sub, cases, tuple(np.concatenate([row["packet"][x] for row in sub])
                                                                            for x in range(3)),
                                                    thf, T, Tf, m, H0, W0, tag, sim.GEN_NAMES(f), sim.BIRTH_NAMES(f),
                                                    t_gen=t_gen, gen_fn=gen_fn, keep=D.HORIZONS)
        for g, rd in reads.items():
            for e, v in rd.items():
                ends[f"f{f}/g{g}/{e}"] = v
            ends[f"f{f}/g{g}/rows"] = np.array([sel[j] for j in alive_at[g]])
        for g, st in kept.items():
            for x in ("V", "r", "H", "W"):
                states[f"f{f}/g{g}/{x}"] = st[x]
        timing[f"future{f}"] = round(time.process_time() - t1, 3)
    meta_out = {"study": D.STUDY, "stage": stage, "source": source, "body": body, "unit": unit, "block": block,
                "record_tag": meta["tag"], "tag": tag, "futures": nf, "situations": sits, "design_digest": D.digest(),
                "rows": [{"labels": row["labels"], "stop": row["stop"], "route": row["route"].name,
                          "persist": bool(row["persist"])} for row in rows],
                "labels": labels, "aliases": aliases, "checks0": checks0, "rawfile": rawfile,
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
