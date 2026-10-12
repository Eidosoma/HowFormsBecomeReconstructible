"""Contingency, exposure-state, carrier, and renewal campaign.

The campaign is deliberately one sealed, resumable run.  Its stage gates keep
relational memory separate from durable exposure state and prevent either from
reaching heredity language without transfer and renewal controls.
"""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import os
import platform
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .artifacts import (
    atomic_write_text,
    canonical_json,
    digest,
    read_jsonl,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .atlas import learned_margin, state_from_payload, state_payload
from .ca_bridge import (
    build_codebooks,
    common_damage,
    copy_normalized,
    decode_codec,
    encode_codec,
    norm_matched_random,
    normalized_shuffle,
)
from .engine import JaxBackend, State, run_epoch_schedule
from .renewal import ResourceLedger
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    validate_upstream,
)


RELATIONAL_TASKS = ("10-1-25", "29-0-2", "29-3-3", "23-8-28", "27-1-1")
EXPOSURE_TASKS = ("10-1-32", "26-6-39", "37-10-41", "69-4-16", "204-5-10")
SCHEDULES = ("coincident", "cs_leading", "ucs_leading", "blocked", "shuffled")
CONTINGENCY_CONTROLS = ("blocked", "shuffled", "naive", "cs_only", "ucs_only")
TRANSFER_CONTROLS = (
    "intact",
    "matched_background",
    "opposite",
    "inversion",
    "zero",
    "normalized_shuffle",
    "norm_matched_random",
)
LINEAGE_ARMS = (
    "active",
    "passive",
    "erase_g2",
    "rescue_g3",
    "wrong_content",
    "inversion",
    "normalized_shuffle",
    "norm_matched_random",
    "recipient_control",
)


def _sum(values: Sequence[float]) -> float:
    return float(np.sum(np.asarray(values, dtype=float)))


def vector_rms(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(array * array))) if array.size else 0.0


def cosine_alignment(left: Sequence[float], right: Sequence[float]) -> float | None:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator <= 1e-12 or not np.isfinite(denominator):
        return None
    value = float(np.dot(a, b) / denominator)
    return value if np.isfinite(value) else None


def quantile(values: Sequence[float], value: float) -> float | None:
    finite = np.asarray([row for row in values if np.isfinite(float(row))], dtype=float)
    return None if not finite.size else float(np.quantile(finite, value))


def control_median_envelope(
    groups: Mapping[str, Sequence[float]],
) -> tuple[float, dict[str, float | None]]:
    """Return the strictest median absolute response across named controls."""

    medians = {
        str(name): quantile([abs(float(value)) for value in values], 0.5)
        for name, values in groups.items()
    }
    finite = [float(value) for value in medians.values() if value is not None]
    return (max(finite) if finite else math.inf), medians


def axis_score(values: Sequence[float], background: Sequence[float], direction: Sequence[float]) -> float | None:
    x = np.asarray(values, dtype=float)
    origin = np.asarray(background, dtype=float)
    axis = np.asarray(direction, dtype=float)
    denominator = float(np.dot(axis, axis))
    if x.shape != origin.shape or x.shape != axis.shape:
        raise ValueError("axis-score shapes differ")
    if denominator <= 1e-12 or not np.isfinite(denominator):
        return None
    result = float(np.dot(x - origin, axis) / denominator)
    return result if np.isfinite(result) else None


def bipolar_score(values: Sequence[float], form_a: Sequence[float], form_b: Sequence[float]) -> float | None:
    a = np.asarray(form_a, dtype=float)
    b = np.asarray(form_b, dtype=float)
    return axis_score(values, 0.5 * (a + b), 0.5 * (a - b))


def _seed(config: Mapping[str, Any], *parts: object) -> int:
    payload = "|".join([str(config["experiment_seed"]), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def _stable_rank(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def _validate_schedule(name: str, tokens: Sequence[str]) -> None:
    if len(tokens) != 10 or any(token not in {"B", "C", "U", "-"} for token in tokens):
        raise ValueError(f"invalid schedule template: {name}")
    cs_count = sum(token in {"B", "C"} for token in tokens)
    ucs_count = sum(token in {"B", "U"} for token in tokens)
    if cs_count != 5 or ucs_count != 5:
        raise ValueError(f"schedule {name} does not match five CS and UCS exposures")


def load_contingency_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported contingency schema")
    if config.get("experiment_kind") != "contingency-memory-campaign":
        raise ValueError("not a contingency-memory protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("contingency protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("contingency protocol does not pin the release generator")
    if tuple(config.get("relational_candidate_task_ids", ())) != RELATIONAL_TASKS:
        raise ValueError("relational candidate cohort changed")
    if tuple(config.get("exposure_anchor_task_ids", ())) != EXPOSURE_TASKS:
        raise ValueError("exposure anchor cohort changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("contingency protocol must cap workers at four")
    if not (0 < float(config["soft_wall_seconds"]) < float(config["terminate_wall_seconds"]) < float(config["hard_wall_seconds"]) <= 14400):
        raise ValueError("contingency wall-time contract is invalid")
    if not (0 < float(config["soft_aggregate_cpu_seconds"]) < float(config["hard_aggregate_cpu_seconds"]) <= 57600):
        raise ValueError("contingency aggregate CPU contract is invalid")
    for key, expected in {"delta_t": 0.01, "phase_duration": 2500.0, "epoch_duration": 250.0, "epoch_count": 10, "pulse_count": 5}.items():
        if not math.isclose(float(config.get(key, -1)), expected):
            raise ValueError(f"historical setting differs for {key}")
    if [float(row) for row in config["washout_checkpoints"]] != [2500.0, 12500.0]:
        raise ValueError("washout checkpoint ladder changed")
    templates = config.get("schedule_templates", {})
    if tuple(templates) != SCHEDULES:
        raise ValueError("timing schedule order changed")
    for name, tokens in templates.items():
        _validate_schedule(name, tokens)
    seed_groups = [
        config["timing_discovery"]["seed_indices"],
        config["contingency_validation"]["seed_indices"],
        config["exposure_validation"]["seed_indices"],
        config["two_cue_reversal"]["seed_indices"],
        config["native_transfer"]["seed_indices"],
        config["carrier_dissection"]["discovery_seed_indices"],
        config["carrier_dissection"]["validation_seed_indices"],
        config["active_renewal"]["seed_indices"],
    ]
    flat = [int(seed) for group in seed_groups for seed in group]
    if len(flat) != len(set(flat)):
        raise ValueError("discovery, validation, transfer, and lineage seeds overlap")
    return config


def schedule_exposure_counts(tokens: Sequence[str]) -> dict[str, int]:
    return {
        "cs": sum(token in {"B", "C"} for token in tokens),
        "ucs": sum(token in {"B", "U"} for token in tokens),
        "coincident": sum(token == "B" for token in tokens),
    }


def schedule_stimuli(tokens: Sequence[str], cs: Mapping[int, float], ucs: Mapping[int, float]) -> list[dict[int, float] | None]:
    epochs: list[dict[int, float] | None] = []
    for token in tokens:
        values: dict[int, float] = {}
        if token in {"B", "C"}:
            values.update({int(key): float(value) for key, value in cs.items()})
        if token in {"B", "U"}:
            values.update({int(key): float(value) for key, value in ucs.items()})
        epochs.append(values or None)
    return epochs


def _control_tokens(condition: str) -> list[str]:
    if condition == "naive":
        return ["-"] * 10
    token = "C" if condition == "cs_only" else "U"
    return [token, "-", token, "-", token, "-", token, "-", token, "-"]


def _runtime_manifest() -> dict[str, Any]:
    versions: dict[str, str] = {}
    for package in ("jax", "jaxlib", "numpy", "autodiscjax", "sbmltoodejax"):
        try:
            from importlib.metadata import version

            versions[package] = version(package)
        except Exception:
            versions[package] = "not-installed"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "packages": versions,
    }


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(row) + "\n" for row in records))


def _all_shard_cpu(output: Path) -> float:
    total = 0.0
    root = output / ".shards"
    for path in sorted(root.rglob("*.json")) if root.is_dir() else ():
        try:
            total += float(json.loads(path.read_text(encoding="utf-8")).get("aggregate_cpu_seconds", 0.0))
        except (OSError, TypeError, ValueError):
            continue
    return total


def _parallel(worker: Any, args: list[tuple[Any, ...]], workers: int) -> list[dict[str, Any]]:
    if not args:
        return []
    if workers == 1:
        return [worker(arg) for arg in args]
    context = multiprocessing.get_context("spawn")
    indexed: dict[int, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        futures = {pool.submit(worker, arg): index for index, arg in enumerate(args)}
        for future in as_completed(futures):
            indexed[futures[future]] = future.result()
    return [indexed[index] for index in range(len(args))]


def _merge_shards(output: Path, name: str, shards: Sequence[Mapping[str, Any]], record_key: str = "records") -> list[dict[str, Any]]:
    records = [dict(row) for shard in shards for row in shard.get(record_key, ())]
    ids = [str(row["task_id"]) for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate task IDs while merging {name}")
    _write_jsonl(output / f"{name}.jsonl", records)
    return records


def _verify_parent(path: Path, expected_id: str, hashes: Mapping[str, str]) -> dict[str, Any]:
    verify_checksums(path)
    for name, expected in hashes.items():
        if sha256_file(path / name) != str(expected):
            raise ValueError(f"parent {name} hash mismatch")
    registration = json.loads((path / "registration.json").read_text(encoding="utf-8"))
    state = json.loads((path / "state.json").read_text(encoding="utf-8"))
    if registration.get("experiment_id") != expected_id or state.get("status") != "completed":
        raise ValueError(f"wrong or incomplete parent: {expected_id}")
    return {
        "path": str(path),
        "experiment_id": expected_id,
        "manifest_sha256": sha256_file(path / "SHA256SUMS"),
        "checksum_count": len(verify_checksums(path)),
    }


def validate_parents(config: Mapping[str, Any], atlas: Path, form_run: Path, upstream: Path) -> dict[str, Any]:
    provenance = validate_upstream(upstream, str(config["upstream_commit"]))
    return {
        "upstream": provenance,
        "atlas": _verify_parent(atlas, str(config["atlas_parent_experiment_id"]), config["atlas_parent_hashes"]),
        "form_run": _verify_parent(form_run, str(config["form_parent_experiment_id"]), config["form_parent_hashes"]),
    }


def _calibration_map(atlas: Path) -> dict[str, dict[str, Any]]:
    return {str(row["memory_task_id"]): row for row in read_jsonl(atlas / "calibration.jsonl")}


def _history_map(atlas: Path) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(row["memory_task_id"]), str(row["arm"])): row for row in read_jsonl(atlas / "histories.jsonl")}


def _naive_start(atlas: Path, task_id: str) -> State:
    payload = _history_map(atlas)[(task_id, "naive")]["start"]["state"]
    state = state_from_payload(payload)
    if state is None:
        raise ValueError(f"invalid naive start for {task_id}")
    return state


def _perturb_start(start: State, memory: Any, config: Mapping[str, Any], namespace: str, task_id: str, seed_index: int) -> tuple[State, int]:
    fraction = float(config["contingency_validation"]["initial_perturbation_fraction"])
    seed_value = _seed(config, namespace, task_id, seed_index)
    rng = np.random.Generator(np.random.Philox(seed_value))
    width = np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8)
    y = np.clip(start.y + rng.normal(0.0, fraction, len(start.y)) * width, memory.bounds[:, 0], memory.bounds[:, 1])
    w_scale = np.maximum(np.abs(start.w), 1.0)
    w = start.w + rng.normal(0.0, fraction, len(start.w)) * w_scale
    return State(y, w, start.c.copy(), start.t), seed_value


def residual_audit(config: Mapping[str, Any], atlas: Path, form_run: Path) -> dict[str, Any]:
    calibrations = _calibration_map(atlas)
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in read_jsonl(form_run / "screen.jsonl"):
        grouped.setdefault(str(row["memory_task_id"]), {})[str(row["condition"])] = row
    rows: list[dict[str, Any]] = []
    all_tasks = [*config["relational_candidate_task_ids"], *config["exposure_anchor_task_ids"]]
    for task_id in all_tasks:
        arms = grouped[str(task_id)]
        selected = int(calibrations[str(task_id)]["reconstructed_ucs_bound_index"])
        ucs_a = "low_ucs_only" if selected == 0 else "high_ucs_only"
        ucs_b = "high_ucs_only" if selected == 0 else "low_ucs_only"
        checkpoint_rows: dict[str, Any] = {}
        for key in ("2500", "12500"):
            fp = {arm: np.asarray(value["checkpoints"][key]["fingerprint"], dtype=float) for arm, value in arms.items()}
            residual_a = fp["form_a"] - fp[ucs_a]
            residual_b = fp["form_b"] - fp[ucs_b]
            checkpoint_rows[key] = {
                "residual_a": residual_a,
                "residual_b": residual_b,
                "relational_direction": residual_a - residual_b,
                "relational_rms": vector_rms(residual_a - residual_b),
                "residual_a_rms": vector_rms(residual_a),
                "residual_b_rms": vector_rms(residual_b),
                "low_ucs": fp["low_ucs_only"],
                "high_ucs": fp["high_ucs_only"],
                "exposure_direction": fp["high_ucs_only"] - fp["low_ucs_only"],
            }
        selected_side = "a" if checkpoint_rows["12500"]["residual_a_rms"] >= checkpoint_rows["12500"]["residual_b_rms"] else "b"
        selected_form = "form_a" if selected_side == "a" else "form_b"
        selected_ucs = ucs_a if selected_side == "a" else ucs_b
        references: dict[str, Any] = {}
        for key in ("2500", "12500"):
            references[key] = {
                "background": arms[selected_ucs]["checkpoints"][key]["fingerprint"],
                "direction": checkpoint_rows[key][f"residual_{selected_side}"],
                "form": arms[selected_form]["checkpoints"][key]["fingerprint"],
            }
        rows.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(str(task_id).split("-")[0]),
                "channel_class": "relational" if task_id in config["relational_candidate_task_ids"] else "exposure",
                "reconstructed_ucs_bound_index": selected,
                "selected_side": selected_side,
                "selected_form_condition": selected_form,
                "selected_ucs_condition": selected_ucs,
                "selected_ucs_bound_index": selected if selected_side == "a" else 1 - selected,
                "short_relational_rms": checkpoint_rows["2500"]["relational_rms"],
                "long_relational_rms": checkpoint_rows["12500"]["relational_rms"],
                "relational_direction_cosine": cosine_alignment(checkpoint_rows["2500"]["relational_direction"], checkpoint_rows["12500"]["relational_direction"]),
                "references": references,
                "exposure_reference": {
                    key: {"low": checkpoint_rows[key]["low_ucs"], "high": checkpoint_rows[key]["high_ucs"]}
                    for key in ("2500", "12500")
                },
            }
        )
    return {
        "task_id": "frozen-residual-audit",
        "pass": True,
        "post_hoc_hypothesis_generation": True,
        "threshold_relaxation": False,
        "references": rows,
    }


