from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.special import gammaln, logsumexp

from fep_surprise_15.observers import (
    EPS,
    INVARIANT_KNN,
    SHELF,
    CosineShelfObserver,
    ObserverEnsemble,
)


@dataclass
class RelabeledObserverEnsemble:
    """Exact coordinate relabeling of a fitted observer ensemble.

    If ``x_new = x_native[order]``, querying the relabeled observer maps the
    state back to the native coordinates before applying the frozen model.
    No observer is refit for a pure molecule-name permutation.
    """

    native: ObserverEnsemble
    order: np.ndarray

    def __post_init__(self) -> None:
        order = np.asarray(self.order, dtype=np.int64)
        if sorted(order.tolist()) != list(range(len(order))):
            raise ValueError("order must be a permutation")
        self.order = order
        self._inverse = np.argsort(order)

    def _unlabel(self, counts: np.ndarray) -> np.ndarray:
        # Canonicalize memory layout as part of the relabeling contract.
        # sklearn's distance kernels can otherwise take layout-dependent BLAS
        # paths and move a score across an empirical-calibration tie.
        return np.ascontiguousarray(np.asarray(counts)[..., self._inverse])

    def raw_halves(self, counts: np.ndarray, observer: str) -> np.ndarray:
        return self.native.raw_halves(self._unlabel(counts), observer)

    def raw(self, counts: np.ndarray, observer: str) -> np.ndarray:
        return self.native.raw(self._unlabel(counts), observer)

    def anomaly_halves(
        self, counts: np.ndarray, phase: int, observer: str
    ) -> np.ndarray:
        return self.native.anomaly_halves(self._unlabel(counts), phase, observer)

    def anomaly(self, counts: np.ndarray, phase: int, observer: str) -> np.ndarray:
        return self.native.anomaly(self._unlabel(counts), phase, observer)

    def anomaly_grid_halves(
        self, phase_counts: np.ndarray, observer: str
    ) -> np.ndarray:
        return self.native.anomaly_grid_halves(
            self._unlabel(phase_counts), observer
        )

    def anomaly_grid(self, phase_counts: np.ndarray, observer: str) -> np.ndarray:
        return self.native.anomaly_grid(self._unlabel(phase_counts), observer)

    @property
    def halves(self) -> tuple[Any, Any]:
        # Consumers needing fitted parameters should use ``shelf_halves`` so
        # coordinate labels cannot accidentally be ignored.
        return self.native.halves

    def shelf_halves(self) -> tuple[CosineShelfObserver, CosineShelfObserver]:
        output = []
        for half in self.native.halves:
            shelf = half.shelf
            output.append(
                CosineShelfObserver(
                    weights=shelf.weights.copy(),
                    centers=shelf.centers[:, self.order].copy(),
                    gamma_shape=shelf.gamma_shape.copy(),
                    gamma_scale=shelf.gamma_scale.copy(),
                )
            )
        return output[0], output[1]


ObserverLike = ObserverEnsemble | RelabeledObserverEnsemble


@dataclass
class AtlasRegistry:
    """Actual simulated atlases plus analytic relabeling views."""

    actual: dict[str, ObserverEnsemble]
    permutation_orders: dict[int, np.ndarray]

    def get(self, key: str) -> ObserverLike:
        if key in self.actual:
            return self.actual[key]
        if key.startswith("perm_"):
            count = int(key.split("_", 1)[1])
            return RelabeledObserverEnsemble(
                self.actual["native"], self.permutation_orders[count]
            )
        raise KeyError(key)


def _shelf_halves(
    observer: ObserverLike,
) -> tuple[CosineShelfObserver, CosineShelfObserver]:
    if isinstance(observer, RelabeledObserverEnsemble):
        return observer.shelf_halves()
    return observer.halves[0].shelf, observer.halves[1].shelf


def _responsibility(model: CosineShelfObserver, counts: np.ndarray) -> np.ndarray:
    values = np.asarray(counts, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    values = values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    distance = np.maximum(1.0 - values @ model.centers.T, 1e-9)
    shape = model.gamma_shape[None, :]
    scale = model.gamma_scale[None, :]
    log_residual = (
        (shape - 1.0) * np.log(distance)
        - distance / scale
        - gammaln(shape)
        - shape * np.log(scale)
    )
    log_weight = np.log(model.weights + EPS)[None, :] + log_residual
    return np.exp(log_weight - logsumexp(log_weight, axis=1, keepdims=True))


def shelf_profile(
    observer: ObserverLike,
    launch: np.ndarray,
    *,
    minimum_cosine: float,
) -> dict[str, Any]:
    """Freeze prospective capture scores and two non-landscape baselines.

    Components are matched between the disjoint-training reference halves. Cells
    lacking the same stable multi-shelf partition in both halves remain in the
    departure analyses but are prospectively ineligible for destination tests.
    """

    left, right = _shelf_halves(observer)
    output: dict[str, Any] = {
        "eligible": False,
        "selected_k": [int(len(left.weights)), int(len(right.weights))],
        "matched_center_min_cosine": None,
        "matched_center_mean_cosine": None,
        "capture": np.empty(0, dtype=np.float64),
        "occupancy": np.empty(0, dtype=np.float64),
        "nearest": np.empty(0, dtype=np.float64),
        "centers": np.empty((0, left.centers.shape[1]), dtype=np.float64),
    }
    if len(left.weights) != len(right.weights) or len(left.weights) < 2:
        return output
    similarity = left.centers @ right.centers.T
    rows, columns = linear_sum_assignment(-similarity)
    ordering = columns[np.argsort(rows)]
    matched = similarity[np.arange(len(rows)), ordering]
    output["matched_center_min_cosine"] = float(np.min(matched))
    output["matched_center_mean_cosine"] = float(np.mean(matched))
    if float(np.min(matched)) < minimum_cosine:
        return output

    right_centers = right.centers[ordering]
    centers = left.centers + right_centers
    centers /= np.maximum(np.linalg.norm(centers, axis=1, keepdims=True), EPS)
    capture = 0.5 * (
        _responsibility(left, launch)[0]
        + _responsibility(right, launch)[0, ordering]
    )
    capture /= capture.sum()
    occupancy = 0.5 * (left.weights + right.weights[ordering])
    occupancy /= occupancy.sum()
    values = np.asarray(launch, dtype=np.float64)
    values /= max(float(np.linalg.norm(values)), EPS)
    # Frozen nearest-centroid baseline.  A small fixed temperature keeps this
    # probabilistic without learning anything from confirmation outcomes.
    logits = (values @ centers.T) / 0.025
    nearest = np.exp(logits - logsumexp(logits))
    output.update(
        {
            "eligible": True,
            "capture": capture,
            "occupancy": occupancy,
            "nearest": nearest,
            "centers": centers,
        }
    )
    return output


def destination_label(
    certification_daughters: np.ndarray, centers: np.ndarray
) -> int:
    values = np.asarray(certification_daughters, dtype=np.float64)
    if values.ndim != 2 or len(values) != 8:
        raise ValueError("a strict-8 destination requires eight daughters")
    values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    return int(np.argmax(np.mean(values @ np.asarray(centers).T, axis=0)))


def mismatch_jump(
    native: ObserverEnsemble,
    target: ObserverLike,
    native_state: np.ndarray,
    target_state: np.ndarray,
    phase: int,
) -> dict[str, np.ndarray]:
    """Cross-fitted rulebook mismatch, retained separately by observer half."""

    return {
        observer: target.anomaly_halves(target_state, phase, observer)[0]
        - native.anomaly_halves(native_state, phase, observer)[0]
        for observer in (INVARIANT_KNN, SHELF)
    }
