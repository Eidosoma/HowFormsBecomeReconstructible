from __future__ import annotations

import json
from pathlib import Path

from gre_sim.analysis import SHRINKAGE_KAPPAS
from gre_sim.artifacts import canonical_digest
from gre_sim.cli import build_parser
from gre_sim.config import StudySpec
from gre_sim.stage_a import (
    EXPECTED_FUTURES,
    EXPECTED_RULEBOOKS_PER_ENGINE,
    KAPPA_GRID,
)


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_stage_a_protocol_roundtrips_and_has_expected_size() -> None:
    value = json.loads(
        (ROOT / "protocols" / "stage-a-v2.json").read_text(encoding="utf-8")
    )
    spec = StudySpec.stage_a_v2()
    assert StudySpec.from_dict(value) == spec
    assert canonical_digest(spec.to_dict()) == (
        "eb0e201ea26df783852c3a134b2b8aace7e94c79a0c5853c5e100942af0de9d0"
    )
    assert spec.cohorts == ("sampled",)
    assert not spec.evolution.enabled
    assert spec.sampled_rulebooks == EXPECTED_RULEBOOKS_PER_ENGINE
    assert (
        len(spec.engines)
        * spec.sampled_rulebooks
        * spec.launch_states_per_rulebook
        * len(spec.arms)
        * len(spec.carryover_values)
        * spec.futures_per_cell
        * len(spec.inheritance_modes)
        == EXPECTED_FUTURES
    )
    assert KAPPA_GRID == SHRINKAGE_KAPPAS


def test_stage_a_cli_alias_and_audit_command_are_registered() -> None:
    parser = build_parser()
    run = parser.parse_args(
        ["run", "--protocol", "stage-a-v2", "--output", "unused"]
    )
    audit = parser.parse_args(["audit-stage-a", "unused"])
    assert run.protocol == "stage-a-v2"
    assert audit.command == "audit-stage-a"
