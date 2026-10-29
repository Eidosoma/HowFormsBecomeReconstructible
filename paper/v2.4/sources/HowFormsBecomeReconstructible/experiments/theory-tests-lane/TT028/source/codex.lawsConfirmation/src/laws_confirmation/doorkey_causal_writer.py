"""Causal, baseline-aware writer for the unchanged DoorKey 64-byte germ.

The writer is deliberately analytic.  It records only lived actions whose
public before/after transition verifies one of the four Stage-A effects, and
compares those actions with the same individual's reconstructed birth policy.
The evidence ledger is somatic; only the resulting PHRL-0 bytes may cross a
lineage boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from .doorkey_carrier import (
    GermSchema,
    empty_germ,
    read_germ,
    write_germ_from_local_evidence,
)
from .doorkey_env import Action, DoorKeyEnv


SLOT_NAMES = ("find_key", "acquire_key", "find_door", "open_door")
MIN_VERIFIED_EFFECTS = 10
JEFFREYS_ALPHA = 0.5
INTERACTION_SLOTS = (1, 3)
ORTHOGONAL_TILE_INDICES = (1, 3, 5, 7)


def _observation_array(observation: np.ndarray) -> np.ndarray:
    value = np.asarray(observation, dtype=np.float32)
    if value.shape != (13,) or not np.isfinite(value).all():
        raise ValueError("DoorKey observation must be one finite 13-vector")
    return value


def _probability_array(probabilities: np.ndarray) -> np.ndarray:
    value = np.asarray(probabilities, dtype=np.float64)
    if value.shape != (8,) or not np.isfinite(value).all():
        raise ValueError("action probabilities must be one finite eight-vector")
    if np.any(value < 0) or not np.isclose(value.sum(), 1.0, atol=1e-6):
        raise ValueError("action probabilities must be nonnegative and sum to one")
    return value


def router_context_numpy(observation: np.ndarray) -> int:
    """Mirror the frozen four-slot public reader address."""

    value = _observation_array(observation)
    tiles = np.rint(value[:9]).astype(np.int64)
    has_key = bool(value[9] > 0.5)
    standing_on_key = bool(value[10] > 0.5)
    key_visible = bool(np.any(tiles == DoorKeyEnv.KEY) or standing_on_key)
    door_visible = bool(
        np.any((tiles == DoorKeyEnv.DOOR_CLOSED) | (tiles == DoorKeyEnv.DOOR_OPEN))
    )
    context = 0
    if not has_key and key_visible:
        context = 1
    if has_key:
        context = 2
    if has_key and door_visible:
        context = 3
    return context


def exact_interaction_opportunity(observation: np.ndarray, slot: int) -> bool:
    """Whether an interaction action can have the declared effect now."""

    value = _observation_array(observation)
    if slot == 1:
        return router_context_numpy(value) == 1 and bool(value[10] > 0.5)
    if slot == 3:
        tiles = np.rint(value[:9]).astype(np.int64)
        adjacent_closed_door = any(
            tiles[index] == DoorKeyEnv.DOOR_CLOSED
            for index in ORTHOGONAL_TILE_INDICES
        )
        return (
            router_context_numpy(value) == 3
            and bool(value[9] > 0.5)
            and not bool(value[11] > 0.5)
            and adjacent_closed_door
        )
    return False


def _transition_has_effect(
    slot: int,
    before: np.ndarray,
    after: np.ndarray,
    info: Mapping[str, Any],
) -> bool:
    events = tuple(str(event) for event in info.get("events_fired", ()))
    before_tiles = np.rint(before[:9]).astype(np.int64)
    after_tiles = np.rint(after[:9]).astype(np.int64)
    before_key_visible = bool(
        np.any(before_tiles == DoorKeyEnv.KEY) or before[10] > 0.5
    )
    after_key_visible = bool(
        np.any(after_tiles == DoorKeyEnv.KEY) or after[10] > 0.5
    )
    before_door_visible = bool(
        np.any(
            (before_tiles == DoorKeyEnv.DOOR_CLOSED)
            | (before_tiles == DoorKeyEnv.DOOR_OPEN)
        )
    )
    after_door_visible = bool(
        np.any(
            (after_tiles == DoorKeyEnv.DOOR_CLOSED)
            | (after_tiles == DoorKeyEnv.DOOR_OPEN)
        )
    )
    if slot == 0:
        return (
            "find_key" in events
            and not before_key_visible
            and after_key_visible
        )
    if slot == 1:
        return (
            exact_interaction_opportunity(before, 1)
            and bool(info.get("acquired", False))
            and not bool(before[9] > 0.5)
            and bool(after[9] > 0.5)
        )
    if slot == 2:
        return (
            "find_door" in events
            and not before_door_visible
            and after_door_visible
            and bool(before[9] > 0.5)
        )
    if slot == 3:
        return (
            exact_interaction_opportunity(before, 3)
            and bool(info.get("opened", False))
            and not bool(before[11] > 0.5)
            and bool(after[11] > 0.5)
        )
    raise ValueError("slot must lie in [0, 4)")


@dataclass
class CausalWriterLedger:
    """Disposable counts and baseline sums accumulated inside one life."""

    effect_action_counts: np.ndarray
    birth_probability_sums: np.ndarray
    final_probability_sums: np.ndarray
    context_action_counts: np.ndarray
    interaction_attempt_counts: np.ndarray
    transition_count: int = 0

    @classmethod
    def empty(cls) -> "CausalWriterLedger":
        return cls(
            effect_action_counts=np.zeros((4, 8), dtype=np.int64),
            birth_probability_sums=np.zeros((4, 8), dtype=np.float64),
            final_probability_sums=np.zeros((4, 8), dtype=np.float64),
            context_action_counts=np.zeros((4, 8), dtype=np.int64),
            interaction_attempt_counts=np.zeros((4, 8), dtype=np.int64),
        )

    def validate(self) -> None:
        integer_fields = (
            self.effect_action_counts,
            self.context_action_counts,
            self.interaction_attempt_counts,
        )
        float_fields = (
            self.birth_probability_sums,
            self.final_probability_sums,
        )
        if any(value.shape != (4, 8) for value in (*integer_fields, *float_fields)):
            raise ValueError("writer ledger fields must have shape [4, 8]")
        if any(not np.issubdtype(value.dtype, np.integer) for value in integer_fields):
            raise TypeError("writer count ledgers must be integer arrays")
        if any(np.any(value < 0) for value in integer_fields):
            raise ValueError("writer counts cannot be negative")
        if any(not np.isfinite(value).all() for value in float_fields):
            raise ValueError("writer probability sums must be finite")
        if self.transition_count < 0:
            raise ValueError("transition count cannot be negative")
        if np.any(self.effect_action_counts > self.context_action_counts):
            raise ValueError("effect counts cannot exceed context action counts")
        if np.any(self.interaction_attempt_counts > self.context_action_counts):
            raise ValueError("interaction attempts cannot exceed context actions")

    def record(
        self,
        before_observation: np.ndarray,
        action: int,
        after_observation: np.ndarray,
        info: Mapping[str, Any],
        birth_probabilities: np.ndarray,
        final_probabilities: np.ndarray,
    ) -> bool:
        """Record one lived transition; return whether its addressed effect fired."""

        before = _observation_array(before_observation)
        after = _observation_array(after_observation)
        if not 0 <= int(action) < 8:
            raise ValueError("action must lie in [0, 8)")
        selected = int(action)
        birth = _probability_array(birth_probabilities)
        final = _probability_array(final_probabilities)
        slot = router_context_numpy(before)
        self.context_action_counts[slot, selected] += 1
        if exact_interaction_opportunity(before, slot):
            self.interaction_attempt_counts[slot, selected] += 1
        effect = _transition_has_effect(slot, before, after, info)
        if effect:
            self.effect_action_counts[slot, selected] += 1
            self.birth_probability_sums[slot] += birth
            self.final_probability_sums[slot] += final
        self.transition_count += 1
        return effect

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "effect_action_counts": self.effect_action_counts.tolist(),
            "effect_counts": self.effect_action_counts.sum(axis=1).tolist(),
            "birth_probability_sums": self.birth_probability_sums.tolist(),
            "final_probability_sums": self.final_probability_sums.tolist(),
            "context_action_counts": self.context_action_counts.tolist(),
            "interaction_attempt_counts": self.interaction_attempt_counts.tolist(),
            "transition_count": int(self.transition_count),
        }


@dataclass(frozen=True)
class CausalWriterDecision:
    evidence_logits: np.ndarray
    confirmation_mask: np.ndarray
    effect_distribution: np.ndarray
    birth_distribution: np.ndarray
    targets: np.ndarray
    confidence: np.ndarray
    trust: np.ndarray
    effect_counts: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_logits": self.evidence_logits.tolist(),
            "confirmation_mask": self.confirmation_mask.tolist(),
            "effect_distribution": self.effect_distribution.tolist(),
            "birth_distribution": self.birth_distribution.tolist(),
            "targets": self.targets.tolist(),
            "confidence": self.confidence.tolist(),
            "trust": self.trust.tolist(),
            "effect_counts": self.effect_counts.tolist(),
        }


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - values.max(axis=-1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum(axis=-1, keepdims=True)


def derive_causal_writer_decision(
    ledger: CausalWriterLedger,
    *,
    min_verified_effects: int = MIN_VERIFIED_EFFECTS,
    alpha: float = JEFFREYS_ALPHA,
) -> CausalWriterDecision:
    """Convert verified actions minus same-self birth behavior into logits."""

    ledger.validate()
    if min_verified_effects < 1:
        raise ValueError("minimum verified effects must be positive")
    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("Jeffreys mass must be positive and finite")
    counts = ledger.effect_action_counts.astype(np.float64)
    totals = counts.sum(axis=1)
    denominator = totals[:, None] + 8.0 * alpha
    effect_distribution = (counts + alpha) / denominator
    birth_distribution = (ledger.birth_probability_sums + alpha) / denominator
    if not np.allclose(effect_distribution.sum(axis=1), 1.0, atol=1e-9):
        raise RuntimeError("effect posterior is not normalized")
    if not np.allclose(birth_distribution.sum(axis=1), 1.0, atol=1e-6):
        raise RuntimeError("birth comparator is not normalized")
    logits = np.log(effect_distribution) - np.log(birth_distribution)
    logits -= logits.mean(axis=1, keepdims=True)
    probabilities = _softmax(logits)
    confidence = probabilities.max(axis=1)
    trust = np.clip(np.rint(confidence * 255.0), 0, 255).astype(np.uint8)
    return CausalWriterDecision(
        evidence_logits=logits[None].astype(np.float32),
        confirmation_mask=(totals >= min_verified_effects)[None],
        effect_distribution=effect_distribution,
        birth_distribution=birth_distribution,
        targets=logits.argmax(axis=1).astype(np.int64),
        confidence=confidence,
        trust=trust,
        effect_counts=totals.astype(np.int64),
    )


@dataclass(frozen=True)
class GermRenewal:
    germ: np.ndarray
    write_mask: np.ndarray
    new_write_mask: np.ndarray
    same_content_renewal_mask: np.ndarray
    semantic_change_mask: np.ndarray
    revocation_mask: np.ndarray
    silent_aging_mask: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "write_mask": self.write_mask.tolist(),
            "new_write_mask": self.new_write_mask.tolist(),
            "same_content_renewal_mask": self.same_content_renewal_mask.tolist(),
            "semantic_change_mask": self.semantic_change_mask.tolist(),
            "revocation_mask": self.revocation_mask.tolist(),
            "silent_aging_mask": self.silent_aging_mask.tolist(),
        }


def _revocation_request(
    ledger: CausalWriterLedger,
    inherited_germ: np.ndarray,
    schema: GermSchema,
) -> np.ndarray:
    inherited = read_germ(inherited_germ, schema)
    inherited_targets = inherited.prior_logits.argmax(axis=-1)[0]
    request = np.zeros((1, 4), dtype=bool)
    for slot in INTERACTION_SLOTS:
        target = int(inherited_targets[slot])
        request[0, slot] = bool(
            inherited.active[0, slot]
            and ledger.interaction_attempt_counts[slot, target]
            >= MIN_VERIFIED_EFFECTS
            and ledger.effect_action_counts[slot, target] == 0
        )
    return request


def renew_germ_from_causal_evidence(
    ledger: CausalWriterLedger,
    inherited_germ: np.ndarray,
    schema: GermSchema | None = None,
) -> GermRenewal:
    """Write, renew, age, or revoke records without changing their byte format."""

    schema = schema or GermSchema()
    schema.validate()
    decision = derive_causal_writer_decision(ledger)
    inherited = read_germ(inherited_germ, schema)
    if inherited_germ.shape != (1, schema.carrier_bytes):
        raise ValueError("causal writer currently accepts one 64-byte carrier")

    candidate, write_mask = write_germ_from_local_evidence(
        decision.evidence_logits,
        empty_germ(1, schema),
        schema,
        confirmation_mask=decision.confirmation_mask,
    )
    requested_revocation = _revocation_request(ledger, inherited_germ, schema)
    aged, _ = write_germ_from_local_evidence(
        decision.evidence_logits,
        inherited_germ,
        schema,
        confirmation_mask=np.zeros((1, 4), dtype=bool),
        revocation_mask=requested_revocation,
    )
    outgoing_slots = aged.reshape(1, 4, 16).copy()
    candidate_slots = candidate.reshape(1, 4, 16)
    outgoing_slots[write_mask] = candidate_slots[write_mask]
    outgoing = outgoing_slots.reshape(1, schema.carrier_bytes)

    candidate_targets = decision.targets[None]
    inherited_targets = inherited.prior_logits.argmax(axis=-1)
    new_write = write_mask & ~inherited.active
    same_content = write_mask & inherited.active & (
        candidate_targets == inherited_targets
    )
    semantic_change = write_mask & inherited.active & (
        candidate_targets != inherited_targets
    )
    actual_revocation = requested_revocation & ~write_mask
    silent_aging = inherited.active & ~write_mask & ~actual_revocation
    decoded = read_germ(outgoing, schema)
    if not decoded.address_valid.all() or not decoded.checksum_valid.all():
        raise RuntimeError("causal writer emitted an invalid carrier")
    return GermRenewal(
        germ=outgoing,
        write_mask=write_mask,
        new_write_mask=new_write,
        same_content_renewal_mask=same_content,
        semantic_change_mask=semantic_change,
        revocation_mask=actual_revocation,
        silent_aging_mask=silent_aging,
    )


def ledger_storage_bytes(ledger: CausalWriterLedger) -> int:
    """Exact transient array bytes, excluding Python/container overhead."""

    ledger.validate()
    return int(
        sum(
            value.nbytes
            for value in (
                ledger.effect_action_counts,
                ledger.birth_probability_sums,
                ledger.final_probability_sums,
                ledger.context_action_counts,
                ledger.interaction_attempt_counts,
            )
        )
    )


def expected_interaction_actions() -> dict[int, int]:
    return {1: int(Action.PICKUP), 3: int(Action.OPEN)}
