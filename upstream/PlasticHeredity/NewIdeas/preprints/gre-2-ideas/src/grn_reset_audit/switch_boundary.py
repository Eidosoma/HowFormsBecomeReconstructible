"""Prospective mapping of the task-10 direction-asymmetric switch boundary."""

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
from .carrier_discrimination import (
    _cone_project,
    _diverse_selection,
    _maximum_radius,
    _unit,
)
from .causal_carrier import (
    _contingency_protocol,
    _payload_state,
    _stable_seed,
    _task_resources,
    source_enclosing_envelope,
    transfer_metrics,
)
from .contingency import (
    _all_shard_cpu,
    _control_tokens,
    _naive_start,
    _parallel,
    _perturb_start,
    _run_history,
    _runtime_manifest,
    _verify_parent,
    quantile,
)
from .engine import State
from .exposure_autopsy import _merge_shards, _shard
from .renewal import ResourceLedger
from .upstream import PINNED_COMMIT, RELEASE_GENERATOR_COMMIT, validate_upstream


TASK_ID = "10-1-32"
EXPERIMENT_ID = "grn-switch-boundary-mapping-v1"
FRESH_SEEDS = tuple(range(232, 248))
RANKED_NODES = (1, 0, 2, 4, 3, 6, 5, 7)
LATCH_NODE = 7
RECORD_FILES = (
    "fresh-exposure.jsonl",
    "no-op.jsonl",
    "fine-boundary.jsonl",
    "single-node.jsonl",
    "matched-controls.jsonl",
    "pairwise-grid.jsonl",
    "reverse-masks.jsonl",
    "reverse-completion.jsonl",
    "timing-probes.jsonl",
)
EXPECTED_COUNTS = {
    "fresh-exposure.jsonl": 32,
    "no-op.jsonl": 32,
    "fine-boundary.jsonl": 640,
    "single-node.jsonl": 1344,
    "matched-controls.jsonl": 1024,
    "pairwise-grid.jsonl": 1200,
    "reverse-masks.jsonl": 384,
    "reverse-completion.jsonl": 384,
    "timing-probes.jsonl": 800,
}
METADATA_KEYS = (
    "assay",
    "direction",
    "dose",
    "delay",
    "node_index",
    "partner_node",
    "latch_dose",
    "partner_dose",
    "control_slot",
    "candidate_index",
    "target_norm",
    "latch_cosine",
    "observer_fraction",
    "mask_family",
    "mask_index",
    "selected_nodes",
    "withheld_node",
    "component_count",
    "base_full_dose",
    "completed_node",
)


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_text(path, "".join(canonical_json(dict(row)) + "\n" for row in records))


def _floats(values: Sequence[Any]) -> list[float]:
    return [float(value) for value in values]


