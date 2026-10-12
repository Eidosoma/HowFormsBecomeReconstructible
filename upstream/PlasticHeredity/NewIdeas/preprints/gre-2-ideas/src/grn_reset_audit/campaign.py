"""Cohort selection and CPU-budgeted production campaign."""

from __future__ import annotations

import json
import os
import platform
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .artifacts import append_jsonl, digest, read_jsonl, write_checksums, write_json
from .engine import (
    JaxBackend,
    historical_release_replay,
    independent_action,
    run_assay_condition,
    source_faithful_replay,
)
from .models import MemoryData, ReleasedMemory
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    projected_cpu_seconds,
    scan_associative_corpus,
    select_balanced_cohort,
    stable_rank,
    validate_upstream,
)


ARMS = ["naive", "trained_no_reset", "cs_sham", "control_only", "combined_reset"]


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported protocol schema")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("protocol does not pin the registered upstream commit")
    semantics = config.get("source_semantics", "pinned-head")
    if semantics not in {"pinned-head", "historical-release"}:
        raise ValueError(f"unsupported source semantics: {semantics}")
    if semantics == "historical-release" and config.get(
        "release_generator_commit"
    ) != RELEASE_GENERATOR_COMMIT:
        raise ValueError("historical protocol does not pin the release generator")
    if semantics == "historical-release":
        expected = {
            "delta_t": 0.01,
            "phase_duration": 2500.0,
            "pulse_count": 5,
        }
        for key, value in expected.items():
            if not np.isclose(float(config.get(key, -1)), float(value)):
                raise ValueError(f"historical protocol has incorrect {key}")
    soft = float(config["soft_cpu_seconds"])
    terminate = float(config["terminate_cpu_seconds"])
    hard = float(config["hard_cpu_seconds"])
    wall = float(config["hard_wall_seconds"])
    if not (0 < soft < terminate < hard <= 14100.0 and wall <= 14400.0):
        raise ValueError("protocol exceeds or misorders the four-hour budget")
    return config


