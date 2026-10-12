"""Registry construction and deterministic plastic-memory future simulation."""

from __future__ import annotations

import concurrent.futures
import math
import multiprocessing
from collections.abc import Callable, Iterator
from typing import Any

import numpy as np

from .boolean import BooleanRulebook
from .engines import Rulebook, rulebook_from_dict
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_config import (
    MemoryCondition,
    MemoryModelSpec,
    PlasticMemorySpec,
)
from .plastic_memory_dynamics import (
    AttractorPair,
    ablate_mark,
    balanced_midpoints,
    cue_nodes,
    damage_state,
    descriptor_matched_state,
    develop_memory_cycle,
    forced_break_state,
    permute_mark,
    permute_state,
    select_attractor_pair,
    summarize_memory_future,
)
from .rng import digest_parts, rng_for
from .wagner import WagnerRulebook


def _random_rulebook(engine: str, genes: int, rng: np.random.Generator) -> Rulebook:
    if engine == "boolean":
        return BooleanRulebook.random(genes, rng)
    if engine == "wagner":
        return WagnerRulebook.random(genes, rng)
    raise ValueError(engine)


def _derangement(size: int, rng: np.random.Generator) -> np.ndarray:
    if size < 2:
        raise ValueError("derangement requires at least two nodes")
    for _ in range(10_000):
        value = rng.permutation(size)
        if np.all(value != np.arange(size)):
            return value.astype(np.int64)
    raise RuntimeError("could not generate a node derangement")


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


def _model_metadata(
    rulebook: Rulebook,
    model: MemoryModelSpec,
    spec: PlasticMemorySpec,
    source_id: str,
) -> dict[str, Any] | None:
    viewed = MechanismRulebook(rulebook, model.variant)
    landscape = viewed.landscape()
    pair = select_attractor_pair(
        landscape,
        rulebook.genes,
        spec.minimum_basin_fraction,
        spec.minimum_form_distance,
    )
    if pair is None:
        return None
    ordering = rng_for(
        spec.master_seed, "memory-node-order", source_id, model.name
    ).permutation(rulebook.genes)
    midpoints = balanced_midpoints(
        pair, rulebook.genes, ordering, spec.midpoint_count
    )
    return {
        "pair": _pair_dict(pair),
        "midpoints": list(midpoints),
        "node_order": ordering.tolist(),
        "mark_permutation": _derangement(
            rulebook.genes,
            rng_for(spec.master_seed, "memory-mark-permutation", source_id, model.name),
        ).tolist(),
        "ablation_order": rng_for(
            spec.master_seed, "memory-ablation-order", source_id, model.name
        ).permutation(rulebook.genes).tolist(),
        "forced_breaks": {
            history: forced_break_state(
                landscape,
                pair.index(history),
                pair.state(history),
                rulebook.genes,
            )
            for history in ("A", "B")
        },
        "landscape": landscape.to_dict(),
    }


