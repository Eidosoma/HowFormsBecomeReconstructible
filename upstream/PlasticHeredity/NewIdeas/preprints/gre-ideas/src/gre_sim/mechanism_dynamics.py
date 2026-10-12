"""Engine variants used to causally decompose Boolean--Wagner differences."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np

from .boolean import BooleanRulebook
from .engines import Rulebook
from .landscape import (
    Landscape,
    bits_to_int,
    canonical_cycle,
    enumerate_landscape,
    int_to_bits,
    int_to_signs,
    signs_to_int,
)
from .types import DevelopmentResult
from .wagner import WagnerRulebook


def boolean_sequential_step(rulebook: BooleanRulebook, state: int) -> int:
    """Update Boolean genes in index order, exposing earlier in-sweep changes."""

    current = int(state)
    for gene in range(rulebook.genes):
        value = int(rulebook.truth_table[gene, current])
        if value:
            current |= 1 << gene
        else:
            current &= ~(1 << gene)
    return current


def wagner_synchronous_step(
    rulebook: WagnerRulebook,
    state: int,
    multipliers: np.ndarray | None = None,
) -> int:
    """Update all Wagner genes from the same pre-sweep state."""

    signs = int_to_signs(int(state), rulebook.genes)
    fields = rulebook.effective_weights(multipliers) @ signs + rulebook.bias
    updated = signs.copy()
    updated[fields > 0.0] = 1
    updated[fields < 0.0] = -1
    return signs_to_int(updated)


def successor_table(
    rulebook: Rulebook,
    variant: str,
    compiled_update_mode: str = "sequential",
) -> np.ndarray:
    """Enumerate the deterministic global successor map for one variant."""

    if isinstance(rulebook, BooleanRulebook):
        if variant == "boolean_sync":
            result = rulebook.successor.copy()
        elif variant == "boolean_sequential":
            result = np.asarray(
                [boolean_sequential_step(rulebook, state) for state in range(rulebook.state_count)],
                dtype=np.int64,
            )
        else:
            raise TypeError(f"variant {variant} cannot use a Boolean source")
    elif isinstance(rulebook, WagnerRulebook):
        if variant == "wagner_sequential":
            result = rulebook.successor_table().copy()
        elif variant == "wagner_synchronous":
            result = np.asarray(
                [wagner_synchronous_step(rulebook, state) for state in range(rulebook.state_count)],
                dtype=np.int64,
            )
        elif variant == "wagner_compiled":
            source_variant = (
                "wagner_sequential"
                if compiled_update_mode == "sequential"
                else "wagner_synchronous"
            )
            result = successor_table(rulebook, source_variant)
        else:
            raise TypeError(f"variant {variant} cannot use a Wagner source")
    else:  # pragma: no cover - protected by the Rulebook union.
        raise TypeError(type(rulebook))
    result = np.asarray(result, dtype=np.int64)
    result.setflags(write=False)
    return result


def _develop_successor(
    transitions: np.ndarray,
    initial_state: int,
    max_steps: int,
) -> DevelopmentResult:
    current = int(initial_state)
    positions: dict[int, int] = {}
    path: list[int] = []
    for step_index in range(max_steps):
        if current in positions:
            cycle = canonical_cycle(path[positions[current] :])
            if len(cycle) == 1:
                return DevelopmentResult("point", cycle[0], step_index, cycle)
            return DevelopmentResult("cycle", current, step_index, cycle)
        positions[current] = len(path)
        path.append(current)
        following = int(transitions[current])
        if following == current:
            return DevelopmentResult("point", current, step_index + 1, (current,))
        current = following
    return DevelopmentResult("nonconvergent", current, max_steps, ())


@dataclass(frozen=True)
class MechanismRulebook:
    """A source rulebook viewed through a selected update implementation."""

    source: Rulebook
    variant: str
    compiled_update_mode: str = "sequential"

    @property
    def genes(self) -> int:
        return self.source.genes

    @property
    def state_count(self) -> int:
        return self.source.state_count

    @cached_property
    def _successor_table(self) -> np.ndarray:
        return successor_table(self.source, self.variant, self.compiled_update_mode)

    def successor_table(self) -> np.ndarray:
        """Return the immutable deterministic map, constructing it only once."""

        return self._successor_table

    @cached_property
    def _landscape(self) -> Landscape:
        return enumerate_landscape(self.successor_table())

    def landscape(self) -> Landscape:
        return self._landscape

    def step(self, state: int, multipliers: np.ndarray | None = None) -> int:
        if isinstance(self.source, BooleanRulebook):
            if multipliers is not None:
                raise ValueError("Boolean mechanism variants do not use weight noise")
            if self.variant == "boolean_sync":
                return self.source.step(state)
            if self.variant == "boolean_sequential":
                return boolean_sequential_step(self.source, state)
        elif isinstance(self.source, WagnerRulebook):
            if self.variant == "wagner_sequential":
                return self.source.step(state, multipliers)
            if self.variant == "wagner_synchronous":
                return wagner_synchronous_step(self.source, state, multipliers)
            if self.variant == "wagner_compiled":
                if multipliers is not None:
                    raise ValueError("compiled Wagner is a fixed deterministic map")
                return int(self.successor_table()[state])
        raise TypeError(f"variant {self.variant} is incompatible with {type(self.source)}")

    def develop(
        self,
        initial_state: int,
        multipliers: np.ndarray | None = None,
        max_sweeps: int = 100,
    ) -> DevelopmentResult:
        if self.variant == "wagner_compiled":
            return _develop_successor(
                self.successor_table(), initial_state, max_sweeps
            )
        current = int(initial_state)
        positions: dict[int, int] = {}
        path: list[int] = []
        for sweep in range(max_sweeps):
            if current in positions:
                cycle = canonical_cycle(path[positions[current] :])
                if len(cycle) == 1:
                    return DevelopmentResult("point", cycle[0], sweep, cycle)
                return DevelopmentResult("cycle", current, sweep, cycle)
            positions[current] = len(path)
            path.append(current)
            following = self.step(current, multipliers)
            if following == current:
                return DevelopmentResult("point", current, sweep + 1, (current,))
            current = following
        return DevelopmentResult("nonconvergent", current, max_sweeps, ())


def compile_wagner(
    rulebook: WagnerRulebook, update_mode: str = "sequential"
) -> BooleanRulebook:
    """Compile a deterministic Wagner sweep into an exactly equal Boolean map."""

    variant = (
        "wagner_sequential" if update_mode == "sequential" else "wagner_synchronous"
    )
    if update_mode not in {"sequential", "synchronous"}:
        raise ValueError("unknown Wagner update mode")
    return BooleanRulebook.from_successor(successor_table(rulebook, variant))


def state_after_boolean_sequential_gene(
    rulebook: BooleanRulebook, state: int, genes_to_update: int
) -> int:
    """Test helper exposing a prefix of the sequential Boolean sweep."""

    if not 0 <= genes_to_update <= rulebook.genes:
        raise ValueError("invalid Boolean update prefix")
    bits = int_to_bits(state, rulebook.genes)
    current = bits_to_int(bits)
    for gene in range(genes_to_update):
        value = int(rulebook.truth_table[gene, current])
        if value:
            current |= 1 << gene
        else:
            current &= ~(1 << gene)
    return current
