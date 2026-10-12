from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import joblib
from threadpoolctl import threadpool_limits

from fep_surprise_15 import compat
from fep_surprise_15.integrity import (
    atomic_destination,
    canonical_digest,
    sha256_file,
    verify_checksums,
    write_checksums,
)

from .analysis import analyze_confirmation, fit_development_models
from .config import CANDIDATES, Campaign2Config
from .validation import validate
from .worker import (
    Cell2Spec,
    load_atlases,
    load_design,
    load_futures,
    prepare_cell,
    run_futures,
)


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
FORMAT = "fep-surprise-2-registration-v1"
SHARED_SOURCES = (
    "fep_surprise/dynamics.py",
    "fep_surprise/tracing.py",
    "fep_surprise_15/compat.py",
    "fep_surprise_15/integrity.py",
    "fep_surprise_15/observers.py",
    "fep_surprise_15/predictor.py",
)


def _locked_requirements() -> dict[str, str]:
    output = {}
    for line in (CAMPAIGN_ROOT / "requirements-2-lock.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, version = stripped.split("==", 1)
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
        for path in sorted((CAMPAIGN_ROOT / "fep_surprise_2").glob("*.py"))
    }
    for name in SHARED_SOURCES:
        sources[name] = sha256_file(CAMPAIGN_ROOT / name)
    for name in compat.REQUIRED_SIMULATOR_SOURCES:
        sources[f"simulator::{name}"] = sha256_file(
            compat.PLASTIC_HEREDITY_ROOT / name
        )
    for name in ("EXPERIMENT_2_PREREGISTRATION.md", "requirements-2-lock.txt"):
        sources[name] = sha256_file(CAMPAIGN_ROOT / name)
    return sources


def profile_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile


def validation_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "validation"


def registration_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "registration"


def development_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "development"


def confirmation_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "confirmation"


def replay_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "confirmation_replay"


def analysis_path(run_root: Path, profile: str) -> Path:
    return profile_path(run_root, profile) / "analysis"


