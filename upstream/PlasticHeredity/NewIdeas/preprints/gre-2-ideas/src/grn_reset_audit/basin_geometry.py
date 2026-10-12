"""Basin geometry and collective-coordinate audit for durable exposure states."""

from __future__ import annotations

import itertools
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .artifacts import (
    atomic_write_text,
    canonical_json,
    digest,
    read_jsonl,
    write_checksums,
    write_json,
)
from .atlas import state_payload
from .contingency import (
    EXPOSURE_TASKS,
    _all_shard_cpu,
    _calibration_map,
    _fingerprint,
    _parallel,
    _runtime_manifest,
    _seed,
    _verify_parent,
    bipolar_score,
    cosine_alignment,
    vector_rms,
)
from .engine import JaxBackend, State, run_epoch_schedule
from .exposure_autopsy import (
    _fingerprint_from_parent,
    _merge_shards,
    _parent_pair,
    _parent_records,
    _shard,
    _state,
    _state_scale,
    route_epochs,
)
from .renewal import ResourceLedger
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    validate_upstream,
)


RECORD_FILES = (
    "state-transect.jsonl",
    "boundary-specificity.jsonl",
    "local-return.jsonl",
    "hysteresis.jsonl",
)


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(dict(row)) + "\n" for row in records))


def _median(values: Iterable[float]) -> float | None:
    data = [float(value) for value in values if value is not None and np.isfinite(value)]
    return None if not data else float(np.median(np.asarray(data, dtype=float)))


def load_basin_geometry_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported basin-geometry schema")
    if config.get("experiment_kind") != "exposure-basin-geometry":
        raise ValueError("not an exposure-basin-geometry protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("basin geometry does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("basin geometry does not pin the release generator")
    if tuple(config.get("exposure_task_ids", ())) != EXPOSURE_TASKS:
        raise ValueError("basin-geometry task cohort changed")
    parent_seeds = tuple(int(value) for value in config["parent_seed_indices"])
    discovery = tuple(int(value) for value in config["discovery_seed_indices"])
    validation = tuple(int(value) for value in config["validation_seed_indices"])
    if parent_seeds != tuple(range(200, 208)):
        raise ValueError("basin-geometry parent seeds changed")
    if set(discovery) & set(validation) or set(discovery) | set(validation) != set(parent_seeds):
        raise ValueError("basin discovery and validation seeds are not a partition")
    expected = {
        "delta_t": 0.01,
        "phase_duration": 2500.0,
        "epoch_duration": 250.0,
        "epoch_count": 10,
        "pulse_count": 5,
        "washout_total": 12500.0,
        "washout_chunk_duration": 2500.0,
    }
    for key, value in expected.items():
        if not math.isclose(float(config.get(key, -1)), value):
            raise ValueError(f"basin historical setting differs for {key}")
    alphas = [round(float(value), 10) for value in config["transect"]["alphas"]]
    amplitudes = [round(float(value), 10) for value in config["hysteresis"]["amplitudes"]]
    if alphas != [round(index * 0.05, 10) for index in range(21)]:
        raise ValueError("transect grid changed")
    if amplitudes != [round(index * 0.1, 10) for index in range(11)]:
        raise ValueError("hysteresis grid changed")
    if config["hysteresis"]["schedule"] != ["U", "-", "U", "-", "U", "-", "U", "-", "U", "-"]:
        raise ValueError("hysteresis schedule changed")
    if [float(value) for value in config["release_checkpoints"]] != [0.0, 250.0, 2500.0, 12500.0]:
        raise ValueError("release checkpoints changed")
    if int(config["collective_coordinate"]["orthogonal_direction_count"]) != 4:
        raise ValueError("basin geometry requires four orthogonal controls")
    if int(config.get("registered_condition_count", 0)) != 2840:
        raise ValueError("registered basin condition count changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("basin geometry must cap workers at four")
    if not (
        0 < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 14400.0
    ):
        raise ValueError("basin wall-time contract exceeds four hours")
    if not (
        0 < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 57600.0
    ):
        raise ValueError("basin aggregate CPU contract is invalid")
    return config


def validate_basin_parents(
    config: Mapping[str, Any],
    autopsy: Path,
    exposure: Path,
    atlas: Path,
    upstream: Path,
) -> dict[str, Any]:
    provenance = validate_upstream(upstream, str(config["upstream_commit"]))
    gates = {
        "upstream": provenance,
        "autopsy": _verify_parent(
            autopsy,
            str(config["autopsy_parent_experiment_id"]),
            config["autopsy_parent_hashes"],
        ),
        "exposure": _verify_parent(
            exposure,
            str(config["exposure_parent_experiment_id"]),
            config["exposure_parent_hashes"],
        ),
        "atlas": _verify_parent(
            atlas,
            str(config["atlas_parent_experiment_id"]),
            config["atlas_parent_hashes"],
        ),
    }
    autopsy_decision = json.loads((autopsy / "decision.json").read_text(encoding="utf-8"))
    if (
        not autopsy_decision.get("source_valid")
        or int(autopsy_decision.get("stable_separate_task_count", 0)) != len(EXPOSURE_TASKS)
    ):
        raise ValueError("autopsy parent lacks the sealed five-of-five stable-state lead")
    records = _parent_records(exposure)
    expected = len(EXPOSURE_TASKS) * len(config["parent_seed_indices"]) * 2
    if len(records) != expected or not all(bool(row.get("valid")) for row in records.values()):
        raise ValueError("sealed exposure state cohort is incomplete")
    return gates


def interpolate_state(low: State, high: State, alpha: float) -> State:
    if low.w.shape != high.w.shape or not np.array_equal(low.c, high.c):
        raise ValueError("exposure endpoints do not share an unchanged rulebook")
    alpha = float(alpha)
    return State(
        low.y + alpha * (high.y - low.y),
        low.w + alpha * (high.w - low.w),
        low.c.copy(),
        max(float(low.t), float(high.t)),
    )


def orthogonal_directions(axis: Sequence[float], count: int, seed: int) -> np.ndarray:
    primary = np.asarray(axis, dtype=float)
    norm = float(np.linalg.norm(primary))
    if norm <= 1e-12 or not np.isfinite(norm):
        raise ValueError("collective coordinate has zero norm")
    primary = primary / norm
    if count < 1 or count > len(primary) - 1:
        raise ValueError("invalid orthogonal direction count")
    rng = np.random.Generator(np.random.Philox(int(seed)))
    result: list[np.ndarray] = []
    for _ in range(10_000):
        candidate = rng.normal(size=len(primary))
        candidate -= float(np.dot(candidate, primary)) * primary
        for prior in result:
            candidate -= float(np.dot(candidate, prior)) * prior
        candidate_norm = float(np.linalg.norm(candidate))
        if candidate_norm > 1e-10:
            result.append(candidate / candidate_norm)
        if len(result) == int(count):
            return np.asarray(result, dtype=float)
    raise RuntimeError("could not construct deterministic orthogonal controls")


def collective_coordinate_models(
    config: Mapping[str, Any], exposure: Path, upstream: Path
) -> dict[str, Any]:
    parent_map = _parent_records(exposure)
    models: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        released = load_released_task(upstream, str(task_id))
        memory = load_memory(released.memory_path, released.key)
        scale = _state_scale(memory)
        discovery_vectors: list[np.ndarray] = []
        discovery_norms: list[float] = []
        for seed in config["discovery_seed_indices"]:
            low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed))
            delta = (_state(high_row).y - _state(low_row).y) / scale
            delta_norm = float(np.linalg.norm(delta))
            if delta_norm <= 1e-12:
                raise ValueError(f"zero high-low separation for {task_id}/{seed}")
            discovery_vectors.append(delta / delta_norm)
            discovery_norms.append(delta_norm)
        matrix = np.asarray(discovery_vectors, dtype=float)
        _, singular, right = np.linalg.svd(matrix, full_matrices=False)
        axis = np.asarray(right[0], dtype=float)
        if float(np.dot(axis, np.mean(matrix, axis=0))) < 0.0:
            axis = -axis
        energy = float(singular[0] ** 2 / max(float(np.sum(singular**2)), 1e-12))
        controls = orthogonal_directions(
            axis,
            int(config["collective_coordinate"]["orthogonal_direction_count"]),
            _seed(config, "orthogonal-basis", task_id),
        )
        validation_cosines: list[dict[str, Any]] = []
        validation_norms: list[float] = []
        for seed in config["validation_seed_indices"]:
            low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed))
            delta = (_state(high_row).y - _state(low_row).y) / scale
            validation_norms.append(float(np.linalg.norm(delta)))
            validation_cosines.append(
                {
                    "seed_index": int(seed),
                    "cosine": cosine_alignment(axis, delta),
                }
            )
        models.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "axis": axis,
                "orthogonal_directions": controls,
                "energy_fraction": energy,
                "discovery_seed_indices": list(config["discovery_seed_indices"]),
                "discovery_separation_norms": discovery_norms,
                "validation_alignments": validation_cosines,
                "validation_separation_norms": validation_norms,
                "node_count": len(axis),
            }
        )
    return {
        "task_id": "collective-coordinate-models",
        "leakage_allowed": False,
        "models": models,
    }


