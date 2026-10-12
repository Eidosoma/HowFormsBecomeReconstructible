"""Phase-gated key/door/goal value heads for the DoorKey causal chain."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import re
import time
import traceback
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
    _deepest_reached,
    _disk_preflight,
    _read_hash_manifest,
    _without_world_rows,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import (
    START_ACTION,
    FeedbackPPOConfig,
    FeedbackPPODescendant,
    _apply_prior,
    _module_digest,
    evaluate_feedback_policy,
    feedback_learner_digests,
    make_empty_feedback_descendant,
)
from .io import (
    atomic_json,
    atomic_text,
    canonical_digest,
    environment_manifest,
    external_root,
    git_head,
    sha256_file,
    utc_now,
    write_hash_manifest,
)


NULL_REFERENCE_RUN = "doorkey_zero_reward_null_panel_v1_attempt1"
ARMS = ("guarded_terminal", "aux_critic_only", "phase_actor")
CHANNELS = ("key", "door", "goal")
KEY_CHANNEL = 0
DOOR_CHANNEL = 1
GOAL_CHANNEL = 2
UPDATES = 100
BIRTH_SEED = 920_000
TRAINING_SEED = 930_000
EXPECTED_STEPS = 409_600
RUN_ID = "doorkey_phase_value_credit_scout_v1_attempt1"


class AuxiliaryValueHeads(nn.Module):
    """Zero-initialized key-acquisition and door-opening value heads."""

    def __init__(self, hidden_size: int) -> None:
        super().__init__()
        self.linear = nn.Linear(hidden_size, 2)
        nn.init.zeros_(self.linear.weight)
        nn.init.zeros_(self.linear.bias)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.linear(hidden)


@dataclass
class CausalCreditDescendant:
    learner: FeedbackPPODescendant
    auxiliary_heads: AuxiliaryValueHeads


@dataclass
class CausalCreditRollout:
    observations: torch.Tensor
    previous_actions: torch.Tensor
    previous_rewards: torch.Tensor
    actions: torch.Tensor
    old_log_probabilities: torch.Tensor
    terminal_rewards: torch.Tensor
    event_rewards: torch.Tensor
    dones: torch.Tensor
    episode_starts: torch.Tensor
    phases: torch.Tensor
    next_phases: torch.Tensor
    old_goal_values: torch.Tensor
    old_auxiliary_values: torch.Tensor
    goal_advantages: torch.Tensor
    goal_returns: torch.Tensor
    auxiliary_advantages: torch.Tensor
    auxiliary_returns: torch.Tensor
    initial_hidden: torch.Tensor


def make_causal_credit_descendant(
    config: FeedbackPPOConfig, birth_seed: int
) -> CausalCreditDescendant:
    learner = make_empty_feedback_descendant(config, birth_seed)
    heads = AuxiliaryValueHeads(config.hidden_size).to(
        next(learner.model.parameters()).device
    )
    learner.optimizer = torch.optim.Adam(
        [*learner.model.parameters(), *heads.parameters()],
        lr=config.learning_rate,
    )
    return CausalCreditDescendant(learner=learner, auxiliary_heads=heads)


def causal_credit_digests(descendant: CausalCreditDescendant) -> dict[str, str]:
    return {
        **feedback_learner_digests(descendant.learner),
        "auxiliary_heads": _module_digest(descendant.auxiliary_heads),
    }


def phase_from_observations(observations: torch.Tensor) -> torch.Tensor:
    if observations.ndim != 2 or observations.shape[1] != 13:
        raise ValueError("observations must have shape [batch, 13]")
    has_key = observations[:, 9] > 0.5
    door_open = observations[:, 11] > 0.5
    phases = torch.zeros(
        observations.shape[0], dtype=torch.long, device=observations.device
    )
    phases = torch.where(has_key, torch.ones_like(phases), phases)
    return torch.where(door_open, torch.full_like(phases, 2), phases)


def _forward_step_values(
    descendant: CausalCreditDescendant,
    observations: torch.Tensor,
    hidden: torch.Tensor,
    episode_starts: torch.Tensor,
    previous_actions: torch.Tensor,
    previous_rewards: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    logits, goal_value, next_hidden = descendant.learner.model.forward_step(
        observations,
        hidden,
        episode_starts,
        previous_actions,
        previous_rewards,
    )
    auxiliary_values = descendant.auxiliary_heads(next_hidden)
    return logits, goal_value, auxiliary_values, next_hidden


def _forward_sequence_values(
    descendant: CausalCreditDescendant,
    observations: torch.Tensor,
    initial_hidden: torch.Tensor,
    episode_starts: torch.Tensor,
    previous_actions: torch.Tensor,
    previous_rewards: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    hidden = initial_hidden
    logits: list[torch.Tensor] = []
    goal_values: list[torch.Tensor] = []
    auxiliary_values: list[torch.Tensor] = []
    for step in range(observations.shape[0]):
        step_logits, step_goal, step_auxiliary, hidden = _forward_step_values(
            descendant,
            observations[step],
            hidden,
            episode_starts[step],
            previous_actions[step],
            previous_rewards[step],
        )
        logits.append(step_logits)
        goal_values.append(step_goal)
        auxiliary_values.append(step_auxiliary)
    return (
        torch.stack(logits),
        torch.stack(goal_values),
        torch.stack(auxiliary_values),
    )


def _compute_goal_gae(
    rewards: torch.Tensor,
    dones: torch.Tensor,
    values: torch.Tensor,
    next_value: torch.Tensor,
    config: FeedbackPPOConfig,
) -> tuple[torch.Tensor, torch.Tensor]:
    advantages = torch.zeros_like(rewards)
    last_advantage = torch.zeros(config.num_envs, device=rewards.device)
    for step in reversed(range(config.rollout_steps)):
        nonterminal = (~dones[step]).to(torch.float32)
        following_value = (
            next_value if step == config.rollout_steps - 1 else values[step + 1]
        )
        delta = rewards[step] + config.gamma * following_value * nonterminal - values[step]
        last_advantage = (
            delta
            + config.gamma * config.gae_lambda * nonterminal * last_advantage
        )
        advantages[step] = last_advantage
    return advantages, advantages + values


def _compute_phase_gae(
    rewards: torch.Tensor,
    phases: torch.Tensor,
    next_phases: torch.Tensor,
    dones: torch.Tensor,
    values: torch.Tensor,
    next_values: torch.Tensor,
    config: FeedbackPPOConfig,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Option-terminated GAE for key and door channels."""

    advantages = torch.zeros_like(rewards)
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        last_advantage = torch.zeros(config.num_envs, device=rewards.device)
        for step in reversed(range(config.rollout_steps)):
            active = phases[step] == channel
            next_active = (next_phases[step] == channel) & (~dones[step])
            following_value = (
                next_values[:, channel]
                if step == config.rollout_steps - 1
                else values[step + 1, :, channel]
            )
            delta = (
                rewards[step, :, channel]
                + config.gamma
                * following_value
                * next_active.to(torch.float32)
                - values[step, :, channel]
            )
            last_advantage = torch.where(
                active,
                delta
                + config.gamma
                * config.gae_lambda
                * next_active.to(torch.float32)
                * last_advantage,
                torch.zeros_like(last_advantage),
            )
            advantages[step, :, channel] = last_advantage
    return advantages, advantages + values


