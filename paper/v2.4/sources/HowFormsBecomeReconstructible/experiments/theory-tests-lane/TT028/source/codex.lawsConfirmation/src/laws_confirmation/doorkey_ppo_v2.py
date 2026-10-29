"""DoorKey recurrent PPO v2 with explicit previous-action/reward feedback.

Version 1 is retained in :mod:`laws_confirmation.doorkey_ppo` as the exact
learner used by the first germ-blind scout.  This module changes only somatic
learner state and evaluation: the environment and 64-byte germ are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
import json
import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .doorkey_boundary import BoundaryPacket, make_boundary_packet
from .doorkey_carrier import GermSchema, empty_germ, read_germ
from .doorkey_env import CAUSAL_CHAIN, DoorKeyEnv, TRANSFORMS, make_layout
from .doorkey_ppo import DoorKeyGermWriter, DoorKeyVectorEnv, PPOConfig


START_ACTION = 8


@dataclass(frozen=True)
class FeedbackPPOConfig(PPOConfig):
    action_embedding_size: int = 8
    previous_reward_clip: float = 2.0

    def validate(self) -> None:
        super().validate()
        if self.action_embedding_size < 1:
            raise ValueError("action_embedding_size must be positive")
        if self.previous_reward_clip <= 0:
            raise ValueError("previous_reward_clip must be positive")


class FeedbackRecurrentActorCritic(nn.Module):
    """Recurrent policy whose transition observes its last action and reward."""

    def __init__(self, config: FeedbackPPOConfig) -> None:
        super().__init__()
        config.validate()
        self.config = config
        self.tile_embedding = nn.Embedding(
            config.tile_vocab, config.tile_embedding_size
        )
        self.action_embedding = nn.Embedding(
            config.num_actions + 1, config.action_embedding_size
        )
        encoder_width = (
            config.tile_positions * config.tile_embedding_size
            + config.scalar_features
            + config.action_embedding_size
            + 1
        )
        self.encoder = nn.Sequential(
            nn.Linear(encoder_width, config.hidden_size),
            nn.Tanh(),
        )
        self.recurrent = nn.GRUCell(config.hidden_size, config.hidden_size)
        self.actor = nn.Linear(config.hidden_size, config.num_actions)
        self.critic = nn.Linear(config.hidden_size, 1)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.normal_(self.tile_embedding.weight, mean=0.0, std=0.05)
        nn.init.normal_(self.action_embedding.weight, mean=0.0, std=0.05)
        for module in self.modules():
            if isinstance(module, nn.Linear):
                gain = math.sqrt(2.0)
                if module is self.actor:
                    gain = 0.01
                elif module is self.critic:
                    gain = 1.0
                nn.init.orthogonal_(module.weight, gain=gain)
                nn.init.zeros_(module.bias)
        for name, parameter in self.recurrent.named_parameters():
            if "weight" in name:
                nn.init.orthogonal_(parameter, gain=1.0)
            else:
                nn.init.zeros_(parameter)

    def encode(
        self,
        observations: torch.Tensor,
        previous_actions: torch.Tensor,
        previous_rewards: torch.Tensor,
        episode_start: torch.Tensor,
    ) -> torch.Tensor:
        config = self.config
        if observations.ndim != 2 or observations.shape[1] != config.observation_width:
            raise ValueError("observations must have shape [batch, 13]")
        batch = observations.shape[0]
        if previous_actions.shape != (batch,) or previous_rewards.shape != (batch,):
            raise ValueError("previous action/reward must have shape [batch]")
        if episode_start.shape != (batch,):
            raise ValueError("episode_start must have shape [batch]")
        tiles = observations[:, : config.tile_positions].round().long()
        tiles = tiles.clamp(0, config.tile_vocab - 1)
        embedded_tiles = self.tile_embedding(tiles).flatten(start_dim=1)
        scalars = observations[:, config.tile_positions :]
        reset = episode_start.bool()
        action = torch.where(
            reset,
            torch.full_like(previous_actions, START_ACTION),
            previous_actions,
        ).long()
        if torch.any((action < 0) | (action > START_ACTION)):
            raise ValueError("previous action lies outside action/sentinel range")
        reward = torch.where(
            reset, torch.zeros_like(previous_rewards), previous_rewards
        ).clamp(-config.previous_reward_clip, config.previous_reward_clip)
        embedded_action = self.action_embedding(action)
        return self.encoder(
            torch.cat(
                (embedded_tiles, scalars, embedded_action, reward[:, None]), dim=1
            )
        )

    def forward_step(
        self,
        observations: torch.Tensor,
        hidden: torch.Tensor,
        episode_start: torch.Tensor,
        previous_actions: torch.Tensor,
        previous_rewards: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        batch = observations.shape[0]
        if hidden.shape != (batch, self.config.hidden_size):
            raise ValueError("hidden state has the wrong shape")
        reset = episode_start.bool()
        retained_hidden = hidden * (~reset).to(hidden.dtype)[:, None]
        encoded = self.encode(
            observations,
            previous_actions,
            previous_rewards,
            episode_start,
        )
        next_hidden = self.recurrent(encoded, retained_hidden)
        return (
            self.actor(next_hidden),
            self.critic(next_hidden).squeeze(-1),
            next_hidden,
        )

    def forward_sequence(
        self,
        observations: torch.Tensor,
        initial_hidden: torch.Tensor,
        episode_starts: torch.Tensor,
        previous_actions: torch.Tensor,
        previous_rewards: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if observations.ndim != 3:
            raise ValueError("observations must have shape [time, batch, obs]")
        expected = observations.shape[:2]
        if any(value.shape != expected for value in (episode_starts, previous_actions, previous_rewards)):
            raise ValueError("sequence feedback tensors have the wrong shape")
        hidden = initial_hidden
        logits: list[torch.Tensor] = []
        values: list[torch.Tensor] = []
        for step in range(observations.shape[0]):
            step_logits, step_values, hidden = self.forward_step(
                observations[step],
                hidden,
                episode_starts[step],
                previous_actions[step],
                previous_rewards[step],
            )
            logits.append(step_logits)
            values.append(step_values)
        return torch.stack(logits), torch.stack(values), hidden


@dataclass
class FeedbackRolloutBatch:
    observations: torch.Tensor
    previous_actions: torch.Tensor
    previous_rewards: torch.Tensor
    actions: torch.Tensor
    old_log_probabilities: torch.Tensor
    rewards: torch.Tensor
    dones: torch.Tensor
    episode_starts: torch.Tensor
    old_values: torch.Tensor
    advantages: torch.Tensor
    returns: torch.Tensor
    initial_hidden: torch.Tensor


@dataclass
class FeedbackPPODescendant:
    germ: np.ndarray
    birth_seed: int
    public_rulebook_digest: str
    model: FeedbackRecurrentActorCritic
    writer: DoorKeyGermWriter
    optimizer: torch.optim.Optimizer
    writer_optimizer: torch.optim.Optimizer
    recurrent_hidden: torch.Tensor
    previous_actions: torch.Tensor
    previous_rewards: torch.Tensor
    rollout_state: FeedbackRolloutBatch | None
    numpy_rng: np.random.Generator
    torch_generator: torch.Generator
    normalization_state: None
    curriculum_state: None
    population_statistics: None

    def refresh_carrier(self) -> tuple[torch.Tensor, torch.Tensor]:
        decoded = read_germ(self.germ, GermSchema())
        device = next(self.model.parameters()).device
        return (
            torch.from_numpy(decoded.prior_logits[0].copy()).to(device),
            torch.from_numpy(decoded.active[0].copy()).to(device),
        )


def birth_feedback_ppo_descendant(
    packet: BoundaryPacket,
    config: FeedbackPPOConfig,
    birth_seed: int,
    device: str | torch.device = "cpu",
) -> FeedbackPPODescendant:
    """Fresh v2 soma; no parent learner or trajectory state is accepted."""

    config.validate()
    if not 0 <= birth_seed < 2**63:
        raise ValueError("birth_seed must be in [0, 2^63)")
    target = torch.device(device)
    if target.type != "cpu":
        raise ValueError("DoorKey feedback v1 is frozen to CPU")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(birth_seed)
        model = FeedbackRecurrentActorCritic(config).to(target)
        writer = DoorKeyGermWriter(config).to(target)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    writer_optimizer = torch.optim.Adam(
        writer.parameters(), lr=config.writer_learning_rate
    )
    generator = torch.Generator(device=target)
    generator.manual_seed(birth_seed + 1_000_000_007)
    return FeedbackPPODescendant(
        germ=np.frombuffer(packet.payload, dtype=np.uint8).copy().reshape(1, 64),
        birth_seed=int(birth_seed),
        public_rulebook_digest=config.digest(),
        model=model,
        writer=writer,
        optimizer=optimizer,
        writer_optimizer=writer_optimizer,
        recurrent_hidden=torch.zeros(
            (config.num_envs, config.hidden_size), dtype=torch.float32, device=target
        ),
        previous_actions=torch.full(
            (config.num_envs,), START_ACTION, dtype=torch.long, device=target
        ),
        previous_rewards=torch.zeros(
            config.num_envs, dtype=torch.float32, device=target
        ),
        rollout_state=None,
        numpy_rng=np.random.default_rng(birth_seed + 2_000_000_011),
        torch_generator=generator,
        normalization_state=None,
        curriculum_state=None,
        population_statistics=None,
    )


def make_empty_feedback_descendant(
    config: FeedbackPPOConfig, birth_seed: int
) -> FeedbackPPODescendant:
    schema = GermSchema()
    return birth_feedback_ppo_descendant(
        make_boundary_packet(empty_germ(1, schema), schema), config, birth_seed
    )


def _tensor_digest(tensor: torch.Tensor) -> str:
    array = tensor.detach().cpu().contiguous().numpy()
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _module_digest(module: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(module.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(_tensor_digest(value).encode("ascii"))
    return digest.hexdigest()


def _generator_digest(generator: torch.Generator) -> str:
    return _tensor_digest(generator.get_state())


def _numpy_generator_digest(generator: np.random.Generator) -> str:
    payload = json.dumps(
        generator.bit_generator.state,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda value: value.tolist()
        if isinstance(value, np.ndarray)
        else int(value),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def feedback_learner_digests(
    descendant: FeedbackPPODescendant,
) -> dict[str, str]:
    return {
        "actor_critic": _module_digest(descendant.model),
        "writer": _module_digest(descendant.writer),
        "hidden": _tensor_digest(descendant.recurrent_hidden),
        "previous_actions": _tensor_digest(descendant.previous_actions),
        "previous_rewards": _tensor_digest(descendant.previous_rewards),
        "torch_generator": _generator_digest(descendant.torch_generator),
        "numpy_generator": _numpy_generator_digest(descendant.numpy_rng),
    }


def _optimizer_tensor_count(optimizer: torch.optim.Optimizer) -> int:
    return sum(
        isinstance(value, torch.Tensor)
        for state in optimizer.state.values()
        for value in state.values()
    )


def prime_feedback_parent_for_boundary_audit(
    descendant: FeedbackPPODescendant, marker: float
) -> None:
    if not math.isfinite(marker) or marker == 0:
        raise ValueError("marker must be finite and nonzero")
    config = descendant.model.config
    descendant.optimizer.zero_grad(set_to_none=True)
    sum(parameter.square().mean() for parameter in descendant.model.parameters()).backward()
    descendant.optimizer.step()
    descendant.writer_optimizer.zero_grad(set_to_none=True)
    sum(parameter.square().mean() for parameter in descendant.writer.parameters()).backward()
    descendant.writer_optimizer.step()
    descendant.recurrent_hidden.fill_(marker)
    descendant.previous_actions.fill_(int(abs(marker)) % config.num_actions)
    descendant.previous_rewards.fill_(marker)
    time_steps = 2
    zeros = torch.zeros((time_steps, config.num_envs), dtype=torch.float32)
    descendant.rollout_state = FeedbackRolloutBatch(
        observations=torch.full(
            (time_steps, config.num_envs, config.observation_width),
            marker,
            dtype=torch.float32,
        ),
        previous_actions=torch.zeros_like(zeros, dtype=torch.long),
        previous_rewards=torch.full_like(zeros, marker),
        actions=torch.zeros_like(zeros, dtype=torch.long),
        old_log_probabilities=zeros,
        rewards=zeros,
        dones=zeros.bool(),
        episode_starts=zeros.bool(),
        old_values=zeros,
        advantages=zeros,
        returns=zeros,
        initial_hidden=torch.full_like(descendant.recurrent_hidden, marker),
    )
    descendant.numpy_rng.random(257)
    torch.rand(257, generator=descendant.torch_generator)


def audit_feedback_boundary(
    parent: FeedbackPPODescendant,
    child: FeedbackPPODescendant,
    packet: BoundaryPacket,
) -> dict[str, Any]:
    birth_parameters = tuple(
        inspect.signature(birth_feedback_ppo_descendant).parameters
    )
    rows: dict[str, dict[str, Any]] = {
        "actor_critic_parameters": {
            "parent_digest": _module_digest(parent.model),
            "child_digest": _module_digest(child.model),
            "reset": _module_digest(parent.model) != _module_digest(child.model),
        },
        "writer_parameters": {
            "parent_digest": _module_digest(parent.writer),
            "child_digest": _module_digest(child.writer),
            "reset": _module_digest(parent.writer) != _module_digest(child.writer),
        },
        "ppo_optimizer": {
            "parent_tensor_count": _optimizer_tensor_count(parent.optimizer),
            "child_tensor_count": _optimizer_tensor_count(child.optimizer),
            "reset": _optimizer_tensor_count(parent.optimizer) > 0
            and _optimizer_tensor_count(child.optimizer) == 0,
        },
        "writer_optimizer": {
            "parent_tensor_count": _optimizer_tensor_count(parent.writer_optimizer),
            "child_tensor_count": _optimizer_tensor_count(child.writer_optimizer),
            "reset": _optimizer_tensor_count(parent.writer_optimizer) > 0
            and _optimizer_tensor_count(child.writer_optimizer) == 0,
        },
        "rollout_state": {
            "parent_present": parent.rollout_state is not None,
            "child_present": child.rollout_state is not None,
            "reset": parent.rollout_state is not None and child.rollout_state is None,
        },
        "recurrent_state": {
            "parent_nonzero": bool(torch.count_nonzero(parent.recurrent_hidden)),
            "child_nonzero": bool(torch.count_nonzero(child.recurrent_hidden)),
            "memory_shared": parent.recurrent_hidden.data_ptr()
            == child.recurrent_hidden.data_ptr(),
            "reset": bool(torch.count_nonzero(parent.recurrent_hidden))
            and not bool(torch.count_nonzero(child.recurrent_hidden))
            and parent.recurrent_hidden.data_ptr() != child.recurrent_hidden.data_ptr(),
        },
        "previous_action_state": {
            "parent_all_start": bool(
                torch.all(parent.previous_actions == START_ACTION)
            ),
            "child_all_start": bool(torch.all(child.previous_actions == START_ACTION)),
            "memory_shared": parent.previous_actions.data_ptr()
            == child.previous_actions.data_ptr(),
            "reset": not bool(torch.all(parent.previous_actions == START_ACTION))
            and bool(torch.all(child.previous_actions == START_ACTION))
            and parent.previous_actions.data_ptr() != child.previous_actions.data_ptr(),
        },
        "previous_reward_state": {
            "parent_nonzero": bool(torch.count_nonzero(parent.previous_rewards)),
            "child_nonzero": bool(torch.count_nonzero(child.previous_rewards)),
            "memory_shared": parent.previous_rewards.data_ptr()
            == child.previous_rewards.data_ptr(),
            "reset": bool(torch.count_nonzero(parent.previous_rewards))
            and not bool(torch.count_nonzero(child.previous_rewards))
            and parent.previous_rewards.data_ptr() != child.previous_rewards.data_ptr(),
        },
        "rng_state": {
            "parent_torch_digest": _generator_digest(parent.torch_generator),
            "child_torch_digest": _generator_digest(child.torch_generator),
            "parent_numpy_digest": _numpy_generator_digest(parent.numpy_rng),
            "child_numpy_digest": _numpy_generator_digest(child.numpy_rng),
            "reset": _generator_digest(parent.torch_generator)
            != _generator_digest(child.torch_generator)
            and _numpy_generator_digest(parent.numpy_rng)
            != _numpy_generator_digest(child.numpy_rng),
        },
        "normalization_state": {"status": "absent_by_design", "reset": True},
        "curriculum_state": {"status": "absent_by_design", "reset": True},
        "population_statistics": {"status": "absent_by_design", "reset": True},
        "global_rng_state": {
            "status": "avoided_by_fork_rng_and_private_generators",
            "reset": True,
        },
    }
    child_carrier = child.germ[0].tobytes(order="C")
    gates = {
        "birth_api_has_no_parent_argument": birth_parameters
        == ("packet", "config", "birth_seed", "device"),
        "packet_is_exactly_64_bytes": len(packet.payload) == 64,
        "carrier_exactly_preserved": child_carrier == packet.payload,
        "public_rulebook_unchanged": (
            parent.public_rulebook_digest == child.public_rulebook_digest
        ),
        "all_somatic_state_reset": all(bool(row["reset"]) for row in rows.values()),
    }
    return {
        "birth_api_parameters": list(birth_parameters),
        "state_rows": rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def _carrier_prior(
    descendant: FeedbackPPODescendant,
    observations: torch.Tensor,
    mode: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    if mode not in ("blind", "direct_prior"):
        raise ValueError(f"unknown germ mode: {mode}")
    batch = observations.shape[0]
    if mode == "blind":
        return (
            torch.zeros(
                (batch, descendant.model.config.num_actions),
                dtype=observations.dtype,
                device=observations.device,
            ),
            torch.zeros(batch, dtype=torch.bool, device=observations.device),
        )
    slot_logits, slot_active = descendant.refresh_carrier()
    tiles = observations[:, :9].round().long()
    has_key = observations[:, 9] > 0.5
    standing_on_key = observations[:, 10] > 0.5
    key_visible = (tiles == DoorKeyEnv.KEY).any(dim=1) | standing_on_key
    door_visible = (
        (tiles == DoorKeyEnv.DOOR_CLOSED) | (tiles == DoorKeyEnv.DOOR_OPEN)
    ).any(dim=1)
    context = torch.zeros(batch, dtype=torch.long, device=observations.device)
    context = torch.where(~has_key & key_visible, torch.ones_like(context), context)
    context = torch.where(has_key, torch.full_like(context, 2), context)
    context = torch.where(has_key & door_visible, torch.full_like(context, 3), context)
    return slot_logits[context], slot_active[context]


def _apply_prior(
    logits: torch.Tensor,
    descendant: FeedbackPPODescendant,
    observations: torch.Tensor,
    germ_mode: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    prior, active = _carrier_prior(descendant, observations, germ_mode)
    return (
        logits
        + prior
        * active.to(logits.dtype)[:, None]
        * descendant.model.config.germ_logit_scale,
        active,
    )


def collect_feedback_rollout(
    descendant: FeedbackPPODescendant,
    environments: DoorKeyVectorEnv,
    config: FeedbackPPOConfig,
    germ_mode: str,
) -> tuple[FeedbackRolloutBatch, list[dict[str, Any]]]:
    config.validate()
    device = next(descendant.model.parameters()).device
    observations_np = environments.observations()
    hidden = descendant.recurrent_hidden.detach()
    previous_action = descendant.previous_actions.detach()
    previous_reward = descendant.previous_rewards.detach()
    initial_hidden = hidden.clone()
    episode_start_np = environments.episode_starts.copy()
    observations: list[torch.Tensor] = []
    previous_actions: list[torch.Tensor] = []
    previous_rewards: list[torch.Tensor] = []
    actions: list[torch.Tensor] = []
    log_probabilities: list[torch.Tensor] = []
    rewards: list[torch.Tensor] = []
    dones: list[torch.Tensor] = []
    episode_starts: list[torch.Tensor] = []
    values: list[torch.Tensor] = []
    descendant.model.eval()

    for _ in range(config.rollout_steps):
        observation = torch.from_numpy(observations_np).to(
            device=device, dtype=torch.float32
        )
        episode_start = torch.from_numpy(episode_start_np).to(device=device)
        with torch.no_grad():
            base_logits, value, next_hidden = descendant.model.forward_step(
                observation,
                hidden,
                episode_start,
                previous_action,
                previous_reward,
            )
            logits, _ = _apply_prior(
                base_logits, descendant, observation, germ_mode
            )
            log_probs = F.log_softmax(logits, dim=-1)
            probabilities = log_probs.exp()
            action = torch.multinomial(
                probabilities, 1, generator=descendant.torch_generator
            ).squeeze(1)
            chosen_log_probability = log_probs.gather(1, action[:, None]).squeeze(1)
        next_observations, reward_np, done_np, _ = environments.step(
            action.detach().cpu().numpy()
        )
        reward = torch.from_numpy(reward_np).to(device)
        done = torch.from_numpy(done_np).to(device)
        observations.append(observation)
        previous_actions.append(previous_action)
        previous_rewards.append(previous_reward)
        actions.append(action)
        log_probabilities.append(chosen_log_probability)
        rewards.append(reward)
        dones.append(done)
        episode_starts.append(episode_start)
        values.append(value)

        hidden = next_hidden.detach()
        hidden[done] = 0.0
        previous_action = action.detach().clone()
        previous_reward = reward.detach().clone()
        previous_action[done] = START_ACTION
        previous_reward[done] = 0.0
        observations_np = next_observations
        episode_start_np = done_np

    next_observation = torch.from_numpy(observations_np).to(
        device=device, dtype=torch.float32
    )
    next_episode_start = torch.from_numpy(episode_start_np).to(device=device)
    with torch.no_grad():
        _, next_value, _ = descendant.model.forward_step(
            next_observation,
            hidden,
            next_episode_start,
            previous_action,
            previous_reward,
        )
    reward_tensor = torch.stack(rewards)
    done_tensor = torch.stack(dones)
    value_tensor = torch.stack(values)
    advantages = torch.zeros_like(reward_tensor)
    last_advantage = torch.zeros(config.num_envs, device=device)
    for step in reversed(range(config.rollout_steps)):
        nonterminal = (~done_tensor[step]).to(torch.float32)
        following_value = (
            next_value
            if step == config.rollout_steps - 1
            else value_tensor[step + 1]
        )
        delta = (
            reward_tensor[step]
            + config.gamma * following_value * nonterminal
            - value_tensor[step]
        )
        last_advantage = (
            delta
            + config.gamma * config.gae_lambda * nonterminal * last_advantage
        )
        advantages[step] = last_advantage
    batch = FeedbackRolloutBatch(
        observations=torch.stack(observations),
        previous_actions=torch.stack(previous_actions),
        previous_rewards=torch.stack(previous_rewards),
        actions=torch.stack(actions),
        old_log_probabilities=torch.stack(log_probabilities),
        rewards=reward_tensor,
        dones=done_tensor,
        episode_starts=torch.stack(episode_starts),
        old_values=value_tensor,
        advantages=advantages,
        returns=advantages + value_tensor,
        initial_hidden=initial_hidden,
    )
    descendant.recurrent_hidden = hidden
    descendant.previous_actions = previous_action
    descendant.previous_rewards = previous_reward
    descendant.rollout_state = batch
    return batch, environments.pop_completed()


def feedback_ppo_update(
    descendant: FeedbackPPODescendant,
    rollout: FeedbackRolloutBatch,
    config: FeedbackPPOConfig,
    germ_mode: str,
) -> dict[str, float]:
    descendant.model.train()
    normalized_advantage = (rollout.advantages - rollout.advantages.mean()) / (
        rollout.advantages.std(unbiased=False) + 1e-8
    )
    collected: dict[str, list[float]] = {
        "policy_loss": [],
        "value_loss": [],
        "entropy": [],
        "approx_kl": [],
        "clip_fraction": [],
        "grad_norm": [],
    }
    for _ in range(config.ppo_epochs):
        order = descendant.numpy_rng.permutation(config.num_envs)
        for start in range(0, config.num_envs, config.minibatch_envs):
            indices = torch.as_tensor(
                order[start : start + config.minibatch_envs],
                dtype=torch.long,
                device=rollout.observations.device,
            )
            observations = rollout.observations[:, indices]
            logits, values, _ = descendant.model.forward_sequence(
                observations,
                rollout.initial_hidden[indices],
                rollout.episode_starts[:, indices],
                rollout.previous_actions[:, indices],
                rollout.previous_rewards[:, indices],
            )
            flat_observations = observations.reshape(-1, config.observation_width)
            flat_logits, _ = _apply_prior(
                logits.reshape(-1, config.num_actions),
                descendant,
                flat_observations,
                germ_mode,
            )
            log_probs = F.log_softmax(flat_logits, dim=-1)
            probabilities = log_probs.exp()
            actions = rollout.actions[:, indices].reshape(-1)
            new_log_probability = log_probs.gather(1, actions[:, None]).squeeze(1)
            old_log_probability = rollout.old_log_probabilities[:, indices].reshape(-1)
            advantage = normalized_advantage[:, indices].reshape(-1)
            ratio = torch.exp(new_log_probability - old_log_probability)
            clipped_ratio = torch.clamp(
                ratio, 1.0 - config.clip_epsilon, 1.0 + config.clip_epsilon
            )
            policy_loss = -torch.minimum(
                ratio * advantage, clipped_ratio * advantage
            ).mean()
            value_loss = 0.5 * F.mse_loss(
                values.reshape(-1), rollout.returns[:, indices].reshape(-1)
            )
            entropy = -(probabilities * log_probs).sum(dim=-1).mean()
            loss = (
                policy_loss
                + config.value_coefficient * value_loss
                - config.entropy_coefficient * entropy
            )
            descendant.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            grad_norm = nn.utils.clip_grad_norm_(
                descendant.model.parameters(), config.max_grad_norm
            )
            descendant.optimizer.step()
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
                ("entropy", entropy),
                ("approx_kl", approx_kl),
                ("clip_fraction", clip_fraction),
                ("grad_norm", grad_norm),
            ):
                collected[name].append(float(value.detach()))
    return {name: float(np.mean(values)) for name, values in collected.items()}


def _router_contexts(observations: torch.Tensor) -> torch.Tensor:
    tiles = observations[:, :9].round().long()
    has_key = observations[:, 9] > 0.5
    key_visible = (tiles == DoorKeyEnv.KEY).any(dim=1) | (observations[:, 10] > 0.5)
    door_visible = (
        (tiles == DoorKeyEnv.DOOR_CLOSED) | (tiles == DoorKeyEnv.DOOR_OPEN)
    ).any(dim=1)
    context = torch.zeros(observations.shape[0], dtype=torch.long, device=observations.device)
    context = torch.where(~has_key & key_visible, torch.ones_like(context), context)
    context = torch.where(has_key, torch.full_like(context, 2), context)
    return torch.where(has_key & door_visible, torch.full_like(context, 3), context)


def _conditional_chain(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    previous: str | None = None
    for event in CAUSAL_CHAIN:
        eligible = [
            row
            for row in rows
            if previous is None or row["event_steps"][previous] is not None
        ]
        reached = [row for row in eligible if row["event_steps"][event] is not None]
        result.append(
            {
                "from": "episode_start" if previous is None else previous,
                "to": event,
                "eligible": len(eligible),
                "reached": len(reached),
                "conditional_probability": float(len(reached) / len(eligible))
                if eligible
                else None,
            }
        )
        previous = event
    return result


def evaluate_feedback_policy(
    descendant: FeedbackPPODescendant,
    config: FeedbackPPOConfig,
    *,
    germ_mode: str,
    feedback_reward_mode: str,
    action_mode: str,
    worlds_per_transform: int = 8,
    seed_base: int = 70_000_000,
    action_seed: int = 71_000_000,
    stochastic_repeats: int = 4,
) -> dict[str, Any]:
    """Evaluate argmax or fixed-common-uniform stochastic behavior."""

    if action_mode not in ("deterministic", "fixed_random"):
        raise ValueError("action_mode must be deterministic or fixed_random")
    if feedback_reward_mode not in ("terminal", "stage_shaped"):
        raise ValueError("invalid feedback reward mode")
    repeats = 1 if action_mode == "deterministic" else stochastic_repeats
    if repeats < 1:
        raise ValueError("stochastic_repeats must be positive")
    envs: list[DoorKeyEnv] = []
    stream_ids: list[int] = []
    for transform_index, transform in enumerate(TRANSFORMS):
        for local_seed in range(worlds_per_transform):
            seed = seed_base + transform_index * 10_000 + local_seed
            for stream in range(repeats):
                envs.append(
                    DoorKeyEnv(
                        make_layout(seed, transform),
                        max_steps=config.max_episode_steps,
                    )
                )
                stream_ids.append(stream)
    count = len(envs)
    device = next(descendant.model.parameters()).device
    hidden = torch.zeros((count, config.hidden_size), dtype=torch.float32, device=device)
    previous_action = torch.full(
        (count,), START_ACTION, dtype=torch.long, device=device
    )
    previous_reward = torch.zeros(count, dtype=torch.float32, device=device)
    episode_start = torch.ones(count, dtype=torch.bool, device=device)
    active = np.ones(count, dtype=bool)
    early_action_counts = np.zeros((4, 8), dtype=np.int64)
    early_context_counts = np.zeros(4, dtype=np.int64)
    uniforms = np.random.default_rng(action_seed).random(
        (config.max_episode_steps, count)
    )
    descendant.model.eval()

    for step in range(config.max_episode_steps):
        observations_np = np.stack([env.observation().vector() for env in envs])
        observations = torch.from_numpy(observations_np).to(
            device=device, dtype=torch.float32
        )
        with torch.no_grad():
            base_logits, _, next_hidden = descendant.model.forward_step(
                observations,
                hidden,
                episode_start,
                previous_action,
                previous_reward,
            )
            logits, _ = _apply_prior(
                base_logits, descendant, observations, germ_mode
            )
            if action_mode == "deterministic":
                action = logits.argmax(dim=-1)
            else:
                probabilities = F.softmax(logits, dim=-1).cpu().numpy()
                cumulative = np.cumsum(probabilities, axis=1)
                action_np = (uniforms[step, :, None] > cumulative).sum(axis=1)
                action_np = np.minimum(action_np, config.num_actions - 1)
                action = torch.from_numpy(action_np).to(device=device, dtype=torch.long)
            contexts = _router_contexts(observations)
        action_np = action.cpu().numpy()
        context_np = contexts.cpu().numpy()
        if step < 16:
            for index in np.flatnonzero(active):
                early_action_counts[context_np[index], action_np[index]] += 1
                early_context_counts[context_np[index]] += 1
        reward_np = np.zeros(count, dtype=np.float32)
        done_indices: list[int] = []
        for index in np.flatnonzero(active):
            _, terminal_reward, terminated, truncated, info = envs[index].step(
                int(action_np[index])
            )
            reward = terminal_reward
            if feedback_reward_mode == "stage_shaped":
                reward += sum(
                    DoorKeyVectorEnv.STAGE_REWARDS[event]
                    for event in info["events_fired"]  # type: ignore[union-attr]
                )
            reward_np[index] = reward
            if terminated or truncated:
                active[index] = False
                done_indices.append(int(index))
        hidden = next_hidden
        previous_action = action.detach().clone()
        previous_reward = torch.from_numpy(reward_np).to(device)
        if done_indices:
            hidden[done_indices] = 0.0
            previous_action[done_indices] = START_ACTION
            previous_reward[done_indices] = 0.0
        episode_start = torch.zeros_like(episode_start)
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
    return {
        "germ_mode": germ_mode,
        "feedback_reward_mode": feedback_reward_mode,
        "action_mode": action_mode,
        "world_count": count,
        "unique_layout_count": worlds_per_transform * len(TRANSFORMS),
        "action_seed": action_seed if action_mode == "fixed_random" else None,
        "stochastic_repeats": repeats,
        "successes": sum(bool(row["success"]) for row in rows),
        "success_rate": float(np.mean([bool(row["success"]) for row in rows])),
        "conditional_chain": _conditional_chain(rows),
        "early_action_counts_by_context": early_action_counts.tolist(),
        "early_context_counts": early_context_counts.tolist(),
        "world_rows": rows,
    }


def train_feedback_ppo(
    descendant: FeedbackPPODescendant,
    config: FeedbackPPOConfig,
    *,
    updates: int,
    training_seed: int,
    reward_mode: str,
    germ_mode: str,
    evaluation_every: int = 0,
    evaluation_worlds_per_transform: int = 8,
    stochastic_evaluation_repeats: int = 4,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if updates < 1:
        raise ValueError("updates must be positive")
    environments = DoorKeyVectorEnv(
        config.num_envs,
        training_seed,
        config.max_episode_steps,
        reward_mode,
    )
    history: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    total_episodes = 0
    total_successes = 0
    for update_index in range(1, updates + 1):
        rollout, completed = collect_feedback_rollout(
            descendant, environments, config, germ_mode
        )
        metrics = feedback_ppo_update(descendant, rollout, config, germ_mode)
        update_successes = sum(bool(row["success"]) for row in completed)
        total_episodes += len(completed)
        total_successes += update_successes
        row: dict[str, Any] = {
            "update": update_index,
            "environment_steps": update_index * config.num_envs * config.rollout_steps,
            "episodes_completed": len(completed),
            "episode_successes": update_successes,
            "cumulative_episodes": total_episodes,
            "cumulative_successes": total_successes,
            "mean_rollout_reward": float(rollout.rewards.mean()),
            "max_rollout_reward": float(rollout.rewards.max()),
            **metrics,
        }
        history.append(row)
        latest_evaluations: list[dict[str, Any]] = []
        if evaluation_every and update_index % evaluation_every == 0:
            for action_mode in ("deterministic", "fixed_random"):
                evaluation = evaluate_feedback_policy(
                    descendant,
                    config,
                    germ_mode=germ_mode,
                    feedback_reward_mode=reward_mode,
                    action_mode=action_mode,
                    worlds_per_transform=evaluation_worlds_per_transform,
                    stochastic_repeats=stochastic_evaluation_repeats,
                )
                evaluation.pop("world_rows")
                evaluation["update"] = update_index
                evaluations.append(evaluation)
                latest_evaluations.append(evaluation)
        if progress_callback is not None:
            progress_callback(
                {
                    "update": update_index,
                    "updates": updates,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_successes": total_successes,
                    "latest_evaluations": latest_evaluations,
                }
            )
    return {
        "updates": updates,
        "environment_steps": updates * config.num_envs * config.rollout_steps,
        "training_seed": training_seed,
        "reward_mode": reward_mode,
        "germ_mode": germ_mode,
        "episodes_completed": total_episodes,
        "episode_successes": total_successes,
        "history": history,
        "evaluations": evaluations,
        "model_sha256": _module_digest(descendant.model),
        "writer_sha256": _module_digest(descendant.writer),
    }

