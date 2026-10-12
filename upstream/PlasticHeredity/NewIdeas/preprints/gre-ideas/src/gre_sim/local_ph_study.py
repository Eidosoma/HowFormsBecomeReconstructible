"""Replayable, source-sharded execution for local-memory PH studies."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

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
from .engines import rulebook_from_dict
from .landscape import int_to_signs
from .lineage_carrier_config import (
    LineageArmSpec,
    LineageSourceSpec,
    LineageStudySpec,
    LineageWriterSpec,
)
from .lineage_carrier_study import build_lineage_registry
from .local_ph_config import (
    LOCAL_PH_MANIFEST_FORMAT,
    LOCAL_PH_RAW_FORMAT,
    LOCAL_PH_REGISTRATION_FORMAT,
    LocalConditionSpec,
    LocalStudySpec,
    expected_local_records,
    intervention_locus,
)
from .local_ph_dynamics import (
    LocalCarrierState,
    blank_local,
    copy_local,
    develop_local_cycle,
    structural_mask,
    write_local,
)
from .mechanism_dynamics import MechanismRulebook
from .plastic_heredity_v2_protocols import carrier_grid
from .plastic_memory_dynamics import (
    AttractorPair,
    clamp_state,
    cue_nodes,
    damage_state,
    develop_memory_cycle,
    summarize_memory_future,
)
from .rng import digest_parts, rng_for


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _pair(value: dict[str, Any]) -> AttractorPair:
    return AttractorPair(
        int(value["left_index"]),
        int(value["right_index"]),
        int(value["left_state"]),
        int(value["right_state"]),
    )


def build_local_registry(spec: LocalStudySpec, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Generate fresh outcome-blind Wagner sources using the established eligibility filter."""

    latch = next(value for value in carrier_grid() if value.name == "latch.threshold-1.retention-16.mu-1")
    lineage = LineageStudySpec(
        spec.cohort_id,
        f"{spec.phase}.eligibility",
        spec.master_seed,
        (LineageSourceSpec("wagner", spec.source_count),),
        (LineageWriterSpec("wagner.selected-natural", "wagner", "natural", spec.cue_fraction, spec.cue_dwell),),
        (replace(latch, engines=("wagner",)),),
        (LineageArmSpec("natural-full", primary=True), LineageArmSpec("zero", bottleneck="zero")),
        (0,),
        ("forced_break",),
        4,
        midpoint_count=1,
        generation_cycles=spec.generation_cycles,
        horizon=spec.horizon,
        strict_run=spec.strict_run,
        stable_run=spec.stable_run,
        expression_flip_probability=spec.expression_flip_probability,
        neutral_damage_fraction=spec.neutral_damage_fraction,
        bootstrap_repetitions=max(64, spec.bootstrap_repetitions),
        exploratory=spec.exploratory,
    )
    registry = build_lineage_registry(lineage, progress)
    registry["format"] = "gre-wagner-local-ph-rulebooks-v1"
    return registry


def _founder_training(
    spec: LocalStudySpec,
    source: dict[str, Any],
    history: str,
    future_index: int,
) -> tuple[tuple[int, ...], bool]:
    metadata = source["models"]["wagner.lineage"]
    pair = _pair(metadata["pair"])
    viewed = MechanismRulebook(rulebook_from_dict(source["source"]), "wagner_sequential")
    base = int(metadata["midpoints"][0])
    target = pair.state(history)
    ordering = np.asarray(metadata["node_order"], dtype=int)
    nodes = cue_nodes(pair, viewed.genes, spec.cue_fraction, ordering)
    state = base
    adults: list[int] = []
    for cycle in range(spec.cue_dwell):
        common = (
            spec.master_seed,
            "local-founder",
            source["source_id"],
            history,
            future_index,
            cycle,
        )
        value = develop_memory_cycle(
            viewed,
            state,
            base,
            np.zeros(viewed.genes, dtype=float),
            1.0,
            spec.expression_flip_probability,
            0.0,
            0.0,
            0.0,
            100,
            rng_for(*common, "carry"),
            rng_for(*common, "mark"),
            rng_for(*common, "dynamics"),
            cue_target=target,
            clamped_nodes=nodes,
            write_mark=False,
        )
        state = int(value.state)
        adults.append(state)
    return tuple(adults), bool(adults and adults[-1] == target)


