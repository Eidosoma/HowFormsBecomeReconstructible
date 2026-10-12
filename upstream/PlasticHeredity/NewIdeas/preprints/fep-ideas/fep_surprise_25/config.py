from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any


CANDIDATES = ("02", "03")
STRATA = ("stable", "transitional", "saturated")
LANDMARKS = (20, 50, 80)
SIGMA_LEVELS = (2.50, 3.25, 5.00)
ARMS = (
    "ALIGNED_NATIVE",
    "ALIGNED_SIGMA_250",
    "PERM_SIGMA_250",
    "ALIGNED_SIGMA_325",
    "PERM_SIGMA_325",
    "PERM_NATIVE",
    "ALIGNED_SIGMA_500",
    "PERM_SIGMA_500",
    "RAW_MORPH_050",
    "NORMALIZED_MORPH_050",
    "COMPOSITION_ONLY_100",
    "ISOMORPHIC_BOTH_100",
)
ACTUAL_ATLASES = (
    "native",
    "sigma_250",
    "sigma_325",
    "sigma_500",
    "raw_morph_050",
    "normalized_morph_050",
)


@dataclass(frozen=True)
class Screen25Scale:
    matrices: int
    main_generations: int
    landmarks: tuple[int, ...]
    branches: int
    horizon: int

    def validate(self) -> None:
        if self.matrices < 3:
            raise ValueError("screen requires at least three matrices")
        if not self.landmarks or max(self.landmarks) > self.main_generations:
            raise ValueError("screen landmarks exceed the main trajectory")
        if self.branches < 2 or self.horizon < 9:
            raise ValueError("screen branches/horizon cannot resolve strict-8")


@dataclass(frozen=True)
class Confirmation25Scale:
    selected_per_stratum: int
    reference_lineages: int
    reference_fissions: int
    reference_burnin: int
    minimum_reference_states: int
    training_subsample: int
    landmarks: tuple[int, ...]
    pilot_branches: int
    pilot_horizon: int
    branches: int
    horizon: int
    durability_events: int
    durability_horizon: int
    damage_perturbations: int
    damage_horizon: int

    def validate(self) -> None:
        if self.selected_per_stratum < 1:
            raise ValueError("selected matrix quota must be positive")
        if self.reference_lineages < 4 or self.reference_lineages % 2:
            raise ValueError("reference lineages must be even and at least four")
        if not 0 <= self.reference_burnin < self.reference_fissions:
            raise ValueError("reference burn-in must precede its horizon")
        available = self.reference_lineages * (
            self.reference_fissions - self.reference_burnin
        )
        if not 1 <= self.minimum_reference_states <= available:
            raise ValueError("invalid minimum reference pool")
        if self.training_subsample < 20:
            raise ValueError("observer training subsample is too small")
        if self.pilot_branches < 2 or self.pilot_horizon < 2:
            raise ValueError("pilot scale is invalid")
        if self.branches < 2 or self.branches % 2 or self.horizon < 9:
            raise ValueError("confirmation requires even branches and F9+")
        if self.durability_events < 1 or self.durability_horizon < 8:
            raise ValueError("durability continuation is invalid")
        if self.damage_perturbations < 1 or self.damage_horizon < 1:
            raise ValueError("damage-spread design is invalid")


