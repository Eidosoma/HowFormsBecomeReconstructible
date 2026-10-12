from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .gard import cosine_similarity


def _longest_run(values: NDArray[np.bool_]) -> int:
    best = 0
    current = 0
    for value in np.asarray(values, dtype=bool):
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def f12_break_renewal(
    completed: NDArray,
    similarities: NDArray,
    threshold: float = 0.9,
) -> bool:
    valid = np.asarray(completed, dtype=bool)[:12]
    inherited = valid & (np.asarray(similarities, dtype=np.float64)[:12] > threshold)
    breaks = np.flatnonzero(valid & ~inherited)
    if breaks.size == 0:
        return False
    first = int(breaks[0])
    for start in range(first + 1, max(first + 1, len(inherited) - 2)):
        if bool(inherited[start : start + 3].all()):
            return True
    return False


def strict_eight(
    completed: NDArray,
    similarities: NDArray,
    parents: NDArray,
    daughters: NDArray,
    inheritance_threshold: float = 0.90,
    coherence_threshold: float = 0.90,
    distinctness_threshold: float = 0.85,
) -> bool:
    valid = np.asarray(completed, dtype=bool)
    inherited = valid & (
        np.asarray(similarities, dtype=np.float64) > inheritance_threshold
    )
    breaks = np.flatnonzero(valid & ~inherited)
    if breaks.size == 0:
        return False
    first_break = int(breaks[0])
    anchor = np.asarray(parents[first_break], dtype=np.float64)
    anchor_norm = max(float(np.linalg.norm(anchor)), np.finfo(np.float64).tiny)
    daughter_values = np.asarray(daughters, dtype=np.float64)
    daughter_norms = np.maximum(
        np.linalg.norm(daughter_values, axis=1), np.finfo(np.float64).tiny
    )
    normalized = daughter_values / daughter_norms[:, None]
    anchor_similarity = normalized @ (anchor / anchor_norm)
    last_start = len(inherited) - 8
    for start in range(first_break + 1, last_start + 1):
        if not bool(inherited[start : start + 8].all()):
            continue
        anchor_max = float(np.max(anchor_similarity[start : start + 8]))
        if anchor_max > distinctness_threshold:
            continue
        window = normalized[start : start + 8]
        similarity = window @ window.T
        pairwise = float(np.min(similarity[np.triu_indices(8, k=1)]))
        if pairwise > coherence_threshold:
            return True
    return False


def episode_metrics(arrays: dict[str, NDArray], horizon: int) -> dict[str, float]:
    completed = np.asarray(arrays["completed"], dtype=bool)
    similarity = np.asarray(arrays["similarity"], dtype=np.float64)
    inherited = completed & (similarity > 0.9)
    observed = int(completed.sum())
    completed_similarity = similarity[completed]
    growth = np.asarray(arrays["growth_steps"], dtype=np.float64)[completed]
    actions = np.asarray(arrays["executed_actions"], dtype=np.int64)
    decision_regime = np.asarray(arrays["decision_regime"], dtype=np.int64)
    beliefs = np.asarray(arrays["beliefs"], dtype=np.float64)
    regime_probability = np.stack(
        [beliefs[:, index * 3 : (index + 1) * 3].sum(axis=1) for index in range(3)],
        axis=1,
    )
    valid_belief = (
        (decision_regime >= 0)
        & np.all(np.isfinite(regime_probability), axis=1)
    )
    if np.any(valid_belief):
        selected = np.maximum(
            regime_probability[np.flatnonzero(valid_belief), decision_regime[valid_belief]],
            1e-300,
        )
        regime_log_loss = float(-np.mean(np.log(selected)))
        truth = np.eye(3)[decision_regime[valid_belief]]
        regime_brier = float(
            np.mean(np.sum((regime_probability[valid_belief] - truth) ** 2, axis=1))
        )
    else:
        regime_log_loss = float("nan")
        regime_brier = float("nan")
    turnover = (
        float(np.mean(1.0 - completed_similarity))
        if completed_similarity.size
        else 1.0
    )
    anchor_decay = float("nan")
    if observed:
        anchor = np.asarray(arrays["parents"][0], dtype=np.int64)
        final = np.asarray(arrays["compositions"][observed - 1], dtype=np.int64)
        anchor_decay = 1.0 - cosine_similarity(anchor, final)
    return {
        "completion_fraction": observed / horizon,
        "survival_to_horizon": float(observed == horizon),
        "time_to_terminal": float(observed if observed < horizon else horizon + 1),
        "growth_mean": float(np.mean(growth)) if growth.size else float(horizon * 1000),
        "growth_cv": (
            float(np.std(growth) / max(float(np.mean(growth)), 1e-12))
            if growth.size
            else float("nan")
        ),
        "inherited_fixed_fraction": float(inherited.sum() / horizon),
        "inherited_observed_fraction": (
            float(inherited.sum() / observed) if observed else 0.0
        ),
        "longest_inherited_run": float(_longest_run(inherited)),
        "turnover": turnover,
        "anchor_decay": anchor_decay,
        "abstract_action_cost": float(np.sum(arrays["abstract_action_cost"])),
        "physical_action_cost": float(np.sum(arrays["physical_action_cost"])),
        "sample_fraction": float(np.mean(actions == 3)),
        "adapt_fraction": float(np.mean((actions == 1) | (actions == 2))),
        "regime_log_loss": regime_log_loss,
        "regime_brier": regime_brier,
        "mean_vfe": float(np.nanmean(arrays["vfe"]))
        if np.any(np.isfinite(arrays["vfe"]))
        else float("nan"),
        "mean_state_information_gain": float(
            np.nanmean(arrays["state_information_gain"])
        )
        if np.any(np.isfinite(arrays["state_information_gain"]))
        else float("nan"),
        "f12": float(f12_break_renewal(completed, similarity)),
        "strict8": float(
            strict_eight(
                completed,
                similarity,
                arrays["parents"],
                arrays["compositions"],
            )
        ),
    }
