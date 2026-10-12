"""Checkpointed execution, verification, replay, and reporting for rescue phases."""

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
from .wagner_rescue_analysis import analyze_rescue_records
from .wagner_rescue_campaign import (
    build_rescue_registry,
    expected_rescue_futures,
    expected_rescue_source_futures,
    iter_rescue_source_results,
    simulate_rescue_source,
)
from .wagner_rescue_config import (
    WAGNER_RESCUE_RAW_FORMAT,
    WAGNER_RESCUE_REGISTRATION_FORMAT,
    WagnerRescueSpec,
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
    candidates = [
        cell
        for cell in analysis["cells"].values()
        if cell["role"] == "candidate"
    ]
    candidates.sort(
        key=lambda cell: (
            not bool(cell["replication_passed"]),
            not bool(cell["screen_passed"]),
            -float(
                cell["metrics"]["cue_gain_over_no_cue"]["mean"]
                if cell["metrics"]["cue_gain_over_no_cue"]["mean"] is not None
                else -1e9
            ),
            cell["condition"],
        )
    )
    lines = [
        f"# Wagner induction rescue: {analysis['phase']}",
        "",
        "> Exploratory mechanism search; candidate selection is allowed and is not confirmation.",
        "",
        f"- Futures: {analysis['record_count']:,}",
        f"- Independent Wagner rulebooks: {manifest['source_rulebooks']}",
        f"- Runtime: {manifest['elapsed_seconds'] / 3600:.2f} h",
        f"- Screen-passing candidates: {sum(cell['screen_passed'] for cell in candidates)}",
        f"- Replication-passing candidates: {sum(cell['replication_passed'] for cell in candidates)}",
        "",
        "## Leading cells",
        "",
    ]
    if not candidates:
        lines.append("This phase contains no candidate cells.")
    for cell in candidates[:10]:
        acquisition = min(
            float(cell["histories"][history]["exact_acquisition"]["mean"] or 0.0)
            for history in ("A", "B")
        )
        crossover = cell["metrics"]["correct_minus_wrong"]
        cue_gain = cell["metrics"]["cue_gain_over_no_cue"]
        intervention = cell["intervention"]
        lines.extend(
            (
                f"### `{cell['condition']}`",
                "",
                f"- Screen / replication gate: {'PASS' if cell['screen_passed'] else 'fail'} / {'PASS' if cell['replication_passed'] else 'fail'}",
                f"- Model: `{cell['model']['variant']}`, theta={cell['model']['gamma_variance']:g}",
                f"- Cue: `{intervention['mode']}`, fraction={intervention['fraction']:g}, dwell={intervention['dwell']}, field={intervention['field_strength']:g}",
                f"- Minimum exact acquisition: {acquisition:.4f}",
                f"- Correct-minus-wrong strict-8: {_optional(crossover['mean'], True)} (lower {_optional(crossover['lower'], True)})",
                f"- Gain over no cue: {_optional(cue_gain['mean'], True)} (lower {_optional(cue_gain['lower'], True)})",
                f"- Split-half reliability: {_optional(cell['split_half_reliability'])}",
                f"- Fraction of injection ceiling: {_optional(cell['injection_ceiling_fraction'])}",
                "",
            )
        )
    lines.extend(
        (
            "## Interpretation boundary",
            "",
            "A passing cell shows that a temporary intervention can write and retain "
            "history-specific state in this Wagner regime. It does not by itself show "
            "state transplantation, descendant heredity, slow-mark memory, evolution, "
            "or replication in GARD.",
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


def run_rescue_study(
    spec: WagnerRescueSpec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Run or resume one immutable source-sharded rescue phase."""

    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("Wagner rescue study requires 1-8 workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_rescue_run(destination)
        if progress is not None:
            progress("rescue phase already sealed; verified without mutation")
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
        "format": WAGNER_RESCUE_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if canonical_digest(read_json(registration_path)) != canonical_digest(
            registration
        ):
            raise ValueError("existing rescue phase uses a different registration")
    else:
        _atomic_json(registration_path, registration)

    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        registry = read_json(registry_path)
    else:
        registry = build_rescue_registry(spec, progress)
        _atomic_json(registry_path, registry)
    expected = expected_rescue_futures(spec)
    source_expected = expected_rescue_source_futures(spec)
    shards = destination / "shards"
    shards.mkdir(exist_ok=True)
    completed_sources: set[str] = set()
    completed_records = 0
    for source in registry["sources"]:
        source_id = str(source["source_id"])
        shard = shards / f"{source_id}.jsonl.gz"
        valid, count = _valid_shard(
            shard,
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
            f"rescue phase resume: {len(completed_sources)}/{spec.source_count} "
            f"sources, {completed_records:,}/{expected:,} futures sealed"
        )
    pending_registry = {**registry, "sources": missing}
    for source, records in iter_rescue_source_results(
        pending_registry, spec, workers, progress
    ):
        source_id = str(source["source_id"])
        shard = shards / f"{source_id}.jsonl.gz"
        temporary = shards / f".{source_id}.jsonl.gz.tmp"
        count = write_jsonl_gz(temporary, records)
        if count != source_expected:
            raise RuntimeError(
                f"rescue source {source_id} produced {count}; expected {source_expected}"
            )
        temporary.replace(shard)
        _atomic_json(
            shards / f"{source_id}.manifest.json",
            {
                "format": "gre-wagner-rescue-shard-v1",
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
                "format": "gre-wagner-rescue-progress-v1",
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
                f"checkpointed rescue source {len(completed_sources)}/{spec.source_count} "
                f"({completed_records:,}/{expected:,} futures)"
            )
    if len(completed_sources) != spec.source_count:
        raise RuntimeError("rescue source checkpoint set is incomplete")

    def merged_records():
        for source in sorted(registry["sources"], key=lambda value: value["source_id"]):
            yield from read_jsonl_gz(shards / f"{source['source_id']}.jsonl.gz")

    futures_path = destination / "futures.jsonl.gz"
    temporary_futures = destination / ".futures.jsonl.gz.tmp"
    merged_count = write_jsonl_gz(temporary_futures, merged_records())
    temporary_futures.replace(futures_path)
    if merged_count != expected or completed_records != expected:
        raise RuntimeError(
            f"rescue phase produced {merged_count} records; expected {expected}"
        )
    if progress is not None:
        progress("streaming Wagner rescue analysis and gates")
    analysis = analyze_rescue_records(read_jsonl_gz(futures_path), spec)
    _atomic_json(destination / "analysis.json", analysis)
    elapsed = prior_elapsed + time.monotonic() - started
    manifest = {
        "format": "gre-wagner-rescue-runtime-manifest-v1",
        "cohort_id": spec.cohort_id,
        "phase": spec.phase,
        "protocol_digest": protocol_digest,
        "raw_format": WAGNER_RESCUE_RAW_FORMAT,
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
    verify_rescue_run(destination)
    if progress is not None:
        progress("sealed Wagner rescue phase and checksum manifest")
    return destination


def load_rescue_run(
    directory: Path,
) -> tuple[WagnerRescueSpec, dict[str, Any], dict[str, Any]]:
    registration = read_json(directory / "registration.json")
    spec = WagnerRescueSpec.from_dict(registration["protocol"])
    return spec, read_json(directory / "rulebooks.json"), read_json(
        directory / "analysis.json"
    )


def verify_rescue_run(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != WAGNER_RESCUE_REGISTRATION_FORMAT:
        raise ValueError("Wagner rescue registration format mismatch")
    spec = WagnerRescueSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("Wagner rescue protocol digest mismatch")
    expected = expected_rescue_futures(spec)
    count = 0
    seen: set[str] = set()
    for record in read_jsonl_gz(directory / "futures.jsonl.gz"):
        count += 1
        future_id = str(record["future_id"])
        if future_id in seen:
            raise ValueError(f"duplicate Wagner rescue future: {future_id}")
        seen.add(future_id)
    if count != expected or count != int(manifest["record_count"]):
        raise ValueError(f"Wagner rescue record mismatch: {count}, expected {expected}")
    return {
        "verified": True,
        "files": len(checksums),
        "records": count,
        "unique_future_ids": len(seen),
        "protocol_digest": digest,
    }


def recompute_rescue_analysis(directory: Path) -> dict[str, Any]:
    spec, _, archived = load_rescue_run(directory)
    recomputed = analyze_rescue_records(
        read_jsonl_gz(directory / "futures.jsonl.gz"), spec
    )
    return {
        "matches": canonical_digest(recomputed) == canonical_digest(archived),
        "analysis": recomputed,
    }


def replay_rescue_future(directory: Path, future_id: str) -> dict[str, Any]:
    spec, registry, _ = load_rescue_run(directory)
    archived = next(
        (
            record
            for record in read_jsonl_gz(directory / "futures.jsonl.gz")
            if record["future_id"] == future_id
        ),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown Wagner rescue future: {future_id}")
    source = next(
        item
        for item in registry["sources"]
        if item["source_id"] == archived["source_id"]
    )
    condition = spec.condition(str(archived["condition"]))
    replay_spec = replace(spec, conditions=(condition,))
    replayed = next(
        record
        for record in simulate_rescue_source(source, replay_spec.to_dict())
        if record["future_id"] == future_id
    )
    fields = (
        "trained_state",
        "acquired",
        "basin_acquired",
        "training_status",
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
