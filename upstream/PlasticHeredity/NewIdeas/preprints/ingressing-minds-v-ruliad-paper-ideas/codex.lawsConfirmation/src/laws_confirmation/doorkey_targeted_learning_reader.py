"""Behavioral test of gradient-selected, action-blind DoorKey credit rules."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import platform
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from . import doorkey_counterfactual_gradient as gradient_audit
from . import doorkey_learning_only_reader as source_reader
from . import doorkey_matched_disposition as matched
from . import doorkey_vertical_multifounder as source_confirmation
from . import doorkey_vertical_scout as frozen_vertical
from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import GermSchema, carrier_digest, empty_germ, read_germ
from .doorkey_env import CAUSAL_CHAIN
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
    _finite_credit_history,
    _first_evaluation_reach,
    _forward_sequence_values,
    _masked_mse,
    _module_birth_details,
    actor_advantage_for_arm,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import FeedbackPPOConfig, _apply_prior, _optimizer_tensor_count
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


RUN_ID = "doorkey_targeted_learning_reader_v1_attempt1"
SOURCE_RUN = source_reader.RUN_ID
RATIONALE_RUN = gradient_audit.RUN_ID
FOUNDERS = (1, 2, 3)
GENERATION = 4
ARMS = (
    "target_trace_correct",
    "event_only_correct",
    "target_trace_wrong",
    "target_trace_reader_off",
    "learning_silence",
)
NULL_ALIAS_ARMS = (
    "target_trace_wrong",
    "target_trace_reader_off",
    "learning_silence",
)
ACTIVE_ARMS = ("target_trace_correct", "event_only_correct")
CREDIT_MODES = ("target_trace", "event_only", "off")
UPDATES = frozen_vertical.UPDATES
EXPECTED_STEPS = frozen_vertical.EXPECTED_STEPS
MAX_WORKERS = 4
REGISTERED_CELLS = len(FOUNDERS) * len(ARMS)
REGISTERED_TRANSITIONS = REGISTERED_CELLS * EXPECTED_STEPS


def seed_row(founder: int) -> dict[str, int]:
    """Return the prospectively frozen fresh G4 seed pair."""

    if founder not in FOUNDERS:
        raise ValueError("unregistered founder")
    return {
        "birth": 220_000_000 + 100_000 * founder,
        "training": 230_000_000 + 100_000 * founder,
    }


SEEDS = {founder: seed_row(founder) for founder in FOUNDERS}


def credit_mode_for_arm(arm: str) -> str:
    """Return the frozen post-standardization credit rule for an arm."""

    if arm in {
        "target_trace_correct",
        "target_trace_wrong",
        "learning_silence",
    }:
        return "target_trace"
    if arm == "event_only_correct":
        return "event_only"
    if arm == "target_trace_reader_off":
        return "off"
    raise ValueError(f"unregistered targeted-reader arm: {arm}")


def learning_carrier_for(
    arm: str,
    incoming: np.ndarray,
) -> np.ndarray | None:
    """Expose only the inherited packet, and only to an enabled reader."""

    mode = credit_mode_for_arm(arm)
    if mode == "off":
        return None
    return np.asarray(incoming, dtype=np.uint8)


def targeted_actor_advantage(
    rollout: CausalCreditRollout,
    carrier: np.ndarray | None,
    credit_mode: str,
) -> tuple[torch.Tensor, dict[str, bool], dict[str, Any]]:
    """Add frozen positive event or target-trace credit after standardization."""

    if credit_mode not in CREDIT_MODES:
        raise ValueError("unknown targeted credit mode")
    if credit_mode == "off" and carrier is not None:
        raise ValueError("reader-off mode cannot receive a carrier")
    if credit_mode != "off" and carrier is None:
        raise ValueError("enabled targeted reader requires a carrier")

    base, signals = actor_advantage_for_arm(rollout, "phase_actor")
    actor_advantage = base.clone()
    channel_rows: dict[str, Any] = {}
    total_confirmed = 0
    total_target_trace = 0
    total_event_only = 0
    total_credited = 0
    total_extra_predecessor = 0
    packet_digest = None
    packet_present = carrier is not None
    if carrier is not None:
        packet = np.asarray(carrier)
        if packet.dtype != np.uint8 or packet.shape != (1, 64) or packet.nbytes != 64:
            raise ValueError("targeted reader requires one exact 64-byte packet")
        packet_digest = carrier_digest(packet)

    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        event = rollout.event_rewards[:, :, channel] > 0
        if carrier is None:
            confirmed = torch.zeros_like(event)
            trace = torch.zeros_like(event)
            target_trace = torch.zeros_like(event)
            active = False
            target_action = None
            trust = None
            amplitude = 0.0
        else:
            support = gradient_audit.confirmed_trace_support(
                rollout,
                np.asarray(carrier),
                channel,
            )
            confirmed = support["confirmed"]
            trace = support["trace"]
            target_trace = support["target_trace"]
            active = bool(support["active"])
            target_action = int(support["target_action"])
            trust = int(support["trust"])
            amplitude = float(support["amplitude"])

        event_only = confirmed
        selected = (
            target_trace
            if credit_mode == "target_trace"
            else event_only
            if credit_mode == "event_only"
            else torch.zeros_like(event)
        )
        delta = selected.to(base.dtype) * amplitude
        actor_advantage += delta

        confirmed_count = int(torch.count_nonzero(confirmed).item())
        trace_count = int(torch.count_nonzero(trace).item())
        target_count = int(torch.count_nonzero(target_trace).item())
        event_only_count = int(torch.count_nonzero(event_only).item())
        credited_count = int(torch.count_nonzero(selected).item())
        extra_count = target_count - event_only_count
        channel_name = CHANNELS[channel]
        channel_rows[channel_name] = {
            "record_active": active,
            "target_action": target_action,
            "trust": trust,
            "amplitude": amplitude,
            "event_count": int(torch.count_nonzero(event).item()),
            "confirmed_event_count": confirmed_count,
            "confirmed_trace_steps": trace_count,
            "target_trace_steps": target_count,
            "event_only_steps": event_only_count,
            "available_extra_predecessor_steps": extra_count,
            "credited_steps": credited_count,
            "trace_sha256": matched.deep_digest(trace),
            "target_trace_sha256": matched.deep_digest(target_trace),
            "delta_sha256": matched.deep_digest(delta),
        }
        total_confirmed += confirmed_count
        total_target_trace += target_count
        total_event_only += event_only_count
        total_credited += credited_count
        total_extra_predecessor += extra_count

    audit = {
        "credit_mode": credit_mode,
        "packet_present": packet_present,
        "packet_sha256": packet_digest,
        "channels": channel_rows,
        "confirmed_event_count": total_confirmed,
        "target_trace_steps": total_target_trace,
        "event_only_steps": total_event_only,
        "available_extra_predecessor_steps": total_extra_predecessor,
        "credited_steps": total_credited,
        "base_actor_advantage_sha256": matched.deep_digest(base),
        "targeted_actor_advantage_sha256": matched.deep_digest(actor_advantage),
        "differs_from_base": not torch.equal(actor_advantage, base),
    }
    return actor_advantage, signals, audit


def targeted_ppo_update(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    *,
    learning_carrier: np.ndarray | None,
    credit_mode: str,
    germ_mode: str,
) -> dict[str, Any]:
    """Apply the frozen PPO update with one post-standardization credit rule."""

    if germ_mode != "blind":
        raise ValueError("targeted learning readers require a blind action path")
    actor_advantage, signals, credit = targeted_actor_advantage(
        rollout,
        learning_carrier,
        credit_mode,
    )
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
                ratio,
                1.0 - config.clip_epsilon,
                1.0 + config.clip_epsilon,
            )
            policy_loss = -torch.minimum(
                ratio * advantage,
                clipped_ratio * advantage,
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
    result.update(
        {
            "actor_channel_signal": signals,
            "actor_advantage_nonzero": bool(torch.count_nonzero(actor_advantage)),
            "actor_advantage_nonzero_count": int(
                torch.count_nonzero(actor_advantage)
            ),
            "credit_audit": credit,
        }
    )
    return result


def qualify_sources(root: Path) -> dict[str, Any]:
    """Verify the failed reader, exact gradient audit, and three G3 parents."""

    learning_source = gradient_audit.qualify_source(root)
    output_dir = root / "outputs" / RATIONALE_RUN
    run_dir = root / "runs" / RATIONALE_RUN
    audit_path = output_dir / "gradient_audit.json"
    manifest_path = run_dir / "MANIFEST.json"
    status_path = run_dir / "STATUS.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    input_rows = matched._verify_manifest_inputs(manifest)
    output_rows = _read_hash_manifest(output_dir / "output_hashes.sha256")
    recommendations = audit.get("geometric_admissibility", {}).get(
        "recommendations",
        {},
    )
    gates = {
        "learning_source_qualified": bool(learning_source["passes"]),
        "rationale_run_ids_exact": audit.get("run_id") == RATIONALE_RUN
        and audit.get("source_run_id") == SOURCE_RUN
        and manifest.get("run_id") == RATIONALE_RUN,
        "rationale_complete": status.get("status") == "COMPLETE"
        and bool(audit.get("completed_cleanly")),
        "rationale_complete_sentinel_present": (run_dir / "COMPLETE").is_file(),
        "rationale_failed_sentinel_absent": not (run_dir / "FAILED").exists(),
        "rationale_completion_gates_pass": bool(audit.get("completion_gates"))
        and all(audit.get("completion_gates", {}).values()),
        "target_trace_recommended_for_both_channels": all(
            recommendations.get(channel, {}).get("candidate")
            == "trace_target_only"
            for channel in ("key", "door")
        ),
        "rationale_behavior_claim_absent": not bool(
            audit.get("geometric_admissibility", {}).get(
                "behavioral_success_claimed",
                True,
            )
        ),
        "rationale_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "rationale_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
        "rationale_manifest_self_verified": bool(
            status.get("output_manifest_self_verifies")
        ),
    }
    parents = [
        {
            "founder": int(row["founder"]),
            "checkpoint": row["parent_checkpoint"],
            "checkpoint_sha256": row["parent_checkpoint_sha256"],
            "outgoing_carrier": row["diagnostic_carrier"],
            "outgoing_carrier_sha256": row["diagnostic_carrier_sha256"],
            "config": row["config"],
            "source_result": row["source_result"],
            "source_result_sha256": row["source_result_sha256"],
        }
        for row in learning_source["replay_sources"]
    ]
    return {
        "learning_source": learning_source,
        "gradient_audit": {
            "audit_path": str(audit_path),
            "manifest_path": str(manifest_path),
            "status_path": str(status_path),
            "input_manifest": matched._manifest_summary(input_rows),
            "output_manifest": matched._manifest_summary(output_rows),
            "recommendations": recommendations,
        },
        "parents": parents,
        "gates": gates,
        "passes": all(gates.values()),
    }


def cell_specs(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build the frozen five-arm registry for three new G4 seed pairs."""

    parents = {int(row["founder"]): row for row in source["parents"]}
    specs: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        parent = parents[founder]
        correct = np.asarray(parent["outgoing_carrier"], dtype=np.uint8)
        controls = source_confirmation.initial_carriers(correct)
        wrong = np.asarray(controls["wrong_frozen"], dtype=np.uint8)
        silence = empty_germ(1, GermSchema())
        for arm in ARMS:
            if arm == "target_trace_wrong":
                incoming = wrong
            elif arm == "learning_silence":
                incoming = silence
            else:
                incoming = correct
            specs.append(
                {
                    "founder": founder,
                    "generation": GENERATION,
                    "arm": arm,
                    "credit_mode": credit_mode_for_arm(arm),
                    "birth_seed": seed_row(founder)["birth"],
                    "training_seed": seed_row(founder)["training"],
                    "parent_checkpoint": parent["checkpoint"],
                    "parent_checkpoint_sha256": parent["checkpoint_sha256"],
                    "source_result": parent["source_result"],
                    "source_result_sha256": parent["source_result_sha256"],
                    "source_carrier_sha256": carrier_digest(correct),
                    "incoming_germ": incoming.tolist(),
                    "wrong_germ_sha256": carrier_digest(wrong),
                }
            )
    return specs


