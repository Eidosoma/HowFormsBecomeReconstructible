from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
import torch

from laws_confirmation import doorkey_vertical_scout as vertical
from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import empty_germ, write_germ_from_local_evidence
from laws_confirmation.doorkey_consequence_predictor import (
    ARMS,
    BUFFER_ROLLOUTS,
    MAX_WORKERS,
    SNAPSHOTS,
    ConsequenceReader,
    TransitionRecorder,
    centered_scores,
    evaluate_panel,
    intervention_row,
    make_panel,
    make_readers,
    observation_features,
    prequential_rows,
    qualification,
    roc_auc,
    score_metrics,
)
from laws_confirmation.doorkey_env import Action, DoorKeyEnv, make_layout, oracle_plan
from laws_confirmation.doorkey_matched_disposition import (
    deep_digest,
    soma_environment_digests,
)
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig
from laws_confirmation.doorkey_targeted_learning_reader import targeted_ppo_update


def _packet() -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    evidence[0, 1, 4] = 10.0
    evidence[0, 3, 5] = 10.0
    packet, _ = write_germ_from_local_evidence(
        evidence,
        empty_germ(1),
        confirmation_mask=np.asarray([[False, True, False, True]]),
    )
    return packet


def _examples() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    # Synthetic transition examples test routing and gradients, not performance.
    observations = torch.zeros((64, 13))
    observations[:, 4] = DoorKeyEnv.AGENT
    observations[0:16, 10] = 1
    observations[32:, 9] = 1
    observations[32:48, 1] = DoorKeyEnv.DOOR_CLOSED
    actions = torch.tensor([4] * 32 + [5] * 32)
    outcomes = torch.zeros((64, 2))
    outcomes[0:16, 0] = 1
    outcomes[32:48, 1] = 1
    return observations, actions, outcomes


def test_registry_and_feature_encoding_are_frozen():
    assert ARMS == ("correct", "wrong", "empty", "reader_off", "shuffled")
    assert MAX_WORKERS == 3
    assert BUFFER_ROLLOUTS == 8
    assert SNAPSHOTS == (0, 10, 20, 40, 60, 80, 100)
    obs, _, _ = _examples()
    assert observation_features(obs).shape == (64, 76)
    assert torch.equal(observation_features(obs)[:, :72].sum(1), torch.full((64,), 9.0))
    obs[0, 0] = 0.5
    with pytest.raises(ValueError, match="integral"):
        observation_features(obs)
    with pytest.raises(ValueError, match="64-byte"):
        ConsequenceReader(np.zeros((1, 65), np.uint8), 1, "correct")


def test_birth_is_action_constant_and_does_not_consume_global_randomness():
    before = torch.get_rng_state().clone()
    readers = make_readers(_packet(), 9)
    assert torch.equal(before, torch.get_rng_state())
    observations, _, _ = _examples()
    policy = torch.softmax(torch.arange(8).float().repeat(64, 1), -1)
    for reader in readers.values():
        assert torch.equal(reader.scores(observations), torch.full((64, 2, 8), 0.5))
        assert not torch.count_nonzero(reader.credit_table(observations, policy))
        assert not reader.optimizer.state
        assert not reader.buffer
    assert len({deep_digest(r.model.state_dict()) for r in readers.values()}) == 1


def test_constant_centering_is_exact_and_general_centering_is_policy_zero():
    policy = torch.softmax(torch.arange(8).float().repeat(7, 1), -1)
    assert not torch.count_nonzero(centered_scores(torch.full((7, 8), 0.37), policy))
    scores = torch.arange(56).reshape(7, 8).float() / 56
    centered = centered_scores(scores, policy)
    assert float((centered * policy).sum(-1).abs().max()) < 1e-7
    assert torch.allclose(centered_scores(scores + 3, policy), centered, atol=4e-7)


