from __future__ import annotations

import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from . import compat as _compat  # noqa: F401
from .config import Campaign15Config
from .observers import (
    INVARIANT_KNN,
    LEGACY_KNN,
    SHELF,
    fit_observer_ensemble,
    scale_invariance_error,
)
from fep_surprise.tracing import traced_advance
from plastic_heredity.config import CANDIDATES, GardConfig
from plastic_heredity.regime_confirmation import evaluate_regime
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import (
    FissionRecord,
    advance_fission,
    generate_beta,
    generate_initial_composition,
)


VALIDATION_SEED = 0x15A11D


def _strict_fixture() -> bool:
    old = np.zeros(100, dtype=np.int64)
    old[0] = 80
    form = np.zeros(100, dtype=np.int64)
    form[1] = 40
    records = [
        FissionRecord(old, np.r_[np.array([40]), np.zeros(99, dtype=int)], 0.5, 1)
    ]
    for _ in range(8):
        records.append(FissionRecord(form * 2, form.copy(), 1.0, 1))
    return bool(evaluate_regime(records).primary_all8)


def _scientific_geometry(
    phase_count: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return 1,600 parents so each reference half has scientific 800 x 100 geometry."""

    rng = np.random.default_rng(VALIDATION_SEED)
    parents = []
    phases = []
    lineages = []
    phase_masses = np.rint(np.linspace(40, 80, phase_count)).astype(int)
    for lineage in range(16):
        center = rng.dirichlet(np.full(100, 0.35))
        for _ in range(100):
            probability = 0.85 * center + 0.15 * rng.dirichlet(np.full(100, 0.5))
            probability /= probability.sum()
            parent = rng.multinomial(80, probability)
            parents.append(parent)
            phases.append(
                np.stack([rng.multinomial(int(mass), probability) for mass in phase_masses])
            )
            lineages.append(lineage)
    return np.asarray(parents), np.asarray(phases), np.asarray(lineages)


def _observer_kwargs(config: Campaign15Config) -> dict[str, Any]:
    return {
        "pseudocount": config.pseudocount,
        "reference_mass": config.reference_mass,
        "pca_variance": config.pca_variance,
        "pca_min": config.pca_min,
        "pca_max": 20,
        "knn_k": config.knn_k,
        "mixture_k_max": min(config.mixture_k_max, 3),
        "training_subsample": 800,
        "seed": VALIDATION_SEED + 1,
    }


def _fresh_process_fit(config: Campaign15Config) -> dict[str, Any]:
    parents, phases, lineages = _scientific_geometry(len(config.phase_grid))
    model = fit_observer_ensemble(
        parents, phases, lineages, **_observer_kwargs(config)
    )
    probe = phases[:32]
    return {
        "model_hash": joblib.hash(model),
        "scores": {
            observer: model.anomaly_grid(probe, observer)
            for observer in (LEGACY_KNN, INVARIANT_KNN, SHELF)
        },
    }


def validate(config: Campaign15Config, destination: Path) -> dict[str, Any]:
    gard = GardConfig()
    beta = generate_beta(gard, np.random.default_rng(1))
    initial = generate_initial_composition(gard, np.random.default_rng(2))
    trace_exact = True
    for candidate in ("02", "03"):
        left = np.random.default_rng(3)
        right = np.random.default_rng(3)
        ordinary = advance_fission(initial, beta, gard, CANDIDATES[candidate], left)
        traced = traced_advance(
            initial, beta, gard, CANDIDATES[candidate], right, config.phase_grid
        ).record
        trace_exact &= bool(
            np.array_equal(ordinary.parent, traced.parent)
            and np.array_equal(ordinary.daughter, traced.daughter)
            and ordinary.h == traced.h
            and ordinary.growth_steps == traced.growth_steps
            and left.bit_generator.state == right.bit_generator.state
        )

    parents, phases, lineages = _scientific_geometry(len(config.phase_grid))
    kwargs = _observer_kwargs(config)
    first = fit_observer_ensemble(parents, phases, lineages, **kwargs)
    second = fit_observer_ensemble(parents, phases, lineages, **kwargs)
    probe = phases[:32]
    deterministic_scores = {}
    for observer in (LEGACY_KNN, INVARIANT_KNN, SHELF):
        left_score = first.anomaly_grid(probe, observer)
        right_score = second.anomaly_grid(probe, observer)
        deterministic_scores[observer] = float(np.max(np.abs(left_score - right_score)))
    deterministic_hash = joblib.hash(first) == joblib.hash(second)

    spawn = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=spawn) as one_worker:
        process_one = one_worker.submit(_fresh_process_fit, config).result()
    with ProcessPoolExecutor(max_workers=2, mp_context=spawn) as two_workers:
        process_two = [
            future.result()
            for future in (
                two_workers.submit(_fresh_process_fit, config),
                two_workers.submit(_fresh_process_fit, config),
            )
        ]
    fresh_results = [process_one, *process_two]
    fresh_process_hash_exact = bool(
        all(result["model_hash"] == joblib.hash(first) for result in fresh_results)
    )
    fresh_process_score_errors = {
        observer: max(
            float(
                np.max(
                    np.abs(
                        result["scores"][observer]
                        - first.anomaly_grid(probe, observer)
                    )
                )
            )
            for result in fresh_results
        )
        for observer in (LEGACY_KNN, INVARIANT_KNN, SHELF)
    }

    scale_errors = {
        observer: scale_invariance_error(first, parents[:32], observer)
        for observer in (LEGACY_KNN, INVARIANT_KNN, SHELF)
    }

    order = np.random.default_rng(VALIDATION_SEED + 2).permutation(100)
    permuted = fit_observer_ensemble(
        parents[:, order], phases[:, :, order], lineages, **kwargs
    )
    relabel_errors = {}
    for observer in (INVARIANT_KNN, SHELF):
        original_score = first.anomaly_grid(probe, observer)
        permuted_score = permuted.anomaly_grid(probe[:, :, order], observer)
        relabel_errors[observer] = float(
            np.max(np.abs(original_score - permuted_score))
        )

    development_seed = derive_seed(config.master_seed, "development.beta", 0)
    confirmation_seed = derive_seed(config.master_seed, "confirmation.beta", 0)
    pca_dimensions = [len(half.projection.coordinate_mean) for half in first.halves]
    results: dict[str, Any] = {
        "format": "fep-surprise-15-validation-v1",
        "traced_untraced_exact": trace_exact,
        "strict8_fixture_positive": _strict_fixture(),
        "scientific_scale_shape": [800, 100],
        "scientific_scale_pca_dimensions": pca_dimensions,
        "repeated_model_hash_exact": deterministic_hash,
        "repeated_score_max_abs_errors": deterministic_scores,
        "fresh_process_worker_count_model_hash_exact": fresh_process_hash_exact,
        "fresh_process_worker_count_score_max_abs_errors": (
            fresh_process_score_errors
        ),
        "scale_max_abs_errors": scale_errors,
        "relabel_max_abs_errors": relabel_errors,
        "legacy_scale_positive_control_nonzero": scale_errors[LEGACY_KNN] > 1e-6,
        "primary_scale_within_tolerance": bool(
            scale_errors[INVARIANT_KNN] <= config.scale_tolerance
            and scale_errors[SHELF] <= config.scale_tolerance
        ),
        "primary_relabel_within_tolerance": bool(
            all(value <= config.relabel_tolerance for value in relabel_errors.values())
        ),
        "development_confirmation_seed_domains_distinct": bool(
            development_seed != confirmation_seed
        ),
        "simulator_root": str(_compat.PLASTIC_HEREDITY_ROOT),
    }
    results["all_pass"] = bool(
        results["traced_untraced_exact"]
        and results["strict8_fixture_positive"]
        and results["repeated_model_hash_exact"]
        and max(deterministic_scores.values()) <= 1e-12
        and results["fresh_process_worker_count_model_hash_exact"]
        and max(fresh_process_score_errors.values()) <= 1e-12
        and results["legacy_scale_positive_control_nonzero"]
        and results["primary_scale_within_tolerance"]
        and results["primary_relabel_within_tolerance"]
        and results["development_confirmation_seed_domains_distinct"]
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "validation.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not results["all_pass"]:
        raise ValueError(f"Experiment 1.5 validation failed: {results}")
    return results
