"""Resumable multigeneration carrier simulation for Boolean and Wagner GRNs."""

from __future__ import annotations

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
    read_jsonl_gz,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
    write_jsonl_gz,
)
from .engines import rulebook_from_dict
from .landscape import int_to_signs, normalized_hamming
from .lineage_carrier_config import (
    LINEAGE_MANIFEST_FORMAT,
    LINEAGE_RAW_FORMAT,
    LINEAGE_REGISTRATION_FORMAT,
    LineageArmSpec,
    LineageStudySpec,
)
from .mechanism_dynamics import MechanismRulebook
from .plastic_heredity_v2_carriers import _CarrierState, _advance, _blank
from .plastic_memory_campaign import build_memory_registry
from .plastic_memory_config import (
    CueDose,
    MarkSetting,
    MemoryCondition,
    MemoryModelSpec,
    MemorySourceSpec,
    PlasticMemorySpec,
)
from .plastic_memory_dynamics import (
    AttractorPair,
    clamp_state,
    cue_nodes,
    damage_state,
    develop_memory_cycle,
    summarize_memory_future,
)
from .rng import digest_parts, rng_for
from .study import source_hashes


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _model_name(engine: str) -> str:
    return f"{engine}.lineage"


def _eligibility_spec(spec: LineageStudySpec) -> PlasticMemorySpec:
    sources = tuple(
        MemorySourceSpec(
            f"{value.engine}_n{spec.genes}",
            value.engine,
            spec.genes,
            value.count,
            "boolean_sync" if value.engine == "boolean" else "wagner_sequential",
        )
        for value in spec.sources
    )
    models = tuple(
        MemoryModelSpec(
            _model_name(value.engine),
            f"{value.engine}_n{spec.genes}",
            "boolean_sync" if value.engine == "boolean" else "wagner_sequential",
        )
        for value in spec.sources
    )
    conditions = tuple(
        MemoryCondition(
            f"eligibility.{model.name}",
            model.name,
            CueDose(1.0, 1),
            ("none",),
            ("state_transplant",),
            (0,),
            ("release_only",),
            4,
        )
        for model in models
    )
    return PlasticMemorySpec(
        spec.cohort_id,
        f"{spec.phase}.eligibility",
        spec.master_seed,
        sources,
        models,
        (MarkSetting("none", 0, 0.0),),
        conditions,
        midpoint_count=spec.midpoint_count,
        horizon=spec.horizon,
        stable_run=spec.stable_run,
        strict_run=spec.strict_run,
        expression_flip_probability=spec.expression_flip_probability,
        neutral_damage_fraction=spec.neutral_damage_fraction,
        minimum_basin_fraction=spec.minimum_basin_fraction,
        minimum_form_distance=spec.minimum_form_distance,
        maximum_source_proposals=spec.maximum_source_proposals,
        wagner_max_sweeps=spec.wagner_max_sweeps,
        bootstrap_repetitions=spec.bootstrap_repetitions,
        interval_level=spec.interval_level,
        exploratory=spec.exploratory,
    )


def _pair(value: dict[str, Any]) -> AttractorPair:
    return AttractorPair(
        int(value["left_index"]),
        int(value["right_index"]),
        int(value["left_state"]),
        int(value["right_state"]),
    )


def _opposite(history: str) -> str:
    return "B" if history == "A" else "A"


def _pair_alignment(
    donor: AttractorPair, recipient: AttractorPair, genes: int
) -> tuple[float, dict[str, str]]:
    same = normalized_hamming(donor.left_state, recipient.left_state, genes) + normalized_hamming(
        donor.right_state, recipient.right_state, genes
    )
    swapped = normalized_hamming(
        donor.left_state, recipient.right_state, genes
    ) + normalized_hamming(donor.right_state, recipient.left_state, genes)
    if same <= swapped:
        return same, {"A": "A", "B": "B"}
    return swapped, {"A": "B", "B": "A"}


