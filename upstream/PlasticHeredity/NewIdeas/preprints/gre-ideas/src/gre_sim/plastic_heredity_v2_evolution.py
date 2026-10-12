"""Prospective evolution with selection endpoints separated from one common assay."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    verify_checksums,
    write_checksums,
    write_json,
)
from .engines import rulebook_from_dict
from .mechanism_dynamics import MechanismRulebook
from .plastic_heredity_v2_config import EvolutionV2Spec
from .plastic_memory_dynamics import (
    AttractorPair,
    balanced_midpoints,
    clamp_state,
    cue_nodes,
    damage_state,
    develop_memory_cycle,
    select_attractor_pair,
)
from .plastic_memory_evolution import _mutate, _recombine
from .rng import rng_for
from .wagner import WagnerRulebook


TREATMENTS = ("memory_selection", "cue_performance_sham", "neutral")
EVOLUTION_REGISTRATION_FORMAT = "gre-plastic-heredity-v2-evolution-registration-v1"
EVOLUTION_POPULATION_FORMAT = "gre-plastic-heredity-v2-evolution-population-v1"
EVOLUTION_ANALYSIS_FORMAT = "gre-plastic-heredity-v2-evolution-analysis-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _sample_founder(
    spec: EvolutionV2Spec, population_id: str
) -> tuple[WagnerRulebook, AttractorPair, int, tuple[int, ...]]:
    for proposal in range(100_000):
        rulebook = WagnerRulebook.random(
            spec.genes,
            rng_for(spec.master_seed, "v2-evolution-founder", population_id, proposal),
        )
        viewed = MechanismRulebook(rulebook, "wagner_sequential")
        pair = select_attractor_pair(viewed.landscape(), spec.genes, 0.05, 0.40)
        if pair is None:
            continue
        ordering = rng_for(
            spec.master_seed, "v2-evolution-node-order", population_id
        ).permutation(spec.genes)
        midpoint = balanced_midpoints(pair, spec.genes, ordering, 1)[0]
        nodes = cue_nodes(pair, spec.genes, 0.50, ordering)
        return rulebook, pair, midpoint, nodes
    raise RuntimeError(f"could not sample v2 evolution founder for {population_id}")


def _score_endpoint(
    rulebook: WagnerRulebook,
    pair: AttractorPair,
    midpoint: int,
    cue_node_indices: tuple[int, ...],
    endpoint: str,
    spec: EvolutionV2Spec,
    population_id: str,
    coordinate: tuple[Any, ...],
    replicates: int,
) -> float:
    if endpoint == "neutral":
        return 0.5
    viewed = MechanismRulebook(rulebook, "wagner_sequential")
    successes: list[float] = []
    for history in ("A", "B"):
        target = pair.state(history)
        for replicate in range(replicates):
            common = (
                spec.master_seed,
                "plastic-heredity-v2-evolution-score",
                population_id,
                *coordinate,
                history,
                replicate,
            )
            if endpoint == "cue_only":
                initial = clamp_state(midpoint, target, cue_node_indices)
                result = viewed.develop(initial, None, 100)
                successes.append(
                    float(result.status == "point" and int(result.final_state) == target)
                )
                continue
            if endpoint != "descendant_memory":
                raise ValueError(f"unknown v2 evolution endpoint: {endpoint}")
            # Exact target injection equalizes writing. The selected phenotype is
            # the ability of an uncued descendant to retain and recover that state.
            state = target
            mark = np.zeros(viewed.genes, dtype=float)
            for age in range(spec.descendant_age):
                value = develop_memory_cycle(
                    viewed,
                    state,
                    midpoint,
                    mark,
                    1.0,
                    spec.expression_flip_probability,
                    0.0,
                    0.0,
                    0.0,
                    100,
                    rng_for(*common, "descendant", age, "carry"),
                    rng_for(*common, "descendant", age, "mark"),
                    rng_for(*common, "descendant", age, "dynamics"),
                    write_mark=False,
                )
                state = value.state
            state, _ = damage_state(
                state,
                viewed.genes,
                spec.neutral_damage_fraction,
                rng_for(*common, "damage"),
            )
            run = 0
            maximum = 0
            for cycle in range(spec.post_horizon):
                value = develop_memory_cycle(
                    viewed,
                    state,
                    midpoint,
                    mark,
                    1.0,
                    spec.expression_flip_probability,
                    0.0,
                    0.0,
                    0.0,
                    100,
                    rng_for(*common, "post", cycle, "carry"),
                    rng_for(*common, "post", cycle, "mark"),
                    rng_for(*common, "post", cycle, "dynamics"),
                    write_mark=False,
                )
                state = value.state
                run = run + 1 if value.status == "point" and state == target else 0
                maximum = max(maximum, run)
            successes.append(float(maximum >= spec.hold_run))
    return float(np.mean(successes))


def _population_task(
    args: tuple[dict[str, Any], str, int, str, str]
) -> dict[str, Any]:
    spec_value, treatment, population_index, output_text, protocol_digest = args
    spec = EvolutionV2Spec.from_dict(spec_value)
    population_id = f"{treatment}.population-{population_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"v2 evolution population registration differs: {final_path}")
    checkpoint = output / f"{population_id}.checkpoint.json"
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        founder = rulebook_from_dict(saved["founder"])
        if not isinstance(founder, WagnerRulebook):
            raise TypeError("v2 evolution checkpoint founder is not Wagner")
        pair = AttractorPair(**saved["pair"])
        midpoint = int(saved["midpoint"])
        nodes = tuple(int(value) for value in saved["nodes"])
        population = [rulebook_from_dict(value) for value in saved["population"]]
        if not all(isinstance(value, WagnerRulebook) for value in population):
            raise TypeError("v2 evolution checkpoint population is not Wagner")
        fitnesses = np.asarray(saved["fitnesses"], dtype=float)
        trace = list(saved["trace"])
        start_generation = int(saved["generation"]) + 1
    else:
        founder, pair, midpoint, nodes = _sample_founder(spec, population_id)
        population = [founder]
        for index in range(1, spec.population_size):
            child = _mutate(
                founder,
                rng_for(spec.master_seed, "v2-evolution-initial", population_id, index),
            )
            if not isinstance(child, WagnerRulebook):
                raise TypeError("v2 evolution mutation produced a non-Wagner child")
            population.append(child)
        endpoint = spec.selection_endpoint(treatment)
        fitnesses = np.asarray(
            [
                _score_endpoint(
                    value,
                    pair,
                    midpoint,
                    nodes,
                    endpoint,
                    spec,
                    population_id,
                    ("initial", index),
                    spec.training_replicates,
                )
                for index, value in enumerate(population)
            ],
            dtype=float,
        )
        trace = [
            {
                "generation": 0,
                "mean_score": float(np.mean(fitnesses)),
                "best_score": float(np.max(fitnesses)),
                "proposals": 0,
            }
        ]
        start_generation = 1
    endpoint = spec.selection_endpoint(treatment)
    for generation in range(start_generation, spec.generations + 1):
        following: list[WagnerRulebook] = []
        scores: list[float] = []
        proposal = 0
        maximum = spec.population_size * 100
        while len(following) < spec.population_size and proposal < maximum:
            rng = rng_for(
                spec.master_seed,
                "v2-evolution-offspring",
                population_id,
                generation,
                proposal,
            )
            left = population[int(rng.integers(len(population)))]
            right = population[int(rng.integers(len(population)))]
            child = _mutate(_recombine(left, right, rng), rng)
            if not isinstance(child, WagnerRulebook):
                raise TypeError("v2 evolution produced a non-Wagner child")
            score = _score_endpoint(
                child,
                pair,
                midpoint,
                nodes,
                endpoint,
                spec,
                population_id,
                ("generation", generation, proposal),
                spec.training_replicates,
            )
            proposal += 1
            acceptance = 1.0 if endpoint == "neutral" else 0.05 + 0.95 * score
            if rng.random() <= acceptance:
                following.append(child)
                scores.append(score)
        if len(following) != spec.population_size:
            raise RuntimeError(f"{population_id} could not fill generation {generation}")
        population = following
        fitnesses = np.asarray(scores, dtype=float)
        trace.append(
            {
                "generation": generation,
                "mean_score": float(np.mean(fitnesses)),
                "best_score": float(np.max(fitnesses)),
                "proposals": proposal,
            }
        )
        _atomic_json(
            checkpoint,
            {
                "format": "gre-plastic-heredity-v2-evolution-checkpoint-v1",
                "protocol_digest": protocol_digest,
                "population_id": population_id,
                "generation": generation,
                "founder": founder.to_dict(),
                "pair": asdict(pair),
                "midpoint": midpoint,
                "nodes": list(nodes),
                "population": [value.to_dict() for value in population],
                "fitnesses": fitnesses.tolist(),
                "trace": trace,
            },
        )
    selection_scores = np.asarray(
        [
            _score_endpoint(
                value,
                pair,
                midpoint,
                nodes,
                endpoint,
                spec,
                population_id,
                ("selection", index),
                spec.selection_replicates,
            )
            for index, value in enumerate(population)
        ],
        dtype=float,
    )
    selected_index = int(np.argmax(selection_scores))
    selected = population[selected_index]
    common_coordinate = ("heldout-common-descendant-memory",)
    founder_score = _score_endpoint(
        founder,
        pair,
        midpoint,
        nodes,
        spec.common_assay_endpoint,
        spec,
        population_id,
        common_coordinate,
        spec.heldout_replicates,
    )
    selected_score = _score_endpoint(
        selected,
        pair,
        midpoint,
        nodes,
        spec.common_assay_endpoint,
        spec,
        population_id,
        common_coordinate,
        spec.heldout_replicates,
    )
    parent_values: list[float] = []
    offspring_values: list[float] = []
    for index, parent in enumerate(population[: min(32, len(population))]):
        child = _mutate(
            parent,
            rng_for(spec.master_seed, "v2-evolution-breeding", population_id, index),
        )
        if not isinstance(child, WagnerRulebook):
            raise TypeError("v2 evolution breeding mutation is not Wagner")
        coordinate = ("breeding-common", index)
        parent_values.append(
            _score_endpoint(
                parent,
                pair,
                midpoint,
                nodes,
                spec.common_assay_endpoint,
                spec,
                population_id,
                coordinate,
                spec.selection_replicates,
            )
        )
        offspring_values.append(
            _score_endpoint(
                child,
                pair,
                midpoint,
                nodes,
                spec.common_assay_endpoint,
                spec,
                population_id,
                coordinate,
                spec.selection_replicates,
            )
        )
    breeding = (
        float(np.corrcoef(parent_values, offspring_values)[0, 1])
        if np.std(parent_values) > 0.0 and np.std(offspring_values) > 0.0
        else 0.0
    )
    result = {
        "format": EVOLUTION_POPULATION_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "population_index": population_index,
        "treatment": treatment,
        "selection_endpoint": endpoint,
        "common_assay_endpoint": spec.common_assay_endpoint,
        "founder": founder.to_dict(),
        "selected": selected.to_dict(),
        "pair": asdict(pair),
        "midpoint": midpoint,
        "nodes": list(nodes),
        "founder_common_score": founder_score,
        "selected_common_score": selected_score,
        "common_score_change": selected_score - founder_score,
        "common_breeding_value_correlation": breeding,
        "trace": trace,
    }
    _atomic_json(final_path, result)
    return result


def _estimate(values: list[float], spec: EvolutionV2Spec, label: str) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    rng = rng_for(spec.master_seed, "v2-evolution-bootstrap", label)
    indices = rng.integers(0, array.size, size=(4096, array.size))
    draws = np.mean(array[indices], axis=1)
    return {
        "mean": float(np.mean(array)),
        "interval": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "lower": float(np.quantile(draws, 0.05 / 3.0)),
        "populations": int(array.size),
    }


def _difference(
    left: list[float], right: list[float], spec: EvolutionV2Spec, label: str
) -> dict[str, Any]:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    rng = rng_for(spec.master_seed, "v2-evolution-contrast", label)
    ai = rng.integers(0, a.size, size=(4096, a.size))
    bi = rng.integers(0, b.size, size=(4096, b.size))
    draws = np.mean(a[ai], axis=1) - np.mean(b[bi], axis=1)
    return {
        "mean": float(np.mean(a) - np.mean(b)),
        "interval": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "lower": float(np.quantile(draws, 0.05 / 3.0)),
    }


def analyze_v2_evolution(
    results: list[dict[str, Any]], spec: EvolutionV2Spec
) -> dict[str, Any]:
    changes = {
        treatment: [
            float(value["common_score_change"])
            for value in results
            if value["treatment"] == treatment
        ]
        for treatment in TREATMENTS
    }
    breeding = {
        treatment: [
            float(value["common_breeding_value_correlation"])
            for value in results
            if value["treatment"] == treatment
        ]
        for treatment in TREATMENTS
    }
    cells = {
        treatment: {
            "common_score_change": _estimate(
                changes[treatment], spec, f"change.{treatment}"
            ),
            "common_breeding_value_correlation": _estimate(
                breeding[treatment], spec, f"breeding.{treatment}"
            ),
            "selection_endpoint": spec.selection_endpoint(treatment),
            "common_assay_endpoint": spec.common_assay_endpoint,
        }
        for treatment in TREATMENTS
    }
    contrasts = {
        control: _difference(
            changes["memory_selection"],
            changes[control],
            spec,
            f"memory-minus-{control}",
        )
        for control in ("cue_performance_sham", "neutral")
    }
    memory_breeding = cells["memory_selection"]["common_breeding_value_correlation"]
    criteria = {
        f"memory_improvement_over_{control}_at_least_0_05": value["mean"] >= 0.05
        for control, value in contrasts.items()
    }
    criteria.update(
        {
            f"memory_improvement_over_{control}_lower_above_zero": value["lower"] > 0.0
            for control, value in contrasts.items()
        }
    )
    criteria["common_assay_breeding_lower_above_zero"] = memory_breeding["lower"] > 0.0
    return {
        "format": EVOLUTION_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "exploratory": spec.exploratory,
        "record_count": len(results),
        "cells": cells,
        "contrasts": contrasts,
        "response_gate": {"criteria": criteria, "passed": all(criteria.values())},
        "endpoint_separation": {
            "selection": {
                treatment: spec.selection_endpoint(treatment) for treatment in TREATMENTS
            },
            "heldout_for_all_treatments": spec.common_assay_endpoint,
        },
    }


def run_v2_evolution(
    spec: EvolutionV2Spec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("v2 evolution requires 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_v2_evolution(destination)
        return destination
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": EVOLUTION_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
        "selection_and_assay_endpoints_separated": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing v2 evolution registration differs")
    else:
        _atomic_json(registration_path, registration)
    tasks = [
        (spec.to_dict(), treatment, index, str(populations), digest)
        for treatment in TREATMENTS
        for index in range(spec.populations_per_treatment)
    ]
    started = time.monotonic()
    prior_elapsed = 0.0
    progress_path = destination / "progress.json"
    if progress_path.is_file():
        try:
            prior_elapsed = float(read_json(progress_path).get("elapsed_seconds", 0.0))
        except (OSError, TypeError, ValueError):
            prior_elapsed = 0.0
    results: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        futures = [executor.submit(_population_task, task) for task in tasks]
        for index, future in enumerate(futures, start=1):
            results.append(future.result())
            elapsed = prior_elapsed + time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                progress_path,
                {
                    "format": "gre-plastic-heredity-v2-evolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress is not None:
                progress(f"completed v2 evolution population {index}/{len(tasks)}")
    analysis = analyze_v2_evolution(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    manifest = {
        "format": "gre-plastic-heredity-v2-evolution-manifest-v1",
        "protocol_digest": digest,
        "populations": len(results),
        "workers": workers,
        "elapsed_seconds": prior_elapsed + time.monotonic() - started,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "manifest.json", manifest)
    lines = [
        "# Prospective Plastic Heredity v2 evolution",
        "",
        "> Exploratory." if spec.exploratory else "> Untouched confirmation.",
        "",
        f"- Populations: {len(results)}",
        f"- Common assay: `{spec.common_assay_endpoint}` for every treatment",
        "",
        f"- Response gate: {'PASS' if analysis['response_gate']['passed'] else 'fail'}",
        "",
    ]
    (destination / "report.md").write_text("\n".join(lines), encoding="utf-8")
    write_checksums(destination)
    verify_v2_evolution(destination)
    return destination


def verify_v2_evolution(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != EVOLUTION_REGISTRATION_FORMAT:
        raise ValueError("v2 evolution registration format mismatch")
    spec = EvolutionV2Spec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("v2 evolution protocol digest mismatch")
    finals = [
        path
        for path in (directory / "populations").glob("*.json")
        if ".checkpoint." not in path.name
    ]
    expected = len(TREATMENTS) * spec.populations_per_treatment
    if len(finals) != expected or len(finals) != int(manifest["populations"]):
        raise ValueError("v2 evolution population count mismatch")
    return {
        "verified": True,
        "files": len(checksums),
        "populations": len(finals),
        "protocol_digest": digest,
    }
