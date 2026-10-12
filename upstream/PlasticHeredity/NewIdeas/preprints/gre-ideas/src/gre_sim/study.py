"""Top-level immutable study lifecycle, verification, and replay."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from .analysis import analyze_records
from .artifacts import (
    atomic_destination,
    canonical_digest,
    read_json,
    read_jsonl_gz,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
    write_jsonl_gz,
)
from .campaign import (
    _arm_values,
    build_registry,
    expected_future_count,
    run_registry,
    simulate_v2_cell_half,
)
from .config import (
    StudySpec,
    analysis_format,
    raw_format,
    registration_format,
)
from .endpoints import simulate_future
from .reporting import render_report, write_figures
from .rng import rng_for
from .validation import validate_implementation


def source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    files = sorted((root / "src" / "gre_sim").glob("*.py"))
    files.extend(
        path
        for path in (
            root / "pyproject.toml",
            root / "requirements-lock.txt",
            root / "IMPLEMENTATION_PROTOCOL.md",
        )
        if path.is_file()
    )
    return {str(path.relative_to(root)): sha256_file(path) for path in files}


def run_study(
    spec: StudySpec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if progress is not None:
        progress("validating deterministic implementation fixtures")
    validation = validate_implementation()
    started = time.monotonic()
    registration = {
        "format": registration_format(spec.protocol_format),
        "protocol": spec.to_dict(),
        "protocol_digest": canonical_digest(spec.to_dict()),
    }
    with atomic_destination(destination) as temporary:
        write_json(temporary / "registration.json", registration)
        write_json(temporary / "validation.json", validation)
        if progress is not None:
            progress("building sampled and evolved rulebook registry")
        registry = build_registry(spec, workers, progress)
        write_json(temporary / "rulebooks.json", registry)
        if progress is not None:
            progress("running repeated-cycle futures")
        records = run_registry(registry, spec, workers, progress)
        expected = expected_future_count(spec, registry)
        if len(records) != expected:
            raise RuntimeError(f"campaign produced {len(records)} records; expected {expected}")
        record_count = write_jsonl_gz(temporary / "futures.jsonl.gz", records)
        if progress is not None:
            progress("cross-fitting committors and dynamical baselines")
        analysis = analyze_records(records, registry, spec)
        write_json(temporary / "analysis.json", analysis)
        figures = write_figures(temporary / "figures", analysis, registry)
        elapsed = time.monotonic() - started
        manifest = {
            "format": "gre-runtime-manifest-v1",
            "mode": spec.mode,
            "cohort_id": spec.cohort_id,
            "protocol_digest": registration["protocol_digest"],
            "raw_format": raw_format(spec.protocol_format),
            "record_count": record_count,
            "expected_record_count": expected,
            "source_rulebooks": len(registry["sources"]),
            "workers": workers,
            "elapsed_seconds": elapsed,
            "runtime": runtime_manifest(),
            "source_hashes": source_hashes(),
            "figures": figures,
        }
        write_json(temporary / "manifest.json", manifest)
        (temporary / "report.md").write_text(
            render_report(analysis, registry, manifest), encoding="utf-8"
        )
        write_checksums(temporary)
        if progress is not None:
            progress("sealed report, figures, manifests, and checksums")
    return destination.resolve()


def load_run(directory: Path) -> tuple[StudySpec, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    registration = read_json(directory / "registration.json")
    spec = StudySpec.from_dict(registration["protocol"])
    registry = read_json(directory / "rulebooks.json")
    records = list(read_jsonl_gz(directory / "futures.jsonl.gz"))
    analysis = read_json(directory / "analysis.json")
    return spec, registry, records, analysis


def verify_run(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    spec = StudySpec.from_dict(registration["protocol"])
    if registration.get("format") != registration_format(spec.protocol_format):
        raise ValueError("registration format mismatch")
    if manifest.get("raw_format") != raw_format(spec.protocol_format):
        raise ValueError("raw format mismatch")
    protocol_digest = canonical_digest(registration["protocol"])
    if protocol_digest != registration["protocol_digest"]:
        raise ValueError("registration protocol digest mismatch")
    if protocol_digest != manifest["protocol_digest"]:
        raise ValueError("manifest protocol digest mismatch")
    registry = read_json(directory / "rulebooks.json")
    archived_analysis = read_json(directory / "analysis.json")
    if archived_analysis.get("format") != analysis_format(spec.protocol_format):
        raise ValueError("analysis format mismatch")
    records = list(read_jsonl_gz(directory / "futures.jsonl.gz"))
    actual_records = len(records)
    if actual_records != manifest["record_count"]:
        raise ValueError("record count mismatch")
    expected = expected_future_count(spec, registry)
    if actual_records != expected or manifest.get("expected_record_count") != expected:
        raise ValueError("expected record count mismatch")
    if spec.is_v2:
        half_size = spec.futures_per_cell // 2
        for record in records:
            mode = record.get("inheritance_mode")
            if mode not in spec.inheritance_modes:
                raise ValueError("missing or invalid v2 inheritance mode")
            expected_half = "A" if int(record["future_index"]) < half_size else "B"
            if record.get("half") != expected_half:
                raise ValueError("v2 future half mismatch")
    return {
        "verified": True,
        "files": len(checksums),
        "records": actual_records,
        "protocol_digest": protocol_digest,
    }


def recompute_analysis(directory: Path) -> dict[str, Any]:
    spec, registry, records, archived = load_run(directory)
    recomputed = analyze_records(records, registry, spec)
    return {
        "matches": canonical_digest(recomputed) == canonical_digest(archived),
        "analysis": recomputed,
    }


def replay_future(directory: Path, future_id: str) -> dict[str, Any]:
    spec, registry, records, _ = load_run(directory)
    archived = next((record for record in records if record["future_id"] == future_id), None)
    if archived is None:
        raise KeyError(f"unknown future id: {future_id}")
    bundle = next(
        value for value in registry["sources"] if value["source_id"] == archived["source_id"]
    )
    launch = next(
        value
        for value in bundle["launches"]
        if int(value["state_id"]) == int(archived["state_id"])
    )
    if spec.is_v2:
        inheritance_mode = archived.get("inheritance_mode")
        if inheritance_mode not in spec.inheritance_modes:
            raise ValueError("missing or invalid v2 inheritance mode")
        results = simulate_v2_cell_half(
            bundle,
            launch,
            str(archived["arm"]),
            float(archived["carryover"]),
            str(inheritance_mode),
            str(archived["half"]),
            spec,
        )
        _, summary, observations = next(
            value
            for value in results
            if int(value[0]) == int(archived["future_index"])
        )
        replayed = {
            "destination": summary.destination,
            "strict_event": summary.strict_event,
            "first_break": summary.first_break,
            "stable_destination_cycle": summary.stable_destination_cycle,
            "active_capture": summary.active_capture,
            "old_return": summary.old_return,
            "point_cycles": summary.point_cycles,
            "cycle_cycles": summary.cycle_cycles,
            "nonconvergent_cycles": summary.nonconvergent_cycles,
            "trace_digest": summary.trace_digest,
        }
        matches = all(archived[name] == value for name, value in replayed.items())
        return {
            "future_id": future_id,
            "matches": matches,
            "archived": {name: archived[name] for name in replayed},
            "replayed": replayed,
            "observations": [
                {
                    "cycle_index": item.cycle_index,
                    "status": item.status,
                    "adult_state": item.adult_state,
                    "steps": item.steps,
                    "destination": item.destination,
                }
                for item in observations
            ],
        }
    active, base_state, previous_state, old_state = _arm_values(
        bundle, launch, archived["arm"]
    )
    flip_probability = (
        spec.boolean.expression_flip_probability
        if archived["engine"] == "boolean"
        else spec.wagner.expression_flip_probability
    )
    rng = rng_for(
        spec.master_seed,
        "future",
        archived["engine"],
        archived["cohort"],
        archived["source_id"],
        int(archived["state_id"]),
        archived["arm"],
        float(archived["carryover"]),
        int(archived["future_index"]),
        "fallback",
    )
    cycle_rngs = tuple(
        (
            rng_for(
                spec.master_seed,
                "future",
                archived["engine"],
                archived["cohort"],
                archived["source_id"],
                int(archived["state_id"]),
                archived["arm"],
                float(archived["carryover"]),
                int(archived["future_index"]),
                cycle_index,
                "carryover",
            ),
            rng_for(
                spec.master_seed,
                "future",
                archived["engine"],
                archived["cohort"],
                archived["source_id"],
                int(archived["state_id"]),
                archived["arm"],
                float(archived["carryover"]),
                int(archived["future_index"]),
                cycle_index,
                "dynamics",
            ),
        )
        for cycle_index in range(spec.horizon)
    )
    summary, observations = simulate_future(
        active,
        active.landscape(),
        base_state,
        previous_state,
        old_state,
        float(archived["carryover"]),
        flip_probability,
        spec.horizon,
        spec.stable_destination_run,
        spec.strict_run,
        spec.old_distinct_distance,
        rng,
        spec.wagner.gamma_variance if archived["engine"] == "wagner" else 0.0,
        spec.wagner.max_sweeps,
        cycle_rngs,
    )
    replayed = {
        "destination": summary.destination,
        "strict_event": summary.strict_event,
        "first_break": summary.first_break,
        "stable_destination_cycle": summary.stable_destination_cycle,
        "active_capture": summary.active_capture,
        "old_return": summary.old_return,
        "point_cycles": summary.point_cycles,
        "cycle_cycles": summary.cycle_cycles,
        "nonconvergent_cycles": summary.nonconvergent_cycles,
        "trace_digest": summary.trace_digest,
    }
    matches = all(archived[name] == value for name, value in replayed.items())
    return {
        "future_id": future_id,
        "matches": matches,
        "archived": {name: archived[name] for name in replayed},
        "replayed": replayed,
        "observations": [
            {
                "cycle_index": item.cycle_index,
                "status": item.status,
                "adult_state": item.adult_state,
                "steps": item.steps,
                "destination": item.destination,
            }
            for item in observations
        ],
    }
