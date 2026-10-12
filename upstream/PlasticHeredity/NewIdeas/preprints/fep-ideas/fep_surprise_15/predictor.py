from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression


def sigmoid(value: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(value, dtype=np.float64), -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-values))


def log_loss(labels: np.ndarray, predictions: np.ndarray) -> float:
    y = np.asarray(labels, dtype=np.float64)
    p = np.clip(np.asarray(predictions, dtype=np.float64), 1e-12, 1.0 - 1e-12)
    if len(y) == 0:
        return float("nan")
    return float(np.mean(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))))


@dataclass
class FrozenPredictor15:
    mean: np.ndarray
    scale: np.ndarray
    coefficient: np.ndarray
    intercept: float
    c: float
    calibration_slope: float = 1.0
    calibration_intercept: float = 0.0
    constant: float | None = None

    def linear_predictor(self, values: np.ndarray) -> np.ndarray:
        x = np.asarray(values, dtype=np.float64)
        if self.constant is not None:
            probability = float(np.clip(self.constant, 1e-12, 1.0 - 1e-12))
            return np.full(len(x), np.log(probability / (1.0 - probability)))
        standardized = (x - self.mean) / self.scale
        return standardized @ self.coefficient + self.intercept

    def predict(self, values: np.ndarray) -> np.ndarray:
        if self.constant is not None:
            return np.full(len(values), self.constant, dtype=np.float64)
        linear = self.linear_predictor(values)
        return sigmoid(
            self.calibration_slope * linear + self.calibration_intercept
        )


def _fit_base(
    values: np.ndarray, labels: np.ndarray, c: float
) -> FrozenPredictor15:
    x = np.asarray(values, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int8)
    if x.ndim != 2 or len(x) != len(y) or not len(x):
        raise ValueError("predictor arrays must be nonempty and aligned")
    mean = x.mean(axis=0)
    scale = x.std(axis=0, ddof=1 if len(x) > 1 else 0)
    scale = np.where(np.isfinite(scale) & (scale >= 1e-8), scale, 1.0)
    prevalence = float(np.clip(y.mean(), 1e-6, 1.0 - 1e-6))
    if len(np.unique(y)) < 2:
        return FrozenPredictor15(
            mean,
            scale,
            np.zeros(x.shape[1]),
            0.0,
            float(c),
            constant=prevalence,
        )
    model = LogisticRegression(
        C=float(c),
        l1_ratio=0.0,
        solver="lbfgs",
        max_iter=2_000,
        class_weight=None,
        random_state=0,
    ).fit((x - mean) / scale, y)
    return FrozenPredictor15(
        mean=mean,
        scale=scale,
        coefficient=model.coef_[0].copy(),
        intercept=float(model.intercept_[0]),
        c=float(c),
    )


def _matrix_folds(matrix_ids: np.ndarray, folds: int) -> list[np.ndarray]:
    unique = np.unique(np.asarray(matrix_ids, dtype=np.int64))
    if len(unique) < 2:
        return []
    count = max(2, min(int(folds), len(unique)))
    return [
        np.isin(matrix_ids, unique[np.arange(len(unique)) % count == fold])
        for fold in range(count)
    ]


def _cross_fitted_linear(
    values: np.ndarray,
    labels: np.ndarray,
    matrix_ids: np.ndarray,
    c: float,
    folds: int,
) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int8)
    output = np.full(len(y), np.nan, dtype=np.float64)
    masks = _matrix_folds(matrix_ids, folds)
    if not masks:
        return _fit_base(x, y, c).linear_predictor(x)
    for valid in masks:
        if not valid.any() or not (~valid).any():
            continue
        fitted = _fit_base(x[~valid], y[~valid], c)
        output[valid] = fitted.linear_predictor(x[valid])
    if not np.isfinite(output).all():
        raise RuntimeError("development cross-fitting left unscored rows")
    return output


def _fit_platt(linear: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    z = np.asarray(linear, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    if len(np.unique(y)) < 2 or float(np.std(z)) < 1e-12:
        prevalence = float(np.clip(y.mean(), 1e-6, 1.0 - 1e-6))
        return 0.0, float(np.log(prevalence / (1.0 - prevalence)))

    prevalence = float(np.clip(y.mean(), 1e-6, 1.0 - 1e-6))
    center = float(np.mean(z))
    scale = max(float(np.std(z)), 1e-8)
    standardized = (z - center) / scale
    design = np.column_stack([standardized, np.ones(len(standardized))])
    parameters = np.asarray(
        [0.0, np.log(prevalence / (1.0 - prevalence))], dtype=np.float64
    )
    ridge = 1e-8

    def objective(theta: np.ndarray) -> float:
        probability = sigmoid(design @ theta)
        return log_loss(y, probability) + ridge * float(theta[0] ** 2)

    for _ in range(200):
        probability = sigmoid(design @ parameters)
        residual = probability - y
        gradient = design.T @ residual / len(y)
        gradient[0] += 2.0 * ridge * parameters[0]
        weights = np.maximum(probability * (1.0 - probability), 1e-10)
        hessian = (design.T * weights) @ design / len(y)
        hessian[0, 0] += 2.0 * ridge
        hessian[1, 1] += 1e-12
        step = np.linalg.solve(hessian, gradient)
        if float(np.max(np.abs(gradient))) < 1e-10:
            break
        current = objective(parameters)
        rate = 1.0
        accepted = False
        while rate >= 2.0**-30:
            candidate = parameters - rate * step
            if objective(candidate) <= current - 1e-4 * rate * float(
                gradient @ step
            ):
                parameters = candidate
                accepted = True
                break
            rate *= 0.5
        if not accepted:
            if float(np.max(np.abs(gradient))) < 1e-7:
                break
            raise RuntimeError("development calibration Newton line search failed")
        if float(np.max(np.abs(rate * step))) < 1e-10:
            break
    if not np.isfinite(parameters).all():
        raise RuntimeError("development calibration produced nonfinite parameters")
    # Platt calibration is constrained to preserve the ridge model's ordering.
    # For this convex problem, a negative unconstrained slope puts the
    # nonnegative optimum at slope zero with the prevalence-only intercept.
    if parameters[0] < 0.0:
        return 0.0, float(np.log(prevalence / (1.0 - prevalence)))
    slope = float(parameters[0] / scale)
    intercept = float(parameters[1] - parameters[0] * center / scale)
    return slope, intercept


def select_and_fit(
    values: np.ndarray,
    labels: np.ndarray,
    matrix_ids: np.ndarray,
    c_grid: Iterable[float],
    folds: int,
) -> FrozenPredictor15:
    x = np.asarray(values, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int8)
    matrices = np.asarray(matrix_ids, dtype=np.int64)
    if len(x) != len(y) or len(y) != len(matrices):
        raise ValueError("predictor arrays do not align")
    best: tuple[float, float, np.ndarray] | None = None
    for candidate_c in c_grid:
        c = float(candidate_c)
        linear = _cross_fitted_linear(x, y, matrices, c, folds)
        slope, intercept = _fit_platt(linear, y)
        loss = log_loss(y, sigmoid(slope * linear + intercept))
        if best is None or loss < best[0] - 1e-12 or (
            abs(loss - best[0]) <= 1e-12 and c < best[1]
        ):
            best = (loss, c, linear)
    if best is None:
        raise ValueError("could not select a development predictor")
    fitted = _fit_base(x, y, best[1])
    if fitted.constant is None:
        slope, intercept = _fit_platt(best[2], y)
        fitted.calibration_slope = slope
        fitted.calibration_intercept = intercept
    return fitted
