from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression


def sigmoid(value: np.ndarray) -> np.ndarray:
    value = np.clip(np.asarray(value, dtype=np.float64), -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-value))


@dataclass
class FrozenPredictor:
    mean: np.ndarray
    scale: np.ndarray
    coefficient: np.ndarray
    intercept: float
    c: float
    constant: float | None = None

    def predict(self, values: np.ndarray) -> np.ndarray:
        if self.constant is not None:
            return np.full(len(values), self.constant, dtype=np.float64)
        x = (np.asarray(values, dtype=np.float64) - self.mean) / self.scale
        return sigmoid(x @ self.coefficient + self.intercept)


def _fit(values: np.ndarray, labels: np.ndarray, c: float) -> FrozenPredictor:
    x = np.asarray(values, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int8)
    mean = x.mean(axis=0)
    scale = x.std(axis=0, ddof=1)
    scale = np.where(scale < 1e-8, 1.0, scale)
    prevalence = float(np.clip(y.mean() if len(y) else 0.5, 1e-6, 1 - 1e-6))
    if len(np.unique(y)) < 2:
        return FrozenPredictor(mean, scale, np.zeros(x.shape[1]), 0.0, c, prevalence)
    model = LogisticRegression(
        C=c,
        penalty="l2",
        solver="lbfgs",
        max_iter=2_000,
        class_weight=None,
    ).fit((x - mean) / scale, y)
    return FrozenPredictor(
        mean=mean,
        scale=scale,
        coefficient=model.coef_[0].copy(),
        intercept=float(model.intercept_[0]),
        c=c,
    )


def log_loss(labels: np.ndarray, predictions: np.ndarray) -> float:
    y = np.asarray(labels, dtype=np.float64)
    p = np.clip(np.asarray(predictions, dtype=np.float64), 1e-12, 1 - 1e-12)
    return float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))))


def select_c_and_fit(
    values: np.ndarray,
    labels: np.ndarray,
    matrix_ids: np.ndarray,
    c_grid: Iterable[float],
    folds: int,
) -> FrozenPredictor:
    x = np.asarray(values, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int8)
    matrices = np.asarray(matrix_ids, dtype=np.int64)
    unique = np.unique(matrices)
    folds = max(2, min(folds, len(unique)))
    best: tuple[float, float] | None = None
    for c in c_grid:
        losses = []
        for fold in range(folds):
            valid_matrices = unique[np.arange(len(unique)) % folds == fold]
            valid = np.isin(matrices, valid_matrices)
            if not valid.any() or not (~valid).any():
                continue
            fitted = _fit(x[~valid], y[~valid], float(c))
            losses.append(log_loss(y[valid], fitted.predict(x[valid])))
        score = float(np.mean(losses)) if losses else float("inf")
        # Registered tie-break: stronger regularization (smaller C).
        if best is None or score < best[0] - 1e-12 or (
            abs(score - best[0]) <= 1e-12 and float(c) < best[1]
        ):
            best = (score, float(c))
    if best is None:
        raise ValueError("could not select predictor regularization")
    return _fit(x, y, best[1])

