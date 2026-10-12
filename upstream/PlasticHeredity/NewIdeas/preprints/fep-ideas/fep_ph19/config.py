from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from fep_ph18.config import ExperimentConfig as BaseConfig


MASTER_SEED = "1b536e80dd6aa6bdeb45e5ea3527e0656131b24967710199e7f932645963ca8c"
MAX_WORKERS = 4
SWITCH_PROBABILITIES = (0.08, 0.15, 0.25)
DELAYED_CONTROL_PROBABILITY = 0.15
MODEL_ACTIONS = 7
SCALE_PAIRS = (
    (32, 48),
    (32, 40),
    (32, 32),
    (24, 24),
    (20, 20),
    (16, 16),
)
MECHANISM_KEYS = (
    "c02--catalytic--uptake",
    "c03--catalytic--uptake",
)


@dataclass(frozen=True)
class ExperimentConfig(BaseConfig):
    """Frozen resource and scientific contract for FEP–PH1.9."""

    master_seed: str = MASTER_SEED
    development_matrices: int = 32
    development_episodes: int = 2
    development_steps: int = 24
    stage_a_matrices: int = 32
    stage_b_matrices: int = 48
    branches: int = 2
    horizon: int = 64
    ensemble_members: int = 4
    bootstrap_repetitions: int = 8_192
    workers: int = MAX_WORKERS
    planner_depths: tuple[int, ...] = (2, 3)
    selected_planner_depth: int | None = 2
    clr_components: int = 12
    wall_time_limit_seconds: int = 28_800
    graceful_stop_seconds: int = 27_600
    registration_projection_ceiling_seconds: int = 24_300
    recurrent_hidden_width: int = 32
    recurrent_epochs: int = 160
    recurrent_learning_rate: float = 1.0e-3
    recurrent_patience: int = 24
    recurrent_action_tolerance: float = 0.05
    causal_pseudocount: float = 0.5
    epistemic_coefficient: float = 1.0
    entropy_threshold: float = 0.58
    efficiency_equivalence_margin: float = 0.03
    sham_equivalence_margin: float = 0.02
    sensing_reduction_margin: float = 0.25

    def validate(self) -> None:
        super().validate()
        if self.master_seed != MASTER_SEED:
            raise ValueError("FEP–PH1.9 master seed is frozen")
        if self.workers > MAX_WORKERS:
            raise ValueError(f"FEP–PH1.9 is capped at {MAX_WORKERS} workers")
        if self.wall_time_limit_seconds != 8 * 60 * 60 and self.profile == "full":
            raise ValueError("the full FEP–PH1.9 hard wall is eight hours")
        if self.recurrent_hidden_width <= 0 or self.recurrent_epochs <= 0:
            raise ValueError("recurrent-model scale must be positive")
        if not 0.0 < self.recurrent_learning_rate < 1.0:
            raise ValueError("recurrent learning rate is invalid")
        if not 0.0 < self.causal_pseudocount <= 1.0:
            raise ValueError("causal pseudocount is invalid")
        if self.epistemic_coefficient != 1.0:
            raise ValueError("the normalized epistemic coefficient is frozen at one")
        if self.efficiency_equivalence_margin != 0.03:
            raise ValueError("the balanced biological equivalence margin is frozen")
        if self.sensing_reduction_margin != 0.25:
            raise ValueError("the balanced sensing-reduction margin is frozen")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.update(
            {
                "switch_probabilities": list(SWITCH_PROBABILITIES),
                "delayed_control_probability": DELAYED_CONTROL_PROBABILITY,
                "scale_pairs": [list(pair) for pair in SCALE_PAIRS],
                "mechanism_keys": list(MECHANISM_KEYS),
                "model_actions": MODEL_ACTIONS,
                "scientific_class": "prospective_exploratory_component_atlas",
                "global_classifier": False,
            }
        )
        return value


def profile_config(profile: str) -> ExperimentConfig:
    if profile == "smoke":
        value = ExperimentConfig(
            profile="smoke",
            development_matrices=2,
            development_episodes=1,
            development_steps=7,
            stage_a_matrices=1,
            stage_b_matrices=1,
            branches=1,
            horizon=4,
            ensemble_members=2,
            bootstrap_repetitions=32,
            workers=1,
            planner_depths=(1, 2),
            selected_planner_depth=1,
            clr_components=2,
            recurrent_hidden_width=6,
            recurrent_epochs=4,
            recurrent_patience=2,
            wall_time_limit_seconds=2_400,
            graceful_stop_seconds=2_300,
            registration_projection_ceiling_seconds=2_100,
        )
    elif profile == "quick":
        value = ExperimentConfig(
            profile="quick",
            development_matrices=8,
            development_episodes=1,
            development_steps=14,
            stage_a_matrices=4,
            stage_b_matrices=4,
            branches=1,
            horizon=12,
            ensemble_members=2,
            bootstrap_repetitions=256,
            workers=4,
            planner_depths=(1, 2),
            selected_planner_depth=2,
            clr_components=6,
            recurrent_hidden_width=16,
            recurrent_epochs=30,
            recurrent_patience=6,
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


__all__ = (
    "DELAYED_CONTROL_PROBABILITY",
    "ExperimentConfig",
    "MAX_WORKERS",
    "MECHANISM_KEYS",
    "MODEL_ACTIONS",
    "SCALE_PAIRS",
    "SWITCH_PROBABILITIES",
    "profile_config",
    "with_selected_scales",
)