def _reference_map(audit: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["memory_task_id"]): dict(row) for row in audit["references"]}


def _stimulus_values(memory: Any, ucs_bound: int) -> tuple[dict[int, float], dict[int, float], dict[int, float]]:
    cs = {int(memory.cs_id): float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])}
    ucs = {int(memory.ucs_id): float(memory.bounds[memory.ucs_id, int(ucs_bound)])}
    opposite = {int(memory.ucs_id): float(memory.bounds[memory.ucs_id, 1 - int(ucs_bound)])}
    return cs, ucs, opposite


def _probe_specs(memory: Any, ucs_bound: int, cue2: tuple[int, float] | None = None) -> list[tuple[str, dict[int, float] | None]]:
    cs, ucs, opposite = _stimulus_values(memory, ucs_bound)
    if cue2 is not None:
        other = {int(cue2[0]): float(cue2[1])}
        return [
            ("no_input", None),
            ("cue1", cs),
            ("cue2", other),
            ("ucs", ucs),
            ("cue1_ucs", {**cs, **ucs}),
            ("cue2_ucs", {**other, **ucs}),
        ]
    return [
        ("no_input", None),
        ("cs", cs),
        ("ucs", ucs),
        ("cs_ucs", {**cs, **ucs}),
        ("opposite_ucs", opposite),
        ("cs_opposite_ucs", {**cs, **opposite}),
    ]


def _fingerprint(backend: JaxBackend, memory: Any, state: State, config: Mapping[str, Any], ucs_bound: int, cue2: tuple[int, float] | None = None) -> dict[str, Any]:
    probes: list[dict[str, Any]] = []
    cpu = wall = 0.0
    valid = True
    for name, stimuli in _probe_specs(memory, ucs_bound, cue2=cue2):
        phase = backend.run_phase(
            state.copy(),
            float(config["phase_duration"]),
            stimuli,
            memory.key.response_id,
            int(config["trajectory_samples"]),
            int(config["pulse_count"]),
        )
        margin = float(learned_margin(memory, float(phase.mean_y[memory.key.response_id])))
        probes.append(
            {
                "probe": name,
                "stimuli": stimuli,
                "mean_response": float(phase.mean_y[memory.key.response_id]),
                "learned_margin": margin,
                "response_trajectory": phase.response_trajectory,
                "sampled_y": phase.sampled_y,
                "valid": bool(phase.valid),
            }
        )
        valid = valid and bool(phase.valid) and np.isfinite(margin)
        cpu += float(phase.cpu_seconds)
        wall += float(phase.wall_seconds)
    raw = np.asarray([row["learned_margin"] for row in probes], dtype=float)
    return {
        "fingerprint": np.arcsinh(raw),
        "raw_fingerprint": raw,
        "probes": probes,
        "valid": bool(valid),
        "cpu_seconds": cpu,
        "wall_seconds": wall,
    }


