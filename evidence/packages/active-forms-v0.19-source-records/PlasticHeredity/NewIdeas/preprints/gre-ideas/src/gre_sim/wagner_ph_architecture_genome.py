"""Interpreter genomes and mutation kernels for Architecture v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .artifacts import canonical_digest
from .wagner import WagnerRulebook, mutate_wagner, recombine_wagner
from .wagner_ph_architecture_config import ArchitectureSpec, arm_settings
from .wagner_ph_cooption_config import QuantizedCarrierGenome
from .wagner_ph_cooption_evolution import (
    deserialize_genotype as deserialize_base_genotype,
    mutate_carrier,
    serialize_genotype as serialize_base_genotype,
)
from .wagner_ph_resilience_genome import deserialize_genome as deserialize_resilience_genome


@dataclass(frozen=True)
class ArchitectureInterpreter:
    """One Wagner matrix or three matrices with a frozen decoder rule."""

    copies: tuple[WagnerRulebook, ...]
    architecture: str
    repair_strength: float = 0.0

    def __post_init__(self) -> None:
        if self.architecture not in {"single", "repair", "mean3", "median3"}:
            raise ValueError("unknown architecture interpreter")
        expected = 3 if self.architecture in {"mean3", "median3"} else 1
        if len(self.copies) != expected:
            raise ValueError("interpreter copy count does not match architecture")
        if len({value.weights.shape for value in self.copies}) != 1:
            raise ValueError("interpreter copies must share dimensions")
        if self.architecture != "repair" and self.repair_strength != 0.0:
            raise ValueError("repair strength belongs only to repair interpreters")
        if not 0.0 <= self.repair_strength <= 0.9:
            raise ValueError("repair strength must lie in [0, 0.9]")

    def effective_rulebook(self) -> WagnerRulebook:
        first = self.copies[0]
        if len(self.copies) == 1:
            return first
        stacked = np.stack([value.weights for value in self.copies])
        weights = np.median(stacked, axis=0) if self.architecture == "median3" else np.mean(stacked, axis=0)
        return WagnerRulebook(weights, first.bias, first.order)


Genome = tuple[ArchitectureInterpreter, QuantizedCarrierGenome]


def initialize_interpreter(
    rulebook: WagnerRulebook,
    architecture: str,
    repair_strength: float = 0.0,
) -> ArchitectureInterpreter:
    copies = (rulebook, rulebook, rulebook) if architecture in {"mean3", "median3"} else (rulebook,)
    return ArchitectureInterpreter(copies, architecture, repair_strength if architecture == "repair" else 0.0)


def convert_interpreter(value: ArchitectureInterpreter, architecture: str) -> ArchitectureInterpreter:
    if architecture in {"mean3", "median3"} and len(value.copies) == 3:
        return ArchitectureInterpreter(value.copies, architecture)
    return initialize_interpreter(value.effective_rulebook(), architecture, value.repair_strength)


def architecture_cost(value: ArchitectureInterpreter, spec: ArchitectureSpec) -> float:
    if value.architecture == "repair":
        return spec.repair_cost * value.repair_strength
    if value.architecture in {"mean3", "median3"}:
        return spec.redundancy_cost
    return 0.0


def serialize_interpreter(value: ArchitectureInterpreter) -> dict[str, Any]:
    return {
        "architecture": value.architecture,
        "repair_strength": value.repair_strength,
        "copies": [copy.to_dict() for copy in value.copies],
        "effective_rulebook": value.effective_rulebook().to_dict(),
    }


def deserialize_interpreter(value: dict[str, Any]) -> ArchitectureInterpreter:
    result = ArchitectureInterpreter(
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
    effective, carrier = deserialize_base_genotype(value["effective_genotype"])
    if effective.uid != interpreter.effective_rulebook().uid:
        raise ValueError("effective genotype differs from architecture interpreter")
    result = interpreter, carrier
    if value.get("genotype_id") not in {None, genome_id(result)}:
        raise ValueError("architecture genome id mismatch")
    return result


def genome_id(genome: Genome) -> str:
    interpreter, carrier = genome
    return canonical_digest({
        "architecture": interpreter.architecture,
        "repair_strength": interpreter.repair_strength,
        "copies": [copy.uid for copy in interpreter.copies],
        "carrier": carrier.to_dict(),
    })[:24]


def effective_genotype(genome: Genome) -> tuple[WagnerRulebook, QuantizedCarrierGenome]:
    return genome[0].effective_rulebook(), genome[1]


def initialize_from_source(value: dict[str, Any], architecture: str) -> Genome:
    """Fork a Resilience population member or ordinary burn-in genotype."""

    if "interpreter" in value:
        old_interpreter, carrier = deserialize_resilience_genome(value)
        repair = old_interpreter.repair_strength if architecture == "repair" else 0.0
        return initialize_interpreter(old_interpreter.effective_rulebook(), architecture, repair), carrier
    rulebook, carrier = deserialize_base_genotype(value)
    return initialize_interpreter(rulebook, architecture), carrier


def _mutate_rulebook(
    rulebook: WagnerRulebook,
    random: np.random.Generator,
    repair_strength: float = 0.0,
    forced_edge: int | None = None,
) -> WagnerRulebook:
    if forced_edge is None and repair_strength == 0.0:
        return mutate_wagner(rulebook, random)
    weights = rulebook.weights.copy()
    if forced_edge is None:
        mask = random.random(weights.shape) < 1.0 / weights.size
        indices = np.argwhere(mask)
    else:
        if not 0 <= forced_edge < weights.size:
            raise ValueError("forced edge lies outside the regulatory matrix")
        indices = np.asarray([divmod(int(forced_edge), weights.shape[1])], dtype=int)
    targets = random.normal(0.0, 1.0, size=len(indices))
    for (row, column), target in zip(indices, targets):
        old = weights[row, column]
        weights[row, column] = old + (1.0 - repair_strength) * (target - old)
    return WagnerRulebook(weights, rulebook.bias, rulebook.order)


def _concerted_mutation(
    copies: tuple[WagnerRulebook, ...],
    random: np.random.Generator,
    forced_edge: int | None = None,
) -> tuple[WagnerRulebook, ...]:
    first = copies[0]
    if forced_edge is None:
        mask = random.random(first.weights.shape) < 1.0 / first.weights.size
        indices = np.argwhere(mask)
    else:
        indices = np.asarray([divmod(int(forced_edge), first.genes)], dtype=int)
    targets = random.normal(0.0, 1.0, size=len(indices))
    result = []
    for copy in copies:
        weights = copy.weights.copy()
        for (row, column), target in zip(indices, targets):
            weights[row, column] = target
        result.append(WagnerRulebook(weights, copy.bias, copy.order))
    return tuple(result)


def mutate_genome(
    left: Genome,
    right: Genome,
    arm: str,
    random: np.random.Generator,
    spec: ArchitectureSpec,
    *,
    forced_edge: int | None = None,
    mechanism: str = "natural",
) -> Genome:
    settings = arm_settings(arm)
    architecture = settings["architecture"]
    allowed_mechanisms = {
        "single": {"natural"},
        "repair": {"natural", "repair_off"},
        "mean3": {"natural", "concerted"},
        "median3": {"natural", "concerted"},
    }
    if mechanism not in allowed_mechanisms[architecture]:
        raise ValueError(
            f"mechanism {mechanism!r} is invalid for {architecture!r} interpreters"
        )
    if left[0].architecture != architecture or right[0].architecture != architecture:
        raise ValueError("arm and parent architecture differ")
    recombined = tuple(
        recombine_wagner(left[0].copies[index], right[0].copies[index], random)
        for index in range(len(left[0].copies))
    )
    if architecture == "repair":
        inherited = 0.5 * (left[0].repair_strength + right[0].repair_strength)
        used = 0.0 if mechanism == "repair_off" else inherited
        copies = (_mutate_rulebook(recombined[0], random, used, forced_edge),)
        repair = float(np.clip(inherited + random.normal(0.0, spec.repair_mutation_sigma), 0.0, spec.repair_maximum))
    elif architecture in {"mean3", "median3"}:
        copies = (
            _concerted_mutation(recombined, random, forced_edge)
            if mechanism == "concerted"
            else tuple(_mutate_rulebook(copy, random, forced_edge=forced_edge) for copy in recombined)
        )
        repair = 0.0
    else:
        copies = (_mutate_rulebook(recombined[0], random, forced_edge=forced_edge),)
        repair = 0.0
    return (
        ArchitectureInterpreter(copies, architecture, repair),
        mutate_carrier(left[1], right[1], "independent", random),
    )


def mutation_delta(parent: Genome, child: Genome) -> dict[str, Any]:
    effective_left = parent[0].effective_rulebook().weights
    effective_right = child[0].effective_rulebook().weights
    return {
        "architecture_before": parent[0].architecture,
        "architecture_after": child[0].architecture,
        "changed_effective_weight_indices": np.argwhere(effective_left != effective_right).tolist(),
        "changed_copy_weight_indices": [
            np.argwhere(a.weights != b.weights).tolist()
            for a, b in zip(parent[0].copies, child[0].copies)
        ],
        "effective_weight_l2": float(np.linalg.norm(effective_right - effective_left)),
        "repair_strength_before": parent[0].repair_strength,
        "repair_strength_after": child[0].repair_strength,
        "carrier_changed": parent[1].to_dict() != child[1].to_dict(),
    }


__all__ = (
    "ArchitectureInterpreter",
    "Genome",
    "architecture_cost",
    "convert_interpreter",
    "deserialize_genome",
    "effective_genotype",
    "genome_id",
    "initialize_from_source",
    "initialize_interpreter",
    "mutate_genome",
    "mutation_delta",
    "serialize_genome",
)
