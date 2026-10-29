"""Physical-time solver, clock gauge, and translator score bundles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu

from finite_gard_ruliad.combinatorics import Composition
from finite_gard_ruliad.config import AtlasConfig
from finite_gard_ruliad.kernels import (
    AbsorptionKernel,
    PhysicalKernel,
    StateSpaces,
    build_physical_kernel,
    event_rates,
    make_state_spaces,
    solve_absorption,
)


def gauge_beta(beta: np.ndarray, factor: float) -> np.ndarray:
    """Catalytic clock gauge: multiplies every event rate by ``factor``.

    With ``boost = 1 + (beta @ n)/N`` the transformed matrix
    ``factor*beta + (factor-1)*ones`` gives ``factor*boost`` for every state,
    so the embedded jump chain is invariant while physical waiting times
    divide by ``factor``.
    """
    if factor <= 0:
        raise ValueError("gauge factor must be positive")
    return factor * np.asarray(beta, dtype=np.float64) + (factor - 1.0) * np.ones_like(beta)


def expected_physical_time(
    beta: np.ndarray,
    config: AtlasConfig,
    spaces: StateSpaces | None = None,
) -> np.ndarray:
    """Expected continuous time to absorption from every nonzero state.

    Solves ``(I - Q) t = w`` with ``w_i = 1/rate_i`` on the transient states;
    parents are at fission and contribute zero. Under the clock gauge the
    result divides exactly by the gauge factor.
    """
    spaces = spaces or make_state_spaces(config)
    n_t = len(spaces.transient)
    q_rows: list[int] = []
    q_cols: list[int] = []
    q_data: list[float] = []
    w = np.zeros(n_t, dtype=np.float64)
    for row, state in enumerate(spaces.transient):
        joins, leaves = event_rates(state, beta, config)
        total_rate = float(joins.sum() + leaves.sum())
        w[row] = 1.0 / total_rate
        mass = sum(state)
        for species, rate in enumerate(joins):
            if mass + 1 == config.n_max:
                continue
            target = list(state)
            target[species] += 1
            q_rows.append(row)
            q_cols.append(spaces.transient_index[tuple(target)])
            q_data.append(float(rate / total_rate))
        for species, rate in enumerate(leaves):
            if state[species] == 0 or rate == 0 or mass - 1 == 0:
                continue
            target = list(state)
            target[species] -= 1
            q_rows.append(row)
            q_cols.append(spaces.transient_index[tuple(target)])
            q_data.append(float(rate / total_rate))
    q = sparse.csc_matrix((q_data, (q_rows, q_cols)), shape=(n_t, n_t))
    system = sparse.eye(n_t, format="csc", dtype=np.float64) - q
    t = np.asarray(splu(system).solve(w), dtype=np.float64)
    residual = float(np.max(np.abs(system @ t - w)))
    if residual > config.numeric_tolerance:
        raise RuntimeError(f"physical-time residual {residual:.3g} out of tolerance")
    out = np.zeros(len(spaces.all_nonzero), dtype=np.float64)
    out[:n_t] = t
    return out


@dataclass(frozen=True)
class Bundle:
    """State-indexed observables for one (rule, contract) system.

    All bundles share the ``all_nonzero`` state list of the atlas so that
    identity couplings are meaningful across contracts. The equal contract's
    fission destinations occupy a subset of columns; its transition matrix is
    embedded into the common space with zeros elsewhere.
    """

    rule_key: int
    contract: str
    states: tuple[Composition, ...]
    launch_rows: np.ndarray
    transition: np.ndarray
    death: np.ndarray
    strict: np.ndarray
    physical_time: np.ndarray
    destination: np.ndarray


def build_bundle(
    rule_key: int,
    beta: np.ndarray,
    contract: str,
    config: AtlasConfig,
    spaces: StateSpaces,
    *,
    strict: np.ndarray,
    absorption: AbsorptionKernel | None = None,
    destination_horizon: int = 8,
) -> Bundle:
    absorption = absorption or solve_absorption(rule_key, beta, config, spaces)
    kernel = build_physical_kernel(absorption, contract, config, spaces)
    n = len(spaces.all_nonzero)
    transition = np.zeros((n, n), dtype=np.float64)
    columns = np.asarray(
        [spaces.all_index[state] for state in kernel.destination_states], dtype=np.int64
    )
    transition[:, columns] = kernel.transition
    launch_rows = np.asarray(
        [idx for idx, state in enumerate(spaces.all_nonzero) if sum(state) == config.n_min],
        dtype=np.int64,
    )
    strict = np.asarray(strict, dtype=np.float64)
    if strict.shape != (len(launch_rows),):
        raise ValueError("strict vector must align with the mass-n_min launch rows")
    destination = np.zeros((len(launch_rows), n), dtype=np.float64)
    destination[np.arange(len(launch_rows)), launch_rows] = 1.0
    for _step in range(destination_horizon):
        destination = np.einsum("ij,jk->ik", destination, transition, optimize=False)
    return Bundle(
        rule_key=rule_key,
        contract=contract,
        states=spaces.all_nonzero,
        launch_rows=launch_rows,
        transition=transition,
        death=kernel.death.copy(),
        strict=strict,
        physical_time=expected_physical_time(beta, config, spaces),
        destination=destination,
    )


def closed_kernel(
    rule_key: int,
    beta: np.ndarray,
    contract: str,
    config: AtlasConfig,
    spaces: StateSpaces,
    absorption: AbsorptionKernel | None = None,
) -> PhysicalKernel:
    absorption = absorption or solve_absorption(rule_key, beta, config, spaces)
    return build_physical_kernel(absorption, contract, config, spaces).square_on_destinations()
