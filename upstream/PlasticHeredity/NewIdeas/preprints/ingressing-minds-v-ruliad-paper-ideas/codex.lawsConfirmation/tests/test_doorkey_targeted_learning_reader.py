from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
import torch

from laws_confirmation import doorkey_vertical_multifounder as source_confirmation
from laws_confirmation import doorkey_vertical_scout as frozen_vertical
from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_carrier import (
    carrier_digest,
    empty_germ,
    read_germ,
    write_germ_from_local_evidence,
)
from laws_confirmation.doorkey_counterfactual_gradient import counterfactual_deltas
from laws_confirmation.doorkey_env import CAUSAL_CHAIN
from laws_confirmation.doorkey_matched_disposition import soma_environment_digests
from laws_confirmation.doorkey_phase_value_credit import (
    CausalCreditRollout,
    actor_advantage_for_arm,
)
from laws_confirmation.doorkey_ppo import DoorKeyVectorEnv
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig
from laws_confirmation.doorkey_targeted_learning_reader import (
    ACTIVE_ARMS,
    ARMS,
    FOUNDERS,
    GENERATION,
    NULL_ALIAS_ARMS,
    REGISTERED_CELLS,
    REGISTERED_TRANSITIONS,
    cell_specs,
    credit_mode_for_arm,
    exact_apparatus_audit,
    learning_carrier_for,
    registered_classification,
    seed_row,
    targeted_actor_advantage,
    targeted_ppo_update,
)


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
    phases = [0, 0, 0, 0, 1, 1, 1, 1]
    starts = [True, False, False, False, False, False, False, False]
    actions = [0, 4, 0, 4, 5, 0, 5, 5]
    steps = len(phases)
    events = torch.zeros((steps, 1, 3), dtype=torch.float32)
    events[3, 0, 0] = 1.0
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
        num_envs=2,
        rollout_steps=16,
        ppo_epochs=1,
        minibatch_envs=1,
        max_episode_steps=16,
    )


def test_registry_seeds_size_and_action_blind_modes_are_frozen():
    assert seed_row(1) == {"birth": 220_100_000, "training": 230_100_000}
    assert seed_row(3) == {"birth": 220_300_000, "training": 230_300_000}
    assert len(ARMS) == 5
    assert len(ACTIVE_ARMS) == 2
    assert len(NULL_ALIAS_ARMS) == 3
    assert REGISTERED_CELLS == 15
    assert REGISTERED_TRANSITIONS == 6_144_000
    assert GENERATION == 4
    assert credit_mode_for_arm("target_trace_correct") == "target_trace"
    assert credit_mode_for_arm("event_only_correct") == "event_only"
    assert credit_mode_for_arm("target_trace_reader_off") == "off"
    with pytest.raises(ValueError):
        seed_row(0)


def test_target_and_event_rules_match_frozen_gradient_candidates_exactly():
    rollout = _rollout()
    carrier = _correct_carrier()
    base, _ = actor_advantage_for_arm(rollout, "phase_actor")
    target, _, target_audit = targeted_actor_advantage(
        rollout,
        carrier,
        "target_trace",
    )
    event, _, event_audit = targeted_actor_advantage(
        rollout,
        carrier,
        "event_only",
    )
    key_deltas, _ = counterfactual_deltas(rollout, carrier, 0)
    door_deltas, _ = counterfactual_deltas(rollout, carrier, 1)
    assert torch.equal(
        target - base,
        key_deltas["trace_target_only"] + door_deltas["trace_target_only"],
    )
    assert torch.equal(
        event - base,
        key_deltas["event_only_reference"]
        + door_deltas["event_only_reference"],
    )
    assert target_audit["credited_steps"] == 5
    assert event_audit["credited_steps"] == 2
    assert target_audit["available_extra_predecessor_steps"] == 3
    assert torch.count_nonzero((target - base)[rollout.actions == 0]) == 0


def test_wrong_empty_and_reader_off_are_exact_null_advantages():
    rollout = _rollout()
    correct = _correct_carrier()
    wrong = np.asarray(
        source_confirmation.initial_carriers(correct)["wrong_frozen"],
        dtype=np.uint8,
    )
    base, _ = actor_advantage_for_arm(rollout, "phase_actor")
    for carrier, mode in (
        (wrong, "target_trace"),
        (empty_germ(1), "target_trace"),
        (None, "off"),
    ):
        result, _, audit = targeted_actor_advantage(rollout, carrier, mode)
        assert torch.equal(result, base)
        assert audit["credited_steps"] == 0
        assert not audit["differs_from_base"]


