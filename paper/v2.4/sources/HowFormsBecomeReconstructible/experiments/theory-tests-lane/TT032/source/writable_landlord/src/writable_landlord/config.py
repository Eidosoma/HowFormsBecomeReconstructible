"""Frozen configuration for E66."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

CAPACITY_NORMS = (0.3, 0.4, 0.5)
GAIN_GRID = (0.2, 0.3, 0.4, 0.6, 0.9)
# Calibration round 0 (recorded): the register's lambda = rho/50 gives
# a 25k-sweep write clock, beyond the wave's budget; the grid is
# {rho/2, rho/10} — the lambda << rho separation is kept by rho/10.
LAMBDA_FRACS = (0.5, 0.1)


@dataclass(frozen=True)
class LandlordConfig:
    mode: str = "full"
    n_tissues: int = 4
    futures: int = 6
    settle_sweeps: int = 120
    imprint_sweeps: int = 1000     # 2/rho
    imprint_hold: float = 1.2
    cycles: int = 12
    inter_fission: int = 1000      # 2/rho
    amp_threshold: float = 0.2
    capacity_settle: int = 300
    capacity_bar: float = 0.8
    # Gain matching (review #3): standardized zap, pull-back slope.
    pullback_zap_sweeps: int = 8
    pullback_window: int = 50
    # Probes.
    consensus_launches: int = 4
    consensus_settle: int = 300
    repertoire_seeds: int = 8
    repertoire_distinct: float = 0.8
    # Freedom cost.
    zap_recover: int = 300
    # The single confirmatory imprint shot.
    imprint_gate_cycles: int = 8
    imprint_gate_bar: float = 0.75
    trajectory_seed_tag: str = "writable-landlord-v1"

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: LandlordConfig) -> Path:
    return capsule_root() / "results" / config.mode
