import math
from dataclasses import asdict

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import empty_germ, read_germ
from laws_confirmation.doorkey_causal_writer import (
    CausalWriterLedger,
    renew_germ_from_causal_evidence,
)
from laws_confirmation.doorkey_env import Action, CAUSAL_CHAIN
from laws_confirmation.doorkey_feedback_scout import _atomic_torch_save
from laws_confirmation.doorkey_phase_value_credit import causal_credit_digests
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv
from laws_confirmation.doorkey_ppo_v2 import (
    FeedbackPPOConfig,
    START_ACTION,
    _apply_prior,
)
from laws_confirmation.doorkey_vertical_scout import (
    ARMS,
    audit_vertical_boundary,
    behavior_fingerprint,
    collect_vertical_rollout,
    exact_alias_audit,
    initial_carriers,
    learning_auc,
    make_vertical_descendant,
    rollout_payload,
    run_descendant_writer,
    vertical_phase_ppo_update,
)
import laws_confirmation.doorkey_vertical_scout as vertical_module


def _small_config() -> FeedbackPPOConfig:
    return FeedbackPPOConfig(
        num_envs=4,
        rollout_steps=8,
        minibatch_envs=2,
        ppo_epochs=1,
        max_episode_steps=32,
        hidden_size=16,
        tile_embedding_size=4,
        action_embedding_size=4,
    )


def _pickup_germ() -> np.ndarray:
    ledger = CausalWriterLedger.empty()
    ledger.effect_action_counts[1, Action.PICKUP] = 10
    ledger.context_action_counts[1, Action.PICKUP] = 10
    ledger.birth_probability_sums[1] = 10 / 8
    ledger.final_probability_sums[1, Action.PICKUP] = 10
    ledger.transition_count = 10
    return renew_germ_from_causal_evidence(ledger, empty_germ(1)).germ


def test_vertical_birth_accepts_and_expresses_arbitrary_packet():
    config = _small_config()
    germ = _pickup_germ()
    descendant = make_vertical_descendant(make_boundary_packet(germ), config, 123)
    assert np.array_equal(descendant.learner.germ, germ)
    assert descendant.learner.rollout_state is None
    assert not torch.count_nonzero(descendant.learner.recurrent_hidden)
    assert torch.all(descendant.learner.previous_actions == START_ACTION)
    observation = torch.zeros((1, 13), dtype=torch.float32)
    observation[0, 4] = 2  # key tile in the egocentric center
    base = torch.zeros((1, 8), dtype=torch.float32)
    direct, active = _apply_prior(base, descendant.learner, observation, "direct_prior")
    blind, blind_active = _apply_prior(base, descendant.learner, observation, "blind")
    assert active.item()
    assert direct.argmax(dim=-1).item() == int(Action.PICKUP)
    assert torch.equal(blind, base)
    assert not blind_active.item()


