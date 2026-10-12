"""Interpreter genomes and mutation kernels for Adaptive Maintenance v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .artifacts import canonical_digest
from .wagner import WagnerRulebook, recombine_wagner
from .wagner_ph_cooption_config import QuantizedCarrierGenome
from .wagner_ph_cooption_evolution import (
    deserialize_genotype as deserialize_base_genotype,
    mutate_carrier,
    serialize_genotype as serialize_base_genotype,
)
from .wagner_ph_maintenance_config import MaintenanceSpec, arm_settings


@dataclass(frozen=True)
class MaintenanceInterpreter:
    """A Wagner interpreter with optional attenuation or copy redundancy."""

    copies: tuple[WagnerRulebook, ...]
    architecture: str
    global_repair: float = 0.0
    node_repair: tuple[float, ...] = ()
    decoder: str = "mean"

    def __post_init__(self) -> None:
        allowed = {"single", "global_repair", "node_repair", "duplication", "median3"}
        if self.architecture not in allowed:
            raise ValueError("unknown maintenance interpreter architecture")
        if not 1 <= len(self.copies) <= 3 or len({copy.weights.shape for copy in self.copies}) != 1:
            raise ValueError("maintenance copies must contain one to three equal shapes")
        if self.architecture in {"single", "global_repair", "node_repair"} and len(self.copies) != 1:
            raise ValueError("single and repair interpreters require exactly one copy")
        if self.architecture == "median3" and len(self.copies) != 3:
            raise ValueError("median3 requires three copies")
        if self.architecture != "global_repair" and self.global_repair != 0.0:
            raise ValueError("global repair belongs only to global-repair interpreters")
        if not 0.0 <= self.global_repair <= 0.9:
            raise ValueError("global repair must lie in [0, 0.9]")
        genes = self.copies[0].genes
        if self.architecture == "node_repair":
            if len(self.node_repair) != genes or any(not 0.0 <= value <= 0.9 for value in self.node_repair):
                raise ValueError("node repair must contain one bounded value per target gene")
        elif self.node_repair:
            raise ValueError("node repair belongs only to node-repair interpreters")
        if self.decoder not in {"mean", "median"}:
            raise ValueError("unknown maintenance decoder")
        if self.decoder == "median" and len(self.copies) != 3:
            raise ValueError("median decoding requires exactly three copies")
        if self.architecture == "median3" and self.decoder not in {"mean", "median"}:
            raise ValueError("invalid median3 decoder")

    @property
    def copy_count(self) -> int:
        return len(self.copies)

    @property
    def mean_repair(self) -> float:
        if self.architecture == "global_repair":
            return self.global_repair
        if self.architecture == "node_repair":
            return float(np.mean(self.node_repair))
        return 0.0

    def effective_rulebook(self) -> WagnerRulebook:
        first = self.copies[0]
        if len(self.copies) == 1:
            return first
        stacked = np.stack([copy.weights for copy in self.copies])
        weights = np.median(stacked, axis=0) if self.decoder == "median" else np.mean(stacked, axis=0)
        return WagnerRulebook(weights, first.bias, first.order)


Genome = tuple[MaintenanceInterpreter, QuantizedCarrierGenome]


def initialize_interpreter(
    rulebook: WagnerRulebook,
    architecture: str,
    spec: MaintenanceSpec,
    *,
    seeded: bool = False,
) -> MaintenanceInterpreter:
    if architecture == "global_repair":
        return MaintenanceInterpreter(
            (rulebook,), architecture, spec.seeded_repair_strength if seeded else 0.0
        )
    if architecture == "node_repair":
        return MaintenanceInterpreter(
            (rulebook,), architecture, node_repair=(0.0,) * rulebook.genes
        )
    if architecture == "median3":
        return MaintenanceInterpreter((rulebook, rulebook, rulebook), architecture, decoder="median")
    return MaintenanceInterpreter((rulebook,), architecture)


def initialize_from_source(value: dict[str, Any], arm: str, spec: MaintenanceSpec) -> Genome:
    rulebook, carrier = deserialize_base_genotype(value)
    settings = arm_settings(arm)
    interpreter = initialize_interpreter(
        rulebook,
        str(settings["architecture"]),
        spec,
        seeded=settings["initialization"] == "seeded",
    )
    return interpreter, carrier


def architecture_cost(interpreter: MaintenanceInterpreter, spec: MaintenanceSpec) -> float:
    if interpreter.architecture in {"global_repair", "node_repair"}:
        return spec.repair_cost * interpreter.mean_repair
    if interpreter.architecture in {"duplication", "median3"}:
        return spec.extra_copy_cost * (interpreter.copy_count - 1)
    return 0.0


def serialize_interpreter(value: MaintenanceInterpreter) -> dict[str, Any]:
    return {
        "architecture": value.architecture,
        "global_repair": value.global_repair,
        "node_repair": list(value.node_repair),
        "decoder": value.decoder,
        "copy_count": value.copy_count,
        "copies": [copy.to_dict() for copy in value.copies],
        "effective_rulebook": value.effective_rulebook().to_dict(),
    }


def deserialize_interpreter(value: dict[str, Any]) -> MaintenanceInterpreter:
    result = MaintenanceInterpreter(
        tuple(WagnerRulebook.from_dict(copy) for copy in value["copies"]),
        str(value["architecture"]),
        float(value.get("global_repair", 0.0)),
        tuple(float(item) for item in value.get("node_repair", ())),
        str(value.get("decoder", "mean")),
    )
    archived = value.get("effective_rulebook")
    if archived is not None and archived["uid"] != result.effective_rulebook().uid:
        raise ValueError("archived effective interpreter differs from its copies")
    if value.get("copy_count") not in {None, result.copy_count}:
        raise ValueError("archived maintenance copy count differs")
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
        raise ValueError("effective genotype differs from maintenance interpreter")
    result = interpreter, carrier
    if value.get("genotype_id") not in {None, genome_id(result)}:
        raise ValueError("maintenance genotype id mismatch")
    return result


def genome_id(genome: Genome) -> str:
    interpreter, carrier = genome
    return canonical_digest(
        {
            "architecture": interpreter.architecture,
            "global_repair": interpreter.global_repair,
            "node_repair": list(interpreter.node_repair),
            "decoder": interpreter.decoder,
            "copies": [copy.uid for copy in interpreter.copies],
            "carrier": carrier.to_dict(),
        }
    )[:24]


def effective_genotype(genome: Genome) -> tuple[WagnerRulebook, QuantizedCarrierGenome]:
    return genome[0].effective_rulebook(), genome[1]


def _mutation_draws(rulebook: WagnerRulebook, random: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    mask = random.random(rulebook.weights.shape) < 1.0 / rulebook.weights.size
    indices = np.argwhere(mask)
    targets = random.normal(0.0, 1.0, size=len(indices))
    return indices, targets


def _apply_mutation(
    rulebook: WagnerRulebook,
    indices: np.ndarray,
    targets: np.ndarray,
    repair_by_target: np.ndarray,
) -> WagnerRulebook:
    weights = rulebook.weights.copy()
    for (row, column), target in zip(indices, targets):
        attenuation = float(repair_by_target[int(row)])
        old = weights[row, column]
        weights[row, column] = old + (1.0 - attenuation) * (target - old)
    return WagnerRulebook(weights, rulebook.bias, rulebook.order)


def _mutate_copy(
    rulebook: WagnerRulebook,
    random: np.random.Generator,
    repair_by_target: np.ndarray,
) -> WagnerRulebook:
    return _apply_mutation(rulebook, *_mutation_draws(rulebook, random), repair_by_target)


def _mutate_copies(
    copies: tuple[WagnerRulebook, ...],
    random: np.random.Generator,
    *,
    concerted: bool,
) -> tuple[WagnerRulebook, ...]:
    zeros = np.zeros(copies[0].genes, dtype=float)
    if concerted:
        indices, targets = _mutation_draws(copies[0], random)
        return tuple(_apply_mutation(copy, indices, targets, zeros) for copy in copies)
    return tuple(_mutate_copy(copy, random, zeros) for copy in copies)


def _mutate_node_rates(
    inherited: np.ndarray,
    random: np.random.Generator,
    spec: MaintenanceSpec,
) -> tuple[float, ...]:
    mask = random.random(len(inherited)) < 1.0 / len(inherited)
    values = inherited.copy()
    values[mask] += random.normal(0.0, spec.repair_mutation_sigma, size=int(mask.sum()))
    return tuple(float(value) for value in np.clip(values, 0.0, spec.repair_maximum))


def _duplication_recombination(
    left: MaintenanceInterpreter,
    right: MaintenanceInterpreter,
    random: np.random.Generator,
    spec: MaintenanceSpec,
    mechanism: str,
) -> MaintenanceInterpreter:
    template = left if random.random() < 0.5 else right
    count = template.copy_count
    copies = [
        recombine_wagner(
            left.copies[min(index, left.copy_count - 1)],
            right.copies[min(index, right.copy_count - 1)],
            random,
        )
        for index in range(count)
    ]
    if mechanism != "single_copy" and random.random() < spec.copy_number_mutation_probability:
        if len(copies) == 1:
            direction = 1
        elif len(copies) == 3:
            direction = -1
        else:
            direction = 1 if random.random() < 0.5 else -1
        if direction > 0:
            copies.append(copies[int(random.integers(len(copies)))])
        else:
            copies.pop(int(random.integers(len(copies))))
    if mechanism == "single_copy":
        copies = [MaintenanceInterpreter(tuple(copies), "duplication", decoder="mean").effective_rulebook()]
    decoder = template.decoder if len(copies) == 3 else "mean"
    if len(copies) == 3 and random.random() < spec.decoder_mutation_probability:
        decoder = "median" if decoder == "mean" else "mean"
    if mechanism == "mean_decoder":
        decoder = "mean"
    mutated = _mutate_copies(tuple(copies), random, concerted=mechanism == "concerted")
    return MaintenanceInterpreter(mutated, "duplication", decoder=decoder)


def mutate_genome(
    left: Genome,
    right: Genome,
    arm: str,
    random: np.random.Generator,
    spec: MaintenanceSpec,
    *,
    mechanism: str = "natural",
) -> Genome:
    settings = arm_settings(arm)
    architecture = str(settings["architecture"])
    if left[0].architecture != architecture or right[0].architecture != architecture:
        raise ValueError("arm and parent maintenance architecture differ")
    allowed = {
        "single": {"natural"},
        "global_repair": {"natural", "repair_off"},
        "node_repair": {"natural", "repair_off", "uniform_repair", "shuffled_repair"},
        "duplication": {"natural", "concerted", "mean_decoder", "single_copy"},
        "median3": {"natural", "concerted", "mean_decoder"},
    }
    if mechanism not in allowed[architecture]:
        raise ValueError(f"mechanism {mechanism!r} is invalid for {architecture!r}")

    left_interpreter, right_interpreter = left[0], right[0]
    if architecture == "duplication":
        interpreter = _duplication_recombination(
            left_interpreter, right_interpreter, random, spec, mechanism
        )
    else:
        recombined = tuple(
            recombine_wagner(left_interpreter.copies[index], right_interpreter.copies[index], random)
            for index in range(left_interpreter.copy_count)
        )
        if architecture == "global_repair":
            inherited = 0.5 * (left_interpreter.global_repair + right_interpreter.global_repair)
            used = 0.0 if mechanism == "repair_off" else inherited
            repaired = np.full(recombined[0].genes, used, dtype=float)
            copies = (_mutate_copy(recombined[0], random, repaired),)
            evolved = float(
                np.clip(
                    inherited + random.normal(0.0, spec.repair_mutation_sigma),
                    0.0,
                    spec.repair_maximum,
                )
            )
            interpreter = MaintenanceInterpreter(copies, architecture, global_repair=evolved)
        elif architecture == "node_repair":
            inherited = 0.5 * (
                np.asarray(left_interpreter.node_repair)
                + np.asarray(right_interpreter.node_repair)
            )
            permutation = random.permutation(len(inherited))
            if mechanism == "repair_off":
                used = np.zeros_like(inherited)
            elif mechanism == "uniform_repair":
                used = np.full_like(inherited, float(np.mean(inherited)))
            elif mechanism == "shuffled_repair":
                used = inherited[permutation]
            else:
                used = inherited
            copies = (_mutate_copy(recombined[0], random, used),)
            rates = _mutate_node_rates(inherited, random, spec)
            interpreter = MaintenanceInterpreter(copies, architecture, node_repair=rates)
        elif architecture == "median3":
            copies = _mutate_copies(recombined, random, concerted=mechanism == "concerted")
            interpreter = MaintenanceInterpreter(
                copies,
                architecture,
                decoder="mean" if mechanism == "mean_decoder" else "median",
            )
        else:
            copies = (_mutate_copy(recombined[0], random, np.zeros(recombined[0].genes)),)
            interpreter = MaintenanceInterpreter(copies, architecture)
    carrier = mutate_carrier(left[1], right[1], "independent", random)
    return interpreter, carrier


def mutation_delta(parent: Genome, child: Genome) -> dict[str, Any]:
    before, after = parent[0], child[0]
    effective_before = before.effective_rulebook().weights
    effective_after = after.effective_rulebook().weights
    return {
        "architecture": after.architecture,
        "copy_count_before": before.copy_count,
        "copy_count_after": after.copy_count,
        "decoder_before": before.decoder,
        "decoder_after": after.decoder,
        "global_repair_before": before.global_repair,
        "global_repair_after": after.global_repair,
        "node_repair_before": list(before.node_repair),
        "node_repair_after": list(after.node_repair),
        "changed_effective_weight_indices": np.argwhere(effective_before != effective_after).tolist(),
        "effective_weight_l2": float(np.linalg.norm(effective_after - effective_before)),
        "carrier_changed": parent[1].to_dict() != child[1].to_dict(),
    }


__all__ = (
    "Genome",
    "MaintenanceInterpreter",
    "architecture_cost",
    "deserialize_genome",
    "effective_genotype",
    "genome_id",
    "initialize_from_source",
    "initialize_interpreter",
    "mutate_genome",
    "mutation_delta",
    "serialize_genome",
)