def _evaluate_cell(
    descendant: CausalCreditDescendant,
    config: FeedbackPPOConfig,
    action_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return source_reader._evaluate_cell(
        descendant,
        config,
        "blind",
        action_mode,
    )


def _clean_history_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Remove intervention labels while retaining behavior and PPO metrics."""

    return {
        key: value
        for key, value in row.items()
        if key not in {"credit_audit", "credit_mode", "germ_mode"}
    }


def behavior_digest(
    history: Sequence[Mapping[str, Any]],
    evaluations: Sequence[Mapping[str, Any]],
    final_evaluations: Mapping[str, Any],
    final_world_rows: Mapping[str, Any],
) -> str:
    payload = {
        "history": [_clean_history_row(row) for row in history],
        "evaluations": [matched._clean_evaluation(row) for row in evaluations],
        "final_evaluations": {
            mode: matched._clean_evaluation(row)
            for mode, row in final_evaluations.items()
        },
        "final_world_rows": final_world_rows,
    }
    return matched.deep_digest(payload)


def _train_cell(
    spec: Mapping[str, Any],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Train one new G4 descendant under a frozen targeted credit rule."""

    founder = int(spec["founder"])
    arm = str(spec["arm"])
    if founder not in FOUNDERS or arm not in ARMS:
        raise ValueError("unregistered targeted-reader cell")
    birth_seed = int(spec["birth_seed"])
    training_seed = int(spec["training_seed"])
    credit_mode = credit_mode_for_arm(arm)
    if str(spec["credit_mode"]) != credit_mode:
        raise ValueError("registered credit mode mismatch")
    incoming = np.asarray(spec["incoming_germ"], dtype=np.uint8)
    packet = make_boundary_packet(incoming)
    stem = f"g4_{arm}"
    result_path = output_dir / f"{stem}.json"
    checkpoint_path = output_dir / f"{stem}_checkpoint.pt"
    progress_path = output_dir / "progress" / f"{stem}.json"
    if result_path.is_file() != checkpoint_path.is_file():
        raise RuntimeError(f"partial resumable artifacts for founder {founder} {arm}")
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("run_id") != RUN_ID
            or result.get("founder") != founder
            or result.get("generation") != GENERATION
            or result.get("arm") != arm
            or result.get("credit_mode") != credit_mode
            or result.get("birth_seed") != birth_seed
            or result.get("training_seed") != training_seed
            or result.get("updates") != UPDATES
            or result.get("incoming_carrier_sha256") != packet.digest()
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable result for founder {founder} {arm}")
        print(f"founder {founder} {stem} already complete; resuming", flush=True)
        return result

    atomic_json(
        progress_path,
        {
            "status": "STARTING",
            "updated_utc": utc_now(),
            "founder": founder,
            "generation": GENERATION,
            "arm": arm,
            "credit_mode": credit_mode,
            "update": 0,
        },
        output_root,
    )
    descendant = frozen_vertical.make_vertical_descendant(packet, config, birth_seed)
    boundary = frozen_vertical.audit_vertical_boundary(
        Path(spec["parent_checkpoint"]),
        descendant,
        packet,
        generation=GENERATION,
    )
    initial_state = _module_birth_details(descendant)
    initial_germ = descendant.learner.germ.copy()
    incoming_read = read_germ(initial_germ)

    evaluations: list[dict[str, Any]] = []
    for action_mode in ACTION_MODES:
        evaluation, _ = _evaluate_cell(descendant, config, action_mode)
        evaluation["update"] = 0
        evaluations.append(evaluation)
    birth_evaluation_sha256 = source_reader._birth_evaluation_digest(evaluations)

    environments = DoorKeyVectorEnv(
        config.num_envs,
        training_seed,
        config.max_episode_steps,
        "terminal",
    )
    birth_soma_environment_digests = matched.soma_environment_digests(
        descendant,
        environments,
    )
    history: list[dict[str, Any]] = []
    total_episodes = 0
    total_successes = 0
    cumulative_events = {channel: 0 for channel in CHANNELS}
    cumulative_confirmed = {"key": 0, "door": 0}
    cumulative_target_steps = {"key": 0, "door": 0}
    cumulative_event_steps = {"key": 0, "door": 0}
    cumulative_credited_steps = {"key": 0, "door": 0}
    cumulative_extra_predecessor = {"key": 0, "door": 0}
    first_signal_update: dict[str, int | None] = {
        channel: None for channel in CHANNELS
    }
    first_credit_update: int | None = None
    first_extra_predecessor_update: int | None = None
    semantics_accumulator: dict[str, bool] = {}
    packet_unchanged_each_update = True
    last_rollout: CausalCreditRollout | None = None
    first_rollout_sha256: str | None = None
    first_completed_rows_sha256: str | None = None
    first_pre_update_digests: dict[str, str] | None = None

    for update in range(1, UPDATES + 1):
        rollout, completed = frozen_vertical.collect_vertical_rollout(
            descendant,
            environments,
            config,
            "blind",
        )
        last_rollout = rollout
        rollout_sha256 = matched.deep_digest(vars(rollout))
        completed_sha256 = matched.deep_digest(completed)
        if update == 1:
            first_rollout_sha256 = rollout_sha256
            first_completed_rows_sha256 = completed_sha256
            first_pre_update_digests = matched.soma_environment_digests(
                descendant,
                environments,
            )
        semantics = rollout_semantics(rollout)
        for name, passed in semantics.items():
            semantics_accumulator[name] = bool(
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

        learning_carrier = learning_carrier_for(arm, descendant.learner.germ)
        packet_before = descendant.learner.germ.copy()
        metrics = targeted_ppo_update(
            descendant,
            rollout,
            config,
            learning_carrier=learning_carrier,
            credit_mode=credit_mode,
            germ_mode="blind",
        )
        packet_unchanged_each_update &= bool(
            np.array_equal(descendant.learner.germ, packet_before)
            and np.array_equal(descendant.learner.germ, initial_germ)
        )
        credit = dict(metrics["credit_audit"])
        for channel in ("key", "door"):
            channel_credit = credit["channels"][channel]
            cumulative_confirmed[channel] += int(
                channel_credit["confirmed_event_count"]
            )
            cumulative_target_steps[channel] += int(
                channel_credit["target_trace_steps"]
            )
            cumulative_event_steps[channel] += int(
                channel_credit["event_only_steps"]
            )
            cumulative_credited_steps[channel] += int(
                channel_credit["credited_steps"]
            )
            cumulative_extra_predecessor[channel] += int(
                channel_credit["available_extra_predecessor_steps"]
            )
        if credit["credited_steps"] and first_credit_update is None:
            first_credit_update = update
        if (
            credit["available_extra_predecessor_steps"]
            and first_extra_predecessor_update is None
        ):
            first_extra_predecessor_update = update

        update_successes = sum(bool(row["success"]) for row in completed)
        total_episodes += len(completed)
        total_successes += update_successes
        post_update_digests = matched.soma_environment_digests(
            descendant,
            environments,
        )
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
            "rollout_sha256": rollout_sha256,
            "completed_episode_rows_sha256": completed_sha256,
            "germ_mode": "blind",
            "credit_mode": credit_mode,
            "post_update_soma_environment_sha256": post_update_digests[
                "aggregate"
            ],
            **metrics,
        }
        history.append(row)
        latest: list[dict[str, Any]] = []
        if update % 10 == 0:
            for action_mode in ACTION_MODES:
                evaluation, _ = _evaluate_cell(descendant, config, action_mode)
                evaluation["update"] = update
                evaluations.append(evaluation)
                latest.append(evaluation)
        if update % 5 == 0:
            atomic_json(
                progress_path,
                {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    "founder": founder,
                    "generation": GENERATION,
                    "arm": arm,
                    "credit_mode": credit_mode,
                    "update": update,
                    "updates": UPDATES,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_successes": total_successes,
                    "cumulative_event_counts": dict(cumulative_events),
                    "cumulative_confirmed_events": dict(cumulative_confirmed),
                    "cumulative_credited_steps": dict(cumulative_credited_steps),
                    "latest_evaluations": latest,
                },
                output_root,
            )
            print(
                f"founder {founder} {stem} update {update}/{UPDATES} "
                f"events={cumulative_events['key']}/"
                f"{cumulative_events['door']}/{cumulative_events['goal']} "
                f"credited={sum(cumulative_credited_steps.values())}",
                flush=True,
            )

    if (
        last_rollout is None
        or first_rollout_sha256 is None
        or first_completed_rows_sha256 is None
        or first_pre_update_digests is None
    ):
        raise RuntimeError("targeted-reader cell missed a registered state capture")

    final_evaluations: dict[str, Any] = {}
    final_world_rows: dict[str, Any] = {}
    final_replay = True
    for action_mode in ACTION_MODES:
        evaluation, rows = _evaluate_cell(descendant, config, action_mode)
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
    final_digests = matched.soma_environment_digests(descendant, environments)
    behavior_fingerprint = behavior_digest(
        history,
        evaluations,
        final_evaluations,
        final_world_rows,
    )
    checkpoint_payload = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "source_run_id": SOURCE_RUN,
        "rationale_run_id": RATIONALE_RUN,
        "founder": founder,
        "generation": GENERATION,
        "arm": arm,
        "credit_mode": credit_mode,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "reward_mode": "terminal",
        "germ_mode": "blind",
        "config": asdict(config),
        "germ": descendant.learner.germ,
        "model_state_dict": descendant.learner.model.state_dict(),
        "auxiliary_heads_state_dict": descendant.auxiliary_heads.state_dict(),
        "writer_state_dict": descendant.learner.writer.state_dict(),
        "optimizer_state_dict": descendant.learner.optimizer.state_dict(),
        "writer_optimizer_state_dict": descendant.learner.writer_optimizer.state_dict(),
        "recurrent_hidden": descendant.learner.recurrent_hidden,
        "previous_actions": descendant.learner.previous_actions,
        "previous_rewards": descendant.learner.previous_rewards,
        "rollout_state": frozen_vertical.rollout_payload(last_rollout),
        "numpy_rng_state": descendant.learner.numpy_rng.bit_generator.state,
        "torch_generator_state": descendant.learner.torch_generator.get_state(),
    }
    _atomic_torch_save(checkpoint_path, checkpoint_payload)
    checkpoint_verified = False
    try:
        reloaded = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        checkpoint_verified = bool(
            reloaded.get("run_id") == RUN_ID
            and reloaded.get("founder") == founder
            and reloaded.get("generation") == GENERATION
            and reloaded.get("arm") == arm
            and reloaded.get("credit_mode") == credit_mode
            and int(reloaded.get("updates", -1)) == UPDATES
            and reloaded.get("germ_mode") == "blind"
            and np.array_equal(reloaded.get("germ"), initial_germ)
            and reloaded.get("rollout_state") is not None
            and "external_learning_packet" not in reloaded
        )
    except Exception:
        checkpoint_verified = False

    evaluation_counts = {
        action_mode: sum(row["action_mode"] == action_mode for row in evaluations)
        for action_mode in ACTION_MODES
    }
    expected_evaluations = 1 + UPDATES // 10
    total_credit = sum(cumulative_credited_steps.values())
    total_extra = sum(cumulative_extra_predecessor.values())
    active_expected = arm in ACTIVE_ARMS
    null_expected = arm in NULL_ALIAS_ARMS
    packet_presence_expected = arm != "target_trace_reader_off"
    gates = {
        "boundary_reset_passes": bool(boundary["passes"]),
        "parent_checkpoint_hash_exact": sha256_file(Path(spec["parent_checkpoint"]))
        == spec["parent_checkpoint_sha256"],
        "source_result_hash_exact": sha256_file(Path(spec["source_result"]))
        == spec["source_result_sha256"],
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
        "auxiliary_heads_changed_in_life": initial_state["digests"][
            "auxiliary_heads"
        ]
        != final_state["digests"]["auxiliary_heads"],
        "auxiliary_heads_zero_at_birth": bool(initial_state["auxiliary_heads_zero"]),
        "neural_writer_scaffold_dormant": initial_state["digests"]["writer"]
        == final_state["digests"]["writer"],
        "writer_optimizer_dormant": _optimizer_tensor_count(
            descendant.learner.writer_optimizer
        )
        == 0,
        "birth_carrier_unchanged_inside_life": packet_unchanged_each_update
        and np.array_equal(descendant.learner.germ, initial_germ),
        "incoming_packet_exactly_64_bytes": initial_germ.nbytes == 64,
        "action_reader_blind_throughout": all(
            row["germ_mode"] == "blind" for row in history
        ),
        "credit_mode_schedule_exact": all(
            row["credit_mode"] == credit_mode for row in history
        ),
        "learning_packet_presence_exact": all(
            bool(row["credit_audit"]["packet_present"])
            == packet_presence_expected
            for row in history
        ),
        "null_arm_has_exact_zero_credit": not null_expected or total_credit == 0,
        "active_arm_observed_credit": not active_expected or total_credit > 0,
        "target_arm_observed_predecessor_support": arm != "target_trace_correct"
        or total_extra > 0,
        "no_external_packet_state": not any(
            "external" in name.lower() for name in vars(descendant.learner)
        ),
        "checkpoint_reloads_with_leak_probe": checkpoint_verified,
        "scientific_outcome_not_cell_completion_gate": True,
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "source_run_id": SOURCE_RUN,
        "rationale_run_id": RATIONALE_RUN,
        "founder": founder,
        "generation": GENERATION,
        "arm": arm,
        "credit_mode": credit_mode,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "environment_steps": EXPECTED_STEPS,
        "reward_mode": "terminal",
        "phase_credit_mode": "phase_actor",
        "action_germ_mode": "blind",
        "config": asdict(config),
        "parent_checkpoint": str(spec["parent_checkpoint"]),
        "parent_checkpoint_sha256": spec["parent_checkpoint_sha256"],
        "source_result": str(spec["source_result"]),
        "source_result_sha256": spec["source_result_sha256"],
        "source_carrier_sha256": spec["source_carrier_sha256"],
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
            action_mode: frozen_vertical.learning_auc(evaluations, action_mode)
            for action_mode in ACTION_MODES
        },
        "final_evaluations": final_evaluations,
        "final_world_rows": final_world_rows,
        "episodes_completed": total_episodes,
        "training_goal_successes": total_successes,
        "cumulative_event_counts": cumulative_events,
        "cumulative_confirmed_events": cumulative_confirmed,
        "cumulative_target_trace_steps": cumulative_target_steps,
        "cumulative_event_only_steps": cumulative_event_steps,
        "cumulative_credited_steps": cumulative_credited_steps,
        "cumulative_extra_predecessor_steps": cumulative_extra_predecessor,
        "first_signal_update": first_signal_update,
        "first_credit_update": first_credit_update,
        "first_extra_predecessor_update": first_extra_predecessor_update,
        "first_evaluation_reach": {
            action_mode: _first_evaluation_reach(evaluations, action_mode)
            for action_mode in ACTION_MODES
        },
        "initial_state": initial_state,
        "final_state": final_state,
        "birth_evaluation_sha256": birth_evaluation_sha256,
        "birth_soma_environment_digests": birth_soma_environment_digests,
        "first_rollout_sha256": first_rollout_sha256,
        "first_completed_episode_rows_sha256": first_completed_rows_sha256,
        "first_pre_update_soma_environment_digests": first_pre_update_digests,
        "final_soma_environment_digests": final_digests,
        "behavior_fingerprint": behavior_fingerprint,
        "rollout_semantics": semantics_accumulator,
        "final_training_entropy": float(history[-1]["entropy"]),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    atomic_json(result_path, result, output_root)
    atomic_json(
        progress_path,
        {
            "status": "COMPLETE" if result["completed_cleanly"] else "FAILED_GATES",
            "updated_utc": utc_now(),
            "founder": founder,
            "generation": GENERATION,
            "arm": arm,
            "credit_mode": credit_mode,
            "update": UPDATES,
            "training_goal_successes": total_successes,
            "cumulative_event_counts": cumulative_events,
            "cumulative_credited_steps": cumulative_credited_steps,
            "incoming_carrier_sha256": packet.digest(),
            "result_path": str(result_path),
        },
        output_root,
    )
    if not result["completed_cleanly"]:
        raise RuntimeError(f"founder {founder} {stem} failed gates: {gates}")
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


