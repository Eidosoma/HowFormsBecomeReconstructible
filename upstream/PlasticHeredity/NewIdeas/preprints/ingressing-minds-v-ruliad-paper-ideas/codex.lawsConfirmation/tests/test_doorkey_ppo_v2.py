import inspect

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import GermSchema, empty_germ
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv
from laws_confirmation.doorkey_ppo_v2 import (
    START_ACTION,
    FeedbackPPOConfig,
    FeedbackRecurrentActorCritic,
    audit_feedback_boundary,
    birth_feedback_ppo_descendant,
    collect_feedback_rollout,
    evaluate_feedback_policy,
    feedback_learner_digests,
    feedback_ppo_update,
    make_empty_feedback_descendant,
    prime_feedback_parent_for_boundary_audit,
    train_feedback_ppo,
)


def _small_config() -> FeedbackPPOConfig:
    return FeedbackPPOConfig(
        hidden_size=16,
        tile_embedding_size=4,
        action_embedding_size=4,
        num_envs=4,
        rollout_steps=16,
        ppo_epochs=1,
        minibatch_envs=2,
        max_episode_steps=32,
    )


def test_episode_birth_overrides_action_reward_and_hidden_feedback():
    config = _small_config()
    model = FeedbackRecurrentActorCritic(config)
    observations = torch.zeros((4, 13), dtype=torch.float32)
    hidden = torch.randn((4, config.hidden_size))
    starts = torch.ones(4, dtype=torch.bool)
    first = model.forward_step(
        observations,
        hidden,
        starts,
        torch.tensor([0, 1, 2, 3]),
        torch.tensor([1.0, -1.0, 0.5, 0.25]),
    )
    second = model.forward_step(
        observations,
        torch.zeros_like(hidden),
        starts,
        torch.full((4,), START_ACTION),
        torch.zeros(4),
    )
    for left, right in zip(first, second):
        assert torch.equal(left, right)

    continuing = torch.zeros(4, dtype=torch.bool)
    third = model.forward_step(
        observations,
        torch.zeros_like(hidden),
        continuing,
        torch.tensor([0, 1, 2, 3]),
        torch.tensor([1.0, -1.0, 0.5, 0.25]),
    )
    assert not torch.equal(second[0], third[0])


def test_feedback_birth_api_and_actual_reset_include_action_reward_state():
    config = _small_config()
    parent = make_empty_feedback_descendant(config, 1010)
    prime_feedback_parent_for_boundary_audit(parent, 17.0)
    packet = make_boundary_packet(parent.germ)
    child = birth_feedback_ppo_descendant(packet, config, 1011)
    audit = audit_feedback_boundary(parent, child, packet)
    assert audit["passes"], audit
    assert audit["state_rows"]["previous_action_state"]["reset"]
    assert audit["state_rows"]["previous_reward_state"]["reset"]
    assert tuple(inspect.signature(birth_feedback_ppo_descendant).parameters) == (
        "packet",
        "config",
        "birth_seed",
        "device",
    )


def test_rollout_carries_sampled_action_and_reward_into_next_transition():
    config = _small_config()
    descendant = make_empty_feedback_descendant(config, 1020)
    environments = DoorKeyVectorEnv(
        config.num_envs,
        base_seed=8000,
        max_steps=config.max_episode_steps,
        reward_mode="stage_shaped",
    )
    rollout, _ = collect_feedback_rollout(
        descendant, environments, config, germ_mode="blind"
    )
    assert rollout.previous_actions.shape == (16, 4)
    assert rollout.previous_rewards.shape == (16, 4)
    assert torch.all(rollout.previous_actions[0] == START_ACTION)
    assert torch.equal(rollout.previous_actions[1], rollout.actions[0])
    assert torch.equal(rollout.previous_rewards[1], rollout.rewards[0])
    assert torch.isfinite(rollout.advantages).all()

    before = [parameter.detach().clone() for parameter in descendant.model.parameters()]
    metrics = feedback_ppo_update(descendant, rollout, config, germ_mode="blind")
    assert all(np.isfinite(value) for value in metrics.values())
    assert any(
        not torch.equal(old, new)
        for old, new in zip(before, descendant.model.parameters())
    )


def test_fixed_random_evaluation_replays_exactly():
    config = _small_config()
    descendant = make_empty_feedback_descendant(config, 1030)
    first = evaluate_feedback_policy(
        descendant,
        config,
        germ_mode="blind",
        feedback_reward_mode="stage_shaped",
        action_mode="fixed_random",
        worlds_per_transform=1,
        action_seed=123,
        stochastic_repeats=2,
    )
    second = evaluate_feedback_policy(
        descendant,
        config,
        germ_mode="blind",
        feedback_reward_mode="stage_shaped",
        action_mode="fixed_random",
        worlds_per_transform=1,
        action_seed=123,
        stochastic_repeats=2,
    )
    assert first == second
    assert first["world_count"] == 8
    assert first["unique_layout_count"] == 4


def test_feedback_training_is_deterministic_and_finite():
    config = _small_config()

    def run_once():
        descendant = make_empty_feedback_descendant(config, 1040)
        before = feedback_learner_digests(descendant)
        result = train_feedback_ppo(
            descendant,
            config,
            updates=2,
            training_seed=9000,
            reward_mode="stage_shaped",
            germ_mode="blind",
            evaluation_every=1,
            evaluation_worlds_per_transform=1,
            stochastic_evaluation_repeats=2,
        )
        return result, before, feedback_learner_digests(descendant)

    first, before, first_after = run_once()
    second, _, second_after = run_once()
    assert first == second
    assert first_after == second_after
    assert before["actor_critic"] != first_after["actor_critic"]
    assert before["writer"] == first_after["writer"]
    assert len(first["evaluations"]) == 4

