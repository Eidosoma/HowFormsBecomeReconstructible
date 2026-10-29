"""Frozen configuration for E57."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

REGIMES = ("static", "switching_k2", "switching_k4", "drift")


@dataclass(frozen=True)
class AssimilationConfig:
    mode: str = "full"
    population: int = 10
    generations: int = 16
    n_repeats: int = 6
    futures: int = 2
    tournament: int = 3
    # Gene ranges (declared; horizon uses rho_min of THIS range).
    rho_init: tuple = (0.002, 0.05)
    rho_range: tuple = (0.002, 0.05)
    cm_init: tuple = (0.1, 0.8)
    cm_range: tuple = (0.05, 1.6)
    mutation_sigma: float = 0.3
    theta_mutation: float = 0.05
    theta_norm: float = 0.3          # fixed-norm shell (review #15)
    # Fitness eval = 1000 sweeps = 2/rho_min (review #16):
    # settle 100 + instruct 200 + free 200 + 2 x (fission + regrow 250).
    eval_settle: int = 100
    eval_instruct: int = 200
    eval_free: int = 200
    eval_regrow: int = 250
    eval_cycles: int = 2
    imprint_hold: float = 1.2
    amp_threshold: float = 0.2
    n_targets: int = 3
    target_settle: int = 400
    # Post-evolution assays.
    assay_evals: int = 2
    consensus_launches: int = 4
    readopt_horizon: int = 1000      # 2/rho_min
    transport_shift: int = 8
    transport_recover: int = 300
    trajectory_seed_tag: str = "assimilation-v1"

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: AssimilationConfig) -> Path:
    return capsule_root() / "results" / config.mode
