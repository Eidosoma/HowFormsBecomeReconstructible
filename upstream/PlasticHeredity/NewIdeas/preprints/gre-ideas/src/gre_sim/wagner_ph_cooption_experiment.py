"""Carrier-meaning assays shared by co-option evolution and held-out audits."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any

import numpy as np

from .artifacts import canonical_digest
from .landscape import int_to_signs
from .local_ph_config import LocalCarrierGenome
from .local_ph_dynamics import LocalCarrierState, blank_local, structural_mask, write_local
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import (
    AttractorPair,
    balanced_midpoints,
    cue_nodes,
    damage_state,
    develop_memory_cycle,
    forced_break_state,
    select_attractor_pair,
    summarize_memory_future,
)
from .rng import rng_for
from .wagner import WagnerRulebook
from .wagner_ph_cooption_config import (
    COOPTION_ATLAS_RESULT_FORMAT,
    COOPTION_TASK_FORMAT,
    MEANING_INTERVENTIONS,
    CooptionSpec,
    QuantizedCarrierGenome,
)
from .wagner_ph_ladder_experiment import quantize_carrier


def local_carrier(genome: QuantizedCarrierGenome, name: str = "candidate") -> LocalCarrierGenome:
    result = LocalCarrierGenome(
        name=name,
        write_rate=genome.write_rate,
        decay=genome.decay,
        coupling=genome.coupling,
        hysteresis=genome.hysteresis,
        topology=genome.topology,
        k=genome.k,
    )
    result.validate()
    return result


def carrier_resource_cost(genome: QuantizedCarrierGenome, spec: CooptionSpec) -> float:
    """Resource cost with precision charged explicitly and a 0.10 maximum."""

    genome.validate(spec.genes)
    return float(
        spec.capacity_cost * genome.k / spec.genes
        + spec.precision_cost
        * (genome.k / spec.genes)
        * (genome.bits_per_mark - 2)
        / 6.0
        + spec.writing_cost * genome.write_rate
        + spec.coupling_cost * genome.coupling
    )


def quantized_write(
    inherited: LocalCarrierState,
    adults: tuple[int, ...],
    genome: QuantizedCarrierGenome,
    mask: tuple[int, ...],
) -> LocalCarrierState:
    written = write_local(inherited, adults, local_carrier(genome), mask)
    return quantize_carrier(written, mask, genome.bits_per_mark)


def quantized_copy(
    state: LocalCarrierState,
    genome: QuantizedCarrierGenome,
    mask: tuple[int, ...],
    spec: CooptionSpec,
    random: np.random.Generator,
) -> LocalCarrierState:
    values = np.asarray(state.values, dtype=float).copy()
    allowed = np.zeros(spec.genes, dtype=bool)
    allowed[list(mask)] = True
    values[~allowed] = 0.0
    values[allowed] *= (1.0 - genome.decay) * spec.noise.dilution
    if spec.noise.sigma:
        noise = random.normal(0.0, spec.noise.sigma, size=spec.genes)
        values[allowed] += noise[allowed]
    dropped = random.random(spec.genes) < spec.noise.dropout
    values[dropped | ~allowed] = 0.0
    bounded = LocalCarrierState(
        tuple(float(value) for value in np.clip(values, -1.0, 1.0))
    )
    return quantize_carrier(bounded, mask, genome.bits_per_mark)


def _pair(task: dict[str, Any]) -> AttractorPair:
    value = task["pair"]
    return AttractorPair(
        int(value["left_index"]),
        int(value["right_index"]),
        int(value["left_state"]),
        int(value["right_state"]),
    )


def validate_task(task: dict[str, Any]) -> None:
    if task.get("format") != COOPTION_TASK_FORMAT:
        raise ValueError("co-option task format mismatch")
    payload = dict(task)
    archived = payload.pop("task_digest", None)
    if archived != canonical_digest(payload):
        raise ValueError("co-option task digest mismatch")


def sample_cooption_task(
    spec: CooptionSpec,
    task_index: int,
    domain: str,
    *,
    master_seed: str | None = None,
) -> dict[str, Any]:
    """Sample an eligible two-form task without inspecting any assay outcome."""

    seed = master_seed or spec.master_seed
    task_id = f"{domain}-task-{task_index:03d}"
    for proposal in range(100_000):
        founder = WagnerRulebook.random(
            spec.genes,
            rng_for(seed, "cooption-founder", domain, task_index, proposal),
        )
        viewed = MechanismRulebook(founder, "wagner_sequential")
        landscape = viewed.landscape()
        pair = select_attractor_pair(landscape, spec.genes, 0.05, 0.40)
        if pair is None:
            continue
        ordering = tuple(
            int(value)
            for value in rng_for(
                seed, "cooption-order", domain, task_index
            ).permutation(spec.genes)
        )
        midpoint = int(
            balanced_midpoints(pair, spec.genes, np.asarray(ordering), 1)[0]
        )
        forced = {
            history: forced_break_state(
                landscape, pair.index(history), pair.state(history), spec.genes
            )
            for history in ("A", "B")
        }
        shuffle = ordering[1:] + ordering[:1]
        result = {
            "format": COOPTION_TASK_FORMAT,
            "task_id": task_id,
            "task_index": task_index,
            "domain": domain,
            "proposal_index": proposal,
            "founder": founder.to_dict(),
            "pair": {
                "left_index": pair.left_index,
                "right_index": pair.right_index,
                "left_state": pair.left_state,
                "right_state": pair.right_state,
            },
            "midpoint": midpoint,
            "ordering": list(ordering),
            "shuffle_permutation": list(shuffle),
            "forced_breaks": forced,
            "selection_is_outcome_blind": True,
            "neutral_pre_cue_state_is_shared_between_histories": True,
        }
        result["task_digest"] = canonical_digest(result)
        return result
    raise RuntimeError(f"could not sample eligible co-option task: {task_id}")


def _history_sequence(
    seed: str,
    task: dict[str, Any],
    scope: str,
    initial: str,
    future_index: int,
    persistence: float,
    generations: int,
) -> tuple[str, ...]:
    values = [initial]
    random = rng_for(
        seed,
        "cooption-ecology-sequence",
        scope,
        task["task_id"],
        future_index,
        persistence,
        initial,
    )
    for _ in range(generations):
        previous = values[-1]
        values.append(
            previous if random.random() < persistence else ("B" if previous == "A" else "A")
        )
    return tuple(values)


def _independent_sequence(
    seed: str,
    task: dict[str, Any],
    scope: str,
    future_index: int,
    persistence: float,
    generations: int,
) -> tuple[str, ...]:
    """Balanced donor stream exactly independent of the recipient's initial label."""

    initial = "A" if future_index % 2 == 0 else "B"
    values = [initial]
    random = rng_for(
        seed,
        "cooption-independent-donor-sequence",
        scope,
        task["task_id"],
        future_index,
        persistence,
    )
    for _ in range(generations):
        previous = values[-1]
        values.append(
            previous if random.random() < persistence else ("B" if previous == "A" else "A")
        )
    return tuple(values)


