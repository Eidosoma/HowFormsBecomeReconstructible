"""Continuous-GRN carrier ladder inspired by the cellular-automata assays.

The ladder is intentionally exploratory and stage separated.  Every stage is
an independently sealed, resumable run with an immutable predecessor.  A
negative gate is a completed result, not an invitation to relax thresholds.
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
from .engine import JaxBackend, State
from .renewal import ResourceLedger
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    validate_upstream,
)


STAGES = (
    "form-qualification",
    "native-transfer",
    "compression",
    "native-lineage",
    "engineered-renewal",
    "g16-replication",
)
FORM_ARMS = (
    "form_a",
    "form_b",
    "naive",
    "cs_only",
    "low_ucs_only",
    "high_ucs_only",
)
TRANSFER_CONDITIONS = (
    "intact",
    "opposite_history",
    "midpoint_inversion",
    "zero",
    "normalized_shuffle",
    "norm_matched_random",
    "ucs_only",
)
COMPRESSION_CONDITIONS = (
    "intact",
    "inversion",
    "zero",
    "normalized_shuffle",
    "norm_matched_random",
    "ucs_only",
)
NATIVE_LINEAGE_ARMS = (
    "active_rewrite",
    "passive",
    "erase_g2",
    "rescue_g3",
    "wrong_history",
    "inversion",
    "normalized_shuffle",
    "norm_matched_random",
    "control",
)
ENGINEERED_ARMS = (
    "intact",
    "writer_off",
    "reader_off",
    "renewal_off",
    "passive",
    "erase",
    "rescue",
    "opposite",
    "inversion",
    "normalized_shuffle",
    "zero",
)


def load_ca_bridge_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported CA-bridge schema")
    if config.get("experiment_kind") != "ca-bridge-carrier-ladder":
        raise ValueError("not a CA-bridge carrier-ladder protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("CA-bridge protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("CA-bridge protocol does not pin the release generator")
    if tuple(config.get("stages", ())) != STAGES:
        raise ValueError("CA-bridge stage order changed")
    expected_parents = {
        "form-qualification": None,
        "native-transfer": "form-qualification",
        "compression": "native-transfer",
        "native-lineage": "native-transfer",
        "engineered-renewal": "compression",
        "g16-replication": "engineered-renewal",
    }
    if config.get("stage_parents") != expected_parents:
        raise ValueError("CA-bridge stage-parent graph changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("CA-bridge protocol must cap workers at four")
    if not (
        0
        < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 14400.0
    ):
        raise ValueError("CA-bridge wall-time contract is invalid")
    if not (
        0
        < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 57600.0
    ):
        raise ValueError("CA-bridge aggregate CPU contract is invalid")
    expected = {"delta_t": 0.01, "phase_duration": 2500.0, "pulse_count": 5}
    for key, value in expected.items():
        if not math.isclose(float(config.get(key, -1)), value):
            raise ValueError(f"historical setting differs for {key}")
    if [float(value) for value in config["acquisition_checkpoints"]] != [2500.0, 12500.0]:
        raise ValueError("acquisition checkpoints changed")
    if tuple(config.get("form_arms", ())) != FORM_ARMS:
        raise ValueError("form controls changed")
    if list(config.get("fingerprint_probes", ())) != [
        "no_input",
        "cs",
        "selected_control",
        "cs_selected_control",
        "opposite_control",
        "cs_opposite_control",
    ]:
        raise ValueError("six-probe fingerprint changed")
    tasks = [str(value) for value in config.get("fixed_cohort_task_ids", ())]
    if len(tasks) != 24 or len(set(tasks)) != 24:
        raise ValueError("CA-bridge cohort must contain 24 unique tasks")
    if int(config["qualification"]["validation_seeds"]) != 4:
        raise ValueError("qualification seed count changed")
    if int(config["native_transfer"]["seeds"]) != 8:
        raise ValueError("native-transfer seed count changed")
    if int(config["compression"]["validation_seeds"]) != 8:
        raise ValueError("compression validation seed count changed")
    if [float(value) for value in config["compression"]["reader_couplings"]] != [
        0.25,
        0.50,
        0.75,
    ]:
        raise ValueError("compression reader-coupling ladder changed")
    if [int(value) for value in config["native_lineage"]["checkpoints"]] != [1, 2, 4, 8]:
        raise ValueError("native-lineage checkpoint ladder changed")
    if [int(value) for value in config["engineered_renewal"]["validation_checkpoints"]] != [8]:
        raise ValueError("engineered validation endpoint changed")
    if [int(value) for value in config["g16_replication"]["checkpoints"]] != [8, 16]:
        raise ValueError("G16 replication checkpoints changed")
    return config


def validate_ca_bridge_stage(config: Mapping[str, Any], stage: str) -> str:
    if stage not in config["stages"]:
        raise ValueError(f"unknown CA-bridge stage: {stage}")
    return stage


def _seed(config: Mapping[str, Any], *parts: object) -> int:
    payload = "|".join([str(config["experiment_seed"]), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def transform_fingerprint(values: Sequence[float]) -> np.ndarray:
    return np.arcsinh(np.asarray(values, dtype=float))


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


def form_score(
    values: Sequence[float], form_a: Sequence[float], form_b: Sequence[float]
) -> float | None:
    """Frozen A/B coordinate with A=+1 and B=-1."""

    values_array = np.asarray(values, dtype=float)
    a = np.asarray(form_a, dtype=float)
    b = np.asarray(form_b, dtype=float)
    if values_array.shape != a.shape or values_array.shape != b.shape:
        raise ValueError("form-score shapes differ")
    direction = a - b
    denominator = float(np.dot(direction, direction))
    if denominator <= 1e-12 or not np.isfinite(denominator):
        return None
    midpoint = 0.5 * (a + b)
    value = float(2.0 * np.dot(values_array - midpoint, direction) / denominator)
    return value if np.isfinite(value) else None


def state_mode_available(form_a: State, form_b: State, mode: str) -> bool:
    if mode == "y":
        return bool(form_a.y.size)
    if mode == "yw":
        return bool(
            form_a.w.size
            and form_a.w.shape == form_b.w.shape
            and np.linalg.norm(form_a.w - form_b.w) > 1e-12
        )
    raise ValueError(f"unknown state mode: {mode}")


def state_vector(state: State, mode: str) -> np.ndarray:
    if mode == "y":
        return np.asarray(state.y, dtype=float).copy()
    if mode == "yw":
        return np.concatenate((np.asarray(state.y, dtype=float), np.asarray(state.w, dtype=float)))
    raise ValueError(f"unknown state mode: {mode}")


def state_scale(memory: Any, baseline: State, form_a: State, form_b: State, mode: str) -> np.ndarray:
    y_scale = np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8)
    if mode == "y":
        return y_scale
    w_scale = np.maximum.reduce(
        (
            np.abs(form_a.w - form_b.w),
            np.abs(baseline.w),
            np.full_like(baseline.w, 1e-8),
        )
    )
    return np.concatenate((y_scale, w_scale))


def state_from_vector(vector: Sequence[float], baseline: State, memory: Any, mode: str) -> State:
    values = np.asarray(vector, dtype=float)
    y_count = len(baseline.y)
    expected = y_count if mode == "y" else y_count + len(baseline.w)
    if values.shape != (expected,):
        raise ValueError("state-vector length differs from selected mode")
    y = np.clip(values[:y_count], memory.bounds[:, 0], memory.bounds[:, 1])
    w = baseline.w.copy() if mode == "y" else values[y_count:].copy()
    # c is deliberately taken only from the recipient baseline.
    return State(y.copy(), w, baseline.c.copy(), float(baseline.t))


def normalized_state_vector(
    state: State, baseline: State, scale: np.ndarray, mode: str
) -> np.ndarray:
    return (state_vector(state, mode) - state_vector(baseline, mode)) / np.asarray(scale)


def state_from_normalized(
    values: Sequence[float], baseline: State, scale: np.ndarray, memory: Any, mode: str
) -> State:
    vector = state_vector(baseline, mode) + np.asarray(values, dtype=float) * np.asarray(scale)
    return state_from_vector(vector, baseline, memory, mode)


def common_damage(
    config: Mapping[str, Any],
    namespace: str,
    task_id: str,
    seed_index: int,
    generation: int,
    size: int,
    environment: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, int]:
    seed_value = _seed(config, namespace, task_id, seed_index, generation, size)
    rng = np.random.Generator(np.random.Philox(seed_value))
    keep = rng.random(size) >= float(environment["dropout"])
    noise = rng.normal(0.0, float(environment["noise_sigma"]), size)
    return keep, noise, seed_value


def copy_normalized(
    values: Sequence[float], keep: np.ndarray, noise: np.ndarray, retention: float
) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape != keep.shape or array.shape != noise.shape:
        raise ValueError("copy-normalized shapes differ")
    return np.where(keep, float(retention) * array * (1.0 + noise), 0.0)


def invert_about_midpoint(values: Sequence[float], midpoint: Sequence[float]) -> np.ndarray:
    return 2.0 * np.asarray(midpoint, dtype=float) - np.asarray(values, dtype=float)


def normalized_shuffle(values: Sequence[float], rng: np.random.Generator) -> tuple[np.ndarray, str]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return array.copy(), "empty"
    if array.size == 1:
        # A literal singleton permutation is a silent no-op.  Randomising its
        # polarity is the registered destructive surrogate.
        sign = -1.0 if int(rng.integers(0, 2)) == 0 else 1.0
        return np.asarray([sign * abs(float(array[0]))]), "singleton-random-sign-surrogate"
    return array[rng.permutation(array.size)], "permutation"


def norm_matched_random(values: Sequence[float], rng: np.random.Generator) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    target = float(np.linalg.norm(array))
    if target <= 1e-12 or array.size == 0:
        return np.zeros_like(array)
    direction = rng.normal(size=array.size)
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        direction = np.ones(array.size)
        norm = float(np.linalg.norm(direction))
    return target * direction / norm


def next_native_donor(
    arm: str, post_copy: State, adult: State, generation: int
) -> tuple[State, str]:
    if arm == "passive":
        return post_copy.copy(), f"post-copy-g{generation}"
    return adult.copy(), f"adult-g{generation}"


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(row) + "\n" for row in records))


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


def _identity_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    return {"key": str(args[-1]), "payload": list(args[:-1])}


def _merge_shards(output: Path, name: str, shards: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    records = [dict(row) for shard in shards for row in shard.get("records", ())]
    task_ids = [str(row["task_id"]) for row in records]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError(f"duplicate task IDs while merging {name}")
    _write_jsonl(output / f"{name}.jsonl", records)
    return records


def _all_shard_cpu(output: Path) -> float:
    total = 0.0
    root = output / ".shards"
    for path in sorted(root.rglob("*.json")) if root.is_dir() else ():
        try:
            total += float(json.loads(path.read_text(encoding="utf-8")).get("aggregate_cpu_seconds", 0.0))
        except (OSError, TypeError, ValueError):
            continue
    return total


def _calibration_map(atlas: Path) -> dict[str, dict[str, Any]]:
    return {str(row["memory_task_id"]): row for row in read_jsonl(atlas / "calibration.jsonl")}


def _history_map(atlas: Path) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row["memory_task_id"]), str(row["arm"])): row
        for row in read_jsonl(atlas / "histories.jsonl")
    }


def _atlas_naive_start(histories: Mapping[tuple[str, str], Mapping[str, Any]], task_id: str) -> State:
    payload = histories[(task_id, "naive")]["start"]["state"]
    state = state_from_payload(payload)
    if state is None:
        raise ValueError(f"invalid frozen naive start for {task_id}")
    return state


def _probe_specs(memory: Any, calibration: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected = calibration.get("reconstructed_ucs_bound_index")
    if memory.ucs_id is None or selected is None:
        raise ValueError(f"task {memory.key.task_id} lacks a reconstructed UCS")
    selected = int(selected)
    opposite = 1 - selected
    cs_value = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
    selected_value = float(memory.bounds[memory.ucs_id, selected])
    opposite_value = float(memory.bounds[memory.ucs_id, opposite])
    return [
        {"name": "no_input", "stimuli": None},
        {"name": "cs", "stimuli": {int(memory.cs_id): cs_value}},
        {"name": "selected_control", "stimuli": {int(memory.ucs_id): selected_value}},
        {
            "name": "cs_selected_control",
            "stimuli": {int(memory.cs_id): cs_value, int(memory.ucs_id): selected_value},
        },
        {"name": "opposite_control", "stimuli": {int(memory.ucs_id): opposite_value}},
        {
            "name": "cs_opposite_control",
            "stimuli": {int(memory.cs_id): cs_value, int(memory.ucs_id): opposite_value},
        },
    ]


def _form_stimuli(memory: Any, calibration: Mapping[str, Any], arm: str) -> Mapping[int, float] | None:
    selected = calibration.get("reconstructed_ucs_bound_index")
    if memory.ucs_id is None or selected is None:
        raise ValueError(f"task {memory.key.task_id} lacks a reconstructed UCS")
    selected = int(selected)
    cs = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
    low = float(memory.bounds[memory.ucs_id, 0])
    high = float(memory.bounds[memory.ucs_id, 1])
    if arm == "form_a":
        return {int(memory.cs_id): cs, int(memory.ucs_id): float(memory.bounds[memory.ucs_id, selected])}
    if arm == "form_b":
        return {int(memory.cs_id): cs, int(memory.ucs_id): float(memory.bounds[memory.ucs_id, 1 - selected])}
    if arm == "naive":
        return None
    if arm == "cs_only":
        return {int(memory.cs_id): cs}
    if arm == "low_ucs_only":
        return {int(memory.ucs_id): low}
    if arm == "high_ucs_only":
        return {int(memory.ucs_id): high}
    raise ValueError(f"unknown form arm: {arm}")


def _fingerprint(
    backend: JaxBackend,
    memory: Any,
    calibration: Mapping[str, Any],
    state: State,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    cpu = wall = 0.0
    valid = True
    for spec in _probe_specs(memory, calibration):
        phase = backend.run_phase(
            state.copy(),
            float(config["phase_duration"]),
            spec["stimuli"],
            memory.key.response_id,
            int(config["trajectory_samples"]),
            int(config["pulse_count"]),
        )
        mean_response = float(phase.mean_y[memory.key.response_id])
        margin = float(learned_margin(memory, mean_response))
        rows.append(
            {
                "probe": spec["name"],
                "stimuli": spec["stimuli"],
                "mean_response": mean_response,
                "learned_margin": margin,
                "valid": bool(phase.valid),
            }
        )
        cpu += float(phase.cpu_seconds)
        wall += float(phase.wall_seconds)
        valid = valid and bool(phase.valid) and np.isfinite(margin)
    raw = np.asarray([row["learned_margin"] for row in rows], dtype=float)
    return {
        "raw_fingerprint": raw,
        "fingerprint": transform_fingerprint(raw),
        "probes": rows,
        "valid": bool(valid),
        "cpu_seconds": cpu,
        "wall_seconds": wall,
    }


def _develop(
    backend: JaxBackend, memory: Any, start: State, config: Mapping[str, Any]
) -> dict[str, Any]:
    phase = backend.run_unstimulated(
        start,
        float(config["phase_duration"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
    )
    return {
        "adult": phase.state,
        "sampled_y": np.asarray(phase.sampled_y, dtype=float),
        "valid": bool(phase.valid),
        "cpu_seconds": float(phase.cpu_seconds),
        "wall_seconds": float(phase.wall_seconds),
    }


def _develop_and_fingerprint(
    backend: JaxBackend,
    memory: Any,
    calibration: Mapping[str, Any],
    start: State,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    developed = _develop(backend, memory, start, config)
    fingerprint = _fingerprint(backend, memory, calibration, developed["adult"], config)
    return {
        "adult_state": state_payload(developed["adult"]),
        "sampled_y": developed["sampled_y"],
        "raw_fingerprint": fingerprint["raw_fingerprint"],
        "fingerprint": fingerprint["fingerprint"],
        "probes": fingerprint["probes"],
        "valid": bool(developed["valid"] and fingerprint["valid"]),
        "cpu_seconds": float(developed["cpu_seconds"] + fingerprint["cpu_seconds"]),
        "wall_seconds": float(developed["wall_seconds"] + fingerprint["wall_seconds"]),
    }


def _develop_with_reader(
    backend: JaxBackend,
    memory: Any,
    calibration: Mapping[str, Any],
    baseline: State,
    decoded: State,
    reader_mode: str,
    config: Mapping[str, Any],
    with_fingerprint: bool,
) -> dict[str, Any]:
    if reader_mode == "initialization":
        start = decoded.copy()
        developed = _develop(backend, memory, start, config)
    elif reader_mode == "clamp_20pct":
        # run_phase clamps for the first half of its interval; a 1000-unit
        # interval therefore gives an exact 500/2500 = 20% clamp.
        start = State(baseline.y.copy(), decoded.w.copy(), baseline.c.copy(), baseline.t)
        clamp = backend.run_phase(
            start,
            1000.0,
            {index: float(value) for index, value in enumerate(decoded.y)},
            memory.key.response_id,
            int(config["trajectory_samples"]),
            1,
        )
        tail = backend.run_unstimulated(
            clamp.state,
            float(config["phase_duration"]) - 1000.0,
            memory.key.response_id,
            int(config["trajectory_samples"]),
        )
        developed = {
            "adult": tail.state,
            "sampled_y": np.concatenate((clamp.sampled_y, tail.sampled_y), axis=1),
            "valid": bool(clamp.valid and tail.valid),
            "cpu_seconds": float(clamp.cpu_seconds + tail.cpu_seconds),
            "wall_seconds": float(clamp.wall_seconds + tail.wall_seconds),
        }
    else:
        raise ValueError(f"unknown reader mode: {reader_mode}")
    result: dict[str, Any] = {
        "adult_state": state_payload(developed["adult"]),
        "sampled_y": developed["sampled_y"],
        "valid": bool(developed["valid"]),
        "cpu_seconds": float(developed["cpu_seconds"]),
        "wall_seconds": float(developed["wall_seconds"]),
        "raw_fingerprint": None,
        "fingerprint": None,
        "probes": None,
    }
    if with_fingerprint:
        fingerprint = _fingerprint(backend, memory, calibration, developed["adult"], config)
        result.update(
            {
                "raw_fingerprint": fingerprint["raw_fingerprint"],
                "fingerprint": fingerprint["fingerprint"],
                "probes": fingerprint["probes"],
                "valid": bool(result["valid"] and fingerprint["valid"]),
                "cpu_seconds": float(result["cpu_seconds"] + fingerprint["cpu_seconds"]),
                "wall_seconds": float(result["wall_seconds"] + fingerprint["wall_seconds"]),
            }
        )
    return result


def _perturb_start(
    start: State, memory: Any, config: Mapping[str, Any], task_id: str, seed_index: int
) -> tuple[State, int]:
    fraction = float(config["qualification"]["validation_initial_perturbation_fraction"])
    seed_value = _seed(config, "qualification-start", task_id, seed_index)
    rng = np.random.Generator(np.random.Philox(seed_value))
    width = np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8)
    y = np.clip(start.y + rng.normal(0.0, fraction, len(start.y)) * width, memory.bounds[:, 0], memory.bounds[:, 1])
    w_scale = np.maximum(np.abs(start.w), 1.0)
    w = start.w + rng.normal(0.0, fraction, len(start.w)) * w_scale
    return State(y, w, start.c.copy(), start.t), seed_value


def _run_form_history(
    backend: JaxBackend,
    memory: Any,
    calibration: Mapping[str, Any],
    start: State,
    arm: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    training = backend.run_phase(
        start,
        float(config["phase_duration"]),
        _form_stimuli(memory, calibration, arm),
        memory.key.response_id,
        int(config["trajectory_samples"]),
        int(config["pulse_count"]),
    )
    cpu = float(training.cpu_seconds)
    wall = float(training.wall_seconds)
    current = training.state
    valid = bool(training.valid)
    prior = 0.0
    checkpoints: dict[str, Any] = {}
    for checkpoint in (float(value) for value in config["acquisition_checkpoints"]):
        washout = backend.run_unstimulated(
            current,
            checkpoint - prior,
            memory.key.response_id,
            int(config["trajectory_samples"]),
            float(config["phase_duration"]),
        )
        current = washout.state
        fp = _fingerprint(backend, memory, calibration, current, config)
        cpu += float(washout.cpu_seconds + fp["cpu_seconds"])
        wall += float(washout.wall_seconds + fp["wall_seconds"])
        valid = valid and bool(washout.valid and fp["valid"])
        checkpoints[f"{checkpoint:g}"] = {
            "duration": checkpoint,
            "state": state_payload(current),
            "raw_fingerprint": fp["raw_fingerprint"],
            "fingerprint": fp["fingerprint"],
            "probes": fp["probes"],
            "valid": bool(washout.valid and fp["valid"]),
        }
        prior = checkpoint
    return {
        "training_state": state_payload(training.state),
        "checkpoints": checkpoints,
        "valid": bool(valid),
        "cpu_seconds": cpu,
        "wall_seconds": wall,
    }


def _qualification_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        output_path,
        model_id,
        task_ids,
        mode,
        seed_index,
        shard_key,
    ) = args
    config = load_ca_bridge_config(Path(config_path))
    atlas = Path(atlas_path)
    output = Path(output_path)
    shard = output / ".shards" / f"qualification-{mode}" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    calibrations = _calibration_map(atlas)
    histories = _history_map(atlas)
    backend = JaxBackend(Path(upstream_path), int(model_id), float(config["delta_t"]))
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for task_id in task_ids:
        released = load_released_task(Path(upstream_path), str(task_id))
        memory = load_memory(released.memory_path, released.key)
        base = _atlas_naive_start(histories, str(task_id))
        if mode == "screen":
            start = base
            philox_seed = None
        elif mode == "validation":
            if seed_index is None:
                raise ValueError("qualification validation requires a seed")
            start, philox_seed = _perturb_start(base, memory, config, str(task_id), int(seed_index))
        else:
            raise ValueError(f"unknown qualification mode: {mode}")
        for arm in FORM_ARMS:
            result = _run_form_history(backend, memory, calibrations[str(task_id)], start.copy(), arm, config)
            total_cpu += float(result["cpu_seconds"])
            records.append(
                {
                    "task_id": f"qualification-{mode}|{task_id}|{seed_index if seed_index is not None else 'deterministic'}|{arm}",
                    "memory_task_id": str(task_id),
                    "model_id": int(model_id),
                    "seed_index": seed_index,
                    "philox_seed": philox_seed,
                    "condition": arm,
                    "same_naive_start_hash": digest(state_payload(start)),
                    "rulebook_inherited": False,
                    **result,
                }
            )
    payload = {
        "protocol_digest": protocol_digest,
        "mode": mode,
        "model_id": int(model_id),
        "task_ids": list(task_ids),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def _form_reference(
    task_id: str, rows: Mapping[str, Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    checkpoints: dict[str, Any] = {}
    controls = ("naive", "cs_only", "low_ucs_only", "high_ucs_only")
    for checkpoint in (float(value) for value in config["acquisition_checkpoints"]):
        key = f"{checkpoint:g}"
        a = np.asarray(rows["form_a"]["checkpoints"][key]["fingerprint"], dtype=float)
        b = np.asarray(rows["form_b"]["checkpoints"][key]["fingerprint"], dtype=float)
        control_scores = {
            arm: form_score(rows[arm]["checkpoints"][key]["fingerprint"], a, b)
            for arm in controls
        }
        checkpoints[key] = {
            "form_a": a,
            "form_b": b,
            "midpoint": 0.5 * (a + b),
            "direction": a - b,
            "rms_separation": vector_rms(a - b),
            "control_scores": control_scores,
        }
    short = checkpoints["2500"]
    long = checkpoints["12500"]
    cosine = cosine_alignment(short["direction"], long["direction"])
    retention = float(long["rms_separation"] / max(short["rms_separation"], 1e-12))
    valid = bool(all(bool(row.get("valid", False)) for row in rows.values()))
    finite_control_scores = [
        abs(float(score))
        for checkpoint in checkpoints.values()
        for score in checkpoint["control_scores"].values()
        if score is not None and np.isfinite(float(score))
    ]
    control_max = max(finite_control_scores) if finite_control_scores else math.inf
    long_a_state = state_from_payload(
        rows["form_a"]["checkpoints"]["12500"].get("state")
    )
    state_dimension = (
        0 if long_a_state is None else int(len(long_a_state.y) + len(long_a_state.w))
    )
    q = config["qualification"]
    passed = bool(
        valid
        and short["rms_separation"] >= float(q["short_rms_min"])
        and long["rms_separation"] >= float(q["long_rms_min"])
        and cosine is not None
        and cosine >= float(q["direction_cosine_min"])
        and retention >= float(q["long_retention_fraction_min"])
        and control_max <= float(q["control_max_fraction"])
    )
    return {
        "memory_task_id": task_id,
        "model_id": int(task_id.split("-")[0]),
        "checkpoints": checkpoints,
        "direction_cosine": cosine,
        "long_retention_fraction": retention,
        "max_control_abs_score": control_max,
        "state_dimension": state_dimension,
        "valid": valid,
        "screen_pass": passed,
    }


def qualification_screen_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    grouped: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in records:
        grouped.setdefault(str(row["memory_task_id"]), {})[str(row["condition"])] = row
    references = [_form_reference(task_id, grouped[task_id], config) for task_id in config["fixed_cohort_task_ids"]]
    ranked = sorted(
        (row for row in references if row["screen_pass"]),
        key=lambda row: (
            -float(row["checkpoints"]["12500"]["rms_separation"]),
            int(row["model_id"]),
            str(row["memory_task_id"]),
        ),
    )
    nominations: list[str] = []
    used_models: set[int] = set()
    maximum = int(config["qualification"]["max_validation_nominations"])
    for row in ranked:
        if int(row["model_id"]) in used_models:
            continue
        nominations.append(str(row["memory_task_id"]))
        used_models.add(int(row["model_id"]))
        if len(nominations) == maximum:
            break
    return {
        "task_id": "qualification-screen-decision",
        "cohort_count": len(references),
        "pass_count": len(ranked),
        "references": references,
        "ranking": [row["memory_task_id"] for row in ranked],
        "validation_nominations": nominations,
        "pass": bool(nominations),
    }


def qualification_validation_decision(
    records: Sequence[Mapping[str, Any]],
    screen: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    reference_map = {str(row["memory_task_id"]): row for row in screen["references"]}
    by_key = {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["condition"])): row
        for row in records
    }
    q = config["qualification"]
    summaries: list[dict[str, Any]] = []
    for task_id in screen["validation_nominations"]:
        reference = reference_map[str(task_id)]
        seed_rows: list[dict[str, Any]] = []
        for seed_index in range(int(q["validation_seeds"])):
            arms = {arm: by_key.get((str(task_id), seed_index, arm)) for arm in FORM_ARMS}
            valid = bool(all(row is not None and row.get("valid") for row in arms.values()))
            metrics: dict[str, Any] = {"seed_index": seed_index, "valid": valid}
            if valid:
                checkpoint_metrics: dict[str, Any] = {}
                for checkpoint in ("2500", "12500"):
                    ref = reference["checkpoints"][checkpoint]
                    scores = {
                        arm: form_score(
                            arms[arm]["checkpoints"][checkpoint]["fingerprint"],
                            ref["form_a"],
                            ref["form_b"],
                        )
                        for arm in FORM_ARMS
                    }
                    checkpoint_metrics[checkpoint] = {
                        "scores": scores,
                        "crossover": 0.5 * (float(scores["form_a"]) - float(scores["form_b"])),
                        "correct": bool(float(scores["form_a"]) > 0 and float(scores["form_b"]) < 0),
                        "max_control_abs_score": max(abs(float(scores[arm])) for arm in FORM_ARMS[2:]),
                    }
                metrics["checkpoints"] = checkpoint_metrics
                metrics["crossover"] = min(
                    float(checkpoint_metrics["2500"]["crossover"]),
                    float(checkpoint_metrics["12500"]["crossover"]),
                )
                metrics["correct"] = bool(all(row["correct"] for row in checkpoint_metrics.values()))
                metrics["control_pass"] = bool(
                    max(row["max_control_abs_score"] for row in checkpoint_metrics.values())
                    <= float(q["control_max_fraction"])
                )
            seed_rows.append(metrics)
        valid_rows = [row for row in seed_rows if row["valid"]]
        crossover_values = [float(row["crossover"]) for row in valid_rows]
        median_crossover = float(np.median(crossover_values)) if crossover_values else 0.0
        lower_quartile = float(np.quantile(crossover_values, 0.25)) if crossover_values else 0.0
        consistent = sum(bool(row.get("correct") and row.get("control_pass")) for row in valid_rows)
        passed = bool(
            median_crossover >= float(q["validation_crossover_min"])
            and consistent >= int(q["minimum_consistent_seeds"])
        )
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(str(task_id).split("-")[0]),
                "median_crossover": median_crossover,
                "lower_quartile_crossover": lower_quartile,
                "valid_seed_count": len(valid_rows),
                "consistent_seed_count": consistent,
                "seed_metrics": seed_rows,
                "pass": passed,
            }
        )
    reference_map = {str(row["memory_task_id"]): row for row in screen["references"]}
    ranked = sorted(
        (row for row in summaries if row["pass"]),
        key=lambda row: (
            -float(row["lower_quartile_crossover"]),
            -float(reference_map[row["memory_task_id"]]["checkpoints"]["12500"]["rms_separation"]),
            int(reference_map[row["memory_task_id"]]["state_dimension"]),
            str(row["memory_task_id"]),
        ),
    )
    advanced: list[str] = []
    used_models: set[int] = set()
    for row in ranked:
        if int(row["model_id"]) in used_models:
            continue
        advanced.append(str(row["memory_task_id"]))
        used_models.add(int(row["model_id"]))
        if len(advanced) == int(q["max_advanced_distinct_models"]):
            break
    return {
        "task_id": "form-qualification-decision",
        "candidate_summaries": summaries,
        "ranking": [row["memory_task_id"] for row in ranked],
        "advanced_candidates": advanced,
        "pass_count": len(ranked),
        "pass": bool(advanced),
        "verdict": "robust-acquired-forms" if advanced else "no-robust-acquired-forms",
    }


def _stage1_inputs(parent: Path, task_id: str) -> dict[str, Any]:
    screen = {
        str(row["condition"]): row
        for row in read_jsonl(parent / "screen.jsonl")
        if str(row["memory_task_id"]) == task_id
    }
    if set(screen) != set(FORM_ARMS):
        raise ValueError(f"incomplete form screen for {task_id}")
    screen_decision = json.loads((parent / "screen-decision.json").read_text(encoding="utf-8"))
    reference = next(
        row for row in screen_decision["references"] if row["memory_task_id"] == task_id
    )
    states: dict[str, State] = {}
    for arm, row in screen.items():
        state = state_from_payload(row["checkpoints"]["12500"]["state"])
        if state is None:
            raise ValueError(f"invalid long-checkpoint state for {task_id}/{arm}")
        states[arm] = state
    return {"screen": screen, "reference": reference, "states": states}


def _transfer_control_vector(
    condition: str,
    history: str,
    form_a: np.ndarray,
    form_b: np.ndarray,
    ucs_a: np.ndarray,
    ucs_b: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, str]:
    source = form_a if history == "a" else form_b
    opposite = form_b if history == "a" else form_a
    midpoint = 0.5 * (form_a + form_b)
    if condition == "intact":
        return source.copy(), f"form-{history}"
    if condition == "opposite_history":
        return opposite.copy(), f"opposite-form-{'b' if history == 'a' else 'a'}"
    if condition == "midpoint_inversion":
        return invert_about_midpoint(source, midpoint), "midpoint-inversion"
    if condition == "zero":
        return np.zeros_like(source), "recipient-baseline"
    if condition == "normalized_shuffle":
        shuffled, method = normalized_shuffle(source - midpoint, rng)
        return midpoint + shuffled, f"normalized-shuffle:{method}"
    if condition == "norm_matched_random":
        return midpoint + norm_matched_random(source - midpoint, rng), "norm-matched-random"
    if condition == "ucs_only":
        return (ucs_a if history == "a" else ucs_b).copy(), f"ucs-only-{history}"
    raise ValueError(f"unknown transfer condition: {condition}")


def _transfer_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        parent_path,
        output_path,
        task_id,
        shard_key,
    ) = args
    config = load_ca_bridge_config(Path(config_path))
    atlas = Path(atlas_path)
    upstream = Path(upstream_path)
    parent = Path(parent_path)
    output = Path(output_path)
    shard = output / ".shards" / "native-transfer" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    inputs = _stage1_inputs(parent, str(task_id))
    calibrations = _calibration_map(atlas)
    calibration = calibrations[str(task_id)]
    released = load_released_task(upstream, str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
    states: dict[str, State] = inputs["states"]
    baseline = states["naive"]
    form_states = {"a": states["form_a"], "b": states["form_b"]}
    selected_bound = int(calibration["reconstructed_ucs_bound_index"])
    ucs_states = {
        "a": states["low_ucs_only" if selected_bound == 0 else "high_ucs_only"],
        "b": states["high_ucs_only" if selected_bound == 0 else "low_ucs_only"],
    }
    reference = inputs["reference"]["checkpoints"]["12500"]
    settings = config["native_transfer"]
    records: list[dict[str, Any]] = []
    reset_records: list[dict[str, Any]] = []
    channel_inputs: list[dict[str, Any]] = []
    total_cpu = 0.0
    modes = [mode for mode in ("y", "yw") if state_mode_available(form_states["a"], form_states["b"], mode)]
    for mode in modes:
        scale = state_scale(memory, baseline, form_states["a"], form_states["b"], mode)
        normalized_forms = {
            history: normalized_state_vector(state, baseline, scale, mode)
            for history, state in form_states.items()
        }
        normalized_ucs = {
            history: normalized_state_vector(state, baseline, scale, mode)
            for history, state in ucs_states.items()
        }
        for environment_name, environment in settings["environments"].items():
            for seed_index in range(int(settings["seeds"])):
                keep, noise, seed_value = common_damage(
                    config,
                    "native-transfer",
                    str(task_id),
                    seed_index,
                    0,
                    len(scale),
                    environment,
                )
                for history in ("a", "b"):
                    for condition in TRANSFER_CONDITIONS:
                        rng = np.random.Generator(
                            np.random.Philox(
                                _seed(config, "native-control", task_id, mode, seed_index, condition, history)
                            )
                        )
                        donor, ancestry = _transfer_control_vector(
                            condition,
                            history,
                            normalized_forms["a"],
                            normalized_forms["b"],
                            normalized_ucs["a"],
                            normalized_ucs["b"],
                            rng,
                        )
                        copied = copy_normalized(donor, keep, noise, float(environment["retention"]))
                        child = state_from_normalized(copied, baseline, scale, memory, mode)
                        result = _develop_and_fingerprint(
                            backend, memory, calibration, child, config
                        )
                        total_cpu += float(result["cpu_seconds"])
                        score = (
                            form_score(result["fingerprint"], reference["form_a"], reference["form_b"])
                            if result["valid"]
                            else None
                        )
                        records.append(
                            {
                                "task_id": f"native-transfer|{task_id}|{mode}|{environment_name}|{seed_index}|{history}|{condition}",
                                "memory_task_id": str(task_id),
                                "model_id": memory.key.model_id,
                                "state_mode": mode,
                                "environment": environment_name,
                                "seed_index": seed_index,
                                "philox_seed": seed_value,
                                "history": history,
                                "condition": condition,
                                "donor_ancestry": ancestry,
                                "inherited_state": copied,
                                "recipient_state": state_payload(child),
                                "rulebook_inherited": False,
                                "recipient_c_hash": digest(baseline.c),
                                "child_c_hash": digest(child.c),
                                "form_score": score,
                                **result,
                            }
                        )
        # Apply the one frozen historical combined-reset intervention to both
        # acquired forms, then test whether the surviving state is causal.
        action_index = int(calibration["selected_action_index"])
        control, _, control_value = memory.action(action_index)
        cs_value = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
        reset_stimuli = {int(memory.cs_id): cs_value, int(control): float(control_value)}
        post_reset: dict[str, State] = {}
        reset_lost: dict[str, bool] = {}
        reset_valid: dict[str, bool] = {}
        for history in ("a", "b"):
            phase = backend.run_phase(
                form_states[history].copy(),
                float(config["phase_duration"]),
                reset_stimuli,
                memory.key.response_id,
                int(config["trajectory_samples"]),
                int(config["pulse_count"]),
            )
            total_cpu += float(phase.cpu_seconds)
            mean_response = float(phase.mean_y[memory.key.response_id])
            margin = float(learned_margin(memory, mean_response))
            post_reset[history] = phase.state
            reset_lost[history] = bool(margin <= 0.0)
            reset_valid[history] = bool(phase.valid and np.isfinite(margin))
            direct = _fingerprint(backend, memory, calibration, phase.state, config)
            total_cpu += float(direct["cpu_seconds"])
            direct_score = (
                form_score(direct["fingerprint"], reference["form_a"], reference["form_b"])
                if direct["valid"]
                else None
            )
            reset_records.append(
                {
                    "task_id": f"reset-residual|{task_id}|{mode}|direct|{history}",
                    "memory_task_id": str(task_id),
                    "model_id": memory.key.model_id,
                    "state_mode": mode,
                    "record_kind": "direct-reset",
                    "history": history,
                    "condition": "combined_reset",
                    "reset_stimuli": reset_stimuli,
                    "learned_margin": margin,
                    "lost_learned_response": reset_lost[history],
                    "post_reset_state": state_payload(phase.state),
                    "raw_fingerprint": direct["raw_fingerprint"],
                    "fingerprint": direct["fingerprint"],
                    "form_score": direct_score,
                    "rulebook_inherited": False,
                    "valid": bool(reset_valid[history] and direct["valid"]),
                    "cpu_seconds": float(phase.cpu_seconds + direct["cpu_seconds"]),
                    "wall_seconds": float(phase.wall_seconds + direct["wall_seconds"]),
                }
            )
        pre_a = normalized_forms["a"]
        pre_b = normalized_forms["b"]
        post_a = normalized_state_vector(post_reset["a"], baseline, scale, mode)
        post_b = normalized_state_vector(post_reset["b"], baseline, scale, mode)
        pre_direction = pre_a - pre_b
        post_direction = post_a - post_b
        state_retention = float(
            np.linalg.norm(post_direction) / max(np.linalg.norm(pre_direction), 1e-12)
        )
        state_cosine = cosine_alignment(pre_direction, post_direction)
        residual_eligible = bool(all(reset_valid.values()) and all(reset_lost.values()))
        if residual_eligible:
            for seed_index in range(int(settings["seeds"])):
                for history in ("a", "b"):
                    post_vector = post_a if history == "a" else post_b
                    child = state_from_normalized(post_vector, baseline, scale, memory, mode)
                    result = _develop_and_fingerprint(backend, memory, calibration, child, config)
                    total_cpu += float(result["cpu_seconds"])
                    score = (
                        form_score(result["fingerprint"], reference["form_a"], reference["form_b"])
                        if result["valid"]
                        else None
                    )
                    reset_records.append(
                        {
                            "task_id": f"reset-residual|{task_id}|{mode}|transfer|{seed_index}|{history}",
                            "memory_task_id": str(task_id),
                            "model_id": memory.key.model_id,
                            "state_mode": mode,
                            "record_kind": "fresh-recipient-transfer",
                            "seed_index": seed_index,
                            "history": history,
                            "condition": "post_reset_intact",
                            "recipient_state": state_payload(child),
                            "form_score": score,
                            "rulebook_inherited": False,
                            **result,
                        }
                    )
        channel_inputs.append(
            {
                "memory_task_id": str(task_id),
                "model_id": memory.key.model_id,
                "state_mode": mode,
                "baseline_state": state_payload(baseline),
                "form_a_state": state_payload(form_states["a"]),
                "form_b_state": state_payload(form_states["b"]),
                "ucs_a_state": state_payload(ucs_states["a"]),
                "ucs_b_state": state_payload(ucs_states["b"]),
                "post_reset_a_state": state_payload(post_reset["a"]),
                "post_reset_b_state": state_payload(post_reset["b"]),
                "reference": reference,
                "state_scale": scale,
                "reset_valid": reset_valid,
                "reset_lost": reset_lost,
                "residual_eligible": residual_eligible,
                "residual_state_retention": state_retention,
                "residual_direction_cosine": state_cosine,
                "rulebook_inherited": False,
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "memory_task_id": str(task_id),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
        "reset_records": reset_records,
        "channel_inputs": channel_inputs,
    }
    write_json(shard, payload)
    return payload


def _paired_scores(
    rows: Mapping[tuple[Any, ...], Mapping[str, Any]],
    key_prefix: tuple[Any, ...],
    condition: str,
) -> tuple[float, float] | None:
    a = rows.get((*key_prefix, "a", condition))
    b = rows.get((*key_prefix, "b", condition))
    if (
        a is None
        or b is None
        or not a.get("valid")
        or not b.get("valid")
        or a.get("form_score") is None
        or b.get("form_score") is None
    ):
        return None
    return float(a["form_score"]), float(b["form_score"])


def native_transfer_decision(
    records: Sequence[Mapping[str, Any]],
    reset_records: Sequence[Mapping[str, Any]],
    channel_inputs: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["native_transfer"]
    rows = {
        (
            str(row["memory_task_id"]),
            str(row["state_mode"]),
            str(row["environment"]),
            int(row["seed_index"]),
            str(row["history"]),
            str(row["condition"]),
        ): row
        for row in records
    }
    reset_rows = {
        (
            str(row["memory_task_id"]),
            str(row["state_mode"]),
            int(row.get("seed_index", -1)),
            str(row["history"]),
        ): row
        for row in reset_records
        if row["record_kind"] == "fresh-recipient-transfer"
    }
    input_map = {
        (str(row["memory_task_id"]), str(row["state_mode"])): row
        for row in channel_inputs
    }
    candidate_summaries: list[dict[str, Any]] = []
    for task_id in candidates:
        mode_summaries: list[dict[str, Any]] = []
        modes = [mode for mode in ("y", "yw") if (str(task_id), mode) in input_map]
        for mode in modes:
            environments: dict[str, Any] = {}
            for environment in ("exact", "moderate"):
                seed_metrics: list[dict[str, Any]] = []
                for seed_index in range(int(settings["seeds"])):
                    prefix = (str(task_id), mode, environment, seed_index)
                    paired = {
                        condition: _paired_scores(rows, prefix, condition)
                        for condition in TRANSFER_CONDITIONS
                    }
                    valid = bool(all(value is not None for value in paired.values()))
                    metric: dict[str, Any] = {"seed_index": seed_index, "valid": valid}
                    if valid:
                        intact_a, intact_b = paired["intact"]
                        opposite_a, opposite_b = paired["opposite_history"]
                        inversion_a, inversion_b = paired["midpoint_inversion"]
                        crossover = 0.5 * (intact_a - intact_b)
                        benchmark = max(abs(crossover), 1e-12)
                        content_scores = [
                            abs(value)
                            for condition in ("zero", "normalized_shuffle", "norm_matched_random", "ucs_only")
                            for value in paired[condition]
                        ]
                        metric.update(
                            {
                                "crossover": crossover,
                                "correct": bool(intact_a > 0 and intact_b < 0),
                                "opposite_reversed": bool(opposite_a < 0 and opposite_b > 0),
                                "inversion_reversed": bool(inversion_a < 0 and inversion_b > 0),
                                "control_fraction": max(content_scores) / benchmark,
                            }
                        )
                    seed_metrics.append(metric)
                valid_rows = [row for row in seed_metrics if row["valid"]]
                values = [float(row["crossover"]) for row in valid_rows]
                median_crossover = float(np.median(values)) if values else 0.0
                lower_quartile = float(np.quantile(values, 0.25)) if values else 0.0
                consistent = sum(
                    bool(
                        row.get("correct")
                        and row.get("opposite_reversed")
                        and row.get("inversion_reversed")
                        and float(row.get("control_fraction", math.inf))
                        <= float(settings["control_max_fraction"])
                    )
                    for row in valid_rows
                )
                threshold = (
                    float(settings["exact_crossover_min"])
                    if environment == "exact"
                    else float(settings["moderate_crossover_reporting_min"])
                )
                passed = bool(
                    median_crossover >= threshold
                    and consistent >= int(settings["minimum_consistent_seeds"])
                    and (
                        environment != "exact"
                        or lower_quartile >= float(settings["exact_lower_quartile_min"])
                    )
                )
                environments[environment] = {
                    "median_crossover": median_crossover,
                    "lower_quartile_crossover": lower_quartile,
                    "valid_seed_count": len(valid_rows),
                    "consistent_seed_count": consistent,
                    "seed_metrics": seed_metrics,
                    "pass": passed,
                }
            channel = input_map[(str(task_id), mode)]
            residual_seed_metrics: list[dict[str, Any]] = []
            if channel["residual_eligible"]:
                for seed_index in range(int(settings["seeds"])):
                    a = reset_rows.get((str(task_id), mode, seed_index, "a"))
                    b = reset_rows.get((str(task_id), mode, seed_index, "b"))
                    valid = bool(
                        a is not None
                        and b is not None
                        and a.get("valid")
                        and b.get("valid")
                        and a.get("form_score") is not None
                        and b.get("form_score") is not None
                    )
                    residual_seed_metrics.append(
                        {
                            "seed_index": seed_index,
                            "valid": valid,
                            "crossover": None
                            if not valid
                            else 0.5 * (float(a["form_score"]) - float(b["form_score"])),
                            "correct": bool(
                                valid and float(a["form_score"]) > 0 and float(b["form_score"]) < 0
                            ),
                        }
                    )
            valid_residual = [row for row in residual_seed_metrics if row["valid"]]
            residual_crossover = (
                float(np.median([float(row["crossover"]) for row in valid_residual]))
                if valid_residual
                else 0.0
            )
            residual_consistent = sum(bool(row["correct"]) for row in valid_residual)
            decodable = bool(
                channel["residual_eligible"]
                and float(channel["residual_state_retention"])
                >= float(settings["residual_state_retention_min"])
                and channel["residual_direction_cosine"] is not None
                and float(channel["residual_direction_cosine"])
                >= float(settings["residual_direction_cosine_min"])
            )
            causal = bool(
                channel["residual_eligible"]
                and residual_crossover >= float(settings["residual_causal_crossover_min"])
                and residual_consistent >= int(settings["minimum_consistent_seeds"])
            )
            if not all(channel["reset_valid"].values()) or not all(channel["reset_lost"].values()):
                residual_label = "rehoming/asymmetric-reset"
            elif causal:
                residual_label = "causal-latent-memory"
            elif decodable:
                residual_label = "decodable-noncausal-trace"
            else:
                residual_label = "operational-erasure"
            mode_summaries.append(
                {
                    "state_mode": mode,
                    "environments": environments,
                    "native_pass": bool(environments["exact"]["pass"]),
                    "residual_label": residual_label,
                    "residual_state_retention": channel["residual_state_retention"],
                    "residual_direction_cosine": channel["residual_direction_cosine"],
                    "residual_crossover": residual_crossover,
                    "residual_consistent_seed_count": residual_consistent,
                    "residual_seed_metrics": residual_seed_metrics,
                    "post_reset_causal_pass": causal,
                }
            )
        passing_modes = [row for row in mode_summaries if row["native_pass"]]
        selected_native = next(
            (row for row in passing_modes if row["state_mode"] == "y"),
            passing_modes[0] if passing_modes else None,
        )
        causal_modes = [row for row in mode_summaries if row["post_reset_causal_pass"]]
        selected_residual = next(
            (row for row in causal_modes if row["state_mode"] == "y"),
            causal_modes[0] if causal_modes else None,
        )
        candidate_summaries.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(str(task_id).split("-")[0]),
                "modes": mode_summaries,
                "selected_native_mode": None if selected_native is None else selected_native["state_mode"],
                "selected_residual_mode": None if selected_residual is None else selected_residual["state_mode"],
                "native_pass": selected_native is not None,
                "post_reset_causal_pass": selected_residual is not None,
            }
        )

    def advance(key: str, mode_key: str, maximum: int) -> list[dict[str, Any]]:
        ranked = sorted(
            (row for row in candidate_summaries if row[key]),
            key=lambda row: (
                0 if row[mode_key] == "y" else 1,
                -max(
                    float(mode["environments"]["exact"]["lower_quartile_crossover"])
                    for mode in row["modes"]
                    if mode["state_mode"] == row[mode_key]
                )
                if key == "native_pass"
                else -max(
                    float(mode["residual_crossover"])
                    for mode in row["modes"]
                    if mode["state_mode"] == row[mode_key]
                ),
                str(row["memory_task_id"]),
            ),
        )
        result: list[dict[str, Any]] = []
        used: set[int] = set()
        for row in ranked:
            if int(row["model_id"]) in used:
                continue
            result.append(
                {
                    "memory_task_id": row["memory_task_id"],
                    "model_id": row["model_id"],
                    "state_mode": row[mode_key],
                }
            )
            used.add(int(row["model_id"]))
            if len(result) == maximum:
                break
        return result

    compression = advance(
        "native_pass", "selected_native_mode", int(settings["max_compression_candidates"])
    )
    lineage = advance(
        "post_reset_causal_pass",
        "selected_residual_mode",
        int(settings["max_native_lineage_candidates"]),
    )
    return {
        "task_id": "native-transfer-decision",
        "candidate_summaries": candidate_summaries,
        "compression_candidates": compression,
        "native_lineage_candidates": lineage,
        "native_pass_count": sum(bool(row["native_pass"]) for row in candidate_summaries),
        "post_reset_causal_count": sum(bool(row["post_reset_causal_pass"]) for row in candidate_summaries),
        "pass": bool(compression or lineage),
        "verdict": (
            "native-and-residual-leads"
            if compression and lineage
            else "native-transfer-leads"
            if compression
            else "post-reset-causal-leads"
            if lineage
            else "no-native-transfer-or-causal-residual"
        ),
    }


def _codec_hash(codec: Mapping[str, Any]) -> str:
    return digest({key: value for key, value in codec.items() if key != "codebook_hash"})


def encode_codec(codec: Mapping[str, Any], normalized_state: Sequence[float]) -> np.ndarray:
    values = np.asarray(normalized_state, dtype=float)
    dimension = int(codec["state_dimension"])
    if values.shape != (dimension,):
        raise ValueError("codec input dimension differs")
    family = str(codec["family"])
    if family == "sparse":
        return values[np.asarray(codec["selected_indices"], dtype=int)]
    center = np.asarray(codec["center"], dtype=float)
    basis = np.asarray(codec["basis"], dtype=float)
    return basis @ (values - center)


def decode_codec(codec: Mapping[str, Any], payload: Sequence[float]) -> np.ndarray:
    values = np.asarray(payload, dtype=float)
    if values.shape != (int(codec["payload_float_count"]),):
        raise ValueError("codec payload length differs")
    family = str(codec["family"])
    if family == "sparse":
        decoded = np.zeros(int(codec["state_dimension"]), dtype=float)
        decoded[np.asarray(codec["selected_indices"], dtype=int)] = values
        return decoded
    center = np.asarray(codec["center"], dtype=float)
    basis = np.asarray(codec["basis"], dtype=float)
    return center + basis.T @ values


def build_codebooks(
    discovery_matrix: np.ndarray,
    form_a_mean: np.ndarray,
    form_b_mean: np.ndarray,
    y_count: int,
    sparse_sizes: Sequence[int],
    pca_ranks: Sequence[int],
    observability_ranks: Sequence[int],
    observability_basis: np.ndarray,
) -> list[dict[str, Any]]:
    matrix = np.asarray(discovery_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != len(form_a_mean):
        raise ValueError("invalid discovery matrix")
    dimension = matrix.shape[1]
    common_interface_floats = 2 * dimension
    direction = np.asarray(form_a_mean) - np.asarray(form_b_mean)
    ranked_nodes = sorted(range(int(y_count)), key=lambda index: (-abs(float(direction[index])), index))
    codecs: list[dict[str, Any]] = []
    for size in sparse_sizes:
        size = int(size)
        if size < 1 or size > int(y_count):
            continue
        selected = ranked_nodes[:size]
        codec = {
            "codec_id": f"sparse-k{size}",
            "family": "sparse",
            "rank": size,
            "state_dimension": dimension,
            "selected_indices": selected,
            "center": np.zeros(dimension),
            "basis": [],
            "payload_float_count": size,
            "codebook_float_count": common_interface_floats,
        }
        codec["codebook_hash"] = _codec_hash(codec)
        codecs.append(codec)
    center = np.mean(matrix, axis=0)
    centered = matrix - center
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    for rank_value in pca_ranks:
        rank = min(int(rank_value), vt.shape[0], dimension)
        if rank < 1:
            continue
        codec = {
            "codec_id": f"pca-r{rank_value}",
            "family": "pca",
            "rank": rank,
            "state_dimension": dimension,
            "selected_indices": [],
            "center": center,
            "basis": vt[:rank],
            "payload_float_count": rank,
            "codebook_float_count": common_interface_floats + dimension + rank * dimension,
        }
        codec["codebook_hash"] = _codec_hash(codec)
        codecs.append(codec)
    obs = np.asarray(observability_basis, dtype=float)
    for rank_value in observability_ranks:
        rank = min(int(rank_value), obs.shape[0], dimension)
        if rank < 1:
            continue
        codec = {
            "codec_id": f"observability-r{rank_value}",
            "family": "observability",
            "rank": rank,
            "state_dimension": dimension,
            "selected_indices": [],
            "center": np.zeros(dimension),
            "basis": obs[:rank],
            "payload_float_count": rank,
            "codebook_float_count": common_interface_floats + rank * dimension,
        }
        codec["codebook_hash"] = _codec_hash(codec)
        codecs.append(codec)
    norm = float(np.linalg.norm(direction))
    if norm > 1e-12:
        codec = {
            "codec_id": "signed-direction-r1",
            "family": "direction",
            "rank": 1,
            "state_dimension": dimension,
            "selected_indices": [],
            "center": 0.5 * (np.asarray(form_a_mean) + np.asarray(form_b_mean)),
            "basis": (direction / norm)[None, :],
            "payload_float_count": 1,
            "codebook_float_count": common_interface_floats + 2 * dimension,
        }
        codec["codebook_hash"] = _codec_hash(codec)
        codecs.append(codec)
    ids = [str(codec["codec_id"]) for codec in codecs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate codec IDs")
    return codecs


def _stage2_channel(parent: Path, task_id: str, mode: str) -> dict[str, Any]:
    payload = json.loads((parent / "channel-inputs.json").read_text(encoding="utf-8"))
    matches = [
        row
        for row in payload["channels"]
        if row["memory_task_id"] == task_id and row["state_mode"] == mode
    ]
    if len(matches) != 1:
        raise ValueError(f"missing unique stage-2 channel {task_id}/{mode}")
    return matches[0]


def _compression_payload_control(
    condition: str,
    history: str,
    codec: Mapping[str, Any],
    form_vectors: Mapping[str, np.ndarray],
    ucs_vectors: Mapping[str, np.ndarray],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, str]:
    source = encode_codec(codec, form_vectors[history])
    other = encode_codec(codec, form_vectors["b" if history == "a" else "a"])
    midpoint = 0.5 * (source + other)
    zero = encode_codec(codec, np.zeros(int(codec["state_dimension"])))
    if condition == "intact":
        payload = source
        ancestry = f"form-{history}"
    elif condition == "inversion":
        payload = invert_about_midpoint(source, midpoint)
        ancestry = "payload-midpoint-inversion"
    elif condition == "zero":
        payload = zero
        ancestry = "zero-recipient-code"
    elif condition == "normalized_shuffle":
        shuffled, method = normalized_shuffle(source - midpoint, rng)
        payload = midpoint + shuffled
        ancestry = f"payload-shuffle:{method}"
    elif condition == "norm_matched_random":
        payload = midpoint + norm_matched_random(source - midpoint, rng)
        ancestry = "payload-norm-matched-random"
    elif condition == "ucs_only":
        payload = encode_codec(codec, ucs_vectors[history])
        ancestry = f"ucs-only-{history}"
    else:
        raise ValueError(f"unknown compression condition: {condition}")
    return payload, zero, ancestry


def _compression_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        parent_path,
        output_path,
        candidate,
        shard_key,
    ) = args
    config = load_ca_bridge_config(Path(config_path))
    atlas = Path(atlas_path)
    upstream = Path(upstream_path)
    parent = Path(parent_path)
    output = Path(output_path)
    task_id = str(candidate["memory_task_id"])
    mode = str(candidate["state_mode"])
    shard = output / ".shards" / "compression" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    settings = config["compression"]
    channel = _stage2_channel(parent, task_id, mode)
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    calibration = _calibration_map(atlas)[task_id]
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))

    def load_state(name: str) -> State:
        state = state_from_payload(channel[name])
        if state is None:
            raise ValueError(f"invalid channel state {name}")
        return state

    baseline = load_state("baseline_state")
    forms = {"a": load_state("form_a_state"), "b": load_state("form_b_state")}
    ucs = {"a": load_state("ucs_a_state"), "b": load_state("ucs_b_state")}
    scale = np.asarray(channel["state_scale"], dtype=float)
    form_vectors = {
        history: normalized_state_vector(state, baseline, scale, mode)
        for history, state in forms.items()
    }
    ucs_vectors = {
        history: normalized_state_vector(state, baseline, scale, mode)
        for history, state in ucs.items()
    }
    reference = channel["reference"]
    discovery_by_history: dict[str, list[np.ndarray]] = {"a": [], "b": []}
    trajectory_rows: list[np.ndarray] = []
    total_cpu = 0.0
    discovery_states: dict[tuple[int, str], State] = {}
    for seed_index in range(int(settings["discovery_seeds"])):
        rng = np.random.Generator(
            np.random.Philox(_seed(config, "compression-discovery-state", task_id, seed_index))
        )
        common = rng.normal(
            0.0, float(settings["initial_perturbation_fraction"]), len(scale)
        )
        for history in ("a", "b"):
            vector = form_vectors[history] + common
            state = state_from_normalized(vector, baseline, scale, memory, mode)
            discovery_states[(seed_index, history)] = state
            actual = normalized_state_vector(state, baseline, scale, mode)
            discovery_by_history[history].append(actual)
            developed = _develop(backend, memory, state, config)
            total_cpu += float(developed["cpu_seconds"])
            adult = developed["adult"]
            trajectory_rows.append(normalized_state_vector(adult, baseline, scale, mode))
            sampled = np.asarray(developed["sampled_y"], dtype=float)
            for column in range(sampled.shape[1]):
                snapshot = State(sampled[:, column], adult.w.copy(), baseline.c.copy(), baseline.t)
                trajectory_rows.append(normalized_state_vector(snapshot, baseline, scale, mode))
    discovery_matrix = np.vstack(
        [*discovery_by_history["a"], *discovery_by_history["b"], *trajectory_rows]
    )
    form_means = {
        history: np.mean(np.vstack(rows), axis=0)
        for history, rows in discovery_by_history.items()
    }
    midpoint = 0.5 * (form_means["a"] + form_means["b"])
    midpoint_state = state_from_normalized(midpoint, baseline, scale, memory, mode)
    baseline_assay = _develop_and_fingerprint(backend, memory, calibration, midpoint_state, config)
    total_cpu += float(baseline_assay["cpu_seconds"])
    impulse = float(settings["observability_impulse_fraction"])
    sensitivity_columns: list[np.ndarray] = []
    for index in range(len(scale)):
        perturbed = midpoint.copy()
        perturbed[index] += impulse
        state = state_from_normalized(perturbed, baseline, scale, memory, mode)
        assay = _develop_and_fingerprint(backend, memory, calibration, state, config)
        total_cpu += float(assay["cpu_seconds"])
        if assay["valid"] and baseline_assay["valid"]:
            sensitivity_columns.append(
                (np.asarray(assay["fingerprint"]) - np.asarray(baseline_assay["fingerprint"]))
                / impulse
            )
        else:
            sensitivity_columns.append(np.zeros(len(config["fingerprint_probes"])))
    sensitivity = np.column_stack(sensitivity_columns)
    _, _, observability_vt = np.linalg.svd(sensitivity, full_matrices=False)
    codebooks = build_codebooks(
        discovery_matrix,
        form_means["a"],
        form_means["b"],
        len(baseline.y),
        settings["sparse_sizes"],
        settings["pca_ranks"],
        settings["observability_ranks"],
        observability_vt,
    )
    discovery_records: list[dict[str, Any]] = []
    # The four discovery seeds fit every frozen codebook.  Setting selection is
    # then evaluated once at the fitted A/B centroids; all stochastic
    # replication is reserved for the eight untouched validation seeds.
    for codec in codebooks:
        for reader_mode in settings["reader_modes"]:
            for coupling in settings["reader_couplings"]:
                for history in ("a", "b"):
                    source = form_means[history]
                    payload_values = encode_codec(codec, source)
                    decoded_values = float(coupling) * decode_codec(codec, payload_values)
                    decoded = state_from_normalized(decoded_values, baseline, scale, memory, mode)
                    assay = _develop_with_reader(
                        backend,
                        memory,
                        calibration,
                        baseline,
                        decoded,
                        str(reader_mode),
                        config,
                        True,
                    )
                    total_cpu += float(assay["cpu_seconds"])
                    score = (
                        form_score(assay["fingerprint"], reference["form_a"], reference["form_b"])
                        if assay["valid"]
                        else None
                    )
                    discovery_records.append(
                        {
                            "task_id": f"compression-discovery|{task_id}|{codec['codec_id']}|{reader_mode}|{coupling:g}|centroid|{history}",
                            "memory_task_id": task_id,
                            "model_id": memory.key.model_id,
                            "state_mode": mode,
                            "codec_id": codec["codec_id"],
                            "codebook_hash": codec["codebook_hash"],
                            "payload_float_count": codec["payload_float_count"],
                            "codebook_float_count": codec["codebook_float_count"],
                            "reader_mode": reader_mode,
                            "coupling": float(coupling),
                            "seed_partition": "discovery-fitted-centroid",
                            "seed_index": -1,
                            "history": history,
                            "condition": "intact",
                            "payload": payload_values,
                            "form_score": score,
                            "rulebook_inherited": False,
                            **assay,
                        }
                    )
    selections = select_compression_discovery(discovery_records, codebooks, config)
    selected_ids = {str(row["codec_id"]): row for row in selections["family_selections"]}
    codebook_map = {str(codec["codec_id"]): codec for codec in codebooks}
    validation_records: list[dict[str, Any]] = []
    for selection in selected_ids.values():
        codec = codebook_map[str(selection["codec_id"])]
        reader_mode = str(selection["reader_mode"])
        coupling = float(selection["coupling"])
        for environment_name, environment in settings["environments"].items():
            for seed_index in range(int(settings["validation_seeds"])):
                keep, noise, seed_value = common_damage(
                    config,
                    "compression-validation-payload",
                    task_id,
                    seed_index + 100,
                    0,
                    int(codec["payload_float_count"]),
                    environment,
                )
                for history in ("a", "b"):
                    for condition in COMPRESSION_CONDITIONS:
                        rng = np.random.Generator(
                            np.random.Philox(
                                _seed(
                                    config,
                                    "compression-validation-control",
                                    task_id,
                                    codec["codec_id"],
                                    seed_index + 100,
                                    history,
                                    condition,
                                )
                            )
                        )
                        payload_values, zero_payload, ancestry = _compression_payload_control(
                            condition,
                            history,
                            codec,
                            form_vectors,
                            ucs_vectors,
                            rng,
                        )
                        copied_delta = copy_normalized(
                            payload_values - zero_payload,
                            keep,
                            noise,
                            float(environment["retention"]),
                        )
                        copied = zero_payload + copied_delta
                        decoded_values = coupling * decode_codec(codec, copied)
                        decoded = state_from_normalized(decoded_values, baseline, scale, memory, mode)
                        assay = _develop_with_reader(
                            backend,
                            memory,
                            calibration,
                            baseline,
                            decoded,
                            reader_mode,
                            config,
                            True,
                        )
                        total_cpu += float(assay["cpu_seconds"])
                        score = (
                            form_score(assay["fingerprint"], reference["form_a"], reference["form_b"])
                            if assay["valid"]
                            else None
                        )
                        validation_records.append(
                            {
                                "task_id": f"compression-validation|{task_id}|{codec['codec_id']}|{reader_mode}|{coupling:g}|{environment_name}|{seed_index}|{history}|{condition}",
                                "memory_task_id": task_id,
                                "model_id": memory.key.model_id,
                                "state_mode": mode,
                                "codec_id": codec["codec_id"],
                                "codebook_hash": codec["codebook_hash"],
                                "payload_float_count": codec["payload_float_count"],
                                "codebook_float_count": codec["codebook_float_count"],
                                "reader_mode": reader_mode,
                                "coupling": coupling,
                                "environment": environment_name,
                                "seed_partition": "validation",
                                "seed_index": seed_index,
                                "philox_seed": seed_value,
                                "history": history,
                                "condition": condition,
                                "donor_ancestry": ancestry,
                                "payload": copied,
                                "form_score": score,
                                "rulebook_inherited": False,
                                **assay,
                            }
                        )
    payload = {
        "protocol_digest": protocol_digest,
        "memory_task_id": task_id,
        "state_mode": mode,
        "aggregate_cpu_seconds": total_cpu,
        "discovery_records": discovery_records,
        "validation_records": validation_records,
        "codebooks": codebooks,
        "discovery_selection": selections,
        "channel_input": channel,
    }
    write_json(shard, payload)
    return payload


def select_compression_discovery(
    records: Sequence[Mapping[str, Any]],
    codebooks: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    by_setting: dict[tuple[str, str, float], list[Mapping[str, Any]]] = {}
    for row in records:
        key = (str(row["codec_id"]), str(row["reader_mode"]), float(row["coupling"]))
        by_setting.setdefault(key, []).append(row)
    codec_map = {str(row["codec_id"]): row for row in codebooks}
    summaries: list[dict[str, Any]] = []
    for (codec_id, reader_mode, coupling), setting_rows in by_setting.items():
        keyed = {str(row["history"]): row for row in setting_rows}
        a = keyed.get("a")
        b = keyed.get("b")
        valid = bool(
            a is not None
            and b is not None
            and a.get("valid")
            and b.get("valid")
            and a.get("form_score") is not None
            and b.get("form_score") is not None
        )
        median_crossover = (
            0.5 * (float(a["form_score"]) - float(b["form_score"])) if valid else 0.0
        )
        correct = bool(valid and float(a["form_score"]) > 0 and float(b["form_score"]) < 0)
        seed_metrics = [
            {
                "evaluation": "four-seed-fitted-centroid",
                "valid": valid,
                "crossover": median_crossover if valid else None,
                "correct": correct,
            }
        ]
        codec = codec_map[codec_id]
        summaries.append(
            {
                "codec_id": codec_id,
                "family": codec["family"],
                "reader_mode": reader_mode,
                "coupling": coupling,
                "payload_float_count": codec["payload_float_count"],
                "codebook_float_count": codec["codebook_float_count"],
                "median_crossover": median_crossover,
                "consistent_seed_count": int(correct),
                "seed_metrics": seed_metrics,
                "pass": bool(
                    median_crossover >= float(config["compression"]["discovery_crossover_min"])
                    and correct
                ),
            }
        )
    selections: list[dict[str, Any]] = []
    for family in ("sparse", "pca", "observability", "direction"):
        ranked = sorted(
            (row for row in summaries if row["family"] == family and row["pass"]),
            key=lambda row: (
                int(row["payload_float_count"]),
                0 if row["reader_mode"] == "initialization" else 1,
                float(row["coupling"]),
                int(row["codebook_float_count"]),
                -float(row["median_crossover"]),
                str(row["codec_id"]),
            ),
        )
        if ranked:
            selections.append(ranked[0])
    return {
        "task_id": "compression-discovery-selection",
        "setting_summaries": summaries,
        "family_selections": selections,
        "pass": bool(selections),
    }


def compression_validation_decision(
    records: Sequence[Mapping[str, Any]],
    codebooks: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["compression"]
    codebook_map = {
        (str(row["memory_task_id"]), str(row["codec_id"])): row for row in codebooks
    }
    setting_keys = sorted(
        {
            (
                str(row["memory_task_id"]),
                str(row["state_mode"]),
                str(row["codec_id"]),
                str(row["reader_mode"]),
                float(row["coupling"]),
            )
            for row in records
        }
    )
    rows = {
        (
            str(row["memory_task_id"]),
            str(row["state_mode"]),
            str(row["codec_id"]),
            str(row["reader_mode"]),
            float(row["coupling"]),
            str(row["environment"]),
            int(row["seed_index"]),
            str(row["history"]),
            str(row["condition"]),
        ): row
        for row in records
    }
    summaries: list[dict[str, Any]] = []
    for setting_key in setting_keys:
        task_id, mode, codec_id, reader_mode, coupling = setting_key
        environment_summaries: dict[str, Any] = {}
        for environment in ("ordinary", "moderate"):
            seed_metrics: list[dict[str, Any]] = []
            for seed_index in range(int(settings["validation_seeds"])):
                pairs: dict[str, tuple[float, float] | None] = {}
                for condition in COMPRESSION_CONDITIONS:
                    a = rows.get((*setting_key, environment, seed_index, "a", condition))
                    b = rows.get((*setting_key, environment, seed_index, "b", condition))
                    pairs[condition] = (
                        None
                        if a is None
                        or b is None
                        or not a.get("valid")
                        or not b.get("valid")
                        or a.get("form_score") is None
                        or b.get("form_score") is None
                        else (float(a["form_score"]), float(b["form_score"]))
                    )
                valid = bool(all(value is not None for value in pairs.values()))
                metric: dict[str, Any] = {"seed_index": seed_index, "valid": valid}
                if valid:
                    intact_a, intact_b = pairs["intact"]
                    inversion_a, inversion_b = pairs["inversion"]
                    crossover = 0.5 * (intact_a - intact_b)
                    benchmark = max(abs(crossover), 1e-12)
                    controls = [
                        abs(value)
                        for condition in ("zero", "normalized_shuffle", "norm_matched_random", "ucs_only")
                        for value in pairs[condition]
                    ]
                    metric.update(
                        {
                            "crossover": crossover,
                            "correct": bool(intact_a > 0 and intact_b < 0),
                            "inversion_reversed": bool(inversion_a < 0 and inversion_b > 0),
                            "control_fraction": max(controls) / benchmark,
                        }
                    )
                seed_metrics.append(metric)
            valid_rows = [row for row in seed_metrics if row["valid"]]
            values = [float(row["crossover"]) for row in valid_rows]
            median_crossover = float(np.median(values)) if values else 0.0
            consistent = sum(
                bool(
                    row.get("correct")
                    and row.get("inversion_reversed")
                    and float(row.get("control_fraction", math.inf))
                    <= float(settings["control_max_fraction"])
                )
                for row in valid_rows
            )
            threshold = float(
                settings[
                    "ordinary_crossover_min"
                    if environment == "ordinary"
                    else "moderate_crossover_min"
                ]
            )
            environment_summaries[environment] = {
                "median_crossover": median_crossover,
                "valid_seed_count": len(valid_rows),
                "consistent_seed_count": consistent,
                "seed_metrics": seed_metrics,
                "pass": bool(
                    median_crossover >= threshold
                    and consistent >= int(settings["minimum_consistent_seeds"])
                ),
            }
        codec = codebook_map[(task_id, codec_id)]
        summaries.append(
            {
                "memory_task_id": task_id,
                "model_id": int(task_id.split("-")[0]),
                "state_mode": mode,
                "codec_id": codec_id,
                "codebook_hash": codec["codebook_hash"],
                "payload_float_count": codec["payload_float_count"],
                "codebook_float_count": codec["codebook_float_count"],
                "reader_mode": reader_mode,
                "coupling": coupling,
                "environments": environment_summaries,
                "pass": bool(all(row["pass"] for row in environment_summaries.values())),
            }
        )
    ranked = sorted(
        (row for row in summaries if row["pass"]),
        key=lambda row: (
            int(row["payload_float_count"]),
            0 if row["reader_mode"] == "initialization" else 1,
            float(row["coupling"]),
            int(row["codebook_float_count"]),
            str(row["memory_task_id"]),
            str(row["codec_id"]),
        ),
    )
    advanced: list[dict[str, Any]] = []
    used_models: set[int] = set()
    for row in ranked:
        if int(row["model_id"]) in used_models:
            continue
        advanced.append(row)
        used_models.add(int(row["model_id"]))
        if len(advanced) == int(settings["max_advanced_distinct_models"]):
            break
    return {
        "task_id": "compression-validation-decision",
        "candidate_summaries": summaries,
        "ranking": [f"{row['memory_task_id']}|{row['codec_id']}" for row in ranked],
        "advanced_channels": advanced,
        "pass_count": len(ranked),
        "pass": bool(advanced),
        "verdict": "compact-codec-leads" if advanced else "no-validated-compact-codec",
    }


def _native_lineage_founder(
    arm: str,
    history: str,
    form_vectors: Mapping[str, np.ndarray],
    rng: np.random.Generator,
) -> tuple[np.ndarray, str]:
    source = form_vectors[history]
    opposite_history = "b" if history == "a" else "a"
    opposite = form_vectors[opposite_history]
    midpoint = 0.5 * (source + opposite)
    if arm in {"active_rewrite", "passive", "erase_g2", "rescue_g3"}:
        return source.copy(), f"post-reset-form-{history}"
    if arm == "wrong_history":
        return opposite.copy(), f"wrong-history-{opposite_history}"
    if arm == "inversion":
        return invert_about_midpoint(source, midpoint), "midpoint-inversion"
    if arm == "normalized_shuffle":
        shuffled, method = normalized_shuffle(source - midpoint, rng)
        return midpoint + shuffled, f"normalized-shuffle:{method}"
    if arm == "norm_matched_random":
        return midpoint + norm_matched_random(source - midpoint, rng), "norm-matched-random"
    if arm == "control":
        return np.zeros_like(source), "recipient-baseline"
    raise ValueError(f"unknown native-lineage arm: {arm}")


def _native_lineage_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        parent_path,
        output_path,
        candidate,
        seed_index,
        shard_key,
    ) = args
    config = load_ca_bridge_config(Path(config_path))
    atlas = Path(atlas_path)
    upstream = Path(upstream_path)
    parent = Path(parent_path)
    output = Path(output_path)
    task_id = str(candidate["memory_task_id"])
    mode = str(candidate["state_mode"])
    shard = output / ".shards" / "native-lineage" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    channel = _stage2_channel(parent, task_id, mode)
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    calibration = _calibration_map(atlas)[task_id]
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))

    def load_state(name: str) -> State:
        state = state_from_payload(channel[name])
        if state is None:
            raise ValueError(f"invalid native-lineage state {name}")
        return state

    baseline = load_state("baseline_state")
    founders = {
        "a": load_state("post_reset_a_state"),
        "b": load_state("post_reset_b_state"),
    }
    scale = np.asarray(channel["state_scale"], dtype=float)
    form_vectors = {
        history: normalized_state_vector(state, baseline, scale, mode)
        for history, state in founders.items()
    }
    reference = channel["reference"]
    settings = config["native_lineage"]
    environment = config["native_transfer"]["environments"]["moderate"]
    checkpoints = {int(value) for value in settings["checkpoints"]}
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for history in ("a", "b"):
        for arm in NATIVE_LINEAGE_ARMS:
            rng = np.random.Generator(
                np.random.Philox(_seed(config, "native-lineage-founder", task_id, seed_index, history, arm))
            )
            founder_vector, founder_source = _native_lineage_founder(
                arm, history, form_vectors, rng
            )
            founder = state_from_normalized(founder_vector, baseline, scale, memory, mode)
            donor = founder.copy()
            donor_source = founder_source
            parent_record_id: str | None = None
            for generation in range(1, int(settings["generations"]) + 1):
                keep, noise, seed_value = common_damage(
                    config,
                    "native-lineage-copy",
                    task_id,
                    int(seed_index),
                    generation,
                    len(scale),
                    environment,
                )
                effective = donor
                effective_source = donor_source
                founder_reused = generation == 1
                if arm in {"erase_g2", "rescue_g3"} and generation == 2:
                    effective = baseline
                    effective_source = "explicit-erase"
                    founder_reused = False
                elif arm == "rescue_g3" and generation == 3:
                    effective = founder
                    effective_source = "explicit-founder-rescue"
                    founder_reused = True
                normalized = normalized_state_vector(effective, baseline, scale, mode)
                copied_vector = copy_normalized(
                    normalized, keep, noise, float(environment["retention"])
                )
                post_copy = state_from_normalized(copied_vector, baseline, scale, memory, mode)
                with_fingerprint = generation in checkpoints
                if with_fingerprint:
                    result = _develop_and_fingerprint(
                        backend, memory, calibration, post_copy, config
                    )
                else:
                    developed = _develop(backend, memory, post_copy, config)
                    result = {
                        "adult_state": state_payload(developed["adult"]),
                        "sampled_y": developed["sampled_y"],
                        "raw_fingerprint": None,
                        "fingerprint": None,
                        "probes": None,
                        "valid": developed["valid"],
                        "cpu_seconds": developed["cpu_seconds"],
                        "wall_seconds": developed["wall_seconds"],
                    }
                total_cpu += float(result["cpu_seconds"])
                adult = state_from_payload(result["adult_state"])
                if adult is None:
                    adult = post_copy.copy()
                score = (
                    form_score(result["fingerprint"], reference["form_a"], reference["form_b"])
                    if result["valid"] and result["fingerprint"] is not None
                    else None
                )
                record_id = (
                    f"native-lineage|{task_id}|{mode}|{seed_index}|{history}|{arm}|g{generation}"
                )
                records.append(
                    {
                        "task_id": record_id,
                        "memory_task_id": task_id,
                        "model_id": memory.key.model_id,
                        "state_mode": mode,
                        "environment": "moderate",
                        "seed_index": int(seed_index),
                        "philox_seed": seed_value,
                        "history": history,
                        "condition": arm,
                        "generation": generation,
                        "donor_source": effective_source,
                        "donor_parent_record_id": parent_record_id,
                        "founder_reused": founder_reused,
                        "inherited_state": copied_vector,
                        "post_copy_state": state_payload(post_copy),
                        "form_score": score,
                        "rulebook_inherited": False,
                        **result,
                    }
                )
                donor, donor_source = next_native_donor(arm, post_copy, adult, generation)
                parent_record_id = record_id
    payload = {
        "protocol_digest": protocol_digest,
        "memory_task_id": task_id,
        "state_mode": mode,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def native_lineage_decision(
    records: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["native_lineage"]
    rows = {
        (
            str(row["memory_task_id"]),
            int(row["seed_index"]),
            int(row["generation"]),
            str(row["history"]),
            str(row["condition"]),
        ): row
        for row in records
    }
    summaries: list[dict[str, Any]] = []
    for candidate in candidates:
        task_id = str(candidate["memory_task_id"])
        checkpoint_summaries: dict[str, Any] = {}
        for generation in (4, 8):
            seed_metrics: list[dict[str, Any]] = []
            for seed_index in range(int(settings["seeds"])):
                pairs: dict[str, tuple[float, float] | None] = {}
                for arm in NATIVE_LINEAGE_ARMS:
                    a = rows.get((task_id, seed_index, generation, "a", arm))
                    b = rows.get((task_id, seed_index, generation, "b", arm))
                    pairs[arm] = (
                        None
                        if a is None
                        or b is None
                        or not a.get("valid")
                        or not b.get("valid")
                        or a.get("form_score") is None
                        or b.get("form_score") is None
                        else (float(a["form_score"]), float(b["form_score"]))
                    )
                valid = bool(all(value is not None for value in pairs.values()))
                metric: dict[str, Any] = {"seed_index": seed_index, "valid": valid}
                if valid:
                    crossover = {
                        arm: 0.5 * (values[0] - values[1]) for arm, values in pairs.items()
                    }
                    active = crossover["active_rewrite"]
                    denominator = max(abs(active), 1e-12)
                    controls = [
                        abs(value)
                        for arm in ("normalized_shuffle", "norm_matched_random", "control")
                        for value in pairs[arm]
                    ]
                    metric.update(
                        {
                            "crossovers": crossover,
                            "active_correct": bool(
                                pairs["active_rewrite"][0] > 0
                                and pairs["active_rewrite"][1] < 0
                            ),
                            "wrong_history_reversed": crossover["wrong_history"] < 0,
                            "inversion_reversed": crossover["inversion"] < 0,
                            "active_passive_advantage": active
                            - abs(crossover["passive"]),
                            "erase_removal_fraction": (
                                active - abs(crossover["erase_g2"])
                            )
                            / denominator,
                            "rescue_fraction": crossover["rescue_g3"] / denominator,
                            "control_fraction": max(controls) / denominator,
                        }
                    )
                seed_metrics.append(metric)
            valid_rows = [row for row in seed_metrics if row["valid"]]

            def med(key: str) -> float:
                return (
                    float(np.median([float(row[key]) for row in valid_rows]))
                    if valid_rows
                    else 0.0
                )

            active_values = [
                float(row["crossovers"]["active_rewrite"]) for row in valid_rows
            ]
            active_crossover = float(np.median(active_values)) if active_values else 0.0
            consistent = sum(
                bool(
                    row.get("active_correct")
                    and row.get("wrong_history_reversed")
                    and row.get("inversion_reversed")
                    and float(row.get("control_fraction", math.inf))
                    <= float(settings["control_max_fraction"])
                )
                for row in valid_rows
            )
            metrics = {
                "active_crossover": active_crossover,
                "active_passive_advantage": med("active_passive_advantage"),
                "erase_removal_fraction": med("erase_removal_fraction"),
                "rescue_fraction": med("rescue_fraction"),
                "control_fraction": med("control_fraction"),
                "valid_seed_count": len(valid_rows),
                "consistent_seed_count": consistent,
                "seed_metrics": seed_metrics,
            }
            metrics["pass"] = bool(
                metrics["active_crossover"] >= float(settings["crossover_min"])
                and metrics["active_passive_advantage"]
                >= float(settings["active_passive_advantage_min"])
                and metrics["erase_removal_fraction"]
                >= float(settings["erase_removal_fraction_min"])
                and metrics["rescue_fraction"] >= float(settings["rescue_fraction_min"])
                and metrics["control_fraction"] <= float(settings["control_max_fraction"])
                and consistent >= int(settings["minimum_consistent_seeds"])
            )
            checkpoint_summaries[str(generation)] = metrics
        passed = bool(all(row["pass"] for row in checkpoint_summaries.values()))
        summaries.append(
            {
                "memory_task_id": task_id,
                "model_id": int(task_id.split("-")[0]),
                "state_mode": candidate["state_mode"],
                "checkpoints": checkpoint_summaries,
                "pass": passed,
            }
        )
    return {
        "task_id": "native-lineage-decision",
        "candidate_summaries": summaries,
        "passing_candidates": [row["memory_task_id"] for row in summaries if row["pass"]],
        "pass": any(bool(row["pass"]) for row in summaries),
        "verdict": (
            "native-post-reset-renewal-through-g8"
            if any(bool(row["pass"]) for row in summaries)
            else "no-native-post-reset-renewal-through-g8"
        ),
    }


def renew_packet(copied: Sequence[float], encoded_adult: Sequence[float], half_life: int) -> np.ndarray:
    rho = 2.0 ** (-1.0 / float(half_life))
    return rho * np.asarray(copied, dtype=float) + (1.0 - rho) * np.asarray(
        encoded_adult, dtype=float
    )


def _compression_channel(parent: Path, task_id: str, codec_id: str) -> dict[str, Any]:
    payload = json.loads((parent / "channels.json").read_text(encoding="utf-8"))
    matches = [
        row
        for row in payload["channels"]
        if row["memory_task_id"] == task_id and row["codec"]["codec_id"] == codec_id
    ]
    if len(matches) != 1:
        raise ValueError(f"missing unique compact channel {task_id}/{codec_id}")
    return matches[0]


def _engineered_founder_payload(
    arm: str,
    history: str,
    codec: Mapping[str, Any],
    form_vectors: Mapping[str, np.ndarray],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, str]:
    source = encode_codec(codec, form_vectors[history])
    opposite_history = "b" if history == "a" else "a"
    opposite = encode_codec(codec, form_vectors[opposite_history])
    midpoint = 0.5 * (source + opposite)
    zero = encode_codec(codec, np.zeros(int(codec["state_dimension"])))
    if arm in {"intact", "reader_off", "renewal_off", "passive", "erase", "rescue"}:
        return source.copy(), zero, f"form-{history}"
    if arm in {"writer_off", "zero"}:
        return zero.copy(), zero, "zero-packet"
    if arm == "opposite":
        return opposite.copy(), zero, f"opposite-form-{opposite_history}"
    if arm == "inversion":
        return invert_about_midpoint(source, midpoint), zero, "payload-midpoint-inversion"
    if arm == "normalized_shuffle":
        shuffled, method = normalized_shuffle(source - midpoint, rng)
        return midpoint + shuffled, zero, f"payload-shuffle:{method}"
    raise ValueError(f"unknown engineered arm: {arm}")


def _engineered_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        parent_path,
        output_path,
        candidate,
        run_mode,
        frozen_setting,
        environment_name,
        seed_indices,
        shard_key,
    ) = args
    config = load_ca_bridge_config(Path(config_path))
    atlas = Path(atlas_path)
    upstream = Path(upstream_path)
    parent = Path(parent_path)
    output = Path(output_path)
    task_id = str(candidate["memory_task_id"])
    codec_id = str(candidate["codec_id"])
    shard = output / ".shards" / f"engineered-{run_mode}" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        prior = json.loads(shard.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return prior
    channel = _compression_channel(parent, task_id, codec_id)
    codec = channel["codec"]
    channel_input = channel["channel_input"]
    state_mode = str(channel["state_mode"])
    reader_mode = str(channel["reader_mode"])
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    calibration = _calibration_map(atlas)[task_id]
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))

    def load_state(name: str) -> State:
        state = state_from_payload(channel_input[name])
        if state is None:
            raise ValueError(f"invalid engineered channel state {name}")
        return state

    baseline = load_state("baseline_state")
    forms = {"a": load_state("form_a_state"), "b": load_state("form_b_state")}
    scale = np.asarray(channel_input["state_scale"], dtype=float)
    form_vectors = {
        history: normalized_state_vector(state, baseline, scale, state_mode)
        for history, state in forms.items()
    }
    reference = channel_input["reference"]
    settings = config["engineered_renewal"]
    if run_mode == "grid":
        parameter_settings = [
            (int(half_life), float(coupling))
            for coupling in settings["couplings"]
            for half_life in settings["half_lives"]
        ]
        arms = ("intact", "renewal_off")
        generations = int(settings["grid_generation"])
        checkpoints = {generations}
        environment_name = "ordinary"
        environment = settings["environments"][environment_name]
    elif run_mode in {"validation", "g16"}:
        if frozen_setting is None or environment_name is None:
            raise ValueError("engineered validation requires a setting and environment")
        parameter_settings = [
            (int(frozen_setting["half_life"]), float(frozen_setting["coupling"]))
        ]
        arms = ENGINEERED_ARMS
        if run_mode == "validation":
            generations = int(settings["validation_generations"])
            checkpoints = {int(value) for value in settings["validation_checkpoints"]}
        else:
            generations = int(config["g16_replication"]["generations"])
            checkpoints = {int(value) for value in config["g16_replication"]["checkpoints"]}
        environment = settings["environments"][str(environment_name)]
    else:
        raise ValueError(f"unknown engineered run mode: {run_mode}")
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for half_life, coupling in parameter_settings:
        for seed_index in seed_indices:
            for history in ("a", "b"):
                for arm in arms:
                    rng = np.random.Generator(
                        np.random.Philox(
                            _seed(config, "engineered-founder", task_id, run_mode, seed_index, history, arm)
                        )
                    )
                    founder, zero_payload, founder_source = _engineered_founder_payload(
                        arm, history, codec, form_vectors, rng
                    )
                    donor_packet = founder.copy()
                    donor_source = founder_source
                    passive_donor: State | None = None
                    parent_record_id: str | None = None
                    for generation in range(1, generations + 1):
                        founder_reused = generation == 1
                        effective = donor_packet
                        effective_source = donor_source
                        if arm in {"erase", "rescue"} and generation == 2:
                            effective = zero_payload
                            effective_source = "explicit-erase"
                            founder_reused = False
                        elif arm == "rescue" and generation == 3:
                            effective = founder
                            effective_source = "explicit-founder-rescue"
                            founder_reused = True
                        keep, noise, seed_value = common_damage(
                            config,
                            f"engineered-{run_mode}-packet",
                            task_id,
                            int(seed_index),
                            generation,
                            len(founder),
                            environment,
                        )
                        copied = zero_payload + copy_normalized(
                            np.asarray(effective) - zero_payload,
                            keep,
                            noise,
                            float(environment["retention"]),
                        )
                        if arm == "passive" and generation > 1:
                            if passive_donor is None:
                                raise ValueError("passive lineage lost its current donor")
                            passive_vector = normalized_state_vector(
                                passive_donor, baseline, scale, state_mode
                            )
                            state_keep, state_noise, _ = common_damage(
                                config,
                                f"engineered-{run_mode}-passive-state",
                                task_id,
                                int(seed_index),
                                generation,
                                len(scale),
                                environment,
                            )
                            copied_state = copy_normalized(
                                passive_vector,
                                state_keep,
                                state_noise,
                                float(environment["retention"]),
                            )
                            decoded = state_from_normalized(
                                copied_state, baseline, scale, memory, state_mode
                            )
                            effective_source = f"passive-post-copy-g{generation - 1}"
                            channel_kind = "passive-native-state"
                        else:
                            decoded_vector = coupling * decode_codec(codec, copied)
                            if arm == "reader_off":
                                decoded_vector = np.zeros_like(decoded_vector)
                            decoded = state_from_normalized(
                                decoded_vector, baseline, scale, memory, state_mode
                            )
                            channel_kind = "engineered-packet"
                        with_fingerprint = generation in checkpoints
                        result = _develop_with_reader(
                            backend,
                            memory,
                            calibration,
                            baseline,
                            decoded,
                            reader_mode,
                            config,
                            with_fingerprint,
                        )
                        total_cpu += float(result["cpu_seconds"])
                        adult = state_from_payload(result["adult_state"])
                        if adult is None:
                            adult = decoded.copy()
                        score = (
                            form_score(
                                result["fingerprint"], reference["form_a"], reference["form_b"]
                            )
                            if result["valid"] and result["fingerprint"] is not None
                            else None
                        )
                        record_id = (
                            f"engineered-{run_mode}|{task_id}|{codec_id}|h{half_life}|c{coupling:g}|"
                            f"{environment_name}|{seed_index}|{history}|{arm}|g{generation}"
                        )
                        records.append(
                            {
                                "task_id": record_id,
                                "memory_task_id": task_id,
                                "model_id": memory.key.model_id,
                                "state_mode": state_mode,
                                "codec_id": codec_id,
                                "codebook_hash": codec["codebook_hash"],
                                "payload_float_count": codec["payload_float_count"],
                                "codebook_float_count": codec["codebook_float_count"],
                                "reader_mode": reader_mode,
                                "half_life": half_life,
                                "coupling": coupling,
                                "environment": environment_name,
                                "seed_index": int(seed_index),
                                "philox_seed": seed_value,
                                "history": history,
                                "condition": arm,
                                "generation": generation,
                                "channel_kind": channel_kind,
                                "donor_source": effective_source,
                                "donor_parent_record_id": parent_record_id,
                                "founder_reused": founder_reused,
                                "copied_payload": copied,
                                "form_score": score,
                                "rulebook_inherited": False,
                                **result,
                            }
                        )
                        if arm == "passive":
                            passive_donor = decoded.copy()
                            donor_source = f"passive-post-copy-g{generation}"
                        elif arm in {"writer_off", "zero"}:
                            donor_packet = zero_payload.copy()
                            donor_source = f"zero-g{generation}"
                        elif arm == "renewal_off":
                            donor_packet = copied.copy()
                            donor_source = f"damaged-copy-g{generation}"
                        else:
                            encoded_adult = encode_codec(
                                codec,
                                normalized_state_vector(adult, baseline, scale, state_mode),
                            )
                            donor_packet = renew_packet(copied, encoded_adult, half_life)
                            donor_source = f"rewritten-g{generation}"
                        parent_record_id = record_id
    payload = {
        "protocol_digest": protocol_digest,
        "run_mode": run_mode,
        "memory_task_id": task_id,
        "codec_id": codec_id,
        "environment": environment_name,
        "seed_indices": list(seed_indices),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def select_engineered_grid(
    records: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["engineered_renewal"]
    rows = {
        (
            str(row["memory_task_id"]),
            int(row["half_life"]),
            float(row["coupling"]),
            int(row["seed_index"]),
            str(row["history"]),
            str(row["condition"]),
        ): row
        for row in records
        if int(row["generation"]) == int(settings["grid_generation"])
    }
    summaries: list[dict[str, Any]] = []
    selections: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        task_id = str(candidate["memory_task_id"])
        task_summaries: list[dict[str, Any]] = []
        for coupling in settings["couplings"]:
            for half_life in settings["half_lives"]:
                seed_metrics: list[dict[str, Any]] = []
                for seed_index in range(int(settings["discovery_seeds"])):
                    values: dict[str, tuple[float, float] | None] = {}
                    for arm in ("intact", "renewal_off"):
                        a = rows.get((task_id, int(half_life), float(coupling), seed_index, "a", arm))
                        b = rows.get((task_id, int(half_life), float(coupling), seed_index, "b", arm))
                        values[arm] = (
                            None
                            if a is None
                            or b is None
                            or not a.get("valid")
                            or not b.get("valid")
                            or a.get("form_score") is None
                            or b.get("form_score") is None
                            else (float(a["form_score"]), float(b["form_score"]))
                        )
                    valid = bool(all(value is not None for value in values.values()))
                    if valid:
                        intact = 0.5 * (values["intact"][0] - values["intact"][1])
                        off = 0.5 * (values["renewal_off"][0] - values["renewal_off"][1])
                    else:
                        intact = off = None
                    seed_metrics.append(
                        {
                            "seed_index": seed_index,
                            "valid": valid,
                            "intact_crossover": intact,
                            "renewal_off_crossover": off,
                            "renewal_advantage": None if not valid else intact - abs(off),
                            "correct": bool(
                                valid
                                and values["intact"][0] > 0
                                and values["intact"][1] < 0
                            ),
                        }
                    )
                valid_rows = [row for row in seed_metrics if row["valid"]]

                def median(key: str) -> float:
                    return (
                        float(np.median([float(row[key]) for row in valid_rows]))
                        if valid_rows
                        else 0.0
                    )

                summary = {
                    "memory_task_id": task_id,
                    "codec_id": candidate["codec_id"],
                    "half_life": int(half_life),
                    "coupling": float(coupling),
                    "intact_crossover": median("intact_crossover"),
                    "renewal_advantage": median("renewal_advantage"),
                    "consistent_seed_count": sum(bool(row["correct"]) for row in valid_rows),
                    "seed_metrics": seed_metrics,
                }
                summary["pass"] = bool(
                    summary["intact_crossover"] >= float(settings["grid_crossover_min"])
                    and summary["renewal_advantage"] >= float(settings["renewal_advantage_min"])
                    and summary["consistent_seed_count"] >= 3
                )
                task_summaries.append(summary)
                summaries.append(summary)
        ranked = sorted(
            (row for row in task_summaries if row["pass"]),
            key=lambda row: (
                float(row["coupling"]),
                int(row["half_life"]),
                -float(row["intact_crossover"]),
            ),
        )
        if ranked:
            selections[task_id] = ranked[0]
    return {
        "task_id": "engineered-grid-selection",
        "setting_summaries": summaries,
        "selections": selections,
        "pass": bool(selections),
    }


def engineered_validation_decision(
    records: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    generation: int,
    direct_replication: bool = False,
) -> dict[str, Any]:
    settings = config["engineered_renewal"]
    thresholds = config["g16_replication"] if direct_replication else settings
    seed_count = int(
        config["g16_replication"]["seeds"]
        if direct_replication
        else settings["validation_seeds"]
    )
    minimum_consistent = int(thresholds["minimum_consistent_seeds"])
    rows = {
        (
            str(row["memory_task_id"]),
            str(row["environment"]),
            int(row["seed_index"]),
            str(row["history"]),
            str(row["condition"]),
        ): row
        for row in records
        if int(row["generation"]) == int(generation)
    }
    summaries: list[dict[str, Any]] = []
    for candidate in candidates:
        task_id = str(candidate["memory_task_id"])
        environment_summaries: dict[str, Any] = {}
        for environment in ("ordinary", "moderate"):
            seed_metrics: list[dict[str, Any]] = []
            for seed_index in range(seed_count):
                pairs: dict[str, tuple[float, float] | None] = {}
                for arm in ENGINEERED_ARMS:
                    a = rows.get((task_id, environment, seed_index, "a", arm))
                    b = rows.get((task_id, environment, seed_index, "b", arm))
                    pairs[arm] = (
                        None
                        if a is None
                        or b is None
                        or not a.get("valid")
                        or not b.get("valid")
                        or a.get("form_score") is None
                        or b.get("form_score") is None
                        else (float(a["form_score"]), float(b["form_score"]))
                    )
                valid = bool(all(value is not None for value in pairs.values()))
                metric: dict[str, Any] = {"seed_index": seed_index, "valid": valid}
                if valid:
                    crossovers = {
                        arm: 0.5 * (values[0] - values[1]) for arm, values in pairs.items()
                    }
                    intact = crossovers["intact"]
                    denominator = max(abs(intact), 1e-12)
                    removal = {
                        arm: (intact - abs(crossovers[arm])) / denominator
                        for arm in ("writer_off", "reader_off", "renewal_off", "erase")
                    }
                    content_scores = [
                        abs(value)
                        for arm in ("normalized_shuffle", "zero")
                        for value in pairs[arm]
                    ]
                    metric.update(
                        {
                            "crossovers": crossovers,
                            "intact_correct": bool(
                                pairs["intact"][0] > 0 and pairs["intact"][1] < 0
                            ),
                            "opposite_reversed": crossovers["opposite"] < 0,
                            "inversion_reversed": crossovers["inversion"] < 0,
                            "removal_fractions": removal,
                            "active_passive_advantage": intact
                            - abs(crossovers["passive"]),
                            "rescue_fraction": crossovers["rescue"] / denominator,
                            "content_fraction": max(content_scores) / denominator,
                        }
                    )
                seed_metrics.append(metric)
            valid_rows = [row for row in seed_metrics if row["valid"]]

            def median(values: Sequence[float]) -> float:
                return float(np.median(values)) if values else 0.0

            intact = median(
                [float(row["crossovers"]["intact"]) for row in valid_rows]
            )
            removal = {
                arm: median(
                    [float(row["removal_fractions"][arm]) for row in valid_rows]
                )
                for arm in ("writer_off", "reader_off", "renewal_off", "erase")
            }
            advantage = median(
                [float(row["active_passive_advantage"]) for row in valid_rows]
            )
            rescue = median([float(row["rescue_fraction"]) for row in valid_rows])
            content = median([float(row["content_fraction"]) for row in valid_rows])
            consistent = sum(
                bool(
                    row.get("intact_correct")
                    and row.get("opposite_reversed")
                    and row.get("inversion_reversed")
                    and min(row.get("removal_fractions", {}).values(), default=-math.inf)
                    >= float(thresholds["removal_fraction_min"])
                    and float(row.get("content_fraction", math.inf))
                    <= float(thresholds["control_max_fraction"])
                )
                for row in valid_rows
            )
            crossover_threshold = float(
                thresholds[
                    "ordinary_crossover_min"
                    if environment == "ordinary"
                    else "moderate_crossover_min"
                ]
            )
            environment_summaries[environment] = {
                "intact_crossover": intact,
                "removal_fractions": removal,
                "active_passive_advantage": advantage,
                "rescue_fraction": rescue,
                "content_fraction": content,
                "valid_seed_count": len(valid_rows),
                "consistent_seed_count": consistent,
                "seed_metrics": seed_metrics,
                "pass": bool(
                    intact >= crossover_threshold
                    and min(removal.values(), default=-math.inf)
                    >= float(thresholds["removal_fraction_min"])
                    and advantage >= float(thresholds["renewal_advantage_min"])
                    and rescue >= float(thresholds["rescue_fraction_min"])
                    and content <= float(thresholds["control_max_fraction"])
                    and consistent >= minimum_consistent
                ),
            }
        summaries.append(
            {
                **dict(candidate),
                "environments": environment_summaries,
                "pass": bool(all(row["pass"] for row in environment_summaries.values())),
            }
        )
    ranked = sorted(
        (row for row in summaries if row["pass"]),
        key=lambda row: (
            -float(row["environments"]["moderate"]["intact_crossover"]),
            int(row.get("payload_float_count", 10**9)),
            str(row["memory_task_id"]),
        ),
    )
    return {
        "task_id": (
            "g16-direct-replication-decision"
            if direct_replication
            else "engineered-validation-decision"
        ),
        "generation": int(generation),
        "outcome_known_direct_replication": bool(direct_replication),
        "candidate_summaries": summaries,
        "ranking": [row["memory_task_id"] for row in ranked],
        "passing_candidates": [row["memory_task_id"] for row in ranked],
        "strongest_candidate": ranked[0] if ranked else None,
        "pass": bool(ranked),
        "verdict": (
            "g16-direct-replication-passed"
            if direct_replication and ranked
            else "g16-direct-replication-failed"
            if direct_replication
            else "engineered-constructive-sufficiency-through-g8"
            if ranked
            else "no-engineered-renewal-through-g8"
        ),
    }


def _validate_atlas(
    config: Mapping[str, Any], atlas: Path, upstream: Path
) -> dict[str, Any]:
    provenance = validate_upstream(upstream, str(config["upstream_commit"]))
    verified = verify_checksums(atlas)
    for name, expected in config["atlas_parent_hashes"].items():
        if sha256_file(atlas / name) != expected:
            raise ValueError(f"atlas parent hash mismatch: {name}")
    registration = json.loads((atlas / "registration.json").read_text(encoding="utf-8"))
    state = json.loads((atlas / "state.json").read_text(encoding="utf-8"))
    if registration.get("experiment_id") != config["atlas_parent_experiment_id"]:
        raise ValueError("wrong observer-atlas parent")
    if state.get("status") != "completed":
        raise ValueError("observer atlas is not completed")
    calibration = _calibration_map(atlas)
    histories = _history_map(atlas)
    tasks = list(config["fixed_cohort_task_ids"])
    if set(calibration) != set(tasks):
        raise ValueError("atlas calibration cohort differs")
    if any((task_id, "naive") not in histories for task_id in tasks):
        raise ValueError("atlas lacks a frozen naive history")
    return {
        "upstream": provenance,
        "checksum_count": len(verified),
        "experiment_id": registration["experiment_id"],
        "manifest_sha256": sha256_file(atlas / "SHA256SUMS"),
    }


def _validate_stage_parent(
    config: Mapping[str, Any], stage: str, parent: Path | None
) -> dict[str, Any] | None:
    expected = config["stage_parents"][stage]
    if expected is None:
        if parent is not None:
            raise ValueError("form qualification must not have a stage parent")
        return None
    if parent is None:
        raise ValueError(f"stage {stage} requires parent stage {expected}")
    verified = verify_checksums(parent)
    registration = json.loads((parent / "registration.json").read_text(encoding="utf-8"))
    state = json.loads((parent / "state.json").read_text(encoding="utf-8"))
    if registration.get("protocol_digest") != digest(config):
        raise ValueError("stage parent uses a different CA-bridge protocol")
    if registration.get("stage") != expected:
        raise ValueError(f"expected parent stage {expected}, got {registration.get('stage')}")
    if state.get("status") != "completed":
        raise ValueError("stage parent is not completed")
    decision = json.loads((parent / "decision.json").read_text(encoding="utf-8"))
    return {
        "stage": expected,
        "experiment_id": registration["experiment_id"],
        "manifest_sha256": sha256_file(parent / "SHA256SUMS"),
        "registration_sha256": sha256_file(parent / "registration.json"),
        "decision_sha256": sha256_file(parent / "decision.json"),
        "checksum_count": len(verified),
        "decision_pass": bool(decision.get("pass", False)),
    }


def _stage_candidates(stage: str, parent: Path | None) -> list[dict[str, Any]]:
    if parent is None:
        return []
    decision = json.loads((parent / "decision.json").read_text(encoding="utf-8"))
    if stage == "native-transfer":
        return [
            {
                "memory_task_id": task_id,
                "model_id": int(str(task_id).split("-")[0]),
            }
            for task_id in decision.get("advanced_candidates", ())
        ]
    if stage == "compression":
        return [dict(row) for row in decision.get("compression_candidates", ())]
    if stage == "native-lineage":
        return [dict(row) for row in decision.get("native_lineage_candidates", ())]
    if stage == "engineered-renewal":
        return [dict(row) for row in decision.get("advanced_channels", ())]
    if stage == "g16-replication":
        strongest = decision.get("strongest_candidate")
        return [] if strongest is None else [dict(strongest)]
    return []


def _hypotheses(stage: str) -> dict[str, Any]:
    descriptions = {
        "form-qualification": "Within-task opposite UCS histories create two durable, content-specific acquired forms.",
        "native-transfer": "Expression or dynamic auxiliary state transmits a form, and post-reset residual state may remain causal.",
        "compression": "A structured low-dimensional state code can retain the frozen A/B coordinate under held-out damage.",
        "native-lineage": "A causal post-reset native channel is actively renewed through eight fresh recipients.",
        "engineered-renewal": "A frozen compact writer/reader channel is constructively sufficient for active G8 renewal.",
        "g16-replication": "The strongest outcome-known G8 engineered channel directly reproduces through G16.",
    }
    return {
        "stage": stage,
        "primary_hypothesis": descriptions[stage],
        "negative_is_informative": True,
        "threshold_relaxation_allowed": False,
        "claim_class": "exploratory-in-silico-hypothesis-generation",
    }


def analyze_ca_bridge(output: Path, final_status: str | None = None) -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    state = json.loads((output / "state.json").read_text(encoding="utf-8"))
    parent_gate = json.loads((output / "parent-gate.json").read_text(encoding="utf-8"))
    decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
    ledger = json.loads((output / "resource-ledger.json").read_text(encoding="utf-8"))
    record_files = list(registration.get("record_files", ()))
    counts = {
        name: sum(1 for _ in read_jsonl(output / name))
        for name in record_files
        if (output / name).is_file()
    }
    required = [
        "registration.json",
        "parent-gate.json",
        "decision.json",
        "resource-ledger.json",
        "runtime-incidents.json",
        *record_files,
    ]
    minimum_completion = bool(parent_gate.get("pass")) and all(
        (output / name).is_file() for name in required
    )
    run_status = final_status or str(state["status"])
    result = {
        "task_id": "ca-bridge-analysis",
        "experiment_id": registration["experiment_id"],
        "stage": registration["stage"],
        "run_status": run_status,
        "minimum_completion_gate": minimum_completion,
        "decision_pass": bool(decision.get("pass", False)),
        "verdict": decision.get("verdict", "undetermined"),
        "record_counts": counts,
        "aggregate_cpu_seconds": float(ledger.get("aggregate_cpu_seconds", 0.0)),
        "active_wall_seconds": float(ledger.get("active_wall_seconds", 0.0)),
        "sealed_negative_is_valid": bool(minimum_completion and not decision.get("pass", False)),
        "claim_boundary": registration["protocol"]["claim_boundary"],
    }
    write_json(output / "analysis.json", result)
    report = f"""# Continuous-GRN CA carrier ladder: {registration['stage']}

