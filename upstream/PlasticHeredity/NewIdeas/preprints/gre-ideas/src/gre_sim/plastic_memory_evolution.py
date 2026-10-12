"""Checkpointed exploratory and confirmatory evolution of memory capacity."""

from __future__ import annotations

import concurrent.futures
import math
import multiprocessing
import time
from dataclasses import asdict, dataclass
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
from .boolean import BooleanRulebook, mutate_boolean, recombine_boolean
from .engines import Rulebook, rulebook_from_dict
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_config import CueDose, MarkSetting
from .plastic_memory_dynamics import (
    AttractorPair,
    balanced_midpoints,
    cue_nodes,
    damage_state,
    develop_memory_cycle,
    select_attractor_pair,
)
from .plastic_memory_protocols import EVOLUTION_SEED
from .rng import rng_for
from .wagner import WagnerRulebook, mutate_wagner, recombine_wagner


EVOLUTION_TREATMENTS = ("memory_selection", "cue_performance_sham", "neutral")


@dataclass(frozen=True)
class MemoryEvolutionCell:
    name: str
    engine: str
    variant: str
    gamma_variance: float
    carrier: str
    cue: CueDose
    mark: MarkSetting
    treatment: str

    def validate(self) -> None:
        if self.engine not in {"boolean", "wagner"}:
            raise ValueError("unknown memory-evolution engine")
        if not self.variant.startswith(self.engine):
            raise ValueError("memory-evolution engine and variant disagree")
        if self.carrier not in {"state", "slow_mark"}:
            raise ValueError("unknown memory-evolution carrier")
        if self.treatment not in EVOLUTION_TREATMENTS:
            raise ValueError("unknown memory-evolution treatment")
        self.cue.validate()
        self.mark.validate()


@dataclass(frozen=True)
class MemoryEvolutionSpec:
    cohort_id: str
    master_seed: str
    cells: tuple[MemoryEvolutionCell, ...]
    populations_per_cell: int
    population_size: int
    generations: int
    training_replicates: int
    selection_replicates: int
    heldout_replicates: int
    post_horizon: int = 12
    hold_run: int = 4
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    maximum_founder_proposals: int = 100_000
    maximum_offspring_factor: int = 100
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32 or not self.cells:
            raise ValueError("invalid memory-evolution identity")
        for cell in self.cells:
            cell.validate()
        names = [cell.name for cell in self.cells]
        if len(names) != len(set(names)):
            raise ValueError("memory-evolution cell names must be unique")
        for value in (
            self.populations_per_cell,
            self.population_size,
            self.generations,
            self.training_replicates,
            self.selection_replicates,
            self.heldout_replicates,
            self.post_horizon,
            self.hold_run,
        ):
            if value < 1:
                raise ValueError("memory-evolution counts must be positive")
        if self.post_horizon < self.hold_run:
            raise ValueError("memory-evolution horizon cannot certify hold run")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MemoryEvolutionSpec":
        fields = dict(value)
        cells = []
        for item in fields["cells"]:
            if isinstance(item, MemoryEvolutionCell):
                cells.append(item)
                continue
            cell = dict(item)
            cell["cue"] = cell["cue"] if isinstance(cell["cue"], CueDose) else CueDose(**cell["cue"])
            cell["mark"] = (
                cell["mark"]
                if isinstance(cell["mark"], MarkSetting)
                else MarkSetting(**cell["mark"])
            )
            cells.append(MemoryEvolutionCell(**cell))
        fields["cells"] = tuple(cells)
        result = cls(**fields)
        result.validate()
        return result