def test_reader_off_matches_learning_empty_is_noop_and_wrong_unconfirmed():
    readers = make_readers(_packet(), 91)
    empty_before = readers["empty"].digest()
    examples = _examples()
    global_before = torch.get_rng_state().clone()
    for _ in range(2):
        for reader in readers.values():
            result = reader.fit(*examples)
            assert result["label_counts_preserved"]
    assert torch.equal(global_before, torch.get_rng_state())
    assert readers["correct"].digest() == readers["reader_off"].digest()
    assert readers["empty"].digest() == empty_before
    assert readers["wrong"].positive_counts == [0, 0]
    assert readers["correct"].positive_counts == [32, 32]
    assert readers["shuffled"].positive_counts == [32, 32]
    assert readers["correct"].digest() != readers["shuffled"].digest()
    policy = torch.full((64, 8), 0.125)
    for arm in ("wrong", "empty", "reader_off"):
        assert not torch.count_nonzero(readers[arm].credit_table(examples[0], policy))
    credit = readers["correct"].credit_table(examples[0], policy)
    assert torch.count_nonzero(credit) > 0
    assert float((credit * policy[:, None]).sum(-1).abs().max()) < 1e-6
    assert not torch.count_nonzero(credit[:32, 1])
    assert not torch.count_nonzero(credit[32:, 0])
    assert all(
        parameter.grad is None for parameter in readers["correct"].model.parameters()
    )


def test_replay_buffer_is_bounded_and_preserves_old_shuffled_labels():
    reader = make_readers(_packet(), 51)["shuffled"]
    examples = _examples()
    reader.fit(*examples)
    retained = reader.buffer[0][2].clone()
    reader.fit(*examples)
    assert torch.equal(retained, reader.buffer[0][2])
    for _ in range(BUFFER_ROLLOUTS):
        reader.fit(*examples)
    assert len(reader.buffer) == BUFFER_ROLLOUTS
    for _, _, labels in reader.buffer:
        assert labels.sum(0).tolist() == [16.0, 16.0]


def test_intervention_labels_are_real_and_do_not_mutate_environment():
    environment = DoorKeyEnv(make_layout(343), max_steps=128)
    plan = oracle_plan(environment.layout)
    while plan[0] != Action.PICKUP:
        environment.step(plan.pop(0))
    before = deep_digest(environment)
    observation, labels, _ = intervention_row(environment)
    assert observation[10] == 1
    assert labels.sum() == 1
    assert labels[0, Action.PICKUP] == 1
    assert before == deep_digest(environment)
    environment.step(Action.PICKUP)
    environment.step(Action.DROP)
    _, labels, _ = intervention_row(environment)
    # Raw reacquisition stays positive even when first-acquisition reward is spent.
    assert labels[0, Action.PICKUP] == 1
    environment.step(Action.PICKUP)
    plan.pop(0)
    while plan[0] != Action.OPEN:
        environment.step(plan.pop(0))
    _, labels, _ = intervention_row(environment)
    assert labels.sum() == 1
    assert labels[1, Action.OPEN] == 1


def test_recorder_preserves_rollouts_ppo_states_and_completed_episode_resets():
    config = FeedbackPPOConfig(
        hidden_size=8,
        tile_embedding_size=2,
        action_embedding_size=2,
        num_envs=2,
        rollout_steps=8,
        minibatch_envs=1,
        ppo_epochs=1,
        max_episode_steps=4,
    )
    packet = _packet()
    left = vertical.make_vertical_descendant(make_boundary_packet(packet), config, 301)
    right = vertical.make_vertical_descendant(make_boundary_packet(packet), config, 301)
    env_left = DoorKeyVectorEnv(2, 501, 4, "terminal")
    env_right = DoorKeyVectorEnv(2, 501, 4, "terminal")
    recorder = TransitionRecorder(env_right)
    plain, completed_left = vertical.collect_vertical_rollout(
        left, env_left, config, "blind"
    )
    recorded, completed_right = vertical.collect_vertical_rollout(
        right, recorder, config, "blind"
    )
    assert deep_digest(vars(plain)) == deep_digest(vars(recorded))
    assert deep_digest(completed_left) == deep_digest(completed_right)
    outcomes = recorder.take_outcomes()
    assert outcomes.shape == (8, 2, 2)
    assert recorder.outcomes == []
    assert recorded.episode_starts[4].all()
    before = soma_environment_digests(right, env_right)
    reader = ConsequenceReader(packet, 21, "correct")
    reader.fit(recorded.observations, recorded.actions, outcomes)
    assert before == soma_environment_digests(right, env_right)
    left_metrics = targeted_ppo_update(
        left,
        plain,
        config,
        learning_carrier=packet,
        credit_mode="event_only",
        germ_mode="blind",
    )
    right_metrics = targeted_ppo_update(
        right,
        recorded,
        config,
        learning_carrier=packet,
        credit_mode="event_only",
        germ_mode="blind",
    )
    assert left_metrics == right_metrics
    assert soma_environment_digests(left, env_left) == soma_environment_digests(
        right, env_right
    )


