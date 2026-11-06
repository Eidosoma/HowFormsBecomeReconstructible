"""Evaluator-only scores on batched (..., 16, 16) fields. No controller imports this.

Conventions (frozen with the design): sign b(x) = x > 0, so zero counts as negative;
amplitude eligibility |V| > 0.2 strictly; every score divides by all 256 sites.
"""
from __future__ import annotations

import numpy as np

from .ops import bands

ELIGIBLE = 0.2


def sign_agreement(V, target):
    return ((V > 0) == (target > 0)).mean(axis=(-2, -1))


def amplitude(V):
    return (np.abs(V) > ELIGIBLE).mean(axis=(-2, -1))


def qualified(V, target):
    return (((V > 0) == (target > 0)) & (np.abs(V) > ELIGIBLE)).mean(axis=(-2, -1))


def joint(V, target):
    """Counts [[mismatch & ineligible, mismatch & eligible], [match & ineligible, match & eligible]]."""
    m = (V > 0) == (target > 0)
    a = np.abs(V) > ELIGIBLE
    cell = lambda x, y: ((m == x) & (a == y)).sum(axis=(-2, -1))
    return np.stack([np.stack([cell(False, False), cell(False, True)], -1),
                     np.stack([cell(True, False), cell(True, True)], -1)], -2)


def recognition(V, templates, own):
    """Tie-split decoder credit: correlate V with each template; credit 1/k when own ties k."""
    corr = np.einsum("...ij,kij->...k", V, templates)
    best = corr.max(axis=-1, keepdims=True)
    winners = np.isclose(corr, best, rtol=0.0, atol=1e-12)
    own_wins = np.take_along_axis(winners, np.asarray(own)[..., None], -1)[..., 0]
    return np.where(own_wins, 1.0 / winners.sum(axis=-1), 0.0)


def band_errors(V, target):
    """Squared error of V - target in each orthogonal band (offline only)."""
    return {k: (b ** 2).sum(axis=(-2, -1)) for k, b in bands(V - target).items()}


def summary(V, target, templates=None, own=None) -> dict:
    out = {"sign": sign_agreement(V, target), "amplitude": amplitude(V),
           "qualified": qualified(V, target)}
    out.update({f"err_{k}": v for k, v in band_errors(V, target).items()})
    if templates is not None:
        out["recognition"] = recognition(V, templates, own)
    return out
