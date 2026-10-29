"""Common-state read/write separation with a zero-initialized candidate record."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import json
import math
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l17_centered_renewal as centered
from . import l17_common_birth as common
from . import l17_r_channel as base
from . import l17_r_channel_twelve as chain
from .io import (atomic_json, atomic_text, canonical_digest, environment_manifest,
                 external_root, git_head, sha256_file, utc_now, write_hash_manifest)


RUN_ID = "l17_read_write_split_v1_attempt1"
SOURCE_ID = centered.RUN_ID
TISSUES, CHECKPOINTS, WORKERS = base.TISSUES, (1, 2, 3), 4
CONFIG = base.ExperimentConfig(sample_times=(0, 50, 1000))
ARMS = ("live_correct", "held_correct", "live_reset", "held_reset", "held_wrong", "off_correct", "off_reset")
PROBES = tuple(f"q_{a}" for a in ARMS) + ("input_held", "zero_held", "q_held_correct_off", "zero_off")
REPLAY_ARM = "held_correct"
REGISTERED_LIVES = len(TISSUES) * len(CHECKPOINTS) * 4 * CONFIG.replicates * (len(ARMS) + len(PROBES))
REPLAY_LIVES = len(TISSUES) * len(CHECKPOINTS) * 4 * CONFIG.replicates * 2
ENDPOINTS = (("candidate_margin", "candidate", "held_correct", "live_correct", "reference_true_margin"),
             ("candidate_readout", "probe", "q_held_correct", "q_live_correct", "body_accuracy"),
             ("reference_contribution", "probe", "q_held_correct", "q_held_reset", "body_accuracy"))


def source_directory(root: Path, tissue: int, generation: int) -> Path:
    return root / "outputs" / SOURCE_ID / f"tissue_{tissue}" / f"g{generation:02d}"


def load_common(root: Path, context: dict, generation: int) -> dict:
    if generation not in CHECKPOINTS:
        raise ValueError("unregistered checkpoint")
    directory = source_directory(root, context["index"], generation)
    anchor = chain.load_arrays(directory / "centered_copy_live_states.npz")
    initial = {k: anchor[f"s0_{k}"].copy() for k in ("V", "ema", "R")}
    saved = json.loads((directory / "generation.json").read_text())
    ancestor = chain.parent_input(root, context)
    if generation == 1:
        parent = base.state_copy(ancestor)
    else:
        previous = chain.load_arrays(source_directory(root, context["index"], generation - 1) / "centered_copy_live_states.npz")
        parent = {k: previous[f"s1000_{k}"] for k in ("V", "ema", "R")}
    births = chain.load_arrays(directory / "births.npz")
    old = centered.old_directory(root, context["index"], generation)
    newborn = chain.load_arrays(old / "newborn.npz")
    calibration = json.loads((old / "calibration.json").read_text())
    raw, fresh = chain.fission(context, parent, generation)
    if (base.state_digest(initial) != saved["birth_state_sha256"]["centered_copy_live"]
            or base.state_digest(parent) != saved["parent_state_sha256"]["centered_copy_live"]
            or base.state_digest(newborn) != calibration["newborn_sha256"]
            or not np.array_equal(initial["V"], common.centered_body(raw))
            or not np.array_equal(initial["R"], parent["R"])
            or not np.array_equal(fresh, births["fresh"])
            or not np.array_equal(newborn["R"], births["reset_R"])):
        raise RuntimeError("immutable common birth / naive readout body changed")
    return {"initial": initial, "parent": parent, "ancestor": ancestor, "newborn": newborn,
            "fresh": fresh, "counts": births["counts"], "anchor": anchor}


def branches(data: dict, replicates: int) -> dict:
    states = {}
    for arm in ARMS:
        state = base.state_copy(data["initial"])
        if arm.endswith("reset"):
            state["R"] = data["newborn"]["R"].copy()
        elif arm.endswith("wrong"):
            state["R"] = chain.permute_message(data["initial"]["R"], replicates)
        states[arm] = state
    return states


def develop(context: dict, initial: dict, generation: int, arm: str) -> dict:
    if arm not in ARMS:
        raise ValueError("unregistered development arm")
    cfg, rho = context["config"], context["bp"].rho
    rng = base.MessageCoupledRNG(context["index"], chain.phase(generation, "child_development"), cfg.replicates)
    rng_initial, initial_hash = rng.digest(), base.state_digest(initial)
    bp = replace(context["bp"], rho=0.) if arm.startswith("held") else context["bp"]
    state = base.state_copy(initial)
    q, weighted = np.zeros_like(state["V"]), np.zeros_like(state["V"])
    snapshots = {0: base.state_copy(state) | {"Q": q.copy()}}
    body_scores = [base.decode(state["V"], context["codes"])[0]]
    accumulator_errors, carry_errors = {}, {}
    for sweep in range(1, cfg.child_sweeps + 1):
        # The native body/reader receives only the working state, never Q.
        values = context["api"]["blueprint_step"](state["V"], state["ema"], state["R"],
            context["theta"], context["tissue"], context["ladder"], bp, "T", rng,
            c_m=0. if arm.startswith("off") else None)
        state = dict(zip(("V", "ema", "R"), values))
        q = q + rho * (state["V"] - q)
        weighted = (1 - rho) * weighted + state["V"]
        body_scores.append(base.decode(state["V"], context["codes"])[0])
        if sweep in cfg.sample_times:
            snapshots[sweep] = base.state_copy(state) | {"Q": q.copy()}
            accumulator_errors[str(sweep)] = float(np.max(abs(q - rho * weighted)))
            if not arm.startswith("held"):
                carry_errors[str(sweep)] = float(np.max(abs(state["R"] - q - (1-rho)**sweep * initial["R"])))
    gates = {"input_unchanged": base.state_digest(initial) == initial_hash,
             "candidate_birth_zero": bool(np.all(snapshots[0]["Q"] == 0)),
             "candidate_actually_written": not np.array_equal(snapshots[0]["Q"], q),
             "finite": all(np.isfinite(v).all() for s in snapshots.values() for v in s.values()),
             "independent_weighted_accumulator": all(v < 1e-12 for v in accumulator_errors.values()),
             "working_R_carry_identity": all(v < 1e-12 for v in carry_errors.values()),
             "held_working_R_exact": not arm.startswith("held") or all(np.array_equal(s["R"], initial["R"]) for s in snapshots.values())}
    if not all(gates.values()):
        raise RuntimeError(f"development structural failure: {gates}")
    return {"snapshots": snapshots, "final": base.state_copy(state) | {"Q": q.copy()},
            "body_scores": np.asarray(body_scores), "rng_initial_sha256": rng_initial, "rng_final_sha256": rng.digest(),
            "initial_sha256": initial_hash, "accumulator_errors": accumulator_errors, "carry_errors": carry_errors, "gates": gates}


def development_digest(trajectory: dict) -> str:
    return canonical_digest({"snapshots": {str(t): base.state_digest(s) for t, s in trajectory["snapshots"].items()},
        "body_scores": base.array_digest(trajectory["body_scores"]),
        **{k: v for k, v in trajectory.items() if k not in ("snapshots", "final", "body_scores")}})


def candidate_view(trajectory: dict) -> dict:
    return {"snapshots": {t: {"V": s["V"], "ema": s["ema"], "R": s["Q"]} for t, s in trajectory["snapshots"].items()}}


def probe_birth(newborn: dict, reference: np.ndarray) -> dict:
    """Only a reference enters a matched naive body; no development state."""
    return {"V": newborn["V"].copy(), "ema": newborn["ema"].copy(), "R": reference.copy()}


def probe(context: dict, newborn: dict, reference: np.ndarray, generation: int, off=False) -> dict:
    return base.simulate(context, probe_birth(newborn, reference), chain.phase(generation, "child_development"),
                         context["config"].child_sweeps, sample_times=context["config"].sample_times,
                         rho=0., c_m=0. if off else None)


def measure(context: dict, trajectory: dict, data: dict | None = None) -> list[dict]:
    args = (data["ancestor"], data["parent"], data["fresh"], data["counts"]) if data else ()
    rows = chain.measurements(context, trajectory, *args)
    for row in rows:
        i = row["message"] * context["config"].replicates + row["replicate"]
        v = trajectory["snapshots"][row["sweep"]]["V"][i]
        row["body_min"], row["body_max"] = float(v.min()), float(v.max())
    return rows


def experiment(context: dict, data: dict, generation: int) -> tuple[dict, dict, dict]:
    cfg = context["config"]
    hashes = {k: base.state_digest(data[k]) for k in ("initial", "parent", "ancestor", "newborn")}
    states = branches(data, cfg.replicates)
    developed = {a: develop(context, s, generation, a) for a, s in states.items()}
    references = {f"q_{a}": tr["final"]["Q"] for a, tr in developed.items()}
    references.update(input_held=data["initial"]["R"], zero_held=np.zeros_like(data["initial"]["R"]),
                      q_held_correct_off=developed[REPLAY_ARM]["final"]["Q"], zero_off=np.zeros_like(data["initial"]["R"]))
    probes = {a: probe(context, data["newborn"], references[a], generation, a.endswith("off")) for a in PROBES}
    replay = develop(context, states[REPLAY_ARM], generation, REPLAY_ARM)
    replay_probe = probe(context, data["newborn"], replay["final"]["Q"], generation)
    rows = {"working": {a: measure(context, tr, data) for a, tr in developed.items()},
            "candidate": {a: measure(context, candidate_view(tr), data) for a, tr in developed.items()},
            "probe": {a: measure(context, tr) for a, tr in probes.items()}}
    summaries = {kind: {a: common.summarize(r) for a, r in group.items()} for kind, group in rows.items()}
    links = {a: {"reference_sha256": base.array_digest(references[a]), "birth_sha256": base.array_digest(tr["snapshots"][0]["R"])} for a, tr in probes.items()}
    anchor = data.get("anchor")
    gates = {"common_inputs_unchanged": hashes == {k: base.state_digest(data[k]) for k in hashes},
             "birth_bodies_matched": all(np.array_equal(s[k], data["initial"][k]) for s in states.values() for k in ("V", "ema")),
             "all_development_gates": all(all(tr["gates"].values()) for tr in developed.values()),
             "reset_and_naive_body_message_independent": all(base.message_independent(v, cfg.replicates) for v in data["newborn"].values()),
             "candidate_births_exact_zero": all(np.all(tr["snapshots"][0]["Q"] == 0) for tr in developed.values()),
             "wrong_R_value_permutation": np.array_equal(np.sort(states["held_wrong"]["R"].ravel()), np.sort(data["initial"]["R"].ravel())),
             "off_development_V_ema_Q_alias": all(np.array_equal(developed["off_correct"]["snapshots"][t][k], developed["off_reset"]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema", "Q")),
             "off_body_projection_trace_alias": np.array_equal(developed["off_correct"]["body_scores"], developed["off_reset"]["body_scores"]),
             "naive_probe_bodies_exact": all(np.array_equal(tr["snapshots"][0][k], data["newborn"][k]) for tr in probes.values() for k in ("V", "ema")),
             "probe_reference_links": all(v["reference_sha256"] == v["birth_sha256"] for v in links.values()),
             "probe_references_held": all(np.array_equal(s["R"], references[a]) for a, tr in probes.items() for s in tr["snapshots"].values()),
             "off_probe_body_alias": all(np.array_equal(probes["q_held_correct_off"]["snapshots"][t][k], probes["zero_off"]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema")),
             "off_probe_chance": all(s["body_accuracy"] == .25 for a in ("q_held_correct_off", "zero_off") for s in summaries["probe"][a].values()),
             "streams_matched": all(len({tr[k] for tr in (*developed.values(), *probes.values())}) == 1 for k in ("rng_initial_sha256", "rng_final_sha256")),
             "full_new_development_replay": development_digest(developed[REPLAY_ARM]) == development_digest(replay),
             "full_new_candidate_probe_replay": base.trajectory_digest(probes[f"q_{REPLAY_ARM}"]) == base.trajectory_digest(replay_probe),
             "historical_live_anchor_exact": anchor is None or (set(anchor) == {f"s{t}_{k}" for t in cfg.sample_times for k in ("V", "ema", "R")} and all(np.array_equal(developed["live_correct"]["snapshots"][t][k], anchor[f"s{t}_{k}"]) for t in cfg.sample_times for k in ("V", "ema", "R")))}
    if not all(gates.values()):
        raise RuntimeError(f"read/write split structural failure: {gates}")
    result = {"tissue": context["index"], "generation": generation, "passes": True, "structural_gates": gates,
              "source_sha256": hashes, "birth_sha256": {a: base.state_digest(s) for a, s in states.items()},
              "development_sha256": {a: development_digest(tr) for a, tr in developed.items()},
              "development_checks": {a: {k: tr[k] for k in ("gates", "accumulator_errors", "carry_errors")} for a, tr in developed.items()},
              "probe_sha256": {a: base.trajectory_digest(tr) for a, tr in probes.items()}, "probe_reference_links": links,
              "rng_initial_sha256": developed[REPLAY_ARM]["rng_initial_sha256"], "rng_final_sha256": developed[REPLAY_ARM]["rng_final_sha256"],
              "summaries": summaries, "rows": rows}
    return result, developed, probes


def classify(results: list[dict], structural=True) -> dict:
    expected = [(t, g) for t in TISSUES for g in CHECKPOINTS]
    if not structural or sorted((r["tissue"], r["generation"]) for r in results) != expected or not all(r["passes"] for r in results):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    selected = sorted((r for r in results if r["generation"] == 2), key=lambda r: r["tissue"])
    contrasts = {name: centered.contrast([r["summaries"][kind][left][str(CONFIG.child_sweeps)][metric] - r["summaries"][kind][right][str(CONFIG.child_sweeps)][metric] for r in selected], 20260907170501+i)
                 for i, (name, kind, left, right, metric) in enumerate(ENDPOINTS)}
    return {"label": "READ_WRITE_SEPARATION_IMPROVES_NEW_RECORD" if all(c["supported"] for c in contrasts.values()) else "NO_QUALIFIED_SPLIT_READER_LEAD", "co_primary_G2": contrasts}


def qualify_source(root: Path) -> dict:
    upstream = centered.qualify_source(root)
    run = root / "runs" / SOURCE_ID
    status = json.loads((run / "STATUS.json").read_text())
    audit = root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1"
    audited = json.loads((audit / "rescore.json").read_text())
    maps = [chain.manifest_hashes(d / n) for d in (root / "outputs" / SOURCE_ID, audit) for n in ("input_hashes.sha256", "output_hashes.sha256")]
    calibration = [[json.loads((centered.old_directory(root, t, g) / "calibration.json").read_text())["positive_accuracy"] for g in CHECKPOINTS] for t in TISSUES]
    scores = np.asarray(calibration)
    gates = {"upstream_qualified": upstream["passes"], "source_complete": status["status"] == "COMPLETE" and status["completed_cleanly"] and (run / "COMPLETE").is_file() and not (run / "FAILED").exists(),
             "source_independent_audit": audited["passes"], "source_hashes": all(base.verify_hashes(h) for h in maps),
             "exact_reused_readout_instrument": bool((scores > .25).all() and (scores.mean(axis=0) >= .75).all())}
    if not all(gates.values()):
        raise RuntimeError(f"source qualification failed: {gates}")
    return {"passes": True, "gates": gates, "reused_positive_accuracy": calibration}


def input_paths(root: Path) -> list[Path]:
    workspace = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), workspace / "tests/test_l17_read_write_split.py", workspace / "scripts/run_l17_read_write_split.sh",
             workspace / "scripts/audit_l17_read_write_split_outputs.py", workspace / "protocols/L17_READ_WRITE_SPLIT_V1.md",
             workspace / "reviews/L17_CENTERED_RENEWAL_2026-09-07.md"]
    for directory in (root / "outputs" / SOURCE_ID, root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1"):
        for name in ("input_hashes.sha256", "output_hashes.sha256"):
            path = directory / name
            paths.append(path)
            paths.extend(Path(p) for p in chain.manifest_hashes(path))
    paths.extend(root / "runs" / SOURCE_ID / n for n in ("STATUS.json", "COMPLETE", "MANIFEST.json"))
    return sorted(set(paths))


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def disposable(context: dict) -> dict:
    parent = base.teach_parent(context)["after_render"]
    raw, fresh = chain.fission(context, parent, 2)
    v = common.centered_body(raw)
    return {"initial": {"V": v, "ema": v.copy(), "R": parent["R"].copy()}, "parent": parent,
            "ancestor": base.state_copy(parent), "newborn": base.naive_body(context, chain.phase(2, "fresh_body_birth")),
            "fresh": fresh, "counts": fresh.astype(np.int32)}


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("cannot alter prepared benchmark")
    runtime, source = base.runtime(), qualify_source(root)
    if not runtime["passes"] or not centered.disk_preflight(root)["passes"]:
        raise RuntimeError("benchmark runtime/storage gate")
    cfg = replace(CONFIG, replicates=2, settle_sweeps=8, imprint_sweeps=32, render_sweeps=32, child_sweeps=32, sample_times=(0, 8, 32))
    context = base.make_context(20042, cfg)
    data = disposable(context)
    start = time.monotonic()
    result, _, _ = experiment(context, data, 2)
    elapsed = time.monotonic() - start
    projection = elapsed * CONFIG.replicates / cfg.replicates * CONFIG.child_sweeps / cfg.child_sweeps * math.ceil(len(TISSUES)*len(CHECKPOINTS)/WORKERS) * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "effect_sizes_not_reported": True,
              "disposable_tissue": 20042, "config": asdict(cfg), "runtime": runtime, "source_qualification": source,
              "cell_seconds": elapsed, "projected_seconds_four_workers": projection, "safety_multiplier": 1.75,
              "must_detach": projection > 600, "all_structural_gates_pass": result["passes"],
              "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
    atomic_json(benchmark_path(root), record, root)
    print(json.dumps({k:v for k,v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def prepare(root: Path) -> dict:
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if run.exists() or output.exists():
        raise FileExistsError("refusing existing immutable run/output")
    timing = json.loads(benchmark_path(root).read_text())
    runtime, disk, source = base.runtime(), centered.disk_preflight(root), qualify_source(root)
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    if not (timing["all_structural_gates_pass"] and timing["input_sha256"] == hashes and runtime["passes"] and disk["passes"]):
        raise RuntimeError("source/benchmark/runtime/storage preflight failed")
    hashes[str(benchmark_path(root))] = sha256_file(benchmark_path(root))
    run.mkdir(parents=True)
    output.mkdir(parents=True)
    manifest = {"run_id": RUN_ID, "prepared_utc": utc_now(), "config": asdict(CONFIG), "tissues": list(TISSUES), "checkpoints": list(CHECKPOINTS),
                "arms": list(ARMS), "probes": list(PROBES), "workers": WORKERS, "registered_lives": REGISTERED_LIVES, "replay_lives": REPLAY_LIVES,
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
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths(root)+[benchmark_path(root)]}
            or canonical_digest(manifest["config"]) != canonical_digest(asdict(CONFIG))
            or manifest["tissues"] != list(TISSUES) or manifest["checkpoints"] != list(CHECKPOINTS)
            or manifest["arms"] != list(ARMS) or manifest["probes"] != list(PROBES) or manifest["workers"] != WORKERS
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
    command = [sys.executable, "-m", "laws_confirmation.l17_read_write_split", "--external-root", str(root), "--run"]
    with stdout.open("xb") as out_handle, stderr.open("xb") as err_handle:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                                   stdout=out_handle, stderr=err_handle, start_new_session=True)
    record = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(), "command": command, "stdout_log": str(stdout),
              "stderr_log": str(stderr), "status": str(run / "STATUS.json"), "complete": str(run / "COMPLETE"), "failed": str(run / "FAILED"),
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
    data = load_common(root, context, generation)
    result, developed, probes = experiment(context, data, generation)
    output = root / "outputs" / RUN_ID / f"tissue_{tissue}" / f"g{generation:02d}"
    arrays = {f"{name}_{k}": v for name in ("initial", "parent", "ancestor", "newborn") for k,v in data[name].items()}
    base.atomic_npz(output / "common.npz", arrays | {k:data[k] for k in ("fresh", "counts")}, root)
    for arm, tr in developed.items():
        base.atomic_npz(output / f"development_{arm}.npz", base.trajectory_arrays(tr) | {"body_scores": tr["body_scores"]}, root)
    for arm, tr in probes.items():
        base.atomic_npz(output / f"probe_{arm}.npz", base.trajectory_arrays(tr), root)
    atomic_json(output / "cell.json", result, root)
    print(f"tissue {tissue} G{generation}: read/write split cell complete", flush=True)
    return {k:v for k,v in result.items() if k != "rows"}


def report(study: dict) -> str:
    lines = ["# L17 read/write split", "", f"Run: `{RUN_ID}`.", "", f"Result: `{study['classification']['label']}`.", "",
             "Matched branch points, zero-initialized candidate, one held-reference readout assay; not a twelve-generation renewal test.", "",
             "| Source G | Live Q margin | Held Q margin | Live Q readout | Held Q readout | Reset-held Q readout |",
             "|---|---:|---:|---:|---:|---:|"]
    for g in CHECKPOINTS:
        selected = [r["summaries"] for r in study["results"] if r["generation"] == g]
        values = [np.mean([s[kind][arm][str(CONFIG.child_sweeps)][metric] for s in selected]) for kind, arm, metric in (
            ("candidate", "live_correct", "reference_true_margin"), ("candidate", "held_correct", "reference_true_margin"),
            ("probe", "q_live_correct", "body_accuracy"), ("probe", "q_held_correct", "body_accuracy"), ("probe", "q_held_reset", "body_accuracy"))]
        lines.append(f"| {g} | " + " | ".join(f"{v:.6f}" for v in values) + " |")
    return "\n".join(lines + ["", "No automatic law-verdict change or next experiment.", ""])


def run_study(root: Path) -> int:
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("detached launch required above ten minutes")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        runtime, source = base.runtime(), qualify_source(root)
        if not runtime["passes"] or not centered.disk_preflight(root)["passes"]:
            raise RuntimeError("run runtime/storage gate")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        atomic_json(run / "STATUS.json", {"status": "RUNNING", "completed_cells": 0, "updated_utc": utc_now()}, root)
        collected = []
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as executor:
            futures = [executor.submit(worker, t, g, str(root)) for t in TISSUES for g in CHECKPOINTS]
            for future in as_completed(futures):
                collected.append(future.result())
                atomic_json(run / "STATUS.json", {"status": "RUNNING", "completed_cells": len(collected), "updated_utc": utc_now()}, root)
        collected.sort(key=lambda r: (r["tissue"], r["generation"]))
        gates = {"runtime": runtime["passes"], "source_qualification": source["passes"],
                 "all_cells_present": [(r["tissue"], r["generation"]) for r in collected] == [(t,g) for t in TISSUES for g in CHECKPOINTS],
                 "all_structural_gates": all(r["passes"] and all(r["structural_gates"].values()) for r in collected),
                 "input_hashes_unchanged": base.verify_hashes(manifest["input_sha256"])}
        classification = classify(collected, all(gates.values()))
        study = {"run_id": RUN_ID, "generated_utc": utc_now(), "config": asdict(CONFIG), "runtime": runtime, "results": collected,
                 "classification": classification, "completion_gates": gates, "completed_cleanly": all(gates.values()),
                 "scientific_lives": REGISTERED_LIVES, "replay_lives": REPLAY_LIVES, "elapsed_seconds": time.monotonic()-start, "law_verdict_changes": 0}
        atomic_json(output / "read_write_split.json", study, root)
        atomic_text(output / "audit.md", report(study), root)
        write_hash_manifest(sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256"), output / "output_hashes.sha256", root)
        verified = base.verify_hashes(chain.manifest_hashes(output / "output_hashes.sha256"))
        success = study["completed_cleanly"] and verified
        status = {"run_id": RUN_ID, "status": "COMPLETE" if success else "FAILED_GATES", "completed_cleanly": success,
                  "classification": classification["label"], "completed_utc": utc_now(), "elapsed_seconds": time.monotonic()-start,
                  "workers": WORKERS, "cpu_affinity": runtime["cpu_affinity"], "scientific_lives": REGISTERED_LIVES,
                  "replay_lives": REPLAY_LIVES, "output_manifest_self_verifies": verified}
        atomic_json(run / "STATUS.json", status, root)
        atomic_text(run / ("COMPLETE" if success else "FAILED"), status["completed_utc"]+"\n", root)
        print(json.dumps(status, indent=2), flush=True)
        return 0 if success else 1
    except Exception as error:
        failure = {"status": "FAILED", "run_id": RUN_ID, "failed_utc": utc_now(), "error": str(error), "traceback": traceback.format_exc()}
        atomic_json(run / "STATUS.json", failure, root)
        atomic_text(run / "FAILED", failure["failed_utc"]+"\n", root)
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
