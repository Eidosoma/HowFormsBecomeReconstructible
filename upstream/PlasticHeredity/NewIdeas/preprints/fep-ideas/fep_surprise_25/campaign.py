from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, TypeVar

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from fep_surprise.tracing import trace_future
from fep_surprise_15 import compat
from fep_surprise_15.integrity import (
    atomic_destination,
    canonical_digest,
    sha256_file,
    verify_checksums,
    write_checksums,
)
from fep_surprise_15.observers import fit_observer_ensemble
from fep_surprise_15.validation import _scientific_geometry
from plastic_heredity.config import CANDIDATES as SIMULATOR_CONTRACTS
from plastic_heredity.config import GardConfig
from plastic_heredity.simulator import generate_beta, generate_initial_composition

from .analysis import analyze_confirmation
from .budget import TimeBudgetExhausted, budget_status, ensure_budget, guard_budget
from .config import CANDIDATES, STRATA, Campaign25Config
from .regime import Screen25Spec, classify_break_regime, load_screen, screen_matrix
from .validation import validate
from .worker import (
    Cell25Spec,
    load_atlases,
    load_design,
    load_futures,
    prepare_cell,
    run_futures,
)


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
FORMAT = "fep-surprise-25-registration-v1"
SHARED_SOURCES = (
    "fep_surprise/dynamics.py",
    "fep_surprise/tracing.py",
    "fep_surprise_15/compat.py",
    "fep_surprise_15/integrity.py",
    "fep_surprise_15/observers.py",
    "fep_surprise_15/predictor.py",
    "fep_surprise_2/atlas.py",
    "fep_surprise_2/interventions.py",
    "fep_surprise_2/validation.py",
    "fep_surprise_2/worker.py",
)


def profile_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile


def validation_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "validation"


def benchmark_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "benchmark"


def registration_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "registration"


def screen_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "screen"


def confirmation_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "confirmation"


def replay_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "confirmation_replay"


def analysis_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "analysis"


