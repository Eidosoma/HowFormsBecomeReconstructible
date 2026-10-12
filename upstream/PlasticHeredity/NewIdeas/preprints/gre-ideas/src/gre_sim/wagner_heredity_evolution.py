"""Checkpointed evolution of rescue-writer heredity capacity."""

from __future__ import annotations

import concurrent.futures
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
from .endpoints import apply_carryover
from .engines import rulebook_from_dict
from .mechanism_dynamics import MechanismRulebook
from .plastic_memory_config import MarkSetting
from .plastic_memory_dynamics import (
    AttractorPair,
    apply_mark_bias,
    balanced_midpoints,
    damage_state,
    develop_memory_cycle,
    select_attractor_pair,
    update_mark,
)
from .plastic_memory_evolution import (
    _analyze_evolution,
    _mutate,
    _recombine,
)
from .rng import rng_for
from .wagner import WagnerRulebook
from .wagner_heredity_config import HeredityWriterSpec
from .wagner_rescue_config import CueIntervention
from .wagner_rescue_dynamics import develop_with_intervention, intervention_nodes


EVOLUTION_TREATMENTS = ("memory_selection", "cue_performance_sham", "neutral")
EVOLUTION_EXPLORATORY_SEED = (
    "d0cff0a551e206e7be2c9059f3a9101813c7723b4859a12d2b9361f5c1a9f6a0"
)
EVOLUTION_CONFIRMATION_SEED = (
    "82fdf5354318d9bd8a5c3b36309c9b3fed97166df7a3908cac22c58957342e56"
)


@dataclass(frozen=True)
class HeredityEvolutionCell:
    name: str
    writer: HeredityWriterSpec
    carrier: str
    mark: MarkSetting
    treatment: str
    engine: str = "wagner"
    variant: str = "wagner_sequential"

    @property
    def gamma_variance(self) -> float:
        return self.writer.gamma_variance

    def validate(self) -> None:
        self.writer.validate()
        self.mark.validate()
        if self.carrier not in {"state", "slow_mark"}:
            raise ValueError("unknown heredity-evolution carrier")
        if self.treatment not in EVOLUTION_TREATMENTS:
            raise ValueError("unknown heredity-evolution treatment")
        if self.engine != "wagner" or self.variant != "wagner_sequential":
            raise ValueError("heredity evolution requires sequential Wagner")
        if self.carrier == "state" and self.mark.active:
            raise ValueError("state evolution must use the inactive mark")
        if self.carrier == "slow_mark" and not self.mark.active:
            raise ValueError("slow-mark evolution requires an active mark")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "HeredityEvolutionCell":
        fields = dict(value)
        fields.pop("gamma_variance", None)
        writer = fields["writer"]
        if not isinstance(writer, HeredityWriterSpec):
            writer = dict(writer)
            intervention = writer["intervention"]
            writer["intervention"] = (
                intervention
                if isinstance(intervention, CueIntervention)
                else CueIntervention(**intervention)
            )
            fields["writer"] = HeredityWriterSpec(**writer)
        mark = fields["mark"]
        fields["mark"] = mark if isinstance(mark, MarkSetting) else MarkSetting(**mark)
        return cls(**fields)


