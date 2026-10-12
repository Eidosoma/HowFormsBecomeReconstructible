import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from laws_confirmation.doorkey_phase_value_credit import (
    ARMS,
    CausalCreditRollout,
    _train_arm,
    actor_advantage_for_arm,
    causal_credit_digests,
    causal_credit_ppo_update,
    collect_causal_credit_rollout,
    guarded_standardize,
    make_causal_credit_descendant,
    phase_from_observations,
    qualify_null_reference,
    rollout_semantics,
)
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig
from laws_confirmation.doorkey_zero_reward_null import TERMINAL_REFERENCE_RUN


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synthetic_rollout(*, key_signal: bool) -> CausalCreditRollout:
    time_steps = 4
    batch = 1
    observations = torch.zeros(time_steps, batch, 13)
    phases = torch.tensor([[0], [0], [1], [2]], dtype=torch.long)
    event_rewards = torch.zeros(time_steps, batch, 3)
    if key_signal:
        event_rewards[1, 0, 0] = 1.0
    auxiliary_advantages = torch.zeros(time_steps, batch, 2)
    auxiliary_advantages[:, 0, 0] = torch.tensor([0.0, 2.0, 8.0, 9.0])
    return CausalCreditRollout(
        observations=observations,
        previous_actions=torch.zeros(time_steps, batch, dtype=torch.long),
        previous_rewards=torch.zeros(time_steps, batch),
        actions=torch.zeros(time_steps, batch, dtype=torch.long),
        old_log_probabilities=torch.zeros(time_steps, batch),
        terminal_rewards=torch.zeros(time_steps, batch),
        event_rewards=event_rewards,
        dones=torch.tensor([[False], [False], [False], [True]]),
        episode_starts=torch.tensor([[True], [False], [False], [False]]),
        phases=phases,
        next_phases=torch.tensor([[0], [1], [2], [0]], dtype=torch.long),
        old_goal_values=torch.zeros(time_steps, batch),
        old_auxiliary_values=torch.zeros(time_steps, batch, 2),
        goal_advantages=torch.tensor([[1.0], [2.0], [3.0], [4.0]]),
        goal_returns=torch.zeros(time_steps, batch),
        auxiliary_advantages=auxiliary_advantages,
        auxiliary_returns=torch.zeros(time_steps, batch, 2),
        initial_hidden=torch.zeros(batch, 16),
    )


def test_phase_address_uses_functional_state_bits():
    observations = torch.zeros(4, 13)
    observations[1, 9] = 1.0
    observations[2, 11] = 1.0
    observations[3, 9] = 1.0
    observations[3, 11] = 1.0
    assert phase_from_observations(observations).tolist() == [0, 1, 2, 2]


def test_guarded_standardize_is_exactly_null_without_signal():
    values = torch.tensor([1.0, 3.0, 99.0])
    mask = torch.tensor([True, True, False])
    assert torch.equal(
        guarded_standardize(values, mask, False), torch.zeros_like(values)
    )
    active = guarded_standardize(values, mask, True)
    assert torch.allclose(active, torch.tensor([-1.0, 1.0, 0.0]))


def test_phase_actor_uses_only_signalled_matching_phase():
    rollout = _synthetic_rollout(key_signal=True)
    phase_actor, signals = actor_advantage_for_arm(rollout, "phase_actor")
    assert signals == {"key": True, "door": False, "goal": False}
    assert torch.allclose(
        phase_actor[:, 0], torch.tensor([-1.0, 1.0, 0.0, 0.0])
    )
    auxiliary_control, _ = actor_advantage_for_arm(
        rollout, "aux_critic_only"
    )
    assert torch.equal(auxiliary_control, torch.zeros_like(auxiliary_control))


@pytest.mark.parametrize("arm", ARMS)
def test_no_events_make_actor_advantage_exactly_zero(arm):
    rollout = _synthetic_rollout(key_signal=False)
    advantage, signals = actor_advantage_for_arm(rollout, arm)
    assert not any(signals.values())
    assert torch.equal(advantage, torch.zeros_like(advantage))


