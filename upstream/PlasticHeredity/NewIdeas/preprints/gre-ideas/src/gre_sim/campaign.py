"""Rulebook construction, mismatch arms, and deterministic campaign orchestration."""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .boolean import BooleanRulebook
from .config import StudySpec
from .endpoints import simulate_future, simulate_future_ensemble
from .engines import Rulebook, rulebook_from_dict
from .evolution import (
    EvolutionExhausted,
    EvolutionResult,
    eligible_landscape,
    evolve_population,
    generate_founder_and_contexts,
)
from .landscape import Landscape, normalized_hamming, permute_state
from .rng import digest_parts, rng_for
from .wagner import WagnerRulebook

try:  # scipy is required by the package, but keep registry inspection graceful.
    from scipy.optimize import linear_sum_assignment
except Exception:  # pragma: no cover
    linear_sum_assignment = None


@dataclass(frozen=True)
class TargetCandidate:
    rulebook: Rulebook
    origin_id: str


def _genes(spec: StudySpec, engine: str) -> int:
    if engine == "boolean":
        return spec.boolean.genes
    if engine == "wagner":
        return spec.wagner.genes
    raise ValueError(engine)


def _random_rulebook(engine: str, genes: int, rng: np.random.Generator) -> Rulebook:
    if engine == "boolean":
        return BooleanRulebook.random(genes, rng)
    if engine == "wagner":
        return WagnerRulebook.random(genes, rng)
    raise ValueError(engine)


def _is_eligible(rulebook: Rulebook, spec: StudySpec) -> bool:
    return eligible_landscape(
        rulebook.landscape(),
        spec.minimum_point_attractors,
        spec.minimum_basin_fraction,
    )


def generate_conditioned_rulebooks(
    engine: str,
    count: int,
    spec: StudySpec,
    domain: str,
) -> tuple[list[Rulebook], dict[str, int]]:
    result: list[Rulebook] = []
    seen: set[str] = set()
    proposals = 0
    while len(result) < count and proposals < spec.maximum_rulebook_proposals:
        rng = rng_for(spec.master_seed, "rulebook", engine, domain, proposals)
        candidate = _random_rulebook(engine, _genes(spec, engine), rng)
        proposals += 1
        if candidate.uid in seen or not _is_eligible(candidate, spec):
            continue
        seen.add(candidate.uid)
        result.append(candidate)
    if len(result) != count:
        raise RuntimeError(
            f"generated only {len(result)}/{count} eligible {engine} rulebooks "
            f"after {proposals} proposals"
        )
    return result, {"proposals": proposals, "accepted": len(result)}


def _evolve_one(
    engine: str,
    population_id: str,
    spec: StudySpec,
) -> EvolutionResult:
    genes = _genes(spec, engine)
    founder, contexts = generate_founder_and_contexts(
        engine,
        genes,
        spec.evolution.target_min_distance,
        max(2, spec.minimum_point_attractors),
        spec.minimum_basin_fraction,
        spec.master_seed,
        population_id,
        spec.maximum_rulebook_proposals,
    )
    return evolve_population(
        engine,
        genes,
        contexts,
        spec.evolution,
        spec.master_seed,
        population_id,
        spec.boolean.expression_flip_probability,
        spec.wagner.expression_flip_probability,
        spec.wagner.gamma_variance,
        spec.wagner.max_sweeps,
        founder=founder,
        eligibility=lambda candidate: _is_eligible(candidate, spec),
    )


def _evolve_one_safe(
    engine: str, population_id: str, spec: StudySpec
) -> tuple[str, EvolutionResult | None, str | None]:
    try:
        return population_id, _evolve_one(engine, population_id, spec), None
    except EvolutionExhausted as error:
        return population_id, None, str(error)


