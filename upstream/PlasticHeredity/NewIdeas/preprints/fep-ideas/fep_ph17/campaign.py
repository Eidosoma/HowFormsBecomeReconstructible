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

from .analysis import analyze_final, analyze_stage_a
from .config import (
    MAX_WORKERS,
    RIDGE_GRID,
    SCALE_PAIRS,
    ExperimentConfig,
    profile_config,
    with_selected_scales,
    with_stage_b_choices,
)
from .data import (
    cohort_seed_domains,
    development_cell,
    development_conditions,
    stage_a_conditions,
    stage_b_conditions,
    training_data_from_cells,
)
from .hybrid_model import (
    fit_hybrid_model,
    load_model,
    model_arrays,
    model_digest,
    model_summary,
    save_model,
)
from .tuning import select_epistemic_coefficient
from .types import CellSpec, ConditionSpec, ObservationThresholds
from .validation import validate_experiment
from .worker import generate_evaluation_cell, hybrid_model_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_REGISTRATION_SCHEMA = "fep-ph17-development-registration-v1"
EVALUATION_REGISTRATION_SCHEMA = "fep-ph17-evaluation-registration-v1"
STAGE_B_REGISTRATION_SCHEMA = "fep-ph17-stage-b-registration-v1"


def profile_root(run_root: Path, profile: str) -> Path:
    return Path(run_root) / profile


def _source_files() -> list[Path]:
    paths = list((PROJECT_ROOT / "fep_ph17").glob("*.py"))
    paths.extend((PROJECT_ROOT / "fep_ph16").glob("*.py"))
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
        "EXPERIMENT_FEP_PH16_FINAL_REPORT.md",
        "EXPERIMENT_FEP_PH17_PROTOCOL.md",
        "requirements-fep-lab-lock.txt",
        "scripts/run_fep_ph17_campaign.sh",
        "scripts/run_fep_ph17_detached.sh",
        "scripts/status_fep_ph17.sh",
        "scripts/control_fep_ph17.sh",
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
    return bool(sources) and all(
        (PROJECT_ROOT / relative).is_file()
        and sha256_file(PROJECT_ROOT / relative) == expected
        for relative, expected in sources.items()
    )


