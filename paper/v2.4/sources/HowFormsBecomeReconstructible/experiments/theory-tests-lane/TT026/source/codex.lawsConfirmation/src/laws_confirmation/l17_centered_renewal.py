"""Native writing through twelve mean-corrected fragment births, no G0 rescue."""

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

from . import l17_common_birth as common
from . import l17_r_channel as base
from . import l17_r_channel_twelve as chain
from .io import (atomic_json, atomic_text, canonical_digest, environment_manifest,
                 external_root, git_head, sha256_file, utc_now, write_hash_manifest)


RUN_ID = "l17_centered_renewal_v1_attempt1"
SOURCE_ID = common.RUN_ID
TISSUES, WORKERS, CONFIG = base.TISSUES, 4, chain.ChainConfig()
ARMS = tuple(f"{b}_{r}_{w}" for b in ("native", "centered") for r in ("copy", "reset") for w in ("live", "held")) + (
    "centered_copy_off", "centered_reset_off")
ANCHORS = {"native_copy_live": "fragment_renew", "native_reset_live": "fragment_reset"}
REPLAY_ARM = "centered_copy_live"
REGISTERED_LIVES = len(TISSUES) * CONFIG.generations * CONFIG.replicates * 4 * len(ARMS)
REPLAY_LIVES = len(TISSUES) * CONFIG.generations * CONFIG.replicates * 4
QUANTILES = (1 / 120, 119 / 120)
ENDPOINTS = (("body_vs_reset", "body_accuracy", "centered_reset_live"),
             ("body_vs_reader_off", "body_accuracy", "centered_copy_off"),
             ("reference_vs_reset", "reference_accuracy", "centered_reset_live"))


def old_directory(root: Path, tissue: int, generation: int) -> Path:
    return root / "outputs" / chain.RUN_ID / f"tissue_{tissue}" / f"g{generation:02d}"


def reset_reference(context: dict, generation: int, root: Path | None = None) -> np.ndarray:
    if root is None:
        newborn = base.naive_body(context, chain.phase(generation, "fresh_body_birth"))
    else:
        directory = old_directory(root, context["index"], generation)
        newborn = chain.load_arrays(directory / "newborn.npz")
        record = json.loads((directory / "calibration.json").read_text())
        if base.state_digest(newborn) != record["newborn_sha256"]:
            raise RuntimeError("immutable reset-reference body changed")
    reference = newborn["R"]
    if not base.message_independent(reference, context["config"].replicates):
        raise RuntimeError("reset R contains message identity")
    return reference.copy()


def birth(context: dict, parent: dict, reset_r: np.ndarray, generation: int, arm: str) -> tuple[dict, np.ndarray, np.ndarray]:
    """No ancestor argument: R can only come from this parent or naive reset."""
    if arm not in ARMS:
        raise ValueError("unregistered arm")
    body, reference, _ = arm.split("_")
    raw_v, fresh = chain.fission(context, parent, generation)
    v = common.centered_body(raw_v) if body == "centered" else raw_v.copy()
    r = parent["R"] if reference == "copy" else reset_r
    return {"V": v, "ema": v.copy(), "R": r.copy()}, fresh, raw_v


def evolve(context: dict, initial: dict, generation: int, arm: str) -> dict:
    writer = arm.split("_")[-1]
    return base.simulate(context, initial, chain.phase(generation, "child_development"), context["config"].child_sweeps,
                         sample_times=context["config"].sample_times, rho=0. if writer == "held" else None,
                         c_m=0. if writer == "off" else None)


def measurements(context: dict, trajectory: dict, ancestor_v: np.ndarray, parent: dict, fresh, counts) -> list[dict]:
    rows = chain.measurements(context, trajectory, {"V": ancestor_v}, parent, fresh, counts)
    for row in rows:
        i = row["message"] * context["config"].replicates + row["replicate"]
        v = trajectory["snapshots"][row["sweep"]]["V"][i]
        row["body_min"], row["body_max"] = float(v.min()), float(v.max())
    return rows


