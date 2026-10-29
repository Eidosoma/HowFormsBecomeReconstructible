"""From-birth 200-update horizon extension for DoorKey feedback PPO v2."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import time
import traceback
from typing import Any, Mapping

import numpy as np
import torch

from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
    _causal_comparison,
    _classification,
    _deepest_reached,
    _disk_preflight,
    _finite_history,
    _read_hash_manifest,
    _without_world_rows,
)
from .doorkey_ppo_v2 import (
    FeedbackPPOConfig,
    evaluate_feedback_policy,
    feedback_learner_digests,
    make_empty_feedback_descendant,
    train_feedback_ppo,
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


PRIOR_SCOUT_RUN = "doorkey_feedback_shaped_scout_v1_attempt1"


def qualify_prior_scout(
    workspace: Path,
    prior_scout_path: Path,
    prior_manifest_path: Path,
    prior_hashes_path: Path,
) -> dict[str, Any]:
    prior = json.loads(prior_scout_path.read_text(encoding="utf-8"))
    manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
    source_rows: list[dict[str, Any]] = []
    for source_text, expected in manifest["input_sha256"].items():
        source = Path(source_text)
        try:
            in_workspace = source.resolve().is_relative_to(workspace.resolve())
        except OSError:
            in_workspace = False
        if not in_workspace:
            continue
        live = sha256_file(source) if source.is_file() else None
        source_rows.append(
            {
                "path": str(source),
                "prior_scout_sha256": expected,
                "live_sha256": live,
                "unchanged": live == expected,
            }
        )
    output_rows = _read_hash_manifest(prior_hashes_path)
    gates = {
        "prior_scout_completed_cleanly": bool(prior.get("completed_cleanly")),
        "prior_scout_run_id_exact": prior.get("run_id") == PRIOR_SCOUT_RUN,
        "all_prior_workspace_inputs_unchanged": bool(source_rows)
        and all(row["unchanged"] for row in source_rows),
        "all_prior_output_hashes_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
    }
    return {
        "workspace_input_rows": source_rows,
        "prior_output_rows": output_rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def markdown_report(extension: Mapping[str, Any]) -> str:
    final = extension["final_evaluations"]
    deterministic = final["deterministic"]
    fixed_random = final["fixed_random"]
    prior = extension["prior_final_evaluations"]
    history = extension["training"]["history"]
    first_successes = sum(row["episode_successes"] for row in history[:100])
    later_successes = sum(row["episode_successes"] for row in history[100:])
    lines = [
        "# DoorKey feedback-v2 shaped horizon extension v1",
        "",
        "**Status:** `DEVELOPMENT — NOT A SCIENTIFIC TEST`  ",
        f"**Causal-chain classification:** `{extension['causal_chain_classification']}`  ",
        f"**Exact update-100 replay:** `{'PASS' if extension['first_100_replay_pass'] else 'FAIL'}`  ",
        "**Carrier modes compared:** `NONE`",
        "",
        "## Bottom line",
        "",
        f"The from-birth run reproduced the immutable first 100 updates exactly, then trained to 200 updates ({extension['environment_steps']:,} transitions). Final completion was `{deterministic['successes']}/{deterministic['world_count']}` under argmax and `{fixed_random['successes']}/{fixed_random['world_count']}` under fixed common randomness, compared with `{prior['deterministic']['successes']}/{prior['deterministic']['world_count']}` and `{prior['fixed_random']['successes']}/{prior['fixed_random']['world_count']}` at update 100.",
        "",
        f"Stochastic training successes were `{first_successes}` in updates 1–100 and `{later_successes}` in updates 101–200. Final policy entropy was `{history[-1]['entropy']:.3f}`. Both estimators clear the old 50% engineering robustness line: `{extension['both_estimators_clear_robustness_line']}`.",
        "",
        "## Exact replay gates",
        "",
        "| Gate | Result |",
        "|---|---|",
    ]
    for gate, passed in extension["first_100_replay_gates"].items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "## Learning curve",
            "",
            "| Update | Environment steps | Deterministic | Fixed common-random |",
            "|---:|---:|---:|---:|",
        ]
    )
    by_mode = {
        mode: {
            row["update"]: row
            for row in extension["evaluations"]
            if row["action_mode"] == mode
        }
        for mode in ACTION_MODES
    }
    for update in sorted(set(by_mode["deterministic"]) & set(by_mode["fixed_random"])):
        det = by_mode["deterministic"][update]
        fixed = by_mode["fixed_random"][update]
        steps = (
            update
            * extension["config"]["num_envs"]
            * extension["config"]["rollout_steps"]
        )
        lines.append(
            f"| {update} | {steps:,} | {det['successes']}/{det['world_count']} ({det['success_rate']:.3f}) | {fixed['successes']}/{fixed['world_count']} ({fixed['success_rate']:.3f}) |"
        )
    lines.extend(
        [
            "",
            "## Update-100 to update-200 causal chain",
            "",
            "| Conditional link | u100 argmax | u200 argmax | u100 fixed | u200 fixed |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    prior_det = {row["to"]: row for row in prior["deterministic"]["conditional_chain"]}
    prior_fixed = {row["to"]: row for row in prior["fixed_random"]["conditional_chain"]}
    final_fixed = {row["to"]: row for row in fixed_random["conditional_chain"]}
    for row in deterministic["conditional_chain"]:
        old_det = prior_det[row["to"]]
        old_fixed = prior_fixed[row["to"]]
        new_fixed = final_fixed[row["to"]]
        lines.append(
            f"| `{row['from']} -> {row['to']}` | {old_det['reached']}/{old_det['eligible']} | {row['reached']}/{row['eligible']} | {old_fixed['reached']}/{old_fixed['eligible']} | {new_fixed['reached']}/{new_fixed['eligible']} |"
        )
    lines.extend(
        [
            "",
            "## Completion integrity",
            "",
        ]
    )
    for gate, passed in extension["completion_gates"].items():
        lines.append(f"- `{gate}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            f"Training took `{extension['elapsed_training_seconds']:.3f}` seconds on one CPU process/thread. Deepest reached events were `{extension['deepest_reached']['deterministic']}` under argmax and `{extension['deepest_reached']['fixed_random']}` under fixed randomness.",
            "",
            "## Interpretation boundary",
            "",
        ]
    )
    if not extension["first_100_replay_pass"]:
        lines.append(
            "The extension is uninterpretable because its first 100 updates did not exactly replay the immutable source run. Debug determinism before reading the later curve."
        )
    elif extension["both_estimators_clear_robustness_line"]:
        lines.append(
            "Longer shaped training yields a robust germ-blind baseline in this seed. Replicate from birth across frozen seeds, then test terminal-only credit assignment before introducing any germ arm."
        )
    elif fixed_random["success_rate"] > prior["fixed_random"]["success_rate"]:
        lines.append(
            "The shaped stochastic policy continued improving but is not yet robust in both estimators. The next decision should use the complete link curve and seed replication before adding a mechanism."
        )
    else:
        lines.append(
            "Extra horizon did not improve the primary stochastic completion rate. Use the plateaued conditional link to specify the next isolated optimization or subgoal/value intervention."
        )
    lines.extend(
        [
            "",
            "The germ remained birth-exact and blind, and the writer remained dormant. This extension supplies no evidence for a carrier effect, vertical renewal, a learning disposition, functional ontology, or any numbered law.",
            "",
        ]
    )
    return "\n".join(lines)


def run_extension(args: argparse.Namespace) -> int:
    started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    if args.updates != 200 or args.evaluation_every != 10:
        raise ValueError("frozen extension requires 200 updates and cadence 10")
    output_root = external_root(args.external_root)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(f"immutable run ID exists: {args.run_id}")
    run_dir.mkdir(parents=True)
    disk = _disk_preflight(output_root, 128 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    workspace = Path(__file__).resolve().parents[2]
    prior_scout_path = output_root / "outputs" / PRIOR_SCOUT_RUN / "scout.json"
    prior_manifest_path = output_root / "runs" / PRIOR_SCOUT_RUN / "MANIFEST.json"
    prior_hashes_path = output_root / "outputs" / PRIOR_SCOUT_RUN / "output_hashes.sha256"
    input_paths = [
        workspace / "protocols/DOORKEY_FEEDBACK_SHAPED_HORIZON_EXTENSION_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_scout.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_ppo_v2.py",
        workspace / "tests/test_doorkey_feedback_scout.py",
        workspace / "tests/test_doorkey_feedback_horizon.py",
        prior_scout_path,
        prior_manifest_path,
        prior_hashes_path,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    prior_gate = qualify_prior_scout(
        workspace, prior_scout_path, prior_manifest_path, prior_hashes_path
    )
    if not prior_gate["passes"]:
        raise RuntimeError(f"prior scout gate failed: {prior_gate['gates']}")
    prior = json.loads(prior_scout_path.read_text(encoding="utf-8"))
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = FeedbackPPOConfig()
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "DoorKey feedback-v2 shaped horizon extension",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "input_sha256": input_hashes,
        "contract_digest": canonical_digest(
            {
                "input_sha256": input_hashes,
                "config": asdict(config),
                "updates": args.updates,
                "evaluation_every": args.evaluation_every,
                "birth_seed": args.birth_seed,
                "training_seed": args.training_seed,
            }
        ),
        "repository_head": git_head(workspace),
        "config": asdict(config),
        "updates": args.updates,
        "evaluation_every": args.evaluation_every,
        "birth_seed": args.birth_seed,
        "training_seed": args.training_seed,
        "workers": 1,
        "scientific_futures_generated": 0,
        "carrier_effect_comparisons": 0,
        "germ_mode": "blind",
        "reward_mode": "stage_shaped",
        "disk_preflight": disk,
        "prior_scout_gate": prior_gate,
        "environment": environment_manifest(),
    }
    atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    atomic_json(
        run_dir / "STATUS.json",
        {"status": "RUNNING", "updated_utc": utc_now(), "update": 0},
        output_root,
    )
    try:
        descendant = make_empty_feedback_descendant(config, args.birth_seed)
        initial_germ = descendant.germ.copy()
        initial_state = feedback_learner_digests(descendant)
        evaluations: list[dict[str, Any]] = []
        for mode in ACTION_MODES:
            evaluation, _ = _without_world_rows(
                evaluate_feedback_policy(
                    descendant,
                    config,
                    germ_mode="blind",
                    feedback_reward_mode="stage_shaped",
                    action_mode=mode,
                    worlds_per_transform=8,
                    stochastic_repeats=4,
                )
            )
            evaluation["update"] = 0
            evaluations.append(evaluation)
        update_100_state: dict[str, str] | None = None

        def progress(row: Mapping[str, Any]) -> None:
            nonlocal update_100_state
            if row["update"] == 100:
                update_100_state = feedback_learner_digests(descendant)
            if row["update"] % 5 == 0 or row["update"] == args.updates:
                latest = {
                    item["action_mode"]: item
                    for item in row.get("latest_evaluations", [])
                }
                status = {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    **dict(row),
                    "update_100_state_captured": update_100_state is not None,
                }
                atomic_json(run_dir / "STATUS.json", status, output_root)
                suffix = ""
                if latest:
                    det = latest["deterministic"]
                    fixed = latest["fixed_random"]
                    suffix = (
                        f" det={det['successes']}/{det['world_count']}"
                        f" fixed={fixed['successes']}/{fixed['world_count']}"
                    )
                print(
                    f"stage_shaped_v2 update {row['update']}/{row['updates']}"
                    f" steps={row['environment_steps']}{suffix}",
                    flush=True,
                )

        training_started = time.monotonic()
        training = train_feedback_ppo(
            descendant,
            config,
            updates=args.updates,
            training_seed=args.training_seed,
            reward_mode="stage_shaped",
            germ_mode="blind",
            evaluation_every=args.evaluation_every,
            evaluation_worlds_per_transform=8,
            stochastic_evaluation_repeats=4,
            progress_callback=progress,
        )
        elapsed_training = time.monotonic() - training_started
        evaluations.extend(training["evaluations"])
        final_evaluations: dict[str, Any] = {}
        final_world_rows: dict[str, Any] = {}
        for mode in ACTION_MODES:
            evaluation, rows = _without_world_rows(
                evaluate_feedback_policy(
                    descendant,
                    config,
                    germ_mode="blind",
                    feedback_reward_mode="stage_shaped",
                    action_mode=mode,
                    worlds_per_transform=8,
                    stochastic_repeats=4,
                )
            )
            final_evaluations[mode] = evaluation
            final_world_rows[mode] = rows
        final_state = feedback_learner_digests(descendant)

        prior_training = prior["training"]
        current_through_100 = [
            row for row in training["evaluations"] if row["update"] <= 100
        ]
        prior_initial = [row for row in prior["evaluations"] if row["update"] == 0]
        current_initial = [row for row in evaluations if row["update"] == 0]
        update_100_evaluation_gates: dict[str, bool] = {}
        for mode in ACTION_MODES:
            current_rows = [
                row
                for row in training["evaluations"]
                if row["update"] == 100 and row["action_mode"] == mode
            ]
            expected = dict(prior["final_evaluations"][mode])
            expected["update"] = 100
            update_100_evaluation_gates[mode] = (
                len(current_rows) == 1 and current_rows[0] == expected
            )
        replay_gates = {
            "birth_state_exact": initial_state == prior["initial_state_sha256"],
            "birth_evaluations_exact": current_initial == prior_initial,
            "history_rows_1_through_100_exact": training["history"][:100]
            == prior_training["history"],
            "scheduled_evaluations_through_100_exact": current_through_100
            == prior_training["evaluations"],
            "update_100_state_exact": update_100_state
            == prior["final_state_sha256"],
            "update_100_deterministic_summary_exact": update_100_evaluation_gates[
                "deterministic"
            ],
            "update_100_fixed_random_summary_exact": update_100_evaluation_gates[
                "fixed_random"
            ],
        }
        final_replay = True
        for mode in ACTION_MODES:
            rows = [
                row
                for row in training["evaluations"]
                if row["update"] == args.updates and row["action_mode"] == mode
            ]
            expected = dict(final_evaluations[mode])
            expected["update"] = args.updates
            final_replay &= len(rows) == 1 and rows[0] == expected
        evaluation_counts = {
            mode: sum(row["action_mode"] == mode for row in evaluations)
            for mode in ACTION_MODES
        }
        completion_gates = {
            "prior_scout_gate_passed": prior_gate["passes"],
            "first_100_replay_passed": all(replay_gates.values()),
            "all_training_metrics_finite": _finite_history(training["history"]),
            "expected_environment_steps": training["environment_steps"] == 819_200,
            "all_scheduled_evaluations_present": all(
                evaluation_counts[mode] == 21 for mode in ACTION_MODES
            ),
            "final_summaries_replay_exactly": final_replay,
            "actor_critic_changed_after_update_100": update_100_state is not None
            and update_100_state["actor_critic"] != final_state["actor_critic"],
            "dormant_writer_unchanged": initial_state["writer"]
            == final_state["writer"],
            "carrier_remains_birth_exact": bool(
                np.array_equal(descendant.germ, initial_germ)
            ),
        }
        deterministic = final_evaluations["deterministic"]
        fixed_random = final_evaluations["fixed_random"]
        extension = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "DEVELOPMENT",
            "config": asdict(config),
            "updates": args.updates,
            "environment_steps": training["environment_steps"],
            "evaluation_every": args.evaluation_every,
            "birth_seed": args.birth_seed,
            "training_seed": args.training_seed,
            "germ_mode": "blind",
            "reward_mode": "stage_shaped",
            "training": training,
            "evaluations": evaluations,
            "final_evaluations": final_evaluations,
            "final_world_rows": final_world_rows,
            "prior_final_evaluations": prior["final_evaluations"],
            "update_100_state_sha256": update_100_state,
            "final_state_sha256": final_state,
            "elapsed_training_seconds": elapsed_training,
            "first_100_replay_gates": replay_gates,
            "first_100_replay_pass": all(replay_gates.values()),
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "causal_chain_classification": _classification(
                deterministic["successes"], fixed_random["successes"]
            ),
            "deepest_reached": {
                mode: _deepest_reached(final_evaluations[mode]["conditional_chain"])
                for mode in ACTION_MODES
            },
            "both_estimators_clear_robustness_line": (
                deterministic["success_rate"] >= 0.5
                and fixed_random["success_rate"] >= 0.5
            ),
            "update_100_to_200_chain_comparison": {
                mode: _causal_comparison(
                    prior["final_evaluations"][mode]["conditional_chain"],
                    final_evaluations[mode]["conditional_chain"],
                )
                for mode in ACTION_MODES
            },
            "prior_scout_gate": prior_gate,
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        output_dir.mkdir(parents=True)
        checkpoint_path = output_dir / "stage_shaped_v2_u200_checkpoint.pt"
        _atomic_torch_save(
            checkpoint_path,
            {
                "schema_version": 1,
                "config": asdict(config),
                "birth_seed": args.birth_seed,
                "training_seed": args.training_seed,
                "updates": args.updates,
                "germ": descendant.germ,
                "model_state_dict": descendant.model.state_dict(),
                "writer_state_dict": descendant.writer.state_dict(),
                "optimizer_state_dict": descendant.optimizer.state_dict(),
                "writer_optimizer_state_dict": descendant.writer_optimizer.state_dict(),
                "recurrent_hidden": descendant.recurrent_hidden,
                "previous_actions": descendant.previous_actions,
                "previous_rewards": descendant.previous_rewards,
            },
        )
        atomic_json(output_dir / "extension.json", extension, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(extension), output_root)
        atomic_text(
            output_dir / "history.jsonl",
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in training["history"]
            ),
            output_root,
        )
        atomic_text(
            output_dir / "evaluations.jsonl",
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in evaluations
            ),
            output_root,
        )
        flat_rows = [
            {"action_mode": mode, **row}
            for mode in ACTION_MODES
            for row in final_world_rows[mode]
        ]
        atomic_text(
            output_dir / "final_world_rows.jsonl",
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in flat_rows
            ),
            output_root,
        )
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "extension.json",
            output_dir / "audit.md",
            output_dir / "history.jsonl",
            output_dir / "evaluations.jsonl",
            output_dir / "final_world_rows.jsonl",
            checkpoint_path,
            output_dir / "input_hashes.sha256",
        ]
        write_hash_manifest(
            output_paths, output_dir / "output_hashes.sha256", output_root
        )
        status = {
            "status": "COMPLETE" if extension["completed_cleanly"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
            "first_100_replay_pass": extension["first_100_replay_pass"],
            "causal_chain_classification": extension[
                "causal_chain_classification"
            ],
            "deterministic_success_rate": deterministic["success_rate"],
            "fixed_random_success_rate": fixed_random["success_rate"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        sentinel = "COMPLETE" if extension["completed_cleanly"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0 if extension["completed_cleanly"] else 1
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
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
    parser.add_argument("--updates", type=int, default=200)
    parser.add_argument("--evaluation-every", type=int, default=10)
    parser.add_argument("--birth-seed", type=int, default=920_000)
    parser.add_argument("--training-seed", type=int, default=930_000)
    return parser


def main() -> int:
    return run_extension(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
