"""Exclusive 64-byte lineage-boundary API for the DoorKey benchmark.

The API is intentionally narrow: ``make_boundary_packet`` accepts one carrier,
and ``birth_descendant`` accepts that packet plus a public rulebook and an
outcome-independent birth seed.  It cannot receive a parent learner object.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
from typing import Mapping

import numpy as np

from .doorkey_carrier import GermSchema


SOMATIC_STATE_INVENTORY = (
    "actor_parameters",
    "critic_parameters",
    "writer_parameters",
    "optimizer_state",
    "rollout_state",
    "recurrent_state",
    "normalization_state",
    "curriculum_state",
    "rng_probe",
    "population_statistics",
)


@dataclass(frozen=True)
class PublicRulebook:
    """Frozen, non-lineage-conditioned initialization distribution."""

    version: str = "doorkey-stage-a-v1"
    action_count: int = 8
    observation_width: int = 13
    actor_parameter_count: int = 256
    critic_parameter_count: int = 128
    writer_parameter_count: int = 128
    initialization_std: float = 0.05

    def validate(self) -> None:
        if self.action_count != 8:
            raise ValueError("public rulebook must preserve eight carrier actions")
        for count in (
            self.observation_width,
            self.actor_parameter_count,
            self.critic_parameter_count,
            self.writer_parameter_count,
        ):
            if count < 1:
                raise ValueError("rulebook dimensions must be positive")
        if not 0 < self.initialization_std < 1:
            raise ValueError("initialization_std must lie in (0, 1)")

    def digest(self) -> str:
        self.validate()
        payload = {
            field.name: getattr(self, field.name) for field in fields(self)
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BoundaryPacket:
    """The whole transmissible lineage packet: exactly 64 opaque bytes."""

    payload: bytes

    def __post_init__(self) -> None:
        if type(self.payload) is not bytes:
            raise TypeError("boundary payload must be immutable bytes")
        if len(self.payload) != 64:
            raise ValueError("boundary packet must contain exactly 64 bytes")

    def digest(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


@dataclass
class DescendantState:
    """Fresh somatic state plus an inherited carrier read at birth."""

    germ: np.ndarray
    birth_seed: int
    public_rulebook_digest: str
    somatic: dict[str, np.ndarray]

    def somatic_digests(self) -> dict[str, str]:
        return {
            name: hashlib.sha256(value.tobytes(order="C")).hexdigest()
            for name, value in sorted(self.somatic.items())
        }


def make_boundary_packet(
    germ: np.ndarray, schema: GermSchema | None = None
) -> BoundaryPacket:
    """Serialize one carrier without adding metadata or parent state."""

    schema = schema or GermSchema()
    schema.validate()
    array = np.asarray(germ)
    if array.dtype != np.uint8 or array.shape != (1, schema.carrier_bytes):
        raise ValueError("boundary requires one rank-two uint8 64-byte carrier")
    return BoundaryPacket(array[0].tobytes(order="C"))


def birth_descendant(
    packet: BoundaryPacket,
    rulebook: PublicRulebook,
    birth_seed: int,
) -> DescendantState:
    """Sample fresh soma from the public distribution and read only the packet."""

    rulebook.validate()
    if not 0 <= birth_seed < 2**63:
        raise ValueError("birth_seed must be in [0, 2^63)")
    rng = np.random.default_rng(birth_seed)
    scale = np.float32(rulebook.initialization_std)
    somatic = {
        "actor_parameters": rng.normal(
            0.0, scale, size=rulebook.actor_parameter_count
        ).astype(np.float32),
        "critic_parameters": rng.normal(
            0.0, scale, size=rulebook.critic_parameter_count
        ).astype(np.float32),
        "writer_parameters": rng.normal(
            0.0, scale, size=rulebook.writer_parameter_count
        ).astype(np.float32),
        "optimizer_state": np.zeros(
            rulebook.actor_parameter_count + rulebook.critic_parameter_count,
            dtype=np.float32,
        ),
        "rollout_state": np.zeros((32, rulebook.observation_width), dtype=np.float32),
        "recurrent_state": np.zeros(64, dtype=np.float32),
        "normalization_state": np.zeros(2 * rulebook.observation_width, dtype=np.float32),
        "curriculum_state": np.zeros(8, dtype=np.float32),
        "rng_probe": rng.integers(0, 2**32, size=16, dtype=np.uint32),
        "population_statistics": np.zeros(16, dtype=np.float32),
    }
    if tuple(sorted(somatic)) != tuple(sorted(SOMATIC_STATE_INVENTORY)):
        raise RuntimeError("somatic state inventory and constructor diverged")
    germ = np.frombuffer(packet.payload, dtype=np.uint8).copy().reshape(1, 64)
    return DescendantState(
        germ=germ,
        birth_seed=int(birth_seed),
        public_rulebook_digest=rulebook.digest(),
        somatic=somatic,
    )


def contaminate_soma(state: DescendantState, marker: float) -> None:
    """Development-only leak probe: make every somatic field parent-specific."""

    if not np.isfinite(marker) or marker == 0:
        raise ValueError("marker must be finite and nonzero")
    for name, value in state.somatic.items():
        if np.issubdtype(value.dtype, np.floating):
            state.somatic[name] = np.full_like(value, marker)
        else:
            integer_marker = int(abs(marker)) % (2**32 - 1)
            if integer_marker == 0:
                integer_marker = 1
            state.somatic[name] = np.full_like(value, integer_marker)


def audit_boundary_reset(
    parent: DescendantState,
    child: DescendantState,
    packet: BoundaryPacket,
) -> dict[str, object]:
    """Report structural and byte-level evidence for an exclusive reset."""

    parent_digests = parent.somatic_digests()
    child_digests = child.somatic_digests()
    field_rows: dict[str, dict[str, object]] = {}
    for name in SOMATIC_STATE_INVENTORY:
        parent_value = parent.somatic[name]
        child_value = child.somatic[name]
        field_rows[name] = {
            "parent_digest": parent_digests[name],
            "child_digest": child_digests[name],
            "digest_changed": parent_digests[name] != child_digests[name],
            "memory_shared": bool(np.shares_memory(parent_value, child_value)),
        }
    packet_fields = tuple(field.name for field in fields(BoundaryPacket))
    child_carrier = child.germ[0].tobytes(order="C")
    return {
        "packet_fields": list(packet_fields),
        "packet_has_only_payload_field": packet_fields == ("payload",),
        "packet_bytes": len(packet.payload),
        "packet_digest": packet.digest(),
        "child_carrier_digest": hashlib.sha256(child_carrier).hexdigest(),
        "carrier_exactly_preserved": child_carrier == packet.payload,
        "public_rulebook_unchanged": (
            parent.public_rulebook_digest == child.public_rulebook_digest
        ),
        "somatic_fields": field_rows,
        "all_somatic_digests_changed": all(
            bool(row["digest_changed"]) for row in field_rows.values()
        ),
        "no_somatic_memory_shared": not any(
            bool(row["memory_shared"]) for row in field_rows.values()
        ),
    }


def boundary_audit_passes(result: Mapping[str, object]) -> bool:
    return bool(
        result["packet_has_only_payload_field"]
        and result["packet_bytes"] == 64
        and result["carrier_exactly_preserved"]
        and result["public_rulebook_unchanged"]
        and result["all_somatic_digests_changed"]
        and result["no_somatic_memory_shared"]
    )

