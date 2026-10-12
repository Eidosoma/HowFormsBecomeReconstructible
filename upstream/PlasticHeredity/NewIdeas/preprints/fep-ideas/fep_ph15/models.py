from __future__ import annotations

from dataclasses import replace

import numpy as np
from numpy.typing import NDArray

from fep_lab.types import CategoricalModel
from fep_ph1.models import (
    ModelCounts,
    hidden_state,
    load_model,
    model_digest,
    model_from_arrays,
    model_to_arrays,
    policy_array,
    prior_counts_from_model,
    save_model,
    scrambled_model,
    state_factors,
)

from .config import ExperimentConfig
from .types import PreferenceMode


def model_from_counts(
    counts: ModelCounts,
    config: ExperimentConfig,
    preference: PreferenceMode = PreferenceMode.BALANCED,
    *,
    information_gain: bool = True,
) -> CategoricalModel:
    base = __import__("fep_ph1.models", fromlist=["model_from_counts"]).model_from_counts(
        counts, config, information_gain=information_gain
    )
    similarity = (
        np.asarray((-0.50, 0.0, 0.50), dtype=np.float64)
        if preference == PreferenceMode.BALANCED
        else np.zeros(3, dtype=np.float64)
    )
    value = replace(
        base,
        C=(
            np.asarray((0.50, 0.20, -0.50, -4.00), dtype=np.float64),
            similarity,
            np.zeros(3, dtype=np.float64),
            np.zeros(4, dtype=np.float64),
        ),
        use_states_info_gain=bool(information_gain),
    )
    value.validate()
    return value


def with_preferences(
    model: CategoricalModel,
    preference: PreferenceMode,
    *,
    information_gain: bool,
) -> CategoricalModel:
    similarity = np.asarray((-0.50, 0.0, 0.50), dtype=np.float64) if preference == PreferenceMode.BALANCED else np.zeros(3, dtype=np.float64)
    value = replace(
        model,
        C=(
            np.asarray((0.50, 0.20, -0.50, -4.00), dtype=np.float64),
            similarity,
            np.zeros(3, dtype=np.float64),
            np.zeros(4, dtype=np.float64),
        ),
        use_states_info_gain=information_gain,
    )
    value.validate()
    return value


def action_costs(
    config: ExperimentConfig, adapt_cost: float
) -> NDArray[np.float64]:
    return np.asarray((0.0, adapt_cost, adapt_cost, config.action_cost_sample), dtype=np.float64)


__all__ = (
    "ModelCounts",
    "action_costs",
    "hidden_state",
    "load_model",
    "model_digest",
    "model_from_arrays",
    "model_from_counts",
    "model_to_arrays",
    "policy_array",
    "prior_counts_from_model",
    "save_model",
    "scrambled_model",
    "state_factors",
    "with_preferences",
)

