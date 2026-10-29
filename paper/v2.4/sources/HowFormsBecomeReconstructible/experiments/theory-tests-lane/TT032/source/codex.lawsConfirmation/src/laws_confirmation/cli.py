"""Command-line entry points for the confirmation workspace."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import traceback

from .io import (
    DEFAULT_EXTERNAL_ROOT,
    atomic_json,
    atomic_text,
    canonical_digest,
    environment_manifest,
    external_root,
    git_head,
    require_beneath,
    sha256_file,
    utc_now,
    write_hash_manifest,
)


THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def _default_plastic_root() -> Path:
    # .../PlasticHeredity/NewIdeas/preprints/<programme>/codex.../src/package/file
    return Path(__file__).resolve().parents[6]


def _configure_runtime(root: Path) -> None:
    for variable in THREAD_VARIABLES:
        os.environ[variable] = "1"
    temporary = root / "tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TMPDIR", str(temporary))
    os.environ.setdefault("XDG_CACHE_HOME", str(temporary / "cache"))
    # This affects child interpreters. The launch command also sets it before
    # Python starts so bytecode from this interpreter stays external.
    os.environ.setdefault("PYTHONPYCACHEPREFIX", str(temporary / "pycache"))


def _disk_manifest(root: Path, *, estimated_output_bytes: int = 10 * 1024 * 1024) -> dict:
    usage = shutil.disk_usage(root)
    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "estimated_output_bytes": estimated_output_bytes,
        "required_free_margin_bytes": 1024 * 1024 * 1024,
        "preflight_pass": usage.free
        >= estimated_output_bytes + 1024 * 1024 * 1024,
    }


def _validate_run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(
            "run ID must contain only letters, digits, dots, underscores, and hyphens"
        )
    return value


def retained_audit(args: argparse.Namespace) -> int:
    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / args.run_id
    run_dir = output_root / "runs" / args.run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {args.run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocols = (
        workspace / "protocols/L01_L02_ECA_AUDIT_V1.md",
        workspace / "protocols/L01_L02_ECA_AUDIT_V1_1_AMENDMENT.md",
    )
    protocol_hashes = {str(path): sha256_file(path) for path in protocols}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 2,
        "run_id": args.run_id,
        "stage": "L01/L02 retained-artifact audit A/B",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocols_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocols_sha256": protocol_hashes,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "scientific_futures_generated": 0,
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
        # Delayed import ensures numerical thread limits are installed first.
        from .artifact_audit import markdown_report, run_retained_audit

        audit, input_paths = run_retained_audit(plastic_root)
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
            "scientific_futures_generated": 0,
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l3_retained_audit(args: argparse.Namespace) -> int:
    """Recalculate L03 atlas and translation claims from retained artefacts."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L03_RETAINED_AUDIT_V1.md"
    protocol_hash = sha256_file(protocol)
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L03 retained atlas and translation audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": {str(protocol): protocol_hash},
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hash,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "scientific_futures_generated": 0,
        "outcome_blinding": "none; retained outcomes known",
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
        from .l3_audit import markdown_report, run_l3_retained_audit

        audit, input_paths = run_l3_retained_audit(plastic_root)
        audit["contract_digest"] = manifest["contract_digest"]
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "scientific_futures_generated": 0,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "scientific_futures_generated": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l4_retained_audit(args: argparse.Namespace) -> int:
    """Audit L04 and replay E28's historical post-hoc horizon namespace."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    from .l4_audit import E28_REPLAY_TRAJECTORIES

    workspace = Path(__file__).resolve().parents[2]
    protocols = (
        workspace / "protocols/L04_RETAINED_AUDIT_V1.md",
        workspace / "protocols/L04_RETAINED_AUDIT_V1_1_AMENDMENT.md",
    )
    protocol_hashes = {str(path): sha256_file(path) for path in protocols}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L04 retained observer/compressibility audit and E28 replay",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocols_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocols_sha256": protocol_hashes,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_namespace_trajectory_replays_planned": E28_REPLAY_TRAJECTORIES,
        "outcome_blinding": "none; retained outcomes and A1 result known",
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
        from .l4_audit import markdown_report, run_l4_audit

        audit, input_paths = run_l4_audit(plastic_root, output_root)
        audit["contract_digest"] = manifest["contract_digest"]
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_trajectories_replayed": E28_REPLAY_TRAJECTORIES,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_trajectory_replays_planned": E28_REPLAY_TRAJECTORIES,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l5_retained_audit(args: argparse.Namespace) -> int:
    """Recalculate L05 conservation-selfhood claims from retained artefacts."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L05_RETAINED_AUDIT_V1.md"
    protocol_hash = sha256_file(protocol)
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L05 retained conservation-selfhood audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": {str(protocol): protocol_hash},
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hash,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_namespace_trajectory_replays_planned": 0,
        "outcome_blinding": "none; retained outcomes known",
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
        from .l5_audit import markdown_report, run_l5_audit

        audit, input_paths = run_l5_audit(plastic_root, output_root)
        audit["contract_digest"] = manifest["contract_digest"]
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_trajectories_replayed": 0,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_trajectories_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l6_retained_replay_audit(args: argparse.Namespace) -> int:
    """Audit L06, replaying only E29's exact historical axis streams."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    from .l6_audit import E29_CONFIGS, E29_HISTORICAL_FUTURES

    workspace = Path(__file__).resolve().parents[2]
    protocols = (
        workspace / "protocols/L06_RETAINED_REPLAY_AUDIT_V1.md",
        workspace / "protocols/L06_RETAINED_REPLAY_AUDIT_V1_1_AMENDMENT.md",
    )
    protocol_hashes = {str(path): sha256_file(path) for path in protocols}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L06 retained graft audit and E29 historical-axis replay",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocols_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocols_sha256": protocol_hashes,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_namespace_futures_planned": E29_HISTORICAL_FUTURES,
        "outcome_blinding": "none; retained aggregate outcomes known",
        "disk_preflight": disk,
        "environment": environment_manifest(),
    }
    atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    atomic_json(
        run_dir / "STATUS.json",
        {
            "status": "RUNNING",
            "updated_utc": utc_now(),
            "stage": "E29 historical fidelity replay",
            "completed_axis_configs": 0,
            "total_axis_configs": E29_CONFIGS,
            "historical_namespace_futures_completed": 0,
            "historical_namespace_futures_planned": E29_HISTORICAL_FUTURES,
        },
        output_root,
    )

    def record_progress(completed: int, total: int) -> None:
        futures_completed = completed * (E29_HISTORICAL_FUTURES // E29_CONFIGS)
        atomic_json(
            run_dir / "STATUS.json",
            {
                "status": "RUNNING",
                "updated_utc": utc_now(),
                "stage": "E29 historical fidelity replay",
                "completed_axis_configs": completed,
                "total_axis_configs": total,
                "historical_namespace_futures_completed": futures_completed,
                "historical_namespace_futures_planned": E29_HISTORICAL_FUTURES,
            },
            output_root,
        )

    try:
        from .l6_audit import run_l6_audit

        audit, input_paths = run_l6_audit(plastic_root, progress=record_progress)
        audit["contract_digest"] = manifest["contract_digest"]
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_futures_replayed": E29_HISTORICAL_FUTURES,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.json")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_futures_planned": E29_HISTORICAL_FUTURES,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l7_retained_audit(args: argparse.Namespace) -> int:
    """Audit L07 from retained masks, aggregates, and source design."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocols = (
        workspace / "protocols/L07_RETAINED_AUDIT_V1.md",
        workspace / "protocols/L07_RETAINED_AUDIT_V1_1_AMENDMENT.md",
    )
    protocol_hashes = {str(path): sha256_file(path) for path in protocols}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L07 retained learning/history-dependence audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocols_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocols_sha256": protocol_hashes,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_namespace_futures_planned": 0,
        "outcome_blinding": "none; retained aggregate outcomes known",
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
        from .l7_audit import markdown_report, run_l7_retained_audit

        audit, input_paths = run_l7_retained_audit(plastic_root)
        audit["contract_digest"] = manifest["contract_digest"]
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_futures_replayed": 0,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_namespace_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l8_retained_replay_audit(args: argparse.Namespace) -> int:
    """Audit L08 and replay only E39's fixed current-source paths."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    from .l8_audit import E39_REPLAY_ARM_PATHS

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L08_RETAINED_REPLAY_AUDIT_V1.md"
    protocol_hash = sha256_file(protocol)
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L08 retained field/amplifier audit and E39 current-source replay",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": {str(protocol): protocol_hash},
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hash,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_current_source_arm_paths_planned": E39_REPLAY_ARM_PATHS,
        "outcome_blinding": "none; retained outcomes known",
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
        from .l8_audit import markdown_report, run_l8_audit

        audit, input_paths = run_l8_audit(plastic_root)
        audit["contract_digest"] = manifest["contract_digest"]
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_current_source_arm_paths_replayed": E39_REPLAY_ARM_PATHS,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_current_source_arm_paths_planned": E39_REPLAY_ARM_PATHS,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l9_retained_audit(args: argparse.Namespace) -> int:
    """Audit L09 from retained rows and the chronological source record."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L09_RETAINED_AUDIT_V1.md"
    protocol_hash = sha256_file(protocol)
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L09 retained triangle/resolution audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": {str(protocol): protocol_hash},
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hash,
                "code_sha256": code_hashes,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_paths_planned": 0,
        "outcome_blinding": "none; retained outcomes known",
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
        from .l9_audit import markdown_report, run_l9_audit

        audit, input_paths = run_l9_audit(plastic_root)
        audit["contract_digest"] = manifest["contract_digest"]
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_paths_replayed": 0,
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_paths_planned": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l10_retained_replay_audit(args: argparse.Namespace) -> int:
    """Audit L10 and replay only the historical cessation rows."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L10_RETAINED_REPLAY_AUDIT_V1.md"
    protocol_hash = sha256_file(protocol)
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    planned_futures = 4160
    planned_rows = 220
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L10 retained/replay honest-stress audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": {str(protocol): protocol_hash},
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hash,
                "code_sha256": code_hashes,
                "historical_rows_planned": planned_rows,
                "historical_simulator_futures_planned": planned_futures,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_rows_planned": planned_rows,
        "historical_simulator_futures_planned": planned_futures,
        "outcome_blinding": "none; retained outcomes known",
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
        from .l10_audit import markdown_report, run_l10_audit

        audit, input_paths = run_l10_audit(plastic_root, replay=True)
        audit["contract_digest"] = manifest["contract_digest"]
        if sha256_file(protocol) != protocol_hash:
            raise RuntimeError("frozen L10 protocol changed during the run")
        changed_code = [
            path for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_rows_replayed": audit["focused_replay"]["historical_rows_replayed"],
            "historical_simulator_futures_replayed": audit[
                "historical_simulator_futures_replayed"
            ],
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_rows_planned": planned_rows,
            "historical_simulator_futures_planned": planned_futures,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l11_retained_replay_audit(args: argparse.Namespace) -> int:
    """Audit L11 and replay only E46's historical trap paths."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=32 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L11_RETAINED_REPLAY_AUDIT_V1.md"
    protocol_hash = sha256_file(protocol)
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    planned_rows = 40
    planned_futures = 640
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L11 retained/replay greedy-trap audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": {str(protocol): protocol_hash},
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hash,
                "code_sha256": code_hashes,
                "historical_rows_planned": planned_rows,
                "historical_simulator_futures_planned": planned_futures,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_rows_planned": planned_rows,
        "historical_simulator_futures_planned": planned_futures,
        "outcome_blinding": "none; retained outcomes known",
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
        from .l11_audit import markdown_report, run_l11_audit

        audit, input_paths = run_l11_audit(plastic_root, replay=True)
        audit["contract_digest"] = manifest["contract_digest"]
        if sha256_file(protocol) != protocol_hash:
            raise RuntimeError("frozen L11 protocol changed during the run")
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_rows_replayed": audit["E46_focused_replay"][
                "historical_rows_replayed"
            ],
            "historical_simulator_futures_replayed": audit[
                "historical_simulator_futures_replayed"
            ],
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(output_dir / "input_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_rows_planned": planned_rows,
            "historical_simulator_futures_planned": planned_futures,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l12_retained_replay_audit(args: argparse.Namespace) -> int:
    """Audit L12 and re-instrument its historical road-map futures."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=64 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocols = (
        workspace / "protocols/L12_RETAINED_REPLAY_AUDIT_V1.md",
        workspace / "protocols/L12_RETAINED_REPLAY_AUDIT_V1_1_AMENDMENT.md",
    )
    protocol_hashes = {str(path): sha256_file(path) for path in protocols}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    planned_rows = 160
    planned_futures = 3040
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L12 retained/replay single-road audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "historical_rows_planned": planned_rows,
                "historical_simulator_futures_planned": planned_futures,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_rows_planned": planned_rows,
        "historical_simulator_futures_planned": planned_futures,
        "outcome_blinding": "none; retained outcomes and L12 claim known",
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
        # Delayed import keeps NumPy thread limits in place before replay.
        import numpy as np
        import tempfile

        from .l12_audit import markdown_report, run_l12_audit

        audit, input_paths, road_arrays, frozen_input_hashes = run_l12_audit(
            plastic_root, output_root, replay=True
        )
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L12 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L12 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        road_target = require_beneath(output_dir / "road_maps.npz", output_root)
        descriptor, temporary = tempfile.mkstemp(
            prefix=road_target.name + ".",
            suffix=".tmp",
            dir=road_target.parent,
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                np.savez_compressed(handle, **road_arrays)
            os.replace(temporary, road_target)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
        audit["road_map_bundle"] = {
            "path": str(road_target),
            "sha256": sha256_file(road_target),
            "array_count": len(road_arrays),
            "arrays": {
                key: {"shape": list(value.shape), "dtype": str(value.dtype)}
                for key, value in sorted(road_arrays.items())
            },
        }
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        write_hash_manifest(input_paths, output_dir / "input_hashes.sha256", output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "fresh_scientific_futures_generated": 0,
            "historical_rows_replayed": audit["historical_rows_replayed"],
            "historical_simulator_futures_replayed": audit[
                "historical_simulator_futures_replayed"
            ],
            "output_files": [
                str(output_dir / "audit.json"),
                str(output_dir / "audit.md"),
                str(road_target),
                str(output_dir / "input_hashes.sha256"),
            ],
            "output_sha256": {
                path.name: sha256_file(path)
                for path in (
                    output_dir / "audit.json",
                    output_dir / "audit.md",
                    road_target,
                    output_dir / "input_hashes.sha256",
                )
            },
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_rows_planned": planned_rows,
            "historical_simulator_futures_planned": planned_futures,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l13_prophecy_census(args: argparse.Namespace) -> int:
    """Audit L13's interpolation/extrapolation prophecy contrast."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=16 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocols = (
        workspace / "protocols/L13_PROPHECY_CENSUS_V1.md",
        workspace / "protocols/L13_PROPHECY_CENSUS_V1_1_AMENDMENT.md",
    )
    protocol_hashes = {str(path): sha256_file(path) for path in protocols}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L13 retained prophecy census and provenance audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "expected_component_predictions": 75,
                "expected_composite_headlines": 2,
                "fresh_scientific_futures_planned": 0,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": (
            "none; retained outcomes were known before the result-hidden-text "
            "classification rubric was frozen"
        ),
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
        from .l13_audit import (
            clauses_csv,
            markdown_report,
            records_csv,
            run_l13_audit,
        )

        audit, input_paths, records, clauses, frozen_input_hashes = run_l13_audit(
            plastic_root, workspace
        )
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L13 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L13 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        atomic_json(output_dir / "audit.json", audit, output_root)
        atomic_text(output_dir / "audit.md", markdown_report(audit), output_root)
        atomic_json(
            output_dir / "prophecy_census.json",
            {"schema_version": 1, "records": records},
            output_root,
        )
        atomic_text(
            output_dir / "prophecy_census.csv", records_csv(records), output_root
        )
        atomic_text(
            output_dir / "gate_clause_census.csv", clauses_csv(clauses), output_root
        )
        write_hash_manifest(
            input_paths, output_dir / "input_hashes.sha256", output_root
        )
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "prophecy_census.json",
            output_dir / "prophecy_census.csv",
            output_dir / "gate_clause_census.csv",
            output_dir / "input_hashes.sha256",
        ]
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "prophecy_records": len(records),
            "gate_clause_records": len(clauses),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l14_price_order_ledger(args: argparse.Namespace) -> int:
    """Audit L14's metaphorical price order against repository-visible costs."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=16 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L14_PRICE_ORDER_LEDGER_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L14 retained engineering-cost and search-history ledger",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "milestones": ["E26", "E30", "E33", "E49"],
                "price_scalar_defined": False,
                "fresh_scientific_futures_planned": 0,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; this is an explicitly outcome-known retrospective ledger",
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
        from .l14_audit import (
            markdown_report,
            milestone_ledger_csv,
            package_ledger_csv,
            run_l14_audit,
            search_effort_csv,
            search_ladder_csv,
        )

        (
            audit,
            input_paths,
            package_rows,
            milestone_rows,
            search_rows,
            ladder_rows,
            frozen_input_hashes,
        ) = run_l14_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L14 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L14 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "package_ledger.csv",
            output_dir / "milestone_ledger.csv",
            output_dir / "search_effort.csv",
            output_dir / "search_ladder.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], package_ledger_csv(package_rows), output_root)
        atomic_text(output_files[3], milestone_ledger_csv(milestone_rows), output_root)
        atomic_text(output_files[4], search_effort_csv(search_rows), output_root)
        atomic_text(output_files[5], search_ladder_csv(ladder_rows), output_root)
        write_hash_manifest(input_paths, output_files[6], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "historical_packages_inventoried": len(package_rows),
            "milestone_records": len(milestone_rows),
            "search_effort_records": len(search_rows),
            "search_ladder_records": len(ladder_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def stage_c_benchmark(args: argparse.Namespace) -> int:
    """Run the preregistered, outcome-blind A1 sizing benchmark."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    if not 1 <= args.workers <= 4:
        raise ValueError("--workers must lie in [1, 4]")

    run_dir = output_root / "runs" / run_id
    if run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    # Delayed import installs thread and temporary-directory limits before
    # NumPy or multiprocessing code enters the process.
    from .benchmark import (
        BENCHMARK_CONDITIONS,
        BENCHMARK_NAMESPACE,
        BENCHMARK_RULES,
        assert_blind_payload,
        benchmark_tasks,
        run_benchmark,
        runtime_projection,
    )

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L01_L02_STAGE_C_BENCHMARK_V1.md"
    adapted_source_root = workspace.parent / "codex.reconstructionsAndStressTesting"
    adapted_sources = (
        adapted_source_root / "plastic_ca/e19.py",
        adapted_source_root / "plastic_ca/particle_e19.py",
        adapted_source_root / "plastic_ca/particle.py",
    )
    missing_sources = [str(path) for path in adapted_sources if not path.is_file()]
    if missing_sources:
        raise FileNotFoundError(f"missing adapted source files: {missing_sources}")
    protocol_hash = sha256_file(protocol)
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    source_hashes = {str(path): sha256_file(path) for path in adapted_sources}
    task_count = len(benchmark_tasks())
    condition_count = (
        2 * len(BENCHMARK_RULES) * sum(len(values) for values in BENCHMARK_CONDITIONS.values())
    )
    futures_planned = condition_count * 8 * 32
    contract = {
        "namespace": BENCHMARK_NAMESPACE,
        "rules": list(BENCHMARK_RULES),
        "conditions": {
            str(width): list(values)
            for width, values in BENCHMARK_CONDITIONS.items()
        },
        "observers": ["raw4", "particle4"],
        "launches_per_condition": 8,
        "futures_per_launch": 32,
        "task_count": task_count,
        "condition_count": condition_count,
        "future_count": futures_planned,
    }
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L01/L02 Stage-C non-inferential runtime benchmark",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "external_root": str(output_root),
        "run_dir": str(run_dir),
        "protocol_sha256": {str(protocol): protocol_hash},
        "code_sha256": code_hashes,
        "adapted_sources_sha256": source_hashes,
        "benchmark_contract": contract,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hash,
                "code_sha256": code_hashes,
                "adapted_sources_sha256": source_hashes,
                "benchmark_contract": contract,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": args.workers,
        "scientific_futures_generated": 0,
        "benchmark_futures_planned": futures_planned,
        "disk_preflight": disk,
        "environment": environment_manifest(),
    }
    atomic_json(run_dir / "MANIFEST.json", manifest, output_root)
    atomic_json(
        run_dir / "STATUS.json",
        {
            "status": "RUNNING",
            "updated_utc": utc_now(),
            "completed_tasks": 0,
            "total_tasks": task_count,
            "benchmark_futures_completed": 0,
        },
        output_root,
    )

    benchmark_futures_completed = 0

    def record_progress(result: dict[str, object], completed: int, total: int) -> None:
        nonlocal benchmark_futures_completed
        condition_timings = result["condition_timings"]
        benchmark_futures_completed += sum(
            int(row["futures"]) for row in condition_timings  # type: ignore[union-attr]
        )
        atomic_json(
            run_dir / "STATUS.json",
            {
                "status": "RUNNING",
                "updated_utc": utc_now(),
                "completed_tasks": completed,
                "total_tasks": total,
                "benchmark_futures_completed": benchmark_futures_completed,
                "last_completed_task": {
                    "observer": result["observer"],
                    "rule": result["rule"],
                    "width": result["width"],
                },
            },
            output_root,
        )

    try:
        results = run_benchmark(args.workers, progress=record_progress)
        projection = runtime_projection(results, workers=args.workers)
        elapsed = time.monotonic() - started_monotonic
        payload = {
            "schema_version": 1,
            "run_id": run_id,
            "inferential_use": "PROHIBITED",
            "contract_digest": manifest["contract_digest"],
            "elapsed_seconds": elapsed,
            "workers": args.workers,
            "task_count": task_count,
            "condition_count": condition_count,
            "benchmark_future_count": benchmark_futures_completed,
            "results": results,
            "runtime_projection": projection,
        }
        assert_blind_payload(payload)
        atomic_json(run_dir / "BENCHMARK.json", payload, output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": elapsed,
            "completed_tasks": task_count,
            "benchmark_futures_completed": benchmark_futures_completed,
            "scientific_futures_generated": 0,
            "benchmark_file": str(run_dir / "BENCHMARK.json"),
            "a1_detach_required": projection["a1_focused"]["detach_required"],
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(run_dir / "BENCHMARK.json")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "completed_tasks": None,
            "benchmark_futures_completed": benchmark_futures_completed,
            "scientific_futures_generated": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def stage_d_a1(args: argparse.Namespace) -> int:
    """Run or exactly resume the frozen Stage-D A1 scientific campaign."""

    invocation_started = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    if not 1 <= args.workers <= 4:
        raise ValueError("--workers must lie in [1, 4]")

    # Install thread limits before importing the numerical campaign module.
    from .a1 import (
        adjudicate,
        campaign_tasks,
        design_contract,
        markdown_report,
        replay_integrity_checks,
        run_campaign,
    )

    workspace = Path(__file__).resolve().parents[2]
    run_dir = output_root / "runs" / run_id
    output_dir = output_root / "outputs" / run_id
    protocol = workspace / "protocols/L01_L02_STAGE_D_A1_V1.md"
    adapted_source_root = workspace.parent / "codex.reconstructionsAndStressTesting"
    adapted_sources = (
        adapted_source_root / "plastic_ca/e19.py",
        adapted_source_root / "plastic_ca/particle_e19.py",
        adapted_source_root / "plastic_ca/particle.py",
    )
    missing_sources = [str(path) for path in adapted_sources if not path.is_file()]
    if missing_sources:
        raise FileNotFoundError(f"missing adapted source files: {missing_sources}")
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    source_hashes = {str(path): sha256_file(path) for path in adapted_sources}
    protocol_hash = sha256_file(protocol)
    design = design_contract()
    contract_digest = canonical_digest(
        {
            "protocol_sha256": protocol_hash,
            "code_sha256": code_hashes,
            "adapted_sources_sha256": source_hashes,
            "design": design,
        }
    )
    disk = _disk_manifest(output_root, estimated_output_bytes=512 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    if run_dir.exists():
        if not args.resume:
            raise FileExistsError(
                f"immutable run ID already exists; use --resume only for an exact continuation: {run_id}"
            )
        manifest_path = run_dir / "MANIFEST.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"existing run lacks manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("contract_digest") != contract_digest:
            raise RuntimeError(
                "resume refused: current protocol/code/design digest differs from the run manifest"
            )
        if (run_dir / "COMPLETE").exists():
            raise FileExistsError(f"run is already complete: {run_id}")
    else:
        if args.resume:
            raise FileNotFoundError(f"cannot resume missing run: {run_id}")
        if output_dir.exists():
            raise FileExistsError(f"output ID already exists without a run: {output_dir}")
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "run_id": run_id,
            "stage": "L01/L02 Stage-D focused A1 fresh ECA confirmation",
            "status": "RUNNING",
            "started_utc": utc_now(),
            "pid": os.getpid(),
            "external_root": str(output_root),
            "run_dir": str(run_dir),
            "output_dir": str(output_dir),
            "protocol_sha256": {str(protocol): protocol_hash},
            "code_sha256": code_hashes,
            "adapted_sources_sha256": source_hashes,
            "design": design,
            "contract_digest": contract_digest,
            "repository_head": git_head(workspace),
            "workers": args.workers,
            "scientific_futures_planned": design["total_futures"],
            "disk_preflight": disk,
            "environment": environment_manifest(),
        }
        atomic_json(run_dir / "MANIFEST.json", manifest, output_root)

    atomic_text(run_dir / "RUN.pid", f"{os.getpid()}\n", output_root)

    checkpoints_root = run_dir / "checkpoints"
    completed: dict[str, dict[str, object]] = {}
    checkpoint_paths: list[Path] = []
    if checkpoints_root.exists():
        for path in sorted(checkpoints_root.glob("*/*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("contract_digest") != contract_digest:
                raise RuntimeError(f"checkpoint digest mismatch: {path}")
            panel = payload.get("panel")
            if not isinstance(panel, dict) or "panel_key" not in panel:
                raise ValueError(f"malformed checkpoint: {path}")
            key = str(panel["panel_key"])
            if key in completed:
                raise ValueError(f"duplicate checkpoint panel key: {key}")
            completed[key] = panel
            checkpoint_paths.append(path)

    total_tasks = len(campaign_tasks())

    def panel_future_count(panel: dict[str, object]) -> int:
        return sum(
            int(condition["partitions"]["combined"]["n_futures"])
            for condition in panel["conditions"]  # type: ignore[union-attr]
        )

    completed_futures = sum(panel_future_count(panel) for panel in completed.values())
    atomic_json(
        run_dir / "STATUS.json",
        {
            "status": "RUNNING",
            "updated_utc": utc_now(),
            "pid": os.getpid(),
            "resume": bool(args.resume),
            "completed_panel_tasks": len(completed),
            "total_panel_tasks": total_tasks,
            "scientific_futures_completed": completed_futures,
            "scientific_futures_planned": design["total_futures"],
        },
        output_root,
    )

    def save_progress(panel: dict[str, object], count: int, total: int) -> None:
        nonlocal completed_futures
        observer = str(panel["observer"])
        rule = int(panel["rule"])
        width = int(panel["width"])
        path = checkpoints_root / observer / f"rule-{rule:03d}-width-{width:03d}.json"
        if path.exists():
            raise FileExistsError(f"refusing to overwrite checkpoint: {path}")
        atomic_json(
            path,
            {"contract_digest": contract_digest, "panel": panel},
            output_root,
        )
        checkpoint_paths.append(path)
        completed_futures += panel_future_count(panel)
        atomic_json(
            run_dir / "STATUS.json",
            {
                "status": "RUNNING",
                "updated_utc": utc_now(),
                "pid": os.getpid(),
                "completed_panel_tasks": count,
                "total_panel_tasks": total,
                "scientific_futures_completed": completed_futures,
                "scientific_futures_planned": design["total_futures"],
                "last_completed_panel": {
                    "observer": observer,
                    "rule": rule,
                    "width": width,
                },
            },
            output_root,
        )

    try:
        panels = run_campaign(
            args.workers,
            completed,
            progress=save_progress,
        )
        adjudication = adjudicate(panels)
        replay = replay_integrity_checks(panels)
        if not replay["passes"]:
            raise RuntimeError("deterministic replay integrity check failed")
        elapsed = time.monotonic() - invocation_started
        result = {
            "schema_version": 1,
            "run_id": run_id,
            "contract_digest": contract_digest,
            "completed_utc": utc_now(),
            "elapsed_seconds": elapsed,
            "panel_cpu_seconds_sum": sum(
                float(panel["panel_elapsed_seconds"]) for panel in panels
            ),
            "workers": args.workers,
            "scientific_future_count": completed_futures,
            "design": design,
            "replay_integrity": replay,
            "adjudication": adjudication,
            "panels": panels,
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(output_dir / "RESULTS.json", result, output_root)
        atomic_text(output_dir / "REPORT.md", markdown_report(result), output_root)
        write_hash_manifest(
            checkpoint_paths,
            output_dir / "checkpoint_hashes.sha256",
            output_root,
        )
        complete = {
            "status": "COMPLETE",
            "completed_utc": result["completed_utc"],
            "elapsed_seconds": elapsed,
            "completed_panel_tasks": total_tasks,
            "scientific_futures_completed": completed_futures,
            "replay_integrity_passed": True,
            "output_files": [
                str(output_dir / "RESULTS.json"),
                str(output_dir / "REPORT.md"),
                str(output_dir / "checkpoint_hashes.sha256"),
            ],
        }
        atomic_json(run_dir / "STATUS.json", complete, output_root)
        atomic_text(run_dir / "COMPLETE", complete["completed_utc"] + "\n", output_root)
        print(output_dir / "REPORT.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds_this_invocation": time.monotonic() - invocation_started,
            "completed_panel_tasks": len(completed),
            "total_panel_tasks": total_tasks,
            "scientific_futures_completed": completed_futures,
            "scientific_futures_planned": design["total_futures"],
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "resume_allowed_only_with_exact_digest": True,
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l15_timescale_audit(args: argparse.Namespace) -> int:
    """Recalculate L15's retained surface and exact limited-case dynamics."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    prior_l10_audit = (
        Path(args.prior_l10_audit).expanduser().resolve()
        if args.prior_l10_audit
        else output_root
        / "outputs/l10_retained_replay_audit_v1_attempt2/audit.json"
    )
    if not prior_l10_audit.is_file():
        raise FileNotFoundError(f"completed L10 audit not found: {prior_l10_audit}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L15_TIMESCALE_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L15 retained timescale and category audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "prior_l10_audit": str(prior_l10_audit),
        "prior_l10_audit_sha256": sha256_file(prior_l10_audit),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "rho_values": [0.002, 0.01, 0.05],
                "gain_values": [0.2, 0.4, 0.8],
                "dt": 0.2,
                "bootstrap_draws": 4096,
                "bootstrap_seeds": [20260902151, 20260902152, 20260902153, 20260902154],
                "prior_l10_audit_sha256": sha256_file(prior_l10_audit),
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "prior_replayed_futures_consumed_as_audited_input": 1120,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l15_audit import (
            e48_surface_csv,
            e49_tissue_contrasts_csv,
            markdown_report,
            run_l15_audit,
        )

        audit, input_paths, e48_rows, e49_rows, frozen_input_hashes = run_l15_audit(
            plastic_root,
            workspace,
            prior_l10_audit=prior_l10_audit,
        )
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L15 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L15 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "e48_surface.csv",
            output_dir / "e49_tissue_contrasts.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], e48_surface_csv(e48_rows), output_root)
        atomic_text(output_files[3], e49_tissue_contrasts_csv(e49_rows), output_root)
        write_hash_manifest(input_paths, output_files[4], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "e48_surface_cells": len(e48_rows),
            "e49_tissue_rows": len(e49_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "prior_replayed_futures_consumed_as_audited_input": 1120,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l16_landlord_tenant_audit(args: argparse.Namespace) -> int:
    """Recalculate L16's retained carrier, alignment, and horizon evidence."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=6 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L16_LANDLORD_TENANT_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L16 retained landlord/tenant role audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "bootstrap_draws": 4096,
                "bootstrap_seeds": list(range(20260902161, 20260902166))
                + list(range(20260902171, 20260902178)),
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l16_audit import (
            e53_tissue_contrasts_csv,
            e54_class_dose_csv,
            e57_regime_repeats_csv,
            markdown_report,
            role_table_csv,
            run_l16_audit,
        )

        (
            audit,
            input_paths,
            role_rows,
            e53_rows,
            e54_rows,
            e57_rows,
            frozen_input_hashes,
        ) = run_l16_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L16 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L16 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "role_table.csv",
            output_dir / "e53_tissue_contrasts.csv",
            output_dir / "e54_class_dose.csv",
            output_dir / "e57_regime_repeats.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], role_table_csv(role_rows), output_root)
        atomic_text(output_files[3], e53_tissue_contrasts_csv(e53_rows), output_root)
        atomic_text(output_files[4], e54_class_dose_csv(e54_rows), output_root)
        atomic_text(output_files[5], e57_regime_repeats_csv(e57_rows), output_root)
        write_hash_manifest(input_paths, output_files[6], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "role_table_rows": len(role_rows),
            "e53_tissue_rows": len(e53_rows),
            "e54_class_dose_rows": len(e54_rows),
            "e57_repeat_rows": len(e57_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l17_development_heredity_audit(args: argparse.Namespace) -> int:
    """Recalculate L17's retained fixed-ancestor and channel evidence."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=6 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L17_DEVELOPMENT_HEREDITY_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L17 retained development/heredity channel audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "bootstrap_draws": 4096,
                "bootstrap_seeds": list(range(20260903171, 20260903176)),
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l17_audit import (
            channel_table_csv,
            e54_flagship_rows_csv,
            e55_channel_curves_csv,
            e55_generation_trace_csv,
            e57_transport_rows_csv,
            markdown_report,
            run_l17_audit,
        )

        (
            audit,
            input_paths,
            channel_rows,
            e54_rows,
            e55_curve_rows,
            e55_generation_rows,
            e57_rows,
            frozen_input_hashes,
        ) = run_l17_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L17 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L17 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "channel_table.csv",
            output_dir / "e54_flagship_rows.csv",
            output_dir / "e55_channel_curves.csv",
            output_dir / "e55_generation_trace.csv",
            output_dir / "e57_transport_rows.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], channel_table_csv(channel_rows), output_root)
        atomic_text(output_files[3], e54_flagship_rows_csv(e54_rows), output_root)
        atomic_text(output_files[4], e55_channel_curves_csv(e55_curve_rows), output_root)
        atomic_text(
            output_files[5],
            e55_generation_trace_csv(e55_generation_rows),
            output_root,
        )
        atomic_text(output_files[6], e57_transport_rows_csv(e57_rows), output_root)
        write_hash_manifest(input_paths, output_files[7], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "channel_table_rows": len(channel_rows),
            "e54_flagship_rows": len(e54_rows),
            "e55_curve_rows": len(e55_curve_rows),
            "e55_generation_rows": len(e55_generation_rows),
            "e57_transport_rows": len(e57_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l18_takeover_bounded_audit(args: argparse.Namespace) -> int:
    """Recalculate L18's retained scaffold and selection evidence."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L18_TAKEOVER_BOUNDED_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L18 retained bounded-takeover audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "bootstrap_draws": 4096,
                "bootstrap_seeds": list(range(20260903181, 20260903194)),
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l18_audit import (
            e56_knife_rows_csv,
            e56_schedule_rows_csv,
            e57_regime_repeats_csv,
            markdown_report,
            run_l18_audit,
        )

        (
            audit,
            input_paths,
            knife_rows,
            schedule_rows,
            e57_rows,
            frozen_input_hashes,
        ) = run_l18_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L18 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L18 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "e56_knife_rows.csv",
            output_dir / "e56_schedule_rows.csv",
            output_dir / "e57_regime_repeats.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], e56_knife_rows_csv(knife_rows), output_root)
        atomic_text(output_files[3], e56_schedule_rows_csv(schedule_rows), output_root)
        atomic_text(output_files[4], e57_regime_repeats_csv(e57_rows), output_root)
        write_hash_manifest(input_paths, output_files[5], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "e56_knife_rows": len(knife_rows),
            "e56_schedule_rows": len(schedule_rows),
            "e57_regime_repeat_rows": len(e57_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l19_incorruptible_reference_audit(args: argparse.Namespace) -> int:
    """Recalculate L19's retained clock, teaching, and cascade evidence."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L19_INCORRUPTIBLE_REFERENCE_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L19 retained incorruptible-reference audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "bootstrap_draws": 4096,
                "bootstrap_seeds": list(range(20260903194, 20260903215)),
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l19_audit import (
            architecture_inventory_csv,
            e64_corner_rows_csv,
            e64_regime_repeats_csv,
            e65_arm_rows_csv,
            markdown_report,
            run_l19_audit,
        )

        (
            audit,
            input_paths,
            e64_rows,
            corner_rows,
            e65_rows,
            architecture_rows,
            frozen_input_hashes,
        ) = run_l19_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L19 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L19 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "e64_regime_repeats.csv",
            output_dir / "e64_corner_rows.csv",
            output_dir / "e65_arm_rows.csv",
            output_dir / "architecture_inventory.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], e64_regime_repeats_csv(e64_rows), output_root)
        atomic_text(output_files[3], e64_corner_rows_csv(corner_rows), output_root)
        atomic_text(output_files[4], e65_arm_rows_csv(e65_rows), output_root)
        atomic_text(
            output_files[5],
            architecture_inventory_csv(architecture_rows),
            output_root,
        )
        write_hash_manifest(input_paths, output_files[6], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "e64_regime_repeat_rows": len(e64_rows),
            "e64_corner_rows": len(corner_rows),
            "e65_arm_rows": len(e65_rows),
            "architecture_inventory_rows": len(architecture_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l20_self_written_genome_audit(args: argparse.Namespace) -> int:
    """Audit L20's retained writable-theta result and later modifiers."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L20_SELF_WRITTEN_GENOME_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L20 retained self-written-genome audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
                "static_seed_input_reconstructions": 4,
                "E68_retained_tissue_rows_recalculated": 48,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l20_audit import (
            markdown_report,
            metric_ledger_csv,
            modifier_ledger_csv,
            native_theta_inputs_csv,
            run_l20_audit,
        )

        (
            audit,
            input_paths,
            metric_rows,
            theta_rows,
            modifier_rows,
            frozen_input_hashes,
        ) = run_l20_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L20 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L20 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "e66_metric_ledger.csv",
            output_dir / "native_theta_inputs.csv",
            output_dir / "followon_modifier_ledger.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], metric_ledger_csv(metric_rows), output_root)
        atomic_text(output_files[3], native_theta_inputs_csv(theta_rows), output_root)
        atomic_text(output_files[4], modifier_ledger_csv(modifier_rows), output_root)
        write_hash_manifest(input_paths, output_files[5], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "e66_metric_rows": len(metric_rows),
            "native_theta_input_rows": len(theta_rows),
            "followon_modifier_rows": len(modifier_rows),
            "E68_retained_tissue_rows_recalculated": audit[
                "E68_limited_modifier"
            ]["lineage_rows"],
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l21_ancestry_selects_pen_audit(args: argparse.Namespace) -> int:
    """Audit L21's retained ancestry-selection result and bounded follow-on."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L21_ANCESTRY_SELECTS_PEN_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L21 retained ancestry-selection audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
                "E69_population_rows_recalculated": 25,
                "E69_trajectory_records_recalculated": 400,
                "E71_race_rows_recalculated": 30,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l21_audit import (
            markdown_report,
            population_ledger_csv,
            race_ledger_csv,
            run_l21_audit,
        )

        (
            audit,
            input_paths,
            population_rows,
            race_rows,
            frozen_input_hashes,
        ) = run_l21_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L21 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L21 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "e69_population_ledger.csv",
            output_dir / "e71_race_ledger.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(
            output_files[2], population_ledger_csv(population_rows), output_root
        )
        atomic_text(output_files[3], race_ledger_csv(race_rows), output_root)
        write_hash_manifest(input_paths, output_files[4], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "E69_population_rows_recalculated": len(population_rows),
            "E69_trajectory_records_recalculated": audit[
                "E69_ancestry_world"
            ]["trajectory_records"],
            "E71_race_rows_recalculated": len(race_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l22_body_proofreads_gene_audit(args: argparse.Namespace) -> int:
    """Audit L22's retained E68 threshold and proofreading interpretation."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L22_BODY_PROOFREADS_GENE_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L22 retained proofreading audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
                "E68_tissue_rows_recalculated": 48,
                "E68_curve_conditions_recalculated": 16,
                "projection_identity_checks": 8,
                "comparison_currency_rows": 3,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l22_audit import (
            curve_ledger_csv,
            hierarchy_currency_csv,
            markdown_report,
            run_l22_audit,
            tissue_trajectory_csv,
        )

        (
            audit,
            input_paths,
            curve_rows,
            tissue_rows,
            hierarchy_rows,
            frozen_input_hashes,
        ) = run_l22_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L22 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L22 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "e68_curve_diagnostics.csv",
            output_dir / "e68_tissue_trajectories.csv",
            output_dir / "hierarchy_currency.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], curve_ledger_csv(curve_rows), output_root)
        atomic_text(output_files[3], tissue_trajectory_csv(tissue_rows), output_root)
        atomic_text(
            output_files[4], hierarchy_currency_csv(hierarchy_rows), output_root
        )
        write_hash_manifest(input_paths, output_files[5], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "E68_tissue_rows_recalculated": len(tissue_rows),
            "E68_curve_conditions_recalculated": len(curve_rows),
            "projection_identity_checks": audit[
                "deterministic_projection_identity_checks"
            ],
            "comparison_currency_rows": len(hierarchy_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l23_words_balance_books_audit(args: argparse.Namespace) -> int:
    """Audit L23's retained E67 composition, capacity, and discreteness."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L23_WORDS_BALANCE_BOOKS_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L23 retained composition/capacity/discreteness audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
                "static_launch_forms_planned": 4,
                "ordered_pair_eligibility_rows_planned": 12,
                "capacity_rows_recalculated": 6,
                "discreteness_curve_rows_recalculated": 11,
                "start_dependence_rows_recalculated": 5,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l23_audit import (
            capacity_ledger_csv,
            discreteness_curve_csv,
            form_ledger_csv,
            hysteresis_ledger_csv,
            markdown_report,
            pair_ledger_csv,
            run_l23_audit,
        )

        (
            audit,
            input_paths,
            form_rows,
            pair_rows,
            capacity_rows,
            curve_rows,
            hysteresis_rows,
            frozen_input_hashes,
        ) = run_l23_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L23 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L23 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "form_ledger.csv",
            output_dir / "pair_eligibility.csv",
            output_dir / "capacity_ledger.csv",
            output_dir / "discreteness_curve.csv",
            output_dir / "start_dependence.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], form_ledger_csv(form_rows), output_root)
        atomic_text(output_files[3], pair_ledger_csv(pair_rows), output_root)
        atomic_text(output_files[4], capacity_ledger_csv(capacity_rows), output_root)
        atomic_text(output_files[5], discreteness_curve_csv(curve_rows), output_root)
        atomic_text(
            output_files[6], hysteresis_ledger_csv(hysteresis_rows), output_root
        )
        write_hash_manifest(input_paths, output_files[7], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "static_launch_forms_reconstructed": len(form_rows),
            "ordered_pair_eligibility_rows": len(pair_rows),
            "capacity_rows_recalculated": len(capacity_rows),
            "discreteness_curve_rows_recalculated": len(curve_rows),
            "start_dependence_rows_recalculated": len(hysteresis_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def l24_slow_writing_germline_barrier_audit(args: argparse.Namespace) -> int:
    """Audit L24's retained E70 pre-round, evolution, and channel evidence."""

    started_monotonic = time.monotonic()
    output_root = external_root(args.external_root)
    _configure_runtime(output_root)
    run_id = _validate_run_id(args.run_id)
    plastic_root = Path(args.plastic_heredity_root).expanduser().resolve()
    if not (plastic_root / "PRE_PRINT_PAPER_DRAFT_V2.3.md").is_file():
        raise FileNotFoundError(f"not a PlasticHeredity root: {plastic_root}")

    output_dir = output_root / "outputs" / run_id
    run_dir = output_root / "runs" / run_id
    if output_dir.exists() or run_dir.exists():
        raise FileExistsError(
            f"immutable run ID already exists; choose a new --run-id: {run_id}"
        )
    run_dir.mkdir(parents=True)
    disk = _disk_manifest(output_root, estimated_output_bytes=4 * 1024 * 1024)
    if not disk["preflight_pass"]:
        raise RuntimeError("external disk preflight failed")

    workspace = Path(__file__).resolve().parents[2]
    protocol = workspace / "protocols/L24_SLOW_WRITING_GERMLINE_BARRIER_AUDIT_V1.md"
    protocol_hashes = {str(protocol): sha256_file(protocol)}
    code_files = sorted((Path(__file__).resolve().parent).glob("*.py"))
    code_hashes = {str(path): sha256_file(path) for path in code_files}
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "stage": "L24 retained Weismann/slow-writing audit",
        "status": "RUNNING",
        "started_utc": utc_now(),
        "plastic_heredity_root": str(plastic_root),
        "external_root": str(output_root),
        "output_dir": str(output_dir),
        "protocol_sha256": protocol_hashes,
        "code_sha256": code_hashes,
        "contract_digest": canonical_digest(
            {
                "protocol_sha256": protocol_hashes,
                "code_sha256": code_hashes,
                "fresh_scientific_futures_planned": 0,
                "historical_simulator_futures_planned": 0,
                "retained_evolution_rows_planned": 20,
                "retained_trajectory_rows_planned": 320,
                "paired_rows_planned": 5,
                "clock_rows_planned": 4,
                "preround_rows_planned": 3,
            }
        ),
        "repository_head": git_head(workspace),
        "workers": 1,
        "fresh_scientific_futures_planned": 0,
        "historical_simulator_futures_planned": 0,
        "outcome_blinding": "none; explicitly outcome-known first-pass audit",
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
        from .l24_audit import (
            clock_ledger_csv,
            evolution_ledger_csv,
            markdown_report,
            paired_ledger_csv,
            preround_ledger_csv,
            run_l24_audit,
            trajectory_ledger_csv,
        )

        (
            audit,
            input_paths,
            evolution_rows,
            paired_rows,
            trajectory_rows,
            clock_rows,
            preround_rows,
            frozen_input_hashes,
        ) = run_l24_audit(plastic_root, workspace)
        audit["contract_digest"] = manifest["contract_digest"]
        changed_protocols = [
            path
            for path, digest in protocol_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_protocols:
            raise RuntimeError(
                f"frozen L24 protocol changed during the run: {changed_protocols}"
            )
        changed_code = [
            path
            for path, digest in code_hashes.items()
            if sha256_file(Path(path)) != digest
        ]
        if changed_code:
            raise RuntimeError(f"audit code changed during the run: {changed_code}")
        changed_inputs = [
            str(path)
            for path, digest in frozen_input_hashes.items()
            if sha256_file(path) != digest
        ]
        if changed_inputs:
            raise RuntimeError(f"L24 input changed before finalization: {changed_inputs}")

        output_dir.mkdir(parents=True)
        output_files = [
            output_dir / "audit.json",
            output_dir / "audit.md",
            output_dir / "evolution_ledger.csv",
            output_dir / "paired_contrasts.csv",
            output_dir / "generation_trajectories.csv",
            output_dir / "clock_ledger.csv",
            output_dir / "preround_ledger.csv",
            output_dir / "input_hashes.sha256",
        ]
        atomic_json(output_files[0], audit, output_root)
        atomic_text(output_files[1], markdown_report(audit), output_root)
        atomic_text(output_files[2], evolution_ledger_csv(evolution_rows), output_root)
        atomic_text(output_files[3], paired_ledger_csv(paired_rows), output_root)
        atomic_text(
            output_files[4], trajectory_ledger_csv(trajectory_rows), output_root
        )
        atomic_text(output_files[5], clock_ledger_csv(clock_rows), output_root)
        atomic_text(output_files[6], preround_ledger_csv(preround_rows), output_root)
        write_hash_manifest(input_paths, output_files[7], output_root)
        completed = {
            "status": "COMPLETE",
            "completed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "input_file_count": len(input_paths),
            "evolution_rows_reconstructed": len(evolution_rows),
            "paired_rows_reconstructed": len(paired_rows),
            "trajectory_rows_exported": len(trajectory_rows),
            "clock_rows_reconstructed": len(clock_rows),
            "preround_rows_reconstructed": len(preround_rows),
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "output_files": [str(path) for path in output_files],
            "output_sha256": {path.name: sha256_file(path) for path in output_files},
        }
        atomic_json(run_dir / "STATUS.json", completed, output_root)
        atomic_text(run_dir / "COMPLETE", completed["completed_utc"] + "\n", output_root)
        print(output_dir / "audit.md")
        return 0
    except Exception as error:
        failure = {
            "status": "FAILED",
            "failed_utc": utc_now(),
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        atomic_json(run_dir / "STATUS.json", failure, output_root)
        atomic_text(run_dir / "FAILED", failure["failed_utc"] + "\n", output_root)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="laws-confirm")
    subparsers = parser.add_subparsers(dest="command", required=True)
    retained = subparsers.add_parser(
        "retained-audit", help="recalculate retained L01/L02 ECA artefacts"
    )
    retained.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    retained.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    retained.add_argument(
        "--run-id",
        default="l01_l02_eca_audit_v1_1",
    )
    retained.set_defaults(handler=retained_audit)
    l3 = subparsers.add_parser(
        "l3-retained-audit", help="recalculate retained L03 atlas and translation artefacts"
    )
    l3.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l3.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l3.add_argument(
        "--run-id",
        default="l03_retained_audit_v1",
    )
    l3.set_defaults(handler=l3_retained_audit)
    l4 = subparsers.add_parser(
        "l4-retained-audit",
        help="audit retained L04 observer evidence and replay E28 horizons",
    )
    l4.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l4.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l4.add_argument(
        "--run-id",
        default="l04_retained_audit_v1",
    )
    l4.set_defaults(handler=l4_retained_audit)
    l5 = subparsers.add_parser(
        "l5-retained-audit",
        help="audit retained L05 conservation-selfhood evidence",
    )
    l5.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l5.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l5.add_argument(
        "--run-id",
        default="l05_retained_audit_v1",
    )
    l5.set_defaults(handler=l5_retained_audit)
    l6 = subparsers.add_parser(
        "l6-retained-replay-audit",
        help="audit retained L06 graft evidence and replay E29's historical axis",
    )
    l6.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l6.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l6.add_argument(
        "--run-id",
        default="l06_retained_replay_audit_v1",
    )
    l6.set_defaults(handler=l6_retained_replay_audit)
    l7 = subparsers.add_parser(
        "l7-retained-audit",
        help="audit retained L07 learning and history-dependence evidence",
    )
    l7.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l7.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l7.add_argument(
        "--run-id",
        default="l07_retained_audit_v1",
    )
    l7.set_defaults(handler=l7_retained_audit)
    l8 = subparsers.add_parser(
        "l8-retained-replay-audit",
        help="audit retained L08 evidence and replay E39's fixed current-source paths",
    )
    l8.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l8.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l8.add_argument(
        "--run-id",
        default="l08_retained_replay_audit_v1",
    )
    l8.set_defaults(handler=l8_retained_replay_audit)
    l9 = subparsers.add_parser(
        "l9-retained-audit",
        help="audit retained L09 triangle and resolution-theorem evidence",
    )
    l9.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l9.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l9.add_argument(
        "--run-id",
        default="l09_retained_audit_v1",
    )
    l9.set_defaults(handler=l9_retained_audit)
    l10 = subparsers.add_parser(
        "l10-retained-replay-audit",
        help="audit L10 honest-stress evidence and replay its cessation rows",
    )
    l10.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l10.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l10.add_argument(
        "--run-id",
        default="l10_retained_replay_audit_v1",
    )
    l10.set_defaults(handler=l10_retained_replay_audit)
    l11 = subparsers.add_parser(
        "l11-retained-replay-audit",
        help="audit L11 greedy-trap evidence and replay E46 trap paths",
    )
    l11.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l11.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l11.add_argument(
        "--run-id",
        default="l11_retained_replay_audit_v1",
    )
    l11.set_defaults(handler=l11_retained_replay_audit)
    l12 = subparsers.add_parser(
        "l12-retained-replay-audit",
        help="audit L12 single-road evidence and re-instrument historical maps",
    )
    l12.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l12.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l12.add_argument(
        "--run-id",
        default="l12_retained_replay_audit_v1",
    )
    l12.set_defaults(handler=l12_retained_replay_audit)
    l13 = subparsers.add_parser(
        "l13-prophecy-census",
        help="audit L13's retained interpolation/extrapolation prophecy census",
    )
    l13.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l13.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l13.add_argument(
        "--run-id",
        default="l13_prophecy_census_v1",
    )
    l13.set_defaults(handler=l13_prophecy_census)
    l14 = subparsers.add_parser(
        "l14-price-order-ledger",
        help="audit L14's price metaphor with a retained engineering/search ledger",
    )
    l14.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l14.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l14.add_argument(
        "--run-id",
        default="l14_price_order_ledger_v1",
    )
    l14.set_defaults(handler=l14_price_order_ledger)
    l15 = subparsers.add_parser(
        "l15-timescale-audit",
        help="audit L15's retained gain/rho surface, dynamics, and category claims",
    )
    l15.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l15.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l15.add_argument(
        "--prior-l10-audit",
        default=None,
    )
    l15.add_argument(
        "--run-id",
        default="l15_timescale_audit_v1",
    )
    l15.set_defaults(handler=l15_timescale_audit)
    l16 = subparsers.add_parser(
        "l16-landlord-tenant-audit",
        help="audit L16's retained carrier, alignment, and horizon evidence",
    )
    l16.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l16.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l16.add_argument(
        "--run-id",
        default="l16_landlord_tenant_audit_v1",
    )
    l16.set_defaults(handler=l16_landlord_tenant_audit)
    l17 = subparsers.add_parser(
        "l17-development-heredity-audit",
        help="audit L17's retained fixed-ancestor, channel, and portability evidence",
    )
    l17.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l17.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l17.add_argument(
        "--run-id",
        default="l17_development_heredity_audit_v1",
    )
    l17.set_defaults(handler=l17_development_heredity_audit)
    l18 = subparsers.add_parser(
        "l18-takeover-bounded-audit",
        help="audit L18's retained scaffold crossover and selection evidence",
    )
    l18.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l18.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l18.add_argument(
        "--run-id",
        default="l18_takeover_bounded_audit_v1",
    )
    l18.set_defaults(handler=l18_takeover_bounded_audit)
    l19 = subparsers.add_parser(
        "l19-incorruptible-reference-audit",
        help="audit L19's retained clock, instruction, and cascade evidence",
    )
    l19.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l19.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l19.add_argument(
        "--run-id",
        default="l19_incorruptible_reference_audit_v1",
    )
    l19.set_defaults(handler=l19_incorruptible_reference_audit)
    l20 = subparsers.add_parser(
        "l20-self-written-genome-audit",
        help="audit L20's writable-theta result and E67/E68 modifiers",
    )
    l20.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l20.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l20.add_argument(
        "--run-id",
        default="l20_self_written_genome_audit_v1_attempt2",
    )
    l20.set_defaults(handler=l20_self_written_genome_audit)
    l21 = subparsers.add_parser(
        "l21-ancestry-selects-pen-audit",
        help="audit L21's E69 ancestry result and bounded E64/E71 context",
    )
    l21.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l21.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l21.add_argument(
        "--run-id",
        default="l21_ancestry_selects_pen_audit_v1",
    )
    l21.set_defaults(handler=l21_ancestry_selects_pen_audit)
    l22 = subparsers.add_parser(
        "l22-body-proofreads-gene-audit",
        help="audit L22's E68 threshold and E55/E65/E67 comparison context",
    )
    l22.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l22.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l22.add_argument(
        "--run-id",
        default="l22_body_proofreads_gene_audit_v1",
    )
    l22.set_defaults(handler=l22_body_proofreads_gene_audit)
    l23 = subparsers.add_parser(
        "l23-words-balance-books-audit",
        help="audit L23's E67 composition, capacity, and discreteness evidence",
    )
    l23.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l23.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l23.add_argument(
        "--run-id",
        default="l23_words_balance_books_audit_v1",
    )
    l23.set_defaults(handler=l23_words_balance_books_audit)
    l24 = subparsers.add_parser(
        "l24-slow-writing-germline-barrier-audit",
        help="audit L24's E70 void, timing, leak observer, and evolution evidence",
    )
    l24.add_argument(
        "--plastic-heredity-root",
        default=str(_default_plastic_root()),
    )
    l24.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    l24.add_argument(
        "--run-id",
        default="l24_slow_writing_germline_barrier_audit_v1",
    )
    l24.set_defaults(handler=l24_slow_writing_germline_barrier_audit)
    benchmark = subparsers.add_parser(
        "stage-c-benchmark", help="run the outcome-blind A1 runtime benchmark"
    )
    benchmark.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    benchmark.add_argument(
        "--run-id",
        default="l01_l02_stage_c_benchmark_v1",
    )
    benchmark.add_argument("--workers", type=int, default=4)
    benchmark.set_defaults(handler=stage_c_benchmark)
    fresh = subparsers.add_parser(
        "stage-d-a1", help="run or resume the frozen fresh A1 ECA campaign"
    )
    fresh.add_argument(
        "--external-root",
        default=str(DEFAULT_EXTERNAL_ROOT),
    )
    fresh.add_argument(
        "--run-id",
        default="l01_l02_stage_d_a1_v1",
    )
    fresh.add_argument("--workers", type=int, default=4)
    fresh.add_argument("--resume", action="store_true")
    fresh.set_defaults(handler=stage_d_a1)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    raise SystemExit(result)
