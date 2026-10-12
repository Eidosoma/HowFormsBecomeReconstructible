from __future__ import annotations

from dataclasses import replace

from gre_sim.boolean import BooleanRulebook
from gre_sim.config import EvolutionSpec, StudySpec
from gre_sim.evolution import (
    EvolutionContext,
    context_pair_from_landscape,
    evolve_population,
    run_published_wagner_validation,
)


def test_contexts_are_drawn_from_distinct_point_basins() -> None:
    founder = BooleanRulebook.from_successor([0, 1, 0, 1])
    contexts = context_pair_from_landscape(founder.landscape(), 2, 0.5)
    assert contexts is not None
    assert {context.target_state for context in contexts} == {0, 1}


def test_small_boolean_evolution_is_deterministic() -> None:
    founder = BooleanRulebook.from_successor([0, 1, 0, 1])
    contexts = (EvolutionContext(2, 0), EvolutionContext(3, 1))
    spec = EvolutionSpec(
        population=4,
        generations=2,
        training_replicates=1,
        selection_replicates=2,
        heldout_replicates=2,
        selection_strength=0.0,
        max_offspring_attempts_factor=16,
    )
    arguments = dict(
        engine="boolean",
        genes=2,
        contexts=contexts,
        spec=spec,
        master_seed=StudySpec.quick().master_seed,
        population_id="test-population",
        boolean_flip_probability=0.0,
        wagner_flip_probability=0.0,
        wagner_variance=0.0,
        wagner_max_sweeps=20,
        founder=founder,
    )
    first = evolve_population(**arguments)
    second = evolve_population(**arguments)
    assert first.selected.uid == second.selected.uid
    assert first.trace == second.trace
    assert first.heldout_fitness == second.heldout_fitness == 1.0


def test_published_wagner_validation_is_a_separate_runnable_cohort() -> None:
    quick = StudySpec.quick()
    values = run_published_wagner_validation(
        quick.evolution, quick.master_seed, quick.wagner.genes
    )
    assert len(values) == 2
    assert {value["variance"] for value in values} == {0.0, 0.1}

