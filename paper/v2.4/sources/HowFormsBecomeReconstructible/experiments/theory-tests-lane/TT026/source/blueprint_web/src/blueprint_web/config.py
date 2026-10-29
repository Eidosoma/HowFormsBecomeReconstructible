"""Frozen configuration for the blueprint substrates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

BP_RUNGS = ("A", "T", "S", "Y", "TM")


@dataclass(frozen=True)
class BlueprintConfig:
    mode: str = "full"
    # Rung T dials (the freedom-vs-enforcement square; calibrated).
    # Frozen at the calibration square's chosen point: the only passing
    # enforcement gain (0.2; 0.4 collapses freedom, 0.8 enslaves) at the
    # slowest reference clock (highest conversion, 0.188).
    rho: float = 0.002
    c_m: float = 0.2
    # Rung S staged growth.
    seed_side: int = 4
    # Rung Y blend.
    coarse_weight: float = 0.5
    # Rung TM motility (from the frozen growing_web operating point).
    trajectory_seed_tag: str = "blueprint-traj-v1"
    motility_seed_tag: str = "blueprint-motility-v1"

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: BlueprintConfig) -> Path:
    return capsule_root() / "results" / config.mode
