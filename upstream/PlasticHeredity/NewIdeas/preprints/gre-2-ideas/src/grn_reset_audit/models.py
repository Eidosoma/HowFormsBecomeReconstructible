"""Typed records shared by selection, simulation, and analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class MemoryKey:
    model_id: int
    response_id: int
    circuit_id: int

    @property
    def task_id(self) -> str:
        return f"{self.model_id}-{self.response_id}-{self.circuit_id}"

    @classmethod
    def parse(cls, task_id: str) -> "MemoryKey":
        parts = task_id.split("-")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError(f"not an associative task id: {task_id}")
        return cls(*(int(part) for part in parts))


@dataclass
class MemoryData:
    key: MemoryKey
    y: np.ndarray
    w: np.ndarray
    c: np.ndarray
    bounds: np.ndarray
    mean_relax: float
    response_reg: int
    stimulus_reg: int
    r_scale: float
    ucs_id: int | None
    cs_id: int
    prev_mean: np.ndarray
    has_native_prev_mean: bool
    path: Path

    @property
    def node_count(self) -> int:
        return int(self.y.shape[0])

    def action_controls(self) -> list[int]:
        return [
            node
            for node in range(self.node_count)
            if node not in {self.key.response_id, self.cs_id}
        ]

    def action_count(self) -> int:
        return 2 * len(self.action_controls())

    def action(self, index: int) -> tuple[int, int, float]:
        if not 0 <= index < self.action_count():
            raise IndexError(index)
        control = self.action_controls()[index // 2]
        bound_index = index % 2
        return control, bound_index, float(self.bounds[control, bound_index])


@dataclass(frozen=True)
class ReleasedAction:
    index: int
    reward: float | None
    is_broken: bool
    elapsed_seconds: float


@dataclass
class ReleasedMemory:
    key: MemoryKey
    csv_path: Path
    memory_path: Path
    actions: list[ReleasedAction]
    released_runtime_seconds: float
    response_reg: int

    @property
    def released_positive_indices(self) -> list[int]:
        return [action.index for action in self.actions if action.is_broken]

    def to_manifest(self) -> dict[str, Any]:
        return {
            "key": asdict(self.key),
            "task_id": self.key.task_id,
            "csv_path": str(self.csv_path),
            "memory_path": str(self.memory_path),
            "released_runtime_seconds": self.released_runtime_seconds,
            "response_reg": self.response_reg,
            "released_positive_indices": self.released_positive_indices,
            "released_action_count": len(self.actions),
        }
