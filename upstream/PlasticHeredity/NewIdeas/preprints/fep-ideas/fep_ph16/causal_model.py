from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import canonical_json_bytes, sha256_bytes
from fep_ph1.types import RawObservation

from .state import BodyState, composition_clr, normalized_entropy
from .types import Action, ConditionSpec


BASE_TARGETS = 12
CLR_TARGETS = 100
SHUFFLED_ACTIONS = np.asarray((1, 3, 0, 2), dtype=np.int8)
EPSILON = 1.0e-8


@dataclass(frozen=True)
class TrainingData:
    matrix_ids: NDArray[np.int32]
    actions: NDArray[np.int8]
    coarse_features: NDArray[np.float64]
    rich_features: NDArray[np.float64]
    coarse_targets: NDArray[np.float64]
    rich_targets: NDArray[np.float64]

    def validate(self) -> None:
        count = len(self.matrix_ids)
        if self.actions.shape != (count,):
            raise ValueError("training action shape does not match matrix IDs")
        if any(value.shape[0] != count for value in (
            self.coarse_features, self.rich_features,
            self.coarse_targets, self.rich_targets,
        )):
            raise ValueError("training arrays have different row counts")
        if self.coarse_targets.shape[1] != BASE_TARGETS:
            raise ValueError("coarse target width is invalid")
        if self.rich_targets.shape[1] != BASE_TARGETS + CLR_TARGETS:
            raise ValueError("rich target width is invalid")
        if np.any((self.actions < 0) | (self.actions > 3)):
            raise ValueError("training action is outside the four-action alphabet")
        if any(not np.all(np.isfinite(value)) for value in (
            self.coarse_features, self.rich_features,
            self.coarse_targets, self.rich_targets,
        )):
            raise ValueError("training data contain non-finite values")


@dataclass(frozen=True)
class EnsemblePrediction:
    members: NDArray[np.float64]
    residual_variance: NDArray[np.float64]

    def mean(self, weights: NDArray[np.floating]) -> NDArray[np.float64]:
        values = np.asarray(weights, dtype=np.float64)
        values = values / float(values.sum())
        return np.einsum("m,mt->t", values, self.members)


@dataclass(frozen=True)
class CausalEnsemble:
    rich: bool
    ridge_lambda: float
    feature_mean: NDArray[np.float64]
    feature_scale: NDArray[np.float64]
    coefficients: NDArray[np.float64]
    residual_variance: NDArray[np.float64]
    cross_validation: dict[str, float]

    @property
    def members(self) -> int:
        return int(self.coefficients.shape[0])

    @property
    def target_width(self) -> int:
        return BASE_TARGETS + (CLR_TARGETS if self.rich else 0)

    @property
    def feature_width(self) -> int:
        return int(self.feature_mean.shape[1])

    def validate(self) -> None:
        if (
            self.feature_mean.ndim != 2
            or self.feature_mean.shape[0] != self.members
            or self.feature_scale.shape != self.feature_mean.shape
        ):
            raise ValueError("causal model feature scaler is invalid")
        expected = (
            self.members,
            4,
            self.feature_width + 1,
            self.target_width,
        )
        if self.coefficients.shape != expected:
            raise ValueError(f"causal coefficient shape {self.coefficients.shape} != {expected}")
        if self.residual_variance.shape != (self.members, 4, self.target_width):
            raise ValueError("causal residual-variance shape is invalid")
        if np.any(self.feature_scale <= 0.0) or np.any(self.residual_variance <= 0.0):
            raise ValueError("causal model scales and variances must be positive")
        if not np.all(np.isfinite(self.coefficients)):
            raise ValueError("causal model has non-finite coefficients")

    def predict(
        self,
        features: NDArray[np.floating],
        action: int,
        *,
        offsets: NDArray[np.floating] | None = None,
        shuffled_actions: bool = False,
    ) -> EnsemblePrediction:
        self.validate()
        values = np.asarray(features, dtype=np.float64)
        if values.shape != (self.feature_width,):
            raise ValueError("causal feature vector has wrong shape")
        model_action = int(SHUFFLED_ACTIONS[int(action)]) if shuffled_actions else int(action)
        standardized = (values - self.feature_mean) / self.feature_scale
        design = np.column_stack((np.ones(self.members, dtype=np.float64), standardized))
        raw = np.einsum(
            "md,mdt->mt", design, self.coefficients[:, model_action]
        )
        if offsets is not None:
            adjustment = np.asarray(offsets, dtype=np.float64)
            if adjustment.shape != (4, 5):
                raise ValueError("calibration offsets must have shape (4, 5)")
            raw[:, :5] += adjustment[int(action)]
        members = _constrain_predictions(raw, self.rich)
        return EnsemblePrediction(members, self.residual_variance[:, model_action].copy())


