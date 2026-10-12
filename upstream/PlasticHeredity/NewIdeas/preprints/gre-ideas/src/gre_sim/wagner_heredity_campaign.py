"""Fresh registries and deterministic futures for Wagner plastic heredity."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
from collections.abc import Callable, Iterator
from typing import Any

import numpy as np

from .endpoints import apply_carryover
from .engines import rulebook_from_dict
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_campaign import (
    _carrier_values,
    _pair_from_dict,
    _streams,
    _summary_dict,
    build_memory_registry,
)
from .plastic_memory_dynamics import (
    AttractorPair,
    apply_mark_bias,
    damage_state,
    develop_memory_cycle,
    summarize_memory_future,
    update_mark,
)
from .rng import digest_parts
from .wagner import WagnerRulebook
from .wagner_heredity_config import (
    HeredityCondition,
    HeredityWriterSpec,
    WagnerHereditySpec,
)
from .wagner_rescue_dynamics import develop_with_intervention, intervention_nodes


def build_heredity_registry(
    spec: WagnerHereditySpec,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Generate fresh sources with frozen, outcome-blind control metadata."""

    spec.validate()
    registry = build_memory_registry(spec.memory_spec(), progress)
    return {
        **registry,
        "format": "gre-wagner-heredity-rulebooks-v1",
        "parent_candidate_digest": spec.parent_candidate_digest,
    }


