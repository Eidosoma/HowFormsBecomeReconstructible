"""Read and validate the pinned BreakingGRNMemories release corpus."""

from __future__ import annotations

import csv
import hashlib
import math
import pickle
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np

from .artifacts import sha256_file
from .models import MemoryData, MemoryKey, ReleasedAction, ReleasedMemory


UPSTREAM_URL = "https://github.com/pigozzif/BreakingGRNMemories.git"
PINNED_COMMIT = "afe44231ad3ce915172cdb53a6b234bd76fcb6a5"
RELEASE_GENERATOR_COMMIT = "dac00b7a2f99f5d89151d1f3bcb2f7c7d9618de5"


def git_output(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def validate_upstream(root: Path, expected_commit: str = PINNED_COMMIT) -> dict[str, object]:
    root = root.resolve()
    required = [root / "data", root / "memories" / "ass", root / "output"]
    if not root.is_dir() or any(not path.exists() for path in required):
        raise FileNotFoundError(f"incomplete upstream checkout: {root}")
    head = git_output(root, "rev-parse", "HEAD")
    if head != expected_commit:
        raise ValueError(f"upstream HEAD {head} does not match pinned {expected_commit}")
    if git_output(root, "status", "--porcelain"):
        raise ValueError("upstream checkout is dirty")
    return {
        "root": str(root),
        "commit": head,
        "readme_sha256": sha256_file(root / "README.md"),
        "requirements_sha256": sha256_file(root / "requirements.txt"),
    }


def prepare_upstream(destination: Path, commit: str = PINNED_COMMIT) -> dict[str, object]:
    destination = destination.resolve()
    if destination.exists():
        return validate_upstream(destination, commit)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--no-checkout", UPSTREAM_URL, str(destination)], check=True
    )
    subprocess.run(
        ["git", "-C", str(destination), "checkout", "--detach", commit], check=True
    )
    return validate_upstream(destination, commit)


def load_memory(path: Path, key: MemoryKey | None = None) -> MemoryData:
    with path.open("rb") as handle:
        values = pickle.load(handle)
    if not isinstance(values, (list, tuple)) or len(values) < 11:
        raise ValueError(f"unexpected memory payload in {path}")
    if key is None:
        parts = path.name.split(".")
        key = MemoryKey(int(parts[0]), int(parts[1]), int(parts[2]))
    stored_response = int(values[8])
    if stored_response != key.response_id:
        raise ValueError(
            f"response mismatch for {key.task_id}: filename={key.response_id}, stored={stored_response}"
        )
    ucs = None if values[9] is None else int(values[9])
    cs = int(values[10] if values[10] is not None else values[9])
    has_native_prev_mean = len(values) >= 12
    # The committed corpus is an 11-field legacy export. The pinned source
    # later added the phase-wide previous mean as field 11 and refers to an
    # uncommitted old_memories tree. Never invent that missing phase mean:
    # preserve the endpoint only as a placeholder and disable reward gating.
    previous_mean = values[11] if has_native_prev_mean else values[0]
    memory = MemoryData(
        key=key,
        y=np.asarray(values[0], dtype=float),
        w=np.asarray(values[1], dtype=float),
        c=np.asarray(values[2], dtype=float),
        bounds=np.asarray(values[3], dtype=float),
        mean_relax=float(values[4]),
        response_reg=int(values[5]),
        stimulus_reg=int(values[6]),
        r_scale=float(values[7]),
        ucs_id=ucs,
        cs_id=cs,
        prev_mean=np.asarray(previous_mean, dtype=float),
        has_native_prev_mean=has_native_prev_mean,
        path=path.resolve(),
    )
    if memory.response_reg not in {1, 2}:
        raise ValueError(f"unsupported response regulation in {path}: {memory.response_reg}")
    if memory.bounds.shape != (memory.node_count, 2):
        raise ValueError(f"invalid bounds shape in {path}: {memory.bounds.shape}")
    if memory.prev_mean.shape != (memory.node_count,):
        raise ValueError(f"invalid previous-mean shape in {path}: {memory.prev_mean.shape}")
    if not 0 <= memory.cs_id < memory.node_count:
        raise ValueError(f"invalid CS index in {path}: {memory.cs_id}")
    return memory


def _parse_released_csv(path: Path) -> list[ReleasedAction]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or not lines[0].startswith("#{"):
        raise ValueError(f"unexpected released CSV header: {path}")
    actions: list[ReleasedAction] = []
    for index, row in enumerate(csv.DictReader(lines[1:])):
        reward = float(row["r"])
        elapsed = float(row["t"])
        actions.append(
            ReleasedAction(
                index=index,
                reward=reward if math.isfinite(reward) else None,
                is_broken=row["is_broken"].strip().lower() == "true",
                elapsed_seconds=elapsed,
            )
        )
    return actions


