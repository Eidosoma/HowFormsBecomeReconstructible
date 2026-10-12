"""Structural-quotient and mode-plane audit of durable GRN exposure states."""

from __future__ import annotations

import hashlib
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
from .basin_geometry import _finish_record, _release_path
from .constrained_basin import apply_standardized_direction, maximum_feasible_radius
from .contingency import (
    EXPOSURE_TASKS,
    _all_shard_cpu,
    _calibration_map,
    _fingerprint,
    _parallel,
    _runtime_manifest,
    _verify_parent,
    bipolar_score,
    vector_rms,
)
from .engine import JaxBackend, State
from .exposure_autopsy import _merge_shards, _shard
from .renewal import ResourceLedger
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    validate_upstream,
)


FOCAL_TASKS = ("37-10-41", "204-5-10", "10-1-32")
RECORD_FILES = (
    "no-op.jsonl",
    "targeted-rays.jsonl",
    "mode-plane.jsonl",
    "confirmations.jsonl",
)
CHECKPOINT_KEYS = ("0", "250", "2500", "12500")


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(dict(row)) + "\n" for row in records))


def _unit(values: Sequence[float], *, fallback: Sequence[float] | None = None) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12 or not np.isfinite(norm):
        if fallback is None:
            raise ValueError("cannot normalize a zero or non-finite vector")
        return _unit(fallback)
    vector = vector / norm
    pivot = int(np.argmax(np.abs(vector)))
    return -vector if vector[pivot] < 0.0 else vector


def _checkpoint_y(row: Mapping[str, Any], checkpoint: str) -> np.ndarray | None:
    payload = row.get("checkpoints", {}).get(str(checkpoint), {}).get("state")
    if not isinstance(payload, Mapping):
        return None
    values = np.asarray(payload.get("y", ()), dtype=float)
    return values if values.ndim == 1 and np.all(np.isfinite(values)) else None


def _state(row: Mapping[str, Any]) -> State:
    return state_from_payload(row["source_state"])


def _parent_no_op_map(parent: Path) -> dict[tuple[str, int, str], dict[str, Any]]:
    rows = list(read_jsonl(parent / "no-op.jsonl"))
    result = {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["arm"])): dict(row)
        for row in rows
    }
    if len(result) != len(rows):
        raise ValueError("duplicate constrained-basin no-op key")
    return result


def _geometry_map(parent: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads((parent / "feasible-geometry.json").read_text(encoding="utf-8"))
    return {str(row["memory_task_id"]): dict(row) for row in payload["models"]}


def _model_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["memory_task_id"]): dict(row) for row in payload["models"]}


