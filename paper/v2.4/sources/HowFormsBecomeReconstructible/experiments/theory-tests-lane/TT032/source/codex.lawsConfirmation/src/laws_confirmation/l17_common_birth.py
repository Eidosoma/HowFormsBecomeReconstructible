"""Common-birth L17 interventions: bulk state, reference quality and writing.

An outcome-informed one-life factorial at immutable G2/G12 fragment births;
not a new lineage, new-tissue confirmation or a learned reader.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import json
import math
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l17_r_channel as base
from . import l17_r_channel_twelve as chain
from .io import (atomic_json, atomic_text, canonical_digest, environment_manifest,
                 external_root, git_head, sha256_file, utc_now, write_hash_manifest)


RUN_ID = "l17_common_birth_factorial_v1_attempt1"
SOURCE_ID = chain.RUN_ID
TISSUES, CHECKPOINTS, WORKERS = base.TISSUES, (2, 12), 4
CONFIG = base.ExperimentConfig(sample_times=(0, 1, 50, 500, 1000))
CORE_ARMS = tuple(f"{body}_{reference}_{writer}" for body in ("native", "centered")
                  for reference in ("current", "ancestor") for writer in ("live", "held"))
ARMS = (*CORE_ARMS, "centered_wrong_held", "centered_ancestor_off", "centered_current_off")
REPLAY_ARM = "centered_ancestor_held"
REGISTERED_LIVES = len(TISSUES) * len(CHECKPOINTS) * 4 * CONFIG.replicates * len(ARMS)
REPLAY_LIVES = len(TISSUES) * len(CHECKPOINTS) * 4 * CONFIG.replicates


def source_directory(root: Path, tissue: int, generation: int) -> Path:
    return root / "outputs" / SOURCE_ID / f"tissue_{tissue}" / f"g{generation:02d}"


def load_common(root: Path, context: dict, generation: int) -> dict:
    if generation not in CHECKPOINTS:
        raise ValueError("unregistered checkpoint")
    old = source_directory(root, context["index"], generation - 1)
    now = source_directory(root, context["index"], generation)
    previous = chain.load_arrays(old / "fragment_renew_states.npz")
    parent = {k: previous[f"s1000_{k}"] for k in ("V", "ema", "R")}
    ancestor = chain.parent_input(root, context)
    v, fresh = chain.fission(context, parent, generation)
    initial = {"V": v, "ema": v.copy(), "R": parent["R"].copy()}
    anchor = chain.load_arrays(now / "fragment_renew_states.npz")
    growth = chain.load_arrays(now / "regrowth.npz")
    if (not all(np.array_equal(initial[k], anchor[f"s0_{k}"]) for k in initial)
            or not np.array_equal(fresh, growth["fresh"])):
        raise RuntimeError("native common birth does not reconstruct immutable source")
    return {"parent": parent, "ancestor": ancestor, "initial": initial,
            "fresh": fresh, "counts": growth["counts"], "anchor": anchor}


def centered_body(value: np.ndarray) -> np.ndarray:
    """Uniform offset only; no target pattern, reference, clipping or decoder."""
    return value - value.mean(axis=(-2, -1), keepdims=True)


def branches(initial: dict, ancestor: dict, replicates: int) -> dict:
    states = {}
    for arm in ARMS:
        body, reference, _ = arm.split("_")
        v = initial["V"].copy() if body == "native" else centered_body(initial["V"])
        if reference == "current":
            r = initial["R"].copy()
        elif reference == "ancestor":
            r = ancestor["R"].copy()
        else:
            r = chain.permute_message(ancestor["R"], replicates)
        states[arm] = {"V": v, "ema": v.copy(), "R": r}
    return states


def branch_measurements(context: dict, trajectory: dict, common: dict) -> list[dict]:
    rows = chain.measurements(context, trajectory, common["ancestor"], common["parent"], common["fresh"], common["counts"])
    for row in rows:
        index = row["message"] * context["config"].replicates + row["replicate"]
        v = trajectory["snapshots"][row["sweep"]]["V"][index]
        row["body_min"], row["body_max"] = float(v.min()), float(v.max())
    return rows


def summarize(rows: list[dict]) -> dict:
    result = chain.summaries(rows)
    for t, summary in result.items():
        selected = [r for r in rows if r["sweep"] == int(t)]
        for key in ("body_mean", "body_rms", "body_min", "body_max", "positive_fraction", "reference_mean"):
            summary[key] = float(np.mean([r[key] for r in selected]))
    return result


def experiment(context: dict, common: dict, generation: int) -> tuple[dict, dict]:
    cfg = context["config"]
    source_hashes = {k: base.state_digest(common[k]) for k in ("initial", "parent", "ancestor")}
    mask_hashes = {k: base.array_digest(common[k]) for k in ("fresh", "counts")}
    states = branches(common["initial"], common["ancestor"], cfg.replicates)
    hashes = {a: base.state_digest(s) for a, s in states.items()}
    trajectories = {}
    for arm in ARMS:
        writer = arm.split("_")[-1]
        trajectories[arm] = base.simulate(context, states[arm], chain.phase(generation, "child_development"),
            cfg.child_sweeps, sample_times=cfg.sample_times, rho=None if writer == "live" else 0.,
            c_m=0. if writer == "off" else None)
    replay = base.simulate(context, states[REPLAY_ARM], chain.phase(generation, "child_development"),
                           cfg.child_sweeps, sample_times=cfg.sample_times, rho=0.)
    rows = {a: branch_measurements(context, tr, common) for a, tr in trajectories.items()}
    summaries = {a: summarize(r) for a, r in rows.items()}
    centered = states[REPLAY_ARM]["V"]
    shape_error = float(np.max(np.abs(centered_body(centered) - centered_body(common["initial"]["V"]))))
    reference_links = {}
    for a, state in states.items():
        reference = a.split("_")[1]
        expected = (common["initial"]["R"] if reference == "current" else common["ancestor"]["R"]
                    if reference == "ancestor" else chain.permute_message(common["ancestor"]["R"], cfg.replicates))
        reference_links[a] = {"source": reference, "expected_sha256": base.array_digest(expected), "birth_sha256": base.array_digest(state["R"])}
    anchor = common.get("anchor")
    gates = {
        "common_sources_unchanged": source_hashes == {k: base.state_digest(common[k]) for k in source_hashes},
        "regrowth_unchanged": mask_hashes == {k: base.array_digest(common[k]) for k in mask_hashes},
        "birth_states_unchanged": hashes == {a: base.state_digest(s) for a, s in states.items()},
        "finite_birth_states": all(np.isfinite(v).all() for s in states.values() for v in s.values()),
        "native_birth_exact": all(np.array_equal(states["native_current_live"][k], common["initial"][k]) for k in ("V", "ema", "R")),
        "bodies_match_within_factor": all(np.array_equal(s[k], states[f"{a.split('_')[0]}_current_live"][k]) for a, s in states.items() for k in ("V", "ema")),
        "birth_ema_equals_body": all(np.array_equal(s["V"], s["ema"]) for s in states.values()),
        "centered_mean_zero": bool(np.max(np.abs(centered.mean(axis=(-2, -1)))) < 1e-14),
        "centered_spatial_shape_preserved": shape_error < 1e-14,
        "reference_links_exact": all(v["expected_sha256"] == v["birth_sha256"] for v in reference_links.values()),
        "held_references_exact": all(np.array_equal(s["R"], states[a]["R"]) for a, tr in trajectories.items() if not a.endswith("live") for s in tr["snapshots"].values()),
        "streams_exact": all(len({tr[k] for tr in trajectories.values()}) == 1 for k in ("rng_initial_sha256", "rng_final_sha256")),
        "reader_off_body_alias": all(np.array_equal(trajectories["centered_ancestor_off"]["snapshots"][t][k], trajectories["centered_current_off"]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema")),
        "wrong_original_reference_bijection": np.array_equal(np.sort(states["centered_wrong_held"]["R"].ravel()), np.sort(common["ancestor"]["R"].ravel())),
        "new_arm_exact_replay": base.trajectory_digest(trajectories[REPLAY_ARM]) == base.trajectory_digest(replay),
        "historical_anchor_exact": anchor is None or all(np.array_equal(v, anchor[f"s{t}_{k}"]) for t, s in trajectories["native_current_live"]["snapshots"].items() for k, v in s.items() if f"s{t}_{k}" in anchor),
    }
    if not all(gates.values()):
        raise RuntimeError(f"common-birth structural failure: {gates}")
    record = {"tissue": context["index"], "generation": generation, "passes": True, "structural_gates": gates,
              "source_state_sha256": source_hashes, "mask_sha256": mask_hashes, "birth_state_sha256": hashes,
              "reference_links": reference_links, "centered_shape_max_error": shape_error,
              "trajectory_sha256": {a: base.trajectory_digest(tr) for a, tr in trajectories.items()},
              "rng_initial_sha256": trajectories[REPLAY_ARM]["rng_initial_sha256"],
              "rng_final_sha256": trajectories[REPLAY_ARM]["rng_final_sha256"], "summaries": summaries, "rows": rows}
    return record, trajectories


def classify(results: list[dict], structural=True) -> dict:
    expected = [(t, g) for t in TISSUES for g in CHECKPOINTS]
    if not structural or sorted((r["tissue"], r["generation"]) for r in results) != expected or not all(r["passes"] for r in results):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    final = [r["summaries"] for r in sorted(results, key=lambda r: r["tissue"]) if r["generation"] == 12]
    pairs = (("body_compatibility", "centered_ancestor_held", "native_ancestor_held"),
             ("reference_quality", "centered_ancestor_held", "centered_current_held"))
    contrasts = {name: chain.contrast([s[left][str(CONFIG.child_sweeps)]["body_accuracy"] - s[right][str(CONFIG.child_sweeps)]["body_accuracy"] for s in final], 20260907170301 + n)
                 for n, (name, left, right) in enumerate(pairs)}
    supported = tuple(contrasts[k]["supported"] for k, _, _ in pairs)
    label = {(True, True): "BODY_AND_REFERENCE_LIMITATIONS", (True, False): "BODY_LIMITATION_ONLY",
             (False, True): "REFERENCE_LIMITATION_ONLY", (False, False): "NO_QUALIFIED_COMMON_BIRTH_LEAD"}[supported]
    return {"label": label, "co_primary_G12": contrasts}


def retained_diagnostics(root: Path) -> dict:
    """Retrospective measurements, never an available input to any branch."""
    codes, labels = base.codebook(), base.labels(8)
    index = np.arange(32)
    alpha = (1 - .002)**1000
    rows = []
    for tissue in TISSUES:
        for generation in range(1, 13):
            directory = source_directory(root, tissue, generation)
            for arm in ("fresh_renew", "fresh_reader_off", "fragment_renew", "fragment_reset", "fragment_ancestor_rescue"):
                raw = chain.load_arrays(directory / f"{arm}_states.npz")
                reference, birth_r = raw["s1000_R"], raw["s0_R"]
                grouped = reference.reshape(4, 8, 16, 16)
                residual = (grouped - grouped.mean(axis=0, keepdims=True)).reshape(32, 16, 16)
                scores, probabilities = base.decode(reference, codes)
                residual_scores, residual_probabilities = base.decode(residual, codes)
                birth_scores, _ = base.decode(birth_r, codes)
                rows.append({"tissue": tissue, "generation": generation, "arm": arm,
                    "birth_body_mean": float(raw["s0_V"].mean()), "final_body_mean": float(raw["s1000_V"].mean()),
                    "final_positive_fraction": float((raw["s1000_V"] > 0).mean()),
                    "raw_reference_accuracy": float(probabilities[index, labels].mean()),
                    "oracle_centered_reference_accuracy": float(residual_probabilities[index, labels].mean()),
                    "oracle_residual_rms": float(np.sqrt(np.mean(residual**2))),
                    "reference_rms": float(np.sqrt(np.mean(reference**2))),
                    "birth_true_projection": float(birth_scores[index, labels].mean()),
                    "final_true_projection": float(scores[index, labels].mean()),
                    "direct_carry_projection": float(alpha * birth_scores[index, labels].mean()),
                    "implied_body_history_projection": float(((scores - alpha * birth_scores) / (1 - alpha))[index, labels].mean())})
    return {"retrospective": True, "oracle_not_available_to_descendant": True, "new_simulations": 0,
            "direct_R_coefficient_per_1000_sweeps": alpha, "direct_R_coefficient_per_12000_sweeps": (1-.002)**12000,
            "body_history_is_algebraically_implied_not_independent_step_measurement": True, "rows": rows}


def qualify_source(root: Path) -> dict:
    run = root / "runs" / SOURCE_ID
    source = root / "outputs" / SOURCE_ID
    audit = root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1"
    status = json.loads((run / "STATUS.json").read_text())
    result = json.loads((audit / "rescore.json").read_text())
    maps = [chain.manifest_hashes(directory / name) for directory in (source, audit) for name in ("input_hashes.sha256", "output_hashes.sha256")]
    gates = {"source_complete": status["status"] == "COMPLETE" and status["completed_cleanly"] and (run / "COMPLETE").is_file() and not (run / "FAILED").exists(),
             "instrument_qualified": status["instrument_qualified"], "full_independent_audit_passed": result["passes"],
             "all_source_and_audit_hashes_verify": all(base.verify_hashes(h) for h in maps)}
    if not all(gates.values()):
        raise RuntimeError(f"source qualification failed: {gates}")
    return {"passes": True, "gates": gates, "unique_hashed_files": len(set().union(*(set(h) for h in maps)))}


def input_paths(root: Path) -> list[Path]:
    workspace = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), workspace / "scripts/run_l17_common_birth.sh", workspace / "tests/test_l17_common_birth.py",
             workspace / "scripts/audit_l17_common_birth_outputs.py", workspace / "protocols/L17_COMMON_BIRTH_FACTORIAL_V1.md",
             workspace / "reviews/L17_R_CHANNEL_TWELVE_BOUNDARY_2026-09-07.md"]
    for directory in (root / "outputs" / SOURCE_ID, root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1"):
        for name in ("input_hashes.sha256", "output_hashes.sha256"):
            path = directory / name
            paths.append(path)
            paths.extend(Path(p) for p in chain.manifest_hashes(path))
    paths.extend(root / "runs" / SOURCE_ID / name for name in ("STATUS.json", "COMPLETE", "MANIFEST.json"))
    return sorted(set(paths))


def disk_preflight(root: Path) -> dict:
    free = shutil.disk_usage(root).free
    return {"free_bytes": free, "estimated_output_bytes": 512 * 1024**2, "safety_margin_bytes": 1024**3,
            "passes": free >= 512 * 1024**2 + 1024**3}


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("cannot alter prepared benchmark")
    runtime, source = base.runtime(), qualify_source(root)
    if not runtime["passes"] or not disk_preflight(root)["passes"]:
        raise RuntimeError("runtime/storage preflight")
    cfg = replace(CONFIG, replicates=2, settle_sweeps=8, imprint_sweeps=32, render_sweeps=32,
                  child_sweeps=32, sample_times=(0, 1, 8, 16, 32))
    context = base.make_context(20022, cfg)
    parent = base.teach_parent(context)["after_render"]
    v, fresh = chain.fission(context, parent, 2)
    common = {"parent": parent, "ancestor": base.state_copy(parent), "initial": {"V": v, "ema": v.copy(), "R": parent["R"].copy()},
              "fresh": fresh, "counts": fresh.astype(np.int32)}
    start = time.monotonic()
    result, _ = experiment(context, common, 2)
    elapsed = time.monotonic() - start
    projection = elapsed * (CONFIG.replicates / cfg.replicates) * (CONFIG.child_sweeps / cfg.child_sweeps) * math.ceil(len(TISSUES) * len(CHECKPOINTS) / WORKERS) * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "effect_sizes_not_reported": True,
              "disposable_tissue": 20022, "runtime": runtime, "source_qualification": source, "config": asdict(cfg),
              "branch_seconds": elapsed, "projected_seconds_four_workers": projection, "safety_multiplier": 1.75,
              "must_detach": projection > 600, "all_structural_gates_pass": result["passes"],
              "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
    atomic_json(benchmark_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root: Path) -> dict:
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("refusing immutable existing target")
    timing = json.loads(benchmark_path(root).read_text())
    runtime, source, disk = base.runtime(), qualify_source(root), disk_preflight(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    if not (timing["all_structural_gates_pass"] and timing["input_sha256"] == hashes and runtime["passes"] and disk["passes"]):
        raise RuntimeError("changed source/benchmark or failed runtime/storage preflight")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    manifest = {"run_id": RUN_ID, "prepared_utc": utc_now(), "config": asdict(CONFIG), "tissues": list(TISSUES),
                "checkpoints": list(CHECKPOINTS), "arms": list(ARMS), "workers": WORKERS, "registered_lives": REGISTERED_LIVES,
                "replay_lives": REPLAY_LIVES, "input_sha256": hashes, "contract_digest": canonical_digest(hashes),
                "benchmark": timing, "runtime": runtime, "source_qualification": source, "disk_preflight": disk,
                "environment": environment_manifest(), "repository_head": git_head(Path(__file__).resolve().parents[2]), "law_verdict_changes": 0}
    atomic_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], output / "input_hashes.sha256", root)
    atomic_json(run / "STATUS.json", {"status": "PREPARED", "run_id": RUN_ID, "updated_utc": utc_now()}, root)
    return manifest


def verify_prepared(root: Path) -> dict:
    run = root / "runs" / RUN_ID
    manifest = json.loads((run / "MANIFEST.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    if (status["status"] != "PREPARED" or manifest["run_id"] != RUN_ID
            or not base.verify_hashes(manifest["input_sha256"])
            or manifest["contract_digest"] != canonical_digest(manifest["input_sha256"])
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths(root) + [benchmark_path(root)]}
            or canonical_digest(manifest["config"]) != canonical_digest(asdict(CONFIG))
            or manifest["tissues"] != list(TISSUES) or manifest["checkpoints"] != list(CHECKPOINTS)
            or manifest["arms"] != list(ARMS) or manifest["workers"] != WORKERS
            or (run / "COMPLETE").exists() or (run / "FAILED").exists()):
        raise RuntimeError("not uniquely prepared or frozen contract changed")
    return manifest


def launch_detached(root: Path) -> dict:
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest = verify_prepared(root)
    run = root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l17_common_birth", "--external-root", str(root), "--run"]
    with stdout.open("xb") as out_handle, stderr.open("xb") as err_handle:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                                   stdout=out_handle, stderr=err_handle, start_new_session=True)
    record = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(), "command": command,
              "stdout_log": str(stdout), "stderr_log": str(stderr), "status": str(run / "STATUS.json"),
              "complete": str(run / "COMPLETE"), "failed": str(run / "FAILED"),
              "estimated_seconds": manifest["benchmark"]["projected_seconds_four_workers"], "polling_owner": "user"}
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    atomic_json(run / "LAUNCH.json", record, root)
    print(json.dumps(record, indent=2), flush=True)
    return record  # No poll/wait/status inspection.


def worker(tissue: int, generation: int, root_text: str) -> dict:
    root = external_root(root_text)
    if not base.runtime()["passes"]:
        raise RuntimeError("worker runtime gate")
    context = base.make_context(tissue, CONFIG)
    common = load_common(root, context, generation)
    result, trajectories = experiment(context, common, generation)
    output = root / "outputs" / RUN_ID / f"tissue_{tissue}" / f"g{generation:02d}"
    base.atomic_npz(output / "common.npz", {**{f"{name}_{k}": v for name in ("initial", "parent", "ancestor") for k, v in common[name].items()},
                                          "fresh": common["fresh"], "counts": common["counts"], "codes": context["codes"], "theta": context["theta"]}, root)
    for arm, tr in trajectories.items():
        base.atomic_npz(output / f"{arm}_states.npz", base.trajectory_arrays(tr), root)
    atomic_json(output / "branches.json", result, root)
    print(f"tissue {tissue}, G{generation} common-birth branches complete", flush=True)
    return {k: v for k, v in result.items() if k != "rows"}


def report(study: dict) -> str:
    lines = ["# L17 common-birth factorial", "", f"Run: `{RUN_ID}`.", "", f"Result: `{study['classification']['label']}`.", "",
             "One-life branches of the same saved births; external original-R rescue and held writing are not renewal.", "",
             "| Arm | G2 body | G12 body | G12 R | G12 mean V |", "|---|---:|---:|---:|---:|"]
    for arm in ARMS:
        means = []
        for generation, key in ((2, "body_accuracy"), (12, "body_accuracy"), (12, "reference_accuracy"), (12, "body_mean")):
            means.append(np.mean([r["summaries"][arm][str(CONFIG.child_sweeps)][key] for r in study["results"] if r["generation"] == generation]))
        lines.append(f"| {arm} | " + " | ".join(f"{v:.6f}" for v in means) + " |")
    lines += ["", "No automatic numbered-law verdict changes. Retrospective oracle centering is not a descendant reader.", ""]
    return "\n".join(lines)


def run_study(root: Path) -> int:
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required for estimate above ten minutes")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        runtime, source = base.runtime(), qualify_source(root)
        if not runtime["passes"] or not disk_preflight(root)["passes"]:
            raise RuntimeError("run runtime/storage gate")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        atomic_json(run / "STATUS.json", {"status": "RUNNING", "phase": "retained_diagnostics", "updated_utc": utc_now()}, root)
        atomic_json(output / "retained_diagnostics.json", retained_diagnostics(root), root)
        collected = []
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as executor:
            futures = [executor.submit(worker, tissue, generation, str(root)) for tissue in TISSUES for generation in CHECKPOINTS]
            for future in as_completed(futures):
                collected.append(future.result())
                atomic_json(run / "STATUS.json", {"status": "RUNNING", "phase": "branches", "completed_cells": len(collected), "total_cells": 16, "updated_utc": utc_now()}, root)
        collected.sort(key=lambda r: (r["tissue"], r["generation"]))
        gates = {"runtime": runtime["passes"], "source_qualification": source["passes"],
                 "all_cells_present": [(r["tissue"], r["generation"]) for r in collected] == [(t, g) for t in TISSUES for g in CHECKPOINTS],
                 "all_structural_gates": all(r["passes"] and all(r["structural_gates"].values()) for r in collected),
                 "input_hashes_unchanged": base.verify_hashes(manifest["input_sha256"])}
        classification = classify(collected, all(gates.values()))
        study = {"run_id": RUN_ID, "generated_utc": utc_now(), "config": asdict(CONFIG), "runtime": runtime,
                 "results": collected, "classification": classification, "completion_gates": gates, "completed_cleanly": all(gates.values()),
                 "child_lives": REGISTERED_LIVES, "replay_lives": REPLAY_LIVES, "elapsed_seconds": time.monotonic() - start, "law_verdict_changes": 0}
        atomic_json(output / "common_birth.json", study, root)
        atomic_text(output / "audit.md", report(study), root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"), output / "output_hashes.sha256", root)
        hashes_pass = base.verify_hashes(chain.manifest_hashes(output / "output_hashes.sha256"))
        success = study["completed_cleanly"] and hashes_pass
        status = {"run_id": RUN_ID, "status": "COMPLETE" if success else "FAILED_GATES", "completed_cleanly": success,
                  "classification": classification["label"], "completed_utc": utc_now(), "elapsed_seconds": time.monotonic() - start,
                  "workers": WORKERS, "cpu_affinity": runtime["cpu_affinity"], "child_lives": REGISTERED_LIVES,
                  "replay_lives": REPLAY_LIVES, "output_manifest_self_verifies": hashes_pass}
        atomic_json(run / "STATUS.json", status, root)
        atomic_text(run / ("COMPLETE" if success else "FAILED"), status["completed_utc"] + "\n", root)
        print(json.dumps(status, indent=2), flush=True)
        return 0 if success else 1
    except Exception as error:
        failure = {"status": "FAILED", "run_id": RUN_ID, "failed_utc": utc_now(), "error": str(error), "traceback": traceback.format_exc()}
        atomic_json(run / "STATUS.json", failure, root)
        atomic_text(run / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for option in ("benchmark", "prepare", "detach", "run"):
        group.add_argument(f"--{option}", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        m = prepare(root)
        print(json.dumps({"status": "PREPARED", "input_files": len(m["input_sha256"]), "estimated_seconds": m["benchmark"]["projected_seconds_four_workers"]}, indent=2))
    elif args.detach:
        launch_detached(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