def collect_causal_credit_rollout(
    descendant: CausalCreditDescendant,
    environments: DoorKeyVectorEnv,
    config: FeedbackPPOConfig,
) -> tuple[CausalCreditRollout, list[dict[str, Any]]]:
    learner = descendant.learner
    device = next(learner.model.parameters()).device
    observations_np = environments.observations()
    hidden = learner.recurrent_hidden.detach()
    previous_action = learner.previous_actions.detach()
    previous_reward = learner.previous_rewards.detach()
    initial_hidden = hidden.clone()
    episode_start_np = environments.episode_starts.copy()
    observations: list[torch.Tensor] = []
    previous_actions: list[torch.Tensor] = []
    previous_rewards: list[torch.Tensor] = []
    actions: list[torch.Tensor] = []
    log_probabilities: list[torch.Tensor] = []
    terminal_rewards: list[torch.Tensor] = []
    event_rewards: list[torch.Tensor] = []
    dones: list[torch.Tensor] = []
    episode_starts: list[torch.Tensor] = []
    phases: list[torch.Tensor] = []
    next_phases: list[torch.Tensor] = []
    goal_values: list[torch.Tensor] = []
    auxiliary_values: list[torch.Tensor] = []
    learner.model.eval()
    descendant.auxiliary_heads.eval()

    for _ in range(config.rollout_steps):
        observation = torch.from_numpy(observations_np).to(
            device=device, dtype=torch.float32
        )
        episode_start = torch.from_numpy(episode_start_np).to(device=device)
        phase = phase_from_observations(observation)
        with torch.no_grad():
            base_logits, goal_value, aux_value, next_hidden = _forward_step_values(
                descendant,
                observation,
                hidden,
                episode_start,
                previous_action,
                previous_reward,
            )
            logits, _ = _apply_prior(base_logits, learner, observation, "blind")
            log_probs = F.log_softmax(logits, dim=-1)
            probabilities = log_probs.exp()
            action = torch.multinomial(
                probabilities, 1, generator=learner.torch_generator
            ).squeeze(1)
            chosen_log_probability = log_probs.gather(1, action[:, None]).squeeze(1)
        next_observations_np, reward_np, done_np, infos = environments.step(
            action.detach().cpu().numpy()
        )
        reward = torch.from_numpy(reward_np).to(device)
        done = torch.from_numpy(done_np).to(device)
        channel_rewards_np = np.zeros((config.num_envs, 3), dtype=np.float32)
        for index, info in enumerate(infos):
            first_acquisition = bool(info["acquired"]) and (
                info["auxiliary_steps"]["key_acquired"] == info["step"]
            )
            channel_rewards_np[index, KEY_CHANNEL] = float(first_acquisition)
            channel_rewards_np[index, DOOR_CHANNEL] = float(bool(info["opened"]))
            channel_rewards_np[index, GOAL_CHANNEL] = float(reward_np[index])
        channel_reward = torch.from_numpy(channel_rewards_np).to(device)
        next_observation = torch.from_numpy(next_observations_np).to(
            device=device, dtype=torch.float32
        )

        observations.append(observation)
        previous_actions.append(previous_action)
        previous_rewards.append(previous_reward)
        actions.append(action)
        log_probabilities.append(chosen_log_probability)
        terminal_rewards.append(reward)
        event_rewards.append(channel_reward)
        dones.append(done)
        episode_starts.append(episode_start)
        phases.append(phase)
        next_phases.append(phase_from_observations(next_observation))
        goal_values.append(goal_value)
        auxiliary_values.append(aux_value)

        hidden = next_hidden.detach()
        hidden[done] = 0.0
        previous_action = action.detach().clone()
        previous_reward = reward.detach().clone()
        previous_action[done] = START_ACTION
        previous_reward[done] = 0.0
        observations_np = next_observations_np
        episode_start_np = done_np

    next_observation = torch.from_numpy(observations_np).to(
        device=device, dtype=torch.float32
    )
    next_episode_start = torch.from_numpy(episode_start_np).to(device=device)
    with torch.no_grad():
        _, next_goal_value, next_auxiliary_value, _ = _forward_step_values(
            descendant,
            next_observation,
            hidden,
            next_episode_start,
            previous_action,
            previous_reward,
        )
    terminal_reward_tensor = torch.stack(terminal_rewards)
    event_reward_tensor = torch.stack(event_rewards)
    done_tensor = torch.stack(dones)
    phase_tensor = torch.stack(phases)
    next_phase_tensor = torch.stack(next_phases)
    goal_value_tensor = torch.stack(goal_values)
    auxiliary_value_tensor = torch.stack(auxiliary_values)
    goal_advantages, goal_returns = _compute_goal_gae(
        terminal_reward_tensor,
        done_tensor,
        goal_value_tensor,
        next_goal_value,
        config,
    )
    auxiliary_rewards = event_reward_tensor[:, :, :2]
    auxiliary_advantages, auxiliary_returns = _compute_phase_gae(
        auxiliary_rewards,
        phase_tensor,
        next_phase_tensor,
        done_tensor,
        auxiliary_value_tensor,
        next_auxiliary_value,
        config,
    )
    batch = CausalCreditRollout(
        observations=torch.stack(observations),
        previous_actions=torch.stack(previous_actions),
        previous_rewards=torch.stack(previous_rewards),
        actions=torch.stack(actions),
        old_log_probabilities=torch.stack(log_probabilities),
        terminal_rewards=terminal_reward_tensor,
        event_rewards=event_reward_tensor,
        dones=done_tensor,
        episode_starts=torch.stack(episode_starts),
        phases=phase_tensor,
        next_phases=next_phase_tensor,
        old_goal_values=goal_value_tensor,
        old_auxiliary_values=auxiliary_value_tensor,
        goal_advantages=goal_advantages,
        goal_returns=goal_returns,
        auxiliary_advantages=auxiliary_advantages,
        auxiliary_returns=auxiliary_returns,
        initial_hidden=initial_hidden,
    )
    learner.recurrent_hidden = hidden
    learner.previous_actions = previous_action
    learner.previous_rewards = previous_reward
    learner.rollout_state = None
    return batch, environments.pop_completed()


