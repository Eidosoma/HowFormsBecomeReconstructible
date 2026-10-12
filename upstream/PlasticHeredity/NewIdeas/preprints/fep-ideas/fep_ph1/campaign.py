from __future__ import annotations

import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import fields
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

from .analysis import analyze_atlas
from .config import ExperimentConfig, profile_config, with_selected_scale
from .models import model_digest, save_model
from .types import ObservationThresholds
from .validation import validate_experiment
from .worker import (
    CellSpec,
    ConditionSpec,
    conditions,
    fit_pooled_condition,
    generate_evaluation_cell,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "fep-ph1-registration-v1"


def profile_root(run_root: Path, profile: str) -> Path:
    return Path(run_root) / profile


def _source_files() -> list[Path]:
    paths = list((PROJECT_ROOT / "fep_ph1").glob("*.py"))
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
        "EXPERIMENT_FEP_PH1_PROTOCOL.md",
        "requirements-fep-lab-lock.txt",
    ):
        path = PROJECT_ROOT / name
        if path.is_file():
            paths.append(path)
    return sorted(path for path in paths if path.is_file())


def _stage0_dependency() -> dict[str, str]:
    root = PROJECT_ROOT / "runs-fep-lab" / "full"
    metrics = root / "analysis" / "metrics.json"
    seal = root / "analysis" / "seal.json"
    replay = root / "replay" / "seal.json"
    if not (metrics.is_file() and seal.is_file() and replay.is_file()):
        raise RuntimeError("missing sealed full Stage 0 validation dependency")
    payload = read_json(metrics)
    if payload.get("verdict") != "VALIDATION_PASS":
        raise RuntimeError("Stage 0 dependency did not pass validation")
    return {
        "metrics_sha256": sha256_file(metrics),
        "analysis_seal_sha256": sha256_file(seal),
        "replay_seal_sha256": sha256_file(replay),
    }


def _current_source_digest() -> str:
    return sha256_bytes(
        canonical_json_bytes(source_manifest(PROJECT_ROOT, _source_files()))
    )


def _array_digest(arrays: dict[str, np.ndarray]) -> str:
    digest: list[bytes] = []
    for name in sorted(arrays):
        value = np.ascontiguousarray(arrays[name])
        digest.extend(
            (
                name.encode("utf-8"),
                str(value.shape).encode("ascii"),
                value.dtype.str.encode("ascii"),
                value.tobytes(),
            )
        )
    return sha256_bytes(b"".join(digest))


def _save_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}.npz")
    np.savez_compressed(temporary, **arrays)
    temporary.replace(path)


def _cell_complete(data_path: Path, manifest_path: Path) -> bool:
    if not data_path.is_file() or not manifest_path.is_file():
        return False
    manifest = read_json(manifest_path)
    if manifest.get("file_sha256") != sha256_file(data_path):
        return False
    with np.load(data_path, allow_pickle=False) as archive:
        digest = _array_digest({name: archive[name] for name in archive.files})
    return digest == manifest.get("array_digest")


def _deadline(started: float, config: ExperimentConfig) -> None:
    elapsed = time.monotonic() - started
    if elapsed >= config.graceful_stop_seconds:
        raise TimeoutError(
            f"FEP-PH1 graceful stop after {elapsed:.1f}s; rerun to resume"
        )


def validate_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    output = profile_root(run_root, config.profile) / "validation"
    current_digest = _current_source_digest()
    if verify_seal(output):
        result = read_json(output / "validation.json")
        if result.get("source_digest") != current_digest:
            raise RuntimeError("sealed FEP-PH1 validation belongs to different source")
        return result
    return validate_experiment(config, output, current_digest)


