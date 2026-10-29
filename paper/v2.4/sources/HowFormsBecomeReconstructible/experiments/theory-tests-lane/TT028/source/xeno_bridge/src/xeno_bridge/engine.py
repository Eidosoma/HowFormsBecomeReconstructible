"""Batched adaptive tau-leaping growth between divisions.

Pure-numpy, vectorized across futures. This IS the substrate's physics
contract: Poisson channel draws per adaptive step with clamp-repair on
overshoot (repair events are counted and reported as a diagnostic). An
exact single-trajectory SSA reference is provided for validation at small
sizes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .chemistry import Chemistry, batch_propensities
from .config import XenoConfig

STATUS_ACTIVE = 0
STATUS_DIVIDED = 1
STATUS_DEAD = 2
STATUS_TIMEOUT = 3


@dataclass
class GrowthResult:
    counts: np.ndarray  # (B, S) final counts
    elapsed: np.ndarray  # (B,) physical time consumed
    status: np.ndarray  # (B,)
    events: np.ndarray  # (B,) reaction+influx events applied
    catalyzed_events: np.ndarray  # (B,) events in catalyzed channels
    repairs: np.ndarray  # (B,) clamped molecule count (contract diagnostic)


def grow_batch(
    counts: np.ndarray,
    table: np.ndarray,
    chemistry: Chemistry,
    config: XenoConfig,
    rng: np.random.Generator,
) -> GrowthResult:
    counts = counts.astype(np.int64).copy()
    batch = counts.shape[0]
    elapsed = np.zeros(batch)
    status = np.full(batch, STATUS_ACTIVE, dtype=np.int8)
    events = np.zeros(batch, dtype=np.int64)
    catalyzed_events = np.zeros(batch, dtype=np.int64)
    repairs = np.zeros(batch, dtype=np.int64)
    catalyzed_channel = table.sum(axis=1) > 0  # (R,)
    influx_rate = np.full(2, config.influx)

    for _step in range(config.max_steps_per_generation):
        active = np.flatnonzero(status == STATUS_ACTIVE)
        if active.size == 0:
            break
        sub = counts[active]
        ligation, cleavage = batch_propensities(sub, table, chemistry, config)
        dilution = config.dilution * sub.astype(np.float64)
        total = (
            ligation.sum(axis=1)
            + cleavage.sum(axis=1)
            + dilution.sum(axis=1)
            + influx_rate.sum()
        )
        dt = np.minimum(config.tau_target_events / np.maximum(total, 1e-12), config.tau_max)

        lig_k = rng.poisson(ligation * dt[:, None])
        clv_k = rng.poisson(cleavage * dt[:, None])
        influx_k = rng.poisson(np.broadcast_to(influx_rate, (active.size, 2)) * dt[:, None])
        dil_k = np.minimum(rng.poisson(dilution * dt[:, None]), sub)

        delta = (lig_k - clv_k) @ chemistry.lig_stoich
        delta[:, chemistry.monomer_ids[0]] += influx_k[:, 0]
        delta[:, chemistry.monomer_ids[1]] += influx_k[:, 1]
        delta -= dil_k

        updated = sub + delta
        negative = np.minimum(updated, 0)
        repairs[active] += (-negative).sum(axis=1)
        updated = np.maximum(updated, 0)
        counts[active] = updated
        elapsed[active] += dt
        step_events = (lig_k + clv_k).sum(axis=1) + influx_k.sum(axis=1) + dil_k.sum(axis=1)
        events[active] += step_events
        catalyzed_events[active] += (lig_k + clv_k)[:, catalyzed_channel].sum(axis=1)

        mass = (updated * chemistry.masses).sum(axis=1)
        status[active[mass >= config.mass_max]] = STATUS_DIVIDED
        status[active[mass <= config.mass_dead]] = STATUS_DEAD

    status[status == STATUS_ACTIVE] = STATUS_TIMEOUT
    return GrowthResult(counts, elapsed, status, events, catalyzed_events, repairs)


def ssa_reference(
    counts: np.ndarray,
    table: np.ndarray,
    chemistry: Chemistry,
    config: XenoConfig,
    rng: np.random.Generator,
    *,
    max_events: int = 200_000,
) -> tuple[np.ndarray, float, int]:
    """Exact Gillespie single trajectory, for engine validation only."""
    counts = counts.astype(np.int64).copy()
    time = 0.0
    for event_index in range(max_events):
        ligation, cleavage = batch_propensities(counts[None, :], table, chemistry, config)
        dilution = config.dilution * counts.astype(np.float64)
        channels = np.concatenate(
            [ligation[0], cleavage[0], np.full(2, config.influx), dilution]
        )
        total = channels.sum()
        if total <= 0:
            return counts, time, STATUS_DEAD
        time += rng.exponential(1.0 / total)
        choice = np.searchsorted(np.cumsum(channels), rng.random() * total)
        n_r = chemistry.n_reactions
        if choice < n_r:
            counts += chemistry.lig_stoich[choice]
        elif choice < 2 * n_r:
            counts -= chemistry.lig_stoich[choice - n_r]
        elif choice < 2 * n_r + 2:
            counts[chemistry.monomer_ids[choice - 2 * n_r]] += 1
        else:
            counts[choice - 2 * n_r - 2] -= 1
        mass = int((counts * chemistry.masses).sum())
        if mass >= config.mass_max:
            return counts, time, STATUS_DIVIDED
        if mass <= config.mass_dead:
            return counts, time, STATUS_DEAD
    return counts, time, STATUS_TIMEOUT
