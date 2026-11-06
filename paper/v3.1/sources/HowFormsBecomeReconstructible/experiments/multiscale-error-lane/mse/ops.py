"""Batched spatial operators on (..., 16, 16) fields.

These are mathematical aggregates standing in for communication; mse.engine logs the
messages each one implies. The single-field fixtures in ../operators.py remain the
design record; tests/test_ops.py checks these against them.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .native import LEVELS, SIDE, center

PATCH = {"site": 1, "region": 4, "sheet": 8}
MESSAGES = {"site": 256, "region": 16, "sheet": 4}   # scalars leaving the sensing stage


def block_projection(x: np.ndarray, size: int) -> np.ndarray:
    if size == 1:
        return x
    n = SIDE // size
    means = x.reshape(*x.shape[:-2], n, size, n, size).mean(axis=(-3, -1))
    return np.repeat(np.repeat(means, size, axis=-2), size, axis=-1)


def project(x: np.ndarray, level: str) -> np.ndarray:
    if level == "site":
        return x
    if level == "region":
        return block_projection(x, 4)
    if level == "sheet":
        return center(block_projection(x, 8))
    raise ValueError(f"Unknown level: {level}")


@dataclass(frozen=True)
class Op:
    """A projection on a grid displaced by `offset` sites (roll back, project, roll forward)."""
    level: str = "site"
    offset: tuple = (0, 0)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        if self.level == "site" or self.offset == (0, 0):
            return project(x, self.level)
        back = tuple(-int(k) for k in self.offset)
        return np.roll(project(np.roll(x, back, axis=(-2, -1)), self.level),
                       self.offset, axis=(-2, -1))


def canonical(sensor: Op, actuator: Op) -> Op | None:
    """The single operator equal to actuator(sensor(x)) for aligned nested grids.

    Aligned site/region/sheet projections compose to the coarser one, so the nine aligned
    pairs are three maps. Composing through the canonical operator makes aliased arms
    bit-identical rather than equal to rounding. Returns None when the pair does not
    reduce (displaced grids).
    """
    if sensor.offset != (0, 0) and sensor.level != "site":
        return None
    if actuator.offset != (0, 0) and actuator.level != "site":
        return None
    order = LEVELS.index
    return Op(max(sensor.level, actuator.level, key=order))


def bands(x: np.ndarray) -> dict:
    """Offline orthogonal decomposition: fine, regional, collective, constant."""
    p4, p8 = block_projection(x, 4), block_projection(x, 8)
    dc = np.broadcast_to(x.mean(axis=(-2, -1), keepdims=True), x.shape)
    return {"fine": x - p4, "regional": p4 - p8, "collective": p8 - dc, "constant": dc}


def band_power(x: np.ndarray) -> dict:
    return {k: (v ** 2).sum(axis=(-2, -1)) for k, v in bands(x).items()}