def _recipient_map(
    donor: dict[str, Any], candidates: list[dict[str, Any]], genes: int
) -> dict[str, Any]:
    donor_meta = donor["models"][_model_name(str(donor["engine"]))]
    donor_pair = _pair(donor_meta["pair"])
    alternatives = [value for value in candidates if value["source_id"] != donor["source_id"]]
    if not alternatives:
        return {
            mode: {"source_id": donor["source_id"], "history_map": {"A": "A", "B": "B"}}
            for mode in ("clone", "destination_matched", "descriptor_matched")
        }
    scored: list[tuple[float, float, str, dict[str, str]]] = []
    donor_separation = normalized_hamming(
        donor_pair.left_state, donor_pair.right_state, genes
    )
    for candidate in alternatives:
        metadata = candidate["models"][_model_name(str(candidate["engine"]))]
        pair = _pair(metadata["pair"])
        alignment, mapping = _pair_alignment(donor_pair, pair, genes)
        separation = normalized_hamming(pair.left_state, pair.right_state, genes)
        scored.append(
            (
                alignment,
                abs(separation - donor_separation),
                str(candidate["source_id"]),
                mapping,
            )
        )
    destination = min(scored, key=lambda value: (value[0], value[1], value[2]))
    descriptor = min(scored, key=lambda value: (value[1], -value[0], value[2]))
    return {
        "clone": {
            "source_id": donor["source_id"],
            "history_map": {"A": "A", "B": "B"},
        },
        "destination_matched": {
            "source_id": destination[2],
            "history_map": destination[3],
        },
        "descriptor_matched": {
            "source_id": descriptor[2],
            "history_map": descriptor[3],
        },
    }


def build_lineage_registry(
    spec: LineageStudySpec, progress: Callable[[str], None] | None = None
) -> dict[str, Any]:
    """Generate outcome-blind donors and freeze compatibility recipients."""

    registry = build_memory_registry(_eligibility_spec(spec), progress)
    by_engine = {
        engine: [value for value in registry["sources"] if value["engine"] == engine]
        for engine in ("boolean", "wagner")
    }
    mappings = {
        str(source["source_id"]): _recipient_map(
            source, by_engine[str(source["engine"])], spec.genes
        )
        for source in registry["sources"]
    }
    registry["format"] = "gre-wagner-lineage-carrier-rulebooks-v1"
    registry["recipient_mappings"] = mappings
    return registry


def _write_from_states(
    inherited: _CarrierState,
    candidate: Any,
    states: tuple[int, ...],
    genes: int,
) -> _CarrierState:
    if not states:
        return inherited
    values = np.asarray(inherited.values, dtype=float).copy()
    ttl = np.asarray(inherited.ttl, dtype=int).copy()
    if candidate.mechanism in {
        "trace",
        "recurrent_field",
        "wagner_edge_trace",
        "boolean_transition_trace",
    }:
        for state in states:
            signs = int_to_signs(state, genes).astype(float)
            values = candidate.rho * values + (1.0 - candidate.rho) * signs
        return _CarrierState(
            tuple(float(value) for value in np.clip(values, -1.0, 1.0)),
            tuple(int(value) for value in ttl),
        )
    if candidate.mechanism == "latch":
        signs = np.asarray([int_to_signs(state, genes) for state in states], dtype=float)
        threshold = int(candidate.write_threshold)
        if len(states) >= threshold:
            tail = signs[-threshold:]
            agreed = np.all(tail == tail[0], axis=0)
            values[agreed] = tail[0, agreed]
            ttl[agreed] = int(candidate.retention)
        return _CarrierState(
            tuple(float(value) for value in values),
            tuple(int(value) for value in ttl),
        )
    raise ValueError(f"unsupported lineage carrier mechanism: {candidate.mechanism}")


