"""Frozen configuration for the motile substrate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

GROW_RUNGS = ("D", "G", "H")


@dataclass(frozen=True)
class GrowConfig:
    mode: str = "full"
    adhesion_j: float = 1.0
    chemotaxis_chi: float = 1.0
    temperature: float = 0.5
    phases_per_sweep: int = 2     # one horizontal + one vertical Kawasaki phase
    # Parallel-update fix (recorded): dense simultaneous acceptance is
    # pathological (a checkerboard where every swap "improves" maps to
    # itself — each pair's delta assumes still neighbors). Thin proposals.
    proposal_fraction: float = 0.25
    motility_seed_tag: str = "grow-motility-v1"
    trajectory_seed_tag: str = "grow-traj-v1"

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: GrowConfig) -> Path:
    return capsule_root() / "results" / config.mode
