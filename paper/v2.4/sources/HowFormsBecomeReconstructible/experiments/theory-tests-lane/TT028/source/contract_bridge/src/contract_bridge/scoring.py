"""Symmetric translator block scorer (Part C).

Every candidate map — learned or baseline — is scored by the same
``score_map`` entry point over the same ``BLOCKS`` registry, with the same
frozen robust scaling. This encodes, by construction, the corrections to the
five audited EIDOSOMA-2 protocol deviations: a single frozen regularization,
robust scaling actually applied, identical block sets for every map,
independently evaluated baselines, and an occupancy-matched null map.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from eidosoma_ruliad_2.translator import (
    exact_state_coupling,
    fit_species_translator,
    fit_state_translator,
)

from .physics import Bundle

BLOCK_HORIZONS = (1, 2, 4, 8)


def _js_rows(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    left = left / np.maximum(left.sum(axis=1, keepdims=True), 1e-300)
    right = right / np.maximum(right.sum(axis=1, keepdims=True), 1e-300)
    middle = 0.5 * (left + right)

    def kl(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        safe = np.where(a > 0, a * np.log(np.maximum(a, 1e-300) / np.maximum(b, 1e-300)), 0.0)
        return safe.sum(axis=1)

    return 0.5 * (kl(left, middle) + kl(right, middle))


def _launch_coupling(bundle_a: Bundle, bundle_b: Bundle, coupling: np.ndarray) -> np.ndarray:
    sub = coupling[np.ix_(bundle_a.launch_rows, bundle_b.launch_rows)]
    sums = sub.sum(axis=1, keepdims=True)
    fallback = np.full_like(sub, 1.0 / sub.shape[1])
    return np.where(sums > 1e-300, sub / np.maximum(sums, 1e-300), fallback)


def _kernel_js(horizon: int) -> Callable[[Bundle, Bundle, np.ndarray], float]:
    def block(bundle_a: Bundle, bundle_b: Bundle, coupling: np.ndarray) -> float:
        power_a = np.linalg.matrix_power(bundle_a.transition, horizon)
        power_b = np.linalg.matrix_power(bundle_b.transition, horizon)
        mapped_a = power_a @ coupling
        mapped_b = coupling @ power_b
        death_left = np.maximum(0.0, 1.0 - power_a.sum(axis=1))
        death_right = np.maximum(0.0, 1.0 - mapped_b.sum(axis=1))
        left = np.column_stack([death_left, mapped_a])
        right = np.column_stack([death_right, mapped_b])
        return float(_js_rows(left, right).mean())

    return block


def _strict_mae(bundle_a: Bundle, bundle_b: Bundle, coupling: np.ndarray) -> float:
    mapped = _launch_coupling(bundle_a, bundle_b, coupling) @ bundle_b.strict
    return float(np.mean(np.abs(bundle_a.strict - mapped)))


def _time_log_mae(bundle_a: Bundle, bundle_b: Bundle, coupling: np.ndarray) -> float:
    mapped = coupling @ np.maximum(bundle_b.physical_time, 0.0)
    return float(
        np.mean(
            np.abs(
                np.log1p(np.maximum(bundle_a.physical_time, 0.0)) - np.log1p(mapped)
            )
        )
    )


def _destination_mae(bundle_a: Bundle, bundle_b: Bundle, coupling: np.ndarray) -> float:
    mapped_a = bundle_a.destination @ coupling
    mapped_b = _launch_coupling(bundle_a, bundle_b, coupling) @ bundle_b.destination
    return float(np.mean(np.abs(mapped_a - mapped_b)))


BLOCKS: tuple[tuple[str, Callable[[Bundle, Bundle, np.ndarray], float]], ...] = (
    ("kernel_js_1", _kernel_js(1)),
    ("kernel_js_2", _kernel_js(2)),
    ("kernel_js_4", _kernel_js(4)),
    ("kernel_js_8", _kernel_js(8)),
    ("strict_mae", _strict_mae),
    ("time_log_mae", _time_log_mae),
    ("destination_mae", _destination_mae),
)

BLOCK_NAMES: tuple[str, ...] = tuple(name for name, _ in BLOCKS)


def score_map(bundle_a: Bundle, bundle_b: Bundle, coupling: np.ndarray) -> dict[str, float]:
    """The single scoring entry point used for every candidate map."""
    coupling = np.asarray(coupling, dtype=np.float64)
    if coupling.shape != (len(bundle_a.states), len(bundle_b.states)):
        raise ValueError("coupling shape does not match the bundle state spaces")
    # Divide/overflow/invalid were the silent-warning classes in the audited
    # EIDOSOMA-2 run; underflow to zero is benign in probability products.
    with np.errstate(divide="raise", over="raise", invalid="raise"):
        return {name: fn(bundle_a, bundle_b, coupling) for name, fn in BLOCKS}


@dataclass(frozen=True)
class BlockScaler:
    """Per-block robust scales fitted on development scores, then frozen."""

    scales: tuple[tuple[str, float], ...]

    @classmethod
    def fit(cls, score_dicts: list[dict[str, float]]) -> "BlockScaler":
        if not score_dicts:
            raise ValueError("cannot fit a scaler on zero score dictionaries")
        scales = []
        for name in BLOCK_NAMES:
            values = np.asarray([scores[name] for scores in score_dicts], dtype=np.float64)
            q25, q75 = np.quantile(values, (0.25, 0.75))
            scale = q75 - q25
            if scale <= 0:
                scale = float(np.median(np.abs(values)))
            if scale <= 0:
                scale = 1.0
            scales.append((name, float(scale)))
        return cls(scales=tuple(scales))

    def composite(self, scores: dict[str, float]) -> float:
        lookup = dict(self.scales)
        if set(scores) != set(lookup):
            raise ValueError("score blocks do not match the frozen scaler blocks")
        return float(np.mean([scores[name] / lookup[name] for name in BLOCK_NAMES]))

    def as_dict(self) -> dict:
        return {name: scale for name, scale in self.scales}

    @classmethod
    def from_dict(cls, payload: dict) -> "BlockScaler":
        missing = set(BLOCK_NAMES) - set(payload)
        if missing:
            raise ValueError(f"frozen scaler is missing blocks: {sorted(missing)}")
        return cls(scales=tuple((name, float(payload[name])) for name in BLOCK_NAMES))


def occupancy_product_coupling(bundle_a: Bundle, bundle_b: Bundle) -> np.ndarray:
    """Occupancy-matched null: every source row maps to the target occupancy."""
    occupancy = bundle_b.destination.mean(axis=0)
    total = occupancy.sum()
    if total <= 0:
        occupancy = np.full(len(bundle_b.states), 1.0 / len(bundle_b.states))
    else:
        occupancy = occupancy / total
    return np.tile(occupancy, (len(bundle_a.states), 1))


def candidate_maps(
    bundle_a: Bundle,
    bundle_b: Bundle,
    beta_a: np.ndarray,
    beta_b: np.ndarray,
    *,
    regularization: float,
    random_permutation: tuple[int, ...],
    exact_permutation: tuple[int, ...] | None = None,
) -> dict[str, np.ndarray]:
    """All candidate maps for one pair, built through identical machinery.

    ``regularization`` must come from the capsule config; there is no
    default, so no call site can silently reintroduce a local constant.
    """
    species_coupling = fit_species_translator(beta_a, beta_b, regularization)
    maps: dict[str, np.ndarray] = {
        "learned": fit_state_translator(
            bundle_a.states, bundle_b.states, species_coupling, regularization
        ),
        "identity": np.eye(len(bundle_a.states), dtype=np.float64),
        "random_perm": exact_state_coupling(bundle_a.states, random_permutation),
        "occupancy": occupancy_product_coupling(bundle_a, bundle_b),
    }
    if exact_permutation is not None:
        maps["exact"] = exact_state_coupling(bundle_a.states, exact_permutation)
    return maps
