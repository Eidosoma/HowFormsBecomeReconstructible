"""Registry construction and deterministic Wagner-rescue future simulation."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
from collections.abc import Callable, Iterator
from typing import Any

import numpy as np

from .engines import rulebook_from_dict
from .endpoints import apply_carryover
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import (
    AttractorPair,
    MemoryCycle,
    balanced_midpoints,
    select_attractor_pair,
    summarize_memory_future,
)
from .rng import digest_parts, rng_for
from .wagner import WagnerRulebook, gamma_multipliers
from .wagner_rescue_config import (
    RescueModelSpec,
    WagnerRescueCondition,
    WagnerRescueSpec,
)
from .wagner_rescue_dynamics import develop_with_intervention, intervention_nodes


def _pair_dict(pair: AttractorPair) -> dict[str, int]:
    return {
        "left_index": pair.left_index,
        "right_index": pair.right_index,
        "left_state": pair.left_state,
        "right_state": pair.right_state,
    }


def _pair_from_dict(value: dict[str, Any]) -> AttractorPair:
    return AttractorPair(
        int(value["left_index"]),
        int(value["right_index"]),
        int(value["left_state"]),
        int(value["right_state"]),
    )


def build_rescue_registry(
    spec: WagnerRescueSpec,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Sample a cohort eligible under every registered update variant."""

    spec.validate()
    sources: list[dict[str, Any]] = []
    proposals = 0
    if progress is not None:
        progress(
            "sampling Wagner rescue sources eligible under "
            + ", ".join(spec.eligibility_variants)
        )
    while len(sources) < spec.source_count and proposals < spec.maximum_source_proposals:
        source_rng = rng_for(spec.master_seed, "wagner-rescue-source", proposals)
        source = WagnerRulebook.random(spec.genes, source_rng)
        proposal_index = proposals
        proposals += 1
        accepted_index = len(sources)
        source_id = f"wagner_n{spec.genes}.{accepted_index:04d}"
        metadata: dict[str, Any] = {}
        eligible = True
        for variant in spec.eligibility_variants:
            viewed = MechanismRulebook(source, variant)
            landscape = viewed.landscape()
            pair = select_attractor_pair(
                landscape,
                spec.genes,
                spec.minimum_basin_fraction,
                spec.minimum_form_distance,
            )
            if pair is None:
                eligible = False
                break
            ordering = rng_for(
                spec.master_seed,
                "wagner-rescue-node-order",
                source_id,
                variant,
            ).permutation(spec.genes)
            metadata[variant] = {
                "pair": _pair_dict(pair),
                "midpoints": list(
                    balanced_midpoints(pair, spec.genes, ordering, spec.midpoint_count)
                ),
                "node_order": ordering.tolist(),
            }
        if not eligible:
            continue
        sources.append(
            {
                "source_id": source_id,
                "engine": "wagner",
                "genes": spec.genes,
                "proposal_index": proposal_index,
                "source": source.to_dict(),
                "variants": metadata,
            }
        )
    if len(sources) != spec.source_count:
        raise RuntimeError(
            f"generated only {len(sources)}/{spec.source_count} eligible Wagner "
            f"sources after {proposals} proposals"
        )
    return {
        "format": "gre-wagner-rescue-rulebooks-v1",
        "cohort_id": spec.cohort_id,
        "sources": sources,
        "generation": {
            "accepted": len(sources),
            "proposals": proposals,
            "eligibility_variants": list(spec.eligibility_variants),
        },
    }


def _streams(
    spec: WagnerRescueSpec,
    source_id: str,
    history: str,
    midpoint_index: int,
    future_index: int,
    stage: str,
    cycle: int,
) -> tuple[np.random.Generator, np.random.Generator]:
    shared = (
        "wagner-rescue-future",
        source_id,
        history,
        midpoint_index,
        future_index,
        stage,
        cycle,
    )
    return (
        rng_for(spec.master_seed, *shared, "carryover"),
        rng_for(spec.master_seed, *shared, "dynamics"),
    )