def _benchmark_episode_seconds(
    config: ExperimentConfig, controller_name: str = "ai_pooled"
) -> float:
    from .gard import generate_beta, generate_initial_composition
    from .models import ModelCounts, model_from_counts, reward_only, reversed_preferences, scrambled_model
    from .simulation import controller_for, run_episode
    from .types import ActionChannel, ControllerName, EnvironmentFamily
    from .worker import environment_design

    probe = with_selected_scale(config, max(1, config.evaluation_matrices))
    counts = ModelCounts.empty()
    for state in range(9):
        observation = (state % 4, state % 3, state % 3, state % 4)
        counts.add_initial(state, observation)
        for action in range(4):
            counts.add_transition(state, action, (state + action + 1) % 9, observation)
    model = model_from_counts(counts, probe)
    condition = next(
        item
        for item in conditions()
        if item.candidate == "02"
        and item.family == EnvironmentFamily.NUTRIENT
        and item.channel == ActionChannel.UPTAKE
        and item.regime.severity_index == 2
    )
    design = environment_design(probe, condition, 0)
    beta = generate_beta(probe.gard, np.random.default_rng(771))
    initial = generate_initial_composition(probe.gard, np.random.default_rng(772))
    variants = {
        "reward_pooled": reward_only(model),
        "reward_local": reward_only(model),
        "scrambled": scrambled_model(model, 773),
        "reversed": reversed_preferences(model),
    }
    selected_name = ControllerName(controller_name)
    short = ExperimentConfig(
        **{
            **{field.name: getattr(probe, field.name) for field in fields(probe)},
            "horizon": min(8, probe.horizon),
        }
    )
    timings = []
    for repetition in range(3):
        controller = controller_for(
            selected_name, probe, model, model, variants
        )
        started = time.perf_counter()
        run_episode(
            short,
            design,
            beta,
            initial,
            ObservationThresholds(),
            selected_name,
            controller,
            (774, 775, 776),
            777 + repetition,
        )
        timings.append((time.perf_counter() - started) / short.horizon)
    return float(np.median(timings))


def benchmark_stage(run_root: Path, config: ExperimentConfig) -> dict[str, Any]:
    output = profile_root(run_root, config.profile) / "benchmark"
    if verify_seal(output):
        return read_json(output / "benchmark.json")
    output.mkdir(parents=True, exist_ok=True)
    active_seconds_per_fission = _benchmark_episode_seconds(config, "ai_pooled")
    simple_seconds_per_fission = _benchmark_episode_seconds(config, "noop")
    scales = (128, 96, 64) if config.profile == "full" else (config.evaluation_matrices,)
    projections: dict[str, float] = {}
    for scale in scales:
        core_unit = scale * 2 * 2 * 2 * 6 * config.branches * config.horizon
        core_active = core_unit * 4
        core_simple = core_unit * 5
        diagnostic_active = (
            scale * 2 * 2 * 2 * 2 * config.branches * 4 * config.horizon
        )
        calibration = (
            scale
            * 2
            * 2
            * 2
            * 6
            * config.calibration_episodes
            * config.calibration_steps
        )
        development = (
            config.development_matrices
            * 2
            * 2
            * 2
            * 6
            * config.development_episodes
            * config.calibration_steps
        )
        projected_work_seconds = 2 * (
            (core_active + diagnostic_active) * active_seconds_per_fission
            + (core_simple + calibration + development) * simple_seconds_per_fission
        )
        parallel_seconds = projected_work_seconds / max(1, config.workers)
        fixed_overhead = (
            900.0 if config.profile == "full" else 120.0 if config.profile == "quick" else 30.0
        )
        projections[str(scale)] = 1.65 * parallel_seconds + fixed_overhead
    eligible = [
        scale
        for scale in scales
        if projections[str(scale)] <= config.registration_projection_ceiling_seconds
    ]
    if not eligible:
        raise RuntimeError(
            "FEP-PH1 timing projects beyond its registration ceiling at minimum scale"
        )
    result = {
        "schema": "fep-ph1-benchmark-v1",
        "profile": config.profile,
        "representative_seconds_per_fission": {
            "active_inference": active_seconds_per_fission,
            "simple_or_behavior": simple_seconds_per_fission,
        },
        "workers": config.workers,
        "projections_seconds_including_replay": projections,
        "selected_evaluation_matrices": max(eligible),
        "registration_projection_ceiling_seconds": config.registration_projection_ceiling_seconds,
        "hard_wall_time_seconds": config.wall_time_limit_seconds,
        "source_digest": _current_source_digest(),
    }
    write_json(output / "benchmark.json", result)
    seal_directory(output, ["benchmark.json"])
    return result