def _normalize_rows(values: NDArray[np.float64]) -> NDArray[np.float64]:
    clipped = np.clip(values, EPSILON, 1.0)
    return clipped / clipped.sum(axis=1, keepdims=True)


def _constrain_predictions(raw: NDArray[np.float64], rich: bool) -> NDArray[np.float64]:
    output = np.asarray(raw, dtype=np.float64).copy()
    output[:, 0] = np.clip(output[:, 0], EPSILON, 1.0 - EPSILON)
    output[:, 1] = np.clip(output[:, 1], 0.0, 1.5)
    output[:, 2:4] = np.clip(output[:, 2:4], 0.0, 1.0)
    output[:, 4] = np.clip(output[:, 4], 0.0, 1.5)
    output[:, 5:9] = _normalize_rows(output[:, 5:9])
    output[:, 9:12] = _normalize_rows(output[:, 9:12])
    if rich:
        output[:, BASE_TARGETS:] -= output[:, BASE_TARGETS:].mean(axis=1, keepdims=True)
    return output


def transition_target(
    composition: NDArray[np.integer],
    raw: RawObservation,
    completed: bool,
    true_regime: int,
    growth_budget: int,
    *,
    rich: bool,
) -> NDArray[np.float64]:
    cue = np.zeros(4, dtype=np.float64)
    cue[int(raw.cue)] = 1.0
    regime = np.zeros(3, dtype=np.float64)
    regime[int(true_regime)] = 1.0
    base = np.concatenate(
        (
            np.asarray(
                (
                    float(completed),
                    float(np.log1p(max(0, raw.growth_steps)) / np.log1p(growth_budget)),
                    float(raw.boundary_similarity),
                    float(raw.alignment_score),
                    float(np.asarray(composition).sum() / 80.0),
                ),
                dtype=np.float64,
            ),
            cue,
            regime,
        )
    )
    return np.concatenate((base, composition_clr(composition))) if rich else base


def _ridge(
    features: NDArray[np.float64], targets: NDArray[np.float64], ridge_lambda: float
) -> NDArray[np.float64]:
    design = np.column_stack((np.ones(len(features), dtype=np.float64), features))
    gram = design.T @ design
    penalty = np.eye(gram.shape[0], dtype=np.float64) * float(ridge_lambda)
    penalty[0, 0] = 0.0
    try:
        return np.linalg.solve(gram + penalty, design.T @ targets)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(gram + penalty, rcond=1.0e-12) @ design.T @ targets


def _fit_action_models(
    features: NDArray[np.float64],
    targets: NDArray[np.float64],
    actions: NDArray[np.int8],
    ridge_lambda: float,
) -> NDArray[np.float64]:
    output = np.empty((4, features.shape[1] + 1, targets.shape[1]), dtype=np.float64)
    for action in range(4):
        mask = actions == action
        if not np.any(mask):
            raise ValueError(f"development corpus contains no action {action}")
        output[action] = _ridge(features[mask], targets[mask], ridge_lambda)
    return output


def _raw_predict(
    features: NDArray[np.float64], actions: NDArray[np.int8], coefficients: NDArray[np.float64]
) -> NDArray[np.float64]:
    design = np.column_stack((np.ones(len(features), dtype=np.float64), features))
    output = np.empty((len(features), coefficients.shape[-1]), dtype=np.float64)
    for action in range(4):
        mask = actions == action
        if np.any(mask):
            output[mask] = design[mask] @ coefficients[action]
    return output


