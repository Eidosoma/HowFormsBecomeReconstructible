from __future__ import annotations

import numpy as np
import pytest
import torch

from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import empty_germ, write_germ_from_local_evidence
from laws_confirmation.doorkey_counterfactual_gradient import (
    CANDIDATES,
    GRADIENT_UPDATES,
    MAX_WORKERS,
    REGISTERED_TRANSITIONS,
    confirmed_trace_support,
    counterfactual_deltas,
    geometric_admissibility,
    gradient_geometry,
    policy_gradient_vector,
)
from laws_confirmation.doorkey_learning_only_reader import learning_actor_advantage
from laws_confirmation.doorkey_phase_value_credit import (
    CausalCreditRollout,
    actor_advantage_for_arm,
)
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
    return carrier


def _rollout() -> CausalCreditRollout:
    phases = [0, 0, 0, 0, 0, 1, 1, 1]
    starts = [True, False, True, False, False, False, False, False]
    actions = [0, 0, 0, 4, 4, 0, 5, 5]
    steps = len(phases)
    events = torch.zeros((steps, 1, 3), dtype=torch.float32)
    events[4, 0, 0] = 1.0
    events[7, 0, 1] = 1.0
    zeros = torch.zeros((steps, 1), dtype=torch.float32)
    auxiliary = torch.tensor(
        [[[float(index - 2), float(index + 1)]] for index in range(steps)],
        dtype=torch.float32,
    )
    return CausalCreditRollout(
        observations=torch.zeros((steps, 1, 13)),
        previous_actions=torch.zeros((steps, 1), dtype=torch.long),
        previous_rewards=zeros.clone(),
        actions=torch.tensor(actions, dtype=torch.long)[:, None],
        old_log_probabilities=zeros.clone(),
        terminal_rewards=zeros.clone(),
        event_rewards=events,
        dones=torch.zeros((steps, 1), dtype=torch.bool),
        episode_starts=torch.tensor(starts, dtype=torch.bool)[:, None],
        phases=torch.tensor(phases, dtype=torch.long)[:, None],
        next_phases=torch.tensor(phases, dtype=torch.long)[:, None],
        old_goal_values=zeros.clone(),
        old_auxiliary_values=torch.zeros((steps, 1, 2)),
        goal_advantages=zeros.clone(),
        goal_returns=zeros.clone(),
        auxiliary_advantages=auxiliary,
        auxiliary_returns=torch.zeros((steps, 1, 2)),
        initial_hidden=torch.zeros((1, 8)),
    )


def _small_config() -> FeedbackPPOConfig:
    return FeedbackPPOConfig(
        tile_embedding_size=2,
        hidden_size=8,
        action_embedding_size=2,
        num_envs=1,
        rollout_steps=8,
        ppo_epochs=1,
        minibatch_envs=1,
        max_episode_steps=8,
    )


def test_frozen_registry_has_six_rules_and_three_replays():
    assert CANDIDATES == (
        "prestandard_uniform_current",
        "poststandard_uniform",
        "event_only_reference",
        "trace_target_only",
        "positive_decay_short",
        "positive_decay_long",
    )
    assert GRADIENT_UPDATES == (1, 10, 20, 40, 60, 80, 100)
    assert MAX_WORKERS == 3
    assert REGISTERED_TRANSITIONS == 1_228_800


def test_confirmed_support_respects_episode_phase_and_frozen_decay():
    rollout = _rollout()
    carrier = _correct_carrier()
    key = confirmed_trace_support(rollout, carrier, 0)
    assert key["trace"][:, 0].tolist() == [False, False, True, True, True, False, False, False]
    assert key["target_trace"][:, 0].tolist() == [False, False, False, True, True, False, False, False]
    assert key["decay_short"][:, 0].tolist() == pytest.approx(
        [0, 0, 0.25, 0.5, 1, 0, 0, 0]
    )
    assert key["decay_long"][:, 0].tolist() == pytest.approx(
        [0, 0, 0.81, 0.9, 1, 0, 0, 0]
    )
    door = confirmed_trace_support(rollout, carrier, 1)
    assert door["trace"][:, 0].tolist() == [False, False, False, False, False, True, True, True]