def _adult_training(
    rulebook: WagnerRulebook,
    task: dict[str, Any],
    spec: CooptionSpec,
    history: str,
    future_index: int,
    generation: int,
    scope: str,
    seed: str,
) -> tuple[int, ...]:
    viewed = MechanismRulebook(rulebook, "wagner_sequential")
    pair = _pair(task)
    base = int(task["midpoint"])
    target = pair.state(history)
    nodes = cue_nodes(
        pair, spec.genes, 1.0, np.asarray(task["ordering"], dtype=int)
    )
    state = base
    adults: list[int] = []
    for cycle in range(spec.cue_dwell):
        common = (
            seed,
            "cooption-adult-training",
            scope,
            task["task_id"],
            history,
            future_index,
            generation,
            cycle,
        )
        developed = develop_memory_cycle(
            viewed,
            state,
            base,
            np.zeros(spec.genes, dtype=float),
            1.0,
            spec.expression_flip_probability,
            0.0,
            0.0,
            0.0,
            100,
            rng_for(*common, "carry"),
            rng_for(*common, "mark"),
            rng_for(*common, "dynamics"),
            cue_target=target,
            clamped_nodes=nodes,
            write_mark=False,
        )
        state = int(developed.state)
        adults.append(state)
    return tuple(adults)