def _prediction_loss(
    expected: NDArray[np.float64], predicted: NDArray[np.float64], rich: bool
) -> float:
    constrained = _constrain_predictions(predicted, rich)
    biological_scale = np.var(expected[:, :5], axis=0) + 0.01
    biological = float(np.mean(((expected[:, :5] - constrained[:, :5]) ** 2) / biological_scale))
    categorical = float(np.mean((expected[:, 5:12] - constrained[:, 5:12]) ** 2))
    if not rich:
        return 0.75 * biological + 0.25 * categorical
    body_scale = float(np.var(expected[:, BASE_TARGETS:]) + 0.01)
    body = float(np.mean((expected[:, BASE_TARGETS:] - constrained[:, BASE_TARGETS:]) ** 2) / body_scale)
    return 0.50 * biological + 0.25 * categorical + 0.25 * body


def fit_ensemble(
    data: TrainingData,
    *,
    rich: bool,
    members: int,
    ridge_grid: Iterable[float],
) -> CausalEnsemble:
    data.validate()
    features = data.rich_features if rich else data.coarse_features
    targets = data.rich_targets if rich else data.coarse_targets
    folds = np.mod(data.matrix_ids, members)
    losses: dict[float, float] = {}
    for ridge_lambda in ridge_grid:
        predictions = np.empty_like(targets)
        for fold in range(members):
            train = folds != fold
            holdout = folds == fold
            mean = features[train].mean(axis=0)
            scale = features[train].std(axis=0)
            scale[scale < 1.0e-8] = 1.0
            training_features = (features[train] - mean) / scale
            holdout_features = (features[holdout] - mean) / scale
            coefficients = _fit_action_models(
                training_features,
                targets[train],
                data.actions[train],
                float(ridge_lambda),
            )
            predictions[holdout] = _raw_predict(
                holdout_features, data.actions[holdout], coefficients
            )
        losses[float(ridge_lambda)] = _prediction_loss(targets, predictions, rich)
    selected = min(losses, key=lambda value: (losses[value], value))
    coefficient_values = []
    variance_values = []
    mean_values = []
    scale_values = []
    heldout_predictions = np.empty_like(targets)
    for fold in range(members):
        train = folds != fold
        holdout = folds == fold
        mean = features[train].mean(axis=0)
        scale = features[train].std(axis=0)
        scale[scale < 1.0e-8] = 1.0
        training_features = (features[train] - mean) / scale
        holdout_features = (features[holdout] - mean) / scale
        coefficients = _fit_action_models(
            training_features, targets[train], data.actions[train], selected
        )
        mean_values.append(mean)
        scale_values.append(scale)
        coefficient_values.append(coefficients)
        predicted = _raw_predict(
            holdout_features, data.actions[holdout], coefficients
        )
        heldout_predictions[holdout] = predicted
        residual = targets[holdout] - _constrain_predictions(predicted, rich)
        action_variance = np.empty((4, targets.shape[1]), dtype=np.float64)
        for action in range(4):
            selected_rows = residual[data.actions[holdout] == action]
            if len(selected_rows) < 2:
                selected_rows = residual
            action_variance[action] = np.maximum(np.mean(selected_rows ** 2, axis=0), 1.0e-4)
        variance_values.append(action_variance)
    constrained = _constrain_predictions(heldout_predictions, rich)
    persistence = np.tile(targets[:, :1], (1, targets.shape[1]))
    cross_validation = {
        "composite_loss": float(losses[selected]),
        "completion_brier": float(np.mean((targets[:, 0] - constrained[:, 0]) ** 2)),
        "completion_intercept_brier": float(np.mean((targets[:, 0] - targets[:, 0].mean()) ** 2)),
        "growth_mae": float(np.mean(np.abs(targets[:, 1] - constrained[:, 1]))),
        "similarity_mae": float(np.mean(np.abs(targets[:, 2] - constrained[:, 2]))),
        "alignment_mae": float(np.mean(np.abs(targets[:, 3] - constrained[:, 3]))),
    }
    if rich:
        cross_validation["next_clr_rmse"] = float(
            np.sqrt(np.mean((targets[:, BASE_TARGETS:] - constrained[:, BASE_TARGETS:]) ** 2))
        )
        cross_validation["next_clr_zero_rmse"] = float(
            np.sqrt(np.mean(targets[:, BASE_TARGETS:] ** 2))
        )
    model = CausalEnsemble(
        rich,
        float(selected),
        np.stack(mean_values),
        np.stack(scale_values),
        np.stack(coefficient_values),
        np.stack(variance_values),
        cross_validation,
    )
    model.validate()
    return model


