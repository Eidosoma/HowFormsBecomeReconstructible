from __future__ import annotations

from dataclasses import replace

import pytest

from gre_sim.artifacts import read_json, read_jsonl_gz, sha256_file
from gre_sim.lineage_carrier_analysis import (
    _control_names,
    _inapplicable_controls,
    select_calibrated_carriers,
    select_discovery_candidate,
)
from gre_sim.lineage_carrier_config import (
    LineageArmSpec,
    LineageSourceSpec,
    LineageStudySpec,
    LineageWriterSpec,
)
from gre_sim.lineage_carrier_evolution import (
    _correlation_interval,
    run_lineage_evolution,
    verify_lineage_evolution,
)
from gre_sim.lineage_carrier_orchestrator import (
    LINEAGE_RECORD_CAP,
    lineage_carrier_status,
    run_lineage_carrier_campaign,
)
from gre_sim.lineage_carrier_protocols import (
    bounded_initial_replication_spec,
    carrier_calibration_spec,
    evolution_spec,
    lineage_confirmation_spec,
    lineage_discovery_spec,
)
from gre_sim.lineage_carrier_study import (
    _CarrierState,
    _bottleneck,
    _write_from_states,
    expected_lineage_records,
    replay_lineage_future,
    run_lineage_study,
    verify_lineage_study,
)
from gre_sim.plastic_heredity_v2_protocols import carrier_grid


def _writer(engine: str) -> LineageWriterSpec:
    return LineageWriterSpec(f"{engine}.test-natural", engine, "natural", 1.0, 4)


def _tiny_spec() -> LineageStudySpec:
    return LineageStudySpec(
        "lineage-test-cohort",
        "lineage-test",
        "a" * 64,
        (LineageSourceSpec("wagner", 1),),
        (_writer("wagner"),),
        (replace(carrier_grid()[0], engines=("wagner",)),),
        (
            LineageArmSpec("natural-full", primary=True),
            LineageArmSpec("zero", bottleneck="zero"),
        ),
        (0, 1),
        ("forced_break",),
        4,
        midpoint_count=1,
        generation_cycles=2,
        horizon=12,
        strict_run=2,
        stable_run=2,
        bootstrap_repetitions=64,
    )


def test_lineage_config_and_record_budget_are_frozen() -> None:
    spec = _tiny_spec()
    spec.validate()
    assert expected_lineage_records(spec) == 32
    with pytest.raises(ValueError, match="begin at generation zero"):
        replace(spec, checkpoint_generations=(1,)).validate()
    with pytest.raises(ValueError, match="require k"):
        LineageArmSpec("bad", bottleneck="targeted").validate(10)


def test_actual_state_writer_and_bottlenecks() -> None:
    candidate = carrier_grid()[0]
    blank = _CarrierState((0.0,) * 4, (0,) * 4)
    written = _write_from_states(blank, candidate, (0b1111, 0b0011), 4)
    assert written.values[0] > 0.0
    assert written.values[3] < written.values[0]
    targeted = _bottleneck(
        written,
        LineageArmSpec("target", bottleneck="targeted", k=1),
        (3, 2, 1, 0),
        (0, 1, 2, 3),
        (1, 0, 3, 2),
    )
    random = _bottleneck(
        written,
        LineageArmSpec("random", bottleneck="random", k=1),
        (3, 2, 1, 0),
        (0, 1, 2, 3),
        (1, 0, 3, 2),
    )
    assert sum(value != 0.0 for value in targeted.values) == 1
    assert sum(value != 0.0 for value in random.values) == 1
    assert targeted.values != random.values


def test_lineage_study_verifies_replays_and_is_worker_invariant(tmp_path) -> None:
    spec = _tiny_spec()
    one = run_lineage_study(spec, tmp_path / "one", 1)
    two = run_lineage_study(spec, tmp_path / "two", 2)
    assert verify_lineage_study(one)["records"] == 32
    assert verify_lineage_study(two)["records"] == 32
    assert sha256_file(one / "futures.jsonl.gz") == sha256_file(
        two / "futures.jsonl.gz"
    )
    records = list(read_jsonl_gz(one / "futures.jsonl.gz"))
    assert {record["generation"] for record in records} == {0, 1}
    assert all(record["recipient_mode"] == "clone" for record in records)
    assert replay_lineage_future(one, records[-1]["future_id"])["matches"]


