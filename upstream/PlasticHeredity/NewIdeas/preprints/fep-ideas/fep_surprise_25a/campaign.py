from __future__ import annotations

import json
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any

import joblib

from fep_surprise_15.integrity import (
    atomic_destination,
    canonical_digest,
    sha256_file,
    verify_checksums,
    write_checksums,
)
from fep_surprise_25 import campaign as base_campaign
from fep_surprise_25.budget import (
    TimeBudgetExhausted,
    budget_status,
    ensure_budget,
    guard_budget,
)
from fep_surprise_25.config import ACTUAL_ATLASES, CANDIDATES, STRATA, Campaign25Config
from fep_surprise_25.config import profile_config as base_profile_config

from .analysis import analyze_confirmation
from .config import (
    AMENDMENT_LABEL,
    EXPECTED_FULL_REGISTRATION_ID,
    REGISTRATION_PROJECTION_CEILING_SECONDS,
    profile_config,
    reference_lineages,
)
from .worker import (
    Cell25Spec,
    TERMINAL_CAUSE_CODES,
    deterministic_reference_indices,
    load_atlases,
    load_design,
    load_futures,
    prepare_cell,
    run_futures,
)
from .validation import exposed_matrix189_reference_regression


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
FORMAT = "fep-surprise-25a-registration-v1"


def profile_path(run_root: Path, profile: str) -> Path:
    return run_root.resolve() / profile


def stage_path(run_root: Path, profile: str, stage: str) -> Path:
    return profile_path(run_root, profile) / stage


def _source_profile(source_run_root: Path, profile: str) -> Path:
    return source_run_root.resolve() / profile


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_bundle(source_run_root: Path, profile: str) -> dict[str, Any]:
    base_config = base_profile_config(profile)
    registration = base_campaign.verify_registration(
        base_campaign.registration_path(source_run_root, profile), base_config
    )
    screened = base_campaign.verify_screen(
        base_campaign.screen_path(source_run_root, profile), base_config
    )
    if profile == "full" and registration["registration_id"] != EXPECTED_FULL_REGISTRATION_ID:
        raise ValueError("full amendment source is not the registered failed Experiment 2.5 capsule")
    if not screened["seal"]["replay"]["all_exact"]:
        raise ValueError("source screen did not replay exactly")
    if not screened["selection"]["complete"]:
        raise ValueError("source screen selection is incomplete")
    return {"registration": registration, "screen": screened}


def config_for_source(source_run_root: Path, profile: str) -> Campaign25Config:
    bundle = _source_bundle(source_run_root, profile)
    return profile_config(profile, bundle["registration"]["registration_id"])


