from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np

from grn_reset_audit.artifacts import (
    append_jsonl,
    canonical_json,
    digest,
    read_jsonl,
    verify_checksums,
    write_checksums,
)
from grn_reset_audit.campaign import load_config
from grn_reset_audit.engine import (
    PhaseResult,
    State,
    historical_release_replay,
    independent_action,
    is_broken,
    reset_margin,
    run_assay_condition,
    source_faithful_replay,
)
from grn_reset_audit.models import MemoryData, MemoryKey, ReleasedAction, ReleasedMemory
from grn_reset_audit.upstream import (
    load_memory,
    projected_cpu_seconds,
    select_balanced_cohort,
)


def memory(direction: int = 1) -> MemoryData:
    return MemoryData(
        key=MemoryKey(10, 0, 1),
        y=np.asarray([2.0, 3.0, 4.0, 5.0]),
        w=np.asarray([]),
        c=np.asarray([1.0]),
        bounds=np.asarray([[0.0, 10.0], [0.0, 20.0], [0.0, 30.0], [0.0, 40.0]]),
        mean_relax=1.0,
        response_reg=direction,
        stimulus_reg=1,
        r_scale=2.0,
        ucs_id=2,
        cs_id=1,
        prev_mean=np.asarray([2.0, 3.0, 4.0, 5.0]),
        has_native_prev_mean=True,
        path=Path("memory.pickle"),
    )


class FakeBackend:
    def __init__(self):
        self.calls = []

    def memory_state(self, mem):
        return State(mem.y.copy(), mem.w.copy(), mem.c.copy(), 10000.0)

    def run_phase(
        self,
        state,
        duration,
        stimuli,
        response_id,
        sample_count=101,
        pulse_count=1,
    ):
        self.calls.append(
            (
                duration,
                None if stimuli is None else dict(stimuli),
                state.y.copy(),
                pulse_count,
            )
        )
        y = state.y.copy()
        if stimuli:
            y[response_id] = sum(stimuli.values()) / 10.0 + 0.123
        else:
            y[response_id] *= 0.9
        samples = np.repeat(y[:, None], 3, axis=1)
        return PhaseResult(
            state=State(y.copy(), state.w.copy(), state.c.copy(), state.t + duration),
            mean_y=y.copy(),
            terminal_y=y.copy(),
            sampled_y=samples,
            response_trajectory=samples[response_id],
            valid=True,
            cpu_seconds=0.01,
            wall_seconds=0.01,
        )

    def run_unstimulated(
        self,
        state,
        duration,
        response_id,
        sample_count=101,
        chunk_duration=None,
    ):
        return self.run_phase(
            state,
            duration,
            None,
            response_id=response_id,
            sample_count=sample_count,
        )


def test_action_mapping_and_threshold_directions():
    up = memory(1)
    assert up.action_controls() == [2, 3]
    assert up.action(0) == (2, 0, 0.0)
    assert up.action(3) == (3, 1, 40.0)
    assert is_broken(up, 1.99)
    assert not is_broken(up, 2.0)
    assert reset_margin(up, 1.0) > 0
    down = memory(2)
    assert is_broken(down, 0.51)
    assert not is_broken(down, 0.5)
    assert reset_margin(down, 1.0) > 0


def test_load_memory_tuple(tmp_path):
    values = [
        np.arange(4.0), np.asarray([]), np.asarray([1.0]), np.ones((4, 2)),
        1.0, 1, 2, 2.0, 0, 2, 1, np.arange(4.0),
    ]
    path = tmp_path / "10.0.1.pickle"
    with path.open("wb") as handle:
        pickle.dump(values, handle)
    loaded = load_memory(path)
    assert loaded.key.task_id == "10-0-1"
    assert loaded.cs_id == 1
    assert loaded.ucs_id == 2
    assert loaded.has_native_prev_mean


def test_load_legacy_memory_uses_endpoint_without_claiming_phase_mean(tmp_path):
    values = [
        np.arange(4.0), np.asarray([]), np.asarray([1.0]), np.ones((4, 2)),
        1.0, 2, 1, 2.0, 0, 2, 1,
    ]
    path = tmp_path / "10.0.1.pickle"
    with path.open("wb") as handle:
        pickle.dump(values, handle)
    loaded = load_memory(path)
    assert not loaded.has_native_prev_mean
    assert np.array_equal(loaded.prev_mean, loaded.y)


def test_source_replay_carries_state_but_independent_action_restores():
    backend = FakeBackend()
    mem = memory(1)
    rows = source_faithful_replay(backend, mem)
    assert len(rows) == 4
    assert np.array_equal(backend.calls[0][2], mem.y)
    assert not np.array_equal(backend.calls[1][2], mem.y)
    backend.calls.clear()
    independent_action(backend, mem, 0)
    independent_action(backend, mem, 1)
    assert np.array_equal(backend.calls[0][2], mem.y)
    assert np.array_equal(backend.calls[1][2], mem.y)


