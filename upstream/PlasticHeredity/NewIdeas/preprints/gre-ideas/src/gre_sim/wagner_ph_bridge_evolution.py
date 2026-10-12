"""Joint evolution of Wagner weights and a target-blind local carrier."""

from __future__ import annotations

import collections
import concurrent.futures
import multiprocessing
import time
from dataclasses import replace
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
from .local_ph_config import LocalCarrierGenome, LocalConditionSpec, LocalStudySpec
from .local_ph_study import simulate_local_source
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import (
    AttractorPair,
    balanced_midpoints,
    cue_nodes,
    forced_break_state,
    select_attractor_pair,
)
from .rng import rng_for
from .wagner import WagnerRulebook, mutate_wagner, recombine_wagner
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_bridge_config import (
    BRIDGE_EVOLUTION_FORMAT,
    BRIDGE_EVOLUTION_MANIFEST_FORMAT,
    CoevolutionSpec,
)


EVOLUTION_REGISTRATION_FORMAT = "gre-wagner-ph-bridge-coevolution-registration-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def resource_cost(carrier: LocalCarrierGenome, spec: CoevolutionSpec) -> float:
    """Frozen normalized carrier cost, capped at one tenth fitness unit."""

    return float(
        spec.capacity_cost * carrier.k / spec.genes
        + spec.coupling_cost * carrier.coupling
        + spec.writing_cost * carrier.write_rate
    )


def _carrier_payload(carrier: LocalCarrierGenome) -> dict[str, Any]:
    value = carrier.to_dict()
    value.pop("name")
    return value


def _named_carrier(payload: dict[str, Any]) -> LocalCarrierGenome:
    normalized = {
        "write_rate": round(float(payload["write_rate"]), 3),
        "decay": round(float(payload["decay"]), 3),
        "coupling": round(float(payload["coupling"]), 3),
        "hysteresis": int(payload["hysteresis"]),
        "topology": str(payload["topology"]),
        "k": int(payload["k"]),
    }
    if normalized["topology"] == "all":
        normalized["k"] = 10
    result = LocalCarrierGenome(
        f"coevolved-{canonical_digest(normalized)[:12]}", **normalized
    )
    result.validate()
    return result


def _genotype_id(rulebook: WagnerRulebook, carrier: LocalCarrierGenome) -> str:
    return canonical_digest(
        {"rulebook": rulebook.to_dict(), "carrier": _carrier_payload(carrier)}
    )[:24]


def _serialize_genotype(
    rulebook: WagnerRulebook, carrier: LocalCarrierGenome
) -> dict[str, Any]:
    return {
        "genotype_id": _genotype_id(rulebook, carrier),
        "rulebook": rulebook.to_dict(),
        "carrier": carrier.to_dict(),
    }


def _deserialize_genotype(value: dict[str, Any]) -> tuple[WagnerRulebook, LocalCarrierGenome]:
    rulebook = WagnerRulebook.from_dict(value["rulebook"])
    carrier = LocalCarrierGenome(**value["carrier"])
    if value.get("genotype_id") != _genotype_id(rulebook, carrier):
        raise ValueError("coevolution genotype digest mismatch")
    return rulebook, carrier


def _recombine_carrier(
    left: LocalCarrierGenome,
    right: LocalCarrierGenome,
    random: np.random.Generator,
) -> LocalCarrierGenome:
    payload: dict[str, Any] = {}
    for field in ("write_rate", "decay", "coupling", "hysteresis", "topology", "k"):
        payload[field] = getattr(left if random.random() < 0.5 else right, field)
    if random.random() < 0.35:
        payload["write_rate"] = float(
            np.clip(float(payload["write_rate"]) + random.normal(0.0, 0.08), 0.10, 1.0)
        )
    if random.random() < 0.35:
        payload["decay"] = float(
            np.clip(float(payload["decay"]) + random.normal(0.0, 0.02), 0.0, 0.20)
        )
    if random.random() < 0.35:
        payload["coupling"] = float(
            np.clip(float(payload["coupling"]) + random.normal(0.0, 0.08), 0.10, 1.0)
        )
    if random.random() < 0.20:
        payload["hysteresis"] = int(
            np.clip(int(payload["hysteresis"]) + int(random.integers(-1, 2)), 1, 3)
        )
    if random.random() < 0.20:
        payload["k"] = (1, 2, 3, 5, 7, 10)[int(random.integers(6))]
    if random.random() < 0.15:
        payload["topology"] = ("all", "outgoing", "self_feedback")[
            int(random.integers(3))
        ]
    if payload["topology"] == "all":
        payload["k"] = 10
    return _named_carrier(payload)


