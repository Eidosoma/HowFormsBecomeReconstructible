"""One SM005 reread task (source, unit, block): the refined unit's saved final records (r, H, W per patch size, 9 arms and
the no-record control, 8 cases) reread by the five readers (sm005.readers): the base (sm001.sim.successor, with its
bridge to the saved g 1 reads at every read), cg (sm002.coarse.read_cg, with its bridge to the saved cg reads), and the
variants C, E and B. Every input file is checked by sha256 against its stage's manifest and the case set enrolled as its
study enrolled it. Writes an endpoint shard, a body shard (float32) and a completion record, each atomically.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

from dl002 import design as D2
from mse.assay import enrol
from sm001 import design as S1D
from sm001 import sim as S1
from sm002 import coarse as C
from sm003 import readers as RD3
from sm004 import fitread4 as F4R

from . import design as D
from . import readers as RD

SIGN_ENDS = ("in", "in_gen", "align", "r_align", "shape", "agree")      # gated exactly; the spacing recorded
_MANIFESTS = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_manifest(source):
    if source not in _MANIFESTS:
        _MANIFESTS[source] = json.loads((Path(D.SOURCES[source][0]) / "manifest.json").read_text())
    return _MANIFESTS[source]


def load_task(source, unit, block):
    root, tag, purpose = D.SOURCES[source]
    root = Path(root)
    M = source_manifest(source)
    files = M["tasks"][f"{unit}/{block}"]["files"]
    for f in files.values():
        if sha(root / f["path"]) != f["sha256"]:
            raise ValueError(f"{source} {f['path']}: sha256 differs from its manifest")
    raw, shard = np.load(root / "raw" / unit / f"{block}.npz"), np.load(root / "shards" / unit / f"{block}.npz")
    meta = json.loads(str(shard["__meta__"]))
    if meta["unit"] != unit or meta["block"] != block or meta["tag"] != tag or meta["design_digest"] != M["design_digest"]:
        raise ValueError(f"{source} {unit} {block}: the shard's meta does not match its manifest")
    cases = enrol([block], D2.MESSAGES, D2.PARENTS, purpose)
    if [list(c.key()) for c in cases] != [list(x) for x in meta["cases"]]:
        raise ValueError(f"{source} {unit} {block}: the case set differs from the shard's")
    return raw, shard, cases, tag, M["design_digest"]


def task(source, unit, block, variants=D.VARIANTS):
    raw, shard, cases, tag, src_digest = load_task(source, unit, block)
    cfg = S1D.UNIT[unit]
    side, w, na, k = cfg["side"], cfg["w"], len(S1D.unit_arms(unit)), len(cases)
    T = raw["T"].astype(np.float64)
    gains = [S1D.GAIN] * na + [0.0]
    ends, bodies, bridge, timing = {}, {}, {}, {}
    for L in cfg["sizes"]:
        rn = f"L{L}"
        r, H, W = F4R.branches(raw, rn, na, k, side)
        m = raw[f"{rn}/m"]
        t1 = time.time()
        o = RD.read_base(r, H, W, cases, T, m, side, w, gains, tag)
        timing[f"{rn}/base"] = round(time.time() - t1, 3)
        got = {e: o[e].reshape(len(S1D.READS2), na + 1, k) for e in S1.ENDS2}
        b = {"exact": {e: bool(np.array_equal(got[e], shard[f"{rn}/u/{e}"])) for e in SIGN_ENDS},
             "spacing_rel_max": float((np.abs(got["spacing"] - shard[f"{rn}/u/spacing"]) / np.abs(shard[f"{rn}/u/spacing"])).max()),
             "V_max_abs_diff": float(np.abs(o["V"].reshape(na + 1, k, side, side) - raw[f"{rn}/uV"].astype(np.float64)).max())}
        for e in RD.ENDS:
            ends[f"{rn}/base/{e}"] = o[e][-1].reshape(na + 1, k)
        bodies[f"{rn}/base/V"] = o["V"].reshape(na + 1, k, side, side).astype(np.float32)
        t1 = time.time()
        o2 = RD3.read_g2(r, H, W, cases, np.zeros_like(T), T, m, side, w, gains, tag)
        timing[f"{rn}/cg"] = round(time.time() - t1, 3)
        b["cg_exact"] = {e: bool(np.array_equal(o2[e].reshape(na + 1, k), shard[f"{rn}/cg/{e}"])) for e in C.ENDS_CG
                         if e != "spacing"}
        b["cg_spacing_rel_max"] = float((np.abs(o2["spacing"].reshape(na + 1, k) - shard[f"{rn}/cg/spacing"])
                                         / np.abs(shard[f"{rn}/cg/spacing"])).max())
        b["all_equal"] = all(b["exact"].values()) and all(b["cg_exact"].values())
        bridge[rn] = b
        for e in RD.ENDS:
            ends[f"{rn}/cg/{e}"] = o2[e].reshape(na + 1, k)
        bodies[f"{rn}/cg/V"] = o2["V"].reshape(na + 1, k, side // 2, side // 2).astype(np.float32)
        for v in variants:
            t1 = time.time()
            ov = RD.read_variant(v, r, H, W, cases, T, m, side, w, gains, tag)
            timing[f"{rn}/{v}"] = round(time.time() - t1, 3)
            for e in RD.ENDS:
                ends[f"{rn}/{v}/{e}"] = ov[e].reshape(na + 1, k)
            bodies[f"{rn}/{v}/V"] = ov["V"].reshape(na + 1, k, side, side).astype(np.float32)
    return ends, bodies, bridge, timing, {"tag": tag, "source_digest": src_digest, "cases": [c.key() for c in cases]}


def key(source):
    return source.replace("/", "_")


def run_task(source, unit, block, root):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, bodies, bridge, timing, info = task(source, unit, block)
    bad = [kk for kk, v in ends.items() if not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite endpoints in {source} {unit} {block}: {bad[:5]}")
    meta = {"study": D.STUDY, "source": source, "unit": unit, "block": block, "design_digest": D.digest(),
            "readers": list(D.READERS), "variants": {v: D.variant(v) for v in D.VARIANTS}, "numpy": np.__version__,
            "timing_s": timing, **info}
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
           "bridge_all_equal": all(b["all_equal"] for b in bridge.values()),
           "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "cpu": sorted(os.sched_getaffinity(0)), "timing_s": timing,
           "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / key(source) / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmp = done.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmp, done)
    return rec