def uniform_weights(model: CausalEnsemble) -> NDArray[np.float64]:
    return np.full(model.members, 1.0 / model.members, dtype=np.float64)


def member_log_likelihood(
    prediction: EnsemblePrediction,
    observed: NDArray[np.floating],
) -> NDArray[np.float64]:
    values = np.asarray(observed, dtype=np.float64)
    if values.shape != (9,):
        raise ValueError("observed transition likelihood vector must have width 9")
    members = prediction.members
    probability = np.clip(members[:, 0], EPSILON, 1.0 - EPSILON)
    binary = values[0] * np.log(probability) + (1.0 - values[0]) * np.log(1.0 - probability)
    variance = np.maximum(prediction.residual_variance[:, 1:5], 1.0e-4)
    gaussian = -0.5 * np.sum(
        np.log(2.0 * np.pi * variance) + (values[1:5] - members[:, 1:5]) ** 2 / variance,
        axis=1,
    )
    cue_index = int(np.argmax(values[5:9]))
    categorical = np.log(np.maximum(members[:, 5 + cue_index], EPSILON))
    return binary + gaussian + categorical


def update_member_weights(
    weights: NDArray[np.floating],
    prediction: EnsemblePrediction,
    observed: NDArray[np.floating],
) -> NDArray[np.float64]:
    prior = np.asarray(weights, dtype=np.float64)
    log_values = np.log(np.maximum(prior, EPSILON)) + member_log_likelihood(prediction, observed)
    log_values -= float(np.max(log_values))
    posterior = np.exp(log_values)
    return posterior / float(posterior.sum())


def expected_information_gain(
    prediction: EnsemblePrediction, weights: NDArray[np.floating]
) -> float:
    values = np.asarray(weights, dtype=np.float64)
    values = values / float(values.sum())
    members = prediction.members

    def entropy(probabilities: NDArray[np.float64]) -> NDArray[np.float64]:
        clipped = np.maximum(probabilities, EPSILON)
        return -np.sum(clipped * np.log(clipped), axis=-1)

    completion = np.stack((members[:, 0], 1.0 - members[:, 0]), axis=1)
    blocks = (completion, members[:, 5:9], members[:, 9:12])
    gains = []
    for block in blocks:
        mixture = np.einsum("m,mk->k", values, block)
        gains.append(float(entropy(mixture) - np.dot(values, entropy(block))))
    for index in range(1, 5):
        between = float(np.dot(values, (members[:, index] - np.dot(values, members[:, index])) ** 2))
        within = float(np.dot(values, prediction.residual_variance[:, index]))
        gains.append(0.5 * np.log1p(between / max(within, 1.0e-8)))
    return float(np.clip(np.mean(gains), 0.0, 1.0))


def predicted_state(
    previous: BodyState,
    prediction: EnsemblePrediction,
    weights: NDArray[np.floating],
    action: int,
    *,
    rich: bool,
) -> BodyState:
    mean = prediction.mean(weights)
    clr = mean[BASE_TARGETS:].copy() if rich else previous.clr.copy()
    history_row = np.concatenate(
        (
            np.asarray((previous.growth_norm, previous.similarity, previous.alignment)),
            previous.cue_probs,
            np.eye(4, dtype=np.float64)[previous.previous_action],
        )
    )
    output = BodyState(
        clr,
        float(mean[4]),
        float(mean[1]),
        float(mean[2]),
        float(mean[3]),
        mean[5:9].copy(),
        mean[9:12].copy(),
        int(action),
        np.vstack((history_row, previous.history[0])),
    )
    output.validate()
    return output