def _ordinary_cycle(
    rulebook: MechanismRulebook,
    state: int,
    base: int,
    spec: WagnerRescueSpec,
    gamma_variance: float,
    carry_rng: np.random.Generator,
    dynamics_rng: np.random.Generator,
) -> MemoryCycle:
    initial = apply_carryover(
        state,
        base,
        rulebook.genes,
        spec.expression_carryover,
        spec.expression_flip_probability,
        carry_rng,
    )
    multipliers = gamma_multipliers(rulebook.genes, gamma_variance, dynamics_rng)
    result = rulebook.develop(initial, multipliers, spec.wagner_max_sweeps)
    return MemoryCycle(
        state=int(result.final_state),
        mark=tuple(0.0 for _ in range(rulebook.genes)),
        status=str(result.status),
        steps=int(result.steps),
    )


def _train(
    spec: WagnerRescueSpec,
    bundle: dict[str, Any],
    condition: WagnerRescueCondition,
    model: RescueModelSpec,
    rulebook: MechanismRulebook,
    pair: AttractorPair,
    base: int,
    nodes: tuple[int, ...],
    midpoint_index: int,
    history: str,
    future_index: int,
) -> tuple[tuple[int, ...], tuple[str, ...], tuple[int, ...]]:
    target = pair.state(history)
    state = base
    states: list[int] = []
    statuses: list[str] = []
    steps: list[int] = []
    for cycle in range(condition.intervention.dwell):
        carry_rng, dynamics_rng = _streams(
            spec,
            str(bundle["source_id"]),
            history,
            midpoint_index,
            future_index,
            "training",
            cycle,
        )
        initial = apply_carryover(
            state,
            base,
            rulebook.genes,
            spec.expression_carryover,
            spec.expression_flip_probability,
            carry_rng,
        )
        result = develop_with_intervention(
            rulebook,
            initial,
            condition.intervention,
            target,
            nodes,
            model.gamma_variance,
            spec.wagner_max_sweeps,
            dynamics_rng,
        )
        state = int(result.final_state)
        states.append(state)
        statuses.append(str(result.status))
        steps.append(int(result.steps))
    return tuple(states), tuple(statuses), tuple(steps)


def _summary_dict(value: Any) -> dict[str, Any]:
    return {
        "acquired": value.acquired,
        "form_destination": value.form_destination,
        "correct_hold_run": value.correct_hold_run,
        "wrong_hold_run": value.wrong_hold_run,
        "generic_hold_run": value.generic_hold_run,
        "correct_hold8": value.correct_hold8,
        "wrong_hold8": value.wrong_hold8,
        "generic_hold8": value.generic_hold8,
        "returned": value.returned,
        "return_cycle": value.return_cycle,
        "first_break_cycle": value.first_break_cycle,
        "point_cycles": value.point_cycles,
        "cycle_cycles": value.cycle_cycles,
        "nonconvergent_cycles": value.nonconvergent_cycles,
        "unique_adult_states": value.unique_adult_states,
        "trace_digest": value.trace_digest,
    }