def _perfect_write(adults: tuple[int, ...], genes: int) -> LocalCarrierState:
    if not adults:
        return blank_local(genes)
    return LocalCarrierState(tuple(float(value) for value in int_to_signs(adults[-1], genes)))


def _condition_founder(
    condition: LocalConditionSpec,
    spec: LocalStudySpec,
    source: dict[str, Any],
    adults: tuple[int, ...],
    opposite_adults: tuple[int, ...] | None = None,
) -> tuple[LocalCarrierState, tuple[int, ...]]:
    viewed = rulebook_from_dict(source["source"])
    if condition.intervention in {"zero", "founder_write_off"}:
        return blank_local(spec.genes), tuple()
    if condition.intervention == "perfect_latch":
        return _perfect_write(adults, spec.genes), tuple(range(spec.genes))
    genome = spec.genome(str(condition.genome))
    random_order = tuple(int(value) for value in source["models"]["wagner.lineage"]["ablation_order"])
    mask = structural_mask(
        viewed,
        genome,
        random_order if condition.intervention == "random_mask" else None,
    )
    writing_adults = (
        opposite_adults
        if condition.intervention == "opposite_history_transplant"
        and opposite_adults is not None
        else adults
    )
    carrier = write_local(blank_local(spec.genes), writing_adults, genome, mask)
    if condition.intervention == "shuffle":
        permutation = tuple(
            int(value)
            for value in source["models"]["wagner.lineage"]["mark_permutation"]
        )
        carrier = LocalCarrierState(tuple(carrier.values[index] for index in permutation))
    return carrier, mask


def _assay(
    spec: LocalStudySpec,
    source: dict[str, Any],
    condition: LocalConditionSpec,
    carrier: LocalCarrierState,
    history: str,
    future_index: int,
    generation: int,
    challenge: str,
) -> tuple[Any, int]:
    metadata = source["models"]["wagner.lineage"]
    pair = _pair(metadata["pair"])
    viewed = MechanismRulebook(rulebook_from_dict(source["source"]), "wagner_sequential")
    base = int(metadata["midpoints"][0])
    state = base
    if challenge == "forced_break":
        state = int(metadata["forced_breaks"][history])
    elif challenge == "neutral_damage":
        state, _ = damage_state(
            state,
            spec.genes,
            spec.neutral_damage_fraction,
            rng_for(
                spec.master_seed,
                "local-damage",
                source["source_id"],
                history,
                future_index,
                generation,
            ),
        )
    elif challenge != "release_only":
        raise ValueError(challenge)
    assay_initial_state = int(state)
    coupling = 0.0
    if condition.intervention == "perfect_latch":
        coupling = 1.0
    elif condition.intervention not in {"zero", "reader_off"}:
        coupling = spec.genome(str(condition.genome)).coupling
    post = []
    for cycle in range(spec.horizon):
        common = (
            spec.master_seed,
            "local-assay",
            source["source_id"],
            history,
            future_index,
            generation,
            challenge,
            cycle,
        )
        value = develop_local_cycle(
            viewed,
            state,
            base,
            carrier,
            coupling,
            spec.expression_flip_probability,
            100,
            rng_for(*common, "carry"),
            rng_for(*common, "read"),
        )
        post.append(value)
        state = int(value.state)
    return (
        summarize_memory_future(
            (), tuple(post), pair, history, np.asarray(carrier.values), spec.strict_run, spec.stable_run
        ),
        assay_initial_state,
    )


