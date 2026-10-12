from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Any

import joblib
from threadpoolctl import threadpool_limits

from . import compat
from .analysis import analyze_confirmation, fit_development_models
from .config import (
    CANDIDATES,
    NATURAL,
    NULL_MECHANISMS,
    Campaign15Config,
)
from .integrity import (
    atomic_destination,
    canonical_digest,
    sha256_file,
    verify_checksums,
    write_checksums,
)
from .validation import validate
from .worker import Cell15Spec, load_cell, load_observers, run_cell


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
FORMAT = "fep-surprise-15-registration-v1"
PARENT_SOURCES = compat.REQUIRED_SIMULATOR_SOURCES
SHARED_SOURCES = (
    "fep_surprise/dynamics.py",
    "fep_surprise/tracing.py",
)


def _locked_requirements() -> dict[str, str]:
    output = {}
    for line in (CAMPAIGN_ROOT / "requirements-15-lock.txt").read_text(
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
        for path in sorted((CAMPAIGN_ROOT / "fep_surprise_15").glob("*.py"))
    }
    for name in SHARED_SOURCES:
        sources[name] = sha256_file(CAMPAIGN_ROOT / name)
    for name in PARENT_SOURCES:
        sources[f"simulator::{name}"] = sha256_file(
            compat.PLASTIC_HEREDITY_ROOT / name
        )
    for name in (
        "EXPERIMENT_1_5_PREREGISTRATION.md",
        "requirements-15-lock.txt",
    ):
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