def test_all_arms_have_identical_base_birth_and_zero_auxiliary_heads():
    config = _small_config()
    descendants = [make_causal_credit_descendant(config, 12345) for _ in ARMS]
    digests = [causal_credit_digests(descendant) for descendant in descendants]
    assert len({row["actor_critic"] for row in digests}) == 1
    assert len({row["writer"] for row in digests}) == 1
    assert len({row["auxiliary_heads"] for row in digests}) == 1
    assert all(
        torch.count_nonzero(parameter).item() == 0
        for descendant in descendants
        for parameter in descendant.auxiliary_heads.parameters()
    )


@pytest.mark.parametrize("arm", ARMS)
def test_small_causal_credit_update_is_finite_and_guard_heads_are_dormant(arm):
    config = _small_config()
    descendant = make_causal_credit_descendant(config, 222)
    environments = DoorKeyVectorEnv(
        config.num_envs, 333, config.max_episode_steps, "terminal"
    )
    before_auxiliary = causal_credit_digests(descendant)["auxiliary_heads"]
    rollout, _ = collect_causal_credit_rollout(
        descendant, environments, config
    )
    assert rollout.event_rewards.shape == (
        config.rollout_steps,
        config.num_envs,
        3,
    )
    assert all(rollout_semantics(rollout).values())
    metrics = causal_credit_ppo_update(descendant, rollout, config, arm)
    numeric = [
        value
        for value in metrics.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    assert numeric and all(math.isfinite(float(value)) for value in numeric)
    if not any(metrics["actor_channel_signal"].values()):
        assert metrics["actor_advantage_nonzero"] is False
        assert metrics["policy_loss"] == 0.0
    if arm == "guarded_terminal":
        assert causal_credit_digests(descendant)["auxiliary_heads"] == before_auxiliary


def test_null_reference_gate_checks_hashes_and_guard_drift(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("frozen\n", encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")
    panel_path = tmp_path / "panel.json"
    panel_path.write_text(
        json.dumps(
            {
                "run_id": "doorkey_zero_reward_null_panel_v1_attempt1",
                "completed_cleanly": True,
                "completion_gates": {"terminal_reference_gate_passed": True},
                "terminal_reference_gate": {
                    "passes": True,
                    "gates": {
                        "reference_run_id_exact": TERMINAL_REFERENCE_RUN
                        == "doorkey_feedback_terminal_multiseed_v1_attempt1"
                    },
                },
                "arm_aggregates": [
                    {
                        "arm": "normalized_reference",
                        "absolute_entropy_change": {"mean": 0.4},
                        "early_action_total_variation": {"mean": 0.3},
                    },
                    {
                        "arm": "actor_guard",
                        "absolute_entropy_change": {"mean": 0.001},
                        "early_action_total_variation": {"mean": 0.002},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": "doorkey_zero_reward_null_panel_v1_attempt1",
                "input_sha256": {str(source): _sha256(source)},
            }
        ),
        encoding="utf-8",
    )
    output_hashes_path = tmp_path / "output_hashes.sha256"
    output_hashes_path.write_text(
        f"{_sha256(artifact)}  {artifact}\n", encoding="utf-8"
    )
    qualified = qualify_null_reference(
        panel_path, manifest_path, output_hashes_path
    )
    assert qualified["passes"], qualified
    source.write_text("changed\n", encoding="utf-8")
    failed = qualify_null_reference(
        panel_path, manifest_path, output_hashes_path
    )
    assert not failed["passes"]
    assert not failed["gates"]["all_null_inputs_verify"]


def test_complete_small_guarded_arm(tmp_path, monkeypatch):
    import laws_confirmation.doorkey_phase_value_credit as phase_credit

    config = _small_config()
    monkeypatch.setattr(phase_credit, "UPDATES", 10)
    monkeypatch.setattr(
        phase_credit,
        "EXPECTED_STEPS",
        10 * config.num_envs * config.rollout_steps,
    )
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    result = _train_arm(
        "guarded_terminal", config, tmp_path, output_dir
    )
    assert result["completed_cleanly"], result["completion_gates"]
    assert result["environment_steps"] == 320
    assert len(result["evaluations"]) == 4
    assert result["initial_state"]["digests"]["auxiliary_heads"] == result[
        "final_state"
    ]["digests"]["auxiliary_heads"]