@dataclass(frozen=True)
class HeredityEvolutionSpec:
    cohort_id: str
    master_seed: str
    parent_candidate_digest: str
    cells: tuple[HeredityEvolutionCell, ...]
    populations_per_cell: int
    population_size: int
    generations: int
    training_replicates: int
    selection_replicates: int
    heldout_replicates: int
    genes: int = 10
    descendant_age: int = 1
    post_horizon: int = 12
    hold_run: int = 4
    expression_flip_probability: float = 0.05
    neutral_damage_fraction: float = 0.20
    maximum_founder_proposals: int = 100_000
    maximum_offspring_factor: int = 100
    exploratory: bool = True

    def validate(self) -> None:
        if not self.cohort_id or len(self.master_seed) < 32:
            raise ValueError("invalid heredity-evolution identity")
        if len(self.parent_candidate_digest) != 64 or not self.cells:
            raise ValueError("invalid heredity-evolution parent or cells")
        for cell in self.cells:
            cell.validate()
        if len({cell.name for cell in self.cells}) != len(self.cells):
            raise ValueError("heredity-evolution cell names must be unique")
        for value in (
            self.populations_per_cell,
            self.population_size,
            self.generations,
            self.training_replicates,
            self.selection_replicates,
            self.heldout_replicates,
            self.genes,
            self.descendant_age,
            self.post_horizon,
            self.hold_run,
        ):
            if value < 1:
                raise ValueError("heredity-evolution counts must be positive")
        if self.post_horizon < self.hold_run:
            raise ValueError("heredity-evolution horizon cannot certify hold run")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "HeredityEvolutionSpec":
        fields = dict(value)
        fields["cells"] = tuple(
            item
            if isinstance(item, HeredityEvolutionCell)
            else HeredityEvolutionCell.from_dict(item)
            for item in fields["cells"]
        )
        result = cls(**fields)
        result.validate()
        return result


def _cells(
    writer: HeredityWriterSpec,
    mark: MarkSetting | None,
) -> tuple[HeredityEvolutionCell, ...]:
    carriers = [("state", MarkSetting("none", 0, 0.0))]
    if mark is not None:
        carriers.append(("slow_mark", mark))
    return tuple(
        HeredityEvolutionCell(
            f"{writer.name}.{carrier}.{treatment}",
            writer,
            carrier,
            setting,
            treatment,
        )
        for carrier, setting in carriers
        for treatment in EVOLUTION_TREATMENTS
    )


def exploratory_evolution_spec(
    parent_candidate_digest: str,
    writer: HeredityWriterSpec,
    mark: MarkSetting | None,
) -> HeredityEvolutionSpec:
    return HeredityEvolutionSpec(
        "wagner-heredity-v1-evolution-exploratory",
        EVOLUTION_EXPLORATORY_SEED,
        parent_candidate_digest,
        _cells(writer, mark),
        32,
        64,
        100,
        4,
        32,
        128,
        exploratory=True,
    )


def confirmatory_evolution_spec(
    parent_candidate_digest: str,
    writer: HeredityWriterSpec,
    mark: MarkSetting | None,
    passing_carriers: tuple[str, ...],
) -> HeredityEvolutionSpec:
    cells = tuple(
        cell for cell in _cells(writer, mark) if cell.carrier in passing_carriers
    )
    return HeredityEvolutionSpec(
        "wagner-heredity-v1-evolution-confirmation",
        EVOLUTION_CONFIRMATION_SEED,
        parent_candidate_digest,
        cells,
        64,
        128,
        200,
        4,
        32,
        128,
        exploratory=False,
    )


def quick_evolution_spec() -> HeredityEvolutionSpec:
    writer = HeredityWriterSpec(
        "quick-hard",
        "fixture",
        CueIntervention("persistent_hard", 1.0, 1),
        0.0,
        True,
        "quick-hard",
    )
    return HeredityEvolutionSpec(
        "wagner-heredity-evolution-quick",
        EVOLUTION_EXPLORATORY_SEED,
        "0" * 64,
        _cells(writer, None),
        1,
        4,
        2,
        1,
        2,
        4,
        genes=4,
        post_horizon=4,
        hold_run=2,
        maximum_founder_proposals=10_000,
        maximum_offspring_factor=20,
        exploratory=True,
    )