def guarded_standardize(
    advantages: torch.Tensor,
    mask: torch.Tensor,
    signal_present: bool,
) -> torch.Tensor:
    """Standardize only real-evidence transitions; otherwise return exact zero."""

    if advantages.shape != mask.shape:
        raise ValueError("advantage and mask shapes differ")
    result = torch.zeros_like(advantages)
    if not signal_present or not bool(mask.any()):
        return result
    selected = advantages[mask]
    standardized = (selected - selected.mean()) / (
        selected.std(unbiased=False) + 1e-8
    )
    result[mask] = standardized
    return result


def actor_advantage_for_arm(
    rollout: CausalCreditRollout, arm: str
) -> tuple[torch.Tensor, dict[str, bool]]:
    if arm not in ARMS:
        raise ValueError(f"unknown causal-credit arm: {arm}")
    goal_signal = bool(torch.count_nonzero(rollout.event_rewards[:, :, 2]))
    signals = {
        "key": bool(torch.count_nonzero(rollout.event_rewards[:, :, 0])),
        "door": bool(torch.count_nonzero(rollout.event_rewards[:, :, 1])),
        "goal": goal_signal,
    }
    if arm in ("guarded_terminal", "aux_critic_only"):
        return (
            guarded_standardize(
                rollout.goal_advantages,
                torch.ones_like(rollout.goal_advantages, dtype=torch.bool),
                goal_signal,
            ),
            signals,
        )

    actor_advantage = torch.zeros_like(rollout.goal_advantages)
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        mask = rollout.phases == channel
        selected = guarded_standardize(
            rollout.auxiliary_advantages[:, :, channel],
            mask,
            signals[CHANNELS[channel]],
        )
        actor_advantage += selected
    goal_mask = rollout.phases == GOAL_CHANNEL
    actor_advantage += guarded_standardize(
        rollout.goal_advantages, goal_mask, goal_signal
    )
    return actor_advantage, signals