def generate_evolved_rulebooks(
    engine: str,
    count: int,
    spec: StudySpec,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> tuple[list[Rulebook], list[TargetCandidate], list[dict[str, Any]], dict[str, int]]:
    sources: list[Rulebook] = []
    targets: list[TargetCandidate] = []
    metadata: list[dict[str, Any]] = []
    failed = 0
    attempts = 0
    successful_populations = 0
    target_goal = count * spec.target_pool_multiplier
    minimum_origins = 2 if count == 1 else count
    executor: concurrent.futures.ProcessPoolExecutor | None = None
    if workers > 1:
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=workers)
    try:
        while (
            len(sources) < count
            or len(targets) < target_goal
            or successful_populations < minimum_origins
        ) and attempts < spec.evolution.max_population_attempts:
            batch_size = min(
                workers,
                spec.evolution.max_population_attempts - attempts,
            )
            population_ids = [
                f"{engine}-population-{index:04d}"
                for index in range(attempts, attempts + batch_size)
            ]
            attempts += batch_size
            if executor is None:
                results = [
                    _evolve_one_safe(engine, population_id, spec)
                    for population_id in population_ids
                ]
            else:
                futures = {
                    executor.submit(
                        _evolve_one_safe, engine, population_id, spec
                    ): population_id
                    for population_id in population_ids
                }
                completed: dict[
                    str, tuple[str, EvolutionResult | None, str | None]
                ] = {}
                for completed_count, future in enumerate(
                    concurrent.futures.as_completed(futures), start=1
                ):
                    population_id = futures[future]
                    completed[population_id] = future.result()
                    if progress is not None:
                        progress(
                            f"evolution {engine} batch: {completed_count}/{batch_size} "
                            "populations finished"
                        )
                # Commit in semantic population-id order, not completion order.
                results = [completed[population_id] for population_id in population_ids]
            for population_id, result, error in results:
                if result is None:
                    failed += 1
                    metadata.append(
                        {
                            "population_id": population_id,
                            "status": "ineligible",
                            "reason": error,
                        }
                    )
                    continue
                successful_populations += 1
                if len(sources) < count:
                    sources.append(result.selected)
                for candidate in result.eligible_pool:
                    targets.append(TargetCandidate(candidate, population_id))
                metadata.append(
                    {
                        "population_id": population_id,
                        "status": "eligible",
                        "source_uid": result.selected.uid,
                        **result.metadata(),
                    }
                )
            if progress is not None:
                progress(
                    f"evolution {engine}: {len(sources)}/{count} sources, "
                    f"{len(targets)}/{target_goal} target candidates, "
                    f"{attempts}/{spec.evolution.max_population_attempts} attempts"
                )
    finally:
        if executor is not None:
            executor.shutdown(wait=True)
    if len(sources) < count:
        raise RuntimeError(f"only {len(sources)}/{count} evolved {engine} sources were eligible")
    if len(targets) < count:
        raise RuntimeError(
            f"only {len(targets)} evolved {engine} target candidates were available"
        )
    return sources, targets, metadata, {
        "population_attempts": attempts,
        "failed_populations": failed,
        "sources": len(sources),
        "target_candidates": len(targets),
    }


def _point_count(landscape: Landscape) -> int:
    return len(landscape.point_indices)


def _match_cost(source: Landscape, target: Landscape) -> float:
    return (
        5.0 * abs(_point_count(source) - _point_count(target))
        + 2.0 * abs(source.basin_entropy - target.basin_entropy)
        + abs(source.mean_transient - target.mean_transient)
        / max(source.state_count, 1)
    )


def match_independent_targets(
    sources: list[Rulebook],
    source_origins: list[str],
    targets: list[TargetCandidate],
) -> tuple[list[TargetCandidate], list[float]]:
    if len(targets) < len(sources):
        raise ValueError("target pool is smaller than the source cohort")
    source_landscapes = [source.landscape() for source in sources]
    target_landscapes = [target.rulebook.landscape() for target in targets]
    costs = np.empty((len(sources), len(targets)), dtype=float)
    for source_index, (source, source_origin) in enumerate(zip(sources, source_origins)):
        for target_index, target in enumerate(targets):
            invalid = target.origin_id == source_origin or target.rulebook.uid == source.uid
            costs[source_index, target_index] = (
                1e12
                if invalid
                else _match_cost(source_landscapes[source_index], target_landscapes[target_index])
            )
    if linear_sum_assignment is not None:
        rows, columns = linear_sum_assignment(costs)
        assignment = {int(row): int(column) for row, column in zip(rows, columns)}
    else:  # pragma: no cover
        assignment = {}
        unused = set(range(len(targets)))
        for row in range(len(sources)):
            column = min(unused, key=lambda candidate: costs[row, candidate])
            assignment[row] = column
            unused.remove(column)
    selected: list[TargetCandidate] = []
    selected_costs: list[float] = []
    for row in range(len(sources)):
        column = assignment[row]
        if costs[row, column] >= 1e11:
            raise RuntimeError("could not form independent source-target matches")
        selected.append(targets[column])
        selected_costs.append(float(costs[row, column]))
    return selected, selected_costs


