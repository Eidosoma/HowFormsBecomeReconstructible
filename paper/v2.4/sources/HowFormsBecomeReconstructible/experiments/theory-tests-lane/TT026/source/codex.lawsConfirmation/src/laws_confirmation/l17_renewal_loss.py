"""Retained-array decomposition of message, background and temporal renewal loss."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from .io import (atomic_json, atomic_text, canonical_digest, environment_manifest,
                 external_root, sha256_file, utc_now, write_hash_manifest)


RUN_ID = "l17_renewal_loss_audit_v1_attempt1"
SOURCE_ID = "l17_replacement_chain_v1_attempt1"
SOURCE_AUDIT_ID = SOURCE_ID + "_independent_rescore_v1"
TISSUES, GENERATIONS, REPLICATES, SWEEPS, WORKERS = tuple(range(10000, 10008)), tuple(range(1, 13)), 8, 1000, 4
ARMS = ("split_replace", "split_reset", "split_wrong", "split_off", "reset_off", "coupled_replace", "native_carry", "native_reset", "protected_copy")
BASELINES = {a: "reset_off" if a in ("split_off", "reset_off") else
             "native_reset" if a in ("coupled_replace", "native_carry", "native_reset") else "split_reset" for a in ARMS}
FIELDS = {"incoming_R": "s0_R", "body_50": "s50_V", "body_1000": "s1000_V", "candidate_50": "s50_Q", "candidate_1000": "s1000_Q"}
TRANSFERS = {"input_to_body": ("s0_R", "s1000_V"), "input_to_candidate": ("s0_R", "s1000_Q"), "body_to_candidate": ("s1000_V", "s1000_Q")}
BANDS = ((1, 50), (51, 250), (251, 500), (501, 1000))
LATE = (751, 1000)
RHO = .002


def templates() -> np.ndarray:
    first = np.broadcast_to(np.where((np.arange(16)//4) % 2 == 0, 1., -1.), (16, 16))
    return np.stack([np.roll(first, shift, axis=1) for shift in (0, 2, 4, 6)])


def arrays(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as saved:
        return {k: saved[k].copy() for k in saved.files}


def scores(field: np.ndarray, codes: np.ndarray) -> np.ndarray:
    return field.reshape(len(field), -1) @ codes.reshape(4, -1).T / codes[0].size


def summarize(rows: list[dict]) -> dict:
    keys = set(rows[0]) - {"replicate", "world", "message", "competitor"}
    means, counts = {}, {}
    for key in sorted(keys):
        values = [r[key] for r in rows if r[key] is not None]
        means[key] = float(np.mean(values)) if values else None
        counts[key] = len(values)
    return means | {"valid_counts": counts}


def contrast_parts(field: np.ndarray, replicates: int) -> tuple[np.ndarray, np.ndarray]:
    if field.shape != (4*replicates, 16, 16) or not np.isfinite(field).all():
        raise ValueError("expected finite four-message full fields")
    grouped = field.reshape(4, replicates, 16, 16)
    common = grouped[0] + (grouped-grouped[0]).mean(axis=0)
    contrast = grouped-common
    np.testing.assert_allclose(common+contrast, grouped, rtol=0., atol=1e-12)
    np.testing.assert_allclose(contrast.mean(axis=0), 0., rtol=0., atol=1e-12)
    np.testing.assert_allclose((grouped**2).mean(axis=(0,2,3)), (common**2).mean(axis=(1,2))+(contrast**2).mean(axis=(0,2,3)), rtol=0., atol=1e-12)
    return common, contrast


def decoder_metrics(projected: np.ndarray, replicates: int) -> dict:
    labels, indices = np.repeat(np.arange(4), replicates), np.arange(4*replicates)
    ties = np.isclose(projected, projected.max(axis=1, keepdims=True), rtol=0., atol=1e-12)
    probabilities = ties/ties.sum(axis=1, keepdims=True)
    wrong = projected.copy()
    wrong[indices, labels] = -np.inf
    return {"accuracy": probabilities[indices, labels].reshape(4, replicates).mean(axis=0),
            "true_projection": projected[indices, labels].reshape(4, replicates).mean(axis=0),
            "margin": (projected[indices, labels]-wrong.max(axis=1)).reshape(4, replicates).mean(axis=0)}


def field_metrics(field: np.ndarray, codes: np.ndarray, replicates: int) -> dict:
    common, contrast = contrast_parts(field, replicates)
    raw = decoder_metrics(scores(field, codes), replicates)
    oracle = decoder_metrics(scores(contrast.reshape(field.shape), codes), replicates)
    energy = (field.reshape(4, replicates, 16, 16)**2).mean(axis=(0,2,3))
    common_energy = (common**2).mean(axis=(1,2))
    contrast_energy = (contrast**2).mean(axis=(0,2,3))
    rows = [{"replicate": r, "field_rms": float(np.sqrt(energy[r])), "field_mean": float(common[r].mean()),
             "common_rms": float(np.sqrt(common_energy[r])), "message_rms": float(np.sqrt(contrast_energy[r])),
             "message_energy_fraction": float(contrast_energy[r]/energy[r]) if energy[r] else None,
             **{f"raw_{k}": float(v[r]) for k,v in raw.items()},
             **{f"oracle_centered_{k}": float(v[r]) for k,v in oracle.items()}} for r in range(replicates)]
    return {"per_replicate": rows, "mean": summarize(rows)}


def transfer_metrics(incoming: np.ndarray, outgoing: np.ndarray, replicates: int) -> dict:
    x = contrast_parts(incoming, replicates)[1].transpose(1,0,2,3).reshape(replicates,-1)
    y = contrast_parts(outgoing, replicates)[1].transpose(1,0,2,3).reshape(replicates,-1)
    rows = []
    for r in range(replicates):
        xx, yy, xy = float(np.mean(x[r]**2)), float(np.mean(y[r]**2)), float(np.mean(x[r]*y[r]))
        gain = xy/xx if xx else None
        residual = y[r]-gain*x[r] if gain is not None else y[r]
        residual_energy = float(np.mean(residual**2))
        if gain is not None:
            np.testing.assert_allclose(yy, gain*gain*xx+residual_energy, rtol=0., atol=1e-12)
            np.testing.assert_allclose(np.mean(x[r]*residual), 0., rtol=0., atol=1e-12)
        rows.append({"replicate": r, "input_message_rms": math.sqrt(xx), "output_message_rms": math.sqrt(yy),
                     "aligned_gain": gain, "cosine": xy/math.sqrt(xx*yy) if xx and yy else None,
                     "residual_rms": math.sqrt(residual_energy), "residual_energy_fraction": residual_energy/yy if yy else None})
    return {"per_replicate": rows, "mean": summarize(rows)}


def background_metrics(field: np.ndarray, reset: np.ndarray, replicates: int) -> dict:
    common, contrast = contrast_parts(field, replicates)
    reset_common, reset_contrast = contrast_parts(reset, replicates)
    if np.any(reset_contrast != 0.):
        raise ValueError("matched reset contains message contrast")
    grouped = field.reshape(4, replicates, 16, 16)
    rows = []
    for r in range(replicates):
        bb, zz = float(np.mean(common[r]**2)), float(np.mean(reset_common[r]**2))
        delta = float(np.mean((common[r]-reset_common[r])**2))
        whole = float(np.mean((grouped[:,r]-reset_common[r])**2))
        np.testing.assert_allclose(whole, delta+np.mean(contrast[:,r]**2), rtol=0., atol=1e-12)
        rows.append({"replicate": r, "reset_rms": math.sqrt(zz), "common_minus_reset_rms": math.sqrt(delta),
                     "whole_minus_reset_rms": math.sqrt(whole),
                     "common_reset_cosine": float(np.mean(common[r]*reset_common[r]))/math.sqrt(bb*zz) if bb and zz else None})
    return {"per_replicate": rows, "mean": summarize(rows)}


def writer_metrics(trace: np.ndarray, incoming: np.ndarray, candidate: np.ndarray, codes: np.ndarray,
                   replicates: int, bands=BANDS, late=LATE, rho=RHO) -> dict:
    sweeps = len(trace)-1
    if trace.shape != (sweeps+1, 4*replicates, 4) or not np.isfinite(trace).all():
        raise ValueError("invalid writer trace")
    if [s for lo,hi in bands for s in range(lo,hi+1)] != list(range(1,sweeps+1)) or not 1 <= late[0] <= late[1] <= sweeps:
        raise ValueError("bands must partition every post-step write exactly once")
    weights = rho*(1-rho)**np.arange(sweeps-1,-1,-1)
    weight_sum = float(weights.sum())
    np.testing.assert_allclose(weight_sum, 1-(1-rho)**sweeps, rtol=0., atol=1e-12)
    integrated = np.einsum("t,twk->wk", weights, trace[1:])
    recursive = np.zeros_like(trace[0])
    for body in trace[1:]:
        recursive = (1-rho)*recursive + rho*body
    actual = scores(candidate, codes)
    np.testing.assert_allclose(integrated, recursive, rtol=0., atol=1e-12)
    np.testing.assert_allclose(integrated, actual, rtol=0., atol=1e-12)
    labels, indices = np.repeat(np.arange(4), replicates), np.arange(4*replicates)
    wrong = actual.copy()
    wrong[indices,labels] = -np.inf
    competitors = wrong.argmax(axis=1)  # Fixed final wrong competitor; not instantaneous maxima.
    actual_margin = actual[indices,labels]-actual[indices,competitors]
    band_records, summed_margin = [], np.zeros(4*replicates)
    for lo,hi in bands:
        projected = np.einsum("t,twk->wk", weights[lo-1:hi], trace[lo:hi+1])
        margin = projected[indices,labels]-projected[indices,competitors]
        summed_margin += margin
        rows = [{"world": int(i), "message": int(labels[i]), "replicate": int(i % replicates),
                 "competitor": int(competitors[i]), "true_projection_contribution": float(projected[i,labels[i]]),
                 "final_competitor_margin_contribution": float(margin[i])} for i in indices]
        band_records.append({"start": lo, "end": hi, "weight_mass": float(weights[lo-1:hi].sum()),
                             "projection_contributions": projected.tolist(), "per_world": rows, "mean": summarize(rows)})
    np.testing.assert_allclose(summed_margin, actual_margin, rtol=0., atol=1e-12)
    r = scores(incoming,codes)[indices,labels]
    b = trace[late[0]:late[1]+1].mean(axis=0)[indices,labels]
    q = actual[indices,labels]
    rendered, finite_mass, history = r-b, (1-weight_sum)*b, weight_sum*b-q
    np.testing.assert_allclose(r-q, rendered+finite_mass+history, rtol=0., atol=1e-12)
    rows = [{"world": int(i), "message": int(labels[i]), "replicate": int(i % replicates),
             "incoming_true_projection": float(r[i]), "late_body_true_projection": float(b[i]), "candidate_true_projection": float(q[i]),
             "input_to_candidate_change": float(r[i]-q[i]), "input_to_late_body_change": float(rendered[i]),
             "finite_weight_loss": float(finite_mass[i]), "history_vs_late_change": float(history[i]),
             "candidate_margin": float(actual_margin[i])} for i in indices]
    checkpoints = sorted({0, *(hi for _,hi in bands)})
    body = {str(t): {k: float(v.mean()) for k,v in decoder_metrics(trace[t],replicates).items()} for t in checkpoints}
    last = trace[late[0]:late[1]+1]
    late_true = last[:,indices,labels]
    late_wrong = last.copy()
    late_wrong[:,indices,labels] = -np.inf
    late_ties = np.isclose(last,last.max(axis=2,keepdims=True),rtol=0.,atol=1e-12)
    late_probability = late_ties/late_ties.sum(axis=2,keepdims=True)
    late_metrics = {"accuracy":float(late_probability[:,indices,labels].mean()),
                    "true_projection":float(late_true.mean()),"margin":float((late_true-late_wrong.max(axis=2)).mean())}
    return {"total_weight": weight_sum, "bands": band_records, "late_window": list(late), "budget_per_world": rows,
            "budget_mean": summarize(rows), "body_checkpoints": body, "late_body_mean": late_metrics,
            "projection_reconstruction_max_error": float(np.max(abs(integrated-actual)))}


def analyze_arm(raw: dict, baseline: dict, replicates=REPLICATES, bands=BANDS, late=LATE) -> dict:
    codes = templates()
    for sweep in (0, 50, 1000):
        if f"s{sweep}_V" in raw and sweep < len(raw["body_scores"]):
            np.testing.assert_allclose(scores(raw[f"s{sweep}_V"],codes), raw["body_scores"][sweep], rtol=0., atol=1e-12)
    if not np.all(raw["s0_Q"] == 0.):
        raise ValueError("candidate birth not zero")
    fields = {name: field_metrics(raw[key],codes,replicates) for name,key in FIELDS.items()}
    transfers = {name: transfer_metrics(raw[left],raw[right],replicates) for name,(left,right) in TRANSFERS.items()}
    backgrounds = {name: background_metrics(raw[key],baseline[key],replicates) for name,key in FIELDS.items() if name != "incoming_R"}
    writer = writer_metrics(raw["body_scores"],raw["s0_R"],raw["s1000_Q"],codes,replicates,bands,late)
    return {"passes": True, "fields": fields, "transfers": transfers, "backgrounds": backgrounds, "writer": writer}


def analyze_generation(root: Path, tissue: int, generation: int) -> dict:
    directory = root/"outputs"/SOURCE_ID/f"tissue_{tissue}"/f"g{generation:02d}"
    raw = {a: arrays(directory/f"development_{a}.npz") for a in ARMS}
    records = {a: analyze_arm(raw[a],raw[BASELINES[a]]) for a in ARMS}
    return {"tissue": tissue, "generation": generation, "passes": all(r["passes"] for r in records.values()), "arms": records}


def small_summary(record: dict) -> dict:
    return {"fields": {k:v["mean"] for k,v in record["fields"].items()},
            "transfers": {k:v["mean"] for k,v in record["transfers"].items()},
            "backgrounds": {k:v["mean"] for k,v in record["backgrounds"].items()},
            "budget": record["writer"]["budget_mean"], "body_checkpoints": record["writer"]["body_checkpoints"],
            "late_body_mean": record["writer"]["late_body_mean"],
            "bands": {f"{b['start']}-{b['end']}": b["mean"] | {"weight_mass":b["weight_mass"]} for b in record["writer"]["bands"]}}


def pooled_summary(records: list[dict]) -> dict:
    expected = [(t,g) for t in TISSUES for g in GENERATIONS]
    if sorted((r["tissue"],r["generation"]) for r in records) != expected or not all(r["passes"] for r in records):
        raise ValueError("missing, duplicated or failed tissue/generation")
    def average(nodes):
        if isinstance(nodes[0],dict):
            result = {k: average([n[k] for n in nodes]) for k in nodes[0] if k != "valid_counts"}
            counts = {k:sum(n[k] is not None for n in nodes) for k in result if not isinstance(nodes[0][k],dict)}
            return result | ({"valid_tissues":counts} if counts else {})
        valid = [n for n in nodes if n is not None]
        return float(np.mean(valid)) if valid else None
    return {str(g): {a: average([small_summary(r["arms"][a]) for r in records if r["generation"] == g]) for a in ARMS} for g in GENERATIONS}


def read_manifest(path: Path) -> dict:
    return {p:d for d,p in (line.split("  ",1) for line in path.read_text().splitlines())}


def verify_hashes(hashes: dict) -> bool:
    return bool(hashes) and all(Path(p).is_file() and sha256_file(Path(p)) == d for p,d in hashes.items())


def qualify_source(root: Path) -> dict:
    run = root/"runs"/SOURCE_ID
    status = json.loads((run/"STATUS.json").read_text())
    audited = json.loads((root/"outputs"/SOURCE_AUDIT_ID/"rescore.json").read_text())
    counts = {}
    for name in (SOURCE_ID,SOURCE_AUDIT_ID):
        for kind in ("input","output"):
            hashes = read_manifest(root/"outputs"/name/f"{kind}_hashes.sha256")
            if not verify_hashes(hashes):
                raise RuntimeError("source/audit hashes changed")
            counts[f"{name}:{kind}"] = len(hashes)
    if not (status["status"] == "COMPLETE" and status["completed_cleanly"] and (run/"COMPLETE").is_file() and not (run/"FAILED").exists() and audited["passes"]):
        raise RuntimeError("source not complete and independently audited")
    return {"passes": True, "hash_counts": counts, "source_classification": status["classification"]}


def input_paths(root: Path) -> list[Path]:
    ws = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), ws/"protocols/L17_RENEWAL_LOSS_AUDIT_V1.md", ws/"tests/test_l17_renewal_loss.py",
             ws/"scripts/run_l17_renewal_loss.sh", ws/"scripts/audit_l17_renewal_loss_outputs.py", ws/"reviews/L17_REPLACEMENT_CHAIN_2026-09-08.md"]
    for name in (SOURCE_ID,SOURCE_AUDIT_ID):
        for kind in ("input","output"):
            manifest = root/"outputs"/name/f"{kind}_hashes.sha256"
            paths.extend([manifest, *(Path(p) for p in read_manifest(manifest))])
    paths.extend(root/"runs"/SOURCE_ID/n for n in ("STATUS.json","COMPLETE","MANIFEST.json"))
    return sorted(set(paths))


def runtime() -> dict:
    cpus = sorted(os.sched_getaffinity(0))[:4]
    os.sched_setaffinity(0,cpus)
    gates = {"four_cpu_limit": 0 < len(cpus) <= 4, "threads_one": all(os.environ.get(k)=="1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS")),
             "pinned_runtime": platform.python_version_tuple()[:2] == ("3","13") and np.__version__ == "2.5.2"}
    return {"passes": all(gates.values()), "gates": gates, "cpu_affinity": cpus, "workers": WORKERS}


def disk_preflight(root: Path) -> dict:
    free = shutil.disk_usage(root).free
    return {"passes": free >= (1024+128)*1024**2, "free_bytes": free, "output_reserve_bytes": 128*1024**2, "safety_bytes": 1024**3}


def benchmark_path(root: Path) -> Path:
    return root/"tmp"/f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root/"runs"/RUN_ID).exists() or (root/"outputs"/RUN_ID).exists():
        raise FileExistsError("cannot change prepared benchmark")
    rt, qualification = runtime(), qualify_source(root)
    if not rt["passes"] or not disk_preflight(root)["passes"]:
        raise RuntimeError("benchmark runtime/storage gate")
    start = time.monotonic()
    result = analyze_generation(root,10000,1)
    elapsed = time.monotonic()-start
    estimate = elapsed*math.ceil(len(TISSUES)*len(GENERATIONS)/WORKERS)*2+60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "read_only_retained_cell": [10000,1], "new_simulations": 0,
              "effects_not_reported": True, "cell_seconds": elapsed, "projected_seconds": estimate, "must_detach": estimate > 600,
              "passes": result["passes"], "runtime": rt, "source": qualification, "input_sha256": {str(p):sha256_file(p) for p in input_paths(root)}}
    atomic_json(benchmark_path(root),record,root)
    print(json.dumps({k:v for k,v in record.items() if k != "input_sha256"},indent=2),flush=True)
    return record


def contract() -> dict:
    return {"run_id": RUN_ID, "source_id": SOURCE_ID, "tissues": list(TISSUES), "generations": list(GENERATIONS), "arms": list(ARMS),
            "replicates": REPLICATES, "sweeps": SWEEPS, "workers": WORKERS, "bands": BANDS, "late_window": LATE, "rho": RHO,
            "fields": FIELDS, "transfers": TRANSFERS, "baselines": BASELINES, "new_simulations": 0, "law_verdict_changes": 0}


def prepare(root: Path) -> dict:
    run, output = root/"runs"/RUN_ID, root/"outputs"/RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("immutable run/output already exists")
    timing = json.loads(benchmark_path(root).read_text())
    rt, source, disk = runtime(), qualify_source(root), disk_preflight(root)
    hashes = {str(p):sha256_file(p) for p in input_paths(root)}
    if not (timing["passes"] and timing["input_sha256"] == hashes and rt["passes"] and disk["passes"]):
        raise RuntimeError("prepare gates or benchmark contract changed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    manifest = contract() | {"prepared_utc": utc_now(), "benchmark": timing, "runtime": rt, "disk": disk, "source": source,
                            "input_sha256": hashes, "hash_contract": canonical_digest(hashes), "environment": environment_manifest()}
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    atomic_json(run/"MANIFEST.json",manifest,root)
    write_hash_manifest([Path(p) for p in hashes],output/"input_hashes.sha256",root)
    atomic_json(run/"STATUS.json",{"status":"PREPARED","run_id":RUN_ID,"updated_utc":utc_now()},root)
    return manifest


def verify_prepared(root: Path) -> dict:
    run = root/"runs"/RUN_ID
    manifest = json.loads((run/"MANIFEST.json").read_text())
    status = json.loads((run/"STATUS.json").read_text())
    if (status["status"] != "PREPARED" or (run/"COMPLETE").exists() or (run/"FAILED").exists()
            or not verify_hashes(manifest["input_sha256"]) or manifest["hash_contract"] != canonical_digest(manifest["input_sha256"])
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths(root)+[benchmark_path(root)]}
            or any(canonical_digest(manifest.get(k)) != canonical_digest(v) for k,v in contract().items())):
        raise RuntimeError("not uniquely prepared or contract changed")
    return manifest


def launch_detached(root: Path) -> dict:
    if not (root/"runs"/RUN_ID).exists():
        prepare(root)
    manifest, run = verify_prepared(root), root/"runs"/RUN_ID
    (run/"LAUNCH.lock").mkdir()
    stdout, stderr = [root/"logs"/f"{RUN_ID}.{kind}.log" for kind in ("stdout","stderr")]
    command = [sys.executable,"-m","laws_confirmation.l17_renewal_loss","--external-root",str(root),"--run"]
    with stdout.open("xb") as out, stderr.open("xb") as err:
        process = subprocess.Popen(command,cwd=Path(__file__).resolve().parents[2],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    record = {"run_id":RUN_ID,"pid":process.pid,"launched_utc":utc_now(),"command":command,"stdout_log":str(stdout),"stderr_log":str(stderr),
              "status":str(run/"STATUS.json"),"complete":str(run/"COMPLETE"),"failed":str(run/"FAILED"),"estimated_seconds":manifest["benchmark"]["projected_seconds"],"polling_owner":"user"}
    atomic_text(run/"RUN.pid",f"{process.pid}\n",root)
    atomic_json(run/"LAUNCH.json",record,root)
    print(json.dumps(record,indent=2),flush=True)
    return record  # No polling or wait.


def worker(tissue: int, generation: int, root_text: str) -> dict:
    if not runtime()["passes"]:
        raise RuntimeError("worker runtime gate")
    return analyze_generation(external_root(root_text),tissue,generation)


def report(pooled: dict) -> str:
    lines = ["# Retained-data renewal-loss analysis", "", "Outcome-informed decomposition only; zero new simulations. Across-message centering and fitted gains are evaluator-only.", "",
             "| G | Input raw margin | New Q raw margin | Q message RMS | Q common RMS | Q oracle accuracy | Contrast gain | Contrast cosine |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for g in GENERATIONS:
        r = pooled[str(g)]["split_replace"]
        q,t = r["fields"]["candidate_1000"],r["transfers"]["input_to_candidate"]
        values = [r["fields"]["incoming_R"]["raw_margin"],q["raw_margin"],q["message_rms"],q["common_rms"],q["oracle_centered_accuracy"],t["aligned_gain"],t["cosine"]]
        lines.append(f"| {g} | " + " | ".join("undefined" if v is None else f"{v:.6f}" for v in values)+" |")
    lines.extend(["", "## Signed intended-projection budget", "", "| G | Input minus Q | Input minus late body | Finite weight | History versus late body |", "|---|---:|---:|---:|---:|"])
    for g in GENERATIONS:
        b = pooled[str(g)]["split_replace"]["budget"]
        lines.append(f"| {g} | " + " | ".join(f"{b[k]:.6f}" for k in ("input_to_candidate_change","input_to_late_body_change","finite_weight_loss","history_vs_late_change"))+" |")
    return "\n".join(lines+["", "The late window need not be mature; this budget is not a simulated timing intervention. No old endpoint or law verdict changes.", ""])


def run_study(root: Path) -> int:
    manifest = verify_prepared(root)
    run,output = root/"runs"/RUN_ID,root/"outputs"/RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run/"LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required above ten minutes")
    (run/"EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        rt = runtime()
        if not rt["passes"] or not disk_preflight(root)["passes"]:
            raise RuntimeError("run runtime/storage gate")
        atomic_text(run/"RUN.pid",f"{os.getpid()}\n",root)
        atomic_json(run/"STATUS.json",{"status":"RUNNING","completed_cells":0,"updated_utc":utc_now()},root)
        collected = []
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context("spawn")) as pool:
            futures = [pool.submit(worker,t,g,str(root)) for t in TISSUES for g in GENERATIONS]
            for future in as_completed(futures):
                result = future.result()
                collected.append(result)
                atomic_json(output/f"tissue_{result['tissue']}"/f"g{result['generation']:02d}.json",result,root)
                atomic_json(run/"STATUS.json",{"status":"RUNNING","completed_cells":len(collected),"updated_utc":utc_now()},root)
        collected.sort(key=lambda r:(r["tissue"],r["generation"]))
        pooled = pooled_summary(collected)
        if not verify_hashes(manifest["input_sha256"]):
            raise RuntimeError("frozen inputs changed during analysis")
        result = {"run_id":RUN_ID,"completed_cleanly":True,"generated_utc":utc_now(),"source_classification":manifest["source"]["source_classification"],
                  "cell_count":len(collected),"arm_cells":len(collected)*len(ARMS),"new_simulations":0,"law_verdict_changes":0,"pooled":pooled,
                  "per_tissue": [{"tissue":r["tissue"],"generation":r["generation"],"arms":{a:small_summary(r["arms"][a]) for a in ARMS}} for r in collected]}
        atomic_json(output/"loss_analysis.json",result,root)
        atomic_text(output/"audit.md",report(pooled),root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"),output/"output_hashes.sha256",root)
        if not verify_hashes(read_manifest(output/"output_hashes.sha256")):
            raise RuntimeError("output manifest does not verify")
        status = {"status":"COMPLETE","run_id":RUN_ID,"completed_cleanly":True,"completed_utc":utc_now(),"elapsed_seconds":time.monotonic()-start,
                  "cells":len(collected),"arm_cells":len(collected)*len(ARMS),"cpu_affinity":rt["cpu_affinity"],"new_simulations":0,"output_manifest_self_verifies":True}
        atomic_json(run/"STATUS.json",status,root)
        atomic_text(run/"COMPLETE",status["completed_utc"]+"\n",root)
        print(json.dumps(status,indent=2),flush=True)
        return 0
    except Exception as error:
        failure = {"status":"FAILED","run_id":RUN_ID,"failed_utc":utc_now(),"error":str(error),"traceback":traceback.format_exc()}
        atomic_json(run/"STATUS.json",failure,root)
        atomic_text(run/"FAILED",failure["failed_utc"]+"\n",root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root",required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ("benchmark","prepare","run","detach"):
        group.add_argument(f"--{name}",action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        m = prepare(root)
        print(json.dumps({"status":"PREPARED","input_hashes":len(m["input_sha256"]),"estimate_seconds":m["benchmark"]["projected_seconds"]},indent=2))
    elif args.detach:
        launch_detached(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