def _run_history(
    backend: JaxBackend,
    memory: Any,
    start: State,
    config: Mapping[str, Any],
    ucs_bound: int,
    tokens: Sequence[str],
    cue2: tuple[int, float] | None = None,
    two_cue_arm: str | None = None,
    seed_index: int | None = None,
    probe_ucs_bound: int | None = None,
) -> dict[str, Any]:
    cs, ucs, _ = _stimulus_values(memory, ucs_bound)
    if cue2 is None:
        epochs = schedule_stimuli(tokens, cs, ucs)
    else:
        cue1 = cs
        other = {int(cue2[0]): float(cue2[1])}
        paired_positions = {0, 2, 4, 6, 8} if int(seed_index or 0) % 2 == 0 else {1, 3, 5, 7, 9}
        epochs = []
        mixed_one = 3 if int(seed_index or 0) % 2 == 0 else 2
        seen_pair = 0
        for index in range(10):
            paired_slot = index in paired_positions
            if two_cue_arm == "form_a":
                values = {**cue1, **ucs} if paired_slot else other
            elif two_cue_arm == "form_b":
                values = {**other, **ucs} if paired_slot else cue1
            elif two_cue_arm == "mixed":
                if paired_slot:
                    with_one = seen_pair < mixed_one
                    values = {**(cue1 if with_one else other), **ucs}
                    seen_pair += 1
                else:
                    solo_index = sum(1 for prior in range(index + 1) if prior not in paired_positions) - 1
                    values = other if solo_index < mixed_one else cue1
            else:
                raise ValueError("two-cue history lacks a valid arm")
            epochs.append(values)
    training = run_epoch_schedule(
        backend,
        start,
        epochs,
        float(config["epoch_duration"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
    )
    cpu = float(training.cpu_seconds)
    wall = float(training.wall_seconds)
    current = training.state
    prior = 0.0
    valid = bool(training.valid)
    checkpoints: dict[str, Any] = {}
    for checkpoint in (float(value) for value in config["washout_checkpoints"]):
        washout = backend.run_unstimulated(
            current,
            checkpoint - prior,
            memory.key.response_id,
            int(config["trajectory_samples"]),
            float(config["phase_duration"]),
        )
        current = washout.state
        fp = _fingerprint(
            backend,
            memory,
            current,
            config,
            ucs_bound if probe_ucs_bound is None else int(probe_ucs_bound),
            cue2=cue2,
        )
        cpu += float(washout.cpu_seconds + fp["cpu_seconds"])
        wall += float(washout.wall_seconds + fp["wall_seconds"])
        valid = valid and bool(washout.valid and fp["valid"])
        checkpoints[f"{checkpoint:g}"] = {
            "state": state_payload(current),
            "fingerprint": fp["fingerprint"],
            "raw_fingerprint": fp["raw_fingerprint"],
            "probes": fp["probes"],
            "valid": bool(washout.valid and fp["valid"]),
        }
        prior = checkpoint
    return {
        "training_state": state_payload(training.state),
        "training_response_trajectory": training.response_trajectory,
        "checkpoints": checkpoints,
        "valid": bool(valid),
        "cpu_seconds": cpu,
        "wall_seconds": wall,
    }


def _score_history(result: Mapping[str, Any], reference: Mapping[str, Any], channel_class: str) -> dict[str, Any]:
    scores: dict[str, Any] = {}
    for key in ("2500", "12500"):
        fingerprint = result["checkpoints"][key]["fingerprint"]
        if channel_class == "relational":
            scores[key] = axis_score(
                fingerprint,
                reference["references"][key]["background"],
                reference["references"][key]["direction"],
            )
        else:
            scores[key] = bipolar_score(
                fingerprint,
                reference["exposure_reference"][key]["high"],
                reference["exposure_reference"][key]["low"],
            )
    return scores


def _history_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        output_path,
        mode,
        task_id,
        seed_index,
        conditions,
        shard_key,
    ) = args
    config = load_contingency_config(Path(config_path))
    atlas = Path(atlas_path)
    output = Path(output_path)
    shard = output / ".shards" / mode / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    audit = json.loads((output / "residual-audit.json").read_text(encoding="utf-8"))
    reference = _reference_map(audit)[str(task_id)]
    released = load_released_task(Path(upstream_path), str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    base = _naive_start(atlas, str(task_id))
    start, philox_seed = _perturb_start(base, memory, config, mode, str(task_id), int(seed_index))
    calibration = _calibration_map(atlas)[str(task_id)]
    reconstructed = int(calibration["reconstructed_ucs_bound_index"])
    records: list[dict[str, Any]] = []
    cpu = 0.0
    cue_payload = None
    if mode == "two-cue":
        cue_rows = {
            str(row["memory_task_id"]): row
            for row in read_jsonl(output / "cue-calibration.jsonl")
        }
        cue_payload = cue_rows[str(task_id)]
        if not cue_payload.get("eligible"):
            conditions = []
    for condition in conditions:
        if mode == "exposure":
            training_bound = 0 if condition == "low_ucs" else 1
            tokens = _control_tokens("ucs_only")
            result = _run_history(
                backend,
                memory,
                start.copy(),
                config,
                training_bound,
                tokens,
                seed_index=int(seed_index),
                probe_ucs_bound=reconstructed,
            )
            channel_class = "exposure"
        elif mode == "two-cue":
            training_bound = int(reference["selected_ucs_bound_index"])
            cue2 = (int(cue_payload["node_id"]), float(cue_payload["value"]))
            result = _run_history(
                backend,
                memory,
                start.copy(),
                config,
                training_bound,
                config["schedule_templates"]["coincident"],
                cue2=cue2,
                two_cue_arm=str(condition),
                seed_index=int(seed_index),
            )
            channel_class = "relational"
        else:
            training_bound = int(reference["selected_ucs_bound_index"])
            tokens = (
                config["schedule_templates"][condition]
                if condition in config["schedule_templates"]
                else _control_tokens(str(condition))
            )
            result = _run_history(
                backend,
                memory,
                start.copy(),
                config,
                training_bound,
                tokens,
                seed_index=int(seed_index),
            )
            channel_class = "relational"
        cpu += float(result["cpu_seconds"])
        scores = None if mode == "two-cue" else _score_history(result, reference, channel_class)
        records.append(
            {
                "task_id": f"{mode}|{task_id}|{seed_index}|{condition}",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "philox_seed": int(philox_seed),
                "channel_class": channel_class,
                "condition": str(condition),
                "schedule_exposures": (
                    {"cue1": 5, "cue2": 5, "ucs": 5}
                    if mode == "two-cue"
                    else schedule_exposure_counts(tokens)
                ),
                "scores": scores,
                "same_naive_start_hash": digest(state_payload(start)),
                "rulebook_inherited": False,
                "cue2": cue_payload,
                **result,
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "mode": mode,
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def _cue_calibration_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, task_id, shard_key = args
    config = load_contingency_config(Path(config_path))
    output = Path(output_path)
    shard = output / ".shards" / "cue-calibration" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    released = load_released_task(Path(upstream_path), str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    start = _naive_start(Path(atlas_path), str(task_id))
    cs, _, _ = _stimulus_values(memory, 0)
    cs_phase = backend.run_phase(
        start.copy(),
        float(config["phase_duration"]),
        cs,
        memory.key.response_id,
        int(config["trajectory_samples"]),
        int(config["pulse_count"]),
    )
    cs_margin = float(learned_margin(memory, float(cs_phase.mean_y[memory.key.response_id])))
    candidates: list[dict[str, Any]] = []
    cpu = float(cs_phase.cpu_seconds)
    excluded = {int(memory.key.response_id), int(memory.cs_id), int(memory.ucs_id)}
    for node in range(memory.node_count):
        if node in excluded:
            continue
        for bound_index in (0, 1):
            value = float(memory.bounds[node, bound_index])
            phase = backend.run_phase(
                start.copy(),
                float(config["phase_duration"]),
                {node: value},
                memory.key.response_id,
                int(config["trajectory_samples"]),
                int(config["pulse_count"]),
            )
            cpu += float(phase.cpu_seconds)
            margin = float(learned_margin(memory, float(phase.mean_y[memory.key.response_id])))
            candidates.append(
                {
                    "node_id": node,
                    "bound_index": bound_index,
                    "value": value,
                    "learned_margin": margin,
                    "valid": bool(phase.valid and np.isfinite(margin)),
                    "nonlearned": bool(margin <= float(config["two_cue_reversal"]["neutral_learned_margin_max"])),
                    "cs_margin_distance": abs(float(np.arcsinh(margin) - np.arcsinh(cs_margin))),
                    "stable_rank": _stable_rank(config["experiment_id"], task_id, node, bound_index),
                }
            )
    eligible = [row for row in candidates if row["valid"] and row["nonlearned"]]
    selected = min(eligible, key=lambda row: (float(row["cs_margin_distance"]), str(row["stable_rank"]))) if eligible else None
    record = {
        "task_id": f"cue-calibration|{task_id}",
        "memory_task_id": str(task_id),
        "model_id": int(memory.key.model_id),
        "eligible": selected is not None,
        "original_cs_learned_margin": cs_margin,
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        **({} if selected is None else selected),
    }
    payload = {
        "protocol_digest": protocol_digest,
        "aggregate_cpu_seconds": cpu,
        "records": [record],
    }
    write_json(shard, payload)
    return payload


def timing_selection(records: Sequence[Mapping[str, Any]], audit: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in records:
        grouped.setdefault(str(row["memory_task_id"]), []).append(row)
    selections: list[dict[str, Any]] = []
    for task_id in config["relational_candidate_task_ids"]:
        rows = grouped.get(str(task_id), [])
        schedule_metrics: dict[str, Any] = {}
        for schedule in SCHEDULES:
            schedule_rows = [row for row in rows if row["condition"] == schedule and row.get("valid")]
            values = [float(row["scores"]["12500"]) for row in schedule_rows if row.get("scores", {}).get("12500") is not None]
            schedule_metrics[schedule] = {
                "n": len(values),
                "median_long_score": quantile(values, 0.5),
                "lower_quartile_long_score": quantile(values, 0.25),
            }
        eligible = list(config["timing_discovery"]["eligible_schedules"])
        selected = min(
            eligible,
            key=lambda name: (
                -float(schedule_metrics[name]["median_long_score"] if schedule_metrics[name]["median_long_score"] is not None else -math.inf),
                eligible.index(name),
            ),
        )
        selections.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(str(task_id).split("-")[0]),
                "selected_schedule": selected,
                "schedule_metrics": schedule_metrics,
                "complete": all(schedule_metrics[name]["n"] == len(config["timing_discovery"]["seed_indices"]) for name in SCHEDULES),
            }
        )
    return {
        "task_id": "timing-selection",
        "selections": selections,
        "pass": all(row["complete"] for row in selections),
    }


def _mean_fingerprint(rows: Sequence[Mapping[str, Any]], condition: str, key: str) -> np.ndarray | None:
    values = [np.asarray(row["checkpoints"][key]["fingerprint"], dtype=float) for row in rows if row["condition"] == condition and row.get("valid")]
    return None if not values else np.mean(np.vstack(values), axis=0)


def contingency_decision(
    records: Sequence[Mapping[str, Any]],
    timing: Mapping[str, Any],
    audit: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["contingency_validation"]
    selected_map = {str(row["memory_task_id"]): str(row["selected_schedule"]) for row in timing["selections"]}
    reference_map = _reference_map(audit)
    summaries: list[dict[str, Any]] = []
    for task_id in config["relational_candidate_task_ids"]:
        rows = [row for row in records if row["memory_task_id"] == task_id]
        selected = selected_map[str(task_id)]
        paired = [row for row in rows if row["condition"] == selected and row.get("valid")]
        short_scores = [float(row["scores"]["2500"]) for row in paired]
        long_scores = [float(row["scores"]["12500"]) for row in paired]
        control_medians: dict[str, dict[str, float | None]] = {}
        control_values: list[float] = []
        for condition in CONTINGENCY_CONTROLS:
            condition_rows = [row for row in rows if row["condition"] == condition and row.get("valid")]
            control_medians[condition] = {}
            for key in ("2500", "12500"):
                values = [float(row["scores"][key]) for row in condition_rows]
                median = quantile(values, 0.5)
                control_medians[condition][key] = median
                if median is not None:
                    control_values.append(abs(median))
        short_direction = None
        long_direction = None
        background = "ucs_only"
        for key in ("2500", "12500"):
            left = _mean_fingerprint(rows, selected, key)
            right = _mean_fingerprint(rows, background, key)
            if left is not None and right is not None:
                if key == "2500":
                    short_direction = left - right
                else:
                    long_direction = left - right
        direction_cosine = None if short_direction is None or long_direction is None else cosine_alignment(short_direction, long_direction)
        retention = None if short_direction is None or long_direction is None else vector_rms(long_direction) / max(vector_rms(short_direction), 1e-12)
        reference_direction = np.asarray(reference_map[str(task_id)]["references"]["12500"]["direction"], dtype=float)
        cue_sign = math.copysign(1.0, float(reference_direction[1] - reference_direction[0])) if abs(float(reference_direction[1] - reference_direction[0])) > 1e-12 else 1.0
        consistent_cue = 0
        seed_count = 0
        for seed in settings["seed_indices"]:
            seed_rows = {str(row["condition"]): row for row in rows if int(row["seed_index"]) == int(seed) and row.get("valid")}
            if selected not in seed_rows or "blocked" not in seed_rows or "shuffled" not in seed_rows:
                continue
            paired_gain = float(seed_rows[selected]["checkpoints"]["12500"]["fingerprint"][1] - seed_rows[selected]["checkpoints"]["12500"]["fingerprint"][0])
            null_gain = 0.5 * sum(float(seed_rows[name]["checkpoints"]["12500"]["fingerprint"][1] - seed_rows[name]["checkpoints"]["12500"]["fingerprint"][0]) for name in ("blocked", "shuffled"))
            consistent_cue += int(cue_sign * (paired_gain - null_gain) > 0)
            seed_count += 1
        median_long = quantile(long_scores, 0.5)
        lower_long = quantile(long_scores, 0.25)
        consistent = sum(value >= float(settings["lower_quartile_min"]) for value in long_scores)
        control_max = max(control_values) if control_values else math.inf
        passed = bool(
            len(paired) == len(settings["seed_indices"])
            and median_long is not None
            and median_long >= float(settings["median_score_min"])
            and lower_long is not None
            and lower_long >= float(settings["lower_quartile_min"])
            and consistent >= int(settings["minimum_consistent_seeds"])
            and direction_cosine is not None
            and direction_cosine >= float(settings["direction_cosine_min"])
            and retention is not None
            and retention >= float(settings["long_retention_fraction_min"])
            and control_max <= float(settings["control_max_abs"])
            and consistent_cue >= int(settings["minimum_consistent_seeds"])
        )
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(str(task_id).split("-")[0]),
                "selected_schedule": selected,
                "valid_seed_count": len(paired),
                "median_long_score": median_long,
                "lower_quartile_long_score": lower_long,
                "consistent_seed_count": consistent,
                "cue_interaction_consistent_seed_count": consistent_cue,
                "cue_interaction_evaluable_seed_count": seed_count,
                "direction_cosine": direction_cosine,
                "long_retention_fraction": retention,
                "control_max_abs": control_max,
                "control_medians": control_medians,
                "pass": passed,
            }
        )
    ranked = sorted(
        (row for row in summaries if row["pass"]),
        key=lambda row: (-float(row["lower_quartile_long_score"]), -float(row["median_long_score"]), str(row["memory_task_id"])),
    )
    advanced: list[dict[str, Any]] = []
    used: set[int] = set()
    for row in ranked:
        if int(row["model_id"]) in used:
            continue
        advanced.append({"memory_task_id": row["memory_task_id"], "model_id": row["model_id"], "selected_schedule": row["selected_schedule"], "channel_class": "relational"})
        used.add(int(row["model_id"]))
        if len(advanced) == int(settings["max_two_cue_candidates"]):
            break
    return {
        "task_id": "contingency-validation-decision",
        "candidate_summaries": summaries,
        "two_cue_candidates": advanced,
        "pass_count": sum(bool(row["pass"]) for row in summaries),
        "pass": bool(advanced),
        "verdict": "prospective-contingency-leads" if advanced else "no-prospective-contingency-memory",
    }


def exposure_decision(records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config["exposure_validation"]
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_anchor_task_ids"]:
        rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        crossovers: dict[str, list[float]] = {"2500": [], "12500": []}
        for seed in settings["seed_indices"]:
            seed_rows = {str(row["condition"]): row for row in rows if int(row["seed_index"]) == int(seed)}
            if set(seed_rows) != {"low_ucs", "high_ucs"}:
                continue
            for key in crossovers:
                crossovers[key].append(0.5 * (float(seed_rows["high_ucs"]["scores"][key]) - float(seed_rows["low_ucs"]["scores"][key])))
        short_d = _mean_fingerprint(rows, "high_ucs", "2500")
        short_l = _mean_fingerprint(rows, "low_ucs", "2500")
        long_d = _mean_fingerprint(rows, "high_ucs", "12500")
        long_l = _mean_fingerprint(rows, "low_ucs", "12500")
        short_direction = None if short_d is None or short_l is None else short_d - short_l
        long_direction = None if long_d is None or long_l is None else long_d - long_l
        cosine = None if short_direction is None or long_direction is None else cosine_alignment(short_direction, long_direction)
        retention = None if short_direction is None or long_direction is None else vector_rms(long_direction) / max(vector_rms(short_direction), 1e-12)
        median = quantile(crossovers["12500"], 0.5)
        lower = quantile(crossovers["12500"], 0.25)
        consistent = sum(value >= float(settings["lower_quartile_min"]) for value in crossovers["12500"])
        passed = bool(
            len(crossovers["12500"]) == len(settings["seed_indices"])
            and median is not None and median >= float(settings["median_crossover_min"])
            and lower is not None and lower >= float(settings["lower_quartile_min"])
            and consistent >= int(settings["minimum_consistent_seeds"])
            and cosine is not None and cosine >= float(settings["direction_cosine_min"])
            and retention is not None and retention >= float(settings["long_retention_fraction_min"])
        )
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(str(task_id).split("-")[0]),
                "median_long_crossover": median,
                "lower_quartile_long_crossover": lower,
                "consistent_seed_count": consistent,
                "direction_cosine": cosine,
                "long_retention_fraction": retention,
                "pass": passed,
            }
        )
    ranked = sorted((row for row in summaries if row["pass"]), key=lambda row: (-float(row["lower_quartile_long_crossover"]), str(row["memory_task_id"])))
    advanced = [{"memory_task_id": row["memory_task_id"], "model_id": row["model_id"], "channel_class": "exposure"} for row in ranked[: int(settings["max_transfer_candidates"])]]
    return {
        "task_id": "exposure-validation-decision",
        "candidate_summaries": summaries,
        "transfer_candidates": advanced,
        "pass_count": sum(bool(row["pass"]) for row in summaries),
        "pass": bool(advanced),
        "verdict": "durable-exposure-state-leads" if advanced else "no-durable-exposure-state",
    }


def two_cue_decision(records: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config["two_cue_reversal"]
    summaries: list[dict[str, Any]] = []
    for candidate in candidates:
        task_id = str(candidate["memory_task_id"])
        rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        crossovers: dict[str, list[float]] = {"2500": [], "12500": []}
        mixed: dict[str, list[float]] = {"2500": [], "12500": []}
        for seed in settings["seed_indices"]:
            seed_rows = {str(row["condition"]): row for row in rows if int(row["seed_index"]) == int(seed)}
            if set(seed_rows) != {"form_a", "form_b", "mixed"}:
                continue
            for key in crossovers:
                a = np.asarray(seed_rows["form_a"]["checkpoints"][key]["fingerprint"], dtype=float)
                b = np.asarray(seed_rows["form_b"]["checkpoints"][key]["fingerprint"], dtype=float)
                m = np.asarray(seed_rows["mixed"]["checkpoints"][key]["fingerprint"], dtype=float)
                crossovers[key].append(0.5 * (float(a[1] - a[2]) - float(b[1] - b[2])))
                mixed[key].append(float(m[1] - m[2]))
        median = quantile(crossovers["12500"], 0.5)
        lower = quantile(crossovers["12500"], 0.25)
        consistent = sum(value >= float(settings["lower_quartile_min"]) for value in crossovers["12500"])
        control = max((abs(float(quantile(values, 0.5))) for values in mixed.values() if quantile(values, 0.5) is not None), default=math.inf)
        short = quantile([abs(row) for row in crossovers["2500"]], 0.5)
        long = quantile([abs(row) for row in crossovers["12500"]], 0.5)
        retention = None if short is None or long is None else long / max(short, 1e-12)
        passed = bool(
            len(crossovers["12500"]) == len(settings["seed_indices"])
            and median is not None and median >= float(settings["median_crossover_min"])
            and lower is not None and lower >= float(settings["lower_quartile_min"])
            and consistent >= int(settings["minimum_consistent_seeds"])
            and control <= float(settings["control_max_abs"])
            and retention is not None and retention >= float(settings["long_retention_fraction_min"])
        )
        form_means = {}
        for arm in ("form_a", "form_b", "mixed"):
            mean = _mean_fingerprint(rows, arm, "12500")
            form_means[arm] = None if mean is None else mean
        cue2 = next((row.get("cue2") for row in rows if row.get("cue2")), None)
        summaries.append(
            {
                "memory_task_id": task_id,
                "model_id": int(candidate["model_id"]),
                "selected_schedule": candidate["selected_schedule"],
                "median_long_crossover": median,
                "lower_quartile_long_crossover": lower,
                "consistent_seed_count": consistent,
                "mixed_control_max_abs": control,
                "long_retention_fraction": retention,
                "reference_fingerprints": form_means,
                "cue2": cue2,
                "pass": passed,
            }
        )
    ranked = sorted((row for row in summaries if row["pass"]), key=lambda row: (-float(row["lower_quartile_long_crossover"]), str(row["memory_task_id"])))
    advanced = [
        {
            "memory_task_id": row["memory_task_id"],
            "model_id": row["model_id"],
            "channel_class": "relational",
            "selected_schedule": row["selected_schedule"],
            "cue2": row["cue2"],
            "reference_fingerprints": row["reference_fingerprints"],
        }
        for row in ranked[: int(settings["max_transfer_candidates"])]
    ]
    return {
        "task_id": "two-cue-reversal-decision",
        "candidate_summaries": summaries,
        "transfer_candidates": advanced,
        "pass_count": sum(bool(row["pass"]) for row in summaries),
        "pass": bool(advanced),
        "verdict": "counterbalanced-relational-forms" if advanced else "no-counterbalanced-relational-form",
    }


def _state_vector(state: State, mode: str) -> np.ndarray:
    if mode == "y":
        return np.asarray(state.y, dtype=float)
    if mode == "yw":
        return np.concatenate((np.asarray(state.y, dtype=float), np.asarray(state.w, dtype=float)))
    raise ValueError(f"unknown state mode: {mode}")


def _state_scale(memory: Any, baseline: State, form_a: State, form_b: State, mode: str) -> np.ndarray:
    y_scale = np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8)
    if mode == "y":
        return y_scale
    w_scale = np.maximum.reduce((np.abs(form_a.w - form_b.w), np.abs(baseline.w), np.full_like(baseline.w, 1e-8)))
    return np.concatenate((y_scale, w_scale))


def _normalized_state(state: State, baseline: State, scale: np.ndarray, mode: str) -> np.ndarray:
    return (_state_vector(state, mode) - _state_vector(baseline, mode)) / np.asarray(scale, dtype=float)


def _state_from_normalized(values: Sequence[float], baseline: State, scale: np.ndarray, memory: Any, mode: str) -> State:
    vector = _state_vector(baseline, mode) + np.asarray(values, dtype=float) * np.asarray(scale, dtype=float)
    y_count = len(baseline.y)
    y = np.clip(vector[:y_count], memory.bounds[:, 0], memory.bounds[:, 1])
    w = baseline.w.copy() if mode == "y" else vector[y_count:].copy()
    return State(y.copy(), w, baseline.c.copy(), baseline.t)


def _channel_histories(
    backend: JaxBackend,
    memory: Any,
    start: State,
    config: Mapping[str, Any],
    candidate: Mapping[str, Any],
    reconstructed_bound: int,
    seed_index: int,
) -> dict[str, dict[str, Any]]:
    if candidate["channel_class"] == "relational":
        cue = candidate["cue2"]
        cue2 = (int(cue["node_id"]), float(cue["value"]))
        bound = int(candidate.get("selected_ucs_bound_index", reconstructed_bound))
        return {
            arm: _run_history(
                backend,
                memory,
                start.copy(),
                config,
                bound,
                config["schedule_templates"]["coincident"],
                cue2=cue2,
                two_cue_arm=arm,
                seed_index=seed_index,
            )
            for arm in ("form_a", "form_b", "mixed")
        }
    return {
        "form_a": _run_history(
            backend,
            memory,
            start.copy(),
            config,
            1,
            _control_tokens("ucs_only"),
            seed_index=seed_index,
            probe_ucs_bound=reconstructed_bound,
        ),
        "form_b": _run_history(
            backend,
            memory,
            start.copy(),
            config,
            0,
            _control_tokens("ucs_only"),
            seed_index=seed_index,
            probe_ucs_bound=reconstructed_bound,
        ),
        "mixed": _run_history(
            backend,
            memory,
            start.copy(),
            config,
            reconstructed_bound,
            _control_tokens("naive"),
            seed_index=seed_index,
            probe_ucs_bound=reconstructed_bound,
        ),
    }


def _assay_transferred(
    backend: JaxBackend,
    memory: Any,
    child: State,
    config: Mapping[str, Any],
    candidate: Mapping[str, Any],
    reconstructed_bound: int,
) -> dict[str, Any]:
    development = backend.run_unstimulated(
        child,
        float(config["phase_duration"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
    )
    cue2 = None
    if candidate["channel_class"] == "relational":
        cue = candidate["cue2"]
        cue2 = (int(cue["node_id"]), float(cue["value"]))
    fp = _fingerprint(backend, memory, development.state, config, reconstructed_bound, cue2=cue2)
    reference = candidate["reference_fingerprints"]
    score = bipolar_score(fp["fingerprint"], reference["form_a"], reference["form_b"])
    return {
        "adult_state": state_payload(development.state),
        "fingerprint": fp["fingerprint"],
        "probes": fp["probes"],
        "score": score,
        "valid": bool(development.valid and fp["valid"] and score is not None),
        "cpu_seconds": float(development.cpu_seconds + fp["cpu_seconds"]),
        "wall_seconds": float(development.wall_seconds + fp["wall_seconds"]),
    }


def _transfer_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, candidate, seed_index, shard_key = args
    config = load_contingency_config(Path(config_path))
    output = Path(output_path)
    shard = output / ".shards" / "native-transfer" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    task_id = str(candidate["memory_task_id"])
    released = load_released_task(Path(upstream_path), task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    base = _naive_start(Path(atlas_path), task_id)
    start, philox_seed = _perturb_start(base, memory, config, "native-transfer", task_id, int(seed_index))
    reconstructed = int(_calibration_map(Path(atlas_path))[task_id]["reconstructed_ucs_bound_index"])
    histories = _channel_histories(backend, memory, start, config, candidate, reconstructed, int(seed_index))
    donor_states = {arm: state_from_payload(row["checkpoints"]["12500"]["state"]) for arm, row in histories.items()}
    if any(state is None for state in donor_states.values()):
        raise ValueError(f"invalid transfer donor state for {task_id}")
    form_a = donor_states["form_a"]
    form_b = donor_states["form_b"]
    assert form_a is not None and form_b is not None
    modes = ["y"]
    if form_a.w.size and form_a.w.shape == form_b.w.shape and np.linalg.norm(form_a.w - form_b.w) > 1e-12:
        modes.append("yw")
    records: list[dict[str, Any]] = []
    cpu = sum(float(row["cpu_seconds"]) for row in histories.values())
    for mode in modes:
        scale = _state_scale(memory, start, form_a, form_b, mode)
        vectors = {
            "a": _normalized_state(form_a, start, scale, mode),
            "b": _normalized_state(form_b, start, scale, mode),
            "background": _normalized_state(donor_states["mixed"], start, scale, mode),
        }
        midpoint = 0.5 * (vectors["a"] + vectors["b"])
        for environment_name, environment in config["native_transfer"]["environments"].items():
            keep, noise, damage_seed = common_damage(config, "contingency-transfer", task_id, int(seed_index), 0, len(scale), environment)
            for history in ("a", "b"):
                source = vectors[history]
                opposite = vectors["b" if history == "a" else "a"]
                rng = np.random.Generator(np.random.Philox(_seed(config, "transfer-controls", task_id, seed_index, mode, environment_name, history)))
                shuffled, shuffle_method = normalized_shuffle(source, rng)
                condition_vectors = {
                    "intact": source,
                    "matched_background": vectors["background"],
                    "opposite": opposite,
                    "inversion": 2.0 * midpoint - source,
                    "zero": np.zeros_like(source),
                    "normalized_shuffle": shuffled,
                    "norm_matched_random": norm_matched_random(source, rng),
                }
                for condition, vector in condition_vectors.items():
                    copied = copy_normalized(vector, keep, noise, float(environment["retention"]))
                    child = _state_from_normalized(copied, start, scale, memory, mode)
                    assay = _assay_transferred(backend, memory, child, config, candidate, reconstructed)
                    cpu += float(assay["cpu_seconds"])
                    records.append(
                        {
                            "task_id": f"native-transfer|{task_id}|{seed_index}|{mode}|{environment_name}|{history}|{condition}",
                            "memory_task_id": task_id,
                            "model_id": int(memory.key.model_id),
                            "channel_class": candidate["channel_class"],
                            "seed_index": int(seed_index),
                            "philox_seed": int(philox_seed),
                            "damage_seed": int(damage_seed),
                            "state_mode": mode,
                            "environment": environment_name,
                            "history": history,
                            "condition": condition,
                            "shuffle_method": shuffle_method if condition == "normalized_shuffle" else None,
                            "recipient_c_hash": digest(start.c),
                            "child_c_hash": digest(child.c),
                            "rulebook_inherited": False,
                            "source_vector": vector,
                            "state_scale": scale,
                            **assay,
                        }
                    )
    payload = {
        "protocol_digest": protocol_digest,
        "memory_task_id": task_id,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def native_transfer_decision(records: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config["native_transfer"]
    summaries: list[dict[str, Any]] = []
    for candidate in candidates:
        task_id = str(candidate["memory_task_id"])
        task_rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        for mode in sorted({str(row["state_mode"]) for row in task_rows}):
            environments: dict[str, Any] = {}
            mode_pass = True
            for environment in ("exact", "moderate"):
                rows = [row for row in task_rows if row["state_mode"] == mode and row["environment"] == environment]
                crossovers: list[float] = []
                opposite_reversal = 0
                inversion_reversal = 0
                control_groups: dict[str, list[float]] = {
                    name: []
                    for name in (
                        "matched_background",
                        "zero",
                        "normalized_shuffle",
                        "norm_matched_random",
                    )
                }
                for seed in settings["seed_indices"]:
                    index = {(str(row["history"]), str(row["condition"])): row for row in rows if int(row["seed_index"]) == int(seed)}
                    if ("a", "intact") not in index or ("b", "intact") not in index:
                        continue
                    crossovers.append(0.5 * (float(index[("a", "intact")]["score"]) - float(index[("b", "intact")]["score"])))
                    if ("a", "opposite") in index and ("b", "opposite") in index:
                        opposite_reversal += int(
                            float(index[("a", "opposite")]["score"]) < 0
                            and float(index[("b", "opposite")]["score"]) > 0
                        )
                    if ("a", "inversion") in index and ("b", "inversion") in index:
                        inversion_reversal += int(
                            float(index[("a", "inversion")]["score"]) < 0
                            and float(index[("b", "inversion")]["score"]) > 0
                        )
                    for history in ("a", "b"):
                        for control in ("matched_background", "zero", "normalized_shuffle", "norm_matched_random"):
                            if (history, control) in index:
                                control_groups[control].append(
                                    float(index[(history, control)]["score"])
                                )
                median = quantile(crossovers, 0.5)
                lower = quantile(crossovers, 0.25)
                consistent = sum(value >= (float(settings["exact_lower_quartile_min"]) if environment == "exact" else float(settings["moderate_crossover_reporting_min"])) for value in crossovers)
                control_max, control_medians = control_median_envelope(control_groups)
                environment_pass = bool(
                    len(crossovers) == len(settings["seed_indices"])
                    and median is not None
                    and median >= (float(settings["exact_crossover_min"]) if environment == "exact" else float(settings["moderate_crossover_reporting_min"]))
                    and (environment != "exact" or (lower is not None and lower >= float(settings["exact_lower_quartile_min"])))
                    and consistent >= int(settings["minimum_consistent_seeds"])
                    and opposite_reversal >= int(settings["minimum_consistent_seeds"])
                    and inversion_reversal >= int(settings["minimum_consistent_seeds"])
                    and control_max is not None and control_max <= float(settings["control_max_fraction"])
                )
                environments[environment] = {
                    "median_crossover": median,
                    "lower_quartile_crossover": lower,
                    "consistent_seed_count": consistent,
                    "opposite_reversal_seed_count": opposite_reversal,
                    "inversion_reversal_seed_count": inversion_reversal,
                    "control_median_abs": control_max,
                    "control_medians_abs": control_medians,
                    "pass": environment_pass,
                }
                if environment == "exact":
                    mode_pass = mode_pass and environment_pass
            summaries.append(
                {
                    "memory_task_id": task_id,
                    "model_id": int(candidate["model_id"]),
                    "channel_class": candidate["channel_class"],
                    "state_mode": mode,
                    "environments": environments,
                    "pass": mode_pass,
                    "candidate": candidate,
                }
            )
    passing = sorted(
        (row for row in summaries if row["pass"]),
        key=lambda row: (
            0 if row["channel_class"] == "relational" else 1,
            0 if row["state_mode"] == "y" else 1,
            -float(row["environments"]["exact"]["lower_quartile_crossover"]),
            str(row["memory_task_id"]),
        ),
    )
    selected: list[dict[str, Any]] = []
    used_tasks: set[str] = set()
    for wanted_class in ("relational", "exposure"):
        match = next((row for row in passing if row["channel_class"] == wanted_class and row["memory_task_id"] not in used_tasks), None)
        if match is not None:
            selected.append({**match["candidate"], "state_mode": match["state_mode"]})
            used_tasks.add(str(match["memory_task_id"]))
    for row in passing:
        if len(selected) >= int(settings["max_carrier_channels"]):
            break
        if row["memory_task_id"] not in used_tasks:
            selected.append({**row["candidate"], "state_mode": row["state_mode"]})
            used_tasks.add(str(row["memory_task_id"]))
    return {
        "task_id": "native-transfer-decision",
        "channel_summaries": summaries,
        "carrier_candidates": selected[: int(settings["max_carrier_channels"])],
        "pass_count": sum(bool(row["pass"]) for row in summaries),
        "pass": bool(selected),
        "verdict": "native-transfer-leads" if selected else "no-native-transfer",
    }


def _carrier_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, candidate, shard_key = args
    config = load_contingency_config(Path(config_path))
    settings = config["carrier_dissection"]
    output = Path(output_path)
    shard = output / ".shards" / "carrier-dissection" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    task_id = str(candidate["memory_task_id"])
    released = load_released_task(Path(upstream_path), task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    reconstructed = int(_calibration_map(Path(atlas_path))[task_id]["reconstructed_ucs_bound_index"])
    mode = str(candidate["state_mode"])
    discovery_vectors: dict[str, list[np.ndarray]] = {"a": [], "b": [], "background": []}
    discovery_contexts: list[tuple[State, dict[str, State]]] = []
    cpu = 0.0
    fixed_scale: np.ndarray | None = None
    for seed_index in settings["discovery_seed_indices"]:
        base = _naive_start(Path(atlas_path), task_id)
        start, _ = _perturb_start(base, memory, config, "carrier-discovery", task_id, int(seed_index))
        histories = _channel_histories(backend, memory, start, config, candidate, reconstructed, int(seed_index))
        cpu += sum(float(row["cpu_seconds"]) for row in histories.values())
        states = {name: state_from_payload(row["checkpoints"]["12500"]["state"]) for name, row in histories.items()}
        if any(state is None for state in states.values()):
            raise ValueError(f"invalid carrier discovery state for {task_id}")
        a = states["form_a"]
        b = states["form_b"]
        assert a is not None and b is not None
        if fixed_scale is None:
            fixed_scale = _state_scale(memory, start, a, b, mode)
        discovery_vectors["a"].append(_normalized_state(a, start, fixed_scale, mode))
        discovery_vectors["b"].append(_normalized_state(b, start, fixed_scale, mode))
        discovery_vectors["background"].append(_normalized_state(states["mixed"], start, fixed_scale, mode))
        discovery_contexts.append((start, {key: value for key, value in states.items() if value is not None}))
    if fixed_scale is None:
        raise ValueError("carrier discovery produced no scale")
    form_means = {name: np.mean(np.vstack(values), axis=0) for name, values in discovery_vectors.items()}
    matrix = np.vstack([*discovery_vectors["a"], *discovery_vectors["b"], *discovery_vectors["background"]])
    baseline = discovery_contexts[0][0]
    midpoint = 0.5 * (form_means["a"] + form_means["b"])
    midpoint_state = _state_from_normalized(midpoint, baseline, fixed_scale, memory, mode)
    midpoint_assay = _assay_transferred(backend, memory, midpoint_state, config, candidate, reconstructed)
    cpu += float(midpoint_assay["cpu_seconds"])
    sensitivity_columns: list[np.ndarray] = []
    impulse = 0.01
    for index in range(len(fixed_scale)):
        perturbed = midpoint.copy()
        perturbed[index] += impulse
        state = _state_from_normalized(perturbed, baseline, fixed_scale, memory, mode)
        assay = _assay_transferred(backend, memory, state, config, candidate, reconstructed)
        cpu += float(assay["cpu_seconds"])
        if assay["valid"] and midpoint_assay["valid"]:
            sensitivity_columns.append((np.asarray(assay["fingerprint"], dtype=float) - np.asarray(midpoint_assay["fingerprint"], dtype=float)) / impulse)
        else:
            sensitivity_columns.append(np.zeros(len(candidate["reference_fingerprints"]["form_a"])))
    sensitivity = np.column_stack(sensitivity_columns)
    _, _, observability_vt = np.linalg.svd(sensitivity, full_matrices=False)
    codebooks = build_codebooks(
        matrix,
        form_means["a"],
        form_means["b"],
        len(baseline.y),
        settings["sparse_sizes"],
        settings["pca_ranks"],
        settings["observability_ranks"],
        observability_vt,
    )
    discovery_records: list[dict[str, Any]] = []
    for codec in codebooks:
        scores: dict[str, float | None] = {}
        for history in ("a", "b"):
            payload = encode_codec(codec, form_means[history])
            decoded = decode_codec(codec, payload)
            state = _state_from_normalized(decoded, baseline, fixed_scale, memory, mode)
            assay = _assay_transferred(backend, memory, state, config, candidate, reconstructed)
            cpu += float(assay["cpu_seconds"])
            scores[history] = assay["score"]
        crossover = None if scores["a"] is None or scores["b"] is None else 0.5 * (float(scores["a"]) - float(scores["b"]))
        discovery_records.append(
            {
                "task_id": f"carrier-discovery|{task_id}|{codec['codec_id']}",
                "memory_task_id": task_id,
                "model_id": int(memory.key.model_id),
                "channel_class": candidate["channel_class"],
                "state_mode": mode,
                "codec_id": codec["codec_id"],
                "family": codec["family"],
                "payload_float_count": codec["payload_float_count"],
                "crossover": crossover,
                "scores": scores,
                "valid": crossover is not None,
            }
        )
    eligible = [row for row in discovery_records if row["valid"] and float(row["crossover"]) >= float(settings["median_crossover_min"])]
    selected_row = min(
        eligible,
        key=lambda row: (
            int(row["payload_float_count"]),
            -float(row["crossover"]),
            ("sparse", "direction", "pca", "observability").index(str(row["family"])),
            str(row["codec_id"]),
        ),
    ) if eligible else None
    selected_codec = None if selected_row is None else next(codec for codec in codebooks if codec["codec_id"] == selected_row["codec_id"])
    validation_records: list[dict[str, Any]] = []
    if selected_codec is not None:
        for seed_index in settings["validation_seed_indices"]:
            base = _naive_start(Path(atlas_path), task_id)
            start, philox_seed = _perturb_start(base, memory, config, "carrier-validation", task_id, int(seed_index))
            histories = _channel_histories(backend, memory, start, config, candidate, reconstructed, int(seed_index))
            cpu += sum(float(row["cpu_seconds"]) for row in histories.values())
            states = {name: state_from_payload(row["checkpoints"]["12500"]["state"]) for name, row in histories.items()}
            if any(state is None for state in states.values()):
                continue
            vectors = {
                "a": _normalized_state(states["form_a"], start, fixed_scale, mode),
                "b": _normalized_state(states["form_b"], start, fixed_scale, mode),
                "background": _normalized_state(states["mixed"], start, fixed_scale, mode),
            }
            midpoint_seed = 0.5 * (vectors["a"] + vectors["b"])
            for history in ("a", "b"):
                source = vectors[history]
                opposite = vectors["b" if history == "a" else "a"]
                source_packet = encode_codec(selected_codec, source)
                opposite_packet = encode_codec(selected_codec, opposite)
                background_packet = encode_codec(selected_codec, vectors["background"])
                midpoint_packet = encode_codec(selected_codec, midpoint_seed)
                intact = decode_codec(selected_codec, source_packet)
                wrong = decode_codec(selected_codec, opposite_packet)
                background = decode_codec(selected_codec, background_packet)
                rng = np.random.Generator(np.random.Philox(_seed(config, "carrier-controls", task_id, seed_index, history)))
                shuffled_packet, shuffle_method = normalized_shuffle(source_packet, rng)
                conditions = {
                    "intact": intact,
                    "matched_background": background,
                    "erase": decode_codec(selected_codec, np.zeros_like(source_packet)),
                    "inversion": decode_codec(
                        selected_codec, 2.0 * midpoint_packet - source_packet
                    ),
                    "wrong_content": wrong,
                    "normalized_shuffle": decode_codec(selected_codec, shuffled_packet),
                    "norm_matched_random": decode_codec(
                        selected_codec, norm_matched_random(source_packet, rng)
                    ),
                    "rescue": intact,
                }
                for condition, decoded in conditions.items():
                    child = _state_from_normalized(decoded, start, fixed_scale, memory, mode)
                    assay = _assay_transferred(backend, memory, child, config, candidate, reconstructed)
                    cpu += float(assay["cpu_seconds"])
                    validation_records.append(
                        {
                            "task_id": f"carrier-validation|{task_id}|{seed_index}|{history}|{condition}",
                            "memory_task_id": task_id,
                            "model_id": int(memory.key.model_id),
                            "channel_class": candidate["channel_class"],
                            "seed_index": int(seed_index),
                            "philox_seed": int(philox_seed),
                            "history": history,
                            "condition": condition,
                            "state_mode": mode,
                            "codec_id": selected_codec["codec_id"],
                            "payload_float_count": selected_codec["payload_float_count"],
                            "control_space": "codec-payload",
                            "shuffle_method": shuffle_method if condition == "normalized_shuffle" else None,
                            "recipient_c_hash": digest(start.c),
                            "child_c_hash": digest(child.c),
                            "rulebook_inherited": False,
                            **assay,
                        }
                    )
    payload = {
        "protocol_digest": protocol_digest,
        "memory_task_id": task_id,
        "aggregate_cpu_seconds": cpu,
        "discovery_records": discovery_records,
        "validation_records": validation_records,
        "codebooks": codebooks,
        "selected_codec": selected_codec,
        "fixed_state_scale": fixed_scale,
        "candidate": candidate,
    }
    write_json(shard, payload)
    return payload


def carrier_decision(shards: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config["carrier_dissection"]
    summaries: list[dict[str, Any]] = []
    passing_channels: list[dict[str, Any]] = []
    for shard in shards:
        candidate = dict(shard["candidate"])
        task_id = str(candidate["memory_task_id"])
        codec = shard.get("selected_codec")
        rows = [row for row in shard.get("validation_records", ()) if row.get("valid")]
        crossovers: dict[str, list[float]] = {condition: [] for condition in ("intact", "erase", "rescue", "wrong_content", "inversion")}
        control_groups: dict[str, list[float]] = {
            name: []
            for name in (
                "matched_background",
                "normalized_shuffle",
                "norm_matched_random",
            )
        }
        for seed in settings["validation_seed_indices"]:
            index = {(str(row["history"]), str(row["condition"])): row for row in rows if int(row["seed_index"]) == int(seed)}
            for condition in crossovers:
                if ("a", condition) in index and ("b", condition) in index:
                    crossovers[condition].append(0.5 * (float(index[("a", condition)]["score"]) - float(index[("b", condition)]["score"])))
            for history in ("a", "b"):
                for condition in ("matched_background", "normalized_shuffle", "norm_matched_random"):
                    if (history, condition) in index:
                        control_groups[condition].append(
                            float(index[(history, condition)]["score"])
                        )
        intact = quantile(crossovers["intact"], 0.5)
        erase = quantile([abs(row) for row in crossovers["erase"]], 0.5)
        rescue = quantile(crossovers["rescue"], 0.5)
        removal = None if intact is None or erase is None else 1.0 - erase / max(abs(intact), 1e-12)
        rescue_fraction = None if intact is None or rescue is None else rescue / max(abs(intact), 1e-12)
        control, control_medians = control_median_envelope(control_groups)
        consistent = sum(value >= float(settings["median_crossover_min"]) for value in crossovers["intact"])
        wrong_reversal = sum(value <= -float(settings["median_crossover_min"]) for value in crossovers["wrong_content"])
        inversion_reversal = sum(value <= -float(settings["median_crossover_min"]) for value in crossovers["inversion"])
        passed = bool(
            codec is not None
            and len(crossovers["intact"]) == len(settings["validation_seed_indices"])
            and intact is not None and intact >= float(settings["median_crossover_min"])
            and consistent >= int(settings["minimum_consistent_seeds"])
            and wrong_reversal >= int(settings["minimum_consistent_seeds"])
            and inversion_reversal >= int(settings["minimum_consistent_seeds"])
            and removal is not None and removal >= float(settings["ablation_removal_fraction_min"])
            and rescue_fraction is not None and rescue_fraction >= float(settings["rescue_fraction_min"])
            and control is not None and control <= float(settings["control_max_fraction"])
        )
        summary = {
            "memory_task_id": task_id,
            "model_id": int(candidate["model_id"]),
            "channel_class": candidate["channel_class"],
            "codec_id": None if codec is None else codec["codec_id"],
            "payload_float_count": None if codec is None else codec["payload_float_count"],
            "median_intact_crossover": intact,
            "consistent_seed_count": consistent,
            "wrong_content_reversal_seed_count": wrong_reversal,
            "inversion_reversal_seed_count": inversion_reversal,
            "ablation_removal_fraction": removal,
            "rescue_fraction": rescue_fraction,
            "control_median_abs": control,
            "control_medians_abs": control_medians,
            "pass": passed,
        }
        summaries.append(summary)
        if passed:
            passing_channels.append(
                {
                    **candidate,
                    "codec": codec,
                    "state_scale": shard["fixed_state_scale"],
                }
            )
    return {
        "task_id": "carrier-dissection-decision",
        "channel_summaries": summaries,
        "renewal_candidates": passing_channels,
        "pass_count": len(passing_channels),
        "pass": bool(passing_channels),
        "verdict": "causal-compact-carrier-leads" if passing_channels else "no-causal-compact-carrier",
    }


def _lineage_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, candidate, seed_index, shard_key = args
    config = load_contingency_config(Path(config_path))
    settings = config["active_renewal"]
    output = Path(output_path)
    shard = output / ".shards" / "active-renewal" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    task_id = str(candidate["memory_task_id"])
    released = load_released_task(Path(upstream_path), task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    reconstructed = int(_calibration_map(Path(atlas_path))[task_id]["reconstructed_ucs_bound_index"])
    base = _naive_start(Path(atlas_path), task_id)
    start, philox_seed = _perturb_start(base, memory, config, "active-renewal", task_id, int(seed_index))
    histories = _channel_histories(backend, memory, start, config, candidate, reconstructed, int(seed_index))
    cpu = sum(float(row["cpu_seconds"]) for row in histories.values())
    states = {name: state_from_payload(row["checkpoints"]["12500"]["state"]) for name, row in histories.items()}
    if any(state is None for state in states.values()):
        raise ValueError(f"invalid lineage founder for {task_id}")
    mode = str(candidate["state_mode"])
    scale = np.asarray(candidate["state_scale"], dtype=float)
    codec = candidate["codec"]
    founder_vectors = {
        "a": _normalized_state(states["form_a"], start, scale, mode),
        "b": _normalized_state(states["form_b"], start, scale, mode),
        "background": _normalized_state(states["mixed"], start, scale, mode),
    }
    founder_packets = {name: encode_codec(codec, vector) for name, vector in founder_vectors.items()}
    packet_midpoint = 0.5 * (founder_packets["a"] + founder_packets["b"])
    records: list[dict[str, Any]] = []
    for history in ("a", "b"):
        correct = founder_packets[history]
        opposite = founder_packets["b" if history == "a" else "a"]
        rng = np.random.Generator(np.random.Philox(_seed(config, "lineage-controls", task_id, seed_index, history)))
        shuffled, shuffle_method = normalized_shuffle(correct, rng)
        initial_packets = {
            "active": correct,
            "passive": correct,
            "erase_g2": correct,
            "rescue_g3": correct,
            "wrong_content": opposite,
            "inversion": 2.0 * packet_midpoint - correct,
            "normalized_shuffle": shuffled,
            "norm_matched_random": norm_matched_random(correct, rng),
            "recipient_control": np.zeros_like(correct),
        }
        for arm in LINEAGE_ARMS:
            donor_packet = np.asarray(initial_packets[arm], dtype=float).copy()
            for generation in range(1, int(settings["generations"]) + 1):
                keep, noise, damage_seed = common_damage(
                    config,
                    "contingency-lineage",
                    task_id,
                    int(seed_index),
                    generation,
                    len(donor_packet),
                    settings,
                )
                copied = copy_normalized(donor_packet, keep, noise, float(settings["retention"]))
                founder_reused = False
                donor_source = f"damaged-copy-g{generation}"
                if arm == "erase_g2" and generation == 2:
                    copied = np.zeros_like(copied)
                    donor_source = "explicit-erase-g2"
                if arm == "rescue_g3" and generation == 2:
                    copied = np.zeros_like(copied)
                    donor_source = "explicit-erase-g2"
                if arm == "rescue_g3" and generation == 3:
                    copied = correct.copy()
                    donor_source = "explicit-founder-rescue"
                    founder_reused = True
                if arm == "recipient_control":
                    child = start.copy()
                else:
                    decoded = decode_codec(codec, copied)
                    child = _state_from_normalized(decoded, start, scale, memory, mode)
                assay = _assay_transferred(backend, memory, child, config, candidate, reconstructed)
                cpu += float(assay["cpu_seconds"])
                adult = state_from_payload(assay["adult_state"])
                if adult is None:
                    raise ValueError("lineage assay returned no adult state")
                if arm == "passive":
                    next_packet = copied.copy()
                    next_source = f"damaged-copy-g{generation}"
                elif arm == "recipient_control":
                    next_packet = np.zeros_like(copied)
                    next_source = f"recipient-control-g{generation}"
                else:
                    adult_vector = _normalized_state(adult, start, scale, mode)
                    next_packet = encode_codec(codec, adult_vector)
                    next_source = f"adult-rewrite-g{generation}"
                if generation in set(int(value) for value in settings["checkpoints"]):
                    records.append(
                        {
                            "task_id": f"active-renewal|{task_id}|{seed_index}|{history}|{arm}|g{generation}",
                            "memory_task_id": task_id,
                            "model_id": int(memory.key.model_id),
                            "channel_class": candidate["channel_class"],
                            "seed_index": int(seed_index),
                            "philox_seed": int(philox_seed),
                            "history": history,
                            "condition": arm,
                            "generation": generation,
                            "codec_id": codec["codec_id"],
                            "payload_float_count": codec["payload_float_count"],
                            "damage_seed": int(damage_seed),
                            "donor_source": donor_source,
                            "next_donor_source": next_source,
                            "founder_reused": founder_reused or generation == 1,
                            "shuffle_method": shuffle_method if arm == "normalized_shuffle" else None,
                            "recipient_c_hash": digest(start.c),
                            "child_c_hash": digest(child.c),
                            "rulebook_inherited": False,
                            **assay,
                        }
                    )
                donor_packet = next_packet
    payload = {
        "protocol_digest": protocol_digest,
        "memory_task_id": task_id,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def renewal_decision(records: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config["active_renewal"]
    summaries: list[dict[str, Any]] = []
    for candidate in candidates:
        task_id = str(candidate["memory_task_id"])
        task_rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        checkpoints: dict[str, Any] = {}
        channel_pass = True
        for generation in (4, 8):
            generation_rows = [row for row in task_rows if int(row["generation"]) == generation]
            crosses: dict[str, list[float]] = {arm: [] for arm in LINEAGE_ARMS}
            for seed in settings["seed_indices"]:
                index = {(str(row["history"]), str(row["condition"])): row for row in generation_rows if int(row["seed_index"]) == int(seed)}
                for arm in LINEAGE_ARMS:
                    if ("a", arm) in index and ("b", arm) in index:
                        crosses[arm].append(0.5 * (float(index[("a", arm)]["score"]) - float(index[("b", arm)]["score"])))
            active = quantile(crosses["active"], 0.5)
            passive = quantile(crosses["passive"], 0.5)
            erase = quantile([abs(row) for row in crosses["erase_g2"]], 0.5)
            rescue = quantile(crosses["rescue_g3"], 0.5)
            advantage = None if active is None or passive is None else active - passive
            removal = None if active is None or erase is None else 1.0 - erase / max(abs(active), 1e-12)
            rescue_fraction = None if active is None or rescue is None else rescue / max(abs(active), 1e-12)
            control, control_medians = control_median_envelope(
                {
                    arm: crosses[arm]
                    for arm in (
                        "normalized_shuffle",
                        "norm_matched_random",
                        "recipient_control",
                    )
                }
            )
            consistent = sum(row >= float(settings["crossover_min"]) for row in crosses["active"])
            wrong_reversal = sum(row <= -float(settings["crossover_min"]) for row in crosses["wrong_content"])
            inversion_reversal = sum(row <= -float(settings["crossover_min"]) for row in crosses["inversion"])
            passed = bool(
                len(crosses["active"]) == len(settings["seed_indices"])
                and active is not None and active >= float(settings["crossover_min"])
                and advantage is not None and advantage >= float(settings["active_passive_advantage_min"])
                and removal is not None and removal >= float(settings["erase_removal_fraction_min"])
                and rescue_fraction is not None and rescue_fraction >= float(settings["rescue_fraction_min"])
                and control is not None and control <= float(settings["control_max_fraction"])
                and consistent >= int(settings["minimum_consistent_seeds"])
                and wrong_reversal >= int(settings["minimum_consistent_seeds"])
                and inversion_reversal >= int(settings["minimum_consistent_seeds"])
            )
            checkpoints[str(generation)] = {
                "median_active_crossover": active,
                "median_passive_crossover": passive,
                "active_passive_advantage": advantage,
                "erase_removal_fraction": removal,
                "rescue_fraction": rescue_fraction,
                "control_median_abs": control,
                "control_medians_abs": control_medians,
                "consistent_seed_count": consistent,
                "wrong_content_reversal_seed_count": wrong_reversal,
                "inversion_reversal_seed_count": inversion_reversal,
                "pass": passed,
            }
            channel_pass = channel_pass and passed
        summaries.append(
            {
                "memory_task_id": task_id,
                "model_id": int(candidate["model_id"]),
                "channel_class": candidate["channel_class"],
                "codec_id": candidate["codec"]["codec_id"],
                "checkpoints": checkpoints,
                "pass": channel_pass,
                "classification": (
                    "relational-plastic-heredity"
                    if channel_pass and candidate["channel_class"] == "relational"
                    else "exposure-state-plastic-heredity"
                    if channel_pass
                    else "no-active-renewal"
                ),
            }
        )
    return {
        "task_id": "active-renewal-decision",
        "channel_summaries": summaries,
        "pass_count": sum(bool(row["pass"]) for row in summaries),
        "pass": any(bool(row["pass"]) for row in summaries),
        "verdict": (
            "renewable-relational-or-exposure-state-channel"
            if any(bool(row["pass"]) for row in summaries)
            else "no-active-renewal"
        ),
    }


RECORD_FILES = (
    "timing-discovery.jsonl",
    "contingency-validation.jsonl",
    "exposure-validation.jsonl",
    "cue-calibration.jsonl",
    "two-cue-reversal.jsonl",
    "native-transfer.jsonl",
    "carrier-discovery.jsonl",
    "carrier-validation.jsonl",
    "active-renewal.jsonl",
)


def _projection_basis(atlas: Path, form_run: Path) -> dict[str, float]:
    """Derive frozen runtime units from the two sealed parent campaigns.

    A history contains 18 phase-equivalents, but only its first call pays the
    JAX compilation cost.  Projecting every equivalent as a fresh calibration
    phase therefore badly overstates the campaign.  The form parent supplies
    directly comparable complete-history timings and per-task cold-start
    overheads; the atlas remains the source for isolated phase timing.
    """

    calibration_phases = [
        float(row["selected_phase"]["cpu_seconds"])
        for row in _calibration_map(atlas).values()
        if row.get("selected_phase")
        and row["selected_phase"].get("cpu_seconds") is not None
    ]
    form_rows = [row for row in read_jsonl(form_run / "screen.jsonl")]
    warm_histories = [
        float(row["cpu_seconds"])
        for row in form_rows
        if row.get("condition") != "form_a" and row.get("cpu_seconds") is not None
    ]
    by_task: dict[str, dict[str, float]] = {}
    for row in form_rows:
        if row.get("cpu_seconds") is not None:
            by_task.setdefault(str(row["memory_task_id"]), {})[
                str(row["condition"])
            ] = float(row["cpu_seconds"])
    startup_deltas = []
    for conditions in by_task.values():
        warm = [value for name, value in conditions.items() if name != "form_a"]
        if "form_a" in conditions and warm:
            startup_deltas.append(max(0.0, conditions["form_a"] - float(np.median(warm))))
    history = float(np.median(warm_histories)) if warm_histories else 18.0
    return {
        "isolated_phase_cpu_seconds": (
            float(np.median(calibration_phases)) if calibration_phases else history / 18.0
        ),
        "warm_history_cpu_seconds": history,
        "cold_start_cpu_seconds": (
            float(np.median(startup_deltas)) if startup_deltas else history
        ),
        "develop_and_fingerprint_cpu_seconds": history * (7.0 / 18.0),
    }


def _parent_state_dimensions(form_run: Path) -> dict[str, int]:
    dimensions: dict[str, int] = {}
    for row in read_jsonl(form_run / "screen.jsonl"):
        task_id = str(row["memory_task_id"])
        if task_id in dimensions:
            continue
        state = row.get("training_state", {})
        dimensions[task_id] = len(state.get("y", ())) + len(state.get("w", ()))
    return dimensions


def _stage_workloads(config: Mapping[str, Any], form_run: Path) -> dict[str, dict[str, int]]:
    relational = len(config["relational_candidate_task_ids"])
    exposure = len(config["exposure_anchor_task_ids"])
    timing_seeds = len(config["timing_discovery"]["seed_indices"])
    validation_seeds = len(config["contingency_validation"]["seed_indices"])
    exposure_seeds = len(config["exposure_validation"]["seed_indices"])
    two_cue_cap = int(config["contingency_validation"]["max_two_cue_candidates"])
    two_cue_seeds = len(config["two_cue_reversal"]["seed_indices"])
    transfer_cap = int(config["two_cue_reversal"]["max_transfer_candidates"]) + int(
        config["exposure_validation"]["max_transfer_candidates"]
    )
    transfer_seeds = len(config["native_transfer"]["seed_indices"])
    carrier_cap = int(config["native_transfer"]["max_carrier_channels"])
    discovery_seeds = len(config["carrier_dissection"]["discovery_seed_indices"])
    carrier_seeds = len(config["carrier_dissection"]["validation_seed_indices"])
    renewal_seeds = len(config["active_renewal"]["seed_indices"])
    dimensions = _parent_state_dimensions(form_run)
    relational_dimensions = sorted(
        (dimensions.get(str(task_id), 128) for task_id in config["relational_candidate_task_ids"]),
        reverse=True,
    )
    cue_phases = sum(1 + 2 * max(0, value - 3) for value in relational_dimensions[:two_cue_cap])
    max_state_dimension = max(
        (dimensions.get(str(task_id), 128) for task_id in (
            *config["relational_candidate_task_ids"],
            *config["exposure_anchor_task_ids"],
        )),
        default=128,
    )
    codec_count = (
        len(config["carrier_dissection"]["sparse_sizes"])
        + len(config["carrier_dissection"]["pca_ranks"])
        + len(config["carrier_dissection"]["observability_ranks"])
        + 1
    )
    carrier_assays_per_channel = (
        1
        + max_state_dimension
        + 2 * codec_count
        + carrier_seeds * 2 * 8
    )
    return {
        "timing-discovery": {
            "parallelism": min(4, relational * timing_seeds),
            "histories": relational * timing_seeds * len(SCHEDULES),
            "cold_starts": relational * timing_seeds,
            "assays": 0,
            "isolated_phases": 0,
        },
        "contingency-validation": {
            "parallelism": min(4, relational * validation_seeds),
            "histories": relational * validation_seeds * (1 + len(CONTINGENCY_CONTROLS)),
            "cold_starts": relational * validation_seeds,
            "assays": 0,
            "isolated_phases": 0,
        },
        "exposure-validation": {
            "parallelism": min(4, exposure * exposure_seeds),
            "histories": exposure * exposure_seeds * 2,
            "cold_starts": exposure * exposure_seeds,
            "assays": 0,
            "isolated_phases": 0,
        },
        "cue-calibration": {
            "parallelism": min(4, two_cue_cap),
            "histories": 0,
            "cold_starts": two_cue_cap,
            "assays": 0,
            "isolated_phases": cue_phases,
        },
        "two-cue-reversal": {
            "parallelism": min(4, two_cue_cap * two_cue_seeds),
            "histories": two_cue_cap * two_cue_seeds * 3,
            "cold_starts": two_cue_cap * two_cue_seeds,
            "assays": 0,
            "isolated_phases": 0,
        },
        "native-transfer": {
            "parallelism": min(4, transfer_cap * transfer_seeds),
            "histories": transfer_cap * transfer_seeds * 3,
            "cold_starts": transfer_cap * transfer_seeds,
            "assays": transfer_cap * transfer_seeds * 2 * 2 * 2 * len(TRANSFER_CONTROLS),
            "isolated_phases": 0,
        },
        "carrier-dissection": {
            "parallelism": min(4, carrier_cap),
            "histories": carrier_cap * (discovery_seeds + carrier_seeds) * 3,
            "cold_starts": carrier_cap,
            "assays": carrier_cap * carrier_assays_per_channel,
            "isolated_phases": 0,
        },
        "active-renewal": {
            "parallelism": min(4, carrier_cap * renewal_seeds),
            "histories": carrier_cap * renewal_seeds * 3,
            "cold_starts": carrier_cap * renewal_seeds,
            "assays": carrier_cap * renewal_seeds * 2 * len(LINEAGE_ARMS) * int(config["active_renewal"]["generations"]),
            "isolated_phases": 0,
        },
    }


def _project_campaign(config: Mapping[str, Any], atlas: Path, form_run: Path) -> dict[str, Any]:
    basis = _projection_basis(atlas, form_run)
    workloads = _stage_workloads(config, form_run)
    safety = float(config["projection_safety_factor"])
    stages: dict[str, float] = {}
    for stage, workload in workloads.items():
        raw = (
            workload["histories"] * basis["warm_history_cpu_seconds"]
            + workload["cold_starts"] * basis["cold_start_cpu_seconds"]
            + workload["assays"] * basis["develop_and_fingerprint_cpu_seconds"]
            + workload["isolated_phases"] * basis["isolated_phase_cpu_seconds"]
        )
        stages[stage] = float(raw * safety)
    total = float(sum(stages.values()))
    parallelism = {
        stage: max(1, int(workload["parallelism"]))
        for stage, workload in workloads.items()
    }
    stage_wall = {
        stage: stages[stage] / parallelism[stage]
        for stage in stages
    }
    return {
        "basis": basis,
        "workloads": workloads,
        "safety_factor": safety,
        "stage_projected_cpu_seconds": stages,
        "stage_parallelism_cap": parallelism,
        "stage_projected_wall_seconds_at_four_workers": stage_wall,
        "worst_case_aggregate_cpu_seconds": total,
        "worst_case_active_wall_seconds_at_four_workers": float(sum(stage_wall.values())),
    }


class BudgetGateStop(RuntimeError):
    pass


def _exposure_transfer_candidates(records: Sequence[Mapping[str, Any]], decision: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for candidate in decision.get("transfer_candidates", ()):
        task_id = str(candidate["memory_task_id"])
        rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        high = _mean_fingerprint(rows, "high_ucs", "12500")
        low = _mean_fingerprint(rows, "low_ucs", "12500")
        if high is None or low is None:
            continue
        result.append(
            {
                **dict(candidate),
                "reference_fingerprints": {"form_a": high, "form_b": low, "mixed": 0.5 * (high + low)},
            }
        )
    return result


def _augment_relational_candidates(candidates: Sequence[Mapping[str, Any]], audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs = _reference_map(audit)
    return [
        {
            **dict(candidate),
            "selected_ucs_bound_index": int(refs[str(candidate["memory_task_id"])]["selected_ucs_bound_index"]),
        }
        for candidate in candidates
    ]


def analyze_contingency(output: Path, final_status: str | None = None) -> dict[str, Any]:
    output = output.resolve()
    state_path = output / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {"status": final_status or "unknown"}
    status = final_status or str(state.get("status", "unknown"))
    ledger_path = output / "resource-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.is_file() else {}
    final_path = output / "decision.json"
    final = json.loads(final_path.read_text(encoding="utf-8")) if final_path.is_file() else {"pass": False, "verdict": "incomplete"}
    counts = {name: sum(1 for _ in read_jsonl(output / name)) if (output / name).is_file() else 0 for name in RECORD_FILES}
    required = ["registration.json", "parent-gate.json", "residual-audit.json", "decision.json", *RECORD_FILES]
    minimum = all((output / name).is_file() for name in required)
    result = {
        "task_id": "contingency-analysis",
        "experiment_id": "grn-contingency-memory-v1",
        "run_status": status,
        "minimum_completion_gate": bool(minimum),
        "decision_pass": bool(final.get("pass", False)),
        "verdict": final.get("verdict", "incomplete"),
        "budget_gate_stop": bool(final.get("budget_gate_stop", False)),
        "record_counts": counts,
        "active_wall_seconds": float(ledger.get("active_wall_seconds", 0.0)),
        "aggregate_cpu_seconds": float(ledger.get("aggregate_cpu_seconds", 0.0)),
        "claim_boundary": final.get("claim_boundary"),
    }
    write_json(output / "analysis.json", result)
    report = f"""# GRN contingency memory and plastic-heredity campaign V1

Status: **{status}**

Verdict: **{result['verdict']}**

Final gate passed: **{str(result['decision_pass']).lower()}**

This campaign keeps relational contingency memory separate from durable
exposure-state memory.  Only channels passing counterbalanced content,
same-rulebook transfer, causal carrier, and active-renewal controls qualify for
the corresponding exploratory plastic-heredity label.

Records: {json.dumps(counts, sort_keys=True)}

Resource use: {result['active_wall_seconds']:.3f} active wall seconds and
{result['aggregate_cpu_seconds']:.3f} aggregate worker CPU seconds.

Budget gate stop: {str(result['budget_gate_stop']).lower()}.

Claim boundary: {result['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return result


class ContingencyCampaign:
    def __init__(
        self,
        config_path: Path,
        atlas: Path,
        form_run: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_contingency_config(self.config_path)
        self.atlas = atlas.resolve()
        self.form_run = form_run.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("contingency workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed contingency campaign cannot be resumed")
        self.parent_gate = validate_parents(self.config, self.atlas, self.form_run, self.upstream)
        self.output.mkdir(parents=True, exist_ok=True)
        self.ledger = ResourceLedger(self.output, self.config)
        self.budget_stop_stage: str | None = None

    def _register(self) -> None:
        path = self.output / "registration.json"
        payload = {
            "experiment_id": self.config["experiment_id"],
            "protocol": self.config,
            "protocol_digest": digest(self.config),
            "workers": self.workers,
            "upstream": self.parent_gate["upstream"],
            "atlas": self.parent_gate["atlas"],
            "form_run": self.parent_gate["form_run"],
            "runtime": _runtime_manifest(),
            "record_files": list(RECORD_FILES),
        }
        if path.is_file():
            prior = json.loads(path.read_text(encoding="utf-8"))
            for key in ("experiment_id", "protocol_digest", "atlas", "form_run"):
                if prior.get(key) != payload.get(key):
                    raise ValueError(f"resumed contingency registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"]["container_image_id"]:
                raise ValueError("resumed contingency image differs")
        write_json(path, payload)
        write_json(self.output / "parent-gate.json", {"task_id": "parent-gate", "pass": True, **self.parent_gate})
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "relational": "Dose-matched temporal contingency creates a durable cue-specific state.",
                "exposure": "UCS history alone can create a durable transferable state without association.",
                "renewal": "A compact causal state is actively rewritten across a defined renewal boundary.",
                "negative_is_informative": True,
                "threshold_relaxation_allowed": False,
            },
        )
        if not (self.output / "runtime-incidents.json").is_file():
            write_json(self.output / "runtime-incidents.json", {"incidents": []})
        if not (self.output / "codebooks.json").is_file():
            write_json(
                self.output / "codebooks.json",
                {
                    "discovery_seed_indices": self.config["carrier_dissection"]["discovery_seed_indices"],
                    "validation_seed_indices": self.config["carrier_dissection"]["validation_seed_indices"],
                    "leakage_allowed": False,
                    "channels": [],
                },
            )
        for name in RECORD_FILES:
            if not (self.output / name).is_file():
                _write_jsonl(self.output / name, [])

    def _state(self, status: str, stage: str, **extra: Any) -> None:
        write_json(
            self.output / "state.json",
            {
                "status": status,
                "stage": stage,
                "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **extra,
            },
        )
        self.ledger.checkpoint(stage, _all_shard_cpu(self.output))

    def _require_budget(self, stage: str) -> None:
        self.ledger.checkpoint(stage, _all_shard_cpu(self.output))
        self.ledger.enforce_hard()
        registration = json.loads((self.output / "registration.json").read_text(encoding="utf-8"))
        projection = registration.get("projection", {})
        stage_cpu = float(projection.get("stage_projected_cpu_seconds", {}).get(stage, 0.0))
        parallelism = int(
            projection.get("stage_parallelism_cap", {}).get(stage, self.workers)
        )
        stage_wall = stage_cpu / max(1, min(self.workers, parallelism))
        remaining_cpu = float(self.config["soft_aggregate_cpu_seconds"]) - self.ledger.cpu_seconds
        remaining_wall = float(self.config["soft_wall_seconds"]) - self.ledger.wall_seconds
        if not self.ledger.may_start() or stage_cpu > remaining_cpu or stage_wall > remaining_wall:
            self.budget_stop_stage = stage
            raise BudgetGateStop(f"insufficient complete-stage budget before {stage}")

    def _store_projection(self) -> None:
        registration = json.loads((self.output / "registration.json").read_text(encoding="utf-8"))
        registration["projection"] = _project_campaign(
            self.config, self.atlas, self.form_run
        )
        write_json(self.output / "registration.json", registration)

    def _run_history_stage(self, mode: str, tasks: Sequence[str], seeds: Sequence[int], conditions: Sequence[str], output_name: str) -> list[dict[str, Any]]:
        args = [
            (
                str(self.config_path),
                str(self.atlas),
                str(self.upstream),
                str(self.output),
                mode,
                str(task_id),
                int(seed),
                list(conditions),
                f"task-{task_id}-seed-{seed}",
            )
            for task_id in tasks
            for seed in seeds
        ]
        shards = _parallel(_history_worker, args, min(self.workers, len(args)))
        return _merge_shards(self.output, output_name, shards)

    def run(self) -> int:
        self._register()
        self._store_projection()
        self.ledger.start_heartbeat()
        decisions: dict[str, Any] = {}
        try:
            self._state("running", "residual-audit")
            audit = residual_audit(self.config, self.atlas, self.form_run)
            write_json(self.output / "residual-audit.json", audit)

            self._require_budget("timing-discovery")
            self._state("running", "timing-discovery")
            timing_records = self._run_history_stage(
                "timing-discovery",
                self.config["relational_candidate_task_ids"],
                self.config["timing_discovery"]["seed_indices"],
                list(SCHEDULES),
                "timing-discovery",
            )
            timing = timing_selection(timing_records, audit, self.config)
            decisions["timing"] = timing
            write_json(self.output / "timing-selection.json", timing)

            self._require_budget("contingency-validation")
            self._state("running", "contingency-validation")
            selected_map = {str(row["memory_task_id"]): str(row["selected_schedule"]) for row in timing["selections"]}
            validation_shards: list[dict[str, Any]] = []
            for task_id in self.config["relational_candidate_task_ids"]:
                validation_shards.extend(
                    _parallel(
                        _history_worker,
                        [
                            (
                                str(self.config_path), str(self.atlas), str(self.upstream), str(self.output),
                                "contingency-validation", str(task_id), int(seed),
                                [selected_map[str(task_id)], *CONTINGENCY_CONTROLS],
                                f"task-{task_id}-seed-{seed}",
                            )
                            for seed in self.config["contingency_validation"]["seed_indices"]
                        ],
                        min(self.workers, len(self.config["contingency_validation"]["seed_indices"])),
                    )
                )
            contingency_records = _merge_shards(self.output, "contingency-validation", validation_shards)
            contingency = contingency_decision(contingency_records, timing, audit, self.config)
            decisions["contingency"] = contingency
            write_json(self.output / "contingency-decision.json", contingency)

            self._require_budget("exposure-validation")
            self._state("running", "exposure-validation")
            exposure_records = self._run_history_stage(
                "exposure",
                self.config["exposure_anchor_task_ids"],
                self.config["exposure_validation"]["seed_indices"],
                ["low_ucs", "high_ucs"],
                "exposure-validation",
            )
            exposure = exposure_decision(exposure_records, self.config)
            decisions["exposure"] = exposure
            write_json(self.output / "exposure-decision.json", exposure)

            relational_candidates = _augment_relational_candidates(contingency["two_cue_candidates"], audit)
            cue_records: list[dict[str, Any]] = []
            two_cue_records: list[dict[str, Any]] = []
            if relational_candidates:
                self._require_budget("cue-calibration")
                self._state("running", "cue-calibration")
                cue_shards = _parallel(
                    _cue_calibration_worker,
                    [
                        (str(self.config_path), str(self.atlas), str(self.upstream), str(self.output), row["memory_task_id"], f"task-{row['memory_task_id']}")
                        for row in relational_candidates
                    ],
                    min(self.workers, len(relational_candidates)),
                )
                cue_records = _merge_shards(self.output, "cue-calibration", cue_shards)
                self._require_budget("two-cue-reversal")
                self._state("running", "two-cue-reversal")
                two_cue_records = self._run_history_stage(
                    "two-cue",
                    [str(row["memory_task_id"]) for row in relational_candidates],
                    self.config["two_cue_reversal"]["seed_indices"],
                    ["form_a", "form_b", "mixed"],
                    "two-cue-reversal",
                )
            else:
                _write_jsonl(self.output / "cue-calibration.jsonl", [])
                _write_jsonl(self.output / "two-cue-reversal.jsonl", [])
            two_cue = two_cue_decision(two_cue_records, relational_candidates, self.config)
            decisions["two_cue"] = two_cue
            write_json(self.output / "two-cue-decision.json", two_cue)

            transfer_candidates = [
                *_augment_relational_candidates(two_cue["transfer_candidates"], audit),
                *_exposure_transfer_candidates(exposure_records, exposure),
            ]
            transfer_records: list[dict[str, Any]] = []
            if transfer_candidates:
                self._require_budget("native-transfer")
                self._state("running", "native-transfer")
                transfer_shards = _parallel(
                    _transfer_worker,
                    [
                        (
                            str(self.config_path), str(self.atlas), str(self.upstream), str(self.output), candidate, int(seed),
                            f"task-{candidate['memory_task_id']}-seed-{seed}",
                        )
                        for candidate in transfer_candidates
                        for seed in self.config["native_transfer"]["seed_indices"]
                    ],
                    self.workers,
                )
                transfer_records = _merge_shards(self.output, "native-transfer", transfer_shards)
            else:
                _write_jsonl(self.output / "native-transfer.jsonl", [])
            transfer = native_transfer_decision(transfer_records, transfer_candidates, self.config)
            decisions["transfer"] = transfer
            write_json(self.output / "native-transfer-decision.json", transfer)

            carrier_shards: list[dict[str, Any]] = []
            if transfer["carrier_candidates"]:
                self._require_budget("carrier-dissection")
                self._state("running", "carrier-dissection")
                carrier_shards = _parallel(
                    _carrier_worker,
                    [
                        (str(self.config_path), str(self.atlas), str(self.upstream), str(self.output), candidate, f"task-{candidate['memory_task_id']}")
                        for candidate in transfer["carrier_candidates"]
                    ],
                    min(self.workers, len(transfer["carrier_candidates"])),
                )
            carrier_discovery = [dict(row) for shard in carrier_shards for row in shard.get("discovery_records", ())]
            carrier_validation = [dict(row) for shard in carrier_shards for row in shard.get("validation_records", ())]
            _write_jsonl(self.output / "carrier-discovery.jsonl", carrier_discovery)
            _write_jsonl(self.output / "carrier-validation.jsonl", carrier_validation)
            write_json(
                self.output / "codebooks.json",
                {
                    "discovery_seed_indices": self.config["carrier_dissection"]["discovery_seed_indices"],
                    "validation_seed_indices": self.config["carrier_dissection"]["validation_seed_indices"],
                    "leakage_allowed": False,
                    "channels": [
                        {"memory_task_id": shard["memory_task_id"], "codebooks": shard.get("codebooks", ()), "selected_codec": shard.get("selected_codec")}
                        for shard in carrier_shards
                    ],
                },
            )
            carrier = carrier_decision(carrier_shards, self.config)
            decisions["carrier"] = carrier
            write_json(self.output / "carrier-decision.json", carrier)

            renewal_records: list[dict[str, Any]] = []
            if carrier["renewal_candidates"]:
                self._require_budget("active-renewal")
                self._state("running", "active-renewal")
                renewal_shards = _parallel(
                    _lineage_worker,
                    [
                        (
                            str(self.config_path), str(self.atlas), str(self.upstream), str(self.output), candidate, int(seed),
                            f"task-{candidate['memory_task_id']}-seed-{seed}",
                        )
                        for candidate in carrier["renewal_candidates"]
                        for seed in self.config["active_renewal"]["seed_indices"]
                    ],
                    self.workers,
                )
                renewal_records = _merge_shards(self.output, "active-renewal", renewal_shards)
            else:
                _write_jsonl(self.output / "active-renewal.jsonl", [])
            renewal = renewal_decision(renewal_records, carrier["renewal_candidates"], self.config)
            decisions["renewal"] = renewal
            write_json(self.output / "renewal-decision.json", renewal)
            self._finalize(decisions, budget_stop=False)
            return 0
        except BudgetGateStop as error:
            self._state("finalizing", "budget-gate-stop", error=str(error))
            self._finalize(decisions, budget_stop=True)
            return 0
        except BaseException as error:
            incidents = json.loads((self.output / "runtime-incidents.json").read_text(encoding="utf-8"))
            incidents.setdefault("incidents", []).append(
                {
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "stage": json.loads((self.output / "state.json").read_text(encoding="utf-8")).get("stage"),
                    "error": repr(error),
                }
            )
            write_json(self.output / "runtime-incidents.json", incidents)
            self._state("failed", "exception", error=repr(error))
            self.ledger.close()
            raise

    def _finalize(self, decisions: Mapping[str, Any], budget_stop: bool) -> None:
        renewal = decisions.get("renewal", {"pass": False})
        carrier = decisions.get("carrier", {"pass": False})
        transfer = decisions.get("transfer", {"pass": False})
        two_cue = decisions.get("two_cue", {"pass": False})
        contingency = decisions.get("contingency", {"pass": False})
        exposure = decisions.get("exposure", {"pass": False})
        verdict = (
            "budget-gate-stop"
            if budget_stop
            else "renewable-plastic-heredity-lead"
            if renewal.get("pass")
            else "causal-compact-carrier-without-renewal"
            if carrier.get("pass")
            else "native-transfer-without-causal-carrier"
            if transfer.get("pass")
            else "counterbalanced-relational-form-without-transfer"
            if two_cue.get("pass")
            else "single-cue-contingency-lead-only"
            if contingency.get("pass")
            else "durable-exposure-state-only"
            if exposure.get("pass")
            else "no-robust-contingency-or-exposure-state"
        )
        final = {
            "task_id": "contingency-campaign-decision",
            "pass": bool(renewal.get("pass", False)),
            "verdict": verdict,
            "budget_gate_stop": budget_stop,
            "budget_gate_stop_stage": self.budget_stop_stage,
            "stage_passes": {name: bool(value.get("pass", False)) for name, value in decisions.items()},
            "claim_boundary": self.config["claim_boundary"],
        }
        write_json(self.output / "decision.json", final)
        self.ledger.checkpoint("finalizing", _all_shard_cpu(self.output))
        self.ledger.close()
        self._state("completed", "complete", verdict=verdict)
        analyze_contingency(self.output, final_status="completed")
        write_checksums(self.output)


def run_contingency(config: Path, atlas: Path, form_run: Path, upstream: Path, output: Path, workers: int = 4) -> int:
    return ContingencyCampaign(config, atlas, form_run, upstream, output, workers).run()


def smoke_contingency(config_path: Path, atlas: Path, form_run: Path, upstream: Path, output: Path) -> dict[str, Any]:
    config = load_contingency_config(config_path)
    atlas = atlas.resolve()
    form_run = form_run.resolve()
    upstream = upstream.resolve()
    parents = validate_parents(config, atlas, form_run, upstream)
    task_id = str(config["relational_candidate_task_ids"][0])
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
    start = _naive_start(atlas, task_id)
    audit = residual_audit(config, atlas, form_run)
    reference = _reference_map(audit)[task_id]
    bound = int(reference["selected_ucs_bound_index"])
    cs, ucs, _ = _stimulus_values(memory, bound)
    tokens = config["schedule_templates"]["coincident"]
    training = run_epoch_schedule(
        backend,
        start,
        schedule_stimuli(tokens, cs, ucs),
        float(config["epoch_duration"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
    )
    washout = backend.run_unstimulated(
        training.state,
        float(config["washout_checkpoints"][0]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
        float(config["phase_duration"]),
    )
    fingerprint = _fingerprint(
        backend, memory, washout.state, config, bound
    )
    smoke_score = axis_score(
        fingerprint["fingerprint"],
        reference["references"]["2500"]["background"],
        reference["references"]["2500"]["direction"],
    )
    projection = _project_campaign(config, atlas, form_run)
    allowed = bool(
        training.valid
        and washout.valid
        and fingerprint["valid"]
        and schedule_exposure_counts(tokens) == {"cs": 5, "ucs": 5, "coincident": 5}
        and projection["worst_case_aggregate_cpu_seconds"] < float(config["soft_aggregate_cpu_seconds"])
        and projection["worst_case_active_wall_seconds_at_four_workers"] < float(config["soft_wall_seconds"])
    )
    result = {
        "target": "contingency-memory-campaign",
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "atlas_parent_manifest_sha256": parents["atlas"]["manifest_sha256"],
        "form_parent_manifest_sha256": parents["form_run"]["manifest_sha256"],
        "biological_probe": {
            "memory_task_id": task_id,
            "valid": bool(training.valid and washout.valid and fingerprint["valid"]),
            "schedule": "coincident",
            "schedule_exposures": schedule_exposure_counts(tokens),
            "training_cpu_seconds": float(training.cpu_seconds),
            "washout_cpu_seconds": float(washout.cpu_seconds),
            "fingerprint_cpu_seconds": float(fingerprint["cpu_seconds"]),
            "cpu_seconds": float(training.cpu_seconds + washout.cpu_seconds + fingerprint["cpu_seconds"]),
            "wall_seconds": float(training.wall_seconds + washout.wall_seconds + fingerprint["wall_seconds"]),
            "residual_axis_score": smoke_score,
        },
        "projection": projection,
        "worker_cap": int(config["max_workers"]),
        "deterministic_batch_plan": "task-by-seed shards with conditional candidate caps",
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "smoke.json", result)
    return result


def contingency_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {"output": str(output), "sealed": (output / "SHA256SUMS").is_file()}
    for name in (
        "state", "resource-ledger", "residual-audit", "timing-selection", "contingency-decision",
        "exposure-decision", "two-cue-decision", "native-transfer-decision", "carrier-decision",
        "renewal-decision", "decision", "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    for name in RECORD_FILES:
        path = output / name
        if path.is_file():
            result[f"{Path(name).stem.replace('-', '_')}_records"] = sum(1 for _ in read_jsonl(path))
    return result