def _train(
    spec: WagnerHereditySpec,
    memory_spec: Any,
    bundle: dict[str, Any],
    rulebook: MechanismRulebook,
    writer: HeredityWriterSpec,
    condition: HeredityCondition,
    pair: AttractorPair,
    midpoint_index: int,
    history: str,
    future_index: int,
    mark_name: str,
    write_mark: bool,
) -> tuple[int, np.ndarray, tuple[int, ...], tuple[str, ...], tuple[int, ...]]:
    model = memory_spec.model(writer.name)
    metadata = bundle["models"][writer.name]
    base = int(metadata["midpoints"][midpoint_index])
    target = pair.state(history)
    nodes = intervention_nodes(
        pair,
        rulebook.genes,
        writer.intervention,
        np.asarray(metadata["node_order"], dtype=np.int64),
    )
    mark_spec = spec.mark(mark_name)
    state = base
    mark = np.zeros(rulebook.genes, dtype=float)
    states: list[int] = []
    statuses: list[str] = []
    steps: list[int] = []
    for cycle in range(writer.intervention.dwell):
        carry_rng, mark_rng, dynamics_rng = _streams(
            memory_spec,
            bundle,
            model,
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
        initial = apply_mark_bias(initial, mark, mark_spec.coupling, mark_rng)
        result = develop_with_intervention(
            rulebook,
            initial,
            writer.intervention,
            target,
            nodes,
            writer.gamma_variance,
            spec.wagner_max_sweeps,
            dynamics_rng,
        )
        state = int(result.final_state)
        if write_mark and mark_spec.active:
            mark = update_mark(mark, state, rulebook.genes, mark_spec.rho)
        states.append(state)
        statuses.append(str(result.status))
        steps.append(int(result.steps))
    return state, mark, tuple(states), tuple(statuses), tuple(steps)


def _donor_index(future_index: int, futures_per_cell: int) -> int:
    half_size = futures_per_cell // 2
    half_start = 0 if future_index < half_size else half_size
    return half_start + ((future_index - half_start + 1) % half_size)


def simulate_heredity_source(
    bundle: dict[str, Any], spec_value: dict[str, Any]
) -> list[dict[str, Any]]:
    """Simulate all registered donor/recipient futures for one rulebook."""

    spec = WagnerHereditySpec.from_dict(spec_value)
    memory_spec = spec.memory_spec()
    source = rulebook_from_dict(bundle["source"])
    if not isinstance(source, WagnerRulebook):
        raise TypeError("Wagner heredity registry contains a non-Wagner rulebook")
    rulebook = MechanismRulebook(source, "wagner_sequential")
    records: list[dict[str, Any]] = []
    training_cache: dict[
        tuple[str, int, str, int, str, bool],
        tuple[int, np.ndarray, tuple[int, ...], tuple[str, ...], tuple[int, ...]],
    ] = {}
    donor_cache: dict[tuple[str, int, str, int], tuple[int, bool]] = {}
    for condition in spec.conditions:
        writer = spec.writer(condition.writer)
        model = memory_spec.model(writer.name)
        memory_condition = next(
            value for value in memory_spec.conditions if value.name == condition.name
        )
        metadata = bundle["models"][writer.name]
        pair = _pair_from_dict(metadata["pair"])
        landscape = rulebook.landscape()
        for midpoint_index in range(spec.midpoint_count):
            base = int(metadata["midpoints"][midpoint_index])
            for history in ("A", "B"):
                target = pair.state(history)
                for mark_name in condition.mark_settings:
                    mark_spec = spec.mark(mark_name)
                    for carrier in condition.carrier_arms:
                        for age in condition.descendant_ages:
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
                                            memory_spec,
                                            bundle,
                                            rulebook,
                                            writer,
                                            condition,
                                            pair,
                                            midpoint_index,
                                            history,
                                            future_index,
                                            mark_name,
                                            training_write,
                                        )
                                    (
                                        trained_state,
                                        trained_mark,
                                        training_states,
                                        training_statuses,
                                        training_steps,
                                    ) = training_cache[training_key]
                                    donor_state: int | None = None
                                    donor_exact = True
                                    if carrier == "destination_matched_donor":
                                        donor_key = (
                                            condition.name,
                                            midpoint_index,
                                            history,
                                            future_index,
                                        )
                                        if donor_key not in donor_cache:
                                            half_size = condition.futures_per_cell // 2
                                            half_start = (
                                                0 if future_index < half_size else half_size
                                            )
                                            candidates = [
                                                half_start
                                                + (
                                                    (future_index - half_start + offset)
                                                    % half_size
                                                )
                                                for offset in range(1, half_size)
                                            ]
                                            chosen = _donor_index(
                                                future_index,
                                                condition.futures_per_cell,
                                            )
                                            matched = False
                                            for donor_future in candidates:
                                                key = (
                                                    condition.name,
                                                    midpoint_index,
                                                    history,
                                                    donor_future,
                                                    NO_MARK_NAME,
                                                    False,
                                                )
                                                if key not in training_cache:
                                                    training_cache[key] = _train(
                                                        spec,
                                                        memory_spec,
                                                        bundle,
                                                        rulebook,
                                                        writer,
                                                        condition,
                                                        pair,
                                                        midpoint_index,
                                                        history,
                                                        donor_future,
                                                        NO_MARK_NAME,
                                                        False,
                                                    )
                                                candidate = training_cache[key][0]
                                                if int(
                                                    landscape.attractor_index[candidate]
                                                ) == pair.index(history):
                                                    chosen = donor_future
                                                    matched = True
                                                    break
                                            key = (
                                                condition.name,
                                                midpoint_index,
                                                history,
                                                chosen,
                                                NO_MARK_NAME,
                                                False,
                                            )
                                            if key not in training_cache:
                                                training_cache[key] = _train(
                                                    spec,
                                                    memory_spec,
                                                    bundle,
                                                    rulebook,
                                                    writer,
                                                    condition,
                                                    pair,
                                                    midpoint_index,
                                                    history,
                                                    chosen,
                                                    NO_MARK_NAME,
                                                    False,
                                                )
                                            donor_cache[donor_key] = (
                                                training_cache[key][0],
                                                matched,
                                            )
                                        donor_state, donor_exact = donor_cache[donor_key]
                                    (
                                        state,
                                        mark,
                                        descriptor_exact,
                                        post_coupling,
                                        post_write,
                                    ) = _carrier_values(
                                        memory_spec,
                                        bundle,
                                        model,
                                        memory_condition,
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
                                    for cycle in range(age):
                                        carry_rng, mark_rng, dynamics_rng = _streams(
                                            memory_spec,
                                            bundle,
                                            model,
                                            history,
                                            midpoint_index,
                                            future_index,
                                            "descendant",
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
                                            writer.gamma_variance,
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
                                        damage_rng, _, _ = _streams(
                                            memory_spec,
                                            bundle,
                                            model,
                                            history,
                                            midpoint_index,
                                            future_index,
                                            f"damage-{age}",
                                            0,
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
                                    post = []
                                    for cycle in range(spec.horizon):
                                        carry_rng, mark_rng, dynamics_rng = _streams(
                                            memory_spec,
                                            bundle,
                                            model,
                                            history,
                                            midpoint_index,
                                            future_index,
                                            f"post-{age}-{challenge}",
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
                                            writer.gamma_variance,
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
                                        midpoint_index,
                                        history,
                                        mark_name,
                                        carrier,
                                        age,
                                        challenge,
                                        future_index,
                                    )
                                    records.append(
                                        {
                                            "future_id": future_id,
                                            "cohort_id": spec.cohort_id,
                                            "phase": spec.phase,
                                            "condition": condition.name,
                                            "source_id": bundle["source_id"],
                                            "engine": "wagner",
                                            "genes": spec.genes,
                                            "model": writer.name,
                                            "writer_tier": writer.tier,
                                            "variant": "wagner_sequential",
                                            "gamma_variance": writer.gamma_variance,
                                            "cue_mode": writer.intervention.mode,
                                            "cue_fraction": writer.intervention.fraction,
                                            "cue_dwell": writer.intervention.dwell,
                                            "field_strength": writer.intervention.field_strength,
                                            "mark_setting": mark_name,
                                            "carrier": carrier,
                                            "washout_age": age,
                                            "descendant_age": age,
                                            "challenge": challenge,
                                            "midpoint_index": midpoint_index,
                                            "history": history,
                                            "future_index": future_index,
                                            "half": (
                                                "A"
                                                if future_index
                                                < condition.futures_per_cell // 2
                                                else "B"
                                            ),
                                            "base_state": base,
                                            "target_state": target,
                                            "trained_state": trained_state,
                                            "trained_mark_norm": float(
                                                np.linalg.norm(trained_mark)
                                            ),
                                            "descriptor_exact": descriptor_exact,
                                            "damage_nodes": list(damage_nodes),
                                            "training_status": training_statuses[-1],
                                            "training_steps": training_steps[-1],
                                            **_summary_dict(summary),
                                        }
                                    )
    records.sort(
        key=lambda value: (
            value["model"],
            value["condition"],
            value["mark_setting"],
            value["carrier"],
            value["washout_age"],
            value["challenge"],
            value["midpoint_index"],
            value["history"],
            value["future_index"],
        )
    )
    return records


NO_MARK_NAME = "none"


def expected_heredity_source_futures(spec: WagnerHereditySpec) -> int:
    return sum(
        spec.midpoint_count
        * 2
        * len(condition.mark_settings)
        * len(condition.carrier_arms)
        * len(condition.descendant_ages)
        * len(condition.challenges)
        * condition.futures_per_cell
        for condition in spec.conditions
    )


def expected_heredity_futures(spec: WagnerHereditySpec) -> int:
    return spec.source_count * expected_heredity_source_futures(spec)


def iter_heredity_source_results(
    registry: dict[str, Any],
    spec: WagnerHereditySpec,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    if workers < 1:
        raise ValueError("heredity workers must be positive")
    sources = sorted(registry["sources"], key=lambda source: source["source_id"])
    expected = expected_heredity_futures(spec)
    per_source = expected_heredity_source_futures(spec)
    if workers == 1:
        for index, source in enumerate(sources, start=1):
            records = simulate_heredity_source(source, spec.to_dict())
            if progress is not None:
                progress(
                    f"simulated heredity source {index}/{len(sources)} "
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
                simulate_heredity_source,
                sources[next_submit],
                spec.to_dict(),
            )
            next_submit += 1
        for index, source in enumerate(sources):
            records = pending.pop(index).result()
            completed = index + 1
            if progress is not None:
                progress(
                    f"simulated heredity source {completed}/{len(sources)} "
                    f"({completed * per_source:,}/{expected:,} futures)"
                )
            yield source, records
            if next_submit < len(sources):
                pending[next_submit] = executor.submit(
                    simulate_heredity_source,
                    sources[next_submit],
                    spec.to_dict(),
                )
                next_submit += 1
