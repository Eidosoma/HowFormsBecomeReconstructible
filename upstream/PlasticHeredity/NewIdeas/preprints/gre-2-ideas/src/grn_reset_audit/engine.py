"""Exact upstream-compatible ODE phases and reset assay logic."""

from __future__ import annotations

import importlib.util
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .models import MemoryData


@dataclass
class State:
    y: np.ndarray
    w: np.ndarray
    c: np.ndarray
    t: float

    def copy(self) -> "State":
        return State(self.y.copy(), self.w.copy(), self.c.copy(), float(self.t))


@dataclass
class PhaseResult:
    state: State
    mean_y: np.ndarray
    terminal_y: np.ndarray
    sampled_y: np.ndarray
    response_trajectory: np.ndarray
    valid: bool
    cpu_seconds: float
    wall_seconds: float


def is_broken(memory: MemoryData, mean_response: float) -> bool:
    if memory.response_reg == 1:
        return mean_response < memory.r_scale * memory.mean_relax
    return mean_response > memory.mean_relax / memory.r_scale


def reset_margin(memory: MemoryData, mean_response: float) -> float:
    if memory.response_reg == 1:
        threshold = memory.r_scale * memory.mean_relax
        return (threshold - mean_response) / max(abs(threshold), 1e-12)
    threshold = memory.mean_relax / memory.r_scale
    return (mean_response - threshold) / max(abs(threshold), 1e-12)


def raw_reward(memory: MemoryData, mean_response: float, previous_response: float) -> float:
    epsilon = 1e-10
    if memory.response_reg == 1:
        return (mean_response - previous_response) / (previous_response + epsilon)
    return (previous_response - mean_response) / (previous_response + epsilon)


def normalized_reward(raw: float, rewards: list[float]) -> float:
    scale = float(np.nanstd(rewards)) if len(rewards) > 1 else 1.0
    return (raw - float(np.nanmedian(rewards))) / scale


