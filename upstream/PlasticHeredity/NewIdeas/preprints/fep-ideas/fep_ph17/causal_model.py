from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from fep_ph1.types import RawObservation

from .state import composition_clr


BASE_TARGETS = 12
CLR_TARGETS = 100


@dataclass(frozen=True)
class TrainingData:
    """Balanced development transitions consumed by the frozen hybrid model."""

    matrix_ids: NDArray[np.int32]
    actions: NDArray[np.int8]
    coarse_features: NDArray[np.float64]
    rich_features: NDArray[np.float64]
    coarse_targets: NDArray[np.float64]
    rich_targets: NDArray[np.float64]

    def validate(self) -> None:
        count = len(self.matrix_ids)
        if self.matrix_ids.shape != (count,) or self.actions.shape != (count,):
            raise ValueError("training action shape does not match matrix IDs")
        matrices = (
            self.coarse_features,
            self.rich_features,
            self.coarse_targets,
            self.rich_targets,
        )
        if any(value.ndim != 2 or value.shape[0] != count for value in matrices):
            raise ValueError("training arrays have different row counts or ranks")
        if self.coarse_targets.shape[1] != BASE_TARGETS:
            raise ValueError("coarse target width is invalid")
        if self.rich_targets.shape[1] != BASE_TARGETS + CLR_TARGETS:
            raise ValueError("rich target width is invalid")
        if np.any((self.actions < 0) | (self.actions > 3)):
            raise ValueError("training action is outside the four-action alphabet")
        if any(not np.all(np.isfinite(value)) for value in matrices):
            raise ValueError("training data contain non-finite values")


def transition_target(
    composition: NDArray[np.integer],
    raw: RawObservation,
    completed: bool,
    true_regime: int,
    growth_budget: int,
    *,
    rich: bool,
) -> NDArray[np.float64]:
    cue = np.zeros(4, dtype=np.float64)
    cue[int(raw.cue)] = 1.0
    regime = np.zeros(3, dtype=np.float64)
    regime[int(true_regime)] = 1.0
    base = np.concatenate(
        (
            np.asarray(
                (
                    float(completed),
                    float(
                        np.log1p(max(0, raw.growth_steps))
                        / np.log1p(growth_budget)
                    ),
                    float(raw.boundary_similarity),
                    float(raw.alignment_score),
                    float(np.asarray(composition).sum() / 80.0),
                ),
                dtype=np.float64,
            ),
            cue,
            regime,
        )
    )
    return np.concatenate((base, composition_clr(composition))) if rich else base


__all__ = ("BASE_TARGETS", "CLR_TARGETS", "TrainingData", "transition_target")
