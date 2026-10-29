"""Ordinal (rank/quantile) observer partitions (Part D).

Rank partitions depend only on the per-column orderings of the feature
matrix, so they are invariant under strictly monotone column transforms —
the property whose absence made the E1 epsilon-quantizers fragile across
fission contracts and bin offsets.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import rankdata


def rank_partition(
    values: np.ndarray,
    n_quantiles: int,
    offset_fraction: float = 0.0,
) -> np.ndarray:
    """Quantile-bin every column in rank space, then label unique rows.

    ``offset_fraction`` shifts every bin boundary by that fraction of one
    bin width in rank space, generalizing the {0, 0.5} offsets of
    ``finite_gard_ruliad.quotients.quantized_partition``.
    """
    if n_quantiles < 1:
        raise ValueError("n_quantiles must be positive")
    if not 0.0 <= offset_fraction < 1.0:
        raise ValueError("offset_fraction must lie in [0, 1)")
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("values must be a 2-D feature matrix")
    if not np.isfinite(array).all():
        raise ValueError("partition coordinates must be finite")
    n = array.shape[0]
    bins = np.empty_like(array, dtype=np.int64)
    for column in range(array.shape[1]):
        cdf = (rankdata(array[:, column], method="average") - 0.5) / n
        bins[:, column] = np.floor(cdf * n_quantiles + offset_fraction).astype(np.int64)
    _, labels = np.unique(bins, axis=0, return_inverse=True)
    return labels.astype(np.int64)


def offset_fractions(count: int) -> tuple[float, ...]:
    if count < 1:
        raise ValueError("offset count must be positive")
    return tuple(k / count for k in range(count))


def fast_partition_distortion(
    labels: np.ndarray,
    values: np.ndarray,
    shape_distributions: np.ndarray,
) -> dict:
    """Vectorized equivalent of ``finite_gard_ruliad.quotients.partition_distortion``.

    The reference implementation loops over blocks with a full-length scan
    per block (quadratic in practice for fine partitions); this uses sorted
    ``reduceat`` segments instead. A unit test pins agreement with the
    reference on the mini fixture.
    """
    labels = np.asarray(labels)
    values = np.asarray(values, dtype=np.float64)
    shapes = np.asarray(shape_distributions, dtype=np.float64)
    order = np.argsort(labels, kind="stable")
    sorted_labels = labels[order]
    boundaries = np.flatnonzero(np.diff(sorted_labels)) + 1
    starts = np.concatenate([[0], boundaries])
    ends = np.concatenate([boundaries, [len(labels)]])
    sorted_values = values[order]
    sorted_shapes = shapes[order]
    value_max = np.maximum.reduceat(sorted_values, starts, axis=0)
    value_min = np.minimum.reduceat(sorted_values, starts, axis=0)
    shape_max = np.maximum.reduceat(sorted_shapes, starts, axis=0)
    shape_min = np.minimum.reduceat(sorted_shapes, starts, axis=0)
    singleton = (ends - starts) <= 1
    ranges = (value_max - value_min).max(axis=1)
    ranges[singleton] = 0.0
    tv = np.minimum(1.0, 0.5 * (shape_max - shape_min).sum(axis=1))
    tv[singleton] = 0.0
    n_blocks = len(starts)
    return {
        "n_blocks": int(n_blocks),
        "compression": 1.0 - n_blocks / len(labels),
        "median_feature_range": float(np.median(ranges)),
        "max_feature_range": float(np.max(ranges)),
        "max_tv_upper_bound": float(np.max(tv)),
    }
