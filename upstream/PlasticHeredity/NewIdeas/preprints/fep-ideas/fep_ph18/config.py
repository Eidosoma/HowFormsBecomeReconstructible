from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from fep_ph1.config import CANDIDATES, GardConfig
from fep_ph1.types import RegimeSpec


MASTER_SEED = "b388120edc6ebfddb15bb22b650e7eba36c40640c816f034a8d03dee2ecfacba"
MAX_WORKERS = 4
SCREEN_SWITCH_PROBABILITIES = (0.02, 0.08, 0.15, 0.25, 0.40)
CONFIRM_SWITCH_PROBABILITIES = (0.08, 0.15, 0.25)
MATCHED_SWITCH_PROBABILITY = 0.15
RFF_WIDTHS = (128, 256, 512)
RIDGE_GRID = (0.01, 0.1, 1.0, 10.0)
PLANNER_DEPTHS = (2, 3, 4)
SCALE_PAIRS = ((48, 48), (40, 40), (32, 32), (24, 24), (20, 20), (16, 16))
MECHANISM_KEYS = (
    "c02--catalytic--uptake",
    "c03--catalytic--uptake",
)
MODEL_ACTIONS = 7
EFE_COEFFICIENT = 1.0


def regime_spec(switch_probability: float) -> RegimeSpec:
    if float(switch_probability) not in SCREEN_SWITCH_PROBABILITIES:
        raise ValueError("switch probability is outside the frozen screen")
    return RegimeSpec(
        severity_index=2,
        volatility=f"p{float(switch_probability):.2f}",
        switch_probability=float(switch_probability),
        shock_probability=0.05,
        nutrient_contrast=0.80,
        catalytic_morph=0.35,
        catalytic_shock_morph=0.70,
        shock_supply_multiplier=0.50,
    )


@dataclass(frozen=True)
class ExperimentConfig:
    profile: str
    master_seed: str = MASTER_SEED
    development_matrices: int = 24
    development_episodes: int = 2
    development_steps: int = 24
    stage_a_matrices: int = 48
    stage_b_matrices: int = 48
    branches: int = 2
    horizon: int = 64
    ensemble_members: int = 8
    bootstrap_repetitions: int = 8_192
    workers: int = MAX_WORKERS
    selected_stage_a_matrices: int | None = None
    selected_stage_b_matrices: int | None = None
    selected_authority_scale: float | None = None
    selected_epistemic_coefficient: float = EFE_COEFFICIENT
    selected_rff_width: int | None = None
    selected_planner_depth: int | None = None
    rff_widths: tuple[int, ...] = RFF_WIDTHS
    planner_depths: tuple[int, ...] = PLANNER_DEPTHS
    contingent_beam: int = 32
    policy_precision: float = 12.0
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
    stage_a_passive_cue_accuracy: float = 0.50
    stage_a_sample_accuracy: float = 0.98
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
            self.contingent_beam,
            self.clr_components,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("all FEP-PH1.8 scales must be positive")
        if self.workers > MAX_WORKERS:
            raise ValueError(f"FEP-PH1.8 is capped at {MAX_WORKERS} workers")
        if self.development_matrices < self.ensemble_members:
            raise ValueError("development matrices must cover every ensemble fold")
        if not 0 < self.graceful_stop_seconds < self.wall_time_limit_seconds:
            raise ValueError("graceful stop must precede the hard wall")
        if not 0 < self.registration_projection_ceiling_seconds < self.graceful_stop_seconds:
            raise ValueError("registration projection ceiling is invalid")
        if tuple(sorted(self.rff_widths)) != self.rff_widths or any(value <= 0 for value in self.rff_widths):
            raise ValueError("RFF widths must be positive and increasing")
        if tuple(sorted(self.planner_depths)) != self.planner_depths or any(value <= 0 for value in self.planner_depths):
            raise ValueError("planner depths must be positive and increasing")
        if self.selected_rff_width is not None and self.selected_rff_width not in self.rff_widths:
            raise ValueError("selected RFF width is outside the frozen grid")
        if self.selected_planner_depth is not None and self.selected_planner_depth not in self.planner_depths:
            raise ValueError("selected planner depth is outside the frozen grid")
        if self.selected_authority_scale is not None and self.selected_authority_scale != 1.0:
            raise ValueError("FEP-PH1.8 freezes normal action authority")
        if self.selected_epistemic_coefficient != EFE_COEFFICIENT:
            raise ValueError("FEP-PH1.8 freezes the normalized EFE coefficient at one")
        if not 0.0 < self.passive_cue_accuracy < self.informative_sample_accuracy <= 1.0:
            raise ValueError("informative sensing must improve the passive cue")
        if self.sham_sample_accuracy != self.passive_cue_accuracy:
            raise ValueError("sham sensing must add no information")
        if self.policy_precision <= 0.0 or self.risk_coefficient < 0.0:
            raise ValueError("planner coefficients are invalid")
        if self.clr_components >= self.gard.n_types:
            raise ValueError("CLR projection must be lower dimensional than composition")

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["candidates"] = {key: asdict(value) for key, value in CANDIDATES.items()}
        output["screen_switch_probabilities"] = list(SCREEN_SWITCH_PROBABILITIES)
        output["confirm_switch_probabilities"] = list(CONFIRM_SWITCH_PROBABILITIES)
        output["matched_switch_probability"] = MATCHED_SWITCH_PROBABILITY
        output["ridge_grid"] = list(RIDGE_GRID)
        output["scale_pairs"] = [list(value) for value in SCALE_PAIRS]
        output["mechanism_keys"] = list(MECHANISM_KEYS)
        output["model_actions"] = MODEL_ACTIONS
        output["regimes"] = [asdict(regime_spec(value)) for value in SCREEN_SWITCH_PROBABILITIES]
        return output


