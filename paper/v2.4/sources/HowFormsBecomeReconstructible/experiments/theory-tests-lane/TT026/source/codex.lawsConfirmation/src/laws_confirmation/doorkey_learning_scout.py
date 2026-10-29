"""Paired germ-blind DoorKey PPO learning scout (development only)."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import traceback
from typing import Any, Mapping

import numpy as np
import torch

from .doorkey_ppo import (
    PPOConfig,
    evaluate_policy,
    learner_state_digests,
    make_empty_ppo_descendant,
    train_ppo,
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


ARMS = ("terminal", "stage_shaped")


def _atomic_torch_save(path: Path, value: Any) -> None:
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    try:
        torch.save(value, temporary)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _disk_preflight(root: Path, estimate: int) -> dict[str, Any]:
    usage = shutil.disk_usage(root)
    margin = 1024**3
    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "estimated_output_bytes": estimate,
        "required_free_margin_bytes": margin,
        "preflight_pass": usage.free >= estimate + margin,
    }


def _classification(terminal_rate: float, shaped_rate: float) -> str:
    terminal_learns = terminal_rate >= 0.5
    shaped_learns = shaped_rate >= 0.5
    if terminal_learns and shaped_learns:
        return "BOTH_CLEAR_DEVELOPMENT_THRESHOLD"
    if shaped_learns:
        return "SHAPED_ONLY_CREDIT_ASSIGNMENT_CANDIDATE"
    if terminal_learns:
        return "TERMINAL_ONLY_UNEXPECTED"
    return "NEITHER_CLEARS_DEVELOPMENT_THRESHOLD"


def markdown_report(scout: Mapping[str, Any]) -> str:
    arms = scout["arms"]
    terminal = arms["terminal"]
    shaped = arms["stage_shaped"]
    lines = [
        "# DoorKey germ-blind PPO learning scout v1",
        "",
        "**Status:** `DEVELOPMENT — NOT A SCIENTIFIC TEST`  ",
        f"**Diagnostic classification:** `{scout['diagnostic_classification']}`  ",
        "**Carrier modes compared:** `NONE`",
        "",
        "## Bottom line",
        "",
        f"Two identically initialized recurrent PPO learners used the same seeded training-schedule rule and exactly common evaluation worlds. One received terminal goal reward only; the other received the declared one-time stage rewards. After {scout['updates_per_arm']} updates ({scout['environment_steps_per_arm']:,} transitions per arm), deterministic common-world success was `{terminal['final_evaluation']['successes']}/{terminal['final_evaluation']['world_count']}` terminal-only and `{shaped['final_evaluation']['successes']}/{shaped['final_evaluation']['world_count']}` stage-shaped.",
        "",
        "This is a debugging learning curve. It estimates neither a germ effect nor vertical heredity. Its 50% diagnostic line is a routing rule for the next engineering intervention, not a confirmatory threshold.",
        "",
        "## Deterministic common-world curve",
        "",
        "| Update | Environment steps | Terminal success | Stage-shaped success |",
        "|---:|---:|---:|---:|",
    ]
    terminal_by_update = {
        row["update"]: row for row in terminal["evaluations"]
    }
    shaped_by_update = {row["update"]: row for row in shaped["evaluations"]}
    for update in sorted(set(terminal_by_update) & set(shaped_by_update)):
        terminal_row = terminal_by_update[update]
        shaped_row = shaped_by_update[update]
        steps = update * scout["config"]["num_envs"] * scout["config"]["rollout_steps"]
        lines.append(
            f"| {update} | {steps:,} | {terminal_row['successes']}/{terminal_row['world_count']} ({terminal_row['success_rate']:.3f}) | {shaped_row['successes']}/{shaped_row['world_count']} ({shaped_row['success_rate']:.3f}) |"
        )
    lines.extend(
        [
            "",
            "## Final causal chain",
            "",
            "| Conditional link | Terminal reached/eligible | Stage-shaped reached/eligible |",
            "|---|---:|---:|",
        ]
    )
    for terminal_row, shaped_row in zip(
        terminal["final_evaluation"]["conditional_chain"],
        shaped["final_evaluation"]["conditional_chain"],
    ):
        lines.append(
            f"| `{terminal_row['from']} -> {terminal_row['to']}` | {terminal_row['reached']}/{terminal_row['eligible']} | {shaped_row['reached']}/{shaped_row['eligible']} |"
        )
    lines.extend(
        [
            "",
            "## Training diagnostics",
            "",
            "| Arm | Completed episodes | Stochastic training successes | Wall seconds | Final model SHA-256 |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for arm in ARMS:
        result = arms[arm]
        lines.append(
            f"| `{arm}` | {result['training']['episodes_completed']} | {result['training']['episode_successes']} | {result['elapsed_seconds']:.3f} | `{result['training']['model_sha256']}` |"
        )
    lines.extend(
        [
            "",
            f"Total scout wall time was `{scout['elapsed_training_seconds']:.3f}` seconds using one CPU process/thread. Initial actor/critic hashes were identical across arms: `{scout['initial_actor_critic_identical']}`. Evaluation worlds and seeds were identical. Each checkpoint, history row, evaluation row, and final per-world event row is retained externally.",
            "",
            "## Interpretation boundary",
            "",
        ]
    )
    classification = scout["diagnostic_classification"]
    if classification == "SHAPED_ONLY_CREDIT_ASSIGNMENT_CANDIDATE":
        lines.append(
            "The shaped positive control clears the developmental line while terminal PPO does not. This localizes the next coding work toward credit assignment: add separate key/door/goal value heads without changing the policy reward or the 64-byte germ, then rerun a fresh development scout. It does not yet show that such heads fix the problem."
        )
    elif classification == "BOTH_CLEAR_DEVELOPMENT_THRESHOLD":
        lines.append(
            "Both arms clear the developmental line. The terminal learner is adequate for the first direct-prior integration scout; extra value heads are not yet justified."
        )
    elif classification == "NEITHER_CLEARS_DEVELOPMENT_THRESHOLD":
        lines.append(
            "Even the shaped positive control misses the developmental line. The next work must diagnose representation, recurrent optimization, and exploration before introducing any germ mechanism; a carrier comparison at this floor would be uninterpretable."
        )
    else:
        lines.append(
            "Only terminal reward clears the line, an unexpected pattern requiring exact replay and reward-path review before any carrier work."
        )
    lines.extend(
        [
            "",
            "No outcome here supports inherited action shaping, learned germ writing, renewal across real trained generations, a learning disposition, functional ontology, or any numbered law.",
            "",
        ]
    )
    return "\n".join(lines)


def run_scout(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    if args.updates < 1 or args.evaluation_every < 1:
        raise ValueError("updates and evaluation cadence must be positive")
    if args.updates % args.evaluation_every:
        raise ValueError("evaluation cadence must divide updates")
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
    qualification = output_root / "outputs" / (
        "doorkey_vertical_stage_b_learner_qualification_v1_attempt1"
    ) / "qualification.json"
    qualification_payload = json.loads(qualification.read_text(encoding="utf-8"))
    if not qualification_payload.get("overall_pass"):
        raise RuntimeError("Stage-B qualification did not pass")
    input_paths = [
        workspace / "protocols/DOORKEY_GERM_BLIND_LEARNING_SCOUT_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_ppo.py",
        qualification,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = PPOConfig()
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "DoorKey germ-blind paired learning scout",
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
        "updates_per_arm": args.updates,
        "evaluation_every": args.evaluation_every,
        "birth_seed": args.birth_seed,
        "training_seed": args.training_seed,
        "workers": 1,
        "scientific_futures_generated": 0,
        "carrier_effect_comparisons": 0,
        "germ_mode": "blind",
        "disk_preflight": disk,
        "environment": environment_manifest(),
    }
    atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    atomic_json(
        run_dir / "STATUS.json",
        {"status": "RUNNING", "updated_utc": utc_now(), "arm": None, "update": 0},
        output_root,
    )
    try:
        arms: dict[str, Any] = {}
        checkpoint_payloads: dict[str, Any] = {}
        initial_hashes: dict[str, dict[str, str]] = {}
        elapsed_training = 0.0
        for arm in ARMS:
            descendant = make_empty_ppo_descendant(config, args.birth_seed)
            initial_hashes[arm] = learner_state_digests(descendant)
            initial_evaluation = evaluate_policy(
                descendant,
                config,
                germ_mode="blind",
                worlds_per_transform=args.evaluation_worlds_per_transform,
            )
            initial_evaluation.pop("world_rows")
            initial_evaluation["update"] = 0

            def progress(row: Mapping[str, Any], *, current_arm: str = arm) -> None:
                if row["update"] % 5 == 0 or row["update"] == args.updates:
                    status = {
                        "status": "RUNNING",
                        "updated_utc": utc_now(),
                        "arm": current_arm,
                        **dict(row),
                    }
                    atomic_json(run_dir / "STATUS.json", status, output_root)
                    latest = row.get("latest_evaluation")
                    suffix = ""
                    if latest is not None:
                        suffix = (
                            f" eval={latest['successes']}/{latest['world_count']}"
                        )
                    print(
                        f"{current_arm} update {row['update']}/{row['updates']}"
                        f" steps={row['environment_steps']}{suffix}",
                        flush=True,
                    )

            arm_started = time.monotonic()
            training = train_ppo(
                descendant,
                config,
                updates=args.updates,
                training_seed=args.training_seed,
                reward_mode=arm,
                germ_mode="blind",
                evaluation_every=args.evaluation_every,
                evaluation_worlds_per_transform=args.evaluation_worlds_per_transform,
                progress_callback=progress,
            )
            arm_elapsed = time.monotonic() - arm_started
            elapsed_training += arm_elapsed
            final_evaluation = evaluate_policy(
                descendant,
                config,
                germ_mode="blind",
                worlds_per_transform=args.evaluation_worlds_per_transform,
            )
            final_rows = final_evaluation.pop("world_rows")
            evaluations = [initial_evaluation, *training["evaluations"]]
            arms[arm] = {
                "elapsed_seconds": arm_elapsed,
                "training": training,
                "evaluations": evaluations,
                "final_evaluation": final_evaluation,
                "final_world_rows": final_rows,
                "learner_state_sha256": learner_state_digests(descendant),
            }
            checkpoint_payloads[arm] = {
                "schema_version": 1,
                "arm": arm,
                "config": asdict(config),
                "birth_seed": args.birth_seed,
                "training_seed": args.training_seed,
                "updates": args.updates,
                "germ": descendant.germ,
                "model_state_dict": descendant.model.state_dict(),
                "writer_state_dict": descendant.writer.state_dict(),
                "optimizer_state_dict": descendant.optimizer.state_dict(),
                "writer_optimizer_state_dict": descendant.writer_optimizer.state_dict(),
            }

        terminal_rate = arms["terminal"]["final_evaluation"]["success_rate"]
        shaped_rate = arms["stage_shaped"]["final_evaluation"]["success_rate"]
        scout = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "DEVELOPMENT",
            "config": asdict(config),
            "updates_per_arm": args.updates,
            "environment_steps_per_arm": (
                args.updates * config.num_envs * config.rollout_steps
            ),
            "evaluation_every": args.evaluation_every,
            "development_success_threshold": 0.5,
            "diagnostic_classification": _classification(
                terminal_rate, shaped_rate
            ),
            "initial_actor_critic_identical": (
                initial_hashes["terminal"]["actor_critic"]
                == initial_hashes["stage_shaped"]["actor_critic"]
            ),
            "elapsed_training_seconds": elapsed_training,
            "arms": arms,
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "scout.json", scout, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(scout), output_root)
        history_rows = [
            {"arm": arm, **row}
            for arm in ARMS
            for row in arms[arm]["training"]["history"]
        ]
        evaluation_rows = [
            {"arm": arm, **row}
            for arm in ARMS
            for row in arms[arm]["evaluations"]
        ]
        final_world_rows = [
            {"arm": arm, **row}
            for arm in ARMS
            for row in arms[arm]["final_world_rows"]
        ]
        for filename, rows in (
            ("history.jsonl", history_rows),
            ("evaluations.jsonl", evaluation_rows),
            ("final_world_rows.jsonl", final_world_rows),
        ):
            atomic_text(
                output_dir / filename,
                "".join(
                    json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                    for row in rows
                ),
                output_root,
            )
        checkpoint_paths = []
        for arm, payload in checkpoint_payloads.items():
            path = output_dir / f"{arm}_checkpoint.pt"
            _atomic_torch_save(path, payload)
            checkpoint_paths.append(path)
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "scout.json",
            output_dir / "audit.md",
            output_dir / "history.jsonl",
            output_dir / "evaluations.jsonl",
            output_dir / "final_world_rows.jsonl",
            output_dir / "input_hashes.sha256",
            *checkpoint_paths,
        ]
        write_hash_manifest(
            output_paths, output_dir / "output_hashes.sha256", output_root
        )
        status = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "diagnostic_classification": scout["diagnostic_classification"],
            "terminal_final_success_rate": terminal_rate,
            "stage_shaped_final_success_rate": shaped_rate,
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        atomic_text(run_dir / "COMPLETE", status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
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
    parser.add_argument("--updates", type=int, default=100)
    parser.add_argument("--evaluation-every", type=int, default=10)
    parser.add_argument("--evaluation-worlds-per-transform", type=int, default=8)
    parser.add_argument("--birth-seed", type=int, default=900_000)
    parser.add_argument("--training-seed", type=int, default=910_000)
    return parser


def main() -> int:
    return run_scout(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