def simulate_rescue_source(
    bundle: dict[str, Any], spec_value: dict[str, Any]
) -> list[dict[str, Any]]:
    """Simulate every registered rescue future for one independent rulebook."""

    spec = WagnerRescueSpec.from_dict(spec_value)
    source = rulebook_from_dict(bundle["source"])
    if not isinstance(source, WagnerRulebook):
        raise TypeError("rescue registry contains a non-Wagner rulebook")
    records: list[dict[str, Any]] = []
    rulebooks = {
        model.name: MechanismRulebook(source, model.variant) for model in spec.models
    }
    landscapes = {
        variant: MechanismRulebook(source, variant).landscape()
        for variant in spec.eligibility_variants
    }
    for condition in spec.conditions:
        model = spec.model(condition.model)
        rulebook = rulebooks[model.name]
        landscape = landscapes[model.variant]
        metadata = bundle["variants"][model.variant]
        pair = _pair_from_dict(metadata["pair"])
        nodes = intervention_nodes(
            pair,
            rulebook.genes,
            condition.intervention,
            np.asarray(metadata["node_order"], dtype=np.int64),
        )
        for midpoint_index in range(spec.midpoint_count):
            base = int(metadata["midpoints"][midpoint_index])
            for history in ("A", "B"):
                target = pair.state(history)
                for future_index in range(condition.futures_per_cell):
                    training_states, training_statuses, training_steps = _train(
                        spec,
                        bundle,
                        condition,
                        model,
                        rulebook,
                        pair,
                        base,
                        nodes,
                        midpoint_index,
                        history,
                        future_index,
                    )
                    trained_state = training_states[-1]
                    post: list[MemoryCycle] = []
                    state = trained_state
                    for cycle in range(spec.horizon):
                        carry_rng, dynamics_rng = _streams(
                            spec,
                            str(bundle["source_id"]),
                            history,
                            midpoint_index,
                            future_index,
                            "post-release",
                            cycle,
                        )
                        value = _ordinary_cycle(
                            rulebook,
                            state,
                            base,
                            spec,
                            model.gamma_variance,
                            carry_rng,
                            dynamics_rng,
                        )
                        post.append(value)
                        state = value.state
                    summary = summarize_memory_future(
                        training_states,
                        tuple(post),
                        pair,
                        history,
                        np.zeros(rulebook.genes, dtype=float),
                        spec.strict_run,
                        spec.stable_run,
                    )
                    future_id = digest_parts(
                        spec.protocol_format,
                        spec.cohort_id,
                        condition.name,
                        bundle["source_id"],
                        midpoint_index,
                        history,
                        future_index,
                    )
                    records.append(
                        {
                            "future_id": future_id,
                            "cohort_id": spec.cohort_id,
                            "phase": spec.phase,
                            "condition": condition.name,
                            "role": condition.role,
                            "source_id": bundle["source_id"],
                            "engine": "wagner",
                            "genes": spec.genes,
                            "model": model.name,
                            "variant": model.variant,
                            "gamma_variance": model.gamma_variance,
                            "cue_mode": condition.intervention.mode,
                            "cue_fraction": condition.intervention.fraction,
                            "cue_dwell": condition.intervention.dwell,
                            "field_strength": condition.intervention.field_strength,
                            "midpoint_index": midpoint_index,
                            "history": history,
                            "future_index": future_index,
                            "half": (
                                "A"
                                if future_index < condition.futures_per_cell // 2
                                else "B"
                            ),
                            "base_state": base,
                            "target_state": target,
                            "trained_state": trained_state,
                            "basin_acquired": bool(
                                int(landscape.attractor_index[trained_state])
                                == pair.index(history)
                            ),
                            "training_status": training_statuses[-1],
                            "training_steps": training_steps[-1],
                            "training_point_cycles": sum(
                                status == "point" for status in training_statuses
                            ),
                            "training_cycle_cycles": sum(
                                status == "cycle" for status in training_statuses
                            ),
                            "training_nonconvergent_cycles": sum(
                                status == "nonconvergent"
                                for status in training_statuses
                            ),
                            **_summary_dict(summary),
                        }
                    )
    records.sort(
        key=lambda record: (
            record["condition"],
            record["midpoint_index"],
            record["history"],
            record["future_index"],
        )
    )
    return records


def expected_rescue_futures(spec: WagnerRescueSpec) -> int:
    return sum(
        spec.source_count
        * spec.midpoint_count
        * 2
        * condition.futures_per_cell
        for condition in spec.conditions
    )


def expected_rescue_source_futures(spec: WagnerRescueSpec) -> int:
    return sum(
        spec.midpoint_count * 2 * condition.futures_per_cell
        for condition in spec.conditions
    )


def iter_rescue_source_results(
    registry: dict[str, Any],
    spec: WagnerRescueSpec,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    if workers < 1:
        raise ValueError("rescue workers must be positive")
    sources = sorted(registry["sources"], key=lambda source: source["source_id"])
    expected = expected_rescue_futures(spec)
    per_source = expected_rescue_source_futures(spec)
    if workers == 1:
        for index, source in enumerate(sources, start=1):
            records = simulate_rescue_source(source, spec.to_dict())
            if progress is not None:
                progress(
                    f"simulated rescue source {index}/{len(sources)} "
                    f"({index * per_source:,}/{expected:,} futures)"
                )
            yield source, records
        return
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        pending: dict[int, concurrent.futures.Future[list[dict[str, Any]]]] = {}
        next_submit = 0
        window = max(workers, workers * 2)
        while next_submit < min(window, len(sources)):
            pending[next_submit] = executor.submit(
                simulate_rescue_source, sources[next_submit], spec.to_dict()
            )
            next_submit += 1
        for index, source in enumerate(sources):
            records = pending.pop(index).result()
            completed = index + 1
            if progress is not None:
                progress(
                    f"simulated rescue source {completed}/{len(sources)} "
                    f"({completed * per_source:,}/{expected:,} futures)"
                )
            yield source, records
            if next_submit < len(sources):
                pending[next_submit] = executor.submit(
                    simulate_rescue_source, sources[next_submit], spec.to_dict()
                )
                next_submit += 1
