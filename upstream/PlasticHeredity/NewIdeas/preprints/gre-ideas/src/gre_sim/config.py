"""Frozen and validated GRE study contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


PROTOCOL_FORMAT = "gre-rehoming-study-v1"
REGISTRATION_FORMAT = "gre-rehoming-registration-v1"
RAW_FORMAT = "gre-rehoming-futures-v1"
ANALYSIS_FORMAT = "gre-rehoming-analysis-v1"

PROTOCOL_FORMAT_V2 = "gre-rehoming-study-v2-prototype"
REGISTRATION_FORMAT_V2 = "gre-rehoming-registration-v2-prototype"
RAW_FORMAT_V2 = "gre-rehoming-futures-v2-prototype"
ANALYSIS_FORMAT_V2 = "gre-rehoming-analysis-v2-prototype"

DEFAULT_MASTER_SEED = (
    "bc6d0b528811332d4ef8692509f336692c981ed50a06e25ed8f66ac739b4f231"
)
STAGE_A_MASTER_SEED = (
    "2b471224f8f9cc2fcd0a56578a776720cfbcecc02204974c8f059a344db3914b"
)

ARMS = (
    "natural",
    "joint_isomorphic",
    "acute_mismatch",
    "developed_under_target",
    "independent_target",
    "single_attractor",
)

V2_ARMS = (*ARMS, "target_aligned_own_anchor")
INHERITANCE_MODES = ("self", "donor_shuffled")


def registration_format(protocol_format: str) -> str:
    if protocol_format == PROTOCOL_FORMAT:
        return REGISTRATION_FORMAT
    if protocol_format == PROTOCOL_FORMAT_V2:
        return REGISTRATION_FORMAT_V2
    raise ValueError(f"unsupported protocol format: {protocol_format}")


def raw_format(protocol_format: str) -> str:
    if protocol_format == PROTOCOL_FORMAT:
        return RAW_FORMAT
    if protocol_format == PROTOCOL_FORMAT_V2:
        return RAW_FORMAT_V2
    raise ValueError(f"unsupported protocol format: {protocol_format}")


def analysis_format(protocol_format: str) -> str:
    if protocol_format == PROTOCOL_FORMAT:
        return ANALYSIS_FORMAT
    if protocol_format == PROTOCOL_FORMAT_V2:
        return ANALYSIS_FORMAT_V2
    raise ValueError(f"unsupported protocol format: {protocol_format}")


@dataclass(frozen=True)
class BooleanSpec:
    genes: int = 6
    expression_flip_probability: float = 0.05


@dataclass(frozen=True)
class WagnerSpec:
    genes: int = 10
    gamma_variance: float = 0.10
    expression_flip_probability: float = 0.05
    max_sweeps: int = 100


@dataclass(frozen=True)
class EvolutionSpec:
    enabled: bool = True
    validation_replicates_per_noise: int = 4
    validation_population: int = 300
    validation_generations: int = 500
    population: int = 128
    generations: int = 200
    contexts: int = 2
    training_replicates: int = 4
    selection_replicates: int = 32
    heldout_replicates: int = 64
    selection_strength: float = 10.0
    target_min_distance: float = 0.40
    max_population_attempts: int = 64
    max_offspring_attempts_factor: int = 10_000


@dataclass(frozen=True)
class StudySpec:
    """All constants that define a run and its inferential boundaries."""

    mode: str = "pilot"
    protocol_format: str = PROTOCOL_FORMAT
    master_seed: str = DEFAULT_MASTER_SEED
    cohort_id: str = "pilot-v1"
    engines: tuple[str, ...] = ("boolean", "wagner")
    cohorts: tuple[str, ...] = ("sampled", "evolved")
    arms: tuple[str, ...] = ARMS

    sampled_rulebooks: int = 16
    evolved_rulebooks: int = 16
    target_pool_multiplier: int = 4
    launch_states_per_rulebook: int = 5
    minimum_point_attractors: int = 2
    minimum_basin_fraction: float = 0.05
    maximum_rulebook_proposals: int = 100_000

    futures_per_cell: int = 64
    horizon: int = 32
    carryover_values: tuple[float, ...] = (0.0, 1.0)
    stable_destination_run: int = 3
    strict_run: int = 8
    old_distinct_distance: float = 0.20
    dirichlet_alpha: float = 0.50

    bootstrap_repetitions: int = 4_096
    pilot_interval: float = 0.80
    advancement_log_loss_gain: float = 0.02
    distance_temperatures: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 4.0)

    boolean: BooleanSpec = field(default_factory=BooleanSpec)
    wagner: WagnerSpec = field(default_factory=WagnerSpec)
    evolution: EvolutionSpec = field(default_factory=EvolutionSpec)
    inheritance_modes: tuple[str, ...] = ("self",)

    @classmethod
    def pilot(cls) -> "StudySpec":
        return cls()

    @classmethod
    def quick(cls) -> "StudySpec":
        """Tiny, explicitly non-scientific end-to-end contract."""

        return cls(
            mode="quick",
            cohort_id="quick-v1",
            sampled_rulebooks=1,
            evolved_rulebooks=1,
            target_pool_multiplier=2,
            launch_states_per_rulebook=2,
            minimum_point_attractors=1,
            minimum_basin_fraction=0.0,
            maximum_rulebook_proposals=2_000,
            futures_per_cell=4,
            horizon=4,
            stable_destination_run=2,
            strict_run=2,
            bootstrap_repetitions=32,
            evolution=EvolutionSpec(
                validation_replicates_per_noise=1,
                validation_population=8,
                validation_generations=2,
                population=8,
                generations=2,
                training_replicates=1,
                selection_replicates=2,
                heldout_replicates=2,
                selection_strength=2.0,
                max_population_attempts=2,
                max_offspring_attempts_factor=256,
            ),
        )

    @classmethod
    def quick_v2(cls) -> "StudySpec":
        """Tiny v2 control-and-shrinkage prototype with no gate eligibility."""

        quick = cls.quick()
        return cls.from_dict(
            {
                **quick.to_dict(),
                "mode": "quick-v2",
                "protocol_format": PROTOCOL_FORMAT_V2,
                "cohort_id": "quick-v2",
                "arms": V2_ARMS,
                "inheritance_modes": INHERITANCE_MODES,
            }
        )

    @classmethod
    def stage_a_v2(cls) -> "StudySpec":
        """Frozen sampled-only v2 design-validation cohort."""

        pilot = cls.pilot()
        return cls.from_dict(
            {
                **pilot.to_dict(),
                "mode": "stage-a",
                "protocol_format": PROTOCOL_FORMAT_V2,
                "cohort_id": "stage-a-v2",
                "master_seed": STAGE_A_MASTER_SEED,
                "cohorts": ("sampled",),
                "arms": V2_ARMS,
                "sampled_rulebooks": 32,
                "evolved_rulebooks": 0,
                "pilot_interval": 0.95,
                "evolution": {
                    **asdict(pilot.evolution),
                    "enabled": False,
                },
                "inheritance_modes": INHERITANCE_MODES,
            }
        )

    @property
    def is_v2(self) -> bool:
        return self.protocol_format == PROTOCOL_FORMAT_V2

    def validate(self) -> None:
        if self.protocol_format not in {PROTOCOL_FORMAT, PROTOCOL_FORMAT_V2}:
            raise ValueError(f"unsupported protocol format: {self.protocol_format}")
        if not self.master_seed or len(self.master_seed) < 32:
            raise ValueError("master_seed must contain at least 128 bits")
        if not set(self.engines).issubset({"boolean", "wagner"}):
            raise ValueError(f"unknown engines: {self.engines}")
        if not set(self.cohorts).issubset({"sampled", "evolved"}):
            raise ValueError(f"unknown cohorts: {self.cohorts}")
        supported_arms = V2_ARMS if self.is_v2 else ARMS
        if not self.arms or not set(self.arms).issubset(set(supported_arms)):
            raise ValueError(f"unknown arms: {self.arms}")
        if not self.inheritance_modes or not set(self.inheritance_modes).issubset(
            set(INHERITANCE_MODES)
        ):
            raise ValueError(f"unknown inheritance modes: {self.inheritance_modes}")
        if not self.is_v2 and self.inheritance_modes != ("self",):
            raise ValueError("v1 supports only self inheritance")
        if self.futures_per_cell < 2 or self.futures_per_cell % 2:
            raise ValueError("futures_per_cell must be a positive even number")
        if self.horizon < self.stable_destination_run:
            raise ValueError("horizon is shorter than stable_destination_run")
        if self.horizon < self.strict_run:
            raise ValueError("horizon is shorter than strict_run")
        if any(value < 0 or value > 1 for value in self.carryover_values):
            raise ValueError("carryover values must lie in [0, 1]")
        if not 0 <= self.old_distinct_distance <= 1:
            raise ValueError("old_distinct_distance must lie in [0, 1]")
        if self.boolean.genes < 2 or self.wagner.genes < 2:
            raise ValueError("each engine needs at least two genes")
        if self.boolean.genes > 16 or self.wagner.genes > 16:
            raise ValueError("packed-state implementation supports at most 16 genes")
        if self.target_pool_multiplier < 1:
            raise ValueError("target_pool_multiplier must be positive")
        if self.bootstrap_repetitions < 1:
            raise ValueError("bootstrap_repetitions must be positive")
        if "donor_shuffled" in self.inheritance_modes and self.futures_per_cell < 4:
            raise ValueError(
                "donor-shuffled inheritance requires at least two futures per half"
            )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        # V1 registrations predate inheritance modes. Omitting the v2-only field
        # preserves their canonical JSON and protocol digests byte-for-byte.
        if not self.is_v2:
            value.pop("inheritance_modes")
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StudySpec":
        fields = dict(value)
        for name in (
            "engines",
            "cohorts",
            "arms",
            "carryover_values",
            "distance_temperatures",
            "inheritance_modes",
        ):
            if name in fields:
                fields[name] = tuple(fields[name])
        if "boolean" in fields and not isinstance(fields["boolean"], BooleanSpec):
            fields["boolean"] = BooleanSpec(**fields["boolean"])
        if "wagner" in fields and not isinstance(fields["wagner"], WagnerSpec):
            fields["wagner"] = WagnerSpec(**fields["wagner"])
        if "evolution" in fields and not isinstance(fields["evolution"], EvolutionSpec):
            fields["evolution"] = EvolutionSpec(**fields["evolution"])
        spec = cls(**fields)
        spec.validate()
        return spec