def exploratory_evolution_spec(cues: dict[str, CueDose]) -> MemoryEvolutionSpec:
    cells = []
    mark = MarkSetting("half-8.mu-0.25", 8, 0.25)
    no_mark = MarkSetting("none", 0, 0.0)
    for engine, model, variant, variance in (
        ("boolean", "boolean-primary", "boolean_sync", 0.0),
        ("wagner", "wagner-primary", "wagner_sequential", 0.10),
    ):
        for carrier, setting in (("state", no_mark), ("slow_mark", mark)):
            for treatment in EVOLUTION_TREATMENTS:
                cells.append(
                    MemoryEvolutionCell(
                        f"{engine}.{carrier}.{treatment}",
                        engine,
                        variant,
                        variance,
                        carrier,
                        cues[model],
                        setting,
                        treatment,
                    )
                )
    return MemoryEvolutionSpec(
        "plastic-memory-v1-evolution-exploratory",
        EVOLUTION_SEED,
        tuple(cells),
        populations_per_cell=32,
        population_size=64,
        generations=100,
        training_replicates=4,
        selection_replicates=32,
        heldout_replicates=128,
        exploratory=True,
    )


def confirmatory_evolution_spec(
    cues: dict[str, CueDose],
    confirmed: tuple[tuple[str, str, MarkSetting], ...],
) -> MemoryEvolutionSpec:
    cells = []
    for model, carrier, mark in confirmed:
        engine = "boolean" if model.startswith("boolean") else "wagner"
        variant = "boolean_sync" if engine == "boolean" else "wagner_sequential"
        variance = 0.0 if engine == "boolean" else 0.10
        for treatment in EVOLUTION_TREATMENTS:
            cells.append(
                MemoryEvolutionCell(
                    f"{engine}.{carrier}.{treatment}",
                    engine,
                    variant,
                    variance,
                    carrier,
                    cues[model],
                    mark,
                    treatment,
                )
            )
    return MemoryEvolutionSpec(
        "plastic-memory-v1-evolution-confirmation",
        "a564436a35eb12447927f3f3a6f1020902d55369457524c482cb597032a7a5de",
        tuple(cells),
        populations_per_cell=64,
        population_size=128,
        generations=200,
        training_replicates=4,
        selection_replicates=32,
        heldout_replicates=128,
        exploratory=False,
    )


def quick_evolution_spec() -> MemoryEvolutionSpec:
    cue = CueDose(1.0, 1)
    cells = tuple(
        MemoryEvolutionCell(
            f"boolean.state.{treatment}",
            "boolean",
            "boolean_sync",
            0.0,
            "state",
            cue,
            MarkSetting("none", 0, 0.0),
            treatment,
        )
        for treatment in EVOLUTION_TREATMENTS
    )
    return MemoryEvolutionSpec(
        "plastic-memory-evolution-quick",
        "51bd733486f2320be197456e36374c65a94e532d1b04b12b09e9c4af0cb1e819",
        cells,
        1,
        4,
        2,
        1,
        2,
        4,
        post_horizon=4,
        hold_run=2,
        maximum_founder_proposals=10_000,
        maximum_offspring_factor=20,
        exploratory=True,
    )


def _random_rulebook(engine: str, genes: int, rng: np.random.Generator) -> Rulebook:
    return BooleanRulebook.random(genes, rng) if engine == "boolean" else WagnerRulebook.random(genes, rng)


def _mutate(rulebook: Rulebook, rng: np.random.Generator) -> Rulebook:
    if isinstance(rulebook, BooleanRulebook):
        return mutate_boolean(rulebook, rng)
    return mutate_wagner(rulebook, rng)


def _recombine(left: Rulebook, right: Rulebook, rng: np.random.Generator) -> Rulebook:
    if isinstance(left, BooleanRulebook) and isinstance(right, BooleanRulebook):
        return recombine_boolean(left, right, rng)
    if isinstance(left, WagnerRulebook) and isinstance(right, WagnerRulebook):
        return recombine_wagner(left, right, rng)
    raise TypeError("memory-evolution parents must share an engine")


