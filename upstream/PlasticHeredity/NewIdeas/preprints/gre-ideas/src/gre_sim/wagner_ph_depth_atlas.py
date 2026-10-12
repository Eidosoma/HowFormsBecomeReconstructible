"""Causal single-edge atlas for the Wagner carrier interpreter."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .local_ph_dynamics import structural_mask
from .rng import rng_for
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import deserialize_genotype, serialize_genotype
from .wagner_ph_cooption_experiment import local_carrier, simulate_ecology_condition
from .wagner_ph_depth_config import (
    DEPTH_ATLAS_FORMAT,
    ATLAS_PERTURBATIONS,
    InterpreterDepthSpec,
)
from .wagner_ph_depth_mechanisms import Genotype, edge_features, perturb_edge
from .wagner_ph_robustness_campaign import verify_wagner_ph_robustness_campaign


ATLAS_HIGH_INTERVENTIONS = (
    "natural",
    "independent_history",
    "opposite_history",
    "zero",
    "reader_off",
    "renewal_off",
)


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _rates(condition: dict[str, Any], generation: int) -> dict[str, float]:
    checkpoint = condition["checkpoints"][str(generation)]
    return {
        "correct_rate": float(checkpoint["correct_rate"]),
        "functional_rate": float(checkpoint["functional_rate"]),
        "wrong_rate": float(checkpoint["wrong_rate"]),
    }


def atlas_effects(
    genotype: Genotype,
    task: dict[str, Any],
    kernel: CooptionSpec,
    spec: InterpreterDepthSpec,
    scope: str,
) -> dict[str, float]:
    """Measure the compact causal panel used for every atlas perturbation."""

    rulebook, carrier = genotype
    high = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            carrier,
            kernel,
            intervention,
            spec.predictive_persistence,
            0.0,
            spec.atlas_futures_per_history,
            spec.atlas_lineage_generations,
            (spec.atlas_lineage_generations,),
            scope,
            master_seed=spec.atlas_seed,
        )
        for intervention in ATLAS_HIGH_INTERVENTIONS
    }
    low = {
        intervention: simulate_ecology_condition(
            rulebook,
            task,
            carrier,
            kernel,
            intervention,
            0.0,
            0.0,
            spec.atlas_futures_per_history,
            spec.atlas_lineage_generations,
            (spec.atlas_lineage_generations,),
            scope,
            master_seed=spec.atlas_seed,
        )
        for intervention in ("natural", "independent_history")
    }
    h = {name: _rates(value, spec.atlas_lineage_generations) for name, value in high.items()}
    l = {name: _rates(value, spec.atlas_lineage_generations) for name, value in low.items()}
    information_high = h["natural"]["correct_rate"] - h["independent_history"]["correct_rate"]
    information_low = l["natural"]["correct_rate"] - l["independent_history"]["correct_rate"]
    return {
        "natural_performance": h["natural"]["correct_rate"],
        "information_high": information_high,
        "natural_minus_zero": h["natural"]["correct_rate"] - h["zero"]["correct_rate"],
        "reader_dependence": h["natural"]["correct_rate"] - h["reader_off"]["correct_rate"],
        "renewal_dependence": h["natural"]["correct_rate"] - h["renewal_off"]["correct_rate"],
        "opposite_donor_following": h["opposite_history"]["wrong_rate"]
        - h["opposite_history"]["correct_rate"],
        "information_low": information_low,
        "predictability_interaction": information_high - information_low,
    }


def _rank_roots(population: dict[str, Any], count: int) -> list[dict[str, Any]]:
    return sorted(
        population["final_population"],
        key=lambda value: (-float(value["selection_score"]["fitness"]), str(value["genotype_id"])),
    )[:count]


def _task_atlas(
    args: tuple[str, dict[str, Any], dict[str, Any], str, str]
) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, protocol_digest = args
    population = read_json(Path(population_text))
    spec = InterpreterDepthSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    task_index = int(population["population_index"])
    final_path = Path(output_text) / f"task-{task_index:03d}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"interpreter atlas registration differs: {final_path}")
    roots: list[dict[str, Any]] = []
    for root_index, archived in enumerate(_rank_roots(population, spec.atlas_roots_per_task)):
        root = deserialize_genotype(archived)
        mask = structural_mask(root[0], local_carrier(root[1]))
        rows: list[dict[str, Any]] = []
        for flat_index in range(spec.atlas_edge_limit):
            target, source = divmod(flat_index, root[0].genes)
            features = edge_features(root[0], mask, target, source)
            for operation in spec.atlas_perturbations:
                scope = (
                    f"interpreter-atlas.task-{task_index:03d}.root-{root_index:02d}."
                    f"edge-{target:02d}-{source:02d}.{operation}"
                )
                random = rng_for(
                    spec.atlas_seed,
                    "interpreter-atlas-perturbation",
                    task_index,
                    root_index,
                    target,
                    source,
                    operation,
                )
                perturbed_rulebook = perturb_edge(
                    root[0],
                    target,
                    source,
                    operation,
                    random,
                    local_sigma=spec.local_weight_sigma,
                )
                perturbed_mask = structural_mask(
                    perturbed_rulebook, local_carrier(root[1])
                )
                baseline = atlas_effects(root, population["task"], kernel, spec, scope)
                candidate = atlas_effects(
                    (perturbed_rulebook, root[1]), population["task"], kernel, spec, scope
                )
                delta = {field: candidate[field] - baseline[field] for field in baseline}
                rows.append(
                    {
                        "task_index": task_index,
                        "root_index": root_index,
                        "edge_index": flat_index,
                        "operation": operation,
                        "features": features,
                        "perturbed_weight": float(perturbed_rulebook.weights[target, source]),
                        "perturbed_carrier_mask": list(perturbed_mask),
                        "carrier_mask_changed": perturbed_mask != mask,
                        "baseline": baseline,
                        "perturbed": candidate,
                        "delta": delta,
                        "scope": scope,
                    }
                )
        roots.append(
            {
                "root_index": root_index,
                "genotype": serialize_genotype(*root),
                "selection_score": archived["selection_score"],
                "carrier_mask": list(mask),
                "rows": rows,
            }
        )
    result = {
        "format": DEPTH_ATLAS_FORMAT,
        "protocol_digest": protocol_digest,
        "task_index": task_index,
        "task_digest": population["task"]["task_digest"],
        "task": population["task"],
        "source_population_id": population["population_id"],
        "roots": roots,
        "perturbations": sum(len(root["rows"]) for root in roots),
        "common_stream_baseline_is_recomputed_for_every_perturbation": True,
    }
    result["result_digest"] = canonical_digest(result)
    _atomic_json(final_path, result)
    return result


def _atlas_analysis(results: list[dict[str, Any]], spec: InterpreterDepthSpec) -> dict[str, Any]:
    fields = (
        "natural_performance",
        "information_high",
        "natural_minus_zero",
        "reader_dependence",
        "renewal_dependence",
        "opposite_donor_following",
        "predictability_interaction",
    )
    summaries: dict[str, Any] = {}
    for operation in spec.atlas_perturbations:
        task_values: dict[str, dict[str, float]] = {}
        for result in results:
            rows = [
                row for root in result["roots"] for row in root["rows"]
                if row["operation"] == operation
            ]
            task_values[str(result["task_index"])] = {
                field: float(np.mean([row["delta"][field] for row in rows])) for field in fields
            }
        summaries[operation] = {
            "task_values": task_values,
            "intervals": {
                field: _interval(
                    (value[field] for value in task_values.values()),
                    spec.atlas_seed,
                    f"interpreter-atlas.{operation}.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in fields
            },
        }

    strata: dict[str, Any] = {}
    for label, predicate in (
        ("carrier_to_carrier", lambda row: row["features"]["both_endpoints_are_carrier_loci"]),
        ("source_carrier_only", lambda row: row["features"]["source_is_carrier_locus"] and not row["features"]["target_is_carrier_locus"]),
        ("target_carrier_only", lambda row: row["features"]["target_is_carrier_locus"] and not row["features"]["source_is_carrier_locus"]),
        ("outside_carrier", lambda row: not row["features"]["source_is_carrier_locus"] and not row["features"]["target_is_carrier_locus"]),
        ("self_edges", lambda row: row["features"]["self_edge"]),
        ("nonself_edges", lambda row: not row["features"]["self_edge"]),
        ("carrier_mask_changing", lambda row: row["carrier_mask_changed"]),
        ("carrier_mask_stable", lambda row: not row["carrier_mask_changed"]),
    ):
        task_values = {}
        for result in results:
            rows = [
                row for root in result["roots"] for row in root["rows"]
                if predicate(row)
            ]
            if rows:
                task_values[str(result["task_index"])] = float(
                    np.mean([row["delta"]["information_high"] for row in rows])
                )
        strata[label] = {
            "task_values": task_values,
            "information_delta_interval": _interval(
                task_values.values(),
                spec.atlas_seed,
                f"interpreter-atlas.stratum.{label}",
                spec.bootstrap_repetitions,
                spec.interval_level,
            ),
        }

    all_rows = [row for result in results for root in result["roots"] for row in root["rows"]]
    damaging = sorted(all_rows, key=lambda value: float(value["delta"]["information_high"]))[:50]
    result = {
        "format": f"{DEPTH_ATLAS_FORMAT}-analysis",
        "inferential_unit": "sealed founder task",
        "perturbations": len(all_rows),
        "operation_summaries": summaries,
        "edge_strata": strata,
        "most_information_damaging_perturbations": damaging,
        "negative_delta_means_damage": True,
        "atlas_is_diagnostic_and_cannot_select_fitness_terms": True,
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def run_interpreter_atlas(
    spec: InterpreterDepthSpec,
    parent: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("interpreter atlas permits one to four CPU workers")
    parent = parent.resolve()
    verify_wagner_ph_robustness_campaign(parent)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_interpreter_atlas(destination)
        return destination
    source = parent / "evolution"
    kernel = spec.kernel()
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "parent_checksum": sha256_file(parent / "SHA256SUMS"),
        "source_evolution_checksum": sha256_file(source / "SHA256SUMS"),
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": f"{DEPTH_ATLAS_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **payload,
        "parent": str(parent),
        "source_arm": "individual_independent",
    }
    path = destination / "registration.json"
    if path.is_file() and read_json(path) != registration:
        raise ValueError("existing interpreter-atlas registration differs")
    if not path.is_file():
        _atomic_json(path, registration)
    shards = destination / "tasks"
    shards.mkdir(exist_ok=True)
    population_files = sorted(source.glob("populations/individual_independent.population-*.json"))
    if len(population_files) != spec.task_count:
        raise ValueError("interpreter atlas source population count mismatch")
    work = [
        (str(path), spec.to_dict(), kernel.to_dict(), str(shards), protocol_digest)
        for path in population_files
    ]
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_task_atlas, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_task_atlas, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(destination / "progress.json", {
                "format": f"{DEPTH_ATLAS_FORMAT}-progress",
                "completed_tasks": index,
                "total_tasks": len(work),
                "elapsed_seconds": elapsed,
                "tasks_per_second": rate,
                "eta_seconds": (len(work) - index) / rate if rate else None,
            })
            if progress:
                progress(f"interpreter atlas {index}/{len(work)} tasks")
    finally:
        if executor is not None:
            executor.shutdown()
    results.sort(key=lambda value: value["task_index"])
    analysis = _atlas_analysis(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "manifest.json", {
        "format": f"{DEPTH_ATLAS_FORMAT}-manifest",
        "protocol_digest": protocol_digest,
        "tasks": len(results),
        "perturbations": sum(value["perturbations"] for value in results),
        "expected_perturbations": (
            spec.task_count * spec.atlas_roots_per_task * spec.atlas_edge_limit
            * len(spec.atlas_perturbations)
        ),
        "workers": workers,
        "elapsed_seconds": time.monotonic() - started,
        "runtime": runtime_manifest(),
    })
    write_checksums(destination)
    verify_interpreter_atlas(destination)
    return destination


def verify_interpreter_atlas(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != f"{DEPTH_ATLAS_FORMAT}-registration":
        raise ValueError("interpreter-atlas registration format mismatch")
    spec = InterpreterDepthSpec.from_dict(registration["spec"])
    parent = Path(registration["parent"])
    if sha256_file(parent / "SHA256SUMS") != registration["parent_checksum"]:
        raise ValueError("sealed robustness parent changed after interpreter atlas")
    payload = {
        "spec": spec.to_dict(),
        "kernel": registration["kernel"],
        "parent_checksum": registration["parent_checksum"],
        "source_evolution_checksum": registration["source_evolution_checksum"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("interpreter-atlas protocol digest mismatch")
    files = sorted((directory / "tasks").glob("*.json"))
    expected = spec.task_count * spec.atlas_roots_per_task * spec.atlas_edge_limit * len(spec.atlas_perturbations)
    count = 0
    for path in files:
        value = read_json(path)
        archived = dict(value)
        result_digest = archived.pop("result_digest", None)
        if result_digest != canonical_digest(archived):
            raise ValueError(f"interpreter-atlas shard digest mismatch: {path.name}")
        count += int(value["perturbations"])
    if len(files) != spec.task_count or count != expected or int(manifest["perturbations"]) != expected:
        raise ValueError("interpreter-atlas dimensions are incomplete")
    archived_analysis = dict(analysis)
    analysis_digest = archived_analysis.pop("analysis_digest", None)
    if analysis_digest != canonical_digest(archived_analysis):
        raise ValueError("interpreter-atlas analysis digest mismatch")
    return {"verified": True, "tasks": len(files), "perturbations": count, "checksums": len(checksums)}


def replay_atlas_cell(
    directory: Path,
    task_index: int,
    root_index: int,
    edge_index: int,
    operation: str,
) -> dict[str, Any]:
    registration = read_json(directory / "registration.json")
    spec = InterpreterDepthSpec.from_dict(registration["spec"])
    kernel = CooptionSpec.from_dict(registration["kernel"])
    shard = read_json(directory / "tasks" / f"task-{task_index:03d}.json")
    root_record = shard["roots"][root_index]
    root = deserialize_genotype(root_record["genotype"])
    row = next(
        value for value in root_record["rows"]
        if int(value["edge_index"]) == edge_index and value["operation"] == operation
    )
    target, source = divmod(edge_index, root[0].genes)
    candidate = perturb_edge(
        root[0], target, source, operation,
        rng_for(spec.atlas_seed, "interpreter-atlas-perturbation", task_index, root_index, target, source, operation),
        local_sigma=spec.local_weight_sigma,
    )
    baseline = atlas_effects(root, shard["task"], kernel, spec, row["scope"])
    perturbed = atlas_effects((candidate, root[1]), shard["task"], kernel, spec, row["scope"])
    replay = {
        "perturbed_weight": float(candidate.weights[target, source]),
        "perturbed_carrier_mask": list(
            structural_mask(candidate, local_carrier(root[1]))
        ),
        "carrier_mask_changed": tuple(
            structural_mask(candidate, local_carrier(root[1]))
        ) != tuple(root_record["carrier_mask"]),
        "baseline": baseline,
        "perturbed": perturbed,
        "delta": {field: perturbed[field] - baseline[field] for field in baseline},
    }
    matches = canonical_digest(replay) == canonical_digest({
        "perturbed_weight": row["perturbed_weight"],
        "perturbed_carrier_mask": row["perturbed_carrier_mask"],
        "carrier_mask_changed": row["carrier_mask_changed"],
        "baseline": row["baseline"],
        "perturbed": row["perturbed"],
        "delta": row["delta"],
    })
    return {
        "task_index": task_index,
        "root_index": root_index,
        "edge_index": edge_index,
        "operation": operation,
        "matches": matches,
        "replayed": replay,
    }
