from __future__ import annotations

from pathlib import Path

import numpy as np

from gre_sim.wagner_ph_cooption_analysis import analyze_audit_results
from gre_sim.wagner_ph_cooption_campaign import wagner_ph_cooption_status
from gre_sim.wagner_ph_cooption_config import QuantizedCarrierGenome, treatment_selection_phase
from gre_sim.wagner_ph_cooption_evolution import (
    founder_carrier,
    mutate_carrier,
    training_panel_indices,
)
from gre_sim.wagner_ph_cooption_experiment import (
    anchor_carriers,
    carrier_resource_cost,
    sample_cooption_task,
    simulate_ecology_condition,
)
from gre_sim.wagner_ph_cooption_protocols import wagner_ph_cooption_spec
from gre_sim.wagner import WagnerRulebook


def test_contract_separates_six_hour_exploration_and_four_hour_confirmation() -> None:
    spec = wagner_ph_cooption_spec()
    assert spec.atlas_tasks == 24
    assert spec.population_count == 40
    assert spec.population_size == 16
    assert spec.generations == 30
    assert spec.cooption_switch_generation == 15
    assert spec.hard_wall_seconds == 21_600
    assert spec.soft_wall_seconds == 20_400
    assert sum(spec.stage_reservations_seconds) == spec.soft_wall_seconds
    assert spec.confirmation_tasks == 6
    assert spec.confirmation_hard_wall_seconds == 14_400
    assert spec.master_seed != spec.confirmation_seed
    assert treatment_selection_phase("cooption_independent", 15, 15) == "homeostasis"
    assert treatment_selection_phase("cooption_independent", 16, 15) == "predictive"
    assert treatment_selection_phase("direct_independent", 1, 15) == "predictive"
    assert treatment_selection_phase("robustness_only_independent", 30, 15) == "homeostasis"


def test_quantized_cost_is_monotone_and_exactly_capped() -> None:
    spec = wagner_ph_cooption_spec()
    low = founder_carrier()
    middle = QuantizedCarrierGenome("middle", 0.5, 0.1, 0.5, 2, "outgoing", 5, 4)
    high = QuantizedCarrierGenome("high", 1.0, 0.0, 1.0, 3, "all", 10, 8)
    assert carrier_resource_cost(low, spec) < carrier_resource_cost(middle, spec)
    assert carrier_resource_cost(middle, spec) < carrier_resource_cost(high, spec)
    assert abs(carrier_resource_cost(high, spec) - 0.10) < 1e-12
    assert anchor_carriers()[0].payload_upper_bits == 10
    assert anchor_carriers()[1].payload_upper_bits == 80


def test_mutation_architectures_encode_the_registered_accessibility_hypotheses() -> None:
    founder = founder_carrier()
    independent = [
        mutate_carrier(founder, founder, "independent", np.random.default_rng(seed))
        for seed in range(200)
    ]
    assert any((value.write_rate > 0.0) != (value.coupling > 0.0) for value in independent)
    linked = [
        mutate_carrier(founder, founder, "linked", np.random.default_rng(seed))
        for seed in range(200)
    ]
    assert all(value.write_rate == value.coupling for value in linked)
    ramp = [
        mutate_carrier(founder, founder, "linked_ramp", np.random.default_rng(seed))
        for seed in range(200)
    ]
    assert all(value.write_rate == value.coupling for value in ramp)
    assert {value.k for value in ramp} <= {1, 2}
    assert {value.bits_per_mark for value in ramp} <= {2, 4}


def test_training_panel_rotation_covers_every_stream_without_resampling() -> None:
    spec = wagner_ph_cooption_spec()
    blocks = [training_panel_indices(generation, spec) for generation in range(4)]
    assert sorted(value for block in blocks for value in block) == list(range(16))
    assert training_panel_indices(4, spec) == blocks[0]


def test_precue_task_and_independent_donor_are_replayable_and_balanced() -> None:
    spec = wagner_ph_cooption_spec(smoke=True)
    task = sample_cooption_task(spec, 0, "unit")
    assert task == sample_cooption_task(spec, 0, "unit")
    assert task["neutral_pre_cue_state_is_shared_between_histories"] is True
    result = simulate_ecology_condition(
        WagnerRulebook.from_dict(task["founder"]),
        task,
        anchor_carriers()[0],
        spec,
        "independent_history",
        0.9,
        0.0,
        4,
        2,
        (1, 2),
        "unit",
    )
    rows = result["final_carriers"]
    paired = {}
    for row in rows:
        paired.setdefault(int(row["future_index"]), set()).add(row["donor_history"])
    assert all(len(values) == 1 for values in paired.values())
    assert {row["donor_history"] for row in rows} == {"A", "B"}


