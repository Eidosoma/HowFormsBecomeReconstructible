from __future__ import annotations

from pathlib import Path

import numpy as np

from gre_sim.artifacts import canonical_digest
from gre_sim.wagner import WagnerRulebook
from gre_sim.wagner_ph_architecture_analysis import nominate_two
from gre_sim.wagner_ph_architecture_campaign import (
    confirmation_arms,
    wagner_ph_architecture_status,
)
from gre_sim.wagner_ph_architecture_config import (
    ARCHITECTURE_ARMS,
    arm_settings,
    architecture_spec,
    evidence_family,
    uniform_control,
)
from gre_sim.wagner_ph_architecture_evolution import architecture_score
from gre_sim.wagner_ph_architecture_genome import (
    ArchitectureInterpreter,
    architecture_cost,
    deserialize_genome,
    effective_genotype,
    initialize_interpreter,
    mutate_genome,
    serialize_genome,
)
from gre_sim.wagner_ph_architecture_predictor import (
    FEATURE_NAMES,
    predicted_edge_ranking,
    structural_feature_matrix,
)
from gre_sim.wagner_ph_cooption_evolution import founder_carrier
from gre_sim.wagner_ph_cooption_experiment import sample_cooption_task


def _genome(architecture: str, repair: float = 0.0):
    rulebook = WagnerRulebook.random(10, np.random.default_rng(4))
    return initialize_interpreter(rulebook, architecture, repair), founder_carrier()


def test_architecture_contract_fixes_factorial_confirmation_and_eight_hour_cap() -> None:
    spec = architecture_spec()
    assert spec.arms == ARCHITECTURE_ARMS
    assert len(spec.arms) * spec.task_count == 84
    assert spec.confirmation_task_count == 16
    assert (spec.population_size, spec.generations) == (16, 24)
    assert spec.predictor_top_k == 10 and spec.predictor_ridge == 1.0
    assert spec.maximum_workers == 4
    assert (spec.hard_wall_seconds, spec.soft_wall_seconds) == (28_800, 27_600)
    assert spec.stage_reservations_seconds == (
        2400,
        7200,
        4200,
        300,
        7200,
        4200,
        900,
    )
    assert sum(spec.stage_reservations_seconds) == 26_400
    assert spec.soft_wall_seconds - sum(spec.stage_reservations_seconds) == 1200


def test_arm_factorial_and_confirmation_controls_are_explicit() -> None:
    assert arm_settings("mh_single_guided") == {
        "selection_mode": "multihorizon",
        "architecture": "single",
        "challenge": "guided",
    }
    assert arm_settings("mh_repair_uniform")["architecture"] == "repair"
    assert arm_settings("mh_median3_ordinary")["architecture"] == "median3"
    assert uniform_control("mh_single_guided") == "mh_single_uniform"
    assert evidence_family("mh_median3_ordinary") == "engineered_error_correction"
    assert confirmation_arms(("mh_single_guided", "mh_repair_guided")) == (
        "individual_single",
        "mh_single_ordinary",
        "mh_single_uniform",
        "mh_single_guided",
        "mh_repair_ordinary",
        "mh_repair_uniform",
        "individual_repair",
        "mh_repair_guided",
    )


def test_median_triplication_rejects_one_copy_outlier_and_round_trips() -> None:
    base = WagnerRulebook.random(10, np.random.default_rng(3))
    low = base.weights.copy()
    middle = base.weights.copy()
    high = base.weights.copy()
    low[2, 7], middle[2, 7], high[2, 7] = -1.0, 0.5, 20.0
    copies = tuple(
        WagnerRulebook(weights, base.bias, base.order)
        for weights in (low, middle, high)
    )
    median = ArchitectureInterpreter(copies, "median3")
    mean = ArchitectureInterpreter(copies, "mean3")
    assert median.effective_rulebook().weights[2, 7] == 0.5
    assert mean.effective_rulebook().weights[2, 7] == 6.5
    genome = median, founder_carrier()
    assert serialize_genome(deserialize_genome(serialize_genome(genome))) == serialize_genome(genome)


def test_repair_attenuates_the_same_reset_and_has_explicit_cost() -> None:
    spec = architecture_spec(smoke=True)
    repaired = _genome("repair", 0.9)
    natural = mutate_genome(
        repaired,
        repaired,
        "mh_repair_ordinary",
        np.random.default_rng(18),
        spec,
    )
    repair_off = mutate_genome(
        repaired,
        repaired,
        "mh_repair_ordinary",
        np.random.default_rng(18),
        spec,
        mechanism="repair_off",
    )
    natural_l2 = np.linalg.norm(
        natural[0].copies[0].weights - repaired[0].copies[0].weights
    )
    off_l2 = np.linalg.norm(
        repair_off[0].copies[0].weights - repaired[0].copies[0].weights
    )
    assert natural_l2 < off_l2
    assert architecture_cost(repaired[0], spec) == spec.repair_cost * 0.9


