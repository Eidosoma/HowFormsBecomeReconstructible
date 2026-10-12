"""Cue-aware Wagner dynamics used only by the exploratory rescue campaign."""

from __future__ import annotations

import numpy as np

from .accelerate import wagner_clamped_sweep, wagner_sweep
from .landscape import bits_to_int, canonical_cycle, int_to_bits, int_to_signs, signs_to_int
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import AttractorPair, cue_nodes
from .types import DevelopmentResult
from .wagner import WagnerRulebook, gamma_multipliers
from .wagner_rescue_config import CueIntervention


def intervention_nodes(
    pair: AttractorPair,
    genes: int,
    intervention: CueIntervention,
    ordering: np.ndarray,
) -> tuple[int, ...]:
    """Return the frozen target-discriminating node subset for one cue."""

    if intervention.mode == "no_cue":
        return ()
    if intervention.mode == "target_injection":
        return tuple(range(genes))
    return cue_nodes(
        pair,
        genes,
        intervention.fraction,
        ordering,
    )


def _clamp_signs(
    state: int, target_state: int, genes: int, nodes: tuple[int, ...]
) -> int:
    bits = int_to_bits(state, genes)
    target = int_to_bits(target_state, genes)
    for gene in nodes:
        bits[gene] = target[gene]
    return bits_to_int(bits)


def _field_bias(
    source: WagnerRulebook,
    target_state: int,
    nodes: tuple[int, ...],
    strength: float,
) -> np.ndarray:
    """Build a row-norm-standardized, target-directed external field."""

    bias = source.bias.copy()
    target = int_to_signs(target_state, source.genes).astype(float)
    row_norms = np.linalg.norm(source.weights, axis=1)
    for gene in nodes:
        scale = float(row_norms[gene])
        if scale == 0.0:
            scale = 1.0
        bias[gene] += strength * scale * target[gene]
    return bias


def _cue_step(
    rulebook: MechanismRulebook,
    state: int,
    multipliers: np.ndarray,
    intervention: CueIntervention,
    target_state: int,
    nodes: tuple[int, ...],
    clamped_mask: np.ndarray | None = None,
    target_signs: np.ndarray | None = None,
    cue_bias: np.ndarray | None = None,
) -> int:
    source = rulebook.source
    if not isinstance(source, WagnerRulebook):  # pragma: no cover - config guards this.
        raise TypeError("Wagner rescue dynamics require a Wagner rulebook")
    effective = source.effective_weights(multipliers)
    signs = int_to_signs(state, source.genes)
    if intervention.mode == "persistent_hard":
        if clamped_mask is None or target_signs is None:
            raise ValueError("persistent hard cue context is missing")
        if rulebook.variant == "wagner_sequential":
            updated = wagner_clamped_sweep(
                effective,
                source.bias,
                source.order,
                signs,
                clamped_mask,
                target_signs,
            )
        else:
            fields = effective @ signs + source.bias
            updated = signs.copy()
            updated[fields > 0.0] = 1
            updated[fields < 0.0] = -1
            updated[clamped_mask] = target_signs[clamped_mask]
        return signs_to_int(updated)
    if intervention.mode == "target_field":
        if cue_bias is None:
            raise ValueError("target-field cue context is missing")
        if rulebook.variant == "wagner_sequential":
            return signs_to_int(
                wagner_sweep(effective, cue_bias, source.order, signs)
            )
        fields = effective @ signs + cue_bias
        updated = signs.copy()
        updated[fields > 0.0] = 1
        updated[fields < 0.0] = -1
        return signs_to_int(updated)
    raise ValueError(f"cue step does not support mode {intervention.mode}")


def develop_with_intervention(
    rulebook: MechanismRulebook,
    initial_state: int,
    intervention: CueIntervention,
    target_state: int,
    nodes: tuple[int, ...],
    gamma_variance: float,
    max_sweeps: int,
    rng: np.random.Generator,
) -> DevelopmentResult:
    """Develop once while applying one registered temporary cue policy."""

    source = rulebook.source
    if not isinstance(source, WagnerRulebook):
        raise TypeError("Wagner rescue dynamics require a Wagner rulebook")
    if intervention.mode == "target_injection":
        return DevelopmentResult("injected", int(target_state), 0, (int(target_state),))
    multipliers = gamma_multipliers(source.genes, gamma_variance, rng)
    if intervention.mode == "no_cue":
        return rulebook.develop(initial_state, multipliers, max_sweeps)
    if intervention.mode == "initialization":
        clamped = _clamp_signs(initial_state, target_state, source.genes, nodes)
        return rulebook.develop(clamped, multipliers, max_sweeps)

    current = (
        _clamp_signs(initial_state, target_state, source.genes, nodes)
        if intervention.mode == "persistent_hard"
        else int(initial_state)
    )
    clamped_mask: np.ndarray | None = None
    target_signs: np.ndarray | None = None
    cue_bias: np.ndarray | None = None
    if intervention.mode == "persistent_hard":
        clamped_mask = np.zeros(source.genes, dtype=np.bool_)
        clamped_mask[list(nodes)] = True
        target_signs = int_to_signs(target_state, source.genes)
    elif intervention.mode == "target_field":
        cue_bias = _field_bias(
            source, target_state, nodes, intervention.field_strength
        )
    positions: dict[int, int] = {}
    path: list[int] = []
    for sweep in range(max_sweeps):
        if current in positions:
            cycle = canonical_cycle(path[positions[current] :])
            if len(cycle) == 1:
                return DevelopmentResult("point", cycle[0], sweep, cycle)
            return DevelopmentResult("cycle", current, sweep, cycle)
        positions[current] = len(path)
        path.append(current)
        following = _cue_step(
            rulebook,
            current,
            multipliers,
            intervention,
            target_state,
            nodes,
            clamped_mask,
            target_signs,
            cue_bias,
        )
        if following == current:
            return DevelopmentResult("point", current, sweep + 1, (current,))
        current = following
    return DevelopmentResult("nonconvergent", current, max_sweeps, ())
