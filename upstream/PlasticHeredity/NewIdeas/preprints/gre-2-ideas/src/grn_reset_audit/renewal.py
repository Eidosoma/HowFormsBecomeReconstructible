"""Latent-memory carrier and renewal campaign.

The campaign deliberately treats renewal as a registered in-silico state
bottleneck.  Native expression state is tested before a conditional engineered
slow mark.  All production work is sharded by BioModel for deterministic,
resumable execution with no shared worker writes.
"""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import os
import platform
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Mapping

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
from .engine import JaxBackend, State, is_broken, reset_margin
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    validate_upstream,
)


PARENT_ARMS = ("naive", "trained_no_reset", "combined_reset", "control_only")
MARK_CONTROLS = (
    "founder_write_off",
    "reader_off",
    "renewal_off",
    "inert",
    "shuffle",
    "erase",
    "rescue",
    "paired_donor",
    "sign_reverse",
)


def load_renewal_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported renewal schema")
    if config.get("experiment_kind") != "latent-memory-renewal":
        raise ValueError("not a latent-memory-renewal protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("renewal protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("renewal protocol does not pin the historical generator")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("renewal protocol must cap workers at four")
    if not (
        0 < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 28800.0
    ):
        raise ValueError("renewal wall budget exceeds or misorders eight hours")
    if not (
        0 < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 112800.0
    ):
        raise ValueError("renewal aggregate CPU budget is invalid")
    pairs = config.get("fixed_model_pairs", {})
    if list(pairs) != ["10", "16", "37", "204"]:
        raise ValueError("renewal model-pair order differs from the frozen cohort")
    tasks = [task for pair in pairs.values() for task in pair]
    if len(tasks) != 8 or len(set(tasks)) != 8:
        raise ValueError("renewal cohort must contain eight unique tasks")
    expected = {"delta_t": 0.01, "phase_duration": 2500.0, "pulse_count": 5}
    for key, value in expected.items():
        if not math.isclose(float(config[key]), value):
            raise ValueError(f"renewal historical setting differs for {key}")
    return config


def fixed_tasks(config: Mapping[str, Any]) -> list[str]:
    return [task for pair in config["fixed_model_pairs"].values() for task in pair]


def _seed(config: Mapping[str, Any], *parts: object) -> int:
    payload = "|".join([str(config["renewal_seed"]), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def dilution_y(naive: np.ndarray, parent: np.ndarray, retention: float) -> np.ndarray:
    retention = float(retention)
    if not 0.0 <= retention <= 1.0:
        raise ValueError("retention must lie in [0,1]")
    return (1.0 - retention) * naive + retention * parent


def partition_mask(
    node_count: int,
    retention: float,
    config: Mapping[str, Any],
    model_id: int,
    future: int,
) -> np.ndarray:
    rng = np.random.Generator(
        np.random.Philox(_seed(config, "partition", model_id, retention, future))
    )
    return rng.random(int(node_count)) < float(retention)


def partition_y(naive: np.ndarray, parent: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if naive.shape != parent.shape or naive.shape != mask.shape:
        raise ValueError("partition shapes differ")
    return np.where(mask, parent, naive)


def mark_scale(memory: Any, naive: np.ndarray, trained: np.ndarray) -> np.ndarray:
    width = np.abs(np.asarray(memory.bounds[:, 1]) - np.asarray(memory.bounds[:, 0]))
    return np.maximum.reduce([width, np.abs(trained - naive), np.full_like(naive, 1e-8)])


def encode_mark(y: np.ndarray, naive: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return np.clip((y - naive) / scale, -1.0, 1.0)


def update_mark(mark: np.ndarray, encoded_adult: np.ndarray, half_life: int) -> np.ndarray:
    rho = 2.0 ** (-1.0 / float(half_life))
    return rho * mark + (1.0 - rho) * encoded_adult


def read_mark(
    naive: np.ndarray, mark: np.ndarray, scale: np.ndarray, coupling: float
) -> np.ndarray:
    return naive + float(coupling) * mark * scale


def _write_jsonl_atomic(path: Path, records: Iterable[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(row) + "\n" for row in records))


def _runtime_manifest() -> dict[str, Any]:
    try:
        import jax

        jax_version = jax.__version__
    except Exception:
        jax_version = "unavailable"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "jax": jax_version,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
    }


class ResourceLedger:
    """Persistent active-wall and completed-worker CPU accounting."""

    def __init__(self, output: Path, config: Mapping[str, Any]):
        self.path = output / "resource-ledger.json"
        prior: dict[str, Any] = {}
        if self.path.is_file():
            prior = json.loads(self.path.read_text(encoding="utf-8"))
        self.prior_wall = float(prior.get("active_wall_seconds", 0.0))
        self.cpu_seconds = float(prior.get("aggregate_cpu_seconds", 0.0))
        self.started = time.monotonic()
        self.stage = "initializing"
        self.config = config
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    @property
    def wall_seconds(self) -> float:
        return self.prior_wall + max(0.0, time.monotonic() - self.started)

    def checkpoint(self, stage: str | None = None, cpu_seconds: float | None = None) -> None:
        with self.lock:
            if stage is not None:
                self.stage = stage
            if cpu_seconds is not None:
                self.cpu_seconds = float(cpu_seconds)
            write_json(
                self.path,
                {
                    "active_wall_seconds": self.wall_seconds,
                    "aggregate_cpu_seconds": self.cpu_seconds,
                    "stage": self.stage,
                    "soft_wall_seconds": self.config["soft_wall_seconds"],
                    "terminate_wall_seconds": self.config["terminate_wall_seconds"],
                    "hard_wall_seconds": self.config["hard_wall_seconds"],
                    "soft_aggregate_cpu_seconds": self.config[
                        "soft_aggregate_cpu_seconds"
                    ],
                    "hard_aggregate_cpu_seconds": self.config[
                        "hard_aggregate_cpu_seconds"
                    ],
                    "updated_utc": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                },
            )

    def start_heartbeat(self) -> None:
        def heartbeat() -> None:
            while not self.stop_event.wait(30.0):
                self.checkpoint()

        self.thread = threading.Thread(target=heartbeat, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        self.checkpoint()

    def may_start(self) -> bool:
        return (
            self.wall_seconds < float(self.config["soft_wall_seconds"])
            and self.cpu_seconds
            < float(self.config["soft_aggregate_cpu_seconds"])
        )

    def enforce_hard(self) -> None:
        if self.wall_seconds >= float(self.config["hard_wall_seconds"]):
            raise TimeoutError("cumulative active wall budget exhausted")
        if self.cpu_seconds >= float(self.config["hard_aggregate_cpu_seconds"]):
            raise TimeoutError("aggregate worker CPU budget exhausted")


def _phase_summary(phase: Any, memory: Any) -> dict[str, Any]:
    mean_response = float(phase.mean_y[memory.key.response_id])
    trajectory = np.asarray(phase.response_trajectory, dtype=float)
    return {
        "valid": bool(phase.valid),
        "mean_response": mean_response,
        "learned_margin": learned_margin(memory, mean_response),
        "reset_margin": reset_margin(memory, mean_response),
        "is_broken": bool(is_broken(memory, mean_response)),
        "response_trajectory": trajectory,
        "response_range": float(np.ptp(trajectory)) if len(trajectory) else 0.0,
        "terminal_y": phase.terminal_y,
        "cpu_seconds": float(phase.cpu_seconds),
        "wall_seconds": float(phase.wall_seconds),
    }


def _stimuli(memory: Any, calibration: Mapping[str, Any]) -> tuple[dict[int, float], dict[int, float]]:
    cs = {
        int(memory.cs_id): float(
            memory.bounds[memory.cs_id, memory.stimulus_reg % 2]
        )
    }
    bound = calibration.get("reconstructed_ucs_bound_index")
    if memory.ucs_id is None or bound is None:
        return cs, cs.copy()
    ucs = {int(memory.ucs_id): float(memory.bounds[memory.ucs_id, int(bound)])}
    paired = dict(cs)
    paired.update(ucs)
    return cs, paired


def _develop_and_probe(
    backend: JaxBackend,
    memory: Any,
    calibration: Mapping[str, Any],
    start: State,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    duration = float(config["phase_duration"])
    samples = int(config["trajectory_samples"])
    pulses = int(config["pulse_count"])
    cs, paired = _stimuli(memory, calibration)
    adult = backend.run_unstimulated(
        start, duration, memory.key.response_id, sample_count=samples
    )
    recall = backend.run_phase(
        adult.state.copy(), duration, cs, memory.key.response_id, samples, pulses
    )
    training = backend.run_phase(
        adult.state.copy(), duration, paired, memory.key.response_id, samples, pulses
    )
    washout = backend.run_unstimulated(
        training.state, duration, memory.key.response_id, sample_count=samples
    )
    relearn = backend.run_phase(
        washout.state, duration, cs, memory.key.response_id, samples, pulses
    )
    phases = (adult, recall, training, washout, relearn)
    return {
        "adult_state": state_payload(adult.state),
        "adult_terminal_y": adult.terminal_y,
        "recall": _phase_summary(recall, memory),
        "relearn": _phase_summary(relearn, memory),
        "valid": bool(all(phase.valid for phase in phases)),
        "cpu_seconds": float(sum(phase.cpu_seconds for phase in phases)),
        "wall_seconds": float(sum(phase.wall_seconds for phase in phases)),
    }


def _load_parent(parent: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, dict[str, Any]]]:
    histories = {
        (row["memory_task_id"], row["arm"]): row
        for row in read_jsonl(parent / "histories.jsonl")
    }
    calibration = {
        row["memory_task_id"]: row
        for row in read_jsonl(parent / "calibration.jsonl")
    }
    return histories, calibration


def _checkpoint_state(
    histories: Mapping[tuple[str, str], Mapping[str, Any]],
    task_id: str,
    arm: str,
    checkpoint: float,
) -> State:
    key = f"{float(checkpoint):g}"
    payload = histories[(task_id, arm)]["checkpoints"][key]["state"]
    state = state_from_payload(payload)
    if state is None:
        raise ValueError(f"invalid parent state for {task_id}/{arm}")
    return state


def _native_model_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        parent_path,
        upstream_path,
        output_path,
        model_id,
        tasks,
        profile,
    ) = args
    config = load_renewal_config(Path(config_path))
    parent = Path(parent_path)
    upstream = Path(upstream_path)
    output = Path(output_path)
    shard = output / ".shards" / "native" / f"model-{model_id}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        existing = json.loads(shard.read_text(encoding="utf-8"))
        if existing.get("protocol_digest") == protocol_digest and existing.get("profile") == profile:
            return existing
    histories, calibrations = _load_parent(parent)
    backend = JaxBackend(upstream, int(model_id), delta_t=float(config["delta_t"]))
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    futures = int(
        config["partition_futures"]
        if profile == "full"
        else config["lite_partition_futures"]
    )
    for task_id in tasks:
        released = load_released_task(upstream, task_id)
        memory = load_memory(released.memory_path, released.key)
        calibration = calibrations[task_id]
        naive = _checkpoint_state(
            histories, task_id, "naive", float(config["parent_checkpoint"])
        )
        parent_states = {
            arm: _checkpoint_state(
                histories, task_id, arm, float(config["parent_checkpoint"])
            )
            for arm in PARENT_ARMS
        }
        for retention in config["dilution_retention"]:
            for arm in PARENT_ARMS:
                y = dilution_y(naive.y, parent_states[arm].y, float(retention))
                start = State(y, naive.w.copy(), naive.c.copy(), naive.t)
                result = _develop_and_probe(
                    backend, memory, calibration, start, config
                )
                total_cpu += float(result["cpu_seconds"])
                records.append(
                    {
                        "task_id": f"native|{task_id}|dilution|{float(retention):g}|0|{arm}",
                        "memory_task_id": task_id,
                        "model_id": int(model_id),
                        "operator": "dilution",
                        "retention": float(retention),
                        "future": 0,
                        "arm": arm,
                        **result,
                    }
                )
        for retention in config["partition_retention"]:
            for future in range(futures):
                mask = partition_mask(
                    memory.node_count,
                    float(retention),
                    config,
                    int(model_id),
                    future,
                )
                for arm in PARENT_ARMS:
                    y = partition_y(naive.y, parent_states[arm].y, mask)
                    start = State(y, naive.w.copy(), naive.c.copy(), naive.t)
                    result = _develop_and_probe(
                        backend, memory, calibration, start, config
                    )
                    total_cpu += float(result["cpu_seconds"])
                    records.append(
                        {
                            "task_id": f"native|{task_id}|partition|{float(retention):g}|{future}|{arm}",
                            "memory_task_id": task_id,
                            "model_id": int(model_id),
                            "operator": "partition",
                            "retention": float(retention),
                            "future": future,
                            "arm": arm,
                            "inherited_node_count": int(np.sum(mask)),
                            **result,
                        }
                    )
    payload = {
        "protocol_digest": protocol_digest,
        "profile": profile,
        "model_id": int(model_id),
        "tasks": list(tasks),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def _run_model_workers(
    worker: Any,
    args: list[tuple[Any, ...]],
    workers: int,
) -> list[dict[str, Any]]:
    if workers == 1:
        return [worker(arg) for arg in args]
    context = multiprocessing.get_context("spawn")
    results: dict[int, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        futures = {pool.submit(worker, arg): int(arg[4]) for arg in args}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return [results[int(arg[4])] for arg in args]


def _identity_model_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    """Pickle-safe process-pool sentinel used by the deterministic worker test."""

    return {"model_id": int(args[4]), "tasks": list(args[5])}


def _merge_stage(output: Path, name: str, shards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = [row for shard in shards for row in shard["records"]]
    ids = [row["task_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate record IDs in {name}")
    _write_jsonl_atomic(output / f"{name}.jsonl", records)
    return records


def _paired_values(
    rows: list[dict[str, Any]], endpoint: str
) -> dict[str, list[tuple[int, float, bool]]]:
    result: dict[str, list[tuple[int, float, bool]]] = {arm: [] for arm in PARENT_ARMS}
    for row in rows:
        item = row[endpoint]
        result[row["arm"]].append(
            (int(row["future"]), float(item["learned_margin"]), bool(row["valid"]))
        )
    for arm in result:
        result[arm].sort()
    return result


def _consistency(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if not len(finite):
        return 0.0
    median = float(np.median(finite))
    if abs(median) <= 1e-12:
        return 0.0
    return float(np.mean(np.sign(finite) == np.sign(median)))


def native_branch_decision(
    records: list[dict[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    tasks = fixed_tasks(config)
    models = {task: int(task.split("-")[0]) for task in tasks}
    cells: list[dict[str, Any]] = []
    for task in tasks:
        task_rows = [row for row in records if row["memory_task_id"] == task]
        boundaries = sorted(
            {(row["operator"], float(row["retention"])) for row in task_rows},
            key=lambda item: (item[1], 0 if item[0] == "partition" else 1),
        )
        for operator, retention in boundaries:
            rows = [
                row
                for row in task_rows
                if row["operator"] == operator
                and math.isclose(float(row["retention"]), retention)
            ]
            endpoint_results: dict[str, Any] = {}
            signal_endpoints: list[str] = []
            for endpoint in ("recall", "relearn"):
                values = _paired_values(rows, endpoint)
                arrays = {
                    arm: np.asarray([value for _, value, _ in items], dtype=float)
                    for arm, items in values.items()
                }
                valids = {
                    arm: np.asarray([valid for _, _, valid in items], dtype=bool)
                    for arm, items in values.items()
                }
                n = min(len(array) for array in arrays.values())
                arrays = {arm: array[:n] for arm, array in arrays.items()}
                joint_valid = np.logical_and.reduce(
                    [valids[arm][:n] for arm in PARENT_ARMS]
                )
                if np.any(joint_valid):
                    arr = {arm: values_[joint_valid] for arm, values_ in arrays.items()}
                    reference = max(
                        abs(float(np.median(arr["trained_no_reset"] - arr["naive"]))),
                        1e-8,
                    )
                    reset_naive = arr["combined_reset"] - arr["naive"]
                    reset_control = arr["combined_reset"] - arr["control_only"]
                    ratio_naive = abs(float(np.median(reset_naive))) / reference
                    ratio_control = abs(float(np.median(reset_control))) / reference
                    consistency = min(
                        _consistency(reset_naive), _consistency(reset_control)
                    )
                    valid_fraction = float(np.mean(joint_valid))
                else:
                    reference = 0.0
                    ratio_naive = ratio_control = consistency = valid_fraction = 0.0
                signal = bool(
                    valid_fraction >= float(config["valid_future_fraction"])
                    and ratio_naive >= float(config["reference_effect_fraction"])
                    and ratio_control >= float(config["reference_effect_fraction"])
                    and consistency >= float(config["direction_consistency_fraction"])
                )
                if signal:
                    signal_endpoints.append(endpoint)
                endpoint_results[endpoint] = {
                    "signal": signal,
                    "reference": reference,
                    "reset_naive_ratio": ratio_naive,
                    "reset_control_ratio": ratio_control,
                    "direction_consistency": consistency,
                    "valid_fraction": valid_fraction,
                }
            cells.append(
                {
                    "memory_task_id": task,
                    "model_id": models[task],
                    "operator": operator,
                    "retention": retention,
                    "signal": bool(signal_endpoints),
                    "signal_endpoints": signal_endpoints,
                    "endpoints": endpoint_results,
                }
            )
    zero_identity = True
    trained_memories: set[str] = set()
    trained_models: set[int] = set()
    for task in tasks:
        zero = [
            row
            for row in records
            if row["memory_task_id"] == task
            and row["operator"] == "dilution"
            and math.isclose(float(row["retention"]), 0.0)
        ]
        for endpoint in ("recall", "relearn"):
            values = [float(row[endpoint]["learned_margin"]) for row in zero]
            zero_identity = zero_identity and bool(
                values and np.allclose(values, values[0], rtol=1e-7, atol=1e-9)
            )
        full = [
            row
            for row in records
            if row["memory_task_id"] == task
            and row["operator"] == "dilution"
            and math.isclose(float(row["retention"]), 1.0)
        ]
        value = {row["arm"]: row for row in full}
        if all(arm in value and value[arm]["valid"] for arm in ("naive", "trained_no_reset")):
            separation = max(
                abs(
                    float(value["trained_no_reset"][endpoint]["learned_margin"])
                    - float(value["naive"][endpoint]["learned_margin"])
                )
                for endpoint in ("recall", "relearn")
            )
            if separation > 1e-8:
                trained_memories.add(task)
                trained_models.add(models[task])
    assay_valid = bool(
        zero_identity
        and len(trained_memories) >= int(config["trained_control_min_memories"])
        and len(trained_models) >= int(config["trained_control_min_models"])
    )
    boundary_summaries: list[dict[str, Any]] = []
    boundary_keys = sorted(
        {(cell["operator"], cell["retention"]) for cell in cells},
        key=lambda item: (item[1], 0 if item[0] == "partition" else 1),
    )
    for operator, retention in boundary_keys:
        matches = [
            cell
            for cell in cells
            if cell["operator"] == operator
            and math.isclose(float(cell["retention"]), float(retention))
            and cell["signal"]
        ]
        models_here = sorted({cell["model_id"] for cell in matches})
        qualifies = bool(
            retention <= float(config["native_max_retention"])
            and len(matches) >= int(config["native_min_memories"])
            and len(models_here) >= int(config["native_min_models"])
        )
        boundary_summaries.append(
            {
                "operator": operator,
                "retention": retention,
                "signal_memory_count": len(matches),
                "signal_model_count": len(models_here),
                "signal_memories": [cell["memory_task_id"] for cell in matches],
                "qualifies": qualifies,
            }
        )
    selected = next(
        (row for row in boundary_summaries if row["qualifies"]), None
    )
    native_pass = bool(assay_valid and selected is not None)
    branch = "invalid-stop" if not assay_valid else (
        "native-carrier" if native_pass else "engineered-mark"
    )
    return {
        "assay_valid": assay_valid,
        "zero_carryover_identity": zero_identity,
        "trained_control_memory_count": len(trained_memories),
        "trained_control_model_count": len(trained_models),
        "native_pass": native_pass,
        "selected_boundary": selected,
        "branch": branch,
        "boundary_summaries": boundary_summaries,
        "task_cells": cells,
    }


def _replace_coordinates(
    recipient: np.ndarray, donor: np.ndarray, nodes: Iterable[int]
) -> np.ndarray:
    result = recipient.copy()
    indices = np.asarray(list(nodes), dtype=int)
    if len(indices):
        result[indices] = donor[indices]
    return result


def _deranged(values: np.ndarray, config: Mapping[str, Any], *parts: object) -> np.ndarray:
    if len(values) < 2:
        return values.copy()
    rng = np.random.Generator(np.random.Philox(_seed(config, "shuffle", *parts)))
    shift = int(rng.integers(1, len(values)))
    return np.roll(values, shift)


def _carrier_model_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        parent_path,
        upstream_path,
        output_path,
        model_id,
        tasks,
        selected_boundary,
    ) = args
    config = load_renewal_config(Path(config_path))
    parent = Path(parent_path)
    upstream = Path(upstream_path)
    output = Path(output_path)
    shard = output / ".shards" / "carrier" / f"model-{model_id}.json"
    protocol_digest = digest(config)
    boundary_digest = digest(selected_boundary)
    if shard.is_file():
        existing = json.loads(shard.read_text(encoding="utf-8"))
        if (
            existing.get("protocol_digest") == protocol_digest
            and existing.get("boundary_digest") == boundary_digest
        ):
            return existing
    histories, calibrations = _load_parent(parent)
    backend = JaxBackend(upstream, int(model_id), delta_t=float(config["delta_t"]))
    records: list[dict[str, Any]] = []
    recurrence: list[dict[str, Any]] = []
    nominations: list[dict[str, Any]] = []
    total_cpu = 0.0
    pair = {tasks[0]: tasks[1], tasks[1]: tasks[0]}
    operator = str(selected_boundary["operator"])
    retention = float(selected_boundary["retention"])
    for task_id in tasks:
        memory = load_memory(
            load_released_task(upstream, task_id).memory_path,
            load_released_task(upstream, task_id).key,
        )
        calibration = calibrations[task_id]
        states = {
            arm: _checkpoint_state(
                histories, task_id, arm, float(config["parent_checkpoint"])
            )
            for arm in PARENT_ARMS
        }
        naive = states["naive"]
        paired_state = _checkpoint_state(
            histories,
            pair[task_id],
            "combined_reset",
            float(config["parent_checkpoint"]),
        )

        def evaluate(label: str, y: np.ndarray, node: int | None = None) -> dict[str, Any]:
            nonlocal total_cpu
            result = _develop_and_probe(
                backend,
                memory,
                calibration,
                State(y.copy(), naive.w.copy(), naive.c.copy(), naive.t),
                config,
            )
            total_cpu += float(result["cpu_seconds"])
            row = {
                "task_id": f"carrier|{task_id}|{label}|{node if node is not None else 'set'}",
                "memory_task_id": task_id,
                "model_id": int(model_id),
                "condition": label,
                "node": node,
                **result,
            }
            records.append(row)
            return row

        base = {
            arm: evaluate(f"full-{arm}", states[arm].y)
            for arm in PARENT_ARMS
        }
        reference_by_endpoint = {
            endpoint: max(
                abs(
                    float(base["trained_no_reset"][endpoint]["learned_margin"])
                    - float(base["naive"][endpoint]["learned_margin"])
                ),
                1e-8,
            )
            for endpoint in ("recall", "relearn")
        }
        endpoint = max(
            ("recall", "relearn"),
            key=lambda name: min(
                abs(
                    float(base["combined_reset"][name]["learned_margin"])
                    - float(base["naive"][name]["learned_margin"])
                ),
                abs(
                    float(base["combined_reset"][name]["learned_margin"])
                    - float(base["control_only"][name]["learned_margin"])
                ),
            )
            / reference_by_endpoint[name],
        )
        naive_metric = float(base["naive"][endpoint]["learned_margin"])
        full_metric = float(base["combined_reset"][endpoint]["learned_margin"])
        full_effect = max(abs(full_metric - naive_metric), 1e-8)
        node_rows: list[dict[str, Any]] = []
        for node in range(memory.node_count):
            transfer = evaluate(
                "single-transfer", _replace_coordinates(naive.y, states["combined_reset"].y, [node]), node
            )
            ablation = evaluate(
                "single-ablation", _replace_coordinates(states["combined_reset"].y, naive.y, [node]), node
            )
            control_transfer = evaluate(
                "single-control-transfer",
                _replace_coordinates(naive.y, states["control_only"].y, [node]),
                node,
            )
            transfer_fraction = abs(
                float(transfer[endpoint]["learned_margin"]) - naive_metric
            ) / full_effect
            ablation_fraction = 1.0 - abs(
                float(ablation[endpoint]["learned_margin"]) - naive_metric
            ) / full_effect
            control_fraction = abs(
                float(control_transfer[endpoint]["learned_margin"]) - naive_metric
            ) / full_effect
            node_rows.append(
                {
                    "node": node,
                    "score": min(transfer_fraction, ablation_fraction),
                    "transfer_fraction": transfer_fraction,
                    "ablation_fraction": ablation_fraction,
                    "control_fraction": control_fraction,
                }
            )
        ranked = sorted(node_rows, key=lambda row: (-row["score"], row["node"]))
        selected_nodes: list[int] = []
        prefix_evidence: list[dict[str, Any]] = []
        for size in range(1, min(int(config["compact_carrier_max_nodes"]), memory.node_count) + 1):
            nodes = [int(row["node"]) for row in ranked[:size]]
            transfer = evaluate(
                f"prefix-{size}-transfer",
                _replace_coordinates(naive.y, states["combined_reset"].y, nodes),
            )
            ablation = evaluate(
                f"prefix-{size}-ablation",
                _replace_coordinates(states["combined_reset"].y, naive.y, nodes),
            )
            transfer_fraction = abs(
                float(transfer[endpoint]["learned_margin"]) - naive_metric
            ) / full_effect
            ablation_fraction = 1.0 - abs(
                float(ablation[endpoint]["learned_margin"]) - naive_metric
            ) / full_effect
            prefix_evidence.append(
                {
                    "size": size,
                    "nodes": nodes,
                    "transfer_fraction": transfer_fraction,
                    "ablation_fraction": ablation_fraction,
                }
            )
            if (
                transfer_fraction >= float(config["carrier_transfer_fraction"])
                and ablation_fraction >= float(config["carrier_ablation_fraction"])
            ):
                selected_nodes = nodes
                break
        if not selected_nodes:
            selected_nodes = [int(row["node"]) for row in ranked[: min(5, memory.node_count)]]
        random_nodes = sorted(
            range(memory.node_count),
            key=lambda node: _seed(config, "random-carrier", task_id, node),
        )[: len(selected_nodes)]
        random_nodes.sort()
        shuffled_donor = states["combined_reset"].y.copy()
        shuffled_donor[selected_nodes] = _deranged(
            shuffled_donor[selected_nodes], config, task_id, "carrier"
        )
        for label, donor, nodes in (
            ("selected-transfer", states["combined_reset"].y, selected_nodes),
            ("matched-random-transfer", states["combined_reset"].y, random_nodes),
            ("shuffle-transfer", shuffled_donor, selected_nodes),
            ("paired-memory-transfer", paired_state.y, selected_nodes),
            ("control-transfer", states["control_only"].y, selected_nodes),
        ):
            evaluate(label, _replace_coordinates(naive.y, donor, nodes))
        nominations.append(
            {
                "memory_task_id": task_id,
                "model_id": int(model_id),
                "endpoint": endpoint,
                "selected_nodes": selected_nodes,
                "compact_gate_pass": bool(
                    prefix_evidence
                    and any(
                        row["transfer_fraction"]
                        >= float(config["carrier_transfer_fraction"])
                        and row["ablation_fraction"]
                        >= float(config["carrier_ablation_fraction"])
                        for row in prefix_evidence
                    )
                ),
                "random_nodes": random_nodes,
                "ranked_nodes": ranked,
                "prefix_evidence": prefix_evidence,
            }
        )

        recurrence_arms = (
            "intact",
            "renewal_off",
            "erase",
            "rescue",
            "matched_random",
            "shuffle",
            "paired_donor",
            "control_donor",
        )
        for future in range(int(config["recurrence_futures"])):
            for recurrence_arm in recurrence_arms:
                nodes = random_nodes if recurrence_arm == "matched_random" else selected_nodes
                founder = (
                    paired_state.y.copy()
                    if recurrence_arm == "paired_donor"
                    else states["control_only"].y.copy()
                    if recurrence_arm == "control_donor"
                    else shuffled_donor.copy()
                    if recurrence_arm == "shuffle"
                    else states["combined_reset"].y.copy()
                )
                donor = founder.copy()
                current_time = naive.t
                for generation in range(1, max(config["recurrence_generations"]) + 1):
                    effective_nodes = list(nodes)
                    effective_donor = donor
                    if recurrence_arm in {"erase", "rescue"} and generation >= 2:
                        effective_nodes = []
                    if recurrence_arm == "rescue" and generation >= 3:
                        effective_nodes = list(nodes)
                        effective_donor = founder
                    child_y = naive.y.copy()
                    if effective_nodes:
                        if operator == "dilution":
                            mixed = dilution_y(naive.y, effective_donor, retention)
                            child_y[effective_nodes] = mixed[effective_nodes]
                        else:
                            mask = partition_mask(
                                memory.node_count,
                                retention,
                                config,
                                int(model_id),
                                future + generation * 1000,
                            )
                            inherited = [node for node in effective_nodes if mask[node]]
                            child_y = _replace_coordinates(naive.y, effective_donor, inherited)
                    result = _develop_and_probe(
                        backend,
                        memory,
                        calibration,
                        State(child_y, naive.w.copy(), naive.c.copy(), current_time),
                        config,
                    )
                    total_cpu += float(result["cpu_seconds"])
                    adult = state_from_payload(result["adult_state"])
                    if adult is None:
                        break
                    current_time = adult.t
                    if recurrence_arm != "renewal_off":
                        donor = adult.y.copy()
                    if generation in config["recurrence_generations"]:
                        recurrence.append(
                            {
                                "task_id": f"recurrence|{task_id}|{recurrence_arm}|{future}|{generation}",
                                "memory_task_id": task_id,
                                "model_id": int(model_id),
                                "arm": recurrence_arm,
                                "future": future,
                                "generation": generation,
                                "selected_nodes": nodes,
                                **result,
                            }
                        )
    payload = {
        "protocol_digest": protocol_digest,
        "boundary_digest": boundary_digest,
        "model_id": int(model_id),
        "tasks": list(tasks),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
        "recurrence": recurrence,
        "nominations": nominations,
    }
    write_json(shard, payload)
    return payload


def _copy_mark(
    mark: np.ndarray,
    config: Mapping[str, Any],
    model_id: int,
    future: int,
    generation: int,
) -> np.ndarray:
    rng = np.random.Generator(
        np.random.Philox(_seed(config, "mark-copy", model_id, future, generation))
    )
    copied = float(config["mark_copy_dilution"]) * mark
    dropout = rng.random(len(mark)) < float(config["mark_copy_dropout"])
    copied[dropout] = 0.0
    copied += rng.normal(0.0, float(config["mark_copy_sigma"]), len(mark))
    return np.clip(copied, -1.0, 1.0)


def _mark_lineage(
    backend: JaxBackend,
    memory: Any,
    calibration: Mapping[str, Any],
    naive: State,
    trained: State,
    founder_state: State,
    config: Mapping[str, Any],
    half_life: int,
    coupling: float,
    future: int,
    control: str,
    paired_state: State | None = None,
) -> tuple[list[dict[str, Any]], float]:
    scale = mark_scale(memory, naive.y, trained.y)
    founder_mark = encode_mark(founder_state.y, naive.y, scale)
    if control == "paired_donor":
        if paired_state is None:
            raise ValueError("paired donor control lacks a paired state")
        founder_mark = encode_mark(paired_state.y, naive.y, scale)
    elif control == "sign_reverse":
        founder_mark = -founder_mark
    elif control == "founder_write_off":
        founder_mark = np.zeros_like(founder_mark)
    mark = founder_mark.copy()
    current_time = naive.t
    records: list[dict[str, Any]] = []
    cpu = 0.0
    checkpoints = set(int(value) for value in config["recurrence_generations"])
    for generation in range(1, max(checkpoints) + 1):
        if control in {"erase", "rescue"} and generation == 2:
            mark = np.zeros_like(mark)
        if control == "rescue" and generation == 3:
            mark = founder_mark.copy()
        copied = _copy_mark(mark, config, memory.key.model_id, future, generation)
        if control == "shuffle":
            copied = _deranged(
                copied, config, memory.key.task_id, future, generation, "mark"
            )
        effective_coupling = 0.0 if control in {"reader_off", "inert"} else coupling
        child_y = read_mark(naive.y, copied, scale, effective_coupling)
        result = _develop_and_probe(
            backend,
            memory,
            calibration,
            State(child_y, naive.w.copy(), naive.c.copy(), current_time),
            config,
        )
        cpu += float(result["cpu_seconds"])
        adult = state_from_payload(result["adult_state"])
        if adult is None:
            break
        current_time = adult.t
        if control == "renewal_off":
            mark = copied
        else:
            mark = update_mark(
                copied,
                encode_mark(adult.y, naive.y, scale),
                half_life,
            )
        if generation in checkpoints:
            records.append(
                {
                    "generation": generation,
                    "mark_norm": float(np.linalg.norm(mark)),
                    **result,
                }
            )
    return records, cpu


def _mark_grid_model_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        parent_path,
        upstream_path,
        output_path,
        model_id,
        tasks,
        profile,
    ) = args
    config = load_renewal_config(Path(config_path))
    parent = Path(parent_path)
    upstream = Path(upstream_path)
    output = Path(output_path)
    shard = output / ".shards" / "mark-grid" / f"model-{model_id}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        existing = json.loads(shard.read_text(encoding="utf-8"))
        if existing.get("protocol_digest") == protocol_digest and existing.get("profile") == profile:
            return existing
    histories, calibrations = _load_parent(parent)
    backend = JaxBackend(upstream, int(model_id), delta_t=float(config["delta_t"]))
    futures = int(config["mark_futures"] if profile == "full" else config["lite_partition_futures"])
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for task_id in tasks:
        released = load_released_task(upstream, task_id)
        memory = load_memory(released.memory_path, released.key)
        calibration = calibrations[task_id]
        states = {
            arm: _checkpoint_state(
                histories, task_id, arm, float(config["parent_checkpoint"])
            )
            for arm in PARENT_ARMS
        }
        for half_life in config["mark_half_lives"]:
            for coupling in config["mark_couplings"]:
                for future in range(futures):
                    for arm in PARENT_ARMS:
                        lineage, cpu = _mark_lineage(
                            backend,
                            memory,
                            calibration,
                            states["naive"],
                            states["trained_no_reset"],
                            states[arm],
                            config,
                            int(half_life),
                            float(coupling),
                            future,
                            "intact",
                        )
                        total_cpu += cpu
                        for row in lineage:
                            records.append(
                                {
                                    "task_id": f"mark-grid|{task_id}|{half_life}|{float(coupling):g}|{future}|{arm}|{row['generation']}",
                                    "memory_task_id": task_id,
                                    "model_id": int(model_id),
                                    "half_life": int(half_life),
                                    "coupling": float(coupling),
                                    "future": future,
                                    "history": arm,
                                    "control": "intact",
                                    **row,
                                }
                            )
    payload = {
        "protocol_digest": protocol_digest,
        "profile": profile,
        "model_id": int(model_id),
        "tasks": list(tasks),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def mark_selection(
    records: list[dict[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    discovery_models = {int(value) for value in config["mark_discovery_models"]}
    candidates: list[dict[str, Any]] = []
    for half_life in sorted(int(value) for value in config["mark_half_lives"]):
        for coupling in sorted(float(value) for value in config["mark_couplings"]):
            parameter_rows = [
                row
                for row in records
                if row["model_id"] in discovery_models
                and int(row["half_life"]) == half_life
                and math.isclose(float(row["coupling"]), coupling)
                and int(row["generation"]) == 4
            ]
            signals: list[dict[str, Any]] = []
            for task in sorted({row["memory_task_id"] for row in parameter_rows}):
                rows = [row for row in parameter_rows if row["memory_task_id"] == task]
                endpoint_signal = False
                endpoint_payload: dict[str, Any] = {}
                for endpoint in ("recall", "relearn"):
                    values = {
                        arm: np.asarray(
                            [
                                float(row[endpoint]["learned_margin"])
                                for row in rows
                                if row["history"] == arm and row["valid"]
                            ],
                            dtype=float,
                        )
                        for arm in PARENT_ARMS
                    }
                    n = min((len(value) for value in values.values()), default=0)
                    if n:
                        values = {arm: value[:n] for arm, value in values.items()}
                        reference = max(
                            abs(float(np.median(values["trained_no_reset"] - values["naive"]))),
                            1e-8,
                        )
                        reset_naive = values["combined_reset"] - values["naive"]
                        reset_control = values["combined_reset"] - values["control_only"]
                        rn = abs(float(np.median(reset_naive))) / reference
                        rc = abs(float(np.median(reset_control))) / reference
                        consistency = min(
                            _consistency(reset_naive), _consistency(reset_control)
                        )
                    else:
                        rn = rc = consistency = 0.0
                    signal = bool(
                        rn >= float(config["reference_effect_fraction"])
                        and rc >= float(config["reference_effect_fraction"])
                        and consistency >= float(config["direction_consistency_fraction"])
                    )
                    endpoint_signal = endpoint_signal or signal
                    endpoint_payload[endpoint] = {
                        "signal": signal,
                        "reset_naive_ratio": rn,
                        "reset_control_ratio": rc,
                        "direction_consistency": consistency,
                    }
                signals.append(
                    {
                        "memory_task_id": task,
                        "model_id": int(task.split("-")[0]),
                        "signal": endpoint_signal,
                        "endpoints": endpoint_payload,
                    }
                )
            positive = [row for row in signals if row["signal"]]
            models = {row["model_id"] for row in positive}
            qualifies = bool(
                len(positive) >= int(config["mark_min_discovery_memories"])
                and models == discovery_models
            )
            candidates.append(
                {
                    "half_life": half_life,
                    "coupling": coupling,
                    "signal_memory_count": len(positive),
                    "signal_model_count": len(models),
                    "qualifies": qualifies,
                    "task_results": signals,
                }
            )
    selected = next((row for row in candidates if row["qualifies"]), None)
    return {
        "pass": selected is not None,
        "selected": None
        if selected is None
        else {
            "half_life": selected["half_life"],
            "coupling": selected["coupling"],
        },
        "selection_order": "shortest-half-life-then-weakest-coupling",
        "candidates": candidates,
    }


def _mark_validation_model_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        parent_path,
        upstream_path,
        output_path,
        model_id,
        tasks,
        selected,
        profile,
    ) = args
    config = load_renewal_config(Path(config_path))
    parent = Path(parent_path)
    upstream = Path(upstream_path)
    output = Path(output_path)
    shard = output / ".shards" / "mark-validation" / f"model-{model_id}.json"
    selection_digest = digest(selected)
    if shard.is_file():
        existing = json.loads(shard.read_text(encoding="utf-8"))
        if existing.get("protocol_digest") == digest(config) and existing.get("selection_digest") == selection_digest:
            return existing
    histories, calibrations = _load_parent(parent)
    backend = JaxBackend(upstream, int(model_id), delta_t=float(config["delta_t"]))
    futures = int(config["mark_futures"] if profile == "full" else config["lite_partition_futures"])
    pair = {tasks[0]: tasks[1], tasks[1]: tasks[0]}
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for task_id in tasks:
        released = load_released_task(upstream, task_id)
        memory = load_memory(released.memory_path, released.key)
        calibration = calibrations[task_id]
        states = {
            arm: _checkpoint_state(
                histories, task_id, arm, float(config["parent_checkpoint"])
            )
            for arm in PARENT_ARMS
        }
        paired_state = _checkpoint_state(
            histories, pair[task_id], "combined_reset", float(config["parent_checkpoint"])
        )
        specifications = [(arm, "intact") for arm in PARENT_ARMS]
        specifications.extend(("combined_reset", control) for control in MARK_CONTROLS)
        for future in range(futures):
            for history, control in specifications:
                lineage, cpu = _mark_lineage(
                    backend,
                    memory,
                    calibration,
                    states["naive"],
                    states["trained_no_reset"],
                    states[history],
                    config,
                    int(selected["half_life"]),
                    float(selected["coupling"]),
                    future,
                    control,
                    paired_state=paired_state,
                )
                total_cpu += cpu
                for row in lineage:
                    records.append(
                        {
                            "task_id": f"mark-validation|{task_id}|{history}|{control}|{future}|{row['generation']}",
                            "memory_task_id": task_id,
                            "model_id": int(model_id),
                            "half_life": int(selected["half_life"]),
                            "coupling": float(selected["coupling"]),
                            "history": history,
                            "control": control,
                            "future": future,
                            **row,
                        }
                    )
    payload = {
        "protocol_digest": digest(config),
        "selection_digest": selection_digest,
        "model_id": int(model_id),
        "tasks": list(tasks),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def _all_shard_cpu(output: Path) -> float:
    total = 0.0
    for path in sorted((output / ".shards").rglob("*.json")) if (output / ".shards").is_dir() else []:
        try:
            total += float(json.loads(path.read_text(encoding="utf-8")).get("aggregate_cpu_seconds", 0.0))
        except (OSError, ValueError, TypeError):
            continue
    return total


class RenewalCampaign:
    def __init__(
        self,
        config_path: Path,
        parent: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_renewal_config(self.config_path)
        self.parent = parent.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("renewal workers must lie between one and four")
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed renewal output cannot be resumed")
        self.profile = os.environ.get("RENEWAL_PROFILE", "full")
        if self.profile not in {"full", "lite"}:
            raise ValueError("RENEWAL_PROFILE must be full or lite")
        self.ledger = ResourceLedger(self.output, self.config)

    def state(self, status: str, stage: str, **extra: Any) -> None:
        self.ledger.checkpoint(stage, _all_shard_cpu(self.output))
        write_json(
            self.output / "state.json",
            {
                "status": status,
                "stage": stage,
                "profile": self.profile,
                "workers": self.workers,
                "active_wall_seconds": self.ledger.wall_seconds,
                "aggregate_cpu_seconds": self.ledger.cpu_seconds,
                "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **extra,
            },
        )

    def register(self) -> None:
        validate_upstream(self.upstream, self.config["upstream_commit"])
        verified = verify_checksums(self.parent)
        hashes = {
            "SHA256SUMS": self.config["parent_manifest_sha256"],
            "registration.json": self.config["parent_registration_sha256"],
            "mechanism-labels.jsonl": self.config["parent_mechanisms_sha256"],
            "observer-scores.jsonl": self.config["parent_observers_sha256"],
        }
        for name, expected in hashes.items():
            if sha256_file(self.parent / name) != expected:
                raise ValueError(f"renewal parent hash mismatch: {name}")
        parent_state = json.loads((self.parent / "state.json").read_text(encoding="utf-8"))
        if parent_state.get("status") != "completed":
            raise ValueError("renewal parent is not completed")
        mechanisms = {
            row["memory_task_id"]: row
            for row in read_jsonl(self.parent / "mechanism-labels.jsonl")
        }
        tasks = fixed_tasks(self.config)
        if any(task not in mechanisms or mechanisms[task]["dysfunctional"] for task in tasks):
            raise ValueError("renewal cohort contains a missing or dysfunctional atlas memory")
        generic_count = sum(bool(mechanisms[task]["generic_perturbation_candidate"]) for task in tasks)
        if generic_count != 4:
            raise ValueError("renewal cohort lost its four/four generic balance")
        registration = {
            "experiment_id": self.config["experiment_id"],
            "protocol": self.config,
            "protocol_digest": digest(self.config),
            "profile": self.profile,
            "workers": self.workers,
            "parent": {
                "path": str(self.parent),
                "experiment_id": self.config["parent_experiment_id"],
                "hashes": hashes,
            },
            "upstream": validate_upstream(self.upstream, self.config["upstream_commit"]),
            "runtime": _runtime_manifest(),
            "cohort": [mechanisms[task] for task in tasks],
        }
        path = self.output / "registration.json"
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            for key in ("protocol_digest", "profile", "workers"):
                if existing[key] != registration[key]:
                    raise ValueError(f"renewal resume differs in {key}")
        else:
            write_json(path, registration)
        write_json(
            self.output / "parent-gate.json",
            {
                "pass": True,
                "checksum_count": len(verified),
                "cohort_size": len(tasks),
                "represented_models": sorted(int(value) for value in self.config["fixed_model_pairs"]),
                "generic_count": generic_count,
                "non_generic_count": len(tasks) - generic_count,
            },
        )

    def _model_args(self, worker_extra: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        return [
            (
                str(self.config_path),
                str(self.parent),
                str(self.upstream),
                str(self.output),
                int(model),
                list(tasks),
                *worker_extra,
            )
            for model, tasks in self.config["fixed_model_pairs"].items()
        ]

    def run_native(self) -> list[dict[str, Any]]:
        args = self._model_args((self.profile,))
        shards = _run_model_workers(_native_model_worker, args, self.workers)
        records = _merge_stage(self.output, "native-renewal", shards)
        self.ledger.checkpoint("native-complete", _all_shard_cpu(self.output))
        self.ledger.enforce_hard()
        return records

    def run_carrier(self, decision: Mapping[str, Any]) -> None:
        args = self._model_args((decision["selected_boundary"],))
        shards = _run_model_workers(_carrier_model_worker, args, self.workers)
        _merge_stage(self.output, "carrier-screen", shards)
        recurrence = [row for shard in shards for row in shard["recurrence"]]
        _write_jsonl_atomic(self.output / "native-recurrence.jsonl", recurrence)
        nominations = [row for shard in shards for row in shard["nominations"]]
        write_json(self.output / "carrier-nominations.json", {"nominations": nominations})
        self.ledger.checkpoint("carrier-complete", _all_shard_cpu(self.output))
        self.ledger.enforce_hard()

    def run_mark(self) -> None:
        discovery = {int(value) for value in self.config["mark_discovery_models"]}
        grid_args = [
            arg
            for arg in self._model_args((self.profile,))
            if int(arg[4]) in discovery
        ]
        grid_shards = _run_model_workers(_mark_grid_model_worker, grid_args, min(self.workers, 2))
        grid = _merge_stage(self.output, "mark-grid", grid_shards)
        selection = mark_selection(grid, self.config)
        write_json(self.output / "mark-selection.json", selection)
        self.ledger.checkpoint("mark-grid-complete", _all_shard_cpu(self.output))
        self.ledger.enforce_hard()
        if not selection["pass"]:
            return
        validation = {int(value) for value in self.config["mark_validation_models"]}
        validation_args = [
            (
                str(self.config_path),
                str(self.parent),
                str(self.upstream),
                str(self.output),
                int(model),
                list(tasks),
                selection["selected"],
                self.profile,
            )
            for model, tasks in self.config["fixed_model_pairs"].items()
            if int(model) in validation
        ]
        shards = _run_model_workers(
            _mark_validation_model_worker, validation_args, min(self.workers, 2)
        )
        _merge_stage(self.output, "mark-validation", shards)
        self.ledger.checkpoint("mark-validation-complete", _all_shard_cpu(self.output))
        self.ledger.enforce_hard()

    def run(self) -> int:
        self.ledger.start_heartbeat()
        try:
            self.state("running", "registration")
            self.register()
            self.state("running", "native-renewal")
            native = self.run_native()
            decision = native_branch_decision(native, self.config)
            write_json(self.output / "branch-decision.json", decision)
            self.state("running", f"branch:{decision['branch']}")
            if decision["branch"] == "invalid-stop":
                final_status = "invalid-assay"
            elif not self.ledger.may_start():
                final_status = "time-budget-exhausted"
            else:
                if decision["branch"] == "native-carrier":
                    self.run_carrier(decision)
                else:
                    self.run_mark()
                final_status = "completed"
            from .renewal_analysis import analyze_renewal

            self.state("finalizing", "analysis")
            analyze_renewal(self.output, final_status=final_status)
            self.state(final_status, "complete")
            self.ledger.close()
            write_checksums(self.output)
            return 0 if final_status == "completed" else 124 if "time" in final_status else 2
        except TimeoutError as error:
            from .renewal_analysis import analyze_renewal

            self.state("time-budget-exhausted", "interrupted", error=str(error))
            analyze_renewal(self.output, final_status="time-budget-exhausted")
            self.ledger.close()
            write_checksums(self.output)
            return 124
        except BaseException as error:
            self.state("failed", "exception", error=repr(error))
            self.ledger.close()
            raise


def run_renewal(
    config: Path,
    parent: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return RenewalCampaign(config, parent, upstream, output, workers).run()


def _validate_parent_for_smoke(
    config: Mapping[str, Any], parent: Path, upstream: Path
) -> None:
    validate_upstream(upstream, config["upstream_commit"])
    verify_checksums(parent)
    checks = {
        "SHA256SUMS": config["parent_manifest_sha256"],
        "registration.json": config["parent_registration_sha256"],
        "mechanism-labels.jsonl": config["parent_mechanisms_sha256"],
        "observer-scores.jsonl": config["parent_observers_sha256"],
    }
    for name, expected in checks.items():
        if sha256_file(parent / name) != expected:
            raise ValueError(f"smoke parent hash mismatch: {name}")


def smoke_renewal(
    config_path: Path,
    parent: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_renewal_config(config_path)
    parent = parent.resolve()
    upstream = upstream.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _validate_parent_for_smoke(config, parent, upstream)
    histories, calibrations = _load_parent(parent)
    task_id = "10-1-25"
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, delta_t=float(config["delta_t"]))
    naive = _checkpoint_state(histories, task_id, "naive", float(config["parent_checkpoint"]))
    reset = _checkpoint_state(histories, task_id, "combined_reset", float(config["parent_checkpoint"]))
    midpoint = dilution_y(naive.y, reset.y, 0.5)
    probe = _develop_and_probe(
        backend,
        memory,
        calibrations[task_id],
        State(midpoint, naive.w.copy(), naive.c.copy(), naive.t),
        config,
    )
    identity = bool(
        np.array_equal(dilution_y(naive.y, reset.y, 0.0), naive.y)
        and np.array_equal(dilution_y(naive.y, reset.y, 1.0), reset.y)
        and np.array_equal(
            partition_y(naive.y, reset.y, np.zeros(memory.node_count, dtype=bool)),
            naive.y,
        )
        and np.array_equal(
            partition_y(naive.y, reset.y, np.ones(memory.node_count, dtype=bool)),
            reset.y,
        )
    )
    eval_cpu = max(float(probe["cpu_seconds"]), 0.01)
    full_native = 8 * (5 * 4 + 3 * int(config["partition_futures"]) * 4)
    lite_native = 8 * (5 * 4 + 3 * int(config["lite_partition_futures"]) * 4)
    full_worst = max(full_native + 2340, full_native + 4736)
    lite_worst = max(lite_native + 1320, lite_native + 2368)

    def projection(profile: str, evaluations: int) -> dict[str, Any]:
        raw_cpu = eval_cpu * evaluations
        safe_cpu = raw_cpu * float(config["projection_safety_factor"])
        safe_wall = safe_cpu / int(config["max_workers"])
        return {
            "profile": profile,
            "evaluation_equivalents": evaluations,
            "smoke_evaluation_cpu_seconds": eval_cpu,
            "safe_aggregate_cpu_seconds": safe_cpu,
            "safe_wall_seconds": safe_wall,
            "pass": bool(
                safe_cpu < float(config["soft_aggregate_cpu_seconds"])
                and safe_wall < float(config["soft_wall_seconds"])
            ),
        }

    projections = [projection("full", full_worst), projection("lite", lite_worst)]
    selected = next((row for row in projections if row["pass"]), None)
    result = {
        "target": "latent-memory-renewal",
        "pass": bool(identity and probe["valid"] and selected is not None),
        "production_launch_allowed": bool(identity and probe["valid"] and selected is not None),
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "parent_manifest_sha256": config["parent_manifest_sha256"],
        "cohort_size": len(fixed_tasks(config)),
        "model_count": len(config["fixed_model_pairs"]),
        "max_workers": config["max_workers"],
        "operator_identity_pass": identity,
        "biological_probe": {
            "task_id": task_id,
            "valid": probe["valid"],
            "recall_learned_margin": probe["recall"]["learned_margin"],
            "relearn_learned_margin": probe["relearn"]["learned_margin"],
            "cpu_seconds": probe["cpu_seconds"],
        },
        "projections": projections,
        "selected_profile": None if selected is None else selected["profile"],
    }
    write_json(output / "smoke.json", result)
    return result


def renewal_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {"output": str(output), "exists": output.exists()}
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "branch-decision",
        "mark-selection",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    counts = {}
    for name in (
        "native-renewal",
        "carrier-screen",
        "native-recurrence",
        "mark-grid",
        "mark-validation",
    ):
        path = output / f"{name}.jsonl"
        if path.is_file():
            counts[name] = sum(1 for _ in read_jsonl(path))
    result["record_counts"] = counts
    result["sealed"] = (output / "SHA256SUMS").is_file()
    return result
