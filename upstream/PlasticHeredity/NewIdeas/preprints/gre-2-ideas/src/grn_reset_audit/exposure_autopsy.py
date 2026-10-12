"""Mechanistic autopsy of durable UCS-exposure states in continuous GRNs.

This campaign begins from the sealed contingency parent.  It deliberately
keeps persistence, route sensitivity, component localization, and
counterfactual divergence separate, and it contains no renewal claim.
"""

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
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .atlas import state_from_payload, state_payload
from .contingency import (
    EXPOSURE_TASKS,
    _all_shard_cpu,
    _calibration_map,
    _fingerprint,
    _naive_start,
    _parallel,
    _perturb_start,
    _runtime_manifest,
    _seed,
    _verify_parent,
    axis_score,
    bipolar_score,
    cosine_alignment,
    quantile,
    vector_rms,
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


ROUTES = (
    "naive",
    "low_spaced",
    "quarter_spaced",
    "mid_spaced",
    "three_quarter_spaced",
    "high_spaced",
    "high_early",
    "high_late",
    "mid_continuous",
    "ramp_up",
    "ramp_down",
)
STATE_CONDITIONS = (
    "high_intact",
    "low_intact",
    "midpoint",
    "erase_top1",
    "erase_topk",
    "write_top1",
    "write_topk",
    "rescue_topk",
    "shuffled_delta",
    "norm_matched_random",
)
RECORD_FILES = (
    "long-horizon.jsonl",
    "route-factorial.jsonl",
    "state-localization.jsonl",
)


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(dict(row)) + "\n" for row in records))


