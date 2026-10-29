"""Conway Life (B3/S23) on a torus, with the shared-observer lineage mode.

Traps encoded as tests (the literature pass): Moore-8 excludes the center;
double-buffered updates (in-place corrupts the glider while the block still
passes); positive-modulo wrap (np.roll); glider grid >= 8x8, LWSS >= 10x10;
assert period-displacement invariants, never a single source-named phase.
"""

from __future__ import annotations

import numpy as np

from xeno_bridge.lineage import SeedStats

from .config import LifeConfig

# --- Literature fixtures (cell sets as (row, col)) -------------------------
GLIDER = ((0, 1), (1, 2), (2, 0), (2, 1), (2, 2))  # evolve(P,4) == shift(P,+1,+1)
BLOCK = ((0, 0), (0, 1), (1, 0), (1, 1))  # still life
BLINKER_H = ((1, 0), (1, 1), (1, 2))  # period 2
TOAD = ((1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2))  # period 2
LWSS_WEST = (  # evolve(P,4) == shift(P,0,-2)
    (0, 1), (0, 4), (1, 0), (2, 0), (2, 4), (3, 0), (3, 1), (3, 2), (3, 3),
)
# Lineage-forming fixtures: activity-positive objects. The block is run
# descriptively — a still life has no activity, so it cannot divide under
# an activity-gated clock (dev round 3: survival 0.12; a real finding).
NAMED_OBJECTS = {"glider": GLIDER, "blinker": BLINKER_H, "toad": TOAD}


def paint(cells, height: int, width: int, top: int = 2, left: int = 2) -> np.ndarray:
    grid = np.zeros((height, width), dtype=np.uint8)
    for r, c in cells:
        grid[(top + r) % height, (left + c) % width] = 1
    return grid


def life_step(grids: np.ndarray, eta: float = 0.0, rng=None) -> np.ndarray:
    """Batched B3/S23 step on (B, H, W) torus grids; double-buffered."""
    neighbors = np.zeros(grids.shape, dtype=np.int64)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue  # Moore-8 excludes the center
            neighbors += np.roll(np.roll(grids, dr, axis=-2), dc, axis=-1)
    born = (grids == 0) & (neighbors == 3)
    survives = (grids == 1) & ((neighbors == 2) | (neighbors == 3))
    updated = (born | survives).astype(np.uint8)
    if eta > 0:
        updated = updated ^ (rng.random(grids.shape) < eta).astype(np.uint8)
    return updated


def evolve(grid: np.ndarray, steps: int) -> np.ndarray:
    out = grid[None].copy()
    for _ in range(steps):
        out = life_step(out)
    return out[0]


def shift(grid: np.ndarray, dr: int, dc: int) -> np.ndarray:
    return np.roll(np.roll(grid, dr, axis=0), dc, axis=1)


def block_counts(grids: np.ndarray) -> np.ndarray:
    """(B, 15) counts of NON-EMPTY 2x2 block patterns.

    Dev round 1 lesson (the ECA round-1 twin): the all-dead block dominates
    sparse grids, making every object's spectrum nearly parallel — score the
    living texture, not the vacuum. Dev round 2 lesson: oscillators alternate
    their census phase-to-phase (a blinker reads as perpetual breaking), so
    the composition is the mass-weighted average of the live census over the
    generation's sweeps — phase-robust, still vacuum-free."""
    a = grids
    b = np.roll(grids, -1, axis=-1)
    c = np.roll(grids, -1, axis=-2)
    d = np.roll(np.roll(grids, -1, axis=-2), -1, axis=-1)
    index = (8 * a + 4 * b + 2 * c + d).astype(np.int64)
    batch = grids.shape[0]
    offsets = (np.arange(batch) * 16)[:, None, None]
    counts = np.bincount((index + offsets).ravel(), minlength=batch * 16)
    return counts.reshape(batch, 16)[:, 1:].astype(np.float64)


def run_generation(grids, config: LifeConfig, rng):
    """Activity-gated growth to division, exactly the ECA semantics in 2D."""
    grids = grids.astype(np.uint8).copy()
    batch = grids.shape[0]
    cells = grids.shape[-2] * grids.shape[-1]
    activity = np.zeros(batch, dtype=np.int64)
    sweeps = np.zeros(batch, dtype=np.int64)
    active = np.ones(batch, dtype=bool)
    divided = np.zeros(batch, dtype=bool)
    census = np.zeros((batch, 15), dtype=np.float64)
    for _ in range(config.t_max_sweeps):
        if not active.any():
            break
        idx = np.flatnonzero(active)
        updated = life_step(grids[idx], config.flip_noise, rng)
        activity[idx] += (updated != grids[idx]).sum(axis=(-2, -1))
        grids[idx] = updated
        census[idx] += block_counts(updated)
        sweeps[idx] += 1
        done = (activity[idx] >= config.activity_budget) & (sweeps[idx] >= config.t_min_sweeps)
        divided[idx[done]] = True
        active[idx[done]] = False
    spectrum = census / np.maximum(census.sum(axis=1, keepdims=True), 1.0)
    total = grids.sum(axis=(-2, -1))
    divided = divided & (total > 0) & (total < cells)
    errors = rng.random(grids.shape) < config.copy_error
    offspring = grids ^ errors.astype(np.uint8)
    return spectrum, sweeps, divided, offspring


