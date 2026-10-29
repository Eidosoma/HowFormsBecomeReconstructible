"""Estimator and gate power calibration against exact truth (Part E).

Each Monte-Carlo future is an iid Bernoulli draw from the cell's true strict
probability, so estimator behavior is computable from binomial draws against
the exact truth vector, without any trajectory simulation.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import binom, spearmanr

from .artifacts import seed_rng


def rank_reliability(
    p_truth: np.ndarray,
    budgets: tuple[int, ...],
    replicates: int,
    seed_tag: str,
    *,
    group: np.ndarray | None = None,
) -> list[dict]:
    """Simulated rank reliability of binomial estimators per futures budget.

    Reports Spearman agreement with the truth and split-half Spearman
    between two independent half-budget estimates; when ``group`` is given
    (e.g., a rule id per cell), group-mean estimates are also scored.
    """
    p = np.asarray(p_truth, dtype=np.float64)
    if np.any(p < 0) or np.any(p > 1):
        raise ValueError("truth probabilities must lie in [0, 1]")
    rows: list[dict] = []
    for budget in budgets:
        rng = seed_rng(seed_tag, budget)
        truth_rho = np.empty(replicates)
        split_rho = np.empty(replicates)
        group_truth_rho = np.empty(replicates)
        half = max(budget // 2, 1)
        for r in range(replicates):
            estimate = rng.binomial(budget, p) / budget
            half_a = rng.binomial(half, p) / half
            half_b = rng.binomial(half, p) / half
            truth_rho[r] = spearmanr(estimate, p).statistic
            split_rho[r] = spearmanr(half_a, half_b).statistic
            if group is not None:
                order = np.argsort(group, kind="stable")
                boundaries = np.flatnonzero(np.diff(group[order])) + 1
                grouped_est = np.array(
                    [chunk.mean() for chunk in np.split(estimate[order], boundaries)]
                )
                grouped_truth = np.array(
                    [chunk.mean() for chunk in np.split(p[order], boundaries)]
                )
                group_truth_rho[r] = spearmanr(grouped_est, grouped_truth).statistic
        row = {
            "budget": int(budget),
            "replicates": int(replicates),
            "spearman_vs_truth_mean": float(np.nanmean(truth_rho)),
            "spearman_vs_truth_lo": float(np.nanquantile(truth_rho, 0.025)),
            "spearman_vs_truth_hi": float(np.nanquantile(truth_rho, 0.975)),
            "split_half_spearman_mean": float(np.nanmean(split_rho)),
            "split_half_spearman_lo": float(np.nanquantile(split_rho, 0.025)),
            "split_half_spearman_hi": float(np.nanquantile(split_rho, 0.975)),
        }
        if group is not None:
            row["group_spearman_vs_truth_mean"] = float(np.nanmean(group_truth_rho))
        rows.append(row)
    return rows


def gate_operating_characteristics(
    p_truth: np.ndarray,
    budgets: tuple[int, ...],
    gate_grid: tuple[float, ...],
) -> list[dict]:
    """Exact per-cell threshold-gate error rates from binomial tails."""
    p = np.asarray(p_truth, dtype=np.float64)
    rows: list[dict] = []
    for budget in budgets:
        for gate in gate_grid:
            critical = int(np.ceil(gate * budget))
            pass_probability = binom.sf(critical - 1, budget, p)
            below = p < gate
            at_or_above = ~below
            rows.append(
                {
                    "budget": int(budget),
                    "gate": float(gate),
                    "n_below": int(below.sum()),
                    "n_at_or_above": int(at_or_above.sum()),
                    "false_pass_rate": (
                        float(pass_probability[below].mean()) if below.any() else 0.0
                    ),
                    "false_fail_rate": (
                        float(1.0 - pass_probability[at_or_above].mean())
                        if at_or_above.any()
                        else 0.0
                    ),
                }
            )
    return rows