def _derangement(genes: int, rng: np.random.Generator) -> np.ndarray:
    identity = np.arange(genes, dtype=np.int64)
    for _ in range(1_000):
        permutation = rng.permutation(genes).astype(np.int64)
        if np.all(permutation != identity):
            return permutation
    # A cyclic shift is a deterministic derangement for every genes > 1.
    return np.roll(identity, 1)


def choose_launch_states(
    landscape: Landscape,
    genes: int,
    count: int,
    minimum_basin_fraction: float,
) -> list[dict[str, int]]:
    points = [
        index
        for index in landscape.point_indices
        if landscape.basin_fractions[index] >= minimum_basin_fraction
    ]
    if not points:
        raise ValueError("landscape has no eligible point attractors")
    points.sort(key=lambda index: (-int(landscape.basin_sizes[index]), index))
    primary = points[: max(1, min(2, len(points)))]
    selected: list[tuple[int, int]] = []
    used: set[int] = set()

    def add(state: int, attractor_state: int) -> None:
        if state not in used and len(selected) < count:
            selected.append((state, attractor_state))
            used.add(state)

    for attractor_index in primary:
        target = landscape.attractors[attractor_index].states[0]
        add(target, target)
    for attractor_index in primary:
        target = landscape.attractors[attractor_index].states[0]
        basin = [
            int(state)
            for state in np.flatnonzero(landscape.attractor_index == attractor_index)
            if int(state) != target
        ]
        if basin:
            nearest = min(
                basin, key=lambda state: (normalized_hamming(state, target, genes), state)
            )
            add(nearest, target)
    largest_index = primary[0]
    largest_target = landscape.attractors[largest_index].states[0]
    largest_basin = [
        int(state)
        for state in np.flatnonzero(landscape.attractor_index == largest_index)
    ]
    for state in sorted(
        largest_basin,
        key=lambda value: (-normalized_hamming(value, largest_target, genes), value),
    ):
        add(state, largest_target)
    for state in range(landscape.state_count):
        attractor_index = int(landscape.attractor_index[state])
        attractor = landscape.attractors[attractor_index]
        if attractor.kind == "point":
            add(state, attractor.states[0])
    if len(selected) < count:
        raise RuntimeError(f"could choose only {len(selected)}/{count} unique launch states")
    return [
        {"state_id": index, "launch_state": state, "old_state": old_state}
        for index, (state, old_state) in enumerate(selected)
    ]


def _developed_state(rulebook: Rulebook, initial_state: int) -> tuple[int, str]:
    if isinstance(rulebook, BooleanRulebook):
        result = rulebook.develop(initial_state)
    else:
        assert isinstance(rulebook, WagnerRulebook)
        result = rulebook.develop(initial_state, None, 100)
    return result.final_state, result.status


def build_source_bundle(
    engine: str,
    cohort: str,
    index: int,
    source: Rulebook,
    independent: TargetCandidate,
    independent_cost: float,
    source_origin: str,
    spec: StudySpec,
) -> dict[str, Any]:
    source_id = f"{engine}.{cohort}.{index:04d}"
    landscape = source.landscape()
    rng = rng_for(spec.master_seed, "bundle", source_id)
    permutation = _derangement(source.genes, rng)
    permuted = source.permute(permutation)
    single_target = int(rng.integers(0, source.state_count))
    if isinstance(source, BooleanRulebook):
        single = BooleanRulebook.constant(source.genes, single_target)
    else:
        single = WagnerRulebook.constant(source.genes, single_target)
    launches = choose_launch_states(
        landscape,
        source.genes,
        spec.launch_states_per_rulebook,
        spec.minimum_basin_fraction,
    )
    for launch in launches:
        launch_state = int(launch["launch_state"])
        old_state = int(launch["old_state"])
        launch["joint_launch_state"] = permute_state(
            launch_state, permutation, source.genes
        )
        launch["joint_old_state"] = permute_state(old_state, permutation, source.genes)
        developed_state, developed_status = _developed_state(permuted, launch_state)
        launch["developed_state"] = developed_state
        launch["developed_status"] = developed_status
    return {
        "source_id": source_id,
        "engine": engine,
        "cohort": cohort,
        "source_origin": source_origin,
        "source": source.to_dict(),
        "permuted": permuted.to_dict(),
        "independent": independent.rulebook.to_dict(),
        "independent_origin": independent.origin_id,
        "independent_match_cost": independent_cost,
        "single": single.to_dict(),
        "single_target": single_target,
        "permutation": permutation.tolist(),
        "launches": launches,
        "source_landscape": landscape.to_dict(),
    }


