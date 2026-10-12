from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
import torch

from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import (
    carrier_digest,
    empty_germ,
    permute_payloads,
    read_germ,
    write_germ_from_local_evidence,
)
from laws_confirmation.doorkey_env import CAUSAL_CHAIN
from laws_confirmation.doorkey_learning_only_reader import (
    ACTION_BLIND_ARMS,
    ARMS,
    CUTOFF_UPDATE,
    FOUNDERS,
    GENERATION,
    NULL_ALIAS_ARMS,
    REGISTERED_CELLS,
    action_germ_mode,
    causal_trace_gains,
    cell_specs,
    exact_apparatus_audit,
    learning_actor_advantage,
    learning_only_ppo_update,
    learning_packet_for,
    registered_classification,
    seed_row,
)
from laws_confirmation.doorkey_matched_disposition import (
    deep_digest,
    make_post_key_mask,
    soma_environment_digests,
)
from laws_confirmation.doorkey_phase_value_credit import (
    CausalCreditRollout,
    actor_advantage_for_arm,
)
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig
from laws_confirmation import doorkey_vertical_scout as frozen_vertical


def _correct_carrier() -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    evidence[0, 1, 4] = 10.0
    evidence[0, 3, 5] = 10.0
    confirmation = np.asarray([[False, True, False, True]])
    carrier, committed = write_germ_from_local_evidence(
        evidence,
        empty_germ(1),
        confirmation_mask=confirmation,
    )
    assert np.array_equal(committed, confirmation)
    assert read_germ(carrier).trust[0, [1, 3]].tolist() == [255, 255]
    return carrier


def _rollout(
    *,
    phases: list[int],
    starts: list[bool],
    actions: list[int],
    key_events: list[int] = [],
    door_events: list[int] = [],
) -> CausalCreditRollout:
    steps = len(phases)
    assert len(starts) == len(actions) == steps
    event_rewards = torch.zeros((steps, 1, 3), dtype=torch.float32)
    for index in key_events:
        event_rewards[index, 0, 0] = 1.0
    for index in door_events:
        event_rewards[index, 0, 1] = 1.0
    auxiliary_advantages = torch.tensor(
        [[[float(index + 1), float((index + 1) * 2)]] for index in range(steps)]
    )
    zeros = torch.zeros((steps, 1), dtype=torch.float32)
    return CausalCreditRollout(
        observations=torch.zeros((steps, 1, 13)),
        previous_actions=torch.zeros((steps, 1), dtype=torch.long),
        previous_rewards=zeros.clone(),
        actions=torch.tensor(actions, dtype=torch.long)[:, None],
        old_log_probabilities=zeros.clone(),
        terminal_rewards=zeros.clone(),
        event_rewards=event_rewards,
        dones=torch.zeros((steps, 1), dtype=torch.bool),
        episode_starts=torch.tensor(starts, dtype=torch.bool)[:, None],
        phases=torch.tensor(phases, dtype=torch.long)[:, None],
        next_phases=torch.tensor(phases, dtype=torch.long)[:, None],
        old_goal_values=zeros.clone(),
        old_auxiliary_values=torch.zeros((steps, 1, 2)),
        goal_advantages=torch.arange(steps, dtype=torch.float32)[:, None],
        goal_returns=zeros.clone(),
        auxiliary_advantages=auxiliary_advantages,
        auxiliary_returns=torch.zeros((steps, 1, 2)),
        initial_hidden=torch.zeros((1, 8)),
    )


def _small_config() -> FeedbackPPOConfig:
    return FeedbackPPOConfig(
        tile_embedding_size=2,
        hidden_size=8,
        action_embedding_size=2,
        num_envs=2,
        rollout_steps=16,
        ppo_epochs=1,
        minibatch_envs=1,
        max_episode_steps=16,
    )


def test_registry_seeds_and_action_separation_are_frozen():
    assert seed_row(1) == {"birth": 200_100_000, "training": 210_100_000}
    assert seed_row(3) == {"birth": 200_300_000, "training": 210_300_000}
    assert len(ARMS) == 8
    assert len(ACTION_BLIND_ARMS) == 7
    assert len(NULL_ALIAS_ARMS) == 3
    assert REGISTERED_CELLS == 24
    assert GENERATION == 4
    assert CUTOFF_UPDATE == 20
    assert action_germ_mode("direct_prior") == "direct_prior"
    assert all(action_germ_mode(arm) == "blind" for arm in ACTION_BLIND_ARMS)
    with pytest.raises(ValueError):
        seed_row(0)


