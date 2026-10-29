"""Paired terminal-only DoorKey study for the qualified feedback-v2 learner."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from .doorkey_feedback_multiseed import (
    _aggregate_classification,
    _distribution,
    _replicate_summary,
)
from .doorkey_feedback_scout import (
    ACTION_MODES,
    _atomic_torch_save,
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


SHAPED_REFERENCE_RUN = "doorkey_feedback_shaped_multiseed_v1_attempt1"
REGISTERED_REPLICATES = (
    {"replicate": 0, "birth_seed": 920_000, "training_seed": 930_000},
    {"replicate": 1, "birth_seed": 921_000, "training_seed": 931_000},
    {"replicate": 2, "birth_seed": 922_000, "training_seed": 932_000},
    {"replicate": 3, "birth_seed": 923_000, "training_seed": 933_000},
)
UPDATES = 200
EXPECTED_STEPS = 819_200


def qualify_shaped_reference(
    replication_path: Path,
    manifest_path: Path,
    output_hashes_path: Path,
) -> dict[str, Any]:
    """Verify the complete frozen shaped study used as the positive control."""

    replication = json.loads(replication_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
    summary_specs = [
        {
            "replicate": int(row["replicate"]),
            "birth_seed": int(row["birth_seed"]),
            "training_seed": int(row["training_seed"]),
        }
        for row in replication.get("replicate_summaries", [])
    ]
    gates = {
        "shaped_run_id_exact": replication.get("run_id")
        == SHAPED_REFERENCE_RUN,
        "shaped_manifest_run_id_exact": manifest.get("run_id")
        == SHAPED_REFERENCE_RUN,
        "shaped_completed_cleanly": bool(replication.get("completed_cleanly")),
        "shaped_all_seeds_complete_both_modes": replication.get(
            "seed_classification"
        )
        == "ALL_SEEDS_COMPLETE_BOTH_MODES",
        "shaped_seed_table_exact": summary_specs == list(REGISTERED_REPLICATES),
        "all_shaped_inputs_verify": bool(input_rows)
        and all(row["matches"] for row in input_rows),
        "all_shaped_outputs_verify": bool(output_rows)
        and all(row["matches"] for row in output_rows),
    }
    return {
        "gates": gates,
        "passes": all(gates.values()),
        "input_rows": input_rows,
        "output_rows": output_rows,
        "reference_digest": canonical_digest(replication),
    }


def credit_routing_classification(
    summaries: Sequence[Mapping[str, Any]],
) -> str:
    """Classify outcomes descriptively without imposing a pass threshold."""

    if not summaries:
        raise ValueError("at least one terminal summary is required")
    both = sum(
        row["classification"] == "CHAIN_COMPLETION_BOTH_MODES"
        for row in summaries
    )
    any_chain = any(
        row["classification"] != "NO_CHAIN_COMPLETION" for row in summaries
    )
    observed_rewards = sum(int(row["training_successes"]) for row in summaries)
    if both == len(summaries):
        return "TERMINAL_CHAIN_ALL_SEEDS"
    if any_chain:
        return "TERMINAL_CHAIN_SEED_SENSITIVE"
    if observed_rewards > 0:
        return "TERMINAL_REWARD_OBSERVED_NO_EVALUATION_CHAIN"
    return "NO_TERMINAL_REWARD_OBSERVED"


def paired_seed_summary(
    terminal: Mapping[str, Any], shaped: Mapping[str, Any]
) -> dict[str, Any]:
    """Create a paired descriptive comparison for one registered seed."""

    identifiers = ("replicate", "birth_seed", "training_seed")
    if any(int(terminal[name]) != int(shaped[name]) for name in identifiers):
        raise ValueError("terminal and shaped summaries do not identify one seed")
    chain_comparison: dict[str, list[dict[str, Any]]] = {}
    for mode in ACTION_MODES:
        terminal_chain = terminal["final_chain"][mode]
        shaped_chain = shaped["final_chain"][mode]
        if [row["to"] for row in terminal_chain] != [
            row["to"] for row in shaped_chain
        ]:
            raise ValueError("terminal and shaped causal-chain orders differ")
        chain_comparison[mode] = [
            {
                "from": terminal_row["from"],
                "to": terminal_row["to"],
                "terminal_reached": terminal_row["reached"],
                "terminal_eligible": terminal_row["eligible"],
                "terminal_conditional_probability": terminal_row[
                    "conditional_probability"
                ],
                "shaped_reached": shaped_row["reached"],
                "shaped_eligible": shaped_row["eligible"],
                "shaped_conditional_probability": shaped_row[
                    "conditional_probability"
                ],
            }
            for terminal_row, shaped_row in zip(terminal_chain, shaped_chain)
        ]
    return {
        "replicate": int(terminal["replicate"]),
        "birth_seed": int(terminal["birth_seed"]),
        "training_seed": int(terminal["training_seed"]),
        "terminal_classification": terminal["classification"],
        "shaped_classification": shaped["classification"],
        "terminal_training_successes": int(terminal["training_successes"]),
        "shaped_training_successes": int(shaped["training_successes"]),
        "success_rate": {
            mode: {
                "terminal": float(terminal[f"{mode}_success_rate"]),
                "shaped": float(shaped[f"{mode}_success_rate"]),
                "terminal_minus_shaped": float(
                    terminal[f"{mode}_success_rate"]
                    - shaped[f"{mode}_success_rate"]
                ),
            }
            for mode in ACTION_MODES
        },
        "chain_comparison": chain_comparison,
    }


def _run_terminal_replicate(
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
    if result_path.is_file() != checkpoint_path.is_file():
        raise RuntimeError(f"partial resumable artifacts for replicate {replicate}")
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("replicate") != replicate
            or result.get("birth_seed") != birth_seed
            or result.get("training_seed") != training_seed
            or result.get("reward_mode") != "terminal"
            or result.get("updates") != UPDATES
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
                feedback_reward_mode="terminal",
                action_mode=mode,
                worlds_per_transform=8,
                stochastic_repeats=4,
            )
        )
        evaluation["update"] = 0
        evaluations.append(evaluation)

    def progress(row: Mapping[str, Any]) -> None:
        if row["update"] % 5 == 0 or row["update"] == UPDATES:
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
                "reward_mode": "terminal",
                **dict(row),
            }
            atomic_json(run_dir / "STATUS.json", status, output_root)
            suffix = ""
            if latest:
                deterministic = latest["deterministic"]
                fixed = latest["fixed_random"]
                suffix = (
                    f" det={deterministic['successes']}/"
                    f"{deterministic['world_count']}"
                    f" fixed={fixed['successes']}/{fixed['world_count']}"
                )
            print(
                f"replicate {replicate} update {row['update']}/{UPDATES}"
                f" steps={row['environment_steps']}{suffix}",
                flush=True,
            )

    started = time.monotonic()
    training = train_feedback_ppo(
        descendant,
        config,
        updates=UPDATES,
        training_seed=training_seed,
        reward_mode="terminal",
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
                feedback_reward_mode="terminal",
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
            if row["update"] == UPDATES and row["action_mode"] == mode
        ]
        expected = dict(evaluation)
        expected["update"] = UPDATES
        final_replay &= len(scheduled) == 1 and scheduled[0] == expected
    final_state = feedback_learner_digests(descendant)
    counts = {
        mode: sum(row["action_mode"] == mode for row in evaluations)
        for mode in ACTION_MODES
    }
    gates = {
        "all_training_metrics_finite": _finite_history(training["history"]),
        "expected_environment_steps": training["environment_steps"]
        == EXPECTED_STEPS,
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
        "updates": UPDATES,
        "environment_steps": training["environment_steps"],
        "germ_mode": "blind",
        "reward_mode": "terminal",
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
            "updates": UPDATES,
            "reward_mode": "terminal",
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
        raise RuntimeError(
            f"replicate {replicate} failed completion gates: {gates}"
        )
    return result


def markdown_report(batch: Mapping[str, Any]) -> str:
    summaries = batch["terminal_replicate_summaries"]
    paired = batch["paired_seed_summaries"]
    distribution = batch["terminal_success_rate_distribution"]
    lines = [
        "# DoorKey feedback-v2 terminal-only multi-seed study v1",
        "",
        "**Status:** `DEVELOPMENT — NOT A CARRIER OR LAW TEST`  ",
        f"**Credit routing:** `{batch['credit_routing_classification']}`  ",
        "**Carrier modes compared:** `NONE`",
        "",
        "## Bottom line",
        "",
        (
            "Four registered terminal-only, germ-blind feedback-v2 seeds each "
            f"ran {UPDATES} updates. Final argmax success ranged from "
            f"`{distribution['deterministic']['minimum']:.3f}` to "
            f"`{distribution['deterministic']['maximum']:.3f}` with median "
            f"`{distribution['deterministic']['median']:.3f}`. "
            "Fixed-common-random success ranged from "
            f"`{distribution['fixed_random']['minimum']:.3f}` to "
            f"`{distribution['fixed_random']['maximum']:.3f}` with median "
            f"`{distribution['fixed_random']['median']:.3f}`."
        ),
        "",
        (
            f"Training encountered `{batch['total_terminal_training_successes']}` "
            "terminal successes in total. Complete chains occurred under both "
            f"estimators in `{batch['terminal_seeds_completing_both_modes']}/4` "
            "seeds. These are mechanism-routing descriptions, not thresholds."
        ),
        "",
        "## Paired raw results",
        "",
        (
            "| Replicate | Terminal argmax | Shaped argmax | Terminal fixed | "
            "Shaped fixed | Terminal / shaped training successes |"
        ),
        "|---:|---:|---:|---:|---:|---:|",
    ]
    shaped_by_seed = {
        int(row["replicate"]): row
        for row in batch["shaped_reference_summaries"]
    }
    for terminal in summaries:
        shaped = shaped_by_seed[int(terminal["replicate"])]
        lines.append(
            f"| {terminal['replicate']} | "
            f"{terminal['deterministic_successes']}/"
            f"{terminal['deterministic_world_count']} | "
            f"{shaped['deterministic_successes']}/"
            f"{shaped['deterministic_world_count']} | "
            f"{terminal['fixed_random_successes']}/"
            f"{terminal['fixed_random_world_count']} | "
            f"{shaped['fixed_random_successes']}/"
            f"{shaped['fixed_random_world_count']} | "
            f"{terminal['training_successes']} / "
            f"{shaped['training_successes']} |"
        )
    for mode, title in (
        ("deterministic", "Terminal argmax final causal chains"),
        ("fixed_random", "Terminal fixed-random final causal chains"),
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
    lines.extend(["", "## Completion integrity", ""])
    for gate, passed in batch["completion_gates"].items():
        lines.append(f"- `{gate}`: `{'PASS' if passed else 'FAIL'}`")
    lines.extend(
        [
            "",
            (
                "The four terminal seeds used one CPU process/thread "
                f"sequentially and took `{batch['elapsed_training_seconds']:.3f}` "
                "training seconds in total. Every carrier stayed byte-exact to "
                "birth, every writer stayed dormant, and no carrier comparison "
                "or scientific future ran."
            ),
            "",
            "## Next boundary",
            "",
        ]
    )
    routing = batch["credit_routing_classification"]
    if routing == "TERMINAL_CHAIN_ALL_SEEDS":
        lines.append(
            "Ordinary terminal-only PPO completes the chain across these four "
            "seeds. A vertical carrier comparison can now be designed without "
            "first adding a credit mechanism."
        )
    elif routing == "TERMINAL_CHAIN_SEED_SENSITIVE":
        lines.append(
            "Terminal-only completion is seed-sensitive. Use the raw conditional "
            "links and reward exposures to choose between additional maturation "
            "and one targeted credit intervention before a carrier comparison."
        )
    elif routing == "TERMINAL_REWARD_OBSERVED_NO_EVALUATION_CHAIN":
        lines.append(
            "The learner experienced terminal rewards but did not consolidate a "
            "complete evaluation policy. The next isolated mechanism should be "
            "separate stage value heads while keeping the 64-byte germ fixed."
        )
    else:
        lines.append(
            "The learner never experienced a terminal reward. This is an "
            "exploration/exposure failure, not evidence that PPO failed to "
            "propagate an observed reward. The next mechanism should expose "
            "event-labelled or hindsight credit while keeping the germ fixed."
        )
    lines.extend(
        [
            "",
            "The shaped reference changes the reward signal and is a positive "
            "control, not a carrier treatment. This study cannot establish "
            "heredity or confirm a numbered law.",
            "",
        ]
    )
    # Ensure the paired structure was actually assembled before rendering.
    if len(paired) != len(REGISTERED_REPLICATES):
        raise ValueError("paired seed table is incomplete")
    return "\n".join(lines)


def run_batch(args: argparse.Namespace) -> int:
    overall_started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    output_root = external_root(args.external_root)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    workspace = Path(__file__).resolve().parents[2]
    shaped_replication_path = (
        output_root / "outputs" / SHAPED_REFERENCE_RUN / "replication.json"
    )
    shaped_manifest_path = (
        output_root / "runs" / SHAPED_REFERENCE_RUN / "MANIFEST.json"
    )
    shaped_hashes_path = (
        output_root / "outputs" / SHAPED_REFERENCE_RUN / "output_hashes.sha256"
    )
    input_paths = [
        workspace / "protocols/DOORKEY_FEEDBACK_TERMINAL_MULTISEED_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        workspace / "src/laws_confirmation/doorkey_feedback_scout.py",
        workspace / "src/laws_confirmation/doorkey_feedback_multiseed.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_ppo_v2.py",
        workspace / "tests/test_doorkey_feedback_scout.py",
        workspace / "tests/test_doorkey_feedback_multiseed.py",
        workspace / "tests/test_doorkey_feedback_terminal_multiseed.py",
        shaped_replication_path,
        shaped_manifest_path,
        shaped_hashes_path,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    shaped_gate = qualify_shaped_reference(
        shaped_replication_path, shaped_manifest_path, shaped_hashes_path
    )
    if not shaped_gate["passes"]:
        raise RuntimeError(f"shaped reference gate failed: {shaped_gate['gates']}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    config = FeedbackPPOConfig()
    disk = _disk_preflight(output_root, 512 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if args.resume:
        if not output_dir.is_dir() or not run_dir.is_dir():
            raise FileNotFoundError("resumable run directories do not exist")
        if (run_dir / "COMPLETE").exists() or (run_dir / "FAILED").exists():
            raise RuntimeError("only an interrupted RUNNING batch may resume")
        manifest = json.loads(
            (run_dir / "MANIFEST.json").read_text(encoding="utf-8")
        )
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
            "stage": "DoorKey feedback-v2 terminal-only multi-seed study",
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
                    "updates": UPDATES,
                    "reward_mode": "terminal",
                    "shaped_reference_digest": shaped_gate[
                        "reference_digest"
                    ],
                }
            ),
            "repository_head": git_head(workspace),
            "config": asdict(config),
            "replicates": list(REGISTERED_REPLICATES),
            "updates": UPDATES,
            "workers": 1,
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "reward_mode_comparisons": len(REGISTERED_REPLICATES),
            "germ_mode": "blind",
            "reward_mode": "terminal",
            "disk_preflight": disk,
            "shaped_reference_gate": shaped_gate,
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
        {
            "status": "RUNNING",
            "updated_utc": utc_now(),
            "replicate": 0,
            "reward_mode": "terminal",
        },
        output_root,
    )
    try:
        results = [
            _run_terminal_replicate(
                spec, config, output_root, output_dir, run_dir
            )
            for spec in REGISTERED_REPLICATES
        ]
        summaries = [
            _replicate_summary(result, "terminal_new") for result in results
        ]
        shaped_reference = json.loads(
            shaped_replication_path.read_text(encoding="utf-8")
        )
        shaped_summaries = shaped_reference["replicate_summaries"]
        shaped_by_seed = {
            int(row["replicate"]): row for row in shaped_summaries
        }
        paired = [
            paired_seed_summary(row, shaped_by_seed[int(row["replicate"])])
            for row in summaries
        ]
        deterministic_rates = [
            row["deterministic_success_rate"] for row in summaries
        ]
        fixed_rates = [row["fixed_random_success_rate"] for row in summaries]
        completion_gates = {
            "shaped_reference_gate_passed": shaped_gate["passes"],
            "four_registered_terminal_replicates": [
                {
                    "replicate": row["replicate"],
                    "birth_seed": row["birth_seed"],
                    "training_seed": row["training_seed"],
                }
                for row in results
            ]
            == list(REGISTERED_REPLICATES),
            "all_terminal_replicates_complete_cleanly": all(
                row["completed_cleanly"] for row in results
            ),
            "all_terminal_replicates_expected_transitions": all(
                row["environment_steps"] == EXPECTED_STEPS for row in results
            ),
            "paired_seed_table_complete": len(paired)
            == len(REGISTERED_REPLICATES),
        }
        batch = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "status": "DEVELOPMENT",
            "config": asdict(config),
            "registered_replicates": list(REGISTERED_REPLICATES),
            "updates": UPDATES,
            "terminal_replicate_summaries": summaries,
            "shaped_reference_summaries": shaped_summaries,
            "paired_seed_summaries": paired,
            "terminal_success_rate_distribution": {
                "deterministic": _distribution(deterministic_rates),
                "fixed_random": _distribution(fixed_rates),
            },
            "terminal_seed_classification": _aggregate_classification(
                summaries
            ),
            "credit_routing_classification": credit_routing_classification(
                summaries
            ),
            "terminal_seeds_completing_both_modes": sum(
                row["classification"] == "CHAIN_COMPLETION_BOTH_MODES"
                for row in summaries
            ),
            "total_terminal_training_successes": sum(
                int(row["training_successes"]) for row in summaries
            ),
            "elapsed_training_seconds": sum(
                row["elapsed_training_seconds"] for row in results
            ),
            "shaped_reference_gate": shaped_gate,
            "completion_gates": completion_gates,
            "completed_cleanly": all(completion_gates.values()),
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "reward_mode_comparisons": len(REGISTERED_REPLICATES),
        }
        atomic_json(output_dir / "study.json", batch, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(batch), output_root)
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "study.json",
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
            "credit_routing_classification": batch[
                "credit_routing_classification"
            ],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "reward_mode_comparisons": len(REGISTERED_REPLICATES),
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
