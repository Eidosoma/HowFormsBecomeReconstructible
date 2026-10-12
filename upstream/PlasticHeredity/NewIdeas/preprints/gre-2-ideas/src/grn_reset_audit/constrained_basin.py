"""Constraint-aware recovery audit for durable continuous-GRN exposure states."""

from __future__ import annotations

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
from .atlas import state_from_payload, state_payload
from .basin_geometry import _finish_record, _task_context
from .contingency import (
    EXPOSURE_TASKS,
    _all_shard_cpu,
    _parallel,
    _runtime_manifest,
    _seed,
    _verify_parent,
    vector_rms,
)
from .engine import State
from .exposure_autopsy import (
    _fingerprint_from_parent,
    _merge_shards,
    _parent_pair,
    _parent_records,
    _shard,
    _state,
    _state_scale,
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
    "no-op.jsonl",
    "axial-return.jsonl",
    "transverse-return.jsonl",
    "coordinate-return.jsonl",
)


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(dict(row)) + "\n" for row in records))


def _median(values: Iterable[float | None]) -> float | None:
    data = [float(value) for value in values if value is not None and np.isfinite(value)]
    return None if not data else float(np.median(np.asarray(data, dtype=float)))


def load_constrained_basin_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported constrained-basin schema")
    if config.get("experiment_kind") != "constrained-basin-recovery":
        raise ValueError("not a constrained-basin-recovery protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("constrained basin does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("constrained basin does not pin the release generator")
    if tuple(config.get("exposure_task_ids", ())) != EXPOSURE_TASKS:
        raise ValueError("constrained-basin task cohort changed")
    if tuple(int(value) for value in config.get("validation_seed_indices", ())) != tuple(
        range(204, 208)
    ):
        raise ValueError("constrained-basin seed cohort changed")
    expected_nodes = {
        "10-1-32": 8,
        "26-6-39": 11,
        "37-10-41": 12,
        "69-4-16": 10,
        "204-5-10": 10,
    }
    if config.get("node_counts") != expected_nodes:
        raise ValueError("constrained-basin node counts changed")
    expected_dynamics = {
        "delta_t": 0.01,
        "phase_duration": 2500.0,
        "pulse_count": 5,
        "washout_total": 12500.0,
        "washout_chunk_duration": 2500.0,
    }
    for key, value in expected_dynamics.items():
        if not math.isclose(float(config.get(key, -1.0)), value):
            raise ValueError(f"constrained-basin historical setting differs for {key}")
    if [float(value) for value in config.get("release_checkpoints", ())] != [
        0.0,
        250.0,
        2500.0,
        12500.0,
    ]:
        raise ValueError("constrained-basin checkpoint ladder changed")
    geometry = config["geometry"]
    if int(geometry["candidate_pool_size"]) != 4096:
        raise ValueError("feasible-cone candidate pool changed")
    if int(geometry["direction_count"]) != 16:
        raise ValueError("constrained-basin direction count changed")
    if int(geometry["minimum_qualified_directions"]) != 12:
        raise ValueError("constrained-basin coverage gate changed")
    if [float(value) for value in geometry["radius_fractions_of_separation"]] != [
        0.05,
        0.025,
        0.01,
        0.005,
    ]:
        raise ValueError("constrained-basin radius ladder changed")
    if [float(value) for value in geometry["radius_multipliers"]] != [0.25, 0.5, 1.0]:
        raise ValueError("constrained-basin radius multipliers changed")
    if [float(value) for value in config["axial"]["fractions_toward_opposite"]] != [
        0.0025,
        0.005,
        0.01,
        0.015,
        0.02,
        0.025,
        0.03,
        0.04,
        0.05,
        0.1,
        0.25,
        0.5,
        0.75,
    ]:
        raise ValueError("constrained-basin axial ladder changed")
    counts = {str(key): int(value) for key, value in config["registered_record_counts"].items()}
    expected_counts = {
        "no-op.jsonl": 40,
        "axial-return.jsonl": 520,
        "transverse-return.jsonl": 1920,
        "coordinate-return.jsonl": 408,
    }
    if counts != expected_counts or sum(counts.values()) != int(
        config["registered_condition_count"]
    ):
        raise ValueError("constrained-basin registered condition count changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("constrained basin must cap workers at four")
    if not (
        0
        < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 14400.0
    ):
        raise ValueError("constrained-basin wall-time contract exceeds four hours")
    if not (
        0
        < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 57600.0
    ):
        raise ValueError("constrained-basin aggregate CPU contract is invalid")
    return config


def validate_constrained_basin_parents(
    config: Mapping[str, Any],
    basin: Path,
    autopsy: Path,
    exposure: Path,
    atlas: Path,
    upstream: Path,
) -> dict[str, Any]:
    gates = {
        "upstream": validate_upstream(upstream, str(config["upstream_commit"])),
        "basin": _verify_parent(
            basin,
            str(config["basin_parent_experiment_id"]),
            config["basin_parent_hashes"],
        ),
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
    basin_decision = json.loads((basin / "decision.json").read_text(encoding="utf-8"))
    if not basin_decision.get("source_valid"):
        raise ValueError("basin parent failed source reproduction")
    autopsy_decision = json.loads((autopsy / "decision.json").read_text(encoding="utf-8"))
    if not autopsy_decision.get("source_valid") or int(
        autopsy_decision.get("stable_separate_task_count", 0)
    ) != len(EXPOSURE_TASKS):
        raise ValueError("autopsy parent lacks the five stable exposure states")
    records = _parent_records(exposure)
    expected = len(EXPOSURE_TASKS) * len(config["validation_seed_indices"]) * 2
    selected = {
        key: value
        for key, value in records.items()
        if int(key[1]) in config["validation_seed_indices"]
    }
    if len(selected) != expected or not all(bool(row.get("valid")) for row in selected.values()):
        raise ValueError("exposure parent lacks a complete valid follow-up cohort")
    return gates


def project_to_feasible_cone(
    candidate: Sequence[float],
    position: Sequence[float],
    fixed: Sequence[bool] | None = None,
    tolerance: float = 1e-8,
) -> np.ndarray | None:
    """Project into the cone that never moves farther outside intervention bounds."""

    direction = np.asarray(candidate, dtype=float).copy()
    z = np.asarray(position, dtype=float)
    if direction.shape != z.shape or not np.all(np.isfinite(direction)):
        raise ValueError("candidate and position must be finite and shape-matched")
    fixed_mask = (
        np.zeros(len(z), dtype=bool)
        if fixed is None
        else np.asarray(fixed, dtype=bool)
    )
    if fixed_mask.shape != z.shape:
        raise ValueError("fixed mask differs from the state shape")
    direction[fixed_mask] = 0.0
    lower = (z <= float(tolerance)) & ~fixed_mask
    upper = (z >= 1.0 - float(tolerance)) & ~fixed_mask
    direction[lower] = np.maximum(direction[lower], 0.0)
    direction[upper] = np.minimum(direction[upper], 0.0)
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12 or not np.isfinite(norm):
        return None
    return direction / norm


def maximum_feasible_radius(
    position: Sequence[float], direction: Sequence[float], tolerance: float = 1e-8
) -> float:
    z = np.asarray(position, dtype=float)
    unit = np.asarray(direction, dtype=float)
    if z.shape != unit.shape:
        raise ValueError("position and direction shapes differ")
    norm = float(np.linalg.norm(unit))
    if norm <= 1e-12:
        return 0.0
    unit = unit / norm
    # ``memory.bounds`` are intervention ranges, not hard ODE state bounds.
    # Natural source states can sit outside them.  The admissible envelope is
    # therefore the smallest per-coordinate box containing both the source and
    # the intervention interval.  Cone projection prevents motion farther out.
    lower = np.minimum(z, 0.0)
    upper = np.maximum(z, 1.0)
    limits: list[float] = []
    for value, component, low, high in zip(z, unit, lower, upper):
        if component > 1e-14:
            limits.append((float(high) - float(value) + float(tolerance)) / float(component))
        elif component < -1e-14:
            limits.append((float(value) - float(low) + float(tolerance)) / -float(component))
    if not limits:
        return 0.0
    return max(0.0, float(min(limits)))


def select_feasible_directions(
    position: Sequence[float],
    axis: Sequence[float],
    fixed: Sequence[bool],
    radius: float,
    config: Mapping[str, Any],
    seed: int,
) -> dict[str, Any]:
    """Select deterministic, legal, low-axis-cosine, angularly diverse rays."""

    settings = config["geometry"]
    z = np.asarray(position, dtype=float)
    primary = np.asarray(axis, dtype=float)
    primary_norm = float(np.linalg.norm(primary))
    if primary_norm <= 1e-12:
        raise ValueError("high-low axis has zero norm")
    primary = primary / primary_norm
    rng = np.random.Generator(np.random.Philox(int(seed)))
    qualified: list[dict[str, Any]] = []
    for index in range(int(settings["candidate_pool_size"])):
        projected = project_to_feasible_cone(
            rng.normal(size=len(z)),
            z,
            fixed=fixed,
            tolerance=float(settings["active_bound_tolerance"]),
        )
        if projected is None:
            continue
        cosine = abs(float(np.dot(projected, primary)))
        feasible = maximum_feasible_radius(
            z, projected, tolerance=float(settings["box_tolerance"])
        )
        if (
            cosine <= float(settings["maximum_axis_cosine"]) + 1e-12
            and feasible + 1e-12 >= float(radius)
        ):
            qualified.append(
                {
                    "candidate_index": index,
                    "direction": projected,
                    "absolute_axis_cosine": cosine,
                    "maximum_feasible_radius": feasible,
                }
            )
    qualified.sort(key=lambda row: (float(row["absolute_axis_cosine"]), int(row["candidate_index"])))
    selected: list[dict[str, Any]] = []
    remaining = qualified.copy()
    while remaining and len(selected) < int(settings["direction_count"]):
        if not selected:
            chosen = remaining[0]
        else:
            def rank(row: Mapping[str, Any]) -> tuple[float, float, int]:
                direction = np.asarray(row["direction"], dtype=float)
                separation = min(
                    1.0 - float(np.dot(direction, np.asarray(prior["direction"], dtype=float)))
                    for prior in selected
                )
                return (
                    separation,
                    -float(row["absolute_axis_cosine"]),
                    -int(row["candidate_index"]),
                )

            chosen = max(remaining, key=rank)
        selected.append(chosen)
        remaining.remove(chosen)
    return {
        "requested_radius": float(radius),
        "qualified_pool_count": len(qualified),
        "selected_count": len(selected),
        "directions": selected,
    }


def _position_and_fixed(memory: Any, state: State, tolerance: float) -> tuple[np.ndarray, np.ndarray]:
    bounds = np.asarray(memory.bounds, dtype=float)
    widths = bounds[:, 1] - bounds[:, 0]
    fixed = np.abs(widths) <= 1e-12
    scale = np.maximum(np.abs(widths), 1e-8)
    position = (np.asarray(state.y, dtype=float) - bounds[:, 0]) / scale
    if not np.all(np.isfinite(position)):
        raise ValueError(f"source state for {memory.key.task_id} is non-finite")
    position = np.where(fixed, 0.0, position)
    return position, fixed


def build_feasible_geometry(
    config: Mapping[str, Any], exposure: Path, upstream: Path
) -> dict[str, Any]:
    parent_map = _parent_records(exposure)
    models: list[dict[str, Any]] = []
    settings = config["geometry"]
    minimum = int(settings["minimum_qualified_directions"])
    for task_id in config["exposure_task_ids"]:
        released = load_released_task(upstream, str(task_id))
        memory = load_memory(released.memory_path, released.key)
        if int(config["node_counts"][str(task_id)]) != int(memory.node_count):
            raise ValueError(f"registered node count changed for {task_id}")
        scale = _state_scale(memory)
        bounds = np.asarray(memory.bounds, dtype=float)
        cache: dict[tuple[float, int, str], dict[str, Any]] = {}
        radius_audit: list[dict[str, Any]] = []
        for fraction in settings["radius_fractions_of_separation"]:
            counts: list[int] = []
            for seed_index in config["validation_seed_indices"]:
                low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
                low, high = _state(low_row), _state(high_row)
                axis = (high.y - low.y) / scale
                separation = float(np.linalg.norm(axis))
                if separation <= 1e-12:
                    raise ValueError(f"zero exposure-state separation for {task_id}/{seed_index}")
                axis = axis / separation
                for arm, base in (("low", low), ("high", high)):
                    position, fixed = _position_and_fixed(
                        memory, base, float(settings["box_tolerance"])
                    )
                    selection = select_feasible_directions(
                        position,
                        axis,
                        fixed,
                        float(fraction) * separation,
                        config,
                        _seed(config, "feasible-cone", task_id, seed_index, arm),
                    )
                    cache[(float(fraction), int(seed_index), arm)] = selection
                    counts.append(int(selection["selected_count"]))
            radius_audit.append(
                {
                    "radius_fraction": float(fraction),
                    "minimum_selected_count": min(counts),
                    "all_endpoints_qualified": bool(counts and min(counts) >= minimum),
                }
            )
        eligible_rows = [row for row in radius_audit if row["all_endpoints_qualified"]]
        selected_fraction = (
            float(eligible_rows[0]["radius_fraction"]) if eligible_rows else None
        )
        diagnostic_fraction = (
            selected_fraction
            if selected_fraction is not None
            else float(settings["radius_fractions_of_separation"][-1])
        )
        endpoints: list[dict[str, Any]] = []
        for seed_index in config["validation_seed_indices"]:
            low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
            low, high = _state(low_row), _state(high_row)
            axis_vector = (high.y - low.y) / scale
            separation = float(np.linalg.norm(axis_vector))
            axis = axis_vector / separation
            for arm, base in (("low", low), ("high", high)):
                position, fixed = _position_and_fixed(
                    memory, base, float(settings["box_tolerance"])
                )
                selection = cache[(float(diagnostic_fraction), int(seed_index), arm)]
                endpoints.append(
                    {
                        "seed_index": int(seed_index),
                        "arm": arm,
                        "separation": separation,
                        "axis": axis,
                        "position": position,
                        "outside_intervention_range_count": int(
                            np.sum((position < 0.0) | (position > 1.0))
                        ),
                        "fixed_components": fixed,
                        "selected_radius": (
                            None
                            if selected_fraction is None
                            else selected_fraction * separation
                        ),
                        "diagnostic_radius_fraction": diagnostic_fraction,
                        **selection,
                    }
                )
        models.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "node_count": int(memory.node_count),
                "bounds": bounds,
                "scale": scale,
                "eligible": selected_fraction is not None,
                "selected_radius_fraction": selected_fraction,
                "radius_audit": radius_audit,
                "endpoints": endpoints,
            }
        )
    return {
        "task_id": "feasible-geometry",
        "frozen_before_dynamic_assays": True,
        "outcome_leakage_allowed": False,
        "models": models,
    }


def _geometry_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["memory_task_id"]): row for row in payload["models"]}


