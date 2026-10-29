"""DoorKey zero-reward null panel for diagnosing PPO policy drift."""

from __future__ import annotations

import argparse
from dataclasses import asdict
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
    _disk_preflight,
    _finite_history,
    _read_hash_manifest,
    _without_world_rows,
)
from .doorkey_feedback_terminal_multiseed import REGISTERED_REPLICATES
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import (
    FeedbackPPOConfig,
    FeedbackPPODescendant,
    FeedbackRolloutBatch,
    _apply_prior,
    collect_feedback_rollout,
    evaluate_feedback_policy,
    feedback_learner_digests,
    feedback_ppo_update,
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


TERMINAL_REFERENCE_RUN = "doorkey_feedback_terminal_multiseed_v1_attempt1"
NEW_ARMS = ("raw_advantage", "actor_guard", "zero_critic")
UPDATES = 20
EXPECTED_STEPS = 81_920


class ZeroRewardDoorKeyVectorEnv(DoorKeyVectorEnv):
    """Unchanged DoorKey transitions with all learner-visible rewards clamped."""

    def __init__(self, num_envs: int, base_seed: int, max_steps: int) -> None:
        super().__init__(num_envs, base_seed, max_steps, "terminal")

    def step(
        self, actions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]]]:
        observations, rewards, dones, infos = super().step(actions)
        rewards.fill(0.0)
        return observations, rewards, dones, infos


