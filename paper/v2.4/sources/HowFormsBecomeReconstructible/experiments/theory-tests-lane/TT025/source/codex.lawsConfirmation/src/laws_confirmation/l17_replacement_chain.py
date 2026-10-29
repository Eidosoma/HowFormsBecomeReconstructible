"""Fresh bodies inherit only a rebuilt packet through twelve serial replacements."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
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

from . import l17_read_write_split as split
from . import l17_r_channel as base
from . import l17_r_channel_twelve as chain
from . import l17_common_birth as common
from . import l17_centered_renewal as centered
from .io import (atomic_json, atomic_text, canonical_digest, environment_manifest,
                 external_root, git_head, sha256_file, utc_now, write_hash_manifest)


RUN_ID = "l17_replacement_chain_v1_attempt1"
SOURCE_ID = split.RUN_ID
CONFIG, TISSUES, WORKERS = chain.ChainConfig(), base.TISSUES, 4
MODES = {"split_replace": "held_correct", "split_reset": "held_reset", "split_wrong": "held_wrong",
         "split_off": "off_correct", "reset_off": "off_reset", "coupled_replace": "live_correct",
         "native_carry": "live_correct", "native_reset": "live_reset", "protected_copy": "held_correct"}
ARMS = tuple(MODES)
RESET_ARMS = ("split_reset", "reset_off", "native_reset")
COPY_ARMS = ("native_carry", "protected_copy")
ANCHORS = {"native_carry": "fresh_renew", "native_reset": "fresh_reset"}
PROBE_DONORS = {"q_split": "split_replace", "q_reset": "split_reset", "q_coupled": "coupled_replace",
                "q_reader_off": "split_off", "q_wrong": "split_wrong", "q_split_off": "split_replace", "zero_off": None}
PROBES = tuple(PROBE_DONORS)
REGISTERED_LIVES = len(TISSUES) * 4 * CONFIG.replicates * (CONFIG.generations * len(ARMS) + len(PROBES))
REPLAY_LIVES = len(TISSUES) * 4 * CONFIG.replicates * (CONFIG.generations + 1)
ENDPOINTS = (("body_vs_reset", "generation", "split_replace", "split_reset"),
             ("new_record_readout_vs_reset", "terminal", "q_split", "q_reset"),
             ("new_record_readout_vs_reader_off", "terminal", "q_split", "q_split_off"))


def serialize(reference: np.ndarray) -> bytes:
    if reference.dtype != np.dtype("float64") or reference.ndim != 3 or reference.shape[1:] != (16, 16) or not np.isfinite(reference).all():
        raise ValueError("packet must be finite float64 full fields")
    return reference.tobytes(order="C")


def packet_hash(packet: bytes) -> str:
    return hashlib.sha256(packet).hexdigest()


def birth(newborn: dict, packet: bytes) -> dict:
    """The complete inheritance interface: public naive state and one byte packet."""
    if type(packet) is not bytes or len(packet) != newborn["V"].size * 8:
        raise ValueError("exactly one 2048-byte record per newborn required")
    reference = np.frombuffer(packet, dtype=np.float64).reshape(newborn["V"].shape).copy()
    if not np.isfinite(reference).all():
        raise ValueError("nonfinite incoming packet")
    return {"V": newborn["V"].copy(), "ema": newborn["ema"].copy(), "R": reference}


def initial_packets(seed: bytes, newborn: dict, replicates: int) -> dict:
    r = birth(newborn, seed)["R"]
    return {a: serialize(chain.permute_message(r, replicates)) if a == "split_wrong" else bytes(seed) for a in ARMS}


def load_newborn(root: Path, context: dict, generation: int) -> dict:
    directory = centered.old_directory(root, context["index"], generation)
    newborn = chain.load_arrays(directory / "newborn.npz")
    saved = json.loads((directory / "calibration.json").read_text())
    if set(newborn) != {"V", "ema", "R"} or base.state_digest(newborn) != saved["newborn_sha256"]:
        raise RuntimeError("immutable naive birth changed")
    if not all(base.message_independent(v, context["config"].replicates) for v in newborn.values()):
        raise RuntimeError("naive birth contains message identity")
    return newborn


def generation(context: dict, packets: dict, newborn: dict, number: int, replay_packet: bytes,
               anchors: dict | None = None) -> tuple[dict, dict, bytes, dict]:
    cfg = context["config"]
    if set(packets) != set(ARMS) or not 1 <= number <= cfg.generations:
        raise ValueError("unregistered lineage cell")
    naive_hash = base.state_digest(newborn)
    upstream_hashes = {a: packet_hash(p) for a, p in packets.items()}
    effective = {a: serialize(newborn["R"]) if a in RESET_ARMS else p for a, p in packets.items()}
    states = {a: birth(newborn, p) for a, p in effective.items()}
    developed = {a: split.develop(context, states[a], number, MODES[a]) for a in ARMS}
    outgoing = {a: serialize(tr["final"]["R" if a in COPY_ARMS else "Q"]) for a, tr in developed.items()}
    # Replay has its own independently advanced packet, not the production parent's Q.
    replay = split.develop(context, birth(newborn, replay_packet), number, MODES["split_replace"])
    replay_outgoing = serialize(replay["final"]["Q"])
    rows = {"working": {a: split.measure(context, tr) for a, tr in developed.items()},
            "candidate": {a: split.measure(context, split.candidate_view(tr)) for a, tr in developed.items()}}
    summaries = {kind: {a: common.summarize(r) for a, r in group.items()} for kind, group in rows.items()}
    gates = {
        "public_newborn_unchanged": base.state_digest(newborn) == naive_hash,
        "public_newborn_message_independent": all(base.message_independent(v, cfg.replicates) for v in newborn.values()),
        "incoming_packets_unchanged": upstream_hashes == {a: packet_hash(p) for a, p in packets.items()},
        "fresh_body_and_ema_only": all(np.array_equal(tr["snapshots"][0][k], newborn[k]) for tr in developed.values() for k in ("V", "ema")),
        "serialized_reference_links": all(serialize(tr["snapshots"][0]["R"]) == effective[a] for a, tr in developed.items()),
        "all_development_gates": all(all(tr["gates"].values()) for tr in developed.values()),
        "off_V_ema_Q_alias": all(np.array_equal(developed["split_off"]["snapshots"][t][k], developed["reset_off"]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema", "Q")),
        "off_trace_alias": np.array_equal(developed["split_off"]["body_scores"], developed["reset_off"]["body_scores"]),
        "wrong_is_donor_permutation": all(np.array_equal(developed["split_wrong"]["snapshots"][t][k], chain.permute_message(developed["split_replace"]["snapshots"][t][k], cfg.replicates)) for t in cfg.sample_times for k in ("V", "ema", "R", "Q")),
        "reset_and_off_chance": all(s["body_accuracy"] == .25 for a in (*RESET_ARMS, "split_off") for s in summaries["working"][a].values()),
        "protected_serial_copy_exact": outgoing["protected_copy"] == effective["protected_copy"],
        "full_own_packet_replay": split.development_digest(developed["split_replace"]) == split.development_digest(replay) and outgoing["split_replace"] == replay_outgoing,
        "matched_streams": all(len({tr[k] for tr in (*developed.values(), replay)}) == 1 for k in ("rng_initial_sha256", "rng_final_sha256")),
        "historical_native_anchors": anchors is None or (set(anchors) == set(ANCHORS) and all(set(raw) == {f"s{t}_{k}" for t in cfg.sample_times for k in ("V", "ema", "R")} and all(np.array_equal(raw[f"s{t}_{k}"], developed[a]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema", "R")) for a, raw in anchors.items())),
    }
    if not all(gates.values()):
        raise RuntimeError(f"replacement boundary failed: {gates}")
    record = {"tissue": context["index"], "generation": number, "passes": True, "structural_gates": gates,
              "newborn_sha256": naive_hash, "upstream_packet_sha256": upstream_hashes,
              "received_packet_sha256": {a: packet_hash(p) for a, p in effective.items()},
              "outgoing_packet_sha256": {a: packet_hash(p) for a, p in outgoing.items()},
              "outgoing_field": {a: "R" if a in COPY_ARMS else "Q" for a in ARMS},
              "birth_sha256": {a: base.state_digest(s) for a, s in states.items()},
              "development_sha256": {a: split.development_digest(tr) for a, tr in developed.items()},
              "development_checks": {a: {k: tr[k] for k in ("gates", "accumulator_errors", "carry_errors")} for a, tr in developed.items()},
              "replay_received_packet_sha256": packet_hash(replay_packet), "replay_outgoing_packet_sha256": packet_hash(replay_outgoing),
              "replay_development_sha256": split.development_digest(replay),
              "rng_initial_sha256": replay["rng_initial_sha256"], "rng_final_sha256": replay["rng_final_sha256"],
              "summaries": summaries, "rows": rows}
    return record, outgoing, replay_outgoing, developed


def terminal(context: dict, packets: dict, newborn: dict, replay_packet: bytes) -> tuple[dict, dict]:
    cfg, zero = context["config"], serialize(np.zeros_like(newborn["R"]))
    references = {a: zero if donor is None else packets[donor] for a, donor in PROBE_DONORS.items()}
    assays = {a: split.probe(context, newborn, birth(newborn, p)["R"], cfg.generations, off=a in ("q_split_off", "zero_off")) for a, p in references.items()}
    replay = split.probe(context, newborn, birth(newborn, replay_packet)["R"], cfg.generations)
    rows = {a: split.measure(context, tr) for a, tr in assays.items()}
    summaries = {a: common.summarize(r) for a, r in rows.items()}
    gates = {"fresh_body_and_ema": all(np.array_equal(tr["snapshots"][0][k], newborn[k]) for tr in assays.values() for k in ("V", "ema")),
             "reference_link_and_held": all(serialize(s["R"]) == references[a] for a, tr in assays.items() for s in tr["snapshots"].values()),
             "all_assay_gates": all(all(tr["gates"].values()) for tr in assays.values()),
             "off_exact_alias": all(np.array_equal(assays["q_split_off"]["snapshots"][t][k], assays["zero_off"]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema")),
             "off_reset_and_off_built_chance": all(s["body_accuracy"] == .25 for a in ("q_split_off", "zero_off", "q_reset", "q_reader_off") for s in summaries[a].values()),
             "wrong_is_donor_permutation": all(np.array_equal(assays["q_wrong"]["snapshots"][t][k], chain.permute_message(assays["q_split"]["snapshots"][t][k], cfg.replicates)) for t in cfg.sample_times for k in ("V", "ema", "R")),
             "own_final_Q_replay": base.trajectory_digest(assays["q_split"]) == base.trajectory_digest(replay),
             "matched_streams": all(len({tr[k] for tr in (*assays.values(), replay)}) == 1 for k in ("rng_initial_sha256", "rng_final_sha256"))}
    if not all(gates.values()):
        raise RuntimeError(f"terminal readout failed: {gates}")
    return {"passes": True, "structural_gates": gates, "newborn_sha256": base.state_digest(newborn),
            "received_packet_sha256": {a: packet_hash(p) for a, p in references.items()},
            "probe_sha256": {a: base.trajectory_digest(tr) for a, tr in assays.items()},
            "replay_received_packet_sha256": packet_hash(replay_packet), "replay_probe_sha256": base.trajectory_digest(replay),
            "summaries": summaries, "rows": rows}, assays


def lineage(context: dict, seed_packet: bytes, newborns: list[dict], root: Path | None = None,
            output: Path | None = None) -> dict:
    cfg = context["config"]
    if len(newborns) != cfg.generations:
        raise ValueError("one public naive birth per registered generation required")
    packets = initial_packets(seed_packet, newborns[0], cfg.replicates)
    seed_hash, replay_packet = packet_hash(seed_packet), bytes(seed_packet)
    del seed_packet  # Only observer hash and separately advanced arm packets remain.
    records, generation_seconds = [], 0.
    for g, naive in enumerate(newborns, 1):
        anchors = ({a: chain.load_arrays(centered.old_directory(root, context["index"], g) / f"{old}_states.npz") for a, old in ANCHORS.items()} if root else None)
        start = time.monotonic()
        record, packets, replay_packet, developed = generation(context, packets, naive, g, replay_packet, anchors)
        generation_seconds += time.monotonic() - start
        if output is not None:
            directory = output / f"g{g:02d}"
            base.atomic_npz(directory / "newborn.npz", naive, root)
            for a, tr in developed.items():
                base.atomic_npz(directory / f"development_{a}.npz", base.trajectory_arrays(tr) | {"body_scores": tr["body_scores"]}, root)
            atomic_json(directory / "generation.json", record, root)
        records.append({k: v for k, v in record.items() if k != "rows"})
        del developed, record  # Lifetime maps are never the next birth's inputs.
    start = time.monotonic()
    readout, assays = terminal(context, packets, newborns[-1], replay_packet)
    terminal_seconds = time.monotonic() - start
    if output is not None:
        for a, tr in assays.items():
            base.atomic_npz(output / "terminal" / f"probe_{a}.npz", base.trajectory_arrays(tr), root)
        atomic_json(output / "terminal" / "readout.json", readout, root)
    result = {"tissue": context["index"], "passes": all(r["passes"] for r in records) and readout["passes"],
              "seed_packet_sha256": seed_hash, "generations": records,
              "terminal": {k: v for k, v in readout.items() if k != "rows"},
              "generation_seconds": generation_seconds, "terminal_seconds": terminal_seconds}
    if output is not None:
        atomic_json(output / "lineage.json", result, root)
    return result


def classify(results: list[dict], structural=True) -> dict:
    if (not structural or sorted(r["tissue"] for r in results) != list(TISSUES)
            or not all(r["passes"] and [g["generation"] for g in r["generations"]] == list(range(1, CONFIG.generations+1)) and all(g["passes"] for g in r["generations"]) and r["terminal"]["passes"] for r in results)):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    ordered = sorted(results, key=lambda r: r["tissue"])
    endpoints = {}
    for i, (name, kind, left, right) in enumerate(ENDPOINTS):
        groups = [r["generations"][-1]["summaries"]["working"] if kind == "generation" else r["terminal"]["summaries"] for r in ordered]
        endpoints[name] = centered.contrast([s[left][str(CONFIG.child_sweeps)]["body_accuracy"] - s[right][str(CONFIG.child_sweeps)]["body_accuracy"] for s in groups], 20260907183001+i)
    protected = np.asarray([[g["summaries"]["working"]["protected_copy"][str(CONFIG.child_sweeps)]["body_accuracy"] for g in r["generations"]] for r in ordered])
    qualified = bool((protected > .25).all() and (protected.mean(axis=0) >= .75).all())
    label = ("NO_QUALIFIED_PROTECTED_REFERENCE_CONTROL" if not qualified else
             "QUALIFIED_TWELVE_GENERATION_REPLACEMENT" if all(c["supported"] for c in endpoints.values()) else "NO_QUALIFIED_REPLACEMENT_LEAD")
    return {"label": label, "co_primary_G12": endpoints, "protected_control_qualified": qualified,
            "protected_control_per_tissue_generation": protected.tolist()}


def qualify_source(root: Path) -> dict:
    upstream = split.qualify_source(root)
    source, audit, run = root / "outputs" / SOURCE_ID, root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1", root / "runs" / SOURCE_ID
    status, audited = json.loads((run / "STATUS.json").read_text()), json.loads((audit / "rescore.json").read_text())
    maps = [chain.manifest_hashes(d / n) for d in (source, audit) for n in ("input_hashes.sha256", "output_hashes.sha256")]
    scores = np.asarray([[json.loads((centered.old_directory(root, t, g) / "calibration.json").read_text())["positive_accuracy"] for g in range(1, CONFIG.generations+1)] for t in TISSUES])
    gates = {"upstream_qualified": upstream["passes"], "source_complete": status["status"] == "COMPLETE" and status["completed_cleanly"] and (run / "COMPLETE").is_file() and not (run / "FAILED").exists(),
             "source_independent_audit": audited["passes"], "source_hashes": all(base.verify_hashes(h) for h in maps),
             "all_twelve_instruments_qualified": bool((scores > .25).all() and (scores.mean(axis=0) >= .75).all())}
    if not all(gates.values()):
        raise RuntimeError(f"replacement source qualification failed: {gates}")
    return {"passes": True, "gates": gates, "reused_positive_accuracy": scores.tolist()}


def input_paths(root: Path) -> list[Path]:
    workspace = Path(__file__).resolve().parents[2]
    paths = [Path(__file__).resolve(), workspace / "tests/test_l17_replacement_chain.py", workspace / "scripts/run_l17_replacement_chain.sh",
             workspace / "scripts/audit_l17_replacement_chain_outputs.py", workspace / "protocols/L17_REPLACEMENT_CHAIN_V1.md",
             workspace / "reviews/L17_READ_WRITE_SPLIT_2026-09-07.md", workspace / "RUN_POLICY.md"]
    for directory in (root / "outputs" / SOURCE_ID, root / "outputs" / f"{SOURCE_ID}_independent_rescore_v1"):
        for name in ("input_hashes.sha256", "output_hashes.sha256"):
            path = directory / name
            paths.append(path)
            paths.extend(Path(p) for p in chain.manifest_hashes(path))
    paths.extend(root / "runs" / SOURCE_ID / n for n in ("STATUS.json", "COMPLETE", "MANIFEST.json"))
    return sorted(set(paths))


def disk_preflight(root: Path) -> dict:
    free = shutil.disk_usage(root).free
    return {"free_bytes": free, "estimated_output_bytes": 2*1024**3, "safety_margin_bytes": 1024**3, "passes": free >= 3*1024**3}


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("cannot alter prepared benchmark")
    runtime, source = base.runtime(), qualify_source(root)
    if not runtime["passes"] or not disk_preflight(root)["passes"]:
        raise RuntimeError("benchmark runtime/storage gate")
    cfg = replace(CONFIG, generations=2, replicates=2, settle_sweeps=8, imprint_sweeps=32, render_sweeps=32, child_sweeps=32, sample_times=(0, 8, 32))
    context = base.make_context(20043, cfg)
    seed = serialize(base.teach_parent(context)["after_render"]["R"])
    newborns = [base.naive_body(context, chain.phase(g, "fresh_body_birth")) for g in range(1, cfg.generations+1)]
    start = time.monotonic()
    result = lineage(context, seed, newborns)
    elapsed = time.monotonic() - start
    overhead = max(0., elapsed - result["generation_seconds"] - result["terminal_seconds"])
    serial = (result["generation_seconds"] + overhead) * CONFIG.generations / cfg.generations + result["terminal_seconds"]
    projection = serial * CONFIG.replicates / cfg.replicates * CONFIG.child_sweeps / cfg.child_sweeps * math.ceil(len(TISSUES)/WORKERS) * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "effect_sizes_not_reported": True,
              "disposable_tissue": 20043, "config": asdict(cfg), "runtime": runtime, "source_qualification": source,
              "measured_seconds": elapsed, "generation_seconds": result["generation_seconds"], "terminal_seconds": result["terminal_seconds"], "overhead_seconds": overhead,
              "projected_seconds_four_workers": projection, "safety_multiplier": 1.75, "must_detach": projection > 600,
              "all_structural_gates_pass": result["passes"], "input_sha256": {str(p): sha256_file(p) for p in input_paths(root)}}
    atomic_json(benchmark_path(root), record, root)
    print(json.dumps({k: v for k, v in record.items() if k != "input_sha256"}, indent=2), flush=True)
    return record


def contract() -> dict:
    return {"run_id": RUN_ID, "config": asdict(CONFIG), "tissues": list(TISSUES), "arms": list(ARMS), "probes": list(PROBES),
            "workers": WORKERS, "registered_lives": REGISTERED_LIVES, "replay_lives": REPLAY_LIVES,
            "packet_bytes_per_world": 2048, "renewing_generations": 12, "terminal_nonrenewing_readouts": 1}


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
    manifest = contract() | {"prepared_utc": utc_now(), "input_sha256": hashes, "contract_digest": canonical_digest(hashes),
                "benchmark": timing, "runtime": runtime, "source_qualification": source, "disk_preflight": disk,
                "environment": environment_manifest(), "repository_head": git_head(Path(__file__).resolve().parents[2]), "law_verdict_changes": 0}
    atomic_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest([Path(p) for p in hashes], output / "input_hashes.sha256", root)
    atomic_json(run / "STATUS.json", {"status": "PREPARED", "run_id": RUN_ID, "updated_utc": utc_now()}, root)
    return manifest


def verify_prepared(root: Path) -> dict:
    run = root / "runs" / RUN_ID
    manifest, status = json.loads((run / "MANIFEST.json").read_text()), json.loads((run / "STATUS.json").read_text())
    if (status["status"] != "PREPARED" or not base.verify_hashes(manifest["input_sha256"])
            or manifest["contract_digest"] != canonical_digest(manifest["input_sha256"])
            or set(manifest["input_sha256"]) != {str(p) for p in input_paths(root)+[benchmark_path(root)]}
            or any(canonical_digest(manifest.get(k)) != canonical_digest(v) for k, v in contract().items())
            or (run / "COMPLETE").exists() or (run / "FAILED").exists()):
        raise RuntimeError("not uniquely prepared or contract changed")
    return manifest


def launch_detached(root: Path) -> dict:
    if not (root / "runs" / RUN_ID).exists():
        prepare(root)
    manifest, run = verify_prepared(root), root / "runs" / RUN_ID
    (run / "LAUNCH.lock").mkdir()
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{kind}.log" for kind in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l17_replacement_chain", "--external-root", str(root), "--run"]
    with stdout.open("xb") as out_handle, stderr.open("xb") as err_handle:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                                   stdout=out_handle, stderr=err_handle, start_new_session=True)
    record = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(), "command": command, "stdout_log": str(stdout),
              "stderr_log": str(stderr), "status": str(run / "STATUS.json"), "complete": str(run / "COMPLETE"), "failed": str(run / "FAILED"),
              "estimated_seconds": manifest["benchmark"]["projected_seconds_four_workers"], "polling_owner": "user"}
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    atomic_json(run / "LAUNCH.json", record, root)
    print(json.dumps(record, indent=2), flush=True)
    return record  # Deliberately no poll, wait or post-launch status read.


def worker(tissue: int, root_text: str) -> dict:
    root = external_root(root_text)
    if not base.runtime()["passes"]:
        raise RuntimeError("worker runtime gate")
    context = base.make_context(tissue, CONFIG)
    seed = serialize(chain.parent_input(root, context)["R"])
    newborns = [load_newborn(root, context, g) for g in range(1, CONFIG.generations+1)]
    result = lineage(context, seed, newborns, root, root / "outputs" / RUN_ID / f"tissue_{tissue}")
    print(f"tissue {tissue}: twelve replacements and terminal readout complete", flush=True)
    return result


def report(study: dict) -> str:
    lines = ["# L17 replacement chain", "", f"Run: `{RUN_ID}`.", "", f"Result: `{study['classification']['label']}`.", "",
             "Twelve fresh-body replacements plus one non-renewing terminal Q12 readout. Protected-copy is storage, not renewal.", "",
             "| G | Split body | Split Q | Coupled Q-only body | Native carry body | Protected body | Reset body |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for g in range(CONFIG.generations):
        selected = [r["generations"][g]["summaries"] for r in study["results"]]
        values = [np.mean([s[kind][a][str(CONFIG.child_sweeps)][metric] for s in selected]) for kind, a, metric in (
            ("working", "split_replace", "body_accuracy"), ("candidate", "split_replace", "reference_accuracy"),
            ("working", "coupled_replace", "body_accuracy"), ("working", "native_carry", "body_accuracy"),
            ("working", "protected_copy", "body_accuracy"), ("working", "split_reset", "body_accuracy"))]
        lines.append(f"| {g+1} | " + " | ".join(f"{v:.6f}" for v in values) + " |")
    lines.extend(["", "## Terminal Q12 readout", ""])
    for a in PROBES:
        value = np.mean([r["terminal"]["summaries"][a][str(CONFIG.child_sweeps)]["body_accuracy"] for r in study["results"]])
        lines.append(f"- {a}: {value:.6f}")
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
        if not runtime["passes"] or not disk_preflight(root)["passes"]:
            raise RuntimeError("run runtime/storage gate")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        atomic_json(run / "STATUS.json", {"status": "RUNNING", "completed_tissues": 0, "updated_utc": utc_now()}, root)
        collected = []
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as executor:
            futures = [executor.submit(worker, t, str(root)) for t in TISSUES]
            for future in as_completed(futures):
                collected.append(future.result())
                atomic_json(run / "STATUS.json", {"status": "RUNNING", "completed_tissues": len(collected), "updated_utc": utc_now()}, root)
        collected.sort(key=lambda r: r["tissue"])
        gates = {"runtime": runtime["passes"], "source_qualification": source["passes"], "all_tissues_present": [r["tissue"] for r in collected] == list(TISSUES),
                 "all_structural_gates": all(r["passes"] and all(all(g["structural_gates"].values()) for g in r["generations"]) and all(r["terminal"]["structural_gates"].values()) for r in collected),
                 "input_hashes_unchanged": base.verify_hashes(manifest["input_sha256"])}
        classification = classify(collected, all(gates.values()))
        study = {"run_id": RUN_ID, "generated_utc": utc_now(), "config": asdict(CONFIG), "runtime": runtime, "results": collected,
                 "classification": classification, "completion_gates": gates, "completed_cleanly": all(gates.values()),
                 "scientific_lives": REGISTERED_LIVES, "replay_lives": REPLAY_LIVES, "elapsed_seconds": time.monotonic()-start, "law_verdict_changes": 0}
        atomic_json(output / "replacement_chain.json", study, root)
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