class JaxBackend:
    """Minimal replica of the upstream GeneRegulatoryNetwork rollout path."""

    def __init__(self, upstream_root: Path, model_id: int, delta_t: float = 0.1):
        import jax
        from addict import Dict
        from autodiscjax import DictTree
        from autodiscjax.modules import grnwrappers

        self.jax = jax
        self.Dict = Dict
        self.DictTree = DictTree
        self.grnwrappers = grnwrappers
        self.upstream_root = upstream_root.resolve()
        self.model_id = int(model_id)
        self.delta_t = float(delta_t)
        model_path = self.upstream_root / "data" / f"biomodel_{model_id}.py"
        if not model_path.is_file():
            raise FileNotFoundError(model_path)
        module_name = f"grn_reset_upstream_biomodel_{model_id}"
        spec = importlib.util.spec_from_file_location(module_name, model_path)
        if spec is None or spec.loader is None:
            raise ImportError(model_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        self.module = module
        self.node_count = len(module.y_indexes)
        self.default_y = np.asarray(module.y0, dtype=float)
        self.default_w = np.asarray(module.w0, dtype=float)
        self.default_c = np.asarray(module.c, dtype=float)
        self.default_t = float(module.t0)
        self._key = jax.random.PRNGKey(0)

    def initial_state(self) -> State:
        return State(
            self.default_y.copy(),
            self.default_w.copy(),
            self.default_c.copy(),
            self.default_t,
        )

    def memory_state(self, memory: MemoryData) -> State:
        return State(memory.y.copy(), memory.w.copy(), memory.c.copy(), 10000.0)

    def _system(self, state: State, duration: float):
        config = self.Dict()
        config.system_type = "grn"
        config.model_filepath = str(
            self.upstream_root / "data" / f"biomodel_{self.model_id}.py"
        )
        config.atol = 1e-3
        config.rtol = 1e-12
        config.mxstep = 50000
        config.deltaT = self.delta_t
        config.n_secs = float(duration)
        config.n_system_steps = int(round(float(duration) / self.delta_t))
        grnstep = self.module.ModelStep(
            atol=config.atol, rtol=config.rtol, mxstep=config.mxstep
        )
        return self.grnwrappers.GRNRollout(
            n_steps=config.n_system_steps,
            y0=self.jax.numpy.asarray(state.y),
            w0=self.jax.numpy.asarray(state.w),
            c=self.jax.numpy.asarray(state.c),
            t0=state.t,
            deltaT=self.delta_t,
            grn_step=grnstep,
        )

    @staticmethod
    def _sample_columns(values: np.ndarray, count: int) -> np.ndarray:
        if values.ndim != 2 or values.shape[1] == 0:
            return np.empty((values.shape[0] if values.ndim else 0, 0), dtype=float)
        indices = np.linspace(0, values.shape[1] - 1, min(count, values.shape[1]))
        return values[:, np.rint(indices).astype(int)]

    def run_phase(
        self,
        state: State,
        duration: float,
        stimuli: Mapping[int, float] | None,
        response_id: int,
        sample_count: int = 101,
        pulse_count: int = 1,
    ) -> PhaseResult:
        duration = float(duration)
        if duration == 0.0:
            sampled = state.y[:, None]
            return PhaseResult(
                state=state.copy(),
                mean_y=state.y.copy(),
                terminal_y=state.y.copy(),
                sampled_y=sampled,
                response_trajectory=np.asarray([state.y[response_id]], dtype=float),
                valid=bool(np.all(np.isfinite(state.y))),
                cpu_seconds=0.0,
                wall_seconds=0.0,
            )
        if duration < 0 or not math.isclose(
            duration / self.delta_t, round(duration / self.delta_t), abs_tol=1e-8
        ):
            raise ValueError(f"duration {duration} is not a nonnegative delta-t multiple")
        if not isinstance(pulse_count, int) or pulse_count < 1:
            raise ValueError("pulse_count must be a positive integer")
        system = self._system(state, duration)
        intervention_fn = None
        intervention_params = None
        if stimuli:
            intervention_params = self.DictTree()
            intervals: list[list[float]] = []
            window = duration // (pulse_count * 2)
            for node, value in stimuli.items():
                intervention_params.y[int(node)] = self.jax.numpy.asarray([float(value)])
                start = state.t
                for _ in range(pulse_count):
                    intervals.append([start, start + window])
                    start += window * 2
            intervention_fn = self.grnwrappers.PiecewiseSetConstantIntervention(
                time_to_interval_fn=self.grnwrappers.TimeToInterval(intervals=intervals)
            )
        _, subkey = self.jax.random.split(self._key)
        cpu_start = time.process_time()
        wall_start = time.monotonic()
        output = system(subkey, intervention_fn, intervention_params, None, None)[0]
        # Force completion before taking timings.
        ys = np.asarray(output.ys, dtype=float)
        ws = np.asarray(output.ws, dtype=float)
        cs = np.asarray(output.cs, dtype=float)
        wall_seconds = time.monotonic() - wall_start
        cpu_seconds = time.process_time() - cpu_start
        if ys.ndim != 2 or ys.shape[1] == 0:
            raise ValueError("upstream rollout returned no state samples")
        final_w = ws[:, -1] if ws.ndim == 2 and ws.shape[1] else state.w.copy()
        final_c = cs[:, -1] if cs.ndim == 2 and cs.shape[1] else state.c.copy()
        terminal = ys[:, -1]
        final_state = State(
            terminal.copy(),
            np.asarray(final_w, dtype=float).copy(),
            np.asarray(final_c, dtype=float).copy(),
            state.t + ys.shape[1] * self.delta_t,
        )
        sampled = self._sample_columns(ys, sample_count)
        return PhaseResult(
            state=final_state,
            mean_y=np.nanmean(ys, axis=1),
            terminal_y=terminal,
            sampled_y=sampled,
            response_trajectory=sampled[response_id, :].copy(),
            valid=bool(np.all(np.isfinite(ys))),
            cpu_seconds=float(cpu_seconds),
            wall_seconds=float(wall_seconds),
        )

    def run_unstimulated(
        self,
        state: State,
        duration: float,
        response_id: int,
        sample_count: int = 101,
        chunk_duration: float | None = None,
    ) -> PhaseResult:
        """Evolve without intervention, chunking long washouts at exact boundaries."""

        duration = float(duration)
        if chunk_duration is None or duration <= float(chunk_duration):
            return self.run_phase(
                state, duration, None, response_id=response_id, sample_count=sample_count
            )
        chunk_duration = float(chunk_duration)
        if chunk_duration <= 0:
            raise ValueError("chunk_duration must be positive")
        remaining = duration
        current = state.copy()
        weighted_mean = np.zeros_like(state.y, dtype=float)
        total_steps = 0
        sample_blocks: list[np.ndarray] = []
        valid = True
        cpu_seconds = 0.0
        wall_seconds = 0.0
        while remaining > 1e-9:
            segment = min(chunk_duration, remaining)
            phase = self.run_phase(
                current,
                segment,
                None,
                response_id=response_id,
                sample_count=sample_count,
            )
            steps = int(round(segment / self.delta_t))
            weighted_mean += phase.mean_y * steps
            total_steps += steps
            sample_blocks.append(phase.sampled_y)
            valid = valid and phase.valid
            cpu_seconds += phase.cpu_seconds
            wall_seconds += phase.wall_seconds
            current = phase.state
            remaining -= segment
        combined_samples = np.concatenate(sample_blocks, axis=1)
        sampled = self._sample_columns(combined_samples, sample_count)
        return PhaseResult(
            state=current,
            mean_y=weighted_mean / total_steps,
            terminal_y=current.y.copy(),
            sampled_y=sampled,
            response_trajectory=sampled[response_id, :].copy(),
            valid=bool(valid),
            cpu_seconds=float(cpu_seconds),
            wall_seconds=float(wall_seconds),
        )

    def naive_at_time(
        self,
        target_time: float,
        response_id: int,
        sample_count: int = 101,
        chunk_duration: float | None = None,
    ) -> PhaseResult:
        initial = self.initial_state()
        return self.run_unstimulated(
            initial,
            target_time - initial.t,
            response_id=response_id,
            sample_count=sample_count,
            chunk_duration=chunk_duration,
        )


def run_epoch_schedule(
    backend: JaxBackend,
    state: State,
    epochs: Sequence[Mapping[int, float] | None],
    epoch_duration: float,
    response_id: int,
    sample_count: int = 101,
) -> PhaseResult:
    """Run an ordered, dose-auditable sequence of half-on/half-off epochs.

    ``JaxBackend.run_phase`` applies a one-pulse intervention during the first
    half of a phase.  Chaining equal phases therefore gives a simple exact
    timing language without changing the pinned upstream intervention code.
    """

    if not epochs:
        raise ValueError("epoch schedule must contain at least one epoch")
    duration = float(epoch_duration)
    if duration <= 0:
        raise ValueError("epoch_duration must be positive")
    current = state.copy()
    weighted_mean = np.zeros_like(state.y, dtype=float)
    total_steps = 0
    blocks: list[np.ndarray] = []
    valid = True
    cpu_seconds = 0.0
    wall_seconds = 0.0
    for stimuli in epochs:
        phase = backend.run_phase(
            current,
            duration,
            stimuli,
            response_id=response_id,
            sample_count=sample_count,
            pulse_count=1,
        )
        steps = int(round(duration / backend.delta_t))
        weighted_mean += np.asarray(phase.mean_y, dtype=float) * steps
        total_steps += steps
        blocks.append(np.asarray(phase.sampled_y, dtype=float))
        current = phase.state
        valid = valid and bool(phase.valid)
        cpu_seconds += float(phase.cpu_seconds)
        wall_seconds += float(phase.wall_seconds)
    combined = np.concatenate(blocks, axis=1)
    sampled = backend._sample_columns(combined, sample_count)
    return PhaseResult(
        state=current,
        mean_y=weighted_mean / total_steps,
        terminal_y=current.y.copy(),
        sampled_y=sampled,
        response_trajectory=sampled[response_id, :].copy(),
        valid=bool(valid),
        cpu_seconds=cpu_seconds,
        wall_seconds=wall_seconds,
    )


def stimuli_for_action(memory: MemoryData, action_index: int) -> dict[int, float]:
    control, _, value = memory.action(action_index)
    return {
        memory.cs_id: float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2]),
        control: value,
    }


