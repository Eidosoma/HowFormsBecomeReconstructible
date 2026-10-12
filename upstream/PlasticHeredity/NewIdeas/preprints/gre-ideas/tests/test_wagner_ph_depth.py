from __future__ import annotations

from pathlib import Path

import numpy as np

from gre_sim.artifacts import canonical_digest
from gre_sim.rng import rng_for
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_ph_cooption_evolution import founder_carrier, serialize_genotype
from gre_sim.wagner_ph_cooption_experiment import sample_cooption_task
from gre_sim.wagner_ph_depth_analysis import CANDIDATE_ARMS, nominate_candidate
from gre_sim.wagner_ph_depth_campaign import wagner_ph_depth_status
from gre_sim.wagner_ph_depth_config import (
    ATLAS_PERTURBATIONS,
    DEPTH_ARMS,
    arm_settings,
    interpreter_depth_spec,
    matched_control,
)
from gre_sim.wagner_ph_depth_evolution import depth_score
from gre_sim.wagner_ph_depth_mechanisms import (
    mutate_for_arm,
    mutate_wagner_local,
    perturb_edge,
)


def _founder() -> tuple[WagnerRulebook, object]:
    return WagnerRulebook.constant(10, 0), founder_carrier()


def test_interpreter_depth_contract_fixes_counts_and_six_hour_boundary() -> None:
    spec = interpreter_depth_spec()
    assert spec.arms == DEPTH_ARMS
    assert spec.atlas_perturbations == ATLAS_PERTURBATIONS
    assert spec.development_population_count == 72
    assert spec.development_pedigree_rows == 2304
    assert spec.task_count == 12
    assert spec.confirmation_task_count == 16
    assert spec.atlas_edge_limit == 100
    assert spec.generations == 24
    assert spec.confirmation_burnin_generations == 30
    assert spec.maximum_workers == 4
    assert spec.hard_wall_seconds == 21_600
    assert spec.soft_wall_seconds == 20_700
    assert spec.stage_reservations_seconds == (3600, 6000, 3600, 300, 3600, 3000, 600)
    assert sum(spec.stage_reservations_seconds) == spec.soft_wall_seconds
    assert len({spec.master_seed, spec.atlas_seed, spec.audit_seed, spec.pedigree_seed, spec.confirmation_seed}) == 5
    assert spec.evidence_strategy == "develop_then_confirm"


def test_arm_grid_separates_breadth_depth_and_mutation_geometry() -> None:
    assert arm_settings("individual_reset")["selection_mode"] == "individual"
    assert arm_settings("offspring3_reset")["virtual_children"] == 3
    assert arm_settings("offspring8_reset")["virtual_children"] == 8
    lineage = arm_settings("lineage2x2_reset")
    assert lineage["selection_mode"] == "lineage"
    assert lineage["virtual_children"] == 2
    assert lineage["virtual_grandchildren_per_child"] == 2
    assert arm_settings("offspring8_local")["weight_mutation"] == "local"
    assert matched_control("offspring8_local") == "individual_local"
    assert matched_control("lineage2x2_reset") == "individual_reset"


def test_local_wagner_mutation_is_additive_and_replayable() -> None:
    rulebook = WagnerRulebook.random(10, np.random.default_rng(1))
    first = mutate_wagner_local(rulebook, np.random.default_rng(2), sigma=0.1, probability=1.0)
    second = mutate_wagner_local(rulebook, np.random.default_rng(2), sigma=0.1, probability=1.0)
    assert np.array_equal(first.weights, second.weights)
    assert not np.array_equal(first.weights, rulebook.weights)
    assert float(np.max(np.abs(first.weights - rulebook.weights))) < 0.5


