"""Common-endpoint rescore of the completed v1 Wagner evolution populations."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    sha256_file,
    verify_checksums,
    write_checksums,
    write_json,
)
from .engines import rulebook_from_dict
from .plastic_heredity_v2_config import EvolutionV2Spec
from .plastic_memory_dynamics import AttractorPair
from .rng import rng_for
from .wagner import WagnerRulebook
from .wagner_heredity_evolution import (
    HeredityEvolutionCell,
    HeredityEvolutionSpec,
    _score_rulebook,
)


RESCORE_REGISTRATION_FORMAT = "gre-plastic-heredity-v2-common-rescore-registration-v1"
RESCORE_RESULT_FORMAT = "gre-plastic-heredity-v2-common-rescore-population-v1"
RESCORE_ANALYSIS_FORMAT = "gre-plastic-heredity-v2-common-rescore-analysis-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _rescore_task(
    args: tuple[str, dict[str, Any], dict[str, Any], str, str]
) -> dict[str, Any]:
    population_path_text, parent_spec_value, v2_spec_value, protocol_digest, output_text = args
    population_path = Path(population_path_text)
    output = Path(output_text)
    archived = read_json(population_path)
    population_id = str(archived["population_id"])
    result_path = output / f"{population_id}.json"
    if result_path.is_file():
        prior = read_json(result_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"rescore shard registration differs: {result_path}")
    parent_spec = HeredityEvolutionSpec.from_dict(parent_spec_value)
    v2_spec = EvolutionV2Spec.from_dict(v2_spec_value)
    assay_spec = replace(
        parent_spec,
        master_seed=v2_spec.master_seed,
        heldout_replicates=v2_spec.heldout_replicates,
        descendant_age=v2_spec.descendant_age,
        expression_flip_probability=v2_spec.expression_flip_probability,
        neutral_damage_fraction=v2_spec.neutral_damage_fraction,
        post_horizon=v2_spec.post_horizon,
        hold_run=v2_spec.hold_run,
        exploratory=True,
    )
    archived_cell = HeredityEvolutionCell.from_dict(archived["cell"])
    common_cell = replace(archived_cell, treatment="memory_selection")
    founder = rulebook_from_dict(archived["founder"])
    selected = rulebook_from_dict(archived["selected"])
    if not isinstance(founder, WagnerRulebook) or not isinstance(selected, WagnerRulebook):
        raise TypeError("v2 common rescore requires Wagner population genotypes")
    pair = AttractorPair(**archived["pair"])
    midpoint = int(archived["midpoint"])
    nodes = tuple(int(value) for value in archived["nodes"])
    # The same semantic coordinate is intentional: founder and selected receive
    # paired stochastic futures under the one common descendant-memory endpoint.
    coordinate = ("plastic-heredity-v2-common-assay",)
    founder_score = _score_rulebook(
        founder,
        pair,
        midpoint,
        nodes,
        common_cell,
        assay_spec,
        population_id,
        coordinate,
        v2_spec.heldout_replicates,
    )
    selected_score = _score_rulebook(
        selected,
        pair,
        midpoint,
        nodes,
        common_cell,
        assay_spec,
        population_id,
        coordinate,
        v2_spec.heldout_replicates,
    )
    result = {
        "format": RESCORE_RESULT_FORMAT,
        "protocol_digest": protocol_digest,
        "population_id": population_id,
        "source_file": population_path.name,
        "selection_treatment": archived_cell.treatment,
        "selection_endpoint": v2_spec.selection_endpoint(archived_cell.treatment),
        "common_assay_endpoint": v2_spec.common_assay_endpoint,
        "founder_common_score": founder_score,
        "selected_common_score": selected_score,
        "common_score_change": selected_score - founder_score,
        "paired_random_coordinates": True,
    }
    _atomic_json(result_path, result)
    return result


def _estimate(values: list[float], spec: EvolutionV2Spec, label: str) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if not array.size:
        return {"mean": None, "interval": [None, None], "lower": None, "populations": 0}
    rng = rng_for(spec.master_seed, "v2-common-rescore-bootstrap", label)
    repetitions = 4096
    indices = rng.integers(0, array.size, size=(repetitions, array.size))
    draws = np.mean(array[indices], axis=1)
    return {
        "mean": float(np.mean(array)),
        "interval": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "lower": float(np.quantile(draws, 0.05 / 4.0)),
        "populations": int(array.size),
        "positive_changes": int(np.sum(array > 0.0)),
    }


def _contrast(
    left: list[float], right: list[float], spec: EvolutionV2Spec, label: str
) -> dict[str, Any]:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if not a.size or not b.size:
        return {"mean": None, "interval": [None, None], "lower": None}
    rng = rng_for(spec.master_seed, "v2-common-rescore-contrast", label)
    repetitions = 4096
    ai = rng.integers(0, a.size, size=(repetitions, a.size))
    bi = rng.integers(0, b.size, size=(repetitions, b.size))
    draws = np.mean(a[ai], axis=1) - np.mean(b[bi], axis=1)
    return {
        "mean": float(np.mean(a) - np.mean(b)),
        "interval": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "lower": float(np.quantile(draws, 0.05 / 4.0)),
    }


def analyze_common_rescore(
    results: list[dict[str, Any]], spec: EvolutionV2Spec
) -> dict[str, Any]:
    grouped: dict[str, list[float]] = {
        treatment: []
        for treatment in ("memory_selection", "cue_performance_sham", "neutral")
    }
    for result in results:
        grouped[str(result["selection_treatment"])].append(
            float(result["common_score_change"])
        )
    cells = {
        treatment: _estimate(values, spec, f"cell.{treatment}")
        for treatment, values in grouped.items()
    }
    contrasts = {
        control: _contrast(
            grouped["memory_selection"],
            grouped[control],
            spec,
            f"memory-minus-{control}",
        )
        for control in ("cue_performance_sham", "neutral")
    }
    return {
        "format": RESCORE_ANALYSIS_FORMAT,
        "cohort_id": spec.cohort_id,
        "exploratory": True,
        "post_hoc": True,
        "can_confirm_evolution": False,
        "common_assay_endpoint": spec.common_assay_endpoint,
        "record_count": len(results),
        "cells": cells,
        "contrasts": contrasts,
        "separation_audit": {
            "selection_endpoints": {
                treatment: spec.selection_endpoint(treatment)
                for treatment in grouped
            },
            "heldout_endpoint_for_every_treatment": spec.common_assay_endpoint,
            "all_populations_rescored": all(len(values) == 64 for values in grouped.values()),
            "paired_founder_selected_random_coordinates": all(
                bool(result["paired_random_coordinates"]) for result in results
            ),
        },
    }


def run_common_endpoint_rescore(
    spec: EvolutionV2Spec,
    destination: Path,
    workers: int = 1,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Rescore every sealed v1 population without mutating the parent run."""

    spec.validate()
    if workers < 1 or workers > 8:
        raise ValueError("v2 common rescore requires 1-8 workers")
    parent = spec.parent_path.resolve()
    verify_checksums(parent)
    parent_registration = read_json(parent / "registration.json")
    parent_spec = HeredityEvolutionSpec.from_dict(parent_registration["protocol"])
    population_files = sorted((parent / "populations").glob("*.json"))
    population_files = [path for path in population_files if ".checkpoint." not in path.name]
    expected = len(parent_spec.cells) * parent_spec.populations_per_cell
    if len(population_files) != expected:
        raise ValueError(
            f"sealed parent exposes {len(population_files)} final populations; expected {expected}"
        )
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_common_endpoint_rescore(destination)
        return destination
    results_dir = destination / "populations"
    results_dir.mkdir(exist_ok=True)
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": RESCORE_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
        "parent_registration_digest": canonical_digest(parent_registration),
        "parent_checksum_digest": sha256_file(parent / "SHA256SUMS"),
        "parent_read_only": True,
        "post_hoc": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file():
        if read_json(registration_path) != registration:
            raise ValueError("existing v2 common-rescore registration differs")
    else:
        _atomic_json(registration_path, registration)
    tasks = [
        (
            str(path),
            parent_spec.to_dict(),
            spec.to_dict(),
            digest,
            str(results_dir),
        )
        for path in population_files
    ]
    started = time.monotonic()
    prior_elapsed = 0.0
    progress_path = destination / "progress.json"
    if progress_path.is_file():
        try:
            prior_elapsed = float(read_json(progress_path).get("elapsed_seconds", 0.0))
        except (OSError, TypeError, ValueError):
            prior_elapsed = 0.0
    results: list[dict[str, Any]] = []
    if workers == 1:
        iterator = map(_rescore_task, tasks)
        executor = None
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        iterator = executor.map(_rescore_task, tasks)
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = prior_elapsed + time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                progress_path,
                {
                    "format": "gre-plastic-heredity-v2-common-rescore-progress-v1",
                    "completed_populations": index,
                    "total_populations": len(tasks),
                    "elapsed_seconds": elapsed,
                    "populations_per_second": rate,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress is not None:
                progress(f"common endpoint rescore {index}/{len(tasks)} populations")
    finally:
        if executor is not None:
            executor.shutdown()
    analysis = analyze_common_rescore(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    elapsed = prior_elapsed + time.monotonic() - started
    manifest = {
        "format": "gre-plastic-heredity-v2-common-rescore-manifest-v1",
        "protocol_digest": digest,
        "populations": len(results),
        "expected_populations": expected,
        "elapsed_seconds": elapsed,
        "workers": workers,
        "runtime": runtime_manifest(),
    }
    _atomic_json(destination / "manifest.json", manifest)
    lines = [
        "# Corrected common-endpoint evolution rescore",
        "",
        "> Exploratory post-hoc analysis; it cannot confirm evolution.",
        "",
        f"- Populations rescored: {len(results)}",
        "- Founder and selected genotypes were tested on the same descendant-memory endpoint.",
        "- The completed v1 parent was read only.",
        "",
        "## Common-assay changes",
        "",
    ]
    for treatment, estimate in analysis["cells"].items():
        lines.append(f"- `{treatment}`: {estimate['mean']} {estimate['interval']}")
    lines.extend(("", "## Memory-selection contrasts", ""))
    for control, estimate in analysis["contrasts"].items():
        lines.append(f"- versus `{control}`: {estimate['mean']} {estimate['interval']}")
    (destination / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_checksums(destination)
    verify_common_endpoint_rescore(destination)
    return destination


def verify_common_endpoint_rescore(directory: Path) -> dict[str, Any]:
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != RESCORE_REGISTRATION_FORMAT:
        raise ValueError("v2 common-rescore registration format mismatch")
    spec = EvolutionV2Spec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("v2 common-rescore protocol digest mismatch")
    population_files = list((directory / "populations").glob("*.json"))
    if len(population_files) != int(manifest["populations"]):
        raise ValueError("v2 common-rescore population count mismatch")
    return {
        "verified": True,
        "files": len(checksums),
        "populations": len(population_files),
        "protocol_digest": digest,
    }
