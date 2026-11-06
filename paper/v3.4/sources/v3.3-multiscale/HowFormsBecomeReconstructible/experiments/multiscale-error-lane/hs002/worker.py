"""HS002's worker: one block's lineages continued from HS001's saved rewrite-256 records to 1,024 rewrites.

It checks the block's HS001 raw file against the sha256 its HS001 run recorded, continues each budget of the stage
(hs002.sim.continue_lineages), and writes ROOT/shards/<block>.npz (the eight new checkpoints' scores, the sign-only
and amplitude outcomes, the lineage reads 257-1,024, the field SDs and the concordance), ROOT/raw/<block>.npz (the
checkpoint and final packets), ROOT/export/<block>.npz for HS001's own cohort (HS001's founder-identification schema at
the new checkpoints: the candidate dictionary, packets, recipients' full states, labels, IDs; no decoder) and
ROOT/done/<block>.json. No identity export is written for E014's cohort.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import time
from pathlib import Path

import numpy as np

from hs001 import sim as S1, worker as W1

from . import design as D, sim as S

SHARD_KEYS = ("ck_scores", "ck_sign_scores", "ck_amp", "g_scores", "field_sd", "conc_same", "conc_cross", "corr_same",
              "corr_cross")


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def source_raw(stage, block):
    """HS001's raw file for the block, checked against the sha256 its HS001 run recorded."""
    root = D.SOURCE_ROOT[stage]
    M = json.loads((root / "manifest.json").read_text())
    rec = M["tasks"][str(block)]["files"]["raw"]
    path = root / rec["path"]
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != rec["sha256"]:
        raise RuntimeError(f"HS001's raw record for {block} differs from its recorded sha256")
    return np.load(path), {"path": str(path), "sha256": sha, "hs001_digest": M["design_digest"]}


def run_task(block, stage, root, horizon=D.HORIZON):
    root = Path(root)
    t0, c0 = time.time(), time.process_time()
    export = stage in D.EXPORT_STAGES
    raw1, prov = source_raw(stage, block)
    proto = raw1["prototype"]
    cks = tuple(c for c in D.NEW_CHECKPOINTS if c <= horizon)
    shard, raw, exp = {}, {}, {}
    for f in D.FACTORS[stage]:
        c = S.continue_lineages(raw1[f"f{f}/final_packets"], block, f, proto, horizon=horizon, checkpoints=cks, export=export)
        for k in SHARD_KEYS:
            shard[f"f{f}/{k}"] = c[k]
        raw[f"f{f}/ck_packets"], raw[f"f{f}/final_packets"] = c["ck_packets"], c["final_packets"]
        if export:
            exp[f"f{f}/packets_checkpoint"] = c["ck_packets"]
            exp[f"f{f}/recipient_checkpoint"] = c["ck_fields"]
    if export:
        src = S1.source(block)                          # the candidate dictionary (E001's formation, unchanged)
        if not np.array_equal(src["prototype"], proto):
            raise RuntimeError("the regenerated prototypes differ from HS001's saved ones")
        exp["evaluator/prototypes"] = src["prototype"]
        exp["evaluator/prototype_halves"] = src["prototype_halves"]
        exp["labels/lineage_source_founder"] = W1.labels(D.LINEAGE)
        exp["labels/formation_qualified"] = np.asarray(S1.E14.formation_metrics(src)["qualified"], bool)
        exp["ids/block"] = np.array(block, np.int64)
        exp["ids/background_id"] = np.array(block, np.int64)
        exp["ids/stream"] = np.array(block + 1000000, np.int64)
        exp["ids/founder"] = np.arange(4, dtype=np.int64)
        exp["ids/recipient"] = np.arange(2, dtype=np.int64)
        exp["ids/checkpoint"] = np.array(cks, np.int64)
    meta = {"study": D.STUDY, "block": block, "stage": stage, "tag": D.STAGE_TAG[stage], "design_digest": D.digest(),
            "factors": D.FACTORS[stage], "start": D.START, "horizon": horizon, "checkpoints": list(cks),
            "lineage": D.LINEAGE, "stream": block + 1000000, "source": prov, "numpy": np.__version__,
            "identity_export": export}
    files = {}
    for kind, arrays in (("shards", shard), ("raw", raw)) + ((("export", exp),) if export else ()):
        d = root / kind
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{block}.npz"
        tmp = d / f".{block}.{os.getpid()}.tmp.npz"
        np.savez(tmp, __meta__=np.array(json.dumps(meta, default=list)), **arrays)
        os.replace(tmp, path)
        files[kind] = {"path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "bytes": path.stat().st_size}
    rec = {"block": block, "stage": stage, "design_digest": D.digest(), "files": files, "source": prov,
           "finished_utc": utc(), "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "cpu": os.sched_getaffinity(0).pop() if len(os.sched_getaffinity(0)) == 1 else -1}
    d = root / "done"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{block}.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec
