"""Evidence-gated learning-only reading of the unchanged DoorKey carrier.

The learning-only arms never expose carrier content to action logits. A valid
record can only reweight an already collected, event-confirmed causal trace
inside the PPO actor-advantage calculation.
"""

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
    GOAL_CHANNEL,
    KEY_CHANNEL,
    CausalCreditDescendant,
    CausalCreditRollout,
    _finite_credit_history,
    _first_evaluation_reach,
    _forward_sequence_values,
    _masked_mse,
    _module_birth_details,
    actor_advantage_for_arm,
    guarded_standardize,
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


RUN_ID = "doorkey_learning_only_reader_v1_attempt1"
SOURCE_RUN = source_confirmation.RUN_ID
RATIONALE_RUN = matched.RUN_ID
FOUNDERS = (1, 2, 3)
GENERATION = 4
ARMS = (
    "learning_correct",
    "learning_external",
    "learning_wrong",
    "learning_silence",
    "learning_reader_off",
    "direct_prior",
    "learning_post_key",
    "learning_delayed",
)
ACTION_BLIND_ARMS = tuple(arm for arm in ARMS if arm != "direct_prior")
NULL_ALIAS_ARMS = (
    "learning_wrong",
    "learning_silence",
    "learning_reader_off",
)
UPDATES = frozen_vertical.UPDATES
CUTOFF_UPDATE = matched.CUTOFF_UPDATE
EXPECTED_STEPS = frozen_vertical.EXPECTED_STEPS
MAX_WORKERS = 4
REGISTERED_CELLS = len(FOUNDERS) * len(ARMS)
REGISTERED_TRANSITIONS = REGISTERED_CELLS * EXPECTED_STEPS
CHANNEL_SLOT = {KEY_CHANNEL: 1, DOOR_CHANNEL: 3}


def seed_row(founder: int) -> dict[str, int]:
    """Return the frozen fresh G4 seed pair for one founder."""

    if founder not in FOUNDERS:
        raise ValueError("unregistered founder")
    return {
        "birth": 200_000_000 + 100_000 * founder,
        "training": 210_000_000 + 100_000 * founder,
    }


SEEDS = {founder: seed_row(founder) for founder in FOUNDERS}


def action_germ_mode(arm: str) -> str:
    """Return the only action-reader schedule allowed by the protocol."""

    if arm not in ARMS:
        raise ValueError("unregistered arm")
    return "direct_prior" if arm == "direct_prior" else "blind"


def learning_packet_for(
    arm: str,
    update: int,
    *,
    incoming: np.ndarray,
    correct_external: np.ndarray,
) -> np.ndarray | None:
    """Select the packet visible only to actor-credit construction."""

    if arm not in ARMS or not 1 <= update <= UPDATES:
        raise ValueError("unregistered arm or update")
    if arm in {"learning_reader_off", "direct_prior"}:
        return None
    if arm == "learning_external":
        return np.asarray(correct_external, dtype=np.uint8)
    if arm == "learning_delayed" and update <= CUTOFF_UPDATE:
        return None
    return np.asarray(incoming, dtype=np.uint8)