def test_structural_predictor_is_deterministic_and_task_excluding() -> None:
    rulebook, carrier = effective_genotype(_genome("single"))
    matrix = structural_feature_matrix(rulebook, (0,))
    assert matrix.shape == (100, len(FEATURE_NAMES))
    coefficients = [0.0] * len(FEATURE_NAMES)
    coefficients[1] = 1.0
    predictor = {
        "top_k": 10,
        "development_coefficients_by_heldout_task": {"0": coefficients},
        "fresh_coefficients_fit_historical_tasks_only": coefficients,
        "fold_membership": {"0": {"training_tasks": list(range(1, 12))}},
        "historical_tasks": list(range(12)),
    }
    first = predicted_edge_ranking(rulebook, carrier, predictor, 0, "development")
    second = predicted_edge_ranking(rulebook, carrier, predictor, 0, "development")
    assert canonical_digest(first) == canonical_digest(second)
    assert first["target_task_excluded"] is True
    assert len(first["top_edges"]) == 10


def test_multihorizon_score_is_replayable_and_contains_no_ph_label() -> None:
    spec = architecture_spec(smoke=True)
    kernel = spec.kernel()
    task = sample_cooption_task(
        kernel, 0, "architecture-unit", master_seed=spec.master_seed
    )
    genome = (
        initialize_interpreter(WagnerRulebook.from_dict(task["founder"]), "single"),
        founder_carrier(),
    )
    coefficient = [0.0] * len(FEATURE_NAMES)
    predictor = {
        "top_k": 10,
        "development_coefficients_by_heldout_task": {"0": coefficient},
        "fresh_coefficients_fit_historical_tasks_only": coefficient,
        "fold_membership": {"0": {"training_tasks": list(range(1, 12))}},
        "historical_tasks": list(range(12)),
    }
    first = architecture_score(
        genome,
        task,
        kernel,
        spec,
        "mh_single_ordinary",
        0,
        1,
        predictor,
        "development",
    )
    second = architecture_score(
        genome,
        task,
        kernel,
        spec,
        "mh_single_ordinary",
        0,
        1,
        predictor,
        "development",
    )
    assert canonical_digest(first) == canonical_digest(second)
    assert len(first["virtual_descendants"]) == 4
    assert all(len(value["chain"]) == 4 for value in first["virtual_descendants"])
    assert first["fitness_contains_memory_information_intervention_atlas_damage_or_ph_metric"] is False


def test_two_candidates_are_ranked_even_when_no_arm_passes_every_gate() -> None:
    decisions = {}
    for index, name in enumerate(ARCHITECTURE_ARMS):
        decisions[name] = {
            "core_gate_count": index,
            "pedigree": {
                "distances": {
                    "1": {"retention_interval": {"lower": index / 100}},
                    "4": {"retention_interval": {"lower": index / 100}},
                }
            },
            "information_advantage": {"interval": {"mean": index / 100}},
            "evidence_tier": evidence_family(name),
            "passes": False,
        }
    nomination = nominate_two(decisions)
    assert nomination["single_candidate"] == "mh_single_guided"
    assert nomination["engineered_candidate"] == "mh_median3_ordinary"
    assert nomination["selection_does_not_require_development_pass"] is True


def test_status_is_read_only_and_runner_has_shared_host_guards(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_architecture_status(target)["status"] == "not-started"
    assert not target.exists()
    runner = Path(
        "scripts/run-wagner-ph-interpreter-architecture-detached.sh"
    ).read_text()
    status = Path("scripts/status-wagner-ph-interpreter-architecture.sh").read_text()
    for text in (
        "maximum_wall_seconds=28800",
        "soft_wall_seconds=27600",
        "maximum_start_load=18",
        "minimum_available_kib=10485760",
        "minimum_free_disk_kib=10485760",
        "workers must lie in [1, 4]",
        "GRE_WAGNER_PH_ARCHITECTURE_SOFT_DEADLINE_EPOCH",
        "GRE_WAGNER_PH_ARCHITECTURE_PRIOR_CONSUMED_SECONDS",
        "OPENBLAS_NUM_THREADS=1",
        "CUDA_VISIBLE_DEVICES",
        "kill -KILL",
    ):
        assert text in runner
    assert "heartbeat age" in status
