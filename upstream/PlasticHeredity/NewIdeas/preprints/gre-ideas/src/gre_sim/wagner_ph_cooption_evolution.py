"""Performance-only co-option evolution for Wagner GRNs and quantized carriers."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    verify_checksums,
    write_checksums,
    write_json,
)
from .local_ph_dynamics import blank_local, structural_mask
from .rng import rng_for
from .wagner import WagnerRulebook, mutate_wagner, recombine_wagner
from .wagner_ph_cooption_config import (
    CAPACITY_STEPS,
    COOPTION_EVOLUTION_RESULT_FORMAT,
    PRECISION_STEPS,
    CooptionSpec,
    QuantizedCarrierGenome,
    treatment_architecture,
    treatment_selection_phase,
)
from .wagner_ph_cooption_experiment import (
    _adult_training,
    _assay_carrier,
    _history_sequence,
    carrier_resource_cost,
    local_carrier,
    quantized_copy,
    quantized_write,
    sample_cooption_task,
)


EVOLUTION_REGISTRATION_FORMAT = "gre-wagner-ph-cooption-evolution-registration-v1"
EVOLUTION_MANIFEST_FORMAT = "gre-wagner-ph-cooption-evolution-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def founder_carrier() -> QuantizedCarrierGenome:
    result = QuantizedCarrierGenome(
        "cooption-founder", 0.0, 0.2, 0.0, 1, "outgoing", 1, 2
    )
    result.validate()
    return result


def _carrier_payload(carrier: QuantizedCarrierGenome) -> dict[str, Any]:
    result = carrier.to_dict()
    result.pop("name")
    return result


def _named_carrier(payload: dict[str, Any]) -> QuantizedCarrierGenome:
    normalized = {
        "write_rate": round(float(payload["write_rate"]), 3),
        "decay": round(float(payload["decay"]), 3),
        "coupling": round(float(payload["coupling"]), 3),
        "hysteresis": int(payload["hysteresis"]),
        "topology": str(payload["topology"]),
        "k": int(payload["k"]),
        "bits_per_mark": int(payload["bits_per_mark"]),
    }
    if normalized["topology"] == "all":
        normalized["k"] = 10
    result = QuantizedCarrierGenome(
        f"quantized-{canonical_digest(normalized)[:12]}", **normalized
    )
    result.validate()
    return result


def _mutate_strength(value: float, random: np.random.Generator) -> float:
    if value == 0.0:
        return float(random.uniform(0.05, 0.20))
    proposal = float(np.clip(value + random.normal(0.0, 0.08), 0.0, 1.0))
    if proposal < 0.025:
        return 0.0
    return proposal


def _adjacent(value: int, ordered: tuple[int, ...], random: np.random.Generator) -> int:
    index = ordered.index(value)
    choices = [candidate for candidate in (index - 1, index + 1) if 0 <= candidate < len(ordered)]
    return ordered[int(choices[int(random.integers(len(choices)))])] if choices else value


def mutate_carrier(
    left: QuantizedCarrierGenome,
    right: QuantizedCarrierGenome,
    architecture: str,
    random: np.random.Generator,
) -> QuantizedCarrierGenome:
    """Recombine and mutate independent, linked, or linked+ramp channels."""

    if architecture not in {"independent", "linked", "linked_ramp"}:
        raise ValueError(f"unknown carrier mutation architecture: {architecture}")
    payload: dict[str, Any] = {}
    for field in ("decay", "hysteresis", "topology", "k", "bits_per_mark"):
        payload[field] = getattr(left if random.random() < 0.5 else right, field)
    if architecture == "independent":
        payload["write_rate"] = getattr(left if random.random() < 0.5 else right, "write_rate")
        payload["coupling"] = getattr(left if random.random() < 0.5 else right, "coupling")
        if random.random() < 0.35:
            payload["write_rate"] = _mutate_strength(float(payload["write_rate"]), random)
        if random.random() < 0.35:
            payload["coupling"] = _mutate_strength(float(payload["coupling"]), random)
    else:
        parent = left if random.random() < 0.5 else right
        latent = 0.5 * (parent.write_rate + parent.coupling)
        if random.random() < 0.35:
            latent = _mutate_strength(float(latent), random)
        payload["write_rate"] = latent
        payload["coupling"] = latent
    if random.random() < 0.35:
        payload["decay"] = float(
            np.clip(float(payload["decay"]) + random.normal(0.0, 0.02), 0.0, 0.20)
        )
    if random.random() < 0.20:
        payload["hysteresis"] = int(
            np.clip(int(payload["hysteresis"]) + int(random.integers(-1, 2)), 1, 3)
        )
    if random.random() < 0.20:
        payload["k"] = (
            _adjacent(int(payload["k"]), CAPACITY_STEPS, random)
            if architecture == "linked_ramp"
            else CAPACITY_STEPS[int(random.integers(len(CAPACITY_STEPS)))]
        )
    if random.random() < 0.15:
        payload["bits_per_mark"] = (
            _adjacent(int(payload["bits_per_mark"]), PRECISION_STEPS, random)
            if architecture == "linked_ramp"
            else PRECISION_STEPS[int(random.integers(len(PRECISION_STEPS)))]
        )
    if random.random() < 0.15:
        topologies = (
            ("outgoing", "self_feedback")
            if architecture == "linked_ramp" and int(payload["k"]) < 10
            else ("all", "outgoing", "self_feedback")
        )
        payload["topology"] = topologies[int(random.integers(len(topologies)))]
    if payload["topology"] == "all":
        if architecture == "linked_ramp" and int(payload["k"]) < 10:
            payload["topology"] = "outgoing"
        else:
            payload["k"] = 10
    return _named_carrier(payload)


def constrain_carrier(
    carrier: QuantizedCarrierGenome, constraint: str | None
) -> QuantizedCarrierGenome:
    """Apply a prospective carrier-component constraint after mutation.

    The default path is deliberately an identity so archived co-option runs retain
    their exact behavior.  The constrained paths are used by later, separately
    registered experiments to distinguish ordinary GRN adaptation from selection
    on a writable and readable carrier.
    """

    if constraint is None or constraint == "full":
        return carrier
    if constraint not in {"inert", "writer_only", "reader_only", "fixed_k1"}:
        raise ValueError(f"unknown carrier constraint: {constraint}")
    payload = _carrier_payload(carrier)
    if constraint == "inert":
        payload.update(
            write_rate=0.0,
            coupling=0.0,
            decay=0.2,
            hysteresis=1,
            topology="outgoing",
            k=1,
            bits_per_mark=2,
        )
    elif constraint == "writer_only":
        payload["coupling"] = 0.0
    elif constraint == "reader_only":
        payload["write_rate"] = 0.0
    else:
        payload["k"] = 1
        payload["bits_per_mark"] = 2
        if payload["topology"] == "all":
            payload["topology"] = "outgoing"
    return _named_carrier(payload)


def genotype_id(rulebook: WagnerRulebook, carrier: QuantizedCarrierGenome) -> str:
    return canonical_digest(
        {"rulebook": rulebook.to_dict(), "carrier": _carrier_payload(carrier)}
    )[:24]


def serialize_genotype(
    rulebook: WagnerRulebook, carrier: QuantizedCarrierGenome
) -> dict[str, Any]:
    return {
        "genotype_id": genotype_id(rulebook, carrier),
        "rulebook": rulebook.to_dict(),
        "carrier": carrier.to_dict(),
    }


def deserialize_genotype(
    value: dict[str, Any],
) -> tuple[WagnerRulebook, QuantizedCarrierGenome]:
    rulebook = WagnerRulebook.from_dict(value["rulebook"])
    carrier = QuantizedCarrierGenome(**value["carrier"])
    carrier.validate(rulebook.genes)
    if value.get("genotype_id") != genotype_id(rulebook, carrier):
        raise ValueError("co-option genotype digest mismatch")
    return rulebook, carrier


def mutate_genotype(
    left: tuple[WagnerRulebook, QuantizedCarrierGenome],
    right: tuple[WagnerRulebook, QuantizedCarrierGenome],
    architecture: str,
    random: np.random.Generator,
) -> tuple[WagnerRulebook, QuantizedCarrierGenome]:
    rulebook = mutate_wagner(recombine_wagner(left[0], right[0], random), random)
    carrier = mutate_carrier(left[1], right[1], architecture, random)
    return rulebook, carrier


def training_panel_indices(generation: int, spec: CooptionSpec) -> tuple[int, ...]:
    block = generation % (spec.training_panel_size // spec.training_panels_per_generation)
    start = block * spec.training_panels_per_generation
    return tuple(range(start, start + spec.training_panels_per_generation))


def _training_episode(
    genotype: tuple[WagnerRulebook, QuantizedCarrierGenome],
    task: dict[str, Any],
    spec: CooptionSpec,
    phase: str,
    population_index: int,
    panel_index: int,
    stream: str,
    *,
    master_seed: str,
    predictive_persistence: float = 0.9,
) -> dict[str, float]:
    rulebook, genome = genotype
    mask = structural_mask(rulebook, local_carrier(genome))
    initial = "A" if panel_index % 2 == 0 else "B"
    persistence = 0.5 if phase == "homeostasis" else predictive_persistence
    scope = f"{stream}.population-{population_index:03d}.panel-{panel_index:03d}.{phase}"
    sequence = _history_sequence(
        master_seed,
        task,
        scope,
        initial,
        panel_index,
        persistence,
        spec.training_episode_generations,
    )
    adults = _adult_training(
        rulebook, task, spec, sequence[0], panel_index, 0, scope, master_seed
    )
    carrier = quantized_write(blank_local(spec.genes), adults, genome, mask)
    carrier = quantized_copy(
        carrier,
        genome,
        mask,
        spec,
        rng_for(master_seed, "cooption-training-copy", scope, 0),
    )
    totals: dict[str, float] = {"correct": 0.0, "functional": 0.0, "wrong": 0.0}
    for episode_generation in range(1, spec.training_episode_generations + 1):
        outcome = _assay_carrier(
            rulebook,
            task,
            spec,
            carrier,
            genome.coupling,
            sequence[episode_generation],
            panel_index,
            episode_generation,
            0.0,
            scope,
            master_seed,
            damaged_start=phase == "homeostasis",
        )
        for field in totals:
            totals[field] += float(outcome[field])
        if episode_generation < spec.training_episode_generations:
            adults = _adult_training(
                rulebook,
                task,
                spec,
                sequence[episode_generation],
                panel_index,
                episode_generation,
                scope,
                master_seed,
            )
            carrier = quantized_write(carrier, adults, genome, mask)
            carrier = quantized_copy(
                carrier,
                genome,
                mask,
                spec,
                rng_for(
                    master_seed,
                    "cooption-training-copy",
                    scope,
                    episode_generation,
                ),
            )
    denominator = float(spec.training_episode_generations)
    return {field: value / denominator for field, value in totals.items()}


def training_score(
    genotype: tuple[WagnerRulebook, QuantizedCarrierGenome],
    task: dict[str, Any],
    spec: CooptionSpec,
    treatment: str,
    population_index: int,
    generation: int,
    *,
    panel_indices: tuple[int, ...] | None = None,
    stream: str = "training",
    master_seed: str | None = None,
    predictive_persistence: float = 0.9,
    resource_cost_multiplier: float = 1.0,
) -> dict[str, Any]:
    """Score observable performance only; no memory or information term enters fitness."""

    if not 0.0 <= predictive_persistence <= 1.0:
        raise ValueError("predictive persistence must lie in [0, 1]")
    if resource_cost_multiplier < 0.0:
        raise ValueError("resource-cost multiplier cannot be negative")
    seed = master_seed or spec.master_seed
    phase = treatment_selection_phase(
        treatment, generation, spec.cooption_switch_generation
    )
    cost = carrier_resource_cost(genotype[1], spec) * resource_cost_multiplier
    if phase == "neutral":
        return {
            "phase": phase,
            "performance": 0.0,
            "correct_rate": 0.0,
            "functional_rate": 0.0,
            "wrong_rate": 0.0,
            "resource_cost": cost,
            "fitness": 0.0,
            "fitness_contains_memory_label": False,
        }
    panels = panel_indices or training_panel_indices(generation, spec)
    episodes = [
        _training_episode(
            genotype,
            task,
            spec,
            phase,
            population_index,
            panel,
            stream,
            master_seed=seed,
            predictive_persistence=predictive_persistence,
        )
        for panel in panels
    ]
    correct = float(np.mean([value["correct"] for value in episodes]))
    functional = float(np.mean([value["functional"] for value in episodes]))
    wrong = float(np.mean([value["wrong"] for value in episodes]))
    performance = functional if phase == "homeostasis" else correct
    return {
        "phase": phase,
        "performance": performance,
        "correct_rate": correct,
        "functional_rate": functional,
        "wrong_rate": wrong,
        "resource_cost": cost,
        "fitness": performance - cost,
        "fitness_contains_memory_label": False,
    }


def _tournament(fitness: np.ndarray, random: np.random.Generator, size: int) -> int:
    candidates = random.integers(0, len(fitness), size=size)
    return int(max(candidates, key=lambda index: (fitness[int(index)], -int(index))))


def _population_task(
    args: tuple[
        dict[str, Any],
        str,
        int,
        str,
        str,
        str,
        dict[str, Any] | None,
    ]
) -> dict[str, Any]:
    (
        spec_value,
        treatment,
        population_index,
        output_text,
        protocol_digest,
        seed,
        selection_settings,
    ) = args
    spec = CooptionSpec.from_dict(spec_value)
    settings = selection_settings or {}
    carrier_constraint = settings.get("carrier_constraint")
    predictive_persistence = float(settings.get("predictive_persistence", 0.9))
    resource_cost_multiplier = float(settings.get("resource_cost_multiplier", 1.0))
    architecture = treatment_architecture(treatment)
    population_id = f"{treatment}.population-{population_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"co-option evolution registration differs: {final_path}")
    checkpoint_path = output / f"{population_id}.checkpoint.json"
    task = sample_cooption_task(
        spec, population_index, "evolution", master_seed=seed
    )
    if checkpoint_path.is_file():
        saved = read_json(checkpoint_path)
        if saved.get("protocol_digest") != protocol_digest:
            raise ValueError("co-option checkpoint protocol differs")
        population = [deserialize_genotype(value) for value in saved["population"]]
        lineage_ids = [str(value) for value in saved["lineage_ids"]]
        scores = [dict(value) for value in saved["scores"]]
        ancestry = list(saved["ancestry"])
        trace = list(saved["trace"])
        start_generation = int(saved["generation"]) + 1
    else:
        founder = (
            WagnerRulebook.from_dict(task["founder"]),
            constrain_carrier(founder_carrier(), carrier_constraint),
        )
        population = [founder]
        for index in range(1, spec.population_size):
            random = rng_for(
                seed,
                "cooption-initial",
                architecture,
                population_index,
                index,
            )
            mutated = mutate_genotype(founder, founder, architecture, random)
            population.append(
                (mutated[0], constrain_carrier(mutated[1], carrier_constraint))
            )
        scores = [
            training_score(
                value,
                task,
                spec,
                treatment,
                population_index,
                0,
                master_seed=seed,
                predictive_persistence=predictive_persistence,
                resource_cost_multiplier=resource_cost_multiplier,
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest((population_id, 0, index, genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry = [
            {
                "generation": 0,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        "parent_ids": [],
                        **serialize_genotype(*value),
                        "training_score": scores[index],
                    }
                    for index, value in enumerate(population)
                ],
            }
        ]
        trace = []
        start_generation = 1

    def trace_item(generation: int) -> dict[str, Any]:
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        best = 0 if treatment == "neutral_drift" else int(np.argmax(fitness))
        validation_panels = tuple(
            range(spec.training_panel_size, spec.training_panel_size + spec.validation_panels)
        )
        validation = training_score(
            population[best],
            task,
            spec,
            treatment,
            population_index,
            generation,
            panel_indices=validation_panels,
            stream="validation",
            master_seed=seed,
            predictive_persistence=predictive_persistence,
            resource_cost_multiplier=resource_cost_multiplier,
        )
        return {
            "generation": generation,
            "selection_phase": scores[0]["phase"],
            "mean_fitness": float(np.mean(fitness)),
            "best_fitness": float(np.max(fitness)),
            "mean_performance": float(np.mean([value["performance"] for value in scores])),
            "validation_best_performance": float(validation["performance"]),
            "training_minus_validation": float(scores[best]["performance"] - validation["performance"]),
            "mean_capacity": float(np.mean([value[1].k for value in population])),
            "mean_precision": float(np.mean([value[1].bits_per_mark for value in population])),
            "writer_active_fraction": float(np.mean([value[1].write_rate > 0.0 for value in population])),
            "reader_active_fraction": float(np.mean([value[1].coupling > 0.0 for value in population])),
        }

    if not trace:
        trace.append(trace_item(0))
    for generation in range(start_generation, spec.generations + 1):
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        random = rng_for(
            seed,
            "cooption-generation",
            architecture,
            population_index,
            generation,
        )
        following: list[tuple[WagnerRulebook, QuantizedCarrierGenome]] = []
        parents: list[tuple[str, ...]] = []
        if treatment != "neutral_drift":
            elites = sorted(
                range(len(population)), key=lambda index: (-fitness[index], index)
            )[: spec.elite_count]
            for index in elites:
                following.append(population[index])
                parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            if treatment == "neutral_drift":
                left = int(random.integers(len(population)))
                right = int(random.integers(len(population)))
            else:
                left = _tournament(fitness, random, spec.tournament_size)
                right = _tournament(fitness, random, spec.tournament_size)
            mutated = mutate_genotype(
                population[left], population[right], architecture, random
            )
            following.append(
                (mutated[0], constrain_carrier(mutated[1], carrier_constraint))
            )
            parents.append((lineage_ids[left], lineage_ids[right]))
        population = following
        scores = [
            training_score(
                value,
                task,
                spec,
                treatment,
                population_index,
                generation,
                master_seed=seed,
                predictive_persistence=predictive_persistence,
                resource_cost_multiplier=resource_cost_multiplier,
            )
            for value in population
        ]
        lineage_ids = [
            canonical_digest((population_id, generation, index, genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry.append(
            {
                "generation": generation,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        "parent_ids": list(parents[index]),
                        **serialize_genotype(*value),
                        "training_score": scores[index],
                    }
                    for index, value in enumerate(population)
                ],
            }
        )
        trace.append(trace_item(generation))
        _atomic_json(
            checkpoint_path,
            {
                "format": "gre-wagner-ph-cooption-evolution-checkpoint-v1",
                "protocol_digest": protocol_digest,
                "generation": generation,
                "population": [serialize_genotype(*value) for value in population],
                "lineage_ids": lineage_ids,
                "scores": scores,
                "ancestry": ancestry,
                "trace": trace,
            },
        )
    final_fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
    selected_index = 0 if treatment == "neutral_drift" else int(np.argmax(final_fitness))
    founder = (
        WagnerRulebook.from_dict(task["founder"]),
        constrain_carrier(founder_carrier(), carrier_constraint),
    )
    result = {
        "format": COOPTION_EVOLUTION_RESULT_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "population_index": population_index,
        "treatment": treatment,
        "mutation_architecture": architecture,
        "task": task,
        "task_is_paired_across_treatments": True,
        "fitness_contains_only_observable_performance_and_resource_cost": True,
        "carrier_receives_target_label": False,
        "founder": serialize_genotype(*founder),
        "selected": serialize_genotype(*population[selected_index]),
        "selected_training_score": scores[selected_index],
        "final_population": [
            {**serialize_genotype(*value), "training_score": scores[index]}
            for index, value in enumerate(population)
        ],
        "trace": trace,
        "ancestry": ancestry,
    }
    if settings:
        result["selection_settings"] = settings
    result["result_digest"] = canonical_digest(
        {
            "selected": result["selected"],
            "score": result["selected_training_score"],
            "trace": result["trace"],
        }
    )
    _atomic_json(final_path, result)
    if checkpoint_path.is_file():
        checkpoint_path.unlink()
    return result


def run_cooption_evolution(
    spec: CooptionSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    *,
    treatments: tuple[str, ...] | None = None,
    task_count: int | None = None,
    master_seed: str | None = None,
    carrier_constraint: str | None = None,
    predictive_persistence: float = 0.9,
    resource_cost_multiplier: float = 1.0,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("co-option evolution permits one to four workers")
    selected_treatments = treatments or spec.treatments
    if not selected_treatments or not set(selected_treatments) <= set(spec.treatments):
        raise ValueError("invalid co-option evolution treatment subset")
    tasks_count = task_count or spec.evolution_tasks
    seed = master_seed or spec.master_seed
    if carrier_constraint not in {
        None,
        "full",
        "inert",
        "writer_only",
        "reader_only",
        "fixed_k1",
    }:
        raise ValueError("invalid prospective carrier constraint")
    if not 0.0 <= predictive_persistence <= 1.0:
        raise ValueError("predictive persistence must lie in [0, 1]")
    if resource_cost_multiplier < 0.0:
        raise ValueError("resource-cost multiplier cannot be negative")
    selection_settings: dict[str, Any] = {}
    if carrier_constraint not in (None, "full"):
        selection_settings["carrier_constraint"] = carrier_constraint
    if predictive_persistence != 0.9:
        selection_settings["predictive_persistence"] = predictive_persistence
    if resource_cost_multiplier != 1.0:
        selection_settings["resource_cost_multiplier"] = resource_cost_multiplier
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_cooption_evolution(destination)
        return destination
    started = time.monotonic()
    digest_payload: dict[str, Any] = {
        "spec": spec.to_dict(),
        "treatments": selected_treatments,
        "task_count": tasks_count,
        "master_seed": seed,
    }
    if selection_settings:
        digest_payload["selection_settings"] = selection_settings
    protocol_digest = canonical_digest(digest_payload)
    registration = {
        "format": EVOLUTION_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "treatments": list(selected_treatments),
        "task_count": tasks_count,
        "master_seed": seed,
        "tasks_are_paired_by_population_index": True,
        "training_panels_rotate_without_adaptive_resampling": True,
        "validation_never_affects_selection": True,
        "fitness_contains_no_memory_information_or_renewal_metric": True,
        "resource_cost_is_identical_across_selected_arms": True,
    }
    if selection_settings:
        registration["selection_settings"] = selection_settings
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing co-option evolution registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    work = [
        (
            spec.to_dict(),
            treatment,
            index,
            str(populations),
            protocol_digest,
            seed,
            selection_settings or None,
        )
        for treatment in selected_treatments
        for index in range(tasks_count)
    ]
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_population_task, item) for item in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-ph-cooption-evolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(work),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(work) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"co-option evolution {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (value["treatment"], value["population_index"]))
    pairing = all(
        len(
            {
                value["task"]["task_digest"]
                for value in completed
                if int(value["population_index"]) == task_index
            }
        )
        == 1
        for task_index in range(tasks_count)
    )
    _atomic_json(
        destination / "analysis.json",
        {
            "format": "gre-wagner-ph-cooption-evolution-analysis-v1",
            "selection_data_are_not_heldout_evidence": True,
            "paired_task_indices": pairing,
            "population_count": len(completed),
            "training_overfit_by_population": {
                value["population_id"]: value["trace"][-1]["training_minus_validation"]
                for value in completed
            },
        },
    )
    _atomic_json(
        destination / "manifest.json",
        {
            "format": EVOLUTION_MANIFEST_FORMAT,
            "protocol_digest": protocol_digest,
            "population_count": len(completed),
            "expected_population_count": len(work),
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_cooption_evolution(destination)
    return destination


def verify_cooption_evolution(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != EVOLUTION_REGISTRATION_FORMAT:
        raise ValueError("co-option evolution registration format mismatch")
    if manifest.get("format") != EVOLUTION_MANIFEST_FORMAT:
        raise ValueError("co-option evolution manifest format mismatch")
    spec = CooptionSpec.from_dict(registration["protocol"])
    digest_payload: dict[str, Any] = {
        "spec": spec.to_dict(),
        "treatments": tuple(registration["treatments"]),
        "task_count": int(registration["task_count"]),
        "master_seed": registration["master_seed"],
    }
    if registration.get("selection_settings"):
        digest_payload["selection_settings"] = registration["selection_settings"]
    digest = canonical_digest(digest_payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("co-option evolution protocol digest mismatch")
    expected = len(registration["treatments"]) * int(registration["task_count"])
    files = [
        path
        for path in (directory / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    ]
    if len(files) != expected or int(manifest["population_count"]) != expected:
        raise ValueError("co-option evolution population count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"population protocol mismatch: {path.name}")
        expected_digest = canonical_digest(
            {
                "selected": value["selected"],
                "score": value["selected_training_score"],
                "trace": value["trace"],
            }
        )
        if value.get("result_digest") != expected_digest:
            raise ValueError(f"population result digest mismatch: {path.name}")
    return {"verified": True, "populations": expected, "checksums": len(checksums)}


def replay_cooption_population(directory: Path, population_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    spec = CooptionSpec.from_dict(registration["protocol"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    genotype = deserialize_genotype(archived["selected"])
    replayed = training_score(
        genotype,
        archived["task"],
        spec,
        str(archived["treatment"]),
        int(archived["population_index"]),
        spec.generations,
        master_seed=str(registration["master_seed"]),
        predictive_persistence=float(
            registration.get("selection_settings", {}).get(
                "predictive_persistence", 0.9
            )
        ),
        resource_cost_multiplier=float(
            registration.get("selection_settings", {}).get(
                "resource_cost_multiplier", 1.0
            )
        ),
    )
    return {
        "population_id": population_id,
        "matches": canonical_digest(replayed)
        == canonical_digest(archived["selected_training_score"]),
        "archived_score": archived["selected_training_score"],
        "replayed_score": replayed,
    }