def _model_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["memory_task_id"]): row for row in payload["models"]}


def perturb_state(
    base: State,
    direction: Sequence[float],
    radius: float,
    scale: np.ndarray,
    bounds: np.ndarray,
    tolerance: float,
) -> State | None:
    unit = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(unit))
    if norm <= 1e-12 or not np.isfinite(norm):
        raise ValueError("perturbation direction has zero norm")
    unit = unit / norm
    candidate = base.y + float(radius) * unit * scale
    if np.any(candidate < bounds[:, 0] - tolerance) or np.any(candidate > bounds[:, 1] + tolerance):
        return None
    return State(candidate, base.w.copy(), base.c.copy(), float(base.t))


def _release_path(
    backend: JaxBackend,
    state: State,
    memory: Any,
    config: Mapping[str, Any],
) -> tuple[State, dict[str, Any], float, float, bool]:
    current = state.copy()
    checkpoints: dict[str, Any] = {
        "0": {
            "state": state_payload(current),
            "response_value": float(current.y[memory.key.response_id]),
            "phase_mean_response": None,
            "valid": True,
        }
    }
    cpu = wall = 0.0
    valid = True
    prior = 0.0
    for total in [float(value) for value in config["release_checkpoints"] if float(value) > 0.0]:
        phase = backend.run_unstimulated(
            current,
            total - prior,
            memory.key.response_id,
            int(config["trajectory_samples"]),
            float(config["washout_chunk_duration"]),
        )
        current = phase.state
        valid = valid and bool(phase.valid)
        cpu += float(phase.cpu_seconds)
        wall += float(phase.wall_seconds)
        checkpoints[f"{total:g}"] = {
            "state": state_payload(current),
            "response_value": float(current.y[memory.key.response_id]),
            "phase_mean_response": float(phase.mean_y[memory.key.response_id]),
            "valid": bool(phase.valid),
        }
        prior = total
    return current, checkpoints, cpu, wall, valid


