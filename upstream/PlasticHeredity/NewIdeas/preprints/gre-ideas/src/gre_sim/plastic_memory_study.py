"""Checkpointed lifecycle, verification, replay, and reporting for memory runs."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from .artifacts import (
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
from .plastic_memory_analysis import analyze_memory_records
from .plastic_memory_campaign import (
    build_memory_registry,
    expected_memory_futures,
    expected_memory_source_futures,
    iter_memory_source_results,
    simulate_memory_source,
)
from .plastic_memory_config import (
    PLASTIC_MEMORY_ANALYSIS_FORMAT,
    PLASTIC_MEMORY_RAW_FORMAT,
    PLASTIC_MEMORY_REGISTRATION_FORMAT,
    MemoryCondition,
    PlasticMemorySpec,
)
from .study import source_hashes


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _format_signed_estimate(value: Any, unit: str = "") -> str:
    """Render an optional gate estimate without mistaking absence for zero."""

    if value is None:
        return "not estimable"
    return f"{float(value):+.4f}{unit}"


def _render_report(analysis: dict[str, Any], manifest: dict[str, Any]) -> str:
    descriptor_rate = analysis["descriptor_exact_rate"]
    descriptor_text = (
        "not present" if descriptor_rate is None else f"{float(descriptor_rate):.3f}"
    )
    lines = [
        "# Plastic-memory causal campaign phase",
        "",
        (
            "> Exploratory evidence; candidate selection is allowed."
            if analysis["exploratory"]
            else "> Untouched fresh-cohort confirmation under the sealed conditional protocol."
        ),
        "",
        f"- Phase: `{analysis['phase']}`",
        f"- Futures: {analysis['record_count']:,}",
        f"- Independent rulebooks: {manifest['source_rulebooks']}",
        f"- Runtime: {manifest['elapsed_seconds'] / 3600:.2f} h",
        f"- Descriptor-matched exact rate: {descriptor_text}",
        "",
        "## Minimal state-transfer gate",
        "",
    ]
    if not analysis["state_transfer_gates"]:
        lines.append("This phase contains no state-transfer scientific gate.")
    for model, gate in analysis["state_transfer_gates"].items():
        risk = gate["metrics"]["risk_difference"]
        crossover = gate["metrics"]["crossover"]
        gain = gate["metrics"]["log_loss_gain"]
        lines.extend(
            (
                f"### {model}",
                "",
                f"- Passed: **{'yes' if gate['passed'] else 'no'}**",
                f"- Absolute correct-form hold-8 gain: {_format_signed_estimate(risk['mean'])} "
                f"(simultaneous lower {_format_signed_estimate(risk['lower'])})",
                f"- History-specific crossover: {_format_signed_estimate(crossover['mean'])} "
                f"(simultaneous lower {_format_signed_estimate(crossover['lower'])})",
                f"- Held-out log-loss gain: {_format_signed_estimate(gain['mean'], ' nats')} "
                f"(simultaneous lower {_format_signed_estimate(gain['lower'], ' nats')})",
                f"- Split-half reliability: {gate['split_half_reliability']}",
                "",
            )
        )
    lines.extend(("## Slow-mark recovery gate", ""))
    if not any(analysis["mark_transfer_gates"].values()):
        lines.append("This phase contains no active slow-mark gate.")
    for model, settings in analysis["mark_transfer_gates"].items():
        for mark, gate in settings.items():
            risk = gate["metrics"]["risk_difference"]
            lines.append(
                f"- `{model}` / `{mark}`: {'PASS' if gate['passed'] else 'fail'}, "
                f"forced-break hold-8 gain {_format_signed_estimate(risk['mean'])} "
                f"(lower {_format_signed_estimate(risk['lower'])})"
            )
    lines.extend(
        (
            "",
            "## Interpretation boundary",
            "",
            "A passing state transplant supports only minimal, material state inheritance. "
            "Forced-break recovery, descendant persistence, a slow-mark effect, cross-engine "
            "replication, GARD replication, and evolutionary response are separate stronger gates.",
            "",
        )
    )
    return "\n".join(lines)


def _valid_shard(
    shard: Path,
    manifest_path: Path,
    protocol_digest: str,
    source_id: str,
    expected_count: int,
) -> tuple[bool, int]:
    if not shard.is_file() or not manifest_path.is_file():
        return False, 0
    try:
        manifest = read_json(manifest_path)
        valid = (
            manifest.get("protocol_digest") == protocol_digest
            and manifest.get("source_id") == source_id
            and manifest.get("sha256") == sha256_file(shard)
            and int(manifest.get("record_count", -1)) == expected_count
        )
        return valid, int(manifest["record_count"]) if valid else 0
    except (OSError, ValueError, KeyError, TypeError):
        return False, 0


def run_memory_study(
    spec: PlasticMemorySpec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or resume one rulebook-sharded immutable memory phase."""

    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("plastic-memory study requires 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_memory_run(destination)
        if progress is not None:
            progress("memory phase already sealed; verified without mutation")
        return destination
    started = time.monotonic()
    progress_path = destination / "progress.json"
    prior_elapsed = 0.0
    if progress_path.is_file():
        try:
            prior_elapsed = max(0.0, float(read_json(progress_path).get("elapsed_seconds", 0.0)))
        except (OSError, ValueError, TypeError):
            prior_elapsed = 0.0
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": PLASTIC_MEMORY_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if canonical_digest(read_json(registration_path)) != canonical_digest(
            registration
        ):
            raise ValueError("existing memory phase uses a different registration")
    else:
        _atomic_json(registration_path, registration)

    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        registry = read_json(registry_path)
    else:
        registry = build_memory_registry(spec, progress)
        _atomic_json(registry_path, registry)
    expected = expected_memory_futures(spec, registry)
    shards = destination / "shards"
    shards.mkdir(exist_ok=True)
    completed_sources: set[str] = set()
    completed_records = 0
    for source in registry["sources"]:
        source_id = str(source["source_id"])
        shard = shards / f"{source_id}.jsonl.gz"
        shard_manifest = shards / f"{source_id}.manifest.json"
        valid, count = _valid_shard(
            shard,
            shard_manifest,
            protocol_digest,
            source_id,
            expected_memory_source_futures(spec, str(source["source_set"])),
        )
        if valid:
            completed_sources.add(source_id)
            completed_records += count
    missing = [
        source for source in registry["sources"] if source["source_id"] not in completed_sources
    ]
    if progress is not None:
        progress(
            f"memory phase resume: {len(completed_sources)}/{len(registry['sources'])} "
            f"sources, {completed_records:,}/{expected:,} futures sealed"
        )
    pending_registry = {**registry, "sources": missing}
    for source, records in iter_memory_source_results(
        pending_registry, spec, workers, progress
    ):
        source_id = str(source["source_id"])
        shard = shards / f"{source_id}.jsonl.gz"
        temporary = shards / f".{source_id}.jsonl.gz.tmp"
        count = write_jsonl_gz(temporary, records)
        source_expected = expected_memory_source_futures(
            spec, str(source["source_set"])
        )
        if count != source_expected:
            raise RuntimeError(
                f"memory source {source_id} produced {count} records; "
                f"expected {source_expected}"
            )
        temporary.replace(shard)
        _atomic_json(
            shards / f"{source_id}.manifest.json",
            {
                "format": "gre-plastic-memory-shard-v1",
                "source_id": source_id,
                "protocol_digest": protocol_digest,
                "record_count": count,
                "sha256": sha256_file(shard),
            },
        )
        completed_sources.add(source_id)
        completed_records += count
        elapsed_now = prior_elapsed + time.monotonic() - started
        records_per_second = completed_records / max(elapsed_now, 1e-9)
        _atomic_json(
            progress_path,
            {
                "format": "gre-plastic-memory-progress-v1",
                "completed_sources": len(completed_sources),
                "total_sources": len(registry["sources"]),
                "completed_records": completed_records,
                "expected_records": expected,
                "elapsed_seconds": elapsed_now,
                "records_per_second": records_per_second,
                "eta_seconds": (
                    (expected - completed_records) / records_per_second
                    if records_per_second > 0
                    else None
                ),
            },
        )
        if progress is not None:
            progress(
                f"checkpointed memory source {len(completed_sources)}/{len(registry['sources'])} "
                f"({completed_records:,}/{expected:,} futures)"
            )
    if len(completed_sources) != len(registry["sources"]):
        raise RuntimeError("memory source checkpoint set is incomplete")

    def merged_records():
        for source in sorted(registry["sources"], key=lambda value: value["source_id"]):
            yield from read_jsonl_gz(shards / f"{source['source_id']}.jsonl.gz")

    futures_path = destination / "futures.jsonl.gz"
    merged_count = write_jsonl_gz(futures_path.with_name(".futures.jsonl.gz.tmp"), merged_records())
    futures_path.with_name(".futures.jsonl.gz.tmp").replace(futures_path)
    if merged_count != expected or completed_records != expected:
        raise RuntimeError(
            f"memory phase produced {merged_count} records; expected {expected}"
        )
    if progress is not None:
        progress("streaming plastic-memory analysis and causal gates")
    analysis = analyze_memory_records(read_jsonl_gz(futures_path), spec)
    _atomic_json(destination / "analysis.json", analysis)
    elapsed = prior_elapsed + time.monotonic() - started
    manifest = {
        "format": "gre-plastic-memory-runtime-manifest-v1",
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "protocol_digest": protocol_digest,
        "raw_format": PLASTIC_MEMORY_RAW_FORMAT,
        "analysis_format": PLASTIC_MEMORY_ANALYSIS_FORMAT,
        "record_count": merged_count,
        "expected_record_count": expected,
        "source_rulebooks": len(registry["sources"]),
        "workers": workers,
        "elapsed_seconds": elapsed,
        "runtime": runtime_manifest(),
        "source_hashes": source_hashes(),
        "checkpointed_sources": len(completed_sources),
    }
    _atomic_json(destination / "manifest.json", manifest)
    (destination / "report.md").write_text(
        _render_report(analysis, manifest), encoding="utf-8"
    )
    write_checksums(destination)
    if progress is not None:
        progress("sealed plastic-memory phase and checksum manifest")
    verify_memory_run(destination)
    return destination


