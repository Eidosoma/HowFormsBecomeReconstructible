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
from fep_ph18.campaign import _array_digest, _cell_complete, _save_npz

from .analysis import analyze_final, analyze_stage_a
from .causal_pomdp import (
    fit_exact_model,
    load_model as load_exact_model,
    model_digest as exact_digest,
    save_model as save_exact_model,
)
from .config import (
    MAX_WORKERS,
    SCALE_PAIRS,
    ExperimentConfig,
    profile_config,
    with_selected_scales,
)
from .data import (
    cohort_seed_domains,
    development_cell,
    development_conditions,
    stage_a_conditions,
    stage_b_conditions,
)
from .recurrent_model import (
    fit_recurrent_model,
    load_model as load_recurrent_model,
    load_sequence_corpus,
    model_digest as recurrent_digest,
    save_model as save_recurrent_model,
)
from .types import CellSpec, ConditionSpec, ObservationThresholds
from .validation import validate_experiment
from .worker import (
    exact_model_path,
    generate_evaluation_cell,
    legacy_model_path,
    recurrent_model_path,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_REGISTRATION_SCHEMA = "fep-ph19-development-registration-v1"
EVALUATION_REGISTRATION_SCHEMA = "fep-ph19-evaluation-registration-v1"
STAGE_B_REGISTRATION_SCHEMA = "fep-ph19-stage-b-registration-v1"


def profile_root(run_root: Path, profile: str) -> Path:
    return Path(run_root) / profile


def _source_files() -> list[Path]:
    paths = list((PROJECT_ROOT / "fep_ph19").glob("*.py"))
    paths.extend((PROJECT_ROOT / "fep_ph18").glob("*.py"))
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
        "EXPERIMENT_FEP_PH19_PROTOCOL.md",
        "requirements-fep-lab-lock.txt",
        "scripts/run_fep_ph19_campaign.sh",
        "scripts/run_fep_ph19_detached.sh",
        "scripts/status_fep_ph19.sh",
        "scripts/control_fep_ph19.sh",
    ):
        path = PROJECT_ROOT / name
        if path.is_file():
            paths.append(path)
    return sorted(path for path in paths if path.is_file())


def _source_digest() -> str:
    return sha256_bytes(canonical_json_bytes(source_manifest(PROJECT_ROOT, _source_files())))


def _registered_sources_current(registration: Path) -> bool:
    sources = read_json(registration).get("sources", {})
    return bool(sources) and all(
        (PROJECT_ROOT / relative).is_file()
        and sha256_file(PROJECT_ROOT / relative) == expected
        for relative, expected in sources.items()
    )


def _screen_root() -> Path:
    return PROJECT_ROOT / "runs-fep-ph15" / "full" / "screen"