def _prior_dependencies() -> dict[str, str]:
    experiment15 = PROJECT_ROOT / "runs-fep-ph15" / "full"
    experiment16 = PROJECT_ROOT / "runs-fep-ph16" / "full"
    required = {
        "fep_ph15_screen_seal": experiment15 / "screen" / "seal.json",
        "fep_ph15_screen_replay_seal": experiment15 / "screen-replay" / "seal.json",
        "fep_ph16_registration": experiment16 / "registration.json",
        "fep_ph16_development_replay_seal": experiment16 / "development-replay" / "seal.json",
        "fep_ph16_fit_replay_seal": experiment16 / "fit-replay" / "seal.json",
        "fep_ph16_replay_seal": experiment16 / "replay" / "seal.json",
        "fep_ph16_analysis_seal": experiment16 / "analysis" / "seal.json",
        "fep_ph16_metrics": experiment16 / "analysis" / "metrics.json",
        "fep_ph16_final_report": PROJECT_ROOT / "EXPERIMENT_FEP_PH16_FINAL_REPORT.md",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing sealed prerequisite artifacts: {missing}")
    for label, directory in (
        ("FEP-PH1.5 screen", experiment15 / "screen"),
        ("FEP-PH1.5 screen replay", experiment15 / "screen-replay"),
        ("FEP-PH1.6 development replay", experiment16 / "development-replay"),
        ("FEP-PH1.6 fit replay", experiment16 / "fit-replay"),
        ("FEP-PH1.6 evaluation replay", experiment16 / "replay"),
        ("FEP-PH1.6 analysis", experiment16 / "analysis"),
    ):
        if not verify_seal(directory):
            raise RuntimeError(f"{label} dependency seal does not verify")
    if read_json(experiment15 / "screen-replay" / "replay.json").get("all_exact") is not True:
        raise RuntimeError("FEP-PH1.5 screen replay dependency is not exact")
    if read_json(experiment16 / "replay" / "replay.json").get("all_exact") is not True:
        raise RuntimeError("FEP-PH1.6 replay dependency is not exact")
    decision = read_json(experiment16 / "analysis" / "metrics.json").get("decision", {})
    if decision.get("integrity_verdict") != "VALID":
        raise RuntimeError("FEP-PH1.6 integrity dependency is not valid")
    if not _registered_sources_current(experiment16 / "registration.json"):
        raise RuntimeError("FEP-PH1.6 registered source has drifted")
    return {name: sha256_file(path) for name, path in sorted(required.items())}


def _array_digest(arrays: dict[str, np.ndarray]) -> str:
    chunks: list[bytes] = []
    for name in sorted(arrays):
        value = np.ascontiguousarray(arrays[name])
        chunks.extend(
            (name.encode(), str(value.shape).encode(), value.dtype.str.encode(), value.tobytes())
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
        "schema": "fep-ph17-wall-clock-v1",
        "started_epoch": now,
        "started_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "hard_wall_time_seconds": config.wall_time_limit_seconds,
        "pauses_and_restarts_consume_budget": True,
    }
    write_json(path, payload)
    return payload


def elapsed_seconds(run_root: Path, config: ExperimentConfig) -> float:
    return max(0.0, time.time() - float(ensure_clock(run_root, config)["started_epoch"]))


def _deadline(run_root: Path, config: ExperimentConfig) -> None:
    elapsed = elapsed_seconds(run_root, config)
    if elapsed >= config.graceful_stop_seconds:
        raise TimeoutError(
            f"FEP-PH1.7 graceful stop reached after {elapsed:.1f} seconds"
        )


def _map_tasks(function: Any, arguments: list[Any], workers: int) -> Iterable[Any]:
    if workers <= 1:
        return map(function, arguments)
    context = multiprocessing.get_context("spawn")
    executor = ProcessPoolExecutor(max_workers=workers, mp_context=context)
    futures = [executor.submit(function, argument) for argument in arguments]

    def iterator() -> Iterable[Any]:
        try:
            for future in futures:
                yield future.result()
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    return iterator()


def _screen_root() -> Path:
    return PROJECT_ROOT / "runs-fep-ph15" / "full" / "screen"


def validate_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    ensure_clock(run_root, config)
    _prior_dependencies()
    output = profile_root(run_root, config.profile) / "validation"
    if verify_seal(output):
        return read_json(output / "validation.json")
    result = validate_experiment(config, _screen_root())
    if result.get("all_passed") is not True:
        raise RuntimeError("FEP-PH1.7 validation failed")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "validation.json", result)
    seal_directory(output, ["validation.json"])
    return result


def development_registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "development-registration.json"


def develop_register(run_root: Path, config: ExperimentConfig) -> Path:
    validate_stage(run_root, config)
    manifest: dict[str, Any] = {
        "schema": DEVELOPMENT_REGISTRATION_SCHEMA,
        "config": config.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "runtime": runtime_manifest(),
        "prior_dependencies": _prior_dependencies(),
        "seed_domains": cohort_seed_domains(config),
        "development_conditions": [
            value.key for value in development_conditions(_screen_root())
        ],
        "evaluation_streams_touched": False,
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = development_registration_path(run_root, config.profile)
    if path.is_file():
        if read_json(path) != manifest:
            raise RuntimeError("existing development registration differs from contract")
        return path
    write_json(path, manifest)
    return path


def verify_development_registration(run_root: Path, config: ExperimentConfig) -> None:
    path = development_registration_path(run_root, config.profile)
    if not path.is_file():
        raise FileNotFoundError("missing FEP-PH1.7 development registration")
    payload = read_json(path)
    if payload.get("schema") != DEVELOPMENT_REGISTRATION_SCHEMA:
        raise RuntimeError("development registration schema mismatch")
    if payload.get("sources") != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("development-registered source has drifted")
    if payload.get("dependencies") != dependency_versions():
        raise RuntimeError("development dependencies have drifted")
    if payload.get("prior_dependencies") != _prior_dependencies():
        raise RuntimeError("sealed prior dependencies have drifted")


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
    payload.update({"array_digest": _array_digest(arrays), "file_sha256": sha256_file(data)})
    write_json(metadata, payload)
    return str(data), str(metadata)


def development_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_development_registration(run_root, config)
    output = profile_root(run_root, config.profile) / "development"
    if verify_seal(output):
        return output
    conditions = development_conditions(_screen_root())
    arguments = [(config, condition, output) for condition in conditions]
    sealed: list[str] = []
    for index, paths in enumerate(_map_tasks(_save_development_task, arguments, config.workers), start=1):
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
        "array_exact": _array_digest(arrays) == expected["array_digest"],
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
    conditions = development_conditions(_screen_root())
    arguments = [(config, condition, development) for condition in conditions]
    results = []
    for index, result in enumerate(_map_tasks(_replay_development_task, arguments, config.workers), start=1):
        _deadline(run_root, config)
        results.append(result)
        print(f"[development-replay] conditions {index}/{len(arguments)}", flush=True)
    exact = all(value["array_exact"] and value["metadata_exact"] for value in results)
    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "replay.json",
        {"schema": "fep-ph17-development-replay-v1", "cells": results, "all_exact": exact},
    )
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError("FEP-PH1.7 development exact replay failed")
    return output


