"""Qualify DoorKey PPO v2 action/reward feedback (development only)."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import platform
from pathlib import Path
import re
import shutil
import sys
import time
import traceback
from typing import Any, Mapping

import numpy as np
import torch

from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import GermSchema, read_germ, write_germ_from_local_evidence
from .doorkey_ppo import DoorKeyVectorEnv
from .doorkey_ppo_v2 import (
    START_ACTION,
    FeedbackPPOConfig,
    audit_feedback_boundary,
    birth_feedback_ppo_descendant,
    collect_feedback_rollout,
    evaluate_feedback_policy,
    feedback_learner_digests,
    make_empty_feedback_descendant,
    prime_feedback_parent_for_boundary_audit,
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


UPSTREAM_STAGE_B_RUN = "doorkey_vertical_stage_b_learner_qualification_v1_attempt1"
UPSTREAM_SCOUT_RUN = "doorkey_germ_blind_learning_scout_v1_attempt1"


def runtime_qualification() -> dict[str, Any]:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "torch_num_threads": torch.get_num_threads(),
        "torch_num_interop_threads": torch.get_num_interop_threads(),
    }
    gates = {
        "python_3_13": sys.version_info[:2] == (3, 13),
        "numpy_2_5_2": np.__version__ == "2.5.2",
        "torch_2_14_cpu": torch.__version__ == "2.14.0+cpu",
        "cuda_disabled": not torch.cuda.is_available(),
        "intraop_threads_one": torch.get_num_threads() == 1,
        "interop_threads_one": torch.get_num_interop_threads() == 1,
    }
    return {"versions": versions, "gates": gates, "passes": all(gates.values())}


def qualify_upstream_invariance(
    workspace: Path,
    stage_b_path: Path,
    scout_path: Path,
    scout_manifest_path: Path,
) -> dict[str, Any]:
    stage_b = json.loads(stage_b_path.read_text(encoding="utf-8"))
    scout = json.loads(scout_path.read_text(encoding="utf-8"))
    scout_manifest = json.loads(scout_manifest_path.read_text(encoding="utf-8"))
    recorded = scout_manifest["input_sha256"]
    targets = (
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
    )
    rows = []
    for path in targets:
        resolved = str(path.resolve())
        live = sha256_file(path)
        prior = recorded.get(resolved)
        rows.append(
            {
                "path": resolved,
                "v1_scout_sha256": prior,
                "live_sha256": live,
                "unchanged": prior is not None and live == prior,
            }
        )
    gates = {
        "stage_b_passed": bool(stage_b.get("overall_pass")),
        "v1_scout_diagnosed_learner_floor": scout.get(
            "diagnostic_classification"
        )
        == "NEITHER_CLEARS_DEVELOPMENT_THRESHOLD",
        "carrier_boundary_world_and_v1_learner_unchanged": all(
            row["unchanged"] for row in rows
        ),
    }
    return {
        "stage_b_run_id": stage_b.get("run_id"),
        "v1_scout_run_id": scout.get("run_id"),
        "v1_scout_classification": scout.get("diagnostic_classification"),
        "source_rows": rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def qualify_episode_feedback_reset() -> dict[str, Any]:
    config = FeedbackPPOConfig(
        tile_embedding_size=4,
        action_embedding_size=4,
        hidden_size=16,
        num_envs=4,
        rollout_steps=16,
        ppo_epochs=1,
        minibatch_envs=2,
        max_episode_steps=32,
    )
    descendant = make_empty_feedback_descendant(config, 860_000)
    model = descendant.model
    observations = torch.zeros((config.num_envs, config.observation_width))
    arbitrary_hidden = torch.arange(
        config.num_envs * config.hidden_size, dtype=torch.float32
    ).reshape(config.num_envs, config.hidden_size)
    arbitrary_actions = torch.arange(config.num_envs) % config.num_actions
    arbitrary_rewards = torch.tensor([1.0, -1.0, 0.5, -0.5])
    starts = torch.ones(config.num_envs, dtype=torch.bool)
    canonical = model.forward_step(
        observations,
        torch.zeros_like(arbitrary_hidden),
        starts,
        torch.full_like(arbitrary_actions, START_ACTION),
        torch.zeros_like(arbitrary_rewards),
    )
    perturbed = model.forward_step(
        observations,
        arbitrary_hidden,
        starts,
        arbitrary_actions,
        arbitrary_rewards,
    )
    episode_outputs_equal = all(
        torch.equal(left, right) for left, right in zip(canonical, perturbed)
    )
    continuing = torch.zeros(config.num_envs, dtype=torch.bool)
    baseline = model.forward_step(
        observations,
        torch.zeros_like(arbitrary_hidden),
        continuing,
        torch.full_like(arbitrary_actions, START_ACTION),
        torch.zeros_like(arbitrary_rewards),
    )
    action_changed = model.forward_step(
        observations,
        torch.zeros_like(arbitrary_hidden),
        continuing,
        torch.zeros_like(arbitrary_actions),
        torch.zeros_like(arbitrary_rewards),
    )
    reward_changed = model.forward_step(
        observations,
        torch.zeros_like(arbitrary_hidden),
        continuing,
        torch.full_like(arbitrary_actions, START_ACTION),
        torch.ones_like(arbitrary_rewards),
    )
    action_difference = float(
        torch.max(torch.abs(baseline[2] - action_changed[2])).detach()
    )
    reward_difference = float(
        torch.max(torch.abs(baseline[2] - reward_changed[2])).detach()
    )
    gates = {
        "episode_start_erases_hidden_action_and_reward": episode_outputs_equal,
        "continuing_transition_uses_previous_action": action_difference > 0.0,
        "continuing_transition_uses_previous_reward": reward_difference > 0.0,
    }
    return {
        "config": asdict(config),
        "max_hidden_difference_after_action_change": action_difference,
        "max_hidden_difference_after_reward_change": reward_difference,
        "gates": gates,
        "passes": all(gates.values()),
    }


def _strong_evidence(offset: int) -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    for slot in range(4):
        evidence[0, slot, (slot + offset) % 8] = 12.0
    return evidence


def qualify_feedback_boundaries() -> dict[str, Any]:
    config = FeedbackPPOConfig()
    schema = GermSchema()
    parent = make_empty_feedback_descendant(config, 870_000)
    rows: list[dict[str, Any]] = []
    for boundary_index in range(3):
        prime_feedback_parent_for_boundary_audit(parent, 41.0 + boundary_index)
        packet = make_boundary_packet(parent.germ, schema)
        child = birth_feedback_ppo_descendant(
            packet, config, 870_001 + boundary_index, device="cpu"
        )
        reset = audit_feedback_boundary(parent, child, packet)
        inherited = read_germ(child.germ, schema)
        rewritten, commit = write_germ_from_local_evidence(
            _strong_evidence(boundary_index + 1), child.germ, schema
        )
        child.germ = rewritten
        rows.append(
            {
                "boundary": boundary_index + 1,
                "packet_bytes": len(packet.payload),
                "packet_sha256": packet.digest(),
                "inherited_active_slots": int(inherited.active.sum()),
                "commit_mask": commit.tolist()[0],
                "outgoing_active_slots": int(read_germ(rewritten, schema).active.sum()),
                "reset_audit": reset,
                "child_state_sha256": feedback_learner_digests(child),
            }
        )
        parent = child
    gates = {
        "three_boundaries": len(rows) == 3,
        "all_packets_64_bytes": all(row["packet_bytes"] == 64 for row in rows),
        "all_real_state_audits_pass": all(
            row["reset_audit"]["passes"] for row in rows
        ),
        "previous_action_and_reward_reset_each_birth": all(
            row["reset_audit"]["state_rows"]["previous_action_state"]["reset"]
            and row["reset_audit"]["state_rows"]["previous_reward_state"]["reset"]
            for row in rows
        ),
        "all_descendants_rewrite_all_slots": all(
            all(row["commit_mask"]) for row in rows
        ),
        "all_outgoing_slots_readable": all(
            row["outgoing_active_slots"] == 4 for row in rows
        ),
    }
    return {
        "config": asdict(config),
        "public_rulebook_sha256": config.digest(),
        "boundary_rows": rows,
        "gates": gates,
        "passes": all(gates.values()),
    }


def qualify_rollout_feedback() -> dict[str, Any]:
    config = FeedbackPPOConfig(
        tile_embedding_size=4,
        action_embedding_size=4,
        hidden_size=32,
        num_envs=8,
        rollout_steps=32,
        ppo_epochs=1,
        minibatch_envs=4,
        max_episode_steps=16,
    )
    descendant = make_empty_feedback_descendant(config, 880_000)
    environments = DoorKeyVectorEnv(
        config.num_envs,
        base_seed=8_810_000,
        max_steps=config.max_episode_steps,
        reward_mode="stage_shaped",
    )
    rollout, completed = collect_feedback_rollout(
        descendant, environments, config, germ_mode="blind"
    )
    expected_actions = rollout.actions[:-1].clone()
    expected_rewards = rollout.rewards[:-1].clone()
    prior_done = rollout.dones[:-1]
    expected_actions[prior_done] = START_ACTION
    expected_rewards[prior_done] = 0.0
    reset_mask = rollout.episode_starts
    gates = {
        "first_feedback_is_start_and_zero": bool(
            torch.all(rollout.previous_actions[0] == START_ACTION)
            and torch.all(rollout.previous_rewards[0] == 0.0)
        ),
        "every_later_action_matches_sample_or_reset": torch.equal(
            rollout.previous_actions[1:], expected_actions
        ),
        "every_later_reward_matches_observation_or_reset": torch.equal(
            rollout.previous_rewards[1:], expected_rewards
        ),
        "episode_start_feedback_always_reset": bool(
            torch.all(rollout.previous_actions[reset_mask] == START_ACTION)
            and torch.all(rollout.previous_rewards[reset_mask] == 0.0)
        ),
        "rollout_exercises_post_birth_episode_reset": int(reset_mask.sum())
        > config.num_envs,
        "advantages_finite": bool(torch.isfinite(rollout.advantages).all()),
    }
    return {
        "config": asdict(config),
        "transitions": config.num_envs * config.rollout_steps,
        "completed_episodes": len(completed),
        "stored_episode_starts": int(reset_mask.sum()),
        "nonzero_received_rewards": int(torch.count_nonzero(rollout.rewards)),
        "gates": gates,
        "passes": all(gates.values()),
    }


def _finite_history(result: Mapping[str, Any]) -> bool:
    numeric_names = (
        "mean_rollout_reward",
        "max_rollout_reward",
        "policy_loss",
        "value_loss",
        "entropy",
        "approx_kl",
        "clip_fraction",
        "grad_norm",
    )
    return all(
        math.isfinite(float(row[name]))
        for row in result["history"]
        for name in numeric_names
    )


def qualify_training_replay() -> dict[str, Any]:
    config = FeedbackPPOConfig(
        tile_embedding_size=4,
        action_embedding_size=4,
        hidden_size=32,
        num_envs=8,
        rollout_steps=32,
        ppo_epochs=2,
        minibatch_envs=4,
        max_episode_steps=64,
    )

    def run_once(
        reward_mode: str,
    ) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
        descendant = make_empty_feedback_descendant(config, 890_000)
        before = feedback_learner_digests(descendant)
        result = train_feedback_ppo(
            descendant,
            config,
            updates=3,
            training_seed=8_910_000,
            reward_mode=reward_mode,
            germ_mode="blind",
            evaluation_every=0,
        )
        return result, before, feedback_learner_digests(descendant)

    shaped_first, shaped_before, shaped_after = run_once("stage_shaped")
    shaped_second, _, shaped_second_after = run_once("stage_shaped")
    terminal, terminal_before, terminal_after = run_once("terminal")
    gates = {
        "stage_shaped_metrics_finite": _finite_history(shaped_first),
        "terminal_metrics_finite": _finite_history(terminal),
        "actor_critic_updates_in_shaped_mode": (
            shaped_before["actor_critic"] != shaped_after["actor_critic"]
        ),
        "actor_critic_updates_in_terminal_mode": (
            terminal_before["actor_critic"] != terminal_after["actor_critic"]
        ),
        "dormant_writer_does_not_change": (
            shaped_before["writer"] == shaped_after["writer"]
            and terminal_before["writer"] == terminal_after["writer"]
        ),
        "stage_shaped_replay_exact": (
            shaped_first == shaped_second
            and shaped_after == shaped_second_after
        ),
        "expected_environment_step_count": (
            shaped_first["environment_steps"] == 3 * 8 * 32
            and terminal["environment_steps"] == 3 * 8 * 32
        ),
    }
    return {
        "config": asdict(config),
        "stage_shaped_first": shaped_first,
        "stage_shaped_second_final_sha256": shaped_second_after,
        "terminal": terminal,
        "state_before": shaped_before,
        "state_after_stage_shaped": shaped_after,
        "state_after_terminal": terminal_after,
        "gates": gates,
        "passes": all(gates.values()),
    }


def _behavior_digest(evaluation: Mapping[str, Any]) -> str:
    return canonical_digest(
        {
            "successes": evaluation["successes"],
            "conditional_chain": evaluation["conditional_chain"],
            "early_action_counts_by_context": evaluation[
                "early_action_counts_by_context"
            ],
            "world_rows": evaluation["world_rows"],
        }
    )


def qualify_evaluation_replay() -> dict[str, Any]:
    config = FeedbackPPOConfig(
        tile_embedding_size=4,
        action_embedding_size=4,
        hidden_size=32,
        num_envs=8,
        rollout_steps=32,
        ppo_epochs=1,
        minibatch_envs=4,
        max_episode_steps=64,
    )
    descendant = make_empty_feedback_descendant(config, 900_000)
    state_before = feedback_learner_digests(descendant)

    def evaluate(action_mode: str, action_seed: int = 71_000_000) -> dict[str, Any]:
        return evaluate_feedback_policy(
            descendant,
            config,
            germ_mode="blind",
            feedback_reward_mode="stage_shaped",
            action_mode=action_mode,
            worlds_per_transform=1,
            action_seed=action_seed,
            stochastic_repeats=3,
        )

    deterministic_first = evaluate("deterministic")
    deterministic_second = evaluate("deterministic")
    fixed_first = evaluate("fixed_random")
    fixed_second = evaluate("fixed_random")
    fixed_alternate = evaluate("fixed_random", action_seed=71_000_001)
    state_after = feedback_learner_digests(descendant)
    fixed_digest = _behavior_digest(fixed_first)
    alternate_digest = _behavior_digest(fixed_alternate)
    gates = {
        "deterministic_evaluation_replays_exactly": (
            deterministic_first == deterministic_second
        ),
        "fixed_random_evaluation_replays_exactly": fixed_first == fixed_second,
        "different_uniform_seed_changes_behavioral_trace": (
            fixed_digest != alternate_digest
        ),
        "evaluation_does_not_consume_training_state": state_before == state_after,
        "deterministic_world_contract": (
            deterministic_first["world_count"] == 4
            and deterministic_first["unique_layout_count"] == 4
        ),
        "stochastic_replication_contract": (
            fixed_first["world_count"] == 12
            and fixed_first["unique_layout_count"] == 4
            and fixed_first["stochastic_repeats"] == 3
        ),
    }
    return {
        "config": asdict(config),
        "deterministic": deterministic_first,
        "fixed_random": fixed_first,
        "fixed_random_behavior_sha256": fixed_digest,
        "alternate_seed_behavior_sha256": alternate_digest,
        "state_before_sha256": state_before,
        "state_after_sha256": state_after,
        "gates": gates,
        "passes": all(gates.values()),
    }


def benchmark_default_training() -> dict[str, Any]:
    config = FeedbackPPOConfig()
    descendant = make_empty_feedback_descendant(config, 910_000)
    training_started = time.monotonic()
    result = train_feedback_ppo(
        descendant,
        config,
        updates=3,
        training_seed=9_110_000,
        reward_mode="stage_shaped",
        germ_mode="blind",
        evaluation_every=0,
    )
    training_elapsed = time.monotonic() - training_started
    evaluation_rows: dict[str, Any] = {}
    evaluation_seconds: dict[str, float] = {}
    for mode in ("deterministic", "fixed_random"):
        evaluation_started = time.monotonic()
        evaluation = evaluate_feedback_policy(
            descendant,
            config,
            germ_mode="blind",
            feedback_reward_mode="stage_shaped",
            action_mode=mode,
            worlds_per_transform=8,
            stochastic_repeats=4,
        )
        evaluation_seconds[mode] = time.monotonic() - evaluation_started
        evaluation.pop("world_rows")
        evaluation_rows[mode] = evaluation
    seconds_per_update = training_elapsed / 3
    return {
        "config": asdict(config),
        "updates": 3,
        "environment_steps": result["environment_steps"],
        "training_elapsed_seconds": training_elapsed,
        "seconds_per_update": seconds_per_update,
        "environment_steps_per_second": result["environment_steps"]
        / training_elapsed,
        "evaluation_elapsed_seconds": evaluation_seconds,
        "evaluation_summaries": evaluation_rows,
        "projected_training_seconds": {
            str(updates): seconds_per_update * updates
            for updates in (100, 300, 500, 1000)
        },
        "historical_development_result": result,
        "noninferential": True,
    }


def markdown_report(audit: Mapping[str, Any]) -> str:
    runtime = audit["runtime"]
    upstream = audit["upstream_invariance"]
    episode = audit["episode_feedback_reset"]
    boundaries = audit["real_boundaries"]
    rollout = audit["rollout_feedback"]
    smoke = audit["training_replay"]
    evaluation = audit["evaluation_replay"]
    benchmark = audit["benchmark"]
    lines = [
        "# DoorKey action/reward-feedback learner qualification v1",
        "",
        f"**Qualification:** `{'PASS' if audit['overall_pass'] else 'FAIL'}`  ",
        "**Scientific verdict:** `NONE — DEVELOPMENT APPARATUS ONLY`  ",
        "**Carrier-effect comparison:** `NOT RUN`",
        "",
        "## Bottom line",
        "",
        "The separately versioned v2 recurrent learner passed its action/reward-feedback, episode reset, three-boundary somatic reset, deterministic PPO replay, and common-random evaluation gates. The DoorKey environment and 64-byte carrier sources remain byte-identical to the first scout. This qualifies a new shaped germ-blind learning scout; it does not show that DoorKey is learned or that a germ has any effect.",
        "",
        f"The pinned runtime was Python `{runtime['versions']['python']}`, NumPy `{runtime['versions']['numpy']}`, and PyTorch `{runtime['versions']['torch']}` with CUDA disabled and one intra-op/inter-op thread.",
        "",
        "## Qualification gates",
        "",
        "| Layer | Gate | Result |",
        "|---|---|---|",
    ]
    for layer, section in (
        ("runtime", runtime),
        ("upstream", upstream),
        ("episode", episode),
        ("boundary", boundaries),
        ("rollout", rollout),
        ("PPO replay", smoke),
        ("evaluation", evaluation),
    ):
        for gate, passed in section["gates"].items():
            lines.append(f"| {layer} | `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "## What was actually exercised",
            "",
            f"The rollout stored `{rollout['transitions']}` transitions, crossed `{rollout['stored_episode_starts']}` episode starts, completed `{rollout['completed_episodes']}` episodes, and contained `{rollout['nonzero_received_rewards']}` nonzero received rewards. Every later feedback tuple matched the preceding sampled action and received reward, including reset after completion.",
            "",
            f"Three consecutive lineage births transmitted exactly 64 bytes and reset actor/critic, dormant writer, both Adam states, rollout, recurrent hidden, previous action, previous reward, and both private RNGs. All four germ slots were synthetically rewritten after each birth only as a plumbing test.",
            "",
            "Two independent three-update stage-shaped smokes replayed exactly, while a terminal smoke independently changed the actor/critic with finite metrics. The writer remained dormant. The fixed-random evaluator replayed exactly under the same uniform seed and produced a different behavioral trace under a different seed, without advancing training state.",
            "",
            "## Runtime sizing",
            "",
            f"The default v2 learner processed `{benchmark['environment_steps']}` transitions in `{benchmark['training_elapsed_seconds']:.3f}` seconds (`{benchmark['seconds_per_update']:.3f}` s/update; `{benchmark['environment_steps_per_second']:.1f}` transitions/s). A 100-update shaped run projects to `{benchmark['projected_training_seconds']['100']:.1f}` seconds before scheduled evaluations. The full deterministic 32-world evaluation took `{benchmark['evaluation_elapsed_seconds']['deterministic']:.3f}` seconds and the fixed-random 128-trajectory evaluation took `{benchmark['evaluation_elapsed_seconds']['fixed_random']:.3f}` seconds.",
            "",
            "## Next boundary",
            "",
            "Freeze and run a stage-shaped, germ-blind v2 scout with both estimators. The first question is whether explicit action/reward feedback repairs the observed causal-chain failure. Terminal reward, value-head variants, and carrier arms remain out of scope until that positive control is interpretable.",
            "",
            "No outcome here supports inherited action shaping, a learning disposition, autonomous writing, vertical renewal, functional ontology, or any numbered law.",
            "",
        ]
    )
    return "\n".join(lines)


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


def run_qualification(args: argparse.Namespace) -> int:
    started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    output_root = external_root(args.external_root)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(f"immutable run ID exists: {args.run_id}")
    run_dir.mkdir(parents=True)
    disk = _disk_preflight(output_root, 16 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    workspace = Path(__file__).resolve().parents[2]
    stage_b_path = (
        output_root / "outputs" / UPSTREAM_STAGE_B_RUN / "qualification.json"
    )
    scout_path = output_root / "outputs" / UPSTREAM_SCOUT_RUN / "scout.json"
    scout_manifest_path = output_root / "runs" / UPSTREAM_SCOUT_RUN / "MANIFEST.json"
    input_paths = [
        workspace / "protocols/DOORKEY_ACTION_REWARD_FEEDBACK_QUALIFICATION_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        workspace / "src/laws_confirmation/doorkey_ppo_v2.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_ppo_v2.py",
        stage_b_path,
        scout_path,
        scout_manifest_path,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "DoorKey action/reward-feedback learner qualification",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "input_sha256": input_hashes,
        "contract_digest": canonical_digest(input_hashes),
        "repository_head": git_head(workspace),
        "workers": 1,
        "scientific_futures_generated": 0,
        "carrier_effect_comparisons": 0,
        "disk_preflight": disk,
        "environment": environment_manifest(),
    }
    atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    atomic_json(
        run_dir / "STATUS.json",
        {"status": "RUNNING", "updated_utc": utc_now()},
        output_root,
    )
    try:
        runtime = runtime_qualification()
        upstream = qualify_upstream_invariance(
            workspace, stage_b_path, scout_path, scout_manifest_path
        )
        episode = qualify_episode_feedback_reset()
        boundaries = qualify_feedback_boundaries()
        rollout = qualify_rollout_feedback()
        training = qualify_training_replay()
        evaluation = qualify_evaluation_replay()
        benchmark = benchmark_default_training()
        gated_sections = (
            runtime,
            upstream,
            episode,
            boundaries,
            rollout,
            training,
            evaluation,
        )
        audit = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "runtime": runtime,
            "upstream_invariance": upstream,
            "episode_feedback_reset": episode,
            "real_boundaries": boundaries,
            "rollout_feedback": rollout,
            "training_replay": training,
            "evaluation_replay": evaluation,
            "benchmark": benchmark,
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "overall_pass": all(section["passes"] for section in gated_sections),
        }
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "qualification.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        atomic_text(
            output_dir / "smoke_history.jsonl",
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in training["stage_shaped_first"]["history"]
            ),
            output_root,
        )
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "qualification.json",
            output_dir / "audit.md",
            output_dir / "smoke_history.jsonl",
            output_dir / "input_hashes.sha256",
        ]
        write_hash_manifest(
            output_paths, output_dir / "output_hashes.sha256", output_root
        )
        status = {
            "status": "COMPLETE" if audit["overall_pass"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started,
            "overall_pass": audit["overall_pass"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
        }
        atomic_json(run_dir / "STATUS.json", status, output_root)
        sentinel = "COMPLETE" if audit["overall_pass"] else "FAILED"
        atomic_text(run_dir / sentinel, status["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0 if audit["overall_pass"] else 1
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
    return parser


def main() -> int:
    return run_qualification(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