def _propagate(
    spec: LocalStudySpec,
    source: dict[str, Any],
    condition: LocalConditionSpec,
    incoming: LocalCarrierState,
    mask: tuple[int, ...],
    history: str,
    future_index: int,
    generation: int,
) -> LocalCarrierState:
    metadata = source["models"]["wagner.lineage"]
    viewed = MechanismRulebook(rulebook_from_dict(source["source"]), "wagner_sequential")
    base = int(metadata["midpoints"][0])
    state = base  # Complete expression reset at every new generation.
    coupling = 0.0
    if condition.intervention == "perfect_latch":
        coupling = 1.0
    elif condition.intervention not in {"zero", "reader_off"}:
        coupling = spec.genome(str(condition.genome)).coupling
    adults: list[int] = []
    for cycle in range(spec.generation_cycles):
        common = (
            spec.master_seed,
            "local-propagation",
            source["source_id"],
            history,
            future_index,
            generation,
            cycle,
        )
        value = develop_local_cycle(
            viewed,
            state,
            base,
            incoming,
            coupling,
            spec.expression_flip_probability,
            100,
            rng_for(*common, "carry"),
            rng_for(*common, "read"),
        )
        state = int(value.state)
        adults.append(state)
    adult_tuple = tuple(adults)
    if condition.intervention == "perfect_latch":
        return _perfect_write(adult_tuple, spec.genes)
    if condition.intervention == "zero":
        return blank_local(spec.genes)
    genome = spec.genome(str(condition.genome))
    carrier = incoming
    renewal_blocked = condition.intervention == "renewal_off" or (
        condition.intervention == "renewal_block_g1_g4" and 0 <= generation <= 3
    ) or (
        condition.intervention == "renewal_block_g9_g12" and 8 <= generation <= 11
    )
    if not renewal_blocked:
        carrier = write_local(carrier, adult_tuple, genome, mask)
    return copy_local(
        carrier,
        genome,
        spec.noise(condition.noise),
        mask,
        rng_for(
            spec.master_seed,
            "local-copy",
            source["source_id"],
            condition.genome,
            condition.noise,
            history,
            future_index,
            generation,
        ),
    )


def _summary(summary: Any) -> dict[str, Any]:
    return {
        "form_destination": summary.form_destination,
        "correct_hold8": summary.correct_hold8,
        "wrong_hold8": summary.wrong_hold8,
        "generic_hold8": summary.generic_hold8,
        "returned": summary.returned,
        "return_cycle": summary.return_cycle,
        "correct_hold_run": summary.correct_hold_run,
        "wrong_hold_run": summary.wrong_hold_run,
        "trace_digest": summary.trace_digest,
    }


def simulate_local_source(source: dict[str, Any], spec_value: dict[str, Any]) -> list[dict[str, Any]]:
    spec = LocalStudySpec.from_dict(spec_value)
    records: list[dict[str, Any]] = []
    maximum = max(spec.checkpoint_generations)
    checkpoints = set(spec.checkpoint_generations)
    for history in ("A", "B"):
        for future_index in range(spec.futures_per_history):
            training, acquired = _founder_training(spec, source, history, future_index)
            opposite_training, _ = _founder_training(
                spec,
                source,
                "B" if history == "A" else "A",
                future_index,
            )
            for condition in spec.conditions:
                incoming, mask = _condition_founder(
                    condition, spec, source, training, opposite_training
                )
                archived = incoming
                lineage_payload: list[Any] = []
                for generation in range(maximum + 1):
                    if generation == 2 and condition.intervention in {"erase_g2", "erase_g2_rescue_g3"}:
                        incoming = blank_local(spec.genes)
                    if generation == 2 and condition.intervention == "reverse_g2":
                        incoming = LocalCarrierState(tuple(-float(value) for value in incoming.values))
                    if generation == 3 and condition.intervention == "erase_g2_rescue_g3":
                        incoming = archived
                    if generation == 6 and condition.intervention in {
                        "erase_g6",
                        "erase_g6_rescue_g7",
                    }:
                        incoming = blank_local(spec.genes)
                    if generation == 7 and condition.intervention == "erase_g6_rescue_g7":
                        incoming = archived
                    locus = intervention_locus(condition.intervention, spec.genes)
                    if generation == 2 and locus is not None:
                        values = list(incoming.values)
                        values[locus] = 0.0
                        incoming = LocalCarrierState(tuple(float(value) for value in values))
                    lineage_payload.append((generation, list(incoming.values)))
                    if generation in checkpoints:
                        lineage_digest = canonical_digest(lineage_payload)
                        for challenge in spec.challenges:
                            result, assay_initial_state = _assay(
                                spec,
                                source,
                                condition,
                                incoming,
                                history,
                                future_index,
                                generation,
                                challenge,
                            )
                            future_id = digest_parts(
                                LOCAL_PH_RAW_FORMAT,
                                spec.cohort_id,
                                source["source_id"],
                                condition.name,
                                history,
                                future_index,
                                generation,
                                challenge,
                            )
                            records.append(
                                {
                                    "future_id": future_id,
                                    "cohort_id": spec.cohort_id,
                                    "phase": spec.phase,
                                    "source_id": source["source_id"],
                                    "source_set": source["source_set"],
                                    "engine": "wagner",
                                    "genes": spec.genes,
                                    "condition": condition.name,
                                    "genome": condition.genome,
                                    "intervention": condition.intervention,
                                    "copy_noise": condition.noise,
                                    "history": history,
                                    "future_index": future_index,
                                    "half": "A" if future_index < spec.futures_per_history // 2 else "B",
                                    "generation": generation,
                                    "challenge": challenge,
                                    "acquired": acquired,
                                    "mask": list(mask),
                                    "capacity": len(mask),
                                    "expression_reset": True,
                                    "carrier_norm": float(np.mean(np.abs(incoming.values))),
                                    "carrier_values": [float(value) for value in incoming.values],
                                    "assay_initial_state": assay_initial_state,
                                    "lineage_digest": lineage_digest,
                                    **_summary(result),
                                }
                            )
                    if generation < maximum:
                        incoming = _propagate(
                            spec,
                            source,
                            condition,
                            incoming,
                            mask,
                            history,
                            future_index,
                            generation,
                        )
    records.sort(
        key=lambda value: (
            value["condition"],
            value["history"],
            value["generation"],
            value["challenge"],
            value["future_index"],
        )
    )
    return records


