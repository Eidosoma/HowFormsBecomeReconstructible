"""Frozen configuration for E27."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class RewriteConfig:
    mode: str = "full"
    n_tissues: int = 48
    off_band_tissues: int = 16
    futures: int = 128
    horizon: int = 32
    # Protocol (frozen): zap = clamp the posterior quarter depolarized for
    # 8 sweeps during generation 3; lesion = instant reset of a random
    # quarter to resting at the start of generation 14.
    zap_generation: int = 3
    zap_sweeps: int = 8
    lesion_generation: int = 14
    # Rewrite detector: 8 coherent generations (pairwise > 0.9), all
    # distinct (<= 0.85) from the pre-zap wild census (mean of gens 1-2).
    wild_window: tuple = (1, 2)
    run_length: int = 8
    coherence: float = 0.9
    distinct: float = 0.85
    inherit: float = 0.9
    # Cohorts: the E26 band point and the off-band coupling controls.
    coupling_band: float = 1.0
    coupling_under: float = 0.25
    coupling_over: float = 4.0
    tissue_param_tag: str = "voltage-tissue-params-v1"
    trajectory_seed_tag: str = "rewrite-traj-v1"

    @classmethod
    def tiny(cls) -> "RewriteConfig":
        return cls(
            mode="tiny", n_tissues=3, off_band_tissues=2, futures=8,
            horizon=12, lesion_generation=9, run_length=3,
        )

    def as_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def results_root(config: RewriteConfig) -> Path:
    return capsule_root() / "results" / config.mode
