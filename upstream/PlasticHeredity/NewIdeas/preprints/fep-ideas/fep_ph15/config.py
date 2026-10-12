from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from fep_ph1.config import CANDIDATES, GardConfig
from fep_ph1.types import RegimeSpec


MASTER_SEED = "1d739295d13dc6e199c425caa5e64be3876c1596e4d940b45155f8d9a9194887"
SCREEN_BUDGETS = (60, 80, 100, 125, 150, 180, 220, 280, 360, 480)
SCALE_LADDER = (80, 72, 64, 56, 48)
MOLECULAR_DOSES = (1, 2, 4, 8)


@dataclass(frozen=True)
class ExperimentConfig:
    profile: str
    master_seed: str = MASTER_SEED
    screen_matrices: int = 24
    screen_branches: int = 2
    screen_horizon: int = 48
    development_matrices: int = 32
    development_episodes: int = 12
    development_steps: int = 24
    calibration_episodes: int = 12
    calibration_steps: int = 24
    evaluation_matrices: int = 80
    branches: int = 4
    horizon: int = 48
    policy_horizon: int = 2
    bootstrap_repetitions: int = 4_096
    workers: int = 8
    selected_scale: int | None = None
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
            self.screen_matrices,
            self.screen_branches,
            self.screen_horizon,
            self.development_matrices,
            self.development_episodes,
            self.development_steps,
            self.calibration_episodes,
            self.calibration_steps,
            self.evaluation_matrices,
            self.branches,
            self.horizon,
            self.bootstrap_repetitions,
            self.workers,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("all FEP-PH1.5 scales must be positive")
        if self.policy_horizon != 2:
            raise ValueError("FEP-PH1.5 freezes the policy horizon at two")
        if self.gard.max_growth_steps < max(SCREEN_BUDGETS):
            raise ValueError("screen kernel must reach the largest frozen budget")
        if not 0 < self.graceful_stop_seconds < self.wall_time_limit_seconds:
            raise ValueError("graceful stop must precede the hard wall time")
        if not 0 < self.registration_projection_ceiling_seconds < self.graceful_stop_seconds:
            raise ValueError("registration projection ceiling is invalid")
        if not 0.0 < self.passive_cue_accuracy < self.sampled_cue_accuracy <= 1.0:
            raise ValueError("active sampling must improve a valid cue accuracy")
        if self.gate_strength <= 0.0:
            raise ValueError("uptake gate strength must be positive")

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["candidates"] = {key: asdict(value) for key, value in CANDIDATES.items()}
        output["regimes"] = [asdict(value) for value in regime_specs()]
        output["screen_budgets"] = list(SCREEN_BUDGETS)
        output["molecular_doses"] = list(MOLECULAR_DOSES)
        output["scale_ladder"] = list(SCALE_LADDER)
        return output


def regime_specs() -> tuple[RegimeSpec, ...]:
    return tuple(
        RegimeSpec(
            severity_index=2,
            volatility=volatility,
            switch_probability=switch_probability,
            shock_probability=0.05,
            nutrient_contrast=0.80,
            shock_supply_multiplier=0.50,
            catalytic_morph=0.35,
            catalytic_shock_morph=0.70,
        )
        for volatility, switch_probability in (("slow", 0.08), ("fast", 0.25))
    )


def profile_config(profile: str) -> ExperimentConfig:
    if profile == "smoke":
        value = ExperimentConfig(
            profile="smoke",
            screen_matrices=1,
            screen_branches=1,
            screen_horizon=4,
            development_matrices=1,
            development_episodes=1,
            development_steps=4,
            calibration_episodes=1,
            calibration_steps=4,
            evaluation_matrices=1,
            branches=1,
            horizon=12,
            bootstrap_repetitions=32,
            workers=1,
            wall_time_limit_seconds=1_200,
            graceful_stop_seconds=1_140,
            registration_projection_ceiling_seconds=1_020,
        )
    elif profile == "quick":
        value = ExperimentConfig(
            profile="quick",
            screen_matrices=4,
            screen_branches=1,
            screen_horizon=16,
            development_matrices=4,
            development_episodes=4,
            development_steps=12,
            calibration_episodes=4,
            calibration_steps=12,
            evaluation_matrices=8,
            branches=2,
            horizon=24,
            bootstrap_repetitions=512,
            workers=4,
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