def causal_trace_gains(
    rollout: CausalCreditRollout,
    carrier: np.ndarray | None,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Build trust gains for event-confirmed same-phase episode traces."""

    if rollout.auxiliary_advantages.ndim != 3:
        raise ValueError("auxiliary advantages must be time x env x channel")
    gains = torch.ones_like(rollout.auxiliary_advantages)
    decoded = None
    packet_digest = None
    if carrier is not None:
        packet = np.asarray(carrier)
        if packet.dtype != np.uint8 or packet.shape != (1, 64) or packet.nbytes != 64:
            raise ValueError("learning reader requires one exact 64-byte uint8 packet")
        decoded = read_germ(packet, GermSchema())
        packet_digest = carrier_digest(packet)

    channel_rows: dict[str, dict[str, Any]] = {}
    total_confirmed = 0
    total_steps = 0
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        slot = CHANNEL_SLOT[channel]
        active = bool(decoded is not None and decoded.active[0, slot])
        target = (
            int(decoded.prior_logits[0, slot].argmax()) if decoded is not None else None
        )
        trust = int(decoded.trust[0, slot]) if decoded is not None else None
        event_mask = rollout.event_rewards[:, :, channel] > 0
        event_count = int(torch.count_nonzero(event_mask).item())
        matching = torch.zeros_like(event_mask)
        if active and target is not None:
            matching = event_mask & (rollout.actions == target)
        locations = torch.nonzero(matching, as_tuple=False).detach().cpu().tolist()
        trace_mask = torch.zeros_like(event_mask)
        for time_index, environment_index in locations:
            for cursor in range(int(time_index), -1, -1):
                if int(rollout.phases[cursor, environment_index].item()) != channel:
                    break
                trace_mask[cursor, environment_index] = True
                if bool(rollout.episode_starts[cursor, environment_index].item()):
                    break
        trace_steps = int(torch.count_nonzero(trace_mask).item())
        confirmed = len(locations)
        gain_value = 1.0
        if confirmed and trust is not None:
            gain_value = 1.0 + trust / 255.0
            gains[:, :, channel] = torch.where(
                trace_mask,
                torch.full_like(gains[:, :, channel], gain_value),
                gains[:, :, channel],
            )
        channel_name = CHANNELS[channel]
        channel_rows[channel_name] = {
            "slot": slot,
            "record_active": active,
            "target_action": target,
            "trust": trust,
            "event_count": event_count,
            "confirmed_event_count": confirmed,
            "boosted_trace_steps": trace_steps,
            "gain": gain_value,
            "trace_mask_sha256": matched.deep_digest(trace_mask),
        }
        total_confirmed += confirmed
        total_steps += trace_steps

    audit = {
        "packet_present": decoded is not None,
        "packet_sha256": packet_digest,
        "channels": channel_rows,
        "confirmed_event_count": total_confirmed,
        "boosted_trace_steps": total_steps,
        "gain_tensor_sha256": matched.deep_digest(gains),
    }
    return gains, audit


def learning_actor_advantage(
    rollout: CausalCreditRollout,
    carrier: np.ndarray | None,
) -> tuple[torch.Tensor, dict[str, bool], dict[str, Any]]:
    """Return phase actor credit after optional evidence-gated consolidation."""

    base, signals = actor_advantage_for_arm(rollout, "phase_actor")
    gains, trace = causal_trace_gains(rollout, carrier)
    trace["base_actor_advantage_sha256"] = matched.deep_digest(base)
    if int(trace["boosted_trace_steps"]) == 0:
        trace["learning_actor_advantage_sha256"] = trace[
            "base_actor_advantage_sha256"
        ]
        trace["differs_from_base"] = False
        return base, signals, trace

    actor_advantage = torch.zeros_like(rollout.goal_advantages)
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        mask = rollout.phases == channel
        weighted = (
            rollout.auxiliary_advantages[:, :, channel] * gains[:, :, channel]
        )
        actor_advantage += guarded_standardize(
            weighted,
            mask,
            signals[CHANNELS[channel]],
        )
    goal_mask = rollout.phases == GOAL_CHANNEL
    actor_advantage += guarded_standardize(
        rollout.goal_advantages,
        goal_mask,
        signals[CHANNELS[GOAL_CHANNEL]],
    )
    trace["learning_actor_advantage_sha256"] = matched.deep_digest(actor_advantage)
    trace["differs_from_base"] = not torch.equal(actor_advantage, base)
    return actor_advantage, signals, trace


def learning_only_ppo_update(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    *,
    learning_carrier: np.ndarray | None,
    germ_mode: str,
) -> dict[str, Any]:
    """Run the frozen phase PPO update with an optional learning-only packet."""

    if learning_carrier is not None and germ_mode != "blind":
        raise ValueError("a learning-only packet cannot coexist with action reading")
    actor_advantage, signals, trace = learning_actor_advantage(
        rollout, learning_carrier
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
    result.update(
        {
            "actor_channel_signal": signals,
            "actor_advantage_nonzero": bool(torch.count_nonzero(actor_advantage)),
            "actor_advantage_nonzero_count": int(
                torch.count_nonzero(actor_advantage)
            ),
            "learning_trace": trace,
        }
    )
    return result


def qualify_sources(root: Path) -> dict[str, Any]:
    """Verify the G3 parents and the completed motivating decomposition."""

    vertical = matched.qualify_sources(root)
    output_dir = root / "outputs" / RATIONALE_RUN
    run_dir = root / "runs" / RATIONALE_RUN
    study_path = output_dir / "disposition.json"
    manifest_path = run_dir / "MANIFEST.json"
    status_path = run_dir / "STATUS.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    input_rows = matched._verify_manifest_inputs(manifest)
    output_rows = _read_hash_manifest(output_dir / "output_hashes.sha256")
    outcome = study.get("matched_behavior_audit", {})
    gates = {
        "vertical_sources_qualify": bool(vertical["passes"]),
        "rationale_run_ids_exact": study.get("run_id") == RATIONALE_RUN
        and manifest.get("run_id") == RATIONALE_RUN,
        "rationale_complete": status.get("status") == "COMPLETE"
        and bool(study.get("completed_cleanly")),
        "rationale_complete_sentinel_present": (run_dir / "COMPLETE").is_file(),
        "rationale_failed_sentinel_absent": not (run_dir / "FAILED").exists(),
        "rationale_completion_gates_pass": bool(study.get("completion_gates"))
        and all(study.get("completion_gates", {}).values()),
        "rationale_classification_exact": outcome.get("classification")
        == "DIRECT_ACTION_SHAPING_SUFFICIENT_3_OF_3"
        and outcome.get("disposition_classification")
        == "NO_SEPARATE_GERM_DISPOSITION_DETECTED_3_OF_3",
        "rationale_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "rationale_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
        "rationale_manifest_self_verified": bool(
            status.get("output_manifest_self_verifies")
        ),
    }
    return {
        "vertical": vertical,
        "parents": vertical["parents"],
        "rationale": {
            "study_path": str(study_path),
            "manifest_path": str(manifest_path),
            "status_path": str(status_path),
            "input_manifest": matched._manifest_summary(input_rows),
            "output_manifest": matched._manifest_summary(output_rows),
            "classification": outcome.get("classification"),
            "disposition_classification": outcome.get(
                "disposition_classification"
            ),
        },
        "gates": gates,
        "passes": all(gates.values()),
    }


def cell_specs(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build the frozen 24-cell intervention registry."""

    parents = {int(row["founder"]): row for row in source["parents"]}
    specs: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        correct = np.asarray(parents[founder]["outgoing_carrier"], dtype=np.uint8)
        controls = source_confirmation.initial_carriers(correct)
        wrong = np.asarray(controls["wrong_frozen"], dtype=np.uint8)
        silence = empty_germ(1, GermSchema())
        post_key = matched.make_post_key_mask(correct)
        for arm in ARMS:
            if arm in {"learning_external", "learning_silence"}:
                incoming = silence
            elif arm == "learning_wrong":
                incoming = wrong
            elif arm == "learning_post_key":
                incoming = post_key
            else:
                incoming = correct
            specs.append(
                {
                    "founder": founder,
                    "generation": GENERATION,
                    "arm": arm,
                    "birth_seed": seed_row(founder)["birth"],
                    "training_seed": seed_row(founder)["training"],
                    "parent_checkpoint": parents[founder]["checkpoint"],
                    "parent_checkpoint_sha256": parents[founder][
                        "checkpoint_sha256"
                    ],
                    "source_carrier_sha256": carrier_digest(correct),
                    "incoming_germ": incoming.tolist(),
                    "correct_external_germ": correct.tolist(),
                    "wrong_germ_sha256": carrier_digest(wrong),
                    "post_key_germ_sha256": carrier_digest(post_key),
                }
            )
    return specs


def _evaluate_cell(
    descendant: CausalCreditDescendant,
    config: FeedbackPPOConfig,
    germ_mode: str,
    action_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evaluation, rows = frozen_vertical._evaluate(
        descendant, config, germ_mode, action_mode
    )
    evaluation["world_rows_sha256"] = matched.deep_digest(rows)
    return evaluation, rows


def _clean_history_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Remove packet diagnostics while retaining every behavioral/update value."""

    return {
        key: value
        for key, value in row.items()
        if key not in {"learning_trace", "germ_mode"}
    }


def behavior_digest(
    history: Sequence[Mapping[str, Any]],
    evaluations: Sequence[Mapping[str, Any]],
    *,
    first_update: int,
    last_update: int,
    final_evaluations: Mapping[str, Any] | None = None,
    final_world_rows: Mapping[str, Any] | None = None,
) -> str:
    """Digest behavior and learner updates while excluding packet provenance."""

    payload: dict[str, Any] = {
        "history": [
            _clean_history_row(row)
            for row in history
            if first_update <= int(row["update"]) <= last_update
        ],
        "evaluations": [
            matched._clean_evaluation(row)
            for row in evaluations
            if first_update <= int(row["update"]) <= last_update
        ],
    }
    if final_evaluations is not None:
        payload["final_evaluations"] = {
            mode: matched._clean_evaluation(row)
            for mode, row in final_evaluations.items()
        }
    if final_world_rows is not None:
        payload["final_world_rows"] = final_world_rows
    return matched.deep_digest(payload)


def _birth_evaluation_digest(evaluations: Sequence[Mapping[str, Any]]) -> str:
    rows = [
        matched._clean_evaluation(row)
        for row in evaluations
        if int(row["update"]) == 0
    ]
    return matched.deep_digest(rows)


def _train_cell(
    spec: Mapping[str, Any],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Train one registered G4 descendant under the frozen reader schedule."""

    founder = int(spec["founder"])
    arm = str(spec["arm"])
    if founder not in FOUNDERS or arm not in ARMS:
        raise ValueError("unregistered learning-only cell")
    birth_seed = int(spec["birth_seed"])
    training_seed = int(spec["training_seed"])
    incoming = np.asarray(spec["incoming_germ"], dtype=np.uint8)
    correct_external = np.asarray(spec["correct_external_germ"], dtype=np.uint8)
    initial_external = correct_external.copy()
    packet = make_boundary_packet(incoming)
    germ_mode = action_germ_mode(arm)
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
        evaluation, _ = _evaluate_cell(descendant, config, germ_mode, action_mode)
        evaluation["update"] = 0
        evaluations.append(evaluation)
    birth_evaluation_sha256 = _birth_evaluation_digest(evaluations)

    environments = DoorKeyVectorEnv(
        config.num_envs,
        training_seed,
        config.max_episode_steps,
        "terminal",
    )
    birth_soma_environment_digests = matched.soma_environment_digests(
        descendant, environments
    )
    history: list[dict[str, Any]] = []
    total_episodes = 0
    total_successes = 0
    cumulative_events = {channel: 0 for channel in CHANNELS}
    cumulative_confirmed = {"key": 0, "door": 0}
    cumulative_boosted_steps = {"key": 0, "door": 0}
    first_signal_update: dict[str, int | None] = {channel: None for channel in CHANNELS}
    first_confirmed_trace_update: int | None = None
    semantics_accumulator: dict[str, bool] = {}
    last_rollout: CausalCreditRollout | None = None
    first_rollout_sha256: str | None = None
    first_completed_rows_sha256: str | None = None
    first_pre_update_digests: dict[str, str] | None = None
    cutoff_digests: dict[str, str] | None = None
    external_tracker: dict[str, Any] = {
        "calls": 0,
        "packet_sha256": carrier_digest(correct_external),
        "packet_unchanged_each_call": True,
        "inherited_germ_unchanged_each_call": True,
    }

    for update in range(1, UPDATES + 1):
        rollout, completed = frozen_vertical.collect_vertical_rollout(
            descendant, environments, config, germ_mode
        )
        last_rollout = rollout
        rollout_sha256 = matched.deep_digest(vars(rollout))
        completed_sha256 = matched.deep_digest(completed)
        if update == 1:
            first_rollout_sha256 = rollout_sha256
            first_completed_rows_sha256 = completed_sha256
            first_pre_update_digests = matched.soma_environment_digests(
                descendant, environments
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

        learning_carrier = learning_packet_for(
            arm,
            update,
            incoming=incoming,
            correct_external=correct_external,
        )
        germ_before = descendant.learner.germ.copy()
        packet_before = None if learning_carrier is None else learning_carrier.copy()
        if arm == "learning_external":
            external_tracker["calls"] += 1
        metrics = learning_only_ppo_update(
            descendant,
            rollout,
            config,
            learning_carrier=learning_carrier,
            germ_mode=germ_mode,
        )
        if arm == "learning_external":
            external_tracker["inherited_germ_unchanged_each_call"] &= bool(
                np.array_equal(descendant.learner.germ, germ_before)
            )
            external_tracker["packet_unchanged_each_call"] &= bool(
                packet_before is not None
                and np.array_equal(learning_carrier, packet_before)
                and np.array_equal(correct_external, initial_external)
            )

        trace = dict(metrics["learning_trace"])
        for channel in ("key", "door"):
            channel_trace = trace["channels"][channel]
            cumulative_confirmed[channel] += int(
                channel_trace["confirmed_event_count"]
            )
            cumulative_boosted_steps[channel] += int(
                channel_trace["boosted_trace_steps"]
            )
        if trace["boosted_trace_steps"] and first_confirmed_trace_update is None:
            first_confirmed_trace_update = update

        update_successes = sum(bool(row["success"]) for row in completed)
        total_episodes += len(completed)
        total_successes += update_successes
        post_update_digests = matched.soma_environment_digests(
            descendant, environments
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
            "germ_mode": germ_mode,
            "post_update_soma_environment_sha256": post_update_digests["aggregate"],
            **metrics,
        }
        history.append(row)
        latest: list[dict[str, Any]] = []
        if update % 10 == 0:
            for action_mode in ACTION_MODES:
                evaluation, _ = _evaluate_cell(
                    descendant, config, germ_mode, action_mode
                )
                evaluation["update"] = update
                evaluations.append(evaluation)
                latest.append(evaluation)
        if update == CUTOFF_UPDATE:
            cutoff_digests = post_update_digests
        if update % 5 == 0:
            atomic_json(
                progress_path,
                {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    "founder": founder,
                    "generation": GENERATION,
                    "arm": arm,
                    "update": update,
                    "updates": UPDATES,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_successes": total_successes,
                    "cumulative_event_counts": dict(cumulative_events),
                    "cumulative_confirmed_events": dict(cumulative_confirmed),
                    "cumulative_boosted_trace_steps": dict(
                        cumulative_boosted_steps
                    ),
                    "latest_evaluations": latest,
                },
                output_root,
            )
            print(
                f"founder {founder} {stem} update {update}/{UPDATES} "
                f"events={cumulative_events['key']}/"
                f"{cumulative_events['door']}/{cumulative_events['goal']} "
                f"boosted={sum(cumulative_boosted_steps.values())}",
                flush=True,
            )

    if (
        last_rollout is None
        or first_rollout_sha256 is None
        or first_completed_rows_sha256 is None
        or first_pre_update_digests is None
        or cutoff_digests is None
    ):
        raise RuntimeError("learning-only cell missed a registered state capture")

    final_evaluations: dict[str, Any] = {}
    final_world_rows: dict[str, Any] = {}
    final_replay = True
    for action_mode in ACTION_MODES:
        evaluation, rows = _evaluate_cell(
            descendant, config, germ_mode, action_mode
        )
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
    early_behavior_sha256 = behavior_digest(
        history,
        evaluations,
        first_update=0,
        last_update=CUTOFF_UPDATE,
    )
    post_behavior_sha256 = behavior_digest(
        history,
        evaluations,
        first_update=CUTOFF_UPDATE + 1,
        last_update=UPDATES,
        final_evaluations=final_evaluations,
        final_world_rows=final_world_rows,
    )
    full_behavior_sha256 = behavior_digest(
        history,
        evaluations,
        first_update=0,
        last_update=UPDATES,
        final_evaluations=final_evaluations,
        final_world_rows=final_world_rows,
    )

    checkpoint_payload = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "source_run_id": SOURCE_RUN,
        "founder": founder,
        "generation": GENERATION,
        "arm": arm,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "reward_mode": "terminal",
        "germ_mode": germ_mode,
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
    external_packet_absent = False
    try:
        reloaded = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        external_packet_absent = "external_learning_packet" not in reloaded
        checkpoint_verified = bool(
            reloaded.get("run_id") == RUN_ID
            and reloaded.get("founder") == founder
            and reloaded.get("generation") == GENERATION
            and reloaded.get("arm") == arm
            and int(reloaded.get("updates", -1)) == UPDATES
            and np.array_equal(reloaded.get("germ"), initial_germ)
            and reloaded.get("rollout_state") is not None
            and external_packet_absent
        )
    except Exception:
        checkpoint_verified = False

    evaluation_counts = {
        action_mode: sum(row["action_mode"] == action_mode for row in evaluations)
        for action_mode in ACTION_MODES
    }
    expected_evaluations = 1 + UPDATES // 10
    post_key = matched.make_post_key_mask(correct_external)
    post_key_read = read_germ(post_key)
    post_key_exact = bool(
        post_key_read.address_valid.all()
        and post_key_read.checksum_valid.all()
        and post_key_read.active[0].tolist() == [False, False, False, True]
        and int(post_key_read.prior_logits.argmax(axis=-1)[0, 3]) == 5
        and carrier_digest(post_key) == spec["post_key_germ_sha256"]
    )
    external_expected_calls = UPDATES if arm == "learning_external" else 0
    gates = {
        "boundary_reset_passes": bool(boundary["passes"]),
        "parent_checkpoint_hash_exact": sha256_file(Path(spec["parent_checkpoint"]))
        == spec["parent_checkpoint_sha256"],
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
        "birth_carrier_unchanged_inside_life": np.array_equal(
            descendant.learner.germ, initial_germ
        ),
        "incoming_packet_exactly_64_bytes": initial_germ.nbytes == 64,
        "action_reader_schedule_exact": all(
            row["germ_mode"] == germ_mode for row in history
        )
        and (arm == "direct_prior") == (germ_mode == "direct_prior"),
        "learning_packet_never_combined_with_action_reader": all(
            not row["learning_trace"]["packet_present"]
            or row["germ_mode"] == "blind"
            for row in history
        ),
        "external_learning_call_count_exact": int(external_tracker["calls"])
        == external_expected_calls,
        "external_packet_unchanged": bool(
            external_tracker["packet_unchanged_each_call"]
        ),
        "external_calls_preserved_inherited_germ": bool(
            external_tracker["inherited_germ_unchanged_each_call"]
        ),
        "external_packet_absent_from_checkpoint": external_packet_absent,
        "external_packet_absent_from_descendant_fields": not any(
            "external" in name.lower() for name in vars(descendant.learner)
        ),
        "post_key_packet_exact": post_key_exact,
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
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "environment_steps": EXPECTED_STEPS,
        "cutoff_update": CUTOFF_UPDATE,
        "reward_mode": "terminal",
        "phase_credit_mode": "phase_actor",
        "action_germ_mode": germ_mode,
        "config": asdict(config),
        "parent_checkpoint": str(spec["parent_checkpoint"]),
        "parent_checkpoint_sha256": spec["parent_checkpoint_sha256"],
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
        "external_learning_audit": external_tracker,
        "history": history,
        "evaluations": evaluations,
        "learning_auc": {
            action_mode: frozen_vertical.learning_auc(evaluations, action_mode)
            for action_mode in ACTION_MODES
        },
        "post_cutoff_learning_auc": {
            action_mode: matched.segment_learning_auc(
                evaluations, action_mode, CUTOFF_UPDATE, UPDATES
            )
            for action_mode in ACTION_MODES
        },
        "final_evaluations": final_evaluations,
        "final_world_rows": final_world_rows,
        "episodes_completed": total_episodes,
        "training_goal_successes": total_successes,
        "cumulative_event_counts": cumulative_events,
        "cumulative_confirmed_events": cumulative_confirmed,
        "cumulative_boosted_trace_steps": cumulative_boosted_steps,
        "first_signal_update": first_signal_update,
        "first_confirmed_trace_update": first_confirmed_trace_update,
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
        "cutoff_soma_environment_digests": cutoff_digests,
        "final_soma_environment_digests": final_digests,
        "early_behavior_sha256": early_behavior_sha256,
        "post_cutoff_behavior_sha256": post_behavior_sha256,
        "behavior_fingerprint": full_behavior_sha256,
        "rollout_semantics": semantics_accumulator,
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
            "update": UPDATES,
            "training_goal_successes": total_successes,
            "cumulative_event_counts": cumulative_events,
            "cumulative_confirmed_events": cumulative_confirmed,
            "cumulative_boosted_trace_steps": cumulative_boosted_steps,
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


def exact_apparatus_audit(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply all registered action-blind aliases and causal mediation checks."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    founder_rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        blind = [by_cell[(founder, arm)] for arm in ACTION_BLIND_ARMS]
        birth_fields = {
            "birth_evaluation_sha256": [row["birth_evaluation_sha256"] for row in blind],
            "birth_soma_environment": [
                row["birth_soma_environment_digests"]["aggregate"] for row in blind
            ],
            "first_rollout_sha256": [row["first_rollout_sha256"] for row in blind],
            "first_completed_episode_rows_sha256": [
                row["first_completed_episode_rows_sha256"] for row in blind
            ],
            "first_pre_update_soma_environment": [
                row["first_pre_update_soma_environment_digests"]["aggregate"]
                for row in blind
            ],
        }
        blind_birth_first_exact = all(
            len(set(values)) == 1 for values in birth_fields.values()
        )

        correct = by_cell[(founder, "learning_correct")]
        external = by_cell[(founder, "learning_external")]
        inherited_external_gates = {
            "behavior_exact": correct["behavior_fingerprint"]
            == external["behavior_fingerprint"],
            "all_post_update_states_exact": _post_update_digest_rows(correct)
            == _post_update_digest_rows(external),
            "cutoff_state_exact": correct["cutoff_soma_environment_digests"][
                "aggregate"
            ]
            == external["cutoff_soma_environment_digests"]["aggregate"],
            "final_state_exact": correct["final_soma_environment_digests"][
                "aggregate"
            ]
            == external["final_soma_environment_digests"]["aggregate"],
        }

        silence = by_cell[(founder, "learning_silence")]
        null_rows: list[dict[str, Any]] = []
        for arm in NULL_ALIAS_ARMS:
            row = by_cell[(founder, arm)]
            gates = {
                "behavior_exact": row["behavior_fingerprint"]
                == silence["behavior_fingerprint"],
                "all_post_update_states_exact": _post_update_digest_rows(row)
                == _post_update_digest_rows(silence),
                "cutoff_state_exact": row["cutoff_soma_environment_digests"][
                    "aggregate"
                ]
                == silence["cutoff_soma_environment_digests"]["aggregate"],
                "final_state_exact": row["final_soma_environment_digests"][
                    "aggregate"
                ]
                == silence["final_soma_environment_digests"]["aggregate"],
            }
            null_rows.append(
                {"arm": arm, "gates": gates, "passes": all(gates.values())}
            )

        delayed = by_cell[(founder, "learning_delayed")]
        delayed_states = _post_update_digest_rows(delayed)[:CUTOFF_UPDATE]
        silence_states = _post_update_digest_rows(silence)[:CUTOFF_UPDATE]
        delayed_gates = {
            "early_behavior_exact": delayed["early_behavior_sha256"]
            == silence["early_behavior_sha256"],
            "updates_1_through_20_exact": delayed_states == silence_states,
            "cutoff_state_exact": delayed["cutoff_soma_environment_digests"][
                "aggregate"
            ]
            == silence["cutoff_soma_environment_digests"]["aggregate"],
        }

        correct_states = _post_update_digest_rows(correct)
        silence_states_all = _post_update_digest_rows(silence)
        differing_updates = [
            index + 1
            for index, (left, right) in enumerate(
                zip(correct_states, silence_states_all, strict=True)
            )
            if left != right
        ]
        first_divergence = differing_updates[0] if differing_updates else None
        first_boost = correct["first_confirmed_trace_update"]
        mediation_gates = {
            "first_divergence_equals_first_confirmed_trace": first_divergence
            == first_boost,
            "all_pre_trace_states_exact": all(
                correct_states[index] == silence_states_all[index]
                for index in range((first_boost or 1) - 1)
            ),
            "trace_or_state_both_absent_together": (first_boost is None)
            == (first_divergence is None),
        }

        gates = {
            "seven_action_blind_birth_and_first_rollout_exact": blind_birth_first_exact,
            "inherited_external_exact": all(inherited_external_gates.values()),
            "wrong_silence_reader_off_exact": all(
                row["passes"] for row in null_rows
            ),
            "delayed_silence_exact_through_update_20": all(delayed_gates.values()),
            "first_divergence_mediated_by_confirmed_trace": all(
                mediation_gates.values()
            ),
        }
        founder_rows.append(
            {
                "founder": founder,
                "birth_and_first_rollout_fields": birth_fields,
                "inherited_external": inherited_external_gates,
                "null_aliases": null_rows,
                "delayed_silence": delayed_gates,
                "mediation": {
                    "first_confirmed_trace_update": first_boost,
                    "first_soma_divergence_update": first_divergence,
                    "gates": mediation_gates,
                },
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


def _open_door_auc(result: Mapping[str, Any], *, post_cutoff: bool = False) -> float:
    key = "post_cutoff_learning_auc" if post_cutoff else "learning_auc"
    return float(
        result[key]["fixed_random"]["events"]["open_door"][
            "reached_fraction_auc"
        ]
    )


def registered_classification(
    results: Sequence[Mapping[str, Any]],
    apparatus: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the registered three-founder sign rule without a score threshold."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        correct = by_cell[(founder, "learning_correct")]
        silence = by_cell[(founder, "learning_silence")]
        wrong = by_cell[(founder, "learning_wrong")]
        correct_auc = _open_door_auc(correct)
        silence_auc = _open_door_auc(silence)
        wrong_auc = _open_door_auc(wrong)
        rows.append(
            {
                "founder": founder,
                "learning_correct_open_door_auc": correct_auc,
                "learning_silence_open_door_auc": silence_auc,
                "learning_wrong_open_door_auc": wrong_auc,
                "correct_minus_silence": correct_auc - silence_auc,
                "correct_minus_wrong": correct_auc - wrong_auc,
                "correct_minus_silence_positive": correct_auc > silence_auc,
                "correct_minus_wrong_positive": correct_auc > wrong_auc,
            }
        )
    if not apparatus["passes"]:
        classification = "LEARNING_ONLY_APPARATUS_INVALID"
    elif all(row["correct_minus_silence_positive"] for row in rows):
        classification = "LEARNING_ONLY_BENEFIT_3_OF_3"
    else:
        classification = "LEARNING_ONLY_BENEFIT_NOT_3_OF_3"
    return {
        "classification": classification,
        "founder_results": rows,
        "all_three_correct_minus_silence_positive": all(
            row["correct_minus_silence_positive"] for row in rows
        ),
        "all_three_correct_minus_wrong_positive": all(
            row["correct_minus_wrong_positive"] for row in rows
        ),
        "strict_sign_rule_no_practical_threshold": True,
        "scientific_outcome_used_as_completion_gate": False,
        "direct_prior_excluded": True,
        "exploratory_post_selected_mechanism": True,
    }


def cell_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "founder": int(result["founder"]),
        "generation": int(result["generation"]),
        "arm": str(result["arm"]),
        "action_germ_mode": result["action_germ_mode"],
        "incoming_carrier_sha256": result["incoming_carrier_sha256"],
        "source_carrier_sha256": result["source_carrier_sha256"],
        "learning_auc": result["learning_auc"],
        "post_cutoff_learning_auc": result["post_cutoff_learning_auc"],
        "training_events": dict(result["cumulative_event_counts"]),
        "confirmed_events": dict(result["cumulative_confirmed_events"]),
        "boosted_trace_steps": dict(result["cumulative_boosted_trace_steps"]),
        "first_confirmed_trace_update": result["first_confirmed_trace_update"],
        "training_goal_successes": int(result["training_goal_successes"]),
        "final_fixed_successes": int(
            result["final_evaluations"]["fixed_random"]["successes"]
        ),
        "final_deterministic_successes": int(
            result["final_evaluations"]["deterministic"]["successes"]
        ),
        "birth_evaluation_sha256": result["birth_evaluation_sha256"],
        "first_rollout_sha256": result["first_rollout_sha256"],
        "early_behavior_sha256": result["early_behavior_sha256"],
        "behavior_fingerprint": result["behavior_fingerprint"],
        "cutoff_soma_environment_sha256": result[
            "cutoff_soma_environment_digests"
        ]["aggregate"],
        "final_soma_environment_sha256": result[
            "final_soma_environment_digests"
        ]["aggregate"],
        "completed_cleanly": bool(result["completed_cleanly"]),
    }


def descriptive_contrasts(
    results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return outcome-open chain differences for the declared mechanism probes."""

    by_cell = {(int(row["founder"]), str(row["arm"])): row for row in results}
    comparisons = (
        ("learning_correct", "learning_silence", "learning_only_correct"),
        ("learning_correct", "learning_wrong", "content_specificity"),
        ("learning_external", "learning_silence", "external_packet_learning"),
        ("learning_post_key", "learning_silence", "door_only_consolidation"),
        ("learning_delayed", "learning_silence", "delayed_consolidation"),
        ("direct_prior", "learning_silence", "direct_action_prior_benchmark"),
    )
    rows: list[dict[str, Any]] = []
    for founder in FOUNDERS:
        for left_arm, right_arm, label in comparisons:
            left = by_cell[(founder, left_arm)]
            right = by_cell[(founder, right_arm)]
            full_events: dict[str, float] = {}
            post_events: dict[str, float] = {}
            for event in CAUSAL_CHAIN:
                full_events[event] = float(
                    left["learning_auc"]["fixed_random"]["events"][event][
                        "reached_fraction_auc"
                    ]
                    - right["learning_auc"]["fixed_random"]["events"][event][
                        "reached_fraction_auc"
                    ]
                )
                post_events[event] = float(
                    left["post_cutoff_learning_auc"]["fixed_random"]["events"][
                        event
                    ]["reached_fraction_auc"]
                    - right["post_cutoff_learning_auc"]["fixed_random"]["events"][
                        event
                    ]["reached_fraction_auc"]
                )
            rows.append(
                {
                    "founder": founder,
                    "contrast": label,
                    "left": left_arm,
                    "right": right_arm,
                    "fixed_random_full_reached_auc_difference": full_events,
                    "fixed_random_post_cutoff_reached_auc_difference": post_events,
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
        "# DoorKey learning-only reader test v1",
        "",
        f"**Structural completion:** `{'PASS' if study['completed_cleanly'] else 'FAIL'}`  ",
        f"**Registered classification:** `{outcome['classification']}`",
        "",
        "## Registered learning-only comparison",
        "",
        "| Founder | Correct AUC | Silence AUC | Difference | Correct - wrong |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in outcome["founder_results"]:
        lines.append(
            f"| {row['founder']} | {row['learning_correct_open_door_auc']:.6f} | "
            f"{row['learning_silence_open_door_auc']:.6f} | "
            f"{row['correct_minus_silence']:+.6f} | "
            f"{row['correct_minus_wrong']:+.6f} |"
        )
    lines.extend(
        [
            "",
            "## Exact action-blind apparatus",
            "",
            "| Founder | Birth + first rollout | Inherited = external | Wrong = null = off | Delayed = null through 20 | Trace mediation |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in study["exact_apparatus_audit"]["founder_results"]:
        gates = row["gates"]
        lines.append(
            f"| {row['founder']} | "
            f"`{'EXACT' if gates['seven_action_blind_birth_and_first_rollout_exact'] else 'DIFF'}` | "
            f"`{'EXACT' if gates['inherited_external_exact'] else 'DIFF'}` | "
            f"`{'EXACT' if gates['wrong_silence_reader_off_exact'] else 'DIFF'}` | "
            f"`{'EXACT' if gates['delayed_silence_exact_through_update_20'] else 'DIFF'}` | "
            f"`{'PASS' if gates['first_divergence_mediated_by_confirmed_trace'] else 'FAIL'}` |"
        )
    lines.extend(["", "## Cell outcomes", ""])
    lines.append(
        "| Founder | Arm | Open-door AUC | Post-20 open AUC | Confirmed events | Boosted steps | Final fixed goals |"
    )
    lines.append("|---:|---|---:|---:|---:|---:|---:|")
    for row in study["cell_summaries"]:
        full = row["learning_auc"]["fixed_random"]["events"]["open_door"][
            "reached_fraction_auc"
        ]
        post = row["post_cutoff_learning_auc"]["fixed_random"]["events"][
            "open_door"
        ]["reached_fraction_auc"]
        confirmed = sum(row["confirmed_events"].values())
        boosted = sum(row["boosted_trace_steps"].values())
        lines.append(
            f"| {row['founder']} | `{row['arm']}` | {full:.6f} | "
            f"{post:.6f} | {confirmed} | {boosted} | "
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
                "The reader is deliberately engineered and retains fixed event "
                "ontology and addresses. A positive result would show a "
                "learning-only 64-byte influence in this apparatus, not a "
                "universal law, evolved ontology, or biological genome."
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
        workspace / "protocols/DOORKEY_LEARNING_ONLY_READER_V1.md",
        workspace / "requirements-doorkey.lock",
        Path(__file__).resolve(),
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
        workspace / "tests/test_doorkey_learning_only_reader.py",
        workspace / "scripts/run_doorkey_learning_only_reader.sh",
        workspace / "scripts/run_doorkey_learning_only_reader_detached.sh",
        rationale_output / "disposition.json",
        rationale_output / "audit.md",
        rationale_output / "input_hashes.sha256",
        rationale_output / "output_hashes.sha256",
        rationale_run / "MANIFEST.json",
        rationale_run / "STATUS.json",
        rationale_run / "COMPLETE",
    ]
    paths.extend(Path(path) for path in rationale_manifest.get("input_sha256", {}))
    for parent in source["parents"]:
        paths.extend((Path(parent["result"]), Path(parent["checkpoint"])))
    unique = sorted({path.resolve() for path in paths})
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen learning-only inputs: {missing}")
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
            "stage": "DoorKey evidence-gated learning-only reader",
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
            "action_blind_arms": list(ACTION_BLIND_ARMS),
            "cutoff_update": CUTOFF_UPDATE,
            "registered_cells": REGISTERED_CELLS,
            "updates_per_cell": UPDATES,
            "transitions_per_cell": EXPECTED_STEPS,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "registered_sign_rule": "strict_positive_all_three_no_margin",
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
        source_digests = {
            int(parent["founder"]): parent["outgoing_carrier_sha256"]
            for parent in source["parents"]
        }
        completion_gates = {
            "runtime_qualified": bool(runtime["passes"]),
            "frozen_sources_qualified": bool(source["passes"]),
            "exactly_24_registered_cells": len(results) == REGISTERED_CELLS
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
            "all_24_boundaries_reset": all(
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
            "all_cell_gates_pass": all(
                all(row["completion_gates"].values()) for row in results
            ),
            "all_action_blind_and_mediation_aliases_pass": bool(apparatus["passes"]),
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
            "external_packet_absent_from_descendants_and_checkpoints": all(
                row["completion_gates"]["external_packet_absent_from_checkpoint"]
                and row["completion_gates"][
                    "external_packet_absent_from_descendant_fields"
                ]
                for row in results
            ),
            "direct_prior_excluded_from_learning_classification": bool(
                outcome["direct_prior_excluded"]
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
            "status": "EVIDENCE_GATED_LEARNING_ONLY_READER",
            "runtime": runtime,
            "sources": source,
            "config": asdict(config),
            "seeds": SEEDS,
            "founders": list(FOUNDERS),
            "generation": GENERATION,
            "arms": list(ARMS),
            "action_blind_arms": list(ACTION_BLIND_ARMS),
            "cutoff_update": CUTOFF_UPDATE,
            "cell_specs": specs,
            "cell_result_files": [
                str(output_dir / f"founder_{row['founder']}" / f"g4_{row['arm']}.json")
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
        atomic_json(output_dir / "learning_only_reader.json", study, root)
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
            "classification": outcome["classification"],
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