def _influence_order(
    viewed: MechanismRulebook,
    pair: AttractorPair,
    forced_breaks: dict[str, int],
    carrier: _CarrierState,
) -> tuple[int, ...]:
    states = (
        pair.left_state,
        pair.right_state,
        int(forced_breaks["A"]),
        int(forced_breaks["B"]),
    )
    values = np.asarray(carrier.values, dtype=float)
    scores: list[tuple[float, int]] = []
    for gene in range(viewed.genes):
        sensitivity = float(
            np.mean(
                [
                    normalized_hamming(
                        viewed.step(state), viewed.step(state ^ (1 << gene)), viewed.genes
                    )
                    for state in states
                ]
            )
        )
        scores.append((abs(float(values[gene])) * sensitivity, gene))
    return tuple(gene for _score, gene in sorted(scores, key=lambda value: (-value[0], value[1])))


def _retain(state: _CarrierState, indices: tuple[int, ...]) -> _CarrierState:
    values = np.zeros(len(state.values), dtype=float)
    ttl = np.zeros(len(state.ttl), dtype=int)
    for index in indices:
        values[index] = float(state.values[index])
        ttl[index] = int(state.ttl[index])
    return _CarrierState(
        tuple(float(value) for value in values), tuple(int(value) for value in ttl)
    )


def _bottleneck(
    state: _CarrierState,
    arm: LineageArmSpec,
    targeted_order: tuple[int, ...],
    random_order: tuple[int, ...],
    permutation: tuple[int, ...],
) -> _CarrierState:
    if arm.bottleneck == "zero":
        return _blank(len(state.values))
    if arm.bottleneck == "targeted":
        return _retain(state, targeted_order[: arm.k])
    if arm.bottleneck == "random":
        return _retain(state, random_order[: arm.k])
    if arm.bottleneck == "shuffle":
        return _CarrierState(
            tuple(float(state.values[index]) for index in permutation),
            tuple(int(state.ttl[index]) for index in permutation),
        )
    return state


def _founder_carrier(
    spec: LineageStudySpec,
    donor: dict[str, Any],
    candidate: Any,
    arm: LineageArmSpec,
    midpoint_index: int,
    history: str,
    future_index: int,
) -> tuple[_CarrierState, tuple[int, ...], bool, str]:
    engine = str(donor["engine"])
    writer = spec.writer(engine)
    metadata = donor["models"][_model_name(engine)]
    pair = _pair(metadata["pair"])
    founder_history = _opposite(history) if arm.bottleneck == "opposite" else history
    target = pair.state(founder_history)
    base = int(metadata["midpoints"][midpoint_index])
    if arm.writer_mode == "exact":
        dwell = max(2, int(candidate.write_threshold))
        training_states = tuple(target for _ in range(dwell))
    else:
        viewed = MechanismRulebook(
            rulebook_from_dict(donor["source"]),
            "boolean_sync" if engine == "boolean" else "wagner_sequential",
        )
        ordering = np.asarray(metadata["node_order"], dtype=int)
        nodes = cue_nodes(pair, viewed.genes, writer.cue_fraction, ordering)
        state = base
        trained: list[int] = []
        for cycle in range(writer.cue_dwell):
            common = (
                spec.master_seed,
                "lineage-founder",
                donor["source_id"],
                midpoint_index,
                history,
                future_index,
                cycle,
            )
            value = develop_memory_cycle(
                viewed,
                state,
                base,
                np.zeros(viewed.genes, dtype=float),
                1.0,
                spec.expression_flip_probability,
                0.0,
                0.0,
                0.0,
                spec.wagner_max_sweeps,
                rng_for(*common, "carry"),
                rng_for(*common, "mark"),
                rng_for(*common, "dynamics"),
                cue_target=target,
                clamped_nodes=nodes,
                write_mark=False,
            )
            state = int(value.state)
            trained.append(state)
        training_states = tuple(trained)
    acquired = bool(training_states and training_states[-1] == target)
    carrier = (
        _write_from_states(_blank(spec.genes), candidate, training_states, spec.genes)
        if arm.write_enabled
        else _blank(spec.genes)
    )
    return carrier, training_states, acquired, founder_history


