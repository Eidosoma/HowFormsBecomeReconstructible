from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from fep_surprise_2.validation import validate as validate_foundation
from plastic_heredity.config import CANDIDATES as SIMULATOR_CONTRACTS
from plastic_heredity.config import GardConfig
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import generate_beta, generate_initial_composition

from .config import Campaign25Config
from .interventions import (
    arm_launches25,
    beta_variants25,
    launch_metrics25,
    log_beta_sigma,
)
from .regime import mass_preserving_perturbations


def validate(config: Campaign25Config, destination: Path) -> dict[str, Any]:
    """Validate the deterministic observer foundation and new transforms."""

    foundation_dir = destination / "foundation"
    foundation = validate_foundation(config, foundation_dir)  # type: ignore[arg-type]
    gard = GardConfig()
    rng = np.random.default_rng(2525)
    beta = generate_beta(gard, rng)
    state = generate_initial_composition(gard, rng)
    order = np.arange(gard.n_types, dtype=np.int64)[::-1]
    variants = beta_variants25(beta, order)
    sigma_errors = {
        key: abs(log_beta_sigma(variants[key]) - target)
        for key, target in (
            ("sigma_250", 2.50),
            ("sigma_325", 3.25),
            ("sigma_500", 5.00),
        )
    }
    mean_errors = {
        key: abs(float(np.mean(value)) / float(np.mean(beta)) - 1.0)
        for key, value in variants.items()
        if key not in ("native", "raw_morph_050")
    }
    normalized_sigma_error = abs(
        log_beta_sigma(variants["normalized_morph_050"])
        - log_beta_sigma(beta)
    )
    raw_reduces_variance = bool(
        log_beta_sigma(variants["raw_morph_050"]) < log_beta_sigma(beta)
    )
    launches = arm_launches25(beta, state, order)
    isomorphism_errors = {
        candidate: abs(
            launch_metrics25(
                beta,
                state,
                launches["ISOMORPHIC_BOTH_100"],
                gard,
                SIMULATOR_CONTRACTS[candidate],
            )[-1]
        )
        for candidate in ("02", "03")
    }
    perturbations = mass_preserving_perturbations(state, 8, 2525)
    perturbation_mass_exact = bool(
        np.all(perturbations.sum(axis=1) == int(state.sum()))
        and np.all(perturbations >= 0)
        and np.all(np.abs(perturbations - state).sum(axis=1) == 2)
    )
    seed_firewalls = len(
        {
            derive_seed(config.master_seed, f"experiment25.{domain}", 0)
            for domain in (
                "screen", "pilot", "main", "durability", "bootstrap", "randomization"
            )
        }
    ) == 6
    results = {
        "format": "fep-surprise-25-validation-v1",
        "foundation": foundation,
        "sigma_max_abs_error": max(sigma_errors.values()),
        "arithmetic_mean_max_relative_error": max(mean_errors.values()),
        "normalized_morph_sigma_abs_error": normalized_sigma_error,
        "raw_morph_reduces_log_variance": raw_reduces_variance,
        "isomorphism_aligned_local_mismatch": isomorphism_errors,
        "mass_preserving_damage_design": perturbation_mass_exact,
        "purpose_seed_domains_distinct": seed_firewalls,
    }
    results["all_pass"] = bool(
        foundation["all_pass"]
        and results["sigma_max_abs_error"] <= 1e-12
        and results["arithmetic_mean_max_relative_error"] <= 1e-12
        and results["normalized_morph_sigma_abs_error"] <= 1e-12
        and results["raw_morph_reduces_log_variance"]
        and max(isomorphism_errors.values()) <= config.aligned_mismatch_tolerance
        and results["mass_preserving_damage_design"]
        and results["purpose_seed_domains_distinct"]
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "validation.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not results["all_pass"]:
        raise ValueError(f"Experiment 2.5 validation failed: {results}")
    return results