def observed_likelihood_vector(
    composition: NDArray[np.integer], raw: RawObservation, completed: bool, growth_budget: int
) -> NDArray[np.float64]:
    cue = np.zeros(4, dtype=np.float64)
    cue[int(raw.cue)] = 1.0
    return np.concatenate(
        (
            np.asarray(
                (
                    float(completed),
                    float(np.log1p(max(0, raw.growth_steps)) / np.log1p(growth_budget)),
                    float(raw.boundary_similarity),
                    float(raw.alignment_score),
                    float(np.asarray(composition).sum() / 80.0),
                )
            ),
            cue,
        )
    )


def model_arrays(model: CausalEnsemble) -> dict[str, NDArray[Any]]:
    return {
        "rich": np.asarray((int(model.rich),), dtype=np.int8),
        "ridge_lambda": np.asarray((model.ridge_lambda,), dtype=np.float64),
        "feature_mean": model.feature_mean,
        "feature_scale": model.feature_scale,
        "coefficients": model.coefficients,
        "residual_variance": model.residual_variance,
        "cv_names": np.asarray(sorted(model.cross_validation)),
        "cv_values": np.asarray([model.cross_validation[key] for key in sorted(model.cross_validation)]),
    }


def model_from_arrays(arrays: dict[str, NDArray[Any]]) -> CausalEnsemble:
    names = [str(value) for value in arrays["cv_names"]]
    values = [float(value) for value in arrays["cv_values"]]
    model = CausalEnsemble(
        bool(int(arrays["rich"][0])),
        float(arrays["ridge_lambda"][0]),
        np.asarray(arrays["feature_mean"], dtype=np.float64),
        np.asarray(arrays["feature_scale"], dtype=np.float64),
        np.asarray(arrays["coefficients"], dtype=np.float64),
        np.asarray(arrays["residual_variance"], dtype=np.float64),
        dict(zip(names, values, strict=True)),
    )
    model.validate()
    return model


def save_model(path: Path, model: CausalEnsemble) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **model_arrays(model))


def load_model(path: Path) -> CausalEnsemble:
    with np.load(path, allow_pickle=False) as archive:
        return model_from_arrays({name: archive[name].copy() for name in archive.files})


def model_digest(model: CausalEnsemble) -> str:
    chunks: list[bytes] = []
    for name, value in sorted(model_arrays(model).items()):
        array = np.ascontiguousarray(value)
        chunks.extend((name.encode(), str(array.shape).encode(), array.dtype.str.encode(), array.tobytes()))
    chunks.append(canonical_json_bytes(model.cross_validation))
    return sha256_bytes(b"".join(chunks))


def action_calibration_offsets(
    model: CausalEnsemble,
    features: NDArray[np.float64],
    actions: NDArray[np.int8],
    targets: NDArray[np.float64],
    shrinkage: float,
) -> NDArray[np.float64]:
    output = np.zeros((4, 5), dtype=np.float64)
    weights = uniform_weights(model)
    for action in range(4):
        mask = actions == action
        if not np.any(mask):
            continue
        predictions = np.stack(
            [model.predict(row, action).mean(weights)[:5] for row in features[mask]]
        )
        residual = targets[mask, :5] - predictions
        output[action] = residual.sum(axis=0) / (len(residual) + float(shrinkage))
    return output


def model_summary(model: CausalEnsemble) -> dict[str, Any]:
    return {
        "rich": model.rich,
        "ridge_lambda": model.ridge_lambda,
        "members": model.members,
        "feature_width": model.feature_width,
        "target_width": model.target_width,
        "cross_validation": model.cross_validation,
        "digest": model_digest(model),
    }
