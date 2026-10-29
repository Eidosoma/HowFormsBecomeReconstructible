"""Twelve-boundary, same-panel persistence follow-up on the original R sheet.

Frozen one-boundary apparatus and historical engines are imported read-only.
Fresh-R-only lineages, fragment lineages and external ancestor rescue are
deliberately distinct interventions. Generated artifacts are external only.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict, dataclass
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
from .io import (atomic_json, atomic_text, canonical_digest, environment_manifest,
                 external_root, git_head, sha256_file, utc_now, write_hash_manifest)


RUN_ID = "l17_r_channel_twelve_boundary_v1_attempt1"
TISSUES, WORKERS = base.TISSUES, 4
ARMS = ("fresh_renew", "fresh_reset", "fresh_wrong_seed", "fresh_ancestor_rescue",
        "fresh_reader_off", "fresh_reset_reader_off", "fragment_renew",
        "fragment_reset", "fragment_ancestor_rescue")
CAL_ARMS = ("injected", "injected_reader_off")
ANCHOR_ARMS = dict(zip(ARMS, ("copy", "reset", "wrong", "copy", "copy_reader_off",
                             "reset_reader_off", "fragment_copy", "fragment_reset", "fragment_copy")))


@dataclass(frozen=True)
class ChainConfig(base.ExperimentConfig):
    sample_times: tuple[int, ...] = (0, 50, 1000)
    generations: int = 12


CONFIG = ChainConfig()
REGISTERED_LIVES = len(TISSUES) * 4 * CONFIG.replicates * CONFIG.generations * (len(ARMS) + 2)
REPLAY_LIVES = len(TISSUES) * 4 * CONFIG.replicates * CONFIG.generations


def phase(generation: int, event: str) -> str:
    if generation < 1:
        raise ValueError("generations begin at one")
    return event if generation == 1 else f"twelve_boundary_v1:g{generation:02d}:{event}"


def load_arrays(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as loaded:
        return {k: loaded[k].copy() for k in loaded.files}


def old_directory(root: Path, tissue: int) -> Path:
    return root / "outputs" / base.RUN_ID / f"tissue_{tissue}"


def parent_input(root: Path, context: dict) -> dict:
    directory = old_directory(root, context["index"])
    arrays = load_arrays(directory / "parent_states.npz")
    stages = {s: {k: arrays[f"{s}_{k}"] for k in ("V", "ema", "R")}
              for s in ("before_instruction", "after_instruction", "after_render")}
    recorded = json.loads((directory / "acquired.json").read_text())
    if canonical_digest({k: base.state_digest(s) for k, s in stages.items()}) != recorded["parent_sha256"]:
        raise RuntimeError("immutable parent reconstruction failed")
    return stages["after_render"]


def newborn(context: dict, generation: int, source_root: Path | None = None) -> dict:
    if generation == 1 and source_root is not None:
        directory = old_directory(source_root, context["index"])
        arrays = load_arrays(directory / "newborn.npz")
        body = {k: arrays[f"newborn_{k}"] for k in ("V", "ema", "R")}
        record = json.loads((directory / "calibration.json").read_text())
        if (base.state_digest(body) != record["newborn_sha256"]
                or not np.array_equal(arrays["theta"], context["theta"])
                or not np.array_equal(arrays["codes"], context["codes"])):
            raise RuntimeError("immutable newborn/rulebook reconstruction failed")
        return body
    return base.naive_body(context, phase(generation, "fresh_body_birth"))


def permute_message(array: np.ndarray, replicates: int) -> np.ndarray:
    return np.roll(array.reshape(4, replicates, *array.shape[1:]), -1, axis=0).reshape(array.shape).copy()


def fission(context: dict, parent: dict, generation: int) -> tuple[np.ndarray, np.ndarray]:
    rng = base.MessageCoupledRNG(context["index"], phase(generation, "fragment_boundary"), context["config"].replicates)
    preview = deepcopy(rng)
    v, tissue = parent["V"], context["tissue"]
    axes, sides = preview.integers(0, 2, len(v)), preview.integers(0, 2, len(v))
    fresh = np.ones_like(v, dtype=bool)
    for b, (axis, side) in enumerate(zip(axes, sides)):
        if axis == 0:
            fresh[b, slice(0, tissue.height // 2) if side == 0 else slice(tissue.height // 2, None), :] = False
        else:
            fresh[b, :, slice(0, tissue.width // 2) if side == 0 else slice(tissue.width // 2, None)] = False
    return context["api"]["fission"](v.copy(), tissue, rng), fresh


def birth(context: dict, arm: str, parent: dict, ancestor: dict, body: dict, generation: int) -> tuple[dict, np.ndarray | None]:
    if arm not in ARMS:
        raise ValueError("unregistered arm")
    state, fresh = base.state_copy(body), None
    if arm.startswith("fragment"):
        fragment, fresh = fission(context, parent, generation)
        state["V"], state["ema"] = fragment, fragment.copy()
    if "reset" in arm:
        reference = body["R"]
    elif arm.endswith("ancestor_rescue"):
        reference = ancestor["R"]
    elif arm == "fresh_wrong_seed" and generation == 1:
        reference = permute_message(parent["R"], context["config"].replicates)
    else:
        reference = parent["R"]
    state["R"] = reference.copy()
    return state, fresh


def anchor_matches(root: Path, tissue: int, arm: str, trajectory: dict) -> bool:
    original = load_arrays(old_directory(root, tissue) / f"{ANCHOR_ARMS.get(arm, arm)}_states.npz")
    return all(np.array_equal(value, original[f"s{t}_{k}"])
               for t, state in trajectory["snapshots"].items() for k, value in state.items())


def masked_measure(field: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict:
    count = int(mask.sum())
    return {"cells": count, "metrics": base.measure_field(field[mask], target[mask]) if count else None}


def measurements(context: dict, trajectory: dict, ancestor: dict | None = None,
                 parent: dict | None = None, fresh=None, counts=None) -> list[dict]:
    rows = base.trajectory_rows(context, trajectory)
    for row in rows:
        i = row["message"] * context["config"].replicates + row["replicate"]
        v = trajectory["snapshots"][row["sweep"]]["V"][i]
        scores = np.asarray(row["reference_scores"])
        row["reference_true_margin"] = float(scores[row["message"]] - np.delete(scores, row["message"]).max())
        row["wrong_donor_reference_accuracy"] = row["reference_probabilities"][(row["message"] + 1) % 4]
        for name, target in (("fixed_ancestor", ancestor), ("immediate_parent", parent)):
            if target is not None:
                row[name] = base.measure_field(v, target["V"][i])
                if fresh is not None:
                    for suffix, mask in (("newly_regrown", fresh[i]), ("regrown1", counts[i] >= 1), ("regrown2", counts[i] >= 2)):
                        row[f"{name}_{suffix}"] = masked_measure(v, target["V"][i], mask)
        if fresh is not None:
            row["intended_newly_regrown"] = masked_measure(v, context["codes"][row["message"]], fresh[i])
    return rows


def summaries(rows: list[dict]) -> dict:
    result = base.summarize_rows(rows)
    for t, item in result.items():
        selected = [r for r in rows if r["sweep"] == int(t)]
        for key in ("reference_rms", "reference_true_margin", "wrong_donor_reference_accuracy"):
            item[key] = float(np.mean([r[key] for r in selected]))
        for key in ("intended_pattern", "fixed_ancestor", "immediate_parent"):
            if key in selected[0]:
                item[key] = {metric: float(np.mean([r[key][metric] for r in selected])) for metric in selected[0][key]}
        for name in ("fixed_ancestor", "immediate_parent"):
            for suffix in ("newly_regrown", "regrown1", "regrown2"):
                key = f"{name}_{suffix}"
                if key in selected[0]:
                    valid = [r[key]["metrics"] for r in selected if r[key]["cells"]]
                    item[key] = {"valid_worlds": len(valid), "metrics": {
                        m: float(np.mean([v[m] for v in valid])) for m in valid[0]} if valid else None}
    return result


def calibration_chain(context: dict, root: Path | None = None, output: Path | None = None) -> tuple[dict, dict]:
    cfg = context["config"]
    records, bodies = [], {}
    for generation in range(1, cfg.generations + 1):
        body = newborn(context, generation, root)
        initial = base.state_copy(body)
        initial["R"] = np.repeat(context["codes"], cfg.replicates, axis=0) * 3.
        trajectories = {arm: base.simulate(context, initial, phase(generation, "child_development"), cfg.child_sweeps,
                         sample_times=cfg.sample_times, rho=0., c_m=0. if arm.endswith("reader_off") else None)
                        for arm in CAL_ARMS}
        rows = {a: measurements(context, tr) for a, tr in trajectories.items()}
        summary = {a: summaries(r) for a, r in rows.items()}
        gates = {
            "newborn_message_independent": all(base.message_independent(a, cfg.replicates) for a in body.values()),
            "reader_off_message_independent": all(base.message_independent(s["V"], cfg.replicates) for s in trajectories["injected_reader_off"]["snapshots"].values()),
            "reader_off_exact_chance": all(s["body_accuracy"] == .25 for s in summary["injected_reader_off"].values()),
            "reference_held_exact": all(np.array_equal(s["R"], initial["R"]) for tr in trajectories.values() for s in tr["snapshots"].values()),
            "streams_match": len({tr["rng_final_sha256"] for tr in trajectories.values()}) == 1,
            "G1_anchor": generation != 1 or root is None or all(anchor_matches(root, context["index"], a, tr) for a, tr in trajectories.items()),
        }
        if not all(gates.values()):
            raise RuntimeError(f"calibration structural failure: {gates}")
        record = {"generation": generation, "structural_gates": gates, "passes": True, "summaries": summary,
                  "positive_accuracy": summary["injected"][str(cfg.child_sweeps)]["body_accuracy"], "newborn_sha256": base.state_digest(body)}
        if output is not None:
            directory = output / f"g{generation:02d}"
            base.atomic_npz(directory / "newborn.npz", body, root)
            for arm, tr in trajectories.items():
                base.atomic_npz(directory / f"{arm}_states.npz", base.trajectory_arrays(tr), root)
            atomic_json(directory / "calibration.json", record | {"rows": rows}, root)
        else:
            bodies[generation] = body
        records.append(record)
    result = {"tissue": context["index"], "generations": records, "passes": all(r["passes"] for r in records)}
    if output is not None:
        atomic_json(output / "calibration.json", result, root)
    return result, bodies


def calibration_qualified(results: list[dict]) -> bool:
    if (sorted(r["tissue"] for r in results) != list(TISSUES)
            or not all(r["passes"] and all(g["passes"] for g in r["generations"])
                       and [g["generation"] for g in r["generations"]] == list(range(1, CONFIG.generations + 1)) for r in results)):
        return False
    for generation in range(CONFIG.generations):
        selected = [r["generations"][generation] for r in results]
        if not (all(r["passes"] and r["positive_accuracy"] > .25 for r in selected)
                and float(np.mean([r["positive_accuracy"] for r in selected])) >= .75):
            return False
    return True


def lineage_chain(context: dict, ancestor: dict, bodies: dict | None = None,
                  root: Path | None = None, output: Path | None = None) -> dict:
    cfg = context["config"]
    parents = {a: base.state_copy(ancestor) for a in ARMS}
    replay_parent = base.state_copy(ancestor)
    ancestor_hash = base.state_digest(ancestor)
    counts = np.zeros_like(ancestor["V"], dtype=np.int32)
    records, stream_hashes = [], []
    for generation in range(1, cfg.generations + 1):
        directory = output / f"g{generation:02d}" if output is not None else None
        body = load_arrays(directory / "newborn.npz") if directory else base.state_copy(bodies[generation])
        body_hash = base.state_digest(body)
        if directory:
            cal = json.loads((directory / "calibration.json").read_text())
            if body_hash != cal["newborn_sha256"]:
                raise RuntimeError("calibrated newborn changed")
        states, masks = {}, {}
        for arm in ARMS:
            states[arm], masks[arm] = birth(context, arm, parents[arm], ancestor, body, generation)
        fresh = masks["fragment_renew"]
        counts += fresh
        reference_links = {}
        for arm in ARMS:
            if "reset" in arm:
                source, expected = "naive_newborn", body["R"]
            elif arm.endswith("ancestor_rescue"):
                source, expected = "external_ancestor_backup", ancestor["R"]
            elif arm == "fresh_wrong_seed" and generation == 1:
                source, expected = "G0_wrong_donor", permute_message(ancestor["R"], cfg.replicates)
            else:
                source, expected = "immediate_parent", parents[arm]["R"]
            reference_links[arm] = {"source": source, "expected_sha256": base.array_digest(expected),
                                   "birth_sha256": base.array_digest(states[arm]["R"])}
        parent_hashes = {a: base.state_digest(p) for a, p in parents.items()}
        initial_hashes = {a: base.state_digest(s) for a, s in states.items()}
        trajectories = {a: base.simulate(context, states[a], phase(generation, "child_development"), cfg.child_sweeps,
                        sample_times=cfg.sample_times, c_m=0. if a.endswith("reader_off") else None) for a in ARMS}
        replay_birth, _ = birth(context, "fresh_renew", replay_parent, ancestor, body, generation)
        replay = base.simulate(context, replay_birth, phase(generation, "child_development"), cfg.child_sweeps, sample_times=cfg.sample_times)
        rows = {a: measurements(context, tr, ancestor, parents[a], masks[a], counts if masks[a] is not None else None)
                for a, tr in trajectories.items()}
        summary = {a: summaries(r) for a, r in rows.items()}
        gates = {
            "ancestor_unchanged": base.state_digest(ancestor) == ancestor_hash,
            "parents_unchanged": parent_hashes == {a: base.state_digest(p) for a, p in parents.items()},
            "newborn_unchanged": base.state_digest(body) == body_hash,
            "birth_states_unchanged": initial_hashes == {a: base.state_digest(s) for a, s in states.items()},
            "reference_links_exact": all(r["expected_sha256"] == r["birth_sha256"] for r in reference_links.values()),
            "fresh_births_match": all(np.array_equal(states[a][k], body[k]) for a in ARMS[:6] for k in ("V", "ema")),
            "fragment_masks_match": all(np.array_equal(masks[a], fresh) for a in ARMS[6:]),
            "native_half_fission": bool(np.all(fresh.sum(axis=(1, 2)) == 128)),
            "G1_fragment_births_match": generation != 1 or all(np.array_equal(states[a]["V"], states["fragment_renew"]["V"]) for a in ARMS[6:]),
            "streams_match": all(len({tr[k] for tr in trajectories.values()}) == 1 for k in ("rng_initial_sha256", "rng_final_sha256")),
            "reader_off_alias": all(np.array_equal(trajectories["fresh_reader_off"]["snapshots"][t][k], trajectories["fresh_reset_reader_off"]["snapshots"][t][k]) for t in cfg.sample_times for k in ("V", "ema")),
            "null_message_independent": all(base.message_independent(trajectories[a]["snapshots"][t]["V"], cfg.replicates) for a in ("fresh_reset", "fresh_reader_off", "fresh_reset_reader_off") for t in cfg.sample_times),
            "null_exact_chance": all(summary[a][str(t)]["body_accuracy"] == .25 for a in ("fresh_reset", "fresh_reader_off", "fresh_reset_reader_off") for t in cfg.sample_times),
            "wrong_is_single_donor_permutation": all(np.array_equal(trajectories["fresh_wrong_seed"]["snapshots"][t][k], permute_message(trajectories["fresh_renew"]["snapshots"][t][k], cfg.replicates)) for t in cfg.sample_times for k in ("V", "ema", "R")),
            "full_chain_exact_replay": base.trajectory_digest(trajectories["fresh_renew"]) == base.trajectory_digest(replay),
            "G1_anchor": generation != 1 or root is None or all(anchor_matches(root, context["index"], a, tr) for a, tr in trajectories.items()),
        }
        stream_hashes.append(trajectories["fresh_renew"]["rng_initial_sha256"])
        gates["generations_have_distinct_noise"] = len(set(stream_hashes)) == generation
        if not all(gates.values()):
            raise RuntimeError(f"G{generation} lineage structural failure: {gates}")
        record = {"generation": generation, "passes": True, "structural_gates": gates, "summaries": summary,
                  "reference_links": reference_links, "parent_sha256": parent_hashes, "birth_sha256": initial_hashes,
                  "final_sha256": {a: tr["final_sha256"] for a, tr in trajectories.items()},
                  "trajectory_sha256": {a: base.trajectory_digest(tr) for a, tr in trajectories.items()},
                  "reference_changed_in_life": {a: not np.array_equal(states[a]["R"], tr["final"]["R"]) for a, tr in trajectories.items()},
                  "rng_initial_sha256": trajectories["fresh_renew"]["rng_initial_sha256"],
                  "rng_final_sha256": trajectories["fresh_renew"]["rng_final_sha256"]}
        if directory:
            for arm, tr in trajectories.items():
                base.atomic_npz(directory / f"{arm}_states.npz", base.trajectory_arrays(tr), root)
            base.atomic_npz(directory / "regrowth.npz", {"fresh": fresh, "counts": counts}, root)
            atomic_json(directory / "lineage.json", record | {"rows": rows}, root)
            atomic_json(output / "PROGRESS.json", {"generation_complete": generation, "updated_utc": utc_now()}, root)
            print(f"lineage tissue {context['index']}: G{generation} complete", flush=True)
        records.append(record)
        parents = {a: base.state_copy(tr["final"]) for a, tr in trajectories.items()}
        replay_parent = base.state_copy(replay["final"])
    result = {"tissue": context["index"], "generations": records, "passes": all(r["passes"] for r in records), "ancestor_sha256": ancestor_hash}
    if output is not None:
        atomic_json(output / "lineage.json", result, root)
    return result


def contrast(values: list[float], seed_value: int) -> dict:
    values = np.asarray(values)
    draws = np.random.default_rng(seed_value).integers(0, len(values), (10000, len(values)))
    interval = np.quantile(values[draws].mean(axis=1), [.0125, .9875]).tolist()
    positive = int((values > 0).sum())
    return {"tissue_differences": values.tolist(), "mean": float(values.mean()), "positive_tissues": positive,
            "paired_tissue_bootstrap_97_5": interval, "seed": seed_value, "resamples": 10000,
            "supported": interval[0] > 0 and positive >= 6}


def classify(results: list[dict], calibrated: bool, structural=True) -> dict:
    if not structural:
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    if not calibrated:
        return {"label": "INSTRUMENT_NOT_QUALIFIED"}
    if (sorted(r["tissue"] for r in results) != list(TISSUES)
            or not all(r["passes"] and all(g["passes"] for g in r["generations"])
                       and [g["generation"] for g in r["generations"]] == list(range(1, CONFIG.generations + 1)) for r in results)):
        return {"label": "INVALID_STRUCTURAL_FAILURE"}
    endpoints = [r["generations"][-1]["summaries"] for r in sorted(results, key=lambda r: r["tissue"])]
    contrasts = {kind: contrast([s["fresh_renew"][str(CONFIG.child_sweeps)][key] - s["fresh_reset"][str(CONFIG.child_sweeps)][key] for s in endpoints], 20260907171201 + i)
                 for i, (kind, key) in enumerate((("body", "body_accuracy"), ("reference", "reference_accuracy")))}
    flags = tuple(contrasts[k]["supported"] for k in ("body", "reference"))
    label = {(True, True): "BODY_AND_REFERENCE_PERSIST_G12", (False, True): "REFERENCE_ONLY_DETECTED_G12",
             (True, False): "BODY_ONLY_DETECTED_G12", (False, False): "NO_QUALIFIED_G12_MESSAGE_LEAD"}[flags]
    return {"label": label, "co_primary_G12": contrasts}


def manifest_hashes(path: Path) -> dict:
    return {p: digest for digest, p in (line.split("  ", 1) for line in path.read_text().splitlines())}


def qualify_source(root: Path) -> dict:
    run = root / "runs" / base.RUN_ID
    output = root / "outputs" / base.RUN_ID
    rescore = root / "outputs" / f"{base.RUN_ID}_independent_rescore_v1"
    status = json.loads((run / "STATUS.json").read_text())
    audit = json.loads((rescore / "rescore.json").read_text())
    hashes = {**manifest_hashes(output / "input_hashes.sha256"), **manifest_hashes(output / "output_hashes.sha256"),
              **manifest_hashes(rescore / "input_hashes.sha256"), **manifest_hashes(rescore / "output_hashes.sha256")}
    gates = {"source_complete": status["status"] == "COMPLETE" and status["completed_cleanly"] and (run / "COMPLETE").is_file() and not (run / "FAILED").exists(),
             "source_instrument_qualified": status["instrument_qualified"], "independent_audit_passes": audit["passes"],
             "source_and_audit_hashes": base.verify_hashes(hashes)}
    if not all(gates.values()):
        raise RuntimeError(f"source qualification failed: {gates}")
    return {"passes": True, "gates": gates, "verified_files": len(hashes)}


def input_paths(root: Path) -> list[Path]:
    workspace = Path(__file__).resolve().parents[2]
    output = root / "outputs" / base.RUN_ID
    rescore = root / "outputs" / f"{base.RUN_ID}_independent_rescore_v1"
    paths = base.input_paths() + [Path(__file__).resolve(), workspace / "tests/test_l17_r_channel_twelve.py",
        workspace / "scripts/run_l17_r_channel_twelve.sh", workspace / "scripts/audit_l17_r_channel_twelve_outputs.py",
        workspace / "protocols/L17_R_CHANNEL_TWELVE_BOUNDARY_V1.md", workspace / "reviews/L17_R_CHANNEL_ONE_BOUNDARY_2026-09-07.md"]
    for directory in (output, rescore):
        for filename in ("input_hashes.sha256", "output_hashes.sha256"):
            manifest = directory / filename
            paths.append(manifest)
            paths.extend(Path(p) for p in manifest_hashes(manifest))
    paths.extend(root / "runs" / base.RUN_ID / name for name in ("STATUS.json", "COMPLETE", "MANIFEST.json"))
    return sorted(set(paths))


def disk_preflight(root: Path) -> dict:
    free = shutil.disk_usage(root).free
    return {"free_bytes": free, "estimated_output_bytes": 1024**3, "safety_margin_bytes": 1024**3, "passes": free >= 2 * 1024**3}


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("cannot change prepared benchmark")
    runtime, source = base.runtime(), qualify_source(root)
    if not runtime["passes"] or not disk_preflight(root)["passes"]:
        raise RuntimeError("benchmark runtime/storage gate")
    cfg = ChainConfig(replicates=2, generations=3, settle_sweeps=8, imprint_sweeps=32,
                      render_sweeps=32, child_sweeps=32, sample_times=(0, 8, 32))
    context = base.make_context(20012, cfg)
    parent = base.teach_parent(context)["after_render"]
    start = time.monotonic()
    calibration, bodies = calibration_chain(context)
    calibration_seconds = time.monotonic() - start
    start = time.monotonic()
    scientific = lineage_chain(context, parent, bodies)
    lineage_seconds = time.monotonic() - start
    cal_scale = (CONFIG.settle_sweeps + 2 * CONFIG.child_sweeps) / (cfg.settle_sweeps + 2 * cfg.child_sweeps)
    scale = CONFIG.replicates / cfg.replicates * CONFIG.generations / cfg.generations
    projection = math.ceil(len(TISSUES) / WORKERS) * scale * (calibration_seconds * cal_scale + lineage_seconds * CONFIG.child_sweeps / cfg.child_sweeps) * 1.75 + 60
    record = {"run_id": RUN_ID, "measured_utc": utc_now(), "non_scientific": True, "effect_sizes_not_reported": True,
              "disposable_tissue": 20012, "runtime": runtime, "source_qualification": source, "config": asdict(cfg),
              "calibration_seconds": calibration_seconds, "lineage_seconds": lineage_seconds,
              "projected_seconds_four_workers": projection, "safety_multiplier": 1.75, "must_detach": projection > 600,
              "all_structural_gates_pass": calibration["passes"] and scientific["passes"],
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
                "input_sha256": hashes, "contract_digest": canonical_digest(hashes), "benchmark": timing,
                "runtime": runtime, "disk_preflight": disk, "source_qualification": source, "environment": environment_manifest(),
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
    stdout, stderr = [root / "logs" / f"{RUN_ID}.{suffix}.log" for suffix in ("stdout", "stderr")]
    command = [sys.executable, "-m", "laws_confirmation.l17_r_channel_twelve", "--external-root", str(root), "--run"]
    with stdout.open("xb") as out_handle, stderr.open("xb") as err_handle:
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                                   stdout=out_handle, stderr=err_handle, start_new_session=True)
    launch = {"run_id": RUN_ID, "pid": process.pid, "launched_utc": utc_now(), "command": command,
              "stdout_log": str(stdout), "stderr_log": str(stderr), "status": str(run / "STATUS.json"),
              "complete": str(run / "COMPLETE"), "failed": str(run / "FAILED"),
              "estimated_seconds": manifest["benchmark"]["projected_seconds_four_workers"], "polling_owner": "user"}
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    atomic_json(run / "LAUNCH.json", launch, root)
    print(json.dumps(launch, indent=2), flush=True)
    return launch  # No poll, wait, status read or process inspection.


def worker(tissue: int, stage: str, root_text: str) -> dict:
    root = external_root(root_text)
    if not base.runtime()["passes"]:
        raise RuntimeError("worker runtime gate")
    context = base.make_context(tissue, CONFIG)
    output = root / "outputs" / RUN_ID / f"tissue_{tissue}"
    if stage == "calibration":
        return calibration_chain(context, root, output)[0]
    if stage == "lineage":
        return lineage_chain(context, parent_input(root, context), root=root, output=output)
    raise ValueError("unregistered stage")


def report(study: dict) -> str:
    lines = ["# L17 twelve-boundary original-sheet R channel", "", f"Run: `{RUN_ID}`.", "",
             f"Result: `{study['classification']['label']}`.", "",
             "Same eight-tissue persistence follow-up; not independent new-tissue replication.",
             "Fresh-body, fragment and external ancestor-backup routes are not interchangeable.", ""]
    if study["lineage_results"]:
        lines += ["| G | Renew V | Reset V | Renew R | Reset R | Ancestor rescue V | Fragment renew V | Fragment reset V |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for g in range(CONFIG.generations):
            selections = [r["generations"][g]["summaries"] for r in study["lineage_results"]]
            vals = [np.mean([s[a][str(CONFIG.child_sweeps)][k] for s in selections]) for a, k in (
                ("fresh_renew", "body_accuracy"), ("fresh_reset", "body_accuracy"),
                ("fresh_renew", "reference_accuracy"), ("fresh_reset", "reference_accuracy"),
                ("fresh_ancestor_rescue", "body_accuracy"), ("fragment_renew", "body_accuracy"), ("fragment_reset", "body_accuracy"))]
            lines.append(f"| {g + 1} | " + " | ".join(f"{v:.6f}" for v in vals) + " |")
    lines += ["", "No numbered-law verdict changes automatically; null results are not zero capacity.", ""]
    return "\n".join(lines)


def run_study(root: Path) -> int:
    manifest = verify_prepared(root)
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    if manifest["benchmark"]["must_detach"] and not (run / "LAUNCH.lock").is_dir():
        raise RuntimeError("benchmark exceeds ten minutes: detached launch required")
    (run / "EXECUTION.lock").mkdir()
    start = time.monotonic()
    try:
        runtime, source = base.runtime(), qualify_source(root)
        if not runtime["passes"] or not disk_preflight(root)["passes"]:
            raise RuntimeError("run runtime/storage gate")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        collected = {"calibration": [], "lineage": []}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn")) as executor:
            for stage in collected:
                if stage == "lineage" and not calibration_qualified(collected["calibration"]):
                    break
                atomic_json(run / "STATUS.json", {"status": "RUNNING", "phase": stage, "completed_tissues_in_phase": 0, "updated_utc": utc_now()}, root)
                futures = [executor.submit(worker, tissue, stage, str(root)) for tissue in TISSUES]
                for future in as_completed(futures):
                    collected[stage].append(future.result())
                    atomic_json(run / "STATUS.json", {"status": "RUNNING", "phase": stage, "completed_tissues_in_phase": len(collected[stage]), "updated_utc": utc_now()}, root)
        for records in collected.values():
            records.sort(key=lambda r: r["tissue"])
        qualified = calibration_qualified(collected["calibration"])
        gates = {"runtime": runtime["passes"], "source_qualified": source["passes"],
                 "all_calibration_structural": len(collected["calibration"]) == len(TISSUES) and all(r["passes"] for r in collected["calibration"]),
                 "lineages_correctly_gated": len(collected["lineage"]) == (len(TISSUES) if qualified else 0),
                 "all_lineage_structural": all(r["passes"] for r in collected["lineage"]),
                 "input_hashes_unchanged": base.verify_hashes(manifest["input_sha256"])}
        classification = classify(collected["lineage"], qualified, all(gates.values()))
        study = {"run_id": RUN_ID, "generated_utc": utc_now(), "config": asdict(CONFIG), "runtime": runtime,
                 "instrument_qualified": qualified, "calibration_results": collected["calibration"], "lineage_results": collected["lineage"],
                 "classification": classification, "completion_gates": gates, "completed_cleanly": all(gates.values()),
                 "child_lives_run_excluding_replays": REGISTERED_LIVES if qualified else len(TISSUES) * CONFIG.generations * 4 * CONFIG.replicates * 2,
                 "replay_lives": REPLAY_LIVES if qualified else 0, "elapsed_seconds": time.monotonic() - start, "numbered_law_verdict_changes": 0}
        atomic_json(output / "r_channel_twelve.json", study, root)
        atomic_text(output / "audit.md", report(study), root)
        paths = sorted(p for p in output.rglob("*") if p.is_file() and p.name != "output_hashes.sha256")
        write_hash_manifest(paths, output / "output_hashes.sha256", root)
        output_pass = base.verify_hashes(manifest_hashes(output / "output_hashes.sha256"))
        success = study["completed_cleanly"] and output_pass
        status = {"run_id": RUN_ID, "status": "COMPLETE" if success else "FAILED_GATES", "completed_cleanly": success,
                  "classification": classification["label"], "completed_utc": utc_now(), "elapsed_seconds": time.monotonic() - start,
                  "instrument_qualified": qualified, "workers": WORKERS, "cpu_affinity": runtime["cpu_affinity"],
                  "child_lives_run_excluding_replays": study["child_lives_run_excluding_replays"], "replay_lives": study["replay_lives"],
                  "output_manifest_self_verifies": output_pass}
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