def _assay(
    spec: LineageStudySpec,
    recipient: dict[str, Any],
    candidate: Any,
    arm: LineageArmSpec,
    incoming: _CarrierState,
    midpoint_index: int,
    history: str,
    future_index: int,
    generation: int,
    challenge: str,
) -> Any:
    engine = str(recipient["engine"])
    viewed = MechanismRulebook(
        rulebook_from_dict(recipient["source"]),
        "boolean_sync" if engine == "boolean" else "wagner_sequential",
    )
    metadata = recipient["models"][_model_name(engine)]
    pair = _pair(metadata["pair"])
    base = int(metadata["midpoints"][midpoint_index])
    state = base
    if challenge == "forced_break":
        state = int(metadata["forced_breaks"][history])
    elif challenge == "neutral_damage":
        state, _ = damage_state(
            state,
            viewed.genes,
            spec.neutral_damage_fraction,
            rng_for(
                spec.master_seed,
                "lineage-damage",
                recipient["source_id"],
                candidate.name,
                midpoint_index,
                history,
                future_index,
                generation,
            ),
        )
    elif challenge != "release_only":
        raise ValueError(f"unknown lineage challenge: {challenge}")
    coupling = float(candidate.coupling) if arm.read_enabled else 0.0
    carrier = incoming
    post = []
    for cycle in range(spec.horizon):
        common = (
            spec.master_seed,
            "lineage-assay",
            recipient["source_id"],
            candidate.name,
            midpoint_index,
            history,
            future_index,
            generation,
            challenge,
            cycle,
        )
        value, carrier = _advance(
            spec,
            viewed,
            candidate,
            state,
            base,
            carrier,
            coupling,
            rng_for(*common, "carry"),
            rng_for(*common, "carrier"),
        )
        post.append(value)
        state = int(value.state)
    return summarize_memory_future(
        (), tuple(post), pair, history, np.asarray(incoming.values), spec.strict_run, spec.stable_run
    )


def _propagate(
    spec: LineageStudySpec,
    recipient: dict[str, Any],
    candidate: Any,
    arm: LineageArmSpec,
    incoming: _CarrierState,
    targeted_order: tuple[int, ...],
    random_order: tuple[int, ...],
    permutation: tuple[int, ...],
    midpoint_index: int,
    history: str,
    future_index: int,
    generation: int,
) -> _CarrierState:
    engine = str(recipient["engine"])
    viewed = MechanismRulebook(
        rulebook_from_dict(recipient["source"]),
        "boolean_sync" if engine == "boolean" else "wagner_sequential",
    )
    metadata = recipient["models"][_model_name(engine)]
    base = int(metadata["midpoints"][midpoint_index])
    state = base
    carrier = incoming
    adults: list[int] = []
    coupling = float(candidate.coupling) if arm.read_enabled else 0.0
    for cycle in range(spec.generation_cycles):
        common = (
            spec.master_seed,
            "lineage-propagation",
            recipient["source_id"],
            candidate.name,
            midpoint_index,
            history,
            future_index,
            generation,
            cycle,
        )
        value, carrier = _advance(
            spec,
            viewed,
            candidate,
            state,
            base,
            carrier,
            coupling,
            rng_for(*common, "carry"),
            rng_for(*common, "carrier"),
        )
        state = int(value.state)
        adults.append(state)
    if arm.rewrite and arm.write_enabled:
        carrier = _write_from_states(carrier, candidate, tuple(adults), viewed.genes)
    return _bottleneck(carrier, arm, targeted_order, random_order, permutation)


