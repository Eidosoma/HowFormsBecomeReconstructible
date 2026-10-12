"""Checkpointed v2 state-channel execution, verification, and replay."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .plastic_heredity_v2_analysis import (
    analyze_state_channel_path,
    render_state_channel_report,
)
from .plastic_heredity_v2_config import (
    PLASTIC_HEREDITY_V2_REGISTRATION_FORMAT,
    PlasticHeredityV2Spec,
)
from .plastic_memory_campaign import expected_memory_futures
from .plastic_memory_study import (
    replay_memory_future,
    run_memory_study,
    verify_memory_run,
)


V2_STATE_STUDY_REGISTRATION_FORMAT = "gre-plastic-heredity-v2-study-registration-v1"
V2_STATE_STUDY_MANIFEST_FORMAT = "gre-plastic-heredity-v2-study-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def run_v2_state_study(
    spec: PlasticHeredityV2Spec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or resume one independently sealed v2 state-channel phase."""

    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("Plastic Heredity v2 studies require 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_v2_state_study(destination)
        if progress is not None:
            progress("v2 state study already sealed; verified without mutation")
        return destination
    started = time.monotonic()
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": V2_STATE_STUDY_REGISTRATION_FORMAT,
        "campaign_format": PLASTIC_HEREDITY_V2_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
        "executor": "gre-plastic-memory-study-v1-compatible",
        "scientific_analysis": "gre-plastic-heredity-v2-analysis-v1",
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing v2 state study registration differs")
    else:
        _atomic_json(registration_path, registration)
    _atomic_json(destination / "protocol.json", spec.to_dict())
    memory_spec = spec.memory_spec()
    executor = run_memory_study(
        memory_spec,
        destination / "executor",
        workers,
        progress,
    )
    if progress is not None:
        progress("computing Plastic Heredity v2 channel gates and engine verdict")
    analysis = analyze_state_channel_path(executor / "futures.jsonl.gz", spec)
    _atomic_json(destination / "analysis.json", analysis)
    executor_manifest = read_json(executor / "manifest.json")
    registry = read_json(executor / "rulebooks.json")
    expected = expected_memory_futures(memory_spec, registry)
    if analysis["record_count"] != expected:
        raise RuntimeError("v2 state analysis record count does not match registration")
    manifest = {
        "format": V2_STATE_STUDY_MANIFEST_FORMAT,
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "protocol_digest": digest,
        "executor_checksum_digest": sha256_file(executor / "SHA256SUMS"),
        "record_count": analysis["record_count"],
        "expected_record_count": expected,
        "source_rulebooks": len(registry["sources"]),
        "source_count_per_engine": spec.source_count_per_engine,
        "workers": workers,
        "elapsed_seconds": time.monotonic() - started,
        "executor_elapsed_seconds": executor_manifest["elapsed_seconds"],
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "manifest.json", manifest)
    (destination / "report.md").write_text(
        render_state_channel_report(analysis), encoding="utf-8"
    )
    write_checksums(destination)
    verify_v2_state_study(destination)
    if progress is not None:
        progress("sealed Plastic Heredity v2 state-channel phase")
    return destination


def verify_v2_state_study(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != V2_STATE_STUDY_REGISTRATION_FORMAT:
        raise ValueError("v2 state-study registration format mismatch")
    if manifest.get("format") != V2_STATE_STUDY_MANIFEST_FORMAT:
        raise ValueError("v2 state-study manifest format mismatch")
    spec = PlasticHeredityV2Spec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("v2 state-study protocol digest mismatch")
    child = verify_memory_run(directory / "executor")
    if sha256_file(directory / "executor" / "SHA256SUMS") != manifest.get(
        "executor_checksum_digest"
    ):
        raise ValueError("v2 state-study executor checksum digest mismatch")
    analysis = read_json(directory / "analysis.json")
    if int(analysis["record_count"]) != int(manifest["record_count"]):
        raise ValueError("v2 state-study analysis record count mismatch")
    return {
        "verified": True,
        "files": len(checksums),
        "records": int(manifest["record_count"]),
        "protocol_digest": digest,
        "executor": child,
    }


def replay_v2_state_future(directory: Path, future_id: str) -> dict[str, Any]:
    result = replay_memory_future(directory / "executor", future_id)
    return {
        "format": "gre-plastic-heredity-v2-replay-v1",
        "stage": str(directory.resolve()),
        **result,
    }
