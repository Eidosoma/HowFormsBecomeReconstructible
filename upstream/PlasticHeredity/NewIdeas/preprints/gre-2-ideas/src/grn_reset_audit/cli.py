"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .analysis import analyze
from .atlas import run_atlas, smoke_atlas
from .atlas_analysis import analyze_atlas
from .artifacts import canonical_json, digest, write_json
from .campaign import load_config, run_campaign
from .renewal import renewal_status, run_renewal, smoke_renewal
from .renewal_analysis import analyze_renewal
from .history_renewal import (
    analyze_history_renewal,
    history_renewal_status,
    run_history_renewal,
    smoke_history_renewal,
)
from .ca_bridge import (
    STAGES as CA_BRIDGE_STAGES,
    analyze_ca_bridge,
    ca_bridge_status,
    run_ca_bridge,
    smoke_ca_bridge,
)
from .contingency import (
    analyze_contingency,
    contingency_status,
    run_contingency,
    smoke_contingency,
)
from .exposure_autopsy import (
    analyze_exposure_autopsy,
    exposure_autopsy_status,
    run_exposure_autopsy,
    smoke_exposure_autopsy,
)
from .basin_geometry import (
    analyze_basin_geometry,
    basin_geometry_status,
    run_basin_geometry,
    smoke_basin_geometry,
)
from .constrained_basin import (
    analyze_constrained_basin,
    constrained_basin_status,
    run_constrained_basin,
    smoke_constrained_basin,
)
from .memory_manifold import (
    analyze_memory_manifold,
    memory_manifold_status,
    run_memory_manifold,
    smoke_memory_manifold,
)
from .causal_carrier import (
    analyze_causal_carrier,
    causal_carrier_status,
    run_causal_carrier,
    smoke_causal_carrier,
)
from .carrier_discrimination import (
    analyze_carrier_discrimination,
    carrier_discrimination_status,
    run_carrier_discrimination,
    smoke_carrier_discrimination,
)
from .switch_boundary import (
    analyze_switch_boundary,
    run_switch_boundary,
    smoke_switch_boundary,
    switch_boundary_status,
)
from .engine import (
    JaxBackend,
    historical_release_replay,
    independent_action,
    run_assay_condition,
    source_faithful_replay,
)
from .upstream import (
    PINNED_COMMIT,
    RELEASE_GENERATOR_COMMIT,
    load_memory,
    load_released_task,
    prepare_upstream,
    validate_upstream,
)
from .verification import verify_run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grn-reset-audit")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--destination", type=Path, required=True)

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--upstream", type=Path, required=True)
    smoke.add_argument("--output", type=Path, required=True)
    smoke.add_argument("--target", choices=("head", "historical"), default="head")
    smoke.add_argument("--protocol", type=Path)

    run = sub.add_parser("run")
    run.add_argument("--protocol", type=Path, required=True)
    run.add_argument("--upstream", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--workers", type=int, default=1)

    atlas_smoke = sub.add_parser("atlas-smoke")
    atlas_smoke.add_argument("--protocol", type=Path, required=True)
    atlas_smoke.add_argument("--parent-run", type=Path, required=True)
    atlas_smoke.add_argument("--upstream", type=Path, required=True)
    atlas_smoke.add_argument("--output", type=Path, required=True)

    atlas_run = sub.add_parser("atlas-run")
    atlas_run.add_argument("--protocol", type=Path, required=True)
    atlas_run.add_argument("--parent-run", type=Path, required=True)
    atlas_run.add_argument("--upstream", type=Path, required=True)
    atlas_run.add_argument("--output", type=Path, required=True)
    atlas_run.add_argument("--workers", type=int, default=1)

    atlas_analyze = sub.add_parser("atlas-analyze")
    atlas_analyze.add_argument("--output", type=Path, required=True)
    atlas_analyze.add_argument("--final-status", default="completed")

    atlas_status = sub.add_parser("atlas-status")
    atlas_status.add_argument("--output", type=Path, required=True)

    renewal_smoke = sub.add_parser("renewal-smoke")
    renewal_smoke.add_argument("--protocol", type=Path, required=True)
    renewal_smoke.add_argument("--parent-run", type=Path, required=True)
    renewal_smoke.add_argument("--upstream", type=Path, required=True)
    renewal_smoke.add_argument("--output", type=Path, required=True)

    renewal_run = sub.add_parser("renewal-run")
    renewal_run.add_argument("--protocol", type=Path, required=True)
    renewal_run.add_argument("--parent-run", type=Path, required=True)
    renewal_run.add_argument("--upstream", type=Path, required=True)
    renewal_run.add_argument("--output", type=Path, required=True)
    renewal_run.add_argument("--workers", type=int, default=4)

    renewal_analyze = sub.add_parser("renewal-analyze")
    renewal_analyze.add_argument("--output", type=Path, required=True)
    renewal_analyze.add_argument("--final-status", default="completed")

    renewal_status_parser = sub.add_parser("renewal-status")
    renewal_status_parser.add_argument("--output", type=Path, required=True)

    history_smoke = sub.add_parser("history-renewal-smoke")
    history_smoke.add_argument("--protocol", type=Path, required=True)
    history_smoke.add_argument("--atlas-run", type=Path, required=True)
    history_smoke.add_argument("--renewal-run", type=Path, required=True)
    history_smoke.add_argument("--upstream", type=Path, required=True)
    history_smoke.add_argument("--output", type=Path, required=True)

    history_run = sub.add_parser("history-renewal-run")
    history_run.add_argument("--protocol", type=Path, required=True)
    history_run.add_argument("--atlas-run", type=Path, required=True)
    history_run.add_argument("--renewal-run", type=Path, required=True)
    history_run.add_argument("--upstream", type=Path, required=True)
    history_run.add_argument("--output", type=Path, required=True)
    history_run.add_argument("--workers", type=int, default=2)

    history_analyze = sub.add_parser("history-renewal-analyze")
    history_analyze.add_argument("--output", type=Path, required=True)
    history_analyze.add_argument("--final-status", default="completed")

    history_status = sub.add_parser("history-renewal-status")
    history_status.add_argument("--output", type=Path, required=True)

    ca_bridge_smoke = sub.add_parser("ca-bridge-smoke")
    ca_bridge_smoke.add_argument("--protocol", type=Path, required=True)
    ca_bridge_smoke.add_argument("--stage", choices=CA_BRIDGE_STAGES, required=True)
    ca_bridge_smoke.add_argument("--atlas-run", type=Path, required=True)
    ca_bridge_smoke.add_argument("--parent-run", type=Path)
    ca_bridge_smoke.add_argument("--upstream", type=Path, required=True)
    ca_bridge_smoke.add_argument("--output", type=Path, required=True)

    ca_bridge_run = sub.add_parser("ca-bridge-run")
    ca_bridge_run.add_argument("--protocol", type=Path, required=True)
    ca_bridge_run.add_argument("--stage", choices=CA_BRIDGE_STAGES, required=True)
    ca_bridge_run.add_argument("--atlas-run", type=Path, required=True)
    ca_bridge_run.add_argument("--parent-run", type=Path)
    ca_bridge_run.add_argument("--upstream", type=Path, required=True)
    ca_bridge_run.add_argument("--output", type=Path, required=True)
    ca_bridge_run.add_argument("--workers", type=int, default=4)

    ca_bridge_analyze = sub.add_parser("ca-bridge-analyze")
    ca_bridge_analyze.add_argument("--output", type=Path, required=True)
    ca_bridge_analyze.add_argument("--final-status")

    ca_bridge_status_parser = sub.add_parser("ca-bridge-status")
    ca_bridge_status_parser.add_argument("--output", type=Path, required=True)

    contingency_smoke = sub.add_parser("contingency-smoke")
    contingency_smoke.add_argument("--protocol", type=Path, required=True)
    contingency_smoke.add_argument("--atlas-run", type=Path, required=True)
    contingency_smoke.add_argument("--form-run", type=Path, required=True)
    contingency_smoke.add_argument("--upstream", type=Path, required=True)
    contingency_smoke.add_argument("--output", type=Path, required=True)

    contingency_run = sub.add_parser("contingency-run")
    contingency_run.add_argument("--protocol", type=Path, required=True)
    contingency_run.add_argument("--atlas-run", type=Path, required=True)
    contingency_run.add_argument("--form-run", type=Path, required=True)
    contingency_run.add_argument("--upstream", type=Path, required=True)
    contingency_run.add_argument("--output", type=Path, required=True)
    contingency_run.add_argument("--workers", type=int, default=4)

    contingency_analyze = sub.add_parser("contingency-analyze")
    contingency_analyze.add_argument("--output", type=Path, required=True)
    contingency_analyze.add_argument("--final-status")

    contingency_status_parser = sub.add_parser("contingency-status")
    contingency_status_parser.add_argument("--output", type=Path, required=True)

    exposure_autopsy_smoke = sub.add_parser("exposure-autopsy-smoke")
    exposure_autopsy_smoke.add_argument("--protocol", type=Path, required=True)
    exposure_autopsy_smoke.add_argument("--parent-run", type=Path, required=True)
    exposure_autopsy_smoke.add_argument("--atlas-run", type=Path, required=True)
    exposure_autopsy_smoke.add_argument("--upstream", type=Path, required=True)
    exposure_autopsy_smoke.add_argument("--output", type=Path, required=True)

    exposure_autopsy_run = sub.add_parser("exposure-autopsy-run")
    exposure_autopsy_run.add_argument("--protocol", type=Path, required=True)
    exposure_autopsy_run.add_argument("--parent-run", type=Path, required=True)
    exposure_autopsy_run.add_argument("--atlas-run", type=Path, required=True)
    exposure_autopsy_run.add_argument("--upstream", type=Path, required=True)
    exposure_autopsy_run.add_argument("--output", type=Path, required=True)
    exposure_autopsy_run.add_argument("--workers", type=int, default=4)

    exposure_autopsy_analyze = sub.add_parser("exposure-autopsy-analyze")
    exposure_autopsy_analyze.add_argument("--output", type=Path, required=True)
    exposure_autopsy_analyze.add_argument("--final-status", default="completed")

    exposure_autopsy_status_parser = sub.add_parser("exposure-autopsy-status")
    exposure_autopsy_status_parser.add_argument("--output", type=Path, required=True)

    basin_smoke = sub.add_parser("exposure-basin-smoke")
    basin_smoke.add_argument("--protocol", type=Path, required=True)
    basin_smoke.add_argument("--autopsy-run", type=Path, required=True)
    basin_smoke.add_argument("--exposure-run", type=Path, required=True)
    basin_smoke.add_argument("--atlas-run", type=Path, required=True)
    basin_smoke.add_argument("--upstream", type=Path, required=True)
    basin_smoke.add_argument("--output", type=Path, required=True)

    basin_run = sub.add_parser("exposure-basin-run")
    basin_run.add_argument("--protocol", type=Path, required=True)
    basin_run.add_argument("--autopsy-run", type=Path, required=True)
    basin_run.add_argument("--exposure-run", type=Path, required=True)
    basin_run.add_argument("--atlas-run", type=Path, required=True)
    basin_run.add_argument("--upstream", type=Path, required=True)
    basin_run.add_argument("--output", type=Path, required=True)
    basin_run.add_argument("--workers", type=int, default=4)

    basin_analyze = sub.add_parser("exposure-basin-analyze")
    basin_analyze.add_argument("--output", type=Path, required=True)
    basin_analyze.add_argument("--final-status", default="completed")

    basin_status_parser = sub.add_parser("exposure-basin-status")
    basin_status_parser.add_argument("--output", type=Path, required=True)

    constrained_basin_smoke = sub.add_parser("constrained-basin-smoke")
    constrained_basin_smoke.add_argument("--protocol", type=Path, required=True)
    constrained_basin_smoke.add_argument("--basin-run", type=Path, required=True)
    constrained_basin_smoke.add_argument("--autopsy-run", type=Path, required=True)
    constrained_basin_smoke.add_argument("--exposure-run", type=Path, required=True)
    constrained_basin_smoke.add_argument("--atlas-run", type=Path, required=True)
    constrained_basin_smoke.add_argument("--upstream", type=Path, required=True)
    constrained_basin_smoke.add_argument("--output", type=Path, required=True)

    constrained_basin_run = sub.add_parser("constrained-basin-run")
    constrained_basin_run.add_argument("--protocol", type=Path, required=True)
    constrained_basin_run.add_argument("--basin-run", type=Path, required=True)
    constrained_basin_run.add_argument("--autopsy-run", type=Path, required=True)
    constrained_basin_run.add_argument("--exposure-run", type=Path, required=True)
    constrained_basin_run.add_argument("--atlas-run", type=Path, required=True)
    constrained_basin_run.add_argument("--upstream", type=Path, required=True)
    constrained_basin_run.add_argument("--output", type=Path, required=True)
    constrained_basin_run.add_argument("--workers", type=int, default=4)

    constrained_basin_analyze = sub.add_parser("constrained-basin-analyze")
    constrained_basin_analyze.add_argument("--output", type=Path, required=True)
    constrained_basin_analyze.add_argument("--final-status", default="completed")

    constrained_basin_status_parser = sub.add_parser("constrained-basin-status")
    constrained_basin_status_parser.add_argument("--output", type=Path, required=True)

    manifold_smoke = sub.add_parser("memory-manifold-smoke")
    manifold_smoke.add_argument("--protocol", type=Path, required=True)
    manifold_smoke.add_argument("--parent-run", type=Path, required=True)
    manifold_smoke.add_argument("--atlas-run", type=Path, required=True)
    manifold_smoke.add_argument("--upstream", type=Path, required=True)
    manifold_smoke.add_argument("--output", type=Path, required=True)

    manifold_run = sub.add_parser("memory-manifold-run")
    manifold_run.add_argument("--protocol", type=Path, required=True)
    manifold_run.add_argument("--parent-run", type=Path, required=True)
    manifold_run.add_argument("--atlas-run", type=Path, required=True)
    manifold_run.add_argument("--upstream", type=Path, required=True)
    manifold_run.add_argument("--output", type=Path, required=True)
    manifold_run.add_argument("--workers", type=int, default=4)

    manifold_analyze = sub.add_parser("memory-manifold-analyze")
    manifold_analyze.add_argument("--output", type=Path, required=True)
    manifold_analyze.add_argument("--final-status", default="completed")

    manifold_status_parser = sub.add_parser("memory-manifold-status")
    manifold_status_parser.add_argument("--output", type=Path, required=True)

    causal_smoke = sub.add_parser("causal-carrier-smoke")
    causal_smoke.add_argument("--protocol", type=Path, required=True)
    causal_smoke.add_argument("--manifold-run", type=Path, required=True)
    causal_smoke.add_argument("--constrained-run", type=Path, required=True)
    causal_smoke.add_argument("--contingency-run", type=Path, required=True)
    causal_smoke.add_argument("--atlas-run", type=Path, required=True)
    causal_smoke.add_argument("--upstream", type=Path, required=True)
    causal_smoke.add_argument("--output", type=Path, required=True)

    causal_run = sub.add_parser("causal-carrier-run")
    causal_run.add_argument("--protocol", type=Path, required=True)
    causal_run.add_argument("--manifold-run", type=Path, required=True)
    causal_run.add_argument("--constrained-run", type=Path, required=True)
    causal_run.add_argument("--contingency-run", type=Path, required=True)
    causal_run.add_argument("--atlas-run", type=Path, required=True)
    causal_run.add_argument("--upstream", type=Path, required=True)
    causal_run.add_argument("--output", type=Path, required=True)
    causal_run.add_argument("--workers", type=int, default=4)

    causal_analyze = sub.add_parser("causal-carrier-analyze")
    causal_analyze.add_argument("--output", type=Path, required=True)
    causal_analyze.add_argument("--final-status", default="completed")

    causal_status_parser = sub.add_parser("causal-carrier-status")
    causal_status_parser.add_argument("--output", type=Path, required=True)

    discrimination_smoke = sub.add_parser("carrier-discrimination-smoke")
    discrimination_smoke.add_argument("--protocol", type=Path, required=True)
    discrimination_smoke.add_argument("--v1-run", type=Path, required=True)
    discrimination_smoke.add_argument("--contingency-run", type=Path, required=True)
    discrimination_smoke.add_argument("--atlas-run", type=Path, required=True)
    discrimination_smoke.add_argument("--upstream", type=Path, required=True)
    discrimination_smoke.add_argument("--output", type=Path, required=True)

    discrimination_run = sub.add_parser("carrier-discrimination-run")
    discrimination_run.add_argument("--protocol", type=Path, required=True)
    discrimination_run.add_argument("--v1-run", type=Path, required=True)
    discrimination_run.add_argument("--contingency-run", type=Path, required=True)
    discrimination_run.add_argument("--atlas-run", type=Path, required=True)
    discrimination_run.add_argument("--upstream", type=Path, required=True)
    discrimination_run.add_argument("--output", type=Path, required=True)
    discrimination_run.add_argument("--workers", type=int, default=4)

    discrimination_analyze = sub.add_parser("carrier-discrimination-analyze")
    discrimination_analyze.add_argument("--output", type=Path, required=True)
    discrimination_analyze.add_argument("--final-status", default="completed")

    discrimination_status_parser = sub.add_parser("carrier-discrimination-status")
    discrimination_status_parser.add_argument("--output", type=Path, required=True)

    switch_smoke = sub.add_parser("switch-boundary-smoke")
    switch_smoke.add_argument("--protocol", type=Path, required=True)
    switch_smoke.add_argument("--discrimination-run", type=Path, required=True)
    switch_smoke.add_argument("--contingency-run", type=Path, required=True)
    switch_smoke.add_argument("--atlas-run", type=Path, required=True)
    switch_smoke.add_argument("--upstream", type=Path, required=True)
    switch_smoke.add_argument("--output", type=Path, required=True)

    switch_run = sub.add_parser("switch-boundary-run")
    switch_run.add_argument("--protocol", type=Path, required=True)
    switch_run.add_argument("--discrimination-run", type=Path, required=True)
    switch_run.add_argument("--contingency-run", type=Path, required=True)
    switch_run.add_argument("--atlas-run", type=Path, required=True)
    switch_run.add_argument("--upstream", type=Path, required=True)
    switch_run.add_argument("--output", type=Path, required=True)
    switch_run.add_argument("--workers", type=int, default=4)

    switch_analyze = sub.add_parser("switch-boundary-analyze")
    switch_analyze.add_argument("--output", type=Path, required=True)
    switch_analyze.add_argument("--final-status", default="completed")

    switch_status_parser = sub.add_parser("switch-boundary-status")
    switch_status_parser.add_argument("--output", type=Path, required=True)

    status = sub.add_parser("status")
    status.add_argument("--output", type=Path, required=True)

    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("--output", type=Path, required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--output", type=Path, required=True)
    verify.add_argument("--allow-unsealed", action="store_true")
    return parser


def smoke(
    upstream: Path,
    output: Path,
    target: str = "head",
    protocol: Path | None = None,
) -> dict[str, object]:
    validate_upstream(upstream)
    protocol_digest = None
    if target == "historical":
        if protocol is None:
            raise ValueError("historical smoke requires its frozen protocol")
        config = load_config(protocol)
        if config.get("source_semantics") != "historical-release":
            raise ValueError("historical smoke received a non-historical protocol")
        protocol_digest = digest(config)
    # Direct fixtures avoid spending development time unpickling the full corpus.
    # Both are fast model-10 tasks with a released positive; one is learned-UP
    # and the other learned-DOWN.
    chosen = [
        load_released_task(upstream, "10-1-10"),
        load_released_task(upstream, "10-0-10"),
    ]
    records = []
    assay_probe = None
    known_nonfinite_probe = None
    head_backends = {}
    historical_backends = {}
    for released in chosen:
        memory = load_memory(released.memory_path, released.key)
        backend = head_backends.setdefault(
            released.key.model_id, JaxBackend(upstream, released.key.model_id)
        )
        source = source_faithful_replay(backend, memory)
        historical_backend = historical_backends.setdefault(
            released.key.model_id,
            JaxBackend(upstream, released.key.model_id, delta_t=0.01),
        )
        historical = historical_release_replay(historical_backend, memory)
        action_index = released.released_positive_indices[0]
        if target == "historical":
            corrected, _ = independent_action(
                historical_backend,
                memory,
                action_index,
                phase_duration=2500.0,
                pulse_count=5,
            )
            if assay_probe is None:
                naive = historical_backend.naive_at_time(
                    10000.0,
                    memory.key.response_id,
                    sample_count=11,
                    chunk_duration=2500.0,
                )
                probe = run_assay_condition(
                    historical_backend,
                    memory,
                    action_index,
                    "combined_reset",
                    2500.0,
                    naive.state,
                    sample_count=11,
                    phase_duration=2500.0,
                    pulse_count=5,
                    washout_chunk_duration=2500.0,
                    time_match_reset_slot=True,
                )
                assay_probe = {
                    "task_id": released.key.task_id,
                    "valid": probe["valid"],
                    "washout_duration": probe["washout_duration"],
                    "reset_is_broken": probe["reset_is_broken"],
                    "challenge_is_broken": probe["challenge_is_broken"],
                    "cpu_seconds": probe["cpu_seconds"],
                    "wall_seconds": probe["wall_seconds"],
                }
        else:
            corrected, _ = independent_action(backend, memory, action_index)
        head_agreement = sum(
            row["is_broken"] == expected.is_broken
            for row, expected in zip(source, released.actions, strict=True)
        ) / len(source)
        historical_agreement = sum(
            row["is_broken"] == expected.is_broken
            for row, expected in zip(historical, released.actions, strict=True)
        ) / len(historical)
        historical_all_valid = all(bool(row["valid"]) for row in historical)
        historical_reward_errors = [
            abs(float(row["reward"]) - float(expected.reward))
            for row, expected in zip(historical, released.actions, strict=True)
            if expected.reward is not None
        ]
        records.append(
            {
                "task_id": released.key.task_id,
                "direction": memory.response_reg,
                "source_row_count": len(source),
                "head_is_broken_agreement": head_agreement,
                "historical_is_broken_agreement": historical_agreement,
                "historical_all_valid": historical_all_valid,
                "historical_max_reward_abs_error": max(historical_reward_errors),
                "corrected_action": corrected,
            }
        )
    if target == "historical":
        # V3 reached this deterministic model-69 condition and correctly
        # marked its trajectory invalid, but ndarray NaNs then broke JSONL
        # serialization. Exercise that exact biological and artifact path in
        # every amended-image preflight.
        released = load_released_task(upstream, "69-0-2")
        memory = load_memory(released.memory_path, released.key)
        backend = JaxBackend(upstream, released.key.model_id, delta_t=0.01)
        probe = run_assay_condition(
            backend,
            memory,
            1,
            "control_only",
            0.0,
            backend.memory_state(memory),
            sample_count=11,
            phase_duration=2500.0,
            pulse_count=5,
            washout_chunk_duration=2500.0,
            time_match_reset_slot=True,
        )
        round_trip = json.loads(canonical_json(probe))

        def count_nulls(value: object) -> int:
            if value is None:
                return 1
            if isinstance(value, dict):
                return sum(count_nulls(item) for item in value.values())
            if isinstance(value, list):
                return sum(count_nulls(item) for item in value)
            return 0

        null_count = count_nulls(round_trip)
        known_nonfinite_probe = {
            "task_id": released.key.task_id,
            "action_index": 1,
            "arm": "control_only",
            "washout_duration": 0.0,
            "valid": probe["valid"],
            "strict_json_round_trip": True,
            "null_leaf_count": null_count,
            "pass": probe["valid"] is False and null_count > 0,
        }
    head_pass = all(row["head_is_broken_agreement"] >= 0.99 for row in records)
    historical_pass = all(
        row["historical_is_broken_agreement"] == 1.0
        and row["historical_all_valid"]
        and row["historical_max_reward_abs_error"] <= 1e-5
        for row in records
    )
    target_pass = (
        head_pass
        if target == "head"
        else historical_pass
        and bool(assay_probe and assay_probe["valid"])
        and bool(known_nonfinite_probe and known_nonfinite_probe["pass"])
    )
    result = {
        "target": target,
        "container_image_id": os.environ.get("EXPERIMENT_IMAGE_ID", "unknown"),
        "protocol_digest": protocol_digest,
        "pass": target_pass,
        "production_launch_allowed": target_pass,
        "historical_release_compatible": historical_pass,
        "diagnosis": (
            "released CSVs reproduce under the 2024 generator, not pinned HEAD"
            if historical_pass and not head_pass
            else "no semantic-version diagnosis established"
        ),
        "head_semantics": {
            "commit": PINNED_COMMIT,
            "duration": 100.0,
            "delta_t": 0.1,
            "pulse_count": 1,
            "candidate_start": "sequential-until-termination",
        },
        "historical_release_semantics": {
            "commit": RELEASE_GENERATOR_COMMIT,
            "duration": 2500.0,
            "delta_t": 0.01,
            "pulse_count": 5,
            "candidate_start": "independent-via-termination",
        },
        "assay_probe": assay_probe,
        "known_nonfinite_probe": known_nonfinite_probe,
        "records": records,
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "smoke.json", result)
    return result


def status(output: Path) -> dict[str, object]:
    result: dict[str, object] = {"output": str(output.resolve())}
    for name in ("state.json", "cpu-ledger.json", "source-gate.json", "continuation-gate.json"):
        path = output / name
        if path.is_file():
            result[name.removesuffix(".json")] = json.loads(path.read_text(encoding="utf-8"))
    for name in ("source-replay", "independent-correction", "washout", "sentinel-exhaustive"):
        path = output / f"{name}.jsonl"
        if path.is_file():
            result[f"{name}_records"] = sum(1 for line in path.open(encoding="utf-8") if line.strip())
    return result


def atlas_status(output: Path) -> dict[str, object]:
    result: dict[str, object] = {"output": str(output.resolve())}
    for name in (
        "state",
        "cpu-ledger",
        "parent-gate",
        "calibration-gate",
        "analysis",
    ):
        path = output / f"{name}.json"
        if path.is_file():
            result[name.replace("-", "_")] = json.loads(
                path.read_text(encoding="utf-8")
            )
    for name in (
        "calibration",
        "histories",
        "probes",
        "reinstatement",
        "relearning",
        "observer-scores",
        "mechanism-labels",
    ):
        path = output / f"{name}.jsonl"
        if path.is_file():
            result[f"{name.replace('-', '_')}_records"] = sum(
                1 for line in path.open(encoding="utf-8") if line.strip()
            )
    result["sealed"] = (output / "SHA256SUMS").is_file()
    return result


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "prepare":
        print(json.dumps(prepare_upstream(args.destination, PINNED_COMMIT), indent=2))
        return 0
    if args.command == "smoke":
        result = smoke(
            args.upstream,
            args.output,
            target=args.target,
            protocol=args.protocol,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "run":
        return run_campaign(args.protocol, args.upstream, args.output, workers=args.workers)
    if args.command == "atlas-smoke":
        result = smoke_atlas(
            args.protocol, args.parent_run, args.upstream, args.output
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "atlas-run":
        return run_atlas(
            args.protocol,
            args.parent_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "atlas-analyze":
        print(
            json.dumps(
                analyze_atlas(args.output, final_status=args.final_status), indent=2
            )
        )
        return 0
    if args.command == "atlas-status":
        print(json.dumps(atlas_status(args.output), indent=2))
        return 0
    if args.command == "renewal-smoke":
        result = smoke_renewal(
            args.protocol, args.parent_run, args.upstream, args.output
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "renewal-run":
        return run_renewal(
            args.protocol,
            args.parent_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "renewal-analyze":
        print(
            json.dumps(
                analyze_renewal(args.output, final_status=args.final_status), indent=2
            )
        )
        return 0
    if args.command == "renewal-status":
        print(json.dumps(renewal_status(args.output), indent=2))
        return 0
    if args.command == "history-renewal-smoke":
        result = smoke_history_renewal(
            args.protocol,
            args.atlas_run,
            args.renewal_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "history-renewal-run":
        return run_history_renewal(
            args.protocol,
            args.atlas_run,
            args.renewal_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "history-renewal-analyze":
        print(
            json.dumps(
                analyze_history_renewal(args.output, final_status=args.final_status),
                indent=2,
            )
        )
        return 0
    if args.command == "history-renewal-status":
        print(json.dumps(history_renewal_status(args.output), indent=2))
        return 0
    if args.command == "ca-bridge-smoke":
        result = smoke_ca_bridge(
            args.protocol,
            args.stage,
            args.atlas_run,
            args.parent_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "ca-bridge-run":
        return run_ca_bridge(
            args.protocol,
            args.stage,
            args.atlas_run,
            args.parent_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "ca-bridge-analyze":
        print(
            json.dumps(
                analyze_ca_bridge(args.output, final_status=args.final_status), indent=2
            )
        )
        return 0
    if args.command == "ca-bridge-status":
        print(json.dumps(ca_bridge_status(args.output), indent=2))
        return 0
    if args.command == "contingency-smoke":
        result = smoke_contingency(
            args.protocol,
            args.atlas_run,
            args.form_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "contingency-run":
        return run_contingency(
            args.protocol,
            args.atlas_run,
            args.form_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "contingency-analyze":
        print(
            json.dumps(
                analyze_contingency(args.output, final_status=args.final_status),
                indent=2,
            )
        )
        return 0
    if args.command == "contingency-status":
        print(json.dumps(contingency_status(args.output), indent=2))
        return 0
    if args.command == "exposure-autopsy-smoke":
        result = smoke_exposure_autopsy(
            args.protocol,
            args.parent_run,
            args.atlas_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "exposure-autopsy-run":
        return run_exposure_autopsy(
            args.protocol,
            args.parent_run,
            args.atlas_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "exposure-autopsy-analyze":
        print(
            json.dumps(
                analyze_exposure_autopsy(
                    args.output, final_status=args.final_status
                ),
                indent=2,
            )
        )
        return 0
    if args.command == "exposure-autopsy-status":
        print(json.dumps(exposure_autopsy_status(args.output), indent=2))
        return 0
    if args.command == "exposure-basin-smoke":
        result = smoke_basin_geometry(
            args.protocol,
            args.autopsy_run,
            args.exposure_run,
            args.atlas_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "exposure-basin-run":
        return run_basin_geometry(
            args.protocol,
            args.autopsy_run,
            args.exposure_run,
            args.atlas_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "exposure-basin-analyze":
        print(
            json.dumps(
                analyze_basin_geometry(args.output, final_status=args.final_status),
                indent=2,
            )
        )
        return 0
    if args.command == "exposure-basin-status":
        print(json.dumps(basin_geometry_status(args.output), indent=2))
        return 0
    if args.command == "constrained-basin-smoke":
        result = smoke_constrained_basin(
            args.protocol,
            args.basin_run,
            args.autopsy_run,
            args.exposure_run,
            args.atlas_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "constrained-basin-run":
        return run_constrained_basin(
            args.protocol,
            args.basin_run,
            args.autopsy_run,
            args.exposure_run,
            args.atlas_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "constrained-basin-analyze":
        print(
            json.dumps(
                analyze_constrained_basin(args.output, final_status=args.final_status),
                indent=2,
            )
        )
        return 0
    if args.command == "constrained-basin-status":
        print(json.dumps(constrained_basin_status(args.output), indent=2))
        return 0
    if args.command == "memory-manifold-smoke":
        result = smoke_memory_manifold(
            args.protocol,
            args.parent_run,
            args.atlas_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "memory-manifold-run":
        return run_memory_manifold(
            args.protocol,
            args.parent_run,
            args.atlas_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "memory-manifold-analyze":
        print(
            json.dumps(
                analyze_memory_manifold(args.output, final_status=args.final_status),
                indent=2,
            )
        )
        return 0
    if args.command == "memory-manifold-status":
        print(json.dumps(memory_manifold_status(args.output), indent=2))
        return 0
    if args.command == "causal-carrier-smoke":
        result = smoke_causal_carrier(
            args.protocol,
            args.manifold_run,
            args.constrained_run,
            args.contingency_run,
            args.atlas_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "causal-carrier-run":
        return run_causal_carrier(
            args.protocol,
            args.manifold_run,
            args.constrained_run,
            args.contingency_run,
            args.atlas_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "causal-carrier-analyze":
        print(
            json.dumps(
                analyze_causal_carrier(args.output, final_status=args.final_status),
                indent=2,
            )
        )
        return 0
    if args.command == "causal-carrier-status":
        print(json.dumps(causal_carrier_status(args.output), indent=2))
        return 0
    if args.command == "carrier-discrimination-smoke":
        result = smoke_carrier_discrimination(
            args.protocol,
            args.v1_run,
            args.contingency_run,
            args.atlas_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "carrier-discrimination-run":
        return run_carrier_discrimination(
            args.protocol,
            args.v1_run,
            args.contingency_run,
            args.atlas_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "carrier-discrimination-analyze":
        print(
            json.dumps(
                analyze_carrier_discrimination(
                    args.output, final_status=args.final_status
                ),
                indent=2,
            )
        )
        return 0
    if args.command == "carrier-discrimination-status":
        print(json.dumps(carrier_discrimination_status(args.output), indent=2))
        return 0
    if args.command == "switch-boundary-smoke":
        result = smoke_switch_boundary(
            args.protocol,
            args.discrimination_run,
            args.contingency_run,
            args.atlas_run,
            args.upstream,
            args.output,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    if args.command == "switch-boundary-run":
        return run_switch_boundary(
            args.protocol,
            args.discrimination_run,
            args.contingency_run,
            args.atlas_run,
            args.upstream,
            args.output,
            workers=args.workers,
        )
    if args.command == "switch-boundary-analyze":
        print(
            json.dumps(
                analyze_switch_boundary(args.output, final_status=args.final_status),
                indent=2,
            )
        )
        return 0
    if args.command == "switch-boundary-status":
        print(json.dumps(switch_boundary_status(args.output), indent=2))
        return 0
    if args.command == "status":
        print(json.dumps(status(args.output), indent=2))
        return 0
    if args.command == "analyze":
        print(json.dumps(analyze(args.output), indent=2))
        return 0
    if args.command == "verify":
        print(
            json.dumps(
                verify_run(args.output, require_sealed=not args.allow_unsealed), indent=2
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