def _assay_carrier(
    rulebook: WagnerRulebook,
    task: dict[str, Any],
    spec: CooptionSpec,
    carrier: LocalCarrierState,
    coupling: float,
    history: str,
    future_index: int,
    generation: int,
    cue_fraction: float,
    scope: str,
    seed: str,
    *,
    damaged_start: bool = False,
) -> dict[str, Any]:
    """Assay prediction from a shared midpoint, optionally after target-blind damage."""

    viewed = MechanismRulebook(rulebook, "wagner_sequential")
    pair = _pair(task)
    base = int(task["midpoint"])
    state = base
    if damaged_start:
        state, _ = damage_state(
            base,
            spec.genes,
            0.20,
            rng_for(seed, "cooption-homeostasis-damage", scope, task["task_id"], future_index, generation),
        )
    nodes: tuple[int, ...] = ()
    if cue_fraction > 0.0:
        nodes = cue_nodes(
            pair,
            spec.genes,
            cue_fraction,
            np.asarray(task["ordering"], dtype=int),
        )
    post = []
    for cycle in range(spec.horizon):
        common = (
            seed,
            "cooption-assay",
            scope,
            task["task_id"],
            future_index,
            generation,
            cue_fraction,
            cycle,
        )
        developed = develop_memory_cycle(
            viewed,
            state,
            base,
            np.asarray(carrier.values, dtype=float),
            1.0,
            spec.expression_flip_probability,
            0.0,
            coupling,
            0.0,
            100,
            rng_for(*common, "carry"),
            rng_for(*common, "mark"),
            rng_for(*common, "dynamics"),
            cue_target=pair.state(history) if nodes and cycle < spec.cue_dwell else None,
            clamped_nodes=nodes if cycle < spec.cue_dwell else (),
            write_mark=False,
        )
        post.append(developed)
        state = int(developed.state)
    summary = summarize_memory_future(
        (),
        tuple(post),
        pair,
        history,
        np.asarray(carrier.values, dtype=float),
        spec.strict_run,
        spec.stable_run,
    )
    return {
        "correct": float(summary.correct_hold8),
        "wrong": float(summary.wrong_hold8),
        "functional": float(summary.correct_hold8 or summary.wrong_hold8),
        "returned": float(summary.returned),
        "convergence_cycle": float(
            summary.return_cycle if summary.return_cycle is not None else spec.horizon
        ),
        "mean_development_steps": float(np.mean([value.steps for value in post])),
        "trace_digest": summary.trace_digest,
    }


def _permuted(state: LocalCarrierState, permutation: tuple[int, ...]) -> LocalCarrierState:
    return LocalCarrierState(tuple(float(state.values[index]) for index in permutation))


def _opposite(history: str) -> str:
    return "B" if history == "A" else "A"


