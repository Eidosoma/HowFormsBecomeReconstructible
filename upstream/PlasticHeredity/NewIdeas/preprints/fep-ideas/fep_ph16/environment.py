from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import numpy as np

from fep_lab.integrity import canonical_json_bytes, sha256_bytes
from fep_ph15.environment import EnvironmentDesign, GardGoalAlignmentEnvironment


@dataclass(frozen=True)
class PlanningSeeds:
    chemistry: int
    environment: int
    observation: int


def clone_environment(environment: GardGoalAlignmentEnvironment) -> GardGoalAlignmentEnvironment:
    """Exact state snapshot without copying immutable 100 x 100 physics arrays.

    The inherited environment mutates only ``composition``, three RNGs, and
    scalar regime/terminal fields after construction. A shallow object copy
    therefore safely shares the fixed beta landscapes, partitions, target
    scores, frozen dataclasses, and thresholds. Explicit RNG-state copies keep
    the snapshot trajectory-identical and independent.
    """

    value = copy.copy(environment)
    value.composition = environment.composition.copy()
    for name in ("chemistry_rng", "environment_rng", "observation_rng"):
        source = getattr(environment, name)
        bit_generator = type(source.bit_generator)()
        bit_generator.state = copy.deepcopy(source.bit_generator.state)
        setattr(value, name, np.random.Generator(bit_generator))
    return value


def planning_clone(
    environment: GardGoalAlignmentEnvironment, seeds: PlanningSeeds
) -> GardGoalAlignmentEnvironment:
    """Snapshot physical state, then replace all RNGs with planning-only streams."""

    value = clone_environment(environment)
    value.chemistry_rng = np.random.default_rng(seeds.chemistry)
    value.environment_rng = np.random.default_rng(seeds.environment)
    value.observation_rng = np.random.default_rng(seeds.observation)
    return value


def environment_fingerprint(environment: GardGoalAlignmentEnvironment) -> str:
    payload: dict[str, Any] = {
        "composition": environment.composition.tolist(),
        "base_regime": int(environment.base_regime),
        "regime": int(environment.regime),
        "terminal": bool(environment.terminal),
        "chemistry_rng": environment.chemistry_rng.bit_generator.state,
        "environment_rng": environment.environment_rng.bit_generator.state,
        "observation_rng": environment.observation_rng.bit_generator.state,
    }
    return sha256_bytes(canonical_json_bytes(payload))


__all__ = (
    "EnvironmentDesign",
    "GardGoalAlignmentEnvironment",
    "PlanningSeeds",
    "clone_environment",
    "environment_fingerprint",
    "planning_clone",
)
