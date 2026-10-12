from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from gre_sim.artifacts import read_json, write_jsonl_gz
from gre_sim.local_ph_config import LocalCarrierGenome, intervention_locus
from gre_sim.wagner_ph_bridge_analysis import analyze_precision_path, icc_2_1
from gre_sim.wagner_ph_bridge_evolution import (
    replay_coevolution_population,
    resource_cost,
    run_bridge_coevolution,
    verify_bridge_coevolution,
)
from gre_sim.wagner_ph_bridge_protocols import (
    bridge_campaign_spec,
    causal_confirmation_spec,
    frozen_candidate_family,
)


def _prior_selection() -> dict:
    return read_json(Path("runs/wagner-local-ph-v1/search/selection.json"))


def test_bridge_contract_has_frozen_sizes_and_eight_hour_boundary() -> None:
    spec = bridge_campaign_spec(_prior_selection())
    assert len(frozen_candidate_family(_prior_selection())) == 6
    assert len(spec.precision.study.conditions) == 8
    assert len(spec.phase_diagram.cells) == 30
    assert len(spec.phase_diagram.screening.conditions) == 30
    assert spec.coevolution_template.population_count == 32
    assert spec.maximum_workers == 4
    assert spec.hard_wall_seconds == 28_800
    assert sum(spec.stage_reservations_seconds) == 28_800


def _precision_rows(spec, stable: bool) -> list[dict]:
    rows = []
    for source_index in range(2):
        source = f"source-{source_index}"
        for condition in spec.study.conditions:
            for history in ("A", "B"):
                for future in range(spec.study.futures_per_history):
                    block = future // spec.reliability.block_size
                    if condition.name == "zero":
                        correct = 0 if stable or block == 0 else 1
                    elif condition.name == "perfect-latch":
                        correct = 1
                    else:
                        correct = 1 if stable or block == 0 else 0
                    rows.append(
                        {
                            "future_id": f"{source}.{condition.name}.{history}.{future}",
                            "source_id": source,
                            "condition": condition.name,
                            "generation": 4,
                            "challenge": "forced_break",
                            "history": history,
                            "future_index": future,
                            "half": "A" if future < spec.study.futures_per_history // 2 else "B",
                            "correct_hold8": correct,
                            "wrong_hold8": 1 - correct,
                            "returned": correct,
                            "acquired": True,
                        }
                    )
    return rows


def test_precision_gate_handles_saturation_without_requiring_pearson(tmp_path) -> None:
    spec = bridge_campaign_spec(_prior_selection(), smoke=True).precision
    stable_path = tmp_path / "stable.jsonl.gz"
    write_jsonl_gz(stable_path, _precision_rows(spec, True))
    stable = analyze_precision_path(stable_path, spec)
    assert stable["verdict"]["repeatable_local_effect"]
    first = next(iter(stable["candidates"].values()))
    assert first["mean_raw_absolute_rate_pearson"] is None
    assert first["stable_effect"]

    unstable_path = tmp_path / "unstable.jsonl.gz"
    write_jsonl_gz(unstable_path, _precision_rows(spec, False))
    unstable = analyze_precision_path(unstable_path, spec)
    assert not unstable["verdict"]["repeatable_local_effect"]


def test_icc_reports_variable_agreement_and_not_constant_saturation() -> None:
    assert icc_2_1([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]]) == 1.0
    assert icc_2_1([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]]) is None


def test_causal_protocol_has_single_locus_lesions_and_k10_gate_is_applicable_safe() -> None:
    campaign = bridge_campaign_spec(_prior_selection(), smoke=True)
    nominees = (
        campaign.phase_diagram.screening.genomes[0],
        campaign.phase_diagram.screening.genomes[5],
    )
    causal = causal_confirmation_spec(campaign.phase_diagram, nominees, smoke=True)
    assert len(causal.conditions) == 42
    assert intervention_locus("ablate_locus_0_g2", 10) == 0
    assert intervention_locus("ablate_locus_9_g2", 10) == 9
    assert nominees[1].k == 10


def test_coevolution_smoke_seals_and_replays_without_carrier_target_label(tmp_path) -> None:
    spec = bridge_campaign_spec(_prior_selection(), smoke=True).coevolution_template
    assert resource_cost(spec.initial_carrier, spec) <= 0.10
    run = run_bridge_coevolution(spec, tmp_path / "coevolution", workers=1)
    assert verify_bridge_coevolution(run)["populations"] == 4
    population = read_json(
        run / "populations" / "descendant_memory_cost.population-000.json"
    )
    assert population["selection_uses_target_label_inside_carrier"] is False
    assert population["common_heldout_source_id"] == "heldout.population-000"
    replay = replay_coevolution_population(
        run, "descendant_memory_cost.population-000"
    )
    assert replay["matches"]