def anchor_matches(root: Path, context: dict, generation: int, trajectories: dict, fresh, counts) -> bool:
    directory = old_directory(root, context["index"], generation)
    growth = chain.load_arrays(directory / "regrowth.npz")
    if not (np.array_equal(fresh, growth["fresh"]) and np.array_equal(counts, growth["counts"])):
        return False
    for arm, name in ANCHORS.items():
        original = chain.load_arrays(directory / f"{name}_states.npz")
        actual = base.trajectory_arrays(trajectories[arm])
        if set(actual) != set(original) or not all(np.array_equal(actual[k], original[k]) for k in original):
            return False
    return True


def lineage(context: dict, g0: dict, root: Path | None = None, output: Path | None = None) -> dict:
    cfg = context["config"]
    # The only ongoing G0 data used by measurements are V and observer hashes.
    ancestor_v = g0["V"].copy()
    g0_hash = base.state_digest(g0)
    parents = {a: base.state_copy(g0) for a in ARMS}
    replay_parent = base.state_copy(g0)
    held_origin = base.array_digest(g0["R"])
    counts = np.zeros_like(g0["V"], dtype=np.int32)
    records, streams = [], []
    for generation in range(1, cfg.generations + 1):
        reset_r = reset_reference(context, generation, root)
        reset_hash = base.array_digest(reset_r)
        source_hashes = {a: base.state_digest(p) for a, p in parents.items()}
        states, masks, raw_bodies = {}, {}, {}
        for arm in ARMS:
            states[arm], masks[arm], raw_bodies[arm] = birth(context, parents[arm], reset_r, generation, arm)
        fresh = masks[REPLAY_ARM]
        counts += fresh
        birth_hashes = {a: base.state_digest(s) for a, s in states.items()}
        links = {}
        for a in ARMS:
            source = "immediate_parent" if a.split("_")[1] == "copy" else "naive_reset"
            expected = parents[a]["R"] if source == "immediate_parent" else reset_r
            links[a] = {"source": source, "expected_sha256": base.array_digest(expected), "birth_sha256": base.array_digest(states[a]["R"])}
        trajectories = {a: evolve(context, states[a], generation, a) for a in ARMS}
        replay_birth, replay_mask, replay_raw = birth(context, replay_parent, reset_r, generation, REPLAY_ARM)
        replay = evolve(context, replay_birth, generation, REPLAY_ARM)
        rows = {a: measurements(context, tr, ancestor_v, parents[a], fresh, counts) for a, tr in trajectories.items()}
        summaries = {a: common.summarize(r) for a, r in rows.items()}
        corrections = {a: {"raw_means": raw.mean(axis=(1, 2)).tolist(), "raw_mins": raw.min(axis=(1, 2)).tolist(),
                           "raw_maxs": raw.max(axis=(1, 2)).tolist(),
                           "birth_means": states[a]["V"].mean(axis=(1, 2)).tolist(),
                           "centered_shape_max_error": float(np.max(np.abs(common.centered_body(states[a]["V"]) - common.centered_body(raw))))}
                       for a, raw in raw_bodies.items()}
        changed = {a: not np.array_equal(states[a]["R"], tr["final"]["R"]) for a, tr in trajectories.items()}
        streams.append(trajectories[REPLAY_ARM]["rng_initial_sha256"])
        gates = {
            "g0_unchanged": base.state_digest(g0) == g0_hash,
            "parents_unchanged": source_hashes == {a: base.state_digest(p) for a, p in parents.items()},
            "reset_unchanged_and_message_independent": base.array_digest(reset_r) == reset_hash and base.message_independent(reset_r, cfg.replicates),
            "birth_states_unchanged": birth_hashes == {a: base.state_digest(s) for a, s in states.items()},
            "finite_births": all(np.isfinite(v).all() for s in states.values() for v in s.values()),
            "reference_links_exact": all(v["expected_sha256"] == v["birth_sha256"] for v in links.values()),
            "birth_ema_equals_v": all(np.array_equal(s["V"], s["ema"]) for s in states.values()),
            "all_fission_masks_match": all(np.array_equal(mask, fresh) for mask in masks.values()),
            "native_half_fission": bool(np.all(fresh.sum(axis=(1, 2)) == 128)),
            "centered_birth_mean_zero": all(np.max(np.abs(s["V"].mean(axis=(1, 2)))) < 1e-14 for a, s in states.items() if a.startswith("centered")),
            "centered_shapes_preserved": all(v["centered_shape_max_error"] < 1e-14 for v in corrections.values()),
            "G1_bodies_match_within_factor": generation != 1 or all(np.array_equal(s["V"], states[f"{a.split('_')[0]}_copy_live"]["V"]) for a, s in states.items()),
            "held_references_unchanged": all(np.array_equal(s["R"], states[a]["R"]) for a, tr in trajectories.items() if a.endswith("held") for s in tr["snapshots"].values()),
            "held_copy_serial_identity": all(base.array_digest(trajectories[a]["final"]["R"]) == held_origin for a in ("native_copy_held", "centered_copy_held")),
            "native_writers_change_R": all(changed[a] for a in ARMS if not a.endswith("held")),
            "reader_off_full_body_alias": all(np.array_equal(trajectories["centered_copy_off"]["snapshots"][t][k], trajectories["centered_reset_off"]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema")),
            "arm_noise_streams_match": all(len({tr[k] for tr in trajectories.values()}) == 1 for k in ("rng_initial_sha256", "rng_final_sha256")),
            "distinct_generation_streams": len(set(streams)) == generation,
            "full_chain_exact_replay": base.trajectory_digest(trajectories[REPLAY_ARM]) == base.trajectory_digest(replay),
            "replay_boundary_exact": np.array_equal(replay_raw, raw_bodies[REPLAY_ARM]) and np.array_equal(replay_mask, fresh),
            "native_historical_anchors": root is None or anchor_matches(root, context, generation, trajectories, fresh, counts),
        }
        if not all(gates.values()):
            raise RuntimeError(f"G{generation} structural failure: {gates}")
        record = {"generation": generation, "passes": True, "structural_gates": gates, "summaries": summaries,
                  "parent_state_sha256": source_hashes, "birth_state_sha256": birth_hashes, "reference_links": links,
                  "reset_reference_sha256": reset_hash, "reference_changed_in_life": changed, "birth_corrections": corrections,
                  "final_state_sha256": {a: tr["final_sha256"] for a, tr in trajectories.items()},
                  "trajectory_sha256": {a: base.trajectory_digest(tr) for a, tr in trajectories.items()},
                  "rng_initial_sha256": streams[-1], "rng_final_sha256": trajectories[REPLAY_ARM]["rng_final_sha256"]}
        if output is not None:
            directory = output / f"g{generation:02d}"
            for a, tr in trajectories.items():
                base.atomic_npz(directory / f"{a}_states.npz", base.trajectory_arrays(tr), root)
            base.atomic_npz(directory / "births.npz", {**{f"raw_{a}": v for a, v in raw_bodies.items()}, "reset_R": reset_r, "fresh": fresh, "counts": counts}, root)
            atomic_json(directory / "generation.json", record | {"rows": rows}, root)
            atomic_json(output / "PROGRESS.json", {"generation_complete": generation, "updated_utc": utc_now()}, root)
            print(f"tissue {context['index']}: G{generation} centered-renewal complete", flush=True)
        records.append(record)
        parents = {a: base.state_copy(tr["final"]) for a, tr in trajectories.items()}
        replay_parent = base.state_copy(replay["final"])
    result = {"tissue": context["index"], "generations": records, "passes": all(r["passes"] for r in records), "g0_sha256": g0_hash}
    if output is not None:
        atomic_json(output / "lineage.json", result, root)
    return result


def contrast(values: list[float], seed: int) -> dict:
    array = np.asarray(values)
    draws = np.random.default_rng(seed).integers(0, len(array), (10000, len(array)))
    interval = np.quantile(array[draws].mean(axis=1), QUANTILES).tolist()
    positive = int((array > 0).sum())
    return {"tissue_differences": array.tolist(), "mean": float(array.mean()), "positive_tissues": positive,
            "paired_tissue_interval": interval, "quantiles": list(QUANTILES), "resamples": 10000, "seed": seed,
            "supported": interval[0] > 0 and positive >= 6}


def classify(results: list[dict], structural=True) -> dict:
    if (not structural or sorted(r["tissue"] for r in results) != list(TISSUES)
            or not all(r["passes"] and len(r["generations"]) == CONFIG.generations and all(g["passes"] for g in r["generations"])
                       and [g["generation"] for g in r["generations"]] == list(range(1, CONFIG.generations + 1)) for r in results)):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    results = sorted(results, key=lambda r: r["tissue"])
    protected = np.asarray([[g["summaries"]["centered_copy_held"][str(CONFIG.child_sweeps)]["body_accuracy"] for g in r["generations"]] for r in results])
    qualified = bool((protected > .25).all() and (protected.mean(axis=0) >= .75).all())
    final = [r["generations"][-1]["summaries"] for r in results]
    contrasts = {name: contrast([s[REPLAY_ARM][str(CONFIG.child_sweeps)][metric] - s[other][str(CONFIG.child_sweeps)][metric] for s in final], 20260907170401 + i)
                 for i, (name, metric, other) in enumerate(ENDPOINTS)}
    if not qualified:
        label = "PROTECTED_REFERENCE_CONTROL_NOT_QUALIFIED"
    elif all(c["supported"] for c in contrasts.values()):
        label = "CENTERED_NATIVE_RENEWAL_WITH_R_CONTRIBUTION"
    else:
        label = "NO_QUALIFIED_CENTERED_RENEWAL_LEAD"
    return {"label": label, "protected_reference_control_qualified": qualified,
            "protected_body_accuracy_tissue_by_generation": protected.tolist(), "co_primary_G12": contrasts}


def qualify_source(root: Path) -> dict:
    upstream = common.qualify_source(root)
    run = root / "runs" / SOURCE_ID
    status = json.loads((run / "STATUS.json").read_text())
    audit = root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1"
    audited = json.loads((audit / "rescore.json").read_text())
    directories = (root / "outputs" / SOURCE_ID, audit)
    maps = [chain.manifest_hashes(d / n) for d in directories for n in ("input_hashes.sha256", "output_hashes.sha256")]
    gates = {"earlier_instrument_qualified": upstream["passes"], "common_birth_complete": status["status"] == "COMPLETE" and status["completed_cleanly"] and (run / "COMPLETE").is_file() and not (run / "FAILED").exists(),
             "common_birth_independent_audit": audited["passes"], "all_common_source_audit_hashes": all(base.verify_hashes(h) for h in maps)}
    if not all(gates.values()):
        raise RuntimeError(f"source qualification failed: {gates}")
    return {"passes": True, "gates": gates, "unique_hashed_files": len(set().union(*(set(h) for h in maps)))}


def input_paths(root: Path) -> list[Path]:
    workspace = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), workspace / "tests/test_l17_centered_renewal.py", workspace / "scripts/run_l17_centered_renewal.sh",
             workspace / "scripts/audit_l17_centered_renewal_outputs.py", workspace / "protocols/L17_CENTERED_RENEWAL_V1.md",
             workspace / "reviews/L17_COMMON_BIRTH_FACTORIAL_2026-09-07.md"]
    for directory in (root / "outputs" / SOURCE_ID, root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1"):
        for name in ("input_hashes.sha256", "output_hashes.sha256"):
            path = directory / name
            paths.append(path)
            paths.extend(Path(p) for p in chain.manifest_hashes(path))
    paths.extend(root / "runs" / SOURCE_ID / n for n in ("STATUS.json", "COMPLETE", "MANIFEST.json"))
    return sorted(set(paths))


def disk_preflight(root: Path) -> dict:
    free = shutil.disk_usage(root).free
    return {"free_bytes": free, "estimated_output_bytes": 1024**3, "safety_margin_bytes": 1024**3, "passes": free >= 2 * 1024**3}


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("cannot alter prepared benchmark")
    runtime, source = base.runtime(), qualify_source(root)
    if not runtime["passes"] or not disk_preflight(root)["passes"]:
        raise RuntimeError("benchmark runtime/storage gate")
    cfg = replace(CONFIG, replicates=2, generations=3, settle_sweeps=8, imprint_sweeps=32, render_sweeps=32, child_sweeps=32, sample_times=(0, 8, 32))
    context = base.make_context(20032, cfg)
    g0 = base.teach_parent(context)["after_render"]
    start = time.monotonic()
    result = lineage(context, g0)
    elapsed = time.monotonic() - start
    projection = elapsed * CONFIG.replicates / cfg.replicates * CONFIG.generations / cfg.generations * CONFIG.child_sweeps / cfg.child_sweeps * math.ceil(len(TISSUES) / WORKERS) * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "effect_sizes_not_reported": True,
              "disposable_tissue": 20032, "config": asdict(cfg), "runtime": runtime, "source_qualification": source,
              "lineage_seconds": elapsed, "projected_seconds_four_workers": projection, "safety_multiplier": 1.75,
              "must_detach": projection > 600, "all_structural_gates_pass": result["passes"],
              "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
    atomic_json(benchmark_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root: Path) -> dict:
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("refusing existing immutable run/output")
    timing = json.loads(benchmark_path(root).read_text())
    runtime, disk, source = base.runtime(), disk_preflight(root), qualify_source(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    if not (timing["all_structural_gates_pass"] and timing["input_sha256"] == hashes and runtime["passes"] and disk["passes"]):
        raise RuntimeError("source/benchmark/runtime/storage preflight failed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    manifest = {"run_id": RUN_ID, "prepared_utc": utc_now(), "config": asdict(CONFIG), "tissues": list(TISSUES), "arms": list(ARMS),
                "workers": WORKERS, "registered_lives": REGISTERED_LIVES, "replay_lives": REPLAY_LIVES,
                "input_sha256": hashes, "contract_digest": canonical_digest(hashes), "benchmark": timing, "runtime": runtime,
                "source_qualification": source, "disk_preflight": disk, "environment": environment_manifest(),
                "repository_head": git_head(Path(__file__).resolve().parents[2]), "law_verdict_changes": 0}
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
            or manifest["tissues"] != list(TISSUES) or manifest["arms"] != list(ARMS) or manifest["workers"] != WORKERS
            or (run / "COMPLETE").exists() or (run / "FAILED").exists()):
        raise RuntimeError("not uniquely prepared or contract changed")
    return manifest


def launch_detached(root: Path) -> dict:
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest = verify_prepared(root)
    run = root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l17_centered_renewal", "--external-root", str(root), "--run"]
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
    return record  # Deliberately no poll/wait/status inspection.


def worker(tissue: int, root_text: str) -> dict:
    root = external_root(root_text)
    if not base.runtime()["passes"]:
        raise RuntimeError("worker runtime gate")
    context = base.make_context(tissue, CONFIG)
    g0 = chain.parent_input(root, context)
    output = root / "outputs" / RUN_ID / f"tissue_{tissue}"
    return lineage(context, g0, root, output)


def report(study: dict) -> str:
    lines = ["# L17 centered native renewal", "", f"Run: `{RUN_ID}`.", "", f"Result: `{study['classification']['label']}`.", "",
             "Fragment inheritance, not an exclusive-R reset. No ancestor backup is restored.", "",
             "| G | Centered copy/live V | Reset/live V | Copy/off V | Copy/live R | Copy/held V | Native copy/live V |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for g in range(CONFIG.generations):
        summaries = [r["generations"][g]["summaries"] for r in study["results"]]
        values = [np.mean([s[a][str(CONFIG.child_sweeps)][k] for s in summaries]) for a, k in (
            (REPLAY_ARM, "body_accuracy"), ("centered_reset_live", "body_accuracy"), ("centered_copy_off", "body_accuracy"),
            (REPLAY_ARM, "reference_accuracy"), ("centered_copy_held", "body_accuracy"), ("native_copy_live", "body_accuracy"))]
        lines.append(f"| {g+1} | " + " | ".join(f"{v:.6f}" for v in values) + " |")
    return "\n".join(lines + ["", "No automatic law-verdict changes; negative decoding is not zero information.", ""])


def run_study(root: Path) -> int:
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required above ten minutes")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        runtime, source = base.runtime(), qualify_source(root)
        if not runtime["passes"] or not disk_preflight(root)["passes"]:
            raise RuntimeError("run runtime/storage gate")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        atomic_json(run / "STATUS.json", {"status": "RUNNING", "completed_tissues": 0, "updated_utc": utc_now()}, root)
        collected = []
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as executor:
            futures = [executor.submit(worker, tissue, str(root)) for tissue in TISSUES]
            for future in as_completed(futures):
                collected.append(future.result())
                atomic_json(run / "STATUS.json", {"status": "RUNNING", "completed_tissues": len(collected), "updated_utc": utc_now()}, root)
        collected.sort(key=lambda r: r["tissue"])
        gates = {"runtime": runtime["passes"], "source_qualification": source["passes"],
                 "all_tissues_present": [r["tissue"] for r in collected] == list(TISSUES),
                 "all_structural_gates": all(r["passes"] and all(g["passes"] and all(g["structural_gates"].values()) for g in r["generations"]) for r in collected),
                 "input_hashes_unchanged": base.verify_hashes(manifest["input_sha256"])}
        classification = classify(collected, all(gates.values()))
        study = {"run_id": RUN_ID, "generated_utc": utc_now(), "config": asdict(CONFIG), "runtime": runtime,
                 "results": collected, "classification": classification, "completion_gates": gates, "completed_cleanly": all(gates.values()),
                 "child_lives": REGISTERED_LIVES, "replay_lives": REPLAY_LIVES, "elapsed_seconds": time.monotonic() - start, "law_verdict_changes": 0}
        atomic_json(output / "centered_renewal.json", study, root)
        atomic_text(output / "audit.md", report(study), root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"), output / "output_hashes.sha256", root)
        verified = base.verify_hashes(chain.manifest_hashes(output / "output_hashes.sha256"))
        success = study["completed_cleanly"] and verified
        status = {"run_id": RUN_ID, "status": "COMPLETE" if success else "FAILED_GATES", "completed_cleanly": success,
                  "classification": classification["label"], "completed_utc": utc_now(), "elapsed_seconds": time.monotonic() - start,
                  "workers": WORKERS, "cpu_affinity": runtime["cpu_affinity"], "child_lives": REGISTERED_LIVES,
                  "replay_lives": REPLAY_LIVES, "output_manifest_self_verifies": verified}
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
    for name in ("benchmark", "prepare", "detach", "run"):
        group.add_argument(f"--{name}", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        manifest = prepare(root)
        print(json.dumps({"status": "PREPARED", "input_files": len(manifest["input_sha256"]), "estimated_seconds": manifest["benchmark"]["projected_seconds_four_workers"]}, indent=2))
    elif args.detach:
        launch_detached(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
