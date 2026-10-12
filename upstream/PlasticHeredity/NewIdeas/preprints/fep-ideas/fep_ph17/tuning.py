from __future__ import annotations

from typing import Any

import numpy as np

from .causal_model import TrainingData
from .config import (
    EPISTEMIC_GRID,
    EPISTEMIC_MAX_SHAM_SHIFT,
    EPISTEMIC_MIN_ENTROPY_GAP,
    EPISTEMIC_MIN_INFORMATION_UPLIFT,
    EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL,
    ExperimentConfig,
)
from .hybrid_model import (
    HybridModel,
    entropy,
    expected_regime_information,
    transformed_training,
    uniform_weights,
)
from .types import Action


def _softmax(values: np.ndarray, precision: float) -> np.ndarray:
    scores = precision * np.asarray(values, dtype=np.float64)
    scores -= float(np.max(scores))
    weights = np.exp(scores)
    return weights / float(weights.sum())


def tuning_row_eligible(row: dict[str, Any]) -> bool:
    """Apply the frozen v2 information-specific activation rule."""

    lower, upper = EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL
    return bool(
        lower <= row["pooled_informative_sample_probability"] <= upper
        and row["informative_minus_sham_sample_probability"]
        >= EPISTEMIC_MIN_INFORMATION_UPLIFT
        and row["high_minus_low_informative_sample_probability"]
        >= EPISTEMIC_MIN_ENTROPY_GAP
        and row["sham_shift_from_pragmatic"] <= EPISTEMIC_MAX_SHAM_SHIFT
    )


def _sample_probabilities(
    pragmatic: np.ndarray, information: np.ndarray, coefficient: float, precision: float
) -> np.ndarray:
    scores = precision * (pragmatic + float(coefficient) * information)
    scores -= np.max(scores, axis=1, keepdims=True)
    weights = np.exp(scores)
    probabilities = weights / np.sum(weights, axis=1, keepdims=True)
    return probabilities[:, int(Action.SAMPLE)]


