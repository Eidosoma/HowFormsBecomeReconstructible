"""Observer Atlas V1 simulation campaign.

The atlas is deliberately separate from the historical washout campaign.  It
uses the sealed V4 cohort/actions as immutable inputs, then creates richer
state, counterfactual, reinstatement, and relearning observations.
"""

from __future__ import annotations

import json
import math
import os
import platform
import time
from dataclasses import asdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

import numpy as np

from .artifacts import (
    append_jsonl,
    canonical_json,
    digest,
    read_jsonl,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .campaign import CpuBudget
from .engine import (
    JaxBackend,
    PhaseResult,
    State,
    historical_release_replay,
    is_broken,
    reset_margin,
    run_assay_condition,
    stimuli_for_action,
)
from .models import MemoryData, ReleasedMemory
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    stable_rank,
    validate_upstream,
)


ATLAS_ARMS = [
    "naive",
    "trained_no_reset",
    "cs_sham",
    "control_only",
    "combined_reset",
    "matched_negative",
]


def load_atlas_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0":
        raise ValueError("unsupported atlas schema")
    if config.get("experiment_kind") != "observer-atlas":
        raise ValueError("not an observer-atlas protocol")
    if config.get("upstream_commit") != PINNED_COMMIT:
        raise ValueError("atlas does not pin the registered upstream commit")
    if config.get("release_generator_commit") != RELEASE_GENERATOR_COMMIT:
        raise ValueError("atlas does not pin the historical generator")
    expected = {"delta_t": 0.01, "phase_duration": 2500.0, "pulse_count": 5}
    for key, value in expected.items():
        if not np.isclose(float(config.get(key, -1)), value):
            raise ValueError(f"atlas has incorrect historical {key}")
    if list(config.get("arms", [])) != ATLAS_ARMS:
        raise ValueError("atlas arms differ from the frozen six-arm design")
    checkpoints = [float(value) for value in config["washout_checkpoints"]]
    if checkpoints != [0.0, 2500.0, 12500.0, 62500.0]:
        raise ValueError("atlas washout checkpoints differ from the frozen ladder")
    soft = float(config["soft_cpu_seconds"])
    terminate = float(config["terminate_cpu_seconds"])
    hard = float(config["hard_cpu_seconds"])
    wall = float(config["hard_wall_seconds"])
    if not (0 < soft < terminate < hard <= 14100.0 and wall <= 14400.0):
        raise ValueError("atlas exceeds or misorders the four-hour budget")
    if int(config.get("max_workers", 0)) != 1:
        raise ValueError("atlas aggregate CPU contract requires one worker")
    return config


def _completed_ids(path: Path) -> set[str]:
    return {str(row["task_id"]) for row in read_jsonl(path)}


def _append(path: Path, record: dict[str, Any]) -> None:
    append_jsonl(path, [record])


def state_payload(state: State) -> dict[str, Any]:
    return {
        "y": state.y,
        "w": state.w,
        "c": state.c,
        "t": float(state.t),
        "valid": bool(
            np.all(np.isfinite(state.y))
            and np.all(np.isfinite(state.w))
            and np.all(np.isfinite(state.c))
            and np.isfinite(state.t)
        ),
    }


def state_from_payload(payload: Mapping[str, Any] | None) -> State | None:
    if payload is None or not bool(payload.get("valid", False)):
        return None
    values = [payload.get("y"), payload.get("w"), payload.get("c")]
    if any(value is None for value in values):
        return None
    arrays = [np.asarray(value, dtype=float) for value in values]
    if not all(np.all(np.isfinite(value)) for value in arrays):
        return None
    return State(arrays[0], arrays[1], arrays[2], float(payload["t"]))


def phase_payload(phase: PhaseResult | None) -> dict[str, Any] | None:
    if phase is None:
        return None
    return {
        "state": state_payload(phase.state),
        "mean_y": phase.mean_y,
        "terminal_y": phase.terminal_y,
        "sampled_y": phase.sampled_y,
        "response_trajectory": phase.response_trajectory,
        "valid": bool(phase.valid),
        "cpu_seconds": float(phase.cpu_seconds),
        "wall_seconds": float(phase.wall_seconds),
    }


def normalized_state_distance(
    left: np.ndarray, right: np.ndarray, bounds: np.ndarray
) -> float:
    scale = np.maximum(np.abs(bounds[:, 1] - bounds[:, 0]), 1e-8)
    return float(np.sqrt(np.mean(((np.asarray(left) - np.asarray(right)) / scale) ** 2)))


def learned_margin(memory: MemoryData, mean_response: float) -> float:
    """Positive values are on the learned side of the operational threshold."""

    return -float(reset_margin(memory, float(mean_response)))


def _challenge_payload(memory: MemoryData, phase: PhaseResult) -> dict[str, Any]:
    mean_response = float(phase.mean_y[memory.key.response_id])
    return {
        "mean_response": mean_response,
        "is_broken": bool(is_broken(memory, mean_response)),
        "reset_margin": float(reset_margin(memory, mean_response)),
        "learned_margin": float(learned_margin(memory, mean_response)),
        "phase": phase_payload(phase),
        "valid": bool(phase.valid),
    }


