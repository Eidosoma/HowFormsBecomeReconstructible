"""Cross-fitted structural predictor of interpreter edge vulnerability."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

from .artifacts import canonical_digest, read_json
from .local_ph_dynamics import structural_mask
from .wagner import WagnerRulebook
from .wagner_ph_architecture_config import ArchitectureSpec
from .wagner_ph_cooption_config import QuantizedCarrierGenome
from .wagner_ph_cooption_experiment import local_carrier
from .wagner_ph_depth_mechanisms import edge_features


BASE_FEATURES = (
    "absolute_weight_rank",
    "source_absolute_output_rank",
    "target_absolute_input_rank",
    "self_edge",
    "source_is_carrier_locus",
    "target_is_carrier_locus",
    "both_endpoints_are_carrier_loci",
)
PAIR_FEATURES = tuple(f"{BASE_FEATURES[a]}*{BASE_FEATURES[b]}" for a, b in combinations(range(len(BASE_FEATURES)), 2))
FEATURE_NAMES = ("intercept",) + BASE_FEATURES + PAIR_FEATURES


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    result = np.empty(len(values), dtype=float)
    result[order] = np.arange(len(values), dtype=float)
    return result / max(1, len(values) - 1)


def structural_feature_matrix(rulebook: WagnerRulebook, carrier_mask: tuple[int, ...] | list[int]) -> np.ndarray:
    rows = []
    raw = []
    mask = tuple(int(value) for value in carrier_mask)
    for edge_index in range(rulebook.weights.size):
        target, source = divmod(edge_index, rulebook.genes)
        value = edge_features(rulebook, mask, target, source)
        raw.append(value)
    continuous = np.asarray([
        [value["absolute_weight"], value["source_absolute_output"], value["target_absolute_input"]]
        for value in raw
    ], dtype=float)
    ranked = np.column_stack([_ranks(continuous[:, column]) for column in range(continuous.shape[1])])
    for index, value in enumerate(raw):
        base = [
            *ranked[index].tolist(),
            float(value["self_edge"]),
            float(value["source_is_carrier_locus"]),
            float(value["target_is_carrier_locus"]),
            float(value["both_endpoints_are_carrier_loci"]),
        ]
        interactions = [base[a] * base[b] for a, b in combinations(range(len(base)), 2)]
        rows.append([1.0, *base, *interactions])
    return np.asarray(rows, dtype=float)


def _ridge(x: np.ndarray, y: np.ndarray, penalty: float) -> np.ndarray:
    regularizer = np.eye(x.shape[1], dtype=float) * penalty
    regularizer[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + regularizer, x.T @ y)


def _rank_correlation(left: np.ndarray, right: np.ndarray) -> float | None:
    if np.all(left == left[0]) or np.all(right == right[0]):
        return None
    a, b = _ranks(left), _ranks(right)
    value = float(np.corrcoef(a, b)[0, 1])
    return value if np.isfinite(value) else None


def fit_cross_fitted_predictor(reference: Path, spec: ArchitectureSpec) -> dict[str, Any]:
    """Fit task-excluding development models and one historical-only fresh model."""

    records: list[dict[str, Any]] = []
    for path in sorted((reference / "atlas" / "tasks").glob("task-*.json")):
        task = read_json(path)
        for root in task["roots"]:
            rulebook = WagnerRulebook.from_dict(root["genotype"]["rulebook"])
            matrix = structural_feature_matrix(rulebook, root["carrier_mask"])
            reset = sorted(
                (row for row in root["rows"] if row["operation"] == "reset"),
                key=lambda value: int(value["edge_index"]),
            )
            if len(reset) != rulebook.weights.size:
                raise ValueError("atlas reset rows do not cover every edge")
            for row, features in zip(reset, matrix):
                records.append({
                    "task_index": int(task["task_index"]),
                    "root_index": int(root["root_index"]),
                    "edge_index": int(row["edge_index"]),
                    "features": features,
                    "damage": max(0.0, -float(row["delta"]["information_high"])),
                })
    if not records:
        raise ValueError("sealed atlas contains no reset records")
    x = np.stack([value["features"] for value in records])
    y = np.asarray([value["damage"] for value in records], dtype=float)
    tasks = np.asarray([value["task_index"] for value in records], dtype=int)
    coefficients: dict[str, Any] = {}
    predictions = np.zeros(len(records), dtype=float)
    fold_membership: dict[str, Any] = {}
    historical_tasks = sorted(set(tasks.tolist()))
    for task_index in range(spec.task_count):
        heldout = tasks == task_index
        training = ~heldout
        if not np.any(heldout) or not np.any(training):
            raise ValueError("cross-fitted predictor lacks a complete held-out task")
        beta = _ridge(x[training], y[training], spec.predictor_ridge)
        coefficients[str(task_index)] = beta.tolist()
        predictions[heldout] = x[heldout] @ beta
        fold_membership[str(task_index)] = {
            "heldout_task": task_index,
            "training_tasks": [value for value in historical_tasks if value != task_index],
        }
    all_beta = _ridge(x, y, spec.predictor_ridge)
    root_metrics = []
    for task_index in range(spec.task_count):
        for root_index in sorted({value["root_index"] for value in records if value["task_index"] == task_index}):
            indices = np.asarray([
                index for index, value in enumerate(records)
                if value["task_index"] == task_index and value["root_index"] == root_index
            ], dtype=int)
            observed, predicted = y[indices], predictions[indices]
            total = float(np.sum(observed))
            top = indices[np.argsort(predicted)[-spec.predictor_top_k:]]
            root_metrics.append({
                "task_index": task_index,
                "root_index": root_index,
                "rank_correlation": _rank_correlation(predicted, observed),
                "top_k_damage_capture": float(np.sum(y[top]) / total) if total > 0.0 else None,
                "positive_damage_rate": float(np.mean(observed > 0.0)),
            })
    valid_correlations = [value["rank_correlation"] for value in root_metrics if value["rank_correlation"] is not None]
    valid_capture = [value["top_k_damage_capture"] for value in root_metrics if value["top_k_damage_capture"] is not None]
    result = {
        "format": "gre-wagner-ph-interpreter-architecture-v1-cross-fitted-predictor",
        "target": "max(0, -delta_information_high)",
        "atlas_operation": "reset",
        "feature_names": list(FEATURE_NAMES),
        "ridge_penalty": spec.predictor_ridge,
        "top_k": spec.predictor_top_k,
        "development_coefficients_by_heldout_task": coefficients,
        "fresh_coefficients_fit_historical_tasks_only": all_beta.tolist(),
        "fold_membership": fold_membership,
        "historical_tasks": historical_tasks,
        "root_metrics": root_metrics,
        "mean_rank_correlation": float(np.mean(valid_correlations)) if valid_correlations else None,
        "mean_top_k_damage_capture": float(np.mean(valid_capture)) if valid_capture else None,
        "random_top_k_expectation": spec.predictor_top_k / 100.0,
        "predictor_quality_never_cancels_a_registered_arm": True,
    }
    result["predictor_digest"] = canonical_digest(result)
    return result


def predicted_edge_ranking(
    rulebook: WagnerRulebook,
    carrier: QuantizedCarrierGenome,
    predictor: dict[str, Any],
    task_index: int,
    phase: str,
) -> dict[str, Any]:
    mask = structural_mask(rulebook, local_carrier(carrier))
    matrix = structural_feature_matrix(rulebook, mask)
    if phase == "development":
        coefficients = predictor["development_coefficients_by_heldout_task"][str(task_index)]
        training_tasks = predictor["fold_membership"][str(task_index)]["training_tasks"]
    else:
        coefficients = predictor["fresh_coefficients_fit_historical_tasks_only"]
        training_tasks = predictor["historical_tasks"]
    scores = matrix @ np.asarray(coefficients, dtype=float)
    order = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    return {
        "carrier_mask": list(mask),
        "edge_scores": scores.tolist(),
        "ranking": order,
        "top_edges": order[: int(predictor["top_k"])],
        "training_tasks": list(training_tasks),
        "target_task_excluded": phase != "development" or task_index not in training_tasks,
    }


def verify_predictor(predictor: dict[str, Any]) -> dict[str, Any]:
    payload = dict(predictor)
    archived = payload.pop("predictor_digest", None)
    if archived != canonical_digest(payload):
        raise ValueError("architecture predictor digest mismatch")
    if tuple(predictor["feature_names"]) != FEATURE_NAMES:
        raise ValueError("architecture predictor feature contract changed")
    if int(predictor["top_k"]) <= 0:
        raise ValueError("architecture predictor top-k is invalid")
    coefficient_count = len(FEATURE_NAMES)
    coefficient_sets = list(
        predictor["development_coefficients_by_heldout_task"].values()
    ) + [predictor["fresh_coefficients_fit_historical_tasks_only"]]
    if any(len(values) != coefficient_count for values in coefficient_sets):
        raise ValueError("architecture predictor coefficient shape mismatch")
    return {
        "verified": True,
        "predictor_digest": archived,
        "development_folds": len(
            predictor["development_coefficients_by_heldout_task"]
        ),
    }


__all__ = (
    "FEATURE_NAMES",
    "fit_cross_fitted_predictor",
    "predicted_edge_ranking",
    "structural_feature_matrix",
    "verify_predictor",
)