def _summary_dict(summary: Any, acquired: bool) -> dict[str, Any]:
    return {
        "acquired": acquired,
        "form_destination": summary.form_destination,
        "correct_hold_run": summary.correct_hold_run,
        "wrong_hold_run": summary.wrong_hold_run,
        "generic_hold_run": summary.generic_hold_run,
        "correct_hold8": summary.correct_hold8,
        "wrong_hold8": summary.wrong_hold8,
        "generic_hold8": summary.generic_hold8,
        "returned": summary.returned,
        "return_cycle": summary.return_cycle,
        "first_break_cycle": summary.first_break_cycle,
        "point_cycles": summary.point_cycles,
        "cycle_cycles": summary.cycle_cycles,
        "nonconvergent_cycles": summary.nonconvergent_cycles,
        "unique_adult_states": summary.unique_adult_states,
        "start_mark_norm": summary.start_mark_norm,
        "end_mark_norm": summary.end_mark_norm,
        "trace_digest": summary.trace_digest,
    }


def simulate_lineage_source(
    task: dict[str, Any], spec_value: dict[str, Any]
) -> list[dict[str, Any]]:
    spec = LineageStudySpec.from_dict(spec_value)
    donor = task["donor"]
    engine = str(donor["engine"])
    records: list[dict[str, Any]] = []
    for recipient_mode in spec.recipient_modes:
        link = task["recipients"][recipient_mode]
        recipient = link["source"]
        history_map = {str(key): str(value) for key, value in link["history_map"].items()}
        recipient_metadata = recipient["models"][_model_name(engine)]
        recipient_pair = _pair(recipient_metadata["pair"])
        viewed_recipient = MechanismRulebook(
            rulebook_from_dict(recipient["source"]),
            "boolean_sync" if engine == "boolean" else "wagner_sequential",
        )
        permutation = tuple(int(value) for value in recipient_metadata["mark_permutation"])
        random_order = tuple(int(value) for value in recipient_metadata["ablation_order"])
        for candidate in spec.carriers:
            if engine not in candidate.engines:
                continue
            model = f"{engine}.{candidate.name}.{recipient_mode}"
            for midpoint_index in range(spec.midpoint_count):
                for donor_history in ("A", "B"):
                    history = history_map[donor_history]
                    for arm in spec.arms:
                        for future_index in range(spec.futures_per_cell):
                            founder, training_states, acquired, founder_history = _founder_carrier(
                                spec,
                                donor,
                                candidate,
                                arm,
                                midpoint_index,
                                donor_history,
                                future_index,
                            )
                            targeted_order = _influence_order(
                                viewed_recipient,
                                recipient_pair,
                                recipient_metadata["forced_breaks"],
                                founder,
                            )
                            initial = _bottleneck(
                                founder, arm, targeted_order, random_order, permutation
                            )
                            archived_founder = initial
                            incoming = initial
                            lineage_payload: list[Any] = []
                            checkpoints = set(spec.checkpoint_generations)
                            maximum = max(spec.checkpoint_generations)
                            for generation in range(maximum + 1):
                                if arm.ablate_generation == generation:
                                    incoming = _blank(spec.genes)
                                if arm.rescue_generation == generation:
                                    incoming = archived_founder
                                lineage_payload.append(
                                    (generation, list(incoming.values), list(incoming.ttl))
                                )
                                if generation in checkpoints:
                                    lineage_digest = canonical_digest(lineage_payload)
                                    for challenge in spec.challenges:
                                        summary = _assay(
                                            spec,
                                            recipient,
                                            candidate,
                                            arm,
                                            incoming,
                                            midpoint_index,
                                            history,
                                            future_index,
                                            generation,
                                            challenge,
                                        )
                                        future_id = digest_parts(
                                            LINEAGE_RAW_FORMAT,
                                            spec.cohort_id,
                                            donor["source_id"],
                                            recipient["source_id"],
                                            recipient_mode,
                                            candidate.name,
                                            midpoint_index,
                                            donor_history,
                                            arm.name,
                                            generation,
                                            challenge,
                                            future_index,
                                        )
                                        records.append(
                                            {
                                                "future_id": future_id,
                                                "cohort_id": spec.cohort_id,
                                                "phase": spec.phase,
                                                "condition": spec.phase,
                                                "source_set": donor["source_set"],
                                                "source_id": donor["source_id"],
                                                "recipient_source_id": recipient["source_id"],
                                                "recipient_mode": recipient_mode,
                                                "engine": engine,
                                                "genes": spec.genes,
                                                "model": model,
                                                "variant": viewed_recipient.variant,
                                                "candidate": candidate.name,
                                                "carrier_mechanism": candidate.mechanism,
                                                "mark_setting": candidate.name,
                                                "carrier": arm.name,
                                                "writer_mode": arm.writer_mode,
                                                "cue_fraction": spec.writer(engine).cue_fraction,
                                                "cue_dwell": spec.writer(engine).cue_dwell,
                                                "midpoint_index": midpoint_index,
                                                "history": history,
                                                "donor_history": donor_history,
                                                "founder_history": founder_history,
                                                "target_state": recipient_pair.state(history),
                                                "washout_age": generation,
                                                "generation": generation,
                                                "challenge": challenge,
                                                "future_index": future_index,
                                                "half": "A"
                                                if future_index < spec.futures_per_cell // 2
                                                else "B",
                                                "bottleneck": arm.bottleneck,
                                                "bottleneck_k": arm.k,
                                                "rewrite": arm.rewrite,
                                                "read_enabled": arm.read_enabled,
                                                "write_enabled": arm.write_enabled,
                                                "retained_coordinates": int(
                                                    np.count_nonzero(incoming.values)
                                                ),
                                                "lineage_digest": lineage_digest,
                                                **_summary_dict(summary, acquired),
                                            }
                                        )
                                if generation < maximum:
                                    incoming = _propagate(
                                        spec,
                                        recipient,
                                        candidate,
                                        arm,
                                        incoming,
                                        targeted_order,
                                        random_order,
                                        permutation,
                                        midpoint_index,
                                        history,
                                        future_index,
                                        generation,
                                    )
    records.sort(
        key=lambda value: (
            value["recipient_mode"],
            value["model"],
            value["midpoint_index"],
            value["history"],
            value["carrier"],
            value["generation"],
            value["challenge"],
            value["future_index"],
        )
    )
    return records