def profile_config(profile: str) -> ExperimentConfig:
    if profile == "smoke":
        value = ExperimentConfig(
            profile="smoke", development_matrices=2, development_episodes=1,
            development_steps=7, stage_a_matrices=1, stage_b_matrices=1,
            branches=1, horizon=4, ensemble_members=2, bootstrap_repetitions=32,
            workers=1, rff_widths=(8, 16), planner_depths=(1, 2),
            contingent_beam=8, clr_components=2, wall_time_limit_seconds=2_400,
            graceful_stop_seconds=2_300, registration_projection_ceiling_seconds=2_100,
        )
    elif profile == "quick":
        value = ExperimentConfig(
            profile="quick", development_matrices=8, development_episodes=1,
            development_steps=14, stage_a_matrices=4, stage_b_matrices=4,
            branches=1, horizon=12, ensemble_members=4, bootstrap_repetitions=256,
            workers=4, rff_widths=(32, 64), planner_depths=(1, 2, 3),
            contingent_beam=16, clr_components=6, wall_time_limit_seconds=10_800,
            graceful_stop_seconds=10_200, registration_projection_ceiling_seconds=9_000,
        )
    elif profile == "full":
        value = ExperimentConfig(profile="full")
    else:
        raise ValueError(f"unknown profile {profile!r}")
    value.validate()
    return value


def with_selected_scales(
    config: ExperimentConfig, stage_a: int, stage_b: int, *, planner_depth: int | None = None
) -> ExperimentConfig:
    value = replace(
        config,
        stage_a_matrices=int(stage_a), stage_b_matrices=int(stage_b),
        selected_stage_a_matrices=int(stage_a), selected_stage_b_matrices=int(stage_b),
        selected_planner_depth=(int(planner_depth) if planner_depth is not None else config.selected_planner_depth),
    )
    value.validate()
    return value


def with_stage_b_choices(
    config: ExperimentConfig, authority: float = 1.0, epistemic: float = EFE_COEFFICIENT
) -> ExperimentConfig:
    value = replace(
        config, selected_authority_scale=float(authority),
        selected_epistemic_coefficient=float(epistemic),
    )
    value.validate()
    return value
