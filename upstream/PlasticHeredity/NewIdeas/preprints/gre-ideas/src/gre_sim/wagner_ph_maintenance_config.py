"""Frozen contract for Wagner PH Adaptive Maintenance v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_direct_config import direct_prediction_spec


MAINTENANCE_FORMAT = "gre-wagner-ph-adaptive-maintenance-v1"

DEVELOPMENT_ARMS = (
    "individual_single_rho90",
    "mh_single_rho90",
    "individual_global_seeded_rho90",
    "mh_global_seeded_rho90",
    "mh_global_zero_rho90",
    "mh_node_repair_zero_rho90",
    "mh_duplication_zero_rho90",
    "mh_median3_rho90",
    "mh_node_repair_zero_rho50",
    "mh_duplication_zero_rho50",
)

EMERGENT_CANDIDATES = (
    "mh_global_zero_rho90",
    "mh_node_repair_zero_rho90",
    "mh_duplication_zero_rho90",
)
ENGINEERED_CANDIDATES = (
    "mh_global_seeded_rho90",
    "mh_median3_rho90",
)
CONTROL_ARMS = (
    "individual_single_rho90",
    "mh_single_rho90",
    "individual_global_seeded_rho90",
    "mh_node_repair_zero_rho50",
    "mh_duplication_zero_rho50",
)


def arm_settings(name: str) -> dict[str, Any]:
    if name not in DEVELOPMENT_ARMS:
        raise ValueError(f"unknown adaptive-maintenance arm: {name}")
    if "node_repair" in name:
        architecture = "node_repair"
        initial = "zero"
    elif "global" in name:
        architecture = "global_repair"
        initial = "seeded" if "seeded" in name else "zero"
    elif "duplication" in name:
        architecture = "duplication"
        initial = "one_copy"
    elif "median3" in name:
        architecture = "median3"
        initial = "engineered"
    else:
        architecture = "single"
        initial = "ordinary"
    return {
        "selection_mode": "individual" if name.startswith("individual_") else "multihorizon",
        "architecture": architecture,
        "initialization": initial,
        "predictive_persistence": 0.5 if name.endswith("rho50") else 0.9,
    }


def evidence_tier(name: str) -> str:
    settings = arm_settings(name)
    if settings["architecture"] == "single":
        return "ordinary_single"
    if name in EMERGENT_CANDIDATES:
        return "dormant_start_maintenance"
    return "engineered_sufficiency"


def matched_single_control(_: str) -> str:
    return "mh_single_rho90"


def matched_ecology_control(name: str) -> str | None:
    mapping = {
        "mh_node_repair_zero_rho90": "mh_node_repair_zero_rho50",
        "mh_duplication_zero_rho90": "mh_duplication_zero_rho50",
    }
    return mapping.get(name)


def matched_individual_control(name: str) -> str | None:
    if name == "mh_single_rho90":
        return "individual_single_rho90"
    if name == "mh_global_seeded_rho90":
        return "individual_global_seeded_rho90"
    return None


@dataclass(frozen=True)
class MaintenanceSpec:
    cohort_id: str
    master_seed: str
    diagnosis_seed: str
    audit_seed: str
    pedigree_seed: str
    confirmation_seed: str
    arms: tuple[str, ...] = DEVELOPMENT_ARMS
    task_count: int = 16
    confirmation_task_count: int = 12
    population_size: int = 16
    generations: int = 30
    confirmation_burnin_generations: int = 30
    elite_count: int = 2
    tournament_size: int = 3
    lineage_count: int = 4
    lineage_depth: int = 4
    tail_size: int = 2
    audit_futures_per_history: int = 16
    audit_persistence: tuple[float, ...] = (0.0, 0.5, 0.9, 1.0)
    cue_fractions: tuple[float, ...] = (0.0, 0.25)
    lineage_generations: int = 12
    lineage_checkpoints: tuple[int, ...] = (1, 4, 12)
    pedigree_roots_per_task: int = 2
    pedigree_lineages_per_root: int = 4
    pedigree_depths: tuple[int, ...] = (1, 2, 4)
    pedigree_futures_per_history: int = 16
    seeded_repair_strength: float = 0.8
    repair_maximum: float = 0.9
    repair_mutation_sigma: float = 0.05
    repair_cost: float = 0.04
    copy_number_mutation_probability: float = 0.05
    decoder_mutation_probability: float = 0.05
    extra_copy_cost: float = 0.02
    retention_fraction: float = 0.70
    retention_mean_gate: float = 0.70
    retention_lower_gate: float = 0.50
    distance_two_gate: float = 0.55
    distance_four_gate: float = 0.35
    information_gate: float = 0.10
    information_advantage_gate: float = 0.08
    distance_four_advantage_gate: float = 0.20
    mechanism_gate: float = 0.15
    localization_gate: float = 0.10
    performance_loss_gate: float = 0.05
    f12_fraction_gate: float = 0.50
    natural_zero_gate: float = 0.15
    predictability_interaction_gate: float = 0.15
    low_predictability_mean_gate: float = -0.05
    donor_gate: float = 0.15
    reader_gate: float = 0.10
    renewal_gate: float = 0.05
    decoder_gate: float = 0.70
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    maximum_workers: int = 4
    hard_wall_seconds: int = 28_800
    soft_wall_seconds: int = 27_600
    stage_reservations_seconds: tuple[int, ...] = (1_800, 18_000, 6_000, 600)
    confirmation_hard_wall_seconds: int = 14_400
    confirmation_soft_wall_seconds: int = 13_500
    confirmation_stage_reservations_seconds: tuple[int, ...] = (1_800, 6_000, 5_100, 600)
    exploratory: bool = True
    evidence_strategy: str = "development_then_explicitly_authorized_confirmation"

    def validate(self) -> None:
        seeds = (
            self.master_seed,
            self.diagnosis_seed,
            self.audit_seed,
            self.pedigree_seed,
            self.confirmation_seed,
        )
        if not self.cohort_id or min(map(len, seeds)) < 32 or len(set(seeds)) != 5:
            raise ValueError("maintenance identities and seed families must be distinct")
        if self.arms != DEVELOPMENT_ARMS:
            raise ValueError("adaptive-maintenance arms are frozen and ordered")
        if self.population_size not in {4, 16} or self.population_size <= self.elite_count:
            raise ValueError("invalid maintenance population dimensions")
        if self.task_count != 1 and (self.population_size, self.generations) != (16, 30):
            raise ValueError("production maintenance evolution dimensions changed")
        if self.lineage_depth != 4 or self.pedigree_depths != (1, 2, 4):
            raise ValueError("maintenance mutation horizons are frozen")
        if self.task_count == 1:
            if self.lineage_checkpoints != (1, 2) or self.lineage_generations != 2:
                raise ValueError("maintenance smoke checkpoints changed")
        elif self.lineage_checkpoints != (1, 4, 12) or self.lineage_generations != 12:
            raise ValueError("maintenance F12 checkpoints are frozen")
        if any(value % 2 for value in (self.audit_futures_per_history, self.pedigree_futures_per_history)):
            raise ValueError("paired future counts must be even")
        if not 0.0 <= self.seeded_repair_strength <= self.repair_maximum < 1.0:
            raise ValueError("invalid seeded or maximum repair")
        if min(self.repair_mutation_sigma, self.repair_cost, self.extra_copy_cost) <= 0.0:
            raise ValueError("maintenance mutation and cost parameters must be positive")
        if not 0.0 < self.copy_number_mutation_probability <= 1.0 or not 0.0 < self.decoder_mutation_probability <= 1.0:
            raise ValueError("invalid duplication mutation probability")
        if self.maximum_workers != 4:
            raise ValueError("adaptive maintenance is capped at four workers")
        if (self.hard_wall_seconds, self.soft_wall_seconds) != (28_800, 27_600):
            raise ValueError("development must retain its eight-hour boundary")
        if sum(self.stage_reservations_seconds) != 26_400 or self.soft_wall_seconds - sum(self.stage_reservations_seconds) != 1_200:
            raise ValueError("development reservations must retain 1,200 seconds contingency")
        if (self.confirmation_hard_wall_seconds, self.confirmation_soft_wall_seconds) != (14_400, 13_500):
            raise ValueError("confirmation must retain its four-hour boundary")
        if sum(self.confirmation_stage_reservations_seconds) != self.confirmation_soft_wall_seconds:
            raise ValueError("confirmation reservations must cover its soft wall")
        if self.evidence_strategy != "development_then_explicitly_authorized_confirmation":
            raise ValueError("confirmation authorization boundary changed")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MaintenanceSpec":
        payload = dict(value)
        for field in (
            "arms",
            "audit_persistence",
            "cue_fractions",
            "lineage_checkpoints",
            "pedigree_depths",
            "stage_reservations_seconds",
            "confirmation_stage_reservations_seconds",
        ):
            payload[field] = tuple(payload[field])
        result = cls(**payload)
        result.validate()
        return result

    def kernel(self, *, confirmation: bool = False) -> CooptionSpec:
        base = direct_prediction_spec(smoke=self.task_count == 1).cooption_spec()
        tasks = self.confirmation_task_count if confirmation else self.task_count
        result = replace(
            base,
            cohort_id=self.cohort_id + ("-confirmation" if confirmation else ""),
            master_seed=self.confirmation_seed if confirmation else self.master_seed,
            confirmation_seed=canonical_digest((self.confirmation_seed, "unused-nested-confirmation")),
            evolution_tasks=tasks,
            confirmation_tasks=max(tasks, base.confirmation_tasks),
            population_size=self.population_size,
            generations=self.generations,
            elite_count=self.elite_count,
            tournament_size=self.tournament_size,
            audit_futures_per_history=self.audit_futures_per_history,
            audit_persistence=self.audit_persistence,
            cue_fractions=self.cue_fractions,
            lineage_generations=self.lineage_generations,
            checkpoints=self.lineage_checkpoints,
            bootstrap_repetitions=self.bootstrap_repetitions,
        )
        result.validate()
        return result

    def smoke(self) -> "MaintenanceSpec":
        result = replace(
            self,
            cohort_id=self.cohort_id + "-smoke",
            master_seed=canonical_digest((self.master_seed, "smoke")),
            diagnosis_seed=canonical_digest((self.diagnosis_seed, "smoke")),
            audit_seed=canonical_digest((self.audit_seed, "smoke")),
            pedigree_seed=canonical_digest((self.pedigree_seed, "smoke")),
            confirmation_seed=canonical_digest((self.confirmation_seed, "smoke")),
            task_count=1,
            confirmation_task_count=2,
            population_size=4,
            generations=2,
            confirmation_burnin_generations=2,
            elite_count=1,
            lineage_count=2,
            tail_size=1,
            audit_futures_per_history=4,
            audit_persistence=(0.0, 0.9),
            cue_fractions=(0.0,),
            lineage_generations=2,
            lineage_checkpoints=(1, 2),
            pedigree_roots_per_task=1,
            pedigree_lineages_per_root=1,
            pedigree_depths=(1, 2, 4),
            pedigree_futures_per_history=4,
            bootstrap_repetitions=64,
        )
        result.validate()
        return result


MASTER_SEED = canonical_digest("wagner-ph-adaptive-maintenance-v1-development-2026-08-31")
DIAGNOSIS_SEED = canonical_digest("wagner-ph-adaptive-maintenance-v1-diagnosis-2026-08-31")
AUDIT_SEED = canonical_digest("wagner-ph-adaptive-maintenance-v1-audit-2026-08-31")
PEDIGREE_SEED = canonical_digest("wagner-ph-adaptive-maintenance-v1-pedigree-2026-08-31")
CONFIRMATION_SEED = canonical_digest("wagner-ph-adaptive-maintenance-v1-confirmation-2026-08-31")


def maintenance_spec(*, smoke: bool = False) -> MaintenanceSpec:
    result = MaintenanceSpec(
        cohort_id="wagner-ph-adaptive-maintenance-v1",
        master_seed=MASTER_SEED,
        diagnosis_seed=DIAGNOSIS_SEED,
        audit_seed=AUDIT_SEED,
        pedigree_seed=PEDIGREE_SEED,
        confirmation_seed=CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result


__all__ = (
    "CONTROL_ARMS",
    "DEVELOPMENT_ARMS",
    "EMERGENT_CANDIDATES",
    "ENGINEERED_CANDIDATES",
    "MAINTENANCE_FORMAT",
    "MaintenanceSpec",
    "arm_settings",
    "evidence_tier",
    "maintenance_spec",
    "matched_ecology_control",
    "matched_individual_control",
    "matched_single_control",
)
