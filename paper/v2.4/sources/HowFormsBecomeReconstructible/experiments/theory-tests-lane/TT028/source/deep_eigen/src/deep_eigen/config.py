"""Frozen configuration for E68."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

CORR_GRID = (1.0, 0.95, 0.9, 0.8, 0.65, 0.5, 0.3, 0.1)
PREROUND_CORRS = (0.9, 0.7, 0.5, 0.3)


@dataclass(frozen=True)
class DeepEigenConfig:
    mode: str = "full"
    n_tissues: int = 3
    futures: int = 4
    norm: float = 0.3
    write_lambda: float = 0.001      # rho/2, writing ON throughout
    settle_sweeps: int = 120
    imprint_sweeps: int = 1000       # 2/rho
    imprint_hold: float = 1.2
    cycles: int = 12
    inter_fission: int = 1000
    amp_threshold: float = 0.2
    chance: float = 0.5
    bootstrap: int = 200
    trajectory_seed_tag: str = "deep-eigen-v1"

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: DeepEigenConfig) -> Path:
    return capsule_root() / "results" / config.mode
