"""Untouched, resumable causal audit for evolved co-option populations."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterator

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .wagner_ph_cooption_analysis import analyze_audit_results
from .wagner_ph_cooption_config import (
    COOPTION_AUDIT_RESULT_FORMAT,
    CooptionSpec,
    QuantizedCarrierGenome,
)
from .wagner_ph_cooption_evolution import (
    deserialize_genotype,
    verify_cooption_evolution,
)
from .wagner_ph_cooption_experiment import history_information, simulate_ecology_condition


AUDIT_REGISTRATION_FORMAT = "gre-wagner-ph-cooption-audit-registration-v1"
AUDIT_MANIFEST_FORMAT = "gre-wagner-ph-cooption-audit-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _audit_population(
    args: tuple[str, dict[str, Any], str, str, str]
) -> dict[str, Any]:
    population_path_text, spec_value, output_text, protocol_digest, seed = args
    population_path = Path(population_path_text)
    archived = read_json(population_path)
    spec = CooptionSpec.from_dict(spec_value)
    output = Path(output_text)
    final_path = output / population_path.name
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"co-option audit registration differs: {final_path}")
    rulebook, genome = deserialize_genotype(archived["selected"])
    task = archived["task"]
    population_index = int(archived["population_index"])
    scope = f"audit.population-{population_index:03d}"
    cells: list[dict[str, Any]] = []
    for persistence in spec.audit_persistence:
        for cue_fraction in spec.cue_fractions:
            conditions = {
                intervention: simulate_ecology_condition(
                    rulebook,
                    task,
                    genome,
                    spec,
                    intervention,
                    persistence,
                    cue_fraction,
                    spec.audit_futures_per_history,
                    spec.lineage_generations,
                    spec.checkpoints,
                    scope,
                    master_seed=seed,
                )
                for intervention in spec.meaning_interventions
            }
            cells.append(
                {
                    "cell_id": f"rho{persistence:.2f}.cue{cue_fraction:.2f}",
                    "persistence": persistence,
                    "cue_fraction": cue_fraction,
                    "conditions": conditions,
                    "history_information": history_information(
                        conditions["natural"]["final_carriers"]
                    ),
                }
            )
    result = {
        "format": COOPTION_AUDIT_RESULT_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": archived["population_id"],
        "population_index": population_index,
        "treatment": archived["treatment"],
        "mutation_architecture": archived["mutation_architecture"],
        "task_digest": task["task_digest"],
        "task": task,
        "selected": archived["selected"],
        "selected_training_score": archived["selected_training_score"],
        "carrier": QuantizedCarrierGenome(**archived["selected"]["carrier"]).to_dict(),
        "neutral_pre_cue_state_is_shared_between_histories": True,
        "audit_streams_are_untouched_by_selection": True,
        "cells": cells,
    }
    result["result_digest"] = canonical_digest(
        {"selected": result["selected"], "cells": cells}
    )
    _atomic_json(final_path, result)
    return result


def run_cooption_audit(
    spec: CooptionSpec,
    evolution: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("co-option audit permits one to four workers")
    evolution = evolution.resolve()
    verify_cooption_evolution(evolution)
    evolution_registration = read_json(evolution / "registration.json")
    seed = str(evolution_registration["master_seed"])
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_cooption_audit(destination)
        return destination
    started = time.monotonic()
    protocol_digest = canonical_digest(
        {
            "spec": spec.to_dict(),
            "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
            "master_seed": seed,
        }
    )
    registration = {
        "format": AUDIT_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": protocol_digest,
        "evolution": str(evolution),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
        "master_seed": seed,
        "audit_streams_were_not_generated_during_selection": True,
        "forced_break_state_is_not_used_for_pre_cue_prediction": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing co-option audit registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    shards = destination / "populations"
    shards.mkdir(exist_ok=True)
    population_files = sorted(
        path
        for path in (evolution / "populations").glob("*.json")
        if not path.name.endswith(".checkpoint.json")
    )
    work = [
        (str(path), spec.to_dict(), str(shards), protocol_digest, seed)
        for path in population_files
    ]
    completed: list[dict[str, Any]] = []
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_audit_population, work)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        futures = [executor.submit(_audit_population, item) for item in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-ph-cooption-audit-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(work),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(work) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"held-out causal audit {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (value["treatment"], value["population_index"]))
    analysis = analyze_audit_results(completed, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": AUDIT_MANIFEST_FORMAT,
            "protocol_digest": protocol_digest,
            "population_count": len(completed),
            "expected_population_count": len(population_files),
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_cooption_audit(destination)
    return destination


def verify_cooption_audit(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != AUDIT_REGISTRATION_FORMAT:
        raise ValueError("co-option audit registration format mismatch")
    if manifest.get("format") != AUDIT_MANIFEST_FORMAT:
        raise ValueError("co-option audit manifest format mismatch")
    spec = CooptionSpec.from_dict(registration["protocol"])
    if sha256_file(Path(registration["evolution"]) / "SHA256SUMS") != registration[
        "evolution_checksum"
    ]:
        raise ValueError("sealed co-option evolution changed after audit")
    digest = canonical_digest(
        {
            "spec": spec.to_dict(),
            "evolution_checksum": registration["evolution_checksum"],
            "master_seed": registration["master_seed"],
        }
    )
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("co-option audit protocol digest mismatch")
    files = sorted((directory / "populations").glob("*.json"))
    expected = int(manifest["expected_population_count"])
    if len(files) != expected or int(manifest["population_count"]) != expected:
        raise ValueError("co-option audit population count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"audit population protocol mismatch: {path.name}")
        if value.get("result_digest") != canonical_digest(
            {"selected": value["selected"], "cells": value["cells"]}
        ):
            raise ValueError(f"audit population result mismatch: {path.name}")
    archived_analysis = dict(analysis)
    archived_digest = archived_analysis.pop("analysis_digest", None)
    if archived_digest != canonical_digest(archived_analysis):
        raise ValueError("co-option audit analysis digest mismatch")
    return {
        "verified": True,
        "populations": expected,
        "checksums": len(checksums),
        "nomination": analysis.get("nomination"),
    }


def replay_cooption_audit_population(
    directory: Path, population_id: str
) -> dict[str, Any]:
    directory = directory.resolve()
    registration = read_json(directory / "registration.json")
    spec = CooptionSpec.from_dict(registration["protocol"])
    archived = read_json(directory / "populations" / f"{population_id}.json")
    source = Path(registration["evolution"]) / "populations" / f"{population_id}.json"
    with tempfile.TemporaryDirectory(prefix="gre-cooption-replay-") as temporary_text:
        replayed = _audit_population(
            (
                str(source),
                spec.to_dict(),
                temporary_text,
                registration["protocol_digest"],
                registration["master_seed"],
            )
        )
    return {
        "population_id": population_id,
        "matches": replayed["result_digest"] == archived["result_digest"],
        "archived_digest": archived["result_digest"],
        "replayed_digest": replayed["result_digest"],
    }
