"""Prospective discrimination of three causal-carrier leads.

V2 is an exploratory, preregistered follow-up to the sealed V1 carrier run.
It uses untouched exposure seeds and keeps three questions separate:

* is the compact 204 carrier selective and controllable;
* is the 37 memory stored on a neutral sheet with contracting walls; and
* is the 10 contrast a direction-dependent nonlinear switch.

Every expensive unit is an independently resumable task/seed shard.  Invalid
or geometrically unavailable interventions occupy their registered slots and
are never replaced after outcomes are observed.
"""

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
from .atlas import state_payload
from .basin_geometry import _finish_record
from .causal_carrier import (
    _contingency_protocol,
    _payload_state,
    _stable_seed,
    _task_resources,
    donor_recipient_envelope,
    source_enclosing_envelope,
    transfer_metrics,
)
from .contingency import (
    _all_shard_cpu,
    _control_tokens,
    _fingerprint,
    _naive_start,
    _parallel,
    _perturb_start,
    _run_history,
    _runtime_manifest,
    _verify_parent,
    bipolar_score,
    quantile,
    vector_rms,
)
from .engine import State
from .exposure_autopsy import _merge_shards, _shard
from .memory_manifold import standardized_jacobian
from .renewal import ResourceLedger
from .upstream import PINNED_COMMIT, RELEASE_GENERATOR_COMMIT, validate_upstream


FOCAL_TASKS = ("37-10-41", "204-5-10", "10-1-32")
FRESH_COHORTS = {
    "grn-causal-carrier-discrimination-v2": tuple(range(216, 224)),
    "grn-causal-carrier-discrimination-v2r": tuple(range(224, 232)),
}
TASK_204 = "204-5-10"
TASK_37 = "37-10-41"
TASK_10 = "10-1-32"
RECORD_FILES = (
    "fresh-exposure.jsonl",
    "no-op.jsonl",
    "compact-dose-response.jsonl",
    "matched-controls.jsonl",
    "erase-rescue.jsonl",
    "neutral-geometry.jsonl",
    "bridge-transect.jsonl",
    "switch-dose-response.jsonl",
)
EXPECTED_COUNTS = {
    "fresh-exposure.jsonl": 48,
    "no-op.jsonl": 48,
    "compact-dose-response.jsonl": 576,
    "matched-controls.jsonl": 640,
    "erase-rescue.jsonl": 48,
    "neutral-geometry.jsonl": 1536,
    "bridge-transect.jsonl": 40,
    "switch-dose-response.jsonl": 448,
}


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(dict(row)) + "\n" for row in records))


