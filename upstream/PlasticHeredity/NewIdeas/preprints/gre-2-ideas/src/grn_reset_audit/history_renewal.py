"""History-specific carrier and renewal audit (V2).

The V2 campaign replaces scalar ratios with held-out multivariate fingerprints,
uses common-random-number damage seeds, and records donor ancestry explicitly.
An engineered local mark is attempted only after an immediate carrier passes
and the corrected native lineage fails.
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


FINGERPRINT_ARMS = ("naive", "trained_no_reset", "combined_reset", "control_only")
AUDIT_ARMS = (
    "full_combined",
    "control_donor",
    "selected_transplant",
    "selected_ablation",
    "matched_random",
    "paired_memory",
    "content_inversion",
    "naive",
)
NATIVE_ARMS = (
    "adult_rewrite",
    "passive_no_rewrite",
    "erase_g2",
    "rescue_g3",
    "matched_random",
    "paired_donor",
    "content_inversion",
    "control_donor",
)
MARK_VALIDATION_ARMS = (
    "intact",
    "writer_off",
    "renewal_off",
    "reader_off",
    "erase_g2",
    "rescue_g3",
    "inverted_founder",
    "paired_donor",
    "zero_donor",
)


def load_history_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "2.0":
        raise ValueError("unsupported history-renewal schema")
    if config.get("experiment_kind") != "history-carrier-renewal":
        raise ValueError("not a history-carrier-renewal protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("history-renewal protocol does not pin upstream HEAD")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("history-renewal protocol does not pin the release generator")
    if int(config.get("max_workers", 0)) != 2:
        raise ValueError("history-renewal protocol must cap workers at two")
    if not (
        0 < float(config["soft_wall_seconds"])
        < float(config["terminate_wall_seconds"])
        < float(config["hard_wall_seconds"])
        <= 14400.0
    ):
        raise ValueError("history-renewal active-wall contract is invalid")
    if not (
        0 < float(config["soft_aggregate_cpu_seconds"])
        < float(config["hard_aggregate_cpu_seconds"])
        <= 28800.0
    ):
        raise ValueError("history-renewal CPU contract is invalid")
    expected = {"delta_t": 0.01, "phase_duration": 2500.0, "pulse_count": 5}
    for key, value in expected.items():
        if not math.isclose(float(config[key]), value):
            raise ValueError(f"historical setting differs for {key}")
    candidates = list(config.get("candidates", []))
    task_ids = [str(row["task_id"]) for row in candidates]
    if len(candidates) != 8 or len(set(task_ids)) != 8:
        raise ValueError("history-renewal requires eight unique frozen candidates")
    if [int(row["model_id"]) for row in candidates] != [10, 10, 16, 16, 37, 37, 204, 204]:
        raise ValueError("frozen candidate/model order changed")
    for row in candidates:
        selected = [int(value) for value in row["selected_nodes"]]
        random_nodes = [int(value) for value in row["random_nodes"]]
        if not selected or len(selected) > 5 or len(selected) != len(random_nodes):
            raise ValueError(f"invalid compact node sets for {row['task_id']}")
        if len(set(selected)) != len(selected) or len(set(random_nodes)) != len(random_nodes):
            raise ValueError(f"duplicate node in frozen nomination {row['task_id']}")
        if row["paired_task_id"] not in task_ids:
            raise ValueError(f"missing paired memory for {row['task_id']}")
    if list(config["fingerprint_probes"]) != [
        "no_input",
        "selected_control",
        "cs_selected_control",
        "opposite_selected_control",
        "cs_opposite_selected_control",
    ]:
        raise ValueError("primary fingerprint differs from the preregistration")
    if int(config["audit_seeds"]) != 8 or int(config["lineage_generations"]) != 8:
        raise ValueError("seed or generation count differs from the preregistration")
    return config


def _seed(config: Mapping[str, Any], *parts: object) -> int:
    payload = "|".join([str(config["experiment_seed"]), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")


def transform_fingerprint(values: Sequence[float]) -> np.ndarray:
    values_array = np.asarray(values, dtype=float)
    return np.arcsinh(values_array)


def vector_rms(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(array * array))) if array.size else 0.0


def cosine_alignment(left: Sequence[float], right: Sequence[float]) -> float | None:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    denominator = float(np.linalg.norm(left_array) * np.linalg.norm(right_array))
    if denominator <= 1e-12 or not np.isfinite(denominator):
        return None
    return float(np.dot(left_array, right_array) / denominator)


def project_fingerprint(
    values: Sequence[float], baseline: Sequence[float], direction: Sequence[float]
) -> float | None:
    values_array = np.asarray(values, dtype=float)
    baseline_array = np.asarray(baseline, dtype=float)
    direction_array = np.asarray(direction, dtype=float)
    if values_array.shape != baseline_array.shape or values_array.shape != direction_array.shape:
        raise ValueError("fingerprint projection shapes differ")
    denominator = float(np.dot(direction_array, direction_array))
    if denominator <= 1e-12 or not np.isfinite(denominator):
        return None
    value = float(np.dot(values_array - baseline_array, direction_array) / denominator)
    return value if np.isfinite(value) else None


def reference_record(
    task_id: str,
    probes: Mapping[tuple[str, str, str], Mapping[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    names = list(config["fingerprint_probes"])
    raw: dict[str, list[float]] = {}
    valid = True
    for arm in FINGERPRINT_ARMS:
        rows = [probes.get((task_id, arm, name)) for name in names]
        if any(row is None or not bool(row.get("valid", False)) for row in rows):
            valid = False
            raw[arm] = []
        else:
            raw[arm] = [float(row["learned_margin"]) for row in rows if row is not None]
    transformed = {
        arm: transform_fingerprint(values).tolist() if len(values) == len(names) else []
        for arm, values in raw.items()
    }
    if valid:
        trained = np.asarray(transformed["trained_no_reset"]) - np.asarray(transformed["naive"])
        reset = np.asarray(transformed["combined_reset"]) - np.asarray(transformed["control_only"])
        trained_rms = vector_rms(trained)
        reset_rms = vector_rms(reset)
        cosine = cosine_alignment(trained, reset)
    else:
        trained = reset = np.asarray([], dtype=float)
        trained_rms = reset_rms = 0.0
        cosine = None
    eligible = bool(
        valid
        and trained_rms >= float(config["fingerprint_min_rms"])
        and reset_rms >= float(config["fingerprint_min_rms"])
        and cosine is not None
        and cosine >= float(config["fingerprint_min_cosine"])
    )
    return {
        "task_id": f"fingerprint-reference|{task_id}",
        "memory_task_id": task_id,
        "probe_names": names,
        "raw_fingerprints": raw,
        "transformed_fingerprints": transformed,
        "trained_direction": trained,
        "reset_history_direction": reset,
        "trained_rms": trained_rms,
        "reset_history_rms": reset_rms,
        "cosine_alignment": cosine,
        "valid": valid,
        "eligible": eligible,
    }


def _probe_specs(memory: Any, calibration: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected = int(calibration["selected_action_index"])
    control, bound_index, selected_value = memory.action(selected)
    opposite = float(memory.bounds[control, 1 - int(bound_index)])
    cs_value = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
    return [
        {"name": "no_input", "stimuli": None},
        {"name": "selected_control", "stimuli": {int(control): float(selected_value)}},
        {
            "name": "cs_selected_control",
            "stimuli": {int(memory.cs_id): cs_value, int(control): float(selected_value)},
        },
        {"name": "opposite_selected_control", "stimuli": {int(control): opposite}},
        {
            "name": "cs_opposite_selected_control",
            "stimuli": {int(memory.cs_id): cs_value, int(control): opposite},
        },
    ]


def _develop_and_fingerprint(
    backend: JaxBackend,
    memory: Any,
    calibration: Mapping[str, Any],
    start: State,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    duration = float(config["phase_duration"])
    samples = int(config["trajectory_samples"])
    pulses = int(config["pulse_count"])
    adult = backend.run_unstimulated(start, duration, memory.key.response_id, samples)
    probe_rows: list[dict[str, Any]] = []
    phases = [adult]
    for spec in _probe_specs(memory, calibration):
        phase = backend.run_phase(
            adult.state.copy(), duration, spec["stimuli"], memory.key.response_id, samples, pulses
        )
        phases.append(phase)
        mean_response = float(phase.mean_y[memory.key.response_id])
        probe_rows.append(
            {
                "probe": spec["name"],
                "stimuli": spec["stimuli"],
                "mean_response": mean_response,
                "learned_margin": learned_margin(memory, mean_response),
                "valid": bool(phase.valid),
                "response_range": float(np.ptp(phase.response_trajectory)),
            }
        )
    raw = [float(row["learned_margin"]) for row in probe_rows]
    valid = bool(all(phase.valid for phase in phases) and all(np.isfinite(raw)))
    return {
        "adult_state": state_payload(adult.state),
        "raw_fingerprint": raw,
        "fingerprint": transform_fingerprint(raw),
        "probes": probe_rows,
        "valid": valid,
        "cpu_seconds": float(sum(phase.cpu_seconds for phase in phases)),
        "wall_seconds": float(sum(phase.wall_seconds for phase in phases)),
    }


def damage_noise(
    config: Mapping[str, Any], task_id: str, seed_index: int, generation: int, node_count: int
) -> np.ndarray:
    rng = np.random.Generator(
        np.random.Philox(_seed(config, "damage", task_id, seed_index, generation))
    )
    return rng.normal(0.0, float(config["damage_noise_sigma"]), int(node_count))


def damaged_copy(
    naive: np.ndarray,
    donor: np.ndarray,
    bounds: np.ndarray,
    retention: float,
    epsilon: np.ndarray,
    nodes: Sequence[int] | None = None,
) -> np.ndarray:
    naive_array = np.asarray(naive, dtype=float)
    donor_array = np.asarray(donor, dtype=float)
    epsilon_array = np.asarray(epsilon, dtype=float)
    if naive_array.shape != donor_array.shape or naive_array.shape != epsilon_array.shape:
        raise ValueError("damage-copy shapes differ")
    result = naive_array.copy()
    indices = np.arange(len(result), dtype=int) if nodes is None else np.asarray(nodes, dtype=int)
    result[indices] = naive_array[indices] + float(retention) * (
        donor_array[indices] - naive_array[indices]
    ) * (1.0 + epsilon_array[indices])
    return np.clip(result, np.asarray(bounds)[:, 0], np.asarray(bounds)[:, 1])


def content_inversion(control: np.ndarray, combined: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    control_array = np.asarray(control, dtype=float)
    combined_array = np.asarray(combined, dtype=float)
    inverted = control_array - (combined_array - control_array)
    return np.clip(inverted, np.asarray(bounds)[:, 0], np.asarray(bounds)[:, 1])


def _history_maps(atlas: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, dict[str, Any]]]:
    histories = {
        (row["memory_task_id"], row["arm"]): row
        for row in read_jsonl(atlas / "histories.jsonl")
    }
    calibration = {
        row["memory_task_id"]: row for row in read_jsonl(atlas / "calibration.jsonl")
    }
    return histories, calibration


def _checkpoint(
    histories: Mapping[tuple[str, str], Mapping[str, Any]], task_id: str, arm: str, checkpoint: float
) -> State:
    key = f"{float(checkpoint):g}"
    state = state_from_payload(histories[(task_id, arm)]["checkpoints"][key]["state"])
    if state is None:
        raise ValueError(f"invalid atlas checkpoint for {task_id}/{arm}")
    return state


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
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


def _all_shard_cpu(output: Path) -> float:
    total = 0.0
    shard_root = output / ".shards"
    for path in sorted(shard_root.rglob("*.json")) if shard_root.is_dir() else []:
        try:
            total += float(json.loads(path.read_text(encoding="utf-8")).get("aggregate_cpu_seconds", 0.0))
        except (OSError, ValueError, TypeError):
            continue
    return total


def _parallel(worker: Any, args: list[tuple[Any, ...]], workers: int) -> list[dict[str, Any]]:
    if workers == 1:
        return [worker(arg) for arg in args]
    context = multiprocessing.get_context("spawn")
    results: dict[str, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        futures = {pool.submit(worker, arg): str(arg[-1]) for arg in args}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return [results[str(arg[-1])] for arg in args]


def _identity_history_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    """Pickle-safe deterministic sentinel for the worker-count equivalence test."""

    return {"key": str(args[-1]), "payload": list(args[:-1])}


def _merge(output: Path, name: str, shards: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    records = [row for shard in shards for row in shard.get("records", [])]
    ids = [str(row["task_id"]) for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate task IDs in {name}")
    _write_jsonl(output / f"{name}.jsonl", records)
    return records


def _candidate_map(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["task_id"]): dict(row) for row in config["candidates"]}


def _audit_model_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        output_path,
        model_id,
        task_ids,
        profile,
        shard_key,
    ) = args
    config = load_history_config(Path(config_path))
    atlas = Path(atlas_path)
    upstream = Path(upstream_path)
    output = Path(output_path)
    shard = output / ".shards" / "carrier-audit" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        existing = json.loads(shard.read_text(encoding="utf-8"))
        if existing.get("protocol_digest") == protocol_digest and existing.get("profile") == profile:
            return existing
    histories, calibrations = _history_maps(atlas)
    references = {
        row["memory_task_id"]: row for row in read_jsonl(output / "fingerprint-reference.jsonl")
    }
    candidates = _candidate_map(config)
    backend = JaxBackend(upstream, int(model_id), delta_t=float(config["delta_t"]))
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for task_id in task_ids:
        reference = references[task_id]
        if not reference["eligible"]:
            continue
        candidate = candidates[task_id]
        released = load_released_task(upstream, task_id)
        memory = load_memory(released.memory_path, released.key)
        calibration = calibrations[task_id]
        checkpoint = float(config["parent_checkpoint"])
        naive = _checkpoint(histories, task_id, "naive", checkpoint)
        combined = _checkpoint(histories, task_id, "combined_reset", checkpoint)
        control = _checkpoint(histories, task_id, "control_only", checkpoint)
        paired = _checkpoint(
            histories, str(candidate["paired_task_id"]), "combined_reset", checkpoint
        )
        selected = [int(value) for value in candidate["selected_nodes"]]
        random_nodes = [int(value) for value in candidate["random_nodes"]]
        selected_donor = control.y.copy()
        selected_donor[selected] = combined.y[selected]
        ablated_donor = combined.y.copy()
        ablated_donor[selected] = control.y[selected]
        random_donor = control.y.copy()
        random_donor[random_nodes] = combined.y[random_nodes]
        paired_donor = control.y.copy()
        paired_donor[selected] = paired.y[selected]
        donors: dict[str, np.ndarray | None] = {
            "full_combined": combined.y,
            "control_donor": control.y,
            "selected_transplant": selected_donor,
            "selected_ablation": ablated_donor,
            "matched_random": random_donor,
            "paired_memory": paired_donor,
            "content_inversion": content_inversion(control.y, combined.y, memory.bounds),
            "naive": None,
        }
        for seed_index in range(int(config["audit_seeds"])):
            epsilon = damage_noise(config, task_id, seed_index, 0, memory.node_count)
            seed_value = _seed(config, "damage", task_id, seed_index, 0)
            seed_rows: list[dict[str, Any]] = []
            for arm in AUDIT_ARMS:
                donor = donors[arm]
                y = (
                    naive.y.copy()
                    if donor is None
                    else damaged_copy(
                        naive.y,
                        donor,
                        memory.bounds,
                        float(config["damage_retention"]),
                        epsilon,
                    )
                )
                start = State(y, naive.w.copy(), naive.c.copy(), naive.t)
                result = _develop_and_fingerprint(backend, memory, calibration, start, config)
                total_cpu += float(result["cpu_seconds"])
                row = {
                    "task_id": f"carrier-audit|{task_id}|{seed_index}|{arm}",
                    "memory_task_id": task_id,
                    "model_id": int(model_id),
                    "seed_index": seed_index,
                    "philox_seed": seed_value,
                    "generation": 0,
                    "condition": arm,
                    "selected_nodes": selected,
                    "random_nodes": random_nodes,
                    "donor_ancestry": "none" if donor is None else arm,
                    "damage_noise": epsilon,
                    **result,
                }
                seed_rows.append(row)
            baseline = next(row for row in seed_rows if row["condition"] == "control_donor")
            direction = reference["reset_history_direction"]
            for row in seed_rows:
                row["projection"] = (
                    project_fingerprint(row["fingerprint"], baseline["fingerprint"], direction)
                    if row["valid"] and baseline["valid"]
                    else None
                )
            records.extend(seed_rows)
    payload = {
        "protocol_digest": protocol_digest,
        "profile": profile,
        "model_id": int(model_id),
        "tasks": list(task_ids),
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def immediate_carrier_decision(
    records: Sequence[Mapping[str, Any]],
    references: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    profile: str,
) -> dict[str, Any]:
    candidates = _candidate_map(config)
    rows_by_key = {
        (str(row["memory_task_id"]), int(row["seed_index"]), str(row["condition"])): row
        for row in records
    }
    reference_map = {str(row["memory_task_id"]): row for row in references}
    summaries: list[dict[str, Any]] = []
    for task_id, candidate in candidates.items():
        reference = reference_map[task_id]
        seed_metrics: list[dict[str, Any]] = []
        if reference["eligible"]:
            for seed_index in range(int(config["audit_seeds"])):
                arm_rows = {
                    arm: rows_by_key.get((task_id, seed_index, arm)) for arm in AUDIT_ARMS
                }
                joint_valid = bool(
                    all(row is not None and bool(row.get("valid", False)) for row in arm_rows.values())
                    and all(row.get("projection") is not None for row in arm_rows.values() if row is not None)
                )
                if not joint_valid:
                    seed_metrics.append({"seed_index": seed_index, "valid": False})
                    continue
                projection = {arm: float(arm_rows[arm]["projection"]) for arm in AUDIT_ARMS}
                benchmark = projection["full_combined"]
                denominator = max(abs(benchmark), 1e-12)
                seed_metrics.append(
                    {
                        "seed_index": seed_index,
                        "valid": True,
                        "correct_direction": benchmark > 0.0,
                        "benchmark_projection": benchmark,
                        "selected_transfer_fraction": projection["selected_transplant"] / denominator,
                        "ablation_removal_fraction": (benchmark - projection["selected_ablation"]) / denominator,
                        "matched_random_fraction": abs(projection["matched_random"]) / denominator,
                        "paired_memory_fraction": abs(projection["paired_memory"]) / denominator,
                        "content_inversion_fraction": abs(projection["content_inversion"]) / denominator,
                        "naive_fraction": abs(projection["naive"]) / denominator,
                    }
                )
        valid = [row for row in seed_metrics if row.get("valid")]

        def median(key: str, default: float = 0.0) -> float:
            return float(np.median([float(row[key]) for row in valid])) if valid else default

        transfer_values = [float(row["selected_transfer_fraction"]) for row in valid]
        metrics = {
            "valid_seed_count": len(valid),
            "correct_direction_seed_count": sum(bool(row["correct_direction"]) for row in valid),
            "benchmark_projection": median("benchmark_projection"),
            "selected_transfer_fraction": median("selected_transfer_fraction"),
            "selected_transfer_lower_quartile": float(np.quantile(transfer_values, 0.25)) if transfer_values else 0.0,
            "ablation_removal_fraction": median("ablation_removal_fraction"),
            "matched_random_fraction": median("matched_random_fraction", math.inf),
            "paired_memory_fraction": median("paired_memory_fraction", math.inf),
            "content_inversion_fraction": median("content_inversion_fraction", math.inf),
            "naive_fraction": median("naive_fraction", math.inf),
        }
        passed = bool(
            reference["eligible"]
            and metrics["valid_seed_count"] >= int(config["minimum_consistent_seeds"])
            and metrics["correct_direction_seed_count"] >= int(config["minimum_consistent_seeds"])
            and metrics["benchmark_projection"] >= float(config["audit_benchmark_min"])
            and metrics["selected_transfer_fraction"] >= float(config["audit_transfer_fraction"])
            and metrics["ablation_removal_fraction"] >= float(config["audit_ablation_fraction"])
            and max(
                metrics["matched_random_fraction"],
                metrics["paired_memory_fraction"],
                metrics["content_inversion_fraction"],
                metrics["naive_fraction"],
            )
            <= float(config["audit_control_max_fraction"])
        )
        summaries.append(
            {
                "memory_task_id": task_id,
                "model_id": int(candidate["model_id"]),
                "selected_nodes": candidate["selected_nodes"],
                "eligible": bool(reference["eligible"]),
                "pass": passed,
                "metrics": metrics,
                "seed_metrics": seed_metrics,
            }
        )
    ranked = sorted(
        (row for row in summaries if row["pass"]),
        key=lambda row: (
            len(row["selected_nodes"]),
            -float(row["metrics"]["selected_transfer_lower_quartile"]),
            str(row["memory_task_id"]),
        ),
    )
    maximum = int(
        config["max_advanced_candidates_full"]
        if profile == "full"
        else config["max_advanced_candidates_lite"]
    )
    advanced: list[dict[str, Any]] = []
    used_models: set[int] = set()
    for row in ranked:
        if int(row["model_id"]) not in used_models:
            advanced.append(row)
            used_models.add(int(row["model_id"]))
        if len(advanced) == maximum:
            break
    for row in ranked:
        if len(advanced) == maximum:
            break
        if row not in advanced:
            advanced.append(row)
    return {
        "task_id": "carrier-audit-decision",
        "profile": profile,
        "eligible_count": sum(bool(row["eligible"]) for row in summaries),
        "pass_count": len(ranked),
        "candidate_summaries": summaries,
        "ranking": [row["memory_task_id"] for row in ranked],
        "advanced_candidates": [row["memory_task_id"] for row in advanced],
        "pass": bool(ranked),
    }


def native_next_donor(
    arm: str,
    founder: np.ndarray,
    post_copy: np.ndarray,
    adult: np.ndarray,
    generation: int,
) -> tuple[np.ndarray, str]:
    """Return the true next donor; renewal-off/passive never gets the founder back."""

    if arm == "passive_no_rewrite":
        return np.asarray(post_copy, dtype=float).copy(), f"post-copy-g{generation}"
    return np.asarray(adult, dtype=float).copy(), f"adult-g{generation}"


def _native_candidate_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        output_path,
        model_id,
        task_id,
        profile,
        shard_key,
    ) = args
    config = load_history_config(Path(config_path))
    atlas = Path(atlas_path)
    upstream = Path(upstream_path)
    output = Path(output_path)
    shard = output / ".shards" / "natural-lineage" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        existing = json.loads(shard.read_text(encoding="utf-8"))
        if existing.get("protocol_digest") == protocol_digest and existing.get("profile") == profile:
            return existing
    histories, calibrations = _history_maps(atlas)
    references = {
        row["memory_task_id"]: row for row in read_jsonl(output / "fingerprint-reference.jsonl")
    }
    candidate = _candidate_map(config)[task_id]
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, int(model_id), delta_t=float(config["delta_t"]))
    calibration = calibrations[task_id]
    checkpoint = float(config["parent_checkpoint"])
    naive = _checkpoint(histories, task_id, "naive", checkpoint)
    combined = _checkpoint(histories, task_id, "combined_reset", checkpoint)
    control = _checkpoint(histories, task_id, "control_only", checkpoint)
    paired = _checkpoint(histories, str(candidate["paired_task_id"]), "combined_reset", checkpoint)
    selected = [int(value) for value in candidate["selected_nodes"]]
    random_nodes = [int(value) for value in candidate["random_nodes"]]
    matched_founder = control.y.copy()
    matched_founder[random_nodes] = combined.y[random_nodes]
    paired_founder = control.y.copy()
    paired_founder[selected] = paired.y[selected]
    founders = {
        "adult_rewrite": combined.y.copy(),
        "passive_no_rewrite": combined.y.copy(),
        "erase_g2": combined.y.copy(),
        "rescue_g3": combined.y.copy(),
        "matched_random": matched_founder,
        "paired_donor": paired_founder,
        "content_inversion": content_inversion(control.y, combined.y, memory.bounds),
        "control_donor": control.y.copy(),
    }
    arm_nodes = {arm: selected for arm in NATIVE_ARMS}
    arm_nodes["matched_random"] = random_nodes
    checkpoints = {int(value) for value in config["lineage_checkpoints"]}
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for seed_index in range(int(config["audit_seeds"])):
        for arm in NATIVE_ARMS:
            founder = founders[arm].copy()
            donor = founder.copy()
            donor_source = "founder"
            parent_record_id: str | None = None
            for generation in range(1, int(config["lineage_generations"]) + 1):
                epsilon = damage_noise(config, task_id, seed_index, generation, memory.node_count)
                effective_donor: np.ndarray | None = donor
                effective_source = donor_source
                if arm in {"erase_g2", "rescue_g3"} and generation == 2:
                    effective_donor = None
                    effective_source = "explicit-erase"
                elif arm == "rescue_g3" and generation == 3:
                    effective_donor = founder
                    effective_source = "explicit-founder-rescue"
                if effective_donor is None:
                    y = naive.y.copy()
                else:
                    y = damaged_copy(
                        naive.y,
                        effective_donor,
                        memory.bounds,
                        float(config["damage_retention"]),
                        epsilon,
                        arm_nodes[arm],
                    )
                start = State(y, naive.w.copy(), naive.c.copy(), naive.t)
                if generation in checkpoints:
                    result = _develop_and_fingerprint(backend, memory, calibration, start, config)
                    adult = state_from_payload(result["adult_state"])
                    if adult is None:
                        adult = start.copy()
                    cpu_seconds = float(result["cpu_seconds"])
                    wall_seconds = float(result["wall_seconds"])
                    raw_fingerprint: Any = result["raw_fingerprint"]
                    fingerprint: Any = result["fingerprint"]
                    probes: Any = result["probes"]
                    valid = bool(result["valid"])
                else:
                    phase = backend.run_unstimulated(
                        start,
                        float(config["phase_duration"]),
                        memory.key.response_id,
                        int(config["trajectory_samples"]),
                    )
                    adult = phase.state
                    cpu_seconds = float(phase.cpu_seconds)
                    wall_seconds = float(phase.wall_seconds)
                    raw_fingerprint = fingerprint = probes = None
                    valid = bool(phase.valid)
                total_cpu += cpu_seconds
                record_id = f"natural-lineage|{task_id}|{seed_index}|{arm}|g{generation}"
                record = {
                    "task_id": record_id,
                    "memory_task_id": task_id,
                    "model_id": int(model_id),
                    "seed_index": seed_index,
                    "philox_seed": _seed(config, "damage", task_id, seed_index, generation),
                    "generation": generation,
                    "condition": arm,
                    "nodes": arm_nodes[arm],
                    "donor_source": effective_source,
                    "donor_parent_record_id": parent_record_id,
                    "founder_reused": effective_source in {"founder", "explicit-founder-rescue"},
                    "damage_noise": epsilon,
                    "post_copy_y": y,
                    "adult_state": state_payload(adult),
                    "raw_fingerprint": raw_fingerprint,
                    "fingerprint": fingerprint,
                    "probes": probes,
                    "projection": None,
                    "valid": valid,
                    "cpu_seconds": cpu_seconds,
                    "wall_seconds": wall_seconds,
                }
                records.append(record)
                donor, donor_source = native_next_donor(
                    arm, founder, y, adult.y, generation
                )
                parent_record_id = record_id
    by_key = {
        (int(row["seed_index"]), int(row["generation"]), str(row["condition"])): row
        for row in records
    }
    direction = references[task_id]["reset_history_direction"]
    for seed_index in range(int(config["audit_seeds"])):
        for generation in checkpoints:
            baseline = by_key[(seed_index, generation, "control_donor")]
            for arm in NATIVE_ARMS:
                row = by_key[(seed_index, generation, arm)]
                row["projection"] = (
                    project_fingerprint(row["fingerprint"], baseline["fingerprint"], direction)
                    if row["valid"] and baseline["valid"]
                    else None
                )
    payload = {
        "protocol_digest": protocol_digest,
        "profile": profile,
        "model_id": int(model_id),
        "memory_task_id": task_id,
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def natural_lineage_decision(
    records: Sequence[Mapping[str, Any]],
    advanced: Sequence[str],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    by_key = {
        (
            str(row["memory_task_id"]),
            int(row["seed_index"]),
            int(row["generation"]),
            str(row["condition"]),
        ): row
        for row in records
    }
    summaries: list[dict[str, Any]] = []
    for task_id in advanced:
        endpoint_summaries: list[dict[str, Any]] = []
        for generation in (4, 8):
            seed_metrics: list[dict[str, Any]] = []
            for seed_index in range(int(config["audit_seeds"])):
                arm_rows = {
                    arm: by_key.get((task_id, seed_index, generation, arm)) for arm in NATIVE_ARMS
                }
                valid = bool(
                    all(row is not None and bool(row.get("valid", False)) for row in arm_rows.values())
                    and all(row.get("projection") is not None for row in arm_rows.values() if row is not None)
                )
                if not valid:
                    seed_metrics.append({"seed_index": seed_index, "valid": False})
                    continue
                projection = {arm: float(arm_rows[arm]["projection"]) for arm in NATIVE_ARMS}
                intact = projection["adult_rewrite"]
                denominator = max(abs(intact), 1e-12)
                erase = (intact - projection["erase_g2"]) / denominator
                rescue = projection["rescue_g3"] / denominator
                seed_metrics.append(
                    {
                        "seed_index": seed_index,
                        "valid": True,
                        "consistent": bool(
                            intact > 0.0
                            and intact > projection["passive_no_rewrite"]
                            and projection["erase_g2"] < intact
                            and projection["rescue_g3"] > projection["erase_g2"]
                        ),
                        "projection": intact,
                        "rewrite_advantage": intact - projection["passive_no_rewrite"],
                        "erase_removal_fraction": erase,
                        "rescue_fraction": rescue,
                        "matched_random_fraction": abs(projection["matched_random"]) / denominator,
                        "paired_donor_fraction": abs(projection["paired_donor"]) / denominator,
                        "content_inversion_fraction": abs(projection["content_inversion"]) / denominator,
                    }
                )
            valid_rows = [row for row in seed_metrics if row.get("valid")]

            def med(key: str, default: float = 0.0) -> float:
                return float(np.median([float(row[key]) for row in valid_rows])) if valid_rows else default

            metrics = {
                "valid_seed_count": len(valid_rows),
                "consistent_seed_count": sum(bool(row["consistent"]) for row in valid_rows),
                "projection": med("projection"),
                "rewrite_advantage": med("rewrite_advantage"),
                "erase_removal_fraction": med("erase_removal_fraction"),
                "rescue_fraction": med("rescue_fraction"),
                "matched_random_fraction": med("matched_random_fraction", math.inf),
                "paired_donor_fraction": med("paired_donor_fraction", math.inf),
                "content_inversion_fraction": med("content_inversion_fraction", math.inf),
            }
            passed = bool(
                metrics["valid_seed_count"] >= int(config["minimum_consistent_seeds"])
                and metrics["consistent_seed_count"] >= int(config["minimum_consistent_seeds"])
                and metrics["projection"] >= float(config["natural_projection_min"])
                and metrics["rewrite_advantage"] >= float(config["natural_rewrite_advantage_min"])
                and metrics["erase_removal_fraction"] >= float(config["natural_erase_fraction"])
                and metrics["rescue_fraction"] >= float(config["natural_rescue_fraction"])
                and max(
                    metrics["matched_random_fraction"],
                    metrics["paired_donor_fraction"],
                    metrics["content_inversion_fraction"],
                )
                <= float(config["natural_content_max_fraction"])
            )
            endpoint_summaries.append(
                {
                    "generation": generation,
                    "pass": passed,
                    "metrics": metrics,
                    "seed_metrics": seed_metrics,
                }
            )
        summaries.append(
            {
                "memory_task_id": task_id,
                "model_id": int(task_id.split("-")[0]),
                "pass": all(row["pass"] for row in endpoint_summaries),
                "endpoints": endpoint_summaries,
            }
        )
    passes = [row for row in summaries if row["pass"]]
    represented_models = sorted({int(row["model_id"]) for row in passes})
    label = (
        "replicated-native-lead"
        if len(passes) >= 2 and len(represented_models) >= 2
        else "single-model-candidate"
        if passes
        else "no-native-renewal"
    )
    return {
        "task_id": "natural-lineage-decision",
        "candidate_summaries": summaries,
        "pass_count": len(passes),
        "passing_candidates": [row["memory_task_id"] for row in passes],
        "represented_models": represented_models,
        "label": label,
        "pass": bool(passes),
    }


def local_mark_scale(
    bounds: np.ndarray, control: np.ndarray, combined: np.ndarray, nodes: Sequence[int]
) -> np.ndarray:
    indices = np.asarray(nodes, dtype=int)
    width = np.abs(np.asarray(bounds, dtype=float)[indices, 1] - np.asarray(bounds, dtype=float)[indices, 0])
    difference = np.abs(np.asarray(combined, dtype=float)[indices] - np.asarray(control, dtype=float)[indices])
    return np.maximum.reduce([difference, 0.01 * width, np.full_like(difference, 1e-8)])


def encode_local_mark(
    values: np.ndarray, control: np.ndarray, scale: np.ndarray, nodes: Sequence[int]
) -> np.ndarray:
    indices = np.asarray(nodes, dtype=int)
    return np.clip((np.asarray(values, dtype=float)[indices] - np.asarray(control, dtype=float)[indices]) / scale, -1.0, 1.0)


def mark_randomness(
    config: Mapping[str, Any], task_id: str, seed_index: int, generation: int, size: int
) -> tuple[np.ndarray, np.ndarray, int]:
    seed_value = _seed(config, "mark-copy", task_id, seed_index, generation)
    rng = np.random.Generator(np.random.Philox(seed_value))
    keep = rng.random(int(size)) >= float(config["mark_copy_dropout"])
    noise = rng.normal(0.0, float(config["mark_copy_sigma"]), int(size))
    return keep, noise, seed_value


def copy_local_mark(
    mark: np.ndarray, keep: np.ndarray, noise: np.ndarray, dilution: float
) -> np.ndarray:
    arrays = [np.asarray(value) for value in (mark, keep, noise)]
    if arrays[0].shape != arrays[1].shape or arrays[0].shape != arrays[2].shape:
        raise ValueError("local-mark copy shapes differ")
    return np.clip(float(dilution) * arrays[0] * arrays[1] * (1.0 + arrays[2]), -1.0, 1.0)


def renew_local_mark(mark: np.ndarray, encoded_adult: np.ndarray, half_life: int) -> np.ndarray:
    rho = 2.0 ** (-1.0 / float(half_life))
    return np.clip(rho * np.asarray(mark) + (1.0 - rho) * np.asarray(encoded_adult), -1.0, 1.0)


def _mark_candidate_worker(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        config_path,
        atlas_path,
        upstream_path,
        output_path,
        model_id,
        task_id,
        mode,
        selection,
        profile,
        shard_key,
    ) = args
    config = load_history_config(Path(config_path))
    atlas = Path(atlas_path)
    upstream = Path(upstream_path)
    output = Path(output_path)
    shard = output / ".shards" / f"mark-{mode}" / f"{shard_key}.json"
    protocol_digest = digest(config)
    if shard.is_file():
        existing = json.loads(shard.read_text(encoding="utf-8"))
        if existing.get("protocol_digest") == protocol_digest and existing.get("profile") == profile:
            return existing
    histories, calibrations = _history_maps(atlas)
    references = {
        row["memory_task_id"]: row for row in read_jsonl(output / "fingerprint-reference.jsonl")
    }
    candidate = _candidate_map(config)[task_id]
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, int(model_id), delta_t=float(config["delta_t"]))
    calibration = calibrations[task_id]
    checkpoint = float(config["parent_checkpoint"])
    naive = _checkpoint(histories, task_id, "naive", checkpoint)
    combined = _checkpoint(histories, task_id, "combined_reset", checkpoint)
    control = _checkpoint(histories, task_id, "control_only", checkpoint)
    paired = _checkpoint(histories, str(candidate["paired_task_id"]), "combined_reset", checkpoint)
    nodes = [int(value) for value in candidate["selected_nodes"]]
    indices = np.asarray(nodes, dtype=int)
    scale = local_mark_scale(memory.bounds, control.y, combined.y, nodes)
    founder = encode_local_mark(combined.y, control.y, scale, nodes)
    paired_founder = encode_local_mark(paired.y, control.y, scale, nodes)
    if mode == "grid":
        settings = [
            (int(half_life), float(coupling))
            for coupling in config["mark_couplings"]
            for half_life in config["mark_half_lives"]
        ]
        seed_count = int(
            config["mark_discovery_seeds_full"]
            if profile == "full"
            else config["mark_discovery_seeds_lite"]
        )
        arms = ("intact", "renewal_off", "zero_donor")
        max_generation = 4
        checkpoints = {4}
    elif mode == "validation":
        if selection is None:
            raise ValueError("mark validation requires a frozen selection")
        settings = [(int(selection["half_life"]), float(selection["coupling"]))]
        seed_count = int(
            config["mark_validation_seeds_full"]
            if profile == "full"
            else config["mark_validation_seeds_lite"]
        )
        arms = MARK_VALIDATION_ARMS
        max_generation = 8
        checkpoints = {int(value) for value in config["lineage_checkpoints"]}
    else:
        raise ValueError(f"unknown mark worker mode: {mode}")
    records: list[dict[str, Any]] = []
    total_cpu = 0.0
    for half_life, coupling in settings:
        for seed_index in range(seed_count):
            for arm in arms:
                initial = (
                    np.zeros_like(founder)
                    if arm in {"writer_off", "zero_donor"}
                    else -founder
                    if arm == "inverted_founder"
                    else paired_founder
                    if arm == "paired_donor"
                    else founder.copy()
                )
                donor_mark = initial.copy()
                donor_source = "founder"
                parent_record_id: str | None = None
                for generation in range(1, max_generation + 1):
                    keep, noise, seed_value = mark_randomness(
                        config, task_id, seed_index, generation, len(nodes)
                    )
                    effective = donor_mark
                    effective_source = donor_source
                    if arm in {"erase_g2", "rescue_g3"} and generation == 2:
                        effective = np.zeros_like(founder)
                        effective_source = "explicit-erase"
                    elif arm == "rescue_g3" and generation == 3:
                        effective = founder
                        effective_source = "explicit-founder-rescue"
                    copied = copy_local_mark(
                        effective, keep, noise, float(config["mark_copy_dilution"])
                    )
                    if arm in {"writer_off", "zero_donor"}:
                        copied = np.zeros_like(copied)
                    y = naive.y.copy()
                    if arm != "reader_off":
                        y[indices] = np.clip(
                            naive.y[indices] + coupling * copied * scale,
                            np.asarray(memory.bounds)[indices, 0],
                            np.asarray(memory.bounds)[indices, 1],
                        )
                    start = State(y, naive.w.copy(), naive.c.copy(), naive.t)
                    if generation in checkpoints:
                        result = _develop_and_fingerprint(
                            backend, memory, calibration, start, config
                        )
                        adult = state_from_payload(result["adult_state"])
                        if adult is None:
                            adult = start.copy()
                        raw_fingerprint: Any = result["raw_fingerprint"]
                        fingerprint: Any = result["fingerprint"]
                        probes: Any = result["probes"]
                        valid = bool(result["valid"])
                        cpu_seconds = float(result["cpu_seconds"])
                        wall_seconds = float(result["wall_seconds"])
                    else:
                        phase = backend.run_unstimulated(
                            start,
                            float(config["phase_duration"]),
                            memory.key.response_id,
                            int(config["trajectory_samples"]),
                        )
                        adult = phase.state
                        raw_fingerprint = fingerprint = probes = None
                        valid = bool(phase.valid)
                        cpu_seconds = float(phase.cpu_seconds)
                        wall_seconds = float(phase.wall_seconds)
                    total_cpu += cpu_seconds
                    record_id = (
                        f"mark-{mode}|{task_id}|h{half_life}|c{coupling:g}|"
                        f"{seed_index}|{arm}|g{generation}"
                    )
                    records.append(
                        {
                            "task_id": record_id,
                            "memory_task_id": task_id,
                            "model_id": int(model_id),
                            "seed_index": seed_index,
                            "philox_seed": seed_value,
                            "generation": generation,
                            "condition": arm,
                            "nodes": nodes,
                            "half_life": half_life,
                            "coupling": coupling,
                            "mark_scale": scale,
                            "founder_mark": founder,
                            "copied_mark": copied,
                            "copy_keep": keep,
                            "copy_noise": noise,
                            "donor_source": effective_source,
                            "donor_parent_record_id": parent_record_id,
                            "founder_reused": effective_source in {"founder", "explicit-founder-rescue"},
                            "adult_state": state_payload(adult),
                            "raw_fingerprint": raw_fingerprint,
                            "fingerprint": fingerprint,
                            "probes": probes,
                            "projection": None,
                            "valid": valid,
                            "cpu_seconds": cpu_seconds,
                            "wall_seconds": wall_seconds,
                        }
                    )
                    encoded_adult = encode_local_mark(adult.y, naive.y, scale, nodes)
                    if arm == "renewal_off":
                        donor_mark = copied.copy()
                        donor_source = f"damaged-copy-g{generation}"
                    elif arm in {"writer_off", "zero_donor"}:
                        donor_mark = np.zeros_like(copied)
                        donor_source = f"zero-g{generation}"
                    else:
                        donor_mark = renew_local_mark(copied, encoded_adult, half_life)
                        donor_source = f"rewritten-g{generation}"
                    parent_record_id = record_id
    by_key = {
        (
            int(row["half_life"]),
            float(row["coupling"]),
            int(row["seed_index"]),
            int(row["generation"]),
            str(row["condition"]),
        ): row
        for row in records
    }
    direction = references[task_id]["reset_history_direction"]
    baseline_arm = "zero_donor"
    for half_life, coupling in settings:
        for seed_index in range(seed_count):
            for generation in checkpoints:
                baseline = by_key[(half_life, coupling, seed_index, generation, baseline_arm)]
                for arm in arms:
                    row = by_key[(half_life, coupling, seed_index, generation, arm)]
                    row["projection"] = (
                        project_fingerprint(row["fingerprint"], baseline["fingerprint"], direction)
                        if row["valid"] and baseline["valid"]
                        else None
                    )
    payload = {
        "protocol_digest": protocol_digest,
        "profile": profile,
        "mode": mode,
        "model_id": int(model_id),
        "memory_task_id": task_id,
        "aggregate_cpu_seconds": total_cpu,
        "records": records,
    }
    write_json(shard, payload)
    return payload


def select_mark_settings(
    records: Sequence[Mapping[str, Any]], advanced: Sequence[str], config: Mapping[str, Any]
) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    selections: dict[str, dict[str, Any]] = {}
    for task_id in advanced:
        task_rows = [
            row
            for row in records
            if row["memory_task_id"] == task_id and int(row["generation"]) == 4
        ]
        settings = sorted(
            {(float(row["coupling"]), int(row["half_life"])) for row in task_rows},
            key=lambda item: (item[0], item[1]),
        )
        chosen: dict[str, Any] | None = None
        for coupling, half_life in settings:
            keyed = {
                (int(row["seed_index"]), str(row["condition"])): row
                for row in task_rows
                if int(row["half_life"]) == half_life
                and math.isclose(float(row["coupling"]), coupling)
            }
            metrics: list[dict[str, Any]] = []
            seed_indices = sorted({key[0] for key in keyed})
            for seed_index in seed_indices:
                intact = keyed.get((seed_index, "intact"))
                off = keyed.get((seed_index, "renewal_off"))
                zero = keyed.get((seed_index, "zero_donor"))
                valid = bool(
                    intact and off and zero
                    and intact["valid"] and off["valid"] and zero["valid"]
                    and intact["projection"] is not None and off["projection"] is not None
                )
                metrics.append(
                    {"seed_index": seed_index, "valid": valid}
                    if not valid
                    else {
                        "seed_index": seed_index,
                        "valid": True,
                        "intact_projection": float(intact["projection"]),
                        "renewal_advantage": float(intact["projection"]) - float(off["projection"]),
                    }
                )
            valid_metrics = [row for row in metrics if row["valid"]]
            intact_projection = (
                float(np.median([row["intact_projection"] for row in valid_metrics]))
                if valid_metrics
                else 0.0
            )
            renewal_advantage = (
                float(np.median([row["renewal_advantage"] for row in valid_metrics]))
                if valid_metrics
                else 0.0
            )
            minimum_valid = max(1, math.ceil(0.75 * len(seed_indices)))
            passed = bool(
                len(valid_metrics) >= minimum_valid
                and intact_projection >= float(config["mark_discovery_projection_min"])
                and renewal_advantage >= float(config["mark_renewal_advantage_min"])
            )
            summary = {
                "memory_task_id": task_id,
                "half_life": half_life,
                "coupling": coupling,
                "valid_seed_count": len(valid_metrics),
                "intact_projection": intact_projection,
                "renewal_advantage": renewal_advantage,
                "pass": passed,
                "seed_metrics": metrics,
            }
            summaries.append(summary)
            if passed and chosen is None:
                chosen = {"half_life": half_life, "coupling": coupling}
        if chosen is not None:
            selections[task_id] = chosen
    return {
        "task_id": "mark-selection",
        "summaries": summaries,
        "selections": selections,
        "selected_candidate_count": len(selections),
        "pass": bool(selections),
    }


def mark_validation_decision(
    records: Sequence[Mapping[str, Any]], selections: Mapping[str, Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    for task_id in selections:
        task_rows = [
            row
            for row in records
            if row["memory_task_id"] == task_id and int(row["generation"]) == 8
        ]
        keyed = {(int(row["seed_index"]), str(row["condition"])): row for row in task_rows}
        seed_indices = sorted({key[0] for key in keyed})
        seed_metrics: list[dict[str, Any]] = []
        for seed_index in seed_indices:
            arm_rows = {arm: keyed.get((seed_index, arm)) for arm in MARK_VALIDATION_ARMS}
            valid = bool(
                all(row is not None and bool(row.get("valid", False)) for row in arm_rows.values())
                and all(row.get("projection") is not None for row in arm_rows.values() if row is not None)
            )
            if not valid:
                seed_metrics.append({"seed_index": seed_index, "valid": False})
                continue
            projection = {arm: float(arm_rows[arm]["projection"]) for arm in MARK_VALIDATION_ARMS}
            intact = projection["intact"]
            denominator = max(abs(intact), 1e-12)
            seed_metrics.append(
                {
                    "seed_index": seed_index,
                    "valid": True,
                    "consistent": bool(
                        intact > 0.0
                        and all(
                            projection[arm] < intact
                            for arm in ("writer_off", "renewal_off", "reader_off", "erase_g2")
                        )
                        and projection["rescue_g3"] > projection["erase_g2"]
                    ),
                    "intact_projection": intact,
                    "writer_removal_fraction": (intact - projection["writer_off"]) / denominator,
                    "renewal_removal_fraction": (intact - projection["renewal_off"]) / denominator,
                    "reader_removal_fraction": (intact - projection["reader_off"]) / denominator,
                    "erase_removal_fraction": (intact - projection["erase_g2"]) / denominator,
                    "rescue_fraction": projection["rescue_g3"] / denominator,
                    "inverted_fraction": abs(projection["inverted_founder"]) / denominator,
                    "paired_fraction": abs(projection["paired_donor"]) / denominator,
                }
            )
        valid_rows = [row for row in seed_metrics if row.get("valid")]

        def med(key: str, default: float = 0.0) -> float:
            return float(np.median([float(row[key]) for row in valid_rows])) if valid_rows else default

        metrics = {
            "valid_seed_count": len(valid_rows),
            "consistent_seed_count": sum(bool(row["consistent"]) for row in valid_rows),
            "intact_projection": med("intact_projection"),
            "writer_removal_fraction": med("writer_removal_fraction"),
            "renewal_removal_fraction": med("renewal_removal_fraction"),
            "reader_removal_fraction": med("reader_removal_fraction"),
            "erase_removal_fraction": med("erase_removal_fraction"),
            "rescue_fraction": med("rescue_fraction"),
            "inverted_fraction": med("inverted_fraction", math.inf),
            "paired_fraction": med("paired_fraction", math.inf),
        }
        passed = bool(
            metrics["valid_seed_count"] >= int(config["minimum_consistent_seeds"])
            and metrics["consistent_seed_count"] >= int(config["minimum_consistent_seeds"])
            and metrics["intact_projection"] >= float(config["mark_validation_projection_min"])
            and min(
                metrics["writer_removal_fraction"],
                metrics["renewal_removal_fraction"],
                metrics["reader_removal_fraction"],
                metrics["erase_removal_fraction"],
            )
            >= float(config["mark_control_removal_fraction"])
            and metrics["rescue_fraction"] >= float(config["mark_rescue_fraction"])
            and max(metrics["inverted_fraction"], metrics["paired_fraction"])
            <= float(config["mark_wrong_content_max_fraction"])
        )
        summaries.append(
            {
                "memory_task_id": task_id,
                "selection": selections[task_id],
                "pass": passed,
                "metrics": metrics,
                "seed_metrics": seed_metrics,
            }
        )
    passes = [row for row in summaries if row["pass"]]
    return {
        "task_id": "mark-validation-decision",
        "candidate_summaries": summaries,
        "passing_candidates": [row["memory_task_id"] for row in passes],
        "pass_count": len(passes),
        "label": "constructive-engineered-sufficiency" if passes else "no-engineered-renewal",
        "pass": bool(passes),
    }


def _validate_parents(
    config: Mapping[str, Any], atlas: Path, renewal: Path, upstream: Path
) -> dict[str, Any]:
    provenance = validate_upstream(upstream, config["upstream_commit"])
    atlas_verified = verify_checksums(atlas)
    renewal_verified = verify_checksums(renewal)
    for name, expected in config["atlas_parent_hashes"].items():
        if sha256_file(atlas / name) != expected:
            raise ValueError(f"atlas parent hash mismatch: {name}")
    for name, expected in config["renewal_parent_hashes"].items():
        if sha256_file(renewal / name) != expected:
            raise ValueError(f"renewal parent hash mismatch: {name}")
    atlas_registration = json.loads((atlas / "registration.json").read_text(encoding="utf-8"))
    renewal_registration = json.loads(
        (renewal / "registration.json").read_text(encoding="utf-8")
    )
    atlas_state = json.loads((atlas / "state.json").read_text(encoding="utf-8"))
    renewal_state = json.loads((renewal / "state.json").read_text(encoding="utf-8"))
    if atlas_registration.get("experiment_id") != config["atlas_parent_experiment_id"]:
        raise ValueError("wrong atlas parent experiment")
    if renewal_registration.get("experiment_id") != config["renewal_parent_experiment_id"]:
        raise ValueError("wrong renewal parent experiment")
    if atlas_state.get("status") != "completed" or renewal_state.get("status") != "completed":
        raise ValueError("both history-renewal parents must be completed")
    nominations = {
        row["memory_task_id"]: row
        for row in json.loads(
            (renewal / "carrier-nominations.json").read_text(encoding="utf-8")
        )["nominations"]
    }
    for candidate in config["candidates"]:
        task_id = candidate["task_id"]
        if task_id not in nominations:
            raise ValueError(f"V1 nomination missing: {task_id}")
        if list(nominations[task_id]["selected_nodes"]) != list(candidate["selected_nodes"]):
            raise ValueError(f"V1 selected-node nomination changed: {task_id}")
        if list(nominations[task_id]["random_nodes"]) != list(candidate["random_nodes"]):
            raise ValueError(f"V1 random-node control changed: {task_id}")
    return {
        "upstream": provenance,
        "atlas_checksum_count": len(atlas_verified),
        "renewal_checksum_count": len(renewal_verified),
        "atlas_registration": atlas_registration,
        "renewal_registration": renewal_registration,
    }


def analyze_history_renewal(output: Path, final_status: str = "completed") -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    references = list(read_jsonl(output / "fingerprint-reference.jsonl"))
    audit_records = list(read_jsonl(output / "carrier-audit.jsonl"))
    natural_records = list(read_jsonl(output / "natural-lineage.jsonl"))
    grid_records = list(read_jsonl(output / "mark-grid.jsonl"))
    validation_records = list(read_jsonl(output / "mark-validation.jsonl"))
    audit = json.loads((output / "carrier-audit-decision.json").read_text(encoding="utf-8"))
    natural = json.loads((output / "natural-lineage-decision.json").read_text(encoding="utf-8"))
    selection = json.loads((output / "mark-selection.json").read_text(encoding="utf-8"))
    validation = json.loads((output / "mark-validation-decision.json").read_text(encoding="utf-8"))
    if not references or audit["eligible_count"] == 0:
        verdict = "no-robust-history-fingerprint"
    elif not audit["pass"]:
        verdict = "no-compact-causal-carrier"
    elif natural["pass"]:
        verdict = "native-renewal-lead"
    elif validation["pass"]:
        verdict = "engineered-constructive-sufficiency"
    elif selection["pass"]:
        verdict = "engineered-renewal-failed-validation"
    else:
        verdict = "no-renewal-under-tested-mechanisms"
    minimum_gate = bool(
        len(references) == 8
        and all(name in registration for name in ("protocol", "parents", "worker_history"))
        and (output / "parent-gate.json").is_file()
        and (final_status != "completed" or all(row.get("valid") for row in references))
    )
    analysis = {
        "experiment_id": registration["experiment_id"],
        "run_status": final_status,
        "profile": registration["profile"],
        "verdict": verdict,
        "minimum_completion_gate": minimum_gate,
        "eligible_fingerprint_count": int(audit["eligible_count"]),
        "immediate_carrier_pass_count": int(audit["pass_count"]),
        "advanced_candidates": audit["advanced_candidates"],
        "native_pass_count": int(natural["pass_count"]),
        "native_label": natural["label"],
        "mark_selected_candidate_count": int(selection["selected_candidate_count"]),
        "engineered_pass_count": int(validation["pass_count"]),
        "record_counts": {
            "fingerprint-reference.jsonl": len(references),
            "carrier-audit.jsonl": len(audit_records),
            "natural-lineage.jsonl": len(natural_records),
            "mark-grid.jsonl": len(grid_records),
            "mark-validation.jsonl": len(validation_records),
        },
        "claim_boundary": registration["protocol"]["claim_boundary"],
    }
    write_json(output / "analysis.json", analysis)
    hypotheses = {
        "experiment_id": registration["experiment_id"],
        "verdict": verdict,
        "hypotheses": [
            {
                "status": "supported" if audit["pass"] else "not-supported",
                "hypothesis": "A compact subset of V1-nominated expression coordinates carries a history-specific held-out response fingerprint immediately after damage.",
            },
            {
                "status": "supported" if natural["pass"] else "not-supported",
                "hypothesis": "Adult GRN dynamics rewrite that compact native state strongly enough for content-specific recurrence through G8.",
            },
            {
                "status": "supported" if validation["pass"] else "not-supported" if selection["pass"] else "not-tested",
                "hypothesis": "A compact, explicitly engineered, locally renewed mark is sufficient to bridge the missing G8 recurrence mechanism.",
            },
        ],
        "interpretation": "Negative gates narrow the hypothesis space; engineered success would be constructive sufficiency, not discovery of a natural carrier.",
    }
    write_json(output / "hypotheses.json", hypotheses)
    report = f"""# History-specific carrier and renewal V2