def validate_stage(run_root: Path, config: Campaign15Config) -> Path:
    destination = validation_path(run_root, config.profile)
    if destination.exists():
        verify_validation(destination, config)
        return destination
    with atomic_destination(destination) as output:
        results = validate(config, output)
        seal: dict[str, Any] = {
            "format": "fep-surprise-15-validation-seal-v1",
            "profile": config.profile,
            "all_pass": bool(results["all_pass"]),
            "sources": _source_hashes(),
            "runtime": _runtime_manifest(),
        }
        if not seal["runtime"]["lock_matches"]:
            raise ValueError("installed environment differs from requirements-15-lock.txt")
        seal["validation_id"] = canonical_digest(seal)
        (output / "validation_seal.json").write_text(
            json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    return destination


def verify_validation(path: Path, config: Campaign15Config) -> dict[str, Any]:
    verify_checksums(path)
    results = json.loads((path / "validation.json").read_text(encoding="utf-8"))
    if not results.get("all_pass"):
        raise ValueError("Experiment 1.5 validation did not pass")
    seal = json.loads(
        (path / "validation_seal.json").read_text(encoding="utf-8")
    )
    identifier = seal.pop("validation_id")
    if canonical_digest(seal) != identifier:
        raise ValueError("validation identifier mismatch")
    seal["validation_id"] = identifier
    if seal["profile"] != config.profile or seal["sources"] != _source_hashes():
        raise ValueError("validation was produced by another profile or source tree")
    runtime = _runtime_manifest()
    if not runtime["lock_matches"] or seal["runtime"] != runtime:
        raise ValueError("validated runtime differs from the pinned environment")
    return {"seal": seal, "results": results}


def protocol(config: Campaign15Config, validation: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": FORMAT,
        "status": "sealed_before_scientific_matrix_generation",
        "title": "Scale-, phase-, and observer-audited compositional recurrence",
        "config": config.to_dict(),
        "validation_id": validation["seal"]["validation_id"],
        "preregistration": "EXPERIMENT_1_5_PREREGISTRATION.md",
        "stage_order": [
            "validation",
            "registration",
            "development_generation",
            "development_exact_replay",
            "development_model_freeze",
            "confirmation_generation_seal",
            "confirmation_exact_replay",
            "confirmation_analysis",
        ],
        "analysis_firewall": (
            "confirmation outcomes cannot be analyzed until every confirmation "
            "cell and observer model replays exactly"
        ),
        "claim_boundary": (
            "No variational-free-energy, active-inference, cognition, autonomous-"
            "control, prebiotic-chemistry, inherited-repertoire, universal-origin, "
            "or Platonic-causation claim is eligible."
        ),
        "sources": _source_hashes(),
    }
    payload["registration_id"] = canonical_digest(payload)
    return payload


def register(run_root: Path, config: Campaign15Config) -> Path:
    validation = verify_validation(
        validation_path(run_root, config.profile), config
    )
    destination = registration_path(run_root, config.profile)
    if destination.exists():
        verify_registration(destination, config)
        return destination
    with atomic_destination(destination) as output:
        payload = protocol(config, validation)
        (output / "protocol.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "runtime.json").write_text(
            json.dumps(_runtime_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output / "README.md").write_text(
            "# Sealed Experiment 1.5 protocol\n\n"
            f"Registration ID: `{payload['registration_id']}`\n\n"
            "This bundle was created after validation and before this profile "
            "generated any scientific beta matrix.\n",
            encoding="utf-8",
        )
        write_checksums(output)
    return destination


def verify_registration(path: Path, config: Campaign15Config) -> dict[str, Any]:
    verify_checksums(path)
    payload = json.loads((path / "protocol.json").read_text(encoding="utf-8"))
    if payload.get("format") != FORMAT:
        raise ValueError("unsupported Experiment 1.5 registration")
    identifier = payload.pop("registration_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("registration identifier mismatch")
    payload["registration_id"] = identifier
    expected = json.loads(json.dumps(config.to_dict()))
    if payload["config"] != expected:
        raise ValueError("registered configuration differs from requested profile")
    if payload["sources"] != _source_hashes():
        raise ValueError("registered scientific source changed")
    validation = verify_validation(
        validation_path(path.parents[1], config.profile), config
    )
    if payload["validation_id"] != validation["seal"]["validation_id"]:
        raise ValueError("registration references another validation seal")
    return payload


def _stage_jobs(
    output: Path, stage: str, config: Campaign15Config
) -> list[Cell15Spec]:
    scale = config.development if stage == "development" else config.confirmation
    mechanism_counts = (
        ((NATURAL, scale.natural_matrices),)
        if stage == "development"
        else (
            (NATURAL, scale.natural_matrices),
            *((mechanism, scale.null_matrices) for mechanism in NULL_MECHANISMS),
        )
    )
    cells = output / "cells"
    return [
        Cell15Spec(stage, matrix, candidate, mechanism, cells)
        for mechanism, count in mechanism_counts
        for candidate in CANDIDATES
        for matrix in range(count)
    ]


def _cell_artifacts(spec: Cell15Spec) -> tuple[Path, Path, Path]:
    return (
        spec.output / f"{spec.stem}.joblib",
        spec.output / f"{spec.stem}_observers.joblib",
        spec.output / f"{spec.stem}.json",
    )


def _cell_paths(cells: Path) -> list[Path]:
    return sorted(
        path
        for path in cells.glob("cell_*.joblib")
        if not path.stem.endswith("_observers")
    )


def _execute_jobs(
    jobs: list[Cell15Spec], config: Campaign15Config, workers: int
) -> list[Path]:
    if not jobs:
        return []
    completed: list[Path] = []
    pending: list[Cell15Spec] = []
    for spec in jobs:
        artifacts = _cell_artifacts(spec)
        if all(path.is_file() for path in artifacts):
            completed.append(artifacts[0])
        else:
            pending.append(replace(spec, force=any(path.exists() for path in artifacts)))
    print(
        f"[{jobs[0].stage}] {len(completed)} checkpointed, {len(pending)} pending",
        flush=True,
    )
    worker_count = max(1, int(workers))
    with threadpool_limits(limits=1):
        if worker_count == 1:
            for index, spec in enumerate(pending, start=1):
                completed.append(run_cell(spec, config))
                print(
                    f"[{spec.stage}] cells {index}/{len(pending)} "
                    f"({spec.mechanism} c{spec.candidate} m{spec.matrix_id})",
                    flush=True,
                )
        else:
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(run_cell, spec, config): spec for spec in pending
                }
                for index, future in enumerate(as_completed(futures), start=1):
                    spec = futures[future]
                    completed.append(future.result())
                    print(
                        f"[{spec.stage}] cells {index}/{len(pending)} "
                        f"({spec.mechanism} c{spec.candidate} m{spec.matrix_id})",
                        flush=True,
                    )
    return sorted(completed)


def _artifact_hashes(output: Path) -> dict[str, str]:
    roots = [output / "cells", output / "auxiliary"]
    paths = sorted(
        path
        for root in roots
        if root.exists()
        for path in root.rglob("*")
        if path.is_file()
    )
    return {str(path.relative_to(output)): sha256_file(path) for path in paths}


def _seal_generation(output: Path, cell_count: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": "fep-surprise-15-generation-manifest-v1",
        "cell_count": cell_count,
        "artifacts": _artifact_hashes(output),
    }
    payload["generation_id"] = canonical_digest(payload)
    (output / "generation_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _verify_generation(output: Path, expected_cells: int) -> dict[str, Any]:
    payload = json.loads(
        (output / "generation_manifest.json").read_text(encoding="utf-8")
    )
    identifier = payload.pop("generation_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("generation identifier mismatch")
    payload["generation_id"] = identifier
    if payload["cell_count"] != expected_cells:
        raise ValueError("generated cell count differs from frozen design")
    if payload["artifacts"] != _artifact_hashes(output):
        raise ValueError("generated artifact hashes changed")
    return payload


def _replay_one(original_name: str, config: Campaign15Config) -> dict[str, Any]:
    original_path = Path(original_name)
    original = load_cell(original_path)
    metadata = original["metadata"]
    original_model_path = original_path.with_name(
        original_path.stem + "_observers.joblib"
    )
    original_model = load_observers(original_model_path)
    with tempfile.TemporaryDirectory(prefix="fep15-replay-") as temporary:
        replayed_path = run_cell(
            Cell15Spec(
                stage=str(metadata["stage"]),
                matrix_id=int(metadata["matrix_id"]),
                candidate=str(metadata["candidate"]),
                mechanism=str(metadata["mechanism"]),
                output=Path(temporary),
                force=True,
            ),
            config,
        )
        replayed = load_cell(replayed_path)
        replayed_model = load_observers(
            replayed_path.with_name(replayed_path.stem + "_observers.joblib")
        )
        scientific = bool(
            metadata["scientific_digest"]
            == replayed["metadata"]["scientific_digest"]
        )
        payload_exact = bool(joblib.hash(original) == joblib.hash(replayed))
        model_exact = bool(joblib.hash(original_model) == joblib.hash(replayed_model))
    return {
        "stage": metadata["stage"],
        "matrix_id": metadata["matrix_id"],
        "candidate": metadata["candidate"],
        "mechanism": metadata["mechanism"],
        "scientific_digest_exact": scientific,
        "derived_payload_exact": payload_exact,
        "observer_model_exact": model_exact,
        "exact": bool(scientific and payload_exact and model_exact),
        "artifact": original_path.name,
    }


def _replay_cells(
    originals: list[Path], audits: Path, config: Campaign15Config, workers: int
) -> dict[str, Any]:
    audits.mkdir(parents=True, exist_ok=True)
    pending = []
    results = []
    for original in originals:
        audit_path = audits / f"{original.stem}.json"
        if audit_path.exists():
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if not audit.get("exact"):
                raise ValueError(f"prior replay mismatch: {original.name}")
            results.append(audit)
        else:
            pending.append(original)
    print(
        f"[replay] {len(results)} checkpointed, {len(pending)} pending", flush=True
    )
    worker_count = max(1, min(int(workers), 4))
    with threadpool_limits(limits=1):
        if worker_count == 1:
            iterator = ((path, _replay_one(str(path), config)) for path in pending)
            for index, (path, audit) in enumerate(iterator, start=1):
                audit_path = audits / f"{path.stem}.json"
                audit_path.write_text(
                    json.dumps(audit, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                results.append(audit)
                print(
                    f"[replay] cells {index}/{len(pending)} exact={audit['exact']}",
                    flush=True,
                )
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
                        json.dumps(audit, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    results.append(audit)
                    print(
                        f"[replay] cells {index}/{len(pending)} exact={audit['exact']}",
                        flush=True,
                    )
                    if not audit["exact"]:
                        for other in futures:
                            other.cancel()
                        raise ValueError(f"replay mismatch: {path.name}")
    return {
        "cells": len(results),
        "all_exact": bool(results and all(item["exact"] for item in results)),
        "fresh_process_workers": worker_count,
    }


def _cohort_integrity(
    cells: Path, stage: str, config: Campaign15Config
) -> dict[str, bool]:
    jobs = _stage_jobs(cells.parent, stage, config)
    paths = _cell_paths(cells)
    expected_future_batches = len(
        (config.development if stage == "development" else config.confirmation).landmarks
    ) * (config.development if stage == "development" else config.confirmation).branches
    complete_reference = True
    complete_future_batches = True
    for path in paths:
        cell = load_cell(path)
        reference = cell["metadata"]["reference"]
        complete_reference &= bool(
            reference["completed_lineages"] == reference["requested_lineages"]
        )
        complete_future_batches &= bool(len(cell["trace_lengths"]) == expected_future_batches)
    return {
        "expected_cell_count": len(paths) == len(jobs),
        "all_reference_lineages_retained": complete_reference,
        "all_future_batches_recorded": complete_future_batches,
    }


def develop(run_root: Path, config: Campaign15Config, workers: int) -> Path:
    registration = registration_path(run_root, config.profile)
    design = verify_registration(registration, config)
    output = development_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_development(output, registration, config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    jobs = _stage_jobs(output, "development", config)
    manifest_path = output / "generation_manifest.json"
    if manifest_path.exists():
        generation = _verify_generation(output, len(jobs))
    else:
        paths = _execute_jobs(jobs, config, workers)
        if len(paths) != len(jobs):
            raise RuntimeError("development generation did not complete")
        generation = _seal_generation(output, len(paths))
    originals = _cell_paths(output / "cells")
    replay = _replay_cells(
        originals, output / "replay_audits", config, max(1, min(workers, 2))
    )
    if not replay["all_exact"] or replay["cells"] != len(jobs):
        raise ValueError("development replay gate failed")
    if design["sources"] != _source_hashes():
        raise ValueError("scientific source changed during development")
    model_summary = fit_development_models(
        output / "cells", config, output / "predictors.joblib"
    )
    cohort = _cohort_integrity(output / "cells", "development", config)
    if not all(cohort.values()):
        raise ValueError(f"development cohort integrity failed: {cohort}")
    seal: dict[str, Any] = {
        "format": "fep-surprise-15-development-v1",
        "status": "sealed_after_exact_replay_and_model_freeze",
        "registration_id": design["registration_id"],
        "profile": config.profile,
        "generation_id": generation["generation_id"],
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


def verify_development(
    path: Path, registration: Path, config: Campaign15Config
) -> dict[str, Any]:
    design = verify_registration(registration, config)
    verify_checksums(path)
    payload = json.loads((path / "development.json").read_text(encoding="utf-8"))
    identifier = payload.pop("development_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("development identifier mismatch")
    payload["development_id"] = identifier
    if payload["registration_id"] != design["registration_id"]:
        raise ValueError("development references another registration")
    if not payload["replay"]["all_exact"] or not all(
        payload["cohort_integrity"].values()
    ):
        raise ValueError("development integrity gate is not complete")
    return payload


def generate_confirmation(
    run_root: Path, config: Campaign15Config, workers: int
) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    design = verify_registration(registration, config)
    development_seal = verify_development(development, registration, config)
    output = confirmation_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_confirmation(output, registration, development, config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    jobs = _stage_jobs(output, "confirmation", config)
    if (output / "generation_manifest.json").exists():
        generation = _verify_generation(output, len(jobs))
    else:
        paths = _execute_jobs(jobs, config, workers)
        if len(paths) != len(jobs):
            raise RuntimeError("confirmation generation did not complete")
        generation = _seal_generation(output, len(paths))
    cohort = _cohort_integrity(output / "cells", "confirmation", config)
    if not all(cohort.values()):
        raise ValueError(f"confirmation cohort integrity failed: {cohort}")
    if design["sources"] != _source_hashes():
        raise ValueError("scientific source changed during confirmation generation")
    seal: dict[str, Any] = {
        "format": "fep-surprise-15-confirmation-v1",
        "status": "sealed_before_replay_without_scientific_analysis",
        "registration_id": design["registration_id"],
        "development_id": development_seal["development_id"],
        "profile": config.profile,
        "generation_id": generation["generation_id"],
        "cells": len(jobs),
        "cohort_integrity": cohort,
        "analysis_artifacts_present": False,
    }
    seal["confirmation_id"] = canonical_digest(seal)
    (output / "confirmation.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(output)
    return output


def verify_confirmation(
    path: Path,
    registration: Path,
    development: Path,
    config: Campaign15Config,
) -> dict[str, Any]:
    design = verify_registration(registration, config)
    development_seal = verify_development(development, registration, config)
    verify_checksums(path)
    payload = json.loads((path / "confirmation.json").read_text(encoding="utf-8"))
    identifier = payload.pop("confirmation_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("confirmation identifier mismatch")
    payload["confirmation_id"] = identifier
    if payload["registration_id"] != design["registration_id"]:
        raise ValueError("confirmation references another registration")
    if payload["development_id"] != development_seal["development_id"]:
        raise ValueError("confirmation references another development stage")
    if payload.get("analysis_artifacts_present"):
        raise ValueError("confirmation violated the analysis firewall")
    return payload


def replay_confirmation(
    run_root: Path, config: Campaign15Config, workers: int
) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    confirmation = confirmation_path(run_root, config.profile)
    confirmation_seal = verify_confirmation(
        confirmation, registration, development, config
    )
    output = replay_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_replay(output, confirmation, registration, development, config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    originals = _cell_paths(confirmation / "cells")
    replay = _replay_cells(originals, output / "audits", config, workers)
    if not replay["all_exact"] or replay["cells"] != confirmation_seal["cells"]:
        raise ValueError("confirmation replay gate failed")
    design = verify_registration(registration, config)
    if design["sources"] != _source_hashes():
        raise ValueError("scientific source changed during confirmation replay")
    payload: dict[str, Any] = {
        "format": "fep-surprise-15-confirmation-replay-v1",
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


def verify_replay(
    path: Path,
    confirmation: Path,
    registration: Path,
    development: Path,
    config: Campaign15Config,
) -> dict[str, Any]:
    confirmation_seal = verify_confirmation(
        confirmation, registration, development, config
    )
    verify_checksums(path)
    payload = json.loads((path / "replay.json").read_text(encoding="utf-8"))
    identifier = payload.pop("replay_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("confirmation replay identifier mismatch")
    payload["replay_id"] = identifier
    if payload["confirmation_id"] != confirmation_seal["confirmation_id"]:
        raise ValueError("replay references another confirmation stage")
    if not payload["all_exact"]:
        raise ValueError("confirmation replay was not exact")
    return payload


def analyze(run_root: Path, config: Campaign15Config) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    confirmation = confirmation_path(run_root, config.profile)
    replay = replay_path(run_root, config.profile)
    design = verify_registration(registration, config)
    development_seal = verify_development(development, registration, config)
    confirmation_seal = verify_confirmation(
        confirmation, registration, development, config
    )
    replay_seal = verify_replay(
        replay, confirmation, registration, development, config
    )
    destination = analysis_path(run_root, config.profile)
    if destination.exists():
        verify_checksums(destination)
        return destination
    validation = verify_validation(
        validation_path(run_root, config.profile), config
    )["results"]
    cohort = _cohort_integrity(confirmation / "cells", "confirmation", config)
    integrity = {
        "validation_all_pass": bool(validation["all_pass"]),
        "trace_and_endpoint_validation": bool(
            validation["traced_untraced_exact"]
            and validation["strict8_fixture_positive"]
        ),
        "deterministic_observers": bool(
            validation["repeated_model_hash_exact"]
        ),
        "scale_invariance": bool(
            validation["primary_scale_within_tolerance"]
        ),
        "relabeling_invariance": bool(
            validation["primary_relabel_within_tolerance"]
        ),
        "seed_firewall": bool(
            validation["development_confirmation_seed_domains_distinct"]
        ),
        "development_exact_replay": bool(
            development_seal["replay"]["all_exact"]
        ),
        "confirmation_exact_replay": bool(replay_seal["all_exact"]),
        "complete_confirmation_cohort": bool(all(cohort.values())),
        "source_tree_matches_registration": bool(
            design["sources"] == _source_hashes()
        ),
        "analysis_firewall_intact": bool(
            not confirmation_seal["analysis_artifacts_present"]
        ),
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
            "format": "fep-surprise-15-analysis-v1",
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
    output: dict[str, Any] = {"profile": profile}
    for name, path in (
        ("validation", validation_path(run_root, profile)),
        ("registration", registration_path(run_root, profile)),
        ("development", development_path(run_root, profile)),
        ("confirmation", confirmation_path(run_root, profile)),
        ("confirmation_replay", replay_path(run_root, profile)),
        ("analysis", analysis_path(run_root, profile)),
    ):
        entry: dict[str, Any] = {
            "exists": path.exists(),
            "sealed": (path / "SHA256SUMS").exists(),
        }
        cells = path / "cells"
        if cells.exists():
            entry["cell_artifacts"] = len(_cell_paths(cells))
        audits = path / "audits"
        if audits.exists():
            entry["replay_audits"] = len(list(audits.glob("cell_*.json")))
        output[name] = entry
    return output