def _endpoint_geometry(model: Mapping[str, Any], seed_index: int, arm: str) -> dict[str, Any]:
    for row in model["endpoints"]:
        if int(row["seed_index"]) == int(seed_index) and str(row["arm"]) == str(arm):
            return dict(row)
    raise KeyError(f"missing endpoint geometry for {seed_index}/{arm}")


def apply_standardized_direction(
    base: State,
    direction: Sequence[float],
    radius: float,
    scale: Sequence[float],
    bounds: Sequence[Sequence[float]],
    tolerance: float,
) -> tuple[State | None, float | None]:
    unit = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(unit))
    if norm <= 1e-12 or not np.isfinite(norm):
        raise ValueError("perturbation direction has zero norm")
    unit = unit / norm
    width = np.asarray(scale, dtype=float)
    box = np.asarray(bounds, dtype=float)
    base_y = np.asarray(base.y, dtype=float)
    candidate = base_y + float(radius) * unit * width
    base_z = (base_y - box[:, 0]) / width
    candidate_z = (candidate - box[:, 0]) / width
    lower = np.minimum(base_z, 0.0)
    upper = np.maximum(base_z, 1.0)
    if np.any(candidate_z < lower - float(tolerance)) or np.any(
        candidate_z > upper + float(tolerance)
    ):
        return None, None
    actual = float(np.linalg.norm((candidate - base_y) / width))
    return State(candidate, base.w.copy(), base.c.copy(), float(base.t)), actual