def test_registered_discovery_and_confirmation_fit_cap() -> None:
    writers = (_writer("wagner"), _writer("boolean"))
    candidates = (
        replace(carrier_grid()[0], engines=("wagner",)),
        replace(carrier_grid()[1], engines=("wagner",)),
        replace(carrier_grid()[2], engines=("boolean",)),
    )
    calibration = carrier_calibration_spec(writers)
    discovery = lineage_discovery_spec(writers, candidates)
    confirmation = lineage_confirmation_spec(
        writers, (candidates[0], candidates[2]), 3
    )
    total = sum(
        expected_lineage_records(value)
        for value in (calibration, discovery, confirmation)
    )
    assert total < LINEAGE_RECORD_CAP
    assert discovery.checkpoint_generations == (0, 1, 2, 4, 8)
    assert confirmation.checkpoint_generations[-1] == 16


def test_bounded_initial_replication_preserves_causal_ladder() -> None:
    candidate = replace(carrier_grid()[0], engines=("wagner",))
    spec = bounded_initial_replication_spec(_writer("wagner"), candidate, 10)
    assert spec.sources == (LineageSourceSpec("wagner", 128),)
    assert spec.futures_per_cell == 16
    assert spec.checkpoint_generations == (0, 1, 2, 4, 8, 16)
    assert spec.challenges == ("forced_break", "neutral_damage", "release_only")
    assert expected_lineage_records(spec) == 1_916_928
    assert spec.exploratory
    assert "matched-random-k10" not in _control_names(
        spec, "selected-targeted-k10"
    )
    reason = _inapplicable_controls(spec, "selected-targeted-k10")
    assert "matched-random-k10" in reason
    assert "structurally identical" in reason["matched-random-k10"]


def test_selection_is_wagner_primary_and_smallest_k() -> None:
    def gate(engine: str, candidate: str, risk: float, crossover: float) -> dict:
        return {
            "engine": engine,
            "candidate": candidate,
            "arm": "natural-full",
            "calibration_passed": risk >= 0.02 and crossover > 0,
            "primary": {
                "risk_difference": {"mean": risk},
                "crossover": {"mean": crossover},
            },
        }

    calibrated = select_calibrated_carriers(
        {
            "lineage_gates": {
                "w1": gate("wagner", "w1", 0.08, 0.10),
                "w2": gate("wagner", "w2", 0.06, 0.20),
                "b1": gate("boolean", "b1", 0.01, 0.10),
            }
        }
    )
    assert calibrated["wagner"] == ("w1", "w2")
    assert calibrated["boolean"] == ()
    assert calibrated["boolean_benchmark"] == "b1"

    selected = select_discovery_candidate(
        {
            "lineage_gates": {
                "full": {
                    "engine": "wagner",
                    "candidate": "w1",
                    "arm": "natural-full",
                    "k": 10,
                    "passed": True,
                    "persistence": {"risk_difference": {"lower": 0.20}},
                },
                "small": {
                    "engine": "wagner",
                    "candidate": "w2",
                    "arm": "targeted-k3",
                    "k": 3,
                    "passed": True,
                    "persistence": {"risk_difference": {"lower": 0.05}},
                },
            }
        }
    )
    assert selected == {
        "engine": "wagner",
        "candidate": "w2",
        "arm": "targeted-k3",
        "k": 3,
        "generation_8_risk_lower": 0.05,
    }


def test_smoke_campaign_reaches_discovery_boundary(tmp_path) -> None:
    parent = tmp_path / "parent" / "wave-1"
    parent.mkdir(parents=True)
    (parent / "SHA256SUMS").write_text("sealed parent fixture\n", encoding="ascii")
    run = run_lineage_carrier_campaign(
        tmp_path / "campaign",
        parent.parent,
        "discovery",
        2,
        smoke=True,
    )
    status = lineage_carrier_status(run)
    assert status["progress"]["active_stage"] == "paused-after-discovery"
    assert status["stages"]["discovery"]["sealed"]
    assert read_json(run / "discovery-selection.json")["selected"]["engine"] == "wagner"


def test_lineage_evolution_smoke_is_sealed(tmp_path) -> None:
    candidate = replace(carrier_grid()[0], engines=("wagner",))
    spec = evolution_spec(_writer("wagner"), candidate, 3, smoke=True)
    run = run_lineage_evolution(spec, tmp_path / "evolution", 2)
    verified = verify_lineage_evolution(run)
    assert verified["populations"] == 3
    analysis = read_json(run / "analysis.json")
    assert analysis["claim_boundary"].startswith("exploratory")
    assert analysis["parent_offspring_association"]["pairs"] == 1


def test_parent_offspring_interval_is_paired_and_positive() -> None:
    candidate = replace(carrier_grid()[0], engines=("wagner",))
    spec = replace(
        evolution_spec(_writer("wagner"), candidate, 3, smoke=True),
        bootstrap_repetitions=256,
    )
    interval = _correlation_interval(
        [0.05, 0.20, 0.35, 0.55, 0.70, 0.90],
        [0.10, 0.18, 0.40, 0.50, 0.75, 0.88],
        spec,
    )
    assert interval["mean"] > 0.95
    assert interval["lower"] > 0.0
