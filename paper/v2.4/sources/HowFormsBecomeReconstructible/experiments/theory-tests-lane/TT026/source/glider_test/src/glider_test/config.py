"""Frozen configuration for the glider test."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class LifeConfig:
    mode: str = "full"
    height: int = 16
    width: int = 16
    flip_noise: float = 0.002
    copy_error: float = 0.005
    activity_budget: int = 48
    t_min_sweeps: int = 4
    t_max_sweeps: int = 64
    # Shared observer constants.
    inherit_threshold: float = 0.9
    coherence_threshold: float = 0.9
    distinct_threshold: float = 0.85
    strict_run: int = 8
    strict_horizon: int = 32
    # Campaign shape.
    n_futures: int = 256
    n_random_seeds: int = 32
    mass_quantile: float = 0.75  # dev round 3: 0.5 keeps only single-cell windows
    trajectory_seed_tag: str = "life-traj-v1"

    @classmethod
    def tiny(cls) -> "LifeConfig":
        return cls(
            mode="tiny", height=12, width=12, activity_budget=24, strict_run=3,
            strict_horizon=8, n_futures=32, n_random_seeds=6, t_max_sweeps=24,
        )

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: LifeConfig) -> Path:
    return capsule_root() / "results" / config.mode
