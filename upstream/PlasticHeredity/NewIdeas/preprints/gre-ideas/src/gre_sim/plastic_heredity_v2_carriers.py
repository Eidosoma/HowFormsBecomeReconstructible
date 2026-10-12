"""Engine-neutral trace, recurrent-field, and latch carrier experiments."""

from __future__ import annotations

import collections
import concurrent.futures
import math
import multiprocessing
import time
from dataclasses import dataclass, replace
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
from .endpoints import apply_carryover
from .engines import rulebook_from_dict
from .landscape import canonical_cycle, int_to_signs, signs_to_int
from .mechanism_dynamics import MechanismRulebook
from .plastic_heredity_v2_config import CarrierStudyV2Spec, CarrierV2Spec
from .plastic_memory_analysis import (
    _bootstrap,
    _cell,
    _outcome_key,
    _reliability,
    _source_metric_values,
)
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
    MemoryCycle,
    apply_mark_bias,
    damage_state,
    summarize_memory_future,
)
from .rng import digest_parts, rng_for
from .study import source_hashes
from .types import DevelopmentResult
from .wagner import WagnerRulebook


CARRIER_REGISTRATION_FORMAT = "gre-plastic-heredity-v2-carrier-registration-v1"
CARRIER_RAW_FORMAT = "gre-plastic-heredity-v2-carrier-futures-v1"
CARRIER_ANALYSIS_FORMAT = "gre-plastic-heredity-v2-carrier-analysis-v1"


@dataclass(frozen=True)
class _CarrierState:
    values: tuple[float, ...]
    ttl: tuple[int, ...]


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _eligibility_spec(spec: CarrierStudyV2Spec) -> PlasticMemorySpec:
    sources = (
        MemorySourceSpec("boolean_n10", "boolean", spec.genes, spec.source_count_per_engine, "boolean_sync"),
        MemorySourceSpec("wagner_n10", "wagner", spec.genes, spec.source_count_per_engine, "wagner_sequential"),
    )
    models = (
        MemoryModelSpec("boolean.base", "boolean_n10", "boolean_sync"),
        MemoryModelSpec("wagner.base", "wagner_n10", "wagner_sequential"),
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
        maximum_source_proposals=spec.maximum_source_proposals,
        wagner_max_sweeps=spec.wagner_max_sweeps,
        bootstrap_repetitions=spec.bootstrap_repetitions,
        interval_level=spec.interval_level,
        exploratory=spec.exploratory,
    )