def load_carrier_discrimination_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0" or config.get("experiment_kind") != "causal-carrier-discrimination":
        raise ValueError("not a supported causal-carrier-discrimination protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("carrier-discrimination protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("carrier-discrimination protocol does not pin the release generator")
    if tuple(config.get("focal_task_ids", ())) != FOCAL_TASKS:
        raise ValueError("carrier-discrimination focal cohort changed")
    expected_fresh = FRESH_COHORTS.get(str(config.get("experiment_id")))
    if expected_fresh is None:
        raise ValueError("unknown carrier-discrimination experiment ID")
    if tuple(int(value) for value in config.get("fresh_seed_indices", ())) != expected_fresh:
        raise ValueError("carrier-discrimination prospective cohort changed")
    if {str(k): int(v) for k, v in config.get("registered_record_counts", {}).items()} != EXPECTED_COUNTS:
        raise ValueError("carrier-discrimination registered record counts changed")
    if int(config.get("registered_condition_count", -1)) != sum(EXPECTED_COUNTS.values()):
        raise ValueError("carrier-discrimination registered condition count changed")
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
            raise ValueError(f"carrier-discrimination historical setting differs for {key}")
    if [float(value) for value in config["release_checkpoints"]] != [0.0, 25.0, 250.0, 2500.0, 12500.0]:
        raise ValueError("carrier-discrimination release checkpoints changed")
    compact = config["compact_204"]
    if [float(v) for v in compact["doses"]] != [0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0]:
        raise ValueError("204 dose ladder changed")
    if [float(v) for v in compact["control_doses"]] != [0.0025, 0.005, 0.01, 0.025, 0.1]:
        raise ValueError("204 matched-control ladder changed")
    if list(compact["conditions"]) != ["full-expression", "memory-axis", "top-ranked-1", "bottom-ranked-1"]:
        raise ValueError("204 intervention set changed")
    neutral = config["neutral_37"]
    if [float(v) for v in neutral["radii"]] != [0.005, 0.01, 0.025]:
        raise ValueError("37 radius ladder changed")
    if [float(v) for v in neutral["bridge_alphas"]] != [0.1, 0.25, 0.5, 0.75, 0.9]:
        raise ValueError("37 bridge transect changed")
    switch = config["switch_10"]
    if [float(v) for v in switch["doses"]] != [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]:
        raise ValueError("10 dose ladder changed")
    if list(switch["conditions"]) != ["full-expression", "top-ranked-1", "top-ranked-2", "anti-ranked-1"]:
        raise ValueError("10 intervention set changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("carrier-discrimination campaign must cap workers at four")
    if not (0.0 < float(config["soft_wall_seconds"]) < float(config["terminate_wall_seconds"]) < float(config["hard_wall_seconds"]) <= 14400.0):
        raise ValueError("carrier-discrimination wall contract exceeds four hours")
    if not (0.0 < float(config["soft_aggregate_cpu_seconds"]) < float(config["hard_aggregate_cpu_seconds"]) <= 57600.0):
        raise ValueError("carrier-discrimination aggregate CPU contract is invalid")
    return config


def validate_carrier_discrimination_parents(
    config: Mapping[str, Any], v1: Path, contingency: Path, atlas: Path, upstream: Path
) -> dict[str, Any]:
    gates = {
        "upstream": validate_upstream(upstream, str(config["upstream_commit"])),
        "v1": _verify_parent(v1, str(config["v1_parent_experiment_id"]), config["v1_parent_hashes"]),
        "contingency": _verify_parent(
            contingency,
            str(config["contingency_parent_experiment_id"]),
            config["contingency_parent_hashes"],
        ),
        "atlas": _verify_parent(atlas, str(config["atlas_parent_experiment_id"]), config["atlas_parent_hashes"]),
    }
    decision = json.loads((v1 / "decision.json").read_text(encoding="utf-8"))
    if decision.get("verdict") != "distributed-state-transfer-only" or not decision.get("minimum_completion_gate"):
        raise ValueError("V1 parent lacks the sealed distributed-state-transfer lead")
    models = json.loads((v1 / "carrier-models.json").read_text(encoding="utf-8"))
    if {str(row["memory_task_id"]) for row in models.get("models", ())} != set(FOCAL_TASKS):
        raise ValueError("V1 carrier model cohort is incomplete")
    return gates


def _model_map(v1: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads((v1 / "carrier-models.json").read_text(encoding="utf-8"))
    return {str(row["memory_task_id"]): dict(row) for row in payload["models"]}


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


def _unit(values: Sequence[float]) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12 or not np.isfinite(norm):
        raise ValueError("cannot normalize a zero or non-finite vector")
    return vector / norm


def _orthonormal(values: Sequence[Sequence[float]], dimension: int) -> np.ndarray:
    matrix = np.asarray(values, dtype=float).reshape(int(dimension), -1)
    if matrix.size == 0:
        return np.empty((int(dimension), 0), dtype=float)
    q, r = np.linalg.qr(matrix)
    rank = int(np.sum(np.abs(np.diag(r)) > 1e-10))
    return q[:, :rank]


def _maximum_radius(state: State, direction: np.ndarray, scale: np.ndarray, envelope: np.ndarray) -> float:
    limits: list[float] = []
    for value, component, width, lower, upper in zip(
        state.y, direction, scale, envelope[:, 0], envelope[:, 1]
    ):
        delta = float(component * width)
        if delta > 1e-14:
            limits.append(max(0.0, float(upper - value)) / delta)
        elif delta < -1e-14:
            limits.append(max(0.0, float(value - lower)) / -delta)
    return 0.0 if not limits else float(min(limits))


def state_at_dose(
    recipient: State,
    donor: State,
    condition: str,
    dose: float,
    model: Mapping[str, Any],
) -> tuple[State | None, dict[str, Any]]:
    """Apply an exact, no-clipping fractional expression intervention."""

    scale = np.asarray(model["scale"], dtype=float)
    delta = (donor.y - recipient.y) / scale
    condition = str(condition)
    if condition == "full-expression":
        shift = delta
        dimension = len(delta)
    elif condition == "memory-axis":
        basis = _orthonormal(np.asarray(model["memory_axis"], dtype=float)[:, None], len(delta))
        shift = basis @ (basis.T @ delta)
        dimension = int(basis.shape[1])
    elif condition == "top-ranked-1":
        indices = [int(model["ranked_nodes"][0])]
        shift = np.zeros_like(delta)
        shift[indices] = delta[indices]
        dimension = 1
    elif condition == "top-ranked-2":
        indices = [int(v) for v in model["ranked_nodes"][:2]]
        shift = np.zeros_like(delta)
        shift[indices] = delta[indices]
        dimension = 2
    elif condition in {"bottom-ranked-1", "anti-ranked-1"}:
        key = "anti_ranked_nodes" if condition == "anti-ranked-1" else "ranked_nodes"
        index = int(model[key][0] if key == "anti_ranked_nodes" else model[key][-1])
        shift = np.zeros_like(delta)
        shift[index] = delta[index]
        dimension = 1
    else:
        raise ValueError(f"unknown dose condition: {condition}")
    requested = float(dose) * float(np.linalg.norm(shift))
    if requested <= 1e-12:
        return None, {"requested_standardized_norm": requested, "effective_dimension": dimension}
    standardized_shift = float(dose) * shift
    envelope = donor_recipient_envelope(recipient, donor)
    raw_shift = standardized_shift * scale
    line_fraction = 1.0
    for value, raw, lower, upper in zip(
        recipient.y, raw_shift, envelope[:, 0], envelope[:, 1]
    ):
        if raw > 0.0:
            line_fraction = min(
                line_fraction, float(max(0.0, upper - value) / raw)
            )
        elif raw < 0.0:
            line_fraction = min(
                line_fraction, float(max(0.0, value - lower) / -raw)
            )
    line_fraction = float(max(0.0, min(1.0, line_fraction)))
    if 0.0 < line_fraction < 1.0:
        line_fraction = float(np.nextafter(line_fraction, 0.0))
    if line_fraction <= 0.0:
        return None, {
            "requested_standardized_norm": requested,
            "applied_standardized_norm": 0.0,
            "effective_dimension": dimension,
            "coefficient_fraction": 0.0,
            "line_fraction": 0.0,
        }
    y = recipient.y + line_fraction * raw_shift
    if np.any(y < envelope[:, 0] - 1e-8) or np.any(y > envelope[:, 1] + 1e-8):
        raise AssertionError("dose intervention escaped donor-recipient envelope")
    return (
        State(y, recipient.w.copy(), recipient.c.copy(), float(recipient.t)),
        {
            "requested_standardized_norm": requested,
            "applied_standardized_norm": line_fraction * requested,
            "effective_dimension": dimension,
            "coefficient_fraction": float(dose) * line_fraction,
            "line_fraction": line_fraction,
            "standardized_shift": line_fraction * standardized_shift,
        },
    )


def _diverse_selection(candidates: Sequence[Mapping[str, Any]], count: int) -> list[dict[str, Any]]:
    remaining = [dict(row) for row in candidates]
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < int(count):
        if not selected:
            chosen = min(remaining, key=lambda row: (float(row.get("observer_fraction", 0.0)), int(row["candidate_index"])))
        else:
            def score(row: Mapping[str, Any]) -> tuple[float, float, int]:
                vector = np.asarray(row["direction"], dtype=float)
                diversity = min(1.0 - abs(float(np.dot(vector, np.asarray(prior["direction"], dtype=float)))) for prior in selected)
                return diversity, -float(row.get("observer_fraction", 0.0)), -int(row["candidate_index"])
            chosen = max(remaining, key=score)
        selected.append(chosen)
        remaining.remove(chosen)
    return selected


def _rayleigh_ranked_diverse_selection(
    candidates: Sequence[Mapping[str, Any]], count: int, maximum_absolute_cosine: float = 0.95
) -> list[dict[str, Any]]:
    """Take the most contracting candidates while avoiding duplicate axes."""

    ordered = sorted(
        (dict(row) for row in candidates),
        key=lambda row: (float(row["rayleigh_quotient"]), int(row["candidate_index"])),
    )
    selected: list[dict[str, Any]] = []
    for row in ordered:
        vector = np.asarray(row["direction"], dtype=float)
        if all(
            abs(float(np.dot(vector, np.asarray(prior["direction"], dtype=float))))
            <= float(maximum_absolute_cosine)
            for prior in selected
        ):
            selected.append(row)
        if len(selected) == int(count):
            return selected
    chosen = {int(row["candidate_index"]) for row in selected}
    for row in ordered:
        if int(row["candidate_index"]) not in chosen:
            selected.append(row)
        if len(selected) == int(count):
            break
    return selected


def matched_control_slots(
    config: Mapping[str, Any],
    recipient: State,
    donor: State,
    model: Mapping[str, Any],
    bounds: np.ndarray,
    seed_index: int,
    recipient_arm: str,
    dose: float,
) -> list[dict[str, Any]]:
    """Freeze up to eight norm-matched controls without outcome feedback."""

    scale = np.asarray(model["scale"], dtype=float)
    top = int(model["ranked_nodes"][0])
    delta = (donor.y - recipient.y) / scale
    carrier = np.zeros_like(delta)
    carrier[top] = delta[top]
    target_norm = float(dose) * float(np.linalg.norm(carrier))
    carrier_unit = _unit(carrier)
    observer = np.asarray(model["observer_map"]["matrix"], dtype=float)
    observer_carrier = observer @ carrier_unit
    observer_denominator = max(float(np.dot(observer_carrier, observer_carrier)), 1e-12)
    envelope = source_enclosing_envelope(recipient, bounds)
    rng = np.random.Generator(
        np.random.Philox(_stable_seed(config, "matched-control", TASK_204, seed_index, recipient_arm, dose))
    )
    eligible: list[dict[str, Any]] = []
    for candidate_index in range(int(config["compact_204"]["candidate_pool_size"])):
        direction = rng.normal(size=len(scale))
        direction -= float(np.dot(direction, carrier_unit)) * carrier_unit
        # Work in the source-envelope inward cone.  In particular, coordinates
        # whose registered range and source value coincide are structurally
        # fixed and must be removed rather than allowed to force radius zero.
        direction = _cone_project(direction, recipient, envelope, scale)
        if direction is None:
            continue
        direction -= float(np.dot(direction, carrier_unit)) * carrier_unit
        direction = _cone_project(direction, recipient, envelope, scale)
        if direction is None:
            continue
        feasible = _maximum_radius(recipient, direction, scale, envelope)
        if feasible + 1e-10 < target_norm:
            continue
        carrier_cosine = abs(float(np.dot(direction, carrier_unit)))
        predicted = observer @ direction
        observer_fraction = abs(float(np.dot(predicted, observer_carrier) / observer_denominator))
        if carrier_cosine > float(config["compact_204"]["maximum_carrier_cosine"]) + 1e-12:
            continue
        if observer_fraction > float(config["compact_204"]["maximum_observer_transfer_fraction"]) + 1e-12:
            continue
        eligible.append(
            {
                "candidate_index": candidate_index,
                "direction": direction,
                "maximum_feasible_radius": feasible,
                "carrier_cosine": carrier_cosine,
                "observer_fraction": observer_fraction,
            }
        )
    selected = _diverse_selection(eligible, int(config["compact_204"]["controls_per_cell"]))
    slots: list[dict[str, Any]] = []
    for slot in range(int(config["compact_204"]["controls_per_cell"])):
        if slot < len(selected):
            row = selected[slot]
            slots.append({"slot": slot, "available": True, "target_norm": target_norm, **row})
        else:
            slots.append(
                {
                    "slot": slot,
                    "available": False,
                    "target_norm": target_norm,
                    "reason": "no-feasible-orthogonal-observer-quiet-candidate",
                }
            )
    return slots


def _cone_project(direction: np.ndarray, state: State, envelope: np.ndarray, scale: np.ndarray) -> np.ndarray | None:
    result = np.asarray(direction, dtype=float).copy()
    tolerance = 1e-9
    for index, (value, lower, upper) in enumerate(zip(state.y, envelope[:, 0], envelope[:, 1])):
        raw = float(result[index] * scale[index])
        if value <= lower + tolerance and raw < 0.0:
            result[index] = 0.0
        if value >= upper - tolerance and raw > 0.0:
            result[index] = 0.0
    norm = float(np.linalg.norm(result))
    return None if norm <= 1e-12 else result / norm


def neutral_direction_slots(
    config: Mapping[str, Any],
    state: State,
    model: Mapping[str, Any],
    bounds: np.ndarray,
    jacobian: np.ndarray,
    separation: float,
    seed_index: int,
    arm: str,
) -> list[dict[str, Any]]:
    """Select 16 tangent and 16 tangent-orthogonal inward probes."""

    scale = np.asarray(model["scale"], dtype=float)
    tangent = _orthonormal(model["tangent_basis"], len(scale))
    if tangent.shape[1] < 1:
        raise ValueError("V1 task 37 tangent basis is empty")
    envelope = source_enclosing_envelope(state, bounds)
    target_radius = max(float(value) for value in config["neutral_37"]["radii"]) * float(separation)
    sym = 0.5 * (np.asarray(jacobian, dtype=float) + np.asarray(jacobian, dtype=float).T)
    rng = np.random.Generator(np.random.Philox(_stable_seed(config, "neutral-directions", TASK_37, seed_index, arm)))
    tangent_candidates: dict[int, list[dict[str, Any]]] = {-1: [], 1: []}
    normal_candidates: list[dict[str, Any]] = []
    for candidate_index in range(int(config["neutral_37"]["candidate_pool_size"])):
        raw = rng.normal(size=len(scale))
        tangent_raw = tangent @ (tangent.T @ raw)
        tangent_direction = _cone_project(tangent_raw, state, envelope, scale)
        if tangent_direction is not None:
            projection = float(np.linalg.norm(tangent.T @ tangent_direction))
            feasible = _maximum_radius(state, tangent_direction, scale, envelope)
            if projection >= float(config["neutral_37"]["minimum_tangent_projection"]) and feasible + 1e-10 >= target_radius:
                orientation = 1 if float(np.dot(tangent_direction, tangent[:, 0])) >= 0.0 else -1
                tangent_candidates[orientation].append(
                    {
                        "candidate_index": candidate_index,
                        "direction": tangent_direction,
                        "maximum_feasible_radius": feasible,
                        "tangent_projection": projection,
                        "rayleigh_quotient": float(tangent_direction @ sym @ tangent_direction),
                    }
                )
        normal_raw = raw - tangent @ (tangent.T @ raw)
        normal_direction = _cone_project(normal_raw, state, envelope, scale)
        if normal_direction is not None:
            projection = float(np.linalg.norm(tangent.T @ normal_direction))
            feasible = _maximum_radius(state, normal_direction, scale, envelope)
            if projection <= float(config["neutral_37"]["maximum_normal_tangent_projection"]) and feasible + 1e-10 >= target_radius:
                normal_candidates.append(
                    {
                        "candidate_index": candidate_index,
                        "direction": normal_direction,
                        "maximum_feasible_radius": feasible,
                        "tangent_projection": projection,
                        "rayleigh_quotient": float(normal_direction @ sym @ normal_direction),
                    }
                )
    slots: list[dict[str, Any]] = []
    per_orientation = int(config["neutral_37"]["tangent_directions_per_orientation"])
    for orientation in (-1, 1):
        selected = _diverse_selection(tangent_candidates[orientation], per_orientation)
        for slot in range(per_orientation):
            common = {"kind": "tangent", "orientation": orientation, "slot": slot}
            if slot < len(selected):
                slots.append({**common, "available": True, **selected[slot]})
            else:
                slots.append({**common, "available": False, "reason": "no-feasible-inward-tangent-direction"})
    selected_normals = _rayleigh_ranked_diverse_selection(
        normal_candidates, int(config["neutral_37"]["normal_direction_count"])
    )
    for slot in range(int(config["neutral_37"]["normal_direction_count"])):
        common = {"kind": "normal", "orientation": 0, "slot": slot}
        if slot < len(selected_normals):
            slots.append({**common, "available": True, **selected_normals[slot]})
        else:
            slots.append({**common, "available": False, "reason": "no-feasible-inward-tangent-orthogonal-direction"})
    if len(slots) != 32:
        raise AssertionError("neutral direction registration is not 32 slots")
    return slots


def _fresh_exposure_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, contingency_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "fresh-exposure", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    history_config = _contingency_protocol(Path(contingency_path))
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), str(task_id))
    base = _naive_start(Path(atlas_path), str(task_id))
    start, philox_seed = _perturb_start(base, memory, history_config, "carrier-discrimination", str(task_id), int(seed_index))
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
                "task_id": f"v2-fresh|{task_id}|{seed_index}|{arm}",
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


def _no_op_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "no-op", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), str(task_id))
    references = {
        arm: np.asarray(fresh[(str(task_id), int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        source = _payload_state(fresh[(str(task_id), int(seed_index), arm)]["source_state"])
        result, used_cpu, used_wall = _finish_record(
            backend, memory, reconstructed, config, source, references["high"], references["low"]
        )
        cpu += used_cpu
        wall += used_wall
        records.append(
            {
                "task_id": f"v2-no-op|{task_id}|{seed_index}|{arm}",
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


def build_intervention_geometry(
    config: Mapping[str, Any], v1: Path, atlas: Path, upstream: Path, output: Path
) -> tuple[dict[str, Any], float]:
    """Freeze all controls and local directions before intervention outcomes."""

    started = time.process_time()
    fresh = _fresh_map(output)
    no_ops = _no_op_map(output)
    models = _model_map(v1)
    compact_cells: list[dict[str, Any]] = []
    memory_204, _, _ = _task_resources(config, atlas, upstream, TASK_204)
    bounds_204 = np.asarray(memory_204.bounds, dtype=float)
    for seed_index in config["fresh_seed_indices"]:
        states = {
            arm: _payload_state(fresh[(TASK_204, int(seed_index), arm)]["source_state"])
            for arm in ("low", "high")
        }
        for recipient_arm, donor_arm in (("low", "high"), ("high", "low")):
            for dose in config["compact_204"]["control_doses"]:
                slots = matched_control_slots(
                    config,
                    states[recipient_arm],
                    states[donor_arm],
                    models[TASK_204],
                    bounds_204,
                    int(seed_index),
                    recipient_arm,
                    float(dose),
                )
                compact_cells.append(
                    {
                        "memory_task_id": TASK_204,
                        "seed_index": int(seed_index),
                        "recipient_arm": recipient_arm,
                        "donor_arm": donor_arm,
                        "dose": float(dose),
                        "slots": slots,
                    }
                )
    neutral_cells: list[dict[str, Any]] = []
    memory_37, backend_37, _ = _task_resources(config, atlas, upstream, TASK_37)
    bounds_37 = np.asarray(memory_37.bounds, dtype=float)
    model_37 = models[TASK_37]
    scale_37 = np.asarray(model_37["scale"], dtype=float)
    for seed_index in config["fresh_seed_indices"]:
        centers = {
            arm: _payload_state(no_ops[(TASK_37, int(seed_index), arm)]["terminal_state"])
            for arm in ("low", "high")
        }
        separation = float(np.linalg.norm((centers["high"].y - centers["low"].y) / scale_37))
        for arm in ("low", "high"):
            jacobian, residual = standardized_jacobian(backend_37, centers[arm], scale_37)
            slots = neutral_direction_slots(
                config,
                centers[arm],
                model_37,
                bounds_37,
                jacobian,
                separation,
                int(seed_index),
                arm,
            )
            eigenvalues = np.linalg.eigvals(jacobian)
            neutral_cells.append(
                {
                    "memory_task_id": TASK_37,
                    "seed_index": int(seed_index),
                    "arm": arm,
                    "source_state_digest": digest(state_payload(centers[arm])),
                    "separation": separation,
                    "jacobian": jacobian,
                    "residual": residual,
                    "spectral_abscissa": float(np.max(np.real(eigenvalues))),
                    "slots": slots,
                }
            )
    payload = {
        "task_id": "v2-intervention-geometry",
        "protocol_digest": digest(config),
        "selection_frozen_before_post_intervention_outcomes": True,
        "fresh_endpoint_states_used_only_for_feasibility": True,
        "post_intervention_outcomes_used": False,
        "compact_control_cells": compact_cells,
        "neutral_geometry_cells": neutral_cells,
    }
    return payload, float(time.process_time() - started)


def _geometry_maps(output: Path) -> tuple[dict[tuple[int, str, float], list[dict[str, Any]]], dict[tuple[int, str], dict[str, Any]]]:
    payload = json.loads((output / "intervention-geometry.json").read_text(encoding="utf-8"))
    compact = {
        (int(row["seed_index"]), str(row["recipient_arm"]), float(row["dose"])): [dict(slot) for slot in row["slots"]]
        for row in payload["compact_control_cells"]
    }
    neutral = {
        (int(row["seed_index"]), str(row["arm"])): dict(row)
        for row in payload["neutral_geometry_cells"]
    }
    return compact, neutral


def _compact_dose_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, v1_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "compact-dose-response", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    no_ops = _no_op_map(output)
    model = _model_map(Path(v1_path))[TASK_204]
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_204)
    states = {arm: _payload_state(fresh[(TASK_204, int(seed_index), arm)]["source_state"]) for arm in ("low", "high")}
    references = {arm: np.asarray(no_ops[(TASK_204, int(seed_index), arm)]["fingerprint"], dtype=float) for arm in ("low", "high")}
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for recipient_arm, donor_arm in (("low", "high"), ("high", "low")):
        for condition in config["compact_204"]["conditions"]:
            for dose in config["compact_204"]["doses"]:
                condition_id = f"compact-dose|{recipient_arm}-to-{donor_arm}|{condition}|d={float(dose):g}"
                common = {
                    "assay": "compact-carrier-dose-response",
                    "model_id": int(memory.key.model_id),
                    "seed_role": "fresh-prospective",
                    "recipient_arm": recipient_arm,
                    "donor_arm": donor_arm,
                    "target_arm": donor_arm,
                    "condition": str(condition),
                    "dose": float(dose),
                    "is_primary_candidate": str(condition) == "top-ranked-1",
                    "primary_eligible": True,
                }
                start, intervention = state_at_dose(
                    states[recipient_arm], states[donor_arm], str(condition), float(dose), model
                )
                if start is None:
                    records.append(_invalid_record(TASK_204, int(seed_index), condition_id, "zero-component-at-dose", **common, **intervention))
                    continue
                result, used_cpu, used_wall = _finish_record(
                    backend, memory, reconstructed, config, start, references["high"], references["low"]
                )
                cpu += used_cpu
                wall += used_wall
                records.append(
                    {
                        "task_id": f"compact-dose|{TASK_204}|{seed_index}|{recipient_arm}-to-{donor_arm}|{condition}|{float(dose):g}",
                        "condition_id": condition_id,
                        "memory_task_id": TASK_204,
                        "seed_index": int(seed_index),
                        **common,
                        **{key: value for key, value in intervention.items() if key != "standardized_shift"},
                        **result,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "compact-dose-response",
        "memory_task_id": TASK_204,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _matched_control_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, v1_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "matched-controls", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    no_ops = _no_op_map(output)
    model = _model_map(Path(v1_path))[TASK_204]
    scale = np.asarray(model["scale"], dtype=float)
    compact, _ = _geometry_maps(output)
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_204)
    states = {arm: _payload_state(fresh[(TASK_204, int(seed_index), arm)]["source_state"]) for arm in ("low", "high")}
    references = {arm: np.asarray(no_ops[(TASK_204, int(seed_index), arm)]["fingerprint"], dtype=float) for arm in ("low", "high")}
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for recipient_arm, donor_arm in (("low", "high"), ("high", "low")):
        recipient = states[recipient_arm]
        envelope = source_enclosing_envelope(recipient, np.asarray(memory.bounds, dtype=float))
        for dose in config["compact_204"]["control_doses"]:
            for slot in compact[(int(seed_index), recipient_arm, float(dose))]:
                condition = f"matched-control-{int(slot['slot']) + 1}"
                condition_id = f"matched|{recipient_arm}-to-{donor_arm}|d={float(dose):g}|slot={int(slot['slot'])}"
                common = {
                    "assay": "norm-matched-carrier-orthogonal-control",
                    "model_id": int(memory.key.model_id),
                    "seed_role": "fresh-prospective",
                    "recipient_arm": recipient_arm,
                    "donor_arm": donor_arm,
                    "target_arm": donor_arm,
                    "condition": condition,
                    "dose": float(dose),
                    "control_slot": int(slot["slot"]),
                    "is_primary_candidate": False,
                    "primary_eligible": False,
                    "requested_standardized_norm": float(slot["target_norm"]),
                }
                if not bool(slot.get("available")):
                    records.append(_invalid_record(TASK_204, int(seed_index), condition_id, str(slot.get("reason")), **common))
                    continue
                direction = np.asarray(slot["direction"], dtype=float)
                y = recipient.y + float(slot["target_norm"]) * direction * scale
                if np.any(y < envelope[:, 0] - 1e-8) or np.any(y > envelope[:, 1] + 1e-8):
                    raise AssertionError("matched control escaped source-enclosing envelope")
                start = State(y, recipient.w.copy(), recipient.c.copy(), float(recipient.t))
                result, used_cpu, used_wall = _finish_record(
                    backend, memory, reconstructed, config, start, references["high"], references["low"]
                )
                cpu += used_cpu
                wall += used_wall
                records.append(
                    {
                        "task_id": f"matched|{TASK_204}|{seed_index}|{recipient_arm}-to-{donor_arm}|{float(dose):g}|{int(slot['slot'])}",
                        "condition_id": condition_id,
                        "memory_task_id": TASK_204,
                        "seed_index": int(seed_index),
                        "carrier_cosine": float(slot["carrier_cosine"]),
                        "observer_fraction": float(slot["observer_fraction"]),
                        "candidate_index": int(slot["candidate_index"]),
                        **common,
                        **result,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "matched-controls",
        "memory_task_id": TASK_204,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _erase_rescue_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, v1_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "erase-rescue", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    no_ops = _no_op_map(output)
    model = _model_map(Path(v1_path))[TASK_204]
    top = int(model["ranked_nodes"][0])
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_204)
    states = {arm: _payload_state(fresh[(TASK_204, int(seed_index), arm)]["source_state"]) for arm in ("low", "high")}
    references = {arm: np.asarray(no_ops[(TASK_204, int(seed_index), arm)]["fingerprint"], dtype=float) for arm in ("low", "high")}
    reference_scores = {arm: bipolar_score(references[arm], references["high"], references["low"]) for arm in ("low", "high")}
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        opposite = "high" if arm == "low" else "low"
        for sequence in ("sham", "source-rescue", "opposite-insertion"):
            source = states[arm]
            erased_y = source.y.copy()
            if sequence != "sham":
                erased_y[top] = 0.5 * (states[arm].y[top] + states[opposite].y[top])
            erased = State(erased_y, source.w.copy(), source.c.copy(), float(source.t))
            phase = backend.run_unstimulated(
                erased,
                float(config["compact_204"]["erase_delay"]),
                memory.key.response_id,
                int(config["trajectory_samples"]),
                float(config["washout_chunk_duration"]),
            )
            erase_fp = _fingerprint(backend, memory, phase.state, config, reconstructed)
            reinserted_y = phase.state.y.copy()
            if sequence == "source-rescue":
                reinserted_y[top] = states[arm].y[top]
            elif sequence == "opposite-insertion":
                reinserted_y[top] = states[opposite].y[top]
            reinserted = State(
                reinserted_y, phase.state.w.copy(), phase.state.c.copy(), float(phase.state.t)
            )
            result, used_cpu, used_wall = _finish_record(
                backend,
                memory,
                reconstructed,
                config,
                reinserted,
                references["high"],
                references["low"],
            )
            cpu += float(phase.cpu_seconds + erase_fp["cpu_seconds"] + used_cpu)
            wall += float(phase.wall_seconds + erase_fp["wall_seconds"] + used_wall)
            erase_score = bipolar_score(erase_fp["fingerprint"], references["high"], references["low"])
            final_score = result.get("bipolar_score")
            sign = 1.0 if arm == "high" else -1.0
            source_oriented = None if reference_scores[arm] is None else sign * float(reference_scores[arm])
            opposite_oriented = None if reference_scores[opposite] is None else sign * float(reference_scores[opposite])
            erase_oriented = None if erase_score is None else sign * float(erase_score)
            final_oriented = None if final_score is None else sign * float(final_score)
            span = None
            if source_oriented is not None and opposite_oriented is not None:
                span = max(source_oriented - opposite_oriented, 1e-12)
            erase_effect = (
                None
                if span is None or erase_oriented is None
                else float((source_oriented - erase_oriented) / span)
            )
            rescue_fraction = None
            if erase_oriented is not None and final_oriented is not None and source_oriented is not None:
                denominator = source_oriented - erase_oriented
                rescue_fraction = None if abs(denominator) <= 1e-12 else float((final_oriented - erase_oriented) / denominator)
            opposite_switch = (
                None
                if span is None or final_oriented is None
                else float((source_oriented - final_oriented) / span)
            )
            target_reference = references[opposite] if sequence == "opposite-insertion" else references[arm]
            records.append(
                {
                    "task_id": f"erase-rescue|{TASK_204}|{seed_index}|{arm}|{sequence}",
                    "condition_id": f"erase-rescue|{arm}|{sequence}",
                    "assay": "midpoint-erase-and-coordinate-reinsertion",
                    "memory_task_id": TASK_204,
                    "model_id": int(memory.key.model_id),
                    "seed_index": int(seed_index),
                    "seed_role": "fresh-prospective",
                    "arm": arm,
                    "opposite_arm": opposite,
                    "sequence": sequence,
                    "carrier_node": top,
                    "erasure_value": float(erased_y[top]),
                    "reinsertion_value": float(reinserted_y[top]),
                    "post_erasure_state": state_payload(phase.state),
                    "post_erasure_fingerprint": erase_fp["fingerprint"],
                    "post_erasure_bipolar_score": erase_score,
                    "erase_effect_fraction": erase_effect,
                    "rescue_fraction": rescue_fraction,
                    "opposite_switch_fraction": opposite_switch,
                    "target_fingerprint_rms": vector_rms(np.asarray(result["fingerprint"], dtype=float) - target_reference),
                    "valid": bool(phase.valid and erase_fp["valid"] and result["valid"]),
                    **{key: value for key, value in result.items() if key != "valid"},
                }
            )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "erase-rescue",
        "memory_task_id": TASK_204,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _neutral_geometry_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, v1_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "neutral-geometry", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    no_ops = _no_op_map(output)
    model = _model_map(Path(v1_path))[TASK_37]
    scale = np.asarray(model["scale"], dtype=float)
    _, neutral = _geometry_maps(output)
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_37)
    references = {arm: np.asarray(no_ops[(TASK_37, int(seed_index), arm)]["fingerprint"], dtype=float) for arm in ("low", "high")}
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        center = _payload_state(no_ops[(TASK_37, int(seed_index), arm)]["terminal_state"])
        cell = neutral[(int(seed_index), arm)]
        separation = float(cell["separation"])
        envelope = source_enclosing_envelope(center, np.asarray(memory.bounds, dtype=float))
        for direction_index, slot in enumerate(cell["slots"]):
            for radius_fraction in config["neutral_37"]["radii"]:
                radius = float(radius_fraction) * separation
                condition_id = (
                    f"neutral|{arm}|{slot['kind']}|o={int(slot['orientation'])}|"
                    f"slot={int(slot['slot'])}|r={float(radius_fraction):g}"
                )
                common = {
                    "assay": "neutral-sheet-tangent-normal-probe",
                    "model_id": int(memory.key.model_id),
                    "seed_role": "fresh-prospective",
                    "arm": arm,
                    "direction_kind": str(slot["kind"]),
                    "orientation": int(slot["orientation"]),
                    "direction_slot": int(slot["slot"]),
                    "direction_index": direction_index,
                    "radius_fraction": float(radius_fraction),
                    "requested_radius": radius,
                    "separation": separation,
                }
                if not bool(slot.get("available")):
                    records.append(_invalid_record(TASK_37, int(seed_index), condition_id, str(slot.get("reason")), **common))
                    continue
                direction = np.asarray(slot["direction"], dtype=float)
                y = center.y + radius * direction * scale
                if np.any(y < envelope[:, 0] - 1e-8) or np.any(y > envelope[:, 1] + 1e-8):
                    raise AssertionError("neutral geometry probe escaped source-enclosing envelope")
                start = State(y, center.w.copy(), center.c.copy(), float(center.t))
                result, used_cpu, used_wall = _finish_record(
                    backend, memory, reconstructed, config, start, references["high"], references["low"]
                )
                cpu += used_cpu
                wall += used_wall
                checkpoint_ratios: dict[str, float | None] = {}
                for checkpoint, checkpoint_row in result["checkpoints"].items():
                    state = _payload_state(checkpoint_row["state"])
                    checkpoint_ratios[str(checkpoint)] = (
                        None if radius <= 1e-12 else float(np.linalg.norm((state.y - center.y) / scale) / radius)
                    )
                terminal = _payload_state(result["terminal_state"])
                final_ratio = None if radius <= 1e-12 else float(np.linalg.norm((terminal.y - center.y) / scale) / radius)
                fp_rms = vector_rms(np.asarray(result["fingerprint"], dtype=float) - references[arm])
                records.append(
                    {
                        "task_id": f"neutral|{TASK_37}|{seed_index}|{arm}|{direction_index}|{float(radius_fraction):g}",
                        "condition_id": condition_id,
                        "memory_task_id": TASK_37,
                        "seed_index": int(seed_index),
                        "direction": direction,
                        "candidate_index": int(slot["candidate_index"]),
                        "tangent_projection": float(slot["tangent_projection"]),
                        "rayleigh_quotient": float(slot["rayleigh_quotient"]),
                        "checkpoint_distance_ratios": checkpoint_ratios,
                        "final_distance_ratio": final_ratio,
                        "center_fingerprint_rms": fp_rms,
                        "behavior_returned": bool(fp_rms <= float(config["decision"]["fingerprint_rms_max"])),
                        **common,
                        **result,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "neutral-geometry",
        "memory_task_id": TASK_37,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _bridge_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "bridge-transect", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    no_ops = _no_op_map(output)
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_37)
    low = _payload_state(no_ops[(TASK_37, int(seed_index), "low")]["terminal_state"])
    high = _payload_state(no_ops[(TASK_37, int(seed_index), "high")]["terminal_state"])
    references = {arm: np.asarray(no_ops[(TASK_37, int(seed_index), arm)]["fingerprint"], dtype=float) for arm in ("low", "high")}
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for alpha in config["neutral_37"]["bridge_alphas"]:
        value = float(alpha)
        start = State(
            low.y + value * (high.y - low.y),
            low.w + value * (high.w - low.w),
            low.c.copy(),
            max(float(low.t), float(high.t)),
        )
        result, used_cpu, used_wall = _finish_record(
            backend, memory, reconstructed, config, start, references["high"], references["low"]
        )
        cpu += used_cpu
        wall += used_wall
        records.append(
            {
                "task_id": f"bridge|{TASK_37}|{seed_index}|{value:g}",
                "condition_id": f"bridge|alpha={value:g}",
                "assay": "endpoint-bridge-transect",
                "memory_task_id": TASK_37,
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "seed_role": "fresh-prospective",
                "alpha": value,
                **result,
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "bridge-transect",
        "memory_task_id": TASK_37,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _switch_dose_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, v1_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_carrier_discrimination_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "switch-dose-response", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    no_ops = _no_op_map(output)
    model = _model_map(Path(v1_path))[TASK_10]
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_10)
    states = {arm: _payload_state(fresh[(TASK_10, int(seed_index), arm)]["source_state"]) for arm in ("low", "high")}
    references = {arm: np.asarray(no_ops[(TASK_10, int(seed_index), arm)]["fingerprint"], dtype=float) for arm in ("low", "high")}
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for recipient_arm, donor_arm in (("low", "high"), ("high", "low")):
        for condition in config["switch_10"]["conditions"]:
            for dose in config["switch_10"]["doses"]:
                condition_id = f"switch-dose|{recipient_arm}-to-{donor_arm}|{condition}|d={float(dose):g}"
                common = {
                    "assay": "nonlinear-switch-dose-response",
                    "model_id": int(memory.key.model_id),
                    "seed_role": "fresh-prospective",
                    "recipient_arm": recipient_arm,
                    "donor_arm": donor_arm,
                    "target_arm": donor_arm,
                    "condition": str(condition),
                    "dose": float(dose),
                    "is_primary_candidate": str(condition) == "top-ranked-1",
                    "primary_eligible": True,
                }
                start, intervention = state_at_dose(
                    states[recipient_arm], states[donor_arm], str(condition), float(dose), model
                )
                if start is None:
                    records.append(_invalid_record(TASK_10, int(seed_index), condition_id, "zero-component-at-dose", **common, **intervention))
                    continue
                result, used_cpu, used_wall = _finish_record(
                    backend, memory, reconstructed, config, start, references["high"], references["low"]
                )
                cpu += used_cpu
                wall += used_wall
                records.append(
                    {
                        "task_id": f"switch-dose|{TASK_10}|{seed_index}|{recipient_arm}-to-{donor_arm}|{condition}|{float(dose):g}",
                        "condition_id": condition_id,
                        "memory_task_id": TASK_10,
                        "seed_index": int(seed_index),
                        **common,
                        **{key: value for key, value in intervention.items() if key != "standardized_shift"},
                        **result,
                    }
                )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "switch-dose-response",
        "memory_task_id": TASK_10,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _metric_success(row: Mapping[str, Any], config: Mapping[str, Any]) -> bool:
    return bool(
        row.get("valid")
        and row.get("target_oriented_bipolar_score") is not None
        and float(row["target_oriented_bipolar_score"]) >= float(config["decision"]["target_bipolar_min"])
        and row.get("target_fingerprint_rms") is not None
        and float(row["target_fingerprint_rms"]) <= float(config["decision"]["fingerprint_rms_max"])
    )


def _dose_summaries(
    metrics: Sequence[Mapping[str, Any]],
    conditions: Sequence[str],
    doses: Sequence[float],
    config: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], float | None]]:
    summaries: list[dict[str, Any]] = []
    thresholds: dict[tuple[str, str], float | None] = {}
    for condition in conditions:
        for recipient_arm in ("low", "high"):
            direction = f"{recipient_arm}-to-{'high' if recipient_arm == 'low' else 'low'}"
            passing_doses: list[float] = []
            for dose in doses:
                rows = [
                    row
                    for row in metrics
                    if str(row.get("condition")) == str(condition)
                    and str(row.get("recipient_arm")) == recipient_arm
                    and math.isclose(float(row.get("dose", -1.0)), float(dose))
                ]
                valid = [row for row in rows if bool(row.get("valid"))]
                successes = sum(_metric_success(row, config) for row in rows)
                if successes >= int(config["decision"]["minimum_consistent_seeds"]):
                    passing_doses.append(float(dose))
                summaries.append(
                    {
                        "condition": str(condition),
                        "direction": direction,
                        "dose": float(dose),
                        "registered_count": len(rows),
                        "valid_count": len(valid),
                        "success_count": successes,
                        "median_target_bipolar": quantile(
                            [float(row["target_oriented_bipolar_score"]) for row in valid if row.get("target_oriented_bipolar_score") is not None],
                            0.5,
                        ),
                        "median_fingerprint_rms": quantile(
                            [float(row["target_fingerprint_rms"]) for row in valid if row.get("target_fingerprint_rms") is not None],
                            0.5,
                        ),
                    }
                )
            thresholds[(str(condition), direction)] = min(passing_doses) if passing_doses else None
    return summaries, thresholds


def compact_204_decision(
    dose_metrics: Sequence[Mapping[str, Any]],
    control_metrics: Sequence[Mapping[str, Any]],
    erase_rows: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = config["compact_204"]
    summaries, thresholds = _dose_summaries(
        dose_metrics, settings["conditions"], settings["doses"], config
    )
    selectivity_cells: list[dict[str, Any]] = []
    for dose in settings["control_doses"]:
        for recipient_arm in ("low", "high"):
            donor_arm = "high" if recipient_arm == "low" else "low"
            direction = f"{recipient_arm}-to-{donor_arm}"
            top_rows = [
                row for row in dose_metrics
                if str(row.get("condition")) == "top-ranked-1"
                and str(row.get("recipient_arm")) == recipient_arm
                and math.isclose(float(row.get("dose", -1.0)), float(dose))
            ]
            controls = [
                row for row in control_metrics
                if str(row.get("recipient_arm")) == recipient_arm
                and math.isclose(float(row.get("dose", -1.0)), float(dose))
            ]
            availability_by_seed: dict[int, int] = {}
            switch_by_seed: dict[int, bool] = {}
            for row in controls:
                seed = int(row["seed_index"])
                availability_by_seed[seed] = availability_by_seed.get(seed, 0) + int(bool(row.get("valid")))
                switch_by_seed[seed] = switch_by_seed.get(seed, False) or _metric_success(row, config)
            top_success = sum(_metric_success(row, config) for row in top_rows)
            eligible_seed_count = sum(
                count >= int(settings["minimum_controls_per_seed"])
                for count in availability_by_seed.values()
            )
            control_switch_seed_count = sum(switch_by_seed.values())
            passed = bool(
                top_success >= int(config["decision"]["minimum_consistent_seeds"])
                and eligible_seed_count >= int(config["decision"]["minimum_consistent_seeds"])
                and control_switch_seed_count <= int(config["decision"]["control_switch_seed_max"])
            )
            selectivity_cells.append(
                {
                    "direction": direction,
                    "dose": float(dose),
                    "top_success_count": top_success,
                    "control_valid_count": sum(bool(row.get("valid")) for row in controls),
                    "control_eligible_seed_count": eligible_seed_count,
                    "control_switch_seed_count": control_switch_seed_count,
                    "pass": passed,
                }
            )
    selective_doses = [
        float(dose)
        for dose in settings["control_doses"]
        if all(
            row["pass"]
            for row in selectivity_cells
            if math.isclose(float(row["dose"]), float(dose))
        )
    ]
    erase_summaries: list[dict[str, Any]] = []
    for arm in ("low", "high"):
        sham = [row for row in erase_rows if str(row.get("arm")) == arm and str(row.get("sequence")) == "sham" and bool(row.get("valid"))]
        rescue = [row for row in erase_rows if str(row.get("arm")) == arm and str(row.get("sequence")) == "source-rescue" and bool(row.get("valid"))]
        opposite = [row for row in erase_rows if str(row.get("arm")) == arm and str(row.get("sequence")) == "opposite-insertion" and bool(row.get("valid"))]
        sham_count = sum((1.0 if arm == "high" else -1.0) * float(row["bipolar_score"]) >= float(config["decision"]["target_bipolar_min"]) for row in sham if row.get("bipolar_score") is not None)
        erase_count = sum(float(row["erase_effect_fraction"]) >= float(config["decision"]["erase_effect_fraction_min"]) for row in rescue if row.get("erase_effect_fraction") is not None)
        rescue_count = sum(
            float(row["rescue_fraction"]) >= float(config["decision"]["rescue_fraction_min"])
            and float(row["target_fingerprint_rms"]) <= float(config["decision"]["fingerprint_rms_max"])
            for row in rescue if row.get("rescue_fraction") is not None and row.get("target_fingerprint_rms") is not None
        )
        opposite_count = sum(
            float(row["opposite_switch_fraction"]) >= float(config["decision"]["rescue_fraction_min"])
            and float(row["target_fingerprint_rms"]) <= float(config["decision"]["fingerprint_rms_max"])
            for row in opposite if row.get("opposite_switch_fraction") is not None and row.get("target_fingerprint_rms") is not None
        )
        required = int(config["decision"]["minimum_consistent_seeds"])
        erase_summaries.append(
            {
                "arm": arm,
                "sham_preservation_count": sham_count,
                "erase_effect_count": erase_count,
                "source_rescue_count": rescue_count,
                "opposite_insertion_count": opposite_count,
                "pass": bool(sham_count >= required and erase_count >= required and rescue_count >= required and opposite_count >= required),
            }
        )
    top_bidirectional = all(
        thresholds[("top-ranked-1", direction)] is not None
        for direction in ("low-to-high", "high-to-low")
    )
    controls_available_at_transfer_dose = any(
        row["top_success_count"] >= int(config["decision"]["minimum_consistent_seeds"])
        and row["control_eligible_seed_count"] >= int(config["decision"]["minimum_consistent_seeds"])
        for row in selectivity_cells
    )
    selective = bool(selective_doses)
    controllable = selective and all(row["pass"] for row in erase_summaries)
    if controllable:
        classification = "selective-controllable-single-coordinate-carrier"
    elif selective:
        classification = "selective-single-coordinate-carrier"
    elif top_bidirectional and not controls_available_at_transfer_dose:
        classification = "compact-transfer-active-dose-control-inconclusive"
    elif top_bidirectional:
        classification = "compact-but-nonselective-transfer"
    else:
        classification = "no-bidirectional-compact-carrier"
    return {
        "task_id": "compact-204-decision",
        "memory_task_id": TASK_204,
        "dose_summaries": summaries,
        "minimum_success_doses": [
            {"condition": condition, "direction": direction, "dose": value}
            for (condition, direction), value in sorted(thresholds.items())
        ],
        "selectivity_cells": selectivity_cells,
        "selective_doses": selective_doses,
        "active_dose_matched_controls_available": controls_available_at_transfer_dose,
        "erase_rescue": erase_summaries,
        "selective": selective,
        "controllable": controllable,
        "classification": classification,
    }


def neutral_37_decision(
    records: Sequence[Mapping[str, Any]], bridge_rows: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    for arm in ("low", "high"):
        for kind in ("tangent", "normal"):
            for radius in config["neutral_37"]["radii"]:
                per_seed: list[dict[str, Any]] = []
                for seed in config["fresh_seed_indices"]:
                    rows = [
                        row for row in records
                        if str(row.get("arm")) == arm
                        and str(row.get("direction_kind")) == kind
                        and int(row.get("seed_index", -1)) == int(seed)
                        and math.isclose(float(row.get("radius_fraction", -1.0)), float(radius))
                        and bool(row.get("valid"))
                    ]
                    ratios = [float(row["final_distance_ratio"]) for row in rows if row.get("final_distance_ratio") is not None]
                    median_ratio = quantile(ratios, 0.5)
                    early = {
                        checkpoint: quantile(
                            [float(row["checkpoint_distance_ratios"][checkpoint]) for row in rows if row.get("checkpoint_distance_ratios", {}).get(checkpoint) is not None],
                            0.5,
                        )
                        for checkpoint in ("25", "250", "2500", "12500")
                    }
                    if kind == "tangent":
                        passed = bool(
                            median_ratio is not None
                            and float(config["decision"]["tangent_ratio_min"]) <= median_ratio <= float(config["decision"]["tangent_ratio_max"])
                        )
                    else:
                        passed = bool(median_ratio is not None and median_ratio <= float(config["decision"]["normal_ratio_max"]))
                    per_seed.append(
                        {
                            "seed_index": int(seed),
                            "valid_direction_count": len(rows),
                            "median_final_ratio": median_ratio,
                            "median_checkpoint_ratios": early,
                            "behavior_return_count": sum(bool(row.get("behavior_returned")) for row in rows),
                            "pass": passed,
                        }
                    )
                groups.append(
                    {
                        "arm": arm,
                        "direction_kind": kind,
                        "radius_fraction": float(radius),
                        "seed_pass_count": sum(bool(row["pass"]) for row in per_seed),
                        "per_seed": per_seed,
                    }
                )
    bridge_summaries: list[dict[str, Any]] = []
    for seed in config["fresh_seed_indices"]:
        rows = sorted(
            [row for row in bridge_rows if int(row.get("seed_index", -1)) == int(seed) and bool(row.get("valid"))],
            key=lambda row: float(row["alpha"]),
        )
        scores = [float(row["bipolar_score"]) for row in rows if row.get("bipolar_score") is not None]
        monotonic = len(scores) == len(config["neutral_37"]["bridge_alphas"]) and all(
            right >= left - float(config["decision"]["monotonic_tolerance"])
            for left, right in zip(scores, scores[1:])
        )
        bridge_summaries.append(
            {
                "seed_index": int(seed),
                "valid_point_count": len(rows),
                "scores": scores,
                "monotonic": monotonic,
                "interior_identity_count": sum(abs(value) < float(config["decision"]["target_bipolar_min"]) for value in scores),
            }
        )
    largest = max(float(v) for v in config["neutral_37"]["radii"])
    largest_groups = [row for row in groups if math.isclose(float(row["radius_fraction"]), largest)]
    required = int(config["decision"]["minimum_consistent_seeds"])
    tangent_persists = all(row["seed_pass_count"] >= required for row in largest_groups if row["direction_kind"] == "tangent")
    normal_contracts = all(row["seed_pass_count"] >= required for row in largest_groups if row["direction_kind"] == "normal")
    tangent_contracts = all(
        sum(
            row_seed["median_final_ratio"] is not None and row_seed["median_final_ratio"] <= float(config["decision"]["normal_ratio_max"])
            for row_seed in row["per_seed"]
        ) >= required
        for row in largest_groups if row["direction_kind"] == "tangent"
    )
    normal_persists = all(
        sum(
            row_seed["median_final_ratio"] is not None
            and float(config["decision"]["tangent_ratio_min"]) <= row_seed["median_final_ratio"] <= float(config["decision"]["tangent_ratio_max"])
            for row_seed in row["per_seed"]
        ) >= required
        for row in largest_groups if row["direction_kind"] == "normal"
    )
    unstable = any(
        sum(
            row_seed["median_final_ratio"] is not None and row_seed["median_final_ratio"] > float(config["decision"]["tangent_ratio_max"])
            for row_seed in row["per_seed"]
        ) >= required
        for row in largest_groups
    )
    bridge_monotonic_count = sum(bool(row["monotonic"]) for row in bridge_summaries)
    if tangent_persists and normal_contracts:
        classification = "curved-neutral-sheet-with-contracting-walls" if bridge_monotonic_count >= required else "curved-neutral-sheet-bridge-unresolved"
    elif tangent_contracts and normal_contracts:
        classification = "point-attractor"
    elif tangent_persists and normal_persists:
        classification = "flat-neutral-region-without-detected-walls"
    elif unstable:
        classification = "locally-unstable-or-expanding"
    else:
        classification = "mixed-or-unresolved-local-geometry"
    return {
        "task_id": "neutral-37-decision",
        "memory_task_id": TASK_37,
        "group_summaries": groups,
        "bridge_summaries": bridge_summaries,
        "bridge_monotonic_count": bridge_monotonic_count,
        "tangent_persists": tangent_persists,
        "normal_contracts": normal_contracts,
        "classification": classification,
    }


def switch_10_decision(metrics: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config["switch_10"]
    summaries, thresholds = _dose_summaries(metrics, settings["conditions"], settings["doses"], config)
    curves: dict[tuple[str, str], list[int]] = {}
    for row in summaries:
        curves.setdefault((str(row["condition"]), str(row["direction"])), []).append(int(row["success_count"]))
    nonmonotone_events: list[dict[str, Any]] = []
    for (condition, direction), counts in curves.items():
        for left_index, (left, right) in enumerate(zip(counts, counts[1:])):
            if right <= left - int(config["decision"]["nonmonotone_drop_min"]):
                nonmonotone_events.append(
                    {
                        "kind": "dose-increase-removes-transfer",
                        "condition": condition,
                        "direction": direction,
                        "from_dose": float(settings["doses"][left_index]),
                        "to_dose": float(settings["doses"][left_index + 1]),
                        "success_drop": left - right,
                    }
                )
    for direction in ("low-to-high", "high-to-low"):
        top1 = curves[("top-ranked-1", direction)]
        top2 = curves[("top-ranked-2", direction)]
        for dose, one, two in zip(settings["doses"], top1, top2):
            if two <= one - int(config["decision"]["nonmonotone_drop_min"]):
                nonmonotone_events.append(
                    {
                        "kind": "adding-second-node-removes-transfer",
                        "direction": direction,
                        "dose": float(dose),
                        "success_drop": one - two,
                    }
                )
    directional_thresholds = {
        str(condition): {
            direction: thresholds[(str(condition), direction)]
            for direction in ("low-to-high", "high-to-low")
        }
        for condition in settings["conditions"]
    }
    asymmetric_conditions: list[str] = []
    for condition, pair in directional_thresholds.items():
        values = [pair["low-to-high"], pair["high-to-low"]]
        if (values[0] is None) != (values[1] is None) or (
            values[0] is not None
            and values[1] is not None
            and not math.isclose(float(values[0]), float(values[1]))
        ):
            asymmetric_conditions.append(condition)
    asymmetric = bool(asymmetric_conditions)
    compact_transfer = any(
        directional_thresholds[condition][direction] is not None
        for condition in ("top-ranked-1", "top-ranked-2", "anti-ranked-1")
        for direction in ("low-to-high", "high-to-low")
    )
    full_transfer = any(
        directional_thresholds["full-expression"][direction] is not None
        for direction in ("low-to-high", "high-to-low")
    )
    if nonmonotone_events and asymmetric:
        classification = "asymmetric-nonmonotone-switch"
    elif nonmonotone_events:
        classification = "nonmonotone-component-interaction"
    elif asymmetric and compact_transfer:
        classification = "direction-asymmetric-compact-threshold-switch"
    elif asymmetric:
        classification = "direction-asymmetric-full-state-threshold-switch"
    elif compact_transfer:
        classification = "monotone-compact-dose-responsive-transfer"
    elif full_transfer:
        classification = "monotone-full-state-dose-responsive-transfer"
    else:
        classification = "no-state-switch-transfer"
    return {
        "task_id": "switch-10-decision",
        "memory_task_id": TASK_10,
        "dose_summaries": summaries,
        "minimum_success_doses": [
            {"condition": condition, "direction": direction, "dose": value}
            for (condition, direction), value in sorted(thresholds.items())
        ],
        "directional_thresholds": directional_thresholds,
        "top1_directional_thresholds": directional_thresholds["top-ranked-1"],
        "asymmetric": asymmetric,
        "asymmetric_conditions": asymmetric_conditions,
        "compact_transfer": compact_transfer,
        "full_state_transfer": full_transfer,
        "nonmonotone_events": nonmonotone_events,
        "classification": classification,
    }


def analyze_carrier_discrimination(output: Path, final_status: str = "completed") -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    models = json.loads((output / "v1-carrier-models.json").read_text(encoding="utf-8"))
    no_ops = list(read_jsonl(output / "no-op.jsonl"))
    compact_rows = list(read_jsonl(output / "compact-dose-response.jsonl"))
    control_rows = list(read_jsonl(output / "matched-controls.jsonl"))
    switch_rows = list(read_jsonl(output / "switch-dose-response.jsonl"))
    compact_metrics = transfer_metrics(compact_rows, no_ops, models, config)
    control_metrics = transfer_metrics(control_rows, no_ops, models, config)
    switch_metrics = transfer_metrics(switch_rows, no_ops, models, config)
    for rows, metrics in ((compact_rows, compact_metrics), (control_rows, control_metrics), (switch_rows, switch_metrics)):
        dose_by_id = {str(row["task_id"]): float(row["dose"]) for row in rows}
        for metric in metrics:
            metric["dose"] = dose_by_id[str(metric["source_task_id"])]
    _write_jsonl(output / "compact-transfer-metrics.jsonl", compact_metrics)
    _write_jsonl(output / "control-transfer-metrics.jsonl", control_metrics)
    _write_jsonl(output / "switch-transfer-metrics.jsonl", switch_metrics)
    compact = compact_204_decision(
        compact_metrics,
        control_metrics,
        list(read_jsonl(output / "erase-rescue.jsonl")),
        config,
    )
    neutral = neutral_37_decision(
        list(read_jsonl(output / "neutral-geometry.jsonl")),
        list(read_jsonl(output / "bridge-transect.jsonl")),
        config,
    )
    switch = switch_10_decision(switch_metrics, config)
    write_json(output / "compact-204-decision.json", compact)
    write_json(output / "neutral-37-decision.json", neutral)
    write_json(output / "switch-10-decision.json", switch)
    counts = {name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES}
    completion = counts == EXPECTED_COUNTS
    verdict = "three-leads-unresolved"
    if compact["controllable"]:
        verdict = "selective-controllable-compact-carrier-lead"
    elif compact["selective"]:
        verdict = "selective-compact-carrier-lead"
    elif neutral["classification"].startswith("curved-neutral-sheet"):
        verdict = "neutral-sheet-memory-lead"
    elif switch["nonmonotone_events"]:
        verdict = "nonlinear-switch-memory-lead"
    elif switch["asymmetric"]:
        verdict = "direction-asymmetric-switch-memory-lead"
    decision = {
        "task_id": "carrier-discrimination-v2-decision",
        "primary_scope": "exploratory-hypothesis-generation",
        "minimum_completion_gate": completion,
        "record_counts": counts,
        "registered_condition_count": int(config["registered_condition_count"]),
        "task_summaries": {
            TASK_204: compact["classification"],
            TASK_37: neutral["classification"],
            TASK_10: switch["classification"],
        },
        "verdict": verdict,
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "decision.json", decision)
    analysis = {
        "task_id": "carrier-discrimination-v2-analysis",
        "experiment_id": str(config["experiment_id"]),
        "status": final_status,
        "minimum_completion_gate": completion,
        "record_counts": counts,
        "registered_condition_count": int(config["registered_condition_count"]),
        "verdict": verdict,
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    report = f"""# Causal carrier discrimination V2

Status: **{final_status}**

Verdict: **{verdict}**

This exploratory prospective run discriminates three leads inherited from the
sealed V1 discovery run on eight untouched exposure histories (seeds 216–223).

- `{TASK_204}`: **{compact['classification']}**. Selective={compact['selective']}; controllable={compact['controllable']}.
- `{TASK_37}`: **{neutral['classification']}**. Tangent persistence={neutral['tangent_persists']}; normal contraction={neutral['normal_contracts']}.
- `{TASK_10}`: **{switch['classification']}**. Asymmetric={switch['asymmetric']}; nonlinear events={len(switch['nonmonotone_events'])}.

Exact registered records: {sum(counts.values())}/{config['registered_condition_count']}.

Geometrically unavailable controls remain registered nulls and are not replaced.

Claim boundary: {config['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class CarrierDiscriminationCampaign:
    def __init__(
        self,
        config_path: Path,
        v1: Path,
        contingency: Path,
        atlas: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_carrier_discrimination_config(self.config_path)
        self.v1 = v1.resolve()
        self.contingency = contingency.resolve()
        self.atlas = atlas.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("carrier-discrimination workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed carrier-discrimination campaign cannot be resumed")
        self.parent_gate = validate_carrier_discrimination_parents(
            self.config, self.v1, self.contingency, self.atlas, self.upstream
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
            "inputs": {
                "v1": str(self.v1),
                "contingency": str(self.contingency),
                "atlas": str(self.atlas),
                "upstream": str(self.upstream),
            },
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
                    raise ValueError(f"resumed carrier-discrimination registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"].get("container_image_id"):
                raise ValueError("resumed carrier-discrimination image differs")
        write_json(path, payload)
        write_json(self.output / "parent-gate.json", {"task_id": "parent-gate", "pass": True, **self.parent_gate})
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "task_204": "A single present-state coordinate is selectively causal and bidirectionally controllable.",
                "task_37": "Remembered states lie along locally neutral directions bounded by contracting normal directions.",
                "task_10": "The compact intervention response is asymmetric or non-monotone because it crosses a nonlinear switch boundary.",
                "v1_is_discovery_parent_only": True,
                "post_intervention_outcome_adaptation_allowed": False,
                "threshold_relaxation_allowed": False,
            },
        )
        write_json(
            self.output / "v1-carrier-models.json",
            json.loads((self.v1 / "carrier-models.json").read_text(encoding="utf-8")),
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
            focused_args = [
                (
                    str(self.config_path),
                    str(self.v1),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    int(seed_index),
                )
                for seed_index in self.config["fresh_seed_indices"]
            ]
            bridge_args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    int(seed_index),
                )
                for seed_index in self.config["fresh_seed_indices"]
            ]
            self._require_budget("fresh-exposure")
            _merge_shards(
                self.output,
                "fresh-exposure",
                _parallel(_fresh_exposure_worker, prospective_args, self.workers),
            )
            self._require_budget("no-op")
            _merge_shards(
                self.output,
                "no-op",
                _parallel(_no_op_worker, dynamic_args, self.workers),
            )
            self._require_budget("intervention-geometry-freeze")
            static_start = time.process_time()
            geometry, geometry_cpu = build_intervention_geometry(
                self.config, self.v1, self.atlas, self.upstream, self.output
            )
            write_json(self.output / "intervention-geometry.json", geometry)
            write_json(
                self.output / ".shards" / "static" / "intervention-geometry.json",
                {
                    "protocol_digest": digest(self.config),
                    "stage": "static",
                    "aggregate_cpu_seconds": max(geometry_cpu, time.process_time() - static_start),
                    "aggregate_wall_seconds": 0.0,
                    "records": [],
                },
            )
            stages = (
                ("compact-dose-response", _compact_dose_worker, focused_args),
                ("matched-controls", _matched_control_worker, focused_args),
                ("erase-rescue", _erase_rescue_worker, focused_args),
                ("neutral-geometry", _neutral_geometry_worker, focused_args),
                ("bridge-transect", _bridge_worker, bridge_args),
                ("switch-dose-response", _switch_dose_worker, focused_args),
            )
            for stage, worker, args in stages:
                self._require_budget(stage)
                rows = _merge_shards(self.output, stage, _parallel(worker, args, self.workers))
                expected = EXPECTED_COUNTS[f"{stage}.jsonl"]
                if len(rows) != expected:
                    raise ValueError(f"registered {stage} count differs: {len(rows)} != {expected}")
            self._state("analyzing", "analysis")
            self.ledger.close()
            analysis = analyze_carrier_discrimination(self.output, final_status="completed")
            if not analysis["minimum_completion_gate"]:
                raise ValueError("carrier-discrimination registered record set is incomplete")
            self._state("completed", "complete", verdict=analysis["verdict"])
            write_checksums(self.output)
            return 0
        except BaseException as error:
            incidents_path = self.output / "runtime-incidents.json"
            incidents = json.loads(incidents_path.read_text(encoding="utf-8")) if incidents_path.is_file() else {"incidents": []}
            prior_state = json.loads((self.output / "state.json").read_text(encoding="utf-8")) if (self.output / "state.json").is_file() else {}
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


def run_carrier_discrimination(
    config: Path,
    v1: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return CarrierDiscriminationCampaign(
        config, v1, contingency, atlas, upstream, output, workers
    ).run()


def smoke_carrier_discrimination(
    config_path: Path,
    v1: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_carrier_discrimination_config(config_path)
    v1, contingency, atlas, upstream, output = (
        v1.resolve(), contingency.resolve(), atlas.resolve(), upstream.resolve(), output.resolve()
    )
    if output.exists():
        raise FileExistsError(f"carrier-discrimination smoke output exists: {output}")
    parents = validate_carrier_discrimination_parents(config, v1, contingency, atlas, upstream)
    output.mkdir(parents=True)
    models = _model_map(v1)
    history_config = _contingency_protocol(contingency)
    seed_index = int(config["fresh_seed_indices"][0])
    task_probes: list[dict[str, Any]] = []
    histories_cpu = histories_wall = no_op_cpu = no_op_wall = intervention_cpu = intervention_wall = 0.0
    all_valid = True
    erase_kernel_cpu = erase_kernel_wall = 0.0
    for task_id in FOCAL_TASKS:
        memory, backend, reconstructed = _task_resources(config, atlas, upstream, task_id)
        base = _naive_start(atlas, task_id)
        start, philox_seed = _perturb_start(base, memory, history_config, "carrier-discrimination", task_id, seed_index)
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
        states = {arm: _payload_state(histories[arm]["checkpoints"]["12500"]["state"]) for arm in ("low", "high")}
        fresh_refs = {arm: np.asarray(histories[arm]["checkpoints"]["12500"]["fingerprint"], dtype=float) for arm in ("low", "high")}
        histories_cpu += sum(float(row["cpu_seconds"]) for row in histories.values())
        histories_wall += sum(float(row["wall_seconds"]) for row in histories.values())
        no_ops: dict[str, dict[str, Any]] = {}
        for arm in ("low", "high"):
            no_ops[arm], used_cpu, used_wall = _finish_record(
                backend, memory, reconstructed, config, states[arm], fresh_refs["high"], fresh_refs["low"]
            )
            no_op_cpu += used_cpu
            no_op_wall += used_wall
        references = {arm: np.asarray(no_ops[arm]["fingerprint"], dtype=float) for arm in ("low", "high")}
        if task_id == TASK_204:
            condition, dose = "top-ranked-1", 0.01
        elif task_id == TASK_37:
            condition, dose = "full-expression", 0.01
        else:
            condition, dose = "top-ranked-1", 0.1
        probe_start, _ = state_at_dose(states["low"], states["high"], condition, dose, models[task_id])
        if probe_start is None:
            raise ValueError(f"smoke intervention unavailable for {task_id}")
        probe, used_cpu, used_wall = _finish_record(
            backend, memory, reconstructed, config, probe_start, references["high"], references["low"]
        )
        intervention_cpu += used_cpu
        intervention_wall += used_wall
        geometry_valid = True
        geometry_detail: dict[str, Any] = {}
        if task_id == TASK_37:
            centers = {arm: _payload_state(no_ops[arm]["terminal_state"]) for arm in ("low", "high")}
            scale = np.asarray(models[task_id]["scale"], dtype=float)
            separation = float(np.linalg.norm((centers["high"].y - centers["low"].y) / scale))
            jacobian, residual = standardized_jacobian(backend, centers["low"], scale)
            slots = neutral_direction_slots(
                config,
                centers["low"],
                models[task_id],
                np.asarray(memory.bounds, dtype=float),
                jacobian,
                separation,
                seed_index,
                "low",
            )
            geometry_valid = any(bool(slot.get("available")) for slot in slots)
            geometry_detail = {
                "available_direction_count": sum(bool(slot.get("available")) for slot in slots),
                "residual_norm": float(np.linalg.norm(residual)),
            }
        if task_id == TASK_204:
            top = int(models[task_id]["ranked_nodes"][0])
            erased_y = states["high"].y.copy()
            erased_y[top] = 0.5 * (states["low"].y[top] + states["high"].y[top])
            phase = backend.run_unstimulated(
                State(erased_y, states["high"].w.copy(), states["high"].c.copy(), float(states["high"].t)),
                float(config["compact_204"]["erase_delay"]),
                memory.key.response_id,
                int(config["trajectory_samples"]),
                float(config["washout_chunk_duration"]),
            )
            erase_fp = _fingerprint(backend, memory, phase.state, config, reconstructed)
            rescued_y = phase.state.y.copy()
            rescued_y[top] = states["high"].y[top]
            rescue, rescue_cpu, rescue_wall = _finish_record(
                backend,
                memory,
                reconstructed,
                config,
                State(rescued_y, phase.state.w.copy(), phase.state.c.copy(), float(phase.state.t)),
                references["high"],
                references["low"],
            )
            erase_kernel_cpu = float(phase.cpu_seconds + erase_fp["cpu_seconds"] + rescue_cpu)
            erase_kernel_wall = float(phase.wall_seconds + erase_fp["wall_seconds"] + rescue_wall)
            all_valid = all_valid and bool(phase.valid and erase_fp["valid"] and rescue["valid"])
        all_valid = all_valid and all(bool(row["valid"]) for row in histories.values()) and all(bool(row["valid"]) for row in no_ops.values()) and bool(probe["valid"]) and geometry_valid
        task_probes.append(
            {
                "memory_task_id": task_id,
                "philox_seed": int(philox_seed),
                "history_valid": all(bool(row["valid"]) for row in histories.values()),
                "no_op_valid": all(bool(row["valid"]) for row in no_ops.values()),
                "intervention_valid": bool(probe["valid"]),
                "geometry": geometry_detail,
            }
        )
    counts = config["registered_record_counts"]
    ordinary_count = (
        int(counts["compact-dose-response.jsonl"])
        + int(counts["matched-controls.jsonl"])
        + int(counts["neutral-geometry.jsonl"])
        + int(counts["bridge-transect.jsonl"])
        + int(counts["switch-dose-response.jsonl"])
    )
    projected_cpu = float(config["projection_safety_factor"]) * (
        (histories_cpu / 6.0) * int(counts["fresh-exposure.jsonl"])
        + (no_op_cpu / 6.0) * int(counts["no-op.jsonl"])
        + (intervention_cpu / 3.0) * ordinary_count
        + erase_kernel_cpu * int(counts["erase-rescue.jsonl"])
    )
    projected_wall = projected_cpu / float(config["max_workers"])
    allowed = bool(
        all_valid
        and sum(int(value) for value in counts.values()) == int(config["registered_condition_count"])
        and projected_cpu < float(config["soft_aggregate_cpu_seconds"])
        and projected_wall < float(config["soft_wall_seconds"])
    )
    result = {
        "target": str(config["experiment_id"]),
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "parent_manifests": {
            name: parents[name]["manifest_sha256"] for name in ("v1", "contingency", "atlas")
        },
        "worker_cap": int(config["max_workers"]),
        "fresh_seed_indices": list(config["fresh_seed_indices"]),
        "intervention_selection_frozen_before_post_intervention_outcomes": True,
        "biological_probes": task_probes,
        "projection": {
            "registered_condition_count": int(config["registered_condition_count"]),
            "record_counts": counts,
            "worst_case_aggregate_cpu_seconds": projected_cpu,
            "worst_case_active_wall_seconds_at_four_workers": projected_wall,
            "safety_factor": float(config["projection_safety_factor"]),
            "measured_history_cpu_seconds": histories_cpu,
            "measured_no_op_cpu_seconds": no_op_cpu,
            "measured_intervention_cpu_seconds": intervention_cpu,
            "measured_erase_rescue_cpu_seconds": erase_kernel_cpu,
        },
        "deterministic_batch_plan": "stage-by-task-by-seed shards",
    }
    write_json(output / "smoke.json", result)
    return result


def carrier_discrimination_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {"output": str(output), "sealed": (output / "SHA256SUMS").is_file()}
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "intervention-geometry",
        "compact-204-decision",
        "neutral-37-decision",
        "switch-10-decision",
        "decision",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    result["record_counts"] = {name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES}
    result["shard_counts"] = {
        stage: len(list((output / ".shards" / stage).glob("*.json"))) if (output / ".shards" / stage).is_dir() else 0
        for stage in (
            "static",
            "fresh-exposure",
            "no-op",
            "compact-dose-response",
            "matched-controls",
            "erase-rescue",
            "neutral-geometry",
            "bridge-transect",
            "switch-dose-response",
        )
    }
    return result