def _cosine_rows(left, right):
    numerator = (left * right).sum(axis=-1)
    denominator = np.linalg.norm(left, axis=-1) * np.linalg.norm(right, axis=-1)
    return np.where(denominator > 0, numerator / np.maximum(denominator, 1e-300), 0.0)


def run_lineage(
    launch: np.ndarray, config: LifeConfig, rng, n_futures: int
) -> tuple[SeedStats, np.ndarray, np.ndarray]:
    """Shared-observer lineage from one launch grid.

    Returns (stats, mean_h_per_future, pre_break_spectrum_per_future)."""
    grids = np.tile(launch, (n_futures, 1, 1))
    alive = np.ones(n_futures, dtype=bool)
    positive = np.zeros(n_futures, dtype=bool)
    seen_break = np.zeros(n_futures, dtype=bool)
    anchor = np.zeros((n_futures, 15))
    recent = np.zeros((n_futures, config.strict_run, 15))
    run_length = np.zeros(n_futures, dtype=np.int16)
    success_step = np.full(n_futures, -1, dtype=np.int16)
    first_break = np.full(n_futures, -1, dtype=np.int16)
    first_recovery_lag = np.full(n_futures, -1, dtype=np.int16)
    inherit_run_length = np.zeros(n_futures, dtype=np.int16)
    survival_generation = np.zeros(n_futures, dtype=np.int16)
    first_generation_time = np.zeros(n_futures)
    h_sum = np.zeros(n_futures)
    h_count = np.zeros(n_futures)
    pre_break = np.zeros((n_futures, 15))
    pre_break_n = np.zeros(n_futures)
    h_sample = []
    total_sweeps = 0
    generations_run = 0

    previous = None
    for generation in range(config.strict_horizon):
        active = np.flatnonzero(alive & ~positive)
        if active.size == 0:
            break
        spectra, sweeps, divided, offspring = run_generation(grids[active], config, rng)
        died = active[~divided]
        alive[died] = False
        total_sweeps += int(sweeps.sum())
        generations_run += int(divided.sum())
        if generation == 0:
            first_generation_time[active] = sweeps
        live = active[divided]
        if live.size == 0:
            continue
        composition = spectra[divided]
        grids[live] = offspring[divided]
        no_break_yet = ~seen_break[live]
        pre_break[live[no_break_yet]] += composition[no_break_yet]
        pre_break_n[live[no_break_yet]] += 1
        if previous is None:
            previous = np.zeros((n_futures, 15))
            previous[live] = composition
            survival_generation[live] = 1
            continue
        h = _cosine_rows(previous[live], composition)
        h_sample.append(h)
        h_sum[live] += h
        h_count[live] += 1
        previous[live] = composition
        survival_generation[live] = generation + 1
        inherited = h > config.inherit_threshold
        was_clean = ~seen_break[live]
        inherit_run_length[live[inherited & was_clean]] = np.minimum(
            inherit_run_length[live[inherited & was_clean]] + 1, 127
        )
        new_break = (~inherited) & was_clean
        if np.any(new_break):
            marked = live[new_break]
            seen_break[marked] = True
            first_break[marked] = generation
            anchor[marked] = composition[new_break]
            recent[marked] = 0.0
            run_length[marked] = 0
        later_break = (~inherited) & seen_break[live] & (~new_break)
        if np.any(later_break):
            marked = live[later_break]
            recent[marked] = 0.0
            run_length[marked] = 0
        continuing = inherited & seen_break[live]
        if np.any(continuing):
            marked = live[continuing]
            lagged = marked[(first_recovery_lag[marked] < 0) & (first_break[marked] >= 0)]
            first_recovery_lag[lagged] = generation - first_break[lagged]
            recent[marked, :-1] = recent[marked, 1:]
            recent[marked, -1] = composition[continuing]
            run_length[marked] = np.minimum(run_length[marked] + 1, config.strict_run)
            ready = marked[run_length[marked] >= config.strict_run]
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
                            _cosine_rows(window[:, a], window[:, b]) > config.coherence_threshold
                        )
                hits = ready[distinct_ok & pair_ok]
                positive[hits] = True
                success_step[hits] = generation

    h_values = np.concatenate(h_sample) if h_sample else np.zeros(0)
    stats = SeedStats(
        seed_index=0,
        n_futures=n_futures,
        strict_probability=float(positive.mean()),
        success_step=success_step,
        first_break=first_break,
        first_recovery_lag=first_recovery_lag,
        inherit_run_length=inherit_run_length,
        survival_generation=survival_generation,
        first_generation_time=first_generation_time,
        h_values=h_values,
        mean_events_per_generation=(total_sweeps / generations_run if generations_run else 0.0),
        mean_catalyzed_per_molecule=0.0,
        repair_fraction=0.0,
    )
    mean_h = np.where(h_count > 0, h_sum / np.maximum(h_count, 1), np.nan)
    spectra_pre = pre_break / np.maximum(pre_break_n[:, None], 1)
    return stats, mean_h, spectra_pre
