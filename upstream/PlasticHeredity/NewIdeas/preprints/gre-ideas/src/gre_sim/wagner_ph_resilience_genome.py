"""Interpreter genotypes and mutation kernels for Resilience v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .artifacts import canonical_digest
from .wagner import WagnerRulebook, mutate_wagner, recombine_wagner
from .wagner_ph_cooption_config import QuantizedCarrierGenome
from .wagner_ph_cooption_evolution import (
    deserialize_genotype as deserialize_base_genotype,
    mutate_carrier,
    serialize_genotype as serialize_base_genotype,
)
from .wagner_ph_resilience_config import ResilienceSpec, arm_settings


@dataclass(frozen=True)
class InterpreterGenome:
    """One or three inherited Wagner matrices plus optional repair strength."""

    copies: tuple[WagnerRulebook, ...]
    architecture: str
    repair_strength: float = 0.0

    def __post_init__(self) -> None:
        if self.architecture not in {"single", "repair", "triplicate"}:
            raise ValueError("unknown interpreter architecture")
        expected = 3 if self.architecture == "triplicate" else 1
        if len(self.copies) != expected:
            raise ValueError("interpreter copy count does not match architecture")
        shapes = {value.weights.shape for value in self.copies}
        if len(shapes) != 1:
            raise ValueError("interpreter copies must share dimensions")
        if self.architecture != "repair" and self.repair_strength != 0.0:
            raise ValueError("repair strength belongs only to repair architectures")
        if not 0.0 <= self.repair_strength <= 0.9:
            raise ValueError("repair strength must lie in [0, 0.9]")

    def effective_rulebook(self) -> WagnerRulebook:
        first = self.copies[0]
        if len(self.copies) == 1:
            return first
        weights = np.mean(np.stack([value.weights for value in self.copies]), axis=0)
        return WagnerRulebook(weights, first.bias, first.order)


Genome = tuple[InterpreterGenome, QuantizedCarrierGenome]


def initialize_interpreter(
    rulebook: WagnerRulebook,
    architecture: str,
    repair_strength: float = 0.0,
) -> InterpreterGenome:
    copies = (rulebook, rulebook, rulebook) if architecture == "triplicate" else (rulebook,)
    return InterpreterGenome(copies, architecture, repair_strength if architecture == "repair" else 0.0)


def serialize_interpreter(value: InterpreterGenome) -> dict[str, Any]:
    return {
        "architecture": value.architecture,
        "repair_strength": value.repair_strength,
        "copies": [copy.to_dict() for copy in value.copies],
        "effective_rulebook": value.effective_rulebook().to_dict(),
    }


def deserialize_interpreter(value: dict[str, Any]) -> InterpreterGenome:
    result = InterpreterGenome(
        tuple(WagnerRulebook.from_dict(copy) for copy in value["copies"]),
        str(value["architecture"]),
        float(value.get("repair_strength", 0.0)),
    )
    archived = value.get("effective_rulebook")
    if archived is not None and archived["uid"] != result.effective_rulebook().uid:
        raise ValueError("archived effective interpreter differs from its copies")
    return result


def serialize_genome(genome: Genome) -> dict[str, Any]:
    interpreter, carrier = genome
    effective = serialize_base_genotype(interpreter.effective_rulebook(), carrier)
    return {
        "interpreter": serialize_interpreter(interpreter),
        "carrier": effective["carrier"],
        "effective_genotype": effective,
        "genotype_id": genome_id(genome),
    }


def deserialize_genome(value: dict[str, Any]) -> Genome:
    interpreter = deserialize_interpreter(value["interpreter"])
    archived_effective = value.get("effective_genotype")
    if archived_effective is None:
        raise ValueError("resilience genotype lacks its effective base genotype")
    effective_rulebook, carrier = deserialize_base_genotype(archived_effective)
    if effective_rulebook.uid != interpreter.effective_rulebook().uid:
        raise ValueError("effective base genotype differs from interpreter copies")
    result = interpreter, carrier
    archived = value.get("genotype_id")
    if archived is not None and archived != genome_id(result):
        raise ValueError("resilience genotype id mismatch")
    return result


def genome_id(genome: Genome) -> str:
    interpreter, carrier = genome
    payload = {
        "architecture": interpreter.architecture,
        "repair_strength": interpreter.repair_strength,
        "copies": [copy.uid for copy in interpreter.copies],
        "carrier": carrier.to_dict(),
    }
    return canonical_digest(payload)[:24]


def effective_genotype(genome: Genome) -> tuple[WagnerRulebook, QuantizedCarrierGenome]:
    return genome[0].effective_rulebook(), genome[1]


def architecture_cost(interpreter: InterpreterGenome, spec: ResilienceSpec) -> float:
    if interpreter.architecture == "repair":
        return spec.repair_cost * interpreter.repair_strength
    if interpreter.architecture == "triplicate":
        return spec.triplicate_cost
    return 0.0


def _mutate_repaired(
    rulebook: WagnerRulebook,
    random: np.random.Generator,
    repair_strength: float,
) -> WagnerRulebook:
    weights = rulebook.weights.copy()
    mask = random.random(weights.shape) < 1.0 / weights.size
    targets = random.normal(0.0, 1.0, size=int(mask.sum()))
    weights[mask] += (1.0 - repair_strength) * (targets - weights[mask])
    return WagnerRulebook(weights, rulebook.bias, rulebook.order)


def _mutate_triplicate_concerted(
    copies: tuple[WagnerRulebook, ...], random: np.random.Generator
) -> tuple[WagnerRulebook, ...]:
    first = copies[0]
    mask = random.random(first.weights.shape) < 1.0 / first.weights.size
    targets = random.normal(0.0, 1.0, size=int(mask.sum()))
    result: list[WagnerRulebook] = []
    for copy in copies:
        weights = copy.weights.copy()
        weights[mask] = targets
        result.append(WagnerRulebook(weights, copy.bias, copy.order))
    return tuple(result)


def mutate_genome(
    left: Genome,
    right: Genome,
    arm: str,
    random: np.random.Generator,
    spec: ResilienceSpec,
    *,
    mechanism_off: bool = False,
) -> Genome:
    settings = arm_settings(arm)
    architecture = settings["architecture"]
    if left[0].architecture != architecture or right[0].architecture != architecture:
        raise ValueError("arm and parent interpreter architecture differ")
    recombined = tuple(
        recombine_wagner(left[0].copies[index], right[0].copies[index], random)
        for index in range(len(left[0].copies))
    )
    if architecture == "repair":
        inherited = 0.5 * (left[0].repair_strength + right[0].repair_strength)
        used = 0.0 if mechanism_off else inherited
        copies = (_mutate_repaired(recombined[0], random, used),)
        repair = float(np.clip(inherited + random.normal(0.0, spec.repair_mutation_sigma), 0.0, spec.repair_maximum))
    elif architecture == "triplicate":
        copies = (
            _mutate_triplicate_concerted(recombined, random)
            if mechanism_off
            else tuple(mutate_wagner(copy, random) for copy in recombined)
        )
        repair = 0.0
    else:
        copies = (mutate_wagner(recombined[0], random),)
        repair = 0.0
    interpreter = InterpreterGenome(tuple(copies), architecture, repair)
    carrier = mutate_carrier(left[1], right[1], "independent", random)
    return interpreter, carrier


def diagnostic_mutation(
    genome: Genome,
    condition: str,
    random: np.random.Generator,
    spec: ResilienceSpec,
) -> Genome:
    interpreter, carrier = genome
    if condition == "ordinary_reset":
        arm = "lineage4_reset"
        base = initialize_interpreter(interpreter.effective_rulebook(), "single")
        return mutate_genome((base, carrier), (base, carrier), arm, random, spec)
    if condition.startswith("repair_"):
        strength = int(condition.removeprefix("repair_")) / 10.0
        base = initialize_interpreter(interpreter.effective_rulebook(), "repair", strength)
        child = mutate_genome((base, carrier), (base, carrier), "lineage4_repair", random, spec)
        return InterpreterGenome(child[0].copies, "repair", strength), child[1]
    if condition in {"triplicate_independent", "triplicate_concerted"}:
        base = initialize_interpreter(interpreter.effective_rulebook(), "triplicate")
        return mutate_genome(
            (base, carrier), (base, carrier), "lineage4_triplicate", random, spec,
            mechanism_off=condition == "triplicate_concerted",
        )
    raise ValueError(f"unknown diagnostic condition: {condition}")


def mutation_delta(parent: Genome, child: Genome) -> dict[str, Any]:
    left, right = parent[0], child[0]
    effective_left = left.effective_rulebook().weights
    effective_right = right.effective_rulebook().weights
    changed = np.argwhere(effective_left != effective_right)
    copy_changes = [
        np.argwhere(a.weights != b.weights).tolist()
        for a, b in zip(left.copies, right.copies)
    ]
    return {
        "architecture": right.architecture,
        "changed_effective_weight_indices": changed.tolist(),
        "changed_copy_weight_indices": copy_changes,
        "effective_weight_l2": float(np.linalg.norm(effective_right - effective_left)),
        "repair_strength_before": left.repair_strength,
        "repair_strength_after": right.repair_strength,
        "carrier_changed": parent[1].to_dict() != child[1].to_dict(),
    }


__all__ = (
    "Genome",
    "InterpreterGenome",
    "architecture_cost",
    "deserialize_genome",
    "diagnostic_mutation",
    "effective_genotype",
    "genome_id",
    "initialize_interpreter",
    "mutate_genome",
    "mutation_delta",
    "serialize_genome",
)
