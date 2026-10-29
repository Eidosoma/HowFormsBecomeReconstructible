"""NumPy conformance implementation of the unchanged PHRL-0 64-byte germ.

The authoritative implementation remains ``ai-11-rl-frontier/phrl/slot_germ.py``.
This module mirrors its byte layout so the DoorKey apparatus can run in the
small, NumPy-only laws-confirmation environment.  It intentionally does not add
DoorKey-specific fields or reinterpret the four addresses.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np


@dataclass(frozen=True)
class GermSchema:
    """Four 16-byte records matching the PHRL-0 v0 contract."""

    num_slots: int = 4
    num_actions: int = 8
    slot_bytes: int = 16
    payload_scale: float = 0.25
    max_payload_range: float = 6.0
    min_read_trust: int = 190
    min_write_trust: int = 190
    max_freshness: int = 32
    analytic_route_id: int = 1

    @property
    def carrier_bytes(self) -> int:
        return self.num_slots * self.slot_bytes

    def validate(self) -> None:
        if self.num_slots != 4 or self.slot_bytes != 16:
            raise ValueError("PHRL-0 v0 requires four 16-byte slots")
        if self.num_actions != 8:
            raise ValueError("PHRL-0 v0 payload has exactly eight action bytes")
        if self.carrier_bytes != 64:
            raise ValueError("carrier must serialize to exactly 64 bytes")
        if not 0 <= self.min_read_trust <= 255:
            raise ValueError("read trust must be a byte")
        if not 0 <= self.min_write_trust <= 255:
            raise ValueError("write trust must be a byte")


@dataclass(frozen=True)
class GermRead:
    prior_logits: np.ndarray
    active: np.ndarray
    checksum_valid: np.ndarray
    address_valid: np.ndarray
    trust: np.ndarray
    freshness: np.ndarray


def address_table(schema: GermSchema) -> np.ndarray:
    schema.validate()
    contexts = np.arange(schema.num_slots, dtype=np.int64)
    return np.stack(
        (
            contexts,
            (contexts * 73 + 19) % 256,
            (contexts * 151 + 41) % 256,
            (contexts * 199 + 97) % 256,
        ),
        axis=1,
    ).astype(np.uint8)


def _seal(slots: np.ndarray) -> np.ndarray:
    sealed = np.array(slots, dtype=np.uint8, copy=True)
    checksum = sealed[..., :15].astype(np.int64).sum(axis=-1) % 256
    sealed[..., 15] = checksum.astype(np.uint8)
    return sealed


def _validate_germ(germ: np.ndarray, schema: GermSchema) -> np.ndarray:
    schema.validate()
    array = np.asarray(germ)
    if array.dtype != np.uint8 or array.ndim != 2:
        raise ValueError("germ must be a rank-two uint8 array")
    if array.shape[1] != schema.carrier_bytes:
        raise ValueError("wrong serialized germ size")
    return array


def empty_germ(batch_size: int, schema: GermSchema | None = None) -> np.ndarray:
    """Create addressable, untrusted records with valid checksums."""

    schema = schema or GermSchema()
    schema.validate()
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    slots = np.zeros(
        (batch_size, schema.num_slots, schema.slot_bytes), dtype=np.uint8
    )
    slots[..., 0:4] = address_table(schema)[None, :, :]
    slots[..., 4:12] = 128
    slots[..., 12] = 0
    slots[..., 13] = 255
    slots[..., 14] = 0
    return _seal(slots).reshape(batch_size, schema.carrier_bytes)


def read_germ(germ: np.ndarray, schema: GermSchema | None = None) -> GermRead:
    """Validate and decode the carrier; invalid or weak slots abstain."""

    schema = schema or GermSchema()
    array = _validate_germ(germ, schema)
    slots = array.reshape(array.shape[0], schema.num_slots, schema.slot_bytes)
    expected_address = address_table(schema)[None, :, :]
    address_valid = np.all(slots[..., 0:4] == expected_address, axis=-1)
    expected_checksum = slots[..., :15].astype(np.int64).sum(axis=-1) % 256
    checksum_valid = slots[..., 15].astype(np.int64) == expected_checksum
    trust = slots[..., 12].astype(np.int64)
    freshness = slots[..., 13].astype(np.int64)
    active = (
        address_valid
        & checksum_valid
        & (trust >= schema.min_read_trust)
        & (freshness <= schema.max_freshness)
    )
    quantized = slots[..., 4:12].astype(np.int16) - 128
    decoded = quantized.astype(np.float32) * np.float32(schema.payload_scale)
    centered = decoded - decoded.mean(axis=-1, keepdims=True)
    prior_logits = np.where(active[..., None], centered, np.zeros_like(centered))
    return GermRead(
        prior_logits=prior_logits,
        active=active,
        checksum_valid=checksum_valid,
        address_valid=address_valid,
        trust=trust,
        freshness=freshness,
    )


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - values.max(axis=-1, keepdims=True)
    exponentiated = np.exp(shifted).astype(np.float32)
    return exponentiated / exponentiated.sum(axis=-1, keepdims=True)


def write_germ_from_local_evidence(
    local_evidence_logits: np.ndarray,
    inherited_germ: np.ndarray,
    schema: GermSchema | None = None,
    confirmation_mask: np.ndarray | None = None,
    revocation_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Mirror the PHRL-0 writer without consulting environment truth."""

    schema = schema or GermSchema()
    inherited = _validate_germ(inherited_germ, schema)
    evidence = np.asarray(local_evidence_logits, dtype=np.float32)
    batch_size = inherited.shape[0]
    expected = (batch_size, schema.num_slots, schema.num_actions)
    if evidence.shape != expected:
        raise ValueError(f"local evidence must have shape {expected}")

    inherited_slots = inherited.reshape(
        batch_size, schema.num_slots, schema.slot_bytes
    )
    slots = inherited_slots.copy()
    old_read = read_germ(inherited, schema)

    probabilities = _softmax(evidence)
    confidence = probabilities.max(axis=-1)
    trust = np.clip(np.rint(confidence * np.float32(255.0)), 0, 255).astype(
        np.uint8
    )
    local_target = evidence.argmax(axis=-1)
    inherited_target = old_read.prior_logits.argmax(axis=-1)
    semantic_change = (~old_read.active) | (local_target != inherited_target)
    commit = (trust.astype(np.int64) >= schema.min_write_trust) & semantic_change

    if confirmation_mask is not None:
        confirmation = np.asarray(confirmation_mask, dtype=bool)
        if confirmation.shape != commit.shape:
            raise ValueError("confirmation mask must have one value per carrier slot")
        commit &= confirmation
    if revocation_mask is not None:
        revocation = np.asarray(revocation_mask, dtype=bool)
        if revocation.shape != commit.shape:
            raise ValueError("revocation mask must have one value per carrier slot")
    else:
        revocation = None

    centered = evidence - evidence.mean(axis=-1, keepdims=True)
    payload_range = centered.max(axis=-1, keepdims=True) - centered.min(
        axis=-1, keepdims=True
    )
    denominator = np.maximum(payload_range, np.float32(1e-12))
    shrink = np.minimum(
        np.float32(schema.max_payload_range) / denominator, np.float32(1.0)
    )
    centered = centered * shrink
    quantized_signed = np.clip(
        np.rint(centered / np.float32(schema.payload_scale)), -127, 127
    )
    payload = (quantized_signed.astype(np.int16) + 128).astype(np.uint8)

    candidate = np.zeros_like(slots)
    candidate[..., 0:4] = address_table(schema)[None, :, :]
    candidate[..., 4:12] = payload
    candidate[..., 12] = trust
    candidate[..., 13] = 0
    candidate[..., 14] = schema.analytic_route_id
    slots = np.where(commit[..., None], candidate, slots)

    aged = np.clip(old_read.freshness + 1, 0, 255).astype(np.uint8)
    slots[..., 13] = np.where(commit, np.zeros_like(aged), aged)
    if revocation is not None:
        revoke = revocation & ~commit
        slots[..., 4:12] = np.where(
            revoke[..., None], np.full_like(slots[..., 4:12], 128), slots[..., 4:12]
        )
        slots[..., 12] = np.where(revoke, np.zeros_like(slots[..., 12]), slots[..., 12])
        slots[..., 13] = np.where(revoke, np.zeros_like(slots[..., 13]), slots[..., 13])
        slots[..., 14] = np.where(revoke, np.full_like(slots[..., 14], 3), slots[..., 14])

    sealed = _seal(slots).reshape(batch_size, schema.carrier_bytes)
    return sealed, commit


