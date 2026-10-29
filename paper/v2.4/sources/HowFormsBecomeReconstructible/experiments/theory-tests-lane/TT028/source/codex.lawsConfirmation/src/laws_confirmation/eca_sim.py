"""Flexible-width ECA lineage simulation for fresh L01/L02 confirmation.

The lifecycle and observer calculations are adapted from the reconciled E19
implementation in ``codex.reconstructionsAndStressTesting/plastic_ca``.  This
module deliberately owns its launch rows and random streams: retained runs are
inputs to the audit, not seed material for the fresh campaign.

Random masks are addressed by trajectory event rather than consumed from one
mutable batch generator.  Consequently, stopping one future (or changing the
observer) cannot shift the random stream used by any other future.  The
resulting Bernoulli draws have the requested marginal probabilities and are
reproducible independently of process scheduling.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import math
from typing import Any, Literal

import numpy as np


ObserverName = Literal["raw4", "particle4"]

_UINT64_MASK = (1 << 64) - 1
_FUTURE_MIX = np.uint64(0xD2B74407B1CE6E93)
_CELL_MIX = np.uint64(0xCA5A826395121157)
_PROCESS_KIND = 0x9E3779B97F4A7C15
_COPY_KIND = 0x94D049BB133111EB


@dataclass(frozen=True)
class LineageContract:
    """Complete execution contract for one rule/width/noise condition."""

    width: int
    flip_noise: float
    copy_error: float
    n_launches: int
    futures_per_launch: int
    namespace: str
    launch_split: str
    activity_budget: int | None = None
    min_sweeps: int = 4
    max_sweeps: int = 128
    horizon: int = 32
    break_horizon: int = 8
    inherit: float = 0.9
    coherence: float = 0.9
    distinct: float = 0.85
    strict_run: int = 8
    form_mass_quantile: float = 0.5

    def __post_init__(self) -> None:
        if self.width < 4:
            raise ValueError("width must be at least four cells")
        if self.n_launches <= 0 or self.futures_per_launch <= 0:
            raise ValueError("launch and future counts must be positive")
        if not self.namespace or not self.launch_split:
            raise ValueError("namespace and launch split must be non-empty")
        if self.min_sweeps <= 0 or self.max_sweeps < self.min_sweeps:
            raise ValueError("invalid sweep bounds")
        if self.horizon <= 0 or self.break_horizon <= 1 or self.strict_run <= 0:
            raise ValueError("invalid lineage horizon")
        if self.resolved_activity_budget <= 0:
            raise ValueError("activity budget must be positive")
        for name, value in (
            ("flip_noise", self.flip_noise),
            ("copy_error", self.copy_error),
            ("inherit", self.inherit),
            ("coherence", self.coherence),
            ("distinct", self.distinct),
            ("form_mass_quantile", self.form_mass_quantile),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1]")

    @property
    def resolved_activity_budget(self) -> int:
        return 4 * self.width if self.activity_budget is None else self.activity_budget

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["resolved_activity_budget"] = self.resolved_activity_budget
        value["execution_semantics"] = {
            "launch_preparation": "none",
            "composition_zero": "first_completed_generation",
            "process_noise_order": "post_rule",
            "activity_count": "realized_post_noise",
            "boundary_death": "timeout_or_terminal_monochrome",
            "observed_daughter": "terminal_pre_copy",
            "copy_draw": "unconditional_for_every_generation_entrant",
            "random_addressing": "trajectory_event_counter_v1",
            "cell_order": "array_index_zero_first",
        }
        return value


@dataclass(frozen=True)
class DomainDictionary:
    codes: frozenset[int]
    coverage: float
    n_distinct_codes: int
    counts: tuple[tuple[int, int], ...]
    seed_rows_hex: tuple[str, ...]


@dataclass(frozen=True)
class LaunchResult:
    launch_index: int
    strict_count: int
    break_by_8_count: int
    survival_sum: int
    first_generation_times: tuple[int, ...]
    form_support: int
    form_n_futures: int
    total_sweeps: int
    death_counts: dict[str, int]


@dataclass(frozen=True)
class ConditionResult:
    rule: int
    observer: ObserverName
    width: int
    flip_noise: float
    copy_error: float
    n_futures: int
    strict_count: int
    break_by_8_count: int
    survival_sum: int
    total_sweeps: int
    launches: tuple[LaunchResult, ...]


def eca_step(states: np.ndarray, rule: int) -> np.ndarray:
    """Apply a numbered ECA rule to periodic Boolean rows of any width."""

    values = np.asarray(states, dtype=np.bool_)
    if values.ndim != 2 or values.shape[1] < 1:
        raise ValueError("states must have shape (n, width)")
    if not 0 <= rule <= 255:
        raise ValueError("an ECA rule must lie in [0, 255]")
    left = np.roll(values, 1, axis=1).astype(np.uint8, copy=False)
    centre = values.astype(np.uint8, copy=False)
    right = np.roll(values, -1, axis=1).astype(np.uint8, copy=False)
    index = (left << 2) | (centre << 1) | right
    return ((np.uint16(rule) >> index) & np.uint16(1)) != 0


def final4_counts(states: np.ndarray) -> np.ndarray:
    """Return the 16-bin cyclic four-mer census for each Boolean row."""

    values = np.asarray(states, dtype=np.bool_)
    if values.ndim != 2 or values.shape[1] < 4:
        raise ValueError("states must have shape (n, width>=4)")
    codes = (
        (np.roll(values, 1, axis=1).astype(np.uint8) << 3)
        | (values.astype(np.uint8) << 2)
        | (np.roll(values, -1, axis=1).astype(np.uint8) << 1)
        | np.roll(values, -2, axis=1).astype(np.uint8)
    )
    counts = np.zeros((values.shape[0], 16), dtype=np.float64)
    for code in range(16):
        counts[:, code] = np.count_nonzero(codes == code, axis=1)
    return counts


def spacetime_codes(histories: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    """Return row-major 3x3 spacetime codes for three equally shaped rows."""

    if len(histories) != 3:
        raise ValueError("exactly three history rows are required")
    shape = histories[0].shape
    if len(shape) != 2 or any(row.shape != shape for row in histories):
        raise ValueError("history batches must share shape (n, width)")
    codes = np.zeros(shape, dtype=np.uint16)
    bit = 0
    for row in histories:
        for delta in (-1, 0, 1):
            codes |= np.roll(row, -delta, axis=1).astype(np.uint16) << bit
            bit += 1
    return codes


def figure_states(
    histories: tuple[np.ndarray, np.ndarray, np.ndarray],
    domain_codes: frozenset[int],
) -> np.ndarray:
    """Mark cells whose local spacetime code lies outside the rule domain."""

    codes = spacetime_codes(histories)
    domain = np.fromiter(sorted(domain_codes), dtype=np.uint16)
    return ~np.isin(codes, domain)


def _hash_bytes(*parts: object, length: int) -> bytes:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return hashlib.shake_256(payload).digest(length)


def hash_launch_row(namespace: str, split: str, index: int, width: int) -> np.ndarray:
    """Create a non-monochrome, expected-half-density launch row."""

    if width < 2 or index < 0:
        raise ValueError("invalid launch row request")
    byte_count = (width + 7) // 8
    raw = _hash_bytes(namespace, "launch-row", split, index, width, length=byte_count)
    integer = int.from_bytes(raw, "little") & ((1 << width) - 1)
    if integer == 0:
        integer = 1
    elif integer == (1 << width) - 1:
        integer ^= 1
    return np.fromiter(
        ((integer >> (width - 1 - position)) & 1 for position in range(width)),
        dtype=np.bool_,
        count=width,
    )


def fixed_density_row(namespace: str, index: int, width: int, density: float) -> np.ndarray:
    """Create a version-independent fixed-density row by hash ranking cells."""

    if not 0.0 <= density <= 1.0:
        raise ValueError("density must lie in [0, 1]")
    count = min(width, max(0, round(width * density)))
    ranked = sorted(
        range(width),
        key=lambda position: (
            hashlib.sha256(
                f"{namespace}\x1fdomain-row\x1f{index}\x1f{width}\x1f{density:.17g}\x1f{position}".encode(
                    "utf-8"
                )
            ).digest(),
            position,
        ),
    )
    row = np.zeros(width, dtype=np.bool_)
    row[ranked[:count]] = True
    return row


def _row_to_hex(row: np.ndarray) -> str:
    value = 0
    for bit in row:
        value = (value << 1) | int(bit)
    digits = math.ceil(len(row) / 4)
    return f"{value:0{digits}x}"


def trajectory_key(rule: int, launch_index: int, contract: LineageContract) -> int:
    """Return the 64-bit key shared by observers for one physical batch."""

    payload = "\x1f".join(
        (
            contract.namespace,
            "trajectory-event-counter-v1",
            str(rule),
            str(contract.width),
            f"{contract.flip_noise:.17g}",
            f"{contract.copy_error:.17g}",
            contract.launch_split,
            str(launch_index),
        )
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")


def _splitmix64(values: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        mixed = values + np.uint64(0x9E3779B97F4A7C15)
        mixed = (mixed ^ (mixed >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        mixed = (mixed ^ (mixed >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return mixed ^ (mixed >> np.uint64(31))


def event_bernoulli_mask(
    key: int,
    future_indices: np.ndarray,
    generation: int,
    event_index: int,
    width: int,
    probability: float,
    *,
    kind: Literal["process", "copy"],
) -> np.ndarray:
    """Draw deterministic Bernoulli masks addressed by physical event."""

    futures = np.asarray(future_indices, dtype=np.uint64)
    if futures.ndim != 1:
        raise ValueError("future indices must be one-dimensional")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must lie in [0, 1]")
    if probability <= 0.0:
        return np.zeros((len(futures), width), dtype=np.bool_)
    if probability >= 1.0:
        return np.ones((len(futures), width), dtype=np.bool_)
    kind_value = _PROCESS_KIND if kind == "process" else _COPY_KIND
    scalar = (
        key
        ^ kind_value
        ^ (((generation + 1) * 0x8CB92BA72F3D8DD7) & _UINT64_MASK)
        ^ (((event_index + 1) * 0xDB4F0B9175AE2165) & _UINT64_MASK)
    )
    cells = np.arange(width, dtype=np.uint64)
    counters = (
        np.uint64(scalar)
        ^ (futures[:, None] * _FUTURE_MIX)
        ^ (cells[None, :] * _CELL_MIX)
    )
    random53 = (_splitmix64(counters) >> np.uint64(11)).astype(np.float64)
    random53 *= 1.0 / float(1 << 53)
    return random53 < probability


def build_domain_dictionary(
    rule: int,
    width: int,
    namespace: str,
    *,
    n_seeds: int = 4,
    burnin: int = 64,
    collect: int = 16,
    coverage_target: float = 0.9,
    cap: int = 64,
) -> DomainDictionary:
    """Build the particle observer's rule- and width-conditioned domain."""

    if not 0 <= rule <= 255:
        raise ValueError("an ECA rule must lie in [0, 255]")
    if width < 4 or n_seeds <= 0 or burnin < 0 or collect <= 0 or cap <= 0:
        raise ValueError("invalid domain dictionary design")
    if not 0.0 <= coverage_target <= 1.0:
        raise ValueError("coverage target must lie in [0, 1]")
    counts: Counter[int] = Counter()
    seed_rows: list[str] = []
    densities = (0.2, 0.4, 0.6, 0.8)
    for seed_index in range(n_seeds):
        row = fixed_density_row(
            namespace,
            seed_index,
            width,
            densities[seed_index % len(densities)],
        )[None, :]
        seed_rows.append(_row_to_hex(row[0]))
        history = [row.copy(), row.copy(), row.copy()]
        for _ in range(burnin):
            row = eca_step(row, rule)
            history = [history[1], history[2], row.copy()]
        for _ in range(collect):
            row = eca_step(row, rule)
            history = [history[1], history[2], row.copy()]
            values, frequencies = np.unique(
                spacetime_codes((history[0], history[1], history[2])),
                return_counts=True,
            )
            counts.update(
                {
                    int(value): int(frequency)
                    for value, frequency in zip(values, frequencies, strict=True)
                }
            )
    total = sum(counts.values())
    selected: list[int] = []
    selected_mass = 0
    for code, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if len(selected) >= cap:
            break
        selected.append(code)
        selected_mass += count
        if total and selected_mass / total >= coverage_target:
            break
    return DomainDictionary(
        codes=frozenset(selected),
        coverage=selected_mass / total if total else 0.0,
        n_distinct_codes=len(counts),
        counts=tuple(sorted(counts.items())),
        seed_rows_hex=tuple(seed_rows),
    )


