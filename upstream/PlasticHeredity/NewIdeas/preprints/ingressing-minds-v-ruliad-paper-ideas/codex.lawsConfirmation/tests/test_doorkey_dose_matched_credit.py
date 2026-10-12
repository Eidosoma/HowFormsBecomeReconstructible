from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
import torch

from laws_confirmation.doorkey_carrier import empty_germ, write_germ_from_local_evidence
from laws_confirmation.doorkey_boundary import make_boundary_packet
from laws_confirmation.doorkey_dose_matched_credit import (
    BETAS,
    CANDIDATES,
    MAX_WORKERS,
    REGISTERED_TRANSITIONS,
    candidate_support_metrics,
    dose_matched_deltas,
    gradient_snapshot,
    mechanical_admissibility,
)
from laws_confirmation.doorkey_env import DoorKeyEnv
from laws_confirmation.doorkey_phase_value_credit import CausalCreditRollout
from laws_confirmation.doorkey_ppo_v2 import FeedbackPPOConfig
from laws_confirmation import doorkey_vertical_scout as frozen_vertical


def _carrier() -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    evidence[0, 1, 4] = 10.0
    evidence[0, 3, 5] = 10.0
    carrier, committed = write_germ_from_local_evidence(
        evidence,
        empty_germ(1),
        confirmation_mask=np.asarray([[False, True, False, True]]),
    )
    assert committed[0, [1, 3]].all()
    return carrier


def _rollout() -> CausalCreditRollout:
    # Key-phase PICKUP attempts occur once with no visible key (context 0),
    # once with a visible key (context 1), then at the confirming event.
    steps = 7
    observations = torch.zeros((steps, 1, 13), dtype=torch.float32)
    observations[2, 0, 0] = float(DoorKeyEnv.KEY)
    observations[3, 0, 0] = float(DoorKeyEnv.KEY)
    observations[4:, 0, 9] = 1.0
    observations[5:, 0, 0] = float(DoorKeyEnv.DOOR_CLOSED)
    actions = torch.tensor([0, 4, 4, 4, 5, 5, 5], dtype=torch.long)[:, None]
    phases = torch.tensor([0, 0, 0, 0, 1, 1, 1], dtype=torch.long)[:, None]
    events = torch.zeros((steps, 1, 3), dtype=torch.float32)
    events[3, 0, 0] = 1.0
    events[6, 0, 1] = 1.0
    zeros = torch.zeros((steps, 1), dtype=torch.float32)
    return CausalCreditRollout(
        observations=observations,
        previous_actions=torch.zeros((steps, 1), dtype=torch.long),
        previous_rewards=zeros.clone(),
        actions=actions,
        old_log_probabilities=zeros.clone(),
        terminal_rewards=zeros.clone(),
        event_rewards=events,
        dones=torch.zeros((steps, 1), dtype=torch.bool),
        episode_starts=torch.tensor(
            [True, False, False, False, False, False, False], dtype=torch.bool
        )[:, None],
        phases=phases,
        next_phases=phases.clone(),
        old_goal_values=zeros.clone(),
        old_auxiliary_values=torch.zeros((steps, 1, 2)),
        goal_advantages=zeros.clone(),
        goal_returns=zeros.clone(),
        auxiliary_advantages=torch.zeros((steps, 1, 2)),
        auxiliary_returns=torch.zeros((steps, 1, 2)),
        initial_hidden=torch.zeros((1, 8)),
    )


def test_frozen_registry_has_nine_fixed_mass_candidates_and_three_workers():
    assert BETAS == (0.25, 0.50, 0.75, 1.00)
    assert CANDIDATES == (
        "event_only",
        "unrestricted_beta_025",
        "unrestricted_beta_050",
        "unrestricted_beta_075",
        "unrestricted_beta_100",
        "addressed_beta_025",
        "addressed_beta_050",
        "addressed_beta_075",
        "addressed_beta_100",
    )
    assert MAX_WORKERS == 3
    assert REGISTERED_TRANSITIONS == 1_228_800


def test_dose_is_conserved_and_address_filter_removes_direct_context_leak():
    deltas, audit = dose_matched_deltas(_rollout(), _carrier(), 0)
    for candidate in CANDIDATES:
        metrics = candidate_support_metrics(deltas[candidate], audit)
        assert metrics["total_positive_mass"] == pytest.approx(1.0)
        assert metrics["absolute_conservation_error"] <= 1e-7
        assert metrics["minimum_delta"] >= 0.0
    unrestricted = candidate_support_metrics(
        deltas["unrestricted_beta_100"], audit
    )
    addressed = candidate_support_metrics(deltas["addressed_beta_100"], audit)
    assert unrestricted["context_mass"]["no_key_visible"] == pytest.approx(0.5)
    assert unrestricted["off_address_fraction"] == pytest.approx(0.5)
    assert addressed["context_mass"]["no_key_visible"] == 0.0
    assert addressed["off_address_fraction"] == 0.0
    assert addressed["context_mass"]["key_visible"] == pytest.approx(1.0)


def test_no_predecessor_falls_back_to_the_event_without_losing_dose():
    rollout = _rollout()
    rollout.actions[:3, 0] = 0
    deltas, audit = dose_matched_deltas(rollout, _carrier(), 0)
    assert torch.equal(deltas["event_only"], deltas["addressed_beta_100"])
    assert torch.equal(deltas["event_only"], deltas["unrestricted_beta_100"])
    assert float(deltas["event_only"].sum()) == pytest.approx(1.0)
    assert audit["events_with_addressed_predecessor"] == 0


def test_gradient_and_context_probe_is_finite_and_read_only():
    config = FeedbackPPOConfig(
        tile_embedding_size=2,
        hidden_size=8,
        action_embedding_size=2,
        num_envs=1,
        rollout_steps=7,
        ppo_epochs=1,
        minibatch_envs=1,
        max_episode_steps=7,
    )
    carrier = _carrier()
    descendant = frozen_vertical.make_vertical_descendant(
        make_boundary_packet(carrier), config, 12345
    )
    snapshot = gradient_snapshot(descendant, _rollout(), config, carrier)
    assert snapshot["diagnostic_state_exact"]
    for channel in ("key", "door"):
        for candidate in CANDIDATES:
            assert snapshot["channels"][channel]["gradient_geometry"][candidate][
                "finite"
            ]
            assert snapshot["channels"][channel]["context_probability_response"][
                candidate
            ]


def _synthetic_result(founder: int) -> dict:
    support = {}
    gradient = {}
    for channel in ("key", "door"):
        support[channel] = {"candidates": {}}
        gradient[channel] = {"candidates": {}}
        for candidate in CANDIDATES:
            addressed = candidate.startswith("addressed_")
            support[channel]["candidates"][candidate] = {
                "maximum_absolute_conservation_error": 0.0,
                "off_address_fraction": 0.0 if addressed or candidate == "event_only" else 0.5,
                "predecessor_mass": 0.0 if candidate == "event_only" else 1.0,
            }
            beta = 0.0 if candidate == "event_only" else int(candidate[-3:]) / 100.0
            gradient[channel]["candidates"][candidate] = {
                "concatenated_cosine": 1.0,
                "gradient_norm_ratio": 1.0,
                "context_response": {
                    "desired_response_sum": 1.0,
                    "spill_response_sum": 0.1,
                    "positive_spill_to_desired_ratio": 0.1 + (0.0 if addressed else beta),
                },
            }
    return {"founder": founder, "support_aggregate": support, "gradient_aggregate": gradient}


def test_decision_prefers_largest_addressed_beta_when_spill_is_not_worse():
    results = [_synthetic_result(founder) for founder in (1, 2, 3)]
    decision = mechanical_admissibility(results)
    assert decision["recommendations"]["key"]["candidate"] == "addressed_beta_100"
    assert decision["recommendations"]["door"]["candidate"] == "addressed_beta_100"
    broken = deepcopy(results)
    for result in broken:
        result["gradient_aggregate"]["key"]["candidates"]["addressed_beta_100"][
            "context_response"
        ]["positive_spill_to_desired_ratio"] = 0.2
    decision = mechanical_admissibility(broken)
    assert decision["recommendations"]["key"]["candidate"] == "addressed_beta_075"