def validate_stage(run_root: Path, config: Campaign2Config) -> Path:
    destination = validation_path(run_root, config.profile)
    if destination.exists():
        verify_validation(destination, config)
        return destination
    with atomic_destination(destination) as output:
        results = validate(config, output)
        seal: dict[str, Any] = {
            "format": "fep-surprise-2-validation-seal-v1",
            "profile": config.profile,
            "all_pass": bool(results["all_pass"]),
            "sources": _source_hashes(),
            "runtime": _runtime_manifest(),
        }
        if not seal["runtime"]["lock_matches"]:
            raise ValueError("installed environment differs from requirements-2-lock.txt")
        seal["validation_id"] = canonical_digest(seal)
        (output / "validation_seal.json").write_text(
            json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    return destination


def verify_validation(path: Path, config: Campaign2Config) -> dict[str, Any]:
    verify_checksums(path)
    results = json.loads((path / "validation.json").read_text(encoding="utf-8"))
    if not results.get("all_pass"):
        raise ValueError("Experiment 2 validation did not pass")
    seal = json.loads((path / "validation_seal.json").read_text(encoding="utf-8"))
    identifier = seal.pop("validation_id")
    if canonical_digest(seal) != identifier:
        raise ValueError("validation identifier mismatch")
    seal["validation_id"] = identifier
    if seal["profile"] != config.profile or seal["sources"] != _source_hashes():
        raise ValueError("validation came from another profile or source tree")
    runtime = _runtime_manifest()
    if not runtime["lock_matches"] or seal["runtime"] != runtime:
        raise ValueError("validated runtime differs from pinned environment")
    return {"seal": seal, "results": results}


def protocol(config: Campaign2Config, validation_bundle: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": FORMAT,
        "status": "sealed_before_scientific_matrix_generation",
        "title": "Fixed-state rulebook mismatch and prospective strict-8 rehoming",
        "config": config.to_dict(),
        "validation_id": validation_bundle["seal"]["validation_id"],
        "preregistration": "EXPERIMENT_2_PREREGISTRATION.md",
        "stage_order": [
            "validation",
            "registration",
            "development_design_and_futures",
            "development_exact_replay_and_model_freeze",
            "confirmation_design_seal_before_outcomes",
            "confirmation_future_generation_seal",
            "confirmation_exact_replay",
            "confirmation_analysis",
        ],
        "analysis_firewall": (
            "Confirmation outcomes cannot be analyzed until every design, atlas, "
            "and future payload has replayed exactly."
        ),
        "exact_relabel_control": (
            "ISOMORPHIC_BOTH_100 reuses the NOOP stochastic path and applies the "
            "registered molecule-label permutation to every state and readout."
        ),
        "claim_boundary": (
            "No FEP, variational-free-energy, active-inference, cognition, "
            "autonomous-control, prebiotic-chemistry, inherited-repertoire, "
            "universal-origin, or Platonic-causation claim is eligible."
        ),
        "sources": _source_hashes(),
    }
    payload["registration_id"] = canonical_digest(payload)
    return payload


def register(run_root: Path, config: Campaign2Config) -> Path:
    validation_bundle = verify_validation(
        validation_path(run_root, config.profile), config
    )
    destination = registration_path(run_root, config.profile)
    if destination.exists():
        verify_registration(destination, config)
        return destination
    with atomic_destination(destination) as output:
        payload = protocol(config, validation_bundle)
        (output / "protocol.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "runtime.json").write_text(
            json.dumps(_runtime_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output / "README.md").write_text(
            "# Sealed Experiment 2 protocol\n\n"
            f"Registration ID: `{payload['registration_id']}`\n\n"
            "Created after validation and before this profile generated any "
            "scientific beta matrix.\n",
            encoding="utf-8",
        )
        write_checksums(output)
    return destination


def verify_registration(path: Path, config: Campaign2Config) -> dict[str, Any]:
    verify_checksums(path)
    payload = json.loads((path / "protocol.json").read_text(encoding="utf-8"))
    if payload.get("format") != FORMAT:
        raise ValueError("unsupported Experiment 2 registration")
    identifier = payload.pop("registration_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("registration identifier mismatch")
    payload["registration_id"] = identifier
    if payload["config"] != json.loads(json.dumps(config.to_dict())):
        raise ValueError("registered configuration differs from requested profile")
    if payload["sources"] != _source_hashes():
        raise ValueError("registered scientific source changed")
    validation_bundle = verify_validation(
        validation_path(path.parents[1], config.profile), config
    )
    if payload["validation_id"] != validation_bundle["seal"]["validation_id"]:
        raise ValueError("registration references another validation")
    return payload


def _jobs(output: Path, stage: str, config: Campaign2Config) -> list[Cell2Spec]:
    scale = config.development if stage == "development" else config.confirmation
    cells = output / "cells"
    return [
        Cell2Spec(stage, matrix, candidate, cells)
        for candidate in CANDIDATES
        for matrix in range(scale.matrices)
    ]


def _future_for_design(path: Path) -> Path:
    return path.with_name(path.name.replace("_design.joblib", "_futures.joblib"))


def _run_parallel(
    jobs: list[Cell2Spec],
    config: Campaign2Config,
    workers: int,
    operation: Callable[[Cell2Spec, Campaign2Config], Path],
    complete: Callable[[Cell2Spec], bool],
    label: str,
) -> list[Path]:
    checkpointed = [spec for spec in jobs if complete(spec)]
    pending = [replace(spec, force=False) for spec in jobs if not complete(spec)]
    print(f"[{label}] {len(checkpointed)} checkpointed, {len(pending)} pending", flush=True)
    results = [operation(spec, config) for spec in []]
    results.extend(
        spec.design_path if operation is prepare_cell else spec.future_path
        for spec in checkpointed
    )
    worker_count = max(1, int(workers))
    with threadpool_limits(limits=1):
        if worker_count == 1:
            for index, spec in enumerate(pending, start=1):
                results.append(operation(spec, config))
                print(
                    f"[{label}] cells {index}/{len(pending)} "
                    f"(c{spec.candidate} m{spec.matrix_id})",
                    flush=True,
                )
        else:
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(operation, spec, config): spec for spec in pending
                }
                for index, future in enumerate(as_completed(futures), start=1):
                    spec = futures[future]
                    results.append(future.result())
                    print(
                        f"[{label}] cells {index}/{len(pending)} "
                        f"(c{spec.candidate} m{spec.matrix_id})",
                        flush=True,
                    )
    return sorted(results)


def _prepare_jobs(jobs: list[Cell2Spec], config: Campaign2Config, workers: int) -> list[Path]:
    return _run_parallel(
        jobs,
        config,
        workers,
        prepare_cell,
        lambda spec: spec.design_path.is_file()
        and spec.atlas_path.is_file()
        and spec.metadata_path.is_file(),
        f"{jobs[0].stage}-design",
    )


def _future_jobs(jobs: list[Cell2Spec], config: Campaign2Config, workers: int) -> list[Path]:
    return _run_parallel(
        jobs,
        config,
        workers,
        run_futures,
        lambda spec: spec.future_path.is_file(),
        f"{jobs[0].stage}-futures",
    )


def _artifact_hashes(output: Path, kind: str) -> dict[str, str]:
    if kind == "design":
        suffixes = ("_design.joblib", "_atlases.joblib", ".json")
        paths = [
            path
            for path in (output / "cells").glob("cell_*")
            if path.name.endswith(suffixes)
        ]
    elif kind == "futures":
        paths = list((output / "cells").glob("cell_*_futures.joblib"))
    else:
        raise ValueError(kind)
    return {
        str(path.relative_to(output)): sha256_file(path) for path in sorted(paths)
    }


def _write_manifest(output: Path, kind: str, count: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": f"fep-surprise-2-{kind}-manifest-v1",
        "cell_count": count,
        "artifacts": _artifact_hashes(output, kind),
    }
    payload[f"{kind}_id"] = canonical_digest(payload)
    (output / f"{kind}_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _verify_manifest(output: Path, kind: str, count: int) -> dict[str, Any]:
    payload = json.loads(
        (output / f"{kind}_manifest.json").read_text(encoding="utf-8")
    )
    identifier = payload.pop(f"{kind}_id")
    if canonical_digest(payload) != identifier:
        raise ValueError(f"{kind} manifest identifier mismatch")
    payload[f"{kind}_id"] = identifier
    if payload["cell_count"] != count or payload["artifacts"] != _artifact_hashes(output, kind):
        raise ValueError(f"{kind} artifacts differ from sealed manifest")
    return payload


def _replay_one(original_name: str, config: Campaign2Config) -> dict[str, Any]:
    original_design_path = Path(original_name)
    design = load_design(original_design_path)
    metadata = design["metadata"]
    atlas_path = original_design_path.with_name(
        original_design_path.name.replace("_design.joblib", "_atlases.joblib")
    )
    future_path = _future_for_design(original_design_path)
    original_atlases = load_atlases(atlas_path)
    original_futures = load_futures(future_path)
    with tempfile.TemporaryDirectory(prefix="fep2-replay-") as temporary:
        spec = Cell2Spec(
            stage=str(metadata["stage"]),
            matrix_id=int(metadata["matrix_id"]),
            candidate=str(metadata["candidate"]),
            output=Path(temporary),
            force=True,
        )
        replay_design_path = prepare_cell(spec, config)
        replay_future_path = run_futures(spec, config)
        replay_design = load_design(replay_design_path)
        replay_atlases = load_atlases(spec.atlas_path)
        replay_futures = load_futures(replay_future_path)
        design_exact = joblib.hash(design) == joblib.hash(replay_design)
        atlas_exact = joblib.hash(original_atlases) == joblib.hash(replay_atlases)
        futures_exact = joblib.hash(original_futures) == joblib.hash(replay_futures)
        scientific_exact = bool(
            metadata["scientific_digest"]
            == replay_design["metadata"]["scientific_digest"]
            and original_futures["metadata"]["scientific_digest"]
            == replay_futures["metadata"]["scientific_digest"]
        )
    return {
        "stage": metadata["stage"],
        "matrix_id": metadata["matrix_id"],
        "candidate": metadata["candidate"],
        "design_exact": design_exact,
        "atlas_exact": atlas_exact,
        "futures_exact": futures_exact,
        "scientific_digest_exact": scientific_exact,
        "exact": bool(design_exact and atlas_exact and futures_exact and scientific_exact),
        "artifact": original_design_path.name,
    }


def _replay_cells(
    designs: list[Path], audits: Path, config: Campaign2Config, workers: int
) -> dict[str, Any]:
    audits.mkdir(parents=True, exist_ok=True)
    pending = []
    results = []
    for path in designs:
        audit_path = audits / f"{path.stem}.json"
        if audit_path.exists():
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if not audit.get("exact"):
                raise ValueError(f"prior replay mismatch: {path.name}")
            results.append(audit)
        else:
            pending.append(path)
    print(f"[replay] {len(results)} checkpointed, {len(pending)} pending", flush=True)
    worker_count = max(1, min(int(workers), 4))
    with threadpool_limits(limits=1):
        if worker_count == 1:
            iterator = ((path, _replay_one(str(path), config)) for path in pending)
            for index, (path, audit) in enumerate(iterator, start=1):
                (audits / f"{path.stem}.json").write_text(
                    json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                results.append(audit)
                print(f"[replay] cells {index}/{len(pending)} exact={audit['exact']}", flush=True)
                if not audit["exact"]:
                    raise ValueError(f"replay mismatch: {path.name}")
        else:
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(_replay_one, str(path), config): path
                    for path in pending
                }
                for index, future in enumerate(as_completed(futures), start=1):
                    path = futures[future]
                    audit = future.result()
                    (audits / f"{path.stem}.json").write_text(
                        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                    )
                    results.append(audit)
                    print(f"[replay] cells {index}/{len(pending)} exact={audit['exact']}", flush=True)
                    if not audit["exact"]:
                        for other in futures:
                            other.cancel()
                        raise ValueError(f"replay mismatch: {path.name}")
    return {
        "cells": len(results),
        "all_exact": bool(results and all(item["exact"] for item in results)),
        "fresh_process_workers": worker_count,
    }


def _cohort_integrity(output: Path, stage: str, config: Campaign2Config) -> dict[str, bool]:
    jobs = _jobs(output, stage, config)
    complete_reference = True
    complete_futures = True
    shape_exact = True
    for spec in jobs:
        if not (spec.design_path.is_file() and spec.atlas_path.is_file() and spec.future_path.is_file()):
            complete_reference = complete_futures = shape_exact = False
            continue
        design = load_design(spec.design_path)
        future = load_futures(spec.future_path)
        complete_reference &= all(
            item["completed_lineages"] == item["requested_lineages"]
            for item in design["metadata"]["reference"].values()
        )
        complete_futures &= bool(future["complete"].all())
        scale = config.development if stage == "development" else config.confirmation
        shape_exact &= future["strict8"].shape == (
            len(scale.landmarks), len(design["arms"]), scale.branches
        )
    return {
        "expected_cell_count": all(
            spec.design_path.is_file() and spec.atlas_path.is_file() and spec.future_path.is_file()
            for spec in jobs
        ),
        "all_reference_lineages_retained": bool(complete_reference),
        "all_future_streams_complete": bool(complete_futures),
        "outcome_shapes_exact": bool(shape_exact),
    }


def develop(run_root: Path, config: Campaign2Config, workers: int) -> Path:
    registration = registration_path(run_root, config.profile)
    design = verify_registration(registration, config)
    output = development_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_development(output, registration, config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    jobs = _jobs(output, "development", config)
    if (output / "design_manifest.json").exists():
        design_manifest = _verify_manifest(output, "design", len(jobs))
    else:
        _prepare_jobs(jobs, config, workers)
        design_manifest = _write_manifest(output, "design", len(jobs))
    if (output / "futures_manifest.json").exists():
        future_manifest = _verify_manifest(output, "futures", len(jobs))
    else:
        _future_jobs(jobs, config, workers)
        future_manifest = _write_manifest(output, "futures", len(jobs))
    replay = _replay_cells(
        [spec.design_path for spec in jobs], output / "replay_audits", config, min(workers, 2)
    )
    if not replay["all_exact"] or replay["cells"] != len(jobs):
        raise ValueError("development exact-replay gate failed")
    model_summary = fit_development_models(
        output / "cells", config, output / "predictors.joblib"
    )
    cohort = _cohort_integrity(output, "development", config)
    if not all(cohort.values()):
        raise ValueError(f"development cohort integrity failed: {cohort}")
    if design["sources"] != _source_hashes():
        raise ValueError("scientific source changed during development")
    seal: dict[str, Any] = {
        "format": "fep-surprise-2-development-v1",
        "status": "sealed_after_exact_replay_and_model_freeze",
        "registration_id": design["registration_id"],
        "profile": config.profile,
        "design_id": design_manifest["design_id"],
        "futures_id": future_manifest["futures_id"],
        "replay": replay,
        "cohort_integrity": cohort,
        "predictors": model_summary,
    }
    seal["development_id"] = canonical_digest(seal)
    (output / "development.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(output)
    return output


def verify_development(path: Path, registration: Path, config: Campaign2Config) -> dict[str, Any]:
    design = verify_registration(registration, config)
    verify_checksums(path)
    payload = json.loads((path / "development.json").read_text(encoding="utf-8"))
    identifier = payload.pop("development_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("development identifier mismatch")
    payload["development_id"] = identifier
    if payload["registration_id"] != design["registration_id"]:
        raise ValueError("development references another registration")
    if not payload["replay"]["all_exact"] or not all(payload["cohort_integrity"].values()):
        raise ValueError("development integrity gate incomplete")
    return payload


def prepare_confirmation(run_root: Path, config: Campaign2Config, workers: int) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    design = verify_registration(registration, config)
    development_seal = verify_development(development, registration, config)
    output = confirmation_path(run_root, config.profile)
    if (output / "confirmation_design.json").exists():
        verify_confirmation_design(output, registration, development, config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    jobs = _jobs(output, "confirmation", config)
    _prepare_jobs(jobs, config, workers)
    if list((output / "cells").glob("cell_*_futures.joblib")):
        raise ValueError("confirmation outcomes exist before the design seal")
    manifest = _write_manifest(output, "design", len(jobs))
    if design["sources"] != _source_hashes():
        raise ValueError("scientific source changed during confirmation preparation")
    payload: dict[str, Any] = {
        "format": "fep-surprise-2-confirmation-design-v1",
        "status": "sealed_design_before_outcome_generation",
        "registration_id": design["registration_id"],
        "development_id": development_seal["development_id"],
        "profile": config.profile,
        "design_id": manifest["design_id"],
        "cells": len(jobs),
        "future_artifacts_present": False,
    }
    payload["confirmation_design_id"] = canonical_digest(payload)
    (output / "confirmation_design.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output


def verify_confirmation_design(
    path: Path, registration: Path, development: Path, config: Campaign2Config
) -> dict[str, Any]:
    design = verify_registration(registration, config)
    development_seal = verify_development(development, registration, config)
    payload = json.loads((path / "confirmation_design.json").read_text(encoding="utf-8"))
    identifier = payload.pop("confirmation_design_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("confirmation-design identifier mismatch")
    payload["confirmation_design_id"] = identifier
    if payload["registration_id"] != design["registration_id"]:
        raise ValueError("confirmation design references another registration")
    if payload["development_id"] != development_seal["development_id"]:
        raise ValueError("confirmation design references another development")
    _verify_manifest(path, "design", payload["cells"])
    return payload


def generate_confirmation(run_root: Path, config: Campaign2Config, workers: int) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    output = confirmation_path(run_root, config.profile)
    confirmation_design = verify_confirmation_design(
        output, registration, development, config
    )
    if (output / "SHA256SUMS").exists():
        verify_confirmation(output, registration, development, config)
        return output
    jobs = _jobs(output, "confirmation", config)
    _future_jobs(jobs, config, workers)
    future_manifest = _write_manifest(output, "futures", len(jobs))
    cohort = _cohort_integrity(output, "confirmation", config)
    if not all(cohort.values()):
        raise ValueError(f"confirmation cohort integrity failed: {cohort}")
    design = verify_registration(registration, config)
    if design["sources"] != _source_hashes():
        raise ValueError("scientific source changed during confirmation generation")
    if any((output / name).exists() for name in ("metrics.json", "REPORT.md")):
        raise ValueError("scientific analysis appeared inside the confirmation stage")
    payload: dict[str, Any] = {
        "format": "fep-surprise-2-confirmation-v1",
        "status": "sealed_outcomes_before_replay_without_scientific_analysis",
        "confirmation_design_id": confirmation_design["confirmation_design_id"],
        "futures_id": future_manifest["futures_id"],
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


def verify_confirmation(
    path: Path, registration: Path, development: Path, config: Campaign2Config
) -> dict[str, Any]:
    confirmation_design = verify_confirmation_design(path, registration, development, config)
    verify_checksums(path)
    payload = json.loads((path / "confirmation.json").read_text(encoding="utf-8"))
    identifier = payload.pop("confirmation_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("confirmation identifier mismatch")
    payload["confirmation_id"] = identifier
    if payload["confirmation_design_id"] != confirmation_design["confirmation_design_id"]:
        raise ValueError("confirmation references another sealed design")
    if payload.get("analysis_artifacts_present"):
        raise ValueError("confirmation violated analysis firewall")
    _verify_manifest(path, "futures", payload["cells"])
    return payload


def replay_confirmation(run_root: Path, config: Campaign2Config, workers: int) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    confirmation = confirmation_path(run_root, config.profile)
    confirmation_seal = verify_confirmation(confirmation, registration, development, config)
    output = replay_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_replay(output, confirmation, registration, development, config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    designs = _design_paths_for_campaign(confirmation / "cells")
    replay = _replay_cells(designs, output / "audits", config, workers)
    if not replay["all_exact"] or replay["cells"] != confirmation_seal["cells"]:
        raise ValueError("confirmation exact-replay gate failed")
    design = verify_registration(registration, config)
    if design["sources"] != _source_hashes():
        raise ValueError("scientific source changed during confirmation replay")
    payload: dict[str, Any] = {
        "format": "fep-surprise-2-confirmation-replay-v1",
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


def _design_paths_for_campaign(cells: Path) -> list[Path]:
    return sorted(cells.glob("cell_*_design.joblib"))


def verify_replay(
    path: Path,
    confirmation: Path,
    registration: Path,
    development: Path,
    config: Campaign2Config,
) -> dict[str, Any]:
    confirmation_seal = verify_confirmation(confirmation, registration, development, config)
    verify_checksums(path)
    payload = json.loads((path / "replay.json").read_text(encoding="utf-8"))
    identifier = payload.pop("replay_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("confirmation replay identifier mismatch")
    payload["replay_id"] = identifier
    if payload["confirmation_id"] != confirmation_seal["confirmation_id"] or not payload["all_exact"]:
        raise ValueError("confirmation replay is not an exact match")
    return payload


def analyze(run_root: Path, config: Campaign2Config) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    confirmation = confirmation_path(run_root, config.profile)
    replay = replay_path(run_root, config.profile)
    design = verify_registration(registration, config)
    development_seal = verify_development(development, registration, config)
    confirmation_seal = verify_confirmation(confirmation, registration, development, config)
    replay_seal = verify_replay(replay, confirmation, registration, development, config)
    destination = analysis_path(run_root, config.profile)
    if destination.exists():
        verify_checksums(destination)
        return destination
    validation_results = verify_validation(
        validation_path(run_root, config.profile), config
    )["results"]
    cohort = _cohort_integrity(confirmation, "confirmation", config)
    integrity = {
        "validation_all_pass": bool(validation_results["all_pass"]),
        "trace_and_endpoint_validation": bool(
            validation_results["traced_untraced_exact"]
            and validation_results["strict8_fixture_positive"]
            and validation_results["strict8_relabel_invariant"]
        ),
        "deterministic_observers": bool(
            validation_results["repeated_model_hash_exact"]
            and validation_results["fresh_process_worker_count_model_hash_exact"]
        ),
        "relabeling_invariance": bool(
            max(validation_results["relabel_max_abs_errors"].values())
            <= config.relabel_tolerance
        ),
        "aligned_isomorphism": bool(
            max(validation_results["isomorphism_aligned_local_mismatch"].values())
            <= config.aligned_mismatch_tolerance
        ),
        "seed_firewall": bool(validation_results["development_confirmation_seed_domains_distinct"]),
        "development_exact_replay": bool(development_seal["replay"]["all_exact"]),
        "confirmation_exact_replay": bool(replay_seal["all_exact"]),
        "complete_confirmation_cohort": bool(all(cohort.values())),
        "source_tree_matches_registration": bool(design["sources"] == _source_hashes()),
        "analysis_firewall_intact": bool(not confirmation_seal["analysis_artifacts_present"]),
    }
    with atomic_destination(destination) as output:
        metrics = analyze_confirmation(
            confirmation / "cells",
            development / "predictors.joblib",
            config,
            output,
            integrity,
        )
        seal: dict[str, Any] = {
            "format": "fep-surprise-2-analysis-seal-v1",
            "status": "sealed_after_exact_confirmation_replay",
            "registration_id": design["registration_id"],
            "development_id": development_seal["development_id"],
            "confirmation_id": confirmation_seal["confirmation_id"],
            "replay_id": replay_seal["replay_id"],
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
    for name, path in (
        ("validation", root / "validation"),
        ("registration", root / "registration"),
        ("development", root / "development"),
        ("confirmation", root / "confirmation"),
        ("confirmation_replay", root / "confirmation_replay"),
        ("analysis", root / "analysis"),
    ):
        entry: dict[str, Any] = {
            "exists": path.exists(),
            "sealed": (path / "SHA256SUMS").exists(),
        }
        cells = path / "cells"
        if cells.exists():
            entry["design_cells"] = len(list(cells.glob("cell_*_design.joblib")))
            entry["future_cells"] = len(list(cells.glob("cell_*_futures.joblib")))
        audits = path / "audits"
        if audits.exists():
            entry["replay_audits"] = len(list(audits.glob("cell_*.json")))
        output[name] = entry
    for label, filename in (
        ("detached_run_status", "experiment2.status"),
        ("detached_run_pid", "experiment2.pid"),
        ("detached_run_session", "experiment2.session"),
        ("detached_run_started", "experiment2.started"),
        ("detached_run_finished", "experiment2.finished"),
    ):
        path = root / filename
        output[label] = path.read_text(encoding="utf-8").strip() if path.exists() else None
    pid = output.get("detached_run_pid")
    try:
        output["detached_run_alive"] = bool(pid and int(pid) > 0 and Path(f"/proc/{int(pid)}").exists())
    except (TypeError, ValueError):
        output["detached_run_alive"] = False
    return output
