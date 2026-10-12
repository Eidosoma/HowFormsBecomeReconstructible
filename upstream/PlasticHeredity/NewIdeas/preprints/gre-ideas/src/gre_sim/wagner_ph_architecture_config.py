"""Frozen contract for Wagner PH Interpreter Architecture v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_direct_config import direct_prediction_spec


ARCHITECTURE_FORMAT = "gre-wagner-ph-interpreter-architecture-v1"
ARCHITECTURE_ARMS = (
    "mh_single_ordinary",
    "mh_single_uniform",
    "mh_single_guided",
    "mh_repair_ordinary",
    "mh_repair_uniform",
    "mh_repair_guided",
    "mh_median3_ordinary",
)
SINGLE_CANDIDATES = ARCHITECTURE_ARMS[:3]
ENGINEERED_CANDIDATES = ARCHITECTURE_ARMS[3:]
CONTROL_ARMS = (
    "individual_single",
    "individual_repair",
    "individual_mean3",
    "mh_mean3_ordinary",
)


def arm_settings(name: str) -> dict[str, str]:
    if name not in ARCHITECTURE_ARMS + CONTROL_ARMS:
        raise ValueError(f"unknown interpreter-architecture arm: {name}")
    selection = "individual" if name.startswith("individual_") else "multihorizon"
    if "median3" in name:
        architecture = "median3"
    elif "mean3" in name:
        architecture = "mean3"
    elif "repair" in name:
        architecture = "repair"
    else:
        architecture = "single"
    challenge = "guided" if name.endswith("_guided") else "uniform" if name.endswith("_uniform") else "ordinary"
    return {"selection_mode": selection, "architecture": architecture, "challenge": challenge}


def evidence_family(name: str) -> str:
    architecture = arm_settings(name)["architecture"]
    if architecture == "single":
        return "ordinary_single"
    if architecture == "repair":
        return "engineered_repair"
    return "engineered_error_correction"


def uniform_control(name: str) -> str | None:
    settings = arm_settings(name)
    if settings["challenge"] != "guided":
        return None
    return name.removesuffix("guided") + "uniform"


@dataclass(frozen=True)
class ArchitectureSpec:
    cohort_id: str
    master_seed: str
    diagnosis_seed: str
    audit_seed: str
    pedigree_seed: str
    confirmation_seed: str
    task_count: int = 12
    confirmation_task_count: int = 16
    population_size: int = 16
    generations: int = 24
    confirmation_burnin_generations: int = 30
    elite_count: int = 2
    tournament_size: int = 3
    predictive_persistence: float = 0.9
    repair_maximum: float = 0.9
    repair_mutation_sigma: float = 0.05
    repair_cost: float = 0.04
    redundancy_cost: float = 0.04
    predictor_top_k: int = 10
    predictor_ridge: float = 1.0
    diagnosis_roots_per_task: int = 2
    diagnosis_chains_per_root: int = 16
    diagnosis_futures_per_history: int = 8
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
    distance_two_gate: float = 0.55
    distance_four_gate: float = 0.35
    information_advantage_gate: float = 0.08
    distance_one_advantage_gate: float = 0.30
    distance_four_advantage_gate: float = 0.20
    repair_attribution_gate: float = 0.15
    guided_attribution_gate: float = 0.10
    median_attribution_gate: float = 0.15
    performance_loss_gate: float = 0.05
    distance_four_information_fraction_gate: float = 0.50
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    maximum_workers: int = 4
    hard_wall_seconds: int = 28_800
    soft_wall_seconds: int = 27_600
    stage_reservations_seconds: tuple[int, ...] = (2400, 7200, 4200, 300, 7200, 4200, 900)
    arms: tuple[str, ...] = ARCHITECTURE_ARMS
    exploratory: bool = True
    evidence_strategy: str = "develop_then_confirm_top_two"

    def validate(self) -> None:
        seeds = (self.master_seed, self.diagnosis_seed, self.audit_seed, self.pedigree_seed, self.confirmation_seed)
        if not self.cohort_id or min(map(len, seeds)) < 32 or len(set(seeds)) != 5:
            raise ValueError("architecture identities and seed families must be distinct")
        if self.arms != ARCHITECTURE_ARMS:
            raise ValueError("architecture arms are frozen")
        if self.population_size not in {4, 16} or self.generations < 1 or self.population_size <= self.elite_count:
            raise ValueError("invalid architecture evolution dimensions")
        if self.task_count != 1 and self.population_size != 16:
            raise ValueError("production architecture populations are frozen at 16")
        if self.pedigree_depths != (1, 2, 4) or self.predictor_top_k != 10 or self.predictor_ridge != 1.0:
            raise ValueError("architecture diagnostic contract changed")
        if self.maximum_workers != 4 or (self.hard_wall_seconds, self.soft_wall_seconds) != (28800, 27600):
            raise ValueError("architecture runtime contract changed")
        if sum(self.stage_reservations_seconds) != 26400 or self.soft_wall_seconds - sum(self.stage_reservations_seconds) != 1200:
            raise ValueError("architecture reservations must preserve soft contingency")
        if not 0.0 < self.repair_maximum < 1.0 or min(self.repair_mutation_sigma, self.repair_cost, self.redundancy_cost) <= 0.0:
            raise ValueError("invalid repair or redundancy contract")
        if any(value % 2 for value in (self.diagnosis_futures_per_history, self.audit_futures_per_history, self.pedigree_futures_per_history)):
            raise ValueError("paired future counts must be even")
        if self.evidence_strategy != "develop_then_confirm_top_two":
            raise ValueError("two-candidate confirmation is mandatory")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ArchitectureSpec":
        payload = dict(value)
        for field in ("arms", "audit_persistence", "audit_cue_fractions", "pedigree_depths", "stage_reservations_seconds"):
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

    def smoke(self) -> "ArchitectureSpec":
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
            diagnosis_roots_per_task=1,
            diagnosis_chains_per_root=2,
            diagnosis_futures_per_history=4,
            audit_futures_per_history=4,
            pedigree_roots_per_task=1,
            pedigree_lineages_per_root=1,
            pedigree_futures_per_history=4,
            bootstrap_repetitions=64,
        )
        result.validate()
        return result


MASTER_SEED = canonical_digest("wagner-ph-interpreter-architecture-v1-development-2026-08-30")
DIAGNOSIS_SEED = canonical_digest("wagner-ph-interpreter-architecture-v1-diagnosis-2026-08-30")
AUDIT_SEED = canonical_digest("wagner-ph-interpreter-architecture-v1-audit-2026-08-30")
PEDIGREE_SEED = canonical_digest("wagner-ph-interpreter-architecture-v1-pedigree-2026-08-30")
CONFIRMATION_SEED = canonical_digest("wagner-ph-interpreter-architecture-v1-confirmation-2026-08-30")


def architecture_spec(*, smoke: bool = False) -> ArchitectureSpec:
    result = ArchitectureSpec(
        cohort_id="wagner-ph-interpreter-architecture-v1",
        master_seed=MASTER_SEED,
        diagnosis_seed=DIAGNOSIS_SEED,
        audit_seed=AUDIT_SEED,
        pedigree_seed=PEDIGREE_SEED,
        confirmation_seed=CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result