def build_carrier_registry(
    spec: CarrierStudyV2Spec,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    registry = build_memory_registry(_eligibility_spec(spec), progress)
    registry["format"] = "gre-plastic-heredity-v2-carrier-rulebooks-v1"
    return registry


def _pair(value: dict[str, Any]) -> AttractorPair:
    return AttractorPair(
        int(value["left_index"]),
        int(value["right_index"]),
        int(value["left_state"]),
        int(value["right_state"]),
    )


def _blank(genes: int) -> _CarrierState:
    return _CarrierState((0.0,) * genes, (0,) * genes)


def _train_carrier(
    candidate: CarrierV2Spec, target: int, genes: int
) -> tuple[_CarrierState, tuple[int, ...]]:
    signs = int_to_signs(target, genes).astype(float)
    dwell = max(2, candidate.write_threshold)
    if candidate.mechanism in {
        "trace",
        "recurrent_field",
        "wagner_edge_trace",
        "boolean_transition_trace",
    }:
        values = np.zeros(genes, dtype=float)
        for _ in range(dwell):
            values = candidate.rho * values + (1.0 - candidate.rho) * signs
        state = _CarrierState(tuple(float(value) for value in values), (0,) * genes)
    elif candidate.mechanism == "latch":
        values = signs.copy() if dwell >= candidate.write_threshold else np.zeros(genes)
        ttl = np.full(genes, candidate.retention, dtype=int)
        state = _CarrierState(
            tuple(float(value) for value in values),
            tuple(int(value) for value in ttl),
        )
    else:  # pragma: no cover - protected by validation.
        raise ValueError(candidate.mechanism)
    return state, tuple([target] * dwell)


def _ablate(
    state: _CarrierState,
    fraction: float,
    random_order: tuple[int, ...] | None = None,
) -> _CarrierState:
    values = np.asarray(state.values, dtype=float).copy()
    ttl = np.asarray(state.ttl, dtype=int).copy()
    amount = int(math.ceil(fraction * len(values)))
    if amount == 0:
        return state
    if random_order is None:
        indices = sorted(range(len(values)), key=lambda gene: (-abs(values[gene]), gene))[:amount]
    else:
        indices = list(random_order[:amount])
    values[indices] = 0.0
    ttl[indices] = 0
    return _CarrierState(
        tuple(float(value) for value in values), tuple(int(value) for value in ttl)
    )


def _prepare_arm(
    trained: _CarrierState,
    candidate: CarrierV2Spec,
    arm: str,
    permutation: tuple[int, ...],
    random_order: tuple[int, ...],
) -> tuple[_CarrierState, float]:
    if arm in {"carrier_transplant", "ablation_0", "rescue"}:
        return trained, candidate.coupling
    if arm in {"reset", "write_disabled"}:
        return _blank(len(trained.values)), candidate.coupling
    if arm == "inert":
        return trained, 0.0
    if arm == "pattern_shuffle":
        return _CarrierState(
            tuple(trained.values[index] for index in permutation),
            tuple(trained.ttl[index] for index in permutation),
        ), candidate.coupling
    if arm.startswith("ablation_"):
        fraction = float(arm.removeprefix("ablation_")) / 100.0
        return _ablate(trained, fraction), candidate.coupling
    if arm.startswith("random_ablation_"):
        fraction = float(arm.removeprefix("random_ablation_")) / 100.0
        return _ablate(trained, fraction, random_order), candidate.coupling
    raise ValueError(f"unknown carrier arm: {arm}")


def _decay(state: _CarrierState, candidate: CarrierV2Spec) -> _CarrierState:
    values = np.asarray(state.values, dtype=float)
    ttl = np.asarray(state.ttl, dtype=int)
    if candidate.mechanism in {
        "trace",
        "recurrent_field",
        "wagner_edge_trace",
        "boolean_transition_trace",
    }:
        values = candidate.rho * values
        return _CarrierState(tuple(float(value) for value in values), state.ttl)
    ttl = np.maximum(0, ttl - 1)
    values = np.where(ttl > 0, values, 0.0)
    return _CarrierState(
        tuple(float(value) for value in values), tuple(int(value) for value in ttl)
    )


def _develop_recurrent_field(
    rulebook: MechanismRulebook,
    initial: int,
    carrier: _CarrierState,
    coupling: float,
    rng: np.random.Generator,
    max_sweeps: int,
) -> DevelopmentResult:
    current = int(initial)
    positions: dict[int, int] = {}
    path: list[int] = []
    values = np.asarray(carrier.values, dtype=float)
    for sweep in range(max_sweeps):
        if current in positions:
            cycle = canonical_cycle(path[positions[current] :])
            status = "point" if len(cycle) == 1 else "cycle"
            return DevelopmentResult(status, cycle[0] if status == "point" else current, sweep, cycle)
        positions[current] = len(path)
        path.append(current)
        following = rulebook.step(current)
        following = apply_mark_bias(following, values, coupling, rng)
        if following == current:
            return DevelopmentResult("point", current, sweep + 1, (current,))
        current = following
    return DevelopmentResult("nonconvergent", current, max_sweeps, ())


def _develop_wagner_edge_trace(
    rulebook: MechanismRulebook,
    initial: int,
    carrier: _CarrierState,
    coupling: float,
    max_sweeps: int,
) -> DevelopmentResult:
    source = rulebook.source
    if not isinstance(source, WagnerRulebook):
        raise TypeError("Wagner edge trace requires a Wagner rulebook")
    trace = np.asarray(carrier.values, dtype=float)
    weights = source.weights + coupling * np.outer(trace, trace) / source.genes
    current = int(initial)
    positions: dict[int, int] = {}
    path: list[int] = []
    for sweep in range(max_sweeps):
        if current in positions:
            cycle = canonical_cycle(path[positions[current] :])
            status = "point" if len(cycle) == 1 else "cycle"
            return DevelopmentResult(
                status, cycle[0] if status == "point" else current, sweep, cycle
            )
        positions[current] = len(path)
        path.append(current)
        signs = int_to_signs(current, source.genes)
        for gene_value in source.order:
            gene = int(gene_value)
            field = float(weights[gene] @ signs + source.bias[gene])
            if field > 0.0:
                signs[gene] = 1
            elif field < 0.0:
                signs[gene] = -1
        following = signs_to_int(signs)
        if following == current:
            return DevelopmentResult("point", current, sweep + 1, (current,))
        current = following
    return DevelopmentResult("nonconvergent", current, max_sweeps, ())


def _advance(
    spec: CarrierStudyV2Spec,
    rulebook: MechanismRulebook,
    candidate: CarrierV2Spec,
    previous: int,
    base: int,
    carrier: _CarrierState,
    coupling: float,
    carry_rng: np.random.Generator,
    carrier_rng: np.random.Generator,
) -> tuple[MemoryCycle, _CarrierState]:
    initial = apply_carryover(
        previous,
        base,
        rulebook.genes,
        1.0,
        spec.expression_flip_probability,
        carry_rng,
    )
    if candidate.mechanism in {"recurrent_field", "boolean_transition_trace"}:
        result = _develop_recurrent_field(
            rulebook,
            initial,
            carrier,
            coupling,
            carrier_rng,
            spec.wagner_max_sweeps,
        )
    elif candidate.mechanism == "wagner_edge_trace":
        result = _develop_wagner_edge_trace(
            rulebook,
            initial,
            carrier,
            coupling,
            spec.wagner_max_sweeps,
        )
    else:
        initial = apply_mark_bias(
            initial, np.asarray(carrier.values, dtype=float), coupling, carrier_rng
        )
        result = rulebook.develop(initial, None, spec.wagner_max_sweeps)
    following = _decay(carrier, candidate)
    return (
        MemoryCycle(
            int(result.final_state),
            following.values,
            result.status,
            int(result.steps),
        ),
        following,
    )


def _streams(
    spec: CarrierStudyV2Spec,
    source_id: str,
    candidate: str,
    midpoint: int,
    history: str,
    future: int,
    stage: str,
    cycle: int,
) -> tuple[np.random.Generator, np.random.Generator]:
    # Arm is omitted deliberately so every causal intervention receives paired noise.
    shared = (
        spec.master_seed,
        "plastic-heredity-v2-carrier-future",
        source_id,
        candidate,
        midpoint,
        history,
        future,
        stage,
        cycle,
    )
    return rng_for(*shared, "carry"), rng_for(*shared, "carrier")


def _summary(value: Any) -> dict[str, Any]:
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


def simulate_carrier_source(
    bundle: dict[str, Any], spec_value: dict[str, Any]
) -> list[dict[str, Any]]:
    spec = CarrierStudyV2Spec.from_dict(spec_value)
    source = rulebook_from_dict(bundle["source"])
    engine = str(bundle["engine"])
    base_model = f"{engine}.base"
    viewed = MechanismRulebook(
        source, "boolean_sync" if engine == "boolean" else "wagner_sequential"
    )
    metadata = bundle["models"][base_model]
    landscape = viewed.landscape()
    pair = _pair(metadata["pair"])
    permutation = tuple(int(value) for value in metadata["mark_permutation"])
    random_order = tuple(int(value) for value in metadata["ablation_order"])
    records: list[dict[str, Any]] = []
    for candidate in spec.carriers:
        if engine not in candidate.engines:
            continue
        model = f"{engine}.{candidate.name}"
        for midpoint_index in range(spec.midpoint_count):
            base = int(metadata["midpoints"][midpoint_index])
            for history in ("A", "B"):
                target = pair.state(history)
                trained, training_states = _train_carrier(candidate, target, viewed.genes)
                for arm in spec.arms:
                    for age in spec.descendant_ages:
                        for challenge in spec.challenges:
                            for future_index in range(spec.futures_per_cell):
                                carrier, coupling = _prepare_arm(
                                    trained, candidate, arm, permutation, random_order
                                )
                                start_carrier = carrier
                                # Every engineered-carrier recipient begins with a full
                                # expression reset. Only the registered carrier crosses.
                                state = base
                                for cycle in range(age):
                                    carry_rng, carrier_rng = _streams(
                                        spec,
                                        str(bundle["source_id"]),
                                        candidate.name,
                                        midpoint_index,
                                        history,
                                        future_index,
                                        f"descendant-{age}",
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
                                        carry_rng,
                                        carrier_rng,
                                    )
                                    state = value.state
                                damage_nodes: tuple[int, ...] = ()
                                if challenge == "forced_break":
                                    state = int(metadata["forced_breaks"][history])
                                elif challenge == "neutral_damage":
                                    state, damage_nodes = damage_state(
                                        state,
                                        viewed.genes,
                                        spec.neutral_damage_fraction,
                                        rng_for(
                                            spec.master_seed,
                                            "plastic-heredity-v2-carrier-damage",
                                            bundle["source_id"],
                                            candidate.name,
                                            midpoint_index,
                                            history,
                                            future_index,
                                            age,
                                        ),
                                    )
                                elif challenge != "release_only":
                                    raise ValueError(challenge)
                                post: list[MemoryCycle] = []
                                for cycle in range(spec.horizon):
                                    carry_rng, carrier_rng = _streams(
                                        spec,
                                        str(bundle["source_id"]),
                                        candidate.name,
                                        midpoint_index,
                                        history,
                                        future_index,
                                        f"post-{age}-{challenge}",
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
                                        carry_rng,
                                        carrier_rng,
                                    )
                                    post.append(value)
                                    state = value.state
                                summary = summarize_memory_future(
                                    training_states,
                                    tuple(post),
                                    pair,
                                    history,
                                    np.asarray(start_carrier.values, dtype=float),
                                    spec.strict_run,
                                    spec.stable_run,
                                )
                                future_id = digest_parts(
                                    "gre-plastic-heredity-v2-carrier-future-v1",
                                    spec.cohort_id,
                                    bundle["source_id"],
                                    candidate.name,
                                    midpoint_index,
                                    history,
                                    arm,
                                    age,
                                    challenge,
                                    future_index,
                                )
                                records.append(
                                    {
                                        "future_id": future_id,
                                        "cohort_id": spec.cohort_id,
                                        "phase": spec.phase,
                                        "condition": f"{candidate.name}.{engine}",
                                        "source_set": bundle["source_set"],
                                        "source_id": bundle["source_id"],
                                        "engine": engine,
                                        "genes": viewed.genes,
                                        "model": model,
                                        "variant": viewed.variant,
                                        "gamma_variance": 0.0,
                                        "cue_fraction": 1.0,
                                        "cue_dwell": max(2, candidate.write_threshold),
                                        "midpoint_index": midpoint_index,
                                        "base_state": base,
                                        "history": history,
                                        "target_state": target,
                                        "mark_setting": candidate.name,
                                        "carrier_mechanism": candidate.mechanism,
                                        "carrier_half_life": candidate.half_life,
                                        "carrier_coupling": candidate.coupling,
                                        "carrier_write_threshold": candidate.write_threshold,
                                        "carrier_retention": candidate.retention,
                                        "carrier": arm,
                                        "washout_age": age,
                                        "descendant_age": age,
                                        "challenge": challenge,
                                        "future_index": future_index,
                                        "half": "A"
                                        if future_index < spec.futures_per_cell // 2
                                        else "B",
                                        "descriptor_exact": True,
                                        "damage_nodes": list(damage_nodes),
                                        **_summary(summary),
                                    }
                                )
    records.sort(
        key=lambda value: (
            value["model"],
            value["midpoint_index"],
            value["history"],
            value["carrier"],
            value["washout_age"],
            value["challenge"],
            value["future_index"],
        )
    )
    return records


def expected_carrier_source_futures(
    spec: CarrierStudyV2Spec, engine: str | None = None
) -> int:
    candidates = (
        len(spec.carriers)
        if engine is None
        else sum(engine in candidate.engines for candidate in spec.carriers)
    )
    return (
        candidates
        * spec.midpoint_count
        * 2
        * len(spec.arms)
        * len(spec.descendant_ages)
        * len(spec.challenges)
        * spec.futures_per_cell
    )


def expected_carrier_futures(spec: CarrierStudyV2Spec) -> int:
    return spec.source_count_per_engine * sum(
        expected_carrier_source_futures(spec, engine)
        for engine in ("boolean", "wagner")
    )


def iter_carrier_source_results(
    registry: dict[str, Any],
    spec: CarrierStudyV2Spec,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    sources = sorted(registry["sources"], key=lambda value: value["source_id"])
    if workers == 1:
        for index, source in enumerate(sources, start=1):
            records = simulate_carrier_source(source, spec.to_dict())
            if progress is not None:
                progress(f"simulated v2 carrier source {index}/{len(sources)}")
            yield source, records
        return
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        pending: dict[int, concurrent.futures.Future[list[dict[str, Any]]]] = {}
        next_submit = 0
        window = workers * 2
        while next_submit < min(window, len(sources)):
            pending[next_submit] = executor.submit(
                simulate_carrier_source, sources[next_submit], spec.to_dict()
            )
            next_submit += 1
        for index, source in enumerate(sources):
            records = pending.pop(index).result()
            if progress is not None:
                progress(f"simulated v2 carrier source {index + 1}/{len(sources)}")
            yield source, records
            if next_submit < len(sources):
                pending[next_submit] = executor.submit(
                    simulate_carrier_source, sources[next_submit], spec.to_dict()
                )
                next_submit += 1


def _arm_rate(
    source_rates: dict[tuple[Any, str, str], list[float]],
    model: str,
    mark: str,
    arm: str,
    age: int,
) -> float | None:
    successes = 0.0
    total = 0.0
    for (cell, _source, field), value in source_rates.items():
        if (
            field == "correct_hold8"
            and cell[1] == model
            and cell[4] == mark
            and cell[5] == arm
            and cell[6] == age
            and cell[7] == "forced_break"
        ):
            successes += value[0]
            total += value[1]
    return successes / total if total else None


def _carrier_contrast(
    source_rates: dict[tuple[Any, str, str], list[float]],
    outcomes: dict[Any, collections.Counter[str]],
    model: str,
    mark: str,
    left: str,
    right: str,
    age: int,
    spec: CarrierStudyV2Spec,
    label: str,
    simultaneous: int,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    raw = _source_metric_values(
        source_rates,
        outcomes,
        model,
        mark,
        left,
        right,
        age,
        "forced_break",
    )
    memory_spec = _eligibility_spec(spec)
    estimates = {
        name: _bootstrap(
            values,
            memory_spec,
            f"plastic-heredity-v2-carrier.{label}.{name}",
            simultaneous,
        )
        for name, values in raw.items()
        if name != "sources"
    }
    return estimates, raw


def analyze_carrier_path(path: Path, spec: CarrierStudyV2Spec) -> dict[str, Any]:
    source_rates: dict[tuple[Any, str, str], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    outcomes: dict[Any, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    equivalence_pairs: dict[tuple[Any, ...], dict[str, str]] = {}
    record_count = 0
    future_ids: set[str] = set()
    for record in read_jsonl_gz(path):
        record_count += 1
        future_id = str(record["future_id"])
        if future_id in future_ids:
            raise ValueError(f"duplicate v2 carrier future: {future_id}")
        future_ids.add(future_id)
        cell = _cell(record)
        source = str(record["source_id"])
        for field in ("correct_hold8", "wrong_hold8", "generic_hold8", "returned"):
            value = source_rates[(cell, source, field)]
            value[0] += float(record[field])
            value[1] += 1.0
        half = source_rates[(cell, source, f"correct_hold8.half-{record['half']}")]
        half[0] += float(record["correct_hold8"])
        half[1] += 1.0
        outcomes[_outcome_key(record)][str(record["form_destination"])] += 1
        if record["carrier"] in {"carrier_transplant", "ablation_0"}:
            key = (
                source,
                record["model"],
                record["midpoint_index"],
                record["history"],
                record["washout_age"],
                record["challenge"],
                record["future_index"],
            )
            equivalence_pairs.setdefault(key, {})[str(record["carrier"])] = str(
                record["trace_digest"]
            )
    complete = [value for value in equivalence_pairs.values() if len(value) == 2]
    path_identity = {
        "pairs": len(complete),
        "matches": sum(
            value["carrier_transplant"] == value["ablation_0"] for value in complete
        ),
    }
    path_identity["equal"] = bool(complete) and path_identity["matches"] == len(complete)
    simultaneous = max(1, len(spec.carriers) * 2 * 10)
    gates: dict[str, Any] = {}
    for engine in ("boolean", "wagner"):
        for candidate in spec.carriers:
            if engine not in candidate.engines:
                continue
            model = f"{engine}.{candidate.name}"
            mark = candidate.name
            primary, raw = _carrier_contrast(
                source_rates,
                outcomes,
                model,
                mark,
                "carrier_transplant",
                "reset",
                0,
                spec,
                f"{model}.primary",
                simultaneous,
            )
            controls: dict[str, Any] = {}
            for control in ("write_disabled", "inert", "pattern_shuffle", "ablation_100"):
                if control not in spec.arms:
                    continue
                controls[control], _ = _carrier_contrast(
                    source_rates,
                    outcomes,
                    model,
                    mark,
                    "carrier_transplant",
                    control,
                    0,
                    spec,
                    f"{model}.{control}",
                    simultaneous,
                )
            generation_one, _ = _carrier_contrast(
                source_rates,
                outcomes,
                model,
                mark,
                "carrier_transplant",
                "reset",
                1,
                spec,
                f"{model}.generation-one",
                simultaneous,
            )
            reliability = _reliability(
                source_rates,
                model,
                mark,
                "carrier_transplant",
                0,
                "forced_break",
            )
            rates = {
                arm: _arm_rate(source_rates, model, mark, arm, 0)
                for arm in spec.arms
            }
            ablation_rates = [rates.get(f"ablation_{amount}") for amount in (0, 25, 50, 100)]
            monotonic = all(value is not None for value in ablation_rates) and all(
                float(left) + 1e-12 >= float(right)
                for left, right in zip(ablation_rates, ablation_rates[1:])
            )
            rescue_fraction = None
            if (
                rates.get("rescue") is not None
                and rates.get("ablation_100") is not None
                and rates.get("carrier_transplant") is not None
            ):
                denominator = float(rates["carrier_transplant"]) - float(rates["ablation_100"])
                if denominator > 0.0:
                    rescue_fraction = (
                        float(rates["rescue"]) - float(rates["ablation_100"])
                    ) / denominator
            risk = primary["risk_difference"]
            crossover = primary["crossover"]
            logloss = primary["log_loss_gain"]
            criteria = {
                "risk_difference_at_least_0_05": risk["mean"] is not None
                and float(risk["mean"]) >= 0.05,
                "risk_difference_lower_above_zero": risk["lower"] is not None
                and float(risk["lower"]) > 0.0,
                "crossover_at_least_0_05": crossover["mean"] is not None
                and float(crossover["mean"]) >= 0.05,
                "crossover_lower_above_zero": crossover["lower"] is not None
                and float(crossover["lower"]) > 0.0,
                "log_loss_gain_at_least_0_02": logloss["mean"] is not None
                and float(logloss["mean"]) >= 0.02,
                "log_loss_gain_lower_above_zero": logloss["lower"] is not None
                and float(logloss["lower"]) > 0.0,
                "split_half_reliability_at_least_0_80": reliability is not None
                and reliability >= 0.80,
                "carrier_ablation_zero_path_identity": bool(path_identity["equal"]),
                "beats_write_disabled_inert_shuffle_and_full_ablation": bool(controls)
                and all(
                    value["risk_difference"]["lower"] is not None
                    and float(value["risk_difference"]["lower"]) > 0.0
                    for value in controls.values()
                ),
                "ablation_dose_response_monotonic": monotonic,
                "rescue_restores_at_least_0_70": rescue_fraction is not None
                and rescue_fraction >= 0.70,
                "one_uncued_generation_risk_lower_above_zero": generation_one[
                    "risk_difference"
                ]["lower"]
                is not None
                and float(generation_one["risk_difference"]["lower"]) > 0.0,
                "one_uncued_generation_crossover_lower_above_zero": generation_one[
                    "crossover"
                ]["lower"]
                is not None
                and float(generation_one["crossover"]["lower"]) > 0.0,
            }
            gates[model] = {
                "engine": engine,
                "candidate": candidate.name,
                "mechanism": candidate.mechanism,
                "primary": primary,
                "controls": controls,
                "generation_one": generation_one,
                "split_half_reliability": reliability,
                "arm_rates": rates,
                "ablation_monotonic": monotonic,
                "rescue_fraction": rescue_fraction,
                "localization_only": {
                    "targeted_25": rates.get("ablation_25"),
                    "random_25": rates.get("random_ablation_25"),
                    "targeted_50": rates.get("ablation_50"),
                    "random_50": rates.get("random_ablation_50"),
                    "used_in_general_gate": False,
                },
                "criteria": criteria,
                "passed": all(criteria.values()),
                "source_values": {
                    name: values for name, values in raw.items() if name != "sources"
                },
            }
    return {
        "format": CARRIER_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "exploratory": spec.exploratory,
        "record_count": record_count,
        "unique_future_ids": len(future_ids),
        "carrier_gates": gates,
        "carrier_ablation_zero_path_identity": path_identity,
    }


def select_carrier_candidates(
    analysis: dict[str, Any], maximum_per_engine: int
) -> dict[str, tuple[str, ...]]:
    """Rank candidates without ever pooling Boolean and Wagner sources."""

    result: dict[str, tuple[str, ...]] = {}
    for engine in ("boolean", "wagner"):
        candidates = [
            gate
            for gate in analysis["carrier_gates"].values()
            if gate["engine"] == engine
            and gate["primary"]["risk_difference"]["mean"] is not None
            and float(gate["primary"]["risk_difference"]["mean"]) >= 0.02
            and gate["primary"]["crossover"]["mean"] is not None
            and float(gate["primary"]["crossover"]["mean"]) > 0.0
        ]
        candidates.sort(
            key=lambda gate: (
                -float(gate["primary"]["risk_difference"]["mean"]),
                -float(gate["primary"]["crossover"]["mean"]),
                gate["candidate"],
            )
        )
        result[engine] = tuple(
            gate["candidate"] for gate in candidates[:maximum_per_engine]
        )
    return result


def _valid_shard(
    shard: Path,
    manifest_path: Path,
    digest: str,
    source_id: str,
    expected: int,
) -> tuple[bool, int]:
    if not shard.is_file() or not manifest_path.is_file():
        return False, 0
    try:
        manifest = read_json(manifest_path)
        valid = (
            manifest.get("protocol_digest") == digest
            and manifest.get("source_id") == source_id
            and manifest.get("sha256") == sha256_file(shard)
            and int(manifest.get("record_count", -1)) == expected
        )
        return valid, expected if valid else 0
    except (OSError, TypeError, ValueError, KeyError):
        return False, 0


def run_carrier_study(
    spec: CarrierStudyV2Spec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("v2 carrier study requires 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_carrier_study(destination)
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
        "format": CARRIER_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing v2 carrier registration differs")
    else:
        _atomic_json(registration_path, registration)
    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        registry = read_json(registry_path)
    else:
        registry = build_carrier_registry(spec, progress)
        _atomic_json(registry_path, registry)
    expected = expected_carrier_futures(spec)
    shards = destination / "shards"
    shards.mkdir(exist_ok=True)
    completed: set[str] = set()
    completed_records = 0
    for source in registry["sources"]:
        source_id = str(source["source_id"])
        source_expected = expected_carrier_source_futures(spec, str(source["engine"]))
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
    missing = [source for source in registry["sources"] if source["source_id"] not in completed]
    for source, records in iter_carrier_source_results(
        {**registry, "sources": missing}, spec, workers, progress
    ):
        source_id = str(source["source_id"])
        source_expected = expected_carrier_source_futures(spec, str(source["engine"]))
        temporary = shards / f".{source_id}.jsonl.gz.tmp"
        count = write_jsonl_gz(temporary, records)
        if count != source_expected:
            raise RuntimeError(f"v2 carrier source produced {count}; expected {source_expected}")
        shard = shards / f"{source_id}.jsonl.gz"
        temporary.replace(shard)
        _atomic_json(
            shards / f"{source_id}.manifest.json",
            {
                "format": "gre-plastic-heredity-v2-carrier-shard-v1",
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
                "format": "gre-plastic-heredity-v2-carrier-progress-v1",
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
        raise RuntimeError(f"v2 carrier study produced {count}; expected {expected}")
    analysis = analyze_carrier_path(futures, spec)
    _atomic_json(destination / "analysis.json", analysis)
    manifest = {
        "format": "gre-plastic-heredity-v2-carrier-manifest-v1",
        "protocol_digest": digest,
        "raw_format": CARRIER_RAW_FORMAT,
        "record_count": count,
        "expected_record_count": expected,
        "source_rulebooks": len(registry["sources"]),
        "workers": workers,
        "elapsed_seconds": prior_elapsed + time.monotonic() - started,
        "runtime": runtime_manifest(),
        "source_hashes": source_hashes(),
    }
    _atomic_json(destination / "manifest.json", manifest)
    lines = [
        f"# Plastic Heredity v2 carriers: {spec.phase}",
        "",
        "> Exploratory." if spec.exploratory else "> Untouched confirmation.",
        "",
        f"- Futures: {count:,}",
        f"- Engine-neutral candidates: {len(spec.carriers)}",
        "",
        "## Causal carrier gates",
        "",
    ]
    for gate in analysis["carrier_gates"].values():
        lines.append(
            f"- `{gate['engine']}` / `{gate['candidate']}`: "
            f"{'PASS' if gate['passed'] else 'fail'}"
        )
    (destination / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_checksums(destination)
    verify_carrier_study(destination)
    return destination


def verify_carrier_study(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != CARRIER_REGISTRATION_FORMAT:
        raise ValueError("v2 carrier registration format mismatch")
    spec = CarrierStudyV2Spec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("v2 carrier protocol digest mismatch")
    expected = expected_carrier_futures(spec)
    count = sum(1 for _ in read_jsonl_gz(directory / "futures.jsonl.gz"))
    if count != expected or count != int(manifest["record_count"]):
        raise ValueError("v2 carrier record count mismatch")
    return {
        "verified": True,
        "files": len(checksums),
        "records": count,
        "protocol_digest": digest,
    }


def replay_carrier_future(directory: Path, future_id: str) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = CarrierStudyV2Spec.from_dict(registration["protocol"])
    archived = next(
        (record for record in read_jsonl_gz(directory / "futures.jsonl.gz") if record["future_id"] == future_id),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown v2 carrier future: {future_id}")
    registry = read_json(directory / "rulebooks.json")
    source = next(value for value in registry["sources"] if value["source_id"] == archived["source_id"])
    candidate = next(value for value in spec.carriers if value.name == archived["mark_setting"])
    narrowed = replace(
        spec,
        carriers=(candidate,),
        arms=(str(archived["carrier"]),),
        descendant_ages=(int(archived["washout_age"]),),
        challenges=(str(archived["challenge"]),),
    )
    replayed = next(
        record
        for record in simulate_carrier_source(source, narrowed.to_dict())
        if record["future_id"] == future_id
    )
    fields = ("form_destination", "correct_hold8", "returned", "trace_digest")
    return {
        "future_id": future_id,
        "matches": all(archived[field] == replayed[field] for field in fields),
        "archived": {field: archived[field] for field in fields},
        "replayed": {field: replayed[field] for field in fields},
    }
