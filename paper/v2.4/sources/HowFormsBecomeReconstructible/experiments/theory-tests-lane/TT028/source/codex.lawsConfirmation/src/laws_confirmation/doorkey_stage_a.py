"""Developmental qualification runner for the DoorKey vertical boundary."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import shutil
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

from .doorkey_boundary import (
    PublicRulebook,
    audit_boundary_reset,
    birth_descendant,
    boundary_audit_passes,
    contaminate_soma,
    make_boundary_packet,
)
from .doorkey_carrier import (
    GermSchema,
    address_table,
    carrier_digest,
    corrupt_byte,
    empty_germ,
    permute_payloads,
    read_germ,
    write_germ_from_local_evidence,
)
from .doorkey_env import (
    Action,
    CAUSAL_CHAIN,
    DoorKeyEnv,
    TRANSFORMS,
    make_layout,
    oracle_plan,
    run_actions,
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


def _golden_empty_slots() -> list[list[int]]:
    addresses = (
        (0, 19, 41, 97),
        (1, 92, 192, 40),
        (2, 165, 87, 239),
        (3, 238, 238, 182),
    )
    checksums = (156, 68, 236, 148)
    return [
        [*address, *([128] * 8), 0, 255, 0, checksum]
        for address, checksum in zip(addresses, checksums)
    ]


def qualify_carrier(reference_source: Path) -> dict[str, Any]:
    schema = GermSchema()
    schema.validate()
    empty = empty_germ(1, schema)
    empty_read = read_germ(empty, schema)
    golden_empty = _golden_empty_slots()

    written, commit = write_germ_from_local_evidence(
        _strong_evidence(0), empty, schema
    )
    written_read = read_germ(written, schema)
    written_slots = written.reshape(4, 16)
    expected_payloads = []
    for target in range(4):
        payload = [125] * 8
        payload[target] = 149
        expected_payloads.append(payload)
    written_golden = bool(
        written_slots[:, 4:12].tolist() == expected_payloads
        and written_slots[:, 12].tolist() == [255] * 4
        and written_slots[:, 13].tolist() == [0] * 4
        and written_slots[:, 14].tolist() == [1] * 4
        and written_slots[:, 15].tolist() == [157, 69, 237, 149]
    )

    corrupted_read = read_germ(corrupt_byte(written, 5), schema)
    wrong = permute_payloads(written, np.asarray([1, 2, 3, 0]), schema)
    wrong_read = read_germ(wrong, schema)
    source_text = reference_source.read_text(encoding="utf-8")
    source_markers = (
        "num_slots: int = 4",
        "num_actions: int = 8",
        "slot_bytes: int = 16",
        "payload_scale: float = 0.25",
        "min_read_trust: int = 190",
        "min_write_trust: int = 190",
        "max_freshness: int = 32",
        "analytic_route_id: int = 1",
    )
    gates = {
        "reference_source_markers_present": all(
            marker in source_text for marker in source_markers
        ),
        "exact_64_byte_shape": empty.shape == (1, 64) and empty.dtype == np.uint8,
        "empty_golden_vector": empty.reshape(4, 16).tolist() == golden_empty,
        "empty_addresses_valid": bool(empty_read.address_valid.all()),
        "empty_checksums_valid": bool(empty_read.checksum_valid.all()),
        "empty_abstains": not bool(empty_read.active.any()),
        "strong_write_commits_all_slots": bool(commit.all()),
        "strong_write_golden_vector": written_golden,
        "strong_write_reads_all_slots": bool(written_read.active.all()),
        "strong_write_targets_roundtrip": (
            written_read.prior_logits.argmax(axis=-1).tolist() == [[0, 1, 2, 3]]
        ),
        "single_byte_lesion_invalidates_only_one_slot": (
            corrupted_read.checksum_valid.tolist() == [[False, True, True, True]]
            and corrupted_read.active.tolist() == [[False, True, True, True]]
        ),
        "wrong_content_keeps_addresses_and_checksums": bool(
            wrong_read.address_valid.all() and wrong_read.checksum_valid.all()
        ),
    }
    return {
        "schema": asdict(schema),
        "reference_source": str(reference_source),
        "reference_source_sha256": sha256_file(reference_source),
        "reference_runtime": (
            "not imported: its torch dependency is absent from the NumPy-only "
            "review environment; conformance here is source-transcribed plus golden-byte"
        ),
        "address_table": address_table(schema).tolist(),
        "empty_carrier_hex": empty[0].tobytes(order="C").hex(),
        "empty_carrier_sha256": carrier_digest(empty, schema),
        "written_carrier_hex": written[0].tobytes(order="C").hex(),
        "written_carrier_sha256": carrier_digest(written, schema),
        "wrong_content_targets": wrong_read.prior_logits.argmax(axis=-1).tolist()[0],
        "gates": gates,
        "passes": all(gates.values()),
    }


def _trace_digest(env: DoorKeyEnv) -> str:
    return canonical_digest(env.transition_trace)


def _conditional_chain(rows: Sequence[Mapping[str, Any]], arm: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    prior_event: str | None = None
    for event in CAUSAL_CHAIN:
        eligible = [
            row
            for row in rows
            if prior_event is None or row[f"{arm}_events"][prior_event] is not None
        ]
        reached = [row for row in eligible if row[f"{arm}_events"][event] is not None]
        if prior_event is None:
            lags: list[int] = [
                int(row[f"{arm}_events"][event]) for row in reached
            ]
        else:
            lags = [
                int(row[f"{arm}_events"][event])
                - int(row[f"{arm}_events"][prior_event])
                for row in reached
            ]
        result.append(
            {
                "from": "episode_start" if prior_event is None else prior_event,
                "to": event,
                "eligible": len(eligible),
                "reached": len(reached),
                "censored": len(eligible) - len(reached),
                "conditional_probability": (
                    float(len(reached) / len(eligible)) if eligible else None
                ),
                "median_transition_steps": (
                    float(np.median(lags)) if lags else None
                ),
            }
        )
        prior_event = event
    return result


def qualify_environment(worlds_per_transform: int, max_steps: int) -> dict[str, Any]:
    if worlds_per_transform < 1:
        raise ValueError("worlds_per_transform must be positive")
    rows: list[dict[str, Any]] = []
    for transform_index, transform in enumerate(TRANSFORMS):
        for seed in range(worlds_per_transform):
            layout_seed = 10_000 * transform_index + seed
            layout = make_layout(layout_seed, transform)
            plan = oracle_plan(layout)
            oracle = run_actions(layout, plan, max_steps=max_steps)
            replay = run_actions(layout, plan, max_steps=max_steps)

            random_rng = np.random.default_rng(9_000_000 + layout_seed)
            random_actions = random_rng.integers(0, 8, size=max_steps).tolist()
            random_env = run_actions(layout, random_actions, max_steps=max_steps)
            rows.append(
                {
                    "layout_seed": layout_seed,
                    "transform": transform,
                    "start": list(layout.start),
                    "key": list(layout.key),
                    "door": list(layout.door),
                    "goal": list(layout.goal),
                    "oracle_plan_length": len(plan),
                    "oracle_success": oracle.terminated,
                    "oracle_ordered_chain": oracle.chain_complete_and_ordered(),
                    "oracle_events": dict(oracle.event_steps),
                    "oracle_auxiliary_events": dict(oracle.auxiliary_steps),
                    "oracle_trace_sha256": _trace_digest(oracle),
                    "oracle_replay_sha256": _trace_digest(replay),
                    "oracle_replay_exact": (
                        oracle.state_signature() == replay.state_signature()
                        and oracle.transition_trace == replay.transition_trace
                    ),
                    "random_success": random_env.terminated,
                    "random_ordered_chain": random_env.chain_complete_and_ordered(),
                    "random_events": dict(random_env.event_steps),
                    "random_auxiliary_events": dict(random_env.auxiliary_steps),
                    "random_visited_cells": len(random_env.visited),
                }
            )

    plan_lengths = [int(row["oracle_plan_length"]) for row in rows]
    gates = {
        "all_four_rotations_present": sorted({row["transform"] for row in rows})
        == sorted(TRANSFORMS),
        "all_oracle_runs_reach_goal": all(bool(row["oracle_success"]) for row in rows),
        "all_oracle_chains_strictly_ordered": all(
            bool(row["oracle_ordered_chain"]) for row in rows
        ),
        "all_oracle_replays_exact": all(
            bool(row["oracle_replay_exact"]) for row in rows
        ),
        "all_oracle_plans_within_horizon": max(plan_lengths) < max_steps,
    }
    return {
        "worlds_per_transform": worlds_per_transform,
        "world_count": len(rows),
        "max_steps": max_steps,
        "observation": {
            "view_radius": 1,
            "tile_shape": [3, 3],
            "flat_width": 13,
            "partial_observation": True,
        },
        "action_names": [action.name for action in Action],
        "causal_chain": list(CAUSAL_CHAIN),
        "event_definition_note": (
            "retain_key is the first post-acquisition transition ending with the "
            "key still in inventory; find_door is first visibility after retention"
        ),
        "oracle_plan_length": {
            "min": min(plan_lengths),
            "median": float(np.median(plan_lengths)),
            "max": max(plan_lengths),
        },
        "oracle_successes": sum(bool(row["oracle_success"]) for row in rows),
        "random_successes": sum(bool(row["random_success"]) for row in rows),
        "oracle_conditional_chain": _conditional_chain(rows, "oracle"),
        "random_conditional_chain": _conditional_chain(rows, "random"),
        "gates": gates,
        "passes": all(gates.values()),
        "world_rows": rows,
    }


def qualify_boundary() -> dict[str, Any]:
    schema = GermSchema()
    rulebook = PublicRulebook()
    parent = birth_descendant(
        make_boundary_packet(empty_germ(1, schema), schema), rulebook, 40_000
    )
    cycles: list[dict[str, Any]] = []
    for boundary_index in range(3):
        contaminate_soma(parent, 50_000.0 + boundary_index)
        parent_soma_digests = parent.somatic_digests()
        packet = make_boundary_packet(parent.germ, schema)
        child = birth_descendant(packet, rulebook, 40_001 + boundary_index)
        reset_audit = audit_boundary_reset(parent, child, packet)
        inherited_read = read_germ(child.germ, schema)
        rewritten, commit = write_germ_from_local_evidence(
            _strong_evidence(boundary_index + 1), child.germ, schema
        )
        rewritten_read = read_germ(rewritten, schema)
        cycles.append(
            {
                "boundary": boundary_index + 1,
                "birth_seed": child.birth_seed,
                "public_rulebook_sha256": child.public_rulebook_digest,
                "packet_bytes": len(packet.payload),
                "packet_sha256": packet.digest(),
                "parent_somatic_sha256": parent_soma_digests,
                "child_somatic_sha256": child.somatic_digests(),
                "inherited_active_slots": int(inherited_read.active.sum()),
                "commit_mask": commit.tolist()[0],
                "rewrote_at_least_one_slot": bool(commit.any()),
                "rewrote_all_slots": bool(commit.all()),
                "rewritten_active_slots": int(rewritten_read.active.sum()),
                "rewritten_carrier_sha256": carrier_digest(rewritten, schema),
                "reset_audit": reset_audit,
                "reset_passes": boundary_audit_passes(reset_audit),
            }
        )
        child.germ = rewritten
        parent = child
    gates = {
        "exactly_three_boundaries": len(cycles) == 3,
        "all_packets_exactly_64_bytes": all(
            row["packet_bytes"] == 64 for row in cycles
        ),
        "all_boundaries_reset_full_inventory": all(
            bool(row["reset_passes"]) for row in cycles
        ),
        "all_descendants_rewrite_carrier": all(
            bool(row["rewrote_at_least_one_slot"]) for row in cycles
        ),
        "all_rewritten_carriers_readable": all(
            row["rewritten_active_slots"] == 4 for row in cycles
        ),
        "carrier_changes_across_cycles": len(
            {row["rewritten_carrier_sha256"] for row in cycles}
        )
        == 3,
        "public_rulebook_digest_constant": len(
            {row["public_rulebook_sha256"] for row in cycles}
        )
        == 1
        and all(
            row["public_rulebook_sha256"] == rulebook.digest() for row in cycles
        )
        and all(
            row["reset_audit"]["public_rulebook_unchanged"] for row in cycles
        ),
    }
    return {
        "boundary_count": 3,
        "transmitted_state_allowlist": ["64-byte germ payload"],
        "somatic_destroy_list": [
            "actor parameters",
            "critic parameters",
            "writer parameters",
            "optimizer state",
            "rollout state",
            "recurrent state",
            "normalization state",
            "curriculum state",
            "RNG state",
            "population statistics",
        ],
        "public_rulebook": asdict(rulebook),
        "public_rulebook_sha256": rulebook.digest(),
        "cycle_rows": cycles,
        "gates": gates,
        "passes": all(gates.values()),
        "scope_note": (
            "This is a synthetic boundary leak probe and writer positive control. "
            "The somatic arrays are state-inventory fixtures, not trained PPO state."
        ),
    }


def markdown_report(audit: Mapping[str, Any]) -> str:
    carrier = audit["carrier"]
    environment = audit["environment"]
    boundary = audit["boundary"]
    lines = [
        "# DoorKey Stage-A apparatus qualification",
        "",
        f"**Qualification:** `{'PASS' if audit['overall_pass'] else 'FAIL'}`  ",
        "**Scientific verdict:** `NONE — DEVELOPMENT APPARATUS ONLY`  ",
        "**Learner:** `NONE`",
        "",
        "## Bottom line",
        "",
        "The missing DoorKey substrate now has a deterministic, partially observed 9x9 test world; eight fixed public actions; explicit timestamps for `explore -> find_key -> retain_key -> find_door -> open_door -> reach_goal`; an oracle positive control; and an exclusive boundary constructor whose entire lineage packet is one immutable 64-byte field. This run does not train PPO, compare germ arms, or test heredity.",
        "",
        f"The source-transcribed carrier passed all {len(carrier['gates'])} byte/schema gates. The {environment['world_count']} oracle worlds ({environment['worlds_per_transform']} seeds x four rotations) all reached the goal in strict event order and replayed exactly. Uniform random action is descriptive only: {environment['random_successes']}/{environment['world_count']} reached the goal. Three synthetic hard resets destroyed the declared somatic inventory, transmitted 64 bytes, and let each fresh descendant read and rewrite the carrier.",
        "",
        "## Frozen qualification gates",
        "",
        "| Layer | Gate | Result |",
        "|---|---|---|",
    ]
    for layer, section in (
        ("carrier", carrier),
        ("environment", environment),
        ("boundary", boundary),
    ):
        for name, value in section["gates"].items():
            lines.append(f"| {layer} | `{name}` | `{'PASS' if value else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "## Carrier conformance",
            "",
            f"Reference source: `{carrier['reference_source']}`  ",
            f"Reference SHA-256: `{carrier['reference_source_sha256']}`  ",
            f"Empty carrier SHA-256: `{carrier['empty_carrier_sha256']}`  ",
            f"Strong-write carrier SHA-256: `{carrier['written_carrier_sha256']}`",
            "",
            "The DoorKey code preserves four 16-byte records and eight payload actions. Addresses, payload bytes, trust, freshness, route, and checksum match frozen golden vectors; a one-byte unsealed lesion disables only its record; and a wrong-content permutation keeps addresses and checksums valid. The original PyTorch module was not executed in this environment because Torch is absent. Randomized differential execution against that module remains a Stage-B integration gate; this run establishes source-level and golden-byte conformance, not implementation independence.",
            "",
            "## Causal-chain instrumentation",
            "",
            "| Transition | Oracle reached/eligible | Oracle median steps | Random reached/eligible |",
            "|---|---:|---:|---:|",
        ]
    )
    for oracle_row, random_row in zip(
        environment["oracle_conditional_chain"], environment["random_conditional_chain"]
    ):
        transition = f"{oracle_row['from']} -> {oracle_row['to']}"
        oracle_median = oracle_row["median_transition_steps"]
        oracle_text = "—" if oracle_median is None else f"{oracle_median:.1f}"
        lines.append(
            f"| `{transition}` | {oracle_row['reached']}/{oracle_row['eligible']} | {oracle_text} | {random_row['reached']}/{random_row['eligible']} |"
        )
    lines.extend(
        [
            "",
            f"Oracle plans span {environment['oracle_plan_length']['min']}–{environment['oracle_plan_length']['max']} actions (median {environment['oracle_plan_length']['median']:.1f}) inside the frozen {environment['max_steps']}-step horizon. `retain_key` is operationally the first later transition that ends with the acquired key still in inventory. `find_door` is first door visibility after that retention event. Raw door visibility and key acquisition are also retained as auxiliary timestamps.",
            "",
            "## Vertical boundary",
            "",
            f"Public rulebook SHA-256: `{boundary['public_rulebook_sha256']}`",
            "",
            "| Boundary | Incoming active slots | Packet bytes | Rewritten slots | Reset gate |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for row in boundary["cycle_rows"]:
        lines.append(
            f"| {row['boundary']} | {row['inherited_active_slots']} | {row['packet_bytes']} | {sum(row['commit_mask'])}/4 | `{'PASS' if row['reset_passes'] else 'FAIL'}` |"
        )
    lines.extend(
        [
            "",
            "The birth function accepts only `(packet, public rulebook, birth seed)`; no parent learner object is in its interface. Each parent was marked uniquely in every declared somatic field before birth. Every child had different storage and digests for actor, critic, writer, optimizer, rollout, recurrent, normalization, curriculum, RNG-probe, and population-statistic fixtures, while carrier bytes were exact. The rewrite evidence was synthetic, so this is a plumbing positive control—not learned renewal.",
            "",
            "## What this does not show",
            "",
            "There is no PPO or other learner in Stage A, no terminal-reward credit assignment, no population training, no germ-conditioned behavior, no matched intact/zero/wrong/reversal/ablation/rescue comparison, and no evidence for a learning disposition. The environment currently uses fixed functional object codes. Consequently this output changes no law verdict and cannot be cited as vertical heredity.",
            "",
            "## Next coding gate",
            "",
            "Attach one learner behind the exclusive birth API and inventory its real state. The first developmental comparison should be germ-blind training versus the existing direct action-prior reader, while logging stagewise rewards/values and preserving terminal success as the primary outcome. Before any confirmatory cohort, add randomized byte-for-byte differential tests against the original PyTorch carrier and freeze common-world control arms. Separate value heads and the early-behavior-matched disposition test come only after this baseline learns the task at all.",
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


def run_stage_a(args: argparse.Namespace) -> int:
    started = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id):
        raise ValueError(
            "run ID must contain only letters, digits, dots, underscores, and hyphens"
        )
    output_root = external_root(args.external_root)
    reference_source = Path(args.reference_slot_germ).expanduser().resolve()
    if not reference_source.is_file():
        raise FileNotFoundError(reference_source)
    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {args.run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_preflight(output_root, 4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/DOORKEY_VERTICAL_STAGE_A_APPARATUS_V1.md"
    input_paths = [
        protocol,
        workspace / "src/laws_confirmation/doorkey_carrier.py",
        workspace / "src/laws_confirmation/doorkey_env.py",
        workspace / "src/laws_confirmation/doorkey_boundary.py",
        Path(__file__).resolve(),
        workspace / "tests/test_doorkey_carrier.py",
        workspace / "tests/test_doorkey_env.py",
        workspace / "tests/test_doorkey_boundary.py",
        reference_source,
    ]
    missing = [path for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs: {missing}")
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "DoorKey vertical Stage-A apparatus qualification",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "input_sha256": input_hashes,
        "contract_digest": canonical_digest(input_hashes),
        "repository_head": git_head(workspace),
        "workers": 1,
        "scientific_futures_generated": 0,
        "learner_updates": 0,
        "outcome_status": "development apparatus; no scientific hypothesis test",
        "disk_preflight": disk,
        "environment": environment_manifest(),
        "thread_environment": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }
    atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    atomic_json(
        run_dir / "STATUS.json",
        {"status": "RUNNING", "updated_utc": utc_now()},
        output_root,
    )
    try:
        carrier = qualify_carrier(reference_source)
        environment = qualify_environment(args.worlds_per_transform, args.max_steps)
        boundary = qualify_boundary()
        environment_rows = environment.pop("world_rows")
        audit = {
            "schema_version": 1,
            "run_id": args.run_id,
            "generated_utc": utc_now(),
            "stage": "development apparatus qualification",
            "scientific_futures_generated": 0,
            "learner_updates": 0,
            "carrier": carrier,
            "environment": environment,
            "boundary": boundary,
            "overall_pass": bool(
                carrier["passes"] and environment["passes"] and boundary["passes"]
            ),
        }
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "qualification.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        rows_text = "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in environment_rows
        )
        atomic_text(output_dir / "world_rows.jsonl", rows_text, output_root)
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_paths = [
            output_dir / "qualification.json",
            output_dir / "audit.md",
            output_dir / "world_rows.jsonl",
            output_dir / "input_hashes.sha256",
        ]
        write_hash_manifest(
            output_paths, output_dir / "output_hashes.sha256", output_root
        )
        elapsed = time.monotonic() - started
        completed = {
            "status": "COMPLETE" if audit["overall_pass"] else "FAILED_GATES",
            "completed_utc": utc_now(),
            "elapsed_seconds": elapsed,
            "overall_pass": audit["overall_pass"],
            "output_files": [str(path) for path in output_paths]
            + [str(output_dir / "output_hashes.sha256")],
            "output_bytes": sum(path.stat().st_size for path in output_paths)
            + (output_dir / "output_hashes.sha256").stat().st_size,
            "scientific_futures_generated": 0,
            "learner_updates": 0,
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        sentinel = "COMPLETE" if audit["overall_pass"] else "FAILED"
        atomic_text(run_dir / sentinel, completed["completed_utc"] + "\n", output_root)
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
    parser.add_argument("--worlds-per-transform", type=int, default=32)
    parser.add_argument("--max-steps", type=int, default=128)
    return parser


def main() -> int:
    return run_stage_a(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
