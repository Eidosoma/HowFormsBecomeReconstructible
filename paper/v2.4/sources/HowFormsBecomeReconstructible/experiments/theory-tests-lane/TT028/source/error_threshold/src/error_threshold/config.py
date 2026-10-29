"""Frozen configuration for E55."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

SIGMA_GRID = (0.0, 0.02, 0.045, 0.1, 0.22, 0.5, 1.1, 2.4, 5.0)
COMPLEXITIES = (2, 4, 8, 16)


@dataclass(frozen=True)
class EigenConfig:
    mode: str = "full"
    n_tissues: int = 2
    futures: int = 6
    settle_sweeps: int = 120
    imprint_hold_sweeps: int = 1000   # 2/rho: R adopts the message
    imprint_hold: float = 1.2
    render_sweeps: int = 500          # 1/rho: the tissue's own rendition
    cycles: int = 12
    inter_fission: int = 1000         # 2/rho (review #21)
    amp_threshold: float = 0.2
    # Selection arm (quasispecies rescue) at complexity 4.
    selection_complexity: int = 4
    tournament: int = 3
    # Freedom check.
    zap_sweeps: int = 8
    zap_recover: int = 300
    freedom_bar: float = 0.10
    trajectory_seed_tag: str = "eigen-v1"

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: EigenConfig) -> Path:
    return capsule_root() / "results" / config.mode