def load_exposure_autopsy_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported exposure-autopsy schema")
    if config.get("experiment_kind") != "exposure-state-autopsy":
        raise ValueError("not an exposure-state-autopsy protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("exposure autopsy does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("exposure autopsy does not pin the release generator")
    if tuple(config.get("exposure_task_ids", ())) != EXPOSURE_TASKS:
        raise ValueError("exposure-autopsy cohort changed")
    if tuple(config.get("route_order", ())) != ROUTES:
        raise ValueError("exposure-autopsy route order changed")
    if tuple(config.get("state_localization", {}).get("conditions", ())) != STATE_CONDITIONS:
        raise ValueError("state-localization controls changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("exposure autopsy must cap workers at four")
    if not (
        0 < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 14400.0
    ):
        raise ValueError("exposure-autopsy wall contract exceeds four hours")
    if not (
        0 < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 57600.0
    ):
        raise ValueError("exposure-autopsy aggregate CPU contract is invalid")
    expected = {
        "delta_t": 0.01,
        "phase_duration": 2500.0,
        "epoch_duration": 250.0,
        "epoch_count": 10,
        "pulse_count": 5,
        "parent_washout_total": 12500.0,
        "washout_chunk_duration": 2500.0,
    }
    for key, value in expected.items():
        if not math.isclose(float(config.get(key, -1)), value):
            raise ValueError(f"exposure-autopsy historical setting differs for {key}")
    parent_seeds = tuple(int(seed) for seed in config["parent_seed_indices"])
    discovery = tuple(int(seed) for seed in config["discovery_seed_indices"])
    validation = tuple(int(seed) for seed in config["validation_seed_indices"])
    if parent_seeds != tuple(range(200, 208)):
        raise ValueError("parent seed cohort changed")
    if set(discovery) & set(validation) or set(discovery) | set(validation) != set(parent_seeds):
        raise ValueError("component discovery and validation seeds are not a partition")
    for name in ROUTES:
        spec = config["route_specs"].get(name)
        if not isinstance(spec, list) or len(spec) != int(config["epoch_count"]):
            raise ValueError(f"invalid route specification: {name}")
        for value in spec:
            if value is not None and value != "low" and not (
                isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0
            ):
                raise ValueError(f"invalid route amplitude in {name}: {value}")
    equal = config["route_analysis"]["equal_dose_routes"]
    doses = [normalized_route_dose(config["route_specs"][name]) for name in equal]
    if max(doses) - min(doses) > 1e-12:
        raise ValueError("registered equal-dose routes do not have equal normalized dose")
    horizons = [float(value) for value in config["state_localization"]["release_horizons"]]
    if horizons != [0.0, 250.0, 2500.0, 12500.0]:
        raise ValueError("state-localization release ladder changed")
    return config


def normalized_route_dose(spec: Sequence[Any]) -> float:
    return float(sum(float(value) for value in spec if isinstance(value, (int, float))))


def route_epochs(memory: Any, spec: Sequence[Any]) -> list[dict[int, float] | None]:
    low = float(memory.bounds[memory.ucs_id, 0])
    high = float(memory.bounds[memory.ucs_id, 1])
    epochs: list[dict[int, float] | None] = []
    for value in spec:
        if value is None:
            epochs.append(None)
        elif value == "low":
            epochs.append({int(memory.ucs_id): low})
        else:
            alpha = float(value)
            epochs.append({int(memory.ucs_id): low + alpha * (high - low)})
    return epochs


def _parent_records(parent: Path) -> dict[tuple[str, int, str], dict[str, Any]]:
    result: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in read_jsonl(parent / "exposure-validation.jsonl"):
        key = (str(row["memory_task_id"]), int(row["seed_index"]), str(row["condition"]))
        if key in result:
            raise ValueError(f"duplicate parent exposure record: {key}")
        result[key] = row
    return result


def _parent_pair(
    parent_map: Mapping[tuple[str, int, str], Mapping[str, Any]],
    task_id: str,
    seed_index: int,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    low = parent_map[(str(task_id), int(seed_index), "low_ucs")]
    high = parent_map[(str(task_id), int(seed_index), "high_ucs")]
    return low, high


def _state(row: Mapping[str, Any], checkpoint: str = "12500") -> State:
    result = state_from_payload(row["checkpoints"][checkpoint]["state"])
    if result is None:
        raise ValueError("parent contains an invalid state payload")
    return result


def _state_scale(memory: Any) -> np.ndarray:
    return np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8)


def _standardized_delta(left: State, right: State, scale: np.ndarray) -> np.ndarray:
    return (np.asarray(left.y, dtype=float) - np.asarray(right.y, dtype=float)) / scale


def _state_distance(left: State, right: State, scale: np.ndarray) -> float:
    return float(np.linalg.norm(_standardized_delta(left, right, scale)))


def _fingerprint_from_parent(row: Mapping[str, Any]) -> np.ndarray:
    return np.asarray(row["checkpoints"]["12500"]["fingerprint"], dtype=float)


def validate_exposure_autopsy_parents(
    config: Mapping[str, Any], parent: Path, atlas: Path, upstream: Path
) -> dict[str, Any]:
    provenance = validate_upstream(upstream, str(config["upstream_commit"]))
    parent_gate = _verify_parent(parent, str(config["parent_experiment_id"]), config["parent_hashes"])
    atlas_gate = _verify_parent(
        atlas, str(config["atlas_parent_experiment_id"]), config["atlas_parent_hashes"]
    )
    decision = json.loads((parent / "exposure-decision.json").read_text(encoding="utf-8"))
    if not decision.get("pass") or int(decision.get("pass_count", 0)) != len(EXPOSURE_TASKS):
        raise ValueError("parent does not contain the sealed five-of-five exposure result")
    records = _parent_records(parent)
    expected = len(EXPOSURE_TASKS) * len(config["parent_seed_indices"]) * 2
    if len(records) != expected or not all(bool(row.get("valid")) for row in records.values()):
        raise ValueError("parent exposure cohort is incomplete or invalid")
    return {"upstream": provenance, "parent": parent_gate, "atlas": atlas_gate}


def _shard(output: Path, stage: str, key: str, protocol_digest: str) -> tuple[Path, dict[str, Any] | None]:
    path = output / ".shards" / stage / f"{key}.json"
    if path.is_file():
        prior = json.loads(path.read_text(encoding="utf-8"))
        if prior.get("protocol_digest") == protocol_digest:
            return path, prior
    return path, None


def _merge_shards(
    output: Path, name: str, shards: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    records = [dict(row) for shard in shards for row in shard.get("records", ())]
    task_ids = [str(row["task_id"]) for row in records]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError(f"duplicate task IDs while merging {name}")
    _write_jsonl(output / f"{name}.jsonl", records)
    return records


def _long_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, parent_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_exposure_autopsy_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "long-horizon", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    parent_map = _parent_records(Path(parent_path))
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    released = load_released_task(Path(upstream_path), str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    reconstructed = int(_calibration_map(Path(atlas_path))[str(task_id)]["reconstructed_ucs_bound_index"])
    scale = _state_scale(memory)
    endpoint = float(config["long_horizon"]["checkpoint_total"])
    ultra = str(task_id) in set(config["long_horizon"]["ultra_task_ids"])
    totals = [float(config["parent_washout_total"]), endpoint]
    if ultra:
        totals.append(float(config["long_horizon"]["ultra_total"]))
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm, parent_row in (("low", low_row), ("high", high_row)):
        current = _state(parent_row)
        checkpoints: dict[str, Any] = {
            f"{totals[0]:g}": {
                "state": state_payload(current),
                "fingerprint": parent_row["checkpoints"]["12500"]["fingerprint"],
                "valid": bool(parent_row["checkpoints"]["12500"]["valid"]),
                "source": "sealed-parent",
            }
        }
        prior_total = totals[0]
        valid = bool(parent_row.get("valid"))
        for total in totals[1:]:
            washout = backend.run_unstimulated(
                current,
                total - prior_total,
                memory.key.response_id,
                int(config["trajectory_samples"]),
                float(config["washout_chunk_duration"]),
            )
            current = washout.state
            fp = _fingerprint(backend, memory, current, config, reconstructed)
            valid = valid and bool(washout.valid and fp["valid"])
            cpu += float(washout.cpu_seconds + fp["cpu_seconds"])
            wall += float(washout.wall_seconds + fp["wall_seconds"])
            checkpoints[f"{total:g}"] = {
                "state": state_payload(current),
                "fingerprint": fp["fingerprint"],
                "raw_fingerprint": fp["raw_fingerprint"],
                "valid": bool(washout.valid and fp["valid"]),
                "source": "continued",
            }
            prior_total = total
        stability = backend.run_unstimulated(
            current.copy(),
            float(config["long_horizon"]["stability_probe_duration"]),
            memory.key.response_id,
            int(config["trajectory_samples"]),
            float(config["washout_chunk_duration"]),
        )
        cpu += float(stability.cpu_seconds)
        wall += float(stability.wall_seconds)
        valid = valid and bool(stability.valid)
        records.append(
            {
                "task_id": f"long|{task_id}|{seed_index}|{arm}",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "arm": arm,
                "checkpoints": checkpoints,
                "final_total": totals[-1],
                "stability_probe_state": state_payload(stability.state),
                "state_scale": scale,
                "parent_record_digest": digest(parent_row),
                "valid": bool(valid),
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "long-horizon",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _route_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, parent_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_exposure_autopsy_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "route-factorial", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    parent = Path(parent_path)
    parent_map = _parent_records(parent)
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    parent_protocol = json.loads((parent / "registration.json").read_text(encoding="utf-8"))["protocol"]
    released = load_released_task(Path(upstream_path), str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    base = _naive_start(Path(atlas_path), str(task_id))
    start, philox_seed = _perturb_start(
        base, memory, parent_protocol, "exposure", str(task_id), int(seed_index)
    )
    expected_start = str(low_row["same_naive_start_hash"])
    if digest(state_payload(start)) != expected_start or expected_start != str(high_row["same_naive_start_hash"]):
        raise ValueError(f"failed to reconstruct sealed parent start for {task_id}/{seed_index}")
    reconstructed = int(_calibration_map(Path(atlas_path))[str(task_id)]["reconstructed_ucs_bound_index"])
    reference_low = _fingerprint_from_parent(low_row)
    reference_high = _fingerprint_from_parent(high_row)
    parent_low_state = _state(low_row)
    parent_high_state = _state(high_row)
    scale = _state_scale(memory)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for route_name in config["route_order"]:
        spec = config["route_specs"][route_name]
        training = run_epoch_schedule(
            backend,
            start.copy(),
            route_epochs(memory, spec),
            float(config["epoch_duration"]),
            memory.key.response_id,
            int(config["trajectory_samples"]),
        )
        washout = backend.run_unstimulated(
            training.state,
            float(config["route_analysis"]["washout_total"]),
            memory.key.response_id,
            int(config["trajectory_samples"]),
            float(config["washout_chunk_duration"]),
        )
        fp = _fingerprint(backend, memory, washout.state, config, reconstructed)
        score = bipolar_score(fp["fingerprint"], reference_high, reference_low)
        state_score = axis_score(
            _standardized_delta(washout.state, parent_low_state, scale),
            np.zeros_like(scale),
            _standardized_delta(parent_high_state, parent_low_state, scale),
        )
        valid = bool(training.valid and washout.valid and fp["valid"] and score is not None)
        cpu += float(training.cpu_seconds + washout.cpu_seconds + fp["cpu_seconds"])
        wall += float(training.wall_seconds + washout.wall_seconds + fp["wall_seconds"])
        source_row = low_row if route_name == "low_spaced" else high_row if route_name == "high_spaced" else None
        source_fp_distance = None
        source_state_distance = None
        if source_row is not None:
            source_fp_distance = vector_rms(
                np.asarray(fp["fingerprint"], dtype=float) - _fingerprint_from_parent(source_row)
            )
            source_state_distance = _state_distance(washout.state, _state(source_row), scale)
        records.append(
            {
                "task_id": f"route|{task_id}|{seed_index}|{route_name}",
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "seed_index": int(seed_index),
                "philox_seed": int(philox_seed),
                "route": str(route_name),
                "route_spec": spec,
                "normalized_dose": normalized_route_dose(spec),
                "physical_clamp_epochs": sum(value is not None for value in spec),
                "training_state": state_payload(training.state),
                "terminal_state": state_payload(washout.state),
                "fingerprint": fp["fingerprint"],
                "raw_fingerprint": fp["raw_fingerprint"],
                "probes": fp["probes"],
                "bipolar_score": score,
                "state_axis_score": state_score,
                "source_fingerprint_distance": source_fp_distance,
                "source_state_distance": source_state_distance,
                "same_parent_start": True,
                "valid": valid,
            }
        )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "route-factorial",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def component_rankings(
    config: Mapping[str, Any], parent: Path, upstream: Path
) -> dict[str, Any]:
    parent_map = _parent_records(parent)
    results: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        released = load_released_task(upstream, str(task_id))
        memory = load_memory(released.memory_path, released.key)
        scale = _state_scale(memory)
        differences: list[np.ndarray] = []
        for seed in config["discovery_seed_indices"]:
            low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed))
            differences.append(np.abs(_standardized_delta(_state(high_row), _state(low_row), scale)))
        scores = np.mean(np.asarray(differences, dtype=float), axis=0)
        ranking = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), int(index)))
        top_k = min(int(config["state_localization"]["top_k"]), len(ranking))
        results.append(
            {
                "memory_task_id": str(task_id),
                "model_id": int(memory.key.model_id),
                "discovery_seed_indices": list(config["discovery_seed_indices"]),
                "standardized_abs_difference": scores,
                "ranking": ranking,
                "top_one": ranking[:1],
                "top_k": ranking[:top_k],
                "node_count": len(scores),
            }
        )
    return {
        "task_id": "component-ranking",
        "leakage_allowed": False,
        "validation_seed_indices": list(config["validation_seed_indices"]),
        "rankings": results,
    }


def _mid_state(high: State, low: State) -> State:
    if not np.array_equal(high.c, low.c):
        raise ValueError("high and low states do not share a rulebook")
    return State(
        0.5 * (high.y + low.y),
        0.5 * (high.w + low.w),
        high.c.copy(),
        max(float(high.t), float(low.t)),
    )


def localization_states(
    high: State,
    low: State,
    memory: Any,
    top_one: Sequence[int],
    top_k: Sequence[int],
    seed: int,
) -> dict[str, State]:
    midpoint = _mid_state(high, low)

    def replace(base: State, donor: State, indices: Sequence[int]) -> State:
        result = base.copy()
        if indices:
            result.y[np.asarray(indices, dtype=int)] = donor.y[np.asarray(indices, dtype=int)]
        return result

    erased = replace(high, low, top_k)
    rescued = replace(erased, high, top_k)
    scale = _state_scale(memory)
    delta = (high.y - midpoint.y) / scale
    rng = np.random.Generator(np.random.Philox(int(seed)))
    shuffled = midpoint.copy()
    shuffled.y = np.clip(
        midpoint.y + rng.permutation(delta) * scale,
        memory.bounds[:, 0],
        memory.bounds[:, 1],
    )
    random_direction = rng.normal(size=len(delta))
    random_norm = float(np.linalg.norm(random_direction))
    target_norm = float(np.linalg.norm(delta))
    random_delta = (
        np.zeros_like(delta)
        if random_norm <= 1e-12
        else random_direction * (target_norm / random_norm)
    )
    random_state = midpoint.copy()
    random_state.y = np.clip(
        midpoint.y + random_delta * scale,
        memory.bounds[:, 0],
        memory.bounds[:, 1],
    )
    return {
        "high_intact": high.copy(),
        "low_intact": low.copy(),
        "midpoint": midpoint,
        "erase_top1": replace(high, low, top_one),
        "erase_topk": erased,
        "write_top1": replace(low, high, top_one),
        "write_topk": replace(low, high, top_k),
        "rescue_topk": rescued,
        "shuffled_delta": shuffled,
        "norm_matched_random": random_state,
    }


def _localization_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, parent_path, atlas_path, upstream_path, output_path, task_id, seed_index = args
    config = load_exposure_autopsy_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "state-localization", f"{task_id}-{seed_index}", protocol_digest)
    if prior is not None:
        return prior
    parent_map = _parent_records(Path(parent_path))
    low_row, high_row = _parent_pair(parent_map, str(task_id), int(seed_index))
    released = load_released_task(Path(upstream_path), str(task_id))
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(Path(upstream_path), memory.key.model_id, float(config["delta_t"]))
    reconstructed = int(_calibration_map(Path(atlas_path))[str(task_id)]["reconstructed_ucs_bound_index"])
    reference_low = _fingerprint_from_parent(low_row)
    reference_high = _fingerprint_from_parent(high_row)
    rankings = json.loads((output / "component-rankings.json").read_text(encoding="utf-8"))
    ranking = next(row for row in rankings["rankings"] if row["memory_task_id"] == str(task_id))
    states = localization_states(
        _state(high_row),
        _state(low_row),
        memory,
        ranking["top_one"],
        ranking["top_k"],
        _seed(config, "localization-control", task_id, seed_index),
    )
    scale = _state_scale(memory)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for condition in config["state_localization"]["conditions"]:
        source = states[str(condition)]
        for horizon in config["state_localization"]["release_horizons"]:
            release = backend.run_unstimulated(
                source.copy(),
                float(horizon),
                memory.key.response_id,
                int(config["trajectory_samples"]),
                float(config["washout_chunk_duration"]),
            )
            fp = _fingerprint(backend, memory, release.state, config, reconstructed)
            score = bipolar_score(fp["fingerprint"], reference_high, reference_low)
            state_score = axis_score(
                _standardized_delta(release.state, _state(low_row), scale),
                np.zeros_like(scale),
                _standardized_delta(_state(high_row), _state(low_row), scale),
            )
            valid = bool(release.valid and fp["valid"] and score is not None)
            cpu += float(release.cpu_seconds + fp["cpu_seconds"])
            wall += float(release.wall_seconds + fp["wall_seconds"])
            source_distance = None
            source_fp_distance = None
            if float(horizon) == 0.0 and condition in {"high_intact", "low_intact"}:
                parent_row = high_row if condition == "high_intact" else low_row
                source_distance = _state_distance(release.state, _state(parent_row), scale)
                source_fp_distance = vector_rms(
                    np.asarray(fp["fingerprint"], dtype=float) - _fingerprint_from_parent(parent_row)
                )
            records.append(
                {
                    "task_id": f"localize|{task_id}|{seed_index}|{condition}|{float(horizon):g}",
                    "memory_task_id": str(task_id),
                    "model_id": int(memory.key.model_id),
                    "seed_index": int(seed_index),
                    "condition": str(condition),
                    "release_horizon": float(horizon),
                    "top_one": ranking["top_one"],
                    "top_k": ranking["top_k"],
                    "source_state": state_payload(source),
                    "released_state": state_payload(release.state),
                    "fingerprint": fp["fingerprint"],
                    "raw_fingerprint": fp["raw_fingerprint"],
                    "probes": fp["probes"],
                    "bipolar_score": score,
                    "state_axis_score": state_score,
                    "source_state_distance": source_distance,
                    "source_fingerprint_distance": source_fp_distance,
                    "valid": valid,
                }
            )
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "state-localization",
        "memory_task_id": str(task_id),
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _median(values: Iterable[float]) -> float | None:
    return quantile([float(value) for value in values], 0.5)


def _rank_correlation(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None

    def ranks(values: Sequence[float]) -> np.ndarray:
        array = np.asarray(values, dtype=float)
        order = np.argsort(array, kind="mergesort")
        result = np.empty(len(array), dtype=float)
        result[order] = np.arange(len(array), dtype=float)
        for value in np.unique(array):
            indices = np.flatnonzero(array == value)
            result[indices] = float(np.mean(result[indices]))
        return result

    left = ranks(x)
    right = ranks(y)
    if float(np.std(left) * np.std(right)) <= 1e-12:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def long_horizon_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["long_horizon"]
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        task_rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        endpoint = (
            float(settings["ultra_total"])
            if task_id in set(settings["ultra_task_ids"])
            else float(settings["checkpoint_total"])
        )
        per_seed: list[dict[str, Any]] = []
        for seed in config["parent_seed_indices"]:
            arms = {row["arm"]: row for row in task_rows if int(row["seed_index"]) == int(seed)}
            if set(arms) != {"low", "high"}:
                continue
            high = arms["high"]
            low = arms["low"]
            scale = np.asarray(high["state_scale"], dtype=float)
            base_high = state_from_payload(high["checkpoints"]["12500"]["state"])
            base_low = state_from_payload(low["checkpoints"]["12500"]["state"])
            final_high = state_from_payload(high["checkpoints"][f"{endpoint:g}"]["state"])
            final_low = state_from_payload(low["checkpoints"][f"{endpoint:g}"]["state"])
            drift_high = state_from_payload(high["stability_probe_state"])
            drift_low = state_from_payload(low["stability_probe_state"])
            if any(
                value is None
                for value in (
                    base_high,
                    base_low,
                    final_high,
                    final_low,
                    drift_high,
                    drift_low,
                )
            ):
                continue
            assert base_high is not None and base_low is not None
            assert final_high is not None and final_low is not None
            assert drift_high is not None and drift_low is not None
            base_state_delta = _standardized_delta(base_high, base_low, scale)
            final_state_delta = _standardized_delta(final_high, final_low, scale)
            base_state_sep = float(np.linalg.norm(base_state_delta))
            final_state_sep = float(np.linalg.norm(final_state_delta))
            base_fp_delta = np.asarray(high["checkpoints"]["12500"]["fingerprint"], dtype=float) - np.asarray(
                low["checkpoints"]["12500"]["fingerprint"], dtype=float
            )
            final_fp_delta = np.asarray(high["checkpoints"][f"{endpoint:g}"]["fingerprint"], dtype=float) - np.asarray(
                low["checkpoints"][f"{endpoint:g}"]["fingerprint"], dtype=float
            )
            base_fp_sep = vector_rms(base_fp_delta)
            final_fp_sep = vector_rms(final_fp_delta)
            drift = max(
                _state_distance(drift_high, final_high, scale),
                _state_distance(drift_low, final_low, scale),
            )
            state_retention = final_state_sep / max(base_state_sep, 1e-12)
            functional_retention = final_fp_sep / max(base_fp_sep, 1e-12)
            direction = cosine_alignment(base_fp_delta, final_fp_delta)
            drift_ratio = drift / max(final_state_sep, 1e-12)
            consistent = bool(
                state_retention >= float(settings["state_retention_min"])
                and functional_retention >= float(settings["functional_retention_min"])
                and direction is not None
                and direction >= float(settings["direction_cosine_min"])
                and drift_ratio <= float(settings["drift_ratio_max"])
            )
            per_seed.append(
                {
                    "seed_index": int(seed),
                    "state_retention": state_retention,
                    "functional_retention": functional_retention,
                    "direction_cosine": direction,
                    "drift_ratio": drift_ratio,
                    "consistent": consistent,
                }
            )
        med_state = _median(row["state_retention"] for row in per_seed)
        med_function = _median(row["functional_retention"] for row in per_seed)
        med_direction = _median(
            row["direction_cosine"] for row in per_seed if row["direction_cosine"] is not None
        )
        med_drift = _median(row["drift_ratio"] for row in per_seed)
        consistent_count = sum(bool(row["consistent"]) for row in per_seed)
        stable = bool(
            med_state is not None
            and med_function is not None
            and med_direction is not None
            and med_drift is not None
            and med_state >= float(settings["state_retention_min"])
            and med_function >= float(settings["functional_retention_min"])
            and med_direction >= float(settings["direction_cosine_min"])
            and med_drift <= float(settings["drift_ratio_max"])
            and consistent_count >= int(settings["minimum_consistent_seeds"])
        )
        if stable:
            classification = "stable-separate-compatible"
        elif med_state is not None and med_state >= float(settings["state_retention_min"]) and med_function is not None and med_function < 0.25:
            classification = "inert-state-scar"
        elif med_function is not None and med_function >= float(settings["functional_retention_min"]):
            classification = "persistent-but-drifting"
        else:
            classification = "converging-transient"
        summaries.append(
            {
                "memory_task_id": task_id,
                "endpoint_total": endpoint,
                "valid_seed_count": len(per_seed),
                "consistent_seed_count": consistent_count,
                "median_state_retention": med_state,
                "median_functional_retention": med_function,
                "median_direction_cosine": med_direction,
                "median_drift_ratio": med_drift,
                "classification": classification,
                "pass": stable,
                "per_seed": per_seed,
            }
        )
    return {
        "task_id": "long-horizon-decision",
        "candidate_summaries": summaries,
        "pass_count": sum(bool(row["pass"]) for row in summaries),
        "pass": any(bool(row["pass"]) for row in summaries),
        "verdict": "stable-separate-compatible-leads" if any(bool(row["pass"]) for row in summaries) else "no-stable-separate-lead",
    }


def route_factorial_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["route_analysis"]
    summaries: list[dict[str, Any]] = []
    all_pairs: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        grouped = {name: [row for row in rows if row["route"] == name] for name in ROUTES}
        medians = {
            name: _median(row["bipolar_score"] for row in values if row.get("bipolar_score") is not None)
            for name, values in grouped.items()
        }
        source_consistent = 0
        for seed in config["parent_seed_indices"]:
            by_route = {
                row["route"]: row
                for row in rows
                if int(row["seed_index"]) == int(seed) and row["route"] in {"low_spaced", "high_spaced"}
            }
            if set(by_route) == {"low_spaced", "high_spaced"} and (
                abs(float(by_route["low_spaced"]["bipolar_score"]) + 1.0)
                <= float(settings["source_score_tolerance"])
                and abs(float(by_route["high_spaced"]["bipolar_score"]) - 1.0)
                <= float(settings["source_score_tolerance"])
            ):
                source_consistent += 1
        source_pass = source_consistent >= int(settings["minimum_source_reproduction_seeds"])
        ladder = list(settings["dose_ladder"])
        doses = [normalized_route_dose(config["route_specs"][name]) for name in ladder]
        ladder_scores = [medians[name] for name in ladder]
        rho = None if any(value is None for value in ladder_scores) else _rank_correlation(doses, [float(value) for value in ladder_scores])
        adjacent = [] if any(value is None for value in ladder_scores) else [
            float(ladder_scores[index + 1]) - float(ladder_scores[index])
            for index in range(len(ladder_scores) - 1)
        ]
        equal_values = [medians[name] for name in settings["equal_dose_routes"] if medians[name] is not None]
        equal_spread = None if not equal_values else float(max(equal_values) - min(equal_values))
        peak_effect = None if medians["high_spaced"] is None or medians["mid_continuous"] is None else float(medians["high_spaced"] - medians["mid_continuous"])
        recency_effect = None if medians["high_late"] is None or medians["high_early"] is None else float(medians["high_late"] - medians["high_early"])
        ramp_order_effect = None if medians["ramp_up"] is None or medians["ramp_down"] is None else float(medians["ramp_up"] - medians["ramp_down"])
        threshold = float(settings["route_effect_min"])
        flags = {
            "graded_integrator_compatible": bool(rho is not None and rho >= float(settings["dose_rank_correlation_min"]) and equal_spread is not None and equal_spread <= threshold),
            "switch_like": bool(adjacent and max(abs(value) for value in adjacent) >= float(settings["switch_jump_min"])),
            "peak_sensitive": bool(peak_effect is not None and abs(peak_effect) >= threshold),
            "recency_sensitive": bool(recency_effect is not None and abs(recency_effect) >= threshold),
            "path_sensitive": bool(ramp_order_effect is not None and abs(ramp_order_effect) >= threshold),
        }
        task_pairs: list[dict[str, Any]] = []
        for left_name, right_name in itertools.combinations(ROUTES, 2):
            differences: list[tuple[float, float]] = []
            for seed in config["parent_seed_indices"]:
                seed_rows = {
                    row["route"]: row
                    for row in rows
                    if int(row["seed_index"]) == int(seed) and row["route"] in {left_name, right_name}
                }
                if set(seed_rows) != {left_name, right_name}:
                    continue
                left = np.asarray(seed_rows[left_name]["fingerprint"], dtype=float)
                right = np.asarray(seed_rows[right_name]["fingerprint"], dtype=float)
                differences.append((abs(float(left[0] - right[0])), vector_rms(left[1:] - right[1:])))
            resting = _median(value[0] for value in differences)
            counterfactual = _median(value[1] for value in differences)
            qualifies = bool(
                resting is not None
                and counterfactual is not None
                and resting <= float(settings["coarse_match_max"])
                and counterfactual >= float(settings["counterfactual_divergence_min"])
                and len(differences) >= int(settings["minimum_source_reproduction_seeds"])
            )
            if qualifies:
                task_pairs.append(
                    {
                        "memory_task_id": task_id,
                        "left_route": left_name,
                        "right_route": right_name,
                        "median_no_input_difference": resting,
                        "median_counterfactual_rms": counterfactual,
                        "valid_seed_count": len(differences),
                        "classification": "coarse-matched-counterfactual-divergence",
                    }
                )
        task_pairs.sort(key=lambda row: (-float(row["median_counterfactual_rms"]), row["left_route"], row["right_route"]))
        all_pairs.extend(task_pairs)
        summaries.append(
            {
                "memory_task_id": task_id,
                "source_consistent_seed_count": source_consistent,
                "source_pass": source_pass,
                "condition_medians": medians,
                "dose_rank_correlation": rho,
                "dose_adjacent_changes": adjacent,
                "largest_adjacent_change": max((abs(value) for value in adjacent), default=None),
                "equal_dose_spread": equal_spread,
                "peak_effect": peak_effect,
                "recency_effect": recency_effect,
                "ramp_order_effect": ramp_order_effect,
                "flags": flags,
                "coarse_matched_pair_count": len(task_pairs),
            }
        )
    source_pass = all(bool(row["source_pass"]) for row in summaries)
    return {
        "task_id": "route-factorial-decision",
        "candidate_summaries": summaries,
        "source_reproduction_pass": source_pass,
        "source_reproduction_pass_count": sum(bool(row["source_pass"]) for row in summaries),
        "coarse_matched_counterfactual_pairs": all_pairs,
        "counterfactual_pair_count": len(all_pairs),
        "path_sensitive_task_count": sum(bool(row["flags"]["path_sensitive"] or row["flags"]["recency_sensitive"]) for row in summaries),
        "integrator_compatible_task_count": sum(bool(row["flags"]["graded_integrator_compatible"]) for row in summaries),
        "pass": source_pass,
        "verdict": "source-valid-route-atlas" if source_pass else "source-reproduction-failed",
    }


def state_localization_decision(
    records: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    settings = config["state_localization"]
    summaries: list[dict[str, Any]] = []
    for task_id in config["exposure_task_ids"]:
        task_rows = [row for row in records if row["memory_task_id"] == task_id and row.get("valid")]
        horizons: dict[str, Any] = {}
        task_pass = False
        for horizon in settings["release_horizons"]:
            rows = [row for row in task_rows if math.isclose(float(row["release_horizon"]), float(horizon))]
            medians = {
                condition: _median(
                    row["bipolar_score"]
                    for row in rows
                    if row["condition"] == condition and row.get("bipolar_score") is not None
                )
                for condition in STATE_CONDITIONS
            }
            high = medians["high_intact"]
            low = medians["low_intact"]
            denominator = None if high is None or low is None else float(high - low)
            erase = None if denominator is None or abs(denominator) <= 1e-12 or medians["erase_topk"] is None else float((high - medians["erase_topk"]) / denominator)
            write = None if denominator is None or abs(denominator) <= 1e-12 or medians["write_topk"] is None else float((medians["write_topk"] - low) / denominator)
            rescue_denominator = None if high is None or medians["erase_topk"] is None else float(high - medians["erase_topk"])
            rescue = None if rescue_denominator is None or abs(rescue_denominator) <= 1e-12 or medians["rescue_topk"] is None else float((medians["rescue_topk"] - medians["erase_topk"]) / rescue_denominator)
            controls = [medians[name] for name in ("midpoint", "shuffled_delta", "norm_matched_random") if medians[name] is not None]
            control_max = max((abs(float(value)) for value in controls), default=math.inf)
            consistent = 0
            for seed in config["validation_seed_indices"]:
                seed_rows = {
                    row["condition"]: row
                    for row in rows
                    if int(row["seed_index"]) == int(seed)
                }
                if not all(name in seed_rows for name in STATE_CONDITIONS):
                    continue
                sh = float(seed_rows["high_intact"]["bipolar_score"])
                sl = float(seed_rows["low_intact"]["bipolar_score"])
                denom = sh - sl
                if abs(denom) <= 1e-12:
                    continue
                se = (sh - float(seed_rows["erase_topk"]["bipolar_score"])) / denom
                sw = (float(seed_rows["write_topk"]["bipolar_score"]) - sl) / denom
                er = sh - float(seed_rows["erase_topk"]["bipolar_score"])
                sr = 0.0 if abs(er) <= 1e-12 else (
                    float(seed_rows["rescue_topk"]["bipolar_score"])
                    - float(seed_rows["erase_topk"]["bipolar_score"])
                ) / er
                sc = max(
                    abs(float(seed_rows[name]["bipolar_score"]))
                    for name in ("midpoint", "shuffled_delta", "norm_matched_random")
                )
                if (
                    denom >= float(settings["intact_separation_min"])
                    and se >= float(settings["erase_fraction_min"])
                    and sw >= float(settings["write_fraction_min"])
                    and sr >= float(settings["rescue_fraction_min"])
                    and sc <= float(settings["control_max_abs"])
                ):
                    consistent += 1
            passed = bool(
                denominator is not None
                and denominator >= float(settings["intact_separation_min"])
                and erase is not None
                and erase >= float(settings["erase_fraction_min"])
                and write is not None
                and write >= float(settings["write_fraction_min"])
                and rescue is not None
                and rescue >= float(settings["rescue_fraction_min"])
                and control_max <= float(settings["control_max_abs"])
                and consistent >= int(settings["minimum_consistent_seeds"])
            )
            task_pass = task_pass or passed
            horizons[f"{float(horizon):g}"] = {
                "condition_medians": medians,
                "intact_separation": denominator,
                "erase_fraction": erase,
                "write_fraction": write,
                "rescue_fraction": rescue,
                "control_max_abs": control_max,
                "consistent_seed_count": consistent,
                "pass": passed,
            }
        source_rows = [row for row in task_rows if float(row["release_horizon"]) == 0.0 and row["condition"] in {"high_intact", "low_intact"}]
        source_pass = len(source_rows) == 2 * len(config["validation_seed_indices"]) and all(
            float(row.get("source_state_distance") or 0.0) <= 1e-10
            and float(row.get("source_fingerprint_distance") or 0.0) <= 1e-8
            for row in source_rows
        )
        summaries.append(
            {
                "memory_task_id": task_id,
                "source_pass": source_pass,
                "horizons": horizons,
                "pass": bool(source_pass and task_pass),
            }
        )
    return {
        "task_id": "state-localization-decision",
        "candidate_summaries": summaries,
        "pass_count": sum(bool(row["pass"]) for row in summaries),
        "pass": any(bool(row["pass"]) for row in summaries),
        "source_reproduction_pass": all(bool(row["source_pass"]) for row in summaries),
        "verdict": "localized-state-component-leads" if any(bool(row["pass"]) for row in summaries) else "no-localized-state-component-lead",
    }


def analyze_exposure_autopsy(output: Path, final_status: str | None = None) -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    long_records = list(read_jsonl(output / "long-horizon.jsonl"))
    route_records = list(read_jsonl(output / "route-factorial.jsonl"))
    localization_records = list(read_jsonl(output / "state-localization.jsonl"))
    long_decision = long_horizon_decision(long_records, config)
    route_decision = route_factorial_decision(route_records, config)
    localization_decision = state_localization_decision(localization_records, config)
    write_json(output / "long-horizon-decision.json", long_decision)
    write_json(output / "route-factorial-decision.json", route_decision)
    write_json(output / "state-localization-decision.json", localization_decision)
    source_valid = bool(
        route_decision["source_reproduction_pass"]
        and localization_decision["source_reproduction_pass"]
    )
    if not source_valid:
        verdict = "source-reproduction-failed"
    elif localization_decision["pass"]:
        verdict = "localized-causal-state-component-lead"
    elif route_decision["path_sensitive_task_count"] and route_decision["counterfactual_pair_count"]:
        verdict = "path-sensitive-counterfactual-state-lead"
    elif long_decision["pass"]:
        verdict = "stable-functional-exposure-valley-lead"
    elif route_decision["integrator_compatible_task_count"]:
        verdict = "graded-exposure-integrator-compatible"
    else:
        verdict = "slow-or-inert-exposure-trace"
    decision = {
        "task_id": "exposure-autopsy-decision",
        "pass": bool(source_valid and (localization_decision["pass"] or long_decision["pass"] or route_decision["counterfactual_pair_count"] > 0)),
        "verdict": verdict,
        "source_valid": source_valid,
        "stable_separate_task_count": int(long_decision["pass_count"]),
        "localized_task_count": int(localization_decision["pass_count"]),
        "path_sensitive_task_count": int(route_decision["path_sensitive_task_count"]),
        "integrator_compatible_task_count": int(route_decision["integrator_compatible_task_count"]),
        "counterfactual_pair_count": int(route_decision["counterfactual_pair_count"]),
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "decision.json", decision)
    ledger = json.loads((output / "resource-ledger.json").read_text(encoding="utf-8")) if (output / "resource-ledger.json").is_file() else {}
    analysis = {
        "task_id": "exposure-autopsy-analysis",
        "experiment_id": config["experiment_id"],
        "run_status": final_status or "analyzed",
        "decision_pass": bool(decision["pass"]),
        "verdict": verdict,
        "record_counts": {
            "long-horizon.jsonl": len(long_records),
            "route-factorial.jsonl": len(route_records),
            "state-localization.jsonl": len(localization_records),
        },
        "active_wall_seconds": float(ledger.get("active_wall_seconds", 0.0)),
        "aggregate_cpu_seconds": float(ledger.get("aggregate_cpu_seconds", 0.0)),
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    report = f"""# GRN exposure-state autopsy V1

Status: **{analysis['run_status']}**

Verdict: **{verdict}**

- Source-valid: **{source_valid}**.
- Stable-separate-compatible tasks: **{decision['stable_separate_task_count']} / {len(config['exposure_task_ids'])}**.
- Causally localized state-component tasks: **{decision['localized_task_count']} / {len(config['exposure_task_ids'])}**.
- Route/recency-sensitive tasks: **{decision['path_sensitive_task_count']} / {len(config['exposure_task_ids'])}**.
- Graded-integrator-compatible tasks: **{decision['integrator_compatible_task_count']} / {len(config['exposure_task_ids'])}**.
- Coarse-matched counterfactual route pairs: **{decision['counterfactual_pair_count']}**.

Records: {analysis['record_counts']}

Resource use: {analysis['active_wall_seconds']:.3f} active wall seconds and
{analysis['aggregate_cpu_seconds']:.3f} aggregate worker CPU seconds.

Claim boundary: {config['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class ExposureAutopsyCampaign:
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
        self.config = load_exposure_autopsy_config(self.config_path)
        self.parent = parent.resolve()
        self.atlas = atlas.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("exposure-autopsy workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed exposure-autopsy campaign cannot be resumed")
        self.parent_gate = validate_exposure_autopsy_parents(
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
                    raise ValueError(f"resumed exposure-autopsy registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"]["container_image_id"]:
                raise ValueError("resumed exposure-autopsy image differs")
        write_json(path, payload)
        write_json(self.output / "parent-gate.json", {"task_id": "parent-gate", "pass": True, **self.parent_gate})
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "persistence": "The exposure contrast remains functionally separate with low drift at extended washout.",
                "route": "Equal normalized dose can distinguish integration, peak, recency, and order effects.",
                "localization": "A discovery-frozen expression subset can erase, write, and rescue exposure content on untouched seeds.",
                "observer": "Routes can match a resting output while diverging under counterfactual probes.",
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
            self._state("running", "long-horizon")
            common_args = [
                (
                    str(self.config_path),
                    str(self.parent),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed),
                )
                for task_id in self.config["exposure_task_ids"]
                for seed in self.config["parent_seed_indices"]
            ]
            long_shards = _parallel(_long_worker, common_args, self.workers)
            _merge_shards(self.output, "long-horizon", long_shards)
            self._state("running", "route-factorial")
            route_shards = _parallel(_route_worker, common_args, self.workers)
            _merge_shards(self.output, "route-factorial", route_shards)
            self._state("running", "component-ranking")
            rankings = component_rankings(self.config, self.parent, self.upstream)
            write_json(self.output / "component-rankings.json", rankings)
            localization_args = [
                (
                    str(self.config_path),
                    str(self.parent),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    str(task_id),
                    int(seed),
                )
                for task_id in self.config["exposure_task_ids"]
                for seed in self.config["validation_seed_indices"]
            ]
            self._state("running", "state-localization")
            localization_shards = _parallel(_localization_worker, localization_args, self.workers)
            _merge_shards(self.output, "state-localization", localization_shards)
            self._state("analyzing", "analysis")
            self.ledger.close()
            analyze_exposure_autopsy(self.output, final_status="completed")
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


def run_exposure_autopsy(
    config: Path,
    parent: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return ExposureAutopsyCampaign(config, parent, atlas, upstream, output, workers).run()


def smoke_exposure_autopsy(
    config_path: Path,
    parent: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_exposure_autopsy_config(config_path)
    parent = parent.resolve()
    atlas = atlas.resolve()
    upstream = upstream.resolve()
    parents = validate_exposure_autopsy_parents(config, parent, atlas, upstream)
    task_id = str(config["exposure_task_ids"][0])
    seed_index = int(config["parent_seed_indices"][0])
    parent_map = _parent_records(parent)
    low_row, high_row = _parent_pair(parent_map, task_id, seed_index)
    parent_protocol = json.loads((parent / "registration.json").read_text(encoding="utf-8"))["protocol"]
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, float(config["delta_t"]))
    base = _naive_start(atlas, task_id)
    start, _ = _perturb_start(base, memory, parent_protocol, "exposure", task_id, seed_index)
    reconstructed = int(_calibration_map(atlas)[task_id]["reconstructed_ucs_bound_index"])
    training = run_epoch_schedule(
        backend,
        start,
        route_epochs(memory, config["route_specs"]["high_spaced"]),
        float(config["epoch_duration"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
    )
    washout = backend.run_unstimulated(
        training.state,
        float(config["route_analysis"]["washout_total"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
        float(config["washout_chunk_duration"]),
    )
    route_fp = _fingerprint(backend, memory, washout.state, config, reconstructed)
    route_score = bipolar_score(
        route_fp["fingerprint"], _fingerprint_from_parent(high_row), _fingerprint_from_parent(low_row)
    )
    continuation = backend.run_unstimulated(
        _state(high_row),
        float(config["washout_chunk_duration"]),
        memory.key.response_id,
        int(config["trajectory_samples"]),
        float(config["washout_chunk_duration"]),
    )
    continuation_fp = _fingerprint(backend, memory, continuation.state, config, reconstructed)
    route_unit_cpu = float(training.cpu_seconds + washout.cpu_seconds + route_fp["cpu_seconds"])
    parent_max_cpu = max(float(row["cpu_seconds"]) for row in _parent_records(parent).values())
    chunk_cpu = max(float(continuation.cpu_seconds), 1e-6)
    fingerprint_cpu = max(float(continuation_fp["cpu_seconds"]), 1e-6)
    route_count = len(config["exposure_task_ids"]) * len(config["parent_seed_indices"]) * len(config["route_order"])
    base_cases = len(config["exposure_task_ids"]) * len(config["parent_seed_indices"]) * 2
    base_chunks = int(round((float(config["long_horizon"]["checkpoint_total"]) - float(config["parent_washout_total"])) / float(config["washout_chunk_duration"])))
    ultra_cases = len(config["long_horizon"]["ultra_task_ids"]) * len(config["parent_seed_indices"]) * 2
    ultra_chunks = int(round((float(config["long_horizon"]["ultra_total"]) - float(config["long_horizon"]["checkpoint_total"])) / float(config["washout_chunk_duration"])))
    localization_cases = len(config["exposure_task_ids"]) * len(config["validation_seed_indices"]) * len(config["state_localization"]["conditions"])
    release_chunks = sum(float(value) / float(config["washout_chunk_duration"]) for value in config["state_localization"]["release_horizons"])
    projected_cpu = float(config["projection_safety_factor"]) * (
        max(route_unit_cpu, parent_max_cpu) * route_count
        + chunk_cpu * (base_cases * (base_chunks + 1) + ultra_cases * ultra_chunks + localization_cases * release_chunks)
        + fingerprint_cpu * (base_cases + ultra_cases + localization_cases * len(config["state_localization"]["release_horizons"]))
    )
    projected_wall = projected_cpu / float(config["max_workers"])
    source_fp_distance = vector_rms(
        np.asarray(route_fp["fingerprint"], dtype=float) - _fingerprint_from_parent(high_row)
    )
    allowed = bool(
        training.valid
        and washout.valid
        and route_fp["valid"]
        and continuation.valid
        and continuation_fp["valid"]
        and route_score is not None
        and abs(float(route_score) - 1.0) <= float(config["route_analysis"]["source_score_tolerance"])
        and source_fp_distance <= 1e-8
        and projected_cpu < float(config["soft_aggregate_cpu_seconds"])
        and projected_wall < float(config["soft_wall_seconds"])
    )
    result = {
        "target": "exposure-state-autopsy",
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "parent_manifest_sha256": parents["parent"]["manifest_sha256"],
        "atlas_parent_manifest_sha256": parents["atlas"]["manifest_sha256"],
        "worker_cap": int(config["max_workers"]),
        "biological_probe": {
            "memory_task_id": task_id,
            "seed_index": seed_index,
            "route": "high_spaced",
            "route_score": route_score,
            "source_fingerprint_distance": source_fp_distance,
            "route_unit_cpu_seconds": route_unit_cpu,
            "continuation_chunk_cpu_seconds": chunk_cpu,
            "fingerprint_cpu_seconds": fingerprint_cpu,
            "valid": bool(training.valid and washout.valid and route_fp["valid"]),
        },
        "projection": {
            "route_record_count": route_count,
            "long_base_case_count": base_cases,
            "long_ultra_case_count": ultra_cases,
            "localization_condition_count": localization_cases,
            "worst_case_aggregate_cpu_seconds": projected_cpu,
            "worst_case_active_wall_seconds_at_four_workers": projected_wall,
            "safety_factor": float(config["projection_safety_factor"]),
        },
        "deterministic_batch_plan": "task-by-seed shards with discovery/validation separation",
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "smoke.json", result)
    return result


def exposure_autopsy_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {"output": str(output), "sealed": (output / "SHA256SUMS").is_file()}
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "component-rankings",
        "long-horizon-decision",
        "route-factorial-decision",
        "state-localization-decision",
        "decision",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    for name in RECORD_FILES:
        path = output / name
        if path.is_file():
            result[f"{Path(name).stem.replace('-', '_')}_records"] = sum(1 for _ in read_jsonl(path))
    return result
