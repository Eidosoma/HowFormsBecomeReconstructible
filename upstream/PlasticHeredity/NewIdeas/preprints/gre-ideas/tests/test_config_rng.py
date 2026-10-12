from __future__ import annotations

import json
from pathlib import Path

from gre_sim.artifacts import canonical_digest
from gre_sim.config import StudySpec
from gre_sim.rng import rng_for, seed_for


ROOT = Path(__file__).resolve().parents[1]


def test_protocol_roundtrip_and_static_files_are_fully_frozen() -> None:
    for name, expected in (("quick-v1.json", StudySpec.quick()), ("pilot-v1.json", StudySpec.pilot())):
        value = json.loads((ROOT / "protocols" / name).read_text(encoding="utf-8"))
        restored = StudySpec.from_dict(value)
        assert restored == expected
        assert StudySpec.from_dict(restored.to_dict()) == restored

    v2_value = json.loads(
        (ROOT / "protocols" / "quick-v2-prototype.json").read_text(encoding="utf-8")
    )
    assert StudySpec.from_dict(v2_value) == StudySpec.quick_v2()


def test_v1_protocol_digests_are_unchanged_by_v2_fields() -> None:
    assert (
        canonical_digest(StudySpec.quick().to_dict())
        == "68f3d6e179d67535bb80a21867ab90a441d7c27bd3d15c36712084d654828604"
    )
    assert (
        canonical_digest(StudySpec.pilot().to_dict())
        == "7c1751eca2d6152b1551eb8ee1a0d31872b0834d660a73d1278aa79d85e27579"
    )
    assert "inheritance_modes" not in StudySpec.quick().to_dict()
    assert StudySpec.quick_v2().to_dict()["inheritance_modes"] == (
        "self",
        "donor_shuffled",
    )


def test_semantic_seed_domains_are_stable_and_distinct() -> None:
    master = StudySpec.quick().master_seed
    assert seed_for(master, "future", 1) == seed_for(master, "future", 1)
    assert seed_for(master, "future", 1) != seed_for(master, "future", 2)
    assert rng_for(master, "cell", 4).integers(0, 2**32) == rng_for(
        master, "cell", 4
    ).integers(0, 2**32)


def test_invalid_future_halves_are_rejected() -> None:
    value = StudySpec.quick().to_dict()
    value["futures_per_cell"] = 3
    try:
        StudySpec.from_dict(value)
    except ValueError as error:
        assert "even" in str(error)
    else:  # pragma: no cover
        raise AssertionError("odd future count was accepted")

    donor = StudySpec.quick_v2().to_dict()
    donor["futures_per_cell"] = 2
    try:
        StudySpec.from_dict(donor)
    except ValueError as error:
        assert "two futures per half" in str(error)
    else:  # pragma: no cover
        raise AssertionError("one-future donor halves were accepted")
