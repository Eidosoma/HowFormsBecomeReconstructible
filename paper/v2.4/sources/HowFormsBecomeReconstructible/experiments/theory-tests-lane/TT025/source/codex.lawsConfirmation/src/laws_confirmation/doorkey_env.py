"""Small deterministic DoorKey world with explicit causal-chain telemetry.

This is benchmark apparatus, not a scientific result and not an implementation
of MiniGrid.  Its public action count is fixed at eight to match the unchanged
PHRL-0 germ payload.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Mapping, Sequence

import numpy as np


Position = tuple[int, int]


class Action(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3
    PICKUP = 4
    OPEN = 5
    DROP = 6
    WAIT = 7


MOVE_DELTAS: Mapping[Action, Position] = {
    Action.NORTH: (-1, 0),
    Action.EAST: (0, 1),
    Action.SOUTH: (1, 0),
    Action.WEST: (0, -1),
}

CAUSAL_CHAIN = (
    "explore",
    "find_key",
    "retain_key",
    "find_door",
    "open_door",
    "reach_goal",
)

TRANSFORMS = ("identity", "rot90", "rot180", "rot270")


@dataclass(frozen=True)
class DoorKeyLayout:
    size: int
    walls: frozenset[Position]
    start: Position
    key: Position
    door: Position
    goal: Position
    seed: int
    transform: str

    def validate(self) -> None:
        if self.size < 7:
            raise ValueError("layout is too small")
        if self.transform not in TRANSFORMS:
            raise ValueError(f"unknown transform: {self.transform}")
        named = (self.start, self.key, self.door, self.goal)
        if len(set(named)) != len(named):
            raise ValueError("start, key, door, and goal must be distinct")
        for position in named:
            row, column = position
            if not (0 <= row < self.size and 0 <= column < self.size):
                raise ValueError(f"position outside layout: {position}")
            if position in self.walls:
                raise ValueError(f"named position is a wall: {position}")
        for index in range(self.size):
            if (0, index) not in self.walls or (self.size - 1, index) not in self.walls:
                raise ValueError("outer horizontal boundary must be walled")
            if (index, 0) not in self.walls or (index, self.size - 1) not in self.walls:
                raise ValueError("outer vertical boundary must be walled")


@dataclass(frozen=True)
class DoorKeyObservation:
    tiles: np.ndarray
    has_key: bool
    standing_on_key: bool
    door_open: bool
    step_fraction: float

    def vector(self) -> np.ndarray:
        scalars = np.asarray(
            (
                float(self.has_key),
                float(self.standing_on_key),
                float(self.door_open),
                self.step_fraction,
            ),
            dtype=np.float32,
        )
        return np.concatenate((self.tiles.astype(np.float32).ravel(), scalars))


@dataclass(frozen=True)
class WorldState:
    position: Position
    has_key: bool
    key_position: Position | None
    door_open: bool


def _transform_position(position: Position, size: int, transform: str) -> Position:
    row, column = position
    if transform == "identity":
        return row, column
    if transform == "rot90":
        return column, size - 1 - row
    if transform == "rot180":
        return size - 1 - row, size - 1 - column
    if transform == "rot270":
        return size - 1 - column, row
    raise ValueError(f"unknown transform: {transform}")


def make_layout(
    seed: int,
    transform: str = "identity",
    size: int = 9,
) -> DoorKeyLayout:
    """Generate a two-room task, then apply a registered rigid rotation."""

    if size != 9:
        raise ValueError("stage-A generator is frozen at a 9x9 grid")
    if transform not in TRANSFORMS:
        raise ValueError(f"unknown transform: {transform}")
    rng = np.random.default_rng(seed)
    divider = size // 2
    walls: set[Position] = set()
    for index in range(size):
        walls.update(((0, index), (size - 1, index), (index, 0), (index, size - 1)))
    door_row = int(rng.integers(2, size - 2))
    for row in range(1, size - 1):
        if row != door_row:
            walls.add((row, divider))
    door = (door_row, divider)

    left = [(row, column) for row in range(1, size - 1) for column in range(1, divider)]
    right = [
        (row, column)
        for row in range(1, size - 1)
        for column in range(divider + 1, size - 1)
    ]
    left_door_neighbor = (door_row, divider - 1)
    right_door_neighbor = (door_row, divider + 1)

    admissible_pairs = [
        (start, key)
        for start in left
        for key in left
        if start != key
        and _manhattan(start, key) >= 4
        and _manhattan(key, left_door_neighbor) >= 4
    ]
    if not admissible_pairs:
        raise RuntimeError("no admissible start/key pair")
    start, key = admissible_pairs[int(rng.integers(len(admissible_pairs)))]
    admissible_goals = [
        goal for goal in right if _manhattan(goal, right_door_neighbor) >= 4
    ]
    goal = admissible_goals[int(rng.integers(len(admissible_goals)))]

    transform_one = lambda value: _transform_position(value, size, transform)
    layout = DoorKeyLayout(
        size=size,
        walls=frozenset(transform_one(position) for position in walls),
        start=transform_one(start),
        key=transform_one(key),
        door=transform_one(door),
        goal=transform_one(goal),
        seed=int(seed),
        transform=transform,
    )
    layout.validate()
    return layout


def _manhattan(left: Position, right: Position) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _add(left: Position, right: Position) -> Position:
    return left[0] + right[0], left[1] + right[1]


def _passable(layout: DoorKeyLayout, position: Position, door_open: bool) -> bool:
    if position in layout.walls:
        return False
    if position == layout.door and not door_open:
        return False
    row, column = position
    return 0 <= row < layout.size and 0 <= column < layout.size


def _shortest_moves(
    layout: DoorKeyLayout,
    start: Position,
    targets: Iterable[Position],
    door_open: bool,
) -> list[Action]:
    target_set = frozenset(targets)
    queue: deque[Position] = deque((start,))
    predecessor: dict[Position, tuple[Position, Action] | None] = {start: None}
    reached: Position | None = start if start in target_set else None
    while queue and reached is None:
        position = queue.popleft()
        for action, delta in MOVE_DELTAS.items():
            candidate = _add(position, delta)
            if candidate in predecessor or not _passable(layout, candidate, door_open):
                continue
            predecessor[candidate] = (position, action)
            if candidate in target_set:
                reached = candidate
                break
            queue.append(candidate)
    if reached is None:
        raise RuntimeError("target is unreachable")
    actions: list[Action] = []
    cursor = reached
    while predecessor[cursor] is not None:
        previous, action = predecessor[cursor]  # type: ignore[misc]
        actions.append(action)
        cursor = previous
    actions.reverse()
    return actions


def oracle_plan(layout: DoorKeyLayout) -> list[Action]:
    """Return a shortest phase-wise plan using privileged layout knowledge."""

    to_key = _shortest_moves(layout, layout.start, (layout.key,), door_open=False)
    position = layout.key
    neighbors = tuple(
        _add(layout.door, delta)
        for delta in MOVE_DELTAS.values()
        if _passable(layout, _add(layout.door, delta), door_open=False)
    )
    to_door = _shortest_moves(layout, position, neighbors, door_open=False)
    for action in to_door:
        position = _add(position, MOVE_DELTAS[action])
    to_goal = _shortest_moves(layout, position, (layout.goal,), door_open=True)
    return [*to_key, Action.PICKUP, *to_door, Action.OPEN, *to_goal]


class DoorKeyEnv:
    """Deterministic partially observed environment with event timestamps."""

    # Tile codes are public rulebook, not inherited state.
    EMPTY = 0
    WALL = 1
    KEY = 2
    DOOR_CLOSED = 3
    DOOR_OPEN = 4
    GOAL = 5
    AGENT = 6
    OUTSIDE = 7

    def __init__(
        self,
        layout: DoorKeyLayout,
        *,
        max_steps: int = 128,
        view_radius: int = 1,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        if view_radius < 1:
            raise ValueError("view_radius must be positive")
        layout.validate()
        self.layout = layout
        self.max_steps = max_steps
        self.view_radius = view_radius
        self.reset()

    def reset(self) -> DoorKeyObservation:
        self.state = WorldState(
            position=self.layout.start,
            has_key=False,
            key_position=self.layout.key,
            door_open=False,
        )
        self.steps = 0
        self.terminated = False
        self.truncated = False
        self.visited: set[Position] = {self.layout.start}
        self.event_steps: dict[str, int | None] = {
            event: None for event in CAUSAL_CHAIN
        }
        self.auxiliary_steps: dict[str, int | None] = {
            "key_acquired": None,
            "raw_door_seen": None,
        }
        self.transition_trace: list[dict[str, object]] = []
        self._update_events(moved=False, acquired=False, opened=False)
        return self.observation()

    def _visible(self, position: Position) -> bool:
        row, column = self.state.position
        return (
            abs(position[0] - row) <= self.view_radius
            and abs(position[1] - column) <= self.view_radius
        )

    def _update_events(self, *, moved: bool, acquired: bool, opened: bool) -> list[str]:
        fired: list[str] = []
        if moved and self.event_steps["explore"] is None:
            self.event_steps["explore"] = self.steps
            fired.append("explore")
        if (
            self.state.key_position is not None
            and self._visible(self.state.key_position)
            and self.event_steps["find_key"] is None
        ):
            self.event_steps["find_key"] = self.steps
            fired.append("find_key")
        if acquired and self.auxiliary_steps["key_acquired"] is None:
            self.auxiliary_steps["key_acquired"] = self.steps
        acquired_step = self.auxiliary_steps["key_acquired"]
        if (
            self.state.has_key
            and acquired_step is not None
            and self.steps > acquired_step
            and self.event_steps["retain_key"] is None
        ):
            self.event_steps["retain_key"] = self.steps
            fired.append("retain_key")
        if self._visible(self.layout.door) and self.auxiliary_steps["raw_door_seen"] is None:
            self.auxiliary_steps["raw_door_seen"] = self.steps
        if (
            self.event_steps["retain_key"] is not None
            and self._visible(self.layout.door)
            and self.event_steps["find_door"] is None
        ):
            self.event_steps["find_door"] = self.steps
            fired.append("find_door")
        if opened and self.event_steps["open_door"] is None:
            self.event_steps["open_door"] = self.steps
            fired.append("open_door")
        if (
            self.state.position == self.layout.goal
            and self.state.door_open
            and self.event_steps["reach_goal"] is None
        ):
            self.event_steps["reach_goal"] = self.steps
            fired.append("reach_goal")
        return fired

    def observation(self) -> DoorKeyObservation:
        diameter = self.view_radius * 2 + 1
        tiles = np.full((diameter, diameter), self.OUTSIDE, dtype=np.uint8)
        center_row, center_column = self.state.position
        for local_row, delta_row in enumerate(range(-self.view_radius, self.view_radius + 1)):
            for local_column, delta_column in enumerate(
                range(-self.view_radius, self.view_radius + 1)
            ):
                position = center_row + delta_row, center_column + delta_column
                row, column = position
                if not (0 <= row < self.layout.size and 0 <= column < self.layout.size):
                    continue
                if position in self.layout.walls:
                    code = self.WALL
                elif position == self.state.key_position:
                    code = self.KEY
                elif position == self.layout.door:
                    code = self.DOOR_OPEN if self.state.door_open else self.DOOR_CLOSED
                elif position == self.layout.goal:
                    code = self.GOAL
                else:
                    code = self.EMPTY
                tiles[local_row, local_column] = code
        tiles[self.view_radius, self.view_radius] = self.AGENT
        return DoorKeyObservation(
            tiles=tiles,
            has_key=self.state.has_key,
            standing_on_key=self.state.key_position == self.state.position,
            door_open=self.state.door_open,
            step_fraction=float(self.steps / self.max_steps),
        )

    def step(
        self, action: Action | int
    ) -> tuple[DoorKeyObservation, float, bool, bool, dict[str, object]]:
        if self.terminated or self.truncated:
            raise RuntimeError("step called after episode ended")
        try:
            selected = Action(int(action))
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid DoorKey action: {action}") from error

        self.steps += 1
        before = self.state
        position = before.position
        has_key = before.has_key
        key_position = before.key_position
        door_open = before.door_open
        moved = acquired = opened = dropped = False

        if selected in MOVE_DELTAS:
            candidate = _add(position, MOVE_DELTAS[selected])
            if _passable(self.layout, candidate, door_open):
                position = candidate
                moved = candidate != before.position
        elif selected == Action.PICKUP:
            if not has_key and key_position == position:
                has_key = True
                key_position = None
                acquired = True
        elif selected == Action.OPEN:
            if has_key and not door_open and _manhattan(position, self.layout.door) == 1:
                door_open = True
                opened = True
        elif selected == Action.DROP:
            if has_key and position != self.layout.door:
                has_key = False
                key_position = position
                dropped = True

        self.state = WorldState(
            position=position,
            has_key=has_key,
            key_position=key_position,
            door_open=door_open,
        )
        if moved:
            self.visited.add(position)
        fired = self._update_events(moved=moved, acquired=acquired, opened=opened)
        if self.event_steps["reach_goal"] is not None:
            self.terminated = True
        elif self.steps >= self.max_steps:
            self.truncated = True
        reward = 1.0 if "reach_goal" in fired else 0.0
        info: dict[str, object] = {
            "step": self.steps,
            "action": selected.name,
            "position": list(position),
            "moved": moved,
            "acquired": acquired,
            "dropped": dropped,
            "opened": opened,
            "events_fired": fired,
            "event_steps": dict(self.event_steps),
            "auxiliary_steps": dict(self.auxiliary_steps),
        }
        self.transition_trace.append(info)
        return self.observation(), reward, self.terminated, self.truncated, info

    def chain_complete_and_ordered(self) -> bool:
        values = [self.event_steps[event] for event in CAUSAL_CHAIN]
        return all(value is not None for value in values) and all(
            int(left) < int(right)
            for left, right in zip(values, values[1:])
            if left is not None and right is not None
        )

    def state_signature(self) -> tuple[object, ...]:
        return (
            self.state.position,
            self.state.has_key,
            self.state.key_position,
            self.state.door_open,
            self.steps,
            self.terminated,
            self.truncated,
            tuple((event, self.event_steps[event]) for event in CAUSAL_CHAIN),
        )


def run_actions(
    layout: DoorKeyLayout,
    actions: Sequence[Action | int],
    *,
    max_steps: int = 128,
) -> DoorKeyEnv:
    env = DoorKeyEnv(layout, max_steps=max_steps)
    for action in actions:
        if env.terminated or env.truncated:
            break
        env.step(action)
    return env

