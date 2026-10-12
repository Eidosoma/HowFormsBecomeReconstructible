"""Registry construction and bounded-memory execution for mechanism phases."""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from .artifacts import read_json
from .boolean import BooleanRulebook
from .engines import Rulebook, rulebook_from_dict
from .landscape import Landscape, normalized_hamming, permute_state
from .mechanism_config import MechanismCondition, MechanismSpec
from .mechanism_dynamics import MechanismRulebook
from .mechanism_endpoints import MechanismSummary, simulate_mechanism_ensemble
from .rng import digest_parts, rng_for
from .study import verify_run
from .wagner import WagnerRulebook


def _derangement(size: int, rng: np.random.Generator) -> np.ndarray:
    if size < 2:
        raise ValueError("derangements need at least two genes")
    for _ in range(10_000):
        value = rng.permutation(size)
        if np.all(value != np.arange(size)):
            return value.astype(np.int64)
    raise RuntimeError("could not generate a node derangement")


def _default_variant(engine: str) -> str:
    return "boolean_sync" if engine == "boolean" else "wagner_sequential"


def _variant_landscape(rulebook: Rulebook, variant: str) -> Landscape:
    return MechanismRulebook(rulebook, variant).landscape()


def _eligible(landscape: Landscape, minimum_basin_fraction: float = 0.05) -> bool:
    eligible_points = [
        index
        for index in landscape.point_indices
        if float(landscape.basin_fractions[index]) >= minimum_basin_fraction
    ]
    return len(eligible_points) >= 2


def _choose_launches(
    landscape: Landscape, genes: int, count: int
) -> list[dict[str, int]]:
    points = sorted(
        landscape.point_indices,
        key=lambda index: (-int(landscape.basin_sizes[index]), index),
    )
    if len(points) < 2:
        raise ValueError("mechanism source needs two point attractors")
    selected: list[tuple[int, int]] = []
    used: set[int] = set()

    def add(state: int, old_state: int) -> None:
        if state not in used and len(selected) < count:
            selected.append((int(state), int(old_state)))
            used.add(int(state))

    primary = points[:2]
    for index in primary:
        state = int(landscape.attractors[index].states[0])
        add(state, state)
    for index in primary:
        target = int(landscape.attractors[index].states[0])
        basin = [
            int(state)
            for state in np.flatnonzero(landscape.attractor_index == index)
            if int(state) != target
        ]
        if basin:
            add(
                min(
                    basin,
                    key=lambda state: (
                        normalized_hamming(state, target, genes),
                        state,
                    ),
                ),
                target,
            )
    largest = primary[0]
    target = int(landscape.attractors[largest].states[0])
    basin = [
        int(state)
        for state in np.flatnonzero(landscape.attractor_index == largest)
    ]
    for state in sorted(
        basin,
        key=lambda state: (-normalized_hamming(state, target, genes), state),
    ):
        add(state, target)
    for state in range(landscape.state_count):
        index = int(landscape.attractor_index[state])
        attractor = landscape.attractors[index]
        if attractor.kind == "point":
            add(state, int(attractor.states[0]))
    if len(selected) != count:
        raise RuntimeError(f"could choose only {len(selected)}/{count} launch states")
    return [
        {"state_id": index, "launch_state": state, "old_state": old}
        for index, (state, old) in enumerate(selected)
    ]


