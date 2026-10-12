from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from fep_ph1.config import CANDIDATES, GardConfig
from fep_ph15.config import regime_specs


MASTER_SEED = "87b722ca8b6bcf3be37058f0bcc2f7d1941a7feaf8223461bca09ca4099a9180"
MAX_WORKERS = 4
SCALE_PAIRS = (
    (48, 64),
    (48, 48),
    (40, 48),
    (32, 48),
    (32, 40),
    (24, 32),
    (24, 24),
    (20, 24),
    (20, 20),
    (16, 24),
    (16, 20),
    (16, 16),
    (12, 16),
    (12, 12),
)
RIDGE_GRID = (0.001, 0.01, 0.1, 1.0, 10.0)
EPISTEMIC_GRID = (0.25, 0.5, 1.0, 2.0, 4.0)
EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL = (0.40, 0.70)
EPISTEMIC_MIN_INFORMATION_UPLIFT = 0.10
EPISTEMIC_MIN_ENTROPY_GAP = 0.05
EPISTEMIC_MAX_SHAM_SHIFT = 1.0e-10
AUTHORITY_SCALES = (0.0, 1.0, 1.5)
MECHANISM_KEYS = (
    "c02--catalytic--uptake",
    "c03--catalytic--uptake",
)


@dataclass(frozen=True)
class ExperimentConfig:
    profile: str
    master_seed: str = MASTER_SEED
    development_matrices: int = 32
    development_episodes: int = 4
    development_steps: int = 32
    stage_a_matrices: int = 48
    stage_b_matrices: int = 64
    branches: int = 2
    horizon: int = 64
    ensemble_members: int = 8
    bootstrap_repetitions: int = 8_192
    workers: int = MAX_WORKERS
    selected_stage_a_matrices: int | None = None
    selected_stage_b_matrices: int | None = None
    selected_authority_scale: float | None = None
    selected_epistemic_coefficient: float | None = None
    legacy_oracle_depth: int = 3
    legacy_oracle_beam: int = 4
    legacy_oracle_replicas: int = 1
    goal_short_depth: int = 3
    goal_short_beam: int = 4
    goal_short_replicas: int = 1
    goal_long_depth: int = 8
    goal_long_beam: int = 4
    goal_long_replicas: int = 1
    hybrid_depth: int = 6
    hybrid_beam: int = 16
    policy_precision: float = 16.0
    risk_coefficient: float = 0.5
    action_cost_weight: float = 0.05
    clr_components: int = 12
    wall_time_limit_seconds: int = 57_600
    graceful_stop_seconds: int = 55_200
    registration_projection_ceiling_seconds: int = 50_400
    action_cost_adapt: float = 0.15
    action_cost_sample: float = 0.20
    action_cost_uptake: float = 0.15
    molecular_base_cost: float = 0.15
    molecular_increment_cost: float = 0.025
    sampling_exposure_multiplier: float = 0.95
    stage_a_passive_cue_accuracy: float = 0.55
    stage_a_sample_accuracy: float = 0.95
    passive_cue_accuracy: float = 0.50
    informative_sample_accuracy: float = 0.98
    sham_sample_accuracy: float = 0.50
    gate_strength: float = 0.35
    gard: GardConfig = GardConfig(max_growth_steps=600)

    def validate(self) -> None:
        if self.profile not in {"smoke", "quick", "full"}:
            raise ValueError(f"unknown profile {self.profile!r}")
        positive = (
            self.development_matrices,
            self.development_episodes,
            self.development_steps,
            self.stage_a_matrices,
            self.stage_b_matrices,
            self.branches,
            self.horizon,
            self.ensemble_members,
            self.bootstrap_repetitions,
            self.workers,
            self.legacy_oracle_depth,
            self.legacy_oracle_beam,
            self.legacy_oracle_replicas,
            self.goal_short_depth,
            self.goal_short_beam,
            self.goal_short_replicas,
            self.goal_long_depth,
            self.goal_long_beam,
            self.goal_long_replicas,
            self.hybrid_depth,
            self.hybrid_beam,
            self.clr_components,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("all FEP-PH1.7 scales and search sizes must be positive")
        if self.workers > MAX_WORKERS:
            raise ValueError(f"FEP-PH1.7 is capped at {MAX_WORKERS} workers")
        if self.development_matrices < self.ensemble_members:
            raise ValueError("development matrices must cover every ensemble fold")
        if self.goal_short_depth > self.goal_long_depth:
            raise ValueError("long goal planner must be at least as deep as short planner")
        if not 0 < self.graceful_stop_seconds < self.wall_time_limit_seconds:
            raise ValueError("graceful stop must precede the hard wall")
        if not 0 < self.registration_projection_ceiling_seconds < self.graceful_stop_seconds:
            raise ValueError("registration projection ceiling is invalid")
        if not 0.0 < self.stage_a_passive_cue_accuracy < self.stage_a_sample_accuracy <= 1.0:
            raise ValueError("Stage A cue accuracies are invalid")
        if not 0.0 <= self.passive_cue_accuracy <= 1.0:
            raise ValueError("passive cue accuracy is invalid")
        if not self.passive_cue_accuracy < self.informative_sample_accuracy <= 1.0:
            raise ValueError("informative sampling must improve cue accuracy")
        if self.sham_sample_accuracy != self.passive_cue_accuracy:
            raise ValueError("sham sampling must carry no incremental information")
        if self.policy_precision <= 0.0 or self.risk_coefficient < 0.0:
            raise ValueError("planner coefficients are invalid")
        if self.action_cost_weight < 0.0:
            raise ValueError("action cost weight must be nonnegative")
        if self.clr_components >= self.gard.n_types:
            raise ValueError("CLR projection must be lower dimensional than composition")
        if self.selected_authority_scale is not None and self.selected_authority_scale not in (1.0, 1.5):
            raise ValueError("Stage B authority must be current or strengthened")
        epistemic_lower, epistemic_upper = EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL
        if not 0.0 < epistemic_lower < epistemic_upper < 1.0:
            raise ValueError("epistemic sampling interval is invalid")
        if EPISTEMIC_MIN_INFORMATION_UPLIFT <= 0.0:
            raise ValueError("epistemic information uplift must be positive")
        if EPISTEMIC_MIN_ENTROPY_GAP <= 0.0:
            raise ValueError("epistemic entropy gap must be positive")
        if EPISTEMIC_MAX_SHAM_SHIFT < 0.0:
            raise ValueError("epistemic sham tolerance must be nonnegative")
        if (
            self.selected_epistemic_coefficient is not None
            and self.selected_epistemic_coefficient not in EPISTEMIC_GRID
        ):
            raise ValueError("selected epistemic coefficient is outside the frozen grid")

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["candidates"] = {key: asdict(value) for key, value in CANDIDATES.items()}
        output["regimes"] = [asdict(value) for value in regime_specs()]
        output["mechanism_keys"] = list(MECHANISM_KEYS)
        output["ridge_grid"] = list(RIDGE_GRID)
        output["epistemic_grid"] = list(EPISTEMIC_GRID)
        output["epistemic_sample_probability_interval"] = list(
            EPISTEMIC_SAMPLE_PROBABILITY_INTERVAL
        )
        output["epistemic_min_information_uplift"] = EPISTEMIC_MIN_INFORMATION_UPLIFT
        output["epistemic_min_entropy_gap"] = EPISTEMIC_MIN_ENTROPY_GAP
        output["epistemic_max_sham_shift"] = EPISTEMIC_MAX_SHAM_SHIFT
        output["authority_scales"] = list(AUTHORITY_SCALES)
        output["scale_pairs"] = [list(value) for value in SCALE_PAIRS]
        return output


def profile_config(profile: str) -> ExperimentConfig:
    if profile == "smoke":
        value = ExperimentConfig(
            profile="smoke",
            development_matrices=2,
            development_episodes=1,
            development_steps=4,
            stage_a_matrices=1,
            stage_b_matrices=1,
            branches=1,
            horizon=6,
            ensemble_members=2,
            bootstrap_repetitions=64,
            workers=1,
            legacy_oracle_depth=1,
            goal_short_depth=1,
            goal_long_depth=2,
            goal_long_beam=4,
            goal_long_replicas=1,
            hybrid_depth=2,
            hybrid_beam=4,
            clr_components=2,
            wall_time_limit_seconds=2_400,
            graceful_stop_seconds=2_300,
            registration_projection_ceiling_seconds=2_100,
        )
    elif profile == "quick":
        value = ExperimentConfig(
            profile="quick",
            development_matrices=8,
            development_episodes=2,
            development_steps=12,
            stage_a_matrices=8,
            stage_b_matrices=8,
            branches=2,
            horizon=24,
            ensemble_members=4,
            bootstrap_repetitions=512,
            workers=4,
            legacy_oracle_depth=2,
            goal_short_depth=2,
            goal_long_depth=4,
            goal_long_beam=4,
            goal_long_replicas=1,
            hybrid_depth=3,
            hybrid_beam=8,
            clr_components=6,
            wall_time_limit_seconds=10_800,
            graceful_stop_seconds=10_200,
            registration_projection_ceiling_seconds=9_000,
        )
    elif profile == "full":
        value = ExperimentConfig(profile="full")
    else:
        raise ValueError(f"unknown profile {profile!r}")
    value.validate()
    return value


def with_selected_scales(
    config: ExperimentConfig, stage_a: int, stage_b: int
) -> ExperimentConfig:
    value = replace(
        config,
        stage_a_matrices=int(stage_a),
        stage_b_matrices=int(stage_b),
        selected_stage_a_matrices=int(stage_a),
        selected_stage_b_matrices=int(stage_b),
    )
    value.validate()
    return value


def with_stage_b_choices(
    config: ExperimentConfig, authority: float, epistemic: float
) -> ExperimentConfig:
    value = replace(
        config,
        selected_authority_scale=float(authority),
        selected_epistemic_coefficient=float(epistemic),
    )
    value.validate()
    return value