def _task_context(
    config: Mapping[str, Any], exposure: Path, atlas: Path, upstream: Path, task_id: str
) -> tuple[Any, Any, JaxBackend, int, dict[tuple[str, int, str], dict[str, Any]]]:
    released = load_released_task(upstream, str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
    reconstructed = int(_calibration_map(atlas)[str(task_id)]["reconstructed_ucs_bound_index"])
    return released, memory, backend, reconstructed, _parent_records(exposure)


def _finish_record(
    backend: JaxBackend,
    memory: Any,
    reconstructed: int,
    config: Mapping[str, Any],
    start: State,
    reference_high: np.ndarray,
    reference_low: np.ndarray,
) -> tuple[dict[str, Any], float, float]:
    terminal, checkpoints, cpu, wall, release_valid = _release_path(
        backend, start, memory, config
    )
    fp = _fingerprint(backend, memory, terminal, config, reconstructed)
    score = bipolar_score(fp["fingerprint"], reference_high, reference_low)
    return (
        {
            "source_state": state_payload(start),
            "terminal_state": state_payload(terminal),
            "checkpoints": checkpoints,
            "resting_response": float(terminal.y[memory.key.response_id]),
            "fingerprint": fp["fingerprint"],
            "raw_fingerprint": fp["raw_fingerprint"],
            "bipolar_score": score,
            "valid": bool(release_valid and fp["valid"] and score is not None),
        },
        float(cpu + fp["cpu_seconds"]),
        float(wall + fp["wall_seconds"]),
    )


def _transect_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_basin_geometry_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "state-transect", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    low, high = _state(low_row), _state(high_row)
    scale = _state_scale(memory)
    reference_low, reference_high = _fingerprint_from_parent(low_row), _fingerprint_from_parent(high_row)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for alpha in config["transect"]["alphas"]:
        start = interpolate_state(low, high, float(alpha))
        result, used_cpu, used_wall = _finish_record(
            backend, memory, reconstructed, config, start, reference_high, reference_low
        )
        cpu += used_cpu
        wall += used_wall
        source_distance = None
        if float(alpha) in {0.0, 1.0}:
            expected = low if float(alpha) == 0.0 else high
            source_distance = float(np.linalg.norm((start.y - expected.y) / scale))
        records.append(
            {
                "task_id": f"transect|{task_id}|{seed_index}|{float(alpha):.2f}",
                "condition_id": f"transect|alpha={float(alpha):.2f}",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "seed_role": "discovery" if int(seed_index) in config["discovery_seed_indices"] else "validation",
                "alpha": float(alpha),
                "source_endpoint_distance": source_distance,
                **result,
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "state-transect",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def crossing_summary(rows: Sequence[Mapping[str, Any]], tolerance: float) -> dict[str, Any]:
    ordered = sorted(
        [row for row in rows if row.get("valid") and row.get("bipolar_score") is not None],
        key=lambda row: float(row["alpha"]),
    )
    locations: list[float] = []
    for left, right in zip(ordered, ordered[1:]):
        a0, a1 = float(left["alpha"]), float(right["alpha"])
        s0, s1 = float(left["bipolar_score"]), float(right["bipolar_score"])
        if s0 == 0.0:
            locations.append(a0)
        if s0 * s1 < 0.0 or s1 == 0.0:
            location = a1 if s1 == 0.0 else a0 + (-s0) * (a1 - a0) / (s1 - s0)
            locations.append(float(location))
    unique: list[float] = []
    for value in locations:
        if not unique or abs(value - unique[-1]) > 1e-9:
            unique.append(value)
    scores = [float(row["bipolar_score"]) for row in ordered]
    monotonic = len(scores) >= 2 and all(
        scores[index + 1] >= scores[index] - float(tolerance)
        for index in range(len(scores) - 1)
    )
    return {
        "valid_point_count": len(ordered),
        "crossing_count": len(unique),
        "crossing_locations": unique,
        "monotonic": bool(monotonic),
    }


def boundary_models(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        seed_rows: list[dict[str, Any]] = []
        accepted: list[float] = []
        for seed in config["discovery_seed_indices"]:
            summary = crossing_summary(
                [
                    row
                    for row in records
                    if row["memory_task_id"] == task_id and int(row["seed_index"]) == int(seed)
                ],
                float(config["transect"]["monotonic_tolerance"]),
            )
            if summary["monotonic"] and int(summary["crossing_count"]) == 1:
                accepted.append(float(summary["crossing_locations"][0]))
            seed_rows.append({"seed_index": int(seed), **summary})
        eligible = len(accepted) >= int(config["transect"]["minimum_discovery_crossing_seeds"])
        models.append(
            {
                "memory_task_id": str(task_id),
                "boundary_alpha": _median(accepted) if eligible else None,
                "eligible": bool(eligible),
                "accepted_seed_count": len(accepted),
                "per_discovery_seed": seed_rows,
            }
        )
    return {"task_id": "boundary-models", "leakage_allowed": False, "models": models}


def _unavailable_perturbation_record(
    task_id: str,
    seed_index: int,
    condition_id: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "task_id": f"invalid|{task_id}|{seed_index}|{condition_id}",
        "condition_id": condition_id,
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "bound_constrained": True,
        "valid": False,
        "fingerprint": None,
        "bipolar_score": None,
        "resting_response": None,
        **fields,
    }


def _boundary_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_basin_geometry_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "boundary-specificity", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    low, high = _state(low_row), _state(high_row)
    scale = _state_scale(memory)
    separation = float(np.linalg.norm((high.y - low.y) / scale))
    coordinate = _model_map(output / "collective-coordinate-models.json")[str(task_id)]
    boundary = _model_map(output / "boundary-models.json")[str(task_id)]
    directions = [("collective", -1, np.asarray(coordinate["axis"], dtype=float))]
    directions.extend(
        ("orthogonal", index, np.asarray(value, dtype=float))
        for index, value in enumerate(coordinate["orthogonal_directions"])
    )
    reference_low, reference_high = _fingerprint_from_parent(low_row), _fingerprint_from_parent(high_row)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for radius_fraction in config["collective_coordinate"]["boundary_radius_fractions_of_separation"]:
        for kind, index, direction in directions:
            for sign in (-1, 1):
                condition_id = f"boundary|{kind}|{index}|sign={sign}|r={float(radius_fraction):.3f}"
                common = {
                    "model_id": int(memory.key.model_id),
                    "direction_kind": kind,
                    "direction_index": int(index),
                    "sign": int(sign),
                    "radius_fraction": float(radius_fraction),
                    "radius": float(radius_fraction) * separation,
                    "boundary_alpha": boundary.get("boundary_alpha"),
                }
                if not boundary.get("eligible") or boundary.get("boundary_alpha") is None:
                    records.append(
                        _unavailable_perturbation_record(
                            str(task_id), int(seed_index), condition_id,
                            reason="discovery-boundary-unavailable", **common
                        )
                    )
                    continue
                base = interpolate_state(low, high, float(boundary["boundary_alpha"]))
                start = perturb_state(
                    base,
                    float(sign) * direction,
                    float(radius_fraction) * separation,
                    scale,
                    np.asarray(memory.bounds, dtype=float),
                    float(config["collective_coordinate"]["box_tolerance"]),
                )
                if start is None:
                    records.append(
                        _unavailable_perturbation_record(
                            str(task_id), int(seed_index), condition_id,
                            reason="bound-constrained", **common
                        )
                    )
                    continue
                result, used_cpu, used_wall = _finish_record(
                    backend, memory, reconstructed, config, start, reference_high, reference_low
                )
                cpu += used_cpu
                wall += used_wall
                records.append(
                    {
                        "task_id": f"boundary|{task_id}|{seed_index}|{kind}|{index}|{sign}|{float(radius_fraction):.3f}",
                        "condition_id": condition_id,
                        "memory_task_id": str(task_id),
                        "seed_index": int(seed_index),
                        "bound_constrained": False,
                        **common,
                        **result,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "boundary-specificity",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _local_return_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_basin_geometry_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "local-return", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    low, high = _state(low_row), _state(high_row)
    scale = _state_scale(memory)
    separation = float(np.linalg.norm((high.y - low.y) / scale))
    coordinate = _model_map(output / "collective-coordinate-models.json")[str(task_id)]
    controls = [np.asarray(value, dtype=float) for value in coordinate["orthogonal_directions"]]
    reference_low, reference_high = _fingerprint_from_parent(low_row), _fingerprint_from_parent(high_row)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm, base, source_fp in (("low", low, reference_low), ("high", high, reference_high)):
        for radius_fraction in config["collective_coordinate"]["local_return_radius_fractions_of_separation"]:
            for index, direction in enumerate(controls):
                for sign in (-1, 1):
                    condition_id = f"return|{arm}|orthogonal|{index}|sign={sign}|r={float(radius_fraction):.3f}"
                    common = {
                        "model_id": int(memory.key.model_id),
                        "arm": arm,
                        "direction_index": int(index),
                        "sign": int(sign),
                        "radius_fraction": float(radius_fraction),
                        "radius": float(radius_fraction) * separation,
                    }
                    start = perturb_state(
                        base,
                        float(sign) * direction,
                        float(radius_fraction) * separation,
                        scale,
                        np.asarray(memory.bounds, dtype=float),
                        float(config["collective_coordinate"]["box_tolerance"]),
                    )
                    if start is None:
                        records.append(
                            _unavailable_perturbation_record(
                                str(task_id), int(seed_index), condition_id,
                                reason="bound-constrained", **common
                            )
                        )
                        continue
                    result, used_cpu, used_wall = _finish_record(
                        backend, memory, reconstructed, config, start, reference_high, reference_low
                    )
                    cpu += used_cpu
                    wall += used_wall
                    fp_distance = (
                        None
                        if result["fingerprint"] is None
                        else vector_rms(np.asarray(result["fingerprint"], dtype=float) - source_fp)
                    )
                    returned = bool(
                        result["valid"]
                        and fp_distance is not None
                        and fp_distance <= float(config["local_return"]["fingerprint_rms_max"])
                        and (
                            (arm == "high" and float(result["bipolar_score"]) > 0.0)
                            or (arm == "low" and float(result["bipolar_score"]) < 0.0)
                        )
                    )
                    records.append(
                        {
                            "task_id": f"return|{task_id}|{seed_index}|{arm}|{index}|{sign}|{float(radius_fraction):.3f}",
                            "condition_id": condition_id,
                            "memory_task_id": str(task_id),
                            "seed_index": int(seed_index),
                            "bound_constrained": False,
                            "source_fingerprint_distance": fp_distance,
                            "returned": returned,
                            **common,
                            **result,
                        }
                    )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "local-return",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _hysteresis_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_basin_geometry_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "hysteresis", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    reference_low, reference_high = _fingerprint_from_parent(low_row), _fingerprint_from_parent(high_row)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for start_arm, start in (("low", _state(low_row)), ("high", _state(high_row))):
        for amplitude in config["hysteresis"]["amplitudes"]:
            spec = [float(amplitude) if token == "U" else None for token in config["hysteresis"]["schedule"]]
            training = run_epoch_schedule(
                backend,
                start.copy(),
                route_epochs(memory, spec),
                float(config["epoch_duration"]),
                memory.key.response_id,
                int(config["trajectory_samples"]),
            )
            result, used_cpu, used_wall = _finish_record(
                backend, memory, reconstructed, config, training.state, reference_high, reference_low
            )
            cpu += float(training.cpu_seconds) + used_cpu
            wall += float(training.wall_seconds) + used_wall
            result["valid"] = bool(result["valid"] and training.valid)
            records.append(
                {
                    "task_id": f"hysteresis|{task_id}|{seed_index}|{start_arm}|{float(amplitude):.1f}",
                    "condition_id": f"hysteresis|start={start_arm}|amplitude={float(amplitude):.1f}",
                    "memory_task_id": str(task_id),
                    "model_id": int(memory.key.model_id),
                    "seed_index": int(seed_index),
                    "start_arm": start_arm,
                    "amplitude": float(amplitude),
                    "route_spec": spec,
                    "training_state": state_payload(training.state),
                    **result,
                }
            )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "hysteresis",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def transect_decision(
    records: Sequence[Mapping[str, Any]],
    boundaries: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    boundary_map = {str(row["memory_task_id"]): row for row in boundaries["models"]}
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        validation: list[dict[str, Any]] = []
        for seed in config["validation_seed_indices"]:
            summary = crossing_summary(
                [
                    row
                    for row in records
                    if row["memory_task_id"] == task_id and int(row["seed_index"]) == int(seed)
                ],
                float(config["transect"]["monotonic_tolerance"]),
            )
            validation.append({"seed_index": int(seed), **summary})
        source_rows = [
            row
            for row in records
            if row["memory_task_id"] == task_id and float(row["alpha"]) in {0.0, 1.0}
        ]
        source_pass = len(source_rows) == 2 * len(config["parent_seed_indices"]) and all(
            float(row.get("source_endpoint_distance") or 0.0) <= 1e-10 for row in source_rows
        )
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "source_pass": bool(source_pass),
                "discovery_boundary": boundary_map[str(task_id)],
                "validation_single_monotonic_crossing_count": sum(
                    bool(row["monotonic"] and int(row["crossing_count"]) == 1)
                    for row in validation
                ),
                "validation": validation,
            }
        )
    source_valid = all(bool(row["source_pass"]) for row in summaries)
    return {
        "task_id": "transect-decision",
        "source_reproduction_pass": source_valid,
        "candidate_summaries": summaries,
        "verdict": "source-valid-basin-transects" if source_valid else "source-reproduction-failed",
    }


def coordinate_decision(
    records: Sequence[Mapping[str, Any]],
    coordinates: Mapping[str, Any],
    boundaries: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    coordinate_map = {str(row["memory_task_id"]): row for row in coordinates["models"]}
    boundary_map = {str(row["memory_task_id"]): row for row in boundaries["models"]}
    settings = config["collective_coordinate"]
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        model = coordinate_map[str(task_id)]
        boundary = boundary_map[str(task_id)]
        validation_cosine = _median(
            row["cosine"]
            for row in model["validation_alignments"]
            if row.get("cosine") is not None
        )
        radius_rows: list[dict[str, Any]] = []
        for radius in settings["boundary_radius_fractions_of_separation"]:
            per_seed: list[dict[str, Any]] = []
            all_orthogonal: list[float] = []
            for seed in config["validation_seed_indices"]:
                seed_rows = [
                    row
                    for row in records
                    if row["memory_task_id"] == task_id
                    and int(row["seed_index"]) == int(seed)
                    and math.isclose(float(row["radius_fraction"]), float(radius))
                    and row.get("valid")
                ]
                collective = {
                    int(row["sign"]): row
                    for row in seed_rows
                    if row["direction_kind"] == "collective"
                }
                axis_separation = None
                correct_sign = False
                if set(collective) == {-1, 1}:
                    minus = float(collective[-1]["bipolar_score"])
                    plus = float(collective[1]["bipolar_score"])
                    axis_separation = plus - minus
                    correct_sign = minus < 0.0 < plus
                orthogonal_pairs: list[float] = []
                for index in range(int(settings["orthogonal_direction_count"])):
                    pair = {
                        int(row["sign"]): row
                        for row in seed_rows
                        if row["direction_kind"] == "orthogonal"
                        and int(row["direction_index"]) == index
                    }
                    if set(pair) == {-1, 1}:
                        orthogonal_pairs.append(
                            abs(float(pair[1]["bipolar_score"]) - float(pair[-1]["bipolar_score"]))
                        )
                orthogonal_median = _median(orthogonal_pairs)
                all_orthogonal.extend(orthogonal_pairs)
                consistent = bool(
                    axis_separation is not None
                    and axis_separation >= float(settings["axis_separation_min"])
                    and correct_sign
                    and orthogonal_median is not None
                    and orthogonal_median <= float(settings["orthogonal_pair_separation_max"])
                )
                per_seed.append(
                    {
                        "seed_index": int(seed),
                        "axis_separation": axis_separation,
                        "correct_sign": correct_sign,
                        "valid_orthogonal_pair_count": len(orthogonal_pairs),
                        "median_orthogonal_pair_separation": orthogonal_median,
                        "consistent": consistent,
                    }
                )
            median_axis = _median(
                row["axis_separation"] for row in per_seed if row["axis_separation"] is not None
            )
            median_orthogonal = _median(all_orthogonal)
            consistent_count = sum(bool(row["consistent"]) for row in per_seed)
            radius_pass = bool(
                median_axis is not None
                and median_axis >= float(settings["axis_separation_min"])
                and median_orthogonal is not None
                and median_orthogonal <= float(settings["orthogonal_pair_separation_max"])
                and consistent_count >= int(settings["minimum_consistent_validation_seeds"])
            )
            radius_rows.append(
                {
                    "radius_fraction": float(radius),
                    "median_axis_separation": median_axis,
                    "median_orthogonal_pair_separation": median_orthogonal,
                    "consistent_seed_count": consistent_count,
                    "pass": radius_pass,
                    "per_seed": per_seed,
                }
            )
        geometry_pass = any(bool(row["pass"]) for row in radius_rows)
        direction_gate = bool(
            float(model["energy_fraction"]) >= float(settings["energy_fraction_min"])
            and validation_cosine is not None
            and validation_cosine >= float(settings["validation_cosine_min"])
            and boundary.get("eligible")
        )
        passed = bool(direction_gate and geometry_pass)
        generic = any(
            row["median_axis_separation"] is not None
            and row["median_axis_separation"] >= float(settings["axis_separation_min"])
            and row["median_orthogonal_pair_separation"] is not None
            and row["median_orthogonal_pair_separation"] > float(settings["orthogonal_pair_separation_max"])
            for row in radius_rows
        )
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "energy_fraction": float(model["energy_fraction"]),
                "median_validation_cosine": validation_cosine,
                "boundary_eligible": bool(boundary.get("eligible")),
                "direction_gate": direction_gate,
                "radius_summaries": radius_rows,
                "generic_threshold_sensitive": bool(generic),
                "pass": passed,
            }
        )
    pass_count = sum(bool(row["pass"]) for row in summaries)
    generic_count = sum(bool(row["generic_threshold_sensitive"]) for row in summaries)
    return {
        "task_id": "coordinate-decision",
        "candidate_summaries": summaries,
        "pass_count": pass_count,
        "generic_threshold_sensitive_count": generic_count,
        "pass": pass_count > 0,
        "verdict": "shared-collective-coordinate-leads" if pass_count else "no-specific-collective-coordinate-lead",
    }


def local_return_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["local_return"]
    radius = float(settings["decision_radius_fraction"])
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        per_seed: list[dict[str, Any]] = []
        for seed in config["validation_seed_indices"]:
            arms: dict[str, Any] = {}
            for arm in ("low", "high"):
                rows = [
                    row
                    for row in records
                    if row["memory_task_id"] == task_id
                    and int(row["seed_index"]) == int(seed)
                    and row.get("arm") == arm
                    and math.isclose(float(row["radius_fraction"]), radius)
                    and row.get("valid")
                ]
                recovered = sum(bool(row.get("returned")) for row in rows)
                fraction = None if not rows else recovered / len(rows)
                arms[arm] = {
                    "valid_control_count": len(rows),
                    "recovered_count": recovered,
                    "recovery_fraction": fraction,
                    "pass": bool(
                        len(rows) >= int(settings["minimum_valid_controls_per_arm"])
                        and fraction is not None
                        and fraction >= float(settings["minimum_recovery_fraction"])
                    ),
                }
            per_seed.append(
                {
                    "seed_index": int(seed),
                    "arms": arms,
                    "consistent": bool(arms["low"]["pass"] and arms["high"]["pass"]),
                }
            )
        consistent = sum(bool(row["consistent"]) for row in per_seed)
        passed = consistent >= int(settings["minimum_consistent_validation_seeds"])
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "decision_radius_fraction": radius,
                "consistent_seed_count": consistent,
                "pass": bool(passed),
                "per_seed": per_seed,
            }
        )
    pass_count = sum(bool(row["pass"]) for row in summaries)
    return {
        "task_id": "local-return-decision",
        "candidate_summaries": summaries,
        "pass_count": pass_count,
        "pass": pass_count > 0,
        "verdict": "attractor-basin-compatible-leads" if pass_count else "no-local-return-basin-lead",
    }


def hysteresis_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["hysteresis"]
    amplitudes = [float(value) for value in settings["amplitudes"]]
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        amplitude_rows: list[dict[str, Any]] = []
        qualifying: list[bool] = []
        for amplitude in amplitudes:
            per_seed: list[dict[str, Any]] = []
            for seed in config["validation_seed_indices"]:
                arms = {
                    str(row["start_arm"]): row
                    for row in records
                    if row["memory_task_id"] == task_id
                    and int(row["seed_index"]) == int(seed)
                    and math.isclose(float(row["amplitude"]), amplitude)
                    and row.get("valid")
                }
                difference = None
                consistent = False
                if set(arms) == {"low", "high"}:
                    difference = float(arms["high"]["bipolar_score"]) - float(
                        arms["low"]["bipolar_score"]
                    )
                    consistent = difference >= float(settings["endpoint_difference_min"])
                per_seed.append(
                    {
                        "seed_index": int(seed),
                        "endpoint_difference": difference,
                        "consistent": consistent,
                    }
                )
            consistent_count = sum(bool(row["consistent"]) for row in per_seed)
            median_difference = _median(
                row["endpoint_difference"] for row in per_seed if row["endpoint_difference"] is not None
            )
            passed = bool(
                consistent_count >= int(settings["minimum_consistent_validation_seeds"])
                and median_difference is not None
                and median_difference >= float(settings["endpoint_difference_min"])
            )
            qualifying.append(passed)
            amplitude_rows.append(
                {
                    "amplitude": amplitude,
                    "median_endpoint_difference": median_difference,
                    "consistent_seed_count": consistent_count,
                    "qualifies": passed,
                    "per_seed": per_seed,
                }
            )
        adjacent = [
            [amplitudes[index], amplitudes[index + 1]]
            for index in range(len(amplitudes) - 1)
            if qualifying[index] and qualifying[index + 1]
        ]
        passed = bool(adjacent)
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "qualifying_amplitude_count": sum(qualifying),
                "adjacent_qualifying_windows": adjacent,
                "pass": passed,
                "amplitudes": amplitude_rows,
            }
        )
    pass_count = sum(bool(row["pass"]) for row in summaries)
    return {
        "task_id": "hysteresis-decision",
        "candidate_summaries": summaries,
        "pass_count": pass_count,
        "pass": pass_count > 0,
        "verdict": "hysteretic-multistability-leads" if pass_count else "no-hysteresis-window-lead",
    }


