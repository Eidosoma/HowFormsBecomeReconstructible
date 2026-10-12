"""Optional Numba kernels with identical pure-Python fallbacks."""

from __future__ import annotations

import numpy as np

try:  # pragma: no cover - availability depends on the runtime Python.
    from numba import njit

    NUMBA_AVAILABLE = True
except Exception:  # pragma: no cover
    NUMBA_AVAILABLE = False

    def njit(*args, **kwargs):  # type: ignore[no-redef]
        if args and callable(args[0]):
            return args[0]

        def decorate(function):
            return function

        return decorate


@njit(cache=True)
def wagner_sweep(
    weights: np.ndarray,
    bias: np.ndarray,
    order: np.ndarray,
    state: np.ndarray,
) -> np.ndarray:
    result = state.copy()
    for order_index in range(order.shape[0]):
        gene = int(order[order_index])
        field = bias[gene]
        for regulator in range(result.shape[0]):
            field += weights[gene, regulator] * result[regulator]
        if field > 0.0:
            result[gene] = 1
        elif field < 0.0:
            result[gene] = -1
        # Exact zero deliberately retains the previous state.
    return result


@njit(cache=True)
def wagner_clamped_sweep(
    weights: np.ndarray,
    bias: np.ndarray,
    order: np.ndarray,
    state: np.ndarray,
    clamped: np.ndarray,
    target: np.ndarray,
) -> np.ndarray:
    """Sequential Wagner sweep with selected genes fixed throughout."""

    result = state.copy()
    for gene in range(result.shape[0]):
        if clamped[gene]:
            result[gene] = target[gene]
    for order_index in range(order.shape[0]):
        gene = int(order[order_index])
        if clamped[gene]:
            continue
        field = bias[gene]
        for regulator in range(result.shape[0]):
            field += weights[gene, regulator] * result[regulator]
        if field > 0.0:
            result[gene] = 1
        elif field < 0.0:
            result[gene] = -1
    return result


@njit(cache=True)
def boolean_successors(truth_table: np.ndarray) -> np.ndarray:
    genes = truth_table.shape[0]
    states = truth_table.shape[1]
    result = np.zeros(states, dtype=np.int64)
    for state in range(states):
        successor = 0
        for gene in range(genes):
            successor |= int(truth_table[gene, state]) << gene
        result[state] = successor
    return result