def _serialize_bundle(
    source_set: str,
    index: int,
    rulebook: Rulebook,
    spec: MechanismSpec,
    origin: str,
) -> dict[str, Any]:
    source_id = f"{source_set}.{index:04d}"
    default_variant = _default_variant("boolean" if isinstance(rulebook, BooleanRulebook) else "wagner")
    landscape = _variant_landscape(rulebook, default_variant)
    rng = rng_for(spec.master_seed, "mechanism-bundle", source_id)
    permutation = _derangement(rulebook.genes, rng)
    permuted = rulebook.permute(permutation)
    target = int(rng.integers(0, rulebook.state_count))
    if isinstance(rulebook, BooleanRulebook):
        single: Rulebook = BooleanRulebook.constant(rulebook.genes, target)
        engine = "boolean"
    else:
        single = WagnerRulebook.constant(rulebook.genes, target)
        engine = "wagner"
    launches = _choose_launches(
        landscape, rulebook.genes, spec.launch_states_per_rulebook
    )
    for launch in launches:
        launch["joint_launch_state"] = permute_state(
            int(launch["launch_state"]), permutation, rulebook.genes
        )
        launch["joint_old_state"] = permute_state(
            int(launch["old_state"]), permutation, rulebook.genes
        )
    return {
        "source_set": source_set,
        "source_id": source_id,
        "engine": engine,
        "genes": rulebook.genes,
        "origin": origin,
        "source": rulebook.to_dict(),
        "permuted": permuted.to_dict(),
        "single": single.to_dict(),
        "single_target": target,
        "permutation": permutation.tolist(),
        "launches": launches,
        "default_landscape": landscape.to_dict(),
    }