def _masked_mse(
    predicted: torch.Tensor, target: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    if predicted.shape != target.shape or predicted.shape != mask.shape:
        raise ValueError("masked MSE tensors have different shapes")
    if not bool(mask.any()):
        return predicted.sum() * 0.0
    return 0.5 * F.mse_loss(predicted[mask], target[mask])


def causal_credit_ppo_update(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    arm: str,
) -> dict[str, Any]:
    actor_advantage, signals = actor_advantage_for_arm(rollout, arm)
    descendant.learner.model.train()
    descendant.auxiliary_heads.train()
    collected: dict[str, list[float]] = {
        "policy_loss": [],
        "value_loss": [],
        "goal_value_loss": [],
        "key_value_loss": [],
        "door_value_loss": [],
        "entropy": [],
        "approx_kl": [],
        "clip_fraction": [],
        "grad_norm": [],
    }
    for _ in range(config.ppo_epochs):
        order = descendant.learner.numpy_rng.permutation(config.num_envs)
        for start in range(0, config.num_envs, config.minibatch_envs):
            indices = torch.as_tensor(
                order[start : start + config.minibatch_envs],
                dtype=torch.long,
                device=rollout.observations.device,
            )
            observations = rollout.observations[:, indices]
            logits, goal_values, auxiliary_values = _forward_sequence_values(
                descendant,
                observations,
                rollout.initial_hidden[indices],
                rollout.episode_starts[:, indices],
                rollout.previous_actions[:, indices],
                rollout.previous_rewards[:, indices],
            )
            flat_observations = observations.reshape(-1, config.observation_width)
            flat_logits, _ = _apply_prior(
                logits.reshape(-1, config.num_actions),
                descendant.learner,
                flat_observations,
                "blind",
            )
            log_probs = F.log_softmax(flat_logits, dim=-1)
            probabilities = log_probs.exp()
            actions = rollout.actions[:, indices].reshape(-1)
            new_log_probability = log_probs.gather(1, actions[:, None]).squeeze(1)
            old_log_probability = rollout.old_log_probabilities[:, indices].reshape(-1)
            advantage = actor_advantage[:, indices].reshape(-1)
            ratio = torch.exp(new_log_probability - old_log_probability)
            clipped_ratio = torch.clamp(
                ratio, 1.0 - config.clip_epsilon, 1.0 + config.clip_epsilon
            )
            policy_loss = -torch.minimum(
                ratio * advantage, clipped_ratio * advantage
            ).mean()
            goal_value_loss = 0.5 * F.mse_loss(
                goal_values.reshape(-1),
                rollout.goal_returns[:, indices].reshape(-1),
            )
            if arm == "guarded_terminal":
                key_value_loss = goal_values.sum() * 0.0
                door_value_loss = goal_values.sum() * 0.0
            else:
                phase = rollout.phases[:, indices]
                key_value_loss = _masked_mse(
                    auxiliary_values[:, :, KEY_CHANNEL],
                    rollout.auxiliary_returns[:, indices, KEY_CHANNEL],
                    phase == KEY_CHANNEL,
                )
                door_value_loss = _masked_mse(
                    auxiliary_values[:, :, DOOR_CHANNEL],
                    rollout.auxiliary_returns[:, indices, DOOR_CHANNEL],
                    phase == DOOR_CHANNEL,
                )
            value_loss = goal_value_loss + key_value_loss + door_value_loss
            entropy = -(probabilities * log_probs).sum(dim=-1).mean()
            loss = (
                policy_loss
                + config.value_coefficient * value_loss
                - config.entropy_coefficient * entropy
            )
            descendant.learner.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            grad_norm = nn.utils.clip_grad_norm_(
                [
                    *descendant.learner.model.parameters(),
                    *descendant.auxiliary_heads.parameters(),
                ],
                config.max_grad_norm,
            )
            descendant.learner.optimizer.step()
            with torch.no_grad():
                log_ratio = new_log_probability - old_log_probability
                approx_kl = ((torch.exp(log_ratio) - 1.0) - log_ratio).mean()
                clip_fraction = (
                    (torch.abs(ratio - 1.0) > config.clip_epsilon)
                    .to(torch.float32)
                    .mean()
                )
            for name, value in (
                ("policy_loss", policy_loss),
                ("value_loss", value_loss),
                ("goal_value_loss", goal_value_loss),
                ("key_value_loss", key_value_loss),
                ("door_value_loss", door_value_loss),
                ("entropy", entropy),
                ("approx_kl", approx_kl),
                ("clip_fraction", clip_fraction),
                ("grad_norm", grad_norm),
            ):
                collected[name].append(float(value.detach()))
    result: dict[str, Any] = {
        name: float(np.mean(values)) for name, values in collected.items()
    }
    result["actor_channel_signal"] = signals
    result["actor_advantage_nonzero"] = bool(torch.count_nonzero(actor_advantage))
    result["actor_advantage_nonzero_count"] = int(
        torch.count_nonzero(actor_advantage)
    )
    return result


def rollout_semantics(rollout: CausalCreditRollout) -> dict[str, bool]:
    key_events = rollout.event_rewards[:, :, KEY_CHANNEL] > 0
    door_events = rollout.event_rewards[:, :, DOOR_CHANNEL] > 0
    goal_events = rollout.event_rewards[:, :, GOAL_CHANNEL] > 0
    previous_reward_matches = True
    if rollout.terminal_rewards.shape[0] > 1:
        continuing = ~rollout.episode_starts[1:]
        previous_reward_matches = bool(
            torch.equal(
                rollout.previous_rewards[1:][continuing],
                rollout.terminal_rewards[:-1][continuing],
            )
        )
    at_episode_start = rollout.episode_starts
    event_counts_per_episode_are_bounded = True
    for env_index in range(rollout.terminal_rewards.shape[1]):
        counts = torch.zeros(3, dtype=torch.long)
        for step in range(rollout.terminal_rewards.shape[0]):
            if bool(rollout.episode_starts[step, env_index]):
                if bool(torch.any(counts > 1)):
                    event_counts_per_episode_are_bounded = False
                counts.zero_()
            counts += rollout.event_rewards[step, env_index].to(torch.long).cpu()
            if bool(rollout.dones[step, env_index]):
                if bool(torch.any(counts > 1)):
                    event_counts_per_episode_are_bounded = False
                counts.zero_()
        if bool(torch.any(counts > 1)):
            event_counts_per_episode_are_bounded = False
    return {
        "key_events_only_in_key_phase": bool(
            torch.all(rollout.phases[key_events] == KEY_CHANNEL)
        ),
        "door_events_only_in_door_phase": bool(
            torch.all(rollout.phases[door_events] == DOOR_CHANNEL)
        ),
        "goal_events_only_in_goal_phase": bool(
            torch.all(rollout.phases[goal_events] == GOAL_CHANNEL)
        ),
        "goal_channel_equals_terminal_reward": bool(
            torch.equal(
                rollout.event_rewards[:, :, GOAL_CHANNEL],
                rollout.terminal_rewards,
            )
        ),
        "previous_reward_is_terminal_only": previous_reward_matches,
        "feedback_zero_at_episode_start": bool(
            torch.count_nonzero(rollout.previous_rewards[at_episode_start]) == 0
        ),
        "events_are_binary": bool(
            torch.all(
                (rollout.event_rewards == 0.0)
                | (rollout.event_rewards == 1.0)
            )
        ),
        "at_most_one_event_per_channel_per_episode": (
            event_counts_per_episode_are_bounded
        ),
        "key_event_enters_door_phase": bool(
            torch.all(
                rollout.next_phases[key_events & ~rollout.dones]
                == DOOR_CHANNEL
            )
        ),
        "door_event_enters_goal_phase": bool(
            torch.all(
                rollout.next_phases[door_events & ~rollout.dones]
                == GOAL_CHANNEL
            )
        ),
        "goal_event_terminates_episode": bool(torch.all(rollout.dones[goal_events])),
    }


def qualify_null_reference(
    panel_path: Path,
    manifest_path: Path,
    output_hashes_path: Path,
) -> dict[str, Any]:
    """Verify the completed zero-reward diagnosis used as this scout's gate."""

    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    input_rows: list[dict[str, Any]] = []
    for path_text, expected in manifest.get("input_sha256", {}).items():
        path = Path(path_text)
        live = sha256_file(path) if path.is_file() else None
        input_rows.append(
            {
                "path": str(path),
                "expected_sha256": expected,
                "live_sha256": live,
                "matches": live == expected,
            }
        )
    output_rows = _read_hash_manifest(output_hashes_path)
    aggregates = {
        row["arm"]: row for row in panel.get("arm_aggregates", [])
    }
    normalized = aggregates.get("normalized_reference", {})
    guarded = aggregates.get("actor_guard", {})
    normalized_entropy = normalized.get("absolute_entropy_change", {}).get("mean")
    guarded_entropy = guarded.get("absolute_entropy_change", {}).get("mean")
    normalized_tv = normalized.get("early_action_total_variation", {}).get("mean")
    guarded_tv = guarded.get("early_action_total_variation", {}).get("mean")
    numeric_drift_present = all(
        isinstance(value, (int, float)) and math.isfinite(float(value))
        for value in (normalized_entropy, guarded_entropy, normalized_tv, guarded_tv)
    )
    entropy_ratio = (
        float(guarded_entropy) / float(normalized_entropy)
        if numeric_drift_present and float(normalized_entropy) > 0
        else None
    )
    action_tv_ratio = (
        float(guarded_tv) / float(normalized_tv)
        if numeric_drift_present and float(normalized_tv) > 0
        else None
    )
    panel_gates = panel.get("completion_gates", {})
    gates = {
        "null_run_id_exact": panel.get("run_id") == NULL_REFERENCE_RUN,
        "null_manifest_run_id_exact": manifest.get("run_id")
        == NULL_REFERENCE_RUN,
        "null_completed_cleanly": bool(panel.get("completed_cleanly")),
        "all_null_completion_gates_passed": bool(panel_gates)
        and all(bool(value) for value in panel_gates.values()),
        "all_null_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "all_null_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
        "guard_entropy_drift_below_normalized_reference": numeric_drift_present
        and float(guarded_entropy) < float(normalized_entropy),
        "guard_action_drift_below_normalized_reference": numeric_drift_present
        and float(guarded_tv) < float(normalized_tv),
        "terminal_reference_nested_gate_passed": bool(
            panel.get("terminal_reference_gate", {}).get("passes")
        ),
    }
    return {
        "gates": gates,
        "passes": all(gates.values()),
        "input_rows": input_rows,
        "output_rows": output_rows,
        "drift_evidence": {
            "normalized_mean_absolute_entropy_change": normalized_entropy,
            "actor_guard_mean_absolute_entropy_change": guarded_entropy,
            "actor_guard_to_normalized_entropy_ratio": entropy_ratio,
            "normalized_mean_early_action_tv": normalized_tv,
            "actor_guard_mean_early_action_tv": guarded_tv,
            "actor_guard_to_normalized_action_tv_ratio": action_tv_ratio,
        },
        "reference_digest": canonical_digest(panel),
    }


def _finite_credit_history(history: Sequence[Mapping[str, Any]]) -> bool:
    names = (
        "mean_rollout_terminal_reward",
        "max_rollout_terminal_reward",
        "policy_loss",
        "value_loss",
        "goal_value_loss",
        "key_value_loss",
        "door_value_loss",
        "entropy",
        "approx_kl",
        "clip_fraction",
        "grad_norm",
    )
    return bool(history) and all(
        math.isfinite(float(row[name])) for row in history for name in names
    )


def _evaluate(
    descendant: CausalCreditDescendant,
    config: FeedbackPPOConfig,
    mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return _without_world_rows(
        evaluate_feedback_policy(
            descendant.learner,
            config,
            germ_mode="blind",
            feedback_reward_mode="terminal",
            action_mode=mode,
            worlds_per_transform=8,
            stochastic_repeats=4,
        )
    )


def _module_birth_details(
    descendant: CausalCreditDescendant,
) -> dict[str, Any]:
    return {
        "digests": causal_credit_digests(descendant),
        "actor_head": _module_digest(descendant.learner.model.actor),
        "goal_critic": _module_digest(descendant.learner.model.critic),
        "auxiliary_heads_zero": all(
            torch.count_nonzero(parameter).item() == 0
            for parameter in descendant.auxiliary_heads.parameters()
        ),
    }


def _first_evaluation_reach(
    evaluations: Sequence[Mapping[str, Any]], mode: str
) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    relevant = sorted(
        (row for row in evaluations if row["action_mode"] == mode),
        key=lambda row: int(row["update"]),
    )
    event_order = [row["to"] for row in relevant[0]["conditional_chain"]]
    for event in event_order:
        hits = [
            int(row["update"])
            for row in relevant
            if next(
                item for item in row["conditional_chain"] if item["to"] == event
            )["reached"]
            > 0
        ]
        result[event] = min(hits) if hits else None
    return result


def _train_arm(
    arm: str,
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown causal-credit arm: {arm}")
    result_path = output_dir / f"{arm}.json"
    checkpoint_path = output_dir / f"{arm}_checkpoint.pt"
    if result_path.is_file() != checkpoint_path.is_file():
        raise RuntimeError(f"partial resumable artifacts for {arm}")
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("arm") != arm
            or result.get("birth_seed") != BIRTH_SEED
            or result.get("training_seed") != TRAINING_SEED
            or result.get("updates") != UPDATES
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable result for {arm}")
        print(f"{arm} already complete; resuming after it", flush=True)
        return result

    descendant = make_causal_credit_descendant(config, BIRTH_SEED)
    initial_germ = descendant.learner.germ.copy()
    initial_state = _module_birth_details(descendant)
    evaluations: list[dict[str, Any]] = []
    for mode in ACTION_MODES:
        evaluation, _ = _evaluate(descendant, config, mode)
        evaluation["update"] = 0
        evaluations.append(evaluation)

    environments = DoorKeyVectorEnv(
        config.num_envs,
        TRAINING_SEED,
        config.max_episode_steps,
        "terminal",
    )
    history: list[dict[str, Any]] = []
    total_episodes = 0
    total_successes = 0
    cumulative_events = {channel: 0 for channel in CHANNELS}
    first_signal_update: dict[str, int | None] = {
        channel: None for channel in CHANNELS
    }
    semantics_accumulator: dict[str, bool] = {}
    for update in range(1, UPDATES + 1):
        rollout, completed = collect_causal_credit_rollout(
            descendant, environments, config
        )
        semantics = rollout_semantics(rollout)
        for name, passed in semantics.items():
            semantics_accumulator[name] = semantics_accumulator.get(name, True) and passed
        event_counts = {
            channel: int(rollout.event_rewards[:, :, index].sum().item())
            for index, channel in enumerate(CHANNELS)
        }
        phase_counts = {
            channel: int(torch.count_nonzero(rollout.phases == index).item())
            for index, channel in enumerate(CHANNELS)
        }
        for channel in CHANNELS:
            cumulative_events[channel] += event_counts[channel]
            if event_counts[channel] and first_signal_update[channel] is None:
                first_signal_update[channel] = update
        metrics = causal_credit_ppo_update(descendant, rollout, config, arm)
        update_successes = sum(bool(row["success"]) for row in completed)
        total_episodes += len(completed)
        total_successes += update_successes
        row: dict[str, Any] = {
            "update": update,
            "environment_steps": (
                update * config.num_envs * config.rollout_steps
            ),
            "episodes_completed": len(completed),
            "episode_successes": update_successes,
            "cumulative_episodes": total_episodes,
            "cumulative_successes": total_successes,
            "mean_rollout_terminal_reward": float(
                rollout.terminal_rewards.mean()
            ),
            "max_rollout_terminal_reward": float(
                rollout.terminal_rewards.max()
            ),
            "event_counts": event_counts,
            "cumulative_event_counts": dict(cumulative_events),
            "phase_counts": phase_counts,
            "rollout_semantics": semantics,
            **metrics,
        }
        history.append(row)
        latest: list[dict[str, Any]] = []
        if update % 10 == 0:
            for mode in ACTION_MODES:
                evaluation, _ = _evaluate(descendant, config, mode)
                evaluation["update"] = update
                evaluations.append(evaluation)
                latest.append(evaluation)
        if progress_callback is not None:
            progress_callback(
                {
                    "arm": arm,
                    "update": update,
                    "updates": UPDATES,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_successes": total_successes,
                    "cumulative_event_counts": dict(cumulative_events),
                    "latest_evaluations": latest,
                }
            )

    final_evaluations: dict[str, Any] = {}
    final_world_rows: dict[str, Any] = {}
    final_replay = True
    for mode in ACTION_MODES:
        evaluation, rows = _evaluate(descendant, config, mode)
        final_evaluations[mode] = evaluation
        final_world_rows[mode] = rows
        scheduled = [
            row
            for row in evaluations
            if int(row["update"]) == UPDATES and row["action_mode"] == mode
        ]
        expected = dict(evaluation)
        expected["update"] = UPDATES
        final_replay &= len(scheduled) == 1 and scheduled[0] == expected
    final_state = _module_birth_details(descendant)
    evaluation_counts = {
        mode: sum(row["action_mode"] == mode for row in evaluations)
        for mode in ACTION_MODES
    }
    checkpoint_payload = {
        "schema_version": 1,
        "arm": arm,
        "birth_seed": BIRTH_SEED,
        "training_seed": TRAINING_SEED,
        "updates": UPDATES,
        "reward_mode": "terminal",
        "germ_mode": "blind",
        "config": asdict(config),
        "germ": descendant.learner.germ,
        "model_state_dict": descendant.learner.model.state_dict(),
        "auxiliary_heads_state_dict": descendant.auxiliary_heads.state_dict(),
        "writer_state_dict": descendant.learner.writer.state_dict(),
        "optimizer_state_dict": descendant.learner.optimizer.state_dict(),
        "writer_optimizer_state_dict": (
            descendant.learner.writer_optimizer.state_dict()
        ),
        "recurrent_hidden": descendant.learner.recurrent_hidden,
        "previous_actions": descendant.learner.previous_actions,
        "previous_rewards": descendant.learner.previous_rewards,
        "numpy_rng_state": descendant.learner.numpy_rng.bit_generator.state,
        "torch_generator_state": descendant.learner.torch_generator.get_state(),
    }
    _atomic_torch_save(checkpoint_path, checkpoint_payload)
    checkpoint_verified = False
    try:
        reloaded = torch.load(
            checkpoint_path, map_location="cpu", weights_only=False
        )
        checkpoint_verified = (
            reloaded.get("arm") == arm
            and int(reloaded.get("updates", -1)) == UPDATES
            and np.array_equal(reloaded.get("germ"), initial_germ)
        )
    except Exception:
        checkpoint_verified = False

    expected_evaluations = 1 + UPDATES // 10
    gates = {
        "all_metrics_finite": _finite_credit_history(history),
        "expected_update_count": len(history) == UPDATES,
        "expected_environment_steps": history[-1]["environment_steps"]
        == EXPECTED_STEPS,
        "expected_evaluations_per_mode": all(
            evaluation_counts[mode] == expected_evaluations
            for mode in ACTION_MODES
        ),
        "final_evaluations_replay_exactly": final_replay,
        "all_rollout_semantics_pass": bool(semantics_accumulator)
        and all(semantics_accumulator.values()),
        "base_actor_critic_changed": initial_state["digests"]["actor_critic"]
        != final_state["digests"]["actor_critic"],
        "auxiliary_head_state_matches_arm": (
            initial_state["digests"]["auxiliary_heads"]
            == final_state["digests"]["auxiliary_heads"]
        )
        == (arm == "guarded_terminal"),
        "auxiliary_heads_zero_at_birth": bool(
            initial_state["auxiliary_heads_zero"]
        ),
        "writer_unchanged": initial_state["digests"]["writer"]
        == final_state["digests"]["writer"],
        "carrier_birth_exact": bool(
            np.array_equal(descendant.learner.germ, initial_germ)
        ),
        "checkpoint_reloads": checkpoint_verified,
    }
    result = {
        "schema_version": 1,
        "arm": arm,
        "birth_seed": BIRTH_SEED,
        "training_seed": TRAINING_SEED,
        "updates": UPDATES,
        "environment_steps": EXPECTED_STEPS,
        "reward_mode": "terminal",
        "germ_mode": "blind",
        "config": asdict(config),
        "history": history,
        "evaluations": evaluations,
        "final_evaluations": final_evaluations,
        "final_world_rows": final_world_rows,
        "episodes_completed": total_episodes,
        "training_goal_successes": total_successes,
        "cumulative_event_counts": cumulative_events,
        "first_signal_update": first_signal_update,
        "first_evaluation_reach": {
            mode: _first_evaluation_reach(evaluations, mode)
            for mode in ACTION_MODES
        },
        "initial_state": initial_state,
        "final_state": final_state,
        "rollout_semantics": semantics_accumulator,
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    atomic_json(result_path, result, output_root)
    if not result["completed_cleanly"]:
        raise RuntimeError(f"{arm} failed completion gates: {gates}")
    return result


def _arm_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    final = result["final_evaluations"]
    return {
        "arm": result["arm"],
        "training_goal_successes": int(result["training_goal_successes"]),
        "training_event_counts": dict(result["cumulative_event_counts"]),
        "first_signal_update": dict(result["first_signal_update"]),
        "first_evaluation_reach": dict(result["first_evaluation_reach"]),
        "final_entropy": float(result["history"][-1]["entropy"]),
        "final_successes": {
            mode: int(final[mode]["successes"]) for mode in ACTION_MODES
        },
        "deepest_reached": {
            mode: _deepest_reached(final[mode]["conditional_chain"])
            for mode in ACTION_MODES
        },
        "final_chain": {
            mode: final[mode]["conditional_chain"] for mode in ACTION_MODES
        },
    }


def _outcome_classification(
    summaries: Sequence[Mapping[str, Any]],
) -> str:
    event_order = [
        row["to"] for row in summaries[0]["final_chain"]["fixed_random"]
    ]
    ranks = {
        row["arm"]: (
            event_order.index(row["deepest_reached"]["fixed_random"])
            if row["deepest_reached"]["fixed_random"] in event_order
            else -1
        )
        for row in summaries
    }
    by_arm = {row["arm"]: row for row in summaries}
    guarded = by_arm["guarded_terminal"]
    if guarded["training_goal_successes"] or any(
        guarded["final_successes"].values()
    ):
        return "GUARDED_TERMINAL_FOUND_GOAL"
    if ranks["phase_actor"] > max(
        ranks["guarded_terminal"], ranks["aux_critic_only"]
    ):
        return "PHASE_ACTOR_ADVANCED_DEEPEST_LINK"
    if (
        ranks["aux_critic_only"] > ranks["guarded_terminal"]
        and ranks["aux_critic_only"] >= ranks["phase_actor"]
    ):
        return "AUXILIARY_REPRESENTATION_REMAINS_LIVE"
    return "NO_UNIQUE_PHASE_ACTOR_DEPTH_ADVANCE"


def markdown_report(scout: Mapping[str, Any]) -> str:
    summaries = scout["arm_summaries"]
    lines = [
        "# DoorKey phase-value causal-credit scout v1",
        "",
        "**Status:** `MECHANISM SCOUT — NOT A LAW TEST`  ",
        f"**Outcome:** `{scout['outcome_classification']}`  ",
        "**Carrier:** unchanged, empty, blind 64-byte germ in every arm",
        "",
        "## Bottom line",
        "",
        (
            "Three matched learners tested terminal-only guarded PPO, auxiliary "
            "event critics without auxiliary actor credit, and phase-specific "
            "actor credit. The table reports raw outcomes; behavioral success "
            "was not a completion gate."
        ),
        "",
        "| Arm | Training key / door / goal events | Training goals | Final argmax / fixed goals | Deepest fixed-random event | Final entropy |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for row in summaries:
        events = row["training_event_counts"]
        lines.append(
            f"| `{row['arm']}` | {events['key']} / {events['door']} / "
            f"{events['goal']} | {row['training_goal_successes']} | "
            f"{row['final_successes']['deterministic']} / "
            f"{row['final_successes']['fixed_random']} | "
            f"`{row['deepest_reached']['fixed_random']}` | "
            f"{row['final_entropy']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Final fixed-random causal chain",
            "",
            "| Arm | Explore | Find key | Retain key | Find door | Open door | Reach goal |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summaries:
        cells = " | ".join(
            f"{event['reached']}/{event['eligible']}"
            for event in row["final_chain"]["fixed_random"]
        )
        lines.append(f"| `{row['arm']}` | {cells} |")
    lines.extend(["", "## First naturally observed training signal", ""])
    lines.extend(
        [
            "| Arm | Key update | Door update | Goal update |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in summaries:
        first = row["first_signal_update"]
        lines.append(
            f"| `{row['arm']}` | {first['key']} | {first['door']} | "
            f"{first['goal']} |"
        )
    lines.extend(["", "## Completion integrity", ""])
    for gate, passed in scout["completion_gates"].items():
        lines.append(f"- `{gate}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            (
                f"The three arms used {scout['total_new_transitions']:,} new "
                f"transitions in {scout['elapsed_training_seconds']:.3f} seconds "
                "on one CPU thread. All generated artifacts are external."
            ),
            "",
            "## Interpretation boundary",
            "",
            (
                "This is a within-lifetime credit-assignment diagnostic. It "
                "does not test germ content, vertical transmission, renewal, "
                "ontology, or any numbered law."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_scout(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if args.run_id != RUN_ID:
        raise ValueError(f"frozen run ID must be {RUN_ID}")
    output_root = external_root(args.external_root)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    null_output = output_root / "outputs" / NULL_REFERENCE_RUN
    null_run = output_root / "runs" / NULL_REFERENCE_RUN
    null_panel_path = null_output / "panel.json"
    null_manifest_path = null_run / "MANIFEST.json"
    null_hashes_path = null_output / "output_hashes.sha256"
    input_paths = [
        workspace / "protocols/DOORKEY_PHASE_VALUE_CREDIT_SCOUT_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_scout.py",
        workspace / "src/laws_confirmation/doorkey_zero_reward_null.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_phase_value_credit.py",
        null_panel_path,
        null_manifest_path,
        null_hashes_path,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    null_gate = qualify_null_reference(
        null_panel_path, null_manifest_path, null_hashes_path
    )
    if not null_gate["passes"]:
        raise RuntimeError(f"null reference gate failed: {null_gate['gates']}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = FeedbackPPOConfig()
    disk = _disk_preflight(output_root, 256 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")
    arm_specs = [
        {
            "arm": arm,
            "birth_seed": BIRTH_SEED,
            "training_seed": TRAINING_SEED,
            "updates": UPDATES,
        }
        for arm in ARMS
    ]
    if args.resume:
        if not output_dir.is_dir() or not run_dir.is_dir():
            raise FileNotFoundError("resumable run directories do not exist")
        if (run_dir / "COMPLETE").exists() or (run_dir / "FAILED").exists():
            raise RuntimeError("only an interrupted RUNNING scout may resume")
        manifest = json.loads(
            (run_dir / "MANIFEST.json").read_text(encoding="utf-8")
        )
        if manifest.get("input_sha256") != input_hashes:
            raise RuntimeError("frozen inputs changed; refusing resume")
        if manifest.get("arm_specs") != arm_specs:
            raise RuntimeError("frozen arm specifications changed; refusing resume")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        output_dir.mkdir(parents=True)
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "stage": "DoorKey phase-value causal-credit scout",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "external_root": str(output_root),
            "output_dir": str(output_dir),
            "input_sha256": input_hashes,
            "contract_digest": canonical_digest(
                {
                    "input_sha256": input_hashes,
                    "config": asdict(config),
                    "arm_specs": arm_specs,
                    "null_reference_digest": null_gate["reference_digest"],
                }
            ),
            "repository_head": git_head(workspace),
            "config": asdict(config),
            "arm_specs": arm_specs,
            "workers": 1,
            "cpu_thread_limit": 1,
            "reward_mode": "terminal",
            "germ_mode": "blind",
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "null_reference_gate": null_gate,
            "disk_preflight": disk,
            "environment": environment_manifest(),
        }
        atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    atomic_text(run_dir / "RUN.pid", f"{os.getpid()}\n", output_root)
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    atomic_json(
        run_dir / "STATUS.json",
        {"status": "RUNNING", "updated_utc": utc_now(), "arm_index": 0},
        output_root,
    )

    def progress(row: Mapping[str, Any]) -> None:
        if int(row["update"]) % 5 == 0:
            status = {"status": "RUNNING", "updated_utc": utc_now(), **dict(row)}
            atomic_json(run_dir / "STATUS.json", status, output_root)
            events = row["cumulative_event_counts"]
            print(
                f"{row['arm']} update {row['update']}/{UPDATES} "
                f"events={events['key']}/{events['door']}/{events['goal']}",
                flush=True,
            )

    try:
        training_started = time.monotonic()
        results = [
            _train_arm(
                arm,
                config,
                output_root,
                output_dir,
                progress,
            )
            for arm in ARMS
        ]
        elapsed_training = time.monotonic() - training_started
        birth_evaluations = [
            {
                row["action_mode"]: row
                for row in result["evaluations"]
                if int(row["update"]) == 0
            }
            for result in results
        ]
        birth_evaluations_match = all(
            evaluation == birth_evaluations[0]
            for evaluation in birth_evaluations[1:]
        )
        summaries = [_arm_summary(result) for result in results]
        observed_specs = [
            {
                "arm": result["arm"],
                "birth_seed": result["birth_seed"],
                "training_seed": result["training_seed"],
                "updates": result["updates"],
            }
            for result in results
        ]
        completion_gates = {
            "null_reference_gate_passed": null_gate["passes"],
            "three_frozen_arms_exact": observed_specs == arm_specs,
            "all_arms_completed_cleanly": all(
                result["completed_cleanly"] for result in results
            ),
            "all_arms_expected_transitions": all(
                result["environment_steps"] == EXPECTED_STEPS
                for result in results
            ),
            "common_birth_evaluations_exact": birth_evaluations_match,
            "all_writers_dormant": all(
                result["completion_gates"]["writer_unchanged"]
                for result in results
            ),
            "all_carriers_birth_exact": all(
                result["completion_gates"]["carrier_birth_exact"]
                for result in results
            ),
        }
        scout = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "MECHANISM_SCOUT",
            "config": asdict(config),
            "arm_specs": arm_specs,
            "arm_summaries": summaries,
            "outcome_classification": _outcome_classification(summaries),
            "elapsed_training_seconds": elapsed_training,
            "total_new_transitions": len(ARMS) * EXPECTED_STEPS,
            "null_reference_gate": null_gate,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(output_dir / "scout.json", scout, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(scout), output_root)
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "scout.json",
            output_dir / "audit.md",
            output_dir / "input_hashes.sha256",
        ]
        for arm in ARMS:
            output_paths.extend(
                (
                    output_dir / f"{arm}.json",
                    output_dir / f"{arm}_checkpoint.pt",
                )
            )
        write_hash_manifest(
            output_paths, output_dir / "output_hashes.sha256", output_root
        )
        status = {
            "status": "COMPLETE" if scout["completed_cleanly"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "outcome_classification": scout["outcome_classification"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        sentinel = "COMPLETE" if scout["completed_cleanly"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0 if scout["completed_cleanly"] else 1
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> int:
    return run_scout(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