def _inventory(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _source_hashes() -> dict[str, str]:
    output = {
        f"base::{name}": digest for name, digest in base_campaign._source_hashes().items()
    }
    for path in sorted((CAMPAIGN_ROOT / "fep_surprise_25a").glob("*.py")):
        output[str(path.relative_to(CAMPAIGN_ROOT))] = sha256_file(path)
    for name in ("EXPERIMENT_2_5_AMENDMENT_1.md", "requirements-25-lock.txt"):
        output[name] = sha256_file(CAMPAIGN_ROOT / name)
    return output


def audit_source(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> Path:
    if source_run_root.resolve() == run_root.resolve():
        raise ValueError("source and amendment run roots must differ")
    ensure_budget(run_root, config)
    guard_budget(run_root, config, "source-audit")
    bundle = _source_bundle(source_run_root, config.profile)
    destination = stage_path(run_root, config.profile, "source_audit")
    if destination.exists():
        verify_source_audit(source_run_root, run_root, config)
        return destination
    source_profile = _source_profile(source_run_root, config.profile)
    source_confirmation = source_profile / "confirmation"
    partial_designs = len(list((source_confirmation / "cells").glob("*_design.joblib")))
    main_futures = len(list((source_confirmation / "cells").glob("*_futures.joblib")))
    design_sealed = (source_confirmation / "confirmation_design.json").exists()
    if config.profile == "full" and (main_futures != 0 or design_sealed):
        raise ValueError(
            "source capsule no longer represents the disclosed pre-outcome failure"
        )
    with atomic_destination(destination) as output:
        payload = {
            "format": "fep-surprise-25a-source-audit-v1",
            "status": "failed_source_capsule_frozen_read_only",
            "source_profile": str(source_profile),
            "source_registration_id": bundle["registration"]["registration_id"],
            "source_screen_seal_id": bundle["screen"]["seal"]["screen_seal_id"],
            "source_screen_replay_exact": True,
            "source_selection_id": bundle["screen"]["selection"]["selection_id"],
            "source_inventory": _inventory(source_profile),
            "disclosure": {
                "failure_stage": "pre_confirmation_design_seal",
                "partial_design_artifacts": partial_designs,
                "confirmation_design_sealed": design_sealed,
                "main_future_artifacts": main_futures,
                "reference_only_diagnostics_exposed": True,
                "known_shortfall_matrix": 189,
                "known_shortfall_atlas": "sigma_500",
                "partial_designs_reused": False,
            },
        }
        payload["source_audit_id"] = canonical_digest(payload)
        (output / "source_audit.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    return destination


def verify_source_audit(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> dict[str, Any]:
    path = stage_path(run_root, config.profile, "source_audit")
    verify_checksums(path)
    payload = _json(path / "source_audit.json")
    identifier = payload.pop("source_audit_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("source audit identifier mismatch")
    payload["source_audit_id"] = identifier
    source_profile = _source_profile(source_run_root, config.profile)
    if payload["source_profile"] != str(source_profile):
        raise ValueError("amendment source path changed")
    if payload["source_inventory"] != _inventory(source_profile):
        raise ValueError("failed Experiment 2.5 capsule changed after amendment audit")
    bundle = _source_bundle(source_run_root, config.profile)
    if payload["source_registration_id"] != bundle["registration"]["registration_id"]:
        raise ValueError("source registration changed")
    return payload


def validate_stage(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> Path:
    source_audit = verify_source_audit(source_run_root, run_root, config)
    guard_budget(run_root, config, "validation")
    destination = stage_path(run_root, config.profile, "validation")
    if destination.exists():
        verify_validation(run_root, config)
        return destination
    with atomic_destination(destination) as output:
        foundation = base_campaign.validate(config, output / "foundation")
        import numpy as np

        lineage = np.repeat(np.arange(4), 20)
        fission = np.tile(np.arange(20), 4)
        spec = Cell25Spec(0, "02", "stable", Path("unused"), output)
        first, metadata = deterministic_reference_indices(
            lineage, fission, 20, config.master_seed, spec, "native"
        )
        second, _ = deterministic_reference_indices(
            lineage, fission, 20, config.master_seed, spec, "native"
        )
        source_registration = _source_bundle(source_run_root, config.profile)["registration"]
        matrix189 = exposed_matrix189_reference_regression(
            source_run_root,
            source_registration["config"]["master_seed"],
            config.profile,
            config.confirmation.reference_burnin,
            config.confirmation.reference_fissions,
            config.phase_grid,
        )
        results = {
            "format": "fep-surprise-25a-validation-v1",
            "foundation_all_pass": bool(foundation["all_pass"]),
            "source_audit_id": source_audit["source_audit_id"],
            "reference_selector_exact": bool(np.array_equal(first, second)),
            "reference_selector_half_counts": metadata["available_by_half"],
            "terminal_cause_codes_unique": len(set(TERMINAL_CAUSE_CODES.values()))
            == len(TERMINAL_CAUSE_CODES),
            "source_and_amendment_seeds_distinct": bool(
                config.master_seed
                != source_registration["config"]["master_seed"]
            ),
            "exposed_matrix189_scientific_scale_regression": matrix189,
        }
        results["all_pass"] = bool(
            results["foundation_all_pass"]
            and results["reference_selector_exact"]
            and results["terminal_cause_codes_unique"]
            and results["source_and_amendment_seeds_distinct"]
            and matrix189["all_parity_halves_at_least_600"]
        )
        seal = {
            "format": "fep-surprise-25a-validation-seal-v1",
            "profile": config.profile,
            "results": results,
            "runtime": base_campaign._runtime_manifest(),
            "sources": _source_hashes(),
        }
        if not seal["runtime"]["lock_matches"] or not results["all_pass"]:
            raise ValueError("Experiment 2.5a validation failed")
        seal["validation_id"] = canonical_digest(seal)
        (output / "validation.json").write_text(
            json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    return destination


def verify_validation(run_root: Path, config: Campaign25Config) -> dict[str, Any]:
    path = stage_path(run_root, config.profile, "validation")
    verify_checksums(path)
    payload = _json(path / "validation.json")
    identifier = payload.pop("validation_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("amendment validation identifier mismatch")
    payload["validation_id"] = identifier
    if payload["profile"] != config.profile or payload["sources"] != _source_hashes():
        raise ValueError("amendment validation source tree changed")
    if not payload["results"]["all_pass"]:
        raise ValueError("amendment validation is not passing")
    return payload


def _project(config: Campaign25Config, seconds_per_fission: float, seconds_per_fit: float) -> dict[str, float]:
    scale = config.confirmation
    reference_fissions = sum(
        reference_lineages(config.profile, atlas) * scale.reference_fissions
        for atlas in ACTUAL_ATLASES
    )
    nonreference_fissions = (
        len(scale.landmarks) * scale.damage_perturbations * 2 * scale.damage_horizon
        + len(scale.landmarks) * 11 * scale.pilot_branches * scale.pilot_horizon
        + len(scale.landmarks) * 11 * scale.branches * scale.horizon
        + len(scale.landmarks) * 11 * scale.durability_events * scale.durability_horizon
    )
    per_cell = reference_fissions + nonreference_fissions
    cells = scale.selected_per_stratum * len(STRATA) * len(CANDIDATES)
    worker_factor = 1 / config.generation_workers + 1 / config.replay_workers
    raw = 600.0 + cells * (
        per_cell * seconds_per_fission + len(ACTUAL_ATLASES) * seconds_per_fit
    ) * worker_factor
    return {
        "confirmation_cells": float(cells),
        "reference_fissions_per_cell_each_pass": float(reference_fissions),
        "total_fissions_per_cell_each_pass": float(per_cell),
        "raw_remaining_seconds": float(raw),
        "conservative_remaining_seconds": float(raw * config.conservative_multiplier),
    }


def benchmark(run_root: Path, config: Campaign25Config, workers: int) -> Path:
    verify_validation(run_root, config)
    guard_budget(run_root, config, "benchmark")
    destination = stage_path(run_root, config.profile, "benchmark")
    if destination.exists():
        verify_benchmark(run_root, config)
        return destination
    with atomic_destination(destination) as output:
        seconds_per_fission, simulated = base_campaign._benchmark_dynamics(config)
        seconds_per_fit = base_campaign._benchmark_observer(config)
        projection = _project(config, seconds_per_fission, seconds_per_fit)
        elapsed = budget_status(run_root, config)["elapsed_seconds"]
        projection["conservative_total_seconds"] = (
            elapsed + projection["conservative_remaining_seconds"]
        )
        ceiling = (
            REGISTRATION_PROJECTION_CEILING_SECONDS
            if config.profile == "full"
            else config.graceful_stop_seconds
        )
        payload = {
            "format": "fep-surprise-25a-benchmark-v1",
            "profile": config.profile,
            "disposable_seed_domain": "experiment25a-benchmark-only-never-scientific",
            "seconds_per_fission": seconds_per_fission,
            "benchmark_fissions": simulated,
            "seconds_per_observer_fit": seconds_per_fit,
            "workers": int(workers),
            "projection": projection,
            "registration_ceiling_seconds": ceiling,
            "eligible_to_register": bool(
                (config.profile != "full" or workers >= config.generation_workers)
                and projection["conservative_total_seconds"] <= ceiling
            ),
            "sources": _source_hashes(),
        }
        payload["benchmark_id"] = canonical_digest(payload)
        (output / "benchmark.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(output)
    if not payload["eligible_to_register"]:
        raise TimeBudgetExhausted(
            "AMENDMENT_BENCHMARK_EXCEEDS_6H30_REGISTRATION_CEILING_NO_VERDICT"
        )
    return destination


def verify_benchmark(run_root: Path, config: Campaign25Config) -> dict[str, Any]:
    path = stage_path(run_root, config.profile, "benchmark")
    verify_checksums(path)
    payload = _json(path / "benchmark.json")
    identifier = payload.pop("benchmark_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("amendment benchmark identifier mismatch")
    payload["benchmark_id"] = identifier
    if payload["profile"] != config.profile or payload["sources"] != _source_hashes():
        raise ValueError("amendment benchmark source tree changed")
    if not payload["eligible_to_register"]:
        raise TimeBudgetExhausted("amendment benchmark forbids registration")
    return payload


def register(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> Path:
    audit = verify_source_audit(source_run_root, run_root, config)
    validation = verify_validation(run_root, config)
    timing = verify_benchmark(run_root, config)
    guard_budget(run_root, config, "registration")
    destination = stage_path(run_root, config.profile, "registration")
    if destination.exists():
        verify_registration(source_run_root, run_root, config)
        return destination
    with atomic_destination(destination) as output:
        payload = {
            "format": FORMAT,
            "status": "sealed_preoutcome_amendment_before_fresh_reference_generation",
            "title": "Experiment 2.5a — Goldilocks Boundary Amendment",
            "amendment": AMENDMENT_LABEL,
            "config": config.to_dict(),
            "source_audit_id": audit["source_audit_id"],
            "source_registration_id": audit["source_registration_id"],
            "source_screen_seal_id": audit["source_screen_seal_id"],
            "source_selection_id": audit["source_selection_id"],
            "validation_id": validation["validation_id"],
            "benchmark_id": timing["benchmark_id"],
            "budget_start": ensure_budget(run_root, config),
            "protocol": "EXPERIMENT_2_5_AMENDMENT_1.md",
            "reference_policy": {
                "regular_lineages": reference_lineages(config.profile, "native"),
                "sigma_500_lineages": reference_lineages(config.profile, "sigma_500"),
                "selected_states_per_parity_half": config.confirmation.training_subsample,
                "terminal_prefixes_retained": True,
                "retries_or_replacements": False,
            },
            "stage_order": [
                "source_capsule_audit",
                "validation",
                "disposable_benchmark",
                "amendment_registration",
                "fresh_reference_damage_and_pilot_designs",
                "confirmation_design_seal",
                "fresh_main_and_durability_outcomes",
                "outcome_seal",
                "fresh_process_exact_replay",
                "analysis",
            ],
            "analysis_firewall": "No outcome analysis before exact replay of all 96 full-profile cells.",
            "claim_boundary": (
                "At most simulator-specific viability-aware regime-gated rehoming and "
                "incremental calibrated surprise; never FEP, active inference, agency, "
                "prebiotic chemistry, universal origins, or Platonic causation."
            ),
            "sources": _source_hashes(),
        }
        payload["registration_id"] = canonical_digest(payload)
        (output / "protocol.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output / "README.md").write_text(
            "# Sealed Experiment 2.5a amendment\n\n"
            f"Registration ID: `{payload['registration_id']}`\n\n"
            "Sealed after source audit and disposable timing, before any fresh amended reference.\n",
            encoding="utf-8",
        )
        write_checksums(output)
    return destination


def verify_registration(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> dict[str, Any]:
    path = stage_path(run_root, config.profile, "registration")
    verify_checksums(path)
    payload = _json(path / "protocol.json")
    identifier = payload.pop("registration_id")
    if payload.get("format") != FORMAT or canonical_digest(payload) != identifier:
        raise ValueError("amendment registration seal is invalid")
    payload["registration_id"] = identifier
    if payload["config"] != json.loads(json.dumps(config.to_dict())):
        raise ValueError("amendment config differs from registration")
    if payload["sources"] != _source_hashes():
        raise ValueError("amendment source tree changed after registration")
    if payload["budget_start"] != ensure_budget(run_root, config):
        raise ValueError("amendment budget clock differs from registration")
    audit = verify_source_audit(source_run_root, run_root, config)
    if payload["source_audit_id"] != audit["source_audit_id"]:
        raise ValueError("registration references another source audit")
    return payload


def _confirmation_jobs(
    source_run_root: Path,
    output: Path,
    config: Campaign25Config,
) -> list[Cell25Spec]:
    bundle = _source_bundle(source_run_root, config.profile)
    selection = bundle["screen"]["selection"]
    jobs: list[Cell25Spec] = []
    cells = output / "cells"
    source_cells = base_campaign.screen_path(source_run_root, config.profile) / "cells"
    for stratum in STRATA:
        rows = selection["selected"][stratum]
        if len(rows) != config.confirmation.selected_per_stratum:
            raise ValueError(f"source selection quota changed for {stratum}")
        for row in rows:
            for candidate in CANDIDATES:
                jobs.append(
                    Cell25Spec(
                        int(row["matrix_id"]),
                        candidate,
                        stratum,
                        source_cells / str(row["artifact"]),
                        cells,
                    )
                )
    return jobs


def prepare_confirmation(
    source_run_root: Path,
    run_root: Path,
    config: Campaign25Config,
    workers: int,
) -> Path:
    registration = verify_registration(source_run_root, run_root, config)
    guard_budget(run_root, config, "prepare-confirmation")
    output = stage_path(run_root, config.profile, "confirmation")
    if (output / "confirmation_design.json").exists():
        verify_confirmation_design(source_run_root, run_root, config)
        return output
    output.mkdir(parents=True, exist_ok=True)
    jobs = _confirmation_jobs(source_run_root, output, config)
    base_campaign._parallel(
        jobs,
        prepare_cell,
        config,
        run_root,
        min(workers, config.generation_workers),
        lambda spec: (
            spec.design_path.is_file()
            and spec.atlas_path.is_file()
            and spec.metadata_path.is_file()
        ),
        lambda spec: spec.design_path,
        "amendment-confirmation-design",
    )
    if list((output / "cells").glob("*_futures.joblib")):
        raise ValueError("main outcomes exist before amended design seal")
    manifest = base_campaign._write_manifest(output, "design", len(jobs))
    if registration["sources"] != _source_hashes():
        raise ValueError("source changed during amended design generation")
    payload = {
        "format": "fep-surprise-25a-confirmation-design-v1",
        "status": "sealed_fresh_atlases_damage_metrics_and_pilots_before_main_outcomes",
        "registration_id": registration["registration_id"],
        "source_screen_seal_id": registration["source_screen_seal_id"],
        "design_id": manifest["design_id"],
        "cells": len(jobs),
        "main_future_artifacts_present": False,
        "partial_original_designs_reused": False,
    }
    payload["confirmation_design_id"] = canonical_digest(payload)
    (output / "confirmation_design.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output


def verify_confirmation_design(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> dict[str, Any]:
    registration = verify_registration(source_run_root, run_root, config)
    output = stage_path(run_root, config.profile, "confirmation")
    payload = _json(output / "confirmation_design.json")
    identifier = payload.pop("confirmation_design_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("amended confirmation design identifier mismatch")
    payload["confirmation_design_id"] = identifier
    if payload["registration_id"] != registration["registration_id"]:
        raise ValueError("amended design references another registration")
    base_campaign._verify_manifest(output, "design", int(payload["cells"]))
    return payload


def _amendment_cohort_integrity(
    output: Path, config: Campaign25Config, expected: int
) -> dict[str, Any]:
    base = base_campaign._cohort_integrity(output, config, expected)
    designs = sorted((output / "cells").glob("cell_*_design.joblib"))
    base.update(
        {
            "amendment_metadata_present": True,
            "reference_half_quotas_exact": True,
            "terminal_cause_shapes_exact": True,
        }
    )
    quota = config.confirmation.training_subsample
    for design_path in designs:
        design = load_design(design_path)
        base["amendment_metadata_present"] &= bool(
            design["metadata"].get("amendment") == AMENDMENT_LABEL
        )
        for metadata in design["metadata"]["reference"].values():
            base["reference_half_quotas_exact"] &= bool(
                metadata.get("selected_states_by_half") == [quota, quota]
            )
        future = load_futures(
            design_path.with_name(
                design_path.name.replace("_design.joblib", "_futures.joblib")
            )
        )
        base["terminal_cause_shapes_exact"] &= bool(
            future.get("terminal_cause", []).shape == future["complete"].shape
            and future.get("durability_terminal_cause", []).shape
            == future["durability_complete"].shape
        )
    return base


def generate_confirmation(
    source_run_root: Path,
    run_root: Path,
    config: Campaign25Config,
    workers: int,
) -> Path:
    design = verify_confirmation_design(source_run_root, run_root, config)
    output = stage_path(run_root, config.profile, "confirmation")
    if (output / "SHA256SUMS").exists():
        verify_confirmation(source_run_root, run_root, config)
        return output
    guard_budget(run_root, config, "generate-confirmation")
    jobs = _confirmation_jobs(source_run_root, output, config)
    base_campaign._parallel(
        jobs,
        run_futures,
        config,
        run_root,
        min(workers, config.generation_workers),
        lambda spec: spec.future_path.is_file(),
        lambda spec: spec.future_path,
        "amendment-main-futures",
    )
    if (output / "metrics.json").exists() or (output / "REPORT.md").exists():
        raise ValueError("analysis firewall violated inside confirmation directory")
    manifest = base_campaign._write_manifest(output, "futures", len(jobs))
    cohort = _amendment_cohort_integrity(output, config, len(jobs))
    boolean_checks = [
        bool(value)
        for key, value in cohort.items()
        if not key.endswith("retained")
    ]
    if not all(boolean_checks):
        raise ValueError(f"amended confirmation cohort integrity failed: {cohort}")
    payload = {
        "format": "fep-surprise-25a-confirmation-v1",
        "status": "sealed_main_and_durability_outcomes_without_analysis",
        "confirmation_design_id": design["confirmation_design_id"],
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


def verify_confirmation(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> dict[str, Any]:
    design = verify_confirmation_design(source_run_root, run_root, config)
    output = stage_path(run_root, config.profile, "confirmation")
    verify_checksums(output)
    payload = _json(output / "confirmation.json")
    identifier = payload.pop("confirmation_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("amended confirmation identifier mismatch")
    payload["confirmation_id"] = identifier
    if payload["confirmation_design_id"] != design["confirmation_design_id"]:
        raise ValueError("amended confirmation references another design")
    if payload["analysis_artifacts_present"]:
        raise ValueError("amended analysis firewall was violated")
    base_campaign._verify_manifest(output, "futures", int(payload["cells"]))
    return payload


def _replay_one(
    original_name: str,
    source_cells_name: str,
    config: Campaign25Config,
) -> dict[str, Any]:
    original_path = Path(original_name)
    design = load_design(original_path)
    atlas_path = original_path.with_name(
        original_path.name.replace("_design.joblib", "_atlases.joblib")
    )
    future_path = original_path.with_name(
        original_path.name.replace("_design.joblib", "_futures.joblib")
    )
    atlases = load_atlases(atlas_path)
    futures = load_futures(future_path)
    metadata = design["metadata"]
    screen_cell = Path(source_cells_name) / f"screen_m{int(metadata['matrix_id']):04d}.joblib"
    with tempfile.TemporaryDirectory(prefix="fep25a-confirmation-replay-") as temporary:
        spec = Cell25Spec(
            int(metadata["matrix_id"]),
            str(metadata["candidate"]),
            str(metadata["stratum"]),
            screen_cell,
            Path(temporary),
            force=True,
        )
        replay_design = load_design(prepare_cell(spec, config))
        replay_atlases = load_atlases(spec.atlas_path)
        replay_futures = load_futures(run_futures(spec, config))
    checks = {
        "design_exact": joblib.hash(design) == joblib.hash(replay_design),
        "atlas_exact": joblib.hash(atlases) == joblib.hash(replay_atlases),
        "futures_exact": joblib.hash(futures) == joblib.hash(replay_futures),
        "design_digest_exact": (
            metadata["scientific_digest"]
            == replay_design["metadata"]["scientific_digest"]
        ),
        "future_digest_exact": (
            futures["metadata"]["scientific_digest"]
            == replay_futures["metadata"]["scientific_digest"]
        ),
    }
    return {
        "matrix_id": int(metadata["matrix_id"]),
        "candidate": str(metadata["candidate"]),
        "stratum": str(metadata["stratum"]),
        "artifact": original_path.name,
        **checks,
        "exact": bool(all(checks.values())),
    }


def _replay_cells(
    designs: list[Path],
    output: Path,
    source_cells: Path,
    config: Campaign25Config,
    run_root: Path,
    workers: int,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    pending: list[Path] = []
    for path in designs:
        audit_path = output / f"{path.stem}.json"
        if audit_path.exists():
            audit = _json(audit_path)
            if not audit["exact"]:
                raise ValueError(f"prior amended replay mismatch: {path.name}")
            completed.append(audit)
        else:
            pending.append(path)
    with ProcessPoolExecutor(max_workers=max(1, workers)) as executor:
        iterator = iter(pending)
        active: dict[Any, Path] = {}
        for _ in range(min(max(1, workers), len(pending))):
            path = next(iterator)
            active[
                executor.submit(_replay_one, str(path), str(source_cells), config)
            ] = path
        progress = 0
        while active:
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                path = active.pop(future)
                audit = future.result()
                (output / f"{path.stem}.json").write_text(
                    json.dumps(audit, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                if not audit["exact"]:
                    raise ValueError(f"amended confirmation replay mismatch: {path.name}")
                completed.append(audit)
                progress += 1
                print(f"[amendment-confirmation-replay] {progress}/{len(pending)}", flush=True)
                guard_budget(run_root, config, "confirmation-replay")
                try:
                    next_path = next(iterator)
                except StopIteration:
                    continue
                active[
                    executor.submit(_replay_one, str(next_path), str(source_cells), config)
                ] = next_path
    return {
        "cells": len(completed),
        "all_exact": bool(completed and all(item["exact"] for item in completed)),
        "fresh_process_workers": max(1, workers),
    }


def replay_confirmation(
    source_run_root: Path,
    run_root: Path,
    config: Campaign25Config,
    workers: int,
) -> Path:
    confirmation = verify_confirmation(source_run_root, run_root, config)
    output = stage_path(run_root, config.profile, "confirmation_replay")
    if (output / "SHA256SUMS").exists():
        verify_replay(source_run_root, run_root, config)
        return output
    guard_budget(run_root, config, "confirmation-replay")
    designs = sorted(
        (stage_path(run_root, config.profile, "confirmation") / "cells").glob(
            "cell_*_design.joblib"
        )
    )
    source_cells = base_campaign.screen_path(source_run_root, config.profile) / "cells"
    replay = _replay_cells(
        designs,
        output / "audits",
        source_cells,
        config,
        run_root,
        min(workers, config.replay_workers),
    )
    if not replay["all_exact"] or replay["cells"] != confirmation["cells"]:
        raise ValueError("amended confirmation exact replay failed")
    registration = verify_registration(source_run_root, run_root, config)
    payload = {
        "format": "fep-surprise-25a-confirmation-replay-v1",
        "status": "sealed_exact_before_analysis",
        "confirmation_id": confirmation["confirmation_id"],
        **replay,
        "source_tree_matches_registration": registration["sources"] == _source_hashes(),
    }
    payload["replay_id"] = canonical_digest(payload)
    (output / "replay.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_checksums(output)
    return output


def verify_replay(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> dict[str, Any]:
    confirmation = verify_confirmation(source_run_root, run_root, config)
    output = stage_path(run_root, config.profile, "confirmation_replay")
    verify_checksums(output)
    payload = _json(output / "replay.json")
    identifier = payload.pop("replay_id")
    if canonical_digest(payload) != identifier:
        raise ValueError("amended replay identifier mismatch")
    payload["replay_id"] = identifier
    if payload["confirmation_id"] != confirmation["confirmation_id"] or not payload["all_exact"]:
        raise ValueError("amended replay is not exact")
    return payload


def analyze(
    source_run_root: Path, run_root: Path, config: Campaign25Config
) -> Path:
    registration = verify_registration(source_run_root, run_root, config)
    confirmation = verify_confirmation(source_run_root, run_root, config)
    replay = verify_replay(source_run_root, run_root, config)
    validation = verify_validation(run_root, config)
    audit = verify_source_audit(source_run_root, run_root, config)
    guard_budget(run_root, config, "analysis")
    destination = stage_path(run_root, config.profile, "analysis")
    if destination.exists():
        verify_checksums(destination)
        return destination
    cohort = _amendment_cohort_integrity(
        stage_path(run_root, config.profile, "confirmation"),
        config,
        int(confirmation["cells"]),
    )
    integrity = {
        "validation_all_pass": bool(validation["results"]["all_pass"]),
        "source_capsule_unchanged": True,
        "source_screen_exact_replay": bool(audit["source_screen_replay_exact"]),
        "fresh_confirmation_exact_replay": bool(replay["all_exact"]),
        "complete_confirmation_artifact_cohort": bool(
            all(value for key, value in cohort.items() if not key.endswith("retained"))
        ),
        "source_tree_matches_registration": bool(registration["sources"] == _source_hashes()),
        "analysis_firewall_intact": bool(not confirmation["analysis_artifacts_present"]),
        "partial_original_designs_not_reused": bool(
            audit["disclosure"]["partial_designs_reused"] is False
        ),
    }
    with atomic_destination(destination) as output:
        metrics = analyze_confirmation(
            stage_path(run_root, config.profile, "confirmation") / "cells",
            config,
            output,
            integrity,
        )
        seal = {
            "format": "fep-surprise-25a-analysis-seal-v1",
            "status": "sealed_after_exact_confirmation_replay",
            "registration_id": registration["registration_id"],
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


def run_all(
    source_run_root: Path,
    run_root: Path,
    config: Campaign25Config,
    workers: int,
) -> list[Path]:
    return [
        audit_source(source_run_root, run_root, config),
        validate_stage(source_run_root, run_root, config),
        benchmark(run_root, config, workers),
        register(source_run_root, run_root, config),
        prepare_confirmation(source_run_root, run_root, config, workers),
        generate_confirmation(source_run_root, run_root, config, workers),
        replay_confirmation(source_run_root, run_root, config, workers),
        analyze(source_run_root, run_root, config),
    ]


def status(source_run_root: Path, run_root: Path, profile: str) -> dict[str, Any]:
    root = profile_path(run_root, profile)
    output: dict[str, Any] = {
        "profile": profile,
        "source_run_root": str(source_run_root.resolve()),
        "run_root": str(run_root.resolve()),
    }
    for name in (
        "source_audit",
        "validation",
        "benchmark",
        "registration",
        "confirmation",
        "confirmation_replay",
        "analysis",
    ):
        path = root / name
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
            entry["replay_audits"] = len(list(audits.glob("*.json")))
        output[name] = entry
    try:
        registration_file = root / "registration" / "protocol.json"
        if registration_file.exists():
            config = profile_config(
                profile, _json(registration_file)["source_registration_id"]
            )
        else:
            config = config_for_source(source_run_root, profile)
        output["budget"] = (
            budget_status(run_root, config)
            if (root / "budget_start.json").exists()
            else None
        )
        benchmark_file = root / "benchmark" / "benchmark.json"
        if benchmark_file.exists():
            projection = _json(benchmark_file)["projection"]
            output["timing_projection"] = projection
            if output["budget"] is not None:
                projected_epoch = float(output["budget"]["started_epoch"]) + float(
                    projection["conservative_total_seconds"]
                )
                output["projected_conservative_completion_epoch"] = projected_epoch
                output["projected_conservative_completion_utc"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(projected_epoch)
                )
    except Exception as error:  # status remains useful for a damaged capsule
        output["budget_error"] = str(error)
    return output


__all__ = [
    "analyze",
    "audit_source",
    "benchmark",
    "config_for_source",
    "generate_confirmation",
    "prepare_confirmation",
    "register",
    "replay_confirmation",
    "run_all",
    "status",
    "validate_stage",
]