def _sample_founder(
    spec: MemoryEvolutionSpec, cell: MemoryEvolutionCell, population_id: str
) -> tuple[Rulebook, AttractorPair, int, tuple[int, ...]]:
    genes = 10 if not spec.cohort_id.endswith("quick") else 4
    for proposal in range(spec.maximum_founder_proposals):
        candidate = _random_rulebook(
            cell.engine,
            genes,
            rng_for(spec.master_seed, "memory-evolution-founder", population_id, proposal),
        )
        viewed = MechanismRulebook(candidate, cell.variant)
        pair = select_attractor_pair(viewed.landscape(), genes, 0.05 if genes == 10 else 0.0, 0.40 if genes == 10 else 0.25)
        if pair is None:
            continue
        ordering = rng_for(spec.master_seed, "memory-evolution-order", population_id).permutation(genes)
        midpoint = balanced_midpoints(pair, genes, ordering, 1)[0]
        nodes = cue_nodes(pair, genes, cell.cue.fraction, ordering)
        return candidate, pair, midpoint, nodes
    raise RuntimeError(f"could not sample memory-evolution founder for {population_id}")


def _score_rulebook(
    rulebook: Rulebook,
    pair: AttractorPair,
    midpoint: int,
    nodes: tuple[int, ...],
    cell: MemoryEvolutionCell,
    spec: MemoryEvolutionSpec,
    population_id: str,
    coordinate: tuple[Any, ...],
    replicates: int,
) -> float:
    if cell.treatment == "neutral":
        return 0.5
    viewed = MechanismRulebook(rulebook, cell.variant)
    successes = []
    for history in ("A", "B"):
        target = pair.state(history)
        for replicate in range(replicates):
            state = midpoint
            mark = np.zeros(viewed.genes, dtype=float)
            training_states = []
            for cycle in range(cell.cue.dwell):
                base_parts = (
                    spec.master_seed,
                    "memory-evolution-score",
                    population_id,
                    *coordinate,
                    history,
                    replicate,
                    "train",
                    cycle,
                )
                value = develop_memory_cycle(
                    viewed,
                    state,
                    midpoint,
                    mark,
                    1.0,
                    spec.expression_flip_probability,
                    cell.mark.rho,
                    cell.mark.coupling,
                    cell.gamma_variance,
                    100,
                    rng_for(*base_parts, "carry"),
                    rng_for(*base_parts, "mark"),
                    rng_for(*base_parts, "dynamics"),
                    cue_target=target,
                    clamped_nodes=nodes,
                    write_mark=cell.mark.active,
                )
                state = value.state
                mark = np.asarray(value.mark, dtype=float)
                training_states.append(state)
            if cell.treatment == "cue_performance_sham":
                successes.append(float(bool(training_states and training_states[-1] == target)))
                continue
            if cell.carrier == "state":
                mark = np.zeros(viewed.genes, dtype=float)
            else:
                state = midpoint
            damage_rng = rng_for(
                spec.master_seed,
                "memory-evolution-score",
                population_id,
                *coordinate,
                history,
                replicate,
                "damage",
            )
            state, _ = damage_state(
                state, viewed.genes, spec.neutral_damage_fraction, damage_rng
            )
            run = 0
            maximum = 0
            for cycle in range(spec.post_horizon):
                base_parts = (
                    spec.master_seed,
                    "memory-evolution-score",
                    population_id,
                    *coordinate,
                    history,
                    replicate,
                    "post",
                    cycle,
                )
                value = develop_memory_cycle(
                    viewed,
                    state,
                    midpoint,
                    mark,
                    1.0,
                    spec.expression_flip_probability,
                    cell.mark.rho,
                    cell.mark.coupling if cell.carrier == "slow_mark" else 0.0,
                    cell.gamma_variance,
                    100,
                    rng_for(*base_parts, "carry"),
                    rng_for(*base_parts, "mark"),
                    rng_for(*base_parts, "dynamics"),
                    write_mark=cell.carrier == "slow_mark",
                )
                state = value.state
                mark = np.asarray(value.mark, dtype=float)
                run = run + 1 if value.status == "point" and state == target else 0
                maximum = max(maximum, run)
            successes.append(float(maximum >= spec.hold_run))
    return float(np.mean(successes))


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _population_task(args: tuple[dict[str, Any], dict[str, Any], int, str]) -> dict[str, Any]:
    spec_value, cell_value, population_index, directory_text = args
    spec = MemoryEvolutionSpec.from_dict(spec_value)
    cell = MemoryEvolutionCell(
        **{
            **cell_value,
            "cue": CueDose(**cell_value["cue"]),
            "mark": MarkSetting(**cell_value["mark"]),
        }
    )
    population_id = f"{cell.name}.population-{population_index:03d}"
    directory = Path(directory_text)
    final_path = directory / f"{population_id}.json"
    if final_path.is_file():
        return read_json(final_path)
    checkpoint = directory / f"{population_id}.checkpoint.json"
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        founder = rulebook_from_dict(saved["founder"])
        pair = AttractorPair(**saved["pair"])
        midpoint = int(saved["midpoint"])
        nodes = tuple(int(value) for value in saved["nodes"])
        population = [rulebook_from_dict(value) for value in saved["population"]]
        fitnesses = np.asarray(saved["fitnesses"], dtype=float)
        trace = list(saved["trace"])
        start_generation = int(saved["generation"]) + 1
    else:
        founder, pair, midpoint, nodes = _sample_founder(spec, cell, population_id)
        population = [founder]
        for index in range(1, spec.population_size):
            population.append(
                _mutate(
                    founder,
                    rng_for(spec.master_seed, "memory-evolution-initial", population_id, index),
                )
            )
        fitnesses = np.asarray(
            [
                _score_rulebook(
                    rulebook,
                    pair,
                    midpoint,
                    nodes,
                    cell,
                    spec,
                    population_id,
                    ("initial", index),
                    spec.training_replicates,
                )
                for index, rulebook in enumerate(population)
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
    for generation in range(start_generation, spec.generations + 1):
        following: list[Rulebook] = []
        scores: list[float] = []
        proposal = 0
        maximum = spec.population_size * spec.maximum_offspring_factor
        while len(following) < spec.population_size and proposal < maximum:
            rng = rng_for(
                spec.master_seed,
                "memory-evolution-offspring",
                population_id,
                generation,
                proposal,
            )
            left = population[int(rng.integers(len(population)))]
            right = population[int(rng.integers(len(population)))]
            child = _mutate(_recombine(left, right, rng), rng)
            score = _score_rulebook(
                child,
                pair,
                midpoint,
                nodes,
                cell,
                spec,
                population_id,
                ("generation", generation, proposal),
                spec.training_replicates,
            )
            proposal += 1
            acceptance = 1.0 if cell.treatment == "neutral" else 0.05 + 0.95 * score
            if rng.random() <= acceptance:
                following.append(child)
                scores.append(score)
        if len(following) != spec.population_size:
            raise RuntimeError(
                f"{population_id} filled only {len(following)}/{spec.population_size} "
                f"offspring in generation {generation}"
            )
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
                "format": "gre-plastic-memory-evolution-checkpoint-v1",
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
            _score_rulebook(
                rulebook,
                pair,
                midpoint,
                nodes,
                cell,
                spec,
                population_id,
                ("selection", index),
                spec.selection_replicates,
            )
            for index, rulebook in enumerate(population)
        ]
    )
    selected_index = int(np.argmax(selection_scores))
    selected = population[selected_index]
    founder_score = _score_rulebook(
        founder,
        pair,
        midpoint,
        nodes,
        cell,
        spec,
        population_id,
        ("heldout-founder",),
        spec.heldout_replicates,
    )
    heldout_score = _score_rulebook(
        selected,
        pair,
        midpoint,
        nodes,
        cell,
        spec,
        population_id,
        ("heldout-selected",),
        spec.heldout_replicates,
    )
    parent_values = []
    offspring_values = []
    sample_count = min(32, len(population))
    for index in range(sample_count):
        parent = population[index]
        child = _mutate(
            parent,
            rng_for(spec.master_seed, "memory-evolution-breeding", population_id, index),
        )
        parent_values.append(float(selection_scores[index]))
        offspring_values.append(
            _score_rulebook(
                child,
                pair,
                midpoint,
                nodes,
                cell,
                spec,
                population_id,
                ("breeding", index),
                spec.selection_replicates,
            )
        )
    breeding = (
        float(np.corrcoef(parent_values, offspring_values)[0, 1])
        if np.std(parent_values) > 0 and np.std(offspring_values) > 0
        else 0.0
    )
    result = {
        "format": "gre-plastic-memory-evolution-population-v1",
        "population_id": population_id,
        "cell": asdict(cell),
        "population_index": population_index,
        "founder": founder.to_dict(),
        "selected": selected.to_dict(),
        "pair": asdict(pair),
        "midpoint": midpoint,
        "nodes": list(nodes),
        "founder_heldout_score": founder_score,
        "selected_heldout_score": heldout_score,
        "heldout_change": heldout_score - founder_score,
        "breeding_value_correlation": breeding,
        "trace": trace,
    }
    _atomic_json(final_path, result)
    return result