def simulate_ecology_condition(
    rulebook: WagnerRulebook,
    task: dict[str, Any],
    genome: QuantizedCarrierGenome,
    spec: CooptionSpec,
    intervention: str,
    persistence: float,
    cue_fraction: float,
    futures_per_history: int,
    generations: int,
    checkpoints: tuple[int, ...],
    scope: str,
    *,
    master_seed: str | None = None,
) -> dict[str, Any]:
    """Simulate a prospective ecology with content and mechanism interventions."""

    validate_task(task)
    genome.validate(spec.genes)
    if intervention not in MEANING_INTERVENTIONS:
        raise ValueError(f"unknown carrier-meaning intervention: {intervention}")
    if not 0.0 <= persistence <= 1.0 or not 0.0 <= cue_fraction <= 1.0:
        raise ValueError("ecology parameters must lie in [0, 1]")
    seed = master_seed or spec.master_seed
    mask = structural_mask(rulebook, local_carrier(genome))
    permutation = tuple(int(value) for value in task["shuffle_permutation"])
    counts: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    decoder_rows: list[dict[str, Any]] = []
    checkpoints_set = set(checkpoints)
    for initial_history in ("A", "B"):
        for future_index in range(futures_per_history):
            recipient = _history_sequence(
                seed,
                task,
                scope,
                initial_history,
                future_index,
                persistence,
                generations,
            )
            donor = _independent_sequence(
                seed,
                task,
                scope,
                future_index,
                persistence,
                generations,
            )

            def writer_history(generation: int) -> str:
                if intervention == "independent_history":
                    return donor[generation]
                if intervention == "opposite_history":
                    return _opposite(recipient[generation])
                return recipient[generation]

            if intervention in {"zero", "founder_write_off"}:
                native = blank_local(spec.genes)
            else:
                adults = _adult_training(
                    rulebook,
                    task,
                    spec,
                    writer_history(0),
                    future_index,
                    0,
                    scope,
                    seed,
                )
                native = quantized_write(
                    blank_local(spec.genes), adults, genome, mask
                )
                native = quantized_copy(
                    native,
                    genome,
                    mask,
                    spec,
                    rng_for(seed, "cooption-copy", scope, task["task_id"], future_index, 0),
                )
            for generation in range(1, generations + 1):
                incoming = (
                    _permuted(native, permutation)
                    if intervention == "shuffle"
                    else native
                )
                if generation in checkpoints_set:
                    outcome = _assay_carrier(
                        rulebook,
                        task,
                        spec,
                        incoming,
                        0.0 if intervention in {"zero", "reader_off"} else genome.coupling,
                        recipient[generation],
                        future_index,
                        generation,
                        cue_fraction,
                        scope,
                        seed,
                    )
                    cell = counts[generation]
                    cell["n"] += 1.0
                    for field in (
                        "correct",
                        "wrong",
                        "functional",
                        "returned",
                        "convergence_cycle",
                        "mean_development_steps",
                    ):
                        cell[field] += float(outcome[field])
                    values = np.asarray(incoming.values, dtype=float)
                    cell["carrier_norm"] += float(np.mean(np.abs(values)))
                    cell["nonzero_marks"] += float(np.sum(values != 0.0))
                    if generation == generations:
                        decoder_rows.append(
                            {
                                "parent_history": recipient[generation - 1],
                                "recipient_history": recipient[generation],
                                "donor_history": writer_history(generation - 1),
                                "initial_history": initial_history,
                                "future_index": future_index,
                                "carrier_values": [float(value) for value in incoming.values],
                            }
                        )
                if generation == generations:
                    continue
                if intervention == "zero":
                    native = blank_local(spec.genes)
                    continue
                carrier = native
                if intervention != "renewal_off":
                    adults = _adult_training(
                        rulebook,
                        task,
                        spec,
                        writer_history(generation),
                        future_index,
                        generation,
                        scope,
                        seed,
                    )
                    carrier = quantized_write(carrier, adults, genome, mask)
                native = quantized_copy(
                    carrier,
                    genome,
                    mask,
                    spec,
                    rng_for(
                        seed,
                        "cooption-copy",
                        scope,
                        task["task_id"],
                        future_index,
                        generation,
                    ),
                )
    summarized: dict[str, Any] = {}
    for generation in checkpoints:
        value = counts[generation]
        denominator = value["n"]
        summarized[str(generation)] = {
            f"{field}_rate" if field in {"correct", "wrong", "functional", "returned"} else field: (
                value[field] / denominator if denominator else None
            )
            for field in (
                "correct",
                "wrong",
                "functional",
                "returned",
                "convergence_cycle",
                "mean_development_steps",
                "carrier_norm",
                "nonzero_marks",
            )
        }
        summarized[str(generation)]["observations"] = int(denominator)
    return {
        "intervention": intervention,
        "persistence": persistence,
        "cue_fraction": cue_fraction,
        "checkpoints": summarized,
        "final_carriers": decoder_rows,
        "common_random_streams_exclude_intervention": True,
    }


