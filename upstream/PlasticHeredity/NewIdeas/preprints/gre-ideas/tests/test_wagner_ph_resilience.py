from __future__ import annotations

from pathlib import Path

import numpy as np

from gre_sim.artifacts import canonical_digest
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_ph_cooption_evolution import founder_carrier
from gre_sim.wagner_ph_cooption_experiment import sample_cooption_task
from gre_sim.wagner_ph_resilience_analysis import CANDIDATE_ARMS, nominate_candidate
from gre_sim.wagner_ph_resilience_campaign import wagner_ph_resilience_status
from gre_sim.wagner_ph_resilience_config import (
    DIAGNOSTIC_CONDITIONS,
    RESILIENCE_ARMS,
    architecture_control,
    arm_settings,
    evidence_tier,
    resilience_spec,
)
from gre_sim.wagner_ph_resilience_evolution import resilience_score
from gre_sim.wagner_ph_resilience_genome import (
    architecture_cost,
    deserialize_genome,
    effective_genotype,
    initialize_interpreter,
    mutate_genome,
    serialize_genome,
)


def _genome(architecture: str, repair: float = 0.0):
    rulebook = WagnerRulebook.random(10, np.random.default_rng(4))
    return initialize_interpreter(rulebook, architecture, repair), founder_carrier()


def test_resilience_contract_fixes_balanced_tournament_and_six_hour_wall() -> None:
    spec = resilience_spec()
    assert spec.arms == RESILIENCE_ARMS
    assert spec.diagnostic_conditions == DIAGNOSTIC_CONDITIONS
    assert len(spec.arms) * spec.task_count == 72
    assert spec.population_size == 16 and spec.generations == 24
    assert spec.maximum_workers == 4
    assert (spec.hard_wall_seconds, spec.soft_wall_seconds) == (21600, 20700)
    assert spec.stage_reservations_seconds == (1800, 7800, 3300, 300, 4200, 2700, 600)
    assert sum(spec.stage_reservations_seconds) == spec.soft_wall_seconds


def test_arm_tiers_and_controls_are_explicit() -> None:
    assert arm_settings("cvar8_reset") == {"selection_mode": "cvar8", "architecture": "single"}
    assert arm_settings("lineage4_repair")["selection_mode"] == "lineage4_cvar50"
    assert arm_settings("individual_triplicate")["architecture"] == "triplicate"
    assert evidence_tier("lineage4_reset") == "ordinary_full_reset"
    assert evidence_tier("individual_repair") == "engineered_global_repair"
    assert architecture_control("lineage4_triplicate") == "individual_triplicate"


def test_repair_is_global_attenuation_with_explicit_cost_and_replays() -> None:
    spec = resilience_spec(smoke=True)
    repaired = _genome("repair", 0.9)
    first = mutate_genome(repaired, repaired, "lineage4_repair", np.random.default_rng(18), spec)
    second = mutate_genome(repaired, repaired, "lineage4_repair", np.random.default_rng(18), spec)
    assert serialize_genome(first) == serialize_genome(second)
    assert 0.0 <= first[0].repair_strength <= 0.9
    assert architecture_cost(repaired[0], spec) == spec.repair_cost * 0.9
    ordinary = _genome("single")
    ordinary_child = mutate_genome(ordinary, ordinary, "lineage4_reset", np.random.default_rng(18), spec)
    repaired_l2 = np.linalg.norm(first[0].copies[0].weights - repaired[0].copies[0].weights)
    ordinary_l2 = np.linalg.norm(ordinary_child[0].copies[0].weights - ordinary[0].copies[0].weights)
    assert repaired_l2 < ordinary_l2


def test_triplication_uses_three_complete_copies_and_effective_mean() -> None:
    spec = resilience_spec(smoke=True)
    genome = _genome("triplicate")
    child = mutate_genome(genome, genome, "lineage4_triplicate", np.random.default_rng(9), spec)
    assert len(child[0].copies) == 3
    expected = np.mean(np.stack([copy.weights for copy in child[0].copies]), axis=0)
    assert np.array_equal(effective_genotype(child)[0].weights, expected)
    assert architecture_cost(child[0], spec) == spec.triplicate_cost
    assert serialize_genome(deserialize_genome(serialize_genome(child))) == serialize_genome(child)


def test_tail_scores_use_only_observable_descendant_function() -> None:
    spec = resilience_spec(smoke=True)
    kernel = spec.kernel()
    task = sample_cooption_task(kernel, 0, "resilience-unit", master_seed=spec.master_seed)
    genome = (initialize_interpreter(WagnerRulebook.from_dict(task["founder"]), "single"), founder_carrier())
    first = resilience_score(genome, task, kernel, spec, "cvar8_reset", 0, 1)
    second = resilience_score(genome, task, kernel, spec, "cvar8_reset", 0, 1)
    assert canonical_digest(first) == canonical_digest(second)
    assert len(first["virtual_descendants"]) == 8 and first["selected_tail_size"] == 2
    assert first["fitness_contains_memory_information_intervention_or_ph_metric"] is False
    lineage = resilience_score(genome, task, kernel, spec, "lineage4_reset", 0, 1)
    assert len(lineage["virtual_descendants"]) == 4
    assert all(value["distance"] == 4 for value in lineage["virtual_descendants"])


def test_nomination_respects_evidence_tier_before_effect_size() -> None:
    decisions = {
        name: {
            "passes": False,
            "evidence_tier": evidence_tier(name),
            "pedigree": {"distances": {"4": {"retention_interval": {"lower": 0.0}}}},
            "information_advantage": {"interval": {"mean": 0.0}},
        }
        for name in CANDIDATE_ARMS
    }
    decisions["individual_triplicate"].update(passes=True, pedigree={"distances": {"4": {"retention_interval": {"lower": 0.9}}}})
    decisions["lineage4_reset"].update(passes=True, pedigree={"distances": {"4": {"retention_interval": {"lower": 0.4}}}})
    assert nominate_candidate(decisions)["candidate"] == "lineage4_reset"


def test_status_is_read_only_and_detached_runner_has_shared_host_guards(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_resilience_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path("scripts/run-wagner-ph-interpreter-resilience-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-interpreter-resilience.sh").read_text()
    for text in (
        "maximum_wall_seconds=21600",
        "soft_wall_seconds=20700",
        "maximum_start_load=18",
        "minimum_available_kib=10485760",
        "minimum_free_disk_kib=10485760",
        "workers must lie in [1, 4]",
        "GRE_WAGNER_PH_RESILIENCE_SOFT_DEADLINE_EPOCH",
        "GRE_WAGNER_PH_RESILIENCE_PRIOR_CONSUMED_SECONDS",
        "kill -KILL",
    ):
        assert text in runner
    assert "heartbeat age" in status
