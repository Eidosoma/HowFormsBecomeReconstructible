from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import joblib

from . import compat
from .analysis import analyze_confirmation, fit_development_models
from .config import CampaignConfig, profile_config
from .integrity import (
    atomic_destination,
    canonical_digest,
    sha256_file,
    verify_checksums,
    write_checksums,
)
from .worker import CellSpec, load_cell, run_cell


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
CODEX_ROOT = compat.CODEX_ROOT
FORMAT = "fep-surprise-registration-v1"
CAMPAIGN_SOURCES = tuple(
    str(path.relative_to(CAMPAIGN_ROOT))
    for path in sorted((CAMPAIGN_ROOT / "fep_surprise").glob("*.py"))
)
PARENT_SOURCES = (
    "plastic_heredity/config.py",
    "plastic_heredity/generative_nulls.py",
    "plastic_heredity/regime_confirmation.py",
    "plastic_heredity/seeds.py",
    "plastic_heredity/simulator.py",
)


def _runtime_manifest() -> dict[str, Any]:
    packages = {}
    for name in ("numpy", "scipy", "scikit-learn", "pandas", "joblib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }


def _source_hashes() -> dict[str, str]:
    values = {
        name: sha256_file(CAMPAIGN_ROOT / name) for name in CAMPAIGN_SOURCES
    }
    values.update({name: sha256_file(CODEX_ROOT / name) for name in PARENT_SOURCES})
    values["PREREGISTRATION.md"] = sha256_file(CAMPAIGN_ROOT / "PREREGISTRATION.md")
    return values


def protocol(config: CampaignConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": FORMAT,
        "status": "sealed_before_scientific_matrix_generation",
        "title": "Cross-fitted compositional-surprise cycle",
        "config": config.to_dict(),
        "landscape": {
            "conditioning": "beta and simulator contract",
            "training_states": "independent post-burn-in pre-fission parents",
            "transform": "pseudocount-0.5 proportions, CLR, reference-only PCA",
            "primary_estimators": [
                (
                    "trajectory-cross-validated cosine shelf-occupancy mixture "
                    "with gamma within-shelf residual density"
                ),
                "k=20 nearest-neighbour density in CLR/PCA coordinates",
            ],
            "primary_reference": "one viable-state density scores every growth phase",
            "phase_conditioned_density": "secondary calibration only",
        },
        "endpoint": {
            "name": "primary_all8",
            "first_break": "first H<=0.90",
            "inheritance": "eight consecutive strict H>0.90 boundaries after break",
            "coherence": "all 28 daughter pairs strict H>0.90",
            "distinctness": "all eight daughters inclusive H<=0.85 to pre-break parent",
        },
        "primary_cycle_contrasts": {
            "shock": "S(daughter)-S(parent)>0",
            "growth": "S(next parent)-S(launch daughter)<0",
            "break_excess": "break shock minus inherited shock >0",
            "strict_recovery_difference": (
                "post-break recovery in strict-8 positives minus failures <0"
            ),
        },
        "prediction": {
            "forecast_origin": "first break with eight later observable positions",
            "baseline": (
                "H10, timing, masses, growth steps, atlas distance, expected-flux "
                "alignment, and mean-field distance"
            ),
            "added": "parent/daughter shock and preceding-growth surprise profile",
            "primary_metric": "baseline-minus-enhanced branch log loss",
            "training": "development matrices only",
            "evaluation": "confirmation halves A and B separately",
        },
        "controls": [
            "exact simultaneous beta/composition relabeling",
            "wrong-beta landscape scoring",
            "homogeneous catalysis",
            "fission-only generation",
            "forced K=1 fixed-target landscape",
            "within-stratum outcome permutation",
        ],
        "inference": {
            "unit": "catalytic matrix",
            "bootstrap": config.bootstrap_repetitions,
            "randomization": config.randomization_repetitions,
            "multiplicity": "Holm within each registered primary family",
            "candidates_pooled": False,
            "branch_halves_pooled": False,
        },
        "claim_boundary": (
            "A positive result supports a beta-and-contract-conditioned, "
            "coarse-grained self-organizing probability landscape. It does not "
            "establish variational free energy, active inference, cognition, or "
            "nonphysical Platonic causation."
        ),
        "sources": _source_hashes(),
    }
    payload["registration_id"] = canonical_digest(payload)
    return payload


def registration_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile / "registration"


def development_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile / "development"


def confirmation_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile / "confirmation"


def replay_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile / "replay"


def register(run_root: Path, config: CampaignConfig) -> Path:
    destination = registration_path(run_root, config.profile)
    if destination.exists():
        verify_registration(destination, config)
        return destination
    with atomic_destination(destination) as output:
        payload = protocol(config)
        (output / "protocol.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "runtime.json").write_text(
            json.dumps(_runtime_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output / "README.md").write_text(
            "# Sealed compositional-surprise protocol\n\n"
            f"Registration ID: `{payload['registration_id']}`\n\n"
            "This bundle was written before this profile generated scientific matrices.\n",
            encoding="utf-8",
        )
        write_checksums(output)
    return destination


def verify_registration(path: Path, config: CampaignConfig) -> dict[str, Any]:
    verify_checksums(path)
    payload = json.loads((path / "protocol.json").read_text(encoding="utf-8"))
    if payload.get("format") != FORMAT:
        raise ValueError("unsupported registration format")
    identifier = payload.pop("registration_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("registration identifier mismatch")
    payload["registration_id"] = identifier
    expected_config = json.loads(json.dumps(config.to_dict()))
    if payload["config"] != expected_config:
        raise ValueError("registration profile differs from requested profile")
    if payload["sources"] != _source_hashes():
        raise ValueError("registered scientific source changed")
    return payload


def _stage_jobs(
    output: Path,
    stage: str,
    config: CampaignConfig,
) -> list[CellSpec]:
    scale = config.development if stage == "development" else config.confirmation
    mechanisms = ("NATURAL_GARD",) if stage == "development" else (
        "NATURAL_GARD",
        "HOMOGENEOUS_GENERATIVE",
        "FISSION_ONLY_GENERATIVE",
    )
    cells = output / "cells"
    return [
        CellSpec(
            stage=stage,
            matrix_id=matrix,
            candidate=candidate,
            mechanism=mechanism,
            output=cells,
            save_landscape=stage == "confirmation" and mechanism == "NATURAL_GARD",
        )
        for mechanism in mechanisms
        for candidate in ("02", "03")
        for matrix in range(scale.matrices)
    ]


def _execute_jobs(jobs: list[CellSpec], config: CampaignConfig, workers: int) -> list[Path]:
    completed = []
    pending = []
    for spec in jobs:
        target = spec.output / (
            f"cell_{spec.stage}_{spec.mechanism}_c{spec.candidate}_m{spec.matrix_id:04d}.joblib"
        )
        if target.exists():
            completed.append(target)
        else:
            pending.append(spec)
    print(
        f"[{jobs[0].stage}] {len(completed)} checkpointed, {len(pending)} pending",
        flush=True,
    )
    if workers <= 1:
        for index, spec in enumerate(pending, start=1):
            completed.append(run_cell(spec, config))
            print(f"[{spec.stage}] cells {index}/{len(pending)}", flush=True)
    else:
        try:
            executor = ProcessPoolExecutor(max_workers=workers)
        except PermissionError:
            print(
                f"[{jobs[0].stage}] process semaphores unavailable; "
                "falling back to one worker",
                flush=True,
            )
            return _execute_jobs(jobs, config, 1)
        with executor:
            futures = {executor.submit(run_cell, spec, config): spec for spec in pending}
            for index, future in enumerate(as_completed(futures), start=1):
                spec = futures[future]
                completed.append(future.result())
                print(
                    f"[{spec.stage}] cells {index}/{len(pending)} "
                    f"({spec.mechanism} c{spec.candidate} m{spec.matrix_id})",
                    flush=True,
                )
    return sorted(completed)


def develop(run_root: Path, config: CampaignConfig, workers: int) -> Path:
    registration = registration_path(run_root, config.profile)
    design = verify_registration(registration, config)
    output = development_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_checksums(output)
        return output
    output.mkdir(parents=True, exist_ok=True)
    (output / "stage_state.json").write_text(
        json.dumps(
            {
                "status": "running_resumable",
                "registration_id": design["registration_id"],
                "profile": config.profile,
            },
            indent=2,
        )
        + "\n"
    )
    jobs = _stage_jobs(output, "development", config)
    paths = _execute_jobs(jobs, config, workers)
    model_summary = fit_development_models(
        output / "cells", config, output / "predictors.joblib"
    )
    seal: dict[str, Any] = {
        "format": "fep-surprise-development-v1",
        "status": "sealed",
        "registration_id": design["registration_id"],
        "profile": config.profile,
        "cells": len(paths),
        "models": model_summary,
    }
    seal["development_id"] = canonical_digest(seal)
    (output / "development.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n"
    )
    (output / "stage_state.json").write_text(
        json.dumps({"status": "sealed", "development_id": seal["development_id"]}, indent=2)
        + "\n"
    )
    write_checksums(output)
    return output


def verify_development(path: Path, registration: Path, config: CampaignConfig) -> dict[str, Any]:
    design = verify_registration(registration, config)
    verify_checksums(path)
    payload = json.loads((path / "development.json").read_text(encoding="utf-8"))
    identifier = payload.pop("development_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("development identifier mismatch")
    payload["development_id"] = identifier
    if payload["registration_id"] != design["registration_id"]:
        raise ValueError("development references another registration")
    return payload


def confirm(run_root: Path, config: CampaignConfig, workers: int) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    design = verify_registration(registration, config)
    model_seal = verify_development(development, registration, config)
    output = confirmation_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_checksums(output)
        return output
    output.mkdir(parents=True, exist_ok=True)
    (output / "stage_state.json").write_text(
        json.dumps(
            {
                "status": "running_resumable",
                "registration_id": design["registration_id"],
                "development_id": model_seal["development_id"],
                "profile": config.profile,
            },
            indent=2,
        )
        + "\n"
    )
    paths = _execute_jobs(_stage_jobs(output, "confirmation", config), config, workers)
    metrics = analyze_confirmation(
        output / "cells",
        development / "predictors.joblib",
        config,
        output,
    )
    seal: dict[str, Any] = {
        "format": "fep-surprise-confirmation-v1",
        "status": "sealed_before_replay",
        "registration_id": design["registration_id"],
        "development_id": model_seal["development_id"],
        "profile": config.profile,
        "cells": len(paths),
        "decision": metrics["decision"],
    }
    seal["confirmation_id"] = canonical_digest(seal)
    (output / "confirmation.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n"
    )
    (output / "stage_state.json").write_text(
        json.dumps({"status": "sealed", "confirmation_id": seal["confirmation_id"]}, indent=2)
        + "\n"
    )
    write_checksums(output)
    return output


def replay(run_root: Path, config: CampaignConfig) -> Path:
    registration = registration_path(run_root, config.profile)
    development = development_path(run_root, config.profile)
    confirmation = confirmation_path(run_root, config.profile)
    verify_development(development, registration, config)
    verify_checksums(confirmation)
    output = replay_path(run_root, config.profile)
    if (output / "SHA256SUMS").exists():
        verify_checksums(output)
        return output
    audits = output / "cells"
    audits.mkdir(parents=True, exist_ok=True)
    originals = sorted(
        path
        for path in (confirmation / "cells").glob("cell_*.joblib")
        if not path.name.endswith("_landscape.joblib")
    )
    equal = True
    for index, original_path in enumerate(originals, start=1):
        original = load_cell(original_path)
        meta = original["metadata"]
        audit_path = audits / (original_path.stem + ".json")
        if audit_path.exists():
            audit = json.loads(audit_path.read_text())
            equal &= bool(audit["exact"])
            continue
        with tempfile.TemporaryDirectory(prefix="fep-replay-", dir=output) as temporary:
            spec = CellSpec(
                stage="confirmation",
                matrix_id=int(meta["matrix_id"]),
                candidate=str(meta["candidate"]),
                mechanism=str(meta["mechanism"]),
                output=Path(temporary),
                save_landscape=False,
                force=True,
            )
            replayed_path = run_cell(spec, config)
            replayed = load_cell(replayed_path)
            scientific = meta["scientific_digest"] == replayed["metadata"][
                "scientific_digest"
            ]
            payload = joblib.hash(original) == joblib.hash(replayed)
            exact = bool(scientific and payload)
            equal &= exact
            audit_path.write_text(
                json.dumps(
                    {
                        "matrix_id": meta["matrix_id"],
                        "candidate": meta["candidate"],
                        "mechanism": meta["mechanism"],
                        "scientific_digest_exact": scientific,
                        "derived_payload_exact": payload,
                        "exact": exact,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        print(f"[replay] cells {index}/{len(originals)} exact={exact}", flush=True)
        if not exact:
            raise ValueError(f"replay mismatch: {original_path.name}")
    payload = {
        "format": "fep-surprise-replay-v1",
        "cells": len(originals),
        "all_exact": bool(equal),
    }
    (output / "replay.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    write_checksums(output)
    return output


def status(run_root: Path, profile: str) -> dict[str, Any]:
    output: dict[str, Any] = {"profile": profile}
    for name, path in (
        ("registration", registration_path(run_root, profile)),
        ("development", development_path(run_root, profile)),
        ("confirmation", confirmation_path(run_root, profile)),
        ("replay", replay_path(run_root, profile)),
    ):
        entry: dict[str, Any] = {"exists": path.exists(), "sealed": False}
        if path.exists():
            entry["sealed"] = (path / "SHA256SUMS").exists()
            cells = path / "cells"
            if cells.exists():
                entry["cell_artifacts"] = len(
                    [
                        p
                        for p in cells.glob("cell_*.joblib")
                        if not p.name.endswith("_landscape.joblib")
                    ]
                )
        output[name] = entry
    detached_status = run_root.resolve() / profile / "full-run.status"
    if detached_status.exists():
        output["detached_run_status"] = detached_status.read_text().strip()
    detached_pid = run_root.resolve() / profile / "full-run.pid"
    if detached_pid.exists():
        pid_text = detached_pid.read_text().strip()
        output["detached_run_pid"] = pid_text
        try:
            pid = int(pid_text)
            if pid <= 0:
                raise ValueError("PID must be positive")
            os.kill(pid, 0)
        except (OSError, ValueError):
            output["detached_run_alive"] = False
        else:
            output["detached_run_alive"] = True
    for key, filename in (
        ("detached_run_session", "full-run.session"),
        ("detached_run_started", "full-run.started"),
        ("detached_run_finished", "full-run.finished"),
    ):
        metadata = run_root.resolve() / profile / filename
        if metadata.exists():
            output[key] = metadata.read_text().strip()
    return output
