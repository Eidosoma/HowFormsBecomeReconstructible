"""Contract-agnostic strict-event machinery: census, exact DPs, sampler.

The exact automaton approach of ``finite_gard_ruliad.strict8`` is
algorithmically contract-agnostic, but the binomial closure (164 destination
states in the full universe) makes the automaton combinatorially infeasible
to materialize there. This module therefore provides:

- a budgeted per-anchor census that measures automaton size without
  materializing edges, producing a machine-readable feasibility verdict;
- a generalized exact backward DP (gated on that verdict) and a generalized,
  key-budgeted forward reference DP that also emits success-by-step curves;
- a generalized trajectory sampler recording the first success step per
  future, usable on either contract with a capsule-specific seed tag.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np
from scipy import sparse

from finite_gard_ruliad.combinatorics import Composition, cosine
from finite_gard_ruliad.config import AtlasConfig
from finite_gard_ruliad.kernels import PhysicalKernel
from finite_gard_ruliad.strict8 import (
    StrictResult,
    _strict_topology,
    maximal_coherence_cliques,
    seed_from_tag,
)


class FeasibilityExceeded(RuntimeError):
    """The strict automaton exceeds the registered census bound."""


@dataclass(frozen=True)
class CensusResult:
    contract: str
    n_pre: int
    n_cliques: int
    n_anchors: int
    anchor_counts: tuple[int, ...]
    anchor_complete: tuple[bool, ...]
    post_states_lower_bound: int
    complete: bool
    within_bound: bool
    edge_upper_bound_per_state: int
    elapsed_seconds: float

    def as_dict(self) -> dict:
        return {
            "contract": self.contract,
            "n_pre": self.n_pre,
            "n_cliques": self.n_cliques,
            "n_anchors": self.n_anchors,
            "anchor_counts": list(self.anchor_counts),
            "anchor_complete": list(self.anchor_complete),
            "post_states_lower_bound": self.post_states_lower_bound,
            "complete": self.complete,
            "within_bound": self.within_bound,
            "edge_upper_bound_per_state": self.edge_upper_bound_per_state,
            "elapsed_seconds": self.elapsed_seconds,
        }


def _strict_geometry(
    states: tuple[Composition, ...],
    parents: tuple[Composition, ...],
    fission: np.ndarray,
    inherit_t: float,
    cohere_t: float,
    distinct_t: float,
):
    support = fission > 0.0
    h = np.asarray(
        [[cosine(parent, daughter) for daughter in states] for parent in parents],
        dtype=np.float64,
    )
    break_support = support & (h <= inherit_t)
    inherit_support = support & (h > inherit_t)
    broken_destinations = tuple(int(v) for v in np.flatnonzero(break_support.any(axis=0)))
    inherited_destinations = tuple(
        int(v) for v in np.flatnonzero(inherit_support.any(axis=0))
    )
    cliques = maximal_coherence_cliques(states, cohere_t)
    memberships = tuple(
        tuple(ci for ci, clique in enumerate(cliques) if state_id in clique)
        for state_id in range(len(states))
    )
    distinct = np.asarray(
        [[cosine(parent, daughter) <= distinct_t for daughter in states] for parent in parents],
        dtype=bool,
    )
    return break_support, broken_destinations, inherited_destinations, cliques, memberships, distinct


def automaton_census(
    kernel: PhysicalKernel,
    config: AtlasConfig,
    *,
    state_bound: int,
    seconds_budget: float,
) -> CensusResult:
    """Measure the strict automaton size per anchor without building edges.

    Post-break states are ``(current, anchor, counts)`` triples; the anchor
    never changes after the first break, so each anchor block is enumerated
    independently. Counts are stored sparsely as sorted nonzero
    ``(clique, count)`` pairs, a bijective compression of the dense tuple used
    by ``finite_gard_ruliad.strict8._strict_topology``.
    """
    if kernel.launch_states != kernel.destination_states:
        raise ValueError("census requires a closed kernel")
    states = kernel.destination_states
    parents = kernel.parents
    run = config.strict_run
    (
        break_support,
        broken_destinations,
        inherited_destinations,
        cliques,
        memberships,
        distinct,
    ) = _strict_geometry(
        states,
        parents,
        kernel.fission,
        config.inherit_threshold,
        config.coherence_threshold,
        config.distinct_threshold,
    )

    anchors = tuple(int(v) for v in np.flatnonzero(break_support.any(axis=1)))
    started = time.time()
    anchor_counts: list[int] = []
    anchor_complete: list[bool] = []
    total = 0
    all_complete = True

    for anchor in anchors:
        seeds = {
            (int(daughter), ()) for daughter in np.flatnonzero(break_support[anchor])
        }
        # Every anchor block also absorbs later-break resets to any globally
        # break-supported daughter, mirroring the joint BFS in strict8.
        discovered = set(seeds)
        pending = list(seeds)
        complete = True
        while pending:
            if len(discovered) > state_bound or time.time() - started > seconds_budget:
                complete = False
                break
            current, counts_key = pending.pop()
            counts = dict(counts_key)
            destinations: list[tuple[int, tuple[tuple[int, int], ...]]] = [
                (daughter, ()) for daughter in broken_destinations
            ]
            for daughter in inherited_destinations:
                if distinct[anchor, daughter]:
                    updated = tuple(
                        sorted(
                            (clique_id, counts.get(clique_id, 0) + 1)
                            for clique_id in memberships[daughter]
                        )
                    )
                else:
                    updated = ()
                if updated and max(v for _, v in updated) >= run:
                    continue
                destinations.append((daughter, updated))
            for destination in destinations:
                if destination not in discovered:
                    discovered.add(destination)
                    pending.append(destination)
        anchor_counts.append(len(discovered))
        anchor_complete.append(complete)
        total += len(discovered)
        all_complete = all_complete and complete
        if total > state_bound:
            all_complete = all_complete and complete
            # Keep the totals honest but stop enumerating further anchors.
            remaining = len(anchors) - len(anchor_counts)
            anchor_counts.extend([0] * remaining)
            anchor_complete.extend([False] * remaining)
            all_complete = False
            break

    within = all_complete and total <= state_bound
    return CensusResult(
        contract=kernel.contract,
        n_pre=len(states),
        n_cliques=len(cliques),
        n_anchors=len(anchors),
        anchor_counts=tuple(anchor_counts),
        anchor_complete=tuple(anchor_complete),
        post_states_lower_bound=total,
        complete=all_complete,
        within_bound=within,
        edge_upper_bound_per_state=len(broken_destinations) + len(inherited_destinations),
        elapsed_seconds=time.time() - started,
    )


def exact_strict_probabilities_any(
    kernel: PhysicalKernel,
    config: AtlasConfig,
    *,
    launch_mass: int | None = None,
    horizon: int | None = None,
    run: int | None = None,
    precheck_state_bound: int | None = None,
    precheck_seconds: float = 120.0,
) -> StrictResult:
    """Exact strict probabilities for any closed kernel via the automaton.

    This is the contract-agnostic form of
    ``finite_gard_ruliad.strict8.exact_strict_probabilities``. When
    ``precheck_state_bound`` is given, a census runs first and the function
    raises :class:`FeasibilityExceeded` instead of attempting to materialize
    an oversized automaton.
    """
    if kernel.launch_states != kernel.destination_states:
        raise ValueError("exact strict DP requires a closed kernel")
    horizon = config.strict_horizon if horizon is None else int(horizon)
    run = config.strict_run if run is None else int(run)
    if precheck_state_bound is not None:
        census = automaton_census(
            kernel,
            config,
            state_bound=precheck_state_bound,
            seconds_budget=precheck_seconds,
        )
        if not census.within_bound:
            raise FeasibilityExceeded(
                f"{kernel.contract} automaton exceeds {precheck_state_bound} states"
            )

    states = kernel.destination_states
    parents = kernel.parents
    support = tuple(tuple(bool(v > 0.0) for v in row) for row in kernel.fission)
    topology = _strict_topology(
        states,
        parents,
        support,
        float(config.inherit_threshold),
        float(config.coherence_threshold),
        float(config.distinct_threshold),
        run,
    )

    joint = kernel.joint()
    h = np.asarray(
        [[cosine(parent, daughter) for daughter in states] for parent in parents],
        dtype=np.float64,
    )
    inherited_mask = h > config.inherit_threshold
    inherited = np.einsum("xpy,py->xy", joint, inherited_mask, optimize=False)
    broken = np.einsum("xpy,py->xy", joint, ~inherited_mask, optimize=False)
    break_anchor = joint * (~inherited_mask)[None, :, :]

    edge_values = np.concatenate(
        [
            inherited[topology.inherit_x, topology.inherit_daughter],
            broken[topology.broken_x, topology.broken_daughter],
            break_anchor[
                topology.anchor_x, topology.anchor_parent, topology.anchor_daughter
            ],
        ]
    )
    edge_sources = np.concatenate(
        [topology.inherit_source, topology.broken_source, topology.anchor_source]
    )
    edge_targets = np.concatenate(
        [topology.inherit_target, topology.broken_target, topology.anchor_target]
    )
    positive = edge_values > 0.0
    transition = sparse.csr_matrix(
        (edge_values[positive], (edge_sources[positive], edge_targets[positive])),
        shape=(topology.n_states, topology.n_states),
    )
    success = np.zeros(topology.n_states, dtype=np.float64)
    np.add.at(
        success,
        topology.success_source,
        inherited[topology.success_x, topology.success_daughter],
    )

    future = np.zeros(topology.n_states, dtype=np.float64)
    for _step in range(horizon):
        future = success + transition.dot(future)
    probabilities = future[: topology.n_pre]
    tol = config.numeric_tolerance
    if not np.isfinite(probabilities).all():
        raise RuntimeError("strict-event probability is non-finite")
    if float(probabilities.min()) < -tol or float(probabilities.max()) > 1 + tol:
        raise RuntimeError("strict-event probability left [0,1]")
    probabilities = probabilities.copy()
    probabilities[np.abs(probabilities) < tol * 0.01] = 0.0
    if launch_mass is not None:
        rows = np.asarray(
            [idx for idx, state in enumerate(states) if sum(state) == launch_mass],
            dtype=np.int64,
        )
        probabilities = probabilities[rows]
    return StrictResult(probabilities, topology.post_states, topology.cliques)


class ForwardBudgetExceeded(RuntimeError):
    """The forward DP exceeded its registered key budget."""


@dataclass(frozen=True)
class ForwardResult:
    launch_states: tuple[Composition, ...]
    success_by_step: np.ndarray  # (horizon, n_launch) cumulative probability
    peak_keys: int


def forward_reference_any(
    kernel: PhysicalKernel,
    config: AtlasConfig,
    *,
    launch_mass: int | None = None,
    horizon: int | None = None,
    run: int | None = None,
    key_budget: int | None = None,
) -> ForwardResult:
    """Generalized dict-based forward DP emitting success-by-step curves.

    An independent re-derivation of the strict recursion (no automaton), kept
    deliberately close to ``_exact_strict_probabilities_forward`` in
    ``finite_gard_ruliad.strict8`` but valid for any closed kernel, filtered
    to ``launch_mass`` rows, and guarded by an explicit key budget so it can
    be attempted safely at truncated horizons in the full binomial universe.
    """
    if kernel.launch_states != kernel.destination_states:
        raise ValueError("forward strict DP requires a closed kernel")
    horizon = config.strict_horizon if horizon is None else int(horizon)
    run = config.strict_run if run is None else int(run)
    states = kernel.destination_states
    parents = kernel.parents
    n_states = len(states)
    if launch_mass is None:
        launch_ids = list(range(n_states))
    else:
        launch_ids = [i for i, s in enumerate(states) if sum(s) == launch_mass]
    n_launch = len(launch_ids)

    cliques = maximal_coherence_cliques(states, config.coherence_threshold)
    memberships = tuple(
        tuple(ci for ci, clique in enumerate(cliques) if state_id in clique)
        for state_id in range(n_states)
    )
    distinct = np.asarray(
        [[cosine(parent, s) <= config.distinct_threshold for s in states] for parent in parents],
        dtype=bool,
    )
    joint = kernel.joint()
    h = np.asarray(
        [[cosine(parent, daughter) for daughter in states] for parent in parents],
        dtype=np.float64,
    )
    inherited_mask = h > config.inherit_threshold
    inherited = np.einsum("xpy,py->xy", joint, inherited_mask, optimize=False)
    broken = np.einsum("xpy,py->xy", joint, ~inherited_mask, optimize=False)
    break_anchor = joint * (~inherited_mask)[None, :, :]

    pre = np.zeros((n_launch, n_states), dtype=np.float64)
    for row, launch in enumerate(launch_ids):
        pre[row, launch] = 1.0
    post: dict[tuple[int, int, tuple[tuple[int, int], ...]], np.ndarray] = {}
    success = np.zeros(n_launch, dtype=np.float64)
    success_by_step = np.zeros((horizon, n_launch), dtype=np.float64)
    peak = 0

    def add(target, key, value) -> None:
        if not np.any(value):
            return
        if key in target:
            target[key] += value
        else:
            target[key] = value.copy()

    for step in range(horizon):
        next_pre = np.einsum("ij,jk->ik", pre, inherited, optimize=False)
        next_post: dict[tuple[int, int, tuple[tuple[int, int], ...]], np.ndarray] = {}

        for x in range(n_states):
            origin = pre[:, x]
            if not np.any(origin):
                continue
            for parent_id, daughter_id in np.argwhere(break_anchor[x] > 0.0):
                add(
                    next_post,
                    (int(daughter_id), int(parent_id), ()),
                    origin * break_anchor[x, parent_id, daughter_id],
                )

        for (x, anchor, counts_key), origin in post.items():
            counts = dict(counts_key)
            for daughter_id in np.flatnonzero(broken[x] > 0.0):
                add(next_post, (int(daughter_id), anchor, ()), origin * broken[x, daughter_id])
            for daughter_id in np.flatnonzero(inherited[x] > 0.0):
                if distinct[anchor, daughter_id]:
                    updated = tuple(
                        sorted(
                            (clique_id, counts.get(clique_id, 0) + 1)
                            for clique_id in memberships[daughter_id]
                        )
                    )
                else:
                    updated = ()
                probability = inherited[x, daughter_id]
                if updated and max(v for _, v in updated) >= run:
                    success += origin * probability
                else:
                    add(next_post, (int(daughter_id), anchor, updated), origin * probability)

        pre = next_pre
        post = next_post
        peak = max(peak, len(post))
        if key_budget is not None and peak > key_budget:
            raise ForwardBudgetExceeded(
                f"forward DP exceeded {key_budget} keys at step {step + 1}"
            )
        success_by_step[step] = success

    tol = config.numeric_tolerance
    if float(success.min()) < -tol or float(success.max()) > 1 + tol:
        raise RuntimeError("strict-event probability left [0,1]")
    return ForwardResult(
        launch_states=tuple(states[i] for i in launch_ids),
        success_by_step=success_by_step,
        peak_keys=peak,
    )


@dataclass(frozen=True)
class PathDiagnostic:
    launch_states: tuple[Composition, ...]
    probability: np.ndarray  # (n_launch,)
    half_a: np.ndarray
    half_b: np.ndarray
    success_step: np.ndarray  # (n_launch, n_futures) int16, -1 = no success
    n_futures: int


def simulate_strict_paths(
    kernel: PhysicalKernel,
    config: AtlasConfig,
    *,
    rule_key: int,
    n_futures: int,
    seed_tag: str,
) -> PathDiagnostic:
    """Sample strict histories from any exact closed kernel.

    Growth and fission draws are exact inverse-CDF samples; only the
    horizon-history probability is estimated. This generalizes
    ``finite_gard_ruliad.strict8.simulate_binomial_strict`` to either
    contract, records the first success step per future, and takes an
    explicit seed tag so this capsule never reuses the sealed E1 stream.
    """
    if kernel.launch_states != kernel.destination_states:
        raise ValueError("path sampler requires a closed kernel")
    if n_futures % 2:
        raise ValueError("n_futures must be even for the fixed half split")
    states = kernel.destination_states
    parents = kernel.parents
    launch_ids = [idx for idx, state in enumerate(states) if sum(state) == config.n_min]
    h = np.asarray(
        [[cosine(parent, daughter) for daughter in states] for parent in parents],
        dtype=np.float64,
    )
    coherent = np.asarray(
        [[cosine(left, right) > config.coherence_threshold for right in states] for left in states],
        dtype=bool,
    )
    distinct = np.asarray(
        [[cosine(parent, daughter) <= config.distinct_threshold for daughter in states] for parent in parents],
        dtype=bool,
    )
    absorption_cdf = np.cumsum(
        np.column_stack([kernel.death, kernel.absorption_parent]), axis=1
    )
    fission_cdf = np.cumsum(kernel.fission, axis=1)
    absorption_cdf[:, -1] = 1.0
    fission_cdf[:, -1] = 1.0
    positives = np.zeros((len(launch_ids), n_futures), dtype=bool)
    success_step = np.full((len(launch_ids), n_futures), -1, dtype=np.int16)

    for launch_row, launch_id in enumerate(launch_ids):
        rng = seed_from_tag(seed_tag, rule_key, launch_id)
        current = np.full(n_futures, launch_id, dtype=np.int32)
        alive = np.ones(n_futures, dtype=bool)
        seen_break = np.zeros(n_futures, dtype=bool)
        anchor = np.full(n_futures, -1, dtype=np.int16)
        recent = np.full((n_futures, config.strict_run), -1, dtype=np.int16)
        run_length = np.zeros(n_futures, dtype=np.int16)

        for step in range(config.strict_horizon):
            active = np.flatnonzero(alive & ~positives[launch_row])
            if active.size == 0:
                break
            parent_draw = np.full(active.size, -1, dtype=np.int16)
            for state_id in np.unique(current[active]):
                positions = np.flatnonzero(current[active] == state_id)
                u = rng.random(len(positions))
                parent_draw[positions] = np.searchsorted(
                    absorption_cdf[state_id], u, side="right"
                ) - 1  # -1 is death; 0..n_parent-1 are parents
            died_positions = active[parent_draw < 0]
            alive[died_positions] = False
            live_local = np.flatnonzero(parent_draw >= 0)
            if live_local.size == 0:
                continue
            live = active[live_local]
            parent_ids = parent_draw[live_local]
            daughter_ids = np.empty(len(live), dtype=np.int32)
            for parent_id in np.unique(parent_ids):
                positions = np.flatnonzero(parent_ids == parent_id)
                daughter_ids[positions] = np.searchsorted(
                    fission_cdf[parent_id], rng.random(len(positions)), side="right"
                )

            inherited = h[parent_ids, daughter_ids] > config.inherit_threshold
            first_break = (~inherited) & (~seen_break[live])
            if np.any(first_break):
                rows = live[first_break]
                seen_break[rows] = True
                anchor[rows] = parent_ids[first_break]
                recent[rows] = -1
                run_length[rows] = 0

            later_break = (~inherited) & seen_break[live] & (~first_break)
            if np.any(later_break):
                rows = live[later_break]
                recent[rows] = -1
                run_length[rows] = 0

            continuing = inherited & seen_break[live]
            if np.any(continuing):
                rows = live[continuing]
                daughters = daughter_ids[continuing]
                recent[rows, :-1] = recent[rows, 1:]
                recent[rows, -1] = daughters
                run_length[rows] = np.minimum(run_length[rows] + 1, config.strict_run)
                ready = rows[run_length[rows] >= config.strict_run]
                if ready.size:
                    windows = recent[ready]
                    anchor_ok = distinct[anchor[ready, None], windows].all(axis=1)
                    pair_ok = np.ones(len(ready), dtype=bool)
                    for a in range(config.strict_run):
                        for b in range(a + 1, config.strict_run):
                            pair_ok &= coherent[windows[:, a], windows[:, b]]
                    hits = ready[anchor_ok & pair_ok]
                    positives[launch_row, hits] = True
                    success_step[launch_row, hits] = step
            current[live] = daughter_ids

    half = n_futures // 2
    return PathDiagnostic(
        launch_states=tuple(states[i] for i in launch_ids),
        probability=positives.mean(axis=1),
        half_a=positives[:, :half].mean(axis=1),
        half_b=positives[:, half:].mean(axis=1),
        success_step=success_step,
        n_futures=n_futures,
    )
