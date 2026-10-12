from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gre_sim.artifacts import canonical_digest
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_ph_cooption_evolution import founder_carrier
from gre_sim.wagner_ph_cooption_experiment import sample_cooption_task
from gre_sim.wagner_ph_maintenance_campaign import (
    confirmation_arms,
    run_wagner_ph_maintenance_confirmation,
    wagner_ph_maintenance_status,
)
from gre_sim.wagner_ph_maintenance_config import (
    DEVELOPMENT_ARMS,
    arm_settings,
    evidence_tier,
    maintenance_spec,
)
from gre_sim.wagner_ph_maintenance_evidence import pedigree_modes
from gre_sim.wagner_ph_maintenance_evolution import maintenance_score
from gre_sim.wagner_ph_maintenance_genome import (
    MaintenanceInterpreter,
    architecture_cost,
    deserialize_genome,
    effective_genotype,
    initialize_interpreter,
    mutate_genome,
    serialize_genome,
)


def _genome(architecture: str, spec, *, seeded: bool = False):
    rulebook = WagnerRulebook.random(10, np.random.default_rng(4))
    return initialize_interpreter(rulebook, architecture, spec, seeded=seeded), founder_carrier()


def test_maintenance_contract_fixes_factorial_f12_and_split_wall_budgets() -> None:
    spec = maintenance_spec()
    assert spec.arms == DEVELOPMENT_ARMS and len(spec.arms) == 10
    assert len(spec.arms) * spec.task_count == 160
    assert (spec.population_size, spec.generations) == (16, 30)
    assert spec.lineage_checkpoints == (1, 4, 12)
    assert spec.maximum_workers == 4
    assert (spec.hard_wall_seconds, spec.soft_wall_seconds) == (28800, 27600)
    assert sum(spec.stage_reservations_seconds) == 26400
    assert spec.soft_wall_seconds - sum(spec.stage_reservations_seconds) == 1200
    assert (spec.confirmation_hard_wall_seconds, spec.confirmation_soft_wall_seconds) == (14400, 13500)
    assert sum(spec.confirmation_stage_reservations_seconds) == 13500


def test_arms_and_evidence_tiers_keep_emergence_separate_from_engineering() -> None:
    assert arm_settings("mh_node_repair_zero_rho90") == {
        "selection_mode": "multihorizon",
        "architecture": "node_repair",
        "initialization": "zero",
        "predictive_persistence": 0.9,
    }
    assert evidence_tier("mh_node_repair_zero_rho90") == "dormant_start_maintenance"
    assert evidence_tier("mh_global_seeded_rho90") == "engineered_sufficiency"
    assert pedigree_modes("mh_node_repair_zero_rho90") == (
        "natural",
        "repair_off",
        "uniform_repair",
        "shuffled_repair",
    )
    assert confirmation_arms(("mh_node_repair_zero_rho90", "mh_global_seeded_rho90")) == (
        "individual_single_rho90",
        "mh_single_rho90",
        "mh_node_repair_zero_rho50",
        "mh_node_repair_zero_rho90",
        "individual_global_seeded_rho90",
        "mh_global_seeded_rho90",
    )


def test_node_local_repair_attenuates_target_rows_and_round_trips() -> None:
    spec = maintenance_spec(smoke=True)
    base = _genome("node_repair", spec)
    protected = (
        MaintenanceInterpreter(
            base[0].copies,
            "node_repair",
            node_repair=(0.9,) * base[0].copies[0].genes,
        ),
        base[1],
    )
    natural = mutate_genome(
        protected, protected, "mh_node_repair_zero_rho90", np.random.default_rng(18), spec
    )
    repair_off = mutate_genome(
        protected,
        protected,
        "mh_node_repair_zero_rho90",
        np.random.default_rng(18),
        spec,
        mechanism="repair_off",
    )
    natural_l2 = np.linalg.norm(natural[0].copies[0].weights - protected[0].copies[0].weights)
    off_l2 = np.linalg.norm(repair_off[0].copies[0].weights - protected[0].copies[0].weights)
    assert natural_l2 < off_l2
    assert architecture_cost(protected[0], spec) == pytest.approx(spec.repair_cost * 0.9)
    archived = serialize_genome(natural)
    assert serialize_genome(deserialize_genome(archived)) == archived