def _condition(correct: float, wrong: float, functional: float | None = None) -> dict:
    values = {
        "correct_rate": correct,
        "wrong_rate": wrong,
        "functional_rate": correct + wrong if functional is None else functional,
        "returned_rate": correct,
        "convergence_cycle": 1.0,
        "mean_development_steps": 1.0,
        "carrier_norm": 0.5,
        "nonzero_marks": 5.0,
        "observations": 32,
    }
    return {"1": dict(values), "8": dict(values), "16": dict(values)}


def _fake_population(treatment: str, index: int, cooption: bool) -> dict:
    high_information = 0.60 if cooption else 0.20
    independent = 0.30
    high_natural = independent + high_information
    low_natural = 0.10

    def cell(rho: float) -> dict:
        natural = high_natural if rho == 0.9 else low_natural
        return {
            "persistence": rho,
            "cue_fraction": 0.0,
            "conditions": {
                "natural": {"checkpoints": _condition(natural, 0.0)},
                "independent_history": {"checkpoints": _condition(independent, 0.20, 0.80)},
                "opposite_history": {"checkpoints": _condition(0.05, 0.85)},
                "zero": {"checkpoints": _condition(0.05, 0.05, 0.10)},
                "reader_off": {"checkpoints": _condition(0.05, 0.05)},
                "renewal_off": {"checkpoints": _condition(0.10, 0.05)},
                "founder_write_off": {"checkpoints": _condition(0.05, 0.05)},
                "shuffle": {"checkpoints": _condition(0.20, 0.20)},
            },
            "history_information": {
                "decoder_balanced_accuracy": 0.90 if cooption else 0.60,
                "mean_locus_mutual_information_bits": 0.30,
            },
        }

    return {
        "population_id": f"{treatment}.population-{index:03d}",
        "population_index": index,
        "treatment": treatment,
        "selected_training_score": {"performance": high_natural},
        "cells": [cell(0.0), cell(0.9)],
    }


def test_analysis_does_not_mistake_generic_stabilization_for_inherited_information() -> None:
    spec = wagner_ph_cooption_spec()
    results = []
    for index in range(5):
        results.append(_fake_population("cooption_independent", index, True))
        results.append(_fake_population("direct_independent", index, False))
    analysis = analyze_audit_results(results, spec)
    assert analysis["tiers"]["A"]["passes"] is True
    assert analysis["nomination"]["treatment"] == "cooption_independent"
    assert analysis["confirmation_reserve"]["rng_draws_consumed"] == 0

    generic_only = []
    for index in range(5):
        left = _fake_population("cooption_independent", index, True)
        right = _fake_population("direct_independent", index, False)
        for population in (left, right):
            high = next(value for value in population["cells"] if value["persistence"] == 0.9)
            high["conditions"]["natural"] = high["conditions"]["independent_history"]
        generic_only.extend((left, right))
    rejected = analyze_audit_results(generic_only, spec)
    assert rejected["tiers"]["A"]["passes"] is False
    assert rejected["nomination"] is None


def test_status_is_read_only_and_detached_runner_has_shared_host_guards(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_cooption_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path("scripts/run-wagner-ph-cooption-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-cooption.sh").read_text()
    assert "maximum_wall_seconds=21600" in runner
    assert "soft_wall_seconds=20400" in runner
    assert "maximum_start_load=18" in runner
    assert "waiting-for-load" in runner
    assert "GRE_WAGNER_PH_COOPTION_SOFT_DEADLINE_EPOCH" in runner
    assert "GRE_WAGNER_PH_COOPTION_PRIOR_CONSUMED_SECONDS" in runner
    assert "kill -KILL" in runner
    assert "heartbeat age" in status
    confirmation = Path(
        "scripts/run-wagner-ph-cooption-confirmation-detached.sh"
    ).read_text()
    assert "maximum_wall_seconds=14400" in confirmation
    assert "soft_wall_seconds=13500" in confirmation
    assert "--authorize-confirmation" in confirmation