def test_learning_packet_schedule_and_provenance():
    correct = _correct_carrier()
    empty = empty_germ(1)
    assert learning_packet_for(
        "learning_correct", 1, incoming=correct, correct_external=correct
    ) is not None
    assert np.array_equal(
        learning_packet_for(
            "learning_external", 1, incoming=empty, correct_external=correct
        ),
        correct,
    )
    assert learning_packet_for(
        "learning_reader_off", 1, incoming=correct, correct_external=correct
    ) is None
    assert learning_packet_for(
        "direct_prior", 1, incoming=correct, correct_external=correct
    ) is None
    assert learning_packet_for(
        "learning_delayed", 20, incoming=correct, correct_external=correct
    ) is None
    assert np.array_equal(
        learning_packet_for(
            "learning_delayed", 21, incoming=correct, correct_external=correct
        ),
        correct,
    )


def test_trace_gain_is_event_confirmed_and_stops_at_boundaries():
    carrier = _correct_carrier()
    rollout = _rollout(
        phases=[0, 0, 0, 0, 1, 1],
        starts=[True, False, True, False, False, False],
        actions=[0, 0, 0, 4, 0, 5],
        key_events=[3],
        door_events=[5],
    )
    gains, audit = causal_trace_gains(rollout, carrier)
    assert gains[:, 0, 0].tolist() == [1.0, 1.0, 2.0, 2.0, 1.0, 1.0]
    assert gains[:, 0, 1].tolist() == [1.0, 1.0, 1.0, 1.0, 2.0, 2.0]
    assert audit["confirmed_event_count"] == 2
    assert audit["boosted_trace_steps"] == 4
    assert audit["channels"]["key"]["gain"] == 2.0
    assert audit["channels"]["door"]["gain"] == 2.0


def test_no_event_and_wrong_action_are_exact_null_advantages():
    carrier = _correct_carrier()
    no_event = _rollout(
        phases=[0, 0, 1, 1],
        starts=[True, False, False, False],
        actions=[4, 4, 5, 5],
    )
    base, _ = actor_advantage_for_arm(no_event, "phase_actor")
    learned, _, audit = learning_actor_advantage(no_event, carrier)
    assert torch.equal(base, learned)
    assert not audit["differs_from_base"]

    wrong_action = _rollout(
        phases=[0, 0, 1, 1],
        starts=[True, False, False, False],
        actions=[0, 5, 0, 4],
        key_events=[1],
        door_events=[3],
    )
    base, _ = actor_advantage_for_arm(wrong_action, "phase_actor")
    learned, _, audit = learning_actor_advantage(wrong_action, carrier)
    assert torch.equal(base, learned)
    assert audit["confirmed_event_count"] == 0
    assert not audit["differs_from_base"]

    wrong_packet = permute_payloads(carrier, np.asarray([0, 3, 2, 1]))
    actual_events = _rollout(
        phases=[0, 0, 1, 1],
        starts=[True, False, False, False],
        actions=[0, 4, 0, 5],
        key_events=[1],
        door_events=[3],
    )
    base, _ = actor_advantage_for_arm(actual_events, "phase_actor")
    learned, _, audit = learning_actor_advantage(actual_events, wrong_packet)
    assert torch.equal(base, learned)
    assert audit["confirmed_event_count"] == 0


def test_learning_packet_is_rejected_with_action_reader():
    config = _small_config()
    carrier = _correct_carrier()
    descendant = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(carrier), config, 111
    )
    environments = DoorKeyVectorEnv(2, 222, 16, "terminal")
    rollout, _ = frozen_vertical.collect_vertical_rollout(
        descendant, environments, config, "blind"
    )
    with pytest.raises(ValueError, match="cannot coexist"):
        learning_only_ppo_update(
            descendant,
            rollout,
            config,
            learning_carrier=carrier,
            germ_mode="direct_prior",
        )


def test_inherited_and_external_learning_packets_update_exactly():
    config = _small_config()
    correct = _correct_carrier()
    inherited = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(correct), config, 333
    )
    external = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(empty_germ(1)), config, 333
    )
    inherited_env = DoorKeyVectorEnv(2, 444, 16, "terminal")
    external_env = DoorKeyVectorEnv(2, 444, 16, "terminal")
    left_rollout, left_completed = frozen_vertical.collect_vertical_rollout(
        inherited, inherited_env, config, "blind"
    )
    right_rollout, right_completed = frozen_vertical.collect_vertical_rollout(
        external, external_env, config, "blind"
    )
    assert deep_digest(vars(left_rollout)) == deep_digest(vars(right_rollout))
    assert deep_digest(left_completed) == deep_digest(right_completed)
    left_metrics = learning_only_ppo_update(
        inherited,
        left_rollout,
        config,
        learning_carrier=correct,
        germ_mode="blind",
    )
    right_metrics = learning_only_ppo_update(
        external,
        right_rollout,
        config,
        learning_carrier=correct,
        germ_mode="blind",
    )
    assert deep_digest(left_metrics) == deep_digest(right_metrics)
    assert (
        soma_environment_digests(inherited, inherited_env)["aggregate"]
        == soma_environment_digests(external, external_env)["aggregate"]
    )
    assert carrier_digest(external.learner.germ) == carrier_digest(empty_germ(1))


