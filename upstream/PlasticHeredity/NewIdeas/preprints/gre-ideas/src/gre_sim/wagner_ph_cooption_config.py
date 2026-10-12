"""Frozen contracts for the Wagner plastic-heredity co-option campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .local_ph_config import CopyNoiseSpec, TOPOLOGIES


COOPTION_CAMPAIGN_FORMAT = "gre-wagner-ph-cooption-campaign-v1"
COOPTION_TASK_FORMAT = "gre-wagner-ph-cooption-task-v1"
COOPTION_ATLAS_RESULT_FORMAT = "gre-wagner-ph-cooption-atlas-result-v1"
COOPTION_EVOLUTION_RESULT_FORMAT = "gre-wagner-ph-cooption-evolution-result-v1"
COOPTION_AUDIT_RESULT_FORMAT = "gre-wagner-ph-cooption-audit-result-v1"
COOPTION_ANALYSIS_FORMAT = "gre-wagner-ph-cooption-analysis-v1"

COOPTION_TREATMENTS = (
    "direct_independent",
    "cooption_independent",
    "direct_linked",
    "cooption_linked",
    "direct_linked_ramp",
    "cooption_linked_ramp",
    "robustness_only_independent",
    "neutral_drift",
)

MEANING_INTERVENTIONS = (
    "natural",
    "independent_history",
    "opposite_history",
    "shuffle",
    "zero",
    "reader_off",
    "renewal_off",
    "founder_write_off",
)

CAPACITY_STEPS = (1, 2, 3, 5, 7, 10)
PRECISION_STEPS = (2, 4, 8)


def treatment_architecture(treatment: str) -> str:
    if treatment not in COOPTION_TREATMENTS:
        raise ValueError(f"unknown co-option treatment: {treatment}")
    if treatment.endswith("linked_ramp"):
        return "linked_ramp"
    if treatment.endswith("linked"):
        return "linked"
    return "independent"


def treatment_selection_phase(treatment: str, generation: int, switch: int) -> str:
    """Return the performance-only objective active at one generation."""

    if treatment not in COOPTION_TREATMENTS:
        raise ValueError(f"unknown co-option treatment: {treatment}")
    if treatment == "neutral_drift":
        return "neutral"
    if treatment == "robustness_only_independent":
        return "homeostasis"
    if treatment.startswith("direct_"):
        return "predictive"
    return "homeostasis" if generation <= switch else "predictive"


def matched_direct(treatment: str) -> str:
    mapping = {
        "cooption_independent": "direct_independent",
        "cooption_linked": "direct_linked",
        "cooption_linked_ramp": "direct_linked_ramp",
    }
    if treatment not in mapping:
        raise ValueError(f"no matched direct arm for {treatment}")
    return mapping[treatment]


@dataclass(frozen=True)
class QuantizedCarrierGenome:
    """A local writer/reader plus an explicit finite mark alphabet."""

    name: str
    write_rate: float
    decay: float
    coupling: float
    hysteresis: int
    topology: str
    k: int
    bits_per_mark: int

    def validate(self, genes: int = 10) -> None:
        if not self.name:
            raise ValueError("quantized carrier name cannot be empty")
        if not 0.0 <= self.write_rate <= 1.0:
            raise ValueError("write rate must lie in [0, 1]")
        if not 0.0 <= self.decay < 1.0:
            raise ValueError("carrier decay must lie in [0, 1)")
        if not 0.0 <= self.coupling <= 1.0:
            raise ValueError("carrier coupling must lie in [0, 1]")
        if self.hysteresis not in {1, 2, 3}:
            raise ValueError("carrier hysteresis must be one, two, or three")
        if self.topology not in TOPOLOGIES:
            raise ValueError("unknown carrier topology")
        if self.k not in CAPACITY_STEPS or self.k > genes:
            raise ValueError("invalid quantized carrier capacity")
        if self.topology == "all" and self.k != genes:
            raise ValueError("all topology requires full capacity")
        if self.bits_per_mark not in PRECISION_STEPS:
            raise ValueError("precision must be two, four, or eight bits per mark")

    @property
    def payload_upper_bits(self) -> int:
        return self.k * self.bits_per_mark

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CooptionSpec:
    """Prospective six-hour exploration with a separate confirmation reserve."""

    cohort_id: str
    master_seed: str
    confirmation_seed: str
    parent_cohort_id: str = "wagner-ph-origin-ladder-v1"
    treatments: tuple[str, ...] = COOPTION_TREATMENTS
    meaning_interventions: tuple[str, ...] = MEANING_INTERVENTIONS
    atlas_tasks: int = 24
    atlas_futures_per_history: int = 8
    atlas_persistence: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 0.9, 1.0)
    cue_fractions: tuple[float, ...] = (0.0, 0.25)
    evolution_tasks: int = 5
    population_size: int = 16
    generations: int = 30
    cooption_switch_generation: int = 15
    elite_count: int = 2
    tournament_size: int = 3
    training_panel_size: int = 16
    training_panels_per_generation: int = 4
    training_episode_generations: int = 4
    validation_panels: int = 4
    audit_futures_per_history: int = 16
    audit_persistence: tuple[float, ...] = (0.0, 0.5, 0.9, 1.0)
    lineage_generations: int = 16
    checkpoints: tuple[int, ...] = (1, 8, 16)
    genes: int = 10
    cue_dwell: int = 1
    generation_cycles: int = 4
    horizon: int = 16
    strict_run: int = 8
    stable_run: int = 3
    expression_flip_probability: float = 0.05
    noise: CopyNoiseSpec = CopyNoiseSpec("d095-p002", 0.95, 0.02, 0.05)
    capacity_cost: float = 0.035
    precision_cost: float = 0.015
    writing_cost: float = 0.025
    coupling_cost: float = 0.025
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    natural_zero_gate: float = 0.15
    information_gate: float = 0.10
    predictability_interaction_gate: float = 0.15
    low_predictability_mean_gate: float = -0.05
    donor_gate: float = 0.15
    reader_gate: float = 0.10
    renewal_gate: float = 0.05
    decoder_gate: float = 0.70
    cooption_advantage_gate: float = 0.08
    maximum_workers: int = 4
    hard_wall_seconds: int = 21_600
    soft_wall_seconds: int = 20_400
    stage_reservations_seconds: tuple[int, ...] = (2400, 12_600, 4800, 600)
    confirmation_tasks: int = 6
    confirmation_hard_wall_seconds: int = 14_400
    confirmation_soft_wall_seconds: int = 13_500
    pedigree_retention_gate: float = 0.70
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32 or len(self.confirmation_seed) < 32:
            raise ValueError("invalid co-option campaign identity")
        if self.master_seed == self.confirmation_seed:
            raise ValueError("exploration and confirmation seeds must be disjoint")
        if self.treatments != COOPTION_TREATMENTS:
            raise ValueError("co-option treatments are frozen and ordered")
        if self.meaning_interventions != MEANING_INTERVENTIONS:
            raise ValueError("carrier-meaning interventions are frozen and ordered")
        dimensions = (
            self.atlas_tasks,
            self.atlas_futures_per_history,
            self.evolution_tasks,
            self.population_size,
            self.generations,
            self.elite_count,
            self.tournament_size,
            self.training_panel_size,
            self.training_panels_per_generation,
            self.training_episode_generations,
            self.validation_panels,
            self.audit_futures_per_history,
            self.lineage_generations,
        )
        if min(dimensions) < 1:
            raise ValueError("co-option dimensions must be positive")
        if self.atlas_futures_per_history % 2 or self.audit_futures_per_history % 2:
            raise ValueError("atlas and audit futures must be even")
        if self.elite_count >= self.population_size:
            raise ValueError("elite count must be smaller than the population")
        if self.training_panel_size % self.training_panels_per_generation:
            raise ValueError("training panel must rotate evenly")
        if not 0 < self.cooption_switch_generation < self.generations:
            raise ValueError("co-option switch must lie inside the evolution run")
        if self.genes != 10 or self.horizon < self.strict_run or self.stable_run < 1:
            raise ValueError("co-option requires ten-gene Wagner tasks and a valid horizon")
        if self.generation_cycles < 1 or self.cue_dwell < 1:
            raise ValueError("developmental cycle counts must be positive")
        if not 0.0 <= self.expression_flip_probability <= 1.0:
            raise ValueError("invalid expression noise")
        self.noise.validate()
        for grid in (self.atlas_persistence, self.audit_persistence, self.cue_fractions):
            if tuple(sorted(set(grid))) != grid or min(grid) < 0.0 or max(grid) > 1.0:
                raise ValueError("ecology and cue grids must be ordered in [0, 1]")
        if self.atlas_persistence[0] != 0.0 or self.atlas_persistence[-1] != 1.0:
            raise ValueError("meaning atlas must include always-switch and always-stay")
        if 0.0 not in self.audit_persistence or 0.9 not in self.audit_persistence:
            raise ValueError("audit must include low and high predictability")
        if 0.0 not in self.cue_fractions:
            raise ValueError("audit must include a genuinely pre-cue condition")
        if tuple(sorted(set(self.checkpoints))) != self.checkpoints:
            raise ValueError("checkpoints must be increasing and unique")
        if self.checkpoints[-1] != self.lineage_generations:
            raise ValueError("last checkpoint must equal lineage length")
        costs = (self.capacity_cost, self.precision_cost, self.writing_cost, self.coupling_cost)
        if min(costs) < 0.0 or abs(sum(costs) - 0.10) > 1e-12:
            raise ValueError("maximum carrier cost must equal 0.10")
        if self.bootstrap_repetitions < 1 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid co-option inference")
        if not 1 <= self.maximum_workers <= 4:
            raise ValueError("co-option permits at most four CPU workers")
        if (self.hard_wall_seconds, self.soft_wall_seconds) != (21_600, 20_400):
            raise ValueError("initial co-option campaign is frozen at six hours")
        if sum(self.stage_reservations_seconds) != self.soft_wall_seconds:
            raise ValueError("stage reservations must cover the scientific soft budget")
        if (self.confirmation_hard_wall_seconds, self.confirmation_soft_wall_seconds) != (14_400, 13_500):
            raise ValueError("confirmation campaign is frozen at four hours")
        if self.confirmation_tasks < self.evolution_tasks:
            raise ValueError("confirmation must use more paired tasks than exploration")

    @property
    def population_count(self) -> int:
        return len(self.treatments) * self.evolution_tasks

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CooptionSpec":
        fields = dict(value)
        fields["noise"] = CopyNoiseSpec(**fields["noise"])
        for name in (
            "treatments",
            "meaning_interventions",
            "atlas_persistence",
            "cue_fractions",
            "audit_persistence",
            "checkpoints",
            "stage_reservations_seconds",
        ):
            fields[name] = tuple(fields[name])
        result = cls(**fields)
        result.validate()
        return result

    def smoke(self) -> "CooptionSpec":
        result = replace(
            self,
            cohort_id=f"{self.cohort_id}-smoke",
            master_seed=f"{self.master_seed[:-6]}smoke0",
            confirmation_seed=f"{self.confirmation_seed[:-6]}smoke1",
            atlas_tasks=1,
            atlas_futures_per_history=4,
            atlas_persistence=(0.0, 0.9, 1.0),
            cue_fractions=(0.0,),
            evolution_tasks=1,
            population_size=4,
            generations=2,
            cooption_switch_generation=1,
            elite_count=1,
            training_panel_size=4,
            training_panels_per_generation=2,
            training_episode_generations=2,
            validation_panels=2,
            audit_futures_per_history=4,
            audit_persistence=(0.0, 0.9),
            lineage_generations=2,
            checkpoints=(1, 2),
            horizon=8,
            strict_run=4,
            stable_run=2,
            bootstrap_repetitions=64,
            confirmation_tasks=2,
        )
        result.validate()
        return result