def load_switch_boundary_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0" or config.get("experiment_kind") != "switch-boundary-mapping":
        raise ValueError("not a supported switch-boundary protocol")
    if config.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("unknown switch-boundary experiment ID")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("switch-boundary protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("switch-boundary protocol does not pin the release generator")
    if str(config.get("focal_task_id")) != TASK_ID:
        raise ValueError("switch-boundary focal task changed")
    if int(config.get("node_count", -1)) != 8 or int(config.get("latch_node_index", -1)) != LATCH_NODE:
        raise ValueError("switch-boundary latch coordinate changed")
    if tuple(int(value) for value in config.get("v1_ranked_nodes", ())) != RANKED_NODES:
        raise ValueError("switch-boundary V1 node rank changed")
    if tuple(int(value) for value in config.get("fresh_seed_indices", ())) != FRESH_SEEDS:
        raise ValueError("switch-boundary prospective cohort changed")
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
            raise ValueError(f"switch-boundary historical setting differs for {key}")
    if _floats(config["release_checkpoints"]) != [0.0, 25.0, 250.0, 2500.0, 12500.0]:
        raise ValueError("switch-boundary release checkpoints changed")
    fine = config["fine_boundary"]
    if list(fine["conditions"]) != ["full-expression", "latch-node"]:
        raise ValueError("fine-boundary conditions changed")
    if _floats(fine["low_to_high_doses"]) != [0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.0075, 0.01, 0.015, 0.025, 0.05]:
        raise ValueError("forward fine-boundary ladder changed")
    if _floats(fine["high_to_low_doses"]) != [0.5, 0.75, 0.9, 0.95, 0.975, 0.99, 0.995, 0.999, 1.0]:
        raise ValueError("reverse fine-boundary ladder changed")
    single = config["single_node"]
    if [int(value) for value in single["node_indices"]] != list(range(7)):
        raise ValueError("single-node census changed")
    controls = config["matched_controls"]
    if _floats(controls["doses"]) != [0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.0075, 0.01]:
        raise ValueError("matched-control dose ladder changed")
    if int(controls["controls_per_cell"]) != 8 or int(controls["candidate_pool_size"]) != 4096:
        raise ValueError("matched-control geometry changed")
    pairs = config["pairwise_grid"]
    if [int(value) for value in pairs["partner_nodes"]] != [1, 0, 2]:
        raise ValueError("pairwise partner set changed")
    if _floats(pairs["latch_doses"]) != [0.001, 0.0025, 0.005, 0.0075, 0.01]:
        raise ValueError("pairwise latch ladder changed")
    if _floats(pairs["partner_doses"]) != [0.001, 0.0025, 0.005, 0.0075, 0.01]:
        raise ValueError("pairwise partner ladder changed")
    if list(config["reverse_masks"]["families"]) != ["leave-one-behind", "ranked-cumulative", "anti-cumulative"]:
        raise ValueError("reverse mask families changed")
    if _floats(config["reverse_completion"]["base_full_doses"]) != [0.9, 0.99, 0.999]:
        raise ValueError("reverse completion ladder changed")
    if _floats(config["timing"]["delays"]) != [0.0, 25.0, 250.0, 2500.0, 12500.0]:
        raise ValueError("timing ladder changed")
    counts = {str(key): int(value) for key, value in config.get("registered_record_counts", {}).items()}
    if counts != EXPECTED_COUNTS or int(config.get("registered_condition_count", -1)) != sum(EXPECTED_COUNTS.values()):
        raise ValueError("switch-boundary registered record set changed")
    if int(config.get("max_workers", 0)) != 4:
        raise ValueError("switch-boundary campaign must cap workers at four")
    if not (0.0 < float(config["soft_wall_seconds"]) < float(config["terminate_wall_seconds"]) < float(config["hard_wall_seconds"]) <= 14400.0):
        raise ValueError("switch-boundary wall contract exceeds four hours")
    if not (0.0 < float(config["soft_aggregate_cpu_seconds"]) < float(config["hard_aggregate_cpu_seconds"]) <= 57600.0):
        raise ValueError("switch-boundary aggregate CPU contract is invalid")
    return config


def validate_switch_boundary_parents(
    config: Mapping[str, Any],
    discrimination: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
) -> dict[str, Any]:
    gates = {
        "upstream": validate_upstream(upstream, str(config["upstream_commit"])),
        "discrimination": _verify_parent(
            discrimination,
            str(config["discrimination_parent_experiment_id"]),
            config["discrimination_parent_hashes"],
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
    parent_decision = json.loads((discrimination / "decision.json").read_text(encoding="utf-8"))
    switch = json.loads((discrimination / "switch-10-decision.json").read_text(encoding="utf-8"))
    if parent_decision.get("verdict") != "direction-asymmetric-switch-memory-lead":
        raise ValueError("discrimination parent lacks the sealed switch lead")
    if switch.get("classification") != "direction-asymmetric-compact-threshold-switch" or not switch.get("asymmetric"):
        raise ValueError("discrimination parent lacks direction asymmetry")
    thresholds = switch.get("directional_thresholds", {})
    if thresholds.get("anti-ranked-1") != {"high-to-low": None, "low-to-high": 0.01}:
        raise ValueError("discrimination parent node-7 lead changed")
    model = _task_model(discrimination)
    if int(model.get("node_count", -1)) != 8 or [int(value) for value in model.get("anti_ranked_nodes", ())] != [LATCH_NODE]:
        raise ValueError("discrimination parent latch model changed")
    if tuple(int(value) for value in model.get("ranked_nodes", ())) != RANKED_NODES:
        raise ValueError("discrimination parent node ranking changed")
    return gates


def _models_payload(discrimination: Path) -> dict[str, Any]:
    return json.loads((discrimination / "v1-carrier-models.json").read_text(encoding="utf-8"))


def _task_model(discrimination: Path) -> dict[str, Any]:
    payload = _models_payload(discrimination)
    matches = [dict(row) for row in payload["models"] if str(row["memory_task_id"]) == TASK_ID]
    if len(matches) != 1:
        raise ValueError("task-10 carrier model is missing or duplicated")
    return matches[0]


def _fresh_map(output: Path) -> dict[tuple[int, str], dict[str, Any]]:
    return {
        (int(row["seed_index"]), str(row["arm"])): dict(row)
        for row in read_jsonl(output / "fresh-exposure.jsonl")
    }


def _no_op_map(output: Path) -> dict[tuple[int, str], dict[str, Any]]:
    return {
        (int(row["seed_index"]), str(row["arm"])): dict(row)
        for row in read_jsonl(output / "no-op.jsonl")
    }


def state_from_node_fractions(
    recipient: State,
    donor: State,
    node_fractions: Mapping[int, float],
    scale: Sequence[float],
) -> tuple[State | None, dict[str, Any]]:
    """Move selected expression coordinates exactly toward a donor endpoint."""

    if recipient.y.shape != donor.y.shape:
        raise ValueError("recipient and donor expression states differ")
    fractions = np.zeros(len(recipient.y), dtype=float)
    for node, fraction in node_fractions.items():
        index, value = int(node), float(fraction)
        if index < 0 or index >= len(fractions) or not 0.0 <= value <= 1.0:
            raise ValueError("invalid endpoint-directed node fraction")
        fractions[index] = value
    y = recipient.y + fractions * (donor.y - recipient.y)
    envelope = np.column_stack((np.minimum(recipient.y, donor.y), np.maximum(recipient.y, donor.y)))
    if np.any(y < envelope[:, 0] - 1e-10) or np.any(y > envelope[:, 1] + 1e-10):
        raise AssertionError("endpoint-directed intervention escaped its envelope")
    standardized = (y - recipient.y) / np.asarray(scale, dtype=float)
    norm = float(np.linalg.norm(standardized))
    detail = {
        "requested_standardized_norm": norm,
        "applied_standardized_norm": norm,
        "effective_dimension": int(np.count_nonzero(np.abs(standardized) > 1e-14)),
        "coefficient_fraction": max(node_fractions.values(), default=0.0),
        "node_fractions": {str(int(node)): float(value) for node, value in node_fractions.items()},
    }
    if norm <= 1e-12:
        return None, detail
    return State(y, recipient.w.copy(), recipient.c.copy(), float(recipient.t)), detail


def _condition_state(
    recipient: State,
    donor: State,
    condition: str,
    dose: float,
    scale: Sequence[float],
    latch_node: int = LATCH_NODE,
) -> tuple[State | None, dict[str, Any]]:
    if condition == "full-expression":
        fractions = {index: float(dose) for index in range(len(recipient.y))}
    elif condition == "latch-node":
        fractions = {int(latch_node): float(dose)}
    elif condition.startswith("node-"):
        fractions = {int(condition.split("-", 1)[1]): float(dose)}
    else:
        raise ValueError(f"unknown switch-boundary condition: {condition}")
    return state_from_node_fractions(recipient, donor, fractions, scale)


def _invalid(seed_index: int, condition_id: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "task_id": f"invalid|{TASK_ID}|{seed_index}|{condition_id}",
        "condition_id": condition_id,
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "valid": False,
        "reason": str(reason),
        "fingerprint": None,
        "bipolar_score": None,
        **extra,
    }


def _common(
    memory: Any,
    seed_index: int,
    recipient_arm: str,
    condition: str,
    assay: str,
    **extra: Any,
) -> dict[str, Any]:
    target_arm = "high" if recipient_arm == "low" else "low"
    return {
        "assay": assay,
        "memory_task_id": TASK_ID,
        "model_id": int(memory.key.model_id),
        "seed_index": int(seed_index),
        "seed_role": "fresh-prospective",
        "recipient_arm": recipient_arm,
        "donor_arm": target_arm,
        "target_arm": target_arm,
        "direction": f"{recipient_arm}-to-{target_arm}",
        "condition": str(condition),
        "is_primary_candidate": str(condition) == "latch-node",
        "primary_eligible": True,
        **extra,
    }


def _fresh_exposure_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, contingency_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "fresh-exposure", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    history_config = _contingency_protocol(Path(contingency_path))
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_ID)
    base = _naive_start(Path(atlas_path), TASK_ID)
    start, philox_seed = _perturb_start(
        base, memory, history_config, "switch-boundary", TASK_ID, int(seed_index)
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
                "task_id": f"switch-boundary-fresh|{TASK_ID}|{seed_index}|{arm}",
                "assay": "fresh-ucs-only-exposure-history",
                "memory_task_id": TASK_ID,
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
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _no_op_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "no-op", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    fresh = _fresh_map(output)
    memory, backend, reconstructed = _task_resources(config, Path(atlas_path), Path(upstream_path), TASK_ID)
    references = {
        arm: np.asarray(fresh[(int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for arm in ("low", "high"):
        source = _payload_state(fresh[(int(seed_index), arm)]["source_state"])
        result, used_cpu, used_wall = _finish_record(
            backend, memory, reconstructed, config, source, references["high"], references["low"]
        )
        cpu += used_cpu
        wall += used_wall
        records.append(
            {
                "task_id": f"switch-boundary-no-op|{TASK_ID}|{seed_index}|{arm}",
                "condition_id": f"no-op|{arm}",
                "assay": "release-matched-no-op",
                "memory_task_id": TASK_ID,
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
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def matched_latch_control_slots(
    config: Mapping[str, Any],
    recipient: State,
    donor: State,
    model: Mapping[str, Any],
    bounds: np.ndarray,
    seed_index: int,
    dose: float,
) -> list[dict[str, Any]]:
    """Freeze norm-matched, latch-orthogonal controls without outcome feedback."""

    settings = config["matched_controls"]
    scale = np.asarray(model["scale"], dtype=float)
    delta = (donor.y - recipient.y) / scale
    latch = np.zeros_like(delta)
    latch[LATCH_NODE] = delta[LATCH_NODE]
    target_norm = float(dose) * float(np.linalg.norm(latch))
    latch_unit = _unit(latch)
    observer = np.asarray(model["observer_map"]["matrix"], dtype=float)
    observer_latch = observer @ latch_unit
    observer_denominator = max(float(np.dot(observer_latch, observer_latch)), 1e-12)
    envelope = source_enclosing_envelope(recipient, bounds)
    rng = np.random.Generator(
        np.random.Philox(_stable_seed(config, "switch-boundary-controls", TASK_ID, seed_index, dose))
    )
    eligible: list[dict[str, Any]] = []
    for candidate_index in range(int(settings["candidate_pool_size"])):
        direction = rng.normal(size=len(scale))
        direction -= float(np.dot(direction, latch_unit)) * latch_unit
        direction = _cone_project(direction, recipient, envelope, scale)
        if direction is None:
            continue
        direction -= float(np.dot(direction, latch_unit)) * latch_unit
        direction = _cone_project(direction, recipient, envelope, scale)
        if direction is None:
            continue
        feasible = _maximum_radius(recipient, direction, scale, envelope)
        if feasible + 1e-10 < target_norm:
            continue
        latch_cosine = abs(float(np.dot(direction, latch_unit)))
        predicted = observer @ direction
        observer_fraction = abs(float(np.dot(predicted, observer_latch) / observer_denominator))
        if latch_cosine > float(settings["maximum_latch_cosine"]) + 1e-12:
            continue
        if observer_fraction > float(settings["maximum_observer_transfer_fraction"]) + 1e-12:
            continue
        eligible.append(
            {
                "candidate_index": int(candidate_index),
                "direction": direction,
                "maximum_feasible_radius": feasible,
                "latch_cosine": latch_cosine,
                "observer_fraction": observer_fraction,
            }
        )
    selected = _diverse_selection(eligible, int(settings["controls_per_cell"]))
    slots: list[dict[str, Any]] = []
    for slot in range(int(settings["controls_per_cell"])):
        if slot < len(selected):
            slots.append({"slot": slot, "available": True, "target_norm": target_norm, **selected[slot]})
        else:
            slots.append(
                {
                    "slot": slot,
                    "available": False,
                    "target_norm": target_norm,
                    "reason": "no-feasible-latch-orthogonal-observer-quiet-candidate",
                }
            )
    return slots


def build_control_geometry(
    config: Mapping[str, Any], discrimination: Path, atlas: Path, upstream: Path, output: Path
) -> tuple[dict[str, Any], float]:
    started = time.process_time()
    fresh = _fresh_map(output)
    model = _task_model(discrimination)
    memory, _, _ = _task_resources(config, atlas, upstream, TASK_ID)
    bounds = np.asarray(memory.bounds, dtype=float)
    cells: list[dict[str, Any]] = []
    for seed_index in config["fresh_seed_indices"]:
        low = _payload_state(fresh[(int(seed_index), "low")]["source_state"])
        high = _payload_state(fresh[(int(seed_index), "high")]["source_state"])
        for dose in config["matched_controls"]["doses"]:
            cells.append(
                {
                    "memory_task_id": TASK_ID,
                    "seed_index": int(seed_index),
                    "recipient_arm": "low",
                    "donor_arm": "high",
                    "dose": float(dose),
                    "slots": matched_latch_control_slots(
                        config, low, high, model, bounds, int(seed_index), float(dose)
                    ),
                }
            )
    return (
        {
            "task_id": "switch-boundary-control-geometry",
            "protocol_digest": digest(config),
            "selection_frozen_before_post_intervention_outcomes": True,
            "fresh_endpoint_states_used_only_for_feasibility": True,
            "post_intervention_outcomes_used": False,
            "cells": cells,
        },
        float(time.process_time() - started),
    )


def _control_map(output: Path) -> dict[tuple[int, float], list[dict[str, Any]]]:
    payload = json.loads((output / "control-geometry.json").read_text(encoding="utf-8"))
    return {
        (int(cell["seed_index"]), float(cell["dose"])): [dict(slot) for slot in cell["slots"]]
        for cell in payload["cells"]
    }


def _context(
    config: Mapping[str, Any],
    discrimination: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    seed_index: int,
) -> tuple[Any, Any, int, dict[str, State], dict[str, np.ndarray], dict[str, Any]]:
    fresh, no_ops = _fresh_map(output), _no_op_map(output)
    model = _task_model(discrimination)
    memory, backend, reconstructed = _task_resources(config, atlas, upstream, TASK_ID)
    states = {
        arm: _payload_state(fresh[(int(seed_index), arm)]["source_state"])
        for arm in ("low", "high")
    }
    references = {
        arm: np.asarray(no_ops[(int(seed_index), arm)]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    return memory, backend, reconstructed, states, references, model


def _finish_intervention(
    records: list[dict[str, Any]],
    backend: Any,
    memory: Any,
    reconstructed: int,
    config: Mapping[str, Any],
    start: State | None,
    references: Mapping[str, np.ndarray],
    common: Mapping[str, Any],
    condition_id: str,
    intervention: Mapping[str, Any],
) -> tuple[float, float]:
    if start is None:
        records.append(
            _invalid(
                int(common["seed_index"]),
                condition_id,
                "zero-component-at-dose",
                **common,
                **intervention,
            )
        )
        return 0.0, 0.0
    result, cpu, wall = _finish_record(
        backend,
        memory,
        reconstructed,
        config,
        start,
        references["high"],
        references["low"],
    )
    records.append(
        {
            "task_id": f"{condition_id}|{TASK_ID}|{common['seed_index']}",
            "condition_id": condition_id,
            **common,
            **intervention,
            **result,
        }
    )
    return float(cpu), float(wall)


def _fine_boundary_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, discrimination_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "fine-boundary", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    memory, backend, reconstructed, states, refs, model = _context(
        config, Path(discrimination_path), Path(atlas_path), Path(upstream_path), output, int(seed_index)
    )
    scale = np.asarray(model["scale"], dtype=float)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    settings = config["fine_boundary"]
    for recipient_arm, dose_key in (("low", "low_to_high_doses"), ("high", "high_to_low_doses")):
        donor_arm = "high" if recipient_arm == "low" else "low"
        for condition in settings["conditions"]:
            for dose in settings[dose_key]:
                value = float(dose)
                condition_id = f"fine|{recipient_arm}-to-{donor_arm}|{condition}|d={value:g}"
                common = _common(
                    memory,
                    int(seed_index),
                    recipient_arm,
                    str(condition),
                    "fine-switch-boundary",
                    dose=value,
                )
                start, intervention = _condition_state(
                    states[recipient_arm], states[donor_arm], str(condition), value, scale
                )
                used_cpu, used_wall = _finish_intervention(
                    records, backend, memory, reconstructed, config, start, refs, common, condition_id, intervention
                )
                cpu += used_cpu
                wall += used_wall
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "fine-boundary",
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _single_node_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, discrimination_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "single-node", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    memory, backend, reconstructed, states, refs, model = _context(
        config, Path(discrimination_path), Path(atlas_path), Path(upstream_path), output, int(seed_index)
    )
    scale = np.asarray(model["scale"], dtype=float)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    settings = config["single_node"]
    for node_index in settings["node_indices"]:
        condition = f"node-{int(node_index)}"
        for recipient_arm, dose_key in (("low", "low_to_high_doses"), ("high", "high_to_low_doses")):
            donor_arm = "high" if recipient_arm == "low" else "low"
            for dose in settings[dose_key]:
                value = float(dose)
                condition_id = f"single|{recipient_arm}-to-{donor_arm}|node={node_index}|d={value:g}"
                common = _common(
                    memory,
                    int(seed_index),
                    recipient_arm,
                    condition,
                    "single-node-census",
                    dose=value,
                    node_index=int(node_index),
                )
                start, intervention = _condition_state(
                    states[recipient_arm], states[donor_arm], condition, value, scale
                )
                used_cpu, used_wall = _finish_intervention(
                    records, backend, memory, reconstructed, config, start, refs, common, condition_id, intervention
                )
                cpu += used_cpu
                wall += used_wall
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "single-node",
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _matched_control_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, discrimination_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "matched-controls", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    memory, backend, reconstructed, states, refs, model = _context(
        config, Path(discrimination_path), Path(atlas_path), Path(upstream_path), output, int(seed_index)
    )
    controls = _control_map(output)
    scale = np.asarray(model["scale"], dtype=float)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for dose in config["matched_controls"]["doses"]:
        value = float(dose)
        for slot in controls[(int(seed_index), value)]:
            condition = f"matched-control-{int(slot['slot'])}"
            condition_id = f"control|low-to-high|d={value:g}|slot={int(slot['slot'])}"
            common = _common(
                memory,
                int(seed_index),
                "low",
                condition,
                "norm-matched-latch-orthogonal-control",
                dose=value,
                control_slot=int(slot["slot"]),
                candidate_index=slot.get("candidate_index"),
                target_norm=float(slot["target_norm"]),
                latch_cosine=slot.get("latch_cosine"),
                observer_fraction=slot.get("observer_fraction"),
            )
            if not bool(slot.get("available")):
                records.append(
                    _invalid(
                        int(seed_index),
                        condition_id,
                        str(slot.get("reason", "unavailable-control")),
                        **common,
                    )
                )
                continue
            direction = np.asarray(slot["direction"], dtype=float)
            y = states["low"].y + float(slot["target_norm"]) * direction * scale
            start = State(y, states["low"].w.copy(), states["low"].c.copy(), float(states["low"].t))
            intervention = {
                "requested_standardized_norm": float(slot["target_norm"]),
                "applied_standardized_norm": float(slot["target_norm"]),
                "effective_dimension": int(np.count_nonzero(np.abs(direction) > 1e-14)),
                "coefficient_fraction": None,
            }
            used_cpu, used_wall = _finish_intervention(
                records, backend, memory, reconstructed, config, start, refs, common, condition_id, intervention
            )
            cpu += used_cpu
            wall += used_wall
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "matched-controls",
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _pairwise_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, discrimination_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "pairwise-grid", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    memory, backend, reconstructed, states, refs, model = _context(
        config, Path(discrimination_path), Path(atlas_path), Path(upstream_path), output, int(seed_index)
    )
    scale = np.asarray(model["scale"], dtype=float)
    settings = config["pairwise_grid"]
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for partner in settings["partner_nodes"]:
        for latch_dose in settings["latch_doses"]:
            for partner_dose in settings["partner_doses"]:
                a, b = float(latch_dose), float(partner_dose)
                condition = f"latch-{LATCH_NODE}+node-{int(partner)}"
                condition_id = f"pair|low-to-high|partner={int(partner)}|a={a:g}|b={b:g}"
                common = _common(
                    memory,
                    int(seed_index),
                    "low",
                    condition,
                    "conditional-pairwise-grid",
                    partner_node=int(partner),
                    latch_dose=a,
                    partner_dose=b,
                )
                start, intervention = state_from_node_fractions(
                    states["low"], states["high"], {LATCH_NODE: a, int(partner): b}, scale
                )
                used_cpu, used_wall = _finish_intervention(
                    records, backend, memory, reconstructed, config, start, refs, common, condition_id, intervention
                )
                cpu += used_cpu
                wall += used_wall
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "pairwise-grid",
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def reverse_mask_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    all_nodes = list(range(8))
    for node in all_nodes:
        specs.append(
            {
                "family": "leave-one-behind",
                "mask_index": int(node),
                "selected_nodes": [value for value in all_nodes if value != node],
                "withheld_node": int(node),
            }
        )
    for family, order in (("ranked-cumulative", list(RANKED_NODES)), ("anti-cumulative", list(reversed(RANKED_NODES)))):
        for index in range(1, 9):
            specs.append(
                {
                    "family": family,
                    "mask_index": index - 1,
                    "selected_nodes": order[:index],
                    "withheld_node": None,
                }
            )
    if len(specs) != 24:
        raise AssertionError("reverse mask registration is not 24 conditions")
    return specs


def _reverse_mask_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, discrimination_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "reverse-masks", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    memory, backend, reconstructed, states, refs, model = _context(
        config, Path(discrimination_path), Path(atlas_path), Path(upstream_path), output, int(seed_index)
    )
    scale = np.asarray(model["scale"], dtype=float)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for spec in reverse_mask_specs():
        selected = [int(value) for value in spec["selected_nodes"]]
        condition = f"{spec['family']}-{int(spec['mask_index'])}"
        condition_id = f"reverse-mask|{spec['family']}|index={int(spec['mask_index'])}"
        common = _common(
            memory,
            int(seed_index),
            "high",
            condition,
            "reverse-component-mask",
            mask_family=str(spec["family"]),
            mask_index=int(spec["mask_index"]),
            selected_nodes=selected,
            withheld_node=spec["withheld_node"],
            component_count=len(selected),
        )
        start, intervention = state_from_node_fractions(
            states["high"], states["low"], {node: 1.0 for node in selected}, scale
        )
        used_cpu, used_wall = _finish_intervention(
            records, backend, memory, reconstructed, config, start, refs, common, condition_id, intervention
        )
        cpu += used_cpu
        wall += used_wall
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "reverse-masks",
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _reverse_completion_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, discrimination_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "reverse-completion", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    memory, backend, reconstructed, states, refs, model = _context(
        config, Path(discrimination_path), Path(atlas_path), Path(upstream_path), output, int(seed_index)
    )
    scale = np.asarray(model["scale"], dtype=float)
    settings = config["reverse_completion"]
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for base_dose in settings["base_full_doses"]:
        for node in settings["node_indices"]:
            value, index = float(base_dose), int(node)
            fractions = {candidate: value for candidate in range(8)}
            fractions[index] = 1.0
            condition = f"full-{value:g}+complete-node-{index}"
            condition_id = f"reverse-completion|base={value:g}|node={index}"
            common = _common(
                memory,
                int(seed_index),
                "high",
                condition,
                "reverse-near-boundary-node-completion",
                base_full_dose=value,
                completed_node=index,
            )
            start, intervention = state_from_node_fractions(states["high"], states["low"], fractions, scale)
            used_cpu, used_wall = _finish_intervention(
                records, backend, memory, reconstructed, config, start, refs, common, condition_id, intervention
            )
            cpu += used_cpu
            wall += used_wall
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "reverse-completion",
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _timing_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    config_path, discrimination_path, atlas_path, upstream_path, output_path, seed_index = args
    config = load_switch_boundary_config(Path(config_path))
    output = Path(output_path)
    protocol_digest = digest(config)
    shard_path, prior = _shard(output, "timing-probes", str(seed_index), protocol_digest)
    if prior is not None:
        return prior
    memory, backend, reconstructed, _, refs, model = _context(
        config, Path(discrimination_path), Path(atlas_path), Path(upstream_path), output, int(seed_index)
    )
    scale = np.asarray(model["scale"], dtype=float)
    no_ops = _no_op_map(output)
    records: list[dict[str, Any]] = []
    cpu = wall = 0.0
    for delay in config["timing"]["delays"]:
        delay_value = float(delay)
        checkpoint = f"{delay_value:g}"
        states = {
            arm: _payload_state(no_ops[(int(seed_index), arm)]["checkpoints"][checkpoint]["state"])
            for arm in ("low", "high")
        }
        for direction_key, recipient_arm in (("low_to_high", "low"), ("high_to_low", "high")):
            donor_arm = "high" if recipient_arm == "low" else "low"
            for condition, doses in config["timing"][direction_key].items():
                for dose in doses:
                    value = float(dose)
                    condition_id = f"timing|delay={delay_value:g}|{recipient_arm}-to-{donor_arm}|{condition}|d={value:g}"
                    common = _common(
                        memory,
                        int(seed_index),
                        recipient_arm,
                        str(condition),
                        "intervention-age-probe",
                        delay=delay_value,
                        dose=value,
                    )
                    start, intervention = _condition_state(
                        states[recipient_arm], states[donor_arm], str(condition), value, scale
                    )
                    used_cpu, used_wall = _finish_intervention(
                        records, backend, memory, reconstructed, config, start, refs, common, condition_id, intervention
                    )
                    cpu += used_cpu
                    wall += used_wall
    payload = {
        "protocol_digest": protocol_digest,
        "stage": "timing-probes",
        "memory_task_id": TASK_ID,
        "seed_index": int(seed_index),
        "aggregate_cpu_seconds": cpu,
        "aggregate_wall_seconds": wall,
        "records": records,
    }
    write_json(shard_path, payload)
    return payload


def _metrics(
    rows: Sequence[Mapping[str, Any]],
    no_ops: Sequence[Mapping[str, Any]],
    models: Mapping[str, Any],
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    source = {str(row["task_id"]): row for row in rows}
    metrics = transfer_metrics(rows, no_ops, models, config)
    for metric in metrics:
        row = source[str(metric["source_task_id"])]
        for key in METADATA_KEYS:
            if key in row:
                metric[key] = row[key]
    return metrics


def metric_success(row: Mapping[str, Any], config: Mapping[str, Any]) -> bool:
    return bool(
        row.get("valid")
        and row.get("target_oriented_bipolar_score") is not None
        and float(row["target_oriented_bipolar_score"]) >= float(config["decision"]["target_bipolar_min"])
        and row.get("target_fingerprint_rms") is not None
        and float(row["target_fingerprint_rms"]) <= float(config["decision"]["fingerprint_rms_max"])
    )


def _cell_summary(rows: Sequence[Mapping[str, Any]], config: Mapping[str, Any], **labels: Any) -> dict[str, Any]:
    valid = [row for row in rows if bool(row.get("valid"))]
    return {
        **labels,
        "registered_count": len(rows),
        "valid_count": len(valid),
        "success_count": sum(metric_success(row, config) for row in rows),
        "median_target_bipolar": quantile(
            [float(row["target_oriented_bipolar_score"]) for row in valid if row.get("target_oriented_bipolar_score") is not None],
            0.5,
        ),
        "median_fingerprint_rms": quantile(
            [float(row["target_fingerprint_rms"]) for row in valid if row.get("target_fingerprint_rms") is not None],
            0.5,
        ),
    }


def fine_boundary_decision(metrics: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    settings = config["fine_boundary"]
    required = int(config["decision"]["minimum_consistent_seeds"])
    summaries: list[dict[str, Any]] = []
    thresholds: dict[tuple[str, str], float | None] = {}
    for condition in settings["conditions"]:
        for direction, dose_key in (("low-to-high", "low_to_high_doses"), ("high-to-low", "high_to_low_doses")):
            passing: list[float] = []
            for dose in settings[dose_key]:
                rows = [
                    row for row in metrics
                    if str(row.get("condition")) == str(condition)
                    and str(row.get("direction")) == direction
                    and math.isclose(float(row.get("dose", -1.0)), float(dose))
                ]
                summary = _cell_summary(rows, config, condition=str(condition), direction=direction, dose=float(dose))
                summaries.append(summary)
                if int(summary["success_count"]) >= required:
                    passing.append(float(dose))
            thresholds[(str(condition), direction)] = min(passing) if passing else None
    directional = {
        condition: {
            direction: thresholds[(condition, direction)]
            for direction in ("low-to-high", "high-to-low")
        }
        for condition in settings["conditions"]
    }
    forward = directional["latch-node"]["low-to-high"]
    reverse = directional["latch-node"]["high-to-low"]
    full_reverse = directional["full-expression"]["high-to-low"]
    classification = (
        "fine-direction-asymmetric-boundary"
        if forward is not None and reverse is None and full_reverse is not None
        else "fine-boundary-mixed-or-unresolved"
    )
    return {
        "task_id": "fine-boundary-decision",
        "dose_summaries": summaries,
        "directional_thresholds": directional,
        "classification": classification,
    }


def specificity_decision(
    fine_metrics: Sequence[Mapping[str, Any]],
    single_metrics: Sequence[Mapping[str, Any]],
    control_metrics: Sequence[Mapping[str, Any]],
    fine: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    required = int(config["decision"]["minimum_consistent_seeds"])
    latch_threshold = fine["directional_thresholds"]["latch-node"]["low-to-high"]
    node_summaries: list[dict[str, Any]] = []
    node_thresholds: dict[int, float | None] = {}
    for node in config["single_node"]["node_indices"]:
        passing: list[float] = []
        for dose in config["single_node"]["low_to_high_doses"]:
            rows = [
                row for row in single_metrics
                if int(row.get("node_index", -1)) == int(node)
                and str(row.get("direction")) == "low-to-high"
                and math.isclose(float(row.get("dose", -1.0)), float(dose))
            ]
            summary = _cell_summary(rows, config, node_index=int(node), direction="low-to-high", dose=float(dose))
            node_summaries.append(summary)
            if int(summary["success_count"]) >= required:
                passing.append(float(dose))
        node_thresholds[int(node)] = min(passing) if passing else None
    control_summary: dict[str, Any] = {
        "dose": latch_threshold,
        "eligible_seed_count": 0,
        "switch_seed_count": None,
        "valid_control_count": 0,
        "registered_control_count": 0,
    }
    controls_comparable = latch_threshold is not None and any(
        math.isclose(float(latch_threshold), float(value)) for value in config["matched_controls"]["doses"]
    )
    if controls_comparable:
        rows = [
            row for row in control_metrics
            if math.isclose(float(row.get("dose", -1.0)), float(latch_threshold))
        ]
        per_seed_valid: dict[int, int] = {}
        per_seed_switch: dict[int, bool] = {}
        for row in rows:
            seed = int(row["seed_index"])
            per_seed_valid[seed] = per_seed_valid.get(seed, 0) + int(bool(row.get("valid")))
            per_seed_switch[seed] = per_seed_switch.get(seed, False) or metric_success(row, config)
        control_summary = {
            "dose": float(latch_threshold),
            "eligible_seed_count": sum(
                count >= int(config["matched_controls"]["minimum_controls_per_seed"])
                for count in per_seed_valid.values()
            ),
            "switch_seed_count": sum(per_seed_switch.values()),
            "valid_control_count": sum(bool(row.get("valid")) for row in rows),
            "registered_control_count": len(rows),
        }
    other_passing_at_or_below = [
        node for node, threshold in node_thresholds.items()
        if threshold is not None and latch_threshold is not None and float(threshold) <= float(latch_threshold) + 1e-15
    ]
    controls_clean = bool(
        controls_comparable
        and int(control_summary["eligible_seed_count"]) >= required
        and int(control_summary["switch_seed_count"]) <= int(config["decision"]["control_switch_seed_max"])
    )
    node_specific = bool(latch_threshold is not None and controls_clean and not other_passing_at_or_below)
    globally_fragile = bool(
        len(other_passing_at_or_below) >= int(config["decision"]["global_fragility_other_node_min"])
        or (
            control_summary["switch_seed_count"] is not None
            and int(control_summary["switch_seed_count"]) >= int(config["decision"]["global_fragility_control_seed_min"])
        )
    )
    if node_specific:
        classification = "node-specific-forward-latch"
    elif globally_fragile:
        classification = "non-specific-fragile-boundary"
    elif latch_threshold is not None and not controls_comparable:
        classification = "forward-latch-control-dose-unresolved"
    else:
        classification = "specificity-mixed-or-unresolved"
    return {
        "task_id": "specificity-decision",
        "latch_threshold": latch_threshold,
        "node_thresholds": [
            {"node_index": node, "dose": threshold}
            for node, threshold in sorted(node_thresholds.items())
        ],
        "node_dose_summaries": node_summaries,
        "other_nodes_passing_at_or_below_latch": other_passing_at_or_below,
        "matched_control_summary": control_summary,
        "controls_comparable": controls_comparable,
        "node_specific": node_specific,
        "globally_fragile": globally_fragile,
        "classification": classification,
    }


def pairwise_decision(
    pair_metrics: Sequence[Mapping[str, Any]],
    fine_metrics: Sequence[Mapping[str, Any]],
    single_metrics: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    required = int(config["decision"]["minimum_consistent_seeds"])
    failure_max = int(config["decision"]["strong_failure_seed_max"])
    summaries: list[dict[str, Any]] = []
    synergy: list[dict[str, Any]] = []
    antagonism: list[dict[str, Any]] = []
    for partner in config["pairwise_grid"]["partner_nodes"]:
        for latch_dose in config["pairwise_grid"]["latch_doses"]:
            for partner_dose in config["pairwise_grid"]["partner_doses"]:
                a, b = float(latch_dose), float(partner_dose)
                rows = [
                    row for row in pair_metrics
                    if int(row.get("partner_node", -1)) == int(partner)
                    and math.isclose(float(row.get("latch_dose", -1.0)), a)
                    and math.isclose(float(row.get("partner_dose", -1.0)), b)
                ]
                latch_rows = [
                    row for row in fine_metrics
                    if str(row.get("condition")) == "latch-node"
                    and str(row.get("direction")) == "low-to-high"
                    and math.isclose(float(row.get("dose", -1.0)), a)
                ]
                partner_rows = [
                    row for row in single_metrics
                    if int(row.get("node_index", -1)) == int(partner)
                    and str(row.get("direction")) == "low-to-high"
                    and math.isclose(float(row.get("dose", -1.0)), b)
                ]
                pair_success = sum(metric_success(row, config) for row in rows)
                latch_success = sum(metric_success(row, config) for row in latch_rows)
                partner_success = sum(metric_success(row, config) for row in partner_rows)
                summary = {
                    **_cell_summary(
                        rows,
                        config,
                        partner_node=int(partner),
                        latch_dose=a,
                        partner_dose=b,
                    ),
                    "latch_alone_success_count": latch_success,
                    "partner_alone_success_count": partner_success,
                }
                summaries.append(summary)
                if pair_success >= required and latch_success <= failure_max and partner_success <= failure_max:
                    synergy.append(summary)
                if latch_success >= required and pair_success <= failure_max:
                    antagonism.append(summary)
    conditional_gate = bool(synergy)
    classification = (
        "conditional-pair-gate"
        if conditional_gate
        else "pairwise-antagonism"
        if antagonism
        else "no-strong-pairwise-gate"
    )
    return {
        "task_id": "pairwise-decision",
        "cell_summaries": summaries,
        "synergy_cells": synergy,
        "antagonistic_cells": antagonism,
        "conditional_gate": conditional_gate,
        "classification": classification,
    }


def reverse_decision(
    mask_metrics: Sequence[Mapping[str, Any]],
    completion_metrics: Sequence[Mapping[str, Any]],
    fine_metrics: Sequence[Mapping[str, Any]],
    fine: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    required = int(config["decision"]["minimum_consistent_seeds"])
    failure_max = int(config["decision"]["strong_failure_seed_max"])
    mask_summaries: list[dict[str, Any]] = []
    for spec in reverse_mask_specs():
        rows = [
            row for row in mask_metrics
            if str(row.get("mask_family")) == str(spec["family"])
            and int(row.get("mask_index", -1)) == int(spec["mask_index"])
        ]
        mask_summaries.append(
            _cell_summary(
                rows,
                config,
                mask_family=str(spec["family"]),
                mask_index=int(spec["mask_index"]),
                selected_nodes=list(spec["selected_nodes"]),
                withheld_node=spec["withheld_node"],
                component_count=len(spec["selected_nodes"]),
            )
        )
    indispensable = [
        int(row["withheld_node"])
        for row in mask_summaries
        if row["mask_family"] == "leave-one-behind"
        and int(row["success_count"]) <= failure_max
    ]
    path_thresholds: dict[str, int | None] = {}
    for family in ("ranked-cumulative", "anti-cumulative"):
        passing = [
            int(row["component_count"])
            for row in mask_summaries
            if row["mask_family"] == family and int(row["success_count"]) >= required
        ]
        path_thresholds[family] = min(passing) if passing else None
    values = list(path_thresholds.values())
    path_dependent = bool(
        values[0] is not None
        and values[1] is not None
        and abs(int(values[0]) - int(values[1])) >= int(config["decision"]["path_component_difference_min"])
    )
    completion_summaries: list[dict[str, Any]] = []
    unlocks: list[dict[str, Any]] = []
    for base in config["reverse_completion"]["base_full_doses"]:
        base_value = float(base)
        base_rows = [
            row for row in fine_metrics
            if str(row.get("condition")) == "full-expression"
            and str(row.get("direction")) == "high-to-low"
            and math.isclose(float(row.get("dose", -1.0)), base_value)
        ]
        base_success = sum(metric_success(row, config) for row in base_rows)
        for node in config["reverse_completion"]["node_indices"]:
            rows = [
                row for row in completion_metrics
                if int(row.get("completed_node", -1)) == int(node)
                and math.isclose(float(row.get("base_full_dose", -1.0)), base_value)
            ]
            summary = {
                **_cell_summary(rows, config, base_full_dose=base_value, completed_node=int(node)),
                "base_success_count": base_success,
            }
            completion_summaries.append(summary)
            if base_success <= failure_max and int(summary["success_count"]) >= required:
                unlocks.append(summary)
    full_threshold = fine["directional_thresholds"]["full-expression"]["high-to-low"]
    latch_threshold = fine["directional_thresholds"]["latch-node"]["high-to-low"]
    reverse_distributed = bool(
        full_threshold is not None
        and float(full_threshold) >= float(config["decision"]["reverse_near_full_min"])
        and latch_threshold is None
        and (len(indispensable) >= 2 or path_dependent or len(unlocks) >= 2)
    )
    if reverse_distributed:
        classification = "distributed-conjunctive-reverse-gate"
    elif full_threshold is not None and latch_threshold is None:
        classification = "near-full-reverse-gate-mechanism-unresolved"
    elif latch_threshold is not None:
        classification = "compact-reverse-gate"
    else:
        classification = "reverse-transfer-unresolved"
    return {
        "task_id": "reverse-decision",
        "full_expression_threshold": full_threshold,
        "latch_node_threshold": latch_threshold,
        "mask_summaries": mask_summaries,
        "indispensable_nodes": indispensable,
        "path_component_thresholds": path_thresholds,
        "path_dependent": path_dependent,
        "completion_summaries": completion_summaries,
        "unlocking_completions": unlocks,
        "reverse_distributed": reverse_distributed,
        "classification": classification,
    }


def timing_decision(
    timing_metrics: Sequence[Mapping[str, Any]],
    fine: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    required = int(config["decision"]["minimum_consistent_seeds"])
    summaries: list[dict[str, Any]] = []
    for delay in config["timing"]["delays"]:
        for direction_key, direction in (("low_to_high", "low-to-high"), ("high_to_low", "high-to-low")):
            for condition, doses in config["timing"][direction_key].items():
                for dose in doses:
                    rows = [
                        row for row in timing_metrics
                        if str(row.get("direction")) == direction
                        and str(row.get("condition")) == str(condition)
                        and math.isclose(float(row.get("delay", -1.0)), float(delay))
                        and math.isclose(float(row.get("dose", -1.0)), float(dose))
                    ]
                    summaries.append(
                        _cell_summary(
                            rows,
                            config,
                            delay=float(delay),
                            direction=direction,
                            condition=str(condition),
                            dose=float(dose),
                        )
                    )
    latch_threshold = fine["directional_thresholds"]["latch-node"]["low-to-high"]
    timing_doses = _floats(config["timing"]["low_to_high"]["latch-node"])
    eligible = [dose for dose in timing_doses if latch_threshold is not None and dose >= float(latch_threshold)]
    test_dose = min(eligible) if eligible else None
    age_counts: list[dict[str, Any]] = []
    if test_dose is not None:
        for delay in config["timing"]["delays"]:
            matches = [
                row for row in summaries
                if row["direction"] == "low-to-high"
                and row["condition"] == "latch-node"
                and math.isclose(float(row["dose"]), float(test_dose))
                and math.isclose(float(row["delay"]), float(delay))
            ]
            if len(matches) != 1:
                raise ValueError("timing decision cell is missing or duplicated")
            age_counts.append({"delay": float(delay), "success_count": int(matches[0]["success_count"])})
    baseline = next((row["success_count"] for row in age_counts if math.isclose(float(row["delay"]), 0.0)), None)
    durable = bool(
        baseline is not None
        and int(baseline) >= required
        and all(
            int(row["success_count"]) >= required
            and int(baseline) - int(row["success_count"]) <= int(config["decision"]["timing_loss_seed_max"])
            for row in age_counts
        )
    )
    classification = "age-persistent-forward-latch" if durable else "age-dependent-or-unresolved-forward-latch"
    return {
        "task_id": "timing-decision",
        "cell_summaries": summaries,
        "registered_latch_test_dose": test_dose,
        "latch_success_by_age": age_counts,
        "durable": durable,
        "classification": classification,
    }


def analyze_switch_boundary(output: Path, final_status: str = "completed") -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    models = json.loads((output / "carrier-models.json").read_text(encoding="utf-8"))
    no_ops = list(read_jsonl(output / "no-op.jsonl"))
    row_sets = {name: list(read_jsonl(output / f"{name}.jsonl")) for name in (
        "fine-boundary",
        "single-node",
        "matched-controls",
        "pairwise-grid",
        "reverse-masks",
        "reverse-completion",
        "timing-probes",
    )}
    metric_sets = {
        name: _metrics(rows, no_ops, models, config)
        for name, rows in row_sets.items()
    }
    all_metrics = [row for name in metric_sets for row in metric_sets[name]]
    _write_jsonl(output / "transfer-metrics.jsonl", all_metrics)
    fine = fine_boundary_decision(metric_sets["fine-boundary"], config)
    specificity = specificity_decision(
        metric_sets["fine-boundary"],
        metric_sets["single-node"],
        metric_sets["matched-controls"],
        fine,
        config,
    )
    pairwise = pairwise_decision(
        metric_sets["pairwise-grid"],
        metric_sets["fine-boundary"],
        metric_sets["single-node"],
        config,
    )
    reverse = reverse_decision(
        metric_sets["reverse-masks"],
        metric_sets["reverse-completion"],
        metric_sets["fine-boundary"],
        fine,
        config,
    )
    timing = timing_decision(metric_sets["timing-probes"], fine, config)
    write_json(output / "fine-boundary-decision.json", fine)
    write_json(output / "specificity-decision.json", specificity)
    write_json(output / "pairwise-decision.json", pairwise)
    write_json(output / "reverse-decision.json", reverse)
    write_json(output / "timing-decision.json", timing)
    if specificity["node_specific"] and reverse["reverse_distributed"] and timing["durable"]:
        verdict = "durable-node-specific-asymmetric-latch-lead"
    elif specificity["node_specific"] and reverse["reverse_distributed"]:
        verdict = "contextual-node-specific-asymmetric-latch-lead"
    elif specificity["globally_fragile"]:
        verdict = "non-specific-fragile-basin-boundary-lead"
    elif pairwise["conditional_gate"]:
        verdict = "conditional-multinode-switch-gate-lead"
    elif specificity["node_specific"]:
        verdict = "node-specific-forward-switch-reverse-unresolved"
    else:
        verdict = "mixed-or-unresolved-switch-boundary"
    counts = {name: sum(1 for _ in read_jsonl(output / name)) for name in RECORD_FILES}
    completion = counts == EXPECTED_COUNTS
    decision = {
        "task_id": "switch-boundary-decision",
        "memory_task_id": TASK_ID,
        "minimum_completion_gate": completion,
        "fine_boundary": fine["classification"],
        "specificity": specificity["classification"],
        "pairwise": pairwise["classification"],
        "reverse": reverse["classification"],
        "timing": timing["classification"],
        "verdict": verdict,
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "decision.json", decision)
    analysis = {
        "task_id": "switch-boundary-analysis",
        "experiment_id": config["experiment_id"],
        "status": str(final_status),
        "record_counts": counts,
        "registered_condition_count": int(config["registered_condition_count"]),
        "minimum_completion_gate": completion,
        "verdict": verdict,
        "claim_boundary": config["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    report = f"""# Switch Boundary Mapping V1 Report

Status: **{final_status}**  
Verdict: **{verdict}**

## Registered decisions

- Fine boundary: **{fine['classification']}**; thresholds={json.dumps(fine['directional_thresholds'], sort_keys=True)}.
- Specificity: **{specificity['classification']}**; node-specific={specificity['node_specific']}; globally fragile={specificity['globally_fragile']}.
- Pairwise: **{pairwise['classification']}**; strong synergy cells={len(pairwise['synergy_cells'])}.
- Reverse: **{reverse['classification']}**; indispensable nodes={reverse['indispensable_nodes']}; path-dependent={reverse['path_dependent']}.
- Timing: **{timing['classification']}**; durable={timing['durable']}.

Exact registered records: {sum(counts.values())}/{config['registered_condition_count']}.

Controls and all intervention grids were frozen before post-intervention outcomes. Geometrically unavailable controls remain registered nulls and were not replaced.

Claim boundary: {config['claim_boundary']}
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class SwitchBoundaryCampaign:
    def __init__(
        self,
        config_path: Path,
        discrimination: Path,
        contingency: Path,
        atlas: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_switch_boundary_config(self.config_path)
        self.discrimination = discrimination.resolve()
        self.contingency = contingency.resolve()
        self.atlas = atlas.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("switch-boundary workers must lie between one and four")
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed switch-boundary campaign cannot be resumed")
        self.parent_gate = validate_switch_boundary_parents(
            self.config, self.discrimination, self.contingency, self.atlas, self.upstream
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
                "discrimination": str(self.discrimination),
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
                    raise ValueError(f"resumed switch-boundary registration differs for {key}")
            if prior.get("runtime", {}).get("container_image_id") != payload["runtime"].get("container_image_id"):
                raise ValueError("resumed switch-boundary image differs")
        write_json(path, payload)
        write_json(self.output / "parent-gate.json", {"task_id": "parent-gate", "pass": True, **self.parent_gate})
        write_json(
            self.output / "hypotheses.json",
            {
                "claim_class": "exploratory-in-silico-hypothesis-generation",
                "h1": "Node 7 is a selective low-to-high latch rather than one of many fragile directions.",
                "h2": "The high-to-low transition requires a distributed conjunctive state rewrite.",
                "h3": "The forward latch remains effective after long unstimulated release.",
                "h4": "Specific node-7 partner coordinates can gate or suppress the forward transition.",
                "v2r_is_design_parent_only": True,
                "fresh_outcome_adaptation_allowed": False,
                "threshold_relaxation_allowed": False,
            },
        )
        write_json(self.output / "carrier-models.json", _models_payload(self.discrimination))
        if not (self.output / "runtime-incidents.json").is_file():
            write_json(self.output / "runtime-incidents.json", {"incidents": []})
        for name in RECORD_FILES:
            if not (self.output / name).is_file():
                _write_jsonl(self.output / name, [])

    def run(self) -> int:
        self._register()
        self.ledger.start_heartbeat()
        try:
            fresh_args = [
                (
                    str(self.config_path),
                    str(self.contingency),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    int(seed),
                )
                for seed in self.config["fresh_seed_indices"]
            ]
            no_op_args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    int(seed),
                )
                for seed in self.config["fresh_seed_indices"]
            ]
            focused_args = [
                (
                    str(self.config_path),
                    str(self.discrimination),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    int(seed),
                )
                for seed in self.config["fresh_seed_indices"]
            ]
            self._require_budget("fresh-exposure")
            rows = _merge_shards(
                self.output,
                "fresh-exposure",
                _parallel(_fresh_exposure_worker, fresh_args, self.workers),
            )
            if len(rows) != EXPECTED_COUNTS["fresh-exposure.jsonl"]:
                raise ValueError("registered fresh-exposure count differs")
            self._require_budget("no-op")
            rows = _merge_shards(
                self.output,
                "no-op",
                _parallel(_no_op_worker, no_op_args, self.workers),
            )
            if len(rows) != EXPECTED_COUNTS["no-op.jsonl"]:
                raise ValueError("registered no-op count differs")
            self._require_budget("control-geometry-freeze")
            geometry, geometry_cpu = build_control_geometry(
                self.config, self.discrimination, self.atlas, self.upstream, self.output
            )
            write_json(self.output / "control-geometry.json", geometry)
            write_json(
                self.output / ".shards" / "static" / "control-geometry.json",
                {
                    "protocol_digest": digest(self.config),
                    "stage": "static",
                    "aggregate_cpu_seconds": geometry_cpu,
                    "aggregate_wall_seconds": 0.0,
                    "records": [],
                },
            )
            stages = (
                ("fine-boundary", _fine_boundary_worker),
                ("single-node", _single_node_worker),
                ("matched-controls", _matched_control_worker),
                ("pairwise-grid", _pairwise_worker),
                ("reverse-masks", _reverse_mask_worker),
                ("reverse-completion", _reverse_completion_worker),
                ("timing-probes", _timing_worker),
            )
            for stage, worker in stages:
                self._require_budget(stage)
                rows = _merge_shards(
                    self.output,
                    stage,
                    _parallel(worker, focused_args, self.workers),
                )
                expected = EXPECTED_COUNTS[f"{stage}.jsonl"]
                if len(rows) != expected:
                    raise ValueError(f"registered {stage} count differs: {len(rows)} != {expected}")
            self._state("analyzing", "analysis")
            self.ledger.close()
            analysis = analyze_switch_boundary(self.output, final_status="completed")
            if not analysis["minimum_completion_gate"]:
                raise ValueError("switch-boundary registered record set is incomplete")
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


def run_switch_boundary(
    config: Path,
    discrimination: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
    workers: int = 4,
) -> int:
    return SwitchBoundaryCampaign(
        config, discrimination, contingency, atlas, upstream, output, workers
    ).run()


def smoke_switch_boundary(
    config_path: Path,
    discrimination: Path,
    contingency: Path,
    atlas: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_switch_boundary_config(config_path)
    discrimination, contingency, atlas, upstream, output = (
        discrimination.resolve(), contingency.resolve(), atlas.resolve(), upstream.resolve(), output.resolve()
    )
    if output.exists():
        raise FileExistsError(f"switch-boundary smoke output exists: {output}")
    parents = validate_switch_boundary_parents(config, discrimination, contingency, atlas, upstream)
    output.mkdir(parents=True)
    model = _task_model(discrimination)
    history_config = _contingency_protocol(contingency)
    seed_index = int(config["fresh_seed_indices"][0])
    memory, backend, reconstructed = _task_resources(config, atlas, upstream, TASK_ID)
    base = _naive_start(atlas, TASK_ID)
    start, philox_seed = _perturb_start(base, memory, history_config, "switch-boundary", TASK_ID, seed_index)
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
    states = {
        arm: _payload_state(histories[arm]["checkpoints"]["12500"]["state"])
        for arm in ("low", "high")
    }
    fresh_refs = {
        arm: np.asarray(histories[arm]["checkpoints"]["12500"]["fingerprint"], dtype=float)
        for arm in ("low", "high")
    }
    no_ops: dict[str, dict[str, Any]] = {}
    no_op_cpu = no_op_wall = 0.0
    for arm in ("low", "high"):
        no_ops[arm], used_cpu, used_wall = _finish_record(
            backend, memory, reconstructed, config, states[arm], fresh_refs["high"], fresh_refs["low"]
        )
        no_op_cpu += used_cpu
        no_op_wall += used_wall
    refs = {arm: np.asarray(no_ops[arm]["fingerprint"], dtype=float) for arm in ("low", "high")}
    scale = np.asarray(model["scale"], dtype=float)
    probes = [
        _condition_state(states["low"], states["high"], "latch-node", 0.001, scale)[0],
        _condition_state(states["high"], states["low"], "full-expression", 1.0, scale)[0],
        state_from_node_fractions(states["low"], states["high"], {LATCH_NODE: 0.001, 1: 0.001}, scale)[0],
        state_from_node_fractions(states["high"], states["low"], {node: 1.0 for node in range(7)}, scale)[0],
    ]
    slots = matched_latch_control_slots(
        config, states["low"], states["high"], model, np.asarray(memory.bounds, dtype=float), seed_index, 0.001
    )
    available = [slot for slot in slots if bool(slot.get("available"))]
    if not available:
        raise ValueError("smoke found no feasible matched control")
    control = available[0]
    probes.append(
        State(
            states["low"].y + float(control["target_norm"]) * np.asarray(control["direction"], dtype=float) * scale,
            states["low"].w.copy(),
            states["low"].c.copy(),
            float(states["low"].t),
        )
    )
    intervention_cpu = intervention_wall = 0.0
    probe_valid: list[bool] = []
    for probe in probes:
        if probe is None:
            raise ValueError("smoke intervention is geometrically unavailable")
        result, used_cpu, used_wall = _finish_record(
            backend, memory, reconstructed, config, probe, refs["high"], refs["low"]
        )
        intervention_cpu += used_cpu
        intervention_wall += used_wall
        probe_valid.append(bool(result["valid"]))
    history_cpu = sum(float(row["cpu_seconds"]) for row in histories.values())
    history_wall = sum(float(row["wall_seconds"]) for row in histories.values())
    intervention_count = int(config["registered_condition_count"]) - EXPECTED_COUNTS["fresh-exposure.jsonl"] - EXPECTED_COUNTS["no-op.jsonl"]
    projected_cpu = float(config["projection_safety_factor"]) * (
        (history_cpu / 2.0) * EXPECTED_COUNTS["fresh-exposure.jsonl"]
        + (no_op_cpu / 2.0) * EXPECTED_COUNTS["no-op.jsonl"]
        + (intervention_cpu / len(probes)) * intervention_count
    )
    projected_wall = projected_cpu / float(config["max_workers"])
    all_valid = bool(
        all(bool(row["valid"]) for row in histories.values())
        and all(bool(row["valid"]) for row in no_ops.values())
        and all(probe_valid)
        and len(available) >= int(config["matched_controls"]["minimum_controls_per_seed"])
    )
    allowed = bool(
        all_valid
        and sum(EXPECTED_COUNTS.values()) == int(config["registered_condition_count"])
        and projected_cpu < float(config["soft_aggregate_cpu_seconds"])
        and projected_wall < float(config["soft_wall_seconds"])
    )
    result = {
        "target": config["experiment_id"],
        "pass": allowed,
        "production_launch_allowed": allowed,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "parent_manifests": {
            name: parents[name]["manifest_sha256"]
            for name in ("discrimination", "contingency", "atlas")
        },
        "worker_cap": int(config["max_workers"]),
        "fresh_seed_indices": list(config["fresh_seed_indices"]),
        "control_selection_frozen_before_post_intervention_outcomes": True,
        "biological_probe": {
            "memory_task_id": TASK_ID,
            "philox_seed": int(philox_seed),
            "history_valid": all(bool(row["valid"]) for row in histories.values()),
            "no_op_valid": all(bool(row["valid"]) for row in no_ops.values()),
            "intervention_valid": all(probe_valid),
            "available_control_count": len(available),
        },
        "projection": {
            "registered_condition_count": int(config["registered_condition_count"]),
            "record_counts": EXPECTED_COUNTS,
            "worst_case_aggregate_cpu_seconds": projected_cpu,
            "worst_case_active_wall_seconds_at_four_workers": projected_wall,
            "safety_factor": float(config["projection_safety_factor"]),
            "measured_history_cpu_seconds": history_cpu,
            "measured_history_wall_seconds": history_wall,
            "measured_no_op_cpu_seconds": no_op_cpu,
            "measured_no_op_wall_seconds": no_op_wall,
            "measured_intervention_cpu_seconds": intervention_cpu,
            "measured_intervention_wall_seconds": intervention_wall,
        },
        "deterministic_batch_plan": "stage-by-seed shards",
    }
    write_json(output / "smoke.json", result)
    return result


def switch_boundary_status(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result: dict[str, Any] = {
        "output": str(output),
        "sealed": (output / "SHA256SUMS").is_file(),
    }
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "control-geometry",
        "fine-boundary-decision",
        "specificity-decision",
        "pairwise-decision",
        "reverse-decision",
        "timing-decision",
        "decision",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    result["record_counts"] = {
        name: sum(1 for _ in read_jsonl(output / name))
        for name in RECORD_FILES
    }
    return result
