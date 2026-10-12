"""Mutation and component-swap mechanisms for the robustness experiment."""

from __future__ import annotations

from typing import Any

import numpy as np

from .wagner import WagnerRulebook, mutate_wagner, recombine_wagner
from .wagner_ph_cooption_config import CAPACITY_STEPS, PRECISION_STEPS, QuantizedCarrierGenome
from .wagner_ph_cooption_evolution import (
    _carrier_payload,
    _mutate_strength,
    _named_carrier,
    constrain_carrier,
    mutate_genotype,
    serialize_genotype,
)
from .wagner_ph_robustness_config import AUTOPSY_COMPONENTS, arm_settings


Genotype = tuple[WagnerRulebook, QuantizedCarrierGenome]


def _protected_carrier(
    left: QuantizedCarrierGenome,
    right: QuantizedCarrierGenome,
    architecture: str,
    random: np.random.Generator,
    multiplier: float,
) -> QuantizedCarrierGenome:
    """Existing carrier operator with every mutation probability scaled uniformly."""

    if architecture not in {"independent", "linked"}:
        raise ValueError(f"unknown robustness mutation architecture: {architecture}")
    if not 0.0 <= multiplier <= 1.0:
        raise ValueError("carrier mutation multiplier must lie in [0, 1]")
    payload: dict[str, Any] = {}
    for field in ("decay", "hysteresis", "topology", "k", "bits_per_mark"):
        payload[field] = getattr(left if random.random() < 0.5 else right, field)
    if architecture == "independent":
        payload["write_rate"] = getattr(left if random.random() < 0.5 else right, "write_rate")
        payload["coupling"] = getattr(left if random.random() < 0.5 else right, "coupling")
        if random.random() < 0.35 * multiplier:
            payload["write_rate"] = _mutate_strength(float(payload["write_rate"]), random)
        if random.random() < 0.35 * multiplier:
            payload["coupling"] = _mutate_strength(float(payload["coupling"]), random)
    else:
        parent = left if random.random() < 0.5 else right
        latent = 0.5 * (parent.write_rate + parent.coupling)
        if random.random() < 0.35 * multiplier:
            latent = _mutate_strength(float(latent), random)
        payload["write_rate"] = latent
        payload["coupling"] = latent
    if random.random() < 0.35 * multiplier:
        payload["decay"] = float(
            np.clip(float(payload["decay"]) + random.normal(0.0, 0.02), 0.0, 0.20)
        )
    if random.random() < 0.20 * multiplier:
        payload["hysteresis"] = int(
            np.clip(int(payload["hysteresis"]) + int(random.integers(-1, 2)), 1, 3)
        )
    if random.random() < 0.20 * multiplier:
        payload["k"] = CAPACITY_STEPS[int(random.integers(len(CAPACITY_STEPS)))]
    if random.random() < 0.15 * multiplier:
        payload["bits_per_mark"] = PRECISION_STEPS[
            int(random.integers(len(PRECISION_STEPS)))
        ]
    if random.random() < 0.15 * multiplier:
        topologies = ("all", "outgoing", "self_feedback")
        payload["topology"] = topologies[int(random.integers(len(topologies)))]
    if payload["topology"] == "all":
        payload["k"] = 10
    return _named_carrier(payload)


def mutate_for_arm(
    left: Genotype,
    right: Genotype,
    arm: str,
    random: np.random.Generator,
) -> Genotype:
    settings = arm_settings(arm)
    multiplier = float(settings["carrier_mutation_multiplier"])
    architecture = str(settings["mutation_architecture"])
    if multiplier == 1.0:
        rulebook, carrier = mutate_genotype(left, right, architecture, random)
    else:
        rulebook = mutate_wagner(recombine_wagner(left[0], right[0], random), random)
        carrier = _protected_carrier(left[1], right[1], architecture, random, multiplier)
    return rulebook, constrain_carrier(carrier, settings["carrier_constraint"])


def initialize_for_arm(genotype: Genotype, arm: str) -> Genotype:
    """Place the same sealed genotype inside one arm's prospective architecture."""

    rulebook, carrier = genotype
    settings = arm_settings(arm)
    if settings["mutation_architecture"] == "linked":
        payload = _carrier_payload(carrier)
        latent = 0.5 * (carrier.write_rate + carrier.coupling)
        payload.update(write_rate=latent, coupling=latent)
        carrier = _named_carrier(payload)
    carrier = constrain_carrier(carrier, settings["carrier_constraint"])
    return rulebook, carrier


def hybrid_genotype(parent: Genotype, descendant: Genotype, mask: int) -> Genotype:
    """Construct one of all 2^4 parent/descendant component combinations."""

    if not 0 <= mask < 1 << len(AUTOPSY_COMPONENTS):
        raise ValueError("autopsy hybrid mask must lie in [0, 15]")
    if mask == 0:
        return parent
    if mask == (1 << len(AUTOPSY_COMPONENTS)) - 1:
        return descendant
    parent_rulebook, parent_carrier = parent
    descendant_rulebook, descendant_carrier = descendant
    rulebook = descendant_rulebook if mask & 1 else parent_rulebook
    payload = _carrier_payload(parent_carrier)
    if mask & 2:
        payload.update(
            write_rate=descendant_carrier.write_rate,
            coupling=descendant_carrier.coupling,
        )
    if mask & 4:
        payload.update(
            topology=descendant_carrier.topology,
            k=descendant_carrier.k,
            bits_per_mark=descendant_carrier.bits_per_mark,
        )
    if mask & 8:
        payload.update(
            decay=descendant_carrier.decay,
            hysteresis=descendant_carrier.hysteresis,
        )
    return rulebook, _named_carrier(payload)


def mutation_delta(parent: Genotype, descendant: Genotype) -> dict[str, Any]:
    parent_rulebook, parent_carrier = parent
    descendant_rulebook, descendant_carrier = descendant
    changed = np.argwhere(parent_rulebook.weights != descendant_rulebook.weights)
    carrier_fields = {
        field: {
            "parent": getattr(parent_carrier, field),
            "descendant": getattr(descendant_carrier, field),
            "changed": getattr(parent_carrier, field) != getattr(descendant_carrier, field),
        }
        for field in (
            "write_rate",
            "coupling",
            "topology",
            "k",
            "bits_per_mark",
            "decay",
            "hysteresis",
        )
    }
    return {
        "changed_weight_count": int(len(changed)),
        "changed_weight_indices": changed.tolist(),
        "carrier_fields": carrier_fields,
        "component_changed": {
            "grn_weights": bool(len(changed)),
            "writer_reader_strengths": carrier_fields["write_rate"]["changed"]
            or carrier_fields["coupling"]["changed"],
            "storage_layout": any(
                carrier_fields[field]["changed"]
                for field in ("topology", "k", "bits_per_mark")
            ),
            "copy_dynamics": carrier_fields["decay"]["changed"]
            or carrier_fields["hysteresis"]["changed"],
        },
        "parent": serialize_genotype(*parent),
        "descendant": serialize_genotype(*descendant),
    }