def select_epistemic_coefficient(
    config: ExperimentConfig, model: HybridModel, data: TrainingData
) -> dict[str, Any]:
    """Select only from development behavior; no evaluation stream is touched."""

    model.validate()
    features, _targets = transformed_training(data, model.projection)
    beliefs = np.asarray(data.rich_features[:, 109:112], dtype=np.float64)
    if beliefs.shape[1] != 3:
        raise ValueError("development feature layout lacks a three-state regime belief")
    if len(features) > 1_024:
        positions = np.linspace(0, len(features) - 1, 1_024, dtype=np.int64)
        features = features[positions]
        beliefs = beliefs[positions]
    weights = uniform_weights(model)
    entropies = np.asarray([entropy(value) for value in beliefs])
    maximum = np.log(3.0)
    high = entropies >= 0.65 * maximum
    low = entropies <= 0.35 * maximum
    if not np.any(high) or not np.any(low):
        median = float(np.median(entropies))
        high = entropies >= median
        low = entropies < median
    pragmatic_scores = np.empty((len(features), 4), dtype=np.float64)
    informative_information = np.empty_like(pragmatic_scores)
    sham_information = np.empty_like(pragmatic_scores)
    for row_index, (feature, belief) in enumerate(zip(features, beliefs, strict=True)):
        for action in range(4):
            prediction = model.predict_features(feature, action)
            mean = prediction.mean(weights)
            variance = float(
                np.dot(weights, (prediction.members[:, 0] - mean[0]) ** 2)
            )
            cost = (
                config.action_cost_sample
                if action == int(Action.SAMPLE)
                else config.action_cost_uptake
                if action in (int(Action.ADAPT_A), int(Action.ADAPT_B))
                else 0.0
            )
            pragmatic_scores[row_index, action] = (
                float(mean[0])
                - config.action_cost_weight * cost
                - config.risk_coefficient * np.sqrt(max(0.0, variance))
            )
            informative_accuracy = (
                config.informative_sample_accuracy
                if action == int(Action.SAMPLE)
                else config.passive_cue_accuracy
            )
            sham_accuracy = (
                config.sham_sample_accuracy
                if action == int(Action.SAMPLE)
                else config.passive_cue_accuracy
            )
            informative_information[row_index, action] = expected_regime_information(
                belief, 0.25, 0.05, informative_accuracy
            )
            sham_information[row_index, action] = expected_regime_information(
                belief, 0.25, 0.05, sham_accuracy
            )

    pragmatic_values = _sample_probabilities(
        pragmatic_scores, sham_information, 0.0, config.policy_precision
    )
    pragmatic_pooled = float(np.mean(pragmatic_values))
    pragmatic_high = float(np.mean(pragmatic_values[high])) if np.any(high) else 0.0
    pragmatic_low = float(np.mean(pragmatic_values[low])) if np.any(low) else 0.0

    rows: list[dict[str, Any]] = []
    for coefficient in EPISTEMIC_GRID:
        informative_values = _sample_probabilities(
            pragmatic_scores,
            informative_information,
            coefficient,
            config.policy_precision,
        )
        sham_values = _sample_probabilities(
            pragmatic_scores, sham_information, coefficient, config.policy_precision
        )
        high_rate = (
            float(np.mean(informative_values[high])) if np.any(high) else 0.0
        )
        low_rate = (
            float(np.mean(informative_values[low])) if np.any(low) else 0.0
        )
        pooled_rate = float(np.mean(informative_values))
        sham_rate = float(np.mean(sham_values))
        ratio = high_rate / max(low_rate, 1.0e-9)
        row = {
            "coefficient": float(coefficient),
            "high_entropy_sample_probability": high_rate,
            "low_entropy_sample_probability": low_rate,
            "high_to_low_ratio": ratio,
            "pooled_informative_sample_probability": pooled_rate,
            "pooled_sham_sample_probability": sham_rate,
            "informative_minus_sham_sample_probability": pooled_rate - sham_rate,
            "high_minus_low_informative_sample_probability": high_rate - low_rate,
            "sham_shift_from_pragmatic": abs(sham_rate - pragmatic_pooled),
        }
        row["eligible"] = tuning_row_eligible(row)
        rows.append(row)
    eligible_rows = [row for row in rows if row["eligible"]]
    selected = (
        min(eligible_rows, key=lambda row: row["coefficient"])
        if eligible_rows
        else min(
            rows,
            key=lambda row: (
                abs(row["pooled_informative_sample_probability"] - 0.55)
                + max(
                    0.0,
                    EPISTEMIC_MIN_INFORMATION_UPLIFT
                    - row["informative_minus_sham_sample_probability"],
                )
                + max(
                    0.0,
                    EPISTEMIC_MIN_ENTROPY_GAP
                    - row["high_minus_low_informative_sample_probability"],
                ),
                row["coefficient"],
            ),
        )
    )
    return {
        "schema": "fep-ph17-epistemic-tuning-v2",
        "selection_uses_evaluation_outcomes": False,
        "selection_uses_counterfactual_sham_observation_kernel": True,
        "rows_evaluated": int(len(features)),
        "high_entropy_rows": int(np.count_nonzero(high)),
        "low_entropy_rows": int(np.count_nonzero(low)),
        "pragmatic_sample_probability": {
            "pooled": pragmatic_pooled,
            "high_entropy": pragmatic_high,
            "low_entropy": pragmatic_low,
        },
        "eligibility_rule": {
            "informative_sample_probability_interval": list(
                EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL
            ),
            "minimum_informative_minus_sham": EPISTEMIC_MIN_INFORMATION_UPLIFT,
            "minimum_high_minus_low_informative": EPISTEMIC_MIN_ENTROPY_GAP,
            "maximum_sham_shift_from_pragmatic": EPISTEMIC_MAX_SHAM_SHIFT,
        },
        "grid": rows,
        "eligible": bool(eligible_rows),
        "selected_coefficient": float(selected["coefficient"]),
    }
