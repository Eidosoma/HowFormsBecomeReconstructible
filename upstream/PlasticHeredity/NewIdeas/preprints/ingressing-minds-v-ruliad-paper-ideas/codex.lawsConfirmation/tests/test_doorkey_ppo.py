import inspect

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import GermSchema, empty_germ
from laws_confirmation.doorkey_ppo import (
    DoorKeyVectorEnv,
    PPOConfig,
    RecurrentDoorKeyActorCritic,
    audit_real_ppo_boundary,
    birth_ppo_descendant,
    collect_rollout,
    evaluate_policy,
    make_empty_ppo_descendant,
    ppo_update,
    prime_ppo_parent_for_boundary_audit,
    train_ppo,
)


def _small_config() -> PPOConfig:
    return PPOConfig(
        hidden_size=16,
        tile_embedding_size=4,
        num_envs=4,
        rollout_steps=16,
        ppo_epochs=1,
        minibatch_envs=2,
        max_episode_steps=32,
    )


def test_recurrent_model_shapes_and_episode_reset_mask():
    config = _small_config()
    model = RecurrentDoorKeyActorCritic(config)
    observations = torch.zeros((5, 4, 13), dtype=torch.float32)
    initial = torch.ones((4, config.hidden_size), dtype=torch.float32)
    starts = torch.zeros((5, 4), dtype=torch.bool)
    starts[0] = True
    starts[3, 2] = True
    logits, values, final_hidden = model.forward_sequence(
        observations, initial, starts
    )
    assert logits.shape == (5, 4, 8)
    assert values.shape == (5, 4)
    assert final_hidden.shape == (4, config.hidden_size)
    assert torch.isfinite(logits).all()
    assert torch.isfinite(values).all()


def test_birth_is_deterministic_and_has_no_parent_argument():
    config = _small_config()
    packet = make_boundary_packet(empty_germ(1, GermSchema()))
    first = birth_ppo_descendant(packet, config, 81)
    second = birth_ppo_descendant(packet, config, 81)
    third = birth_ppo_descendant(packet, config, 82)
    for left, right in zip(first.model.parameters(), second.model.parameters()):
        assert torch.equal(left, right)
    assert any(
        not torch.equal(left, right)
        for left, right in zip(first.model.parameters(), third.model.parameters())
    )
    assert tuple(inspect.signature(birth_ppo_descendant).parameters) == (
        "packet",
        "config",
        "birth_seed",
        "device",
    )
    assert bytes(first.germ[0]) == packet.payload


def test_actual_ppo_state_is_destroyed_at_boundary():
    config = _small_config()
    parent = make_empty_ppo_descendant(config, 91)
    prime_ppo_parent_for_boundary_audit(parent, 19.0)
    packet = make_boundary_packet(parent.germ)
    child = birth_ppo_descendant(packet, config, 92)
    audit = audit_real_ppo_boundary(parent, child, packet)
    assert audit["passes"], audit
    assert audit["state_rows"]["ppo_optimizer"]["parent_tensor_count"] > 0
    assert audit["state_rows"]["ppo_optimizer"]["child_tensor_count"] == 0
    assert audit["state_rows"]["normalization_state"]["status"] == "absent_by_design"


def test_rollout_and_ppo_update_are_finite_and_change_parameters():
    config = _small_config()
    descendant = make_empty_ppo_descendant(config, 101)
    environments = DoorKeyVectorEnv(
        config.num_envs,
        base_seed=5000,
        max_steps=config.max_episode_steps,
        reward_mode="stage_shaped",
    )
    before = [parameter.detach().clone() for parameter in descendant.model.parameters()]
    rollout, completed = collect_rollout(
        descendant, environments, config, germ_mode="blind"
    )
    assert rollout.observations.shape == (16, 4, 13)
    assert rollout.actions.shape == (16, 4)
    assert rollout.advantages.shape == (16, 4)
    assert torch.isfinite(rollout.advantages).all()
    metrics = ppo_update(descendant, rollout, config, germ_mode="blind")
    assert all(np.isfinite(value) for value in metrics.values())
    assert any(
        not torch.equal(old, new)
        for old, new in zip(before, descendant.model.parameters())
    )
    assert isinstance(completed, list)


def test_short_training_and_common_world_evaluation_execute():
    config = _small_config()
    descendant = make_empty_ppo_descendant(config, 111)
    result = train_ppo(
        descendant,
        config,
        updates=2,
        training_seed=7000,
        reward_mode="stage_shaped",
        germ_mode="blind",
        evaluation_every=1,
        evaluation_worlds_per_transform=1,
    )
    assert result["environment_steps"] == 2 * 4 * 16
    assert len(result["history"]) == 2
    assert len(result["evaluations"]) == 2
    evaluation = evaluate_policy(
        descendant,
        config,
        germ_mode="blind",
        worlds_per_transform=1,
    )
    assert evaluation["world_count"] == 4
    assert len(evaluation["conditional_chain"]) == 6
    assert len(evaluation["world_rows"]) == 4

