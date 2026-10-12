from __future__ import annotations

from dataclasses import replace

import pytest

from gre_sim.analysis import analyze_records
from gre_sim.artifacts import canonical_digest
from gre_sim.campaign import (
    _arm_values,
    build_registry,
    expected_future_count,
    run_registry,
)
from gre_sim.config import StudySpec


def sampled_boolean_quick() -> StudySpec:
    return replace(
        StudySpec.quick(),
        engines=("boolean",),
        cohorts=("sampled",),
    )


def test_campaign_count_analysis_and_worker_invariance() -> None:
    spec = sampled_boolean_quick()
    registry = build_registry(spec)
    serial = run_registry(registry, spec, workers=1)
    parallel = run_registry(registry, spec, workers=2)
    assert len(serial) == expected_future_count(spec, registry) == 96
    assert canonical_digest(serial) == canonical_digest(parallel)
    analysis = analyze_records(serial, registry, spec)
    assert analysis["futures"] == 96
    assert set(analysis["primary"]) == {"boolean.sampled"}
    assert not analysis["eligible_for_advancement_gate"]
    assert not analysis["advance_to_confirmation"]


def test_evolved_quick_targets_come_from_another_population() -> None:
    spec = replace(
        StudySpec.quick(), engines=("boolean",), cohorts=("evolved",)
    )
    registry = build_registry(spec)
    source = registry["sources"][0]
    assert source["source_origin"] != source["independent_origin"]
    assert source["source"]["uid"] != source["independent"]["uid"]


def test_evolved_registry_is_worker_order_invariant() -> None:
    spec = replace(
        StudySpec.quick(), engines=("boolean",), cohorts=("evolved",)
    )
    serial = build_registry(spec, workers=1)
    parallel = build_registry(spec, workers=2)
    assert canonical_digest(serial) == canonical_digest(parallel)


def test_v2_campaign_modes_count_worker_invariance_and_zero_limit() -> None:
    spec = replace(StudySpec.quick_v2(), cohorts=("sampled",))
    registry = build_registry(spec)
    serial = run_registry(registry, spec, workers=1)
    parallel = run_registry(registry, spec, workers=2)
    assert len(serial) == expected_future_count(spec, registry) == 448
    assert canonical_digest(serial) == canonical_digest(parallel)
    assert {record["inheritance_mode"] for record in serial} == {
        "self",
        "donor_shuffled",
    }

    paired = {
        (
            record["source_id"],
            record["state_id"],
            record["arm"],
            record["carryover"],
            record["future_index"],
            record["inheritance_mode"],
        ): record
        for record in serial
    }
    for record in serial:
        if record["inheritance_mode"] != "self" or float(record["carryover"]) != 0:
            continue
        donor = paired[
            (
                record["source_id"],
                record["state_id"],
                record["arm"],
                record["carryover"],
                record["future_index"],
                "donor_shuffled",
            )
        ]
        assert record["trace_digest"] == donor["trace_digest"]
        assert record["future_id"] != donor["future_id"]

    analysis = analyze_records(serial, registry, spec)
    assert analysis["futures"] == 448
    assert len(analysis["primary"]) == 8
    assert not analysis["eligible_for_advancement_gate"]
    assert not analysis["advance_to_confirmation"]
    assert all(
        value["shrinkage_counts"] == {"0": 8}
        for name, value in analysis["primary"].items()
        if name.endswith(".hierarchical")
    )
    broken = [dict(record) for record in serial]
    broken[0].pop("inheritance_mode")
    with pytest.raises(ValueError, match="inheritance mode"):
        analyze_records(broken, registry, spec)


def test_target_aligned_arm_uses_own_old_anchor_without_changing_legacy_arm() -> None:
    spec = replace(
        StudySpec.quick_v2(), engines=("boolean",), cohorts=("sampled",)
    )
    bundle = build_registry(spec)["sources"][0]
    launch = bundle["launches"][0]
    developed = int(launch["developed_state"])
    source_old = int(launch["old_state"])
    legacy = _arm_values(bundle, launch, "developed_under_target")
    own_anchor = _arm_values(bundle, launch, "target_aligned_own_anchor")
    assert legacy[1:] == (developed, developed, source_old)
    assert own_anchor[1:] == (developed, developed, developed)
