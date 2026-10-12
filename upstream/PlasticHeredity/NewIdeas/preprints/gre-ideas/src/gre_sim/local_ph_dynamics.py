"""Target-blind, same-gene writer/reader mechanics for local plastic heredity."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .endpoints import apply_carryover
from .landscape import int_to_signs
from .local_ph_config import CopyNoiseSpec, LocalCarrierGenome
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import MemoryCycle, apply_mark_bias
from .wagner import WagnerRulebook


@dataclass(frozen=True)
class LocalCarrierState:
    """Inherited carrier values; ordinary expression is deliberately absent."""

    values: tuple[float, ...]


def blank_local(genes: int) -> LocalCarrierState:
    return LocalCarrierState((0.0,) * genes)


def structural_mask(
    rulebook: WagnerRulebook,
    genome: LocalCarrierGenome,
    random_order: tuple[int, ...] | None = None,
) -> tuple[int, ...]:
    """Select writable loci from GRN structure without using A/B outcomes."""

    genome.validate(rulebook.genes)
    if random_order is not None:
        if sorted(random_order) != list(range(rulebook.genes)):
            raise ValueError("random mask order is not a gene permutation")
        return tuple(int(value) for value in random_order[: genome.k])
    outgoing = np.sum(np.abs(rulebook.weights), axis=0)
    if genome.topology == "all":
        scores = outgoing
    elif genome.topology == "outgoing":
        scores = outgoing
    elif genome.topology == "self_feedback":
        scores = np.abs(np.diag(rulebook.weights)) + 1e-9 * outgoing
    else:  # pragma: no cover - protected by validation.
        raise ValueError(genome.topology)
    ranked = sorted(range(rulebook.genes), key=lambda gene: (-float(scores[gene]), gene))
    return tuple(ranked[: genome.k])


def write_local(
    inherited: LocalCarrierState,
    adult_states: tuple[int, ...],
    genome: LocalCarrierGenome,
    mask: tuple[int, ...],
) -> LocalCarrierState:
    """Update each mark only from the corresponding gene's expression history."""

    values = np.asarray(inherited.values, dtype=float).copy()
    if not adult_states:
        return inherited
    signs = np.asarray(
        [int_to_signs(state, len(values)) for state in adult_states], dtype=float
    )
    allowed = set(mask)
    for gene in range(len(values)):
        if gene not in allowed:
            values[gene] = 0.0
            continue
        proposal = float(values[gene])
        for sign in signs[:, gene]:
            proposal = (1.0 - genome.write_rate) * proposal + genome.write_rate * float(sign)
        prior_sign = int(np.sign(values[gene]))
        proposal_sign = int(np.sign(proposal))
        if prior_sign and proposal_sign and prior_sign != proposal_sign:
            tail = signs[-genome.hysteresis :, gene]
            if len(tail) < genome.hysteresis or not np.all(tail == proposal_sign):
                proposal = float(values[gene]) * (1.0 - genome.decay)
        values[gene] = float(np.clip(proposal, -1.0, 1.0))
    return LocalCarrierState(tuple(float(value) for value in values))


def copy_local(
    state: LocalCarrierState,
    genome: LocalCarrierGenome,
    noise: CopyNoiseSpec,
    mask: tuple[int, ...],
    rng: np.random.Generator,
) -> LocalCarrierState:
    """Transmit marks with dilution, local noise, decay, and independent dropout."""

    values = np.asarray(state.values, dtype=float).copy()
    allowed = np.zeros(len(values), dtype=bool)
    allowed[list(mask)] = True
    values[~allowed] = 0.0
    values[allowed] *= (1.0 - genome.decay) * noise.dilution
    if noise.sigma:
        values[allowed] += rng.normal(0.0, noise.sigma, size=int(np.sum(allowed)))
    dropped = rng.random(len(values)) < noise.dropout
    values[dropped | ~allowed] = 0.0
    return LocalCarrierState(tuple(float(value) for value in np.clip(values, -1.0, 1.0)))


def read_local(
    base_state: int,
    state: LocalCarrierState,
    coupling: float,
    rng: np.random.Generator,
) -> int:
    """Bias gene i only from mark i; no target or history argument exists."""

    return apply_mark_bias(
        base_state, np.asarray(state.values, dtype=float), coupling, rng
    )


def develop_local_cycle(
    viewed: MechanismRulebook,
    previous_state: int,
    base_state: int,
    carrier: LocalCarrierState,
    coupling: float,
    expression_flip_probability: float,
    wagner_max_sweeps: int,
    carry_rng: np.random.Generator,
    read_rng: np.random.Generator,
) -> MemoryCycle:
    """Develop after ordinary expression carry/reset and a same-gene mark read."""

    initial = apply_carryover(
        previous_state,
        base_state,
        viewed.genes,
        1.0,
        expression_flip_probability,
        carry_rng,
    )
    initial = read_local(initial, carrier, coupling, read_rng)
    result = viewed.develop(initial, None, wagner_max_sweeps)
    return MemoryCycle(
        int(result.final_state),
        tuple(float(value) for value in carrier.values),
        result.status,
        int(result.steps),
    )
