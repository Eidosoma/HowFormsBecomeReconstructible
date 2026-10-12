from __future__ import annotations

from pathlib import Path

import numpy as np

from gre_sim.artifacts import canonical_digest
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_ph_cooption_evolution import founder_carrier, run_cooption_evolution
from gre_sim.wagner_ph_cooption_experiment import sample_cooption_task
from gre_sim.wagner_ph_maintenance_genome import MaintenanceInterpreter
from gre_sim.wagner_ph_repair_ratchet_campaign import wagner_ph_repair_ratchet_status
from gre_sim.wagner_ph_repair_ratchet_config import ROUTE_NAMES, repair_ratchet_spec
from gre_sim.wagner_ph_repair_ratchet_evidence import (
    _paired_child,
    run_repair_ratchet_audit,
    run_repair_ratchet_pedigree,
    verify_repair_ratchet_audit,
    verify_repair_ratchet_pedigree,
)
from gre_sim.wagner_ph_repair_ratchet_evolution import (
    replay_repair_ratchet_population,
    route_score,
    run_repair_ratchet_evolution,
    verify_repair_ratchet_evolution,
)


def test_repair_ratchet_contract_freezes_routes_doses_and_budget() -> None:
    spec = repair_ratchet_spec()
    assert tuple(route.name for route in spec.routes) == ROUTE_NAMES
    assert len(spec.routes) * spec.task_count == 128
    assert (spec.population_size, spec.generations) == (16, 40)
    assert spec.dose_scales == (0.0, 0.25, 0.5, 0.75, 1.0)
    assert spec.maximum_workers == 4
    assert (spec.hard_wall_seconds, spec.soft_wall_seconds) == (28800, 27600)
    assert sum(spec.stage_reservations_seconds) == spec.soft_wall_seconds
    assert [route.name for route in spec.routes if route.zero_start] == [
        "repair_zero_standard",
        "repair_zero_lowcost",
        "repair_zero_cost_ramp",
        "repair_zero_variation_pulse",
        "repair_zero_tail8",
    ]


def test_accessibility_routes_return_to_registered_final_conditions() -> None:
    spec = repair_ratchet_spec()
    routes = {route.name: route for route in spec.routes}
    ramp = routes["repair_zero_cost_ramp"]
    assert ramp.repair_cost(0) == 0.0
    assert ramp.repair_cost(10) == 0.02
    assert ramp.repair_cost(20) == ramp.repair_cost(40) == 0.04
    pulse = routes["repair_zero_variation_pulse"]
    assert pulse.repair_mutation_sigma(20) == 0.10
    assert pulse.repair_mutation_sigma(21) == 0.05
    assert routes["repair_zero_tail8"].virtual_lineages == 8
    assert routes["repair_prime005"].zero_start is False


def test_route_score_is_deterministic_and_excludes_ph_measurements() -> None:
    spec = repair_ratchet_spec(smoke=True)
    base = spec.maintenance()
    kernel = base.kernel()
    route = next(value for value in spec.routes if value.name == "repair_zero_tail8")
    task = sample_cooption_task(kernel, 0, "repair-ratchet-unit", master_seed=spec.master_seed)
    genome = (
        MaintenanceInterpreter(
            (WagnerRulebook.from_dict(task["founder"]),),
            "global_repair",
            global_repair=0.2,
        ),
        founder_carrier(),
    )
    first = route_score(genome, task, kernel, base, spec, route, 0, 1)
    second = route_score(genome, task, kernel, base, spec, route, 0, 1)
    assert canonical_digest(first) == canonical_digest(second)
    assert len(first["virtual_descendants"]) == 8
    assert first["fitness_contains_memory_information_intervention_or_ph_metric"] is False


def test_repair_doses_pair_controller_and_carrier_draws() -> None:
    spec = repair_ratchet_spec(smoke=True)
    base = spec.maintenance()
    route = next(value for value in spec.routes if value.name == "repair_seeded080")
    rulebook = WagnerRulebook.random(10, np.random.default_rng(8))
    genome = (
        MaintenanceInterpreter((rulebook,), "global_repair", global_repair=0.8),
        founder_carrier(),
    )
    found_damage = False
    for task_index in range(32):
        natural = _paired_child(
            genome, route, "natural", base, spec.pedigree_seed, task_index, 0, 0, 1
        )
        repair_off = _paired_child(
            genome, route, "repair_off", base, spec.pedigree_seed, task_index, 0, 0, 1
        )
        assert natural[0].global_repair == repair_off[0].global_repair
        assert natural[1].to_dict() == repair_off[1].to_dict()
        natural_damage = np.linalg.norm(natural[0].copies[0].weights - rulebook.weights)
        off_damage = np.linalg.norm(repair_off[0].copies[0].weights - rulebook.weights)
        assert natural_damage <= off_damage + 1e-12
        found_damage = found_damage or off_damage > natural_damage + 1e-12
    assert found_damage


def test_smoke_evolution_audit_pedigree_verify_and_replay(tmp_path: Path) -> None:
    spec = repair_ratchet_spec(smoke=True)
    base = spec.maintenance()
    source = tmp_path / "source"
    run_cooption_evolution(
        base.kernel(),
        source,
        workers=1,
        treatments=("direct_independent",),
        task_count=1,
        master_seed=base.master_seed,
        predictive_persistence=0.9,
    )
    evolution = tmp_path / "evolution"
    audit = tmp_path / "audit"
    pedigree = tmp_path / "pedigree"
    run_repair_ratchet_evolution(spec, source, evolution, workers=1)
    assert verify_repair_ratchet_evolution(evolution)["populations"] == 8
    assert replay_repair_ratchet_population(
        evolution, "repair_zero_standard.population-000"
    )["matches"] is True
    run_repair_ratchet_audit(spec, evolution, audit, workers=1)
    run_repair_ratchet_pedigree(spec, evolution, pedigree, workers=1)
    assert verify_repair_ratchet_audit(audit)["populations"] == 8
    verification = verify_repair_ratchet_pedigree(pedigree)
    assert verification["populations"] == 8
    assert verification["rows"] == 144


def test_status_is_read_only_and_runner_enforces_shared_host_limits(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_repair_ratchet_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path("scripts/run-wagner-ph-repair-ratchet-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-repair-ratchet.sh").read_text()
    for text in (
        "maximum_wall_seconds=28800",
        "soft_wall_seconds=27600",
        "maximum_start_load=18",
        "minimum_available_kib=10485760",
        "minimum_free_disk_kib=10485760",
        "workers must lie in [1, 4]",
        "GRE_WAGNER_PH_REPAIR_RATCHET_SOFT_DEADLINE_EPOCH",
        "GRE_WAGNER_PH_REPAIR_RATCHET_PRIOR_CONSUMED_SECONDS",
        "OPENBLAS_NUM_THREADS=1",
        "CUDA_VISIBLE_DEVICES",
        "kill -KILL",
    ):
        assert text in runner
    assert "heartbeat age" in status
