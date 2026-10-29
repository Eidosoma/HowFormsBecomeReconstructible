"""Three hard-reset generations for the fixed 64-byte DoorKey carrier.

This is an outcome-open development scout.  The only lineage argument accepted
at birth is a :class:`BoundaryPacket`; all policy, optimizer, recurrent,
rollout, writer, evidence, comparator, and RNG state is reconstructed afresh.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, fields
import inspect
import json
import multiprocessing
from pathlib import Path
import platform
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .doorkey_boundary import BoundaryPacket, make_boundary_packet
from .doorkey_carrier import (
    GermSchema,
    carrier_digest,
    corrupt_byte,
    empty_germ,
    permute_payloads,
    read_germ,
)
from .doorkey_causal_writer import (
    CausalWriterLedger,
    derive_causal_writer_decision,
    ledger_storage_bytes,
    renew_germ_from_causal_evidence,
)
from .doorkey_env import CAUSAL_CHAIN, DoorKeyEnv, TRANSFORMS, make_layout
from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
    _deepest_reached,
    _disk_preflight,
    _read_hash_manifest,
    _without_world_rows,
)
from .doorkey_phase_value_credit import (
    CHANNELS,
    DOOR_CHANNEL,
    GOAL_CHANNEL,
    KEY_CHANNEL,
    AuxiliaryValueHeads,
    CausalCreditDescendant,
    CausalCreditRollout,
    _compute_goal_gae,
    _compute_phase_gae,
    _finite_credit_history,
    _first_evaluation_reach,
    _forward_sequence_values,
    _forward_step_values,
    _masked_mse,
    _module_birth_details,
    actor_advantage_for_arm,
    causal_credit_digests,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import (
    START_ACTION,
    FeedbackPPOConfig,
    _apply_prior,
    _conditional_chain,
    _generator_digest,
    _module_digest,
    _numpy_generator_digest,
    _optimizer_tensor_count,
    _tensor_digest,
    birth_feedback_ppo_descendant,
    evaluate_feedback_policy,
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


RUN_ID = "doorkey_vertical_three_boundary_scout_v1_attempt1"
WRITER_RUN = "doorkey_causal_writer_qualification_v1_attempt1"
ARMS = (
    "rewrite",
    "stale_copy",
    "writer_off",
    "silence",
    "wrong_frozen",
    "wrong_rewrite",
    "reader_off_rewrite",
    "lesion_rewrite",
)
GENERATIONS = (1, 2, 3)
UPDATES = 100
EXPECTED_STEPS = 409_600
MAX_WORKERS = 3
WRITER_WORLDS_PER_TRANSFORM = 8
WRITER_STOCHASTIC_REPEATS = 4
SEEDS = {
    1: {
        "birth": 940_000,
        "training": 950_000,
        "writer_layout": 86_000_000,
        "writer_action": 87_000_000,
    },
    2: {
        "birth": 941_000,
        "training": 951_000,
        "writer_layout": 86_100_000,
        "writer_action": 87_100_000,
    },
    3: {
        "birth": 942_000,
        "training": 952_000,
        "writer_layout": 86_200_000,
        "writer_action": 87_200_000,
    },
}


def make_vertical_descendant(
    packet: BoundaryPacket,
    config: FeedbackPPOConfig,
    birth_seed: int,
) -> CausalCreditDescendant:
    """Birth fresh phase-credit soma from one packet and public inputs only."""

    learner = birth_feedback_ppo_descendant(packet, config, birth_seed)
    auxiliary_heads = AuxiliaryValueHeads(config.hidden_size).to(
        next(learner.model.parameters()).device
    )
    learner.optimizer = torch.optim.Adam(
        [*learner.model.parameters(), *auxiliary_heads.parameters()],
        lr=config.learning_rate,
    )
    return CausalCreditDescendant(
        learner=learner,
        auxiliary_heads=auxiliary_heads,
    )


def collect_vertical_rollout(
    descendant: CausalCreditDescendant,
    environments: DoorKeyVectorEnv,
    config: FeedbackPPOConfig,
    germ_mode: str,
) -> tuple[CausalCreditRollout, list[dict[str, Any]]]:
    """Collect phase-specific rewards while expressing the scheduled reader."""

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

    from .doorkey_phase_value_credit import phase_from_observations

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
            logits, _ = _apply_prior(base_logits, learner, observation, germ_mode)
            log_probs = F.log_softmax(logits, dim=-1)
            action = torch.multinomial(
                log_probs.exp(), 1, generator=learner.torch_generator
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
    auxiliary_advantages, auxiliary_returns = _compute_phase_gae(
        event_reward_tensor[:, :, :2],
        phase_tensor,
        next_phase_tensor,
        done_tensor,
        auxiliary_value_tensor,
        next_auxiliary_value,
        config,
    )
    rollout = CausalCreditRollout(
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
    return rollout, environments.pop_completed()


def vertical_phase_ppo_update(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    germ_mode: str,
) -> dict[str, Any]:
    """The frozen phase-actor update with carrier expression in PPO replay."""

    actor_advantage, signals = actor_advantage_for_arm(rollout, "phase_actor")
    descendant.learner.model.train()
    descendant.auxiliary_heads.train()
    collected: dict[str, list[float]] = {
        name: []
        for name in (
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
                germ_mode,
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
    result["actor_advantage_nonzero_count"] = int(torch.count_nonzero(actor_advantage))
    return result


def _evaluate(
    descendant: CausalCreditDescendant,
    config: FeedbackPPOConfig,
    germ_mode: str,
    action_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return _without_world_rows(
        evaluate_feedback_policy(
            descendant.learner,
            config,
            germ_mode=germ_mode,
            feedback_reward_mode="terminal",
            action_mode=action_mode,
            worlds_per_transform=8,
            stochastic_repeats=4,
        )
    )


def collect_descendant_writer_assay(
    descendant: CausalCreditDescendant,
    birth: CausalCreditDescendant,
    config: FeedbackPPOConfig,
    *,
    germ_mode: str,
    layout_seed: int,
    action_seed: int,
) -> tuple[CausalWriterLedger, list[dict[str, Any]], dict[str, Any]]:
    """Measure lived effects against the same descendant's birth policy."""

    envs: list[DoorKeyEnv] = []
    stream_ids: list[int] = []
    for transform_index, transform in enumerate(TRANSFORMS):
        for local_seed in range(WRITER_WORLDS_PER_TRANSFORM):
            seed = layout_seed + transform_index * 10_000 + local_seed
            for stream in range(WRITER_STOCHASTIC_REPEATS):
                envs.append(
                    DoorKeyEnv(
                        make_layout(seed, transform),
                        max_steps=config.max_episode_steps,
                    )
                )
                stream_ids.append(stream)
    count = len(envs)
    final_hidden = torch.zeros((count, config.hidden_size), dtype=torch.float32)
    birth_hidden = torch.zeros_like(final_hidden)
    previous_action = torch.full((count,), START_ACTION, dtype=torch.long)
    previous_reward = torch.zeros(count, dtype=torch.float32)
    episode_start = torch.ones(count, dtype=torch.bool)
    active = np.ones(count, dtype=bool)
    uniforms = np.random.default_rng(action_seed).random(
        (config.max_episode_steps, count)
    )
    ledger = CausalWriterLedger.empty()
    descendant.learner.model.eval()
    birth.learner.model.eval()
    recurrent_bytes = (
        final_hidden.numel() * final_hidden.element_size()
        + birth_hidden.numel() * birth_hidden.element_size()
    )

    for step in range(config.max_episode_steps):
        before_np = np.stack([env.observation().vector() for env in envs])
        observations = torch.from_numpy(before_np).to(dtype=torch.float32)
        with torch.no_grad():
            final_base_logits, _, next_final_hidden = (
                descendant.learner.model.forward_step(
                    observations,
                    final_hidden,
                    episode_start,
                    previous_action,
                    previous_reward,
                )
            )
            expressed_logits, _ = _apply_prior(
                final_base_logits,
                descendant.learner,
                observations,
                germ_mode,
            )
            birth_logits, _, next_birth_hidden = birth.learner.model.forward_step(
                observations,
                birth_hidden,
                episode_start,
                previous_action,
                previous_reward,
            )
            final_probabilities = F.softmax(expressed_logits, dim=-1).cpu().numpy()
            # Deliberately no inherited prior here: this is the reconstructed
            # before-learning disposition of the same newly initialized body.
            birth_probabilities = F.softmax(birth_logits, dim=-1).cpu().numpy()
            cumulative = np.cumsum(final_probabilities, axis=1)
            action_np = (uniforms[step, :, None] > cumulative).sum(axis=1)
            action_np = np.minimum(action_np, config.num_actions - 1)
        reward_np = np.zeros(count, dtype=np.float32)
        done_indices: list[int] = []
        for index in np.flatnonzero(active):
            after, reward, terminated, truncated, info = envs[index].step(
                int(action_np[index])
            )
            reward_np[index] = reward
            ledger.record(
                before_np[index],
                int(action_np[index]),
                after.vector(),
                info,
                birth_probabilities[index],
                final_probabilities[index],
            )
            if terminated or truncated:
                active[index] = False
                done_indices.append(int(index))
        final_hidden = next_final_hidden
        birth_hidden = next_birth_hidden
        previous_action = torch.from_numpy(action_np).to(dtype=torch.long)
        previous_reward = torch.from_numpy(reward_np)
        episode_start = torch.zeros_like(episode_start)
        if done_indices:
            final_hidden[done_indices] = 0.0
            birth_hidden[done_indices] = 0.0
            previous_action[done_indices] = START_ACTION
            previous_reward[done_indices] = 0.0
        if not active.any():
            break
    rows = [
        {
            "layout_seed": env.layout.seed,
            "transform": env.layout.transform,
            "action_stream": stream_ids[index],
            "success": env.terminated,
            "truncated": env.truncated,
            "episode_steps": env.steps,
            "event_steps": dict(env.event_steps),
            "auxiliary_steps": dict(env.auxiliary_steps),
        }
        for index, env in enumerate(envs)
    ]
    return (
        ledger,
        rows,
        {
            "world_count": count,
            "unique_layout_count": WRITER_WORLDS_PER_TRANSFORM * len(TRANSFORMS),
            "successes": sum(bool(row["success"]) for row in rows),
            "conditional_chain": _conditional_chain(rows),
            "recurrent_comparator_bytes": recurrent_bytes,
            "layout_seed": layout_seed,
            "action_seed": action_seed,
        },
    )


def _model_parameter_bytes(module: nn.Module) -> int:
    return int(
        sum(value.numel() * value.element_size() for value in module.parameters())
    )


def run_descendant_writer(
    descendant: CausalCreditDescendant,
    config: FeedbackPPOConfig,
    *,
    germ_mode: str,
    birth_seed: int,
    layout_seed: int,
    action_seed: int,
) -> dict[str, Any]:
    """Run and exactly replay one late-life analytic writer transaction."""

    before = causal_credit_digests(descendant)
    birth = make_vertical_descendant(
        make_boundary_packet(empty_germ(1)), config, birth_seed
    )
    ledger, rows, summary = collect_descendant_writer_assay(
        descendant,
        birth,
        config,
        germ_mode=germ_mode,
        layout_seed=layout_seed,
        action_seed=action_seed,
    )
    decision = derive_causal_writer_decision(ledger)
    renewal = renew_germ_from_causal_evidence(ledger, descendant.learner.germ)
    after = causal_credit_digests(descendant)

    replay_birth = make_vertical_descendant(
        make_boundary_packet(empty_germ(1)), config, birth_seed
    )
    replay_ledger, replay_rows, replay_summary = collect_descendant_writer_assay(
        descendant,
        replay_birth,
        config,
        germ_mode=germ_mode,
        layout_seed=layout_seed,
        action_seed=action_seed,
    )
    replay_decision = derive_causal_writer_decision(replay_ledger)
    replay_renewal = renew_germ_from_causal_evidence(
        replay_ledger, descendant.learner.germ
    )
    decoded = read_germ(renewal.germ)
    replay_exact = bool(
        ledger.to_dict() == replay_ledger.to_dict()
        and rows == replay_rows
        and summary == replay_summary
        and decision.to_dict() == replay_decision.to_dict()
        and renewal.to_dict() == replay_renewal.to_dict()
        and np.array_equal(renewal.germ, replay_renewal.germ)
    )
    gates = {
        "trained_parent_unchanged": before
        == after
        == causal_credit_digests(descendant),
        "writer_assay_replays_exactly": replay_exact,
        "expected_episode_count": len(rows)
        == WRITER_WORLDS_PER_TRANSFORM * len(TRANSFORMS) * WRITER_STOCHASTIC_REPEATS,
        "carrier_exactly_64_bytes": renewal.germ.nbytes == 64,
        "all_addresses_valid": bool(decoded.address_valid.all()),
        "all_checksums_valid": bool(decoded.checksum_valid.all()),
    }
    return {
        "enabled": True,
        "ledger": ledger.to_dict(),
        "decision": decision.to_dict(),
        "renewal": renewal.to_dict(),
        "candidate_carrier": renewal.germ.tolist(),
        "candidate_carrier_sha256": carrier_digest(renewal.germ),
        "candidate_decoded": {
            "active": decoded.active.tolist(),
            "targets": decoded.prior_logits.argmax(axis=-1).tolist(),
            "trust": decoded.trust.tolist(),
            "freshness": decoded.freshness.tolist(),
            "address_valid": decoded.address_valid.tolist(),
            "checksum_valid": decoded.checksum_valid.tolist(),
        },
        "assay": summary,
        "world_rows": rows,
        "cost": {
            "transmitted_carrier_bytes": 64,
            "analytic_ledger_array_bytes": ledger_storage_bytes(ledger),
            "reconstructed_birth_comparator_parameter_bytes": _model_parameter_bytes(
                birth.learner.model
            ),
            "neural_writer_scaffold_parameter_bytes_unused": _model_parameter_bytes(
                descendant.learner.writer
            ),
            "transient_dual_recurrent_state_bytes": summary[
                "recurrent_comparator_bytes"
            ],
            "assay_transitions": ledger.transition_count,
        },
        "gates": gates,
        "passes": all(gates.values()),
    }


