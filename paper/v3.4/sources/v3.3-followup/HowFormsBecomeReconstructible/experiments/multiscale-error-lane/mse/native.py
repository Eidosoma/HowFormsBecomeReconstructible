"""Native reference-sheet physics, independently restated.

Sources (read-only; hashes in SOURCE_MANIFEST.json): voltage_web.engine.sheet_step,
ladder_web.engine.ladder_step rung "A", blueprint_web.engine.blueprint_step rung "T",
and the L15/L17 protocols. Expression order follows the sources so that the identity
route reproduces blueprint_step bit for bit under common draws (tests/test_native.py).

Differences from the sources, all deliberate: noise arrives as an argument (explicit
addressing instead of one shared generator); the comparator, reference update and the
passive capture Q of L17 are separate stages in mse.engine; nothing here divides,
grows or writes theta.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

import numpy as np

SIDE = 16
LEVELS = ("site", "region", "sheet")


@dataclass(frozen=True)
class Params:
    side: int = SIDE
    dt: float = 0.2
    coupling: float = 1.0
    sigma: float = 0.3
    well_asym: float = 0.0
    threshold_spread: float = 0.2
    ema_rate: float = 0.1
    gain: float = 0.2      # comparator c, BlueprintConfig.c_m
    rho: float = 0.002     # reference and capture rate, BlueprintConfig.rho
    bound: float = 2.0

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


NATIVE = Params()


def address(tag: str, *parts) -> np.random.Generator:
    """PCG64 seeded from SHA-256 of a semantic address (experiments/common.py convention).

    Addresses name the block, case, phase and stream, never an arm or condition.
    """
    key = json.dumps([tag, *parts], separators=(",", ":")).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:16], "little")
    return np.random.Generator(np.random.PCG64(seed))


def center(x: np.ndarray) -> np.ndarray:
    return x - x.mean(axis=(-2, -1), keepdims=True)


def neighbours(V: np.ndarray) -> np.ndarray:
    return (np.roll(V, 1, -2) + np.roll(V, -1, -2)
            + np.roll(V, 1, -1) + np.roll(V, -1, -1)) / 4.0


def sheet(V, theta, z, p: Params = NATIVE):
    """Step 1: conserved double-well drift plus centred additive noise, clipped (V-tilde).

    z holds standard normal draws of V's shape. The noise is not scaled by dt (native).
    """
    drift = V - V ** 3 + p.well_asym + theta + p.coupling * (neighbours(V) - V)
    drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
    noise = p.sigma * z
    noise = noise - noise.mean(axis=(-2, -1), keepdims=True)
    return np.clip(V + p.dt * drift + noise, -p.bound, p.bound)


def moving_average(ema, V, p: Params = NATIVE):
    """Step 2: the fast moving average, read from V-tilde."""
    return (1.0 - p.ema_rate) * ema + p.ema_rate * V


def thresholds(rng: np.random.Generator, p: Params = NATIVE) -> np.ndarray:
    """Quenched environmental field theta: white, target-independent, unprojected."""
    return p.threshold_spread * rng.standard_normal((p.side, p.side))


def half_plane(kind: int, amplitude: float = 1.2, side: int = SIDE) -> np.ndarray:
    """The four supplied messages: 0 left/right, 1 top/bottom, 2 and 3 their reversals.

    Kinds 0 and 1 equal voltage_web.engine.launch_pattern(0 or 1) times the amplitude.
    """
    field = np.full((side, side), -1.0)
    if kind % 2 == 0:
        field[:, : side // 2] = 1.0
    else:
        field[: side // 2, :] = 1.0
    if kind >= 2:
        field = -field
    return amplitude * field