def _cosine_rows(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    numerator = np.sum(left * right, axis=1)
    denominator = np.linalg.norm(left, axis=1) * np.linalg.norm(right, axis=1)
    result = np.zeros(len(left), dtype=np.float64)
    np.divide(numerator, denominator, out=result, where=denominator != 0.0)
    return result


def _mass_support(vector: np.ndarray, quantile: float) -> int:
    total = float(np.maximum(vector, 0.0).sum())
    if total <= 0.0:
        return 0
    order = sorted(range(len(vector)), key=lambda index: (-float(vector[index]), index))
    threshold = quantile * total
    cumulative = 0.0
    support = 0
    for index in order:
        if vector[index] <= 0.0:
            continue
        cumulative += float(vector[index])
        support |= 1 << index
        if cumulative >= threshold:
            break
    return support


def _update_observer_batch(
    compositions: np.ndarray,
    lengths: np.ndarray,
    first_break: np.ndarray,
    broke_by_8: np.ndarray,
    strict_positive: np.ndarray,
    futures: np.ndarray,
    generation: int,
    observed: np.ndarray,
    contract: LineageContract,
) -> None:
    """Append one observer generation and update E19 event state in batches."""

    compositions[futures, generation] = observed
    lengths[futures] = generation + 1
    if generation < 1:
        return

    similarities = _cosine_rows(
        compositions[futures, generation - 1],
        compositions[futures, generation],
    )
    unseen = first_break[futures] < 0
    newly_broken = unseen & (similarities <= contract.inherit)
    broken_futures = futures[newly_broken]
    first_break[broken_futures] = generation - 1
    if generation - 1 < contract.break_horizon - 1:
        broke_by_8[broken_futures] = True

    length = generation + 1
    if length < contract.strict_run + 2:
        return
    start = length - contract.strict_run - 1
    candidates = futures[
        (first_break[futures] >= 0) & (start >= first_break[futures] + 1)
    ]
    if not len(candidates):
        return

    passed = np.ones(len(candidates), dtype=np.bool_)
    for offset in range(contract.strict_run):
        passed &= _cosine_rows(
            compositions[candidates, start + offset],
            compositions[candidates, start + offset + 1],
        ) > contract.inherit
    if not passed.any():
        return
    candidates = candidates[passed]

    daughters = compositions[
        candidates, start + 1 : start + contract.strict_run + 1
    ]
    passed = np.ones(len(candidates), dtype=np.bool_)
    for left in range(contract.strict_run):
        for right in range(left):
            passed &= _cosine_rows(daughters[:, left], daughters[:, right]) > contract.coherence
    if not passed.any():
        return
    candidates = candidates[passed]
    daughters = daughters[passed]

    anchors = compositions[candidates, first_break[candidates] + 1]
    passed = np.ones(len(candidates), dtype=np.bool_)
    for offset in range(contract.strict_run):
        passed &= _cosine_rows(daughters[:, offset], anchors) <= contract.distinct
    strict_positive[candidates[passed]] = True


def simulate_launch(
    rule: int,
    launch_index: int,
    contract: LineageContract,
    *,
    observer: ObserverName = "raw4",
    domain_codes: frozenset[int] | None = None,
) -> LaunchResult:
    """Simulate all futures associated with one launch profile."""

    if not 0 <= rule <= 255:
        raise ValueError("an ECA rule must lie in [0, 255]")
    if not 0 <= launch_index < contract.n_launches:
        raise ValueError("launch index outside contract")
    if observer == "particle4" and domain_codes is None:
        raise ValueError("particle4 requires a domain dictionary")
    if observer == "raw4" and domain_codes is not None:
        raise ValueError("raw4 does not accept a domain dictionary")

    n = contract.futures_per_launch
    launch = hash_launch_row(
        contract.namespace,
        contract.launch_split,
        launch_index,
        contract.width,
    )
    states = np.repeat(launch[None, :], n, axis=0)
    alive = np.ones(n, dtype=np.bool_)
    strict_positive = np.zeros(n, dtype=np.bool_)
    broke_by_8 = np.zeros(n, dtype=np.bool_)
    first_break = np.full(n, -1, dtype=np.int16)
    lengths = np.zeros(n, dtype=np.int16)
    compositions = np.zeros((n, contract.horizon, 16), dtype=np.float64)
    first_generation_times = np.zeros(n, dtype=np.int16)
    total_sweeps = 0
    deaths: Counter[str] = Counter()
    key = trajectory_key(rule, launch_index, contract)

    for generation in range(contract.horizon):
        batch = np.flatnonzero(alive & ~strict_positive)
        if not len(batch):
            break
        current = states[batch].copy()
        history = [current.copy(), current.copy(), current.copy()]
        batch_size = len(batch)
        activity = np.zeros(batch_size, dtype=np.int32)
        sweeps = np.zeros(batch_size, dtype=np.int16)
        reached_budget = np.zeros(batch_size, dtype=np.bool_)

        for sweep in range(1, contract.max_sweeps + 1):
            active = np.flatnonzero(~reached_budget)
            if not len(active):
                break
            global_futures = batch[active]
            previous = current[active]
            terminal = eca_step(previous, rule)
            terminal ^= event_bernoulli_mask(
                key,
                global_futures,
                generation,
                sweep,
                contract.width,
                contract.flip_noise,
                kind="process",
            )
            activity[active] += np.count_nonzero(terminal != previous, axis=1)
            current[active] = terminal
            history[0][active] = history[1][active]
            history[1][active] = history[2][active]
            history[2][active] = terminal
            sweeps[active] = sweep
            if sweep >= contract.min_sweeps:
                reached_budget[active[activity[active] >= contract.resolved_activity_budget]] = True

        total_sweeps += int(sweeps.sum())
        if generation == 0:
            first_generation_times[batch] = sweeps

        monochrome = (~current.any(axis=1)) | current.all(axis=1)
        timed_out = ~reached_budget
        dead = timed_out | monochrome
        for timeout, mono in zip(timed_out, monochrome, strict=True):
            if timeout and mono:
                deaths["timeout_and_monochrome"] += 1
            elif timeout:
                deaths["timeout"] += 1
            elif mono:
                deaths["monochrome"] += 1

        copy_masks = event_bernoulli_mask(
            key,
            batch,
            generation,
            0,
            contract.width,
            contract.copy_error,
            kind="copy",
        )
        offspring = current ^ copy_masks

        if observer == "raw4":
            observed_states = current
            observer_empty = np.zeros(batch_size, dtype=np.bool_)
        else:
            assert domain_codes is not None
            observed_states = figure_states(
                (history[0], history[1], history[2]), domain_codes
            )
            observer_empty = ~observed_states.any(axis=1)
            deaths["observer_empty"] += int(observer_empty.sum())
        stopped = dead | observer_empty
        divided_local = np.flatnonzero(~stopped)
        if len(divided_local):
            future_indices = batch[divided_local]
            observed = final4_counts(observed_states[divided_local])
            _update_observer_batch(
                compositions,
                lengths,
                first_break,
                broke_by_8,
                strict_positive,
                future_indices,
                generation,
                observed,
                contract,
            )
            states[future_indices] = offspring[divided_local]
        alive[batch[stopped]] = False

    qualifies = (first_break >= 0) & (lengths >= first_break + 2)
    qualifying_futures = np.flatnonzero(qualifies)
    if len(qualifying_futures):
        last = compositions[
            qualifying_futures,
            lengths[qualifying_futures].astype(np.int64) - 1,
        ]
        form_support = _mass_support(
            np.mean(last, axis=0), contract.form_mass_quantile
        )
    else:
        form_support = 0
    return LaunchResult(
        launch_index=launch_index,
        strict_count=int(strict_positive.sum()),
        break_by_8_count=int(broke_by_8.sum()),
        survival_sum=int(lengths.sum()),
        first_generation_times=tuple(int(value) for value in first_generation_times),
        form_support=int(form_support),
        form_n_futures=int(len(qualifying_futures)),
        total_sweeps=total_sweeps,
        death_counts=dict(sorted(deaths.items())),
    )


def evaluate_condition(
    rule: int,
    contract: LineageContract,
    *,
    observer: ObserverName,
    domain_codes: frozenset[int] | None = None,
) -> ConditionResult:
    """Evaluate all launch profiles for one rule/condition."""

    launches = tuple(
        simulate_launch(
            rule,
            launch_index,
            contract,
            observer=observer,
            domain_codes=domain_codes,
        )
        for launch_index in range(contract.n_launches)
    )
    return ConditionResult(
        rule=rule,
        observer=observer,
        width=contract.width,
        flip_noise=contract.flip_noise,
        copy_error=contract.copy_error,
        n_futures=contract.n_launches * contract.futures_per_launch,
        strict_count=sum(item.strict_count for item in launches),
        break_by_8_count=sum(item.break_by_8_count for item in launches),
        survival_sum=sum(item.survival_sum for item in launches),
        total_sweeps=sum(item.total_sweeps for item in launches),
        launches=launches,
    )
