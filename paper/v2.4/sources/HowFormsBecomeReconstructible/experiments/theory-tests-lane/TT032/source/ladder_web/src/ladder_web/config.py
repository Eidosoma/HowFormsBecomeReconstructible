"""Frozen configuration for the machinery ladder."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path

RUNGS = ("A", "B", "C", "D")


@dataclass(frozen=True)
class LadderConfig:
    mode: str = "full"
    n_tissues: int = 12
    futures: int = 64
    # Rung B: anchors — niche cells clamped to their wild-pattern values,
    # re-imposed every sweep and after every fission (tissue property).
    n_anchors: int = 8
    anchor_tag: str = "ladder-anchor-v1"
    # Rung C: morphogen — M = k-pass neighbor-smoothed binarized V,
    # feeding back as c_m * (M - sheet mean of M).
    morphogen_passes: int = 4
    morphogen_gain: float = 0.4
    # Rung D: stress — s = |V - EMA(V)|, diffused; gates coupling and noise.
    ema_rate: float = 0.1
    stress_passes: int = 3
    # Round 3 (recorded): with the organizer comparator, alpha_g = 2.0
    # over-stabilized rung D (H> 0.99, breaks vanished) — the error-gated
    # coupling locked identity. Trimmed to keep the heredity straddle.
    alpha_g: float = 0.6
    alpha_sigma: float = 1.5
    # Light cone protocol.
    displacement_ladder: tuple = (2, 4, 8)
    displacement_magnitude: float = 0.8
    recovery_sweeps: int = 60
    persistence_horizon: int = 24
    trajectory_seed_tag: str = "ladder-traj-v2"  # round 2: organizer field

    @classmethod
    def tiny(cls) -> "LadderConfig":
        return cls(
            mode="tiny", n_tissues=2, futures=8, n_anchors=4,
            displacement_ladder=(2,), recovery_sweeps=20,
            persistence_horizon=8,
        )

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: LadderConfig) -> Path:
    return capsule_root() / "results" / config.mode
