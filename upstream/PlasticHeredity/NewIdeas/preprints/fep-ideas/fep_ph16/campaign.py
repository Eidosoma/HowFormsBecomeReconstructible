from __future__ import annotations

import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from fep_lab.integrity import (
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
from fep_lab.pymdp_backend import dependency_versions
from fep_ph1.config import GardConfig
from fep_ph15.models import (
    load_model as load_categorical_model,
    model_digest as categorical_model_digest,
    save_model as save_categorical_model,
)

from .analysis import analyze_atlas
from .causal_model import (
    fit_ensemble,
    model_arrays,
    model_digest,
    model_summary,
)
from .config import (
    MECHANISM_KEYS,
    RIDGE_GRID,
    SCALE_LADDER,
    ExperimentConfig,
    profile_config,
    with_selected_scale,
)
from .data import (
    conditions_for_mechanism,
    development_cell,
    load_conditions,
    thresholds_and_categorical_model,
    training_data_from_cells,
)
from .types import CellSpec, ConditionSpec, ObservationThresholds
from .validation import validate_experiment
from .worker import (
    categorical_model_path,
    generate_evaluation_cell,
    mechanism_model_paths,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_REGISTRATION_SCHEMA = "fep-ph16-development-registration-v1"
EVALUATION_REGISTRATION_SCHEMA = "fep-ph16-evaluation-registration-v1"


def profile_root(run_root: Path, profile: str) -> Path:
    return Path(run_root) / profile


def _source_files() -> list[Path]:
    paths = list((PROJECT_ROOT / "fep_ph16").glob("*.py"))
    paths.extend((PROJECT_ROOT / "fep_ph15").glob("*.py"))
    paths.extend((PROJECT_ROOT / "fep_ph1").glob("*.py"))
    paths.extend(
        PROJECT_ROOT / "fep_lab" / name
        for name in (
            "integrity.py",
            "pymdp_backend.py",
            "reference.py",
            "seeds.py",
            "types.py",
        )
    )
    for name in (
        "EXPERIMENT_FEP_PH15_FINAL_REPORT.md",
        "EXPERIMENT_FEP_PH16_PROTOCOL.md",
        "requirements-fep-lab-lock.txt",
        "scripts/run_fep_ph16_campaign.sh",
        "scripts/run_fep_ph16_detached.sh",
        "scripts/status_fep_ph16.sh",
        "scripts/control_fep_ph16.sh",
    ):
        path = PROJECT_ROOT / name
        if path.is_file():
            paths.append(path)
    return sorted(path for path in paths if path.is_file())


def _source_digest() -> str:
    return sha256_bytes(
        canonical_json_bytes(source_manifest(PROJECT_ROOT, _source_files()))
    )


def _registered_sources_current(registration: Path) -> bool:
    sources = read_json(registration).get("sources", {})
    if not sources:
        return False
    return all(
        (PROJECT_ROOT / relative).is_file()
        and sha256_file(PROJECT_ROOT / relative) == expected
        for relative, expected in sources.items()
    )


def _prior_dependencies() -> dict[str, str]:
    stage0 = PROJECT_ROOT / "runs-fep-lab" / "full"
    experiment1 = PROJECT_ROOT / "runs-fep-ph1" / "full"
    experiment15 = PROJECT_ROOT / "runs-fep-ph15" / "full"
    required = {
        "stage0_metrics": stage0 / "analysis" / "metrics.json",
        "stage0_analysis_seal": stage0 / "analysis" / "seal.json",
        "stage0_replay_seal": stage0 / "replay" / "seal.json",
        "fep_ph1_registration": experiment1 / "registration.json",
        "fep_ph1_replay_seal": experiment1 / "replay" / "seal.json",
        "fep_ph1_amendment_seal": experiment1 / "amendment-1" / "seal.json",
        "fep_ph1_amended_analysis_seal": experiment1
        / "analysis-amendment-1"
        / "seal.json",
        "fep_ph1_final_report": PROJECT_ROOT / "EXPERIMENT_FEP_PH1_FINAL_REPORT.md",
        "fep_ph15_screen_registration": experiment15 / "screen-registration.json",
        "fep_ph15_screen_seal": experiment15 / "screen" / "seal.json",
        "fep_ph15_screen_replay_seal": experiment15
        / "screen-replay"
        / "seal.json",
        "fep_ph15_registration": experiment15 / "registration.json",
        "fep_ph15_replay_seal": experiment15 / "replay" / "seal.json",
        "fep_ph15_analysis_seal": experiment15 / "analysis" / "seal.json",
        "fep_ph15_metrics": experiment15 / "analysis" / "metrics.json",
        "fep_ph15_final_report": PROJECT_ROOT / "EXPERIMENT_FEP_PH15_FINAL_REPORT.md",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing sealed prerequisite artifacts: {missing}")
    for label, directory in (
        ("Stage 0 analysis", stage0 / "analysis"),
        ("Stage 0 replay", stage0 / "replay"),
        ("FEP-PH1 replay", experiment1 / "replay"),
        ("FEP-PH1 amendment", experiment1 / "amendment-1"),
        ("FEP-PH1 amended analysis", experiment1 / "analysis-amendment-1"),
        ("FEP-PH1.5 screen", experiment15 / "screen"),
        ("FEP-PH1.5 screen replay", experiment15 / "screen-replay"),
        ("FEP-PH1.5 replay", experiment15 / "replay"),
        ("FEP-PH1.5 analysis", experiment15 / "analysis"),
    ):
        if not verify_seal(directory):
            raise RuntimeError(f"{label} dependency seal does not verify")
    if read_json(stage0 / "analysis" / "metrics.json").get("verdict") != "VALIDATION_PASS":
        raise RuntimeError("Stage 0 known-positive dependency is invalid")
    if read_json(experiment1 / "replay" / "replay.json").get("all_exact") is not True:
        raise RuntimeError("FEP-PH1 replay dependency is not exact")
    if read_json(experiment15 / "screen-replay" / "replay.json").get("all_exact") is not True:
        raise RuntimeError("FEP-PH1.5 screen replay dependency is not exact")
    if read_json(experiment15 / "replay" / "replay.json").get("all_exact") is not True:
        raise RuntimeError("FEP-PH1.5 evaluation replay dependency is not exact")
    decision = read_json(experiment15 / "analysis" / "metrics.json").get("decision", {})
    if decision.get("integrity_verdict") != "VALID":
        raise RuntimeError("FEP-PH1.5 integrity dependency is not valid")
    if not _registered_sources_current(experiment15 / "registration.json"):
        raise RuntimeError("FEP-PH1.5 registered source has drifted")
    return {name: sha256_file(path) for name, path in sorted(required.items())}


def _array_digest(arrays: dict[str, np.ndarray]) -> str:
    chunks: list[bytes] = []
    for name in sorted(arrays):
        value = np.ascontiguousarray(arrays[name])
        chunks.extend(
            (
                name.encode(),
                str(value.shape).encode(),
                value.dtype.str.encode(),
                value.tobytes(),
            )
        )
    return sha256_bytes(b"".join(chunks))


def _save_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}.npz")
    np.savez_compressed(temporary, **arrays)
    temporary.replace(path)


def _cell_complete(data: Path, metadata: Path) -> bool:
    if not data.is_file() or not metadata.is_file():
        return False
    payload = read_json(metadata)
    if payload.get("file_sha256") != sha256_file(data):
        return False
    with np.load(data, allow_pickle=False) as archive:
        digest = _array_digest({name: archive[name] for name in archive.files})
    return digest == payload.get("array_digest")


def _clock_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "clock.json"


def ensure_clock(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    path = _clock_path(run_root, config.profile)
    if path.is_file():
        return read_json(path)
    now = time.time()
    payload = {
        "schema": "fep-ph16-wall-clock-v1",
        "started_epoch": now,
        "started_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "hard_wall_time_seconds": config.wall_time_limit_seconds,
        "pauses_and_restarts_consume_budget": True,
    }
    write_json(path, payload)
    return payload


def elapsed_seconds(run_root: Path, config: ExperimentConfig) -> float:
    clock = ensure_clock(run_root, config)
    return max(0.0, time.time() - float(clock["started_epoch"]))


def _deadline(run_root: Path, config: ExperimentConfig) -> None:
    elapsed = elapsed_seconds(run_root, config)
    if elapsed >= config.graceful_stop_seconds:
        raise TimeoutError(
            f"TIME_BUDGET_EXHAUSTED_NO_VERDICT after {elapsed:.1f}s; "
            "the four-hour clock includes pauses and restarts"
        )


def _map_tasks(function: Any, arguments: list[Any], workers: int) -> Iterable[Any]:
    if workers <= 1:
        yield from map(function, arguments)
        return
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        yield from executor.map(function, arguments, chunksize=1)


def _screen_root() -> Path:
    return PROJECT_ROOT / "runs-fep-ph15" / "full" / "screen"


def validate_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    ensure_clock(run_root, config)
    output = profile_root(run_root, config.profile) / "validation"
    digest = _source_digest()
    if verify_seal(output):
        payload = read_json(output / "validation.json")
        if payload.get("source_digest") != digest:
            raise RuntimeError("sealed FEP-PH1.6 validation belongs to different source")
        return payload
    _prior_dependencies()
    return validate_experiment(config, _screen_root(), output, digest)


def development_registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "development-registration.json"


def develop_register(run_root: Path, config: ExperimentConfig) -> Path:
    validation = validate_stage(run_root, config)
    if validation.get("all_pass") is not True:
        raise RuntimeError("validation failed; refusing development registration")
    manifest: dict[str, Any] = {
        "schema": DEVELOPMENT_REGISTRATION_SCHEMA,
        "profile": config.profile,
        "master_seed": config.master_seed,
        "development_contract": {
            "mechanisms": list(MECHANISM_KEYS),
            "conditions": 24,
            "matrices": config.development_matrices,
            "episodes": config.development_episodes,
            "steps": config.development_steps,
            "actions": [0, 1, 2, 3],
            "balanced_action_cycles": True,
            "causal_models": ["coarse", "rich_clr100"],
            "ensemble_members": config.ensemble_members,
            "ridge_grid": list(RIDGE_GRID),
            "evaluation_data_hidden": True,
        },
        "scientific_status": "EXPLORATORY_ONLY_NO_GLOBAL_CLASSIFIER",
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "prior_dependencies": _prior_dependencies(),
        "runtime": runtime_manifest(),
    }
    manifest["development_registration_id"] = sha256_bytes(
        canonical_json_bytes(manifest)
    )
    path = development_registration_path(run_root, config.profile)
    if path.is_file():
        if read_json(path) != manifest:
            raise RuntimeError("existing development registration differs from contract")
        return path
    write_json(path, manifest)
    return path


def verify_development_registration(
    run_root: Path, config: ExperimentConfig
) -> dict[str, Any]:
    path = development_registration_path(run_root, config.profile)
    if not path.is_file():
        raise FileNotFoundError(f"missing development registration {path}")
    payload = read_json(path)
    if payload.get("schema") != DEVELOPMENT_REGISTRATION_SCHEMA:
        raise RuntimeError("development registration schema mismatch")
    if payload.get("sources") != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("development-registered source has drifted")
    if payload.get("dependencies") != dependency_versions():
        raise RuntimeError("development-registered dependencies have drifted")
    if payload.get("prior_dependencies") != _prior_dependencies():
        raise RuntimeError("development-registered prior artifacts have drifted")
    return payload


def _development_paths(output: Path, condition: ConditionSpec) -> tuple[Path, Path]:
    return (
        output / "cells" / f"{condition.key}.npz",
        output / "cells" / f"{condition.key}.json",
    )


def _save_development_task(
    argument: tuple[ExperimentConfig, ConditionSpec, Path]
) -> tuple[str, str]:
    config, condition, output = argument
    data, metadata = _development_paths(output, condition)
    if _cell_complete(data, metadata):
        return str(data), str(metadata)
    arrays, payload = development_cell(config, condition)
    _save_npz(data, arrays)
    payload.update(
        {
            "array_digest": _array_digest(arrays),
            "file_sha256": sha256_file(data),
        }
    )
    write_json(metadata, payload)
    return str(data), str(metadata)


def development_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_development_registration(run_root, config)
    output = profile_root(run_root, config.profile) / "development"
    if verify_seal(output):
        return output
    _deadline(run_root, config)
    conditions = load_conditions(_screen_root())
    arguments = [(config, condition, output) for condition in conditions]
    sealed: list[str] = []
    for index, paths in enumerate(
        _map_tasks(_save_development_task, arguments, config.workers), start=1
    ):
        _deadline(run_root, config)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        print(f"[development] conditions {index}/{len(arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _replay_development_task(
    argument: tuple[ExperimentConfig, ConditionSpec, Path]
) -> dict[str, Any]:
    config, condition, development = argument
    _data, metadata = _development_paths(development, condition)
    expected = read_json(metadata)
    arrays, payload = development_cell(config, condition)
    return {
        "condition": condition.key,
        "array_exact": _array_digest(arrays) == expected.get("array_digest"),
        "metadata_exact": payload == {key: expected[key] for key in payload},
    }


def replay_development_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_development_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    development = root / "development"
    if not verify_seal(development):
        raise RuntimeError("development corpus is not sealed")
    output = root / "development-replay"
    if verify_seal(output):
        return output
    arguments = [
        (config, condition, development)
        for condition in load_conditions(_screen_root())
    ]
    results = []
    for index, result in enumerate(
        _map_tasks(_replay_development_task, arguments, config.workers), start=1
    ):
        _deadline(run_root, config)
        results.append(result)
        print(f"[development-replay] conditions {index}/{len(arguments)}", flush=True)
    exact = all(value["array_exact"] and value["metadata_exact"] for value in results)
    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "replay.json",
        {"schema": "fep-ph16-development-replay-v1", "cells": results, "all_exact": exact},
    )
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError("FEP-PH1.6 development exact replay failed")
    return output


def _causal_metadata_path(fit_root: Path, mechanism: str, rich: bool) -> Path:
    label = "rich" if rich else "coarse"
    return fit_root / "causal" / f"{mechanism}--{label}.json"


def _categorical_metadata_path(fit_root: Path, condition: ConditionSpec) -> Path:
    return fit_root / "categorical" / f"{condition.key}.json"


def _fit_causal_task(
    argument: tuple[ExperimentConfig, str, tuple[Path, ...], Path]
) -> tuple[str, ...]:
    config, mechanism, paths, output = argument
    coarse_path, rich_path = mechanism_model_paths(output, mechanism)
    outputs: list[str] = []
    data = training_data_from_cells(paths)
    for rich, path in ((False, coarse_path), (True, rich_path)):
        metadata = _causal_metadata_path(output, mechanism, rich)
        if not _cell_complete(path, metadata):
            model = fit_ensemble(
                data,
                rich=rich,
                members=config.ensemble_members,
                ridge_grid=RIDGE_GRID,
            )
            arrays = model_arrays(model)
            _save_npz(path, arrays)
            write_json(
                metadata,
                {
                    "schema": "fep-ph16-causal-model-v1",
                    "mechanism": mechanism,
                    "model": "rich" if rich else "coarse",
                    "training_rows": int(len(data.actions)),
                    "summary": model_summary(model),
                    "array_digest": _array_digest(arrays),
                    "file_sha256": sha256_file(path),
                },
            )
        outputs.extend((str(path), str(metadata)))
    return tuple(outputs)


def _fit_categorical_task(
    argument: tuple[ExperimentConfig, ConditionSpec, Path, Path]
) -> tuple[str, str]:
    config, condition, development, output = argument
    path = categorical_model_path(output, condition)
    metadata = _categorical_metadata_path(output, condition)
    if _cell_complete(path, metadata):
        return str(path), str(metadata)
    development_path, _development_metadata = _development_paths(development, condition)
    thresholds, counts, model, summary = thresholds_and_categorical_model(
        config, development_path
    )
    save_categorical_model(path, model, counts)
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    write_json(
        metadata,
        {
            "schema": "fep-ph16-categorical-reference-model-v1",
            "condition": condition.key,
            "thresholds": {
                "alignment": list(thresholds.alignment),
                "growth": list(thresholds.growth),
            },
            "model_digest": categorical_model_digest(model),
            "summary": summary,
            "array_digest": _array_digest(arrays),
            "file_sha256": sha256_file(path),
        },
    )
    return str(path), str(metadata)


def fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_development_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "development-replay"
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("exact development replay must pass before fitting")
    development = root / "development"
    output = root / "fit"
    if verify_seal(output):
        return output
    conditions = load_conditions(_screen_root())
    causal_arguments = []
    for mechanism in MECHANISM_KEYS:
        condition_values = conditions_for_mechanism(conditions, mechanism)
        paths = tuple(_development_paths(development, value)[0] for value in condition_values)
        causal_arguments.append((config, mechanism, paths, output))
    sealed: list[str] = []
    for index, paths in enumerate(
        _map_tasks(_fit_causal_task, causal_arguments, config.workers), start=1
    ):
        _deadline(run_root, config)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        print(f"[fit-causal] mechanisms {index}/{len(causal_arguments)}", flush=True)
    categorical_arguments = [
        (config, condition, development, output) for condition in conditions
    ]
    for index, paths in enumerate(
        _map_tasks(_fit_categorical_task, categorical_arguments, config.workers), start=1
    ):
        _deadline(run_root, config)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        print(f"[fit-categorical] conditions {index}/{len(categorical_arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _replay_causal_task(
    argument: tuple[ExperimentConfig, str, tuple[Path, ...], Path]
) -> dict[str, Any]:
    config, mechanism, paths, fit_root = argument
    data = training_data_from_cells(paths)
    results = []
    for rich in (False, True):
        expected = read_json(_causal_metadata_path(fit_root, mechanism, rich))
        model = fit_ensemble(
            data,
            rich=rich,
            members=config.ensemble_members,
            ridge_grid=RIDGE_GRID,
        )
        results.append(
            {
                "model": "rich" if rich else "coarse",
                "model_exact": model_digest(model) == expected["summary"]["digest"],
                "summary_exact": model_summary(model) == expected["summary"],
            }
        )
    return {"mechanism": mechanism, "models": results}


def _replay_categorical_task(
    argument: tuple[ExperimentConfig, ConditionSpec, Path, Path]
) -> dict[str, Any]:
    config, condition, development, fit_root = argument
    expected = read_json(_categorical_metadata_path(fit_root, condition))
    development_path, _metadata = _development_paths(development, condition)
    thresholds, _counts, model, summary = thresholds_and_categorical_model(
        config, development_path
    )
    return {
        "condition": condition.key,
        "model_exact": categorical_model_digest(model) == expected["model_digest"],
        "threshold_exact": (
            list(thresholds.alignment) == expected["thresholds"]["alignment"]
            and list(thresholds.growth) == expected["thresholds"]["growth"]
        ),
        "summary_exact": summary == expected["summary"],
    }


def replay_fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_development_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    fit_root = root / "fit"
    if not verify_seal(fit_root):
        raise RuntimeError("fit stage is not sealed")
    output = root / "fit-replay"
    if verify_seal(output):
        return output
    development = root / "development"
    conditions = load_conditions(_screen_root())
    causal_arguments = []
    for mechanism in MECHANISM_KEYS:
        paths = tuple(
            _development_paths(development, condition)[0]
            for condition in conditions_for_mechanism(conditions, mechanism)
        )
        causal_arguments.append((config, mechanism, paths, fit_root))
    causal_results = []
    for index, result in enumerate(
        _map_tasks(_replay_causal_task, causal_arguments, config.workers), start=1
    ):
        _deadline(run_root, config)
        causal_results.append(result)
        print(f"[fit-replay-causal] mechanisms {index}/{len(causal_arguments)}", flush=True)
    categorical_arguments = [
        (config, condition, development, fit_root) for condition in conditions
    ]
    categorical_results = []
    for index, result in enumerate(
        _map_tasks(_replay_categorical_task, categorical_arguments, config.workers),
        start=1,
    ):
        _deadline(run_root, config)
        categorical_results.append(result)
        print(
            f"[fit-replay-categorical] conditions {index}/{len(categorical_arguments)}",
            flush=True,
        )
    exact = all(
        all(model["model_exact"] and model["summary_exact"] for model in result["models"])
        for result in causal_results
    ) and all(
        result["model_exact"]
        and result["threshold_exact"]
        and result["summary_exact"]
        for result in categorical_results
    )
    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "replay.json",
        {
            "schema": "fep-ph16-fit-replay-v1",
            "causal": causal_results,
            "categorical": categorical_results,
            "all_exact": exact,
        },
    )
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError("FEP-PH1.6 fitted-model exact replay failed")
    return output


def _thresholds(fit_root: Path, condition: ConditionSpec) -> ObservationThresholds:
    payload = read_json(_categorical_metadata_path(fit_root, condition))
    return ObservationThresholds(
        tuple(float(value) for value in payload["thresholds"]["alignment"]),
        tuple(float(value) for value in payload["thresholds"]["growth"]),
    )  # type: ignore[arg-type]


def benchmark_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    verify_development_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    fit_replay = root / "fit-replay"
    if not verify_seal(fit_replay) or read_json(fit_replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("fitted-model replay must be exact before benchmarking")
    output = root / "benchmark"
    if verify_seal(output):
        payload = read_json(output / "benchmark.json")
        if payload.get("source_digest") != _source_digest():
            raise RuntimeError("sealed benchmark belongs to different source")
        return payload
    fit_root = root / "fit"
    condition = load_conditions(_screen_root())[0]
    timing_master_seed = sha256_bytes(
        f"{config.master_seed}.fep_ph16.disposable_timing".encode("utf-8")
    )
    short = replace(
        config,
        master_seed=timing_master_seed,
        branches=1,
        horizon=min(8, config.horizon),
        calibration_episodes=1,
        calibration_steps=min(4, config.calibration_steps),
    )
    timings = []
    for _repetition in range(3):
        started = time.perf_counter()
        generate_evaluation_cell(
            short,
            CellSpec(0, condition),
            fit_root,
            _thresholds(fit_root, condition),
        )
        timings.append(time.perf_counter() - started)
    measured = float(np.median(timings))
    horizon_scaled_cell_seconds = (
        measured
        * config.horizon
        / short.horizon
        * config.branches
        / short.branches
    )
    scales = SCALE_LADDER if config.profile == "full" else (config.evaluation_matrices,)
    elapsed = elapsed_seconds(run_root, config)
    projections: dict[str, dict[str, float]] = {}
    for scale in scales:
        cell_count = int(scale) * 24
        ideal_parallel = (
            2.0 * cell_count * horizon_scaled_cell_seconds / max(1, config.workers)
        )
        fixed = 300.0 if config.profile == "full" else 90.0 if config.profile == "quick" else 30.0
        remaining = 1.75 * ideal_parallel + fixed
        projections[str(scale)] = {
            "evaluation_cells": cell_count,
            "remaining_seconds": remaining,
            "total_from_clock_start_seconds": elapsed + remaining,
        }
    eligible = [
        scale
        for scale in scales
        if projections[str(scale)]["total_from_clock_start_seconds"]
        <= config.registration_projection_ceiling_seconds
    ]
    selected_scale = max(eligible) if eligible else None
    result = {
        "schema": "fep-ph16-benchmark-v1",
        "profile": config.profile,
        "benchmark_condition": condition.key,
        "benchmark_seed_domain": "disposable_timing_not_development_calibration_or_evaluation",
        "benchmark_master_seed": timing_master_seed,
        "short_horizon": short.horizon,
        "short_branches": short.branches,
        "full_horizon": config.horizon,
        "full_branches": config.branches,
        "whole_cell_seconds_samples": timings,
        "median_whole_cell_seconds": measured,
        "horizon_scaled_cell_seconds": horizon_scaled_cell_seconds,
        "controllers_per_cell": 10,
        "workers": config.workers,
        "elapsed_before_benchmark_seconds": elapsed,
        "projections": projections,
        "registration_eligible": selected_scale is not None,
        "selected_evaluation_matrices": selected_scale,
        "registration_projection_ceiling_seconds": config.registration_projection_ceiling_seconds,
        "hard_wall_time_seconds": config.wall_time_limit_seconds,
        "source_digest": _source_digest(),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "benchmark.json", result)
    seal_directory(output, ["benchmark.json"])
    if selected_scale is None:
        minimum = min(scales)
        raise RuntimeError(
            f"minimum {minimum}-matrix atlas projects beyond the four-hour registration contract"
        )
    return result


def registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "registration.json"


def _development_dependencies(run_root: Path, profile: str) -> dict[str, str]:
    root = profile_root(run_root, profile)
    paths = {
        "development_registration": root / "development-registration.json",
        "development_seal": root / "development" / "seal.json",
        "development_replay_seal": root / "development-replay" / "seal.json",
        "fit_seal": root / "fit" / "seal.json",
        "fit_replay_seal": root / "fit-replay" / "seal.json",
        "benchmark_seal": root / "benchmark" / "seal.json",
    }
    if any(not path.is_file() for path in paths.values()):
        raise RuntimeError("development/model/benchmark dependency set is incomplete")
    for name in ("development", "development-replay", "fit", "fit-replay", "benchmark"):
        if not verify_seal(root / name):
            raise RuntimeError(f"{name} dependency seal does not verify")
    return {name: sha256_file(path) for name, path in paths.items()}


def register(run_root: Path, config: ExperimentConfig) -> tuple[Path, ExperimentConfig]:
    benchmark = benchmark_stage(run_root, config)
    if benchmark.get("registration_eligible") is not True:
        raise RuntimeError("sealed timing benchmark refused evaluation registration")
    scale = int(benchmark["selected_evaluation_matrices"])
    resolved = with_selected_scale(config, scale)
    elapsed = elapsed_seconds(run_root, resolved)
    projected = float(benchmark["projections"][str(scale)]["remaining_seconds"])
    if elapsed + projected > resolved.registration_projection_ceiling_seconds:
        raise RuntimeError(
            "elapsed clock plus projected work passed the evaluation registration ceiling"
        )
    manifest: dict[str, Any] = {
        "schema": EVALUATION_REGISTRATION_SCHEMA,
        "config": resolved.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "runtime": runtime_manifest(),
        "prior_dependencies": _prior_dependencies(),
        "development_dependencies": _development_dependencies(
            run_root, config.profile
        ),
        "scientific_status": "EXPLORATORY_ONLY_NO_GLOBAL_CLASSIFIER",
        "primary_outcome": "inherited_completion_fraction",
        "controller_ladder": {
            "learned_agent_access": "blanket_limited",
            "diagnostic_oracle_access": "full_state_isolated_planning_stream_only",
            "f12_and_strict8": "held_out_descriptive_only",
        },
        "clock": read_json(_clock_path(run_root, config.profile)),
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = registration_path(run_root, config.profile)
    if path.is_file():
        if read_json(path) != manifest:
            raise RuntimeError("existing evaluation registration differs from contract")
        return path, resolved
    write_json(path, manifest)
    return path, resolved


def _config_from_manifest(payload: dict[str, Any]) -> ExperimentConfig:
    allowed = {field.name for field in fields(ExperimentConfig)}
    values = {key: value for key, value in payload["config"].items() if key in allowed}
    if isinstance(values.get("gard"), dict):
        values["gard"] = GardConfig(**values["gard"])
    config = ExperimentConfig(**values)
    config.validate()
    return config


def verify_registration(run_root: Path, config: ExperimentConfig) -> ExperimentConfig:
    path = registration_path(run_root, config.profile)
    if not path.is_file():
        raise FileNotFoundError(f"missing evaluation registration {path}")
    payload = read_json(path)
    if payload.get("schema") != EVALUATION_REGISTRATION_SCHEMA:
        raise RuntimeError("evaluation registration schema mismatch")
    if payload.get("sources") != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("evaluation-registered source has drifted")
    if payload.get("dependencies") != dependency_versions():
        raise RuntimeError("evaluation-registered dependencies have drifted")
    if payload.get("prior_dependencies") != _prior_dependencies():
        raise RuntimeError("evaluation-registered prior artifacts have drifted")
    if payload.get("development_dependencies") != _development_dependencies(
        run_root, config.profile
    ):
        raise RuntimeError("registered development dependency has drifted")
    return _config_from_manifest(payload)


def _evaluation_paths(output: Path, cell: CellSpec) -> tuple[Path, Path]:
    return (
        output / "cells" / f"{cell.stem}.npz",
        output / "cells" / f"{cell.stem}.json",
    )


def _save_evaluation_task(
    argument: tuple[
        ExperimentConfig,
        CellSpec,
        Path,
        ObservationThresholds,
        Path,
    ]
) -> tuple[str, str]:
    config, cell, fit_root, thresholds, output = argument
    data, metadata = _evaluation_paths(output, cell)
    if _cell_complete(data, metadata):
        return str(data), str(metadata)
    arrays, payload = generate_evaluation_cell(config, cell, fit_root, thresholds)
    _save_npz(data, arrays)
    payload.update(
        {"array_digest": _array_digest(arrays), "file_sha256": sha256_file(data)}
    )
    write_json(metadata, payload)
    return str(data), str(metadata)


def simulate_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    fit_root = root / "fit"
    if not verify_seal(fit_root):
        raise RuntimeError("fit stage is not sealed")
    output = root / "simulation"
    if verify_seal(output):
        return output
    arguments = []
    conditions = load_conditions(_screen_root())
    for matrix_id in range(resolved.evaluation_matrices):
        for condition in conditions:
            cell = CellSpec(matrix_id, condition)
            arguments.append(
                (resolved, cell, fit_root, _thresholds(fit_root, condition), output)
            )
    sealed: list[str] = []
    for index, paths in enumerate(
        _map_tasks(_save_evaluation_task, arguments, resolved.workers), start=1
    ):
        _deadline(run_root, resolved)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        if index % max(1, len(arguments) // 50) == 0 or index == len(arguments):
            print(f"[simulation] cells {index}/{len(arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _replay_evaluation_task(
    argument: tuple[
        ExperimentConfig,
        CellSpec,
        Path,
        ObservationThresholds,
        Path,
    ]
) -> dict[str, Any]:
    config, cell, fit_root, thresholds, simulation = argument
    _data, metadata = _evaluation_paths(simulation, cell)
    expected = read_json(metadata)
    arrays, payload = generate_evaluation_cell(config, cell, fit_root, thresholds)
    return {
        "stem": cell.stem,
        "array_exact": _array_digest(arrays) == expected["array_digest"],
        "metadata_exact": payload == {key: expected[key] for key in payload},
    }


def replay_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    simulation = root / "simulation"
    if not verify_seal(simulation):
        raise RuntimeError("simulation is not sealed")
    output = root / "replay"
    if verify_seal(output):
        return output
    fit_root = root / "fit"
    arguments = []
    conditions = load_conditions(_screen_root())
    for matrix_id in range(resolved.evaluation_matrices):
        for condition in conditions:
            cell = CellSpec(matrix_id, condition)
            arguments.append(
                (resolved, cell, fit_root, _thresholds(fit_root, condition), simulation)
            )
    results = []
    for index, result in enumerate(
        _map_tasks(_replay_evaluation_task, arguments, resolved.workers), start=1
    ):
        _deadline(run_root, resolved)
        results.append(result)
        if index % max(1, len(arguments) // 50) == 0 or index == len(arguments):
            print(f"[evaluation-replay] cells {index}/{len(arguments)}", flush=True)
    exact = all(value["array_exact"] and value["metadata_exact"] for value in results)
    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "replay.json",
        {"schema": "fep-ph16-evaluation-replay-v1", "cells": results, "all_exact": exact},
    )
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError("FEP-PH1.6 exact evaluation replay failed")
    return output


def analyze_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "replay"
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("exact evaluation replay must pass before analysis")
    output = root / "analysis"
    if verify_seal(output):
        return output
    _deadline(run_root, resolved)
    analyze_atlas(resolved, root / "simulation", root / "fit", output)
    return output


def run_all(run_root: Path, config: ExperimentConfig) -> Path:
    ensure_clock(run_root, config)
    validate_stage(run_root, config)
    develop_register(run_root, config)
    development_stage(run_root, config)
    replay_development_stage(run_root, config)
    fit_stage(run_root, config)
    replay_fit_stage(run_root, config)
    benchmark_stage(run_root, config)
    _path, resolved = register(run_root, config)
    simulate_stage(run_root, resolved)
    replay_stage(run_root, resolved)
    return analyze_stage(run_root, resolved)


def status(run_root: Path, profile: str) -> dict[str, Any]:
    root = profile_root(run_root, profile)
    config = profile_config(profile)

    def seal_present(path: Path) -> bool:
        seal = path / "seal.json"
        if not seal.is_file():
            return False
        try:
            return bool(read_json(seal).get("files"))
        except (OSError, ValueError):
            return False

    stages = {
        "validation": seal_present(root / "validation"),
        "development_registered": (root / "development-registration.json").is_file(),
        "development": seal_present(root / "development"),
        "development_replay": seal_present(root / "development-replay"),
        "fit": seal_present(root / "fit"),
        "fit_replay": seal_present(root / "fit-replay"),
        "benchmark": seal_present(root / "benchmark"),
        "registered": (root / "registration.json").is_file(),
        "simulation": seal_present(root / "simulation"),
        "replay": seal_present(root / "replay"),
        "analysis": seal_present(root / "analysis"),
    }
    output: dict[str, Any] = {"profile": profile, **stages}
    ordered = (
        ("validation", "validation"),
        ("development_registered", "development-registration"),
        ("development", "development"),
        ("development_replay", "development-replay"),
        ("fit", "fit"),
        ("fit_replay", "fit-replay"),
        ("benchmark", "benchmark"),
        ("registered", "evaluation-registration"),
        ("simulation", "simulation"),
        ("replay", "evaluation-replay"),
        ("analysis", "analysis"),
    )
    output["current_stage"] = next(
        (label for key, label in ordered if not stages[key]), "complete"
    )
    if (root / "clock.json").is_file():
        elapsed = elapsed_seconds(run_root, config)
        output.update(
            {
                "elapsed_seconds": elapsed,
                "hard_remaining_seconds": max(
                    0.0, config.wall_time_limit_seconds - elapsed
                ),
                "time_budget_state": (
                    "TIME_BUDGET_EXHAUSTED_NO_VERDICT"
                    if elapsed >= config.wall_time_limit_seconds and not stages["analysis"]
                    else "complete" if stages["analysis"] else "within_budget"
                ),
            }
        )
    if stages["development"]:
        output["development_cells_present"] = len(
            list((root / "development" / "cells").glob("*.json"))
        )
        output["expected_development_cells"] = 24
    if stages["registered"]:
        registration = read_json(root / "registration.json")
        output["registration_id"] = registration["registration_id"]
        output["registered_source_current"] = registration.get("sources") == source_manifest(
            PROJECT_ROOT, _source_files()
        )
        scale = int(registration["config"]["evaluation_matrices"])
        output["selected_evaluation_matrices"] = scale
        output["expected_evaluation_cells"] = scale * 24
        output["simulation_cells_present"] = len(
            list((root / "simulation" / "cells").glob("*.json"))
        )
        replay_payload = (
            read_json(root / "replay" / "replay.json")
            if (root / "replay" / "replay.json").is_file()
            else {}
        )
        output["replay_cells_recorded"] = len(replay_payload.get("cells", []))
    benchmark_path = root / "benchmark" / "benchmark.json"
    if benchmark_path.is_file() and "elapsed_seconds" in output:
        benchmark = read_json(benchmark_path)
        selected = benchmark.get("selected_evaluation_matrices")
        output["benchmark_registration_eligible"] = benchmark.get(
            "registration_eligible"
        )
        if selected is not None:
            scale = str(selected)
            total = float(
                benchmark["projections"][scale]["total_from_clock_start_seconds"]
            )
            eta = 0.0 if stages["analysis"] else max(
                0.0, total - float(output["elapsed_seconds"])
            )
            output["projected_total_seconds"] = total
            output["eta_seconds"] = eta
            output["eta_utc"] = datetime.fromtimestamp(
                time.time() + eta, timezone.utc
            ).isoformat()
    if stages["analysis"]:
        output.update(read_json(root / "analysis" / "metrics.json")["decision"])
    for suffix in ("status", "pid", "started", "finished", "session"):
        path = root / f"fep-ph16.{suffix}"
        output[f"runner_{suffix}"] = (
            path.read_text(encoding="utf-8").strip() if path.is_file() else None
        )
    try:
        pid = int(output.get("runner_pid") or -1)
        if pid <= 0:
            raise ValueError("runner PID must be positive")
        os.kill(pid, 0)
        output["runner_alive"] = True
    except (ValueError, OSError):
        output["runner_alive"] = False
    return output
