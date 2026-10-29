"""Generation loop, division contracts, and strict-event bookkeeping.

The observer semantics — inheritance by cosine between parent and selected
daughter compositions, first-break anchoring, coherent-run counting with
old-anchor distinctness — deliberately mirror the sealed E1 sampler so the
frozen GARD-side pattern signature is well-posed on this substrate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .chemistry import Chemistry
from .config import XenoConfig
from .engine import STATUS_DIVIDED, grow_batch


def launch_seed_counts(
    seed_index: int, chemistry: Chemistry, config: XenoConfig
) -> np.ndarray:
    """Deterministic launch recipe: concentrated mass in one long polymer
    plus a monomer bath."""
    longest = [s for s in chemistry.species if len(s) == config.max_length]
    target = longest[seed_index % len(longest)]
    launch_mass = config.mass_max // 2
    counts = np.zeros(chemistry.n_species, dtype=np.int64)
    target_copies = int(config.seed_mass_fraction * launch_mass / config.max_length)
    counts[chemistry.index[target]] = target_copies
    remainder = launch_mass - target_copies * config.max_length
    counts[chemistry.monomer_ids[0]] += (remainder + 1) // 2
    counts[chemistry.monomer_ids[1]] += remainder // 2
    return counts


def _mass_fractions(counts: np.ndarray, chemistry: Chemistry) -> np.ndarray:
    masses = (counts * chemistry.masses).astype(np.float64)
    total = masses.sum(axis=-1, keepdims=True)
    return masses / np.maximum(total, 1.0)


def _cosine_rows(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    numerator = (left * right).sum(axis=-1)
    denominator = np.linalg.norm(left, axis=-1) * np.linalg.norm(right, axis=-1)
    return np.where(denominator > 0, numerator / np.maximum(denominator, 1e-300), 0.0)


def _divide(
    counts: np.ndarray, chemistry: Chemistry, config: XenoConfig, rng: np.random.Generator
) -> np.ndarray:
    """Selected-daughter division under the configured contract."""
    if config.division_contract == "binomial":
        daughter = rng.binomial(counts, 0.5)
        other = counts - daughter
        pick_first = rng.random(counts.shape[0]) < 0.5
        chosen = np.where(pick_first[:, None], daughter, other)
        alt = np.where(pick_first[:, None], other, daughter)
        empty = (chosen * chemistry.masses).sum(axis=1) == 0
        chosen[empty] = alt[empty]
        return chosen
    half = counts // 2
    remainder = counts - 2 * half
    extra = rng.binomial(remainder, 0.5)
    daughter = half + extra
    other = counts - daughter
    pick_first = rng.random(counts.shape[0]) < 0.5
    chosen = np.where(pick_first[:, None], daughter, other)
    alt = np.where(pick_first[:, None], other, daughter)
    empty = (chosen * chemistry.masses).sum(axis=1) == 0
    chosen[empty] = alt[empty]
    return chosen


@dataclass
class SeedStats:
    seed_index: int
    n_futures: int
    strict_probability: float
    success_step: np.ndarray  # (n_futures,) int16, -1 = none
    first_break: np.ndarray  # (n_futures,) int16, -1 = none
    first_recovery_lag: np.ndarray  # (n_futures,) int16, -1 = none
    inherit_run_length: np.ndarray  # (n_futures,) generations before first break
    survival_generation: np.ndarray  # (n_futures,) generations survived
    first_generation_time: np.ndarray  # (n_futures,) physical duration of gen 1
    h_values: np.ndarray  # all observed parent-daughter cosines (flat sample)
    mean_events_per_generation: float
    mean_catalyzed_per_molecule: float
    repair_fraction: float


def run_seed(
    table: np.ndarray,
    seed_index: int,
    chemistry: Chemistry,
    config: XenoConfig,
    rng: np.random.Generator,
    *,
    n_futures: int | None = None,
) -> SeedStats:
    n_futures = config.futures_per_seed if n_futures is None else n_futures
    counts = np.tile(launch_seed_counts(seed_index, chemistry, config), (n_futures, 1))
    n_species = chemistry.n_species

    alive = np.ones(n_futures, dtype=bool)
    positive = np.zeros(n_futures, dtype=bool)
    seen_break = np.zeros(n_futures, dtype=bool)
    anchor = np.zeros((n_futures, n_species), dtype=np.float64)
    recent = np.zeros((n_futures, config.strict_run, n_species), dtype=np.float64)
    run_length = np.zeros(n_futures, dtype=np.int16)

    success_step = np.full(n_futures, -1, dtype=np.int16)
    first_break = np.full(n_futures, -1, dtype=np.int16)
    first_recovery_lag = np.full(n_futures, -1, dtype=np.int16)
    inherit_run_length = np.zeros(n_futures, dtype=np.int16)
    survival_generation = np.zeros(n_futures, dtype=np.int16)
    first_generation_time = np.zeros(n_futures)
    h_sample: list[np.ndarray] = []
    total_events = 0
    total_catalyzed = 0
    total_repairs = 0
    total_molecule_generations = 0.0
    generations_run = 0

    previous_composition = _mass_fractions(counts, chemistry)

    for generation in range(config.strict_horizon):
        active = np.flatnonzero(alive & ~positive)
        if active.size == 0:
            break
        result = grow_batch(counts[active], table, chemistry, config, rng)
        divided_local = result.status == STATUS_DIVIDED
        died = active[~divided_local]
        alive[died] = False
        total_events += int(result.events.sum())
        total_catalyzed += int(result.catalyzed_events.sum())
        total_repairs += int(result.repairs.sum())
        total_molecule_generations += float(result.counts.sum())
        generations_run += int(divided_local.sum())
        if generation == 0:
            first_generation_time[active] = result.elapsed

        live = active[divided_local]
        if live.size == 0:
            continue
        parent_counts = result.counts[divided_local]
        parent_composition = _mass_fractions(parent_counts, chemistry)
        daughters = _divide(parent_counts, chemistry, config, rng)
        counts[live] = daughters
        daughter_composition = _mass_fractions(daughters, chemistry)

        h = _cosine_rows(parent_composition, daughter_composition)
        h_sample.append(h)
        inherited = h > config.inherit_threshold
        survival_generation[live] = generation + 1
        inherit_run_length[live[inherited & ~seen_break[live]]] = np.minimum(
            inherit_run_length[live[inherited & ~seen_break[live]]] + 1, 127
        )

        new_break = (~inherited) & (~seen_break[live])
        if np.any(new_break):
            rows = live[new_break]
            seen_break[rows] = True
            first_break[rows] = generation
            anchor[rows] = parent_composition[new_break]
            recent[rows] = 0.0
            run_length[rows] = 0

        later_break = (~inherited) & seen_break[live] & (~new_break)
        if np.any(later_break):
            rows = live[later_break]
            recent[rows] = 0.0
            run_length[rows] = 0

        continuing = inherited & seen_break[live]
        if np.any(continuing):
            rows = live[continuing]
            lagged = rows[(first_recovery_lag[rows] < 0) & (first_break[rows] >= 0)]
            first_recovery_lag[lagged] = generation - first_break[lagged]
            recent[rows, :-1] = recent[rows, 1:]
            recent[rows, -1] = daughter_composition[continuing]
            run_length[rows] = np.minimum(run_length[rows] + 1, config.strict_run)
            ready = rows[run_length[rows] >= config.strict_run]
            if ready.size:
                window = recent[ready]
                distinct_ok = np.ones(len(ready), dtype=bool)
                pair_ok = np.ones(len(ready), dtype=bool)
                for a in range(config.strict_run):
                    distinct_ok &= (
                        _cosine_rows(anchor[ready], window[:, a]) <= config.distinct_threshold
                    )
                    for b in range(a + 1, config.strict_run):
                        pair_ok &= (
                            _cosine_rows(window[:, a], window[:, b])
                            > config.coherence_threshold
                        )
                hits = ready[distinct_ok & pair_ok]
                positive[hits] = True
                success_step[hits] = generation

        previous_composition = daughter_composition

    h_values = np.concatenate(h_sample) if h_sample else np.zeros(0)
    return SeedStats(
        seed_index=seed_index,
        n_futures=n_futures,
        strict_probability=float(positive.mean()),
        success_step=success_step,
        first_break=first_break,
        first_recovery_lag=first_recovery_lag,
        inherit_run_length=inherit_run_length,
        survival_generation=survival_generation,
        first_generation_time=first_generation_time,
        h_values=h_values,
        mean_events_per_generation=(
            total_events / generations_run if generations_run else 0.0
        ),
        mean_catalyzed_per_molecule=(
            total_catalyzed / total_molecule_generations
            if total_molecule_generations
            else 0.0
        ),
        repair_fraction=total_repairs / max(total_events, 1),
    )
