"""Frozen configuration for the exploratory contract-bridge capsule."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from finite_gard_ruliad.config import AtlasConfig

E1_FULL_DIGEST = "d109f6ec6d6d6cbf876b718a982cc76819d0a6cad5ac41291ced4c020946f423"
E1_MINI_DIGEST = "b3d36abe499cf02185d8ff6ad569c3561d6e997d75922d32adc6c4fd83ef4d9c"
SEALED_BINOMIAL_CSV_SHA256 = (
    "8a600752a1342b957184c44b0b6eed64ccddefe99f4b467beeae3b2f4664e856"
)


@dataclass(frozen=True)
class BridgeConfig:
    """Complete configuration for one bridge campaign.

    ``mode`` selects the underlying E1 atlas: ``full`` is the scientific
    three-species universe and ``mini`` is the deterministic two-species
    fixture. Every tunable lives here; analysis code must not carry numeric
    literals for anything this class pins, in particular the single Sinkhorn
    regularization used by every translator fit.
    """

    mode: str = "full"
    # Feasibility census for the exact strict automaton.
    census_state_bound: int = 200_000
    census_seconds_budget: float = 600.0
    # Binomial strict Monte Carlo (per-orbit, resumable).
    mc_futures: int = 65_536
    mc_seed_tag: str = "eidosoma-bridge-binomial-v1"
    # Same-sampler equal-contract check against the exact equal DP.
    sampler_check_rules: int = 64
    sampler_check_futures: int = 8_192
    # Truncated-horizon forward-DP cross-check of the MC success-by-step curve.
    forward_check_orbits: int = 6
    forward_check_horizon: int = 12
    forward_check_key_budget: int = 300_000
    # Part B: dev/eval split and monotone recalibration.
    dev_split_tag: str = "bridge-dev-eval-v1"
    quantile_map_knots: int = 33
    # Part C: translator ladder.
    ladder_rules: int = 32
    outlook_pairs: int = 16
    sinkhorn_regularization: float = 1.0e-4
    gauge_factor: float = 2.0
    ladder_seed_tag: str = "bridge-ladder-v1"
    # Part D: ordinal quotients.
    ordinal_quantile_grid: tuple[int, ...] = (4, 8, 16, 32, 64, 128)
    ordinal_offsets: int = 8
    epsilon_grid: tuple[float, ...] = (1.0e-4, 1.0e-3, 1.0e-2, 5.0e-2)
    # Part E: estimator calibration.
    estimator_budgets: tuple[int, ...] = (128, 256, 512, 1024, 2048, 4096, 8192)
    estimator_replicates: int = 128
    estimator_seed_tag: str = "bridge-estimator-v1"
    gate_grid: tuple[float, ...] = (0.001, 0.005, 0.01, 0.02, 0.05)
    # Execution.
    shard_size: int = 64

    @classmethod
    def mini(cls) -> "BridgeConfig":
        return cls(
            mode="mini",
            census_seconds_budget=60.0,
            mc_futures=2_048,
            sampler_check_rules=4,
            sampler_check_futures=2_048,
            forward_check_orbits=2,
            forward_check_horizon=6,
            forward_check_key_budget=50_000,
            ladder_rules=4,
            outlook_pairs=2,
            ordinal_quantile_grid=(2, 4, 8),
            ordinal_offsets=4,
            epsilon_grid=(1.0e-3, 1.0e-2),
            estimator_budgets=(32, 64, 128),
            estimator_replicates=32,
            shard_size=8,
        )

    def validate(self) -> None:
        if self.mode not in ("full", "mini"):
            raise ValueError("mode must be 'full' or 'mini'")
        if self.mc_futures < 2 or self.mc_futures % 2:
            raise ValueError("mc_futures must be even and positive")
        if self.sinkhorn_regularization <= 0:
            raise ValueError("sinkhorn regularization must be positive")
        if self.census_state_bound < 1 or self.census_seconds_budget <= 0:
            raise ValueError("invalid census budget")
        if self.ladder_rules < 2 or self.outlook_pairs < 1:
            raise ValueError("ladder needs at least two rules and one pair")
        expected = E1_FULL_DIGEST if self.mode == "full" else E1_MINI_DIGEST
        if self.atlas().digest() != expected:
            raise RuntimeError(
                "the imported finite_gard_ruliad AtlasConfig no longer matches "
                "the digest this capsule was designed against"
            )

    def atlas(self) -> AtlasConfig:
        return AtlasConfig() if self.mode == "full" else AtlasConfig.mini()

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["e1_digest"] = E1_FULL_DIGEST if self.mode == "full" else E1_MINI_DIGEST
        out["sealed_binomial_csv_sha256"] = (
            SEALED_BINOMIAL_CSV_SHA256 if self.mode == "full" else ""
        )
        return out

    def canonical_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sibling_root(name: str) -> Path:
    return capsule_root().parent / name


def work_root(config: BridgeConfig) -> Path:
    return capsule_root() / "work" / config.mode


def results_root(config: BridgeConfig) -> Path:
    return capsule_root() / "results" / config.mode