def observer_decision(
    record_groups: Sequence[Sequence[Mapping[str, Any]]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["observer"]
    records = [
        row
        for group in record_groups
        for row in group
        if row.get("valid")
        and row.get("fingerprint") is not None
        and int(row.get("seed_index", -1)) in config["validation_seed_indices"]
    ]
    summaries: list[dict[str, Any]] = []
    all_pairs: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        task_rows = [row for row in records if row["memory_task_id"] == task_id]
        names = sorted({str(row["condition_id"]) for row in task_rows})
        pairs: list[dict[str, Any]] = []
        for left_name, right_name in itertools.combinations(names, 2):
            differences: list[tuple[float, float]] = []
            for seed in config["validation_seed_indices"]:
                by_name = {
                    str(row["condition_id"]): row
                    for row in task_rows
                    if int(row["seed_index"]) == int(seed)
                    and str(row["condition_id"]) in {left_name, right_name}
                }
                if set(by_name) != {left_name, right_name}:
                    continue
                left = np.asarray(by_name[left_name]["fingerprint"], dtype=float)
                right = np.asarray(by_name[right_name]["fingerprint"], dtype=float)
                differences.append((abs(float(left[0] - right[0])), vector_rms(left[1:] - right[1:])))
            resting = _median(value[0] for value in differences)
            counterfactual = _median(value[1] for value in differences)
            if (
                len(differences) >= int(settings["minimum_consistent_validation_seeds"])
                and resting is not None
                and resting <= float(settings["coarse_match_max"])
                and counterfactual is not None
                and counterfactual >= float(settings["counterfactual_divergence_min"])
            ):
                pairs.append(
                    {
                        "memory_task_id": str(task_id),
                        "left_condition": left_name,
                        "right_condition": right_name,
                        "valid_seed_count": len(differences),
                        "median_no_input_difference": resting,
                        "median_counterfactual_rms": counterfactual,
                    }
                )
        pairs.sort(
            key=lambda row: (
                -float(row["median_counterfactual_rms"]),
                row["left_condition"],
                row["right_condition"],
            )
        )
        reported = pairs[: int(settings["maximum_reported_pairs_per_task"])]
        all_pairs.extend(reported)
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "qualifying_pair_count": len(pairs),
                "reported_pairs": reported,
            }
        )
    return {
        "task_id": "observer-decision",
        "candidate_summaries": summaries,
        "qualifying_pair_count": sum(int(row["qualifying_pair_count"]) for row in summaries),
        "reported_pairs": all_pairs,
        "pass": any(int(row["qualifying_pair_count"]) > 0 for row in summaries),
        "verdict": "coarse-matched-counterfactual-leads" if all_pairs else "no-coarse-matched-counterfactual-lead",
    }