def permute_payloads(
    germ: np.ndarray,
    permutation: np.ndarray,
    schema: GermSchema | None = None,
) -> np.ndarray:
    """Move content/trust/route among fixed addresses and reseal checksums."""

    schema = schema or GermSchema()
    array = _validate_germ(germ, schema)
    order = np.asarray(permutation, dtype=np.int64)
    if order.shape != (schema.num_slots,):
        raise ValueError("permutation must have one entry per slot")
    if sorted(order.tolist()) != list(range(schema.num_slots)):
        raise ValueError("permutation is not valid")
    slots = array.reshape(array.shape[0], schema.num_slots, schema.slot_bytes).copy()
    slots[..., 4:15] = slots[:, order, 4:15].copy()
    return _seal(slots).reshape(array.shape[0], schema.carrier_bytes)


def corrupt_byte(germ: np.ndarray, byte_index: int, mask: int = 1) -> np.ndarray:
    """Flip one byte without resealing, for checksum lesion controls."""

    array = np.asarray(germ)
    if array.dtype != np.uint8 or array.ndim != 2:
        raise ValueError("germ must be a rank-two uint8 array")
    if not 0 <= byte_index < array.shape[1]:
        raise ValueError("byte index outside carrier")
    if not 0 <= mask <= 255:
        raise ValueError("mask must be a byte")
    corrupted = array.copy()
    corrupted[:, byte_index] = np.bitwise_xor(
        corrupted[:, byte_index], np.uint8(mask)
    )
    return corrupted


def carrier_digest(germ: np.ndarray, schema: GermSchema | None = None) -> str:
    """Hash one exact serialized carrier after enforcing its public shape."""

    schema = schema or GermSchema()
    array = _validate_germ(germ, schema)
    if array.shape[0] != 1:
        raise ValueError("carrier_digest requires exactly one carrier")
    return hashlib.sha256(array[0].tobytes(order="C")).hexdigest()