def _resolved_config(run_root: Path, config: ExperimentConfig) -> ExperimentConfig:
    benchmark = benchmark_stage(run_root, config)
    if benchmark.get("source_digest") != _current_source_digest():
        raise RuntimeError("sealed FEP-PH1 benchmark belongs to different source")
    return with_selected_scale(config, int(benchmark["selected_evaluation_matrices"]))


def registration_path(run_root: Path, profile: str) -> Path:
    return profile_root(run_root, profile) / "registration.json"


def register(run_root: Path, config: ExperimentConfig) -> tuple[Path, ExperimentConfig]:
    validation = validate_stage(run_root, config)
    if not validation["all_pass"]:
        raise RuntimeError("FEP-PH1 validation failed; refusing registration")
    resolved = _resolved_config(run_root, config)
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "config": resolved.to_dict(),
        "sources": source_manifest(PROJECT_ROOT, _source_files()),
        "dependencies": dependency_versions(),
        "runtime": runtime_manifest(),
        "stage0_dependency": _stage0_dependency(),
        "scientific_status": "EXPLORATORY_ONLY",
    }
    manifest["registration_id"] = sha256_bytes(canonical_json_bytes(manifest))
    path = registration_path(run_root, config.profile)
    if path.is_file():
        if read_json(path) != manifest:
            raise RuntimeError("existing FEP-PH1 registration differs from current contract")
        return path, resolved
    write_json(path, manifest)
    return path, resolved


def verify_registration(run_root: Path, config: ExperimentConfig) -> ExperimentConfig:
    path = registration_path(run_root, config.profile)
    if not path.is_file():
        raise FileNotFoundError(f"missing registration {path}")
    payload = read_json(path)
    if payload.get("schema") != SCHEMA:
        raise RuntimeError("FEP-PH1 registration schema mismatch")
    if payload["sources"] != source_manifest(PROJECT_ROOT, _source_files()):
        raise RuntimeError("registered FEP-PH1 source has drifted")
    if payload["dependencies"] != dependency_versions():
        raise RuntimeError("registered FEP-PH1 dependencies have drifted")
    if payload["stage0_dependency"] != _stage0_dependency():
        raise RuntimeError("sealed Stage 0 dependency has drifted")
    allowed = {field.name for field in fields(ExperimentConfig)}
    values = {key: value for key, value in payload["config"].items() if key in allowed}
    gard_values = values.get("gard")
    if isinstance(gard_values, dict):
        from .config import GardConfig

        values["gard"] = GardConfig(**gard_values)
    resolved = ExperimentConfig(**values)
    resolved.validate()
    return resolved


def _model_paths(root: Path, condition: ConditionSpec) -> tuple[Path, Path]:
    return (
        root / "models" / f"{condition.key}.npz",
        root / "models" / f"{condition.key}.json",
    )


def fit_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    output = root / "fit"
    if verify_seal(output):
        return output
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    sealed: list[str] = []
    for index, condition in enumerate(conditions(), start=1):
        _deadline(started, resolved)
        model_path, metadata_path = _model_paths(output, condition)
        if not _cell_complete(model_path, metadata_path):
            thresholds, counts, model, summary = fit_pooled_condition(resolved, condition)
            save_model(model_path, model, counts)
            with np.load(model_path, allow_pickle=False) as archive:
                array_digest = _array_digest({name: archive[name] for name in archive.files})
            write_json(
                metadata_path,
                {
                    "schema": "fep-ph1-pooled-model-v1",
                    "condition": condition.key,
                    "thresholds": {
                        "alignment": thresholds.alignment,
                        "growth": thresholds.growth,
                    },
                    "model_digest": model_digest(model),
                    "array_digest": array_digest,
                    "file_sha256": sha256_file(model_path),
                    "summary": summary,
                },
            )
        sealed.extend(
            str(path.relative_to(output)) for path in (model_path, metadata_path)
        )
        print(f"[fit] condition {index}/{len(conditions())}: {condition.key}", flush=True)
    seal_directory(output, sealed)
    return output


