"""Matched multi-seed replication of DoorKey phase-specific actor credit."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import math
import multiprocessing
import os
from pathlib import Path
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
    _deepest_reached,
    _disk_preflight,
    _read_hash_manifest,
)
from .doorkey_phase_value_credit import (
    ARMS,
    CHANNELS,
    RUN_ID as ANCHOR_RUN,
    _arm_summary,
    _evaluate,
    _finite_credit_history,
    _first_evaluation_reach,
    _module_birth_details,
    causal_credit_ppo_update,
    collect_causal_credit_rollout,
    make_causal_credit_descendant,
    rollout_semantics,
)
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import FeedbackPPOConfig
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


RUN_ID = "doorkey_phase_value_credit_multiseed_v1_attempt1"
ANCHOR_SPEC = {
    "replicate": 0,
    "birth_seed": 920_000,
    "training_seed": 930_000,
    "source": "immutable_anchor",
}
REGISTERED_REPLICATES = (
    {"replicate": 1, "birth_seed": 924_000, "training_seed": 934_000},
    {"replicate": 2, "birth_seed": 925_000, "training_seed": 935_000},
    {"replicate": 3, "birth_seed": 926_000, "training_seed": 936_000},
)
UPDATES = 100
EXPECTED_STEPS = 409_600
MAX_WORKERS = 3


def _expected_anchor_arm_specs() -> list[dict[str, Any]]:
    return [
        {
            "arm": arm,
            "birth_seed": ANCHOR_SPEC["birth_seed"],
            "training_seed": ANCHOR_SPEC["training_seed"],
            "updates": UPDATES,
        }
        for arm in ARMS
    ]


def _new_cell_specs() -> list[dict[str, int | str]]:
    return [
        {
            "replicate": int(spec["replicate"]),
            "arm": arm,
            "birth_seed": int(spec["birth_seed"]),
            "training_seed": int(spec["training_seed"]),
            "updates": UPDATES,
        }
        for spec in REGISTERED_REPLICATES
        for arm in ARMS
    ]


def qualify_anchor(
    scout_path: Path,
    manifest_path: Path,
    output_hashes_path: Path,
    arm_paths: Sequence[Path],
) -> dict[str, Any]:
    """Verify the immutable one-seed phase-credit scout and its inputs."""

    scout = json.loads(scout_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    arm_results = [
        json.loads(path.read_text(encoding="utf-8")) for path in arm_paths
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
    result_specs = [
        {
            "arm": row.get("arm"),
            "birth_seed": row.get("birth_seed"),
            "training_seed": row.get("training_seed"),
            "updates": row.get("updates"),
        }
        for row in arm_results
    ]
    scout_gates = scout.get("completion_gates", {})
    gates = {
        "anchor_run_id_exact": scout.get("run_id") == ANCHOR_RUN,
        "anchor_manifest_run_id_exact": manifest.get("run_id") == ANCHOR_RUN,
        "anchor_completed_cleanly": bool(scout.get("completed_cleanly")),
        "anchor_outcome_exact": scout.get("outcome_classification")
        == "PHASE_ACTOR_ADVANCED_DEEPEST_LINK",
        "all_anchor_completion_gates_passed": bool(scout_gates)
        and all(bool(value) for value in scout_gates.values()),
        "anchor_arm_specs_exact": scout.get("arm_specs")
        == _expected_anchor_arm_specs(),
        "anchor_arm_results_exact": result_specs == _expected_anchor_arm_specs(),
        "all_anchor_arm_results_complete": all(
            bool(row.get("completed_cleanly")) for row in arm_results
        ),
        "all_anchor_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "all_anchor_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
    }
    return {
        "gates": gates,
        "passes": all(gates.values()),
        "input_rows": input_rows,
        "output_rows": output_rows,
        "reference_digest": canonical_digest(scout),
    }


def _train_cell(
    spec: Mapping[str, Any],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    replicate = int(spec["replicate"])
    arm = str(spec["arm"])
    birth_seed = int(spec["birth_seed"])
    training_seed = int(spec["training_seed"])
    if arm not in ARMS:
        raise ValueError(f"unknown causal-credit arm: {arm}")
    stem = f"{arm}_replicate_{replicate}"
    result_path = output_dir / f"{stem}.json"
    checkpoint_path = output_dir / f"{stem}_checkpoint.pt"
    progress_path = output_dir / "progress" / f"{stem}.json"
    if result_path.is_file() != checkpoint_path.is_file():
        raise RuntimeError(f"partial resumable artifacts for {stem}")
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("replicate") != replicate
            or result.get("arm") != arm
            or result.get("birth_seed") != birth_seed
            or result.get("training_seed") != training_seed
            or result.get("updates") != UPDATES
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable result for {stem}")
        atomic_json(
            progress_path,
            {
                "status": "COMPLETE",
                "updated_utc": utc_now(),
                "replicate": replicate,
                "arm": arm,
                "update": UPDATES,
                "resumed": True,
            },
            output_root,
        )
        print(f"{stem} already complete; resuming after it", flush=True)
        return result

    atomic_json(
        progress_path,
        {
            "status": "STARTING",
            "updated_utc": utc_now(),
            "replicate": replicate,
            "arm": arm,
            "update": 0,
        },
        output_root,
    )
    descendant = make_causal_credit_descendant(config, birth_seed)
    initial_germ = descendant.learner.germ.copy()
    initial_state = _module_birth_details(descendant)
    evaluations: list[dict[str, Any]] = []
    for mode in ACTION_MODES:
        evaluation, _ = _evaluate(descendant, config, mode)
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
        if update % 5 == 0:
            atomic_json(
                progress_path,
                {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    "replicate": replicate,
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
        "replicate": replicate,
        "arm": arm,
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
            reloaded.get("replicate") == replicate
            and reloaded.get("arm") == arm
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
        "replicate": replicate,
        "arm": arm,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
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
    atomic_json(
        progress_path,
        {
            "status": "COMPLETE" if result["completed_cleanly"] else "FAILED_GATES",
            "updated_utc": utc_now(),
            "replicate": replicate,
            "arm": arm,
            "update": UPDATES,
            "cumulative_event_counts": cumulative_events,
            "training_goal_successes": total_successes,
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


def _result_summary(
    result: Mapping[str, Any], *, replicate: int, source: str
) -> dict[str, Any]:
    summary = _arm_summary(result)
    return {
        "replicate": replicate,
        "source": source,
        "birth_seed": int(result["birth_seed"]),
        "training_seed": int(result["training_seed"]),
        **summary,
        "completed_cleanly": bool(result["completed_cleanly"]),
    }


def _distribution(values: Sequence[float | int]) -> dict[str, float]:
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
    selected = [row for row in summaries if row["arm"] == arm]
    if len(selected) != 4:
        raise ValueError(f"arm {arm} must contain four seeds")
    chain_totals: dict[str, list[dict[str, Any]]] = {}
    for mode in ACTION_MODES:
        chains = [row["final_chain"][mode] for row in selected]
        order = [event["to"] for event in chains[0]]
        if any([event["to"] for event in chain] != order for chain in chains):
            raise ValueError(f"causal-chain order differs in arm {arm}")
        chain_totals[mode] = [
            {
                "from": chains[0][index]["from"],
                "to": chains[0][index]["to"],
                "reached": sum(int(chain[index]["reached"]) for chain in chains),
                "eligible": sum(int(chain[index]["eligible"]) for chain in chains),
            }
            for index in range(len(order))
        ]
    return {
        "arm": arm,
        "training_event_count_distributions": {
            channel: _distribution(
                [row["training_event_counts"][channel] for row in selected]
            )
            for channel in CHANNELS
        },
        "training_goal_success_distribution": _distribution(
            [row["training_goal_successes"] for row in selected]
        ),
        "final_success_distributions": {
            mode: _distribution(
                [row["final_successes"][mode] for row in selected]
            )
            for mode in ACTION_MODES
        },
        "seeds_with_training_goal": sum(
            int(row["training_goal_successes"] > 0) for row in selected
        ),
        "seeds_with_final_goal": {
            mode: sum(
                int(row["final_successes"][mode] > 0) for row in selected
            )
            for mode in ACTION_MODES
        },
        "deepest_reached_by_seed": {
            mode: [row["deepest_reached"][mode] for row in selected]
            for mode in ACTION_MODES
        },
        "final_chain_totals": chain_totals,
        "final_entropy_distribution": _distribution(
            [row["final_entropy"] for row in selected]
        ),
    }


def _event_reached(chain: Sequence[Mapping[str, Any]], event: str) -> int:
    return int(next(row for row in chain if row["to"] == event)["reached"])


def _paired_seed_summary(
    summaries: Sequence[Mapping[str, Any]], replicate: int
) -> dict[str, Any]:
    by_arm = {
        row["arm"]: row for row in summaries if int(row["replicate"]) == replicate
    }
    if set(by_arm) != set(ARMS):
        raise ValueError(f"replicate {replicate} lacks a complete arm set")
    phase = by_arm["phase_actor"]
    controls = [by_arm["guarded_terminal"], by_arm["aux_critic_only"]]
    event_order = [row["to"] for row in phase["final_chain"]["fixed_random"]]

    def rank(row: Mapping[str, Any], mode: str) -> int:
        deepest = row["deepest_reached"][mode]
        return event_order.index(deepest) if deepest in event_order else -1

    fixed_differences = []
    for event in event_order:
        phase_reached = _event_reached(
            phase["final_chain"]["fixed_random"], event
        )
        control_values = [
            _event_reached(control["final_chain"]["fixed_random"], event)
            for control in controls
        ]
        fixed_differences.append(
            {
                "event": event,
                "phase_actor_reached": phase_reached,
                "guarded_terminal_reached": control_values[0],
                "aux_critic_only_reached": control_values[1],
                "phase_minus_best_control": phase_reached - max(control_values),
            }
        )
    return {
        "replicate": replicate,
        "birth_seed": int(phase["birth_seed"]),
        "training_seed": int(phase["training_seed"]),
        "phase_deeper_than_both_controls": {
            mode: rank(phase, mode) > max(rank(control, mode) for control in controls)
            for mode in ACTION_MODES
        },
        "fixed_random_chain_differences": fixed_differences,
        "phase_minus_best_control_training_events": {
            channel: int(phase["training_event_counts"][channel])
            - max(int(control["training_event_counts"][channel]) for control in controls)
            for channel in CHANNELS
        },
        "phase_minus_best_control_training_goals": int(
            phase["training_goal_successes"]
        )
        - max(int(control["training_goal_successes"]) for control in controls),
        "phase_minus_best_control_final_goals": {
            mode: int(phase["final_successes"][mode])
            - max(int(control["final_successes"][mode]) for control in controls)
            for mode in ACTION_MODES
        },
    }


def _outcome_classification(
    paired: Sequence[Mapping[str, Any]],
) -> str:
    fixed_depth = sum(
        bool(row["phase_deeper_than_both_controls"]["fixed_random"])
        for row in paired
    )
    deterministic_depth = sum(
        bool(row["phase_deeper_than_both_controls"]["deterministic"])
        for row in paired
    )
    return (
        f"PHASE_DEEPER_FIXED_{fixed_depth}_OF_{len(paired)}"
        f"_ARGMAX_{deterministic_depth}_OF_{len(paired)}"
    )


def markdown_report(replication: Mapping[str, Any]) -> str:
    summaries = replication["cell_summaries"]
    paired = replication["paired_seed_summaries"]
    lines = [
        "# DoorKey phase-value causal-credit multi-seed replication v1",
        "",
        "**Status:** `DEVELOPMENT REPLICATION — NOT A LAW TEST`  ",
        f"**Outcome:** `{replication['outcome_classification']}`  ",
        "**Carrier:** unchanged, empty, blind 64-byte germ in all cells",
        "",
        "## Raw seed results",
        "",
        "| Seed | Arm | Training key / door / goal | Final fixed open / goal | Final argmax / fixed goals | Deepest fixed event |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in summaries:
        events = row["training_event_counts"]
        fixed = {event["to"]: event for event in row["final_chain"]["fixed_random"]}
        lines.append(
            f"| {row['replicate']} | `{row['arm']}` | "
            f"{events['key']} / {events['door']} / {events['goal']} | "
            f"{fixed['open_door']['reached']} / {fixed['reach_goal']['reached']} | "
            f"{row['final_successes']['deterministic']} / "
            f"{row['final_successes']['fixed_random']} | "
            f"`{row['deepest_reached']['fixed_random']}` |"
        )
    lines.extend(
        [
            "",
            "## Paired phase-actor advantage over the better control",
            "",
            "| Seed | Deeper fixed? | Door-open count difference | Goal count difference | Training-goal difference |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for row in paired:
        difference = {
            item["event"]: item["phase_minus_best_control"]
            for item in row["fixed_random_chain_differences"]
        }
        lines.append(
            f"| {row['replicate']} | "
            f"{row['phase_deeper_than_both_controls']['fixed_random']} | "
            f"{difference['open_door']:+d} | {difference['reach_goal']:+d} | "
            f"{row['phase_minus_best_control_training_goals']:+d} |"
        )
    lines.extend(["", "## Four-seed fixed-random chain totals", ""])
    lines.extend(
        [
            "| Arm | Explore | Find key | Retain key | Find door | Open door | Reach goal |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in replication["arm_aggregates"]:
        cells = " | ".join(
            f"{event['reached']}/{event['eligible']}"
            for event in row["final_chain_totals"]["fixed_random"]
        )
        lines.append(f"| `{row['arm']}` | {cells} |")
    lines.extend(["", "## Completion integrity", ""])
    for gate, passed in replication["completion_gates"].items():
        lines.append(f"- `{gate}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            (
                f"The nine new cells used {replication['total_new_transitions']:,} "
                f"transitions in {replication['elapsed_training_seconds']:.3f} "
                f"wall-clock seconds with at most {replication['max_workers']} "
                "one-thread workers."
            ),
            "",
            "## Interpretation boundary",
            "",
            (
                "Raw paired differences are descriptive and no behavioral "
                "threshold was used as a completion gate. This run tests "
                "within-life credit assignment, not heredity or any numbered law."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_replication(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if args.run_id != RUN_ID:
        raise ValueError(f"frozen run ID must be {RUN_ID}")
    output_root = external_root(args.external_root)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    anchor_output = output_root / "outputs" / ANCHOR_RUN
    anchor_run = output_root / "runs" / ANCHOR_RUN
    anchor_scout_path = anchor_output / "scout.json"
    anchor_manifest_path = anchor_run / "MANIFEST.json"
    anchor_hashes_path = anchor_output / "output_hashes.sha256"
    anchor_arm_paths = [anchor_output / f"{arm}.json" for arm in ARMS]
    input_paths = [
        workspace / "protocols/DOORKEY_PHASE_VALUE_CREDIT_MULTISEED_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_scout.py",
        workspace / "src/laws_confirmation/doorkey_phase_value_credit.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_phase_value_credit.py",
        workspace / "tests/test_doorkey_phase_value_multiseed.py",
        anchor_scout_path,
        anchor_manifest_path,
        anchor_hashes_path,
        *anchor_arm_paths,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    anchor_gate = qualify_anchor(
        anchor_scout_path,
        anchor_manifest_path,
        anchor_hashes_path,
        anchor_arm_paths,
    )
    if not anchor_gate["passes"]:
        raise RuntimeError(f"phase-credit anchor gate failed: {anchor_gate['gates']}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = FeedbackPPOConfig()
    disk = _disk_preflight(output_root, 512 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")
    cell_specs = _new_cell_specs()
    if args.resume:
        if not output_dir.is_dir() or not run_dir.is_dir():
            raise FileNotFoundError("resumable run directories do not exist")
        if (run_dir / "COMPLETE").exists() or (run_dir / "FAILED").exists():
            raise RuntimeError("only an interrupted RUNNING replication may resume")
        manifest = json.loads(
            (run_dir / "MANIFEST.json").read_text(encoding="utf-8")
        )
        if manifest.get("input_sha256") != input_hashes:
            raise RuntimeError("frozen inputs changed; refusing resume")
        if manifest.get("cell_specs") != cell_specs:
            raise RuntimeError("frozen cell specifications changed; refusing resume")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        output_dir.mkdir(parents=True)
        (output_dir / "progress").mkdir()
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "stage": "DoorKey phase-value causal-credit multi-seed replication",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "external_root": str(output_root),
            "output_dir": str(output_dir),
            "input_sha256": input_hashes,
            "contract_digest": canonical_digest(
                {
                    "input_sha256": input_hashes,
                    "config": asdict(config),
                    "anchor_spec": ANCHOR_SPEC,
                    "cell_specs": cell_specs,
                    "anchor_digest": anchor_gate["reference_digest"],
                    "max_workers": MAX_WORKERS,
                }
            ),
            "repository_head": git_head(workspace),
            "config": asdict(config),
            "anchor_spec": ANCHOR_SPEC,
            "cell_specs": cell_specs,
            "workers": MAX_WORKERS,
            "threads_per_worker": 1,
            "cpu_limit": MAX_WORKERS,
            "reward_mode": "terminal",
            "germ_mode": "blind",
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "anchor_gate": anchor_gate,
            "disk_preflight": disk,
            "environment": environment_manifest(),
        }
        atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    if not (output_dir / "progress").is_dir():
        (output_dir / "progress").mkdir()
    atomic_text(run_dir / "RUN.pid", f"{os.getpid()}\n", output_root)
    atomic_json(
        run_dir / "STATUS.json",
        {
            "status": "RUNNING",
            "updated_utc": utc_now(),
            "completed_cells": 0,
            "total_cells": len(cell_specs),
            "progress_dir": str(output_dir / "progress"),
        },
        output_root,
    )

    try:
        training_started = time.monotonic()
        results_by_key: dict[tuple[int, str], dict[str, Any]] = {}
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=MAX_WORKERS, mp_context=context
        ) as executor:
            future_specs = {
                executor.submit(
                    _worker_train_cell,
                    spec,
                    asdict(config),
                    str(output_root),
                    str(output_dir),
                ): spec
                for spec in cell_specs
            }
            for completed_count, future in enumerate(
                as_completed(future_specs), start=1
            ):
                spec = future_specs[future]
                result = future.result()
                key = (int(spec["replicate"]), str(spec["arm"]))
                results_by_key[key] = result
                atomic_json(
                    run_dir / "STATUS.json",
                    {
                        "status": "RUNNING",
                        "updated_utc": utc_now(),
                        "completed_cells": completed_count,
                        "total_cells": len(cell_specs),
                        "last_completed": {
                            "replicate": spec["replicate"],
                            "arm": spec["arm"],
                        },
                        "progress_dir": str(output_dir / "progress"),
                    },
                    output_root,
                )
        elapsed_training = time.monotonic() - training_started
        new_results = [
            results_by_key[(int(spec["replicate"]), str(spec["arm"]))]
            for spec in cell_specs
        ]
        anchor_results = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in anchor_arm_paths
        ]
        summaries = [
            _result_summary(result, replicate=0, source="immutable_anchor")
            for result in anchor_results
        ] + [
            _result_summary(
                result,
                replicate=int(result["replicate"]),
                source="new",
            )
            for result in new_results
        ]
        summaries.sort(key=lambda row: (int(row["replicate"]), ARMS.index(row["arm"])))
        birth_evaluations_match = True
        for replicate in range(4):
            cells = [row for row in [*anchor_results, *new_results] if int(row.get("replicate", 0)) == replicate]
            births = [
                {
                    evaluation["action_mode"]: evaluation
                    for evaluation in cell["evaluations"]
                    if int(evaluation["update"]) == 0
                }
                for cell in cells
            ]
            birth_evaluations_match &= len(births) == len(ARMS) and all(
                birth == births[0] for birth in births[1:]
            )
        aggregates = [_arm_aggregate(arm, summaries) for arm in ARMS]
        paired = [_paired_seed_summary(summaries, replicate) for replicate in range(4)]
        observed_specs = [
            {
                "replicate": result["replicate"],
                "arm": result["arm"],
                "birth_seed": result["birth_seed"],
                "training_seed": result["training_seed"],
                "updates": result["updates"],
            }
            for result in new_results
        ]
        progress_paths = [
            output_dir
            / "progress"
            / f"{spec['arm']}_replicate_{spec['replicate']}.json"
            for spec in cell_specs
        ]
        progress_complete = all(
            path.is_file()
            and json.loads(path.read_text(encoding="utf-8")).get("status")
            == "COMPLETE"
            for path in progress_paths
        )
        completion_gates = {
            "anchor_gate_passed": anchor_gate["passes"],
            "nine_registered_new_cells_exact": observed_specs == cell_specs,
            "all_new_cells_completed_cleanly": all(
                result["completed_cleanly"] for result in new_results
            ),
            "all_new_cells_expected_transitions": all(
                result["environment_steps"] == EXPECTED_STEPS
                for result in new_results
            ),
            "all_within_seed_birth_evaluations_exact": birth_evaluations_match,
            "all_progress_records_complete": progress_complete,
            "twelve_complete_cell_summaries": len(summaries) == 12,
            "worker_limit_respected": MAX_WORKERS <= 3,
            "all_writers_dormant": all(
                result["completion_gates"]["writer_unchanged"]
                for result in new_results
            ),
            "all_carriers_birth_exact": all(
                result["completion_gates"]["carrier_birth_exact"]
                for result in new_results
            ),
        }
        replication = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "DEVELOPMENT_REPLICATION",
            "config": asdict(config),
            "anchor_spec": ANCHOR_SPEC,
            "new_cell_specs": cell_specs,
            "cell_summaries": summaries,
            "arm_aggregates": aggregates,
            "paired_seed_summaries": paired,
            "outcome_classification": _outcome_classification(paired),
            "elapsed_training_seconds": elapsed_training,
            "total_new_transitions": len(cell_specs) * EXPECTED_STEPS,
            "max_workers": MAX_WORKERS,
            "anchor_gate": anchor_gate,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(output_dir / "replication.json", replication, output_root)
        atomic_text(
            output_dir / "audit.md", markdown_report(replication), output_root
        )
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "replication.json",
            output_dir / "audit.md",
            output_dir / "input_hashes.sha256",
            *progress_paths,
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
            "status": (
                "COMPLETE" if replication["completed_cleanly"] else "FAILED_GATES"
            ),
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "outcome_classification": replication["outcome_classification"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        sentinel = "COMPLETE" if replication["completed_cleanly"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0 if replication["completed_cleanly"] else 1
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
    return run_replication(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
