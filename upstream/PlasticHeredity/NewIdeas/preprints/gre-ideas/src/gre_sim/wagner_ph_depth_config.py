"""Frozen contract for Wagner PH Interpreter-Depth v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_direct_config import direct_prediction_spec


DEPTH_CAMPAIGN_FORMAT = "gre-wagner-ph-interpreter-depth-campaign-v1"
DEPTH_ATLAS_FORMAT = "gre-wagner-ph-interpreter-atlas-v1"
DEPTH_EVOLUTION_FORMAT = "gre-wagner-ph-interpreter-depth-evolution-v1"
DEPTH_AUDIT_FORMAT = "gre-wagner-ph-interpreter-depth-audit-v1"
DEPTH_PEDIGREE_FORMAT = "gre-wagner-ph-interpreter-depth-pedigree-v1"
DEPTH_ANALYSIS_FORMAT = "gre-wagner-ph-interpreter-depth-analysis-v1"

DEPTH_ARMS = (
    "individual_reset",
    "offspring3_reset",
    "offspring8_reset",
    "lineage2x2_reset",
    "individual_local",
    "offspring8_local",
)

ATLAS_PERTURBATIONS = ("reset", "local_add", "zero", "sign_reverse")


def arm_settings(name: str) -> dict[str, Any]:
    if name not in DEPTH_ARMS:
        raise ValueError(f"unknown interpreter-depth arm: {name}")
    if name.startswith("individual_"):
        selection_mode, children, grandchildren = "individual", 0, 0
    elif name.startswith("lineage2x2_"):
        selection_mode, children, grandchildren = "lineage", 2, 2
    elif name.startswith("offspring3_"):
        selection_mode, children, grandchildren = "offspring", 3, 0
    else:
        selection_mode, children, grandchildren = "offspring", 8, 0
    return {
        "selection_mode": selection_mode,
        "weight_mutation": "local" if name.endswith("_local") else "reset",
        "virtual_children": children,
        "virtual_grandchildren_per_child": grandchildren,
    }


def matched_control(name: str) -> str:
    return "individual_local" if arm_settings(name)["weight_mutation"] == "local" else "individual_reset"


@dataclass(frozen=True)
class InterpreterDepthSpec:
    """Six-hour develop-then-confirm experiment on Wagner carrier interpretation."""

    cohort_id: str
    master_seed: str
    atlas_seed: str
    audit_seed: str
    pedigree_seed: str
    confirmation_seed: str
    parent_cohort_id: str = "wagner-ph-robustness-ratchet-v1"
    parent_source_variant: str = "rho90_full"
    arms: tuple[str, ...] = DEPTH_ARMS
    atlas_perturbations: tuple[str, ...] = ATLAS_PERTURBATIONS
    task_count: int = 12
    atlas_roots_per_task: int = 2
    atlas_edge_limit: int = 100
    atlas_futures_per_history: int = 2
    atlas_lineage_generations: int = 8
    population_size: int = 16
    generations: int = 24
    elite_count: int = 2
    tournament_size: int = 3
    predictive_persistence: float = 0.9
    local_weight_sigma: float = 0.1
    audit_futures_per_history: int = 16
    audit_persistence: tuple[float, ...] = (0.0, 0.5, 0.9, 1.0)
    audit_cue_fractions: tuple[float, ...] = (0.0, 0.25)
    pedigree_roots_per_task: int = 2
    pedigree_lineages_per_root: int = 4
    pedigree_depths: tuple[int, ...] = (1, 2, 4)
    pedigree_futures_per_history: int = 16
    retention_fraction: float = 0.70
    retention_mean_gate: float = 0.70
    retention_lower_gate: float = 0.50
    information_advantage_gate: float = 0.08
    retention_advantage_gate: float = 0.30
    performance_loss_gate: float = 0.05
    distance_two_retention_gate: float = 0.55
    distance_four_retention_gate: float = 0.35
    confirmation_task_count: int = 16
    confirmation_burnin_generations: int = 30
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    maximum_workers: int = 4
    hard_wall_seconds: int = 21_600
    soft_wall_seconds: int = 20_700
    stage_reservations_seconds: tuple[int, ...] = (
        3600,
        6000,
        3600,
        300,
        3600,
        3000,
        600,
    )
    exploratory: bool = True
    evidence_strategy: str = "develop_then_confirm"

    def validate(self) -> None:
        seeds = (
            self.master_seed,
            self.atlas_seed,
            self.audit_seed,
            self.pedigree_seed,
            self.confirmation_seed,
        )
        if not self.cohort_id or min(map(len, seeds)) < 32 or len(set(seeds)) != len(seeds):
            raise ValueError("depth campaign identities and seed families must be distinct")
        if self.arms != DEPTH_ARMS or self.atlas_perturbations != ATLAS_PERTURBATIONS:
            raise ValueError("interpreter-depth arms and atlas perturbations are frozen")
        dimensions = (
            self.task_count,
            self.atlas_roots_per_task,
            self.atlas_edge_limit,
            self.atlas_futures_per_history,
            self.atlas_lineage_generations,
            self.population_size,
            self.generations,
            self.elite_count,
            self.tournament_size,
            self.audit_futures_per_history,
            self.pedigree_roots_per_task,
            self.pedigree_lineages_per_root,
            self.pedigree_futures_per_history,
            self.confirmation_task_count,
            self.confirmation_burnin_generations,
            self.bootstrap_repetitions,
        )
        if min(dimensions) < 1 or self.population_size <= self.elite_count:
            raise ValueError("invalid interpreter-depth dimensions")
        if self.atlas_edge_limit > 100:
            raise ValueError("ten-gene Wagner networks contain only 100 directed weights")
        if any(value % 2 for value in (
            self.atlas_futures_per_history,
            self.audit_futures_per_history,
            self.pedigree_futures_per_history,
        )):
            raise ValueError("paired future counts must be even")
        if self.pedigree_depths != (1, 2, 4):
            raise ValueError("mutation-distance pedigree is frozen at depths 1, 2, and 4")
        for grid in (self.audit_persistence, self.audit_cue_fractions):
            if tuple(sorted(set(grid))) != grid or min(grid) < 0.0 or max(grid) > 1.0:
                raise ValueError("ecology grids must be ordered and unique in [0, 1]")
        if self.audit_persistence != (0.0, 0.5, 0.9, 1.0):
            raise ValueError("causal audit persistence grid is frozen")
        if self.audit_cue_fractions != (0.0, 0.25):
            raise ValueError("causal audit cue grid is frozen")
        if not 0.0 <= self.predictive_persistence <= 1.0 or self.local_weight_sigma <= 0.0:
            raise ValueError("invalid ecology or local mutation scale")
        if not 0.0 < self.retention_fraction <= 1.0 or not 0.0 < self.interval_level < 1.0:
            raise ValueError("invalid retention or interval definition")
        if min(
            self.retention_mean_gate,
            self.retention_lower_gate,
            self.information_advantage_gate,
            self.retention_advantage_gate,
            self.performance_loss_gate,
            self.distance_two_retention_gate,
            self.distance_four_retention_gate,
        ) < 0.0:
            raise ValueError("decision gates cannot be negative")
        if self.maximum_workers != 4:
            raise ValueError("interpreter-depth campaign is capped at four CPU workers")
        if (self.hard_wall_seconds, self.soft_wall_seconds) != (21_600, 20_700):
            raise ValueError("interpreter-depth campaign is frozen at six hours")
        if sum(self.stage_reservations_seconds) != self.soft_wall_seconds:
            raise ValueError("stage reservations must cover the scientific soft boundary")
        if self.confirmation_task_count <= self.task_count:
            raise ValueError("fresh confirmation must use more task clusters than development")
        if self.evidence_strategy != "develop_then_confirm":
            raise ValueError("development and confirmation evidence must remain separate")

    @property
    def development_population_count(self) -> int:
        return len(self.arms) * self.task_count

    @property
    def development_pedigree_rows(self) -> int:
        return (
            self.development_population_count
            * self.pedigree_roots_per_task
            * self.pedigree_lineages_per_root
            * max(self.pedigree_depths)
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "InterpreterDepthSpec":
        fields = dict(value)
        for name in (
            "arms",
            "atlas_perturbations",
            "audit_persistence",
            "audit_cue_fractions",
            "pedigree_depths",
            "stage_reservations_seconds",
        ):
            fields[name] = tuple(fields[name])
        result = cls(**fields)
        result.validate()
        return result

    def kernel(self, *, confirmation: bool = False) -> CooptionSpec:
        direct = direct_prediction_spec(smoke=self.task_count == 1)
        base = direct.cooption_spec()
        tasks = self.confirmation_task_count if confirmation else self.task_count
        result = replace(
            base,
            cohort_id=self.cohort_id + ("-confirmation" if confirmation else ""),
            master_seed=self.confirmation_seed if confirmation else self.master_seed,
            confirmation_seed=canonical_digest((self.confirmation_seed, "sealed-reserve")),
            evolution_tasks=tasks,
            confirmation_tasks=max(tasks, base.confirmation_tasks),
            population_size=self.population_size,
            generations=self.generations,
            elite_count=self.elite_count,
            tournament_size=self.tournament_size,
            audit_futures_per_history=self.audit_futures_per_history,
            audit_persistence=self.audit_persistence,
            cue_fractions=self.audit_cue_fractions,
            bootstrap_repetitions=self.bootstrap_repetitions,
        )
        result.validate()
        return result

    def smoke(self) -> "InterpreterDepthSpec":
        result = replace(
            self,
            cohort_id=f"{self.cohort_id}-smoke",
            master_seed=canonical_digest((self.master_seed, "software-smoke")),
            atlas_seed=canonical_digest((self.atlas_seed, "software-smoke")),
            audit_seed=canonical_digest((self.audit_seed, "software-smoke")),
            pedigree_seed=canonical_digest((self.pedigree_seed, "software-smoke")),
            confirmation_seed=canonical_digest((self.confirmation_seed, "software-smoke")),
            task_count=1,
            atlas_roots_per_task=1,
            atlas_edge_limit=4,
            atlas_futures_per_history=2,
            atlas_lineage_generations=2,
            population_size=4,
            generations=2,
            elite_count=1,
            audit_futures_per_history=4,
            pedigree_roots_per_task=1,
            pedigree_lineages_per_root=1,
            pedigree_depths=(1, 2, 4),
            pedigree_futures_per_history=4,
            confirmation_task_count=2,
            confirmation_burnin_generations=2,
            bootstrap_repetitions=64,
        )
        result.validate()
        return result


DEPTH_MASTER_SEED = canonical_digest("wagner-ph-interpreter-depth-v1-development-2026-08-29")
DEPTH_ATLAS_SEED = canonical_digest("wagner-ph-interpreter-depth-v1-atlas-2026-08-29")
DEPTH_AUDIT_SEED = canonical_digest("wagner-ph-interpreter-depth-v1-audit-2026-08-29")
DEPTH_PEDIGREE_SEED = canonical_digest("wagner-ph-interpreter-depth-v1-pedigree-2026-08-29")
DEPTH_CONFIRMATION_SEED = canonical_digest("wagner-ph-interpreter-depth-v1-confirmation-2026-08-29")


def interpreter_depth_spec(*, smoke: bool = False) -> InterpreterDepthSpec:
    result = InterpreterDepthSpec(
        cohort_id="wagner-ph-interpreter-depth-v1",
        master_seed=DEPTH_MASTER_SEED,
        atlas_seed=DEPTH_ATLAS_SEED,
        audit_seed=DEPTH_AUDIT_SEED,
        pedigree_seed=DEPTH_PEDIGREE_SEED,
        confirmation_seed=DEPTH_CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result
