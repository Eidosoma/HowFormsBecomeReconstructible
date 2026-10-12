"""Prospective pilot for evolution of multigeneration carrier fidelity."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
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
from .lineage_carrier_config import (
    LINEAGE_EVOLUTION_FORMAT,
    LineageArmSpec,
    LineageEvolutionSpec,
    LineageSourceSpec,
    LineageStudySpec,
)
from .lineage_carrier_study import simulate_lineage_source
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_dynamics import (
    AttractorPair,
    balanced_midpoints,
    cue_nodes,
    forced_break_state,
    select_attractor_pair,
)
from .plastic_memory_evolution import _mutate, _recombine
from .rng import rng_for
from .wagner import WagnerRulebook


TREATMENTS = ("transmission_selection", "acute_performance", "neutral")
EVOLUTION_REGISTRATION_FORMAT = "gre-wagner-lineage-evolution-registration-v1"
EVOLUTION_MANIFEST_FORMAT = "gre-wagner-lineage-evolution-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _sample_founder(
    spec: LineageEvolutionSpec, population_id: str
) -> tuple[WagnerRulebook, AttractorPair, int, tuple[int, ...], tuple[int, ...]]:
    for proposal in range(100_000):
        rulebook = WagnerRulebook.random(
            spec.genes,
            rng_for(spec.master_seed, "lineage-evolution-founder", population_id, proposal),
        )
        viewed = MechanismRulebook(rulebook, "wagner_sequential")
        pair = select_attractor_pair(viewed.landscape(), spec.genes, 0.05, 0.40)
        if pair is None:
            continue
        ordering = tuple(
            int(value)
            for value in rng_for(
                spec.master_seed, "lineage-evolution-order", population_id
            ).permutation(spec.genes)
        )
        midpoint = balanced_midpoints(
            pair, spec.genes, np.asarray(ordering, dtype=int), 1
        )[0]
        nodes = cue_nodes(
            pair, spec.genes, spec.writer.cue_fraction, np.asarray(ordering, dtype=int)
        )
        return rulebook, pair, midpoint, nodes, ordering
    raise RuntimeError(f"could not sample lineage evolution founder: {population_id}")


def _bundle(
    rulebook: WagnerRulebook,
    pair: AttractorPair,
    midpoint: int,
    ordering: tuple[int, ...],
    source_id: str,
) -> dict[str, Any]:
    viewed = MechanismRulebook(rulebook, "wagner_sequential")
    landscape = viewed.landscape()
    metadata = {
        "pair": {
            "left_index": pair.left_index,
            "right_index": pair.right_index,
            "left_state": pair.left_state,
            "right_state": pair.right_state,
        },
        "midpoints": [midpoint],
        "node_order": list(ordering),
        "mark_permutation": list(ordering[1:] + ordering[:1]),
        "ablation_order": list(reversed(ordering)),
        "forced_breaks": {
            history: forced_break_state(
                landscape, pair.index(history), pair.state(history), rulebook.genes
            )
            for history in ("A", "B")
        },
        "landscape": landscape.to_dict(),
    }
    return {
        "source_set": "wagner_n10",
        "source_id": source_id,
        "engine": "wagner",
        "genes": rulebook.genes,
        "proposal_index": 0,
        "source": rulebook.to_dict(),
        "models": {"wagner.lineage": metadata},
    }


def _score(
    rulebook: WagnerRulebook,
    pair: AttractorPair,
    midpoint: int,
    ordering: tuple[int, ...],
    endpoint: str,
    spec: LineageEvolutionSpec,
    population_id: str,
    coordinate: tuple[Any, ...],
    replicates: int,
) -> float:
    if endpoint == "neutral":
        return 0.5
    generation = (
        8
        if endpoint == "generation_8_descendant_memory"
        else 4
        if endpoint == "generation_4_transmission"
        else 0
    )
    arm = (
        LineageArmSpec(
            f"selected-targeted-k{spec.bottleneck_k}",
            bottleneck="targeted",
            k=spec.bottleneck_k,
            primary=True,
        )
        if endpoint in {"generation_4_transmission", "generation_8_descendant_memory"}
        else LineageArmSpec("natural-full", primary=True)
    )
    study = LineageStudySpec(
        f"{spec.cohort_id}.{population_id}.{canonical_digest(coordinate)[:12]}",
        f"evolution-score.{endpoint}",
        spec.master_seed,
        (LineageSourceSpec("wagner", 1),),
        (spec.writer,),
        (replace(spec.carrier, engines=("wagner",)),),
        (arm,),
        (0,) if generation == 0 else (0, generation),
        ("forced_break",),
        replicates,
        midpoint_count=1,
        generation_cycles=spec.generation_cycles,
        horizon=spec.horizon,
        strict_run=spec.strict_run,
        stable_run=spec.stable_run,
        expression_flip_probability=spec.expression_flip_probability,
        neutral_damage_fraction=spec.neutral_damage_fraction,
        wagner_max_sweeps=spec.wagner_max_sweeps,
        bootstrap_repetitions=64,
        interval_level=spec.interval_level,
        exploratory=True,
    )
    source_id = f"{population_id}.{canonical_digest(coordinate)[:16]}"
    source = _bundle(rulebook, pair, midpoint, ordering, source_id)
    task = {
        "donor": source,
        "recipients": {
            "clone": {
                "source": source,
                "history_map": {"A": "A", "B": "B"},
            }
        },
    }
    records = simulate_lineage_source(task, study.to_dict())
    values = [
        float(record["correct_hold8"])
        for record in records
        if int(record["generation"]) == generation
    ]
    return float(np.mean(values)) if values else 0.0


def _selection_endpoint(treatment: str) -> str:
    return {
        "transmission_selection": "generation_4_transmission",
        "acute_performance": "generation_0_acute",
        "neutral": "neutral",
    }[treatment]


def _population_task(args: tuple[dict[str, Any], str, int, str, str]) -> dict[str, Any]:
    spec_value, treatment, population_index, output_text, protocol_digest = args
    spec = LineageEvolutionSpec.from_dict(spec_value)
    population_id = f"{treatment}.population-{population_index:03d}"
    output = Path(output_text)
    final_path = output / f"{population_id}.json"
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"lineage evolution population registration differs: {final_path}")
    checkpoint = output / f"{population_id}.checkpoint.json"
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        founder = WagnerRulebook.from_dict(saved["founder"])
        pair = AttractorPair(**saved["pair"])
        midpoint = int(saved["midpoint"])
        ordering = tuple(int(value) for value in saved["ordering"])
        population = [WagnerRulebook.from_dict(value) for value in saved["population"]]
        fitnesses = np.asarray(saved["fitnesses"], dtype=float)
        trace = list(saved["trace"])
        start_generation = int(saved["generation"]) + 1
    else:
        founder, pair, midpoint, _nodes, ordering = _sample_founder(spec, population_id)
        population = [founder]
        for index in range(1, spec.population_size):
            child = _mutate(
                founder,
                rng_for(spec.master_seed, "lineage-evolution-initial", population_id, index),
            )
            if not isinstance(child, WagnerRulebook):
                raise TypeError("lineage evolution mutation produced a non-Wagner child")
            population.append(child)
        endpoint = _selection_endpoint(treatment)
        fitnesses = np.asarray(
            [
                _score(
                    value,
                    pair,
                    midpoint,
                    ordering,
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
    endpoint = _selection_endpoint(treatment)
    for generation in range(start_generation, spec.generations + 1):
        following: list[WagnerRulebook] = []
        scores: list[float] = []
        proposal = 0
        maximum = spec.population_size * 100
        while len(following) < spec.population_size and proposal < maximum:
            rng = rng_for(
                spec.master_seed,
                "lineage-evolution-offspring",
                population_id,
                generation,
                proposal,
            )
            left = population[int(rng.integers(len(population)))]
            right = population[int(rng.integers(len(population)))]
            child = _mutate(_recombine(left, right, rng), rng)
            if not isinstance(child, WagnerRulebook):
                raise TypeError("lineage evolution produced a non-Wagner child")
            score = _score(
                child,
                pair,
                midpoint,
                ordering,
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
            raise RuntimeError(f"lineage evolution population stalled: {population_id}")
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
                "format": "gre-wagner-lineage-evolution-checkpoint-v1",
                "protocol_digest": protocol_digest,
                "generation": generation,
                "founder": founder.to_dict(),
                "pair": {
                    "left_index": pair.left_index,
                    "right_index": pair.right_index,
                    "left_state": pair.left_state,
                    "right_state": pair.right_state,
                },
                "midpoint": midpoint,
                "ordering": list(ordering),
                "population": [value.to_dict() for value in population],
                "fitnesses": fitnesses.tolist(),
                "trace": trace,
            },
        )
    selected_index = int(np.argmax(fitnesses))
    selected = population[selected_index]
    founder_assay = _score(
        founder,
        pair,
        midpoint,
        ordering,
        "generation_8_descendant_memory",
        spec,
        population_id,
        ("heldout", "founder"),
        spec.assay_replicates,
    )
    selected_assay = _score(
        selected,
        pair,
        midpoint,
        ordering,
        "generation_8_descendant_memory",
        spec,
        population_id,
        ("heldout", "selected"),
        spec.assay_replicates,
    )
    parent_offspring_pairs: list[dict[str, float]] = []
    if treatment == "transmission_selection":
        for offspring_index in range(spec.heritability_offspring):
            offspring_rng = rng_for(
                spec.master_seed,
                "lineage-evolution-heritability-offspring",
                population_id,
                offspring_index,
            )
            offspring = _mutate(selected, offspring_rng)
            if not isinstance(offspring, WagnerRulebook):
                raise TypeError("lineage heritability assay produced a non-Wagner child")
            assay_coordinate = ("heritability", offspring_index)
            parent_value = _score(
                selected,
                pair,
                midpoint,
                ordering,
                "generation_8_descendant_memory",
                spec,
                population_id,
                assay_coordinate,
                spec.assay_replicates,
            )
            offspring_value = _score(
                offspring,
                pair,
                midpoint,
                ordering,
                "generation_8_descendant_memory",
                spec,
                population_id,
                assay_coordinate,
                spec.assay_replicates,
            )
            parent_offspring_pairs.append(
                {"parent": parent_value, "offspring": offspring_value}
            )
    result = {
        "format": "gre-wagner-lineage-evolution-population-v1",
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "population_index": population_index,
        "treatment": treatment,
        "selection_endpoint": endpoint,
        "heldout_endpoint": "generation_8_descendant_memory",
        "founder_heldout": founder_assay,
        "selected_heldout": selected_assay,
        "improvement": selected_assay - founder_assay,
        "parent_offspring_pairs": parent_offspring_pairs,
        "founder": founder.to_dict(),
        "selected": selected.to_dict(),
        "trace": trace,
    }
    _atomic_json(final_path, result)
    if checkpoint.is_file():
        checkpoint.unlink()
    return result


def _difference_interval(
    left: list[float], right: list[float], spec: LineageEvolutionSpec, label: str
) -> dict[str, Any]:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if not a.size or not b.size:
        return {"mean": None, "interval": [None, None], "lower": None}
    rng = rng_for(spec.master_seed, "lineage-evolution-bootstrap", label)
    repetitions = spec.bootstrap_repetitions
    draws = np.mean(a[rng.integers(0, a.size, (repetitions, a.size))], axis=1) - np.mean(
        b[rng.integers(0, b.size, (repetitions, b.size))], axis=1
    )
    tail = (1.0 - spec.interval_level) / 4.0
    return {
        "mean": float(np.mean(a) - np.mean(b)),
        "interval": [float(np.quantile(draws, tail)), float(np.quantile(draws, 1.0 - tail))],
        "lower": float(np.quantile(draws, 2.0 * tail)),
    }


def _correlation_interval(
    parent: list[float], offspring: list[float], spec: LineageEvolutionSpec
) -> dict[str, Any]:
    """Paired population bootstrap for the parent-offspring association."""

    a = np.asarray(parent, dtype=float)
    b = np.asarray(offspring, dtype=float)
    if a.size < 3 or b.size != a.size or not np.std(a) or not np.std(b):
        return {"mean": None, "interval": [None, None], "lower": None, "pairs": int(a.size)}
    point = float(np.corrcoef(a, b)[0, 1])
    rng = rng_for(spec.master_seed, "lineage-evolution-bootstrap", "parent-offspring")
    draws: list[float] = []
    for _ in range(spec.bootstrap_repetitions):
        indices = rng.integers(0, a.size, a.size)
        left = a[indices]
        right = b[indices]
        if float(np.std(left)) == 0.0 or float(np.std(right)) == 0.0:
            continue
        draws.append(float(np.corrcoef(left, right)[0, 1]))
    if not draws:
        return {"mean": point, "interval": [None, None], "lower": None, "pairs": int(a.size)}
    sampled = np.asarray(draws, dtype=float)
    tail = (1.0 - spec.interval_level) / 2.0
    return {
        "mean": point,
        "interval": [
            float(np.quantile(sampled, tail)),
            float(np.quantile(sampled, 1.0 - tail)),
        ],
        "lower": float(np.quantile(sampled, tail)),
        "pairs": int(a.size),
    }


def analyze_lineage_evolution(
    results: list[dict[str, Any]], spec: LineageEvolutionSpec
) -> dict[str, Any]:
    grouped = {
        treatment: [
            float(value["improvement"])
            for value in results
            if value["treatment"] == treatment
        ]
        for treatment in TREATMENTS
    }
    contrasts = {
        control: _difference_interval(
            grouped["transmission_selection"], grouped[control], spec, control
        )
        for control in ("acute_performance", "neutral")
    }
    heritability_pairs = []
    for value in results:
        if value["treatment"] != "transmission_selection":
            continue
        within_population = value.get("parent_offspring_pairs", [])
        if not within_population:
            continue
        heritability_pairs.append(
            {
                "parent": float(
                    np.mean([float(pair["parent"]) for pair in within_population])
                ),
                "offspring": float(
                    np.mean([float(pair["offspring"]) for pair in within_population])
                ),
            }
        )
    association = _correlation_interval(
        [float(value["parent"]) for value in heritability_pairs],
        [float(value["offspring"]) for value in heritability_pairs],
        spec,
    )
    criteria = {
        f"improvement_over_{control}_at_least_0_05": contrast["mean"] is not None
        and float(contrast["mean"]) >= 0.05
        for control, contrast in contrasts.items()
    }
    criteria.update(
        {
            f"improvement_over_{control}_lower_above_zero": contrast["lower"] is not None
            and float(contrast["lower"]) > 0.0
            for control, contrast in contrasts.items()
        }
    )
    criteria["parent_offspring_association_lower_above_zero"] = (
        association["lower"] is not None and float(association["lower"]) > 0.0
    )
    return {
        "format": "gre-wagner-lineage-evolution-analysis-v1",
        "cohort_id": spec.cohort_id,
        "exploratory": True,
        "population_count": len(results),
        "treatments": {key: {"mean_improvement": float(np.mean(value))} for key, value in grouped.items()},
        "contrasts": contrasts,
        "parent_offspring_association": association,
        "criteria": criteria,
        "passed": all(criteria.values()),
        "claim_boundary": "exploratory evolvability only; fresh replication required",
    }


def run_lineage_evolution(
    spec: LineageEvolutionSpec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("lineage evolution requires 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_lineage_evolution(destination)
        return destination
    started = time.monotonic()
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": EVOLUTION_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing lineage evolution registration differs")
    else:
        _atomic_json(registration_path, registration)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    tasks = [
        (spec.to_dict(), treatment, index, str(populations), digest)
        for treatment in TREATMENTS
        for index in range(spec.populations_per_treatment)
    ]
    results: list[dict[str, Any]] = []
    if workers == 1:
        iterator = map(_population_task, tasks)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        iterator = executor.map(_population_task, tasks)
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-lineage-evolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress is not None:
                progress(f"lineage evolution {index}/{len(tasks)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    analysis = analyze_lineage_evolution(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": EVOLUTION_MANIFEST_FORMAT,
            "protocol_format": LINEAGE_EVOLUTION_FORMAT,
            "protocol_digest": digest,
            "population_count": len(results),
            "expected_population_count": len(tasks),
            "elapsed_seconds": time.monotonic() - started,
            "workers": workers,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_lineage_evolution(destination)
    return destination


def verify_lineage_evolution(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != EVOLUTION_REGISTRATION_FORMAT:
        raise ValueError("lineage evolution registration format mismatch")
    if manifest.get("format") != EVOLUTION_MANIFEST_FORMAT:
        raise ValueError("lineage evolution manifest format mismatch")
    spec = LineageEvolutionSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get("protocol_digest"):
        raise ValueError("lineage evolution protocol digest mismatch")
    expected = len(TREATMENTS) * spec.populations_per_treatment
    if int(manifest["population_count"]) != expected:
        raise ValueError("lineage evolution population count mismatch")
    return {"verified": True, "files": len(checksums), "populations": expected, "protocol_digest": digest}
