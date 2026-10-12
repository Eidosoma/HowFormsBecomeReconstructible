from __future__ import annotations

from pathlib import Path

from gre_sim.artifacts import read_json
from gre_sim.wagner_ph_cooption_evolution import (
    constrain_carrier,
    founder_carrier,
    replay_cooption_population,
    run_cooption_evolution,
    verify_cooption_evolution,
)
from gre_sim.wagner_ph_direct_campaign import wagner_ph_direct_prediction_status
from gre_sim.wagner_ph_direct_config import (
    DIRECT_VARIANTS,
    direct_prediction_spec,
    variant_settings,
)


def test_direct_prediction_contract_is_fresh_paired_and_four_worker_capped() -> None:
    spec = direct_prediction_spec()
    assert spec.variants == DIRECT_VARIANTS
    assert spec.task_count == 12
    assert spec.population_count == 108
    assert spec.descendant_count == 144
    assert spec.maximum_workers == 4
    assert spec.hard_wall_seconds == 14_400
    assert spec.soft_wall_seconds == 13_500
    assert sum(spec.stage_reservations_seconds) == spec.soft_wall_seconds
    assert len(
        {
            spec.master_seed,
            spec.emergence_seed,
            spec.pedigree_seed,
            spec.unused_confirmation_seed,
        }
    ) == 4
    kernel = spec.cooption_spec()
    assert kernel.audit_persistence == (0.0, 0.5, 0.75, 0.9, 1.0)
    assert kernel.maximum_workers == 4


def test_variants_form_predictability_and_component_controls() -> None:
    assert [variant_settings(name)["predictive_persistence"] for name in DIRECT_VARIANTS[:4]] == [
        0.5,
        0.75,
        0.9,
        1.0,
    ]
    assert variant_settings("rho90_inert")["carrier_constraint"] == "inert"
    assert variant_settings("rho90_writer_only")["carrier_constraint"] == "writer_only"
    assert variant_settings("rho90_reader_only")["carrier_constraint"] == "reader_only"
    assert variant_settings("rho90_fixed_k1")["carrier_constraint"] == "fixed_k1"
    assert variant_settings("rho90_cost2")["resource_cost_multiplier"] == 2.0


def test_carrier_constraints_are_structural_and_idempotent() -> None:
    carrier = founder_carrier()
    inert = constrain_carrier(carrier, "inert")
    assert inert.write_rate == inert.coupling == 0.0
    assert inert.k == 1 and inert.bits_per_mark == 2
    assert constrain_carrier(inert, "inert").to_dict() == inert.to_dict()
    writer = constrain_carrier(carrier, "writer_only")
    assert writer.coupling == 0.0
    reader = constrain_carrier(carrier, "reader_only")
    assert reader.write_rate == 0.0
    small = constrain_carrier(carrier, "fixed_k1")
    assert small.k == 1 and small.bits_per_mark == 2


def test_selection_settings_are_registered_verified_and_replayed(tmp_path: Path) -> None:
    spec = direct_prediction_spec(smoke=True).cooption_spec()
    output = tmp_path / "controlled-evolution"
    run_cooption_evolution(
        spec,
        output,
        workers=1,
        treatments=("direct_independent",),
        task_count=1,
        master_seed=spec.master_seed,
        carrier_constraint="writer_only",
        predictive_persistence=0.75,
        resource_cost_multiplier=2.0,
    )
    assert verify_cooption_evolution(output)["verified"] is True
    registration = read_json(output / "registration.json")
    assert registration["selection_settings"] == {
        "carrier_constraint": "writer_only",
        "predictive_persistence": 0.75,
        "resource_cost_multiplier": 2.0,
    }
    population = read_json(
        output / "populations" / "direct_independent.population-000.json"
    )
    assert all(value["carrier"]["coupling"] == 0.0 for value in population["final_population"])
    assert replay_cooption_population(
        output, "direct_independent.population-000"
    )["matches"] is True


def test_direct_status_is_read_only_and_runner_enforces_limits(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_direct_prediction_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path("scripts/run-wagner-ph-direct-prediction-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-direct-prediction.sh").read_text()
    assert "maximum_wall_seconds=14400" in runner
    assert "soft_wall_seconds=13500" in runner
    assert "maximum_start_load=18" in runner
    assert 'workers must lie in [1, 4]' in runner
    assert "waiting-for-load" in runner
    assert "GRE_WAGNER_PH_DIRECT_SOFT_DEADLINE_EPOCH" in runner
    assert "kill -KILL" in runner
    assert "heartbeat age" in status