def test_atlas_operations_change_exactly_one_registered_edge() -> None:
    rulebook = WagnerRulebook.random(10, np.random.default_rng(4))
    for operation in ATLAS_PERTURBATIONS:
        candidate = perturb_edge(
            rulebook, 3, 7, operation, np.random.default_rng(8), local_sigma=0.1
        )
        changed = np.argwhere(candidate.weights != rulebook.weights)
        if operation == "zero" and rulebook.weights[3, 7] == 0.0:
            assert len(changed) == 0
        else:
            assert changed.tolist() == [[3, 7]]


def test_matched_mutation_streams_replay_and_only_weight_geometry_differs() -> None:
    spec = interpreter_depth_spec(smoke=True)
    genotype = _founder()
    coordinates = ("family", 0, 2, "token", 0)
    first = mutate_for_arm(
        genotype,
        genotype,
        "offspring8_reset",
        rng_for(spec.master_seed, "unit-depth", *coordinates),
        local_sigma=spec.local_weight_sigma,
    )
    second = mutate_for_arm(
        genotype,
        genotype,
        "offspring8_reset",
        rng_for(spec.master_seed, "unit-depth", *coordinates),
        local_sigma=spec.local_weight_sigma,
    )
    assert serialize_genotype(*first) == serialize_genotype(*second)


def test_lineage_fitness_uses_six_descendants_and_no_ph_label() -> None:
    spec = interpreter_depth_spec(smoke=True)
    kernel = spec.kernel()
    task = sample_cooption_task(kernel, 0, "depth-unit", master_seed=spec.master_seed)
    genotype = (WagnerRulebook.from_dict(task["founder"]), founder_carrier())
    first = depth_score(genotype, task, kernel, spec, "lineage2x2_reset", 0, 1)
    second = depth_score(genotype, task, kernel, spec, "lineage2x2_reset", 0, 1)
    assert canonical_digest(first) == canonical_digest(second)
    assert first["selection_mode"] == "lineage"
    assert first["virtual_children"] == 2
    assert first["virtual_grandchildren"] == 4
    assert len(first["virtual_descendants"]) == 6
    assert first["fitness_contains_memory_information_or_intervention_metric"] is False


def test_nomination_prefers_reset_distance_four_then_local_fallback() -> None:
    decisions = {
        name: {
            "passes": False,
            "retention_by_distance": {4: 0.0},
            "absolute_ph": {"information_high_mean": 0.0},
        }
        for name in CANDIDATE_ARMS
    }
    decisions["offspring3_reset"].update(
        passes=True,
        retention_by_distance={4: 0.60},
        absolute_ph={"information_high_mean": 0.4},
    )
    decisions["lineage2x2_reset"].update(
        passes=True,
        retention_by_distance={4: 0.70},
        absolute_ph={"information_high_mean": 0.3},
    )
    decisions["offspring8_local"].update(
        passes=True,
        retention_by_distance={4: 0.90},
        absolute_ph={"information_high_mean": 0.8},
    )
    assert nominate_candidate(decisions)["candidate"] == "lineage2x2_reset"
    decisions["offspring3_reset"]["passes"] = False
    decisions["lineage2x2_reset"]["passes"] = False
    assert nominate_candidate(decisions)["candidate"] == "offspring8_local"


def test_status_is_read_only_and_runner_has_shared_host_guards(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_depth_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path("scripts/run-wagner-ph-interpreter-depth-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-interpreter-depth.sh").read_text()
    assert "maximum_wall_seconds=21600" in runner
    assert "soft_wall_seconds=20700" in runner
    assert "maximum_start_load=18" in runner
    assert "minimum_available_kib=10485760" in runner
    assert "minimum_free_disk_kib=10485760" in runner
    assert "workers must lie in [1, 4]" in runner
    assert "GRE_WAGNER_PH_DEPTH_SOFT_DEADLINE_EPOCH" in runner
    assert "GRE_WAGNER_PH_DEPTH_PRIOR_CONSUMED_SECONDS" in runner
    assert "kill -KILL" in runner
    assert "heartbeat age" in status
