"""Frozen fresh-descendant test of learned, action-blind consequence credit.

Only the declared packet crosses birth. The qualified predictor is reused as
source code, never as pretrained weights or a source of diagnostic examples.
"""

from __future__ import annotations

import argparse
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict
import json
import math
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from . import doorkey_consequence_predictor as predictor
from . import doorkey_matched_disposition as matched
from . import doorkey_targeted_learning_reader as targeted
from . import doorkey_vertical_scout as vertical
from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import carrier_digest, empty_germ
from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
    _disk_preflight,
    _read_hash_manifest,
)
from .doorkey_phase_value_credit import (
    CHANNELS,
    DOOR_CHANNEL,
    KEY_CHANNEL,
    CausalCreditDescendant,
    CausalCreditRollout,
    _forward_sequence_values,
    _masked_mse,
    _module_birth_details,
    actor_advantage_for_arm,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import (
    FeedbackPPOConfig,
    _apply_prior,
    _optimizer_tensor_count,
    _router_contexts,
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


RUN_ID = "doorkey_consequence_reader_behavior_v1_attempt1"
SOURCE_RUN = predictor.RUN_ID
ARMS = predictor.ARMS
FOUNDERS = (1, 2, 3)
NULL_ARMS = ("wrong", "empty", "reader_off")
UPDATES = 100
MATCHED_UPDATES = 60
MAX_WORKERS = 4
EXPECTED_STEPS = 409_600
REGISTERED_CELLS = len(FOUNDERS) * len(ARMS)
REGISTERED_TRANSITIONS = REGISTERED_CELLS * EXPECTED_STEPS
PRACTICAL_MARGIN = 0.05
METRIC_NAMES = predictor.dose.METRIC_NAMES


def seed_row(founder: int) -> dict[str, int]:
    if founder not in FOUNDERS:
        raise ValueError("unregistered founder")
    return {
        "birth": 300_000_000 + 100_000 * founder,
        "training": 310_000_000 + 100_000 * founder,
        "head": 320_000_000 + 100_000 * founder,
    }


def pin_cpu_budget() -> list[int]:
    available = sorted(os.sched_getaffinity(0))
    selected = available[:MAX_WORKERS]
    if not selected:
        raise RuntimeError("no CPU available")
    os.sched_setaffinity(0, selected)
    return selected


def runtime_qualification() -> dict:
    cpus = pin_cpu_budget()
    runtime = targeted.runtime_qualification(MAX_WORKERS)
    thread_names = (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    )
    runtime["values"]["cpu_affinity"] = cpus
    runtime["gates"]["at_most_four_cpu_affinity"] = len(cpus) <= MAX_WORKERS
    runtime["gates"]["all_numerical_thread_limits_one"] = all(
        os.environ.get(name) == "1" for name in thread_names
    )
    runtime["passes"] = all(runtime["gates"].values())
    return runtime


def _credit_summary(credit: torch.Tensor, contexts: torch.Tensor) -> dict:
    return {
        "nonzero_steps": int(torch.count_nonzero(credit)),
        "positive_steps": int((credit > 0).sum()),
        "negative_steps": int((credit < 0).sum()),
        "positive_mass": float(credit.clamp_min(0).sum()),
        "negative_mass": float((-credit).clamp_min(0).sum()),
        "max_absolute": float(credit.abs().max()),
        "by_context": {
            str(context): {
                "samples": int((contexts == context).sum()),
                "positive_mass": float(credit[contexts == context].clamp_min(0).sum()),
                "negative_mass": float(
                    (-credit[contexts == context]).clamp_min(0).sum()
                ),
            }
            for context in range(4)
        },
    }


@torch.no_grad()
def learned_actor_advantage(
    descendant: CausalCreditDescendant,
    reader: predictor.ConsequenceReader,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    update: int,
) -> tuple[torch.Tensor, dict, dict]:
    """Read a pre-fit head once; the result stays fixed during every PPO epoch."""
    if not 1 <= update <= UPDATES:
        raise ValueError("update outside the frozen schedule")
    base, signals = actor_advantage_for_arm(rollout, "phase_actor")
    logits, _, _ = _forward_sequence_values(
        descendant,
        rollout.observations,
        rollout.initial_hidden,
        rollout.episode_starts,
        rollout.previous_actions,
        rollout.previous_rewards,
    )
    observations = rollout.observations.reshape(-1, config.observation_width)
    logits, _ = _apply_prior(
        logits.reshape(-1, config.num_actions),
        descendant.learner,
        observations,
        "blind",
    )
    log_probs = F.log_softmax(logits, dim=-1)
    probabilities = log_probs.exp()
    actions = rollout.actions.reshape(-1)
    chosen = log_probs.gather(1, actions[:, None]).squeeze(1)
    table = reader.credit_table(observations, probabilities)
    policy_zero_error = float((table * probabilities[:, None]).sum(-1).abs().max())
    proposed = table.gather(2, actions[:, None, None].expand(-1, 2, 1)).squeeze(-1)
    enabled = update > MATCHED_UPDATES
    applied = proposed.clone() if enabled else torch.zeros_like(proposed)
    delta = applied.sum(1).reshape_as(base)
    # Preserve even signed-zero representations in the exact null path.
    advantage = base + delta if torch.count_nonzero(delta) else base.clone()
    contexts = _router_contexts(observations)
    audit = {
        "update": update,
        "enabled_by_schedule": enabled,
        "reader_output_enabled": reader.arm != "reader_off",
        "confirmations_before_update": list(reader.positive_counts),
        "reader_prefit_sha256": reader.digest(),
        "base_advantage_sha256": matched.deep_digest(base),
        "applied_advantage_sha256": matched.deep_digest(advantage),
        "applied_credit_sha256": matched.deep_digest(applied),
        "blind_log_probabilities_exact": torch.equal(
            chosen.reshape_as(rollout.old_log_probabilities),
            rollout.old_log_probabilities,
        ),
        "policy_centering_max_error": policy_zero_error,
        "credit_finite": bool(torch.isfinite(table).all()),
        "suppressed_read_reconstructs_baseline": torch.equal(base.clone(), base),
        "zero_credit_reconstructs_baseline": bool(torch.count_nonzero(delta))
        or torch.equal(advantage, base),
        "applied_nonzero_steps": int(torch.count_nonzero(delta)),
        "channels": {
            CHANNELS[c]: {
                "proposed": _credit_summary(proposed[:, c], contexts),
                "applied": _credit_summary(applied[:, c], contexts),
            }
            for c in range(2)
        },
    }
    return advantage.detach().clone(), signals, audit


def ppo_update_with_advantage(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    actor_advantage: torch.Tensor,
    signals: Mapping[str, bool],
) -> dict:
    """Frozen phase PPO arithmetic, with one explicit detached advantage input."""
    if actor_advantage.shape != rollout.actions.shape or actor_advantage.requires_grad:
        raise ValueError("PPO requires a fixed detached rollout-shaped advantage")
    descendant.learner.model.train()
    descendant.auxiliary_heads.train()
    collected = {
        name: []
        for name in METRIC_NAMES
        if name
        not in (
            "actor_channel_signal",
            "actor_advantage_nonzero",
            "actor_advantage_nonzero_count",
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
            flat_logits, _ = _apply_prior(
                logits.reshape(-1, config.num_actions),
                descendant.learner,
                observations.reshape(-1, config.observation_width),
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
                goal_values.reshape(-1), rollout.goal_returns[:, indices].reshape(-1)
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
    result = {name: float(np.mean(values)) for name, values in collected.items()}
    result.update(
        {
            "actor_channel_signal": dict(signals),
            "actor_advantage_nonzero": bool(torch.count_nonzero(actor_advantage)),
            "actor_advantage_nonzero_count": int(torch.count_nonzero(actor_advantage)),
        }
    )
    return result


def _actor_grad_digest(descendant: CausalCreditDescendant) -> str:
    return matched.deep_digest(
        [
            p.grad
            for p in [
                *descendant.learner.model.parameters(),
                *descendant.auxiliary_heads.parameters(),
            ]
        ]
    )


def training_step(
    descendant, reader, environments, recorder, config, update
) -> tuple[dict, CausalCreditRollout, torch.Tensor]:
    rollout, completed = vertical.collect_vertical_rollout(
        descendant, recorder, config, "blind"
    )
    outcomes = recorder.take_outcomes()
    before_read = matched.soma_environment_digests(descendant, environments)
    head_before = reader.digest()
    advantage, signals, credit = learned_actor_advantage(
        descendant, reader, rollout, config, update
    )
    after_read = matched.soma_environment_digests(descendant, environments)
    read_head_unchanged = reader.digest() == head_before
    metrics = ppo_update_with_advantage(descendant, rollout, config, advantage, signals)
    head_after_ppo = reader.digest()
    before_fit = matched.soma_environment_digests(descendant, environments)
    grads_before_fit = _actor_grad_digest(descendant)
    global_rng_before_fit = torch.get_rng_state().clone()
    prequential = predictor.prequential_rows(
        reader, rollout.observations, rollout.actions, outcomes
    )
    fit = reader.fit(rollout.observations, rollout.actions, outcomes)
    after_fit = matched.soma_environment_digests(descendant, environments)
    head_after_fit = reader.digest()
    semantics = rollout_semantics(rollout)
    gates = {
        "reader_does_not_mutate_actor_or_environment": before_read == after_read,
        "read_does_not_mutate_head": read_head_unchanged,
        "ppo_does_not_train_head": head_after_ppo == head_before,
        "prefit_state_used_for_credit": head_before == credit["reader_prefit_sha256"],
        "head_fit_does_not_mutate_actor_or_environment": before_fit == after_fit,
        "head_fit_does_not_change_actor_gradients": grads_before_fit
        == _actor_grad_digest(descendant),
        "head_fit_global_rng_unchanged": torch.equal(
            global_rng_before_fit, torch.get_rng_state()
        ),
        "fixed_advantage_not_mutated": matched.deep_digest(advantage)
        == credit["applied_advantage_sha256"],
        "blind_log_probabilities_exact": credit["blind_log_probabilities_exact"],
        "probability_centered_credit": credit["policy_centering_max_error"] < 1e-6,
        "all_credits_finite": credit["credit_finite"],
        "all_metrics_finite": all(
            math.isfinite(float(metrics[name]))
            for name in METRIC_NAMES
            if name
            not in (
                "actor_channel_signal",
                "actor_advantage_nonzero",
                "actor_advantage_nonzero_count",
            )
        ),
        "rollout_semantics_pass": all(semantics.values()),
        "raw_acquisition_includes_first_events": bool(
            torch.all(outcomes[:, :, 0] >= rollout.event_rewards[:, :, 0])
        ),
        "door_events_exact": torch.equal(
            outcomes[:, :, 1], rollout.event_rewards[:, :, 1]
        ),
        "prefix_credit_zero": update > MATCHED_UPDATES
        or credit["applied_nonzero_steps"] == 0,
        "null_arm_credit_zero": reader.arm not in NULL_ARMS
        or credit["applied_nonzero_steps"] == 0,
        "null_reconstructs_base": credit["zero_credit_reconstructs_baseline"],
        "empty_is_exact_noop": reader.arm != "empty" or head_after_fit == head_before,
        "shuffled_counts_preserved": bool(fit["label_counts_preserved"]),
        "buffer_bound": len(reader.buffer) <= predictor.BUFFER_ROLLOUTS,
        "writer_optimizer_dormant": _optimizer_tensor_count(
            descendant.learner.writer_optimizer
        )
        == 0,
    }
    behavior = {
        "update": update,
        "environment_steps": update * config.num_envs * config.rollout_steps,
        "episodes_completed": len(completed),
        "episode_successes": sum(bool(row["success"]) for row in completed),
        "event_counts": {
            name: int(rollout.event_rewards[:, :, c].sum())
            for c, name in enumerate(CHANNELS)
        },
        "phase_counts": {
            name: int((rollout.phases == c).sum()) for c, name in enumerate(CHANNELS)
        },
        "mean_rollout_terminal_reward": float(rollout.terminal_rewards.mean()),
        "max_rollout_terminal_reward": float(rollout.terminal_rewards.max()),
        "rollout_sha256": matched.deep_digest(vars(rollout)),
        "actions_sha256": matched.deep_digest(rollout.actions),
        "completed_episode_rows_sha256": matched.deep_digest(completed),
        "observed_outcomes_sha256": matched.deep_digest(outcomes),
        "post_update_soma_environment_sha256": after_fit["aggregate"],
        "ppo": metrics,
    }
    row = {
        "update": update,
        "behavior": behavior,
        "credit": credit,
        "prequential": prequential,
        "fit": fit,
        "predictor_before_sha256": head_before,
        "predictor_after_sha256": head_after_fit,
        "rollout_semantics": semantics,
        "gates": gates,
        "passes": all(gates.values()),
    }
    if not row["passes"]:
        raise RuntimeError(f"update {update} failed structural gates: {gates}")
    return row, rollout, outcomes


def evaluate(
    descendant, reader, environments, config, update
) -> tuple[list[dict], dict, bool]:
    before = matched.soma_environment_digests(descendant, environments)
    head_before = reader.digest()
    summaries, worlds = [], {}
    for mode in ACTION_MODES:
        summary, rows = vertical._evaluate(descendant, config, "blind", mode)
        summary.update(
            {"update": update, "world_rows_sha256": matched.deep_digest(rows)}
        )
        summaries.append(summary)
        worlds[mode] = rows
    read_only = (
        before == matched.soma_environment_digests(descendant, environments)
        and head_before == reader.digest()
    )
    return summaries, worlds, read_only


def checkpoint_payload(
    descendant, reader, environments, config, spec, rollout, outcomes
) -> dict:
    learner = descendant.learner
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "spec": dict(spec),
        "config": asdict(config),
        "germ": learner.germ.copy(),
        "model_state_dict": learner.model.state_dict(),
        "auxiliary_heads_state_dict": descendant.auxiliary_heads.state_dict(),
        "writer_state_dict": learner.writer.state_dict(),
        "optimizer_state_dict": learner.optimizer.state_dict(),
        "writer_optimizer_state_dict": learner.writer_optimizer.state_dict(),
        "recurrent_hidden": learner.recurrent_hidden,
        "previous_actions": learner.previous_actions,
        "previous_rewards": learner.previous_rewards,
        "rollout_state": learner.rollout_state,
        "last_rollout": vertical.rollout_payload(rollout),
        "last_observed_outcomes": outcomes,
        "numpy_rng_state": learner.numpy_rng.bit_generator.state,
        "torch_generator_state": learner.torch_generator.get_state(),
        "normalization_state": learner.normalization_state,
        "curriculum_state": learner.curriculum_state,
        "population_statistics": learner.population_statistics,
        "environments": environments,
        "reader_state": reader.state(),
        "reader_packet": reader.packet.copy(),
    }


def restore_checkpoint(payload: Mapping[str, Any]) -> tuple:
    config = FeedbackPPOConfig(**payload["config"])
    spec = payload["spec"]
    descendant = vertical.make_vertical_descendant(
        make_boundary_packet(payload["germ"]), config, int(spec["birth_seed"])
    )
    learner = descendant.learner
    for module, key in (
        (learner.model, "model_state_dict"),
        (descendant.auxiliary_heads, "auxiliary_heads_state_dict"),
        (learner.writer, "writer_state_dict"),
    ):
        module.load_state_dict(payload[key])
    learner.optimizer.load_state_dict(deepcopy(payload["optimizer_state_dict"]))
    learner.writer_optimizer.load_state_dict(
        deepcopy(payload["writer_optimizer_state_dict"])
    )
    for name in (
        "recurrent_hidden",
        "previous_actions",
        "previous_rewards",
        "rollout_state",
        "normalization_state",
        "curriculum_state",
        "population_statistics",
    ):
        setattr(learner, name, deepcopy(payload[name]))
    learner.numpy_rng.bit_generator.state = deepcopy(payload["numpy_rng_state"])
    learner.torch_generator.set_state(payload["torch_generator_state"])
    reader = predictor.ConsequenceReader(
        payload["reader_packet"], int(spec["head_seed"]), str(spec["arm"])
    )
    state = payload["reader_state"]
    reader.model.load_state_dict(state["model"])
    reader.optimizer.load_state_dict(deepcopy(state["optimizer"]))
    reader.generator.set_state(state["sampling_rng"])
    reader.shuffle_generator.set_state(state["shuffle_rng"])
    reader.buffer = deque(deepcopy(state["buffer"]), maxlen=predictor.BUFFER_ROLLOUTS)
    reader.positive_counts = list(state["positive_counts"])
    reader.negative_target_counts = list(state["negative_target_counts"])
    reader.updates = int(state["updates"])
    return descendant, reader, deepcopy(payload["environments"]), config


def train_cell(
    spec: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    root_text: str,
    output_text: str,
) -> dict:
    runtime = runtime_qualification()
    if not runtime["passes"]:
        raise RuntimeError(f"worker runtime failed: {runtime}")
    root, output = Path(root_text), Path(output_text)
    founder, arm = int(spec["founder"]), str(spec["arm"])
    if founder not in FOUNDERS or arm not in ARMS:
        raise ValueError("unregistered cell")
    config = FeedbackPPOConfig(**config_payload)
    packet = np.asarray(spec["incoming_germ"], dtype=np.uint8)
    boundary_packet = make_boundary_packet(packet)
    descendant = vertical.make_vertical_descendant(
        boundary_packet, config, int(spec["birth_seed"])
    )
    boundary = vertical.audit_vertical_boundary(
        Path(spec["parent_checkpoint"]), descendant, boundary_packet, generation=4
    )
    reader = predictor.ConsequenceReader(packet, int(spec["head_seed"]), arm)
    environments = DoorKeyVectorEnv(
        config.num_envs,
        int(spec["training_seed"]),
        config.max_episode_steps,
        "terminal",
    )
    recorder = predictor.TransitionRecorder(environments)
    stem = f"g4_{arm}"
    result_path, checkpoint_path = (
        output / f"{stem}.json",
        output / f"{stem}_checkpoint.pt",
    )
    if result_path.exists() or checkpoint_path.exists():
        raise FileExistsError("refusing to overwrite a cell")
    progress_path = output / "progress" / f"{stem}.json"
    initial_actor = _module_birth_details(descendant)
    initial_soma = matched.soma_environment_digests(descendant, environments)
    initial_head = reader.digest()
    actor_params = [
        *descendant.learner.model.parameters(),
        *descendant.auxiliary_heads.parameters(),
        *descendant.learner.writer.parameters(),
    ]
    head_params = list(reader.model.parameters())
    birth_gates = {
        "boundary_reset_passes": bool(boundary["passes"]),
        "head_parameters_disjoint": {p.data_ptr() for p in actor_params}.isdisjoint(
            {p.data_ptr() for p in head_params}
        ),
        "head_optimizer_fresh": not reader.optimizer.state,
        "head_buffer_fresh": not reader.buffer,
        "head_confirmation_counts_fresh": reader.positive_counts == [0, 0],
        "head_output_constant": torch.equal(
            reader.scores(torch.from_numpy(environments.observations())),
            torch.full((config.num_envs, 2, 8), 0.5),
        ),
        "head_birth_credit_zero": not torch.count_nonzero(
            reader.credit_table(
                torch.from_numpy(environments.observations()),
                torch.full((config.num_envs, 8), 0.125),
            )
        ),
    }
    evaluations, initial_worlds, evaluation_read_only = evaluate(
        descendant, reader, environments, config, 0
    )
    world_rows = {"0": initial_worlds}
    history = []
    last_rollout = last_outcomes = None
    for update in range(1, UPDATES + 1):
        row, last_rollout, last_outcomes = training_step(
            descendant, reader, environments, recorder, config, update
        )
        history.append(row)
        if update % 10 == 0:
            summaries, worlds, untouched = evaluate(
                descendant, reader, environments, config, update
            )
            evaluations.extend(summaries)
            world_rows[str(update)] = worlds
            evaluation_read_only &= untouched
        if update % 5 == 0:
            atomic_json(
                progress_path,
                {
                    "status": "RUNNING",
                    "founder": founder,
                    "arm": arm,
                    "update": update,
                    "updates": UPDATES,
                    "updated_utc": utc_now(),
                    "last_event_counts": row["behavior"]["event_counts"],
                    "last_applied_credit_steps": row["credit"]["applied_nonzero_steps"],
                },
                root,
            )
            print(f"founder {founder} {arm}: {update}/{UPDATES}", flush=True)
    final_soma = matched.soma_environment_digests(descendant, environments)
    final_head = reader.digest()
    payload = checkpoint_payload(
        descendant, reader, environments, config, spec, last_rollout, last_outcomes
    )
    payload_digest = matched.deep_digest(payload)
    _atomic_torch_save(checkpoint_path, payload)
    loaded = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    restored, restored_head, restored_env, restored_config = restore_checkpoint(loaded)
    checkpoint_soma_exact = final_soma == matched.soma_environment_digests(
        restored, restored_env
    )
    checkpoint_head_exact = final_head == restored_head.digest()
    replay_evaluations, replay_worlds, replay_read_only = evaluate(
        restored, restored_head, restored_env, restored_config, UPDATES
    )
    expected_evaluations = [row for row in evaluations if row["update"] == UPDATES]
    final_actor = _module_birth_details(descendant)
    gates = {
        **birth_gates,
        "runtime_qualified": runtime["passes"],
        "all_update_gates": len(history) == UPDATES
        and all(row["passes"] for row in history),
        "expected_transition_count": history[-1]["behavior"]["environment_steps"]
        == EXPECTED_STEPS,
        "all_evaluations_read_only": evaluation_read_only and replay_read_only,
        "complete_evaluation_grid": all(
            [r["update"] for r in evaluations if r["action_mode"] == mode]
            == list(range(0, UPDATES + 1, 10))
            for mode in ACTION_MODES
        ),
        "checkpoint_payload_exact": matched.deep_digest(loaded) == payload_digest,
        "checkpoint_soma_exact": checkpoint_soma_exact,
        "checkpoint_head_exact": checkpoint_head_exact,
        "checkpoint_evaluations_replay": replay_evaluations == expected_evaluations
        and replay_worlds == world_rows[str(UPDATES)],
        "carrier_unchanged_64_bytes": packet.nbytes == 64
        and np.array_equal(descendant.learner.germ, packet)
        and np.array_equal(reader.packet, packet),
        "writer_dormant": initial_actor["digests"]["writer"]
        == final_actor["digests"]["writer"],
        "writer_optimizer_dormant": _optimizer_tensor_count(
            descendant.learner.writer_optimizer
        )
        == 0,
        "empty_head_unchanged": arm != "empty" or initial_head == final_head,
        "wrong_no_confirming_events": arm != "wrong"
        or reader.positive_counts == [0, 0],
        "parent_checkpoint_hash_exact": sha256_file(Path(spec["parent_checkpoint"]))
        == spec["parent_checkpoint_sha256"],
        "source_result_hash_exact": sha256_file(Path(spec["source_result"]))
        == spec["source_result_sha256"],
    }
    result = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "founder": founder,
        "generation": 4,
        "arm": arm,
        "spec": dict(spec),
        "config": asdict(config),
        "incoming_carrier_sha256": carrier_digest(packet),
        "boundary_audit": boundary,
        "initial_actor": initial_actor,
        "initial_head_sha256": initial_head,
        "birth_soma_environment_digests": initial_soma,
        "history": history,
        "evaluations": evaluations,
        "evaluation_world_rows": world_rows,
        "learning_auc": {
            mode: vertical.learning_auc(evaluations, mode) for mode in ACTION_MODES
        },
        "post_prefix_auc": {
            mode: matched.segment_learning_auc(
                evaluations, mode, MATCHED_UPDATES, UPDATES
            )
            for mode in ACTION_MODES
        },
        "cumulative_event_counts": {
            ch: sum(row["behavior"]["event_counts"][ch] for row in history)
            for ch in CHANNELS
        },
        "training_goal_successes": sum(
            row["behavior"]["episode_successes"] for row in history
        ),
        "predictor_training_counts": {
            "positive": reader.positive_counts,
            "negative_target": reader.negative_target_counts,
        },
        "first_applied_credit_update": next(
            (
                row["update"]
                for row in history
                if row["credit"]["applied_nonzero_steps"] > 0
            ),
            None,
        ),
        "final_soma_environment_digests": final_soma,
        "final_head_sha256": final_head,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    atomic_json(result_path, result, root)
    atomic_json(
        progress_path,
        {
            "status": "COMPLETE" if result["completed_cleanly"] else "FAILED_GATES",
            "founder": founder,
            "arm": arm,
            "update": UPDATES,
            "updated_utc": utc_now(),
        },
        root,
    )
    return result


def exact_apparatus_audit(results: Sequence[Mapping[str, Any]]) -> dict:
    expected = {(f, arm) for f in FOUNDERS for arm in ARMS}
    indexed = {(int(row["founder"]), str(row["arm"])): row for row in results}
    gates = {
        "all_15_unique_cells": len(results) == len(expected)
        and set(indexed) == expected
    }
    rows = []
    if gates["all_15_unique_cells"]:
        for founder in FOUNDERS:
            controls = {arm: indexed[founder, arm] for arm in ARMS}
            reference = controls["empty"]
            reference_prefix = [
                row["behavior"] for row in reference["history"][:MATCHED_UPDATES]
            ]
            for arm, result in controls.items():
                prefix_evaluations = [
                    r for r in result["evaluations"] if r["update"] <= MATCHED_UPDATES
                ]
                reference_evaluations = [
                    r
                    for r in reference["evaluations"]
                    if r["update"] <= MATCHED_UPDATES
                ]
                row_gates = {
                    "birth_soma_exact": result["birth_soma_environment_digests"]
                    == reference["birth_soma_environment_digests"],
                    "birth_head_exact": result["initial_head_sha256"]
                    == reference["initial_head_sha256"],
                    "first_rollout_exact": result["history"][0]["behavior"][
                        "rollout_sha256"
                    ]
                    == reference["history"][0]["behavior"]["rollout_sha256"],
                    "all_60_prefix_updates_exact": matched.deep_digest(
                        [row["behavior"] for row in result["history"][:MATCHED_UPDATES]]
                    )
                    == matched.deep_digest(reference_prefix),
                    "prefix_evaluations_exact": prefix_evaluations
                    == reference_evaluations,
                    "prefix_world_rows_exact": all(
                        result["evaluation_world_rows"][str(u)]
                        == reference["evaluation_world_rows"][str(u)]
                        for u in range(0, MATCHED_UPDATES + 1, 10)
                    ),
                }
                if arm in NULL_ARMS:
                    row_gates.update(
                        {
                            "null_100_updates_exact": matched.deep_digest(
                                [r["behavior"] for r in result["history"]]
                            )
                            == matched.deep_digest(
                                [r["behavior"] for r in reference["history"]]
                            ),
                            "null_all_evaluations_exact": result["evaluations"]
                            == reference["evaluations"],
                            "null_all_world_rows_exact": result["evaluation_world_rows"]
                            == reference["evaluation_world_rows"],
                            "null_final_soma_exact": result[
                                "final_soma_environment_digests"
                            ]
                            == reference["final_soma_environment_digests"],
                        }
                    )
                if arm == "correct":
                    row_gates["correct_off_head_prefix_exact"] = [
                        r["predictor_after_sha256"]
                        for r in result["history"][:MATCHED_UPDATES]
                    ] == [
                        r["predictor_after_sha256"]
                        for r in controls["reader_off"]["history"][:MATCHED_UPDATES]
                    ]
                rows.append(
                    {
                        "founder": founder,
                        "arm": arm,
                        "gates": row_gates,
                        "passes": all(row_gates.values()),
                    }
                )
    gates["all_exact_comparisons"] = bool(rows) and all(row["passes"] for row in rows)
    gates["all_cell_gates_pass"] = bool(results) and all(
        row["completed_cleanly"] for row in results
    )
    return {"rows": rows, "gates": gates, "passes": all(gates.values())}


def door_auc(result: Mapping[str, Any], *, post_prefix: bool) -> float:
    scope = "post_prefix_auc" if post_prefix else "learning_auc"
    return float(
        result[scope]["fixed_random"]["events"]["open_door"]["reached_fraction_auc"]
    )


def registered_classification(
    results: Sequence[Mapping[str, Any]], apparatus: Mapping[str, Any]
) -> dict:
    if not apparatus["passes"]:
        return {
            "label": "INVALID_STRUCTURAL_FAILURE",
            "founders": [],
            "numbered_law_verdict_changes": 0,
        }
    indexed = {(int(r["founder"]), str(r["arm"])): r for r in results}
    rows = []
    for founder in FOUNDERS:
        correct, empty, shuffled = (
            indexed[founder, arm] for arm in ("correct", "empty", "shuffled")
        )
        difference = door_auc(correct, post_prefix=True) - door_auc(
            empty, post_prefix=True
        )
        shuffle_difference = door_auc(correct, post_prefix=True) - door_auc(
            shuffled, post_prefix=True
        )
        rows.append(
            {
                "founder": founder,
                "correct_minus_empty_post_prefix": difference,
                "correct_minus_shuffled_post_prefix": shuffle_difference,
                "correct_minus_empty_full_life": door_auc(correct, post_prefix=False)
                - door_auc(empty, post_prefix=False),
                "practical_margin_pass": difference > PRACTICAL_MARGIN,
                "shuffle_contrast_positive": shuffle_difference > 0,
                "passes": difference > PRACTICAL_MARGIN and shuffle_difference > 0,
            }
        )
    return {
        "label": "LEARNED_CONSEQUENCE_BENEFIT_3_OF_3"
        if all(r["passes"] for r in rows)
        else "LEARNED_CONSEQUENCE_BENEFIT_NOT_3_OF_3",
        "founders": rows,
        "matched_updates": MATCHED_UPDATES,
        "practical_margin": PRACTICAL_MARGIN,
        "numbered_law_verdict_changes": 0,
    }


def qualify_sources(root: Path) -> dict:
    output, run = root / "outputs" / SOURCE_RUN, root / "runs" / SOURCE_RUN
    audit = json.loads((output / "consequence_predictor_audit.json").read_text())
    manifest = json.loads((run / "MANIFEST.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    input_rows = matched._verify_manifest_inputs(manifest)
    output_rows = _read_hash_manifest(output / "output_hashes.sha256")
    base = predictor.dose.qualify_source(root)
    parents = list(base["replay_sources"])
    gates = {
        "source_identity": audit.get("run_id") == SOURCE_RUN
        and manifest.get("run_id") == SOURCE_RUN,
        "source_complete": status.get("status") == "COMPLETE"
        and bool(audit.get("completed_cleanly")),
        "source_sentinel_complete": (run / "COMPLETE").is_file()
        and not (run / "FAILED").exists(),
        "source_structural_gates": bool(audit.get("completion_gates"))
        and all(audit["completion_gates"].values()),
        "predictor_qualified_three_founders": audit.get("qualification", {}).get(
            "label"
        )
        == "PREDICTOR_QUALIFIED_3_OF_3",
        "source_inputs_verify": bool(input_rows)
        and all(r["matches"] for r in input_rows),
        "source_outputs_verify": bool(output_rows)
        and all(r["matches"] for r in output_rows),
        "base_sources_qualified": bool(base["passes"]),
        "source_parent_inventory_exact": audit.get("source", {}).get("replay_sources")
        == parents,
        "three_parent_founders": [int(r["founder"]) for r in parents] == list(FOUNDERS),
        "parent_configs_identical": len(
            {canonical_digest(r["config"]) for r in parents}
        )
        == 1,
        "source_has_no_behavior_claim": audit.get("qualification", {}).get(
            "behavioral_benefit_tested"
        )
        is False,
    }
    return {
        "run_id": SOURCE_RUN,
        "audit_path": str(output / "consequence_predictor_audit.json"),
        "manifest_path": str(run / "MANIFEST.json"),
        "parents": parents,
        "base_source": base,
        "input_manifest": matched._manifest_summary(input_rows),
        "output_manifest": matched._manifest_summary(output_rows),
        "gates": gates,
        "passes": all(gates.values()),
    }


def cell_specs(source: Mapping[str, Any]) -> list[dict]:
    parents = {int(r["founder"]): r for r in source["parents"]}
    result = []
    for founder in FOUNDERS:
        parent, seeds = parents[founder], seed_row(founder)
        correct = np.asarray(parent["incoming_germ"], dtype=np.uint8)
        wrong = vertical.initial_carriers(correct)["wrong_frozen"]
        for arm in ARMS:
            packet = (
                wrong
                if arm == "wrong"
                else empty_germ(1)
                if arm == "empty"
                else correct
            )
            result.append(
                {
                    "founder": founder,
                    "arm": arm,
                    "generation": 4,
                    "birth_seed": seeds["birth"],
                    "training_seed": seeds["training"],
                    "head_seed": seeds["head"],
                    "incoming_germ": packet.tolist(),
                    "incoming_carrier_sha256": carrier_digest(packet),
                    "source_correct_carrier_sha256": carrier_digest(correct),
                    "parent_checkpoint": parent["parent_checkpoint"],
                    "parent_checkpoint_sha256": parent["parent_checkpoint_sha256"],
                    "source_result": parent["source_result"],
                    "source_result_sha256": parent["source_result_sha256"],
                }
            )
    return result


def input_paths(workspace: Path, root: Path, source: Mapping[str, Any]) -> list[Path]:
    manifest = json.loads(Path(source["manifest_path"]).read_text())
    paths = [Path(path) for path in manifest["input_sha256"]]
    paths.extend(
        [
            Path(__file__).resolve(),
            workspace / "protocols/DOORKEY_CONSEQUENCE_READER_BEHAVIOR_V1.md",
            workspace / "tests/test_doorkey_consequence_reader_behavior.py",
            workspace / "scripts/run_doorkey_consequence_reader_behavior.sh",
            root / "outputs" / SOURCE_RUN / "consequence_predictor_audit.json",
            root / "outputs" / SOURCE_RUN / "input_hashes.sha256",
            root / "outputs" / SOURCE_RUN / "output_hashes.sha256",
            root / "runs" / SOURCE_RUN / "MANIFEST.json",
            root / "runs" / SOURCE_RUN / "STATUS.json",
            root / "runs" / SOURCE_RUN / "COMPLETE",
        ]
    )
    for founder in FOUNDERS:
        paths.append(root / "outputs" / SOURCE_RUN / f"founder_{founder}.json")
    return sorted({p.resolve() for p in paths})


def benchmark_path(root: Path) -> Path:
    return root / "tmp" / f"{RUN_ID}_benchmark.json"


def benchmark(root: Path) -> dict:
    if (root / "runs" / RUN_ID).exists() or (root / "outputs" / RUN_ID).exists():
        raise FileExistsError("benchmark cannot replace a frozen run input")
    runtime = runtime_qualification()
    source = qualify_sources(root)
    if not runtime["passes"] or not source["passes"]:
        raise RuntimeError("benchmark runtime/source gate failed")
    config = FeedbackPPOConfig(**source["parents"][0]["config"])
    packet = np.asarray(source["parents"][0]["incoming_germ"], dtype=np.uint8)
    # Never use registered descendant seeds to select or time the mechanism.
    spec = {
        "arm": "correct",
        "birth_seed": 330_000_001,
        "training_seed": 340_000_001,
        "head_seed": 350_000_001,
    }
    descendant = vertical.make_vertical_descendant(
        make_boundary_packet(packet), config, spec["birth_seed"]
    )
    reader = predictor.ConsequenceReader(packet, spec["head_seed"], "correct")
    environments = DoorKeyVectorEnv(
        config.num_envs, spec["training_seed"], config.max_episode_steps, "terminal"
    )
    recorder = predictor.TransitionRecorder(environments)
    timings = {}
    for name, updates in (("prefix", range(1, 9)), ("enabled", range(61, 69))):
        started = time.monotonic()
        for update in updates:
            _, rollout, outcomes = training_step(
                descendant, reader, environments, recorder, config, update
            )
        timings[name] = (time.monotonic() - started) / 8
    started = time.monotonic()
    _, _, read_only = evaluate(descendant, reader, environments, config, 68)
    timings["evaluation_pair"] = time.monotonic() - started
    payload = checkpoint_payload(
        descendant, reader, environments, config, spec, rollout, outcomes
    )
    restored, restored_reader, restored_env, _ = restore_checkpoint(deepcopy(payload))
    restore_exact = (
        reader.digest() == restored_reader.digest()
        and matched.soma_environment_digests(descendant, environments)
        == matched.soma_environment_digests(restored, restored_env)
    )
    if not read_only or not restore_exact:
        raise RuntimeError("benchmark evaluation or state reconstruction failed")
    cell_seconds = (
        MATCHED_UPDATES * timings["prefix"]
        + (UPDATES - MATCHED_UPDATES) * timings["enabled"]
        + 12 * timings["evaluation_pair"]
        + 5
    )
    projected = math.ceil(REGISTERED_CELLS / MAX_WORKERS) * cell_seconds * 1.5 + 60
    result = {
        "run_id": RUN_ID,
        "non_scientific": True,
        "measured_utc": utc_now(),
        "source_sha256": sha256_file(Path(__file__)),
        "timings_seconds": timings,
        "estimated_cell_seconds": cell_seconds,
        "projected_seconds_four_workers": projected,
        "contention_safety_multiplier": 1.5,
        "fixed_overhead_seconds": 60,
        "must_detach": projected > 600,
        "checkpoint_reconstruction_exact": restore_exact,
        "runtime": runtime,
    }
    atomic_json(benchmark_path(root), result, root)
    print(json.dumps(result, indent=2), flush=True)
    return result


def prepare_run(root: Path) -> dict:
    output, run = root / "outputs" / RUN_ID, root / "runs" / RUN_ID
    if output.exists() or run.exists():
        raise FileExistsError("refusing an existing immutable run directory")
    runtime = runtime_qualification()
    source = qualify_sources(root)
    if not runtime["passes"] or not source["passes"]:
        raise RuntimeError("runtime/source qualification failed")
    timing = json.loads(benchmark_path(root).read_text())
    if timing.get("source_sha256") != sha256_file(Path(__file__)):
        raise RuntimeError("benchmark does not describe the frozen runner")
    disk = _disk_preflight(root, 256 * 1024**2)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk safety margin failed")
    workspace = Path(__file__).resolve().parents[2]
    paths = input_paths(workspace, root, source) + [benchmark_path(root)]
    hashes = {str(p): sha256_file(p) for p in paths}
    specs = cell_specs(source)
    config = source["parents"][0]["config"]
    if (
        int(config["num_envs"]) * int(config["rollout_steps"]) * UPDATES
        != EXPECTED_STEPS
    ):
        raise ValueError("configuration differs from the frozen transition count")
    output.mkdir(parents=True)
    run.mkdir(parents=True)
    for founder in FOUNDERS:
        (output / f"founder_{founder}" / "progress").mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "source_run_id": SOURCE_RUN,
        "prepared_utc": utc_now(),
        "stage": "fresh-descendant learned-consequence behavior comparison",
        "source": source,
        "config": config,
        "cell_specs": specs,
        "workers": MAX_WORKERS,
        "threads_per_worker": 1,
        "runtime": runtime,
        "benchmark": timing,
        "disk_preflight": disk,
        "environment": environment_manifest(),
        "input_sha256": hashes,
        "contract_digest": canonical_digest(hashes),
        "repository_head": git_head(workspace),
        "registered_cells": REGISTERED_CELLS,
        "registered_transitions": REGISTERED_TRANSITIONS,
        "updates": UPDATES,
        "matched_updates": MATCHED_UPDATES,
        "practical_margin": PRACTICAL_MARGIN,
        "scientific_outcome_is_completion_gate": False,
        "external_root": str(root),
        "output_dir": str(output),
    }
    atomic_json(run / "MANIFEST.json", manifest, root)
    write_hash_manifest(paths, output / "input_hashes.sha256", root)
    atomic_json(
        run / "STATUS.json",
        {
            "status": "PREPARED",
            "run_id": RUN_ID,
            "updated_utc": utc_now(),
            "completed_cells": 0,
            "registered_cells": REGISTERED_CELLS,
            "projected_seconds": timing["projected_seconds_four_workers"],
        },
        root,
    )
    return manifest


def _verify_prepared(root: Path) -> dict:
    run = root / "runs" / RUN_ID
    manifest = json.loads((run / "MANIFEST.json").read_text())
    status = json.loads((run / "STATUS.json").read_text())
    if manifest.get("run_id") != RUN_ID or status.get("status") != "PREPARED":
        raise RuntimeError("run is not in the uniquely launchable PREPARED state")
    rows = matched._verify_manifest_inputs(manifest)
    if not rows or not all(r["matches"] for r in rows):
        raise RuntimeError("prepared inputs have changed")
    source = qualify_sources(root)
    expected_inputs = input_paths(Path(__file__).resolve().parents[2], root, source) + [
        benchmark_path(root)
    ]
    if (
        manifest.get("source") != source
        or manifest.get("cell_specs") != cell_specs(source)
        or manifest.get("config") != source["parents"][0]["config"]
        or set(manifest["input_sha256"]) != {str(path) for path in expected_inputs}
        or manifest.get("contract_digest") != canonical_digest(manifest["input_sha256"])
        or manifest.get("matched_updates") != MATCHED_UPDATES
        or manifest.get("registered_cells") != REGISTERED_CELLS
        or manifest.get("workers") != MAX_WORKERS
        or manifest.get("practical_margin") != PRACTICAL_MARGIN
    ):
        raise RuntimeError("prepared registry or contract differs from frozen code")
    return manifest


def launch_detached(root: Path) -> dict:
    if not (root / "runs" / RUN_ID).exists():
        prepare_run(root)
    manifest = _verify_prepared(root)
    stdout = root / "logs" / f"{RUN_ID}.stdout.log"
    stderr = root / "logs" / f"{RUN_ID}.stderr.log"
    command = [
        sys.executable,
        "-m",
        "laws_confirmation.doorkey_consequence_reader_behavior",
        "--external-root",
        str(root),
        "--run",
    ]
    with stdout.open("xb") as out_handle, stderr.open("xb") as err_handle:
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL,
            stdout=out_handle,
            stderr=err_handle,
            start_new_session=True,
        )
    run = root / "runs" / RUN_ID
    launch = {
        "run_id": RUN_ID,
        "pid": process.pid,
        "launched_utc": utc_now(),
        "command": command,
        "stdout_log": str(stdout),
        "stderr_log": str(stderr),
        "status": str(run / "STATUS.json"),
        "progress": str(root / "outputs" / RUN_ID / "progress.json"),
        "cell_progress": str(root / "outputs" / RUN_ID / "founder_N" / "progress"),
        "complete": str(run / "COMPLETE"),
        "failed": str(run / "FAILED"),
        "estimated_seconds": manifest["benchmark"]["projected_seconds_four_workers"],
        "polling_owner": "user",
    }
    atomic_text(run / "RUN.pid", f"{process.pid}\n", root)
    atomic_json(run / "LAUNCH.json", launch, root)
    print(json.dumps(launch, indent=2), flush=True)
    # Intentionally no wait(), poll(), process inspection, or status read here.
    return launch


def markdown_report(study: Mapping[str, Any]) -> str:
    lines = [
        "# DoorKey learned-consequence behavioral comparison",
        "",
        f"Run: `{RUN_ID}`.",
        f"Structural completion: `{study['completed_cleanly']}`.",
        f"Frozen outcome: `{study['registered_classification']['label']}`.",
        "",
        "Three existing founder lineages, fresh G4 actor/head/training seeds, exact",
        "60-update matched prefix, then 40 updates with the selected learned credit.",
        "The warm-up was selected after the earlier prediction audit and is not an",
        "independent biological constant. No predictor weights were inherited.",
        "",
        "| Founder | Correct − empty late door AUC | Correct − shuffled late door AUC | Correct − empty full-life AUC | Pass |",
        "|---|---:|---:|---:|---|",
    ]
    for row in study["registered_classification"].get("founders", []):
        lines.append(
            f"| {row['founder']} | {row['correct_minus_empty_post_prefix']:+.6f} | {row['correct_minus_shuffled_post_prefix']:+.6f} | {row['correct_minus_empty_full_life']:+.6f} | {row['passes']} |"
        )
    lines.extend(
        [
            "",
            "Door opening is the primary subgoal endpoint, not final goal success.",
            "All final success counts, intermediate evaluations, context action counts,",
            "head learning, and credit magnitudes are retained in individual cell files.",
            "This run does not test three-generation renewal of the new reader, learned",
            "ontology, or any universal law. No numbered-law verdict changes automatically.",
            "",
        ]
    )
    return "\n".join(lines)


def run_study(root: Path) -> int:
    run, output = root / "runs" / RUN_ID, root / "outputs" / RUN_ID
    # Refusal must never overwrite a completed, failed, or already-running run.
    current = json.loads((run / "STATUS.json").read_text())
    if (
        current.get("status") != "PREPARED"
        or (run / "COMPLETE").exists()
        or (run / "FAILED").exists()
    ):
        raise RuntimeError("refusing to restart an initialized execution")
    (run / "EXECUTION.lock").mkdir()
    started = time.monotonic()
    try:
        manifest = _verify_prepared(root)
        runtime = runtime_qualification()
        if not runtime["passes"]:
            raise RuntimeError("full-run runtime qualification failed")
        atomic_text(run / "RUN.pid", f"{os.getpid()}\n", root)
        atomic_json(
            run / "STATUS.json",
            {
                "status": "RUNNING",
                "run_id": RUN_ID,
                "started_utc": utc_now(),
                "completed_cells": 0,
                "registered_cells": REGISTERED_CELLS,
            },
            root,
        )
        results = []
        with ProcessPoolExecutor(
            max_workers=MAX_WORKERS, mp_context=multiprocessing.get_context("spawn")
        ) as executor:
            futures = {
                executor.submit(
                    train_cell,
                    spec,
                    manifest["config"],
                    str(root),
                    str(output / f"founder_{spec['founder']}"),
                ): spec
                for spec in manifest["cell_specs"]
            }
            for future in as_completed(futures):
                results.append(future.result())
                progress = {
                    "status": "RUNNING",
                    "run_id": RUN_ID,
                    "completed_cells": len(results),
                    "registered_cells": REGISTERED_CELLS,
                    "updated_utc": utc_now(),
                }
                atomic_json(output / "progress.json", progress, root)
                atomic_json(run / "STATUS.json", progress, root)
                print(f"completed {len(results)}/{REGISTERED_CELLS} cells", flush=True)
        results.sort(key=lambda row: (row["founder"], ARMS.index(row["arm"])))
        apparatus = exact_apparatus_audit(results)
        classification = registered_classification(results, apparatus)
        input_rows = matched._verify_manifest_inputs(manifest)
        expected_packets = {
            (s["founder"], s["arm"]): s["incoming_carrier_sha256"]
            for s in manifest["cell_specs"]
        }
        gates = {
            "runtime_qualified": runtime["passes"],
            "source_qualified": manifest["source"]["passes"],
            "all_15_cells_complete": len(results) == REGISTERED_CELLS
            and all(r["completed_cleanly"] for r in results),
            "exact_apparatus_passes": apparatus["passes"],
            "all_inputs_still_verify": bool(input_rows)
            and all(r["matches"] for r in input_rows),
            "carrier_schedule_exact": all(
                r["incoming_carrier_sha256"] == expected_packets[r["founder"], r["arm"]]
                for r in results
            ),
            "scientific_outcome_not_a_completion_gate": True,
        }
        study = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "generated_utc": utc_now(),
            "source_run_id": SOURCE_RUN,
            "runtime": runtime,
            "elapsed_seconds": time.monotonic() - started,
            "registered_cells": REGISTERED_CELLS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "exact_apparatus": apparatus,
            "registered_classification": classification,
            "cell_summaries": [
                {
                    "founder": r["founder"],
                    "arm": r["arm"],
                    "completed_cleanly": r["completed_cleanly"],
                    "full_life_auc": r["learning_auc"],
                    "post_prefix_auc": r["post_prefix_auc"],
                    "final_evaluations": [
                        e for e in r["evaluations"] if e["update"] == UPDATES
                    ],
                    "cumulative_event_counts": r["cumulative_event_counts"],
                    "first_applied_credit_update": r["first_applied_credit_update"],
                    "predictor_training_counts": r["predictor_training_counts"],
                    "completion_gates": r["completion_gates"],
                }
                for r in results
            ],
            "completion_gates": gates,
            "completed_cleanly": all(gates.values()),
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output / "consequence_reader_behavior.json", study, root)
        atomic_text(output / "audit.md", markdown_report(study), root)
        atomic_json(
            output / "progress.json",
            {
                "status": "COMPLETE" if study["completed_cleanly"] else "FAILED_GATES",
                "completed_cells": len(results),
                "registered_cells": REGISTERED_CELLS,
                "updated_utc": utc_now(),
            },
            root,
        )
        paths = sorted(
            p
            for p in output.rglob("*")
            if p.is_file() and p.name != "output_hashes.sha256"
        )
        write_hash_manifest(paths, output / "output_hashes.sha256", root)
        outputs = _read_hash_manifest(output / "output_hashes.sha256")
        verified = bool(outputs) and all(r["matches"] for r in outputs)
        success = study["completed_cleanly"] and verified
        status = {
            "status": "COMPLETE" if success else "FAILED_GATES",
            "run_id": RUN_ID,
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
            "completed_cells": len(results),
            "registered_cells": REGISTERED_CELLS,
            "completed_cleanly": study["completed_cleanly"],
            "output_manifest_self_verifies": verified,
            "registered_classification": classification["label"],
            "registered_transitions": REGISTERED_TRANSITIONS,
            "max_workers": MAX_WORKERS,
            "cpu_affinity": runtime["values"]["cpu_affinity"],
        }
        atomic_json(run / "STATUS.json", status, root)
        atomic_text(
            run / ("COMPLETE" if success else "FAILED"),
            status["completed_utc"] + "\n",
            root,
        )
        print(output / "audit.md", flush=True)
        return 0 if success else 1
    except Exception as error:
        failure = {
            "status": "FAILED",
            "run_id": RUN_ID,
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run / "STATUS.json", failure, root)
        atomic_text(run / "FAILED", failure["failed_utc"] + "\n", root)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--benchmark", action="store_true")
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--detach", action="store_true")
    group.add_argument("--run", action="store_true")
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        manifest = prepare_run(root)
        print(
            json.dumps(
                {
                    "status": "PREPARED",
                    "run_id": RUN_ID,
                    "benchmark": manifest["benchmark"],
                    "input_files": len(manifest["input_sha256"]),
                },
                indent=2,
            )
        )
    elif args.detach:
        launch_detached(root)
    else:
        return run_study(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
