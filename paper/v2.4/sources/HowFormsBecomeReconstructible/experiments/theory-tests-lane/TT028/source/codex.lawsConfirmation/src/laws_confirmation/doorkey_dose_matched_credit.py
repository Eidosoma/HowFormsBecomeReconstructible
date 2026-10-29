"""Dose- and address-matched counterfactual DoorKey credit audit."""

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

from . import doorkey_counterfactual_gradient as gradient_audit
from . import doorkey_targeted_learning_reader as targeted
from . import doorkey_vertical_multifounder as source_confirmation
from . import doorkey_vertical_scout as frozen_vertical
from . import doorkey_matched_disposition as matched
from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import carrier_digest, read_germ
from .doorkey_feedback_scout import _disk_preflight, _read_hash_manifest
from .doorkey_phase_value_credit import (
    CHANNELS,
    DOOR_CHANNEL,
    KEY_CHANNEL,
    CausalCreditDescendant,
    CausalCreditRollout,
    _forward_sequence_values,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import FeedbackPPOConfig, _apply_prior, _router_contexts
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


RUN_ID = "doorkey_dose_matched_credit_audit_v1_attempt1"
SOURCE_RUN = targeted.RUN_ID
FOUNDERS = (1, 2, 3)
UPDATES = targeted.UPDATES
GRADIENT_UPDATES = (1, 10, 20, 40, 60, 80, 100)
MAX_WORKERS = 3
REGISTERED_TRANSITIONS = len(FOUNDERS) * targeted.EXPECTED_STEPS
BETAS = (0.25, 0.50, 0.75, 1.00)
CONTEXT_LABELS = {
    0: "no_key_visible",
    1: "key_visible",
    2: "has_key_no_door_visible",
    3: "has_key_door_visible",
}
CHANNEL_ADDRESS = {KEY_CHANNEL: 1, DOOR_CHANNEL: 3}
CHANNEL_SPILL = {KEY_CHANNEL: 0, DOOR_CHANNEL: 2}
METRIC_NAMES = gradient_audit.METRIC_NAMES


def _beta_token(beta: float) -> str:
    return f"{int(round(beta * 100)):03d}"


CANDIDATE_SPECS: dict[str, tuple[str, float]] = {
    "event_only": ("event", 0.0),
    **{
        f"unrestricted_beta_{_beta_token(beta)}": ("unrestricted", beta)
        for beta in BETAS
    },
    **{
        f"addressed_beta_{_beta_token(beta)}": ("addressed", beta)
        for beta in BETAS
    },
}
CANDIDATES = tuple(CANDIDATE_SPECS)


def _flatten_gradients(
    gradients: Sequence[torch.Tensor | None],
    parameters: Sequence[torch.nn.Parameter],
) -> torch.Tensor:
    return torch.cat(
        [
            torch.zeros_like(parameter).reshape(-1)
            if gradient is None
            else gradient.detach().reshape(-1)
            for parameter, gradient in zip(parameters, gradients, strict=True)
        ]
    ).cpu()


def dose_matched_deltas(
    rollout: CausalCreditRollout,
    carrier: np.ndarray,
    channel: int,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Allocate exactly one trust-amplitude unit per confirmed event."""

    support = gradient_audit.confirmed_trace_support(rollout, carrier, channel)
    confirmed = support["confirmed"]
    target_action = int(support["target_action"])
    amplitude = float(support["amplitude"])
    address = CHANNEL_ADDRESS[channel]
    contexts = _router_contexts(
        rollout.observations.reshape(-1, rollout.observations.shape[-1])
    ).reshape_as(rollout.actions)
    dtype = rollout.goal_advantages.dtype
    event_delta = confirmed.to(dtype) * amplitude
    predecessor_basis = {
        "unrestricted": torch.zeros_like(event_delta),
        "addressed": torch.zeros_like(event_delta),
    }
    eligible_counts = {family: [] for family in predecessor_basis}

    for time_index, environment_index in (
        torch.nonzero(confirmed, as_tuple=False).detach().cpu().tolist()
    ):
        pools: dict[str, list[tuple[int, int]]] = {
            "unrestricted": [],
            "addressed": [],
        }
        for cursor in range(int(time_index) - 1, -1, -1):
            if int(rollout.phases[cursor, environment_index].item()) != channel:
                break
            if int(rollout.actions[cursor, environment_index].item()) == target_action:
                location = (cursor, int(environment_index))
                pools["unrestricted"].append(location)
                if int(contexts[cursor, environment_index].item()) == address:
                    pools["addressed"].append(location)
            if bool(rollout.episode_starts[cursor, environment_index].item()):
                break
        for family, locations in pools.items():
            eligible_counts[family].append(len(locations))
            if locations:
                share = amplitude / len(locations)
                for cursor, environment in locations:
                    predecessor_basis[family][cursor, environment] += share
            else:
                # With no predecessor, beta cannot move the event's fixed dose.
                predecessor_basis[family][time_index, environment_index] += amplitude

    deltas: dict[str, torch.Tensor] = {"event_only": event_delta}
    for candidate, (family, beta) in CANDIDATE_SPECS.items():
        if candidate == "event_only":
            continue
        deltas[candidate] = (
            (1.0 - beta) * event_delta + beta * predecessor_basis[family]
        )
    if tuple(deltas) != CANDIDATES:
        raise AssertionError("dose-matched candidate registry drift")
    return deltas, {
        "channel": channel,
        "channel_name": CHANNELS[channel],
        "address_context": address,
        "spill_context": CHANNEL_SPILL[channel],
        "record_active": bool(support["active"]),
        "target_action": target_action,
        "trust": int(support["trust"]),
        "amplitude": amplitude,
        "confirmed": confirmed,
        "contexts": contexts,
        "confirmed_event_count": int(torch.count_nonzero(confirmed).item()),
        "eligible_predecessors_per_event": eligible_counts,
        "events_with_unrestricted_predecessor": sum(
            count > 0 for count in eligible_counts["unrestricted"]
        ),
        "events_with_addressed_predecessor": sum(
            count > 0 for count in eligible_counts["addressed"]
        ),
    }


def candidate_support_metrics(
    delta: torch.Tensor,
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Summarize dose conservation and direct contextual placement."""

    contexts = audit["contexts"]
    confirmed = audit["confirmed"]
    address = int(audit["address_context"])
    total = float(delta.sum().item())
    expected = float(audit["confirmed_event_count"]) * float(audit["amplitude"])
    context_mass = {
        CONTEXT_LABELS[context]: float(delta[contexts == context].sum().item())
        for context in CONTEXT_LABELS
    }
    addressed_mass = float(delta[contexts == address].sum().item())
    off_address_mass = float(delta[contexts != address].sum().item())
    event_mass = float(delta[confirmed].sum().item())
    return {
        "total_positive_mass": total,
        "expected_total_mass": expected,
        "absolute_conservation_error": abs(total - expected),
        "event_mass": event_mass,
        "predecessor_mass": total - event_mass,
        "addressed_mass": addressed_mass,
        "off_address_mass": off_address_mass,
        "off_address_fraction": off_address_mass / total if total else None,
        "context_mass": context_mass,
        "credited_steps": int(torch.count_nonzero(delta).item()),
        "minimum_delta": float(delta.min().item()),
        "maximum_delta": float(delta.max().item()),
        "delta_sha256": matched.deep_digest(delta),
    }


def support_snapshot(
    rollout: CausalCreditRollout,
    carrier: np.ndarray,
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        deltas, audit = dose_matched_deltas(rollout, carrier, channel)
        rows[CHANNELS[channel]] = {
            key: value
            for key, value in audit.items()
            if key not in {"confirmed", "contexts"}
        } | {
            "candidates": {
                candidate: candidate_support_metrics(deltas[candidate], audit)
                for candidate in CANDIDATES
            }
        }
    return rows


def target_probability_probe_gradients(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    target_action: int,
) -> dict[int, dict[str, Any]]:
    """Gradients of mean target probability in each observed public context."""

    logits, _, _ = _forward_sequence_values(
        descendant,
        rollout.observations,
        rollout.initial_hidden,
        rollout.episode_starts,
        rollout.previous_actions,
        rollout.previous_rewards,
    )
    flat_observations = rollout.observations.reshape(-1, config.observation_width)
    flat_logits, _ = _apply_prior(
        logits.reshape(-1, config.num_actions),
        descendant.learner,
        flat_observations,
        "blind",
    )
    probabilities = F.softmax(flat_logits, dim=-1)
    contexts = _router_contexts(flat_observations)
    parameters = tuple(descendant.learner.model.parameters())
    present = [
        context
        for context in CONTEXT_LABELS
        if bool(torch.count_nonzero(contexts == context))
    ]
    rows: dict[int, dict[str, Any]] = {}
    for index, context in enumerate(present):
        mask = contexts == context
        value = probabilities[mask, target_action].mean()
        gradients = torch.autograd.grad(
            value,
            parameters,
            allow_unused=True,
            retain_graph=index < len(present) - 1,
        )
        rows[context] = {
            "sample_count": int(torch.count_nonzero(mask).item()),
            "mean_target_probability": float(value.detach().item()),
            "gradient": _flatten_gradients(gradients, parameters),
        }
    return rows


def gradient_snapshot(
    descendant: CausalCreditDescendant,
    rollout: CausalCreditRollout,
    config: FeedbackPPOConfig,
    carrier: np.ndarray,
) -> dict[str, Any]:
    """Measure dose-matched gradients and infinitesimal context responses."""

    before = {
        "soma": frozen_vertical.causal_credit_digests(descendant),
        "numpy_rng": matched.deep_digest(descendant.learner.numpy_rng.bit_generator.state),
        "torch_rng": matched.deep_digest(descendant.learner.torch_generator.get_state()),
    }
    channel_gradients: dict[int, dict[str, torch.Tensor]] = {}
    channel_rows: dict[str, Any] = {}
    for channel in (KEY_CHANNEL, DOOR_CHANNEL):
        deltas, audit = dose_matched_deltas(rollout, carrier, channel)
        basis_names = (
            "event_only",
            "unrestricted_beta_100",
            "addressed_beta_100",
        )
        basis = {
            name: gradient_audit.policy_gradient_vector(
                descendant, rollout, config, deltas[name]
            )
            for name in basis_names
        }
        gradients: dict[str, torch.Tensor] = {"event_only": basis["event_only"]}
        for candidate, (family, beta) in CANDIDATE_SPECS.items():
            if candidate == "event_only":
                continue
            gradients[candidate] = (
                (1.0 - beta) * basis["event_only"]
                + beta * basis[f"{family}_beta_100"]
            )
        reference = gradients["event_only"]
        probes = target_probability_probe_gradients(
            descendant, rollout, config, int(audit["target_action"])
        )
        responses: dict[str, Any] = {}
        for candidate in CANDIDATES:
            responses[candidate] = {
                CONTEXT_LABELS[context]: {
                    "sample_count": row["sample_count"],
                    "mean_target_probability": row["mean_target_probability"],
                    "descent_probability_response": float(
                        -torch.dot(row["gradient"], gradients[candidate]).item()
                    ),
                }
                for context, row in probes.items()
            }
        channel_gradients[channel] = gradients
        channel_rows[CHANNELS[channel]] = {
            key: value
            for key, value in audit.items()
            if key not in {"confirmed", "contexts"}
        } | {
            "candidate_support": {
                candidate: candidate_support_metrics(deltas[candidate], audit)
                for candidate in CANDIDATES
            },
            "gradient_geometry": {
                candidate: gradient_audit.gradient_geometry(
                    gradients[candidate], reference
                )
                for candidate in CANDIDATES
            },
            "context_probability_response": responses,
        }

    combined_reference = (
        channel_gradients[KEY_CHANNEL]["event_only"]
        + channel_gradients[DOOR_CHANNEL]["event_only"]
    )
    combined = {
        candidate: gradient_audit.gradient_geometry(
            channel_gradients[KEY_CHANNEL][candidate]
            + channel_gradients[DOOR_CHANNEL][candidate],
            combined_reference,
        )
        for candidate in CANDIDATES
    }
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


def qualify_source(root: Path) -> dict[str, Any]:
    """Verify the completed targeted-reader run and its event-only cells."""

    output_dir = root / "outputs" / SOURCE_RUN
    run_dir = root / "runs" / SOURCE_RUN
    study_path = output_dir / "targeted_learning_reader.json"
    manifest_path = run_dir / "MANIFEST.json"
    status_path = run_dir / "STATUS.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    input_rows = matched._verify_manifest_inputs(manifest)
    output_rows = _read_hash_manifest(output_dir / "output_hashes.sha256")
    output_paths = {row["path"] for row in output_rows}
    labels = study.get("registered_classification", {}).get("labels", {})
    specs = {
        (int(row["founder"]), str(row["arm"])): row
        for row in study.get("cell_specs", [])
    }
    replay_sources: list[dict[str, Any]] = []
    config_digests: set[str] = set()
    for founder in FOUNDERS:
        spec = specs[(founder, "event_only_correct")]
        result_path = output_dir / f"founder_{founder}" / "g4_event_only_correct.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        incoming = np.asarray(spec["incoming_germ"], dtype=np.uint8)
        packet_audit = source_confirmation._correct_functional_packet(incoming)
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
            and result.get("arm") == "event_only_correct"
            and result.get("generation") == targeted.GENERATION,
            "result_completed": bool(result.get("completed_cleanly")),
            "result_100_updates": len(result.get("history", [])) == UPDATES,
            "event_only_action_blind": result.get("credit_mode") == "event_only"
            and result.get("action_germ_mode") == "blind",
            "correct_packet_exact": incoming.shape == (1, 64)
            and incoming.nbytes == 64
            and bool(packet_audit["passes"])
            and carrier_digest(incoming) == result.get("incoming_carrier_sha256"),
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
        "three_negative_classifications_exact": labels
        == {
            "target_trace": "TARGET_TRACE_BENEFIT_NOT_3_OF_3",
            "event_only": "EVENT_ONLY_BENEFIT_NOT_3_OF_3",
            "predecessor_credit": "PREDECESSOR_CREDIT_BENEFIT_NOT_3_OF_3",
        },
        "source_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "source_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
        "source_manifest_self_verified": bool(
            status.get("output_manifest_self_verifies")
        ),
        "three_event_only_sources_pass": len(replay_sources) == len(FOUNDERS)
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
        candidates: dict[str, Any] = {}
        for candidate in CANDIDATES:
            rows = [row[channel]["candidates"][candidate] for row in support_rows]
            total = sum(float(row["total_positive_mass"]) for row in rows)
            addressed = sum(float(row["addressed_mass"]) for row in rows)
            off_address = sum(float(row["off_address_mass"]) for row in rows)
            context_mass = {
                label: sum(float(row["context_mass"][label]) for row in rows)
                for label in CONTEXT_LABELS.values()
            }
            candidates[candidate] = {
                "total_positive_mass": total,
                "expected_total_mass": sum(
                    float(row["expected_total_mass"]) for row in rows
                ),
                "maximum_absolute_conservation_error": max(
                    float(row["absolute_conservation_error"]) for row in rows
                ),
                "event_mass": sum(float(row["event_mass"]) for row in rows),
                "predecessor_mass": sum(
                    float(row["predecessor_mass"]) for row in rows
                ),
                "addressed_mass": addressed,
                "off_address_mass": off_address,
                "off_address_fraction": off_address / total if total else None,
                "context_mass": context_mass,
                "credited_steps": sum(int(row["credited_steps"]) for row in rows),
                "all_deltas_nonnegative": all(
                    float(row["minimum_delta"]) >= 0.0 for row in rows
                ),
            }
        aggregate[channel] = {
            "confirmed_event_count": sum(
                int(row[channel]["confirmed_event_count"]) for row in support_rows
            ),
            "events_with_unrestricted_predecessor": sum(
                int(row[channel]["events_with_unrestricted_predecessor"])
                for row in support_rows
            ),
            "events_with_addressed_predecessor": sum(
                int(row[channel]["events_with_addressed_predecessor"])
                for row in support_rows
            ),
            "candidates": candidates,
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
                    row["combined_gradient_geometry"][candidate]
                    for row in snapshots
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
            candidate_row: dict[str, Any] = {
                "concatenated_dot": dot,
                "concatenated_gradient_norm": math.sqrt(norm_squared),
                "concatenated_reference_norm": math.sqrt(reference_squared),
                "concatenated_cosine": dot / denominator if denominator else None,
                "gradient_norm_ratio": (
                    math.sqrt(norm_squared / reference_squared)
                    if reference_squared
                    else None
                ),
                "snapshots": len(rows),
                "finite": all(bool(row["finite"]) for row in rows),
            }
            if channel != "combined":
                desired = CHANNEL_ADDRESS[
                    KEY_CHANNEL if channel == "key" else DOOR_CHANNEL
                ]
                spill = CHANNEL_SPILL[
                    KEY_CHANNEL if channel == "key" else DOOR_CHANNEL
                ]
                context_rows = [
                    row["channels"][channel]["context_probability_response"][
                        candidate
                    ]
                    for row in snapshots
                ]

                def responses(context: int) -> list[float]:
                    label = CONTEXT_LABELS[context]
                    return [
                        float(row[label]["descent_probability_response"])
                        for row in context_rows
                        if label in row
                    ]

                desired_values = responses(desired)
                spill_values = responses(spill)
                positive_desired = sum(max(value, 0.0) for value in desired_values)
                positive_spill = sum(max(value, 0.0) for value in spill_values)
                candidate_row["context_response"] = {
                    "desired_context": desired,
                    "spill_context": spill,
                    "desired_response_sum": sum(desired_values),
                    "spill_response_sum": sum(spill_values),
                    "positive_desired_response_sum": positive_desired,
                    "positive_spill_response_sum": positive_spill,
                    "positive_spill_to_desired_ratio": (
                        positive_spill / positive_desired
                        if positive_desired
                        else None
                    ),
                    "desired_snapshots_observed": len(desired_values),
                    "spill_snapshots_observed": len(spill_values),
                }
            candidates[candidate] = candidate_row
        aggregate[channel] = {"candidates": candidates}
    return aggregate


def replay_founder(
    source: Mapping[str, Any],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Exactly replay one event-only learner while auditing alternatives."""

    founder = int(source["founder"])
    if founder not in FOUNDERS:
        raise ValueError("unregistered replay founder")
    source_result_path = Path(source["source_result"])
    source_result = json.loads(source_result_path.read_text(encoding="utf-8"))
    incoming = np.asarray(source["incoming_germ"], dtype=np.uint8)
    initial_carrier = incoming.copy()
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
            raise RuntimeError(f"invalid resumable dose audit for founder {founder}")
        return result

    descendant = frozen_vertical.make_vertical_descendant(
        packet, config, int(source["birth_seed"])
    )
    boundary = frozen_vertical.audit_vertical_boundary(
        Path(source["parent_checkpoint"]),
        descendant,
        packet,
        generation=targeted.GENERATION,
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
        pre_diagnostic = matched.soma_environment_digests(descendant, environments)
        support = support_snapshot(rollout, incoming)
        support_rows.append({"update": update, **support})
        gradient_row = None
        if update in GRADIENT_UPDATES:
            gradient_row = gradient_snapshot(descendant, rollout, config, incoming)
            gradient_row["update"] = update
            gradient_snapshots.append(gradient_row)
        post_diagnostic = matched.soma_environment_digests(descendant, environments)
        metrics = targeted.targeted_ppo_update(
            descendant,
            rollout,
            config,
            learning_carrier=descendant.learner.germ,
            credit_mode="event_only",
            germ_mode="blind",
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
            "event_credit_audit_exact": metrics["credit_audit"]
            == expected["credit_audit"],
            "post_update_state_exact": post_update["aggregate"]
            == expected["post_update_soma_environment_sha256"],
            "diagnostic_state_exact": pre_diagnostic == post_diagnostic,
            "scheduled_gradient_present": (update in GRADIENT_UPDATES)
            == (gradient_row is not None),
        }
        replay_rows.append(
            {
                "update": update,
                "rollout_sha256": rollout_sha256,
                "completed_episode_rows_sha256": completed_sha256,
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
            print(f"founder {founder} dose replay {update}/{UPDATES}", flush=True)

    final_digests = matched.soma_environment_digests(descendant, environments)
    support_aggregate = _aggregate_support(support_rows)
    gradient_aggregate = _aggregate_gradient_snapshots(gradient_snapshots)
    all_conserved = all(
        row["maximum_absolute_conservation_error"] <= 1e-5
        for channel in support_aggregate.values()
        for row in channel["candidates"].values()
    )
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
        "all_candidate_doses_conserved": all_conserved,
        "all_candidate_deltas_nonnegative": all(
            candidate["all_deltas_nonnegative"]
            for channel in support_aggregate.values()
            for candidate in channel["candidates"].values()
        ),
        "final_state_exact": final_digests["aggregate"]
        == source_result["final_soma_environment_digests"]["aggregate"],
        "carrier_unchanged": np.array_equal(incoming, initial_carrier)
        and np.array_equal(descendant.learner.germ, initial_carrier),
        "carrier_exactly_64_bytes": incoming.nbytes == 64,
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
        raise RuntimeError(f"founder {founder} dose replay failed: {gates}")
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


def mechanical_admissibility(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply the frozen mechanism screen and choose no behavioral winner."""

    founder_rows: list[dict[str, Any]] = []
    for result in results:
        founder = int(result["founder"])
        for channel in ("key", "door"):
            for candidate in CANDIDATES:
                support = result["support_aggregate"][channel]["candidates"][
                    candidate
                ]
                gradient = result["gradient_aggregate"][channel]["candidates"][
                    candidate
                ]
                response = gradient["context_response"]
                founder_rows.append(
                    {
                        "founder": founder,
                        "channel": channel,
                        "candidate": candidate,
                        "family": CANDIDATE_SPECS[candidate][0],
                        "beta": CANDIDATE_SPECS[candidate][1],
                        "maximum_absolute_conservation_error": support[
                            "maximum_absolute_conservation_error"
                        ],
                        "off_address_fraction": support["off_address_fraction"],
                        "predecessor_mass": support["predecessor_mass"],
                        "concatenated_cosine": gradient["concatenated_cosine"],
                        "gradient_norm_ratio": gradient["gradient_norm_ratio"],
                        "desired_response_sum": response["desired_response_sum"],
                        "spill_response_sum": response["spill_response_sum"],
                        "positive_spill_to_desired_ratio": response[
                            "positive_spill_to_desired_ratio"
                        ],
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
            predecessor = candidate != "event_only"
            gates = {
                "candidate_retains_predecessor_credit": predecessor
                and len(rows) == len(FOUNDERS)
                and all(float(row["predecessor_mass"]) > 0.0 for row in rows),
                "dose_conserved_all_founders": len(rows) == len(FOUNDERS)
                and all(
                    float(row["maximum_absolute_conservation_error"]) <= 1e-5
                    for row in rows
                ),
                "positive_event_cosine_all_founders": len(rows) == len(FOUNDERS)
                and all(
                    row["concatenated_cosine"] is not None
                    and float(row["concatenated_cosine"]) > 0.0
                    for row in rows
                ),
                "gradient_norm_at_most_twice_reference_all_founders": len(rows)
                == len(FOUNDERS)
                and all(
                    row["gradient_norm_ratio"] is not None
                    and float(row["gradient_norm_ratio"]) <= 2.0
                    for row in rows
                ),
                "desired_response_positive_all_founders": len(rows) == len(FOUNDERS)
                and all(float(row["desired_response_sum"]) > 0.0 for row in rows),
                "zero_direct_off_address_credit_all_founders": len(rows)
                == len(FOUNDERS)
                and all(float(row["off_address_fraction"] or 0.0) == 0.0 for row in rows),
            }
            decisions.append(
                {
                    "channel": channel,
                    "candidate": candidate,
                    "family": CANDIDATE_SPECS[candidate][0],
                    "beta": CANDIDATE_SPECS[candidate][1],
                    "founder_rows": rows,
                    "gates": gates,
                    "classification": (
                        "MECHANICALLY_ADMISSIBLE"
                        if predecessor and all(gates.values())
                        else "NOT_MECHANICALLY_ADMISSIBLE"
                    ),
                }
            )

    recommendations: dict[str, Any] = {}
    for channel in ("key", "door"):
        event_rows = [
            row
            for row in founder_rows
            if row["channel"] == channel and row["candidate"] == "event_only"
        ]
        event_ratios = [
            float(row["positive_spill_to_desired_ratio"])
            for row in event_rows
            if row["positive_spill_to_desired_ratio"] is not None
        ]
        event_mean_ratio = (
            float(np.mean(event_ratios))
            if len(event_ratios) == len(FOUNDERS)
            else None
        )
        eligible: list[tuple[dict[str, Any], float]] = []
        for decision in decisions:
            if (
                decision["channel"] != channel
                or decision["classification"] != "MECHANICALLY_ADMISSIBLE"
            ):
                continue
            ratios = [
                float(row["positive_spill_to_desired_ratio"])
                for row in decision["founder_rows"]
                if row["positive_spill_to_desired_ratio"] is not None
            ]
            if len(ratios) != len(FOUNDERS) or event_mean_ratio is None:
                continue
            mean_ratio = float(np.mean(ratios))
            if mean_ratio <= event_mean_ratio:
                eligible.append((decision, mean_ratio))
        if eligible:
            selected, ratio = max(eligible, key=lambda row: float(row[0]["beta"]))
            recommendations[channel] = {
                "candidate": selected["candidate"],
                "beta": selected["beta"],
                "mean_positive_spill_to_desired_ratio": ratio,
                "event_only_mean_positive_spill_to_desired_ratio": event_mean_ratio,
                "reason": "largest admissible beta no more spill-prone than event-only",
                "behavioral_validation_required": True,
            }
        else:
            recommendations[channel] = {
                "candidate": "event_only",
                "beta": 0.0,
                "mean_positive_spill_to_desired_ratio": event_mean_ratio,
                "event_only_mean_positive_spill_to_desired_ratio": event_mean_ratio,
                "reason": (
                    "no predecessor rule passed the frozen dose, address, geometry, "
                    "desired-response, and spill screen"
                ),
                "next_mechanism": "carrier_conditioned_subgoal_or_successor_value_head",
                "behavioral_validation_required": True,
            }
    return {
        "founder_rows": founder_rows,
        "candidate_decisions": decisions,
        "recommendations": recommendations,
        "behavioral_success_claimed": False,
    }


def markdown_report(audit: Mapping[str, Any]) -> str:
    decision = audit["mechanical_admissibility"]
    lines = [
        "# DoorKey dose-matched contextual-credit audit v1",
        "",
        f"**Structural completion:** `{'PASS' if audit['completed_cleanly'] else 'FAIL'}`  ",
        "**Behavioral result:** not tested",
        "",
        "## Exact event-only replay",
        "",
    ]
    for result in audit["founder_summaries"]:
        lines.append(
            f"- Founder {result['founder']}: 100/100 rollouts and updates "
            f"`{'EXACT' if result['completed_cleanly'] else 'FAILED'}`."
        )
    lines.extend(["", "## Direct contextual placement", ""])
    lines.append(
        "| Channel | Candidate | Mean off-address fraction | F1/F2/F3 cosine | "
        "F1/F2/F3 norm ratio | Decision |"
    )
    lines.append("|---|---|---:|---|---|---|")
    for channel in ("key", "door"):
        for candidate in CANDIDATES:
            rows = [
                row
                for row in decision["founder_rows"]
                if row["channel"] == channel and row["candidate"] == candidate
            ]
            verdict = next(
                row["classification"]
                for row in decision["candidate_decisions"]
                if row["channel"] == channel and row["candidate"] == candidate
            )
            off = [float(row["off_address_fraction"] or 0.0) for row in rows]
            cosines = "/".join(
                "NA"
                if row["concatenated_cosine"] is None
                else f"{float(row['concatenated_cosine']):+.3f}"
                for row in rows
            )
            norms = "/".join(
                "NA"
                if row["gradient_norm_ratio"] is None
                else f"{float(row['gradient_norm_ratio']):.3f}"
                for row in rows
            )
            lines.append(
                f"| {channel} | `{candidate}` | {float(np.mean(off)):.4f} | "
                f"{cosines} | {norms} | `{verdict}` |"
            )
    lines.extend(["", "## Frozen recommendations", ""])
    for channel, row in decision["recommendations"].items():
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
                "This audit tests local credit dose, address, and gradient geometry. "
                "It does not apply a candidate update and makes no behavioral or "
                "numbered-law success claim."
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
        workspace / "protocols/DOORKEY_DOSE_MATCHED_CREDIT_AUDIT_V1.md",
        workspace / "requirements-doorkey.lock",
        Path(__file__).resolve(),
        workspace / "src/laws_confirmation/doorkey_targeted_learning_reader.py",
        workspace / "src/laws_confirmation/doorkey_counterfactual_gradient.py",
        workspace / "src/laws_confirmation/doorkey_matched_disposition.py",
        workspace / "src/laws_confirmation/doorkey_vertical_multifounder.py",
        workspace / "src/laws_confirmation/doorkey_vertical_scout.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_credit.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/io.py",
        workspace / "tests/test_doorkey_dose_matched_credit.py",
        workspace / "scripts/run_doorkey_dose_matched_credit.sh",
        source_output / "targeted_learning_reader.json",
        source_output / "audit.md",
        source_output / "input_hashes.sha256",
        source_output / "output_hashes.sha256",
        source_run / "MANIFEST.json",
        source_run / "STATUS.json",
        source_run / "COMPLETE",
    ]
    paths.extend(Path(path) for path in source_manifest.get("input_sha256", {}))
    for row in source["replay_sources"]:
        paths.extend((Path(row["source_result"]), Path(row["parent_checkpoint"])))
    unique = sorted({path.resolve() for path in paths})
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen dose-audit inputs: {missing}")
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
    disk = _disk_preflight(root, 24 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if args.resume:
        if not run_dir.is_dir() or not output_dir.is_dir():
            raise FileNotFoundError("cannot resume an uninitialized dose audit")
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
            raise RuntimeError("resume contract differs from initialized dose audit")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        run_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "source_run_id": SOURCE_RUN,
            "stage": "DoorKey dose-matched contextual-credit replay audit",
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
            "betas": list(BETAS),
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
                        f"founder {founder} dose-matched replay failed"
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
        decisions = mechanical_admissibility(results)
        founder_summaries = [
            {
                "founder": int(row["founder"]),
                "completed_cleanly": bool(row["completed_cleanly"]),
                "source_result_sha256": row["source_result_sha256"],
                "incoming_carrier_sha256": row["incoming_carrier_sha256"],
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
                row["gradient_aggregate"][channel]["candidates"]["event_only"][
                    "concatenated_reference_norm"
                ]
                > 0.0
                for row in results
                for channel in ("key", "door")
            ),
            "all_candidate_doses_conserved": all(
                row["completion_gates"]["all_candidate_doses_conserved"]
                for row in results
            ),
            "all_boundary_and_carrier_checks_pass": all(
                row["completion_gates"]["boundary_reset_passes"]
                and row["completion_gates"]["carrier_unchanged"]
                and row["completion_gates"]["carrier_exactly_64_bytes"]
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
            "status": "DOSE_MATCHED_CONTEXTUAL_CREDIT_AUDIT",
            "runtime": runtime,
            "source": source,
            "config": asdict(config),
            "founders": list(FOUNDERS),
            "updates": UPDATES,
            "gradient_updates": list(GRADIENT_UPDATES),
            "betas": list(BETAS),
            "candidates": list(CANDIDATES),
            "founder_result_files": [
                str(output_dir / f"founder_{founder}.json") for founder in FOUNDERS
            ],
            "founder_summaries": founder_summaries,
            "mechanical_admissibility": decisions,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "registered_transitions": REGISTERED_TRANSITIONS,
            "elapsed_seconds": elapsed,
            "max_workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "numbered_law_verdict_changes": 0,
        }
        atomic_json(output_dir / "dose_matched_credit_audit.json", audit, root)
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
