"""Immutable lifecycle, verification, replay, and synthesis for mechanism runs."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from .artifacts import (
    atomic_destination,
    canonical_digest,
    read_json,
    read_jsonl_gz,
    runtime_manifest,
    verify_checksums,
    write_checksums,
    write_json,
    write_jsonl_gz,
)
from .mechanism_analysis import analyze_mechanism_records
from .mechanism_campaign import (
    build_mechanism_registry,
    expected_registry_futures,
    iter_mechanism_records,
    simulate_mechanism_source,
)
from .mechanism_config import (
    MECHANISM_ANALYSIS_FORMAT,
    MECHANISM_RAW_FORMAT,
    MECHANISM_REGISTRATION_FORMAT,
    MechanismCondition,
    MechanismSpec,
)
from .mechanism_reporting import render_mechanism_report, write_mechanism_figures
from .study import source_hashes
from .validation import validate_implementation


SUMMARY_FIELDS = (
    "frozen_destination",
    "point_state_destination",
    "signature_destination",
    "competing_outcome",
    "active_capture",
    "stable_point_capture",
    "stable_signature_capture",
    "strict_library",
    "strict_state",
    "strict_library_by_run",
    "strict_state_by_run",
    "max_library_run",
    "max_point_state_run",
    "max_signature_run",
    "first_break",
    "old_return",
    "point_cycles",
    "cycle_cycles",
    "nonconvergent_cycles",
    "unique_adult_states",
    "donor_reassignments",
    "donor_fallbacks",
    "trace_digest",
)


def run_mechanism_study(
    spec: MechanismSpec,
    destination: Path,
    parent_run: Path | None = None,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if progress is not None:
        progress("validating unchanged GRE implementation fixtures")
    validation = validate_implementation()
    started = time.monotonic()
    registration = {
        "format": MECHANISM_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
        "parent_run": str(parent_run.resolve()) if parent_run is not None else None,
    }
    with atomic_destination(destination) as temporary:
        write_json(temporary / "registration.json", registration)
        write_json(temporary / "validation.json", validation)
        if progress is not None:
            progress("building or importing mechanism rulebooks")
        registry = build_mechanism_registry(spec, parent_run, progress)
        write_json(temporary / "rulebooks.json", registry)
        expected = expected_registry_futures(spec, registry)
        if progress is not None:
            progress(f"streaming {expected:,} registered mechanism futures")
        record_count = write_jsonl_gz(
            temporary / "futures.jsonl.gz",
            iter_mechanism_records(registry, spec, workers, progress),
        )
        if record_count != expected:
            raise RuntimeError(
                f"mechanism phase produced {record_count} records; expected {expected}"
            )
        if progress is not None:
            progress("cross-fitting inclusive destination endpoints")
        analysis = analyze_mechanism_records(temporary / "futures.jsonl.gz", spec)
        write_json(temporary / "analysis.json", analysis)
        figures = write_mechanism_figures(temporary / "figures", analysis)
        elapsed = time.monotonic() - started
        manifest = {
            "format": "gre-mechanism-runtime-manifest-v1",
            "cohort_id": spec.cohort_id,
            "phase": spec.phase,
            "protocol_digest": registration["protocol_digest"],
            "raw_format": MECHANISM_RAW_FORMAT,
            "analysis_format": MECHANISM_ANALYSIS_FORMAT,
            "record_count": record_count,
            "expected_record_count": expected,
            "source_rulebooks": len(registry["sources"]),
            "workers": workers,
            "elapsed_seconds": elapsed,
            "runtime": runtime_manifest(),
            "source_hashes": source_hashes(),
            "figures": figures,
            "parent_protocol_digest": spec.parent_protocol_digest,
        }
        write_json(temporary / "manifest.json", manifest)
        (temporary / "report.md").write_text(
            render_mechanism_report(analysis, registry, manifest),
            encoding="utf-8",
        )
        write_checksums(temporary)
        if progress is not None:
            progress("sealed mechanism phase and checksum manifest")
    return destination.resolve()


def load_mechanism_run(
    directory: Path,
) -> tuple[MechanismSpec, dict[str, Any], dict[str, Any]]:
    registration = read_json(directory / "registration.json")
    spec = MechanismSpec.from_dict(registration["protocol"])
    registry = read_json(directory / "rulebooks.json")
    analysis = read_json(directory / "analysis.json")
    return spec, registry, analysis


def verify_mechanism_run(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != MECHANISM_REGISTRATION_FORMAT:
        raise ValueError("mechanism registration format mismatch")
    spec = MechanismSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest"):
        raise ValueError("mechanism registration protocol digest mismatch")
    if digest != manifest.get("protocol_digest"):
        raise ValueError("mechanism manifest protocol digest mismatch")
    if manifest.get("raw_format") != MECHANISM_RAW_FORMAT:
        raise ValueError("mechanism raw format mismatch")
    analysis = read_json(directory / "analysis.json")
    if analysis.get("format") != MECHANISM_ANALYSIS_FORMAT:
        raise ValueError("mechanism analysis format mismatch")
    registry = read_json(directory / "rulebooks.json")
    expected = expected_registry_futures(spec, registry)
    count = 0
    seen: set[str] = set()
    halves_valid = True
    for record in read_jsonl_gz(directory / "futures.jsonl.gz"):
        count += 1
        future_id = str(record["future_id"])
        if future_id in seen:
            raise ValueError(f"duplicate mechanism future id: {future_id}")
        seen.add(future_id)
        condition = next(
            item for item in spec.conditions if item.name == record["condition"]
        )
        expected_half = (
            "A"
            if int(record["future_index"]) < condition.futures_per_cell // 2
            else "B"
        )
        halves_valid = halves_valid and record["half"] == expected_half
    if count != expected or count != manifest.get("record_count"):
        raise ValueError(
            f"mechanism record count mismatch: {count}, expected {expected}"
        )
    if not halves_valid:
        raise ValueError("mechanism future half mismatch")
    return {
        "verified": True,
        "files": len(checksums),
        "records": count,
        "unique_future_ids": len(seen),
        "protocol_digest": digest,
    }


def recompute_mechanism_analysis(directory: Path) -> dict[str, Any]:
    spec, _, archived = load_mechanism_run(directory)
    recomputed = analyze_mechanism_records(directory / "futures.jsonl.gz", spec)
    return {
        "matches": canonical_digest(recomputed) == canonical_digest(archived),
        "analysis": recomputed,
    }


def replay_mechanism_future(directory: Path, future_id: str) -> dict[str, Any]:
    spec, registry, _ = load_mechanism_run(directory)
    archived = next(
        (
            record
            for record in read_jsonl_gz(directory / "futures.jsonl.gz")
            if record["future_id"] == future_id
        ),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown mechanism future id: {future_id}")
    source = next(
        item for item in registry["sources"] if item["source_id"] == archived["source_id"]
    )
    original = next(
        item for item in spec.conditions if item.name == archived["condition"]
    )
    narrowed = MechanismCondition(
        name=original.name,
        source_set=original.source_set,
        variant=original.variant,
        arms=(str(archived["arm"]),),
        carryover_values=(float(archived["carryover"]),),
        inheritance_modes=(str(archived["inheritance_mode"]),),
        gamma_variances=(float(archived["gamma_variance"]),),
        futures_per_cell=original.futures_per_cell,
        compiled_update_mode=original.compiled_update_mode,
    )
    replay_spec = replace(spec, conditions=(narrowed,))
    replayed = next(
        record
        for record in simulate_mechanism_source(source, replay_spec.to_dict())
        if record["future_id"] == future_id
    )
    matches = all(archived[name] == replayed[name] for name in SUMMARY_FIELDS)
    return {
        "future_id": future_id,
        "matches": matches,
        "archived": {name: archived[name] for name in SUMMARY_FIELDS},
        "replayed": {name: replayed[name] for name in SUMMARY_FIELDS},
    }