def _prior_dependencies() -> dict[str, str]:
    experiment15 = PROJECT_ROOT / "runs-fep-ph15" / "full"
    experiment18 = PROJECT_ROOT / "runs-fep-ph18" / "full"
    required = {
        "fep_ph15_screen_seal": experiment15 / "screen" / "seal.json",
        "fep_ph15_screen_replay_seal": experiment15 / "screen-replay" / "seal.json",
        "fep_ph18_registration": experiment18 / "registration.json",
        "fep_ph18_development_replay_seal": experiment18 / "development-replay" / "seal.json",
        "fep_ph18_fit_replay_seal": experiment18 / "fit-replay" / "seal.json",
        "fep_ph18_stage_a_replay_seal": experiment18 / "stage-a-replay" / "seal.json",
        "fep_ph18_stage_b_replay_seal": experiment18 / "stage-b-replay" / "seal.json",
        "fep_ph18_analysis_seal": experiment18 / "analysis" / "seal.json",
        "fep_ph18_metrics": experiment18 / "analysis" / "metrics.json",
        "fep_ph18_legacy_model": legacy_model_path(),
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing sealed FEP–PH1.9 prerequisites: {missing}")
    for label, directory in (
        ("FEP-PH1.5 screen", experiment15 / "screen"),
        ("FEP-PH1.5 screen replay", experiment15 / "screen-replay"),
        ("FEP-PH1.8 development replay", experiment18 / "development-replay"),
        ("FEP-PH1.8 fit replay", experiment18 / "fit-replay"),
        ("FEP-PH1.8 Stage A replay", experiment18 / "stage-a-replay"),
        ("FEP-PH1.8 Stage B replay", experiment18 / "stage-b-replay"),
        ("FEP-PH1.8 analysis", experiment18 / "analysis"),
    ):
        if not verify_seal(directory):
            raise RuntimeError(f"{label} dependency seal does not verify")
    if read_json(experiment15 / "screen-replay" / "replay.json").get("all_exact") is not True:
        raise RuntimeError("FEP-PH1.5 screen replay is not exact")
    for name in ("development-replay", "fit-replay", "stage-a-replay", "stage-b-replay"):
        if read_json(experiment18 / name / "replay.json").get("all_exact") is not True:
            raise RuntimeError(f"FEP-PH1.8 {name} is not exact")
    decision = read_json(experiment18 / "analysis" / "metrics.json").get("decision", {})
    if decision.get("integrity_verdict") != "VALID":
        raise RuntimeError("FEP-PH1.8 integrity prerequisite is not valid")
    if decision.get("scientific_status") != "HYPOTHESIS_NOT_SUPPORTED":
        raise RuntimeError("FEP-PH1.8 scientific prerequisite has changed")
    return {name: sha256_file(path) for name, path in sorted(required.items())}


def _clock_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "clock.json"


def ensure_clock(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    path = _clock_path(run_root, config.profile)
    if path.is_file():
        return read_json(path)
    now = time.time()
    payload = {
        "schema": "fep-ph19-wall-clock-v1",
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
            f"FEP-PH1.9 graceful stop reached after {elapsed:.1f} seconds"
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


def validate_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    ensure_clock(run_root, config)
    _prior_dependencies()
    output = profile_root(run_root, config.profile) / "validation"
    if verify_seal(output):
        return read_json(output / "validation.json")
    result = validate_experiment(config, _screen_root())
    if result.get("all_passed") is not True:
        raise RuntimeError("FEP-PH1.9 validation failed")
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
        "development_only_uses_true_regime_for_causal_qualification": True,
        "runtime_feature_firewall": [
            "true_regime",
            "beta",
            "rng_state",
            "future_outcomes",
            "f12",
            "strict8",
        ],
        "evaluation_outcomes_available": False,
        "clock": read_json(_clock_path(run_root, config.profile)),
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = development_registration_path(run_root, config.profile)
    if path.is_file():
        if canonical_json_bytes(read_json(path)) != canonical_json_bytes(manifest):
            raise RuntimeError("existing development registration differs from contract")
        return path
    write_json(path, manifest)
    return path


def verify_development_registration(run_root: Path, config: ExperimentConfig) -> None:
    path = development_registration_path(run_root, config.profile)
    if not path.is_file():
        raise FileNotFoundError(f"missing development registration {path}")
    payload = read_json(path)
    if payload.get("sources") != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("development-registered source has drifted")
    if payload.get("dependencies") != dependency_versions():
        raise RuntimeError("development dependencies have drifted")
    if payload.get("prior_dependencies") != _prior_dependencies():
        raise RuntimeError("prior dependencies have drifted")


def _development_paths(output: Path, condition: ConditionSpec) -> tuple[Path, Path]:
    return output / "cells" / f"{condition.key}.npz", output / "cells" / f"{condition.key}.json"


def _development_task(
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
    for index, paths in enumerate(_map_tasks(_development_task, arguments, config.workers), start=1):
        _deadline(run_root, config)
        sealed.extend(str(Path(path).relative_to(output)) for path in paths)
        print(f"[development] conditions {index}/{len(arguments)}", flush=True)
    seal_directory(output, sealed)
    return output


def _development_replay_task(
    argument: tuple[ExperimentConfig, ConditionSpec, Path]
) -> dict[str, Any]:
    config, condition, simulation = argument
    _data, metadata = _development_paths(simulation, condition)
    expected = read_json(metadata)
    arrays, payload = development_cell(config, condition)
    return {
        "condition": condition.key,
        "array_exact": _array_digest(arrays) == expected["array_digest"],
        "metadata_exact": payload == {key: expected[key] for key in payload},
    }


def replay_development_stage(run_root: Path, config: ExperimentConfig) -> Path:
    root = profile_root(run_root, config.profile)
    simulation = development_stage(run_root, config)
    output = root / "development-replay"
    if verify_seal(output):
        return output
    arguments = [
        (config, condition, simulation)
        for condition in development_conditions(_screen_root())
    ]
    results = []
    for index, result in enumerate(
        _map_tasks(_development_replay_task, arguments, config.workers), start=1
    ):
        _deadline(run_root, config)
        results.append(result)
        print(f"[development-replay] conditions {index}/{len(arguments)}", flush=True)
    exact = all(value["array_exact"] and value["metadata_exact"] for value in results)
    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "replay.json",
        {"schema": "fep-ph19-development-replay-v1", "cells": results, "all_exact": exact},
    )
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError("FEP-PH1.9 development replay failed")
    return output


def _load_development_cells(
    directory: Path,
) -> list[tuple[dict[str, np.ndarray], dict[str, Any]]]:
    cells = []
    for path in sorted((directory / "cells").glob("*.npz")):
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        cells.append((arrays, read_json(path.with_suffix(".json"))))
    if not cells:
        raise RuntimeError("sealed development directory contains no cells")
    return cells


def fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    root = profile_root(run_root, config.profile)
    replay = replay_development_stage(run_root, config)
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("development must replay exactly before model fitting")
    output = root / "fit"
    if verify_seal(output):
        return output
    development = root / "development"
    cells = _load_development_cells(development)
    exact = fit_exact_model(cells, config)
    corpus = load_sequence_corpus(sorted((development / "cells").glob("*.npz")), config)
    recurrent = fit_recurrent_model(
        corpus,
        config,
        exact_action_concordance=float(exact.qualification["action_order_concordance"]),
    )
    save_exact_model(exact_model_path(output), exact)
    save_recurrent_model(recurrent_model_path(output), recurrent)
    qualification = {
        "schema": "fep-ph19-model-qualification-v1",
        "exact": exact.qualification,
        "recurrent": recurrent.qualification,
        "full_evaluation_requires_exact": True,
        "recurrent_entry_is_conditional": True,
        "workflow_only_overrides": config.profile != "full",
        "uses_evaluation_outcomes": False,
    }
    write_json(output / "model-qualification.json", qualification)
    summary = {
        "schema": "fep-ph19-model-summary-v1",
        "exact_digest": exact_digest(exact),
        "recurrent_digest": recurrent_digest(recurrent),
        "legacy_ph18_digest": sha256_file(legacy_model_path()),
        "exact_qualified": bool(exact.qualification.get("qualified")),
        "recurrent_qualified": bool(recurrent.qualification.get("qualified")),
    }
    write_json(output / "model-summary.json", summary)
    files = [
        str(exact_model_path(output).relative_to(output)),
        str(recurrent_model_path(output).relative_to(output)),
        "model-qualification.json",
        "model-summary.json",
    ]
    seal_directory(output, files)
    return output


def replay_fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    root = profile_root(run_root, config.profile)
    fit = fit_stage(run_root, config)
    output = root / "fit-replay"
    if verify_seal(output):
        return output
    development = root / "development"
    cells = _load_development_cells(development)
    exact = fit_exact_model(cells, config)
    recurrent = fit_recurrent_model(
        load_sequence_corpus(sorted((development / "cells").glob("*.npz")), config),
        config,
        exact_action_concordance=float(exact.qualification["action_order_concordance"]),
    )
    expected_exact = load_exact_model(exact_model_path(fit))
    expected_recurrent = load_recurrent_model(recurrent_model_path(fit))
    result = {
        "schema": "fep-ph19-fit-replay-v1",
        "exact_digest_expected": exact_digest(expected_exact),
        "exact_digest_replayed": exact_digest(exact),
        "recurrent_digest_expected": recurrent_digest(expected_recurrent),
        "recurrent_digest_replayed": recurrent_digest(recurrent),
    }
    result["all_exact"] = bool(
        result["exact_digest_expected"] == result["exact_digest_replayed"]
        and result["recurrent_digest_expected"] == result["recurrent_digest_replayed"]
    )
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "replay.json", result)
    seal_directory(output, ["replay.json"])
    if not result["all_exact"]:
        raise RuntimeError("FEP-PH1.9 fitted-model exact replay failed")
    return output


def benchmark_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    root = profile_root(run_root, config.profile)
    fit = fit_stage(run_root, config)
    replay = replay_fit_stage(run_root, config)
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("model replay must be exact before benchmarking")
    qualification = read_json(fit / "model-qualification.json")
    if config.profile == "full" and qualification["exact"].get("qualified") is not True:
        raise RuntimeError("EXACT_CAUSAL_MODEL_NOT_QUALIFIED")
    output = root / "benchmark"
    if verify_seal(output):
        payload = read_json(output / "benchmark.json")
        if payload.get("source_digest") != _source_digest():
            raise RuntimeError("sealed benchmark belongs to different source")
        return payload
    timing_seed = sha256_bytes(f"{config.master_seed}.fep_ph19.disposable-timing".encode())
    timed = replace(config, master_seed=timing_seed, branches=1, horizon=min(4, config.horizon))
    stage_a_condition = stage_a_conditions(_screen_root())[0]
    stage_b_all = stage_b_conditions(_screen_root())
    representatives = [
        next(
            value
            for value in stage_b_all
            if value.candidate == "02"
            and value.switch_probability == 0.15
            and value.information_arm == "informative"
            and value.sensing_timing == timing
        )
        for timing in ("same-cycle", "delayed")
    ]
    started = time.perf_counter()
    generate_evaluation_cell(
        timed, CellSpec(90_001, stage_a_condition), fit, ObservationThresholds()
    )
    stage_a_short = time.perf_counter() - started
    stage_b_short = []
    for index, condition in enumerate(representatives):
        started = time.perf_counter()
        generate_evaluation_cell(
            timed, CellSpec(90_010 + index, condition), fit, ObservationThresholds()
        )
        stage_b_short.append(time.perf_counter() - started)
    stage_a_scaled = stage_a_short * config.horizon / timed.horizon * config.branches
    stage_b_scaled = max(stage_b_short) * config.horizon / timed.horizon * config.branches
    pairs = SCALE_PAIRS if config.profile == "full" else ((config.stage_a_matrices, config.stage_b_matrices),)
    elapsed = elapsed_seconds(run_root, config)
    projections: dict[str, dict[str, Any]] = {}
    selected: tuple[int, int] | None = None
    for stage_a_scale, stage_b_scale in pairs:
        cells_a = stage_a_scale * len(stage_a_conditions(_screen_root()))
        cells_b = stage_b_scale * len(stage_b_conditions(_screen_root()))
        ideal = 2.0 * (cells_a * stage_a_scaled + cells_b * stage_b_scaled) / max(1, config.workers)
        fixed = 480.0 if config.profile == "full" else 90.0 if config.profile == "quick" else 20.0
        remaining = 1.50 * ideal + fixed
        key = f"{stage_a_scale},{stage_b_scale}"
        projections[key] = {
            "stage_a_matrices": stage_a_scale,
            "stage_b_matrices": stage_b_scale,
            "stage_a_cells": cells_a,
            "stage_b_cells": cells_b,
            "remaining_seconds": remaining,
            "total_from_clock_start_seconds": elapsed + remaining,
        }
        if selected is None and elapsed + remaining <= config.registration_projection_ceiling_seconds:
            selected = (stage_a_scale, stage_b_scale)
            break
    result = {
        "schema": "fep-ph19-benchmark-v1",
        "profile": config.profile,
        "benchmark_seed_domain": "disposable_timing_not_scientific_cohorts",
        "benchmark_master_seed": timing_seed,
        "short_horizon": timed.horizon,
        "full_horizon": config.horizon,
        "whole_cell_seconds": {
            "stage_a": stage_a_short,
            "stage_b": stage_b_short,
        },
        "horizon_scaled_cell_seconds": {
            "stage_a": stage_a_scaled,
            "stage_b": stage_b_scaled,
        },
        "workers": config.workers,
        "elapsed_before_benchmark_seconds": elapsed,
        "projections": projections,
        "registration_eligible": selected is not None,
        "selected_scale_pair": list(selected) if selected else None,
        "registration_projection_ceiling_seconds": config.registration_projection_ceiling_seconds,
        "hard_wall_time_seconds": config.wall_time_limit_seconds,
        "source_digest": _source_digest(),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "benchmark.json", result)
    seal_directory(output, ["benchmark.json"])
    if selected is None:
        raise RuntimeError("minimum PH1.9 scale projects beyond the eight-hour contract")
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
    for name in ("development", "development-replay", "fit", "fit-replay", "benchmark"):
        if not verify_seal(root / name):
            raise RuntimeError(f"{name} dependency seal does not verify")
    return {name: sha256_file(path) for name, path in paths.items()}


def register(run_root: Path, config: ExperimentConfig) -> tuple[Path, ExperimentConfig]:
    benchmark = benchmark_stage(run_root, config)
    if benchmark.get("registration_eligible") is not True:
        raise RuntimeError("sealed timing benchmark refused evaluation registration")
    stage_a_scale, stage_b_scale = (int(value) for value in benchmark["selected_scale_pair"])
    resolved = with_selected_scales(config, stage_a_scale, stage_b_scale)
    fit = profile_root(run_root, config.profile) / "fit"
    qualification = read_json(fit / "model-qualification.json")
    if config.profile == "full" and qualification["exact"].get("qualified") is not True:
        raise RuntimeError("exact causal model cannot register evaluation")
    manifest: dict[str, Any] = {
        "schema": EVALUATION_REGISTRATION_SCHEMA,
        "config": resolved.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "runtime": runtime_manifest(),
        "prior_dependencies": _prior_dependencies(),
        "development_dependencies": _development_dependencies(run_root, config.profile),
        "model_qualification": qualification,
        "primary_outcome": "inherited_completion_fraction",
        "global_classifier": False,
        "same_cycle_is_primary": True,
        "delayed_control_probability": 0.15,
        "resource_ceiling_workers": MAX_WORKERS,
        "clock": read_json(_clock_path(run_root, config.profile)),
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = registration_path(run_root, config.profile)
    if path.is_file():
        if canonical_json_bytes(read_json(path)) != canonical_json_bytes(manifest):
            raise RuntimeError("existing evaluation registration differs from contract")
        return path, resolved
    write_json(path, manifest)
    return path, resolved


def _config_from_manifest(payload: dict[str, Any]) -> ExperimentConfig:
    allowed = {field.name for field in fields(ExperimentConfig)}
    values = {key: value for key, value in payload["config"].items() if key in allowed}
    if isinstance(values.get("gard"), dict):
        values["gard"] = GardConfig(**values["gard"])
    for name in ("rff_widths", "planner_depths"):
        if isinstance(values.get(name), list):
            values[name] = tuple(values[name])
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
    return output / "cells" / f"{cell.stem}.npz", output / "cells" / f"{cell.stem}.json"


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
    arguments = [
        (config, CellSpec(matrix_id, condition), root / "fit", ObservationThresholds(), output)
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
    arguments = [
        (config, CellSpec(matrix_id, condition), root / "fit", ObservationThresholds(), simulation)
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
        {"schema": f"fep-ph19-{replay_name}-v1", "cells": results, "all_exact": exact},
    )
    seal_directory(output, ["replay.json"])
    if not exact:
        raise RuntimeError(f"FEP-PH1.9 {replay_name} exact replay failed")
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
        raise RuntimeError("Stage A must replay exactly before headroom analysis")
    output = root / "stage-a-analysis"
    if verify_seal(output):
        return output
    analyze_stage_a(resolved, root / "stage-a", output)
    return output


def stage_b_registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "stage-b-registration.json"


def register_stage_b(
    run_root: Path, config: ExperimentConfig
) -> tuple[Path, ExperimentConfig | None]:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    analysis = analyze_stage_a_stage(run_root, resolved)
    gate = read_json(analysis / "gate.json")
    stage_b_config = resolved if gate.get("passed") is True else None
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
        if canonical_json_bytes(read_json(path)) != canonical_json_bytes(manifest):
            raise RuntimeError("existing Stage B registration differs from the mechanical gate")
        return path, stage_b_config
    write_json(path, manifest)
    return path, stage_b_config


def verify_stage_b_registration(
    run_root: Path, config: ExperimentConfig
) -> ExperimentConfig | None:
    path, resolved = register_stage_b(run_root, config)
    payload = read_json(path)
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
        stage_b_conditions(_screen_root()),
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
        stage_b_conditions(_screen_root()),
        resolved.stage_b_matrices,
    )


def analyze_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    stage_b_config = verify_stage_b_registration(run_root, resolved)
    output = root / "analysis"
    if verify_seal(output):
        return output
    if stage_b_config is None:
        output.mkdir(parents=True, exist_ok=True)
        decision = {
            "integrity_verdict": "VALID",
            "scientific_status": "HEADROOM_GATE_STOPPED",
            "global_classifier": None,
            "claim_boundary": "Fresh sensing/action headroom was not demonstrated, so selective sensing was not evaluated.",
        }
        write_json(
            output / "metrics.json",
            {"schema": "fep-ph19-final-analysis-v1", "decision": decision, "component_tests": {}},
        )
        (output / "REPORT.md").write_text(
            "# FEP–PH1.9 final report\n\nStage B stopped mechanically because Stage A did not demonstrate fresh sensing/action headroom.\n",
            encoding="utf-8",
        )
        seal_directory(output, ["metrics.json", "REPORT.md"])
        return output
    replay = root / "stage-b-replay"
    if not verify_seal(replay) or read_json(replay / "replay.json").get("all_exact") is not True:
        raise RuntimeError("Stage B must replay exactly before final analysis")
    analyze_final(
        stage_b_config,
        root / "stage-b",
        output,
        fit_root=root / "fit",
        integrity_valid=_registered_sources_current(registration_path(run_root, config.profile)),
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
    _path, stage_b_config = register_stage_b(run_root, resolved)
    if stage_b_config is not None:
        stage_b_stage(run_root, stage_b_config)
        replay_stage_b(run_root, stage_b_config)
    return analyze_stage(run_root, stage_b_config or resolved)


def status(run_root: Path, profile: str) -> dict[str, Any]:
    root = profile_root(run_root, profile)
    stages = {
        name.replace("-", "_"): verify_seal(root / name)
        for name in (
            "validation",
            "development",
            "development-replay",
            "fit",
            "fit-replay",
            "benchmark",
            "stage-a",
            "stage-a-replay",
            "stage-a-analysis",
            "stage-b",
            "stage-b-replay",
            "analysis",
        )
    }
    order = (
        "validation",
        "development",
        "development_replay",
        "fit",
        "fit_replay",
        "benchmark",
        "stage_a",
        "stage_a_replay",
        "stage_a_analysis",
        "stage_b",
        "stage_b_replay",
        "analysis",
    )
    output: dict[str, Any] = {
        "profile": profile,
        **stages,
        "current_stage": "complete" if stages["analysis"] else next(
            (name.replace("_", "-") for name in order if not stages[name]), "unknown"
        ),
    }
    clock_path = root / "clock.json"
    if clock_path.is_file():
        clock = read_json(clock_path)
        clock_elapsed = max(0.0, time.time() - float(clock["started_epoch"]))
        hard_wall = float(clock["hard_wall_time_seconds"])
        output["elapsed_seconds"] = clock_elapsed
        output["hard_remaining_seconds"] = max(0.0, hard_wall - clock_elapsed)
    benchmark_path = root / "benchmark" / "benchmark.json"
    if benchmark_path.is_file():
        benchmark = read_json(benchmark_path)
        output["benchmark_registration_eligible"] = benchmark.get(
            "registration_eligible"
        )
        output["benchmark_selected_scale_pair"] = benchmark.get(
            "selected_scale_pair"
        )
        selected = benchmark.get("selected_scale_pair")
        if isinstance(selected, list) and len(selected) == 2:
            key = f"{int(selected[0])},{int(selected[1])}"
            projection = benchmark.get("projections", {}).get(key, {})
            projected_total = projection.get("total_from_clock_start_seconds")
            if projected_total is not None:
                output["projected_total_seconds"] = float(projected_total)
                output["projected_remaining_seconds"] = max(
                    0.0,
                    float(projected_total) - float(output.get("elapsed_seconds", 0.0)),
                )
    registration = registration_path(run_root, profile)
    if registration.is_file():
        payload = read_json(registration)
        output["registration_id"] = payload.get("registration_id")
        output["registered_source_current"] = _registered_sources_current(registration)
        config = _config_from_manifest(payload)
        output["selected_scale_pair"] = [config.stage_a_matrices, config.stage_b_matrices]
        output["expected_stage_a_cells"] = config.stage_a_matrices * 6
        output["expected_stage_b_cells"] = config.stage_b_matrices * 16
        output["stage_a_cells_present"] = len(list((root / "stage-a" / "cells").glob("*.json")))
        output["stage_b_cells_present"] = len(list((root / "stage-b" / "cells").glob("*.json")))
        output["stage_a_cell_fraction"] = (
            output["stage_a_cells_present"] / output["expected_stage_a_cells"]
        )
        output["stage_b_cell_fraction"] = (
            output["stage_b_cells_present"] / output["expected_stage_b_cells"]
        )
    if (root / "fit" / "model-qualification.json").is_file():
        output["model_qualification"] = read_json(root / "fit" / "model-qualification.json")
    if (root / "stage-a-analysis" / "gate.json").is_file():
        output["stage_a_gate"] = read_json(root / "stage-a-analysis" / "gate.json")
    if (root / "analysis" / "metrics.json").is_file():
        output.update(read_json(root / "analysis" / "metrics.json").get("decision", {}))
    for suffix in ("status", "pid", "started", "finished", "service", "session"):
        path = root / f"fep-ph19.{suffix}"
        output[f"runner_{suffix}"] = path.read_text(encoding="utf-8").strip() if path.is_file() else None
    return output


__all__ = (
    "analyze_stage",
    "analyze_stage_a_stage",
    "benchmark_stage",
    "develop_register",
    "development_stage",
    "fit_stage",
    "register",
    "register_stage_b",
    "replay_development_stage",
    "replay_fit_stage",
    "replay_stage_a",
    "replay_stage_b",
    "run_all",
    "stage_a_stage",
    "stage_b_stage",
    "status",
    "validate_stage",
)