def test_rank_auc_ties_and_imbalance_do_not_hide_within_action_failure():
    labels = np.array([0, 1, 0, 1])
    assert roc_auc(labels, np.array([0.1, 0.9, 0.1, 0.9])) == 1.0
    assert roc_auc(labels, np.ones(4)) == 0.5
    assert roc_auc(labels, np.array([0.9, 0.1, 0.9, 0.1])) == 0.0
    assert roc_auc(np.zeros(4), np.ones(4)) is None
    metrics = score_metrics(np.r_[1, np.zeros(99)], np.zeros(100))
    assert metrics["balanced_brier"] == 0.5


def test_panel_and_prequential_scoring_are_read_only_and_before_fit():
    reader = ConsequenceReader(_packet(), 82, "correct")
    panel = make_panel(299_000_000, worlds=1)
    assert panel["evaluation_only"] and panel["layout_count"] == 4
    before = reader.digest()
    panel_before = deep_digest(panel)
    metrics = evaluate_panel(reader, panel)
    for channel in ("key", "door"):
        assert metrics[channel]["target_action"]["roc_auc"] == 0.5
        assert metrics[channel]["target_action"]["balanced_brier"] == 0.25
        assert metrics[channel]["unique_correct_action_fraction"] == 0
    observations, actions, outcomes = _examples()
    pre = prequential_rows(reader, observations, actions, outcomes)
    assert pre["key"]["executed_target"]["positive_count"] == 16
    assert pre["key"]["executed_target"]["positive_score_sum"] == 8
    assert reader.digest() == before
    reader.fit(observations, actions, outcomes)
    assert pre["key"]["executed_target"]["positive_score_sum"] == 8
    assert deep_digest(panel) == panel_before


def test_qualification_requires_every_founder_channel_and_structural_pass():
    results = []
    for founder in (1, 2, 3):
        good = {
            "target_action": {"roc_auc": 0.99, "balanced_brier": 0.05},
            "unique_correct_action_fraction": 0.99,
        }
        shuffle = {"target_action": {"roc_auc": 0.5, "balanced_brier": 0.25}}
        results.append(
            {
                "founder": founder,
                "completed_cleanly": True,
                "snapshots": [
                    {
                        "arms": {
                            "correct": {"key": deepcopy(good), "door": deepcopy(good)},
                            "shuffled": {
                                "key": deepcopy(shuffle),
                                "door": deepcopy(shuffle),
                            },
                        }
                    }
                ],
                "training_counts": {
                    "correct": {"positive": [1, 1], "negative_target": [1, 1]}
                },
            }
        )
    assert qualification(results)["label"] == "PREDICTOR_QUALIFIED_3_OF_3"
    results[2]["snapshots"][-1]["arms"]["correct"]["door"]["target_action"][
        "roc_auc"
    ] = 0.89
    assert qualification(results)["label"] == "PREDICTOR_NOT_QUALIFIED_3_OF_3"
    results[2]["completed_cleanly"] = False
    assert qualification(results)["label"] == "INVALID_STRUCTURAL_FAILURE"