def source_faithful_replay(
    backend: JaxBackend, memory: MemoryData, sample_count: int = 101
) -> list[dict[str, Any]]:
    state = backend.memory_state(memory)
    previous_mean = memory.prev_mean.copy()
    rewards = [memory.mean_relax]
    records: list[dict[str, Any]] = []
    for action_index in range(memory.action_count()):
        phase = backend.run_phase(
            state,
            100.0,
            stimuli_for_action(memory, action_index),
            response_id=memory.key.response_id,
            sample_count=sample_count,
        )
        mean_response = float(phase.mean_y[memory.key.response_id])
        raw = raw_reward(
            memory, mean_response, float(previous_mean[memory.key.response_id])
        )
        reward = normalized_reward(raw, rewards)
        rewards.append(raw)
        records.append(
            {
                "action_index": action_index,
                "mean_response": mean_response,
                "reward": reward,
                "is_broken": is_broken(memory, mean_response),
                "valid": phase.valid,
                "cpu_seconds": phase.cpu_seconds,
            }
        )
        state = phase.state
        previous_mean = np.nan_to_num(phase.mean_y, nan=0.0)
        if state.t >= 12500.0 or not phase.valid:
            state = backend.memory_state(memory)
            previous_mean = memory.prev_mean.copy()
    return records