def history_information(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Return per-locus plug-in MI and leave-one-out nearest-centroid decoding."""

    if not rows:
        return {"mean_locus_mutual_information_bits": 0.0, "decoder_balanced_accuracy": 0.5}
    matrix = np.asarray([value["carrier_values"] for value in rows], dtype=float)
    labels = np.asarray([0 if value["parent_history"] == "A" else 1 for value in rows], dtype=int)
    mutual: list[float] = []
    states = np.sign(matrix).astype(int) + 1
    for locus in range(matrix.shape[1]):
        information = 0.0
        for label in (0, 1):
            for mark in (0, 1, 2):
                joint = float(np.mean((labels == label) & (states[:, locus] == mark)))
                if joint == 0.0:
                    continue
                left = float(np.mean(labels == label))
                right = float(np.mean(states[:, locus] == mark))
                information += joint * float(np.log2(joint / (left * right)))
        mutual.append(information)
    predictions: list[int] = []
    retained: list[int] = []
    for index in range(len(rows)):
        train = np.arange(len(rows)) != index
        if not np.any(train & (labels == 0)) or not np.any(train & (labels == 1)):
            continue
        centroids = [np.mean(matrix[train & (labels == label)], axis=0) for label in (0, 1)]
        distances = [float(np.sum((matrix[index] - center) ** 2)) for center in centroids]
        predictions.append(0 if distances[0] <= distances[1] else 1)
        retained.append(int(labels[index]))
    recalls = []
    for label in (0, 1):
        chosen = [pred == truth for pred, truth in zip(predictions, retained) if truth == label]
        if chosen:
            recalls.append(float(np.mean(chosen)))
    return {
        "mean_locus_mutual_information_bits": float(np.mean(mutual)),
        "maximum_locus_mutual_information_bits": float(np.max(mutual)),
        "decoder_balanced_accuracy": float(np.mean(recalls)) if len(recalls) == 2 else 0.5,
    }


def anchor_carriers() -> tuple[QuantizedCarrierGenome, ...]:
    return (
        QuantizedCarrierGenome("k5.b2", 0.952, 0.002, 1.0, 3, "outgoing", 5, 2),
        QuantizedCarrierGenome("k10.b8", 0.952, 0.002, 1.0, 3, "all", 10, 8),
    )


def simulate_meaning_task(task: dict[str, Any], spec_value: dict[str, Any]) -> dict[str, Any]:
    spec = CooptionSpec.from_dict(spec_value)
    validate_task(task)
    rulebook = WagnerRulebook.from_dict(task["founder"])
    cells: list[dict[str, Any]] = []
    for genome in anchor_carriers():
        for persistence in spec.atlas_persistence:
            for cue_fraction in spec.cue_fractions:
                conditions = {
                    intervention: simulate_ecology_condition(
                        rulebook,
                        task,
                        genome,
                        spec,
                        intervention,
                        persistence,
                        cue_fraction,
                        spec.atlas_futures_per_history,
                        spec.lineage_generations,
                        spec.checkpoints,
                        "meaning-atlas",
                    )
                    for intervention in spec.meaning_interventions
                }
                information = history_information(conditions["natural"]["final_carriers"])
                cells.append(
                    {
                        "cell_id": f"{genome.name}.rho{persistence:.2f}.cue{cue_fraction:.2f}",
                        "carrier": genome.to_dict(),
                        "persistence": persistence,
                        "cue_fraction": cue_fraction,
                        "conditions": conditions,
                        "history_information": information,
                    }
                )
    result = {
        "format": COOPTION_ATLAS_RESULT_FORMAT,
        "task_id": task["task_id"],
        "task_digest": task["task_digest"],
        "neutral_pre_cue_state_is_identical_between_histories": True,
        "independent_donor_is_balanced_and_recipient_independent": True,
        "cells": cells,
    }
    result["result_digest"] = canonical_digest(result)
    return result