def _training_data(development: Path):
    paths = tuple(
        _development_paths(development, condition)[0]
        for condition in development_conditions(_screen_root())
    )
    return training_data_from_cells(paths)


def fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_development_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "development-replay"
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("exact development replay must pass before fitting")
    output = root / "fit"
    if verify_seal(output):
        return output
    data = _training_data(root / "development")
    model = fit_hybrid_model(
        data,
        components=config.clr_components,
        members=config.ensemble_members,
        ridge_grid=RIDGE_GRID,
    )
    path = hybrid_model_path(output)
    save_model(path, model)
    arrays = model_arrays(model)
    metadata = {
        "schema": "fep-ph17-hybrid-model-v1",
        "training_rows": int(len(data.actions)),
        "summary": model_summary(model),
        "array_digest": _array_digest(arrays),
        "file_sha256": sha256_file(path),
        "thresholds": {"alignment": [1.0 / 3.0, 2.0 / 3.0], "growth": [100.0, 300.0]},
    }
    write_json(path.with_suffix(".json"), metadata)
    tuning = select_epistemic_coefficient(config, model, data)
    if config.profile == "full" and tuning["eligible"] is not True:
        raise RuntimeError("development behavior did not activate a frozen epistemic coefficient")
    if config.profile != "full" and tuning["eligible"] is not True:
        tuning["workflow_only_fallback"] = True
    write_json(output / "epistemic-tuning.json", tuning)
    seal_directory(
        output,
        [
            str(path.relative_to(output)),
            str(path.with_suffix(".json").relative_to(output)),
            "epistemic-tuning.json",
        ],
    )
    return output


def replay_fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    verify_development_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    fit_root = root / "fit"
    if not verify_seal(fit_root):
        raise RuntimeError("fit stage is not sealed")
    output = root / "fit-replay"
    if verify_seal(output):
        return output
    data = _training_data(root / "development")
    expected_model = load_model(hybrid_model_path(fit_root))
    replayed = fit_hybrid_model(
        data,
        components=config.clr_components,
        members=config.ensemble_members,
        ridge_grid=RIDGE_GRID,
    )
    expected_tuning = read_json(fit_root / "epistemic-tuning.json")
    replayed_tuning = select_epistemic_coefficient(config, replayed, data)
    if expected_tuning.get("workflow_only_fallback"):
        replayed_tuning["workflow_only_fallback"] = True
    result = {
        "schema": "fep-ph17-fit-replay-v1",
        "model_exact": model_digest(replayed) == model_digest(expected_model),
        "summary_exact": model_summary(replayed) == model_summary(expected_model),
        "tuning_exact": replayed_tuning == expected_tuning,
    }
    result["all_exact"] = all(result[key] for key in ("model_exact", "summary_exact", "tuning_exact"))
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "replay.json", result)
    seal_directory(output, ["replay.json"])
    if not result["all_exact"]:
        raise RuntimeError("FEP-PH1.7 fitted-model exact replay failed")
    return output


def _thresholds(fit_root: Path) -> ObservationThresholds:
    payload = read_json(hybrid_model_path(fit_root).with_suffix(".json"))["thresholds"]
    return ObservationThresholds(
        tuple(float(value) for value in payload["alignment"]),
        tuple(float(value) for value in payload["growth"]),
    )  # type: ignore[arg-type]