Status: **{run_status}**

Verdict: **{result['verdict']}**

Stage gate passed: **{str(result['decision_pass']).lower()}**

This is an exploratory in-silico hypothesis-generation stage. A completed
negative gate is a sealed outcome; it does not authorize threshold changes or
cross-task substitutions. The GRN rulebook (`c`) was held fixed in recipients.

Records: {json.dumps(counts, sort_keys=True)}

Resource use: {result['active_wall_seconds']:.3f} active wall seconds and
{result['aggregate_cpu_seconds']:.3f} aggregate worker CPU seconds.

Claim boundary: {result['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return result


class CaBridgeCampaign:
    def __init__(
        self,
        config_path: Path,
        stage: str,
        atlas: Path,
        parent: Path | None,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_ca_bridge_config(self.config_path)
        self.stage = validate_ca_bridge_stage(self.config, stage)
        self.atlas = atlas.resolve()
        self.parent = None if parent is None else parent.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("CA-bridge workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed CA-bridge stage cannot be resumed")
        self.atlas_gate = _validate_atlas(self.config, self.atlas, self.upstream)
        self.parent_info = _validate_stage_parent(self.config, self.stage, self.parent)
        self.output.mkdir(parents=True, exist_ok=True)
        self.ledger = ResourceLedger(self.output, self.config)
        self.record_files: list[str] = []

    def _parent_identity(self) -> dict[str, Any] | None:
        return self.parent_info

    def _register(self) -> None:
        registration_path = self.output / "registration.json"
        experiment_id = f"{self.config['experiment_id_prefix']}-{self.stage}"
        payload = {
            "experiment_id": experiment_id,
            "stage": self.stage,
            "protocol": self.config,
            "protocol_digest": digest(self.config),
            "workers": self.workers,
            "upstream": self.atlas_gate["upstream"],
            "atlas": {
                "path": str(self.atlas),
                "experiment_id": self.atlas_gate["experiment_id"],
                "manifest_sha256": self.atlas_gate["manifest_sha256"],
            },
            "parent": self._parent_identity(),
            "runtime": _runtime_manifest(),
            "record_files": self.record_files,
        }
        if registration_path.is_file():
            prior = json.loads(registration_path.read_text(encoding="utf-8"))
            for key in ("experiment_id", "stage", "protocol_digest", "parent"):
                if prior.get(key) != payload.get(key):
                    raise ValueError(f"resumed CA-bridge registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"]["container_image_id"]:
                raise ValueError("resumed CA-bridge image differs")
        write_json(registration_path, payload)
        write_json(
            self.output / "parent-gate.json",
            {
                "task_id": "parent-gate",
                "pass": True,
                "atlas": self.atlas_gate,
                "stage_parent": self.parent_info,
            },
        )
        write_json(self.output / "hypotheses.json", _hypotheses(self.stage))
        if not (self.output / "runtime-incidents.json").is_file():
            write_json(self.output / "runtime-incidents.json", {"incidents": []})

    def _state(self, status: str, stage_detail: str, **extra: Any) -> None:
        write_json(
            self.output / "state.json",
            {
                "status": status,
                "stage": self.stage,
                "stage_detail": stage_detail,
                "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **extra,
            },
        )
        self.ledger.checkpoint(stage_detail, _all_shard_cpu(self.output))

    def _enforce(self, stage_detail: str) -> None:
        self.ledger.checkpoint(stage_detail, _all_shard_cpu(self.output))
        self.ledger.enforce_hard()

    def _require_budget(self, stage_detail: str) -> None:
        self._enforce(stage_detail)
        if not self.ledger.may_start():
            raise TimeoutError(f"soft resource boundary reached before {stage_detail}")

    def _write_registration_records(self) -> None:
        path = self.output / "registration.json"
        registration = json.loads(path.read_text(encoding="utf-8"))
        registration["record_files"] = self.record_files
        write_json(path, registration)

    def _run_qualification(self) -> dict[str, Any]:
        self.record_files = ["screen.jsonl", "validation.jsonl"]
        tasks_by_model: dict[int, list[str]] = {}
        for task_id in self.config["fixed_cohort_task_ids"]:
            tasks_by_model.setdefault(int(str(task_id).split("-")[0]), []).append(str(task_id))
        self._state("running", "qualification-screen")
        screen_args = [
            (
                str(self.config_path),
                str(self.atlas),
                str(self.upstream),
                str(self.output),
                model_id,
                task_ids,
                "screen",
                None,
                f"model-{model_id}",
            )
            for model_id, task_ids in tasks_by_model.items()
        ]
        screen_shards = _parallel(
            _qualification_worker, screen_args, min(self.workers, len(screen_args))
        )
        screen_records = _merge_shards(self.output, "screen", screen_shards)
        screen_decision = qualification_screen_decision(screen_records, self.config)
        write_json(self.output / "screen-decision.json", screen_decision)
        self._enforce("qualification-screen-complete")
        validation_records: list[dict[str, Any]] = []
        if screen_decision["validation_nominations"]:
            self._require_budget("qualification-validation")
            validation_args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    int(str(task_id).split("-")[0]),
                    [str(task_id)],
                    "validation",
                    seed_index,
                    f"task-{task_id}-seed-{seed_index}",
                )
                for task_id in screen_decision["validation_nominations"]
                for seed_index in range(int(self.config["qualification"]["validation_seeds"]))
            ]
            self._state("running", "qualification-validation")
            validation_shards = _parallel(
                _qualification_worker,
                validation_args,
                min(self.workers, len(validation_args)),
            )
            validation_records = _merge_shards(
                self.output, "validation", validation_shards
            )
        else:
            _write_jsonl(self.output / "validation.jsonl", [])
        decision = qualification_validation_decision(
            validation_records, screen_decision, self.config
        )
        write_json(self.output / "decision.json", decision)
        return decision

    def _run_native_transfer(self) -> dict[str, Any]:
        self.record_files = ["transfer.jsonl", "reset-residual.jsonl"]
        candidates = _stage_candidates(self.stage, self.parent)
        shards: list[dict[str, Any]] = []
        if candidates:
            self._require_budget("native-transfer")
            args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.parent),
                    str(self.output),
                    row["memory_task_id"],
                    f"task-{row['memory_task_id']}",
                )
                for row in candidates
            ]
            self._state("running", "native-transfer")
            shards = _parallel(_transfer_worker, args, min(self.workers, len(args)))
        transfer = [row for shard in shards for row in shard.get("records", ())]
        residual = [row for shard in shards for row in shard.get("reset_records", ())]
        channels = [row for shard in shards for row in shard.get("channel_inputs", ())]
        _write_jsonl(self.output / "transfer.jsonl", transfer)
        _write_jsonl(self.output / "reset-residual.jsonl", residual)
        write_json(self.output / "channel-inputs.json", {"channels": channels})
        decision = native_transfer_decision(
            transfer,
            residual,
            channels,
            [str(row["memory_task_id"]) for row in candidates],
            self.config,
        )
        write_json(self.output / "decision.json", decision)
        return decision

    def _run_compression(self) -> dict[str, Any]:
        self.record_files = ["discovery.jsonl", "validation.jsonl"]
        candidates = _stage_candidates(self.stage, self.parent)
        shards: list[dict[str, Any]] = []
        if candidates:
            self._require_budget("compression-discovery-validation")
            args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.parent),
                    str(self.output),
                    candidate,
                    f"task-{candidate['memory_task_id']}",
                )
                for candidate in candidates
            ]
            self._state("running", "compression-discovery-validation")
            shards = _parallel(_compression_worker, args, min(self.workers, len(args)))
        discovery = [row for shard in shards for row in shard.get("discovery_records", ())]
        validation = [row for shard in shards for row in shard.get("validation_records", ())]
        codebooks = [
            {"memory_task_id": shard["memory_task_id"], **row}
            for shard in shards
            for row in shard.get("codebooks", ())
        ]
        _write_jsonl(self.output / "discovery.jsonl", discovery)
        _write_jsonl(self.output / "validation.jsonl", validation)
        write_json(
            self.output / "codebooks.json",
            {
                "discovery_seed_indices": list(
                    range(int(self.config["compression"]["discovery_seeds"]))
                ),
                "validation_seed_indices": list(
                    range(100, 100 + int(self.config["compression"]["validation_seeds"]))
                ),
                "codebooks": codebooks,
                "leakage_allowed": False,
            },
        )
        decision = compression_validation_decision(validation, codebooks, self.config)
        write_json(self.output / "decision.json", decision)
        channels: list[dict[str, Any]] = []
        shard_map = {str(shard["memory_task_id"]): shard for shard in shards}
        codebook_map = {
            (str(row["memory_task_id"]), str(row["codec_id"])): row for row in codebooks
        }
        for selected in decision["advanced_channels"]:
            task_id = str(selected["memory_task_id"])
            codec = codebook_map[(task_id, str(selected["codec_id"]))]
            channels.append(
                {
                    **dict(selected),
                    "codec": {key: value for key, value in codec.items() if key != "memory_task_id"},
                    "channel_input": shard_map[task_id]["channel_input"],
                }
            )
        write_json(self.output / "channels.json", {"channels": channels})
        return decision

    def _run_native_lineage(self) -> dict[str, Any]:
        self.record_files = ["lineage.jsonl"]
        candidates = _stage_candidates(self.stage, self.parent)
        shards: list[dict[str, Any]] = []
        if candidates:
            self._require_budget("native-lineage")
            args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.parent),
                    str(self.output),
                    candidate,
                    seed_index,
                    f"task-{candidate['memory_task_id']}-seed-{seed_index}",
                )
                for candidate in candidates
                for seed_index in range(int(self.config["native_lineage"]["seeds"]))
            ]
            self._state("running", "native-lineage")
            shards = _parallel(_native_lineage_worker, args, min(self.workers, len(args)))
        records = _merge_shards(self.output, "lineage", shards)
        decision = native_lineage_decision(records, candidates, self.config)
        write_json(self.output / "decision.json", decision)
        return decision

    def _run_engineered(self) -> dict[str, Any]:
        self.record_files = ["grid.jsonl", "validation.jsonl"]
        candidates = _stage_candidates(self.stage, self.parent)
        grid_shards: list[dict[str, Any]] = []
        if candidates:
            self._require_budget("engineered-grid")
            args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.parent),
                    str(self.output),
                    candidate,
                    "grid",
                    None,
                    None,
                    list(range(int(self.config["engineered_renewal"]["discovery_seeds"]))),
                    f"task-{candidate['memory_task_id']}",
                )
                for candidate in candidates
            ]
            self._state("running", "engineered-grid")
            grid_shards = _parallel(_engineered_worker, args, min(self.workers, len(args)))
        grid = _merge_shards(self.output, "grid", grid_shards)
        selection = select_engineered_grid(grid, candidates, self.config)
        write_json(self.output / "grid-selection.json", selection)
        validation_shards: list[dict[str, Any]] = []
        validation_candidates: list[dict[str, Any]] = []
        candidate_map = {str(row["memory_task_id"]): row for row in candidates}
        for task_id, setting in selection["selections"].items():
            validation_candidates.append({**candidate_map[task_id], **setting})
        if validation_candidates:
            self._require_budget("engineered-validation")
            args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.parent),
                    str(self.output),
                    candidate,
                    "validation",
                    candidate,
                    environment,
                    [seed_index],
                    f"task-{candidate['memory_task_id']}-{environment}-seed-{seed_index}",
                )
                for candidate in validation_candidates
                for environment in ("ordinary", "moderate")
                for seed_index in range(
                    int(self.config["engineered_renewal"]["validation_seeds"])
                )
            ]
            self._state("running", "engineered-validation")
            validation_shards = _parallel(
                _engineered_worker, args, min(self.workers, len(args))
            )
        validation = _merge_shards(self.output, "validation", validation_shards)
        decision = engineered_validation_decision(
            validation, validation_candidates, self.config, generation=8
        )
        write_json(self.output / "decision.json", decision)
        # Materialise the exact frozen compact interfaces for the separate G16
        # run; it must not reach through an unsealed grandparent path.
        parent_channels = json.loads((self.parent / "channels.json").read_text(encoding="utf-8"))
        selected_ids = {
            (str(row["memory_task_id"]), str(row["codec_id"]))
            for row in validation_candidates
        }
        channels = [
            row
            for row in parent_channels["channels"]
            if (str(row["memory_task_id"]), str(row["codec"]["codec_id"])) in selected_ids
        ]
        write_json(self.output / "channels.json", {"channels": channels})
        return decision

    def _run_g16(self) -> dict[str, Any]:
        self.record_files = ["replication.jsonl"]
        candidates = _stage_candidates(self.stage, self.parent)
        shards: list[dict[str, Any]] = []
        if candidates:
            self._require_budget("g16-direct-replication")
            candidate = candidates[0]
            args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.parent),
                    str(self.output),
                    candidate,
                    "g16",
                    candidate,
                    environment,
                    [seed_index],
                    f"task-{candidate['memory_task_id']}-{environment}-seed-{seed_index}",
                )
                for environment in ("ordinary", "moderate")
                for seed_index in range(int(self.config["g16_replication"]["seeds"]))
            ]
            self._state("running", "g16-direct-replication")
            shards = _parallel(_engineered_worker, args, min(self.workers, len(args)))
        records = _merge_shards(self.output, "replication", shards)
        decision = engineered_validation_decision(
            records,
            candidates,
            self.config,
            generation=16,
            direct_replication=True,
        )
        write_json(self.output / "decision.json", decision)
        return decision

    def run(self) -> int:
        dispatch = {
            "form-qualification": self._run_qualification,
            "native-transfer": self._run_native_transfer,
            "compression": self._run_compression,
            "native-lineage": self._run_native_lineage,
            "engineered-renewal": self._run_engineered,
            "g16-replication": self._run_g16,
        }
        self.record_files = {
            "form-qualification": ["screen.jsonl", "validation.jsonl"],
            "native-transfer": ["transfer.jsonl", "reset-residual.jsonl"],
            "compression": ["discovery.jsonl", "validation.jsonl"],
            "native-lineage": ["lineage.jsonl"],
            "engineered-renewal": ["grid.jsonl", "validation.jsonl"],
            "g16-replication": ["replication.jsonl"],
        }[self.stage]
        self._register()
        self.ledger.start_heartbeat()
        try:
            self._state("running", "starting")
            dispatch[self.stage]()
            self._enforce("stage-complete")
            self._write_registration_records()
            self._state("finalizing", "analysis")
            analyze_ca_bridge(self.output, final_status="completed")
            self._state("completed", "complete")
            self.ledger.close()
            # Refresh analysis/report after the final ledger checkpoint.
            analyze_ca_bridge(self.output, final_status="completed")
            write_checksums(self.output)
            return 0
        except TimeoutError as error:
            self._state("time-budget-exhausted", "interrupted", error=str(error))
            self.ledger.close()
            return 124
        except BaseException as error:
            incidents = {"incidents": []}
            path = self.output / "runtime-incidents.json"
            if path.is_file():
                incidents = json.loads(path.read_text(encoding="utf-8"))
            incidents.setdefault("incidents", []).append(
                {
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "stage": self.stage,
                    "error": repr(error),
                }
            )
            write_json(path, incidents)
            self._state("failed", "exception", error=repr(error))
            self.ledger.close()
            raise