def _thresholds_for(fit_root: Path, condition: ConditionSpec) -> ObservationThresholds:
    _model, metadata = _model_paths(fit_root, condition)
    payload = read_json(metadata)
    return ObservationThresholds(
        alignment=tuple(float(value) for value in payload["thresholds"]["alignment"]),  # type: ignore[arg-type]
        growth=tuple(float(value) for value in payload["thresholds"]["growth"]),  # type: ignore[arg-type]
    )


def _evaluation_paths(output: Path, cell: CellSpec) -> tuple[Path, Path]:
    return output / "cells" / f"{cell.stem}.npz", output / "cells" / f"{cell.stem}.json"


def _save_evaluation_task(
    argument: tuple[ExperimentConfig, CellSpec, Path, ObservationThresholds, Path]
) -> tuple[str, str, str]:
    config, cell, model_path, thresholds, output = argument
    data_path, manifest_path = _evaluation_paths(output, cell)
    if _cell_complete(data_path, manifest_path):
        return cell.stem, str(data_path), str(manifest_path)
    arrays, metadata = generate_evaluation_cell(config, cell, model_path, thresholds)
    _save_npz(data_path, arrays)
    metadata.update(
        {
            "array_digest": _array_digest(arrays),
            "file_sha256": sha256_file(data_path),
        }
    )
    write_json(manifest_path, metadata)
    return cell.stem, str(data_path), str(manifest_path)


def _map_tasks(
    function: Any,
    arguments: list[Any],
    workers: int,
) -> Iterable[Any]:
    if workers <= 1:
        yield from map(function, arguments)
        return
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        yield from executor.map(function, arguments, chunksize=1)


