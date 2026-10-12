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

from .analysis import analyze_atlas
from .config import SCALE_LADDER, ExperimentConfig, profile_config, with_selected_scale
from .models import ModelCounts, model_digest, model_from_counts, save_model
from .screen import ScreenCombination, generate_screen_combination, screen_combinations
from .simulation import controller_for, run_episode
from .types import ControllerName, ObservationThresholds, PreferenceMode
from .validation import validate_experiment
from .worker import (
    CellSpec,
    ConditionSpec,
    conditions,
    environment_design,
    fit_pooled_condition,
    generate_evaluation_cell,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREEN_SCHEMA = "fep-ph15-screen-registration-v1"
REGISTRATION_SCHEMA = "fep-ph15-evaluation-registration-v1"


def profile_root(run_root: Path, profile: str) -> Path:
    return Path(run_root) / profile


def _source_files() -> list[Path]:
    paths = list((PROJECT_ROOT / "fep_ph15").glob("*.py"))
    paths.extend(list((PROJECT_ROOT / "fep_ph1").glob("*.py")))
    paths.extend(
        PROJECT_ROOT / "fep_lab" / name
        for name in ("integrity.py", "pymdp_backend.py", "reference.py", "seeds.py", "types.py")
    )
    for name in (
        "EXPERIMENT_FEP_PH15_PROTOCOL.md",
        "requirements-fep-lab-lock.txt",
        "scripts/run_fep_ph15_campaign.sh",
        "scripts/run_fep_ph15_detached.sh",
        "scripts/status_fep_ph15.sh",
        "scripts/control_fep_ph15.sh",
    ):
        path = PROJECT_ROOT / name
        if path.is_file():
            paths.append(path)
    return sorted(path for path in paths if path.is_file())


def _source_digest() -> str:
    return sha256_bytes(canonical_json_bytes(source_manifest(PROJECT_ROOT, _source_files())))


def _prior_dependencies() -> dict[str, Any]:
    stage0 = PROJECT_ROOT / "runs-fep-lab" / "full"
    e1 = PROJECT_ROOT / "runs-fep-ph1" / "full"
    required = {
        "stage0_metrics": stage0 / "analysis" / "metrics.json",
        "stage0_analysis_seal": stage0 / "analysis" / "seal.json",
        "stage0_replay_seal": stage0 / "replay" / "seal.json",
        "fep_ph1_registration": e1 / "registration.json",
        "fep_ph1_replay_seal": e1 / "replay" / "seal.json",
        "fep_ph1_amendment_seal": e1 / "amendment-1" / "seal.json",
        "fep_ph1_amended_analysis_seal": e1 / "analysis-amendment-1" / "seal.json",
        "fep_ph1_final_report": PROJECT_ROOT / "EXPERIMENT_FEP_PH1_FINAL_REPORT.md",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing sealed prerequisite artifacts: {missing}")
    for label, directory in (
        ("Stage 0 analysis", stage0 / "analysis"),
        ("Stage 0 replay", stage0 / "replay"),
        ("FEP-PH1 replay", e1 / "replay"),
        ("FEP-PH1 amendment", e1 / "amendment-1"),
        ("FEP-PH1 amended analysis", e1 / "analysis-amendment-1"),
    ):
        if not verify_seal(directory):
            raise RuntimeError(f"{label} dependency seal does not verify")
    stage0_metrics = read_json(required["stage0_metrics"])
    e1_replay = read_json(e1 / "replay" / "replay.json")
    amended_metrics = read_json(e1 / "analysis-amendment-1" / "metrics.json")
    if stage0_metrics.get("verdict") != "VALIDATION_PASS":
        raise RuntimeError("Stage 0 known-positive dependency is not valid")
    if e1_replay.get("all_exact") is not True:
        raise RuntimeError("FEP-PH1 exact replay dependency is not valid")
    if amended_metrics.get("decision", {}).get("integrity_verdict") != "VALID_WITH_POSTOUTCOME_MECHANICAL_ANALYSIS_AMENDMENT":
        raise RuntimeError("FEP-PH1 amended analysis dependency is not valid")
    return {name: sha256_file(path) for name, path in sorted(required.items())}


def _array_digest(arrays: dict[str, np.ndarray]) -> str:
    chunks: list[bytes] = []
    for name in sorted(arrays):
        value = np.ascontiguousarray(arrays[name])
        chunks.extend((name.encode(), str(value.shape).encode(), value.dtype.str.encode(), value.tobytes()))
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
        "schema": "fep-ph15-wall-clock-v1",
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


def validate_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    ensure_clock(run_root, config)
    output = profile_root(run_root, config.profile) / "validation"
    digest = _source_digest()
    if verify_seal(output):
        payload = read_json(output / "validation.json")
        if payload.get("source_digest") != digest:
            raise RuntimeError("sealed FEP-PH1.5 validation belongs to different source")
        return payload
    return validate_experiment(config, output, digest)


def screen_registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "screen-registration.json"


def screen_register(run_root: Path, config: ExperimentConfig) -> Path:
    validation = validate_stage(run_root, config)
    if validation.get("all_pass") is not True:
        raise RuntimeError("validation failed; refusing screen registration")
    manifest: dict[str, Any] = {
        "schema": SCREEN_SCHEMA,
        "profile": config.profile,
        "master_seed": config.master_seed,
        "screen_contract": {
            "matrices": config.screen_matrices,
            "branches": config.screen_branches,
            "horizon": config.screen_horizon,
            "selection_targets": {"hard": 0.40, "transition": 0.70},
            "actionability_threshold": 0.10,
            "retain_non_actionable": True,
        },
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "prior_dependencies": _prior_dependencies(),
        "runtime": runtime_manifest(),
    }
    manifest["screen_registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = screen_registration_path(run_root, config.profile)
    if path.is_file():
        if read_json(path) != manifest:
            raise RuntimeError("existing screen registration differs from current contract")
        return path
    write_json(path, manifest)
    return path


def verify_screen_registration(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    path = screen_registration_path(run_root, config.profile)
    if not path.is_file():
        raise FileNotFoundError(f"missing screen registration {path}")
    payload = read_json(path)
    if payload.get("schema") != SCREEN_SCHEMA:
        raise RuntimeError("screen registration schema mismatch")
    if payload.get("sources") != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("screen-registered source has drifted")
    if payload.get("dependencies") != dependency_versions():
        raise RuntimeError("screen-registered dependencies have drifted")
    if payload.get("prior_dependencies") != _prior_dependencies():
        raise RuntimeError("screen-registered prerequisite artifacts have drifted")
    return payload


def _screen_paths(output: Path, combination: ScreenCombination) -> tuple[Path, Path]:
    return output / "cells" / f"{combination.key}.npz", output / "cells" / f"{combination.key}.json"


def _save_screen_task(argument: tuple[ExperimentConfig, ScreenCombination, Path]) -> tuple[str, str]:
    config, combination, output = argument
    data, metadata = _screen_paths(output, combination)
    if _cell_complete(data, metadata):
        return str(data), str(metadata)
    arrays, payload = generate_screen_combination(config, combination)
    _save_npz(data, arrays)
    payload.update({"array_digest": _array_digest(arrays), "file_sha256": sha256_file(data)})
    write_json(metadata, payload)
    return str(data), str(metadata)


def screen_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_screen_registration(run_root, config)
    output = profile_root(run_root, config.profile) / "screen"
    if verify_seal(output):
        return output
    _deadline(run_root, config)
    output.mkdir(parents=True, exist_ok=True)
    arguments = [(config, combination, output) for combination in screen_combinations()]
    sealed: list[str] = []
    for index, paths in enumerate(_map_tasks(_save_screen_task, arguments, config.workers), start=1):
        _deadline(run_root, config)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        print(f"[screen] mechanisms {index}/{len(arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _replay_screen_task(argument: tuple[ExperimentConfig, ScreenCombination, Path]) -> dict[str, Any]:
    config, combination, screen_root = argument
    data, metadata = _screen_paths(screen_root, combination)
    expected = read_json(metadata)
    arrays, payload = generate_screen_combination(config, combination)
    return {
        "combination": combination.key,
        "arrays_exact": _array_digest(arrays) == expected.get("array_digest"),
        "selection_exact": payload == {key: expected[key] for key in payload},
        "file_present": data.is_file(),
    }


def replay_screen_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_screen_registration(run_root, config)
    screen_root = profile_root(run_root, config.profile) / "screen"
    if not verify_seal(screen_root):
        raise RuntimeError("screen stage is not sealed")
    output = profile_root(run_root, config.profile) / "screen-replay"
    if verify_seal(output):
        return output
    _deadline(run_root, config)
    arguments = [(config, combination, screen_root) for combination in screen_combinations()]
    results = []
    for index, result in enumerate(_map_tasks(_replay_screen_task, arguments, config.workers), start=1):
        _deadline(run_root, config)
        results.append(result)
        print(f"[screen-replay] mechanisms {index}/{len(arguments)}", flush=True)
    exact = all(value["arrays_exact"] and value["selection_exact"] and value["file_present"] for value in results)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "replay.json", {"schema": "fep-ph15-screen-replay-v1", "cells": results, "all_exact": exact})
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError("screen exact replay failed")
    return output


def _benchmark_seconds(config: ExperimentConfig, screen_root: Path, name: ControllerName) -> float:
    from fep_ph1.gard import generate_beta, generate_initial_composition
    from .worker import _variants

    condition = conditions(screen_root)[0]
    cell = CellSpec(0, condition)
    counts = ModelCounts.empty()
    for state in range(9):
        observation = (state % 4, state % 3, state % 3, state % 4)
        counts.add_initial(state, observation)
        for action in range(4):
            counts.add_transition(state, action, (state + action + 1) % 9, observation)
    pooled = model_from_counts(counts, config, PreferenceMode.BALANCED)
    variants = _variants(config, cell, pooled, pooled)
    beta = generate_beta(config.gard, np.random.default_rng(15_701))
    initial = generate_initial_composition(config.gard, np.random.default_rng(15_702))
    short = replace(config, horizon=min(8, config.horizon))
    costs = config.action_cost_uptake if condition.channel.value == "uptake" else config.molecular_base_cost
    timings = []
    for repetition in range(3):
        controller = controller_for(name, short, pooled, pooled, variants, costs)
        started = time.perf_counter()
        run_episode(
            short, environment_design(config, condition, 0), beta, initial,
            ObservationThresholds(), name, controller, (15_703, 15_704, 15_705),
            15_706 + repetition,
        )
        timings.append((time.perf_counter() - started) / short.horizon)
    return float(np.median(timings))


def benchmark_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    screen_register(run_root, config)
    screen_stage(run_root, config)
    replay = replay_screen_stage(run_root, config)
    if not read_json(replay / "replay.json").get("all_exact"):
        raise RuntimeError("screen replay is not exact")
    output = profile_root(run_root, config.profile) / "benchmark"
    if verify_seal(output):
        payload = read_json(output / "benchmark.json")
        if payload.get("source_digest") != _source_digest():
            raise RuntimeError("sealed benchmark belongs to different source")
        return payload
    screen_root = profile_root(run_root, config.profile) / "screen"
    active = _benchmark_seconds(config, screen_root, ControllerName.BALANCED_AI_LOCAL)
    simple = _benchmark_seconds(config, screen_root, ControllerName.NOOP)
    scales = SCALE_LADDER if config.profile == "full" else (config.evaluation_matrices,)
    elapsed = elapsed_seconds(run_root, config)
    projections: dict[str, dict[str, float]] = {}
    condition_count = 32
    for scale in scales:
        active_per_matrix = config.branches * config.horizon * (16 * 7 + 16 * 10)
        simple_per_matrix = config.branches * config.horizon * (16 * 3 + 16 * 3)
        calibration_per_matrix = condition_count * config.calibration_episodes * config.calibration_steps
        fit_fissions = condition_count * config.development_matrices * config.development_episodes * config.development_steps
        evaluation_work = scale * (active_per_matrix * active + (simple_per_matrix + calibration_per_matrix) * simple)
        fit_work = fit_fissions * simple
        ideal_parallel = 2.0 * (evaluation_work + fit_work) / max(1, config.workers)
        fixed = 300.0 if config.profile == "full" else 90.0 if config.profile == "quick" else 30.0
        remaining = 1.75 * ideal_parallel + fixed
        projections[str(scale)] = {
            "remaining_seconds": remaining,
            "total_from_clock_start_seconds": elapsed + remaining,
        }
    eligible = [scale for scale in scales if projections[str(scale)]["total_from_clock_start_seconds"] <= config.registration_projection_ceiling_seconds]
    if not eligible:
        raise RuntimeError("minimum 48-matrix atlas projects beyond the four-hour registration contract")
    result = {
        "schema": "fep-ph15-benchmark-v1", "profile": config.profile,
        "seconds_per_fission": {"active": active, "simple": simple},
        "workers": config.workers, "elapsed_before_benchmark_seconds": elapsed,
        "projections": projections, "selected_evaluation_matrices": max(eligible),
        "registration_projection_ceiling_seconds": config.registration_projection_ceiling_seconds,
        "hard_wall_time_seconds": config.wall_time_limit_seconds,
        "source_digest": _source_digest(),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "benchmark.json", result)
    seal_directory(output, ["benchmark.json"])
    return result


def registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "registration.json"


def _screen_dependency(run_root: Path, profile: str) -> dict[str, str]:
    root = profile_root(run_root, profile)
    paths = {
        "screen_registration": root / "screen-registration.json",
        "screen_seal": root / "screen" / "seal.json",
        "screen_replay_seal": root / "screen-replay" / "seal.json",
        "benchmark_seal": root / "benchmark" / "seal.json",
    }
    if any(not path.is_file() for path in paths.values()):
        raise RuntimeError("screen/benchmark dependency set is incomplete")
    for name in ("screen", "screen-replay", "benchmark"):
        if not verify_seal(root / name):
            raise RuntimeError(f"{name} dependency seal does not verify")
    return {name: sha256_file(path) for name, path in paths.items()}


def register(run_root: Path, config: ExperimentConfig) -> tuple[Path, ExperimentConfig]:
    benchmark = benchmark_stage(run_root, config)
    scale = int(benchmark["selected_evaluation_matrices"])
    resolved = with_selected_scale(config, scale)
    elapsed_now = elapsed_seconds(run_root, resolved)
    remaining_projection = float(
        benchmark["projections"][str(scale)]["remaining_seconds"]
    )
    if elapsed_now + remaining_projection > resolved.registration_projection_ceiling_seconds:
        raise RuntimeError(
            "elapsed clock plus projected remaining work passed the evaluation "
            "registration ceiling"
        )
    manifest: dict[str, Any] = {
        "schema": REGISTRATION_SCHEMA, "config": resolved.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(), "runtime": runtime_manifest(),
        "prior_dependencies": _prior_dependencies(),
        "screen_dependencies": _screen_dependency(run_root, config.profile),
        "scientific_status": "EXPLORATORY_ONLY_NO_GLOBAL_CLASSIFIER",
        "clock": read_json(_clock_path(run_root, config.profile)),
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = registration_path(run_root, config.profile)
    if path.is_file():
        if read_json(path) != manifest:
            raise RuntimeError("existing evaluation registration differs from current contract")
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
    if payload.get("schema") != REGISTRATION_SCHEMA:
        raise RuntimeError("evaluation registration schema mismatch")
    if payload.get("sources") != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("registered source has drifted")
    if payload.get("dependencies") != dependency_versions() or payload.get("prior_dependencies") != _prior_dependencies():
        raise RuntimeError("registered dependency has drifted")
    if payload.get("screen_dependencies") != _screen_dependency(run_root, config.profile):
        raise RuntimeError("registered screen dependency has drifted")
    return _config_from_manifest(payload)


def _model_paths(root: Path, condition: ConditionSpec) -> tuple[Path, Path]:
    return root / "models" / f"{condition.key}.npz", root / "models" / f"{condition.key}.json"


def _save_fit_task(argument: tuple[ExperimentConfig, ConditionSpec, Path]) -> tuple[str, str]:
    config, condition, output = argument
    model_path, metadata_path = _model_paths(output, condition)
    if _cell_complete(model_path, metadata_path):
        return str(model_path), str(metadata_path)
    thresholds, counts, model, summary = fit_pooled_condition(config, condition)
    save_model(model_path, model, counts)
    with np.load(model_path, allow_pickle=False) as archive:
        digest = _array_digest({name: archive[name] for name in archive.files})
    write_json(metadata_path, {
        "schema": "fep-ph15-pooled-model-v1", "condition": condition.key,
        "thresholds": {"alignment": thresholds.alignment, "growth": thresholds.growth},
        "model_digest": model_digest(model), "array_digest": digest,
        "file_sha256": sha256_file(model_path), "summary": summary,
    })
    return str(model_path), str(metadata_path)


def fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    output = root / "fit"
    if verify_seal(output):
        return output
    _deadline(run_root, resolved)
    output.mkdir(parents=True, exist_ok=True)
    condition_values = conditions(root / "screen")
    arguments = [(resolved, condition, output) for condition in condition_values]
    sealed: list[str] = []
    for index, paths in enumerate(_map_tasks(_save_fit_task, arguments, resolved.workers), start=1):
        _deadline(run_root, resolved)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        print(f"[fit] conditions {index}/{len(arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _thresholds(fit_root: Path, condition: ConditionSpec) -> ObservationThresholds:
    _model, metadata = _model_paths(fit_root, condition)
    payload = read_json(metadata)
    return ObservationThresholds(
        tuple(float(value) for value in payload["thresholds"]["alignment"]),
        tuple(float(value) for value in payload["thresholds"]["growth"]),
    )  # type: ignore[arg-type]


def _evaluation_paths(output: Path, cell: CellSpec) -> tuple[Path, Path]:
    return output / "cells" / f"{cell.stem}.npz", output / "cells" / f"{cell.stem}.json"


def _save_evaluation_task(argument: tuple[ExperimentConfig, CellSpec, Path, ObservationThresholds, Path]) -> tuple[str, str]:
    config, cell, model_path, thresholds, output = argument
    data, metadata = _evaluation_paths(output, cell)
    if _cell_complete(data, metadata):
        return str(data), str(metadata)
    arrays, payload = generate_evaluation_cell(config, cell, model_path, thresholds)
    _save_npz(data, arrays)
    payload.update({"array_digest": _array_digest(arrays), "file_sha256": sha256_file(data)})
    write_json(metadata, payload)
    return str(data), str(metadata)


def simulate_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    fit_root = root / "fit"
    if not verify_seal(fit_root):
        raise RuntimeError("model fit is not sealed")
    output = root / "simulation"
    if verify_seal(output):
        return output
    _deadline(run_root, resolved)
    output.mkdir(parents=True, exist_ok=True)
    arguments = []
    condition_values = conditions(root / "screen")
    for matrix_id in range(resolved.evaluation_matrices):
        for condition in condition_values:
            cell = CellSpec(matrix_id, condition)
            model_path, _metadata = _model_paths(fit_root, condition)
            arguments.append((resolved, cell, model_path, _thresholds(fit_root, condition), output))
    sealed: list[str] = []
    for index, paths in enumerate(_map_tasks(_save_evaluation_task, arguments, resolved.workers), start=1):
        _deadline(run_root, resolved)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        if index % max(1, len(arguments) // 50) == 0 or index == len(arguments):
            print(f"[simulation] cells {index}/{len(arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _replay_fit_task(argument: tuple[ExperimentConfig, ConditionSpec, Path]) -> dict[str, Any]:
    config, condition, fit_root = argument
    _model_path, metadata_path = _model_paths(fit_root, condition)
    expected = read_json(metadata_path)
    thresholds, _counts, model, summary = fit_pooled_condition(config, condition)
    return {
        "condition": condition.key,
        "model_exact": model_digest(model) == expected["model_digest"],
        "threshold_exact": list(thresholds.alignment) == expected["thresholds"]["alignment"] and list(thresholds.growth) == expected["thresholds"]["growth"],
        "summary_exact": summary == expected["summary"],
    }


def _replay_cell_task(argument: tuple[ExperimentConfig, CellSpec, Path, ObservationThresholds, Path]) -> dict[str, Any]:
    config, cell, model_path, thresholds, simulation = argument
    _data, metadata = _evaluation_paths(simulation, cell)
    expected = read_json(metadata)
    arrays, payload = generate_evaluation_cell(config, cell, model_path, thresholds)
    return {
        "stem": cell.stem, "array_exact": _array_digest(arrays) == expected["array_digest"],
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
    _deadline(run_root, resolved)
    fit_root = root / "fit"
    condition_values = conditions(root / "screen")
    fit_arguments = [(resolved, condition, fit_root) for condition in condition_values]
    fit_results = []
    for index, result in enumerate(_map_tasks(_replay_fit_task, fit_arguments, resolved.workers), start=1):
        _deadline(run_root, resolved)
        fit_results.append(result)
        print(f"[replay-fit] conditions {index}/{len(fit_arguments)}", flush=True)
    cell_arguments = []
    for matrix_id in range(resolved.evaluation_matrices):
        for condition in condition_values:
            cell = CellSpec(matrix_id, condition)
            model_path, _metadata = _model_paths(fit_root, condition)
            cell_arguments.append((resolved, cell, model_path, _thresholds(fit_root, condition), simulation))
    cell_results = []
    for index, result in enumerate(_map_tasks(_replay_cell_task, cell_arguments, resolved.workers), start=1):
        _deadline(run_root, resolved)
        cell_results.append(result)
        if index % max(1, len(cell_arguments) // 50) == 0 or index == len(cell_arguments):
            print(f"[replay] cells {index}/{len(cell_arguments)}", flush=True)
    exact = all(value["model_exact"] and value["threshold_exact"] and value["summary_exact"] for value in fit_results) and all(value["array_exact"] and value["metadata_exact"] for value in cell_results)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "replay.json", {"schema": "fep-ph15-replay-v1", "fit": fit_results, "cells": cell_results, "all_exact": exact})
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError("FEP-PH1.5 exact evaluation replay failed")
    return output


def analyze_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "replay"
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("exact replay must pass before analysis")
    output = root / "analysis"
    if verify_seal(output):
        return output
    _deadline(run_root, resolved)
    analyze_atlas(resolved, root / "simulation", root / "screen", output)
    return output


def run_all(run_root: Path, config: ExperimentConfig) -> Path:
    ensure_clock(run_root, config)
    validate_stage(run_root, config)
    screen_register(run_root, config)
    screen_stage(run_root, config)
    replay_screen_stage(run_root, config)
    benchmark_stage(run_root, config)
    _path, resolved = register(run_root, config)
    fit_stage(run_root, resolved)
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
        "screen_registered": (root / "screen-registration.json").is_file(),
        "screen": seal_present(root / "screen"),
        "screen_replay": seal_present(root / "screen-replay"),
        "benchmark": seal_present(root / "benchmark"),
        "registered": (root / "registration.json").is_file(),
        "fit": seal_present(root / "fit"),
        "simulation": seal_present(root / "simulation"),
        "replay": seal_present(root / "replay"),
        "analysis": seal_present(root / "analysis"),
    }
    output: dict[str, Any] = {"profile": profile, **stages}
    ordered_stages = (
        ("validation", "validation"),
        ("screen_registered", "screen-registration"),
        ("screen", "screen"),
        ("screen_replay", "screen-replay"),
        ("benchmark", "benchmark"),
        ("registered", "evaluation-registration"),
        ("fit", "fit"),
        ("simulation", "simulation"),
        ("replay", "replay"),
        ("analysis", "analysis"),
    )
    output["current_stage"] = next(
        (label for key, label in ordered_stages if not stages[key]), "complete"
    )
    if (root / "clock.json").is_file():
        elapsed = elapsed_seconds(run_root, config)
        output.update({
            "elapsed_seconds": elapsed,
            "hard_remaining_seconds": max(0.0, config.wall_time_limit_seconds - elapsed),
            "time_budget_state": "TIME_BUDGET_EXHAUSTED_NO_VERDICT" if elapsed >= config.wall_time_limit_seconds and not stages["analysis"] else "within_budget" if not stages["analysis"] else "complete",
        })
    if stages["registered"]:
        registration = read_json(root / "registration.json")
        output["registration_id"] = registration["registration_id"]
        output["registered_source_current"] = registration.get("sources") == source_manifest(
            PROJECT_ROOT, _source_files()
        )
        output["selected_evaluation_matrices"] = registration["config"]["evaluation_matrices"]
        expected = int(registration["config"]["evaluation_matrices"]) * 32
        output["expected_evaluation_cells"] = expected
        output["simulation_cells_present"] = len(list((root / "simulation" / "cells").glob("*.json")))
        replay_payload = read_json(root / "replay" / "replay.json") if (root / "replay" / "replay.json").is_file() else {}
        output["replay_cells_recorded"] = len(replay_payload.get("cells", []))
    elif (root / "screen" / "cells").is_dir():
        output["screen_cells_present"] = len(
            list((root / "screen" / "cells").glob("*.json"))
        )
        output["expected_screen_cells"] = 8
    benchmark_path = root / "benchmark" / "benchmark.json"
    if benchmark_path.is_file() and "elapsed_seconds" in output:
        benchmark = read_json(benchmark_path)
        scale = str(benchmark["selected_evaluation_matrices"])
        projected_total = float(benchmark["projections"][scale]["total_from_clock_start_seconds"])
        eta_seconds = 0.0 if stages["analysis"] else max(
            0.0, projected_total - float(output["elapsed_seconds"])
        )
        output["projected_total_seconds"] = projected_total
        output["eta_seconds"] = eta_seconds
        output["eta_utc"] = datetime.fromtimestamp(
            time.time() + eta_seconds, timezone.utc
        ).isoformat()
    if stages["analysis"]:
        decision = read_json(root / "analysis" / "metrics.json")["decision"]
        output.update(decision)
    for suffix in ("status", "pid", "started", "finished", "session"):
        path = root / f"fep-ph15.{suffix}"
        output[f"runner_{suffix}"] = path.read_text(encoding="utf-8").strip() if path.is_file() else None
    try:
        pid = int(output.get("runner_pid") or -1)
        if pid <= 0:
            raise ValueError("runner PID must be positive")
        os.kill(pid, 0)
        output["runner_alive"] = True
    except (ValueError, OSError):
        output["runner_alive"] = False
    return output
