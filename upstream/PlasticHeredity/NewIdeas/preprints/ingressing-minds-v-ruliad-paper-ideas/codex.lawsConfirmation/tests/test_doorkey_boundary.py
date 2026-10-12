from dataclasses import fields
import inspect

import numpy as np
import pytest

from laws_confirmation.doorkey_boundary import (
    BoundaryPacket,
    PublicRulebook,
    audit_boundary_reset,
    birth_descendant,
    boundary_audit_passes,
    contaminate_soma,
    make_boundary_packet,
)
from laws_confirmation.doorkey_carrier import (
    GermSchema,
    empty_germ,
    read_germ,
    write_germ_from_local_evidence,
)


def _evidence(offset: int) -> np.ndarray:
    result = np.zeros((1, 4, 8), dtype=np.float32)
    for slot in range(4):
        result[0, slot, (slot + offset) % 8] = 12.0
    return result


def test_boundary_packet_has_one_field_and_exactly_64_bytes():
    packet = make_boundary_packet(empty_germ(1))
    assert [field.name for field in fields(BoundaryPacket)] == ["payload"]
    assert len(packet.payload) == 64
    with pytest.raises(ValueError):
        BoundaryPacket(bytes(63))
    with pytest.raises(ValueError):
        make_boundary_packet(np.zeros((2, 64), dtype=np.uint8))


def test_birth_api_cannot_accept_parent_state_and_copies_no_memory():
    parameters = tuple(inspect.signature(birth_descendant).parameters)
    assert parameters == ("packet", "rulebook", "birth_seed")
    rulebook = PublicRulebook()
    parent = birth_descendant(make_boundary_packet(empty_germ(1)), rulebook, 10)
    contaminate_soma(parent, 12345.0)
    packet = make_boundary_packet(parent.germ)
    child = birth_descendant(packet, rulebook, 11)
    result = audit_boundary_reset(parent, child, packet)
    assert boundary_audit_passes(result)


def test_three_boundaries_read_and_rewrite_the_same_schema():
    schema = GermSchema()
    rulebook = PublicRulebook()
    parent = birth_descendant(make_boundary_packet(empty_germ(1)), rulebook, 100)
    digests = []
    for boundary in range(3):
        contaminate_soma(parent, 1000.0 + boundary)
        packet = make_boundary_packet(parent.germ, schema)
        child = birth_descendant(packet, rulebook, 101 + boundary)
        audit = audit_boundary_reset(parent, child, packet)
        assert boundary_audit_passes(audit)
        if boundary > 0:
            assert read_germ(child.germ, schema).active.all()
        rewritten, commit = write_germ_from_local_evidence(
            _evidence(boundary + 1), child.germ, schema
        )
        assert commit.all()
        assert read_germ(rewritten, schema).active.all()
        digests.append(bytes(rewritten[0]))
        child.germ = rewritten
        parent = child
    assert len(set(digests)) == 3

