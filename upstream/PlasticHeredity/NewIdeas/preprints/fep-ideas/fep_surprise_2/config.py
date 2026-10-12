from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PHASE_GRID = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)
CANDIDATES = ("02", "03")
PERMUTATION_COUNTS = (10, 30, 60, 100)
MORPH_LEVELS = (0.25, 0.50, 0.75)
ARMS = (
    "NOOP",
    "PERM_BETA_10",
    "PERM_BETA_30",
    "PERM_BETA_60",
    "PERM_BETA_100",
    "MORPH_BETA_025",
    "MORPH_BETA_050",
    "MORPH_BETA_075",
    "COMPOSITION_ONLY_100",
    "ISOMORPHIC_BOTH_100",
)
BETA_PANEL_ARMS = ARMS[:8]
BETA_CHANGE_ARMS = ARMS[1:8]
PRIMARY_OBSERVERS = ("invariant_knn", "shelf")


@dataclass(frozen=True)
class Stage2Scale:
    matrices: int
    reference_lineages: int
    reference_fissions: int
    reference_burnin: int
    minimum_reference_states: int
    training_subsample: int
    main_generations: int
    landmarks: tuple[int, ...]
    branches: int
    horizon: int

    def validate(self) -> None:
        if self.matrices < 1:
            raise ValueError("matrix count must be positive")
        if self.reference_lineages < 4 or self.reference_lineages % 2:
            raise ValueError("reference lineages must be even and at least four")
        if not 0 <= self.reference_burnin < self.reference_fissions:
            raise ValueError("reference burn-in must precede the reference horizon")
        available = self.reference_lineages * (
            self.reference_fissions - self.reference_burnin
        )
        if not 1 <= self.minimum_reference_states <= available:
            raise ValueError("invalid minimum reference-state count")
        if self.training_subsample < 20:
            raise ValueError("training subsample is too small")
        if not self.landmarks or max(self.landmarks) > self.main_generations:
            raise ValueError("landmarks must lie on the native main trajectory")
        if self.branches < 2 or self.branches % 2:
            raise ValueError("branches must be positive and even")
        if self.horizon < 9:
            raise ValueError("strict-8 requires at least nine fissions")


@dataclass(frozen=True)
class Campaign2Config:
    profile: str
    development: Stage2Scale
    confirmation: Stage2Scale
    reference_mass: float = 80.0
    pseudocount: float = 0.5
    pca_variance: float = 0.95
    pca_min: int = 2
    pca_max: int = 20
    knn_k: int = 20
    mixture_k_max: int = 6
    bootstrap_repetitions: int = 4_096
    randomization_repetitions: int = 4_096
    predictor_c_grid: tuple[float, ...] = (0.01, 0.1, 1.0)
    predictor_folds: int = 5
    phase_grid: tuple[float, ...] = PHASE_GRID
    permutation_counts: tuple[int, ...] = PERMUTATION_COUNTS
    morph_levels: tuple[float, ...] = MORPH_LEVELS
    scale_tolerance: float = 1e-10
    relabel_tolerance: float = 1e-7
    aligned_mismatch_tolerance: float = 1e-12
    strict8_equivalence_margin: float = 0.003
    break_equivalence_margin: float = 0.01
    latency_equivalence_margin: float = 0.5
    shelf_stability_cosine: float = 0.90
    destination_min_matrices: int = 30
    destination_min_events: int = 100
    master_seed: str = (
        "0fbefe6aa90570056257837ca5b87cffb54f8622c253c6d1f8344ee277a543bd"
    )

    def validate(self) -> None:
        self.development.validate()
        self.confirmation.validate()
        if self.profile not in ("smoke", "quick", "full"):
            raise ValueError("unknown Experiment 2 profile")
        if len(self.master_seed) != 64:
            raise ValueError("master seed must be a 256-bit hexadecimal string")
        int(self.master_seed, 16)
        if self.phase_grid[0] != 0.0 or self.phase_grid[-1] != 1.0:
            raise ValueError("phase grid must include zero and one")
        if tuple(sorted(set(self.phase_grid))) != self.phase_grid:
            raise ValueError("phase grid must be strictly increasing")
        if self.permutation_counts != tuple(sorted(self.permutation_counts)):
            raise ValueError("permutation doses must be ordered")
        if any(value < 2 or value > 100 or value % 2 for value in self.permutation_counts):
            raise ValueError("permutation doses must be even counts in [2,100]")
        if self.permutation_counts[-1] != 100:
            raise ValueError("the isomorphism control requires a full permutation")
        if any(not 0.0 < value < 1.0 for value in self.morph_levels):
            raise ValueError("morph levels must lie strictly inside (0,1)")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_config(profile: str) -> Campaign2Config:
    if profile == "full":
        config = Campaign2Config(
            profile=profile,
            development=Stage2Scale(
                matrices=40,
                reference_lineages=8,
                reference_fissions=300,
                reference_burnin=100,
                minimum_reference_states=1_200,
                training_subsample=1_600,
                main_generations=100,
                landmarks=(20, 35, 50, 65, 80),
                branches=24,
                horizon=32,
            ),
            confirmation=Stage2Scale(
                matrices=160,
                reference_lineages=12,
                reference_fissions=400,
                reference_burnin=100,
                minimum_reference_states=3_000,
                training_subsample=2_400,
                main_generations=100,
                landmarks=(20, 35, 50, 65, 80),
                branches=48,
                horizon=32,
            ),
        )
    elif profile == "quick":
        config = Campaign2Config(
            profile=profile,
            development=Stage2Scale(3, 4, 32, 8, 80, 96, 16, (6, 12), 4, 12),
            confirmation=Stage2Scale(4, 4, 40, 8, 100, 120, 16, (6, 12), 6, 12),
            pca_max=8,
            knn_k=8,
            mixture_k_max=3,
            bootstrap_repetitions=128,
            randomization_repetitions=128,
            predictor_c_grid=(0.1, 1.0),
            predictor_folds=3,
            phase_grid=(0.0, 0.25, 0.5, 0.75, 1.0),
            destination_min_matrices=2,
            destination_min_events=2,
        )
    elif profile == "smoke":
        config = Campaign2Config(
            profile=profile,
            development=Stage2Scale(1, 4, 16, 4, 40, 48, 8, (4, 8), 2, 12),
            confirmation=Stage2Scale(1, 4, 16, 4, 40, 48, 8, (4, 8), 2, 12),
            pca_max=4,
            knn_k=3,
            mixture_k_max=2,
            bootstrap_repetitions=16,
            randomization_repetitions=16,
            predictor_c_grid=(0.1,),
            predictor_folds=2,
            phase_grid=(0.0, 0.5, 1.0),
            destination_min_matrices=1,
            destination_min_events=1,
        )
    else:
        raise ValueError(f"unknown profile: {profile}")
    config.validate()
    return config
