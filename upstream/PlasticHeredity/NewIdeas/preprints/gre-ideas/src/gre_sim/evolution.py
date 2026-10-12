"""Population evolution for Boolean and stochastic Wagner rulebooks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np

from .boolean import (
    BooleanRulebook,
    mutate_boolean,
    recombine_boolean,
)
from .config import EvolutionSpec
from .endpoints import apply_carryover
from .engines import Rulebook
from .landscape import Landscape, normalized_hamming
from .rng import rng_for
from .wagner import (
    WagnerRulebook,
    gamma_multipliers,
    mutate_wagner,
    recombine_wagner,
)


class EvolutionExhausted(RuntimeError):
    """Selection could not fill a generation within the frozen attempt cap."""


@dataclass(frozen=True)
class EvolutionContext:
    base_state: int
    target_state: int


@dataclass(frozen=True)
class GenerationSummary:
    generation: int
    mean_fitness: float
    best_fitness: float
    accepted: int
    proposals: int


@dataclass(frozen=True)
class EvolutionResult:
    selected: Rulebook
    contexts: tuple[EvolutionContext, ...]
    trace: tuple[GenerationSummary, ...]
    training_fitness: float
    selection_fitness: float
    heldout_fitness: float
    eligible_candidates: int
    eligible_pool: tuple[Rulebook, ...]

    def metadata(self) -> dict[str, object]:
        return {
            "contexts": [asdict(context) for context in self.contexts],
            "trace": [asdict(generation) for generation in self.trace],
            "training_fitness": self.training_fitness,
            "selection_fitness": self.selection_fitness,
            "heldout_fitness": self.heldout_fitness,
            "eligible_candidates": self.eligible_candidates,
        }


def _noisy_initial(
    base_state: int,
    genes: int,
    flip_probability: float,
    rng: np.random.Generator,
) -> int:
    # carryover=0 makes the discrete contract an expression-noise perturbation of base.
    return apply_carryover(
        base_state,
        base_state,
        genes,
        0.0,
        flip_probability,
        rng,
    )


def phenotype_distance(
    rulebook: Rulebook,
    context: EvolutionContext,
    rng: np.random.Generator,
    boolean_flip_probability: float,
    wagner_flip_probability: float,
    wagner_variance: float,
    wagner_max_sweeps: int,
) -> float:
    if isinstance(rulebook, BooleanRulebook):
        initial = _noisy_initial(
            context.base_state,
            rulebook.genes,
            boolean_flip_probability,
            rng,
        )
        result = rulebook.develop(initial)
    elif isinstance(rulebook, WagnerRulebook):
        initial = _noisy_initial(
            context.base_state,
            rulebook.genes,
            wagner_flip_probability,
            rng,
        )
        multipliers = gamma_multipliers(rulebook.genes, wagner_variance, rng)
        result = rulebook.develop(initial, multipliers, wagner_max_sweeps)
    else:  # pragma: no cover
        raise TypeError(type(rulebook))
    if result.status != "point":
        return 1.0
    return normalized_hamming(result.final_state, context.target_state, rulebook.genes)


def evaluate_fitness(
    rulebook: Rulebook,
    contexts: tuple[EvolutionContext, ...],
    replicates: int,
    selection_strength: float,
    master_seed: str,
    seed_parts: tuple[object, ...],
    boolean_flip_probability: float,
    wagner_flip_probability: float,
    wagner_variance: float,
    wagner_max_sweeps: int,
) -> float:
    if replicates < 1:
        raise ValueError("fitness needs at least one replicate")
    distances: list[float] = []
    for context_index, context in enumerate(contexts):
        for replicate in range(replicates):
            rng = rng_for(master_seed, *seed_parts, context_index, replicate)
            distances.append(
                phenotype_distance(
                    rulebook,
                    context,
                    rng,
                    boolean_flip_probability,
                    wagner_flip_probability,
                    wagner_variance,
                    wagner_max_sweeps,
                )
            )
    return float(np.exp(-selection_strength * float(np.mean(distances))))


def _random_rulebook(engine: str, genes: int, rng: np.random.Generator) -> Rulebook:
    if engine == "boolean":
        return BooleanRulebook.random(genes, rng)
    if engine == "wagner":
        return WagnerRulebook.random(genes, rng)
    raise ValueError(f"unknown engine: {engine}")


def _mutate(rulebook: Rulebook, rng: np.random.Generator) -> Rulebook:
    if isinstance(rulebook, BooleanRulebook):
        return mutate_boolean(rulebook, rng)
    if isinstance(rulebook, WagnerRulebook):
        return mutate_wagner(rulebook, rng)
    raise TypeError(type(rulebook))


def _recombine(first: Rulebook, second: Rulebook, rng: np.random.Generator) -> Rulebook:
    if isinstance(first, BooleanRulebook) and isinstance(second, BooleanRulebook):
        return recombine_boolean(first, second, rng)
    if isinstance(first, WagnerRulebook) and isinstance(second, WagnerRulebook):
        return recombine_wagner(first, second, rng)
    raise TypeError("parents must use the same engine")


def _deterministically_settles(rulebook: Rulebook, contexts: tuple[EvolutionContext, ...]) -> bool:
    for context in contexts:
        if isinstance(rulebook, BooleanRulebook):
            result = rulebook.develop(context.base_state)
        else:
            assert isinstance(rulebook, WagnerRulebook)
            result = rulebook.develop(context.base_state, None, 100)
        if result.status != "point":
            return False
    return True


def initialize_population(
    engine: str,
    genes: int,
    contexts: tuple[EvolutionContext, ...],
    population_size: int,
    master_seed: str,
    population_id: str,
    founder: Rulebook | None,
) -> list[Rulebook]:
    population: list[Rulebook] = []
    attempts = 0
    maximum_attempts = population_size * 10_000
    while len(population) < population_size and attempts < maximum_attempts:
        rng = rng_for(master_seed, "evolution", population_id, "initial", attempts)
        if founder is None:
            candidate = _random_rulebook(engine, genes, rng)
        elif not population:
            candidate = founder
        else:
            candidate = _mutate(founder, rng)
        attempts += 1
        if _deterministically_settles(candidate, contexts):
            population.append(candidate)
    if len(population) != population_size:
        raise EvolutionExhausted(
            f"could initialize only {len(population)}/{population_size} stable individuals"
        )
    return population


def evolve_population(
    engine: str,
    genes: int,
    contexts: tuple[EvolutionContext, ...],
    spec: EvolutionSpec,
    master_seed: str,
    population_id: str,
    boolean_flip_probability: float,
    wagner_flip_probability: float,
    wagner_variance: float,
    wagner_max_sweeps: int,
    founder: Rulebook | None = None,
    eligibility: Callable[[Rulebook], bool] | None = None,
) -> EvolutionResult:
    """Evolve one independent population using row-level sexual recombination."""

    population = initialize_population(
        engine,
        genes,
        contexts,
        spec.population,
        master_seed,
        population_id,
        founder,
    )
    fitnesses = np.asarray(
        [
            evaluate_fitness(
                rulebook,
                contexts,
                spec.training_replicates,
                spec.selection_strength,
                master_seed,
                ("evolution", population_id, "initial-fitness", index),
                boolean_flip_probability,
                wagner_flip_probability,
                wagner_variance,
                wagner_max_sweeps,
            )
            for index, rulebook in enumerate(population)
        ],
        dtype=float,
    )
    trace: list[GenerationSummary] = [
        GenerationSummary(0, float(np.mean(fitnesses)), float(np.max(fitnesses)), len(population), 0)
    ]

    for generation in range(1, spec.generations + 1):
        next_population: list[Rulebook] = []
        next_fitnesses: list[float] = []
        proposals = 0
        maximum = spec.population * spec.max_offspring_attempts_factor
        while len(next_population) < spec.population and proposals < maximum:
            rng = rng_for(
                master_seed, "evolution", population_id, "offspring", generation, proposals
            )
            first_index = int(rng.integers(0, len(population)))
            second_index = int(rng.integers(0, len(population)))
            child = _mutate(
                _recombine(population[first_index], population[second_index], rng), rng
            )
            fitness = evaluate_fitness(
                child,
                contexts,
                spec.training_replicates,
                spec.selection_strength,
                master_seed,
                ("evolution", population_id, "fitness", generation, proposals),
                boolean_flip_probability,
                wagner_flip_probability,
                wagner_variance,
                wagner_max_sweeps,
            )
            proposals += 1
            if rng.random() < fitness:
                next_population.append(child)
                next_fitnesses.append(fitness)
        if len(next_population) != spec.population:
            raise EvolutionExhausted(
                f"generation {generation} accepted {len(next_population)}/{spec.population} "
                f"after {proposals} proposals"
            )
        population = next_population
        fitnesses = np.asarray(next_fitnesses, dtype=float)
        trace.append(
            GenerationSummary(
                generation,
                float(np.mean(fitnesses)),
                float(np.max(fitnesses)),
                len(population),
                proposals,
            )
        )

    selection_scores = np.asarray(
        [
            evaluate_fitness(
                rulebook,
                contexts,
                spec.selection_replicates,
                spec.selection_strength,
                master_seed,
                ("evolution", population_id, "selection", index),
                boolean_flip_probability,
                wagner_flip_probability,
                wagner_variance,
                wagner_max_sweeps,
            )
            for index, rulebook in enumerate(population)
        ]
    )
    ranking = np.argsort(-selection_scores)
    selected_index: int | None = None
    eligible_indices: list[int] = []
    for index in ranking:
        valid = eligibility(population[int(index)]) if eligibility is not None else True
        if valid:
            eligible_indices.append(int(index))
            if selected_index is None:
                selected_index = int(index)
    if selected_index is None:
        raise EvolutionExhausted("final population contained no eligible rulebook")
    selected = population[selected_index]
    heldout_fitness = evaluate_fitness(
        selected,
        contexts,
        spec.heldout_replicates,
        spec.selection_strength,
        master_seed,
        ("evolution", population_id, "heldout"),
        boolean_flip_probability,
        wagner_flip_probability,
        wagner_variance,
        wagner_max_sweeps,
    )
    return EvolutionResult(
        selected=selected,
        contexts=contexts,
        trace=tuple(trace),
        training_fitness=float(fitnesses[selected_index]),
        selection_fitness=float(selection_scores[selected_index]),
        heldout_fitness=heldout_fitness,
        eligible_candidates=len(eligible_indices),
        eligible_pool=tuple(population[index] for index in eligible_indices[:4]),
    )


def eligible_landscape(
    landscape: Landscape,
    minimum_point_attractors: int,
    minimum_basin_fraction: float,
) -> bool:
    qualifying = [
        index
        for index in landscape.point_indices
        if landscape.basin_fractions[index] >= minimum_basin_fraction
    ]
    return len(qualifying) >= minimum_point_attractors


def context_pair_from_landscape(
    landscape: Landscape,
    genes: int,
    minimum_target_distance: float,
    minimum_basin_fraction: float = 0.0,
) -> tuple[EvolutionContext, EvolutionContext] | None:
    points = [
        landscape.attractors[index].states[0]
        for index in landscape.point_indices
        if landscape.basin_fractions[index] >= minimum_basin_fraction
    ]
    best: tuple[int, int] | None = None
    best_distance = -1.0
    for left_index, left in enumerate(points):
        for right in points[left_index + 1 :]:
            distance = normalized_hamming(left, right, genes)
            if distance > best_distance:
                best = (left, right)
                best_distance = distance
    if best is None or best_distance < minimum_target_distance:
        return None

    contexts: list[EvolutionContext] = []
    for target in best:
        attractor_index = int(landscape.attractor_index[target])
        basin_states = np.flatnonzero(landscape.attractor_index == attractor_index)
        # Start far from the target so evolution preserves a developmental path.
        base = max(
            (int(state) for state in basin_states),
            key=lambda state: (normalized_hamming(state, target, genes), -state),
        )
        contexts.append(EvolutionContext(base, target))
    return contexts[0], contexts[1]


def generate_founder_and_contexts(
    engine: str,
    genes: int,
    minimum_target_distance: float,
    minimum_point_attractors: int,
    minimum_basin_fraction: float,
    master_seed: str,
    population_id: str,
    maximum_proposals: int,
) -> tuple[Rulebook, tuple[EvolutionContext, ...]]:
    for proposal in range(maximum_proposals):
        rng = rng_for(master_seed, "evolution", population_id, "founder", proposal)
        candidate = _random_rulebook(engine, genes, rng)
        landscape = candidate.landscape()
        if not eligible_landscape(
            landscape, minimum_point_attractors, minimum_basin_fraction
        ):
            continue
        contexts = context_pair_from_landscape(
            landscape, genes, minimum_target_distance, minimum_basin_fraction
        )
        if contexts is not None:
            return candidate, contexts
    raise EvolutionExhausted(
        f"no eligible {engine} founder after {maximum_proposals} proposals"
    )


def run_published_wagner_validation(
    spec: EvolutionSpec,
    master_seed: str,
    genes: int = 10,
    noise_values: tuple[float, ...] = (0.0, 0.1),
) -> list[dict[str, object]]:
    """Exercise the published fixed-target algorithm as a separate validation cohort."""

    validation_spec = EvolutionSpec(
        enabled=True,
        validation_replicates_per_noise=spec.validation_replicates_per_noise,
        validation_population=spec.validation_population,
        validation_generations=spec.validation_generations,
        population=spec.validation_population,
        generations=spec.validation_generations,
        contexts=1,
        training_replicates=1,
        selection_replicates=max(2, min(32, spec.selection_replicates)),
        heldout_replicates=max(2, min(64, spec.heldout_replicates)),
        selection_strength=spec.selection_strength,
        max_offspring_attempts_factor=spec.max_offspring_attempts_factor,
    )
    results: list[dict[str, object]] = []
    for variance in noise_values:
        for replicate in range(spec.validation_replicates_per_noise):
            rng = rng_for(master_seed, "published-validation", variance, replicate, "context")
            base = int(rng.integers(0, 1 << genes))
            target = int(rng.integers(0, 1 << genes))
            while target == base:
                target = int(rng.integers(0, 1 << genes))
            result = evolve_population(
                "wagner",
                genes,
                (EvolutionContext(base, target),),
                validation_spec,
                master_seed,
                f"published-theta-{variance}-rep-{replicate}",
                boolean_flip_probability=0.0,
                wagner_flip_probability=0.0,
                wagner_variance=variance,
                wagner_max_sweeps=100,
            )
            results.append(
                {
                    "variance": variance,
                    "replicate": replicate,
                    **result.metadata(),
                    "selected_uid": result.selected.uid,
                }
            )
    return results