def run_ca_bridge(
    config: Path,
    stage: str,
    atlas: Path,
    parent: Path | None,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return CaBridgeCampaign(config, stage, atlas, parent, upstream, output, workers).run()


def _phase_projection(stage: str, candidate_count: int) -> int:
    upper = {
        "form-qualification": 6500,
        "native-transfer": 3375 * candidate_count,
        "compression": 6750 * candidate_count,
        "native-lineage": 4700 * candidate_count,
        "engineered-renewal": 6400 * candidate_count,
        "g16-replication": 10000 if candidate_count else 0,
    }
    return int(upper[stage])


def smoke_ca_bridge(
    config_path: Path,
    stage: str,
    atlas: Path,
    parent: Path | None,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_ca_bridge_config(config_path)
    validate_ca_bridge_stage(config, stage)
    atlas = atlas.resolve()
    parent = None if parent is None else parent.resolve()
    upstream = upstream.resolve()
    atlas_gate = _validate_atlas(config, atlas, upstream)
    parent_gate = _validate_stage_parent(config, stage, parent)
    candidates = _stage_candidates(stage, parent)
    if stage == "form-qualification":
        candidate_count = len(config["fixed_cohort_task_ids"])
        probe_task = str(config["fixed_cohort_task_ids"][0])
    else:
        candidate_count = len(candidates)
        probe_task = None if not candidates else str(candidates[0]["memory_task_id"])
    calibration_rows = _calibration_map(atlas)
    measured_cpu = measured_wall = 0.0
    biological_valid = True
    if probe_task is not None:
        released = load_released_task(upstream, probe_task)
        memory = load_memory(released.memory_path, released.key)
        backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
        start = _atlas_naive_start(_history_map(atlas), probe_task)
        phase = backend.run_unstimulated(
            start,
            float(config["phase_duration"]),
            memory.key.response_id,
            int(config["trajectory_samples"]),
        )
        measured_cpu = float(phase.cpu_seconds)
        measured_wall = float(phase.wall_seconds)
        biological_valid = bool(phase.valid)
    historical_units = [
        float(row["selected_phase"]["cpu_seconds"])
        for row in calibration_rows.values()
        if row.get("selected_phase") and row["selected_phase"].get("cpu_seconds") is not None
    ]
    phase_unit = float(np.median(historical_units)) if historical_units else max(measured_cpu, 1.0)
    phase_equivalents = _phase_projection(stage, candidate_count)
    projected_cpu = phase_equivalents * phase_unit * float(config["projection_safety_factor"])
    projected_wall = projected_cpu / int(config["max_workers"])
    gate_stop = stage != "form-qualification" and candidate_count == 0
    production_allowed = bool(
        biological_valid
        and (
            gate_stop
            or (
                projected_cpu < float(config["soft_aggregate_cpu_seconds"])
                and projected_wall < float(config["soft_wall_seconds"])
            )
        )
    )
    result = {
        "target": "ca-bridge-carrier-ladder",
        "stage": stage,
        "pass": production_allowed,
        "production_launch_allowed": production_allowed,
        "gate_stop_expected": gate_stop,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "atlas_parent_manifest_sha256": atlas_gate["manifest_sha256"],
        "stage_parent_manifest_sha256": None
        if parent_gate is None
        else parent_gate["manifest_sha256"],
        "candidate_count": candidate_count,
        "biological_probe": {
            "memory_task_id": probe_task,
            "valid": biological_valid,
            "cpu_seconds": measured_cpu,
            "wall_seconds": measured_wall,
        },
        "projection": {
            "phase_equivalents": phase_equivalents,
            "historical_phase_cpu_seconds": phase_unit,
            "safety_factor": config["projection_safety_factor"],
            "projected_aggregate_cpu_seconds": projected_cpu,
            "projected_active_wall_seconds_at_four_workers": projected_wall,
        },
        "deterministic_batch_plan": (
            "model/task shards"
            if stage == "form-qualification"
            else "candidate shards"
            if stage in {"native-transfer", "compression"}
            else "candidate-by-seed shards"
        ),
        "worker_cap": config["max_workers"],
    }
    result = json.loads(canonical_json(result))
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "smoke.json", result)
    return result


def ca_bridge_status(output: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"output": str(output.resolve())}
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "screen-decision",
        "grid-selection",
        "decision",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    registration_path = output / "registration.json"
    if registration_path.is_file():
        registration = json.loads(registration_path.read_text(encoding="utf-8"))
        result["stage"] = registration.get("stage")
        for name in registration.get("record_files", ()):
            path = output / name
            if path.is_file():
                result[f"{Path(name).stem}_records"] = sum(1 for _ in read_jsonl(path))
    result["sealed"] = (output / "SHA256SUMS").is_file()
    return result
