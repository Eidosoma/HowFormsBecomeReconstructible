"""Finite-state reference implementation for RDT-P01 development.

Row-stochastic matrices act on column readout functions. Joint entries
J[i, y, j] retain dependence between cycle success y and successor state j.
These are standard Markov calculations, not a novel empirical law.
"""
from __future__ import annotations

import math
import numpy as np


def kernel(matrix, *, substochastic=False):
    p = np.asarray(matrix, dtype=float)
    if p.ndim != 2 or p.shape[0] != p.shape[1] or p.shape[0] == 0:
        raise ValueError("A nonempty square matrix is required")
    if not np.isfinite(p).all() or (p < 0).any():
        raise ValueError("Probabilities must be finite and nonnegative")
    sums = p.sum(axis=1)
    if substochastic:
        if (sums > 1 + 1e-12).any():
            raise ValueError("Sub-Markov row mass exceeds one")
    elif not np.allclose(sums, 1, rtol=0, atol=1e-12):
        raise ValueError("Markov rows must sum to one")
    return p


def readout(values, size):
    q = np.asarray(values, dtype=float)
    if q.shape != (size,) or not np.isfinite(q).all() or ((q < 0) | (q > 1)).any():
        raise ValueError("Readout must be a [0,1] vector of the correct size")
    return q


def terminal(matrix, q, horizon):
    """Vector of terminal expectations, P**H q, including H=0."""
    p = kernel(matrix, substochastic=True)
    if not isinstance(horizon, int) or horizon < 0:
        raise ValueError("Horizon must be a nonnegative integer")
    result = readout(q, len(p)).copy()
    for _ in range(horizon):
        result = p @ result
    return result


def ordered_terminal(matrices, q):
    """Matrices are in chronological order: first u, then v gives P_u P_v q."""
    matrices = [kernel(p, substochastic=True) for p in matrices]
    if not matrices:
        return np.asarray(q, dtype=float).copy()
    result = readout(q, len(matrices[0])).copy()
    for p in reversed(matrices):
        result = p @ result
    return result


def joint_operators(joint):
    j = np.asarray(joint, dtype=float)
    if j.ndim != 3 or j.shape[1] != 2 or j.shape[0] != j.shape[2]:
        raise ValueError("Joint kernel must have shape (states, 2, states)")
    if not np.isfinite(j).all() or (j < 0).any():
        raise ValueError("Invalid joint probabilities")
    p = kernel(j.sum(axis=1))
    return p, kernel(j[:, 1, :], substochastic=True)


def all_cycle(pass_matrix, horizon, terminal_q=None):
    """P(all H cycles pass), optionally AND an additional terminal assay.

    With terminal_q omitted, H=0 is the vacuous all-cycle event, probability 1.
    Missing row mass is failure and must never be normalized away.
    """
    a = kernel(pass_matrix, substochastic=True)
    q = np.ones(len(a)) if terminal_q is None else terminal_q
    return terminal(a, q, horizon)


def failure_completion(pass_matrix):
    """Convert a sub-Markov operator to a Markov operator with absorbing failure."""
    a = kernel(pass_matrix, substochastic=True)
    result = np.zeros((len(a) + 1, len(a) + 1))
    result[:-1, :-1] = a
    result[:-1, -1] = np.maximum(0, 1 - a.sum(axis=1))
    result[-1, -1] = 1
    return kernel(result)


def fit_joint(counts):
    counts = np.asarray(counts, dtype=float)
    if counts.ndim != 3 or counts.shape[1] != 2 or counts.shape[0] != counts.shape[2]:
        raise ValueError("Counts require shape (states, 2, states)")
    if not np.isfinite(counts).all() or (counts < 0).any() or not np.equal(counts, np.floor(counts)).all():
        raise ValueError("Counts must be finite nonnegative integers")
    n = counts.sum(axis=(1, 2))
    if (n == 0).any():
        raise ValueError("Unobserved source state: no supported transition estimate")
    joint = counts / n[:, None, None]
    p, a = joint_operators(joint)
    return joint, p, a


def membership(labels, size):
    labels = np.asarray(labels)
    if labels.shape != (size,) or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("One integer aggregate label per state is required")
    values = np.unique(labels)
    if not np.array_equal(values, np.arange(len(values))):
        raise ValueError("Aggregate labels must be contiguous starting at zero")
    return np.eye(len(values))[labels]


