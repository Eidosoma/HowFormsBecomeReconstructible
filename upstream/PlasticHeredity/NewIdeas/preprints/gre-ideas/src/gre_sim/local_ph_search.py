"""Deterministic evolutionary search for target-blind local carrier machinery."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
from dataclasses import replace
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
from .local_ph_config import (
    LOCAL_PH_SEARCH_FORMAT,
    LocalCarrierGenome,
    LocalConditionSpec,
    LocalSearchSpec,
    LocalStudySpec,
)
from .local_ph_protocols import NOMINAL_COPY_NOISE, STRONG_COPY_NOISE
from .local_ph_study import build_local_registry, simulate_local_source
from .rng import rng_for


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _named_genome(
    write_rate: float,
    decay: float,
    coupling: float,
    hysteresis: int,
    topology: str,
    k: int,
) -> LocalCarrierGenome:
    payload = {
        "write_rate": round(float(write_rate), 3),
        "decay": round(float(decay), 3),
        "coupling": round(float(coupling), 3),
        "hysteresis": int(hysteresis),
        "topology": str(topology),
        "k": int(k),
    }
    return LocalCarrierGenome(f"local-{canonical_digest(payload)[:12]}", **payload)


def initial_population(spec: LocalSearchSpec) -> tuple[LocalCarrierGenome, ...]:
    """Create a deterministic diverse population, including interpretable anchors."""

    anchors = [
        _named_genome(1.0, 0.0, 1.0, 1, "all", 10),
        _named_genome(0.75, 0.02, 0.75, 1, "outgoing", 5),
        _named_genome(0.50, 0.05, 0.75, 2, "outgoing", 3),
        _named_genome(0.75, 0.02, 0.75, 1, "self_feedback", 5),
    ]
    values = {value.name: value for value in anchors}
    proposal = 0
    while len(values) < spec.population_size:
        rng = rng_for(spec.master_seed, "local-search-initial", proposal)
        topology = ("all", "outgoing", "self_feedback")[int(rng.integers(3))]
        k = 10 if topology == "all" else (3, 5, 10)[int(rng.integers(3))]
        genome = _named_genome(
            rng.uniform(0.10, 1.0),
            rng.uniform(0.0, 0.20),
            rng.uniform(0.10, 1.0),
            int(rng.integers(1, 4)),
            topology,
            k,
        )
        values[genome.name] = genome
        proposal += 1
    return tuple(list(values.values())[: spec.population_size])


def _offspring(
    spec: LocalSearchSpec,
    elites: tuple[LocalCarrierGenome, ...],
    generation: int,
) -> tuple[LocalCarrierGenome, ...]:
    values = {value.name: value for value in elites[:8]}
    proposal = 0
    while len(values) < spec.population_size:
        rng = rng_for(spec.master_seed, "local-search-offspring", generation, proposal)
        left = elites[int(rng.integers(len(elites)))]
        right = elites[int(rng.integers(len(elites)))]
        topology = left.topology if rng.random() < 0.5 else right.topology
        if rng.random() < 0.15:
            topology = ("all", "outgoing", "self_feedback")[int(rng.integers(3))]
        k = left.k if rng.random() < 0.5 else right.k
        if rng.random() < 0.20:
            k = (3, 5, 10)[int(rng.integers(3))]
        if topology == "all":
            k = 10
        genome = _named_genome(
            np.clip(0.5 * (left.write_rate + right.write_rate) + rng.normal(0.0, 0.10), 0.10, 1.0),
            np.clip(0.5 * (left.decay + right.decay) + rng.normal(0.0, 0.025), 0.0, 0.20),
            np.clip(0.5 * (left.coupling + right.coupling) + rng.normal(0.0, 0.10), 0.10, 1.0),
            int(np.clip((left.hysteresis if rng.random() < 0.5 else right.hysteresis) + (int(rng.integers(-1, 2)) if rng.random() < 0.20 else 0), 1, 3)),
            topology,
            k,
        )
        values[genome.name] = genome
        proposal += 1
    return tuple(list(values.values())[: spec.population_size])


def _evaluation_study(
    search: LocalSearchSpec,
    genomes: tuple[LocalCarrierGenome, ...],
    futures: int,
    label: str,
) -> LocalStudySpec:
    conditions = tuple(
        LocalConditionSpec(f"{value.name}.intact", value.name, "intact", "nominal", True)
        for value in genomes
    ) + (LocalConditionSpec("zero", None, "zero", "nominal"),)
    result = LocalStudySpec(
        f"{search.cohort_id}.{label}",
        f"evolutionary-search.{label}",
        search.master_seed,
        1,
        genomes,
        (NOMINAL_COPY_NOISE, STRONG_COPY_NOISE),
        conditions,
        checkpoint_generations=(0, 4),
        challenges=("forced_break",),
        futures_per_history=futures,
        genes=search.genes,
        cue_fraction=search.cue_fraction,
        cue_dwell=search.cue_dwell,
        generation_cycles=search.generation_cycles,
        horizon=search.horizon,
        strict_run=search.strict_run,
        stable_run=search.stable_run,
        expression_flip_probability=search.expression_flip_probability,
        bootstrap_repetitions=64,
        exploratory=True,
    )
    result.validate()
    return result


def _score_source(source: dict[str, Any], study_value: dict[str, Any]) -> dict[str, Any]:
    study = LocalStudySpec.from_dict(study_value)
    records = simulate_local_source(source, study.to_dict())
    cells: dict[tuple[str, str], list[float]] = {}
    acquired: list[float] = []
    for record in records:
        if int(record["generation"]) != 4:
            continue
        condition = str(record["condition"])
        half = str(record["half"])
        value = cells.setdefault((condition, half), [0.0, 0.0])
        value[0] += float(record["correct_hold8"])
        value[1] += 1.0
        if condition == "zero":
            acquired.append(float(record["acquired"]))
    zero_total = [sum(cells[("zero", half)][index] for half in ("A", "B")) for index in (0, 1)]
    zero_rate = zero_total[0] / zero_total[1]
    scores: dict[str, Any] = {}
    for genome in study.genomes:
        condition = f"{genome.name}.intact"
        halves = [cells[(condition, half)][0] / cells[(condition, half)][1] for half in ("A", "B")]
        local = sum(cells[(condition, half)][0] for half in ("A", "B")) / sum(
            cells[(condition, half)][1] for half in ("A", "B")
        )
        scores[genome.name] = {
            "local_rate": local,
            "zero_rate": zero_rate,
            "risk_gain": local - zero_rate,
            "half_rates": halves,
        }
    return {
        "source_id": source["source_id"],
        "acquisition_rate": float(np.mean(acquired)) if acquired else 0.0,
        "scores": scores,
    }


def evaluate_population(
    search: LocalSearchSpec,
    sources: list[dict[str, Any]],
    genomes: tuple[LocalCarrierGenome, ...],
    futures: int,
    label: str,
    workers: int,
) -> dict[str, Any]:
    study = _evaluation_study(search, genomes, futures, label)
    if workers == 1:
        source_scores = [_score_source(source, study.to_dict()) for source in sources]
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        ) as executor:
            source_scores = list(
                executor.map(
                    _score_source,
                    sources,
                    [study.to_dict()] * len(sources),
                )
            )
    result: dict[str, Any] = {}
    for genome in genomes:
        per_source = [float(value["scores"][genome.name]["risk_gain"]) for value in source_scores]
        halves = np.asarray(
            [value["scores"][genome.name]["half_rates"] for value in source_scores], dtype=float
        )
        if len(halves) < 3:
            reliability = None
        elif np.std(halves[:, 0]) == 0.0 or np.std(halves[:, 1]) == 0.0:
            reliability = 1.0 if np.array_equal(halves[:, 0], halves[:, 1]) else 0.0
        else:
            reliability = float(np.corrcoef(halves[:, 0], halves[:, 1])[0, 1])
        result[genome.name] = {
            "genome": genome.to_dict(),
            "risk_gain": float(np.mean(per_source)),
            "positive_sources": int(np.sum(np.asarray(per_source) > 0.0)),
            "sources": len(per_source),
            "split_half_reliability": reliability,
            "acquisition_rate": float(np.mean([value["acquisition_rate"] for value in source_scores])),
            "source_risk_gains": per_source,
        }
    return result


def _rank(scores: dict[str, Any]) -> list[LocalCarrierGenome]:
    values = list(scores.values())
    values.sort(
        key=lambda value: (
            -float(value["risk_gain"]),
            -float(value["split_half_reliability"] if value["split_half_reliability"] is not None else -1.0),
            int(value["genome"]["k"]),
            value["genome"]["name"],
        )
    )
    return [LocalCarrierGenome(**value["genome"]) for value in values]


def select_nominees(validation: dict[str, Any]) -> dict[str, Any]:
    ranked = _rank(validation)
    eligible = [
        value
        for value in ranked
        if float(validation[value.name]["risk_gain"]) >= 0.05
        and validation[value.name]["split_half_reliability"] is not None
        and float(validation[value.name]["split_half_reliability"]) >= 0.70
        and float(validation[value.name]["acquisition_rate"]) >= 0.80
    ]
    nominees: list[LocalCarrierGenome] = []
    if eligible:
        strongest = eligible[0]
        simplest = min(
            eligible,
            key=lambda value: (
                value.k,
                value.coupling,
                -float(validation[value.name]["risk_gain"]),
                value.name,
            ),
        )
        for value in (strongest, simplest):
            if value.name not in {item.name for item in nominees}:
                nominees.append(value)
    diagnostics = ranked[:2]
    return {
        "eligible": bool(eligible),
        "nominees": [value.to_dict() for value in nominees],
        "diagnostic_top_two": [value.to_dict() for value in diagnostics],
        "rule": (
            "strongest validation risk gain plus simplest eligible k/coupling; "
            "eligibility requires risk>=0.05, reliability>=0.70, acquisition>=0.80"
        ),
    }


def run_local_search(
    spec: LocalSearchSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 4:
        raise ValueError("local search permits one to four workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_local_search(destination)
        return destination
    registration = {
        "format": LOCAL_PH_SEARCH_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing local search registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        registry = read_json(registry_path)
    else:
        placeholder = _named_genome(0.75, 0.02, 0.75, 1, "outgoing", 5)
        registry_spec = LocalStudySpec(
            spec.cohort_id,
            "evolutionary-search.registry",
            spec.master_seed,
            spec.training_sources + spec.validation_sources,
            (placeholder,),
            (NOMINAL_COPY_NOISE, STRONG_COPY_NOISE),
            (LocalConditionSpec(f"{placeholder.name}.intact", placeholder.name, "intact", "nominal"),),
            checkpoint_generations=(0,),
            challenges=("forced_break",),
            futures_per_history=4,
            generation_cycles=spec.generation_cycles,
            horizon=spec.horizon,
            strict_run=spec.strict_run,
            stable_run=spec.stable_run,
            expression_flip_probability=spec.expression_flip_probability,
            exploratory=True,
        )
        registry = build_local_registry(registry_spec, progress)
        _atomic_json(registry_path, registry)
    sources = list(registry["sources"])
    training = sources[: spec.training_sources]
    validation_sources = sources[spec.training_sources :]
    checkpoint_path = destination / "checkpoint.json"
    if checkpoint_path.is_file():
        checkpoint = read_json(checkpoint_path)
        if checkpoint.get("protocol_digest") != registration["protocol_digest"]:
            raise ValueError("local search checkpoint protocol differs")
        population = tuple(
            LocalCarrierGenome(**value)
            for value in checkpoint.get("next_population", checkpoint["population"])
        )
        trace = list(checkpoint["trace"])
        generation_start = int(checkpoint["generation"]) + 1
    else:
        population = initial_population(spec)
        trace = []
        generation_start = 0
    for generation in range(generation_start, spec.generations + 1):
        panel_index = generation % (spec.training_sources // spec.rotating_panel_size)
        panel = training[
            panel_index * spec.rotating_panel_size : (panel_index + 1) * spec.rotating_panel_size
        ]
        scores = evaluate_population(
            spec,
            panel,
            population,
            spec.training_futures_per_history,
            f"generation-{generation:02d}",
            workers,
        )
        ranked = _rank(scores)
        trace.append(
            {
                "generation": generation,
                "panel_index": panel_index,
                "best": scores[ranked[0].name],
                "population_scores": scores,
            }
        )
        following = (
            _offspring(spec, tuple(ranked[:16]), generation + 1)
            if generation < spec.generations
            else population
        )
        _atomic_json(
            checkpoint_path,
            {
                "format": "gre-wagner-local-ph-search-checkpoint-v1",
                "protocol_digest": registration["protocol_digest"],
                "generation": generation,
                "population": [value.to_dict() for value in population],
                "next_population": [value.to_dict() for value in following],
                "trace": trace,
            },
        )
        if progress:
            progress(
                f"local search generation {generation}/{spec.generations}; "
                f"best risk={scores[ranked[0].name]['risk_gain']:.4f}"
            )
        if generation < spec.generations:
            population = following
    finalists = tuple(_rank(trace[-1]["population_scores"])[:16])
    validation = evaluate_population(
        spec,
        validation_sources,
        finalists,
        spec.validation_futures_per_history,
        "untouched-validation",
        workers,
    )
    selection = select_nominees(validation)
    _atomic_json(destination / "evolution-trace.json", {"format": LOCAL_PH_SEARCH_FORMAT, "generations": trace})
    _atomic_json(destination / "validation.json", validation)
    _atomic_json(destination / "selection.json", selection)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": LOCAL_PH_SEARCH_FORMAT,
            "protocol_digest": registration["protocol_digest"],
            "training_rulebooks": spec.training_sources,
            "validation_rulebooks": spec.validation_sources,
            "population_size": spec.population_size,
            "generations": spec.generations,
            "workers": workers,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_local_search(destination)
    return destination


def verify_local_search(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    if registration.get("format") != LOCAL_PH_SEARCH_FORMAT:
        raise ValueError("local search registration format mismatch")
    spec = LocalSearchSpec(**registration["protocol"])
    spec.validate()
    if canonical_digest(spec.to_dict()) != registration.get("protocol_digest"):
        raise ValueError("local search protocol digest mismatch")
    return {
        "verified": True,
        "checksums": len(checksums),
        "eligible": bool(read_json(directory / "selection.json")["eligible"]),
    }
