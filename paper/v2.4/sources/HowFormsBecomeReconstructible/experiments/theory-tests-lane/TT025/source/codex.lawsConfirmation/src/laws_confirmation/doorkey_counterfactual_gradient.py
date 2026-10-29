"""Counterfactual policy-gradient audit on exact DoorKey silence replays."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch.nn import functional as F

from . import doorkey_learning_only_reader as source_reader
from . import doorkey_matched_disposition as matched
from . import doorkey_vertical_multifounder as source_confirmation
from . import doorkey_vertical_scout as frozen_vertical
from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import GermSchema, carrier_digest, read_germ
from .doorkey_feedback_scout import _disk_preflight, _read_hash_manifest
from .doorkey_phase_value_credit import (
    CHANNELS,
    DOOR_CHANNEL,
    KEY_CHANNEL,
    CausalCreditDescendant,
    CausalCreditRollout,
    _forward_sequence_values,
    guarded_standardize,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import FeedbackPPOConfig, _apply_prior
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


RUN_ID = "doorkey_counterfactual_gradient_audit_v1_attempt1"
SOURCE_RUN = source_reader.RUN_ID
FOUNDERS = (1, 2, 3)
UPDATES = source_reader.UPDATES
GRADIENT_UPDATES = (1, 10, 20, 40, 60, 80, 100)
MAX_WORKERS = 3
EXPECTED_STEPS_PER_FOUNDER = source_reader.EXPECTED_STEPS
REGISTERED_TRANSITIONS = len(FOUNDERS) * EXPECTED_STEPS_PER_FOUNDER
CHANNEL_SLOT = {KEY_CHANNEL: 1, DOOR_CHANNEL: 3}
CANDIDATES = (
    "prestandard_uniform_current",
    "poststandard_uniform",
    "event_only_reference",
    "trace_target_only",
    "positive_decay_short",
    "positive_decay_long",
)
METRIC_NAMES = (
    "policy_loss",
    "value_loss",
    "goal_value_loss",
    "key_value_loss",
    "door_value_loss",
    "entropy",
    "approx_kl",
    "clip_fraction",
    "grad_norm",
    "actor_channel_signal",
    "actor_advantage_nonzero",
    "actor_advantage_nonzero_count",
)


def confirmed_trace_support(
    rollout: CausalCreditRollout,
    carrier: np.ndarray,
    channel: int,
) -> dict[str, Any]:
    """Return exact event, trace, target, and decayed support for one channel."""

    if channel not in CHANNEL_SLOT:
        raise ValueError("only key and door channels have carrier records")
    packet = np.asarray(carrier)
    if packet.dtype != np.uint8 or packet.shape != (1, 64) or packet.nbytes != 64:
        raise ValueError("gradient audit requires one exact 64-byte uint8 packet")
    decoded = read_germ(packet, GermSchema())
    slot = CHANNEL_SLOT[channel]
    active = bool(decoded.active[0, slot])
    target = int(decoded.prior_logits[0, slot].argmax())
    trust = int(decoded.trust[0, slot])
    amplitude = trust / 255.0 if active else 0.0
    event = rollout.event_rewards[:, :, channel] > 0
    confirmed = event & (rollout.actions == target) if active else torch.zeros_like(event)
    trace = torch.zeros_like(event)
    decay_short = torch.zeros_like(event, dtype=rollout.goal_advantages.dtype)
    decay_long = torch.zeros_like(event, dtype=rollout.goal_advantages.dtype)
    locations = torch.nonzero(confirmed, as_tuple=False).detach().cpu().tolist()
    for time_index, environment_index in locations:
        for cursor in range(int(time_index), -1, -1):
            if int(rollout.phases[cursor, environment_index].item()) != channel:
                break
            distance = int(time_index) - cursor
            trace[cursor, environment_index] = True
            decay_short[cursor, environment_index] = torch.maximum(
                decay_short[cursor, environment_index],
                torch.as_tensor(
                    amplitude * (0.5**distance),
                    dtype=decay_short.dtype,
                    device=decay_short.device,
                ),
            )
            decay_long[cursor, environment_index] = torch.maximum(
                decay_long[cursor, environment_index],
                torch.as_tensor(
                    amplitude * (0.9**distance),
                    dtype=decay_long.dtype,
                    device=decay_long.device,
                ),
            )
            if bool(rollout.episode_starts[cursor, environment_index].item()):
                break
    target_trace = trace & (rollout.actions == target)
    return {
        "channel": channel,
        "channel_name": CHANNELS[channel],
        "slot": slot,
        "active": active,
        "target_action": target,
        "trust": trust,
        "amplitude": amplitude,
        "event": event,
        "confirmed": confirmed,
        "trace": trace,
        "target_trace": target_trace,
        "decay_short": decay_short,
        "decay_long": decay_long,
    }


def counterfactual_deltas(
    rollout: CausalCreditRollout,
    carrier: np.ndarray,
    channel: int,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Construct the six frozen carrier-induced advantage deltas."""

    support = confirmed_trace_support(rollout, carrier, channel)
    signal = bool(torch.count_nonzero(rollout.event_rewards[:, :, channel]))
    phase_mask = rollout.phases == channel
    raw = rollout.auxiliary_advantages[:, :, channel]
    base_channel = guarded_standardize(raw, phase_mask, signal)
    gain = torch.ones_like(raw)
    if support["amplitude"]:
        gain = torch.where(
            support["trace"],
            torch.full_like(raw, 1.0 + float(support["amplitude"])),
            gain,
        )
    current = guarded_standardize(raw * gain, phase_mask, signal) - base_channel
    amplitude = float(support["amplitude"])
    deltas = {
        "prestandard_uniform_current": current,
        "poststandard_uniform": base_channel * (gain - 1.0),
        "event_only_reference": support["confirmed"].to(raw.dtype) * amplitude,
        "trace_target_only": support["target_trace"].to(raw.dtype) * amplitude,
        "positive_decay_short": support["decay_short"],
        "positive_decay_long": support["decay_long"],
    }
    if tuple(deltas) != CANDIDATES:
        raise AssertionError("candidate order drifted from frozen registry")
    audit = {
        "channel": channel,
        "channel_name": support["channel_name"],
        "record_active": support["active"],
        "target_action": support["target_action"],
        "trust": support["trust"],
        "event_count": int(torch.count_nonzero(support["event"]).item()),
        "confirmed_event_count": int(
            torch.count_nonzero(support["confirmed"]).item()
        ),
        "trace_steps": int(torch.count_nonzero(support["trace"]).item()),
        "target_trace_steps": int(
            torch.count_nonzero(support["target_trace"]).item()
        ),
        "support": support,
    }
    return deltas, audit