def _analyze_evolution(results: list[dict[str, Any]], spec: MemoryEvolutionSpec) -> dict[str, Any]:
    cells: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        cells.setdefault(result["cell"]["name"], []).append(result)
    summaries = {}
    for name, values in cells.items():
        changes = np.asarray([value["heldout_change"] for value in values], dtype=float)
        breeding = np.asarray([value["breeding_value_correlation"] for value in values], dtype=float)
        summaries[name] = {
            "populations": len(values),
            "mean_heldout_change": float(np.mean(changes)),
            "mean_breeding_value_correlation": float(np.mean(breeding)),
            "positive_changes": int(np.sum(changes > 0)),
        }
    contrasts = {}
    response_gates: dict[str, Any] = {}
    groups = sorted({(value["cell"]["engine"], value["cell"]["carrier"]) for value in results})
    for engine, carrier in groups:
        by_treatment = {
            treatment: np.asarray(
                [
                    value["heldout_change"]
                    for value in results
                    if value["cell"]["engine"] == engine
                    and value["cell"]["carrier"] == carrier
                    and value["cell"]["treatment"] == treatment
                ],
                dtype=float,
            )
            for treatment in EVOLUTION_TREATMENTS
        }
        breeding_by_treatment = {
            treatment: np.asarray(
                [
                    value["breeding_value_correlation"]
                    for value in results
                    if value["cell"]["engine"] == engine
                    and value["cell"]["carrier"] == carrier
                    and value["cell"]["treatment"] == treatment
                ],
                dtype=float,
            )
            for treatment in EVOLUTION_TREATMENTS
        }
        if any(array.size == 0 for array in by_treatment.values()):
            continue
        group_contrasts: dict[str, Any] = {}
        for control in ("cue_performance_sham", "neutral"):
            observed = float(
                np.mean(by_treatment["memory_selection"]) - np.mean(by_treatment[control])
            )
            rng = rng_for(spec.master_seed, "memory-evolution-bootstrap", engine, carrier, control)
            boot = []
            for _ in range(4096 if not spec.exploratory else 1024):
                left = rng.choice(by_treatment["memory_selection"], size=len(by_treatment["memory_selection"]), replace=True)
                right = rng.choice(by_treatment[control], size=len(by_treatment[control]), replace=True)
                boot.append(float(np.mean(left) - np.mean(right)))
            value = {
                "mean": observed,
                "interval": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
                "lower": float(np.quantile(boot, 0.025 / 2)),
            }
            contrasts[f"{engine}.{carrier}.memory-minus-{control}"] = value
            group_contrasts[control] = value
        memory_breeding = breeding_by_treatment["memory_selection"]
        breeding_rng = rng_for(
            spec.master_seed, "memory-evolution-breeding-bootstrap", engine, carrier
        )
        repetitions = 4096 if not spec.exploratory else 1024
        breeding_boot = [
            float(
                np.mean(
                    breeding_rng.choice(
                        memory_breeding,
                        size=len(memory_breeding),
                        replace=True,
                    )
                )
            )
            for _ in range(repetitions)
        ]
        breeding_summary = {
            "mean": float(np.mean(memory_breeding)),
            "interval": [
                float(np.quantile(breeding_boot, 0.025)),
                float(np.quantile(breeding_boot, 0.975)),
            ],
            "lower": float(np.quantile(breeding_boot, 0.025)),
        }
        criteria = {
            "memory_exceeds_cue_performance_sham": (
                group_contrasts["cue_performance_sham"]["mean"] > 0.0
                and group_contrasts["cue_performance_sham"]["lower"] > 0.0
            ),
            "memory_exceeds_neutral": (
                group_contrasts["neutral"]["mean"] > 0.0
                and group_contrasts["neutral"]["lower"] > 0.0
            ),
            "positive_breeding_value_association": (
                breeding_summary["mean"] > 0.0
                and breeding_summary["lower"] > 0.0
            ),
        }
        response_gates[f"{engine}.{carrier}"] = {
            "contrasts": group_contrasts,
            "breeding_value_correlation": breeding_summary,
            "criteria": criteria,
            "passed": all(criteria.values()),
        }
    return {
        "format": "gre-plastic-memory-evolution-analysis-v1",
        "cohort_id": spec.cohort_id,
        "exploratory": spec.exploratory,
        "cells": summaries,
        "contrasts": contrasts,
        "response_gates": response_gates,
    }


