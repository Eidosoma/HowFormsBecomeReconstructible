"""One NL003 (unit, block) task: NL002's preparation (nl002.sim.prepare, unchanged), the tissue under every label of the
stage (arm x event) as branches with the arbiter where the arm has one (nl003.sim.run), then the recipients: NL002's
L1-only and coded ones for every label, and a coded recipient gated by the arbiter for the gated labels (the tuning
stage runs no recipients). Writes an endpoint shard, a raw-state shard and a completion record, each atomically.
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


def task(unit, block, stage, tag=None):
    tag = D.STAGE_TAG[stage] if tag is None else tag
    purpose = D.PURPOSE[stage]
    arms, labels = sim.use_stage(stage)
    cases = sim.cases_for(block, purpose)
    timing = {}
    t1 = time.time()
    P = sim.prepare(cases, tag)
    timing["prepare"] = round(time.time() - t1, 3)
    t1 = time.time()
    out, dose, final, _, anc = sim.run(cases, unit, labels, prep=P, tag=tag)
    timing["tissue"] = round(time.time() - t1, 3)
    ends = {f"t/{w}/{e}": v for (w, e), v in out.items()}
    gl = [i for i, (a, _) in enumerate(labels) if arms[a].arb]
    k = len(cases)
    rlabels, gated_r = (), []
    if stage != "tuning":
        rlabels = D.recipient_labels(arms, labels)
        ri = [labels.index(l) for l in rlabels]
        rows = np.concatenate([np.arange(i * k, (i + 1) * k) for i in ri])
        final_r = {x: v[ri] for x, v in final.items()}
        anc_r = {x: v[rows] for x, v in anc.items()}
        t1 = time.time()
        rec, coded, gated, gl2 = sim.successor(cases, final_r, P, rlabels, anc_r, tag=tag)
        gated_r = [rlabels[i] for i in gl2]
        timing["successor"] = round(time.time() - t1, 3)
        ends.update({f"s/{e}": v for e, v in rec.items()})
        ends.update({f"c/{e}": v for e, v in coded.items()})
        ends.update({f"g/{e}": v for e, v in gated.items()})
    ends["dose"] = dose
    ends["ncorrupt"] = P["ncorrupt"].astype(float)
    mk = sim.S2.masks(P["TA"], P["TB"], sim.N1S.event_units(cases, tag))
    ends["n_dreg"] = mk["dreg"].sum((-2, -1)).astype(float)
    ends["n_min_reg"] = mk["min_reg"].sum((-2, -1)).astype(float)
    gk = np.array([[i * len(cases) + j for j in range(len(cases))] for i in gl], int).reshape(-1)
    ends["n_anchor_live0"] = np.array([anc["am"][b].sum() for b in gk], float).reshape(len(gl), len(cases)) \
        if gl else np.zeros((0, len(cases)))
    raw = {"TA": P["TA"].astype(np.int8), "TB": P["TB"].astype(np.int8), "R0": P["R0"].astype(np.float32),
           "RB": P["RB"].astype(np.float32), "V0": P["V0"].astype(np.float32),
           "BgA": np.sign(P["refs"]["own"][0][:, ::D.REGION, ::D.REGION]).astype(np.int8),
           "BgK": np.sign(P["refs"]["copy"][0][:, ::D.REGION, ::D.REGION]).astype(np.int8),
           "BgB": np.sign(P["refs"]["foreign"][0][:, ::D.REGION, ::D.REGION]).astype(np.int8),
           "BgC": np.sign(P["refs"]["corrupt"][0][:, ::D.REGION, ::D.REGION]).astype(np.int8),
           "r": final["r"].astype(np.float32), "H": final["H"].astype(np.int8), "W": final["W"].astype(np.int8)}
    if "V" in final:
        raw["V"] = final["V"].astype(np.float32)
    if gl:
        raw["am"] = anc["am"][gk].reshape(len(gl), len(cases), D.SIDE, D.SIDE).astype(np.int8)
        raw["aval"] = anc["aval"][gk].reshape(len(gl), len(cases), D.SIDE, D.SIDE).astype(np.int8)
    return ends, raw, timing, cases, labels, gl, rlabels, gated_r


def run_task(unit, block, stage, root, tag=None):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, raw, timing, cases, labels, gl, rlabels, gated_r = task(unit, block, stage, tag)
    for arrays in (ends, raw):
        bad = [k for k, v in arrays.items() if np.issubdtype(np.asarray(v).dtype, np.floating)
               and not np.isfinite(np.where(np.isnan(v), 0.0, v)).all()]
        if bad:
            raise FloatingPointError(f"non-finite arrays in {unit} {block}: {bad[:5]}")
    meta = {"study": D.STUDY, "unit": unit, "block": block, "stage": stage, "purpose": D.PURPOSE[stage],
            "tag": D.STAGE_TAG[stage] if tag is None else tag, "design_digest": D.digest(), "nl002_digest": sim.S2.D.digest(),
            "numpy": np.__version__, "timing_s": timing, "labels": [list(x) for x in labels],
            "gated": [labels[i][0] + "/" + labels[i][1] for i in gl], "rlabels": [list(x) for x in rlabels],
            "gated_r": [f"{a}/{e}" for a, e in gated_r], "succ": list(sim.SUCC), "reads": list(D.READS),
            "reads2": list(D.READS2), "rule": D.RULE, "cases": [c.key() for c in cases]}
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
    record = {"unit": unit, "block": block, "stage": stage, "design_digest": D.digest(), "files": out,
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
