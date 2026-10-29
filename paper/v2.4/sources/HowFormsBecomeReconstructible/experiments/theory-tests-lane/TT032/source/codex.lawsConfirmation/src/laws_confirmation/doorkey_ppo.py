"""Recurrent PPO development backend for the DoorKey vertical-carrier test.

This module requires PyTorch and is exercised in the external runtime under
``/mnt/bioIce1``.  It is intentionally separate from the NumPy-only audit
package so the retained-law tooling keeps its small dependency surface.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
from .doorkey_env import (
    Action,
    CAUSAL_CHAIN,
    DoorKeyEnv,
    TRANSFORMS,
    make_layout,
)


@dataclass(frozen=True)
class PPOConfig:
    observation_width: int = 13
    tile_positions: int = 9
    scalar_features: int = 4
    tile_vocab: int = 8
    tile_embedding_size: int = 8
    hidden_size: int = 64
    num_actions: int = 8
    num_envs: int = 32
    rollout_steps: int = 128
    ppo_epochs: int = 4
    minibatch_envs: int = 8
    learning_rate: float = 3.0e-4
    writer_learning_rate: float = 3.0e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    value_coefficient: float = 0.5
    entropy_coefficient: float = 0.01
    max_grad_norm: float = 0.5
    max_episode_steps: int = 128
    germ_logit_scale: float = 0.25

    def validate(self) -> None:
        if self.observation_width != self.tile_positions + self.scalar_features:
            raise ValueError("observation dimensions do not add up")
        if self.tile_positions != 9 or self.scalar_features != 4:
            raise ValueError("DoorKey v1 observation must be 9 tiles plus 4 scalars")
        if self.tile_vocab != 8 or self.num_actions != 8:
            raise ValueError("DoorKey v1 uses eight tiles and eight actions")
        for value in (
            self.tile_embedding_size,
            self.hidden_size,
            self.num_envs,
            self.rollout_steps,
            self.ppo_epochs,
            self.minibatch_envs,
            self.max_episode_steps,
        ):
            if value < 1:
                raise ValueError("integer PPO dimensions must be positive")
        if self.num_envs % self.minibatch_envs:
            raise ValueError("minibatch_envs must divide num_envs")
        if not 0 < self.learning_rate < 1 or not 0 < self.writer_learning_rate < 1:
            raise ValueError("learning rates must lie in (0, 1)")
        if not 0 < self.gamma <= 1 or not 0 <= self.gae_lambda <= 1:
            raise ValueError("invalid discount parameters")
        if not 0 < self.clip_epsilon < 1:
            raise ValueError("clip_epsilon must lie in (0, 1)")
        if self.max_grad_norm <= 0 or self.germ_logit_scale < 0:
            raise ValueError("invalid gradient or germ scaling")

    def digest(self) -> str:
        self.validate()
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RecurrentDoorKeyActorCritic(nn.Module):
    """Local-tile encoder, GRU memory, policy head, and terminal critic."""

    def __init__(self, config: PPOConfig) -> None:
        super().__init__()
        config.validate()
        self.config = config
        self.tile_embedding = nn.Embedding(
            config.tile_vocab, config.tile_embedding_size
        )
        encoder_width = (
            config.tile_positions * config.tile_embedding_size
            + config.scalar_features
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

    def encode(self, observations: torch.Tensor) -> torch.Tensor:
        if observations.ndim != 2 or observations.shape[1] != self.config.observation_width:
            raise ValueError("observations must have shape [batch, 13]")
        tiles = observations[:, : self.config.tile_positions].round().long()
        tiles = tiles.clamp(0, self.config.tile_vocab - 1)
        embedded = self.tile_embedding(tiles).flatten(start_dim=1)
        scalars = observations[:, self.config.tile_positions :]
        return self.encoder(torch.cat((embedded, scalars), dim=1))

    def forward_step(
        self,
        observations: torch.Tensor,
        hidden: torch.Tensor,
        episode_start: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if hidden.shape != (observations.shape[0], self.config.hidden_size):
            raise ValueError("hidden state has the wrong shape")
        if episode_start.shape != (observations.shape[0],):
            raise ValueError("episode_start has the wrong shape")
        retained = hidden * (~episode_start.bool()).to(hidden.dtype)[:, None]
        next_hidden = self.recurrent(self.encode(observations), retained)
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
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if observations.ndim != 3:
            raise ValueError("sequence observations must have shape [time, batch, obs]")
        if episode_starts.shape != observations.shape[:2]:
            raise ValueError("sequence reset mask has the wrong shape")
        hidden = initial_hidden
        logits: list[torch.Tensor] = []
        values: list[torch.Tensor] = []
        for step in range(observations.shape[0]):
            step_logits, step_values, hidden = self.forward_step(
                observations[step], hidden, episode_starts[step]
            )
            logits.append(step_logits)
            values.append(step_values)
        return torch.stack(logits), torch.stack(values), hidden


class DoorKeyGermWriter(nn.Module):
    """Dormant Stage-B writer scaffold; no truth-labelled update is implied."""

    def __init__(self, config: PPOConfig) -> None:
        super().__init__()
        self.config = config
        self.network = nn.Sequential(
            nn.Linear(config.hidden_size, config.hidden_size),
            nn.Tanh(),
            nn.Linear(config.hidden_size, 4 * config.num_actions),
        )
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=0.1)
                nn.init.zeros_(module.bias)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.network(hidden).reshape(hidden.shape[0], 4, 8)


@dataclass
class RolloutBatch:
    observations: torch.Tensor
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
class PPODescendant:
    germ: np.ndarray
    birth_seed: int
    public_rulebook_digest: str
    model: RecurrentDoorKeyActorCritic
    writer: DoorKeyGermWriter
    optimizer: torch.optim.Optimizer
    writer_optimizer: torch.optim.Optimizer
    recurrent_hidden: torch.Tensor
    rollout_state: RolloutBatch | None
    numpy_rng: np.random.Generator
    torch_generator: torch.Generator
    normalization_state: None
    curriculum_state: None
    population_statistics: None

    def refresh_carrier(self) -> tuple[torch.Tensor, torch.Tensor]:
        decoded = read_germ(self.germ, GermSchema())
        device = next(self.model.parameters()).device
        logits = torch.from_numpy(decoded.prior_logits[0].copy()).to(device)
        active = torch.from_numpy(decoded.active[0].copy()).to(device)
        return logits, active


def birth_ppo_descendant(
    packet: BoundaryPacket,
    config: PPOConfig,
    birth_seed: int,
    device: str | torch.device = "cpu",
) -> PPODescendant:
    """Create fresh learner state from public config and exactly one packet."""

    config.validate()
    if not 0 <= birth_seed < 2**63:
        raise ValueError("birth_seed must be in [0, 2^63)")
    target = torch.device(device)
    if target.type != "cpu":
        raise ValueError("DoorKey v1 is frozen to CPU execution")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(birth_seed)
        model = RecurrentDoorKeyActorCritic(config).to(target)
        writer = DoorKeyGermWriter(config).to(target)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    writer_optimizer = torch.optim.Adam(
        writer.parameters(), lr=config.writer_learning_rate
    )
    torch_generator = torch.Generator(device=target)
    torch_generator.manual_seed(birth_seed + 1_000_000_007)
    germ = np.frombuffer(packet.payload, dtype=np.uint8).copy().reshape(1, 64)
    return PPODescendant(
        germ=germ,
        birth_seed=int(birth_seed),
        public_rulebook_digest=config.digest(),
        model=model,
        writer=writer,
        optimizer=optimizer,
        writer_optimizer=writer_optimizer,
        recurrent_hidden=torch.zeros(
            (config.num_envs, config.hidden_size), dtype=torch.float32, device=target
        ),
        rollout_state=None,
        numpy_rng=np.random.default_rng(birth_seed + 2_000_000_011),
        torch_generator=torch_generator,
        normalization_state=None,
        curriculum_state=None,
        population_statistics=None,
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


def _optimizer_tensor_count(optimizer: torch.optim.Optimizer) -> int:
    return sum(
        isinstance(value, torch.Tensor)
        for state in optimizer.state.values()
        for value in state.values()
    )


def learner_state_digests(descendant: PPODescendant) -> dict[str, str]:
    """Stable hashes for development replay and reset checks."""

    return {
        "actor_critic": _module_digest(descendant.model),
        "writer": _module_digest(descendant.writer),
        "torch_generator": _generator_digest(descendant.torch_generator),
        "numpy_generator": _numpy_generator_digest(descendant.numpy_rng),
    }


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


def prime_ppo_parent_for_boundary_audit(
    descendant: PPODescendant, marker: float
) -> None:
    """Mutate every present learner-state channel before a reset audit."""

    if not math.isfinite(marker) or marker == 0:
        raise ValueError("marker must be finite and nonzero")
    config = descendant.model.config
    descendant.optimizer.zero_grad(set_to_none=True)
    model_loss = sum(parameter.square().mean() for parameter in descendant.model.parameters())
    model_loss.backward()
    descendant.optimizer.step()
    descendant.writer_optimizer.zero_grad(set_to_none=True)
    writer_loss = sum(
        parameter.square().mean() for parameter in descendant.writer.parameters()
    )
    writer_loss.backward()
    descendant.writer_optimizer.step()
    descendant.recurrent_hidden.fill_(marker)
    dummy = torch.full(
        (2, config.num_envs, config.observation_width),
        marker,
        dtype=torch.float32,
    )
    zeros = torch.zeros((2, config.num_envs), dtype=torch.float32)
    descendant.rollout_state = RolloutBatch(
        observations=dummy,
        actions=zeros.long(),
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


def audit_real_ppo_boundary(
    parent: PPODescendant,
    child: PPODescendant,
    packet: BoundaryPacket,
) -> dict[str, Any]:
    """Audit actual PyTorch objects and explicitly absent optional channels."""

    birth_parameters = tuple(inspect.signature(birth_ppo_descendant).parameters)
    parent_model = _module_digest(parent.model)
    child_model = _module_digest(child.model)
    parent_writer = _module_digest(parent.writer)
    child_writer = _module_digest(child.writer)
    carrier_bytes = child.germ[0].tobytes(order="C")
    rows = {
        "actor_critic_parameters": {
            "parent_digest": parent_model,
            "child_digest": child_model,
            "reset": parent_model != child_model,
        },
        "writer_parameters": {
            "parent_digest": parent_writer,
            "child_digest": child_writer,
            "reset": parent_writer != child_writer,
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
        "rng_state": {
            "parent_torch_digest": _generator_digest(parent.torch_generator),
            "child_torch_digest": _generator_digest(child.torch_generator),
            "parent_numpy_digest": _numpy_generator_digest(parent.numpy_rng),
            "child_numpy_digest": _numpy_generator_digest(child.numpy_rng),
            "reset": (
                _generator_digest(parent.torch_generator)
                != _generator_digest(child.torch_generator)
                and _numpy_generator_digest(parent.numpy_rng)
                != _numpy_generator_digest(child.numpy_rng)
            ),
        },
        "global_rng_state": {
            "status": "avoided_by_design_with_fork_rng_and_private_generators",
            "reset": True,
        },
        "normalization_state": {"status": "absent_by_design", "reset": True},
        "curriculum_state": {"status": "absent_by_design", "reset": True},
        "population_statistics": {"status": "absent_by_design", "reset": True},
    }
    gates = {
        "birth_api_has_no_parent_argument": birth_parameters
        == ("packet", "config", "birth_seed", "device"),
        "packet_is_exactly_64_bytes": len(packet.payload) == 64,
        "carrier_exactly_preserved": carrier_bytes == packet.payload,
        "public_rulebook_unchanged": (
            parent.public_rulebook_digest == child.public_rulebook_digest
        ),
        "all_present_somatic_state_reset": all(
            bool(row["reset"]) for row in rows.values()
        ),
    }
    return {
        "birth_api_parameters": list(birth_parameters),
        "state_rows": rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def _carrier_prior(
    descendant: PPODescendant,
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
    door_visible = ((tiles == DoorKeyEnv.DOOR_CLOSED) | (tiles == DoorKeyEnv.DOOR_OPEN)).any(
        dim=1
    )
    context = torch.zeros(batch, dtype=torch.long, device=observations.device)
    context = torch.where(~has_key & key_visible, torch.ones_like(context), context)
    context = torch.where(has_key, torch.full_like(context, 2), context)
    context = torch.where(has_key & door_visible, torch.full_like(context, 3), context)
    return slot_logits[context], slot_active[context]


def _apply_prior(
    logits: torch.Tensor,
    descendant: PPODescendant,
    observations: torch.Tensor,
    germ_mode: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    prior, active = _carrier_prior(descendant, observations, germ_mode)
    scale = descendant.model.config.germ_logit_scale
    return logits + prior * active.to(logits.dtype)[:, None] * scale, active


class DoorKeyVectorEnv:
    """Deterministic in-process environment batch with resettable schedules."""

    STAGE_REWARDS: Mapping[str, float] = {
        "explore": 0.02,
        "find_key": 0.10,
        "retain_key": 0.10,
        "find_door": 0.15,
        "open_door": 0.25,
        "reach_goal": 0.0,
    }

    def __init__(
        self,
        num_envs: int,
        base_seed: int,
        max_steps: int,
        reward_mode: str,
    ) -> None:
        if reward_mode not in ("terminal", "stage_shaped"):
            raise ValueError("reward_mode must be terminal or stage_shaped")
        self.num_envs = num_envs
        self.base_seed = base_seed
        self.max_steps = max_steps
        self.reward_mode = reward_mode
        self.episode_counts = np.zeros(num_envs, dtype=np.int64)
        self.episode_returns = np.zeros(num_envs, dtype=np.float64)
        self.completed: list[dict[str, Any]] = []
        self.envs = [self._new_env(index) for index in range(num_envs)]
        self.episode_starts = np.ones(num_envs, dtype=bool)

    def _layout_seed(self, index: int) -> int:
        return int(
            self.base_seed
            + index * 1_000_003
            + int(self.episode_counts[index]) * 97
        )

    def _new_env(self, index: int) -> DoorKeyEnv:
        layout_seed = self._layout_seed(index)
        transform = TRANSFORMS[(index + int(self.episode_counts[index])) % 4]
        return DoorKeyEnv(
            make_layout(layout_seed, transform), max_steps=self.max_steps
        )

    def observations(self) -> np.ndarray:
        return np.stack([env.observation().vector() for env in self.envs])

    def step(
        self, actions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]]]:
        if actions.shape != (self.num_envs,):
            raise ValueError("actions must have one entry per environment")
        rewards = np.zeros(self.num_envs, dtype=np.float32)
        dones = np.zeros(self.num_envs, dtype=bool)
        infos: list[dict[str, object]] = []
        for index, selected in enumerate(actions):
            env = self.envs[index]
            _, terminal_reward, terminated, truncated, info = env.step(int(selected))
            reward = terminal_reward
            if self.reward_mode == "stage_shaped":
                reward += sum(
                    self.STAGE_REWARDS[event]
                    for event in info["events_fired"]  # type: ignore[union-attr]
                )
            rewards[index] = reward
            self.episode_returns[index] += reward
            done = terminated or truncated
            dones[index] = done
            infos.append(info)
            if done:
                self.completed.append(
                    {
                        "env_index": index,
                        "layout_seed": env.layout.seed,
                        "transform": env.layout.transform,
                        "success": terminated,
                        "truncated": truncated,
                        "episode_steps": env.steps,
                        "episode_return": float(self.episode_returns[index]),
                        "event_steps": dict(env.event_steps),
                        "auxiliary_steps": dict(env.auxiliary_steps),
                    }
                )
                self.episode_counts[index] += 1
                self.episode_returns[index] = 0.0
                self.envs[index] = self._new_env(index)
        self.episode_starts = dones.copy()
        return self.observations(), rewards, dones, infos

    def pop_completed(self) -> list[dict[str, Any]]:
        result = self.completed
        self.completed = []
        return result


def collect_rollout(
    descendant: PPODescendant,
    environments: DoorKeyVectorEnv,
    config: PPOConfig,
    germ_mode: str,
) -> tuple[RolloutBatch, list[dict[str, Any]]]:
    config.validate()
    device = next(descendant.model.parameters()).device
    observations_np = environments.observations()
    hidden = descendant.recurrent_hidden.detach()
    initial_hidden = hidden.clone()
    episode_start_np = environments.episode_starts.copy()
    observations: list[torch.Tensor] = []
    actions: list[torch.Tensor] = []
    log_probabilities: list[torch.Tensor] = []
    rewards: list[torch.Tensor] = []
    dones: list[torch.Tensor] = []
    episode_starts: list[torch.Tensor] = []
    values: list[torch.Tensor] = []

    descendant.model.eval()
    for _ in range(config.rollout_steps):
        observation = torch.from_numpy(observations_np).to(device=device, dtype=torch.float32)
        episode_start = torch.from_numpy(episode_start_np).to(device=device)
        with torch.no_grad():
            base_logits, value, next_hidden = descendant.model.forward_step(
                observation, hidden, episode_start
            )
            logits, _ = _apply_prior(base_logits, descendant, observation, germ_mode)
            log_probs = F.log_softmax(logits, dim=-1)
            probabilities = log_probs.exp()
            action = torch.multinomial(
                probabilities, 1, generator=descendant.torch_generator
            ).squeeze(1)
            chosen_log_probability = log_probs.gather(1, action[:, None]).squeeze(1)
        next_observations, reward_np, done_np, _ = environments.step(
            action.detach().cpu().numpy()
        )
        observations.append(observation)
        actions.append(action)
        log_probabilities.append(chosen_log_probability)
        rewards.append(torch.from_numpy(reward_np).to(device))
        done = torch.from_numpy(done_np).to(device)
        dones.append(done)
        episode_starts.append(episode_start)
        values.append(value)
        hidden = next_hidden.detach()
        hidden[done] = 0.0
        observations_np = next_observations
        episode_start_np = done_np

    next_observation = torch.from_numpy(observations_np).to(
        device=device, dtype=torch.float32
    )
    next_episode_start = torch.from_numpy(episode_start_np).to(device=device)
    with torch.no_grad():
        _, next_value, _ = descendant.model.forward_step(
            next_observation, hidden, next_episode_start
        )
    reward_tensor = torch.stack(rewards)
    done_tensor = torch.stack(dones)
    value_tensor = torch.stack(values)
    advantages = torch.zeros_like(reward_tensor)
    last_advantage = torch.zeros(config.num_envs, device=device)
    for step in reversed(range(config.rollout_steps)):
        nonterminal = (~done_tensor[step]).to(torch.float32)
        following_value = next_value if step == config.rollout_steps - 1 else value_tensor[step + 1]
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
    returns = advantages + value_tensor
    batch = RolloutBatch(
        observations=torch.stack(observations),
        actions=torch.stack(actions),
        old_log_probabilities=torch.stack(log_probabilities),
        rewards=reward_tensor,
        dones=done_tensor,
        episode_starts=torch.stack(episode_starts),
        old_values=value_tensor,
        advantages=advantages,
        returns=returns,
        initial_hidden=initial_hidden,
    )
    descendant.recurrent_hidden = hidden
    descendant.rollout_state = batch
    return batch, environments.pop_completed()


def ppo_update(
    descendant: PPODescendant,
    rollout: RolloutBatch,
    config: PPOConfig,
    germ_mode: str,
) -> dict[str, float]:
    descendant.model.train()
    normalized_advantages = (rollout.advantages - rollout.advantages.mean()) / (
        rollout.advantages.std(unbiased=False) + 1e-8
    )
    metrics: dict[str, list[float]] = {
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
            indices_np = order[start : start + config.minibatch_envs]
            indices = torch.as_tensor(
                indices_np,
                dtype=torch.long,
                device=rollout.observations.device,
            )
            observations = rollout.observations[:, indices]
            logits, values, _ = descendant.model.forward_sequence(
                observations,
                rollout.initial_hidden[indices],
                rollout.episode_starts[:, indices],
            )
            flat_observations = observations.reshape(-1, config.observation_width)
            flat_logits = logits.reshape(-1, config.num_actions)
            flat_logits, _ = _apply_prior(
                flat_logits, descendant, flat_observations, germ_mode
            )
            log_probs = F.log_softmax(flat_logits, dim=-1)
            probabilities = log_probs.exp()
            actions = rollout.actions[:, indices].reshape(-1)
            new_log_probability = log_probs.gather(1, actions[:, None]).squeeze(1)
            entropy = -(probabilities * log_probs).sum(dim=-1).mean()
            old_log_probability = rollout.old_log_probabilities[:, indices].reshape(-1)
            advantage = normalized_advantages[:, indices].reshape(-1)
            ratio = torch.exp(new_log_probability - old_log_probability)
            unclipped = ratio * advantage
            clipped = torch.clamp(
                ratio, 1.0 - config.clip_epsilon, 1.0 + config.clip_epsilon
            ) * advantage
            policy_loss = -torch.minimum(unclipped, clipped).mean()
            target_return = rollout.returns[:, indices].reshape(-1)
            value_loss = 0.5 * F.mse_loss(values.reshape(-1), target_return)
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
            metrics["policy_loss"].append(float(policy_loss.detach()))
            metrics["value_loss"].append(float(value_loss.detach()))
            metrics["entropy"].append(float(entropy.detach()))
            metrics["approx_kl"].append(float(approx_kl.detach()))
            metrics["clip_fraction"].append(float(clip_fraction.detach()))
            metrics["grad_norm"].append(float(grad_norm.detach()))
    return {name: float(np.mean(values)) for name, values in metrics.items()}


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
                "conditional_probability": (
                    float(len(reached) / len(eligible)) if eligible else None
                ),
            }
        )
        previous = event
    return result


def evaluate_policy(
    descendant: PPODescendant,
    config: PPOConfig,
    *,
    germ_mode: str,
    worlds_per_transform: int = 16,
    seed_base: int = 70_000_000,
) -> dict[str, Any]:
    """Deterministic common-world evaluation with full event endpoints."""

    envs: list[DoorKeyEnv] = []
    for transform_index, transform in enumerate(TRANSFORMS):
        for local_seed in range(worlds_per_transform):
            seed = seed_base + transform_index * 10_000 + local_seed
            envs.append(
                DoorKeyEnv(
                    make_layout(seed, transform),
                    max_steps=config.max_episode_steps,
                )
            )
    count = len(envs)
    hidden = torch.zeros(
        (count, config.hidden_size),
        dtype=torch.float32,
        device=next(descendant.model.parameters()).device,
    )
    episode_start = torch.ones(count, dtype=torch.bool, device=hidden.device)
    active = np.ones(count, dtype=bool)
    early_action_counts = np.zeros((4, 8), dtype=np.int64)
    early_context_counts = np.zeros(4, dtype=np.int64)
    descendant.model.eval()
    for step in range(config.max_episode_steps):
        observations_np = np.stack([env.observation().vector() for env in envs])
        observations = torch.from_numpy(observations_np).to(
            device=hidden.device, dtype=torch.float32
        )
        with torch.no_grad():
            base_logits, _, next_hidden = descendant.model.forward_step(
                observations, hidden, episode_start
            )
            logits, _ = _apply_prior(
                base_logits, descendant, observations, germ_mode
            )
            action = logits.argmax(dim=-1)
            _, context_active = _carrier_prior(descendant, observations, "direct_prior")
            # Reconstruct public router contexts for action-distribution logging.
            tiles = observations[:, :9].round().long()
            has_key = observations[:, 9] > 0.5
            key_visible = (tiles == DoorKeyEnv.KEY).any(dim=1) | (observations[:, 10] > 0.5)
            door_visible = (
                (tiles == DoorKeyEnv.DOOR_CLOSED) | (tiles == DoorKeyEnv.DOOR_OPEN)
            ).any(dim=1)
            contexts = torch.zeros(count, dtype=torch.long, device=hidden.device)
            contexts = torch.where(~has_key & key_visible, torch.ones_like(contexts), contexts)
            contexts = torch.where(has_key, torch.full_like(contexts, 2), contexts)
            contexts = torch.where(has_key & door_visible, torch.full_like(contexts, 3), contexts)
        action_np = action.cpu().numpy()
        context_np = contexts.cpu().numpy()
        if step < 16:
            for index in np.flatnonzero(active):
                early_action_counts[context_np[index], action_np[index]] += 1
                early_context_counts[context_np[index]] += 1
        done_indices: list[int] = []
        for index in np.flatnonzero(active):
            _, _, terminated, truncated, _ = envs[index].step(int(action_np[index]))
            if terminated or truncated:
                active[index] = False
                done_indices.append(int(index))
        hidden = next_hidden
        if done_indices:
            hidden[done_indices] = 0.0
        episode_start = torch.zeros_like(episode_start)
        if not active.any():
            break
    rows = [
        {
            "layout_seed": env.layout.seed,
            "transform": env.layout.transform,
            "success": env.terminated,
            "truncated": env.truncated,
            "episode_steps": env.steps,
            "event_steps": dict(env.event_steps),
            "auxiliary_steps": dict(env.auxiliary_steps),
        }
        for env in envs
    ]
    return {
        "germ_mode": germ_mode,
        "world_count": count,
        "successes": sum(bool(row["success"]) for row in rows),
        "success_rate": float(np.mean([bool(row["success"]) for row in rows])),
        "conditional_chain": _conditional_chain(rows),
        "early_action_counts_by_context": early_action_counts.tolist(),
        "early_context_counts": early_context_counts.tolist(),
        "carrier_active_observed": bool(context_active.any()),
        "world_rows": rows,
    }


def train_ppo(
    descendant: PPODescendant,
    config: PPOConfig,
    *,
    updates: int,
    training_seed: int,
    reward_mode: str,
    germ_mode: str,
    evaluation_every: int = 0,
    evaluation_worlds_per_transform: int = 8,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run a deterministic development training series."""

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
        rollout, completed = collect_rollout(
            descendant, environments, config, germ_mode
        )
        metrics = ppo_update(descendant, rollout, config, germ_mode)
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
        if evaluation_every and update_index % evaluation_every == 0:
            evaluation = evaluate_policy(
                descendant,
                config,
                germ_mode=germ_mode,
                worlds_per_transform=evaluation_worlds_per_transform,
            )
            evaluation.pop("world_rows")
            evaluation["update"] = update_index
            evaluations.append(evaluation)
        if progress_callback is not None:
            progress_callback(
                {
                    "update": update_index,
                    "updates": updates,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_successes": total_successes,
                    "latest_evaluation": evaluations[-1]
                    if evaluations and evaluations[-1]["update"] == update_index
                    else None,
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


def make_empty_ppo_descendant(
    config: PPOConfig, birth_seed: int
) -> PPODescendant:
    packet = make_boundary_packet(empty_germ(1, GermSchema()), GermSchema())
    return birth_ppo_descendant(packet, config, birth_seed)