def _mutate_genotype(
    left: tuple[WagnerRulebook, LocalCarrierGenome],
    right: tuple[WagnerRulebook, LocalCarrierGenome],
    random: np.random.Generator,
) -> tuple[WagnerRulebook, LocalCarrierGenome]:
    rulebook = mutate_wagner(recombine_wagner(left[0], right[0], random), random)
    return rulebook, _recombine_carrier(left[1], right[1], random)


def _sample_task(spec: CoevolutionSpec, population_index: int) -> dict[str, Any]:
    """Create the same founder task for all four treatments at one population index."""

    task_id = f"population-{population_index:03d}"
    for proposal in range(100_000):
        founder = WagnerRulebook.random(
            spec.genes,
            rng_for(spec.master_seed, "coevolution-founder", task_id, proposal),
        )
        viewed = MechanismRulebook(founder, "wagner_sequential")
        landscape = viewed.landscape()
        pair = select_attractor_pair(landscape, spec.genes, 0.05, 0.40)
        if pair is None:
            continue
        ordering = tuple(
            int(value)
            for value in rng_for(spec.master_seed, "coevolution-order", task_id).permutation(
                spec.genes
            )
        )
        midpoint = int(
            balanced_midpoints(pair, spec.genes, np.asarray(ordering, dtype=int), 1)[0]
        )
        nodes = tuple(
            int(value)
            for value in cue_nodes(
                pair, spec.genes, 1.0, np.asarray(ordering, dtype=int)
            )
        )
        forced = {
            history: forced_break_state(
                landscape, pair.index(history), pair.state(history), spec.genes
            )
            for history in ("A", "B")
        }
        return {
            "task_id": task_id,
            "founder": founder.to_dict(),
            "pair": {
                "left_index": pair.left_index,
                "right_index": pair.right_index,
                "left_state": pair.left_state,
                "right_state": pair.right_state,
            },
            "midpoint": midpoint,
            "nodes": list(nodes),
            "ordering": list(ordering),
            "forced_breaks": forced,
            "founder_landscape": landscape.to_dict(),
        }
    raise RuntimeError(f"could not sample coevolution founder task: {task_id}")


def _source(
    task: dict[str, Any], rulebook: WagnerRulebook, source_id: str
) -> dict[str, Any]:
    ordering = tuple(int(value) for value in task["ordering"])
    metadata = {
        "pair": dict(task["pair"]),
        "midpoints": [int(task["midpoint"])],
        "node_order": list(ordering),
        "mark_permutation": list(ordering[1:] + ordering[:1]),
        "ablation_order": list(reversed(ordering)),
        "forced_breaks": dict(task["forced_breaks"]),
        "landscape": task["founder_landscape"],
        "task_is_frozen_across_treatments": True,
    }
    return {
        "source_set": "wagner_n10_coevolution",
        "source_id": source_id,
        "engine": "wagner",
        "genes": rulebook.genes,
        "proposal_index": 0,
        "source": rulebook.to_dict(),
        "models": {"wagner.lineage": metadata},
    }


def _alias(carrier: LocalCarrierGenome) -> LocalCarrierGenome:
    return replace(carrier, name="candidate")


