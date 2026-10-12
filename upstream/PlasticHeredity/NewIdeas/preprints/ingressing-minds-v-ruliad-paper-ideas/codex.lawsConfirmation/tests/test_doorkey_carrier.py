import numpy as np
import pytest

from laws_confirmation.doorkey_carrier import (
    GermSchema,
    address_table,
    carrier_digest,
    corrupt_byte,
    empty_germ,
    permute_payloads,
    read_germ,
    write_germ_from_local_evidence,
)


def _strong_evidence(targets: list[int]) -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    for slot, target in enumerate(targets):
        evidence[0, slot, target] = 12.0
    return evidence


def test_address_table_and_empty_bytes_match_phrl0_golden_vector():
    schema = GermSchema()
    expected_addresses = np.asarray(
        [[0, 19, 41, 97], [1, 92, 192, 40], [2, 165, 87, 239], [3, 238, 238, 182]],
        dtype=np.uint8,
    )
    assert np.array_equal(address_table(schema), expected_addresses)
    germ = empty_germ(1, schema)
    expected_slots = []
    for address, checksum in zip(expected_addresses, (156, 68, 236, 148)):
        expected_slots.append(
            [*address.tolist(), *([128] * 8), 0, 255, 0, checksum]
        )
    assert germ.shape == (1, 64)
    assert germ.dtype == np.uint8
    assert germ.reshape(4, 16).tolist() == expected_slots
    assert len(bytes(germ[0])) == 64
    assert len(carrier_digest(germ)) == 64


def test_strong_local_evidence_matches_phrl0_quantization_and_checksums():
    schema = GermSchema()
    germ = empty_germ(1, schema)
    written, commit = write_germ_from_local_evidence(
        _strong_evidence([0, 1, 2, 3]), germ, schema
    )
    slots = written.reshape(4, 16)
    assert commit.tolist() == [[True, True, True, True]]
    assert slots[:, 12].tolist() == [255] * 4
    assert slots[:, 13].tolist() == [0] * 4
    assert slots[:, 14].tolist() == [1] * 4
    assert slots[:, 15].tolist() == [157, 69, 237, 149]
    for slot, target in enumerate((0, 1, 2, 3)):
        expected_payload = np.full(8, 125, dtype=np.uint8)
        expected_payload[target] = 149
        assert np.array_equal(slots[slot, 4:12], expected_payload)
    decoded = read_germ(written, schema)
    assert decoded.active.all()
    assert decoded.prior_logits.argmax(axis=-1).tolist() == [[0, 1, 2, 3]]


def test_agreement_ages_without_rewriting_and_reversal_rewrites():
    schema = GermSchema()
    inherited, _ = write_germ_from_local_evidence(
        _strong_evidence([0, 1, 2, 3]), empty_germ(1, schema), schema
    )
    renewed, commit = write_germ_from_local_evidence(
        _strong_evidence([0, 1, 2, 3]), inherited, schema
    )
    assert not commit.any()
    assert renewed.reshape(4, 16)[:, 13].tolist() == [1] * 4
    reversed_germ, changed = write_germ_from_local_evidence(
        _strong_evidence([1, 2, 3, 4]), renewed, schema
    )
    assert changed.all()
    assert read_germ(reversed_germ, schema).prior_logits.argmax(axis=-1).tolist() == [
        [1, 2, 3, 4]
    ]


def test_corruption_and_wrong_content_controls_preserve_address_semantics():
    schema = GermSchema()
    written, _ = write_germ_from_local_evidence(
        _strong_evidence([0, 1, 2, 3]), empty_germ(1, schema), schema
    )
    corrupted = corrupt_byte(written, 5)
    lesion = read_germ(corrupted, schema)
    assert lesion.checksum_valid.tolist() == [[False, True, True, True]]
    assert lesion.active.tolist() == [[False, True, True, True]]

    wrong = permute_payloads(written, np.asarray([1, 2, 3, 0]), schema)
    wrong_read = read_germ(wrong, schema)
    assert wrong_read.address_valid.all()
    assert wrong_read.checksum_valid.all()
    assert wrong_read.prior_logits.argmax(axis=-1).tolist() == [[1, 2, 3, 0]]


def test_carrier_rejects_shape_dtype_and_bad_permutation():
    schema = GermSchema()
    germ = empty_germ(1, schema)
    with pytest.raises(ValueError):
        read_germ(germ.astype(np.int16), schema)
    with pytest.raises(ValueError):
        read_germ(germ[:, :-1], schema)
    with pytest.raises(ValueError):
        permute_payloads(germ, np.asarray([0, 0, 2, 3]), schema)