def qualify_terminal_reference(
    study_path: Path,
    manifest_path: Path,
    output_hashes_path: Path,
    replicate_paths: Sequence[Path],
) -> dict[str, Any]:
    """Verify the terminal study and its first-20-update zero-signal reference."""

    study = json.loads(study_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reference_results = [
        json.loads(path.read_text(encoding="utf-8")) for path in replicate_paths
    ]
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
    reference_specs = [
        {
            "replicate": int(row["replicate"]),
            "birth_seed": int(row["birth_seed"]),
            "training_seed": int(row["training_seed"]),
        }
        for row in reference_results
    ]
    first_twenty_zero = all(
        len(result["training"]["history"]) >= UPDATES
        and all(
            float(row["mean_rollout_reward"]) == 0.0
            and float(row["max_rollout_reward"]) == 0.0
            and int(row["cumulative_successes"]) == 0
            for row in result["training"]["history"][:UPDATES]
        )
        for result in reference_results
    )
    gates = {
        "reference_run_id_exact": study.get("run_id") == TERMINAL_REFERENCE_RUN,
        "reference_manifest_run_id_exact": manifest.get("run_id")
        == TERMINAL_REFERENCE_RUN,
        "reference_completed_cleanly": bool(study.get("completed_cleanly")),
        "reference_classification_exact": study.get(
            "credit_routing_classification"
        )
        == "NO_TERMINAL_REWARD_OBSERVED",
        "reference_seed_table_exact": reference_specs
        == list(REGISTERED_REPLICATES),
        "reference_first_twenty_rewards_exactly_zero": first_twenty_zero,
        "all_reference_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "all_reference_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
    }
    return {
        "gates": gates,
        "passes": all(gates.values()),
        "input_rows": input_rows,
        "output_rows": output_rows,
        "reference_digest": canonical_digest(study),
    }


def initialize_null_descendant(
    config: FeedbackPPOConfig, birth_seed: int, arm: str
) -> FeedbackPPODescendant:
    if arm not in NEW_ARMS:
        raise ValueError(f"unknown null-panel arm: {arm}")
    descendant = make_empty_feedback_descendant(config, birth_seed)
    if arm == "zero_critic":
        with torch.no_grad():
            descendant.model.critic.weight.zero_()
            descendant.model.critic.bias.zero_()
    return descendant


def _custom_null_update(
    descendant: FeedbackPPODescendant,
    rollout: FeedbackRolloutBatch,
    config: FeedbackPPOConfig,
    arm: str,
) -> dict[str, float]:
    """PPO update varying only the actor advantage treatment."""

    if arm not in ("raw_advantage", "actor_guard"):
        raise ValueError("custom update requires raw_advantage or actor_guard")
    if torch.count_nonzero(rollout.rewards).item() != 0:
        raise ValueError("null-panel update received nonzero reward")
    actor_advantage = (
        rollout.advantages
        if arm == "raw_advantage"
        else torch.zeros_like(rollout.advantages)
    )
    descendant.model.train()
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


def _evaluate(
    descendant: FeedbackPPODescendant,
    config: FeedbackPPOConfig,
    mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return _without_world_rows(
        evaluate_feedback_policy(
            descendant,
            config,
            germ_mode="blind",
            feedback_reward_mode="terminal",
            action_mode=mode,
            worlds_per_transform=8,
            stochastic_repeats=4,
        )
    )


def _train_cell(
    arm: str,
    spec: Mapping[str, int],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    replicate = int(spec["replicate"])
    birth_seed = int(spec["birth_seed"])
    training_seed = int(spec["training_seed"])
    stem = f"{arm}_replicate_{replicate}"
    result_path = output_dir / f"{stem}.json"
    checkpoint_path = output_dir / f"{stem}_checkpoint.pt"
    if result_path.is_file() != checkpoint_path.is_file():
        raise RuntimeError(f"partial resumable artifacts for {stem}")
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("arm") != arm
            or result.get("replicate") != replicate
            or result.get("birth_seed") != birth_seed
            or result.get("training_seed") != training_seed
            or result.get("updates") != UPDATES
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable result for {stem}")
        print(f"{stem} already complete; resuming after it", flush=True)
        return result

    descendant = initialize_null_descendant(config, birth_seed, arm)
    initial_germ = descendant.germ.copy()
    initial_state = feedback_learner_digests(descendant)
    critic_zero_at_birth = bool(
        torch.count_nonzero(descendant.model.critic.weight).item() == 0
        and torch.count_nonzero(descendant.model.critic.bias).item() == 0
    )
    evaluations: list[dict[str, Any]] = []
    for mode in ACTION_MODES:
        evaluation, _ = _evaluate(descendant, config, mode)
        evaluation["update"] = 0
        evaluations.append(evaluation)

    environments = ZeroRewardDoorKeyVectorEnv(
        config.num_envs, training_seed, config.max_episode_steps
    )
    history: list[dict[str, Any]] = []
    total_episodes = 0
    latent_environment_successes = 0
    for update in range(1, UPDATES + 1):
        rollout, completed = collect_feedback_rollout(
            descendant, environments, config, "blind"
        )
        if torch.count_nonzero(rollout.rewards).item() != 0:
            raise RuntimeError("forced-zero wrapper leaked nonzero reward")
        metrics = (
            feedback_ppo_update(descendant, rollout, config, "blind")
            if arm == "zero_critic"
            else _custom_null_update(descendant, rollout, config, arm)
        )
        update_successes = sum(bool(row["success"]) for row in completed)
        total_episodes += len(completed)
        latent_environment_successes += update_successes
        row: dict[str, Any] = {
            "update": update,
            "environment_steps": update
            * config.num_envs
            * config.rollout_steps,
            "episodes_completed": len(completed),
            "unrewarded_environment_successes": update_successes,
            "cumulative_episodes": total_episodes,
            "cumulative_unrewarded_environment_successes": (
                latent_environment_successes
            ),
            "mean_rollout_reward": float(rollout.rewards.mean()),
            "max_rollout_reward": float(rollout.rewards.max()),
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
                    "replicate": replicate,
                    "update": update,
                    "updates": UPDATES,
                    "environment_steps": row["environment_steps"],
                    "cumulative_episodes": total_episodes,
                    "cumulative_unrewarded_environment_successes": (
                        latent_environment_successes
                    ),
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
            if row["update"] == UPDATES and row["action_mode"] == mode
        ]
        expected = dict(evaluation)
        expected["update"] = UPDATES
        final_replay &= len(scheduled) == 1 and scheduled[0] == expected
    final_state = feedback_learner_digests(descendant)
    evaluation_counts = {
        mode: sum(row["action_mode"] == mode for row in evaluations)
        for mode in ACTION_MODES
    }
    gates = {
        "all_metrics_finite": _finite_history(history),
        "expected_environment_steps": history[-1]["environment_steps"]
        == EXPECTED_STEPS,
        "all_received_rewards_exactly_zero": all(
            row["mean_rollout_reward"] == 0.0
            and row["max_rollout_reward"] == 0.0
            for row in history
        ),
        "three_evaluations_per_mode": all(
            evaluation_counts[mode] == 3 for mode in ACTION_MODES
        ),
        "final_evaluations_replay_exactly": final_replay,
        "actor_critic_changed": initial_state["actor_critic"]
        != final_state["actor_critic"],
        "writer_unchanged": initial_state["writer"] == final_state["writer"],
        "carrier_birth_exact": bool(np.array_equal(descendant.germ, initial_germ)),
        "critic_birth_condition_exact": critic_zero_at_birth
        == (arm == "zero_critic"),
    }
    result = {
        "schema_version": 1,
        "arm": arm,
        "replicate": replicate,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "updates": UPDATES,
        "environment_steps": EXPECTED_STEPS,
        "reward_mode": "forced_zero",
        "germ_mode": "blind",
        "config": asdict(config),
        "critic_zero_at_birth": critic_zero_at_birth,
        "history": history,
        "evaluations": evaluations,
        "final_evaluations": final_evaluations,
        "final_world_rows": final_world_rows,
        "episodes_completed": total_episodes,
        "unrewarded_environment_successes": latent_environment_successes,
        "initial_state_sha256": initial_state,
        "final_state_sha256": final_state,
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    _atomic_torch_save(
        checkpoint_path,
        {
            "schema_version": 1,
            "arm": arm,
            "replicate": replicate,
            "birth_seed": birth_seed,
            "training_seed": training_seed,
            "updates": UPDATES,
            "reward_mode": "forced_zero",
            "config": asdict(config),
            "germ": descendant.germ,
            "model_state_dict": descendant.model.state_dict(),
            "writer_state_dict": descendant.writer.state_dict(),
            "optimizer_state_dict": descendant.optimizer.state_dict(),
            "writer_optimizer_state_dict": (
                descendant.writer_optimizer.state_dict()
            ),
            "recurrent_hidden": descendant.recurrent_hidden,
            "previous_actions": descendant.previous_actions,
            "previous_rewards": descendant.previous_rewards,
        },
    )
    atomic_json(result_path, result, output_root)
    if not result["completed_cleanly"]:
        raise RuntimeError(f"{stem} failed completion gates: {gates}")
    return result


def _action_distribution(evaluation: Mapping[str, Any]) -> np.ndarray:
    counts = np.asarray(
        evaluation["early_action_counts_by_context"], dtype=np.float64
    ).sum(axis=0)
    if counts.sum() <= 0:
        raise ValueError("early action panel has no observations")
    return counts / counts.sum()


def _cell_summary(
    result: Mapping[str, Any], arm: str, history_limit: int = UPDATES
) -> dict[str, Any]:
    history = result["history"] if "history" in result else result["training"]["history"]
    history = history[:history_limit]
    evaluations = [
        row
        for row in result["evaluations"]
        if int(row["update"]) in (0, history_limit)
    ]
    by_key = {(row["action_mode"], int(row["update"])): row for row in evaluations}
    birth_fixed = by_key[("fixed_random", 0)]
    final_fixed = by_key[("fixed_random", history_limit)]
    birth_distribution = _action_distribution(birth_fixed)
    final_distribution = _action_distribution(final_fixed)
    final_deterministic = by_key[("deterministic", history_limit)]
    successes_key = (
        "cumulative_unrewarded_environment_successes"
        if "cumulative_unrewarded_environment_successes" in history[-1]
        else "cumulative_successes"
    )
    return {
        "arm": arm,
        "replicate": int(result["replicate"]),
        "birth_seed": int(result["birth_seed"]),
        "training_seed": int(result["training_seed"]),
        "entropy_update_1": float(history[0]["entropy"]),
        "entropy_final": float(history[-1]["entropy"]),
        "entropy_change": float(history[-1]["entropy"] - history[0]["entropy"]),
        "early_action_total_variation_from_birth": float(
            0.5 * np.abs(final_distribution - birth_distribution).sum()
        ),
        "early_action_distribution_birth": birth_distribution.tolist(),
        "early_action_distribution_final": final_distribution.tolist(),
        "unrewarded_environment_successes": int(history[-1][successes_key]),
        "final_successes": {
            "deterministic": int(final_deterministic["successes"]),
            "fixed_random": int(final_fixed["successes"]),
        },
        "final_chain": {
            "deterministic": final_deterministic["conditional_chain"],
            "fixed_random": final_fixed["conditional_chain"],
        },
    }


def _distribution(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.isfinite(array).all():
        raise ValueError("distribution requires finite values")
    return {
        "minimum": float(array.min()),
        "median": float(np.median(array)),
        "maximum": float(array.max()),
        "mean": float(array.mean()),
    }


def _arm_aggregate(
    arm: str, summaries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(summaries) != len(REGISTERED_REPLICATES):
        raise ValueError(f"arm {arm} does not contain four registered seeds")
    chain_totals: dict[str, list[dict[str, Any]]] = {}
    for mode in ACTION_MODES:
        chains = [row["final_chain"][mode] for row in summaries]
        order = [event["to"] for event in chains[0]]
        if any([event["to"] for event in chain] != order for chain in chains):
            raise ValueError(f"causal-chain order differs within arm {arm}")
        chain_totals[mode] = [
            {
                "from": chains[0][index]["from"],
                "to": chains[0][index]["to"],
                "reached": sum(int(chain[index]["reached"]) for chain in chains),
                "eligible": sum(int(chain[index]["eligible"]) for chain in chains),
            }
            for index in range(len(order))
        ]
    entropy_changes = [float(row["entropy_change"]) for row in summaries]
    action_tv = [
        float(row["early_action_total_variation_from_birth"])
        for row in summaries
    ]
    return {
        "arm": arm,
        "entropy_change": _distribution(entropy_changes),
        "absolute_entropy_change": _distribution(
            [abs(value) for value in entropy_changes]
        ),
        "early_action_total_variation": _distribution(action_tv),
        "unrewarded_environment_successes": sum(
            int(row["unrewarded_environment_successes"]) for row in summaries
        ),
        "final_successes": {
            mode: sum(int(row["final_successes"][mode]) for row in summaries)
            for mode in ACTION_MODES
        },
        "final_chain_totals": chain_totals,
    }


def _birth_evaluations(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        row["action_mode"]: row
        for row in result["evaluations"]
        if int(row["update"]) == 0
    }


def markdown_report(panel: Mapping[str, Any]) -> str:
    aggregates = panel["arm_aggregates"]
    summaries = panel["cell_summaries"]
    lines = [
        "# DoorKey zero-reward PPO null panel v1",
        "",
        "**Status:** `IMPLEMENTATION DIAGNOSTIC — NOT A TASK OR LAW TEST`  ",
        "**Received training reward:** `EXACTLY ZERO IN EVERY NEW CELL`  ",
        "**Carrier modes compared:** `NONE`",
        "",
        "## Bottom line",
        "",
        (
            "The existing normalized-PPO reference and three isolated update "
            "variants were compared over the first 20 updates of the same four "
            "birth/training seeds. The new variants received forcibly clamped "
            "zero reward for 983,040 total transitions."
        ),
        "",
        "Arm-level drift is descriptive; no post-outcome cutoff is applied.",
        "",
        "| Arm | Entropy change, mean [min, max] | Early-action TV, mean | Unrewarded environment goals | Final argmax / fixed goals |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in aggregates:
        entropy = row["entropy_change"]
        action_tv = row["early_action_total_variation"]
        lines.append(
            f"| `{row['arm']}` | {entropy['mean']:+.4f} "
            f"[{entropy['minimum']:+.4f}, {entropy['maximum']:+.4f}] | "
            f"{action_tv['mean']:.4f} | "
            f"{row['unrewarded_environment_successes']} | "
            f"{row['final_successes']['deterministic']} / "
            f"{row['final_successes']['fixed_random']} |"
        )
    lines.extend(
        [
            "",
            "## Raw seed drift",
            "",
            "| Arm | Seed | Entropy u1 -> u20 | Change | Early-action TV | Unrewarded goals |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summaries:
        lines.append(
            f"| `{row['arm']}` | {row['replicate']} | "
            f"{row['entropy_update_1']:.4f} -> {row['entropy_final']:.4f} | "
            f"{row['entropy_change']:+.4f} | "
            f"{row['early_action_total_variation_from_birth']:.4f} | "
            f"{row['unrewarded_environment_successes']} |"
        )
    lines.extend(["", "## Fixed-random chain totals at update 20", ""])
    lines.extend(
        [
            "| Arm | Explore | Find key | Retain key | Find door | Open door | Reach goal |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in aggregates:
        cells = " | ".join(
            f"{event['reached']}/{event['eligible']}"
            for event in row["final_chain_totals"]["fixed_random"]
        )
        lines.append(f"| `{row['arm']}` | {cells} |")
    lines.extend(["", "## Completion integrity", ""])
    for gate, passed in panel["completion_gates"].items():
        lines.append(f"- `{gate}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            (
                "The twelve new cells ran sequentially with one CPU thread in "
                f"`{panel['elapsed_new_training_seconds']:.3f}` seconds. Every "
                "writer remained dormant and every blind 64-byte carrier stayed "
                "birth-exact."
            ),
            "",
            "## Mechanistic reading boundary",
            "",
            (
                f"The smallest combined descriptive drift was in "
                f"`{panel['descriptive_drift_order'][0]['arm']}`. The complete "
                "ordering is retained in `panel.json`; it is a routing summary, "
                "not a significance claim."
            ),
            "",
            "This panel diagnoses optimizer behavior under absent signal. It does not establish task learning, a germ effect, heredity, or any numbered law.",
            "",
        ]
    )
    return "\n".join(lines)


def run_panel(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    output_root = external_root(args.external_root)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    reference_output = output_root / "outputs" / TERMINAL_REFERENCE_RUN
    reference_run = output_root / "runs" / TERMINAL_REFERENCE_RUN
    reference_study_path = reference_output / "study.json"
    reference_manifest_path = reference_run / "MANIFEST.json"
    reference_hashes_path = reference_output / "output_hashes.sha256"
    reference_replicate_paths = [
        reference_output / f"replicate_{spec['replicate']}.json"
        for spec in REGISTERED_REPLICATES
    ]
    input_paths = [
        workspace / "protocols/DOORKEY_ZERO_REWARD_NULL_PANEL_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_scout.py",
        workspace
        / "src/laws_confirmation/doorkey_feedback_terminal_multiseed.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_ppo_v2.py",
        workspace / "tests/test_doorkey_zero_reward_null.py",
        reference_study_path,
        reference_manifest_path,
        reference_hashes_path,
        *reference_replicate_paths,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    reference_gate = qualify_terminal_reference(
        reference_study_path,
        reference_manifest_path,
        reference_hashes_path,
        reference_replicate_paths,
    )
    if not reference_gate["passes"]:
        raise RuntimeError(
            f"terminal reference gate failed: {reference_gate['gates']}"
        )
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = FeedbackPPOConfig()
    disk = _disk_preflight(output_root, 512 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    cell_specs = [
        {
            "arm": arm,
            "replicate": spec["replicate"],
            "birth_seed": spec["birth_seed"],
            "training_seed": spec["training_seed"],
        }
        for arm in NEW_ARMS
        for spec in REGISTERED_REPLICATES
    ]
    if args.resume:
        if not output_dir.is_dir() or not run_dir.is_dir():
            raise FileNotFoundError("resumable run directories do not exist")
        if (run_dir / "COMPLETE").exists() or (run_dir / "FAILED").exists():
            raise RuntimeError("only an interrupted RUNNING panel may resume")
        manifest = json.loads(
            (run_dir / "MANIFEST.json").read_text(encoding="utf-8")
        )
        if manifest.get("input_sha256") != input_hashes:
            raise RuntimeError("frozen inputs changed; refusing resume")
        if manifest.get("cell_specs") != cell_specs:
            raise RuntimeError("registered null-panel cells changed; refusing resume")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        output_dir.mkdir(parents=True)
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "stage": "DoorKey zero-reward PPO null panel",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "external_root": str(output_root),
            "output_dir": str(output_dir),
            "input_sha256": input_hashes,
            "contract_digest": canonical_digest(
                {
                    "input_sha256": input_hashes,
                    "config": asdict(config),
                    "cell_specs": cell_specs,
                    "updates": UPDATES,
                    "reward_mode": "forced_zero",
                    "terminal_reference_digest": reference_gate[
                        "reference_digest"
                    ],
                }
            ),
            "repository_head": git_head(workspace),
            "config": asdict(config),
            "cell_specs": cell_specs,
            "updates": UPDATES,
            "workers": 1,
            "reward_mode": "forced_zero",
            "germ_mode": "blind",
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "terminal_reference_gate": reference_gate,
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
        {"status": "RUNNING", "updated_utc": utc_now(), "cell": 0},
        output_root,
    )

    def progress(row: Mapping[str, Any]) -> None:
        if int(row["update"]) % 5 == 0:
            status = {"status": "RUNNING", "updated_utc": utc_now(), **dict(row)}
            atomic_json(run_dir / "STATUS.json", status, output_root)
            print(
                f"{row['arm']} replicate {row['replicate']} "
                f"update {row['update']}/{UPDATES}",
                flush=True,
            )

    try:
        training_started = time.monotonic()
        new_results = [
            _train_cell(
                arm,
                spec,
                config,
                output_root,
                output_dir,
                progress,
            )
            for arm in NEW_ARMS
            for spec in REGISTERED_REPLICATES
        ]
        elapsed_training = time.monotonic() - training_started
        reference_results = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in reference_replicate_paths
        ]
        reference_by_seed = {
            int(row["replicate"]): row for row in reference_results
        }
        birth_evaluations_match = all(
            _birth_evaluations(result)
            == _birth_evaluations(reference_by_seed[int(result["replicate"])])
            for result in new_results
        )
        reference_summaries = [
            _cell_summary(result, "normalized_reference")
            for result in reference_results
        ]
        new_summaries = [
            _cell_summary(result, str(result["arm"])) for result in new_results
        ]
        summaries = [*reference_summaries, *new_summaries]
        aggregates = [
            _arm_aggregate(
                arm, [row for row in summaries if row["arm"] == arm]
            )
            for arm in ("normalized_reference", *NEW_ARMS)
        ]
        descriptive_order = sorted(
            (
                {
                    "arm": row["arm"],
                    "score": row["absolute_entropy_change"]["mean"]
                    + row["early_action_total_variation"]["mean"],
                    "mean_absolute_entropy_change": row[
                        "absolute_entropy_change"
                    ]["mean"],
                    "mean_early_action_total_variation": row[
                        "early_action_total_variation"
                    ]["mean"],
                }
                for row in aggregates
            ),
            key=lambda row: (row["score"], row["arm"]),
        )
        observed_specs = [
            {
                "arm": row["arm"],
                "replicate": row["replicate"],
                "birth_seed": row["birth_seed"],
                "training_seed": row["training_seed"],
            }
            for row in new_results
        ]
        completion_gates = {
            "terminal_reference_gate_passed": reference_gate["passes"],
            "twelve_registered_new_cells": observed_specs == cell_specs,
            "all_new_cells_complete_cleanly": all(
                row["completed_cleanly"] for row in new_results
            ),
            "all_new_cells_expected_transitions": all(
                row["environment_steps"] == EXPECTED_STEPS
                for row in new_results
            ),
            "all_new_received_rewards_exactly_zero": all(
                row["completion_gates"]["all_received_rewards_exactly_zero"]
                for row in new_results
            ),
            "birth_evaluations_match_reference_exactly": birth_evaluations_match,
            "four_complete_arm_summaries": len(aggregates) == 4,
        }
        panel = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "IMPLEMENTATION_DIAGNOSTIC",
            "config": asdict(config),
            "updates": UPDATES,
            "new_cell_specs": cell_specs,
            "cell_summaries": summaries,
            "arm_aggregates": aggregates,
            "descriptive_drift_order": descriptive_order,
            "elapsed_new_training_seconds": elapsed_training,
            "terminal_reference_gate": reference_gate,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(output_dir / "panel.json", panel, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(panel), output_root)
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "panel.json",
            output_dir / "audit.md",
            output_dir / "input_hashes.sha256",
        ]
        for spec in cell_specs:
            stem = f"{spec['arm']}_replicate_{spec['replicate']}"
            output_paths.extend(
                (
                    output_dir / f"{stem}.json",
                    output_dir / f"{stem}_checkpoint.pt",
                )
            )
        write_hash_manifest(
            output_paths, output_dir / "output_hashes.sha256", output_root
        )
        status = {
            "status": "COMPLETE" if panel["completed_cleanly"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "descriptive_drift_order": descriptive_order,
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        sentinel = "COMPLETE" if panel["completed_cleanly"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0 if panel["completed_cleanly"] else 1
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
    return run_panel(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