Status: **{final_status}**  
Verdict: **{verdict}**  
Profile: **{registration['profile']}**

The robust five-probe reference gate admitted {audit['eligible_count']} of 8
memories.  {audit['pass_count']} compact nomination(s) passed the immediate
causal transfer/ablation/content controls, and the frozen ranking advanced
{len(audit['advanced_candidates'])}.  The corrected lineage produced
{natural['pass_count']} native G4+G8 pass(es).  The engineered branch selected
{selection['selected_candidate_count']} setting(s) and produced
{validation['pass_count']} validated constructive-sufficiency result(s).

This is an exploratory hypothesis-generation branch.  It does not establish
biological inheritance or identify a natural epigenetic substrate.  In
particular, an engineered-mark result would show only that a local writer,
reader and renewal loop can be sufficient in this simulation.
"""
    atomic_write_text(output / "report.md", report)
    return analysis


class HistoryRenewalCampaign:
    def __init__(
        self,
        config_path: Path,
        atlas: Path,
        renewal: Path,
        upstream: Path,
        output: Path,
        workers: int,
    ):
        self.config_path = config_path.resolve()
        self.config = load_history_config(self.config_path)
        self.atlas = atlas.resolve()
        self.renewal = renewal.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        self.workers = int(workers)
        if not 1 <= self.workers <= int(self.config["max_workers"]):
            raise ValueError("history-renewal workers must lie between one and two")
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / "SHA256SUMS").is_file():
            raise ValueError("sealed history-renewal output cannot be resumed")
        self.profile = os.environ.get("HISTORY_RENEWAL_PROFILE", "full")
        if self.profile not in {"full", "lite"}:
            raise ValueError("HISTORY_RENEWAL_PROFILE must be full or lite")
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
        parents = _validate_parents(self.config, self.atlas, self.renewal, self.upstream)
        parent_payload = {
            "atlas": {
                "path": str(self.atlas),
                "experiment_id": self.config["atlas_parent_experiment_id"],
                "hashes": self.config["atlas_parent_hashes"],
            },
            "renewal": {
                "path": str(self.renewal),
                "experiment_id": self.config["renewal_parent_experiment_id"],
                "hashes": self.config["renewal_parent_hashes"],
            },
        }
        path = self.output / "registration.json"
        if path.is_file():
            registration = json.loads(path.read_text(encoding="utf-8"))
            if registration.get("protocol_digest") != digest(self.config):
                raise ValueError("resumed history-renewal protocol differs")
            if registration.get("profile") != self.profile:
                raise ValueError("resumed history-renewal profile differs")
            if registration.get("parents") != parent_payload:
                raise ValueError("resumed history-renewal parents differ")
            runtime_image = registration.get("runtime", {}).get("container_image_id")
            current_image = os.environ.get("EXPERIMENT_IMAGE_ID", "unknown")
            if runtime_image != current_image:
                raise ValueError("resumed history-renewal image differs")
            history = list(registration.get("worker_history", []))
            if not history or int(history[-1]["workers"]) != self.workers:
                history.append(
                    {
                        "workers": self.workers,
                        "resumed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                )
                registration["worker_history"] = history
                registration["workers"] = self.workers
                write_json(path, registration)
        else:
            registration = {
                "experiment_id": self.config["experiment_id"],
                "protocol": self.config,
                "protocol_digest": digest(self.config),
                "profile": self.profile,
                "workers": self.workers,
                "worker_history": [
                    {
                        "workers": self.workers,
                        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                ],
                "parents": parent_payload,
                "upstream": parents["upstream"],
                "runtime": _runtime_manifest(),
                "candidates": self.config["candidates"],
            }
            write_json(path, registration)
        write_json(
            self.output / "parent-gate.json",
            {
                "pass": True,
                "atlas_checksum_count": parents["atlas_checksum_count"],
                "renewal_checksum_count": parents["renewal_checksum_count"],
                "frozen_candidate_count": len(self.config["candidates"]),
                "represented_models": [10, 16, 37, 204],
            },
        )
        incidents = self.output / "runtime-incidents.json"
        if not incidents.is_file():
            write_json(
                incidents,
                {
                    "experiment_id": self.config["experiment_id"],
                    "incidents": [],
                    "note": "Production runtime incidents only; development smoke artifacts are retained separately.",
                },
            )

    def references(self) -> list[dict[str, Any]]:
        probes = {
            (row["memory_task_id"], row["arm"], row["probe"]): row
            for row in read_jsonl(self.atlas / "probes.jsonl")
        }
        records = [
            reference_record(candidate["task_id"], probes, self.config)
            for candidate in self.config["candidates"]
        ]
        _write_jsonl(self.output / "fingerprint-reference.jsonl", records)
        return records

    def _enforce(self, stage: str) -> None:
        self.ledger.checkpoint(stage, _all_shard_cpu(self.output))
        self.ledger.enforce_hard()

    def run(self) -> int:
        self.ledger.start_heartbeat()
        try:
            self.state("running", "registration")
            self.register()
            self.state("running", "fingerprint-reference")
            references = self.references()
            eligible = {row["memory_task_id"] for row in references if row["eligible"]}
            groups: dict[int, list[str]] = {}
            for candidate in self.config["candidates"]:
                if candidate["task_id"] in eligible:
                    groups.setdefault(int(candidate["model_id"]), []).append(candidate["task_id"])
            audit_args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    model_id,
                    tasks,
                    self.profile,
                    f"model-{model_id}",
                )
                for model_id, tasks in sorted(groups.items())
            ]
            self.state("running", "carrier-audit", eligible_count=len(eligible))
            audit_shards = _parallel(_audit_model_worker, audit_args, self.workers) if audit_args else []
            audit_records = _merge(self.output, "carrier-audit", audit_shards)
            audit = immediate_carrier_decision(audit_records, references, self.config, self.profile)
            write_json(self.output / "carrier-audit-decision.json", audit)
            self._enforce("carrier-audit-complete")

            advanced = list(audit["advanced_candidates"])
            natural_args = [
                (
                    str(self.config_path),
                    str(self.atlas),
                    str(self.upstream),
                    str(self.output),
                    int(task_id.split("-")[0]),
                    task_id,
                    self.profile,
                    f"task-{task_id}",
                )
                for task_id in advanced
            ]
            self.state("running", "natural-lineage", advanced_candidates=advanced)
            natural_shards = (
                _parallel(_native_candidate_worker, natural_args, min(self.workers, len(natural_args)))
                if natural_args
                else []
            )
            natural_records = _merge(self.output, "natural-lineage", natural_shards)
            natural = natural_lineage_decision(natural_records, advanced, self.config)
            write_json(self.output / "natural-lineage-decision.json", natural)
            self._enforce("natural-lineage-complete")

            grid_records: list[dict[str, Any]] = []
            validation_records: list[dict[str, Any]] = []
            selection: dict[str, Any] = {
                "task_id": "mark-selection",
                "summaries": [],
                "selections": {},
                "selected_candidate_count": 0,
                "pass": False,
                "skip_reason": "native-pass" if natural["pass"] else "no-immediate-carrier",
            }
            validation: dict[str, Any] = {
                "task_id": "mark-validation-decision",
                "candidate_summaries": [],
                "passing_candidates": [],
                "pass_count": 0,
                "label": "not-run",
                "pass": False,
                "skip_reason": selection["skip_reason"],
            }
            if audit["pass"] and not natural["pass"] and self.ledger.may_start():
                grid_args = [
                    (
                        str(self.config_path),
                        str(self.atlas),
                        str(self.upstream),
                        str(self.output),
                        int(task_id.split("-")[0]),
                        task_id,
                        "grid",
                        None,
                        self.profile,
                        f"task-{task_id}",
                    )
                    for task_id in advanced
                ]
                self.state("running", "mark-grid")
                grid_shards = _parallel(
                    _mark_candidate_worker, grid_args, min(self.workers, len(grid_args))
                )
                grid_records = _merge(self.output, "mark-grid", grid_shards)
                selection = select_mark_settings(grid_records, advanced, self.config)
                self._enforce("mark-grid-complete")
                if selection["pass"] and self.ledger.may_start():
                    validation_args = [
                        (
                            str(self.config_path),
                            str(self.atlas),
                            str(self.upstream),
                            str(self.output),
                            int(task_id.split("-")[0]),
                            task_id,
                            "validation",
                            setting,
                            self.profile,
                            f"task-{task_id}",
                        )
                        for task_id, setting in selection["selections"].items()
                    ]
                    self.state("running", "mark-validation")
                    validation_shards = _parallel(
                        _mark_candidate_worker,
                        validation_args,
                        min(self.workers, len(validation_args)),
                    )
                    validation_records = _merge(
                        self.output, "mark-validation", validation_shards
                    )
                    validation = mark_validation_decision(
                        validation_records, selection["selections"], self.config
                    )
                    self._enforce("mark-validation-complete")
            if not (self.output / "mark-grid.jsonl").is_file():
                _write_jsonl(self.output / "mark-grid.jsonl", grid_records)
            if not (self.output / "mark-validation.jsonl").is_file():
                _write_jsonl(self.output / "mark-validation.jsonl", validation_records)
            write_json(self.output / "mark-selection.json", selection)
            write_json(self.output / "mark-validation-decision.json", validation)
            write_json(
                self.output / "branch-decision.json",
                {
                    "task_id": "branch-decision",
                    "immediate_carrier_pass": bool(audit["pass"]),
                    "native_pass": bool(natural["pass"]),
                    "engineered_branch_entered": bool(grid_records),
                    "engineered_validation_pass": bool(validation["pass"]),
                    "branch": "native-stop" if natural["pass"] else "conditional-engineered" if audit["pass"] else "reference-or-carrier-stop",
                },
            )
            self.state("finalizing", "analysis")
            analyze_history_renewal(self.output, final_status="completed")
            self.state("completed", "complete")
            self.ledger.close()
            write_checksums(self.output)
            return 0
        except TimeoutError as error:
            self.state("time-budget-exhausted", "interrupted", error=str(error))
            self.ledger.close()
            return 124
        except BaseException as error:
            self.state("failed", "exception", error=repr(error))
            self.ledger.close()
            raise


def run_history_renewal(
    config: Path,
    atlas: Path,
    renewal: Path,
    upstream: Path,
    output: Path,
    workers: int = 2,
) -> int:
    return HistoryRenewalCampaign(config, atlas, renewal, upstream, output, workers).run()


def smoke_history_renewal(
    config_path: Path,
    atlas: Path,
    renewal: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    config = load_history_config(config_path)
    parents = _validate_parents(config, atlas, renewal, upstream)
    probes = {
        (row["memory_task_id"], row["arm"], row["probe"]): row
        for row in read_jsonl(atlas / "probes.jsonl")
    }
    references = [
        reference_record(candidate["task_id"], probes, config)
        for candidate in config["candidates"]
    ]
    eligible_count = sum(bool(row["eligible"]) for row in references)
    histories, calibrations = _history_maps(atlas)
    probe_task = next(
        (row["memory_task_id"] for row in references if row["eligible"]),
        str(config["candidates"][0]["task_id"]),
    )
    released = load_released_task(upstream, probe_task)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, memory.key.model_id, delta_t=float(config["delta_t"]))
    naive = _checkpoint(histories, probe_task, "naive", float(config["parent_checkpoint"]))
    biological = _develop_and_fingerprint(
        backend, memory, calibrations[probe_task], naive, config
    )
    v1_ledger = json.loads((renewal / "resource-ledger.json").read_text(encoding="utf-8"))
    v1_records = sum(
        sum(1 for _ in read_jsonl(renewal / name))
        for name in ("native-renewal.jsonl", "carrier-screen.jsonl", "native-recurrence.jsonl")
    )
    v1_phases = max(1, v1_records * 5)

    def projection(profile: str) -> dict[str, float]:
        advanced = int(
            config["max_advanced_candidates_full"]
            if profile == "full"
            else config["max_advanced_candidates_lite"]
        )
        discovery_seeds = int(
            config["mark_discovery_seeds_full"]
            if profile == "full"
            else config["mark_discovery_seeds_lite"]
        )
        validation_seeds = int(
            config["mark_validation_seeds_full"]
            if profile == "full"
            else config["mark_validation_seeds_lite"]
        )
        phases = (
            eligible_count * int(config["audit_seeds"]) * len(AUDIT_ARMS) * 6
            + advanced * int(config["audit_seeds"]) * len(NATIVE_ARMS) * 28
            + advanced * discovery_seeds * 9 * 3 * 9
            + advanced * validation_seeds * len(MARK_VALIDATION_ARMS) * 28
        )
        ratio = phases / v1_phases
        safety = float(config["projection_safety_factor"])
        return {
            "phase_equivalents": phases,
            "projected_active_wall_seconds": float(v1_ledger["active_wall_seconds"]) * ratio * safety,
            "projected_aggregate_cpu_seconds": float(v1_ledger["aggregate_cpu_seconds"]) * ratio * safety,
        }

    projections = {name: projection(name) for name in ("full", "lite")}
    selected_profile = next(
        (
            name
            for name in ("full", "lite")
            if projections[name]["projected_active_wall_seconds"] < float(config["soft_wall_seconds"])
            and projections[name]["projected_aggregate_cpu_seconds"] < float(config["soft_aggregate_cpu_seconds"])
        ),
        None,
    )
    result = {
        "target": "history-carrier-renewal",
        "pass": bool(biological["valid"] and selected_profile is not None),
        "production_launch_allowed": bool(biological["valid"] and selected_profile is not None),
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "atlas_parent_manifest_sha256": config["atlas_parent_hashes"]["SHA256SUMS"],
        "renewal_parent_manifest_sha256": config["renewal_parent_hashes"]["SHA256SUMS"],
        "eligible_fingerprint_count": eligible_count,
        "reference_records": references,
        "biological_probe": {
            "memory_task_id": probe_task,
            "valid": biological["valid"],
            "raw_fingerprint": biological["raw_fingerprint"],
            "cpu_seconds": biological["cpu_seconds"],
            "wall_seconds": biological["wall_seconds"],
        },
        "projection_basis": {
            "v1_record_count": v1_records,
            "v1_phase_equivalents": v1_phases,
            "v1_active_wall_seconds": v1_ledger["active_wall_seconds"],
            "v1_aggregate_cpu_seconds": v1_ledger["aggregate_cpu_seconds"],
            "safety_factor": config["projection_safety_factor"],
        },
        "projections": projections,
        "selected_profile": selected_profile,
        "parent_checksum_counts": {
            "atlas": parents["atlas_checksum_count"],
            "renewal": parents["renewal_checksum_count"],
        },
    }
    # The artifact helpers accept ndarrays, but the CLI pretty-printer receives
    # the return value directly.  Round-trip through strict canonical JSON so
    # smoke output has the same representation at both boundaries.
    result = json.loads(canonical_json(result))
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "smoke.json", result)
    return result


def history_renewal_status(output: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"output": str(output.resolve())}
    for name in (
        "state",
        "resource-ledger",
        "parent-gate",
        "carrier-audit-decision",
        "natural-lineage-decision",
        "mark-selection",
        "mark-validation-decision",
        "branch-decision",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(path.read_text(encoding="utf-8"))
    for name in (
        "fingerprint-reference",
        "carrier-audit",
        "natural-lineage",
        "mark-grid",
        "mark-validation",
    ):
        path = output / f"{name}.jsonl"
        if path.is_file():
            result[f"{name.replace('-', '_')}_records"] = sum(1 for _ in read_jsonl(path))
    result["sealed"] = (output / "SHA256SUMS").is_file()
    return result
