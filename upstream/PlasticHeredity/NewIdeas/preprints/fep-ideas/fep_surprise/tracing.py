from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from . import compat as _compat  # noqa: F401
from plastic_heredity.config import GardConfig, SimulationContract
from plastic_heredity.simulator import (
    FissionRecord,
    SimulationError,
    _fission,
    _sample_without_replacement,
    _trim_whole_assembly,
    cosine_similarity,
)


@dataclass(frozen=True)
class TracedFission:
    record: FissionRecord
    phases: np.ndarray
    phase_compositions: np.ndarray


def _capture_crossings(
    current: np.ndarray,
    start_mass: int,
    target_mass: int,
    phase_grid: Sequence[float],
    captured: list[np.ndarray | None],
) -> None:
    denominator = max(target_mass - start_mass, 1)
    progress = min(1.0, max(0.0, (int(current.sum()) - start_mass) / denominator))
    for index, phase in enumerate(phase_grid):
        if captured[index] is None and phase <= progress + 1e-15:
            captured[index] = current.copy()


def traced_advance(
    composition: np.ndarray,
    beta: np.ndarray,
    config: GardConfig,
    contract: SimulationContract,
    rng: np.random.Generator,
    phase_grid: Sequence[float],
) -> TracedFission:
    """Exact observational copy of the sealed Codex advance operation.

    It duplicates the parent simulator's statement order and RNG calls. The
    only additional operation is copying the state after first phase crossing.
    Tests compare it bit-for-bit with ``advance_fission``.
    """

    current = np.asarray(composition, dtype=np.int64).copy()
    start_mass = int(current.sum())
    captured: list[np.ndarray | None] = [None] * len(phase_grid)
    _capture_crossings(current, start_mass, config.n_max, phase_grid, captured)
    rho = 1.0 / config.n_types
    steps = 0
    for step in range(1, config.max_growth_steps + 1):
        mass = int(current.sum())
        if mass <= 0:
            raise SimulationError("assembly became extinct")
        if mass >= config.n_max:
            current = _trim_whole_assembly(current, config.n_max, rng)
            steps = step - 1
            break

        catalytic_boost = 1.0 + (beta @ current) / mass
        join_rate = config.k_join * rho * mass * catalytic_boost
        leave_rate = config.k_leave * current * catalytic_boost
        exposure = contract.poisson_exposure
        joins = np.asarray(rng.poisson(join_rate * exposure), dtype=np.int64)
        leaves = np.minimum(
            np.asarray(rng.poisson(leave_rate * exposure), dtype=np.int64), current
        )
        survivors = current - leaves
        if contract.overshoot_rule == "admit_joiners_to_capacity":
            capacity = config.n_max - int(survivors.sum())
            if int(joins.sum()) > capacity:
                joins = _sample_without_replacement(joins, capacity, rng)
            current = survivors + joins
        elif contract.overshoot_rule == "trim_whole_assembly":
            current = survivors + joins
            if int(current.sum()) >= config.n_max:
                current = _trim_whole_assembly(current, config.n_max, rng)
        else:
            raise SimulationError(f"unknown overshoot rule: {contract.overshoot_rule}")
        _capture_crossings(current, start_mass, config.n_max, phase_grid, captured)
        if int(current.sum()) >= config.n_max:
            steps = step
            break
    else:
        raise SimulationError(
            f"growth did not reach mass {config.n_max} in {config.max_growth_steps} steps"
        )

    parent = current.copy()
    _capture_crossings(parent, start_mass, config.n_max, phase_grid, captured)
    captured[-1] = parent.copy()
    daughter = _fission(parent, config, contract, rng)
    record = FissionRecord(
        parent=parent,
        daughter=daughter,
        h=cosine_similarity(parent, daughter),
        growth_steps=steps,
    )
    last = composition.copy()
    complete: list[np.ndarray] = []
    for value in captured:
        if value is not None:
            last = value
        complete.append(np.asarray(last, dtype=np.int64).copy())
    return TracedFission(
        record=record,
        phases=np.asarray(phase_grid, dtype=np.float64),
        phase_compositions=np.stack(complete),
    )


def traced_fission_only_advance(
    composition: np.ndarray,
    beta: np.ndarray,
    config: GardConfig,
    contract: SimulationContract,
    rng: np.random.Generator,
    phase_grid: Sequence[float],
) -> TracedFission:
    del beta  # placeholder keeps the traced-advance callable contract uniform
    current = np.asarray(composition, dtype=np.int64).copy()
    start_mass = int(current.sum())
    if start_mass <= 0 or start_mass > config.n_max:
        raise SimulationError("invalid fission-only launch mass")
    captured: list[np.ndarray | None] = [None] * len(phase_grid)
    _capture_crossings(current, start_mass, config.n_max, phase_grid, captured)
    arrivals = config.n_max - start_mass
    # The sealed null draws all IID arrivals in one multinomial operation.
    if arrivals:
        additions = np.asarray(
            rng.multinomial(
                arrivals,
                np.full(config.n_types, 1.0 / config.n_types, dtype=np.float64),
            ),
            dtype=np.int64,
        )
        # Phase snapshots are observational interpolation of the realized IID
        # arrival multiset. They do not consume RNG and never affect the parent.
        cumulative = np.zeros_like(current)
        allocated = 0
        for index, phase in enumerate(phase_grid[1:-1], start=1):
            wanted = min(arrivals, int(np.floor(phase * arrivals)))
            if wanted > allocated:
                remaining = additions - cumulative
                take = _sample_prefix_without_rng(remaining, wanted - allocated)
                cumulative += take
                allocated = wanted
            captured[index] = current + cumulative
        current += additions
    parent = current.copy()
    captured[-1] = parent.copy()
    daughter = _fission(parent, config, contract, rng)
    record = FissionRecord(
        parent=parent,
        daughter=daughter,
        h=cosine_similarity(parent, daughter),
        growth_steps=arrivals,
    )
    last = np.asarray(composition, dtype=np.int64).copy()
    complete = []
    for value in captured:
        if value is not None:
            last = value
        complete.append(last.copy())
    return TracedFission(record, np.asarray(phase_grid), np.stack(complete))


def _sample_prefix_without_rng(counts: np.ndarray, size: int) -> np.ndarray:
    """Deterministic prefix used only to visualize an already drawn multiset."""

    out = np.zeros_like(counts)
    remaining = size
    for index, count in enumerate(counts):
        take = min(int(count), remaining)
        out[index] = take
        remaining -= take
        if remaining == 0:
            break
    if remaining:
        raise AssertionError("prefix exceeds realized additions")
    return out


AdvanceFunction = Callable[
    [np.ndarray, np.ndarray, GardConfig, SimulationContract, np.random.Generator, Sequence[float]],
    TracedFission,
]


def trace_future(
    initial: np.ndarray,
    beta: np.ndarray,
    config: GardConfig,
    contract: SimulationContract,
    horizon: int,
    rng: np.random.Generator,
    phase_grid: Sequence[float],
    fission_only: bool = False,
) -> tuple[list[TracedFission], bool]:
    current = np.asarray(initial, dtype=np.int64).copy()
    output: list[TracedFission] = []
    advance = traced_fission_only_advance if fission_only else traced_advance
    for _ in range(horizon):
        try:
            item = advance(current, beta, config, contract, rng, phase_grid)
        except SimulationError:
            return output, False
        output.append(item)
        current = item.record.daughter
    return output, True
