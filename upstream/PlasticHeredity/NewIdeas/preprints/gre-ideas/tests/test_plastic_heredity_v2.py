from __future__ import annotations

from dataclasses import replace

from gre_sim.artifacts import read_json, read_jsonl_gz
from gre_sim.plastic_heredity_v2_atlas import analyze_atlas_run
from gre_sim.plastic_heredity_v2_carriers import (
    replay_carrier_future,
    run_carrier_study,
    verify_carrier_study,
)
from gre_sim.plastic_heredity_v2_config import PlasticHeredityV2Spec
from gre_sim.plastic_heredity_v2_evolution import (
    run_v2_evolution,
    verify_v2_evolution,
)
from gre_sim.plastic_heredity_v2_protocols import (
    carrier_calibration_spec,
    carrier_grid,
    exact_state_confirmation_spec,
    exact_state_discovery_spec,
    exact_state_fixture_spec,
    mechanism_atlas_specs,
    natural_cue_state_spec,
    prospective_evolution_spec,
)
from gre_sim.plastic_heredity_v2_study import (
    replay_v2_state_future,
    run_v2_state_study,
    verify_v2_state_study,
)
from gre_sim.plastic_memory_campaign import expected_memory_source_futures
from gre_sim.plastic_memory_config import CueDose
from gre_sim.plastic_memory_study import run_memory_study


def test_exact_state_protocol_counts_and_roundtrip() -> None:
    discovery = exact_state_discovery_spec()
    restored = PlasticHeredityV2Spec.from_dict(discovery.to_dict())
    assert restored == discovery
    memory = discovery.memory_spec()
    assert expected_memory_source_futures(memory, "boolean_n10") == 13_312
    assert sum(
        source.count * expected_memory_source_futures(memory, source.name)
        for source in memory.sources
    ) == 2_555_904

    confirmation = exact_state_confirmation_spec().memory_spec()
    assert sum(
        source.count * expected_memory_source_futures(confirmation, source.name)
        for source in confirmation.sources
    ) == 6_389_760
    natural_cue_state_spec(
        {"boolean": CueDose(0.5, 4), "wagner": CueDose(1.0, 1)}, False
    ).validate()


def test_quick_v2_state_study_verifies_and_replays(tmp_path) -> None:
    run = run_v2_state_study(exact_state_fixture_spec(), tmp_path / "state", 1)
    verification = verify_v2_state_study(run)
    assert verification["verified"]
    analysis = read_json(run / "analysis.json")
    assert set(analysis["engine_comparison_inputs"]) == {"boolean", "wagner"}
    archived = next(read_jsonl_gz(run / "executor" / "futures.jsonl.gz"))
    replay = replay_v2_state_future(run, archived["future_id"])
    assert replay["matches"]


def test_engine_neutral_carrier_smoke_verifies_and_replays(tmp_path) -> None:
    spec = carrier_calibration_spec()
    spec = replace(
        spec,
        source_count_per_engine=1,
        carriers=carrier_grid()[:3],
        futures_per_cell=4,
        genes=4,
        midpoint_count=1,
        horizon=12,
        strict_run=2,
        stable_run=2,
        bootstrap_repetitions=64,
    )
    run = run_carrier_study(spec, tmp_path / "carriers", 1)
    assert verify_carrier_study(run)["verified"]
    archived = next(read_jsonl_gz(run / "futures.jsonl.gz"))
    assert replay_carrier_future(run, archived["future_id"])["matches"]


def test_mechanism_atlas_records_geometry_and_paired_candidates(tmp_path) -> None:
    spec = mechanism_atlas_specs(1)[0]
    spec = replace(
        spec,
        sources=tuple(replace(source, count=1, genes=4) for source in spec.sources),
        conditions=tuple(
            replace(
                condition,
                washout_ages=(0,),
                challenges=("neutral_damage",),
                futures_per_cell=4,
            )
            for condition in spec.conditions
        ),
        horizon=12,
        strict_run=2,
        stable_run=2,
        minimum_basin_fraction=0.0,
        minimum_form_distance=0.25,
        bootstrap_repetitions=64,
    )
    run = run_memory_study(spec, tmp_path / "atlas", 1)
    analysis = analyze_atlas_run(run)
    assert analysis["geometry"]
    assert "boolean.sequential" in analysis["candidate_contrasts"]
    assert analysis["compiled_wagner_boolean_role"].startswith("pathwise fixture")


def test_prospective_evolution_uses_one_common_heldout_endpoint(tmp_path) -> None:
    spec = prospective_evolution_spec(str(tmp_path), False)
    spec = replace(
        spec,
        populations_per_treatment=1,
        population_size=4,
        generations=1,
        training_replicates=1,
        selection_replicates=2,
        heldout_replicates=4,
        genes=4,
        post_horizon=4,
        hold_run=2,
    )
    run = run_v2_evolution(spec, tmp_path / "evolution", 1)
    assert verify_v2_evolution(run)["verified"]
    analysis = read_json(run / "analysis.json")
    assert set(analysis["endpoint_separation"]["selection"].values()) == {
        "descendant_memory",
        "cue_only",
        "neutral",
    }
    assert (
        analysis["endpoint_separation"]["heldout_for_all_treatments"]
        == "descendant_memory"
    )
