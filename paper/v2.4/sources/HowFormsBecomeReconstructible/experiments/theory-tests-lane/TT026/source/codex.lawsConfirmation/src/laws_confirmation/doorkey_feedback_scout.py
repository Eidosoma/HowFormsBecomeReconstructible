"""Stage-shaped, germ-blind learning scout for DoorKey feedback PPO v2."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch

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


QUALIFICATION_RUN = "doorkey_action_reward_feedback_qualification_v1_attempt1"
V1_SCOUT_RUN = "doorkey_germ_blind_learning_scout_v1_attempt1"
ACTION_MODES = ("deterministic", "fixed_random")


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


def _read_hash_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        expected, target_text = line.split("  ", 1)
        target = Path(target_text)
        live = sha256_file(target) if target.is_file() else None
        rows.append(
            {
                "path": str(target),
                "expected_sha256": expected,
                "live_sha256": live,
                "matches": live == expected,
            }
        )
    return rows


def qualify_frozen_inputs(
    workspace: Path,
    qualification_path: Path,
    qualification_manifest_path: Path,
    qualification_hashes_path: Path,
) -> dict[str, Any]:
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    manifest = json.loads(qualification_manifest_path.read_text(encoding="utf-8"))
    recorded = manifest["input_sha256"]
    sources = (
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_qualification.py",
        workspace / "tests/test_doorkey_ppo_v2.py",
    )
    source_rows = []
    for source in sources:
        resolved = str(source.resolve())
        live = sha256_file(source)
        expected = recorded.get(resolved)
        source_rows.append(
            {
                "path": resolved,
                "qualification_sha256": expected,
                "live_sha256": live,
                "unchanged": expected is not None and live == expected,
            }
        )
    output_rows = _read_hash_manifest(qualification_hashes_path)
    gates = {
        "qualification_passed": bool(qualification.get("overall_pass")),
        "qualification_run_id_exact": qualification.get("run_id")
        == QUALIFICATION_RUN,
        "qualified_sources_unchanged": all(row["unchanged"] for row in source_rows),
        "qualification_output_hashes_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
    }
    return {
        "source_rows": source_rows,
        "qualification_output_rows": output_rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def _classification(
    deterministic_successes: int, fixed_random_successes: int
) -> str:
    deterministic = deterministic_successes > 0
    fixed_random = fixed_random_successes > 0
    if deterministic and fixed_random:
        return "CHAIN_COMPLETION_BOTH_MODES"
    if deterministic:
        return "CHAIN_COMPLETION_DETERMINISTIC_ONLY"
    if fixed_random:
        return "CHAIN_COMPLETION_FIXED_RANDOM_ONLY"
    return "NO_CHAIN_COMPLETION"


def _causal_comparison(
    v1_chain: Sequence[Mapping[str, Any]],
    v2_chain: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if [row["to"] for row in v1_chain] != [row["to"] for row in v2_chain]:
        raise ValueError("causal-chain event order differs between v1 and v2")
    return [
        {
            "from": newer["from"],
            "to": newer["to"],
            "v1_reached": older["reached"],
            "v1_eligible": older["eligible"],
            "v1_conditional_probability": older["conditional_probability"],
            "v2_reached": newer["reached"],
            "v2_eligible": newer["eligible"],
            "v2_conditional_probability": newer["conditional_probability"],
            "reached_count_difference": newer["reached"] - older["reached"],
            "conditional_probability_difference": (
                None
                if older["conditional_probability"] is None
                or newer["conditional_probability"] is None
                else newer["conditional_probability"]
                - older["conditional_probability"]
            ),
        }
        for older, newer in zip(v1_chain, v2_chain)
    ]


def _deepest_reached(chain: Sequence[Mapping[str, Any]]) -> str | None:
    reached = [row["to"] for row in chain if row["reached"] > 0]
    return reached[-1] if reached else None


def _finite_history(history: Sequence[Mapping[str, Any]]) -> bool:
    names = (
        "mean_rollout_reward",
        "max_rollout_reward",
        "policy_loss",
        "value_loss",
        "entropy",
        "approx_kl",
        "clip_fraction",
        "grad_norm",
    )
    return all(math.isfinite(float(row[name])) for row in history for name in names)


def _without_world_rows(evaluation: dict[str, Any]) -> tuple[dict[str, Any], list[Any]]:
    rows = evaluation.pop("world_rows")
    return evaluation, rows


def markdown_report(scout: Mapping[str, Any]) -> str:
    deterministic = scout["final_evaluations"]["deterministic"]
    fixed_random = scout["final_evaluations"]["fixed_random"]
    v1 = scout["v1_shaped_final_evaluation"]
    lines = [
        "# DoorKey feedback-v2 shaped germ-blind scout v1",
        "",
        "**Status:** `DEVELOPMENT — NOT A SCIENTIFIC TEST`  ",
        f"**Causal-chain classification:** `{scout['causal_chain_classification']}`  ",
        "**Carrier modes compared:** `NONE`",
        "",
        "## Bottom line",
        "",
        f"After {scout['updates']} updates ({scout['environment_steps']:,} transitions), the v2 learner completed `{deterministic['successes']}/{deterministic['world_count']}` deterministic trajectories and `{fixed_random['successes']}/{fixed_random['world_count']}` fixed-random trajectories. The latter are four common action streams over each of 32 layouts, not 128 independent layout samples.",
        "",
        f"The deepest reached event was `{scout['deepest_reached']['deterministic']}` under argmax and `{scout['deepest_reached']['fixed_random']}` under fixed randomness. Both final rates clear the old 50% engineering robustness line: `{scout['both_estimators_clear_robustness_line']}`. The complete chain below is the primary result.",
        "",
        "This scout changes only somatic action/reward feedback. The germ was empty and blind, the writer stayed dormant, and no carrier comparison or scientific future was generated.",
        "",
        "## Learning curve",
        "",
        "| Update | Environment steps | Deterministic | Fixed common-random |",
        "|---:|---:|---:|---:|",
    ]
    evaluations = scout["evaluations"]
    by_mode = {
        mode: {row["update"]: row for row in evaluations if row["action_mode"] == mode}
        for mode in ACTION_MODES
    }
    for update in sorted(set(by_mode["deterministic"]) & set(by_mode["fixed_random"])):
        det = by_mode["deterministic"][update]
        fixed = by_mode["fixed_random"][update]
        steps = update * scout["config"]["num_envs"] * scout["config"]["rollout_steps"]
        lines.append(
            f"| {update} | {steps:,} | {det['successes']}/{det['world_count']} ({det['success_rate']:.3f}) | {fixed['successes']}/{fixed['world_count']} ({fixed['success_rate']:.3f}) |"
        )
    lines.extend(
        [
            "",
            "## Final causal chain",
            "",
            "| Conditional link | v1 shaped argmax | v2 argmax | v2 fixed random |",
            "|---|---:|---:|---:|",
        ]
    )
    fixed_by_event = {row["to"]: row for row in fixed_random["conditional_chain"]}
    v1_by_event = {row["to"]: row for row in v1["conditional_chain"]}
    for row in deterministic["conditional_chain"]:
        old = v1_by_event[row["to"]]
        fixed = fixed_by_event[row["to"]]
        lines.append(
            f"| `{row['from']} -> {row['to']}` | {old['reached']}/{old['eligible']} | {row['reached']}/{row['eligible']} | {fixed['reached']}/{fixed['eligible']} |"
        )
    lines.extend(
        [
            "",
            "## Exact v1-to-v2 deterministic differences",
            "",
            "| Event | Reached count delta | Conditional probability delta |",
            "|---|---:|---:|",
        ]
    )
    for row in scout["v1_to_v2_deterministic_comparison"]:
        probability_delta = row["conditional_probability_difference"]
        formatted = "NA" if probability_delta is None else f"{probability_delta:+.3f}"
        lines.append(
            f"| `{row['to']}` | {row['reached_count_difference']:+d} | {formatted} |"
        )
    training = scout["training"]
    lines.extend(
        [
            "",
            "## Training and integrity",
            "",
            f"Stochastic training completed `{training['episodes_completed']}` episodes with `{training['episode_successes']}` successes. Training took `{scout['elapsed_training_seconds']:.3f}` seconds on one CPU process/thread. The final writer hash equals its birth hash: `{scout['completion_gates']['dormant_writer_unchanged']}`. Scheduled and separately repeated final summaries were exact in both evaluation modes: `{scout['completion_gates']['final_summaries_replay_exactly']}`. All output hashes were written after the run.",
            "",
            "## Interpretation boundary",
            "",
        ]
    )
    classification = scout["causal_chain_classification"]
    if classification == "CHAIN_COMPLETION_BOTH_MODES":
        lines.append(
            "Explicit action/reward feedback repaired enough of the representation for complete chains to appear under both estimators in this seed. The next step is a frozen multi-seed replication of this positive control, followed by a terminal-only v2 scout. A carrier arm is still premature."
        )
    elif classification == "CHAIN_COMPLETION_FIXED_RANDOM_ONLY":
        lines.append(
            "The stochastic policy can complete the chain, but its argmax policy cannot. Diagnose action-probability concentration at the deepest divergent link and replicate before changing credit assignment."
        )
    elif classification == "CHAIN_COMPLETION_DETERMINISTIC_ONLY":
        lines.append(
            "Argmax completed the chain but fixed-random behavior did not, suggesting a brittle or sharply concentrated policy that needs replay and seed replication before further mechanism work."
        )
    else:
        lines.append(
            "Neither estimator completed the chain. Use the deepest conditional failure—not a germ-writing threshold—to choose the next isolated representation, exploration, or optimization intervention."
        )
    lines.extend(
        [
            "",
            "No outcome here supports inherited action shaping, learned germ writing, vertical renewal, a learning disposition, functional ontology, or any numbered law.",
            "",
        ]
    )
    return "\n".join(lines)


def run_scout(args: argparse.Namespace) -> int:
    started = time.monotonic()
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
    qualification_path = (
        output_root / "outputs" / QUALIFICATION_RUN / "qualification.json"
    )
    qualification_manifest_path = (
        output_root / "runs" / QUALIFICATION_RUN / "MANIFEST.json"
    )
    qualification_hashes_path = (
        output_root / "outputs" / QUALIFICATION_RUN / "output_hashes.sha256"
    )
    v1_scout_path = output_root / "outputs" / V1_SCOUT_RUN / "scout.json"
    input_paths = [
        workspace / "protocols/DOORKEY_FEEDBACK_SHAPED_SCOUT_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_qualification.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_ppo_v2.py",
        workspace / "tests/test_doorkey_feedback_scout.py",
        qualification_path,
        qualification_manifest_path,
        qualification_hashes_path,
        v1_scout_path,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    frozen_inputs = qualify_frozen_inputs(
        workspace,
        qualification_path,
        qualification_manifest_path,
        qualification_hashes_path,
    )
    if not frozen_inputs["passes"]:
        raise RuntimeError(f"frozen input gate failed: {frozen_inputs['gates']}")
    v1_scout = json.loads(v1_scout_path.read_text(encoding="utf-8"))
    v1_final = v1_scout["arms"]["stage_shaped"]["final_evaluation"]
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = FeedbackPPOConfig()
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "DoorKey feedback-v2 shaped germ-blind scout",
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
                "evaluation_worlds_per_transform": args.evaluation_worlds_per_transform,
                "stochastic_evaluation_repeats": args.stochastic_evaluation_repeats,
                "birth_seed": args.birth_seed,
                "training_seed": args.training_seed,
            }
        ),
        "repository_head": git_head(workspace),
        "config": asdict(config),
        "updates": args.updates,
        "evaluation_every": args.evaluation_every,
        "evaluation_worlds_per_transform": args.evaluation_worlds_per_transform,
        "stochastic_evaluation_repeats": args.stochastic_evaluation_repeats,
        "birth_seed": args.birth_seed,
        "training_seed": args.training_seed,
        "workers": 1,
        "scientific_futures_generated": 0,
        "carrier_effect_comparisons": 0,
        "germ_mode": "blind",
        "reward_mode": "stage_shaped",
        "disk_preflight": disk,
        "frozen_input_gate": frozen_inputs,
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
            initial, _ = _without_world_rows(
                evaluate_feedback_policy(
                    descendant,
                    config,
                    germ_mode="blind",
                    feedback_reward_mode="stage_shaped",
                    action_mode=mode,
                    worlds_per_transform=args.evaluation_worlds_per_transform,
                    stochastic_repeats=args.stochastic_evaluation_repeats,
                )
            )
            initial["update"] = 0
            evaluations.append(initial)

        def progress(row: Mapping[str, Any]) -> None:
            if row["update"] % 5 == 0 or row["update"] == args.updates:
                latest = {
                    item["action_mode"]: item
                    for item in row.get("latest_evaluations", [])
                }
                status = {
                    "status": "RUNNING",
                    "updated_utc": utc_now(),
                    **dict(row),
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
            evaluation_worlds_per_transform=args.evaluation_worlds_per_transform,
            stochastic_evaluation_repeats=args.stochastic_evaluation_repeats,
            progress_callback=progress,
        )
        elapsed_training = time.monotonic() - training_started
        evaluations.extend(training["evaluations"])
        final_evaluations: dict[str, Any] = {}
        final_world_rows: dict[str, Any] = {}
        for mode in ACTION_MODES:
            final, rows = _without_world_rows(
                evaluate_feedback_policy(
                    descendant,
                    config,
                    germ_mode="blind",
                    feedback_reward_mode="stage_shaped",
                    action_mode=mode,
                    worlds_per_transform=args.evaluation_worlds_per_transform,
                    stochastic_repeats=args.stochastic_evaluation_repeats,
                )
            )
            final_evaluations[mode] = final
            final_world_rows[mode] = rows
        final_state = feedback_learner_digests(descendant)
        final_summaries_replay = True
        for mode in ACTION_MODES:
            scheduled = [
                row
                for row in training["evaluations"]
                if row["update"] == args.updates and row["action_mode"] == mode
            ]
            expected = dict(final_evaluations[mode])
            expected["update"] = args.updates
            final_summaries_replay &= len(scheduled) == 1 and scheduled[0] == expected
        evaluation_counts = {
            mode: sum(row["action_mode"] == mode for row in evaluations)
            for mode in ACTION_MODES
        }
        completion_gates = {
            "all_training_metrics_finite": _finite_history(training["history"]),
            "expected_environment_steps": training["environment_steps"]
            == args.updates * config.num_envs * config.rollout_steps,
            "all_scheduled_evaluations_present": all(
                evaluation_counts[mode] == args.updates // args.evaluation_every + 1
                for mode in ACTION_MODES
            ),
            "final_summaries_replay_exactly": final_summaries_replay,
            "actor_critic_changed": initial_state["actor_critic"]
            != final_state["actor_critic"],
            "dormant_writer_unchanged": initial_state["writer"]
            == final_state["writer"],
            "carrier_remains_birth_exact": bool(
                np.array_equal(descendant.germ, initial_germ)
            ),
        }
        deterministic = final_evaluations["deterministic"]
        fixed_random = final_evaluations["fixed_random"]
        classification = _classification(
            deterministic["successes"], fixed_random["successes"]
        )
        scout = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "DEVELOPMENT",
            "config": asdict(config),
            "updates": args.updates,
            "environment_steps": training["environment_steps"],
            "evaluation_every": args.evaluation_every,
            "evaluation_worlds_per_transform": args.evaluation_worlds_per_transform,
            "stochastic_evaluation_repeats": args.stochastic_evaluation_repeats,
            "birth_seed": args.birth_seed,
            "training_seed": args.training_seed,
            "germ_mode": "blind",
            "reward_mode": "stage_shaped",
            "training": training,
            "evaluations": evaluations,
            "final_evaluations": final_evaluations,
            "final_world_rows": final_world_rows,
            "initial_state_sha256": initial_state,
            "final_state_sha256": final_state,
            "elapsed_training_seconds": elapsed_training,
            "causal_chain_classification": classification,
            "deepest_reached": {
                mode: _deepest_reached(final_evaluations[mode]["conditional_chain"])
                for mode in ACTION_MODES
            },
            "both_estimators_clear_robustness_line": (
                deterministic["success_rate"] >= 0.5
                and fixed_random["success_rate"] >= 0.5
            ),
            "v1_shaped_final_evaluation": v1_final,
            "v1_to_v2_deterministic_comparison": _causal_comparison(
                v1_final["conditional_chain"], deterministic["conditional_chain"]
            ),
            "frozen_input_gate": frozen_inputs,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        output_dir.mkdir(parents=True)
        checkpoint_path = output_dir / "stage_shaped_v2_checkpoint.pt"
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
        atomic_json(output_dir / "scout.json", scout, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(scout), output_root)
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
        flat_world_rows = [
            {"action_mode": mode, **row}
            for mode in ACTION_MODES
            for row in final_world_rows[mode]
        ]
        atomic_text(
            output_dir / "final_world_rows.jsonl",
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in flat_world_rows
            ),
            output_root,
        )
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "scout.json",
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
            "status": "COMPLETE" if scout["completed_cleanly"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
            "causal_chain_classification": classification,
            "deterministic_success_rate": deterministic["success_rate"],
            "fixed_random_success_rate": fixed_random["success_rate"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        sentinel = "COMPLETE" if scout["completed_cleanly"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0 if scout["completed_cleanly"] else 1
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
    parser.add_argument("--updates", type=int, default=100)
    parser.add_argument("--evaluation-every", type=int, default=10)
    parser.add_argument("--evaluation-worlds-per-transform", type=int, default=8)
    parser.add_argument("--stochastic-evaluation-repeats", type=int, default=4)
    parser.add_argument("--birth-seed", type=int, default=920_000)
    parser.add_argument("--training-seed", type=int, default=930_000)
    return parser


def main() -> int:
    return run_scout(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
