"""Fresh copy-environment discrimination screen for Wagner PH origin v1."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterator

from .artifacts import (
    canonical_digest,
    read_json,
    runtime_manifest,
    verify_checksums,
    write_checksums,
    write_json,
)
from .wagner_ph_bridge_analysis import _interval
from .wagner_ph_bridge_evolution import _deserialize_genotype
from .wagner_ph_origin_config import ORIGIN_SCREEN_FORMAT, OriginScreenSpec
from .wagner_ph_renewal_config import RenewalEvolutionSpec
from .wagner_ph_renewal_evolution import _assay_genotype, _risk


SCREEN_REGISTRATION_FORMAT = "gre-wagner-ph-origin-screen-registration-v1"
SCREEN_MANIFEST_FORMAT = "gre-wagner-ph-origin-screen-manifest-v1"


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    write_json(temporary, value)
    temporary.replace(path)


def _screen_task(
    args: tuple[str, str, dict[str, Any], dict[str, Any], str]
) -> dict[str, Any]:
    archive_text, output_text, screen_value, parent_spec_value, protocol_digest = args
    archive_path = Path(archive_text)
    output = Path(output_text)
    screen = OriginScreenSpec.from_dict(screen_value)
    parent_spec = RenewalEvolutionSpec.from_dict(parent_spec_value)
    population_index = int(archive_path.stem.rsplit("-", 1)[1])
    archive = read_json(archive_path)
    selected = _deserialize_genotype(archive["selected"])
    environment_name = output.name.split(".population-", 1)[0]
    environment = next(
        value for value in screen.environments if value.name == environment_name
    )
    final_path = Path(f"{output}.json")
    if final_path.is_file():
        prior = read_json(final_path)
        if prior.get("protocol_digest") == protocol_digest:
            return prior
        raise ValueError(f"origin screen registration differs: {final_path}")
    assay_spec = replace(
        parent_spec,
        selected_noise=environment,
        harsher_noise=environment,
        selected_environment=environment.name,
        harsher_environment=environment.name,
    )
    source_id = f"origin-screen.population-{population_index:03d}"
    assay = _assay_genotype(
        *selected,
        archive["task"],
        assay_spec,
        source_id,
        f"{environment.name}.population-{population_index:03d}",
        screen.futures_per_history,
        screen.checkpoint_generations,
        screen.challenges,
        "minimal",
        master_seed=screen.master_seed,
    )
    result = {
        "format": ORIGIN_SCREEN_FORMAT,
        "protocol_digest": protocol_digest,
        "environment": environment.name,
        "population_index": population_index,
        "parent_population_id": archive["population_id"],
        "parent_result_digest": archive["result_digest"],
        "source_id": source_id,
        "assay": assay,
    }
    result["result_digest"] = canonical_digest(
        {"environment": environment.name, "population": population_index, "assay": assay}
    )
    _atomic_json(final_path, result)
    return result


def _metric(
    result: dict[str, Any], generation: int, challenge: str, kind: str
) -> float:
    assay = result["assay"]
    if kind == "intact_gain":
        return _risk(assay, "candidate.intact", generation, "risk_gain", challenge)
    if kind == "renewal_contrast":
        return _risk(
            assay, "candidate.intact", generation, "correct_rate", challenge
        ) - _risk(
            assay, "candidate.renewal-off", generation, "correct_rate", challenge
        )
    raise ValueError(kind)


def analyze_origin_screen(
    results: list[dict[str, Any]], spec: OriginScreenSpec
) -> dict[str, Any]:
    spec.validate()
    simultaneous = len(spec.environments) * 4
    cells: dict[str, Any] = {}
    for environment in spec.environments:
        values = [
            value for value in results if value["environment"] == environment.name
        ]
        metrics: dict[str, Any] = {}
        for generation in (8, 12):
            for kind in ("intact_gain", "renewal_contrast"):
                for challenge in spec.challenges:
                    label = f"{kind}_g{generation}_{challenge}"
                    metrics[label] = _interval(
                        (
                            _metric(value, generation, challenge, kind)
                            for value in values
                        ),
                        spec.master_seed,
                        f"origin-screen.{environment.name}.{label}",
                        spec.bootstrap_repetitions,
                        spec.interval_level,
                        simultaneous,
                    )
        criteria = {
            "intact_g8_mean_at_least_0_25": float(
                metrics["intact_gain_g8_forced_break"]["mean"] or -1.0
            )
            >= spec.minimum_intact_g8,
            "intact_g8_simultaneous_lower_above_zero": float(
                metrics["intact_gain_g8_forced_break"]["lower"] or -1.0
            )
            > 0.0,
            "intact_g12_simultaneous_lower_above_zero": float(
                metrics["intact_gain_g12_forced_break"]["lower"] or -1.0
            )
            > 0.0,
            "renewal_g8_mean_at_least_0_10": float(
                metrics["renewal_contrast_g8_forced_break"]["mean"] or -1.0
            )
            >= spec.minimum_renewal_contrast,
            "renewal_g8_simultaneous_lower_above_zero": float(
                metrics["renewal_contrast_g8_forced_break"]["lower"] or -1.0
            )
            > 0.0,
            "renewal_g12_mean_at_least_0_10": float(
                metrics["renewal_contrast_g12_forced_break"]["mean"] or -1.0
            )
            >= spec.minimum_renewal_contrast,
            "renewal_g12_simultaneous_lower_above_zero": float(
                metrics["renewal_contrast_g12_forced_break"]["lower"] or -1.0
            )
            > 0.0,
        }
        cells[environment.name] = {
            "environment": environment.to_dict()
            if hasattr(environment, "to_dict")
            else {
                "name": environment.name,
                "dilution": environment.dilution,
                "dropout": environment.dropout,
                "sigma": environment.sigma,
            },
            "metrics": metrics,
            "criteria": criteria,
            "qualified": all(criteria.values()),
        }
    ordered = [value.name for value in spec.environments]
    selectable = ordered[:-1]
    qualified = [name for name in selectable if cells[name]["qualified"]]
    if qualified:
        selected = qualified[0]
        mode = "qualified-screen"
    else:
        selected = "d085-p002"
        mode = "sealed-parent-diagnostic-fallback"
    selected_index = ordered.index(selected)
    selection = {
        "format": "gre-wagner-ph-origin-environment-selection-v1",
        "mode": mode,
        "primary_screen_passed": mode == "qualified-screen",
        "selected_environment": selected,
        "next_harsher_environment": ordered[selected_index + 1],
        "selected_cell": selected,
        "rule": (
            "first of seven ordered environments satisfying all simultaneous gates; "
            "eighth cell is challenge-only; otherwise d085-p002 diagnostic fallback"
        ),
        "frozen_before_evolution": True,
    }
    return {
        "format": "gre-wagner-ph-origin-screen-analysis-v1",
        "population_count": len(
            {int(value["population_index"]) for value in results}
        ),
        "environment_order": ordered,
        "cells": cells,
        "selection": selection,
        "verdict": {"discriminating_environment_found": mode == "qualified-screen"},
        "fresh_seed": True,
        "claim_boundary": (
            "The adaptive screen chooses a copying regime for a new exploratory campaign; "
            "it is not held-out evidence for the downstream origin verdict."
        ),
    }


def render_screen_report(analysis: dict[str, Any]) -> str:
    selection = analysis["selection"]
    return "\n".join(
        (
            "# Wagner PH origin discrimination screen",
            "",
            f"- Discriminating environment: **{'PASS' if analysis['verdict']['discriminating_environment_found'] else 'fallback'}**",
            f"- Selected environment: `{selection['selected_environment']}`",
            f"- Next-harsher challenge: `{selection['next_harsher_environment']}`",
            f"- Selection mode: `{selection['mode']}`",
            "",
            analysis["claim_boundary"],
            "",
        )
    )


def run_origin_screen(
    parent: Path,
    spec: OriginScreenSpec,
    destination: Path,
    workers: int = 4,
    progress: Callable[[str], None] | None = None,
) -> Path:
    spec.validate()
    if workers < 1 or workers > 4:
        raise ValueError("origin screen permits one to four workers")
    parent = parent.resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "SHA256SUMS").is_file():
        verify_origin_screen(destination)
        return destination
    parent_registration = read_json(parent / "evolution" / "registration.json")
    parent_spec = RenewalEvolutionSpec.from_dict(parent_registration["protocol"])
    parent_files = [
        parent
        / "evolution"
        / "populations"
        / f"renewal_standard_cost.population-{index:03d}.json"
        for index in range(spec.parent_populations)
    ]
    if not all(path.is_file() for path in parent_files):
        raise FileNotFoundError("origin screen requires six sealed renewal populations")
    digest = canonical_digest(spec.to_dict())
    registration = {
        "format": SCREEN_REGISTRATION_FORMAT,
        "protocol": spec.to_dict(),
        "protocol_digest": digest,
        "parent_evolution_protocol_digest": parent_registration["protocol_digest"],
        "parent_population_result_digests": {
            path.stem: read_json(path)["result_digest"] for path in parent_files
        },
        "fresh_assay_seed": True,
        "selection_rule_frozen_before_screen": True,
        "eighth_environment_is_challenge_only": True,
    }
    registration_path = destination / "registration.json"
    if registration_path.is_file() and canonical_digest(
        read_json(registration_path)
    ) != canonical_digest(registration):
        raise ValueError("existing origin screen registration differs")
    if not registration_path.is_file():
        _atomic_json(registration_path, registration)
    units = destination / "units"
    units.mkdir(exist_ok=True)
    tasks = [
        (
            str(parent_file),
            str(units / f"{environment.name}.population-{index:03d}"),
            spec.to_dict(),
            parent_spec.to_dict(),
            digest,
        )
        for environment in spec.environments
        for index, parent_file in enumerate(parent_files)
    ]
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    executor: concurrent.futures.ProcessPoolExecutor | None = None
    if workers == 1:
        iterator: Iterator[dict[str, Any]] = map(_screen_task, tasks)
    else:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
        iterator = executor.map(_screen_task, tasks)
    try:
        for index, result in enumerate(iterator, start=1):
            results.append(result)
            elapsed = time.monotonic() - started
            rate = index / max(elapsed, 1e-9)
            _atomic_json(
                destination / "progress.json",
                {
                    "format": "gre-wagner-ph-origin-screen-progress-v1",
                    "completed_units": index,
                    "total_units": len(tasks),
                    "elapsed_seconds": elapsed,
                    "eta_seconds": (len(tasks) - index) / rate if rate else None,
                },
            )
            if progress:
                progress(f"origin discrimination screen {index}/{len(tasks)} units")
    finally:
        if executor is not None:
            executor.shutdown()
    analysis = analyze_origin_screen(results, spec)
    _atomic_json(destination / "analysis.json", analysis)
    _atomic_json(destination / "selection.json", analysis["selection"])
    (destination / "report.md").write_text(
        render_screen_report(analysis), encoding="utf-8"
    )
    _atomic_json(
        destination / "manifest.json",
        {
            "format": SCREEN_MANIFEST_FORMAT,
            "protocol_digest": digest,
            "unit_count": len(results),
            "expected_unit_count": len(tasks),
            "analysis_digest": canonical_digest(analysis),
            "elapsed_seconds": time.monotonic() - started,
            "workers": workers,
            "runtime": runtime_manifest(),
        },
    )
    write_checksums(destination)
    verify_origin_screen(destination)
    return destination


def verify_origin_screen(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    checksums = verify_checksums(directory)
    registration = read_json(directory / "registration.json")
    manifest = read_json(directory / "manifest.json")
    if registration.get("format") != SCREEN_REGISTRATION_FORMAT:
        raise ValueError("origin screen registration format mismatch")
    if manifest.get("format") != SCREEN_MANIFEST_FORMAT:
        raise ValueError("origin screen manifest format mismatch")
    spec = OriginScreenSpec.from_dict(registration["protocol"])
    digest = canonical_digest(spec.to_dict())
    if digest != registration.get("protocol_digest") or digest != manifest.get(
        "protocol_digest"
    ):
        raise ValueError("origin screen protocol digest mismatch")
    expected = len(spec.environments) * spec.parent_populations
    files = list((directory / "units").glob("*.json"))
    if len(files) != expected or int(manifest["unit_count"]) != expected:
        raise ValueError("origin screen unit count mismatch")
    for path in files:
        value = read_json(path)
        if value.get("protocol_digest") != digest:
            raise ValueError(f"origin screen unit digest mismatch: {path.name}")
    analysis = read_json(directory / "analysis.json")
    if canonical_digest(analysis) != manifest.get("analysis_digest"):
        raise ValueError("origin screen analysis digest mismatch")
    if canonical_digest(read_json(directory / "selection.json")) != canonical_digest(
        analysis["selection"]
    ):
        raise ValueError("origin screen selection mismatch")
    return {"verified": True, "units": expected, "checksums": len(checksums)}


def replay_origin_screen_unit(directory: Path, unit_id: str) -> dict[str, Any]:
    directory = directory.resolve()
    archived = read_json(directory / "units" / f"{unit_id}.json")
    registration = read_json(directory / "registration.json")
    screen = OriginScreenSpec.from_dict(registration["protocol"])
    provenance_path = directory.parent / "parent-provenance.json"
    if not provenance_path.is_file():
        raise FileNotFoundError(
            f"origin screen replay requires campaign provenance: {provenance_path}"
        )
    parent = Path(read_json(provenance_path)["parent"])
    parent_registration = read_json(parent / "evolution" / "registration.json")
    parent_spec = RenewalEvolutionSpec.from_dict(parent_registration["protocol"])
    population_index = int(archived["population_index"])
    parent_archive = read_json(
        parent
        / "evolution"
        / "populations"
        / f"renewal_standard_cost.population-{population_index:03d}.json"
    )
    selected = _deserialize_genotype(parent_archive["selected"])
    environment = next(
        value
        for value in screen.environments
        if value.name == str(archived["environment"])
    )
    assay_spec = replace(
        parent_spec,
        selected_noise=environment,
        harsher_noise=environment,
        selected_environment=environment.name,
        harsher_environment=environment.name,
    )
    source_id = f"origin-screen.population-{population_index:03d}"
    assay = _assay_genotype(
        *selected,
        parent_archive["task"],
        assay_spec,
        source_id,
        f"{environment.name}.population-{population_index:03d}",
        screen.futures_per_history,
        screen.checkpoint_generations,
        screen.challenges,
        "minimal",
        master_seed=screen.master_seed,
    )
    regenerated = canonical_digest(
        {
            "environment": environment.name,
            "population": population_index,
            "assay": assay,
        }
    )
    return {
        "unit_id": unit_id,
        "matches": archived.get("result_digest") == regenerated,
        "archived_digest": archived.get("result_digest"),
        "regenerated_digest": regenerated,
    }