def _locked_requirements() -> dict[str, str]:
    output = {}
    for line in (CAMPAIGN_ROOT / "requirements-25-lock.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        output[name] = version
    return output


def _runtime_manifest() -> dict[str, Any]:
    packages = {}
    for name in _locked_requirements():
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    python_version = platform.python_version()
    return {
        "python": python_version,
        "platform": platform.platform(),
        "packages": packages,
        "lock_matches": bool(
            packages == _locked_requirements() and python_version == "3.13.5"
        ),
        "simulator_root": str(compat.PLASTIC_HEREDITY_ROOT),
    }


def _source_hashes() -> dict[str, str]:
    sources = {
        str(path.relative_to(CAMPAIGN_ROOT)): sha256_file(path)
        for path in sorted((CAMPAIGN_ROOT / "fep_surprise_25").glob("*.py"))
    }
    for name in SHARED_SOURCES:
        sources[name] = sha256_file(CAMPAIGN_ROOT / name)
    for name in compat.REQUIRED_SIMULATOR_SOURCES:
        sources[f"simulator::{name}"] = sha256_file(compat.PLASTIC_HEREDITY_ROOT / name)
    for name in ("EXPERIMENT_2_5_PREREGISTRATION.md", "requirements-25-lock.txt"):
        sources[name] = sha256_file(CAMPAIGN_ROOT / name)
    return sources


def validate_stage(run_root: Path, config: Campaign25Config) -> Path:
    ensure_budget(run_root, config)
    guard_budget(run_root, config, "validation")
    destination = validation_path(run_root, config.profile)
    if destination.exists():
        verify_validation(destination, config)
        return destination
    with atomic_destination(destination) as output:
        results = validate(config, output)
        runtime = _runtime_manifest()
        if not runtime["lock_matches"]:
            raise ValueError("installed environment differs from requirements-25-lock.txt")
        seal = {
            "format": "fep-surprise-25-validation-seal-v1",
            "profile": config.profile,
            "all_pass": bool(results["all_pass"]),
            "sources": _source_hashes(),
            "runtime": runtime,
        }
        seal["validation_id"] = canonical_digest(seal)
        (output / "validation_seal.json").write_text(
            json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    return destination


def verify_validation(path: Path, config: Campaign25Config) -> dict[str, Any]:
    verify_checksums(path)
    results = json.loads((path / "validation.json").read_text(encoding="utf-8"))
    if not results.get("all_pass"):
        raise ValueError("Experiment 2.5 validation did not pass")
    seal = json.loads((path / "validation_seal.json").read_text(encoding="utf-8"))
    identifier = seal.pop("validation_id")
    if canonical_digest(seal) != identifier:
        raise ValueError("validation identifier mismatch")
    seal["validation_id"] = identifier
    if seal["profile"] != config.profile or seal["sources"] != _source_hashes():
        raise ValueError("validation profile or source tree changed")
    if seal["runtime"] != _runtime_manifest() or not seal["runtime"]["lock_matches"]:
        raise ValueError("validated runtime changed")
    return {"seal": seal, "results": results}


def _benchmark_dynamics(config: Campaign25Config) -> tuple[float, int]:
    gard = GardConfig(generations=max(config.screen.landmarks))
    beta = generate_beta(gard, np.random.default_rng(2525001))
    initial = generate_initial_composition(gard, np.random.default_rng(2525002))
    horizon = 32
    traces = 8
    started = time.perf_counter()
    simulated = 0
    for candidate in CANDIDATES:
        for branch in range(traces):
            traced, _ = trace_future(
                initial, beta, gard, SIMULATOR_CONTRACTS[candidate], horizon,
                np.random.default_rng(2525100 + branch), config.phase_grid,
            )
            simulated += len(traced)
    elapsed = time.perf_counter() - started
    if simulated < horizon:
        raise RuntimeError("disposable benchmark produced too few fissions")
    return elapsed / simulated, simulated


def _benchmark_observer(config: Campaign25Config) -> float:
    parents, phases, lineages = _scientific_geometry(len(config.phase_grid))
    started = time.perf_counter()
    fit_observer_ensemble(
        parents,
        phases,
        lineages,
        pseudocount=config.pseudocount,
        reference_mass=config.reference_mass,
        pca_variance=config.pca_variance,
        pca_min=config.pca_min,
        pca_max=config.pca_max,
        knn_k=config.knn_k,
        mixture_k_max=min(config.mixture_k_max, 3),
        training_subsample=800,
        seed=2525,
    )
    return time.perf_counter() - started


def _project_seconds(
    config: Campaign25Config,
    quota: int,
    seconds_per_fission: float,
    seconds_per_fit: float,
    workers: int,
) -> dict[str, float]:
    screen = config.screen
    scale = config.confirmation
    generation_workers = max(1, min(int(workers), config.generation_workers))
    replay_workers = max(1, min(config.replay_workers, generation_workers))
    screen_fissions = screen.matrices * len(CANDIDATES) * (
        screen.main_generations
        + len(screen.landmarks) * screen.branches * screen.horizon
    )
    per_cell = (
        len(scale.landmarks) * scale.damage_perturbations * 2 * scale.damage_horizon
        + 6 * scale.reference_lineages * scale.reference_fissions
        + len(scale.landmarks) * 11 * scale.pilot_branches * scale.pilot_horizon
        + len(scale.landmarks) * 11 * scale.branches * scale.horizon
        + len(scale.landmarks) * 11 * scale.durability_events * scale.durability_horizon
    )
    cells = quota * len(STRATA) * len(CANDIDATES)
    screen_wall = screen_fissions * seconds_per_fission * (
        1 / generation_workers + 1 / replay_workers
    )
    fit_scale = max(1.0, scale.training_subsample / 800.0)
    confirmation_wall = cells * (
        per_cell * seconds_per_fission + 6 * seconds_per_fit * fit_scale
    ) * (1 / generation_workers + 1 / replay_workers)
    raw = 600.0 + screen_wall + confirmation_wall
    return {
        "screen_fissions_each_pass": float(screen_fissions),
        "confirmation_fissions_per_cell_each_pass": float(per_cell),
        "confirmation_cells": float(cells),
        "raw_remaining_seconds": raw,
        "conservative_remaining_seconds": raw * config.conservative_multiplier,
    }


def benchmark(run_root: Path, config: Campaign25Config, workers: int) -> Path:
    verify_validation(validation_path(run_root, config.profile), config)
    guard_budget(run_root, config, "benchmark")
    destination = benchmark_path(run_root, config.profile)
    if destination.exists():
        verify_benchmark(destination, config)
        return destination
    with atomic_destination(destination) as output:
        seconds_per_fission, simulated = _benchmark_dynamics(config)
        seconds_per_fit = _benchmark_observer(config)
        elapsed = budget_status(run_root, config)["elapsed_seconds"]
        projections = {
            "large": _project_seconds(
                config, config.large_selected_per_stratum,
                seconds_per_fission, seconds_per_fit, workers,
            ),
            "compact": _project_seconds(
                config, config.compact_selected_per_stratum,
                seconds_per_fission, seconds_per_fit, workers,
            ),
        }
        for value in projections.values():
            value["conservative_total_seconds"] = (
                elapsed + value["conservative_remaining_seconds"]
            )
        if config.profile != "full":
            chosen = config.confirmation.selected_per_stratum
            mode = config.profile
        elif projections["large"]["conservative_total_seconds"] <= config.large_projection_ceiling_seconds:
            chosen, mode = config.large_selected_per_stratum, "large"
        elif projections["compact"]["conservative_total_seconds"] <= config.graceful_stop_seconds:
            chosen, mode = config.compact_selected_per_stratum, "compact"
        else:
            chosen, mode = 0, "abort"
        payload = {
            "format": "fep-surprise-25-benchmark-v1",
            "profile": config.profile,
            "disposable_seed_domain": "benchmark-only-never-scientific",
            "seconds_per_fission": seconds_per_fission,
            "benchmark_fissions": simulated,
            "seconds_per_observer_fit": seconds_per_fit,
            "workers": int(workers),
            "projections": projections,
            "selected_per_stratum": chosen,
            "selected_profile": mode,
            "eligible_to_register": bool(chosen > 0),
            "sources": _source_hashes(),
        }
        payload["benchmark_id"] = canonical_digest(payload)
        (output / "benchmark.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    if chosen == 0:
        raise TimeBudgetExhausted("compact profile projects beyond the 12-hour budget")
    return destination


def verify_benchmark(path: Path, config: Campaign25Config) -> dict[str, Any]:
    verify_checksums(path)
    payload = json.loads((path / "benchmark.json").read_text(encoding="utf-8"))
    identifier = payload.pop("benchmark_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("benchmark identifier mismatch")
    payload["benchmark_id"] = identifier
    if payload["profile"] != config.profile or payload["sources"] != _source_hashes():
        raise ValueError("benchmark profile or source tree changed")
    if not payload["eligible_to_register"]:
        raise TimeBudgetExhausted("benchmark forbids scientific registration")
    return payload


def _resolved_config(run_root: Path, config: Campaign25Config) -> Campaign25Config:
    result = verify_benchmark(benchmark_path(run_root, config.profile), config)
    return config.resolved(int(result["selected_per_stratum"]))


def protocol(
    config: Campaign25Config,
    validation_bundle: dict[str, Any],
    benchmark_bundle: dict[str, Any],
    budget_start: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "format": FORMAT,
        "status": "sealed_before_scientific_screen_matrix_generation",
        "title": "Experiment 2.5 — Goldilocks Crossing",
        "config": config.to_dict(),
        "validation_id": validation_bundle["seal"]["validation_id"],
        "benchmark_id": benchmark_bundle["benchmark_id"],
        "budget_start": budget_start,
        "preregistration": "EXPERIMENT_2_5_PREREGISTRATION.md",
        "stage_order": [
            "validation",
            "disposable_benchmark_and_profile_selection",
            "registration",
            "screen_generation_exact_replay_and_selection_seal",
            "target_atlases_damage_metrics_and_pilots",
            "confirmation_design_seal_before_main_outcomes",
            "main_outcomes_and_selected_lineage_durability_seal",
            "exact_confirmation_replay",
            "analysis",
        ],
        "selection_firewall": (
            "Sealed Experiment 2 outcomes are disclosed discovery only. All screen, "
            "pilot, confirmation, and durability streams use fresh Experiment 2.5 domains."
        ),
        "terminal_prefix_rule": (
            "Every terminal prefix is retained at its resolved length without retry, "
            "replacement, resampling, or conversion into a compositional break."
        ),
        "analysis_firewall": (
            "Main outcomes cannot be analyzed before every confirmation cell replays exactly."
        ),
        "claim_boundary": (
            "At most simulator-specific regime-gated rehoming and incremental calibrated "
            "surprise; never FEP, active inference, agency, prebiotic chemistry, universal "
            "origins, inherited observer-independent forms, or Platonic causation."
        ),
        "sources": _source_hashes(),
    }
    payload["registration_id"] = canonical_digest(payload)
    return payload


def register(run_root: Path, base_config: Campaign25Config) -> Path:
    validation_bundle = verify_validation(
        validation_path(run_root, base_config.profile), base_config
    )
    benchmark_bundle = verify_benchmark(
        benchmark_path(run_root, base_config.profile), base_config
    )
    config = base_config.resolved(int(benchmark_bundle["selected_per_stratum"]))
    guard_budget(run_root, config, "registration")
    destination = registration_path(run_root, config.profile)
    if destination.exists():
        verify_registration(destination, base_config)
        return destination
    with atomic_destination(destination) as output:
        payload = protocol(
            config, validation_bundle, benchmark_bundle, ensure_budget(run_root, config)
        )
        (output / "protocol.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "runtime.json").write_text(
            json.dumps(_runtime_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "README.md").write_text(
            "# Sealed Experiment 2.5 protocol\n\n"
            f"Registration ID: `{payload['registration_id']}`\n\n"
            "Sealed after disposable timing and before any scientific screen matrix.\n",
            encoding="utf-8",
        )
        write_checksums(output)
    return destination


def verify_registration(path: Path, base_config: Campaign25Config) -> dict[str, Any]:
    verify_checksums(path)
    payload = json.loads((path / "protocol.json").read_text(encoding="utf-8"))
    if payload.get("format") != FORMAT:
        raise ValueError("unsupported Experiment 2.5 registration")
    identifier = payload.pop("registration_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("registration identifier mismatch")
    payload["registration_id"] = identifier
    benchmark_bundle = verify_benchmark(
        benchmark_path(path.parents[1], base_config.profile), base_config
    )
    resolved = base_config.resolved(int(benchmark_bundle["selected_per_stratum"]))
    if payload["config"] != json.loads(json.dumps(resolved.to_dict())):
        raise ValueError("registered config differs from selected benchmark profile")
    if payload["sources"] != _source_hashes():
        raise ValueError("registered source tree changed")
    current_budget = ensure_budget(path.parents[1], resolved)
    if payload["budget_start"] != current_budget:
        raise ValueError("campaign budget clock differs from its registration")
    validation_bundle = verify_validation(
        validation_path(path.parents[1], base_config.profile), base_config
    )
    if payload["validation_id"] != validation_bundle["seal"]["validation_id"]:
        raise ValueError("registration references another validation")
    return payload


T = TypeVar("T")


def _parallel(
    jobs: list[T],
    operation: Callable[[T, Campaign25Config], Path],
    config: Campaign25Config,
    run_root: Path,
    workers: int,
    complete: Callable[[T], bool],
    result_path: Callable[[T], Path],
    label: str,
) -> list[Path]:
    checkpointed = [job for job in jobs if complete(job)]
    pending = [job for job in jobs if not complete(job)]
    results = [result_path(job) for job in checkpointed]
    print(f"[{label}] {len(checkpointed)} checkpointed, {len(pending)} pending", flush=True)
    worker_count = max(1, int(workers))
    with threadpool_limits(limits=1):
        if worker_count == 1:
            for index, job in enumerate(pending, 1):
                guard_budget(run_root, config, label)
                results.append(operation(job, config))
                print(f"[{label}] {index}/{len(pending)}", flush=True)
        else:
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                iterator = iter(pending)
                active = {}
                for _ in range(min(worker_count, len(pending))):
                    job = next(iterator)
                    active[executor.submit(operation, job, config)] = job
                completed = 0
                while active:
                    done, _ = wait(active, return_when=FIRST_COMPLETED)
                    for future in done:
                        active.pop(future)
                        results.append(future.result())
                        completed += 1
                        print(f"[{label}] {completed}/{len(pending)}", flush=True)
                        guard_budget(run_root, config, label)
                        try:
                            job = next(iterator)
                        except StopIteration:
                            continue
                        active[executor.submit(operation, job, config)] = job
    return sorted(results)


def _screen_jobs(output: Path, config: Campaign25Config) -> list[Screen25Spec]:
    cells = output / "cells"
    return [Screen25Spec(matrix, cells) for matrix in range(config.screen.matrices)]


def _artifact_hashes(output: Path, kind: str) -> dict[str, str]:
    cells = output / "cells"
    if kind == "screen":
        paths = sorted(cells.glob("screen_*.joblib"))
    elif kind == "design":
        paths = sorted(cells.glob("cell_*_design.joblib"))
        paths += sorted(cells.glob("cell_*_atlases.joblib"))
        paths += sorted(cells.glob("cell_*.json"))
    elif kind == "futures":
        paths = sorted(cells.glob("cell_*_futures.joblib"))
    else:
        raise ValueError(kind)
    return {path.name: sha256_file(path) for path in paths}


def _write_manifest(output: Path, kind: str, count: int) -> dict[str, Any]:
    artifacts = _artifact_hashes(output, kind)
    payload = {
        "format": f"fep-surprise-25-{kind}-manifest-v1",
        "cell_count": count,
        "artifacts": artifacts,
    }
    if kind == "design" and len(artifacts) != count * 3:
        raise ValueError("design manifest does not contain three files per cell")
    if kind != "design" and len(artifacts) != count:
        raise ValueError(f"{kind} manifest cell count mismatch")
    payload[f"{kind}_id"] = canonical_digest(payload)
    (output / f"{kind}_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _verify_manifest(output: Path, kind: str, count: int) -> dict[str, Any]:
    payload = json.loads((output / f"{kind}_manifest.json").read_text(encoding="utf-8"))
    identifier = payload.pop(f"{kind}_id")
    if canonical_digest(payload) != identifier:
        raise ValueError(f"{kind} manifest identifier mismatch")
    payload[f"{kind}_id"] = identifier
    if payload["cell_count"] != count or payload["artifacts"] != _artifact_hashes(output, kind):
        raise ValueError(f"{kind} artifacts differ from sealed manifest")
    return payload


def _replay_screen_one(original_name: str, config: Campaign25Config) -> dict[str, Any]:
    path = Path(original_name)
    original = load_screen(path)
    with tempfile.TemporaryDirectory(prefix="fep25-screen-replay-") as temporary:
        spec = Screen25Spec(int(original["matrix_id"]), Path(temporary), force=True)
        replayed = load_screen(screen_matrix(spec, config))
    exact = joblib.hash(original) == joblib.hash(replayed)
    return {
        "matrix_id": int(original["matrix_id"]),
        "artifact": path.name,
        "payload_exact": exact,
        "scientific_digest_exact": original["scientific_digest"] == replayed["scientific_digest"],
        "exact": bool(exact and original["scientific_digest"] == replayed["scientific_digest"]),
    }


def _replay_screen(
    paths: list[Path], audits: Path, config: Campaign25Config,
    run_root: Path, workers: int,
) -> dict[str, Any]:
    audits.mkdir(parents=True, exist_ok=True)
    results = []
    pending = []
    for path in paths:
        audit_path = audits / f"{path.stem}.json"
        if audit_path.exists():
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if not audit["exact"]:
                raise ValueError(f"prior screen replay mismatch: {path.name}")
            results.append(audit)
        else:
            pending.append(path)
    with threadpool_limits(limits=1):
        worker_count = max(1, workers)
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            iterator = iter(pending)
            active = {}
            for _ in range(min(worker_count, len(pending))):
                path = next(iterator)
                active[executor.submit(_replay_screen_one, str(path), config)] = path
            progress = 0
            while active:
                done, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in done:
                    path = active.pop(future)
                    audit = future.result()
                    (audits / f"{path.stem}.json").write_text(
                        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                    )
                    if not audit["exact"]:
                        raise ValueError(f"screen replay mismatch: {path.name}")
                    results.append(audit)
                    progress += 1
                    print(f"[screen-replay] {progress}/{len(pending)}", flush=True)
                    guard_budget(run_root, config, "screen-replay")
                    try:
                        next_path = next(iterator)
                    except StopIteration:
                        continue
                    active[executor.submit(_replay_screen_one, str(next_path), config)] = next_path
    return {"cells": len(results), "all_exact": bool(results and all(x["exact"] for x in results))}


def _select_screen(output: Path, config: Campaign25Config) -> dict[str, Any]:
    records = []
    for path in sorted((output / "cells").glob("screen_*.joblib")):
        payload = load_screen(path)
        if not all(payload["candidates"][candidate]["usable"] for candidate in CANDIDATES):
            continue
        probabilities = {
            candidate: float(payload["candidates"][candidate]["break_probability"])
            for candidate in CANDIDATES
        }
        records.append(
            {
                "matrix_id": int(payload["matrix_id"]),
                "candidate_break_probability": probabilities,
                "mean_break_probability": float(np.mean(list(probabilities.values()))),
                "threshold_stratum": classify_break_regime(probabilities, config),
                "artifact": path.name,
            }
        )
    quota = config.confirmation.selected_per_stratum
    selected: dict[str, list[dict[str, Any]]] = {}
    if config.profile == "full":
        for stratum in STRATA:
            eligible = [row for row in records if row["threshold_stratum"] == stratum]
            selected[stratum] = sorted(eligible, key=lambda row: row["matrix_id"])[:quota]
    else:
        ordered = sorted(records, key=lambda row: (row["mean_break_probability"], row["matrix_id"]))
        partitions = np.array_split(np.asarray(ordered, dtype=object), 3)
        selected = {
            "stable": list(partitions[0][:quota]),
            "transitional": sorted(
                list(partitions[1]), key=lambda row: abs(row["mean_break_probability"] - 0.5)
            )[:quota],
            "saturated": list(partitions[2][-quota:]),
        }
    shortfalls = {stratum: quota - len(selected[stratum]) for stratum in STRATA}
    payload = {
        "format": "fep-surprise-25-selection-v1",
        "profile": config.profile,
        "method": "two-candidate-fixed-thresholds" if config.profile == "full" else "ranked-workflow-only",
        "quota_per_stratum": quota,
        "usable_matrices": len(records),
        "threshold_counts": {
            stratum: sum(row["threshold_stratum"] == stratum for row in records)
            for stratum in STRATA
        },
        "selected": selected,
        "shortfalls": shortfalls,
        "complete": all(value == 0 for value in shortfalls.values()),
    }
    payload["selection_id"] = canonical_digest(payload)
    (output / "selection.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not payload["complete"]:
        raise RuntimeError(f"SCREEN_STRATUM_SHORTFALL_NO_VERDICT: {shortfalls}")
    return payload


def screen(run_root: Path, base_config: Campaign25Config, workers: int) -> Path:
    registration = verify_registration(
        registration_path(run_root, base_config.profile), base_config
    )
    config = _resolved_config(run_root, base_config)
    guard_budget(run_root, config, "screen")
    output = screen_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_screen(output, base_config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    jobs = _screen_jobs(output, config)
    _parallel(
        jobs, screen_matrix, config, run_root,
        min(workers, config.generation_workers),
        lambda spec: spec.path.is_file(), lambda spec: spec.path, "screen",
    )
    manifest = _write_manifest(output, "screen", len(jobs))
    replay = _replay_screen(
        [spec.path for spec in jobs], output / "replay_audits", config,
        run_root, min(workers, config.replay_workers),
    )
    if not replay["all_exact"] or replay["cells"] != len(jobs):
        raise ValueError("screen exact replay failed")
    selection = _select_screen(output, config)
    if registration["sources"] != _source_hashes():
        raise ValueError("source changed during screen")
    seal = {
        "format": "fep-surprise-25-screen-seal-v1",
        "status": "sealed_after_exact_replay_and_deterministic_selection",
        "registration_id": registration["registration_id"],
        "screen_id": manifest["screen_id"],
        "selection_id": selection["selection_id"],
        "replay": replay,
    }
    seal["screen_seal_id"] = canonical_digest(seal)
    (output / "screen.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(output)
    return output


def verify_screen(path: Path, base_config: Campaign25Config) -> dict[str, Any]:
    registration = verify_registration(
        registration_path(path.parents[1], base_config.profile), base_config
    )
    config = _resolved_config(path.parents[1], base_config)
    verify_checksums(path)
    selection = json.loads((path / "selection.json").read_text(encoding="utf-8"))
    selection_id = selection.pop("selection_id")
    if canonical_digest(selection) != selection_id or not selection["complete"]:
        raise ValueError("screen selection seal is invalid or incomplete")
    selection["selection_id"] = selection_id
    payload = json.loads((path / "screen.json").read_text(encoding="utf-8"))
    identifier = payload.pop("screen_seal_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("screen seal identifier mismatch")
    payload["screen_seal_id"] = identifier
    if payload["registration_id"] != registration["registration_id"]:
        raise ValueError("screen references another registration")
    if payload["selection_id"] != selection_id or not payload["replay"]["all_exact"]:
        raise ValueError("screen replay or selection gate failed")
    _verify_manifest(path, "screen", config.screen.matrices)
    return {"seal": payload, "selection": selection}


def _confirmation_jobs(
    output: Path, screen_output: Path, selection: dict[str, Any]
) -> list[Cell25Spec]:
    jobs = []
    for stratum in STRATA:
        for row in selection["selected"][stratum]:
            matrix = int(row["matrix_id"])
            path = screen_output / "cells" / row["artifact"]
            for candidate in CANDIDATES:
                jobs.append(Cell25Spec(matrix, candidate, stratum, path, output / "cells"))
    return jobs


def prepare_confirmation(
    run_root: Path, base_config: Campaign25Config, workers: int
) -> Path:
    registration = verify_registration(
        registration_path(run_root, base_config.profile), base_config
    )
    screened = verify_screen(screen_path(run_root, base_config.profile), base_config)
    config = _resolved_config(run_root, base_config)
    guard_budget(run_root, config, "prepare-confirmation")
    output = confirmation_path(run_root, config.profile)
    if (output / "confirmation_design.json").exists():
        verify_confirmation_design(output, base_config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    jobs = _confirmation_jobs(
        output, screen_path(run_root, config.profile), screened["selection"]
    )
    _parallel(
        jobs, prepare_cell, config, run_root,
        min(workers, config.generation_workers),
        lambda spec: spec.design_path.is_file() and spec.atlas_path.is_file() and spec.metadata_path.is_file(),
        lambda spec: spec.design_path, "confirmation-design",
    )
    if list((output / "cells").glob("*_futures.joblib")):
        raise ValueError("main outcomes exist before confirmation design seal")
    manifest = _write_manifest(output, "design", len(jobs))
    if registration["sources"] != _source_hashes():
        raise ValueError("source changed during confirmation design")
    payload = {
        "format": "fep-surprise-25-confirmation-design-v1",
        "status": "sealed_atlases_damage_metrics_and_pilots_before_main_outcomes",
        "registration_id": registration["registration_id"],
        "screen_seal_id": screened["seal"]["screen_seal_id"],
        "design_id": manifest["design_id"],
        "cells": len(jobs),
        "main_future_artifacts_present": False,
    }
    payload["confirmation_design_id"] = canonical_digest(payload)
    (output / "confirmation_design.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output


def verify_confirmation_design(path: Path, base_config: Campaign25Config) -> dict[str, Any]:
    registration = verify_registration(
        registration_path(path.parents[1], base_config.profile), base_config
    )
    screened = verify_screen(screen_path(path.parents[1], base_config.profile), base_config)
    payload = json.loads((path / "confirmation_design.json").read_text(encoding="utf-8"))
    identifier = payload.pop("confirmation_design_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("confirmation design identifier mismatch")
    payload["confirmation_design_id"] = identifier
    if payload["registration_id"] != registration["registration_id"]:
        raise ValueError("confirmation design references another registration")
    if payload["screen_seal_id"] != screened["seal"]["screen_seal_id"]:
        raise ValueError("confirmation design references another screen")
    _verify_manifest(path, "design", int(payload["cells"]))
    return payload


def _cohort_integrity(
    output: Path, config: Campaign25Config, expected: int
) -> dict[str, Any]:
    designs = sorted((output / "cells").glob("cell_*_design.joblib"))
    result = {
        "expected_cell_count": len(designs) == expected,
        "minimum_reference_states": True,
        "outcome_shapes_exact": True,
        "durability_selection_cap": True,
        "followed_events_are_strict8": True,
        "pathwise_isomorphism": True,
        "terminal_prefixes_retained": 0,
        "reference_terminal_prefixes_retained": 0,
    }
    scale = config.confirmation
    for design_path in designs:
        design = load_design(design_path)
        future = load_futures(
            design_path.with_name(design_path.name.replace("_design.joblib", "_futures.joblib"))
        )
        result["minimum_reference_states"] &= all(
            int(meta["retained_states"]) >= scale.minimum_reference_states
            for meta in design["metadata"]["reference"].values()
        )
        result["reference_terminal_prefixes_retained"] += sum(
            int(meta["terminal_prefixes"])
            for meta in design["metadata"]["reference"].values()
        )
        shape = (len(scale.landmarks), len(design["arms"]), scale.branches)
        result["outcome_shapes_exact"] &= future["strict8"].shape == shape
        followed = future["durability_followed"]
        result["durability_selection_cap"] &= bool(
            np.all(followed.sum(axis=2) <= scale.durability_events)
        )
        result["followed_events_are_strict8"] &= bool(
            np.all(followed <= future["strict8"])
        )
        native = design["arms"].index("ALIGNED_NATIVE")
        isom = design["arms"].index("ISOMORPHIC_BOTH_100")
        for key in ("strict8", "departed", "first_break", "complete", "trace_lengths", "durability_followed", "durable16"):
            result["pathwise_isomorphism"] &= bool(
                np.array_equal(future[key][:, native], future[key][:, isom])
            )
        result["terminal_prefixes_retained"] += int(np.count_nonzero(future["complete"] == 0))
    return result


def generate_confirmation(
    run_root: Path, base_config: Campaign25Config, workers: int
) -> Path:
    config = _resolved_config(run_root, base_config)
    output = confirmation_path(run_root, config.profile)
    design_seal = verify_confirmation_design(output, base_config)
    if (output / "SHA256SUMS").exists():
        verify_confirmation(output, base_config)
        return output
    guard_budget(run_root, config, "generate-confirmation")
    screened = verify_screen(screen_path(run_root, config.profile), base_config)
    jobs = _confirmation_jobs(output, screen_path(run_root, config.profile), screened["selection"])
    _parallel(
        jobs, run_futures, config, run_root,
        min(workers, config.generation_workers),
        lambda spec: spec.future_path.is_file(), lambda spec: spec.future_path,
        "confirmation-futures",
    )
    manifest = _write_manifest(output, "futures", len(jobs))
    cohort = _cohort_integrity(output, config, len(jobs))
    if not all(value for key, value in cohort.items() if not key.endswith("retained")):
        raise ValueError(f"confirmation cohort integrity failed: {cohort}")
    registration = verify_registration(
        registration_path(run_root, config.profile), base_config
    )
    if registration["sources"] != _source_hashes():
        raise ValueError("source changed during confirmation outcomes")
    if any((output / name).exists() for name in ("metrics.json", "REPORT.md")):
        raise ValueError("analysis artifact appeared inside confirmation")
    payload = {
        "format": "fep-surprise-25-confirmation-v1",
        "status": "sealed_main_and_durability_outcomes_before_replay_without_analysis",
        "confirmation_design_id": design_seal["confirmation_design_id"],
        "futures_id": manifest["futures_id"],
        "cells": len(jobs),
        "cohort_integrity": cohort,
        "analysis_artifacts_present": False,
    }
    payload["confirmation_id"] = canonical_digest(payload)
    (output / "confirmation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(output)
    return output


def verify_confirmation(path: Path, base_config: Campaign25Config) -> dict[str, Any]:
    design = verify_confirmation_design(path, base_config)
    verify_checksums(path)
    payload = json.loads((path / "confirmation.json").read_text(encoding="utf-8"))
    identifier = payload.pop("confirmation_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("confirmation identifier mismatch")
    payload["confirmation_id"] = identifier
    if payload["confirmation_design_id"] != design["confirmation_design_id"]:
        raise ValueError("confirmation references another design")
    if payload["analysis_artifacts_present"]:
        raise ValueError("analysis firewall was violated")
    _verify_manifest(path, "futures", int(payload["cells"]))
    return payload


def _replay_one(original_name: str, config: Campaign25Config) -> dict[str, Any]:
    original_path = Path(original_name)
    design = load_design(original_path)
    atlas_path = original_path.with_name(original_path.name.replace("_design.joblib", "_atlases.joblib"))
    future_path = original_path.with_name(original_path.name.replace("_design.joblib", "_futures.joblib"))
    atlases = load_atlases(atlas_path)
    futures = load_futures(future_path)
    metadata = design["metadata"]
    screen_cell = screen_path(original_path.parents[3], config.profile) / "cells" / f"screen_m{int(metadata['matrix_id']):04d}.joblib"
    with tempfile.TemporaryDirectory(prefix="fep25-confirmation-replay-") as temporary:
        spec = Cell25Spec(
            int(metadata["matrix_id"]), str(metadata["candidate"]),
            str(metadata["stratum"]), screen_cell, Path(temporary), force=True,
        )
        replay_design = load_design(prepare_cell(spec, config))
        replay_atlases = load_atlases(spec.atlas_path)
        replay_futures = load_futures(run_futures(spec, config))
    checks = {
        "design_exact": joblib.hash(design) == joblib.hash(replay_design),
        "atlas_exact": joblib.hash(atlases) == joblib.hash(replay_atlases),
        "futures_exact": joblib.hash(futures) == joblib.hash(replay_futures),
        "design_digest_exact": metadata["scientific_digest"] == replay_design["metadata"]["scientific_digest"],
        "future_digest_exact": futures["metadata"]["scientific_digest"] == replay_futures["metadata"]["scientific_digest"],
    }
    return {
        "matrix_id": int(metadata["matrix_id"]),
        "candidate": str(metadata["candidate"]),
        "stratum": str(metadata["stratum"]),
        "artifact": original_path.name,
        **checks,
        "exact": bool(all(checks.values())),
    }


def _replay_confirmation_cells(
    designs: list[Path], output: Path, config: Campaign25Config,
    run_root: Path, workers: int,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    completed = []
    pending = []
    for path in designs:
        audit_path = output / f"{path.stem}.json"
        if audit_path.exists():
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if not audit["exact"]:
                raise ValueError(f"prior replay mismatch: {path.name}")
            completed.append(audit)
        else:
            pending.append(path)
    with threadpool_limits(limits=1):
        with ProcessPoolExecutor(max_workers=max(1, workers)) as executor:
            active = {}
            iterator = iter(pending)
            for _ in range(min(max(1, workers), len(pending))):
                path = next(iterator)
                active[executor.submit(_replay_one, str(path), config)] = path
            progress = 0
            while active:
                done, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in done:
                    path = active.pop(future)
                    audit = future.result()
                    (output / f"{path.stem}.json").write_text(
                        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                    )
                    if not audit["exact"]:
                        raise ValueError(f"confirmation replay mismatch: {path.name}")
                    completed.append(audit)
                    progress += 1
                    print(f"[confirmation-replay] {progress}/{len(pending)}", flush=True)
                    guard_budget(run_root, config, "confirmation-replay")
                    try:
                        next_path = next(iterator)
                    except StopIteration:
                        continue
                    active[executor.submit(_replay_one, str(next_path), config)] = next_path
    return {
        "cells": len(completed),
        "all_exact": bool(completed and all(item["exact"] for item in completed)),
        "fresh_process_workers": max(1, workers),
    }


def replay_confirmation(
    run_root: Path, base_config: Campaign25Config, workers: int
) -> Path:
    config = _resolved_config(run_root, base_config)
    confirmation = confirmation_path(run_root, config.profile)
    confirmation_seal = verify_confirmation(confirmation, base_config)
    output = replay_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_replay(output, base_config)
        return output
    guard_budget(run_root, config, "confirmation-replay")
    output.mkdir(parents=True, exist_ok=True)
    designs = sorted((confirmation / "cells").glob("cell_*_design.joblib"))
    replay = _replay_confirmation_cells(
        designs, output / "audits", config, run_root,
        min(workers, config.replay_workers),
    )
    if not replay["all_exact"] or replay["cells"] != confirmation_seal["cells"]:
        raise ValueError("confirmation exact replay failed")
    registration = verify_registration(
        registration_path(run_root, config.profile), base_config
    )
    if registration["sources"] != _source_hashes():
        raise ValueError("source changed during confirmation replay")
    payload = {
        "format": "fep-surprise-25-confirmation-replay-v1",
        "status": "sealed_exact_before_analysis",
        "confirmation_id": confirmation_seal["confirmation_id"],
        **replay,
    }
    payload["replay_id"] = canonical_digest(payload)
    (output / "replay.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(output)
    return output


def verify_replay(path: Path, base_config: Campaign25Config) -> dict[str, Any]:
    confirmation = verify_confirmation(
        confirmation_path(path.parents[1], base_config.profile), base_config
    )
    verify_checksums(path)
    payload = json.loads((path / "replay.json").read_text(encoding="utf-8"))
    identifier = payload.pop("replay_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("replay identifier mismatch")
    payload["replay_id"] = identifier
    if payload["confirmation_id"] != confirmation["confirmation_id"] or not payload["all_exact"]:
        raise ValueError("confirmation replay is not exact")
    return payload


def analyze(run_root: Path, base_config: Campaign25Config) -> Path:
    config = _resolved_config(run_root, base_config)
    registration = verify_registration(
        registration_path(run_root, config.profile), base_config
    )
    screened = verify_screen(screen_path(run_root, config.profile), base_config)
    confirmation = verify_confirmation(
        confirmation_path(run_root, config.profile), base_config
    )
    replay = verify_replay(replay_path(run_root, config.profile), base_config)
    guard_budget(run_root, config, "analysis")
    destination = analysis_path(run_root, config.profile)
    if destination.exists():
        verify_checksums(destination)
        return destination
    validation = verify_validation(
        validation_path(run_root, config.profile), base_config
    )
    cohort = _cohort_integrity(
        confirmation_path(run_root, config.profile), config, int(confirmation["cells"])
    )
    integrity = {
        "validation_all_pass": bool(validation["results"]["all_pass"]),
        "screen_exact_replay": bool(screened["seal"]["replay"]["all_exact"]),
        "screen_selection_complete": bool(screened["selection"]["complete"]),
        "confirmation_exact_replay": bool(replay["all_exact"]),
        "complete_confirmation_artifact_cohort": bool(
            all(value for key, value in cohort.items() if not key.endswith("retained"))
        ),
        "source_tree_matches_registration": bool(registration["sources"] == _source_hashes()),
        "analysis_firewall_intact": bool(not confirmation["analysis_artifacts_present"]),
    }
    with atomic_destination(destination) as output:
        metrics = analyze_confirmation(
            confirmation_path(run_root, config.profile) / "cells",
            config,
            output,
            integrity,
        )
        seal = {
            "format": "fep-surprise-25-analysis-seal-v1",
            "status": "sealed_after_exact_confirmation_replay",
            "registration_id": registration["registration_id"],
            "screen_seal_id": screened["seal"]["screen_seal_id"],
            "confirmation_id": confirmation["confirmation_id"],
            "replay_id": replay["replay_id"],
            "decision": metrics["decision"],
        }
        seal["analysis_id"] = canonical_digest(seal)
        (output / "analysis.json").write_text(
            json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    return destination


def status(run_root: Path, profile: str) -> dict[str, Any]:
    root = profile_path(run_root, profile)
    output: dict[str, Any] = {"profile": profile}
    for name in (
        "validation", "benchmark", "registration", "screen",
        "confirmation", "confirmation_replay", "analysis",
    ):
        path = root / name
        entry: dict[str, Any] = {
            "exists": path.exists(),
            "sealed": (path / "SHA256SUMS").exists(),
        }
        cells = path / "cells"
        if cells.exists():
            entry["screen_cells"] = len(list(cells.glob("screen_*.joblib")))
            entry["design_cells"] = len(list(cells.glob("cell_*_design.joblib")))
            entry["future_cells"] = len(list(cells.glob("cell_*_futures.joblib")))
        audits = path / "audits"
        if not audits.exists():
            audits = path / "replay_audits"
        if audits.exists():
            entry["replay_audits"] = len(list(audits.glob("*.json")))
        output[name] = entry
    try:
        from .config import profile_config
        budget_file = root / "budget_start.json"
        if budget_file.exists():
            output["budget"] = budget_status(run_root, profile_config(profile))
        else:
            output["budget"] = None
    except Exception as error:  # status must remain diagnostic
        output["budget_error"] = str(error)
    benchmark_file = root / "benchmark" / "benchmark.json"
    if benchmark_file.exists():
        value = json.loads(benchmark_file.read_text(encoding="utf-8"))
        output["selected_compute_profile"] = value.get("selected_profile")
        output["selected_per_stratum"] = value.get("selected_per_stratum")
        projection = value.get("projections", {}).get(value.get("selected_profile"), {})
        output["projected_total_seconds"] = projection.get("conservative_total_seconds")
    for label, filename in (
        ("detached_run_status", "experiment25.status"),
        ("detached_run_pid", "experiment25.pid"),
        ("detached_run_session", "experiment25.session"),
        ("detached_run_started", "experiment25.started"),
        ("detached_run_finished", "experiment25.finished"),
    ):
        path = root / filename
        output[label] = path.read_text(encoding="utf-8").strip() if path.exists() else None
    pid = output.get("detached_run_pid")
    try:
        output["detached_run_alive"] = bool(pid and Path(f"/proc/{int(pid)}").exists())
    except (TypeError, ValueError):
        output["detached_run_alive"] = False
    return output