def _resolved_before_stage_b(run_root: Path, config: ExperimentConfig) -> ExperimentConfig:
    tuning = read_json(profile_root(run_root, config.profile) / "fit" / "epistemic-tuning.json")
    return replace(
        config,
        selected_epistemic_coefficient=float(tuning["selected_coefficient"]),
    )


def benchmark_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    verify_development_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "fit-replay"
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("fit replay must be exact before benchmarking")
    output = root / "benchmark"
    if verify_seal(output):
        payload = read_json(output / "benchmark.json")
        if payload.get("source_digest") != _source_digest():
            raise RuntimeError("sealed benchmark belongs to different source")
        return payload
    timing_seed = sha256_bytes(f"{config.master_seed}.fep_ph17.disposable_timing".encode())
    timed = replace(
        _resolved_before_stage_b(run_root, config),
        master_seed=timing_seed,
        branches=1,
        horizon=min(6, config.horizon),
        selected_authority_scale=1.5,
    )
    fit_root = root / "fit"
    stage_a_condition = stage_a_conditions(_screen_root())[0]
    stage_b_condition = stage_b_conditions(_screen_root(), 1.5)[0]
    timings: dict[str, list[float]] = {"stage_a": [], "stage_b": []}
    for label, condition in (("stage_a", stage_a_condition), ("stage_b", stage_b_condition)):
        for _repetition in range(3):
            started = time.perf_counter()
            generate_evaluation_cell(
                timed, CellSpec(0, condition), fit_root, _thresholds(fit_root)
            )
            timings[label].append(time.perf_counter() - started)
    scaled = {
        key: float(np.median(value))
        * config.horizon
        / timed.horizon
        * config.branches
        / timed.branches
        for key, value in timings.items()
    }
    pairs = SCALE_PAIRS if config.profile == "full" else ((config.stage_a_matrices, config.stage_b_matrices),)
    elapsed = elapsed_seconds(run_root, config)
    projections: dict[str, dict[str, Any]] = {}
    selected_pair = None
    for stage_a_scale, stage_b_scale in pairs:
        cells_a = stage_a_scale * 10
        cells_b = stage_b_scale * 4
        ideal = 2.0 * (
            cells_a * scaled["stage_a"] + cells_b * scaled["stage_b"]
        ) / max(1, config.workers)
        fixed = 600.0 if config.profile == "full" else 120.0 if config.profile == "quick" else 30.0
        remaining = 1.75 * ideal + fixed
        key = f"{stage_a_scale},{stage_b_scale}"
        projections[key] = {
            "stage_a_matrices": stage_a_scale,
            "stage_b_matrices": stage_b_scale,
            "stage_a_cells": cells_a,
            "stage_b_cells": cells_b,
            "remaining_seconds": remaining,
            "total_from_clock_start_seconds": elapsed + remaining,
        }
        if selected_pair is None and elapsed + remaining <= config.registration_projection_ceiling_seconds:
            selected_pair = (stage_a_scale, stage_b_scale)
    result = {
        "schema": "fep-ph17-benchmark-v1",
        "profile": config.profile,
        "benchmark_seed_domain": "disposable_timing_not_development_stage_a_or_stage_b",
        "benchmark_master_seed": timing_seed,
        "short_horizon": timed.horizon,
        "short_branches": timed.branches,
        "full_horizon": config.horizon,
        "full_branches": config.branches,
        "whole_cell_seconds_samples": timings,
        "horizon_scaled_cell_seconds": scaled,
        "workers": config.workers,
        "elapsed_before_benchmark_seconds": elapsed,
        "projections": projections,
        "registration_eligible": selected_pair is not None,
        "selected_scale_pair": list(selected_pair) if selected_pair else None,
        "registration_projection_ceiling_seconds": config.registration_projection_ceiling_seconds,
        "hard_wall_time_seconds": config.wall_time_limit_seconds,
        "source_digest": _source_digest(),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "benchmark.json", result)
    seal_directory(output, ["benchmark.json"])
    if selected_pair is None:
        raise RuntimeError("minimum (12,12) scale pair projects beyond the sixteen-hour contract")
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
    stage_a_scale, stage_b_scale = (int(value) for value in benchmark["selected_scale_pair"])
    resolved = with_selected_scales(
        _resolved_before_stage_b(run_root, config), stage_a_scale, stage_b_scale
    )
    manifest: dict[str, Any] = {
        "schema": EVALUATION_REGISTRATION_SCHEMA,
        "config": resolved.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "runtime": runtime_manifest(),
        "prior_dependencies": _prior_dependencies(),
        "development_dependencies": _development_dependencies(run_root, config.profile),
        "primary_outcome": "inherited_completion_fraction",
        "stage_b_is_mechanical_and_conditional": True,
        "resource_ceiling_workers": MAX_WORKERS,
        "reduced_power_scale": stage_a_scale < 24 or stage_b_scale < 24,
        "strict_events": "held_out_descriptive_only",
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
        raise RuntimeError("evaluation dependencies have drifted")
    if payload.get("prior_dependencies") != _prior_dependencies():
        raise RuntimeError("registered prior dependencies have drifted")
    if payload.get("development_dependencies") != _development_dependencies(run_root, config.profile):
        raise RuntimeError("registered development dependencies have drifted")
    return _config_from_manifest(payload)


def _evaluation_paths(output: Path, cell: CellSpec) -> tuple[Path, Path]:
    return (
        output / "cells" / f"{cell.stem}.npz",
        output / "cells" / f"{cell.stem}.json",
    )


def _save_evaluation_task(
    argument: tuple[ExperimentConfig, CellSpec, Path, ObservationThresholds, Path]
) -> tuple[str, str]:
    config, cell, fit_root, thresholds, output = argument
    data, metadata = _evaluation_paths(output, cell)
    if _cell_complete(data, metadata):
        return str(data), str(metadata)
    arrays, payload = generate_evaluation_cell(config, cell, fit_root, thresholds)
    _save_npz(data, arrays)
    payload.update({"array_digest": _array_digest(arrays), "file_sha256": sha256_file(data)})
    write_json(metadata, payload)
    return str(data), str(metadata)


def _simulate(
    run_root: Path,
    config: ExperimentConfig,
    output_name: str,
    conditions: tuple[ConditionSpec, ...],
    matrices: int,
) -> Path:
    root = profile_root(run_root, config.profile)
    output = root / output_name
    if verify_seal(output):
        return output
    fit_root = root / "fit"
    arguments = [
        (config, CellSpec(matrix_id, condition), fit_root, _thresholds(fit_root), output)
        for matrix_id in range(matrices)
        for condition in conditions
    ]
    sealed: list[str] = []
    for index, paths in enumerate(_map_tasks(_save_evaluation_task, arguments, config.workers), start=1):
        _deadline(run_root, config)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        if index % max(1, len(arguments) // 50) == 0 or index == len(arguments):
            print(f"[{output_name}] cells {index}/{len(arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _replay_evaluation_task(
    argument: tuple[ExperimentConfig, CellSpec, Path, ObservationThresholds, Path]
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


def _replay(
    run_root: Path,
    config: ExperimentConfig,
    simulation_name: str,
    replay_name: str,
    conditions: tuple[ConditionSpec, ...],
    matrices: int,
) -> Path:
    root = profile_root(run_root, config.profile)
    simulation = root / simulation_name
    if not verify_seal(simulation):
        raise RuntimeError(f"{simulation_name} is not sealed")
    output = root / replay_name
    if verify_seal(output):
        return output
    fit_root = root / "fit"
    arguments = [
        (config, CellSpec(matrix_id, condition), fit_root, _thresholds(fit_root), simulation)
        for matrix_id in range(matrices)
        for condition in conditions
    ]
    results = []
    for index, result in enumerate(_map_tasks(_replay_evaluation_task, arguments, config.workers), start=1):
        _deadline(run_root, config)
        results.append(result)
        if index % max(1, len(arguments) // 50) == 0 or index == len(arguments):
            print(f"[{replay_name}] cells {index}/{len(arguments)}", flush=True)
    exact = all(value["array_exact"] and value["metadata_exact"] for value in results)
    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "replay.json",
        {"schema": f"fep-ph17-{replay_name}-v1", "cells": results, "all_exact": exact},
    )
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError(f"FEP-PH1.7 {replay_name} exact replay failed")
    return output


def stage_a_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    return _simulate(
        run_root,
        resolved,
        "stage-a",
        stage_a_conditions(_screen_root()),
        resolved.stage_a_matrices,
    )


def replay_stage_a(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    return _replay(
        run_root,
        resolved,
        "stage-a",
        "stage-a-replay",
        stage_a_conditions(_screen_root()),
        resolved.stage_a_matrices,
    )


def analyze_stage_a_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "stage-a-replay"
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("Stage A exact replay must pass before gate analysis")
    output = root / "stage-a-analysis"
    if verify_seal(output):
        return output
    _deadline(run_root, resolved)
    analyze_stage_a(resolved, root / "stage-a", output)
    return output


def stage_b_registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "stage-b-registration.json"


def register_stage_b(run_root: Path, config: ExperimentConfig) -> tuple[Path, ExperimentConfig | None]:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    analysis = analyze_stage_a_stage(run_root, resolved)
    if not verify_seal(analysis):
        raise RuntimeError("Stage A analysis does not verify")
    gate = read_json(analysis / "gate.json")
    selected = gate.get("selected_authority_scale")
    stage_b_config = (
        with_stage_b_choices(
            resolved,
            float(selected),
            float(resolved.selected_epistemic_coefficient),
        )
        if gate.get("passed") is True
        else None
    )
    manifest: dict[str, Any] = {
        "schema": STAGE_B_REGISTRATION_SCHEMA,
        "parent_registration_id": read_json(registration_path(run_root, config.profile))["registration_id"],
        "stage_a_analysis_seal": sha256_file(analysis / "seal.json"),
        "stage_a_gate": gate,
        "action": "RUN" if stage_b_config is not None else "STOP",
        "config": None if stage_b_config is None else stage_b_config.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "created_without_manual_choice": True,
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = stage_b_registration_path(run_root, config.profile)
    if path.is_file():
        if read_json(path) != manifest:
            raise RuntimeError("existing Stage B registration differs from mechanical gate")
        return path, stage_b_config
    write_json(path, manifest)
    return path, stage_b_config


def verify_stage_b_registration(run_root: Path, config: ExperimentConfig) -> ExperimentConfig | None:
    path, resolved = register_stage_b(run_root, config)
    payload = read_json(path)
    if payload.get("schema") != STAGE_B_REGISTRATION_SCHEMA:
        raise RuntimeError("Stage B registration schema mismatch")
    if payload.get("sources") != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("Stage B registered source has drifted")
    return resolved


def stage_b_stage(run_root: Path, config: ExperimentConfig) -> Path | None:
    resolved = verify_stage_b_registration(run_root, config)
    if resolved is None:
        return None
    return _simulate(
        run_root,
        resolved,
        "stage-b",
        stage_b_conditions(_screen_root(), float(resolved.selected_authority_scale)),
        resolved.stage_b_matrices,
    )


def replay_stage_b(run_root: Path, config: ExperimentConfig) -> Path | None:
    resolved = verify_stage_b_registration(run_root, config)
    if resolved is None:
        return None
    return _replay(
        run_root,
        resolved,
        "stage-b",
        "stage-b-replay",
        stage_b_conditions(_screen_root(), float(resolved.selected_authority_scale)),
        resolved.stage_b_matrices,
    )


def analyze_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    stage_b_config = verify_stage_b_registration(run_root, resolved)
    if stage_b_config is not None:
        replay = root / "stage-b-replay"
        if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
            raise RuntimeError("Stage B exact replay must pass before final analysis")
    output = root / "analysis"
    if verify_seal(output):
        return output
    _deadline(run_root, resolved)
    analyze_final(
        stage_b_config or resolved,
        root / "stage-a-analysis",
        root / "stage-b" if stage_b_config is not None else None,
        output,
    )
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
    stage_a_stage(run_root, resolved)
    replay_stage_a(run_root, resolved)
    analyze_stage_a_stage(run_root, resolved)
    _stage_b_path, stage_b_config = register_stage_b(run_root, resolved)
    if stage_b_config is not None:
        stage_b_stage(run_root, stage_b_config)
        replay_stage_b(run_root, stage_b_config)
    return analyze_stage(run_root, stage_b_config or resolved)


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
        "stage_a": seal_present(root / "stage-a"),
        "stage_a_replay": seal_present(root / "stage-a-replay"),
        "stage_a_analysis": seal_present(root / "stage-a-analysis"),
        "stage_b_registered": (root / "stage-b-registration.json").is_file(),
        "stage_b": seal_present(root / "stage-b"),
        "stage_b_replay": seal_present(root / "stage-b-replay"),
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
        ("stage_a", "stage-a"),
        ("stage_a_replay", "stage-a-replay"),
        ("stage_a_analysis", "stage-a-analysis"),
        ("stage_b_registered", "stage-b-registration"),
        ("stage_b", "stage-b"),
        ("stage_b_replay", "stage-b-replay"),
        ("analysis", "analysis"),
    )
    stage_b_stopped = False
    if stages["stage_b_registered"]:
        stage_b_stopped = read_json(root / "stage-b-registration.json").get("action") == "STOP"
    output["stage_b_stopped"] = stage_b_stopped
    output["current_stage"] = "complete" if stages["analysis"] else next(
        (
            label
            for key, label in ordered
            if not stages[key]
            and not (stage_b_stopped and key in ("stage_b", "stage_b_replay"))
        ),
        "analysis",
    )
    if (root / "clock.json").is_file():
        elapsed = elapsed_seconds(run_root, config)
        output.update(
            {
                "elapsed_seconds": elapsed,
                "hard_remaining_seconds": max(0.0, config.wall_time_limit_seconds - elapsed),
                "time_budget_state": (
                    "TIME_BUDGET_EXHAUSTED_NO_VERDICT"
                    if elapsed >= config.wall_time_limit_seconds and not stages["analysis"]
                    else "complete"
                    if stages["analysis"]
                    else "within_budget"
                ),
            }
        )
    if stages["registered"]:
        registration = read_json(root / "registration.json")
        output["registration_id"] = registration["registration_id"]
        output["resource_ceiling_workers"] = registration.get(
            "resource_ceiling_workers", MAX_WORKERS
        )
        output["reduced_power_scale"] = bool(
            registration.get("reduced_power_scale", False)
        )
        output["registered_source_current"] = registration.get("sources") == source_manifest(
            PROJECT_ROOT, _source_files()
        )
        resolved = _config_from_manifest(registration)
        output["selected_scale_pair"] = [resolved.stage_a_matrices, resolved.stage_b_matrices]
        output["expected_stage_a_cells"] = resolved.stage_a_matrices * 10
        output["stage_a_cells_present"] = len(list((root / "stage-a" / "cells").glob("*.json")))
        output["expected_stage_b_cells"] = resolved.stage_b_matrices * 4
        output["stage_b_cells_present"] = len(list((root / "stage-b" / "cells").glob("*.json")))
        output["stage_a_fraction"] = (
            output["stage_a_cells_present"] / output["expected_stage_a_cells"]
        )
        output["stage_b_fraction"] = (
            output["stage_b_cells_present"] / output["expected_stage_b_cells"]
        )
        if stages["benchmark"] and (root / "clock.json").is_file():
            benchmark = read_json(root / "benchmark" / "benchmark.json")
            pair_key = f"{resolved.stage_a_matrices},{resolved.stage_b_matrices}"
            projection = benchmark.get("projections", {}).get(pair_key)
            if projection is not None:
                projected_total = float(projection["total_from_clock_start_seconds"])
                elapsed = elapsed_seconds(run_root, config)
                remaining = 0.0 if stages["analysis"] else max(
                    0.0, projected_total - elapsed
                )
                output["projected_total_seconds"] = projected_total
                output["projected_remaining_seconds"] = remaining
                output["projected_completion_utc"] = datetime.fromtimestamp(
                    time.time() + remaining, timezone.utc
                ).isoformat()
    if stages["stage_a_analysis"]:
        output["stage_a_gate"] = read_json(root / "stage-a-analysis" / "gate.json")
    if stages["analysis"]:
        output.update(read_json(root / "analysis" / "metrics.json")["decision"])
    for suffix in ("status", "pid", "started", "finished", "session"):
        path = root / f"fep-ph17.{suffix}"
        output[f"runner_{suffix}"] = path.read_text(encoding="utf-8").strip() if path.is_file() else None
    try:
        pid = int(output.get("runner_pid") or -1)
        if pid <= 0:
            raise ValueError
        os.kill(pid, 0)
        output["runner_alive"] = True
    except (ValueError, OSError):
        output["runner_alive"] = False
    return output