def _assay_genotype(
    rulebook: WagnerRulebook,
    carrier: LocalCarrierGenome,
    task: dict[str, Any],
    spec: CoevolutionSpec,
    source_id: str,
    label: str,
    replicates: int,
    checkpoints: tuple[int, ...],
    challenges: tuple[str, ...],
    causal: bool,
) -> dict[str, Any]:
    candidate = _alias(carrier)
    conditions = [
        LocalConditionSpec("candidate.intact", "candidate", "intact", "nominal", True),
        LocalConditionSpec("candidate.strong", "candidate", "intact", "strong"),
    ]
    if causal:
        conditions.extend(
            (
                LocalConditionSpec(
                    "candidate.founder-write-off", "candidate", "founder_write_off", "nominal"
                ),
                LocalConditionSpec(
                    "candidate.renewal-off", "candidate", "renewal_off", "nominal"
                ),
                LocalConditionSpec("candidate.reader-off", "candidate", "reader_off", "nominal"),
                LocalConditionSpec("candidate.erase-g2", "candidate", "erase_g2", "nominal"),
                LocalConditionSpec("candidate.reverse-g2", "candidate", "reverse_g2", "nominal"),
                LocalConditionSpec(
                    "candidate.erase-g2-rescue-g3",
                    "candidate",
                    "erase_g2_rescue_g3",
                    "nominal",
                ),
            )
        )
    conditions.append(LocalConditionSpec("zero", None, "zero", "nominal"))
    study = LocalStudySpec(
        f"{spec.cohort_id}.{label}",
        f"coevolution-heldout.{label}",
        spec.master_seed,
        1,
        (candidate,),
        (spec.nominal_noise, spec.strong_noise),
        tuple(conditions),
        checkpoint_generations=checkpoints,
        challenges=challenges,
        futures_per_history=replicates,
        generation_cycles=spec.generation_cycles,
        horizon=spec.horizon,
        strict_run=spec.strict_run,
        stable_run=spec.stable_run,
        expression_flip_probability=spec.expression_flip_probability,
        bootstrap_repetitions=64,
        exploratory=True,
    )
    study.validate()
    rows = simulate_local_source(_source(task, rulebook, source_id), study.to_dict())
    counts: dict[tuple[str, int, str], dict[str, float]] = collections.defaultdict(
        lambda: {"correct": 0.0, "wrong": 0.0, "acquired": 0.0, "n": 0.0}
    )
    for record in rows:
        key = (str(record["condition"]), int(record["generation"]), str(record["challenge"]))
        counts[key]["correct"] += float(record["correct_hold8"])
        counts[key]["wrong"] += float(record["wrong_hold8"])
        counts[key]["acquired"] += float(record["acquired"])
        counts[key]["n"] += 1.0
    cells: dict[str, Any] = {}
    for condition in (value.name for value in conditions):
        generations: dict[str, Any] = {}
        for generation in checkpoints:
            events: dict[str, Any] = {}
            for challenge in challenges:
                value = counts[(condition, generation, challenge)]
                denominator = value["n"]
                events[challenge] = {
                    "correct_rate": value["correct"] / denominator if denominator else None,
                    "wrong_rate": value["wrong"] / denominator if denominator else None,
                    "acquisition_rate": value["acquired"] / denominator if denominator else None,
                }
            generations[str(generation)] = events
        cells[condition] = generations
    for condition, generations in cells.items():
        if condition == "zero":
            continue
        for generation, events in generations.items():
            for challenge, value in events.items():
                zero = cells["zero"][generation][challenge]
                value["risk_gain"] = (
                    float(value["correct_rate"]) - float(zero["correct_rate"])
                    if value["correct_rate"] is not None and zero["correct_rate"] is not None
                    else None
                )
    return {"cells": cells, "record_count": len(rows), "digest": canonical_digest(cells)}


def _training_score(
    genotype: tuple[WagnerRulebook, LocalCarrierGenome],
    task: dict[str, Any],
    spec: CoevolutionSpec,
    treatment: str,
    population_index: int,
    generation: int,
) -> dict[str, float]:
    if treatment == "neutral_drift":
        return {"phenotype": 0.0, "resource_cost": resource_cost(genotype[1], spec), "fitness": 0.0}
    endpoint = 0 if treatment == "acute_performance_cost" else 4
    checkpoints = (0,) if endpoint == 0 else (0, endpoint)
    assay = _assay_genotype(
        genotype[0],
        genotype[1],
        task,
        spec,
        f"training.population-{population_index:03d}.generation-{generation:03d}",
        f"training.{population_index}.{generation}",
        spec.training_replicates,
        checkpoints,
        ("forced_break",),
        False,
    )
    phenotype = float(
        assay["cells"]["candidate.intact"][str(endpoint)]["forced_break"]["risk_gain"]
    )
    cost = resource_cost(genotype[1], spec)
    fitness = phenotype
    if treatment in {"descendant_memory_cost", "acute_performance_cost"}:
        fitness -= cost
    return {"phenotype": phenotype, "resource_cost": cost, "fitness": fitness}