def _import_parent_sources(
    source_set: Any,
    spec: MechanismSpec,
    parent_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    parent_engine = source_set.parent_engine or source_set.engine
    candidates = [
        bundle
        for bundle in parent_registry["sources"]
        if bundle["engine"] == parent_engine
    ]
    if len(candidates) < source_set.count:
        raise ValueError(
            f"parent contains only {len(candidates)}/{source_set.count} "
            f"{parent_engine} sources"
        )
    bundles: list[dict[str, Any]] = []
    for index, parent in enumerate(candidates[: source_set.count]):
        rulebook = rulebook_from_dict(parent["source"])
        if rulebook.genes != source_set.genes:
            raise ValueError("parent source gene count does not match mechanism protocol")
        # Copy the exact Stage A definitions. Avoid rebuilding a landscape that
        # is already checksummed in the sealed parent run.
        bundle = {
            "source_set": source_set.name,
            "source_id": f"{source_set.name}.{index:04d}",
            "engine": parent_engine,
            "genes": rulebook.genes,
            "origin": f"parent:{parent['source_id']}",
            "parent_source_id": parent["source_id"],
            "source": parent["source"],
            "permuted": parent["permuted"],
            "single": parent["single"],
            "single_target": parent["single_target"],
            "permutation": parent["permutation"],
            "launches": [
                dict(value)
                for value in parent["launches"][: spec.launch_states_per_rulebook]
            ],
            "default_landscape": parent["source_landscape"],
        }
        if len(bundle["launches"]) != spec.launch_states_per_rulebook:
            raise ValueError("parent run has too few launch states")
        bundles.append(bundle)
    return bundles


def _random_rulebook(engine: str, genes: int, rng: np.random.Generator) -> Rulebook:
    if engine == "boolean":
        return BooleanRulebook.random(genes, rng)
    if engine == "wagner":
        return WagnerRulebook.random(genes, rng)
    raise ValueError(engine)


def _sample_sources(source_set: Any, spec: MechanismSpec) -> tuple[list[dict[str, Any]], dict[str, int]]:
    bundles: list[dict[str, Any]] = []
    proposals = 0
    maximum = max(100_000, source_set.count * 10_000)
    while len(bundles) < source_set.count and proposals < maximum:
        rng = rng_for(
            spec.master_seed,
            "mechanism-source",
            source_set.name,
            proposals,
        )
        candidate = _random_rulebook(source_set.engine, source_set.genes, rng)
        proposals += 1
        variants = [_default_variant(source_set.engine)]
        if source_set.require_both_update_modes:
            variants = (
                ["boolean_sync", "boolean_sequential"]
                if source_set.engine == "boolean"
                else ["wagner_sequential", "wagner_synchronous"]
            )
        if not all(_eligible(_variant_landscape(candidate, variant)) for variant in variants):
            continue
        bundles.append(
            _serialize_bundle(
                source_set.name,
                len(bundles),
                candidate,
                spec,
                f"sampled-proposal:{proposals - 1}",
            )
        )
    if len(bundles) != source_set.count:
        raise RuntimeError(
            f"generated only {len(bundles)}/{source_set.count} sources for "
            f"{source_set.name} after {proposals} proposals"
        )
    return bundles, {"accepted": len(bundles), "proposals": proposals}


def _descriptor(bundle: dict[str, Any], variant: str) -> np.ndarray:
    rulebook = rulebook_from_dict(bundle["source"])
    landscape = _variant_landscape(rulebook, variant)
    point_count = len(landscape.point_indices)
    largest = float(np.max(landscape.basin_fractions))
    return np.asarray(
        [point_count / max(1, rulebook.state_count), landscape.basin_entropy, landscape.mean_transient / max(1, rulebook.state_count), largest],
        dtype=float,
    )


def _annotate_cross_engine_matches(registry: dict[str, Any]) -> None:
    """Pair sampled Boolean/Wagner sets at each size without dropping sources."""

    by_genes: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for bundle in registry["sources"]:
        if not str(bundle["origin"]).startswith("sampled"):
            continue
        by_genes.setdefault(int(bundle["genes"]), {}).setdefault(
            str(bundle["engine"]), []
        ).append(bundle)
    for genes, engines in by_genes.items():
        left = engines.get("boolean", [])
        right = engines.get("wagner", [])
        if not left or len(left) != len(right):
            continue
        left_values = np.asarray([_descriptor(item, "boolean_sync") for item in left])
        right_values = np.asarray([_descriptor(item, "wagner_sequential") for item in right])
        scales = np.std(np.vstack((left_values, right_values)), axis=0)
        scales[scales == 0.0] = 1.0
        costs = np.linalg.norm(
            (left_values[:, None, :] - right_values[None, :, :]) / scales,
            axis=2,
        )
        rows, columns = linear_sum_assignment(costs)
        for row, column in zip(rows.tolist(), columns.tolist()):
            left[row]["cross_engine_partner"] = right[column]["source_id"]
            left[row]["cross_engine_match_cost"] = float(costs[row, column])
            right[column]["cross_engine_partner"] = left[row]["source_id"]
            right[column]["cross_engine_match_cost"] = float(costs[row, column])
        registry.setdefault("matching", {})[f"N={genes}"] = {
            "pairs": len(rows),
            "mean_cost": float(np.mean(costs[rows, columns])),
            "maximum_cost": float(np.max(costs[rows, columns])),
        }


def build_mechanism_registry(
    spec: MechanismSpec,
    parent_run: Path | None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    spec.validate()
    sources: list[dict[str, Any]] = []
    generation: dict[str, Any] = {}
    parent_registry: dict[str, Any] | None = None
    if any(source.origin == "parent" for source in spec.source_sets):
        if parent_run is None:
            raise ValueError("parent source sets require --parent-run")
        verification = verify_run(parent_run)
        if (
            spec.parent_protocol_digest is not None
            and verification["protocol_digest"] != spec.parent_protocol_digest
        ):
            raise ValueError(
                "parent run protocol digest does not match mechanism contract"
            )
        parent_registry = read_json(parent_run / "rulebooks.json")
    for source_set in spec.source_sets:
        if progress is not None:
            progress(f"preparing mechanism source set {source_set.name}")
        if source_set.origin == "parent":
            if parent_registry is None:  # pragma: no cover - guarded above.
                raise RuntimeError("validated parent registry is unavailable")
            values = _import_parent_sources(source_set, spec, parent_registry)
            stats = {"accepted": len(values), "proposals": 0}
        else:
            values, stats = _sample_sources(source_set, spec)
        sources.extend(values)
        generation[source_set.name] = stats
    registry = {
        "format": "gre-mechanism-rulebook-registry-v1",
        "cohort_id": spec.cohort_id,
        "protocol_format": spec.protocol_format,
        "sources": sources,
        "generation": generation,
        "matching": {},
    }
    _annotate_cross_engine_matches(registry)
    return registry


def _arm_values(
    bundle: dict[str, Any],
    launch: dict[str, Any],
    condition: MechanismCondition,
    arm: str,
) -> tuple[MechanismRulebook, int, int, int]:
    source = rulebook_from_dict(bundle["source"])
    permuted = rulebook_from_dict(bundle["permuted"])
    single = rulebook_from_dict(bundle["single"])
    compiled_mode = condition.compiled_update_mode
    if arm == "natural":
        active = MechanismRulebook(source, condition.variant, compiled_mode)
        return active, int(launch["launch_state"]), int(launch["old_state"]), int(launch["old_state"])
    if arm == "joint_isomorphic":
        active = MechanismRulebook(permuted, condition.variant, compiled_mode)
        return active, int(launch["joint_launch_state"]), int(launch["joint_old_state"]), int(launch["joint_old_state"])
    if arm == "acute_mismatch":
        active = MechanismRulebook(permuted, condition.variant, compiled_mode)
        return active, int(launch["launch_state"]), int(launch["old_state"]), int(launch["old_state"])
    if arm == "target_aligned_own_anchor":
        active = MechanismRulebook(permuted, condition.variant, compiled_mode)
        developed = active.develop(int(launch["launch_state"]), None, 100).final_state
        return active, int(developed), int(developed), int(developed)
    if arm == "single_attractor":
        active = MechanismRulebook(single, condition.variant, compiled_mode)
        return active, int(launch["launch_state"]), int(launch["old_state"]), int(launch["old_state"])
    raise ValueError(arm)


def _summary_dict(summary: MechanismSummary) -> dict[str, Any]:
    return {
        "frozen_destination": summary.frozen_destination,
        "point_state_destination": summary.point_state_destination,
        "signature_destination": summary.signature_destination,
        "competing_outcome": summary.competing_outcome,
        "active_capture": summary.active_capture,
        "stable_point_capture": summary.stable_point_capture,
        "stable_signature_capture": summary.stable_signature_capture,
        "strict_library": summary.strict_library,
        "strict_state": summary.strict_state,
        "strict_library_by_run": list(summary.strict_library_by_run),
        "strict_state_by_run": list(summary.strict_state_by_run),
        "max_library_run": summary.max_library_run,
        "max_point_state_run": summary.max_point_state_run,
        "max_signature_run": summary.max_signature_run,
        "first_break": summary.first_break,
        "old_return": summary.old_return,
        "point_cycles": summary.point_cycles,
        "cycle_cycles": summary.cycle_cycles,
        "nonconvergent_cycles": summary.nonconvergent_cycles,
        "unique_adult_states": summary.unique_adult_states,
        "donor_reassignments": summary.donor_reassignments,
        "donor_fallbacks": summary.donor_fallbacks,
        "trace_digest": summary.trace_digest,
    }


def _cycle_streams(
    spec: MechanismSpec,
    bundle: dict[str, Any],
    launch: dict[str, Any],
    arm: str,
    future_indices: tuple[int, ...],
) -> tuple[tuple[tuple[np.random.Generator, np.random.Generator], ...], ...]:
    """Share random coordinates across variants, noise, carryover, and donor modes."""

    return tuple(
        tuple(
            (
                rng_for(
                    spec.master_seed,
                    "mechanism-future",
                    bundle["source_id"],
                    int(launch["state_id"]),
                    arm,
                    future_index,
                    cycle,
                    "carryover",
                ),
                rng_for(
                    spec.master_seed,
                    "mechanism-future",
                    bundle["source_id"],
                    int(launch["state_id"]),
                    arm,
                    future_index,
                    cycle,
                    "dynamics",
                ),
            )
            for cycle in range(spec.horizon)
        )
        for future_index in future_indices
    )


def simulate_mechanism_source(
    bundle: dict[str, Any], spec_value: dict[str, Any]
) -> list[dict[str, Any]]:
    spec = MechanismSpec.from_dict(spec_value)
    records: list[dict[str, Any]] = []
    conditions = [
        value for value in spec.conditions if value.source_set == bundle["source_set"]
    ]
    for condition in conditions:
        for launch in bundle["launches"]:
            for arm in condition.arms:
                active, base, previous, old = _arm_values(bundle, launch, condition, arm)
                landscape = active.landscape()
                for carryover in condition.carryover_values:
                    for gamma_variance in condition.gamma_variances:
                        for mode in condition.inheritance_modes:
                            half_size = condition.futures_per_cell // 2
                            for half_index, half in enumerate(("A", "B")):
                                start = half_index * half_size
                                indices = tuple(range(start, start + half_size))
                                streams = _cycle_streams(
                                    spec, bundle, launch, arm, indices
                                )
                                results = simulate_mechanism_ensemble(
                                    active,
                                    landscape,
                                    base,
                                    previous,
                                    old,
                                    float(carryover),
                                    spec.expression_flip_probability,
                                    spec.horizon,
                                    spec.stable_destination_run,
                                    spec.strict_run,
                                    spec.old_distinct_distance,
                                    mode,
                                    streams,
                                    float(gamma_variance),
                                    spec.wagner_max_sweeps,
                                )
                                for future_index, (summary, _) in zip(indices, results):
                                    future_id = digest_parts(
                                        spec.protocol_format,
                                        spec.cohort_id,
                                        condition.name,
                                        bundle["source_id"],
                                        int(launch["state_id"]),
                                        arm,
                                        float(carryover),
                                        float(gamma_variance),
                                        mode,
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
                                            "source_engine": bundle["engine"],
                                            "genes": int(bundle["genes"]),
                                            "variant": condition.variant,
                                            "compiled_update_mode": condition.compiled_update_mode,
                                            "state_id": int(launch["state_id"]),
                                            "arm": arm,
                                            "carryover": float(carryover),
                                            "gamma_variance": float(gamma_variance),
                                            "inheritance_mode": mode,
                                            "future_index": future_index,
                                            "half": half,
                                            **_summary_dict(summary),
                                        }
                                    )
    records.sort(
        key=lambda item: (
            item["condition"],
            item["state_id"],
            item["arm"],
            item["carryover"],
            item["gamma_variance"],
            item["inheritance_mode"],
            item["future_index"],
        )
    )
    return records


def iter_mechanism_records(
    registry: dict[str, Any],
    spec: MechanismSpec,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield source-ordered results with at most two work windows in memory."""

    if workers < 1:
        raise ValueError("workers must be positive")
    sources = sorted(registry["sources"], key=lambda item: item["source_id"])
    expected_records = expected_registry_futures(spec, registry)
    completed_records = 0
    if workers == 1:
        for index, source in enumerate(sources, start=1):
            records = simulate_mechanism_source(source, spec.to_dict())
            completed_records += len(records)
            yield from records
            if progress is not None:
                progress(
                    f"simulated mechanism source {index}/{len(sources)} "
                    f"({completed_records:,}/{expected_records:,} futures)"
                )
        return
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        pending: dict[int, concurrent.futures.Future[list[dict[str, Any]]]] = {}
        next_submit = 0
        window = max(workers, workers * 2)
        while next_submit < min(window, len(sources)):
            pending[next_submit] = executor.submit(
                simulate_mechanism_source, sources[next_submit], spec.to_dict()
            )
            next_submit += 1
        for index in range(len(sources)):
            records = pending.pop(index).result()
            completed_records += len(records)
            yield from records
            if progress is not None:
                progress(
                    f"simulated mechanism source {index + 1}/{len(sources)} "
                    f"({completed_records:,}/{expected_records:,} futures)"
                )
            if next_submit < len(sources):
                pending[next_submit] = executor.submit(
                    simulate_mechanism_source, sources[next_submit], spec.to_dict()
                )
                next_submit += 1


def expected_registry_futures(spec: MechanismSpec, registry: dict[str, Any]) -> int:
    counts: dict[str, int] = {}
    for source in registry["sources"]:
        counts[source["source_set"]] = counts.get(source["source_set"], 0) + 1
    total = 0
    for condition in spec.conditions:
        total += (
            counts.get(condition.source_set, 0)
            * spec.launch_states_per_rulebook
            * len(condition.arms)
            * len(condition.carryover_values)
            * len(condition.inheritance_modes)
            * len(condition.gamma_variances)
            * condition.futures_per_cell
        )
    return total