def load_released_task(upstream_root: Path, task_id: str) -> ReleasedMemory:
    root = upstream_root.resolve()
    key = MemoryKey.parse(task_id)
    csv_path = root / "output" / f"0.{task_id}.single.MlpLstmPolicy.csv"
    memory_path = root / "memories" / "ass" / (
        f"{key.model_id}.{key.response_id}.{key.circuit_id}.pickle"
    )
    if not csv_path.is_file() or not memory_path.is_file():
        raise FileNotFoundError(f"released task pair missing: {task_id}")
    memory = load_memory(memory_path, key)
    actions = _parse_released_csv(csv_path)
    if len(actions) != memory.action_count():
        raise ValueError(
            f"row count {len(actions)} != legal action count {memory.action_count()}"
        )
    return ReleasedMemory(
        key=key,
        csv_path=csv_path.resolve(),
        memory_path=memory_path.resolve(),
        actions=actions,
        released_runtime_seconds=actions[-1].elapsed_seconds,
        response_reg=memory.response_reg,
    )


def scan_associative_corpus(
    upstream_root: Path, runtime_limit_seconds: float = 60.0
) -> tuple[list[ReleasedMemory], list[dict[str, str]]]:
    root = upstream_root.resolve()
    valid: list[ReleasedMemory] = []
    exclusions: list[dict[str, str]] = []
    pattern = "*.single.MlpLstmPolicy.csv"
    for csv_path in sorted((root / "output").glob(pattern)):
        name_parts = csv_path.name.split(".")
        if len(name_parts) < 5:
            continue
        task_id = name_parts[1]
        try:
            key = MemoryKey.parse(task_id)
        except ValueError:
            continue
        memory_path = root / "memories" / "ass" / (
            f"{key.model_id}.{key.response_id}.{key.circuit_id}.pickle"
        )
        try:
            released = load_released_task(root, task_id)
            actions = released.actions
            if not actions:
                raise ValueError("empty action table")
            released_runtime = actions[-1].elapsed_seconds
            if not math.isfinite(released_runtime) or released_runtime > runtime_limit_seconds:
                raise ValueError(
                    f"released runtime {released_runtime} exceeds {runtime_limit_seconds}"
                )
            if not all(
                action.reward is not None and math.isfinite(action.elapsed_seconds)
                for action in actions
            ):
                raise ValueError("non-finite released row")
            released.released_runtime_seconds = released_runtime
            valid.append(released)
        except (FileNotFoundError, ValueError, pickle.UnpicklingError) as error:
            exclusions.append({"task_id": task_id, "reason": str(error)})
    return valid, exclusions


def stable_rank(salt: str, *parts: object) -> str:
    payload = "|".join([salt, *(str(part) for part in parts)]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def select_balanced_cohort(
    memories: Iterable[ReleasedMemory], quota: int, salt: str
) -> list[ReleasedMemory]:
    groups: dict[int, list[ReleasedMemory]] = defaultdict(list)
    for memory in memories:
        if memory.released_positive_indices:
            groups[memory.key.model_id].append(memory)
    selected: list[ReleasedMemory] = []
    direction_quota = quota // 2
    for model_id in sorted(groups):
        ranked: dict[int, list[ReleasedMemory]] = {}
        for direction in (1, 2):
            ranked[direction] = sorted(
                (item for item in groups[model_id] if item.response_reg == direction),
                key=lambda item: stable_rank(salt, item.key.task_id),
            )
        chosen = ranked[1][:direction_quota] + ranked[2][:direction_quota]
        chosen_ids = {item.key.task_id for item in chosen}
        if len(chosen) < quota:
            remainder = sorted(
                (item for item in groups[model_id] if item.key.task_id not in chosen_ids),
                key=lambda item: stable_rank(salt, item.key.task_id),
            )
            chosen.extend(remainder[: quota - len(chosen)])
        selected.extend(chosen)
    return sorted(selected, key=lambda item: (item.key.model_id, item.key.task_id))


def released_unit_cost(memory: ReleasedMemory) -> float:
    return memory.released_runtime_seconds / max(len(memory.actions), 1)


def projected_cpu_seconds(
    cohort: Iterable[ReleasedMemory], grid_action_equivalents: float = 187.0
) -> float:
    """Conservative released-timing proxy for correction plus the full phase grid."""

    total = 0.0
    for memory in cohort:
        correction_actions = len(memory.released_positive_indices) + 1
        total += released_unit_cost(memory) * (
            correction_actions + float(grid_action_equivalents)
        )
    # One full source-faithful sentinel per represented model.
    by_model: dict[int, ReleasedMemory] = {}
    for memory in cohort:
        by_model.setdefault(memory.key.model_id, memory)
    total += sum(item.released_runtime_seconds for item in by_model.values())
    return total