def expected_lineage_source_records(spec: LineageStudySpec, engine: str) -> int:
    candidates = sum(engine in value.engines for value in spec.carriers)
    return (
        candidates
        * spec.midpoint_count
        * 2
        * len(spec.arms)
        * spec.futures_per_cell
        * len(spec.recipient_modes)
        * len(spec.checkpoint_generations)
        * len(spec.challenges)
    )


def expected_lineage_records(spec: LineageStudySpec) -> int:
    return sum(
        value.count * expected_lineage_source_records(spec, value.engine)
        for value in spec.sources
    )


def _task_for_source(
    source: dict[str, Any], registry: dict[str, Any], modes: tuple[str, ...]
) -> dict[str, Any]:
    lookup = {str(value["source_id"]): value for value in registry["sources"]}
    mappings = registry["recipient_mappings"][str(source["source_id"])]
    return {
        "donor": source,
        "recipients": {
            mode: {
                "source": lookup[str(mappings[mode]["source_id"])],
                "history_map": mappings[mode]["history_map"],
            }
            for mode in modes
        },
    }


def _iter_results(
    tasks: list[dict[str, Any]],
    spec: LineageStudySpec,
    workers: int,
    progress: Callable[[str], None] | None,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    if workers == 1:
        for index, task in enumerate(tasks, start=1):
            records = simulate_lineage_source(task, spec.to_dict())
            if progress is not None:
                progress(f"simulated lineage source {index}/{len(tasks)}")
            yield task, records
        return
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        pending: dict[int, concurrent.futures.Future[list[dict[str, Any]]]] = {}
        next_submit = 0
        window = workers * 2
        while next_submit < min(window, len(tasks)):
            pending[next_submit] = executor.submit(
                simulate_lineage_source, tasks[next_submit], spec.to_dict()
            )
            next_submit += 1
        for index, task in enumerate(tasks):
            records = pending.pop(index).result()
            if progress is not None:
                progress(f"simulated lineage source {index + 1}/{len(tasks)}")
            yield task, records
            if next_submit < len(tasks):
                pending[next_submit] = executor.submit(
                    simulate_lineage_source, tasks[next_submit], spec.to_dict()
                )
                next_submit += 1


def _valid_shard(
    shard: Path,
    manifest_path: Path,
    protocol_digest: str,
    source_id: str,
    expected: int,
) -> tuple[bool, int]:
    if not shard.is_file() or not manifest_path.is_file():
        return False, 0
    try:
        manifest = read_json(manifest_path)
        valid = (
            manifest.get("protocol_digest") == protocol_digest
            and manifest.get("source_id") == source_id
            and manifest.get("sha256") == sha256_file(shard)
            and int(manifest.get("record_count", -1)) == expected
        )
        return valid, expected if valid else 0
    except (OSError, TypeError, ValueError, KeyError):
        return False, 0


def run_lineage_study(
    spec: LineageStudySpec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("lineage carrier study requires 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_lineage_study(destination)
        return destination
    started = time.monotonic()
    progress_path = destination / "progress.json"
    prior_elapsed = 0.0
    if progress_path.is_file():
        try:
            prior_elapsed = float(read_json(progress_path).get("elapsed_seconds", 0.0))
        except (OSError, TypeError, ValueError):
            prior_elapsed = 0.0
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": LINEAGE_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing lineage study registration differs")
    else:
        _atomic_json(registration_path, registration)
    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        registry = read_json(registry_path)
    else:
        registry = build_lineage_registry(spec, progress)
        _atomic_json(registry_path, registry)
    expected = expected_lineage_records(spec)
    shards = destination / "shards"
    shards.mkdir(exist_ok=True)
    completed: set[str] = set()
    completed_records = 0
    for source in registry["sources"]:
        source_id = str(source["source_id"])
        source_expected = expected_lineage_source_records(spec, str(source["engine"]))
        valid, count = _valid_shard(
            shards / f"{source_id}.jsonl.gz",
            shards / f"{source_id}.manifest.json",
            digest,
            source_id,
            source_expected,
        )
        if valid:
            completed.add(source_id)
            completed_records += count
    missing = [
        _task_for_source(source, registry, spec.recipient_modes)
        for source in registry["sources"]
        if source["source_id"] not in completed
    ]
    for task, records in _iter_results(missing, spec, workers, progress):
        source_id = str(task["donor"]["source_id"])
        source_expected = expected_lineage_source_records(
            spec, str(task["donor"]["engine"])
        )
        temporary = shards / f".{source_id}.jsonl.gz.tmp"
        count = write_jsonl_gz(temporary, records)
        if count != source_expected:
            raise RuntimeError(
                f"lineage source produced {count}; expected {source_expected}"
            )
        shard = shards / f"{source_id}.jsonl.gz"
        temporary.replace(shard)
        _atomic_json(
            shards / f"{source_id}.manifest.json",
            {
                "format": "gre-wagner-lineage-carrier-shard-v1",
                "source_id": source_id,
                "protocol_digest": digest,
                "record_count": count,
                "sha256": sha256_file(shard),
            },
        )
        completed.add(source_id)
        completed_records += count
        elapsed = prior_elapsed + time.monotonic() - started
        rate = completed_records / max(elapsed, 1e-9)
        _atomic_json(
            progress_path,
            {
                "format": "gre-wagner-lineage-carrier-progress-v1",
                "completed_sources": len(completed),
                "total_sources": len(registry["sources"]),
                "completed_records": completed_records,
                "expected_records": expected,
                "elapsed_seconds": elapsed,
                "records_per_second": rate,
                "eta_seconds": (expected - completed_records) / rate if rate else None,
            },
        )

    def merged() -> Iterator[dict[str, Any]]:
        for source in sorted(registry["sources"], key=lambda value: value["source_id"]):
            yield from read_jsonl_gz(shards / f"{source['source_id']}.jsonl.gz")

    futures = destination / "futures.jsonl.gz"
    temporary_futures = destination / ".futures.jsonl.gz.tmp"
    count = write_jsonl_gz(temporary_futures, merged())
    temporary_futures.replace(futures)
    if count != expected:
        raise RuntimeError(f"lineage study produced {count}; expected {expected}")
    if progress is not None:
        progress("analyzing multigeneration carrier and causal gates")
    from .lineage_carrier_analysis import analyze_lineage_path, render_lineage_report

    analysis = analyze_lineage_path(futures, spec)
    _atomic_json(destination / "analysis.json", analysis)
    manifest = {
        "format": LINEAGE_MANIFEST_FORMAT,
        "protocol_digest": digest,
        "raw_format": LINEAGE_RAW_FORMAT,
        "record_count": count,
        "expected_record_count": expected,
        "source_rulebooks": len(registry["sources"]),
        "workers": workers,
        "elapsed_seconds": prior_elapsed + time.monotonic() - started,
        "runtime": runtime_manifest(),
        "source_hashes": source_hashes(),
    }
    _atomic_json(destination / "manifest.json", manifest)
    (destination / "report.md").write_text(
        render_lineage_report(analysis), encoding="utf-8"
    )
    write_checksums(destination)
    verify_lineage_study(destination)
    if progress is not None:
        progress("sealed multigeneration lineage-carrier study")
    return destination


def verify_lineage_study(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != LINEAGE_REGISTRATION_FORMAT:
        raise ValueError("lineage registration format mismatch")
    if manifest.get("format") != LINEAGE_MANIFEST_FORMAT:
        raise ValueError("lineage manifest format mismatch")
    spec = LineageStudySpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("lineage protocol digest mismatch")
    expected = expected_lineage_records(spec)
    seen: set[str] = set()
    count = 0
    for record in read_jsonl_gz(directory / "futures.jsonl.gz"):
        count += 1
        future_id = str(record["future_id"])
        if future_id in seen:
            raise ValueError(f"duplicate lineage future: {future_id}")
        seen.add(future_id)
    if count != expected or count != int(manifest["record_count"]):
        raise ValueError(f"lineage record mismatch: {count}, expected {expected}")
    return {
        "verified": True,
        "files": len(checksums),
        "records": count,
        "unique_future_ids": len(seen),
        "protocol_digest": digest,
    }


def replay_lineage_future(directory: Path, future_id: str) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = LineageStudySpec.from_dict(registration["protocol"])
    archived = next(
        (
            record
            for record in read_jsonl_gz(directory / "futures.jsonl.gz")
            if record["future_id"] == future_id
        ),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown lineage future: {future_id}")
    registry = read_json(directory / "rulebooks.json")
    source = next(
        value
        for value in registry["sources"]
        if value["source_id"] == archived["source_id"]
    )
    candidate = spec.carrier(str(archived["candidate"]))
    arm = next(value for value in spec.arms if value.name == archived["carrier"])
    generation = int(archived["generation"])
    narrowed = replace(
        spec,
        carriers=(candidate,),
        arms=(arm,),
        checkpoint_generations=tuple(
            value for value in spec.checkpoint_generations if value <= generation
        ),
        challenges=(str(archived["challenge"]),),
        recipient_modes=(str(archived["recipient_mode"]),),
    )
    task = _task_for_source(source, registry, narrowed.recipient_modes)
    replayed = next(
        value
        for value in simulate_lineage_source(task, narrowed.to_dict())
        if value["future_id"] == future_id
    )
    fields = (
        "form_destination",
        "correct_hold8",
        "wrong_hold8",
        "returned",
        "trace_digest",
        "lineage_digest",
    )
    return {
        "future_id": future_id,
        "matches": all(archived[field] == replayed[field] for field in fields),
        "archived": {field: archived[field] for field in fields},
        "replayed": {field: replayed[field] for field in fields},
    }