def historical_release_replay(
    backend: JaxBackend, memory: MemoryData, sample_count: int = 11
) -> list[dict[str, Any]]:
    """Replay the single-action CSV generator present at upstream ``dac00b7``.

    The released CSV headers date to 2024-10-25, immediately after that
    commit.  At that revision an action lasted 2,500 units at delta-t 0.01,
    used five on/off pulses, and hit the 12,500 termination boundary after
    every candidate.  Consequently every action began from the saved state.
    """

    if not math.isclose(backend.delta_t, 0.01, abs_tol=1e-12):
        raise ValueError("historical release replay requires delta_t=0.01")
    records: list[dict[str, Any]] = []
    for action_index in range(memory.action_count()):
        phase = backend.run_phase(
            backend.memory_state(memory),
            2500.0,
            stimuli_for_action(memory, action_index),
            response_id=memory.key.response_id,
            sample_count=sample_count,
            pulse_count=5,
        )
        mean_response = float(phase.mean_y[memory.key.response_id])
        if memory.response_reg == 1:
            reward = 1.0 - (memory.r_scale * memory.mean_relax / mean_response)
        else:
            reward = mean_response / (memory.mean_relax / memory.r_scale) - 1.0
        records.append(
            {
                "action_index": action_index,
                "mean_response": mean_response,
                "reward": reward,
                "is_broken": is_broken(memory, mean_response),
                "valid": phase.valid,
                "cpu_seconds": phase.cpu_seconds,
            }
        )
    return records


def independent_action(
    backend: JaxBackend,
    memory: MemoryData,
    action_index: int,
    sample_count: int = 101,
    phase_duration: float = 100.0,
    pulse_count: int = 1,
) -> tuple[dict[str, Any], PhaseResult]:
    phase = backend.run_phase(
        backend.memory_state(memory),
        phase_duration,
        stimuli_for_action(memory, action_index),
        response_id=memory.key.response_id,
        sample_count=sample_count,
        pulse_count=pulse_count,
    )
    mean_response = float(phase.mean_y[memory.key.response_id])
    return (
        {
            "action_index": action_index,
            "mean_response": mean_response,
            "is_broken": is_broken(memory, mean_response),
            "reset_margin": reset_margin(memory, mean_response),
            "valid": phase.valid,
            "cpu_seconds": phase.cpu_seconds,
        },
        phase,
    )


def _phase_payload(phase: PhaseResult | None) -> dict[str, Any] | None:
    if phase is None:
        return None
    return {
        "mean_y": phase.mean_y,
        "terminal_y": phase.terminal_y,
        "sampled_y": phase.sampled_y,
        "response_trajectory": phase.response_trajectory,
        "valid": phase.valid,
        "cpu_seconds": phase.cpu_seconds,
        "wall_seconds": phase.wall_seconds,
        "end_time": phase.state.t,
    }