def test_cell_specs_use_only_registered_packets():
    correct = _correct_carrier()
    source = {
        "parents": [
            {
                "founder": founder,
                "outgoing_carrier": correct.tolist(),
                "outgoing_carrier_sha256": carrier_digest(correct),
                "checkpoint": f"/source/founder_{founder}.pt",
                "checkpoint_sha256": f"checkpoint-{founder}",
                "config": {"same": True},
            }
            for founder in FOUNDERS
        ]
    }
    specs = cell_specs(source)
    assert len(specs) == REGISTERED_CELLS
    assert {(row["founder"], row["arm"]) for row in specs} == {
        (founder, arm) for founder in FOUNDERS for arm in ARMS
    }
    for founder in FOUNDERS:
        rows = {row["arm"]: row for row in specs if row["founder"] == founder}
        assert not read_germ(
            np.asarray(rows["learning_external"]["incoming_germ"], dtype=np.uint8)
        ).active.any()
        assert not read_germ(
            np.asarray(rows["learning_silence"]["incoming_germ"], dtype=np.uint8)
        ).active.any()
        assert read_germ(
            np.asarray(rows["learning_wrong"]["incoming_germ"], dtype=np.uint8)
        ).prior_logits.argmax(axis=-1)[0, [1, 3]].tolist() == [5, 4]
        assert read_germ(
            np.asarray(rows["learning_post_key"]["incoming_germ"], dtype=np.uint8)
        ).active[0].tolist() == [False, False, False, True]
        assert np.array_equal(
            np.asarray(rows["learning_post_key"]["incoming_germ"], dtype=np.uint8),
            make_post_key_mask(correct),
        )


def _auc(value: float) -> dict:
    return {
        "fixed_random": {
            "events": {
                event: {"reached_fraction_auc": value} for event in CAUSAL_CHAIN
            }
        }
    }


def _synthetic_result(founder: int, arm: str) -> dict:
    token = {
        "learning_correct": "correct",
        "learning_external": "correct",
        "learning_wrong": "null",
        "learning_silence": "null",
        "learning_reader_off": "null",
        "learning_post_key": "post",
        "learning_delayed": "delayed",
        "direct_prior": "direct",
    }[arm]
    states = []
    for update in range(1, 101):
        if token == "correct":
            state = f"correct-{update}"
        elif token == "delayed" and update > 20:
            state = f"delayed-{update}"
        else:
            state = f"null-{update}"
        states.append(
            {
                "update": update,
                "post_update_soma_environment_sha256": state,
            }
        )
    score = {"correct": 0.2, "null": 0.1, "post": 0.15, "delayed": 0.16, "direct": 0.3}[token]
    early = "null-early" if token in {"null", "delayed"} else f"{token}-early"
    cutoff = "null-20" if token in {"null", "delayed"} else f"{token}-20"
    return {
        "founder": founder,
        "arm": arm,
        "birth_evaluation_sha256": "blind-birth" if arm != "direct_prior" else "direct-birth",
        "birth_soma_environment_digests": {"aggregate": "blind-soma"},
        "first_rollout_sha256": "blind-rollout" if arm != "direct_prior" else "direct-rollout",
        "first_completed_episode_rows_sha256": "blind-completed",
        "first_pre_update_soma_environment_digests": {"aggregate": "blind-pre"},
        "history": states,
        "first_confirmed_trace_update": 1 if token == "correct" else None,
        "early_behavior_sha256": early,
        "behavior_fingerprint": token,
        "cutoff_soma_environment_digests": {"aggregate": cutoff},
        "final_soma_environment_digests": {"aggregate": token},
        "learning_auc": _auc(score),
    }


def test_exact_apparatus_and_registered_classification():
    results = [
        _synthetic_result(founder, arm) for founder in FOUNDERS for arm in ARMS
    ]
    apparatus = exact_apparatus_audit(deepcopy(results))
    assert apparatus["passes"]
    outcome = registered_classification(results, apparatus)
    assert outcome["classification"] == "LEARNING_ONLY_BENEFIT_3_OF_3"
    assert outcome["all_three_correct_minus_wrong_positive"]
    assert outcome["direct_prior_excluded"]

    broken = deepcopy(results)
    next(
        row
        for row in broken
        if row["founder"] == 2 and row["arm"] == "learning_external"
    )["behavior_fingerprint"] = "different"
    broken_apparatus = exact_apparatus_audit(broken)
    assert not broken_apparatus["passes"]
    assert (
        registered_classification(broken, broken_apparatus)["classification"]
        == "LEARNING_ONLY_APPARATUS_INVALID"
    )