def _sample_founder(
    spec: HeredityEvolutionSpec,
    cell: HeredityEvolutionCell,
    population_id: str,
) -> tuple[WagnerRulebook, AttractorPair, int, tuple[int, ...]]:
    for proposal in range(spec.maximum_founder_proposals):
        candidate = WagnerRulebook.random(
            spec.genes,
            rng_for(
                spec.master_seed,
                "heredity-evolution-founder",
                population_id,
                proposal,
            ),
        )
        viewed = MechanismRulebook(candidate, "wagner_sequential")
        pair = select_attractor_pair(
            viewed.landscape(),
            spec.genes,
            0.05 if spec.genes == 10 else 0.0,
            0.40 if spec.genes == 10 else 0.25,
        )
        if pair is None:
            continue
        ordering = rng_for(
            spec.master_seed, "heredity-evolution-order", population_id
        ).permutation(spec.genes)
        midpoint = balanced_midpoints(pair, spec.genes, ordering, 1)[0]
        nodes = intervention_nodes(
            pair, spec.genes, cell.writer.intervention, ordering
        )
        return candidate, pair, midpoint, nodes
    raise RuntimeError(f"could not sample heredity-evolution founder for {population_id}")


def _score_rulebook(
    rulebook: WagnerRulebook,
    pair: AttractorPair,
    midpoint: int,
    nodes: tuple[int, ...],
    cell: HeredityEvolutionCell,
    spec: HeredityEvolutionSpec,
    population_id: str,
    coordinate: tuple[Any, ...],
    replicates: int,
) -> float:
    if cell.treatment == "neutral":
        return 0.5
    viewed = MechanismRulebook(rulebook, "wagner_sequential")
    successes: list[float] = []
    for history in ("A", "B"):
        target = pair.state(history)
        for replicate in range(replicates):
            state = midpoint
            mark = np.zeros(viewed.genes, dtype=float)
            training_states = []
            for cycle in range(cell.writer.intervention.dwell):
                parts = (
                    spec.master_seed,
                    "heredity-evolution-score",
                    population_id,
                    *coordinate,
                    history,
                    replicate,
                    "train",
                    cycle,
                )
                initial = apply_carryover(
                    state,
                    midpoint,
                    viewed.genes,
                    1.0,
                    spec.expression_flip_probability,
                    rng_for(*parts, "carry"),
                )
                initial = apply_mark_bias(
                    initial, mark, cell.mark.coupling, rng_for(*parts, "mark")
                )
                result = develop_with_intervention(
                    viewed,
                    initial,
                    cell.writer.intervention,
                    target,
                    nodes,
                    cell.writer.gamma_variance,
                    100,
                    rng_for(*parts, "dynamics"),
                )
                state = int(result.final_state)
                if cell.mark.active:
                    mark = update_mark(mark, state, viewed.genes, cell.mark.rho)
                training_states.append(state)
            if cell.treatment == "cue_performance_sham":
                successes.append(
                    float(bool(training_states and training_states[-1] == target))
                )
                continue
            if cell.carrier == "state":
                mark = np.zeros(viewed.genes, dtype=float)
                coupling = 0.0
                write_mark = False
            else:
                state = midpoint
                coupling = cell.mark.coupling
                write_mark = True
            for age in range(spec.descendant_age):
                parts = (
                    spec.master_seed,
                    "heredity-evolution-score",
                    population_id,
                    *coordinate,
                    history,
                    replicate,
                    "descendant",
                    age,
                )
                value = develop_memory_cycle(
                    viewed,
                    state,
                    midpoint,
                    mark,
                    1.0,
                    spec.expression_flip_probability,
                    cell.mark.rho,
                    coupling,
                    cell.writer.gamma_variance,
                    100,
                    rng_for(*parts, "carry"),
                    rng_for(*parts, "mark"),
                    rng_for(*parts, "dynamics"),
                    write_mark=write_mark,
                )
                state = value.state
                mark = np.asarray(value.mark, dtype=float)
            state, _ = damage_state(
                state,
                viewed.genes,
                spec.neutral_damage_fraction,
                rng_for(
                    spec.master_seed,
                    "heredity-evolution-score",
                    population_id,
                    *coordinate,
                    history,
                    replicate,
                    "damage",
                ),
            )
            run = 0
            maximum = 0
            for cycle in range(spec.post_horizon):
                parts = (
                    spec.master_seed,
                    "heredity-evolution-score",
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
                    coupling,
                    cell.writer.gamma_variance,
                    100,
                    rng_for(*parts, "carry"),
                    rng_for(*parts, "mark"),
                    rng_for(*parts, "dynamics"),
                    write_mark=write_mark,
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
    spec = HeredityEvolutionSpec.from_dict(spec_value)
    cell = HeredityEvolutionCell.from_dict(cell_value)
    population_id = f"{cell.name}.population-{population_index:03d}"
    directory = Path(directory_text)
    final_path = directory / f"{population_id}.json"
    if final_path.is_file():
        return read_json(final_path)
    checkpoint = directory / f"{population_id}.checkpoint.json"
    if checkpoint.is_file():
        saved = read_json(checkpoint)
        founder = rulebook_from_dict(saved["founder"])
        if not isinstance(founder, WagnerRulebook):
            raise TypeError("heredity-evolution checkpoint founder is not Wagner")
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
                    rng_for(
                        spec.master_seed,
                        "heredity-evolution-initial",
                        population_id,
                        index,
                    ),
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
        following = []
        scores = []
        proposal = 0
        maximum = spec.population_size * spec.maximum_offspring_factor
        while len(following) < spec.population_size and proposal < maximum:
            rng = rng_for(
                spec.master_seed,
                "heredity-evolution-offspring",
                population_id,
                generation,
                proposal,
            )
            left = population[int(rng.integers(len(population)))]
            right = population[int(rng.integers(len(population)))]
            child = _mutate(_recombine(left, right, rng), rng)
            if not isinstance(child, WagnerRulebook):
                raise TypeError("heredity evolution produced a non-Wagner child")
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
                "format": "gre-wagner-heredity-evolution-checkpoint-v1",
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
    selected_score = _score_rulebook(
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
    for index in range(min(32, len(population))):
        parent = population[index]
        child = _mutate(
            parent,
            rng_for(
                spec.master_seed,
                "heredity-evolution-breeding",
                population_id,
                index,
            ),
        )
        if not isinstance(child, WagnerRulebook):
            raise TypeError("heredity evolution produced a non-Wagner child")
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
        "format": "gre-wagner-heredity-evolution-population-v1",
        "population_id": population_id,
        "cell": asdict(cell),
        "population_index": population_index,
        "founder": founder.to_dict(),
        "selected": selected.to_dict(),
        "pair": asdict(pair),
        "midpoint": midpoint,
        "nodes": list(nodes),
        "founder_heldout_score": founder_score,
        "selected_heldout_score": selected_score,
        "heldout_change": selected_score - founder_score,
        "breeding_value_correlation": breeding,
        "trace": trace,
    }
    _atomic_json(final_path, result)
    return result


def run_heredity_evolution(
    spec: HeredityEvolutionSpec,
    destination: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("heredity evolution requires 1-8 workers")
    destination = destination.resolve()
    if (destination / "SHA256SUMS").is_file():
        verify_checksums(destination)
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    populations = destination / "populations"
    populations.mkdir(exist_ok=True)
    registration = {
        "format": "gre-wagner-heredity-evolution-registration-v1",
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if canonical_digest(read_json(registration_path)) != canonical_digest(
            registration
        ):
            raise ValueError("existing heredity-evolution registration differs")
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
            elapsed = prior_elapsed + time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                progress_path,
                {
                    "format": "gre-wagner-heredity-evolution-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (
                        (len(tasks) - index) / rate if rate > 0.0 else None
                    ),
                },
            )
            if progress is not None:
                progress(
                    f"completed heredity-evolution population {index}/{len(tasks)}"
                )
    analysis = _analyze_evolution(results, spec)  # type: ignore[arg-type]
    analysis["format"] = "gre-wagner-heredity-evolution-analysis-v1"
    analysis["parent_candidate_digest"] = spec.parent_candidate_digest
    _atomic_json(destination / "analysis.json", analysis)
    manifest = {
        "format": "gre-wagner-heredity-evolution-manifest-v1",
        "completed": True,
        "populations": len(results),
        "elapsed_seconds": prior_elapsed + time.monotonic() - started,
        "workers": workers,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "manifest.json", manifest)
    lines = [
        "# Evolution of Wagner heredity capacity",
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
