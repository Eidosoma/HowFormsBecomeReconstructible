"""Sequential, resumable shaped multi-seed study for DoorKey feedback PPO."""

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
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
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


ANCHOR_RUN = "doorkey_feedback_shaped_horizon_extension_v1_attempt1"
REGISTERED_REPLICATES = (
    {"replicate": 1, "birth_seed": 921_000, "training_seed": 931_000},
    {"replicate": 2, "birth_seed": 922_000, "training_seed": 932_000},
    {"replicate": 3, "birth_seed": 923_000, "training_seed": 933_000},
)


def qualify_anchor(
    workspace: Path,
    anchor_path: Path,
    anchor_manifest_path: Path,
    anchor_hashes_path: Path,
) -> dict[str, Any]:
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    manifest = json.loads(anchor_manifest_path.read_text(encoding="utf-8"))
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
                "anchor_sha256": expected,
                "live_sha256": live,
                "unchanged": live == expected,
            }
        )
    output_rows = _read_hash_manifest(anchor_hashes_path)
    gates = {
        "anchor_completed_cleanly": bool(anchor.get("completed_cleanly")),
        "anchor_run_id_exact": anchor.get("run_id") == ANCHOR_RUN,
        "anchor_first_100_replay_passed": bool(anchor.get("first_100_replay_pass")),
        "all_anchor_workspace_inputs_unchanged": bool(source_rows)
        and all(row["unchanged"] for row in source_rows),
        "all_anchor_output_hashes_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
    }
    return {
        "workspace_input_rows": source_rows,
        "anchor_output_rows": output_rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def _first_completion_update(
    evaluations: Sequence[Mapping[str, Any]], action_mode: str
) -> int | None:
    completed = [
        int(row["update"])
        for row in evaluations
        if row["action_mode"] == action_mode and int(row["successes"]) > 0
    ]
    return min(completed) if completed else None


def _replicate_summary(result: Mapping[str, Any], source: str) -> dict[str, Any]:
    final = result["final_evaluations"]
    history = result["training"]["history"]
    return {
        "replicate": result["replicate"],
        "source": source,
        "birth_seed": result["birth_seed"],
        "training_seed": result["training_seed"],
        "deterministic_successes": final["deterministic"]["successes"],
        "deterministic_world_count": final["deterministic"]["world_count"],
        "deterministic_success_rate": final["deterministic"]["success_rate"],
        "fixed_random_successes": final["fixed_random"]["successes"],
        "fixed_random_world_count": final["fixed_random"]["world_count"],
        "fixed_random_success_rate": final["fixed_random"]["success_rate"],
        "classification": _classification(
            final["deterministic"]["successes"],
            final["fixed_random"]["successes"],
        ),
        "first_completion_update": {
            mode: _first_completion_update(result["evaluations"], mode)
            for mode in ACTION_MODES
        },
        "deepest_reached": {
            mode: _deepest_reached(final[mode]["conditional_chain"])
            for mode in ACTION_MODES
        },
        "training_episodes": result["training"]["episodes_completed"],
        "training_successes": result["training"]["episode_successes"],
        "final_entropy": history[-1]["entropy"],
        "final_chain": {
            mode: final[mode]["conditional_chain"] for mode in ACTION_MODES
        },
        "completed_cleanly": result["completed_cleanly"],
    }


def _distribution(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "minimum": float(array.min()),
        "median": float(np.median(array)),
        "maximum": float(array.max()),
        "mean": float(array.mean()),
    }


def _aggregate_classification(summaries: Sequence[Mapping[str, Any]]) -> str:
    both = sum(row["classification"] == "CHAIN_COMPLETION_BOTH_MODES" for row in summaries)
    if both == len(summaries):
        return "ALL_SEEDS_COMPLETE_BOTH_MODES"
    any_completion = any(
        row["classification"] != "NO_CHAIN_COMPLETION" for row in summaries
    )
    if any_completion:
        return "MIXED_SEED_CHAIN_COMPLETION"
    return "NO_SEED_COMPLETES_CHAIN"


def _run_replicate(
    spec: Mapping[str, int],
    config: FeedbackPPOConfig,
    output_root: Path,
    output_dir: Path,
    run_dir: Path,
) -> dict[str, Any]:
    replicate = int(spec["replicate"])
    birth_seed = int(spec["birth_seed"])
    training_seed = int(spec["training_seed"])
    result_path = output_dir / f"replicate_{replicate}.json"
    checkpoint_path = output_dir / f"replicate_{replicate}_checkpoint.pt"
    if result_path.is_file() and checkpoint_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("replicate") != replicate
            or result.get("birth_seed") != birth_seed
            or result.get("training_seed") != training_seed
            or not result.get("completed_cleanly")
        ):
            raise RuntimeError(f"invalid resumable replicate {replicate}")
        print(f"replicate {replicate} already complete; resuming after it", flush=True)
        return result

    descendant = make_empty_feedback_descendant(config, birth_seed)
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

    def progress(row: Mapping[str, Any]) -> None:
        if row["update"] % 5 == 0 or row["update"] == 200:
            latest = {
                item["action_mode"]: item
                for item in row.get("latest_evaluations", [])
            }
            status = {
                "status": "RUNNING",
                "updated_utc": utc_now(),
                "replicate": replicate,
                "birth_seed": birth_seed,
                "training_seed": training_seed,
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
                f"replicate {replicate} update {row['update']}/200"
                f" steps={row['environment_steps']}{suffix}",
                flush=True,
            )

    started = time.monotonic()
    training = train_feedback_ppo(
        descendant,
        config,
        updates=200,
        training_seed=training_seed,
        reward_mode="stage_shaped",
        germ_mode="blind",
        evaluation_every=10,
        evaluation_worlds_per_transform=8,
        stochastic_evaluation_repeats=4,
        progress_callback=progress,
    )
    elapsed = time.monotonic() - started
    evaluations.extend(training["evaluations"])
    final_evaluations: dict[str, Any] = {}
    final_world_rows: dict[str, Any] = {}
    final_replay = True
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
        scheduled = [
            row
            for row in training["evaluations"]
            if row["update"] == 200 and row["action_mode"] == mode
        ]
        expected = dict(evaluation)
        expected["update"] = 200
        final_replay &= len(scheduled) == 1 and scheduled[0] == expected
    final_state = feedback_learner_digests(descendant)
    counts = {
        mode: sum(row["action_mode"] == mode for row in evaluations)
        for mode in ACTION_MODES
    }
    gates = {
        "all_training_metrics_finite": _finite_history(training["history"]),
        "expected_environment_steps": training["environment_steps"] == 819_200,
        "all_scheduled_evaluations_present": all(
            counts[mode] == 21 for mode in ACTION_MODES
        ),
        "final_summaries_replay_exactly": final_replay,
        "actor_critic_changed": initial_state["actor_critic"]
        != final_state["actor_critic"],
        "dormant_writer_unchanged": initial_state["writer"]
        == final_state["writer"],
        "carrier_remains_birth_exact": bool(
            np.array_equal(descendant.germ, initial_germ)
        ),
    }
    result = {
        "schema_version": 1,
        "replicate": replicate,
        "birth_seed": birth_seed,
        "training_seed": training_seed,
        "config": asdict(config),
        "updates": 200,
        "environment_steps": training["environment_steps"],
        "germ_mode": "blind",
        "reward_mode": "stage_shaped",
        "training": training,
        "evaluations": evaluations,
        "final_evaluations": final_evaluations,
        "final_world_rows": final_world_rows,
        "initial_state_sha256": initial_state,
        "final_state_sha256": final_state,
        "elapsed_training_seconds": elapsed,
        "completion_gates": gates,
        "completed_cleanly": all(gates.values()),
    }
    _atomic_torch_save(
        checkpoint_path,
        {
            "schema_version": 1,
            "replicate": replicate,
            "config": asdict(config),
            "birth_seed": birth_seed,
            "training_seed": training_seed,
            "updates": 200,
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
    atomic_json(result_path, result, output_root)
    if not result["completed_cleanly"]:
        raise RuntimeError(f"replicate {replicate} failed completion gates: {gates}")
    return result


def markdown_report(batch: Mapping[str, Any]) -> str:
    summaries = batch["replicate_summaries"]
    distribution = batch["success_rate_distribution"]
    lines = [
        "# DoorKey feedback-v2 shaped multi-seed replication v1",
        "",
        "**Status:** `DEVELOPMENT — NOT A SCIENTIFIC TEST`  ",
        f"**Seed classification:** `{batch['seed_classification']}`  ",
        "**Carrier modes compared:** `NONE`",
        "",
        "## Bottom line",
        "",
        f"Four registered shaped, germ-blind feedback-v2 seeds each ran 200 updates. Final argmax success ranged from `{distribution['deterministic']['minimum']:.3f}` to `{distribution['deterministic']['maximum']:.3f}` with median `{distribution['deterministic']['median']:.3f}`. Fixed-common-random success ranged from `{distribution['fixed_random']['minimum']:.3f}` to `{distribution['fixed_random']['maximum']:.3f}` with median `{distribution['fixed_random']['median']:.3f}`.",
        "",
        f"Complete chains occurred under both estimators in `{batch['seeds_completing_both_modes']}/4` seeds. The old 50% engineering line was cleared by `{batch['seeds_clearing_robustness_line']['deterministic']}/4` argmax results and `{batch['seeds_clearing_robustness_line']['fixed_random']}/4` fixed-random results. These are routing summaries, not scientific thresholds.",
        "",
        "## Raw seed results",
        "",
        "| Replicate | Birth / training seed | Source | Argmax | Fixed random | First complete argmax / fixed | Training successes | Final entropy |",
        "|---:|---|---|---:|---:|---|---:|---:|",
    ]
    for row in summaries:
        first = row["first_completion_update"]
        lines.append(
            f"| {row['replicate']} | {row['birth_seed']} / {row['training_seed']} | {row['source']} | {row['deterministic_successes']}/{row['deterministic_world_count']} | {row['fixed_random_successes']}/{row['fixed_random_world_count']} | {first['deterministic']} / {first['fixed_random']} | {row['training_successes']} | {row['final_entropy']:.3f} |"
        )
    for mode, title in (
        ("deterministic", "Argmax final causal chains"),
        ("fixed_random", "Fixed-random final causal chains"),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Link | R0 | R1 | R2 | R3 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        chains = [row["final_chain"][mode] for row in summaries]
        for index, event in enumerate(chains[0]):
            values = " | ".join(
                f"{chain[index]['reached']}/{chain[index]['eligible']}"
                for chain in chains
            )
            lines.append(f"| `{event['from']} -> {event['to']}` | {values} |")
    lines.extend(
        [
            "",
            "## Completion integrity",
            "",
        ]
    )
    for gate, passed in batch["completion_gates"].items():
        lines.append(f"- `{gate}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            f"The three new seeds used one CPU process/thread sequentially and took `{batch['elapsed_new_training_seconds']:.3f}` training seconds in total. Every new carrier stayed byte-exact to birth, every writer stayed dormant, and no carrier comparison or scientific future ran.",
            "",
            "## Next boundary",
            "",
        ]
    )
    if batch["seed_classification"] == "ALL_SEEDS_COMPLETE_BOTH_MODES":
        lines.append(
            "Shaped full-chain competence generalizes across all four registered seeds. The next isolated question is terminal-only credit assignment with the same feedback learner; carrier arms remain later."
        )
    elif batch["seed_classification"] == "MIXED_SEED_CHAIN_COMPLETION":
        lines.append(
            "Shaped competence is seed-sensitive. Use the raw conditional links to decide whether more horizon or a targeted post-open intervention is needed before a terminal or carrier comparison."
        )
    else:
        lines.append(
            "The anchor did not replicate. Revisit the shaped learner at the shared failing link before any terminal-credit or carrier work."
        )
    lines.extend(
        [
            "",
            "This small development panel cannot establish inherited shaping, autonomous writing, vertical renewal, a learning disposition, functional ontology, or any numbered law.",
            "",
        ]
    )
    return "\n".join(lines)


def run_batch(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    output_root = external_root(args.external_root)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    anchor_path = output_root / "outputs" / ANCHOR_RUN / "extension.json"
    anchor_manifest_path = output_root / "runs" / ANCHOR_RUN / "MANIFEST.json"
    anchor_hashes_path = output_root / "outputs" / ANCHOR_RUN / "output_hashes.sha256"
    input_paths = [
        workspace / "protocols/DOORKEY_FEEDBACK_SHAPED_MULTISEED_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_scout.py",
        workspace / "src/laws_confirmation/doorkey_feedback_horizon.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_ppo_v2.py",
        workspace / "tests/test_doorkey_feedback_scout.py",
        workspace / "tests/test_doorkey_feedback_horizon.py",
        workspace / "tests/test_doorkey_feedback_multiseed.py",
        anchor_path,
        anchor_manifest_path,
        anchor_hashes_path,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    anchor_gate = qualify_anchor(
        workspace, anchor_path, anchor_manifest_path, anchor_hashes_path
    )
    if not anchor_gate["passes"]:
        raise RuntimeError(f"anchor gate failed: {anchor_gate['gates']}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = FeedbackPPOConfig()
    disk = _disk_preflight(output_root, 256 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if args.resume:
        if not output_dir.is_dir() or not run_dir.is_dir():
            raise FileNotFoundError("resumable run directories do not exist")
        if (run_dir / "COMPLETE").exists() or (run_dir / "FAILED").exists():
            raise RuntimeError("only an interrupted RUNNING batch may resume")
        manifest = json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        if manifest.get("input_sha256") != input_hashes:
            raise RuntimeError("frozen inputs changed; refusing resume")
        if manifest.get("replicates") != list(REGISTERED_REPLICATES):
            raise RuntimeError("registered replicate table changed; refusing resume")
    else:
        if output_dir.exists() or run_dir.exists():
            raise FileExistsError(f"immutable run ID exists: {args.run_id}")
        output_dir.mkdir(parents=True)
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "stage": "DoorKey feedback-v2 shaped multi-seed replication",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "external_root": str(output_root),
            "output_dir": str(output_dir),
            "input_sha256": input_hashes,
            "contract_digest": canonical_digest(
                {
                    "input_sha256": input_hashes,
                    "config": asdict(config),
                    "replicates": REGISTERED_REPLICATES,
                }
            ),
            "repository_head": git_head(workspace),
            "config": asdict(config),
            "replicates": list(REGISTERED_REPLICATES),
            "workers": 1,
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "germ_mode": "blind",
            "reward_mode": "stage_shaped",
            "disk_preflight": disk,
            "anchor_gate": anchor_gate,
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
        {"status": "RUNNING", "updated_utc": utc_now(), "replicate": 0},
        output_root,
    )
    try:
        results = [
            _run_replicate(spec, config, output_root, output_dir, run_dir)
            for spec in REGISTERED_REPLICATES
        ]
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor_normalized = {
            **anchor,
            "replicate": 0,
            "completed_cleanly": anchor["completed_cleanly"],
        }
        summaries = [
            _replicate_summary(anchor_normalized, "immutable_anchor"),
            *(_replicate_summary(result, "new") for result in results),
        ]
        det_rates = [row["deterministic_success_rate"] for row in summaries]
        fixed_rates = [row["fixed_random_success_rate"] for row in summaries]
        completion_gates = {
            "anchor_gate_passed": anchor_gate["passes"],
            "three_registered_new_replicates": [
                {
                    "replicate": row["replicate"],
                    "birth_seed": row["birth_seed"],
                    "training_seed": row["training_seed"],
                }
                for row in results
            ]
            == list(REGISTERED_REPLICATES),
            "all_new_replicates_complete_cleanly": all(
                row["completed_cleanly"] for row in results
            ),
            "all_new_replicates_819200_transitions": all(
                row["environment_steps"] == 819_200 for row in results
            ),
        }
        batch = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "DEVELOPMENT",
            "config": asdict(config),
            "registered_replicates": list(REGISTERED_REPLICATES),
            "replicate_summaries": summaries,
            "success_rate_distribution": {
                "deterministic": _distribution(det_rates),
                "fixed_random": _distribution(fixed_rates),
            },
            "seed_classification": _aggregate_classification(summaries),
            "seeds_completing_both_modes": sum(
                row["classification"] == "CHAIN_COMPLETION_BOTH_MODES"
                for row in summaries
            ),
            "seeds_clearing_robustness_line": {
                "deterministic": sum(value >= 0.5 for value in det_rates),
                "fixed_random": sum(value >= 0.5 for value in fixed_rates),
                "both": sum(
                    det >= 0.5 and fixed >= 0.5
                    for det, fixed in zip(det_rates, fixed_rates)
                ),
            },
            "elapsed_new_training_seconds": sum(
                row["elapsed_training_seconds"] for row in results
            ),
            "anchor_gate": anchor_gate,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(output_dir / "replication.json", batch, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(batch), output_root)
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "replication.json",
            output_dir / "audit.md",
            output_dir / "input_hashes.sha256",
        ]
        for spec in REGISTERED_REPLICATES:
            index = spec["replicate"]
            output_paths.extend(
                (
                    output_dir / f"replicate_{index}.json",
                    output_dir / f"replicate_{index}_checkpoint.pt",
                )
            )
        write_hash_manifest(
            output_paths, output_dir / "output_hashes.sha256", output_root
        )
        status = {
            "status": "COMPLETE" if batch["completed_cleanly"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - overall_started,
            "seed_classification": batch["seed_classification"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        sentinel = "COMPLETE" if batch["completed_cleanly"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0 if batch["completed_cleanly"] else 1
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
    return run_batch(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
