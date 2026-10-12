from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from fep_surprise_15.predictor import FrozenPredictor15, select_and_fit


MODEL_VARIANTS = ("physical", "local", "landscape")


@dataclass
class FrozenHazard2:
    model: FrozenPredictor15
    horizon: int

    def predict(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(values, dtype=np.float64)
        if x.ndim != 2:
            raise ValueError("hazard features must be two-dimensional")
        time = np.arange(1, self.horizon + 1, dtype=np.float64) / self.horizon
        expanded = np.repeat(x, self.horizon, axis=0)
        tiled_time = np.tile(time, len(x))
        design = np.column_stack([expanded, tiled_time, tiled_time**2])
        hazard = self.model.predict(design).reshape(len(x), self.horizon)
        survival_after = np.cumprod(1.0 - hazard, axis=1)
        probability = 1.0 - survival_after[:, -1]
        survival_before = np.column_stack(
            [np.ones(len(x), dtype=np.float64), survival_after[:, :-1]]
        )
        restricted_mean = survival_before.sum(axis=1)
        return probability, restricted_mean


@dataclass
class FrozenHurdle2:
    departure: FrozenHazard2
    conditional_strict8: FrozenPredictor15

    def predict(self, values: np.ndarray) -> dict[str, np.ndarray]:
        break_probability, latency = self.departure.predict(values)
        conditional = self.conditional_strict8.predict(values)
        return {
            "break": break_probability,
            "latency": latency,
            "conditional_strict8": conditional,
            "joint_strict8": break_probability * conditional,
        }


def _hazard_rows(
    values: np.ndarray,
    first_break: np.ndarray,
    matrix_ids: np.ndarray,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    labels: list[int] = []
    matrices: list[int] = []
    for row, event, matrix_id in zip(values, first_break, matrix_ids):
        event_time = int(event) + 1 if int(event) >= 0 else horizon
        stop = min(max(event_time, 1), horizon)
        for time_index in range(1, stop + 1):
            fraction = time_index / horizon
            features.append(np.r_[row, fraction, fraction**2])
            labels.append(int(int(event) >= 0 and time_index == int(event) + 1))
            matrices.append(int(matrix_id))
    return (
        np.stack(features),
        np.asarray(labels, dtype=np.int8),
        np.asarray(matrices, dtype=np.int64),
    )


def fit_hurdle(
    values: np.ndarray,
    first_break: np.ndarray,
    strict8: np.ndarray,
    matrix_ids: np.ndarray,
    *,
    horizon: int,
    c_grid: Iterable[float],
    folds: int,
) -> FrozenHurdle2:
    x = np.asarray(values, dtype=np.float64)
    breaks = np.asarray(first_break, dtype=np.int16)
    endpoint = np.asarray(strict8, dtype=np.int8)
    matrices = np.asarray(matrix_ids, dtype=np.int64)
    hazard_x, hazard_y, hazard_matrices = _hazard_rows(
        x, breaks, matrices, horizon
    )
    departure = FrozenHazard2(
        select_and_fit(hazard_x, hazard_y, hazard_matrices, c_grid, folds),
        horizon,
    )
    eligible = breaks >= 0
    # A tiny profile may contain no breaks.  The endpoint is structurally zero
    # there, so the deterministic all-row fallback freezes the correct constant.
    if not eligible.any():
        eligible = np.ones(len(endpoint), dtype=bool)
    conditional = select_and_fit(
        x[eligible], endpoint[eligible], matrices[eligible], c_grid, folds
    )
    return FrozenHurdle2(departure, conditional)


def _profile_features(profile: dict, key: str) -> tuple[float, float, float]:
    values = np.asarray(profile.get(key, []), dtype=np.float64)
    if not len(values):
        return 0.0, 0.0, 0.0
    ordered = np.sort(values)
    maximum = float(ordered[-1])
    margin = float(ordered[-1] - ordered[-2]) if len(ordered) >= 2 else maximum
    selected = values > 0
    entropy = float(-np.sum(values[selected] * np.log(values[selected])))
    return maximum, margin, entropy


def model_features(
    baseline: np.ndarray,
    launch: np.ndarray,
    mismatch: float,
    profile: dict,
    variant: str,
) -> np.ndarray:
    """Frozen nested predictors: physical < local dynamics < landscape."""

    baseline = np.asarray(baseline, dtype=np.float64)
    launch = np.asarray(launch, dtype=np.float64)
    nearest = _profile_features(profile, "nearest")
    occupancy = _profile_features(profile, "occupancy")
    physical = np.r_[baseline, launch[:11], nearest, occupancy]
    if variant == "physical":
        return physical
    local = np.r_[physical, launch[11]]
    if variant == "local":
        return local
    if variant == "landscape":
        capture = _profile_features(profile, "capture")
        return np.r_[local, mismatch, mismatch**2, mismatch * launch[11], capture]
    raise ValueError(variant)