def choose_matched_negative(
    selected_displacement: float,
    candidates: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    eligible = [
        row
        for row in candidates
        if bool(row.get("valid"))
        and not bool(row.get("is_broken"))
        and np.isfinite(float(row.get("state_displacement", math.nan)))
    ]
    if not eligible or not np.isfinite(selected_displacement):
        return None
    epsilon = 1e-12
    return min(
        eligible,
        key=lambda row: (
            abs(
                math.log(
                    (float(row["state_displacement"]) + epsilon)
                    / (float(selected_displacement) + epsilon)
                )
            ),
            int(row["action_index"]),
        ),
    )


def choose_reconstructed_ucs(candidates: Iterable[dict[str, Any]]) -> int | None:
    eligible = [
        row
        for row in candidates
        if bool(row.get("valid")) and np.isfinite(float(row.get("learned_margin", math.nan)))
    ]
    if not eligible:
        return None
    return int(
        max(
            eligible,
            key=lambda row: (float(row["learned_margin"]), -int(row["bound_index"])),
        )["bound_index"]
    )


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


def _count_parent_actions(registration: dict[str, Any]) -> tuple[int, int]:
    total = sum(int(row["released_action_count"]) for row in registration["cohort"])
    positives = sum(len(row["released_positive_indices"]) for row in registration["cohort"])
    return total, positives


def project_atlas_cpu(
    parent: Path, registration: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    correction = list(read_jsonl(parent / "independent-correction.jsonl"))
    washout = list(read_jsonl(parent / "washout.jsonl"))
    phase_unit = median(float(row["cpu_seconds"]) for row in correction)
    longest = [row for row in washout if float(row["washout_duration"]) == 62500.0]
    if len(longest) != 120:
        raise ValueError("parent does not contain the complete longest-washout grid")
    long_history_unit = sum(float(row["cpu_seconds"]) for row in longest) / len(longest)
    total_actions, positives = _count_parent_actions(registration)
    memory_count = len(registration["cohort"])
    history_count = memory_count * len(ATLAS_ARMS)
    off_target_count = int(config["off_target_node_count"])
    include_matched_relearning = True

    def estimate() -> dict[str, float]:
        base_probe_count = 11
        probe_count = base_probe_count + 2 * off_target_count
        components = {
            "calibration": (total_actions - positives + memory_count) * phase_unit,
            "long_histories": history_count * long_history_unit,
            "extra_checkpoint_challenges": history_count * 3 * phase_unit,
            "counterfactual_probes": history_count * probe_count * phase_unit,
            "reinstatement": history_count * 3 * phase_unit,
            "relearning": (
                history_count
                - (0 if include_matched_relearning else memory_count)
            )
            * int(config["relearning_cycles"])
            * 3
            * phase_unit,
            "fixed_overhead": 300.0,
        }
        components["raw_projected_cpu_seconds"] = sum(components.values())
        return components

    components = estimate()
    target = float(config["projection_raw_target_cpu_seconds"])
    applied: list[str] = []
    if components["raw_projected_cpu_seconds"] > target and off_target_count > 1:
        off_target_count = 1
        applied.append("reduce-off-target-node-count-to-one")
        components = estimate()
    if components["raw_projected_cpu_seconds"] > target and include_matched_relearning:
        include_matched_relearning = False
        applied.append("omit-matched-negative-relearning")
        components = estimate()
    raw = components["raw_projected_cpu_seconds"]
    safe = raw * float(config["projection_safety_factor"])
    if raw > target or safe >= float(config["hard_cpu_seconds"]):
        raise RuntimeError("atlas exceeds its frozen CPU projection contract")
    return {
        **components,
        "phase_cpu_seconds": phase_unit,
        "long_history_cpu_seconds": long_history_unit,
        "effective_off_target_node_count": off_target_count,
        "include_matched_negative_relearning": include_matched_relearning,
        "fallbacks_applied": applied,
        "safety_factor": float(config["projection_safety_factor"]),
        "safe_projected_cpu_seconds": safe,
    }


class AtlasCampaign:
    def __init__(
        self,
        config_path: Path,
        parent: Path,
        upstream: Path,
        output: Path,
        workers: int = 1,
    ):
        self.config_path = config_path.resolve()
        self.config = load_atlas_config(self.config_path)
        self.parent = parent.resolve()
        self.upstream = upstream.resolve()
        self.output = output.resolve()
        if workers != 1:
            raise ValueError("atlas requires exactly one worker")
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / "SHA256SUMS").exists():
            raise ValueError("sealed atlas output cannot be resumed")
        self.budget = CpuBudget(self.output, self.config)
        self.backends: dict[int, JaxBackend] = {}
        self.memories: dict[str, MemoryData] = {}
        self.released: dict[str, ReleasedMemory] = {}
        self.selected_actions: dict[str, int] = {}
        self.calibrations: dict[str, dict[str, Any]] = {}
        self.histories: dict[tuple[str, str], dict[str, Any]] = {}
        self.projection: dict[str, Any] = {}

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

    def backend(self, model_id: int) -> JaxBackend:
        if model_id not in self.backends:
            self.backends[model_id] = JaxBackend(
                self.upstream, model_id, delta_t=float(self.config["delta_t"])
            )
        return self.backends[model_id]

    def memory(self, task_id: str) -> MemoryData:
        if task_id not in self.memories:
            released = self.release(task_id)
            self.memories[task_id] = load_memory(released.memory_path, released.key)
        return self.memories[task_id]

    def release(self, task_id: str) -> ReleasedMemory:
        if task_id not in self.released:
            self.released[task_id] = load_released_task(self.upstream, task_id)
        return self.released[task_id]

    def prepare_registration(self) -> list[str]:
        provenance = validate_upstream(self.upstream, self.config["upstream_commit"])
        verify_checksums(self.parent)
        expected_hashes = {
            "SHA256SUMS": self.config["parent_manifest_sha256"],
            "registration.json": self.config["parent_registration_sha256"],
            "selected-actions.json": self.config["parent_selected_actions_sha256"],
        }
        for name, expected in expected_hashes.items():
            actual = sha256_file(self.parent / name)
            if actual != expected:
                raise ValueError(f"parent {name} hash mismatch")
        parent_state = json.loads((self.parent / "state.json").read_text(encoding="utf-8"))
        if parent_state.get("status") != "completed":
            raise ValueError("atlas parent is not completed")
        parent_registration = json.loads(
            (self.parent / "registration.json").read_text(encoding="utf-8")
        )
        tasks = [row["task_id"] for row in parent_registration["cohort"]]
        if tasks != list(self.config["fixed_cohort_task_ids"]):
            raise ValueError("parent cohort differs from frozen atlas cohort")
        selected_payload = json.loads(
            (self.parent / "selected-actions.json").read_text(encoding="utf-8")
        )
        self.selected_actions = {
            task_id: int(row["action_index"])
            for task_id, row in selected_payload["actions"].items()
        }
        if sorted(self.selected_actions) != sorted(tasks):
            raise ValueError("parent selected actions do not cover the frozen cohort")
        self.projection = project_atlas_cpu(
            self.parent, parent_registration, self.config
        )
        registration = {
            "experiment_id": self.config["experiment_id"],
            "protocol": self.config,
            "protocol_digest": digest(self.config),
            "parent": {
                "path": str(self.parent),
                "experiment_id": parent_registration["experiment_id"],
                "hashes": expected_hashes,
            },
            "upstream": provenance,
            "runtime": _runtime_manifest(),
            "cohort": parent_registration["cohort"],
            "cohort_size": len(tasks),
            "represented_models": parent_registration["represented_models"],
            "selected_actions": self.selected_actions,
            "projection": self.projection,
        }
        path = self.output / "registration.json"
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing["protocol_digest"] != registration["protocol_digest"]:
                raise ValueError("resumed atlas has a different protocol")
            if existing["parent"]["hashes"] != expected_hashes:
                raise ValueError("resumed atlas has a different parent")
            self.projection = existing["projection"]
        else:
            write_json(path, registration)
        write_json(
            self.output / "parent-gate.json",
            {
                "pass": True,
                "parent_status": parent_state["status"],
                "checksum_count": len(verify_checksums(self.parent)),
                "cohort_size": len(tasks),
                "selected_action_count": len(self.selected_actions),
                "projection_pass": True,
            },
        )
        return tasks

    def _may_start(self, priority: str = "normal") -> bool:
        return self.budget.may_start(priority)

    def calibrate(self, tasks: list[str]) -> bool:
        path = self.output / "calibration.jsonl"
        completed = _completed_ids(path)
        for task_id in tasks:
            record_id = f"calibration|{task_id}"
            if record_id in completed:
                continue
            if not self._may_start("required"):
                return True
            memory = self.memory(task_id)
            released = self.release(task_id)
            backend = self.backend(memory.key.model_id)
            selected_index = self.selected_actions[task_id]
            selected_phase = backend.run_phase(
                backend.memory_state(memory),
                float(self.config["phase_duration"]),
                stimuli_for_action(memory, selected_index),
                response_id=memory.key.response_id,
                sample_count=int(self.config["trajectory_samples_per_phase"]),
                pulse_count=int(self.config["pulse_count"]),
            )
            selected_displacement = normalized_state_distance(
                selected_phase.terminal_y, memory.y, memory.bounds
            )
            candidates: list[dict[str, Any]] = []
            for action in released.actions:
                if action.is_broken:
                    continue
                if not self._may_start("required"):
                    return True
                phase = backend.run_phase(
                    backend.memory_state(memory),
                    float(self.config["phase_duration"]),
                    stimuli_for_action(memory, action.index),
                    response_id=memory.key.response_id,
                    sample_count=11,
                    pulse_count=int(self.config["pulse_count"]),
                )
                mean_response = float(phase.mean_y[memory.key.response_id])
                candidates.append(
                    {
                        "action_index": int(action.index),
                        "released_is_broken": bool(action.is_broken),
                        "is_broken": bool(is_broken(memory, mean_response)),
                        "valid": bool(phase.valid),
                        "mean_response": mean_response,
                        "state_displacement": normalized_state_distance(
                            phase.terminal_y, memory.y, memory.bounds
                        ),
                        "cpu_seconds": float(phase.cpu_seconds),
                    }
                )
            matched = choose_matched_negative(selected_displacement, candidates)
            ucs_candidates: list[dict[str, Any]] = []
            if memory.ucs_id is not None:
                for bound_index in (0, 1):
                    if not self._may_start("required"):
                        return True
                    phase = backend.run_phase(
                        backend.memory_state(memory),
                        float(self.config["phase_duration"]),
                        {int(memory.ucs_id): float(memory.bounds[memory.ucs_id, bound_index])},
                        response_id=memory.key.response_id,
                        sample_count=11,
                        pulse_count=int(self.config["pulse_count"]),
                    )
                    mean_response = float(phase.mean_y[memory.key.response_id])
                    ucs_candidates.append(
                        {
                            "bound_index": bound_index,
                            "value": float(memory.bounds[memory.ucs_id, bound_index]),
                            "mean_response": mean_response,
                            "learned_margin": learned_margin(memory, mean_response),
                            "valid": bool(phase.valid),
                            "cpu_seconds": float(phase.cpu_seconds),
                        }
                    )
            reconstructed_ucs = choose_reconstructed_ucs(ucs_candidates)
            record = {
                "task_id": record_id,
                "memory_task_id": task_id,
                "model_id": memory.key.model_id,
                "selected_action_index": selected_index,
                "selected_state_displacement": selected_displacement,
                "selected_valid": bool(selected_phase.valid),
                "selected_phase": phase_payload(selected_phase),
                "negative_candidates": candidates,
                "matched_negative_action_index": None
                if matched is None
                else int(matched["action_index"]),
                "matched_negative_state_displacement": None
                if matched is None
                else float(matched["state_displacement"]),
                "ucs_id": memory.ucs_id,
                "ucs_candidates": ucs_candidates,
                "reconstructed_ucs_bound_index": reconstructed_ucs,
                "ucs_ambiguous": bool(
                    len(ucs_candidates) == 2
                    and all(row["valid"] for row in ucs_candidates)
                    and abs(
                        float(ucs_candidates[0]["learned_margin"])
                        - float(ucs_candidates[1]["learned_margin"])
                    )
                    <= 1e-8
                ),
            }
            _append(path, record)
            self.budget.checkpoint("atlas-calibration")
            self.budget.enforce_hard()
        self.calibrations = {
            row["memory_task_id"]: row for row in read_jsonl(path)
        }
        write_json(
            self.output / "calibration-gate.json",
            {
                "pass": len(self.calibrations) == len(tasks),
                "memory_count": len(self.calibrations),
                "matched_negative_count": sum(
                    row["matched_negative_action_index"] is not None
                    for row in self.calibrations.values()
                ),
                "reconstructed_ucs_count": sum(
                    row["reconstructed_ucs_bound_index"] is not None
                    for row in self.calibrations.values()
                ),
                "ambiguous_ucs_count": sum(
                    bool(row["ucs_ambiguous"]) for row in self.calibrations.values()
                ),
            },
        )
        return False

    def _load_calibrations(self) -> None:
        self.calibrations = {
            row["memory_task_id"]: row
            for row in read_jsonl(self.output / "calibration.jsonl")
        }

    def _history_reset_stimuli(
        self, memory: MemoryData, arm: str, calibration: dict[str, Any]
    ) -> Mapping[int, float] | None:
        cs_value = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
        selected = self.selected_actions[memory.key.task_id]
        control, _, control_value = memory.action(selected)
        if arm in {"naive", "trained_no_reset"}:
            return None
        if arm == "cs_sham":
            return {memory.cs_id: cs_value}
        if arm == "control_only":
            return {control: control_value}
        if arm == "combined_reset":
            return {memory.cs_id: cs_value, control: control_value}
        if arm == "matched_negative":
            matched = calibration["matched_negative_action_index"]
            return None if matched is None else stimuli_for_action(memory, int(matched))
        raise ValueError(f"unknown atlas arm: {arm}")

    def run_histories(self, tasks: list[str]) -> bool:
        path = self.output / "histories.jsonl"
        completed = _completed_ids(path)
        checkpoints = [float(value) for value in self.config["washout_checkpoints"]]
        phase_duration = float(self.config["phase_duration"])
        pulse_count = int(self.config["pulse_count"])
        sample_count = int(self.config["trajectory_samples_per_phase"])
        chunk = float(self.config["washout_chunk_duration"])
        for task_id in tasks:
            memory = self.memory(task_id)
            backend = self.backend(memory.key.model_id)
            calibration = self.calibrations[task_id]
            for arm in ATLAS_ARMS:
                record_id = f"history|{task_id}|{arm}"
                if record_id in completed:
                    continue
                if not self._may_start("required"):
                    return True
                if arm == "matched_negative" and calibration[
                    "matched_negative_action_index"
                ] is None:
                    _append(
                        path,
                        {
                            "task_id": record_id,
                            "memory_task_id": task_id,
                            "model_id": memory.key.model_id,
                            "arm": arm,
                            "valid": False,
                            "skip_reason": "no-valid-matched-negative",
                            "checkpoints": {},
                        },
                    )
                    continue
                if arm == "naive":
                    naive = backend.naive_at_time(
                        10000.0,
                        memory.key.response_id,
                        sample_count=sample_count,
                        chunk_duration=chunk,
                    )
                    start = naive.state
                    start_valid = naive.valid
                    start_payload = phase_payload(naive)
                else:
                    start = backend.memory_state(memory)
                    start_valid = bool(np.all(np.isfinite(start.y)))
                    start_payload = {"state": state_payload(start), "valid": start_valid}
                stimuli = self._history_reset_stimuli(memory, arm, calibration)
                if stimuli is None:
                    reset_phase = backend.run_unstimulated(
                        start,
                        phase_duration,
                        response_id=memory.key.response_id,
                        sample_count=sample_count,
                        chunk_duration=chunk,
                    )
                else:
                    reset_phase = backend.run_phase(
                        start,
                        phase_duration,
                        stimuli,
                        response_id=memory.key.response_id,
                        sample_count=sample_count,
                        pulse_count=pulse_count,
                    )
                current: State | None = reset_phase.state if reset_phase.valid else None
                checkpoint_payloads: dict[str, Any] = {}
                prior_duration = 0.0
                intervals: list[dict[str, Any]] = []
                for duration in checkpoints:
                    duration_key = f"{duration:g}"
                    if duration > prior_duration and current is not None:
                        washout = backend.run_unstimulated(
                            current,
                            duration - prior_duration,
                            response_id=memory.key.response_id,
                            sample_count=sample_count,
                            chunk_duration=chunk,
                        )
                        intervals.append(
                            {
                                "start_duration": prior_duration,
                                "end_duration": duration,
                                "phase": phase_payload(washout),
                            }
                        )
                        current = washout.state if washout.valid else None
                    if current is None:
                        checkpoint_payloads[duration_key] = {
                            "duration": duration,
                            "valid": False,
                            "state": None,
                            "challenge": None,
                        }
                    else:
                        challenge = backend.run_phase(
                            current.copy(),
                            phase_duration,
                            {
                                memory.cs_id: float(
                                    memory.bounds[
                                        memory.cs_id, memory.stimulus_reg % 2
                                    ]
                                )
                            },
                            response_id=memory.key.response_id,
                            sample_count=sample_count,
                            pulse_count=pulse_count,
                        )
                        checkpoint_payloads[duration_key] = {
                            "duration": duration,
                            "valid": bool(challenge.valid),
                            "state": state_payload(current),
                            "challenge": _challenge_payload(memory, challenge),
                        }
                    prior_duration = duration
                valid = bool(
                    start_valid
                    and reset_phase.valid
                    and all(
                        bool(row["valid"]) for row in checkpoint_payloads.values()
                    )
                )
                _append(
                    path,
                    {
                        "task_id": record_id,
                        "memory_task_id": task_id,
                        "model_id": memory.key.model_id,
                        "response_id": memory.key.response_id,
                        "arm": arm,
                        "selected_action_index": self.selected_actions[task_id],
                        "matched_negative_action_index": calibration[
                            "matched_negative_action_index"
                        ],
                        "start": start_payload,
                        "reset_stimuli": stimuli,
                        "reset_phase": phase_payload(reset_phase),
                        "washout_intervals": intervals,
                        "checkpoints": checkpoint_payloads,
                        "valid": valid,
                    },
                )
                self.budget.checkpoint("atlas-histories")
                self.budget.enforce_hard()
        self.histories = {
            (row["memory_task_id"], row["arm"]): row for row in read_jsonl(path)
        }
        return False

    def _load_histories(self) -> None:
        self.histories = {
            (row["memory_task_id"], row["arm"]): row
            for row in read_jsonl(self.output / "histories.jsonl")
        }

    def probe_specs(
        self, memory: MemoryData, calibration: dict[str, Any]
    ) -> list[dict[str, Any]]:
        cs_value = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
        selected = self.selected_actions[memory.key.task_id]
        selected_control, selected_bound, selected_value = memory.action(selected)
        opposite_value = float(memory.bounds[selected_control, 1 - selected_bound])
        specs: list[dict[str, Any]] = [
            {"name": "no_input", "stimuli": None, "off_target": False},
            {"name": "cs", "stimuli": {memory.cs_id: cs_value}, "off_target": False},
        ]
        ucs_bound = calibration["reconstructed_ucs_bound_index"]
        if memory.ucs_id is not None:
            for bound_index in (0, 1):
                specs.append(
                    {
                        "name": f"ucs_bound_{bound_index}",
                        "stimuli": {
                            memory.ucs_id: float(
                                memory.bounds[memory.ucs_id, bound_index]
                            )
                        },
                        "off_target": False,
                    }
                )
            if ucs_bound is not None:
                specs.append(
                    {
                        "name": "cs_reconstructed_ucs",
                        "stimuli": {
                            memory.cs_id: cs_value,
                            memory.ucs_id: float(memory.bounds[memory.ucs_id, ucs_bound]),
                        },
                        "off_target": False,
                    }
                )
        specs.extend(
            [
                {
                    "name": "selected_control",
                    "stimuli": {selected_control: selected_value},
                    "off_target": False,
                },
                {
                    "name": "cs_selected_control",
                    "stimuli": {
                        memory.cs_id: cs_value,
                        selected_control: selected_value,
                    },
                    "off_target": False,
                },
                {
                    "name": "opposite_selected_control",
                    "stimuli": {selected_control: opposite_value},
                    "off_target": False,
                },
                {
                    "name": "cs_opposite_selected_control",
                    "stimuli": {
                        memory.cs_id: cs_value,
                        selected_control: opposite_value,
                    },
                    "off_target": False,
                },
            ]
        )
        matched_index = calibration["matched_negative_action_index"]
        matched_control: int | None = None
        if matched_index is not None:
            matched_control, _, matched_value = memory.action(int(matched_index))
            specs.extend(
                [
                    {
                        "name": "matched_control",
                        "stimuli": {matched_control: matched_value},
                        "off_target": False,
                    },
                    {
                        "name": "cs_matched_control",
                        "stimuli": {
                            memory.cs_id: cs_value,
                            matched_control: matched_value,
                        },
                        "off_target": False,
                    },
                ]
            )
        excluded = {
            memory.key.response_id,
            memory.cs_id,
            memory.ucs_id,
            selected_control,
            matched_control,
        }
        candidates = [
            node for node in range(memory.node_count) if node not in excluded
        ]
        candidates.sort(
            key=lambda node: stable_rank(
                self.config["off_target_salt"], memory.key.task_id, node
            )
        )
        count = int(self.projection["effective_off_target_node_count"])
        for slot, node in enumerate(candidates[:count]):
            for bound_index in (0, 1):
                specs.append(
                    {
                        "name": f"off_target_{slot}_bound_{bound_index}",
                        "node": node,
                        "bound_index": bound_index,
                        "stimuli": {node: float(memory.bounds[node, bound_index])},
                        "off_target": True,
                    }
                )
        return specs

    def run_probes(self, tasks: list[str]) -> bool:
        path = self.output / "probes.jsonl"
        completed = _completed_ids(path)
        phase_duration = float(self.config["phase_duration"])
        sample_count = int(self.config["trajectory_samples_per_phase"])
        pulse_count = int(self.config["pulse_count"])
        for task_id in tasks:
            memory = self.memory(task_id)
            backend = self.backend(memory.key.model_id)
            specs = self.probe_specs(memory, self.calibrations[task_id])
            for arm in ATLAS_ARMS:
                history = self.histories.get((task_id, arm), {})
                checkpoint = history.get("checkpoints", {}).get("62500", {})
                start = state_from_payload(checkpoint.get("state"))
                for spec in specs:
                    record_id = f"probe|{task_id}|{arm}|{spec['name']}"
                    if record_id in completed:
                        continue
                    priority = "normal" if spec["off_target"] else "required"
                    if not self._may_start(priority):
                        return True
                    if start is None:
                        _append(
                            path,
                            {
                                "task_id": record_id,
                                "memory_task_id": task_id,
                                "model_id": memory.key.model_id,
                                "arm": arm,
                                "probe": spec["name"],
                                "stimuli": spec["stimuli"],
                                "off_target": spec["off_target"],
                                "valid": False,
                                "skip_reason": "invalid-longest-checkpoint",
                            },
                        )
                        continue
                    if spec["stimuli"] is None:
                        phase = backend.run_unstimulated(
                            start.copy(),
                            phase_duration,
                            response_id=memory.key.response_id,
                            sample_count=sample_count,
                            chunk_duration=float(self.config["washout_chunk_duration"]),
                        )
                    else:
                        phase = backend.run_phase(
                            start.copy(),
                            phase_duration,
                            {int(key): float(value) for key, value in spec["stimuli"].items()},
                            response_id=memory.key.response_id,
                            sample_count=sample_count,
                            pulse_count=pulse_count,
                        )
                    payload = _challenge_payload(memory, phase)
                    _append(
                        path,
                        {
                            "task_id": record_id,
                            "memory_task_id": task_id,
                            "model_id": memory.key.model_id,
                            "arm": arm,
                            "probe": spec["name"],
                            "stimuli": spec["stimuli"],
                            "off_target": spec["off_target"],
                            **payload,
                        },
                    )
                    self.budget.checkpoint("atlas-probes")
                    self.budget.enforce_hard()
        return False

    def _ucs_stimuli(
        self, memory: MemoryData, calibration: dict[str, Any], include_cs: bool
    ) -> dict[int, float] | None:
        bound = calibration["reconstructed_ucs_bound_index"]
        if memory.ucs_id is None or bound is None:
            return None
        stimuli = {memory.ucs_id: float(memory.bounds[memory.ucs_id, int(bound)])}
        if include_cs:
            stimuli[memory.cs_id] = float(
                memory.bounds[memory.cs_id, memory.stimulus_reg % 2]
            )
        return stimuli

    def run_reinstatement(self, tasks: list[str]) -> bool:
        path = self.output / "reinstatement.jsonl"
        completed = _completed_ids(path)
        duration = float(self.config["phase_duration"])
        sample_count = int(self.config["trajectory_samples_per_phase"])
        pulse_count = int(self.config["pulse_count"])
        for task_id in tasks:
            memory = self.memory(task_id)
            backend = self.backend(memory.key.model_id)
            calibration = self.calibrations[task_id]
            stimuli = self._ucs_stimuli(memory, calibration, include_cs=False)
            cs = {
                memory.cs_id: float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
            }
            for arm in ATLAS_ARMS:
                record_id = f"reinstatement|{task_id}|{arm}"
                if record_id in completed:
                    continue
                if not self._may_start("normal"):
                    return True
                history = self.histories.get((task_id, arm), {})
                start = state_from_payload(
                    history.get("checkpoints", {}).get("62500", {}).get("state")
                )
                if start is None or stimuli is None:
                    _append(
                        path,
                        {
                            "task_id": record_id,
                            "memory_task_id": task_id,
                            "model_id": memory.key.model_id,
                            "arm": arm,
                            "valid": False,
                            "skip_reason": "missing-valid-checkpoint-or-ucs",
                        },
                    )
                    continue
                ucs_phase = backend.run_phase(
                    start.copy(), duration, stimuli, memory.key.response_id,
                    sample_count=sample_count, pulse_count=pulse_count
                )
                washout = (
                    backend.run_unstimulated(
                        ucs_phase.state,
                        float(self.config["reinstatement_washout_duration"]),
                        memory.key.response_id,
                        sample_count=sample_count,
                        chunk_duration=float(self.config["washout_chunk_duration"]),
                    )
                    if ucs_phase.valid
                    else None
                )
                challenge = (
                    backend.run_phase(
                        washout.state,
                        duration,
                        cs,
                        memory.key.response_id,
                        sample_count=sample_count,
                        pulse_count=pulse_count,
                    )
                    if washout is not None and washout.valid
                    else None
                )
                valid = bool(
                    ucs_phase.valid
                    and washout is not None
                    and washout.valid
                    and challenge is not None
                    and challenge.valid
                )
                _append(
                    path,
                    {
                        "task_id": record_id,
                        "memory_task_id": task_id,
                        "model_id": memory.key.model_id,
                        "arm": arm,
                        "valid": valid,
                        "ucs_phase": phase_payload(ucs_phase),
                        "washout_phase": phase_payload(washout),
                        "challenge": None
                        if challenge is None
                        else _challenge_payload(memory, challenge),
                    },
                )
                self.budget.checkpoint("atlas-reinstatement")
                self.budget.enforce_hard()
        return False

    def run_relearning(self, tasks: list[str]) -> bool:
        path = self.output / "relearning.jsonl"
        completed = _completed_ids(path)
        duration = float(self.config["phase_duration"])
        sample_count = int(self.config["trajectory_samples_per_phase"])
        pulse_count = int(self.config["pulse_count"])
        include_matched = bool(self.projection["include_matched_negative_relearning"])
        for task_id in tasks:
            memory = self.memory(task_id)
            backend = self.backend(memory.key.model_id)
            stimuli = self._ucs_stimuli(
                memory, self.calibrations[task_id], include_cs=True
            )
            cs = {
                memory.cs_id: float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
            }
            for arm in ATLAS_ARMS:
                record_id = f"relearning|{task_id}|{arm}"
                if record_id in completed:
                    continue
                if not self._may_start("normal"):
                    return True
                if arm == "matched_negative" and not include_matched:
                    _append(
                        path,
                        {
                            "task_id": record_id,
                            "memory_task_id": task_id,
                            "model_id": memory.key.model_id,
                            "arm": arm,
                            "valid": False,
                            "skip_reason": "projection-fallback",
                        },
                    )
                    continue
                history = self.histories.get((task_id, arm), {})
                current = state_from_payload(
                    history.get("checkpoints", {}).get("62500", {}).get("state")
                )
                if current is None or stimuli is None:
                    _append(
                        path,
                        {
                            "task_id": record_id,
                            "memory_task_id": task_id,
                            "model_id": memory.key.model_id,
                            "arm": arm,
                            "valid": False,
                            "skip_reason": "missing-valid-checkpoint-or-ucs",
                            "cycles": [],
                        },
                    )
                    continue
                cycles: list[dict[str, Any]] = []
                valid = True
                for cycle_index in range(1, int(self.config["relearning_cycles"]) + 1):
                    train = backend.run_phase(
                        current,
                        duration,
                        stimuli,
                        memory.key.response_id,
                        sample_count=sample_count,
                        pulse_count=pulse_count,
                    )
                    if not train.valid:
                        valid = False
                        cycles.append(
                            {"cycle": cycle_index, "train": phase_payload(train), "valid": False}
                        )
                        break
                    washout = backend.run_unstimulated(
                        train.state,
                        float(self.config["reinstatement_washout_duration"]),
                        memory.key.response_id,
                        sample_count=sample_count,
                        chunk_duration=float(self.config["washout_chunk_duration"]),
                    )
                    if not washout.valid:
                        valid = False
                        cycles.append(
                            {
                                "cycle": cycle_index,
                                "train": phase_payload(train),
                                "washout": phase_payload(washout),
                                "valid": False,
                            }
                        )
                        break
                    challenge = backend.run_phase(
                        washout.state,
                        duration,
                        cs,
                        memory.key.response_id,
                        sample_count=sample_count,
                        pulse_count=pulse_count,
                    )
                    cycles.append(
                        {
                            "cycle": cycle_index,
                            "train": phase_payload(train),
                            "washout": phase_payload(washout),
                            "challenge": _challenge_payload(memory, challenge),
                            "valid": bool(challenge.valid),
                        }
                    )
                    if not challenge.valid:
                        valid = False
                        break
                    current = challenge.state
                valid = valid and len(cycles) == int(self.config["relearning_cycles"])
                _append(
                    path,
                    {
                        "task_id": record_id,
                        "memory_task_id": task_id,
                        "model_id": memory.key.model_id,
                        "arm": arm,
                        "valid": bool(valid),
                        "cycles": cycles,
                    },
                )
                self.budget.checkpoint("atlas-relearning")
                self.budget.enforce_hard()
        return False

    def run(self) -> int:
        self.state("running", "registration")
        try:
            tasks = self.prepare_registration()
            self.state("running", "calibration")
            time_exhausted = self.calibrate(tasks)
            self._load_calibrations()
            if not time_exhausted:
                self.state("running", "histories")
                time_exhausted = self.run_histories(tasks)
            self._load_histories()
            if not time_exhausted:
                self.state("running", "counterfactual-probes")
                time_exhausted = self.run_probes(tasks)
            if not time_exhausted:
                self.state("running", "reinstatement")
                time_exhausted = self.run_reinstatement(tasks)
            if not time_exhausted:
                self.state("running", "relearning")
                time_exhausted = self.run_relearning(tasks)
            from .atlas_analysis import analyze_atlas

            final_status = "time-budget-exhausted" if time_exhausted else "completed"
            self.state("finalizing", "analysis")
            analyze_atlas(self.output, final_status=final_status)
            self.state(final_status, "complete")
            write_checksums(self.output)
            return 124 if time_exhausted else 0
        except TimeoutError as error:
            from .atlas_analysis import analyze_atlas

            analyze_atlas(self.output, final_status="time-budget-exhausted")
            self.state("time-budget-exhausted", "interrupted", error=str(error))
            write_checksums(self.output)
            return 124
        except BaseException as error:
            self.state("failed", "exception", error=repr(error))
            raise


def run_atlas(
    config: Path,
    parent: Path,
    upstream: Path,
    output: Path,
    workers: int = 1,
) -> int:
    return AtlasCampaign(config, parent, upstream, output, workers=workers).run()


def smoke_atlas(
    config_path: Path,
    parent: Path,
    upstream: Path,
    output: Path,
) -> dict[str, Any]:
    """Image-bound historical and biological preflight for the atlas."""

    config = load_atlas_config(config_path)
    parent = parent.resolve()
    upstream = upstream.resolve()
    output = output.resolve()
    validate_upstream(upstream, config["upstream_commit"])
    verify_checksums(parent)
    parent_hashes = {
        "SHA256SUMS": config["parent_manifest_sha256"],
        "registration.json": config["parent_registration_sha256"],
        "selected-actions.json": config["parent_selected_actions_sha256"],
    }
    for name, expected in parent_hashes.items():
        if sha256_file(parent / name) != expected:
            raise ValueError(f"smoke parent {name} hash mismatch")
    parent_registration = json.loads(
        (parent / "registration.json").read_text(encoding="utf-8")
    )
    projection = project_atlas_cpu(parent, parent_registration, config)
    selected_actions = {
        task_id: int(row["action_index"])
        for task_id, row in json.loads(
            (parent / "selected-actions.json").read_text(encoding="utf-8")
        )["actions"].items()
    }

    historical_records: list[dict[str, Any]] = []
    for task_id in ("10-1-10", "10-0-10"):
        released = load_released_task(upstream, task_id)
        memory = load_memory(released.memory_path, released.key)
        backend = JaxBackend(upstream, released.key.model_id, delta_t=0.01)
        replay = historical_release_replay(backend, memory, sample_count=11)
        agreement = sum(
            row["is_broken"] == expected.is_broken
            for row, expected in zip(replay, released.actions, strict=True)
        ) / len(replay)
        historical_records.append(
            {
                "task_id": task_id,
                "direction": memory.response_reg,
                "row_count": len(replay),
                "agreement": agreement,
                "all_valid": all(bool(row["valid"]) for row in replay),
            }
        )

    task_id = "10-1-25"
    released = load_released_task(upstream, task_id)
    memory = load_memory(released.memory_path, released.key)
    backend = JaxBackend(upstream, released.key.model_id, delta_t=0.01)
    selected_index = selected_actions[task_id]
    selected_phase = backend.run_phase(
        backend.memory_state(memory),
        float(config["phase_duration"]),
        stimuli_for_action(memory, selected_index),
        memory.key.response_id,
        sample_count=11,
        pulse_count=int(config["pulse_count"]),
    )
    selected_displacement = normalized_state_distance(
        selected_phase.terminal_y, memory.y, memory.bounds
    )
    negative_candidates: list[dict[str, Any]] = []
    for action in released.actions:
        if action.is_broken:
            continue
        phase = backend.run_phase(
            backend.memory_state(memory),
            float(config["phase_duration"]),
            stimuli_for_action(memory, action.index),
            memory.key.response_id,
            sample_count=11,
            pulse_count=int(config["pulse_count"]),
        )
        mean_response = float(phase.mean_y[memory.key.response_id])
        negative_candidates.append(
            {
                "action_index": action.index,
                "is_broken": is_broken(memory, mean_response),
                "valid": phase.valid,
                "state_displacement": normalized_state_distance(
                    phase.terminal_y, memory.y, memory.bounds
                ),
            }
        )
    matched = choose_matched_negative(selected_displacement, negative_candidates)
    ucs_candidates: list[dict[str, Any]] = []
    if memory.ucs_id is not None:
        for bound_index in (0, 1):
            phase = backend.run_phase(
                backend.memory_state(memory),
                float(config["phase_duration"]),
                {memory.ucs_id: float(memory.bounds[memory.ucs_id, bound_index])},
                memory.key.response_id,
                sample_count=11,
                pulse_count=int(config["pulse_count"]),
            )
            mean_response = float(phase.mean_y[memory.key.response_id])
            ucs_candidates.append(
                {
                    "bound_index": bound_index,
                    "valid": phase.valid,
                    "learned_margin": learned_margin(memory, mean_response),
                }
            )
    ucs_bound = choose_reconstructed_ucs(ucs_candidates)
    reset = backend.run_phase(
        backend.memory_state(memory),
        float(config["phase_duration"]),
        stimuli_for_action(memory, selected_index),
        memory.key.response_id,
        sample_count=11,
        pulse_count=int(config["pulse_count"]),
    )
    longest = backend.run_unstimulated(
        reset.state,
        62500.0,
        memory.key.response_id,
        sample_count=11,
        chunk_duration=float(config["washout_chunk_duration"]),
    )
    cs_value = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
    control, selected_bound, control_value = memory.action(selected_index)
    probe_specs: list[tuple[str, dict[int, float] | None]] = [
        ("no_input", None),
        ("cs", {memory.cs_id: cs_value}),
        ("selected_control", {control: control_value}),
        ("cs_selected_control", {memory.cs_id: cs_value, control: control_value}),
        (
            "opposite_selected_control",
            {control: float(memory.bounds[control, 1 - selected_bound])},
        ),
        (
            "cs_opposite_selected_control",
            {
                memory.cs_id: cs_value,
                control: float(memory.bounds[control, 1 - selected_bound]),
            },
        ),
    ]
    if memory.ucs_id is not None:
        for bound_index in (0, 1):
            probe_specs.append(
                (
                    f"ucs_bound_{bound_index}",
                    {memory.ucs_id: float(memory.bounds[memory.ucs_id, bound_index])},
                )
            )
        if ucs_bound is not None:
            probe_specs.append(
                (
                    "cs_reconstructed_ucs",
                    {
                        memory.cs_id: cs_value,
                        memory.ucs_id: float(memory.bounds[memory.ucs_id, ucs_bound]),
                    },
                )
            )
    if matched is not None:
        matched_control, _, matched_value = memory.action(int(matched["action_index"]))
        probe_specs.extend(
            [
                ("matched_control", {matched_control: matched_value}),
                (
                    "cs_matched_control",
                    {memory.cs_id: cs_value, matched_control: matched_value},
                ),
            ]
        )
    probe_results: list[dict[str, Any]] = []
    for name, stimuli in probe_specs:
        if stimuli is None:
            phase = backend.run_unstimulated(
                longest.state.copy(),
                float(config["phase_duration"]),
                memory.key.response_id,
                sample_count=11,
                chunk_duration=float(config["washout_chunk_duration"]),
            )
        else:
            phase = backend.run_phase(
                longest.state.copy(),
                float(config["phase_duration"]),
                stimuli,
                memory.key.response_id,
                sample_count=11,
                pulse_count=int(config["pulse_count"]),
            )
        probe_results.append({"name": name, "valid": bool(phase.valid)})

    failure_released = load_released_task(upstream, "69-0-2")
    failure_memory = load_memory(failure_released.memory_path, failure_released.key)
    failure_backend = JaxBackend(upstream, 69, delta_t=0.01)
    failure_probe = run_assay_condition(
        failure_backend,
        failure_memory,
        1,
        "control_only",
        0.0,
        failure_backend.memory_state(failure_memory),
        sample_count=11,
        phase_duration=2500.0,
        pulse_count=5,
        washout_chunk_duration=2500.0,
        time_match_reset_slot=True,
    )
    round_trip = json.loads(canonical_json(failure_probe))

    def null_count(value: Any) -> int:
        if value is None:
            return 1
        if isinstance(value, dict):
            return sum(null_count(item) for item in value.values())
        if isinstance(value, list):
            return sum(null_count(item) for item in value)
        return 0

    invalid_probe = {
        "task_id": "69-0-2",
        "valid": bool(failure_probe["valid"]),
        "null_leaf_count": null_count(round_trip),
        "strict_json_round_trip": True,
    }
    historical_pass = all(
        row["agreement"] == 1.0 and row["all_valid"] for row in historical_records
    )
    panel_pass = bool(
        selected_phase.valid
        and matched is not None
        and ucs_bound is not None
        and reset.valid
        and longest.valid
        and len(probe_results) >= 10
        and all(row["valid"] for row in probe_results)
    )
    invalid_pass = bool(not invalid_probe["valid"] and invalid_probe["null_leaf_count"] > 0)
    result = {
        "target": "observer-atlas",
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": digest(config),
        "parent_manifest_sha256": config["parent_manifest_sha256"],
        "pass": historical_pass and panel_pass and invalid_pass,
        "production_launch_allowed": historical_pass and panel_pass and invalid_pass,
        "historical_records": historical_records,
        "projection": projection,
        "full_panel_probe": {
            "task_id": task_id,
            "matched_negative_action_index": None
            if matched is None
            else matched["action_index"],
            "reconstructed_ucs_bound_index": ucs_bound,
            "longest_washout_valid": bool(longest.valid),
            "probe_count": len(probe_results),
            "all_probes_valid": all(row["valid"] for row in probe_results),
            "pass": panel_pass,
        },
        "known_nonfinite_probe": {**invalid_probe, "pass": invalid_pass},
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "smoke.json", result)
    return result