class CpuBudget:
    def __init__(self, output: Path, config: dict[str, Any]):
        self.path = output / "cpu-ledger.json"
        self.soft = float(config["soft_cpu_seconds"])
        self.terminate = float(config["terminate_cpu_seconds"])
        self.hard = float(config["hard_cpu_seconds"])
        self.prior = 0.0
        if self.path.is_file():
            self.prior = float(json.loads(self.path.read_text(encoding="utf-8"))["cpu_seconds"])
        self.started_process = time.process_time()
        self.started_wall = time.monotonic()

    @property
    def consumed(self) -> float:
        return self.prior + max(0.0, time.process_time() - self.started_process)

    @property
    def wall_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.started_wall)

    def checkpoint(self, stage: str) -> None:
        write_json(
            self.path,
            {
                "cpu_seconds": self.consumed,
                "current_invocation_wall_seconds": self.wall_seconds,
                "stage": stage,
                "soft_cpu_seconds": self.soft,
                "terminate_cpu_seconds": self.terminate,
                "hard_cpu_seconds": self.hard,
                "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

    def may_start(self, priority: str = "normal") -> bool:
        boundary = self.terminate if priority == "required" else self.soft
        return self.consumed < boundary

    def enforce_hard(self) -> None:
        if self.consumed >= self.hard:
            raise TimeoutError("aggregate CPU budget exhausted")


def _completed_ids(path: Path) -> set[str]:
    return {str(record["task_id"]) for record in read_jsonl(path)}


def _append_record(path: Path, record: dict[str, Any]) -> None:
    append_jsonl(path, [record])


def _select_quota(
    corpus: list[ReleasedMemory], config: dict[str, Any]
) -> tuple[int, list[ReleasedMemory], list[dict[str, float]]]:
    projections: list[dict[str, float]] = []
    for quota in config["quota_candidates"]:
        cohort = select_balanced_cohort(corpus, int(quota), config["master_salt"])
        raw = projected_cpu_seconds(
            cohort, float(config.get("grid_action_equivalents", 187.0))
        )
        safe = raw * float(config["projection_safety_factor"])
        projections.append(
            {
                "quota": int(quota),
                "cohort_size": len(cohort),
                "raw_projected_cpu_seconds": raw,
                "safe_projected_cpu_seconds": safe,
            }
        )
        if safe <= float(config["projection_target_cpu_seconds"]):
            return int(quota), cohort, projections
    raise RuntimeError("quota two exceeds the registered CPU projection target")


def _sentinels(cohort: Iterable[ReleasedMemory], salt: str) -> list[ReleasedMemory]:
    groups: dict[int, list[ReleasedMemory]] = defaultdict(list)
    for memory in cohort:
        groups[memory.key.model_id].append(memory)
    return [
        min(items, key=lambda item: stable_rank(salt, "sentinel", item.key.task_id))
        for _, items in sorted(groups.items())
    ]


def _runtime_manifest() -> dict[str, Any]:
    versions: dict[str, str] = {}
    for package in ("jax", "jaxlib", "numpy", "autodiscjax", "sbmltoodejax", "equinox"):
        try:
            from importlib.metadata import version

            versions[package] = version(package)
        except Exception:
            versions[package] = "not-installed"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "packages": versions,
    }


class Campaign:
    def __init__(
        self, config_path: Path, upstream_root: Path, output: Path, workers: int = 1
    ):
        self.config_path = config_path.resolve()
        self.config = load_config(self.config_path)
        self.upstream_root = upstream_root.resolve()
        self.output = output.resolve()
        if workers != 1:
            raise ValueError(
                "the aggregate-CPU production path currently requires one worker; "
                "JAX reuses compiled model kernels within that process"
            )
        self.workers = workers
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / "SHA256SUMS").exists():
            raise ValueError("sealed output cannot be resumed")
        self.budget = CpuBudget(self.output, self.config)
        self.backends: dict[int, JaxBackend] = {}
        self.memories: dict[str, MemoryData] = {}

    def backend(self, model_id: int) -> JaxBackend:
        if model_id not in self.backends:
            self.backends[model_id] = JaxBackend(
                self.upstream_root, model_id, delta_t=float(self.config["delta_t"])
            )
        return self.backends[model_id]

    def memory(self, released: ReleasedMemory) -> MemoryData:
        task_id = released.key.task_id
        if task_id not in self.memories:
            self.memories[task_id] = load_memory(released.memory_path, released.key)
        return self.memories[task_id]

    def state(self, status: str, stage: str, **extra: Any) -> None:
        self.budget.checkpoint(stage)
        write_json(
            self.output / "state.json",
            {
                "status": status,
                "stage": stage,
                "cpu_seconds": self.budget.consumed,
                "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **extra,
            },
        )

    def prepare_registration(
        self,
    ) -> tuple[list[ReleasedMemory], list[ReleasedMemory]]:
        provenance = validate_upstream(self.upstream_root, self.config["upstream_commit"])
        corpus, exclusions = scan_associative_corpus(
            self.upstream_root,
            runtime_limit_seconds=float(self.config["released_runtime_limit_seconds"]),
        )
        quota, cohort, projections = _select_quota(corpus, self.config)
        fixed_cohort = self.config.get("fixed_cohort_task_ids")
        if fixed_cohort is not None and [item.key.task_id for item in cohort] != list(
            fixed_cohort
        ):
            raise ValueError("resolved cohort differs from the frozen amended cohort")
        sentinels = _sentinels(cohort, self.config["master_salt"])
        registration = {
            "experiment_id": self.config["experiment_id"],
            "protocol": self.config,
            "protocol_digest": digest(self.config),
            "upstream": provenance,
            "runtime": _runtime_manifest(),
            "valid_associative_corpus_size": len(corpus),
            "released_positive_corpus_size": sum(
                bool(memory.released_positive_indices) for memory in corpus
            ),
            "exclusion_count": len(exclusions),
            "selected_quota": quota,
            "cohort_size": len(cohort),
            "represented_models": sorted({item.key.model_id for item in cohort}),
            "sentinel_task_ids": [item.key.task_id for item in sentinels],
            "projections": projections,
            "selection_is_exploratory": True,
        }
        registration_path = self.output / "registration.json"
        if registration_path.is_file():
            existing = json.loads(registration_path.read_text(encoding="utf-8"))
            if existing["protocol_digest"] != registration["protocol_digest"]:
                raise ValueError("resumed output has a different protocol")
            existing_tasks = [item["task_id"] for item in existing["cohort"]]
            if existing_tasks != [item.key.task_id for item in cohort]:
                raise ValueError("resumed output resolves to a different cohort")
        else:
            registration["cohort"] = [item.to_manifest() for item in cohort]
            registration["exclusions"] = exclusions
            write_json(registration_path, registration)
        return cohort, sentinels

    def source_audit(self, sentinels: list[ReleasedMemory]) -> bool:
        path = self.output / "source-replay.jsonl"
        completed = _completed_ids(path)
        for released in sentinels:
            task_id = f"source|{released.key.task_id}"
            if task_id in completed:
                continue
            if not self.budget.may_start("required"):
                raise TimeoutError("CPU budget exhausted during required source audit")
            memory = self.memory(released)
            historical = self.config.get("source_semantics") == "historical-release"
            replay_fn = historical_release_replay if historical else source_faithful_replay
            replay = replay_fn(
                self.backend(released.key.model_id),
                memory,
                sample_count=int(self.config["trajectory_samples_per_phase"]),
            )
            comparisons = []
            for actual, expected in zip(replay, released.actions, strict=True):
                reward_error = (
                    None
                    if (
                        (not historical and not memory.has_native_prev_mean)
                        or expected.reward is None
                        or not np.isfinite(actual["reward"])
                    )
                    else abs(float(actual["reward"]) - expected.reward)
                )
                comparisons.append(
                    {
                        **actual,
                        "released_reward": expected.reward,
                        "released_is_broken": expected.is_broken,
                        "is_broken_match": bool(actual["is_broken"] == expected.is_broken),
                        "reward_abs_error": reward_error,
                    }
                )
            agreement = float(np.mean([row["is_broken_match"] for row in comparisons]))
            reward_errors = [
                row["reward_abs_error"]
                for row in comparisons
                if row["reward_abs_error"] is not None
            ]
            _append_record(
                path,
                {
                    "task_id": task_id,
                    "memory_task_id": released.key.task_id,
                    "model_id": released.key.model_id,
                    "source_semantics": self.config.get(
                        "source_semantics", "pinned-head"
                    ),
                    "has_native_prev_mean": memory.has_native_prev_mean,
                    "agreement": agreement,
                    "max_reward_abs_error": max(reward_errors, default=None),
                    "comparisons": comparisons,
                },
            )
            self.budget.checkpoint("source-audit")
            self.budget.enforce_hard()
        records = list(read_jsonl(path))
        comparisons = [row for record in records for row in record["comparisons"]]
        agreement = float(np.mean([row["is_broken_match"] for row in comparisons]))
        reward_errors = [
            row["reward_abs_error"]
            for row in comparisons
            if row["reward_abs_error"] is not None
        ]
        reward_required = bool(self.config.get("source_reward_required", False))
        reward_ok = (
            bool(reward_errors)
            and max(reward_errors) <= float(self.config["source_reward_abs_tolerance"])
        ) if reward_required else True
        valid_count = sum(bool(row["valid"]) for row in comparisons)
        validity_ok = valid_count == len(comparisons)
        gate = (
            agreement >= float(self.config["source_agreement_min"])
            and reward_ok
            and validity_ok
        )
        write_json(
            self.output / "source-gate.json",
            {
                "pass": gate,
                "agreement": agreement,
                "max_reward_abs_error": max(reward_errors, default=None),
                "required_agreement": self.config["source_agreement_min"],
                "reward_abs_tolerance": self.config["source_reward_abs_tolerance"],
                "reward_required": reward_required,
                "reward_comparable_row_count": len(reward_errors),
                "validity_required": True,
                "valid_row_count": valid_count,
                "legacy_payload_sentinel_count": sum(
                    not bool(record.get("has_native_prev_mean")) for record in records
                ),
                "sentinel_count": len(records),
                "row_count": len(comparisons),
            },
        )
        return gate

    def correction_audit(self, cohort: list[ReleasedMemory]) -> dict[str, int]:
        path = self.output / "independent-correction.jsonl"
        completed = _completed_ids(path)
        for released in cohort:
            negative_indices = [
                action.index for action in released.actions if not action.is_broken
            ]
            chosen_negative = (
                min(
                    negative_indices,
                    key=lambda index: stable_rank(
                        self.config["master_salt"], "negative", released.key.task_id, index
                    ),
                )
                if negative_indices
                else None
            )
            indices = sorted(
                set(
                    released.released_positive_indices
                    + ([] if chosen_negative is None else [chosen_negative])
                )
            )
            memory = self.memory(released)
            for action_index in indices:
                task_id = f"correction|{released.key.task_id}|{action_index}"
                if task_id in completed:
                    continue
                if not self.budget.may_start("required"):
                    raise TimeoutError("CPU budget exhausted during required correction audit")
                record, phase = independent_action(
                    self.backend(released.key.model_id),
                    memory,
                    action_index,
                    sample_count=int(self.config["trajectory_samples_per_phase"]),
                    phase_duration=float(self.config["phase_duration"]),
                    pulse_count=int(self.config.get("pulse_count", 1)),
                )
                expected = released.actions[action_index]
                _append_record(
                    path,
                    {
                        "task_id": task_id,
                        "memory_task_id": released.key.task_id,
                        "model_id": released.key.model_id,
                        "response_reg": memory.response_reg,
                        "released_is_broken": expected.is_broken,
                        "released_reward": expected.reward,
                        **record,
                        "mean_y": phase.mean_y,
                        "terminal_y": phase.terminal_y,
                    },
                )
                self.budget.checkpoint("independent-correction")
                self.budget.enforce_hard()
        records = list(read_jsonl(path))
        positives: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            if record["released_is_broken"] and record["is_broken"] and record["valid"]:
                positives[record["memory_task_id"]].append(record)
        chosen = {
            task_id: max(rows, key=lambda row: (row["reset_margin"], -row["action_index"]))
            for task_id, rows in positives.items()
        }
        write_json(
            self.output / "selected-actions.json",
            {
                "actions": {
                    task_id: {
                        "action_index": row["action_index"],
                        "reset_margin": row["reset_margin"],
                        "mean_response": row["mean_response"],
                    }
                    for task_id, row in sorted(chosen.items())
                }
            },
        )
        return {task_id: int(row["action_index"]) for task_id, row in chosen.items()}

    def washout_assay(
        self,
        cohort: list[ReleasedMemory],
        selected_actions: dict[str, int],
        full_grid: bool,
    ) -> bool:
        path = self.output / "washout.jsonl"
        completed = _completed_ids(path)
        durations = (
            self.config["washout_durations"]
            if full_grid
            else self.config["short_washout_durations"]
        )
        cohort_by_id = {item.key.task_id: item for item in cohort}
        naive_states: dict[int, Any] = {}
        time_exhausted = False
        for duration in durations:
            for task_key in sorted(selected_actions):
                released = cohort_by_id[task_key]
                memory = self.memory(released)
                backend = self.backend(released.key.model_id)
                if released.key.model_id not in naive_states:
                    if not self.budget.may_start("required"):
                        return True
                    naive = backend.naive_at_time(
                        10000.0,
                        memory.key.response_id,
                        sample_count=int(self.config["trajectory_samples_per_phase"]),
                        chunk_duration=float(
                            self.config.get(
                                "washout_chunk_duration", self.config["phase_duration"]
                            )
                        ),
                    )
                    if not naive.valid:
                        naive_states[released.key.model_id] = None
                    else:
                        naive_states[released.key.model_id] = naive.state
                    self.budget.checkpoint("naive-reference")
                naive_state = naive_states[released.key.model_id]
                if naive_state is None:
                    continue
                for arm in ARMS:
                    condition_id = f"washout|{task_key}|{selected_actions[task_key]}|{duration:g}|{arm}"
                    if condition_id in completed:
                        continue
                    priority = (
                        "required"
                        if float(duration)
                        <= max(float(value) for value in self.config["short_washout_durations"])
                        else "normal"
                    )
                    if not self.budget.may_start(priority):
                        time_exhausted = True
                        break
                    record = run_assay_condition(
                        backend,
                        memory,
                        selected_actions[task_key],
                        arm,
                        float(duration),
                        naive_state,
                        sample_count=int(self.config["trajectory_samples_per_phase"]),
                        phase_duration=float(self.config["phase_duration"]),
                        pulse_count=int(self.config.get("pulse_count", 1)),
                        washout_chunk_duration=float(
                            self.config.get(
                                "washout_chunk_duration", self.config["phase_duration"]
                            )
                        ),
                        time_match_reset_slot=bool(
                            self.config.get("time_match_reset_slot", False)
                        ),
                    )
                    _append_record(
                        path,
                        {
                            "task_id": condition_id,
                            "memory_task_id": task_key,
                            "model_id": released.key.model_id,
                            "response_id": released.key.response_id,
                            "response_reg": memory.response_reg,
                            **record,
                        },
                    )
                    self.budget.checkpoint(f"washout-{duration:g}")
                    self.budget.enforce_hard()
                if time_exhausted:
                    break
            if time_exhausted:
                break
        return time_exhausted

    def sentinel_exhaustive(
        self, sentinels: list[ReleasedMemory]
    ) -> bool:
        path = self.output / "sentinel-exhaustive.jsonl"
        completed = _completed_ids(path)
        for released in sentinels:
            memory = self.memory(released)
            for action_index in range(memory.action_count()):
                task_id = f"exhaustive|{released.key.task_id}|{action_index}"
                if task_id in completed:
                    continue
                if not self.budget.may_start("normal"):
                    return True
                record, _ = independent_action(
                    self.backend(released.key.model_id),
                    memory,
                    action_index,
                    sample_count=int(self.config["trajectory_samples_per_phase"]),
                    phase_duration=float(self.config["phase_duration"]),
                    pulse_count=int(self.config.get("pulse_count", 1)),
                )
                _append_record(
                    path,
                    {
                        "task_id": task_id,
                        "memory_task_id": released.key.task_id,
                        "model_id": released.key.model_id,
                        "released_is_broken": released.actions[action_index].is_broken,
                        **record,
                    },
                )
                self.budget.checkpoint("sentinel-exhaustive")
                self.budget.enforce_hard()
        return False

    def run(self) -> int:
        self.state("running", "registration")
        try:
            cohort, sentinels = self.prepare_registration()
            self.state("running", "source-audit")
            if not self.source_audit(sentinels):
                self.state("source-gate-failed", "source-audit")
                from .analysis import analyze

                analyze(self.output)
                write_checksums(self.output)
                return 3
            self.state("running", "independent-correction")
            selected_actions = self.correction_audit(cohort)
            represented = {
                item.key.model_id
                for item in cohort
                if item.key.task_id in selected_actions
            }
            full_grid = len(selected_actions) >= int(
                self.config["continuation_min_memories"]
            ) and len(represented) >= int(self.config["continuation_min_models"])
            write_json(
                self.output / "continuation-gate.json",
                {
                    "pass": full_grid,
                    "independently_reproduced_memories": len(selected_actions),
                    "represented_models": sorted(represented),
                    "required_memories": self.config["continuation_min_memories"],
                    "required_models": self.config["continuation_min_models"],
                    "durations": self.config["washout_durations"]
                    if full_grid
                    else self.config["short_washout_durations"],
                },
            )
            self.state("running", "washout")
            time_exhausted = self.washout_assay(
                cohort, selected_actions, full_grid=full_grid
            )
            if not time_exhausted:
                time_exhausted = self.sentinel_exhaustive(sentinels)
            from .analysis import analyze

            analyze(self.output)
            final_status = "time-budget-exhausted" if time_exhausted else "completed"
            self.state(final_status, "complete")
            write_checksums(self.output)
            return 124 if time_exhausted else 0
        except TimeoutError as error:
            from .analysis import analyze

            analyze(self.output)
            self.state("time-budget-exhausted", "interrupted", error=str(error))
            write_checksums(self.output)
            return 124
        except BaseException as error:
            self.state("failed", "exception", error=repr(error))
            raise


def run_campaign(
    config_path: Path, upstream_root: Path, output: Path, workers: int = 1
) -> int:
    return Campaign(config_path, upstream_root, output, workers=workers).run()