def simulate_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    fit_root = root / "fit"
    if not verify_seal(fit_root):
        raise RuntimeError("pooled model stage is not sealed")
    output = root / "simulation"
    if verify_seal(output):
        return output
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    arguments = []
    for matrix_id in range(resolved.evaluation_matrices):
        for condition in conditions():
            cell = CellSpec(matrix_id, condition)
            model_path, _metadata = _model_paths(fit_root, condition)
            arguments.append(
                (resolved, cell, model_path, _thresholds_for(fit_root, condition), output)
            )
    sealed: list[str] = []
    total = len(arguments)
    for index, (_stem, data_text, manifest_text) in enumerate(
        _map_tasks(_save_evaluation_task, arguments, resolved.workers), start=1
    ):
        _deadline(started, resolved)
        sealed.extend(
            str(Path(value).relative_to(output))
            for value in (data_text, manifest_text)
        )
        if index % max(1, total // 50) == 0 or index == total:
            print(f"[simulation] cells {index}/{total}", flush=True)
    seal_directory(output, sealed)
    return output


def _replay_cell_task(
    argument: tuple[ExperimentConfig, CellSpec, Path, ObservationThresholds, Path]
) -> dict[str, Any]:
    config, cell, model_path, thresholds, output = argument
    data_path, manifest_path = _evaluation_paths(output, cell)
    expected = read_json(manifest_path)
    arrays, metadata = generate_evaluation_cell(config, cell, model_path, thresholds)
    return {
        "stem": cell.stem,
        "array_exact": _array_digest(arrays) == expected["array_digest"],
        "metadata_exact": all(metadata.get(key) == expected.get(key) for key in metadata),
    }


def _replay_fit(run_root: Path, config: ExperimentConfig) -> list[dict[str, Any]]:
    fit_root = profile_root(run_root, config.profile) / "fit"
    results = []
    for condition in conditions():
        model_path, metadata_path = _model_paths(fit_root, condition)
        expected = read_json(metadata_path)
        thresholds, counts, model, summary = fit_pooled_condition(config, condition)
        threshold_exact = (
            list(thresholds.alignment) == expected["thresholds"]["alignment"]
            and list(thresholds.growth) == expected["thresholds"]["growth"]
        )
        results.append(
            {
                "condition": condition.key,
                "model_exact": model_digest(model) == expected["model_digest"],
                "threshold_exact": threshold_exact,
                "summary_exact": summary == expected["summary"],
            }
        )
    return results


def replay_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    simulation = root / "simulation"
    if not verify_seal(simulation):
        raise RuntimeError("simulation stage is not sealed")
    output = root / "replay"
    if verify_seal(output):
        return output
    started = time.monotonic()
    fit_results = _replay_fit(run_root, resolved)
    arguments = []
    fit_root = root / "fit"
    for matrix_id in range(resolved.evaluation_matrices):
        for condition in conditions():
            cell = CellSpec(matrix_id, condition)
            model_path, _metadata = _model_paths(fit_root, condition)
            arguments.append(
                (resolved, cell, model_path, _thresholds_for(fit_root, condition), simulation)
            )
    cell_results = []
    total = len(arguments)
    for index, result in enumerate(
        _map_tasks(_replay_cell_task, arguments, resolved.workers), start=1
    ):
        _deadline(started, resolved)
        cell_results.append(result)
        if index % max(1, total // 50) == 0 or index == total:
            print(f"[replay] cells {index}/{total}", flush=True)
    all_exact = all(
        result["model_exact"]
        and result["threshold_exact"]
        and result["summary_exact"]
        for result in fit_results
    ) and all(
        result["array_exact"] and result["metadata_exact"]
        for result in cell_results
    )
    payload = {
        "schema": "fep-ph1-replay-v1",
        "fit": fit_results,
        "cells": cell_results,
        "all_exact": all_exact,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "replay.json", payload)
    seal_directory(output, ["replay.json"])
    if not all_exact:
        raise RuntimeError("FEP-PH1 exact replay failed")
    return output


def analyze_stage(run_root: Path, config: ExperimentConfig) -> Path:
    resolved = verify_registration(run_root, config)
    root = profile_root(run_root, config.profile)
    replay = root / "replay"
    if not verify_seal(replay) or not read_json(replay / "replay.json")["all_exact"]:
        raise RuntimeError("exact replay must pass before FEP-PH1 analysis")
    output = root / "analysis"
    if verify_seal(output):
        return output
    analyze_atlas(resolved, root / "simulation", output)
    return output


def run_all(run_root: Path, config: ExperimentConfig) -> Path:
    started = time.monotonic()
    validate_stage(run_root, config)
    benchmark_stage(run_root, config)
    _path, resolved = register(run_root, config)
    fit_stage(run_root, resolved)
    _deadline(started, resolved)
    simulate_stage(run_root, resolved)
    _deadline(started, resolved)
    replay_stage(run_root, resolved)
    _deadline(started, resolved)
    return analyze_stage(run_root, resolved)


def status(run_root: Path, profile: str) -> dict[str, Any]:
    root = profile_root(run_root, profile)
    def seal_present(path: Path) -> bool:
        seal_path = path / "seal.json"
        if not seal_path.is_file():
            return False
        try:
            return bool(read_json(seal_path).get("files"))
        except (OSError, ValueError):
            return False

    stages = {
        "validation": seal_present(root / "validation"),
        "benchmark": seal_present(root / "benchmark"),
        "registered": (root / "registration.json").is_file(),
        "fit": seal_present(root / "fit"),
        "simulation": seal_present(root / "simulation"),
        "replay": seal_present(root / "replay"),
        "analysis": seal_present(root / "analysis"),
    }
    output: dict[str, Any] = {"profile": profile, **stages}
    if stages["registered"]:
        registration = read_json(root / "registration.json")
        output["registration_id"] = registration["registration_id"]
        output["selected_evaluation_matrices"] = registration["config"][
            "evaluation_matrices"
        ]
    if stages["analysis"]:
        metrics = read_json(root / "analysis" / "metrics.json")
        output["integrity_verdict"] = metrics["decision"]["integrity_verdict"]
        output["scientific_status"] = metrics["decision"]["scientific_status"]
    for name in ("fep-ph1.status", "fep-ph1.pid", "fep-ph1.started", "fep-ph1.finished"):
        path = root / name
        output[name.replace("fep-ph1.", "runner_")] = (
            path.read_text(encoding="utf-8").strip() if path.is_file() else None
        )
    pid_text = output.get("runner_pid")
    try:
        pid = int(pid_text) if pid_text else -1
        if pid <= 0:
            raise ValueError("runner PID must be positive")
        os.kill(pid, 0)
        output["runner_alive"] = True
    except (ValueError, OSError):
        output["runner_alive"] = False
    return output
