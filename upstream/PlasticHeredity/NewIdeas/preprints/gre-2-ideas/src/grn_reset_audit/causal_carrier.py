"""Prospective causal transplantation and curved local geometry of GRN memories.

The experiment is deliberately exploratory.  Discovery-only mode-plane states
freeze a compact state-to-behaviour model; untouched exposure seeds are then
used for causal component swaps, matched controls, erase/rescue, and local
tangent/normal perturbations.  Every expensive stage is shard-resumable.
"""

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
from .contingency import (
    _all_shard_cpu,
    _calibration_map,
    _control_tokens,
    _fingerprint,
    _naive_start,
    _parallel,
    _perturb_start,
    _run_history,
    _runtime_manifest,
    _verify_parent,
    bipolar_score,
    cosine_alignment,
    quantile,
    vector_rms,
)
from .engine import JaxBackend, State
from .exposure_autopsy import _merge_shards, _shard
from .memory_manifold import _model_map, _parent_no_op_map, _state, _unit
from .renewal import ResourceLedger
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    validate_upstream,
)


FOCAL_TASKS = ("37-10-41", "204-5-10", "10-1-32")
FRESH_SEEDS = tuple(range(208, 216))
DISCOVERY_SEEDS = (204, 205)
TRANSPLANT_CONDITIONS = (
    "sham",
    "full-state",
    "memory-axis",
    "observer-rank-1",
    "observer-rank-2",
    "observer-rank-4",
    "top-nodes-1",
    "top-nodes-2",
    "top-nodes-3",
    "top-nodes-half",
    "structural-neutral",
    "sheet-tangent",
    "sheet-normal",
    "anti-ranked",
    "random-control-1",
    "random-control-2",
)
RECORD_FILES = (
    "plane-census.jsonl",
    "fresh-exposure.jsonl",
    "no-op.jsonl",
    "carrier-transplants.jsonl",
    "local-geometry.jsonl",
    "erase-rescue.jsonl",
)
EXPECTED_COUNTS = {
    "plane-census.jsonl": 192,
    "fresh-exposure.jsonl": 48,
    "no-op.jsonl": 48,
    "carrier-transplants.jsonl": 768,
    "local-geometry.jsonl": 1536,
    "erase-rescue.jsonl": 48,
}
CHECKPOINT_KEYS = ("0", "250", "2500", "12500")


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(dict(row)) + "\n" for row in records))


