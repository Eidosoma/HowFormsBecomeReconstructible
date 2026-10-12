from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from fep_ph1.config import CANDIDATES, GardConfig
from fep_ph15.config import regime_specs


MASTER_SEED = "ad1887bd7c4adff22168b4d67c259172cd40a6fc5d9c9ebb8bfe28038eae9fc1"
SCALE_LADDER = (64, 56, 48, 40, 32, 24)
RIDGE_GRID = (0.001, 0.01, 0.1, 1.0, 10.0)
MECHANISM_KEYS = (
    "c02--catalytic--molecular",
    "c02--catalytic--uptake",
    "c02--nutrient--uptake",
    "c03--catalytic--molecular",
    "c03--catalytic--uptake",
    "c03--nutrient--uptake",
)


@dataclass(frozen=True)
class ExperimentConfig:
    profile: str
    master_seed: str = MASTER_SEED
    development_matrices: int = 24
    development_episodes: int = 4
    development_steps: int = 24
    calibration_episodes: int = 4
    calibration_steps: int = 16
    evaluation_matrices: int = 64
    branches: int = 2
    horizon: int = 48
    policy_horizon: int = 2
    ensemble_members: int = 8
    bootstrap_repetitions: int = 4_096
    workers: int = 12
    selected_scale: int | None = None
    oracle_depth: int = 3
    oracle_beam: int = 4
    oracle_replicas: int = 1
    mpc_depth: int = 4
    mpc_beam: int = 8
    policy_precision: float = 16.0
    risk_coefficient: float = 0.5
    epistemic_coefficient: float = 1.0
    calibration_shrinkage: float = 8.0
    wall_time_limit_seconds: int = 14_400
    graceful_stop_seconds: int = 13_800
    registration_projection_ceiling_seconds: int = 11_700
    action_cost_adapt: float = 0.15
    action_cost_sample: float = 0.20
    action_cost_uptake: float = 0.15
    molecular_base_cost: float = 0.15
    molecular_increment_cost: float = 0.025
    sampling_exposure_multiplier: float = 0.95
    passive_cue_accuracy: float = 0.55
    sampled_cue_accuracy: float = 0.95
    gate_strength: float = 0.35
    gard: GardConfig = GardConfig(max_growth_steps=600)

    def validate(self) -> None:
        if self.profile not in {"smoke", "quick", "full"}:
            raise ValueError(f"unknown profile {self.profile!r}")
        positive = (
            self.development_matrices,
            self.development_episodes,
            self.development_steps,
            self.calibration_episodes,
            self.calibration_steps,
            self.evaluation_matrices,
            self.branches,
            self.horizon,
            self.ensemble_members,
            self.bootstrap_repetitions,
            self.workers,
            self.oracle_depth,
            self.oracle_beam,
            self.oracle_replicas,
            self.mpc_depth,
            self.mpc_beam,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("all FEP-PH1.6 scales and search sizes must be positive")
        if self.development_matrices < self.ensemble_members:
            raise ValueError("development matrices must cover every ensemble fold")
        if self.policy_horizon != 2:
            raise ValueError("categorical reference policy horizon must remain two")
        if not 0 < self.graceful_stop_seconds < self.wall_time_limit_seconds:
            raise ValueError("graceful stop must precede the hard wall")
        if not 0 < self.registration_projection_ceiling_seconds < self.graceful_stop_seconds:
            raise ValueError("registration projection ceiling is invalid")
        if not 0.0 < self.passive_cue_accuracy < self.sampled_cue_accuracy <= 1.0:
            raise ValueError("sampled cues must be more accurate than passive cues")
        if self.policy_precision <= 0.0 or self.risk_coefficient < 0.0 or self.epistemic_coefficient < 0.0:
            raise ValueError("planner coefficients are invalid")
        if self.calibration_shrinkage < 0.0:
            raise ValueError("calibration shrinkage must be nonnegative")

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["candidates"] = {key: asdict(value) for key, value in CANDIDATES.items()}
        output["regimes"] = [asdict(value) for value in regime_specs()]
        output["mechanism_keys"] = list(MECHANISM_KEYS)
        output["ridge_grid"] = list(RIDGE_GRID)
        output["scale_ladder"] = list(SCALE_LADDER)
        return output


def profile_config(profile: str) -> ExperimentConfig:
    if profile == "smoke":
        value = ExperimentConfig(
            profile="smoke",
            development_matrices=2,
            development_episodes=1,
            development_steps=4,
            calibration_episodes=1,
            calibration_steps=4,
            evaluation_matrices=1,
            branches=1,
            horizon=8,
            ensemble_members=2,
            bootstrap_repetitions=64,
            workers=1,
            oracle_depth=2,
            oracle_beam=4,
            oracle_replicas=1,
            mpc_depth=2,
            mpc_beam=4,
            wall_time_limit_seconds=1_800,
            graceful_stop_seconds=1_740,
            registration_projection_ceiling_seconds=1_620,
        )
    elif profile == "quick":
        value = ExperimentConfig(
            profile="quick",
            development_matrices=8,
            development_episodes=2,
            development_steps=12,
            calibration_episodes=2,
            calibration_steps=8,
            evaluation_matrices=8,
            branches=2,
            horizon=24,
            ensemble_members=4,
            bootstrap_repetitions=512,
            workers=4,
            oracle_depth=2,
            oracle_beam=4,
            oracle_replicas=1,
            mpc_depth=3,
            mpc_beam=6,
            wall_time_limit_seconds=7_200,
            graceful_stop_seconds=6_900,
            registration_projection_ceiling_seconds=5_700,
        )
    elif profile == "full":
        value = ExperimentConfig(profile="full")
    else:
        raise ValueError(f"unknown profile {profile!r}")
    value.validate()
    return value


def with_selected_scale(config: ExperimentConfig, scale: int) -> ExperimentConfig:
    value = replace(config, evaluation_matrices=int(scale), selected_scale=int(scale))
    value.validate()
    return value
