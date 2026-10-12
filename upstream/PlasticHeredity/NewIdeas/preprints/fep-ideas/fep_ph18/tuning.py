from __future__ import annotations

from typing import Any

from .config import EFE_COEFFICIENT, ExperimentConfig


def planner_selection_contract(config: ExperimentConfig) -> dict[str, Any]:
    """Return the prospective, outcome-blind planner selection rule."""

    return {
        "schema": "fep-ph18-planner-selection-contract-v1",
        "candidate_depths": list(config.planner_depths),
        "priority": "largest_matrix_scale_then_deepest_feasible_depth",
        "selector": "disposable_actual_kernel_runtime_only",
        "uses_development_or_confirmation_outcomes": False,
        "epistemic_coefficient": EFE_COEFFICIENT,
    }


__all__ = ("planner_selection_contract",)