def test_historical_release_replay_uses_independent_five_pulse_actions():
    backend = FakeBackend()
    backend.delta_t = 0.01
    mem = memory(1)
    rows = historical_release_replay(backend, mem)
    assert len(rows) == mem.action_count()
    assert all(call[0] == 2500.0 and call[3] == 5 for call in backend.calls)
    assert all(np.array_equal(call[2], mem.y) for call in backend.calls)
    assert all(np.isfinite(row["reward"]) for row in rows)


def test_washout_has_no_intervention_and_arms_are_distinct():
    mem = memory(1)
    naive = State(np.zeros(4), np.asarray([]), np.asarray([1.0]), 10000.0)
    backend = FakeBackend()
    result = run_assay_condition(backend, mem, 3, "combined_reset", 500.0, naive)
    assert result["arm"] == "combined_reset"
    assert backend.calls[0][1] == {1: 20.0, 3: 40.0}
    assert backend.calls[1][0] == 500.0
    assert backend.calls[1][1] is None
    assert backend.calls[2][1] == {1: 20.0}
    backend.calls.clear()
    run_assay_condition(backend, mem, 3, "trained_no_reset", 0.0, naive)
    assert len(backend.calls) == 1
    assert backend.calls[0][1] == {1: 20.0}


def test_historical_assay_time_matches_unstimulated_control_slot():
    mem = memory(1)
    naive = State(np.zeros(4), np.asarray([]), np.asarray([1.0]), 10000.0)
    backend = FakeBackend()
    result = run_assay_condition(
        backend,
        mem,
        3,
        "trained_no_reset",
        2500.0,
        naive,
        phase_duration=2500.0,
        pulse_count=5,
        washout_chunk_duration=2500.0,
        time_match_reset_slot=True,
    )
    assert result["valid"]
    assert [call[0] for call in backend.calls] == [2500.0, 2500.0, 2500.0]
    assert backend.calls[0][1] is None
    assert backend.calls[1][1] is None
    assert backend.calls[2][1] == {1: 20.0}
    assert backend.calls[2][3] == 5


def released(model_id, circuit_id, direction, positive=True):
    key = MemoryKey(model_id, 0, circuit_id)
    return ReleasedMemory(
        key=key,
        csv_path=Path(f"{key.task_id}.csv"),
        memory_path=Path(f"{key.task_id}.pickle"),
        actions=[ReleasedAction(0, 0.0, positive, 1.0), ReleasedAction(1, 0.0, False, 2.0)],
        released_runtime_seconds=2.0,
        response_reg=direction,
    )


def test_balanced_selection_is_stable_and_projection_positive():
    corpus = [released(10, i, 1 if i % 2 else 2) for i in range(12)]
    first = select_balanced_cohort(corpus, 4, "salt")
    second = select_balanced_cohort(reversed(corpus), 4, "salt")
    assert [x.key.task_id for x in first] == [x.key.task_id for x in second]
    assert len(first) == 4
    assert {x.response_reg for x in first} == {1, 2}
    assert projected_cpu_seconds(first) > 0


def test_artifact_checksums(tmp_path):
    (tmp_path / "a.txt").write_text("hello\n")
    write_checksums(tmp_path)
    verdicts = verify_checksums(tmp_path)
    assert verdicts == {"a.txt": True}
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})


def test_nonfinite_numpy_leaves_are_strict_json_nulls(tmp_path):
    record = {
        "valid": False,
        "phase": {
            "mean_y": np.asarray([1.0, np.nan, np.inf, -np.inf]),
            "nested": np.asarray([[np.float64(np.nan)]]),
        },
        "scalar": np.float64(np.nan),
    }
    encoded = canonical_json(record)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded
    path = tmp_path / "invalid-trajectory.jsonl"
    append_jsonl(path, [record])
    loaded = list(read_jsonl(path))
    assert loaded == [
        {
            "phase": {
                "mean_y": [1.0, None, None, None],
                "nested": [[None]],
            },
            "scalar": None,
            "valid": False,
        }
    ]


def test_v4_amendment_freezes_cohort_budget_and_invalid_policy():
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "configs" / "grn-historical-washout-v4.json")
    assert config["source_semantics"] == "historical-release"
    assert config["source_reward_required"] is False
    assert len(config["fixed_cohort_task_ids"]) == 24
    assert config["invalid_trajectory_policy"] == "record-null-exclude-cell-no-rerun"
    assert config["fresh_run"] is True
    assert config["hard_cpu_seconds"] == 14100.0
    assert config["hard_wall_seconds"] == 14400.0
