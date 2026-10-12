from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from fep_ph1.endpoints import f12_break_renewal, strict_eight
from fep_ph1.gard import cosine_similarity

from .types import ExternalRegime


def _longest_run(values: NDArray[np.bool_]) -> int:
    best = current = 0
    for value in np.asarray(values, dtype=bool):
        current = current + 1 if value else 0
        best = max(best, current)
    return best


def _recovery_after_shock(
    decision_regime: NDArray[np.int64], completed: NDArray[np.bool_], inherited: NDArray[np.bool_]
) -> float:
    shocks = np.flatnonzero(decision_regime == int(ExternalRegime.SHOCK))
    if shocks.size == 0:
        return float("nan")
    recovered = []
    for shock in shocks:
        end = min(len(completed), int(shock) + 4)
        recovered.append(bool(np.any(completed[shock:end] & inherited[shock:end])))
    return float(np.mean(recovered))


def episode_metrics(arrays: dict[str, NDArray], horizon: int) -> dict[str, float]:
    completed = np.asarray(arrays["completed"], dtype=bool)
    similarity = np.asarray(arrays["similarity"], dtype=np.float64)
    inherited = completed & (similarity > 0.90)
    observed = int(completed.sum())
    growth = np.asarray(arrays["growth_steps"], dtype=np.float64)[completed]
    actions = np.asarray(arrays["executed_actions"], dtype=np.int64)
    regimes = np.asarray(arrays["decision_regime"], dtype=np.int64)
    beliefs = np.asarray(arrays["beliefs"], dtype=np.float64)
    regime_probability = np.stack(
        [beliefs[:, index * 3 : (index + 1) * 3].sum(axis=1) for index in range(3)], axis=1
    )
    valid_belief = (regimes >= 0) & np.all(np.isfinite(regime_probability), axis=1)
    if np.any(valid_belief):
        positions = np.flatnonzero(valid_belief)
        selected = np.maximum(regime_probability[positions, regimes[valid_belief]], 1e-300)
        log_loss = float(-np.mean(np.log(selected)))
        truth = np.eye(3)[regimes[valid_belief]]
        brier = float(np.mean(np.sum((regime_probability[valid_belief] - truth) ** 2, axis=1)))
    else:
        log_loss = brier = float("nan")
    anchor_decay = float("nan")
    if observed and arrays["parents"][0].sum() > 0:
        anchor_decay = 1.0 - cosine_similarity(arrays["parents"][0], arrays["compositions"][observed - 1])
    vfe = np.asarray(arrays["vfe"], dtype=np.float64)
    information = np.asarray(arrays["state_information_gain"], dtype=np.float64)
    return {
        "completion_fraction": observed / horizon,
        "survival_to_horizon": float(observed == horizon),
        "time_to_terminal": float(observed if observed < horizon else horizon + 1),
        "growth_mean": float(np.mean(growth)) if growth.size else float("nan"),
        "growth_cv": float(np.std(growth) / max(float(np.mean(growth)), 1e-12)) if growth.size else float("nan"),
        "recovery_after_shock": _recovery_after_shock(regimes, completed, inherited),
        "inherited_fixed_fraction": float(inherited.sum() / horizon),
        "inherited_observed_fraction": float(inherited.sum() / observed) if observed else 0.0,
        "longest_inherited_run": float(_longest_run(inherited)),
        "turnover": float(np.mean(1.0 - similarity[completed])) if observed else 1.0,
        "anchor_decay": anchor_decay,
        "abstract_action_cost": float(np.sum(arrays["abstract_action_cost"])),
        "physical_action_cost": float(np.sum(arrays["physical_action_cost"])),
        "sample_fraction": float(np.mean(actions == 3)),
        "adapt_fraction": float(np.mean((actions == 1) | (actions == 2))),
        "regime_log_loss": log_loss,
        "regime_brier": brier,
        "mean_vfe": float(np.mean(vfe[np.isfinite(vfe)])) if np.any(np.isfinite(vfe)) else float("nan"),
        "mean_state_information_gain": float(np.mean(information[np.isfinite(information)])) if np.any(np.isfinite(information)) else float("nan"),
        "f12": float(f12_break_renewal(completed, similarity)),
        "strict8": float(strict_eight(completed, similarity, arrays["parents"], arrays["compositions"])),
    }


__all__ = ("episode_metrics", "f12_break_renewal", "strict_eight")