def analyze_basin_geometry(output: Path, final_status: str | None = None) -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    coordinates = json.loads((output / "collective-coordinate-models.json").read_text(encoding="utf-8"))
    boundaries = json.loads((output / "boundary-models.json").read_text(encoding="utf-8"))
    transect = list(read_jsonl(output / "state-transect.jsonl"))
    boundary = list(read_jsonl(output / "boundary-specificity.jsonl"))
    local_return = list(read_jsonl(output / "local-return.jsonl"))
    hysteresis = list(read_jsonl(output / "hysteresis.jsonl"))
    transect_result = transect_decision(transect, boundaries, config)
    coordinate_result = coordinate_decision(boundary, coordinates, boundaries, config)
    return_result = local_return_decision(local_return, config)
    hysteresis_result = hysteresis_decision(hysteresis, config)
    observer_result = observer_decision(
        [transect, boundary, local_return, hysteresis], config
    )
    for name, value in (
        ("transect-decision", transect_result),
        ("coordinate-decision", coordinate_result),
        ("local-return-decision", return_result),
        ("hysteresis-decision", hysteresis_result),
        ("observer-decision", observer_result),
    ):
        write_json(output / f"{name}.json", value)
    source_valid = bool(transect_result["source_reproduction_pass"])
    if not source_valid:
        verdict = "source-reproduction-failed"
    elif coordinate_result["pass"] and return_result["pass"] and hysteresis_result["pass"]:
        verdict = "shared-coordinate-hysteretic-basin-lead"
    elif return_result["pass"] and hysteresis_result["pass"]:
        verdict = "distributed-hysteretic-basin-lead"
    elif return_result["pass"]:
        verdict = "local-attractor-basin-compatible"
    elif coordinate_result["generic_threshold_sensitive_count"]:
        verdict = "generic-threshold-sensitive-manifold"
    else:
        verdict = "persistent-states-without-basin-support"
    decision = {
        "task_id": "basin-geometry-decision",
        "pass": bool(
            source_valid
            and (
                coordinate_result["pass"]
                or return_result["pass"]
                or hysteresis_result["pass"]
                or observer_result["pass"]
            )
        ),
        "source_valid": source_valid,
        "verdict": verdict,
        "shared_coordinate_task_count": int(coordinate_result["pass_count"]),
        "attractor_compatible_task_count": int(return_result["pass_count"]),
        "hysteretic_task_count": int(hysteresis_result["pass_count"]),
        "generic_threshold_sensitive_task_count": int(
            coordinate_result["generic_threshold_sensitive_count"]
        ),
        "coarse_matched_counterfactual_pair_count": int(
            observer_result["qualifying_pair_count"]
        ),
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "decision.json", decision)
    ledger = (
        json.loads((output / "resource-ledger.json").read_text(encoding="utf-8"))
        if (output / "resource-ledger.json").is_file()
        else {}
    )
    counts = {
        name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES
    }
    analysis = {
        "task_id": "basin-geometry-analysis",
        "experiment_id": config["experiment_id"],
        "run_status": final_status or "analyzed",
        "decision_pass": bool(decision["pass"]),
        "verdict": verdict,
        "record_counts": counts,
        "active_wall_seconds": float(ledger.get("active_wall_seconds", 0.0)),
        "aggregate_cpu_seconds": float(ledger.get("aggregate_cpu_seconds", 0.0)),
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    report = f"""# GRN exposure-basin geometry V1

Status: **{analysis['run_status']}**

Verdict: **{verdict}**

- Source-valid: **{source_valid}**.
- Shared collective-coordinate leads: **{decision['shared_coordinate_task_count']} / {len(config['exposure_task_ids'])}**.
- Local attractor-compatible leads: **{decision['attractor_compatible_task_count']} / {len(config['exposure_task_ids'])}**.
- Hysteretic multistability leads: **{decision['hysteretic_task_count']} / {len(config['exposure_task_ids'])}**.
- Generic threshold-sensitive tasks: **{decision['generic_threshold_sensitive_task_count']} / {len(config['exposure_task_ids'])}**.
- Coarse-matched counterfactual pairs: **{decision['coarse_matched_counterfactual_pair_count']}**.

Records: {counts}

Resource use: {analysis['active_wall_seconds']:.3f} active wall seconds and
{analysis['aggregate_cpu_seconds']:.3f} aggregate worker CPU seconds.

Claim boundary: {config['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class BasinGeometryCampaign:
    def __init__(
        self,
        config_path: Path,
        autopsy: Path,
        exposure: Path,
        atlas: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_basin_geometry_config(self.config_path)
        self.autopsy = autopsy.resolve()
        self.exposure = exposure.resolve()
        self.atlas = atlas.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("basin-geometry workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed basin-geometry campaign cannot be resumed")
        self.parent_gate = validate_basin_parents(
            self.config, self.autopsy, self.exposure, self.atlas, self.upstream
        )
        self.output.mkdir(parents=True, exist_ok=True)
        self.ledger = ResourceLedger(self.output, self.config)

    def _state(self, status: str, stage: str, **extra: Any) -> None:
        write_json(
            self.output / "state.json",
            {
                "status": status,
                "stage": stage,
                "workers": self.workers,
                "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **extra,
            },
        )
        self.ledger.checkpoint(stage, _all_shard_cpu(self.output))
        self.ledger.enforce_hard()

    def _register(self) -> None:
        payload = {
            "experiment_id": self.config["experiment_id"],
            "protocol": self.config,
            "protocol_digest": digest(self.config),
            "workers": self.workers,
            "parents": self.parent_gate,
            "runtime": _runtime_manifest(),
            "record_files": list(RECORD_FILES),
        }
        path = self.output / "registration.json"
        if path.is_file():
            prior = json.loads(path.read_text(encoding="utf-8"))
            for key in ("experiment_id", "protocol_digest", "parents"):
                if prior.get(key) != payload.get(key):
                    raise ValueError(f"resumed basin registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"]["container_image_id"]:
                raise ValueError("resumed basin image differs")
        write_json(path, payload)
        write_json(
            self.output / "parent-gate.json",
            {"task_id": "parent-gate", "pass": True, **self.parent_gate},
        )
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "local_return": "Modest matched perturbations return to the source exposure basin.",
                "collective_coordinate": "A held-out low-dimensional expression direction specifically selects destination.",
                "hysteresis": "Identical forcing retains dependence on the prior exposure state.",
                "observer": "Rest-matched states can retain different counterfactual responses.",
                "negative_is_informative": True,
                "threshold_relaxation_allowed": False,
            },
        )
        if not (self.output / "runtime-incidents.json").is_file():
            write_json(self.output / "runtime-incidents.json", {"incidents": []})
        for name in RECORD_FILES:
            if not (self.output / name).is_file():
                _write_jsonl(self.output / name, [])

    def run(self) -> int:
        self._register()
        self.ledger.start_heartbeat()
        try:
            self._state("running", "collective-coordinate-discovery")
            coordinates = collective_coordinate_models(
                self.config, self.exposure, self.upstream
            )
            write_json(self.output / "collective-coordinate-models.json", coordinates)
            common_args = [
                (
                    str(self.config_path),
                    str(self.exposure),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed),
                )
                for task_id in self.config["exposure_task_ids"]
                for seed in self.config["parent_seed_indices"]
            ]
            self._state("running", "state-transect")
            transect_shards = _parallel(_transect_worker, common_args, self.workers)
            transect_records = _merge_shards(self.output, "state-transect", transect_shards)
            self._state("running", "boundary-discovery")
            boundaries = boundary_models(transect_records, self.config)
            write_json(self.output / "boundary-models.json", boundaries)
            validation_args = [
                (
                    str(self.config_path),
                    str(self.exposure),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed),
                )
                for task_id in self.config["exposure_task_ids"]
                for seed in self.config["validation_seed_indices"]
            ]
            self._state("running", "boundary-specificity")
            boundary_shards = _parallel(_boundary_worker, validation_args, self.workers)
            _merge_shards(self.output, "boundary-specificity", boundary_shards)
            self._state("running", "local-return")
            return_shards = _parallel(_local_return_worker, validation_args, self.workers)
            _merge_shards(self.output, "local-return", return_shards)
            self._state("running", "hysteresis")
            hysteresis_shards = _parallel(_hysteresis_worker, validation_args, self.workers)
            _merge_shards(self.output, "hysteresis", hysteresis_shards)
            self._state("analyzing", "analysis")
            self.ledger.close()
            analyze_basin_geometry(self.output, final_status="completed")
            decision = json.loads((self.output / "decision.json").read_text(encoding="utf-8"))
            self._state("completed", "complete", verdict=decision["verdict"])
            write_checksums(self.output)
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
            self.ledger.close()
            write_json(
                self.output / "state.json",
                {
                    "status": "failed",
                    "stage": "exception",
                    "error": repr(error),
                    "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
            raise


def run_basin_geometry(
    config: Path,
    autopsy: Path,
    exposure: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return BasinGeometryCampaign(
        config, autopsy, exposure, atlas, upstream, output, workers
    ).run()


def _slowest_parent_task(autopsy: Path, allowed: Sequence[str]) -> str:
    best_task = str(allowed[0])
    best_cpu = -1.0
    root = autopsy / ".shards"
    for path in sorted(root.rglob("*.json")) if root.is_dir() else ():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            task_id = str(payload.get("memory_task_id", ""))
            cpu = float(payload.get("aggregate_cpu_seconds", 0.0))
        except (OSError, TypeError, ValueError):
            continue
        if task_id in allowed and cpu > best_cpu:
            best_task, best_cpu = task_id, cpu
    return best_task


def smoke_basin_geometry(
    config_path: Path,
    autopsy: Path,
    exposure: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_basin_geometry_config(config_path)
    autopsy, exposure, atlas, upstream = (
        autopsy.resolve(),
        exposure.resolve(),
        atlas.resolve(),
        upstream.resolve(),
    )
    parents = validate_basin_parents(config, autopsy, exposure, atlas, upstream)
    coordinates = collective_coordinate_models(config, exposure, upstream)
    coordinate_map = {str(row["memory_task_id"]): row for row in coordinates["models"]}
    task_id = _slowest_parent_task(autopsy, config["exposure_task_ids"])
    seed_index = int(config["validation_seed_indices"][0])
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, exposure, atlas, upstream, task_id
    )
    low_row, high_row = _parent_pair(parent_map, task_id, seed_index)
    low, high = _state(low_row), _state(high_row)
    scale = _state_scale(memory)
    reference_low, reference_high = _fingerprint_from_parent(low_row), _fingerprint_from_parent(high_row)
    source_fp = _fingerprint(backend, memory, low.copy(), config, reconstructed)
    source_fp_distance = vector_rms(
        np.asarray(source_fp["fingerprint"], dtype=float) - reference_low
    )
    source_state_distance = float(np.linalg.norm((interpolate_state(low, high, 0.0).y - low.y) / scale))

    transect_result, transect_cpu, transect_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        interpolate_state(low, high, 0.5),
        reference_high,
        reference_low,
    )
    separation = float(np.linalg.norm((high.y - low.y) / scale))
    axis = np.asarray(coordinate_map[task_id]["axis"], dtype=float)
    perturbed = None
    chosen_sign = None
    for sign in (-1, 1):
        candidate = perturb_state(
            interpolate_state(low, high, 0.5),
            float(sign) * axis,
            float(config["collective_coordinate"]["boundary_radius_fractions_of_separation"][0]) * separation,
            scale,
            np.asarray(memory.bounds, dtype=float),
            float(config["collective_coordinate"]["box_tolerance"]),
        )
        if candidate is not None:
            perturbed, chosen_sign = candidate, sign
            break
    perturb_result = None
    perturb_cpu = perturb_wall = 0.0
    if perturbed is not None:
        perturb_result, perturb_cpu, perturb_wall = _finish_record(
            backend,
            memory,
            reconstructed,
            config,
            perturbed,
            reference_high,
            reference_low,
        )

    amplitude = 0.5
    spec = [amplitude if token == "U" else None for token in config["hysteresis"]["schedule"]]
    training = run_epoch_schedule(
        backend,
        high.copy(),
        route_epochs(memory, spec),
        float(config["epoch_duration"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
    )
    hysteresis_result, hysteresis_release_cpu, hysteresis_release_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        training.state,
        reference_high,
        reference_low,
    )
    hysteresis_cpu = float(training.cpu_seconds) + hysteresis_release_cpu
    hysteresis_wall = float(training.wall_seconds) + hysteresis_release_wall

    transect_count = len(config["exposure_task_ids"]) * len(config["parent_seed_indices"]) * len(config["transect"]["alphas"])
    boundary_count = (
        len(config["exposure_task_ids"])
        * len(config["validation_seed_indices"])
        * len(config["collective_coordinate"]["boundary_radius_fractions_of_separation"])
        * (2 + 2 * int(config["collective_coordinate"]["orthogonal_direction_count"]))
    )
    return_count = (
        len(config["exposure_task_ids"])
        * len(config["validation_seed_indices"])
        * 2
        * len(config["collective_coordinate"]["local_return_radius_fractions_of_separation"])
        * 2
        * int(config["collective_coordinate"]["orthogonal_direction_count"])
    )
    hysteresis_count = (
        len(config["exposure_task_ids"])
        * len(config["validation_seed_indices"])
        * 2
        * len(config["hysteresis"]["amplitudes"])
    )
    condition_count = transect_count + boundary_count + return_count + hysteresis_count
    projected_cpu = float(config["projection_safety_factor"]) * (
        float(transect_cpu) * transect_count
        + float(perturb_cpu) * (boundary_count + return_count)
        + hysteresis_cpu * hysteresis_count
    )
    projected_wall = projected_cpu / float(config["max_workers"])
    allowed = bool(
        source_fp["valid"]
        and source_state_distance <= 1e-10
        and source_fp_distance <= 1e-8
        and transect_result["valid"]
        and perturbed is not None
        and perturb_result is not None
        and perturb_result["valid"]
        and training.valid
        and hysteresis_result["valid"]
        and condition_count == int(config["registered_condition_count"])
        and projected_cpu < float(config["soft_aggregate_cpu_seconds"])
        and projected_wall < float(config["soft_wall_seconds"])
    )
    result = {
        "target": "exposure-basin-geometry",
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "autopsy_parent_manifest_sha256": parents["autopsy"]["manifest_sha256"],
        "exposure_parent_manifest_sha256": parents["exposure"]["manifest_sha256"],
        "atlas_parent_manifest_sha256": parents["atlas"]["manifest_sha256"],
        "worker_cap": int(config["max_workers"]),
        "biological_probe": {
            "memory_task_id": task_id,
            "seed_index": seed_index,
            "source_state_distance": source_state_distance,
            "source_fingerprint_distance": source_fp_distance,
            "coordinate_energy_fraction": float(coordinate_map[task_id]["energy_fraction"]),
            "chosen_coordinate_sign": chosen_sign,
            "transect_unit_cpu_seconds": transect_cpu,
            "perturbation_unit_cpu_seconds": perturb_cpu,
            "hysteresis_unit_cpu_seconds": hysteresis_cpu,
            "transect_unit_wall_seconds": transect_wall,
            "perturbation_unit_wall_seconds": perturb_wall,
            "hysteresis_unit_wall_seconds": hysteresis_wall,
            "valid": bool(
                transect_result["valid"]
                and perturb_result is not None
                and perturb_result["valid"]
                and training.valid
                and hysteresis_result["valid"]
            ),
        },
        "projection": {
            "state_transect_condition_count": transect_count,
            "boundary_specificity_condition_count": boundary_count,
            "local_return_condition_count": return_count,
            "hysteresis_condition_count": hysteresis_count,
            "registered_condition_count": condition_count,
            "worst_case_aggregate_cpu_seconds": projected_cpu,
            "worst_case_active_wall_seconds_at_four_workers": projected_wall,
            "safety_factor": float(config["projection_safety_factor"]),
            "projection_basis": "separately measured cold transect, perturbation, and full hysteresis kernels",
        },
        "deterministic_batch_plan": "task-by-seed shards with discovery/validation separation",
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "smoke.json", result)
    return result


def basin_geometry_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {
        "output": str(output),
        "sealed": (output / "SHA256SUMS").is_file(),
    }
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "collective-coordinate-models",
        "boundary-models",
        "transect-decision",
        "coordinate-decision",
        "local-return-decision",
        "hysteresis-decision",
        "observer-decision",
        "decision",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    for name in RECORD_FILES:
        path = output / name
        if path.is_file():
            result[f"{Path(name).stem.replace('-', '_')}_records"] = sum(
                1 for _ in read_jsonl(path)
            )
    return result