def test_counterfactual_rules_match_v1_and_have_declared_support():
    rollout = _rollout()
    carrier = _correct_carrier()
    key, key_audit = counterfactual_deltas(rollout, carrier, 0)
    door, _ = counterfactual_deltas(rollout, carrier, 1)
    assert key["event_only_reference"][:, 0].tolist() == [0, 0, 0, 0, 1, 0, 0, 0]
    assert key["trace_target_only"][:, 0].tolist() == [0, 0, 0, 1, 1, 0, 0, 0]
    assert key["positive_decay_short"][:, 0].tolist() == pytest.approx(
        [0, 0, 0.25, 0.5, 1, 0, 0, 0]
    )
    assert key_audit["confirmed_event_count"] == 1
    base, _ = actor_advantage_for_arm(rollout, "phase_actor")
    v1, _, audit = learning_actor_advantage(rollout, carrier)
    assert audit["differs_from_base"]
    assert torch.equal(
        key["prestandard_uniform_current"]
        + door["prestandard_uniform_current"],
        v1 - base,
    )


def test_policy_gradient_measurement_is_finite_and_does_not_mutate_soma():
    config = _small_config()
    descendant = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(empty_germ(1)), config, 1234
    )
    rollout = _rollout()
    before = frozen_vertical.causal_credit_digests(descendant)
    deltas, _ = counterfactual_deltas(rollout, _correct_carrier(), 0)
    reference = policy_gradient_vector(
        descendant, rollout, config, deltas["event_only_reference"]
    )
    target = policy_gradient_vector(
        descendant, rollout, config, deltas["trace_target_only"]
    )
    after = frozen_vertical.causal_credit_digests(descendant)
    assert before == after
    geometry = gradient_geometry(reference, reference)
    assert geometry["gradient_norm"] > 0
    assert geometry["cosine"] == pytest.approx(1.0)
    assert gradient_geometry(target, reference)["finite"]


def _synthetic_founder(founder: int) -> dict:
    cosine = {
        "prestandard_uniform_current": -0.2,
        "poststandard_uniform": 0.2,
        "event_only_reference": 1.0,
        "trace_target_only": 0.8,
        "positive_decay_short": 0.7,
        "positive_decay_long": 0.3,
    }
    fraction = {
        "prestandard_uniform_current": 0.8,
        "poststandard_uniform": 0.5,
        "event_only_reference": 0.0,
        "trace_target_only": 0.0,
        "positive_decay_short": 0.2,
        "positive_decay_long": 0.6,
    }
    nonnegative = {candidate: candidate != "poststandard_uniform" for candidate in CANDIDATES}
    return {
        "founder": founder,
        "gradient_aggregate": {
            channel: {
                "candidates": {
                    candidate: {"concatenated_cosine": cosine[candidate]}
                    for candidate in CANDIDATES
                }
            }
            for channel in ("key", "door")
        },
        "support_aggregate": {
            channel: {
                "candidates": {
                    candidate: {
                        "non_target_absolute_fraction": fraction[candidate],
                        "all_confirming_event_deltas_nonnegative": nonnegative[
                            candidate
                        ],
                    }
                    for candidate in CANDIDATES
                }
            }
            for channel in ("key", "door")
        },
    }


def test_geometric_admissibility_prefers_targeted_predecessor_credit():
    decision = geometric_admissibility(
        [_synthetic_founder(founder) for founder in (1, 2, 3)]
    )
    assert decision["recommendations"]["key"]["candidate"] == "trace_target_only"
    assert decision["recommendations"]["door"]["candidate"] == "trace_target_only"
    assert not decision["behavioral_success_claimed"]
    current = [
        row
        for row in decision["candidate_decisions"]
        if row["candidate"] == "prestandard_uniform_current"
    ]
    assert all(row["classification"] == "NOT_GEOMETRICALLY_ADMISSIBLE" for row in current)
