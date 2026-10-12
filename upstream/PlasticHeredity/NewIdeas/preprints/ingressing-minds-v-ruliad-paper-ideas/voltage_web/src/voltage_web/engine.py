"""The voltage sheet: double-well cells, gap-junction coupling, quenched
heterogeneity, channel noise — and fission WITH regeneration: a daughter is
one half of the sheet, the other half reset to resting potential, and the
next generation's own dynamics must re-pattern the blank from the fragment.

Identity = the binarized domain map (V > 0); composition = the E21-frozen
15-dim generation-averaged census of depolarized-containing 2x2 blocks
(`glider_test.life.block_counts`). Lineages return
`xeno_bridge.lineage.SeedStats` so every frozen instrument applies."""

from __future__ import annotations

import numpy as np

from contract_bridge.artifacts import seed_rng
from glider_test.life import block_counts
from xeno_bridge.lineage import SeedStats

from .config import VoltageConfig


def make_thresholds(config: VoltageConfig) -> np.ndarray:
    """Quenched per-cell bias theta (cell diversity; mild pinning texture).

    Dev history, recorded: round 3 (white field) showed the coupling
    trade-off — parental regeneration needs g >= 1 but coarsening then
    kills patterns within 8 generations; round 4 (smoothed field)
    OVER-pinned: the prepattern dictated every seed's pattern (theta-slaved,
    not parent-slaved). Round 5 fixes survival with CONSERVED dynamics in
    sheet_step instead of quenched pinning, and theta returns to a white
    per-cell field."""
    rng = seed_rng(config.tissue_tag, config.tissue_index)
    return config.threshold_spread * rng.standard_normal((config.height, config.width))


def sheet_step(V: np.ndarray, theta: np.ndarray, config: VoltageConfig,
               rng: np.random.Generator, clamp: np.ndarray | None = None) -> np.ndarray:
    """One Euler sweep on batched (B, H, W) sheets."""
    neighbors = (
        np.roll(V, 1, axis=-2) + np.roll(V, -1, axis=-2)
        + np.roll(V, 1, axis=-1) + np.roll(V, -1, axis=-1)
    ) / 4.0
    drift = V - V ** 3 + config.well_asym + theta + config.coupling * (neighbors - V)
    # Dev round 5: CONSERVED dynamics (Cahn-Hilliard-like). The sheet's
    # total potential is held per step — the tissue cannot lose its charge
    # content — so the bulk composition is inherited through the fragment
    # and domains cannot coarsen to extinction. The zap clamp deliberately
    # VIOLATES conservation: that is precisely what an ionophore does.
    drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
    noise = config.sigma * rng.standard_normal(V.shape)
    noise = noise - noise.mean(axis=(-2, -1), keepdims=True)
    V = V + config.dt * drift + noise
    V = np.clip(V, -2.0, 2.0)
    if clamp is not None:
        V = np.where(clamp[None, :, :], 1.5, V)
    return V


