"""Quantized capacity, coordination, and ecological assays for Origin Ladder v1."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from .artifacts import canonical_digest
from .local_ph_config import LocalCarrierGenome
from .local_ph_dynamics import (
    LocalCarrierState,
    blank_local,
    develop_local_cycle,
    structural_mask,
    write_local,
)
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import (
    AttractorPair,
    balanced_midpoints,
    cue_nodes,
    develop_memory_cycle,
    forced_break_state,
    select_attractor_pair,
    summarize_memory_future,
)
from .rng import rng_for
from .wagner import WagnerRulebook
from .wagner_ph_ladder_config import (
    LADDER_RESULT_FORMAT,
    LADDER_TASK_FORMAT,
    WagnerPHLadderSpec,
)


CAPACITY_INTERVENTIONS = (
    "intact",
    "founder_write_off",
    "reader_off",
    "renewal_off",
    "opposite_history_transplant",
    "zero",
)
ECOLOGY_INTERVENTIONS = ("intact", "reader_off", "renewal_off", "zero")
_RUNTIME_CACHE: dict[str, tuple[WagnerRulebook, MechanismRulebook]] = {}


def _runtime(task: dict[str, Any]) -> tuple[WagnerRulebook, MechanismRulebook]:
    digest = str(task["task_digest"])
    if digest not in _RUNTIME_CACHE:
        rulebook = WagnerRulebook.from_dict(task["founder"])
        _RUNTIME_CACHE[digest] = (
            rulebook,
            MechanismRulebook(rulebook, "wagner_sequential"),
        )
    return _RUNTIME_CACHE[digest]


def quantization_levels(bits: int) -> np.ndarray:
    """Return an odd symmetric alphabet with exact zero and <2**bits symbols."""

    if bits < 2 or bits > 16:
        raise ValueError("quantized carrier bits must lie in [2, 16]")
    levels = np.linspace(-1.0, 1.0, (1 << bits) - 1, dtype=float)
    levels[len(levels) // 2] = 0.0
    return levels


def quantize_carrier(
    state: LocalCarrierState, mask: tuple[int, ...], bits: int
) -> LocalCarrierState:
    """Quantize only registered loci; inactive loci remain exactly zero."""

    levels = quantization_levels(bits)
    allowed = set(int(value) for value in mask)
    values: list[float] = []
    for gene, raw in enumerate(state.values):
        if gene not in allowed:
            values.append(0.0)
            continue
        index = int(np.argmin(np.abs(levels - float(raw))))
        values.append(float(levels[index]))
    return LocalCarrierState(tuple(values))


def _pair(task: dict[str, Any]) -> AttractorPair:
    value = task["pair"]
    return AttractorPair(
        int(value["left_index"]),
        int(value["right_index"]),
        int(value["left_state"]),
        int(value["right_state"]),
    )


def _candidate(
    k: int,
    write_rate: float,
    coupling: float,
    spec: WagnerPHLadderSpec,
    label: str,
) -> LocalCarrierGenome:
    result = LocalCarrierGenome(
        name=label,
        write_rate=float(write_rate),
        decay=spec.carrier_decay,
        coupling=float(coupling),
        hysteresis=spec.carrier_hysteresis,
        topology="all" if k == spec.genes else "outgoing",
        k=int(k),
    )
    result.validate(spec.genes)
    return result


def sample_ladder_task(spec: WagnerPHLadderSpec, task_index: int) -> dict[str, Any]:
    """Sample a fresh two-attractor Wagner task without inspecting any assay."""

    task_id = f"task-{task_index:03d}"
    for proposal in range(100_000):
        founder = WagnerRulebook.random(
            spec.genes,
            rng_for(spec.master_seed, "origin-ladder-founder", task_id, proposal),
        )
        viewed = MechanismRulebook(founder, "wagner_sequential")
        landscape = viewed.landscape()
        pair = select_attractor_pair(landscape, spec.genes, 0.05, 0.40)
        if pair is None:
            continue
        ordering = tuple(
            int(value)
            for value in rng_for(
                spec.master_seed, "origin-ladder-order", task_id
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
        result = {
            "format": LADDER_TASK_FORMAT,
            "task_id": task_id,
            "task_index": task_index,
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
            "forced_breaks": forced,
            "selection_is_outcome_blind": True,
        }
        result["task_digest"] = canonical_digest(result)
        return result
    raise RuntimeError(f"could not sample eligible Wagner task: {task_id}")


def sample_ladder_tasks(spec: WagnerPHLadderSpec) -> list[dict[str, Any]]:
    return [sample_ladder_task(spec, index) for index in range(spec.tasks)]


def _training(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    history: str,
    future_index: int,
    stage: str = "lineage",
    generation: int = 0,
) -> tuple[tuple[int, ...], bool]:
    _, viewed = _runtime(task)
    pair = _pair(task)
    base = int(task["midpoint"])
    target = pair.state(history)
    nodes = cue_nodes(
        pair,
        spec.genes,
        spec.cue_fraction,
        np.asarray(task["ordering"], dtype=int),
    )
    state = base
    adults: list[int] = []
    for cycle in range(spec.cue_dwell):
        common = (
            spec.master_seed,
            "origin-ladder-training",
            stage,
            task["task_id"],
            history,
            future_index,
            generation,
            cycle,
        )
        value = develop_memory_cycle(
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
        state = int(value.state)
        adults.append(state)
    return tuple(adults), bool(adults and adults[-1] == target)


def _copy_quantized(
    carrier: LocalCarrierState,
    genome: LocalCarrierGenome,
    mask: tuple[int, ...],
    bits: int,
    spec: WagnerPHLadderSpec,
    random: np.random.Generator,
) -> LocalCarrierState:
    """Copy with per-locus common draws, then enforce the registered bit budget."""

    values = np.asarray(carrier.values, dtype=float).copy()
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
    return quantize_carrier(bounded, mask, bits)


def _assay(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    carrier: LocalCarrierState,
    coupling: float,
    history: str,
    future_index: int,
    generation: int,
    stage: str,
) -> dict[str, float]:
    _, viewed = _runtime(task)
    pair = _pair(task)
    base = int(task["midpoint"])
    state = int(task["forced_breaks"][history])
    post = []
    for cycle in range(spec.horizon):
        common = (
            spec.master_seed,
            "origin-ladder-assay",
            stage,
            task["task_id"],
            history,
            future_index,
            generation,
            cycle,
        )
        value = develop_local_cycle(
            viewed,
            state,
            base,
            carrier,
            coupling,
            spec.expression_flip_probability,
            100,
            rng_for(*common, "carry"),
            rng_for(*common, "read"),
        )
        post.append(value)
        state = int(value.state)
    summary = summarize_memory_future(
        (),
        tuple(post),
        pair,
        history,
        np.asarray(carrier.values),
        spec.strict_run,
        spec.stable_run,
    )
    return {
        "correct": float(summary.correct_hold8),
        "wrong": float(summary.wrong_hold8),
        "returned": float(summary.returned),
    }


def _initial_carrier(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    genome: LocalCarrierGenome,
    bits: int,
    intervention: str,
    adults: tuple[int, ...],
    opposite_adults: tuple[int, ...],
    mask: tuple[int, ...],
) -> LocalCarrierState:
    if intervention in {"zero", "founder_write_off"}:
        return blank_local(spec.genes)
    writing = opposite_adults if intervention == "opposite_history_transplant" else adults
    return quantize_carrier(
        write_local(blank_local(spec.genes), writing, genome, mask), mask, bits
    )


def _propagate(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    genome: LocalCarrierGenome,
    bits: int,
    intervention: str,
    incoming: LocalCarrierState,
    mask: tuple[int, ...],
    history: str,
    future_index: int,
    generation: int,
    stage: str,
) -> LocalCarrierState:
    if intervention == "zero":
        return blank_local(spec.genes)
    _, viewed = _runtime(task)
    base = int(task["midpoint"])
    coupling = 0.0 if intervention == "reader_off" else genome.coupling
    state = base
    adults: list[int] = []
    for cycle in range(spec.generation_cycles):
        common = (
            spec.master_seed,
            "origin-ladder-propagation",
            stage,
            task["task_id"],
            history,
            future_index,
            generation,
            cycle,
        )
        value = develop_local_cycle(
            viewed,
            state,
            base,
            incoming,
            coupling,
            spec.expression_flip_probability,
            100,
            rng_for(*common, "carry"),
            rng_for(*common, "read"),
        )
        state = int(value.state)
        adults.append(state)
    carrier = incoming
    if intervention != "renewal_off":
        carrier = write_local(carrier, tuple(adults), genome, mask)
    return _copy_quantized(
        carrier,
        genome,
        mask,
        bits,
        spec,
        rng_for(
            spec.master_seed,
            "origin-ladder-copy",
            stage,
            task["task_id"],
            history,
            future_index,
            generation,
        ),
    )


def _finalize_rates(counts: dict[int, dict[str, float]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for generation, values in sorted(counts.items()):
        denominator = max(values["n"], 1.0)
        result[str(generation)] = {
            "correct_rate": values["correct"] / denominator,
            "wrong_rate": values["wrong"] / denominator,
            "return_rate": values["returned"] / denominator,
            "carrier_norm": values["carrier_norm"] / denominator,
            "nonzero_marks": values["nonzero_marks"] / denominator,
            "observations": int(values["n"]),
        }
    return result


def _simulate_lineage_cell(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    genome: LocalCarrierGenome,
    bits: int,
    intervention: str,
    trainings: dict[tuple[str, int], tuple[int, ...]],
    stage: str,
) -> dict[str, Any]:
    rulebook, _ = _runtime(task)
    mask = structural_mask(rulebook, genome)
    maximum = max(spec.checkpoints)
    checkpoints = set(spec.checkpoints)
    counts: dict[int, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for history in ("A", "B"):
        opposite = "B" if history == "A" else "A"
        for future_index in range(spec.futures_per_history):
            incoming = _initial_carrier(
                task,
                spec,
                genome,
                bits,
                intervention,
                trainings[(history, future_index)],
                trainings[(opposite, future_index)],
                mask,
            )
            for generation in range(maximum + 1):
                if generation in checkpoints:
                    coupling = (
                        0.0
                        if intervention in {"zero", "reader_off"}
                        else genome.coupling
                    )
                    outcome = _assay(
                        task,
                        spec,
                        incoming,
                        coupling,
                        history,
                        future_index,
                        generation,
                        stage,
                    )
                    cell = counts[generation]
                    cell["n"] += 1.0
                    for key in ("correct", "wrong", "returned"):
                        cell[key] += outcome[key]
                    cell["carrier_norm"] += float(
                        np.mean(np.abs(incoming.values))
                    )
                    cell["nonzero_marks"] += float(
                        np.sum(np.asarray(incoming.values) != 0.0)
                    )
                if generation < maximum:
                    incoming = _propagate(
                        task,
                        spec,
                        genome,
                        bits,
                        intervention,
                        incoming,
                        mask,
                        history,
                        future_index,
                        generation,
                        stage,
                    )
    return _finalize_rates(counts)


def _capacity_stage(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    trainings: dict[tuple[str, int], tuple[int, ...]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for k in spec.capacities:
        genome = _candidate(
            k,
            spec.strong_write_rate,
            spec.strong_coupling,
            spec,
            f"capacity-k{k}",
        )
        for bits in spec.bits_per_mark:
            conditions = {
                intervention: _simulate_lineage_cell(
                    task,
                    spec,
                    genome,
                    bits,
                    intervention,
                    trainings,
                    "capacity",
                )
                for intervention in CAPACITY_INTERVENTIONS
            }
            results.append(
                {
                    "cell_id": f"k{k}.b{bits}",
                    "k": k,
                    "bits_per_mark": bits,
                    "alphabet_size": (1 << bits) - 1,
                    "payload_upper_bits": k * bits,
                    "genome": genome.to_dict(),
                    "conditions": conditions,
                }
            )
    return results


def _coordination_stage(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    trainings: dict[tuple[str, int], tuple[int, ...]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for k in spec.coordination_capacities:
        for writer_index, writer in enumerate(spec.writer_rates):
            for reader_index, reader in enumerate(spec.reader_couplings):
                cell_id = f"k{k}.w{writer_index}.r{reader_index}"
                genome = _candidate(k, writer, reader, spec, cell_id)
                conditions = {
                    intervention: _simulate_lineage_cell(
                        task,
                        spec,
                        genome,
                        spec.coordination_bits,
                        intervention,
                        trainings,
                        "coordination",
                    )
                    for intervention in ("intact", "renewal_off")
                }
                results.append(
                    {
                        "cell_id": cell_id,
                        "k": k,
                        "writer_index": writer_index,
                        "reader_index": reader_index,
                        "write_rate": writer,
                        "coupling": reader,
                        "bits_per_mark": spec.coordination_bits,
                        "conditions": conditions,
                    }
                )
    return results


def _ecology_sequence(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    initial_history: str,
    future_index: int,
    persistence: float,
) -> tuple[str, ...]:
    values = [initial_history]
    random = rng_for(
        spec.master_seed,
        "origin-ladder-ecology-sequence",
        task["task_id"],
        initial_history,
        future_index,
        persistence,
    )
    for _ in range(spec.ecology_generations):
        previous = values[-1]
        values.append(
            previous
            if random.random() < persistence
            else ("B" if previous == "A" else "A")
        )
    return tuple(values)


def _ecology_cell(
    task: dict[str, Any],
    spec: WagnerPHLadderSpec,
    genome: LocalCarrierGenome,
    persistence: float,
    intervention: str,
) -> dict[str, Any]:
    rulebook, _ = _runtime(task)
    mask = structural_mask(rulebook, genome)
    counts: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for initial_history in ("A", "B"):
        for future_index in range(spec.futures_per_history):
            sequence = _ecology_sequence(
                task, spec, initial_history, future_index, persistence
            )
            parent_adults, _ = _training(
                task,
                spec,
                sequence[0],
                future_index,
                stage="ecology-parent",
            )
            if intervention == "zero":
                incoming = blank_local(spec.genes)
            else:
                written = write_local(
                    blank_local(spec.genes), parent_adults, genome, mask
                )
                incoming = _copy_quantized(
                    written,
                    genome,
                    mask,
                    spec.ecology_bits,
                    spec,
                    rng_for(
                        spec.master_seed,
                        "origin-ladder-ecology-copy",
                        task["task_id"],
                        initial_history,
                        future_index,
                        0,
                    ),
                )
            for generation in range(1, spec.ecology_generations + 1):
                history = sequence[generation]
                coupling = (
                    0.0 if intervention in {"zero", "reader_off"} else genome.coupling
                )
                outcome = _assay(
                    task,
                    spec,
                    incoming,
                    coupling,
                    history,
                    future_index,
                    generation,
                    "ecology",
                )
                relation = "stay" if history == sequence[generation - 1] else "switch"
                for label in ("overall", relation):
                    cell = counts[label]
                    cell["n"] += 1.0
                    for key in ("correct", "wrong", "returned"):
                        cell[key] += outcome[key]
                adult_states, _ = _training(
                    task,
                    spec,
                    history,
                    future_index,
                    stage="ecology-adult",
                    generation=generation,
                )
                if intervention == "zero":
                    incoming = blank_local(spec.genes)
                    continue
                carrier = incoming
                if intervention != "renewal_off":
                    carrier = write_local(carrier, adult_states, genome, mask)
                incoming = _copy_quantized(
                    carrier,
                    genome,
                    mask,
                    spec.ecology_bits,
                    spec,
                    rng_for(
                        spec.master_seed,
                        "origin-ladder-ecology-copy",
                        task["task_id"],
                        initial_history,
                        future_index,
                        generation,
                    ),
                )
    result: dict[str, Any] = {}
    for label in ("overall", "stay", "switch"):
        values = counts[label]
        denominator = values["n"]
        result[label] = {
            "correct_rate": values["correct"] / denominator if denominator else None,
            "wrong_rate": values["wrong"] / denominator if denominator else None,
            "return_rate": values["returned"] / denominator if denominator else None,
            "observations": int(denominator),
        }
    return result


def _ecology_stage(
    task: dict[str, Any], spec: WagnerPHLadderSpec
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for k in spec.ecology_capacities:
        genome = _candidate(
            k,
            spec.strong_write_rate,
            spec.strong_coupling,
            spec,
            f"ecology-k{k}",
        )
        for persistence in spec.ecology_persistence:
            conditions = {
                intervention: _ecology_cell(
                    task, spec, genome, persistence, intervention
                )
                for intervention in ECOLOGY_INTERVENTIONS
            }
            results.append(
                {
                    "cell_id": f"k{k}.rho{persistence:.2f}",
                    "k": k,
                    "persistence": persistence,
                    "bits_per_mark": spec.ecology_bits,
                    "selection_reward": "offspring correct development before its own inducing cue",
                    "conditions": conditions,
                }
            )
    return results


def simulate_ladder_task(
    task: dict[str, Any], spec_value: dict[str, Any]
) -> dict[str, Any]:
    """Run every frozen diagnostic cell for one independently replayable task."""

    spec = WagnerPHLadderSpec.from_dict(spec_value)
    if task.get("format") != LADDER_TASK_FORMAT:
        raise ValueError("Origin Ladder task format mismatch")
    expected = dict(task)
    task_digest = expected.pop("task_digest", None)
    if task_digest != canonical_digest(expected):
        raise ValueError("Origin Ladder task digest mismatch")
    trainings: dict[tuple[str, int], tuple[int, ...]] = {}
    acquired: list[bool] = []
    for history in ("A", "B"):
        for future_index in range(spec.futures_per_history):
            adults, success = _training(task, spec, history, future_index)
            trainings[(history, future_index)] = adults
            acquired.append(success)
    result = {
        "format": LADDER_RESULT_FORMAT,
        "task_id": task["task_id"],
        "task_digest": task["task_digest"],
        "acquisition_rate": float(np.mean(acquired)),
        "capacity": _capacity_stage(task, spec, trainings),
        "coordination": _coordination_stage(task, spec, trainings),
        "ecology": _ecology_stage(task, spec),
        "quantization_occurs_after_founder_write_and_every_boundary_copy": True,
        "ordinary_expression_is_reset_each_generation": True,
        "ecological_reward_contains_no_memory_label": True,
    }
    result["result_digest"] = canonical_digest(result)
    return result
