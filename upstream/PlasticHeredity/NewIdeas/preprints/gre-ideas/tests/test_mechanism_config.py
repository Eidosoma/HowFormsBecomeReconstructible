from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from gre_sim.artifacts import read_json
from gre_sim.mechanism_config import MechanismSpec, expected_mechanism_futures
from gre_sim.mechanism_protocols import phase_1_spec, phase_2_spec, phase_3_spec


def test_quick_mechanism_protocol_roundtrips_and_counts() -> None:
    spec = MechanismSpec.quick()
    assert MechanismSpec.from_dict(spec.to_dict()) == spec
    assert expected_mechanism_futures(spec) == 200


def test_mechanism_rejects_boolean_weight_noise() -> None:
    spec = MechanismSpec.quick()
    condition = replace(spec.conditions[0], gamma_variances=(0.1,))
    with pytest.raises(ValueError, match="zero rulebook noise"):
        replace(spec, conditions=(condition, *spec.conditions[1:])).validate()


def test_mechanism_requires_twelve_cycle_endpoint_support() -> None:
    with pytest.raises(ValueError, match="run lengths"):
        replace(MechanismSpec.quick(), horizon=8).validate()


def test_frozen_mechanism_phase_record_counts() -> None:
    expected = (665_600, 737_280, 614_400)
    for spec, count in zip(
        (phase_1_spec(), phase_2_spec(), phase_3_spec()), expected, strict=True
    ):
        spec.validate()
        assert expected_mechanism_futures(spec) == count


def test_checked_in_mechanism_protocols_match_executable_specs() -> None:
    root = Path(__file__).resolve().parents[1] / "protocols"
    for index, spec in enumerate(
        (phase_1_spec(), phase_2_spec(), phase_3_spec()), start=1
    ):
        archived = read_json(root / f"wagner-mechanism-phase-{index}-v1.json")
        assert MechanismSpec.from_dict(archived) == spec
