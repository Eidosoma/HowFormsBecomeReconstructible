#!/usr/bin/env python3
"""Seal and execute Experiment 2's pre-analysis terminal-shortfall amendment.

This module is deliberately outside ``fep_surprise_2`` so the originally
registered scientific source tree remains byte-for-byte unchanged.  The
amendment seals this file and its policy document before replay or analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
if str(CAMPAIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(CAMPAIGN_ROOT))

from fep_surprise_15.integrity import (  # noqa: E402
    atomic_destination,
    canonical_digest,
    sha256_file,
    verify_checksums,
    write_checksums,
)
from fep_surprise_2 import campaign as campaign2  # noqa: E402
from fep_surprise_2.analysis import analyze_confirmation  # noqa: E402
from fep_surprise_2.config import ARMS, Campaign2Config, profile_config  # noqa: E402
from fep_surprise_2.worker import load_design, load_futures  # noqa: E402


FORMAT = "fep-surprise-2-terminal-shortfall-amendment-v1"
AMENDMENT_DIRECTORY = "amendment_1"
AMENDMENT_DOCUMENT = CAMPAIGN_ROOT / "EXPERIMENT_2_AMENDMENT_1.md"
AMENDMENT_SOURCE_NAMES = (
    "EXPERIMENT_2_AMENDMENT_1.md",
    "scripts/amend_experiment_2_terminal_shortfalls.py",
    "scripts/run_experiment_2_amended_campaign.sh",
    "scripts/run_experiment_2_amended_detached.sh",
)


def _amendment_sources() -> dict[str, str]:
    paths = {name: CAMPAIGN_ROOT / name for name in AMENDMENT_SOURCE_NAMES}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"amendment source files are absent: {missing}")
    return {name: sha256_file(path) for name, path in sorted(paths.items())}


def _resolution_status(
    complete: np.ndarray, trace_lengths: np.ndarray, horizon: int
) -> dict[str, Any]:
    raw = np.asarray(complete)
    lengths = np.asarray(trace_lengths)
    if raw.shape != lengths.shape:
        raise ValueError("completion and trace-length arrays differ in shape")
    if not bool(np.isin(raw, (0, 1)).all()):
        raise ValueError("completion array contains values outside {0,1}")
    if not np.issubdtype(lengths.dtype, np.integer):
        raise ValueError("trace-length array must contain integers")
    if not isinstance(horizon, (int, np.integer)) or int(horizon) <= 0:
        raise ValueError("future horizon must be a positive integer")
    horizon = int(horizon)
    reached = raw.astype(bool)
    invalid_reached = reached & (lengths != horizon)
    invalid_terminal = (~reached) & ((lengths < 0) | (lengths >= horizon))
    if bool(invalid_reached.any() or invalid_terminal.any()):
        raise ValueError(
            "future resolution is inconsistent with the frozen horizon: "
            f"reached={np.argwhere(invalid_reached)[:8].tolist()} "
            f"terminal={np.argwhere(invalid_terminal)[:8].tolist()}"
        )
    return {
        "all_attempts_resolved": True,
        "all_streams_reached_horizon": bool(reached.all()),
        "terminal_indices": np.argwhere(~reached),
    }


def audit_terminal_shortfalls(
    confirmation: Path, config: Campaign2Config
) -> dict[str, Any]:
    jobs = campaign2._jobs(confirmation, "confirmation", config)
    scale = config.confirmation
    expected_shape = (len(scale.landmarks), len(ARMS), scale.branches)
    no_op = ARMS.index("NOOP")
    isomorphic = ARMS.index("ISOMORPHIC_BOTH_100")
    terminal_entries: list[dict[str, Any]] = []
    all_reference_lineages_retained = True
    pathwise_terminal_control_exact = True

    for spec in jobs:
        required = (
            spec.design_path,
            spec.atlas_path,
            spec.metadata_path,
            spec.future_path,
        )
        if not all(path.is_file() for path in required):
            missing = [str(path) for path in required if not path.is_file()]
            raise FileNotFoundError(f"confirmation cell artifacts are absent: {missing}")
        design = load_design(spec.design_path)
        future = load_futures(spec.future_path)
        if int(design["metadata"]["matrix_id"]) != spec.matrix_id:
            raise ValueError(f"matrix metadata mismatch in {spec.design_path.name}")
        if str(design["metadata"]["candidate"]) != spec.candidate:
            raise ValueError(f"candidate metadata mismatch in {spec.design_path.name}")
        if tuple(future["arms"]) != tuple(ARMS):
            raise ValueError(f"arm contract mismatch in {spec.future_path.name}")
        if tuple(int(value) for value in future["landmarks"]) != scale.landmarks:
            raise ValueError(f"landmark contract mismatch in {spec.future_path.name}")
        for name in (
            "strict8",
            "f12",
            "first_break",
            "complete",
            "trace_lengths",
            "destination",
        ):
            if np.asarray(future[name]).shape != expected_shape:
                raise ValueError(
                    f"{name} shape mismatch in {spec.future_path.name}: "
                    f"{np.asarray(future[name]).shape} != {expected_shape}"
                )
        all_reference_lineages_retained &= all(
            item["completed_lineages"] == item["requested_lineages"]
            for item in design["metadata"]["reference"].values()
        )
        resolution = _resolution_status(
            future["complete"], future["trace_lengths"], scale.horizon
        )
        complete = np.asarray(future["complete"], dtype=bool)
        lengths = np.asarray(future["trace_lengths"], dtype=np.int64)
        pathwise_terminal_control_exact &= bool(
            np.array_equal(complete[:, no_op, :], complete[:, isomorphic, :])
            and np.array_equal(lengths[:, no_op, :], lengths[:, isomorphic, :])
        )
        for landmark_index, arm_index, branch in resolution["terminal_indices"]:
            terminal_entries.append(
                {
                    "artifact": str(spec.future_path.relative_to(confirmation)),
                    "candidate": spec.candidate,
                    "matrix": spec.matrix_id,
                    "landmark": int(scale.landmarks[int(landmark_index)]),
                    "arm": ARMS[int(arm_index)],
                    "branch": int(branch),
                    "prefix_fissions": int(
                        lengths[int(landmark_index), int(arm_index), int(branch)]
                    ),
                }
            )

    expected_entries = len(jobs) * int(np.prod(expected_shape))
    distinct_paths = {
        (
            item["candidate"],
            item["matrix"],
            item["landmark"],
            "NOOP"
            if item["arm"] in ("NOOP", "ISOMORPHIC_BOTH_100")
            else item["arm"],
            item["branch"],
        )
        for item in terminal_entries
    }
    return {
        "format": "fep-surprise-2-terminal-audit-v1",
        "profile": config.profile,
        "expected_cell_count": len(jobs),
        "expected_future_entries": expected_entries,
        "all_cell_artifacts_present": True,
        "all_reference_lineages_retained": bool(all_reference_lineages_retained),
        "all_attempts_resolved": True,
        "outcome_shapes_exact": True,
        "pathwise_terminal_control_exact": bool(pathwise_terminal_control_exact),
        "all_streams_reached_horizon": not terminal_entries,
        "terminal_entry_count": len(terminal_entries),
        "distinct_terminal_stochastic_paths": len(distinct_paths),
        "terminal_fraction": len(terminal_entries) / expected_entries,
        "terminal_entries": terminal_entries,
    }


def _amendment_path(run_root: Path, profile: str) -> Path:
    return campaign2.profile_path(run_root, profile) / AMENDMENT_DIRECTORY


def _read_metadata(root: Path, name: str) -> str | None:
    path = root / name
    return path.read_text(encoding="utf-8").strip() if path.is_file() else None


def seal_amendment(run_root: Path, config: Campaign2Config) -> Path:
    root = campaign2.profile_path(run_root, config.profile)
    destination = _amendment_path(run_root, config.profile)
    if destination.exists():
        verify_amendment(run_root, config)
        return destination

    registration_path = campaign2.registration_path(run_root, config.profile)
    development_path = campaign2.development_path(run_root, config.profile)
    confirmation_path = campaign2.confirmation_path(run_root, config.profile)
    registration = campaign2.verify_registration(registration_path, config)
    development = campaign2.verify_development(
        development_path, registration_path, config
    )
    confirmation_design = campaign2.verify_confirmation_design(
        confirmation_path, registration_path, development_path, config
    )
    if (confirmation_path / "SHA256SUMS").exists():
        raise FileExistsError("confirmation was already sealed before amendment")
    if campaign2.replay_path(run_root, config.profile).exists():
        raise FileExistsError("confirmation replay exists before amendment")
    if campaign2.analysis_path(run_root, config.profile).exists():
        raise FileExistsError("scientific analysis exists before amendment")

    audit = audit_terminal_shortfalls(confirmation_path, config)
    required = (
        audit["all_cell_artifacts_present"],
        audit["all_reference_lineages_retained"],
        audit["all_attempts_resolved"],
        audit["outcome_shapes_exact"],
        audit["pathwise_terminal_control_exact"],
        audit["terminal_entry_count"] > 0,
    )
    if not all(required):
        raise ValueError(f"terminal-shortfall amendment gate failed: {audit}")

    payload: dict[str, Any] = {
        "format": FORMAT,
        "status": (
            "sealed_after_confirmation_generation_before_confirmation_seal_"
            "replay_or_analysis"
        ),
        "profile": config.profile,
        "registration_id": registration["registration_id"],
        "development_id": development["development_id"],
        "confirmation_design_id": confirmation_design["confirmation_design_id"],
        "policy_document": AMENDMENT_DOCUMENT.name,
        "policy": {
            "retain_every_attempt": True,
            "retry_or_replacement_forbidden": True,
            "terminal_prefix_endpoints_retained": True,
            "terminal_failure_is_not_a_compositional_break": True,
            "no_observed_break_latency_remains_f32": True,
            "exact_terminal_map_replay_required": True,
            "integrity_label": "VALID_WITH_PREANALYSIS_AMENDMENT",
        },
        "observation_boundary": (
            "Only runner/integrity metadata and the three terminal entries' "
            "completion flags, prefix lengths, and endpoint fields were viewed; "
            "no aggregate outcomes, predictions, gates, destinations, or verdict "
            "were computed before sealing this amendment."
        ),
        "terminal_audit_digest": canonical_digest(audit),
        "amendment_sources": _amendment_sources(),
        "original_runner": {
            "status": _read_metadata(root, "experiment2.status"),
            "pid": _read_metadata(root, "experiment2.pid"),
            "session": _read_metadata(root, "experiment2.session"),
            "started": _read_metadata(root, "experiment2.started"),
            "finished": _read_metadata(root, "experiment2.finished"),
            "log_sha256_at_amendment": sha256_file(root / "experiment2.log"),
        },
    }
    payload["amendment_id"] = canonical_digest(payload)
    with atomic_destination(destination) as output:
        (output / "terminal_audit.json").write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "amendment.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "README.md").write_text(
            "# Sealed Experiment 2 pre-analysis amendment 1\n\n"
            f"Amendment ID: `{payload['amendment_id']}`\n\n"
            "This seal retains terminal simulator attempts without retry and "
            "requires exact replay before amended analysis.\n",
            encoding="utf-8",
        )
        write_checksums(output)
    return destination


def verify_amendment(run_root: Path, config: Campaign2Config) -> dict[str, Any]:
    path = _amendment_path(run_root, config.profile)
    verify_checksums(path)
    payload = json.loads((path / "amendment.json").read_text(encoding="utf-8"))
    identifier = payload.pop("amendment_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("amendment identifier mismatch")
    payload["amendment_id"] = identifier
    if payload.get("format") != FORMAT or payload.get("profile") != config.profile:
        raise ValueError("unsupported amendment or profile")
    if payload["amendment_sources"] != _amendment_sources():
        raise ValueError("amendment source changed after sealing")

    registration_path = campaign2.registration_path(run_root, config.profile)
    development_path = campaign2.development_path(run_root, config.profile)
    confirmation_path = campaign2.confirmation_path(run_root, config.profile)
    registration = campaign2.verify_registration(registration_path, config)
    development = campaign2.verify_development(
        development_path, registration_path, config
    )
    confirmation_design = campaign2.verify_confirmation_design(
        confirmation_path, registration_path, development_path, config
    )
    if payload["registration_id"] != registration["registration_id"]:
        raise ValueError("amendment references another registration")
    if payload["development_id"] != development["development_id"]:
        raise ValueError("amendment references another development seal")
    if payload["confirmation_design_id"] != confirmation_design["confirmation_design_id"]:
        raise ValueError("amendment references another confirmation design")
    audit = audit_terminal_shortfalls(confirmation_path, config)
    if payload["terminal_audit_digest"] != canonical_digest(audit):
        raise ValueError("terminal audit changed after amendment sealing")
    sealed_audit = json.loads(
        (path / "terminal_audit.json").read_text(encoding="utf-8")
    )
    if sealed_audit != audit:
        raise ValueError("terminal audit payload differs from its seal")
    return {"seal": payload, "audit": audit}


def seal_confirmation_under_amendment(
    run_root: Path, config: Campaign2Config
) -> Path:
    amendment = verify_amendment(run_root, config)
    registration_path = campaign2.registration_path(run_root, config.profile)
    development_path = campaign2.development_path(run_root, config.profile)
    output = campaign2.confirmation_path(run_root, config.profile)
    confirmation_design = campaign2.verify_confirmation_design(
        output, registration_path, development_path, config
    )
    if (output / "SHA256SUMS").exists():
        payload = campaign2.verify_confirmation(
            output, registration_path, development_path, config
        )
        if payload.get("amendment_id") != amendment["seal"]["amendment_id"]:
            raise ValueError("confirmation was sealed under another policy")
        return output

    jobs = campaign2._jobs(output, "confirmation", config)
    if (output / "futures_manifest.json").exists():
        future_manifest = campaign2._verify_manifest(output, "futures", len(jobs))
    else:
        future_manifest = campaign2._write_manifest(output, "futures", len(jobs))
    audit = amendment["audit"]
    cohort = {
        "expected_cell_count": bool(audit["all_cell_artifacts_present"]),
        "all_reference_lineages_retained": bool(
            audit["all_reference_lineages_retained"]
        ),
        "all_future_attempts_resolved": bool(audit["all_attempts_resolved"]),
        "outcome_shapes_exact": bool(audit["outcome_shapes_exact"]),
        "pathwise_terminal_control_exact": bool(
            audit["pathwise_terminal_control_exact"]
        ),
        "all_future_streams_reached_horizon": bool(
            audit["all_streams_reached_horizon"]
        ),
        "terminal_entry_count": int(audit["terminal_entry_count"]),
        "distinct_terminal_stochastic_paths": int(
            audit["distinct_terminal_stochastic_paths"]
        ),
    }
    payload: dict[str, Any] = {
        "format": "fep-surprise-2-confirmation-v1",
        "status": (
            "sealed_outcomes_before_replay_under_preanalysis_terminal_"
            "shortfall_amendment"
        ),
        "confirmation_design_id": confirmation_design["confirmation_design_id"],
        "futures_id": future_manifest["futures_id"],
        "cells": len(jobs),
        "cohort_integrity": cohort,
        "analysis_artifacts_present": False,
        "amendment_id": amendment["seal"]["amendment_id"],
        "terminal_audit_digest": amendment["seal"]["terminal_audit_digest"],
    }
    payload["confirmation_id"] = canonical_digest(payload)
    (output / "confirmation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(output)
    return output


def _terminal_endpoint_summary(
    confirmation: Path, audit: dict[str, Any]
) -> dict[str, Any]:
    values = []
    for item in audit["terminal_entries"]:
        future = load_futures(confirmation / item["artifact"])
        landmark_index = list(int(value) for value in future["landmarks"]).index(
            int(item["landmark"])
        )
        arm_index = list(future["arms"]).index(item["arm"])
        branch = int(item["branch"])
        values.append(
            {
                **item,
                "strict8": int(future["strict8"][landmark_index, arm_index, branch]),
                "f12": int(future["f12"][landmark_index, arm_index, branch]),
                "first_break": int(
                    future["first_break"][landmark_index, arm_index, branch]
                ),
            }
        )
    return {
        "primary_policy": (
            "Retain observed prefixes; certify endpoints only within observed "
            "fissions; terminal failure is not redefined as a compositional break."
        ),
        "entries": values,
        "strict8_positive": sum(item["strict8"] for item in values),
        "f12_positive": sum(item["f12"] for item in values),
        "observed_breaks": sum(item["first_break"] >= 0 for item in values),
        "maximum_global_rate_contribution": len(values)
        / int(audit["expected_future_entries"]),
    }


def analyze_under_amendment(run_root: Path, config: Campaign2Config) -> Path:
    amendment = verify_amendment(run_root, config)
    registration_path = campaign2.registration_path(run_root, config.profile)
    development_path = campaign2.development_path(run_root, config.profile)
    confirmation_path = campaign2.confirmation_path(run_root, config.profile)
    replay_path = campaign2.replay_path(run_root, config.profile)
    registration = campaign2.verify_registration(registration_path, config)
    development = campaign2.verify_development(
        development_path, registration_path, config
    )
    confirmation = campaign2.verify_confirmation(
        confirmation_path, registration_path, development_path, config
    )
    replay = campaign2.verify_replay(
        replay_path, confirmation_path, registration_path, development_path, config
    )
    if confirmation.get("amendment_id") != amendment["seal"]["amendment_id"]:
        raise ValueError("confirmation does not reference the sealed amendment")
    if not replay.get("all_exact"):
        raise ValueError("terminal-shortfall campaign did not replay exactly")

    destination = campaign2.analysis_path(run_root, config.profile)
    if destination.exists():
        verify_checksums(destination)
        seal = json.loads((destination / "analysis.json").read_text(encoding="utf-8"))
        if seal.get("amendment_id") != amendment["seal"]["amendment_id"]:
            raise ValueError("analysis was sealed under another policy")
        return destination

    validation = campaign2.verify_validation(
        campaign2.validation_path(run_root, config.profile), config
    )["results"]
    audit = audit_terminal_shortfalls(confirmation_path, config)
    integrity = {
        "validation_all_pass": bool(validation["all_pass"]),
        "trace_and_endpoint_validation": bool(
            validation["traced_untraced_exact"]
            and validation["strict8_fixture_positive"]
            and validation["strict8_relabel_invariant"]
        ),
        "deterministic_observers": bool(
            validation["repeated_model_hash_exact"]
            and validation["fresh_process_worker_count_model_hash_exact"]
        ),
        "relabeling_invariance": bool(
            max(validation["relabel_max_abs_errors"].values())
            <= config.relabel_tolerance
        ),
        "aligned_isomorphism": bool(
            max(validation["isomorphism_aligned_local_mismatch"].values())
            <= config.aligned_mismatch_tolerance
        ),
        "seed_firewall": bool(
            validation["development_confirmation_seed_domains_distinct"]
        ),
        "development_exact_replay": bool(development["replay"]["all_exact"]),
        "confirmation_exact_replay": bool(replay["all_exact"]),
        "all_confirmation_attempts_resolved": bool(
            audit["all_attempts_resolved"]
            and audit["all_cell_artifacts_present"]
            and audit["all_reference_lineages_retained"]
            and audit["outcome_shapes_exact"]
        ),
        "pathwise_terminal_control_exact": bool(
            audit["pathwise_terminal_control_exact"]
        ),
        "terminal_shortfall_policy_sealed_preanalysis": True,
        "source_tree_matches_registration": bool(
            registration["sources"] == campaign2._source_hashes()
        ),
        "analysis_firewall_intact": bool(
            not confirmation["analysis_artifacts_present"]
        ),
    }
    if not all(integrity.values()):
        raise ValueError(f"amended integrity gate failed: {integrity}")

    with atomic_destination(destination) as output:
        metrics = analyze_confirmation(
            confirmation_path / "cells",
            development_path / "predictors.joblib",
            config,
            output,
            integrity,
        )
        if metrics["decision"]["integrity_verdict"] != "VALID":
            raise ValueError("base analysis rejected amended integrity inputs")
        metrics["decision"][
            "integrity_verdict"
        ] = "VALID_WITH_PREANALYSIS_AMENDMENT"
        metrics["amendment"] = {
            "amendment_id": amendment["seal"]["amendment_id"],
            "terminal_audit": audit,
            "terminal_endpoint_summary": _terminal_endpoint_summary(
                confirmation_path, audit
            ),
        }
        (output / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True, allow_nan=True) + "\n",
            encoding="utf-8",
        )
        report_path = output / "REPORT.md"
        report = report_path.read_text(encoding="utf-8")
        report = report.replace(
            "**Integrity verdict:** `VALID`",
            "**Integrity verdict:** `VALID_WITH_PREANALYSIS_AMENDMENT`",
            1,
        )
        note = (
            "## Pre-analysis amendment\n\n"
            f"All {audit['expected_future_entries']:,} confirmation attempts were "
            f"retained. {audit['terminal_entry_count']} entries representing "
            f"{audit['distinct_terminal_stochastic_paths']} stochastic paths "
            "terminated before F32 and were retained without retry. Their exact "
            "terminal map and complete payloads reproduced before analysis. See "
            "`EXPERIMENT_2_AMENDMENT_1.md` and the sealed amendment ID in "
            "`metrics.json`.\n\n"
        )
        marker = "## Interpretation boundary\n"
        if marker not in report:
            raise ValueError("analysis report lacks its interpretation boundary")
        report_path.write_text(report.replace(marker, note + marker, 1), encoding="utf-8")

        seal: dict[str, Any] = {
            "format": "fep-surprise-2-amended-analysis-seal-v1",
            "status": "sealed_after_exact_confirmation_replay_under_amendment",
            "registration_id": registration["registration_id"],
            "development_id": development["development_id"],
            "confirmation_id": confirmation["confirmation_id"],
            "replay_id": replay["replay_id"],
            "amendment_id": amendment["seal"]["amendment_id"],
            "decision": metrics["decision"],
        }
        seal["analysis_id"] = canonical_digest(seal)
        (output / "analysis.json").write_text(
            json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    return destination


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Seal and run Experiment 2 terminal-shortfall amendment 1"
    )
    value.add_argument("command", choices=("audit", "seal", "verify", "analyze"))
    value.add_argument("--profile", choices=("smoke", "quick", "full"), default="full")
    value.add_argument("--run-root", type=Path, default=CAMPAIGN_ROOT / "runs2")
    return value


def main() -> None:
    args = parser().parse_args()
    config = profile_config(args.profile)
    if args.command == "audit":
        audit = audit_terminal_shortfalls(
            campaign2.confirmation_path(args.run_root, config.profile), config
        )
        print(json.dumps(audit, indent=2, sort_keys=True))
    elif args.command == "seal":
        amendment = seal_amendment(args.run_root, config)
        confirmation = seal_confirmation_under_amendment(args.run_root, config)
        print(f"amendment: {amendment}", flush=True)
        print(f"confirmation: {confirmation}", flush=True)
    elif args.command == "verify":
        bundle = verify_amendment(args.run_root, config)
        print(json.dumps(bundle, indent=2, sort_keys=True))
    elif args.command == "analyze":
        print(f"analysis: {analyze_under_amendment(args.run_root, config)}", flush=True)


if __name__ == "__main__":
    main()
