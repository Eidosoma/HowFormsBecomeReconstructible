"""Frozen configuration for Wagner PH Global Repair Ratchet v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .artifacts import canonical_digest
from .wagner_ph_maintenance_config import MaintenanceSpec, maintenance_spec


RATCHET_FORMAT = "gre-wagner-ph-global-repair-ratchet-v1"
ROUTE_NAMES = (
    "ordinary_mh",
    "repair_zero_standard",
    "repair_zero_lowcost",
    "repair_zero_cost_ramp",
    "repair_zero_variation_pulse",
    "repair_zero_tail8",
    "repair_prime005",
    "repair_seeded080",
)


@dataclass(frozen=True)
class RepairRoute:
    name: str
    legacy_arm: str
    evidence_tier: str
    initial_repair: float
    final_repair_cost: float = 0.04
    initial_repair_cost: float = 0.04
    cost_ramp_generations: int = 0
    initial_repair_mutation_sigma: float = 0.05
    final_repair_mutation_sigma: float = 0.05
    variation_pulse_generations: int = 0
    virtual_lineages: int = 4
    tail_size: int = 2

    @property
    def has_repair(self) -> bool:
        return self.legacy_arm == "mh_global_zero_rho90"

    @property
    def zero_start(self) -> bool:
        return self.has_repair and self.initial_repair == 0.0

    def repair_cost(self, generation: int) -> float:
        if self.cost_ramp_generations <= 0:
            return self.final_repair_cost
        fraction = min(max(generation, 0) / self.cost_ramp_generations, 1.0)
        return self.initial_repair_cost + fraction * (
            self.final_repair_cost - self.initial_repair_cost
        )

    def repair_mutation_sigma(self, generation: int) -> float:
        if self.variation_pulse_generations and generation <= self.variation_pulse_generations:
            return self.initial_repair_mutation_sigma
        return self.final_repair_mutation_sigma

    def validate(self, generations: int) -> None:
        if self.name not in ROUTE_NAMES:
            raise ValueError("unknown repair-ratchet route")
        expected_arm = "mh_single_rho90" if self.name == "ordinary_mh" else "mh_global_zero_rho90"
        if self.legacy_arm != expected_arm:
            raise ValueError("repair-ratchet route has the wrong frozen Wagner arm")
        if not 0.0 <= self.initial_repair <= 0.9:
            raise ValueError("initial repair must lie in [0, 0.9]")
        if self.has_repair:
            if min(self.final_repair_cost, self.initial_repair_mutation_sigma, self.final_repair_mutation_sigma) <= 0.0:
                raise ValueError("repair cost and variation must be positive")
            if self.initial_repair_cost < 0.0:
                raise ValueError("initial repair cost cannot be negative")
        if not 0 <= self.cost_ramp_generations <= generations:
            raise ValueError("invalid repair-cost ramp")
        if not 0 <= self.variation_pulse_generations <= generations:
            raise ValueError("invalid repair-variation pulse")
        if self.virtual_lineages not in {4, 8} or self.tail_size != 2:
            raise ValueError("repair-ratchet descendant challenge changed")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RepairRoute":
        return cls(**value)


def repair_routes() -> tuple[RepairRoute, ...]:
    return (
        RepairRoute("ordinary_mh", "mh_single_rho90", "ordinary_control", 0.0),
        RepairRoute("repair_zero_standard", "mh_global_zero_rho90", "standard_zero_start", 0.0),
        RepairRoute(
            "repair_zero_lowcost",
            "mh_global_zero_rho90",
            "cost_barrier_diagnostic",
            0.0,
            final_repair_cost=0.01,
            initial_repair_cost=0.01,
        ),
        RepairRoute(
            "repair_zero_cost_ramp",
            "mh_global_zero_rho90",
            "cost_ratchet_diagnostic",
            0.0,
            initial_repair_cost=0.0,
            cost_ramp_generations=20,
        ),
        RepairRoute(
            "repair_zero_variation_pulse",
            "mh_global_zero_rho90",
            "search_access_diagnostic",
            0.0,
            initial_repair_mutation_sigma=0.10,
            variation_pulse_generations=20,
        ),
        RepairRoute(
            "repair_zero_tail8",
            "mh_global_zero_rho90",
            "rare_damage_diagnostic",
            0.0,
            virtual_lineages=8,
        ),
        RepairRoute("repair_prime005", "mh_global_zero_rho90", "threshold_primed", 0.05),
        RepairRoute("repair_seeded080", "mh_global_zero_rho90", "engineered_sufficiency", 0.80),
    )


@dataclass(frozen=True)
class RepairRatchetSpec:
    cohort_id: str
    master_seed: str
    audit_seed: str
    pedigree_seed: str
    confirmation_seed: str
    routes: tuple[RepairRoute, ...] = repair_routes()
    task_count: int = 16
    population_size: int = 16
    generations: int = 40
    elite_count: int = 2
    tournament_size: int = 3
    dose_scales: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
    maximum_workers: int = 4
    bootstrap_repetitions: int = 4096
    interval_level: float = 0.95
    information_advantage_gate: float = 0.08
    distance_four_advantage_gate: float = 0.20
    repair_off_gate: float = 0.15
    dose_slope_gate: float = 0.10
    repair_emergence_gate: float = 0.05
    hard_wall_seconds: int = 28_800
    soft_wall_seconds: int = 27_600
    stage_reservations_seconds: tuple[int, ...] = (19_200, 7_800, 600)
    exploratory: bool = True

    def validate(self) -> None:
        seeds = (self.master_seed, self.audit_seed, self.pedigree_seed, self.confirmation_seed)
        if not self.cohort_id or min(map(len, seeds)) < 32 or len(set(seeds)) != 4:
            raise ValueError("repair-ratchet identities and seeds must be distinct")
        if tuple(route.name for route in self.routes) != ROUTE_NAMES:
            raise ValueError("repair-ratchet routes are frozen and ordered")
        for route in self.routes:
            route.validate(self.generations)
        if self.task_count not in {1, 16}:
            raise ValueError("repair-ratchet task count changed")
        if self.task_count == 16 and (self.population_size, self.generations) != (16, 40):
            raise ValueError("production repair-ratchet dimensions changed")
        if self.task_count == 1 and (self.population_size, self.generations) != (4, 2):
            raise ValueError("smoke repair-ratchet dimensions changed")
        if self.population_size <= self.elite_count or self.maximum_workers != 4:
            raise ValueError("invalid repair-ratchet population or worker boundary")
        if self.dose_scales != (0.0, 0.25, 0.5, 0.75, 1.0):
            raise ValueError("repair-dose assay changed")
        if min(self.bootstrap_repetitions, self.information_advantage_gate, self.repair_off_gate, self.dose_slope_gate) <= 0:
            raise ValueError("repair-ratchet inference gates must be positive")
        if (self.hard_wall_seconds, self.soft_wall_seconds) != (28_800, 27_600):
            raise ValueError("repair-ratchet must retain its eight-hour boundary")
        if sum(self.stage_reservations_seconds) != self.soft_wall_seconds:
            raise ValueError("repair-ratchet stage reservations must cover its soft boundary")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["routes"] = [route.to_dict() for route in self.routes]
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RepairRatchetSpec":
        payload = dict(value)
        payload["routes"] = tuple(RepairRoute.from_dict(item) for item in payload["routes"])
        payload["dose_scales"] = tuple(payload["dose_scales"])
        payload["stage_reservations_seconds"] = tuple(payload["stage_reservations_seconds"])
        result = cls(**payload)
        result.validate()
        return result

    def maintenance(self) -> MaintenanceSpec:
        base = maintenance_spec(smoke=self.task_count == 1)
        result = replace(
            base,
            cohort_id=self.cohort_id + "-assay",
            master_seed=canonical_digest((self.master_seed, "maintenance-kernel")),
            audit_seed=self.audit_seed,
            pedigree_seed=self.pedigree_seed,
            confirmation_seed=self.confirmation_seed,
            bootstrap_repetitions=self.bootstrap_repetitions,
        )
        result.validate()
        return result

    def smoke(self) -> "RepairRatchetSpec":
        result = replace(
            self,
            cohort_id=self.cohort_id + "-smoke",
            master_seed=canonical_digest((self.master_seed, "smoke")),
            audit_seed=canonical_digest((self.audit_seed, "smoke")),
            pedigree_seed=canonical_digest((self.pedigree_seed, "smoke")),
            confirmation_seed=canonical_digest((self.confirmation_seed, "smoke")),
            task_count=1,
            population_size=4,
            generations=2,
            elite_count=1,
            bootstrap_repetitions=64,
            routes=tuple(
                replace(
                    route,
                    cost_ramp_generations=min(route.cost_ramp_generations, 1),
                    variation_pulse_generations=min(route.variation_pulse_generations, 1),
                )
                for route in self.routes
            ),
        )
        result.validate()
        return result


MASTER_SEED = canonical_digest("wagner-ph-global-repair-ratchet-v1-development-2026-09-01")
AUDIT_SEED = canonical_digest("wagner-ph-global-repair-ratchet-v1-audit-2026-09-01")
PEDIGREE_SEED = canonical_digest("wagner-ph-global-repair-ratchet-v1-pedigree-2026-09-01")
CONFIRMATION_SEED = canonical_digest("wagner-ph-global-repair-ratchet-v1-confirmation-2026-09-01")


def repair_ratchet_spec(*, smoke: bool = False) -> RepairRatchetSpec:
    result = RepairRatchetSpec(
        cohort_id="wagner-ph-global-repair-ratchet-v1",
        master_seed=MASTER_SEED,
        audit_seed=AUDIT_SEED,
        pedigree_seed=PEDIGREE_SEED,
        confirmation_seed=CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result


__all__ = (
    "RATCHET_FORMAT",
    "ROUTE_NAMES",
    "RepairRatchetSpec",
    "RepairRoute",
    "repair_ratchet_spec",
    "repair_routes",
)
