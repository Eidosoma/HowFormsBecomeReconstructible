"""HS001's worker: one block at both budgets (E001's formation and capture, then per budget the protected probes and
256 renewals of the lineage arms with sixteen checkpoint reads). Writes ROOT/shards/<block>.npz (every score, the
sign-only and amplitude outcomes, the probes, the concordance, the field SDs, formation), ROOT/raw/<block>.npz (the
checkpoint and final packets, the initial panels, the prototypes, the acquired record and the background) and
ROOT/done/<block>.json (sha256 of every file, timings).

For HS001's own cohort it also writes ROOT/export/<block>.npz, the founder-identification export of the information
audit's schema (INFORMATION_AUDIT_HANDOFF.md, the Forms lane; hs001.export documents every array): the candidate
dictionary (the block's four founders' prototypes, evaluator resources that no reader or writer ever receives), the
packets and the recipients' fields in native dtypes, the label table, the IDs and the inclusion flags. No identity
export is written for the stage 'e014' (E014's published cohort): its raw lineage fields are on the producing host
only, and the handoff's note reserves any regeneration of that cohort for identity decoding to the PI's word.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import time
from pathlib import Path

import numpy as np

from . import design as D, sim as S

SHARD_KEYS = ("probe_scores", "probe_sign_scores", "probe_amp", "ck_scores", "ck_sign_scores", "ck_amp", "g_scores",
              "field_sd", "conc_same", "conc_cross", "corr_same", "corr_cross")
RAW_KEYS = ("ck_packets", "final_packets", "initial_lineage", "initial_protected")
EXPORT_STAGES = ("smoke", "tests", "probe", "preflight", "debug", "development")
# the record's source founder per arm, as an offset from the lineage's own founder (None: no founder's record)
SOURCE_OFFSET = {"rewrite": 0, "foreign": 1, "erased": None, "background": None,
                 "copy": 0, "copy_foreign": 1, "copy_erased": None, "copy_background": None}


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def labels(arms, founders=4):
    """(founders, arms) int8: the founder index whose acquired record the arm's lineage started from, -1 for none."""
    out = np.full((founders, len(arms)), -1, np.int8)
    for a, arm in enumerate(arms):
        off = SOURCE_OFFSET[arm]
        if off is not None:
            out[:, a] = (np.arange(founders) + off) % founders
    return out


def run_task(block, stage, root, horizon=D.HORIZON):
    root = Path(root)
    t0, c0 = time.time(), time.process_time()
    export = stage in EXPORT_STAGES
    src = S.source(block)
    shard, raw, exp = {}, {}, {}
    for f in D.FACTORS:
        lc = S.lifecycle(src, block, f, horizon=horizon, checkpoints=tuple(c for c in D.CHECKPOINTS if c <= horizon),
                         export=export)
        for k in SHARD_KEYS:
            shard[f"f{f}/{k}"] = lc[k]
        for k in RAW_KEYS:
            raw[f"f{f}/{k}"] = lc[k]
        if export:
            exp[f"f{f}/packets_initial_lineage"] = lc["initial_lineage"]
            exp[f"f{f}/packets_initial_protected"] = lc["initial_protected"]
            exp[f"f{f}/packets_checkpoint"] = lc["ck_packets"]
            exp[f"f{f}/recipient_checkpoint"] = lc["ck_fields"]
            exp[f"f{f}/recipient_protected"] = lc["probe_fields"]
    fm = S.E14.formation_metrics(src)
    shard["formation_qualified"] = np.asarray(fm["qualified"], float)
    shard["formation_pairwise_disagreement"] = np.asarray(fm["pairwise_disagreement"], float)
    for k in ("prototype", "acquired", "background"):
        raw[k] = src[k]
    if export:
        exp["evaluator/prototypes"] = src["prototype"]
        exp["evaluator/prototype_halves"] = src["prototype_halves"]
        exp["labels/lineage_source_founder"] = labels(D.LINEAGE)
        exp["labels/protected_source_founder"] = labels(D.PROBES)
        exp["labels/formation_qualified"] = np.asarray(fm["qualified"], bool)
        exp["ids/block"] = np.array(block, np.int64)
        exp["ids/background_id"] = np.array(block, np.int64)
        exp["ids/stream"] = np.array(block + 1000000, np.int64)
        exp["ids/founder"] = np.arange(4, dtype=np.int64)
        exp["ids/recipient"] = np.arange(2, dtype=np.int64)
        exp["ids/checkpoint"] = np.array([c for c in D.CHECKPOINTS if c <= horizon], np.int64)
    meta = {"study": D.STUDY, "block": block, "stage": stage, "tag": D.STAGE_TAG[stage], "design_digest": D.digest(),
            "factors": D.FACTORS, "horizon": horizon, "checkpoints": [c for c in D.CHECKPOINTS if c <= horizon],
            "lineage": D.LINEAGE, "probes": D.PROBES, "stream": block + 1000000, "numpy": np.__version__,
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
    rec = {"block": block, "stage": stage, "design_digest": D.digest(), "files": files, "finished_utc": utc(),
           "wall_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - c0, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "cpu": os.sched_getaffinity(0).pop() if len(os.sched_getaffinity(0)) == 1 else -1}
    d = root / "done"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{block}.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec
