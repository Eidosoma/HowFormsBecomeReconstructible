from __future__ import annotations

import os
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .analysis import SCENARIOS, analyze_campaign
from .batch import batch_metrics, run_batch
from .blanket import (
    alternative_partition_scan,
    bootstrap_partial_correlation,
    build_blanket_model,
    estimate_blanket_statistics,
    simulate_blanket,
)
from .config import LabConfig
from .integrity import (
    canonical_json_bytes,
    read_json,
    runtime_manifest,
    seal_directory,
    sha256_bytes,
    sha256_file,
    source_manifest,
    verify_seal,
    write_json,
)
from .pymdp_backend import PymdpBackend, dependency_versions
from .seeds import derive_seed
from .simulation import CONTROLLERS
from .validation import validate_lab

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLANKET_INTERVENTIONS = (
    "intact",
    "sensory_lesion",
    "active_lesion",
    "blanket_break",
)


def _source_files() -> list[Path]:
    files = list((PROJECT_ROOT / "fep_lab").glob("*.py"))
    files.append(PROJECT_ROOT / "requirements-fep-lab-lock.txt")
    return sorted(path for path in files if path.is_file())


def profile_root(run_root: Path, profile: str) -> Path:
    return Path(run_root) / profile


def registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "registration.json"


def _resolved_config(run_root: Path, config: LabConfig) -> LabConfig:
    if config.profile != "full":
        return replace(config, selected_scale=config.episodes_per_condition)
    timing_path = Path(run_root) / "full-timing.json"
    if timing_path.is_file():
        timing = read_json(timing_path)
        selected = int(timing["selected_episodes_per_condition"])
    else:
        timing = benchmark_runtime(config)
        selected = int(timing["selected_episodes_per_condition"])
        write_json(timing_path, timing)
    trajectory_mapping = {4_096: 512, 2_048: 256, 1_024: 128}
    return replace(
        config,
        episodes_per_condition=selected,
        blanket_trajectories=trajectory_mapping[selected],
        selected_scale=selected,
    )


def benchmark_runtime(config: LabConfig) -> dict[str, Any]:
    backend = PymdpBackend()
    # Warm compilation separately so the projection reflects repeated cells.
    run_batch("epistemic", "active_inference", backend, 128, 4, 991, 992)
    start = time.perf_counter()
    run_batch("epistemic", "active_inference", backend, 128, 4, 993, 994)
    homeostat_seconds = time.perf_counter() - start
    blanket = build_blanket_model("intact")
    start = time.perf_counter()
    simulate_blanket(blanket, 16, 128, config.blanket_dt, np.random.default_rng(995))
    blanket_seconds = time.perf_counter() - start
    projections: dict[str, float] = {}
    for candidate in (4_096, 2_048, 1_024):
        episode_multiplier = candidate / 128.0
        homeostat_projection = (
            homeostat_seconds
            * episode_multiplier
            * (config.episode_steps / 4.0)
            * len(SCENARIOS)
            * len(CONTROLLERS)
            * 2.0
        )
        blanket_observations = {4_096: 1_048_576, 2_048: 524_288, 1_024: 262_144}[
            candidate
        ]
        blanket_projection = (
            blanket_seconds
            * (blanket_observations / (16.0 * 128.0))
            * len(BLANKET_INTERVENTIONS)
            * 2.0
        )
        projections[str(candidate)] = 1.5 * (
            homeostat_projection + blanket_projection
        ) + 180.0
    eligible = [
        candidate for candidate in (4_096, 2_048, 1_024) if projections[str(candidate)] <= 5_400
    ]
    if not eligible:
        raise RuntimeError(
            "full validation timing projects above 90 minutes even at minimum scale"
        )
    return {
        "benchmark_homeostat_seconds": homeostat_seconds,
        "benchmark_blanket_seconds": blanket_seconds,
        "projections_seconds_including_replay": projections,
        "selected_episodes_per_condition": max(eligible),
        "registration_projection_ceiling_seconds": 5_400,
    }


def register(run_root: Path, config: LabConfig) -> tuple[Path, LabConfig]:
    resolved = _resolved_config(run_root, config)
    path = registration_path(run_root, config.profile)
    manifest = {
        "schema": "fep-lab-registration-v1",
        "config": resolved.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "runtime": runtime_manifest(),
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    if path.is_file():
        existing = read_json(path)
        if existing != manifest:
            raise RuntimeError("existing FEP laboratory registration does not match current source/config")
        return path, resolved
    write_json(path, manifest)
    return path, resolved


def verify_registration(run_root: Path, config: LabConfig) -> LabConfig:
    path = registration_path(run_root, config.profile)
    if not path.is_file():
        raise FileNotFoundError(f"missing registration {path}")
    registered = read_json(path)
    if registered.get("schema") != "fep-lab-registration-v1":
        raise RuntimeError("registration schema mismatch")
    if registered["config"]["profile"] != config.profile:
        raise RuntimeError("registration profile mismatch")
    if registered["config"]["master_seed"] != config.master_seed:
        raise RuntimeError("registration master seed mismatch")
    current_sources = source_manifest(PROJECT_ROOT, _source_files())
    if current_sources != registered["sources"]:
        raise RuntimeError("registered FEP laboratory source has drifted")
    if dependency_versions() != registered["dependencies"]:
        raise RuntimeError("registered FEP laboratory dependencies have drifted")
    resolved = LabConfig(**registered["config"])
    resolved.validate()
    return resolved


def validate_stage(run_root: Path, config: LabConfig) -> dict[str, Any]:
    resolved = verify_registration(run_root, config)
    output = profile_root(run_root, config.profile) / "validation"
    return validate_lab(resolved, output)


def _array_digest(arrays: dict[str, np.ndarray]) -> str:
    digest_parts: list[bytes] = []
    for name in sorted(arrays):
        value = np.ascontiguousarray(arrays[name])
        digest_parts.extend(
            (
                name.encode("utf-8"),
                str(value.shape).encode("ascii"),
                value.dtype.str.encode("ascii"),
                value.tobytes(),
            )
        )
    return sha256_bytes(b"".join(digest_parts))


def _save_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}.npz")
    np.savez(temporary, **arrays)
    temporary.replace(path)


def _cell_complete(path: Path, manifest_path: Path) -> bool:
    if not path.is_file() or not manifest_path.is_file():
        return False
    manifest = read_json(manifest_path)
    if manifest.get("file_sha256") != sha256_file(path):
        return False
    with np.load(path, allow_pickle=False) as data:
        digest = _array_digest({name: data[name] for name in data.files})
    return digest == manifest.get("array_digest")


def _deadline_guard(started: float, config: LabConfig) -> None:
    elapsed = time.monotonic() - started
    if elapsed >= config.graceful_stop_seconds:
        raise TimeoutError(
            f"graceful FEP laboratory stop after {elapsed:.1f}s; rerun to resume"
        )


def _blanket_arrays(
    config: LabConfig, intervention: str
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    model = build_blanket_model(intervention)  # type: ignore[arg-type]
    samples = simulate_blanket(
        model,
        config.blanket_trajectories,
        config.blanket_steps,
        config.blanket_dt,
        np.random.default_rng(
            derive_seed(config.master_seed, "fep_lab.blanket.trajectory", intervention)
        ),
    )
    statistics = estimate_blanket_statistics(samples)
    bootstrap = bootstrap_partial_correlation(
        samples,
        config.bootstrap_repetitions,
        np.random.default_rng(
            derive_seed(config.master_seed, "fep_lab.blanket.bootstrap", intervention)
        ),
    )
    metrics = {
        **statistics,
        "intervention": intervention,
        "population_partial_correlation": model.population_partial_correlation,
        "population_conditional_mutual_information": model.population_conditional_mutual_information,
        "population_precision": model.precision,
        "bootstrap_ci_95": np.quantile(bootstrap, [0.025, 0.975]),
        "alternative_partitions": alternative_partition_scan(
            np.asarray(statistics["covariance"])
        ),
    }
    arrays = {
        "samples": samples,
        "bootstrap_partial_correlation": bootstrap,
        "population_covariance": model.stationary_covariance,
        "population_precision": model.precision,
        "generator": model.generator,
    }
    return arrays, metrics


def _homeostat_arrays(
    config: LabConfig,
    backend: PymdpBackend,
    scenario: str,
    controller: str,
) -> dict[str, np.ndarray]:
    trace = run_batch(
        scenario,
        controller,  # type: ignore[arg-type]
        backend,
        config.episodes_per_condition,
        config.episode_steps,
        derive_seed(config.master_seed, "fep_lab.homeostat.process", scenario),
        derive_seed(
            config.master_seed, "fep_lab.homeostat.agent", scenario, controller
        ),
    )
    arrays = trace.to_arrays()
    for name, values in batch_metrics(trace).items():
        arrays[f"metric_{name}"] = values
    return arrays


def simulate_stage(
    run_root: Path, config: LabConfig, campaign_started: float | None = None
) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    validation_root = root / "validation"
    if not verify_seal(validation_root):
        raise RuntimeError("validated numerical stage is not sealed")
    if not read_json(validation_root / "validation.json")["all_pass"]:
        raise RuntimeError("numerical validation failed; refusing simulation")
    output = root / "simulation"
    if verify_seal(output):
        return output
    started = time.monotonic() if campaign_started is None else campaign_started
    sealed_files: list[str] = []
    blanket_root = output / "blanket"
    for intervention in BLANKET_INTERVENTIONS:
        _deadline_guard(started, resolved)
        data_path = blanket_root / f"{intervention}.npz"
        metrics_path = blanket_root / f"{intervention}.metrics.json"
        manifest_path = blanket_root / f"{intervention}.cell.json"
        if not (_cell_complete(data_path, manifest_path) and metrics_path.is_file()):
            arrays, metrics = _blanket_arrays(resolved, intervention)
            _save_npz(data_path, arrays)
            write_json(metrics_path, metrics)
            write_json(
                manifest_path,
                {
                    "array_digest": _array_digest(arrays),
                    "file_sha256": sha256_file(data_path),
                    "intervention": intervention,
                },
            )
        sealed_files.extend(
            str(path.relative_to(output))
            for path in (data_path, metrics_path, manifest_path)
        )

    backend = PymdpBackend()
    homeostat_root = output / "homeostat"
    for scenario in SCENARIOS:
        for controller in CONTROLLERS:
            _deadline_guard(started, resolved)
            stem = f"{scenario}--{controller}"
            data_path = homeostat_root / f"{stem}.npz"
            manifest_path = homeostat_root / f"{stem}.cell.json"
            if not _cell_complete(data_path, manifest_path):
                arrays = _homeostat_arrays(resolved, backend, scenario, controller)
                _save_npz(data_path, arrays)
                summary = {
                    name.removeprefix("metric_"): float(np.mean(values))
                    for name, values in arrays.items()
                    if name.startswith("metric_")
                }
                write_json(
                    manifest_path,
                    {
                        "array_digest": _array_digest(arrays),
                        "file_sha256": sha256_file(data_path),
                        "scenario": scenario,
                        "controller": controller,
                        "summary": summary,
                    },
                )
            sealed_files.extend(
                str(path.relative_to(output)) for path in (data_path, manifest_path)
            )
    seal_directory(output, sealed_files)
    return output


def replay_stage(
    run_root: Path, config: LabConfig, campaign_started: float | None = None
) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    simulation = root / "simulation"
    if not verify_seal(simulation):
        raise RuntimeError("simulation stage is not sealed")
    output = root / "replay"
    if verify_seal(output):
        return output
    started = time.monotonic() if campaign_started is None else campaign_started
    cells: list[dict[str, Any]] = []
    for intervention in BLANKET_INTERVENTIONS:
        _deadline_guard(started, resolved)
        arrays, _metrics = _blanket_arrays(resolved, intervention)
        expected = read_json(
            simulation / "blanket" / f"{intervention}.cell.json"
        )["array_digest"]
        actual = _array_digest(arrays)
        cells.append(
            {
                "cell": f"blanket:{intervention}",
                "expected": expected,
                "actual": actual,
                "exact": actual == expected,
            }
        )
    backend = PymdpBackend()
    for scenario in SCENARIOS:
        for controller in CONTROLLERS:
            _deadline_guard(started, resolved)
            arrays = _homeostat_arrays(resolved, backend, scenario, controller)
            expected = read_json(
                simulation / "homeostat" / f"{scenario}--{controller}.cell.json"
            )["array_digest"]
            actual = _array_digest(arrays)
            cells.append(
                {
                    "cell": f"homeostat:{scenario}:{controller}",
                    "expected": expected,
                    "actual": actual,
                    "exact": actual == expected,
                }
            )
    result = {
        "profile": config.profile,
        "cells": cells,
        "all_exact": all(cell["exact"] for cell in cells),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "replay.json", result)
    seal_directory(output, ["replay.json"])
    if not result["all_exact"]:
        raise RuntimeError("FEP laboratory exact replay failed")
    return output


def report_stage(run_root: Path, config: LabConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "replay"
    if not verify_seal(replay) or not read_json(replay / "replay.json")["all_exact"]:
        raise RuntimeError("exact replay has not passed")
    output = root / "analysis"
    if verify_seal(output):
        return output
    analyze_campaign(resolved, root, output)
    return output


def run_all(run_root: Path, config: LabConfig) -> Path:
    started = time.monotonic()
    _registration, resolved = register(run_root, config)
    validate_stage(run_root, resolved)
    simulate_stage(run_root, resolved, campaign_started=started)
    if time.monotonic() - started >= resolved.graceful_stop_seconds:
        raise TimeoutError("graceful stop before replay; rerun to resume")
    replay_stage(run_root, resolved, campaign_started=started)
    return report_stage(run_root, resolved)


def status(run_root: Path, profile: str) -> dict[str, Any]:
    root = profile_root(run_root, profile)
    registration = root / "registration.json"
    result: dict[str, Any] = {
        "profile": profile,
        "registered": registration.is_file(),
        "validation_sealed": verify_seal(root / "validation"),
        "simulation_sealed": verify_seal(root / "simulation"),
        "replay_sealed": verify_seal(root / "replay"),
        "analysis_sealed": verify_seal(root / "analysis"),
    }
    if registration.is_file():
        result["registration_id"] = read_json(registration).get("registration_id")
    metrics = root / "analysis" / "metrics.json"
    if metrics.is_file():
        result["verdict"] = read_json(metrics).get("verdict")
    status_path = root / "fep-lab.status"
    pid_path = root / "fep-lab.pid"
    if status_path.is_file():
        result["detached_status"] = status_path.read_text().strip()
    if pid_path.is_file():
        raw = pid_path.read_text().strip()
        result["detached_pid"] = raw
        try:
            os.kill(int(raw), 0)
            result["detached_alive"] = True
        except (ValueError, ProcessLookupError, PermissionError):
            result["detached_alive"] = False
    return result
