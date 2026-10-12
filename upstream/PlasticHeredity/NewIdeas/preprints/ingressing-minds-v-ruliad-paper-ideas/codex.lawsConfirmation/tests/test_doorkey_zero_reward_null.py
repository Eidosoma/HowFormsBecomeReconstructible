import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from laws_confirmation.doorkey_env import oracle_plan
from laws_confirmation.doorkey_ppo_v2 import (
    FeedbackPPOConfig,
    collect_feedback_rollout,
)
from laws_confirmation.doorkey_zero_reward_null import (
    REGISTERED_REPLICATES,
    TERMINAL_REFERENCE_RUN,
    ZeroRewardDoorKeyVectorEnv,
    _custom_null_update,
    _train_cell,
    initialize_null_descendant,
    qualify_terminal_reference,
)


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


def test_zero_reward_wrapper_records_goal_but_never_exposes_reward():
    environments = ZeroRewardDoorKeyVectorEnv(1, 1234, 128)
    plan = oracle_plan(environments.envs[0].layout)
    observed_rewards = []
    done = False
    for action in plan:
        _, rewards, dones, _ = environments.step(
            np.asarray([int(action)], dtype=np.int64)
        )
        observed_rewards.append(float(rewards[0]))
        done = bool(dones[0])
        if done:
            break
    assert done
    assert observed_rewards and set(observed_rewards) == {0.0}
    completed = environments.pop_completed()
    assert len(completed) == 1
    assert completed[0]["success"] is True


def test_zero_critic_changes_no_actor_or_encoder_birth_parameters():
    config = _small_config()
    ordinary = initialize_null_descendant(config, 555, "raw_advantage")
    zeroed = initialize_null_descendant(config, 555, "zero_critic")
    for name, value in ordinary.model.state_dict().items():
        if name.startswith("critic."):
            assert torch.count_nonzero(zeroed.model.state_dict()[name]) == 0
        else:
            assert torch.equal(value, zeroed.model.state_dict()[name]), name


@pytest.mark.parametrize("arm", ["raw_advantage", "actor_guard"])
def test_custom_zero_reward_updates_are_finite(arm):
    config = _small_config()
    descendant = initialize_null_descendant(config, 777, arm)
    environments = ZeroRewardDoorKeyVectorEnv(
        config.num_envs, 888, config.max_episode_steps
    )
    rollout, _ = collect_feedback_rollout(
        descendant, environments, config, "blind"
    )
    assert torch.count_nonzero(rollout.rewards) == 0
    metrics = _custom_null_update(descendant, rollout, config, arm)
    assert all(math.isfinite(value) for value in metrics.values())
    if arm == "actor_guard":
        assert metrics["policy_loss"] == 0.0


def test_terminal_reference_gate_checks_zero_first_twenty(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("frozen\n", encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")
    study = tmp_path / "study.json"
    study.write_text(
        json.dumps(
            {
                "run_id": TERMINAL_REFERENCE_RUN,
                "completed_cleanly": True,
                "credit_routing_classification": "NO_TERMINAL_REWARD_OBSERVED",
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "run_id": TERMINAL_REFERENCE_RUN,
                "input_sha256": {str(source): _sha256(source)},
            }
        ),
        encoding="utf-8",
    )
    hashes = tmp_path / "output_hashes.sha256"
    hashes.write_text(f"{_sha256(artifact)}  {artifact}\n", encoding="utf-8")
    replicate_paths = []
    for spec in REGISTERED_REPLICATES:
        path = tmp_path / f"replicate_{spec['replicate']}.json"
        path.write_text(
            json.dumps(
                {
                    **spec,
                    "training": {
                        "history": [
                            {
                                "mean_rollout_reward": 0.0,
                                "max_rollout_reward": 0.0,
                                "cumulative_successes": 0,
                            }
                            for _ in range(20)
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        replicate_paths.append(path)

    result = qualify_terminal_reference(
        study, manifest, hashes, replicate_paths
    )
    assert result["passes"], result

    changed = json.loads(replicate_paths[0].read_text(encoding="utf-8"))
    changed["training"]["history"][3]["max_rollout_reward"] = 1.0
    replicate_paths[0].write_text(json.dumps(changed), encoding="utf-8")
    failed = qualify_terminal_reference(
        study, manifest, hashes, replicate_paths
    )
    assert not failed["passes"]
    assert not failed["gates"]["reference_first_twenty_rewards_exactly_zero"]


@pytest.mark.parametrize("arm", ["raw_advantage", "actor_guard", "zero_critic"])
def test_complete_small_null_cell(tmp_path, monkeypatch, arm):
    import laws_confirmation.doorkey_zero_reward_null as null_panel

    config = _small_config()
    monkeypatch.setattr(
        null_panel, "EXPECTED_STEPS", 20 * config.num_envs * config.rollout_steps
    )
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    result = _train_cell(
        arm,
        REGISTERED_REPLICATES[0],
        config,
        tmp_path,
        output_dir,
    )
    assert result["completed_cleanly"], result["completion_gates"]
    assert result["environment_steps"] == 640
    assert len(result["evaluations"]) == 6