def build_memory_registry(
    spec: PlasticMemorySpec,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Generate fresh eligible rulebooks and freeze all outcome-blind metadata."""

    spec.validate()
    sources: list[dict[str, Any]] = []
    generation: dict[str, dict[str, int]] = {}
    for source_spec in spec.sources:
        models = [model for model in spec.models if model.source_set == source_spec.name]
        accepted = 0
        proposals = 0
        if progress is not None:
            progress(f"sampling memory source set {source_spec.name}")
        while accepted < source_spec.count and proposals < spec.maximum_source_proposals:
            rng = rng_for(
                spec.master_seed, "memory-source", source_spec.name, proposals
            )
            rulebook = _random_rulebook(source_spec.engine, source_spec.genes, rng)
            source_id = f"{source_spec.name}.{accepted:04d}"
            proposals += 1
            metadata: dict[str, Any] = {}
            eligible = True
            for model in models:
                value = _model_metadata(rulebook, model, spec, source_id)
                if value is None:
                    eligible = False
                    break
                metadata[model.name] = value
            if not eligible:
                continue
            sources.append(
                {
                    "source_set": source_spec.name,
                    "source_id": source_id,
                    "engine": source_spec.engine,
                    "genes": source_spec.genes,
                    "proposal_index": proposals - 1,
                    "source": rulebook.to_dict(),
                    "models": metadata,
                }
            )
            accepted += 1
        if accepted != source_spec.count:
            raise RuntimeError(
                f"generated only {accepted}/{source_spec.count} eligible memory "
                f"sources for {source_spec.name} after {proposals} proposals"
            )
        generation[source_spec.name] = {"accepted": accepted, "proposals": proposals}
    return {
        "format": "gre-plastic-memory-rulebooks-v1",
        "cohort_id": spec.cohort_id,
        "sources": sources,
        "generation": generation,
    }


def _streams(
    spec: PlasticMemorySpec,
    bundle: dict[str, Any],
    model: MemoryModelSpec,
    history: str,
    midpoint_index: int,
    future_index: int,
    stage: str,
    cycle: int,
) -> tuple[np.random.Generator, np.random.Generator, np.random.Generator]:
    shared = (
        "plastic-memory-future",
        bundle["source_id"],
        model.source_set,
        history,
        midpoint_index,
        future_index,
        stage,
        cycle,
    )
    return (
        rng_for(spec.master_seed, *shared, "carryover"),
        rng_for(spec.master_seed, *shared, "mark"),
        rng_for(spec.master_seed, *shared, "dynamics"),
    )


def _train(
    spec: PlasticMemorySpec,
    bundle: dict[str, Any],
    model: MemoryModelSpec,
    condition: MemoryCondition,
    pair: AttractorPair,
    midpoint_index: int,
    history: str,
    future_index: int,
    mark_name: str,
    write_mark: bool,
) -> tuple[int, np.ndarray, tuple[int, ...]]:
    rulebook = MechanismRulebook(rulebook_from_dict(bundle["source"]), model.variant)
    metadata = bundle["models"][model.name]
    base = int(metadata["midpoints"][midpoint_index])
    target = pair.state(history)
    nodes = cue_nodes(
        pair,
        rulebook.genes,
        condition.cue.fraction,
        np.asarray(metadata["node_order"], dtype=np.int64),
    )
    mark_spec = spec.mark(mark_name)
    state = base
    mark = np.zeros(rulebook.genes, dtype=float)
    states: list[int] = []
    for cycle in range(condition.cue.dwell):
        carry_rng, mark_rng, dynamics_rng = _streams(
            spec,
            bundle,
            model,
            history,
            midpoint_index,
            future_index,
            "training",
            cycle,
        )
        value = develop_memory_cycle(
            rulebook,
            state,
            base,
            mark,
            spec.expression_carryover,
            spec.expression_flip_probability,
            mark_spec.rho,
            mark_spec.coupling,
            model.gamma_variance,
            spec.wagner_max_sweeps,
            carry_rng,
            mark_rng,
            dynamics_rng,
            cue_target=target,
            clamped_nodes=nodes,
            write_mark=write_mark and mark_spec.active,
        )
        state = value.state
        mark = np.asarray(value.mark, dtype=float)
        states.append(state)
    return state, mark, tuple(states)


def _donor_index(future_index: int, futures_per_cell: int) -> int:
    half_size = futures_per_cell // 2
    half_start = 0 if future_index < half_size else half_size
    return half_start + ((future_index - half_start + 1) % half_size)


def _carrier_values(
    spec: PlasticMemorySpec,
    bundle: dict[str, Any],
    model: MemoryModelSpec,
    condition: MemoryCondition,
    pair: AttractorPair,
    landscape: Any,
    midpoint_index: int,
    history: str,
    future_index: int,
    mark_name: str,
    carrier: str,
    trained_state: int,
    trained_mark: np.ndarray,
    donor_state: int | None,
    donor_exact: bool,
) -> tuple[int, np.ndarray, bool, float, bool]:
    """Return recipient state, mark, match flag, coupling, and write flag."""

    metadata = bundle["models"][model.name]
    base = int(metadata["midpoints"][midpoint_index])
    genes = int(bundle["genes"])
    mark_spec = spec.mark(mark_name)
    zero = np.zeros(genes, dtype=float)
    exact_match = True
    coupling = mark_spec.coupling
    write_mark = mark_spec.active
    if carrier == "self_continuation":
        return trained_state, trained_mark.copy(), True, coupling, write_mark
    if carrier == "state_transplant":
        return trained_state, zero, True, 0.0, False
    if carrier == "mark_transplant":
        return base, trained_mark.copy(), True, coupling, write_mark
    if carrier == "state_and_mark_transplant":
        return trained_state, trained_mark.copy(), True, coupling, write_mark
    if carrier == "reset_both":
        return base, zero, True, coupling, write_mark
    if carrier == "destination_matched_donor":
        if donor_state is None:
            raise RuntimeError("destination-matched donor state was not prepared")
        return donor_state, zero, donor_exact, 0.0, False
    if carrier == "descriptor_matched_null":
        ordinal = future_index + 17
        state, exact_match = descriptor_matched_state(
            landscape, trained_state, pair, genes, ordinal
        )
        return state, zero, exact_match, 0.0, False
    if carrier == "state_pattern_shuffle":
        state = permute_state(
            trained_state,
            genes,
            np.asarray(metadata["mark_permutation"], dtype=np.int64),
        )
        return state, zero, state != trained_state, 0.0, False
    if carrier == "mark_pattern_shuffle":
        shuffled = permute_mark(
            trained_mark, np.asarray(metadata["mark_permutation"], dtype=np.int64)
        )
        return base, shuffled, True, coupling, write_mark
    if carrier == "write_disabled":
        return base, zero, True, coupling, False
    if carrier == "mark_inert":
        return base, trained_mark.copy(), True, 0.0, write_mark
    amount = max(1, int(round(0.20 * genes)))
    if carrier == "mark_ablation":
        indices = tuple(
            sorted(range(genes), key=lambda gene: (-abs(trained_mark[gene]), gene))[:amount]
        )
        return base, ablate_mark(trained_mark, indices), True, coupling, write_mark
    if carrier == "mark_random_ablation":
        indices = tuple(int(value) for value in metadata["ablation_order"][:amount])
        return base, ablate_mark(trained_mark, indices), True, coupling, write_mark
    if carrier == "mark_rescue":
        return base, trained_mark.copy(), True, coupling, write_mark
    raise ValueError(f"unknown carrier arm: {carrier}")


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
        "start_mark_norm": value.start_mark_norm,
        "end_mark_norm": value.end_mark_norm,
        "trace_digest": value.trace_digest,
    }


def simulate_memory_source(
    bundle: dict[str, Any], spec_value: dict[str, Any]
) -> list[dict[str, Any]]:
    spec = PlasticMemorySpec.from_dict(spec_value)
    source = rulebook_from_dict(bundle["source"])
    records: list[dict[str, Any]] = []
    training_cache: dict[
        tuple[str, int, str, int, str, bool], tuple[int, np.ndarray, tuple[int, ...]]
    ] = {}
    donor_cache: dict[tuple[str, int, str, int], tuple[int, bool]] = {}
    for condition in spec.conditions:
        model = spec.model(condition.model)
        if model.source_set != bundle["source_set"]:
            continue
        rulebook = MechanismRulebook(source, model.variant)
        landscape = rulebook.landscape()
        metadata = bundle["models"][model.name]
        pair = _pair_from_dict(metadata["pair"])
        for midpoint_index in range(spec.midpoint_count):
            base = int(metadata["midpoints"][midpoint_index])
            for history in ("A", "B"):
                target = pair.state(history)
                for mark_name in condition.mark_settings:
                    for carrier in condition.carrier_arms:
                        for washout_age in condition.washout_ages:
                            for challenge in condition.challenges:
                                for future_index in range(condition.futures_per_cell):
                                    training_write = carrier != "write_disabled"
                                    training_key = (
                                        condition.name,
                                        midpoint_index,
                                        history,
                                        future_index,
                                        mark_name,
                                        training_write,
                                    )
                                    if training_key not in training_cache:
                                        training_cache[training_key] = _train(
                                            spec,
                                            bundle,
                                            model,
                                            condition,
                                            pair,
                                            midpoint_index,
                                            history,
                                            future_index,
                                            mark_name,
                                            training_write,
                                        )
                                    trained_state, trained_mark, training_states = training_cache[
                                        training_key
                                    ]
                                    donor_state: int | None = None
                                    donor_exact = True
                                    if carrier == "destination_matched_donor":
                                        cache_key = (
                                            condition.name,
                                            midpoint_index,
                                            history,
                                            future_index,
                                        )
                                        if cache_key not in donor_cache:
                                            half_size = condition.futures_per_cell // 2
                                            half_start = 0 if future_index < half_size else half_size
                                            candidates = [
                                                half_start
                                                + ((future_index - half_start + offset) % half_size)
                                                for offset in range(1, half_size)
                                            ]
                                            fallback = _donor_index(
                                                future_index, condition.futures_per_cell
                                            )
                                            chosen = fallback
                                            matched = False
                                            for donor_future in candidates:
                                                donor_key = (
                                                    condition.name,
                                                    midpoint_index,
                                                    history,
                                                    donor_future,
                                                    "none",
                                                    False,
                                                )
                                                if donor_key not in training_cache:
                                                    training_cache[donor_key] = _train(
                                                        spec,
                                                        bundle,
                                                        model,
                                                        condition,
                                                        pair,
                                                        midpoint_index,
                                                        history,
                                                        donor_future,
                                                        "none",
                                                        False,
                                                    )
                                                candidate_state = training_cache[donor_key][0]
                                                if int(landscape.attractor_index[candidate_state]) == pair.index(history):
                                                    chosen = donor_future
                                                    matched = True
                                                    break
                                            chosen_key = (
                                                condition.name,
                                                midpoint_index,
                                                history,
                                                chosen,
                                                "none",
                                                False,
                                            )
                                            if chosen_key not in training_cache:
                                                training_cache[chosen_key] = _train(
                                                    spec,
                                                    bundle,
                                                    model,
                                                    condition,
                                                    pair,
                                                    midpoint_index,
                                                    history,
                                                    chosen,
                                                    "none",
                                                    False,
                                                )
                                            donor_cache[cache_key] = (
                                                training_cache[chosen_key][0],
                                                matched,
                                            )
                                        donor_state, donor_exact = donor_cache[cache_key]
                                    (
                                        state,
                                        mark,
                                        descriptor_exact,
                                        post_coupling,
                                        post_write,
                                    ) = _carrier_values(
                                        spec,
                                        bundle,
                                        model,
                                        condition,
                                        pair,
                                        landscape,
                                        midpoint_index,
                                        history,
                                        future_index,
                                        mark_name,
                                        carrier,
                                        trained_state,
                                        trained_mark,
                                        donor_state,
                                        donor_exact,
                                    )
                                    start_mark = mark.copy()
                                    mark_spec = spec.mark(mark_name)
                                    for cycle in range(washout_age):
                                        carry_rng, mark_rng, dynamics_rng = _streams(
                                            spec,
                                            bundle,
                                            model,
                                            history,
                                            midpoint_index,
                                            future_index,
                                            "washout",
                                            cycle,
                                        )
                                        value = develop_memory_cycle(
                                            rulebook,
                                            state,
                                            base,
                                            mark,
                                            spec.expression_carryover,
                                            spec.expression_flip_probability,
                                            mark_spec.rho,
                                            post_coupling,
                                            model.gamma_variance,
                                            spec.wagner_max_sweeps,
                                            carry_rng,
                                            mark_rng,
                                            dynamics_rng,
                                            write_mark=post_write,
                                        )
                                        state = value.state
                                        mark = np.asarray(value.mark, dtype=float)
                                    damage_nodes: tuple[int, ...] = ()
                                    if challenge == "neutral_damage":
                                        damage_rng = rng_for(
                                            spec.master_seed,
                                            "plastic-memory-damage",
                                            bundle["source_id"],
                                            model.source_set,
                                            history,
                                            midpoint_index,
                                            future_index,
                                            washout_age,
                                        )
                                        state, damage_nodes = damage_state(
                                            state,
                                            rulebook.genes,
                                            spec.neutral_damage_fraction,
                                            damage_rng,
                                        )
                                    elif challenge == "forced_break":
                                        state = int(metadata["forced_breaks"][history])
                                    elif challenge != "release_only":
                                        raise ValueError(challenge)
                                    post: list[Any] = []
                                    for cycle in range(spec.horizon):
                                        carry_rng, mark_rng, dynamics_rng = _streams(
                                            spec,
                                            bundle,
                                            model,
                                            history,
                                            midpoint_index,
                                            future_index,
                                            f"post-{washout_age}-{challenge}",
                                            cycle,
                                        )
                                        value = develop_memory_cycle(
                                            rulebook,
                                            state,
                                            base,
                                            mark,
                                            spec.expression_carryover,
                                            spec.expression_flip_probability,
                                            mark_spec.rho,
                                            post_coupling,
                                            model.gamma_variance,
                                            spec.wagner_max_sweeps,
                                            carry_rng,
                                            mark_rng,
                                            dynamics_rng,
                                            write_mark=post_write,
                                        )
                                        post.append(value)
                                        state = value.state
                                        mark = np.asarray(value.mark, dtype=float)
                                    summary = summarize_memory_future(
                                        training_states,
                                        tuple(post),
                                        pair,
                                        history,
                                        start_mark,
                                        spec.strict_run,
                                        spec.stable_run,
                                    )
                                    future_id = digest_parts(
                                        spec.protocol_format,
                                        spec.cohort_id,
                                        condition.name,
                                        bundle["source_id"],
                                        model.name,
                                        midpoint_index,
                                        history,
                                        mark_name,
                                        carrier,
                                        washout_age,
                                        challenge,
                                        future_index,
                                    )
                                    records.append(
                                        {
                                            "future_id": future_id,
                                            "cohort_id": spec.cohort_id,
                                            "phase": spec.phase,
                                            "condition": condition.name,
                                            "source_set": bundle["source_set"],
                                            "source_id": bundle["source_id"],
                                            "engine": bundle["engine"],
                                            "genes": int(bundle["genes"]),
                                            "model": model.name,
                                            "variant": model.variant,
                                            "gamma_variance": model.gamma_variance,
                                            "cue_fraction": condition.cue.fraction,
                                            "cue_dwell": condition.cue.dwell,
                                            "midpoint_index": midpoint_index,
                                            "base_state": base,
                                            "history": history,
                                            "target_state": target,
                                            "mark_setting": mark_name,
                                            "mark_half_life": mark_spec.half_life,
                                            "mark_coupling": mark_spec.coupling,
                                            "carrier": carrier,
                                            "washout_age": washout_age,
                                            "challenge": challenge,
                                            "future_index": future_index,
                                            "half": (
                                                "A"
                                                if future_index < condition.futures_per_cell // 2
                                                else "B"
                                            ),
                                            "descriptor_exact": descriptor_exact,
                                            "damage_nodes": list(damage_nodes),
                                            **_summary_dict(summary),
                                        }
                                    )
    records.sort(
        key=lambda item: (
            item["condition"],
            item["midpoint_index"],
            item["history"],
            item["mark_setting"],
            item["carrier"],
            item["washout_age"],
            item["challenge"],
            item["future_index"],
        )
    )
    return records


def expected_memory_futures(spec: PlasticMemorySpec, registry: dict[str, Any]) -> int:
    source_counts: dict[str, int] = {}
    for source in registry["sources"]:
        source_counts[source["source_set"]] = source_counts.get(source["source_set"], 0) + 1
    total = 0
    for condition in spec.conditions:
        model = spec.model(condition.model)
        total += (
            source_counts[model.source_set]
            * spec.midpoint_count
            * 2
            * len(condition.mark_settings)
            * len(condition.carrier_arms)
            * len(condition.washout_ages)
            * len(condition.challenges)
            * condition.futures_per_cell
        )
    return total


def expected_memory_source_futures(spec: PlasticMemorySpec, source_set: str) -> int:
    """Exact number of records one source bundle must contribute."""

    total = 0
    for condition in spec.conditions:
        if spec.model(condition.model).source_set != source_set:
            continue
        total += (
            spec.midpoint_count
            * 2
            * len(condition.mark_settings)
            * len(condition.carrier_arms)
            * len(condition.washout_ages)
            * len(condition.challenges)
            * condition.futures_per_cell
        )
    return total


def iter_memory_source_results(
    registry: dict[str, Any],
    spec: PlasticMemorySpec,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    if workers < 1:
        raise ValueError("workers must be positive")
    sources = sorted(registry["sources"], key=lambda value: value["source_id"])
    if workers == 1:
        for index, source in enumerate(sources, start=1):
            records = simulate_memory_source(source, spec.to_dict())
            if progress is not None:
                progress(f"simulated memory source {index}/{len(sources)}")
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
                simulate_memory_source, sources[next_submit], spec.to_dict()
            )
            next_submit += 1
        for index, source in enumerate(sources):
            records = pending.pop(index).result()
            if progress is not None:
                progress(f"simulated memory source {index + 1}/{len(sources)}")
            yield source, records
            if next_submit < len(sources):
                pending[next_submit] = executor.submit(
                    simulate_memory_source, sources[next_submit], spec.to_dict()
                )
                next_submit += 1