def expected_local_source_records(spec: LocalStudySpec) -> int:
    return expected_local_records(replace(spec, source_count=1))


def _iter_results(
    sources: list[dict[str, Any]],
    spec: LocalStudySpec,
    workers: int,
    progress: Callable[[str], None] | None,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    if workers == 1:
        for index, source in enumerate(sources, start=1):
            yield source, simulate_local_source(source, spec.to_dict())
            if progress:
                progress(f"simulated local-PH source {index}/{len(sources)}")
        return
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        futures = [executor.submit(simulate_local_source, source, spec.to_dict()) for source in sources]
        for index, (source, future) in enumerate(zip(sources, futures), start=1):
            yield source, future.result()
            if progress:
                progress(f"simulated local-PH source {index}/{len(sources)}")


def run_local_study(
    spec: LocalStudySpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
    registry: dict[str, Any] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 4:
        raise ValueError("local PH permits one to four shared-host workers")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_local_study(destination)
        return destination
    started = time.monotonic()
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": LOCAL_PH_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing local PH registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    registry_path = destination / "rulebooks.json"
    if registry_path.is_file():
        frozen_registry = read_json(registry_path)
    else:
        frozen_registry = registry if registry is not None else build_local_registry(spec, progress)
        if len(frozen_registry["sources"]) != spec.source_count:
            raise ValueError("local PH registry source count differs from protocol")
        _atomic_json(registry_path, frozen_registry)
    shards = destination / "shards"
    shards.mkdir(exist_ok=True)
    source_expected = expected_local_source_records(spec)
    complete: set[str] = set()
    completed_records = 0
    for source in frozen_registry["sources"]:
        source_id = str(source["source_id"])
        shard = shards / f"{source_id}.jsonl.gz"
        manifest = shards / f"{source_id}.manifest.json"
        if shard.is_file() and manifest.is_file():
            value = read_json(manifest)
            if (
                value.get("protocol_digest") == digest
                and value.get("sha256") == sha256_file(shard)
                and int(value.get("record_count", -1)) == source_expected
            ):
                complete.add(source_id)
                completed_records += source_expected
    missing = [value for value in frozen_registry["sources"] if value["source_id"] not in complete]
    for source, records in _iter_results(missing, spec, workers, progress):
        source_id = str(source["source_id"])
        temporary = shards / f".{source_id}.jsonl.gz.tmp"
        count = write_jsonl_gz(temporary, records)
        if count != source_expected:
            raise RuntimeError(f"local PH source produced {count}; expected {source_expected}")
        shard = shards / f"{source_id}.jsonl.gz"
        temporary.replace(shard)
        _atomic_json(
            shards / f"{source_id}.manifest.json",
            {
                "format": "gre-wagner-local-ph-shard-v1",
                "source_id": source_id,
                "protocol_digest": digest,
                "record_count": count,
                "sha256": sha256_file(shard),
            },
        )
        complete.add(source_id)
        completed_records += count
        elapsed = time.monotonic() - started
        rate = completed_records / max(elapsed, 1e-9)
        _atomic_json(
            destination / "progress.json",
            {
                "format": "gre-wagner-local-ph-progress-v1",
                "completed_sources": len(complete),
                "total_sources": spec.source_count,
                "completed_records": completed_records,
                "expected_records": expected_local_records(spec),
                "elapsed_seconds": elapsed,
                "records_per_second": rate,
                "eta_seconds": (expected_local_records(spec) - completed_records) / rate if rate else None,
            },
        )

    def merged() -> Iterator[dict[str, Any]]:
        for source in sorted(frozen_registry["sources"], key=lambda value: value["source_id"]):
            yield from read_jsonl_gz(shards / f"{source['source_id']}.jsonl.gz")

    futures_path = destination / "futures.jsonl.gz"
    temporary = destination / ".futures.jsonl.gz.tmp"
    count = write_jsonl_gz(temporary, merged())
    temporary.replace(futures_path)
    if count != expected_local_records(spec):
        raise RuntimeError(f"local PH study produced {count}; expected {expected_local_records(spec)}")
    if progress:
        progress("analyzing local-memory causal gates")
    from .local_ph_analysis import analyze_local_path, render_local_report

    analysis = analyze_local_path(futures_path, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": LOCAL_PH_MANIFEST_FORMAT,
            "protocol_digest": digest,
            "raw_format": LOCAL_PH_RAW_FORMAT,
            "record_count": count,
            "expected_record_count": expected_local_records(spec),
            "source_rulebooks": spec.source_count,
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    (destination / "report.md").write_text(render_local_report(analysis), encoding="utf-8")
    write_checksums(destination)
    verify_local_study(destination)
    if progress:
        progress("sealed local-memory confirmation")
    return destination


def verify_local_study(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != LOCAL_PH_REGISTRATION_FORMAT:
        raise ValueError("local PH registration format mismatch")
    if manifest.get("format") != LOCAL_PH_MANIFEST_FORMAT:
        raise ValueError("local PH manifest format mismatch")
    spec = LocalStudySpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get("protocol_digest"):
        raise ValueError("local PH protocol digest mismatch")
    expected = expected_local_records(spec)
    if int(manifest["record_count"]) != expected:
        raise ValueError("local PH record count mismatch")
    return {"verified": True, "records": expected, "checksums": len(checksums)}


def replay_local_future(directory: Path, future_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    spec = LocalStudySpec.from_dict(read_json(directory / "registration.json")["protocol"])
    archived = next(
        (value for value in read_jsonl_gz(directory / "futures.jsonl.gz") if value["future_id"] == future_id),
        None,
    )
    if archived is None:
        raise KeyError(f"unknown local PH future: {future_id}")
    source = next(
        value
        for value in read_json(directory / "rulebooks.json")["sources"]
        if value["source_id"] == archived["source_id"]
    )
    condition = next(value for value in spec.conditions if value.name == archived["condition"])
    narrowed = replace(
        spec,
        source_count=1,
        conditions=(condition,),
        checkpoint_generations=tuple(
            value for value in spec.checkpoint_generations if value <= int(archived["generation"])
        ),
        challenges=(str(archived["challenge"]),),
    )
    replayed = next(
        value
        for value in simulate_local_source(source, narrowed.to_dict())
        if value["future_id"] == future_id
    )
    fields = ("form_destination", "correct_hold8", "wrong_hold8", "trace_digest", "lineage_digest")
    return {
        "future_id": future_id,
        "matches": all(archived[field] == replayed[field] for field in fields),
        "archived": {field: archived[field] for field in fields},
        "replayed": {field: replayed[field] for field in fields},
    }
