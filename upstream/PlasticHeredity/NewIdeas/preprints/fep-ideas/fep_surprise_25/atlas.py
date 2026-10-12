from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fep_surprise_15.observers import ObserverEnsemble
from fep_surprise_2.atlas import (
    ObserverLike,
    RelabeledObserverEnsemble,
    destination_label,
    mismatch_jump,
    shelf_profile,
)


@dataclass
class Atlas25Registry:
    """Simulated target atlases and exact relabeled views of those atlases."""

    actual: dict[str, ObserverEnsemble]
    views: dict[str, tuple[str, np.ndarray]]

    def get(self, key: str) -> ObserverLike:
        if key in self.actual:
            return self.actual[key]
        actual_key, order = self.views[key]
        return RelabeledObserverEnsemble(self.actual[actual_key], order)


__all__ = [
    "Atlas25Registry",
    "RelabeledObserverEnsemble",
    "destination_label",
    "mismatch_jump",
    "shelf_profile",
]