def test_small_vertical_rollout_and_phase_update_are_finite():
    config = _small_config()
    descendant = make_vertical_descendant(
        make_boundary_packet(_pickup_germ()), config, 222
    )
    environments = DoorKeyVectorEnv(
        config.num_envs, 333, config.max_episode_steps, "terminal"
    )
    rollout, _ = collect_vertical_rollout(
        descendant, environments, config, "direct_prior"
    )
    before = causal_credit_digests(descendant)["actor_critic"]
    metrics = vertical_phase_ppo_update(descendant, rollout, config, "direct_prior")
    assert all(
        math.isfinite(float(value))
        for value in metrics.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    assert causal_credit_digests(descendant)["actor_critic"] != before
    assert set(rollout_payload(rollout)) == set(vars(rollout))


def test_blind_carrier_and_effectively_empty_reader_are_exact_learning_aliases():
    config = _small_config()
    active = make_vertical_descendant(make_boundary_packet(_pickup_germ()), config, 444)
    silent = make_vertical_descendant(make_boundary_packet(empty_germ(1)), config, 444)
    active_env = DoorKeyVectorEnv(
        config.num_envs, 445, config.max_episode_steps, "terminal"
    )
    silent_env = DoorKeyVectorEnv(
        config.num_envs, 445, config.max_episode_steps, "terminal"
    )
    active_rollout, active_completed = collect_vertical_rollout(
        active, active_env, config, "blind"
    )
    silent_rollout, silent_completed = collect_vertical_rollout(
        silent, silent_env, config, "direct_prior"
    )
    assert active_completed == silent_completed
    assert all(
        torch.equal(getattr(active_rollout, name), getattr(silent_rollout, name))
        for name in vars(active_rollout)
    )
    active_metrics = vertical_phase_ppo_update(active, active_rollout, config, "blind")
    silent_metrics = vertical_phase_ppo_update(
        silent, silent_rollout, config, "direct_prior"
    )
    assert active_metrics == silent_metrics
    assert causal_credit_digests(active) == causal_credit_digests(silent)


def test_small_descendant_writer_is_read_only_valid_and_replayable():
    config = _small_config()
    descendant = make_vertical_descendant(
        make_boundary_packet(_pickup_germ()), config, 555
    )
    before = causal_credit_digests(descendant)
    result = run_descendant_writer(
        descendant,
        config,
        germ_mode="direct_prior",
        birth_seed=555,
        layout_seed=8_600_000,
        action_seed=8_700_000,
    )
    assert result["passes"], result["gates"]
    assert causal_credit_digests(descendant) == before
    assert np.asarray(result["candidate_carrier"], dtype=np.uint8).nbytes == 64


def test_actual_checkpoint_boundary_resets_every_applicable_state(tmp_path):
    config = _small_config()
    germ = _pickup_germ()
    parent = make_vertical_descendant(make_boundary_packet(germ), config, 100)
    parent.learner.optimizer.zero_grad(set_to_none=True)
    sum(
        parameter.square().mean()
        for parameter in (
            *parent.learner.model.parameters(),
            *parent.auxiliary_heads.parameters(),
        )
    ).backward()
    parent.learner.optimizer.step()
    with torch.no_grad():
        for parameter in parent.auxiliary_heads.parameters():
            parameter.fill_(0.25)
    parent.learner.recurrent_hidden.fill_(0.5)
    parent.learner.previous_actions.fill_(2)
    parent.learner.previous_rewards.fill_(0.5)
    parent.learner.numpy_rng.random(17)
    torch.rand(17, generator=parent.learner.torch_generator)
    checkpoint = tmp_path / "parent.pt"
    _atomic_torch_save(
        checkpoint,
        {
            "config": asdict(config),
            "birth_seed": 100,
            "germ": germ,
            "model_state_dict": parent.learner.model.state_dict(),
            "auxiliary_heads_state_dict": parent.auxiliary_heads.state_dict(),
            "writer_state_dict": parent.learner.writer.state_dict(),
            "optimizer_state_dict": parent.learner.optimizer.state_dict(),
            "writer_optimizer_state_dict": parent.learner.writer_optimizer.state_dict(),
            "recurrent_hidden": parent.learner.recurrent_hidden,
            "previous_actions": parent.learner.previous_actions,
            "previous_rewards": parent.learner.previous_rewards,
            "rollout_state": {"probe": torch.ones(1)},
            "numpy_rng_state": parent.learner.numpy_rng.bit_generator.state,
            "torch_generator_state": parent.learner.torch_generator.get_state(),
        },
    )
    packet = make_boundary_packet(germ)
    child = make_vertical_descendant(packet, config, 101)
    audit = audit_vertical_boundary(checkpoint, child, packet, generation=2)
    assert audit["passes"], audit


def _evaluation(update: int, mode: str, reached: int) -> dict:
    chain = []
    eligible = 10
    for event in CAUSAL_CHAIN:
        chain.append(
            {
                "from": "episode_start",
                "to": event,
                "eligible": eligible,
                "reached": reached,
                "conditional_probability": reached / eligible if eligible else None,
            }
        )
        eligible = reached
    return {
        "update": update,
        "germ_mode": "direct_prior",
        "feedback_reward_mode": "terminal",
        "action_mode": mode,
        "world_count": 10,
        "successes": reached,
        "conditional_chain": chain,
    }


def test_learning_auc_and_alias_audit_are_threshold_free():
    evaluations = [
        _evaluation(update, "fixed_random", update // 10)
        for update in range(0, 101, 10)
    ]
    auc = learning_auc(evaluations, "fixed_random")
    assert auc["terminal_success_fraction_auc"] == pytest.approx(0.5)
    assert auc["events"][CAUSAL_CHAIN[-1]]["reached_fraction_auc"] == pytest.approx(0.5)
    results = [
        {"generation": generation, "arm": arm, "behavior_fingerprint": "same"}
        for generation in (1, 2, 3)
        for arm in ARMS
    ]
    assert exact_alias_audit(results)["passes"]


def test_control_carriers_have_the_registered_semantics():
    founder = _pickup_germ()
    carriers = initial_carriers(founder)
    assert np.array_equal(carriers["rewrite"], founder)
    assert not read_germ(carriers["silence"]).active.any()
    assert not read_germ(carriers["lesion_rewrite"]).active[0, 1]
    assert not read_germ(carriers["lesion_rewrite"]).checksum_valid[0, 1]
    assert carriers["wrong_frozen"].shape == (1, 64)


def test_behavior_fingerprint_ignores_reader_label_not_behavior():
    base = {
        "history": [{"x": 1}],
        "evaluations": [{"germ_mode": "direct_prior", "x": 2}],
        "final_evaluations": {"fixed_random": {"germ_mode": "direct_prior", "x": 3}},
        "final_world_rows": {"fixed_random": [{"x": 4}]},
        "episodes_completed": 5,
        "training_goal_successes": 0,
        "cumulative_event_counts": {"key": 1, "door": 0, "goal": 0},
        "first_signal_update": {"key": 1, "door": None, "goal": None},
        "first_evaluation_reach": {"fixed_random": {}},
        "final_state": {"digest": "x"},
        "rollout_semantics": {"ok": True},
    }
    changed = {**base}
    changed["evaluations"] = [{"germ_mode": "blind", "x": 2}]
    changed["final_evaluations"] = {"fixed_random": {"germ_mode": "blind", "x": 3}}
    assert behavior_fingerprint(base) == behavior_fingerprint(changed)


def test_ten_update_cell_smoke_covers_checkpoint_and_result_pipeline(
    tmp_path, monkeypatch
):
    config = FeedbackPPOConfig(
        num_envs=8,
        rollout_steps=32,
        minibatch_envs=4,
        ppo_epochs=1,
        max_episode_steps=64,
        hidden_size=16,
        tile_embedding_size=4,
        action_embedding_size=4,
    )
    germ = _pickup_germ()
    parent = make_vertical_descendant(make_boundary_packet(germ), config, 700)
    parent.learner.optimizer.zero_grad(set_to_none=True)
    sum(
        parameter.square().mean()
        for parameter in (
            *parent.learner.model.parameters(),
            *parent.auxiliary_heads.parameters(),
        )
    ).backward()
    parent.learner.optimizer.step()
    with torch.no_grad():
        for parameter in parent.auxiliary_heads.parameters():
            parameter.fill_(0.25)
    parent.learner.recurrent_hidden.fill_(0.5)
    parent.learner.previous_actions.fill_(2)
    parent.learner.previous_rewards.fill_(0.5)
    parent.learner.numpy_rng.random(17)
    torch.rand(17, generator=parent.learner.torch_generator)
    parent_checkpoint = tmp_path / "founder.pt"
    _atomic_torch_save(
        parent_checkpoint,
        {
            "config": asdict(config),
            "birth_seed": 700,
            "germ": germ,
            "model_state_dict": parent.learner.model.state_dict(),
            "auxiliary_heads_state_dict": parent.auxiliary_heads.state_dict(),
            "writer_state_dict": parent.learner.writer.state_dict(),
            "optimizer_state_dict": parent.learner.optimizer.state_dict(),
            "writer_optimizer_state_dict": parent.learner.writer_optimizer.state_dict(),
            "recurrent_hidden": parent.learner.recurrent_hidden,
            "previous_actions": parent.learner.previous_actions,
            "previous_rewards": parent.learner.previous_rewards,
            "numpy_rng_state": parent.learner.numpy_rng.bit_generator.state,
            "torch_generator_state": parent.learner.torch_generator.get_state(),
        },
    )
    monkeypatch.setattr(vertical_module, "UPDATES", 10)
    monkeypatch.setattr(
        vertical_module, "EXPECTED_STEPS", config.num_envs * config.rollout_steps * 10
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = vertical_module._train_cell(
        {
            "generation": 1,
            "arm": "writer_off",
            "birth_seed": 701,
            "training_seed": 702,
            "writer_layout_seed": 703,
            "writer_action_seed": 704,
            "germ_mode": "direct_prior",
            "writer_enabled": False,
            "schedule_mode": "incoming",
            "incoming_germ": germ.tolist(),
            "parent_checkpoint": str(parent_checkpoint),
        },
        config,
        tmp_path,
        output_dir,
    )
    assert result["completed_cleanly"], result["completion_gates"]
    assert result["boundary_audit"]["passes"]
    assert result["writer"]["enabled"] is False
    assert (output_dir / "g1_writer_off.json").is_file()
    assert (output_dir / "g1_writer_off_checkpoint.pt").is_file()