def _load_parent_checkpoint(
    path: Path,
) -> tuple[CausalCreditDescendant, FeedbackPPOConfig, dict[str, Any]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    config = FeedbackPPOConfig(**payload["config"])
    parent_germ = np.asarray(payload["germ"], dtype=np.uint8)
    parent = make_vertical_descendant(
        make_boundary_packet(parent_germ), config, int(payload["birth_seed"])
    )
    parent.learner.model.load_state_dict(payload["model_state_dict"])
    parent.auxiliary_heads.load_state_dict(payload["auxiliary_heads_state_dict"])
    parent.learner.writer.load_state_dict(payload["writer_state_dict"])
    parent.learner.optimizer.load_state_dict(payload["optimizer_state_dict"])
    parent.learner.writer_optimizer.load_state_dict(
        payload["writer_optimizer_state_dict"]
    )
    parent.learner.recurrent_hidden = payload["recurrent_hidden"].clone()
    parent.learner.previous_actions = payload["previous_actions"].clone()
    parent.learner.previous_rewards = payload["previous_rewards"].clone()
    parent.learner.numpy_rng.bit_generator.state = payload["numpy_rng_state"]
    parent.learner.torch_generator.set_state(payload["torch_generator_state"])
    parent.learner.rollout_state = payload.get("rollout_state")
    return parent, config, payload


def audit_vertical_boundary(
    parent_checkpoint: Path,
    child: CausalCreditDescendant,
    packet: BoundaryPacket,
    *,
    generation: int,
) -> dict[str, Any]:
    """Audit destruction of every serialized parent state at an actual birth."""

    parent, parent_config, payload = _load_parent_checkpoint(parent_checkpoint)
    parent_rollout_present = payload.get("rollout_state") is not None
    child_learner = child.learner
    wrapper_parameters = tuple(inspect.signature(make_vertical_descendant).parameters)
    underlying_parameters = tuple(
        inspect.signature(birth_feedback_ppo_descendant).parameters
    )
    ppo_parent_count = _optimizer_tensor_count(parent.learner.optimizer)
    ppo_child_count = _optimizer_tensor_count(child_learner.optimizer)
    writer_parent_count = _optimizer_tensor_count(parent.learner.writer_optimizer)
    writer_child_count = _optimizer_tensor_count(child_learner.writer_optimizer)
    rows = {
        "actor_critic_parameters": {
            "parent_digest": _module_digest(parent.learner.model),
            "child_digest": _module_digest(child_learner.model),
            "reset": _module_digest(parent.learner.model)
            != _module_digest(child_learner.model),
        },
        "auxiliary_value_heads": {
            "parent_digest": _module_digest(parent.auxiliary_heads),
            "child_digest": _module_digest(child.auxiliary_heads),
            "child_zero": all(
                torch.count_nonzero(value).item() == 0
                for value in child.auxiliary_heads.parameters()
            ),
            "reset": _module_digest(parent.auxiliary_heads)
            != _module_digest(child.auxiliary_heads)
            and all(
                torch.count_nonzero(value).item() == 0
                for value in child.auxiliary_heads.parameters()
            ),
        },
        "neural_writer_scaffold": {
            "parent_digest": _module_digest(parent.learner.writer),
            "child_digest": _module_digest(child_learner.writer),
            "reset": _module_digest(parent.learner.writer)
            != _module_digest(child_learner.writer),
        },
        "ppo_optimizer": {
            "parent_tensor_count": ppo_parent_count,
            "child_tensor_count": ppo_child_count,
            "reset": ppo_parent_count > 0 and ppo_child_count == 0,
        },
        "writer_optimizer": {
            "parent_tensor_count": writer_parent_count,
            "child_tensor_count": writer_child_count,
            "status": "dormant_and_empty_on_both_sides",
            "reset": writer_parent_count == 0 and writer_child_count == 0,
        },
        "rollout_state": {
            "parent_present": parent_rollout_present,
            "parent_status": (
                "already_absent_at_founder_serialization"
                if generation == 1
                else "retained_as_vertical_leak_probe"
            ),
            "child_present": child_learner.rollout_state is not None,
            "reset": (
                (
                    not parent_rollout_present
                    if generation == 1
                    else parent_rollout_present
                )
                and child_learner.rollout_state is None
            ),
        },
        "recurrent_state": {
            "parent_digest": _tensor_digest(parent.learner.recurrent_hidden),
            "child_digest": _tensor_digest(child_learner.recurrent_hidden),
            "parent_nonzero": bool(
                torch.count_nonzero(parent.learner.recurrent_hidden)
            ),
            "child_zero": not bool(torch.count_nonzero(child_learner.recurrent_hidden)),
            "memory_shared": parent.learner.recurrent_hidden.data_ptr()
            == child_learner.recurrent_hidden.data_ptr(),
            "reset": not bool(torch.count_nonzero(child_learner.recurrent_hidden))
            and parent.learner.recurrent_hidden.data_ptr()
            != child_learner.recurrent_hidden.data_ptr(),
        },
        "previous_action_state": {
            "parent_all_start": bool(
                torch.all(parent.learner.previous_actions == START_ACTION)
            ),
            "child_all_start": bool(
                torch.all(child_learner.previous_actions == START_ACTION)
            ),
            "memory_shared": parent.learner.previous_actions.data_ptr()
            == child_learner.previous_actions.data_ptr(),
            "reset": bool(torch.all(child_learner.previous_actions == START_ACTION))
            and parent.learner.previous_actions.data_ptr()
            != child_learner.previous_actions.data_ptr(),
        },
        "previous_reward_state": {
            "parent_nonzero": bool(
                torch.count_nonzero(parent.learner.previous_rewards)
            ),
            "child_zero": not bool(torch.count_nonzero(child_learner.previous_rewards)),
            "memory_shared": parent.learner.previous_rewards.data_ptr()
            == child_learner.previous_rewards.data_ptr(),
            "reset": not bool(torch.count_nonzero(child_learner.previous_rewards))
            and parent.learner.previous_rewards.data_ptr()
            != child_learner.previous_rewards.data_ptr(),
        },
        "private_rngs": {
            "parent_torch_digest": _generator_digest(parent.learner.torch_generator),
            "child_torch_digest": _generator_digest(child_learner.torch_generator),
            "parent_numpy_digest": _numpy_generator_digest(parent.learner.numpy_rng),
            "child_numpy_digest": _numpy_generator_digest(child_learner.numpy_rng),
            "reset": _generator_digest(parent.learner.torch_generator)
            != _generator_digest(child_learner.torch_generator)
            and _numpy_generator_digest(parent.learner.numpy_rng)
            != _numpy_generator_digest(child_learner.numpy_rng),
        },
        "normalization_state": {"status": "absent_by_design", "reset": True},
        "curriculum_state": {"status": "absent_by_design", "reset": True},
        "population_statistics": {"status": "absent_by_design", "reset": True},
        "analytic_writer_ledger": {"status": "not_serialized", "reset": True},
        "birth_comparator": {"status": "not_serialized", "reset": True},
        "global_rng": {
            "status": "birth_uses_fork_rng_and_training_uses_private_generators",
            "reset": True,
        },
    }
    packet_fields = tuple(field.name for field in fields(BoundaryPacket))
    forbidden_fragments = ("ledger", "comparator", "evidence")
    gates = {
        "wrapper_birth_api_has_no_parent": wrapper_parameters
        == ("packet", "config", "birth_seed"),
        "underlying_birth_api_has_no_parent": underlying_parameters
        == ("packet", "config", "birth_seed", "device"),
        "packet_has_only_payload": packet_fields == ("payload",),
        "packet_is_exactly_64_bytes": len(packet.payload) == 64,
        "carrier_exactly_preserved": child_learner.germ[0].tobytes(order="C")
        == packet.payload,
        "public_rulebook_unchanged": parent_config.digest()
        == child_learner.public_rulebook_digest,
        "parent_checkpoint_has_no_writer_soma": not any(
            fragment in key.lower()
            for key in payload
            for fragment in forbidden_fragments
        ),
        "all_state_rows_reset": all(bool(row["reset"]) for row in rows.values()),
    }
    return {
        "generation": generation,
        "parent_checkpoint": str(parent_checkpoint),
        "parent_checkpoint_sha256": sha256_file(parent_checkpoint),
        "birth_wrapper_parameters": list(wrapper_parameters),
        "underlying_birth_parameters": list(underlying_parameters),
        "packet_fields": list(packet_fields),
        "packet_sha256": packet.digest(),
        "state_rows": rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def rollout_payload(rollout: CausalCreditRollout) -> dict[str, torch.Tensor]:
    """Retain one complete final rollout only as the next-boundary leak probe."""

    return {
        name: value.detach().cpu().clone()
        for name, value in vars(rollout).items()
        if isinstance(value, torch.Tensor)
    }


def learning_auc(
    evaluations: Sequence[Mapping[str, Any]], action_mode: str
) -> dict[str, Any]:
    rows = sorted(
        (row for row in evaluations if row["action_mode"] == action_mode),
        key=lambda row: int(row["update"]),
    )
    updates = np.asarray([int(row["update"]) for row in rows], dtype=np.float64)
    if len(rows) < 2 or updates[0] != 0 or updates[-1] != UPDATES:
        raise ValueError("learning AUC requires the complete frozen update grid")
    event_auc: dict[str, dict[str, float]] = {}
    for event in CAUSAL_CHAIN:
        chain_rows = [
            next(item for item in row["conditional_chain"] if item["to"] == event)
            for row in rows
        ]
        reached_fraction = np.asarray(
            [
                item["reached"] / row["world_count"]
                for item, row in zip(chain_rows, rows)
            ],
            dtype=np.float64,
        )
        conditional_probability = np.asarray(
            [
                0.0
                if item["conditional_probability"] is None
                else item["conditional_probability"]
                for item in chain_rows
            ],
            dtype=np.float64,
        )
        event_auc[event] = {
            "reached_fraction_auc": float(
                np.trapezoid(reached_fraction, updates) / UPDATES
            ),
            "conditional_probability_auc": float(
                np.trapezoid(conditional_probability, updates) / UPDATES
            ),
        }
    terminal_fraction = np.asarray(
        [row["successes"] / row["world_count"] for row in rows],
        dtype=np.float64,
    )
    return {
        "action_mode": action_mode,
        "updates": updates.astype(int).tolist(),
        "events": event_auc,
        "terminal_success_fraction_auc": float(
            np.trapezoid(terminal_fraction, updates) / UPDATES
        ),
    }


def _clean_evaluation_for_alias(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "germ_mode"}


def behavior_fingerprint(result: Mapping[str, Any]) -> str:
    """Digest only behavior and learned soma, excluding arm/carrier labels."""

    return canonical_digest(
        {
            "history": result["history"],
            "evaluations": [
                _clean_evaluation_for_alias(row) for row in result["evaluations"]
            ],
            "final_evaluations": {
                mode: _clean_evaluation_for_alias(row)
                for mode, row in result["final_evaluations"].items()
            },
            "final_world_rows": result["final_world_rows"],
            "episodes_completed": result["episodes_completed"],
            "training_goal_successes": result["training_goal_successes"],
            "cumulative_event_counts": result["cumulative_event_counts"],
            "first_signal_update": result["first_signal_update"],
            "first_evaluation_reach": result["first_evaluation_reach"],
            "final_state": result["final_state"],
            "rollout_semantics": result["rollout_semantics"],
        }
    )


def _select_scheduled_carrier(
    spec: Mapping[str, Any],
    incoming: np.ndarray,
    writer: Mapping[str, Any],
) -> tuple[np.ndarray, str]:
    mode = str(spec["schedule_mode"])
    if mode == "writer_candidate":
        if not writer.get("enabled"):
            raise RuntimeError("candidate scheduling requires an enabled writer")
        return np.asarray(
            writer["candidate_carrier"], dtype=np.uint8
        ), "writer_candidate"
    if mode == "incoming":
        return incoming.copy(), "incoming_exact_copy"
    if mode == "fixed":
        return np.asarray(spec["fixed_next_germ"], dtype=np.uint8), str(
            spec["fixed_source_label"]
        )
    raise ValueError(f"unknown schedule mode: {mode}")


def _train_cell(
    spec: Mapping[str, Any],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    arm = str(spec["arm"])
    generation = int(spec["generation"])
    if arm not in ARMS or generation not in GENERATIONS:
        raise ValueError("unregistered vertical cell")
    birth_seed = int(spec["birth_seed"])
    training_seed = int(spec["training_seed"])
    germ_mode = str(spec["germ_mode"])
    incoming = np.asarray(spec["incoming_germ"], dtype=np.uint8)
    packet = make_boundary_packet(incoming)
    stem = f"g{generation}_{arm}"
    result_path = output_dir / f"{stem}.json"
    checkpoint_path = output_dir / f"{stem}_checkpoint.pt"
    progress_path = output_dir / "progress" / f"{stem}.json"
    if result_path.is_file() != checkpoint_path.is_file():
        raise RuntimeError(f"partial resumable artifacts for {stem}")
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("arm") != arm
            or result.get("generation") != generation
            or result.get("birth_seed") != birth_seed
            or result.get("training_seed") != training_seed
            or result.get("updates") != UPDATES
            or result.get("incoming_carrier_sha256") != packet.digest()
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable result for {stem}")
        print(f"{stem} already complete; resuming after it", flush=True)
        return result

    atomic_json(
        progress_path,
        {
            "status": "STARTING",
            "updated_utc": utc_now(),
            "generation": generation,
            "arm": arm,
            "update": 0,
        },
        output_root,
    )
    descendant = make_vertical_descendant(packet, config, birth_seed)
    boundary = audit_vertical_boundary(
        Path(spec["parent_checkpoint"]),
        descendant,
        packet,
        generation=generation,
    )
    initial_state = _module_birth_details(descendant)
    initial_germ = descendant.learner.germ.copy()
    incoming_read = read_germ(initial_germ)
    evaluations: list[dict[str, Any]] = []
    for action_mode in ACTION_MODES:
        evaluation, _ = _evaluate(descendant, config, germ_mode, action_mode)
        evaluation["update"] = 0
        evaluations.append(evaluation)

    environments = DoorKeyVectorEnv(
        config.num_envs,
        training_seed,
        config.max_episode_steps,
        "terminal",
    )
    history: list[dict[str, Any]] = []
    total_episodes = 0
    total_successes = 0
    cumulative_events = {channel: 0 for channel in CHANNELS}
    first_signal_update: dict[str, int | None] = {channel: None for channel in CHANNELS}
    semantics_accumulator: dict[str, bool] = {}
    last_rollout: CausalCreditRollout | None = None
    for update in range(1, UPDATES + 1):
        rollout, completed = collect_vertical_rollout(
            descendant, environments, config, germ_mode
        )
        last_rollout = rollout
        semantics = rollout_semantics(rollout)
        for name, passed in semantics.items():
            semantics_accumulator[name] = (
                semantics_accumulator.get(name, True) and passed
            )
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
        metrics = vertical_phase_ppo_update(descendant, rollout, config, germ_mode)
        update_successes = sum(bool(row["success"]) for row in completed)
        total_episodes += len(completed)
        total_successes += update_successes
        row: dict[str, Any] = {
            "update": update,
            "environment_steps": update * config.num_envs * config.rollout_steps,
            "episodes_completed": len(completed),
            "episode_successes": update_successes,
            "cumulative_episodes": total_episodes,
            "cumulative_successes": total_successes,
            "mean_rollout_terminal_reward": float(rollout.terminal_rewards.mean()),
            "max_rollout_terminal_reward": float(rollout.terminal_rewards.max()),
            "event_counts": event_counts,
            "cumulative_event_counts": dict(cumulative_events),
            "phase_counts": phase_counts,
            "rollout_semantics": semantics,
            **metrics,
        }
        history.append(row)
        latest: list[dict[str, Any]] = []
        if update % 10 == 0:
            for action_mode in ACTION_MODES:
                evaluation, _ = _evaluate(descendant, config, germ_mode, action_mode)
                evaluation["update"] = update
                evaluations.append(evaluation)
                latest.append(evaluation)
        if update % 5 == 0:
            atomic_json(
                progress_path,
                {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    "generation": generation,
                    "arm": arm,
                    "update": update,
                    "updates": UPDATES,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_successes": total_successes,
                    "cumulative_event_counts": dict(cumulative_events),
                    "latest_evaluations": latest,
                },
                output_root,
            )
            print(
                f"{stem} update {update}/{UPDATES} "
                f"events={cumulative_events['key']}/"
                f"{cumulative_events['door']}/{cumulative_events['goal']}",
                flush=True,
            )

    if last_rollout is None:
        raise RuntimeError("vertical cell produced no rollout")
    final_evaluations: dict[str, Any] = {}
    final_world_rows: dict[str, Any] = {}
    final_replay = True
    for action_mode in ACTION_MODES:
        evaluation, rows = _evaluate(descendant, config, germ_mode, action_mode)
        final_evaluations[action_mode] = evaluation
        final_world_rows[action_mode] = rows
        scheduled = [
            row
            for row in evaluations
            if int(row["update"]) == UPDATES and row["action_mode"] == action_mode
        ]
        expected = dict(evaluation)
        expected["update"] = UPDATES
        final_replay &= len(scheduled) == 1 and scheduled[0] == expected
    final_state = _module_birth_details(descendant)

    if bool(spec["writer_enabled"]):
        writer = run_descendant_writer(
            descendant,
            config,
            germ_mode=germ_mode,
            birth_seed=birth_seed,
            layout_seed=int(spec["writer_layout_seed"]),
            action_seed=int(spec["writer_action_seed"]),
        )
    else:
        writer = {
            "enabled": False,
            "reason": "frozen arm disables the causal writer",
            "candidate_carrier": incoming.tolist(),
            "candidate_carrier_sha256": packet.digest(),
            "gates": {"writer_not_run": True},
            "passes": True,
        }
    if causal_credit_digests(descendant) != final_state["digests"]:
        raise RuntimeError("writer measurement changed trained descendant state")
    scheduled_germ, scheduled_source = _select_scheduled_carrier(spec, incoming, writer)
    scheduled_packet = make_boundary_packet(scheduled_germ)

    rollout_state = rollout_payload(last_rollout)
    checkpoint_payload = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "generation": generation,
        "arm": arm,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "reward_mode": "terminal",
        "germ_mode": germ_mode,
        "config": asdict(config),
        "germ": descendant.learner.germ,
        "scheduled_next_germ": scheduled_germ,
        "scheduled_next_source": scheduled_source,
        "model_state_dict": descendant.learner.model.state_dict(),
        "auxiliary_heads_state_dict": descendant.auxiliary_heads.state_dict(),
        "writer_state_dict": descendant.learner.writer.state_dict(),
        "optimizer_state_dict": descendant.learner.optimizer.state_dict(),
        "writer_optimizer_state_dict": descendant.learner.writer_optimizer.state_dict(),
        "recurrent_hidden": descendant.learner.recurrent_hidden,
        "previous_actions": descendant.learner.previous_actions,
        "previous_rewards": descendant.learner.previous_rewards,
        "rollout_state": rollout_state,
        "numpy_rng_state": descendant.learner.numpy_rng.bit_generator.state,
        "torch_generator_state": descendant.learner.torch_generator.get_state(),
    }
    _atomic_torch_save(checkpoint_path, checkpoint_payload)
    checkpoint_verified = False
    try:
        reloaded = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        checkpoint_verified = bool(
            reloaded.get("run_id") == RUN_ID
            and reloaded.get("generation") == generation
            and reloaded.get("arm") == arm
            and int(reloaded.get("updates", -1)) == UPDATES
            and np.array_equal(reloaded.get("germ"), initial_germ)
            and reloaded.get("rollout_state") is not None
            and np.array_equal(reloaded.get("scheduled_next_germ"), scheduled_germ)
        )
    except Exception:
        checkpoint_verified = False

    evaluation_counts = {
        action_mode: sum(row["action_mode"] == action_mode for row in evaluations)
        for action_mode in ACTION_MODES
    }
    expected_evaluations = 1 + UPDATES // 10
    gates = {
        "boundary_reset_passes": bool(boundary["passes"]),
        "all_metrics_finite": _finite_credit_history(history),
        "expected_update_count": len(history) == UPDATES,
        "expected_environment_steps": history[-1]["environment_steps"]
        == EXPECTED_STEPS,
        "expected_evaluations_per_mode": all(
            evaluation_counts[action_mode] == expected_evaluations
            for action_mode in ACTION_MODES
        ),
        "final_evaluations_replay_exactly": final_replay,
        "all_rollout_semantics_pass": bool(semantics_accumulator)
        and all(semantics_accumulator.values()),
        "actor_critic_changed_in_life": initial_state["digests"]["actor_critic"]
        != final_state["digests"]["actor_critic"],
        "auxiliary_heads_changed_in_life": initial_state["digests"]["auxiliary_heads"]
        != final_state["digests"]["auxiliary_heads"],
        "auxiliary_heads_zero_at_birth": bool(initial_state["auxiliary_heads_zero"]),
        "neural_writer_scaffold_dormant": initial_state["digests"]["writer"]
        == final_state["digests"]["writer"],
        "birth_carrier_unchanged_inside_life": bool(
            np.array_equal(descendant.learner.germ, initial_germ)
        ),
        "incoming_packet_exactly_64_bytes": initial_germ.nbytes == 64,
        "writer_transaction_passes_if_enabled": bool(writer["passes"]),
        "scheduled_packet_exactly_64_bytes": len(scheduled_packet.payload) == 64,
        "checkpoint_reloads_with_leak_probe": checkpoint_verified,
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "generation": generation,
        "arm": arm,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "writer_layout_seed": int(spec["writer_layout_seed"]),
        "writer_action_seed": int(spec["writer_action_seed"]),
        "updates": UPDATES,
        "environment_steps": EXPECTED_STEPS,
        "reward_mode": "terminal",
        "phase_credit_mode": "phase_actor",
        "germ_mode": germ_mode,
        "config": asdict(config),
        "parent_checkpoint": str(spec["parent_checkpoint"]),
        "incoming_carrier": incoming.tolist(),
        "incoming_carrier_sha256": packet.digest(),
        "incoming_decoded": {
            "active": incoming_read.active.tolist(),
            "targets": incoming_read.prior_logits.argmax(axis=-1).tolist(),
            "trust": incoming_read.trust.tolist(),
            "freshness": incoming_read.freshness.tolist(),
            "address_valid": incoming_read.address_valid.tolist(),
            "checksum_valid": incoming_read.checksum_valid.tolist(),
        },
        "boundary_audit": boundary,
        "history": history,
        "evaluations": evaluations,
        "learning_auc": {
            action_mode: learning_auc(evaluations, action_mode)
            for action_mode in ACTION_MODES
        },
        "final_evaluations": final_evaluations,
        "final_world_rows": final_world_rows,
        "episodes_completed": total_episodes,
        "training_goal_successes": total_successes,
        "cumulative_event_counts": cumulative_events,
        "first_signal_update": first_signal_update,
        "first_evaluation_reach": {
            action_mode: _first_evaluation_reach(evaluations, action_mode)
            for action_mode in ACTION_MODES
        },
        "initial_state": initial_state,
        "final_state": final_state,
        "rollout_semantics": semantics_accumulator,
        "writer": writer,
        "scheduled_next_carrier": scheduled_germ.tolist(),
        "scheduled_next_carrier_sha256": scheduled_packet.digest(),
        "scheduled_next_source": scheduled_source,
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    result["behavior_fingerprint"] = behavior_fingerprint(result)
    atomic_json(result_path, result, output_root)
    atomic_json(
        progress_path,
        {
            "status": "COMPLETE" if result["completed_cleanly"] else "FAILED_GATES",
            "updated_utc": utc_now(),
            "generation": generation,
            "arm": arm,
            "update": UPDATES,
            "training_goal_successes": total_successes,
            "cumulative_event_counts": cumulative_events,
            "incoming_carrier_sha256": packet.digest(),
            "scheduled_next_carrier_sha256": scheduled_packet.digest(),
            "result_path": str(result_path),
        },
        output_root,
    )
    if not result["completed_cleanly"]:
        raise RuntimeError(f"{stem} failed completion gates: {gates}")
    return result


def _worker_train_cell(
    spec: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    output_root_text: str,
    output_dir_text: str,
) -> dict[str, Any]:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    return _train_cell(
        spec,
        FeedbackPPOConfig(**dict(config_payload)),
        Path(output_root_text),
        Path(output_dir_text),
    )


def runtime_qualification(workers: int) -> dict[str, Any]:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    values = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "torch_num_threads": torch.get_num_threads(),
        "torch_num_interop_threads": torch.get_num_interop_threads(),
        "worker_processes": workers,
    }
    gates = {
        "python_3_13": platform.python_version_tuple()[:2] == ("3", "13"),
        "numpy_2_5_2": np.__version__ == "2.5.2",
        "torch_2_14_cpu": torch.__version__ == "2.14.0+cpu",
        "cuda_disabled": not torch.cuda.is_available(),
        "main_intraop_threads_one": torch.get_num_threads() == 1,
        "main_interop_threads_one": torch.get_num_interop_threads() == 1,
        "exactly_three_workers": workers == MAX_WORKERS,
    }
    return {"values": values, "gates": gates, "passes": all(gates.values())}


def _verify_recorded_inputs(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path_text, expected in manifest.get("input_sha256", {}).items():
        path = Path(path_text)
        live = sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "path": str(path),
                "expected_sha256": expected,
                "live_sha256": live,
                "matches": live == expected,
            }
        )
    return rows


def qualify_writer_source(root: Path) -> dict[str, Any]:
    output = root / "outputs" / WRITER_RUN
    run = root / "runs" / WRITER_RUN
    qualification_path = output / "qualification.json"
    manifest_path = run / "MANIFEST.json"
    status_path = run / "STATUS.json"
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    input_rows = _verify_recorded_inputs(manifest)
    output_rows = _read_hash_manifest(output / "output_hashes.sha256")
    parents = qualification.get("parents", [])
    founder = parents[0] if len(parents) == 4 else {}
    founder_checkpoint = Path(str(founder.get("checkpoint", "")))
    founder_carrier = np.asarray(founder.get("carrier", []), dtype=np.uint8)
    gates = {
        "run_id_exact": qualification.get("run_id") == WRITER_RUN
        and manifest.get("run_id") == WRITER_RUN,
        "qualification_passed": bool(qualification.get("overall_pass")),
        "status_complete": status.get("status") == "COMPLETE",
        "complete_sentinel_present": (run / "COMPLETE").is_file(),
        "all_recorded_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "all_recorded_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
        "four_parent_bank": len(parents) == 4,
        "founder_parent_zero": founder.get("parent") == 0,
        "founder_passed": bool(founder.get("passes")),
        "founder_checkpoint_exists": founder_checkpoint.is_file(),
        "founder_checkpoint_hash_exact": False,
        "founder_carrier_exactly_64_bytes": founder_carrier.shape == (1, 64)
        and founder_carrier.nbytes == 64,
        "founder_carrier_digest_exact": founder_carrier.shape == (1, 64)
        and carrier_digest(founder_carrier) == founder.get("carrier_sha256"),
    }
    # The source qualification records the checkpoint hash in its parent-bank
    # row rather than inside the per-parent writer result.
    parent_bank_rows = qualification.get("parent_bank", {}).get("parent_rows", [])
    founder_bank = next((row for row in parent_bank_rows if row.get("parent") == 0), {})
    gates["founder_checkpoint_hash_exact"] = bool(
        founder_checkpoint.is_file()
        and sha256_file(founder_checkpoint) == founder_bank.get("checkpoint_sha256")
        and founder_bank.get("checkpoint_hash_matches")
    )
    return {
        "qualification_path": str(qualification_path),
        "manifest_path": str(manifest_path),
        "status_path": str(status_path),
        "input_rows": input_rows,
        "output_rows": output_rows,
        "founder": founder,
        "founder_checkpoint": str(founder_checkpoint),
        "gates": gates,
        "passes": all(gates.values()),
    }


def initial_carriers(founder: np.ndarray) -> dict[str, np.ndarray]:
    wrong = permute_payloads(founder, np.asarray([0, 3, 2, 1], dtype=np.int64))
    lesion = corrupt_byte(founder, 20, mask=1)
    lesion = corrupt_byte(lesion, 52, mask=1)
    empty = empty_germ(1, GermSchema())
    return {
        "rewrite": founder.copy(),
        "stale_copy": founder.copy(),
        "writer_off": founder.copy(),
        "silence": empty,
        "wrong_frozen": wrong.copy(),
        "wrong_rewrite": wrong.copy(),
        "reader_off_rewrite": founder.copy(),
        "lesion_rewrite": lesion,
    }


def generation_specs(
    generation: int,
    carriers: Mapping[str, np.ndarray],
    parent_checkpoints: Mapping[str, Path],
    *,
    founder: np.ndarray,
    wrong: np.ndarray,
    empty: np.ndarray,
) -> list[dict[str, Any]]:
    seed = SEEDS[generation]
    enabled = {
        "rewrite",
        "stale_copy",
        "wrong_rewrite",
        "reader_off_rewrite",
        "lesion_rewrite",
    }
    specs: list[dict[str, Any]] = []
    for arm in ARMS:
        schedule_mode = "writer_candidate"
        fixed_next: np.ndarray | None = None
        fixed_label: str | None = None
        if arm == "stale_copy":
            schedule_mode = "fixed"
            fixed_next = founder
            fixed_label = "original_founder"
        elif arm == "writer_off":
            schedule_mode = "incoming"
        elif arm == "silence":
            schedule_mode = "fixed"
            fixed_next = empty
            fixed_label = "valid_empty"
        elif arm == "wrong_frozen":
            schedule_mode = "fixed"
            fixed_next = wrong
            fixed_label = "wrong_founder"
        spec: dict[str, Any] = {
            "generation": generation,
            "arm": arm,
            "birth_seed": seed["birth"],
            "training_seed": seed["training"],
            "writer_layout_seed": seed["writer_layout"],
            "writer_action_seed": seed["writer_action"],
            "germ_mode": "blind" if arm == "reader_off_rewrite" else "direct_prior",
            "writer_enabled": arm in enabled,
            "schedule_mode": schedule_mode,
            "incoming_germ": carriers[arm].tolist(),
            "parent_checkpoint": str(parent_checkpoints[arm]),
        }
        if fixed_next is not None:
            spec["fixed_next_germ"] = fixed_next.tolist()
            spec["fixed_source_label"] = fixed_label
        specs.append(spec)
    return specs


def exact_alias_audit(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_cell = {(int(row["generation"]), str(row["arm"])): row for row in results}

    def same(generation: int, arms: Sequence[str]) -> dict[str, Any]:
        fingerprints = {
            arm: by_cell[(generation, arm)]["behavior_fingerprint"] for arm in arms
        }
        return {
            "generation": generation,
            "arms": list(arms),
            "fingerprints": fingerprints,
            "exact": len(set(fingerprints.values())) == 1,
        }

    rows = [
        same(1, ("rewrite", "stale_copy", "writer_off")),
        *[same(generation, ("stale_copy", "writer_off")) for generation in GENERATIONS],
        same(1, ("wrong_frozen", "wrong_rewrite")),
        same(1, ("silence", "reader_off_rewrite", "lesion_rewrite")),
        *[
            same(generation, ("silence", "reader_off_rewrite"))
            for generation in GENERATIONS
        ],
    ]
    return {"comparisons": rows, "passes": all(row["exact"] for row in rows)}


def lineage_schedule_audit(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_cell = {(int(row["generation"]), str(row["arm"])): row for row in results}
    rows: list[dict[str, Any]] = []
    for arm in ARMS:
        for generation in (2, 3):
            parent = by_cell[(generation - 1, arm)]
            child = by_cell[(generation, arm)]
            rows.append(
                {
                    "arm": arm,
                    "boundary": f"G{generation - 1}->G{generation}",
                    "parent_scheduled_sha256": parent["scheduled_next_carrier_sha256"],
                    "child_incoming_sha256": child["incoming_carrier_sha256"],
                    "exact": parent["scheduled_next_carrier_sha256"]
                    == child["incoming_carrier_sha256"],
                }
            )
    return {"rows": rows, "passes": all(row["exact"] for row in rows)}


def cell_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    fixed = result["final_evaluations"]["fixed_random"]
    deterministic = result["final_evaluations"]["deterministic"]
    outgoing = np.asarray(result["scheduled_next_carrier"], dtype=np.uint8)
    outgoing_read = read_germ(outgoing)
    return {
        "generation": int(result["generation"]),
        "arm": str(result["arm"]),
        "incoming_carrier_sha256": result["incoming_carrier_sha256"],
        "incoming_active": result["incoming_decoded"]["active"][0],
        "incoming_targets": result["incoming_decoded"]["targets"][0],
        "training_event_counts": result["cumulative_event_counts"],
        "training_goal_successes": int(result["training_goal_successes"]),
        "fixed_chain": fixed["conditional_chain"],
        "fixed_successes": int(fixed["successes"]),
        "deterministic_successes": int(deterministic["successes"]),
        "deepest_fixed": _deepest_reached(fixed["conditional_chain"]),
        "learning_auc": result["learning_auc"],
        "writer_enabled": bool(result["writer"]["enabled"]),
        "writer_write_mask": result["writer"].get("renewal", {}).get("write_mask"),
        "writer_revocation_mask": result["writer"]
        .get("renewal", {})
        .get("revocation_mask"),
        "scheduled_next_source": result["scheduled_next_source"],
        "outgoing_carrier_sha256": result["scheduled_next_carrier_sha256"],
        "outgoing_active": outgoing_read.active[0].tolist(),
        "outgoing_targets": outgoing_read.prior_logits.argmax(axis=-1)[0].tolist(),
        "completed_cleanly": bool(result["completed_cleanly"]),
    }


def descriptive_contrasts(
    summaries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_cell = {(int(row["generation"]), str(row["arm"])): row for row in summaries}
    rows: list[dict[str, Any]] = []
    for generation in GENERATIONS:
        for comparator in ("silence", "wrong_frozen", "stale_copy"):
            primary = by_cell[(generation, "rewrite")]
            control = by_cell[(generation, comparator)]
            event_differences = {}
            for event in CAUSAL_CHAIN:
                left = primary["learning_auc"]["fixed_random"]["events"][event][
                    "reached_fraction_auc"
                ]
                right = control["learning_auc"]["fixed_random"]["events"][event][
                    "reached_fraction_auc"
                ]
                event_differences[event] = float(left - right)
            rows.append(
                {
                    "generation": generation,
                    "primary": "rewrite",
                    "comparator": comparator,
                    "fixed_random_reached_fraction_auc_difference": event_differences,
                    "training_goal_difference": int(primary["training_goal_successes"])
                    - int(control["training_goal_successes"]),
                    "final_fixed_goal_difference": int(primary["fixed_successes"])
                    - int(control["fixed_successes"]),
                }
            )
    return rows


def markdown_report(scout: Mapping[str, Any]) -> str:
    lines = [
        "# DoorKey vertical three-boundary carrier scout v1",
        "",
        "**Status:** `DEVELOPMENT SCOUT — NOT A CONFIRMATORY LAW TEST`  ",
        f"**Structural completion:** `{'PASS' if scout['completed_cleanly'] else 'FAIL'}`  ",
        "**Carrier at every boundary:** exactly `64 bytes`",
        "",
        "## Bottom line",
        "",
        (
            "Three fresh descendants were born in each of eight lineages. Actor/critic, "
            "auxiliary values, optimizers, recurrent/action/reward state, rollout state, "
            "writer scaffold, writer evidence, comparator, and private RNG state were "
            "audited at every boundary. Behavioral directions below are descriptive; "
            "they were not completion gates."
        ),
        "",
        "## Per-generation results",
        "",
        "| Gen | Arm | Train key/door/goal | Final fixed open/goal | Deepest fixed | Incoming active targets | Outgoing active targets |",
        "|---:|---|---:|---:|---|---|---|",
    ]
    for row in scout["cell_summaries"]:
        chain = {item["to"]: item for item in row["fixed_chain"]}
        events = row["training_event_counts"]
        incoming = [
            str(target) if active else "-"
            for active, target in zip(row["incoming_active"], row["incoming_targets"])
        ]
        outgoing = [
            str(target) if active else "-"
            for active, target in zip(row["outgoing_active"], row["outgoing_targets"])
        ]
        lines.append(
            f"| G{row['generation']} | `{row['arm']}` | "
            f"{events['key']}/{events['door']}/{events['goal']} | "
            f"{chain['open_door']['reached']}/{chain['reach_goal']['reached']} | "
            f"`{row['deepest_fixed']}` | `{'/'.join(incoming)}` | "
            f"`{'/'.join(outgoing)}` |"
        )
    lines.extend(["", "## Exact apparatus aliases", ""])
    for row in scout["exact_alias_audit"]["comparisons"]:
        lines.append(
            f"- G{row['generation']} `{' = '.join(row['arms'])}`: "
            f"`{'PASS' if row['exact'] else 'FAIL'}`"
        )
    lines.extend(["", "## Structural completion gates", ""])
    for name, passed in scout["completion_gates"].items():
        lines.append(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            (
                "This scout can support the narrow renewable-carrier clauses of L17 "
                "and L20 if the behavioral and rewrite pattern is coherent. It cannot "
                "establish learned ontology, learned addressing, a learning disposition "
                "rather than direct action shaping, or the universal wording of either law."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_scout(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if args.run_id != RUN_ID:
        raise ValueError(f"frozen run ID must be {RUN_ID}")
    if args.workers != MAX_WORKERS:
        raise ValueError(f"frozen scout requires exactly {MAX_WORKERS} workers")
    root = external_root(args.external_root)
    output_dir = root / "outputs" / args.run_id
    run_dir = root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    writer_output = root / "outputs" / WRITER_RUN
    writer_run = root / "runs" / WRITER_RUN
    source = qualify_writer_source(root)
    if not source["passes"]:
        raise RuntimeError(
            f"causal-writer source qualification failed: {source['gates']}"
        )
    founder_record = source["founder"]
    founder = np.asarray(founder_record["carrier"], dtype=np.uint8)
    founder_checkpoint = Path(source["founder_checkpoint"])
    config = FeedbackPPOConfig(**founder_record["config"])

    input_paths = [
        workspace / "protocols/DOORKEY_VERTICAL_THREE_BOUNDARY_SCOUT_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_scout.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_credit.py",
        workspace / "src/laws_confirmation/doorkey_causal_writer.py",
        workspace / "src/laws_confirmation/doorkey_causal_writer_qualification.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_vertical_scout.py",
        workspace / "scripts/run_doorkey_vertical_three_boundary_scout.sh",
        workspace / "scripts/run_doorkey_vertical_three_boundary_scout_detached.sh",
        writer_output / "qualification.json",
        writer_output / "audit.md",
        writer_output / "parent_world_rows.jsonl",
        writer_output / "input_hashes.sha256",
        writer_output / "output_hashes.sha256",
        writer_run / "MANIFEST.json",
        writer_run / "STATUS.json",
        writer_run / "COMPLETE",
        founder_checkpoint,
    ]
    input_paths = sorted({path.resolve() for path in input_paths})
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen vertical inputs: {missing}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    contract_digest = canonical_digest(input_hashes)
    disk = _disk_preflight(root, 64 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if args.resume:
        if not run_dir.is_dir() or not output_dir.is_dir():
            raise FileNotFoundError("cannot resume a run that has not been initialized")
        if (run_dir / "COMPLETE").is_file():
            print(output_dir / "audit.md")
            return 0
        old_manifest = json.loads(
            (run_dir / "MANIFEST.json").read_text(encoding="utf-8")
        )
        if (
            old_manifest.get("run_id") != args.run_id
            or old_manifest.get("contract_digest") != contract_digest
            or old_manifest.get("workers") != MAX_WORKERS
        ):
            raise RuntimeError("resume contract differs from initialized run")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        run_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "stage": "DoorKey vertical three-boundary carrier scout",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "external_root": str(root),
            "output_dir": str(output_dir),
            "input_sha256": input_hashes,
            "contract_digest": contract_digest,
            "repository_head": git_head(workspace),
            "workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "generations": len(GENERATIONS),
            "arms": list(ARMS),
            "registered_cells": len(GENERATIONS) * len(ARMS),
            "updates_per_cell": UPDATES,
            "transitions_per_cell": EXPECTED_STEPS,
            "registered_transitions": len(GENERATIONS) * len(ARMS) * EXPECTED_STEPS,
            "behavioral_completion_thresholds": 0,
            "disk_preflight": disk,
            "environment": environment_manifest(),
        }
        atomic_json(run_dir / "MANIFEST.json", manifest, root)
    atomic_json(
        run_dir / "STATUS.json",
        {
            "status": "RUNNING",
            "updated_utc": utc_now(),
            "run_id": args.run_id,
            "resume": bool(args.resume),
        },
        root,
    )

    try:
        runtime = runtime_qualification(args.workers)
        carriers = initial_carriers(founder)
        wrong = carriers["wrong_frozen"].copy()
        empty = carriers["silence"].copy()
        parent_checkpoints = {arm: founder_checkpoint for arm in ARMS}
        results: list[dict[str, Any]] = []
        generation_specs_record: list[dict[str, Any]] = []
        training_started = time.monotonic()
        for generation in GENERATIONS:
            specs = generation_specs(
                generation,
                carriers,
                parent_checkpoints,
                founder=founder,
                wrong=wrong,
                empty=empty,
            )
            generation_specs_record.extend(specs)
            generation_results: list[dict[str, Any]] = []
            context = multiprocessing.get_context("spawn")
            with ProcessPoolExecutor(
                max_workers=MAX_WORKERS, mp_context=context
            ) as executor:
                future_to_spec = {
                    executor.submit(
                        _worker_train_cell,
                        spec,
                        asdict(config),
                        str(root),
                        str(output_dir),
                    ): spec
                    for spec in specs
                }
                for future in as_completed(future_to_spec):
                    spec = future_to_spec[future]
                    try:
                        generation_results.append(future.result())
                    except Exception as error:
                        raise RuntimeError(
                            f"G{generation} {spec['arm']} worker failed"
                        ) from error
            generation_results.sort(key=lambda row: ARMS.index(str(row["arm"])))
            if [row["arm"] for row in generation_results] != list(ARMS):
                raise RuntimeError(f"G{generation} returned an incomplete arm set")
            results.extend(generation_results)
            for result in generation_results:
                arm = str(result["arm"])
                carriers[arm] = np.asarray(
                    result["scheduled_next_carrier"], dtype=np.uint8
                )
                parent_checkpoints[arm] = (
                    output_dir / f"g{generation}_{arm}_checkpoint.pt"
                )
            atomic_json(
                output_dir / "lineage_progress.json",
                {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    "completed_generations": generation,
                    "completed_cells": len(results),
                    "scheduled_carrier_sha256": {
                        arm: carrier_digest(carriers[arm]) for arm in ARMS
                    },
                },
                root,
            )
        elapsed_training = time.monotonic() - training_started
        results.sort(
            key=lambda row: (int(row["generation"]), ARMS.index(str(row["arm"])))
        )
        aliases = exact_alias_audit(results)
        schedule = lineage_schedule_audit(results)
        summaries = [cell_summary(row) for row in results]
        contrasts = descriptive_contrasts(summaries)
        completion_gates = {
            "runtime_qualified": bool(runtime["passes"]),
            "writer_source_qualified": bool(source["passes"]),
            "exactly_24_registered_cells": len(results) == 24
            and len({(row["generation"], row["arm"]) for row in results}) == 24,
            "all_cells_completed_cleanly": all(
                bool(row["completed_cleanly"]) for row in results
            ),
            "all_cells_100_updates": all(row["updates"] == UPDATES for row in results),
            "all_cells_expected_transitions": all(
                row["environment_steps"] == EXPECTED_STEPS for row in results
            ),
            "all_24_boundaries_reset": all(
                row["boundary_audit"]["passes"] for row in results
            ),
            "all_birth_packets_exactly_64_bytes": all(
                np.asarray(row["incoming_carrier"], dtype=np.uint8).nbytes == 64
                for row in results
            ),
            "all_scheduled_packets_exactly_64_bytes": all(
                np.asarray(row["scheduled_next_carrier"], dtype=np.uint8).nbytes == 64
                for row in results
            ),
            "lineage_schedule_exact": bool(schedule["passes"]),
            "all_writer_transactions_valid_and_replayed": all(
                bool(row["writer"]["passes"])
                for row in results
                if row["writer"]["enabled"]
            ),
            "all_designed_behavioral_aliases_exact": bool(aliases["passes"]),
            "three_workers_one_thread": args.workers == MAX_WORKERS
            and runtime["values"]["torch_num_threads"] == 1,
            "all_metrics_finite": all(
                _finite_credit_history(row["history"]) for row in results
            ),
            "all_final_evaluations_replay_exactly": all(
                row["completion_gates"]["final_evaluations_replay_exactly"]
                for row in results
            ),
            "all_checkpoints_reload": all(
                row["completion_gates"]["checkpoint_reloads_with_leak_probe"]
                for row in results
            ),
            "no_behavioral_direction_used_as_gate": True,
        }
        scout = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "OUTCOME_OPEN_DEVELOPMENT_SCOUT",
            "runtime": runtime,
            "writer_source": source,
            "config": asdict(config),
            "seeds": SEEDS,
            "arms": list(ARMS),
            "generations": list(GENERATIONS),
            "founder_carrier_sha256": carrier_digest(founder),
            "wrong_founder_carrier_sha256": carrier_digest(wrong),
            "empty_carrier_sha256": carrier_digest(empty),
            "generation_specs": generation_specs_record,
            "cell_result_files": [
                str(output_dir / f"g{row['generation']}_{row['arm']}.json")
                for row in results
            ],
            "cell_summaries": summaries,
            "descriptive_contrasts": contrasts,
            "exact_alias_audit": aliases,
            "lineage_schedule_audit": schedule,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "registered_transitions": 24 * EXPECTED_STEPS,
            "elapsed_training_seconds": elapsed_training,
            "max_workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output_dir / "scout.json", scout, root)
        atomic_text(output_dir / "audit.md", markdown_report(scout), root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", root)
        output_paths = sorted(
            path.resolve()
            for path in output_dir.rglob("*")
            if path.is_file() and path.name != "output_hashes.sha256"
        )
        write_hash_manifest(output_paths, output_dir / "output_hashes.sha256", root)
        output_rows = _read_hash_manifest(output_dir / "output_hashes.sha256")
        outputs_verify = bool(output_rows) and all(
            row["matches"] for row in output_rows
        )
        status_ok = bool(scout["completed_cleanly"] and outputs_verify)
        status = {
            "status": "COMPLETE" if status_ok else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "completed_cleanly": bool(scout["completed_cleanly"]),
            "output_manifest_self_verifies": outputs_verify,
            "registered_cells": 24,
            "registered_transitions": 24 * EXPECTED_STEPS,
            "max_workers": MAX_WORKERS,
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
        }
        atomic_json(run_dir / "STATUS.json", status, root)
        sentinel = "COMPLETE" if status_ok else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", root)
        print(output_dir / "audit.md")
        return 0 if status_ok else 1
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> int:
    return run_scout(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