def test_reader_off_ppo_update_is_exact_frozen_null_and_rejects_action_reading():
    config = _small_config()
    carrier = _correct_carrier()
    left = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(carrier),
        config,
        333,
    )
    right = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(carrier),
        config,
        333,
    )
    left_env = DoorKeyVectorEnv(2, 444, 16, "terminal")
    right_env = DoorKeyVectorEnv(2, 444, 16, "terminal")
    left_rollout, left_completed = frozen_vertical.collect_vertical_rollout(
        left,
        left_env,
        config,
        "blind",
    )
    right_rollout, right_completed = frozen_vertical.collect_vertical_rollout(
        right,
        right_env,
        config,
        "blind",
    )
    assert left_completed == right_completed
    left_metrics = targeted_ppo_update(
        left,
        left_rollout,
        config,
        learning_carrier=None,
        credit_mode="off",
        germ_mode="blind",
    )
    right_metrics = frozen_vertical.vertical_phase_ppo_update(
        right,
        right_rollout,
        config,
        "blind",
    )
    for name, value in right_metrics.items():
        assert left_metrics[name] == value
    assert (
        soma_environment_digests(left, left_env)["aggregate"]
        == soma_environment_digests(right, right_env)["aggregate"]
    )
    with pytest.raises(ValueError, match="blind action path"):
        targeted_ppo_update(
            left,
            left_rollout,
            config,
            learning_carrier=carrier,
            credit_mode="target_trace",
            germ_mode="direct_prior",
        )


def test_cell_specs_use_only_frozen_packets_and_new_seed_namespaces():
    correct = _correct_carrier()
    source = {
        "parents": [
            {
                "founder": founder,
                "outgoing_carrier": correct.tolist(),
                "outgoing_carrier_sha256": carrier_digest(correct),
                "checkpoint": f"/source/founder_{founder}.pt",
                "checkpoint_sha256": f"checkpoint-{founder}",
                "source_result": f"/source/founder_{founder}.json",
                "source_result_sha256": f"result-{founder}",
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
        assert rows["target_trace_correct"]["birth_seed"] == seed_row(founder)[
            "birth"
        ]
        assert read_germ(
            np.asarray(rows["target_trace_wrong"]["incoming_germ"], dtype=np.uint8)
        ).prior_logits.argmax(axis=-1)[0, [1, 3]].tolist() == [5, 4]
        assert not read_germ(
            np.asarray(rows["learning_silence"]["incoming_germ"], dtype=np.uint8)
        ).active.any()
        incoming = np.asarray(
            rows["target_trace_reader_off"]["incoming_germ"],
            dtype=np.uint8,
        )
        assert learning_carrier_for("target_trace_reader_off", incoming) is None


def _auc(value: float) -> dict[str, object]:
    return {
        "fixed_random": {
            "events": {
                event: {"reached_fraction_auc": value} for event in CAUSAL_CHAIN
            }
        }
    }


def _synthetic_result(founder: int, arm: str) -> dict[str, object]:
    token = {
        "target_trace_correct": "target",
        "event_only_correct": "event",
        "target_trace_wrong": "null",
        "target_trace_reader_off": "null",
        "learning_silence": "null",
    }[arm]
    score = {"target": 0.3, "event": 0.2, "null": 0.1}[token]
    history = [
        {
            "update": update,
            "post_update_soma_environment_sha256": f"{token}-{update}",
            "credit_mode": credit_mode_for_arm(arm),
            "germ_mode": "blind",
            "credit_audit": {"arm": arm},
        }
        for update in range(1, 101)
    ]
    return {
        "founder": founder,
        "arm": arm,
        "birth_evaluation_sha256": "birth",
        "birth_soma_environment_digests": {"aggregate": "birth-state"},
        "first_rollout_sha256": "first-rollout",
        "first_completed_episode_rows_sha256": "first-completed",
        "first_pre_update_soma_environment_digests": {"aggregate": "first-state"},
        "history": history,
        "behavior_fingerprint": token,
        "final_soma_environment_digests": {"aggregate": token},
        "cumulative_credited_steps": {
            "key": 1 if token in {"target", "event"} else 0,
            "door": 1 if token in {"target", "event"} else 0,
        },
        "first_credit_update": 1 if token in {"target", "event"} else None,
        "first_extra_predecessor_update": 1 if token == "target" else None,
        "learning_auc": _auc(score),
    }


def test_exact_apparatus_and_three_registered_classifications():
    results = [
        _synthetic_result(founder, arm) for founder in FOUNDERS for arm in ARMS
    ]
    apparatus = exact_apparatus_audit(deepcopy(results))
    assert apparatus["passes"]
    outcome = registered_classification(results, apparatus)
    assert outcome["labels"] == {
        "target_trace": "TARGET_TRACE_BENEFIT_3_OF_3",
        "event_only": "EVENT_ONLY_BENEFIT_3_OF_3",
        "predecessor_credit": "PREDECESSOR_CREDIT_BENEFIT_3_OF_3",
    }

    broken = deepcopy(results)
    next(
        row
        for row in broken
        if row["founder"] == 2 and row["arm"] == "target_trace_wrong"
    )["behavior_fingerprint"] = "different"
    broken_apparatus = exact_apparatus_audit(broken)
    assert not broken_apparatus["passes"]
    assert set(
        registered_classification(broken, broken_apparatus)["labels"].values()
    ) == {"TARGETED_READER_APPARATUS_INVALID"}