def load_memory_manifold_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0" or config.get("experiment_kind") != "memory-manifold":
        raise ValueError("not a supported memory-manifold protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("memory-manifold protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("memory-manifold protocol does not pin the release generator")
    if tuple(config.get("exposure_task_ids", ())) != EXPOSURE_TASKS:
        raise ValueError("memory-manifold structural cohort changed")
    if tuple(config.get("focal_task_ids", ())) != FOCAL_TASKS:
        raise ValueError("memory-manifold focal cohort changed")
    if tuple(int(value) for value in config.get("discovery_seed_indices", ())) != (204, 205):
        raise ValueError("memory-manifold discovery cohort changed")
    if tuple(int(value) for value in config.get("validation_seed_indices", ())) != (206, 207):
        raise ValueError("memory-manifold validation cohort changed")
    if tuple(int(value) for value in config.get("all_seed_indices", ())) != tuple(range(204, 208)):
        raise ValueError("memory-manifold complete seed cohort changed")
    if tuple(config.get("directions", ())) != (
        "invariant-memory-aligned",
        "fastest-contracting",
        "slowest-non-invariant",
        "switch-predictive",
    ):
        raise ValueError("memory-manifold causal directions changed")
    expected_radii = [0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25]
    if [float(value) for value in config.get("radial_fractions_of_separation", ())] != expected_radii:
        raise ValueError("memory-manifold radius ladder changed")
    if int(config["mode_plane"]["angle_count"]) != 12:
        raise ValueError("memory-manifold angle count changed")
    expected_counts = {
        "no-op.jsonl": 24,
        "targeted-rays.jsonl": 672,
        "mode-plane.jsonl": 2016,
        "confirmations.jsonl": 72,
    }
    counts = {str(key): int(value) for key, value in config["registered_record_counts"].items()}
    if counts != expected_counts or sum(counts.values()) != int(config["registered_condition_count"]):
        raise ValueError("memory-manifold registered condition count changed")
    for key, expected in {
        "delta_t": 0.01,
        "phase_duration": 2500.0,
        "pulse_count": 5,
        "washout_total": 12500.0,
        "washout_chunk_duration": 2500.0,
    }.items():
        if not math.isclose(float(config.get(key, -1.0)), expected):
            raise ValueError(f"memory-manifold historical setting differs for {key}")
    if [float(value) for value in config["release_checkpoints"]] != [0.0, 250.0, 2500.0, 12500.0]:
        raise ValueError("memory-manifold checkpoint ladder changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("memory-manifold campaign must cap workers at four")
    if not (
        0.0
        < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 14400.0
    ):
        raise ValueError("memory-manifold wall-time contract exceeds four hours")
    if not (
        0.0
        < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 57600.0
    ):
        raise ValueError("memory-manifold CPU contract is invalid")
    return config


def validate_memory_manifold_parents(
    config: Mapping[str, Any], parent: Path, atlas: Path, upstream: Path
) -> dict[str, Any]:
    gates = {
        "upstream": validate_upstream(upstream, str(config["upstream_commit"])),
        "constrained": _verify_parent(
            parent,
            str(config["constrained_parent_experiment_id"]),
            config["constrained_parent_hashes"],
        ),
        "atlas": _verify_parent(
            atlas,
            str(config["atlas_parent_experiment_id"]),
            config["atlas_parent_hashes"],
        ),
    }
    decision = json.loads((parent / "decision.json").read_text(encoding="utf-8"))
    if not decision.get("source_valid"):
        raise ValueError("constrained-basin parent failed source reproduction")
    rows = _parent_no_op_map(parent)
    expected = len(EXPOSURE_TASKS) * len(config["all_seed_indices"]) * 2
    if len(rows) != expected or not all(bool(row.get("valid")) for row in rows.values()):
        raise ValueError("constrained-basin parent no-op cohort is incomplete")
    return gates


def common_nullspace(
    matrices: Sequence[Sequence[Sequence[float]]], relative_tolerance: float = 1e-8
) -> tuple[np.ndarray, np.ndarray]:
    """Return a deterministic orthonormal right nullspace of stacked matrices."""

    arrays = [np.asarray(matrix, dtype=float) for matrix in matrices]
    if not arrays or any(array.ndim != 2 for array in arrays):
        raise ValueError("common-nullspace input must contain matrices")
    width = arrays[0].shape[1]
    if any(array.shape[1] != width or not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("common-nullspace matrices must be finite and width-matched")
    stacked = np.vstack(arrays)
    _, singular_values, vh = np.linalg.svd(stacked, full_matrices=True)
    scale = max(float(singular_values[0]) if len(singular_values) else 0.0, 1e-12)
    rank = int(np.sum(singular_values > float(relative_tolerance) * scale))
    basis = vh[rank:, :].T.copy()
    for index in range(basis.shape[1]):
        basis[:, index] = _unit(basis[:, index])
    return basis, singular_values


def orthogonal_complement(basis: Sequence[Sequence[float]], dimension: int) -> np.ndarray:
    values = np.asarray(basis, dtype=float)
    if values.size == 0:
        return np.eye(int(dimension), dtype=float)
    values = values.reshape(int(dimension), -1)
    q, _ = np.linalg.qr(values, mode="complete")
    return q[:, values.shape[1] :]


def projection_fraction(vector: Sequence[float], basis: Sequence[Sequence[float]]) -> float:
    axis = _unit(vector)
    values = np.asarray(basis, dtype=float)
    if values.size == 0:
        return 0.0
    values = values.reshape(len(axis), -1)
    return float(np.linalg.norm(values.T @ axis))


def standardized_jacobian(backend: JaxBackend, state: State, scale: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    width = np.asarray(scale, dtype=float)
    jnp = backend.jax.numpy
    if not hasattr(backend, "_memory_manifold_rate"):
        rate = backend.module.RateofSpeciesChange()

        def vector_field(y: Any, t: Any, w: Any, c: Any) -> Any:
            return rate(y, t, w, c)

        backend._memory_manifold_rate = rate
        backend._memory_manifold_jacobian = backend.jax.jit(
            backend.jax.jacfwd(vector_field, argnums=0)
        )
    rate = backend._memory_manifold_rate
    jacobian_fn = backend._memory_manifold_jacobian
    w = jnp.asarray(state.w)
    c = jnp.asarray(state.c)
    t = float(state.t)
    y = jnp.asarray(state.y)
    residual = np.asarray(rate(y, t, w, c), dtype=float) / width
    jacobian = np.asarray(jacobian_fn(y, t, w, c), dtype=float)
    standardized = (jacobian * width[None, :]) / width[:, None]
    return standardized, residual


def _local_spectrum(jacobian: np.ndarray, positive_tolerance: float) -> dict[str, Any]:
    values = np.linalg.eigvals(jacobian)
    real = np.real(values)
    imag = np.imag(values)
    return {
        "eigenvalue_real": real,
        "eigenvalue_imag": imag,
        "max_real_eigenvalue": float(np.max(real)),
        "positive_mode_count": int(np.sum(real > float(positive_tolerance))),
        "near_zero_mode_count": int(np.sum(np.abs(values) <= float(positive_tolerance))),
        "negative_mode_count": int(np.sum(real < -float(positive_tolerance))),
        "spectral_abscissa": float(np.max(real)),
        "departure_from_normality": float(
            np.linalg.norm(jacobian.T @ jacobian - jacobian @ jacobian.T)
        ),
    }


def build_structural_census(
    config: Mapping[str, Any], parent: Path, upstream: Path
) -> dict[str, Any]:
    parent_map = _parent_no_op_map(parent)
    geometry = _geometry_map(parent)
    settings = config["structural"]
    models: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        released = load_released_task(upstream, str(task_id))
        memory = load_memory(released.memory_path, released.key)
        backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
        scale = np.asarray(geometry[str(task_id)]["scale"], dtype=float)
        discovery_jacobians: list[np.ndarray] = []
        local_rows: list[dict[str, Any]] = []
        discovery_axes: list[np.ndarray] = []
        for seed_index in config["all_seed_indices"]:
            low = _state(parent_map[(str(task_id), int(seed_index), "low")])
            high = _state(parent_map[(str(task_id), int(seed_index), "high")])
            axis = (high.y - low.y) / scale
            separation = float(np.linalg.norm(axis))
            if separation <= 1e-12:
                raise ValueError(f"zero high-low separation for {task_id}/{seed_index}")
            if int(seed_index) in config["discovery_seed_indices"]:
                discovery_axes.append(axis / separation)
            for arm, state in (("low", low), ("high", high)):
                jacobian, residual = standardized_jacobian(backend, state, scale)
                local_rows.append(
                    {
                        "seed_index": int(seed_index),
                        "seed_role": (
                            "discovery"
                            if int(seed_index) in config["discovery_seed_indices"]
                            else "validation"
                        ),
                        "arm": arm,
                        "standardized_rate_norm": float(np.linalg.norm(residual)),
                        **_local_spectrum(
                            jacobian, float(settings["positive_real_tolerance"])
                        ),
                    }
                )
                if int(seed_index) in config["discovery_seed_indices"]:
                    discovery_jacobians.append(jacobian)
            if int(seed_index) in config["discovery_seed_indices"]:
                fraction = float(settings["probe_fraction_of_separation"])
                for alpha in (0.5, fraction, 1.0 - fraction):
                    probe = State(
                        low.y + float(alpha) * (high.y - low.y),
                        low.w.copy(),
                        low.c.copy(),
                        float(low.t),
                    )
                    jacobian, _ = standardized_jacobian(backend, probe, scale)
                    discovery_jacobians.append(jacobian)
        basis, singular_values = common_nullspace(
            discovery_jacobians, float(settings["relative_null_tolerance"])
        )
        mean_axis = _unit(np.mean(np.asarray(discovery_axes), axis=0))
        _, _, vh = np.linalg.svd(np.vstack(discovery_jacobians), full_matrices=True)
        weakest = _unit(vh[-1])
        models.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "node_count": int(memory.node_count),
                "scale": scale,
                "memory_axis": mean_axis,
                "structural_invariant_dimension": int(basis.shape[1]),
                "structural_invariant_basis": basis,
                "stacked_jacobian_singular_values": singular_values,
                "weakest_structural_direction": weakest,
                "memory_axis_invariant_fraction": projection_fraction(mean_axis, basis),
                "local_spectra": local_rows,
                "no_local_positive_mode": not any(
                    int(row["positive_mode_count"]) > 0 for row in local_rows
                ),
            }
        )
    return {
        "task_id": "structural-census",
        "frozen_before_new_dynamic_assays": True,
        "outcome_leakage_allowed": False,
        "relative_null_tolerance": float(settings["relative_null_tolerance"]),
        "models": models,
    }


def fit_linear_map(
    x: Sequence[Sequence[float]],
    y: Sequence[Sequence[float]],
    ridge_candidates: Sequence[float],
    fold_count: int,
) -> dict[str, Any]:
    """Fit y = A x with deterministic cross-validated ridge regularization."""

    inputs = np.asarray(x, dtype=float)
    outputs = np.asarray(y, dtype=float)
    if inputs.ndim != 2 or outputs.shape != inputs.shape or len(inputs) < 2:
        raise ValueError("finite-time map needs at least two shape-matched samples")
    folds = np.arange(len(inputs)) % max(2, min(int(fold_count), len(inputs)))
    candidates: list[dict[str, Any]] = []
    for ridge in ridge_candidates:
        errors: list[float] = []
        for fold in sorted(set(int(value) for value in folds)):
            train = folds != fold
            test = ~train
            if np.sum(train) < 1 or np.sum(test) < 1:
                continue
            gram = inputs[train].T @ inputs[train] + float(ridge) * np.eye(inputs.shape[1])
            coefficients = np.linalg.solve(gram, inputs[train].T @ outputs[train]).T
            prediction = inputs[test] @ coefficients.T
            denominator = max(float(np.linalg.norm(outputs[test])), 1e-12)
            errors.append(float(np.linalg.norm(prediction - outputs[test]) / denominator))
        candidates.append(
            {
                "ridge": float(ridge),
                "relative_cv_error": float(np.mean(errors)) if errors else float("inf"),
            }
        )
    selected = min(candidates, key=lambda row: (row["relative_cv_error"], row["ridge"]))
    ridge = float(selected["ridge"])
    gram = inputs.T @ inputs + ridge * np.eye(inputs.shape[1])
    matrix = np.linalg.solve(gram, inputs.T @ outputs).T
    return {
        "matrix": matrix,
        "selected_ridge": ridge,
        "candidate_scores": candidates,
        "sample_count": int(len(inputs)),
        "condition_number": float(np.linalg.cond(gram)),
        "training_relative_error": float(
            np.linalg.norm(inputs @ matrix.T - outputs)
            / max(float(np.linalg.norm(outputs)), 1e-12)
        ),
    }


def _parent_dynamic_records(parent: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for name in ("axial-return.jsonl", "transverse-return.jsonl", "coordinate-return.jsonl"):
        records.extend(dict(row) for row in read_jsonl(parent / name))
    metrics = {
        str(row["source_task_id"]): dict(row)
        for row in read_jsonl(parent / "recovery-metrics.jsonl")
    }
    return records, metrics


def _fit_samples(
    task_id: str,
    arm: str,
    config: Mapping[str, Any],
    parent: Path,
    scale: np.ndarray,
    separation: float,
) -> tuple[np.ndarray, dict[str, np.ndarray], list[dict[str, Any]]]:
    records, metrics = _parent_dynamic_records(parent)
    no_ops = _parent_no_op_map(parent)
    inputs: list[np.ndarray] = []
    outputs = {key: [] for key in ("250", "2500", "12500")}
    metadata: list[dict[str, Any]] = []
    maximum = float(config["finite_time_fit"]["maximum_fraction_of_separation"]) * separation
    for row in records:
        if (
            row.get("valid")
            and str(row.get("memory_task_id")) == str(task_id)
            and str(row.get("arm")) == str(arm)
            and int(row.get("seed_index", -1)) in config["discovery_seed_indices"]
        ):
            metric = metrics.get(str(row["task_id"]))
            if not metric or not metric.get("valid") or not metric.get("same_arm"):
                continue
            reference = no_ops[(str(task_id), int(row["seed_index"]), str(arm))]
            initial = _checkpoint_y(row, "0")
            baseline = _checkpoint_y(reference, "0")
            if initial is None or baseline is None:
                continue
            delta = (initial - baseline) / scale
            if float(np.linalg.norm(delta)) > maximum + 1e-12:
                continue
            ys: dict[str, np.ndarray] = {}
            for checkpoint in outputs:
                observed = _checkpoint_y(row, checkpoint)
                control = _checkpoint_y(reference, checkpoint)
                if observed is None or control is None:
                    break
                ys[checkpoint] = (observed - control) / scale
            if len(ys) != len(outputs):
                continue
            inputs.append(delta)
            for checkpoint, value in ys.items():
                outputs[checkpoint].append(value)
            metadata.append(
                {
                    "source_task_id": str(row["task_id"]),
                    "switched": bool(metric.get("switched")),
                    "contraction_ratio": metric.get("contraction_ratio"),
                }
            )
    return np.asarray(inputs, dtype=float), {
        key: np.asarray(value, dtype=float) for key, value in outputs.items()
    }, metadata


def _switch_direction(
    task_id: str,
    config: Mapping[str, Any],
    parent: Path,
    scale: np.ndarray,
    fallback: np.ndarray,
) -> np.ndarray:
    records, metrics = _parent_dynamic_records(parent)
    no_ops = _parent_no_op_map(parent)
    x: list[np.ndarray] = []
    targets: list[float] = []
    for row in records:
        if (
            not row.get("valid")
            or str(row.get("memory_task_id")) != str(task_id)
            or int(row.get("seed_index", -1)) not in config["discovery_seed_indices"]
        ):
            continue
        metric = metrics.get(str(row["task_id"]))
        if not metric or not metric.get("valid"):
            continue
        reference = no_ops[(str(task_id), int(row["seed_index"]), str(row["arm"]))]
        source = _checkpoint_y(row, "0")
        baseline = _checkpoint_y(reference, "0")
        if source is None or baseline is None:
            continue
        x.append((source - baseline) / scale)
        ratio = metric.get("contraction_ratio")
        targets.append(
            2.0
            if metric.get("switched")
            else min(float(ratio), 4.0) / 4.0 if ratio is not None else 1.0
        )
    if len(x) < 2 or float(np.std(targets)) <= 1e-12:
        return _unit(fallback)
    inputs = np.asarray(x, dtype=float)
    target = np.asarray(targets, dtype=float) - float(np.mean(targets))
    beta = np.linalg.solve(
        inputs.T @ inputs + 1e-6 * np.eye(inputs.shape[1]), inputs.T @ target
    )
    return _unit(beta, fallback=fallback)


def build_finite_time_models(
    config: Mapping[str, Any], parent: Path, structural: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    structural_map = {str(row["memory_task_id"]): row for row in structural["models"]}
    no_ops = _parent_no_op_map(parent)
    models: list[dict[str, Any]] = []
    mode_models: list[dict[str, Any]] = []
    fit = config["finite_time_fit"]
    for task_id in config["focal_task_ids"]:
        structure = structural_map[str(task_id)]
        scale = np.asarray(structure["scale"], dtype=float)
        axes: list[np.ndarray] = []
        separations: list[float] = []
        for seed in config["discovery_seed_indices"]:
            low = _state(no_ops[(str(task_id), int(seed), "low")])
            high = _state(no_ops[(str(task_id), int(seed), "high")])
            delta = (high.y - low.y) / scale
            separations.append(float(np.linalg.norm(delta)))
            axes.append(_unit(delta))
        separation = float(np.median(separations))
        axis = _unit(np.mean(np.asarray(axes), axis=0))
        basis = np.asarray(structure["structural_invariant_basis"], dtype=float).reshape(
            len(axis), -1
        )
        complement = orthogonal_complement(basis, len(axis))
        arm_models: list[dict[str, Any]] = []
        final_maps: list[np.ndarray] = []
        for arm in ("low", "high"):
            x, outputs, _ = _fit_samples(
                str(task_id), arm, config, parent, scale, separation
            )
            checkpoint_models: list[dict[str, Any]] = []
            for checkpoint in ("250", "2500", "12500"):
                if len(x) < 2:
                    matrix = np.eye(len(axis), dtype=float)
                    model = {
                        "matrix": matrix,
                        "selected_ridge": None,
                        "candidate_scores": [],
                        "sample_count": int(len(x)),
                        "condition_number": None,
                        "training_relative_error": None,
                    }
                else:
                    model = fit_linear_map(
                        x,
                        outputs[checkpoint],
                        fit["ridge_candidates"],
                        int(fit["fold_count"]),
                    )
                    matrix = np.asarray(model["matrix"], dtype=float)
                checkpoint_models.append({"checkpoint": checkpoint, **model})
                if checkpoint == "12500":
                    final_maps.append(matrix)
            arm_models.append({"arm": arm, "checkpoint_models": checkpoint_models})
        pooled = np.mean(np.asarray(final_maps), axis=0)
        reduced = complement.T @ pooled @ complement
        _, gains, vh = np.linalg.svd(reduced, full_matrices=True)
        fastest = _unit(complement @ vh[-1], fallback=axis)
        slowest = _unit(complement @ vh[0], fallback=axis)
        if basis.shape[1]:
            projected = basis @ (basis.T @ axis)
            invariant = _unit(projected, fallback=basis[:, 0])
        else:
            invariant = _unit(structure["weakest_structural_direction"])
        switch = _switch_direction(str(task_id), config, parent, scale, slowest)
        plane_source = switch if str(task_id) == str(config["contrast_task_id"]) else invariant
        transverse = plane_source - float(np.dot(plane_source, axis)) * axis
        if float(np.linalg.norm(transverse)) <= 1e-8:
            transverse = slowest - float(np.dot(slowest, axis)) * axis
        transverse = _unit(transverse, fallback=fastest)
        directions = {
            "invariant-memory-aligned": invariant,
            "fastest-contracting": fastest,
            "slowest-non-invariant": slowest,
            "switch-predictive": switch,
        }
        models.append(
            {
                "memory_task_id": str(task_id),
                "separation": separation,
                "arm_models": arm_models,
                "reduced_final_singular_values": gains,
            }
        )
        mode_models.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(structure["model_id"]),
                "scale": scale,
                "separation": separation,
                "memory_axis": axis,
                "structural_invariant_basis": basis,
                "structural_invariant_dimension": int(basis.shape[1]),
                "memory_axis_invariant_fraction": float(
                    structure["memory_axis_invariant_fraction"]
                ),
                "directions": [
                    {"direction_kind": name, "vector": directions[name]}
                    for name in config["directions"]
                ],
                "plane_axis": axis,
                "plane_transverse": transverse,
                "plane_transverse_source": (
                    "switch-predictive"
                    if str(task_id) == str(config["contrast_task_id"])
                    else "invariant-memory-aligned"
                ),
                "frozen_from_discovery_seeds": list(config["discovery_seed_indices"]),
            }
        )
    return (
        {
            "task_id": "finite-time-models",
            "outcome_leakage_allowed": False,
            "models": models,
        },
        {
            "task_id": "mode-models",
            "frozen_before_validation_assays": True,
            "outcome_leakage_allowed": False,
            "models": mode_models,
        },
    )


def _task_resources(
    config: Mapping[str, Any],
    parent: Path,
    atlas: Path,
    upstream: Path,
    task_id: str,
) -> tuple[Any, JaxBackend, int, dict[tuple[str, int, str], dict[str, Any]]]:
    released = load_released_task(upstream, str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
    reconstructed = int(
        _calibration_map(atlas)[str(task_id)]["reconstructed_ucs_bound_index"]
    )
    return memory, backend, reconstructed, _parent_no_op_map(parent)


def _inward_direction(
    base: State,
    direction: Sequence[float],
    scale: np.ndarray,
    bounds: np.ndarray,
    tolerance: float = 1e-8,
) -> tuple[np.ndarray, float, int]:
    vector = np.asarray(direction, dtype=float).copy()
    vector = _unit(vector)
    position = (base.y - bounds[:, 0]) / scale
    positive = maximum_feasible_radius(position, vector, tolerance=tolerance)
    negative = maximum_feasible_radius(position, -vector, tolerance=tolerance)
    if negative > positive + 1e-12:
        return -vector, float(negative), -1
    return vector, float(positive), 1


def _invalid_dynamic_record(
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
        **fields,
    }


def _no_op_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, parent_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_memory_manifold_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "no-op", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    memory, backend, reconstructed, parent_map = _task_resources(
        config,
        Path(parent_path),
        Path(atlas_path),
        Path(upstream_path),
        str(task_id),
    )
    references = {
        arm: np.asarray(parent_map[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        parent_row = parent_map[(str(task_id), int(seed_index), arm)]
        result, used_cpu, used_wall = _finish_record(
            backend,
            memory,
            reconstructed,
            config,
            _state(parent_row),
            references["high"],
            references["low"],
        )
        cpu += used_cpu
        wall += used_wall
        fp_distance = (
            None
            if result.get("fingerprint") is None
            else vector_rms(np.asarray(result["fingerprint"], dtype=float) - references[arm])
        )
        score = result.get("bipolar_score")
        correct = bool(
            score is not None
            and ((arm == "low" and float(score) < 0.0) or (arm == "high" and float(score) > 0.0))
        )
        records.append(
            {
                "task_id": f"manifold-no-op|{task_id}|{seed_index}|{arm}",
                "condition_id": f"no-op|{arm}",
                "assay": "no-op",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "seed_role": (
                    "discovery"
                    if int(seed_index) in config["discovery_seed_indices"]
                    else "validation"
                ),
                "arm": arm,
                "source_fingerprint_distance": fp_distance,
                "correct_source_arm": correct,
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


def _targeted_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, parent_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_memory_manifold_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "targeted-rays", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    memory, backend, reconstructed, parent_map = _task_resources(
        config,
        Path(parent_path),
        Path(atlas_path),
        Path(upstream_path),
        str(task_id),
    )
    model = _model_map(output / "mode-models.json")[str(task_id)]
    scale = np.asarray(model["scale"], dtype=float)
    bounds = np.asarray(memory.bounds, dtype=float)
    directions = {
        str(row["direction_kind"]): np.asarray(row["vector"], dtype=float)
        for row in model["directions"]
    }
    states = {
        arm: _state(parent_map[(str(task_id), int(seed_index), arm)])
        for arm in ("low", "high")
    }
    references = {
        arm: np.asarray(parent_map[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    separation = float(np.linalg.norm((states["high"].y - states["low"].y) / scale))
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        for direction_kind in config["directions"]:
            direction, feasible_radius, sign = _inward_direction(
                states[arm], directions[str(direction_kind)], scale, bounds
            )
            for fraction in config["radial_fractions_of_separation"]:
                fraction = float(fraction)
                radius = fraction * separation
                condition_id = f"targeted|{arm}|{direction_kind}|r={fraction:.4f}"
                common = {
                    "assay": "targeted-ray",
                    "arm": arm,
                    "direction_kind": str(direction_kind),
                    "direction_sign": int(sign),
                    "direction": direction,
                    "radius_fraction": fraction,
                    "requested_radius": radius,
                    "maximum_feasible_radius": feasible_radius,
                }
                start, actual = apply_standardized_direction(
                    states[arm], direction, radius, scale, bounds, 1e-8
                )
                if start is None:
                    records.append(
                        _invalid_dynamic_record(
                            str(task_id),
                            int(seed_index),
                            condition_id,
                            "source-enclosing-envelope-exceeded",
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
                    references["high"],
                    references["low"],
                )
                cpu += used_cpu
                wall += used_wall
                records.append(
                    {
                        "task_id": f"targeted|{task_id}|{seed_index}|{arm}|{direction_kind}|{fraction:.4f}",
                        "condition_id": condition_id,
                        "memory_task_id": str(task_id),
                        "model_id": int(memory.key.model_id),
                        "seed_index": int(seed_index),
                        "seed_role": (
                            "discovery"
                            if int(seed_index) in config["discovery_seed_indices"]
                            else "validation"
                        ),
                        "actual_standardized_norm": actual,
                        **common,
                        **result,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "targeted-rays",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _plane_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, parent_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_memory_manifold_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "mode-plane", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    memory, backend, _, parent_map = _task_resources(
        config,
        Path(parent_path),
        Path(atlas_path),
        Path(upstream_path),
        str(task_id),
    )
    model = _model_map(output / "mode-models.json")[str(task_id)]
    scale = np.asarray(model["scale"], dtype=float)
    bounds = np.asarray(memory.bounds, dtype=float)
    transverse = np.asarray(model["plane_transverse"], dtype=float)
    states = {
        arm: _state(parent_map[(str(task_id), int(seed_index), arm)])
        for arm in ("low", "high")
    }
    separation = float(np.linalg.norm((states["high"].y - states["low"].y) / scale))
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    angle_count = int(config["mode_plane"]["angle_count"])
    for arm in ("low", "high"):
        axial = _unit(
            ((states["high"].y - states["low"].y) / scale)
            if arm == "low"
            else ((states["low"].y - states["high"].y) / scale)
        )
        arm_transverse = transverse - float(np.dot(transverse, axial)) * axial
        arm_transverse = _unit(arm_transverse)
        for angle_index in range(angle_count):
            angle = 2.0 * math.pi * float(angle_index) / float(angle_count)
            raw = math.cos(angle) * axial + math.sin(angle) * arm_transverse
            direction, feasible_radius, sign = _inward_direction(
                states[arm], raw, scale, bounds
            )
            for fraction in config["radial_fractions_of_separation"]:
                fraction = float(fraction)
                radius = fraction * separation
                condition_id = f"plane|{arm}|angle={angle_index}|r={fraction:.4f}"
                common = {
                    "assay": "mode-plane",
                    "arm": arm,
                    "angle_index": int(angle_index),
                    "angle_radians": angle,
                    "direction_sign": int(sign),
                    "direction": direction,
                    "radius_fraction": fraction,
                    "requested_radius": radius,
                    "maximum_feasible_radius": feasible_radius,
                    "plane_transverse_source": str(model["plane_transverse_source"]),
                }
                start, actual = apply_standardized_direction(
                    states[arm], direction, radius, scale, bounds, 1e-8
                )
                if start is None:
                    records.append(
                        _invalid_dynamic_record(
                            str(task_id),
                            int(seed_index),
                            condition_id,
                            "source-enclosing-envelope-exceeded",
                            **common,
                        )
                    )
                    continue
                terminal, checkpoints, used_cpu, used_wall, valid = _release_path(
                    backend, start, memory, config
                )
                cpu += used_cpu
                wall += used_wall
                records.append(
                    {
                        "task_id": f"plane|{task_id}|{seed_index}|{arm}|{angle_index}|{fraction:.4f}",
                        "condition_id": condition_id,
                        "memory_task_id": str(task_id),
                        "model_id": int(memory.key.model_id),
                        "seed_index": int(seed_index),
                        "seed_role": (
                            "discovery"
                            if int(seed_index) in config["discovery_seed_indices"]
                            else "validation"
                        ),
                        "actual_standardized_norm": actual,
                        "source_state": state_payload(start),
                        "terminal_state": state_payload(terminal),
                        "checkpoints": checkpoints,
                        "resting_response": float(terminal.y[memory.key.response_id]),
                        "fingerprint": None,
                        "bipolar_score": None,
                        "valid": bool(valid),
                        **common,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "mode-plane",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def recovery_metrics(
    records: Sequence[Mapping[str, Any]],
    no_ops: Sequence[Mapping[str, Any]],
    structural: Mapping[str, Any],
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    references = {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["arm"])): row
        for row in no_ops
    }
    structural_map = {
        str(row["memory_task_id"]): row for row in structural["models"]
    }
    settings = config["decision"]
    metrics: list[dict[str, Any]] = []
    for row in records:
        common = {
            key: row.get(key)
            for key in (
                "assay",
                "arm",
                "direction_kind",
                "angle_index",
                "radius_fraction",
                "requested_radius",
                "selection_slot",
                "selected_plane_task_id",
            )
            if key in row
        }
        metric: dict[str, Any] = {
            "task_id": f"metric|{row['task_id']}",
            "source_task_id": str(row["task_id"]),
            "memory_task_id": str(row["memory_task_id"]),
            "seed_index": int(row["seed_index"]),
            "seed_role": row.get("seed_role"),
            "valid": False,
            "full_contraction_ratio": None,
            "quotient_contraction_ratio": None,
            "quotient_returned": False,
            "full_returned": False,
            "functional_returned": False,
            "same_arm": False,
            "switched": False,
            "same_arm_geometric": False,
            "switched_geometric": False,
            **common,
        }
        if not row.get("valid"):
            metric["reason"] = row.get("reason", "invalid-dynamic-record")
            metrics.append(metric)
            continue
        key = (
            str(row["memory_task_id"]),
            int(row["seed_index"]),
            str(row["arm"]),
        )
        reference = references.get(key)
        opposite_arm = "high" if key[2] == "low" else "low"
        opposite = references.get((key[0], key[1], opposite_arm))
        if reference is None or opposite is None or not reference.get("valid"):
            metric["reason"] = "matched-no-op-unavailable"
            metrics.append(metric)
            continue
        structure = structural_map[key[0]]
        scale = np.asarray(structure["scale"], dtype=float)
        basis = np.asarray(structure["structural_invariant_basis"], dtype=float).reshape(
            len(scale), -1
        )

        def quotient(vector: np.ndarray) -> np.ndarray:
            return vector if basis.shape[1] == 0 else vector - basis @ (basis.T @ vector)

        distances: dict[str, dict[str, float | None]] = {}
        for checkpoint in CHECKPOINT_KEYS:
            observed = _checkpoint_y(row, checkpoint)
            control = _checkpoint_y(reference, checkpoint)
            if observed is None or control is None:
                distances[checkpoint] = {"full": None, "quotient": None}
                continue
            delta = (observed - control) / scale
            distances[checkpoint] = {
                "full": float(np.linalg.norm(delta)),
                "quotient": float(np.linalg.norm(quotient(delta))),
            }
        initial_full = distances["0"]["full"]
        final_full = distances["12500"]["full"]
        initial_q = distances["0"]["quotient"]
        final_q = distances["12500"]["quotient"]
        full_ratio = (
            None
            if initial_full is None or final_full is None or initial_full <= 1e-12
            else float(final_full / initial_full)
        )
        quotient_ratio = (
            None
            if initial_q is None or final_q is None or initial_q <= 1e-12
            else float(final_q / initial_q)
        )
        absolute = float(settings["absolute_quotient_distance_max"])
        quotient_returned = bool(
            initial_q is not None
            and final_q is not None
            and final_q
            <= float(settings["contraction_ratio_max"]) * initial_q + absolute
        )
        full_returned = bool(
            full_ratio is not None
            and full_ratio <= float(settings["contraction_ratio_max"])
        )
        final_y = _checkpoint_y(row, "12500")
        source_y = _checkpoint_y(reference, "12500")
        opposite_y = _checkpoint_y(opposite, "12500")
        source_distance = opposite_distance = None
        if final_y is not None and source_y is not None and opposite_y is not None:
            source_distance = float(np.linalg.norm((final_y - source_y) / scale))
            opposite_distance = float(np.linalg.norm((final_y - opposite_y) / scale))
        same_geometric = bool(
            source_distance is not None
            and opposite_distance is not None
            and source_distance <= opposite_distance
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
            and ((arm == "low" and float(score) < 0.0) or (arm == "high" and float(score) > 0.0))
        )
        switched = bool(
            score is not None
            and ((arm == "low" and float(score) > 0.0) or (arm == "high" and float(score) < 0.0))
        )
        functional = bool(
            fp_distance is not None
            and fp_distance <= float(settings["fingerprint_rms_max"])
            and same_arm
        )
        metric.update(
            {
                "valid": True,
                "checkpoint_distances": distances,
                "initial_full_distance": initial_full,
                "final_full_distance": final_full,
                "initial_quotient_distance": initial_q,
                "final_quotient_distance": final_q,
                "full_contraction_ratio": full_ratio,
                "quotient_contraction_ratio": quotient_ratio,
                "quotient_returned": quotient_returned,
                "full_returned": full_returned,
                "fingerprint_rms_from_no_op": fp_distance,
                "functional_returned": functional,
                "same_arm": same_arm,
                "switched": switched,
                "terminal_distance_to_source_arm": source_distance,
                "terminal_distance_to_opposite_arm": opposite_distance,
                "same_arm_geometric": same_geometric,
                "switched_geometric": bool(
                    source_distance is not None
                    and opposite_distance is not None
                    and opposite_distance < source_distance
                ),
            }
        )
        metrics.append(metric)
    return metrics


def build_plane_selections(
    plane_metrics: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    selections: list[dict[str, Any]] = []
    lower = float(config["decision"]["persistent_ratio_min"])
    upper = float(config["decision"]["persistent_ratio_max"])
    for task_id in config["focal_task_ids"]:
        for seed_index in config["all_seed_indices"]:
            for arm in ("low", "high"):
                rows = [
                    row
                    for row in plane_metrics
                    if row.get("valid")
                    and str(row["memory_task_id"]) == str(task_id)
                    and int(row["seed_index"]) == int(seed_index)
                    and str(row.get("arm")) == arm
                ]
                used: set[str] = set()

                def choose(slot: str) -> Mapping[str, Any] | None:
                    available = [row for row in rows if str(row["source_task_id"]) not in used]
                    if not available:
                        return None
                    if slot == "strongest-quotient-recovery":
                        ranked = sorted(
                            available,
                            key=lambda row: (
                                not bool(row.get("quotient_returned") and row.get("same_arm_geometric")),
                                -float(row.get("radius_fraction") or 0.0),
                                float(row.get("quotient_contraction_ratio") or math.inf),
                                int(row.get("angle_index") or 0),
                            ),
                        )
                    elif slot == "first-geometric-boundary":
                        switched = [row for row in available if row.get("switched_geometric")]
                        ranked = (
                            sorted(
                                switched,
                                key=lambda row: (
                                    float(row.get("radius_fraction") or math.inf),
                                    int(row.get("angle_index") or 0),
                                ),
                            )
                            if switched
                            else sorted(
                                available,
                                key=lambda row: (
                                    -float(row.get("terminal_distance_to_source_arm") or 0.0)
                                    + float(row.get("terminal_distance_to_opposite_arm") or math.inf),
                                    int(row.get("angle_index") or 0),
                                ),
                            )
                        )
                    else:
                        ranked = sorted(
                            available,
                            key=lambda row: (
                                not bool(
                                    row.get("quotient_returned")
                                    and row.get("full_contraction_ratio") is not None
                                    and lower
                                    <= float(row["full_contraction_ratio"])
                                    <= upper
                                ),
                                abs(float(row.get("full_contraction_ratio") or math.inf) - 1.0),
                                -float(row.get("radius_fraction") or 0.0),
                                int(row.get("angle_index") or 0),
                            ),
                        )
                    return ranked[0]

                for slot in config["mode_plane"]["selection_slots"]:
                    selected = choose(str(slot))
                    if selected is not None:
                        used.add(str(selected["source_task_id"]))
                    selections.append(
                        {
                            "memory_task_id": str(task_id),
                            "seed_index": int(seed_index),
                            "arm": arm,
                            "selection_slot": str(slot),
                            "selected_plane_task_id": (
                                None if selected is None else str(selected["source_task_id"])
                            ),
                            "selection_metric_task_id": (
                                None if selected is None else str(selected["task_id"])
                            ),
                        }
                    )
    return {
        "task_id": "mode-plane-selections",
        "selection_rule_frozen": True,
        "manual_selection_allowed": False,
        "selections": selections,
    }


def _confirmation_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, parent_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_memory_manifold_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "confirmations", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    memory, backend, reconstructed, parent_map = _task_resources(
        config,
        Path(parent_path),
        Path(atlas_path),
        Path(upstream_path),
        str(task_id),
    )
    selection_payload = json.loads(
        (output / "mode-plane-selections.json").read_text(encoding="utf-8")
    )
    selected = [
        row
        for row in selection_payload["selections"]
        if str(row["memory_task_id"]) == str(task_id)
        and int(row["seed_index"]) == int(seed_index)
    ]
    plane = {str(row["task_id"]): dict(row) for row in read_jsonl(output / "mode-plane.jsonl")}
    references = {
        arm: np.asarray(parent_map[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for selection in selected:
        arm = str(selection["arm"])
        slot = str(selection["selection_slot"])
        selected_id = selection.get("selected_plane_task_id")
        condition_id = f"confirmation|{arm}|{slot}"
        if selected_id is None or str(selected_id) not in plane:
            records.append(
                _invalid_dynamic_record(
                    str(task_id),
                    int(seed_index),
                    condition_id,
                    "plane-selection-unavailable",
                    assay="confirmation",
                    arm=arm,
                    selection_slot=slot,
                    selected_plane_task_id=selected_id,
                )
            )
            continue
        source = plane[str(selected_id)]
        terminal = state_from_payload(source["terminal_state"])
        fp = _fingerprint(backend, memory, terminal, config, reconstructed)
        score = bipolar_score(fp["fingerprint"], references["high"], references["low"])
        cpu += float(fp["cpu_seconds"])
        wall += float(fp["wall_seconds"])
        records.append(
            {
                "task_id": f"confirmation|{task_id}|{seed_index}|{arm}|{slot}",
                "condition_id": condition_id,
                "assay": "confirmation",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "seed_role": (
                    "discovery"
                    if int(seed_index) in config["discovery_seed_indices"]
                    else "validation"
                ),
                "arm": arm,
                "selection_slot": slot,
                "selected_plane_task_id": str(selected_id),
                "angle_index": source.get("angle_index"),
                "radius_fraction": source.get("radius_fraction"),
                "requested_radius": source.get("requested_radius"),
                "source_state": source["source_state"],
                "terminal_state": source["terminal_state"],
                "checkpoints": source["checkpoints"],
                "resting_response": source["resting_response"],
                "fingerprint": fp["fingerprint"],
                "raw_fingerprint": fp["raw_fingerprint"],
                "bipolar_score": score,
                "valid": bool(fp["valid"] and score is not None),
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "confirmations",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _fraction_summary(
    rows: Sequence[Mapping[str, Any]], expected_count: int, predicate: Any
) -> dict[str, Any]:
    valid = [row for row in rows if row.get("valid")]
    passed = [row for row in valid if bool(predicate(row))]
    fraction = None if not valid else float(len(passed) / len(valid))
    return {
        "registered_count": len(rows),
        "valid_count": len(valid),
        "pass_count": len(passed),
        "pass_fraction": fraction,
        "complete": len(rows) == int(expected_count) and len(valid) == int(expected_count),
    }


def source_decision(
    no_ops: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    threshold = float(config["decision"]["fingerprint_rms_max"])
    summaries: list[dict[str, Any]] = []
    for task_id in config["focal_task_ids"]:
        rows = [row for row in no_ops if str(row["memory_task_id"]) == str(task_id)]
        passing = [
            row
            for row in rows
            if row.get("valid")
            and row.get("correct_source_arm")
            and row.get("source_fingerprint_distance") is not None
            and float(row["source_fingerprint_distance"]) <= threshold
        ]
        passed = len(rows) == 2 * len(config["all_seed_indices"]) and len(passing) == len(rows)
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "registered_count": len(rows),
                "valid_reproduced_count": len(passing),
                "maximum_fingerprint_rms": (
                    max(float(row["source_fingerprint_distance"]) for row in passing)
                    if passing
                    else None
                ),
                "pass": bool(passed),
            }
        )
    return {
        "task_id": "source-decision",
        "candidate_summaries": summaries,
        "pass": all(bool(row["pass"]) for row in summaries),
    }


def manifold_decision(
    metrics: Sequence[Mapping[str, Any]],
    confirmations: Sequence[Mapping[str, Any]],
    structural: Mapping[str, Any],
    source: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["decision"]
    minimum = float(settings["minimum_recovery_fraction"])
    persistent_low = float(settings["persistent_ratio_min"])
    persistent_high = float(settings["persistent_ratio_max"])
    structural_map = {
        str(row["memory_task_id"]): row for row in structural["models"]
    }
    source_map = {
        str(row["memory_task_id"]): row for row in source["candidate_summaries"]
    }
    target = [
        row
        for row in metrics
        if row.get("assay") == "targeted-ray"
        and row.get("seed_role") == "validation"
    ]
    confirmation_switch: dict[str, float | None] = {}
    for task_id in config["focal_task_ids"]:
        rows = [
            row
            for row in confirmations
            if row.get("valid")
            and str(row["memory_task_id"]) == str(task_id)
            and row.get("seed_role") == "validation"
        ]
        switched = 0
        for row in rows:
            score = row.get("bipolar_score")
            arm = str(row.get("arm"))
            switched += int(
                score is not None
                and ((arm == "low" and float(score) > 0.0) or (arm == "high" and float(score) < 0.0))
            )
        confirmation_switch[str(task_id)] = None if not rows else switched / len(rows)
    summaries: list[dict[str, Any]] = []
    for task_id in config["focal_task_ids"]:
        structure = structural_map[str(task_id)]
        radius_rows: list[dict[str, Any]] = []
        for fraction in config["radial_fractions_of_separation"]:
            fraction = float(fraction)
            arms: dict[str, Any] = {}
            for arm in ("low", "high"):
                rows = [
                    row
                    for row in target
                    if str(row["memory_task_id"]) == str(task_id)
                    and str(row.get("arm")) == arm
                    and math.isclose(float(row.get("radius_fraction", -1.0)), fraction)
                ]
                stable_rows = [
                    row
                    for row in rows
                    if row.get("direction_kind")
                    in {"fastest-contracting", "slowest-non-invariant"}
                ]
                neutral_rows = [
                    row
                    for row in rows
                    if row.get("direction_kind") == "invariant-memory-aligned"
                ]
                point_rows = stable_rows + neutral_rows
                stable = _fraction_summary(
                    stable_rows,
                    2 * len(config["validation_seed_indices"]),
                    lambda row: row.get("quotient_returned")
                    and row.get("functional_returned"),
                )
                neutral = _fraction_summary(
                    neutral_rows,
                    len(config["validation_seed_indices"]),
                    lambda row: row.get("quotient_returned")
                    and row.get("functional_returned")
                    and row.get("full_contraction_ratio") is not None
                    and persistent_low
                    <= float(row["full_contraction_ratio"])
                    <= persistent_high,
                )
                point = _fraction_summary(
                    point_rows,
                    3 * len(config["validation_seed_indices"]),
                    lambda row: row.get("full_returned")
                    and row.get("functional_returned"),
                )
                observer = _fraction_summary(
                    stable_rows,
                    2 * len(config["validation_seed_indices"]),
                    lambda row: row.get("functional_returned"),
                )
                switch = _fraction_summary(
                    rows,
                    len(config["directions"]) * len(config["validation_seed_indices"]),
                    lambda row: row.get("switched"),
                )
                for summary in (stable, neutral, point, observer):
                    summary["pass"] = bool(
                        summary["complete"]
                        and summary["pass_fraction"] is not None
                        and float(summary["pass_fraction"]) >= minimum
                    )
                switch["pass"] = bool(
                    switch["valid_count"] >= 4
                    and switch["pass_fraction"] is not None
                    and float(switch["pass_fraction"])
                    >= float(settings["switch_fraction_min"])
                )
                arms[arm] = {
                    "stable_quotient_recovery": stable,
                    "neutral_persistence": neutral,
                    "point_recovery": point,
                    "functional_recovery": observer,
                    "switching": switch,
                }
            radius_rows.append(
                {
                    "radius_fraction": fraction,
                    "arms": arms,
                    "stable_gate": bool(
                        arms["low"]["stable_quotient_recovery"]["pass"]
                        and arms["high"]["stable_quotient_recovery"]["pass"]
                    ),
                    "neutral_gate": bool(
                        arms["low"]["neutral_persistence"]["pass"]
                        and arms["high"]["neutral_persistence"]["pass"]
                    ),
                    "point_gate": bool(
                        arms["low"]["point_recovery"]["pass"]
                        and arms["high"]["point_recovery"]["pass"]
                    ),
                    "observer_gate": bool(
                        arms["low"]["functional_recovery"]["pass"]
                        and arms["high"]["functional_recovery"]["pass"]
                    ),
                    "switch_gate": bool(
                        arms["low"]["switching"]["pass"]
                        or arms["high"]["switching"]["pass"]
                    ),
                }
            )
        manifold = any(row["stable_gate"] and row["neutral_gate"] for row in radius_rows)
        neutral = any(row["neutral_gate"] for row in radius_rows)
        point = any(row["point_gate"] for row in radius_rows)
        observer = any(row["observer_gate"] and not row["stable_gate"] for row in radius_rows)
        switching = any(row["switch_gate"] for row in radius_rows)
        overlap = float(structure["memory_axis_invariant_fraction"])
        source_valid = bool(source_map[str(task_id)]["pass"])
        if not source_valid:
            classification = "source-reproduction-failed"
        elif point:
            classification = "point-attractor-compatible"
        elif neutral and overlap >= float(config["structural"]["passive_axis_overlap_min"]):
            classification = "passive-neutral-register"
        elif manifold and overlap < float(config["structural"]["passive_axis_overlap_min"]):
            classification = "normally-attracting-memory-manifold"
        elif observer:
            classification = "observer-equivalent-sheet"
        elif bool(structure["no_local_positive_mode"]) and switching:
            classification = "nonlinear-switch-sheet"
        else:
            classification = "mixed-or-unresolved"
        summaries.append(
            {
                "memory_task_id": str(task_id),
                "classification": classification,
                "source_valid": source_valid,
                "structural_invariant_dimension": int(
                    structure["structural_invariant_dimension"]
                ),
                "memory_axis_invariant_fraction": overlap,
                "no_local_positive_mode": bool(structure["no_local_positive_mode"]),
                "point_gate_any_radius": point,
                "manifold_gate_any_radius": manifold,
                "neutral_persistence_any_radius": neutral,
                "observer_only_gate_any_radius": observer,
                "switch_gate_any_radius": switching,
                "confirmed_plane_switch_fraction": confirmation_switch[str(task_id)],
                "per_radius": radius_rows,
            }
        )
    counts: dict[str, int] = {}
    for row in summaries:
        counts[str(row["classification"])] = counts.get(str(row["classification"]), 0) + 1
    return {
        "task_id": "manifold-decision",
        "candidate_summaries": summaries,
        "classification_counts": counts,
        "structural_primary": True,
        "functional_secondary": True,
        "pass": any(
            row["classification"]
            in {
                "normally-attracting-memory-manifold",
                "passive-neutral-register",
                "point-attractor-compatible",
            }
            for row in summaries
        ),
    }


def analyze_memory_manifold(
    output: Path, final_status: str | None = None
) -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    structural = json.loads((output / "structural-census.json").read_text(encoding="utf-8"))
    no_ops = list(read_jsonl(output / "no-op.jsonl"))
    targeted = list(read_jsonl(output / "targeted-rays.jsonl"))
    plane = list(read_jsonl(output / "mode-plane.jsonl"))
    confirmations = list(read_jsonl(output / "confirmations.jsonl"))
    metrics = recovery_metrics(targeted + plane + confirmations, no_ops, structural, config)
    _write_jsonl(output / "recovery-metrics.jsonl", metrics)
    source = source_decision(no_ops, config)
    decision = manifold_decision(metrics, confirmations, structural, source, config)
    write_json(output / "source-decision.json", source)
    write_json(output / "manifold-decision.json", decision)
    structural_leads: list[dict[str, Any]] = []
    for row in structural["models"]:
        overlap = float(row["memory_axis_invariant_fraction"])
        if int(row["structural_invariant_dimension"]) == 0:
            interpretation = "no-common-structural-neutral-subspace"
        elif overlap >= float(config["structural"]["passive_axis_overlap_min"]):
            interpretation = "passive-register-structural-lead"
        else:
            interpretation = "attracting-sheet-structural-lead"
        structural_leads.append(
            {
                "memory_task_id": str(row["memory_task_id"]),
                "structural_invariant_dimension": int(row["structural_invariant_dimension"]),
                "memory_axis_invariant_fraction": overlap,
                "no_local_positive_mode": bool(row["no_local_positive_mode"]),
                "interpretation": interpretation,
            }
        )
    write_json(
        output / "structural-leads.json",
        {"task_id": "structural-leads", "models": structural_leads},
    )
    counts = {
        name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES
    }
    expected = {
        str(key): int(value)
        for key, value in config["registered_record_counts"].items()
    }
    ledger = (
        json.loads((output / "resource-ledger.json").read_text(encoding="utf-8"))
        if (output / "resource-ledger.json").is_file()
        else {}
    )
    complete = bool(
        counts == expected
        and len(metrics)
        == int(config["registered_condition_count"]) - expected["no-op.jsonl"]
    )
    classifications = {
        str(row["memory_task_id"]): str(row["classification"])
        for row in decision["candidate_summaries"]
    }
    verdict = (
        "source-reproduction-failed"
        if not source["pass"]
        else "memory-manifold-leads"
        if decision["pass"]
        else "mixed-switching-and-unresolved-geometry"
    )
    analysis = {
        "task_id": "memory-manifold-analysis",
        "experiment_id": config["experiment_id"],
        "run_status": final_status or "analyzed",
        "minimum_completion_gate": complete,
        "source_valid": bool(source["pass"]),
        "decision_pass": bool(decision["pass"]),
        "verdict": verdict,
        "classifications": classifications,
        "record_counts": counts,
        "recovery_metric_count": len(metrics),
        "active_wall_seconds": float(ledger.get("active_wall_seconds", 0.0)),
        "aggregate_cpu_seconds": float(ledger.get("aggregate_cpu_seconds", 0.0)),
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    rows = "\n".join(
        f"| `{row['memory_task_id']}` | {row['classification']} | "
        f"{row['structural_invariant_dimension']} | {row['memory_axis_invariant_fraction']:.3f} |"
        for row in decision["candidate_summaries"]
    )
    report = f"""# GRN memory manifold V1

Status: **{analysis['run_status']}**

Verdict: **{verdict}**

| Network | Classification | Common neutral dimensions | Memory-axis neutral fraction |
| --- | --- | ---: | ---: |
{rows}

The primary test asks whether displacement contracts after removing neutral directions
identified from the equations alone. The fingerprint assay is a secondary check of whether
that structural recovery restores the network's observable behavior.

In plain language, this distinguishes a restoring landscape with a movable memory coordinate
from a passive register, a conventional point-like valley, and a thin nonlinear switch sheet.

Records: {counts}

Resource use: {analysis['active_wall_seconds']:.3f} active wall seconds and
{analysis['aggregate_cpu_seconds']:.3f} aggregate worker CPU seconds.

Claim boundary: {config['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class MemoryManifoldCampaign:
    def __init__(
        self,
        config_path: Path,
        parent: Path,
        atlas: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_memory_manifold_config(self.config_path)
        self.parent = parent.resolve()
        self.atlas = atlas.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("memory-manifold workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed memory-manifold campaign cannot be resumed")
        self.parent_gate = validate_memory_manifold_parents(
            self.config, self.parent, self.atlas, self.upstream
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
                    raise ValueError(f"resumed memory-manifold registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"].get(
                "container_image_id"
            ):
                raise ValueError("resumed memory-manifold image differs")
        write_json(path, payload)
        write_json(
            self.output / "parent-gate.json",
            {"task_id": "parent-gate", "pass": True, **self.parent_gate},
        )
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "primary": "Exposure states lie on a structurally defined normally attracting manifold.",
                "alternatives": [
                    "The memory axis is mainly a passive neutral register.",
                    "Recovery is point-attractor-like even without quotienting.",
                    "Only the six-probe observer returns.",
                    "Finite perturbations encounter a nonlinear switch sheet.",
                    "No coherent geometry generalizes to held-out seeds.",
                ],
                "structural_quotient_frozen_before_new_outcomes": True,
                "functional_endpoint_secondary": True,
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
            self._require_budget("structural-census")
            cpu_start = time.process_time()
            structural = build_structural_census(
                self.config, self.parent, self.upstream
            )
            finite, modes = build_finite_time_models(
                self.config, self.parent, structural
            )
            static_cpu = time.process_time() - cpu_start
            write_json(self.output / "structural-census.json", structural)
            write_json(self.output / "finite-time-models.json", finite)
            write_json(self.output / "mode-models.json", modes)
            write_json(
                self.output / ".shards" / "static" / "models.json",
                {
                    "protocol_digest": digest(self.config),
                    "stage": "static",
                    "aggregate_cpu_seconds": float(static_cpu),
                    "aggregate_wall_seconds": 0.0,
                    "records": [],
                },
            )
            common_args = [
                (
                    str(self.config_path),
                    str(self.parent),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed_index),
                )
                for task_id in self.config["focal_task_ids"]
                for seed_index in self.config["all_seed_indices"]
            ]
            self._require_budget("no-op")
            no_op_shards = _parallel(_no_op_worker, common_args, self.workers)
            no_ops = _merge_shards(self.output, "no-op", no_op_shards)
            self._require_budget("targeted-rays")
            targeted_shards = _parallel(_targeted_worker, common_args, self.workers)
            targeted = _merge_shards(self.output, "targeted-rays", targeted_shards)
            self._require_budget("mode-plane")
            plane_shards = _parallel(_plane_worker, common_args, self.workers)
            plane = _merge_shards(self.output, "mode-plane", plane_shards)
            self._require_budget("mode-plane-selection")
            preliminary = recovery_metrics(
                targeted + plane, no_ops, structural, self.config
            )
            plane_metrics = [row for row in preliminary if row.get("assay") == "mode-plane"]
            _write_jsonl(self.output / "mode-plane-metrics.jsonl", plane_metrics)
            selections = build_plane_selections(plane_metrics, self.config)
            write_json(self.output / "mode-plane-selections.json", selections)
            self._require_budget("confirmations")
            confirmation_shards = _parallel(
                _confirmation_worker, common_args, self.workers
            )
            _merge_shards(self.output, "confirmations", confirmation_shards)
            self._state("analyzing", "analysis")
            self.ledger.close()
            analysis = analyze_memory_manifold(self.output, final_status="completed")
            if not analysis["minimum_completion_gate"]:
                raise ValueError("memory-manifold registered record set is incomplete")
            self._state("completed", "complete", verdict=analysis["verdict"])
            write_checksums(self.output)
            return 0
        except BaseException as error:
            incidents_path = self.output / "runtime-incidents.json"
            incidents = (
                json.loads(incidents_path.read_text(encoding="utf-8"))
                if incidents_path.is_file()
                else {"incidents": []}
            )
            prior_state = (
                json.loads((self.output / "state.json").read_text(encoding="utf-8"))
                if (self.output / "state.json").is_file()
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
                self.output / "state.json",
                {
                    "status": "failed",
                    "stage": "exception",
                    "workers": self.workers,
                    "error": repr(error),
                    "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
            raise


def run_memory_manifold(
    config: Path,
    parent: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return MemoryManifoldCampaign(
        config, parent, atlas, upstream, output, workers
    ).run()


def smoke_memory_manifold(
    config_path: Path,
    parent: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_memory_manifold_config(config_path)
    parent, atlas, upstream, output = (
        parent.resolve(),
        atlas.resolve(),
        upstream.resolve(),
        output.resolve(),
    )
    if output.exists():
        raise FileExistsError(f"memory-manifold smoke output exists: {output}")
    parents = validate_memory_manifold_parents(config, parent, atlas, upstream)
    static_cpu_start = time.process_time()
    structural = build_structural_census(config, parent, upstream)
    finite, modes = build_finite_time_models(config, parent, structural)
    static_cpu = time.process_time() - static_cpu_start
    output.mkdir(parents=True)
    write_json(output / "structural-census.json", structural)
    write_json(output / "finite-time-models.json", finite)
    write_json(output / "mode-models.json", modes)
    task_id = "37-10-41"
    seed_index = int(config["discovery_seed_indices"][0])
    memory, backend, reconstructed, parent_map = _task_resources(
        config, parent, atlas, upstream, task_id
    )
    model = _model_map(output / "mode-models.json")[task_id]
    scale = np.asarray(model["scale"], dtype=float)
    bounds = np.asarray(memory.bounds, dtype=float)
    low = _state(parent_map[(task_id, seed_index, "low")])
    high = _state(parent_map[(task_id, seed_index, "high")])
    reference_low = np.asarray(parent_map[(task_id, seed_index, "low")]["fingerprint"], dtype=float)
    reference_high = np.asarray(parent_map[(task_id, seed_index, "high")]["fingerprint"], dtype=float)
    no_op, no_op_cpu, no_op_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        low,
        reference_high,
        reference_low,
    )
    directions = {
        str(row["direction_kind"]): np.asarray(row["vector"], dtype=float)
        for row in model["directions"]
    }
    separation = float(np.linalg.norm((high.y - low.y) / scale))
    fraction = float(config["radial_fractions_of_separation"][0])
    direction, _, _ = _inward_direction(
        low, directions["fastest-contracting"], scale, bounds
    )
    targeted_start, _ = apply_standardized_direction(
        low, direction, fraction * separation, scale, bounds, 1e-8
    )
    if targeted_start is None:
        raise ValueError("smoke targeted direction is infeasible")
    targeted, target_cpu, target_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        targeted_start,
        reference_high,
        reference_low,
    )
    axial, _, _ = _inward_direction(
        low, (high.y - low.y) / scale, scale, bounds
    )
    plane_start, _ = apply_standardized_direction(
        low, axial, fraction * separation, scale, bounds, 1e-8
    )
    if plane_start is None:
        raise ValueError("smoke plane direction is infeasible")
    plane_terminal, _, plane_cpu, plane_wall, plane_valid = _release_path(
        backend, plane_start, memory, config
    )
    fp = _fingerprint(backend, memory, plane_terminal, config, reconstructed)
    confirmation_cpu = float(fp["cpu_seconds"])
    confirmation_wall = float(fp["wall_seconds"])
    counts = config["registered_record_counts"]
    projected_cpu = float(config["projection_safety_factor"]) * (
        float(static_cpu)
        + float(no_op_cpu) * int(counts["no-op.jsonl"])
        + float(target_cpu) * int(counts["targeted-rays.jsonl"])
        + float(plane_cpu) * int(counts["mode-plane.jsonl"])
        + confirmation_cpu * int(counts["confirmations.jsonl"])
    )
    projected_wall = projected_cpu / float(config["max_workers"])
    valid = bool(
        no_op["valid"]
        and targeted["valid"]
        and plane_valid
        and fp["valid"]
    )
    allowed = bool(
        valid
        and sum(int(value) for value in counts.values())
        == int(config["registered_condition_count"])
        and projected_cpu < float(config["soft_aggregate_cpu_seconds"])
        and projected_wall < float(config["soft_wall_seconds"])
    )
    result = {
        "target": "memory-manifold",
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "constrained_parent_manifest_sha256": parents["constrained"]["manifest_sha256"],
        "atlas_parent_manifest_sha256": parents["atlas"]["manifest_sha256"],
        "worker_cap": int(config["max_workers"]),
        "discovery_seed_indices": list(config["discovery_seed_indices"]),
        "validation_seed_indices": list(config["validation_seed_indices"]),
        "biological_probe": {
            "memory_task_id": task_id,
            "seed_index": seed_index,
            "valid": valid,
            "static_cpu_seconds": static_cpu,
            "no_op": {"cpu_seconds": no_op_cpu, "wall_seconds": no_op_wall},
            "targeted": {"cpu_seconds": target_cpu, "wall_seconds": target_wall},
            "mode_plane": {"cpu_seconds": plane_cpu, "wall_seconds": plane_wall},
            "confirmation": {
                "cpu_seconds": confirmation_cpu,
                "wall_seconds": confirmation_wall,
            },
        },
        "projection": {
            "registered_condition_count": int(config["registered_condition_count"]),
            "record_counts": counts,
            "worst_case_aggregate_cpu_seconds": projected_cpu,
            "worst_case_active_wall_seconds_at_four_workers": projected_wall,
            "safety_factor": float(config["projection_safety_factor"]),
            "projection_basis": "measured static, no-op, full targeted, release-only plane, and fingerprint-only confirmation kernels",
        },
        "structural_quotient_frozen_before_new_outcomes": True,
        "deterministic_batch_plan": "stage-by-task-by-seed shards",
    }
    write_json(output / "smoke.json", result)
    return result


def memory_manifold_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {
        "output": str(output),
        "sealed": (output / "SHA256SUMS").is_file(),
    }
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "structural-census",
        "finite-time-models",
        "mode-models",
        "mode-plane-selections",
        "source-decision",
        "manifold-decision",
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
        stage: (
            len(list((output / ".shards" / stage).glob("*.json")))
            if (output / ".shards" / stage).is_dir()
            else 0
        )
        for stage in ("static", "no-op", "targeted-rays", "mode-plane", "confirmations")
    }
    return result