def launch_pattern(seed_index: int, config: VoltageConfig) -> np.ndarray:
    """Frozen wild-type recipe: one-head gradient, halves, stripes, spots,
    hash-density fields. Values are exactly +-1."""
    h, w = config.height, config.width
    field = np.full((h, w), -1.0)
    if seed_index == 0:  # the "one-head" anterior domain
        field[:, : w // 2] = 1.0
    elif seed_index == 1:
        field[: h // 2, :] = 1.0
    elif seed_index in (2, 3):
        period = 4 if seed_index == 2 else 8
        for c in range(w):
            if (c // (period // 2)) % 2 == 0:
                field[:, c] = 1.0
    elif seed_index in (4, 5):
        rng = seed_rng("voltage-spots-v1", seed_index)
        for _ in range(2 + seed_index - 3):
            cy, cx = rng.integers(0, h), rng.integers(0, w)
            radius = 2 + int(seed_index == 5)
            yy, xx = np.ogrid[:h, :w]
            dist2 = np.minimum(np.abs(yy - cy), h - np.abs(yy - cy)) ** 2 + \
                np.minimum(np.abs(xx - cx), w - np.abs(xx - cx)) ** 2
            field[dist2 <= radius ** 2] = 1.0
    else:
        density = 0.2 + 0.4 * (seed_index - 6) / max(config.n_seeds - 7, 1)
        rng = seed_rng("voltage-density-v1", seed_index)
        field = np.where(rng.random((h, w)) < density, 1.0, -1.0)
    return field


def run_generation(V: np.ndarray, theta: np.ndarray, config: VoltageConfig,
                   rng: np.random.Generator,
                   clamp: np.ndarray | None = None,
                   clamp_sweeps: int = 0):
    """Grow to division; returns (spectra (B,15), sweeps, divided, V_final)."""
    V = V.copy()
    batch = V.shape[0]
    binary = (V > 0).astype(np.uint8)
    activity = np.zeros(batch, dtype=np.int64)
    sweeps = np.zeros(batch, dtype=np.int64)
    active = np.ones(batch, dtype=bool)
    divided = np.zeros(batch, dtype=bool)
    census = np.zeros((batch, 15), dtype=np.float64)
    for sweep in range(config.t_max_sweeps):
        if not active.any():
            break
        idx = np.flatnonzero(active)
        clamping = clamp if (clamp is not None and sweep < clamp_sweeps) else None
        V[idx] = sheet_step(V[idx], theta, config, rng, clamping)
        updated = (V[idx] > 0).astype(np.uint8)
        activity[idx] += (updated != binary[idx]).sum(axis=(-2, -1))
        binary[idx] = updated
        census[idx] += block_counts(updated)
        sweeps[idx] += 1
        done = (activity[idx] >= config.activity_budget) & (sweeps[idx] >= config.t_min_sweeps)
        divided[idx[done]] = True
        active[idx[done]] = False
    spectrum = census / np.maximum(census.sum(axis=1, keepdims=True), 1.0)
    total = binary.sum(axis=(-2, -1))
    divided = divided & (total > 0) & (total < config.cells)
    return spectrum, sweeps, divided, V


def fission(V: np.ndarray, config: VoltageConfig, rng: np.random.Generator,
            mode: str = "fragment") -> np.ndarray:
    """Cut-and-regrow reproduction: keep one half, reset the other to
    resting potential. mode='random_fragment' replaces the INHERITED half
    with a density-matched random field (the pattern-genesis control)."""
    batch = V.shape[0]
    offspring = np.full_like(V, config.resting)
    axis = rng.integers(0, 2, batch)
    side = rng.integers(0, 2, batch)
    for b in range(batch):
        half_h, half_w = config.height // 2, config.width // 2
        if axis[b] == 0:
            rows = slice(0, half_h) if side[b] == 0 else slice(half_h, None)
            fragment = V[b, rows, :]
            if mode == "random_fragment":
                density = float((fragment > 0).mean())
                fragment = np.where(
                    rng.random(fragment.shape) < density, 1.0, -1.0
                )
            offspring[b, rows, :] = fragment
        else:
            cols = slice(0, half_w) if side[b] == 0 else slice(half_w, None)
            fragment = V[b, :, cols]
            if mode == "random_fragment":
                density = float((fragment > 0).mean())
                fragment = np.where(
                    rng.random(fragment.shape) < density, 1.0, -1.0
                )
            offspring[b, :, cols] = fragment
    offspring = offspring + config.copy_jitter * rng.standard_normal(offspring.shape)
    return offspring


def _cosine_rows(left, right):
    numerator = (left * right).sum(axis=-1)
    denominator = np.linalg.norm(left, axis=-1) * np.linalg.norm(right, axis=-1)
    return np.where(denominator > 0, numerator / np.maximum(denominator, 1e-300), 0.0)


def run_seed(seed_index: int, config: VoltageConfig, rng: np.random.Generator,
             n_futures: int | None = None, collect_forms: bool = False,
             fission_mode: str = "fragment",
             zap: dict | None = None):
    """Shared-observer lineage. `zap` (optional): {"generation": k,
    "mask": (H,W) bool, "sweeps": T} — transient clamp during generation k
    (the ionophore analog, used by E27)."""
    n_futures = config.futures if n_futures is None else n_futures
    theta = make_thresholds(config)
    V = np.tile(launch_pattern(seed_index, config), (n_futures, 1, 1))
    V = V + config.copy_jitter * rng.standard_normal(V.shape)

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
    h_sample = []
    last_spectrum = np.zeros((n_futures, 15))
    pre_break_sum = np.zeros((n_futures, 15))
    pre_break_n = np.zeros(n_futures)
    total_sweeps = 0
    generations_run = 0

    previous = None
    for generation in range(config.strict_horizon):
        active = np.flatnonzero(alive & ~positive)
        if active.size == 0:
            break
        clamp_mask, clamp_sweeps = None, 0
        if zap is not None and generation == zap["generation"]:
            clamp_mask, clamp_sweeps = zap["mask"], zap["sweeps"]
        spectra, sweeps, divided, V_final = run_generation(
            V[active], theta, config, rng, clamp_mask, clamp_sweeps
        )
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
        V[live] = fission(V_final[divided], config, rng, fission_mode)
        last_spectrum[live] = composition
        clean = live[~seen_break[live]]
        pre_break_sum[clean] += composition[~seen_break[live]]
        pre_break_n[clean] += 1
        if previous is None:
            previous = np.zeros((n_futures, 15))
            previous[live] = composition
            survival_generation[live] = 1
            continue
        h = _cosine_rows(previous[live], composition)
        h_sample.append(h)
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
        mean_events_per_generation=(total_sweeps / generations_run if generations_run else 0.0),
        mean_catalyzed_per_molecule=0.0,
        repair_fraction=0.0,
    )
    if not collect_forms:
        return stats
    broke = (first_break >= 0) & (survival_generation > first_break)
    resettled = last_spectrum[broke].mean(axis=0) if broke.any() else np.zeros(15)
    had = pre_break_n > 0
    prebreak = (
        (pre_break_sum[had] / pre_break_n[had, None]).mean(axis=0)
        if had.any() else np.zeros(15)
    )
    return stats, resettled, prebreak
