from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PHASE_GRID = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)
CANDIDATES = ("02", "03")
MECHANISMS = ("NATURAL_GARD", "HOMOGENEOUS_GENERATIVE", "FISSION_ONLY_GENERATIVE")


@dataclass(frozen=True)
class CohortScale:
    matrices: int
    reference_lineages: int
    reference_fissions: int
    reference_burnin: int
    main_generations: int
    landmarks: tuple[int, ...]
    branches: int
    horizon: int = 32

    def validate(self) -> None:
        if self.matrices < 1:
            raise ValueError("matrices must be positive")
        if self.reference_lineages < 2 or self.reference_lineages % 2:
            raise ValueError("reference_lineages must be positive, even, and >=2")
        if not 0 <= self.reference_burnin < self.reference_fissions:
            raise ValueError("reference burn-in must precede reference horizon")
        if not self.landmarks or max(self.landmarks) > self.main_generations:
            raise ValueError("landmarks must lie on the main trajectory")
        if self.branches < 2 or self.branches % 2:
            raise ValueError("branches must be positive and even")
        if self.horizon < 9:
            raise ValueError("strict-8 needs at least nine future fissions")


@dataclass(frozen=True)
class CampaignConfig:
    profile: str
    development: CohortScale
    confirmation: CohortScale
    pseudocount: float = 0.5
    pca_variance: float = 0.95
    pca_min: int = 2
    pca_max: int = 20
    mixture_k_max: int = 6
    knn_k: int = 20
    landscape_subsample_per_half: int = 800
    minimum_reference_states_full: int = 1_000
    maximum_unscorable_fraction: float = 0.05
    bootstrap_repetitions: int = 4_096
    randomization_repetitions: int = 4_096
    predictor_c_grid: tuple[float, ...] = (0.01, 0.1, 1.0)
    predictor_folds: int = 5
    phase_grid: tuple[float, ...] = PHASE_GRID
    master_seed: str = (
        "6210ad9c57e73e2094092aa742fdc14b56b1dc826225912f12d9e12e43264f83"
    )

    def validate(self) -> None:
        self.development.validate()
        self.confirmation.validate()
        if not 0 < self.pca_variance <= 1:
            raise ValueError("pca_variance must be in (0,1]")
        if not 1 <= self.pca_min <= self.pca_max:
            raise ValueError("invalid PCA bounds")
        if self.knn_k < 2:
            raise ValueError("knn_k must be >=2")
        if self.phase_grid[0] != 0.0 or self.phase_grid[-1] != 1.0:
            raise ValueError("phase grid must include 0 and 1")
        if tuple(sorted(set(self.phase_grid))) != self.phase_grid:
            raise ValueError("phase grid must be strictly increasing")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_config(profile: str) -> CampaignConfig:
    """Return a frozen full, quick, or smoke scale.

    Smoke exercises every scientific code path but is explicitly unsuitable
    for outcome interpretation. Quick is a development aid only. Full is the
    registered scientific scale.
    """

    if profile == "full":
        cfg = CampaignConfig(
            profile="full",
            development=CohortScale(
                matrices=40,
                reference_lineages=8,
                reference_fissions=500,
                reference_burnin=100,
                main_generations=100,
                landmarks=(20, 35, 50, 65, 80),
                branches=128,
            ),
            confirmation=CohortScale(
                matrices=200,
                reference_lineages=8,
                reference_fissions=500,
                reference_burnin=100,
                main_generations=100,
                landmarks=(20, 35, 50, 65, 80),
                branches=128,
            ),
        )
    elif profile == "quick":
        cfg = CampaignConfig(
            profile="quick",
            development=CohortScale(6, 4, 80, 20, 24, (8, 16, 24), 16, 16),
            confirmation=CohortScale(8, 4, 80, 20, 24, (8, 16, 24), 16, 16),
            pca_max=8,
            mixture_k_max=4,
            knn_k=10,
            landscape_subsample_per_half=120,
            minimum_reference_states_full=40,
            bootstrap_repetitions=256,
            randomization_repetitions=256,
            phase_grid=(0.0, 0.25, 0.5, 0.75, 1.0),
        )
    elif profile == "smoke":
        cfg = CampaignConfig(
            profile="smoke",
            development=CohortScale(2, 2, 20, 4, 10, (5, 10), 4, 12),
            confirmation=CohortScale(2, 2, 20, 4, 10, (5, 10), 4, 12),
            pca_max=4,
            mixture_k_max=2,
            knn_k=3,
            landscape_subsample_per_half=32,
            minimum_reference_states_full=8,
            maximum_unscorable_fraction=1.0,
            bootstrap_repetitions=32,
            randomization_repetitions=32,
            predictor_c_grid=(0.1,),
            predictor_folds=2,
            phase_grid=(0.0, 0.5, 1.0),
        )
    else:
        raise ValueError(f"unknown profile: {profile}")
    cfg.validate()
    return cfg

