from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import canonical_json_bytes, sha256_bytes

from .causal_model import TrainingData
from .state import BodyState, state_features
from .types import ConditionSpec


EPSILON = 1.0e-9
BASE_TARGETS = 12
SHUFFLED_ACTIONS = np.asarray((1, 3, 0, 2), dtype=np.int8)


@dataclass(frozen=True)
class ClrProjection:
    mean: NDArray[np.float64]
    components: NDArray[np.float64]

    def validate(self) -> None:
        if self.mean.shape != (100,) or self.components.ndim != 2:
            raise ValueError("CLR projection shape is invalid")
        if self.components.shape[1] != 100:
            raise ValueError("CLR projection must act on 100 molecular components")
        if not np.all(np.isfinite(self.mean)) or not np.all(np.isfinite(self.components)):
            raise ValueError("CLR projection contains non-finite values")

    def project(self, clr: NDArray[np.floating]) -> NDArray[np.float64]:
        values = np.asarray(clr, dtype=np.float64)
        if values.shape[-1] != 100:
            raise ValueError("CLR input width must be 100")
        return (values - self.mean) @ self.components.T

    def inverse(self, latent: NDArray[np.floating]) -> NDArray[np.float64]:
        values = np.asarray(latent, dtype=np.float64)
        if values.shape[-1] != self.components.shape[0]:
            raise ValueError("latent body width does not match projection")
        clr = values @ self.components + self.mean
        return clr - np.mean(clr, axis=-1, keepdims=True)


@dataclass(frozen=True)
class HybridPrediction:
    members: NDArray[np.float64]
    residual_variance: NDArray[np.float64]

    def mean(self, weights: NDArray[np.floating]) -> NDArray[np.float64]:
        values = np.asarray(weights, dtype=np.float64)
        values = values / float(values.sum())
        return np.einsum("m,mt->t", values, self.members)


@dataclass(frozen=True)
class HybridModel:
    projection: ClrProjection
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
    def latent_width(self) -> int:
        return int(self.projection.components.shape[0])

    @property
    def target_width(self) -> int:
        return 1 + BASE_TARGETS + self.latent_width

    @property
    def feature_width(self) -> int:
        return int(self.feature_mean.shape[1])

    def validate(self) -> None:
        self.projection.validate()
        if self.feature_mean.ndim != 2 or self.feature_scale.shape != self.feature_mean.shape:
            raise ValueError("hybrid feature scaler is invalid")
        expected = (self.members, 4, self.feature_width + 1, self.target_width)
        if self.coefficients.shape != expected:
            raise ValueError(f"hybrid coefficient shape {self.coefficients.shape} != {expected}")
        if self.residual_variance.shape != (self.members, 4, self.target_width):
            raise ValueError("hybrid residual variance shape is invalid")
        if np.any(self.feature_scale <= 0.0) or np.any(self.residual_variance <= 0.0):
            raise ValueError("hybrid scales and variances must be positive")
        if not np.all(np.isfinite(self.coefficients)):
            raise ValueError("hybrid model contains non-finite coefficients")

    def features(self, state: BodyState, condition: ConditionSpec) -> NDArray[np.float64]:
        full = state_features(state, condition, rich=True)
        return np.concatenate((self.projection.project(full[:100]), full[100:]))

    def predict(
        self,
        state: BodyState,
        condition: ConditionSpec,
        action: int,
        *,
        shuffled_actions: bool = False,
    ) -> HybridPrediction:
        return self.predict_features(
            self.features(state, condition),
            action,
            shuffled_actions=shuffled_actions,
        )

    def predict_features(
        self,
        features: NDArray[np.floating],
        action: int,
        *,
        shuffled_actions: bool = False,
    ) -> HybridPrediction:
        values = np.asarray(features, dtype=np.float64)
        if values.shape != (self.feature_width,):
            raise ValueError("hybrid feature vector has wrong shape")
        model_action = (
            int(SHUFFLED_ACTIONS[int(action)]) if shuffled_actions else int(action)
        )
        standardized = (values - self.feature_mean) / self.feature_scale
        design = np.column_stack(
            (np.ones(self.members, dtype=np.float64), standardized)
        )
        raw = np.einsum(
            "md,mdt->mt", design, self.coefficients[:, model_action]
        )
        return HybridPrediction(
            constrain_predictions(raw, self.latent_width),
            self.residual_variance[:, model_action].copy(),
        )