def load_memory_run(
    directory: Path,
) -> tuple[PlasticMemorySpec, dict[str, Any], dict[str, Any]]:
    registration = read_json(directory / "registration.json")
    spec = PlasticMemorySpec.from_dict(registration["protocol"])
    return spec, read_json(directory / "rulebooks.json"), read_json(
        directory / "analysis.json"
    )


def _equivalence_audit(directory: Path) -> dict[str, Any]:
    values: dict[tuple[Any, ...], dict[str, str]] = {}
    for record in read_jsonl_gz(directory / "futures.jsonl.gz"):
        if record["mark_setting"] != "none" or record["carrier"] not in {
            "self_continuation",
            "state_transplant",
        }:
            continue
        key = (
            record["condition"],
            record["source_id"],
            record["midpoint_index"],
            record["history"],
            record["washout_age"],
            record["challenge"],
            record["future_index"],
        )
        values.setdefault(key, {})[str(record["carrier"])] = str(record["trace_digest"])
    complete = [value for value in values.values() if len(value) == 2]
    matches = sum(
        value["self_continuation"] == value["state_transplant"]
        for value in complete
    )
    return {"pairs": len(complete), "matches": matches, "equal": bool(complete) and matches == len(complete)}


def verify_memory_run(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != PLASTIC_MEMORY_REGISTRATION_FORMAT:
        raise ValueError("plastic-memory registration format mismatch")
    spec = PlasticMemorySpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get("protocol_digest"):
        raise ValueError("plastic-memory protocol digest mismatch")
    registry = read_json(directory / "rulebooks.json")
    expected = expected_memory_futures(spec, registry)
    count = 0
    seen: set[str] = set()
    for record in read_jsonl_gz(directory / "futures.jsonl.gz"):
        count += 1
        future_id = str(record["future_id"])
        if future_id in seen:
            raise ValueError(f"duplicate plastic-memory future: {future_id}")
        seen.add(future_id)
    if count != expected or count != int(manifest["record_count"]):
        raise ValueError(f"plastic-memory record mismatch: {count}, expected {expected}")
    equivalence = _equivalence_audit(directory)
    if any(
        "self_continuation" in condition.carrier_arms
        and "state_transplant" in condition.carrier_arms
        and "none" in condition.mark_settings
        for condition in spec.conditions
    ) and not equivalence["equal"]:
        raise ValueError("self/state transplant pathwise equivalence failed")
    return {
        "verified": True,
        "files": len(checksums),
        "records": count,
        "unique_future_ids": len(seen),
        "protocol_digest": digest,
        "self_transplant_equivalence": equivalence,
    }


def recompute_memory_analysis(directory: Path) -> dict[str, Any]:
    spec, _, archived = load_memory_run(directory)
    recomputed = analyze_memory_records(
        read_jsonl_gz(directory / "futures.jsonl.gz"), spec
    )
    return {
        "matches": canonical_digest(recomputed) == canonical_digest(archived),
        "analysis": recomputed,
    }


def replay_memory_future(directory: Path, future_id: str) -> dict[str, Any]:
    spec, registry, _ = load_memory_run(directory)
    archived = next(
        (
            record
            for record in read_jsonl_gz(directory / "futures.jsonl.gz")
            if record["future_id"] == future_id
        ),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown plastic-memory future: {future_id}")
    source = next(
        value for value in registry["sources"] if value["source_id"] == archived["source_id"]
    )
    original = next(
        condition for condition in spec.conditions if condition.name == archived["condition"]
    )
    narrowed = MemoryCondition(
        original.name,
        original.model,
        original.cue,
        (str(archived["mark_setting"]),),
        (str(archived["carrier"]),),
        (int(archived["washout_age"]),),
        (str(archived["challenge"]),),
        original.futures_per_cell,
    )
    replay_spec = replace(spec, conditions=(narrowed,))
    replayed = next(
        record
        for record in simulate_memory_source(source, replay_spec.to_dict())
        if record["future_id"] == future_id
    )
    fields = (
        "acquired",
        "form_destination",
        "correct_hold_run",
        "wrong_hold_run",
        "generic_hold_run",
        "correct_hold8",
        "returned",
        "trace_digest",
    )
    return {
        "future_id": future_id,
        "matches": all(archived[field] == replayed[field] for field in fields),
        "archived": {field: archived[field] for field in fields},
        "replayed": {field: replayed[field] for field in fields},
    }
