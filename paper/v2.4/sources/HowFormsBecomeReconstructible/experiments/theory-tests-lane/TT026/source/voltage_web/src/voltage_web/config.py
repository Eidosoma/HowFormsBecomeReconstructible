"""Frozen configuration for the voltage-sheet substrate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class VoltageConfig:
    mode: str = "full"
    height: int = 16
    width: int = 16
    dt: float = 0.2
    # Frozen at the round-5 screen operating point (the only point passing
    # all six ensemble criteria; interior in g — the coupling sweet spot).
    coupling: float = 1.0
    sigma: float = 0.30
    well_asym: float = 0.0         # a: relative well depth
    threshold_spread: float = 0.2  # quenched per-cell heterogeneity (pinning)
    tissue_tag: str = "voltage-tissue-v1"
    tissue_index: int = 0          # reference tissue for the screen
    resting: float = -1.0
    copy_jitter: float = 0.05
    # Generations: activity gated on binarized flips; budget screened in
    # multiples of the cell count (the E24 clock lesson).
    activity_budget: int = 64
    t_min_sweeps: int = 4
    t_max_sweeps: int = 64
    # Shared observer constants (verbatim).
    inherit_threshold: float = 0.9
    coherence_threshold: float = 0.9
    distinct_threshold: float = 0.85
    strict_run: int = 8
    strict_horizon: int = 32
    mass_quantile: float = 0.75
    # Campaign shape.
    n_seeds: int = 16
    futures: int = 64
    strict_band: tuple = (0.005, 0.5)
    trajectory_seed_tag: str = "voltage-traj-v1"

    @classmethod
    def tiny(cls) -> "VoltageConfig":
        return cls(
            mode="tiny", height=8, width=8, activity_budget=16, strict_run=3,
            strict_horizon=8, n_seeds=4, futures=8, t_max_sweeps=24,
        )

    @property
    def cells(self) -> int:
        return self.height * self.width

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: VoltageConfig) -> Path:
    return capsule_root() / "results" / config.mode