def fit_projection(data: TrainingData, components: int) -> ClrProjection:
    data.validate()
    clr = np.asarray(data.rich_features[:, :100], dtype=np.float64)
    mean = clr.mean(axis=0)
    _u, _s, right = np.linalg.svd(clr - mean, full_matrices=False)
    if components > len(right):
        raise ValueError("development corpus is too small for requested CLR projection")
    selected = right[:components].copy()
    for index in range(len(selected)):
        pivot = int(np.argmax(np.abs(selected[index])))
        if selected[index, pivot] < 0.0:
            selected[index] *= -1.0
    projection = ClrProjection(mean, selected)
    projection.validate()
    return projection


def transformed_training(
    data: TrainingData, projection: ClrProjection
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    current_latent = projection.project(data.rich_features[:, :100])
    features = np.concatenate((current_latent, data.rich_features[:, 100:]), axis=1)
    base = np.asarray(data.rich_targets[:, :BASE_TARGETS], dtype=np.float64)
    inherited = (
        (base[:, 0] > 0.5) & (base[:, 2] > 0.90)
    ).astype(np.float64)[:, None]
    next_latent = projection.project(data.rich_targets[:, BASE_TARGETS:])
    targets = np.concatenate((inherited, base, next_latent), axis=1)
    return features, targets


def constrain_predictions(
    raw: NDArray[np.floating], latent_width: int
) -> NDArray[np.float64]:
    output = np.asarray(raw, dtype=np.float64).copy()
    output[:, 0:2] = np.clip(output[:, 0:2], EPSILON, 1.0 - EPSILON)
    output[:, 2] = np.clip(output[:, 2], 0.0, 1.5)
    output[:, 3:5] = np.clip(output[:, 3:5], 0.0, 1.0)
    output[:, 5] = np.clip(output[:, 5], 0.0, 1.5)
    for start, width in ((6, 4), (10, 3)):
        values = np.clip(output[:, start : start + width], EPSILON, 1.0)
        output[:, start : start + width] = values / values.sum(axis=1, keepdims=True)
    if output.shape[1] != 13 + latent_width:
        raise ValueError("hybrid prediction target width is invalid")
    return output


def _ridge(
    features: NDArray[np.float64], targets: NDArray[np.float64], penalty: float
) -> NDArray[np.float64]:
    design = np.column_stack((np.ones(len(features)), features))
    gram = design.T @ design
    regularizer = np.eye(gram.shape[0]) * float(penalty)
    regularizer[0, 0] = 0.0
    try:
        return np.linalg.solve(gram + regularizer, design.T @ targets)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(gram + regularizer, rcond=1.0e-12) @ design.T @ targets


def _action_models(
    features: NDArray[np.float64],
    targets: NDArray[np.float64],
    actions: NDArray[np.int8],
    penalty: float,
) -> NDArray[np.float64]:
    output = np.empty((4, features.shape[1] + 1, targets.shape[1]))
    for action in range(4):
        mask = actions == action
        if not np.any(mask):
            raise ValueError(f"development corpus contains no action {action}")
        output[action] = _ridge(features[mask], targets[mask], penalty)
    return output


def _raw_predict(
    features: NDArray[np.float64],
    actions: NDArray[np.int8],
    coefficients: NDArray[np.float64],
) -> NDArray[np.float64]:
    design = np.column_stack((np.ones(len(features)), features))
    output = np.empty((len(features), coefficients.shape[-1]))
    for action in range(4):
        mask = actions == action
        if np.any(mask):
            output[mask] = design[mask] @ coefficients[action]
    return output


def _loss(expected: NDArray[np.float64], raw: NDArray[np.float64], latent: int) -> float:
    predicted = constrain_predictions(raw, latent)
    binary = float(np.mean((expected[:, :2] - predicted[:, :2]) ** 2))
    biological_scale = np.var(expected[:, 2:6], axis=0) + 0.01
    biological = float(
        np.mean(((expected[:, 2:6] - predicted[:, 2:6]) ** 2) / biological_scale)
    )
    categorical = float(np.mean((expected[:, 6:13] - predicted[:, 6:13]) ** 2))
    body_scale = float(np.var(expected[:, 13:]) + 0.01)
    body = float(np.mean((expected[:, 13:] - predicted[:, 13:]) ** 2) / body_scale)
    return 0.35 * binary + 0.30 * biological + 0.20 * categorical + 0.15 * body


def fit_hybrid_model(
    data: TrainingData,
    *,
    components: int,
    members: int,
    ridge_grid: Iterable[float],
) -> HybridModel:
    projection = fit_projection(data, components)
    features, targets = transformed_training(data, projection)
    folds = np.mod(data.matrix_ids, members)
    losses: dict[float, float] = {}
    for penalty in ridge_grid:
        heldout = np.empty_like(targets)
        for fold in range(members):
            train = folds != fold
            test = folds == fold
            mean = features[train].mean(axis=0)
            scale = features[train].std(axis=0)
            scale[scale < 1.0e-8] = 1.0
            coefficients = _action_models(
                (features[train] - mean) / scale,
                targets[train],
                data.actions[train],
                float(penalty),
            )
            heldout[test] = _raw_predict(
                (features[test] - mean) / scale,
                data.actions[test],
                coefficients,
            )
        losses[float(penalty)] = _loss(targets, heldout, components)
    selected = min(losses, key=lambda value: (losses[value], value))
    means, scales, coefficients_values, variances = [], [], [], []
    heldout = np.empty_like(targets)
    for fold in range(members):
        train = folds != fold
        test = folds == fold
        mean = features[train].mean(axis=0)
        scale = features[train].std(axis=0)
        scale[scale < 1.0e-8] = 1.0
        coefficients = _action_models(
            (features[train] - mean) / scale,
            targets[train],
            data.actions[train],
            selected,
        )
        predicted = _raw_predict(
            (features[test] - mean) / scale,
            data.actions[test],
            coefficients,
        )
        heldout[test] = predicted
        residual = targets[test] - constrain_predictions(predicted, components)
        by_action = np.empty((4, targets.shape[1]))
        for action in range(4):
            selected_rows = residual[data.actions[test] == action]
            if len(selected_rows) < 2:
                selected_rows = residual
            by_action[action] = np.maximum(np.mean(selected_rows**2, axis=0), 1.0e-4)
        means.append(mean)
        scales.append(scale)
        coefficients_values.append(coefficients)
        variances.append(by_action)
    constrained = constrain_predictions(heldout, components)
    cross_validation = {
        "composite_loss": float(losses[selected]),
        "inherited_brier": float(np.mean((targets[:, 0] - constrained[:, 0]) ** 2)),
        "inherited_intercept_brier": float(
            np.mean((targets[:, 0] - targets[:, 0].mean()) ** 2)
        ),
        "completion_brier": float(np.mean((targets[:, 1] - constrained[:, 1]) ** 2)),
        "similarity_mae": float(np.mean(np.abs(targets[:, 3] - constrained[:, 3]))),
        "next_latent_rmse": float(np.sqrt(np.mean((targets[:, 13:] - constrained[:, 13:]) ** 2))),
        "next_latent_zero_rmse": float(np.sqrt(np.mean(targets[:, 13:] ** 2))),
    }
    model = HybridModel(
        projection,
        float(selected),
        np.stack(means),
        np.stack(scales),
        np.stack(coefficients_values),
        np.stack(variances),
        cross_validation,
    )
    model.validate()
    return model


def uniform_weights(model: HybridModel) -> NDArray[np.float64]:
    return np.full(model.members, 1.0 / model.members)


def predicted_regime_prior(
    belief: NDArray[np.floating], switch_probability: float, shock_probability: float
) -> NDArray[np.float64]:
    values = np.asarray(belief, dtype=np.float64)
    base_total = float(values[:2].sum())
    base = np.asarray((0.5, 0.5)) if base_total <= 0.0 else values[:2] / base_total
    switched = np.asarray(
        (
            (1.0 - switch_probability) * base[0] + switch_probability * base[1],
            switch_probability * base[0] + (1.0 - switch_probability) * base[1],
        )
    )
    return np.asarray(
        (
            (1.0 - shock_probability) * switched[0],
            (1.0 - shock_probability) * switched[1],
            shock_probability,
        )
    )


def cue_distribution(
    prior: NDArray[np.floating], accuracy: float
) -> NDArray[np.float64]:
    values = np.asarray(prior, dtype=np.float64)
    return np.concatenate((np.asarray((1.0 - accuracy,)), accuracy * values))


def posterior_for_cue(
    prior: NDArray[np.floating], cue: int, accuracy: float
) -> NDArray[np.float64]:
    values = np.asarray(prior, dtype=np.float64)
    if int(cue) == 0:
        return values.copy()
    posterior = np.zeros(3)
    posterior[int(cue) - 1] = 1.0
    return posterior if accuracy > 0.0 else values.copy()


def entropy(probability: NDArray[np.floating]) -> float:
    values = np.asarray(probability, dtype=np.float64)
    values = values[values > 0.0]
    return float(-np.sum(values * np.log(values)))


def expected_regime_information(
    belief: NDArray[np.floating],
    switch_probability: float,
    shock_probability: float,
    cue_accuracy: float,
) -> float:
    prior = predicted_regime_prior(belief, switch_probability, shock_probability)
    cues = cue_distribution(prior, cue_accuracy)
    expected = 0.0
    for cue, probability in enumerate(cues):
        expected += float(probability) * entropy(
            posterior_for_cue(prior, cue, cue_accuracy)
        )
    maximum = np.log(3.0)
    return float(np.clip((entropy(prior) - expected) / maximum, 0.0, 1.0))


def model_arrays(model: HybridModel) -> dict[str, NDArray[Any]]:
    return {
        "projection_mean": model.projection.mean,
        "projection_components": model.projection.components,
        "ridge_lambda": np.asarray((model.ridge_lambda,)),
        "feature_mean": model.feature_mean,
        "feature_scale": model.feature_scale,
        "coefficients": model.coefficients,
        "residual_variance": model.residual_variance,
        "cross_validation_names": np.asarray(sorted(model.cross_validation)),
        "cross_validation_values": np.asarray(
            [model.cross_validation[key] for key in sorted(model.cross_validation)]
        ),
    }


def model_from_arrays(arrays: dict[str, NDArray[Any]]) -> HybridModel:
    names = [str(value) for value in arrays["cross_validation_names"]]
    values = np.asarray(arrays["cross_validation_values"], dtype=np.float64)
    model = HybridModel(
        ClrProjection(
            np.asarray(arrays["projection_mean"], dtype=np.float64),
            np.asarray(arrays["projection_components"], dtype=np.float64),
        ),
        float(np.asarray(arrays["ridge_lambda"])[0]),
        np.asarray(arrays["feature_mean"], dtype=np.float64),
        np.asarray(arrays["feature_scale"], dtype=np.float64),
        np.asarray(arrays["coefficients"], dtype=np.float64),
        np.asarray(arrays["residual_variance"], dtype=np.float64),
        dict(zip(names, (float(value) for value in values), strict=True)),
    )
    model.validate()
    return model


def save_model(path: Path, model: HybridModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **model_arrays(model))


def load_model(path: Path) -> HybridModel:
    with np.load(path, allow_pickle=False) as archive:
        return model_from_arrays({name: archive[name].copy() for name in archive.files})


def model_digest(model: HybridModel) -> str:
    chunks: list[bytes] = []
    for name, value in sorted(model_arrays(model).items()):
        array = np.ascontiguousarray(value)
        chunks.extend((name.encode(), str(array.shape).encode(), array.dtype.str.encode(), array.tobytes()))
    return sha256_bytes(b"".join(chunks))


def model_summary(model: HybridModel) -> dict[str, Any]:
    return {
        "digest": model_digest(model),
        "ridge_lambda": model.ridge_lambda,
        "members": model.members,
        "feature_width": model.feature_width,
        "latent_width": model.latent_width,
        "target_width": model.target_width,
        "projection_solver": "numpy.linalg.svd(full_matrices=False)+canonical_sign",
        "cross_validation": model.cross_validation,
    }
