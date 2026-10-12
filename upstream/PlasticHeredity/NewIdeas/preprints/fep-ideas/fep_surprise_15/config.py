from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PHASE_GRID = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)
CANDIDATES = ("02", "03")
NATURAL = "NATURAL_GARD"
NULL_MECHANISMS = ("HOMOGENEOUS_GENERATIVE", "FISSION_ONLY_GENERATIVE")
MECHANISMS = (NATURAL, *NULL_MECHANISMS)


@dataclass(frozen=True)
class Stage15Scale:
    natural_matrices: int
    null_matrices: int
    reference_lineages: int
    reference_fissions: int
    reference_burnin: int
    main_generations: int
    landmarks: tuple[int, ...]
    branches: int
    horizon: int = 32

    def validate(self) -> None:
        if self.natural_matrices < 1 or self.null_matrices < 0:
            raise ValueError("invalid matrix counts")
        if self.reference_lineages < 4 or self.reference_lineages % 2:
            raise ValueError("reference lineages must be even and >=4")
        if not 0 <= self.reference_burnin < self.reference_fissions:
            raise ValueError("reference burn-in must precede its horizon")
        if not self.landmarks or max(self.landmarks) > self.main_generations:
            raise ValueError("landmarks must lie on the main trajectory")
        if self.branches < 2 or self.branches % 2:
            raise ValueError("branches must be positive and even")
        if self.horizon < 9:
            raise ValueError("strict-8 requires at least nine fissions")


@dataclass(frozen=True)
class Campaign15Config:
    profile: str
    development: Stage15Scale
    confirmation: Stage15Scale
    reference_mass: float = 80.0
    pseudocount: float = 0.5
    pca_variance: float = 0.95
    pca_min: int = 2
    pca_max: int = 20
    knn_k: int = 20
    mixture_k_max: int = 6
    training_subsample_per_half: int = 1_600
    minimum_reference_states: int = 1_000
    bootstrap_repetitions: int = 4_096
    randomization_repetitions: int = 4_096
    predictor_c_grid: tuple[float, ...] = (0.01, 0.1, 1.0)
    predictor_folds: int = 5
    phase_grid: tuple[float, ...] = PHASE_GRID
    scale_tolerance: float = 1e-10
    relabel_tolerance: float = 1e-7
    reference_reliability_floor: float = 0.50
    master_seed: str = (
        "848f07c37c27cdc2457963ef6f2bfca1b7ee4022e494b44829d1479ff3293959"
    )

    def validate(self) -> None:
        self.development.validate()
        self.confirmation.validate()
        if len(self.master_seed) != 64:
            raise ValueError("master seed must be a 256-bit hex string")
        int(self.master_seed, 16)
        if not 0 < self.pca_variance <= 1:
            raise ValueError("pca variance target must be in (0,1]")
        if not 1 <= self.pca_min <= self.pca_max:
            raise ValueError("invalid PCA bounds")
        if self.knn_k < 2 or self.mixture_k_max < 1:
            raise ValueError("invalid observer size")
        if self.phase_grid[0] != 0.0 or self.phase_grid[-1] != 1.0:
            raise ValueError("phase grid must contain zero and one")
        if tuple(sorted(set(self.phase_grid))) != self.phase_grid:
            raise ValueError("phase grid must be strictly increasing")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_config(profile: str) -> Campaign15Config:
    if profile == "full":
        common = dict(
            reference_lineages=16,
            reference_fissions=500,
            reference_burnin=100,
            main_generations=100,
            landmarks=(20, 35, 50, 65, 80),
            branches=128,
            horizon=32,
        )
        config = Campaign15Config(
            profile=profile,
            development=Stage15Scale(40, 0, **common),
            confirmation=Stage15Scale(160, 40, **common),
        )
    elif profile == "quick":
        common = dict(
            reference_lineages=8,
            reference_fissions=100,
            reference_burnin=20,
            main_generations=30,
            landmarks=(10, 20, 30),
            branches=24,
            horizon=16,
        )
        config = Campaign15Config(
            profile=profile,
            development=Stage15Scale(8, 0, **common),
            confirmation=Stage15Scale(12, 4, **common),
            pca_max=10,
            knn_k=10,
            mixture_k_max=4,
            training_subsample_per_half=320,
            minimum_reference_states=80,
            bootstrap_repetitions=256,
            randomization_repetitions=256,
            predictor_c_grid=(0.1, 1.0),
            predictor_folds=4,
            phase_grid=(0.0, 0.25, 0.5, 0.75, 1.0),
        )
    elif profile == "smoke":
        common = dict(
            reference_lineages=4,
            reference_fissions=24,
            reference_burnin=4,
            main_generations=12,
            landmarks=(6, 12),
            branches=4,
            horizon=12,
        )
        config = Campaign15Config(
            profile=profile,
            development=Stage15Scale(2, 0, **common),
            confirmation=Stage15Scale(2, 1, **common),
            pca_max=4,
            knn_k=3,
            mixture_k_max=2,
            training_subsample_per_half=40,
            minimum_reference_states=16,
            bootstrap_repetitions=32,
            randomization_repetitions=32,
            predictor_c_grid=(0.1,),
            predictor_folds=2,
            phase_grid=(0.0, 0.5, 1.0),
        )
    else:
        raise ValueError(f"unknown profile: {profile}")
    config.validate()
    return config