def delta_support_metrics(
    delta: torch.Tensor,
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Summarize where one carrier-induced delta places absolute credit."""

    support = audit["support"]
    confirmed = support["confirmed"]
    trace = support["trace"]
    target_trace = support["target_trace"]
    trace_nontarget = trace & ~target_trace
    nontrace = ~trace
    absolute = delta.abs()
    positive = torch.clamp(delta, min=0.0)
    negative = torch.clamp(-delta, min=0.0)

    def mass(mask: torch.Tensor) -> float:
        return float(absolute[mask].sum().item())

    total = float(absolute.sum().item())
    event_values = delta[confirmed]
    event_min = float(event_values.min().item()) if event_values.numel() else None
    event_mean = float(event_values.mean().item()) if event_values.numel() else None
    event_mass = mass(confirmed)
    target_mass = mass(target_trace)
    nontarget_trace_mass = mass(trace_nontarget)
    nontrace_mass = mass(nontrace)
    non_target_mass = nontarget_trace_mass + nontrace_mass
    return {
        "absolute_mass": total,
        "positive_mass": float(positive.sum().item()),
        "negative_mass": float(negative.sum().item()),
        "event_absolute_mass": event_mass,
        "trace_target_absolute_mass": target_mass,
        "trace_nontarget_absolute_mass": nontarget_trace_mass,
        "nontrace_absolute_mass": nontrace_mass,
        "non_target_absolute_mass": non_target_mass,
        "event_absolute_fraction": event_mass / total if total else None,
        "non_target_absolute_fraction": non_target_mass / total if total else None,
        "event_delta_min": event_min,
        "event_delta_mean": event_mean,
        "delta_nonzero_count": int(torch.count_nonzero(delta).item()),
        "delta_sha256": matched.deep_digest(delta),
    }


def policy_gradient_vector(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    advantage_delta: torch.Tensor,
) -> torch.Tensor:
    """Return the full-rollout ratio-one actor-loss gradient without mutation."""

    if advantage_delta.shape != rollout.actions.shape:
        raise ValueError("gradient advantage shape differs from rollout actions")
    observations = rollout.observations
    logits, _, _ = _forward_sequence_values(
        descendant,
        observations,
        rollout.initial_hidden,
        rollout.episode_starts,
        rollout.previous_actions,
        rollout.previous_rewards,
    )
    flat_observations = observations.reshape(-1, config.observation_width)
    flat_logits, _ = _apply_prior(
        logits.reshape(-1, config.num_actions),
        descendant.learner,
        flat_observations,
        "blind",
    )
    log_probs = F.log_softmax(flat_logits, dim=-1)
    actions = rollout.actions.reshape(-1)
    chosen = log_probs.gather(1, actions[:, None]).squeeze(1)
    loss = -(chosen * advantage_delta.detach().reshape(-1)).mean()
    parameters = tuple(descendant.learner.model.parameters())
    gradients = torch.autograd.grad(loss, parameters, allow_unused=True)
    flattened = [
        torch.zeros_like(parameter).reshape(-1)
        if gradient is None
        else gradient.detach().reshape(-1)
        for parameter, gradient in zip(parameters, gradients, strict=True)
    ]
    return torch.cat(flattened).cpu()


def gradient_geometry(
    gradient: torch.Tensor,
    reference: torch.Tensor,
) -> dict[str, Any]:
    """Return norm/dot/cosine geometry, preserving zero-reference undefinedness."""

    norm = float(torch.linalg.vector_norm(gradient).item())
    reference_norm = float(torch.linalg.vector_norm(reference).item())
    dot = float(torch.dot(gradient, reference).item())
    denominator = norm * reference_norm
    return {
        "gradient_norm": norm,
        "reference_norm": reference_norm,
        "dot": dot,
        "cosine": dot / denominator if denominator else None,
        "finite": all(math.isfinite(value) for value in (norm, reference_norm, dot)),
    }


def counterfactual_gradient_snapshot(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    carrier: np.ndarray,
) -> dict[str, Any]:
    """Measure all candidate gradients for key, door, and their combination."""

    before = {
        "soma": frozen_vertical.causal_credit_digests(descendant),
        "numpy_rng": matched.deep_digest(descendant.learner.numpy_rng.bit_generator.state),
        "torch_rng": matched.deep_digest(descendant.learner.torch_generator.get_state()),
    }
    channel_deltas: dict[int, dict[str, torch.Tensor]] = {}
    channel_rows: dict[str, Any] = {}
    channel_gradients: dict[int, dict[str, torch.Tensor]] = {}
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        deltas, audit = counterfactual_deltas(rollout, carrier, channel)
        reference = policy_gradient_vector(
            descendant,
            rollout,
            config,
            deltas["event_only_reference"],
        )
        gradients: dict[str, torch.Tensor] = {}
        geometry: dict[str, Any] = {}
        support_metrics: dict[str, Any] = {}
        for candidate in CANDIDATES:
            gradient = (
                reference
                if candidate == "event_only_reference"
                else policy_gradient_vector(
                    descendant,
                    rollout,
                    config,
                    deltas[candidate],
                )
            )
            gradients[candidate] = gradient
            geometry[candidate] = gradient_geometry(gradient, reference)
            support_metrics[candidate] = delta_support_metrics(
                deltas[candidate], audit
            )
        channel_deltas[channel] = deltas
        channel_gradients[channel] = gradients
        channel_rows[CHANNELS[channel]] = {
            key: value for key, value in audit.items() if key != "support"
        } | {
            "support_metrics": support_metrics,
            "gradient_geometry": geometry,
        }

    combined: dict[str, Any] = {}
    combined_reference = (
        channel_gradients[KEY_CHANNEL]["event_only_reference"]
        + channel_gradients[DOOR_CHANNEL]["event_only_reference"]
    )
    for candidate in CANDIDATES:
        gradient = (
            channel_gradients[KEY_CHANNEL][candidate]
            + channel_gradients[DOOR_CHANNEL][candidate]
        )
        combined[candidate] = gradient_geometry(gradient, combined_reference)
    after = {
        "soma": frozen_vertical.causal_credit_digests(descendant),
        "numpy_rng": matched.deep_digest(descendant.learner.numpy_rng.bit_generator.state),
        "torch_rng": matched.deep_digest(descendant.learner.torch_generator.get_state()),
    }
    return {
        "channels": channel_rows,
        "combined_gradient_geometry": combined,
        "diagnostic_state_before_sha256": matched.deep_digest(before),
        "diagnostic_state_after_sha256": matched.deep_digest(after),
        "diagnostic_state_exact": before == after,
    }


def counterfactual_support_snapshot(
    rollout: CausalCreditRollout,
    carrier: np.ndarray,
) -> dict[str, Any]:
    """Measure candidate credit support without taking counterfactual gradients."""

    rows: dict[str, Any] = {}
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        deltas, audit = counterfactual_deltas(rollout, carrier, channel)
        trace_steps = int(audit["trace_steps"])
        rows[CHANNELS[channel]] = {
            key: value for key, value in audit.items() if key != "support"
        } | {
            "event_fraction_of_trace": (
                audit["confirmed_event_count"] / trace_steps if trace_steps else None
            ),
            "target_fraction_of_trace": (
                audit["target_trace_steps"] / trace_steps if trace_steps else None
            ),
            "candidates": {
                candidate: delta_support_metrics(deltas[candidate], audit)
                for candidate in CANDIDATES
            },
        }
    return rows


def qualify_source(root: Path) -> dict[str, Any]:
    """Verify the completed learning-only run and its three silence sources."""

    output_dir = root / "outputs" / SOURCE_RUN
    run_dir = root / "runs" / SOURCE_RUN
    study_path = output_dir / "learning_only_reader.json"
    manifest_path = run_dir / "MANIFEST.json"
    status_path = run_dir / "STATUS.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    input_rows = matched._verify_manifest_inputs(manifest)
    output_rows = _read_hash_manifest(output_dir / "output_hashes.sha256")
    output_paths = {row["path"] for row in output_rows}
    outcome = study.get("registered_classification", {})
    source_specs = {
        (int(row["founder"]), str(row["arm"])): row
        for row in study.get("cell_specs", [])
    }
    replay_sources: list[dict[str, Any]] = []
    config_digests: set[str] = set()
    for founder in FOUNDERS:
        spec = source_specs[(founder, "learning_silence")]
        result_path = output_dir / f"founder_{founder}" / "g4_learning_silence.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        correct = np.asarray(spec["correct_external_germ"], dtype=np.uint8)
        incoming = np.asarray(spec["incoming_germ"], dtype=np.uint8)
        packet_audit = source_confirmation._correct_functional_packet(correct)
        config = dict(result.get("config", {}))
        config_digests.add(canonical_digest(config))
        gates = {
            "result_in_output_manifest": str(result_path.resolve()) in output_paths,
            "result_hash_matches_manifest": any(
                row["path"] == str(result_path.resolve()) and row["matches"]
                for row in output_rows
            ),
            "result_identity_exact": result.get("run_id") == SOURCE_RUN
            and result.get("founder") == founder
            and result.get("arm") == "learning_silence"
            and result.get("generation") == source_reader.GENERATION,
            "result_completed": bool(result.get("completed_cleanly")),
            "result_100_updates": len(result.get("history", [])) == UPDATES,
            "silence_packet_exact": incoming.shape == (1, 64)
            and incoming.nbytes == 64
            and not bool(read_germ(incoming).active.any())
            and carrier_digest(incoming) == result.get("incoming_carrier_sha256"),
            "correct_diagnostic_packet_exact": bool(packet_audit["passes"])
            and carrier_digest(correct) == result.get("source_carrier_sha256"),
            "seeds_exact": int(spec["birth_seed"]) == int(result["birth_seed"])
            and int(spec["training_seed"]) == int(result["training_seed"]),
            "parent_link_exact": spec["parent_checkpoint"]
            == result["parent_checkpoint"]
            and spec["parent_checkpoint_sha256"]
            == result["parent_checkpoint_sha256"],
            "config_present": bool(config),
        }
        replay_sources.append(
            {
                "founder": founder,
                "source_result": str(result_path),
                "source_result_sha256": sha256_file(result_path),
                "parent_checkpoint": result["parent_checkpoint"],
                "parent_checkpoint_sha256": result["parent_checkpoint_sha256"],
                "birth_seed": int(result["birth_seed"]),
                "training_seed": int(result["training_seed"]),
                "incoming_germ": incoming.tolist(),
                "incoming_carrier_sha256": carrier_digest(incoming),
                "diagnostic_carrier": correct.tolist(),
                "diagnostic_carrier_sha256": carrier_digest(correct),
                "diagnostic_packet_audit": packet_audit,
                "config": config,
                "gates": gates,
                "passes": all(gates.values()),
            }
        )
    gates = {
        "source_run_ids_exact": study.get("run_id") == SOURCE_RUN
        and manifest.get("run_id") == SOURCE_RUN,
        "source_complete": status.get("status") == "COMPLETE"
        and bool(study.get("completed_cleanly")),
        "source_complete_sentinel_present": (run_dir / "COMPLETE").is_file(),
        "source_failed_sentinel_absent": not (run_dir / "FAILED").exists(),
        "all_source_completion_gates_pass": bool(study.get("completion_gates"))
        and all(study.get("completion_gates", {}).values()),
        "source_classification_exact": outcome.get("classification")
        == "LEARNING_ONLY_BENEFIT_NOT_3_OF_3",
        "source_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "source_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
        "source_manifest_self_verified": bool(
            status.get("output_manifest_self_verifies")
        ),
        "three_silence_sources_pass": len(replay_sources) == len(FOUNDERS)
        and all(row["passes"] for row in replay_sources),
        "source_configs_identical": len(config_digests) == 1,
    }
    return {
        "study_path": str(study_path),
        "manifest_path": str(manifest_path),
        "status_path": str(status_path),
        "input_manifest": matched._manifest_summary(input_rows),
        "output_manifest": matched._manifest_summary(output_rows),
        "replay_sources": replay_sources,
        "gates": gates,
        "passes": all(gates.values()),
    }


def _aggregate_support(
    support_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for channel in ("key", "door"):
        candidate_rows: dict[str, Any] = {}
        for candidate in CANDIDATES:
            metrics = [row[channel]["candidates"][candidate] for row in support_rows]
            absolute_mass = sum(float(row["absolute_mass"]) for row in metrics)
            non_target_mass = sum(
                float(row["non_target_absolute_mass"]) for row in metrics
            )
            event_minimums = [
                float(row["event_delta_min"])
                for row in metrics
                if row["event_delta_min"] is not None
            ]
            candidate_rows[candidate] = {
                "absolute_mass": absolute_mass,
                "positive_mass": sum(float(row["positive_mass"]) for row in metrics),
                "negative_mass": sum(float(row["negative_mass"]) for row in metrics),
                "event_absolute_mass": sum(
                    float(row["event_absolute_mass"]) for row in metrics
                ),
                "trace_target_absolute_mass": sum(
                    float(row["trace_target_absolute_mass"]) for row in metrics
                ),
                "trace_nontarget_absolute_mass": sum(
                    float(row["trace_nontarget_absolute_mass"]) for row in metrics
                ),
                "nontrace_absolute_mass": sum(
                    float(row["nontrace_absolute_mass"]) for row in metrics
                ),
                "non_target_absolute_mass": non_target_mass,
                "non_target_absolute_fraction": (
                    non_target_mass / absolute_mass if absolute_mass else None
                ),
                "minimum_event_delta": min(event_minimums)
                if event_minimums
                else None,
                "all_confirming_event_deltas_nonnegative": bool(event_minimums)
                and min(event_minimums) >= 0.0,
            }
        trace_steps = sum(int(row[channel]["trace_steps"]) for row in support_rows)
        aggregate[channel] = {
            "event_count": sum(
                int(row[channel]["event_count"]) for row in support_rows
            ),
            "confirmed_event_count": sum(
                int(row[channel]["confirmed_event_count"]) for row in support_rows
            ),
            "trace_steps": trace_steps,
            "target_trace_steps": sum(
                int(row[channel]["target_trace_steps"]) for row in support_rows
            ),
            "candidates": candidate_rows,
        }
    return aggregate


def _aggregate_gradient_snapshots(
    snapshots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for channel in ("key", "door", "combined"):
        candidates: dict[str, Any] = {}
        for candidate in CANDIDATES:
            if channel == "combined":
                rows = [
                    row["combined_gradient_geometry"][candidate] for row in snapshots
                ]
            else:
                rows = [
                    row["channels"][channel]["gradient_geometry"][candidate]
                    for row in snapshots
                ]
            dot = sum(float(row["dot"]) for row in rows)
            norm_squared = sum(float(row["gradient_norm"]) ** 2 for row in rows)
            reference_squared = sum(
                float(row["reference_norm"]) ** 2 for row in rows
            )
            denominator = math.sqrt(norm_squared * reference_squared)
            candidates[candidate] = {
                "concatenated_dot": dot,
                "concatenated_gradient_norm": math.sqrt(norm_squared),
                "concatenated_reference_norm": math.sqrt(reference_squared),
                "concatenated_cosine": dot / denominator if denominator else None,
                "snapshots": len(rows),
                "finite": all(bool(row["finite"]) for row in rows),
            }
        aggregate[channel] = {"candidates": candidates}
    return aggregate


def replay_founder(
    source: Mapping[str, Any],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Replay one source silence cell and measure read-only gradient alternatives."""

    founder = int(source["founder"])
    if founder not in FOUNDERS:
        raise ValueError("unregistered replay founder")
    source_result_path = Path(source["source_result"])
    source_result = json.loads(source_result_path.read_text(encoding="utf-8"))
    incoming = np.asarray(source["incoming_germ"], dtype=np.uint8)
    diagnostic_carrier = np.asarray(source["diagnostic_carrier"], dtype=np.uint8)
    initial_diagnostic_carrier = diagnostic_carrier.copy()
    packet = make_boundary_packet(incoming)
    result_path = output_dir / f"founder_{founder}.json"
    progress_path = output_dir / f"founder_{founder}_progress.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("run_id") != RUN_ID
            or result.get("founder") != founder
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable gradient result for {founder}")
        return result

    descendant = frozen_vertical.make_vertical_descendant(
        packet, config, int(source["birth_seed"])
    )
    boundary = frozen_vertical.audit_vertical_boundary(
        Path(source["parent_checkpoint"]),
        descendant,
        packet,
        generation=source_reader.GENERATION,
    )
    environments = DoorKeyVectorEnv(
        config.num_envs,
        int(source["training_seed"]),
        config.max_episode_steps,
        "terminal",
    )
    source_history = source_result["history"]
    replay_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    gradient_snapshots: list[dict[str, Any]] = []
    semantics_accumulator: dict[str, bool] = {}
    for update in range(1, UPDATES + 1):
        rollout, completed = frozen_vertical.collect_vertical_rollout(
            descendant, environments, config, "blind"
        )
        expected = source_history[update - 1]
        rollout_sha256 = matched.deep_digest(vars(rollout))
        completed_sha256 = matched.deep_digest(completed)
        semantics = rollout_semantics(rollout)
        for name, passed in semantics.items():
            semantics_accumulator[name] = bool(
                semantics_accumulator.get(name, True) and passed
            )
        pre_diagnostic = matched.soma_environment_digests(
            descendant, environments
        )
        support = counterfactual_support_snapshot(rollout, diagnostic_carrier)
        support_rows.append({"update": update, **support})
        gradient_row = None
        if update in GRADIENT_UPDATES:
            gradient_row = counterfactual_gradient_snapshot(
                descendant,
                rollout,
                config,
                diagnostic_carrier,
            )
            gradient_row["update"] = update
            gradient_snapshots.append(gradient_row)
        post_diagnostic = matched.soma_environment_digests(
            descendant, environments
        )
        diagnostic_exact = pre_diagnostic == post_diagnostic
        metrics = frozen_vertical.vertical_phase_ppo_update(
            descendant, rollout, config, "blind"
        )
        post_update = matched.soma_environment_digests(descendant, environments)
        metric_exact = all(metrics[name] == expected[name] for name in METRIC_NAMES)
        gates = {
            "rollout_exact": rollout_sha256 == expected["rollout_sha256"],
            "completed_rows_exact": completed_sha256
            == expected["completed_episode_rows_sha256"],
            "event_counts_exact": {
                channel: int(rollout.event_rewards[:, :, index].sum().item())
                for index, channel in enumerate(CHANNELS)
            }
            == expected["event_counts"],
            "phase_counts_exact": {
                channel: int(torch.count_nonzero(rollout.phases == index).item())
                for index, channel in enumerate(CHANNELS)
            }
            == expected["phase_counts"],
            "ppo_metrics_exact": metric_exact,
            "post_update_state_exact": post_update["aggregate"]
            == expected["post_update_soma_environment_sha256"],
            "diagnostic_state_exact": diagnostic_exact,
            "scheduled_gradient_present": (update in GRADIENT_UPDATES)
            == (gradient_row is not None),
        }
        replay_rows.append(
            {
                "update": update,
                "rollout_sha256": rollout_sha256,
                "completed_episode_rows_sha256": completed_sha256,
                "pre_diagnostic_soma_environment_sha256": pre_diagnostic[
                    "aggregate"
                ],
                "post_diagnostic_soma_environment_sha256": post_diagnostic[
                    "aggregate"
                ],
                "post_update_soma_environment_sha256": post_update["aggregate"],
                "gates": gates,
                "passes": all(gates.values()),
            }
        )
        if update % 5 == 0:
            atomic_json(
                progress_path,
                {
                    "status": "RUNNING",
                    "founder": founder,
                    "update": update,
                    "updates": UPDATES,
                    "all_replay_rows_exact": all(
                        row["passes"] for row in replay_rows
                    ),
                    "updated_utc": utc_now(),
                },
                output_root,
            )
            print(
                f"founder {founder} gradient replay {update}/{UPDATES}", flush=True
            )

    final_digests = matched.soma_environment_digests(descendant, environments)
    support_aggregate = _aggregate_support(support_rows)
    gradient_aggregate = _aggregate_gradient_snapshots(gradient_snapshots)
    gates = {
        "boundary_reset_passes": bool(boundary["passes"]),
        "source_result_hash_exact": sha256_file(source_result_path)
        == source["source_result_sha256"],
        "all_100_rollouts_and_updates_exact": len(replay_rows) == UPDATES
        and all(row["passes"] for row in replay_rows),
        "all_rollout_semantics_pass": bool(semantics_accumulator)
        and all(semantics_accumulator.values()),
        "seven_gradient_snapshots": [
            int(row["update"]) for row in gradient_snapshots
        ]
        == list(GRADIENT_UPDATES),
        "all_gradient_snapshots_state_exact": all(
            bool(row["diagnostic_state_exact"]) for row in gradient_snapshots
        ),
        "all_gradient_geometry_finite": all(
            candidate["finite"]
            for channel in gradient_aggregate.values()
            for candidate in channel["candidates"].values()
        ),
        "final_state_exact": final_digests["aggregate"]
        == source_result["final_soma_environment_digests"]["aggregate"],
        "diagnostic_carrier_unchanged": np.array_equal(
            diagnostic_carrier, initial_diagnostic_carrier
        ),
        "diagnostic_carrier_exactly_64_bytes": diagnostic_carrier.nbytes == 64,
        "replay_carrier_remains_empty": not bool(
            read_germ(descendant.learner.germ).active.any()
        )
        and carrier_digest(descendant.learner.germ)
        == source["incoming_carrier_sha256"],
        "action_reader_blind_throughout": True,
    }
    result = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "source_run_id": SOURCE_RUN,
        "founder": founder,
        "birth_seed": source["birth_seed"],
        "training_seed": source["training_seed"],
        "source_result": str(source_result_path),
        "source_result_sha256": source["source_result_sha256"],
        "incoming_carrier_sha256": source["incoming_carrier_sha256"],
        "diagnostic_carrier_sha256": source["diagnostic_carrier_sha256"],
        "boundary_audit": boundary,
        "replay_rows": replay_rows,
        "support_rows": support_rows,
        "gradient_snapshots": gradient_snapshots,
        "support_aggregate": support_aggregate,
        "gradient_aggregate": gradient_aggregate,
        "final_soma_environment_digests": final_digests,
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    atomic_json(result_path, result, output_root)
    atomic_json(
        progress_path,
        {
            "status": "COMPLETE" if result["completed_cleanly"] else "FAILED_GATES",
            "founder": founder,
            "update": UPDATES,
            "result_path": str(result_path),
            "updated_utc": utc_now(),
        },
        output_root,
    )
    if not result["completed_cleanly"]:
        raise RuntimeError(f"founder {founder} gradient replay failed: {gates}")
    return result


def _worker_replay(
    source: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    output_root_text: str,
    output_dir_text: str,
) -> dict[str, Any]:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    return replay_founder(
        source,
        FeedbackPPOConfig(**dict(config_payload)),
        Path(output_root_text),
        Path(output_dir_text),
    )


def geometric_admissibility(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply registered gradient-direction sanity checks, not behavior gates."""

    founder_rows: list[dict[str, Any]] = []
    for result in results:
        founder = int(result["founder"])
        for channel in ("key", "door"):
            current_fraction = result["support_aggregate"][channel]["candidates"][
                "prestandard_uniform_current"
            ]["non_target_absolute_fraction"]
            for candidate in CANDIDATES:
                gradient = result["gradient_aggregate"][channel]["candidates"][
                    candidate
                ]
                support = result["support_aggregate"][channel]["candidates"][
                    candidate
                ]
                fraction = support["non_target_absolute_fraction"]
                founder_rows.append(
                    {
                        "founder": founder,
                        "channel": channel,
                        "candidate": candidate,
                        "concatenated_cosine": gradient["concatenated_cosine"],
                        "non_target_absolute_fraction": fraction,
                        "current_non_target_absolute_fraction": current_fraction,
                        "event_deltas_nonnegative": support[
                            "all_confirming_event_deltas_nonnegative"
                        ],
                        "positive_reference_cosine": gradient[
                            "concatenated_cosine"
                        ]
                        is not None
                        and gradient["concatenated_cosine"] > 0.0,
                        "less_non_target_credit_than_current": fraction is not None
                        and current_fraction is not None
                        and fraction < current_fraction,
                    }
                )
    decisions: list[dict[str, Any]] = []
    for channel in ("key", "door"):
        for candidate in CANDIDATES:
            rows = [
                row
                for row in founder_rows
                if row["channel"] == channel and row["candidate"] == candidate
            ]
            gates = {
                "positive_reference_cosine_all_founders": len(rows) == len(FOUNDERS)
                and all(row["positive_reference_cosine"] for row in rows),
                "event_deltas_nonnegative_all_founders": len(rows) == len(FOUNDERS)
                and all(row["event_deltas_nonnegative"] for row in rows),
                "less_non_target_credit_than_current_all_founders": len(rows)
                == len(FOUNDERS)
                and all(row["less_non_target_credit_than_current"] for row in rows),
            }
            decisions.append(
                {
                    "channel": channel,
                    "candidate": candidate,
                    "founder_rows": rows,
                    "gates": gates,
                    "classification": (
                        "GEOMETRICALLY_ADMISSIBLE"
                        if all(gates.values())
                        else "NOT_GEOMETRICALLY_ADMISSIBLE"
                    ),
                }
            )

    recommendations: dict[str, Any] = {}
    predecessor_candidates = {
        "poststandard_uniform",
        "trace_target_only",
        "positive_decay_short",
        "positive_decay_long",
    }
    for channel in ("key", "door"):
        admissible = [
            row
            for row in decisions
            if row["channel"] == channel
            and row["classification"] == "GEOMETRICALLY_ADMISSIBLE"
        ]
        retaining = [
            row for row in admissible if row["candidate"] in predecessor_candidates
        ]
        pool = retaining or admissible
        if pool:
            selected = min(
                pool,
                key=lambda row: float(
                    np.mean(
                        [
                            founder["non_target_absolute_fraction"]
                            for founder in row["founder_rows"]
                        ]
                    )
                ),
            )
            reason = (
                "admissible predecessor-credit rule with least mean non-target mass"
                if retaining
                else "event-only conservative fallback"
            )
            recommendations[channel] = {
                "candidate": selected["candidate"],
                "reason": reason,
                "behavioral_validation_required": True,
            }
        else:
            recommendations[channel] = {
                "candidate": None,
                "reason": "no candidate passed all causal-geometry checks",
                "behavioral_validation_required": True,
            }
    return {
        "founder_rows": founder_rows,
        "candidate_decisions": decisions,
        "recommendations": recommendations,
        "behavioral_success_claimed": False,
    }


def markdown_report(audit: Mapping[str, Any]) -> str:
    decisions = audit["geometric_admissibility"]
    lines = [
        "# DoorKey counterfactual causal-gradient audit v1",
        "",
        f"**Structural completion:** `{'PASS' if audit['completed_cleanly'] else 'FAIL'}`",
        "",
        "## Exact silence replay",
        "",
    ]
    for result in audit["founder_summaries"]:
        lines.append(
            f"- Founder {result['founder']}: 100/100 rollouts, PPO updates, and "
            f"post-update states `{'EXACT' if result['completed_cleanly'] else 'FAILED'}`."
        )
    lines.extend(["", "## Concatenated gradient geometry", ""])
    lines.append(
        "| Channel | Candidate | F1 cosine | F2 cosine | F3 cosine | Mean non-target fraction | Decision |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for channel in ("key", "door"):
        for candidate in CANDIDATES:
            decision = next(
                row
                for row in decisions["candidate_decisions"]
                if row["channel"] == channel and row["candidate"] == candidate
            )
            founder_rows = sorted(decision["founder_rows"], key=lambda row: row["founder"])
            cosines = [row["concatenated_cosine"] for row in founder_rows]
            fractions = [row["non_target_absolute_fraction"] for row in founder_rows]
            lines.append(
                f"| {channel} | `{candidate}` | "
                + " | ".join(
                    "NA" if value is None else f"{value:+.4f}" for value in cosines
                )
                + f" | {float(np.mean(fractions)):.4f} | "
                f"`{decision['classification']}` |"
            )
    lines.extend(["", "## Mechanism recommendation", ""])
    for channel, row in decisions["recommendations"].items():
        lines.append(
            f"- {channel}: `{row['candidate']}` — {row['reason']}."
        )
    lines.extend(["", "## Structural completion gates", ""])
    for name, passed in audit["completion_gates"].items():
        lines.append(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            (
                "Admissibility means only that added credit points in a sane "
                "local event-action direction with less collateral credit than "
                "the failed rule. It is not evidence of behavioral benefit."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _input_paths(workspace: Path, root: Path, source: Mapping[str, Any]) -> list[Path]:
    source_output = root / "outputs" / SOURCE_RUN
    source_run = root / "runs" / SOURCE_RUN
    source_manifest = json.loads(
        (source_run / "MANIFEST.json").read_text(encoding="utf-8")
    )
    paths = [
        workspace / "protocols/DOORKEY_COUNTERFACTUAL_GRADIENT_AUDIT_V1.md",
        workspace / "requirements-doorkey.lock",
        Path(__file__).resolve(),
        workspace / "src/laws_confirmation/doorkey_learning_only_reader.py",
        workspace / "src/laws_confirmation/doorkey_matched_disposition.py",
        workspace / "src/laws_confirmation/doorkey_vertical_scout.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_credit.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/io.py",
        workspace / "tests/test_doorkey_counterfactual_gradient.py",
        workspace / "scripts/run_doorkey_counterfactual_gradient.sh",
        source_output / "learning_only_reader.json",
        source_output / "audit.md",
        source_output / "input_hashes.sha256",
        source_output / "output_hashes.sha256",
        source_run / "MANIFEST.json",
        source_run / "STATUS.json",
        source_run / "COMPLETE",
    ]
    paths.extend(Path(path) for path in source_manifest.get("input_sha256", {}))
    for row in source["replay_sources"]:
        paths.extend(
            (Path(row["source_result"]), Path(row["parent_checkpoint"]))
        )
    unique = sorted({path.resolve() for path in paths})
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen gradient-audit inputs: {missing}")
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
        "exactly_three_workers": workers == MAX_WORKERS,
    }
    return {"values": values, "gates": gates, "passes": all(gates.values())}


def run_audit(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if args.run_id != RUN_ID:
        raise ValueError(f"frozen run ID must be {RUN_ID}")
    if args.workers != MAX_WORKERS:
        raise ValueError(f"frozen audit requires exactly {MAX_WORKERS} workers")
    root = external_root(args.external_root)
    output_dir = root / "outputs" / args.run_id
    run_dir = root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    source = qualify_source(root)
    if not source["passes"]:
        raise RuntimeError(f"source qualification failed: {source['gates']}")
    config = FeedbackPPOConfig(**dict(source["replay_sources"][0]["config"]))
    input_paths = _input_paths(workspace, root, source)
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    contract_digest = canonical_digest(input_hashes)
    disk = _disk_preflight(root, 16 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if args.resume:
        if not run_dir.is_dir() or not output_dir.is_dir():
            raise FileNotFoundError("cannot resume an uninitialized audit")
        if (run_dir / "COMPLETE").is_file():
            print(output_dir / "audit.md")
            return 0
        manifest = json.loads(
            (run_dir / "MANIFEST.json").read_text(encoding="utf-8")
        )
        if (
            manifest.get("run_id") != RUN_ID
            or manifest.get("contract_digest") != contract_digest
            or manifest.get("workers") != MAX_WORKERS
        ):
            raise RuntimeError("resume contract differs from initialized audit")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        run_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "source_run_id": SOURCE_RUN,
            "stage": "DoorKey counterfactual causal-gradient replay audit",
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
            "updates": UPDATES,
            "gradient_updates": list(GRADIENT_UPDATES),
            "candidates": list(CANDIDATES),
            "registered_transitions": REGISTERED_TRANSITIONS,
            "behavioral_success_endpoint": None,
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
            "run_id": RUN_ID,
            "resume": bool(args.resume),
        },
        root,
    )
    atomic_text(run_dir / "RUN.pid", f"{os.getpid()}\n", root)

    try:
        runtime = runtime_qualification(args.workers)
        started = time.monotonic()
        results: list[dict[str, Any]] = []
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=MAX_WORKERS,
            mp_context=context,
        ) as executor:
            futures = {
                executor.submit(
                    _worker_replay,
                    row,
                    asdict(config),
                    str(root),
                    str(output_dir),
                ): int(row["founder"])
                for row in source["replay_sources"]
            }
            for future in as_completed(futures):
                founder = futures[future]
                try:
                    results.append(future.result())
                except Exception as error:
                    raise RuntimeError(
                        f"founder {founder} counterfactual replay failed"
                    ) from error
                atomic_json(
                    output_dir / "progress.json",
                    {
                        "status": "RUNNING",
                        "completed_founders": len(results),
                        "registered_founders": len(FOUNDERS),
                        "updated_utc": utc_now(),
                    },
                    root,
                )
        elapsed = time.monotonic() - started
        results.sort(key=lambda row: int(row["founder"]))
        decisions = geometric_admissibility(results)
        founder_summaries = [
            {
                "founder": int(row["founder"]),
                "completed_cleanly": bool(row["completed_cleanly"]),
                "source_result_sha256": row["source_result_sha256"],
                "diagnostic_carrier_sha256": row["diagnostic_carrier_sha256"],
                "support_aggregate": row["support_aggregate"],
                "gradient_aggregate": row["gradient_aggregate"],
                "completion_gates": row["completion_gates"],
            }
            for row in results
        ]
        completion_gates = {
            "runtime_qualified": bool(runtime["passes"]),
            "source_qualified": bool(source["passes"]),
            "exactly_three_founder_replays": len(results) == len(FOUNDERS)
            and [int(row["founder"]) for row in results] == list(FOUNDERS),
            "all_300_rollouts_and_updates_exact": all(
                row["completion_gates"]["all_100_rollouts_and_updates_exact"]
                for row in results
            ),
            "all_diagnostics_state_invariant": all(
                row["completion_gates"]["all_gradient_snapshots_state_exact"]
                and all(
                    replay["gates"]["diagnostic_state_exact"]
                    for replay in row["replay_rows"]
                )
                for row in results
            ),
            "all_21_gradient_snapshots_present": sum(
                len(row["gradient_snapshots"]) for row in results
            )
            == len(FOUNDERS) * len(GRADIENT_UPDATES),
            "all_gradient_metrics_finite": all(
                row["completion_gates"]["all_gradient_geometry_finite"]
                for row in results
            ),
            "all_channel_reference_gradients_nonzero": all(
                row["gradient_aggregate"][channel]["candidates"][
                    "event_only_reference"
                ]["concatenated_reference_norm"]
                > 0.0
                for row in results
                for channel in ("key", "door")
            ),
            "all_boundary_and_carrier_checks_pass": all(
                row["completion_gates"]["boundary_reset_passes"]
                and row["completion_gates"]["diagnostic_carrier_unchanged"]
                and row["completion_gates"][
                    "diagnostic_carrier_exactly_64_bytes"
                ]
                and row["completion_gates"]["replay_carrier_remains_empty"]
                and row["completion_gates"]["action_reader_blind_throughout"]
                for row in results
            ),
            "all_cell_completion_gates_pass": all(
                all(row["completion_gates"].values()) for row in results
            ),
            "three_workers_one_thread": args.workers == MAX_WORKERS
            and runtime["values"]["torch_num_threads"] == 1,
            "no_behavioral_success_claim": not decisions["behavioral_success_claimed"],
        }
        audit = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "source_run_id": SOURCE_RUN,
            "generated_utc": utc_now(),
            "status": "COUNTERFACTUAL_CAUSAL_GRADIENT_AUDIT",
            "runtime": runtime,
            "source": source,
            "config": asdict(config),
            "founders": list(FOUNDERS),
            "updates": UPDATES,
            "gradient_updates": list(GRADIENT_UPDATES),
            "candidates": list(CANDIDATES),
            "founder_result_files": [
                str(output_dir / f"founder_{founder}.json") for founder in FOUNDERS
            ],
            "founder_summaries": founder_summaries,
            "geometric_admissibility": decisions,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "registered_transitions": REGISTERED_TRANSITIONS,
            "elapsed_seconds": elapsed,
            "max_workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output_dir / "gradient_audit.json", audit, root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), root)
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
        status_ok = bool(audit["completed_cleanly"] and outputs_verify)
        status = {
            "status": "COMPLETE" if status_ok else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "completed_cleanly": bool(audit["completed_cleanly"]),
            "output_manifest_self_verifies": outputs_verify,
            "registered_transitions": REGISTERED_TRANSITIONS,
            "max_workers": MAX_WORKERS,
            "recommendations": decisions["recommendations"],
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
    return run_audit(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
