import hashlib
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from laws_confirmation.doorkey_phase_value_credit import ARMS
from laws_confirmation.doorkey_phase_value_multiseed import (
    ANCHOR_RUN,
    REGISTERED_REPLICATES,
    _new_cell_specs,
    _outcome_classification,
    _paired_seed_summary,
    _train_cell,
    qualify_anchor,
)
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _small_config() -> FeedbackPPOConfig:
    return FeedbackPPOConfig(
        num_envs=4,
        rollout_steps=8,
        minibatch_envs=2,
        max_episode_steps=32,
        hidden_size=16,
        tile_embedding_size=4,
        action_embedding_size=4,
    )


def _chain(reached_through: int, *, goal_count: int = 0):
    events = (
        "explore",
        "find_key",
        "retain_key",
        "find_door",
        "open_door",
        "reach_goal",
    )
    rows = []
    eligible = 128
    for index, event in enumerate(events):
        reached = max(0, 128 - index * 10) if index <= reached_through else 0
        if event == "reach_goal" and index <= reached_through:
            reached = goal_count
        rows.append(
            {
                "from": "episode_start" if index == 0 else events[index - 1],
                "to": event,
                "eligible": eligible,
                "reached": reached,
                "conditional_probability": reached / eligible if eligible else None,
            }
        )
        eligible = reached
    return rows


def _summary(arm: str, depth: int, *, goals: int = 0):
    events = ("explore", "find_key", "retain_key", "find_door", "open_door", "reach_goal")
    chain = _chain(depth, goal_count=goals)
    return {
        "replicate": 0,
        "source": "test",
        "birth_seed": 1,
        "training_seed": 2,
        "arm": arm,
        "training_goal_successes": goals,
        "training_event_counts": {"key": 10, "door": 5, "goal": goals},
        "final_successes": {"deterministic": 0, "fixed_random": goals},
        "deepest_reached": {
            "deterministic": events[depth] if depth >= 0 else None,
            "fixed_random": events[depth] if depth >= 0 else None,
        },
        "final_chain": {"deterministic": chain, "fixed_random": chain},
    }


def test_registered_cells_use_three_new_seed_pairs_and_all_arms():
    assert [row["replicate"] for row in REGISTERED_REPLICATES] == [1, 2, 3]
    assert {row["birth_seed"] for row in REGISTERED_REPLICATES}.isdisjoint(
        {920_000, 921_000, 922_000, 923_000}
    )
    cells = _new_cell_specs()
    assert len(cells) == 9
    assert [row["arm"] for row in cells[:3]] == list(ARMS)
    assert len(
        {(row["replicate"], row["arm"]) for row in cells}
    ) == 9


def test_paired_summary_records_phase_depth_and_raw_difference():
    summaries = [
        _summary("guarded_terminal", 3),
        _summary("aux_critic_only", 3),
        _summary("phase_actor", 5, goals=2),
    ]
    paired = _paired_seed_summary(summaries, 0)
    assert paired["phase_deeper_than_both_controls"] == {
        "deterministic": True,
        "fixed_random": True,
    }
    by_event = {
        row["event"]: row for row in paired["fixed_random_chain_differences"]
    }
    assert by_event["open_door"]["phase_minus_best_control"] == 88
    assert by_event["reach_goal"]["phase_minus_best_control"] == 2
    assert paired["phase_minus_best_control_training_goals"] == 2
    assert _outcome_classification([paired]) == "PHASE_DEEPER_FIXED_1_OF_1_ARGMAX_1_OF_1"


def test_anchor_gate_verifies_frozen_inputs_outputs_and_arm_specs(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("frozen\n", encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")
    scout_path = tmp_path / "scout.json"
    expected_specs = [
        {
            "arm": arm,
            "birth_seed": 920_000,
            "training_seed": 930_000,
            "updates": 100,
        }
        for arm in ARMS
    ]
    scout_path.write_text(
        json.dumps(
            {
                "run_id": ANCHOR_RUN,
                "completed_cleanly": True,
                "outcome_classification": "PHASE_ACTOR_ADVANCED_DEEPEST_LINK",
                "completion_gates": {"all_arms_completed_cleanly": True},
                "arm_specs": expected_specs,
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": ANCHOR_RUN,
                "input_sha256": {str(source): _sha256(source)},
            }
        ),
        encoding="utf-8",
    )
    hashes_path = tmp_path / "output_hashes.sha256"
    hashes_path.write_text(
        f"{_sha256(artifact)}  {artifact}\n", encoding="utf-8"
    )
    arm_paths = []
    for row in expected_specs:
        path = tmp_path / f"{row['arm']}.json"
        path.write_text(
            json.dumps({**row, "completed_cleanly": True}), encoding="utf-8"
        )
        arm_paths.append(path)
    qualified = qualify_anchor(
        scout_path, manifest_path, hashes_path, arm_paths
    )
    assert qualified["passes"], qualified
    source.write_text("changed\n", encoding="utf-8")
    failed = qualify_anchor(scout_path, manifest_path, hashes_path, arm_paths)
    assert not failed["passes"]
    assert not failed["gates"]["all_anchor_inputs_verify"]


def test_complete_small_multiseed_cell(tmp_path, monkeypatch):
    import laws_confirmation.doorkey_phase_value_multiseed as multiseed

    config = _small_config()
    monkeypatch.setattr(multiseed, "UPDATES", 10)
    monkeypatch.setattr(
        multiseed,
        "EXPECTED_STEPS",
        10 * config.num_envs * config.rollout_steps,
    )
    output_dir = tmp_path / "outputs"
    (output_dir / "progress").mkdir(parents=True)
    spec = {
        "replicate": 1,
        "arm": "guarded_terminal",
        "birth_seed": 924_000,
        "training_seed": 934_000,
        "updates": 10,
    }
    result = _train_cell(spec, config, tmp_path, output_dir)
    assert result["completed_cleanly"], result["completion_gates"]
    assert result["environment_steps"] == 320
    assert len(result["evaluations"]) == 4
    progress = json.loads(
        (output_dir / "progress/guarded_terminal_replicate_1.json").read_text(
            encoding="utf-8"
        )
    )
    assert progress["status"] == "COMPLETE"