def test_median_decoder_rejects_an_outlying_copy() -> None:
    spec = maintenance_spec(smoke=True)
    base = WagnerRulebook.random(10, np.random.default_rng(7))
    values = []
    for number in (-1.0, 0.5, 20.0):
        weights = base.weights.copy()
        weights[2, 7] = number
        values.append(WagnerRulebook(weights, base.bias, base.order))
    median = MaintenanceInterpreter(tuple(values), "median3", decoder="median")
    mean = MaintenanceInterpreter(tuple(values), "median3", decoder="mean")
    assert median.effective_rulebook().weights[2, 7] == 0.5
    assert mean.effective_rulebook().weights[2, 7] == 6.5
    assert architecture_cost(median, spec) == 2 * spec.extra_copy_cost


def test_duplication_is_deterministic_and_bounded_between_one_and_three_copies() -> None:
    spec = maintenance_spec(smoke=True)
    genome = _genome("duplication", spec)
    first = mutate_genome(
        genome, genome, "mh_duplication_zero_rho90", np.random.default_rng(9), spec
    )
    second = mutate_genome(
        genome, genome, "mh_duplication_zero_rho90", np.random.default_rng(9), spec
    )
    assert serialize_genome(first) == serialize_genome(second)
    assert 1 <= first[0].copy_count <= 3
    assert effective_genotype(first)[0].genes == 10


def test_multihorizon_score_is_replayable_and_contains_no_ph_measurement() -> None:
    spec = maintenance_spec(smoke=True)
    kernel = spec.kernel()
    task = sample_cooption_task(kernel, 0, "maintenance-unit", master_seed=spec.master_seed)
    genome = (
        initialize_interpreter(WagnerRulebook.from_dict(task["founder"]), "single", spec),
        founder_carrier(),
    )
    first = maintenance_score(
        genome, task, kernel, spec, "mh_single_rho90", 0, 1, "development"
    )
    second = maintenance_score(
        genome, task, kernel, spec, "mh_single_rho90", 0, 1, "development"
    )
    assert canonical_digest(first) == canonical_digest(second)
    assert len(first["virtual_descendants"]) == spec.lineage_count
    assert all(len(value["chain"]) == spec.lineage_depth for value in first["virtual_descendants"])
    assert first["fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric"] is False


def test_confirmation_requires_explicit_authorization_before_any_output(tmp_path: Path) -> None:
    development = tmp_path / "missing-development"
    output = tmp_path / "confirmation"
    with pytest.raises(PermissionError, match="explicit"):
        run_wagner_ph_maintenance_confirmation(development, output)
    assert not output.exists()


def test_status_is_read_only_and_runner_has_shared_host_guards(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_maintenance_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path("scripts/run-wagner-ph-adaptive-maintenance-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-adaptive-maintenance.sh").read_text()
    for text in (
        "maximum_wall_seconds=28800",
        "soft_wall_seconds=27600",
        "maximum_wall_seconds=14400",
        "soft_wall_seconds=13500",
        "maximum_start_load=18",
        "minimum_available_kib=10485760",
        "minimum_free_disk_kib=10485760",
        "workers must lie in [1, 4]",
        "GRE_WAGNER_PH_MAINTENANCE_SOFT_DEADLINE_EPOCH",
        "GRE_WAGNER_PH_MAINTENANCE_PRIOR_CONSUMED_SECONDS",
        "OPENBLAS_NUM_THREADS=1",
        "CUDA_VISIBLE_DEVICES",
        "kill -KILL",
    ):
        assert text in runner
    assert "heartbeat age" in status
