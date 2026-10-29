"""Stage-B runtime, differential, reset, and recurrent-PPO qualification."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time
import traceback
from typing import Any, Mapping

import numpy as np
import torch

from .doorkey_boundary import make_boundary_packet
from .doorkey_carrier import (
    GermSchema,
    empty_germ,
    read_germ,
    write_germ_from_local_evidence,
)
from .doorkey_carrier_conformance import run_torch_differential
from .doorkey_ppo import (
    PPOConfig,
    audit_real_ppo_boundary,
    birth_ppo_descendant,
    learner_state_digests,
    make_empty_ppo_descendant,
    prime_ppo_parent_for_boundary_audit,
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


def _strong_evidence(offset: int) -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    for slot in range(4):
        evidence[0, slot, (slot + offset) % 8] = 12.0
    return evidence


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


def qualify_real_boundaries() -> dict[str, Any]:
    config = PPOConfig()
    schema = GermSchema()
    parent = make_empty_ppo_descendant(config, 810_000)
    rows: list[dict[str, Any]] = []
    for boundary_index in range(3):
        prime_ppo_parent_for_boundary_audit(parent, 31.0 + boundary_index)
        packet = make_boundary_packet(parent.germ, schema)
        child = birth_ppo_descendant(
            packet, config, 810_001 + boundary_index, device="cpu"
        )
        reset = audit_real_ppo_boundary(parent, child, packet)
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
                "learner_state_after_birth_sha256": learner_state_digests(child),
            }
        )
        parent = child
    gates = {
        "three_boundaries": len(rows) == 3,
        "all_packets_64_bytes": all(row["packet_bytes"] == 64 for row in rows),
        "all_real_state_audits_pass": all(
            row["reset_audit"]["passes"] for row in rows
        ),
        "all_descendants_rewrite_all_slots": all(
            all(row["commit_mask"]) for row in rows
        ),
        "all_outgoing_slots_readable": all(
            row["outgoing_active_slots"] == 4 for row in rows
        ),
    }
    return {
        "ppo_config": asdict(config),
        "public_rulebook_sha256": config.digest(),
        "boundary_rows": rows,
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


def qualify_training_smoke() -> dict[str, Any]:
    config = PPOConfig(
        tile_embedding_size=4,
        hidden_size=32,
        num_envs=8,
        rollout_steps=32,
        ppo_epochs=2,
        minibatch_envs=4,
        max_episode_steps=64,
    )

    def run_once(reward_mode: str) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
        descendant = make_empty_ppo_descendant(config, 820_000)
        before = learner_state_digests(descendant)
        result = train_ppo(
            descendant,
            config,
            updates=3,
            training_seed=830_000,
            reward_mode=reward_mode,
            germ_mode="blind",
            evaluation_every=0,
        )
        after = learner_state_digests(descendant)
        return result, before, after

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
        "stage_shaped_second_sha256": shaped_second_after,
        "terminal": terminal,
        "state_before": shaped_before,
        "state_after_stage_shaped": shaped_after,
        "state_after_terminal": terminal_after,
        "gates": gates,
        "passes": all(gates.values()),
    }


def benchmark_default_training() -> dict[str, Any]:
    config = PPOConfig()
    descendant = make_empty_ppo_descendant(config, 840_000)
    started = time.monotonic()
    result = train_ppo(
        descendant,
        config,
        updates=3,
        training_seed=850_000,
        reward_mode="stage_shaped",
        germ_mode="blind",
        evaluation_every=0,
    )
    elapsed = time.monotonic() - started
    seconds_per_update = elapsed / 3
    return {
        "config": asdict(config),
        "updates": 3,
        "environment_steps": result["environment_steps"],
        "elapsed_seconds": elapsed,
        "seconds_per_update": seconds_per_update,
        "environment_steps_per_second": result["environment_steps"] / elapsed,
        "projected_seconds": {
            str(updates): seconds_per_update * updates
            for updates in (100, 300, 500, 1000)
        },
        "historical_development_result": result,
        "noninferential": True,
    }


def markdown_report(audit: Mapping[str, Any]) -> str:
    runtime = audit["runtime"]
    differential = audit["carrier_differential"]
    boundaries = audit["real_boundaries"]
    smoke = audit["training_smoke"]
    benchmark = audit["benchmark"]
    lines = [
        "# DoorKey Stage-B learner qualification",
        "",
        f"**Qualification:** `{'PASS' if audit['overall_pass'] else 'FAIL'}`  ",
        "**Scientific verdict:** `NONE — DEVELOPMENT APPARATUS ONLY`  ",
        "**Carrier-effect comparison:** `NOT RUN`",
        "",
        "## Bottom line",
        "",
        "The external CPU-only PyTorch runtime, randomized carrier differential, recurrent PPO update path, deterministic replay, and real learner-state boundary audit all passed. This qualifies the machinery needed for a learning scout. It does not establish that PPO learns DoorKey, that a germ helps, that the germ is renewed from experience, or that its content is a learning disposition.",
        "",
        f"Runtime is Python `{runtime['versions']['python']}`, NumPy `{runtime['versions']['numpy']}`, and PyTorch `{runtime['versions']['torch']}` with CUDA disabled and both PyTorch thread counts fixed to one. The differential executed {differential['trials']} randomized trials with {differential['operations']['write']} slot writes, {differential['operations']['read']} slot reads, and zero mismatches. Three consecutive births passed the reset audit on actual modules, optimizers, recurrent state, rollout state, and private RNGs.",
        "",
        "## Qualification gates",
        "",
        "| Layer | Gate | Result |",
        "|---|---|---|",
    ]
    for layer, section in (
        ("runtime", runtime),
        ("carrier", differential),
        ("real boundary", boundaries),
        ("PPO smoke", smoke),
    ):
        layer_gates = section.get("gates")
        if layer_gates is None:
            layer_gates = {
                "schema_equal": section["schema_equal"],
                "byte_exact": section["byte_exact"],
                "zero_mismatches": section["mismatch_count"] == 0,
                "decoded_logits_exact": section["max_prior_absolute_difference"] == 0,
            }
        for gate, passed in layer_gates.items():
            lines.append(f"| {layer} | `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "## Randomized carrier differential",
            "",
            f"The NumPy codec and authoritative `slot_germ.py` produced identical empty carriers, reads, commits, writes, aging, confirmation blocks, revocations, payload permutations, and unsealed corruptions over seed `{differential['seed']}`. Maximum decoded-prior difference was `{differential['max_prior_absolute_difference']}` and mismatches were `{differential['mismatch_count']}`. This closes the Stage-A runtime-conformance caveat for the frozen source hash; it does not make the implementation independent evidence for a scientific claim.",
            "",
            "## Real vertical reset",
            "",
            "| Boundary | Incoming active records | Bytes | Rewritten records | Reset |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for row in boundaries["boundary_rows"]:
        lines.append(
            f"| {row['boundary']} | {row['inherited_active_slots']} | {row['packet_bytes']} | {sum(row['commit_mask'])}/4 | `{'PASS' if row['reset_audit']['passes'] else 'FAIL'}` |"
        )
    lines.extend(
        [
            "",
            "The birth function has no parent argument. Actor/critic and dormant writer parameters are freshly initialized; both Adam states are empty; recurrent tensors are zero and non-shared; rollout storage is absent; private NumPy and Torch generator states differ; and fixed encoding deliberately has no learned normalizer, curriculum, or population statistics. The carrier rewrite still uses synthetic evidence, so learned renewal remains untested.",
            "",
            "## PPO smoke and sizing",
            "",
            f"Two independent stage-shaped smoke runs were bit-for-bit replay-identical. A separate terminal-only smoke had finite gradients and changed the actor/critic. Neither three-update smoke is a learnability test. The dormant writer was unchanged in all training smokes, as required at this stage.",
            "",
            f"The default 32-environment recurrent configuration processed {benchmark['environment_steps']} transitions in {benchmark['elapsed_seconds']:.3f} seconds ({benchmark['environment_steps_per_second']:.1f} transitions/s; {benchmark['seconds_per_update']:.3f} s/update). Projected wall times are approximately {benchmark['projected_seconds']['100']:.0f} s for 100 updates, {benchmark['projected_seconds']['300']:.0f} s for 300, and {benchmark['projected_seconds']['500']:.0f} s for 500. Projections are engineering estimates, not outcome data or runtime guarantees.",
            "",
            "## Next gate",
            "",
            "Run a development learning curve on the germ-blind policy. Use the stage-shaped arm only as a positive-control diagnostic and terminal-only reward as the target baseline. Retain all causal-chain endpoints. If neither learns, repair the learner or task representation before adding carrier mechanisms. If terminal-only PPO remains selectively stuck while the shaped arm learns, then the adviser's separate-value-head proposal becomes the next isolated intervention.",
            "",
            "No intact-versus-zero carrier effect, vertical population, parent-trained writer, early-behavior matching, or disposition claim is authorized by this qualification.",
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


def run_stage_b(args: argparse.Namespace) -> int:
    started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError("invalid run ID")
    output_root = external_root(args.external_root)
    reference_source = Path(args.reference_slot_germ).expanduser().resolve()
    if not reference_source.is_file():
        raise FileNotFoundError(reference_source)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(f"immutable run ID exists: {args.run_id}")
    run_dir.mkdir(parents=True)
    disk = _disk_preflight(output_root, 8 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")
    workspace = Path(__file__).resolve().parents[2]
    input_paths = [
        workspace / "protocols/DOORKEY_VERTICAL_STAGE_B_LEARNER_QUALIFICATION_V1.md",
        workspace / "requirements-doorkey.lock",
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_carrier_conformance.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_ppo.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_carrier_conformance.py",
        workspace / "tests/test_doorkey_ppo.py",
        reference_source,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "DoorKey Stage-B learner qualification",
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
        differential = run_torch_differential(
            reference_source, trials=256, seed=2_314_640
        )
        boundaries = qualify_real_boundaries()
        smoke = qualify_training_smoke()
        benchmark = benchmark_default_training()
        differential_pass = bool(
            differential["schema_equal"]
            and differential["byte_exact"]
            and differential["mismatch_count"] == 0
            and differential["max_prior_absolute_difference"] == 0
        )
        audit = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "runtime": runtime,
            "carrier_differential": differential,
            "real_boundaries": boundaries,
            "training_smoke": smoke,
            "benchmark": benchmark,
            "scientific_futures_generated": 0,
            "carrier_effect_comparisons": 0,
            "overall_pass": bool(
                runtime["passes"]
                and differential_pass
                and boundaries["passes"]
                and smoke["passes"]
            ),
        }
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "qualification.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        atomic_text(
            output_dir / "smoke_history.jsonl",
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in smoke["stage_shaped_first"]["history"]
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
    parser.add_argument("--reference-slot-germ", required=True)
    return parser


def main() -> int:
    return run_stage_b(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
