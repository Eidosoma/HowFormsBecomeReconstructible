"""Exploratory observer-ladder analysis for Observer Atlas V1."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import append_jsonl, read_jsonl, write_json
from .atlas import ATLAS_ARMS, learned_margin, normalized_state_distance
from .models import MemoryData, MemoryKey
from .upstream import load_memory, load_released_task


CHECKPOINTS = [0.0, 2500.0, 12500.0, 62500.0]
CORE_PROBES = [
    "no_input",
    "cs",
    "ucs_bound_0",
    "ucs_bound_1",
    "cs_reconstructed_ucs",
    "selected_control",
    "cs_selected_control",
    "opposite_selected_control",
    "cs_opposite_selected_control",
    "matched_control",
    "cs_matched_control",
]


def _finite_array(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    return result if result.size and np.all(np.isfinite(result)) else None


def _auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    positives = scores[labels == 1]
    negatives = scores[labels == 0]
    if not len(positives) or not len(negatives):
        return None
    comparisons = 0.0
    for positive in positives:
        comparisons += float(np.sum(positive > negatives))
        comparisons += 0.5 * float(np.sum(positive == negatives))
    return comparisons / (len(positives) * len(negatives))


def _checkpoint(history: dict[str, Any], duration: float) -> dict[str, Any] | None:
    row = history.get("checkpoints", {}).get(f"{duration:g}")
    return row if row and bool(row.get("valid")) else None


def _response_trajectory(checkpoint: dict[str, Any] | None) -> np.ndarray | None:
    if checkpoint is None:
        return None
    return _finite_array(
        checkpoint.get("challenge", {}).get("phase", {}).get("response_trajectory")
    )


def _state_y(checkpoint: dict[str, Any] | None) -> np.ndarray | None:
    if checkpoint is None:
        return None
    return _finite_array(checkpoint.get("state", {}).get("y"))


def _reset_fraction(memory: MemoryData, values: np.ndarray) -> float:
    if memory.response_reg == 1:
        threshold = memory.r_scale * memory.mean_relax
        return float(np.mean(values < threshold))
    threshold = memory.mean_relax / memory.r_scale
    return float(np.mean(values > threshold))


def _ratio_distance(
    candidate: np.ndarray | None,
    naive: np.ndarray | None,
    trained: np.ndarray | None,
    scale: np.ndarray | float,
) -> dict[str, Any]:
    if candidate is None or naive is None or trained is None:
        return {"valid": False, "to_naive": None, "to_trained": None, "ratio": None}
    if not (candidate.shape == naive.shape == trained.shape):
        return {"valid": False, "to_naive": None, "to_trained": None, "ratio": None}
    scale_array = np.maximum(np.asarray(scale, dtype=float), 1e-8)
    d_naive = float(np.sqrt(np.mean(((candidate - naive) / scale_array) ** 2)))
    d_trained = float(np.sqrt(np.mean(((candidate - trained) / scale_array) ** 2)))
    separation = float(np.sqrt(np.mean(((naive - trained) / scale_array) ** 2)))
    return {
        "valid": True,
        "to_naive": d_naive,
        "to_trained": d_trained,
        "naive_trained": separation,
        "ratio": d_naive / max(separation, 1e-12),
        "nearest": "naive" if d_naive < d_trained else "trained",
    }


def _probe_vector(
    memory: MemoryData,
    probe_lookup: dict[tuple[str, str, str], dict[str, Any]],
    task_id: str,
    arm: str,
    names: list[str],
) -> np.ndarray | None:
    scale = np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8)
    parts: list[np.ndarray] = []
    for name in names:
        row = probe_lookup.get((task_id, arm, name))
        if not row or not bool(row.get("valid")):
            return None
        terminal = _finite_array(row.get("phase", {}).get("terminal_y"))
        trajectory = _finite_array(row.get("phase", {}).get("response_trajectory"))
        if terminal is None or trajectory is None or terminal.shape != scale.shape:
            return None
        response_scale = max(float(scale[memory.key.response_id]), 1e-8)
        parts.extend(
            [
                terminal / scale,
                np.asarray(
                    [
                        float(np.mean(trajectory)) / response_scale,
                        float(trajectory[-1]) / response_scale,
                        float(np.ptp(trajectory)) / response_scale,
                    ]
                ),
            ]
        )
    return np.concatenate(parts) if parts else None


def _relearning_summary(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record or not bool(record.get("valid")):
        return {"valid": False, "first_learned_cycle": None, "mean_margin": None, "margins": []}
    margins: list[float] = []
    first = None
    for row in record.get("cycles", []):
        challenge = row.get("challenge")
        if not row.get("valid") or not challenge or not challenge.get("valid"):
            return {"valid": False, "first_learned_cycle": None, "mean_margin": None, "margins": margins}
        margin = float(challenge["learned_margin"])
        margins.append(margin)
        if first is None and not bool(challenge["is_broken"]):
            first = int(row["cycle"])
    return {
        "valid": True,
        "first_learned_cycle": first if first is not None else len(margins) + 1,
        "mean_margin": float(np.mean(margins)),
        "margins": margins,
    }


def _responsiveness(
    probe_lookup: dict[tuple[str, str, str], dict[str, Any]], task_id: str, arm: str
) -> float | None:
    values = [
        float(row["mean_response"])
        for (row_task, row_arm, _), row in probe_lookup.items()
        if row_task == task_id and row_arm == arm and bool(row.get("valid"))
    ]
    return float(np.ptp(values)) if len(values) >= 4 else None


def _feature_vector(
    memory: MemoryData,
    task_id: str,
    arm: str,
    histories: dict[tuple[str, str], dict[str, Any]],
    probes: dict[tuple[str, str, str], dict[str, Any]],
    reinstatement: dict[tuple[str, str], dict[str, Any]],
    relearning: dict[tuple[str, str], dict[str, Any]],
) -> np.ndarray | None:
    history = histories.get((task_id, arm))
    if not history:
        return None
    values: list[float] = []
    for duration in CHECKPOINTS:
        point = _checkpoint(history, duration)
        trajectory = _response_trajectory(point)
        if point is None or trajectory is None:
            return None
        values.extend(
            [
                float(point["challenge"]["learned_margin"]),
                _reset_fraction(memory, trajectory),
            ]
        )
    state = _state_y(_checkpoint(history, 62500.0))
    if state is None:
        return None
    scale = np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8)
    normalized = state / scale
    values.extend(
        [
            float(np.mean(normalized)),
            float(np.std(normalized)),
            float(np.min(normalized)),
            float(np.max(normalized)),
        ]
    )
    for name in CORE_PROBES:
        row = probes.get((task_id, arm, name))
        if not row or not bool(row.get("valid")):
            return None
        terminal = _finite_array(row.get("phase", {}).get("terminal_y"))
        if terminal is None or terminal.shape != scale.shape:
            return None
        terminal_normalized = terminal / scale
        values.extend(
            [
                float(row["learned_margin"]),
                float(np.mean(terminal_normalized)),
                float(np.std(terminal_normalized)),
            ]
        )
    reinstate = reinstatement.get((task_id, arm))
    if not reinstate or not bool(reinstate.get("valid")):
        return None
    values.append(float(reinstate["challenge"]["learned_margin"]))
    relearn = _relearning_summary(relearning.get((task_id, arm)))
    if not relearn["valid"]:
        return None
    values.extend(float(value) for value in relearn["margins"])
    result = np.asarray(values, dtype=float)
    return result if np.all(np.isfinite(result)) else None


def _nearest_centroid_decoder(
    features: dict[tuple[str, str], np.ndarray],
    models: dict[str, int],
    arms: Iterable[str],
    permutation_replicates: int,
) -> tuple[dict[str, Any], dict[tuple[str, str], float]]:
    tasks = sorted(
        task_id
        for task_id in models
        if (task_id, "naive") in features and (task_id, "trained_no_reset") in features
    )
    observed_scores: dict[tuple[str, str], float] = {}
    def fold_score(held_model: int) -> dict[tuple[str, str], float]:
        train_rows: list[np.ndarray] = []
        train_labels: list[int] = []
        for task_id in tasks:
            if models[task_id] == held_model:
                continue
            pair = [features[(task_id, "naive")], features[(task_id, "trained_no_reset")]]
            pair_labels = [0, 1]
            train_rows.extend(pair)
            train_labels.extend(pair_labels)
        if not train_rows or len(set(train_labels)) < 2:
            return {}
        train = np.vstack(train_rows)
        center = np.mean(train, axis=0)
        spread = np.std(train, axis=0)
        spread[spread < 1e-8] = 1.0
        standardized = (train - center) / spread
        label_array = np.asarray(train_labels)
        naive_center = np.mean(standardized[label_array == 0], axis=0)
        trained_center = np.mean(standardized[label_array == 1], axis=0)
        fold_predictions: dict[tuple[str, str], float] = {}
        for task_id in tasks:
            if models[task_id] != held_model:
                continue
            for arm in arms:
                vector = features.get((task_id, arm))
                if vector is None:
                    continue
                vector = (vector - center) / spread
                score = float(
                    np.linalg.norm(vector - naive_center)
                    - np.linalg.norm(vector - trained_center)
                )
                fold_predictions[(task_id, arm)] = score
        return fold_predictions

    for model_id in sorted(set(models.values())):
        observed_scores.update(fold_score(model_id))
    reference_keys = [
        (task_id, arm)
        for task_id in tasks
        for arm in ("naive", "trained_no_reset")
        if (task_id, arm) in observed_scores
    ]
    label_array = np.asarray(
        [int(arm == "trained_no_reset") for _, arm in reference_keys], dtype=int
    )
    score_array = np.asarray(
        [observed_scores[key] for key in reference_keys], dtype=float
    )
    group_array = np.asarray([models[task_id] for task_id, _ in reference_keys])
    accuracy = (
        float(np.mean((score_array > 0).astype(int) == label_array))
        if len(label_array)
        else None
    )
    auc = _auc(label_array, score_array) if len(label_array) else None
    rng = np.random.Generator(np.random.Philox(20260824))
    null_accuracy = np.empty(permutation_replicates, dtype=float)
    predictions = (score_array > 0).astype(int)
    unique_groups = sorted(set(group_array.tolist()))
    # Scores are genuinely held out by BioModel.  Swap the paired history
    # labels within each held-out BioModel, preserving its grouped structure,
    # without refitting on that held-out group.
    for replicate in range(permutation_replicates):
        swapped = label_array.copy()
        flips = rng.integers(0, 2, len(unique_groups))
        for model_id, flip in zip(unique_groups, flips):
            if flip:
                swapped[group_array == model_id] = 1 - swapped[group_array == model_id]
        null_accuracy[replicate] = float(np.mean(predictions == swapped))
    finite_null = null_accuracy[np.isfinite(null_accuracy)]
    p_value = (
        float((1 + np.sum(finite_null >= float(accuracy))) / (1 + len(finite_null)))
        if accuracy is not None and len(finite_null)
        else None
    )
    result = {
        "method": "leave-one-biomodel-out-nearest-centroid-with-heldout-group-label-swaps",
        "reference_memory_count": len(tasks),
        "reference_row_count": len(label_array),
        "accuracy": accuracy,
        "auc": auc,
        "permutation_replicates": int(permutation_replicates),
        "permutation_p": p_value,
        "null_accuracy_95": None
        if not len(finite_null)
        else float(np.quantile(finite_null, 0.95)),
        "score_direction": "positive-is-trained-like",
    }
    return result, observed_scores


def _kmeans(values: np.ndarray, k: int, rng: np.random.Generator, starts: int = 10) -> np.ndarray:
    best_labels = np.zeros(len(values), dtype=int)
    best_loss = math.inf
    for _ in range(starts):
        centers = values[rng.choice(len(values), size=k, replace=False)].copy()
        labels = np.zeros(len(values), dtype=int)
        for _ in range(100):
            distances = np.linalg.norm(values[:, None, :] - centers[None, :, :], axis=2)
            new_labels = np.argmin(distances, axis=1)
            if np.array_equal(labels, new_labels) and _ > 0:
                break
            labels = new_labels
            for cluster in range(k):
                members = values[labels == cluster]
                centers[cluster] = (
                    np.mean(members, axis=0)
                    if len(members)
                    else values[rng.integers(0, len(values))]
                )
        loss = float(np.sum((values - centers[labels]) ** 2))
        if loss < best_loss:
            best_loss = loss
            best_labels = labels.copy()
    return best_labels


def _silhouette(values: np.ndarray, labels: np.ndarray) -> float:
    if len(set(labels)) < 2:
        return -1.0
    result: list[float] = []
    distances = np.linalg.norm(values[:, None, :] - values[None, :, :], axis=2)
    for index, label in enumerate(labels):
        same = np.where(labels == label)[0]
        same = same[same != index]
        a = float(np.mean(distances[index, same])) if len(same) else 0.0
        b = min(
            float(np.mean(distances[index, labels == other]))
            for other in set(labels)
            if other != label
        )
        result.append((b - a) / max(a, b, 1e-12))
    return float(np.mean(result))


def _cluster_atlas(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    feature_names = [
        "long_reset_margin",
        "trajectory_distance_ratio",
        "state_distance_ratio",
        "counterfactual_distance_ratio",
        "relearning_margin_delta",
        "reinstatement_learned_margin",
        "responsiveness_ratio",
        "combined_control_counterfactual_ratio",
    ]
    complete = [
        row
        for row in rows
        if all(row.get(name) is not None and np.isfinite(float(row[name])) for name in feature_names)
    ]
    if len(complete) < 6:
        return {"stable": False, "reason": "fewer-than-six-complete-feature-rows", "n": len(complete)}
    raw = np.asarray([[float(row[name]) for name in feature_names] for row in complete])
    centers = np.median(raw, axis=0)
    spread = np.median(np.abs(raw - centers), axis=0)
    spread[spread < 1e-8] = 1.0
    values = (raw - centers) / spread
    _, singular, vt = np.linalg.svd(values - np.mean(values, axis=0), full_matrices=False)
    coordinates = (values - np.mean(values, axis=0)) @ vt[: min(3, len(vt))].T
    variance = singular**2
    variance_ratio = variance / max(float(np.sum(variance)), 1e-12)
    rng = np.random.Generator(np.random.Philox(20260824))
    candidates: list[dict[str, Any]] = []
    labels_by_k: dict[int, np.ndarray] = {}
    for k in [int(value) for value in config["cluster_k_values"]]:
        if k >= len(values):
            continue
        labels = _kmeans(values, k, rng, starts=20)
        score = _silhouette(values, labels)
        labels_by_k[k] = labels
        candidates.append({"k": k, "silhouette": score})
    if not candidates:
        return {"stable": False, "reason": "no-valid-k", "n": len(complete)}
    chosen = max(candidates, key=lambda row: (row["silhouette"], -row["k"]))
    labels = labels_by_k[int(chosen["k"])]
    same_pairs = [
        (left, right)
        for left in range(len(labels))
        for right in range(left + 1, len(labels))
        if labels[left] == labels[right]
    ]
    coassign = np.zeros(len(same_pairs), dtype=float)
    replicates = int(config["cluster_bootstrap_replicates"])
    for _ in range(replicates):
        columns = rng.integers(0, values.shape[1], size=values.shape[1])
        boot_labels = _kmeans(values[:, columns], int(chosen["k"]), rng, starts=1)
        for index, (left, right) in enumerate(same_pairs):
            coassign[index] += float(boot_labels[left] == boot_labels[right])
    stability = float(np.mean(coassign / replicates)) if len(coassign) else 0.0
    stable = bool(
        float(chosen["silhouette"]) > float(config["cluster_silhouette_min"])
        and stability > float(config["cluster_coassignment_min"])
    )
    return {
        "stable": stable,
        "n": len(complete),
        "feature_names": feature_names,
        "candidate_k": candidates,
        "chosen_k": int(chosen["k"]),
        "silhouette": float(chosen["silhouette"]),
        "coassignment_stability": stability,
        "pca_variance_ratio": variance_ratio[:3].tolist(),
        "rows": [
            {
                "memory_task_id": row["memory_task_id"],
                "model_id": row["model_id"],
                "cluster": int(label),
                "pca": coordinate.tolist(),
            }
            for row, label, coordinate in zip(complete, labels, coordinates)
        ],
        "claim": "provisional exploratory clusters" if stable else "no stable mechanism clusters",
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.unlink(missing_ok=True)
    append_jsonl(path, rows)


def analyze_atlas(output: Path, final_status: str = "completed") -> dict[str, Any]:
    output = output.resolve()
    registration = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    config = registration["protocol"]
    upstream = Path(registration["upstream"]["root"])
    histories_list = list(read_jsonl(output / "histories.jsonl"))
    probes_list = list(read_jsonl(output / "probes.jsonl"))
    reinstatement_list = list(read_jsonl(output / "reinstatement.jsonl"))
    relearning_list = list(read_jsonl(output / "relearning.jsonl"))
    calibrations = list(read_jsonl(output / "calibration.jsonl"))
    histories = {(row["memory_task_id"], row["arm"]): row for row in histories_list}
    probes = {
        (row["memory_task_id"], row["arm"], row["probe"]): row
        for row in probes_list
    }
    reinstatement = {
        (row["memory_task_id"], row["arm"]): row for row in reinstatement_list
    }
    relearning = {(row["memory_task_id"], row["arm"]): row for row in relearning_list}
    tasks = list(config["fixed_cohort_task_ids"])
    memories: dict[str, MemoryData] = {}
    models: dict[str, int] = {}
    for task_id in tasks:
        released = load_released_task(upstream, task_id)
        memories[task_id] = load_memory(released.memory_path, MemoryKey.parse(task_id))
        models[task_id] = released.key.model_id

    observer_rows: list[dict[str, Any]] = []
    feature_vectors: dict[tuple[str, str], np.ndarray] = {}
    for task_id in tasks:
        memory = memories[task_id]
        for arm in ATLAS_ARMS:
            vector = _feature_vector(
                memory, task_id, arm, histories, probes, reinstatement, relearning
            )
            if vector is not None:
                feature_vectors[(task_id, arm)] = vector

    decoder, history_scores = _nearest_centroid_decoder(
        feature_vectors,
        models,
        ATLAS_ARMS,
        int(config["history_permutation_replicates"]),
    )

    for task_id in tasks:
        memory = memories[task_id]
        naive_history = histories.get((task_id, "naive"), {})
        trained_history = histories.get((task_id, "trained_no_reset"), {})
        naive_long = _checkpoint(naive_history, 62500.0)
        trained_long = _checkpoint(trained_history, 62500.0)
        naive_trajectory = _response_trajectory(naive_long)
        trained_trajectory = _response_trajectory(trained_long)
        naive_state = _state_y(naive_long)
        trained_state = _state_y(trained_long)
        response_scale = max(
            float(abs(memory.bounds[memory.key.response_id, 1] - memory.bounds[memory.key.response_id, 0])),
            1e-8,
        )
        naive_relearn = _relearning_summary(relearning.get((task_id, "naive")))
        trained_relearn = _relearning_summary(
            relearning.get((task_id, "trained_no_reset"))
        )
        expected_probe_names = sorted(
            name
            for (row_task, row_arm, name), row in probes.items()
            if row_task == task_id and row_arm == "naive" and bool(row.get("valid"))
        )
        naive_probe_vector = _probe_vector(
            memory, probes, task_id, "naive", expected_probe_names
        )
        trained_probe_vector = _probe_vector(
            memory, probes, task_id, "trained_no_reset", expected_probe_names
        )
        naive_responsiveness = _responsiveness(probes, task_id, "naive")
        for arm in ATLAS_ARMS:
            history = histories.get((task_id, arm), {})
            long_point = _checkpoint(history, 62500.0)
            trajectory = _response_trajectory(long_point)
            state = _state_y(long_point)
            trajectory_metrics = _ratio_distance(
                trajectory, naive_trajectory, trained_trajectory, response_scale
            )
            state_metrics = _ratio_distance(
                state,
                naive_state,
                trained_state,
                np.maximum(np.abs(memory.bounds[:, 1] - memory.bounds[:, 0]), 1e-8),
            )
            probe_vector = _probe_vector(
                memory, probes, task_id, arm, expected_probe_names
            )
            counterfactual_metrics = _ratio_distance(
                probe_vector, naive_probe_vector, trained_probe_vector, 1.0
            )
            checkpoint_verdicts: dict[str, Any] = {}
            for duration in CHECKPOINTS:
                point = _checkpoint(history, duration)
                checkpoint_verdicts[f"{duration:g}"] = (
                    None
                    if point is None
                    else {
                        "is_broken": bool(point["challenge"]["is_broken"]),
                        "reset_margin": float(point["challenge"]["reset_margin"]),
                        "learned_margin": float(point["challenge"]["learned_margin"]),
                    }
                )
            reset_fraction = None if trajectory is None else _reset_fraction(memory, trajectory)
            o_r = bool(long_point and long_point["challenge"]["is_broken"])
            ratio = float(config["observer_equivalence_ratio"])
            o_trajectory = bool(
                o_r
                and reset_fraction is not None
                and reset_fraction >= float(config["trajectory_nonlearned_fraction"])
                and trajectory_metrics["valid"]
                and float(trajectory_metrics["ratio"]) <= ratio
            )
            o_state = bool(
                o_trajectory
                and state_metrics["valid"]
                and float(state_metrics["ratio"]) <= ratio
            )
            o_counterfactual = bool(
                o_state
                and counterfactual_metrics["valid"]
                and float(counterfactual_metrics["ratio"]) <= ratio
            )
            arm_relearn = _relearning_summary(relearning.get((task_id, arm)))
            relearning_delta = None
            o_relearning = False
            savings = False
            if arm_relearn["valid"] and naive_relearn["valid"] and trained_relearn["valid"]:
                relearning_delta = float(arm_relearn["mean_margin"] - naive_relearn["mean_margin"])
                tolerance = float(config["savings_tolerance_ratio"]) * max(
                    abs(float(trained_relearn["mean_margin"] - naive_relearn["mean_margin"])),
                    1e-8,
                )
                savings = bool(
                    int(arm_relearn["first_learned_cycle"])
                    < int(naive_relearn["first_learned_cycle"])
                    or relearning_delta > tolerance
                )
                o_relearning = bool(o_counterfactual and not savings)
            reinstate = reinstatement.get((task_id, arm))
            reinstatement_margin = (
                float(reinstate["challenge"]["learned_margin"])
                if reinstate and reinstate.get("valid")
                else None
            )
            reinstatement_relapse = bool(
                reinstate
                and reinstate.get("valid")
                and not bool(reinstate["challenge"]["is_broken"])
            )
            responsiveness = _responsiveness(probes, task_id, arm)
            responsiveness_ratio = (
                None
                if responsiveness is None or naive_responsiveness is None
                else responsiveness / max(naive_responsiveness, 1e-12)
            )
            mandatory_probe_invalid = any(
                not bool(probes.get((task_id, arm, name), {}).get("valid"))
                for name in CORE_PROBES
            )
            dysfunctional = bool(
                long_point is None
                or mandatory_probe_invalid
                or responsiveness_ratio is None
                or responsiveness_ratio < float(config["responsiveness_floor_fraction"])
            )
            history_score = history_scores.get((task_id, arm))
            o_information = bool(
                o_relearning and history_score is not None and history_score <= 0.0
            )
            observer_rows.append(
                {
                    "task_id": f"observer|{task_id}|{arm}",
                    "memory_task_id": task_id,
                    "model_id": memory.key.model_id,
                    "arm": arm,
                    "checkpoint_verdicts": checkpoint_verdicts,
                    "long_reset_margin": None
                    if long_point is None
                    else float(long_point["challenge"]["reset_margin"]),
                    "trajectory_reset_fraction": reset_fraction,
                    "trajectory_distance_ratio": trajectory_metrics.get("ratio"),
                    "trajectory_nearest": trajectory_metrics.get("nearest"),
                    "state_distance_ratio": state_metrics.get("ratio"),
                    "state_nearest": state_metrics.get("nearest"),
                    "counterfactual_distance_ratio": counterfactual_metrics.get("ratio"),
                    "counterfactual_nearest": counterfactual_metrics.get("nearest"),
                    "counterfactual_probe_count": len(expected_probe_names),
                    "relearning_first_cycle": arm_relearn["first_learned_cycle"],
                    "relearning_mean_margin": arm_relearn["mean_margin"],
                    "relearning_margin_delta": relearning_delta,
                    "savings": savings,
                    "reinstatement_learned_margin": reinstatement_margin,
                    "reinstatement_relapse": reinstatement_relapse,
                    "responsiveness_ratio": responsiveness_ratio,
                    "history_score": history_score,
                    "dysfunctional": dysfunctional,
                    "o_r": o_r,
                    "o_trajectory": o_trajectory,
                    "o_state": o_state,
                    "o_counterfactual": o_counterfactual,
                    "o_relearning": o_relearning,
                    "o_information": o_information,
                    "valid": not dysfunctional,
                }
            )

    observer_lookup = {
        (row["memory_task_id"], row["arm"]): row for row in observer_rows
    }
    mechanism_rows: list[dict[str, Any]] = []
    for task_id in tasks:
        combined = observer_lookup[(task_id, "combined_reset")]
        control = observer_lookup[(task_id, "control_only")]
        combined_probe = _probe_vector(memories[task_id], probes, task_id, "combined_reset", sorted(
            name for (row_task, row_arm, name), row in probes.items()
            if row_task == task_id and row_arm == "naive" and bool(row.get("valid"))
        ))
        control_probe = _probe_vector(memories[task_id], probes, task_id, "control_only", sorted(
            name for (row_task, row_arm, name), row in probes.items()
            if row_task == task_id and row_arm == "naive" and bool(row.get("valid"))
        ))
        naive_probe = _probe_vector(memories[task_id], probes, task_id, "naive", sorted(
            name for (row_task, row_arm, name), row in probes.items()
            if row_task == task_id and row_arm == "naive" and bool(row.get("valid"))
        ))
        trained_probe = _probe_vector(memories[task_id], probes, task_id, "trained_no_reset", sorted(
            name for (row_task, row_arm, name), row in probes.items()
            if row_task == task_id and row_arm == "naive" and bool(row.get("valid"))
        ))
        combined_control = _ratio_distance(
            combined_probe, control_probe, trained_probe, 1.0
        )
        reference_separation = (
            float(np.linalg.norm(naive_probe - trained_probe) / math.sqrt(len(naive_probe)))
            if naive_probe is not None and trained_probe is not None and len(naive_probe) == len(trained_probe)
            else None
        )
        combined_control_ratio = (
            None
            if not combined_control["valid"] or reference_separation is None
            else float(combined_control["to_naive"] / max(reference_separation, 1e-12))
        )
        verdict_match = all(
            combined["checkpoint_verdicts"].get(f"{duration:g}") is not None
            and control["checkpoint_verdicts"].get(f"{duration:g}") is not None
            and combined["checkpoint_verdicts"][f"{duration:g}"]["is_broken"]
            == control["checkpoint_verdicts"][f"{duration:g}"]["is_broken"]
            for duration in CHECKPOINTS
        )
        generic = bool(
            verdict_match
            and combined_control_ratio is not None
            and combined_control_ratio <= float(config["observer_equivalence_ratio"])
        )
        immediate = combined["checkpoint_verdicts"].get("0")
        later = [combined["checkpoint_verdicts"].get(f"{value:g}") for value in CHECKPOINTS[1:]]
        suppression = bool(
            immediate
            and immediate["is_broken"]
            and any(point and not point["is_broken"] for point in later)
        )
        durable = bool(combined["o_r"])
        naive_like = bool(
            combined["o_information"]
            and not combined["reinstatement_relapse"]
            and not combined["dysfunctional"]
        )
        rehoming = bool(
            durable
            and not naive_like
            and (
                combined["state_nearest"] != "naive"
                or combined["counterfactual_nearest"] != "naive"
                or (combined["history_score"] is not None and combined["history_score"] > 0)
            )
        )
        if combined["dysfunctional"]:
            label = "invalid-or-dysfunctional"
        elif suppression:
            label = "temporary-suppression"
        elif naive_like:
            label = "naive-like-reversion-candidate"
        elif durable and combined["savings"]:
            label = "extinction-with-savings"
        elif rehoming:
            label = "rehoming"
        elif durable:
            label = "persistent-operational-reset-indeterminate"
        else:
            label = "no-durable-reset"
        mechanism_rows.append(
            {
                "task_id": f"mechanism|{task_id}",
                "memory_task_id": task_id,
                "model_id": models[task_id],
                "primary_label": label,
                "durable_operational_reset": durable,
                "temporary_suppression": suppression,
                "naive_like_reversion_candidate": naive_like,
                "extinction_with_savings": bool(durable and combined["savings"]),
                "rehoming": rehoming,
                "generic_perturbation_candidate": generic,
                "dysfunctional": bool(combined["dysfunctional"]),
                "combined_control_verdict_match": verdict_match,
                "combined_control_counterfactual_ratio": combined_control_ratio,
                **{
                    key: combined.get(key)
                    for key in (
                        "long_reset_margin",
                        "trajectory_distance_ratio",
                        "state_distance_ratio",
                        "counterfactual_distance_ratio",
                        "relearning_margin_delta",
                        "reinstatement_learned_margin",
                        "responsiveness_ratio",
                        "history_score",
                    )
                },
            }
        )

    _write_jsonl(output / "observer-scores.jsonl", observer_rows)
    _write_jsonl(output / "mechanism-labels.jsonl", mechanism_rows)
    write_json(output / "history-decoder.json", decoder)
    clusters = _cluster_atlas(mechanism_rows, config)
    write_json(output / "clusters.json", clusters)

    hypotheses = [
        ("functional-reversion", "naive_like_reversion_candidate", "Richer observers remain naive-like and relearning shows no savings."),
        ("extinction-with-savings", "extinction_with_savings", "Reset states reacquire the learned response faster than paired naive states."),
        ("generic-perturbation", "generic_perturbation_candidate", "Control-only and combined histories remain counterfactually interchangeable."),
        ("rehoming", "rehoming", "Response-level resets occupy a stable state distinguishable from both naive and trained references."),
        ("temporary-suppression", "temporary_suppression", "The learned response relapses with time or UCS reinstatement."),
        ("damage-or-instability", "dysfunctional", "Apparent reset co-occurs with numerical failure or collapsed probe responsiveness."),
    ]
    hypothesis_rows: list[dict[str, Any]] = []
    total_models = len(set(models.values()))
    for name, field, prediction in hypotheses:
        supporting = [row for row in mechanism_rows if bool(row[field])]
        model_count = len({row["model_id"] for row in supporting})
        prevalence = len(supporting) / max(len(mechanism_rows), 1)
        score = prevalence * model_count / max(total_models, 1)
        hypothesis_rows.append(
            {
                "hypothesis": name,
                "supporting_memory_count": len(supporting),
                "supporting_model_count": model_count,
                "memory_prevalence": prevalence,
                "cross_model_rank_score": score,
                "falsifiable_next_prediction": prediction,
            }
        )
    hypothesis_rows.sort(
        key=lambda row: (-row["cross_model_rank_score"], row["hypothesis"])
    )
    for rank, row in enumerate(hypothesis_rows, 1):
        row["rank"] = rank
    hypothesis_ledger = {
        "scope": "exploratory-hypothesis-generation",
        "ranking": hypothesis_rows,
        "not_confirmatory": True,
    }
    write_json(output / "hypotheses.json", hypothesis_ledger)

    ladder: dict[str, Any] = {}
    combined_rows = [row for row in observer_rows if row["arm"] == "combined_reset"]
    for observer in (
        "o_r",
        "o_trajectory",
        "o_state",
        "o_counterfactual",
        "o_relearning",
        "o_information",
    ):
        eligible = [row for row in combined_rows if row.get(observer) is not None]
        passed = [row for row in eligible if bool(row[observer])]
        ladder[observer] = {
            "n": len(eligible),
            "pass_count": len(passed),
            "memory_rate": len(passed) / len(eligible) if eligible else None,
            "model_count": len({row["model_id"] for row in passed}),
        }
    sensitivity: dict[str, Any] = {}
    for threshold in [float(value) for value in config["observer_equivalence_sensitivity"]]:
        passes = [
            row
            for row in combined_rows
            if row["o_r"]
            and row["trajectory_reset_fraction"] is not None
            and row["trajectory_reset_fraction"] >= float(config["trajectory_nonlearned_fraction"])
            and all(
                row.get(field) is not None and float(row[field]) <= threshold
                for field in (
                    "trajectory_distance_ratio",
                    "state_distance_ratio",
                    "counterfactual_distance_ratio",
                )
            )
        ]
        sensitivity[str(threshold)] = {
            "pass_count": len(passes),
            "memory_rate": len(passes) / len(combined_rows) if combined_rows else None,
        }
    valid_mechanisms = [row for row in mechanism_rows if not row["dysfunctional"]]
    completed_memories = len(
        {
            row["memory_task_id"]
            for row in observer_rows
            if row["arm"] == "combined_reset" and row["valid"]
        }
    )
    completed_models = len(
        {
            row["model_id"]
            for row in observer_rows
            if row["arm"] == "combined_reset" and row["valid"]
        }
    )
    minimum_pass = bool(
        completed_memories >= int(config["minimum_complete_memories"])
        and completed_models >= int(config["minimum_complete_models"])
    )
    result = {
        "run_status": final_status,
        "scope": "exploratory-hypothesis-generation",
        "cohort_size": len(tasks),
        "completed_combined_memory_count": completed_memories,
        "completed_combined_model_count": completed_models,
        "minimum_completion_gate": minimum_pass,
        "record_counts": {
            "calibration": len(calibrations),
            "histories": len(histories_list),
            "probes": len(probes_list),
            "reinstatement": len(reinstatement_list),
            "relearning": len(relearning_list),
        },
        "observer_ladder": ladder,
        "equivalence_sensitivity": sensitivity,
        "mechanism_label_counts": {
            label: sum(row["primary_label"] == label for row in mechanism_rows)
            for label in sorted({row["primary_label"] for row in mechanism_rows})
        },
        "valid_mechanism_count": len(valid_mechanisms),
        "history_decoder": decoder,
        "cluster_stable": bool(clusters.get("stable")),
        "top_hypothesis": hypothesis_rows[0] if hypothesis_rows else None,
        "claim_boundary": (
            "Exploratory in-silico mechanism hypotheses only; no confirmed erasure, "
            "plastic-heredity, biological-safety, agency, or clinical claim."
        ),
    }
    write_json(output / "analysis.json", result)
    lines = [
        "# Observer Atlas V1 report",
        "",
        f"**Run status:** `{final_status}`  ",
        f"**Minimum completion gate:** `{'PASS' if minimum_pass else 'FAIL'}`  ",
        f"**Complete combined-reset profiles:** {completed_memories} memories across {completed_models} BioModels",
        "",
        "## Observer ladder",
        "",
    ]
    for name, summary in ladder.items():
        rate = summary["memory_rate"]
        rendered = "n/a" if rate is None else f"{100 * rate:.1f}% ({summary['pass_count']}/{summary['n']})"
        lines.append(f"- `{name}`: {rendered}; {summary['model_count']} supporting BioModels.")
    lines.extend(["", "## Mechanism labels", ""])
    for label, count in result["mechanism_label_counts"].items():
        lines.append(f"- `{label}`: {count}")
    lines.extend(["", "## Ranked hypotheses", ""])
    for row in hypothesis_rows:
        lines.append(
            f"{row['rank']}. **{row['hypothesis']}** — {row['supporting_memory_count']} memories / "
            f"{row['supporting_model_count']} BioModels. Next prediction: {row['falsifiable_next_prediction']}"
        )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            result["claim_boundary"],
            "Rates, decoder permutations, and clusters are descriptive tools for choosing the next experiment, not confirmatory evidence.",
            "",
        ]
    )
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return result