def aggregate(matrix, q, labels, weights=None):
    """Finite oracle reduction and its exact worst-case defects.

    This function knows ALL microscopic transition rows. Its defects are not
    estimates available from a few empirical probes of a large simulator.
    """
    p = kernel(matrix)
    q = readout(q, len(p))
    c = membership(labels, len(p))
    weights = np.ones(len(p)) if weights is None else np.asarray(weights, dtype=float)
    if weights.shape != (len(p),) or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Invalid reference weights")
    mass = c.T @ weights
    if (mass <= 0).any():
        raise ValueError("Every aggregate requires positive reference mass")
    mixing = (c.T * weights) / mass[:, None]
    projected_rows = p @ c
    reduced = mixing @ projected_rows
    reduced_q = mixing @ q
    per_state_tv = 0.5 * np.abs(projected_rows - c @ reduced).sum(axis=1)
    return dict(p=reduced, q=reduced_q, membership=c,
                transition_defect=float(per_state_tv.max()),
                readout_defect=float(np.abs(q - c @ reduced_q).max()))


def tv_row_radius(samples, rows, categories, delta):
    """Simultaneous TV radius from subset Hoeffding plus a union bound.

    Partition, source distributions and sample counts must be fixed independently
    of these samples. This controls sampling error about reference rows only.
    """
    if not isinstance(samples, int) or samples < 0:
        raise ValueError("Invalid sample count")
    if not isinstance(rows, int) or rows < 1 or not isinstance(categories, int) or categories < 1:
        raise ValueError("Positive integer rows and categories required")
    if not 0 < delta < 1:
        raise ValueError("Delta must lie strictly between zero and one")
    if samples == 0:
        return 1.0
    if categories == 1:
        return 0.0
    log_subsets = categories * math.log(2) + math.log1p(-2 ** (1 - categories))
    return min(1.0, math.sqrt((math.log(rows / delta) + log_subsets) / (2 * samples)))


def terminal_error_bound(matrix, q, horizon, transition_error, readout_error=0):
    """Conditional telescoping bound using oscillations of reduced future values.

    transition_error must bound ALL reached microscopic rows against the lifted
    reduced row; sampled calibration error alone does not meet that condition.
    """
    p = kernel(matrix)
    values = readout(q, len(p)).copy()
    if not isinstance(horizon, int) or horizon < 0:
        raise ValueError("Invalid horizon")
    if not 0 <= transition_error <= 1 or not 0 <= readout_error <= 1:
        raise ValueError("Errors must lie in [0,1]")
    accumulation = 0.0
    for _ in range(horizon):
        accumulation += float(np.ptp(values))
        values = p @ values
    return min(1.0, readout_error + transition_error * accumulation)


def two_factor_kernel(identity_flip, readiness_loss, readiness_recovery):
    """States: (identity, readiness) = (0,0), (0,1), (1,0), (1,1)."""
    p, a, r = identity_flip, readiness_loss, readiness_recovery
    if any(not 0 <= x <= 1 for x in (p, a, r)):
        raise ValueError("Invalid transition probability")
    identity = np.array([[1-p, p], [p, 1-p]])
    readiness = np.array([[1-r, r], [a, 1-a]])
    return np.kron(identity, readiness)


def two_factor_exact(identity_flip, readiness_loss, readiness_recovery, horizon, *, own=True, ready=True):
    if readiness_loss + readiness_recovery == 0:
        readable = float(ready)
    else:
        pi = readiness_recovery / (readiness_loss + readiness_recovery)
        readable = pi + (float(ready)-pi) * (1-readiness_loss-readiness_recovery)**horizon
    correct = 0.5 + (0.5 if own else -0.5) * (1-2*identity_flip)**horizon
    return correct * readable


def factor_fit(counts):
    """Conventional independent identity/readiness model using the same counts."""
    c = np.asarray(counts, dtype=float).sum(axis=1)
    n = c.sum()
    p = sum(c[i, j] for i in range(4) for j in range(4) if i//2 != j//2) / n
    a = c[[1, 3]][:, [0, 2]].sum() / c[[1, 3]].sum()
    r = c[[0, 2]][:, [1, 3]].sum() / c[[0, 2]].sum()
    return two_factor_kernel(p, a, r)


def output_only_fit(counts, labels):
    """Pooled ordinary Markov model on current output, from identical observations."""
    c = np.asarray(counts).sum(axis=1)
    m = membership(np.asarray(labels, dtype=int), len(c))
    macro_counts = m.T @ c @ m
    row_mass = macro_counts.sum(axis=1)
    if (row_mass == 0).any():
        raise ValueError("Unobserved output class")
    return macro_counts / row_mass[:, None]
