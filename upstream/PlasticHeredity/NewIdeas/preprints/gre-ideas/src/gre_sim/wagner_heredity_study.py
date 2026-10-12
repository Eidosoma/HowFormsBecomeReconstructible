"""Checkpointed execution, verification, replay, and reports for heredity phases."""

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
from .study import source_hashes
from .wagner_heredity_analysis import analyze_heredity_path
from .wagner_heredity_campaign import (
    build_heredity_registry,
    expected_heredity_futures,
    expected_heredity_source_futures,
    iter_heredity_source_results,
    simulate_heredity_source,
)
from .wagner_heredity_config import (
    WAGNER_HEREDITY_RAW_FORMAT,
    WAGNER_HEREDITY_REGISTRATION_FORMAT,
    WagnerHereditySpec,
)


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _optional(value: Any, signed: bool = False) -> str:
    if value is None:
        return "not estimable"
    return f"{float(value):+.4f}" if signed else f"{float(value):.4f}"


def _render_report(analysis: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [
        f"# Wagner plastic heredity: {analysis['phase']}",
        "",
        (
            "> Exploratory source cohort."
            if analysis["exploratory"]
            else "> Untouched confirmatory source cohort."
        ),
        "",
        f"- Futures: {analysis['record_count']:,}",
        f"- Independent Wagner rulebooks: {manifest['source_rulebooks']}",
        f"- Runtime: {manifest['elapsed_seconds'] / 3600:.2f} h",
        "",
        "## State-transfer tiers",
        "",
    ]
    gates = sorted(
        analysis["state_transfer_gates"].values(),
        key=lambda gate: (not gate["primary"], gate["tier"], gate["writer"]),
    )
    for gate in gates:
        transfer = gate["primary_transfer"]
        metrics = transfer["metrics"]
        lines.extend(
            (
                f"### `{gate['writer']}` — {'PASS' if gate['passed'] else 'fail'}",
                "",
                f"- Tier: `{gate['tier']}`; primary: {gate['primary']}",
                f"- Acquisition A/B: {_optional(analysis['acquisition'][gate['writer']]['A']['mean'])} / {_optional(analysis['acquisition'][gate['writer']]['B']['mean'])}",
                f"- State-minus-reset: {_optional(metrics['risk_difference']['mean'], True)} (simultaneous lower {_optional(metrics['risk_difference']['lower'], True)})",
                f"- History crossover: {_optional(metrics['crossover']['mean'], True)} (lower {_optional(metrics['crossover']['lower'], True)})",
                f"- Cross-fitted log-loss gain: {_optional(metrics['log_loss_gain']['mean'], True)} (lower {_optional(metrics['log_loss_gain']['lower'], True)})",
                f"- Injection-ceiling fraction: {_optional(gate['ceiling_fraction'])}",
                f"- Generation-one risk / crossover lower: {_optional(gate['generation_one']['risk_difference']['lower'], True)} / {_optional(gate['generation_one']['crossover']['lower'], True)}",
                "- Failed criteria: "
                + (
                    ", ".join(
                        f"`{name}`"
                        for name, passed in gate["criteria"].items()
                        if not passed
                    )
                    or "none"
                ),
                "",
            )
        )
    mark_rows = [
        (writer, mark, gate)
        for writer, values in analysis["mark_transfer_gates"].items()
        for mark, gate in values.items()
    ]
    if mark_rows:
        lines.extend(("## Slow-mark tiers", ""))
        for writer, mark, gate in mark_rows:
            lines.extend(
                (
                    f"- `{writer}` / `{mark}`: {'PASS' if gate['passed'] else 'fail'}",
                    "",
                )
            )
    lines.extend(
        (
            "## Interpretation boundary",
            "",
            "A hard-writer pass supports minimal transmission of an engineered "
            "expression state. Soft-writer, noisy, slow-mark, evolutionary, and GARD "
            "results are progressively stronger and remain separately labeled. "
            "Destination-matched equivalence means ordinary attractor state is "
            "sufficient; it is not evidence for a hidden carrier.",
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


def run_heredity_study(
    spec: WagnerHereditySpec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or resume one immutable source-sharded heredity phase."""

    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("Wagner heredity study requires 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_heredity_run(destination)
        if progress is not None:
            progress("heredity phase already sealed; verified without mutation")
        return destination
    started = time.monotonic()
    progress_path = destination / "progress.json"
    prior_elapsed = 0.0
    if progress_path.is_file():
        try:
            prior_elapsed = max(
                0.0, float(read_json(progress_path).get("elapsed_seconds", 0.0))
            )
        except (OSError, ValueError, TypeError):
            prior_elapsed = 0.0
    protocol_digest = canonical_digest(spec.to_dict())
    registration = {
        "format": WAGNER_HEREDITY_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "parent_candidate_digest": spec.parent_candidate_digest,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if canonical_digest(read_json(registration_path)) != canonical_digest(
            registration
        ):
            raise ValueError("existing heredity phase uses a different registration")
    else:
        _atomic_json(registration_path, registration)

    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        registry = read_json(registry_path)
    else:
        registry = build_heredity_registry(spec, progress)
        _atomic_json(registry_path, registry)
    if registry.get("parent_candidate_digest") != spec.parent_candidate_digest:
        raise ValueError("heredity registry parent digest mismatch")
    expected = expected_heredity_futures(spec)
    source_expected = expected_heredity_source_futures(spec)
    shards = destination / "shards"
    shards.mkdir(exist_ok=True)
    completed_sources: set[str] = set()
    completed_records = 0
    for source in registry["sources"]:
        source_id = str(source["source_id"])
        valid, count = _valid_shard(
            shards / f"{source_id}.jsonl.gz",
            shards / f"{source_id}.manifest.json",
            protocol_digest,
            source_id,
            source_expected,
        )
        if valid:
            completed_sources.add(source_id)
            completed_records += count
    missing = [
        source
        for source in registry["sources"]
        if source["source_id"] not in completed_sources
    ]
    if progress is not None:
        progress(
            f"heredity phase resume: {len(completed_sources)}/{spec.source_count} "
            f"sources, {completed_records:,}/{expected:,} futures sealed"
        )
    pending_registry = {**registry, "sources": missing}
    for source, records in iter_heredity_source_results(
        pending_registry, spec, workers, progress
    ):
        source_id = str(source["source_id"])
        shard = shards / f"{source_id}.jsonl.gz"
        temporary = shards / f".{source_id}.jsonl.gz.tmp"
        count = write_jsonl_gz(temporary, records)
        if count != source_expected:
            raise RuntimeError(
                f"heredity source {source_id} produced {count}; expected {source_expected}"
            )
        temporary.replace(shard)
        _atomic_json(
            shards / f"{source_id}.manifest.json",
            {
                "format": "gre-wagner-heredity-shard-v1",
                "source_id": source_id,
                "protocol_digest": protocol_digest,
                "record_count": count,
                "sha256": sha256_file(shard),
            },
        )
        completed_sources.add(source_id)
        completed_records += count
        elapsed = prior_elapsed + time.monotonic() - started
        rate = completed_records / max(elapsed, 1e-9)
        _atomic_json(
            progress_path,
            {
                "format": "gre-wagner-heredity-progress-v1",
                "completed_sources": len(completed_sources),
                "total_sources": spec.source_count,
                "completed_records": completed_records,
                "expected_records": expected,
                "elapsed_seconds": elapsed,
                "records_per_second": rate,
                "eta_seconds": (
                    (expected - completed_records) / rate if rate > 0.0 else None
                ),
            },
        )
        if progress is not None:
            progress(
                f"checkpointed heredity source {len(completed_sources)}/{spec.source_count} "
                f"({completed_records:,}/{expected:,} futures)"
            )
    if len(completed_sources) != spec.source_count:
        raise RuntimeError("heredity source checkpoint set is incomplete")

    def merged_records():
        for source in sorted(registry["sources"], key=lambda value: value["source_id"]):
            yield from read_jsonl_gz(shards / f"{source['source_id']}.jsonl.gz")

    futures_path = destination / "futures.jsonl.gz"
    temporary_futures = destination / ".futures.jsonl.gz.tmp"
    merged_count = write_jsonl_gz(temporary_futures, merged_records())
    temporary_futures.replace(futures_path)
    if merged_count != expected or completed_records != expected:
        raise RuntimeError(
            f"heredity phase produced {merged_count} records; expected {expected}"
        )
    if progress is not None:
        progress("streaming Wagner heredity analysis and tiered gates")
    analysis = analyze_heredity_path(futures_path, spec)
    _atomic_json(destination / "analysis.json", analysis)
    elapsed = prior_elapsed + time.monotonic() - started
    manifest = {
        "format": "gre-wagner-heredity-runtime-manifest-v1",
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "protocol_digest": protocol_digest,
        "parent_candidate_digest": spec.parent_candidate_digest,
        "raw_format": WAGNER_HEREDITY_RAW_FORMAT,
        "record_count": merged_count,
        "expected_record_count": expected,
        "source_rulebooks": spec.source_count,
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
    verify_heredity_run(destination)
    if progress is not None:
        progress("sealed Wagner heredity phase and checksum manifest")
    return destination


def load_heredity_run(
    directory: Path,
) -> tuple[WagnerHereditySpec, dict[str, Any], dict[str, Any]]:
    registration = read_json(directory / "registration.json")
    spec = WagnerHereditySpec.from_dict(registration["protocol"])
    return spec, read_json(directory / "rulebooks.json"), read_json(
        directory / "analysis.json"
    )


def verify_heredity_run(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != WAGNER_HEREDITY_REGISTRATION_FORMAT:
        raise ValueError("Wagner heredity registration format mismatch")
    spec = WagnerHereditySpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("Wagner heredity protocol digest mismatch")
    if manifest.get("parent_candidate_digest") != spec.parent_candidate_digest:
        raise ValueError("Wagner heredity parent digest mismatch")
    expected = expected_heredity_futures(spec)
    count = 0
    seen: set[str] = set()
    for record in read_jsonl_gz(directory / "futures.jsonl.gz"):
        count += 1
        future_id = str(record["future_id"])
        if future_id in seen:
            raise ValueError(f"duplicate Wagner heredity future: {future_id}")
        seen.add(future_id)
    if count != expected or count != int(manifest["record_count"]):
        raise ValueError(f"Wagner heredity record mismatch: {count}, expected {expected}")
    return {
        "verified": True,
        "files": len(checksums),
        "records": count,
        "unique_future_ids": len(seen),
        "protocol_digest": digest,
    }


def recompute_heredity_analysis(directory: Path) -> dict[str, Any]:
    spec, _, archived = load_heredity_run(directory)
    recomputed = analyze_heredity_path(directory / "futures.jsonl.gz", spec)
    return {
        "matches": canonical_digest(recomputed) == canonical_digest(archived),
        "analysis": recomputed,
    }


def replay_heredity_future(directory: Path, future_id: str) -> dict[str, Any]:
    spec, registry, _ = load_heredity_run(directory)
    archived = next(
        (
            record
            for record in read_jsonl_gz(directory / "futures.jsonl.gz")
            if record["future_id"] == future_id
        ),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown Wagner heredity future: {future_id}")
    source = next(
        item for item in registry["sources"] if item["source_id"] == archived["source_id"]
    )
    condition = spec.condition(str(archived["condition"]))
    replay_spec = replace(spec, conditions=(condition,))
    replayed = next(
        record
        for record in simulate_heredity_source(source, replay_spec.to_dict())
        if record["future_id"] == future_id
    )
    fields = (
        "trained_state",
        "trained_mark_norm",
        "acquired",
        "form_destination",
        "correct_hold8",
        "wrong_hold8",
        "returned",
        "trace_digest",
    )
    return {
        "future_id": future_id,
        "matches": all(archived[field] == replayed[field] for field in fields),
        "archived": {field: archived[field] for field in fields},
        "replayed": {field: replayed[field] for field in fields},
    }