def run_memory_evolution(
    spec: MemoryEvolutionSpec,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    destination = destination.resolve()
    if (destination / "SHA256SUMS").is_file():
        verify_checksums(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    registration = {
        "format": "gre-plastic-memory-evolution-registration-v1",
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if canonical_digest(read_json(registration_path)) != canonical_digest(
            registration
        ):
            raise ValueError("existing memory-evolution registration differs")
    else:
        _atomic_json(registration_path, registration)
    tasks = [
        (spec.to_dict(), asdict(cell), index, str(populations))
        for cell in spec.cells
        for index in range(spec.populations_per_cell)
    ]
    started = time.monotonic()
    progress_path = destination / "progress.json"
    prior_elapsed = 0.0
    if progress_path.is_file():
        try:
            prior_elapsed = max(
                0.0, float(read_json(progress_path).get("elapsed_seconds", 0.0))
            )
        except (OSError, ValueError, TypeError):
            prior_elapsed = 0.0
    results = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        futures = [executor.submit(_population_task, task) for task in tasks]
        for index, future in enumerate(futures, start=1):
            results.append(future.result())
            elapsed_now = prior_elapsed + time.monotonic() - started
            populations_per_second = index / max(elapsed_now, 1e-9)
            _atomic_json(
                progress_path,
                {
                    "format": "gre-plastic-memory-evolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed_now,
                    "populations_per_second": populations_per_second,
                    "eta_seconds": (
                        (len(tasks) - index) / populations_per_second
                        if populations_per_second > 0
                        else None
                    ),
                },
            )
            if progress is not None:
                progress(f"completed memory-evolution population {index}/{len(tasks)}")
    analysis = _analyze_evolution(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    manifest = {
        "format": "gre-plastic-memory-evolution-manifest-v1",
        "completed": True,
        "populations": len(results),
        "elapsed_seconds": prior_elapsed + time.monotonic() - started,
        "workers": workers,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "manifest.json", manifest)
    lines = [
        "# Evolution of plastic-memory capacity",
        "",
        "> Exploratory." if spec.exploratory else "> Untouched evolutionary confirmation.",
        "",
        f"- Populations: {len(results)}",
        f"- Runtime: {manifest['elapsed_seconds'] / 3600:.2f} h",
        "",
        "## Held-out treatment contrasts",
        "",
    ]
    for name, value in analysis["contrasts"].items():
        lines.append(f"- `{name}`: {value['mean']:+.4f} {value['interval']}")
    lines.extend(("", "## Evolvability gates", ""))
    for name, value in analysis["response_gates"].items():
        lines.append(f"- `{name}`: {'PASS' if value['passed'] else 'fail'}")
    (destination / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_checksums(destination)
    return destination