def build_registry(
    spec: StudySpec,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    spec.validate()
    if workers < 1:
        raise ValueError("workers must be positive")
    bundles: list[dict[str, Any]] = []
    generation: dict[str, Any] = {}
    evolution_metadata: dict[str, Any] = {}
    for engine in spec.engines:
        if "sampled" in spec.cohorts:
            if progress is not None:
                progress(f"preparing {engine} sampled rulebooks")
            sources, source_stats = generate_conditioned_rulebooks(
                engine, spec.sampled_rulebooks, spec, "sampled-source"
            )
            target_count = spec.sampled_rulebooks * spec.target_pool_multiplier
            target_rulebooks, target_stats = generate_conditioned_rulebooks(
                engine, target_count, spec, "sampled-target"
            )
            source_origins = [f"sampled-source-{index}" for index in range(len(sources))]
            candidates = [
                TargetCandidate(rulebook, f"sampled-target-{index}")
                for index, rulebook in enumerate(target_rulebooks)
            ]
            matched, costs = match_independent_targets(sources, source_origins, candidates)
            for index, source in enumerate(sources):
                bundles.append(
                    build_source_bundle(
                        engine,
                        "sampled",
                        index,
                        source,
                        matched[index],
                        costs[index],
                        source_origins[index],
                        spec,
                    )
                )
            generation[f"{engine}.sampled"] = {
                "sources": source_stats,
                "targets": target_stats,
                "matching_costs": costs,
            }
            if progress is not None:
                progress(f"prepared {engine} sampled cohort")

        if "evolved" in spec.cohorts and spec.evolution.enabled:
            if progress is not None:
                progress(f"preparing {engine} evolved populations")
            sources, candidates, metadata, stats = generate_evolved_rulebooks(
                engine, spec.evolved_rulebooks, spec, workers, progress
            )
            successful_origins = [
                str(item["population_id"])
                for item in metadata
                if item.get("status") == "eligible"
            ][: len(sources)]
            matched, costs = match_independent_targets(
                sources, successful_origins, candidates
            )
            for index, source in enumerate(sources):
                bundles.append(
                    build_source_bundle(
                        engine,
                        "evolved",
                        index,
                        source,
                        matched[index],
                        costs[index],
                        successful_origins[index],
                        spec,
                    )
                )
            generation[f"{engine}.evolved"] = {**stats, "matching_costs": costs}
            evolution_metadata[engine] = metadata
            if progress is not None:
                progress(f"prepared {engine} evolved cohort")

    return {
        "format": (
            "gre-rulebook-registry-v2-prototype"
            if spec.is_v2
            else "gre-rulebook-registry-v1"
        ),
        "protocol_format": spec.protocol_format,
        "cohort_id": spec.cohort_id,
        "sources": bundles,
        "generation": generation,
        "evolution": evolution_metadata,
    }


def _arm_values(
    bundle: dict[str, Any], launch: dict[str, int], arm: str
) -> tuple[Rulebook, int, int, int]:
    if arm == "natural":
        return (
            rulebook_from_dict(bundle["source"]),
            int(launch["launch_state"]),
            int(launch["old_state"]),
            int(launch["old_state"]),
        )
    if arm == "joint_isomorphic":
        return (
            rulebook_from_dict(bundle["permuted"]),
            int(launch["joint_launch_state"]),
            int(launch["joint_old_state"]),
            int(launch["joint_old_state"]),
        )
    if arm == "acute_mismatch":
        return (
            rulebook_from_dict(bundle["permuted"]),
            int(launch["launch_state"]),
            int(launch["old_state"]),
            int(launch["old_state"]),
        )
    if arm == "developed_under_target":
        developed = int(launch["developed_state"])
        return (
            rulebook_from_dict(bundle["permuted"]),
            developed,
            developed,
            int(launch["old_state"]),
        )
    if arm == "target_aligned_own_anchor":
        developed = int(launch["developed_state"])
        return (
            rulebook_from_dict(bundle["permuted"]),
            developed,
            developed,
            developed,
        )
    if arm == "independent_target":
        return (
            rulebook_from_dict(bundle["independent"]),
            int(launch["launch_state"]),
            int(launch["old_state"]),
            int(launch["old_state"]),
        )
    if arm == "single_attractor":
        return (
            rulebook_from_dict(bundle["single"]),
            int(launch["launch_state"]),
            int(launch["old_state"]),
            int(launch["old_state"]),
        )
    raise ValueError(f"unknown arm: {arm}")


def _future_streams(
    spec: StudySpec,
    bundle: dict[str, Any],
    state_id: int,
    arm: str,
    carryover: float,
    future_index: int,
) -> tuple[
    np.random.Generator,
    tuple[tuple[np.random.Generator, np.random.Generator], ...],
]:
    """Return mode-shared streams; v1 coordinates remain exactly unchanged."""

    coordinates = (
        bundle["engine"],
        bundle["cohort"],
        bundle["source_id"],
        state_id,
        arm,
        carryover,
        future_index,
    )
    fallback = rng_for(spec.master_seed, "future", *coordinates, "fallback")
    cycle_rngs = tuple(
        (
            rng_for(
                spec.master_seed,
                "future",
                *coordinates,
                cycle_index,
                "carryover",
            ),
            rng_for(
                spec.master_seed,
                "future",
                *coordinates,
                cycle_index,
                "dynamics",
            ),
        )
        for cycle_index in range(spec.horizon)
    )
    return fallback, cycle_rngs


def _future_id(
    spec: StudySpec,
    bundle: dict[str, Any],
    state_id: int,
    arm: str,
    carryover: float,
    future_index: int,
    inheritance_mode: str = "self",
) -> str:
    coordinates: tuple[Any, ...] = (
        spec.protocol_format,
        spec.cohort_id,
        bundle["source_id"],
        state_id,
        arm,
        carryover,
    )
    if spec.is_v2:
        coordinates = (*coordinates, inheritance_mode)
    return digest_parts(*coordinates, future_index)


def _summary_values(summary: Any) -> dict[str, Any]:
    return {
        "destination": summary.destination,
        "strict_event": summary.strict_event,
        "first_break": summary.first_break,
        "stable_destination_cycle": summary.stable_destination_cycle,
        "active_capture": summary.active_capture,
        "old_return": summary.old_return,
        "point_cycles": summary.point_cycles,
        "cycle_cycles": summary.cycle_cycles,
        "nonconvergent_cycles": summary.nonconvergent_cycles,
        "trace_digest": summary.trace_digest,
    }


def simulate_v2_cell_half(
    bundle: dict[str, Any],
    launch: dict[str, int],
    arm: str,
    carryover: float,
    inheritance_mode: str,
    half: str,
    spec: StudySpec,
) -> list[tuple[int, Any, tuple[Any, ...]]]:
    """Simulate one v2 frozen half as a synchronous inheritance ensemble."""

    if not spec.is_v2:
        raise ValueError("ensemble simulation requires a v2 protocol")
    if half not in {"A", "B"}:
        raise ValueError(f"unknown future half: {half}")
    half_size = spec.futures_per_cell // 2
    start = 0 if half == "A" else half_size
    indices = tuple(range(start, start + half_size))
    active, base_state, previous_state, old_state = _arm_values(bundle, launch, arm)
    streams = [
        _future_streams(
            spec,
            bundle,
            int(launch["state_id"]),
            arm,
            carryover,
            future_index,
        )
        for future_index in indices
    ]
    flip_probability = (
        spec.boolean.expression_flip_probability
        if bundle["engine"] == "boolean"
        else spec.wagner.expression_flip_probability
    )
    results = simulate_future_ensemble(
        active,
        active.landscape(),
        base_state,
        previous_state,
        old_state,
        carryover,
        flip_probability,
        spec.horizon,
        spec.stable_destination_run,
        spec.strict_run,
        spec.old_distinct_distance,
        inheritance_mode,
        tuple(value[0] for value in streams),
        tuple(value[1] for value in streams),
        spec.wagner.gamma_variance if bundle["engine"] == "wagner" else 0.0,
        spec.wagner.max_sweeps,
    )
    return [
        (future_index, summary, observations)
        for future_index, (summary, observations) in zip(indices, results)
    ]


def _simulate_source_bundle_v2(
    bundle: dict[str, Any], spec: StudySpec
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for launch in bundle["launches"]:
        state_id = int(launch["state_id"])
        for arm in spec.arms:
            for carryover in spec.carryover_values:
                for inheritance_mode in spec.inheritance_modes:
                    for half in ("A", "B"):
                        results = simulate_v2_cell_half(
                            bundle,
                            launch,
                            arm,
                            carryover,
                            inheritance_mode,
                            half,
                            spec,
                        )
                        for future_index, summary, _ in results:
                            records.append(
                                {
                                    "future_id": _future_id(
                                        spec,
                                        bundle,
                                        state_id,
                                        arm,
                                        carryover,
                                        future_index,
                                        inheritance_mode,
                                    ),
                                    "engine": bundle["engine"],
                                    "cohort": bundle["cohort"],
                                    "source_id": bundle["source_id"],
                                    "state_id": state_id,
                                    "arm": arm,
                                    "inheritance_mode": inheritance_mode,
                                    "carryover": carryover,
                                    "future_index": future_index,
                                    "half": half,
                                    **_summary_values(summary),
                                }
                            )
    return records


def simulate_source_bundle(bundle: dict[str, Any], spec_value: dict[str, Any]) -> list[dict[str, Any]]:
    spec = StudySpec.from_dict(spec_value)
    if spec.is_v2:
        return _simulate_source_bundle_v2(bundle, spec)
    records: list[dict[str, Any]] = []
    half_size = spec.futures_per_cell // 2
    for launch in bundle["launches"]:
        state_id = int(launch["state_id"])
        for arm in spec.arms:
            active, base_state, previous_state, old_state = _arm_values(bundle, launch, arm)
            landscape = active.landscape()
            flip_probability = (
                spec.boolean.expression_flip_probability
                if bundle["engine"] == "boolean"
                else spec.wagner.expression_flip_probability
            )
            for carryover in spec.carryover_values:
                for future_index in range(spec.futures_per_cell):
                    future_id = _future_id(
                        spec, bundle, state_id, arm, carryover, future_index
                    )
                    rng, cycle_rngs = _future_streams(
                        spec, bundle, state_id, arm, carryover, future_index
                    )
                    summary, _ = simulate_future(
                        active,
                        landscape,
                        base_state,
                        previous_state,
                        old_state,
                        carryover,
                        flip_probability,
                        spec.horizon,
                        spec.stable_destination_run,
                        spec.strict_run,
                        spec.old_distinct_distance,
                        rng,
                        spec.wagner.gamma_variance if bundle["engine"] == "wagner" else 0.0,
                        spec.wagner.max_sweeps,
                        cycle_rngs,
                    )
                    records.append(
                        {
                            "future_id": future_id,
                            "engine": bundle["engine"],
                            "cohort": bundle["cohort"],
                            "source_id": bundle["source_id"],
                            "state_id": state_id,
                            "arm": arm,
                            "carryover": carryover,
                            "future_index": future_index,
                            "half": "A" if future_index < half_size else "B",
                            **_summary_values(summary),
                        }
                    )
    return records


def run_registry(
    registry: dict[str, Any],
    spec: StudySpec,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    if workers < 1:
        raise ValueError("workers must be positive")
    records: list[dict[str, Any]] = []
    if workers == 1:
        for index, bundle in enumerate(registry["sources"], start=1):
            records.extend(simulate_source_bundle(bundle, spec.to_dict()))
            if progress is not None:
                progress(f"simulated source {index}/{len(registry['sources'])}")
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(simulate_source_bundle, bundle, spec.to_dict())
                for bundle in registry["sources"]
            ]
            for index, future in enumerate(
                concurrent.futures.as_completed(futures), start=1
            ):
                records.extend(future.result())
                if progress is not None:
                    progress(f"simulated source {index}/{len(futures)}")
    records.sort(
        key=lambda item: (
            item["engine"],
            item["cohort"],
            item["source_id"],
            item["state_id"],
            item["arm"],
            item.get("inheritance_mode", "self"),
            item["carryover"],
            item["future_index"],
        )
    )
    return records


def expected_future_count(spec: StudySpec, registry: dict[str, Any]) -> int:
    return (
        len(registry["sources"])
        * spec.launch_states_per_rulebook
        * len(spec.arms)
        * len(spec.carryover_values)
        * spec.futures_per_cell
        * len(spec.inheritance_modes)
    )