def _stable_seed(config: Mapping[str, Any], *parts: object) -> int:
    payload = "|".join([str(config["experiment_seed"]), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def _payload_state(payload: Mapping[str, Any] | None) -> State:
    state = state_from_payload(payload)
    if state is None:
        raise ValueError("invalid state payload")
    return state


def _checkpoint_state(row: Mapping[str, Any], checkpoint: str) -> State | None:
    payload = row.get("checkpoints", {}).get(str(checkpoint), {}).get("state")
    return state_from_payload(payload) if isinstance(payload, Mapping) else None


def _record_map(path: Path, keys: Sequence[str]) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in read_jsonl(path):
        key = tuple(row[name] for name in keys)
        if key in result:
            raise ValueError(f"duplicate record key in {path.name}: {key}")
        result[key] = dict(row)
    return result


def load_causal_carrier_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0" or config.get("experiment_kind") != "causal-carrier-transplant":
        raise ValueError("not a supported causal-carrier protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("causal-carrier protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("causal-carrier protocol does not pin the release generator")
    if tuple(config.get("focal_task_ids", ())) != FOCAL_TASKS:
        raise ValueError("causal-carrier focal cohort changed")
    if tuple(int(value) for value in config.get("discovery_seed_indices", ())) != DISCOVERY_SEEDS:
        raise ValueError("causal-carrier discovery cohort changed")
    if tuple(int(value) for value in config.get("fresh_seed_indices", ())) != FRESH_SEEDS:
        raise ValueError("causal-carrier prospective cohort changed")
    if tuple(config.get("transplant_conditions", ())) != TRANSPLANT_CONDITIONS:
        raise ValueError("causal-carrier transplant controls changed")
    if {str(key): int(value) for key, value in config.get("registered_record_counts", {}).items()} != EXPECTED_COUNTS:
        raise ValueError("causal-carrier registered record counts changed")
    if int(config.get("registered_condition_count", -1)) != sum(EXPECTED_COUNTS.values()):
        raise ValueError("causal-carrier registered condition count changed")
    historical = {
        "delta_t": 0.01,
        "phase_duration": 2500.0,
        "epoch_duration": 250.0,
        "epoch_count": 10.0,
        "pulse_count": 5.0,
        "washout_chunk_duration": 2500.0,
    }
    for key, expected in historical.items():
        if not math.isclose(float(config.get(key, -1.0)), expected):
            raise ValueError(f"causal-carrier historical setting differs for {key}")
    if [float(value) for value in config["release_checkpoints"]] != [0.0, 250.0, 2500.0, 12500.0]:
        raise ValueError("causal-carrier release checkpoints changed")
    geometry = config["local_geometry"]
    if (
        list(geometry["center_types"]) != ["source", "transplanted"]
        or list(geometry["direction_kinds"]) != ["tangent", "normal"]
        or [int(value) for value in geometry["signs"]] != [-1, 1]
        or [float(value) for value in geometry["radius_factors"]] != [0.1, 0.25, 0.5, 1.0]
    ):
        raise ValueError("causal-carrier local geometry grid changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("causal-carrier campaign must cap workers at four")
    if not (
        0.0
        < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 14400.0
    ):
        raise ValueError("causal-carrier wall contract exceeds four hours")
    if not (
        0.0
        < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 57600.0
    ):
        raise ValueError("causal-carrier aggregate CPU contract is invalid")
    return config


def validate_causal_carrier_parents(
    config: Mapping[str, Any],
    manifold: Path,
    constrained: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
) -> dict[str, Any]:
    gates = {
        "upstream": validate_upstream(upstream, str(config["upstream_commit"])),
        "manifold": _verify_parent(
            manifold,
            str(config["manifold_parent_experiment_id"]),
            config["manifold_parent_hashes"],
        ),
        "constrained": _verify_parent(
            constrained,
            str(config["constrained_parent_experiment_id"]),
            config["constrained_parent_hashes"],
        ),
        "contingency": _verify_parent(
            contingency,
            str(config["contingency_parent_experiment_id"]),
            config["contingency_parent_hashes"],
        ),
        "atlas": _verify_parent(
            atlas,
            str(config["atlas_parent_experiment_id"]),
            config["atlas_parent_hashes"],
        ),
    }
    constrained_decision = json.loads((constrained / "decision.json").read_text(encoding="utf-8"))
    contingency_decision = json.loads((contingency / "decision.json").read_text(encoding="utf-8"))
    if not bool(constrained_decision.get("source_valid")):
        raise ValueError("constrained parent failed source reproduction")
    if not bool(contingency_decision.get("stage_passes", {}).get("exposure")):
        raise ValueError("contingency parent lacks a durable exposure-state lead")
    return gates


def _plane_features(row: Mapping[str, Any]) -> np.ndarray:
    angle = float(row.get("angle_radians", 0.0))
    radius = max(float(row.get("radius_fraction", 0.0)), 1e-12)
    return np.asarray([math.cos(angle), math.sin(angle), math.log10(radius)], dtype=float)


def select_diverse_plane_rows(
    rows: Sequence[Mapping[str, Any]], count: int
) -> list[dict[str, Any]]:
    """Prioritize all feasible endpoints, then fill registered null slots.

    Some bound-pinned arms have fewer than sixteen feasible parent endpoints.
    Those arms retain every feasible endpoint; deterministic, diverse
    unavailable rows occupy the remaining registered slots and are explicitly
    recorded as null rather than clipped, duplicated, or rerun.
    """

    all_candidates = [dict(row) for row in rows]
    if len(all_candidates) < int(count):
        raise ValueError(f"only {len(all_candidates)} plane rows for a {count}-slot census")
    all_candidates.sort(key=lambda row: str(row["task_id"]))
    available = [
        row
        for row in all_candidates
        if bool(row.get("valid")) and isinstance(row.get("terminal_state"), Mapping)
    ]

    def select_available(candidates: list[dict[str, Any]], requested: int) -> list[dict[str, Any]]:
        if requested >= len(candidates):
            return list(candidates)
        features = np.asarray([_plane_features(row) for row in candidates], dtype=float)
        scale = np.maximum(np.ptp(features, axis=0), 1e-12)
        features = (features - np.min(features, axis=0)) / scale
        unique_radii = sorted({float(row["radius_fraction"]) for row in candidates})
        seed_count = min(4, int(requested), len(unique_radii))
        radius_indices = np.rint(
            np.linspace(0, len(unique_radii) - 1, seed_count)
        ).astype(int)
        chosen: list[int] = []
        for seed_index, radius_index in enumerate(radius_indices):
            target_radius = unique_radii[int(radius_index)]
            target_angle = 2.0 * math.pi * float(seed_index) / float(seed_count)
            eligible = [
                index
                for index, row in enumerate(candidates)
                if math.isclose(float(row["radius_fraction"]), target_radius)
                and index not in chosen
            ]
            selected = min(
                eligible,
                key=lambda index: (
                    abs(
                        math.atan2(
                            math.sin(float(candidates[index]["angle_radians"]) - target_angle),
                            math.cos(float(candidates[index]["angle_radians"]) - target_angle),
                        )
                    ),
                    str(candidates[index]["task_id"]),
                ),
            )
            chosen.append(selected)
        remaining = set(range(len(candidates))) - set(chosen)
        while len(chosen) < int(requested):
            ranked = []
            for index in remaining:
                distance = min(
                    float(np.linalg.norm(features[index] - features[prior]))
                    for prior in chosen
                )
                ranked.append((distance, str(candidates[index]["task_id"]), index))
            _, _, selected = min(ranked, key=lambda item: (-item[0], item[1]))
            chosen.append(selected)
            remaining.remove(selected)
        return [candidates[index] for index in chosen]

    selected = select_available(available, min(int(count), len(available)))
    if len(selected) == int(count):
        return selected
    unavailable = [row for row in all_candidates if row not in available]
    base_count = len(selected)
    combined_features = np.asarray(
        [_plane_features(row) for row in [*selected, *unavailable]], dtype=float
    )
    feature_scale = np.maximum(np.ptp(combined_features, axis=0), 1e-12)
    normalized = (combined_features - np.min(combined_features, axis=0)) / feature_scale
    chosen_features = list(range(base_count))
    remaining = set(range(base_count, base_count + len(unavailable)))
    while len(selected) < int(count):
        if chosen_features:
            ranked = [
                (
                    min(
                        float(np.linalg.norm(normalized[index] - normalized[prior]))
                        for prior in chosen_features
                    ),
                    str(unavailable[index - base_count]["task_id"]),
                    index,
                )
                for index in remaining
            ]
            _, _, selected_index = min(ranked, key=lambda item: (-item[0], item[1]))
        else:
            selected_index = min(remaining)
        selected.append(unavailable[selected_index - base_count])
        chosen_features.append(selected_index)
        remaining.remove(selected_index)
    return selected


def fit_multioutput_ridge(
    x: Sequence[Sequence[float]],
    y: Sequence[Sequence[float]],
    ridge_candidates: Sequence[float],
    fold_count: int,
) -> dict[str, Any]:
    """Fit an affine multi-output map with deterministic row-stratified CV."""

    inputs = np.asarray(x, dtype=float)
    outputs = np.asarray(y, dtype=float)
    if inputs.ndim != 2 or outputs.ndim != 2 or len(inputs) != len(outputs) or len(inputs) < 4:
        raise ValueError("observer fit requires at least four paired matrix rows")
    x_mean = np.mean(inputs, axis=0)
    y_mean = np.mean(outputs, axis=0)
    xc = inputs - x_mean
    yc = outputs - y_mean
    folds = np.arange(len(inputs)) % max(2, min(int(fold_count), len(inputs)))
    scores: list[dict[str, float]] = []
    for ridge_value in ridge_candidates:
        ridge = float(ridge_value)
        errors: list[float] = []
        for fold in sorted(set(int(value) for value in folds)):
            train = folds != fold
            test = ~train
            local_x_mean = np.mean(inputs[train], axis=0)
            local_y_mean = np.mean(outputs[train], axis=0)
            train_x = inputs[train] - local_x_mean
            train_y = outputs[train] - local_y_mean
            gram = train_x.T @ train_x + ridge * np.eye(inputs.shape[1])
            matrix = np.linalg.solve(gram, train_x.T @ train_y).T
            prediction = (inputs[test] - local_x_mean) @ matrix.T + local_y_mean
            denominator = max(float(np.linalg.norm(outputs[test] - local_y_mean)), 1e-12)
            errors.append(float(np.linalg.norm(prediction - outputs[test]) / denominator))
        scores.append({"ridge": ridge, "relative_cv_error": float(np.mean(errors))})
    selected = min(scores, key=lambda row: (row["relative_cv_error"], row["ridge"]))
    ridge = float(selected["ridge"])
    gram = xc.T @ xc + ridge * np.eye(inputs.shape[1])
    matrix = np.linalg.solve(gram, xc.T @ yc).T
    intercept = y_mean - matrix @ x_mean
    prediction = inputs @ matrix.T + intercept
    return {
        "matrix": matrix,
        "intercept": intercept,
        "input_mean": x_mean,
        "output_mean": y_mean,
        "selected_ridge": ridge,
        "candidate_scores": scores,
        "sample_count": int(len(inputs)),
        "training_relative_error": float(
            np.linalg.norm(prediction - outputs)
            / max(float(np.linalg.norm(outputs - y_mean)), 1e-12)
        ),
    }


def _orthonormal(values: Sequence[Sequence[float]], dimension: int) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.size == 0:
        return np.empty((int(dimension), 0), dtype=float)
    matrix = matrix.reshape(int(dimension), -1)
    q, r = np.linalg.qr(matrix)
    rank = int(np.sum(np.abs(np.diag(r)) > 1e-10))
    q = q[:, :rank]
    for index in range(q.shape[1]):
        q[:, index] = _unit(q[:, index])
    return q


def _project(basis: Sequence[Sequence[float]], vector: Sequence[float]) -> np.ndarray:
    values = np.asarray(vector, dtype=float)
    q = _orthonormal(basis, len(values))
    return np.zeros_like(values) if q.shape[1] == 0 else q @ (q.T @ values)


def _coordinate_basis(indices: Sequence[int], dimension: int) -> np.ndarray:
    basis = np.zeros((int(dimension), len(indices)), dtype=float)
    for column, index in enumerate(indices):
        basis[int(index), column] = 1.0
    return basis


def donor_recipient_envelope(recipient: State, donor: State) -> np.ndarray:
    """Return the smallest coordinate-wise box containing both endpoints."""

    if recipient.y.shape != donor.y.shape:
        raise ValueError("donor and recipient expression states differ in shape")
    return np.column_stack(
        (np.minimum(recipient.y, donor.y), np.maximum(recipient.y, donor.y))
    )


def source_enclosing_envelope(
    state: State, registered_bounds: Sequence[Sequence[float]]
) -> np.ndarray:
    """Return the smallest box containing a source and intervention ranges."""

    bounds = np.asarray(registered_bounds, dtype=float)
    if bounds.shape != (len(state.y), 2):
        raise ValueError("registered bounds differ from the expression-state shape")
    return np.column_stack(
        (np.minimum(state.y, bounds[:, 0]), np.maximum(state.y, bounds[:, 1]))
    )


def _line_fraction(
    origin: np.ndarray,
    standardized_shift: np.ndarray,
    scale: np.ndarray,
    bounds: np.ndarray,
    tolerance: float,
) -> float:
    raw = standardized_shift * scale
    alpha = 1.0
    for value, delta, lower, upper in zip(origin, raw, bounds[:, 0], bounds[:, 1]):
        if value < lower - tolerance or value > upper + tolerance:
            return 0.0
        if delta > 0.0:
            alpha = min(alpha, float(max(0.0, upper - value) / delta))
        elif delta < 0.0:
            alpha = min(alpha, float(max(0.0, value - lower) / -delta))
    alpha = float(max(0.0, min(1.0, alpha)))
    # A limiting ratio can round upward by one ULP when multiplied back into
    # the raw shift. Contract the line coefficient infinitesimally instead of
    # clipping any expression coordinate.
    if 0.0 < alpha < 1.0:
        alpha = float(np.nextafter(alpha, 0.0))
    return alpha


def apply_component_transplant(
    recipient: State,
    donor: State,
    spec: Mapping[str, Any],
    scale: Sequence[float],
    *,
    tolerance: float = 1e-8,
    norm_target: float | None = None,
) -> tuple[State | None, float, float]:
    """Apply a no-clipping transplant within the endpoint-pair envelope.

    Returns ``(state, coefficient_fraction, requested_standardized_norm)``.
    """

    width = np.asarray(scale, dtype=float)
    envelope = donor_recipient_envelope(recipient, donor)
    kind = str(spec["kind"])
    if kind == "sham":
        return recipient.copy(), 1.0, 0.0
    if kind == "full":
        state = State(donor.y.copy(), donor.w.copy(), donor.c.copy(), float(recipient.t))
        return state, 1.0, float(np.linalg.norm((donor.y - recipient.y) / width))
    delta = (donor.y - recipient.y) / width
    if kind == "coordinates":
        indices = [int(value) for value in spec.get("indices", ())]
        if not indices:
            return None, 0.0, 0.0
        requested = float(np.linalg.norm(delta[indices]))
        if requested <= 1e-12:
            return None, 0.0, requested
        if norm_target is not None:
            raise ValueError("norm matching is not defined for exact coordinate replacement")
        y = recipient.y.copy()
        y[indices] = donor.y[indices]
        return (
            State(y, recipient.w.copy(), recipient.c.copy(), float(recipient.t)),
            1.0,
            requested,
        )
    elif kind == "subspace":
        basis = np.asarray(spec.get("basis", ()), dtype=float)
        if basis.size == 0:
            return None, 0.0, 0.0
        shift = _project(basis, delta)
    else:
        raise ValueError(f"unknown component kind: {kind}")
    requested = float(np.linalg.norm(shift))
    if norm_target is not None:
        target = float(norm_target)
        if target <= 1e-12 or requested <= 1e-12:
            return None, 0.0, target
        shift = shift * (target / requested)
        requested = target
    if requested <= 1e-12:
        return None, 0.0, requested
    alpha = _line_fraction(recipient.y, shift, width, envelope, float(tolerance))
    if alpha <= 0.0:
        return None, 0.0, requested
    y = recipient.y + alpha * shift * width
    if np.any(y < envelope[:, 0] - tolerance) or np.any(y > envelope[:, 1] + tolerance):
        raise AssertionError("component transplant escaped bounds without clipping")
    return State(y, recipient.w.copy(), recipient.c.copy(), float(recipient.t)), alpha, requested


def local_radius_cap(
    state: State,
    direction: Sequence[float],
    scale: Sequence[float],
    bounds: Sequence[Sequence[float]],
    separation: float,
    separation_cap_fraction: float,
    feasible_radius_fraction: float,
    tolerance: float = 1e-8,
) -> tuple[np.ndarray, float, float]:
    vector = np.asarray(direction, dtype=float)
    vector_norm = float(np.linalg.norm(vector))
    if vector_norm <= 1e-12 or not np.isfinite(vector_norm):
        raise ValueError("cannot normalize a zero or non-finite local direction")
    # Preserve the registered sign. ``memory_manifold._unit`` canonicalizes
    # signs for unoriented bases and would collapse the + and - local probes.
    vector = vector / vector_norm
    width = np.asarray(scale, dtype=float)
    if width.shape != state.y.shape or np.any(width <= 0.0):
        raise ValueError("scale must be positive and match the expression-state shape")
    envelope = source_enclosing_envelope(state, bounds)
    if np.any(state.y < envelope[:, 0] - tolerance) or np.any(
        state.y > envelope[:, 1] + tolerance
    ):
        raise ValueError("local-geometry center lies outside its source envelope")
    limits: list[float] = []
    for value, component, scale_value, lower, upper in zip(
        state.y, vector, width, envelope[:, 0], envelope[:, 1]
    ):
        delta = float(component * scale_value)
        if component > 1e-14:
            limits.append(max(0.0, float(upper - value)) / delta)
        elif component < -1e-14:
            limits.append(max(0.0, float(value - lower)) / -delta)
    feasible = 0.0 if not limits else float(min(limits))
    cap = min(float(separation_cap_fraction) * float(separation), float(feasible_radius_fraction) * feasible)
    return vector, float(feasible), float(max(0.0, cap))


def _spec_dimension(spec: Mapping[str, Any], node_count: int) -> int:
    if spec["kind"] == "full":
        return int(node_count)
    if spec["kind"] == "coordinates":
        return len(spec.get("indices", ()))
    if spec["kind"] == "subspace":
        values = np.asarray(spec.get("basis", ()), dtype=float)
        return 0 if values.size == 0 else int(_orthonormal(values, node_count).shape[1])
    return 0


def condition_spec(model: Mapping[str, Any], condition: str) -> dict[str, Any]:
    node_count = int(model["node_count"])
    ranked = [int(value) for value in model["ranked_nodes"]]
    half = int(math.ceil(node_count / 2.0))
    if condition == "sham":
        return {"kind": "sham"}
    if condition == "full-state":
        return {"kind": "full"}
    if condition == "memory-axis":
        return {"kind": "subspace", "basis": np.asarray(model["memory_axis"], dtype=float)[:, None]}
    if condition.startswith("observer-rank-"):
        rank = int(condition.rsplit("-", 1)[1])
        return {"kind": "subspace", "basis": np.asarray(model["observer_basis"], dtype=float)[:, :rank]}
    if condition.startswith("top-nodes-"):
        token = condition.rsplit("-", 1)[1]
        size = half if token == "half" else int(token)
        return {"kind": "coordinates", "indices": ranked[:size]}
    if condition == "structural-neutral":
        return {"kind": "subspace", "basis": model["structural_neutral_basis"]}
    if condition == "sheet-tangent":
        return {"kind": "subspace", "basis": model["tangent_basis"]}
    if condition == "sheet-normal":
        return {"kind": "subspace", "basis": np.asarray(model["normal_direction"], dtype=float)[:, None]}
    if condition == "anti-ranked":
        return {"kind": "coordinates", "indices": model["anti_ranked_nodes"]}
    if condition == "random-control-1":
        return {"kind": "subspace", "basis": model["random_control_basis_1"]}
    if condition == "random-control-2":
        return {"kind": "subspace", "basis": model["random_control_basis_2"]}
    raise ValueError(f"unknown transplant condition: {condition}")


def _candidate_specs(model: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    names = (
        "memory-axis",
        "observer-rank-1",
        "observer-rank-2",
        "observer-rank-4",
        "top-nodes-1",
        "top-nodes-2",
        "top-nodes-3",
        "top-nodes-half",
    )
    return [(name, condition_spec(model, name)) for name in names]


def _predicted_transfer_fraction(
    matrix: np.ndarray,
    component: np.ndarray,
    state_delta: np.ndarray,
    fingerprint_delta: np.ndarray,
) -> float:
    prediction = matrix @ _project(component, state_delta)
    denominator = float(np.dot(fingerprint_delta, fingerprint_delta))
    if denominator <= 1e-12:
        return 0.0
    value = float(np.dot(prediction, fingerprint_delta) / denominator)
    return value if np.isfinite(value) else 0.0


def build_census_selections(
    config: Mapping[str, Any], manifold: Path
) -> dict[str, Any]:
    rows = list(read_jsonl(manifold / "mode-plane.jsonl"))
    selections: list[dict[str, Any]] = []
    count = int(config["plane_census"]["endpoints_per_task_arm_seed"])
    for task_id in config["focal_task_ids"]:
        for seed_index in config["discovery_seed_indices"]:
            for arm in ("low", "high"):
                group = [
                    row
                    for row in rows
                    if str(row.get("memory_task_id")) == str(task_id)
                    and int(row.get("seed_index", -1)) == int(seed_index)
                    and str(row.get("arm")) == arm
                ]
                chosen = select_diverse_plane_rows(group, count)
                for rank, row in enumerate(chosen):
                    selections.append(
                        {
                            "task_id": f"census-selection|{task_id}|{seed_index}|{arm}|{rank}",
                            "memory_task_id": str(task_id),
                            "seed_index": int(seed_index),
                            "seed_role": "discovery",
                            "arm": arm,
                            "selection_rank": int(rank),
                            "source_plane_task_id": str(row["task_id"]),
                            "angle_index": int(row["angle_index"]),
                            "angle_radians": float(row["angle_radians"]),
                            "radius_fraction": float(row["radius_fraction"]),
                            "available": bool(
                                row.get("valid")
                                and isinstance(row.get("terminal_state"), Mapping)
                            ),
                            "unavailable_reason": row.get(
                                "reason", "parent-mode-plane-endpoint-unavailable"
                            ),
                            "terminal_state": row.get("terminal_state"),
                        }
                    )
    if len(selections) != EXPECTED_COUNTS["plane-census.jsonl"]:
        raise ValueError("discovery plane census selection is incomplete")
    return {
        "task_id": "plane-census-selections",
        "selection_rule": "deterministic-farthest-point-angle-log-radius",
        "outcome_leakage_allowed": False,
        "fresh_seed_outcomes_available_at_selection": False,
        "discovery_seed_indices": list(config["discovery_seed_indices"]),
        "selections": selections,
    }


def _task_resources(
    config: Mapping[str, Any], atlas: Path, upstream: Path, task_id: str
) -> tuple[Any, JaxBackend, int]:
    released = load_released_task(upstream, str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
    reconstructed = int(_calibration_map(atlas)[str(task_id)]["reconstructed_ucs_bound_index"])
    return memory, backend, reconstructed


def _plane_census_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_causal_carrier_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "plane-census", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    selection_payload = json.loads(
        (output / "plane-census-selections.json").read_text(encoding="utf-8")
    )
    selected = [
        row
        for row in selection_payload["selections"]
        if str(row["memory_task_id"]) == str(task_id)
        and int(row["seed_index"]) == int(seed_index)
    ]
    memory, backend, reconstructed = _task_resources(
        config, Path(atlas_path), Path(upstream_path), str(task_id)
    )
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for selection in selected:
        if not bool(selection.get("available")):
            records.append(
                {
                    "task_id": str(selection["task_id"]).replace(
                        "census-selection", "plane-census", 1
                    ),
                    "assay": "discovery-plane-fingerprint-census",
                    "memory_task_id": str(task_id),
                    "model_id": int(memory.key.model_id),
                    "seed_index": int(seed_index),
                    "seed_role": "discovery",
                    "arm": str(selection["arm"]),
                    "selection_rank": int(selection["selection_rank"]),
                    "source_plane_task_id": str(selection["source_plane_task_id"]),
                    "angle_index": int(selection["angle_index"]),
                    "angle_radians": float(selection["angle_radians"]),
                    "radius_fraction": float(selection["radius_fraction"]),
                    "state": None,
                    "fingerprint": None,
                    "raw_fingerprint": None,
                    "valid": False,
                    "reason": str(selection["unavailable_reason"]),
                }
            )
            continue
        state = _payload_state(selection["terminal_state"])
        fingerprint = _fingerprint(
            backend, memory, state, config, reconstructed
        )
        cpu += float(fingerprint["cpu_seconds"])
        wall += float(fingerprint["wall_seconds"])
        records.append(
            {
                "task_id": str(selection["task_id"]).replace(
                    "census-selection", "plane-census", 1
                ),
                "assay": "discovery-plane-fingerprint-census",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "seed_role": "discovery",
                "arm": str(selection["arm"]),
                "selection_rank": int(selection["selection_rank"]),
                "source_plane_task_id": str(selection["source_plane_task_id"]),
                "angle_index": int(selection["angle_index"]),
                "angle_radians": float(selection["angle_radians"]),
                "radius_fraction": float(selection["radius_fraction"]),
                "state": state_payload(state),
                "fingerprint": fingerprint["fingerprint"],
                "raw_fingerprint": fingerprint["raw_fingerprint"],
                "valid": bool(fingerprint["valid"]),
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "plane-census",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _basis_for_spec(spec: Mapping[str, Any], node_count: int) -> np.ndarray:
    if spec["kind"] == "coordinates":
        return _coordinate_basis(spec.get("indices", ()), node_count)
    if spec["kind"] == "subspace":
        return _orthonormal(spec.get("basis", ()), node_count)
    if spec["kind"] == "full":
        return np.eye(node_count)
    return np.empty((node_count, 0), dtype=float)


def build_carrier_models(
    config: Mapping[str, Any],
    census_records: Sequence[Mapping[str, Any]],
    manifold: Path,
    constrained: Path,
) -> dict[str, Any]:
    """Freeze observer, sparse-node, neutral, tangent, and normal carriers."""

    if any(int(row["seed_index"]) not in config["discovery_seed_indices"] for row in census_records):
        raise ValueError("fresh or validation outcomes leaked into carrier discovery")
    structural_map = _model_map(manifold / "structural-census.json")
    mode_map = _model_map(manifold / "mode-models.json")
    parent_map = _parent_no_op_map(constrained)
    models: list[dict[str, Any]] = []
    for task_id in config["focal_task_ids"]:
        registered_rows = [
            row
            for row in census_records
            if str(row["memory_task_id"]) == str(task_id)
        ]
        expected = (
            len(config["discovery_seed_indices"])
            * 2
            * int(config["plane_census"]["endpoints_per_task_arm_seed"])
        )
        if len(registered_rows) != expected:
            raise ValueError(
                f"incomplete registered discovery census for {task_id}: "
                f"{len(registered_rows)} != {expected}"
            )
        rows = [row for row in registered_rows if bool(row.get("valid"))]
        scale = np.asarray(mode_map[str(task_id)]["scale"], dtype=float)
        node_count = len(scale)
        if len(rows) < max(4, node_count):
            raise ValueError(f"too few feasible discovery endpoints for {task_id}: {len(rows)}")
        for seed_index in config["discovery_seed_indices"]:
            for arm in ("low", "high"):
                if not any(
                    int(row["seed_index"]) == int(seed_index)
                    and str(row["arm"]) == arm
                    for row in rows
                ):
                    raise ValueError(
                        f"no feasible discovery endpoint for {task_id}/{seed_index}/{arm}"
                    )
        x = np.asarray([_payload_state(row["state"]).y / scale for row in rows], dtype=float)
        y = np.asarray([row["fingerprint"] for row in rows], dtype=float)
        fitted = fit_multioutput_ridge(
            x,
            y,
            config["plane_census"]["ridge_candidates"],
            int(config["plane_census"]["ridge_fold_count"]),
        )
        matrix = np.asarray(fitted["matrix"], dtype=float)
        _, observer_singular, observer_vh = np.linalg.svd(matrix, full_matrices=True)
        observer_basis = observer_vh.T
        for index in range(observer_basis.shape[1]):
            observer_basis[:, index] = _unit(observer_basis[:, index])
        node_scores = np.linalg.norm(matrix, axis=0)
        ranked_nodes = sorted(range(node_count), key=lambda index: (-node_scores[index], index))

        centered: list[np.ndarray] = []
        for seed_index in config["discovery_seed_indices"]:
            for arm in ("low", "high"):
                group = [
                    x[index]
                    for index, row in enumerate(rows)
                    if int(row["seed_index"]) == int(seed_index) and str(row["arm"]) == arm
                ]
                center = np.mean(np.asarray(group), axis=0)
                centered.extend(value - center for value in group)
        _, tangent_singular, tangent_vh = np.linalg.svd(
            np.asarray(centered, dtype=float), full_matrices=False
        )
        tangent_rank = min(int(config["plane_census"]["tangent_rank"]), tangent_vh.shape[0])
        tangent_basis = _orthonormal(tangent_vh[:tangent_rank].T, node_count)

        axes: list[np.ndarray] = []
        discovery_pairs: list[tuple[np.ndarray, np.ndarray]] = []
        for seed_index in config["discovery_seed_indices"]:
            low = parent_map[(str(task_id), int(seed_index), "low")]
            high = parent_map[(str(task_id), int(seed_index), "high")]
            low_state = _state(low)
            high_state = _state(high)
            delta = (high_state.y - low_state.y) / scale
            axes.append(_unit(delta))
            discovery_pairs.append(
                (delta, np.asarray(high["fingerprint"], dtype=float) - np.asarray(low["fingerprint"], dtype=float))
            )
        memory_axis = _unit(np.mean(np.asarray(axes), axis=0))
        normal = observer_basis[:, 0] - _project(tangent_basis, observer_basis[:, 0])
        if np.linalg.norm(normal) <= 1e-10:
            normal = memory_axis - _project(tangent_basis, memory_axis)
        if np.linalg.norm(normal) <= 1e-10:
            complement = np.eye(node_count) - tangent_basis @ tangent_basis.T
            normal = complement[:, int(np.argmax(np.linalg.norm(complement, axis=0)))]
        normal = _unit(normal)
        neutral = np.asarray(
            structural_map[str(task_id)]["structural_invariant_basis"], dtype=float
        ).reshape(node_count, -1)

        partial_model: dict[str, Any] = {
            "node_count": node_count,
            "ranked_nodes": ranked_nodes,
            "memory_axis": memory_axis,
            "observer_basis": observer_basis,
            "structural_neutral_basis": neutral,
            "tangent_basis": tangent_basis,
            "normal_direction": normal,
        }
        candidates: list[dict[str, Any]] = []
        for name, spec in _candidate_specs(partial_model):
            basis = _basis_for_spec(spec, node_count)
            fractions = [
                _predicted_transfer_fraction(matrix, basis, state_delta, fp_delta)
                for state_delta, fp_delta in discovery_pairs
            ]
            candidates.append(
                {
                    "condition": name,
                    "effective_dimension": _spec_dimension(spec, node_count),
                    "per_discovery_pair_predicted_transfer": fractions,
                    "median_predicted_transfer_fraction": float(np.median(fractions)),
                }
            )
        threshold = float(config["plane_census"]["candidate_transfer_fraction_min"])
        qualifying = [row for row in candidates if row["median_predicted_transfer_fraction"] >= threshold]
        if qualifying:
            primary = min(
                qualifying,
                key=lambda row: (row["effective_dimension"], -row["median_predicted_transfer_fraction"], row["condition"]),
            )
            rule = "smallest-at-or-above-discovery-threshold"
        else:
            primary = min(
                candidates,
                key=lambda row: (-row["median_predicted_transfer_fraction"], row["effective_dimension"], row["condition"]),
            )
            rule = "maximum-predicted-transfer-fallback"
        primary_spec = condition_spec(partial_model, str(primary["condition"]))
        primary_dimension = max(1, _spec_dimension(primary_spec, node_count))
        anti_ranked = list(reversed(ranked_nodes))[:primary_dimension]
        random_bases: list[np.ndarray] = []
        for control_index in (1, 2):
            rng = np.random.Generator(
                np.random.Philox(_stable_seed(config, "random-control-basis", task_id, control_index))
            )
            random_bases.append(_orthonormal(rng.normal(size=(node_count, primary_dimension)), node_count))
        model = {
            "memory_task_id": str(task_id),
            "task_role": config["task_roles"][str(task_id)],
            "node_count": node_count,
            "scale": scale,
            "observer_map": fitted,
            "observer_singular_values": observer_singular,
            "observer_basis": observer_basis,
            "node_sensitivity_scores": node_scores,
            "ranked_nodes": ranked_nodes,
            "memory_axis": memory_axis,
            "structural_neutral_basis": neutral,
            "tangent_basis": tangent_basis,
            "tangent_singular_values": tangent_singular,
            "normal_direction": normal,
            "candidate_predictions": candidates,
            "primary_condition": str(primary["condition"]),
            "primary_effective_dimension": int(primary_dimension),
            "primary_selection_rule": rule,
            "anti_ranked_nodes": anti_ranked,
            "random_control_basis_1": random_bases[0],
            "random_control_basis_2": random_bases[1],
            "frozen_from_seed_indices": list(config["discovery_seed_indices"]),
            "fresh_seed_outcomes_used": False,
        }
        model["model_digest"] = digest(model)
        models.append(model)
    return {
        "task_id": "causal-carrier-models",
        "frozen_before_fresh_exposure_generation": True,
        "outcome_leakage_allowed": False,
        "selection_threshold": float(config["plane_census"]["candidate_transfer_fraction_min"]),
        "models": models,
    }


def _contingency_protocol(contingency: Path) -> dict[str, Any]:
    registration = json.loads((contingency / "registration.json").read_text(encoding="utf-8"))
    protocol = dict(registration["protocol"])
    if (
        float(protocol["delta_t"]) != 0.01
        or float(protocol["epoch_duration"]) != 250.0
        or int(protocol["epoch_count"]) != 10
        or [float(value) for value in protocol["washout_checkpoints"]] != [2500.0, 12500.0]
    ):
        raise ValueError("sealed contingency exposure protocol differs from the registered history")
    return protocol


def _fresh_exposure_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        contingency_path,
        atlas_path,
        upstream_path,
        output_path,
        task_id,
        seed_index,
    ) = args
    config = load_causal_carrier_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "fresh-exposure", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    history_config = _contingency_protocol(Path(contingency_path))
    memory, backend, reconstructed = _task_resources(
        config, Path(atlas_path), Path(upstream_path), str(task_id)
    )
    base = _naive_start(Path(atlas_path), str(task_id))
    start, philox_seed = _perturb_start(
        base, memory, history_config, "exposure", str(task_id), int(seed_index)
    )
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm, bound in (("low", 0), ("high", 1)):
        result = _run_history(
            backend,
            memory,
            start.copy(),
            history_config,
            int(bound),
            _control_tokens("ucs_only"),
            seed_index=int(seed_index),
            probe_ucs_bound=reconstructed,
        )
        cpu += float(result["cpu_seconds"])
        wall += float(result["wall_seconds"])
        endpoint = result["checkpoints"]["12500"]
        records.append(
            {
                "task_id": f"fresh-exposure|{task_id}|{seed_index}|{arm}",
                "assay": "fresh-ucs-only-exposure-history",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "seed_role": "fresh-prospective",
                "arm": arm,
                "training_bound_index": int(bound),
                "philox_seed": int(philox_seed),
                "history_protocol_digest": digest(history_config),
                "start_state": state_payload(start),
                "source_state": endpoint["state"],
                "fingerprint": endpoint["fingerprint"],
                "raw_fingerprint": endpoint["raw_fingerprint"],
                "history_checkpoints": result["checkpoints"],
                "valid": bool(result["valid"] and endpoint["valid"]),
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "fresh-exposure",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _fresh_map(output: Path) -> dict[tuple[str, int, str], dict[str, Any]]:
    return {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["arm"])): dict(row)
        for row in read_jsonl(output / "fresh-exposure.jsonl")
    }


def _no_op_map(output: Path) -> dict[tuple[str, int, str], dict[str, Any]]:
    return {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["arm"])): dict(row)
        for row in read_jsonl(output / "no-op.jsonl")
    }


def _carrier_model_map(output: Path) -> dict[str, dict[str, Any]]:
    return _model_map(output / "carrier-models.json")


def _no_op_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_causal_carrier_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "no-op", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    memory, backend, reconstructed = _task_resources(
        config, Path(atlas_path), Path(upstream_path), str(task_id)
    )
    references = {
        arm: np.asarray(fresh[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        source = _payload_state(fresh[(str(task_id), int(seed_index), arm)]["source_state"])
        result, used_cpu, used_wall = _finish_record(
            backend,
            memory,
            reconstructed,
            config,
            source,
            references["high"],
            references["low"],
        )
        cpu += used_cpu
        wall += used_wall
        records.append(
            {
                "task_id": f"carrier-no-op|{task_id}|{seed_index}|{arm}",
                "condition_id": f"no-op|{arm}",
                "assay": "release-matched-no-op",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "seed_role": "fresh-prospective",
                "arm": arm,
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


def _invalid_record(
    task_id: str, seed_index: int, condition_id: str, reason: str, **extra: Any
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
        **extra,
    }


def _transplant_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_causal_carrier_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "carrier-transplants", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    no_ops = _no_op_map(output)
    model = _carrier_model_map(output)[str(task_id)]
    scale = np.asarray(model["scale"], dtype=float)
    memory, backend, reconstructed = _task_resources(
        config, Path(atlas_path), Path(upstream_path), str(task_id)
    )
    references = {
        arm: np.asarray(no_ops[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    states = {
        arm: _payload_state(fresh[(str(task_id), int(seed_index), arm)]["source_state"])
        for arm in ("low", "high")
    }
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    tolerance = float(config["subspace_line_search"]["box_tolerance"])
    for recipient_arm, donor_arm in (("low", "high"), ("high", "low")):
        recipient = states[recipient_arm]
        donor = states[donor_arm]
        primary_spec = condition_spec(model, str(model["primary_condition"]))
        _, _, primary_requested_norm = apply_component_transplant(
            recipient, donor, primary_spec, scale, tolerance=tolerance
        )
        for condition in config["transplant_conditions"]:
            condition = str(condition)
            spec = condition_spec(model, condition)
            norm_target = (
                primary_requested_norm if condition.startswith("random-control-") else None
            )
            start, alpha, requested_norm = apply_component_transplant(
                recipient,
                donor,
                spec,
                scale,
                tolerance=tolerance,
                norm_target=norm_target,
            )
            condition_id = f"transplant|{recipient_arm}-to-{donor_arm}|{condition}"
            common = {
                "assay": "causal-carrier-transplant",
                "model_id": int(memory.key.model_id),
                "seed_role": "fresh-prospective",
                "recipient_arm": recipient_arm,
                "donor_arm": donor_arm,
                "target_arm": donor_arm,
                "condition": condition,
                "component_kind": str(spec["kind"]),
                "effective_dimension": _spec_dimension(spec, len(scale)),
                "requested_standardized_norm": requested_norm,
                "coefficient_fraction": alpha,
                "is_primary_candidate": condition == str(model["primary_condition"]),
                "primary_condition": str(model["primary_condition"]),
                "primary_model_digest": str(model["model_digest"]),
                "primary_eligible": bool(
                    condition == str(model["primary_condition"])
                    and alpha
                    >= float(
                        config["subspace_line_search"][
                            "minimum_primary_coefficient_fraction"
                        ]
                    )
                ),
            }
            if start is None:
                records.append(
                    _invalid_record(
                        str(task_id),
                        int(seed_index),
                        condition_id,
                        "zero-or-infeasible-component",
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
                    "task_id": f"transplant|{task_id}|{seed_index}|{recipient_arm}-to-{donor_arm}|{condition}",
                    "condition_id": condition_id,
                    "memory_task_id": str(task_id),
                    "seed_index": int(seed_index),
                    **common,
                    **result,
                }
            )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "carrier-transplants",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def transfer_metrics(
    records: Sequence[Mapping[str, Any]],
    no_ops: Sequence[Mapping[str, Any]],
    models: Mapping[str, Any],
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    references = {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["arm"])): row
        for row in no_ops
    }
    model_map = {str(row["memory_task_id"]): row for row in models["models"]}
    results: list[dict[str, Any]] = []
    for row in records:
        task_id = str(row["memory_task_id"])
        seed_index = int(row["seed_index"])
        recipient_arm = str(row["recipient_arm"])
        target_arm = str(row["target_arm"])
        common = {
            "task_id": f"metric|{row['task_id']}",
            "source_task_id": str(row["task_id"]),
            "memory_task_id": task_id,
            "seed_index": seed_index,
            "recipient_arm": recipient_arm,
            "target_arm": target_arm,
            "condition": str(row["condition"]),
            "is_primary_candidate": bool(row.get("is_primary_candidate")),
            "primary_eligible": bool(row.get("primary_eligible")),
            "valid": False,
        }
        if not bool(row.get("valid")):
            results.append({**common, "reason": row.get("reason", "invalid-transplant")})
            continue
        recipient = references.get((task_id, seed_index, recipient_arm))
        target = references.get((task_id, seed_index, target_arm))
        if recipient is None or target is None:
            results.append({**common, "reason": "matched-no-op-missing"})
            continue
        scale = np.asarray(model_map[task_id]["scale"], dtype=float)
        checkpoint_vectors: dict[str, np.ndarray] = {}
        state_target_fractions: dict[str, float | None] = {}
        checkpoint_cosines: dict[str, float | None] = {}
        for checkpoint in CHECKPOINT_KEYS:
            observed_state = _checkpoint_state(row, checkpoint)
            recipient_state = _checkpoint_state(recipient, checkpoint)
            target_state = _checkpoint_state(target, checkpoint)
            if observed_state is None or recipient_state is None or target_state is None:
                state_target_fractions[checkpoint] = None
                checkpoint_cosines[checkpoint] = None
                continue
            observed_delta = (observed_state.y - recipient_state.y) / scale
            target_delta = (target_state.y - recipient_state.y) / scale
            checkpoint_vectors[checkpoint] = observed_delta
            denominator = float(np.dot(target_delta, target_delta))
            state_target_fractions[checkpoint] = (
                None
                if denominator <= 1e-12
                else float(np.dot(observed_delta, target_delta) / denominator)
            )
            checkpoint_cosines[checkpoint] = cosine_alignment(observed_delta, target_delta)
        direction_cosine = (
            cosine_alignment(checkpoint_vectors["2500"], checkpoint_vectors["12500"])
            if "2500" in checkpoint_vectors and "12500" in checkpoint_vectors
            else None
        )
        norm_2500 = (
            float(np.linalg.norm(checkpoint_vectors["2500"]))
            if "2500" in checkpoint_vectors
            else 0.0
        )
        norm_12500 = (
            float(np.linalg.norm(checkpoint_vectors["12500"]))
            if "12500" in checkpoint_vectors
            else 0.0
        )
        retention = None if norm_2500 <= 1e-12 else float(norm_12500 / norm_2500)
        target_fp = np.asarray(target["fingerprint"], dtype=float)
        fp_rms = vector_rms(np.asarray(row["fingerprint"], dtype=float) - target_fp)
        score = row.get("bipolar_score")
        target_sign = 1.0 if target_arm == "high" else -1.0
        oriented = None if score is None else float(target_sign * float(score))
        target_identity = bool(oriented is not None and oriented > 0.0)
        results.append(
            {
                **common,
                "valid": True,
                "target_identity": target_identity,
                "target_oriented_bipolar_score": oriented,
                "target_fingerprint_rms": fp_rms,
                "checkpoint_state_target_fractions": state_target_fractions,
                "checkpoint_state_target_cosines": checkpoint_cosines,
                "state_target_fraction_12500": state_target_fractions.get("12500"),
                "state_target_cosine_12500": checkpoint_cosines.get("12500"),
                "transfer_direction_cosine_2500_to_12500": direction_cosine,
                "transfer_retention_fraction": retention,
                "coefficient_fraction": row.get("coefficient_fraction"),
                "effective_dimension": row.get("effective_dimension"),
            }
        )
    return results


def _transplant_map(output: Path) -> dict[tuple[str, int, str, str], dict[str, Any]]:
    return {
        (
            str(row["memory_task_id"]),
            int(row["seed_index"]),
            str(row["recipient_arm"]),
            str(row["condition"]),
        ): dict(row)
        for row in read_jsonl(output / "carrier-transplants.jsonl")
    }


def _local_geometry_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_causal_carrier_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "local-geometry", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    no_ops = _no_op_map(output)
    transplants = _transplant_map(output)
    model = _carrier_model_map(output)[str(task_id)]
    scale = np.asarray(model["scale"], dtype=float)
    memory, backend, reconstructed = _task_resources(
        config, Path(atlas_path), Path(upstream_path), str(task_id)
    )
    bounds = np.asarray(memory.bounds, dtype=float)
    references = {
        arm: np.asarray(no_ops[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    no_op_states = {
        arm: _payload_state(no_ops[(str(task_id), int(seed_index), arm)]["terminal_state"])
        for arm in ("low", "high")
    }
    separation = float(np.linalg.norm((no_op_states["high"].y - no_op_states["low"].y) / scale))
    directions = {
        "tangent": np.asarray(model["tangent_basis"], dtype=float)[:, 0],
        "normal": np.asarray(model["normal_direction"], dtype=float),
    }
    settings = config["local_geometry"]
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        primary = transplants.get(
            (str(task_id), int(seed_index), arm, str(model["primary_condition"]))
        )
        centers: dict[str, tuple[State | None, np.ndarray | None, str]] = {
            "source": (no_op_states[arm], references[arm], arm),
            "transplanted": (
                None if primary is None or not primary.get("valid") else _payload_state(primary["terminal_state"]),
                None if primary is None or not primary.get("valid") else np.asarray(primary["fingerprint"], dtype=float),
                "high" if arm == "low" else "low",
            ),
        }
        for center_type in settings["center_types"]:
            center, center_fp, center_identity = centers[str(center_type)]
            for direction_kind in settings["direction_kinds"]:
                for sign_value in settings["signs"]:
                    sign = int(sign_value)
                    for radius_factor_value in settings["radius_factors"]:
                        radius_factor = float(radius_factor_value)
                        condition_id = (
                            f"geometry|{arm}|{center_type}|{direction_kind}|"
                            f"sign={sign}|r={radius_factor:g}"
                        )
                        common = {
                            "assay": "curved-local-geometry",
                            "model_id": int(memory.key.model_id),
                            "seed_role": "fresh-prospective",
                            "arm": arm,
                            "center_type": str(center_type),
                            "center_identity": center_identity,
                            "direction_kind": str(direction_kind),
                            "sign": sign,
                            "radius_factor": radius_factor,
                            "primary_condition": str(model["primary_condition"]),
                        }
                        if center is None or center_fp is None:
                            records.append(
                                _invalid_record(
                                    str(task_id), int(seed_index), condition_id,
                                    "primary-transplanted-center-unavailable", **common
                                )
                            )
                            continue
                        envelope = source_enclosing_envelope(center, bounds)
                        direction, feasible, cap = local_radius_cap(
                            center,
                            sign * directions[str(direction_kind)],
                            scale,
                            bounds,
                            separation,
                            float(settings["separation_cap_fraction"]),
                            float(settings["feasible_radius_fraction"]),
                            float(config["subspace_line_search"]["box_tolerance"]),
                        )
                        radius = radius_factor * cap
                        geometry_fields = {
                            **common,
                            "direction": direction,
                            "separation": separation,
                            "maximum_feasible_radius": feasible,
                            "local_radius_cap": cap,
                            "requested_radius": radius,
                        }
                        if cap < float(settings["minimum_radius_fraction_of_separation"]) * separation:
                            records.append(
                                _invalid_record(
                                    str(task_id), int(seed_index), condition_id,
                                    "endpoint-specific-radius-unavailable", **geometry_fields
                                )
                            )
                            continue
                        y = center.y + radius * direction * scale
                        if np.any(y < envelope[:, 0] - 1e-8) or np.any(
                            y > envelope[:, 1] + 1e-8
                        ):
                            raise AssertionError("registered local radius escaped the source envelope")
                        start = State(y, center.w.copy(), center.c.copy(), float(center.t))
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
                        terminal = _payload_state(result["terminal_state"])
                        final_distance = float(np.linalg.norm((terminal.y - center.y) / scale))
                        ratio = None if radius <= 1e-12 else float(final_distance / radius)
                        fp_rms = vector_rms(np.asarray(result["fingerprint"], dtype=float) - center_fp)
                        records.append(
                            {
                                "task_id": (
                                    f"geometry|{task_id}|{seed_index}|{arm}|{center_type}|"
                                    f"{direction_kind}|{sign}|{radius_factor:g}"
                                ),
                                "condition_id": condition_id,
                                "memory_task_id": str(task_id),
                                "seed_index": int(seed_index),
                                "center_state": state_payload(center),
                                "center_fingerprint": center_fp,
                                "final_distance_from_center": final_distance,
                                "contraction_or_persistence_ratio": ratio,
                                "center_fingerprint_rms": fp_rms,
                                "behavior_returned": bool(
                                    fp_rms <= float(config["decision"]["fingerprint_rms_max"])
                                ),
                                **geometry_fields,
                                **result,
                            }
                        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "local-geometry",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _erase_rescue_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_causal_carrier_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(
        output, "erase-rescue", f"{task_id}-{seed_index}", protocol_digest
    )
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    no_ops = _no_op_map(output)
    model = _carrier_model_map(output)[str(task_id)]
    scale = np.asarray(model["scale"], dtype=float)
    memory, backend, reconstructed = _task_resources(
        config, Path(atlas_path), Path(upstream_path), str(task_id)
    )
    references = {
        arm: np.asarray(no_ops[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    states = {
        arm: _payload_state(fresh[(str(task_id), int(seed_index), arm)]["source_state"])
        for arm in ("low", "high")
    }
    midpoint = State(
        0.5 * (states["low"].y + states["high"].y),
        0.5 * (states["low"].w + states["high"].w),
        states["low"].c.copy(),
        float(states["low"].t),
    )
    spec = condition_spec(model, str(model["primary_condition"]))
    tolerance = float(config["subspace_line_search"]["box_tolerance"])
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        source = states[arm]
        condition_id = f"erase-rescue|{arm}|{model['primary_condition']}"
        erased, erase_alpha, _ = apply_component_transplant(
            source, midpoint, spec, scale, tolerance=tolerance
        )
        common = {
            "assay": "primary-carrier-erase-rescue",
            "model_id": int(memory.key.model_id),
            "seed_role": "fresh-prospective",
            "arm": arm,
            "primary_condition": str(model["primary_condition"]),
            "erase_coefficient_fraction": erase_alpha,
        }
        if erased is None:
            records.append(
                _invalid_record(
                    str(task_id), int(seed_index), condition_id,
                    "primary-carrier-erasure-unavailable", **common
                )
            )
            continue
        erased_phase = backend.run_unstimulated(
            erased,
            2500.0,
            memory.key.response_id,
            int(config["trajectory_samples"]),
            float(config["washout_chunk_duration"]),
        )
        erased_fp = _fingerprint(
            backend, memory, erased_phase.state, config, reconstructed
        )
        cpu += float(erased_phase.cpu_seconds + erased_fp["cpu_seconds"])
        wall += float(erased_phase.wall_seconds + erased_fp["wall_seconds"])
        rescued, rescue_alpha, _ = apply_component_transplant(
            erased_phase.state, source, spec, scale, tolerance=tolerance
        )
        if rescued is None:
            records.append(
                _invalid_record(
                    str(task_id), int(seed_index), condition_id,
                    "primary-carrier-reinsertion-unavailable",
                    erased_state=state_payload(erased_phase.state),
                    erased_fingerprint=erased_fp["fingerprint"],
                    **common,
                )
            )
            continue
        rescued_result, rescue_cpu, rescue_wall = _finish_record(
            backend,
            memory,
            reconstructed,
            config,
            rescued,
            references["high"],
            references["low"],
        )
        cpu += rescue_cpu
        wall += rescue_wall
        source_fp = references[arm]
        erased_distance = vector_rms(np.asarray(erased_fp["fingerprint"], dtype=float) - source_fp)
        rescued_distance = vector_rms(np.asarray(rescued_result["fingerprint"], dtype=float) - source_fp)
        erase_score = bipolar_score(
            erased_fp["fingerprint"], references["high"], references["low"]
        )
        source_sign = 1.0 if arm == "high" else -1.0
        source_oriented_after_erase = (
            None if erase_score is None else float(source_sign * erase_score)
        )
        erase_effect = (
            None
            if source_oriented_after_erase is None
            else float(max(0.0, 1.0 - source_oriented_after_erase))
        )
        rescue_fraction = (
            None
            if erased_distance <= 1e-12
            else float(1.0 - rescued_distance / erased_distance)
        )
        records.append(
            {
                "task_id": f"erase-rescue|{task_id}|{seed_index}|{arm}",
                "condition_id": condition_id,
                "memory_task_id": str(task_id),
                "seed_index": int(seed_index),
                "erased_start_state": state_payload(erased),
                "erased_state_2500": state_payload(erased_phase.state),
                "erased_fingerprint_2500": erased_fp["fingerprint"],
                "erased_bipolar_score": erase_score,
                "source_oriented_score_after_erase": source_oriented_after_erase,
                "erase_effect_fraction": erase_effect,
                "reinserted_state": state_payload(rescued),
                "rescue_coefficient_fraction": rescue_alpha,
                "source_fingerprint_rms_after_erase": erased_distance,
                "source_fingerprint_rms_after_rescue": rescued_distance,
                "rescue_fraction": rescue_fraction,
                "valid": bool(
                    erased_phase.valid and erased_fp["valid"] and rescued_result["valid"]
                ),
                **common,
                **{f"rescued_{key}": value for key, value in rescued_result.items()},
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "erase-rescue",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _condition_summary(
    metrics: Sequence[Mapping[str, Any]], condition: str, config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["decision"]
    per_direction: list[dict[str, Any]] = []
    for target_arm in ("low", "high"):
        rows = [
            row
            for row in metrics
            if str(row.get("condition")) == str(condition)
            and str(row.get("target_arm")) == target_arm
            and bool(row.get("valid"))
        ]
        scores = [
            float(row["target_oriented_bipolar_score"])
            for row in rows
            if row.get("target_oriented_bipolar_score") is not None
        ]
        fp_pass = sum(
            float(row["target_fingerprint_rms"])
            <= float(settings["fingerprint_rms_max"])
            for row in rows
            if row.get("target_fingerprint_rms") is not None
        )
        direction_pass = sum(
            float(row["transfer_direction_cosine_2500_to_12500"])
            >= float(settings["direction_cosine_min"])
            for row in rows
            if row.get("transfer_direction_cosine_2500_to_12500") is not None
        )
        retention_pass = sum(
            float(row["transfer_retention_fraction"])
            >= float(settings["retention_fraction_min"])
            for row in rows
            if row.get("transfer_retention_fraction") is not None
        )
        identity_count = sum(bool(row.get("target_identity")) for row in rows)
        median_score = quantile(scores, 0.5)
        lower_score = quantile(scores, 0.25)
        required = int(settings["minimum_consistent_seeds"])
        passed = bool(
            len(rows) == len(config["fresh_seed_indices"])
            and identity_count >= required
            and fp_pass >= required
            and direction_pass >= required
            and retention_pass >= required
            and median_score is not None
            and median_score >= float(settings["median_target_bipolar_min"])
            and lower_score is not None
            and lower_score >= float(settings["lower_quartile_target_bipolar_min"])
        )
        per_direction.append(
            {
                "target_arm": target_arm,
                "valid_seed_count": len(rows),
                "target_identity_count": identity_count,
                "target_fingerprint_pass_count": fp_pass,
                "direction_cosine_pass_count": direction_pass,
                "retention_pass_count": retention_pass,
                "median_target_oriented_bipolar_score": median_score,
                "lower_quartile_target_oriented_bipolar_score": lower_score,
                "pass": passed,
            }
        )
    task_rows = [row for row in metrics if str(row.get("condition")) == str(condition)]
    state_fractions = [
        float(row["state_target_fraction_12500"])
        for row in task_rows
        if row.get("state_target_fraction_12500") is not None
    ]
    return {
        "condition": str(condition),
        "per_direction": per_direction,
        "median_state_target_fraction_12500": quantile(state_fractions, 0.5),
        "pass": all(bool(row["pass"]) for row in per_direction),
    }


def _control_summary(
    metrics: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["decision"]
    summaries: list[dict[str, Any]] = []
    for condition in ("sham", "anti-ranked", "random-control-1", "random-control-2"):
        for target_arm in ("low", "high"):
            rows = [
                row
                for row in metrics
                if str(row.get("condition")) == condition
                and str(row.get("target_arm")) == target_arm
                and bool(row.get("valid"))
            ]
            positive_transfer = [
                max(0.0, float(row["target_oriented_bipolar_score"]))
                for row in rows
                if row.get("target_oriented_bipolar_score") is not None
            ]
            switches = sum(bool(row.get("target_identity")) for row in rows)
            median_transfer = quantile(positive_transfer, 0.5)
            passed = bool(
                len(rows) == len(config["fresh_seed_indices"])
                and switches <= int(settings["control_switch_count_max"])
                and median_transfer is not None
                and median_transfer <= float(settings["control_median_transfer_max"])
            )
            summaries.append(
                {
                    "condition": condition,
                    "target_arm": target_arm,
                    "valid_seed_count": len(rows),
                    "target_identity_count": switches,
                    "median_positive_target_transfer": median_transfer,
                    "pass": passed,
                }
            )
    return {"summaries": summaries, "pass": all(bool(row["pass"]) for row in summaries)}


def carrier_decision(
    metrics: Sequence[Mapping[str, Any]],
    models: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    model_map = {str(row["memory_task_id"]): row for row in models["models"]}
    task_summaries: list[dict[str, Any]] = []
    for task_id in config["focal_task_ids"]:
        rows = [row for row in metrics if str(row["memory_task_id"]) == str(task_id)]
        model = model_map[str(task_id)]
        primary = _condition_summary(rows, str(model["primary_condition"]), config)
        full = _condition_summary(rows, "full-state", config)
        controls = _control_summary(rows, config)
        eligible_primary_rows = [
            row
            for row in rows
            if bool(row.get("is_primary_candidate")) and bool(row.get("primary_eligible"))
        ]
        eligibility_pass = len(eligible_primary_rows) >= 2 * int(
            config["decision"]["minimum_consistent_seeds"]
        )
        structural_fraction = primary["median_state_target_fraction_12500"]
        structural_restoration = bool(
            structural_fraction is not None and float(structural_fraction) >= 0.5
        )
        causal_pass = bool(
            primary["pass"] and full["pass"] and controls["pass"] and eligibility_pass
        )
        compact = int(model["primary_effective_dimension"]) < int(model["node_count"])
        if causal_pass and config["task_roles"][str(task_id)] == "nonlinear-switch-contrast" and model["primary_selection_rule"].endswith("fallback"):
            classification = "nonlinear-switch-carrier"
        elif causal_pass and compact and not structural_restoration:
            classification = "observer-equivalent-causal-carrier"
        elif causal_pass and compact:
            classification = "compact-causal-current-state-carrier"
        elif causal_pass or full["pass"]:
            classification = "distributed-current-state-carrier"
        else:
            classification = "no-causal-carrier"
        task_summaries.append(
            {
                "memory_task_id": str(task_id),
                "task_role": config["task_roles"][str(task_id)],
                "primary_condition": str(model["primary_condition"]),
                "primary_effective_dimension": int(model["primary_effective_dimension"]),
                "primary_model_digest": str(model["model_digest"]),
                "primary": primary,
                "full_state_positive_control": full,
                "negative_controls": controls,
                "primary_line_search_eligibility_pass": eligibility_pass,
                "structural_restoration_secondary": structural_restoration,
                "compact": compact,
                "causal_transfer_pass": causal_pass,
                "classification": classification,
            }
        )
    passing = [row for row in task_summaries if row["causal_transfer_pass"]]
    return {
        "task_id": "causal-carrier-decision",
        "primary_success_definition": "behaviour-follows-preregistered-component-transplant",
        "task_summaries": task_summaries,
        "pass_count": len(passing),
        "pass": bool(passing),
        "verdict": "prospective-causal-carrier-leads" if passing else "no-prospective-causal-carrier",
    }


def geometry_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["decision"]
    registered_radii = {float(value) for value in settings["geometry_radius_factors"]}
    task_summaries: list[dict[str, Any]] = []
    for task_id in config["focal_task_ids"]:
        groups: list[dict[str, Any]] = []
        for center_type in config["local_geometry"]["center_types"]:
            for arm in ("low", "high"):
                for direction_kind in config["local_geometry"]["direction_kinds"]:
                    for sign_value in config["local_geometry"]["signs"]:
                        for radius in sorted(registered_radii):
                            rows = [
                                row
                                for row in records
                                if str(row.get("memory_task_id")) == str(task_id)
                                and str(row.get("center_type")) == str(center_type)
                                and str(row.get("arm")) == arm
                                and str(row.get("direction_kind")) == str(direction_kind)
                                and int(row.get("sign", 0)) == int(sign_value)
                                and math.isclose(float(row.get("radius_factor", -1.0)), radius)
                                and bool(row.get("valid"))
                            ]
                            ratios = [
                                float(row["contraction_or_persistence_ratio"])
                                for row in rows
                                if row.get("contraction_or_persistence_ratio") is not None
                            ]
                            if str(direction_kind) == "normal":
                                dynamic_pass_count = sum(
                                    value <= float(settings["normal_contraction_ratio_max"])
                                    for value in ratios
                                )
                            else:
                                dynamic_pass_count = sum(
                                    float(settings["tangent_persistence_ratio_min"])
                                    <= value
                                    <= float(settings["tangent_persistence_ratio_max"])
                                    for value in ratios
                                )
                            behavior_count = sum(bool(row.get("behavior_returned")) for row in rows)
                            required = int(settings["minimum_consistent_seeds"])
                            passed = bool(
                                len(rows) == len(config["fresh_seed_indices"])
                                and dynamic_pass_count >= required
                                and behavior_count >= required
                            )
                            groups.append(
                                {
                                    "center_type": str(center_type),
                                    "arm": arm,
                                    "direction_kind": str(direction_kind),
                                    "sign": int(sign_value),
                                    "radius_factor": radius,
                                    "valid_seed_count": len(rows),
                                    "dynamic_pass_count": dynamic_pass_count,
                                    "behavior_return_count": behavior_count,
                                    "median_ratio": quantile(ratios, 0.5),
                                    "pass": passed,
                                }
                            )
        passed = bool(groups) and all(bool(row["pass"]) for row in groups)
        task_summaries.append(
            {
                "memory_task_id": str(task_id),
                "registered_group_count": len(groups),
                "group_summaries": groups,
                "curved_attracting_functional_manifold": passed,
                "pass": passed,
            }
        )
    return {
        "task_id": "curved-local-geometry-decision",
        "task_summaries": task_summaries,
        "pass_count": sum(bool(row["pass"]) for row in task_summaries),
        "pass": any(bool(row["pass"]) for row in task_summaries),
    }


def erase_rescue_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["decision"]
    task_summaries: list[dict[str, Any]] = []
    for task_id in config["focal_task_ids"]:
        arms: list[dict[str, Any]] = []
        for arm in ("low", "high"):
            rows = [
                row
                for row in records
                if str(row.get("memory_task_id")) == str(task_id)
                and str(row.get("arm")) == arm
                and bool(row.get("valid"))
            ]
            erase_count = sum(
                float(row["erase_effect_fraction"]) >= float(settings["erase_effect_fraction_min"])
                for row in rows
                if row.get("erase_effect_fraction") is not None
            )
            rescue_count = sum(
                float(row["rescue_fraction"]) >= float(settings["rescue_fraction_min"])
                and float(row["source_fingerprint_rms_after_rescue"])
                <= float(settings["rescue_fingerprint_rms_max"])
                for row in rows
                if row.get("rescue_fraction") is not None
                and row.get("source_fingerprint_rms_after_rescue") is not None
            )
            required = int(settings["minimum_consistent_seeds"])
            arms.append(
                {
                    "arm": arm,
                    "valid_seed_count": len(rows),
                    "erase_pass_count": erase_count,
                    "rescue_pass_count": rescue_count,
                    "pass": bool(
                        len(rows) == len(config["fresh_seed_indices"])
                        and erase_count >= required
                        and rescue_count >= required
                    ),
                }
            )
        task_summaries.append(
            {
                "memory_task_id": str(task_id),
                "arm_summaries": arms,
                "pass": all(bool(row["pass"]) for row in arms),
            }
        )
    return {
        "task_id": "erase-rescue-decision",
        "task_summaries": task_summaries,
        "pass_count": sum(bool(row["pass"]) for row in task_summaries),
        "pass": any(bool(row["pass"]) for row in task_summaries),
    }


def analyze_causal_carrier(
    output: Path, final_status: str = "completed"
) -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    models = json.loads((output / "carrier-models.json").read_text(encoding="utf-8"))
    no_ops = list(read_jsonl(output / "no-op.jsonl"))
    transplants = list(read_jsonl(output / "carrier-transplants.jsonl"))
    geometry_rows = list(read_jsonl(output / "local-geometry.jsonl"))
    erase_rows = list(read_jsonl(output / "erase-rescue.jsonl"))
    metrics = transfer_metrics(transplants, no_ops, models, config)
    _write_jsonl(output / "transfer-metrics.jsonl", metrics)
    carrier = carrier_decision(metrics, models, config)
    geometry = geometry_decision(geometry_rows, config)
    erase = erase_rescue_decision(erase_rows, config)
    write_json(output / "carrier-decision.json", carrier)
    write_json(output / "geometry-decision.json", geometry)
    write_json(output / "erase-rescue-decision.json", erase)
    counts = {
        name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES
    }
    completion = counts == EXPECTED_COUNTS
    carrier_map = {row["memory_task_id"]: row for row in carrier["task_summaries"]}
    geometry_map = {row["memory_task_id"]: row for row in geometry["task_summaries"]}
    erase_map = {row["memory_task_id"]: row for row in erase["task_summaries"]}
    combined: list[dict[str, Any]] = []
    for task_id in config["focal_task_ids"]:
        causal = carrier_map[str(task_id)]
        controllable = bool(causal["causal_transfer_pass"] and erase_map[str(task_id)]["pass"])
        combined.append(
            {
                "memory_task_id": str(task_id),
                "carrier_classification": causal["classification"],
                "causal_transfer_pass": bool(causal["causal_transfer_pass"]),
                "erase_rescue_pass": bool(erase_map[str(task_id)]["pass"]),
                "controllable_carrier": controllable,
                "curved_attracting_functional_manifold": bool(geometry_map[str(task_id)]["pass"]),
            }
        )
    if any(row["controllable_carrier"] for row in combined):
        verdict = "controllable-causal-current-state-carrier-lead"
    elif any(row["causal_transfer_pass"] for row in combined):
        verdict = "causal-current-state-carrier-lead"
    elif any(
        carrier_map[str(task_id)]["full_state_positive_control"]["pass"]
        for task_id in config["focal_task_ids"]
    ):
        verdict = "distributed-state-transfer-only"
    else:
        verdict = "no-causal-state-carrier"
    decision = {
        "task_id": "causal-carrier-campaign-decision",
        "primary_endpoint": "behavior-follows-transplant-on-eight-fresh-histories",
        "minimum_completion_gate": completion,
        "record_counts": counts,
        "task_summaries": combined,
        "pass": any(bool(row["causal_transfer_pass"]) for row in combined),
        "verdict": verdict,
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "decision.json", decision)
    analysis = {
        "task_id": "causal-carrier-analysis",
        "experiment_id": config["experiment_id"],
        "status": final_status,
        "minimum_completion_gate": completion,
        "record_counts": counts,
        "registered_condition_count": int(config["registered_condition_count"]),
        "carrier_pass_count": int(carrier["pass_count"]),
        "erase_rescue_pass_count": int(erase["pass_count"]),
        "geometry_pass_count": int(geometry["pass_count"]),
        "verdict": verdict,
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    report_rows = "\n".join(
        f"- `{row['memory_task_id']}`: {row['carrier_classification']}; "
        f"causal transfer={row['causal_transfer_pass']}, erase/rescue={row['erase_rescue_pass']}, "
        f"curved geometry={row['curved_attracting_functional_manifold']}"
        for row in combined
    )
    report = f"""# Causal carrier transplant and curved-manifold experiment V1

Status: **{final_status}**  
Verdict: **{verdict}**

The primary test asked whether a discovery-frozen, compact part of the present
GRN state could transfer the six-probe remembered identity in both directions
on eight untouched exposure histories. Full-state swaps were positive
controls; sham, anti-ranked, and two norm-matched random swaps were negative
controls. Structural restoration, erase/rescue, and tangent/normal geometry
were separate secondary endpoints.

{report_rows}

Exact registered records: {sum(counts.values())}/{config['registered_condition_count']}.

Claim boundary: {config['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class CausalCarrierCampaign:
    def __init__(
        self,
        config_path: Path,
        manifold: Path,
        constrained: Path,
        contingency: Path,
        atlas: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_causal_carrier_config(self.config_path)
        self.manifold = manifold.resolve()
        self.constrained = constrained.resolve()
        self.contingency = contingency.resolve()
        self.atlas = atlas.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("causal-carrier workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed causal-carrier campaign cannot be resumed")
        self.parent_gate = validate_causal_carrier_parents(
            self.config,
            self.manifold,
            self.constrained,
            self.contingency,
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
                    raise ValueError(f"resumed causal-carrier registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"].get(
                "container_image_id"
            ):
                raise ValueError("resumed causal-carrier image differs")
        write_json(path, payload)
        write_json(self.output / "parent-gate.json", {"task_id": "parent-gate", "pass": True, **self.parent_gate})
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "primary": "A compact present-state component causally transfers six-probe remembered identity.",
                "secondary": [
                    "The component is erasable and rescuable.",
                    "Normal directions contract while tangent directions persist.",
                    "Behaviour can transfer without full structural restoration.",
                    "The switch-prone contrast uses a nonlinear carrier boundary.",
                ],
                "carrier_selection_frozen_before_fresh_outcomes": True,
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
            self._require_budget("discovery-plane-selection")
            static_start = time.process_time()
            selections = build_census_selections(self.config, self.manifold)
            write_json(self.output / "plane-census-selections.json", selections)
            discovery_args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed_index),
                )
                for task_id in self.config["focal_task_ids"]
                for seed_index in self.config["discovery_seed_indices"]
            ]
            self._require_budget("plane-census")
            census = _merge_shards(
                self.output,
                "plane-census",
                _parallel(_plane_census_worker, discovery_args, self.workers),
            )
            self._require_budget("carrier-model-freeze")
            models = build_carrier_models(
                self.config, census, self.manifold, self.constrained
            )
            write_json(self.output / "carrier-models.json", models)
            write_json(
                self.output / ".shards" / "static" / "selection-and-models.json",
                {
                    "protocol_digest": digest(self.config),
                    "stage": "static",
                    "aggregate_cpu_seconds": float(time.process_time() - static_start),
                    "aggregate_wall_seconds": 0.0,
                    "records": [],
                },
            )
            prospective_args = [
                (
                    str(self.config_path),
                    str(self.contingency),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed_index),
                )
                for task_id in self.config["focal_task_ids"]
                for seed_index in self.config["fresh_seed_indices"]
            ]
            dynamic_args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed_index),
                )
                for task_id in self.config["focal_task_ids"]
                for seed_index in self.config["fresh_seed_indices"]
            ]
            self._require_budget("fresh-exposure")
            _merge_shards(
                self.output,
                "fresh-exposure",
                _parallel(_fresh_exposure_worker, prospective_args, self.workers),
            )
            self._require_budget("no-op")
            no_ops = _merge_shards(
                self.output,
                "no-op",
                _parallel(_no_op_worker, dynamic_args, self.workers),
            )
            self._require_budget("carrier-transplants")
            transplants = _merge_shards(
                self.output,
                "carrier-transplants",
                _parallel(_transplant_worker, dynamic_args, self.workers),
            )
            metrics = transfer_metrics(transplants, no_ops, models, self.config)
            _write_jsonl(self.output / "transfer-metrics.jsonl", metrics)
            self._require_budget("local-geometry")
            _merge_shards(
                self.output,
                "local-geometry",
                _parallel(_local_geometry_worker, dynamic_args, self.workers),
            )
            self._require_budget("erase-rescue")
            _merge_shards(
                self.output,
                "erase-rescue",
                _parallel(_erase_rescue_worker, dynamic_args, self.workers),
            )
            self._state("analyzing", "analysis")
            self.ledger.close()
            analysis = analyze_causal_carrier(self.output, final_status="completed")
            if not analysis["minimum_completion_gate"]:
                raise ValueError("causal-carrier registered record set is incomplete")
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


def run_causal_carrier(
    config: Path,
    manifold: Path,
    constrained: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return CausalCarrierCampaign(
        config,
        manifold,
        constrained,
        contingency,
        atlas,
        upstream,
        output,
        workers,
    ).run()


def smoke_causal_carrier(
    config_path: Path,
    manifold: Path,
    constrained: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_causal_carrier_config(config_path)
    manifold, constrained, contingency, atlas, upstream, output = (
        manifold.resolve(),
        constrained.resolve(),
        contingency.resolve(),
        atlas.resolve(),
        upstream.resolve(),
        output.resolve(),
    )
    if output.exists():
        raise FileExistsError(f"causal-carrier smoke output exists: {output}")
    parents = validate_causal_carrier_parents(
        config, manifold, constrained, contingency, atlas, upstream
    )
    output.mkdir(parents=True)
    static_start = time.process_time()
    selections = build_census_selections(config, manifold)
    static_cpu = time.process_time() - static_start
    task_id = "37-10-41"
    discovery = next(
        row
        for row in selections["selections"]
        if row["memory_task_id"] == task_id
        and int(row["seed_index"]) == int(config["discovery_seed_indices"][0])
        and row["arm"] == "low"
    )
    memory, backend, reconstructed = _task_resources(config, atlas, upstream, task_id)
    census_fp = _fingerprint(
        backend, memory, _payload_state(discovery["terminal_state"]), config, reconstructed
    )
    history_config = _contingency_protocol(contingency)
    seed_index = int(config["fresh_seed_indices"][0])
    base = _naive_start(atlas, task_id)
    start, philox_seed = _perturb_start(
        base, memory, history_config, "exposure", task_id, seed_index
    )
    histories: dict[str, dict[str, Any]] = {}
    for arm, bound in (("low", 0), ("high", 1)):
        histories[arm] = _run_history(
            backend,
            memory,
            start.copy(),
            history_config,
            bound,
            _control_tokens("ucs_only"),
            seed_index=seed_index,
            probe_ucs_bound=reconstructed,
        )
    fresh_states = {
        arm: _payload_state(histories[arm]["checkpoints"]["12500"]["state"])
        for arm in ("low", "high")
    }
    fresh_refs = {
        arm: np.asarray(histories[arm]["checkpoints"]["12500"]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    no_op, no_op_cpu, no_op_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        fresh_states["low"],
        fresh_refs["high"],
        fresh_refs["low"],
    )
    full_transplant, transplant_cpu, transplant_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        State(
            fresh_states["high"].y.copy(),
            fresh_states["high"].w.copy(),
            fresh_states["high"].c.copy(),
            float(fresh_states["low"].t),
        ),
        fresh_refs["high"],
        fresh_refs["low"],
    )
    mode = _model_map(manifold / "mode-models.json")[task_id]
    scale = np.asarray(mode["scale"], dtype=float)
    bounds = np.asarray(memory.bounds, dtype=float)
    center = _payload_state(no_op["terminal_state"])
    separation = float(np.linalg.norm((fresh_states["high"].y - fresh_states["low"].y) / scale))
    direction, _, cap = local_radius_cap(
        center,
        mode["plane_transverse"],
        scale,
        bounds,
        separation,
        float(config["local_geometry"]["separation_cap_fraction"]),
        float(config["local_geometry"]["feasible_radius_fraction"]),
    )
    local_envelope = source_enclosing_envelope(center, bounds)
    local_start = State(
        center.y + 0.1 * cap * direction * scale,
        center.w.copy(),
        center.c.copy(),
        float(center.t),
    )
    if np.any(local_start.y < local_envelope[:, 0] - 1e-8) or np.any(
        local_start.y > local_envelope[:, 1] + 1e-8
    ):
        raise AssertionError("smoke local radius escaped the source envelope")
    local_result, local_cpu, local_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        local_start,
        fresh_refs["high"],
        fresh_refs["low"],
    )
    midpoint = State(
        0.5 * (fresh_states["low"].y + fresh_states["high"].y),
        0.5 * (fresh_states["low"].w + fresh_states["high"].w),
        fresh_states["high"].c.copy(),
        float(fresh_states["high"].t),
    )
    erase_spec = {
        "kind": "subspace",
        "basis": np.asarray(mode["memory_axis"], dtype=float)[:, None],
    }
    erased, erase_alpha, _ = apply_component_transplant(
        fresh_states["high"], midpoint, erase_spec, scale
    )
    if erased is None:
        erase_spec = {"kind": "coordinates", "indices": [memory.key.response_id]}
        erased, erase_alpha, _ = apply_component_transplant(
            fresh_states["high"], midpoint, erase_spec, scale
        )
    if erased is None:
        raise ValueError("smoke erase kernel has no feasible component")
    erase_phase = backend.run_unstimulated(
        erased,
        2500.0,
        memory.key.response_id,
        int(config["trajectory_samples"]),
        float(config["washout_chunk_duration"]),
    )
    erase_fp = _fingerprint(
        backend, memory, erase_phase.state, config, reconstructed
    )
    rescued, rescue_alpha, _ = apply_component_transplant(
        erase_phase.state, fresh_states["high"], erase_spec, scale
    )
    if rescued is None:
        raise ValueError("smoke rescue kernel has no feasible reinsertion")
    rescue_result, rescue_cpu, rescue_wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        rescued,
        fresh_refs["high"],
        fresh_refs["low"],
    )
    erase_rescue_cpu = float(
        erase_phase.cpu_seconds + erase_fp["cpu_seconds"] + rescue_cpu
    )
    erase_rescue_wall = float(
        erase_phase.wall_seconds + erase_fp["wall_seconds"] + rescue_wall
    )
    history_cpu = sum(float(row["cpu_seconds"]) for row in histories.values())
    history_wall = sum(float(row["wall_seconds"]) for row in histories.values())
    counts = config["registered_record_counts"]
    projected_cpu = float(config["projection_safety_factor"]) * (
        float(static_cpu)
        + float(census_fp["cpu_seconds"]) * int(counts["plane-census.jsonl"])
        + (history_cpu / 2.0) * int(counts["fresh-exposure.jsonl"])
        + float(no_op_cpu) * int(counts["no-op.jsonl"])
        + float(transplant_cpu) * int(counts["carrier-transplants.jsonl"])
        + float(local_cpu) * int(counts["local-geometry.jsonl"])
        + erase_rescue_cpu * int(counts["erase-rescue.jsonl"])
    )
    projected_wall = projected_cpu / float(config["max_workers"])
    valid = bool(
        census_fp["valid"]
        and all(bool(row["valid"]) for row in histories.values())
        and no_op["valid"]
        and full_transplant["valid"]
        and local_result["valid"]
        and erase_phase.valid
        and erase_fp["valid"]
        and rescue_result["valid"]
        and cap > 0.0
        and erase_alpha > 0.0
        and rescue_alpha > 0.0
    )
    allowed = bool(
        valid
        and sum(int(value) for value in counts.values())
        == int(config["registered_condition_count"])
        and projected_cpu < float(config["soft_aggregate_cpu_seconds"])
        and projected_wall < float(config["soft_wall_seconds"])
    )
    result = {
        "target": "causal-carrier-transplant",
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "parent_manifests": {
            name: parents[name]["manifest_sha256"]
            for name in ("manifold", "constrained", "contingency", "atlas")
        },
        "worker_cap": int(config["max_workers"]),
        "carrier_selection_frozen_before_fresh_outcomes": True,
        "fresh_seed_indices": list(config["fresh_seed_indices"]),
        "biological_probe": {
            "memory_task_id": task_id,
            "fresh_seed_index": seed_index,
            "philox_seed": int(philox_seed),
            "valid": valid,
            "plane_fingerprint": {
                "cpu_seconds": float(census_fp["cpu_seconds"]),
                "wall_seconds": float(census_fp["wall_seconds"]),
            },
            "fresh_history_pair": {
                "cpu_seconds": history_cpu,
                "wall_seconds": history_wall,
            },
            "no_op": {"cpu_seconds": no_op_cpu, "wall_seconds": no_op_wall},
            "full_transplant": {
                "cpu_seconds": transplant_cpu,
                "wall_seconds": transplant_wall,
            },
            "local_geometry": {"cpu_seconds": local_cpu, "wall_seconds": local_wall},
            "erase_rescue": {
                "cpu_seconds": erase_rescue_cpu,
                "wall_seconds": erase_rescue_wall,
            },
        },
        "projection": {
            "registered_condition_count": int(config["registered_condition_count"]),
            "record_counts": counts,
            "worst_case_aggregate_cpu_seconds": projected_cpu,
            "worst_case_active_wall_seconds_at_four_workers": projected_wall,
            "safety_factor": float(config["projection_safety_factor"]),
            "projection_basis": "measured plane-fingerprint, fresh-history, no-op, transplant, local-geometry, and erase/rescue kernels",
        },
        "deterministic_batch_plan": "stage-by-task-by-seed shards",
    }
    write_json(output / "smoke.json", result)
    return result


def causal_carrier_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {
        "output": str(output),
        "sealed": (output / "SHA256SUMS").is_file(),
    }
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "plane-census-selections",
        "carrier-models",
        "carrier-decision",
        "geometry-decision",
        "erase-rescue-decision",
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
        for stage in (
            "static",
            "plane-census",
            "fresh-exposure",
            "no-op",
            "carrier-transplants",
            "local-geometry",
            "erase-rescue",
        )
    }
    return result