def _post_update_digest_rows(result: Mapping[str, Any]) -> list[str]:
    return [
        str(row["post_update_soma_environment_sha256"])
        for row in result["history"]
    ]


def _first_state_difference(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> int | None:
    differences = [
        index + 1
        for index, (left_digest, right_digest) in enumerate(
            zip(
                _post_update_digest_rows(left),
                _post_update_digest_rows(right),
                strict=True,
            )
        )
        if left_digest != right_digest
    ]
    return differences[0] if differences else None


def _mediation_audit(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    trigger_update: int | None,
) -> dict[str, Any]:
    first_difference = _first_state_difference(left, right)
    prefix_length = (trigger_update or 1) - 1
    left_states = _post_update_digest_rows(left)
    right_states = _post_update_digest_rows(right)
    left_rows = [_clean_history_row(row) for row in left["history"]]
    right_rows = [_clean_history_row(row) for row in right["history"]]
    gates = {
        "trigger_observed": trigger_update is not None,
        "first_state_difference_equals_trigger": first_difference == trigger_update,
        "all_pretrigger_states_exact": left_states[:prefix_length]
        == right_states[:prefix_length],
        "all_pretrigger_behavior_and_updates_exact": left_rows[:prefix_length]
        == right_rows[:prefix_length],
    }
    return {
        "trigger_update": trigger_update,
        "first_state_difference_update": first_difference,
        "gates": gates,
        "passes": all(gates.values()),
    }


def exact_apparatus_audit(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply exact action-blind, null-alias, and first-divergence checks."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    founder_rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        cells = [by_cell[(founder, arm)] for arm in ARMS]
        birth_fields = {
            "birth_evaluation_sha256": [
                row["birth_evaluation_sha256"] for row in cells
            ],
            "birth_soma_environment": [
                row["birth_soma_environment_digests"]["aggregate"]
                for row in cells
            ],
            "first_rollout_sha256": [row["first_rollout_sha256"] for row in cells],
            "first_completed_episode_rows_sha256": [
                row["first_completed_episode_rows_sha256"] for row in cells
            ],
            "first_pre_update_soma_environment": [
                row["first_pre_update_soma_environment_digests"]["aggregate"]
                for row in cells
            ],
        }
        all_birth_first_exact = all(
            len(set(values)) == 1 for values in birth_fields.values()
        )
        silence = by_cell[(founder, "learning_silence")]
        null_rows: list[dict[str, Any]] = []
        for arm in NULL_ALIAS_ARMS:
            row = by_cell[(founder, arm)]
            gates = {
                "behavior_and_ppo_exact": row["behavior_fingerprint"]
                == silence["behavior_fingerprint"],
                "all_post_update_states_exact": _post_update_digest_rows(row)
                == _post_update_digest_rows(silence),
                "final_state_exact": row["final_soma_environment_digests"][
                    "aggregate"
                ]
                == silence["final_soma_environment_digests"]["aggregate"],
                "zero_credited_steps": sum(
                    int(value) for value in row["cumulative_credited_steps"].values()
                )
                == 0,
            }
            null_rows.append(
                {"arm": arm, "gates": gates, "passes": all(gates.values())}
            )

        target = by_cell[(founder, "target_trace_correct")]
        event = by_cell[(founder, "event_only_correct")]
        target_silence = _mediation_audit(
            target,
            silence,
            target["first_credit_update"],
        )
        event_silence = _mediation_audit(
            event,
            silence,
            event["first_credit_update"],
        )
        target_event = _mediation_audit(
            target,
            event,
            target["first_extra_predecessor_update"],
        )
        gates = {
            "five_action_blind_births_and_first_rollouts_exact": all_birth_first_exact,
            "wrong_off_silence_exact": all(row["passes"] for row in null_rows),
            "target_credit_first_divergence_mediated": target_silence["passes"],
            "event_credit_first_divergence_mediated": event_silence["passes"],
            "predecessor_credit_first_divergence_mediated": target_event["passes"],
        }
        founder_rows.append(
            {
                "founder": founder,
                "birth_and_first_rollout_fields": birth_fields,
                "null_aliases": null_rows,
                "target_vs_silence": target_silence,
                "event_vs_silence": event_silence,
                "target_vs_event": target_event,
                "gates": gates,
                "passes": all(gates.values()),
            }
        )
    return {
        "founder_results": founder_rows,
        "passes": len(founder_rows) == len(FOUNDERS)
        and all(row["passes"] for row in founder_rows),
        "exact_equality_no_tolerance": True,
    }


def _open_door_auc(result: Mapping[str, Any]) -> float:
    return float(
        result["learning_auc"]["fixed_random"]["events"]["open_door"][
            "reached_fraction_auc"
        ]
    )


def registered_classification(
    results: Sequence[Mapping[str, Any]],
    apparatus: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply three prospectively frozen sign classifications."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        target = _open_door_auc(by_cell[(founder, "target_trace_correct")])
        event = _open_door_auc(by_cell[(founder, "event_only_correct")])
        silence = _open_door_auc(by_cell[(founder, "learning_silence")])
        rows.append(
            {
                "founder": founder,
                "target_trace_open_door_auc": target,
                "event_only_open_door_auc": event,
                "silence_open_door_auc": silence,
                "target_minus_silence": target - silence,
                "event_minus_silence": event - silence,
                "target_minus_event": target - event,
                "target_minus_silence_positive": target > silence,
                "event_minus_silence_positive": event > silence,
                "target_minus_event_positive": target > event,
            }
        )
    if not apparatus["passes"]:
        labels = {
            "target_trace": "TARGETED_READER_APPARATUS_INVALID",
            "event_only": "TARGETED_READER_APPARATUS_INVALID",
            "predecessor_credit": "TARGETED_READER_APPARATUS_INVALID",
        }
    else:
        labels = {
            "target_trace": (
                "TARGET_TRACE_BENEFIT_3_OF_3"
                if all(row["target_minus_silence_positive"] for row in rows)
                else "TARGET_TRACE_BENEFIT_NOT_3_OF_3"
            ),
            "event_only": (
                "EVENT_ONLY_BENEFIT_3_OF_3"
                if all(row["event_minus_silence_positive"] for row in rows)
                else "EVENT_ONLY_BENEFIT_NOT_3_OF_3"
            ),
            "predecessor_credit": (
                "PREDECESSOR_CREDIT_BENEFIT_3_OF_3"
                if all(row["target_minus_event_positive"] for row in rows)
                else "PREDECESSOR_CREDIT_BENEFIT_NOT_3_OF_3"
            ),
        }
    return {
        "labels": labels,
        "founder_results": rows,
        "strict_sign_rules_no_practical_threshold": True,
        "scientific_outcomes_used_as_completion_gates": False,
        "post_gradient_selected_exploratory_mechanism": True,
    }


def cell_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "founder": int(result["founder"]),
        "generation": int(result["generation"]),
        "arm": str(result["arm"]),
        "credit_mode": str(result["credit_mode"]),
        "action_germ_mode": result["action_germ_mode"],
        "incoming_carrier_sha256": result["incoming_carrier_sha256"],
        "source_carrier_sha256": result["source_carrier_sha256"],
        "learning_auc": result["learning_auc"],
        "training_events": dict(result["cumulative_event_counts"]),
        "confirmed_events": dict(result["cumulative_confirmed_events"]),
        "target_trace_steps": dict(result["cumulative_target_trace_steps"]),
        "event_only_steps": dict(result["cumulative_event_only_steps"]),
        "credited_steps": dict(result["cumulative_credited_steps"]),
        "extra_predecessor_steps": dict(
            result["cumulative_extra_predecessor_steps"]
        ),
        "first_credit_update": result["first_credit_update"],
        "first_extra_predecessor_update": result[
            "first_extra_predecessor_update"
        ],
        "training_goal_successes": int(result["training_goal_successes"]),
        "final_fixed_successes": int(
            result["final_evaluations"]["fixed_random"]["successes"]
        ),
        "final_deterministic_successes": int(
            result["final_evaluations"]["deterministic"]["successes"]
        ),
        "final_training_entropy": float(result["final_training_entropy"]),
        "birth_evaluation_sha256": result["birth_evaluation_sha256"],
        "first_rollout_sha256": result["first_rollout_sha256"],
        "behavior_fingerprint": result["behavior_fingerprint"],
        "final_soma_environment_sha256": result[
            "final_soma_environment_digests"
        ]["aggregate"],
        "completed_cleanly": bool(result["completed_cleanly"]),
    }


def descriptive_contrasts(
    results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Report every declared causal-chain contrast without reclassification."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    comparisons = (
        ("target_trace_correct", "learning_silence", "target_vs_silence"),
        ("event_only_correct", "learning_silence", "event_vs_silence"),
        ("target_trace_correct", "event_only_correct", "target_vs_event"),
        ("target_trace_correct", "target_trace_wrong", "target_vs_wrong"),
        (
            "target_trace_correct",
            "target_trace_reader_off",
            "target_vs_reader_off",
        ),
    )
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        for left_arm, right_arm, label in comparisons:
            left = by_cell[(founder, left_arm)]
            right = by_cell[(founder, right_arm)]
            action_modes: dict[str, Any] = {}
            for action_mode in ACTION_MODES:
                action_modes[action_mode] = {
                    event: float(
                        left["learning_auc"][action_mode]["events"][event][
                            "reached_fraction_auc"
                        ]
                        - right["learning_auc"][action_mode]["events"][event][
                            "reached_fraction_auc"
                        ]
                    )
                    for event in CAUSAL_CHAIN
                }
            rows.append(
                {
                    "founder": founder,
                    "contrast": label,
                    "left": left_arm,
                    "right": right_arm,
                    "reached_auc_difference": action_modes,
                    "training_goal_difference": int(left["training_goal_successes"])
                    - int(right["training_goal_successes"]),
                    "final_fixed_goal_difference": int(
                        left["final_evaluations"]["fixed_random"]["successes"]
                    )
                    - int(
                        right["final_evaluations"]["fixed_random"]["successes"]
                    ),
                }
            )
    return rows


def markdown_report(study: Mapping[str, Any]) -> str:
    outcome = study["registered_classification"]
    lines = [
        "# DoorKey targeted learning-only reader test v1",
        "",
        f"**Structural completion:** `{'PASS' if study['completed_cleanly'] else 'FAIL'}`  ",
        f"**Target-trace classification:** `{outcome['labels']['target_trace']}`  ",
        f"**Event-only classification:** `{outcome['labels']['event_only']}`  ",
        f"**Predecessor-credit classification:** `{outcome['labels']['predecessor_credit']}`",
        "",
        "## Registered open-door learning AUC",
        "",
        "| Founder | Target trace | Event only | Silence | Target - silence | Event - silence | Target - event |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in outcome["founder_results"]:
        lines.append(
            f"| {row['founder']} | {row['target_trace_open_door_auc']:.6f} | "
            f"{row['event_only_open_door_auc']:.6f} | "
            f"{row['silence_open_door_auc']:.6f} | "
            f"{row['target_minus_silence']:+.6f} | "
            f"{row['event_minus_silence']:+.6f} | "
            f"{row['target_minus_event']:+.6f} |"
        )
    lines.extend(
        [
            "",
            "## Exact causal apparatus",
            "",
            "| Founder | Five births + first rollouts | Wrong = off = silence | Target mediation | Event mediation | Predecessor mediation |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in study["exact_apparatus_audit"]["founder_results"]:
        gates = row["gates"]
        lines.append(
            f"| {row['founder']} | "
            f"`{'EXACT' if gates['five_action_blind_births_and_first_rollouts_exact'] else 'DIFF'}` | "
            f"`{'EXACT' if gates['wrong_off_silence_exact'] else 'DIFF'}` | "
            f"`{'PASS' if gates['target_credit_first_divergence_mediated'] else 'FAIL'}` | "
            f"`{'PASS' if gates['event_credit_first_divergence_mediated'] else 'FAIL'}` | "
            f"`{'PASS' if gates['predecessor_credit_first_divergence_mediated'] else 'FAIL'}` |"
        )
    lines.extend(["", "## Cell outcomes", ""])
    lines.append(
        "| Founder | Arm | Open-door AUC | Confirmed events | Credited steps | Extra predecessors | Final fixed goals |"
    )
    lines.append("|---:|---|---:|---:|---:|---:|---:|")
    for row in study["cell_summaries"]:
        open_auc = row["learning_auc"]["fixed_random"]["events"]["open_door"][
            "reached_fraction_auc"
        ]
        lines.append(
            f"| {row['founder']} | `{row['arm']}` | {open_auc:.6f} | "
            f"{sum(row['confirmed_events'].values())} | "
            f"{sum(row['credited_steps'].values())} | "
            f"{sum(row['extra_predecessor_steps'].values())} | "
            f"{row['final_fixed_successes']} |"
        )
    lines.extend(["", "## Structural completion gates", ""])
    for name, passed in study["completion_gates"].items():
        lines.append(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            (
                "This post-gradient-selected reader is engineered and retains "
                "fixed event ontology and addresses. Behavioral benefit would "
                "establish only an action-blind learning influence in this "
                "apparatus, not a universal law, evolved ontology, or genome."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _input_paths(
    workspace: Path,
    root: Path,
    source: Mapping[str, Any],
) -> list[Path]:
    rationale_output = root / "outputs" / RATIONALE_RUN
    rationale_run = root / "runs" / RATIONALE_RUN
    rationale_manifest = json.loads(
        (rationale_run / "MANIFEST.json").read_text(encoding="utf-8")
    )
    paths = [
        workspace / "protocols/DOORKEY_TARGETED_LEARNING_READER_V1.md",
        workspace / "requirements-doorkey.lock",
        Path(__file__).resolve(),
        workspace / "src/laws_confirmation/doorkey_counterfactual_gradient.py",
        workspace / "src/laws_confirmation/doorkey_learning_only_reader.py",
        workspace / "src/laws_confirmation/doorkey_matched_disposition.py",
        workspace / "src/laws_confirmation/doorkey_vertical_multifounder.py",
        workspace / "src/laws_confirmation/doorkey_vertical_scout.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_credit.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/io.py",
        workspace / "tests/test_doorkey_targeted_learning_reader.py",
        workspace / "scripts/run_doorkey_targeted_learning_reader.sh",
        workspace / "scripts/run_doorkey_targeted_learning_reader_detached.sh",
        rationale_output / "gradient_audit.json",
        rationale_output / "audit.md",
        rationale_output / "input_hashes.sha256",
        rationale_output / "output_hashes.sha256",
        rationale_run / "MANIFEST.json",
        rationale_run / "STATUS.json",
        rationale_run / "COMPLETE",
    ]
    paths.extend(Path(path) for path in rationale_manifest.get("input_sha256", {}))
    for parent in source["parents"]:
        paths.extend(
            (
                Path(parent["source_result"]),
                Path(parent["checkpoint"]),
            )
        )
    unique = sorted({path.resolve() for path in paths})
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen targeted-reader inputs: {missing}")
    return unique


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
        "exactly_four_workers": workers == MAX_WORKERS,
    }
    return {"values": values, "gates": gates, "passes": all(gates.values())}


def run_study(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if args.run_id != RUN_ID:
        raise ValueError(f"frozen run ID must be {RUN_ID}")
    if args.workers != MAX_WORKERS:
        raise ValueError(f"frozen study requires exactly {MAX_WORKERS} workers")
    root = external_root(args.external_root)
    output_dir = root / "outputs" / args.run_id
    run_dir = root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    source = qualify_sources(root)
    if not source["passes"]:
        raise RuntimeError(f"frozen source qualification failed: {source['gates']}")
    config = FeedbackPPOConfig(**dict(source["parents"][0]["config"]))
    specs = cell_specs(source)
    input_paths = _input_paths(workspace, root, source)
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    contract_digest = canonical_digest(input_hashes)
    disk = _disk_preflight(root, 128 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if args.resume:
        if not run_dir.is_dir() or not output_dir.is_dir():
            raise FileNotFoundError("cannot resume a run that was not initialized")
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
        for founder in FOUNDERS:
            (output_dir / f"founder_{founder}" / "progress").mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "source_run_id": SOURCE_RUN,
            "rationale_run_id": RATIONALE_RUN,
            "stage": "DoorKey targeted action-blind learning reader",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "external_root": str(root),
            "output_dir": str(output_dir),
            "input_sha256": input_hashes,
            "contract_digest": contract_digest,
            "repository_head": git_head(workspace),
            "workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "founders": list(FOUNDERS),
            "generation": GENERATION,
            "arms": list(ARMS),
            "credit_modes": list(CREDIT_MODES),
            "seeds": SEEDS,
            "registered_cells": REGISTERED_CELLS,
            "updates_per_cell": UPDATES,
            "transitions_per_cell": EXPECTED_STEPS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "registered_sign_rules": [
                "target_trace_minus_silence_positive_all_three",
                "event_only_minus_silence_positive_all_three",
                "target_trace_minus_event_only_positive_all_three",
            ],
            "scientific_outcomes_are_completion_gates": False,
            "disk_preflight": disk,
            "environment": environment_manifest(),
        }
        atomic_json(run_dir / "MANIFEST.json", manifest, root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", root)
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
    atomic_text(run_dir / "RUN.pid", f"{os.getpid()}\n", root)

    try:
        runtime = runtime_qualification(args.workers)
        training_started = time.monotonic()
        results: list[dict[str, Any]] = []
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=MAX_WORKERS,
            mp_context=context,
        ) as executor:
            future_to_spec = {
                executor.submit(
                    _worker_train_cell,
                    spec,
                    asdict(config),
                    str(root),
                    str(output_dir / f"founder_{spec['founder']}"),
                ): spec
                for spec in specs
            }
            for future in as_completed(future_to_spec):
                spec = future_to_spec[future]
                try:
                    results.append(future.result())
                except Exception as error:
                    raise RuntimeError(
                        f"founder {spec['founder']} G4 {spec['arm']} worker failed"
                    ) from error
                atomic_json(
                    output_dir / "progress.json",
                    {
                        "status": "RUNNING",
                        "updated_utc": utc_now(),
                        "completed_cells": len(results),
                        "registered_cells": REGISTERED_CELLS,
                    },
                    root,
                )
        elapsed_training = time.monotonic() - training_started
        results.sort(key=lambda row: (int(row["founder"]), ARMS.index(row["arm"])))
        unique_cells = {
            (int(row["founder"]), int(row["generation"]), str(row["arm"]))
            for row in results
        }
        apparatus = exact_apparatus_audit(results)
        outcome = registered_classification(results, apparatus)
        summaries = [cell_summary(row) for row in results]
        contrasts = descriptive_contrasts(results)
        expected_incoming = {
            (int(spec["founder"]), str(spec["arm"])): carrier_digest(
                np.asarray(spec["incoming_germ"], dtype=np.uint8)
            )
            for spec in specs
        }
        expected_credit_modes = {
            (int(spec["founder"]), str(spec["arm"])): str(spec["credit_mode"])
            for spec in specs
        }
        source_digests = {
            int(parent["founder"]): parent["outgoing_carrier_sha256"]
            for parent in source["parents"]
        }
        completion_gates = {
            "runtime_qualified": bool(runtime["passes"]),
            "frozen_sources_qualified": bool(source["passes"]),
            "exactly_15_registered_cells": len(results) == REGISTERED_CELLS
            and len(unique_cells) == REGISTERED_CELLS,
            "all_cells_registered_to_study": all(
                row.get("run_id") == RUN_ID
                and row.get("source_run_id") == SOURCE_RUN
                and row.get("rationale_run_id") == RATIONALE_RUN
                and row.get("generation") == GENERATION
                for row in results
            ),
            "all_cells_completed_cleanly": all(
                bool(row["completed_cleanly"]) for row in results
            ),
            "all_cells_100_updates": all(row["updates"] == UPDATES for row in results),
            "all_cells_expected_transitions": all(
                row["environment_steps"] == EXPECTED_STEPS for row in results
            ),
            "all_15_boundaries_reset": all(
                row["boundary_audit"]["passes"] for row in results
            ),
            "all_parent_checkpoint_links_exact": all(
                row["boundary_audit"]["parent_checkpoint_sha256"]
                == row["parent_checkpoint_sha256"]
                for row in results
            ),
            "all_source_carrier_links_exact": all(
                row["source_carrier_sha256"]
                == source_digests[int(row["founder"])]
                for row in results
            ),
            "all_birth_packets_exactly_64_bytes": all(
                np.asarray(row["incoming_carrier"], dtype=np.uint8).nbytes == 64
                for row in results
            ),
            "all_registered_incoming_interventions_exact": all(
                row["incoming_carrier_sha256"]
                == expected_incoming[(int(row["founder"]), str(row["arm"]))]
                for row in results
            ),
            "all_registered_credit_modes_exact": all(
                row["credit_mode"]
                == expected_credit_modes[(int(row["founder"]), str(row["arm"]))]
                for row in results
            ),
            "fresh_seed_registry_exact": all(
                row["birth_seed"] == seed_row(int(row["founder"]))["birth"]
                and row["training_seed"]
                == seed_row(int(row["founder"]))["training"]
                for row in results
            ),
            "all_cell_gates_pass": all(
                all(row["completion_gates"].values()) for row in results
            ),
            "all_action_blind_null_and_mediation_checks_pass": bool(
                apparatus["passes"]
            ),
            "all_writer_scaffolds_and_optimizers_dormant": all(
                row["completion_gates"]["neural_writer_scaffold_dormant"]
                and row["completion_gates"]["writer_optimizer_dormant"]
                for row in results
            ),
            "all_metrics_finite": all(
                _finite_credit_history(row["history"]) for row in results
            ),
            "all_rollout_semantics_pass": all(
                row["completion_gates"]["all_rollout_semantics_pass"]
                for row in results
            ),
            "all_final_evaluations_replay_exactly": all(
                row["completion_gates"]["final_evaluations_replay_exactly"]
                for row in results
            ),
            "all_checkpoints_reload": all(
                row["completion_gates"]["checkpoint_reloads_with_leak_probe"]
                for row in results
            ),
            "four_workers_one_thread": args.workers == MAX_WORKERS
            and runtime["values"]["torch_num_threads"] == 1,
            "scientific_outcomes_not_used_as_completion_gates": True,
        }
        study = {
            "schema_version": 1,
            "run_id": args.run_id,
            "source_run_id": SOURCE_RUN,
            "rationale_run_id": RATIONALE_RUN,
            "generated_utc": utc_now(),
            "status": "TARGETED_ACTION_BLIND_LEARNING_READER",
            "runtime": runtime,
            "sources": source,
            "config": asdict(config),
            "seeds": SEEDS,
            "founders": list(FOUNDERS),
            "generation": GENERATION,
            "arms": list(ARMS),
            "credit_modes": list(CREDIT_MODES),
            "cell_specs": specs,
            "cell_result_files": [
                str(
                    output_dir
                    / f"founder_{row['founder']}"
                    / f"g4_{row['arm']}.json"
                )
                for row in results
            ],
            "cell_summaries": summaries,
            "exact_apparatus_audit": apparatus,
            "registered_classification": outcome,
            "descriptive_contrasts": contrasts,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "registered_cells": REGISTERED_CELLS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "elapsed_training_seconds": elapsed_training,
            "max_workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output_dir / "targeted_learning_reader.json", study, root)
        atomic_text(output_dir / "audit.md", markdown_report(study), root)
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
        status_ok = bool(study["completed_cleanly"] and outputs_verify)
        status = {
            "status": "COMPLETE" if status_ok else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "completed_cleanly": bool(study["completed_cleanly"]),
            "output_manifest_self_verifies": outputs_verify,
            "registered_cells": REGISTERED_CELLS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "max_workers": MAX_WORKERS,
            "classifications": outcome["labels"],
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
    return run_study(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
