"""Frozen monotone recalibration between fission contracts (Part B)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr


@dataclass(frozen=True)
class MonotoneMap:
    """Piecewise-linear nondecreasing map, JSON-serializable for freezing."""

    kind: str
    knots_x: tuple[float, ...]
    knots_y: tuple[float, ...]

    def apply(self, values: np.ndarray) -> np.ndarray:
        return np.interp(np.asarray(values, dtype=np.float64), self.knots_x, self.knots_y)

    def as_dict(self) -> dict:
        return {"kind": self.kind, "knots_x": list(self.knots_x), "knots_y": list(self.knots_y)}

    @classmethod
    def from_dict(cls, payload: dict) -> "MonotoneMap":
        return cls(
            kind=str(payload["kind"]),
            knots_x=tuple(float(v) for v in payload["knots_x"]),
            knots_y=tuple(float(v) for v in payload["knots_y"]),
        )


def _merge_duplicate_x(
    x: np.ndarray, y: np.ndarray, w: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    order = np.argsort(x, kind="stable")
    x, y, w = x[order], y[order], w[order]
    unique_x, start = np.unique(x, return_index=True)
    merged_y = np.empty(len(unique_x), dtype=np.float64)
    merged_w = np.empty(len(unique_x), dtype=np.float64)
    boundaries = np.append(start, len(x))
    for i in range(len(unique_x)):
        block = slice(boundaries[i], boundaries[i + 1])
        weight = w[block].sum()
        merged_y[i] = float(np.average(y[block], weights=w[block]))
        merged_w[i] = float(weight)
    return unique_x, merged_y, merged_w


def pav_isotonic_fit(
    x: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray | None = None,
) -> MonotoneMap:
    """Weighted isotonic regression by pool-adjacent-violators."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    w = np.ones_like(x) if weights is None else np.asarray(weights, dtype=np.float64)
    if x.shape != y.shape or x.shape != w.shape:
        raise ValueError("x, y, and weights must have identical shapes")
    ux, uy, uw = _merge_duplicate_x(x, y, w)
    # Blocks as (weight, weighted-mean, count); merge while decreasing.
    block_w: list[float] = []
    block_mean: list[float] = []
    block_count: list[int] = []
    for value, weight in zip(uy, uw):
        block_w.append(float(weight))
        block_mean.append(float(value))
        block_count.append(1)
        while len(block_mean) > 1 and block_mean[-1] < block_mean[-2]:
            w2, m2, c2 = block_w.pop(), block_mean.pop(), block_count.pop()
            w1, m1, c1 = block_w.pop(), block_mean.pop(), block_count.pop()
            total = w1 + w2
            block_w.append(total)
            block_mean.append((w1 * m1 + w2 * m2) / total)
            block_count.append(c1 + c2)
    fitted = np.concatenate(
        [np.full(count, mean) for count, mean in zip(block_count, block_mean)]
    )
    return MonotoneMap(kind="isotonic", knots_x=tuple(ux), knots_y=tuple(fitted))


def quantile_map_fit(x: np.ndarray, y: np.ndarray, knots: int) -> MonotoneMap:
    """Monotone map sending x-quantiles to y-quantiles."""
    if knots < 2:
        raise ValueError("quantile map needs at least two knots")
    levels = np.linspace(0.0, 1.0, knots)
    kx = np.quantile(np.asarray(x, dtype=np.float64), levels)
    ky = np.quantile(np.asarray(y, dtype=np.float64), levels)
    unique_x, start = np.unique(kx, return_index=True)
    boundaries = np.append(start, len(kx))
    merged_y = np.asarray(
        [float(np.mean(ky[boundaries[i] : boundaries[i + 1]])) for i in range(len(unique_x))]
    )
    merged_y = np.maximum.accumulate(merged_y)
    return MonotoneMap(kind="quantile", knots_x=tuple(unique_x), knots_y=tuple(merged_y))


def removable_fraction(
    p_source: np.ndarray,
    p_target: np.ndarray,
    mapping: MonotoneMap,
    mask: np.ndarray,
    weights: np.ndarray | None = None,
) -> dict:
    """How much of the source-to-target shift a frozen monotone map removes."""
    p_source = np.asarray(p_source, dtype=np.float64)[mask]
    p_target = np.asarray(p_target, dtype=np.float64)[mask]
    w = (
        np.ones_like(p_source)
        if weights is None
        else np.asarray(weights, dtype=np.float64)[mask]
    )
    raw = p_target - p_source
    residual = p_target - mapping.apply(p_source)

    def _wmedian(values: np.ndarray) -> float:
        order = np.argsort(values)
        cumulative = np.cumsum(w[order])
        return float(values[order][np.searchsorted(cumulative, 0.5 * cumulative[-1])])

    def _wrms(values: np.ndarray) -> float:
        return float(np.sqrt(np.average(values**2, weights=w)))

    raw_median = _wmedian(np.abs(raw))
    raw_rms = _wrms(raw)
    rho_before = float(spearmanr(p_source, p_target).statistic)
    rho_after = float(spearmanr(mapping.apply(p_source), p_target).statistic)
    return {
        "kind": mapping.kind,
        "n_cells": int(mask.sum()),
        "median_abs_raw_shift": raw_median,
        "median_abs_residual": _wmedian(np.abs(residual)),
        "removable_fraction_median": (
            1.0 - _wmedian(np.abs(residual)) / raw_median if raw_median > 0 else 1.0
        ),
        "rms_raw_shift": raw_rms,
        "rms_residual": _wrms(residual),
        "removable_fraction_rms": 1.0 - _wrms(residual) / raw_rms if raw_rms > 0 else 1.0,
        "spearman_before": rho_before,
        "spearman_after": rho_after,
    }


def conditional_residual_model(
    p_source: np.ndarray,
    p_target: np.ndarray,
    mapping: MonotoneMap,
    features: np.ndarray,
    feature_names: tuple[str, ...],
    dev_mask: np.ndarray,
    eval_mask: np.ndarray,
) -> dict:
    """Linear conditional structure left after the frozen monotone map.

    Coefficients are fitted on the development half only; the reported
    variance reduction is evaluated on the untouched half.
    """
    residual = np.asarray(p_target, dtype=np.float64) - mapping.apply(p_source)
    x = np.asarray(features, dtype=np.float64)
    design_dev = np.column_stack([np.ones(int(dev_mask.sum())), x[dev_mask]])
    coefficients, *_ = np.linalg.lstsq(design_dev, residual[dev_mask], rcond=None)
    design_eval = np.column_stack([np.ones(int(eval_mask.sum())), x[eval_mask]])
    predicted = design_eval @ coefficients
    eval_residual = residual[eval_mask]
    total = float(np.sum((eval_residual - eval_residual.mean()) ** 2))
    remaining = float(np.sum((eval_residual - predicted) ** 2))
    return {
        "feature_names": list(feature_names),
        "coefficients": {
            name: float(value)
            for name, value in zip(("intercept",) + feature_names, coefficients)
        },
        "eval_r_squared": 1.0 - remaining / total if total > 0 else 0.0,
    }
