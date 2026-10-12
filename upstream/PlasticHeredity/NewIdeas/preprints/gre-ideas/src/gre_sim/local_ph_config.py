"""Frozen contracts for the Wagner local-memory plastic-heredity experiment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


LOCAL_PH_CAMPAIGN_FORMAT = "gre-wagner-local-ph-campaign-v1"
LOCAL_PH_REGISTRATION_FORMAT = "gre-wagner-local-ph-registration-v1"
LOCAL_PH_RAW_FORMAT = "gre-wagner-local-ph-futures-v1"
LOCAL_PH_ANALYSIS_FORMAT = "gre-wagner-local-ph-analysis-v1"
LOCAL_PH_MANIFEST_FORMAT = "gre-wagner-local-ph-manifest-v1"
LOCAL_PH_SEARCH_FORMAT = "gre-wagner-local-ph-search-v1"

TOPOLOGIES = ("all", "outgoing", "self_feedback")
INTERVENTIONS = (
    "intact",
    "random_mask",
    "founder_write_off",
    "renewal_off",
    "reader_off",
    "shuffle",
    "erase_g2",
    "reverse_g2",
    "erase_g2_rescue_g3",
    "renewal_block_g1_g4",
    "renewal_block_g9_g12",
    "erase_g6",
    "erase_g6_rescue_g7",
    "opposite_history_transplant",
    "zero",
    "perfect_latch",
)


def intervention_locus(intervention: str, genes: int) -> int | None:
    """Return the locus for a registered generation-2 single-locus lesion."""

    prefix = "ablate_locus_"
    suffix = "_g2"
    if not intervention.startswith(prefix) or not intervention.endswith(suffix):
        return None
    value = intervention[len(prefix) : -len(suffix)]
    if not value.isdigit() or not 0 <= int(value) < genes:
        raise ValueError("invalid local-carrier locus ablation")
    return int(value)


@dataclass(frozen=True)
class CopyNoiseSpec:
    """Local, imperfect transmission applied once per lineage generation."""

    name: str
    dilution: float
    dropout: float
    sigma: float

    def validate(self) -> None:
        if not self.name:
            raise ValueError("copy-noise name cannot be empty")
        if not 0.0 <= self.dilution <= 1.0:
            raise ValueError("copy dilution must lie in [0, 1]")
        if not 0.0 <= self.dropout <= 1.0:
            raise ValueError("copy dropout must lie in [0, 1]")
        if not isfinite(self.sigma) or self.sigma < 0.0:
            raise ValueError("copy sigma must be finite and nonnegative")


@dataclass(frozen=True)
class LocalCarrierGenome:
    """An evolvable local writer/reader; it contains no outcome label."""

    name: str
    write_rate: float
    decay: float
    coupling: float
    hysteresis: int
    topology: str
    k: int

    def validate(self, genes: int = 10) -> None:
        if not self.name:
            raise ValueError("local carrier name cannot be empty")
        if not 0.0 <= self.write_rate <= 1.0:
            raise ValueError("write rate must lie in [0, 1]")
        if not 0.0 <= self.decay < 1.0:
            raise ValueError("carrier decay must lie in [0, 1)")
        if not 0.0 <= self.coupling <= 1.0:
            raise ValueError("carrier coupling must lie in [0, 1]")
        if self.hysteresis not in {1, 2, 3}:
            raise ValueError("carrier hysteresis must be one, two, or three")
        if self.topology not in TOPOLOGIES:
            raise ValueError("unknown local carrier topology")
        if self.k not in {1, 2, 3, 5, 7, genes}:
            raise ValueError("local carrier capacity must be 1, 2, 3, 5, 7, or all genes")
        if self.topology == "all" and self.k != genes:
            raise ValueError("all topology requires full capacity")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LocalConditionSpec:
    """One explicit mechanism/intervention cell (no Cartesian expansion)."""

    name: str
    genome: str | None
    intervention: str
    noise: str
    primary: bool = False

    def validate(self, genomes: tuple[LocalCarrierGenome, ...], noises: tuple[CopyNoiseSpec, ...]) -> None:
        locus = intervention_locus(self.intervention, 10)
        if not self.name or (self.intervention not in INTERVENTIONS and locus is None):
            raise ValueError("invalid local PH condition")
        genome_names = {value.name for value in genomes}
        noise_names = {value.name for value in noises}
        if self.intervention not in {"zero", "perfect_latch"} and self.genome not in genome_names:
            raise ValueError("local condition references an unknown genome")
        if self.intervention in {"zero", "perfect_latch"} and self.genome is not None:
            raise ValueError("floor and ceiling conditions do not accept a genome")
        if self.noise not in noise_names:
            raise ValueError("local condition references unknown copy noise")


@dataclass(frozen=True)
class LocalStudySpec:
    """Immutable untouched-confirmation contract."""

    cohort_id: str
    phase: str
    master_seed: str
    source_count: int
    genomes: tuple[LocalCarrierGenome, ...]
    noises: tuple[CopyNoiseSpec, ...]
    conditions: tuple[LocalConditionSpec, ...]
    checkpoint_generations: tuple[int, ...] = (0, 1, 2, 4, 8, 16)
    challenges: tuple[str, ...] = ("forced_break", "neutral_damage", "release_only")
    futures_per_history: int = 16
    genes: int = 10
    cue_fraction: float = 1.0
    cue_dwell: int = 1
    generation_cycles: int = 4
    horizon: int = 32
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    exploratory: bool = False

    def validate(self) -> None:
        if not self.cohort_id or not self.phase or len(self.master_seed) < 32:
            raise ValueError("invalid local PH study identity")
        if self.source_count < 1 or self.genes != 10:
            raise ValueError("local PH v1 requires positive ten-gene Wagner sources")
        if not self.genomes or len({value.name for value in self.genomes}) != len(self.genomes):
            raise ValueError("local PH genomes must be nonempty and unique")
        for value in self.genomes:
            value.validate(self.genes)
        if not self.noises or len({value.name for value in self.noises}) != len(self.noises):
            raise ValueError("copy-noise settings must be nonempty and unique")
        for value in self.noises:
            value.validate()
        if not self.conditions or len({value.name for value in self.conditions}) != len(self.conditions):
            raise ValueError("local PH conditions must be nonempty and unique")
        for value in self.conditions:
            value.validate(self.genomes, self.noises)
        if tuple(sorted(set(self.checkpoint_generations))) != self.checkpoint_generations:
            raise ValueError("local PH checkpoints must be increasing and unique")
        if not self.checkpoint_generations or self.checkpoint_generations[0] != 0:
            raise ValueError("local PH checkpoints must start at zero")
        if not set(self.challenges).issubset({"forced_break", "neutral_damage", "release_only"}):
            raise ValueError("unknown local PH challenge")
        if self.futures_per_history < 4 or self.futures_per_history % 2:
            raise ValueError("local PH futures must be even and at least four")
        if not 0.0 < self.cue_fraction <= 1.0 or self.cue_dwell < 1:
            raise ValueError("invalid local PH founder cue")
        if self.generation_cycles < 1 or self.horizon < max(12, self.strict_run):
            raise ValueError("invalid local PH development horizon")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid expression noise")
        if not 0.0 <= self.neutral_damage_fraction <= 1.0:
            raise ValueError("invalid neutral damage")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid local PH interval settings")

    def genome(self, name: str) -> LocalCarrierGenome:
        return next(value for value in self.genomes if value.name == name)

    def noise(self, name: str) -> CopyNoiseSpec:
        return next(value for value in self.noises if value.name == name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LocalStudySpec":
        fields = dict(value)
        fields["genomes"] = tuple(LocalCarrierGenome(**item) for item in fields["genomes"])
        fields["noises"] = tuple(CopyNoiseSpec(**item) for item in fields["noises"])
        fields["conditions"] = tuple(LocalConditionSpec(**item) for item in fields["conditions"])
        fields["checkpoint_generations"] = tuple(fields["checkpoint_generations"])
        fields["challenges"] = tuple(fields["challenges"])
        result = cls(**fields)
        result.validate()
        return result


@dataclass(frozen=True)
class LocalSearchSpec:
    """Frozen evolutionary search contract."""

    cohort_id: str
    master_seed: str
    training_sources: int = 32
    validation_sources: int = 16
    population_size: int = 64
    generations: int = 12
    rotating_panel_size: int = 8
    training_futures_per_history: int = 4
    validation_futures_per_history: int = 8
    genes: int = 10
    cue_fraction: float = 1.0
    cue_dwell: int = 1
    generation_cycles: int = 4
    horizon: int = 32
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    bootstrap_repetitions: int = 1024
    interval_level: float = 0.95

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid local search identity")
        if self.genes != 10 or self.training_sources < self.rotating_panel_size:
            raise ValueError("invalid local search source dimensions")
        if self.training_sources % self.rotating_panel_size:
            raise ValueError("training sources must divide into rotating panels")
        if self.validation_sources < 3 or self.population_size < 8 or self.generations < 1:
            raise ValueError("local search is too small")
        for value in (self.training_futures_per_history, self.validation_futures_per_history):
            if value < 4 or value % 2:
                raise ValueError("local search futures must be even and at least four")
        if not 0.0 < self.cue_fraction <= 1.0 or self.cue_dwell < 1:
            raise ValueError("invalid local search founder cue")
        if self.horizon < max(12, self.strict_run) or self.generation_cycles < 1:
            raise ValueError("invalid local search horizon")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def expected_local_records(spec: LocalStudySpec) -> int:
    """Return the exact non-Cartesian confirmation archive size."""

    return (
        spec.source_count
        * 2
        * spec.futures_per_history
        * len(spec.conditions)
        * len(spec.checkpoint_generations)
        * len(spec.challenges)
    )