def _invalid_record(
    task_id: str,
    seed_index: int,
    condition_id: str,
    reason: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "task_id": f"invalid|{task_id}|{seed_index}|{condition_id}",
        "condition_id": condition_id,
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "valid": False,
        "reason": str(reason),
        "fingerprint": None,
        "bipolar_score": None,
        "resting_response": None,
        **fields,
    }


def _no_op_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_constrained_basin_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "no-op", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    references = {
        "low": _fingerprint_from_parent(low_row),
        "high": _fingerprint_from_parent(high_row),
    }
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm, row in (("low", low_row), ("high", high_row)):
        result, used_cpu, used_wall = _finish_record(
            backend,
            memory,
            reconstructed,
            config,
            _state(row),
            references["high"],
            references["low"],
        )
        cpu += used_cpu
        wall += used_wall
        fp_distance = (
            None
            if result["fingerprint"] is None
            else vector_rms(
                np.asarray(result["fingerprint"], dtype=float) - references[arm]
            )
        )
        correct_arm = bool(
            result["bipolar_score"] is not None
            and (
                (arm == "low" and float(result["bipolar_score"]) < 0.0)
                or (arm == "high" and float(result["bipolar_score"]) > 0.0)
            )
        )
        records.append(
            {
                "task_id": f"no-op|{task_id}|{seed_index}|{arm}",
                "condition_id": f"no-op|{arm}",
                "assay": "no-op",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "arm": arm,
                "source_fingerprint_distance": fp_distance,
                "correct_source_arm": correct_arm,
                **result,
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "no-op",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _axial_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_constrained_basin_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "axial-return", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    low, high = _state(low_row), _state(high_row)
    scale = _state_scale(memory)
    separation = float(np.linalg.norm((high.y - low.y) / scale))
    reference_low = _fingerprint_from_parent(low_row)
    reference_high = _fingerprint_from_parent(high_row)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm, base, opposite in (("low", low, high), ("high", high, low)):
        for fraction in config["axial"]["fractions_toward_opposite"]:
            fraction = float(fraction)
            start = State(
                base.y + fraction * (opposite.y - base.y),
                base.w.copy(),
                base.c.copy(),
                float(base.t),
            )
            result, used_cpu, used_wall = _finish_record(
                backend,
                memory,
                reconstructed,
                config,
                start,
                reference_high,
                reference_low,
            )
            cpu += used_cpu
            wall += used_wall
            records.append(
                {
                    "task_id": f"axial|{task_id}|{seed_index}|{arm}|{fraction:.4f}",
                    "condition_id": f"axial|{arm}|f={fraction:.4f}",
                    "assay": "axial",
                    "memory_task_id": str(task_id),
                    "model_id": int(memory.key.model_id),
                    "seed_index": int(seed_index),
                    "arm": arm,
                    "fraction_toward_opposite": fraction,
                    "requested_radius": fraction * separation,
                    "actual_standardized_norm": float(
                        np.linalg.norm((start.y - base.y) / scale)
                    ),
                    **result,
                }
            )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "axial-return",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _transverse_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_constrained_basin_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "transverse-return", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    states = {"low": _state(low_row), "high": _state(high_row)}
    reference_low = _fingerprint_from_parent(low_row)
    reference_high = _fingerprint_from_parent(high_row)
    geometry = _geometry_map(output / "feasible-geometry.json")[str(task_id)]
    scale = np.asarray(geometry["scale"], dtype=float)
    bounds = np.asarray(geometry["bounds"], dtype=float)
    direction_count = int(config["geometry"]["direction_count"])
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        endpoint = _endpoint_geometry(geometry, int(seed_index), arm)
        selected = list(endpoint.get("directions", ())) if geometry.get("eligible") else []
        for multiplier in config["geometry"]["radius_multipliers"]:
            multiplier = float(multiplier)
            for direction_index in range(direction_count):
                condition_id = (
                    f"transverse|{arm}|direction={direction_index}|m={multiplier:.2f}"
                )
                common = {
                    "assay": "transverse",
                    "arm": arm,
                    "direction_index": direction_index,
                    "radius_multiplier": multiplier,
                    "selected_radius_fraction": geometry.get("selected_radius_fraction"),
                }
                if not geometry.get("eligible"):
                    records.append(
                        _invalid_record(
                            str(task_id),
                            int(seed_index),
                            condition_id,
                            "constraint-geometry-unavailable",
                            **common,
                        )
                    )
                    continue
                if direction_index >= len(selected):
                    records.append(
                        _invalid_record(
                            str(task_id),
                            int(seed_index),
                            condition_id,
                            "qualified-direction-unavailable",
                            **common,
                        )
                    )
                    continue
                selected_radius = float(endpoint["selected_radius"])
                radius = multiplier * selected_radius
                direction_row = selected[direction_index]
                start, actual = apply_standardized_direction(
                    states[arm],
                    direction_row["direction"],
                    radius,
                    scale,
                    bounds,
                    float(config["geometry"]["box_tolerance"]),
                )
                if start is None:
                    records.append(
                        _invalid_record(
                            str(task_id),
                            int(seed_index),
                            condition_id,
                            "bound-constrained-after-selection",
                            requested_radius=radius,
                            absolute_axis_cosine=direction_row["absolute_axis_cosine"],
                            **common,
                        )
                    )
                    continue
                result, used_cpu, used_wall = _finish_record(
                    backend,
                    memory,
                    reconstructed,
                    config,
                    start,
                    reference_high,
                    reference_low,
                )
                cpu += used_cpu
                wall += used_wall
                records.append(
                    {
                        "task_id": f"transverse|{task_id}|{seed_index}|{arm}|{direction_index}|{multiplier:.2f}",
                        "condition_id": condition_id,
                        "memory_task_id": str(task_id),
                        "model_id": int(memory.key.model_id),
                        "seed_index": int(seed_index),
                        "requested_radius": radius,
                        "actual_standardized_norm": actual,
                        "absolute_axis_cosine": float(
                            direction_row["absolute_axis_cosine"]
                        ),
                        "maximum_feasible_radius": float(
                            direction_row["maximum_feasible_radius"]
                        ),
                        **common,
                        **result,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "transverse-return",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _coordinate_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, exposure_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_constrained_basin_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "coordinate-return", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, Path(exposure_path), Path(atlas_path), Path(upstream_path), str(task_id)
    )
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    states = {"low": _state(low_row), "high": _state(high_row)}
    reference_low = _fingerprint_from_parent(low_row)
    reference_high = _fingerprint_from_parent(high_row)
    geometry = _geometry_map(output / "feasible-geometry.json")[str(task_id)]
    scale = np.asarray(geometry["scale"], dtype=float)
    bounds = np.asarray(geometry["bounds"], dtype=float)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        endpoint = _endpoint_geometry(geometry, int(seed_index), arm)
        position = np.asarray(endpoint["position"], dtype=float)
        fixed = np.asarray(endpoint["fixed_components"], dtype=bool)
        radius = endpoint.get("selected_radius")
        for node_index in range(int(memory.node_count)):
            condition_id = f"coordinate|{arm}|node={node_index}"
            common = {
                "assay": "coordinate",
                "arm": arm,
                "node_index": node_index,
                "selected_radius_fraction": geometry.get("selected_radius_fraction"),
            }
            if not geometry.get("eligible") or radius is None:
                records.append(
                    _invalid_record(
                        str(task_id),
                        int(seed_index),
                        condition_id,
                        "constraint-geometry-unavailable",
                        **common,
                    )
                )
                continue
            if fixed[node_index]:
                records.append(
                    _invalid_record(
                        str(task_id),
                        int(seed_index),
                        condition_id,
                        "fixed-width-coordinate",
                        requested_radius=float(radius),
                        **common,
                    )
                )
                continue
            direction = np.zeros(int(memory.node_count), dtype=float)
            direction[node_index] = (
                1.0 if 1.0 - position[node_index] >= position[node_index] else -1.0
            )
            start, actual = apply_standardized_direction(
                states[arm],
                direction,
                float(radius),
                scale,
                bounds,
                float(config["geometry"]["box_tolerance"]),
            )
            if start is None:
                records.append(
                    _invalid_record(
                        str(task_id),
                        int(seed_index),
                        condition_id,
                        "coordinate-bound-constrained",
                        requested_radius=float(radius),
                        **common,
                    )
                )
                continue
            result, used_cpu, used_wall = _finish_record(
                backend,
                memory,
                reconstructed,
                config,
                start,
                reference_high,
                reference_low,
            )
            cpu += used_cpu
            wall += used_wall
            records.append(
                {
                    "task_id": f"coordinate|{task_id}|{seed_index}|{arm}|{node_index}",
                    "condition_id": condition_id,
                    "memory_task_id": str(task_id),
                    "model_id": int(memory.key.model_id),
                    "seed_index": int(seed_index),
                    "requested_radius": float(radius),
                    "actual_standardized_norm": actual,
                    **common,
                    **result,
                }
            )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "coordinate-return",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _checkpoint_y(row: Mapping[str, Any], checkpoint: str) -> np.ndarray | None:
    payload = row.get("checkpoints", {}).get(str(checkpoint), {}).get("state")
    state = state_from_payload(payload)
    return None if state is None else np.asarray(state.y, dtype=float)


def recovery_metrics(
    no_op: Sequence[Mapping[str, Any]],
    assay_groups: Sequence[Sequence[Mapping[str, Any]]],
    geometry: Mapping[str, Any],
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    references = {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["arm"])): row
        for row in no_op
    }
    models = {str(row["memory_task_id"]): row for row in geometry["models"]}
    settings = config["return_decision"]
    metrics: list[dict[str, Any]] = []
    for records in assay_groups:
        for row in records:
            common = {
                key: row.get(key)
                for key in (
                    "condition_id",
                    "assay",
                    "memory_task_id",
                    "seed_index",
                    "arm",
                    "fraction_toward_opposite",
                    "direction_index",
                    "radius_multiplier",
                    "node_index",
                    "requested_radius",
                    "actual_standardized_norm",
                    "reason",
                )
                if key in row
            }
            metric: dict[str, Any] = {
                "task_id": f"metric|{row['task_id']}",
                "source_task_id": str(row["task_id"]),
                "valid": False,
                "initial_distance": None,
                "final_distance": None,
                "contraction_ratio": None,
                "fingerprint_rms_from_no_op": None,
                "same_arm": False,
                "switched": False,
                "returned": False,
                "checkpoint_distances": {},
                **common,
            }
            if not row.get("valid"):
                metrics.append(metric)
                continue
            key = (
                str(row["memory_task_id"]),
                int(row["seed_index"]),
                str(row["arm"]),
            )
            reference = references.get(key)
            if reference is None or not reference.get("valid"):
                metric["reason"] = "matched-no-op-unavailable"
                metrics.append(metric)
                continue
            scale = np.asarray(models[key[0]]["scale"], dtype=float)
            distances: dict[str, float | None] = {}
            for checkpoint in ("0", "250", "2500", "12500"):
                perturbed_y = _checkpoint_y(row, checkpoint)
                reference_y = _checkpoint_y(reference, checkpoint)
                distances[checkpoint] = (
                    None
                    if perturbed_y is None or reference_y is None
                    else float(np.linalg.norm((perturbed_y - reference_y) / scale))
                )
            initial = distances["0"]
            final = distances["12500"]
            ratio = (
                None
                if initial is None or final is None or initial <= 1e-12
                else float(final / initial)
            )
            fp_distance = (
                None
                if row.get("fingerprint") is None or reference.get("fingerprint") is None
                else vector_rms(
                    np.asarray(row["fingerprint"], dtype=float)
                    - np.asarray(reference["fingerprint"], dtype=float)
                )
            )
            score = row.get("bipolar_score")
            arm = str(row["arm"])
            same_arm = bool(
                score is not None
                and (
                    (arm == "low" and float(score) < 0.0)
                    or (arm == "high" and float(score) > 0.0)
                )
            )
            switched = bool(
                score is not None
                and (
                    (arm == "low" and float(score) > 0.0)
                    or (arm == "high" and float(score) < 0.0)
                )
            )
            returned = bool(
                ratio is not None
                and ratio <= float(settings["contraction_ratio_max"])
                and fp_distance is not None
                and fp_distance <= float(settings["fingerprint_rms_max"])
                and same_arm
            )
            metric.update(
                {
                    "valid": True,
                    "initial_distance": initial,
                    "final_distance": final,
                    "contraction_ratio": ratio,
                    "fingerprint_rms_from_no_op": fp_distance,
                    "same_arm": same_arm,
                    "switched": switched,
                    "returned": returned,
                    "checkpoint_distances": distances,
                }
            )
            metrics.append(metric)
    return metrics


def source_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    threshold = float(config["return_decision"]["fingerprint_rms_max"])
    rows: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        task_records = [row for row in records if row["memory_task_id"] == task_id]
        valid = [
            row
            for row in task_records
            if row.get("valid")
            and row.get("correct_source_arm")
            and row.get("source_fingerprint_distance") is not None
            and float(row["source_fingerprint_distance"]) <= threshold
        ]
        passed = len(task_records) == 2 * len(config["validation_seed_indices"]) and len(
            valid
        ) == len(task_records)
        rows.append(
            {
                "memory_task_id": str(task_id),
                "registered_count": len(task_records),
                "valid_reproduced_count": len(valid),
                "maximum_fingerprint_rms": (
                    max(float(row["source_fingerprint_distance"]) for row in valid)
                    if valid
                    else None
                ),
                "pass": bool(passed),
            }
        )
    passed = all(bool(row["pass"]) for row in rows)
    return {
        "task_id": "source-decision",
        "candidate_summaries": rows,
        "pass": passed,
        "verdict": "source-reproduction-passed" if passed else "source-reproduction-failed",
    }


def _arm_summary(
    metrics: Sequence[Mapping[str, Any]],
    task_id: str,
    seed_index: int,
    arm: str,
    multiplier: float,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [
        row
        for row in metrics
        if row.get("assay") == "transverse"
        and row.get("memory_task_id") == task_id
        and int(row.get("seed_index", -1)) == int(seed_index)
        and row.get("arm") == arm
        and row.get("radius_multiplier") is not None
        and math.isclose(float(row["radius_multiplier"]), float(multiplier))
        and row.get("valid")
    ]
    count = len(rows)
    returned = sum(bool(row.get("returned")) for row in rows)
    switched = sum(bool(row.get("switched")) for row in rows)
    same = sum(bool(row.get("same_arm")) for row in rows)
    minimum = int(config["return_decision"]["minimum_valid_controls_per_arm"])
    recovery_fraction = None if not rows else returned / count
    return {
        "valid_control_count": count,
        "returned_count": returned,
        "recovery_fraction": recovery_fraction,
        "switch_fraction": None if not rows else switched / count,
        "same_arm_fraction": None if not rows else same / count,
        "median_contraction_ratio": _median(row.get("contraction_ratio") for row in rows),
        "pass": bool(
            count >= minimum
            and recovery_fraction is not None
            and recovery_fraction
            >= float(config["return_decision"]["minimum_recovery_fraction"])
        ),
    }


def transverse_decision(
    metrics: Sequence[Mapping[str, Any]],
    geometry: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["return_decision"]
    geometry_map = {str(row["memory_task_id"]): row for row in geometry["models"]}
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        model = geometry_map[str(task_id)]
        multiplier_rows: list[dict[str, Any]] = []
        pass_by_multiplier: dict[float, int] = {}
        arm_rows_by_multiplier: dict[float, list[dict[str, Any]]] = {}
        for multiplier in config["geometry"]["radius_multipliers"]:
            multiplier = float(multiplier)
            per_seed: list[dict[str, Any]] = []
            flat_arms: list[dict[str, Any]] = []
            for seed_index in config["validation_seed_indices"]:
                arms = {
                    arm: _arm_summary(
                        metrics,
                        str(task_id),
                        int(seed_index),
                        arm,
                        multiplier,
                        config,
                    )
                    for arm in ("low", "high")
                }
                for arm, row in arms.items():
                    flat_arms.append({"seed_index": int(seed_index), "arm": arm, **row})
                per_seed.append(
                    {
                        "seed_index": int(seed_index),
                        "arms": arms,
                        "consistent": bool(arms["low"]["pass"] and arms["high"]["pass"]),
                    }
                )
            consistent = sum(bool(row["consistent"]) for row in per_seed)
            pass_by_multiplier[multiplier] = consistent
            arm_rows_by_multiplier[multiplier] = flat_arms
            multiplier_rows.append(
                {
                    "radius_multiplier": multiplier,
                    "consistent_seed_count": consistent,
                    "pass": consistent >= int(settings["minimum_consistent_seeds"]),
                    "per_seed": per_seed,
                }
            )
        selected = float(config["geometry"]["radius_multipliers"][-1])
        robust = bool(
            model.get("eligible")
            and pass_by_multiplier.get(selected, 0)
            >= int(settings["minimum_consistent_seeds"])
        )
        radius_limited = bool(
            model.get("eligible")
            and not robust
            and any(
                pass_by_multiplier.get(float(value), 0)
                >= int(settings["minimum_consistent_seeds"])
                for value in config["geometry"]["radius_multipliers"][:-1]
            )
        )
        largest = arm_rows_by_multiplier.get(selected, [])
        switch_by_arm = {
            arm: sum(
                1
                for row in largest
                if row["arm"] == arm
                and row["valid_control_count"]
                >= int(settings["minimum_valid_controls_per_arm"])
                and row["switch_fraction"] is not None
                and float(row["switch_fraction"]) >= float(settings["switch_fraction_min"])
            )
            for arm in ("low", "high")
        }
        switch_prone = any(
            count >= int(settings["minimum_consistent_seeds"])
            for count in switch_by_arm.values()
        )
        persistent_seed_count = 0
        for seed_index in config["validation_seed_indices"]:
            arms = {
                row["arm"]: row
                for row in largest
                if int(row["seed_index"]) == int(seed_index)
            }
            if set(arms) != {"low", "high"}:
                continue
            consistent = True
            for arm in ("low", "high"):
                row = arms[arm]
                ratio = row["median_contraction_ratio"]
                consistent = consistent and bool(
                    row["valid_control_count"]
                    >= int(settings["minimum_valid_controls_per_arm"])
                    and row["same_arm_fraction"] is not None
                    and float(row["same_arm_fraction"])
                    >= float(settings["same_arm_fraction_min"])
                    and ratio is not None
                    and float(settings["persistent_ratio_min"])
                    <= float(ratio)
                    <= float(settings["persistent_ratio_max"])
                )
            persistent_seed_count += int(consistent)
        persistent = persistent_seed_count >= int(settings["minimum_consistent_seeds"])
        if not model.get("eligible"):
            classification = "constraint-corner-pinned"
        elif robust:
            classification = "robust-constrained-basin-compatible"
        elif radius_limited:
            classification = "radius-limited-basin-compatible"
        elif switch_prone:
            classification = "switch-prone"
        elif persistent:
            classification = "persistent-without-restoration"
        else:
            classification = "mixed-or-partial-contraction"
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "geometry_eligible": bool(model.get("eligible")),
                "selected_radius_fraction": model.get("selected_radius_fraction"),
                "classification": classification,
                "robust": robust,
                "radius_limited": radius_limited,
                "switch_prone": switch_prone,
                "persistent_without_restoration": persistent,
                "persistent_seed_count": persistent_seed_count,
                "switch_seed_count_by_arm": switch_by_arm,
                "radius_summaries": multiplier_rows,
            }
        )
    counts = {
        label: sum(row["classification"] == label for row in summaries)
        for label in (
            "constraint-corner-pinned",
            "robust-constrained-basin-compatible",
            "radius-limited-basin-compatible",
            "switch-prone",
            "persistent-without-restoration",
            "mixed-or-partial-contraction",
        )
    }
    return {
        "task_id": "transverse-decision",
        "candidate_summaries": summaries,
        "classification_counts": counts,
        "pass_count": counts["robust-constrained-basin-compatible"]
        + counts["radius-limited-basin-compatible"],
        "pass": counts["robust-constrained-basin-compatible"]
        + counts["radius-limited-basin-compatible"]
        > 0,
    }


def axial_decision(
    metrics: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    minimum = int(config["return_decision"]["minimum_consistent_seeds"])
    for task_id in config["exposure_task_ids"]:
        arms: dict[str, Any] = {}
        for arm in ("low", "high"):
            fractions: list[dict[str, Any]] = []
            qualifying: list[float] = []
            for fraction in config["axial"]["fractions_toward_opposite"]:
                rows = [
                    row
                    for row in metrics
                    if row.get("assay") == "axial"
                    and row.get("memory_task_id") == task_id
                    and row.get("arm") == arm
                    and row.get("fraction_toward_opposite") is not None
                    and math.isclose(
                        float(row["fraction_toward_opposite"]), float(fraction)
                    )
                    and row.get("valid")
                ]
                returned = sum(bool(row.get("returned")) for row in rows)
                switched = sum(bool(row.get("switched")) for row in rows)
                qualifies = len(rows) == len(config["validation_seed_indices"]) and returned >= minimum
                if qualifies:
                    qualifying.append(float(fraction))
                fractions.append(
                    {
                        "fraction_toward_opposite": float(fraction),
                        "valid_seed_count": len(rows),
                        "returned_seed_count": returned,
                        "switched_seed_count": switched,
                        "median_contraction_ratio": _median(
                            row.get("contraction_ratio") for row in rows
                        ),
                        "qualifies": qualifies,
                    }
                )
            arms[arm] = {
                "largest_return_fraction": max(qualifying) if qualifying else None,
                "fractions": fractions,
            }
        summaries.append({"memory_task_id": str(task_id), "arms": arms})
    return {"task_id": "axial-decision", "candidate_summaries": summaries}


def coordinate_decision(
    metrics: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        nodes: list[dict[str, Any]] = []
        for node_index in range(int(config["node_counts"][str(task_id)])):
            arms: dict[str, Any] = {}
            for arm in ("low", "high"):
                rows = [
                    row
                    for row in metrics
                    if row.get("assay") == "coordinate"
                    and row.get("memory_task_id") == task_id
                    and row.get("arm") == arm
                    and int(row.get("node_index", -1)) == node_index
                    and row.get("valid")
                ]
                arms[arm] = {
                    "valid_seed_count": len(rows),
                    "returned_seed_count": sum(bool(row.get("returned")) for row in rows),
                    "switched_seed_count": sum(bool(row.get("switched")) for row in rows),
                    "median_contraction_ratio": _median(
                        row.get("contraction_ratio") for row in rows
                    ),
                    "median_fingerprint_rms": _median(
                        row.get("fingerprint_rms_from_no_op") for row in rows
                    ),
                }
            nodes.append({"node_index": node_index, "arms": arms})
        summaries.append({"memory_task_id": str(task_id), "nodes": nodes})
    return {"task_id": "coordinate-decision", "candidate_summaries": summaries}


def analyze_constrained_basin(
    output: Path, final_status: str | None = None
) -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    geometry = json.loads((output / "feasible-geometry.json").read_text(encoding="utf-8"))
    no_op = list(read_jsonl(output / "no-op.jsonl"))
    axial = list(read_jsonl(output / "axial-return.jsonl"))
    transverse = list(read_jsonl(output / "transverse-return.jsonl"))
    coordinate = list(read_jsonl(output / "coordinate-return.jsonl"))
    metrics = recovery_metrics(no_op, [axial, transverse, coordinate], geometry, config)
    _write_jsonl(output / "recovery-metrics.jsonl", metrics)
    source_result = source_decision(no_op, config)
    transverse_result = transverse_decision(metrics, geometry, config)
    axial_result = axial_decision(metrics, config)
    coordinate_result = coordinate_decision(metrics, config)
    for name, value in (
        ("source-decision", source_result),
        ("transverse-decision", transverse_result),
        ("axial-decision", axial_result),
        ("coordinate-decision", coordinate_result),
    ):
        write_json(output / f"{name}.json", value)
    counts = transverse_result["classification_counts"]
    source_valid = bool(source_result["pass"])
    if not source_valid:
        verdict = "source-reproduction-failed"
    elif counts["robust-constrained-basin-compatible"]:
        verdict = "robust-constrained-basin-leads"
    elif counts["radius-limited-basin-compatible"]:
        verdict = "radius-limited-basin-leads"
    elif counts["switch-prone"]:
        verdict = "switch-prone-exposure-states"
    elif counts["persistent-without-restoration"]:
        verdict = "persistent-states-without-restoration"
    elif counts["constraint-corner-pinned"] == len(config["exposure_task_ids"]):
        verdict = "constraint-corner-pinned"
    else:
        verdict = "mixed-or-partial-contraction"
    decision = {
        "task_id": "constrained-basin-decision",
        "pass": bool(source_valid and transverse_result["pass"]),
        "source_valid": source_valid,
        "verdict": verdict,
        "classification_counts": counts,
        "basin_compatible_task_count": int(transverse_result["pass_count"]),
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "decision.json", decision)
    ledger = (
        json.loads((output / "resource-ledger.json").read_text(encoding="utf-8"))
        if (output / "resource-ledger.json").is_file()
        else {}
    )
    record_counts = {
        name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES
    }
    expected_counts = {
        str(name): int(value)
        for name, value in config["registered_record_counts"].items()
    }
    minimum_completion_gate = bool(
        record_counts == expected_counts
        and len(metrics)
        == int(config["registered_condition_count"]) - expected_counts["no-op.jsonl"]
    )
    analysis = {
        "task_id": "constrained-basin-analysis",
        "experiment_id": config["experiment_id"],
        "run_status": final_status or "analyzed",
        "minimum_completion_gate": minimum_completion_gate,
        "decision_pass": bool(decision["pass"]),
        "verdict": verdict,
        "record_counts": record_counts,
        "recovery_metric_count": len(metrics),
        "active_wall_seconds": float(ledger.get("active_wall_seconds", 0.0)),
        "aggregate_cpu_seconds": float(ledger.get("aggregate_cpu_seconds", 0.0)),
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    report = f"""# GRN constrained basin recovery V1

Status: **{analysis['run_status']}**

Verdict: **{verdict}**

- Source-valid: **{source_valid}**.
- Robust constrained-basin tasks: **{counts['robust-constrained-basin-compatible']} / {len(config['exposure_task_ids'])}**.
- Radius-limited basin tasks: **{counts['radius-limited-basin-compatible']} / {len(config['exposure_task_ids'])}**.
- Switch-prone tasks: **{counts['switch-prone']} / {len(config['exposure_task_ids'])}**.
- Persistent without restoration: **{counts['persistent-without-restoration']} / {len(config['exposure_task_ids'])}**.
- Constraint-corner-pinned tasks: **{counts['constraint-corner-pinned']} / {len(config['exposure_task_ids'])}**.
- Mixed or partial contraction: **{counts['mixed-or-partial-contraction']} / {len(config['exposure_task_ids'])}**.

Records: {record_counts}

Resource use: {analysis['active_wall_seconds']:.3f} active wall seconds and
{analysis['aggregate_cpu_seconds']:.3f} aggregate worker CPU seconds.

Claim boundary: {config['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class ConstrainedBasinCampaign:
    def __init__(
        self,
        config_path: Path,
        basin: Path,
        autopsy: Path,
        exposure: Path,
        atlas: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_constrained_basin_config(self.config_path)
        self.basin = basin.resolve()
        self.autopsy = autopsy.resolve()
        self.exposure = exposure.resolve()
        self.atlas = atlas.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("constrained-basin workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed constrained-basin campaign cannot be resumed")
        self.parent_gate = validate_constrained_basin_parents(
            self.config,
            self.basin,
            self.autopsy,
            self.exposure,
            self.atlas,
            self.upstream,
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

    def _require_budget(self, stage: str) -> None:
        self._state("running", stage)
        if not self.ledger.may_start():
            raise TimeoutError(f"soft resource budget reached before {stage}")

    def _register(self) -> None:
        payload = {
            "experiment_id": self.config["experiment_id"],
            "protocol": self.config,
            "protocol_digest": digest(self.config),
            "workers": self.workers,
            "upstream": self.parent_gate["upstream"],
            "parents": self.parent_gate,
            "runtime": _runtime_manifest(),
            "record_files": list(RECORD_FILES),
        }
        path = self.output / "registration.json"
        if path.is_file():
            prior = json.loads(path.read_text(encoding="utf-8"))
            for key in ("experiment_id", "protocol_digest", "parents"):
                if prior.get(key) != payload.get(key):
                    raise ValueError(f"resumed constrained-basin registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"].get(
                "container_image_id"
            ):
                raise ValueError("resumed constrained-basin image differs")
        write_json(path, payload)
        write_json(
            self.output / "parent-gate.json",
            {"task_id": "parent-gate", "pass": True, **self.parent_gate},
        )
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "primary": "Legal transverse disturbances contract to their source exposure state.",
                "alternatives": [
                    "Recovery exists only below a narrow radius.",
                    "The state persists without restoring displaced expression.",
                    "Legal disturbances cross into the opposite exposure state.",
                    "The registered expression box leaves no transverse local geometry.",
                ],
                "same_state_different_history_in_scope": False,
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
            self._require_budget("feasible-geometry")
            geometry = build_feasible_geometry(self.config, self.exposure, self.upstream)
            write_json(self.output / "feasible-geometry.json", geometry)
            common_args = [
                (
                    str(self.config_path),
                    str(self.exposure),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed_index),
                )
                for task_id in self.config["exposure_task_ids"]
                for seed_index in self.config["validation_seed_indices"]
            ]
            self._require_budget("no-op")
            no_op_shards = _parallel(_no_op_worker, common_args, self.workers)
            _merge_shards(self.output, "no-op", no_op_shards)
            self._require_budget("axial-return")
            axial_shards = _parallel(_axial_worker, common_args, self.workers)
            _merge_shards(self.output, "axial-return", axial_shards)
            self._require_budget("transverse-return")
            transverse_shards = _parallel(_transverse_worker, common_args, self.workers)
            _merge_shards(self.output, "transverse-return", transverse_shards)
            self._require_budget("coordinate-return")
            coordinate_shards = _parallel(_coordinate_worker, common_args, self.workers)
            _merge_shards(self.output, "coordinate-return", coordinate_shards)
            self._state("analyzing", "analysis")
            self.ledger.close()
            analysis = analyze_constrained_basin(self.output, final_status="completed")
            if not analysis["minimum_completion_gate"]:
                raise ValueError("constrained-basin registered record set is incomplete")
            decision = json.loads((self.output / "decision.json").read_text(encoding="utf-8"))
            self._state("completed", "complete", verdict=decision["verdict"])
            write_checksums(self.output)
            return 0
        except BaseException as error:
            incidents_path = self.output / "runtime-incidents.json"
            incidents = (
                json.loads(incidents_path.read_text(encoding="utf-8"))
                if incidents_path.is_file()
                else {"incidents": []}
            )
            state_path = self.output / "state.json"
            prior_state = (
                json.loads(state_path.read_text(encoding="utf-8"))
                if state_path.is_file()
                else {}
            )
            incidents.setdefault("incidents", []).append(
                {
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "stage": prior_state.get("stage"),
                    "error": repr(error),
                }
            )
            write_json(incidents_path, incidents)
            self.ledger.close()
            write_json(
                state_path,
                {
                    "status": "failed",
                    "stage": "exception",
                    "workers": self.workers,
                    "error": repr(error),
                    "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
            raise


def run_constrained_basin(
    config: Path,
    basin: Path,
    autopsy: Path,
    exposure: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return ConstrainedBasinCampaign(
        config, basin, autopsy, exposure, atlas, upstream, output, workers
    ).run()


def _smoke_start(
    arm: str,
    base: State,
    opposite: State,
    endpoint: Mapping[str, Any],
    model: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[State, State, State]:
    axial_fraction = float(config["axial"]["fractions_toward_opposite"][-1])
    axial = State(
        base.y + axial_fraction * (opposite.y - base.y),
        base.w.copy(),
        base.c.copy(),
        float(base.t),
    )
    direction = endpoint["directions"][0]["direction"]
    transverse, _ = apply_standardized_direction(
        base,
        direction,
        float(endpoint["selected_radius"]),
        model["scale"],
        model["bounds"],
        float(config["geometry"]["box_tolerance"]),
    )
    position = np.asarray(endpoint["position"], dtype=float)
    fixed = np.asarray(endpoint["fixed_components"], dtype=bool)
    available = [index for index, value in enumerate(fixed) if not value]
    if not available:
        raise ValueError("smoke task has no non-fixed expression coordinate")
    node_index = available[0]
    coordinate_direction = np.zeros(len(position), dtype=float)
    coordinate_direction[node_index] = (
        1.0 if 1.0 - position[node_index] >= position[node_index] else -1.0
    )
    coordinate, _ = apply_standardized_direction(
        base,
        coordinate_direction,
        float(endpoint["selected_radius"]),
        model["scale"],
        model["bounds"],
        float(config["geometry"]["box_tolerance"]),
    )
    if transverse is None or coordinate is None:
        raise ValueError(f"smoke could not construct qualified {arm} perturbations")
    return axial, transverse, coordinate


def smoke_constrained_basin(
    config_path: Path,
    basin: Path,
    autopsy: Path,
    exposure: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_constrained_basin_config(config_path)
    basin, autopsy, exposure, atlas, upstream = (
        basin.resolve(),
        autopsy.resolve(),
        exposure.resolve(),
        atlas.resolve(),
        upstream.resolve(),
    )
    parents = validate_constrained_basin_parents(
        config, basin, autopsy, exposure, atlas, upstream
    )
    geometry = build_feasible_geometry(config, exposure, upstream)
    models = {str(row["memory_task_id"]): row for row in geometry["models"]}
    eligible = [row for row in geometry["models"] if row.get("eligible")]
    if not eligible:
        raise ValueError("no task supports a transverse real-ODE smoke kernel")
    model = max(eligible, key=lambda row: int(row["node_count"]))
    task_id = str(model["memory_task_id"])
    seed_index = int(config["validation_seed_indices"][0])
    _, memory, backend, reconstructed, parent_map = _task_context(
        config, exposure, atlas, upstream, task_id
    )
    low_row, high_row = _parent_pair(parent_map, task_id, seed_index)
    low, high = _state(low_row), _state(high_row)
    reference_low = _fingerprint_from_parent(low_row)
    reference_high = _fingerprint_from_parent(high_row)
    endpoint = _endpoint_geometry(models[task_id], seed_index, "low")
    axial, transverse, coordinate = _smoke_start(
        "low", low, high, endpoint, models[task_id], config
    )
    measured: dict[str, dict[str, Any]] = {}
    for name, start in (
        ("no_op", low),
        ("axial", axial),
        ("transverse", transverse),
        ("coordinate", coordinate),
    ):
        result, cpu, wall = _finish_record(
            backend,
            memory,
            reconstructed,
            config,
            start,
            reference_high,
            reference_low,
        )
        measured[name] = {
            "valid": bool(result["valid"]),
            "cpu_seconds": float(cpu),
            "wall_seconds": float(wall),
        }
    counts = config["registered_record_counts"]
    projected_cpu = float(config["projection_safety_factor"]) * (
        float(measured["no_op"]["cpu_seconds"]) * int(counts["no-op.jsonl"])
        + float(measured["axial"]["cpu_seconds"]) * int(counts["axial-return.jsonl"])
        + float(measured["transverse"]["cpu_seconds"])
        * int(counts["transverse-return.jsonl"])
        + float(measured["coordinate"]["cpu_seconds"])
        * int(counts["coordinate-return.jsonl"])
    )
    projected_wall = projected_cpu / float(config["max_workers"])
    condition_count = sum(int(value) for value in counts.values())
    allowed = bool(
        all(bool(row["valid"]) for row in measured.values())
        and condition_count == int(config["registered_condition_count"])
        and projected_cpu < float(config["soft_aggregate_cpu_seconds"])
        and projected_wall < float(config["soft_wall_seconds"])
    )
    result = {
        "target": "constrained-basin-recovery",
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "basin_parent_manifest_sha256": parents["basin"]["manifest_sha256"],
        "autopsy_parent_manifest_sha256": parents["autopsy"]["manifest_sha256"],
        "exposure_parent_manifest_sha256": parents["exposure"]["manifest_sha256"],
        "atlas_parent_manifest_sha256": parents["atlas"]["manifest_sha256"],
        "worker_cap": int(config["max_workers"]),
        "biological_probe": {
            "memory_task_id": task_id,
            "seed_index": seed_index,
            "selected_radius_fraction": model["selected_radius_fraction"],
            "qualified_direction_count": int(endpoint["selected_count"]),
            "kernels": measured,
        },
        "geometry": {
            "eligible_task_count": len(eligible),
            "task_classification_remains_defined_when_ineligible": True,
        },
        "projection": {
            "registered_condition_count": condition_count,
            "record_counts": counts,
            "worst_case_aggregate_cpu_seconds": projected_cpu,
            "worst_case_active_wall_seconds_at_four_workers": projected_wall,
            "safety_factor": float(config["projection_safety_factor"]),
            "projection_basis": "separately measured no-op, axial, transverse, and coordinate kernels",
        },
        "deterministic_batch_plan": "assay-by-task-by-seed shards",
    }
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"constrained-basin smoke output exists: {output}")
    output.mkdir(parents=True)
    write_json(output / "smoke.json", result)
    return result


def constrained_basin_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {
        "output": str(output),
        "sealed": (output / "SHA256SUMS").is_file(),
    }
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "feasible-geometry",
        "source-decision",
        "transverse-decision",
        "axial-decision",
        "coordinate-decision",
        "decision",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    result["record_counts"] = {
        name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES
    }
    result["shard_counts"] = {
        stage: len(list((output / ".shards" / stage).glob("*.json")))
        if (output / ".shards" / stage).is_dir()
        else 0
        for stage in ("no-op", "axial-return", "transverse-return", "coordinate-return")
    }
    return result