def _tournament(
    fitnesses: np.ndarray,
    random: np.random.Generator,
    size: int,
) -> int:
    candidates = random.integers(0, len(fitnesses), size=size)
    return int(max(candidates, key=lambda value: (fitnesses[int(value)], -int(value))))


def _population_task(args: tuple[dict[str, Any], str, int, str, str]) -> dict[str, Any]:
    spec_value, treatment, population_index, output_text, protocol_digest = args
    spec = CoevolutionSpec.from_dict(spec_value)
    population_id = f"{treatment}.population-{population_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"coevolution population registration differs: {final_path}")
    checkpoint_path = output / f"{population_id}.checkpoint.json"
    task = _sample_task(spec, population_index)
    if checkpoint_path.is_file():
        saved = read_json(checkpoint_path)
        if saved.get("protocol_digest") != protocol_digest:
            raise ValueError("coevolution checkpoint protocol differs")
        population = [_deserialize_genotype(value) for value in saved["population"]]
        lineage_ids = [str(value) for value in saved["lineage_ids"]]
        fitness = np.asarray(saved["fitness"], dtype=float)
        phenotype = np.asarray(saved["phenotype"], dtype=float)
        cost = np.asarray(saved["cost"], dtype=float)
        ancestry = list(saved["ancestry"])
        trace = list(saved["trace"])
        start_generation = int(saved["generation"]) + 1
    else:
        founder = WagnerRulebook.from_dict(task["founder"])
        founder_genotype = (founder, spec.initial_carrier)
        population = [founder_genotype]
        for index in range(1, spec.population_size):
            random = rng_for(spec.master_seed, "coevolution-initial", population_index, index)
            population.append(_mutate_genotype(founder_genotype, founder_genotype, random))
        scores = [
            _training_score(value, task, spec, treatment, population_index, 0)
            for value in population
        ]
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        phenotype = np.asarray([value["phenotype"] for value in scores], dtype=float)
        cost = np.asarray([value["resource_cost"] for value in scores], dtype=float)
        lineage_ids = [
            canonical_digest((population_id, 0, index, _genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry = [
            {
                "generation": 0,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        "parent_ids": [],
                        **_serialize_genotype(*value),
                        "phenotype": float(phenotype[index]),
                        "resource_cost": float(cost[index]),
                        "fitness": float(fitness[index]),
                    }
                    for index, value in enumerate(population)
                ],
            }
        ]
        trace = [
            {
                "generation": 0,
                "mean_fitness": float(np.mean(fitness)),
                "best_fitness": float(np.max(fitness)),
                "mean_phenotype": float(np.mean(phenotype)),
                "mean_capacity": float(np.mean([value[1].k for value in population])),
            }
        ]
        start_generation = 1
    for generation in range(start_generation, spec.generations + 1):
        random = rng_for(
            spec.master_seed, "coevolution-generation", treatment, population_index, generation
        )
        following: list[tuple[WagnerRulebook, LocalCarrierGenome]] = []
        parents: list[tuple[str, ...]] = []
        if treatment != "neutral_drift":
            elite_indices = sorted(
                range(len(population)), key=lambda value: (-fitness[value], value)
            )[: spec.elite_count]
            for index in elite_indices:
                following.append(population[index])
                parents.append((lineage_ids[index],))
        while len(following) < spec.population_size:
            if treatment == "neutral_drift":
                left_index = int(random.integers(len(population)))
                right_index = int(random.integers(len(population)))
            else:
                left_index = _tournament(fitness, random, spec.tournament_size)
                right_index = _tournament(fitness, random, spec.tournament_size)
            following.append(
                _mutate_genotype(population[left_index], population[right_index], random)
            )
            parents.append((lineage_ids[left_index], lineage_ids[right_index]))
        population = following
        scores = [
            _training_score(value, task, spec, treatment, population_index, generation)
            for value in population
        ]
        fitness = np.asarray([value["fitness"] for value in scores], dtype=float)
        phenotype = np.asarray([value["phenotype"] for value in scores], dtype=float)
        cost = np.asarray([value["resource_cost"] for value in scores], dtype=float)
        lineage_ids = [
            canonical_digest((population_id, generation, index, _genotype_id(*value)))[:24]
            for index, value in enumerate(population)
        ]
        ancestry.append(
            {
                "generation": generation,
                "individuals": [
                    {
                        "lineage_id": lineage_ids[index],
                        "parent_ids": list(parents[index]),
                        **_serialize_genotype(*value),
                        "phenotype": float(phenotype[index]),
                        "resource_cost": float(cost[index]),
                        "fitness": float(fitness[index]),
                    }
                    for index, value in enumerate(population)
                ],
            }
        )
        trace.append(
            {
                "generation": generation,
                "mean_fitness": float(np.mean(fitness)),
                "best_fitness": float(np.max(fitness)),
                "mean_phenotype": float(np.mean(phenotype)),
                "mean_capacity": float(np.mean([value[1].k for value in population])),
            }
        )
        _atomic_json(
            checkpoint_path,
            {
                "format": "gre-wagner-ph-bridge-coevolution-checkpoint-v1",
                "protocol_digest": protocol_digest,
                "generation": generation,
                "population": [_serialize_genotype(*value) for value in population],
                "lineage_ids": lineage_ids,
                "fitness": fitness.tolist(),
                "phenotype": phenotype.tolist(),
                "cost": cost.tolist(),
                "ancestry": ancestry,
                "trace": trace,
            },
        )
    selected_index = 0 if treatment == "neutral_drift" else int(np.argmax(fitness))
    selected = population[selected_index]
    founder_genotype = (
        WagnerRulebook.from_dict(task["founder"]),
        spec.initial_carrier,
    )
    heldout_source = f"heldout.population-{population_index:03d}"
    founder_heldout = _assay_genotype(
        *founder_genotype,
        task,
        spec,
        heldout_source,
        f"heldout.population-{population_index:03d}",
        spec.heldout_replicates,
        (0, 4, 8, 16),
        ("forced_break", "release_only"),
        False,
    )
    selected_heldout = _assay_genotype(
        *selected,
        task,
        spec,
        heldout_source,
        f"heldout.population-{population_index:03d}",
        spec.heldout_replicates,
        (0, 4, 8, 16),
        ("forced_break", "release_only"),
        True,
    )
    parent_offspring_pairs: list[dict[str, float]] = []
    if treatment == "descendant_memory_cost":
        for offspring_index in range(spec.heritability_offspring):
            random = rng_for(
                spec.master_seed,
                "coevolution-heritability",
                population_index,
                offspring_index,
            )
            offspring = _mutate_genotype(selected, selected, random)
            pair_source = (
                f"heritability.population-{population_index:03d}.offspring-{offspring_index:03d}"
            )
            parent_score = _assay_genotype(
                *selected,
                task,
                spec,
                pair_source,
                pair_source,
                max(4, spec.heldout_replicates // 2),
                (0, 8),
                ("forced_break",),
                False,
            )
            offspring_score = _assay_genotype(
                *offspring,
                task,
                spec,
                pair_source,
                pair_source,
                max(4, spec.heldout_replicates // 2),
                (0, 8),
                ("forced_break",),
                False,
            )
            parent_offspring_pairs.append(
                {
                    "parent": float(
                        parent_score["cells"]["candidate.intact"]["8"]["forced_break"]["risk_gain"]
                    ),
                    "offspring": float(
                        offspring_score["cells"]["candidate.intact"]["8"]["forced_break"]["risk_gain"]
                    ),
                }
            )
    result = {
        "format": BRIDGE_EVOLUTION_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "population_index": population_index,
        "treatment": treatment,
        "selection_endpoint": (
            "neutral"
            if treatment == "neutral_drift"
            else "generation_0_acute"
            if treatment == "acute_performance_cost"
            else "generation_4_descendant_memory"
        ),
        "selection_uses_target_label_inside_carrier": False,
        "common_heldout_source_id": heldout_source,
        "task": task,
        "founder": _serialize_genotype(*founder_genotype),
        "selected": _serialize_genotype(*selected),
        "selected_training_fitness": float(fitness[selected_index]),
        "founder_heldout": founder_heldout,
        "selected_heldout": selected_heldout,
        "parent_offspring_pairs": parent_offspring_pairs,
        "trace": trace,
        "ancestry": ancestry,
    }
    result["heldout_digest"] = canonical_digest(
        {"founder": founder_heldout, "selected": selected_heldout}
    )
    _atomic_json(final_path, result)
    if checkpoint_path.is_file():
        checkpoint_path.unlink()
    return result


def _cell(
    result: dict[str, Any],
    state: str,
    condition: str,
    generation: int,
    field: str,
    challenge: str = "forced_break",
) -> float:
    return float(
        result[f"{state}_heldout"]["cells"][condition][str(generation)][challenge][field]
    )


def _paired_treatment_values(
    results: list[dict[str, Any]], left: str, right: str
) -> list[float]:
    by_key = {(value["treatment"], int(value["population_index"])): value for value in results}
    values: list[float] = []
    indices = sorted(
        set(index for treatment, index in by_key if treatment == left)
        & set(index for treatment, index in by_key if treatment == right)
    )
    for index in indices:
        a = _cell(by_key[(left, index)], "selected", "candidate.intact", 8, "risk_gain")
        b = _cell(by_key[(right, index)], "selected", "candidate.intact", 8, "risk_gain")
        values.append(a - b)
    return values


def _correlation_interval(
    parents: list[float], offspring: list[float], spec: CoevolutionSpec
) -> dict[str, Any]:
    left = np.asarray(parents, dtype=float)
    right = np.asarray(offspring, dtype=float)
    if left.size < 3 or left.size != right.size or not np.std(left) or not np.std(right):
        return {"mean": None, "interval": [None, None], "lower": None, "populations": int(left.size)}
    point = float(np.corrcoef(left, right)[0, 1])
    random = rng_for(spec.master_seed, "coevolution-bootstrap", "parent-offspring")
    draws: list[float] = []
    for _ in range(spec.bootstrap_repetitions):
        indices = random.integers(0, left.size, left.size)
        a = left[indices]
        b = right[indices]
        if np.std(a) and np.std(b):
            draws.append(float(np.corrcoef(a, b)[0, 1]))
    tail = (1.0 - spec.interval_level) / 2.0
    return {
        "mean": point,
        "interval": [
            float(np.quantile(draws, tail)) if draws else None,
            float(np.quantile(draws, 1.0 - tail)) if draws else None,
        ],
        "lower": float(np.quantile(draws, tail)) if draws else None,
        "populations": int(left.size),
    }


def analyze_coevolution(
    results: list[dict[str, Any]], spec: CoevolutionSpec
) -> dict[str, Any]:
    grouped = {
        treatment: [value for value in results if value["treatment"] == treatment]
        for treatment in spec.treatments
    }
    treatment_summaries: dict[str, Any] = {}
    for treatment, values in grouped.items():
        heldout = [
            _cell(value, "selected", "candidate.intact", 8, "risk_gain")
            for value in values
        ]
        improvements = [
            _cell(value, "selected", "candidate.intact", 8, "risk_gain")
            - _cell(value, "founder", "candidate.intact", 8, "risk_gain")
            for value in values
        ]
        treatment_summaries[treatment] = {
            "generation_8_selected_risk_gain": _interval(
                heldout,
                spec.master_seed,
                f"coevolution.{treatment}.heldout",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "founder_to_selected_improvement": _interval(
                improvements,
                spec.master_seed,
                f"coevolution.{treatment}.improvement",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
            "median_selected_capacity": float(
                np.median([int(value["selected"]["carrier"]["k"]) for value in values])
            ) if values else None,
        }
    contrasts = {
        control: _interval(
            _paired_treatment_values(results, "descendant_memory_cost", control),
            spec.master_seed,
            f"coevolution.memory-cost.versus.{control}",
            spec.bootstrap_repetitions,
            spec.interval_level,
            2,
        )
        for control in ("acute_performance_cost", "neutral_drift")
    }
    memory = grouped["descendant_memory_cost"]
    strong_values = [
        _cell(value, "selected", "candidate.strong", 8, "risk_gain") for value in memory
    ]
    strong = _interval(
        strong_values,
        spec.master_seed,
        "coevolution.memory-cost.strong-g8",
        spec.bootstrap_repetitions,
        spec.interval_level,
    )
    erase_reductions: list[float] = []
    rescue_fractions: list[float] = []
    reversal_values: list[float] = []
    control_differences: dict[str, list[float]] = {
        "founder-write-off": [],
        "renewal-off": [],
        "reader-off": [],
    }
    for value in memory:
        intact = _cell(value, "selected", "candidate.intact", 4, "correct_rate")
        zero = _cell(value, "selected", "zero", 4, "correct_rate")
        erase = _cell(value, "selected", "candidate.erase-g2", 4, "correct_rate")
        rescue = _cell(
            value, "selected", "candidate.erase-g2-rescue-g3", 4, "correct_rate"
        )
        if intact > zero:
            erase_reductions.append((intact - erase) / (intact - zero))
        if intact > erase:
            rescue_fractions.append((rescue - erase) / (intact - erase))
        reversal_values.append(
            _cell(value, "selected", "candidate.reverse-g2", 4, "wrong_rate")
            - _cell(value, "selected", "candidate.intact", 4, "wrong_rate")
        )
        for suffix in control_differences:
            control_differences[suffix].append(
                intact
                - _cell(value, "selected", f"candidate.{suffix}", 4, "correct_rate")
            )
    causal = {
        "erasure_reduction": _interval(
            erase_reductions,
            spec.master_seed,
            "coevolution.causal.erase",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "rescue_fraction": _interval(
            rescue_fractions,
            spec.master_seed,
            "coevolution.causal.rescue",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "sign_reversal_wrong_form_gain": _interval(
            reversal_values,
            spec.master_seed,
            "coevolution.causal.reverse",
            spec.bootstrap_repetitions,
            spec.interval_level,
        ),
        "controls": {
            key: _interval(
                values,
                spec.master_seed,
                f"coevolution.causal.{key}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            )
            for key, values in control_differences.items()
        },
    }
    parent_means: list[float] = []
    offspring_means: list[float] = []
    for value in memory:
        pairs = value["parent_offspring_pairs"]
        if pairs:
            parent_means.append(float(np.mean([item["parent"] for item in pairs])))
            offspring_means.append(float(np.mean([item["offspring"] for item in pairs])))
    association = _correlation_interval(parent_means, offspring_means, spec)
    improvement = treatment_summaries["descendant_memory_cost"][
        "founder_to_selected_improvement"
    ]
    criteria = {
        "memory_cost_founder_improvement_at_least_0_05": improvement["mean"] is not None
        and float(improvement["mean"]) >= 0.05,
        "memory_cost_founder_improvement_lower_above_zero": improvement["lower"] is not None
        and float(improvement["lower"]) > 0.0,
        "beats_acute_by_at_least_0_05": contrasts["acute_performance_cost"]["mean"] is not None
        and float(contrasts["acute_performance_cost"]["mean"]) >= 0.05,
        "beats_acute_lower_above_zero": contrasts["acute_performance_cost"]["lower"] is not None
        and float(contrasts["acute_performance_cost"]["lower"]) > 0.0,
        "beats_neutral_by_at_least_0_05": contrasts["neutral_drift"]["mean"] is not None
        and float(contrasts["neutral_drift"]["mean"]) >= 0.05,
        "beats_neutral_lower_above_zero": contrasts["neutral_drift"]["lower"] is not None
        and float(contrasts["neutral_drift"]["lower"]) > 0.0,
        "strong_noise_generation_8_lower_above_zero": strong["lower"] is not None
        and float(strong["lower"]) > 0.0,
        "erasure_removes_at_least_0_70": causal["erasure_reduction"]["mean"] is not None
        and float(causal["erasure_reduction"]["mean"]) >= 0.70,
        "rescue_restores_at_least_0_70": causal["rescue_fraction"]["mean"] is not None
        and float(causal["rescue_fraction"]["mean"]) >= 0.70,
        "sign_reversal_lower_above_zero": causal["sign_reversal_wrong_form_gain"]["lower"] is not None
        and float(causal["sign_reversal_wrong_form_gain"]["lower"]) > 0.0,
        "writer_reader_renewal_controls_lower_above_zero": all(
            value["lower"] is not None and float(value["lower"]) > 0.0
            for value in causal["controls"].values()
        ),
        "parent_offspring_association_lower_above_zero": association["lower"] is not None
        and float(association["lower"]) > 0.0,
    }
    median_capacity = treatment_summaries["descendant_memory_cost"][
        "median_selected_capacity"
    ]
    return {
        "format": "gre-wagner-ph-bridge-coevolution-analysis-v1",
        "cohort_id": spec.cohort_id,
        "exploratory": True,
        "population_count": len(results),
        "common_heldout_endpoint": "generation_8_descendant_memory",
        "common_random_streams_verified": all(
            value["common_heldout_source_id"]
            == f"heldout.population-{int(value['population_index']):03d}"
            for value in results
        ),
        "carrier_target_access": False,
        "treatments": treatment_summaries,
        "contrasts": contrasts,
        "strong_noise_generation_8": strong,
        "causal_interventions": causal,
        "parent_offspring_association": association,
        "criteria": criteria,
        "evolved_bridge_nominated": all(criteria.values()),
        "compact_evolved_bridge_nominated": all(criteria.values())
        and median_capacity is not None
        and float(median_capacity) <= 5.0,
        "claim_boundary": "exploratory evolvability nomination; independent replication required",
    }


def render_coevolution_report(analysis: dict[str, Any]) -> str:
    criteria_failed = [key for key, value in analysis["criteria"].items() if not value]
    return "\n".join(
        (
            "# Wagner–local-carrier co-evolution",
            "",
            f"- Evolved bridge nomination: **{'PASS' if analysis['evolved_bridge_nominated'] else 'fail'}**",
            f"- Compact evolved bridge nomination: **{'PASS' if analysis['compact_evolved_bridge_nominated'] else 'fail'}**",
            f"- Common held-out streams: `{analysis['common_random_streams_verified']}`",
            f"- Carrier target access: `{analysis['carrier_target_access']}`",
            f"- Failed criteria: {criteria_failed or 'none'}",
            "",
            analysis["claim_boundary"],
            "",
        )
    )


def run_bridge_coevolution(
    spec: CoevolutionSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 4:
        raise ValueError("bridge coevolution permits one to four workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_bridge_coevolution(destination)
        return destination
    started = time.monotonic()
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": EVOLUTION_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
        "selection_and_heldout_endpoints_separated": True,
        "carrier_receives_target_label": False,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing bridge coevolution registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    tasks = [
        (spec.to_dict(), treatment, index, str(populations), digest)
        for treatment in spec.treatments
        for index in range(spec.populations_per_treatment)
    ]
    results: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_population_task, tasks)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        iterator = executor.map(_population_task, tasks)
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-ph-bridge-coevolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"joint Wagner/carrier evolution {index}/{len(tasks)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    analysis = analyze_coevolution(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": BRIDGE_EVOLUTION_MANIFEST_FORMAT,
            "protocol_digest": digest,
            "population_count": len(results),
            "expected_population_count": len(tasks),
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    (destination / "report.md").write_text(
        render_coevolution_report(analysis), encoding="utf-8"
    )
    write_checksums(destination)
    verify_bridge_coevolution(destination)
    return destination


def verify_bridge_coevolution(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != EVOLUTION_REGISTRATION_FORMAT:
        raise ValueError("bridge coevolution registration format mismatch")
    if manifest.get("format") != BRIDGE_EVOLUTION_MANIFEST_FORMAT:
        raise ValueError("bridge coevolution manifest format mismatch")
    spec = CoevolutionSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get("protocol_digest"):
        raise ValueError("bridge coevolution protocol digest mismatch")
    expected = spec.population_count
    if int(manifest["population_count"]) != expected:
        raise ValueError("bridge coevolution population count mismatch")
    files = list((directory / "populations").glob("*.json"))
    if len(files) != expected:
        raise ValueError("bridge coevolution population file count mismatch")
    return {"verified": True, "populations": expected, "checksums": len(checksums)}


def replay_coevolution_population(directory: Path, population_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    spec = CoevolutionSpec.from_dict(read_json(directory / "registration.json")["protocol"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    selected = _deserialize_genotype(archived["selected"])
    founder = _deserialize_genotype(archived["founder"])
    source_id = str(archived["common_heldout_source_id"])
    index = int(archived["population_index"])
    founder_heldout = _assay_genotype(
        *founder,
        archived["task"],
        spec,
        source_id,
        f"heldout.population-{index:03d}",
        spec.heldout_replicates,
        (0, 4, 8, 16),
        ("forced_break", "release_only"),
        False,
    )
    selected_heldout = _assay_genotype(
        *selected,
        archived["task"],
        spec,
        source_id,
        f"heldout.population-{index:03d}",
        spec.heldout_replicates,
        (0, 4, 8, 16),
        ("forced_break", "release_only"),
        True,
    )
    digest = canonical_digest({"founder": founder_heldout, "selected": selected_heldout})
    return {
        "population_id": population_id,
        "matches": digest == archived["heldout_digest"],
        "archived_digest": archived["heldout_digest"],
        "replayed_digest": digest,
    }
