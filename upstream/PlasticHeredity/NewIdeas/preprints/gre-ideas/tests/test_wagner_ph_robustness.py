from __future__ import annotations

from pathlib import Path

import numpy as np

from gre_sim.artifacts import canonical_digest
from gre_sim.rng import rng_for
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_ph_cooption_evolution import (
    founder_carrier,
    mutate_genotype,
    serialize_genotype,
)
from gre_sim.wagner_ph_cooption_experiment import sample_cooption_task
from gre_sim.wagner_ph_robustness_campaign import wagner_ph_robustness_status
from gre_sim.wagner_ph_robustness_config import (
    AUTOPSY_COMPONENTS,
    ROBUSTNESS_ARMS,
    arm_settings,
    robustness_spec,
)
from gre_sim.wagner_ph_robustness_evolution import robustness_score
from gre_sim.wagner_ph_robustness_mechanisms import (
    hybrid_genotype,
    initialize_for_arm,
    mutate_for_arm,
)


def _founder() -> tuple[WagnerRulebook, object]:
    return WagnerRulebook.constant(10, 0), founder_carrier()


def test_robustness_contract_fixes_counts_seeds_and_four_hour_boundary() -> None:
    spec = robustness_spec()
    assert spec.arms == ROBUSTNESS_ARMS
    assert spec.autopsy_components == AUTOPSY_COMPONENTS
    assert spec.population_count == 96
    assert spec.pedigree_descendant_count == 1152
    assert spec.generations == 24
    assert spec.virtual_offspring == 3
    assert spec.maximum_workers == 4
    assert spec.hard_wall_seconds == 14_400
    assert spec.soft_wall_seconds == 13_500
    assert spec.stage_reservations_seconds == (1800, 7500, 2400, 1500, 300)
    assert sum(spec.stage_reservations_seconds) == spec.soft_wall_seconds
    assert len(
        {
            spec.master_seed,
            spec.autopsy_seed,
            spec.audit_seed,
            spec.pedigree_seed,
            spec.unused_confirmation_seed,
        }
    ) == 5
    assert spec.evidence_strategy == "develop_then_confirm"


def test_arm_pairs_change_selection_without_changing_mutation_family() -> None:
    assert arm_settings("individual_independent")["selection_mode"] == "individual"
    assert arm_settings("offspring_independent")["selection_mode"] == "offspring"
    assert arm_settings("individual_protected")["carrier_mutation_multiplier"] == 0.25
    assert arm_settings("offspring_protected")["carrier_mutation_multiplier"] == 0.25
    assert arm_settings("individual_linked")["mutation_architecture"] == "linked"
    assert arm_settings("offspring_linked")["mutation_architecture"] == "linked"
    assert arm_settings("offspring_fixed_k1")["carrier_constraint"] == "fixed_k1"
    assert arm_settings("offspring_inert")["carrier_constraint"] == "inert"


def test_ordinary_arm_preserves_the_archived_mutation_operator_exactly() -> None:
    founder = _founder()
    left = mutate_genotype(
        founder, founder, "independent", np.random.default_rng(11)
    )
    right = mutate_genotype(
        founder, founder, "independent", np.random.default_rng(12)
    )
    archived = mutate_genotype(
        left, right, "independent", np.random.default_rng(99)
    )
    robustness = mutate_for_arm(
        left, right, "individual_independent", np.random.default_rng(99)
    )
    assert canonical_digest(serialize_genotype(*archived)) == canonical_digest(
        serialize_genotype(*robustness)
    )


def test_linked_and_negative_control_initialization_is_structural() -> None:
    founder = _founder()
    varied = mutate_genotype(
        founder, founder, "independent", np.random.default_rng(7)
    )
    linked = initialize_for_arm(varied, "individual_linked")[1]
    assert linked.write_rate == linked.coupling
    fixed = initialize_for_arm(varied, "offspring_fixed_k1")[1]
    assert fixed.k == 1 and fixed.bits_per_mark == 2 and fixed.topology != "all"
    inert = initialize_for_arm(varied, "offspring_inert")[1]
    assert inert.write_rate == inert.coupling == 0.0


def test_factorial_hybrids_have_all_16_masks_and_exact_corners() -> None:
    parent = _founder()
    descendant = mutate_genotype(
        parent, parent, "independent", np.random.default_rng(123)
    )
    hybrids = [hybrid_genotype(parent, descendant, mask) for mask in range(16)]
    assert len({canonical_digest(serialize_genotype(*value)) for value in hybrids}) >= 2
    assert canonical_digest(serialize_genotype(*hybrids[0])) == canonical_digest(
        serialize_genotype(*parent)
    )
    assert canonical_digest(serialize_genotype(*hybrids[15])) == canonical_digest(
        serialize_genotype(*descendant)
    )


def test_offspring_fitness_contains_only_performance_cost_and_replays() -> None:
    spec = robustness_spec(smoke=True)
    kernel = spec.kernel()
    task = sample_cooption_task(kernel, 0, "robustness-unit", master_seed=spec.master_seed)
    genotype = (
        WagnerRulebook.from_dict(task["founder"]),
        founder_carrier(),
    )
    first = robustness_score(
        genotype, task, kernel, spec, "offspring_independent", 0, 1
    )
    second = robustness_score(
        genotype, task, kernel, spec, "offspring_independent", 0, 1
    )
    assert first == second
    assert first["selection_mode"] == "offspring"
    assert first["virtual_offspring_count"] == 1
    assert first["fitness_contains_memory_information_or_intervention_metric"] is False
    assert all(
        set(value) == {
            "child_index",
            "genotype_id",
            "fitness",
            "performance",
            "resource_cost",
        }
        for value in first["virtual_offspring"]
    )


def test_semantic_mutation_streams_are_worker_order_independent() -> None:
    spec = robustness_spec(smoke=True)
    genotype = _founder()
    coordinates = ("family", 0, 2, "token", 0)
    left = mutate_for_arm(
        genotype,
        genotype,
        "offspring_independent",
        rng_for(spec.master_seed, "robustness-virtual-offspring", *coordinates),
    )
    right = mutate_for_arm(
        genotype,
        genotype,
        "offspring_independent",
        rng_for(spec.master_seed, "robustness-virtual-offspring", *coordinates),
    )
    assert serialize_genotype(*left) == serialize_genotype(*right)


def test_status_is_read_only_and_detached_runner_has_all_guards(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_robustness_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path("scripts/run-wagner-ph-robustness-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-robustness.sh").read_text()
    assert "maximum_wall_seconds=14400" in runner
    assert "soft_wall_seconds=13500" in runner
    assert "maximum_start_load=18" in runner
    assert "minimum_available_kib=10485760" in runner
    assert "minimum_free_disk_kib=10485760" in runner
    assert 'workers must lie in [1, 4]' in runner
    assert "waiting-for-resources" in runner
    assert "GRE_WAGNER_PH_ROBUSTNESS_SOFT_DEADLINE_EPOCH" in runner
    assert "GRE_WAGNER_PH_ROBUSTNESS_PRIOR_CONSUMED_SECONDS" in runner
    assert "kill -KILL" in runner
    assert "heartbeat age" in status