@dataclass(frozen=True)
class Campaign25Config:
    profile: str
    screen: Screen25Scale
    confirmation: Confirmation25Scale
    reference_mass: float = 80.0
    pseudocount: float = 0.5
    pca_variance: float = 0.95
    pca_min: int = 2
    pca_max: int = 20
    knn_k: int = 20
    mixture_k_max: int = 6
    phase_grid: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
    shelf_stability_cosine: float = 0.90
    shelf_max_occupancy: float = 0.90
    relabel_tolerance: float = 1e-7
    aligned_mismatch_tolerance: float = 1e-12
    permutation_counts: tuple[int, ...] = (10, 30, 60, 100)
    stable_max_break: float = 0.10
    transitional_min_break: float = 0.30
    transitional_max_break: float = 0.70
    saturated_min_break: float = 0.90
    bootstrap_repetitions: int = 4_096
    randomization_repetitions: int = 4_096
    crossfit_folds: int = 4
    predictor_c: float = 0.1
    destination_min_matrices: int = 8
    destination_min_events: int = 30
    generation_workers: int = 8
    replay_workers: int = 4
    scientific_budget_seconds: int = 43_200
    graceful_stop_seconds: int = 42_300
    conservative_multiplier: float = 1.35
    large_selected_per_stratum: int = 16
    compact_selected_per_stratum: int = 12
    large_projection_ceiling_seconds: int = 34_200
    master_seed: str = (
        "69d49adccb94bf8b1be2584720eaeda63f8556f257f4fd37e3490dc31af66715"
    )

    def validate(self) -> None:
        self.screen.validate()
        self.confirmation.validate()
        if self.profile not in ("smoke", "quick", "full"):
            raise ValueError("unknown Experiment 2.5 profile")
        if len(self.master_seed) != 64:
            raise ValueError("master seed must be 256-bit hexadecimal")
        int(self.master_seed, 16)
        if not 0 <= self.stable_max_break < self.transitional_min_break:
            raise ValueError("stable and transitional strata overlap")
        if not self.transitional_min_break < self.transitional_max_break:
            raise ValueError("transitional bounds are reversed")
        if not self.transitional_max_break < self.saturated_min_break <= 1:
            raise ValueError("transitional and saturated strata overlap")
        if not 0 < self.shelf_max_occupancy < 1:
            raise ValueError("shelf occupancy ceiling must lie inside (0,1)")
        if self.graceful_stop_seconds >= self.scientific_budget_seconds:
            raise ValueError("graceful stop must precede the hard wall-time cap")
        if self.profile == "full" and self.screen.landmarks != LANDMARKS:
            raise ValueError("full screen must use the registered landmarks")

    def resolved(self, selected_per_stratum: int) -> "Campaign25Config":
        output = replace(
            self,
            confirmation=replace(
                self.confirmation, selected_per_stratum=int(selected_per_stratum)
            ),
        )
        output.validate()
        return output

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_config(profile: str) -> Campaign25Config:
    if profile == "full":
        config = Campaign25Config(
            profile=profile,
            screen=Screen25Scale(384, 80, LANDMARKS, 16, 32),
            confirmation=Confirmation25Scale(
                16, 8, 250, 100, 1_000, 1_200, LANDMARKS,
                16, 8, 32, 32, 8, 16, 8, 4,
            ),
        )
    elif profile == "quick":
        config = Campaign25Config(
            profile=profile,
            screen=Screen25Scale(18, 16, (6, 10, 14), 4, 12),
            confirmation=Confirmation25Scale(
                2, 4, 32, 8, 80, 96, (6, 10, 14),
                4, 4, 4, 12, 2, 8, 2, 2,
            ),
            pca_max=6,
            knn_k=5,
            mixture_k_max=3,
            bootstrap_repetitions=128,
            randomization_repetitions=128,
            destination_min_matrices=2,
            destination_min_events=2,
        )
    elif profile == "smoke":
        config = Campaign25Config(
            profile=profile,
            screen=Screen25Scale(3, 8, (3, 5, 8), 2, 9),
            confirmation=Confirmation25Scale(
                1, 4, 16, 4, 40, 48, (3, 5, 8),
                2, 2, 2, 9, 1, 8, 1, 1,
            ),
            pca_max=4,
            knn_k=3,
            mixture_k_max=2,
            bootstrap_repetitions=16,
            randomization_repetitions=16,
            destination_min_matrices=1,
            destination_min_events=1,
        )
    else:
        raise ValueError(f"unknown profile: {profile}")
    config.validate()
    return config