def run_assay_condition(
    backend: JaxBackend,
    memory: MemoryData,
    action_index: int,
    arm: str,
    washout_duration: float,
    naive_state: State,
    sample_count: int = 101,
    phase_duration: float = 100.0,
    pulse_count: int = 1,
    washout_chunk_duration: float | None = None,
    time_match_reset_slot: bool = False,
) -> dict[str, Any]:
    """Run one reset/washout/rechallenge arm from an explicit initial state."""

    allowed = {"naive", "trained_no_reset", "cs_sham", "control_only", "combined_reset"}
    if arm not in allowed:
        raise ValueError(f"unknown assay arm: {arm}")
    if arm == "naive":
        state = naive_state.copy()
    else:
        state = backend.memory_state(memory)
    control, bound_index, control_value = memory.action(action_index)
    cs_value = float(memory.bounds[memory.cs_id, memory.stimulus_reg % 2])
    reset_phase: PhaseResult | None = None
    reset_stimuli: dict[int, float] | None = None
    if arm == "cs_sham":
        reset_stimuli = {memory.cs_id: cs_value}
    elif arm == "control_only":
        reset_stimuli = {control: control_value}
    elif arm == "combined_reset":
        reset_stimuli = {memory.cs_id: cs_value, control: control_value}
    if reset_stimuli is not None:
        reset_phase = backend.run_phase(
            state,
            phase_duration,
            reset_stimuli,
            response_id=memory.key.response_id,
            sample_count=sample_count,
            pulse_count=pulse_count,
        )
        state = reset_phase.state
    elif time_match_reset_slot:
        reset_phase = backend.run_unstimulated(
            state,
            phase_duration,
            response_id=memory.key.response_id,
            sample_count=sample_count,
            chunk_duration=washout_chunk_duration,
        )
        state = reset_phase.state
    washout_phase: PhaseResult | None = None
    if washout_duration > 0:
        washout_phase = backend.run_unstimulated(
            state,
            washout_duration,
            response_id=memory.key.response_id,
            sample_count=sample_count,
            chunk_duration=washout_chunk_duration,
        )
        state = washout_phase.state
    challenge_phase = backend.run_phase(
        state,
        phase_duration,
        {memory.cs_id: cs_value},
        response_id=memory.key.response_id,
        sample_count=sample_count,
        pulse_count=pulse_count,
    )
    challenge_mean = float(challenge_phase.mean_y[memory.key.response_id])
    reset_mean = (
        None
        if reset_phase is None
        else float(reset_phase.mean_y[memory.key.response_id])
    )
    valid = challenge_phase.valid and (
        reset_phase is None or reset_phase.valid
    ) and (washout_phase is None or washout_phase.valid)
    cpu_seconds = sum(
        phase.cpu_seconds
        for phase in (reset_phase, washout_phase, challenge_phase)
        if phase is not None
    )
    wall_seconds = sum(
        phase.wall_seconds
        for phase in (reset_phase, washout_phase, challenge_phase)
        if phase is not None
    )
    return {
        "arm": arm,
        "washout_duration": float(washout_duration),
        "action_index": int(action_index),
        "control_id": int(control),
        "control_bound_index": int(bound_index),
        "control_value": float(control_value),
        "cs_id": int(memory.cs_id),
        "cs_value": cs_value,
        "reset_mean_response": reset_mean,
        "reset_is_broken": None
        if reset_mean is None
        else is_broken(memory, reset_mean),
        "challenge_mean_response": challenge_mean,
        "challenge_is_broken": is_broken(memory, challenge_mean),
        "challenge_reset_margin": reset_margin(memory, challenge_mean),
        "valid": valid,
        "cpu_seconds": float(cpu_seconds),
        "wall_seconds": float(wall_seconds),
        "reset_phase": _phase_payload(reset_phase),
        "washout_phase": _phase_payload(washout_phase),
        "challenge_phase": _phase_payload(challenge_phase),
    }
