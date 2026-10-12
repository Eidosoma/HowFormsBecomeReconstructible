"""Held-out causal audit for the eight robustness-ratchet arms."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
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
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_cooption_analysis import population_effects
from .wagner_ph_cooption_config import CooptionSpec
from .wagner_ph_cooption_evolution import deserialize_genotype
from .wagner_ph_cooption_experiment import history_information, simulate_ecology_condition
from .wagner_ph_robustness_config import (
    ROBUSTNESS_ARMS,
    ROBUSTNESS_AUDIT_FORMAT,
    RobustnessSpec,
)
from .wagner_ph_robustness_evolution import verify_robustness_evolution


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _audit_population(
    args: tuple[str, dict[str, Any], dict[str, Any], str, str]
) -> dict[str, Any]:
    population_text, spec_value, kernel_value, output_text, protocol_digest = args
    archived = read_json(Path(population_text))
    spec = RobustnessSpec.from_dict(spec_value)
    kernel = CooptionSpec.from_dict(kernel_value)
    output = Path(output_text)
    final_path = output / Path(population_text).name
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"robustness audit registration differs: {final_path}")
    rulebook, carrier = deserialize_genotype(archived["selected"])
    task_index = int(archived["population_index"])
    scope = f"robustness-audit.task-{task_index:03d}"
    cells: list[dict[str, Any]] = []
    for persistence in spec.audit_persistence:
        for cue_fraction in spec.audit_cue_fractions:
            conditions = {
                intervention: simulate_ecology_condition(
                    rulebook,
                    archived["task"],
                    carrier,
                    kernel,
                    intervention,
                    persistence,
                    cue_fraction,
                    spec.audit_futures_per_history,
                    kernel.lineage_generations,
                    kernel.checkpoints,
                    scope,
                    master_seed=spec.audit_seed,
                )
                for intervention in kernel.meaning_interventions
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
        "format": ROBUSTNESS_AUDIT_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": archived["population_id"],
        "population_index": task_index,
        "arm": archived["arm"],
        "arm_settings": archived["arm_settings"],
        "task_digest": archived["task"]["task_digest"],
        "task": archived["task"],
        "selected": archived["selected"],
        "selected_training_score": archived["selected_training_score"],
        "selected_selection_score": archived["selected_selection_score"],
        "neutral_pre_cue_state_is_shared_between_histories": True,
        "audit_streams_are_held_out_from_selection": True,
        "common_random_streams_are_shared_across_arms": True,
        "cells": cells,
    }
    result["result_digest"] = canonical_digest(
        {"selected": result["selected"], "cells": cells}
    )
    _atomic_json(final_path, result)
    return result


def _preliminary_analysis(results: list[dict[str, Any]], spec: RobustnessSpec) -> dict[str, Any]:
    kernel = spec.kernel()
    summaries: dict[str, Any] = {}
    for arm in spec.arms:
        selected = [value for value in results if value["arm"] == arm]
        effects = {
            str(value["population_index"]): population_effects(value, kernel)
            for value in selected
        }
        fields = tuple(next(iter(effects.values()))) if effects else ()
        summaries[arm] = {
            "populations": len(selected),
            "task_effects": effects,
            "intervals": {
                field: _interval(
                    (row[field] for row in effects.values()),
                    spec.audit_seed,
                    f"robustness-audit.{arm}.{field}",
                    spec.bootstrap_repetitions,
                    spec.interval_level,
                )
                for field in fields
            },
        }
    result = {
        "format": f"{ROBUSTNESS_AUDIT_FORMAT}-analysis",
        "inferential_unit": "paired sealed founder task",
        "summaries": summaries,
        "selection_data_are_not_used_as_ph_evidence": True,
    }
    result["analysis_digest"] = canonical_digest(result)
    return result


def run_robustness_audit(
    spec: RobustnessSpec,
    evolution: Path,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if not 1 <= workers <= spec.maximum_workers:
        raise ValueError("robustness audit permits one to four CPU workers")
    evolution = evolution.resolve()
    verify_robustness_evolution(evolution)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_robustness_audit(destination)
        return destination
    started = time.monotonic()
    kernel = spec.kernel()
    payload = {
        "spec": spec.to_dict(),
        "kernel": kernel.to_dict(),
        "evolution_checksum": sha256_file(evolution / "SHA256SUMS"),
    }
    protocol_digest = canonical_digest(payload)
    registration = {
        "format": f"{ROBUSTNESS_AUDIT_FORMAT}-registration",
        "protocol_digest": protocol_digest,
        **payload,
        "evolution": str(evolution),
        "audit_seed": spec.audit_seed,
        "audit_streams_were_not_generated_during_selection": True,
        "pre_cue_primary_and_25_percent_cue_sensitivity_are_both_archived": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and read_json(registration_path) != registration:
        raise ValueError("existing robustness-audit registration differs")
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
        (str(path), spec.to_dict(), kernel.to_dict(), str(shards), protocol_digest)
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
        futures = [executor.submit(_audit_population, value) for value in work]
        iterator = (future.result() for future in concurrent.futures.as_completed(futures))
    try:
        for index, result in enumerate(iterator, start=1):
            completed.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": f"{ROBUSTNESS_AUDIT_FORMAT}-progress",
                    "completed_populations": index,
                    "total_populations": len(work),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(work) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"robustness causal audit {index}/{len(work)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    completed.sort(key=lambda value: (ROBUSTNESS_ARMS.index(value["arm"]), value["population_index"]))
    analysis = _preliminary_analysis(completed, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(
        destination / "manifest.json",
        {
            "format": f"{ROBUSTNESS_AUDIT_FORMAT}-manifest",
            "protocol_digest": protocol_digest,
            "population_count": len(completed),
            "expected_population_count": spec.population_count,
            "workers": workers,
            "elapsed_seconds": time.monotonic() - started,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_robustness_audit(destination)
    return destination


def verify_robustness_audit(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    analysis = read_json(directory / "analysis.json")
    if registration.get("format") != f"{ROBUSTNESS_AUDIT_FORMAT}-registration":
        raise ValueError("robustness-audit registration format mismatch")
    spec = RobustnessSpec.from_dict(registration["spec"])
    evolution = Path(registration["evolution"])
    if sha256_file(evolution / "SHA256SUMS") != registration["evolution_checksum"]:
        raise ValueError("sealed robustness evolution changed after audit")
    payload = {
        "spec": spec.to_dict(),
        "kernel": registration["kernel"],
        "evolution_checksum": registration["evolution_checksum"],
    }
    digest = canonical_digest(payload)
    if digest != registration["protocol_digest"] or digest != manifest["protocol_digest"]:
        raise ValueError("robustness-audit protocol digest mismatch")
    files = sorted((directory / "populations").glob("*.json"))
    if len(files) != spec.population_count or int(manifest["population_count"]) != spec.population_count:
        raise ValueError("robustness-audit population count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"robustness audit shard protocol mismatch: {path.name}")
        if value.get("result_digest") != canonical_digest(
            {"selected": value["selected"], "cells": value["cells"]}
        ):
            raise ValueError(f"robustness audit shard result mismatch: {path.name}")
    archived = dict(analysis)
    digest_value = archived.pop("analysis_digest", None)
    if digest_value != canonical_digest(archived):
        raise ValueError("robustness-audit analysis digest mismatch")
    return {"verified": True, "populations": len(files), "checksums": len(checksums)}
