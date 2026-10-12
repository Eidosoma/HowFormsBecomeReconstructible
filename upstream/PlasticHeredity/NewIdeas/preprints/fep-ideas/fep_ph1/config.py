from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .types import RegimeSpec


MASTER_SEED = "8a98097483c88f27a57b3bd422614178418a504f54712aa22b80a6001da73f0e"


@dataclass(frozen=True)
class GardConfig:
    n_types: int = 100
    n_min: int = 40
    n_max: int = 80
    beta_log_mean: float = -4.0
    beta_log_sd: float = 4.0
    k_join: float = 1e-2
    k_leave: float = 1e-4
    max_growth_steps: int = 1_000
    inheritance_threshold: float = 0.9


@dataclass(frozen=True)
class SimulationContract:
    name: str
    poisson_exposure: float
    overshoot_rule: str
    fission_rule: str
    daughter_rule: str


CANDIDATES: dict[str, SimulationContract] = {
    "02": SimulationContract("02", 0.10, "trim_whole_assembly", "fixed_size", "first"),
    "03": SimulationContract("03", 0.125, "admit_joiners_to_capacity", "binomial", "second"),
}


@dataclass(frozen=True)
class ExperimentConfig:
    profile: str
    master_seed: str = MASTER_SEED
    development_matrices: int = 32
    evaluation_matrices: int = 128
    branches: int = 4
    horizon: int = 60
    development_episodes: int = 12
    calibration_episodes: int = 12
    calibration_steps: int = 24
    policy_horizon: int = 2
    bootstrap_repetitions: int = 4_096
    workers: int = 8
    selected_scale: int | None = None
    wall_time_limit_seconds: int = 28_800
    graceful_stop_seconds: int = 27_900
    registration_projection_ceiling_seconds: int = 23_400
    action_cost_adapt: float = 0.15
    action_cost_sample: float = 0.20
    sampling_exposure_multiplier: float = 0.95
    passive_cue_accuracy: float = 0.55
    sampled_cue_accuracy: float = 0.95
    gate_strength: float = 0.80
    gard: GardConfig = GardConfig()

    def validate(self) -> None:
        if self.profile not in {"smoke", "quick", "full"}:
            raise ValueError(f"unknown profile {self.profile!r}")
        positive = (
            self.development_matrices,
            self.evaluation_matrices,
            self.branches,
            self.horizon,
            self.development_episodes,
            self.calibration_episodes,
            self.calibration_steps,
            self.bootstrap_repetitions,
            self.workers,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("experiment scales must be positive")
        if self.policy_horizon != 2:
            raise ValueError("Experiment 1 freezes the policy horizon at two")
        if self.graceful_stop_seconds >= self.wall_time_limit_seconds:
            raise ValueError("graceful stop must precede hard stop")
        if not 0.0 < self.registration_projection_ceiling_seconds < self.graceful_stop_seconds:
            raise ValueError("registration projection ceiling is invalid")
        for value in (self.sampling_exposure_multiplier, self.passive_cue_accuracy, self.sampled_cue_accuracy):
            if not 0.0 < value <= 1.0:
                raise ValueError("probabilities and exposure multipliers must lie in (0, 1]")
        if self.sampled_cue_accuracy <= self.passive_cue_accuracy:
            raise ValueError("active sampling must improve cue accuracy")

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["candidates"] = {key: asdict(value) for key, value in CANDIDATES.items()}
        output["regimes"] = [asdict(value) for value in regime_specs()]
        return output


def regime_specs() -> tuple[RegimeSpec, ...]:
    severity = (
        (0.35, 0.75, 0.15),
        (0.80, 0.50, 0.35),
        (1.40, 0.25, 0.60),
    )
    values: list[RegimeSpec] = []
    for index, (contrast, supply, morph) in enumerate(severity, start=1):
        for volatility, switch in (("slow", 0.08), ("fast", 0.25)):
            values.append(
                RegimeSpec(
                    severity_index=index,
                    volatility=volatility,
                    switch_probability=switch,
                    shock_probability=0.05,
                    nutrient_contrast=contrast,
                    shock_supply_multiplier=supply,
                    catalytic_morph=morph,
                    catalytic_shock_morph=min(1.0, morph + 0.35),
                )
            )
    return tuple(values)


def profile_config(profile: str) -> ExperimentConfig:
    if profile == "smoke":
        value = ExperimentConfig(
            profile="smoke",
            development_matrices=1,
            evaluation_matrices=1,
            branches=1,
            horizon=6,
            development_episodes=1,
            calibration_episodes=1,
            calibration_steps=4,
            bootstrap_repetitions=32,
            workers=1,
            wall_time_limit_seconds=900,
            graceful_stop_seconds=840,
            registration_projection_ceiling_seconds=780,
        )
    elif profile == "quick":
        value = ExperimentConfig(
            profile="quick",
            development_matrices=8,
            evaluation_matrices=16,
            branches=2,
            horizon=24,
            development_episodes=4,
            calibration_episodes=4,
            calibration_steps=12,
            bootstrap_repetitions=512,
            workers=4,
            wall_time_limit_seconds=7_200,
            graceful_stop_seconds=6_900,
            registration_projection_ceiling_seconds=5_400,
        )
    elif profile == "full":
        value = ExperimentConfig(profile="full")
    else:
        raise ValueError(f"unknown profile {profile!r}")
    value.validate()
    return value


def with_selected_scale(config: ExperimentConfig, scale: int) -> ExperimentConfig:
    value = replace(config, evaluation_matrices=scale, selected_scale=scale)
    value.validate()
    return value

